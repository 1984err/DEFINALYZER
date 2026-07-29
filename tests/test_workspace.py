import tempfile
import unittest
from pathlib import Path

from definalyzer.workspace import WorkspaceManager


class WorkspaceManagerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
