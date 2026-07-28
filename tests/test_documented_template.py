import unittest
from pathlib import Path

from blockchain_collector.jobs import load_collection_job


class DocumentedTemplateTests(unittest.TestCase):
    def test_full_template_matches_current_job_schema(self):
        project_root = Path(__file__).resolve().parents[1]
        job = load_collection_job(
            project_root / "examples" / "collection_job_template.json"
        )

        self.assertEqual(len(job.requests), 3)
        self.assertEqual(
            [request.operation for request in job.requests],
            ["contract_snapshot", "erc20_snapshot", "erc20_transfers"],
        )


if __name__ == "__main__":
    unittest.main()
