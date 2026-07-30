import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from definalyzer.app import OUTPUT_FILES, main
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
                        "15",
                    ]
                ),
                print_fn=messages.append,
            )

            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.load_project("menu-project")

        self.assertEqual(exit_code, 0)
        self.assertEqual(project.name, "Menu Project")
        self.assertTrue(any("Obsidian folder" in item for item in messages))

    @patch("definalyzer.app._registry", return_value=0)
    @patch("definalyzer.app._extract")
    @patch("definalyzer.app._crawl")
    def test_complete_workflow_reuses_existing_sources_and_pages(
        self,
        crawl,
        extract,
        registry,
    ):
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(name="Example")
            (project.sources_directory / "source.md").write_text(
                "# Source",
                encoding="utf-8",
            )
            for filename in OUTPUT_FILES.values():
                (project.vault_entity_directory / filename).write_text(
                    "# Generated",
                    encoding="utf-8",
                )
            exit_code = main(
                ["--workspace", str(workspace_root), "all", "example"],
                print_fn=messages.append,
            )

        self.assertEqual(exit_code, 0)
        crawl.assert_not_called()
        extract.assert_not_called()
        registry.assert_called_once()
        self.assertTrue(any("Complete workflow finished" in item for item in messages))

    @patch("definalyzer.app._verification_plan", return_value=2)
    @patch("definalyzer.app._registry", return_value=0)
    @patch("definalyzer.app._extract")
    def test_complete_workflow_generates_missing_pages_in_template_order(
        self,
        extract,
        registry,
        verification_plan,
    ):
        calls = []

        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(
                name="Ordered",
                verification_status="pending",
            )
            (project.sources_directory / "source.md").write_text(
                "# Source",
                encoding="utf-8",
            )

            def generate(manager_arg, workspace_arg, **kwargs):
                template = kwargs["template_name"]
                calls.append(template)
                filename = OUTPUT_FILES[template]
                (workspace_arg.vault_entity_directory / filename).write_text(
                    f"# {template}",
                    encoding="utf-8",
                )
                return 0

            extract.side_effect = generate
            exit_code = main(
                ["--workspace", str(workspace_root), "all", project.slug],
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, list(OUTPUT_FILES))
        registry.assert_called_once()
        verification_plan.assert_called_once()

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

    @patch("crawler.github_importer.import_github_markdown")
    def test_crawl_routes_repository_url_to_github_importer(self, importer):
        importer.return_value = SimpleNamespace(
            commit_sha="a" * 40,
            discovered=12,
            saved=12,
            skipped=0,
            failed=0,
        )
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(
                name="Repository Project",
                docs_url="https://github.com/example/public-docs",
            )
            exit_code = main(
                [
                    "--workspace",
                    str(workspace_root),
                    "crawl",
                    project.slug,
                    "--ref",
                    "main",
                ],
                print_fn=messages.append,
            )
            updated = manager.load_project(project.slug)

        self.assertEqual(exit_code, 0)
        importer.assert_called_once_with(
            protocol_name="Repository Project",
            repository_url="https://github.com/example/public-docs",
            output_directory=project.sources_directory,
            ref="main",
            refresh=False,
        )
        self.assertEqual(
            updated.document["stages"]["crawl"]["status"],
            "complete",
        )
        self.assertTrue(any("GitHub snapshot" in item for item in messages))

    def test_source_command_registers_and_lists_official_source(self):
        messages = []

        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(name="Coverage Project")
            added = main(
                [
                    "--workspace",
                    str(workspace_root),
                    "source",
                    "add",
                    project.slug,
                    "--category",
                    "tokenomics",
                    "--url",
                    "https://example.test/token",
                ],
                print_fn=messages.append,
            )
            listed = main(
                [
                    "--workspace",
                    str(workspace_root),
                    "source",
                    "list",
                    project.slug,
                ],
                print_fn=messages.append,
            )

        self.assertEqual(added, 0)
        self.assertEqual(listed, 0)
        self.assertTrue(any("tokenomics-token" in item for item in messages))
        self.assertTrue(any("Token and tokenomics: registered" in item for item in messages))


if __name__ == "__main__":
    unittest.main()
