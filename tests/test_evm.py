import unittest
from unittest.mock import MagicMock

from blockchain_collector.evm import RawEvmCollector, block_identifier
from blockchain_collector.registry import RegistryTarget
from blockchain_collector.rpc import RpcEvidence, SUPPORTED_CHAINS


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"
HASH = "0x" + ("ab" * 32)
TOPIC = "0x" + ("cd" * 32)


def target(chain="ethereum"):
    return RegistryTarget(
        address=ADDRESS,
        chain=chain,
        source="protocol-registry.md",
        target_name="Core Contract",
        role="core",
    )


def collector(chain="ethereum"):
    client = MagicMock()
    client.chain = SUPPORTED_CHAINS[chain]
    client.call.side_effect = lambda method, params: RpcEvidence(
        chain=chain,
        expected_chain_id=client.chain.chain_id,
        request_id=1,
        method=method,
        params=params,
        collected_at="2026-07-28T00:00:00+00:00",
        raw_response={"jsonrpc": "2.0", "id": 1, "result": "0x"},
        result="0x",
    )
    return RawEvmCollector(client), client


class TargetCollectionTests(unittest.TestCase):
    def test_get_code_attaches_registry_provenance(self):
        instance, client = collector()

        evidence = instance.get_code(target(), block=123)

        client.call.assert_called_once_with(
            "eth_getCode",
            [ADDRESS, "0x7b"],
        )
        self.assertEqual(evidence.target["source"], "protocol-registry.md")
        self.assertEqual(evidence.target["role"], "core")

    def test_get_storage_preserves_explicit_slot(self):
        instance, client = collector()

        instance.get_storage_at(target(), "0x2", block="safe")

        client.call.assert_called_once_with(
            "eth_getStorageAt",
            [ADDRESS, "0x2", "safe"],
        )

    def test_call_sends_raw_calldata_without_decoding(self):
        instance, client = collector()

        instance.call(target(), "0x18160ddd", value=0)

        client.call.assert_called_once_with(
            "eth_call",
            [{"to": ADDRESS, "data": "0x18160ddd", "value": "0x0"}, "latest"],
        )

    def test_rejects_target_for_different_chain(self):
        instance, _ = collector("base")

        with self.assertRaisesRegex(ValueError, "does not match"):
            instance.get_balance(target("ethereum"))

    def test_accepts_documented_arbitrum_one_name(self):
        instance, client = collector("arbitrum")

        instance.get_balance(target("Arbitrum One"))

        client.call.assert_called_once_with(
            "eth_getBalance",
            [ADDRESS, "latest"],
        )


class GeneralCollectionTests(unittest.TestCase):
    def test_transaction_receipt_uses_hash(self):
        instance, client = collector()

        evidence = instance.get_transaction_receipt(HASH)

        client.call.assert_called_once_with("eth_getTransactionReceipt", [HASH])
        self.assertIsNone(evidence.target)

    def test_block_hash_selects_hash_rpc_method(self):
        instance, client = collector()

        instance.get_block(HASH, full_transactions=True)

        client.call.assert_called_once_with(
            "eth_getBlockByHash",
            [HASH, True],
        )

    def test_logs_preserve_filter_structure(self):
        instance, client = collector()

        instance.get_logs(
            from_block=100,
            to_block="latest",
            address=ADDRESS,
            topics=[TOPIC, None],
        )

        client.call.assert_called_once_with(
            "eth_getLogs",
            [
                {
                    "fromBlock": "0x64",
                    "toBlock": "latest",
                    "address": ADDRESS,
                    "topics": [TOPIC, None],
                }
            ],
        )

    def test_rejects_negative_block_number(self):
        with self.assertRaisesRegex(ValueError, "negative"):
            block_identifier(-1)


if __name__ == "__main__":
    unittest.main()
