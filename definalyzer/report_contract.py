"""Provider-neutral contracts and local storage for evidence-backed reports."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import urlparse

from .workspace import ENTITY_TYPES, ProjectWorkspace, slugify


REPORT_SCHEMA_VERSION = 1
REPORT_MODES = {"question", "full_review"}
REPORT_STATUSES = {
    "scoped", "evidence_ready", "draft", "quality_reviewed", "final",
}
EVIDENCE_SOURCE_TYPES = {
    "research", "source_document", "verification", "blockchain_evidence",
    "market_data", "analyst_input",
}
ASSERTION_TYPES = {
    "documented_fact", "collected_evidence", "interpretation",
    "recommendation", "uncertainty",
}
SUPPORT_LEVELS = {
    "directly_supported", "partially_supported", "unsupported", "conflicted",
}
QUALITY_STATUSES = {"not_run", "passed", "issues_found"}
REPORT_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62})$")
EVIDENCE_ID = re.compile(r"^E-[0-9]{3,}$")
ASSERTION_ID = re.compile(r"^C-[0-9]{3,}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
RESERVED_REPORT_ID = re.compile(r"(?i)^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])$")


@dataclass(frozen=True)
class ReportRequest:
    title: str
    mode: str
    question: str | None = None
    report_id: str | None = None


@dataclass(frozen=True)
class ReportPackage:
    directory: Path
    manifest_path: Path
    report_path: Path
    analyst_notes_path: Path
    evidence_path: Path
    claims_path: Path
    draft_path: Path
    quality_path: Path
    quality_markdown_path: Path
    approval_path: Path
    assets_directory: Path
    revisions_directory: Path
    exports_directory: Path


def report_package(workspace: ProjectWorkspace, report_id: str) -> ReportPackage:
    clean_id = _validate_report_id(report_id)
    directory = workspace.reports_directory / clean_id
    return ReportPackage(
        directory=directory,
        manifest_path=directory / "report.json",
        report_path=directory / "Report.md",
        analyst_notes_path=directory / "Analyst-Notes.md",
        evidence_path=directory / "evidence.json",
        claims_path=directory / "claims.json",
        draft_path=directory / "draft.json",
        quality_path=directory / "quality.json",
        quality_markdown_path=directory / "Quality.md",
        approval_path=directory / "approval.json",
        assets_directory=directory / "Assets",
        revisions_directory=directory / "Revisions",
        exports_directory=directory / "Exports",
    )


def initialize_report_package(
    *,
    workspace: ProjectWorkspace,
    request: ReportRequest,
    now: str | None = None,
) -> ReportPackage:
    """Create an empty scoped report package without invoking an AI provider."""

    title = _required_text(request.title, "Report title", maximum=140)
    if request.mode not in REPORT_MODES:
        raise ValueError("Report mode must be question or full_review.")
    question = _optional_text(request.question, "Research question", maximum=2_000)
    if request.mode == "question" and question is None:
        raise ValueError("Question reports require a research question.")
    identifier = _validate_report_id(request.report_id or slugify(title))
    created_at = report_timestamp(now)
    package = report_package(workspace, identifier)
    _ensure_report_root(workspace)
    if package.directory.exists():
        raise FileExistsError(
            f"Report already exists and will not be overwritten: {identifier}"
        )

    manifest = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": identifier,
        "project": {
            "slug": workspace.slug,
            "name": workspace.name,
            "entity_type": str(workspace.document["entity_type"]),
        },
        "title": title,
        "mode": request.mode,
        "question": question,
        "status": "scoped",
        "created_at": created_at,
        "updated_at": created_at,
        "current_revision": 0,
        "files": {
            "markdown": "Report.md",
            "analyst_notes": "Analyst-Notes.md",
            "evidence": "evidence.json",
            "claims": "claims.json",
            "draft": "draft.json",
            "quality": "quality.json",
            "quality_markdown": "Quality.md",
            "approval": "approval.json",
            "assets": "Assets",
            "revisions": "Revisions",
            "exports": "Exports",
        },
        "provenance": {
            "provider": None,
            "generated_at": None,
            "research_snapshot_sha256": None,
        },
        "quality": {
            "status": "not_run",
            "checked_at": None,
            "issues_file": None,
        },
        "human_review": {
            "recommendation_approved": False,
            "finalized_at": None,
            "approval_sha256": None,
        },
    }
    evidence = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": identifier,
        "evidence": [],
    }
    claims = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": identifier,
        "assertions": [],
    }
    validate_report_manifest(manifest, workspace=workspace)
    validate_evidence_ledger(evidence, report_id=identifier)
    validate_assertion_ledger(claims, report_id=identifier, evidence_ids=set())

    workspace.reports_directory.mkdir(parents=True, exist_ok=True)
    temporary = workspace.reports_directory / f".{identifier}-{uuid.uuid4().hex}.tmp"
    temporary.mkdir()
    try:
        _write_json(temporary / "report.json", manifest)
        _write_json(temporary / "evidence.json", evidence)
        _write_json(temporary / "claims.json", claims)
        (temporary / "Assets").mkdir()
        (temporary / "Revisions").mkdir()
        (temporary / "Exports").mkdir()
        temporary.replace(package.directory)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return package


def validate_report_manifest(
    document: Mapping[str, Any], *, workspace: ProjectWorkspace | None = None
) -> None:
    _require_schema(document)
    report_id = _validate_report_id(document.get("report_id"))
    _required_text(document.get("title"), "Report title", maximum=140)
    mode = document.get("mode")
    if mode not in REPORT_MODES:
        raise ValueError("Report manifest has an invalid mode.")
    question = _optional_text(document.get("question"), "Research question", maximum=2_000)
    if mode == "question" and question is None:
        raise ValueError("Question reports require a research question.")
    if document.get("status") not in REPORT_STATUSES:
        raise ValueError("Report manifest has an invalid status.")
    _iso_timestamp(document.get("created_at"), "created_at")
    _iso_timestamp(document.get("updated_at"), "updated_at")
    revision = document.get("current_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise ValueError("Report current_revision must be a non-negative integer.")

    project = _mapping(document.get("project"), "project")
    for field in ("slug", "name", "entity_type"):
        _required_text(project.get(field), f"Project {field}", maximum=200)
    if project.get("entity_type") not in ENTITY_TYPES:
        raise ValueError("Report project has an invalid entity_type.")
    if workspace is not None and (
        project.get("slug") != workspace.slug
        or project.get("name") != workspace.name
        or project.get("entity_type") != workspace.document["entity_type"]
    ):
        raise ValueError("Report manifest does not belong to this project.")

    files = _mapping(document.get("files"), "files")
    expected_files = {
        "markdown": "Report.md", "evidence": "evidence.json",
        "analyst_notes": "Analyst-Notes.md",
        "claims": "claims.json", "draft": "draft.json",
        "quality": "quality.json", "quality_markdown": "Quality.md",
        "approval": "approval.json",
        "assets": "Assets", "revisions": "Revisions", "exports": "Exports",
    }
    # Phase 6 added a derived Exports directory without changing the meaning of
    # existing report data. Accept earlier schema-1 manifests and create the
    # directory lazily when their first publication is exported.
    legacy_files = []
    for missing in (("exports",), ("analyst_notes",), ("exports", "analyst_notes")):
        layout = dict(expected_files)
        for key in missing:
            layout.pop(key)
        legacy_files.append(layout)
    if dict(files) not in (expected_files, *legacy_files):
        raise ValueError("Report manifest file layout is invalid.")
    provenance = _mapping(document.get("provenance"), "provenance")
    provider = provenance.get("provider")
    if provider is not None:
        _required_text(provider, "Provider", maximum=100)
    _optional_timestamp(provenance.get("generated_at"), "generated_at")
    snapshot = provenance.get("research_snapshot_sha256")
    if snapshot is not None and not (
        isinstance(snapshot, str) and SHA256.fullmatch(snapshot)
    ):
        raise ValueError("Research snapshot must be a lowercase SHA-256 digest.")
    quality = _mapping(document.get("quality"), "quality")
    if quality.get("status") not in QUALITY_STATUSES:
        raise ValueError("Report quality status is invalid.")
    _optional_timestamp(quality.get("checked_at"), "quality checked_at")
    issues_file = quality.get("issues_file")
    if issues_file is not None:
        _portable_relative_path(issues_file, "Quality issues file")
    status = document.get("status")
    if status in {"scoped", "evidence_ready", "draft"} and quality != {
        "status": "not_run", "checked_at": None, "issues_file": None,
    }:
        raise ValueError("An unreviewed report cannot contain committed quality results.")
    if status in {"quality_reviewed", "final"} and (
        quality.get("status") not in {"passed", "issues_found"}
        or quality.get("checked_at") is None
        or quality.get("issues_file") != "quality.json"
    ):
        raise ValueError("A reviewed report requires committed quality results.")
    human = _mapping(document.get("human_review"), "human_review")
    if set(human) != {
        "recommendation_approved", "finalized_at", "approval_sha256",
    }:
        raise ValueError("Report human-review metadata is invalid.")
    if not isinstance(human.get("recommendation_approved"), bool):
        raise ValueError("recommendation_approved must be boolean.")
    _optional_timestamp(human.get("finalized_at"), "finalized_at")
    approval_sha256 = human.get("approval_sha256")
    if approval_sha256 is not None and not (
        isinstance(approval_sha256, str) and SHA256.fullmatch(approval_sha256)
    ):
        raise ValueError("Report approval digest is invalid.")
    if document.get("status") == "final" and human.get("finalized_at") is None:
        raise ValueError("Final reports require a human finalized_at timestamp.")
    if document.get("status") == "final" and approval_sha256 is None:
        raise ValueError("Final reports require a committed human approval record.")
    if document.get("status") != "final" and (
        human.get("finalized_at") is not None or approval_sha256 is not None
        or human.get("recommendation_approved")
    ):
        raise ValueError("Only final reports may contain human approval state.")
    if report_id != document["report_id"]:
        raise AssertionError("Normalized report ID changed unexpectedly.")


def validate_evidence_ledger(
    document: Mapping[str, Any], *, report_id: str
) -> set[str]:
    _require_schema(document)
    if document.get("report_id") != _validate_report_id(report_id):
        raise ValueError("Evidence ledger belongs to another report.")
    rows = document.get("evidence")
    if not isinstance(rows, list):
        raise ValueError("Evidence ledger must contain an evidence list.")
    identifiers: set[str] = set()
    for row in rows:
        item = _mapping(row, "evidence entry")
        identifier = item.get("evidence_id")
        if not isinstance(identifier, str) or not EVIDENCE_ID.fullmatch(identifier):
            raise ValueError("Evidence IDs must use E-001 format.")
        if identifier in identifiers:
            raise ValueError(f"Duplicate evidence ID: {identifier}")
        identifiers.add(identifier)
        if item.get("source_type") not in EVIDENCE_SOURCE_TYPES:
            raise ValueError(f"Evidence {identifier} has an invalid source_type.")
        source_path = item.get("source_path")
        source_url = item.get("source_url")
        if source_path is not None:
            _portable_relative_path(source_path, f"Evidence {identifier} source_path")
        if source_url is not None:
            _http_url(source_url, f"Evidence {identifier} source_url")
        if source_path is None and source_url is None:
            raise ValueError(f"Evidence {identifier} requires a path or URL.")
        locator = _mapping(item.get("locator"), f"Evidence {identifier} locator")
        if not any(locator.get(key) not in (None, "") for key in ("heading", "line", "block_id")):
            raise ValueError(f"Evidence {identifier} requires a precise locator.")
        line = locator.get("line")
        if line is not None and (
            not isinstance(line, int) or isinstance(line, bool) or line < 1
        ):
            raise ValueError(f"Evidence {identifier} line must be positive.")
        end_line = locator.get("end_line")
        if end_line is not None and (
            line is None or not isinstance(end_line, int) or isinstance(end_line, bool)
            or end_line < line
        ):
            raise ValueError(f"Evidence {identifier} end_line must not precede line.")
        for locator_field in ("heading", "block_id"):
            locator_value = locator.get(locator_field)
            if locator_value is not None:
                _required_text(
                    locator_value,
                    f"Evidence {identifier} locator {locator_field}",
                    maximum=500,
                )
        digest = item.get("content_sha256")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ValueError(f"Evidence {identifier} requires a SHA-256 digest.")
        _iso_timestamp(item.get("captured_at"), f"Evidence {identifier} captured_at")
        _optional_timestamp(item.get("as_of"), f"Evidence {identifier} as_of")
        _required_text(item.get("summary"), f"Evidence {identifier} summary", maximum=1_000)
    return identifiers


def validate_assertion_ledger(
    document: Mapping[str, Any], *, report_id: str, evidence_ids: set[str]
) -> set[str]:
    _require_schema(document)
    if document.get("report_id") != _validate_report_id(report_id):
        raise ValueError("Assertion ledger belongs to another report.")
    rows = document.get("assertions")
    if not isinstance(rows, list):
        raise ValueError("Assertion ledger must contain an assertions list.")
    identifiers: set[str] = set()
    for row in rows:
        item = _mapping(row, "assertion")
        identifier = item.get("assertion_id")
        if not isinstance(identifier, str) or not ASSERTION_ID.fullmatch(identifier):
            raise ValueError("Assertion IDs must use C-001 format.")
        if identifier in identifiers:
            raise ValueError(f"Duplicate assertion ID: {identifier}")
        identifiers.add(identifier)
        assertion_type = item.get("assertion_type")
        if assertion_type not in ASSERTION_TYPES:
            raise ValueError(f"Assertion {identifier} has an invalid type.")
        support = item.get("support")
        if support not in SUPPORT_LEVELS:
            raise ValueError(f"Assertion {identifier} has an invalid support level.")
        _required_text(item.get("statement"), f"Assertion {identifier} statement", maximum=2_000)
        _required_text(item.get("report_section"), f"Assertion {identifier} section", maximum=200)
        _required_text(item.get("rationale"), f"Assertion {identifier} rationale", maximum=2_000)
        references = item.get("evidence_ids")
        if not isinstance(references, list) or any(
            not isinstance(value, str) for value in references
        ):
            raise ValueError(f"Assertion {identifier} evidence_ids must be a list.")
        if len(references) != len(set(references)):
            raise ValueError(f"Assertion {identifier} repeats an evidence ID.")
        unknown = set(references) - evidence_ids
        if unknown:
            raise ValueError(
                f"Assertion {identifier} references unknown evidence: "
                + ", ".join(sorted(unknown))
            )
        if assertion_type != "uncertainty" and not references:
            raise ValueError(
                f"Assertion {identifier} requires evidence; only an uncertainty may stand alone."
            )
        if assertion_type in {"documented_fact", "collected_evidence"} and support == "unsupported":
            raise ValueError(f"Assertion {identifier} cannot label an unsupported statement as fact.")
        if assertion_type != "uncertainty" and support == "unsupported":
            raise ValueError(f"Only an uncertainty may be unsupported: {identifier}.")
        limitations = item.get("limitations")
        if not isinstance(limitations, list) or any(
            not isinstance(value, str) or not value.strip() for value in limitations
        ):
            raise ValueError(f"Assertion {identifier} limitations must be a string list.")
    return identifiers


def content_sha256(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def _validate_report_id(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not REPORT_ID.fullmatch(value)
        or RESERVED_REPORT_ID.fullmatch(value)
    ):
        raise ValueError("Report ID must be a lowercase, hyphenated portable identifier.")
    return value


def _required_text(value: Any, label: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")
    clean = value.strip()
    if len(clean) > maximum or any(ord(character) < 32 for character in clean):
        raise ValueError(f"{label} is invalid or exceeds {maximum} characters.")
    return clean


def _optional_text(value: Any, label: str, *, maximum: int) -> str | None:
    if value is None:
        return None
    return _required_text(value, label, maximum=maximum)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Report {label} must be an object.")
    return value


def _require_schema(document: Mapping[str, Any]) -> None:
    if not isinstance(document, Mapping) or document.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError(f"Report data must use schema_version {REPORT_SCHEMA_VERSION}.")


def _portable_relative_path(value: Any, label: str) -> str:
    if (
        not isinstance(value, str) or not value or "\\" in value
        or ":" in value or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(f"{label} must be a portable relative path.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"{label} must remain inside the report workspace.")
    return value


def _http_url(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an HTTP(S) URL.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{label} must be an HTTP(S) URL without credentials.")
    return value


def _iso_timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone offset.")
    return value


def _optional_timestamp(value: Any, label: str) -> str | None:
    return None if value is None else _iso_timestamp(value, label)


def report_timestamp(value: str | None) -> str:
    if value is not None:
        return _iso_timestamp(value, "Report timestamp")
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _ensure_report_root(workspace: ProjectWorkspace) -> None:
    root = (workspace.vault_root / "Reports").resolve()
    candidate = workspace.reports_directory.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Report storage must remain inside the research workspace.") from exc
