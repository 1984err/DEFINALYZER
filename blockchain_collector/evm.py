"""Raw EVM collection operations built on the JSON-RPC transport."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .registry import EVM_ADDRESS_PATTERN, RegistryTarget
from .rpc import JsonRpcClient, RpcEvidence


HEX_VALUE_PATTERN = re.compile(r"^0x[0-9a-fA-F]+$")
BLOCK_TAGS = {"earliest", "finalized", "latest", "pending", "safe"}
CHAIN_ALIASES: Mapping[str, set[str]] = {
    "ethereum": {"ethereum", "ethereum mainnet", "mainnet"},
    "arbitrum": {"arbitrum", "arbitrum one"},
    "base": {"base", "base mainnet"},
}


@dataclass(frozen=True)
class CollectedEvidence:
    """One raw RPC observation tied to its originating registry target."""

    target: Mapping[str, Any] | None
    rpc: RpcEvidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": dict(self.target) if self.target is not None else None,
            "rpc": self.rpc.to_dict(),
        }


class RawEvmCollector:
    """Construct standard EVM requests without interpreting their responses."""

    def __init__(self, client: JsonRpcClient) -> None:
        self.client = client

    def get_code(
        self,
        target: RegistryTarget,
        block: int | str = "latest",
    ) -> CollectedEvidence:
        return self._target_call(
            target,
            "eth_getCode",
            [target.address, block_identifier(block)],
        )

    def get_balance(
        self,
        target: RegistryTarget,
        block: int | str = "latest",
    ) -> CollectedEvidence:
        return self._target_call(
            target,
            "eth_getBalance",
            [target.address, block_identifier(block)],
        )

    def get_storage_at(
        self,
        target: RegistryTarget,
        slot: int | str,
        block: int | str = "latest",
    ) -> CollectedEvidence:
        return self._target_call(
            target,
            "eth_getStorageAt",
            [
                target.address,
                quantity(slot, field_name="storage slot"),
                block_identifier(block),
            ],
        )

    def call(
        self,
        target: RegistryTarget,
        data: str,
        block: int | str = "latest",
        *,
        value: int | str | None = None,
    ) -> CollectedEvidence:
        call_object: dict[str, str] = {
            "to": target.address,
            "data": hex_data(data, field_name="call data"),
        }

        if value is not None:
            call_object["value"] = quantity(value, field_name="call value")

        return self._target_call(
            target,
            "eth_call",
            [call_object, block_identifier(block)],
        )

    def get_transaction(self, transaction_hash: str) -> CollectedEvidence:
        return self._call(
            "eth_getTransactionByHash",
            [hash32(transaction_hash, field_name="transaction hash")],
        )

    def get_transaction_receipt(
        self, transaction_hash: str
    ) -> CollectedEvidence:
        return self._call(
            "eth_getTransactionReceipt",
            [hash32(transaction_hash, field_name="transaction hash")],
        )

    def get_block(
        self,
        block: int | str,
        *,
        full_transactions: bool = False,
    ) -> CollectedEvidence:
        if not isinstance(full_transactions, bool):
            raise ValueError("full_transactions must be a boolean.")

        if isinstance(block, str) and hash32_or_none(block):
            return self._call(
                "eth_getBlockByHash",
                [block, full_transactions],
            )

        return self._call(
            "eth_getBlockByNumber",
            [block_identifier(block), full_transactions],
        )

    def get_logs(
        self,
        *,
        from_block: int | str,
        to_block: int | str,
        address: str | Sequence[str] | None = None,
        topics: Sequence[str | Sequence[str] | None] | None = None,
    ) -> CollectedEvidence:
        log_filter: dict[str, Any] = {
            "fromBlock": block_identifier(from_block),
            "toBlock": block_identifier(to_block),
        }

        if address is not None:
            if isinstance(address, str):
                log_filter["address"] = evm_address(address)
            else:
                addresses = list(address)

                if not addresses:
                    raise ValueError("Log address list cannot be empty.")

                log_filter["address"] = [evm_address(item) for item in addresses]

        if topics is not None:
            log_filter["topics"] = validate_topics(topics)

        return self._call("eth_getLogs", [log_filter])

    def _target_call(
        self,
        target: RegistryTarget,
        method: str,
        params: Sequence[Any],
    ) -> CollectedEvidence:
        if target.chain_id is not None:
            chain_matches = target.chain_id == self.client.chain.chain_id
        else:
            aliases = CHAIN_ALIASES.get(
                self.client.chain.key, {self.client.chain.key}
            )
            chain_matches = target.chain.strip().lower() in aliases

        if not chain_matches:
            raise ValueError(
                f"Target chain {target.chain!r} does not match collector chain "
                f"{self.client.chain.key!r}."
            )

        return CollectedEvidence(
            target=asdict(target),
            rpc=self.client.call(method, params),
        )

    def _call(
        self,
        method: str,
        params: Sequence[Any],
    ) -> CollectedEvidence:
        return CollectedEvidence(
            target=None,
            rpc=self.client.call(method, params),
        )


def block_identifier(value: int | str) -> str:
    if isinstance(value, bool):
        raise ValueError("Block identifier cannot be a boolean.")
    if isinstance(value, int):
        return quantity(value, field_name="block number")
    if isinstance(value, str):
        stripped = value.strip()

        if stripped in BLOCK_TAGS or HEX_VALUE_PATTERN.fullmatch(stripped):
            return stripped

    raise ValueError(
        "Block identifier must be a non-negative integer, hexadecimal "
        "quantity, or standard block tag."
    )


def quantity(value: int | str, *, field_name: str) -> str:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} cannot be a boolean.")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative.")
        return hex(value)
    if isinstance(value, str) and HEX_VALUE_PATTERN.fullmatch(value.strip()):
        return value.strip()

    raise ValueError(
        f"{field_name} must be a non-negative integer or hexadecimal quantity."
    )


def evm_address(value: str) -> str:
    if not isinstance(value, str) or not EVM_ADDRESS_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid EVM address: {value!r}.")
    return value


def hash32(value: str, *, field_name: str) -> str:
    if not hash32_or_none(value):
        raise ValueError(
            f"{field_name} must be 0x followed by 64 hexadecimal characters."
        )
    return value


def hash32_or_none(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 66
        and value.startswith("0x")
        and all(character in "0123456789abcdefABCDEF" for character in value[2:])
    )


def hex_data(value: str, *, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("0x")
        or len(value) % 2 != 0
        or any(character not in "0123456789abcdefABCDEF" for character in value[2:])
    ):
        raise ValueError(f"{field_name} must be even-length 0x-prefixed hex data.")
    return value


def validate_topics(
    topics: Sequence[str | Sequence[str] | None],
) -> list[str | list[str] | None]:
    validated: list[str | list[str] | None] = []

    for topic in topics:
        if topic is None:
            validated.append(None)
        elif isinstance(topic, str):
            validated.append(hash32(topic, field_name="log topic"))
        else:
            alternatives = list(topic)

            if not alternatives:
                raise ValueError("Log topic alternatives cannot be empty.")

            validated.append(
                [hash32(item, field_name="log topic") for item in alternatives]
            )

    return validated
