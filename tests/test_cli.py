import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from blockchain_collector.cli import (
    EXIT_ERROR,
    EXIT_PARTIAL_FAILURE,
    EXIT_SUCCESS,
    main,
)
from blockchain_collector.evidence import EvidenceBundle, EvidenceRecord


def bundle(status="collected"):
    error = None
    evidence = {"rpc": {"result": "0x1"}}

    if status == "failed":
        error = {
            "stage": "collection",
            "type": "TimeoutError",
            "message": "node timed out",
        }
        evidence = None

    return EvidenceBundle(
        job_name="sample",
        started_at="2026-07-28T00:00:00+00:00",
        completed_at="2026-07-28T00:00:01+00:00",
        records=[
            EvidenceRecord(
                request_name="request-one",
                operation="get_code",
                chain="ethereum",
                status=status,
                evidence=evidence,
                collection_error=error,
            )
        ],
    )


class CliTests(unittest.TestCase):
    @patch("blockchain_collector.cli.execute_collection_job")
    @patch("blockchain_collector.cli.load_collection_job")
    def test_writes_successful_evidence(self, load_job, execute_job):
        load_job.return_value = object()
        execute_job.return_value = bundle()

        with tempfile.TemporaryDirectory() as directory:
            job_path = Path(directory) / "job.json"
            output_path = Path(directory) / "evidence.json"
            job_path.write_text("{}", encoding="utf-8")

            with redirect_stdout(StringIO()):
                exit_code = main([str(job_path), str(output_path)])

            document = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, EXIT_SUCCESS)
        self.assertEqual(document["job_name"], "sample")

    @patch("blockchain_collector.cli.execute_collection_job")
    @patch("blockchain_collector.cli.load_collection_job")
    def test_writes_bundle_before_reporting_partial_failure(
        self, load_job, execute_job
    ):
        load_job.return_value = object()
        execute_job.return_value = bundle("failed")

        with tempfile.TemporaryDirectory() as directory:
            job_path = Path(directory) / "job.json"
            output_path = Path(directory) / "evidence.json"
            job_path.write_text("{}", encoding="utf-8")

            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                exit_code = main([str(job_path), str(output_path)])

            output_exists = output_path.exists()

        self.assertEqual(exit_code, EXIT_PARTIAL_FAILURE)
        self.assertTrue(output_exists)

    @patch("blockchain_collector.cli.execute_collection_job")
    @patch("blockchain_collector.cli.load_collection_job")
    def test_refuses_to_overwrite_evidence(self, load_job, execute_job):
        load_job.return_value = object()
        execute_job.return_value = bundle()

        with tempfile.TemporaryDirectory() as directory:
            job_path = Path(directory) / "job.json"
            output_path = Path(directory) / "evidence.json"
            job_path.write_text("{}", encoding="utf-8")
            output_path.write_text("original", encoding="utf-8")

            with redirect_stderr(StringIO()):
                exit_code = main([str(job_path), str(output_path)])

            contents = output_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, EXIT_ERROR)
        self.assertEqual(contents, "original")

    @patch("blockchain_collector.cli.execute_collection_job")
    @patch("blockchain_collector.cli.load_collection_job")
    def test_partial_evidence_returns_warning_exit_code(
        self, load_job, execute_job
    ):
        load_job.return_value = object()
        execute_job.return_value = bundle("partial")

        with tempfile.TemporaryDirectory() as directory:
            job_path = Path(directory) / "job.json"
            output_path = Path(directory) / "evidence.json"
            job_path.write_text("{}", encoding="utf-8")

            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                exit_code = main([str(job_path), str(output_path)])

        self.assertEqual(exit_code, EXIT_PARTIAL_FAILURE)


if __name__ == "__main__":
    unittest.main()
