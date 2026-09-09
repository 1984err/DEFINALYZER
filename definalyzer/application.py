"""Stable application boundary shared by terminal and future dashboard shells."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .analyst_review import (
    AnalystReviewResult,
    ReviewSection,
    list_review_pages,
    run_analyst_review,
    save_analyst_review,
)
from .dune_assistant import (
    DuneAssistantResult,
    DuneCandidate,
    list_dune_candidates,
    run_dune_dialogue,
)
from .evaluation import pending_proposals
from .market_data import MarketRefreshResult, refresh_market_data
from .providers import TextProvider, create_provider
from .registry_workflow import refresh_token_pages_from_registry
from .report_contract import (
    REPORT_ID, ReportRequest, initialize_report_package, report_package,
    validate_report_manifest,
)
from .report_evidence import prepare_report_evidence
from .report_export import ChartRequest, ReportExportResult, export_final_report
from .report_generation import ReportDraft, generate_report_draft, load_report_draft
from .report_lifecycle import (
    FinalReportResult, ReportRevisionResult, finalize_report,
    revise_report_assertion,
)
from .report_quality import ReportQualityResult, review_report_quality
from .settings import SettingsManager
from .workflow_status import workflow_status_document
from .workspace import ProjectWorkspace, WorkspaceManager


ProviderFactory = Callable[[Mapping[str, object]], TextProvider]
APPLICATION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ActionAvailability:
    available: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"available": self.available, "reason": self.reason}


@dataclass(frozen=True)
class ProjectSnapshot:
    """JSON-safe project state suitable for terminal or dashboard rendering."""

    name: str
    slug: str
    entity_type: str
    docs_url: str | None
    verification_status: str
    workflow: Mapping[str, object]
    stages: Mapping[str, object]
    paths: Mapping[str, str]
    research_pages: tuple[str, ...]
    dune_candidates: tuple[str, ...]
    pending_assessments: int
    actions: Mapping[str, ActionAvailability]

    def to_dict(self) -> dict[str, object]:
        return {
            "application_schema_version": APPLICATION_SCHEMA_VERSION,
            "name": self.name,
            "slug": self.slug,
            "entity_type": self.entity_type,
            "docs_url": self.docs_url,
            "verification_status": self.verification_status,
            "workflow": dict(self.workflow),
            "stages": dict(self.stages),
            "paths": dict(self.paths),
            "research_pages": list(self.research_pages),
            "dune_candidates": list(self.dune_candidates),
            "pending_assessments": self.pending_assessments,
            "actions": {
                key: value.to_dict() for key, value in self.actions.items()
            },
        }


@dataclass(frozen=True)
class MarketDataResult:
    refresh: MarketRefreshResult
    token_pages: tuple[Path, ...]


@dataclass(frozen=True)
class ReportSummary:
    report_id: str
    title: str
    mode: str
    question: str | None
    status: str
    revision: int
    quality_status: str
    created_at: str
    updated_at: str
    finalized_at: str | None
    recommendation_approved: bool
    readiness: str | None
    report_page: str | None
    analyst_notes_page: str | None
    quality_page: str | None
    export_revisions: tuple[int, ...]
    actions: Mapping[str, ActionAvailability]
    schema_version: int = 1
    historical: bool = False
    revision_hash: str | None = None
    needs_recommendation_approval: bool = False
    message: str = ""
    edited_files: tuple[str, ...] = ()
    recovery: Mapping[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "historical": self.historical,
            "revision_hash": self.revision_hash,
            "needs_recommendation_approval": self.needs_recommendation_approval,
            "message": self.message,
            "edited_files": list(self.edited_files),
            "recovery": dict(self.recovery) if self.recovery else None,
            "report_id": self.report_id,
            "title": self.title,
            "mode": self.mode,
            "question": self.question,
            "status": self.status,
            "revision": self.revision,
            "quality_status": self.quality_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "finalized_at": self.finalized_at,
            "recommendation_approved": self.recommendation_approved,
            "readiness": self.readiness,
            "report_page": self.report_page,
            "analyst_notes_page": self.analyst_notes_page,
            "quality_page": self.quality_page,
            "export_revisions": list(self.export_revisions),
            "actions": {
                key: value.to_dict() for key, value in self.actions.items()
            },
        }


class DefinalyzerApplication:
    """UI-neutral access to project state and reusable domain operations."""

    def __init__(
        self,
        manager: WorkspaceManager,
        *,
        provider_factory: ProviderFactory = create_provider,
    ) -> None:
        self.manager = manager
        self.settings = SettingsManager(manager.root)
        self._provider_factory = provider_factory

    def initialize(self) -> None:
        self.manager.initialize()

    def create_project(
        self,
        *,
        name: str,
        entity_type: str = "protocol",
        docs_url: str | None = None,
        verification_status: str = "not_requested",
    ) -> ProjectWorkspace:
        return self.manager.create_project(
            name=name,
            entity_type=entity_type,
            docs_url=docs_url,
            verification_status=verification_status,
        )

    def load_project(self, name_or_slug: str) -> ProjectWorkspace:
        return self.manager.load_project(name_or_slug)

    def start_asset_research(self, asset_id: str) -> ProjectWorkspace:
        from .asset_identity import start_asset_research
        return start_asset_research(self.manager, asset_id)

    def list_projects(self) -> tuple[ProjectSnapshot, ...]:
        return tuple(self.snapshot(row) for row in self.manager.list_projects())

    def delete_project(self, name_or_slug: str) -> tuple[Path, ...]:
        return self.manager.delete_project(self.load_project(name_or_slug))

    def refresh_indexes(self) -> tuple[Path, ...]:
        return self.manager.refresh_vault_indexes()

    def provider(self) -> TextProvider:
        return self._provider_factory(self.settings.load()["llm"])

    def snapshot(self, workspace: ProjectWorkspace | str) -> ProjectSnapshot:
        project = (
            self.load_project(workspace)
            if isinstance(workspace, str)
            else workspace
        )
        workflow = workflow_status_document(project)
        pages = tuple(path.name for path in list_review_pages(project))
        try:
            candidates = list_dune_candidates(project)
        except (FileNotFoundError, ValueError):
            candidates = ()
        proposals = pending_proposals(project)
        actions = _action_availability(
            project,
            workflow=workflow,
            research_pages=pages,
            dune_candidates=candidates,
            pending_assessments=len(proposals),
        )
        status = self.manager.status_document(project)
        paths = {
            key: str(status[key])
            for key in (
                "sources",
                "vault",
                "verification",
                "registry",
                "jobs",
                "evidence",
            )
        }
        return ProjectSnapshot(
            name=project.name,
            slug=project.slug,
            entity_type=str(project.document["entity_type"]),
            docs_url=(
                str(project.document["docs_url"])
                if project.document.get("docs_url")
                else None
            ),
            verification_status=str(project.document["verification_status"]),
            workflow=workflow,
            stages=dict(project.document["stages"]),
            paths=paths,
            research_pages=pages,
            dune_candidates=tuple(row.verification_id for row in candidates),
            pending_assessments=len(proposals),
            actions=actions,
        )

    def ask(
        self,
        *,
        workspace: ProjectWorkspace,
        question: str,
        deep: bool = False,
        page: Path | None = None,
        section: ReviewSection | None = None,
        save: bool = False,
    ) -> AnalystReviewResult:
        result = run_analyst_review(
            workspace=workspace,
            provider=self.provider(),
            question=question,
            deep=deep,
            page=page,
            section=section,
        )
        return (
            save_analyst_review(workspace=workspace, result=result)
            if save
            else result
        )

    def dune_candidates(
        self, workspace: ProjectWorkspace
    ) -> tuple[DuneCandidate, ...]:
        return list_dune_candidates(workspace)

    def dune_dialogue(
        self,
        *,
        workspace: ProjectWorkspace,
        verification_id: str,
        feedback_type: str | None = None,
        feedback: str | None = None,
    ) -> DuneAssistantResult:
        return run_dune_dialogue(
            workspace=workspace,
            provider=self.provider(),
            verification_id=verification_id,
            feedback_type=feedback_type,
            feedback=feedback,
        )

    def refresh_market_data(
        self,
        *,
        workspace: ProjectWorkspace,
        force: bool = False,
        asset_id: str = "",
    ) -> MarketDataResult:
        refresh = refresh_market_data(workspace=workspace, force=force, asset_id=asset_id)
        pages = refresh_token_pages_from_registry(workspace, asset_id=asset_id)
        return MarketDataResult(refresh=refresh, token_pages=pages)

    def reports(self, workspace: ProjectWorkspace) -> tuple[ReportSummary, ...]:
        """Return validated report lifecycle state for any user interface."""
        root = workspace.reports_directory
        if not root.exists():
            return ()
        rows = []
        for directory in sorted(
            (path for path in root.iterdir() if path.is_dir()),
            key=lambda path: path.name.casefold(),
        ):
            if (
                not REPORT_ID.fullmatch(directory.name)
                or directory.is_symlink()
                or getattr(directory, "is_junction", lambda: False)()
            ):
                continue
            package = report_package(workspace, directory.name)
            manifest = _read_report_json(package.manifest_path)
            validate_report_manifest(manifest, workspace=workspace)
            exports = []
            if package.exports_directory.exists():
                for export in package.exports_directory.iterdir():
                    if not export.is_dir() or not export.name.startswith("revision-"):
                        continue
                    try:
                        exports.append(int(export.name.removeprefix("revision-")))
                    except ValueError:
                        continue
            relative_root = package.directory.relative_to(workspace.vault_root)
            status = str(manifest["status"])
            quality_status = str(manifest["quality"]["status"])
            revision = int(manifest["current_revision"])
            readiness = None
            if package.draft_path.exists():
                readiness = load_report_draft(
                    workspace=workspace, report_id=manifest["report_id"]
                ).readiness
            publishable = readiness != "insufficient"
            actions = {
                "generate": ActionAvailability(
                    status in {"scoped", "evidence_ready"},
                    None if status in {"scoped", "evidence_ready"} else "This report already has a draft.",
                ),
                "prepare_evidence": ActionAvailability(
                    status == "scoped",
                    None if status == "scoped" else "Evidence can only be prepared for a scoped report.",
                ),
                "generate_draft": ActionAvailability(
                    status == "evidence_ready",
                    None if status == "evidence_ready" else "Prepare the evidence package first.",
                ),
                "review_quality": ActionAvailability(
                    status == "draft" and publishable,
                    None if status == "draft" and publishable else (
                        "Insufficient evidence produced Analyst Notes only."
                        if readiness == "insufficient"
                        else "Quality review requires a committed draft."
                    ),
                ),
                "revise": ActionAvailability(
                    status in {"draft", "quality_reviewed", "final"} and publishable,
                    None if status in {"draft", "quality_reviewed", "final"} and publishable else (
                        "Insufficient evidence produced Analyst Notes only."
                        if readiness == "insufficient" else "Generate a draft first."
                    ),
                ),
                "finalize": ActionAvailability(
                    status == "quality_reviewed" and quality_status == "passed",
                    None
                    if status == "quality_reviewed" and quality_status == "passed"
                    else "Finalization requires a passing quality review.",
                ),
                "export": ActionAvailability(
                    status == "final" and revision not in exports,
                    None
                    if status == "final" and revision not in exports
                    else (
                        "This final revision is already exported."
                        if status == "final" and revision in exports
                        else "Only a finalized report can be exported."
                    ),
                ),
            }
            rows.append(ReportSummary(
                report_id=manifest["report_id"], title=manifest["title"],
                mode=manifest["mode"], question=manifest["question"],
                status=status, revision=revision, quality_status=quality_status,
                created_at=manifest["created_at"], updated_at=manifest["updated_at"],
                finalized_at=manifest["human_review"]["finalized_at"],
                recommendation_approved=manifest["human_review"]["recommendation_approved"],
                readiness=readiness,
                report_page=(relative_root / "Report.md").as_posix()
                if package.report_path.exists() else None,
                analyst_notes_page=(relative_root / "Analyst-Notes.md").as_posix()
                if package.analyst_notes_path.exists() else None,
                quality_page=(relative_root / "Quality.md").as_posix()
                if package.quality_markdown_path.exists() else None,
                export_revisions=tuple(sorted(set(exports))), actions=actions,
            ))
        from .report_v2 import summaries
        rows.extend(summaries(workspace))
        return tuple(rows)

    def create_report(
        self, *, workspace: ProjectWorkspace, title: str, mode: str,
        question: str | None = None, schema_version: int = 1,
        recommendations: bool = False, audience: str = "researcher", depth: str = "standard",
    ) -> ReportSummary:
        if schema_version == 2:
            from .report_v2_store import create
            record = create(workspace, title=title, mode=mode, question=question,
                            recommendations=recommendations, audience=audience, depth=depth)
            return next(row for row in self.reports(workspace) if row.report_id == record["report_id"])
        if schema_version != 1:
            raise ValueError("Unsupported report version.")
        package = initialize_report_package(
            workspace=workspace,
            request=ReportRequest(title=title, mode=mode, question=question),
        )
        return next(
            row for row in self.reports(workspace)
            if row.report_id == package.directory.name
        )

    def delete_report(self, *, workspace: ProjectWorkspace, report_id: str) -> dict[str, str]:
        """Remove a report from the product, retaining its package outside the vault."""
        from uuid import uuid4
        from .app import _project_workflow_lock
        from .report_v2_store import package as v2_package
        with _project_workflow_lock(workspace):
            source = report_package(workspace, report_id).directory
            if report_id.startswith("v2-") and not source.is_dir():
                source = v2_package(workspace, report_id)
            root = workspace.root.resolve()
            destination = root / "trash" / "reports" / f"{workspace.slug}-{report_id}-{uuid4().hex}"
            for path in (source, destination):
                if not path.resolve().is_relative_to(root):
                    raise ValueError("Report removal path escapes the workspace.")
                for parent in (path, *path.parents):
                    if parent == root:
                        break
                    if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                        raise ValueError("Report removal cannot follow linked directories.")
            if not source.is_dir() or not (source / "report.json").is_file():
                raise FileNotFoundError("Report was not found.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
            return {"report_id": report_id, "archived_to": str(destination)}

    def report_detail(
        self, *, workspace: ProjectWorkspace, report_id: str,
    ) -> dict[str, object]:
        from .report_v2_store import exists
        if exists(workspace, report_id):
            from .report_v2 import detail
            return detail(workspace, report_id)
        summary = next(
            (row for row in self.reports(workspace) if row.report_id == report_id),
            None,
        )
        if summary is None:
            raise FileNotFoundError("Report was not found.")
        assertions: list[dict[str, object]] = []
        package = report_package(workspace, report_id)
        if package.draft_path.exists():
            draft = load_report_draft(workspace=workspace, report_id=report_id)
            assertions = [{
                "assertion_id": row["assertion_id"],
                "statement": row["statement"],
                "report_section": row["report_section"],
                "support": row["support"],
            } for row in draft.claims["assertions"]]
        return {"report": summary.to_dict(), "assertions": assertions}

    def prepare_report_evidence(
        self, *, workspace: ProjectWorkspace, report_id: str,
    ) -> dict[str, Any]:
        return prepare_report_evidence(workspace=workspace, report_id=report_id)

    def generate_report(
        self, *, workspace: ProjectWorkspace, report_id: str, progress=None,
    ) -> ReportDraft:
        from .report_v2_store import exists
        if exists(workspace, report_id):
            from .report_v2 import generate
            return generate(workspace, report_id, provider=self.provider(), progress=progress)
        return generate_report_draft(
            workspace=workspace, report_id=report_id, provider=self.provider()
        )

    def generate_complete_report(self, *, workspace, report_id, progress=None):
        """Run the existing saved-evidence workflow once, without automatic repair."""
        from .cancellation import check_cancelled
        package = report_package(workspace, report_id)
        manifest = _read_report_json(package.manifest_path)
        validate_report_manifest(manifest, workspace=workspace)
        if manifest["status"] not in {"scoped", "evidence_ready"}:
            raise ValueError("This report already has a draft.")
        progress = progress or (lambda message: None)
        check_cancelled()
        if manifest["status"] == "scoped":
            progress("[1/3] Preparing saved evidence")
            self.prepare_report_evidence(workspace=workspace, report_id=report_id)
        check_cancelled()
        progress("[2/3] Writing report from saved evidence")
        # Call the normal engine directly: leftover experimental state must not
        # dispatch this combined workflow to V2.
        draft = generate_report_draft(
            workspace=workspace, report_id=report_id, provider=self.provider()
        )
        check_cancelled()
        if draft.readiness == "insufficient":
            progress("Saved evidence is insufficient; read the analyst notes for missing inputs.")
            return draft
        progress("[3/3] Checking the report against saved evidence")
        result = self.review_report(workspace=workspace, report_id=report_id)
        progress("Report ready to read and download." if result.status == "passed"
                 else "Report saved with review issues. Read the quality review before sharing.")
        return result

    def review_report(
        self, *, workspace: ProjectWorkspace, report_id: str,
    ) -> ReportQualityResult:
        return review_report_quality(
            workspace=workspace, report_id=report_id, provider=self.provider()
        )

    def revise_report(
        self, *, workspace: ProjectWorkspace, report_id: str,
        assertion_id: str, instruction: str, expected_revision=None, progress=None,
    ) -> ReportRevisionResult:
        from .report_v2_store import exists
        if exists(workspace, report_id):
            from .report_v2 import generate
            return generate(workspace, report_id, provider=self.provider(), operation="revise",
                            target=assertion_id or "report", instruction=instruction, expected_revision=expected_revision, progress=progress)
        return revise_report_assertion(
            workspace=workspace, report_id=report_id,
            assertion_id=assertion_id, instruction=instruction,
            provider=self.provider(),
        )

    def finalize_report(
        self, *, workspace: ProjectWorkspace, report_id: str,
        human_approved: bool, recommendation_approved: bool = False, expected_revision=None,
    ) -> FinalReportResult:
        from .report_v2_store import exists, finalize
        if exists(workspace, report_id):
            return finalize(workspace, report_id, human_approved=human_approved,
                            recommendation_approved=recommendation_approved, expected_revision=expected_revision)
        return finalize_report(
            workspace=workspace, report_id=report_id,
            human_approved=human_approved,
            recommendation_approved=recommendation_approved,
        )

    def export_report(
        self, *, workspace: ProjectWorkspace, report_id: str,
        formats: tuple[str, ...], charts: tuple[ChartRequest, ...] = (), chart_ids=(),
    ) -> ReportExportResult:
        from .report_v2_store import exists
        if exists(workspace, report_id):
            if charts:
                raise ValueError("V2 exports use suggested charts from checked quantities, not manual field mappings.")
            from .report_v2_export import export
            return export(workspace, report_id, formats=formats, chart_ids=chart_ids)
        return export_final_report(
            workspace=workspace, report_id=report_id,
            formats=formats, charts=charts,
        )

    def change_report(self, *, workspace, report_id, operation, expected_revision=None, texts=None, progress=None):
        from .report_v2_store import exists
        if not exists(workspace, report_id):
            raise ValueError("This operation requires a V2 report.")
        from .report_v2 import generate
        return generate(workspace, report_id, provider=self.provider(), operation=operation,
                        expected_revision=expected_revision, texts=texts, progress=progress)


def _read_report_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return document


def _action_availability(
    workspace: ProjectWorkspace,
    *,
    workflow: Mapping[str, object],
    research_pages: tuple[str, ...],
    dune_candidates: tuple[DuneCandidate, ...],
    pending_assessments: int,
) -> dict[str, ActionAvailability]:
    ready = set(workflow.get("ready_stage_names", []))
    docs_url = bool(workspace.document.get("docs_url"))
    verification_page = workspace.verification_page_path.exists()
    job = (workspace.jobs_directory / "verification-plan.json").exists()
    has_sources = any(workspace.sources_directory.rglob("*.md"))
    return {
        "analyze": ActionAvailability(
            docs_url or has_sources,
            None if docs_url or has_sources else "No documentation URL or saved sources are available.",
        ),
        "crawl": ActionAvailability(
            docs_url,
            None if docs_url else "No documentation URL is configured.",
        ),
        "research": ActionAvailability(
            "crawl" in ready,
            None if "crawl" in ready else "Collect documentation first.",
        ),
        "official_sources": ActionAvailability(True),
        "manual_token": ActionAvailability(True),
        "provider_settings": ActionAvailability(True),
        "project_status": ActionAvailability(True),
        "standalone_collector": ActionAvailability(True),
        "registry": ActionAvailability(
            "research" in ready,
            None if "research" in ready else "Generate research pages first.",
        ),
        "verification_plan": ActionAvailability(
            "registry" in ready,
            None if "registry" in ready else "Generate the registry first.",
        ),
        "collect_evidence": ActionAvailability(
            verification_page and job and "verification_plan" in ready,
            None
            if verification_page and job and "verification_plan" in ready
            else "No current scanner-ready verification job exists.",
        ),
        "evaluate_evidence": ActionAvailability(
            "evidence_collection" in ready,
            None
            if "evidence_collection" in ready
            else "Collect blockchain evidence first.",
        ),
        "review_assessments": ActionAvailability(
            pending_assessments > 0,
            None if pending_assessments else "No assessment proposals are pending.",
        ),
        "ask": ActionAvailability(
            bool(research_pages),
            None if research_pages else "No research pages exist.",
        ),
        "dune": ActionAvailability(
            bool(dune_candidates),
            None
            if dune_candidates
            else "No verification checks are marked as Dune candidates.",
        ),
        "market_data": ActionAvailability(
            (workspace.registry_directory / "registry.json").exists(),
            None
            if (workspace.registry_directory / "registry.json").exists()
            else "Generate the registry first.",
        ),
        "refresh_indexes": ActionAvailability(True),
        "delete": ActionAvailability(True),
    }
