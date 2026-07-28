import unittest
from unittest.mock import MagicMock

from blockchain_collector.chunked_logs import collect_logs_chunked
from blockchain_collector.evm import CollectedEvidence
from blockchain_collector.registry import RegistryTarget
from blockchain_collector.rpc import RpcEvidence


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


def target():
    return RegistryTarget(
        address=ADDRESS,
        chain="Ethereum",
        source="protocol-registry.md",
    )


def log_evidence(from_block, to_block, error=None):
    response = {"jsonrpc": "2.0", "id": 1}

    if error is None:
        response["result"] = []
    else:
        response["error"] = error

    return CollectedEvidence(
        target=None,
        rpc=RpcEvidence(
            chain="ethereum",
            expected_chain_id=1,
            request_id=1,
            method="eth_getLogs",
            params=[],
            collected_at="2026-07-28T00:00:00+00:00",
            raw_response=response,
            result=[] if error is None else None,
            error=error,
        ),
    )


class ChunkedLogTests(unittest.TestCase):
    def test_splits_range_without_gaps_or_overlap(self):
        collector = MagicMock()
        collector.get_logs.side_effect = (
            lambda from_block, to_block, address, topics: log_evidence(
                from_block, to_block
            )
        )

        evidence = collect_logs_chunked(
            collector,
            target(),
            from_block=100,
            to_block=350,
            chunk_size=100,
        )

        ranges = [
            (chunk["from_block"], chunk["to_block"])
            for chunk in evidence.chunks
        ]
        self.assertEqual(ranges, [(100, 199), (200, 299), (300, 350)])
        self.assertTrue(evidence.complete)

    def test_records_failed_chunk_and_continues(self):
        collector = MagicMock()
        call_number = 0

        def get_logs(from_block, to_block, address, topics):
            nonlocal call_number
            call_number += 1

            if call_number == 2:
                raise TimeoutError("node timed out")

            return log_evidence(from_block, to_block)

        collector.get_logs.side_effect = get_logs

        evidence = collect_logs_chunked(
            collector,
            target(),
            from_block="0x64",
            to_block="0x15e",
            chunk_size=100,
        )

        self.assertFalse(evidence.complete)
        self.assertEqual(len(evidence.chunks), 3)
        self.assertEqual(evidence.chunks[1]["status"], "collection_error")
        self.assertEqual(evidence.chunks[2]["status"], "collected")

    def test_rpc_error_marks_range_incomplete(self):
        collector = MagicMock()
        collector.get_logs.return_value = log_evidence(
            1,
            2,
            error={"code": -32005, "message": "limit exceeded"},
        )

        evidence = collect_logs_chunked(
            collector,
            target(),
            from_block=1,
            to_block=2,
        )

        self.assertFalse(evidence.complete)
        self.assertEqual(evidence.chunks[0]["status"], "rpc_error")

    def test_rejects_reversed_range(self):
        with self.assertRaisesRegex(ValueError, "lower"):
            collect_logs_chunked(
                MagicMock(),
                target(),
                from_block=10,
                to_block=9,
            )


if __name__ == "__main__":
    unittest.main()
