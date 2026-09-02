"""Create a categorized, collector-compatible verification plan."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from blockchain_collector.verification_import import (
    ImportResult,
    import_verification_requests,
    load_verification_requests,
)

from .providers import TextProvider
from .obsidian_links import strip_generated_verification_links
from .workspace import ProjectWorkspace


MAX_PROMPT_CHARACTERS = 26_000
RESEARCH_EXCLUSIONS = {"Index.md", "Networks.md", "Registry.md"}
FENCE_PATTERN = re.compile(
    r"```definalyzer-verification[ \t]*\r?\n.*?\r?\n```",
    re.DOTALL,
)

# Reject collection limitations, not negative assertions about protocol behavior.
# This deliberately narrow guard complements (rather than replaces) the prompt.
DOCUMENTATION_GAP_PATTERN = re.compile(
    r"\b(?:is|are|was|were|remains?|has been|have been)\s+"
    r"(?:not\s+(?:documented|disclosed|specified|collected|provided)|undocumented)\b"
    r"|\b(?:documentation|source coverage|coverage)\s+(?:is|was|remains)\s+"
    r"(?:missing|partial|incomplete)\b",
    re.IGNORECASE,
)

CLAIM_SELECTION_RULES = (
    "Select assertions about the entity's behavior, economics, or controls, "
    "not the analyst's assessment of the documentation. Statements that "
    "information is missing, not documented, or coverage is partial are "
    "research gaps: leave them in the research notes, never promote them "
    "to verification claims. Do not invent an assertion to replace a gap. "
    "For conflicting statements, preserve both documented assertions and "
    "their sources; request clarification without declaring a contradiction. "
    "Organize ALL claims by subject (economics, governance, etc.), independently "
    "of Automated/Assisted/Manual route. Manual Review is a route, not a "
    "subject category or a shared two-claim quota. Unsupported scanner chains "
    "still qualify for material claims with a Manual route. "
)


@dataclass(frozen=True)
class VerificationPlanResult:
    page_path: Path
    job_path: Path | None
    report_path: Path
    catalog_path: Path
    provider_calls: int
    reused_calls: int
    ready_requests: int
    manual_claims: int


def generate_verification_plan(
    *,
    workspace: ProjectWorkspace,
    provider: TextProvider,
    prompts_root: str | Path,
    progress: Callable[[str], None] | None = None,
) -> VerificationPlanResult:
    registry_path = workspace.registry_directory / "registry.json"
    if not registry_path.exists():
        raise FileNotFoundError(
            "Registry generation must complete before verification planning."
        )
    research_pages = tuple(
        path
        for path in sorted(workspace.vault_entity_directory.glob("*.md"))
        if path.name not in RESEARCH_EXCLUSIONS
    )
    if not research_pages:
        raise ValueError("No research pages are available for verification planning.")

    template = (
        Path(prompts_root) / "templates" / "template_verification_page.md"
    ).read_text(encoding="utf-8")
    registry = _compact_registry(registry_path)
    state_directory = workspace.project_root / "verification-planning"
    state_directory.mkdir(parents=True, exist_ok=True)

    bundles = _bundle_research_pages(research_pages)
    candidates: list[str] = []
    provider_calls = 0
    reused_calls = 0
    for index, bundle in enumerate(bundles, start=1):
        prompt = _candidate_prompt(bundle)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        ledger = state_directory / f"candidates-{index:04d}.json"
        cached = _read_ledger(ledger, digest)
        if cached is not None:
            candidates.append(_sanitize_candidates(cached, bundle))
            reused_calls += 1
            if progress:
                progress(f"Reused verification candidate batch {index}/{len(bundles)}")
            continue
        if progress:
            progress(f"Selecting verification candidates {index}/{len(bundles)}")
        response = provider.generate(
            prompt,
            working_directory=workspace.project_root,
        )
        candidate_document = _validate_candidate_response(response.text)
        normalized = json.dumps(candidate_document, indent=2).rstrip() + "\n"
        _write_ledger(ledger, digest, normalized)
        candidates.append(_sanitize_candidates(normalized, bundle))
        provider_calls += 1

    final_prompt = _final_prompt(
        entity=workspace.name,
        template=template,
        registry=registry,
        candidates=candidates,
    )
    if len(final_prompt) > MAX_PROMPT_CHARACTERS:
        reduction_prompt = _candidate_reduction_prompt(candidates)
        reduction_digest = hashlib.sha256(
            reduction_prompt.encode("utf-8")
        ).hexdigest()
        reduction_ledger = state_directory / "candidates-consolidated.json"
        reduced = _read_ledger(reduction_ledger, reduction_digest)
        if reduced is None:
            if progress:
                progress("Consolidating verification candidates")
            response = provider.generate(
                reduction_prompt,
                working_directory=workspace.project_root,
            )
            reduced_document = _validate_candidate_response(
                response.text,
                maximum_candidates=10,
            )
            reduced = json.dumps(reduced_document, indent=2).rstrip() + "\n"
            _write_ledger(reduction_ledger, reduction_digest, reduced)
            provider_calls += 1
        else:
            reused_calls += 1
        candidates = [json.dumps(_validate_candidate_response(
            reduced, maximum_candidates=10,
        ))]
        final_prompt = _final_prompt(
            entity=workspace.name,
            template=template,
            registry=registry,
            candidates=candidates,
        )
    if len(final_prompt) > MAX_PROMPT_CHARACTERS:
        raise ValueError(
            "Verification candidate consolidation exceeds the provider prompt "
            "limit; reduce candidate output before retrying."
        )
    final_digest = hashlib.sha256(final_prompt.encode("utf-8")).hexdigest()
    final_ledger = state_directory / "final.md"
    page = _read_ledger(final_ledger, final_digest)
    if page is None:
        if progress:
            progress("Creating categorized verification page")
        response = provider.generate(
            final_prompt,
            working_directory=workspace.project_root,
        )
        page = _validate_page(response.text, workspace.name, require_subject_categories=True)
        _write_ledger(final_ledger, final_digest, page)
        provider_calls += 1
    else:
        reused_calls += 1
        page = _validate_page(page, workspace.name, require_subject_categories=True)
    page = _strip_verification_planning_preamble(
        _normalize_collector_request_aliases(
        _normalize_research_links(
            _repair_mojibake(page),
            entity=workspace.name,
            entity_type=str(workspace.document["entity_type"]),
            research_pages=research_pages,
        ),
        job_name=f"{workspace.slug}-verification",
        ),
        entity=workspace.name,
    )
    page = _normalize_verification_self_links(page, workspace.name)
    page = _normalize_route_statuses(page)

    page_path = workspace.verification_page_path
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_with_frontmatter = (
        "---\n"
        'generated_by: "definalyzer_verification_planner"\n'
        f'entity: "{workspace.name}"\n'
        'verification_status: "pending"\n'
        f'generated_at: "{_timestamp()}"\n'
        "---\n\n"
        f"{page.strip()}\n"
    )
    _write_generated_page(page_path, page_with_frontmatter)

    catalog_path = state_directory / "verification-catalog.json"
    _write_json(
        catalog_path,
        _verification_catalog(page, entity=workspace.name),
    )

    request_document = load_verification_requests(page_path)
    import_result = _import_or_empty(
        request_document,
        source=str(page_path),
    )
    report_path = state_directory / "import-report.json"
    _write_json(report_path, import_result.report)
    job_path: Path | None = None
    planned_job_path = workspace.jobs_directory / "verification-plan.json"
    if import_result.job_document is not None:
        job_path = planned_job_path
        _write_json(job_path, import_result.job_document)
    elif planned_job_path.exists():
        planned_job_path.unlink()

    return VerificationPlanResult(
        page_path=page_path,
        job_path=job_path,
        report_path=report_path,
        catalog_path=catalog_path,
        provider_calls=provider_calls,
        reused_calls=reused_calls,
        ready_requests=import_result.report["ready_count"],
        manual_claims=_manual_claim_count(page),
    )


def _manual_claim_count(page: str) -> int:
    return len(
        re.findall(r"(?mi)^\| Check route \| Manual \|$", page)
    )


def _normalize_route_statuses(page: str) -> str:
    """Migrate legacy result labels without conflating route and status."""
    entry_pattern = re.compile(
        r"(?ms)(^### VR-[A-Z0-9-]+\s+[—-].*?\n)"
        r"(?P<body>.*?)(?=^### |^## |\Z)"
    )

    def normalize_entry(match: re.Match[str]) -> str:
        body = match.group("body")
        status = re.search(r"(?m)^\| Status \| (.*?) \|$", body)
        if status is None:
            return match.group(0)
        current = status.group(1).strip()
        expected = {
            "manual review": "Pending",
            "supported": "Confirmed",
        }.get(current.casefold(), current)
        body = (
            body[: status.start(1)]
            + expected
            + body[status.end(1) :]
        )
        return match.group(1) + body

    page = entry_pattern.sub(normalize_entry, page)
    statuses = re.findall(r"(?m)^\| Status \| (.*?) \|$", page)
    labels = (
        "Pending",
        "Evidence collected",
        "Confirmed",
        "Contradicted",
        "Inconclusive",
        "Public evidence unavailable",
    )
    summary = "| Status | Count |\n|---|---:|\n" + "\n".join(
        f"| {label} | "
        f"{sum(value.casefold() == label.casefold() for value in statuses)} |"
        for label in labels
    )
    page = re.sub(
        r"(?ms)^## Summary\s*\n\n.*?(?=^##(?:#)? |\Z)",
        "## Summary\n\n" + summary + "\n\n",
        page,
        count=1,
    )
    return page


def _verification_catalog(page: str, *, entity: str) -> dict[str, Any]:
    """Return a structured index of every check, including legacy entries."""
    entries: list[dict[str, Any]] = []
    pattern = re.compile(
        r"(?ms)^### (?P<id>VR-[A-Z0-9-]+)\s+[—-]\s+"
        r"(?P<title>.*?)\n(?P<body>.*?)(?=^### |^## |\Z)"
    )
    for match in pattern.finditer(page):
        headings = re.findall(r"(?m)^## ([^\r\n]+)$", page[: match.start()])
        category = headings[-1] if headings else "Uncategorized"
        fields = {
            key.strip(): value.strip()
            for key, value in re.findall(
                r"(?m)^\| ([^|]+?) \| (.*?) \|$",
                match.group("body"),
            )
            if key.strip() != "Field"
        }
        route = fields.get("Check route", "Manual")
        entries.append(
            {
                "id": match.group("id"),
                "title": match.group("title").strip(),
                "category": category,
                "claim": fields.get("Claim", ""),
                "claim_type": fields.get(
                    "Claim type", _legacy_claim_type(category)
                ),
                "evidence_availability": fields.get(
                    "Evidence availability", "Unknown"
                ),
                "recommended_method": fields.get(
                    "Recommended method",
                    "Direct RPC"
                    if route.casefold() == "automated"
                    else "Analyst review",
                ),
                "dune_eligible": (
                    fields.get("Recommended method", "").casefold()
                    == "dune candidate"
                    and fields.get("Evidence availability", "Unknown").casefold()
                    == "public"
                ),
                "check_route": route,
                "status": {
                    "manual review": "Pending",
                    "supported": "Confirmed",
                }.get(
                    fields.get("Status", "Pending").casefold(),
                    fields.get("Status", "Pending"),
                ),
                "research_source": fields.get("Research source", ""),
                "registry_target": fields.get("Registry target", ""),
                "materiality": fields.get("Materiality", ""),
                "how_to_check": fields.get("How to check", ""),
                "likely_source": fields.get("Likely source", ""),
                "evidence_required": fields.get("Evidence required", ""),
            }
        )
    return {
        "schema_version": 1,
        "entity": entity,
        "entries": entries,
        "interpretation_performed": False,
    }


def write_verification_catalog(workspace: ProjectWorkspace) -> Path:
    """Refresh the structured dashboard index from the canonical Markdown page."""
    if not workspace.verification_page_path.exists():
        raise FileNotFoundError(
            f"Verification page does not exist: {workspace.verification_page_path}"
        )
    path = workspace.project_root / "verification-planning" / "verification-catalog.json"
    _write_json(
        path,
        _verification_catalog(
            workspace.verification_page_path.read_text(encoding="utf-8"),
            entity=workspace.name,
        ),
    )
    return path


def _legacy_claim_type(category: str) -> str:
    value = category.casefold()
    if "governance" in value:
        return "Governance"
    if "upgrade" in value or "ownership" in value:
        return "Smart contract/code"
    if "competitive" in value:
        return "Market/external data"
    if "configuration" in value or "oracle" in value or "cross-chain" in value:
        return "Smart contract/code"
    if "token" in value or "fee" in value or "treasury" in value:
        return "On-chain state/events"
    return "Unknown"


def _bundle_research_pages(paths: tuple[Path, ...]) -> tuple[str, ...]:
    overhead = len(_candidate_prompt(""))
    maximum = MAX_PROMPT_CHARACTERS - overhead - 500
    bundles: list[str] = []
    current: list[str] = []
    current_size = 0
    for path in paths:
        text = strip_generated_verification_links(
            path.read_text(encoding="utf-8")
        )
        sections = _page_sections(path.name, text, maximum)
        for section in sections:
            if current and current_size + len(section) > maximum:
                bundles.append("".join(current))
                current, current_size = [], 0
            current.append(section)
            current_size += len(section)
    if current:
        bundles.append("".join(current))
    return tuple(bundles)


def _page_sections(name: str, text: str, maximum: int) -> tuple[str, ...]:
    """Split an oversized note at paragraph boundaries without dropping text."""
    prefix = f"\n\n## SOURCE NOTE: {name}\n\n"
    available = maximum - len(prefix) - 80
    paragraphs = re.split(r"(\n\s*\n)", text.strip())
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > available:
            pieces = [
                paragraph[start : start + available]
                for start in range(0, len(paragraph), available)
            ]
        else:
            pieces = [paragraph]
        for piece in pieces:
            if current and len(current) + len(piece) > available:
                chunks.append(current)
                current = ""
            current += piece
    if current:
        chunks.append(current)
    return tuple(
        f"{prefix}Part {index}/{len(chunks)}\n\n{chunk.strip()}\n"
        for index, chunk in enumerate(chunks, start=1)
    )


def _compact_registry(path: Path) -> str:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Registry must be a JSON object.")
    compact: dict[str, Any] = {
        key: document[key]
        for key in ("entity", "entity_type", "scope")
        if key in document
    }
    tokens = document.get("tokens")
    if isinstance(tokens, list):
        compact["tokens"] = [
            {
                key: row[key]
                for key in (
                    "name",
                    "symbol",
                    "token_type",
                    "network",
                    "standard",
                    "address",
                    "source",
                )
                if key in row
            }
            for row in tokens
            if isinstance(row, dict)
        ]
    networks = document.get("networks")
    if isinstance(networks, list):
        compact["network_count"] = len(networks)
    # Preserve future normalized address inventories when present.
    addresses = document.get("addresses")
    if isinstance(addresses, list):
        eligible = [
            row
            for row in addresses
            if isinstance(row, dict)
            and row.get("provenance") in {"official_registry", "documented"}
            and row.get("status") not in {
                "conflicting",
                "documented_unresolved",
            }
        ]
        source_values = sorted(
            {
                str(row.get("source"))
                for row in eligible
                if row.get("source")
            }
        )
        source_ids = {
            source: f"S{index}"
            for index, source in enumerate(source_values, start=1)
        }
        compact["address_sources"] = {
            identifier: source for source, identifier in source_ids.items()
        }
        compact["addresses"] = [
            {
                **{
                    key: row[key]
                    for key in (
                        "name",
                    "address",
                    "chain",
                    "chain_id",
                )
                    if key in row
                },
                "source_ref": source_ids.get(str(row.get("source"))),
            }
            for row in eligible
        ]
        compact["unresolved_address_count"] = len(addresses) - len(eligible)
    for key in ("address_inventory", "contracts"):
        if key in document:
            compact[key] = document[key]
    return json.dumps(compact, separators=(",", ":"))


def _candidate_prompt(source_bundle: str) -> str:
    return (
        "# Material Verification Candidate Selection\n\n"
        "Use only the supplied research notes. Select at most 4 claims whose "
        "accuracy could materially change an investment, security, economic, "
        "governance, solvency, or operational assessment. Do not verify or "
        "judge claims. Exclude routine facts, component lists, addresses, and "
        "low-impact settings. A candidate may be manual when onchain evidence "
        "cannot answer it.\n\n"
        + CLAIM_SELECTION_RULES + "\n\n"
        "Return strict JSON only:\n"
        '{"candidates":[{"claim":"","materiality":"","category":"",'
        '"research_note":"","claim_location":"","evidence_needed":""}]}\n\n'
        "Keep every field concise. Return an empty candidates list when the "
        "notes contain no material claim.\n\n"
        f"{source_bundle}"
    )


def _candidate_reduction_prompt(candidates: list[str]) -> str:
    return (
        "# Verification Candidate Reduction\n\n"
        "Deduplicate the supplied candidate batches. Retain at most 10 claims "
        "whose accuracy is most likely to materially change an investment, "
        "security, governance, solvency, economic, or operational assessment. "
        "Keep at most 2 claims per subject category. Preserve exact research_note "
        "filenames and concise claim_location values. Do not evaluate claims "
        "or add facts. Return strict JSON only using the same candidates "
        "schema.\n\n"
        + CLAIM_SELECTION_RULES + "\n\n"
        + "\n\n".join(candidates)
    )


def _normalize_collector_request_aliases(
    page: str,
    *,
    job_name: str | None = None,
) -> str:
    """Repair known schema aliases without changing request meaning."""
    match = re.search(
        r"```definalyzer-verification\s*\n(?P<body>.*?)\n```",
        page,
        re.DOTALL,
    )
    if match is None:
        return page
    document = _parse_json(match.group("body"))
    changed = False
    if job_name is not None and document.get("name") != job_name:
        document["name"] = job_name
        changed = True
    requests = document.get("requests")
    if not isinstance(requests, list):
        return page
    for request in requests:
        if not isinstance(request, dict):
            continue
        if request.get("operation") != "standard_call":
            continue
        parameters = request.get("parameters")
        if not isinstance(parameters, dict):
            continue
        if "function" not in parameters and isinstance(
            parameters.get("method"),
            str,
        ):
            parameters["function"] = parameters.pop("method")
            changed = True
    if not changed:
        return page
    replacement = json.dumps(document, indent=2)
    return page[: match.start("body")] + replacement + page[match.end("body") :]


def _strip_verification_planning_preamble(page: str, *, entity: str) -> str:
    heading = re.search(
        rf"(?m)^# {re.escape(entity)}\s+[—-]\s+Verification\s*$",
        page,
    )
    if heading is None:
        return page
    return page[heading.start() :].strip()


def _final_prompt(
    *,
    entity: str,
    template: str,
    registry: str,
    candidates: list[str],
) -> str:
    candidate_text = "\n\n".join(
        f"## Candidate Batch {index}\n{_compact_candidate_json(value)}"
        for index, value in enumerate(candidates, start=1)
    )
    return (
        "# Verification Plan Consolidation\n\n"
        f"Create the verification page for {entity}. Follow the template "
        "exactly. Select at most 10 total claims and at most 2 per subject category. "
        "Deduplicate overlapping claims and retain only the claims most likely "
        "to change an investment decision. Use only exact addresses and "
        "provenance present in the registry. "
        "Create collector requests only when every required parameter is "
        "available without guessing. A collector request may gather material "
        "partial evidence even when it cannot resolve a broader issue; narrow "
        "that automated claim to exactly what the request observes and keep "
        "unobservable governance, timelock, or behavioral conclusions as a "
        "separate entry with a Manual check route. Never imply partial evidence is a "
        "verdict. Route all other material claims to analyst review and give "
        "them a short actionable procedure plus likely official sources. "
        "For every entry, independently classify Claim type, Evidence "
        "availability, Recommended method, Check route, and Status. New "
        "entries always use Pending status, including Manual routes. Never "
        "label evidence unavailable merely because it was not documented. "
        "Mark Dune candidate only for public indexed on-chain history or "
        "aggregate queries, and include Optional Dune query = Available only "
        "for those entries. Dune remains optional and is never executed here. "
        "Treat the page as an analyst checklist, not a promise that every "
        "claim can be automated. Use "
        "table-safe Obsidian aliases (`\\|`) inside tables. Return "
        "only the completed Markdown page with exactly one "
        "definalyzer-verification JSON fence. The JSON requests list may be "
        "empty. Research Note values are exact filenames; link only those note "
        "names and never turn claim text into a wiki link. Do not include "
        "verdicts or expected values.\n\n"
        + CLAIM_SELECTION_RULES + "\n\n"
        "## TEMPLATE\n\n"
        f"{template.strip()}\n\n"
        "## REGISTRY\n\n"
        f"{registry.strip()}\n\n"
        "## MATERIAL CANDIDATES\n\n"
        f"{candidate_text}\n"
    )


def _compact_candidate_json(value: str) -> str:
    """Remove JSON formatting overhead without dropping candidate evidence."""
    return json.dumps(_parse_json(value), separators=(",", ":"))


def _validate_candidate_response(
    text: str,
    *,
    maximum_candidates: int = 4,
) -> dict[str, Any]:
    document = _parse_json(text)
    rows = document.get("candidates")
    if not isinstance(rows, list) or len(rows) > maximum_candidates:
        raise ValueError(
            "Candidate response must contain at most "
            f"{maximum_candidates} candidates."
        )
    required = (
        "claim",
        "materiality",
        "category",
        "research_note",
        "claim_location",
        "evidence_needed",
    )
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each verification candidate must be an object.")
        for field in required:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Candidate field {field!r} must be non-empty.")
    return {"candidates": [
        row for row in rows if not DOCUMENTATION_GAP_PATTERN.search(row["claim"])
    ]}


def _validate_page(text: str, entity: str, *, require_subject_categories: bool = False) -> str:
    value = _repair_mojibake(text.strip())
    if value.startswith("```markdown"):
        value = re.sub(r"^```markdown\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    if f"# {entity}" not in value or "Verification" not in value:
        raise ValueError("Verification page has the wrong entity heading.")
    if require_subject_categories and re.search(r"(?mi)^## Manual Review\s*$", value):
        raise ValueError(
            "Group verification claims by subject; Manual belongs in Check route, "
            "not in a shared Manual Review category."
        )
    if value.count("```definalyzer-verification") != 1:
        raise ValueError(
            "Verification page must contain exactly one collector JSON block."
        )
    match = FENCE_PATTERN.search(value)
    if match is None:
        raise ValueError("Verification page collector JSON block is malformed.")
    payload = re.search(
        r"```definalyzer-verification\s*\n(?P<body>.*?)\n```",
        match.group(0),
        re.DOTALL,
    )
    if payload is None:
        raise ValueError("Verification page collector JSON block is malformed.")
    document = _parse_json(payload.group("body"))
    if document.get("schema_version") != 1:
        raise ValueError("Verification request schema_version must be 1.")
    if not isinstance(document.get("name"), str):
        raise ValueError("Verification request name is required.")
    if not isinstance(document.get("requests"), list):
        raise ValueError("Verification requests must be a list.")
    entry_pattern = re.compile(
        r"^### VR-[A-Z0-9-]+\s+[—-].*?\n"
        r"(?P<body>.*?)(?=^### |^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for entry in entry_pattern.finditer(value):
        body = entry.group("body")
        claim = re.search(r"^\| Claim \| (.*?) \|$", body, re.MULTILINE)
        if claim and DOCUMENTATION_GAP_PATTERN.search(claim.group(1)):
            raise ValueError(
                "A documentation gap is not a verification claim; keep it "
                "under Material Unknowns in the research notes."
            )
        for field in (
            "Claim type",
            "Evidence availability",
            "Recommended method",
            "Check route",
            "How to check",
            "Likely source",
        ):
            if not re.search(
                rf"^\| {re.escape(field)} \| .+ \|$",
                body,
                re.MULTILINE,
            ):
                raise ValueError(
                    f"Verification entry is missing its {field!r} field."
                )
        route = re.search(
            r"^\| Check route \| (?P<route>.*?) \|$",
            body,
            re.MULTILINE,
        )
        if route and route.group("route").casefold() not in {
            "automated",
            "assisted",
            "manual",
        }:
            raise ValueError("Verification Check route is invalid.")
        _validate_taxonomy_field(
            body,
            "Status",
            {
                "pending",
                "evidence collected",
                "confirmed",
                "contradicted",
                "inconclusive",
                "public evidence unavailable",
                # Accepted only for safe migration of cached legacy output.
                "manual review",
                "supported",
            },
        )
        _validate_taxonomy_field(
            body,
            "Claim type",
            {
                "on-chain state/events",
                "smart contract/code",
                "governance",
                "legal/regulatory",
                "organizational/private",
                "off-chain operational",
                "market/external data",
            },
        )
        method = re.search(
            r"^\| Recommended method \| (?P<value>.*?) \|$",
            body,
            re.MULTILINE,
        )
        availability = re.search(
            r"^\| Evidence availability \| (?P<value>.*?) \|$",
            body,
            re.MULTILINE,
        )
        dune_row = re.search(
            r"^\| Optional Dune query \| (?P<value>.*?) \|$",
            body,
            re.MULTILINE,
        )
        is_dune = bool(
            method and method.group("value").strip().casefold() == "dune candidate"
        )
        if is_dune and (
            availability is None
            or availability.group("value").strip().casefold() != "public"
        ):
            raise ValueError("Dune candidates must use public evidence.")
        if is_dune and (
            dune_row is None
            or dune_row.group("value").strip().casefold() != "available"
        ):
            raise ValueError("Dune candidates must show the optional Dune query row.")
        if not is_dune and dune_row is not None:
            raise ValueError("Optional Dune query is only valid for Dune candidates.")
        _validate_taxonomy_field(
            body,
            "Evidence availability",
            {"public", "restricted/private", "not documented", "unknown"},
        )
        _validate_taxonomy_field(
            body,
            "Recommended method",
            {
                "direct rpc",
                "dune candidate",
                "official source",
                "external database",
                "analyst review",
                "public evidence unavailable",
            },
        )
    return value


def _validate_taxonomy_field(
    body: str,
    field: str,
    allowed: set[str],
) -> None:
    match = re.search(
        rf"^\| {re.escape(field)} \| (?P<value>.*?) \|$",
        body,
        re.MULTILINE,
    )
    if match is None or match.group("value").strip().casefold() not in allowed:
        raise ValueError(f"Verification {field} is invalid.")


def _sanitize_candidates(text: str, source_bundle: str) -> str:
    document = _validate_candidate_response(text)
    rows = document.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("Candidate ledger is missing its candidates list.")
    sections = {
        match.group("name"): match.group("body")
        for match in re.finditer(
            r"## SOURCE NOTE: (?P<name>[^\r\n]+)\r?\n\r?\n"
            r"(?P<body>.*?)(?=\r?\n\r?\n## SOURCE NOTE: |\Z)",
            source_bundle,
            re.DOTALL,
        )
    }
    if not sections:
        raise ValueError("Verification source bundle has no named notes.")
    for row in rows:
        if not isinstance(row, dict):
            continue
        documented = str(row.get("research_note", "")).strip()
        exact = next(
            (
                name
                for name in sections
                if documented.lower() in {name.lower(), Path(name).stem.lower()}
            ),
            None,
        )
        if exact is None:
            terms = set(
                re.findall(
                    r"[a-z0-9]{4,}",
                    (
                        str(row.get("claim", ""))
                        + " "
                        + str(row.get("claim_location", ""))
                    ).lower(),
                )
            )
            exact = max(
                sections,
                key=lambda name: len(
                    terms
                    & set(re.findall(r"[a-z0-9]{4,}", sections[name].lower()))
                ),
            )
        row["research_note"] = exact
    return json.dumps(
        {"candidates": rows},
        separators=(",", ":"),
    ) + "\n"


def _repair_mojibake(text: str) -> str:
    replacements = {
        "â€”": "—",
        "â€“": "–",
        "â€™": "’",
        "â€œ": "“",
        "â€": "”",
        "Â": "",
    }
    for broken, repaired in replacements.items():
        text = text.replace(broken, repaired)
    return text


def _normalize_research_links(
    text: str,
    *,
    entity: str,
    entity_type: str = "protocol",
    research_pages: tuple[Path, ...],
) -> str:
    aliases = {
        name.lower(): (path.stem, path.stem)
        for path in research_pages
        for name in (path.name, path.stem)
    }
    output = []
    entity_folder = {
        "protocol": "Protocols",
        "chain": "Chains",
        "token": "Tokens",
    }.get(entity_type, "Protocols")
    pattern = re.compile(r"\[\[(?P<target>[^|\]\\]+)(?:\\?\|[^\]]+)?\]\]")
    for line in text.splitlines():
        in_table = line.strip().startswith("|") and line.strip().endswith("|")

        def replace(match: re.Match[str]) -> str:
            target = match.group("target").strip()
            base, marker, anchor = target.partition("#")
            match_value = aliases.get(base.lower())
            if match_value is None:
                return match.group(0)
            stem, alias = match_value
            separator = "\\|" if in_table else "|"
            suffix = f"#{anchor}" if marker else ""
            return (
                f"[[{entity_folder}/{entity}/{stem}{suffix}{separator}{alias}]]"
            )

        output.append(pattern.sub(replace, line))
    return "\n".join(output).rstrip() + "\n"


def _normalize_verification_self_links(text: str, entity: str) -> str:
    canonical = f"Verification/{entity}/Index#"
    patterns = (
        f"[[{entity} - Verification#",
        f"[[Verification/{entity} - Verification#",
    )
    for pattern in patterns:
        text = text.replace(pattern, f"[[{canonical}")
    return text


def _import_or_empty(
    document: dict[str, Any],
    *,
    source: str,
) -> ImportResult:
    rows = document.get("requests")
    if rows == []:
        report = {
            "import_schema_version": 1,
            "source": source,
            "source_name": document.get("name"),
            "job_name": None,
            "status": "manual_review",
            "ready_count": 0,
            "manual_review_count": 0,
            "requests": [],
            "interpretation_performed": False,
        }
        return ImportResult(job_document=None, report=report)
    return import_verification_requests(document, source=source)


def _parse_json(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    try:
        document = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Provider returned invalid JSON: {exc.msg}") from exc
    if not isinstance(document, dict):
        raise ValueError("Provider JSON output must be an object.")
    return document


def _read_ledger(path: Path, digest: str) -> str | None:
    metadata = path.with_suffix(path.suffix + ".state.json")
    if not path.exists() or not metadata.exists():
        return None
    state = json.loads(metadata.read_text(encoding="utf-8"))
    if state.get("digest") != digest:
        return None
    return path.read_text(encoding="utf-8")


def _write_ledger(path: Path, digest: str, text: str) -> None:
    _write_text(path, text.rstrip() + "\n")
    _write_json(
        path.with_suffix(path.suffix + ".state.json"),
        {"schema_version": 1, "digest": digest},
    )


def _write_generated_page(path: Path, text: str) -> None:
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if 'generated_by: "definalyzer_verification_planner"' not in existing:
            raise FileExistsError(f"Refusing to overwrite a user-owned page: {path}")
    _write_text(path, text)


def _write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(document, file, indent=2)
        file.write("\n")
    temporary.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
