import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from blockchain_collector.evidence import EvidenceBundle, EvidenceRecord
from blockchain_collector.menu import _block_number, run_guided_menu


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


def answers(values):
    iterator = iter(values)
    return lambda prompt: next(iterator)


def successful_bundle(job):
    return EvidenceBundle(
        job_name=job.name,
        started_at="2026-07-28T00:00:00+00:00",
        completed_at="2026-07-28T00:00:01+00:00",
        records=[
            EvidenceRecord(
                request_name=job.requests[0].name,
                operation=job.requests[0].operation,
                chain=job.requests[0].chain,
                status="collected",
                evidence={"rpc": {"result": "0x"}},
            )
        ],
    )


class GuidedMenuTests(unittest.TestCase):
    @patch("blockchain_collector.menu.execute_collection_job")
    def test_builds_saves_and_executes_contract_job(self, execute_job):
        execute_job.side_effect = lambda job, **kwargs: successful_bundle(job)
        prompts = answers(
            [
                "1",
                "1",
                ADDRESS,
                "Core Contract",
                "controller",
                "protocol-registry.md",
                "My Contract Check",
                "y",
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            exit_code = run_guided_menu(
                input_fn=prompts,
                print_fn=lambda message: None,
                working_directory=directory,
            )
            job_path = Path(directory) / "jobs" / "my-contract-check.json"
            evidence_path = (
                Path(directory) / "evidence" / "my-contract-check.json"
            )
            document = json.loads(job_path.read_text(encoding="utf-8"))
            evidence_exists = evidence_path.exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(evidence_exists)
        self.assertEqual(document["requests"][0]["operation"], "contract_snapshot")
        self.assertTrue(
            document["requests"][0]["parameters"]["include_owner_call"]
        )

    @patch("blockchain_collector.menu.execute_collection_job")
    def test_builds_token_snapshot_with_balance_addresses(self, execute_job):
        execute_job.side_effect = lambda job, **kwargs: successful_bundle(job)
        treasury = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        prompts = answers(
            [
                "3",
                "2",
                ADDRESS,
                "Token",
                "",
                "registry.md",
                "Token Check",
                treasury,
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            exit_code = run_guided_menu(
                input_fn=prompts,
                print_fn=lambda message: None,
                working_directory=directory,
            )
            document = json.loads(
                (
                    Path(directory) / "jobs" / "token-check.json"
                ).read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        request = document["requests"][0]
        self.assertEqual(request["chain"], "base")
        self.assertEqual(request["target"]["chain_id"], 8453)
        self.assertEqual(
            request["parameters"]["balance_addresses"],
            [treasury],
        )

    @patch("blockchain_collector.menu.execute_collection_job")
    def test_refuses_to_overwrite_existing_job(self, execute_job):
        prompts = answers(
            [
                "1",
                "3",
                ADDRESS,
                "Proxy",
                "",
                "registry.md",
                "Existing",
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            jobs = Path(directory) / "jobs"
            jobs.mkdir()
            path = jobs / "existing.json"
            path.write_text("original", encoding="utf-8")
            messages = []
            exit_code = run_guided_menu(
                input_fn=prompts,
                print_fn=messages.append,
                working_directory=directory,
            )

        self.assertEqual(exit_code, 1)
        execute_job.assert_not_called()
        self.assertTrue(any("will not be overwritten" in item for item in messages))

    @patch("blockchain_collector.menu.execute_collection_job")
    def test_builds_chunked_transfer_history_job(self, execute_job):
        execute_job.side_effect = lambda job, **kwargs: successful_bundle(job)
        burn_address = "0x000000000000000000000000000000000000dead"
        prompts = answers(
            [
                "1",
                "4",
                ADDRESS,
                "Token",
                "governance token",
                "registry.md",
                "Burn Transfers",
                "19000000",
                "",
                "",
                burn_address,
                "",
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            exit_code = run_guided_menu(
                input_fn=prompts,
                print_fn=lambda message: None,
                working_directory=directory,
            )
            document = json.loads(
                (
                    Path(directory) / "jobs" / "burn-transfers.json"
                ).read_text(encoding="utf-8")
            )

        parameters = document["requests"][0]["parameters"]
        self.assertEqual(exit_code, 0)
        self.assertEqual(parameters["from_block"], 19000000)
        self.assertEqual(parameters["to_block"], "latest")
        self.assertEqual(parameters["to_address"], burn_address)
        self.assertEqual(parameters["chunk_size"], 2000)

    def test_parses_decimal_hex_and_latest_blocks(self):
        self.assertEqual(_block_number("123", allow_latest=False), 123)
        self.assertEqual(_block_number("0x7b", allow_latest=False), 123)
        self.assertEqual(
            _block_number("latest", allow_latest=True),
            "latest",
        )

        with self.assertRaisesRegex(ValueError, "decimal"):
            _block_number("latest", allow_latest=False)

    @patch("blockchain_collector.menu.execute_collection_job")
    def test_builds_readable_balance_of_call(self, execute_job):
        execute_job.side_effect = lambda job, **kwargs: successful_bundle(job)
        account = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        prompts = answers(
            [
                "1",
                "5",
                ADDRESS,
                "Token",
                "governance token",
                "registry.md",
                "Treasury Balance",
                "2",
                account,
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            exit_code = run_guided_menu(
                input_fn=prompts,
                print_fn=lambda message: None,
                working_directory=directory,
            )
            document = json.loads(
                (
                    Path(directory) / "jobs" / "treasury-balance.json"
                ).read_text(encoding="utf-8")
            )

        parameters = document["requests"][0]["parameters"]
        self.assertEqual(exit_code, 0)
        self.assertEqual(parameters["function"], "balanceOf")
        self.assertEqual(parameters["arguments"], [account])


if __name__ == "__main__":
    unittest.main()
