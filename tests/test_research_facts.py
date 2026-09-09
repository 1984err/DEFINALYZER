import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from definalyzer.workspace import WorkspaceManager
from definalyzer.providers import ProviderResponse
from definalyzer.research_scope import prepare_scope, _hash
from definalyzer import research_facts as rf


class FactFixture:
    """Separate extraction/check boundaries, with controllable failures."""
    name = "fixture"

    def __init__(self, reject=False, mutate=None, conflicts=False):
        self.calls = []
        self.reject = reject
        self.mutate = mutate
        self.conflicts = conflicts

    def generate(self, prompt, **kwargs):
        self.calls.append(prompt)
        if prompt.startswith("# Original-source fact extraction"):
            subjects = json.loads(prompt.split("SUBJECTS:\n")[1].split("\nBLOCKS:")[0])
            blocks = json.loads(prompt.split("BLOCKS:\n")[1].split("\nREPAIRS:")[0])
            repairs = json.loads(prompt.split("validation.\n")[1]) if "\nREPAIRS:" in prompt else []
            facts = []
            for block in blocks:
                sid = next(iter(subjects))
                statement = block["text"].splitlines()[-1]
                topic = "revenue-model" if "fee" in statement.lower() else "architecture"
                quantity = re.search(r"\d+%", statement)
                fact = {"kind": "documented_claim", "subject_id": sid, "topic": topic,
                        "predicate": "fee" if quantity else "execution", "statement": statement,
                        "applicability": {"period": "2020" if "2020" in statement else "2025" if "2025" in statement else None},
                        "quantities": [{"value": quantity[0][:-1], "unit": "%", "literal": quantity[0]}] if quantity else [],
                        "question_ids": [topic + ".1"],
                        "evidence": [{"block_id": block["block_id"], "quote": statement}]}
                if repairs:
                    fact["repair_of"] = repairs[0]["repair_id"]
                if self.mutate:
                    self.mutate(fact)
                facts.append(fact)
            response = {"facts": facts, "gaps": []}
        elif prompt.startswith("# Independent original-source support check"):
            facts = json.loads(prompt.split("PROPOSALS:\n")[1].split("\nORIGINAL BLOCKS:")[0])
            response = {"checks": [{"proposal_id": f["proposal_id"], "status": "needs_qualification" if self.reject else "supported",
                         "subject_match": not self.reject, "context_preserved": not self.reject,
                         "reason": "Original subject and conditions were checked.", "evidence": f["evidence"]} for f in facts]}
        elif prompt.startswith("# Independent documentation conflict check"):
            claims = json.loads(prompt.split("CLAIMS:\n")[1])
            response = {"conflicts": [{"revisions": [c["revision"] for c in claims[:2]],
                         "reason": "The documents disagree about the same permission.",
                         "quotes": [c["original_context"][0].splitlines()[-1] for c in claims[:2]]}] if self.conflicts else []}
        else:
            raise AssertionError("Unexpected task boundary")
        return ProviderResponse(json.dumps(response), self.name, ())


class ResearchFactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manager = WorkspaceManager(Path(self.temp.name) / "output")
        self.workspace = self.manager.create_project(name="Northstar", entity_type="chain")

    def source(self, text, name="core.md"):
        path = self.workspace.sources_directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def collect(self, provider=None):
        prepare_scope(self.workspace)
        return rf.collect_facts(self.workspace, provider=provider or FactFixture())

    def proposal(self):
        self.source("# Northstar\nNorthstar charges a 2% fee only on withdrawals.\n")
        doc, _ = self.collect()
        scope = rf.load_scope(self.workspace)
        return copy.deepcopy(doc["facts"][0]), {b["block_id"]: b for b in scope["blocks"]}, rf._subjects(scope)

    def test_original_passages_checks_and_immutable_history_resolve(self):
        fact, _, _ = self.proposal()
        detail = rf.fact_detail(self.workspace, fact["revision"])
        self.assertIn("only on withdrawals", detail["evidence"][0]["context"])
        self.assertEqual(detail["support_check"]["status"], "supported")
        self.assertEqual(detail["support_check"]["verification"], "not_independently_verified")
        with self.assertRaises(ValueError):
            rf.fact_detail(self.workspace, "../current")
        snapshot = self.workspace.project_root / "scope/snapshots" / (fact["evidence"][0]["snapshot_id"] + ".md")
        snapshot.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "integrity"):
            rf.fact_detail(self.workspace, fact["revision"])

    def test_wrong_subject_made_up_numbers_units_and_applicability_rejected(self):
        fact, blocks, subjects = self.proposal()
        for update in ({"kind": "observed_value"}, {"kind": "analyst_statement"}, {"subject_id": "other"},
                       {"statement": "Northstar charges a 3% fee."}, {"applicability": {"network": "mainnet"}},
                       {"quantities": [{"value": "2", "unit": "USD", "literal": "2%"}]},
                       {"question_ids": ["security.1"]}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                rf.validate_proposal(self.workspace, {**fact, **update}, blocks=blocks, subjects=subjects)
        sid = "b" * 64
        with self.assertRaisesRegex(ValueError, "absent"):
            rf.validate_proposal(self.workspace, {**fact, "subject_id": sid}, blocks=blocks,
                                 subjects={**subjects, sid: {"name": "Harbor Bridge"}})

    def test_exact_quote_and_locator_are_required(self):
        fact, blocks, subjects = self.proposal()
        altered = copy.deepcopy(fact)
        altered["evidence"][0]["quote"] = "Northstar never charges a fee."
        with self.assertRaises(ValueError):
            rf.validate_proposal(self.workspace, altered, blocks=blocks, subjects=subjects)
        ref = {**fact["evidence"][0], "start_line": 999}
        with self.assertRaises(ValueError):
            rf.resolve_reference(self.workspace, ref)

    def test_semantic_failure_is_repaired_at_most_once_and_creates_gap(self):
        self.source("# Northstar\nNorthstar uses validator consensus.\n")
        provider = FactFixture(reject=True)
        doc, usage = self.collect(provider)
        self.assertEqual(doc["facts"], [])
        self.assertEqual(usage["provider_calls"], 4)
        self.assertEqual(len([p for p in provider.calls if p.startswith("# Original")]), 2)
        row = next(r for r in doc["coverage"] if r["topic"] == "architecture")
        self.assertTrue(row["gaps"])
        self.assertNotIn("does not use", rf.render_topic(self.workspace, doc, "architecture"))
        same, usage = self.collect(provider)
        self.assertEqual(usage["provider_calls"], 0)
        self.assertEqual(same["revision"], doc["revision"])

    def test_missing_conditions_can_be_fixed_and_valid_work_survives(self):
        self.source("# Northstar\nNorthstar uses validators only after activation.\n")
        class Repair(FactFixture):
            def generate(inner, prompt, **kwargs):
                response = super().generate(prompt, **kwargs)
                if prompt.startswith("# Independent original-source") and len(inner.calls) == 2:
                    data = json.loads(response.text)
                    data["checks"][0].update(status="needs_qualification", context_preserved=False)
                    return ProviderResponse(json.dumps(data), inner.name, ())
                return response
        provider = Repair()
        doc, usage = self.collect(provider)
        self.assertEqual(len(doc["facts"]), 1)
        self.assertEqual(usage["provider_calls"], 4)
        self.assertIn("REPAIRS:", provider.calls[2])

    def test_provider_failure_is_finite_and_does_not_erase_sources(self):
        path = self.source("# Northstar\nNorthstar uses validators.\n")
        before = path.read_bytes()
        class Offline:
            def generate(self, *args, **kwargs):
                raise RuntimeError("offline")
        doc, usage = self.collect(Offline())
        self.assertEqual(usage["provider_calls"], 2)
        self.assertFalse(doc["facts"])
        self.assertEqual(path.read_bytes(), before)

    def test_source_change_reuses_other_batches_topics_and_keeps_history(self):
        self.source("# Northstar\nNorthstar uses validator consensus.\n", "architecture.md")
        path = self.source("# Northstar\nNorthstar charges a 2% fee.\n", "fees.md")
        provider = FactFixture()
        old, _ = self.collect(provider)
        old_fee = next(f for f in old["facts"] if f["topic"] == "revenue-model")
        page, _ = rf.write_topic(self.workspace, old, "architecture", refresh=True)
        page_bytes = page.read_bytes()
        old_fp = rf.topic_fingerprint(self.workspace, "architecture")
        path.write_text("# Northstar\nNorthstar charges a 3% fee.\n", encoding="utf-8")
        new, usage = self.collect(provider)
        self.assertEqual(usage["provider_calls"], 2)
        self.assertEqual(old_fp, rf.topic_fingerprint(self.workspace, "architecture"))
        rf.write_topic(self.workspace, new, "architecture", refresh=True)
        self.assertEqual(page.read_bytes(), page_bytes)
        fee = next(f for f in new["facts"] if f["topic"] == "revenue-model")
        self.assertIn(old_fee["revision"], fee["supersedes"])
        self.assertIn("2%", rf.fact_detail(self.workspace, old_fee["revision"])["statement"])

    def test_conflicting_new_document_and_dates_remain_separate(self):
        self.source("# Northstar\nNorthstar charges a 2% fee.\n", "fees-a.md")
        self.collect()
        self.source("# Northstar\nNorthstar charges a 3% fee.\n", "fees-b.md")
        doc, _ = self.collect()
        coverage = next(r for r in doc["coverage"] if r["topic"] == "revenue-model")
        self.assertTrue(coverage["conflicts"])
        self.assertEqual(len(doc["facts"]), 2)
        self.source("# Northstar\nIn 2020 Northstar charges a 2% fee.\n", "fees-a.md")
        self.source("# Northstar\nIn 2025 Northstar charges a 3% fee.\n", "fees-b.md")
        dated, _ = self.collect()
        row = next(r for r in dated["coverage"] if r["topic"] == "revenue-model")
        self.assertFalse(row["conflicts"])
        self.assertEqual(row["freshness"], "dated_documentation")
        self.assertEqual(row["observations"], "not_assessed")

    def test_qualitative_conflicts_are_preserved_with_both_sources(self):
        self.source("# Northstar\nNorthstar admins may pause execution.\n", "a.md")
        self.source("# Northstar\nNorthstar admins cannot pause execution.\n", "b.md")
        doc, _ = self.collect(FactFixture(conflicts=True))
        row = next(r for r in doc["coverage"] if r["topic"] == "architecture")
        self.assertTrue(row["conflicts"])
        self.assertEqual(len(doc["conflicts"][0]["quotes"]), 2)

    def test_legacy_and_edited_supported_pages_are_preserved_and_comparable(self):
        self.source("# Northstar\nNorthstar uses validators.\n")
        doc, _ = self.collect()
        original = self.workspace.vault_entity_directory / "Architecture.md"
        original.write_text("# My architecture\nMy original notes.\n", encoding="utf-8")
        before = original.read_bytes()
        page, preserved = rf.write_topic(self.workspace, doc, "architecture", refresh=True)
        self.assertTrue(preserved)
        self.assertEqual(original.read_bytes(), before)
        self.assertIn("Original notes", page.read_text())
        self.assertIn("-My original notes", rf.page_comparison(self.workspace, "architecture")["diff"])
        first_bytes = page.read_bytes()
        repeated, _ = rf.write_topic(self.workspace, doc, "architecture", refresh=True)
        self.assertEqual(repeated, page)
        self.assertEqual(repeated.read_bytes(), first_bytes)
        page.write_text("# Edited supported notes\nKeep these too.\n", encoding="utf-8")
        replacement, _ = rf.write_topic(self.workspace, doc, "architecture", refresh=True)
        self.assertNotEqual(replacement, page)
        self.assertIn("Keep these too", page.read_text())
        self.assertEqual(rf.page_views(self.workspace)[original], replacement)

    def test_dashboard_has_one_generated_topic_entry_and_safe_source_links(self):
        from definalyzer.dashboard import _project_pages, render_markdown
        self.source("# Northstar\nNorthstar uses validators.\n")
        doc, _ = self.collect()
        original = self.workspace.vault_entity_directory / "Architecture.md"
        original.write_text("# Architecture\nOlder notes.\n", encoding="utf-8")
        page, _ = rf.write_topic(self.workspace, doc, "architecture", refresh=True)
        rows = _project_pages(self.workspace)
        self.assertEqual(len([r for r in rows if r["title"] == "Architecture"]), 1)
        html = render_markdown(page.read_text())
        self.assertIn('class="fact-source"', html)
        self.assertIn('class="research-comparison"', html)
        self.assertNotIn('href="fact:', html)
        self.assertTrue(any(r["group"] == "Saved experimental research" for r in rows))
        comparison = rf.page_comparison(self.workspace, "architecture")["diff"]
        self.assertNotIn("extraction_provider", comparison)
        self.assertNotIn(doc["facts"][0]["revision"], comparison)

    def test_source_edit_during_provider_call_cannot_commit_stale_facts(self):
        path = self.source("# Northstar\nNorthstar uses validators.\n")
        class Changed(FactFixture):
            def generate(inner, prompt, **kwargs):
                result = super().generate(prompt, **kwargs)
                path.write_text("# Northstar\nNorthstar changed.\n", encoding="utf-8")
                return result
        with self.assertRaisesRegex(ValueError, "changed during"):
            self.collect(Changed())
        self.assertIsNone(rf.load_facts(self.workspace))

    def test_documentation_does_not_satisfy_measurements_or_unanswered_questions(self):
        self.source("# Northstar\nNorthstar charges a 2% fee.\n")
        doc, _ = self.collect()
        row = next(r for r in doc["coverage"] if r["topic"] == "revenue-model")
        self.assertEqual(row["evidence"], "partial")
        self.assertEqual(row["freshness"], "unknown")
        self.assertEqual(row["questions"][1]["evidence"], "missing")
        self.assertEqual(row["observations"], "not_assessed")
        self.assertIn("Dated fees", row["next_action"])

    def test_interrupted_attempt_resumes_with_remaining_budget(self):
        self.source("# Northstar\nNorthstar uses validators.\n")
        class Interrupted(FactFixture):
            def generate(inner, prompt, **kwargs):
                if prompt.startswith("# Independent original-source"):
                    raise KeyboardInterrupt()
                return super().generate(prompt, **kwargs)
        with self.assertRaises(KeyboardInterrupt):
            self.collect(Interrupted())
        self.assertIsNone(rf.load_facts(self.workspace))
        provider = FactFixture(reject=True)
        doc, usage = self.collect(provider)
        self.assertEqual(usage["provider_calls"], 2)
        self.assertFalse(doc["facts"])

    def test_dropped_repair_stays_a_gap(self):
        self.source("# Northstar\nNorthstar uses validators.\n")
        class Dropped(FactFixture):
            def generate(inner, prompt, **kwargs):
                if "\nREPAIRS:" in prompt:
                    inner.calls.append(prompt)
                    return ProviderResponse('{"facts":[],"gaps":[]}', inner.name, ())
                return super().generate(prompt, **kwargs)
        doc, _ = self.collect(Dropped(reject=True))
        self.assertFalse(doc["facts"])
        row = next(r for r in doc["coverage"] if r["topic"] == "architecture")
        self.assertTrue(row["gaps"])

    def test_rendered_claim_cannot_inject_extra_source_link(self):
        from definalyzer.dashboard import render_markdown
        text = rf._plain('Source [Source](fact:northstar:' + 'a' * 64 + ') <script>alert(1)</script>')
        rendered = render_markdown('- ' + text)
        self.assertNotIn('class="fact-source"', rendered)
        self.assertNotIn('<script>', rendered)

    def test_original_documents_are_available_to_project_questions(self):
        from definalyzer.analyst_review import _project_passages, list_review_pages
        self.source("# Northstar\nNorthstar uses validators.\n")
        doc, _ = self.collect()
        original = self.workspace.vault_entity_directory / "Architecture.md"
        original.write_text("# Legacy\nOld untraced assertion.\n", encoding="utf-8")
        proposed, _ = rf.write_topic(self.workspace, doc, "architecture", refresh=True)
        self.assertIn(proposed, list_review_pages(self.workspace))
        self.assertIn(original, list_review_pages(self.workspace))
        passages = _project_passages(self.workspace, deep=True)
        originals = [p for p in passages if p.source_type == "documentation"]
        self.assertTrue(any("Northstar uses validators" in p.text for p in originals))
        self.assertTrue(all(p.path.is_relative_to(self.workspace.sources_directory) for p in originals))

    def test_related_claims_do_not_fill_the_primary_subjects_questions(self):
        fact, _, _ = self.proposal()
        rows = rf._coverage([fact], [], "chain", "another-subject")
        row = next(r for r in rows if r["topic"] == fact["topic"])
        self.assertEqual(row["evidence"], "partial")
        self.assertTrue(all(q["evidence"] == "missing" for q in row["questions"]))

    def test_experimental_fact_extraction_remains_explicitly_callable(self):
        from definalyzer.extraction import extract_research_page, extract_research_page_chunked
        self.source("# Northstar\nNorthstar uses validators.\n")
        prepare_scope(self.workspace)
        provider = FactFixture()
        for _ in range(2):
            result = rf.extract_fact_page(self.workspace, template_name="architecture", provider=provider, refresh=True)
            self.assertEqual(result.mode, "source-backed")
            self.assertIn("[Source](fact:", result.output_path.read_text())
        self.assertEqual(len(provider.calls), 2)

    def test_source_and_comparison_http_endpoints_enforce_integrity(self):
        import threading
        from urllib.request import urlopen
        from urllib.error import HTTPError
        from definalyzer.dashboard import create_dashboard_server
        self.source("# Northstar\nNorthstar uses validators.\n")
        doc, _ = self.collect()
        (self.workspace.vault_entity_directory / "Architecture.md").write_text("# Original\nKeep.\n", encoding="utf-8")
        rf.write_topic(self.workspace, doc, "architecture", refresh=True)
        server = create_dashboard_server(self.manager, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}/api/projects/northstar/"
            url = base + "facts/" + doc["facts"][0]["revision"]
            with urlopen(url, timeout=3) as response:
                detail = json.loads(response.read())
            self.assertIn("Northstar uses validators", detail["evidence"][0]["context"])
            with urlopen(base + "research-diff/architecture", timeout=3) as response:
                self.assertIn("-Keep.", json.loads(response.read())["diff"])
            path = self.workspace.project_root / "facts/revisions" / (doc["facts"][0]["revision"] + ".json")
            raw = json.loads(path.read_text())
            raw["statement"] = "Changed after checking"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(HTTPError) as raised:
                urlopen(url, timeout=3)
            self.assertEqual(raised.exception.code, 400)
            raised.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
