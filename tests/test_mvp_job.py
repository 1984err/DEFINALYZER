import unittest
from pathlib import Path

from blockchain_collector.jobs import load_collection_job


class MvpJobTests(unittest.TestCase):
    def test_weth_mvp_job_matches_current_schema(self):
        project_root = Path(__file__).resolve().parents[1]
        job = load_collection_job(
            project_root / "examples" / "ethereum_weth_mvp_job.json"
        )

        self.assertEqual(
            [request.operation for request in job.requests],
            ["erc20_snapshot", "contract_snapshot"],
        )


if __name__ == "__main__":
    unittest.main()
