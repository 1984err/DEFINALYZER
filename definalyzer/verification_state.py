"""Deterministic identity helpers for planned verification evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


JOB_FINGERPRINT_KEY = "verification_job_sha256"


def verification_job_fingerprint(path: str | Path) -> str:
    """Hash the executable semantics of a verification collection job."""

    input_path = Path(path)
    document = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Verification collection job must be a JSON object.")
    requests = document.get("requests")
    if not isinstance(requests, list) or not requests:
        raise ValueError("Verification collection job has no requests.")
    identity = {
        "schema_version": document.get("schema_version"),
        "name": document.get("name"),
        "requests": requests,
    }
    serialized = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def evidence_job_fingerprint(bundle: Mapping[str, Any]) -> str | None:
    metadata = bundle.get("job_metadata")
    if not isinstance(metadata, Mapping):
        return None
    value = metadata.get(JOB_FINGERPRINT_KEY)
    return value if isinstance(value, str) and value else None
