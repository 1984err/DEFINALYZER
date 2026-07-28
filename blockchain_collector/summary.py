"""Human-readable summaries of evidence bundles without claim interpretation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .evidence import EvidenceBundle, EvidenceRecord


def render_evidence_summary(bundle: EvidenceBundle) -> str:
    lines = [
        f"# Evidence Summary: {bundle.job_name}",
        "",
        "> Collection summary only. This does not confirm or deny any claim.",
        "",
        f"- Started: `{bundle.started_at}`",
        f"- Completed: `{bundle.completed_at}`",
        f"- Raw job: `{bundle.job_source or 'Not recorded'}`",
        "",
        "## Chain snapshots",
        "",
    ]

    if not bundle.chain_snapshots:
        lines.append("- No chain snapshot was recorded.")
    else:
        for chain, snapshot in bundle.chain_snapshots.items():
            result = _nested(snapshot, "rpc", "result")
            block_number = (
                result.get("number") if isinstance(result, Mapping) else None
            )
            block_hash = result.get("hash") if isinstance(result, Mapping) else None
            lines.append(
                f"- **{chain}** — block `{block_number or 'Unavailable'}`, "
                f"hash `{block_hash or 'Unavailable'}`"
            )

    lines.extend(
        [
            "",
            "## Requests",
            "",
            "| Request | Chain | Operation | Status |",
            "|---|---|---|---|",
        ]
    )

    for record in bundle.records:
        lines.append(
            f"| {record.request_name} | {record.chain} | "
            f"{record.operation} | {record.status} |"
        )

    for record in bundle.records:
        lines.extend(_record_details(record))

    return "\n".join(lines).rstrip() + "\n"


def write_evidence_summary(
    bundle: EvidenceBundle,
    destination: str | Path,
) -> Path:
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with output_path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(render_evidence_summary(bundle))
    except FileExistsError as exc:
        raise FileExistsError(
            f"Evidence summary already exists and will not be overwritten: "
            f"{output_path}"
        ) from exc

    return output_path


def _record_details(record: EvidenceRecord) -> list[str]:
    lines = ["", f"### {record.request_name}", ""]

    if record.status == "failed":
        error = record.collection_error or {}
        lines.append(
            f"- Collection error: `{error.get('type', 'Unknown')}` — "
            f"{error.get('message', 'No message')}"
        )
        return lines

    evidence = record.evidence or {}

    if record.operation == "standard_call":
        lines.extend(_standard_call_lines(evidence))
    elif record.operation == "erc20_snapshot":
        calls = evidence.get("calls", {})

        if isinstance(calls, Mapping):
            for name, call in calls.items():
                lines.extend(_standard_call_lines(call, label=name))

        balances = evidence.get("balances", [])

        if isinstance(balances, list):
            for balance in balances:
                address = balance.get("address")
                call = balance.get("evidence", {})
                lines.extend(
                    _standard_call_lines(call, label=f"balanceOf({address})")
                )
    elif record.operation in {"eip1967_slots", "contract_snapshot"}:
        proxy_evidence = (
            evidence.get("eip1967_slots", evidence)
            if isinstance(evidence, Mapping)
            else {}
        )
        slots = (
            proxy_evidence.get("slots", {})
            if isinstance(proxy_evidence, Mapping)
            else {}
        )

        if isinstance(slots, Mapping):
            for name, slot in slots.items():
                address = (
                    slot.get("decoded_address")
                    if isinstance(slot, Mapping)
                    else None
                )
                lines.append(f"- ERC-1967 {name}: `{address or 'Unavailable'}`")
    elif record.operation == "erc20_transfers":
        logs = evidence.get("logs", {})
        chunks = logs.get("chunks", []) if isinstance(logs, Mapping) else []
        log_count = 0

        for chunk in chunks if isinstance(chunks, list) else []:
            result = _nested(chunk, "evidence", "rpc", "result")

            if isinstance(result, list):
                log_count += len(result)

        lines.append(f"- Complete range: `{logs.get('complete')}`")
        lines.append(f"- Chunks: `{len(chunks)}`")
        lines.append(f"- Raw logs returned: `{log_count}`")
    else:
        rpc_method = _nested(evidence, "rpc", "method")
        lines.append(f"- RPC method: `{rpc_method or 'See raw evidence'}`")

    if record.status == "partial":
        lines.append("- Warning: this request contains incomplete evidence.")

    return lines


def _standard_call_lines(
    evidence: Mapping[str, Any],
    *,
    label: str | None = None,
) -> list[str]:
    call = evidence.get("standard_call", {})

    if not isinstance(call, Mapping):
        return ["- Decoded result: `Unavailable`"]

    name = label or call.get("signature") or call.get("function") or "call"
    decoded = call.get("decoded_result")
    decode_error = call.get("decode_error")
    lines = [f"- {name}: `{decoded if decoded is not None else 'Unavailable'}`"]

    if decode_error:
        lines.append(f"  - Decode error: {decode_error}")

    return lines


def _nested(value: Any, *keys: str) -> Any:
    current = value

    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)

    return current
