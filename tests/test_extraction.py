import tempfile
import unittest
from pathlib import Path

from definalyzer.extraction import (
    build_extraction_prompt,
    extract_research_page,
    load_source_bundle,
    validate_extraction_output,
)
from definalyzer.providers import ProviderResponse
from definalyzer.workspace import WorkspaceManager


class FakeProvider:
    name = "fake"

    def generate(self, prompt, *, working_directory):
        return ProviderResponse(
            text=(
                "# Protocol Overview\n\n"
                "# Facts\n\n"
                "## Identity\n\n"
                "| Field | Value |\n|---|---|\n| Protocol | Example |\n"
            ),
            provider=self.name,
            command=("fake",),
        )


class ExtractionTests(unittest.TestCase):
    def test_loads_sources_in_stable_order_with_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b.md").write_text("second", encoding="utf-8")
            (root / "a.md").write_text("first", encoding="utf-8")

            bundle, files = load_source_bundle(root)

        self.assertEqual([path.name for path in files], ["a.md", "b.md"])
        self.assertLess(bundle.index("first"), bundle.index("second"))
        self.assertIn("SOURCE FILE: a.md", bundle)

    def test_rejects_source_larger_than_single_pass_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "large.md").write_text("x" * 100, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "chunking"):
                load_source_bundle(root, maximum_characters=50)

    def test_builds_prompt_without_omitting_source(self):
        prompt = build_extraction_prompt(
            master_prompt="MASTER",
            template="TEMPLATE",
            source_bundle="SOURCE",
        )

        self.assertIn("MASTER", prompt)
        self.assertIn("TEMPLATE", prompt)
        self.assertIn("SOURCE", prompt)

    def test_writes_validated_page_with_provenance_frontmatter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = WorkspaceManager(root / "output")
            workspace = manager.create_project(name="Example")
            (workspace.sources_directory / "docs.md").write_text(
                "# Documentation\n\nExample protocol.",
                encoding="utf-8",
            )
            prompts = root / "prompts"
            templates = prompts / "templates"
            templates.mkdir(parents=True)
            (prompts / "master_prompt.md").write_text(
                "Extract facts.",
                encoding="utf-8",
            )
            (templates / "template_protocol_overview.md").write_text(
                "# Protocol Overview",
                encoding="utf-8",
            )

            result = extract_research_page(
                workspace=workspace,
                template_name="protocol-overview",
                provider=FakeProvider(),
                prompts_root=prompts,
            )
            output = result.output_path.read_text(encoding="utf-8")

        self.assertIn('extraction_provider: "fake"', output)
        self.assertIn("# Protocol Overview", output)
        self.assertEqual(result.source_files, 1)

    def test_rejects_template_instruction_leak(self):
        with self.assertRaisesRegex(ValueError, "template instructions"):
            validate_extraction_output(
                "# Protocol Overview\nTEMPLATE INSTRUCTIONS",
                expected_heading="# Protocol Overview",
            )


if __name__ == "__main__":
    unittest.main()
