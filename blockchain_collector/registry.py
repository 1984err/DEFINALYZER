"""Load collector targets exported from the protocol registry.

This module deliberately validates collection coordinates only. It does not
resolve names, classify contracts, verify documentation, or interpret claims.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


EVM_ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")
MISSING_REGISTRY_VALUES = {
    "",
    "not documented",
    "unable to determine",
    "conflicting documentation",
}


@dataclass(frozen=True)
class RegistryTarget:
    """One registry row that can be passed to a raw evidence collector."""

    address: str
    chain: str
    source: str
    target_name: str | None = None
    role: str | None = None
    chain_id: int | None = None
    deployment_block: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RegistryTarget":
        address = _required_text(value, "address")
        chain = _required_text(value, "chain")
        source = _required_text(value, "source")

        if not EVM_ADDRESS_PATTERN.fullmatch(address):
            raise ValueError(
                f"Invalid EVM address {address!r}; expected 0x followed by 40 "
                "hexadecimal characters."
            )

        return cls(
            address=address,
            chain=chain,
            source=source,
            target_name=_optional_text(value, "target_name"),
            role=_optional_text(value, "role"),
            chain_id=_optional_non_negative_integer(value, "chain_id"),
            deployment_block=_optional_non_negative_integer(
                value, "deployment_block"
            ),
            metadata=_metadata(value),
        )


def load_registry_targets(path: str | Path) -> list[RegistryTarget]:
    """Load registry targets from a JSON list or ``{"targets": [...]}`` object.

    Input order and duplicate addresses are retained because two registry rows
    may intentionally describe different roles or provenance.
    """

    input_path = Path(path)

    try:
        document = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Registry input is not valid JSON: {input_path}: {exc.msg}"
        ) from exc

    rows = document.get("targets") if isinstance(document, dict) else document

    if not isinstance(rows, list):
        raise ValueError(
            "Registry input must be a JSON list or an object containing a "
            "'targets' list."
        )

    targets: list[RegistryTarget] = []

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Registry target at index {index} must be an object.")

        try:
            targets.append(RegistryTarget.from_mapping(row))
        except ValueError as exc:
            raise ValueError(f"Invalid registry target at index {index}: {exc}") from exc

    return targets


def _required_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)

    if not isinstance(item, str) or item.strip().lower() in MISSING_REGISTRY_VALUES:
        raise ValueError(f"{key!r} must contain a documented text value.")

    return item.strip()


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    item = value.get(key)

    if item is None:
        return None

    if not isinstance(item, str):
        raise ValueError(f"{key!r} must be text or null.")

    stripped = item.strip()
    return stripped or None


def _optional_non_negative_integer(
    value: Mapping[str, Any], key: str
) -> int | None:
    item = value.get(key)

    if item is None:
        return None

    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"{key!r} must be a non-negative integer or null.")

    return item


def _metadata(value: Mapping[str, Any]) -> Mapping[str, Any]:
    item = value.get("metadata", {})

    if not isinstance(item, dict):
        raise ValueError("'metadata' must be an object.")

    return dict(item)
