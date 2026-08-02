import tempfile
import unittest
from pathlib import Path

from definalyzer.source_coverage import (
    add_official_source,
    coverage_markdown,
    ensure_source_coverage,
    source_inventory_markdown,
    update_source_status,
)
from definalyzer.workspace import WorkspaceManager


class SourceCoverageTests(unittest.TestCase):
    def test_primary_docs_register_as_technical_and_missing_stays_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(
                name="Example",
                docs_url="https://docs.example.test",
            )
            summary = ensure_source_coverage(workspace)
            rendered = coverage_markdown(workspace)

        self.assertEqual(summary.categories["technical"], "registered")
        self.assertEqual(summary.categories["tokenomics"], "missing")
        self.assertEqual(summary.status, "missing")
        self.assertIn("does not prove", rendered)

    def test_critical_categories_produce_partial_coverage_until_all_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            for category in ("technical", "tokenomics", "fees_revenue"):
                source = add_official_source(
                    workspace,
                    category=category,
                    url=f"https://example.test/{category}",
                )
                update_source_status(
                    workspace,
                    source_id=source.source_id,
                    status="collected",
                )
            summary = ensure_source_coverage(workspace)
            inventory = source_inventory_markdown(workspace)

        self.assertEqual(summary.status, "partial")
        self.assertEqual(summary.categories["tokenomics"], "collected")
        self.assertEqual(summary.categories["governance_security"], "missing")
        self.assertIn("https://example.test/tokenomics", inventory)

    def test_duplicate_source_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            first = add_official_source(
                workspace,
                category="tokenomics",
                url="https://example.test/token",
            )
            second = add_official_source(
                workspace,
                category="tokenomics",
                url="https://example.test/token",
            )

        self.assertEqual(first, second)

    def test_native_token_content_credits_opaque_token_page_name(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(
                name="Kamino",
                docs_url="https://kamino.example/docs",
            )
            workspace.sources_directory.mkdir(parents=True, exist_ok=True)
            (workspace.sources_directory / "kmno.md").write_text(
                "KMNO is the native token of Kamino Finance.\n",
                encoding="utf-8",
            )

            summary = ensure_source_coverage(workspace)

        self.assertEqual(summary.categories["tokenomics"], "collected")

    def test_unrelated_native_token_mention_does_not_credit_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(
                name="Example",
                docs_url="https://docs.example.test",
            )
            workspace.sources_directory.mkdir(parents=True, exist_ok=True)
            (workspace.sources_directory / "overview.md").write_text(
                "SOL is the native token of Solana.\n",
                encoding="utf-8",
            )

            summary = ensure_source_coverage(workspace)

        self.assertEqual(summary.categories["tokenomics"], "missing")


if __name__ == "__main__":
    unittest.main()
