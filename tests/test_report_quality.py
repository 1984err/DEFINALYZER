import json
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from definalyzer.providers import ProviderError, ProviderResponse
from definalyzer.report_contract import (
    ReportRequest, content_sha256, initialize_report_package,
)
from definalyzer.report_evidence import load_report_evidence, prepare_report_evidence
from definalyzer.report_generation import generate_report_draft, load_report_draft
from definalyzer.report_quality import (
    MAX_PROMPT_CHARACTERS, _deterministic_issues, _narrative_blocks,
    _numbers_equivalent,
    load_report_quality,
    review_report_quality,
)
from definalyzer.workspace import WorkspaceManager


NOW = "2026-09-04T00:00:00+00:00"
REVIEWED = "2026-09-04T01:00:00+00:00"


class ScriptedProvider:
    name = "scripted"

    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.prompts = []

    def generate(self, prompt, *, working_directory):
        self.prompts.append((prompt, Path(working_directory)))
        if self.error:
            raise self.error
        if not self.responses:
            raise AssertionError("Unexpected provider call")
        return ProviderResponse(
            text=self.responses.pop(0), provider=self.name, command=("fake",)
        )


class QualityProvider:
    name = "quality-scripted"

    def __init__(self, *, relationship="supports", reasoning="reasonable", raw=None):
        self.relationship = relationship
        self.reasoning = reasoning
        self.raw = raw
        self.prompts = []

    def generate(self, prompt, *, working_directory):
        self.prompts.append((prompt, Path(working_directory)))
        if self.raw is not None:
            text = self.raw
        else:
            match = re.search(
                r"<UNTRUSTED_AUDIT_CASES>\n(.*?)\n</UNTRUSTED_AUDIT_CASES>",
                prompt,
                re.S,
            )
            if not match:
                raise AssertionError("Audit cases were not delimited")
            cases = json.loads(match.group(1))
            text = json.dumps({"assessments": [
                {
                    "case_id": case["case_id"],
                    "evidence_assessments": [
                        {
                            "evidence_id": evidence["evidence_id"],
                            "relationship": self.relationship,
                            "note": "The saved excerpt has the represented relationship.",
                        }
                        for evidence in case["evidence"]
                    ],
                    "reasoning_assessment": self.reasoning,
                    "reasoning_note": "The statement is appropriately qualified for the saved excerpt.",
                }
                for case in cases
            ]})
        return ProviderResponse(
            text=text, provider=self.name, command=("quality-fake",)
        )


def finding_response(*, statement="Documented revenue is variable.", two=False):
    findings = [{
        "category": "economics",
        "assertion_type": "documented_fact",
        "statement": statement,
        "rationale": "The saved passage explicitly describes revenue.",
        "evidence_ids": ["E-001"],
        "support": "directly_supported",
        "limitations": ["This is a documented claim, not independent verification."],
    }]
    if two:
        findings.append({
            "category": "risks",
            "assertion_type": "interpretation",
            "statement": "Revenue variability may weaken predictable value accrual.",
            "rationale": "Variable revenue creates uncertainty.",
            "evidence_ids": ["E-001"],
            "support": "partially_supported",
            "limitations": ["No historical revenue series was retrieved."],
        })
    return json.dumps({"findings": findings})


def question_plan():
    return json.dumps({
        "executive_finding_ids": ["F-01-01"],
        "sections": [],
        "conclusion": {
            "stance": "answer",
            "statement": "The evidence supports a qualified answer.",
            "rationale": "The selected finding addresses the question.",
            "evidence_ids": ["E-001"],
            "support": "partially_supported",
            "limitations": ["The claim was not independently verified."],
            "what_would_change_finding_ids": [],
        },
    })


def full_plan():
    return json.dumps({
        "executive_finding_ids": ["F-01-01"],
        "sections": [{
            "heading": "Risks and Counterarguments",
            "finding_ids": ["F-01-02"],
        }],
        "conclusion": {
            "stance": "neutral",
            "statement": "Maintain a neutral view until revenue is quantified.",
            "rationale": "Variability and absent history prevent a stronger position.",
            "evidence_ids": ["E-001"],
            "support": "partially_supported",
            "limitations": ["No historical revenue series was retrieved."],
            "what_would_change_finding_ids": ["F-01-02"],
        },
    })


