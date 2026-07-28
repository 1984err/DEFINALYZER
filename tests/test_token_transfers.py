import unittest
from unittest.mock import MagicMock, patch

from blockchain_collector.chunked_logs import ChunkedLogEvidence
from blockchain_collector.registry import RegistryTarget
from blockchain_collector.token_transfers import (
    TRANSFER_TOPIC,
    collect_erc20_transfers,
    decode_transfer_log,
)


TOKEN = "0x1234567890abcdef1234567890abcdef12345678"
SENDER = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
RECIPIENT = "0x1111111111111111111111111111111111111111"


def target():
    return RegistryTarget(
        address=TOKEN,
        chain="Ethereum",
        source="protocol-registry.md",
    )


class TransferTests(unittest.TestCase):
    @patch("blockchain_collector.token_transfers.collect_logs_chunked")
    def test_builds_indexed_address_filters(self, collect_logs):
        collect_logs.return_value = ChunkedLogEvidence(1, 2, 2000, True, [])

        evidence = collect_erc20_transfers(
            MagicMock(),
            target(),
            from_block=1,
            to_block=2,
            from_address=SENDER,
            to_address=RECIPIENT,
        )

        topics = collect_logs.call_args.kwargs["topics"]
        self.assertEqual(topics[0], TRANSFER_TOPIC)
        self.assertTrue(topics[1].endswith(SENDER[2:]))
        self.assertTrue(topics[2].endswith(RECIPIENT[2:]))
        self.assertEqual(evidence.event_signature, "Transfer(address,address,uint256)")

    def test_decodes_transfer_fields_without_classification(self):
        log = {
            "topics": [
                TRANSFER_TOPIC,
                "0x" + SENDER[2:].rjust(64, "0"),
                "0x" + RECIPIENT[2:].rjust(64, "0"),
            ],
            "data": "0x" + (123).to_bytes(32, "big").hex(),
            "blockNumber": "0x10",
            "transactionHash": "0x" + ("ab" * 32),
            "logIndex": "0x2",
        }

        decoded = decode_transfer_log(log)

        self.assertEqual(decoded["from_address"], SENDER)
        self.assertEqual(decoded["to_address"], RECIPIENT)
        self.assertEqual(decoded["value"], "123")
        self.assertNotIn("burn", decoded)

    def test_rejects_non_transfer_topic(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            decode_transfer_log(
                {
                    "topics": [
                        "0x" + ("00" * 32),
                        "0x" + ("00" * 32),
                        "0x" + ("00" * 32),
                    ],
                    "data": "0x" + ("00" * 32),
                }
            )


if __name__ == "__main__":
    unittest.main()
