import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from definalyzer.evaluation import (
    generate_evaluation_proposals,
    pending_proposals,
    review_proposal,
)
from definalyzer.providers import ProviderResponse
from definalyzer.workspace import WorkspaceManager


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


class FakeEvaluator:
    name = "fake"

    def generate(self, prompt, *, working_directory):
        return ProviderResponse(
            text=json.dumps(
                {
                    "proposed_status": "inconclusive",
                    "reason": "The slot evidence does not establish governance authority.",
                    "evidence_scope": "One proxy implementation slot.",
                }
            ),
            provider="fake",
            command=("fake",),
        )


class EvaluationTests(unittest.TestCase):
    def test_ignores_evidence_from_an_outdated_planned_job(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            workspace.verification_page_path.write_text(
                "# Example — Verification\n\n"
                "### VR-GOV-001 — Governance\n\n"
                "| Field | Value |\n|---|---|\n"
                "| Claim | Governance controls the proxy. |\n"
                f"| Registry target | Proxy — {ADDRESS} |\n",
                encoding="utf-8",
            )
            job = workspace.jobs_directory / "verification-plan.json"
            job.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "name": "example-verification",
                        "metadata": {},
                        "requests": [
                            {
                                "name": "vr-gov-001",
                                "chain": "ethereum",
                                "operation": "get_code",
                                "parameters": {"block": "latest"},
                                "target": {
                                    "target_name": "Proxy",
                                    "role": "Core proxy",
                                    "address": ADDRESS,
                                    "chain": "Ethereum",
                                    "chain_id": 1,
                                    "source": "official docs",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stale = workspace.evidence_directory / "old.json"
            stale.write_text(
                json.dumps(
                    {
                        "job_name": "example-verification",
                        "job_metadata": {
                            "verification_job_sha256": "0" * 64,
                        },
                        "records": [
                            {
                                "request_name": "vr-gov-001",
                                "status": "collected",
                                "evidence": {"target": {"address": ADDRESS}},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            provider = Mock()

            result = generate_evaluation_proposals(
                workspace=workspace,
                provider=provider,
            )

        self.assertEqual(result.proposals, ())
        self.assertEqual(result.ignored_stale_evidence, (stale,))
        provider.generate.assert_not_called()

    def test_queues_and_human_approves_proposal(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            page = (
                workspace.vault_root
                / "Verification"
                / "Example"
                / "Index.md"
            )
            page.write_text(
                "# Example — Verification\n\n"
                "## Summary\n\n"
                "| Status | Count |\n|---|---:|\n"
                "| Pending | 1 |\n"
                "| Evidence collected | 0 |\n"
                "| Manual review | 0 |\n"
                "| Supported | 0 |\n"
                "| Contradicted | 0 |\n"
                "| Inconclusive | 0 |\n\n"
                "### VR-GOV-001 — Governance authority\n\n"
                "| Field | Value |\n|---|---|\n"
                "| Status | Pending |\n"
                "| Claim | Governance controls the proxy. |\n"
                f"| Registry target | Proxy — {ADDRESS} |\n"
                "| Evidence | Not collected |\n"
                "| Last checked | Never |\n"
                "| Result | Not evaluated |\n",
                encoding="utf-8",
            )
            evidence = workspace.evidence_directory / "slots.json"
            evidence.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "request_name": "slots",
                                "operation": "eip1967_slots",
                                "chain": "ethereum",
                                "status": "collected",
                                "evidence": {
                                    "target": {"address": ADDRESS},
                                    "implementation": ADDRESS,
                                },
                            }
                        ],
                        "chain_snapshots": {},
                    }
                ),
                encoding="utf-8",
            )
            generated = generate_evaluation_proposals(
                workspace=workspace,
                provider=FakeEvaluator(),
            )
            queued = pending_proposals(workspace)
            reviewed = review_proposal(
                workspace=workspace,
                proposal_path=queued[0],
                action="approve",
            )
            updated = page.read_text(encoding="utf-8")

        self.assertEqual(len(generated.proposals), 1)
        self.assertEqual(len(queued), 1)
        self.assertTrue(reviewed.verification_updated)
        self.assertIn("| Status | Inconclusive |", updated)
        self.assertIn("| Inconclusive | 1 |", updated)
        self.assertIn("slot evidence", updated)

    def test_supported_proposal_uses_confirmed_display_status(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            page = workspace.verification_page_path
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(
                "# Example — Verification\n\n## Summary\n\n"
                "| Status | Count |\n|---|---:|\n| Pending | 1 |\n"
                "| Evidence collected | 0 |\n| Confirmed | 0 |\n"
                "| Contradicted | 0 |\n| Inconclusive | 0 |\n"
                "| Public evidence unavailable | 0 |\n\n"
                "### VR-GOV-001 — Governance\n\n| Field | Value |\n|---|---|\n"
                "| Status | Pending |\n| Evidence | Not collected |\n"
                "| Last checked | Never |\n| Result | Not evaluated |\n",
                encoding="utf-8",
            )

            from definalyzer.evaluation import _apply_verification_decision

            _apply_verification_decision(
                page=page,
                verification_id="VR-GOV-001",
                status="supported",
                result="Collected evidence supports the scoped claim.",
                evidence_file="evidence.json",
            )
            updated = page.read_text(encoding="utf-8")

        self.assertIn("| Status | Confirmed |", updated)
        self.assertIn("| Confirmed | 1 |", updated)

    def test_unmatched_evidence_is_not_sent_to_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            page = workspace.verification_page_path
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(
                "# Example — Verification\n\n"
                "### VR-GOV-001 — Governance\n\n"
                "| Field | Value |\n|---|---|\n"
                "| Claim | A claim. |\n"
                "| Registry target | None |\n",
                encoding="utf-8",
            )
            evidence = workspace.evidence_directory / "other.json"
            evidence.write_text(
                json.dumps({"records": [], "chain_snapshots": {}}),
                encoding="utf-8",
            )
            result = generate_evaluation_proposals(
                workspace=workspace,
                provider=FakeEvaluator(),
            )

        self.assertEqual(result.proposals, ())
        self.assertEqual(len(result.unmatched_evidence), 1)


if __name__ == "__main__":
    unittest.main()
