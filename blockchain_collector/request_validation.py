"""Operation-specific validation for collection-job parameters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


TRANSACTION_HASH_PATTERN = re.compile(r"^0x[0-9a-fA-F]{64}$")
ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")
HEX_QUANTITY_PATTERN = re.compile(r"^0x[0-9a-fA-F]+$")
HEX_DATA_PATTERN = re.compile(r"^0x(?:[0-9a-fA-F]{2})*$")
BLOCK_TAGS = {"earliest", "finalized", "latest", "pending", "safe"}
STANDARD_ARGUMENT_COUNTS = {
    "allowance": 2,
    "balanceOf": 1,
    "decimals": 0,
    "name": 0,
    "owner": 0,
    "symbol": 0,
    "totalSupply": 0,
}


@dataclass(frozen=True)
class ParameterRule:
    required: frozenset[str] = frozenset()
    optional: frozenset[str] = frozenset()


PARAMETER_RULES: Mapping[str, ParameterRule] = {
    "contract_snapshot": ParameterRule(
        optional=frozenset({"block", "include_owner_call"})
    ),
    "eip1967_slots": ParameterRule(optional=frozenset({"block"})),
    "erc20_snapshot": ParameterRule(
        optional=frozenset({"block", "balance_addresses"})
    ),
    "erc20_transfers": ParameterRule(
        required=frozenset({"from_block", "to_block"}),
        optional=frozenset(
            {"chunk_size", "from_address", "to_address"}
        ),
    ),
    "get_balance": ParameterRule(optional=frozenset({"block"})),
    "get_block": ParameterRule(
        required=frozenset({"block"}),
        optional=frozenset({"full_transactions"}),
    ),
    "get_code": ParameterRule(optional=frozenset({"block"})),
    "get_logs": ParameterRule(
        required=frozenset({"from_block", "to_block"}),
        optional=frozenset({"address", "topics"}),
    ),
    "get_logs_chunked": ParameterRule(
        required=frozenset({"from_block", "to_block"}),
        optional=frozenset({"chunk_size", "topics"}),
    ),
    "get_storage_at": ParameterRule(
        required=frozenset({"slot"}),
        optional=frozenset({"block"}),
    ),
    "get_transaction": ParameterRule(
        required=frozenset({"transaction_hash"})
    ),
    "get_transaction_receipt": ParameterRule(
        required=frozenset({"transaction_hash"})
    ),
    "raw_call": ParameterRule(
        required=frozenset({"data"}),
        optional=frozenset({"block", "value"}),
    ),
    "standard_call": ParameterRule(
        required=frozenset({"function"}),
        optional=frozenset({"arguments", "block"}),
    ),
}


def validate_operation_parameters(
    operation: str,
    parameters: Mapping[str, Any],
) -> None:
    rule = PARAMETER_RULES.get(operation)

    if rule is None:
        raise ValueError(f"No parameter rules exist for operation {operation!r}.")

    supplied = set(parameters)
    missing = sorted(rule.required - supplied)

    if missing:
        raise ValueError(
            f"Operation {operation!r} is missing required parameter(s): "
            f"{', '.join(missing)}."
        )

    allowed = rule.required | rule.optional
    unexpected = sorted(supplied - allowed)

    if unexpected:
        raise ValueError(
            f"Operation {operation!r} received unexpected parameter(s): "
            f"{', '.join(unexpected)}."
        )

    if operation in {"get_transaction", "get_transaction_receipt"}:
        _transaction_hash(parameters.get("transaction_hash"))

    if "block" in parameters:
        _block_identifier(parameters["block"], field_name="block")

    if operation == "get_storage_at":
        _quantity(parameters["slot"], field_name="slot")

    if operation == "raw_call":
        _hex_data(parameters["data"], field_name="data")

        if "value" in parameters:
            _quantity(parameters["value"], field_name="value")

    if operation == "get_block" and "full_transactions" in parameters:
        _boolean(parameters["full_transactions"], field_name="full_transactions")

    if operation == "contract_snapshot" and "include_owner_call" in parameters:
        _boolean(
            parameters["include_owner_call"],
            field_name="include_owner_call",
        )

    if operation == "erc20_snapshot" and "balance_addresses" in parameters:
        addresses = parameters["balance_addresses"]

        if not isinstance(addresses, list):
            raise ValueError("'balance_addresses' must be a list.")

        for address in addresses:
            _address(address, field_name="balance_addresses item")

    if operation == "standard_call":
        _standard_call(parameters)

    if operation in {"get_logs", "get_logs_chunked", "erc20_transfers"}:
        _log_parameters(operation, parameters)


def _transaction_hash(value: Any) -> None:
    if not isinstance(value, str) or not TRANSACTION_HASH_PATTERN.fullmatch(value):
        raise ValueError(
            "'transaction_hash' must be 0x followed by 64 hexadecimal "
            "characters."
        )


def _block_identifier(value: Any, *, field_name: str) -> None:
    if isinstance(value, bool):
        raise ValueError(f"'{field_name}' cannot be a boolean.")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"'{field_name}' cannot be negative.")
        return
    if isinstance(value, str):
        if (
            value in BLOCK_TAGS
            or HEX_QUANTITY_PATTERN.fullmatch(value)
            or TRANSACTION_HASH_PATTERN.fullmatch(value)
        ):
            return

    raise ValueError(
        f"'{field_name}' must be a non-negative block number, hexadecimal "
        "quantity, block hash, or standard block tag."
    )


def _numeric_block_or_latest(value: Any, *, field_name: str) -> None:
    if value == "latest":
        return
    if isinstance(value, bool):
        raise ValueError(f"'{field_name}' cannot be a boolean.")
    if isinstance(value, int) and value >= 0:
        return
    if isinstance(value, str) and HEX_QUANTITY_PATTERN.fullmatch(value):
        return

    raise ValueError(
        f"'{field_name}' must be a non-negative block number, hexadecimal "
        "quantity, or 'latest'."
    )


def _quantity(value: Any, *, field_name: str) -> None:
    if isinstance(value, bool):
        raise ValueError(f"'{field_name}' cannot be a boolean.")
    if isinstance(value, int) and value >= 0:
        return
    if isinstance(value, str) and HEX_QUANTITY_PATTERN.fullmatch(value):
        return

    raise ValueError(
        f"'{field_name}' must be a non-negative integer or hexadecimal quantity."
    )


def _hex_data(value: Any, *, field_name: str) -> None:
    if not isinstance(value, str) or not HEX_DATA_PATTERN.fullmatch(value):
        raise ValueError(
            f"'{field_name}' must be even-length 0x-prefixed hexadecimal data."
        )


def _boolean(value: Any, *, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"'{field_name}' must be a boolean.")


def _address(value: Any, *, field_name: str) -> None:
    if not isinstance(value, str) or not ADDRESS_PATTERN.fullmatch(value):
        raise ValueError(
            f"'{field_name}' must be 0x followed by 40 hexadecimal characters."
        )


def _standard_call(parameters: Mapping[str, Any]) -> None:
    function = parameters.get("function")

    if not isinstance(function, str) or function not in STANDARD_ARGUMENT_COUNTS:
        supported = ", ".join(sorted(STANDARD_ARGUMENT_COUNTS))
        raise ValueError(
            f"'function' must be one of the supported standard functions: "
            f"{supported}."
        )

    arguments = parameters.get("arguments", [])

    if not isinstance(arguments, list):
        raise ValueError("'arguments' must be a list.")

    expected = STANDARD_ARGUMENT_COUNTS[function]

    if len(arguments) != expected:
        raise ValueError(
            f"Standard function {function!r} requires {expected} argument(s); "
            f"received {len(arguments)}."
        )

    for argument in arguments:
        _address(argument, field_name=f"{function} argument")


def _log_parameters(operation: str, parameters: Mapping[str, Any]) -> None:
    if operation in {"get_logs_chunked", "erc20_transfers"}:
        _numeric_block_or_latest(
            parameters["from_block"],
            field_name="from_block",
        )
        _numeric_block_or_latest(
            parameters["to_block"],
            field_name="to_block",
        )
    else:
        _block_identifier(parameters["from_block"], field_name="from_block")
        _block_identifier(parameters["to_block"], field_name="to_block")

    if "chunk_size" in parameters:
        chunk_size = parameters["chunk_size"]

        if (
            isinstance(chunk_size, bool)
            or not isinstance(chunk_size, int)
            or chunk_size <= 0
        ):
            raise ValueError("'chunk_size' must be a positive integer.")

    for key in ("from_address", "to_address"):
        if key in parameters:
            _address(parameters[key], field_name=key)

    if "address" in parameters:
        addresses = parameters["address"]

        if isinstance(addresses, str):
            _address(addresses, field_name="address")
        elif isinstance(addresses, list) and addresses:
            for address in addresses:
                _address(address, field_name="address item")
        else:
            raise ValueError("'address' must be an address or non-empty list.")

    if "topics" in parameters:
        topics = parameters["topics"]

        if not isinstance(topics, list):
            raise ValueError("'topics' must be a list.")

        for topic in topics:
            _topic(topic)


def _topic(value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str):
        if TRANSACTION_HASH_PATTERN.fullmatch(value):
            return
        raise ValueError(
            "Each log topic must be a 32-byte hexadecimal value, null, or "
            "a non-empty list of alternatives."
        )
    if isinstance(value, list) and value:
        for alternative in value:
            if not isinstance(alternative, str) or not (
                TRANSACTION_HASH_PATTERN.fullmatch(alternative)
            ):
                raise ValueError(
                    "Each log topic alternative must be a 32-byte "
                    "hexadecimal value."
                )
        return

    raise ValueError(
        "Each log topic must be a 32-byte hexadecimal value, null, or "
        "a non-empty list of alternatives."
    )
