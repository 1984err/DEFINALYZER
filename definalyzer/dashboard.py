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
from .source_coverage import load_source_coverage
from .workspace import ProjectWorkspace, WorkspaceManager


DASHBOARD_SCHEMA_VERSION = 1
DEFAULT_PORT = 0
ASSET_ROOT = Path(__file__).with_name("dashboard_assets")
DASHBOARD_GUIDE = Path(__file__).resolve().parent.parent / "docs" / "DASHBOARD_README.md"
MAX_REQUEST_BYTES = 128_000
JOB_ACTIONS = {
    "analyze",
    "crawl",
    "research",
    "registry",
    "verification-plan",
    "collect-evidence",
    "evaluate",
    "market-data",
    "ask",
    "dune",
    "refresh-indexes",
    "provider-test",
    "provider-config",
    "source",
    "manual-token",
}
ACTION_AVAILABILITY_KEYS = {
    "analyze": "analyze",
    "crawl": "crawl",
    "research": "research",
    "registry": "registry",
    "verification-plan": "verification_plan",
    "collect-evidence": "collect_evidence",
    "evaluate": "evaluate_evidence",
    "market-data": "market_data",
    "ask": "ask",
    "dune": "dune",
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
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="definalyzer-dashboard"
        )
        self._jobs: dict[str, DashboardJob] = {}
        self._lock = threading.Lock()

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

    def has_active(self, project: str) -> bool:
        with self._lock:
            return any(
                row.project == project and row.status in {"queued", "running"}
                for row in self._jobs.values()
            )

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

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
        self._executor.submit(self._run, job.job_id, dict(payload))
        return job.to_dict()

    def _run(self, job_id: str, payload: dict[str, Any]) -> None:
        started_at = _timestamp()
        self._update(
            job_id,
            status="running",
            started_at=started_at,
            last_activity_at=started_at,
        )

        def progress(message: str) -> None:
            with self._lock:
                job = self._jobs[job_id]
                text = str(message)
                job.messages.append(text)
                del job.messages[:-250]
                job.last_activity_at = _timestamp()
                parsed = _parse_progress_message(text)
                if parsed is not None:
                    job.progress_current, job.progress_total, job.progress_label = parsed

        try:
            result = _execute_job(
                self.application,
                action=self._jobs[job_id].action,
                project=self._jobs[job_id].project,
                payload=payload,
                progress=progress,
            )
        except Exception as exc:  # reported to the local user, never swallowed
            self._update(
                job_id,
                status="failed",
                finished_at=_timestamp(),
                error=f"{type(exc).__name__}: {exc}",
            )
            progress(traceback.format_exc(limit=5))
            return
        self._update(
            job_id,
            status="complete",
            finished_at=_timestamp(),
            last_activity_at=_timestamp(),
            result=_json_safe(result),
        )

    def _update(self, job_id: str, **values: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in values.items():
                setattr(job, key, value)


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
    if action == "market-data":
        result = application.refresh_market_data(
            workspace=workspace, force=bool(payload.get("refresh"))
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
    if action == "dune":
        verification_id = str(payload.get("verification_id") or "").strip()
        if not verification_id:
            raise ValueError("A verification ID is required.")
        return application.dune_dialogue(
            workspace=workspace,
            verification_id=verification_id,
            feedback_type=(str(payload["feedback_type"]) if payload.get("feedback_type") else None),
            feedback=(str(payload["feedback"]) if payload.get("feedback") else None),
        )
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
            rows.append({
                "path": relative,
                "title": _markdown_title(path),
                "group": group,
            })
    # Project-native asset pages live in a shared vault section. Include only
    # assets listed by this project's registry.
    registry = workspace.registry_directory / "registry.json"
    if registry.exists():
        try:
            document = json.loads(registry.read_text(encoding="utf-8"))
            symbols = [str(row.get("symbol", "")).strip() for row in document.get("tokens", []) if isinstance(row, dict)]
        except (OSError, json.JSONDecodeError):
            symbols = []
        asset_group = "Coins" if workspace.document["entity_type"] == "chain" else "Tokens"
        for symbol in symbols:
            root = workspace.vault_root / asset_group / symbol
            for path in sorted(root.glob("*.md")) if root.exists() else ():
                relative = path.relative_to(workspace.vault_root).as_posix()
                if relative.casefold() not in seen:
                    seen.add(relative.casefold())
                    rows.append({"path": relative, "title": _markdown_title(path), "group": asset_group})
    return rows


def _asset_pages(
    manager: WorkspaceManager,
    *,
    section: str,
    chain_assets: bool,
) -> list[dict[str, Any]]:
    """Inventory shared asset notes and their related research projects."""

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
    rows: list[dict[str, Any]] = []
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
    return {
        "path": path.relative_to(vault).as_posix(),
        "title": _markdown_title(path),
        "markdown": markdown,
        "html": render_markdown(markdown),
    }


def _inline(text: str) -> str:
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
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*", r"<em>\1</em>", value)
    value = re.sub(
        r"\[([^]]+)\]\((https?://[^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        value,
    )
    return value


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


def render_markdown(markdown: str) -> str:
    """Render the generated Markdown subset without allowing embedded HTML."""

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
        heading = re.match(r"^(#{1,6})\s+Collector Requests\s*$", lines[index], re.IGNORECASE)
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
        self.application = DefinalyzerApplication(manager)
        self.application.initialize()
        self.jobs = DashboardJobManager(self.application)
        self.token = secrets.token_urlsafe(24)
        super().__init__(address, DashboardRequestHandler)

    def server_close(self) -> None:
        self.jobs.close()
        super().server_close()


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
            self._json({"project": self.server.application.snapshot(workspace).to_dict(), "pages": _project_pages(workspace), "proposals": _proposal_rows(workspace), "sources": _json_safe(load_source_coverage(workspace))})
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
        if path == "/api/projects":
            workspace = self.server.application.create_project(
                name=str(payload.get("name") or ""),
                entity_type=str(payload.get("entity_type") or "protocol"),
                docs_url=str(payload.get("docs_url") or "") or None,
                verification_status="pending" if payload.get("verification") else "not_requested",
            )
            self._json({"project": self.server.application.snapshot(workspace).to_dict()}, status=HTTPStatus.CREATED); return
        match = re.fullmatch(r"/api/projects/([^/]+)/jobs", path)
        if match:
            project = unquote(match.group(1))
            workspace = self.server.application.load_project(project)
            action = str(payload.get("action") or "")
            action_key = ACTION_AVAILABILITY_KEYS.get(action)
            if action not in {"provider-test", "provider-config", "refresh-indexes"}:
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
        if path == "/api/jobs":
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
        if name not in {"index.html", "app.css", "app.js", "definalyzer-logo.png"}:
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
    finally:
        server.server_close()
    return 0
