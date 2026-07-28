import tempfile
import unittest
from pathlib import Path

from blockchain_collector.evidence import EvidenceBundle, EvidenceRecord
from blockchain_collector.summary import (
    render_evidence_summary,
    write_evidence_summary,
)


class EvidenceSummaryTests(unittest.TestCase):
    def test_renders_snapshot_status_and_decoded_standard_call(self):
        bundle = EvidenceBundle(
            job_name="token-check",
            started_at="2026-07-28T00:00:00+00:00",
            completed_at="2026-07-28T00:00:01+00:00",
            chain_snapshots={
                "ethereum": {
                    "rpc": {
                        "result": {
                            "number": "0x100",
                            "hash": "0x" + ("ab" * 32),
                        }
                    }
                }
            },
            records=[
                EvidenceRecord(
                    request_name="supply",
                    operation="standard_call",
                    chain="ethereum",
                    status="collected",
                    evidence={
                        "standard_call": {
                            "signature": "totalSupply()",
                            "decoded_result": ["123"],
                            "decode_error": None,
                        }
                    },
                )
            ],
        )

        summary = render_evidence_summary(bundle)

        self.assertIn("block `0x100`", summary)
        self.assertIn("| supply | ethereum | standard_call | collected |", summary)
        self.assertIn("totalSupply(): `['123']`", summary)
        self.assertIn("does not confirm or deny", summary)

    def test_renders_partial_transfer_warning_and_counts_logs(self):
        bundle = EvidenceBundle(
            job_name="transfers",
            started_at="start",
            completed_at="end",
            records=[
                EvidenceRecord(
                    request_name="history",
                    operation="erc20_transfers",
                    chain="base",
                    status="partial",
                    evidence={
                        "logs": {
                            "complete": False,
                            "chunks": [
                                {
                                    "evidence": {
                                        "rpc": {"result": [{}, {}]}
                                    }
                                },
                                {"status": "collection_error"},
                            ],
                        }
                    },
                )
            ],
        )

        summary = render_evidence_summary(bundle)

        self.assertIn("Raw logs returned: `2`", summary)
        self.assertIn("incomplete evidence", summary)

    def test_summary_writer_never_overwrites(self):
        bundle = EvidenceBundle(
            job_name="check",
            started_at="start",
            completed_at="end",
            records=[],
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.md"
            write_evidence_summary(bundle, path)

            with self.assertRaisesRegex(FileExistsError, "not be overwritten"):
                write_evidence_summary(bundle, path)


if __name__ == "__main__":
    unittest.main()
