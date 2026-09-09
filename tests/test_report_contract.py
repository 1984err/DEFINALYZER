import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from definalyzer.report_contract import (
    ReportRequest,
    content_sha256,
    initialize_report_package,
    validate_assertion_ledger,
    validate_evidence_ledger,
    validate_report_manifest,
)
from definalyzer.workspace import WorkspaceManager


NOW = "2026-09-03T12:00:00+00:00"


class ReportContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.manager = WorkspaceManager(Path(self.temporary.name) / "output")
        self.workspace = self.manager.create_project(
            name="Example Protocol", entity_type="protocol"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def _package(self):
        return initialize_report_package(
            workspace=self.workspace,
            request=ReportRequest(
                title="Revenue Sustainability",
                mode="question",
                question="Can documented revenue sustain token incentives?",
            ),
            now=NOW,
        )

    def _evidence(self):
        return {
            "schema_version": 1,
            "report_id": "revenue-sustainability",
            "evidence": [{
                "evidence_id": "E-001",
                "source_type": "research",
                "source_path": "Protocols/Example Protocol/Revenue-Model.md",
                "source_url": None,
                "locator": {"heading": "Distribution", "line": 22, "block_id": None},
                "content_sha256": content_sha256("documented distribution"),
                "captured_at": NOW,
                "as_of": None,
                "summary": "The research page records the documented fee distribution.",
            }],
        }

    def test_initializes_portable_scoped_package_without_report_prose(self):
        package = self._package()
        manifest = json.loads(package.manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["status"], "scoped")
        self.assertEqual(manifest["current_revision"], 0)
        self.assertEqual(manifest["project"]["slug"], self.workspace.slug)
        self.assertEqual(manifest["question"], "Can documented revenue sustain token incentives?")
        self.assertTrue(package.evidence_path.exists())
        self.assertTrue(package.claims_path.exists())
        self.assertTrue(package.assets_directory.is_dir())
        self.assertTrue(package.revisions_directory.is_dir())
        self.assertTrue(package.exports_directory.is_dir())
        self.assertFalse(package.report_path.exists())
        self.assertFalse(package.analyst_notes_path.exists())
        self.assertEqual(manifest["files"]["analyst_notes"], "Analyst-Notes.md")
        self.assertFalse(package.draft_path.exists())
        self.assertFalse(package.quality_path.exists())
        self.assertFalse(package.quality_markdown_path.exists())
        self.assertFalse(package.approval_path.exists())
        validate_report_manifest(manifest, workspace=self.workspace)

    def test_phase_six_layout_accepts_existing_schema_one_packages(self):
        package = self._package()
        manifest = json.loads(package.manifest_path.read_text(encoding="utf-8"))
        manifest["files"].pop("exports")
        validate_report_manifest(manifest, workspace=self.workspace)
        manifest["files"].pop("analyst_notes")
        validate_report_manifest(manifest, workspace=self.workspace)

    def test_full_review_allows_no_guiding_question(self):
        package = initialize_report_package(
            workspace=self.workspace,
            request=ReportRequest(title="Full Review", mode="full_review"),
            now=NOW,
        )
        manifest = json.loads(package.manifest_path.read_text(encoding="utf-8"))
        self.assertIsNone(manifest["question"])

    def test_question_mode_requires_question_and_package_never_overwrites(self):
        with self.assertRaisesRegex(ValueError, "require a research question"):
            initialize_report_package(
                workspace=self.workspace,
                request=ReportRequest(title="Missing Question", mode="question"),
                now=NOW,
            )
        self._package()
        with self.assertRaisesRegex(FileExistsError, "will not be overwritten"):
            self._package()

    def test_rejects_unsafe_or_reserved_report_ids(self):
        for identifier in ("../escape", "Has Spaces", "CON", "a" * 64):
            with self.subTest(identifier=identifier):
                with self.assertRaisesRegex(ValueError, "Report ID"):
                    initialize_report_package(
                        workspace=self.workspace,
                        request=ReportRequest(
                            title="Unsafe", mode="full_review", report_id=identifier
                        ),
                        now=NOW,
                    )

    def test_manifest_is_bound_to_project_and_final_requires_human_timestamp(self):
        package = self._package()
        manifest = json.loads(package.manifest_path.read_text(encoding="utf-8"))
        wrong = deepcopy(manifest)
        wrong["project"]["slug"] = "another-project"
        with self.assertRaisesRegex(ValueError, "does not belong"):
            validate_report_manifest(wrong, workspace=self.workspace)
        final = deepcopy(manifest)
        final["status"] = "final"
        final["quality"] = {
            "status": "passed", "checked_at": NOW,
            "issues_file": "quality.json",
        }
        with self.assertRaisesRegex(ValueError, "finalized_at"):
            validate_report_manifest(final, workspace=self.workspace)
        final["human_review"]["finalized_at"] = NOW
        with self.assertRaisesRegex(ValueError, "approval record"):
            validate_report_manifest(final, workspace=self.workspace)
        final["human_review"]["approval_sha256"] = "0" * 64
        validate_report_manifest(final, workspace=self.workspace)

    def test_manifest_timestamps_require_timezone(self):
        package = self._package()
        manifest = json.loads(package.manifest_path.read_text(encoding="utf-8"))
        manifest["updated_at"] = "2026-09-03T12:00:00"
        with self.assertRaisesRegex(ValueError, "timezone"):
            validate_report_manifest(manifest, workspace=self.workspace)

    def test_evidence_requires_provenance_locator_digest_and_unique_id(self):
        ledger = self._evidence()
        self.assertEqual(
            validate_evidence_ledger(ledger, report_id="revenue-sustainability"),
            {"E-001"},
        )
        for field, value, message in (
            ("source_path", "../../secret", "inside"),
            ("content_sha256", "not-a-digest", "SHA-256"),
            ("captured_at", "2026-09-03", "timezone"),
        ):
            invalid = deepcopy(ledger)
            invalid["evidence"][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                validate_evidence_ledger(invalid, report_id="revenue-sustainability")
        duplicate = deepcopy(ledger)
        duplicate["evidence"].append(deepcopy(duplicate["evidence"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_evidence_ledger(duplicate, report_id="revenue-sustainability")

    def test_evidence_urls_cannot_embed_credentials(self):
        ledger = self._evidence()
        item = ledger["evidence"][0]
        item["source_path"] = None
        item["source_url"] = "https://user:secret@example.test/report"
        with self.assertRaisesRegex(ValueError, "without credentials"):
            validate_evidence_ledger(ledger, report_id="revenue-sustainability")

    def test_evidence_paths_and_line_ranges_are_portable(self):
        for path in ("C:/secret.md", "folder//file.md", "folder/./file.md", "folder/file.md/"):
            ledger = self._evidence()
            ledger["evidence"][0]["source_path"] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "path|inside"):
                validate_evidence_ledger(ledger, report_id="revenue-sustainability")
        ledger = self._evidence()
        ledger["evidence"][0]["locator"]["end_line"] = 2
        with self.assertRaisesRegex(ValueError, "end_line"):
            validate_evidence_ledger(ledger, report_id="revenue-sustainability")

    def test_assertions_separate_type_support_and_evidence(self):
        assertion = {
            "assertion_id": "C-001",
            "assertion_type": "interpretation",
            "statement": "Documented revenue may not fully offset incentives.",
            "report_section": "Analysis",
            "rationale": "The cited sources identify both flows but do not reconcile them.",
            "evidence_ids": ["E-001"],
            "support": "partially_supported",
            "limitations": ["No complete historical reconciliation is available."],
        }
        ledger = {
            "schema_version": 1,
            "report_id": "revenue-sustainability",
            "assertions": [assertion],
        }
        self.assertEqual(
            validate_assertion_ledger(
                ledger,
                report_id="revenue-sustainability",
                evidence_ids={"E-001"},
            ),
            {"C-001"},
        )
        no_evidence = deepcopy(ledger)
        no_evidence["assertions"][0]["evidence_ids"] = []
        with self.assertRaisesRegex(ValueError, "requires evidence"):
            validate_assertion_ledger(
                no_evidence,
                report_id="revenue-sustainability",
                evidence_ids={"E-001"},
            )
        unknown = deepcopy(ledger)
        unknown["assertions"][0]["evidence_ids"] = ["E-999"]
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            validate_assertion_ledger(
                unknown,
                report_id="revenue-sustainability",
                evidence_ids={"E-001"},
            )

    def test_only_uncertainty_can_stand_without_evidence(self):
        ledger = {
            "schema_version": 1,
            "report_id": "revenue-sustainability",
            "assertions": [{
                "assertion_id": "C-001",
                "assertion_type": "uncertainty",
                "statement": "Historical revenue reconciliation is unavailable.",
                "report_section": "Material Unknowns",
                "rationale": "No retrieved source contains a complete series.",
                "evidence_ids": [],
                "support": "unsupported",
                "limitations": ["Absence applies only to retrieved evidence."],
            }],
        }
        validate_assertion_ledger(
            ledger, report_id="revenue-sustainability", evidence_ids=set()
        )

    def test_unsupported_interpretation_is_rejected(self):
        ledger = {
            "schema_version": 1,
            "report_id": "revenue-sustainability",
            "assertions": [{
                "assertion_id": "C-001", "assertion_type": "interpretation",
                "statement": "Unsupported interpretation", "report_section": "Analysis",
                "rationale": "No basis", "evidence_ids": ["E-001"],
                "support": "unsupported", "limitations": [],
            }],
        }
        with self.assertRaisesRegex(ValueError, "Only an uncertainty"):
            validate_assertion_ledger(
                ledger, report_id="revenue-sustainability", evidence_ids={"E-001"}
            )

    def test_deleting_project_removes_its_reports(self):
        package = self._package()
        self.assertTrue(package.directory.exists())
        self.manager.delete_project(self.workspace)
        self.assertFalse(package.directory.exists())


if __name__ == "__main__":
    unittest.main()
