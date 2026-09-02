import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from definalyzer.dashboard import (
    _coin_pages,
    _execute_job,
    _project_pages,
    _parse_progress_message,
    _read_vault_page,
    _token_pages,
    create_dashboard_server,
    render_markdown,
)
from definalyzer.application import DefinalyzerApplication
from definalyzer.source_coverage import load_source_coverage
from definalyzer.workspace import WorkspaceManager


class DashboardRenderingTests(unittest.TestCase):
    def test_wide_tables_have_keyboard_accessible_scroll_containers(self):
        rendered = render_markdown(
            "| Risk | Cause | Impact | Mitigation |\n"
            "|---|---|---|---|\n"
            "| Risk one | Cause one | Impact one | Mitigation one |\n"
        )
        self.assertIn('class="table-wrap" tabindex="0" role="region"', rendered)
        self.assertIn('aria-label="Table: scroll sideways to read all columns"', rendered)
        self.assertEqual(rendered.count('<td>'), 4)

    def test_numbered_workflow_progress_is_parsed_without_inventing_percentages(self):
        self.assertEqual(
            _parse_progress_message("[3/5] Building registry and current supply data"),
            (3, 5, "Building registry and current supply data"),
        )
        self.assertIsNone(_parse_progress_message("Waiting for Hermes"))
        self.assertIsNone(_parse_progress_message("[7/5] Invalid stage"))

    def test_renderer_escapes_html_and_preserves_wikilink_alias_in_table(self):
        rendered = render_markdown(
            "| Project | Status |\n"
            "| --- | --- |\n"
            "| [[Protocols/Aave V3/Index|Aave V3]] | Ready |\n\n"
            "<script>alert(1)</script>\n"
        )
        self.assertIn(">Aave V3</a>", rendered)
        self.assertEqual(rendered.count("<td>"), 2)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn(">Material Permissions</a>", render_markdown("[[#Material Permissions]]"))
        linked = render_markdown(
            "[[Verification/Aave V3/Index#^vr-risk-001\\|verification]]\n\n"
            "^vr-risk-001"
        )
        self.assertIn(">verification</a>", linked)
        self.assertIn('id="vr-risk-001"', linked)

    def test_renderer_hides_generated_frontmatter(self):
        rendered = render_markdown(
            "---\nentity: Aave V3\nverification_status: pending\n---\n\n# Overview\n\nFact."
        )
        self.assertNotIn("verification_status", rendered)
        self.assertNotIn("entity:", rendered)
        self.assertIn("Overview", rendered)

    def test_renderer_hides_collector_and_other_machine_only_markup(self):
        rendered = render_markdown(
            "# Verification\n\nReadable check.\n\n"
            "<!-- definalyzer-verification-links:start -->\n"
            "Verification: [[Verification/Example/Index|VR-001]]\n"
            "<!-- definalyzer-verification-links:end -->\n\n"
            "## Collector Requests\n\n"
            "```definalyzer-verification\n"
            '{"schema_version": 1, "requests": []}\n'
            "```\n"
        )
        self.assertIn("Readable check", rendered)
        self.assertNotIn("Collector Requests", rendered)
        self.assertNotIn("schema_version", rendered)
        self.assertNotIn("definalyzer-verification-links", rendered)
        self.assertIn("VR-001", rendered)

    def test_project_page_inventory_and_path_boundary(self):
        with TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            page = workspace.vault_entity_directory / "Overview.md"
            page.write_text("# Overview\n\nFact.", encoding="utf-8")
            pages = _project_pages(workspace)
            self.assertTrue(any(row["title"] == "Overview" for row in pages))
            document = _read_vault_page(
                manager, "Protocols/Example/Overview.md"
            )
            self.assertEqual(document["title"], "Overview")
            with self.assertRaises(ValueError):
                _read_vault_page(manager, "../../outside.md")

    def test_shared_token_inventory_links_generated_page_to_project(self):
        with TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            workspace.registry_directory.mkdir(parents=True, exist_ok=True)
            (workspace.registry_directory / "registry.json").write_text(
                json.dumps({"tokens": [{"symbol": "EXM"}]}), encoding="utf-8"
            )
            token_page = workspace.vault_root / "Tokens" / "EXM" / "Index.md"
            token_page.parent.mkdir(parents=True, exist_ok=True)
            token_page.write_text("# EXM\n\nToken facts.", encoding="utf-8")

            tokens = _token_pages(manager)

            self.assertEqual(tokens, [{
                "symbol": "EXM",
                "title": "EXM",
                "path": "Tokens/EXM/Index.md",
                "projects": [workspace.slug],
            }])

    def test_shared_coin_inventory_links_generated_page_to_chain(self):
        with TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example Chain", entity_type="chain")
            (workspace.registry_directory / "registry.json").write_text(
                json.dumps({"tokens": [{"symbol": "EXC"}]}), encoding="utf-8"
            )
            coin_page = workspace.vault_root / "Coins" / "EXC" / "Index.md"
            coin_page.parent.mkdir(parents=True, exist_ok=True)
            coin_page.write_text("# EXC\n\nCoin facts.", encoding="utf-8")

            coins = _coin_pages(manager)

            self.assertEqual(coins[0]["path"], "Coins/EXC/Index.md")
            self.assertEqual(coins[0]["projects"], [workspace.slug])
            pages = _project_pages(workspace)
            self.assertTrue(
                any(row["path"] == "Coins/EXC/Index.md" and row["group"] == "Coins" for row in pages)
            )

    def test_source_job_uses_existing_source_workflow(self):
        with TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            result = _execute_job(
                DefinalyzerApplication(manager),
                action="source",
                project=workspace.slug,
                payload={
                    "source_action": "add",
                    "category": "tokenomics",
                    "url": "https://example.test/token",
                },
                progress=lambda message: None,
            )
            self.assertEqual(result["exit_code"], 0)
            coverage = load_source_coverage(workspace)
            self.assertEqual(coverage.categories["tokenomics"], "registered")


class DashboardHttpTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.manager = WorkspaceManager(Path(self.temporary.name) / "output")
        self.server = create_dashboard_server(self.manager, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def _json(self, path, *, data=None, token=None):
        body = json.dumps(data).encode() if data is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-DEFINALYZER-Token"] = token
        request = Request(self.base + path, data=body, headers=headers)
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())

    def test_bootstrap_create_and_project_read(self):
        status, bootstrap = self._json("/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertEqual(bootstrap["projects"], [])
        self.assertEqual(bootstrap["tokens"], [])
        self.assertEqual(bootstrap["coins"], [])
        status, created = self._json(
            "/api/projects",
            token=bootstrap["token"],
            data={
                "name": "Dashboard Project",
                "entity_type": "protocol",
                "docs_url": "https://docs.example.test",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["project"]["slug"], "dashboard-project")
        status, detail = self._json("/api/projects/dashboard-project")
        self.assertEqual(status, 200)
        self.assertEqual(detail["project"]["name"], "Dashboard Project")

    def test_dashboard_guide_is_available(self):
        status, guide = self._json("/api/dashboard-guide")
        self.assertEqual(status, 200)
        self.assertIn("Basic workflow", guide["markdown"])
        self.assertIn("<h2", guide["html"])

    def test_mutation_requires_session_token(self):
        with self.assertRaises(HTTPError) as raised:
            self._json("/api/projects", data={"name": "Rejected"})
        self.assertEqual(raised.exception.code, 403)

    def test_mutation_rejects_another_local_origin_even_with_token(self):
        _, bootstrap = self._json("/api/bootstrap")
        request = Request(
            self.base + "/api/projects",
            data=json.dumps({"name": "Rejected Origin"}).encode(),
            headers={"Content-Type": "application/json",
                     "X-DEFINALYZER-Token": bootstrap["token"],
                     "Origin": "http://localhost:12345"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=3)
        self.assertEqual(raised.exception.code, 403)
        raised.exception.close()
        self.assertEqual(self.manager.list_projects(), [])

    def test_mutation_accepts_dashboard_origin(self):
        _, bootstrap = self._json("/api/bootstrap")
        request = Request(
            self.base + "/api/projects",
            data=json.dumps({"name": "Same Origin"}).encode(),
            headers={"Content-Type": "application/json",
                     "X-DEFINALYZER-Token": bootstrap["token"],
                     "Origin": self.base},
        )
        with urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 201)

    def test_untrusted_host_cannot_read_bootstrap(self):
        for host in ("attacker.example", "127.0.0.1:1"):
            request = Request(self.base + "/api/bootstrap", headers={"Host": host})
            with self.assertRaises(HTTPError) as raised:
                urlopen(request, timeout=3)
            self.assertEqual(raised.exception.code, 403)
            raised.exception.close()


if __name__ == "__main__":
    unittest.main()
