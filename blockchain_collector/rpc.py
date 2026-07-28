"""Minimal EVM JSON-RPC transport for raw evidence collection.

The transport records what a node returned. It does not decode contract data,
discover protocol behavior, or decide whether any claim is true.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import count
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ChainConfig:
    key: str
    name: str
    chain_id: int
    rpc_environment_variable: str


SUPPORTED_CHAINS: Mapping[str, ChainConfig] = {
    "ethereum": ChainConfig(
        key="ethereum",
        name="Ethereum Mainnet",
        chain_id=1,
        rpc_environment_variable="ETHEREUM_RPC_URL",
    ),
    "arbitrum": ChainConfig(
        key="arbitrum",
        name="Arbitrum One",
        chain_id=42161,
        rpc_environment_variable="ARBITRUM_RPC_URL",
    ),
    "base": ChainConfig(
        key="base",
        name="Base Mainnet",
        chain_id=8453,
        rpc_environment_variable="BASE_RPC_URL",
    ),
}


@dataclass(frozen=True)
class RpcEvidence:
    chain: str
    expected_chain_id: int
    request_id: int
    method: str
    params: Sequence[Any] | Mapping[str, Any]
    collected_at: str
    raw_response: Mapping[str, Any]
    result: Any = None
    error: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RpcTransportError(RuntimeError):
    """The node could not be reached or returned an invalid HTTP response."""


class ChainIdMismatchError(RuntimeError):
    """The configured endpoint belongs to a different EVM chain."""


class JsonRpcClient:
    """Synchronous JSON-RPC client with bounded retries and raw responses."""

    def __init__(
        self,
        chain: ChainConfig,
        rpc_url: str,
        *,
        timeout: float = 20.0,
        retries: int = 2,
        retry_delay: float = 0.5,
    ) -> None:
        if not rpc_url.strip():
            raise ValueError("RPC URL cannot be empty.")
        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero.")
        if retries < 0:
            raise ValueError("Retries cannot be negative.")
        if retry_delay < 0:
            raise ValueError("Retry delay cannot be negative.")

        self.chain = chain
        self._rpc_url = rpc_url.strip()
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self._request_ids = count(1)

    @classmethod
    def from_environment(
        cls,
        chain_key: str,
        **kwargs: Any,
    ) -> "JsonRpcClient":
        normalized_key = chain_key.strip().lower()

        try:
            chain = SUPPORTED_CHAINS[normalized_key]
        except KeyError as exc:
            supported = ", ".join(sorted(SUPPORTED_CHAINS))
            raise ValueError(
                f"Unsupported chain {chain_key!r}. Supported chains: {supported}."
            ) from exc

        rpc_url = os.environ.get(chain.rpc_environment_variable, "").strip()

        if not rpc_url:
            raise ValueError(
                f"Missing RPC endpoint. Set {chain.rpc_environment_variable}."
            )

        return cls(chain, rpc_url, **kwargs)

    def call(
        self,
        method: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> RpcEvidence:
        if not isinstance(method, str) or not method.strip():
            raise ValueError("RPC method must be non-empty text.")

        request_id = next(self._request_ids)
        request_params: Sequence[Any] | Mapping[str, Any] = (
            [] if params is None else params
        )
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method.strip(),
            "params": request_params,
        }
        response = self._post(payload)

        if response.get("jsonrpc") != "2.0":
            raise RpcTransportError("Node response is missing jsonrpc='2.0'.")
        if response.get("id") != request_id:
            raise RpcTransportError(
                f"Node response ID {response.get('id')!r} does not match "
                f"request ID {request_id}."
            )
        if "result" not in response and "error" not in response:
            raise RpcTransportError(
                "Node response contains neither a result nor an error."
            )

        return RpcEvidence(
            chain=self.chain.key,
            expected_chain_id=self.chain.chain_id,
            request_id=request_id,
            method=payload["method"],
            params=request_params,
            collected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            raw_response=response,
            result=response.get("result"),
            error=response.get("error"),
        )

    def validate_chain_id(self) -> RpcEvidence:
        evidence = self.call("eth_chainId")

        if evidence.error is not None:
            raise RpcTransportError(
                f"eth_chainId returned an RPC error: {evidence.error!r}"
            )

        try:
            actual_chain_id = int(evidence.result, 16)
        except (TypeError, ValueError) as exc:
            raise RpcTransportError(
                f"eth_chainId returned an invalid value: {evidence.result!r}"
            ) from exc

        if actual_chain_id != self.chain.chain_id:
            raise ChainIdMismatchError(
                f"RPC endpoint returned chain ID {actual_chain_id}; "
                f"{self.chain.name} requires {self.chain.chain_id}."
            )

        return evidence

    def _post(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(
            self._rpc_url,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    response_body = response.read()

                decoded = json.loads(response_body)

                if not isinstance(decoded, dict):
                    raise RpcTransportError(
                        "Node response must be a JSON object."
                    )

                return decoded
            except HTTPError as exc:
                last_error = exc

                if exc.code < 500:
                    break
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc

            if attempt < self.retries and self.retry_delay:
                time.sleep(self.retry_delay * (attempt + 1))

        raise RpcTransportError(
            f"RPC request failed after {self.retries + 1} attempt(s): "
            f"{last_error}"
        ) from last_error
