import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from definalyzer.analyst_review import (
    parse_review_sections,
    run_analyst_review,
    save_analyst_review,
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

    def test_review_uses_only_selected_section_and_does_not_edit_source(self):
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
        self.assertIn("using only the selected research section", provider.prompts[0])
        self.assertIn("Unknown", result.answer)

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
        self.assertIn("not research evidence or verification", text)

    def test_selects_page_by_stem_and_rejects_unknown_heading(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace, page = self.make_page(directory)
            selected = select_review_page(workspace, "Governance")
            with self.assertRaisesRegex(ValueError, "was not found"):
                select_review_section(page, "Missing")

        self.assertEqual(selected, page)


if __name__ == "__main__":
    unittest.main()
