import json
import tempfile
import unittest
from pathlib import Path

from definalyzer.application import DefinalyzerApplication
from definalyzer.providers import ProviderResponse
from definalyzer.workspace import WorkspaceManager


class FakeProvider:
    name = "fake"

    def generate(self, prompt, *, working_directory):
        return ProviderResponse(
            text="A cited explanation [Source 1].",
            provider="fake",
            command=("fake",),
        )


class ApplicationServiceTests(unittest.TestCase):
    def test_snapshot_is_json_safe_and_exposes_action_reasons(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            app = DefinalyzerApplication(manager)
            project = app.create_project(name="Example")

            snapshot = app.snapshot(project)
            encoded = json.dumps(snapshot.to_dict())

        self.assertIn('"slug": "example"', encoded)
        self.assertIn('"application_schema_version": 1', encoded)
        self.assertFalse(snapshot.actions["crawl"].available)
        self.assertEqual(
            snapshot.actions["crawl"].reason,
            "No documentation URL is configured.",
        )
        self.assertTrue(snapshot.actions["delete"].available)
        self.assertTrue(snapshot.actions["official_sources"].available)

    def test_question_uses_injected_provider_and_optional_save(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            app = DefinalyzerApplication(
                manager,
                provider_factory=lambda settings: FakeProvider(),
            )
            project = app.create_project(name="Example")
            (project.vault_entity_directory / "Risk-Assessment.md").write_text(
                "# Risk Assessment\n\n## Oracle\n\nPrices can become stale.\n",
                encoding="utf-8",
            )

            result = app.ask(
                workspace=project,
                question="What is the oracle risk?",
                save=True,
            )
            snapshot = app.snapshot(project)

        self.assertIsNotNone(result.saved_path)
        self.assertTrue(snapshot.actions["ask"].available)

    def test_project_lifecycle_uses_one_application_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            app = DefinalyzerApplication(manager)
            created = app.create_project(
                name="Delete Example",
                docs_url="https://docs.example.org/",
            )

            listed = app.list_projects()
            removed = app.delete_project(created.slug)
            remaining = app.list_projects()

        self.assertEqual([row.slug for row in listed], ["delete-example"])
        self.assertTrue(removed)
        self.assertEqual(remaining, ())


if __name__ == "__main__":
    unittest.main()
