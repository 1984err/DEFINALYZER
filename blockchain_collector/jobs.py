"""Versioned collection-job input for the raw EVM collector."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .registry import RegistryTarget
from .request_validation import validate_operation_parameters
from .rpc import SUPPORTED_CHAINS


JOB_SCHEMA_VERSION = 1
REQUEST_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SUPPORTED_OPERATIONS = {
    "get_balance",
    "contract_snapshot",
    "get_block",
    "get_code",
    "get_logs",
    "get_logs_chunked",
    "get_storage_at",
    "get_transaction",
    "get_transaction_receipt",
    "eip1967_slots",
    "erc20_transfers",
    "erc20_snapshot",
    "raw_call",
    "standard_call",
}
TARGET_OPERATIONS = {
    "contract_snapshot",
    "eip1967_slots",
    "erc20_transfers",
    "erc20_snapshot",
    "get_balance",
    "get_code",
    "get_logs_chunked",
    "get_storage_at",
    "raw_call",
    "standard_call",
}


@dataclass(frozen=True)
class CollectionRequest:
    name: str
    chain: str
    operation: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    target: RegistryTarget | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CollectionRequest":
        name = _required_text(value, "name")

        if not REQUEST_NAME_PATTERN.fullmatch(name):
            raise ValueError(
                "'name' must be 1-128 characters using letters, numbers, "
                "periods, underscores, or hyphens."
            )

        chain = _required_text(value, "chain").lower()

        if chain not in SUPPORTED_CHAINS:
            supported = ", ".join(sorted(SUPPORTED_CHAINS))
            raise ValueError(
                f"Unsupported chain {chain!r}. Supported chains: {supported}."
            )

        operation = _required_text(value, "operation")

        if operation not in SUPPORTED_OPERATIONS:
            supported = ", ".join(sorted(SUPPORTED_OPERATIONS))
            raise ValueError(
                f"Unsupported operation {operation!r}. "
                f"Supported operations: {supported}."
            )

        parameters = value.get("parameters", {})

        if not isinstance(parameters, dict):
            raise ValueError("'parameters' must be an object.")

        validate_operation_parameters(operation, parameters)

        target_value = value.get("target")
        target = None

        if target_value is not None:
            if not isinstance(target_value, dict):
                raise ValueError("'target' must be an object or null.")

            target = RegistryTarget.from_mapping(target_value)

        if operation in TARGET_OPERATIONS and target is None:
            raise ValueError(f"Operation {operation!r} requires a registry target.")

        if operation not in TARGET_OPERATIONS and target is not None:
            raise ValueError(
                f"Operation {operation!r} does not accept a registry target."
            )

        return cls(
            name=name,
            chain=chain,
            operation=operation,
            parameters=dict(parameters),
            target=target,
        )


@dataclass(frozen=True)
class CollectionJob:
    name: str
    requests: tuple[CollectionRequest, ...]
    schema_version: int = JOB_SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CollectionJob":
        schema_version = value.get("schema_version")

        if schema_version != JOB_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema_version {schema_version!r}; "
                f"expected {JOB_SCHEMA_VERSION}."
            )

        name = _required_text(value, "name")

        if not REQUEST_NAME_PATTERN.fullmatch(name):
            raise ValueError(
                "Job 'name' must be 1-128 characters using letters, numbers, "
                "periods, underscores, or hyphens."
            )

        rows = value.get("requests")

        if not isinstance(rows, list) or not rows:
            raise ValueError("'requests' must be a non-empty list.")

        requests: list[CollectionRequest] = []
        request_names: set[str] = set()

        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"Request at index {index} must be an object.")

            try:
                request = CollectionRequest.from_mapping(row)
            except ValueError as exc:
                raise ValueError(f"Invalid request at index {index}: {exc}") from exc

            if request.name in request_names:
                raise ValueError(f"Duplicate request name {request.name!r}.")

            request_names.add(request.name)
            requests.append(request)

        metadata = value.get("metadata", {})

        if not isinstance(metadata, dict):
            raise ValueError("'metadata' must be an object.")

        return cls(
            name=name,
            requests=tuple(requests),
            schema_version=schema_version,
            metadata=dict(metadata),
        )


def load_collection_job(path: str | Path) -> CollectionJob:
    input_path = Path(path)

    try:
        document = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Collection job is not valid JSON: {input_path}: {exc.msg}"
        ) from exc

    if not isinstance(document, dict):
        raise ValueError("Collection job must be a JSON object.")

    return CollectionJob.from_mapping(document)


def _required_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)

    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{key!r} must be non-empty text.")

    return item.strip()
