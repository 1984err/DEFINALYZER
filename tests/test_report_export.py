import json
import re
import tempfile
import unittest
from pathlib import Path

from definalyzer.providers import ProviderResponse
from definalyzer.report_contract import ReportRequest, initialize_report_package
from definalyzer.report_evidence import load_report_evidence, prepare_report_evidence
from definalyzer.report_export import (
    ChartRequest, _build_chart, _markdown_to_html, _publication_markdown,
    export_final_report,
)
from definalyzer.report_generation import generate_report_draft
from definalyzer.report_lifecycle import finalize_report
from definalyzer.report_presentation import management_report_markdown
from definalyzer.report_quality import review_report_quality
from definalyzer.workspace import WorkspaceManager


STARTED = "2026-09-04T00:00:00+00:00"
REVIEWED = "2026-09-04T01:00:00+00:00"
FINALIZED = "2026-09-04T02:00:00+00:00"
EXPORTED = "2026-09-04T03:00:00+00:00"


class ScriptedProvider:
    name = "scripted"

    def __init__(self, responses):
        self.responses = list(responses)

    def generate(self, prompt, *, working_directory):
        if not self.responses:
            raise AssertionError("Unexpected provider call")
        return ProviderResponse(
            text=self.responses.pop(0), provider=self.name, command=("fake",)
        )


class SupportingQualityProvider:
    name = "quality-scripted"

    def generate(self, prompt, *, working_directory):
        match = re.search(
            r"<UNTRUSTED_AUDIT_CASES>\n(.*?)\n</UNTRUSTED_AUDIT_CASES>",
            prompt, re.S,
        )
        cases = json.loads(match.group(1))
        return ProviderResponse(text=json.dumps({"assessments": [{
            "case_id": case["case_id"],
            "evidence_assessments": [{
                "evidence_id": item["evidence_id"], "relationship": "supports",
                "note": "The exact saved fields support the qualified statement.",
            } for item in case["evidence"]],
            "reasoning_assessment": "reasonable",
            "reasoning_note": "The report preserves the point-in-time limitation.",
        } for case in cases]}), provider=self.name, command=("quality",))


def finding(evidence_id):
    return json.dumps({"findings": [{
        "category": "economics", "assertion_type": "collected_evidence",
        "statement": "The saved snapshot reports circulating and maximum supply values.",
        "rationale": "The structured snapshot contains both numeric fields.",
        "evidence_ids": [evidence_id], "support": "directly_supported",
        "limitations": ["The values are a dated point-in-time snapshot."],
    }]})


def plan(evidence_id):
    return json.dumps({
        "executive_finding_ids": ["F-01-01"], "sections": [],
        "conclusion": {
            "stance": "answer",
            "statement": "The saved evidence provides a dated supply comparison.",
            "rationale": "Both requested values occur in the same structured snapshot.",
            "evidence_ids": [evidence_id], "support": "directly_supported",
            "limitations": ["No live refresh was performed."],
            "what_would_change_finding_ids": [],
        },
    })


class ReportExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        manager = WorkspaceManager(Path(self.temporary.name) / "output")
        self.workspace = manager.create_project(name="Example Token", entity_type="token")

    def make_report(self, *, finalize=True):
        package = initialize_report_package(
            workspace=self.workspace,
            request=ReportRequest(
                title="Supply Review", mode="question",
                question="What are circulating supply and max supply?",
            ),
            now=STARTED,
        )
        market = self.workspace.registry_directory / "market-data"
        market.mkdir(parents=True, exist_ok=True)
        (market / "snapshot.json").write_text(json.dumps({
            "provider_updated_at": STARTED,
            "source_url": "https://example.test/asset",
            "supply": {"circulating": 450_000_000, "maximum": 1_000_000_000},
        }, indent=2), encoding="utf-8")
        prepare_report_evidence(
            workspace=self.workspace, report_id="supply-review", now=STARTED
        )
        evidence = load_report_evidence(
            workspace=self.workspace, report_id="supply-review"
        )
        evidence_id = next(
            row["evidence_id"] for row in evidence["evidence"]
            if row["source_type"] == "market_data"
        )
        generate_report_draft(
            workspace=self.workspace, report_id="supply-review",
            provider=ScriptedProvider([finding(evidence_id), plan(evidence_id)]),
            now=STARTED,
        )
        if finalize:
            result = review_report_quality(
                workspace=self.workspace, report_id="supply-review",
                provider=SupportingQualityProvider(), now=REVIEWED,
            )
            self.assertEqual(result.status, "passed")
            finalize_report(
                workspace=self.workspace, report_id="supply-review",
                human_approved=True, now=FINALIZED,
            )
        return package, evidence, evidence_id

    def chart_request(self, evidence_id):
        return ChartRequest.from_fields(
            title="Supply Snapshot", evidence_id=evidence_id,
            fields={"Circulating": "supply.circulating", "Maximum": "supply.maximum"},
            unit="tokens",
        )

    def test_all_formats_export_from_exact_final_revision(self):
        _, _, evidence_id = self.make_report()
        result = export_final_report(
            workspace=self.workspace, report_id="supply-review",
            charts=[self.chart_request(evidence_id)], now=EXPORTED,
        )
        self.assertTrue(result.markdown_path.exists())
        self.assertTrue(result.html_path.exists())
        self.assertTrue(result.pdf_path.exists())
        self.assertTrue(result.pdf_path.read_bytes().startswith(b"%PDF"))
        publication = result.markdown_path.read_text(encoding="utf-8")
        self.assertNotIn("Draft generated", publication)
        self.assertIn("- Finalized: September 4, 2026", publication)
        self.assertIn("## Data Visuals", publication)
        self.assertIn("Direct JSON field extraction; no arithmetic.", publication)
        document = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(document["formats"], ["markdown", "html", "pdf"])
        self.assertEqual(document["source"]["finalized_at"], FINALIZED)
        self.assertEqual(document["charts"][0]["evidence_id"], evidence_id)
        self.assertIn("Analyst-Notes.md", document["files"])
        self.assertIn("Answer Readiness", (result.directory / "Analyst-Notes.md").read_text(encoding="utf-8"))
        for relative, digest in document["files"].items():
            import hashlib
            self.assertEqual(
                hashlib.sha256((result.directory / relative).read_bytes()).hexdigest(),
                digest,
            )

    def test_export_refuses_nonfinal_report(self):
        self.make_report(finalize=False)
        with self.assertRaisesRegex(ValueError, "not final"):
            export_final_report(
                workspace=self.workspace, report_id="supply-review",
                formats=("markdown",), now=EXPORTED,
            )

    def test_export_is_immutable_and_refuses_overwrite(self):
        self.make_report()
        export_final_report(
            workspace=self.workspace, report_id="supply-review",
            formats=("markdown",), now=EXPORTED,
        )
        with self.assertRaises(FileExistsError):
            export_final_report(
                workspace=self.workspace, report_id="supply-review",
                formats=("markdown",), now=EXPORTED,
            )

    def test_export_timestamp_cannot_predate_finalization(self):
        self.make_report()
        with self.assertRaisesRegex(ValueError, "precede"):
            export_final_report(
                workspace=self.workspace, report_id="supply-review",
                formats=("markdown",), now=STARTED,
            )

    def test_export_without_chart_invents_no_visual(self):
        self.make_report()
        result = export_final_report(
            workspace=self.workspace, report_id="supply-review",
            formats=("markdown", "html"), now=EXPORTED,
        )
        self.assertNotIn("Data Visuals", result.markdown_path.read_text(encoding="utf-8"))
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["charts"], [])
        self.assertEqual(list((result.directory / "Assets").iterdir()), [])

    def test_chart_values_are_read_from_evidence_not_supplied(self):
        _, evidence, evidence_id = self.make_report(finalize=False)
        chart = _build_chart(
            self.chart_request(evidence_id), evidence=evidence, sequence=1
        )
        self.assertEqual(
            [point["value"] for point in chart["points"]],
            [450_000_000, 1_000_000_000],
        )
        self.assertEqual(chart["evidence_content_sha256"], evidence["evidence"][0]["content_sha256"])

    def test_chart_refuses_undated_unstructured_or_missing_fields(self):
        _, evidence, evidence_id = self.make_report(finalize=False)
        undated = json.loads(json.dumps(evidence))
        undated["evidence"][0]["as_of"] = None
        with self.assertRaisesRegex(ValueError, "dated evidence"):
            _build_chart(self.chart_request(evidence_id), evidence=undated, sequence=1)
        wrong_type = json.loads(json.dumps(evidence))
        wrong_type["evidence"][0]["source_type"] = "research"
        with self.assertRaisesRegex(ValueError, "structured"):
            _build_chart(self.chart_request(evidence_id), evidence=wrong_type, sequence=1)
        missing = ChartRequest.from_fields(
            title="Bad", evidence_id=evidence_id,
            fields={"Unknown": "supply.unknown"}, unit="tokens",
        )
        with self.assertRaisesRegex(ValueError, "not found"):
            _build_chart(missing, evidence=evidence, sequence=1)

    def test_chart_refuses_boolean_and_nonfinite_values(self):
        _, evidence, evidence_id = self.make_report(finalize=False)
        for value, expected in ((True, "not numeric"), (float("inf"), "not finite")):
            changed = json.loads(json.dumps(evidence))
            changed["evidence"][0]["excerpt"] = json.dumps({
                "provider_updated_at": STARTED, "supply": {"circulating": value},
            })
            request = ChartRequest.from_fields(
                title="Bad", evidence_id=evidence_id,
                fields={"Value": "supply.circulating"}, unit="tokens",
            )
            with self.assertRaisesRegex(ValueError, expected):
                _build_chart(request, evidence=changed, sequence=1)

    def test_html_escapes_raw_markup_and_preserves_citations(self):
        rendered = _markdown_to_html(
            "# Review\n\n<script>alert(1)</script> [^E-001]\n\n[^E-001]: saved source\n"
        )
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn('href="#note-E-001"', rendered)

    def test_publication_uses_reader_friendly_numbered_sources(self):
        publication = _publication_markdown(
            "# Review\n\nClaim. [^E-019] [^E-004]\n\n"
            "## Evidence Limitations\n\nLimited.\n\n## Evidence Notes\n\n"
            "[^E-004]: second source\n[^E-019]: first source\n",
            finalized_at=FINALIZED, charts=(),
        )
        self.assertIn("Claim. [^1] [^2]", publication)
        self.assertIn("[^1]: first source", publication)
        self.assertIn("[^2]: second source", publication)
        self.assertIn("## Research Boundaries", publication)
        self.assertIn("## Sources", publication)
        self.assertNotIn("E-019", publication)

    def test_publication_sources_hide_internal_workspace_paths(self):
        publication = _publication_markdown(
            "# Review\n\nClaim. [^E-001]\n\n## Evidence Notes\n\n"
            "[^E-001]: vault/Protocols/Example/Revenue-Model.md; "
            "Fees and Revenue; lines 12-19. Saved evidence excerpt; "
            "inclusion does not independently verify the source claim.\n",
            finalized_at=FINALIZED, charts=(),
        )
        self.assertNotIn("vault/", publication)
        self.assertNotIn("Saved evidence excerpt", publication)
        self.assertIn("Revenue Model - Fees and Revenue, lines 12-19.", publication)

    def test_publication_hides_variable_context_budget_jargon(self):
        publication = management_report_markdown(
            "# Review\n\n## Evidence Limitations\n"
            "- Some material was excluded. Inspect omission counts and the source inventory before drafting.\n"
            "- Excluded material: context budget (52).\n\n## Evidence Notes\n"
        )
        self.assertNotIn("context budget", publication)
        self.assertNotIn("source inventory", publication)
        self.assertIn("bounded selection of saved research", publication)

    def test_format_validation_precedes_file_creation(self):
        package, _, _ = self.make_report()
        with self.assertRaisesRegex(ValueError, "Export formats"):
            export_final_report(
                workspace=self.workspace, report_id="supply-review",
                formats=("docx",), now=EXPORTED,
            )
        self.assertEqual(list(package.exports_directory.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
