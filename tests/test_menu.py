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
    def test_selects_supported_target_from_project_registry(self, execute_job):
        execute_job.side_effect = lambda job, **kwargs: successful_bundle(job)
        prompts = answers(["3", "1", "3", "Pool Proxy Slots"])

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            project = output / "projects" / "example"
            registry = output / "registries" / "example"
            project.mkdir(parents=True)
            registry.mkdir(parents=True)
            (registry / "registry.json").write_text(
                json.dumps(
                    {
                        "addresses": [
                            {
                                "name": "POOL",
                                "component_type": "Pool",
                                "role": "Lending pool",
                                "address": ADDRESS,
                                "chain": "Ethereum",
                                "chain_id": 1,
                                "status": "published_current",
                                "source": "official-address-book.sol",
                                "provenance": "official_registry",
                            }
                        ],
                        "tokens": [],
                    }
                ),
                encoding="utf-8",
            )
            exit_code = run_guided_menu(
                input_fn=prompts,
                print_fn=lambda message: None,
                working_directory=project,
            )
            document = json.loads(
                (project / "jobs" / "pool-proxy-slots.json").read_text(
                    encoding="utf-8"
                )
            )

        request = document["requests"][0]
        self.assertEqual(exit_code, 0)
        self.assertEqual(request["operation"], "eip1967_slots")
        self.assertEqual(request["target"]["target_name"], "POOL")
        self.assertEqual(request["target"]["source"], "official-address-book.sol")

    @patch("blockchain_collector.menu.execute_collection_job")
    def test_builds_saves_and_executes_contract_job(self, execute_job):
        execute_job.side_effect = lambda job, **kwargs: successful_bundle(job)
        prompts = answers(
            [
                "1",
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
            summary_exists = (
                Path(directory) / "evidence" / "my-contract-check.md"
            ).exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(evidence_exists)
        self.assertTrue(summary_exists)
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
                "1",
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

    @patch("blockchain_collector.menu.execute_collection_job")
    def test_builds_transaction_and_receipt_requests(self, execute_job):
        execute_job.side_effect = lambda job, **kwargs: EvidenceBundle(
            job_name=job.name,
            started_at="2026-07-28T00:00:00+00:00",
            completed_at="2026-07-28T00:00:01+00:00",
            records=[
                EvidenceRecord(
                    request_name=request.name,
                    operation=request.operation,
                    chain=request.chain,
                    status="collected",
                    evidence={"rpc": {"result": {}}},
                )
                for request in job.requests
            ],
        )
        transaction_hash = "0x" + ("ab" * 32)
        prompts = answers(
            [
                "1",
                "2",
                "6",
                transaction_hash,
                "deployment-docs.md",
                "Deployment Transaction",
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
                    Path(directory) / "jobs" / "deployment-transaction.json"
                ).read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [request["operation"] for request in document["requests"]],
            ["get_transaction", "get_transaction_receipt"],
        )
        self.assertTrue(
            all(
                request["parameters"]["transaction_hash"] == transaction_hash
                for request in document["requests"]
            )
        )
        self.assertEqual(
            document["metadata"]["transaction_source"],
            "deployment-docs.md",
        )

    @patch("blockchain_collector.menu.execute_collection_job")
    def test_rejects_malformed_transaction_hash_before_writing(self, execute_job):
        prompts = answers(
            [
                "1",
                "1",
                "6",
                "0x1234",
            ]
        )
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            exit_code = run_guided_menu(
                input_fn=prompts,
                print_fn=messages.append,
                working_directory=directory,
            )
            jobs_exist = (Path(directory) / "jobs").exists()

        self.assertEqual(exit_code, 1)
        self.assertFalse(jobs_exist)
        execute_job.assert_not_called()
        self.assertTrue(any("64 hexadecimal" in item for item in messages))

    @patch("blockchain_collector.menu.execute_collection_job")
    def test_imports_and_runs_structured_verification_file(self, execute_job):
        execute_job.side_effect = lambda job, **kwargs: successful_bundle(job)
        request_document = {
            "schema_version": 1,
            "name": "source-name",
            "requests": [
                {
                    "id": "proxy-slots",
                    "claim": "A material proxy-related claim.",
                    "why_verify": "It could change the trust assessment.",
                    "chain": "ethereum",
                    "operation": "eip1967_slots",
                    "parameters": {"block": "latest"},
                    "target": {
                        "target_name": "Core Proxy",
                        "role": "proxy",
                        "address": ADDRESS,
                        "chain": "Ethereum",
                        "chain_id": 1,
                        "source": "registry.md",
                    },
                }
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "research.md"
            source_path.write_text(
                "# Verification\n\n```definalyzer-verification\n"
                + json.dumps(request_document)
                + "\n```\n",
                encoding="utf-8",
            )
            exit_code = run_guided_menu(
                input_fn=answers(["2", "research.md", "Imported Check"]),
                print_fn=lambda message: None,
                working_directory=root,
            )

            job_exists = (root / "jobs" / "imported-check.json").exists()
            report_exists = (
                root / "evidence" / "imported-check-import-report.json"
            ).exists()
            evidence_exists = (
                root / "evidence" / "imported-check.json"
            ).exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(job_exists)
        self.assertTrue(report_exists)
        self.assertTrue(evidence_exists)


if __name__ == "__main__":
    unittest.main()
