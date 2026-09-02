import json
import tempfile
import unittest
from pathlib import Path

from definalyzer.dependencies import (
    bootstrap_legacy_research,
    json_fingerprint,
    record_research_page,
    research_pages_current,
    source_corpus_fingerprint,
    stale_research_pages,
)
from definalyzer.extraction import OUTPUT_FILES, TEMPLATE_FILES
from definalyzer.workspace import WorkspaceManager


class DependencyStateTests(unittest.TestCase):
    def _prompts(self, root: Path) -> Path:
        prompts = root / "prompts"
        templates = prompts / "templates"
        templates.mkdir(parents=True)
        (prompts / "master_prompt.md").write_text(
            "master",
            encoding="utf-8",
        )
        for filename in TEMPLATE_FILES.values():
            (templates / filename).write_text(filename, encoding="utf-8")
        # This prompt is not an input to the ten research pages.
        (templates / "template_verification_page.md").write_text(
            "verification",
            encoding="utf-8",
        )
        return prompts

    def test_source_fingerprint_tracks_selected_not_excluded_files(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Inputs")
            selected = workspace.sources_directory / "overview.md"
            excluded = workspace.sources_directory / "api" / "endpoint.md"
            excluded.parent.mkdir()
            selected.write_text("one", encoding="utf-8")
            excluded.write_text("reference one", encoding="utf-8")
            initial = source_corpus_fingerprint(workspace)

            excluded.write_text("reference two", encoding="utf-8")
            self.assertEqual(initial, source_corpus_fingerprint(workspace))

            selected.write_text("two", encoding="utf-8")
            self.assertNotEqual(initial, source_corpus_fingerprint(workspace))

    def test_research_pages_become_stale_only_for_research_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompts = self._prompts(root)
            manager = WorkspaceManager(root / "output")
            workspace = manager.create_project(name="Current")
            (workspace.sources_directory / "source.md").write_text(
                "source",
                encoding="utf-8",
            )
            for template, filename in OUTPUT_FILES.items():
                (workspace.vault_entity_directory / filename).write_text(
                    template,
                    encoding="utf-8",
                )
                record_research_page(
                    workspace,
                    template_name=template,
                    prompts_root=prompts,
                )

            self.assertTrue(
                research_pages_current(workspace, prompts_root=prompts)
            )
            verification = (
                prompts / "templates" / "template_verification_page.md"
            )
            verification.write_text("changed", encoding="utf-8")
            self.assertTrue(
                research_pages_current(workspace, prompts_root=prompts)
            )

            target = next(iter(TEMPLATE_FILES))
            target_path = prompts / "templates" / TEMPLATE_FILES[target]
            original_target = target_path.read_text(encoding="utf-8")
            target_path.write_text("changed template", encoding="utf-8")
            self.assertEqual(
                stale_research_pages(workspace, prompts_root=prompts),
                (target,),
            )
            target_path.write_text(original_target, encoding="utf-8")

            (prompts / "master_prompt.md").write_text(
                "changed master",
                encoding="utf-8",
            )
            self.assertFalse(
                research_pages_current(workspace, prompts_root=prompts)
            )
            self.assertEqual(
                set(stale_research_pages(workspace, prompts_root=prompts)),
                set(TEMPLATE_FILES),
            )

    def test_bootstrap_adopts_a_complete_legacy_research_set_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompts = self._prompts(root)
            manager = WorkspaceManager(root / "output")
            workspace = manager.create_project(name="Legacy")
            (workspace.sources_directory / "source.md").write_text(
                "source",
                encoding="utf-8",
            )
            for filename in OUTPUT_FILES.values():
                (workspace.vault_entity_directory / filename).write_text(
                    "legacy",
                    encoding="utf-8",
                )

            self.assertTrue(
                bootstrap_legacy_research(workspace, prompts_root=prompts)
            )
            self.assertFalse(
                bootstrap_legacy_research(workspace, prompts_root=prompts)
            )
            self.assertTrue(
                research_pages_current(workspace, prompts_root=prompts)
            )

    def test_json_fingerprint_can_ignore_generated_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(
                json.dumps({"generated_at": "one", "tokens": ["A"]}),
                encoding="utf-8",
            )
            initial = json_fingerprint(path, ignored_keys=("generated_at",))
            path.write_text(
                json.dumps({"generated_at": "two", "tokens": ["A"]}),
                encoding="utf-8",
            )
            self.assertEqual(
                initial,
                json_fingerprint(path, ignored_keys=("generated_at",)),
            )
            path.write_text(
                json.dumps({"generated_at": "three", "tokens": ["B"]}),
                encoding="utf-8",
            )
            self.assertNotEqual(
                initial,
                json_fingerprint(path, ignored_keys=("generated_at",)),
            )


if __name__ == "__main__":
    unittest.main()
