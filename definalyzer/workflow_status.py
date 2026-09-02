"""Read-only effective project readiness shared by CLI and vault indexes."""

from __future__ import annotations

import re
from pathlib import Path

from .dependencies import stale_research_pages
from .evaluation import pending_proposals
from .extraction import OUTPUT_FILES
from .workspace import ProjectWorkspace


DEFAULT_PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "prompts"


def workflow_status_document(
    workspace: ProjectWorkspace,
    *,
    prompts_root: str | Path = DEFAULT_PROMPTS_ROOT,
) -> dict[str, object]:
    """Describe effective readiness without changing project files."""

    outputs_present = {
        template: (workspace.vault_entity_directory / filename).exists()
        for template, filename in OUTPUT_FILES.items()
    }
    output_count = sum(outputs_present.values())
    dependency_state_exists = (
        workspace.project_root / "dependency-state.json"
    ).exists()
    stale = tuple(
        stale_research_pages(workspace, prompts_root=prompts_root)
    )
    if output_count < len(OUTPUT_FILES):
        research_inputs = "incomplete"
    elif not dependency_state_exists:
        research_inputs = "untracked_legacy"
    elif stale:
        research_inputs = "stale"
    else:
        research_inputs = "current"

    stages = workspace.document["stages"]
    source_count = len(_collected_source_pages(workspace))
    crawl_ready = bool(source_count) and stages["crawl"]["status"] in {
        "complete",
        "partial",
    }
    research_ready = (
        research_inputs == "current"
        and stages["research"]["status"] == "complete"
    )
    registry_ready = (
        research_ready
        and (workspace.registry_directory / "registry.json").exists()
        and stages["registry"]["status"] in {"complete", "partial"}
    )
    verification_status = str(
        workspace.document.get("verification_status", "not_requested")
    )
    verification_requested = verification_status not in {
        "not_requested",
        "unsupported",
    }
    plan_ready = (
        registry_ready
        and workspace.verification_page_path.exists()
        and stages["verification_plan"]["status"] == "complete"
    )
    links_ready = plan_ready and stages["obsidian_links"]["status"] in {
        "complete",
        "partial",
    }
    job_exists = (
        workspace.jobs_directory / "verification-plan.json"
    ).exists()
    evidence_ready = (
        plan_ready
        and job_exists
        and stages["evidence_collection"]["status"] in {
            "complete",
            "partial",
        }
    )
    evaluation_ready = (
        evidence_ready
        and stages["evidence_evaluation"]["status"] == "complete"
    )

    active_stages = ["crawl", "research", "registry"]
    ready = {
        "crawl": crawl_ready,
        "research": research_ready,
        "registry": registry_ready,
        "verification_plan": plan_ready,
        "obsidian_links": links_ready,
        "evidence_collection": evidence_ready,
        "evidence_evaluation": evaluation_ready,
    }
    if verification_requested:
        active_stages.extend(("verification_plan", "obsidian_links"))
        if job_exists:
            active_stages.extend(
                ("evidence_collection", "evidence_evaluation")
            )

    if not source_count:
        next_action = "Collect documentation or run Analyze Project."
    elif not research_ready:
        if research_inputs == "stale":
            next_action = "Refresh stale research with Analyze Project."
        elif research_inputs == "untracked_legacy":
            next_action = "Resume Analyze Project to adopt existing research."
        else:
            next_action = "Generate the complete research set."
    elif not registry_ready:
        next_action = "Generate registry and token data."
    elif verification_status == "not_requested":
        next_action = "Research ready; verification was not requested."
    elif verification_status == "unsupported":
        next_action = "Research ready; automated verification is unsupported."
    elif not plan_ready:
        next_action = "Generate the verification checklist."
    elif not job_exists:
        next_action = "Review the categorized manual verification tasks."
    elif not evidence_ready:
        next_action = "Collect scanner-ready blockchain evidence."
    elif pending_proposals(workspace):
        next_action = "Review and approve pending evidence assessments."
    elif stages["evidence_evaluation"]["status"] == "partial":
        next_action = (
            "Inspect partial evidence and categorized manual-review tasks."
        )
    elif not evaluation_ready:
        next_action = "Generate evidence assessment proposals."
    else:
        next_action = "Automated workflow complete; review any manual tasks."

    return {
        "research_inputs": research_inputs,
        "generated_research_pages": f"{output_count}/{len(OUTPUT_FILES)}",
        "stale_research_pages": list(stale) if dependency_state_exists else [],
        "ready_stage_names": [stage for stage in active_stages if ready[stage]],
        "required_stage_names": active_stages,
        "ready_stages": sum(bool(ready[stage]) for stage in active_stages),
        "required_stages": len(active_stages),
        "verification_summary": verification_status_label(workspace),
        "next_action": next_action,
    }


def verification_status_label(workspace: ProjectWorkspace) -> str:
    """Return a truthful verification summary without changing evidence."""

    status = str(workspace.document.get("verification_status", "unknown"))
    stages = workspace.document.get("stages", {})
    evaluation = (
        stages.get("evidence_evaluation", {}).get("status", "not_started")
        if isinstance(stages, dict)
        else "not_started"
    )
    collection = (
        stages.get("evidence_collection", {}).get("status", "not_started")
        if isinstance(stages, dict)
        else "not_started"
    )
    manual = 0
    pending = 0
    if workspace.verification_page_path.exists():
        text = workspace.verification_page_path.read_text(encoding="utf-8")
        manual = len(
            re.findall(r"(?mi)^\|\s*Check route\s*\|\s*Manual\s*\|", text)
        )
        if not manual:
            legacy = re.search(
                r"(?mi)^\|\s*Manual review\s*\|\s*(\d+)\s*\|",
                text,
            )
            manual = int(legacy.group(1)) if legacy else 0
        match = re.search(
            r"(?mi)^\|\s*Pending\s*\|\s*(\d+)\s*\|",
            text,
        )
        pending = int(match.group(1)) if match else 0

    if evaluation == "complete" and pending == 0:
        return "Completed - manual review remaining" if manual else "Completed"
    if pending:
        if collection in {"complete", "partial"}:
            return "Evidence collected - assessment pending"
        return "Verification pending"
    if manual and pending == 0 and collection == "not_started":
        return "Manual review required"
    if status == "manual_review":
        return "Manual review required"
    labels = {
        "not_requested": "Not requested",
        "unsupported": "Not supported automatically",
        "pending": "Verification pending",
        "evidence_collected": "Evidence collected - assessment pending",
        "supported": "Supported",
        "contradicted": "Contradicted",
        "inconclusive": "Inconclusive",
    }
    return labels.get(status, status.replace("_", " ").title())


def _collected_source_pages(workspace: ProjectWorkspace) -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted(workspace.sources_directory.rglob("*.md"))
        if path.name.casefold() != "_source_coverage.md"
    )
