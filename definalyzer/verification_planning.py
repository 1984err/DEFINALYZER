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


@dataclass(frozen=True)
class VerificationPlanResult:
    page_path: Path
    job_path: Path | None
    report_path: Path
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
        candidates = [reduced]
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
        page = _validate_page(response.text, workspace.name)
        _write_ledger(final_ledger, final_digest, page)
        provider_calls += 1
    else:
        reused_calls += 1
    page = _strip_verification_planning_preamble(
        _normalize_collector_request_aliases(
        _normalize_research_links(
            _repair_mojibake(page),
            entity=workspace.name,
            research_pages=research_pages,
        )
        ),
        entity=workspace.name,
    )

    page_path = (
        workspace.vault_root
        / "Verification"
        / f"{workspace.name} - Verification.md"
    )
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
        provider_calls=provider_calls,
        reused_calls=reused_calls,
        ready_requests=import_result.report["ready_count"],
        manual_claims=len(
            re.findall(r"\| Status \| Manual review \|", page)
        ),
    )


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
        section = f"\n\n## SOURCE NOTE: {path.name}\n\n{text.strip()}\n"
        if len(section) > maximum:
            raise ValueError(
                f"Research page is too large for verification planning: {path.name}"
            )
        if current and current_size + len(section) > maximum:
            bundles.append("".join(current))
            current, current_size = [], 0
        current.append(section)
        current_size += len(section)
    if current:
        bundles.append("".join(current))
    return tuple(bundles)


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
        "Keep at most 2 claims per category. Preserve exact research_note "
        "filenames and concise claim_location values. Do not evaluate claims "
        "or add facts. Return strict JSON only using the same candidates "
        "schema.\n\n"
        + "\n\n".join(candidates)
    )


def _normalize_collector_request_aliases(page: str) -> str:
    """Repair known schema aliases without changing request meaning."""
    match = re.search(
        r"```definalyzer-verification\s*\n(?P<body>.*?)\n```",
        page,
        re.DOTALL,
    )
    if match is None:
        return page
    document = _parse_json(match.group("body"))
    requests = document.get("requests")
    if not isinstance(requests, list):
        return page
    changed = False
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
        f"## Candidate Batch {index}\n{value}"
        for index, value in enumerate(candidates, start=1)
    )
    return (
        "# Verification Plan Consolidation\n\n"
        f"Create the verification page for {entity}. Follow the template "
        "exactly. Select at most 10 total claims and at most 2 per category. "
        "Deduplicate overlapping claims and retain only the claims most likely "
        "to change an investment decision. Use only exact addresses and "
        "provenance present in the registry. "
        "Create collector requests only when every required parameter is "
        "available without guessing. A collector request may gather material "
        "partial evidence even when it cannot resolve a broader issue; narrow "
        "that automated claim to exactly what the request observes and keep "
        "unobservable governance, timelock, or behavioral conclusions as a "
        "separate Manual Review entry. Never imply partial evidence is a "
        "verdict. Route all other material claims to Manual Review and give "
        "them a short actionable procedure plus likely official sources. "
        "Treat the page as an analyst checklist, not a promise that every "
        "claim can be automated. Use "
        "table-safe Obsidian aliases (`\\|`) inside tables. Return "
        "only the completed Markdown page with exactly one "
        "definalyzer-verification JSON fence. The JSON requests list may be "
        "empty. Research Note values are exact filenames; link only those note "
        "names and never turn claim text into a wiki link. Do not include "
        "verdicts or expected values.\n\n"
        "## TEMPLATE\n\n"
        f"{template.strip()}\n\n"
        "## REGISTRY\n\n"
        f"{registry.strip()}\n\n"
        "## MATERIAL CANDIDATES\n\n"
        f"{candidate_text}\n"
    )


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
    return {"candidates": rows}


def _validate_page(text: str, entity: str) -> str:
    value = _repair_mojibake(text.strip())
    if value.startswith("```markdown"):
        value = re.sub(r"^```markdown\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    if f"# {entity}" not in value or "Verification" not in value:
        raise ValueError("Verification page has the wrong entity heading.")
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
        for field in ("Check route", "How to check", "Likely source"):
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
    return value


def _sanitize_candidates(text: str, source_bundle: str) -> str:
    document = _parse_json(text)
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
    research_pages: tuple[Path, ...],
) -> str:
    aliases = {
        name.lower(): (path.stem, path.stem)
        for path in research_pages
        for name in (path.name, path.stem)
    }
    output = []
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
                f"[[Protocols/{entity}/{stem}{suffix}{separator}{alias}]]"
            )

        output.append(pattern.sub(replace, line))
    return "\n".join(output).rstrip() + "\n"


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
