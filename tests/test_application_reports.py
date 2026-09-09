import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from definalyzer.application import DefinalyzerApplication
from definalyzer.providers import ProviderResponse
from definalyzer.workspace import WorkspaceManager


class ReportProvider:
    name = "report-test"

    def generate(self, prompt, *, working_directory):
        if "<UNTRUSTED_EVIDENCE>" in prompt:
            document = {"findings": [{
                "category": "economics",
                "assertion_type": "documented_fact",
                "statement": "Documented fees can vary.",
                "rationale": "The saved passage states that fees vary.",
                "evidence_ids": ["E-001"],
                "support": "directly_supported",
                "limitations": ["This is a documented claim."],
            }]}
        elif "<UNTRUSTED_FINDINGS>" in prompt:
            document = {
                "executive_finding_ids": ["F-01-01"],
                "sections": [],
                "conclusion": {
                    "stance": "answer",
                    "statement": "The evidence supports a qualified answer.",
                    "rationale": "The saved finding addresses the question.",
                    "evidence_ids": ["E-001"],
                    "support": "partially_supported",
                    "limitations": ["No independent verification was performed."],
                    "what_would_change_finding_ids": [],
                },
            }
        elif "<UNTRUSTED_AUDIT_CASES>" in prompt:
            match = re.search(
                r"<UNTRUSTED_AUDIT_CASES>\n(.*?)\n</UNTRUSTED_AUDIT_CASES>",
                prompt, re.S,
            )
            cases = json.loads(match.group(1))
            document = {"assessments": [{
                "case_id": case["case_id"],
                "evidence_assessments": [{
                    "evidence_id": row["evidence_id"],
                    "relationship": "supports",
                    "note": "The saved excerpt supports the qualified wording.",
                } for row in case["evidence"]],
                "reasoning_assessment": "reasonable",
                "reasoning_note": "The conclusion remains qualified.",
            } for case in cases]}
        else:
            raise AssertionError("Unexpected report prompt")
        return ProviderResponse(
            text=json.dumps(document), provider=self.name, command=("test",)
        )


class ApplicationReportTests(unittest.TestCase):
    def test_combined_generation_checks_once_and_download_preserves_output(self):
        from definalyzer.report_export import download_report_pdf
        self.application.create_report(workspace=self.workspace, title="Combined", mode="question", question="Are fees predictable?")
        progress = []
        with patch.object(ReportProvider, "generate", autospec=True, side_effect=ReportProvider.generate) as provider:
            result = self.application.generate_complete_report(workspace=self.workspace, report_id="combined", progress=progress.append)
            self.assertEqual(provider.call_count, 3)
        self.assertEqual(result.status, "passed")
        self.assertEqual(sum(message.startswith("[") for message in progress), 3)
        before = {p:p.read_bytes() for p in self.workspace.root.rglob("*") if p.is_file()}
        self.assertTrue(download_report_pdf(workspace=self.workspace, report_id="combined").startswith(b"%PDF"))
        self.assertEqual(before, {p:p.read_bytes() for p in self.workspace.root.rglob("*") if p.is_file()})
        with patch.object(self.application, "provider") as provider:
            with self.assertRaisesRegex(ValueError, "already has a draft"):
                self.application.generate_complete_report(workspace=self.workspace, report_id="combined")
            provider.assert_not_called()

    def test_combined_generation_stops_before_drafting_and_can_resume(self):
        import threading
        from definalyzer.cancellation import cancellation_scope, OperationCancelled
        self.application.create_report(workspace=self.workspace, title="Stopped", mode="question", question="Are fees predictable?")
        event = threading.Event()
        original = self.application.prepare_report_evidence
        def prepare(**kwargs):
            result = original(**kwargs)
            event.set()
            return result
        with patch.object(self.application, "prepare_report_evidence", side_effect=prepare), patch.object(self.application, "provider") as provider:
            with cancellation_scope(event), self.assertRaises(OperationCancelled):
                self.application.generate_complete_report(workspace=self.workspace, report_id="stopped")
            provider.assert_not_called()
        with patch.object(self.application, "prepare_report_evidence") as prepare:
            result = self.application.generate_complete_report(workspace=self.workspace, report_id="stopped")
            prepare.assert_not_called()
        self.assertEqual(result.status, "passed")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        manager = WorkspaceManager(Path(self.temporary.name) / "output")
        self.application = DefinalyzerApplication(
            manager, provider_factory=lambda settings: ReportProvider()
        )
        self.application.initialize()
        self.workspace = self.application.create_project(name="Example")
        (self.workspace.vault_entity_directory / "Economics.md").write_text(
            "# Economics\n\n## Fees\n\nDocumented fees can vary.\n",
            encoding="utf-8",
        )

    def test_application_exposes_complete_report_lifecycle(self):
        dormant = self.workspace.project_root / "facts" / "current.json"
        dormant.parent.mkdir(parents=True, exist_ok=True)
        dormant.write_text("invalid dormant V2 state", encoding="utf-8")
        summary = self.application.create_report(
            workspace=self.workspace, title="Fee Review", mode="question",
            question="Are fees predictable?",
        )
        self.assertEqual(summary.status, "scoped")
        self.assertTrue(summary.actions["prepare_evidence"].available)

        self.application.prepare_report_evidence(
            workspace=self.workspace, report_id="fee-review"
        )
        summary = self.application.reports(self.workspace)[0]
        self.assertEqual(summary.status, "evidence_ready")
        self.assertTrue(summary.actions["generate_draft"].available)

        self.application.generate_report(
            workspace=self.workspace, report_id="fee-review"
        )
        detail = self.application.report_detail(
            workspace=self.workspace, report_id="fee-review"
        )
        self.assertEqual(detail["report"]["status"], "draft")
        self.assertEqual(detail["assertions"][0]["assertion_id"], "C-001")

        reviewed = self.application.review_report(
            workspace=self.workspace, report_id="fee-review"
        )
        self.assertEqual(reviewed.status, "passed")
        summary = self.application.reports(self.workspace)[0]
        self.assertTrue(summary.actions["finalize"].available)

        self.application.finalize_report(
            workspace=self.workspace, report_id="fee-review",
            human_approved=True,
        )
        summary = self.application.reports(self.workspace)[0]
        self.assertEqual(summary.status, "final")
        self.assertTrue(summary.actions["export"].available)

        result = self.application.export_report(
            workspace=self.workspace, report_id="fee-review",
            formats=("markdown", "html", "pdf"),
        )
        self.assertTrue(result.pdf_path.exists())
        summary = self.application.reports(self.workspace)[0]
        self.assertEqual(summary.export_revisions, (0,))
        self.assertFalse(summary.actions["export"].available)
        self.assertTrue(summary.report_page.endswith("/Report.md"))
        self.assertTrue(summary.analyst_notes_page.endswith("/Analyst-Notes.md"))
        self.assertEqual(summary.readiness, "partial")
        self.assertTrue(summary.quality_page.endswith("/Quality.md"))

    def test_report_detail_rejects_unknown_report(self):
        with self.assertRaises(FileNotFoundError):
            self.application.report_detail(
                workspace=self.workspace, report_id="missing"
            )


if __name__ == "__main__":
    unittest.main()
