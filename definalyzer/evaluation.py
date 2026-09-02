"""Human-approved evaluation proposals derived from collected evidence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .providers import TextProvider
from .verification_state import (
    evidence_job_fingerprint,
    verification_job_fingerprint,
)
from .workspace import ProjectWorkspace
from .verification_planning import write_verification_catalog


PROPOSAL_STATUSES = {
    "supported",
    "contradicted",
    "inconclusive",
    "manual_review",
}
ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")


@dataclass(frozen=True)
class EvaluationGenerationResult:
    proposals: tuple[Path, ...]
    reused: int
    unmatched_evidence: tuple[Path, ...]
    ignored_stale_evidence: tuple[Path, ...]


@dataclass(frozen=True)
class ReviewResult:
    proposal_id: str
    action: str
    verification_updated: bool
    decision_path: Path | None


def generate_evaluation_proposals(
    *,
    workspace: ProjectWorkspace,
    provider: TextProvider,
    progress: Callable[[str], None] | None = None,
) -> EvaluationGenerationResult:
    verification_page = _verification_page(workspace)
    claims = _parse_claims(verification_page.read_text(encoding="utf-8"))
    pending = workspace.project_root / "evaluations" / "pending"
    proposals: list[Path] = []
    unmatched: list[Path] = []
    ignored_stale: list[Path] = []
    reused = 0

    planned_job = workspace.jobs_directory / "verification-plan.json"
    current_fingerprint = (
        verification_job_fingerprint(planned_job)
        if planned_job.exists()
        else None
    )
    current_job_name = None
    if planned_job.exists():
        job_document = _read_json(planned_job)
        name = job_document.get("name")
        current_job_name = name if isinstance(name, str) else None

    for evidence_path in sorted(workspace.evidence_directory.glob("*.json")):
        if evidence_path.name.endswith("-import-report.json"):
            continue
        bundle = _read_json(evidence_path)
        bundle_fingerprint = evidence_job_fingerprint(bundle)
        bundle_metadata = bundle.get("job_metadata")
        imported_verification_job = (
            isinstance(bundle_metadata, dict)
            and bundle_metadata.get("created_by")
            == "verification-request-importer"
        )
        if current_fingerprint is None and (
            bundle_fingerprint is not None or imported_verification_job
        ):
            ignored_stale.append(evidence_path)
            if progress:
                progress(f"Ignored obsolete planned evidence: {evidence_path.name}")
            continue
        if current_fingerprint is not None:
            same_planned_name = bundle.get("job_name") == current_job_name
            if (
                bundle_fingerprint is not None
                and bundle_fingerprint != current_fingerprint
            ) or (same_planned_name and bundle_fingerprint is None):
                ignored_stale.append(evidence_path)
                if progress:
                    progress(f"Ignored stale planned evidence: {evidence_path.name}")
                continue
        matches = _match_claims(bundle, claims)
        if not matches:
            unmatched.append(evidence_path)
            continue
        for verification_id, claim, record in matches:
            proposal_id = _proposal_id(
                verification_id,
                evidence_path.stem,
                str(record.get("request_name", "request")),
            )
            path = pending / f"{proposal_id}.json"
            if path.exists():
                proposals.append(path)
                reused += 1
                continue
            if record.get("status") != "collected":
                evaluation = {
                    "proposed_status": "inconclusive",
                    "reason": (
                        "The collection was incomplete or failed, so it cannot "
                        "support a claim-level conclusion."
                    ),
                    "evidence_scope": "Incomplete collection record.",
                }
                provider_name = "deterministic"
            else:
                prompt = _evaluation_prompt(
                    verification_id=verification_id,
                    claim=claim,
                    record=record,
                    chain_snapshots=bundle.get("chain_snapshots", {}),
                )
                if progress:
                    progress(
                        f"Evaluating evidence proposal {proposal_id}"
                    )
                response = provider.generate(
                    prompt,
                    working_directory=workspace.project_root,
                )
                evaluation = _validate_evaluation(response.text)
                provider_name = response.provider
            proposal = {
                "schema_version": 1,
                "proposal_id": proposal_id,
                "project": workspace.name,
                "verification_id": verification_id,
                "claim": claim,
                **evaluation,
                "evidence_file": str(evidence_path),
                "evidence_summary_file": str(
                    evidence_path.with_suffix(".md")
                ),
                "request_name": record.get("request_name"),
                "collection_status": record.get("status"),
                "provider": provider_name,
                "generated_at": _timestamp(),
                "human_approval_required": True,
            }
            _write_json_new(path, proposal)
            proposals.append(path)
    return EvaluationGenerationResult(
        proposals=tuple(proposals),
        reused=reused,
        unmatched_evidence=tuple(unmatched),
        ignored_stale_evidence=tuple(ignored_stale),
    )


def pending_proposals(workspace: ProjectWorkspace) -> tuple[Path, ...]:
    pending = workspace.project_root / "evaluations" / "pending"
    decisions = workspace.project_root / "evaluations" / "decisions"
    decided = {
        path.stem for path in decisions.glob("*.json")
    } if decisions.exists() else set()
    return tuple(
        path
        for path in sorted(pending.glob("*.json"))
        if path.stem not in decided
    ) if pending.exists() else ()


def review_proposal(
    *,
    workspace: ProjectWorkspace,
    proposal_path: Path,
    action: str,
) -> ReviewResult:
    if action not in {"approve", "reject", "inconclusive", "leave"}:
        raise ValueError(f"Unsupported review action {action!r}.")
    proposal = _read_json(proposal_path)
    proposal_id = str(proposal.get("proposal_id", ""))
    if action == "leave":
        return ReviewResult(proposal_id, action, False, None)

    final_status = (
        proposal["proposed_status"] if action == "approve"
        else "inconclusive" if action == "inconclusive"
        else None
    )
    verification_updated = False
    if final_status is not None:
        page = _verification_page(workspace)
        _apply_verification_decision(
            page=page,
            verification_id=str(proposal["verification_id"]),
            status=str(final_status),
            result=str(proposal["reason"]),
            evidence_file=str(proposal["evidence_file"]),
        )
        write_verification_catalog(workspace)
        verification_updated = True

    decision_path = (
        workspace.project_root
        / "evaluations"
        / "decisions"
        / f"{proposal_id}.json"
    )
    _write_json_new(
        decision_path,
        {
            "schema_version": 1,
            "proposal_id": proposal_id,
            "action": action,
            "final_status": final_status,
            "reviewed_at": _timestamp(),
            "human_approved": action in {"approve", "inconclusive"},
        },
    )
    return ReviewResult(
        proposal_id,
        action,
        verification_updated,
        decision_path,
    )


def refresh_verification_summary(page: Path) -> None:
    text = page.read_text(encoding="utf-8")
    updated = _refresh_summary_counts(text)
    if updated == text:
        return
    temporary = page.with_suffix(page.suffix + ".tmp")
    temporary.write_text(updated, encoding="utf-8", newline="\n")
    temporary.replace(page)


def _parse_claims(text: str) -> dict[str, dict[str, Any]]:
    claims = {}
    pattern = re.compile(
        r"^### (?P<id>VR-[A-Z0-9-]+)\s+[—-].*?\n"
        r"(?P<body>.*?)(?=^### |^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(text):
        body = match.group("body")
        claim_match = re.search(r"^\| Claim \| (?P<claim>.*?) \|$", body, re.MULTILINE)
        target_match = re.search(
            r"^\| Registry target \| (?P<target>.*?) \|$",
            body,
            re.MULTILINE,
        )
        if claim_match:
            claims[match.group("id")] = {
                "claim": claim_match.group("claim").strip(),
                "addresses": {
                    value.casefold()
                    for value in ADDRESS_PATTERN.findall(
                        target_match.group("target") if target_match else ""
                    )
                },
            }
    return claims


def _match_claims(
    bundle: dict[str, Any],
    claims: dict[str, dict[str, Any]],
) -> list[tuple[str, str, dict[str, Any]]]:
    matches = []
    for record in bundle.get("records", []):
        if not isinstance(record, dict):
            continue
        request_name = record.get("request_name")
        if isinstance(request_name, str):
            direct_id = request_name.upper()
            direct_claim = claims.get(direct_id)
            if direct_claim is not None:
                matches.append(
                    (direct_id, direct_claim["claim"], record)
                )
                continue
        record_addresses = {
            value.casefold()
            for value in ADDRESS_PATTERN.findall(json.dumps(record))
        }
        for verification_id, claim in claims.items():
            if claim["addresses"] & record_addresses:
                matches.append(
                    (verification_id, claim["claim"], record)
                )
    return matches


def _evaluation_prompt(
    *,
    verification_id: str,
    claim: str,
    record: dict[str, Any],
    chain_snapshots: Any,
) -> str:
    compact_snapshots = {
        chain: {
            "block": snapshot.get("rpc", {}).get("result", {}).get("number"),
            "block_hash": snapshot.get("rpc", {}).get("result", {}).get("hash"),
        }
        for chain, snapshot in chain_snapshots.items()
        if isinstance(snapshot, dict)
    } if isinstance(chain_snapshots, dict) else {}
    return (
        "# Evidence Evaluation Proposal\n\n"
        "Evaluate only whether the supplied raw evidence addresses the exact "
        "claim. Do not use prior knowledge. Missing scope, missing calls, or "
        "partial evidence must be `inconclusive` or `manual_review`. A matching "
        "address alone does not support a behavioral or governance claim. "
        "Return strict JSON only with proposed_status, reason, and "
        "evidence_scope. proposed_status must be supported, contradicted, "
        "inconclusive, or manual_review. Keep reason to one sentence.\n\n"
        f"Verification ID: {verification_id}\n"
        f"Claim: {claim}\n"
        f"Chain context: {json.dumps(compact_snapshots)}\n"
        f"Evidence record:\n{json.dumps(record, separators=(',', ':'))}\n"
    )


def _validate_evaluation(text: str) -> dict[str, str]:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    document = json.loads(value)
    if not isinstance(document, dict):
        raise ValueError("Evaluation output must be a JSON object.")
    if set(document) != {"proposed_status", "reason", "evidence_scope"}:
        raise ValueError("Evaluation output has unexpected fields.")
    if document["proposed_status"] not in PROPOSAL_STATUSES:
        raise ValueError("Evaluation proposed_status is invalid.")
    for field in ("reason", "evidence_scope"):
        if not isinstance(document[field], str) or not document[field].strip():
            raise ValueError(f"Evaluation field {field!r} is invalid.")
    return {
        "proposed_status": document["proposed_status"],
        "reason": document["reason"].strip(),
        "evidence_scope": document["evidence_scope"].strip(),
    }


def _apply_verification_decision(
    *,
    page: Path,
    verification_id: str,
    status: str,
    result: str,
    evidence_file: str,
) -> None:
    text = page.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(^### {re.escape(verification_id)}\s+[—-].*?\n)"
        rf"(?P<body>.*?)(?=^### |^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"Verification entry {verification_id} was not found.")
    body = match.group("body")
    display_status = {
        "supported": "Confirmed",
    }.get(status, status.replace("_", " ").title())
    replacements = {
        "Status": display_status,
        "Evidence": f"`{evidence_file}`",
        "Last checked": _timestamp(),
        "Result": result,
    }
    for field, value in replacements.items():
        body, count = re.subn(
            rf"^\| {re.escape(field)} \| .*? \|$",
            lambda _: f"| {field} | {value} |",
            body,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ValueError(
                f"Verification entry is missing its {field!r} field."
            )
    updated = text[: match.start("body")] + body + text[match.end("body") :]
    updated = _refresh_summary_counts(updated)
    temporary = page.with_suffix(page.suffix + ".tmp")
    temporary.write_text(updated, encoding="utf-8", newline="\n")
    temporary.replace(page)


def _refresh_summary_counts(text: str) -> str:
    entry_statuses = re.findall(
        r"^\| Status \| (.*?) \|$",
        text,
        re.MULTILINE,
    )
    labels = (
        "Pending",
        "Evidence collected",
        "Confirmed",
        "Contradicted",
        "Inconclusive",
        "Public evidence unavailable",
    )
    for label in labels:
        count = sum(
            status.casefold() == label.casefold()
            for status in entry_statuses
        )
        text = re.sub(
            rf"^\| {re.escape(label)} \| \d+ \|$",
            f"| {label} | {count} |",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return text


def _verification_page(workspace: ProjectWorkspace) -> Path:
    path = workspace.verification_page_path
    if not path.exists():
        raise FileNotFoundError(f"Verification page does not exist: {path}")
    return path


def _proposal_id(verification_id: str, evidence: str, request: str) -> str:
    digest = hashlib.sha256(
        f"{verification_id}|{evidence}|{request}".encode("utf-8")
    ).hexdigest()[:10]
    return f"{verification_id.lower()}-{digest}"


def _read_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return document


def _write_json_new(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as file:
        json.dump(document, file, indent=2)
        file.write("\n")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
