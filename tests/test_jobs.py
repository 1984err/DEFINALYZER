import json
import tempfile
import unittest
from pathlib import Path

from blockchain_collector.jobs import CollectionJob, load_collection_job


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


def valid_job():
    return {
        "schema_version": 1,
        "name": "sample-protocol-check",
        "metadata": {"research_page": "tokenomics.md"},
        "requests": [
            {
                "name": "token-code",
                "chain": "ethereum",
                "operation": "get_code",
                "parameters": {"block": "latest"},
                "target": {
                    "address": ADDRESS,
                    "chain": "Ethereum",
                    "source": "protocol-registry.md",
                    "role": "governance token",
                },
            },
            {
                "name": "deployment-receipt",
                "chain": "ethereum",
                "operation": "get_transaction_receipt",
                "parameters": {"transaction_hash": "0x" + ("ab" * 32)},
            },
        ],
    }


class CollectionJobTests(unittest.TestCase):
    def test_loads_versioned_job_and_registry_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "job.json"
            path.write_text(json.dumps(valid_job()), encoding="utf-8")

            job = load_collection_job(path)

        self.assertEqual(job.schema_version, 1)
        self.assertEqual(len(job.requests), 2)
        self.assertEqual(job.requests[0].target.source, "protocol-registry.md")

    def test_requires_target_for_address_operation(self):
        document = valid_job()
        del document["requests"][0]["target"]

        with self.assertRaisesRegex(ValueError, "requires a registry target"):
            CollectionJob.from_mapping(document)

    def test_rejects_duplicate_request_names(self):
        document = valid_job()
        document["requests"][1]["name"] = "token-code"

        with self.assertRaisesRegex(ValueError, "Duplicate request name"):
            CollectionJob.from_mapping(document)

    def test_rejects_unknown_schema_version(self):
        document = valid_job()
        document["schema_version"] = 2

        with self.assertRaisesRegex(ValueError, "Unsupported schema_version"):
            CollectionJob.from_mapping(document)

    def test_rejects_missing_operation_parameter_before_execution(self):
        document = valid_job()
        document["requests"][1]["parameters"] = {}

        with self.assertRaisesRegex(ValueError, "transaction_hash"):
            CollectionJob.from_mapping(document)

    def test_rejects_registry_target_for_different_chain(self):
        document = valid_job()
        document["requests"][0]["target"]["chain"] = "Base"
        document["requests"][0]["target"]["chain_id"] = 8453

        with self.assertRaisesRegex(ValueError, "does not match"):
            CollectionJob.from_mapping(document)

    def test_accepts_documented_chain_alias(self):
        document = valid_job()
        document["requests"][0]["chain"] = "arbitrum"
        document["requests"][0]["target"]["chain"] = "Arbitrum One"
        document["requests"][0]["target"]["chain_id"] = 42161

        job = CollectionJob.from_mapping(document)

        self.assertEqual(job.requests[0].chain, "arbitrum")


if __name__ == "__main__":
    unittest.main()
