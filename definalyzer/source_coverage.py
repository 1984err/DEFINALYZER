"""Categorized official-source coverage for research completeness."""

from __future__ import annotations

import json
import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .workspace import ProjectWorkspace, slugify


CATEGORIES = (
    "technical",
    "tokenomics",
    "fees_revenue",
    "governance_security",
)
CATEGORY_LABELS = {
    "technical": "Technical documentation",
    "tokenomics": "Token and tokenomics",
    "fees_revenue": "Fees, revenue, and value accrual",
    "governance_security": "Governance and security",
}
CRITICAL_CATEGORIES = {"technical", "tokenomics", "fees_revenue"}
SOURCE_STATUSES = {"registered", "collected", "failed"}


@dataclass(frozen=True)
class OfficialSource:
    source_id: str
    category: str
    url: str
    status: str
    collected_at: str | None
    detail: str | None


@dataclass(frozen=True)
class CoverageSummary:
    status: str
    categories: dict[str, str]
    sources: tuple[OfficialSource, ...]


def coverage_path(workspace: ProjectWorkspace) -> Path:
    return workspace.project_root / "source-coverage.json"


def ensure_source_coverage(workspace: ProjectWorkspace) -> CoverageSummary:
    path = coverage_path(workspace)
    if not path.exists():
        sources: list[OfficialSource] = []
        primary = workspace.document.get("docs_url")
        if isinstance(primary, str) and primary.strip():
            sources.append(
                OfficialSource(
                    source_id=_source_id("technical", primary),
                    category="technical",
                    url=primary.strip(),
                    status=(
                        "collected"
                        if any(workspace.sources_directory.rglob("*.md"))
                        else "registered"
                    ),
                    collected_at=None,
                    detail="Primary documentation source",
                )
            )
        _write_sources(workspace, sources)
    _sync_primary_corpus_categories(workspace)
    return load_source_coverage(workspace)


def _sync_primary_corpus_categories(workspace: ProjectWorkspace) -> None:
    """Credit clearly categorized pages found under one official docs root."""
    path = coverage_path(workspace)
    if not path.exists():
        return
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("sources") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        return
    sources = [OfficialSource(**row) for row in rows if isinstance(row, dict)]
    primary = workspace.document.get("docs_url")
    if not isinstance(primary, str) or not primary.strip():
        return
    relative_names = [
        file.relative_to(workspace.sources_directory).as_posix().casefold()
        for file in workspace.sources_directory.rglob("*.md")
        if file.name.casefold() != "_source_coverage.md"
    ]
    keywords = {
        "tokenomics": ("token", "tokenomics", "vesting", "emission"),
        "fees_revenue": ("fee", "revenue", "value-accrual"),
        "governance_security": (
            "governance",
            "security",
            "audit",
            "risk",
        ),
    }
    existing = {(source.category, source.url.casefold()) for source in sources}
    changed = False
    for category, terms in keywords.items():
        key = (category, primary.strip().casefold())
        if key in existing or not any(
            any(term in name for term in terms) for name in relative_names
        ):
            continue
        sources.append(
            OfficialSource(
                source_id=_source_id(category, primary.strip()),
                category=category,
                url=primary.strip(),
                status="collected",
                collected_at=datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                detail="Categorized page found under primary documentation root",
            )
        )
        changed = True
    if changed:
        _write_sources(workspace, sources)


