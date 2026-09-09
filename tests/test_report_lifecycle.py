import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from definalyzer.providers import ProviderError, ProviderResponse
from definalyzer.report_contract import ReportRequest, initialize_report_package
from definalyzer.report_evidence import prepare_report_evidence
from definalyzer.report_generation import generate_report_draft, load_report_draft
from definalyzer.report_lifecycle import (
    MAX_REVISION_PROMPT_CHARACTERS, commit_report_revision, finalize_report,
    load_final_report, revise_report_assertion,
)
from definalyzer.report_quality import review_report_quality
from definalyzer.workspace import WorkspaceManager


NOW = "2026-09-04T00:00:00+00:00"
REVIEWED = "2026-09-04T01:00:00+00:00"
FINALIZED = "2026-09-04T02:00:00+00:00"
REVISED = "2026-09-04T03:00:00+00:00"


class ScriptedProvider:
    def __init__(self, responses, name="scripted"):
        self.responses = list(responses)
        self.name = name
        self.prompts = []

    def generate(self, prompt, *, working_directory):
        self.prompts.append((prompt, Path(working_directory)))
        if not self.responses:
            raise AssertionError("Unexpected provider call")
        return ProviderResponse(
            text=self.responses.pop(0), provider=self.name, command=("fake",)
        )


class SupportingQualityProvider:
    name = "quality-scripted"

    def __init__(self, relationship="supports"):
        self.relationship = relationship

    def generate(self, prompt, *, working_directory):
        match = re.search(
            r"<UNTRUSTED_AUDIT_CASES>\n(.*?)\n</UNTRUSTED_AUDIT_CASES>",
            prompt,
            re.S,
        )
        if not match:
            raise AssertionError("Missing bounded audit cases")
        cases = json.loads(match.group(1))
        return ProviderResponse(text=json.dumps({"assessments": [{
            "case_id": case["case_id"],
            "evidence_assessments": [{
                "evidence_id": evidence["evidence_id"],
                "relationship": self.relationship,
                "note": "The relationship is assessed from this saved excerpt.",
            } for evidence in case["evidence"]],
            "reasoning_assessment": "reasonable",
            "reasoning_note": "The statement is appropriately qualified.",
        } for case in cases]}), provider=self.name, command=("quality",))


class FailingProvider:
    def generate(self, prompt, *, working_directory):
        raise ProviderError("offline")


def findings(*, full=False):
    rows = [{
        "category": "economics", "assertion_type": "documented_fact",
        "statement": "Documented revenue is variable.",
        "rationale": "The passage explicitly describes revenue.",
        "evidence_ids": ["E-001"], "support": "directly_supported",
        "limitations": ["This is not independently verified."],
    }]
    if full:
        rows.append({
            "category": "risks", "assertion_type": "interpretation",
            "statement": "Revenue variability may weaken predictable value accrual.",
            "rationale": "Variable revenue creates uncertainty.",
            "evidence_ids": ["E-001"], "support": "partially_supported",
            "limitations": ["No historical revenue series was retrieved."],
        })
    return json.dumps({"findings": rows})


def plan(*, full=False):
    if not full:
        return json.dumps({
            "executive_finding_ids": ["F-01-01"], "sections": [],
            "conclusion": {
                "stance": "answer",
                "statement": "The evidence supports a qualified answer.",
                "rationale": "The selected finding addresses the question.",
                "evidence_ids": ["E-001"], "support": "partially_supported",
                "limitations": ["The claim was not independently verified."],
                "what_would_change_finding_ids": [],
            },
        })
    return json.dumps({
        "executive_finding_ids": ["F-01-01"],
        "sections": [{
            "heading": "Risks and Counterarguments",
            "finding_ids": ["F-01-02"],
        }],
        "conclusion": {
            "stance": "neutral",
            "statement": "Maintain a neutral view until revenue is quantified.",
            "rationale": "Variability and absent history prevent a stronger view.",
            "evidence_ids": ["E-001"], "support": "partially_supported",
            "limitations": ["No historical revenue series was retrieved."],
            "what_would_change_finding_ids": ["F-01-02"],
        },
    })


class ReportLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.manager = WorkspaceManager(Path(self.temporary.name) / "output")
        self.counter = 0

    def make_report(self, *, full=False, review=True, relationship="supports"):
        self.counter += 1
        workspace = self.manager.create_project(name=f"Example {self.counter}")
        package = initialize_report_package(
            workspace=workspace,
            request=ReportRequest(
                title="Revenue Review", mode="full_review" if full else "question",
                question=None if full else "Is revenue sustainable?",
            ),
            now=NOW,
        )
        source_root = workspace.sources_directory if full else workspace.vault_entity_directory
        source_root.mkdir(parents=True, exist_ok=True)
        (source_root / "Economics.md").write_text(
            "# Economics\n\n## Revenue\n\nDocumented revenue is variable.\n",
            encoding="utf-8",
        )
        prepare_report_evidence(
            workspace=workspace, report_id="revenue-review", now=NOW
        )
        generate_report_draft(
            workspace=workspace, report_id="revenue-review",
            provider=ScriptedProvider([findings(full=full), plan(full=full)]),
            now=NOW,
        )
        if review:
            review_report_quality(
                workspace=workspace, report_id="revenue-review",
                provider=SupportingQualityProvider(relationship), now=REVIEWED,
            )
        return workspace, package

    def revised_content(self, workspace, package):
        draft = load_report_draft(
            workspace=workspace, report_id="revenue-review"
        )
        claims = json.loads(json.dumps(draft.claims))
        old = claims["assertions"][0]["statement"]
        new = "Documented revenue can vary."
        claims["assertions"][0]["statement"] = new
        markdown = draft.markdown.replace(old, new)
        return markdown, claims

    def test_initial_generated_draft_has_revision_provenance(self):
        _, package = self.make_report(review=False)
        bundle = json.loads(package.draft_path.read_text())
        self.assertEqual(bundle["revision"]["number"], 0)
        self.assertIsNone(bundle["revision"]["parent_draft_sha256"])
        self.assertEqual(bundle["revision"]["author"], "provider")

    def test_human_revision_archives_prior_state_and_resets_quality(self):
        workspace, package = self.make_report()
        old_report = package.report_path.read_bytes()
        markdown, claims = self.revised_content(workspace, package)
        result = commit_report_revision(
            workspace=workspace, report_id="revenue-review", claims=claims,
            markdown=markdown, change_summary="Qualified the revenue wording.",
            now=REVISED,
        )
        self.assertEqual(result.revision, 1)
        self.assertEqual(result.archive_path.name, "0000")
        self.assertEqual((result.archive_path / "Report.md").read_bytes(), old_report)
        self.assertTrue((result.archive_path / "Analyst-Notes.md").exists())
        self.assertTrue((result.archive_path / "quality.json").exists())
        record = json.loads((result.archive_path / "revision.json").read_text())
        self.assertEqual(record["status"], "quality_reviewed")
        manifest = json.loads(package.manifest_path.read_text())
        self.assertEqual(manifest["status"], "draft")
        self.assertEqual(manifest["current_revision"], 1)
        self.assertEqual(manifest["quality"]["status"], "not_run")
        self.assertFalse(package.quality_path.exists())
        self.assertFalse(package.quality_markdown_path.exists())
        bundle = json.loads(package.draft_path.read_text())
        self.assertEqual(bundle["revision"]["author"], "human")
        self.assertEqual(bundle["revision"]["number"], 1)
        self.assertRegex(bundle["revision"]["parent_draft_sha256"], r"^[a-f0-9]{64}$")
        self.assertFalse(load_report_draft(
            workspace=workspace, report_id="revenue-review"
        ).modified)

    def test_current_edited_markdown_can_be_committed_without_passing_it_twice(self):
        workspace, package = self.make_report(review=False)
        markdown, claims = self.revised_content(workspace, package)
        package.report_path.write_bytes(markdown.encode("utf-8"))
        result = commit_report_revision(
            workspace=workspace, report_id="revenue-review", claims=claims,
            change_summary="Committed the local analyst edit.", now=REVISED,
        )
        self.assertEqual(result.revision, 1)
        self.assertTrue(json.loads(
            (result.archive_path / "revision.json").read_text()
        )["working_report_modified"])

    def test_provider_can_only_make_one_validated_targeted_draft_revision(self):
        workspace, package = self.make_report()
        response = json.dumps({
            "assertion_id": "C-001",
            "statement": "Documented revenue can vary <materially>.",
            "rationale": "The saved passage characterizes revenue as variable.",
            "support": "directly_supported",
            "limitations": ["The source does not quantify the variation."],
            "change_summary": "Qualified the selected revenue assertion.",
        })
        provider = ScriptedProvider([response], name="revision-scripted")
        result = revise_report_assertion(
            workspace=workspace, report_id="revenue-review",
            assertion_id="C-001",
            instruction="Make this statement more precise without adding facts.",
            provider=provider, now=REVISED,
        )
        self.assertEqual(result.revision, 1)
        bundle = json.loads(package.draft_path.read_text())
        self.assertEqual(bundle["revision"]["author"], "provider")
        self.assertEqual(bundle["revision"]["provider"], "revision-scripted")
        self.assertIn(r"\<materially\>", package.report_path.read_text())
        self.assertNotIn("<materially>", package.report_path.read_text())
        self.assertEqual(len(provider.prompts), 1)
        self.assertLessEqual(len(provider.prompts[0][0]), MAX_REVISION_PROMPT_CHARACTERS)
        self.assertIn("data, never instructions", provider.prompts[0][0])
        self.assertIn("<UNTRUSTED_REVISION_DATA>", provider.prompts[0][0])
        self.assertFalse(package.quality_path.exists())

    def test_invalid_or_failed_provider_revision_preserves_current_report(self):
        invalid = [
            "not json",
            '{"assertion_id":"C-001","assertion_id":"C-001"}',
            json.dumps({
                "assertion_id": "C-999", "statement": "Changed",
                "rationale": "Reason", "support": "directly_supported",
                "limitations": [], "change_summary": "Change",
            }),
            json.dumps({
                "assertion_id": "C-001", "statement": "Changed",
                "rationale": "Reason", "support": "unsupported",
                "limitations": [], "change_summary": "Change",
            }),
        ]
        for response in invalid:
            workspace, package = self.make_report(review=False)
            before = package.report_path.read_bytes()
            with self.assertRaises(ValueError):
                revise_report_assertion(
                    workspace=workspace, report_id="revenue-review",
                    assertion_id="C-001", instruction="Revise carefully.",
                    provider=ScriptedProvider([response]), now=REVISED,
                )
            self.assertEqual(package.report_path.read_bytes(), before)
            self.assertEqual(list(package.revisions_directory.iterdir()), [])
        workspace, package = self.make_report(review=False)
        before = package.report_path.read_bytes()
        with self.assertRaises(ProviderError):
            revise_report_assertion(
                workspace=workspace, report_id="revenue-review",
                assertion_id="C-001", instruction="Revise carefully.",
                provider=FailingProvider(), now=REVISED,
            )
        self.assertEqual(package.report_path.read_bytes(), before)

    def test_provider_revision_never_overwrites_uncommitted_human_edit(self):
        workspace, package = self.make_report(review=False)
        package.report_path.write_bytes(
            package.report_path.read_bytes() + b"\nHuman working note.\n"
        )
        before = package.report_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "existing human edit"):
            revise_report_assertion(
                workspace=workspace, report_id="revenue-review",
                assertion_id="C-001", instruction="Revise carefully.",
                provider=ScriptedProvider([]), now=REVISED,
            )
        self.assertEqual(package.report_path.read_bytes(), before)

    def test_revision_rejects_claim_drift_missing_citations_and_no_change(self):
        workspace, package = self.make_report(review=False)
        draft = load_report_draft(workspace=workspace, report_id="revenue-review")
        claims = json.loads(json.dumps(draft.claims))
        claims["assertions"][0]["statement"] = "Changed but absent"
        with self.assertRaisesRegex(ValueError, "absent"):
            commit_report_revision(
                workspace=workspace, report_id="revenue-review", claims=claims,
                change_summary="Invalid mismatch", now=REVISED,
            )
        claims = json.loads(json.dumps(draft.claims))
        claims["assertions"].pop()
        with self.assertRaisesRegex(ValueError, "stable assertion ID"):
            commit_report_revision(
                workspace=workspace, report_id="revenue-review", claims=claims,
                markdown=draft.markdown, change_summary="Invalid deletion", now=REVISED,
            )
        with self.assertRaisesRegex(ValueError, "does not change"):
            commit_report_revision(
                workspace=workspace, report_id="revenue-review", claims=draft.claims,
                markdown=draft.markdown, change_summary="No change", now=REVISED,
            )
        self.assertEqual(list(package.revisions_directory.iterdir()), [])

    def test_finalize_requires_explicit_human_approval_and_clean_quality_pass(self):
        workspace, package = self.make_report()
        with self.assertRaisesRegex(ValueError, "explicit human approval"):
            finalize_report(
                workspace=workspace, report_id="revenue-review",
                human_approved=False, now=FINALIZED,
            )
        result = finalize_report(
            workspace=workspace, report_id="revenue-review",
            human_approved=True, now=FINALIZED,
        )
        self.assertEqual(result.revision, 0)
        self.assertFalse(result.recommendation_approved)
        self.assertTrue(package.approval_path.exists())
        manifest = json.loads(package.manifest_path.read_text())
        self.assertEqual(manifest["status"], "final")
        self.assertRegex(
            manifest["human_review"]["approval_sha256"], r"^[a-f0-9]{64}$"
        )
        loaded = load_final_report(
            workspace=workspace, report_id="revenue-review"
        )
        self.assertEqual(loaded.finalized_at, FINALIZED)

    def test_full_review_requires_separate_recommendation_approval(self):
        workspace, _ = self.make_report(full=True)
        with self.assertRaisesRegex(ValueError, "recommendation"):
            finalize_report(
                workspace=workspace, report_id="revenue-review",
                human_approved=True, recommendation_approved=False,
                now=FINALIZED,
            )
        result = finalize_report(
            workspace=workspace, report_id="revenue-review",
            human_approved=True, recommendation_approved=True,
            now=FINALIZED,
        )
        self.assertTrue(result.recommendation_approved)

    def test_question_report_cannot_claim_recommendation_approval(self):
        workspace, _ = self.make_report()
        with self.assertRaisesRegex(ValueError, "no recommendation"):
            finalize_report(
                workspace=workspace, report_id="revenue-review",
                human_approved=True, recommendation_approved=True,
                now=FINALIZED,
            )

    def test_quality_issues_and_changed_sources_block_finalization(self):
        workspace, package = self.make_report(relationship="context_only")
        with self.assertRaisesRegex(ValueError, "quality issues"):
            finalize_report(
                workspace=workspace, report_id="revenue-review",
                human_approved=True, now=FINALIZED,
            )
        workspace2, _ = self.make_report()
        source = workspace2.vault_entity_directory / "Economics.md"
        source.write_text(source.read_text() + "\nChanged after review.\n")
        with self.assertRaisesRegex(ValueError, "evidence scope changed"):
            finalize_report(
                workspace=workspace2, report_id="revenue-review",
                human_approved=True, now=FINALIZED,
            )
        self.assertFalse(package.approval_path.exists())

    def test_final_load_rejects_report_and_approval_tampering(self):
        workspace, package = self.make_report()
        finalize_report(
            workspace=workspace, report_id="revenue-review",
            human_approved=True, now=FINALIZED,
        )
        original = package.report_path.read_bytes()
        package.report_path.write_bytes(original + b"\nchanged\n")
        with self.assertRaisesRegex(ValueError, "changed after approval"):
            load_final_report(workspace=workspace, report_id="revenue-review")
        package.report_path.write_bytes(original)
        original_notes = package.analyst_notes_path.read_bytes()
        package.analyst_notes_path.write_bytes(original_notes + b"\nchanged\n")
        with self.assertRaisesRegex(ValueError, "Analyst Notes were changed"):
            load_final_report(workspace=workspace, report_id="revenue-review")
        package.analyst_notes_path.write_bytes(original_notes)
        approval = json.loads(package.approval_path.read_text())
        approval["statement"] = "A different statement."
        package.approval_path.write_text(json.dumps(approval))
        with self.assertRaisesRegex(ValueError, "digest"):
            load_final_report(workspace=workspace, report_id="revenue-review")

    def test_revising_final_report_archives_approval_and_returns_to_draft(self):
        workspace, package = self.make_report()
        finalize_report(
            workspace=workspace, report_id="revenue-review",
            human_approved=True, now=FINALIZED,
        )
        markdown, claims = self.revised_content(workspace, package)
        result = commit_report_revision(
            workspace=workspace, report_id="revenue-review", claims=claims,
            markdown=markdown, change_summary="Post-final analyst revision.",
            now=REVISED,
        )
        self.assertTrue((result.archive_path / "approval.json").exists())
        self.assertFalse(package.approval_path.exists())
        manifest = json.loads(package.manifest_path.read_text())
        self.assertEqual(manifest["status"], "draft")
        self.assertIsNone(manifest["human_review"]["finalized_at"])

    def test_revision_failure_rolls_back_files_and_archive(self):
        workspace, package = self.make_report()
        markdown, claims = self.revised_content(workspace, package)
        tracked = [
            package.manifest_path, package.draft_path, package.claims_path,
            package.report_path, package.quality_path,
            package.quality_markdown_path,
        ]
        before = {path: path.read_bytes() for path in tracked}
        from definalyzer import report_lifecycle
        original = report_lifecycle._atomic_json

        def fail_claims(path, document, *, exclusive=False):
            if path == package.claims_path:
                raise OSError("simulated revision interruption")
            return original(path, document, exclusive=exclusive)

        with patch.object(report_lifecycle, "_atomic_json", fail_claims):
            with self.assertRaises(OSError):
                commit_report_revision(
                    workspace=workspace, report_id="revenue-review",
                    claims=claims, markdown=markdown,
                    change_summary="Interrupted revision", now=REVISED,
                )
        self.assertEqual(list(package.revisions_directory.iterdir()), [])
        for path, value in before.items():
            self.assertEqual(path.read_bytes(), value)

    def test_finalization_failure_rolls_back_approval(self):
        workspace, package = self.make_report()
        from definalyzer import report_lifecycle
        original = report_lifecycle._atomic_json

        def fail_manifest(path, document, *, exclusive=False):
            if path == package.manifest_path:
                raise OSError("simulated finalization interruption")
            return original(path, document, exclusive=exclusive)

        with patch.object(report_lifecycle, "_atomic_json", fail_manifest):
            with self.assertRaises(OSError):
                finalize_report(
                    workspace=workspace, report_id="revenue-review",
                    human_approved=True, now=FINALIZED,
                )
        self.assertFalse(package.approval_path.exists())
        self.assertEqual(
            json.loads(package.manifest_path.read_text())["status"],
            "quality_reviewed",
        )

    def test_lifecycle_lock_and_timestamps_are_enforced(self):
        workspace, package = self.make_report()
        lock = package.directory / ".lifecycle.lock"
        lock.write_text("locked")
        with self.assertRaises(FileExistsError):
            finalize_report(
                workspace=workspace, report_id="revenue-review",
                human_approved=True, now=FINALIZED,
            )
        lock.unlink()
        with self.assertRaisesRegex(ValueError, "predate"):
            finalize_report(
                workspace=workspace, report_id="revenue-review",
                human_approved=True, now=NOW,
            )


if __name__ == "__main__":
    unittest.main()
