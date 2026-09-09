import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from definalyzer.report_contract import ReportRequest, content_sha256, initialize_report_package
from definalyzer.report_evidence import (
    EvidenceLimits, build_report_evidence, evidence_snapshot_sha256,
    load_report_evidence, prepare_report_evidence, report_evidence_is_current,
)
from definalyzer.workspace import WorkspaceManager


NOW = "2026-09-03T12:00:00+00:00"


class ReportEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.manager = WorkspaceManager(Path(self.temporary.name) / "output")
        self.workspace = self.manager.create_project(name="Example Protocol")
        self.package = initialize_report_package(
            workspace=self.workspace,
            request=ReportRequest(title="Revenue review", mode="question", question="Is revenue sustainable?"),
            now=NOW,
        )
        self.manifest = json.loads(self.package.manifest_path.read_text(encoding="utf-8"))

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def research(self, name="Economics.md", text="# Economics\n\n## Revenue\n\nRevenue is variable.\n"):
        return self.write(self.workspace.vault_entity_directory / name, text)

    def build(self, **kwargs):
        return build_report_evidence(workspace=self.workspace, manifest=self.manifest, now=NOW, **kwargs)

    def prepare(self, **kwargs):
        return prepare_report_evidence(workspace=self.workspace, report_id="revenue-review", now=NOW, **kwargs)

    def test_read_only_offline_build_preserves_source_and_state(self):
        page = self.research()
        original = page.read_bytes()
        manifest_bytes = self.package.manifest_path.read_bytes()
        with patch("urllib.request.urlopen", side_effect=AssertionError("No network")):
            result = self.build()
        self.assertEqual(original, page.read_bytes())
        self.assertEqual(manifest_bytes, self.package.manifest_path.read_bytes())
        self.assertFalse(self.package.report_path.exists())
        self.assertTrue(result["evidence"])
        self.assertEqual(result["retrieval"]["readiness"], "review_required")

    def test_verbatim_line_ranges_and_hashes_preserve_crlf(self):
        page = self.research(text='---\r\nentity: "Example"\r\n---\r\n# Economics\r\n\r\n## Revenue\r\n\r\nRevenue is 10.\r\n\r\n| Revenue | Fee |\r\n|---|---|\r\n| 10 | 2 |\r\n')
        result = self.build()
        raw = page.read_bytes()
        lines = raw.decode("utf-8").splitlines(keepends=True)
        for row in result["evidence"]:
            location = row["locator"]
            self.assertEqual(row["excerpt"], "".join(lines[location["line"] - 1:location["end_line"]]))
            self.assertEqual(row["content_sha256"], content_sha256(row["excerpt"]))
            self.assertEqual(row["source_sha256"], content_sha256(raw))
            self.assertNotIn('entity: "Example"', row["excerpt"])
        self.assertTrue(any("|---|---|" in row["excerpt"] for row in result["evidence"]))

    def test_retains_only_explicit_source_url_and_distinguishes_crawl_time(self):
        self.write(self.workspace.sources_directory / "fees.md",
                   '---\nsource: "https://example.test/fees"\ncrawled_at: "2026-08-01T00:00:00Z"\n---\n# Fees\n\nRevenue is variable. [Other](https://other.test/)\n')
        row = self.build()["evidence"][0]
        self.assertEqual(row["source_url"], "https://example.test/fees")
        self.assertEqual(row["source_captured_at"], "2026-08-01T00:00:00Z")
        self.assertIsNone(row["as_of"])

    def test_full_review_covers_all_available_source_types(self):
        self.manifest.update(mode="full_review", question=None)
        self.research()
        self.write(self.workspace.verification_page_path, "# Revenue\n\nStatus: Pending; not independently verified.\n")
        self.write(self.workspace.sources_directory / "fees.md", "# Fees\n\nFees support revenue.\n")
        self.write(self.workspace.registry_directory / "market-data" / "EX.json", json.dumps({"total_supply": 100, "collected_at": NOW}))
        self.write(self.workspace.evidence_directory / "call.json", json.dumps({"chain": "ethereum", "block": 12, "status": "collected", "result": "0x0"}))
        result = self.build(limits=EvidenceLimits(max_passages=5))
        self.assertEqual(set(result["retrieval"]["selected_source_types"]),
                         {"research", "verification", "source_document", "market_data", "blockchain_evidence"})
        self.assertIn("Pending", next(row["excerpt"] for row in result["evidence"] if row["source_type"] == "verification"))

    def test_question_with_no_matches_is_insufficient_not_arbitrary_fallback(self):
        self.research(text="# Governance\n\nOwners vote on upgrades.\n")
        result = self.build()
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["retrieval"]["readiness"], "insufficient")
        self.assertTrue(any("No question-matching" in item for item in result["retrieval"]["warnings"]))

    def test_question_ignores_project_identity_terms_and_uses_focus_budget(self):
        unrelated = "\n\n".join(
            f"## Governance item {index}\n\nExample Protocol governance item {index}."
            for index in range(30)
        )
        self.research(
            text=(
                "# Example Protocol\n\n" + unrelated
                + "\n\n## Revenue\n\nReserve fees provide revenue.\n"
            )
        )
        result = self.build()
        excerpts = "\n".join(row["excerpt"] for row in result["evidence"])
        self.assertIn("Reserve fees", excerpts)
        self.assertNotIn("governance item", excerpts)
        self.assertLessEqual(result["retrieval"]["selected_passages"], 18)
        self.assertLessEqual(result["retrieval"]["selected_characters"], 36_000)
        self.assertEqual(result["retrieval"]["selection_limits"], {
            "max_characters": 36_000,
            "max_passages": 18,
        })

    def test_matched_document_caveats_are_also_retrieved(self):
        self.research(text="# Economics\n\n## Revenue\n\nRevenue grows.\n\n## Risks\n\nHistorical data is unavailable.\n")
        result = self.build()
        self.assertTrue(any(row["selection_reason"] == "related_caveat" for row in result["evidence"]))
        self.assertTrue(any("unavailable" in row["excerpt"] for row in result["evidence"]))

    def test_limits_do_not_clip_tables_or_structured_snapshots(self):
        self.manifest.update(mode="full_review", question=None)
        table = "| Revenue | Amount |\n|---|---|\n" + "| Fees | 10 |\n" * 100
        self.research(text="# Revenue\n\nSmall revenue note.\n\n" + table)
        self.write(self.workspace.evidence_directory / "huge.json", json.dumps({"revenue": "x" * 400}))
        result = self.build(limits=EvidenceLimits(max_characters=500, max_passage_characters=200, max_passages=2))
        self.assertLessEqual(result["retrieval"]["selected_characters"], 500)
        self.assertEqual(result["retrieval"]["omissions"]["oversized_block"], 2)
        self.assertEqual(len(result["evidence"]), 1)
        self.assertNotIn("| Fees", result["evidence"][0]["excerpt"])

    def test_budget_exclusions_are_visible(self):
        self.research(text="# Revenue\n\nRevenue one.\n\nRevenue two.\n\nRevenue three.\n")
        result = self.build(limits=EvidenceLimits(max_passages=1))
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["retrieval"]["omissions"]["context_budget"], 2)

    def test_oversized_and_invalid_files_do_not_break_other_sources(self):
        self.research()
        self.write(self.workspace.sources_directory / "big.md", "revenue " * 200)
        self.write(self.workspace.registry_directory / "market-data" / "bad.json", "{oops")
        result = self.build(limits=EvidenceLimits(max_file_bytes=200))
        self.assertTrue(result["evidence"])
        self.assertEqual(result["retrieval"]["omissions"]["file_size_limit"], 1)
        self.assertEqual(result["retrieval"]["omissions"]["unreadable_or_invalid"], 1)

    def test_file_and_scan_caps_are_reported(self):
        self.research()
        self.write(self.workspace.sources_directory / "fees.md", "Revenue " * 10)
        limited = self.build(limits=EvidenceLimits(max_files=1))
        self.assertTrue(limited["retrieval"]["discovery_limited"])
        limited = self.build(limits=EvidenceLimits(max_scan_bytes=1))
        self.assertFalse(limited["evidence"])
        self.assertGreater(limited["retrieval"]["omissions"]["scan_size_limit"], 0)

    def test_unsafe_paths_and_other_project_files_are_not_read(self):
        other = self.manager.create_project(name="Other")
        self.write(other.vault_entity_directory / "Secret.md", "Revenue forbidden")
        self.write(self.workspace.project_root / "settings.json", '{"api_key":"SECRET"}')
        self.write(self.workspace.vault_root / "Analyst Reviews" / self.workspace.name / "Answer.md", "Revenue noncanonical")
        self.research()
        result = self.build()
        serialized = json.dumps(result)
        self.assertNotIn("forbidden", serialized)
        self.assertNotIn("SECRET", serialized)
        self.assertNotIn("noncanonical", serialized)

    def test_symlink_sources_are_rejected(self):
        external = self.write(Path(self.temporary.name) / "outside.md", "Revenue private")
        link = self.workspace.sources_directory / "linked.md"
        try:
            link.symlink_to(external)
        except OSError:
            self.skipTest("Creating symlinks requires Windows privileges")
        result = self.build()
        self.assertFalse(result["evidence"])
        self.assertEqual(result["retrieval"]["omissions"]["unsafe_path"], 1)

    def test_simulated_link_is_rejected_when_windows_cannot_create_one(self):
        linked = self.write(self.workspace.sources_directory / "linked.md", "Revenue private")
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda path: path == linked or original(path)):
            result = self.build()
        self.assertFalse(result["evidence"])
        self.assertEqual(result["retrieval"]["omissions"]["unsafe_path"], 1)

    def test_sensitive_blocks_and_source_headers_are_excluded(self):
        self.research(text="# Revenue\n\nRevenue public.\n\nRevenue api_key=SECRET\n\nRevenue https://user:password@example.test\n\nRevenue C:\\Users\\Private\\job.json\n")
        self.write(self.workspace.sources_directory / "unsafe.md", '---\nsource: "https://example.test/?api_key=SECRET"\n---\n# Revenue\n\nRevenue documentation.\n')
        result = self.build()
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertNotIn("password@", json.dumps(result))
        self.assertNotIn("Private", json.dumps(result))
        self.assertEqual(result["retrieval"]["omissions"]["sensitive_block"], 3)
        self.assertIsNone(next(row["source_url"] for row in result["evidence"] if row["source_type"] == "source_document"))

    def test_chain_assets_use_coins_not_every_token_in_vault(self):
        chain = self.manager.create_project(name="Example Chain", entity_type="chain")
        self.workspace = chain
        self.manifest["project"] = {"name": chain.name, "slug": chain.slug, "entity_type": "chain"}
        self.write(chain.registry_directory / "registry.json", json.dumps({"tokens": [{"symbol": "EX"}, {"symbol": "../escape"}]}))
        self.write(chain.vault_root / "Coins" / "EX" / "Index.md", '# EX\n\nRevenue coin data.\n')
        self.write(chain.vault_root / "Tokens" / "EX" / "Index.md", '# EX\n\nRevenue wrong network.\n')
        result = self.build()
        self.assertTrue(any("vault/Coins/EX/Index.md" == row["source_path"] for row in result["evidence"]))
        self.assertNotIn("wrong network", json.dumps(result))
        self.assertEqual(result["retrieval"]["omissions"]["invalid_registry_symbol"], 1)

    def test_registry_symbol_collision_does_not_import_another_project_asset(self):
        self.write(self.workspace.registry_directory / "registry.json", json.dumps({"tokens": [{"symbol": "EX"}]}))
        self.write(self.workspace.vault_root / "Tokens" / "EX" / "Index.md", '---\nparent_protocol: "Other"\n---\nRevenue from another project\n')
        result = self.build()
        self.assertFalse(result["evidence"])
        self.assertEqual(result["retrieval"]["omissions"]["asset_page_other_project"], 1)

    def test_market_snapshot_stays_whole_with_its_timestamp(self):
        self.manifest.update(mode="full_review", question=None)
        snapshot = {"status": "unavailable", "total_supply": None, "max_supply": None, "collected_at": "2026-08-01T00:00:00Z"}
        self.write(self.workspace.registry_directory / "market-data" / "EX.json", json.dumps(snapshot))
        result = self.build()
        row = result["evidence"][0]
        self.assertEqual(json.loads(row["excerpt"]), snapshot)
        self.assertEqual(row["as_of"], snapshot["collected_at"])
        self.assertTrue(any("stale" in warning for warning in result["retrieval"]["warnings"]))

    def test_coverage_metadata_is_not_evidence(self):
        self.research()
        result = self.build()
        self.assertTrue(result["retrieval"]["source_coverage"]["not_protocol_evidence"])
        self.assertFalse(any("_SOURCE_COVERAGE" in row["source_path"] for row in result["evidence"]))

    def test_save_and_load_preserve_scope_and_are_repeatable(self):
        self.research()
        first = self.prepare()
        self.assertEqual(first, load_report_evidence(workspace=self.workspace, report_id="revenue-review"))
        second = prepare_report_evidence(workspace=self.workspace, report_id="revenue-review", now="2026-09-04T00:00:00Z")
        self.assertEqual(evidence_snapshot_sha256(first), evidence_snapshot_sha256(second))
        self.assertFalse(self.package.report_path.exists())
        self.assertEqual(json.loads(self.package.manifest_path.read_text())["status"], "evidence_ready")

    def test_insufficient_save_does_not_pretend_sources_exist(self):
        result = self.prepare()
        self.assertEqual(result["retrieval"]["readiness"], "insufficient")
        self.assertEqual(result["evidence"], [])
        load_report_evidence(workspace=self.workspace, report_id="revenue-review")

    def test_current_check_detects_edits_additions_deletions_without_rewriting(self):
        page = self.research()
        self.prepare()
        before = self.package.evidence_path.read_bytes()
        check = lambda: report_evidence_is_current(workspace=self.workspace, report_id="revenue-review")
        self.assertTrue(check())
        original = page.read_text()
        self.write(page, original + "\nRevenue changed.\n")
        self.assertFalse(check())
        self.write(page, original)
        new = self.write(self.workspace.sources_directory / "new.md", "Revenue added.\n")
        self.assertFalse(check())
        new.unlink()
        self.assertTrue(check())
        page.unlink()
        self.assertFalse(check())
        self.assertEqual(before, self.package.evidence_path.read_bytes())

    def test_existing_draft_is_not_modified(self):
        self.research()
        self.write(self.package.report_path, "User-edited draft")
        before = self.package.manifest_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "cannot be replaced"):
            self.prepare()
        self.assertEqual(self.package.report_path.read_text(), "User-edited draft")
        self.assertEqual(before, self.package.manifest_path.read_bytes())
        self.assertFalse((self.package.directory / ".evidence.lock").exists())

    def test_final_status_is_not_mutated(self):
        self.manifest.update(status="final")
        self.manifest["quality"] = {
            "status": "passed", "checked_at": NOW,
            "issues_file": "quality.json",
        }
        self.manifest["human_review"]["finalized_at"] = NOW
        self.manifest["human_review"]["approval_sha256"] = "0" * 64
        self.write(self.package.manifest_path, json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "cannot be replaced"):
            self.prepare()

    def test_mutual_exclusion_and_failed_commit_detection(self):
        self.research()
        lock = self.write(self.package.directory / ".evidence.lock", "")
        with self.assertRaises(FileExistsError):
            self.prepare()
        lock.unlink()
        from definalyzer import report_evidence
        original = report_evidence._atomic_json
        def fail_manifest(path, document):
            if path.name == "report.json":
                raise OSError("Simulated interruption")
            original(path, document)
        with patch.object(report_evidence, "_atomic_json", side_effect=fail_manifest):
            with self.assertRaises(OSError):
                self.prepare()
        with self.assertRaisesRegex(ValueError, "snapshot mismatch"):
            load_report_evidence(workspace=self.workspace, report_id="revenue-review")
        self.prepare()  # Retry safely repairs an incomplete preparation.
        self.assertFalse(lock.exists())

    def test_tampered_excerpt_is_rejected(self):
        self.research()
        document = self.prepare()
        document["evidence"][0]["excerpt"] += " invented conclusion"
        self.write(self.package.evidence_path, json.dumps(document))
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            load_report_evidence(workspace=self.workspace, report_id="revenue-review")

    def test_malformed_retrieval_metadata_is_rejected_even_with_new_fingerprint(self):
        self.research()
        document = self.prepare()
        document["retrieval"]["readiness"] = "complete"
        self.write(self.package.evidence_path, json.dumps(document))
        manifest = json.loads(self.package.manifest_path.read_text())
        manifest["provenance"]["research_snapshot_sha256"] = evidence_snapshot_sha256(document)
        self.write(self.package.manifest_path, json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "retrieval metadata"):
            load_report_evidence(workspace=self.workspace, report_id="revenue-review")

    def test_limits_and_manifest_project_are_validated(self):
        for limits in (EvidenceLimits(max_files=True), EvidenceLimits(max_characters=0), EvidenceLimits(max_passages=1000)):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                self.build(limits=limits)
        self.manifest["project"]["slug"] = "other"
        with self.assertRaisesRegex(ValueError, "does not belong"):
            self.build()


if __name__ == "__main__":
    unittest.main()
