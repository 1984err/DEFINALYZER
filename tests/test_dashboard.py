import json
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from definalyzer.dashboard import (
    DashboardJobManager,
    _dashboard_chart_requests,
    _dashboard_message,
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
    def test_running_job_is_marked_interrupted_after_dashboard_restart(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "output"
            root.mkdir(parents=True)
            (root / "dashboard-jobs.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "jobs": [
                            {
                                "job_id": "abc123",
                                "action": "analyze",
                                "project": "example",
                                "status": "running",
                                "created_at": "2026-09-04T10:00:00+00:00",
                                "started_at": "2026-09-04T10:00:01+00:00",
                                "last_activity_at": "2026-09-04T10:05:00+00:00",
                                "progress_current": 67,
                                "progress_total": 85,
                                "progress_label": "Saved chunk-0067",
                                "messages": ["[67/85] Saved chunk-0067"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            jobs = DashboardJobManager(
                DefinalyzerApplication(WorkspaceManager(root))
            )
            try:
                restored = jobs.get("abc123")
            finally:
                jobs.close()

        self.assertEqual(restored["status"], "interrupted")
        self.assertEqual(restored["progress_current"], 67)
        self.assertEqual(restored["progress_total"], 85)
        self.assertIn("ended before this job completed", restored["error"])

    def test_reader_renders_encoded_spaces_without_decoding_html(self):
        rendered=render_markdown('Text&#x20;here&#32;too. &#x3c;script&#x3e;')
        self.assertIn('Text here too.',rendered)
        self.assertIn('&amp;#x3c;',rendered)
        self.assertNotIn('<script>',rendered)

    def test_reader_hides_internal_link_map_but_preserves_readable_checks(self):
        markdown = (
            "# Example - Verification\n\n## Governance\n\n"
            "| Research source | [[Protocols/Example/Governance|Governance]] |\n\n"
            "## Research Link Map\n\n"
            "| Verification ID | Research Note | Claim Location | Obsidian Link |\n"
            "|---|---|---|---|\n"
            "| VR-GOV-001 | Governance | Authority | internal mapping |\n\n"
            "## Analyst Notes\n\nKeep this readable note.\n"
        )
        rendered = render_markdown(markdown)
        self.assertNotIn("Research Link Map", rendered)
        self.assertNotIn("Obsidian", rendered)
        self.assertNotIn("internal mapping", rendered)
        self.assertIn("Keep this readable note.", rendered)
        self.assertIn('class="wiki-link"', rendered)
        self.assertIn("Obsidian Link", markdown)

    def test_activity_uses_dashboard_terminology(self):
        self.assertEqual(
            _dashboard_message("Obsidian vault: output/vault"),
            "Research folder: output/vault",
        )
        self.assertEqual(
            _dashboard_message("Refreshed 5 Obsidian vault indexes."),
            "Refreshed 5 Research folder indexes.",
        )

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

    def test_management_report_has_numbered_sources_and_clean_details(self):
        rendered = render_markdown(
            "# Revenue Review\n\nClaim. [^E-008]\n"
            "  - Limitation: Dated evidence only.\n\n"
            "## Evidence Notes\n\n[^E-008]: saved/revenue.md; lines 2-8.\n",
            management_report=True,
        )
        self.assertIn('href="#source-1">1</a>', rendered)
        self.assertIn('class="report-detail"', rendered)
        self.assertIn('id="sources"', rendered)
        self.assertIn('class="report-source" id="source-1"', rendered)
        self.assertNotIn("E-008", rendered)

    def test_management_report_uses_human_status_and_dates(self):
        rendered = render_markdown(
            "# Review\n\n"
            "> Draft generated from a bounded evidence package. It has not passed quality review or human approval.\n\n"
            "- Evidence captured: 2026-09-03T20:17:06+00:00\n\n"
            "## Qualified Conclusion\n\n**Stance:** Answer\n",
            management_report=True,
        )
        self.assertIn("Working report", rendered)
        self.assertNotIn("has not passed quality review", rendered)
        self.assertIn("Evidence package: September 3, 2026", rendered)
        self.assertIn("Assessment:</strong> Answered with material limitations", rendered)

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
                json.dumps({"tokens": [{"symbol": "EXC", "asset_kind": "coin"}]}), encoding="utf-8"
            )
            coin_page = workspace.vault_root / "Coins" / "EXC" / "Index.md"
            coin_page.parent.mkdir(parents=True, exist_ok=True)
            coin_page.write_text("# EXC\n\nCoin facts.", encoding="utf-8")

            coins = _coin_pages(manager)

            self.assertEqual(coins[0]["path"], "Coins/EXC/Index.md")
            self.assertEqual(coins[0]["projects"], [workspace.slug])
            pages = _project_pages(workspace)
            self.assertTrue(
                any(row["path"] == "Coins/EXC/Index.md" and row["group"] == "Related asset research" for row in pages)
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

    def test_dashboard_chart_request_accepts_paths_but_not_values(self):
        charts = _dashboard_chart_requests({
            "chart_title": "Supply", "chart_evidence_id": "E-004",
            "chart_unit": "tokens",
            "chart_fields": "Circulating=supply.circulating\nMaximum=supply.maximum",
        })
        self.assertEqual(charts[0].fields, (
            ("Circulating", "supply.circulating"),
            ("Maximum", "supply.maximum"),
        ))
        with self.assertRaisesRegex(ValueError, "Label=path"):
            _dashboard_chart_requests({
                "chart_title": "Supply", "chart_evidence_id": "E-004",
                "chart_unit": "tokens", "chart_fields": "1000000",
            })


class DashboardHttpTests(unittest.TestCase):
    def test_combined_report_job_and_pdf_download_without_finalization(self):
        from tests.test_application_reports import ReportProvider
        self.server.application._provider_factory = lambda settings: ReportProvider()
        workspace = self.server.application.create_project(name="Combined Report")
        (workspace.vault_entity_directory / "Economics.md").write_text(
            "# Economics\n\n## Fees\n\nDocumented fees can vary.\n", encoding="utf-8")
        self.server.application.create_report(workspace=workspace, title="Fees", mode="question", question="Are fees predictable?")
        _, bootstrap = self._json("/api/bootstrap")
        self._run_report_job(workspace, bootstrap["token"], "report-generate", report_id="fees")
        _, detail = self._json(f"/api/projects/{workspace.slug}/reports/fees")
        self.assertEqual(detail["report"]["status"], "quality_reviewed")
        before = {p:p.read_bytes() for p in workspace.root.rglob("*") if p.is_file() and p.name != ".dashboard-instance.lock"}
        with urlopen(self.base + f"/api/projects/{workspace.slug}/reports/fees/download.pdf") as response:
            self.assertEqual(response.headers["Content-Type"], "application/pdf")
            self.assertIn("attachment", response.headers["Content-Disposition"])
            self.assertTrue(response.read().startswith(b"%PDF"))
        self.assertEqual(before, {p:p.read_bytes() for p in workspace.root.rglob("*") if p.is_file() and p.name != ".dashboard-instance.lock"})

    def test_experimental_actions_are_rejected_without_jobs_or_output_changes(self):
        workspace = self.manager.create_project(name="Recovery")
        dormant = workspace.project_root / "scope" / "scope.json"
        dormant.parent.mkdir(parents=True)
        dormant.write_text("invalid dormant scope", encoding="utf-8")
        _, detail = self._json(f"/api/projects/{workspace.slug}")
        self.assertIsNone(detail["scope"])
        _, bootstrap = self._json("/api/bootstrap")
        before = {p: p.read_bytes() for p in workspace.project_root.rglob("*") if p.is_file()}
        for action in ("scope", "scope-adjust", "research-retry", "prepare-research",
                       "report-refresh", "report-edit", "report-reconcile", "report-draft"):
            with self.subTest(action=action), self.assertRaises(HTTPError) as denied:
                self._json(f"/api/projects/{workspace.slug}/jobs", token=bootstrap["token"],
                           data={"action": action, "report_id": "v2-saved"})
            self.assertEqual(denied.exception.code, 400)
        with self.assertRaises(HTTPError) as denied:
            self._json(f"/api/projects/{workspace.slug}/reports", token=bootstrap["token"],
                       data={"title":"Disabled", "mode":"full_review", "schema_version":2})
        self.assertEqual(denied.exception.code, 400)
        self.assertEqual(self.server.jobs.list(), [])
        self.assertEqual(before, {p:p.read_bytes() for p in workspace.project_root.rglob("*") if p.is_file()})

    def test_named_asset_has_own_http_research_context_and_requires_session_token(self):
        from tests.test_asset_identity import token
        from definalyzer.registry_workflow import upsert_manual_token
        workspace = self.manager.create_project(name="Origin protocol")
        row = upsert_manual_token(workspace=workspace, token=token()).tokens[0]
        _, bootstrap = self._json("/api/bootstrap")
        self.assertEqual(bootstrap["tokens"][0]["title"], "Example Token (EX)")
        route = f"/api/assets/{row.asset_id}/research"
        with self.assertRaises(HTTPError) as denied:
            self._json(route, data={})
        self.assertEqual(denied.exception.code, 403)
        status, response = self._json(route, data={}, token=bootstrap["token"])
        self.assertEqual(status, 201)
        self.assertEqual(response["project"]["entity_type"], "token")
        slug = response["project"]["slug"]
        _, again = self._json(route, data={}, token=bootstrap["token"])
        self.assertEqual(again["project"]["slug"], slug)
        _, refreshed = self._json("/api/bootstrap")
        self.assertEqual(len(refreshed["tokens"]), 1)
        self.assertEqual(refreshed["tokens"][0]["subject_projects"], [slug])

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

    def _wait_for_job(self, job_id, *, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            _, job = self._json(f"/api/jobs/{job_id}")
            if job["status"] not in {"queued", "running"}:
                return job
            time.sleep(0.02)
        self.fail(f"Dashboard job did not finish: {job_id}")

    def _run_report_job(self, workspace, token, action, **payload):
        status, response = self._json(
            f"/api/projects/{workspace.slug}/jobs",
            token=token,
            data={"action": action, **payload},
        )
        self.assertEqual(status, 202)
        job = self._wait_for_job(response["job"]["job_id"])
        self.assertEqual(job["status"], "complete", job.get("error"))
        return job

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

    def test_dashboard_assets_include_report_lifecycle_interface(self):
        with urlopen(self.base + "/", timeout=3) as response:
            page = response.read().decode()
        with urlopen(self.base + "/assets/app.js", timeout=3) as response:
            script = response.read().decode()
        self.assertIn('id="reports-dialog"', page)
        self.assertIn('"Reports","Create, review, finalize, and export analysis"', script)
        self.assertIn('startReportJob("finalize"', script)
        self.assertIn("Read analyst notes", script)

    def test_delete_reports_preserves_research_and_requires_authentication_and_idle_project(self):
        from unittest.mock import patch
        from definalyzer.report_v2_store import create
        workspace = self.manager.create_project(name="Delete reports")
        notes = workspace.vault_entity_directory / "Notes.md"
        notes.write_text("Keep research", encoding="utf-8")
        normal = self.server.application.create_report(workspace=workspace, title="Normal", mode="full_review")
        experimental = create(workspace, title="Experimental", mode="full_review")
        _, bootstrap = self._json("/api/bootstrap")
        for report_id, directory in ((normal.report_id, workspace.reports_directory / normal.report_id),
                                      (experimental['report_id'], workspace.reports_directory / "V2" / experimental['report_id'])):
            with self.subTest(report_id=report_id):
                before = {p.relative_to(directory):p.read_bytes() for p in directory.rglob('*') if p.is_file()}
                route = f"/api/projects/{workspace.slug}/reports/{report_id}/delete"
                with self.assertRaises(HTTPError) as denied:
                    self._json(route, data={})
                self.assertEqual(denied.exception.code,403)
                with patch.object(self.server.jobs, 'has_active', return_value=True), self.assertRaises(HTTPError):
                    self._json(route, data={}, token=bootstrap['token'])
                self.assertTrue(directory.exists())
                _, result = self._json(route, data={}, token=bootstrap['token'])
                archive=Path(result['archived_to'])
                self.assertFalse(directory.exists())
                self.assertTrue(archive.is_relative_to(self.manager.root / 'trash'))
                self.assertEqual(before,{p.relative_to(archive):p.read_bytes() for p in archive.rglob('*') if p.is_file()})
        self.assertEqual(notes.read_text(), 'Keep research')
        self.assertEqual(self.server.application.reports(workspace), ())
        with self.assertRaises(ValueError):
            self.server.application.delete_report(workspace=workspace, report_id='../outside')

    def test_clear_activity_requires_authentication_and_preserves_active_jobs(self):
        from definalyzer.dashboard import DashboardJob
        jobs=self.server.jobs
        jobs._jobs={'done':DashboardJob('done','analyze',None,status='failed'),
                    'active':DashboardJob('active','analyze',None,status='running'),
                    'cancelled':DashboardJob('cancelled','analyze',None,status='cancelled')}
        jobs._cancellations['active']=threading.Event()
        _, bootstrap=self._json('/api/bootstrap')
        with self.assertRaises(HTTPError) as denied:self._json('/api/jobs/clear',data={})
        self.assertEqual(denied.exception.code,403)
        _, result=self._json('/api/jobs/clear',data={},token=bootstrap['token'])
        self.assertEqual(result['cleared'],2)
        self.assertEqual([j['job_id'] for j in result['jobs']],['active'])
        self.assertEqual([j['job_id'] for j in json.loads(jobs._state_path.read_text())['jobs']],['active'])
        jobs._run('cancelled',{})  # A cleared queued cancellation cannot dispatch work.
        archived=list((self.manager.root/'trash/activity').glob('*.json'))
        self.assertEqual(len(archived),1)
        self.assertEqual(len(json.loads(archived[0].read_text())['jobs']),2)
        jobs._jobs['active'].status='complete'

    def test_report_scope_and_detail_are_available_through_dashboard_api(self):
        _, bootstrap = self._json("/api/bootstrap")
        workspace = self.server.application.create_project(name="Report Project")
        status, created = self._json(
            f"/api/projects/{workspace.slug}/reports",
            token=bootstrap["token"],
            data={
                "title": "Risk Review", "mode": "question",
                "question": "What is the material risk?",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["report"]["status"], "scoped")
        _, project = self._json(f"/api/projects/{workspace.slug}")
        self.assertEqual(project["reports"][0]["report_id"], "risk-review")
        _, detail = self._json(
            f"/api/projects/{workspace.slug}/reports/risk-review"
        )
        self.assertEqual(detail["assertions"], [])

    def test_report_jobs_complete_full_dashboard_lifecycle_in_order(self):
        from tests.test_application_reports import ReportProvider

        _, bootstrap = self._json("/api/bootstrap")
        token = bootstrap["token"]
        self.server.application._provider_factory = lambda settings: ReportProvider()
        workspace = self.server.application.create_project(name="Lifecycle Project")
        (workspace.vault_entity_directory / "Economics.md").write_text(
            "# Economics\n\n## Fees\n\nDocumented fees can vary.\n",
            encoding="utf-8",
        )
        self._json(
            f"/api/projects/{workspace.slug}/reports",
            token=token,
            data={
                "title": "Fee Reliability", "mode": "question", "schema_version": 1,
                "question": "Are documented fees predictable?",
            },
        )

        # An invalid step is rejected before it becomes a background job.
        with self.assertRaises(HTTPError) as raised:
            self._json(
                f"/api/projects/{workspace.slug}/jobs",
                token=token,
                data={"action": "report-draft", "report_id": "fee-reliability"},
            )
        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()

        self._run_report_job(
            workspace, token, "report-evidence", report_id="fee-reliability"
        )
        self._run_report_job(
            workspace, token, "report-draft", report_id="fee-reliability"
        )
        self._run_report_job(
            workspace, token, "report-quality", report_id="fee-reliability"
        )
        self._run_report_job(
            workspace, token, "report-finalize", report_id="fee-reliability",
            human_approved=True,
        )
        self._run_report_job(
            workspace, token, "report-export", report_id="fee-reliability",
            markdown=True, html=True, pdf=True,
        )

        _, detail = self._json(f"/api/projects/{workspace.slug}")
        report = detail["reports"][0]
        self.assertEqual(report["status"], "final")
        self.assertTrue(report["analyst_notes_page"].endswith("/Analyst-Notes.md"))
        self.assertEqual(report["export_revisions"], [0])
        self.assertFalse(report["actions"]["export"]["available"])

    def test_report_job_rejects_unknown_report_before_queueing(self):
        _, bootstrap = self._json("/api/bootstrap")
        workspace = self.server.application.create_project(name="Missing Report")
        with self.assertRaises(HTTPError) as raised:
            self._json(
                f"/api/projects/{workspace.slug}/jobs",
                token=bootstrap["token"],
                data={"action": "report-evidence", "report_id": "not-here"},
            )
        self.assertEqual(raised.exception.code, 404)
        raised.exception.close()
        _, jobs = self._json("/api/jobs")
        self.assertEqual(jobs["jobs"], [])

    def test_final_report_exports_are_integrity_checked_when_served(self):
        from tests.test_application_reports import ReportProvider

        self.server.application._provider_factory = lambda settings: ReportProvider()
        workspace = self.server.application.create_project(name="Published Project")
        (workspace.vault_entity_directory / "Economics.md").write_text(
            "# Economics\n\n## Fees\n\nDocumented fees can vary.\n",
            encoding="utf-8",
        )
        app = self.server.application
        app.create_report(
            workspace=workspace, title="Fee Review", mode="question",
            question="Are fees predictable?", schema_version=1,
        )
        app.prepare_report_evidence(workspace=workspace, report_id="fee-review")
        app.generate_report(workspace=workspace, report_id="fee-review")
        app.review_report(workspace=workspace, report_id="fee-review")
        app.finalize_report(
            workspace=workspace, report_id="fee-review", human_approved=True
        )
        result = app.export_report(
            workspace=workspace, report_id="fee-review",
            formats=("markdown", "html", "pdf"),
        )
        base = (
            f"{self.base}/api/projects/{workspace.slug}/reports/fee-review/"
            "exports/revision-0000/"
        )
        with urlopen(base + "Report.pdf", timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "application/pdf")
            self.assertTrue(response.read().startswith(b"%PDF"))
        with urlopen(base + "Report.html", timeout=3) as response:
            self.assertIn(b"<!doctype html>", response.read())
            self.assertIn("script-src 'none'", response.headers["Content-Security-Policy"])
        with urlopen(base + "Analyst-Notes.md", timeout=3) as response:
            self.assertIn(b"Answer Readiness", response.read())
        result.markdown_path.write_text("changed", encoding="utf-8")
        with self.assertRaises(HTTPError) as raised:
            urlopen(base + "Report.md", timeout=3)
        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()

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
