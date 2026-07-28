"""Execute versioned collection jobs and retain every collection outcome."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .evidence import EvidenceBundle, EvidenceRecord, utc_now
from .chunked_logs import collect_logs_chunked
from .contract_snapshot import collect_contract_snapshot
from .evm import RawEvmCollector
from .jobs import CollectionJob, CollectionRequest
from .proxy_slots import collect_eip1967_slots
from .rpc import JsonRpcClient
from .standard_calls import collect_standard_call
from .token_transfers import collect_erc20_transfers
from .token_snapshot import collect_erc20_snapshot


ClientFactory = Callable[[str], JsonRpcClient]


@dataclass(frozen=True)
class ChainRuntime:
    collector: RawEvmCollector | None
    pinned_block: str | None = None
    snapshot_evidence: Mapping[str, Any] | None = None
    setup_error: Mapping[str, str] | None = None


def execute_collection_job(
    job: CollectionJob,
    *,
    job_source: str | None = None,
    client_factory: ClientFactory | None = None,
) -> EvidenceBundle:
    """Execute all requests, recording failures without stopping later work."""

    started_at = utc_now()
    factory = client_factory or JsonRpcClient.from_environment
    runtimes = _prepare_chains(job, factory)
    records: list[EvidenceRecord] = []

    for request in job.requests:
        runtime = runtimes[request.chain]

        if runtime.setup_error is not None:
            records.append(
                _failed_record(
                    request,
                    error_type=runtime.setup_error["type"],
                    message=runtime.setup_error["message"],
                    stage="chain_setup",
                )
            )
            continue

        try:
            collected = _execute_request(
                runtime.collector,
                request,
                pinned_block=runtime.pinned_block,
            )
            evidence_document = collected.to_dict()
            status = (
                "partial"
                if _evidence_is_partial(request.operation, evidence_document)
                else "collected"
            )
            records.append(
                EvidenceRecord(
                    request_name=request.name,
                    operation=request.operation,
                    chain=request.chain,
                    status=status,
                    evidence=evidence_document,
                )
            )
        except Exception as exc:
            records.append(
                _failed_record(
                    request,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    stage="collection",
                )
            )

    return EvidenceBundle(
        job_name=job.name,
        job_source=job_source,
        job_metadata=job.metadata,
        chain_snapshots={
            chain: runtime.snapshot_evidence
            for chain, runtime in runtimes.items()
            if runtime.snapshot_evidence is not None
        },
        started_at=started_at,
        completed_at=utc_now(),
        records=records,
    )


def _prepare_chains(
    job: CollectionJob,
    factory: ClientFactory,
) -> dict[str, ChainRuntime]:
    runtimes: dict[str, ChainRuntime] = {}

    for chain in dict.fromkeys(request.chain for request in job.requests):
        try:
            client = factory(chain)
            client.validate_chain_id()
            collector = RawEvmCollector(client)
            chain_requests = [
                request for request in job.requests if request.chain == chain
            ]

            if _requests_require_snapshot(chain_requests):
                snapshot = collector.get_block("latest")
                block_result = snapshot.rpc.result

                if (
                    snapshot.rpc.error is not None
                    or not isinstance(block_result, dict)
                    or not isinstance(block_result.get("number"), str)
                ):
                    raise RuntimeError(
                        "Latest block snapshot did not return a block number."
                    )

                runtimes[chain] = ChainRuntime(
                    collector=collector,
                    pinned_block=block_result["number"],
                    snapshot_evidence=snapshot.to_dict(),
                )
            else:
                runtimes[chain] = ChainRuntime(collector=collector)
        except Exception as exc:
            runtimes[chain] = ChainRuntime(
                collector=None,
                setup_error={
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            )

    return runtimes


def _requests_require_snapshot(
    requests: list[CollectionRequest],
) -> bool:
    block_operations = {
        "contract_snapshot",
        "eip1967_slots",
        "erc20_snapshot",
        "get_balance",
        "get_code",
        "get_storage_at",
        "raw_call",
        "standard_call",
    }

    for request in requests:
        parameters = request.parameters

        if request.operation in block_operations:
            if parameters.get("block", "latest") == "latest":
                return True
        elif request.operation == "get_block":
            if parameters.get("block") == "latest":
                return True
        elif request.operation in {
            "erc20_transfers",
            "get_logs",
            "get_logs_chunked",
        }:
            if (
                parameters.get("from_block") == "latest"
                or parameters.get("to_block") == "latest"
            ):
                return True

    return False


def _execute_request(
    collector: RawEvmCollector | None,
    request: CollectionRequest,
    *,
    pinned_block: str | None,
):
    if collector is None:
        raise RuntimeError("Collector runtime is unavailable.")

    parameters: dict[str, Any] = dict(request.parameters)
    _pin_latest_parameters(parameters, request.operation, pinned_block)

    if request.operation == "get_code":
        return collector.get_code(request.target, **parameters)
    if request.operation == "contract_snapshot":
        return collect_contract_snapshot(collector, request.target, **parameters)
    if request.operation == "get_balance":
        return collector.get_balance(request.target, **parameters)
    if request.operation == "get_storage_at":
        return collector.get_storage_at(request.target, **parameters)
    if request.operation == "raw_call":
        return collector.call(request.target, **parameters)
    if request.operation == "standard_call":
        return collect_standard_call(collector, request.target, **parameters)
    if request.operation == "eip1967_slots":
        return collect_eip1967_slots(collector, request.target, **parameters)
    if request.operation == "get_logs_chunked":
        return collect_logs_chunked(collector, request.target, **parameters)
    if request.operation == "erc20_transfers":
        return collect_erc20_transfers(collector, request.target, **parameters)
    if request.operation == "erc20_snapshot":
        return collect_erc20_snapshot(collector, request.target, **parameters)
    if request.operation == "get_transaction":
        return collector.get_transaction(**parameters)
    if request.operation == "get_transaction_receipt":
        return collector.get_transaction_receipt(**parameters)
    if request.operation == "get_block":
        return collector.get_block(**parameters)
    if request.operation == "get_logs":
        return collector.get_logs(**parameters)

    raise ValueError(f"Unsupported operation {request.operation!r}.")


def _pin_latest_parameters(
    parameters: dict[str, Any],
    operation: str,
    pinned_block: str | None,
) -> None:
    if pinned_block is None:
        return

    if operation in {
        "get_balance",
        "contract_snapshot",
        "get_code",
        "get_storage_at",
        "raw_call",
        "standard_call",
        "eip1967_slots",
        "erc20_snapshot",
    }:
        if parameters.get("block", "latest") == "latest":
            parameters["block"] = pinned_block
    elif operation == "get_block" and parameters.get("block") == "latest":
        parameters["block"] = pinned_block
    elif operation in {"get_logs", "get_logs_chunked", "erc20_transfers"}:
        for key in ("from_block", "to_block"):
            if parameters.get(key) == "latest":
                parameters[key] = pinned_block


def _evidence_is_partial(
    operation: str,
    evidence: Mapping[str, Any],
) -> bool:
    if operation == "get_logs_chunked":
        return evidence.get("complete") is False
    if operation == "erc20_transfers":
        logs = evidence.get("logs")
        return isinstance(logs, Mapping) and logs.get("complete") is False

    return False


def _failed_record(
    request: CollectionRequest,
    *,
    error_type: str,
    message: str,
    stage: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        request_name=request.name,
        operation=request.operation,
        chain=request.chain,
        status="failed",
        collection_error={
            "stage": stage,
            "type": error_type,
            "message": message,
        },
    )
