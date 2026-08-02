import json
import tempfile
import unittest
from pathlib import Path

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
