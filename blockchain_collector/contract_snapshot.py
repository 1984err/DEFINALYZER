"""Point-in-time raw evidence snapshot for a contract address."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .evm import RawEvmCollector
from .proxy_slots import collect_eip1967_slots
from .registry import RegistryTarget
from .standard_calls import collect_standard_call


@dataclass(frozen=True)
class ContractSnapshotEvidence:
    block: int | str
    runtime_code: Mapping[str, Any]
    native_balance: Mapping[str, Any]
    eip1967_slots: Mapping[str, Any]
    owner_call: Mapping[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "block": self.block,
            "runtime_code": dict(self.runtime_code),
            "native_balance": dict(self.native_balance),
            "eip1967_slots": dict(self.eip1967_slots),
            "owner_call": (
                dict(self.owner_call) if self.owner_call is not None else None
            ),
        }


def collect_contract_snapshot(
    collector: RawEvmCollector,
    target: RegistryTarget,
    *,
    block: int | str = "latest",
    include_owner_call: bool = False,
) -> ContractSnapshotEvidence:
    if not isinstance(include_owner_call, bool):
        raise ValueError("include_owner_call must be a boolean.")

    runtime_code = collector.get_code(target, block=block).to_dict()
    native_balance = collector.get_balance(target, block=block).to_dict()
    proxy_slots = collect_eip1967_slots(
        collector,
        target,
        block=block,
    ).to_dict()
    owner_call = None

    if include_owner_call:
        owner_call = collect_standard_call(
            collector,
            target,
            function="owner",
            block=block,
        ).to_dict()

    return ContractSnapshotEvidence(
        block=block,
        runtime_code=runtime_code,
        native_balance=native_balance,
        eip1967_slots=proxy_slots,
        owner_call=owner_call,
    )
