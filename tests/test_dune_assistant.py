import json
import tempfile
import unittest
from pathlib import Path

from definalyzer.dune_assistant import (
    _validate_response,
    list_dune_candidates,
    run_dune_dialogue,
)
from definalyzer.providers import ProviderResponse
from definalyzer.workspace import WorkspaceManager


class RecordingProvider:
    name = "fake"

    def __init__(self):
        self.prompts = []

    def generate(self, prompt, *, working_directory):
        self.prompts.append(prompt)
        version = len(self.prompts)
        return ProviderResponse(
            text=(
                "## Assumptions\n- Address must be confirmed.\n"
                "## SQL\n```sql\nSELECT "
                f"{version} AS query_version\n```\n"
                "## Expected output\nOne row.\n"
                "## Limitations\nThis does not verify the claim."
            ),
            provider="fake",
            command=("fake",),
        )


class DuneAssistantTests(unittest.TestCase):
    def _workspace(self, directory):
        manager = WorkspaceManager(Path(directory) / "output")
        workspace = manager.create_project(name="Example")
        workspace.verification_page_path.write_text(
            "# Example — Verification\n\n## Fees and Value Accrual\n\n"
            "### VR-FEE-001 — Historical fees\n\n"
            "| Field | Value |\n|---|---|\n| Status | Pending |\n"
            "| Claim | Fees are routed to the treasury. |\n"
            "| Claim type | On-chain state/events |\n"
            "| Evidence availability | Public |\n"
            "| Recommended method | Dune candidate |\n"
            "| Optional Dune query | Available |\n"
            "| Check route | Manual |\n"
            "| How to check | Aggregate fee transfers. |\n"
            "| Likely source | Ethereum event data. |\n"
            "| Evidence required | Transfers by recipient and date. |\n",
            encoding="utf-8",
        )
        state = workspace.project_root / "verification-planning"
        state.mkdir(parents=True)
        catalog = {
            "schema_version": 1,
            "entity": "Example",
            "entries": [
                {
                    "id": "VR-FEE-001",
                    "title": "Historical fees",
                    "claim": "Fees are routed to the treasury.",
                    "claim_type": "On-chain state/events",
                    "evidence_availability": "Public",
                    "recommended_method": "Dune candidate",
                    "dune_eligible": True,
                    "check_route": "Manual",
                    "status": "Pending",
                    "research_source": "Revenue-Model.md",
                    "likely_source": "Ethereum event data.",
                    "evidence_required": "Transfers by recipient and date.",
                }
            ],
        }
        (state / "verification-catalog.json").write_text(
            json.dumps(catalog), encoding="utf-8"
        )
        return workspace

    def test_creates_and_revises_persistent_read_only_dialogue(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory)
            provider = RecordingProvider()

            first = run_dune_dialogue(
                workspace=workspace,
                provider=provider,
                verification_id="VR-FEE-001",
            )
            second = run_dune_dialogue(
                workspace=workspace,
                provider=provider,
                verification_id="VR-FEE-001",
                feedback_type="error",
                feedback="Line 2: table does not exist",
            )
            session = json.loads(second.session_path.read_text(encoding="utf-8"))
            page = workspace.verification_page_path.read_text(encoding="utf-8")
            note = second.note_path.read_text(encoding="utf-8")

        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)
        self.assertEqual(len(session["turns"]), 2)
        self.assertFalse(session["execution_performed"])
        self.assertFalse(session["verification_status_changed"])
        self.assertIn("table does not exist", provider.prompts[-1])
        self.assertIn("| Dune dialogue |", page)
        self.assertEqual(page.count("| Dune dialogue |"), 1)
        self.assertIn("## Version 2", note)

    def test_lists_only_explicit_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory)
            candidates = list_dune_candidates(workspace)

        self.assertEqual([row.verification_id for row in candidates], ["VR-FEE-001"])

    def test_rejects_mutating_or_multiple_sql(self):
        with self.assertRaisesRegex(ValueError, "read-only"):
            _validate_response("```sql\nDELETE FROM ethereum.transactions\n```")
        with self.assertRaisesRegex(ValueError, "one SQL statement"):
            _validate_response("```sql\nSELECT 1; SELECT 2\n```")

    def test_stale_page_eligibility_stops_before_provider_call(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory)
            page = workspace.verification_page_path
            page.write_text(
                page.read_text(encoding="utf-8").replace(
                    "| Optional Dune query | Available |\n", ""
                ),
                encoding="utf-8",
            )
            provider = RecordingProvider()

            with self.assertRaisesRegex(ValueError, "no longer Dune-eligible"):
                run_dune_dialogue(
                    workspace=workspace,
                    provider=provider,
                    verification_id="VR-FEE-001",
                )

        self.assertEqual(provider.prompts, [])


if __name__ == "__main__":
    unittest.main()
