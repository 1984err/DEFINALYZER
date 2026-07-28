"""Operation-specific validation for collection-job parameters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


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
