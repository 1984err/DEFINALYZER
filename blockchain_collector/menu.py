"""Guided terminal interface for standalone human use."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Sequence

from .cli import EXIT_ERROR, EXIT_PARTIAL_FAILURE, EXIT_SUCCESS
from .envfile import load_environment_file
from .evidence import write_evidence_bundle
from .executor import ClientFactory, execute_collection_job
from .jobs import CollectionJob
from .request_validation import TRANSACTION_HASH_PATTERN
from .summary import write_evidence_summary
from .verification_import import (
    import_verification_requests,
    load_verification_requests,
    write_json_new,
)


InputFunction = Callable[[str], str]
PrintFunction = Callable[[str], None]

CHAIN_CHOICES = {
    "1": ("ethereum", "Ethereum", 1),
    "2": ("arbitrum", "Arbitrum One", 42161),
    "3": ("base", "Base Mainnet", 8453),
}
CHECK_CHOICES = {
    "1": "contract_snapshot",
    "2": "erc20_snapshot",
    "3": "eip1967_slots",
    "4": "erc20_transfers",
    "5": "standard_call",
    "6": "transaction_bundle",
}
STANDARD_CALL_CHOICES = {
    "1": ("totalSupply", 0),
    "2": ("balanceOf", 1),
    "3": ("allowance", 2),
    "4": ("owner", 0),
    "5": ("name", 0),
    "6": ("symbol", 0),
    "7": ("decimals", 0),
}
WORKFLOW_CHOICES = {
    "1": "single_check",
    "2": "verification_import",
    "3": "registry_check",
}


def run_guided_menu(
    *,
    input_fn: InputFunction = input,
    print_fn: PrintFunction = print,
    client_factory: ClientFactory | None = None,
    working_directory: str | Path = ".",
) -> int:
    root = Path(working_directory).resolve()
    env_path = root / ".env"

    try:
        if env_path.exists():
            load_environment_file(env_path)

        print_fn("DEFINALYZER Blockchain Evidence Collector")
        print_fn("This collects evidence only; it does not verify claims.")
        print_fn("")
        print_fn("Select workflow:")
        print_fn("  1. Create one guided evidence check")
        print_fn("  2. Import structured verification requests")
        print_fn("  3. Select a project registry target")
        workflow = WORKFLOW_CHOICES[
            _choice(input_fn, "Workflow [1-3]: ", WORKFLOW_CHOICES)
        ]

        if workflow == "verification_import":
            return _run_import_workflow(
                root=root,
                input_fn=input_fn,
                print_fn=print_fn,
                client_factory=client_factory,
            )

        registry_target = None
        if workflow == "registry_check":
            registry_target = _select_registry_target(
                root=root,
                input_fn=input_fn,
                print_fn=print_fn,
            )
            chain_key = registry_target["chain_key"]
            chain_name = registry_target["chain"]
            chain_id = registry_target["chain_id"]
            print_fn(f"Chain: {chain_name}")
        else:
            print_fn("")
            print_fn("Select chain:")
            print_fn("  1. Ethereum")
            print_fn("  2. Arbitrum One")
            print_fn("  3. Base")
            chain_key, chain_name, chain_id = CHAIN_CHOICES[
                _choice(input_fn, "Chain [1-3]: ", CHAIN_CHOICES)
            ]

        print_fn("")
        print_fn("Select check:")
        print_fn("  1. Contract snapshot")
        print_fn("  2. ERC-20 token snapshot")
        print_fn("  3. ERC-1967 proxy slots")
        print_fn("  4. ERC-20 transfer history")
        print_fn("  5. Standard contract read")
        available_checks = CHECK_CHOICES
        if registry_target is None:
            print_fn("  6. Transaction and receipt")
        else:
            available_checks = {
                key: value for key, value in CHECK_CHOICES.items() if key != "6"
            }
        operation = available_checks[
            _choice(
                input_fn,
                "Check [1-5]: " if registry_target else "Check [1-6]: ",
                available_checks,
            )
        ]

        if operation == "transaction_bundle":
            transaction_hash = _required(input_fn, "Transaction hash: ")

            if not TRANSACTION_HASH_PATTERN.fullmatch(transaction_hash):
                raise ValueError(
                    "Transaction hash must be 0x followed by 64 hexadecimal "
                    "characters."
                )

            source = _required(
                input_fn,
                "Source URL or document containing this transaction: ",
            )
            job_name = _job_name(_required(input_fn, "Short job name: "))
            requests = [
                {
                    "name": f"{job_name}-transaction",
                    "chain": chain_key,
                    "operation": "get_transaction",
                    "parameters": {"transaction_hash": transaction_hash},
                },
                {
                    "name": f"{job_name}-receipt",
                    "chain": chain_key,
                    "operation": "get_transaction_receipt",
                    "parameters": {"transaction_hash": transaction_hash},
                },
            ]
            metadata = {
                "created_by": "guided-terminal-menu",
                "transaction_source": source,
            }
        else:
            if registry_target:
                address = registry_target["address"]
                target_name = registry_target["target_name"]
                role = registry_target["role"]
                source = registry_target["source"]
            else:
                address = _required(input_fn, "Contract address: ")
                target_name = _required(input_fn, "Documented component name: ")
                role = input_fn("Documented role (optional): ").strip() or None
                source = _required(input_fn, "Registry source URL or document: ")
            job_name = _job_name(_required(input_fn, "Short job name: "))
            parameters = _operation_parameters(operation, input_fn, print_fn)
            requests = [
                {
                    "name": f"{job_name}-request",
                    "chain": chain_key,
                    "operation": operation,
                    "parameters": parameters,
                    "target": {
                        "target_name": target_name,
                        "role": role,
                        "address": address,
                        "chain": chain_name,
                        "chain_id": chain_id,
                        "source": source,
                    },
                }
            ]
            metadata = {
                "created_by": "guided-terminal-menu",
            }

        job_document = {
            "schema_version": 1,
            "name": job_name,
            "metadata": metadata,
            "requests": requests,
        }
        job = CollectionJob.from_mapping(job_document)
        job_path = root / "jobs" / f"{job_name}.json"
        evidence_path = root / "evidence" / f"{job_name}.json"
        summary_path = root / "evidence" / f"{job_name}.md"

        _require_new_paths(job_path, evidence_path, summary_path)
        _write_job(job_document, job_path)
        bundle = execute_collection_job(
            job,
            job_source=str(job_path),
            client_factory=client_factory,
        )
        write_evidence_bundle(bundle, evidence_path)
        write_evidence_summary(bundle, summary_path)
    except (EOFError, KeyboardInterrupt):
        print_fn("\nCancelled.")
        return EXIT_ERROR
    except (KeyError, OSError, ValueError, RuntimeError) as exc:
        print_fn(f"Stopped: {exc}")
        return EXIT_ERROR

    collected = sum(record.status == "collected" for record in bundle.records)
    partial = sum(record.status == "partial" for record in bundle.records)
    failed = sum(record.status == "failed" for record in bundle.records)
    print_fn("")
    print_fn(f"Job saved:      {job_path}")
    print_fn(f"Evidence saved: {evidence_path}")
    print_fn(f"Summary saved:  {summary_path}")
    print_fn(f"Collected: {collected}  Partial: {partial}  Failed: {failed}")

    return EXIT_SUCCESS if not partial and not failed else EXIT_PARTIAL_FAILURE


def _run_import_workflow(
    *,
    root: Path,
    input_fn: InputFunction,
    print_fn: PrintFunction,
    client_factory: ClientFactory | None,
) -> int:
    source_value = _required(
        input_fn,
        "Markdown or JSON verification-request file: ",
    )
    source_path = Path(source_value)

    if not source_path.is_absolute():
        source_path = root / source_path

    source_path = source_path.resolve()
    output_name = _job_name(_required(input_fn, "Short output name: "))
    document = load_verification_requests(source_path)
    result = import_verification_requests(
        document,
        source=str(source_path),
        job_name=output_name,
    )
    report_path = root / "evidence" / f"{output_name}-import-report.json"

    if result.job_document is None:
        _require_new_paths(report_path)
        write_json_new(result.report, report_path)
        print_fn("")
        print_fn("No supported requests were run.")
        print_fn(f"Import report: {report_path}")
        print_fn(
            f"Manual review: {result.report['manual_review_count']}"
        )
        return EXIT_PARTIAL_FAILURE

    job_path = root / "jobs" / f"{output_name}.json"
    evidence_path = root / "evidence" / f"{output_name}.json"
    summary_path = root / "evidence" / f"{output_name}.md"
    _require_new_paths(
        job_path,
        evidence_path,
        summary_path,
        report_path,
    )
    job = result.job

    if job is None:
        raise RuntimeError("Verification import did not create a valid job.")

    write_json_new(result.job_document, job_path)
    write_json_new(result.report, report_path)
    bundle = execute_collection_job(
        job,
        job_source=str(job_path),
        client_factory=client_factory,
    )
    write_evidence_bundle(bundle, evidence_path)
    write_evidence_summary(bundle, summary_path)

    collected = sum(record.status == "collected" for record in bundle.records)
    partial = sum(record.status == "partial" for record in bundle.records)
    failed = sum(record.status == "failed" for record in bundle.records)
    manual = result.report["manual_review_count"]
    print_fn("")
    print_fn(f"Job saved:      {job_path}")
    print_fn(f"Import report:  {report_path}")
    print_fn(f"Evidence saved: {evidence_path}")
    print_fn(f"Summary saved:  {summary_path}")
    print_fn(
        f"Collected: {collected}  Partial: {partial}  Failed: {failed}  "
        f"Manual review: {manual}"
    )

    if partial or failed or manual:
        return EXIT_PARTIAL_FAILURE
    return EXIT_SUCCESS


def _select_registry_target(
    *,
    root: Path,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> dict:
    registry_path = root.parents[1] / "registries" / root.name / "registry.json"
    if not registry_path.exists():
        raise FileNotFoundError(
            "No project registry was found. Run registry generation first: "
            f"{registry_path}"
        )
    document = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Project registry must be a JSON object.")

    chain_lookup = {
        chain_name.casefold(): (chain_key, display_name, chain_id)
        for chain_key, display_name, chain_id in CHAIN_CHOICES.values()
        for chain_name in (
            display_name,
            display_name.replace(" One", ""),
            display_name.replace(" Mainnet", ""),
        )
    }
    targets = []
    for row in document.get("addresses", []):
        if not isinstance(row, dict):
            continue
        chain = str(row.get("chain", "")).casefold()
        chain_data = chain_lookup.get(chain)
        if (
            chain_data is None
            or row.get("status") in {"conflicting", "documented_unresolved"}
            or row.get("provenance") not in {"official_registry", "documented"}
        ):
            continue
        targets.append(
            {
                "target_name": row.get("name"),
                "role": row.get("role"),
                "address": row.get("address"),
                "source": row.get("source"),
                "chain_key": chain_data[0],
                "chain": chain_data[1],
                "chain_id": chain_data[2],
                "kind": row.get("component_type", "Contract"),
            }
        )
    for row in document.get("tokens", []):
        if not isinstance(row, dict):
            continue
        chain_data = chain_lookup.get(str(row.get("network", "")).casefold())
        if chain_data is None:
            continue
        targets.append(
            {
                "target_name": row.get("symbol") or row.get("name"),
                "role": row.get("protocol_relationship"),
                "address": row.get("address"),
                "source": row.get("source"),
                "chain_key": chain_data[0],
                "chain": chain_data[1],
                "chain_id": chain_data[2],
                "kind": row.get("token_type", "Token"),
            }
        )
    valid = [
        target
        for target in targets
        if all(
            isinstance(target.get(field), str) and target[field].strip()
            for field in ("target_name", "address", "source")
        )
    ]
    deduplicated = {
        (
            target["target_name"].casefold(),
            target["chain_key"],
            target["address"].casefold(),
        ): target
        for target in valid
    }
    ordered = sorted(
        deduplicated.values(),
        key=lambda target: (
            target["chain"].casefold(),
            target["kind"].casefold(),
            target["target_name"].casefold(),
        ),
    )
    if not ordered:
        raise ValueError(
            "The registry has no non-conflicting targets on supported chains."
        )

    print_fn("")
    print_fn("Select registry target:")
    choices = {}
    for index, target in enumerate(ordered, start=1):
        key = str(index)
        choices[key] = target
        print_fn(
            f"  {key}. {target['target_name']} "
            f"({target['kind']}, {target['chain']})"
        )
    selected = _choice(input_fn, "Target number: ", choices)
    return choices[selected]


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        print("The guided menu does not accept command-line arguments.", file=sys.stderr)
        return EXIT_ERROR

    return run_guided_menu()


def _operation_parameters(
    operation: str,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> dict:
    if operation == "contract_snapshot":
        include_owner = _yes_no(
            input_fn,
            "Attempt the common owner() read? [y/N]: ",
            default=False,
        )
        return {
            "block": "latest",
            "include_owner_call": include_owner,
        }

    if operation == "erc20_snapshot":
        raw_addresses = input_fn(
            "Addresses whose token balances should be collected "
            "(comma-separated, optional): "
        ).strip()
        addresses = [
            address.strip()
            for address in raw_addresses.split(",")
            if address.strip()
        ]
        return {
            "block": "latest",
            "balance_addresses": addresses,
        }

    if operation == "erc20_transfers":
        from_block = _block_number(
            _required(
                input_fn,
                "Starting block (use the documented deployment block): ",
            ),
            allow_latest=False,
        )
        raw_to_block = (
            input_fn("Ending block [latest]: ").strip() or "latest"
        )
        to_block = _block_number(raw_to_block, allow_latest=True)
        from_address = input_fn(
            "Only transfers from address (optional): "
        ).strip()
        to_address = input_fn(
            "Only transfers to address (optional): "
        ).strip()
        raw_chunk_size = input_fn("Blocks per RPC request [2000]: ").strip()
        chunk_size = int(raw_chunk_size) if raw_chunk_size else 2_000

        if chunk_size <= 0:
            raise ValueError("Blocks per RPC request must be positive.")

        parameters = {
            "from_block": from_block,
            "to_block": to_block,
            "chunk_size": chunk_size,
        }

        if from_address:
            parameters["from_address"] = from_address
        if to_address:
            parameters["to_address"] = to_address

        return parameters

    if operation == "standard_call":
        print_fn("Select function:")
        print_fn("  1. totalSupply()")
        print_fn("  2. balanceOf(address)")
        print_fn("  3. allowance(owner, spender)")
        print_fn("  4. owner()")
        print_fn("  5. name()")
        print_fn("  6. symbol()")
        print_fn("  7. decimals()")
        function, argument_count = STANDARD_CALL_CHOICES[
            _choice(input_fn, "Function [1-7]: ", STANDARD_CALL_CHOICES)
        ]
        arguments = []

        if function == "balanceOf":
            arguments.append(_required(input_fn, "Account address: "))
        elif function == "allowance":
            arguments.append(_required(input_fn, "Owner address: "))
            arguments.append(_required(input_fn, "Spender address: "))

        if len(arguments) != argument_count:
            raise RuntimeError("Standard-call argument collection failed.")

        return {
            "function": function,
            "arguments": arguments,
            "block": "latest",
        }

    return {"block": "latest"}


def _choice(
    input_fn: InputFunction,
    prompt: str,
    choices: dict[str, object],
) -> str:
    while True:
        value = input_fn(prompt).strip()

        if value in choices:
            return value

        print("Please enter one of: " + ", ".join(choices))


def _required(input_fn: InputFunction, prompt: str) -> str:
    while True:
        value = input_fn(prompt).strip()

        if value:
            return value

        print("A value is required.")


def _yes_no(
    input_fn: InputFunction,
    prompt: str,
    *,
    default: bool,
) -> bool:
    value = input_fn(prompt).strip().lower()

    if not value:
        return default
    if value in {"y", "yes"}:
        return True
    if value in {"n", "no"}:
        return False

    raise ValueError("Expected yes or no.")


def _job_name(value: str) -> str:
    normalized = "".join(
        character.lower() if character.isalnum() else "-"
        for character in value
    )
    normalized = "-".join(part for part in normalized.split("-") if part)
    return normalized[:128] or "collection-job"


def _block_number(value: str, *, allow_latest: bool) -> int | str:
    normalized = value.strip().lower()

    if allow_latest and normalized == "latest":
        return "latest"
    if normalized.startswith("0x"):
        try:
            number = int(normalized, 16)
        except ValueError as exc:
            raise ValueError("Block must be a decimal number or 0x quantity.") from exc
    else:
        try:
            number = int(normalized)
        except ValueError as exc:
            raise ValueError("Block must be a decimal number or 0x quantity.") from exc

    if number < 0:
        raise ValueError("Block cannot be negative.")

    return number


def _write_job(document: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("x", encoding="utf-8", newline="\n") as file:
            json.dump(document, file, indent=2)
            file.write("\n")
    except FileExistsError as exc:
        raise FileExistsError(
            f"Job file already exists and will not be overwritten: {path}"
        ) from exc


def _require_new_paths(*paths: Path) -> None:
    existing = [path for path in paths if path.exists()]

    if existing:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Output already exists and will not be overwritten: {joined}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
