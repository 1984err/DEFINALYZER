import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from definalyzer.app import (
    OUTPUT_FILES,
    _collect_planned_verification,
    _default_crawl_pattern,
    _evaluate,
    _invalidate_after_registry_change,
    _invalidate_after_source_change,
    _invalidate_after_verification_job_change,
    _menu_prerequisites_ready,
    _print_supported_collector_chains,
    _project_workflow_lock,
    _verification_status_label,
    _workflow_status_document,
    main,
)
from definalyzer.dependencies import (
    json_fingerprint,
    record_research_page,
    source_corpus_fingerprint,
)
from definalyzer.providers import ProviderResponse
from definalyzer.workspace import WorkspaceManager


def answers(values):
    iterator = iter(values)
    return lambda prompt: next(iterator)


class UnifiedAppTests(unittest.TestCase):
    def test_crawl_pattern_scopes_exact_documentation_subsection(self):
        self.assertEqual(
            _default_crawl_pattern(
                "https://docs.pendle.finance/pendle-v2/"
            ),
            "*/pendle-v2/*",
        )

    def test_crawl_pattern_keeps_default_for_documentation_root(self):
        self.assertEqual(
            _default_crawl_pattern("https://docs.pendle.finance/"),
            "*/docs/*",
        )

    def test_crawl_pattern_uses_parent_for_landing_page_url(self):
        self.assertEqual(
            _default_crawl_pattern(
                "https://docs.pendle.finance/pendle-v2/Introduction"
            ),
            "*/pendle-v2/*",
        )

    @patch("definalyzer.app.generate_evaluation_proposals")
    @patch("definalyzer.app.create_provider")
    def test_evaluation_preserves_newer_collection_stage(
        self,
        create_provider,
        generate_proposals,
    ):
        generate_proposals.return_value = SimpleNamespace(
            proposals=[],
            unmatched_evidence=[],
            ignored_stale_evidence=[],
            reused=0,
        )
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            stale_workspace = manager.create_project(name="Fresh State")
            manager.update_stage(
                stale_workspace,
                "evidence_collection",
                "complete",
                detail="1 collected",
            )

            result = _evaluate(manager, stale_workspace, lambda message: None)
            current = manager.load_project(stale_workspace.slug)

        self.assertEqual(result, 2)
        self.assertEqual(
            current.document["stages"]["evidence_collection"]["status"],
            "complete",
        )
        self.assertEqual(
            current.document["stages"]["evidence_evaluation"]["status"],
            "partial",
        )
        create_provider.assert_called_once()

    def test_status_reports_effective_research_readiness_and_next_action(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(name="Effective Status")
            initial = _workflow_status_document(project)
            self.assertEqual(initial["research_inputs"], "incomplete")
            self.assertEqual(initial["required_stages"], 3)
            self.assertIn("Collect documentation", initial["next_action"])

            source = project.sources_directory / "source.md"
            source.write_text("before", encoding="utf-8")
            prompts = Path(__file__).parents[1] / "prompts"
            for template, filename in OUTPUT_FILES.items():
                (project.vault_entity_directory / filename).write_text(
                    template,
                    encoding="utf-8",
                )
                record_research_page(
                    project,
                    template_name=template,
                    prompts_root=prompts,
                )
            project = manager.update_stage(project, "crawl", "complete")
            project = manager.update_stage(project, "research", "complete")
            (project.registry_directory / "registry.json").write_text(
                '{"tokens":[],"addresses":[]}',
                encoding="utf-8",
            )
            project = manager.update_stage(project, "registry", "partial")
            ready = _workflow_status_document(project)
            self.assertEqual(ready["research_inputs"], "current")
            self.assertEqual(ready["ready_stages"], 3)
            self.assertIn("verification was not requested", ready["next_action"])

            project = manager.set_verification_status(project, "manual_review")
            project.verification_page_path.write_text(
                "# Verification\n\nManual tasks remain.\n",
                encoding="utf-8",
            )
            project = manager.update_stage(
                project,
                "verification_plan",
                "complete",
            )
            project = manager.update_stage(
                project,
                "obsidian_links",
                "complete",
            )
            manual = _workflow_status_document(project)
            self.assertEqual(manual["required_stages"], 5)
            self.assertEqual(manual["ready_stages"], 5)
            self.assertIn("manual verification tasks", manual["next_action"])

            source.write_text("after", encoding="utf-8")
            stale = _workflow_status_document(project)
            self.assertEqual(stale["research_inputs"], "stale")
            self.assertIn("Refresh stale research", stale["next_action"])

    @patch("definalyzer.app._registry")
    def test_cli_registry_enforces_same_prerequisites_as_menu(
        self,
        registry,
    ):
        messages = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output"
            project = WorkspaceManager(root).create_project(name="CLI Order")
            exit_code = main(
                ["--workspace", str(root), "registry", project.slug],
                print_fn=messages.append,
            )

        self.assertEqual(exit_code, 2)
        registry.assert_not_called()
        self.assertTrue(any("Analyze Project" in row for row in messages))

    def test_source_change_preserves_files_and_marks_descendants_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(
                name="Stale Source",
                verification_status="supported",
            )
            source = project.sources_directory / "source.md"
            source.write_text("before", encoding="utf-8")
            evidence = project.evidence_directory / "keep.json"
            evidence.write_text("{}", encoding="utf-8")
            for stage in (
                "research",
                "registry",
                "verification_plan",
                "evidence_collection",
                "evidence_evaluation",
                "obsidian_links",
            ):
                project = manager.update_stage(project, stage, "complete")
            previous = source_corpus_fingerprint(project)
            source.write_text("after", encoding="utf-8")

            _invalidate_after_source_change(
                manager,
                project,
                previous_fingerprint=previous,
                print_fn=lambda message: None,
            )
            updated = manager.load_project(project.slug)

            self.assertTrue(evidence.exists())
            self.assertEqual(updated.document["verification_status"], "pending")
            for stage in (
                "research",
                "registry",
                "verification_plan",
                "evidence_collection",
                "evidence_evaluation",
                "obsidian_links",
            ):
                self.assertEqual(
                    updated.document["stages"][stage]["status"],
                    "pending",
                )

    def test_registry_timestamp_does_not_invalidate_but_data_change_does(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(
                name="Registry Change",
                verification_status="supported",
            )
            registry = project.registry_directory / "registry.json"
            registry.write_text(
                '{"generated_at":"one","tokens":["A"]}',
                encoding="utf-8",
            )
            for stage in (
                "verification_plan",
                "evidence_collection",
                "evidence_evaluation",
                "obsidian_links",
            ):
                project = manager.update_stage(project, stage, "complete")
            previous = json_fingerprint(
                registry,
                ignored_keys=("generated_at",),
            )
            registry.write_text(
                '{"generated_at":"two","tokens":["A"]}',
                encoding="utf-8",
            )
            _invalidate_after_registry_change(
                manager,
                project,
                previous_fingerprint=previous,
                print_fn=lambda message: None,
            )
            unchanged = manager.load_project(project.slug)
            self.assertEqual(
                unchanged.document["stages"]["verification_plan"]["status"],
                "complete",
            )

            previous = json_fingerprint(
                registry,
                ignored_keys=("generated_at",),
            )
            registry.write_text(
                '{"generated_at":"three","tokens":["B"]}',
                encoding="utf-8",
            )
            _invalidate_after_registry_change(
                manager,
                unchanged,
                previous_fingerprint=previous,
                print_fn=lambda message: None,
            )
            changed = manager.load_project(project.slug)
            self.assertEqual(
                changed.document["stages"]["verification_plan"]["status"],
                "pending",
            )
            self.assertEqual(changed.document["verification_status"], "pending")

    def test_verification_job_change_marks_old_evidence_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(name="Plan Change")
            project = manager.update_stage(
                project,
                "evidence_collection",
                "complete",
            )
            project = manager.update_stage(
                project,
                "evidence_evaluation",
                "complete",
            )

            _invalidate_after_verification_job_change(
                manager,
                project,
                previous_fingerprint="old",
                current_fingerprint="new",
                print_fn=lambda message: None,
            )
            updated = manager.load_project(project.slug)

            self.assertEqual(
                updated.document["stages"]["evidence_collection"]["status"],
                "pending",
            )
            self.assertEqual(
                updated.document["stages"]["evidence_evaluation"]["status"],
                "pending",
            )

    def test_individual_steps_explain_missing_prerequisites(self):
        messages = []
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(name="Out of Order")

            ready = _menu_prerequisites_ready(
                project,
                choice="6",
                print_fn=messages.append,
            )

        self.assertFalse(ready)
        self.assertTrue(any("option 4" in item for item in messages))
        self.assertTrue(any("option 5" in item for item in messages))
        self.assertTrue(any("option 2" in item for item in messages))

    def test_verification_status_distinguishes_finished_and_manual_only(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            finished = manager.create_project(
                name="Finished",
                verification_status="pending",
            )
            finished.verification_page_path.write_text(
                "| Status | Count |\n|---|---:|\n"
                "| Pending | 0 |\n| Manual review | 2 |\n",
                encoding="utf-8",
            )
            finished = manager.update_stage(
                finished,
                "evidence_evaluation",
                "complete",
            )
            manual = manager.create_project(
                name="Manual",
                verification_status="manual_review",
            )
            stale_manual = manager.create_project(
                name="Stale Manual",
                verification_status="manual_review",
            )
            stale_manual.verification_page_path.write_text(
                "| Status | Count |\n|---|---:|\n"
                "| Pending | 2 |\n| Manual review | 0 |\n",
                encoding="utf-8",
            )

            finished_label = _verification_status_label(finished)
            manual_label = _verification_status_label(manual)
            stale_manual_label = _verification_status_label(stale_manual)

        self.assertEqual(
            finished_label,
            "Completed - manual review remaining",
        )
        self.assertEqual(manual_label, "Manual review required")
        self.assertEqual(stale_manual_label, "Verification pending")

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

    @patch("definalyzer.app._complete_workflow", return_value=0)
    def test_analyze_is_clear_alias_for_existing_all_command(self, workflow):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output"
            project = WorkspaceManager(root).create_project(name="Alias")

            analyze_code = main(
                ["--workspace", str(root), "analyze", project.slug]
            )
            all_code = main(
                ["--workspace", str(root), "all", project.slug]
            )

        self.assertEqual(analyze_code, 0)
        self.assertEqual(all_code, 0)
        self.assertEqual(workflow.call_count, 2)

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
                        "n",
                        "21",
                    ]
                ),
                print_fn=messages.append,
            )

            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.load_project("menu-project")

        self.assertEqual(exit_code, 0)
        self.assertEqual(project.name, "Menu Project")
        self.assertTrue(any("Obsidian folder" in item for item in messages))

    def test_guided_menu_uses_numbered_entity_type_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output"
            exit_code = main(
                ["--workspace", str(root)],
                input_fn=answers(
                    ["1", "Example Chain", "2", "", "n", "n", "21"]
                ),
                print_fn=lambda message: None,
            )
            project = WorkspaceManager(root).load_project("example-chain")

        self.assertEqual(exit_code, 0)
        self.assertEqual(project.document["entity_type"], "chain")

    def test_guided_menu_deletes_selected_project_after_exact_confirmation(self):
        messages = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output"
            manager = WorkspaceManager(root)
            project = manager.create_project(name="Delete Me")

            exit_code = main(
                ["--workspace", str(root)],
                input_fn=answers(["18", "1", "Delete Me", "21"]),
                print_fn=messages.append,
            )

            self.assertEqual(exit_code, 0)
            self.assertFalse(project.project_root.exists())
            self.assertTrue(any("Deleted project Delete Me" in item for item in messages))

    @patch("definalyzer.app._guided_post_analysis")
    @patch("definalyzer.app._complete_workflow", return_value=0)
    def test_new_project_can_continue_directly_into_analysis(
        self,
        complete_workflow,
        guided_post_analysis,
    ):
        with tempfile.TemporaryDirectory() as directory:
            exit_code = main(
                ["--workspace", str(Path(directory) / "output")],
                input_fn=answers(
                    ["1", "Guided Project", "", "", "n", "y", "21"]
                ),
            )

        self.assertEqual(exit_code, 0)
        complete_workflow.assert_called_once()
        guided_post_analysis.assert_called_once()

    @patch("definalyzer.app._guided_post_analysis")
    @patch("definalyzer.app._complete_workflow", return_value=0)
    def test_existing_project_analysis_uses_same_continuation_path(
        self,
        complete_workflow,
        guided_post_analysis,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output"
            WorkspaceManager(root).create_project(name="Existing")
            exit_code = main(
                ["--workspace", str(root)],
                input_fn=answers(["2", "1", "n", "21"]),
                print_fn=lambda message: None,
            )

        self.assertEqual(exit_code, 0)
        complete_workflow.assert_called_once()
        guided_post_analysis.assert_called_once()

    @patch("definalyzer.app._collect")
    @patch("definalyzer.app._menu_prerequisites_ready", return_value=True)
    def test_declining_planned_menu_collection_does_not_open_standalone(
        self,
        prerequisites,
        standalone,
    ):
        messages = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output"
            WorkspaceManager(root).create_project(name="No Fallthrough")
            exit_code = main(
                ["--workspace", str(root)],
                input_fn=answers(["7", "1", "n", "21"]),
                print_fn=messages.append,
            )

        self.assertEqual(exit_code, 0)
        prerequisites.assert_called_once()
        standalone.assert_not_called()
        self.assertTrue(
            any("was not started" in message for message in messages)
        )

    def test_supported_chain_warning_is_dynamic(self):
        messages = []
        _print_supported_collector_chains(messages.append)

        joined = "\n".join(messages)
        self.assertIn("Ethereum Mainnet", joined)
        self.assertIn("Arbitrum One", joined)
        self.assertIn("Base Mainnet", joined)
        self.assertIn("manual verification tasks", joined)

    @patch("definalyzer.app.write_evidence_summary")
    @patch("definalyzer.app.write_evidence_bundle")
    @patch("definalyzer.app.execute_collection_job")
    def test_guided_planned_collection_writes_evidence_and_updates_stage(
        self,
        execute,
        write_bundle,
        write_summary,
    ):
        execute.return_value = SimpleNamespace(
            records=(SimpleNamespace(request_name="check", status="collected"),)
        )
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Guided Evidence")
            job_path = workspace.jobs_directory / "verification-plan.json"
            job_path.write_text(
                '{"schema_version":1,"name":"guided-verification",'
                '"metadata":{},"requests":[{"name":"check",'
                '"chain":"ethereum","operation":"get_code",'
                '"parameters":{"block":"latest"},"target":{'
                '"target_name":"Example","role":"Core contract",'
                '"address":"0x1111111111111111111111111111111111111111",'
                '"chain":"Ethereum","chain_id":1,'
                '"source":"official docs"}}]}',
                encoding="utf-8",
            )
            ready = _collect_planned_verification(
                manager,
                workspace,
                job_path=job_path,
                print_fn=lambda value: None,
            )
            updated = manager.load_project(workspace.slug)

        self.assertTrue(ready)
        execute.assert_called_once()
        executed_job = execute.call_args.args[0]
        self.assertRegex(
            executed_job.metadata["verification_job_sha256"],
            r"^[0-9a-f]{64}$",
        )
        write_bundle.assert_called_once()
        write_summary.assert_called_once()
        self.assertEqual(
            updated.document["stages"]["evidence_collection"]["status"],
            "complete",
        )
        self.assertEqual(
            updated.document["verification_status"],
            "evidence_collected",
        )

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
        self.assertTrue(any("Project analysis finished" in item for item in messages))

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
                record_research_page(
                    workspace_arg,
                    template_name=template,
                    prompts_root=Path(__file__).parents[1] / "prompts",
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

    @patch("definalyzer.app._registry", return_value=0)
    @patch("definalyzer.app._extract")
    def test_complete_workflow_rebuilds_only_the_stale_research_page(
        self,
        extract,
        registry,
    ):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(name="Selective")
            (project.sources_directory / "source.md").write_text(
                "# Source",
                encoding="utf-8",
            )
            prompts = Path(__file__).parents[1] / "prompts"
            for template, filename in OUTPUT_FILES.items():
                (project.vault_entity_directory / filename).write_text(
                    template,
                    encoding="utf-8",
                )
                record_research_page(
                    project,
                    template_name=template,
                    prompts_root=prompts,
                )
            target = next(iter(OUTPUT_FILES))
            state_path = project.project_root / "dependency-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["research_pages"][target] = "stale"
            state_path.write_text(
                json.dumps(state),
                encoding="utf-8",
            )

            def generate(manager_arg, workspace_arg, **kwargs):
                template = kwargs["template_name"]
                calls.append(template)
                record_research_page(
                    workspace_arg,
                    template_name=template,
                    prompts_root=prompts,
                )
                return 0

            extract.side_effect = generate
            exit_code = main(
                ["--workspace", str(workspace_root), "all", project.slug],
                print_fn=lambda message: None,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [target])
        registry.assert_called_once()

    @patch("definalyzer.app._crawl", return_value=2)
    def test_complete_workflow_recrawls_partial_sources_and_stops(self, crawl):
        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(
                name="Partial",
                docs_url="https://docs.example.test",
            )
            (project.sources_directory / "one-page.md").write_text(
                "# Incomplete",
                encoding="utf-8",
            )
            project = manager.update_stage(
                project,
                "crawl",
                "partial",
                detail="1 saved, 68 failed",
            )

            exit_code = main(
                ["--workspace", str(workspace_root), "all", project.slug],
            )

        self.assertEqual(exit_code, 1)
        crawl.assert_called_once()

    def test_complete_workflow_lock_rejects_overlapping_run(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            project = manager.create_project(name="Locked")

            with _project_workflow_lock(project):
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    with _project_workflow_lock(project):
                        pass

    @patch("definalyzer.app.run_collector_menu", return_value=0)
    def test_standalone_collect_does_not_complete_planned_evidence_stage(
        self, collector
    ):
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
            "not_started",
        )

    @patch("definalyzer.app._collect_planned_verification", return_value=True)
    @patch("definalyzer.app._workflow_prerequisites_ready", return_value=True)
    def test_cli_can_explicitly_collect_planned_verification(
        self,
        prerequisites,
        planned,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output"
            project = WorkspaceManager(root).create_project(name="Planned CLI")
            exit_code = main(
                [
                    "--workspace",
                    str(root),
                    "collect",
                    project.slug,
                    "--planned",
                ],
                print_fn=lambda message: None,
            )

        self.assertEqual(exit_code, 0)
        prerequisites.assert_called_once()
        planned.assert_called_once()

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

    @patch("definalyzer.application.refresh_token_pages_from_registry")
    @patch("definalyzer.application.refresh_market_data")
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

    @patch("definalyzer.app.create_provider")
    def test_dune_command_creates_optional_query_dialogue(self, create_provider):
        create_provider.return_value = SimpleNamespace(
            name="fake",
            generate=lambda prompt, working_directory: ProviderResponse(
                text=(
                    "## Assumptions\n- Contract must be confirmed.\n"
                    "## SQL\n```sql\nSELECT 1 AS amount\n```\n"
                    "## Expected output\nOne row.\n"
                    "## Limitations\nNo verification decision."
                ),
                provider="fake",
                command=("fake",),
            ),
        )
        messages = []
        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "output"
            manager = WorkspaceManager(workspace_root)
            project = manager.create_project(name="Dune Project")
            project.verification_page_path.write_text(
                "# Dune Project — Verification\n\n## Fees\n\n"
                "### VR-FEE-001 — Fees\n\n| Field | Value |\n|---|---|\n"
                "| Status | Pending |\n| Claim | Fees accrue. |\n"
                "| Claim type | On-chain state/events |\n"
                "| Evidence availability | Public |\n"
                "| Recommended method | Dune candidate |\n"
                "| Optional Dune query | Available |\n"
                "| Check route | Manual |\n| How to check | Query events. |\n"
                "| Likely source | Ethereum data. |\n"
                "| Evidence required | Fee totals. |\n",
                encoding="utf-8",
            )
            state = project.project_root / "verification-planning"
            state.mkdir(parents=True)
            (state / "verification-catalog.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "entity": "Dune Project",
                        "entries": [
                            {
                                "id": "VR-FEE-001",
                                "title": "Fees",
                                "claim": "Fees accrue.",
                                "claim_type": "On-chain state/events",
                                "evidence_availability": "Public",
                                "recommended_method": "Dune candidate",
                                "dune_eligible": True,
                                "check_route": "Manual",
                                "status": "Pending",
                                "evidence_required": "Fee totals.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            exit_code = main(
                [
                    "--workspace",
                    str(workspace_root),
                    "dune",
                    project.slug,
                    "VR-FEE-001",
                ],
                print_fn=messages.append,
            )
            session_exists = (
                project.project_root
                / "dune-assistant"
                / "vr-fee-001.json"
            ).exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(session_exists)
        self.assertTrue(any("was not executed" in item for item in messages))

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
