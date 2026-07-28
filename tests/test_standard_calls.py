import unittest
from unittest.mock import MagicMock

from blockchain_collector.evm import CollectedEvidence
from blockchain_collector.registry import RegistryTarget
from blockchain_collector.rpc import RpcEvidence
from blockchain_collector.standard_calls import collect_standard_call


TOKEN = "0x1234567890abcdef1234567890abcdef12345678"
ACCOUNT = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"


def registry_target():
    return RegistryTarget(
        address=TOKEN,
        chain="Ethereum",
        chain_id=1,
        source="protocol-registry.md",
    )


def raw_evidence():
    encoded_one = "0x" + (1).to_bytes(32, "big").hex()
    return CollectedEvidence(
        target={"address": TOKEN},
        rpc=RpcEvidence(
            chain="ethereum",
            expected_chain_id=1,
            request_id=1,
            method="eth_call",
            params=[],
            collected_at="2026-07-28T00:00:00+00:00",
            raw_response={"jsonrpc": "2.0", "id": 1, "result": encoded_one},
            result=encoded_one,
        ),
    )


class StandardCallTests(unittest.TestCase):
    def test_total_supply_uses_known_selector(self):
        collector = MagicMock()
        collector.call.return_value = raw_evidence()

        evidence = collect_standard_call(
            collector,
            registry_target(),
            function="totalSupply",
            block="0x100",
        )

        collector.call.assert_called_once_with(
            registry_target(),
            "0x18160ddd",
            block="0x100",
        )
        self.assertEqual(evidence.signature, "totalSupply()")
        self.assertEqual(evidence.output_types, ("uint256",))
        self.assertEqual(evidence.decoded_result, ["1"])

    def test_balance_of_encodes_address_as_32_byte_word(self):
        collector = MagicMock()
        collector.call.return_value = raw_evidence()

        evidence = collect_standard_call(
            collector,
            registry_target(),
            function="balanceOf",
            arguments=[ACCOUNT],
        )

        expected = "0x70a08231" + ACCOUNT[2:].lower().rjust(64, "0")
        self.assertEqual(evidence.calldata, expected)

    def test_rejects_wrong_argument_count(self):
        collector = MagicMock()

        with self.assertRaisesRegex(ValueError, "requires 1 argument"):
            collect_standard_call(
                collector,
                registry_target(),
                function="balanceOf",
            )

    def test_rejects_unknown_function(self):
        collector = MagicMock()

        with self.assertRaisesRegex(ValueError, "Unsupported standard function"):
            collect_standard_call(
                collector,
                registry_target(),
                function="mint",
            )

    def test_preserves_raw_evidence_when_decoding_fails(self):
        collector = MagicMock()
        broken = raw_evidence()
        broken = CollectedEvidence(
            target=broken.target,
            rpc=RpcEvidence(
                chain="ethereum",
                expected_chain_id=1,
                request_id=1,
                method="eth_call",
                params=[],
                collected_at="2026-07-28T00:00:00+00:00",
                raw_response={"jsonrpc": "2.0", "id": 1, "result": "0x01"},
                result="0x01",
            ),
        )
        collector.call.return_value = broken

        evidence = collect_standard_call(
            collector,
            registry_target(),
            function="totalSupply",
        )

        self.assertIsNone(evidence.decoded_result)
        self.assertIn("shorter", evidence.decode_error)
        self.assertEqual(evidence.collected.rpc.result, "0x01")


if __name__ == "__main__":
    unittest.main()
