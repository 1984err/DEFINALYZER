import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from definalyzer.analyst_review import (
    parse_review_sections,
    retrieve_review_passages,
    run_analyst_review,
    save_analyst_review,
    repair_analyst_review_citations,
    select_review_page,
    select_review_section,
)
from definalyzer.providers import ProviderResponse
from definalyzer.workspace import WorkspaceManager


class RecordingProvider:
    name = "fake"

    def __init__(self):
        self.prompts = []

    def generate(self, prompt, *, working_directory):
        self.prompts.append(prompt)
        return ProviderResponse(
            text=(
                "The selected entry describes a controlled permission.\n\n"
                "Unknown: the section does not state who currently holds it."
            ),
            provider="fake",
            command=("fake",),
        )


class AnalystReviewTests(unittest.TestCase):
    def make_page(self, directory):
        manager = WorkspaceManager(Path(directory) / "output")
        workspace = manager.create_project(name="Example Protocol")
        page = workspace.vault_entity_directory / "Governance.md"
        page.write_text(
            "# Governance\n\n"
            "Overview text.\n\n"
            "## Material Permissions\n\n"
            "| Role | Capability |\n"
            "|---|---|\n"
            "| Guardian | Pause the system. |\n\n"
            "### Limits\n\n"
            "Cannot move user assets.\n\n"
            "```markdown\n"
            "## This Is Not A Heading\n"
            "```\n\n"
            "## Voting\n\n"
            "Token holders vote.\n",
            encoding="utf-8",
        )
        return workspace, page

    def test_parses_nested_section_without_crossing_peer_heading(self):
        with tempfile.TemporaryDirectory() as directory:
            _, page = self.make_page(directory)
            sections = parse_review_sections(page)
            material = next(
                section
                for section in sections
                if section.title == "Material Permissions"
            )

        self.assertIn("Guardian", material.text)
        self.assertIn("Cannot move user assets", material.text)
        self.assertNotIn("Token holders vote", material.text)
        self.assertFalse(
            any(section.title == "This Is Not A Heading" for section in sections)
        )

    def test_review_can_restrict_to_selected_section_without_editing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace, page = self.make_page(directory)
            original = page.read_text(encoding="utf-8")
            section = select_review_section(page, "Material Permissions")
            provider = RecordingProvider()
            result = run_analyst_review(
                workspace=workspace,
                provider=provider,
                page=page,
                section=section,
                question="What can the guardian do?",
            )
            unchanged = page.read_text(encoding="utf-8")

        self.assertEqual(unchanged, original)
        self.assertIn("Guardian", provider.prompts[0])
        self.assertNotIn("Token holders vote", provider.prompts[0])
        self.assertIn("Search scope: Governance.md > Material Permissions", provider.prompts[0])
        self.assertIn("Unknown", result.answer)

    def test_project_review_retrieves_answer_from_another_page(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace, _ = self.make_page(directory)
            revenue = workspace.vault_entity_directory / "Revenue-Model.md"
            revenue.write_text(
                "# Revenue Model\n\n## Protocol Fees\n\n"
                "Borrowers pay an origination fee to the treasury.\n",
                encoding="utf-8",
            )
            provider = RecordingProvider()
            result = run_analyst_review(
                workspace=workspace,
                provider=provider,
                question="How does the protocol make money?",
            )

        self.assertEqual(result.scope, "project research")
        self.assertIn("origination fee", provider.prompts[0])
        self.assertTrue(
            any(row.path.name == "Revenue-Model.md" for row in result.passages)
        )

    def test_deep_review_searches_collected_documentation_with_bounded_context(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace, _ = self.make_page(directory)
            source = workspace.sources_directory / "economics.md"
            source.write_text(
                "# Buybacks\n\nFifty percent of protocol revenue funds token buybacks.\n",
                encoding="utf-8",
            )
            passages = retrieve_review_passages(
                workspace=workspace,
                question="Are there revenue-funded buybacks?",
                deep=True,
                maximum_characters=5_000,
            )

        self.assertTrue(any(row.source_type == "documentation" for row in passages))
        self.assertIn("buybacks", passages[0].text.casefold())
        self.assertLessEqual(sum(len(row.text) for row in passages), 5_000)

    def test_saves_separate_non_canonical_review_with_obsidian_source(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace, page = self.make_page(directory)
            section = select_review_section(page, "Material Permissions")
            result = run_analyst_review(
                workspace=workspace,
                provider=RecordingProvider(),
                page=page,
                section=section,
                question="Explain this permission.",
            )
            saved = save_analyst_review(
                workspace=workspace,
                result=result,
                now=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            text = saved.saved_path.read_text(encoding="utf-8")

        self.assertIn('data_class: "non_canonical_ai_explanation"', text)
        self.assertIn(
            "[[Protocols/Example Protocol/Governance#Material Permissions\\|",
            text,
        )
        self.assertIn("## Sources Consulted", text)
        self.assertIn("**Source 1:**", text)
        self.assertIn("^source-1", text)
        self.assertIn("not research evidence or verification", text)
        self.assertEqual(saved.saved_path.name, "Explain this permission.md")

    def test_repairs_existing_plain_source_citations_as_obsidian_links(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace, _page = self.make_page(directory)
            review_directory = (
                workspace.vault_root / "Analyst Reviews" / workspace.name
            )
            review_directory.mkdir(parents=True)
            review = review_directory / "Legacy.md"
            review.write_text(
                '---\ngenerated_by: "definalyzer_analyst_review"\n---\n\n'
                "# Analyst Review\n\n## Sources Consulted\n\n"
                "- [[Protocols/Example Protocol/Governance|Governance]]\n\n"
                "## Answer\n\nSupported by [Source 1].\n\n"
                "## Use Limitation\n\nCaution.\n",
                encoding="utf-8",
            )

            changed = repair_analyst_review_citations(workspace)
            text = review.read_text(encoding="utf-8")

        self.assertEqual(changed, (review,))
        self.assertIn("**Source 1:**", text)
        self.assertIn("^source-1", text)
        self.assertIn("[[#^source-1|Source 1]]", text)

    def test_duplicate_saved_questions_use_readable_numeric_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace, page = self.make_page(directory)
            section = select_review_section(page, "Material Permissions")
            result = run_analyst_review(
                workspace=workspace,
                provider=RecordingProvider(),
                page=page,
                section=section,
                question="Who controls this?",
            )
            first = save_analyst_review(workspace=workspace, result=result)
            second = save_analyst_review(workspace=workspace, result=result)

        self.assertEqual(first.saved_path.name, "Who controls this.md")
        self.assertEqual(second.saved_path.name, "Who controls this - 2.md")

    def test_selects_page_by_stem_and_rejects_unknown_heading(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace, page = self.make_page(directory)
            selected = select_review_page(workspace, "Governance")
            with self.assertRaisesRegex(ValueError, "was not found"):
                select_review_section(page, "Missing")

        self.assertEqual(selected, page)


if __name__ == "__main__":
    unittest.main()
