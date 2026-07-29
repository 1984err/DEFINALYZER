import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from definalyzer.app import main
from definalyzer.providers import ProviderResponse
from definalyzer.workspace import WorkspaceManager


def answers(values):
    iterator = iter(values)
    return lambda prompt: next(iterator)


class UnifiedAppTests(unittest.TestCase):
    def test_cli_creates_and_reports_project(self):
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            workspace = str(Path(directory) / "output")
            created = main(
                [
                    "--workspace",
                    workspace,
                    "init",
                    "Example",
                    "--docs-url",
                    "https://docs.example.test",
                ],
                print_fn=messages.append,
            )
            reported = main(
                ["--workspace", workspace, "status", "example"],
                print_fn=messages.append,
            )

        self.assertEqual(created, 0)
        self.assertEqual(reported, 0)
        self.assertTrue(any("Project created" in item for item in messages))
        self.assertTrue(any('"verification_status"' in item for item in messages))

    def test_guided_menu_creates_project_and_exits(self):
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            exit_code = main(
                ["--workspace", str(Path(directory) / "output")],
                input_fn=answers(
                    [
                        "1",
                        "Menu Project",
                        "",
                        "",
                        "n",
                        "14",
                    ]
                ),
                print_fn=messages.append,
            )

            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.load_project("menu-project")

        self.assertEqual(exit_code, 0)
        self.assertEqual(project.name, "Menu Project")
        self.assertTrue(any("Obsidian folder" in item for item in messages))

    def test_unconfigured_complete_workflow_is_explicit(self):
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            workspace = str(Path(directory) / "output")
            main(["--workspace", workspace, "init", "Example"])
            exit_code = main(
                ["--workspace", workspace, "all", "example"],
                print_fn=messages.append,
            )

        self.assertEqual(exit_code, 2)
        self.assertTrue(
            any("has not been connected yet" in item for item in messages)
        )

    @patch("definalyzer.app.run_collector_menu", return_value=0)
    def test_collect_uses_existing_collector_and_updates_stage(self, collector):
        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(name="Collector Project")

            exit_code = main(
                [
                    "--workspace",
                    str(workspace_root),
                    "collect",
                    project.slug,
                ]
            )
            updated = manager.load_project(project.slug)

        self.assertEqual(exit_code, 0)
        collector.assert_called_once_with(
            input_fn=unittest.mock.ANY,
            print_fn=unittest.mock.ANY,
            working_directory=project.project_root,
        )
        self.assertEqual(
            updated.document["stages"]["evidence_collection"]["status"],
            "complete",
        )

    @patch("definalyzer.app.create_provider")
    def test_provider_configuration_uses_external_credential_store(
        self,
        create_provider,
    ):
        create_provider.return_value = SimpleNamespace(
            executable=Path("C:/Hermes/hermes.exe")
        )
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            exit_code = main(
                [
                    "--workspace",
                    str(Path(directory) / "output"),
                    "provider",
                    "configure",
                    "--executable",
                    "C:/Hermes/hermes.exe",
                ],
                print_fn=messages.append,
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(
            any("Credentials remain managed by Hermes" in item for item in messages)
        )

    @patch("definalyzer.app.create_provider")
    def test_extract_command_uses_configured_provider(self, create_provider):
        provider = SimpleNamespace(
            name="fake",
            generate=lambda prompt, working_directory: ProviderResponse(
                text="# Protocol Overview\n\n# Facts\n",
                provider="fake",
                command=("fake",),
            ),
        )
        create_provider.return_value = provider
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(name="Extract Project")
            (project.sources_directory / "source.md").write_text(
                "# Source\n\nA documented fact.",
                encoding="utf-8",
            )
            exit_code = main(
                [
                    "--workspace",
                    str(workspace_root),
                    "extract",
                    project.slug,
                ],
                print_fn=messages.append,
            )
            output = (
                project.vault_entity_directory / "Protocol-Overview.md"
            )
            output_exists = output.exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(output_exists)
        self.assertTrue(any("Research page" in item for item in messages))

    @patch("definalyzer.app.refresh_token_pages_from_registry")
    @patch("definalyzer.app.refresh_market_data")
    def test_market_data_command_is_optional_and_separate(
        self,
        refresh_market_data,
        refresh_token_pages,
    ):
        refresh_market_data.return_value = SimpleNamespace(
            snapshots=(
                SimpleNamespace(status="available"),
                SimpleNamespace(status="unavailable"),
            ),
            refreshed=2,
            reused=0,
        )
        refresh_token_pages.return_value = ()
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(name="Market Project")
            exit_code = main(
                [
                    "--workspace",
                    str(workspace_root),
                    "market-data",
                    project.slug,
                    "--refresh",
                ],
                print_fn=messages.append,
            )

        self.assertEqual(exit_code, 0)
        refresh_market_data.assert_called_once_with(
            workspace=unittest.mock.ANY,
            force=True,
        )
        self.assertTrue(any("1 available; 1 unavailable" in item for item in messages))

    @patch("definalyzer.app.create_provider")
    def test_ask_command_reviews_one_selected_heading(self, create_provider):
        provider = SimpleNamespace(
            name="fake",
            generate=lambda prompt, working_directory: ProviderResponse(
                text="A concise scoped explanation.",
                provider="fake",
                command=("fake",),
            ),
        )
        create_provider.return_value = provider
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(name="Review Project")
            (project.vault_entity_directory / "Risk-Assessment.md").write_text(
                "# Risk Assessment\n\n"
                "## Oracle Risk\n\nA stale price can affect liquidations.\n\n"
                "## Other Risk\n\nSeparate content.\n",
                encoding="utf-8",
            )
            exit_code = main(
                [
                    "--workspace",
                    str(workspace_root),
                    "ask",
                    project.slug,
                    "--page",
                    "Risk-Assessment",
                    "--heading",
                    "Oracle Risk",
                    "--question",
                    "Explain the consequence.",
                ],
                print_fn=messages.append,
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(
            any("A concise scoped explanation." in item for item in messages)
        )


if __name__ == "__main__":
    unittest.main()
