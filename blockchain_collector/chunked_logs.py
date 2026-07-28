"""Bounded, auditable collection of EVM event-log ranges."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .evm import RawEvmCollector
from .registry import RegistryTarget


DEFAULT_LOG_CHUNK_SIZE = 2_000


@dataclass(frozen=True)
class ChunkedLogEvidence:
    from_block: int
    to_block: int
    chunk_size: int
    complete: bool
    chunks: Sequence[Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_block": self.from_block,
            "to_block": self.to_block,
            "chunk_size": self.chunk_size,
            "complete": self.complete,
            "chunks": [dict(chunk) for chunk in self.chunks],
        }


def collect_logs_chunked(
    collector: RawEvmCollector,
    target: RegistryTarget,
    *,
    from_block: int | str,
    to_block: int | str,
    topics: Sequence[str | Sequence[str] | None] | None = None,
    chunk_size: int = DEFAULT_LOG_CHUNK_SIZE,
) -> ChunkedLogEvidence:
    start = numeric_block(from_block, field_name="from_block")
    end = numeric_block(to_block, field_name="to_block")

    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int):
        raise ValueError("chunk_size must be a positive integer.")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if end < start:
        raise ValueError("to_block cannot be lower than from_block.")

    chunks: list[Mapping[str, Any]] = []
    complete = True
    chunk_start = start

    while chunk_start <= end:
        chunk_end = min(chunk_start + chunk_size - 1, end)

        try:
            collected = collector.get_logs(
                from_block=chunk_start,
                to_block=chunk_end,
                address=target.address,
                topics=topics,
            )
            rpc_error = collected.rpc.error

            if rpc_error is not None:
                complete = False

            chunks.append(
                {
                    "from_block": chunk_start,
                    "to_block": chunk_end,
                    "status": "collected" if rpc_error is None else "rpc_error",
                    "evidence": collected.to_dict(),
                }
            )
        except Exception as exc:
            complete = False
            chunks.append(
                {
                    "from_block": chunk_start,
                    "to_block": chunk_end,
                    "status": "collection_error",
                    "collection_error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                }
            )

        chunk_start = chunk_end + 1

    return ChunkedLogEvidence(
        from_block=start,
        to_block=end,
        chunk_size=chunk_size,
        complete=complete,
        chunks=chunks,
    )


def numeric_block(value: int | str, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} cannot be a boolean.")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative.")
        return value
    if isinstance(value, str) and value.startswith("0x"):
        try:
            converted = int(value, 16)
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must be a block number or hexadecimal quantity."
            ) from exc

        return converted

    raise ValueError(
        f"{field_name} must be a block number or hexadecimal quantity."
    )
