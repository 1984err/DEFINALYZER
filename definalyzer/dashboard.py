"""Local dashboard shell for the existing DEFINALYZER application.

The dashboard deliberately keeps Markdown and project JSON as the canonical
data.  It is a loopback-only reader/controller, not a second research system.
"""

from __future__ import annotations

import html
import json
import re
import secrets
import threading
import traceback
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import parse_qs, quote, unquote, urlparse

from .application import DefinalyzerApplication
from .evaluation import pending_proposals, review_proposal
from .registry_workflow import TokenRecord, upsert_manual_token
from .report_contract import content_sha256, report_package
from .report_export import ChartRequest, download_report_pdf
from .report_presentation import management_report_markdown
from .source_coverage import load_source_coverage
from .workspace import ProjectWorkspace, WorkspaceManager
from .cancellation import cancellation_scope, check_cancelled, OperationCancelled


DASHBOARD_SCHEMA_VERSION = 1
DEFAULT_PORT = 0
ASSET_ROOT = Path(__file__).with_name("dashboard_assets")
DASHBOARD_GUIDE = Path(__file__).resolve().parent.parent / "docs" / "DASHBOARD_README.md"
MAX_REQUEST_BYTES = 128_000
JOB_ACTIONS = {
    "prepare-research",
    "analyze",
    "scope",
    "scope-adjust",
    "crawl",
    "research",
    "research-retry",
    "registry",
    "verification-plan",
    "collect-evidence",
    "evaluate",
    "market-data",
    "ask",
    "refresh-indexes",
    "provider-test",
    "provider-config",
    "source",
    "manual-token",
    "report-evidence",
    "report-generate",
    "report-draft",
    "report-quality",
    "report-revise",
    "report-finalize",
    "report-export",
    "report-refresh", "report-edit", "report-reconcile",
}
REPORT_JOB_ACTIONS = {
    "report-generate",
    "report-evidence", "report-draft", "report-quality", "report-revise",
    "report-finalize", "report-export", "report-refresh", "report-edit", "report-reconcile",
}
REPORT_ACTION_AVAILABILITY_KEYS = {
    "report-generate": "generate",
    "report-evidence": "prepare_evidence",
    "report-draft": "generate_draft",
    "report-quality": "review_quality",
    "report-revise": "revise",
    "report-finalize": "finalize",
    "report-export": "export",
    "report-refresh": "refresh_evidence", "report-edit": "edit", "report-reconcile": "reconcile",
}
ACTION_AVAILABILITY_KEYS = {
    "scope": "scope",
    "prepare-research": "scope",
    "scope-adjust": "scope_adjust",
    "analyze": "analyze",
    "crawl": "crawl",
    "research": "research",
    "research-retry": "research",
    "registry": "registry",
    "verification-plan": "verification_plan",
    "collect-evidence": "collect_evidence",
    "evaluate": "evaluate_evidence",
    "market-data": "market_data",
    "ask": "ask",
    "source": "official_sources",
    "manual-token": "manual_token",
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class DashboardJob:
    job_id: str
    action: str
    project: str | None
    status: str = "queued"
    created_at: str = field(default_factory=_timestamp)
    started_at: str | None = None
    finished_at: str | None = None
    last_activity_at: str | None = None
    progress_current: int | None = None
    progress_total: int | None = None
    progress_label: str | None = None
    messages: list[str] = field(default_factory=list)
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DashboardJobManager:
    """Run one mutating/AI workflow at a time and expose honest progress."""

    def __init__(self, application: DefinalyzerApplication) -> None:
        self.application = application
        self._state_path = application.manager.root / "dashboard-jobs.json"
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="definalyzer-dashboard"
        )
        self._jobs: dict[str, DashboardJob] = {}
        self._cancellations: dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._load_persisted_jobs()

    def _load_persisted_jobs(self) -> None:
        if not self._state_path.exists():
            return
        try:
            document = json.loads(self._state_path.read_text(encoding="utf-8"))
            rows = document.get("jobs", [])
            if not isinstance(rows, list):
                raise ValueError("jobs must be a list")
            field_names = set(DashboardJob.__dataclass_fields__)
            for row in rows[:50]:
                if not isinstance(row, dict):
                    continue
                values = {key: value for key, value in row.items() if key in field_names}
                job = DashboardJob(**values)
                if job.status in {"queued", "running", "stopping"}:
                    job.status = "interrupted"
                    job.finished_at = _timestamp()
                    job.error = (
                        "The dashboard process ended before this job completed. "
                        "Its saved project outputs may be resumed, but this run "
                        "did not finish."
                    )
                self._jobs[job.job_id] = job
            self._persist_locked()
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            # A damaged activity history must not prevent access to project data.
            self._jobs = {}

    def _persist_locked(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(
            self._jobs.values(), key=lambda row: row.created_at, reverse=True
        )[:50]
        document = {"schema_version": 1, "jobs": [row.to_dict() for row in rows]}
        temporary = self._state_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._state_path)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = sorted(
                self._jobs.values(), key=lambda row: row.created_at, reverse=True
            )
            return [row.to_dict() for row in rows[:50]]

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id].to_dict()

    def clear_finished(self) -> dict[str, Any]:
        """Clear terminal activity, keeping active jobs and an offline diagnostic copy."""
        with self._lock:
            finished = [job for job in self._jobs.values() if job.status in
                        {"complete", "failed", "cancelled", "interrupted", "needs_attention"}]
            if not finished:
                return {"cleared": 0, "jobs": [job.to_dict() for job in self._jobs.values()]}
            archive = self.application.manager.root / "trash" / "activity" / (secrets.token_hex(16) + ".json")
            if not archive.resolve().is_relative_to(self.application.manager.root.resolve()):
                raise ValueError("Activity archive escapes the workspace.")
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_text(json.dumps({"jobs": [job.to_dict() for job in finished]}, indent=2), encoding="utf-8")
            for job in finished:
                self._jobs.pop(job.job_id)
                self._cancellations.pop(job.job_id, None)
            self._persist_locked()
            return {"cleared": len(finished), "jobs": [job.to_dict() for job in self._jobs.values()]}

    def has_active(self, project: str) -> bool:
        with self._lock:
            return any(
                row.project == project and row.status in {"queued", "running", "stopping"}
                for row in self._jobs.values()
            )

    def close(self) -> None:
        for job in self.list():
            if job["status"] in {"queued", "running", "stopping"}:
                self.cancel(job["job_id"])
        self._executor.shutdown(wait=True, cancel_futures=True)

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs[job_id]
            if job.status not in {"queued", "running", "stopping"}:
                return job.to_dict()
            self._cancellations[job_id].set()
            if job.status == "queued":
                job.status = "cancelled"
                job.finished_at = _timestamp()
                job.error = "Stopped before starting."
            elif job.status == "running":
                job.status = "stopping"
                job.messages.append("Stop requested. Ending the active request and retaining saved checkpoints; no further steps will start.")
            job.last_activity_at = _timestamp()
            self._persist_locked()
            return job.to_dict()

    def submit(
        self,
        *,
        action: str,
        project: str | None,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if action not in JOB_ACTIONS:
            raise ValueError(f"Unsupported dashboard action: {action}")
        job = DashboardJob(
            job_id=secrets.token_hex(8), action=action, project=project
        )
        with self._lock:
            self._jobs[job.job_id] = job
            self._cancellations[job.job_id] = threading.Event()
            self._persist_locked()
        self._executor.submit(self._run, job.job_id, dict(payload))
        return job.to_dict()

    def _run(self, job_id: str, payload: dict[str, Any]) -> None:
        started_at = _timestamp()
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return  # A cancelled queued job may have been cleared before dispatch.
            if job.status == "cancelled":
                return
            event = self._cancellations[job_id]
            job.status = "running"
            job.started_at = job.last_activity_at = started_at
            self._persist_locked()

        def progress(message: str) -> None:
            check_cancelled()
            with self._lock:
                job = self._jobs[job_id]
                text = _dashboard_message(str(message))
                job.messages.append(text)
                del job.messages[:-250]
                job.last_activity_at = _timestamp()
                parsed = _parse_progress_message(text)
                if parsed is not None:
                    job.progress_current, job.progress_total, job.progress_label = parsed
                self._persist_locked()

        try:
            with cancellation_scope(event):
                result = _execute_job(
                    self.application,
                    action=self._jobs[job_id].action,
                    project=self._jobs[job_id].project,
                    payload=payload,
                    progress=progress,
                )
                check_cancelled()
        except BaseException as exc:  # futures must not strand interrupted jobs as running
            if isinstance(exc, OperationCancelled) or event.is_set():
                self._update(job_id, status="cancelled", finished_at=_timestamp(), last_activity_at=_timestamp(),
                             error="Stopped at your request. Saved checkpoints retained. This job will not restart automatically.")
                return
            progress(traceback.format_exc(limit=5))
            self._update(
                job_id,
                status="failed" if isinstance(exc, Exception) else "interrupted",
                finished_at=_timestamp(),
                error=f"{type(exc).__name__}: {exc}",
            )
            return
        outcome = _json_safe(result)
        attention = isinstance(outcome, dict) and (
            outcome.get("status") in {"needs_attention", "blocked", "partial"}
            or (type(outcome.get("exit_code")) is int and outcome["exit_code"] != 0)
        )
        self._update(
            job_id,
            status="needs_attention" if attention else "complete",
            finished_at=_timestamp(),
            last_activity_at=_timestamp(),
            result=outcome,
            error=(outcome.get("message") or "The workflow stopped with unresolved work. See its activity details.") if attention else None,
        )

    def _update(self, job_id: str, **values: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if job.status == "stopping" and values.get("status") in {"complete", "needs_attention", "failed"}:
                values.update(status="cancelled", error="Stopped at your request. Saved outputs retained.")
            for key, value in values.items():
                setattr(job, key, value)
            self._persist_locked()


def _parse_progress_message(message: str) -> tuple[int, int, str] | None:
    """Extract an honest numbered workflow stage from console progress."""

    match = re.match(r"^\[(?P<current>\d+)/(?P<total>\d+)\]\s*(?P<label>.+)$", message.strip())
    if match is None:
        return None
    current = int(match.group("current"))
    total = int(match.group("total"))
    if total < 1 or current < 0 or current > total:
        return None
    return current, total, match.group("label").strip()


def _require_supported_action(action: str, report_id: str = "") -> None:
    if action in {"scope", "scope-adjust", "research-retry", "prepare-research",
                  "report-refresh", "report-edit", "report-reconcile"}:
        raise ValueError("Experimental V2 operations are disabled in the dashboard.")
    if action.startswith("report-") and report_id.startswith("v2-"):
        raise ValueError("Existing V2 reports are read-only; create a normal report from saved research.")


def _execute_job(
    application: DefinalyzerApplication,
    *,
    action: str,
    project: str | None,
    payload: Mapping[str, Any],
    progress: Callable[[str], None],
) -> Any:
    """Bridge existing workflow functions into the background job runner."""

    # Import lazily to avoid a module cycle: app imports the dashboard only when
    # the dashboard command is selected.
    from . import app as cli

    _require_supported_action(action, str(payload.get("report_id") or ""))
    manager = application.manager
    workspace = application.load_project(project or "") if project else None
    if action == "refresh-indexes":
        return {"paths": [str(path) for path in application.refresh_indexes()]}
    if action in {"provider-test", "provider-config"}:
        code = cli._provider_command(
            manager,
            action="test" if action == "provider-test" else "configure",
            executable=(str(payload["executable"]) if payload.get("executable") else None),
            timeout=int(payload.get("timeout") or 900),
            print_fn=progress,
        )
        return {"exit_code": code}
    if workspace is None:
        raise ValueError("This action requires a project.")
    if action == "analyze":
        return {"exit_code": cli._complete_workflow(
            manager, workspace, refresh=bool(payload.get("refresh")), print_fn=progress
        )}
    if action == "crawl":
        docs_url = str(payload.get("docs_url") or workspace.document.get("docs_url") or "")
        if not docs_url:
            raise ValueError("No documentation URL is configured.")
        return {"exit_code": cli._crawl(
            manager,
            workspace,
            docs_url=docs_url,
            pattern=str(payload.get("pattern") or cli._default_crawl_pattern(docs_url)),
            refresh=bool(payload.get("refresh")),
            retries=cli.DEFAULT_RETRIES,
            ref=str(payload.get("ref") or "") or None,
            print_fn=progress,
        )}
    if action == "research":
        template = str(payload.get("template") or "protocol-overview")
        return {"exit_code": cli._extract(
            manager,
            workspace,
            template_name=template,
            mode="auto",
            refresh=bool(payload.get("refresh")),
            print_fn=progress,
        )}
    if action == "registry":
        return {"exit_code": cli._registry(manager, workspace, progress)}
    if action == "verification-plan":
        return {"exit_code": cli._verification_plan(manager, workspace, progress)}
    if action == "collect-evidence":
        ready = cli._collect_planned_verification(
            manager,
            workspace,
            job_path=workspace.jobs_directory / "verification-plan.json",
            print_fn=progress,
        )
        return {"exit_code": 0 if ready else 2}
    if action == "evaluate":
        return {"exit_code": cli._evaluate(manager, workspace, progress)}
    if action == "research-retry":
        from .research_facts import collect_facts, retry_summary, write_topic, TOPICS
        facts, usage = collect_facts(workspace, provider=application.provider(), progress=progress,
                                     retry_failed=True, expected_revision=payload.get("expected_revision"))
        for topic in TOPICS:
            write_topic(workspace, facts, topic, refresh=True)
        summary = retry_summary(workspace)
        return {"status": "needs_attention" if summary["unfinished_batches"] else "complete", "usage": usage,
                "message": "Some claims still need source support. Accepted research has been saved." if summary["unfinished_batches"] else "Unfinished research recovered.", **summary}
    if action == 'prepare-research':
        from .research_preparation import prepare_research
        return prepare_research(workspace, provider=application.provider(), selected_paths=payload.get('source_paths'), progress=progress)
    if action == "scope":
        from .research_scope import prepare_scope, scope_summary
        prepare_scope(workspace, provider=application.provider(), call_budget=int(payload.get("call_budget", 32)), extend=bool(payload.get("extend")), progress=progress)
        return scope_summary(workspace)
    if action == "scope-adjust":
        from .research_scope import override_scope, scope_summary
        override_scope(workspace, block_ids=payload.get("block_ids", []), relationship=str(payload.get("relationship", "")), reason=str(payload.get("reason", "")), applicability=payload.get("applicability"))
        return scope_summary(workspace)
    if action == "market-data":
        result = application.refresh_market_data(
            workspace=workspace, force=bool(payload.get("refresh")),
            asset_id=str(payload.get("asset_id") or "")
        )
        return result
    if action == "source":
        return {"exit_code": cli._source_command(
            manager,
            workspace,
            action=str(payload.get("source_action") or "add"),
            category=str(payload.get("category") or "") or None,
            url=str(payload.get("url") or "") or None,
            refresh=bool(payload.get("refresh")),
            print_fn=progress,
        )}
    if action == "manual-token":
        registry_path = workspace.registry_directory / "registry.json"
        before = cli.json_fingerprint(registry_path, ignored_keys=("generated_at",))
        fields = TokenRecord.__dataclass_fields__
        values = {key: str(payload.get(key) or "").strip() for key in fields}
        values["symbol"] = values["symbol"].upper()
        values["name"] = values["name"] or values["symbol"]
        for key in (
            "token_type",
            "protocol_relationship",
            "network",
            "standard",
            "address",
            "emissions",
            "allocation",
            "unlocks",
            "mint_authority",
            "utility",
        ):
            values[key] = values[key] or "Not documented"
        values["supply"] = "Not documented"
        values["maximum_supply"] = "Not documented"
        values["circulating_supply"] = "Not documented"
        token = TokenRecord(**values)
        result = upsert_manual_token(workspace=workspace, token=token)
        cli._invalidate_after_registry_change(
            manager, workspace, previous_fingerprint=before, print_fn=progress
        )
        return result
    report_id = str(payload.get("report_id") or "").strip()
    if action == "report-generate":
        return application.generate_complete_report(
            workspace=workspace, report_id=report_id, progress=progress
        )
    if action == "report-evidence":
        progress("Preparing the bounded local evidence package")
        return application.prepare_report_evidence(
            workspace=workspace, report_id=report_id
        )
    if action == "report-draft":
        progress("Generating a validated report draft from saved evidence")
        return application.generate_report(
            workspace=workspace, report_id=report_id, progress=progress
        )
    if action == "report-quality":
        progress("Checking citations, support, and conclusion strength")
        return application.review_report(
            workspace=workspace, report_id=report_id
        )
    if action == "report-revise":
        progress("Revising the selected report content and checking its implications")
        return application.revise_report(
            workspace=workspace, report_id=report_id,
            assertion_id=str(payload.get("assertion_id") or "").strip(),
            instruction=str(payload.get("instruction") or "").strip(),
            expected_revision=payload.get("expected_revision"), progress=progress,
        )
    if action in {"report-refresh", "report-edit", "report-reconcile"}:
        return application.change_report(workspace=workspace, report_id=report_id,
            operation={"report-refresh": "refresh", "report-edit": "manual", "report-reconcile": "reconcile"}[action],
            expected_revision=payload.get("expected_revision"), texts=payload.get("texts"), progress=progress)
    if action == "report-finalize":
        progress("Validating the human approval against the reviewed revision")
        return application.finalize_report(
            workspace=workspace, report_id=report_id,
            human_approved=payload.get("human_approved") is True,
            recommendation_approved=payload.get("recommendation_approved") is True,
            expected_revision=payload.get("expected_revision"),
        )
    if action == "report-export":
        progress("Creating an immutable publication bundle")
        formats = tuple(
            name for name in ("markdown", "html", "pdf")
            if payload.get(name) is True
        )
        charts = _dashboard_chart_requests(payload)
        return application.export_report(
            workspace=workspace, report_id=report_id,
            formats=formats, charts=charts, chart_ids=payload.get("chart_ids") or (),
        )
    if action == "ask":
        question = str(payload.get("question") or "").strip()
        if not question:
            raise ValueError("Question cannot be empty.")
        result = application.ask(
            workspace=workspace,
            question=question,
            deep=bool(payload.get("deep")),
            save=bool(payload.get("save", True)),
        )
        return result
    raise ValueError(f"Unsupported dashboard action: {action}")


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return {key: _json_safe(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _project_pages(workspace: ProjectWorkspace) -> list[dict[str, str]]:
    roots = (
        ("Research", workspace.vault_entity_directory),
        ("Verification", workspace.verification_directory),
        ("Q&A", workspace.vault_root / "Analyst Reviews" / workspace.name),
    )
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for group, root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md"), key=lambda item: str(item).casefold()):
            relative = path.relative_to(workspace.vault_root).as_posix()
            if relative.casefold() in seen:
                continue
            seen.add(relative.casefold())
            saved_v2 = group == "Research" and ".supported" in path.stem
            rows.append({
                "path": relative,
                "title": _markdown_title(path) + (" (saved V2)" if saved_v2 else ""),
                "group": "Saved experimental research" if saved_v2 else group,
            })
    # Reports have their own lifecycle tree. Show only the active readable
    # report, analyst companion, and quality pages; never archived revisions
    # or machine JSON.
    if workspace.reports_directory.exists():
        for directory in sorted(
            (path for path in workspace.reports_directory.iterdir() if path.is_dir()),
            key=lambda path: path.name.casefold(),
        ):
            for name in ("Report.md", "Analyst-Notes.md", "Quality.md"):
                path = directory / name
                if not path.is_file():
                    continue
                relative = path.relative_to(workspace.vault_root).as_posix()
                if relative.casefold() in seen:
                    continue
                seen.add(relative.casefold())
                rows.append({
                    "path": relative,
                    "title": _markdown_title(path),
                    "group": "Reports",
                })
    from .asset_identity import project_asset_pages
    from .report_v2 import summaries
    for report in summaries(workspace):
        for path, title in ((report.report_page, report.title), (report.analyst_notes_page, report.title + " — Analyst Notes")):
            if path:
                rows.append({"path": path, "title": title, "group": "Reports"})
    for page in project_asset_pages(workspace):
        rows.append({"path": page.relative_to(workspace.vault_root).as_posix(),
                     "title": _markdown_title(page), "group": "Related asset research"})
    return rows


def _asset_pages(
    manager: WorkspaceManager,
    *,
    section: str,
    chain_assets: bool,
) -> list[dict[str, Any]]:
    """Inventory shared asset notes and their related research projects."""

    from .asset_identity import inventory, load_catalog
    catalog = load_catalog(manager.root)
    modern = [row for row in inventory(manager.root) if row["kind"] == ("coin" if chain_assets else "token")]
    migrated_names = {row["name"] for row in catalog["projects"].values()}
    projects_by_symbol: dict[str, list[str]] = {}
    for workspace in manager.list_projects():
        if (workspace.document["entity_type"] == "chain") != chain_assets:
            continue
        registry = workspace.registry_directory / "registry.json"
        if not registry.exists():
            continue
        try:
            document = json.loads(registry.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        tokens = document.get("tokens", []) if isinstance(document, dict) else []
        for token in tokens:
            if not isinstance(token, dict):
                continue
            symbol = str(token.get("symbol") or "").strip()
            if symbol:
                projects_by_symbol.setdefault(symbol.casefold(), []).append(workspace.slug)

    token_root = manager.root / "vault" / section
    rows: list[dict[str, Any]] = list(modern)
    if not token_root.exists():
        return rows
    for directory in sorted(
        (path for path in token_root.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    ):
        page = directory / "Index.md"
        if not page.is_file():
            pages = sorted(directory.glob("*.md"), key=lambda path: path.name.casefold())
            if not pages:
                continue
            page = pages[0]
        text = page.read_text(encoding="utf-8")
        parent = re.search(r'^parent_(?:protocol|chain):\s*"([^"\n]+)"', text, re.M)
        if any(p["page"] == page.relative_to(manager.root).as_posix()
               and p["subject_id"] in catalog["entities"] for p in catalog["projects"].values()):
            continue
        if 'generated_by: "definalyzer_asset_identity"' in text or (parent and parent.group(1) in migrated_names):
            continue
        symbol = directory.name
        rows.append({
            "symbol": symbol,
            "title": _markdown_title(page),
            "path": page.relative_to(token_root.parent).as_posix(),
            "projects": sorted(set(projects_by_symbol.get(symbol.casefold(), []))),
        })
    return rows


def _token_pages(manager: WorkspaceManager) -> list[dict[str, Any]]:
    return _asset_pages(manager, section="Tokens", chain_assets=False)


def _coin_pages(manager: WorkspaceManager) -> list[dict[str, Any]]:
    return _asset_pages(manager, section="Coins", chain_assets=True)


def _markdown_title(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return re.sub(r"\[\[([^]|]+\|)?([^]]+)\]\]", r"\2", line[2:]).strip()
    except OSError:
        pass
    return path.stem


def _read_vault_page(manager: WorkspaceManager, relative: str) -> dict[str, str]:
    clean = unquote(relative).replace("\\", "/").lstrip("/")
    path = (manager.root / "vault" / clean).resolve()
    vault = (manager.root / "vault").resolve()
    try:
        path.relative_to(vault)
    except ValueError as exc:
        raise ValueError("Page must remain inside the research vault.") from exc
    if path.suffix.casefold() != ".md" or not path.is_file():
        raise FileNotFoundError("Research page was not found.")
    markdown = path.read_text(encoding="utf-8")
    relative_path = path.relative_to(vault).as_posix()
    is_report = relative_path.startswith("Reports/") and path.name == "Report.md"
    is_analyst_notes = (
        relative_path.startswith("Reports/") and path.name == "Analyst-Notes.md"
    )
    context = None
    if relative_path.startswith("Reports/") and "/V2/" in relative_path:
        from .report_v2_store import load_revision
        for workspace in manager.list_projects():
            prefix = workspace.reports_directory / "V2"
            if not path.is_relative_to(prefix.resolve()):
                continue
            parts = path.relative_to(prefix.resolve()).parts
            if len(parts) == 4 and parts[1] == "Revisions" and re.fullmatch(r"revision-\d+", parts[2]):
                revision = int(parts[2].split("-")[1])
                saved = load_revision(workspace, parts[0], revision)
                markdown = saved[path.name]
                context = {"project": workspace.slug, "report_id": parts[0], "revision": revision,
                           "source_ids": [s["source_id"] for s in saved["evidence.json"]["sources"]]}
            break
    result = {
        "path": relative_path,
        "title": _markdown_title(path),
        "markdown": markdown,
        "html": render_markdown(markdown, management_report=is_report and context is None),
        "kind": (
            "report" if is_report
            else "analyst_notes" if is_analyst_notes
            else "research"
        ),
    }
    if context:
        result["report_context"] = context
    return result


def _inline(text: str) -> str:
    # Markdown editors may serialize ordinary spaces as entities. Decode only
    # these whitespace forms; encoded HTML remains escaped below.
    text = re.sub(r"&#(?:x20|32);", " ", text, flags=re.IGNORECASE)
    # Protect escaped Markdown punctuation before interpreting link syntax.
    # Numeric entities render literal punctuation without becoming active HTML.
    escaped = []
    def literal(match):
        escaped.append("&#" + str(ord(match.group(1))) + ";")
        return f"\x00literal{len(escaped) - 1}\x00"
    text = re.sub(r"\\([\\`*_{}\[\]<>#])", literal, text)
    value = html.escape(text, quote=False)
    # Obsidian escapes the alias separator inside Markdown tables.
    value = value.replace("\\|", "|")
    value = re.sub(
        r"\[\[([^]|#]*)(#[^]|]+)?(?:\|([^]]+))?\]\]",
        lambda match: (
            '<a class="wiki-link" href="#/page/'
            + quote((match.group(1) + (match.group(2) or "")).strip(), safe="")
            + '">'
            + (
                match.group(3)
                or match.group(1)
                or (match.group(2) or "").lstrip("#^")
            ).strip()
            + "</a>"
        ),
        value,
    )
    value = re.sub(r"\[Source\]\(fact:([a-z0-9-]+):([a-f0-9]{64})\)",
                   r'<a class="fact-source" href="/api/projects/\1/facts/\2" data-project="\1" data-fact="\2">Source</a>', value)
    value = re.sub(r"\[Original notes\]\(original:([^\n)]+)\)",
                   lambda m: '<a class="original-notes" href="#/page/' + quote(html.unescape(m.group(1)), safe="") + '">Original notes</a>', value)
    value = re.sub(r"\[Compare changes\]\(comparison:([a-z0-9-]+):([a-z-]+)\)",
                   r'<a class="research-comparison" href="/api/projects/\1/research-diff/\2">Compare changes</a>', value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*", r"<em>\1</em>", value)
    value = re.sub(
        r"\[([^]]+)\]\((https?://[^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        value,
    )
    value = re.sub(
        r"\[\^([A-Za-z0-9-]+)\]",
        r'<sup class="report-citation"><a href="#source-\1">\1</a></sup>',
        value,
    )
    return re.sub(r"\x00literal(\d+)\x00", lambda m: escaped[int(m.group(1))] if int(m.group(1)) < len(escaped) else "", value)


def _table_cells(line: str) -> list[str]:
    """Split a Markdown table row without breaking Obsidian link aliases."""

    clean = line.strip().strip("|")
    cells: list[str] = []
    current: list[str] = []
    wiki_depth = 0
    index = 0
    while index < len(clean):
        pair = clean[index : index + 2]
        if pair == "[[":
            wiki_depth += 1
            current.extend(pair)
            index += 2
            continue
        if pair == "]]" and wiki_depth:
            wiki_depth -= 1
            current.extend(pair)
            index += 2
            continue
        if clean[index] == "|" and not wiki_depth:
            cells.append("".join(current).strip())
            current.clear()
        else:
            current.append(clean[index])
        index += 1
    cells.append("".join(current).strip())
    return cells


def _dashboard_message(text: str) -> str:
    """Use dashboard terminology without changing CLI output or stored notes."""
    text = re.sub(r"\bObsidian vault\b", "Research folder", text, flags=re.IGNORECASE)
    return re.sub(r"\bObsidian\b", "research", text, flags=re.IGNORECASE)


def render_markdown(markdown: str, *, management_report: bool = False) -> str:
    """Render the generated Markdown subset without allowing embedded HTML."""

    if management_report:
        markdown = management_report_markdown(markdown)
    lines = markdown.splitlines()
    # Keep generated metadata in the canonical Markdown while omitting it from
    # the human-facing dashboard reader.
    if lines and lines[0].strip() == "---":
        closing = next(
            (
                index
                for index, line in enumerate(lines[1:], start=1)
                if line.strip() == "---"
            ),
            None,
        )
        if closing is not None:
            lines = lines[closing + 1 :]
    # Machine instructions stay in the canonical file for the collector but
    # are not research content. Hide their section and any standalone
    # DEFINALYZER data fences from the dashboard reader.
    human_lines: list[str] = []
    index = 0
    while index < len(lines):
        heading = re.match(
            r"^(#{1,6})\s+(?:Collector Requests|Research Link Map)\s*$",
            lines[index], re.IGNORECASE,
        )
        if heading:
            level = len(heading.group(1))
            index += 1
            while index < len(lines):
                next_heading = re.match(r"^(#{1,6})\s+", lines[index])
                if next_heading and len(next_heading.group(1)) <= level:
                    break
                index += 1
            continue
        if re.match(r"^```definalyzer(?:-[A-Za-z0-9_-]+)?\s*$", lines[index], re.IGNORECASE):
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                index += 1
            if index < len(lines):
                index += 1
            continue
        human_lines.append(lines[index])
        index += 1
    lines = human_lines
    output: list[str] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    list_type: str | None = None

    def flush_paragraph() -> None:
        if paragraph:
            output.append("<p>" + " ".join(_inline(row.strip()) for row in paragraph) + "</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            flush_paragraph(); close_list()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear(); in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line); index += 1; continue
        if line.startswith("<!--"):
            flush_paragraph(); close_list()
            while index < len(lines) and "-->" not in lines[index]:
                index += 1
            index += 1
            continue
        block_anchor = re.fullmatch(r"\^([A-Za-z0-9_-]+)\s*", line)
        if block_anchor:
            flush_paragraph(); close_list()
            output.append(
                f'<span class="block-anchor" id="{html.escape(block_anchor.group(1))}"></span>'
            )
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph(); close_list()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            anchor = re.sub(r"[^a-z0-9]+", "-", re.sub(r"\[\[.*?\|?(.*?)\]\]", r"\1", title).casefold()).strip("-")
            output.append(f'<h{level} id="{html.escape(anchor)}">{_inline(title)}</h{level}>')
            index += 1; continue
        if line.startswith("|") and index + 1 < len(lines) and re.match(r"^\|?[\s:|-]+\|?$", lines[index + 1]):
            flush_paragraph(); close_list()
            header_cells = _table_cells(line)
            output.append('<div class="table-wrap" tabindex="0" role="region" aria-label="Table: scroll sideways to read all columns"><table><thead><tr>' + "".join(f"<th>{_inline(cell)}</th>" for cell in header_cells) + "</tr></thead><tbody>")
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                cells = _table_cells(lines[index])
                output.append("<tr>" + "".join(f"<td>{_inline(cell)}</td>" for cell in cells) + "</tr>")
                index += 1
            output.append("</tbody></table></div>")
            continue
        footnote = re.match(r"^\[\^([A-Za-z0-9-]+)\]:\s*(.*)$", line)
        if footnote:
            flush_paragraph(); close_list()
            output.append(
                f'<div class="report-source" id="source-{html.escape(footnote.group(1))}">'
                f'<span>{html.escape(footnote.group(1))}</span>'
                f'<p>{_inline(footnote.group(2))}</p></div>'
            )
            index += 1; continue
        nested_item = re.match(r"^\s{2,}[-*+]\s+(.*)$", line)
        if management_report and nested_item:
            flush_paragraph(); close_list()
            output.append(
                '<p class="report-detail">'
                + _inline(nested_item.group(1)) + "</p>"
            )
            index += 1; continue
        item = re.match(r"^\s*([-*+] |\d+\. )(.*)$", line)
        if item:
            flush_paragraph()
            desired = "ol" if item.group(1)[0].isdigit() else "ul"
            if list_type != desired:
                close_list(); output.append(f"<{desired}>"); list_type = desired
            output.append("<li>" + _inline(item.group(2)) + "</li>")
            index += 1; continue
        if line.startswith(">"):
            flush_paragraph(); close_list()
            output.append("<blockquote>" + _inline(line.lstrip("> ")) + "</blockquote>")
            index += 1; continue
        if not line.strip() or re.match(r"^\s*---+\s*$", line):
            flush_paragraph(); close_list()
            if line.strip(): output.append("<hr>")
            index += 1; continue
        paragraph.append(line)
        index += 1
    flush_paragraph(); close_list()
    if in_code:
        output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(output)


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], manager: WorkspaceManager) -> None:
        from .dashboard_instance import DashboardLease
        self._lease = DashboardLease(manager.root)
        try:
            self.application = DefinalyzerApplication(manager)
            self.application.initialize()
            self.jobs = DashboardJobManager(self.application)
            self.token = secrets.token_urlsafe(24)
            super().__init__(address, DashboardRequestHandler)
        except BaseException:
            if hasattr(self, 'jobs'):
                self.jobs.close()
            self._lease.close()
            raise

    def server_close(self) -> None:
        try:
            self.jobs.close()
            super().server_close()
        finally:
            self._lease.close()


class DashboardRequestHandler(BaseHTTPRequestHandler):
    server: DashboardServer

    def log_message(self, format: str, *args: Any) -> None:
        print("Dashboard:", format % args)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            self._get()
        except Exception as exc:
            self._error(exc)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            self._require_local_request()
            self._post()
        except Exception as exc:
            self._error(exc)

    def _get(self) -> None:
        self._require_loopback_host()
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self._json({"status": "ok", "schema_version": DASHBOARD_SCHEMA_VERSION})
            return
        if path == "/api/bootstrap":
            self._json({
                "schema_version": DASHBOARD_SCHEMA_VERSION,
                "token": self.server.token,
                "projects": [row.to_dict() for row in self.server.application.list_projects()],
                "tokens": _token_pages(self.server.application.manager),
                "coins": _coin_pages(self.server.application.manager),
                "jobs": self.server.jobs.list(),
            })
            return
        if path == "/api/jobs":
            self._json({"jobs": self.server.jobs.list()}); return
        match = re.fullmatch(r'/api/projects/([a-z0-9-]+)/preparation', path)
        if match:
            from .research_preparation import preparation_sources
            workspace = self.server.application.load_project(match[1])
            self._json(preparation_sources(workspace)); return
        if path == "/api/provider":
            self._json({"provider": self.server.application.provider().diagnostic()}); return
        if path == "/api/dashboard-guide":
            markdown = DASHBOARD_GUIDE.read_text(encoding="utf-8")
            self._json({"markdown": markdown, "html": render_markdown(markdown)}); return
        match = re.fullmatch(r"/api/jobs/([a-f0-9]+)", path)
        if match:
            self._json(self.server.jobs.get(match.group(1))); return
        match = re.fullmatch(r"/api/projects/([^/]+)", path)
        if match:
            workspace = self.server.application.load_project(unquote(match.group(1)))
            self._json({"scope": None, "project": self.server.application.snapshot(workspace).to_dict(), "pages": _project_pages(workspace), "proposals": _proposal_rows(workspace), "sources": _json_safe(load_source_coverage(workspace)), "reports": [row.to_dict() for row in self.server.application.reports(workspace)]})
            return
        match = re.fullmatch(r"/api/projects/([a-z0-9-]+)/facts/([a-f0-9]{64})", path)
        if match:
            from .research_facts import fact_detail
            workspace = self.server.application.load_project(match.group(1))
            self._json(fact_detail(workspace, match.group(2))); return
        match = re.fullmatch(r"/api/projects/([a-z0-9-]+)/research-diff/([a-z-]+)", path)
        if match:
            from .research_facts import page_comparison
            workspace = self.server.application.load_project(match.group(1))
            self._json(page_comparison(workspace, match.group(2))); return
        match = re.fullmatch(r"/api/projects/([^/]+)/reports/([^/]+)", path)
        if match:
            workspace = self.server.application.load_project(unquote(match.group(1)))
            self._json(self.server.application.report_detail(
                workspace=workspace, report_id=unquote(match.group(2))
            )); return
        match = re.fullmatch(r"/api/projects/([a-z0-9-]+)/reports/(v2-[a-z0-9-]+)/sources/(\d+)/(S\d+)", path)
        if match:
            from .report_v2 import source
            workspace = self.server.application.load_project(match.group(1))
            self._json(source(workspace, match.group(2), int(match.group(3)), match.group(4))); return
        match = re.fullmatch(
            r"/api/projects/([^/]+)/reports/([^/]+)/exports/(revision-[0-9]{4})/(Report\.(?:md|html|pdf)|Analyst-Notes\.md|Assets/chart-[0-9]{3}\.(?:svg|json))",
            path,
        )
        if match:
            workspace = self.server.application.load_project(unquote(match.group(1)))
            self._report_export(
                workspace, unquote(match.group(2)), match.group(3), match.group(4)
            ); return
        match = re.fullmatch(r"/api/projects/([^/]+)/reports/([^/]+)/download.pdf", path)
        if match:
            workspace = self.server.application.load_project(unquote(match.group(1)))
            self._require_idle(workspace)
            data = download_report_pdf(workspace=workspace, report_id=unquote(match.group(2)))
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", 'attachment; filename="Report.pdf"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers(); self.wfile.write(data)
            return
        if path == "/api/page":
            values = parse_qs(parsed.query)
            self._json(_read_vault_page(self.server.application.manager, values.get("path", [""])[0])); return
        if path.startswith("/assets/"):
            self._asset(path.removeprefix("/assets/")); return
        if path in {"/", "/index.html"}:
            self._asset("index.html"); return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _post(self) -> None:
        payload = self._payload()
        path = urlparse(self.path).path
        if path == "/api/jobs/clear":
            self._json(self.server.jobs.clear_finished()); return
        match = re.fullmatch(r"/api/projects/([^/]+)/reports/([^/]+)/delete", path)
        if match:
            workspace = self.server.application.load_project(unquote(match.group(1)))
            self._require_idle(workspace)
            self._json(self.server.application.delete_report(
                workspace=workspace, report_id=unquote(match.group(2)))); return
        if path == "/api/projects":
            workspace = self.server.application.create_project(
                name=str(payload.get("name") or ""),
                entity_type=str(payload.get("entity_type") or "protocol"),
                docs_url=str(payload.get("docs_url") or "") or None,
                verification_status="pending" if payload.get("verification") else "not_requested",
            )
            self._json({"project": self.server.application.snapshot(workspace).to_dict()}, status=HTTPStatus.CREATED); return
        match = re.fullmatch(r"/api/assets/([a-f0-9]{32})/research", path)
        if match:
            workspace = self.server.application.start_asset_research(match.group(1))
            self._json({"project": self.server.application.snapshot(workspace).to_dict()}, status=HTTPStatus.CREATED); return
        match = re.fullmatch(r"/api/projects/([^/]+)/reports", path)
        if match:
            workspace = self.server.application.load_project(unquote(match.group(1)))
            self._require_idle(workspace)
            if payload.get("schema_version", 1) != 1:
                raise ValueError("New dashboard reports use the supported report engine; V2 creation is disabled.")
            summary = self.server.application.create_report(
                workspace=workspace,
                title=str(payload.get("title") or ""),
                mode=str(payload.get("mode") or "question"),
                question=str(payload.get("question") or "").strip() or None,
                schema_version=payload.get("schema_version", 1), recommendations=payload.get("recommendations") is True,
                audience=str(payload.get("audience") or "researcher"), depth=str(payload.get("depth") or "standard"),
            )
            self._json({"report": summary.to_dict()}, status=HTTPStatus.CREATED); return
        match = re.fullmatch(r"/api/projects/([^/]+)/jobs", path)
        if match:
            project = unquote(match.group(1))
            workspace = self.server.application.load_project(project)
            action = str(payload.get("action") or "")
            _require_supported_action(action, str(payload.get("report_id") or ""))
            action_key = ACTION_AVAILABILITY_KEYS.get(action)
            if action in REPORT_JOB_ACTIONS:
                self._require_idle(workspace)
                report_id = str(payload.get("report_id") or "").strip()
                report = next(
                    (
                        row for row in self.server.application.reports(workspace)
                        if row.report_id == report_id
                    ),
                    None,
                )
                if report is None:
                    raise FileNotFoundError("Report was not found.")
                report_action = REPORT_ACTION_AVAILABILITY_KEYS[action]
                availability = report.actions[report_action]
                if not availability.available:
                    raise ValueError(
                        availability.reason or "This report action is not ready."
                    )
            if action not in {"provider-test", "provider-config", "refresh-indexes"} | REPORT_JOB_ACTIONS:
                availability = (
                    self.server.application.snapshot(workspace).actions.get(action_key)
                    if action_key
                    else None
                )
                if availability is None:
                    raise ValueError(f"Unsupported project action: {action}")
                if not availability.available:
                    raise ValueError(availability.reason or "This action is not ready.")
            job = self.server.jobs.submit(action=action, project=project, payload=payload)
            self._json({"job": job}, status=HTTPStatus.ACCEPTED); return
        match = re.fullmatch(r"/api/jobs/([a-f0-9]+)/cancel", path)
        if match:
            self._json({"job": self.server.jobs.cancel(match.group(1))}, status=HTTPStatus.ACCEPTED); return
        if path == "/api/jobs":
            _require_supported_action(str(payload.get("action") or ""), str(payload.get("report_id") or ""))
            job = self.server.jobs.submit(action=str(payload.get("action") or ""), project=None, payload=payload)
            self._json({"job": job}, status=HTTPStatus.ACCEPTED); return
        match = re.fullmatch(r"/api/projects/([^/]+)/review", path)
        if match:
            workspace = self.server.application.load_project(unquote(match.group(1)))
            self._require_idle(workspace)
            proposal_id = str(payload.get("proposal_id") or "")
            proposal = next((row for row in pending_proposals(workspace) if row.stem == proposal_id), None)
            if proposal is None: raise ValueError("Pending proposal was not found.")
            result = review_proposal(workspace=workspace, proposal_path=proposal, action=str(payload.get("action") or "leave"))
            remaining = pending_proposals(workspace)
            self.server.application.manager.update_stage(
                workspace,
                "evidence_evaluation",
                "complete" if not remaining else "pending",
                detail=f"{len(remaining)} pending human-review proposals",
            )
            self._json({"review": _json_safe(result)}); return
        match = re.fullmatch(r"/api/projects/([^/]+)/delete", path)
        if match:
            workspace = self.server.application.load_project(unquote(match.group(1)))
            self._require_idle(workspace)
            if str(payload.get("confirmation") or "") != workspace.name:
                raise ValueError("Type the exact project name to confirm deletion.")
            removed = self.server.application.delete_project(workspace.slug)
            self._json({"removed": [str(row) for row in removed]}); return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _require_idle(self, workspace: ProjectWorkspace) -> None:
        if self.server.jobs.has_active(workspace.slug):
            raise ValueError(
                "Wait for the active project job to finish before changing it."
            )

    def _require_local_request(self) -> None:
        self._require_loopback_host()
        supplied = self.headers.get("X-DEFINALYZER-Token", "")
        if not secrets.compare_digest(supplied, self.server.token):
            raise PermissionError("Invalid local dashboard session token.")
        origin = self.headers.get("Origin")
        if origin:
            parsed = urlparse(origin)
            host = urlparse("//" + self.headers.get("Host", ""))
            if (
                parsed.scheme != "http"
                or parsed.hostname != host.hostname
                or (parsed.port or 80) != self.server.server_port
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise PermissionError("Dashboard mutations require the same dashboard origin.")

    def _require_loopback_host(self) -> None:
        host = self.headers.get("Host", "")
        parsed = urlparse("//" + host)
        if (
            parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or (parsed.port or 80) != self.server.server_port
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise PermissionError("Dashboard requests accept loopback hosts only.")

    def _payload(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid request length.") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("Dashboard request is too large.")
        value = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(value, dict):
            raise ValueError("Dashboard request must be a JSON object.")
        return value

    def _asset(self, name: str) -> None:
        if name not in {"index.html", "app.css", "app.js", "reports-v2.js", "definalyzer-logo.png"}:
            self.send_error(HTTPStatus.NOT_FOUND); return
        path = ASSET_ROOT / name
        data = path.read_bytes()
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".png": "image/png",
        }[path.suffix]
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers(); self.wfile.write(data)

    def _report_export(
        self, workspace: ProjectWorkspace, report_id: str,
        revision: str, relative: str,
    ) -> None:
        from .report_v2_store import exists, package as v2_package, approval as v2_approval, local
        if exists(workspace, report_id):
            v2_approval(workspace, report_id, int(revision.split("-")[1]))
            directory = local(workspace, v2_package(workspace, report_id) / "Exports" / revision)
        else:
            package = report_package(workspace, report_id)
            directory = package.exports_directory / revision
        manifest_path = directory / "export.json"
        if not manifest_path.is_file():
            raise FileNotFoundError("Report export was not found.")
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        if exists(workspace, report_id):
            from .report_v2_export import export_manifest
            document = export_manifest(workspace, report_id, int(revision.split("-")[1]))
        files = document.get("files") if isinstance(document, dict) else None
        if not isinstance(files, dict) or relative not in files:
            raise FileNotFoundError("Exported report file was not found.")
        path = (directory / Path(relative)).resolve()
        try:
            path.relative_to(directory.resolve())
        except ValueError as exc:
            raise ValueError("Report export path is invalid.") from exc
        if not path.is_file() or content_sha256(path.read_bytes()) != files[relative]:
            raise ValueError("Exported report file failed its integrity check.")
        data = path.read_bytes()
        content_type = {
            ".md": "text/markdown; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".pdf": "application/pdf",
            ".svg": "image/svg+xml; charset=utf-8",
            ".json": "application/json; charset=utf-8",
        }[path.suffix.casefold()]
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; img-src 'self'; "
            "script-src 'none'; frame-ancestors 'none'",
        )
        self.end_headers(); self.wfile.write(data)

    def _json(self, document: Any, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(_json_safe(document), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers(); self.wfile.write(data)

    def _error(self, exc: Exception) -> None:
        status = HTTPStatus.NOT_FOUND if isinstance(exc, (FileNotFoundError, KeyError)) else HTTPStatus.FORBIDDEN if isinstance(exc, PermissionError) else HTTPStatus.BAD_REQUEST
        self._json({"error": str(exc), "type": type(exc).__name__}, status=status)


def _proposal_rows(workspace: ProjectWorkspace) -> list[dict[str, Any]]:
    rows = []
    for path in pending_proposals(workspace):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append({**document, "proposal_id": path.stem})
    return rows


def _dashboard_chart_requests(
    payload: Mapping[str, Any],
) -> tuple[ChartRequest, ...]:
    title = str(payload.get("chart_title") or "").strip()
    evidence_id = str(payload.get("chart_evidence_id") or "").strip()
    unit = str(payload.get("chart_unit") or "").strip()
    raw_fields = str(payload.get("chart_fields") or "").strip()
    limitation = str(payload.get("chart_limitations") or "").strip()
    supplied = any((title, evidence_id, unit, raw_fields, limitation))
    if not supplied:
        return ()
    if not all((title, evidence_id, unit, raw_fields)):
        raise ValueError(
            "Optional chart export requires a title, evidence ID, unit, and fields."
        )
    fields: dict[str, str] = {}
    for line in raw_fields.splitlines():
        if not line.strip():
            continue
        if "=" not in line:
            raise ValueError("Chart fields must use one Label=path entry per line.")
        label, path = (item.strip() for item in line.split("=", 1))
        if not label or not path or label in fields:
            raise ValueError("Chart field labels and paths must be non-empty and unique.")
        fields[label] = path
    return (ChartRequest.from_fields(
        title=title, evidence_id=evidence_id, fields=fields, unit=unit,
        limitations=limitation or None,
    ),)


def create_dashboard_server(
    manager: WorkspaceManager, *, host: str = "127.0.0.1", port: int = DEFAULT_PORT
) -> DashboardServer:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("The dashboard may only bind to this computer.")
    return DashboardServer((host, port), manager)


def run_dashboard(
    manager: WorkspaceManager,
    *,
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
    print_fn: Callable[[str], None] = print,
) -> int:
    server = create_dashboard_server(manager, port=port)
    url = f"http://127.0.0.1:{server.server_port}/"
    print_fn(f"DEFINALYZER dashboard: {url}")
    print_fn("The dashboard is local to this computer. Press Ctrl+C to stop it.")
    if open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print_fn("Dashboard stopped.")
    except Exception:
        crash_path = manager.root / "dashboard-crash.log"
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        crash_path.write_text(
            f"{_timestamp()}\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        print_fn(f"Dashboard crashed. Diagnostic: {crash_path}")
        raise
    finally:
        server.server_close()
    return 0
