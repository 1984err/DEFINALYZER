import json
import os
import unittest
from unittest.mock import MagicMock, patch

from blockchain_collector.rpc import (
    SUPPORTED_CHAINS,
    ChainIdMismatchError,
    JsonRpcClient,
)


def mock_http_response(document):
    response = MagicMock()
    response.read.return_value = json.dumps(document).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


class SupportedChainTests(unittest.TestCase):
    def test_mainnet_chain_ids(self) -> None:
        self.assertEqual(SUPPORTED_CHAINS["ethereum"].chain_id, 1)
        self.assertEqual(SUPPORTED_CHAINS["arbitrum"].chain_id, 42161)
        self.assertEqual(SUPPORTED_CHAINS["base"].chain_id, 8453)

    def test_loads_endpoint_from_chain_specific_environment_variable(self) -> None:
        with patch.dict(
            os.environ,
            {"ARBITRUM_RPC_URL": "https://rpc.example"},
            clear=True,
        ):
            client = JsonRpcClient.from_environment("Arbitrum")

        self.assertEqual(client.chain.chain_id, 42161)


class JsonRpcClientTests(unittest.TestCase):
    @patch("blockchain_collector.rpc.urlopen")
    def test_records_raw_result_and_exact_request(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = mock_http_response(
            {"jsonrpc": "2.0", "id": 1, "result": "0x1234"}
        )
        client = JsonRpcClient(
            SUPPORTED_CHAINS["ethereum"],
            "https://rpc.example",
            retries=0,
        )

        evidence = client.call(
            "eth_getCode",
            ["0x1234567890abcdef1234567890abcdef12345678", "latest"],
        )

        self.assertEqual(evidence.result, "0x1234")
        self.assertEqual(evidence.error, None)
        self.assertEqual(evidence.method, "eth_getCode")
        self.assertEqual(evidence.params[1], "latest")
        self.assertEqual(
            evidence.raw_response,
            {"jsonrpc": "2.0", "id": 1, "result": "0x1234"},
        )

    @patch("blockchain_collector.rpc.urlopen")
    def test_records_rpc_error_without_interpreting_it(self, mocked_urlopen) -> None:
        rpc_error = {"code": -32602, "message": "invalid argument"}
        mocked_urlopen.return_value = mock_http_response(
            {"jsonrpc": "2.0", "id": 1, "error": rpc_error}
        )
        client = JsonRpcClient(
            SUPPORTED_CHAINS["base"],
            "https://rpc.example",
            retries=0,
        )

        evidence = client.call("eth_getStorageAt", ["0x0", "0x0", "latest"])

        self.assertEqual(evidence.error, rpc_error)
        self.assertIsNone(evidence.result)

    @patch("blockchain_collector.rpc.urlopen")
    def test_validates_endpoint_chain_id(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = mock_http_response(
            {"jsonrpc": "2.0", "id": 1, "result": "0x1"}
        )
        client = JsonRpcClient(
            SUPPORTED_CHAINS["ethereum"],
            "https://rpc.example",
            retries=0,
        )

        evidence = client.validate_chain_id()

        self.assertEqual(evidence.result, "0x1")

    @patch("blockchain_collector.rpc.urlopen")
    def test_rejects_endpoint_for_wrong_chain(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = mock_http_response(
            {"jsonrpc": "2.0", "id": 1, "result": "0x2105"}
        )
        client = JsonRpcClient(
            SUPPORTED_CHAINS["ethereum"],
            "https://rpc.example",
            retries=0,
        )

        with self.assertRaises(ChainIdMismatchError):
            client.validate_chain_id()


if __name__ == "__main__":
    unittest.main()
