import unittest
from unittest.mock import MagicMock, patch

from blockchain_collector.contract_snapshot import collect_contract_snapshot
from blockchain_collector.registry import RegistryTarget


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


def target():
    return RegistryTarget(
        address=ADDRESS,
        chain="Ethereum",
        source="protocol-registry.md",
    )


class SerializableEvidence:
    def __init__(self, label):
        self.label = label

    def to_dict(self):
        return {"label": self.label}


class ContractSnapshotTests(unittest.TestCase):
    @patch("blockchain_collector.contract_snapshot.collect_standard_call")
    @patch("blockchain_collector.contract_snapshot.collect_eip1967_slots")
    def test_collects_components_at_one_block(self, proxy_slots, standard_call):
        collector = MagicMock()
        collector.get_code.return_value = SerializableEvidence("code")
        collector.get_balance.return_value = SerializableEvidence("balance")
        proxy_slots.return_value = SerializableEvidence("slots")
        standard_call.return_value = SerializableEvidence("owner")

        evidence = collect_contract_snapshot(
            collector,
            target(),
            block="0x100",
            include_owner_call=True,
        )

        collector.get_code.assert_called_once_with(target(), block="0x100")
        collector.get_balance.assert_called_once_with(target(), block="0x100")
        proxy_slots.assert_called_once_with(
            collector,
            target(),
            block="0x100",
        )
        standard_call.assert_called_once_with(
            collector,
            target(),
            function="owner",
            block="0x100",
        )
        self.assertEqual(evidence.owner_call, {"label": "owner"})

    @patch("blockchain_collector.contract_snapshot.collect_eip1967_slots")
    def test_owner_call_is_opt_in(self, proxy_slots):
        collector = MagicMock()
        collector.get_code.return_value = SerializableEvidence("code")
        collector.get_balance.return_value = SerializableEvidence("balance")
        proxy_slots.return_value = SerializableEvidence("slots")

        evidence = collect_contract_snapshot(collector, target())

        self.assertIsNone(evidence.owner_call)

    def test_rejects_non_boolean_owner_option(self):
        with self.assertRaisesRegex(ValueError, "boolean"):
            collect_contract_snapshot(
                MagicMock(),
                target(),
                include_owner_call="yes",
            )


if __name__ == "__main__":
    unittest.main()