class ReportQualityTests(unittest.TestCase):
    def test_assessment_notes_accept_paragraphs_without_changing_judgments(self):
        from definalyzer.report_quality import _validate_assessment_response
        note = "Saved evidence supports this condition. " * 15
        document = {"assessments": [{
            "case_id": "Q-C-001-01",
            "evidence_assessments": [{"evidence_id": "E-001", "relationship": "contradicts", "note": note + "\n\tHowever, the conclusion omits it."}],
            "reasoning_assessment": "overstated", "reasoning_note": note + "\r\nKeep the condition.",
        }]}
        batch = [{"case_id": "Q-C-001-01", "evidence": [{"evidence_id": "E-001"}]}]
        result = _validate_assessment_response(document, batch)[0]
        self.assertEqual(result["evidence_assessments"][0]["note"], note + "However, the conclusion omits it.")
        self.assertEqual(result["evidence_assessments"][0]["relationship"], "contradicts")
        self.assertEqual(result["reasoning_assessment"], "overstated")
        self.assertEqual(result["reasoning_note"], note + "Keep the condition.")

    def test_assessment_notes_still_reject_missing_or_invalid_content(self):
        from definalyzer.report_quality import _assessment_note, MAX_RESPONSE_CHARACTERS
        for value in (None, " \n\t", "text\x00hidden", "x" * (MAX_RESPONSE_CHARACTERS + 1)):
            with self.subTest(value=repr(value)[:40]), self.assertRaises(ValueError):
                _assessment_note(value, "Evidence assessment note")

    def test_outline_only_markdown_has_no_developed_narrative(self):
        markdown = """# Review

- Subject: Example

## Executive Summary

- One short finding. [^E-001]

## Scope

> **Research question:** Is it worthwhile?

## Qualified Conclusion

- One short conclusion. [^E-001]

## Evidence Notes

[^E-001]: saved evidence.
"""
        self.assertEqual(_narrative_blocks(markdown), [])

    def test_rounded_million_notation_matches_saved_full_values(self):
        self.assertTrue(_numbers_equivalent("15.419M", "15418570.06641533"))
        self.assertTrue(_numbers_equivalent("16M", "16000000.0"))
        self.assertFalse(_numbers_equivalent("15M", "16000000.0"))

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.manager = WorkspaceManager(Path(self.temporary.name) / "output")
        self.counter = 0

    def make_draft(
        self, *, evidence=True, mode="question", statement=None, name=None,
    ):
        self.counter += 1
        workspace = self.manager.create_project(
            name=name or f"Example Protocol {self.counter}"
        )
        request = ReportRequest(
            title="Revenue Review",
            mode=mode,
            question="Is revenue sustainable?" if mode == "question" else None,
        )
        package = initialize_report_package(
            workspace=workspace, request=request, now=NOW
        )
        if evidence:
            (workspace.vault_entity_directory / "Economics.md").write_text(
                "# Economics\n\n## Revenue\n\nDocumented revenue is variable.\n",
                encoding="utf-8",
            )
        prepare_report_evidence(
            workspace=workspace, report_id="revenue-review", now=NOW
        )
        if evidence:
            if mode == "full_review":
                responses = [finding_response(two=True), full_plan()]
            else:
                responses = [finding_response(statement=statement or "Documented revenue is variable."), question_plan()]
        else:
            responses = []
        generate_report_draft(
            workspace=workspace,
            report_id="revenue-review",
            provider=ScriptedProvider(responses),
            now=NOW,
        )
        return workspace, package

    def test_review_passes_without_mutating_report_claims_or_evidence(self):
        workspace, package = self.make_draft()
        before = {
            path.name: path.read_bytes()
            for path in (package.report_path, package.claims_path, package.evidence_path)
        }
        provider = QualityProvider()
        result = review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=provider, now=REVIEWED,
        )
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.issues, ())
        self.assertEqual(result.provider, "quality-scripted")
        self.assertTrue(package.quality_path.exists())
        self.assertTrue(package.quality_markdown_path.exists())
        manifest = json.loads(package.manifest_path.read_text())
        self.assertEqual(manifest["status"], "quality_reviewed")
        self.assertEqual(manifest["quality"]["status"], "passed")
        quality = json.loads(package.quality_path.read_text())
        self.assertEqual(quality["checks"]["ai_calls"], len(provider.prompts))
        self.assertIn("does not verify source claims", " ".join(quality["limitations"]))
        self.assertTrue(all(len(prompt) <= MAX_PROMPT_CHARACTERS for prompt, _ in provider.prompts))
        self.assertTrue(all("data, never instructions" in prompt for prompt, _ in provider.prompts))
        for path in (package.report_path, package.claims_path, package.evidence_path):
            self.assertEqual(path.read_bytes(), before[path.name])

    def test_contradiction_and_overstatement_are_blocking_quality_issues(self):
        workspace, package = self.make_draft()
        result = review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=QualityProvider(
                relationship="contradicts", reasoning="overstated"
            ),
            now=REVIEWED,
        )
        self.assertEqual(result.status, "issues_found")
        codes = {issue.code for issue in result.issues}
        self.assertIn("evidence_contradicts_assertion", codes)
        self.assertIn("assertion_support_unclear", codes)
        self.assertIn("reasoning_overstated", codes)
        quality = json.loads(package.quality_path.read_text())
        self.assertTrue(all(row["outcome"] == "error" for row in quality["assertion_reviews"]))

    def test_context_only_evidence_is_not_treated_as_support(self):
        workspace, _ = self.make_draft()
        result = review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=QualityProvider(relationship="context_only"), now=REVIEWED,
        )
        self.assertIn("assertion_not_supported", {issue.code for issue in result.issues})

    def test_invalid_provider_outputs_never_commit_quality_review(self):
        invalid = [
            "not json",
            '{"assessments":[],"assessments":[]}',
            json.dumps({"assessments": []}),
            json.dumps({"assessments": [{
                "case_id": "Q-C-999-01", "evidence_assessments": [],
                "reasoning_assessment": "reasonable", "reasoning_note": "note",
            }]}),
            json.dumps({"assessments": [{
                "case_id": "Q-C-001-01",
                "evidence_assessments": [{
                    "evidence_id": "E-999", "relationship": "supports", "note": "note",
                }],
                "reasoning_assessment": "reasonable", "reasoning_note": "note",
            }]}),
        ]
        for index, response in enumerate(invalid):
            with self.subTest(index=index):
                workspace, package = self.make_draft()
                with self.assertRaises(ValueError):
                    review_report_quality(
                        workspace=workspace, report_id="revenue-review",
                        provider=QualityProvider(raw=response), now=REVIEWED,
                    )
                self.assertFalse(package.quality_path.exists())
                self.assertFalse(package.quality_markdown_path.exists())
                self.assertEqual(
                    json.loads(package.manifest_path.read_text())["status"], "draft"
                )

    def test_provider_failure_preserves_draft(self):
        workspace, package = self.make_draft()
        provider = ScriptedProvider(error=ProviderError("offline"))
        with self.assertRaises(ProviderError):
            review_report_quality(
                workspace=workspace, report_id="revenue-review",
                provider=provider, now=REVIEWED,
            )
        self.assertFalse(package.quality_path.exists())
        self.assertEqual(json.loads(package.manifest_path.read_text())["status"], "draft")

    def test_evidence_free_result_stops_at_analyst_notes(self):
        workspace, package = self.make_draft(evidence=False)
        provider = ScriptedProvider([])
        with self.assertRaisesRegex(ValueError, "Analyst Notes only"):
            review_report_quality(
                workspace=workspace, report_id="revenue-review",
                provider=provider, now=REVIEWED,
            )
        self.assertEqual(provider.prompts, [])
        self.assertFalse(package.quality_path.exists())

    def test_human_edited_report_must_be_reconciled_before_review(self):
        workspace, package = self.make_draft()
        package.report_path.write_text(
            package.report_path.read_text(encoding="utf-8") + "\nHuman edit.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "human edits"):
            review_report_quality(
                workspace=workspace, report_id="revenue-review",
                provider=QualityProvider(), now=REVIEWED,
            )
        self.assertFalse(package.quality_path.exists())

    def test_changed_analyst_notes_are_rejected_before_review(self):
        workspace, package = self.make_draft()
        package.analyst_notes_path.write_text(
            package.analyst_notes_path.read_text(encoding="utf-8") + "\nChanged.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "Analyst-Notes.md"):
            review_report_quality(
                workspace=workspace, report_id="revenue-review",
                provider=QualityProvider(), now=REVIEWED,
            )
        self.assertFalse(package.quality_path.exists())

    def test_changed_source_is_reported_without_rewriting_snapshot(self):
        workspace, package = self.make_draft()
        source = workspace.vault_entity_directory / "Economics.md"
        source.write_text(
            source.read_text(encoding="utf-8") + "\n## New Revenue Detail\n\nRevenue changed.\n",
            encoding="utf-8",
        )
        result = review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=QualityProvider(), now=REVIEWED,
        )
        self.assertEqual(result.status, "issues_found")
        self.assertIn("source_corpus_changed", {issue.code for issue in result.issues})
        self.assertFalse(json.loads(package.quality_path.read_text())["checks"]["source_snapshot_current"])

    def test_management_report_rejects_internal_retrieval_language(self):
        workspace, package = self.make_draft()
        manifest = json.loads(package.manifest_path.read_text(encoding="utf-8"))
        draft = load_report_draft(workspace=workspace, report_id="revenue-review")
        draft = replace(
            draft,
            markdown=draft.markdown.replace(
                "## Scope\n", "## Scope\n\nThe local corpus may be incomplete.\n"
            ),
        )
        issues = _deterministic_issues(
            workspace=workspace, report_id="revenue-review", manifest=manifest,
            draft=draft,
            evidence=load_report_evidence(
                workspace=workspace, report_id="revenue-review"
            ),
            reviewed_at=REVIEWED,
        )
        self.assertIn(
            "internal_research_process_in_management_report",
            {issue.code for issue in issues},
        )

    def test_untraced_numeric_value_is_flagged(self):
        workspace, _ = self.make_draft(statement="Documented revenue is 11.")
        result = review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=QualityProvider(), now=REVIEWED,
        )
        self.assertIn("untraced_numeric_value", {issue.code for issue in result.issues})

    def test_missing_report_citations_are_detected_against_claims_ledger(self):
        workspace, package = self.make_draft()
        bundle = json.loads(package.draft_path.read_text(encoding="utf-8"))
        markdown = bundle["markdown"].replace("[^E-001]", "")
        package.report_path.write_text(markdown, encoding="utf-8")
        # Hash the materialized representation because Windows text-mode newline
        # handling may normalize the final newline sequence.
        markdown = package.report_path.read_bytes().decode("utf-8")
        bundle["markdown"] = markdown
        bundle["markdown_sha256"] = content_sha256(markdown)
        package.draft_path.write_text(
            json.dumps(bundle, indent=2) + "\n", encoding="utf-8"
        )
        self.assertFalse(
            load_report_draft(
                workspace=workspace, report_id="revenue-review"
            ).modified
        )
        result = review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=QualityProvider(), now=REVIEWED,
        )
        codes = {issue.code for issue in result.issues}
        self.assertIn("missing_inline_citation", codes)
        self.assertIn("missing_evidence_note", codes)

    def test_semantic_review_batches_remain_bounded(self):
        workspace, package = self.make_draft()
        from definalyzer import report_quality
        draft = load_report_draft(
            workspace=workspace, report_id="revenue-review"
        )
        evidence = json.loads(package.evidence_path.read_text(encoding="utf-8"))
        cases = report_quality._audit_cases(
            draft.claims["assertions"], evidence["evidence"]
        )
        single_case_limit = max(
            len(json.dumps([case], ensure_ascii=False)) for case in cases
        ) + 50
        provider = QualityProvider()
        with patch.object(
            report_quality, "MAX_AUDIT_DATA_CHARACTERS", single_case_limit
        ):
            result = review_report_quality(
                workspace=workspace, report_id="revenue-review",
                provider=provider, now=REVIEWED,
            )
        self.assertEqual(result.status, "passed")
        self.assertGreater(len(provider.prompts), 1)
        self.assertTrue(
            all(len(prompt) <= MAX_PROMPT_CHARACTERS for prompt, _ in provider.prompts)
        )

    def test_full_review_recommendation_requires_stronger_source_class(self):
        workspace, _ = self.make_draft(mode="full_review")
        result = review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=QualityProvider(), now=REVIEWED,
        )
        self.assertIn(
            "recommendation_lacks_primary_or_deterministic_support",
            {issue.code for issue in result.issues},
        )

    def test_missing_quality_markdown_can_be_recovered_from_committed_json(self):
        workspace, package = self.make_draft()
        review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=QualityProvider(), now=REVIEWED,
        )
        package.quality_markdown_path.unlink()
        with self.assertRaises(FileNotFoundError):
            load_report_quality(workspace=workspace, report_id="revenue-review")
        restored = load_report_quality(
            workspace=workspace, report_id="revenue-review", repair_missing=True
        )
        self.assertEqual(restored.status, "passed")
        self.assertTrue(package.quality_markdown_path.exists())

    def test_tampered_quality_markdown_and_json_are_rejected(self):
        workspace, package = self.make_draft()
        review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=QualityProvider(), now=REVIEWED,
        )
        original = package.quality_markdown_path.read_text(encoding="utf-8")
        package.quality_markdown_path.write_text(original + "tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed outside"):
            load_report_quality(workspace=workspace, report_id="revenue-review")
        package.quality_markdown_path.write_text(original, encoding="utf-8")
        document = json.loads(package.quality_path.read_text())
        document["provider"] = "tampered"
        package.quality_path.write_text(json.dumps(document), encoding="utf-8")
        # The provider label is provenance, but it is deliberately not trusted as a
        # security boundary. A content digest edit must always be detected.
        document["markdown_sha256"] = "0" * 64
        package.quality_path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "digest"):
            load_report_quality(workspace=workspace, report_id="revenue-review")

    def test_review_is_immutable_and_lock_prevents_concurrent_run(self):
        workspace, package = self.make_draft()
        review_report_quality(
            workspace=workspace, report_id="revenue-review",
            provider=QualityProvider(), now=REVIEWED,
        )
        with self.assertRaises(ValueError):
            review_report_quality(
                workspace=workspace, report_id="revenue-review",
                provider=QualityProvider(), now=REVIEWED,
            )
        workspace2, package2 = self.make_draft()
        lock = package2.directory / ".quality.lock"
        lock.write_text("locked", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            review_report_quality(
                workspace=workspace2, report_id="revenue-review",
                provider=QualityProvider(), now=REVIEWED,
            )

    def test_interrupted_markdown_materialization_is_recoverable(self):
        workspace, package = self.make_draft()
        from definalyzer import report_quality

        original = report_quality._atomic_text

        def fail_quality_markdown(path, text, *, exclusive=False):
            if path == package.quality_markdown_path:
                raise OSError("simulated interruption")
            return original(path, text, exclusive=exclusive)

        with patch.object(report_quality, "_atomic_text", fail_quality_markdown):
            with self.assertRaises(OSError):
                review_report_quality(
                    workspace=workspace, report_id="revenue-review",
                    provider=QualityProvider(), now=REVIEWED,
                )
        self.assertEqual(
            json.loads(package.manifest_path.read_text())["status"], "quality_reviewed"
        )
        self.assertTrue(package.quality_path.exists())
        self.assertFalse(package.quality_markdown_path.exists())
        load_report_quality(
            workspace=workspace, report_id="revenue-review", repair_missing=True
        )
        self.assertTrue(package.quality_markdown_path.exists())

    def test_review_timestamp_cannot_predate_generation(self):
        workspace, package = self.make_draft()
        with self.assertRaisesRegex(ValueError, "predate"):
            review_report_quality(
                workspace=workspace, report_id="revenue-review",
                provider=QualityProvider(), now="2026-09-03T23:59:59+00:00",
            )
        self.assertFalse(package.quality_path.exists())


if __name__ == "__main__":
    unittest.main()
