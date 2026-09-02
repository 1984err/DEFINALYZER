import json
import tempfile
import unittest
from pathlib import Path

from definalyzer.workspace import WorkspaceManager


class WorkspaceManagerTests(unittest.TestCase):
    def test_rejects_project_names_that_can_escape_or_break_vault_links(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            for name in ("../Outside", "Bad/Path", "Broken|Link", "CON"):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(ValueError, "Project name"):
                        manager.create_project(name=name)

    def test_creates_project_and_obsidian_ready_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(
                name="Example Protocol",
                entity_type="protocol",
                docs_url="https://docs.example.test",
                verification_status="not_requested",
            )

            self.assertTrue(project.manifest_path.exists())
            self.assertTrue(project.sources_directory.exists())
            self.assertTrue(project.registry_directory.exists())
            self.assertTrue(project.jobs_directory.exists())
            self.assertTrue(project.evidence_directory.exists())
            self.assertTrue(project.vault_entity_directory.exists())
            self.assertTrue(project.verification_directory.exists())
            self.assertTrue(
                (project.vault_root / "Analyst Reviews").exists()
            )
            self.assertTrue((project.vault_root / "README.md").exists())
            self.assertTrue(
                (project.vault_entity_directory / "Index.md").exists()
            )

    def test_refuses_to_overwrite_existing_project(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            manager.create_project(name="Existing")

            with self.assertRaisesRegex(FileExistsError, "will not be overwritten"):
                manager.create_project(name="Existing")

    def test_migrates_legacy_flat_verification_page_and_links(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(name="Example")
            legacy = project.vault_root / "Verification" / "Example - Verification.md"
            legacy.write_text("# Legacy verification\n", encoding="utf-8")
            research = project.vault_entity_directory / "Risk-Assessment.md"
            research.write_text(
                "[[Verification/Example - Verification#^vr-001|VR-001]]\n",
                encoding="utf-8",
            )

            loaded = manager.load_project("example")

            self.assertFalse(legacy.exists())
            self.assertEqual(
                loaded.verification_page_path.read_text(encoding="utf-8"),
                "# Legacy verification\n",
            )
            self.assertIn(
                "[[Verification/Example/Index#^vr-001|VR-001]]",
                research.read_text(encoding="utf-8"),
            )

    def test_updates_stage_and_verification_status(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(name="Status Test")
            project = manager.update_stage(
                project,
                "crawl",
                "complete",
                detail="4 pages saved",
            )
            project = manager.set_verification_status(project, "pending")
            loaded = manager.load_project("status-test")
            index = (
                loaded.vault_entity_directory / "Index.md"
            ).read_text(encoding="utf-8")

            self.assertEqual(
                loaded.document["stages"]["crawl"]["status"],
                "complete",
            )
            self.assertEqual(loaded.document["verification_status"], "pending")
            self.assertIn('verification_status: "pending"', index)

    def test_lists_projects_in_stable_order(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            manager.create_project(name="Zulu")
            manager.create_project(name="Alpha")

            self.assertEqual(
                [project.slug for project in manager.list_projects()],
                ["alpha", "zulu"],
            )

    def test_persists_documentation_url_added_after_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(name="Docs Later")
            manager.set_docs_url(project, "https://docs.example.test")

            loaded = manager.load_project(project.slug)

        self.assertEqual(
            loaded.document["docs_url"],
            "https://docs.example.test",
        )

    def test_delete_project_removes_generated_data_and_orphan_token(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(name="Disposable")
            (project.registry_directory / "registry.json").write_text(
                json.dumps({"tokens": [{"symbol": "DROP"}]}),
                encoding="utf-8",
            )
            token_directory = project.vault_root / "Tokens" / "DROP"
            token_directory.mkdir(parents=True)
            (token_directory / "Index.md").write_text("# DROP\n", encoding="utf-8")
            review_directory = (
                project.vault_root / "Analyst Reviews" / project.name
            )
            review_directory.mkdir(parents=True)
            (review_directory / "Question.md").write_text(
                "# Question\n", encoding="utf-8"
            )

            removed = manager.delete_project(project)

            self.assertTrue(removed)
            self.assertFalse(project.project_root.exists())
            self.assertFalse(project.sources_directory.exists())
            self.assertFalse(project.registry_directory.exists())
            self.assertFalse(project.vault_entity_directory.exists())
            self.assertFalse(project.verification_directory.exists())
            self.assertFalse(review_directory.exists())
            self.assertFalse(token_directory.exists())
            with self.assertRaises(FileNotFoundError):
                manager.load_project(project.slug)
            self.assertTrue((project.vault_root / "Indexes").exists())

    def test_delete_project_preserves_token_used_by_another_project(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            first = manager.create_project(name="First")
            second = manager.create_project(name="Second")
            registry = json.dumps({"tokens": [{"symbol": "SHARED"}]})
            (first.registry_directory / "registry.json").write_text(
                registry, encoding="utf-8"
            )
            (second.registry_directory / "registry.json").write_text(
                registry, encoding="utf-8"
            )
            token_directory = first.vault_root / "Tokens" / "SHARED"
            token_directory.mkdir(parents=True)

            manager.delete_project(first)

            self.assertTrue(token_directory.exists())
            self.assertEqual(manager.load_project(second.slug).name, "Second")

    def test_delete_chain_project_removes_its_orphan_coin(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(name="Disposable Chain", entity_type="chain")
            (project.registry_directory / "registry.json").write_text(
                json.dumps({"tokens": [{"symbol": "DROP"}]}), encoding="utf-8"
            )
            coin_directory = project.vault_root / "Coins" / "DROP"
            coin_directory.mkdir(parents=True)
            (coin_directory / "Index.md").write_text("# DROP\n", encoding="utf-8")

            manager.delete_project(project)

            self.assertFalse(coin_directory.exists())


if __name__ == "__main__":
    unittest.main()
