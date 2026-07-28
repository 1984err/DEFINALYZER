"""ERC-20 Transfer event collection with mechanical field decoding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .chunked_logs import ChunkedLogEvidence, collect_logs_chunked
from .evm import RawEvmCollector, evm_address
from .registry import RegistryTarget


TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa"
    "952ba7f163c4a11628f55a4df523b3ef"
)
ERC20_SOURCE = "https://eips.ethereum.org/EIPS/eip-20"


@dataclass(frozen=True)
class TransferEvidence:
    event_signature: str
    standard_source: str
    from_address: str | None
    to_address: str | None
    logs: ChunkedLogEvidence

    def to_dict(self) -> dict[str, Any]:
        document = {
            "event_signature": self.event_signature,
            "standard_source": self.standard_source,
            "filter": {
                "from_address": self.from_address,
                "to_address": self.to_address,
            },
            "logs": self.logs.to_dict(),
        }

        for chunk in document["logs"]["chunks"]:
            evidence = chunk.get("evidence")
            raw_logs = (
                evidence.get("rpc", {}).get("result")
                if isinstance(evidence, dict)
                else None
            )

            if isinstance(raw_logs, list):
                chunk["decoded_logs"] = [
                    _decode_with_error(raw_log) for raw_log in raw_logs
                ]

        return document


def collect_erc20_transfers(
    collector: RawEvmCollector,
    target: RegistryTarget,
    *,
    from_block: int | str,
    to_block: int | str,
    from_address: str | None = None,
    to_address: str | None = None,
    chunk_size: int = 2_000,
) -> TransferEvidence:
    normalized_from = (
        evm_address(from_address) if from_address is not None else None
    )
    normalized_to = evm_address(to_address) if to_address is not None else None
    topics: Sequence[str | None] = [
        TRANSFER_TOPIC,
        _address_topic(normalized_from) if normalized_from else None,
        _address_topic(normalized_to) if normalized_to else None,
    ]
    logs = collect_logs_chunked(
        collector,
        target,
        from_block=from_block,
        to_block=to_block,
        topics=topics,
        chunk_size=chunk_size,
    )

    return TransferEvidence(
        event_signature="Transfer(address,address,uint256)",
        standard_source=ERC20_SOURCE,
        from_address=normalized_from,
        to_address=normalized_to,
        logs=logs,
    )


def decode_transfer_log(log: Mapping[str, Any]) -> Mapping[str, Any]:
    topics = log.get("topics")
    data = log.get("data")

    if not isinstance(topics, list) or len(topics) < 3:
        raise ValueError("Transfer log must contain three topics.")
    if topics[0].lower() != TRANSFER_TOPIC:
        raise ValueError("Log topic does not match the ERC-20 Transfer event.")

    return {
        "from_address": _address_from_topic(topics[1]),
        "to_address": _address_from_topic(topics[2]),
        "value": str(_uint256_word(data, field_name="Transfer data")),
        "block_number": log.get("blockNumber"),
        "transaction_hash": log.get("transactionHash"),
        "log_index": log.get("logIndex"),
    }


def _decode_with_error(log: Any) -> Mapping[str, Any]:
    if not isinstance(log, dict):
        return {"decoded": None, "decode_error": "Log must be an object."}

    try:
        return {"decoded": decode_transfer_log(log), "decode_error": None}
    except (TypeError, ValueError) as exc:
        return {"decoded": None, "decode_error": str(exc)}


def _address_topic(address: str) -> str:
    return "0x" + address[2:].lower().rjust(64, "0")


def _address_from_topic(topic: Any) -> str:
    _uint256_word(topic, field_name="address topic")
    return "0x" + topic[-40:].lower()


def _uint256_word(value: Any, *, field_name: str) -> int:
    if not isinstance(value, str) or len(value) != 66 or not value.startswith("0x"):
        raise ValueError(f"{field_name} must be a 32-byte hexadecimal word.")

    try:
        return int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field_name} contains non-hexadecimal characters.") from exc
