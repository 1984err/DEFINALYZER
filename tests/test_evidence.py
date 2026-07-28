import json
import tempfile
import unittest
from pathlib import Path

from blockchain_collector.evidence import (
    EvidenceBundle,
    EvidenceRecord,
    write_evidence_bundle,
)


class EvidenceWriterTests(unittest.TestCase):
    def test_writes_versioned_bundle(self):
        bundle = EvidenceBundle(
            job_name="sample-check",
            job_source="job.json",
            started_at="2026-07-28T00:00:00+00:00",
            completed_at="2026-07-28T00:00:01+00:00",
            records=[
                EvidenceRecord(
                    request_name="contract-code",
                    operation="get_code",
                    chain="ethereum",
                    status="collected",
                    evidence={"rpc": {"result": "0x1234"}},
                )
            ],
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            written = write_evidence_bundle(bundle, path)
            document = json.loads(written.read_text(encoding="utf-8"))

        self.assertEqual(document["evidence_schema_version"], 1)
        self.assertEqual(document["records"][0]["status"], "collected")

    def test_never_overwrites_existing_evidence(self):
        bundle = EvidenceBundle(
            job_name="sample-check",
            started_at="2026-07-28T00:00:00+00:00",
            completed_at="2026-07-28T00:00:01+00:00",
            records=[],
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text("original", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "not be overwritten"):
                write_evidence_bundle(bundle, path)

            self.assertEqual(path.read_text(encoding="utf-8"), "original")

    def test_failed_record_requires_error_details(self):
        with self.assertRaisesRegex(ValueError, "collection_error"):
            EvidenceRecord(
                request_name="logs",
                operation="get_logs",
                chain="base",
                status="failed",
            )


if __name__ == "__main__":
    unittest.main()
