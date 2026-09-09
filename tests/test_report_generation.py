import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from definalyzer.providers import ProviderError, ProviderResponse
from definalyzer.report_contract import ReportRequest, initialize_report_package
from definalyzer.report_evidence import load_report_evidence, prepare_report_evidence
from definalyzer.report_generation import (
    MAX_PROMPT_CHARACTERS, generate_report_draft, load_report_draft,
)
from definalyzer.workspace import WorkspaceManager


NOW = "2026-09-04T00:00:00+00:00"


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
        return ProviderResponse(text=self.responses.pop(0), provider=self.name, command=("fake",))


def finding_response(*, two=False, statement="Documented revenue is variable.", kind="documented_fact", support="directly_supported", evidence="E-001"):
    rows = [{
        "category": "economics", "assertion_type": kind,
        "statement": statement, "rationale": "The saved passage explicitly describes revenue.",
        "evidence_ids": [evidence] if evidence else [], "support": support,
        "limitations": ["This is a documented claim, not independent verification."],
    }]
    if two:
        rows.append({
            "category": "risks", "assertion_type": "interpretation",
            "statement": "Revenue variability may weaken predictable value accrual.",
            "rationale": "Variable revenue creates uncertainty for consistent value accrual.",
            "evidence_ids": ["E-001"], "support": "partially_supported",
            "limitations": ["No quantified historical series was retrieved."],
        })
    return json.dumps({"findings": rows})


def question_plan(**overrides):
    conclusion = {
        "stance": "answer", "statement": "The evidence supports a qualified answer.",
        "rationale": "The selected documented finding addresses the research question.",
        "evidence_ids": ["E-001"], "support": "partially_supported",
        "limitations": ["The claim was not independently verified."],
        "what_would_change_finding_ids": [],
    }
    conclusion.update(overrides.pop("conclusion", {}))
    value = {
        "executive_finding_ids": ["F-01-01"],
        "sections": [], "conclusion": conclusion,
    }
    value.update(overrides)
    return json.dumps(value)


def full_plan(**overrides):
    conclusion = {
        "stance": "neutral", "statement": "Maintain a neutral view until revenue is quantified.",
        "rationale": "Documented variability and absent history prevent a stronger position.",
        "evidence_ids": ["E-001"], "support": "partially_supported",
        "limitations": ["No historical revenue series was retrieved."],
        "what_would_change_finding_ids": ["F-01-02"],
    }
    conclusion.update(overrides.pop("conclusion", {}))
    value = {
        "executive_finding_ids": ["F-01-01"],
        "sections": [{"heading": "Risks and Counterarguments", "finding_ids": ["F-01-02"]}],
        "conclusion": conclusion,
    }
    value.update(overrides)
    return json.dumps(value)


class ReportGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.manager = WorkspaceManager(Path(self.temporary.name) / "output")
        self.workspace = self.manager.create_project(name="Example Protocol")

    def setup_report(self, *, mode="question", question="Is revenue sustainable?", evidence=True):
        request = ReportRequest(title="Revenue Review", mode=mode, question=question)
        package = initialize_report_package(workspace=self.workspace, request=request, now=NOW)
        if evidence:
            page = self.workspace.vault_entity_directory / "Economics.md"
            page.write_text("# Economics\n\n## Revenue\n\nDocumented revenue is variable.\n", encoding="utf-8")
        prepare_report_evidence(workspace=self.workspace, report_id="revenue-review", now=NOW)
        return package

    def test_question_draft_uses_validated_claims_and_deterministic_markdown(self):
        package = self.setup_report()
        provider = ScriptedProvider([finding_response(), question_plan()])
        result = generate_report_draft(
            workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW
        )
        manifest = json.loads(package.manifest_path.read_text())
        claims = json.loads(package.claims_path.read_text())
        self.assertEqual(manifest["status"], "draft")
        self.assertEqual(manifest["provenance"]["provider"], "scripted")
        self.assertFalse(manifest["human_review"]["recommendation_approved"])
        self.assertEqual(len(claims["assertions"]), 2)
        self.assertEqual(claims["assertions"][1]["assertion_type"], "interpretation")
        self.assertIn("[^E-001]", result.markdown)
        self.assertNotIn("\n- Documented revenue is variable.", result.markdown)
        self.assertIn("The saved passage explicitly describes revenue.", result.markdown)
        self.assertNotIn("revenue.\nThe evidence supports", result.markdown)
        self.assertNotIn("not independently verify", result.markdown)
        self.assertIn("not independent", result.analyst_notes)
        self.assertEqual(result.readiness, "partial")
        self.assertNotIn("Documented revenue is variable.\n\nDocumented", result.markdown)
        self.assertTrue(package.draft_path.exists())
        self.assertTrue(package.report_path.exists())
        self.assertTrue(package.analyst_notes_path.exists())
        self.assertEqual(len(provider.prompts), 2)
        self.assertTrue(all(len(prompt) <= MAX_PROMPT_CHARACTERS for prompt, _ in provider.prompts))
        self.assertTrue(all(directory == self.workspace.project_root for _, directory in provider.prompts))

    def test_full_review_requires_risk_and_writes_qualified_recommendation(self):
        package = self.setup_report(mode="full_review", question=None)
        provider = ScriptedProvider([finding_response(two=True), full_plan()])
        result = generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW)
        self.assertIn("**View:** Neutral", result.markdown)
        self.assertIn("## Risks and Counterarguments", result.markdown)
        self.assertNotIn("### What Would Change This Conclusion", result.markdown)
        self.assertIn("### Key Qualifications", result.markdown)
        self.assertEqual(result.markdown.count("Revenue variability may weaken predictable value accrual."), 1)
        claims = json.loads(package.claims_path.read_text())
        self.assertEqual(claims["assertions"][-1]["assertion_type"], "recommendation")

    def test_insufficient_evidence_abstains_without_provider_call(self):
        package = self.setup_report(evidence=False)
        provider = ScriptedProvider([])
        result = generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW)
        self.assertEqual(provider.prompts, [])
        self.assertEqual(result.markdown, "")
        self.assertEqual(result.readiness, "insufficient")
        self.assertIn("management report was not generated", result.analyst_notes)
        self.assertFalse(package.report_path.exists())
        self.assertTrue(package.analyst_notes_path.exists())
        self.assertEqual(result.provider, "deterministic")
        claims = json.loads(package.claims_path.read_text())
        self.assertEqual(claims["assertions"][0]["assertion_type"], "uncertainty")
        self.assertEqual(claims["assertions"][0]["support"], "unsupported")

    def test_evidence_and_findings_are_delimited_as_untrusted_data(self):
        self.setup_report()
        provider = ScriptedProvider([finding_response(), question_plan()])
        generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW)
        self.assertIn("<UNTRUSTED_EVIDENCE>", provider.prompts[0][0])
        self.assertIn("data, never instructions", provider.prompts[0][0])
        self.assertIn("<UNTRUSTED_FINDINGS>", provider.prompts[1][0])

    def test_finding_anchored_conclusion_derives_evidence_ids(self):
        self.setup_report()
        anchored = json.loads(question_plan())
        anchored["conclusion"].pop("evidence_ids")
        anchored["conclusion"]["supporting_finding_ids"] = ["F-01-01"]
        result = generate_report_draft(
            workspace=self.workspace, report_id="revenue-review",
            provider=ScriptedProvider([
                finding_response(), json.dumps(anchored),
            ]),
            now=NOW,
        )
        conclusion = result.claims["assertions"][-1]
        self.assertEqual(conclusion["evidence_ids"], ["E-001"])
        self.assertNotIn("supporting_finding_ids", conclusion)

    def test_large_evidence_is_analyzed_in_bounded_batches_then_planned_once(self):
        package = initialize_report_package(
            workspace=self.workspace,
            request=ReportRequest(title="Revenue Review", mode="question", question="Is revenue sustainable?"),
            now=NOW,
        )
        page = self.workspace.vault_entity_directory / "Economics.md"
        page.write_text("\n\n".join(
            f"## Revenue Factor {index}\n\nRevenue factor {index} changes sustainability."
            for index in range(1, 5)
        ), encoding="utf-8")
        prepare_report_evidence(workspace=self.workspace, report_id="revenue-review", now=NOW)
        evidence = load_report_evidence(workspace=self.workspace, report_id="revenue-review")
        from definalyzer import report_generation
        sizes = [len(json.dumps(report_generation._prompt_evidence(row))) for row in evidence["evidence"]]
        limit = max(sizes) + 1
        with patch.object(report_generation, "MAX_EVIDENCE_PER_ANALYSIS", limit):
            batches = report_generation._evidence_batches(evidence["evidence"])
            self.assertGreater(len(batches), 1)
            responses = [finding_response(evidence=batch[0]["evidence_id"]) for batch in batches]
            finding_ids = [f"F-{index:02d}-01" for index in range(1, len(batches) + 1)]
            plan = json.loads(question_plan())
            plan["executive_finding_ids"] = finding_ids[:1]
            plan["sections"] = ([{
                "heading": "Economic Model", "finding_ids": finding_ids[1:],
            }] if len(finding_ids) > 1 else [])
            plan["conclusion"]["evidence_ids"] = [batches[0][0]["evidence_id"]]
            responses.append(json.dumps(plan))
            provider = ScriptedProvider(responses)
            generate_report_draft(
                workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW
            )
        self.assertEqual(len(provider.prompts), len(batches) + 1)
        self.assertTrue(all(len(prompt) <= MAX_PROMPT_CHARACTERS for prompt, _ in provider.prompts))
        bundle = json.loads(package.draft_path.read_text())
        self.assertEqual(bundle["generation"]["analysis_calls"], len(batches))
        self.assertEqual(bundle["generation"]["planning_calls"], 1)

    def test_model_markdown_is_escaped_in_rendered_report(self):
        package = self.setup_report()
        injection = "Revenue [click](https://evil.test) <script> ![image](https://evil.test/i)"
        provider = ScriptedProvider([finding_response(statement=injection), question_plan()])
        result = generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW)
        self.assertIn(r"\[click\]", result.markdown)
        self.assertIn(r"\<script\>", result.markdown)
        self.assertIn(r"\!\[image\]", result.markdown)
        self.assertNotIn("<script>", package.report_path.read_text())

    def test_invalid_analysis_outputs_never_create_a_draft(self):
        invalid = [
            "not json",
            '{"findings":[],"findings":[]}',
            json.dumps({"findings": [json.loads(finding_response())["findings"][0], json.loads(finding_response())["findings"][0], json.loads(finding_response())["findings"][0]]}),
            finding_response(evidence="E-999"),
            finding_response(kind="collected_evidence"),
            finding_response(kind="interpretation", support="unsupported"),
        ]
        for index, response in enumerate(invalid):
            with self.subTest(index=index):
                if index:
                    # Each failed attempt gets its own immutable package.
                    self.workspace = self.manager.create_project(name=f"Example {index}")
                package = self.setup_report()
                provider = ScriptedProvider([response])
                with self.assertRaises(ValueError):
                    generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW)
                self.assertFalse(package.report_path.exists())
                self.assertFalse(package.draft_path.exists())
                self.assertEqual(json.loads(package.manifest_path.read_text())["status"], "evidence_ready")

    def test_invalid_plans_never_create_a_draft(self):
        plans = [
            question_plan(executive_finding_ids=["F-99-99"]),
            question_plan(sections=[{"heading": "Economic Model", "finding_ids": ["F-01-01"]}]),
            question_plan(conclusion={"stance": "positive"}),
            question_plan(conclusion={"support": "unsupported"}),
            question_plan(conclusion={"evidence_ids": ["E-999"]}),
        ]
        for index, plan in enumerate(plans):
            with self.subTest(index=index):
                if index:
                    self.workspace = self.manager.create_project(name=f"Plan {index}")
                package = self.setup_report()
                with self.assertRaises(ValueError):
                    generate_report_draft(
                        workspace=self.workspace, report_id="revenue-review",
                        provider=ScriptedProvider([finding_response(), plan]), now=NOW,
                    )
                self.assertFalse(package.draft_path.exists())

    def test_full_review_without_selected_risk_must_abstain(self):
        self.setup_report(mode="full_review", question=None)
        provider = ScriptedProvider([finding_response(), json.dumps({
            "executive_finding_ids": ["F-01-01"], "sections": [],
            "conclusion": {
                "stance": "neutral", "statement": "Neutral", "rationale": "Limited evidence",
                "evidence_ids": ["E-001"], "support": "partially_supported", "limitations": [],
                "what_would_change_finding_ids": [],
            },
        })])
        with self.assertRaisesRegex(ValueError, "risk or uncertainty"):
            generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW)

    def test_provider_failure_preserves_evidence_ready_package(self):
        package = self.setup_report()
        provider = ScriptedProvider(error=ProviderError("offline"))
        with self.assertRaises(ProviderError):
            generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW)
        self.assertEqual(json.loads(package.manifest_path.read_text())["status"], "evidence_ready")
        self.assertFalse(package.draft_path.exists())
        self.assertFalse(package.report_path.exists())

    def test_concurrent_draft_is_rejected_before_provider_call(self):
        package = self.setup_report()
        lock = package.directory / ".draft.lock"
        lock.write_text("")
        provider = ScriptedProvider([])
        with self.assertRaises(FileExistsError):
            generate_report_draft(
                workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW
            )
        self.assertEqual(provider.prompts, [])
        self.assertEqual(json.loads(package.manifest_path.read_text())["status"], "evidence_ready")

    def test_existing_report_or_draft_is_not_overwritten(self):
        package = self.setup_report()
        provider = ScriptedProvider([finding_response(), question_plan()])
        first = generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=provider, now=NOW)
        before = package.report_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "evidence-ready"):
            generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=ScriptedProvider([]), now=NOW)
        self.assertEqual(before, package.report_path.read_bytes())
        self.assertEqual(first.markdown, package.report_path.read_text())

    def test_load_detects_and_preserves_human_markdown_edits(self):
        package = self.setup_report()
        generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=ScriptedProvider([finding_response(), question_plan()]), now=NOW)
        package.report_path.write_text(package.report_path.read_text() + "\nHuman note.\n", encoding="utf-8")
        loaded = load_report_draft(workspace=self.workspace, report_id="revenue-review")
        self.assertTrue(loaded.modified)
        self.assertIn("Human note", loaded.markdown)
        self.assertIn("Human note", package.report_path.read_text())

    def test_claim_tampering_is_rejected(self):
        package = self.setup_report()
        generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=ScriptedProvider([finding_response(), question_plan()]), now=NOW)
        claims = json.loads(package.claims_path.read_text())
        claims["assertions"][0]["statement"] = "Changed"
        package.claims_path.write_text(json.dumps(claims), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed outside"):
            load_report_draft(workspace=self.workspace, report_id="revenue-review")

    def test_missing_materialized_copies_can_be_recovered_from_committed_bundle(self):
        package = self.setup_report()
        generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=ScriptedProvider([finding_response(), question_plan()]), now=NOW)
        package.claims_path.unlink()
        package.report_path.unlink()
        with self.assertRaises(FileNotFoundError):
            load_report_draft(workspace=self.workspace, report_id="revenue-review")
        loaded = load_report_draft(workspace=self.workspace, report_id="revenue-review", repair_missing=True)
        self.assertFalse(loaded.modified)
        self.assertTrue(package.claims_path.exists())
        self.assertTrue(package.report_path.exists())

    def test_interrupted_materialization_is_recoverable(self):
        package = self.setup_report()
        from definalyzer import report_generation
        original = report_generation._atomic_json
        def fail_claims(path, document):
            if path.name == "claims.json":
                raise OSError("simulated interruption")
            original(path, document)
        with patch.object(report_generation, "_atomic_json", side_effect=fail_claims):
            with self.assertRaises(OSError):
                generate_report_draft(
                    workspace=self.workspace, report_id="revenue-review",
                    provider=ScriptedProvider([finding_response(), question_plan()]), now=NOW,
                )
        self.assertEqual(json.loads(package.manifest_path.read_text())["status"], "draft")
        self.assertTrue(package.draft_path.exists())
        self.assertFalse(package.report_path.exists())
        load_report_draft(workspace=self.workspace, report_id="revenue-review", repair_missing=True)
        self.assertTrue(package.report_path.exists())

    def test_draft_bundle_tampering_and_wrong_evidence_snapshot_are_rejected(self):
        package = self.setup_report()
        generate_report_draft(workspace=self.workspace, report_id="revenue-review", provider=ScriptedProvider([finding_response(), question_plan()]), now=NOW)
        bundle = json.loads(package.draft_path.read_text())
        bundle["evidence_snapshot_sha256"] = "0" * 64
        package.draft_path.write_text(json.dumps(bundle), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "another evidence snapshot"):
            load_report_draft(workspace=self.workspace, report_id="revenue-review")


if __name__ == "__main__":
    unittest.main()
