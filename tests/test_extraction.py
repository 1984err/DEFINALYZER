import tempfile
import unittest
from pathlib import Path

from definalyzer.extraction import (
    RESEARCH_CATEGORIES,
    build_extraction_prompt,
    extract_research_page,
    extract_research_page_chunked,
    load_source_bundle,
    normalize_markdown_spacing,
    split_source_chunks,
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


class ChunkProvider:
    name = "chunk-fake"

    def __init__(self, fail_on_call=None):
        self.prompts = []
        self.fail_on_call = fail_on_call

    def generate(self, prompt, *, working_directory):
        self.prompts.append(prompt)
        if self.fail_on_call == len(self.prompts):
            raise RuntimeError("simulated provider interruption")
        if "# Shared Research-Ledger Task" in prompt:
            text = "# Research Ledger\n\n" + "\n\n".join(
                f"## {category}\n\n"
                "- Relevant documented fact [source.md]"
                for category in RESEARCH_CATEGORIES
            )
        elif "# Fact-Ledger Reduction" in prompt:
            text = "# Fact Ledger\n\n- Deduplicated documented fact [source.md]"
        else:
            heading = (
                "# Architecture"
                if "# Architecture" in prompt
                else "# Protocol Overview"
            )
            text = f"{heading}\n\n# Facts\n\n- Final documented fact"
        return ProviderResponse(
            text=text,
            provider=self.name,
            command=("chunk-fake",),
        )


class ExtractionTests(unittest.TestCase):
    def test_normalizes_heading_and_table_block_spacing(self):
        text = normalize_markdown_spacing(
            "# Risk\n## Register\nVerification: [[Check]]\n"
            "| A | B |\n|---|---|\n"
        )

        self.assertIn("# Risk\n\n## Register\n\n", text)
        self.assertIn("Verification: [[Check]]\n\n| A | B |", text)

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

    def test_excludes_obvious_non_research_pages_from_ai_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "protocol.md").write_text("protocol facts", encoding="utf-8")
            brand = root / "brand-guidelines"
            brand.mkdir()
            (brand / "logo.md").write_text("logo rules", encoding="utf-8")
            legal = root / "terms-of-service"
            legal.mkdir()
            (legal / "terms.md").write_text("legal boilerplate", encoding="utf-8")
            github = root / ".github"
            github.mkdir()
            (github / "CONTRIBUTING.md").write_text(
                "contribution instructions",
                encoding="utf-8",
            )
            (root / "media-coverage.md").write_text(
                "press links",
                encoding="utf-8",
            )
            tutorials = root / "tutorials-v2"
            tutorials.mkdir()
            (tutorials / "create-market.md").write_text(
                "step by step operations",
                encoding="utf-8",
            )
            sdk = root / "developers" / "sdk"
            sdk.mkdir(parents=True)
            (sdk / "install.md").write_text(
                "sdk installation",
                encoding="utf-8",
            )

            bundle, files = load_source_bundle(root)

        self.assertEqual([path.name for path in files], ["protocol.md"])
        self.assertIn("protocol facts", bundle)
        self.assertNotIn("logo rules", bundle)

    def test_builds_prompt_without_omitting_source(self):
        prompt = build_extraction_prompt(
            master_prompt="MASTER",
            template="TEMPLATE",
            source_bundle="SOURCE",
        )

        self.assertIn("MASTER", prompt)
        self.assertIn("TEMPLATE", prompt)
        self.assertIn("SOURCE", prompt)

    def test_final_consolidation_is_decision_dense_not_a_hard_fact_cap(self):
        from definalyzer.extraction import FINAL_CONSOLIDATION_INSTRUCTIONS

        self.assertIn("under 10,000 characters", FINAL_CONSOLIDATION_INSTRUCTIONS)
        self.assertIn("Never omit such a fact", FINAL_CONSOLIDATION_INSTRUCTIONS)

    def test_splits_large_individual_file_without_losing_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = ("alpha beta gamma\n\n" * 200).strip()
            (root / "large.md").write_text(original, encoding="utf-8")

            chunks, files, character_count = split_source_chunks(
                root,
                maximum_characters=500,
            )

        reconstructed = "\n".join(
            chunk.text.split("\n\n", 1)[1].strip() for chunk in chunks
        )
        self.assertEqual(len(files), 1)
        self.assertEqual(character_count, len(original))
        self.assertEqual(
            "".join(reconstructed.split()),
            "".join(original.split()),
        )

    def test_contract_reference_keeps_overview_but_drops_function_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contracts = root / "developers" / "contracts"
            contracts.mkdir(parents=True)
            (contracts / "vault.md").write_text(
                "# Vault\n\nMaterial cap and timelock overview.\n\n"
                "## External Functions\n\n"
                "### deposit\n\nParameter-by-parameter reference.",
                encoding="utf-8",
            )

            bundle, files = load_source_bundle(root)

        self.assertEqual(len(files), 1)
        self.assertIn("Material cap and timelock overview", bundle)
        self.assertNotIn("Parameter-by-parameter reference", bundle)

    def test_user_facing_corpus_suppresses_developer_integration_bulk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            learn = root / "learn"
            learn.mkdir()
            for index in range(3):
                (learn / f"concept-{index}.md").write_text(
                    "Material protocol concept.",
                    encoding="utf-8",
                )
            integration = root / "developers" / "integration"
            integration.mkdir(parents=True)
            (integration / "sdk-flow.md").write_text(
                "Implementation integration flow.",
                encoding="utf-8",
            )
            contracts = root / "developers" / "contracts"
            contracts.mkdir()
            (contracts / "core.md").write_text(
                "Material contract control.",
                encoding="utf-8",
            )

            bundle, files = load_source_bundle(root)

        self.assertEqual(len(files), 4)
        self.assertIn("Material contract control", bundle)
        self.assertNotIn("Implementation integration flow", bundle)

    def test_chunked_extraction_saves_ledgers_and_final_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = WorkspaceManager(root / "output")
            workspace = manager.create_project(name="Chunked")
            (workspace.sources_directory / "one.md").write_text(
                "a" * 2_500,
                encoding="utf-8",
            )
            (workspace.sources_directory / "two.md").write_text(
                "b" * 2_500,
                encoding="utf-8",
            )
            prompts = self._write_prompts(root)
            provider = ChunkProvider()

            result = extract_research_page_chunked(
                workspace=workspace,
                template_name="protocol-overview",
                provider=provider,
                prompts_root=prompts,
                maximum_prompt_characters=4_000,
            )

            state = (
                workspace.project_root
                / "extraction"
                / "shared-research"
                / "state.json"
            )
            state_exists = state.exists()

        self.assertEqual(result.mode, "chunked")
        self.assertGreaterEqual(result.provider_calls, 3)
        self.assertTrue(state_exists)

    def test_chunked_extraction_resumes_completed_ledgers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = WorkspaceManager(root / "output")
            workspace = manager.create_project(name="Resume")
            (workspace.sources_directory / "one.md").write_text(
                "a" * 2_500,
                encoding="utf-8",
            )
            (workspace.sources_directory / "two.md").write_text(
                "b" * 2_500,
                encoding="utf-8",
            )
            prompts = self._write_prompts(root)

            with self.assertRaisesRegex(RuntimeError, "interruption"):
                extract_research_page_chunked(
                    workspace=workspace,
                    template_name="protocol-overview",
                    provider=ChunkProvider(fail_on_call=2),
                    prompts_root=prompts,
                    maximum_prompt_characters=4_000,
                )

            result = extract_research_page_chunked(
                workspace=workspace,
                template_name="protocol-overview",
                provider=ChunkProvider(),
                prompts_root=prompts,
                maximum_prompt_characters=4_000,
            )

        self.assertGreaterEqual(result.reused_calls, 1)

    def test_second_template_reuses_shared_research_ledgers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = WorkspaceManager(root / "output")
            workspace = manager.create_project(name="Shared")
            (workspace.sources_directory / "one.md").write_text(
                "a" * 5_000,
                encoding="utf-8",
            )
            prompts = self._write_prompts(root)
            provider_one = ChunkProvider()
            extract_research_page_chunked(
                workspace=workspace,
                template_name="protocol-overview",
                provider=provider_one,
                prompts_root=prompts,
                maximum_prompt_characters=4_000,
            )
            provider_two = ChunkProvider()
            result = extract_research_page_chunked(
                workspace=workspace,
                template_name="architecture",
                provider=provider_two,
                prompts_root=prompts,
                maximum_prompt_characters=4_000,
            )

        self.assertGreater(result.reused_calls, 0)
        self.assertFalse(
            any(
                "# Shared Research-Ledger Task" in prompt
                for prompt in provider_two.prompts
            )
        )

    def test_chunked_refresh_rebuilds_changed_shared_source_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = WorkspaceManager(root / "output")
            workspace = manager.create_project(name="Changed Sources")
            source = workspace.sources_directory / "one.md"
            source.write_text("a" * 5_000, encoding="utf-8")
            prompts = self._write_prompts(root)
            extract_research_page_chunked(
                workspace=workspace,
                template_name="protocol-overview",
                provider=ChunkProvider(),
                prompts_root=prompts,
                maximum_prompt_characters=4_000,
            )
            source.write_text("b" * 5_000, encoding="utf-8")

            result = extract_research_page_chunked(
                workspace=workspace,
                template_name="protocol-overview",
                provider=ChunkProvider(),
                prompts_root=prompts,
                maximum_prompt_characters=4_000,
                refresh=True,
            )

        self.assertGreater(result.provider_calls, 0)
        self.assertEqual(result.reused_calls, 0)

    @staticmethod
    def _write_prompts(root):
        prompts = root / "prompts"
        templates = prompts / "templates"
        templates.mkdir(parents=True)
        (prompts / "master_prompt.md").write_text(
            "Extract material facts only.",
            encoding="utf-8",
        )
        (templates / "template_protocol_overview.md").write_text(
            "# Protocol Overview\n\n# Facts",
            encoding="utf-8",
        )
        (templates / "template_architecture.md").write_text(
            "# Architecture\n\n# Facts",
            encoding="utf-8",
        )
        return prompts

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
        self.assertIn('source_coverage: "missing"', output)
        self.assertIn("## Source Coverage", output)
        self.assertIn("does not prove", output)
        self.assertIn("# Protocol Overview", output)
        self.assertEqual(result.source_files, 1)

    def test_refresh_replaces_only_generated_research_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = WorkspaceManager(root / "output")
            workspace = manager.create_project(name="Refresh Example")
            (workspace.sources_directory / "docs.md").write_text(
                "# Documentation\n\nExample protocol.",
                encoding="utf-8",
            )
            prompts = self._write_prompts(root)
            first = extract_research_page(
                workspace=workspace,
                template_name="protocol-overview",
                provider=FakeProvider(),
                prompts_root=prompts,
            )
            refreshed = extract_research_page(
                workspace=workspace,
                template_name="protocol-overview",
                provider=FakeProvider(),
                prompts_root=prompts,
                refresh=True,
            )

        self.assertEqual(first.output_path, refreshed.output_path)

    def test_rejects_template_instruction_leak(self):
        with self.assertRaisesRegex(ValueError, "template instructions"):
            validate_extraction_output(
                "# Protocol Overview\nTEMPLATE INSTRUCTIONS",
                expected_heading="# Protocol Overview",
            )

    def test_rejects_snapshot_supply_fields_from_tokenomics(self):
        with self.assertRaisesRegex(ValueError, "deterministic token index"):
            validate_extraction_output(
                "# Tokenomics\n\n## Supply\n\n"
                "| Field | Value |\n|---|---|\n"
                "| Circulating supply | 100 |\n",
                expected_heading="# Tokenomics",
            )


if __name__ == "__main__":
    unittest.main()
