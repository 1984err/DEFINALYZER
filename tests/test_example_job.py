import unittest
from pathlib import Path

from blockchain_collector.jobs import load_collection_job


class ExampleJobTests(unittest.TestCase):
    def test_weth_smoke_job_matches_current_schema(self):
        project_root = Path(__file__).resolve().parents[1]
        job = load_collection_job(
            project_root / "examples" / "ethereum_weth_smoke_job.json"
        )

        self.assertEqual(job.name, "ethereum-weth-smoke-test")
        self.assertEqual(len(job.requests), 3)
        self.assertTrue(
            all(request.chain == "ethereum" for request in job.requests)
        )
        self.assertTrue(
            all(request.target.chain_id == 1 for request in job.requests)
        )


if __name__ == "__main__":
    unittest.main()
