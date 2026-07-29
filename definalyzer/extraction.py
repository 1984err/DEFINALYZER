"""Controlled research extraction using a provider-neutral text interface."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .providers import TextProvider
from .workspace import ProjectWorkspace


MAX_SINGLE_PASS_SOURCE_CHARACTERS = 300_000
MAX_PROVIDER_PROMPT_CHARACTERS = 26_000
EXTRACTION_STATE_VERSION = 1
TEMPLATE_FILES = {
    "protocol-overview": "template_protocol_overview.md",
    "architecture": "template_architecture.md",
    "tokenomics": "template_tokenomics.md",
    "governance": "template_governance.md",
    "security": "template_security.md",
    "risk-assessment": "template_risk_assessment.md",
    "revenue-model": "template_revenue_model.md",
    "liquidity": "template_liquidity.md",
    "integrations-dependencies": "template_integrations_dependencies.md",
    "competitive-positioning": "template_competitive_analysis.md",
}
OUTPUT_FILES = {
    name: filename.removeprefix("template_").replace("_", " ").removesuffix(
        ".md"
    ).title().replace(" ", "-") + ".md"
    for name, filename in TEMPLATE_FILES.items()
}
EXPECTED_HEADINGS = {
    "protocol-overview": "# Protocol Overview",
    "architecture": "# Architecture",
    "tokenomics": "# Tokenomics",
    "governance": "# Governance",
    "security": "# Security",
    "risk-assessment": "# Risk Assessment",
    "revenue-model": "# Revenue Model",
    "liquidity": "# Liquidity",
    "integrations-dependencies": "# Integrations & Dependencies",
    "competitive-positioning": "# Competitive Positioning",
}
RESEARCH_CATEGORIES = tuple(TEMPLATE_FILES)
NON_RESEARCH_DIRECTORIES = {
    "brand-guidelines",
    "terms-of-service",
}
NON_RESEARCH_FILENAMES = {
    "media-coverage.md",
    "privacy-policy.md",
}


@dataclass(frozen=True)
class ExtractionResult:
    template: str
    output_path: Path
    provider: str
    source_files: int
    source_characters: int
    mode: str = "single"
    provider_calls: int = 1
    reused_calls: int = 0


@dataclass(frozen=True)
class SourceChunk:
    identifier: str
    text: str
    source_files: tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class ExtractionPlan:
    template: str
    source_files: int
    source_characters: int
    initial_chunks: int
    mode: str
    minimum_provider_calls: int


@dataclass(frozen=True)
class _Ledger:
    identifier: str
    text: str
    digest: str


def plan_extraction(
    *,
    workspace: ProjectWorkspace,
    template_name: str,
    prompts_root: str | Path,
    maximum_prompt_characters: int = MAX_PROVIDER_PROMPT_CHARACTERS,
) -> ExtractionPlan:
    if template_name not in TEMPLATE_FILES:
        raise ValueError(f"Unknown research template {template_name!r}.")

    prompts = Path(prompts_root)
    master = (prompts / "master_prompt.md").read_text(encoding="utf-8")
    template = (
        prompts / "templates" / TEMPLATE_FILES[template_name]
    ).read_text(encoding="utf-8")
    try:
        source_bundle, source_files = load_source_bundle(
            workspace.sources_directory
        )
    except ValueError as exc:
        if "chunking" not in str(exc):
            raise
        source_bundle, source_files = "", ()

    if source_bundle and len(
        build_extraction_prompt(
            master_prompt=master,
            template=template,
            source_bundle=source_bundle,
        )
    ) <= maximum_prompt_characters:
        return ExtractionPlan(
            template=template_name,
            source_files=len(source_files),
            source_characters=len(source_bundle),
            initial_chunks=1,
            mode="single",
            minimum_provider_calls=1,
        )

    overhead = len(
        _build_shared_ledger_prompt(
            master_prompt=master,
            source_chunk="",
        )
    )
    chunks, files, source_characters = split_source_chunks(
        workspace.sources_directory,
        maximum_characters=maximum_prompt_characters - overhead - 200,
    )
    return ExtractionPlan(
        template=template_name,
        source_files=len(files),
        source_characters=source_characters,
        initial_chunks=len(chunks),
        mode="chunked",
        minimum_provider_calls=len(chunks) + 1,
    )


def load_source_bundle(
    directory: str | Path,
    *,
    maximum_characters: int = MAX_SINGLE_PASS_SOURCE_CHARACTERS,
) -> tuple[str, tuple[Path, ...]]:
    source_root = Path(directory)

    if maximum_characters <= 0:
        raise ValueError("Maximum source characters must be positive.")
    if not source_root.exists():
        raise FileNotFoundError(
            f"Crawled source directory does not exist: {source_root}"
        )

    files = _research_source_files(source_root)

    if not files:
        raise ValueError(
            f"No Markdown source files were found in {source_root}."
        )

    sections = []
    character_count = 0

    for path in files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(source_root).as_posix()
        section = (
            f"\n\n--- SOURCE FILE: {relative} ---\n\n"
            f"{text.rstrip()}\n"
        )
        character_count += len(section)

        if character_count > maximum_characters:
            raise ValueError(
                "Crawled documentation exceeds the safe single-pass "
                f"extraction limit of {maximum_characters:,} characters. "
                "Source chunking is required before automated extraction."
            )

        sections.append(section)

    return "".join(sections).lstrip(), files


def build_extraction_prompt(
    *,
    master_prompt: str,
    template: str,
    source_bundle: str,
) -> str:
    if not all(
        isinstance(value, str) and value.strip()
        for value in (master_prompt, template, source_bundle)
    ):
        raise ValueError("Extraction prompt components cannot be empty.")

    return (
        f"{master_prompt.rstrip()}\n\n"
        "---\n\n"
        "# Required Output Template\n\n"
        f"{template.rstrip()}\n\n"
        "---\n\n"
        "# Supplied Documentation\n\n"
        f"{source_bundle.rstrip()}\n"
    )


def split_source_chunks(
    directory: str | Path,
    *,
    maximum_characters: int,
) -> tuple[tuple[SourceChunk, ...], tuple[Path, ...], int]:
    """Split Markdown sources deterministically without dropping any text."""
    if maximum_characters <= 0:
        raise ValueError("Maximum chunk characters must be positive.")

    source_root = Path(directory)
    if not source_root.exists():
        raise FileNotFoundError(
            f"Crawled source directory does not exist: {source_root}"
        )

    files = _research_source_files(source_root)
    if not files:
        raise ValueError(
            f"No Markdown source files were found in {source_root}."
        )

    units: list[tuple[str, str]] = []
    source_characters = 0
    for path in files:
        relative = path.relative_to(source_root).as_posix()
        raw_text = path.read_text(encoding="utf-8").rstrip()
        source_characters += len(raw_text)
        text = _remove_fenced_code(raw_text)
        prefix = f"--- SOURCE FILE: {relative} ---\n\n"
        available = maximum_characters - len(prefix)
        if available <= 0:
            raise ValueError("Chunk size is too small for source boundaries.")

        pieces = _split_text(text, available)
        for index, piece in enumerate(pieces, start=1):
            label = relative
            if len(pieces) > 1:
                label = f"{relative} (part {index}/{len(pieces)})"
            units.append((relative, f"--- SOURCE FILE: {label} ---\n\n{piece}"))

    chunks: list[SourceChunk] = []
    current_sections: list[str] = []
    current_files: list[str] = []
    current_length = 0

    def flush() -> None:
        nonlocal current_sections, current_files, current_length
        if not current_sections:
            return
        text = "\n\n".join(current_sections).rstrip() + "\n"
        identifier = f"chunk-{len(chunks) + 1:04d}"
        chunks.append(
            SourceChunk(
                identifier=identifier,
                text=text,
                source_files=tuple(dict.fromkeys(current_files)),
                digest=_digest(text),
            )
        )
        current_sections = []
        current_files = []
        current_length = 0

    for relative, section in units:
        addition = len(section) + (2 if current_sections else 0)
        if current_sections and current_length + addition > maximum_characters:
            flush()
        current_sections.append(section)
        current_files.append(relative)
        current_length += addition
    flush()

    return tuple(chunks), files, source_characters


def _research_source_files(source_root: Path) -> tuple[Path, ...]:
    """Select research-bearing pages while retaining every local crawl file."""
    selected = []
    for path in sorted(source_root.rglob("*.md")):
        if not path.is_file():
            continue
        relative = path.relative_to(source_root)
        parts = {part.casefold() for part in relative.parts[:-1]}
        filename = relative.name.casefold()
        if parts & NON_RESEARCH_DIRECTORIES:
            continue
        if filename in NON_RESEARCH_FILENAMES:
            continue
        selected.append(path)
    return tuple(selected)


def extract_research_page_chunked(
    *,
    workspace: ProjectWorkspace,
    template_name: str,
    provider: TextProvider,
    prompts_root: str | Path,
    maximum_prompt_characters: int = MAX_PROVIDER_PROMPT_CHARACTERS,
    progress: Callable[[str], None] | None = None,
) -> ExtractionResult:
    """Extract all sources through resumable fact ledgers and consolidation."""
    if template_name not in TEMPLATE_FILES:
        supported = ", ".join(sorted(TEMPLATE_FILES))
        raise ValueError(
            f"Unknown research template {template_name!r}. "
            f"Supported templates: {supported}."
        )
    if maximum_prompt_characters < 4_000:
        raise ValueError("Maximum provider prompt is too small.")

    prompts = Path(prompts_root)
    master = (prompts / "master_prompt.md").read_text(encoding="utf-8")
    template = (
        prompts / "templates" / TEMPLATE_FILES[template_name]
    ).read_text(encoding="utf-8")
    output_path = (
        workspace.vault_entity_directory / OUTPUT_FILES[template_name]
    )
    if output_path.exists():
        raise FileExistsError(
            "Research page already exists and will not be overwritten: "
            f"{output_path}"
        )

    ledger_overhead = len(
        _build_shared_ledger_prompt(
            master_prompt=master,
            source_chunk="",
        )
    )
    chunk_budget = maximum_prompt_characters - ledger_overhead - 200
    if chunk_budget < 1_000:
        raise ValueError(
            "The extraction instructions leave insufficient room for sources."
        )

    chunks, source_files, source_characters = split_source_chunks(
        workspace.sources_directory,
        maximum_characters=chunk_budget,
    )
    run_directory = workspace.project_root / "extraction" / "shared-research"
    ledgers_directory = run_directory / "ledgers"
    reductions_directory = (
        workspace.project_root
        / "extraction"
        / template_name
        / "reductions"
    )
    ledgers_directory.mkdir(parents=True, exist_ok=True)
    reductions_directory.mkdir(parents=True, exist_ok=True)

    fingerprint = _digest(
        "\n".join(chunk.digest for chunk in chunks)
        + _digest(master)
        + _digest("|".join(RESEARCH_CATEGORIES))
    )
    state_path = run_directory / "state.json"
    state = _load_or_initialize_state(
        state_path,
        template_name="shared-research",
        fingerprint=fingerprint,
        chunks=chunks,
    )

    provider_calls = 0
    reused_calls = 0
    ledgers: list[_Ledger] = []
    report = progress or (lambda message: None)
    report(
        f"Shared research corpus: {len(chunks)} source batches; "
        "completed batches will be reused."
    )
    for chunk_number, chunk in enumerate(chunks, start=1):
        ledger_path = ledgers_directory / f"{chunk.identifier}.md"
        entry = state["chunks"][chunk.identifier]
        if (
            entry.get("status") == "complete"
            and entry.get("source_digest") == chunk.digest
            and ledger_path.exists()
        ):
            ledger_text = ledger_path.read_text(encoding="utf-8")
            reused_calls += 1
            report(
                f"[{chunk_number}/{len(chunks)}] Reused "
                f"{chunk.identifier}"
            )
        else:
            report(
                f"[{chunk_number}/{len(chunks)}] Extracting "
                f"{chunk.identifier}"
            )
            prompt = _build_shared_ledger_prompt(
                master_prompt=master,
                source_chunk=chunk.text,
            )
            _ensure_prompt_size(prompt, maximum_prompt_characters)
            response = provider.generate(
                prompt,
                working_directory=workspace.project_root,
            )
            ledger_text = _validate_shared_ledger(response.text)
            _replace_text(ledger_path, ledger_text.rstrip() + "\n")
            entry.update(
                {
                    "status": "complete",
                    "source_digest": chunk.digest,
                    "ledger_digest": _digest(ledger_text),
                }
            )
            _write_json(state_path, state)
            provider_calls += 1
            report(
                f"[{chunk_number}/{len(chunks)}] Saved "
                f"{chunk.identifier}"
            )
        category_text = _select_category_ledger(
            ledger_text,
            template_name=template_name,
        )
        ledgers.append(
            _Ledger(
                identifier=chunk.identifier,
                text=category_text,
                digest=_digest(category_text),
            )
        )

    reduced, reduction_calls, reduction_reused = _reduce_ledgers(
        ledgers=tuple(ledgers),
        provider=provider,
        working_directory=workspace.project_root,
        reductions_directory=reductions_directory,
        maximum_prompt_characters=maximum_prompt_characters,
        target_characters=(
            maximum_prompt_characters
            - len(
                build_extraction_prompt(
                    master_prompt=master,
                    template=template,
                    source_bundle="placeholder",
                )
            )
            - 600
        ),
        progress=report,
    )
    provider_calls += reduction_calls
    reused_calls += reduction_reused

    final_prompt = build_extraction_prompt(
        master_prompt=master,
        template=template,
        source_bundle=(
            "# Extracted Fact Ledgers\n\n"
            "The following ledgers were extracted only from the crawled "
            "documentation. Consolidate them into the required page. "
            "Deduplicate facts and preserve source-file references only when "
            "the output template requests provenance.\n\n"
            + reduced
        ),
    )
    _ensure_prompt_size(final_prompt, maximum_prompt_characters)
    response = provider.generate(
        final_prompt,
        working_directory=workspace.project_root,
    )
    provider_calls += 1
    body = validate_extraction_output(
        response.text,
        expected_heading=EXPECTED_HEADINGS[template_name],
    )
    document = _frontmatter(workspace, response.provider) + body.rstrip() + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(document)
    except FileExistsError as exc:
        raise FileExistsError(
            "Research page already exists and will not be overwritten: "
            f"{output_path}"
        ) from exc

    state["status"] = "complete"
    outputs = dict(state.get("outputs", {}))
    outputs[template_name] = str(output_path)
    state["outputs"] = outputs
    _write_json(state_path, state)
    return ExtractionResult(
        template=template_name,
        output_path=output_path,
        provider=response.provider,
        source_files=len(source_files),
        source_characters=source_characters,
        mode="chunked",
        provider_calls=provider_calls,
        reused_calls=reused_calls,
    )


def extract_research_page(
    *,
    workspace: ProjectWorkspace,
    template_name: str,
    provider: TextProvider,
    prompts_root: str | Path,
    mode: str = "auto",
    maximum_prompt_characters: int = MAX_PROVIDER_PROMPT_CHARACTERS,
    progress: Callable[[str], None] | None = None,
) -> ExtractionResult:
    if mode not in {"auto", "single", "chunked"}:
        raise ValueError("Extraction mode must be auto, single, or chunked.")
    if mode == "chunked":
        return extract_research_page_chunked(
            workspace=workspace,
            template_name=template_name,
            provider=provider,
            prompts_root=prompts_root,
            maximum_prompt_characters=maximum_prompt_characters,
            progress=progress,
        )
    if template_name not in TEMPLATE_FILES:
        supported = ", ".join(sorted(TEMPLATE_FILES))
        raise ValueError(
            f"Unknown research template {template_name!r}. "
            f"Supported templates: {supported}."
        )

    prompts = Path(prompts_root)
    master = (prompts / "master_prompt.md").read_text(encoding="utf-8")
    template = (
        prompts / "templates" / TEMPLATE_FILES[template_name]
    ).read_text(encoding="utf-8")
    try:
        source_bundle, source_files = load_source_bundle(
            workspace.sources_directory
        )
    except ValueError as exc:
        if mode == "auto" and "chunking" in str(exc):
            return extract_research_page_chunked(
                workspace=workspace,
                template_name=template_name,
                provider=provider,
                prompts_root=prompts_root,
                maximum_prompt_characters=maximum_prompt_characters,
                progress=progress,
            )
        raise
    prompt = build_extraction_prompt(
        master_prompt=master,
        template=template,
        source_bundle=source_bundle,
    )
    if len(prompt) > maximum_prompt_characters:
        if mode == "auto":
            return extract_research_page_chunked(
                workspace=workspace,
                template_name=template_name,
                provider=provider,
                prompts_root=prompts_root,
                maximum_prompt_characters=maximum_prompt_characters,
                progress=progress,
            )
        raise ValueError(
            "Extraction prompt exceeds the configured single-pass limit; "
            "use auto or chunked mode."
        )
    output_path = (
        workspace.vault_entity_directory / OUTPUT_FILES[template_name]
    )

    if output_path.exists():
        raise FileExistsError(
            f"Research page already exists and will not be overwritten: "
            f"{output_path}"
        )

    response = provider.generate(
        prompt,
        working_directory=workspace.project_root,
    )
    body = validate_extraction_output(
        response.text,
        expected_heading=EXPECTED_HEADINGS[template_name],
    )
    document = _frontmatter(workspace, response.provider) + body.rstrip() + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with output_path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(document)
    except FileExistsError as exc:
        raise FileExistsError(
            f"Research page already exists and will not be overwritten: "
            f"{output_path}"
        ) from exc

    return ExtractionResult(
        template=template_name,
        output_path=output_path,
        provider=response.provider,
        source_files=len(source_files),
        source_characters=len(source_bundle),
        mode="single",
        provider_calls=1,
    )


def _build_shared_ledger_prompt(
    *,
    master_prompt: str,
    source_chunk: str,
) -> str:
    category_list = "\n".join(
        f"- `{category}`" for category in RESEARCH_CATEGORIES
    )
    return (
        f"{master_prompt.rstrip()}\n\n"
        "---\n\n"
        "# Shared Research-Ledger Task\n\n"
        "Extract decision-relevant facts from this source batch once and "
        "classify each fact under the single most specific research category. "
        "This intermediate corpus will be reused to generate multiple pages.\n\n"
        "Required categories:\n"
        f"{category_list}\n\n"
        "Requirements:\n"
        "- Return Markdown beginning with `# Research Ledger`.\n"
        "- Include every category as an exact `## category-name` heading, in "
        "the order listed above.\n"
        "- Put each fact under only one category.\n"
        "- Use compact bullets; write `- No relevant facts.` for an empty "
        "category.\n"
        "- Use plain ASCII punctuation.\n"
        "- Attach the supplied source filename to every fact.\n"
        "- Preserve qualifications, numbers, dates, and conflicting claims.\n"
        "- Do not infer, evaluate truth, add prior knowledge, or write prose.\n"
        "---\n\n"
        "# Source Batch\n\n"
        f"{source_chunk.rstrip()}\n"
    )


def _build_reduction_prompt(
    ledger_bundle: str,
    *,
    maximum_output_characters: int,
) -> str:
    return (
        "# Fact-Ledger Reduction\n\n"
        "Consolidate the supplied intermediate ledgers into a smaller ledger.\n"
        "Return Markdown beginning with `# Fact Ledger`.\n\n"
        f"Hard output limit: {maximum_output_characters:,} characters.\n\n"
        "Rules:\n"
        "- Preserve distinct facts that could materially change an investment "
        "or risk assessment.\n"
        "- Deduplicate repeated facts.\n"
        "- Preserve conflicts, qualifications, numbers, dates, and source "
        "filenames.\n"
        "- Remove function-by-function API descriptions, parameter lists, "
        "tutorial steps, code behavior already represented by a higher-level "
        "mechanism, and minor implementation details.\n"
        "- Combine closely related mechanics into one compact fact without "
        "losing material conditions.\n"
        "- Do not infer, verify, evaluate, or introduce outside information.\n"
        "- Use compact bullets or tables; no introduction or conclusion.\n\n"
        "- Use plain ASCII punctuation.\n\n"
        "---\n\n"
        f"{ledger_bundle.rstrip()}\n"
    )


def _reduce_ledgers(
    *,
    ledgers: tuple[_Ledger, ...],
    provider: TextProvider,
    working_directory: Path,
    reductions_directory: Path,
    maximum_prompt_characters: int,
    target_characters: int,
    progress: Callable[[str], None],
) -> tuple[str, int, int]:
    if target_characters < 1_000:
        raise ValueError("Final extraction prompt leaves too little ledger room.")

    active = list(ledgers)
    provider_calls = 0
    reused_calls = 0

    for round_number in range(1, 9):
        bundle = _join_ledgers(active)
        if len(bundle) <= target_characters:
            return bundle, provider_calls, reused_calls

        groups = _group_ledgers_for_reduction(
            active,
            maximum_prompt_characters=maximum_prompt_characters,
        )
        reduced: list[_Ledger] = []
        for group_number, group in enumerate(groups, start=1):
            group_bundle = _join_ledgers(group)
            reduction_output_limit = min(
                8_000,
                max(3_500, target_characters // len(groups) - 500),
            )
            prompt = _build_reduction_prompt(
                group_bundle,
                maximum_output_characters=reduction_output_limit,
            )
            _ensure_prompt_size(prompt, maximum_prompt_characters)
            input_digest = _digest(prompt)
            path = reductions_directory / (
                f"round-{round_number:02d}-group-{group_number:04d}-"
                f"{input_digest[:12]}.md"
            )
            if path.exists():
                text = path.read_text(encoding="utf-8")
                reused_calls += 1
                progress(
                    f"Reused consolidation round {round_number}, "
                    f"group {group_number}/{len(groups)}"
                )
            else:
                progress(
                    f"Consolidating round {round_number}, "
                    f"group {group_number}/{len(groups)}"
                )
                response = provider.generate(
                    prompt,
                    working_directory=working_directory,
                )
                text = _validate_ledger(response.text)
                _replace_text(path, text.rstrip() + "\n")
                provider_calls += 1
            reduced.append(
                _Ledger(
                    identifier=path.stem,
                    text=text,
                    digest=_digest(text),
                )
            )

        if len(_join_ledgers(reduced)) >= len(bundle):
            raise ValueError(
                "Hermes did not reduce the intermediate ledgers enough to fit "
                "the final prompt. Review the saved ledgers or use smaller "
                "source batches."
            )
        active = reduced

    raise ValueError(
        "Intermediate ledgers remain too large after eight reduction rounds."
    )


def _group_ledgers_for_reduction(
    ledgers: list[_Ledger],
    *,
    maximum_prompt_characters: int,
) -> list[tuple[_Ledger, ...]]:
    overhead = len(
        _build_reduction_prompt(
            "",
            maximum_output_characters=8_000,
        )
    )
    allowance = maximum_prompt_characters - overhead
    if allowance < 1_000:
        raise ValueError("Reduction prompt leaves too little ledger room.")

    normalized: list[_Ledger] = []
    for ledger in ledgers:
        if len(ledger.text) <= allowance:
            normalized.append(ledger)
            continue
        for index, piece in enumerate(
            _split_text(ledger.text, allowance - 100),
            start=1,
        ):
            normalized.append(
                _Ledger(
                    identifier=f"{ledger.identifier}-part-{index}",
                    text=piece,
                    digest=_digest(piece),
                )
            )

    groups: list[tuple[_Ledger, ...]] = []
    current: list[_Ledger] = []
    for ledger in normalized:
        candidate = current + [ledger]
        if current and len(_join_ledgers(candidate)) > allowance:
            groups.append(tuple(current))
            current = []
        current.append(ledger)
    if current:
        groups.append(tuple(current))
    return groups


def _join_ledgers(ledgers: list[_Ledger] | tuple[_Ledger, ...]) -> str:
    return "\n\n".join(
        f"--- LEDGER: {ledger.identifier} ---\n\n{ledger.text.rstrip()}"
        for ledger in ledgers
    ).rstrip()


def _split_text(text: str, maximum_characters: int) -> list[str]:
    if len(text) <= maximum_characters:
        return [text]

    pieces: list[str] = []
    remaining = text
    while len(remaining) > maximum_characters:
        window = remaining[: maximum_characters + 1]
        split_at = max(
            window.rfind("\n\n"),
            window.rfind("\n"),
            window.rfind(" "),
        )
        if split_at < maximum_characters // 2:
            split_at = maximum_characters
        piece = remaining[:split_at].rstrip()
        if not piece:
            piece = remaining[:maximum_characters]
            split_at = maximum_characters
        pieces.append(piece)
        remaining = remaining[split_at:].lstrip()
    if remaining:
        pieces.append(remaining)
    return pieces


def _remove_fenced_code(text: str) -> str:
    """Remove implementation examples while retaining surrounding facts."""
    return re.sub(
        r"(?ms)^```[^\n]*\n.*?^```\s*",
        "",
        text,
    ).strip()


def _load_or_initialize_state(
    path: Path,
    *,
    template_name: str,
    fingerprint: str,
    chunks: tuple[SourceChunk, ...],
) -> dict[str, Any]:
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Chunk state is invalid JSON: {path}") from exc
        if (
            state.get("schema_version") != EXTRACTION_STATE_VERSION
            or state.get("template") != template_name
        ):
            raise ValueError(
                f"Chunk state is incompatible and must be removed: {path}"
            )
        if state.get("source_fingerprint") != fingerprint:
            raise ValueError(
                "Crawled sources or prompts changed after chunk extraction "
                f"started. Remove the stale intermediate folder: {path.parent}"
            )
        return state

    state = {
        "schema_version": EXTRACTION_STATE_VERSION,
        "template": template_name,
        "source_fingerprint": fingerprint,
        "status": "in_progress",
        "chunks": {
            chunk.identifier: {
                "source_files": list(chunk.source_files),
                "source_digest": chunk.digest,
                "status": "pending",
            }
            for chunk in chunks
        },
    }
    _write_json(path, state)
    return state


def _validate_ledger(text: str) -> str:
    output = text.strip()
    if not output:
        raise ValueError("The provider returned an empty fact ledger.")
    if "# Fact Ledger" not in output:
        raise ValueError(
            "The provider output is missing the '# Fact Ledger' heading."
        )
    if output.startswith("```") or output.endswith("```"):
        raise ValueError(
            "The provider wrapped the complete fact ledger in a code fence."
        )
    return output


def _validate_shared_ledger(text: str) -> str:
    output = text.strip()
    if not output:
        raise ValueError("The provider returned an empty research ledger.")
    if "# Research Ledger" not in output:
        raise ValueError(
            "The provider output is missing the '# Research Ledger' heading."
        )
    missing = [
        category
        for category in RESEARCH_CATEGORIES
        if f"## {category}" not in output
    ]
    if missing:
        raise ValueError(
            "The provider research ledger is missing categories: "
            + ", ".join(missing)
        )
    if output.startswith("```") or output.endswith("```"):
        raise ValueError(
            "The provider wrapped the complete research ledger in a code fence."
        )
    return output


def _select_category_ledger(text: str, *, template_name: str) -> str:
    heading = f"## {template_name}"
    start = text.find(heading)
    if start < 0:
        raise ValueError(
            f"Research ledger is missing category {template_name!r}."
        )
    content_start = start + len(heading)
    next_heading = text.find("\n## ", content_start)
    content = (
        text[content_start:]
        if next_heading < 0
        else text[content_start:next_heading]
    ).strip()
    if not content:
        content = "- No relevant facts."
    return f"# Fact Ledger\n\n{content}"


def _ensure_prompt_size(prompt: str, maximum: int) -> None:
    if len(prompt) > maximum:
        raise ValueError(
            f"Prepared provider prompt is {len(prompt):,} characters and "
            f"exceeds the configured limit of {maximum:,}."
        )


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _replace_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _write_json(path: Path, document: dict[str, Any]) -> None:
    _replace_text(path, json.dumps(document, indent=2) + "\n")


def validate_extraction_output(text: str, *, expected_heading: str) -> str:
    output = text.strip()

    if not output:
        raise ValueError("The provider returned an empty research page.")
    if "TEMPLATE INSTRUCTIONS" in output:
        raise ValueError(
            "The provider copied template instructions into the research page."
        )
    if expected_heading not in output:
        raise ValueError(
            f"The provider output is missing heading {expected_heading!r}."
        )
    if output.startswith("```") or output.endswith("```"):
        raise ValueError(
            "The provider wrapped the complete research page in a code fence."
        )

    return output


def _frontmatter(
    workspace: ProjectWorkspace,
    provider: str,
) -> str:
    extracted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return (
        "---\n"
        f'entity: "{workspace.name}"\n'
        f'entity_type: "{workspace.document["entity_type"]}"\n'
        f'verification_status: "{workspace.document["verification_status"]}"\n'
        f'extraction_provider: "{provider}"\n'
        f'extracted_at: "{extracted_at}"\n'
        "---\n\n"
    )
