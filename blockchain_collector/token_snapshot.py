"""Point-in-time collection of standard ERC-20 read functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .evm import RawEvmCollector, evm_address
from .registry import RegistryTarget
from .standard_calls import collect_standard_call


@dataclass(frozen=True)
class TokenSnapshotEvidence:
    block: int | str
    calls: Mapping[str, Mapping[str, Any]]
    balances: Sequence[Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "standard": "ERC-20",
            "standard_source": "https://eips.ethereum.org/EIPS/eip-20",
            "block": self.block,
            "calls": {name: dict(value) for name, value in self.calls.items()},
            "balances": [dict(balance) for balance in self.balances],
        }


def collect_erc20_snapshot(
    collector: RawEvmCollector,
    target: RegistryTarget,
    *,
    block: int | str = "latest",
    balance_addresses: Sequence[str] | None = None,
) -> TokenSnapshotEvidence:
    calls: dict[str, Mapping[str, Any]] = {}

    for function in ("name", "symbol", "decimals", "totalSupply"):
        calls[function] = collect_standard_call(
            collector,
            target,
            function=function,
            block=block,
        ).to_dict()

    balances: list[Mapping[str, Any]] = []

    for address in balance_addresses or []:
        normalized_address = evm_address(address)
        evidence = collect_standard_call(
            collector,
            target,
            function="balanceOf",
            arguments=[normalized_address],
            block=block,
        )
        balances.append(
            {
                "address": normalized_address,
                "evidence": evidence.to_dict(),
            }
        )

    return TokenSnapshotEvidence(
        block=block,
        calls=calls,
        balances=balances,
    )
