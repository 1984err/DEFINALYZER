"""Track whether generated research still matches its deterministic inputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .extraction import OUTPUT_FILES, TEMPLATE_FILES, source_selection
from .workspace import ProjectWorkspace


DEPENDENCY_SCHEMA_VERSION = 1
STATE_NAME = "dependency-state.json"


def source_corpus_fingerprint(workspace: ProjectWorkspace) -> str:
    """Hash collected Markdown and source-coverage metadata."""

    selection = source_selection(workspace.sources_directory)
    # Only documents that are actually sent to the research provider belong
    # in this fingerprint. Changes to excluded API/reference material should
    # not spend AI usage rebuilding otherwise identical research pages.
    files = tuple(sorted(selection.selected))
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(workspace.sources_directory).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    coverage = workspace.project_root / "source-coverage.json"
    if coverage.exists():
        digest.update(b"source-coverage.json\0")
        document = json.loads(coverage.read_text(encoding="utf-8"))
        rows = document.get("sources", []) if isinstance(document, dict) else []
        semantic_rows = [
            {
                "source_id": row.get("source_id"),
                "category": row.get("category"),
                "url": row.get("url"),
                "status": row.get("status"),
            }
            for row in rows
            if isinstance(row, dict)
        ]
        semantic_rows.sort(
            key=lambda row: tuple(
                str(row.get(field) or "")
                for field in ("source_id", "category", "url", "status")
            )
        )
        digest.update(
            json.dumps(
                semantic_rows,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    return digest.hexdigest()


def research_page_input_fingerprint(
    workspace: ProjectWorkspace,
    prompts_root: str | Path,
    template_name: str,
) -> str:
    """Hash the exact inputs used to generate one research page."""

    if template_name not in TEMPLATE_FILES:
        raise ValueError(f"Unknown research template: {template_name}")

    digest = hashlib.sha256()
    digest.update(source_corpus_fingerprint(workspace).encode("ascii"))
    prompts = Path(prompts_root)
    paths = [
        prompts / "master_prompt.md",
        prompts / "templates" / TEMPLATE_FILES[template_name],
    ]
    for path in paths:
        digest.update(path.relative_to(prompts).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def record_research_page(
    workspace: ProjectWorkspace,
    *,
    template_name: str,
    prompts_root: str | Path,
) -> None:
    state = _load(workspace)
    fingerprint = research_page_input_fingerprint(
        workspace,
        prompts_root,
        template_name,
    )
    pages = dict(state.get("research_pages", {}))
    pages[template_name] = fingerprint
    state["research_pages"] = pages
    state["source_corpus_fingerprint"] = source_corpus_fingerprint(workspace)
    _write(workspace, state)


def research_pages_current(
    workspace: ProjectWorkspace,
    *,
    prompts_root: str | Path,
) -> bool:
    return not stale_research_pages(
        workspace,
        prompts_root=prompts_root,
    )


def stale_research_pages(
    workspace: ProjectWorkspace,
    *,
    prompts_root: str | Path,
) -> tuple[str, ...]:
    """Return templates whose output is absent or no longer current."""

    state = _load(workspace)
    pages = state.get("research_pages", {})
    if not isinstance(pages, dict):
        pages = {}
    return tuple(
        template
        for template, filename in OUTPUT_FILES.items()
        if not (workspace.vault_entity_directory / filename).exists()
        or pages.get(template)
        != research_page_input_fingerprint(
            workspace,
            prompts_root,
            template,
        )
    )


def bootstrap_legacy_research(
    workspace: ProjectWorkspace,
    *,
    prompts_root: str | Path,
) -> bool:
    """Adopt a complete pre-tracking project once without rewriting it."""

    state = _load(workspace)
    if state.get("research_pages"):
        return False
    if not all(
        (workspace.vault_entity_directory / filename).exists()
        for filename in OUTPUT_FILES.values()
    ):
        return False
    state["research_pages"] = {
        template: research_page_input_fingerprint(
            workspace,
            prompts_root,
            template,
        )
        for template in OUTPUT_FILES
    }
    state["source_corpus_fingerprint"] = source_corpus_fingerprint(workspace)
    _write(workspace, state)
    return True


def json_fingerprint(
    path: str | Path,
    *,
    ignored_keys: tuple[str, ...] = (),
) -> str | None:
    """Hash JSON semantics while excluding non-semantic metadata fields."""

    candidate = Path(path)
    if not candidate.exists():
        return None
    document = json.loads(candidate.read_text(encoding="utf-8"))

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: clean(item)
                for key, item in value.items()
                if key not in ignored_keys
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    encoded = json.dumps(
        clean(document),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load(workspace: ProjectWorkspace) -> dict[str, Any]:
    path = workspace.project_root / STATE_NAME
    if not path.exists():
        return {
            "schema_version": DEPENDENCY_SCHEMA_VERSION,
            "research_pages": {},
        }
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"Dependency state must be a JSON object: {path}")
    if document.get("schema_version") != DEPENDENCY_SCHEMA_VERSION:
        raise ValueError(f"Unsupported dependency state schema: {path}")
    return document


def _write(workspace: ProjectWorkspace, document: dict[str, Any]) -> None:
    path = workspace.project_root / STATE_NAME
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)