def load_source_coverage(workspace: ProjectWorkspace) -> CoverageSummary:
    path = coverage_path(workspace)
    if not path.exists():
        return CoverageSummary(
            status="missing",
            categories={category: "missing" for category in CATEGORIES},
            sources=(),
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("sources") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise ValueError("Source coverage file has invalid sources.")
    sources = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Source coverage contains an invalid source row.")
        source = OfficialSource(**row)
        _validate_source(source)
        sources.append(source)
    categories = {
        category: (
            "collected"
            if any(
                source.category == category and source.status == "collected"
                for source in sources
            )
            else "registered"
            if any(source.category == category for source in sources)
            else "missing"
        )
        for category in CATEGORIES
    }
    if all(categories[item] == "collected" for item in CRITICAL_CATEGORIES):
        status = (
            "complete"
            if all(value == "collected" for value in categories.values())
            else "partial"
        )
    elif any(value == "collected" for value in categories.values()):
        status = "partial"
    else:
        status = "missing"
    return CoverageSummary(
        status=status,
        categories=categories,
        sources=tuple(sources),
    )


def add_official_source(
    workspace: ProjectWorkspace,
    *,
    category: str,
    url: str,
) -> OfficialSource:
    ensure_source_coverage(workspace)
    clean_category = category.strip().casefold().replace("-", "_")
    clean_url = url.strip()
    if clean_category not in CATEGORIES:
        raise ValueError(
            "Source category must be one of: " + ", ".join(CATEGORIES)
        )
    parsed = urlparse(clean_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Official source must be an HTTP(S) URL.")
    summary = load_source_coverage(workspace)
    for source in summary.sources:
        if source.url.casefold() == clean_url.casefold():
            if source.category != clean_category:
                raise ValueError(
                    "This URL is already registered under another category."
                )
            return source
    source = OfficialSource(
        source_id=_source_id(clean_category, clean_url),
        category=clean_category,
        url=clean_url,
        status="registered",
        collected_at=None,
        detail=None,
    )
    _write_sources(workspace, [*summary.sources, source])
    return source


def update_source_status(
    workspace: ProjectWorkspace,
    *,
    source_id: str,
    status: str,
    detail: str | None = None,
) -> OfficialSource:
    if status not in SOURCE_STATUSES:
        raise ValueError("Invalid official-source status.")
    summary = load_source_coverage(workspace)
    updated: list[OfficialSource] = []
    selected = None
    for source in summary.sources:
        if source.source_id != source_id:
            updated.append(source)
            continue
        selected = OfficialSource(
            source_id=source.source_id,
            category=source.category,
            url=source.url,
            status=status,
            collected_at=(
                datetime.now(timezone.utc).isoformat(timespec="seconds")
                if status == "collected"
                else source.collected_at
            ),
            detail=detail,
        )
        updated.append(selected)
    if selected is None:
        raise ValueError(f"Official source does not exist: {source_id}")
    _write_sources(workspace, updated)
    return selected


def sources_for_category(
    workspace: ProjectWorkspace,
    category: str,
) -> tuple[OfficialSource, ...]:
    clean = category.strip().casefold().replace("-", "_")
    if clean not in CATEGORIES:
        raise ValueError("Unknown source category.")
    return tuple(
        source
        for source in ensure_source_coverage(workspace).sources
        if source.category == clean
    )


def coverage_markdown(workspace: ProjectWorkspace) -> str:
    summary = ensure_source_coverage(workspace)
    rows = "\n".join(
        f"| {CATEGORY_LABELS[category]} | "
        f"{summary.categories[category].replace('_', ' ').title()} |"
        for category in CATEGORIES
    )
    warning = (
        "Missing coverage means the topic was not fully assessed and does not "
        "prove that a feature or asset does not exist. `Not documented` refers "
        "only to the relevant collected sources."
    )
    return (
        "## Source Coverage\n\n"
        f"Overall coverage: **{summary.status.title()}**\n\n"
        "| Category | Coverage |\n|---|---|\n"
        f"{rows}\n\n"
        f"> {warning}\n"
    )


def source_inventory_markdown(workspace: ProjectWorkspace) -> str:
    """Render official source URLs for extraction, not for note display."""

    summary = ensure_source_coverage(workspace)
    rows = "\n".join(
        f"- {CATEGORY_LABELS[source.category]} ({source.status}): "
        f"{source.url}"
        for source in summary.sources
    )
    return (
        "### Official Source Inventory\n\n"
        "Treat URLs as provenance and preserve any explicit contract, mint, "
        "chain, or asset identifier contained in them. Do not infer other "
        "facts from URL wording alone.\n\n"
        f"{rows or '- No official sources registered.'}\n"
    )


def write_coverage_source(workspace: ProjectWorkspace) -> Path:
    path = workspace.sources_directory / "_SOURCE_COVERAGE.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = ensure_source_coverage(workspace)
    source_rows = "\n".join(
        f"- {CATEGORY_LABELS[source.category]}: {source.url} "
        f"({source.status})"
        for source in summary.sources
    ) or "- No official sources registered."
    text = (
        "# DEFINALYZER Source Coverage Metadata\n\n"
        "This file describes research-source coverage. It is not evidence "
        "about the protocol. Use it only to qualify absence claims.\n\n"
        f"{coverage_markdown(workspace)}\n"
        "### Registered Official Sources\n\n"
        f"{source_rows}\n"
    )
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def sync_research_coverage(workspace: ProjectWorkspace) -> tuple[Path, ...]:
    """Update coverage labels without regenerating analytical content."""

    changed = []
    footer = coverage_markdown(workspace).rstrip()
    status = ensure_source_coverage(workspace).status
    for path in sorted(workspace.vault_entity_directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "extraction_provider:" not in text:
            continue
        updated = text
        if "source_coverage:" in updated:
            updated = re.sub(
                r'(?m)^source_coverage: ".*"$',
                f'source_coverage: "{status}"',
                updated,
                count=1,
            )
        else:
            updated = updated.replace(
                "extraction_provider:",
                f'source_coverage: "{status}"\nextraction_provider:',
                1,
            )
        summary = ensure_source_coverage(workspace)
        if summary.status == "complete":
            updated = re.sub(
                r"(?mi)^\|(?=[^\n]*\bcoverage\b)(?=[^\n]*\bmissing\b)"
                r"[^\n]*\|\s*\n?",
                "",
                updated,
            )
        marker = "\n## Source Coverage\n"
        if marker in updated:
            updated = updated.split(marker, 1)[0].rstrip()
        updated = updated.rstrip() + "\n\n" + footer + "\n"
        if updated != text:
            temporary = path.with_suffix(".md.tmp")
            temporary.write_text(updated, encoding="utf-8", newline="\n")
            temporary.replace(path)
            changed.append(path)
    return tuple(changed)


def token_coverage_complete(workspace: ProjectWorkspace) -> bool:
    return (
        ensure_source_coverage(workspace).categories["tokenomics"]
        == "collected"
    )


def _write_sources(
    workspace: ProjectWorkspace,
    sources: list[OfficialSource],
) -> None:
    path = coverage_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": [asdict(source) for source in sources],
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _source_id(category: str, url: str) -> str:
    parsed = urlparse(url)
    tail = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
    base = slugify(f"{category}-{tail}")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    return f"{base[:71]}-{digest}"


def _validate_source(source: OfficialSource) -> None:
    if source.category not in CATEGORIES:
        raise ValueError("Source coverage contains an invalid category.")
    if source.status not in SOURCE_STATUSES:
        raise ValueError("Source coverage contains an invalid status.")
    parsed = urlparse(source.url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Source coverage contains an invalid URL.")
