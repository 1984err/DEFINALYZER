"""Durable, non-overwriting JSON output for raw collection runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


EVIDENCE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class EvidenceRecord:
    request_name: str
    operation: str
    chain: str
    status: str
    evidence: Mapping[str, Any] | None = None
    collection_error: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"collected", "failed"}:
            raise ValueError("Evidence status must be 'collected' or 'failed'.")
        if self.status == "collected" and self.evidence is None:
            raise ValueError("Collected evidence record requires 'evidence'.")
        if self.status == "failed" and self.collection_error is None:
            raise ValueError("Failed evidence record requires 'collection_error'.")


@dataclass(frozen=True)
class EvidenceBundle:
    job_name: str
    started_at: str
    completed_at: str
    records: Sequence[EvidenceRecord]
    job_source: str | None = None
    job_metadata: Mapping[str, Any] = field(default_factory=dict)
    chain_snapshots: Mapping[str, Any] = field(default_factory=dict)
    evidence_schema_version: int = EVIDENCE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_evidence_bundle(
    bundle: EvidenceBundle,
    destination: str | Path,
) -> Path:
    """Write one bundle without replacing evidence already on disk."""

    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        bundle.to_dict(),
        indent=2,
        ensure_ascii=False,
    )

    try:
        with output_path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(serialized)
            file.write("\n")
    except FileExistsError as exc:
        raise FileExistsError(
            f"Evidence output already exists and will not be overwritten: "
            f"{output_path}"
        ) from exc

    return output_path
