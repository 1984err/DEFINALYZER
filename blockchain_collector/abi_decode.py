"""Minimal ABI output decoding for supported standard read calls.

Decoding is a mechanical representation step. It does not attach meaning to a
value or decide whether that value supports a claim.
"""

from __future__ import annotations

from typing import Any, Sequence


def decode_outputs(raw_result: str, output_types: Sequence[str]) -> list[Any]:
    data = _hex_bytes(raw_result)

    if len(data) < 32 * len(output_types):
        raise ValueError("ABI result is shorter than its declared output words.")

    decoded: list[Any] = []

    for index, output_type in enumerate(output_types):
        word = data[index * 32 : (index + 1) * 32]

        if output_type in {"uint8", "uint256"}:
            decoded.append(str(int.from_bytes(word, byteorder="big")))
        elif output_type == "address":
            decoded.append("0x" + word[-20:].hex())
        elif output_type == "bool":
            integer = int.from_bytes(word, byteorder="big")

            if integer not in {0, 1}:
                raise ValueError(f"Invalid ABI boolean value {integer}.")

            decoded.append(bool(integer))
        elif output_type == "bytes32":
            decoded.append("0x" + word.hex())
        elif output_type == "string":
            decoded.append(_decode_dynamic_string(data, word))
        else:
            raise ValueError(f"Unsupported ABI output type {output_type!r}.")

    return decoded


def _hex_bytes(value: str) -> bytes:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError("ABI result must be 0x-prefixed hexadecimal data.")

    payload = value[2:]

    if len(payload) % 2 != 0:
        raise ValueError("ABI result must contain an even number of hex digits.")

    try:
        return bytes.fromhex(payload)
    except ValueError as exc:
        raise ValueError("ABI result contains non-hexadecimal characters.") from exc


def _decode_dynamic_string(data: bytes, offset_word: bytes) -> str:
    offset = int.from_bytes(offset_word, byteorder="big")

    if offset % 32 != 0 or offset + 32 > len(data):
        raise ValueError("ABI string offset is outside the result.")

    length = int.from_bytes(data[offset : offset + 32], byteorder="big")
    start = offset + 32
    end = start + length

    if end > len(data):
        raise ValueError("ABI string length exceeds the result.")

    try:
        return data[start:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("ABI string is not valid UTF-8.") from exc
