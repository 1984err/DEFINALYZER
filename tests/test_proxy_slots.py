import unittest
from unittest.mock import MagicMock

from blockchain_collector.evm import CollectedEvidence
from blockchain_collector.proxy_slots import (
    EIP1967_SLOTS,
    address_from_storage_word,
    collect_eip1967_slots,
)
from blockchain_collector.registry import RegistryTarget
from blockchain_collector.rpc import RpcEvidence


PROXY = "0x1234567890abcdef1234567890abcdef12345678"
IMPLEMENTATION = "abcdefabcdefabcdefabcdefabcdefabcdefabcd"


def target():
    return RegistryTarget(
        address=PROXY,
        chain="Ethereum",
        source="protocol-registry.md",
    )


def storage_evidence(slot):
    result = "0x" + ("00" * 12) + IMPLEMENTATION
    return CollectedEvidence(
        target={"address": PROXY},
        rpc=RpcEvidence(
            chain="ethereum",
            expected_chain_id=1,
            request_id=1,
            method="eth_getStorageAt",
            params=[PROXY, slot, "0x100"],
            collected_at="2026-07-28T00:00:00+00:00",
            raw_response={"jsonrpc": "2.0", "id": 1, "result": result},
            result=result,
        ),
    )


class ProxySlotTests(unittest.TestCase):
    def test_collects_all_standard_slots_at_same_block(self):
        collector = MagicMock()
        collector.get_storage_at.side_effect = (
            lambda registry_target, slot, block: storage_evidence(slot)
        )

        evidence = collect_eip1967_slots(
            collector,
            target(),
            block="0x100",
        )

        self.assertEqual(collector.get_storage_at.call_count, 3)
        self.assertEqual(set(evidence.slots), set(EIP1967_SLOTS))
        self.assertEqual(
            evidence.slots["implementation"]["decoded_address"],
            "0x" + IMPLEMENTATION,
        )
        self.assertTrue(
            all(
                call.kwargs["block"] == "0x100"
                for call in collector.get_storage_at.call_args_list
            )
        )

    def test_decodes_last_twenty_bytes_without_classification(self):
        word = "0x" + ("00" * 12) + IMPLEMENTATION

        self.assertEqual(
            address_from_storage_word(word),
            "0x" + IMPLEMENTATION,
        )

    def test_rejects_invalid_storage_word(self):
        with self.assertRaisesRegex(ValueError, "32-byte"):
            address_from_storage_word("0x01")


if __name__ == "__main__":
    unittest.main()
