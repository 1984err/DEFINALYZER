"""Stable application boundary shared by terminal and future dashboard shells."""

from __future__ import annotations

from dataclasses import dataclass
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
    ) -> MarketDataResult:
        refresh = refresh_market_data(workspace=workspace, force=force)
        pages = refresh_token_pages_from_registry(workspace)
        return MarketDataResult(refresh=refresh, token_pages=pages)


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
    return {
        "analyze": ActionAvailability(
            docs_url,
            None if docs_url else "No documentation URL is configured.",
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
