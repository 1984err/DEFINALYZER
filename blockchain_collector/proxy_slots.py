"""Raw collection of standardized ERC-1967 proxy storage slots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .evm import CollectedEvidence, RawEvmCollector
from .registry import RegistryTarget


EIP1967_SLOTS: Mapping[str, str] = {
    "implementation": (
        "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    ),
    "admin": (
        "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
    ),
    "beacon": (
        "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
    ),
}
EIP1967_SOURCE = "https://eips.ethereum.org/EIPS/eip-1967"


@dataclass(frozen=True)
class ProxySlotEvidence:
    standard: str
    standard_source: str
    block: int | str
    slots: Mapping[str, Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "standard": self.standard,
            "standard_source": self.standard_source,
            "block": self.block,
            "slots": {name: dict(value) for name, value in self.slots.items()},
        }


def collect_eip1967_slots(
    collector: RawEvmCollector,
    target: RegistryTarget,
    *,
    block: int | str = "latest",
) -> ProxySlotEvidence:
    slots: dict[str, Mapping[str, Any]] = {}

    for name, slot in EIP1967_SLOTS.items():
        collected = collector.get_storage_at(target, slot, block=block)
        slots[name] = _slot_document(slot, collected)

    return ProxySlotEvidence(
        standard="ERC-1967",
        standard_source=EIP1967_SOURCE,
        block=block,
        slots=slots,
    )


def _slot_document(
    slot: str,
    collected: CollectedEvidence,
) -> Mapping[str, Any]:
    raw_value = collected.rpc.result
    decoded_address = None
    decode_error = None

    if collected.rpc.error is None:
        try:
            decoded_address = address_from_storage_word(raw_value)
        except ValueError as exc:
            decode_error = str(exc)

    return {
        "slot": slot,
        "decoded_address": decoded_address,
        "decode_error": decode_error,
        "evidence": collected.to_dict(),
    }


def address_from_storage_word(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 66
        or not value.startswith("0x")
    ):
        raise ValueError("Storage result must be a 32-byte hexadecimal word.")

    try:
        bytes.fromhex(value[2:])
    except ValueError as exc:
        raise ValueError(
            "Storage result contains non-hexadecimal characters."
        ) from exc

    return "0x" + value[-40:].lower()
