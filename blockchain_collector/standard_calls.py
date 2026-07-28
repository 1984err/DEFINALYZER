"""Dependency-free encoding for a small set of standard EVM read calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .abi_decode import decode_outputs
from .evm import CollectedEvidence, RawEvmCollector, evm_address
from .registry import RegistryTarget


@dataclass(frozen=True)
class StandardFunction:
    signature: str
    selector: str
    argument_types: tuple[str, ...]
    output_types: tuple[str, ...]


STANDARD_FUNCTIONS: Mapping[str, StandardFunction] = {
    "totalSupply": StandardFunction(
        "totalSupply()", "0x18160ddd", (), ("uint256",)
    ),
    "balanceOf": StandardFunction(
        "balanceOf(address)", "0x70a08231", ("address",), ("uint256",)
    ),
    "allowance": StandardFunction(
        "allowance(address,address)",
        "0xdd62ed3e",
        ("address", "address"),
        ("uint256",),
    ),
    "owner": StandardFunction("owner()", "0x8da5cb5b", (), ("address",)),
    "decimals": StandardFunction("decimals()", "0x313ce567", (), ("uint8",)),
    "name": StandardFunction("name()", "0x06fdde03", (), ("string",)),
    "symbol": StandardFunction("symbol()", "0x95d89b41", (), ("string",)),
}


@dataclass(frozen=True)
class StandardCallEvidence:
    function: str
    signature: str
    arguments: Sequence[Any]
    output_types: Sequence[str]
    calldata: str
    collected: CollectedEvidence
    decoded_result: Sequence[Any] | None = None
    decode_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        document = self.collected.to_dict()
        document["standard_call"] = {
            "function": self.function,
            "signature": self.signature,
            "arguments": list(self.arguments),
            "output_types": list(self.output_types),
            "calldata": self.calldata,
            "decoded_result": (
                list(self.decoded_result)
                if self.decoded_result is not None
                else None
            ),
            "decode_error": self.decode_error,
        }
        return document


def collect_standard_call(
    collector: RawEvmCollector,
    target: RegistryTarget,
    *,
    function: str,
    arguments: Sequence[Any] | None = None,
    block: int | str = "latest",
) -> StandardCallEvidence:
    specification = STANDARD_FUNCTIONS.get(function)

    if specification is None:
        supported = ", ".join(sorted(STANDARD_FUNCTIONS))
        raise ValueError(
            f"Unsupported standard function {function!r}. Supported: {supported}."
        )

    supplied_arguments = list(arguments or [])

    if len(supplied_arguments) != len(specification.argument_types):
        raise ValueError(
            f"{specification.signature} requires "
            f"{len(specification.argument_types)} argument(s); "
            f"received {len(supplied_arguments)}."
        )

    encoded_arguments = "".join(
        _encode_argument(argument, argument_type)
        for argument, argument_type in zip(
            supplied_arguments,
            specification.argument_types,
        )
    )
    calldata = specification.selector + encoded_arguments
    collected = collector.call(target, calldata, block=block)
    decoded_result = None
    decode_error = None

    if collected.rpc.error is None:
        try:
            decoded_result = decode_outputs(
                collected.rpc.result,
                specification.output_types,
            )
        except ValueError as exc:
            decode_error = str(exc)

    return StandardCallEvidence(
        function=function,
        signature=specification.signature,
        arguments=supplied_arguments,
        output_types=specification.output_types,
        calldata=calldata,
        collected=collected,
        decoded_result=decoded_result,
        decode_error=decode_error,
    )


def _encode_argument(value: Any, argument_type: str) -> str:
    if argument_type == "address":
        address = evm_address(value)
        return address[2:].lower().rjust(64, "0")

    raise ValueError(f"Unsupported standard argument type {argument_type!r}.")
