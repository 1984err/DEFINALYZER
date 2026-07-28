import unittest
from unittest.mock import MagicMock, patch

from blockchain_collector.registry import RegistryTarget
from blockchain_collector.token_snapshot import collect_erc20_snapshot


TOKEN = "0x1234567890abcdef1234567890abcdef12345678"
TREASURY = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"


def target():
    return RegistryTarget(
        address=TOKEN,
        chain="Ethereum",
        source="protocol-registry.md",
    )


class FakeStandardEvidence:
    def __init__(self, function, arguments):
        self.function = function
        self.arguments = arguments

    def to_dict(self):
        return {
            "standard_call": {
                "function": self.function,
                "arguments": self.arguments,
            }
        }


class TokenSnapshotTests(unittest.TestCase):
    @patch("blockchain_collector.token_snapshot.collect_standard_call")
    def test_collects_metadata_supply_and_requested_balances(self, standard_call):
        standard_call.side_effect = (
            lambda collector, registry_target, function, block, arguments=None:
            FakeStandardEvidence(function, arguments or [])
        )

        evidence = collect_erc20_snapshot(
            MagicMock(),
            target(),
            block="0x100",
            balance_addresses=[TREASURY],
        )

        self.assertEqual(
            list(evidence.calls),
            ["name", "symbol", "decimals", "totalSupply"],
        )
        self.assertEqual(evidence.block, "0x100")
        self.assertEqual(evidence.balances[0]["address"], TREASURY)
        self.assertEqual(standard_call.call_count, 5)
        self.assertTrue(
            all(call.kwargs["block"] == "0x100" for call in standard_call.call_args_list)
        )

    def test_rejects_invalid_balance_address_before_collection(self):
        with self.assertRaisesRegex(ValueError, "Invalid EVM address"):
            collect_erc20_snapshot(
                MagicMock(),
                target(),
                balance_addresses=["not-an-address"],
            )


if __name__ == "__main__":
    unittest.main()
