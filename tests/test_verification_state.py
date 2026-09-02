import json
import tempfile
import unittest
from pathlib import Path

from definalyzer.verification_state import verification_job_fingerprint


class VerificationStateTests(unittest.TestCase):
    def test_fingerprint_changes_with_executable_request_not_metadata(self):
        base = {
            "schema_version": 1,
            "name": "verification",
            "metadata": {"verification_source": "one-machine"},
            "requests": [
                {
                    "name": "check",
                    "chain": "ethereum",
                    "operation": "get_block",
                    "parameters": {"block": "latest", "full_transactions": False},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "job.json"
            path.write_text(json.dumps(base), encoding="utf-8")
            first = verification_job_fingerprint(path)
            base["metadata"]["verification_source"] = "another-machine"
            path.write_text(json.dumps(base), encoding="utf-8")
            metadata_changed = verification_job_fingerprint(path)
            base["requests"][0]["parameters"]["block"] = "safe"
            path.write_text(json.dumps(base), encoding="utf-8")
            request_changed = verification_job_fingerprint(path)

        self.assertEqual(first, metadata_changed)
        self.assertNotEqual(first, request_changed)


if __name__ == "__main__":
    unittest.main()
