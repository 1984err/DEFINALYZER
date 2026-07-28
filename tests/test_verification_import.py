import json
import tempfile
import unittest
from pathlib import Path

from blockchain_collector.verification_import import (
    import_verification_requests,
    load_verification_requests,
    main,
)


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


def valid_document():
    return {
        "schema_version": 1,
        "name": "token-verification",
        "requests": [
            {
                "id": "supply-snapshot",
                "claim": "The documented token supply is capped.",
                "why_verify": "Supply affects the tokenomics assessment.",
                "chain": "ethereum",
                "operation": "erc20_snapshot",
                "parameters": {"block": "latest"},
                "target": {
                    "target_name": "Protocol Token",
                    "role": "governance token",
                    "address": ADDRESS,
                    "chain": "Ethereum",
                    "chain_id": 1,
                    "source": "registry.md",
                },
            }
        ],
    }


class VerificationImportTests(unittest.TestCase):
    def test_converts_valid_request_and_preserves_claim_as_metadata(self):
        result = import_verification_requests(
            valid_document(),
            source="analysis.md",
        )

        self.assertIsNotNone(result.job)
        self.assertEqual(result.report["status"], "ready")
        self.assertEqual(result.report["ready_count"], 1)
        metadata = result.job_document["metadata"]["verification_requests"][0]
        self.assertEqual(metadata["id"], "supply-snapshot")
        self.assertIn("capped", metadata["claim"])
        self.assertEqual(
            result.job_document["requests"][0]["name"],
            "supply-snapshot",
        )

    def test_routes_unsupported_operation_to_manual_review(self):
        document = valid_document()
        document["requests"][0]["operation"] = "decide_if_claim_is_true"

        result = import_verification_requests(document, source="analysis.md")

        self.assertIsNone(result.job_document)
        self.assertEqual(result.report["status"], "manual_review")
        self.assertEqual(result.report["manual_review_count"], 1)
        self.assertIn(
            "Unsupported operation",
            result.report["requests"][0]["reason"],
        )

    def test_routes_missing_claim_context_to_manual_review(self):
        document = valid_document()
        del document["requests"][0]["why_verify"]

        result = import_verification_requests(document, source="analysis.md")

        self.assertIsNone(result.job_document)
        self.assertIn("why_verify", result.report["requests"][0]["reason"])

    def test_routes_schema_drift_to_manual_review(self):
        document = valid_document()
        document["requests"][0]["verdict"] = "true"

        result = import_verification_requests(document, source="analysis.md")

        self.assertIsNone(result.job_document)
        self.assertIn(
            "Unexpected verification request field",
            result.report["requests"][0]["reason"],
        )

    def test_keeps_valid_rows_when_another_row_needs_manual_review(self):
        document = valid_document()
        document["requests"].append(
            {
                "id": "unknown-chain",
                "claim": "A material claim.",
                "chain": "polygon",
                "operation": "contract_snapshot",
                "parameters": {},
            }
        )

        result = import_verification_requests(document, source="analysis.md")

        self.assertIsNotNone(result.job)
        self.assertEqual(result.report["status"], "partial")
        self.assertEqual(result.report["ready_count"], 1)
        self.assertEqual(result.report["manual_review_count"], 1)

    def test_loads_exact_fenced_block_from_markdown(self):
        payload = json.dumps(valid_document())
        markdown = (
            "# Verification Opportunities\n\n"
            "```definalyzer-verification\n"
            f"{payload}\n"
            "```\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "research.md"
            path.write_text(markdown, encoding="utf-8")
            document = load_verification_requests(path)

        self.assertEqual(document["name"], "token-verification")

    def test_rejects_markdown_without_machine_readable_block(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "research.md"
            path.write_text(
                "# Verification Opportunities\n\n| Claim | Method |\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "fenced"):
                load_verification_requests(path)

    def test_cli_writes_job_and_report_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "requests.json"
            job = root / "job.json"
            report = root / "report.json"
            source.write_text(json.dumps(valid_document()), encoding="utf-8")

            first_exit = main([str(source), str(job), str(report)])
            second_exit = main([str(source), str(job), str(report)])

            self.assertEqual(first_exit, 0)
            self.assertEqual(second_exit, 1)
            self.assertTrue(job.exists())
            self.assertTrue(report.exists())


if __name__ == "__main__":
    unittest.main()
