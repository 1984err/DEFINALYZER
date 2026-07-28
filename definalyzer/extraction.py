"""Controlled research extraction using a provider-neutral text interface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .providers import TextProvider
from .workspace import ProjectWorkspace


MAX_SINGLE_PASS_SOURCE_CHARACTERS = 300_000
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


@dataclass(frozen=True)
class ExtractionResult:
    template: str
    output_path: Path
    provider: str
    source_files: int
    source_characters: int


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

    files = tuple(
        path
        for path in sorted(source_root.rglob("*.md"))
        if path.is_file()
    )

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


def extract_research_page(
    *,
    workspace: ProjectWorkspace,
    template_name: str,
    provider: TextProvider,
    prompts_root: str | Path,
) -> ExtractionResult:
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
    source_bundle, source_files = load_source_bundle(
        workspace.sources_directory
    )
    prompt = build_extraction_prompt(
        master_prompt=master,
        template=template,
        source_bundle=source_bundle,
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
    )


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
