"""Project manifests and Obsidian-ready output paths."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


WORKSPACE_SCHEMA_VERSION = 1
ENTITY_TYPES = {"protocol", "chain", "token"}
VERIFICATION_STATUSES = {
    "not_requested",
    "unsupported",
    "pending",
    "evidence_collected",
    "manual_review",
    "supported",
    "contradicted",
    "inconclusive",
}
STAGE_NAMES = (
    "crawl",
    "research",
    "registry",
    "verification_plan",
    "evidence_collection",
    "evidence_evaluation",
    "obsidian_links",
)
STAGE_STATUSES = {"not_started", "pending", "complete", "partial", "blocked"}


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return value.strip("-") or "research-project"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ProjectWorkspace:
    root: Path
    document: Mapping[str, Any]

    @property
    def slug(self) -> str:
        return str(self.document["slug"])

    @property
    def name(self) -> str:
        return str(self.document["name"])

    @property
    def manifest_path(self) -> Path:
        return self.root / "projects" / self.slug / "project.json"

    @property
    def project_root(self) -> Path:
        return self.manifest_path.parent

    @property
    def sources_directory(self) -> Path:
        return self.root / "sources" / self.slug

    @property
    def registry_directory(self) -> Path:
        return self.root / "registries" / self.slug

    @property
    def jobs_directory(self) -> Path:
        return self.project_root / "jobs"

    @property
    def evidence_directory(self) -> Path:
        return self.project_root / "evidence"

    @property
    def vault_root(self) -> Path:
        return self.root / "vault"

    @property
    def vault_entity_directory(self) -> Path:
        folder = {
            "protocol": "Protocols",
            "chain": "Chains",
            "token": "Tokens",
        }[str(self.document["entity_type"])]
        return self.vault_root / folder / self.name

    @property
    def verification_directory(self) -> Path:
        return self.vault_root / "Verification" / self.name

    @property
    def verification_page_path(self) -> Path:
        return self.verification_directory / "Index.md"


class WorkspaceManager:
    def __init__(self, root: str | Path = "output") -> None:
        self.root = Path(root).resolve()

    def initialize(self) -> None:
        directories = (
            self.root / "projects",
            self.root / "sources",
            self.root / "registries",
            self.root / "vault" / "Protocols",
            self.root / "vault" / "Chains",
            self.root / "vault" / "Tokens",
            self.root / "vault" / "Verification",
            self.root / "vault" / "Analyst Reviews",
            self.root / "vault" / "Indexes",
        )
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        readme = self.root / "vault" / "README.md"
        if not readme.exists():
            readme.write_text(
                "# DEFINALYZER Research Vault\n\n"
                "Open this folder as an Obsidian vault. Research notes are "
                "usable independently of verification status.\n",
                encoding="utf-8",
            )

    def create_project(
        self,
        *,
        name: str,
        entity_type: str = "protocol",
        docs_url: str | None = None,
        verification_status: str = "not_requested",
    ) -> ProjectWorkspace:
        self.initialize()
        clean_name = name.strip()

        if not clean_name:
            raise ValueError("Project name cannot be empty.")
        if entity_type not in ENTITY_TYPES:
            raise ValueError(
                "Entity type must be protocol, chain, or token."
            )
        if verification_status not in VERIFICATION_STATUSES:
            raise ValueError(
                f"Unsupported verification status {verification_status!r}."
            )

        slug = slugify(clean_name)
        manifest = self.root / "projects" / slug / "project.json"

        if manifest.exists():
            raise FileExistsError(
                f"Project already exists and will not be overwritten: {slug}"
            )

        now = timestamp()
        document = {
            "schema_version": WORKSPACE_SCHEMA_VERSION,
            "slug": slug,
            "name": clean_name,
            "entity_type": entity_type,
            "docs_url": docs_url.strip() if docs_url else None,
            "verification_status": verification_status,
            "created_at": now,
            "updated_at": now,
            "stages": {
                stage: {
                    "status": "not_started",
                    "updated_at": None,
                    "detail": None,
                }
                for stage in STAGE_NAMES
            },
        }
        workspace = ProjectWorkspace(self.root, document)

        for directory in (
            workspace.project_root,
            workspace.sources_directory,
            workspace.registry_directory,
            workspace.jobs_directory,
            workspace.evidence_directory,
            workspace.vault_entity_directory,
            workspace.verification_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        self._write_new(document, manifest)
        self._write_project_index(workspace)
        from .source_coverage import (
            ensure_source_coverage,
            write_coverage_source,
        )

        ensure_source_coverage(workspace)
        write_coverage_source(workspace)
        return workspace

    def refresh_vault_indexes(self) -> tuple[Path, ...]:
        """Regenerate deterministic vault navigation without using AI."""
        from .vault_indexes import generate_vault_indexes

        return generate_vault_indexes(self.root)

    def load_project(self, name_or_slug: str) -> ProjectWorkspace:
        slug = slugify(name_or_slug)
        manifest = self.root / "projects" / slug / "project.json"

        if not manifest.exists():
            raise FileNotFoundError(f"Project does not exist: {slug}")

        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Project manifest is invalid JSON: {manifest}: {exc.msg}"
            ) from exc

        self._validate_document(document)
        workspace = ProjectWorkspace(self.root, document)
        self._migrate_verification_page(workspace)
        return workspace

    def list_projects(self) -> list[ProjectWorkspace]:
        if not self.root.exists():
            return []

        projects = []
        for manifest in sorted((self.root / "projects").glob("*/project.json")):
            projects.append(self.load_project(manifest.parent.name))
        return projects

    def update_stage(
        self,
        workspace: ProjectWorkspace,
        stage: str,
        status: str,
        *,
        detail: str | None = None,
    ) -> ProjectWorkspace:
        if stage not in STAGE_NAMES:
            raise ValueError(f"Unknown project stage {stage!r}.")
        if status not in STAGE_STATUSES:
            raise ValueError(f"Unknown stage status {status!r}.")

        document = dict(workspace.document)
        stages = {
            key: dict(value)
            for key, value in document["stages"].items()
        }
        now = timestamp()
        stages[stage] = {
            "status": status,
            "updated_at": now,
            "detail": detail,
        }
        document["stages"] = stages
        document["updated_at"] = now
        self._replace(document, workspace.manifest_path)
        return ProjectWorkspace(self.root, document)

    def set_verification_status(
        self,
        workspace: ProjectWorkspace,
        status: str,
    ) -> ProjectWorkspace:
        if status not in VERIFICATION_STATUSES:
            raise ValueError(f"Unsupported verification status {status!r}.")

        document = dict(workspace.document)
        document["verification_status"] = status
        document["updated_at"] = timestamp()
        self._replace(document, workspace.manifest_path)
        updated = ProjectWorkspace(self.root, document)
        self._update_project_index_status(updated)
        return updated

    def set_docs_url(
        self,
        workspace: ProjectWorkspace,
        docs_url: str,
    ) -> ProjectWorkspace:
        clean_url = docs_url.strip()
        if not clean_url:
            raise ValueError("Documentation URL cannot be empty.")

        document = dict(workspace.document)
        document["docs_url"] = clean_url
        document["updated_at"] = timestamp()
        self._replace(document, workspace.manifest_path)
        return ProjectWorkspace(self.root, document)

    def status_document(self, workspace: ProjectWorkspace) -> dict[str, Any]:
        return {
            "name": workspace.name,
            "slug": workspace.slug,
            "entity_type": workspace.document["entity_type"],
            "docs_url": workspace.document["docs_url"],
            "verification_status": workspace.document["verification_status"],
            "stages": workspace.document["stages"],
            "sources": str(workspace.sources_directory),
            "vault": str(workspace.vault_entity_directory),
            "verification": str(workspace.verification_page_path),
            "registry": str(workspace.registry_directory),
            "jobs": str(workspace.jobs_directory),
            "evidence": str(workspace.evidence_directory),
        }

    @staticmethod
    def _migrate_verification_page(workspace: ProjectWorkspace) -> None:
        legacy = (
            workspace.vault_root
            / "Verification"
            / f"{workspace.name} - Verification.md"
        )
        canonical = workspace.verification_page_path
        if not legacy.exists():
            return
        canonical.parent.mkdir(parents=True, exist_ok=True)
        if canonical.exists():
            if legacy.read_bytes() != canonical.read_bytes():
                raise FileExistsError(
                    "Both legacy and canonical verification pages exist with "
                    f"different contents: {legacy}; {canonical}"
                )
            legacy.unlink()
        else:
            legacy.replace(canonical)

        replacements = {
            f"[[Verification/{workspace.name} - Verification#": (
                f"[[Verification/{workspace.name}/Index#"
            ),
            f"[[{workspace.name} - Verification#": (
                f"[[Verification/{workspace.name}/Index#"
            ),
        }
        pages = [
            *workspace.vault_entity_directory.glob("*.md"),
            canonical,
        ]
        for page in pages:
            if not page.exists():
                continue
            text = page.read_text(encoding="utf-8")
            updated = text
            for old, new in replacements.items():
                updated = updated.replace(old, new)
            if updated != text:
                page.write_text(updated, encoding="utf-8", newline="\n")

    @staticmethod
    def _write_new(document: Mapping[str, Any], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as file:
            json.dump(document, file, indent=2)
            file.write("\n")

    @staticmethod
    def _replace(document: Mapping[str, Any], path: Path) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(document, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _validate_document(document: Any) -> None:
        if not isinstance(document, dict):
            raise ValueError("Project manifest must be a JSON object.")
        if document.get("schema_version") != WORKSPACE_SCHEMA_VERSION:
            raise ValueError("Unsupported project manifest schema version.")
        if document.get("entity_type") not in ENTITY_TYPES:
            raise ValueError("Project manifest has an invalid entity type.")
        if document.get("verification_status") not in VERIFICATION_STATUSES:
            raise ValueError("Project manifest has an invalid verification status.")
        stages = document.get("stages")
        if not isinstance(stages, dict) or set(stages) != set(STAGE_NAMES):
            raise ValueError("Project manifest has invalid stages.")

    @staticmethod
    def _write_project_index(workspace: ProjectWorkspace) -> None:
        index = workspace.vault_entity_directory / "Index.md"
        if index.exists():
            return
        index.write_text(
            "---\n"
            f'entity: "{workspace.name}"\n'
            f'entity_type: "{workspace.document["entity_type"]}"\n'
            f'verification_status: "{workspace.document["verification_status"]}"\n'
            "---\n\n"
            f"# {workspace.name}\n\n"
            "Research pages will be stored in this folder.\n",
            encoding="utf-8",
        )

    @staticmethod
    def _update_project_index_status(workspace: ProjectWorkspace) -> None:
        index = workspace.vault_entity_directory / "Index.md"
        if not index.exists():
            return
        text = index.read_text(encoding="utf-8")
        text = re.sub(
            r'(?m)^verification_status: ".*"$',
            (
                "verification_status: "
                f'"{workspace.document["verification_status"]}"'
            ),
            text,
            count=1,
        )
        index.write_text(text, encoding="utf-8")
