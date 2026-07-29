"""Read-only, section-scoped AI explanations for generated research pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from .providers import TextProvider
from .workspace import ProjectWorkspace, slugify


MAX_SECTION_CHARACTERS = 20_000
REVIEW_FOLDER = "Analyst Reviews"
HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")


@dataclass(frozen=True)
class ReviewSection:
    title: str
    level: int
    line: int
    text: str

    @property
    def label(self) -> str:
        return f"{'#' * self.level} {self.title}"


@dataclass(frozen=True)
class AnalystReviewResult:
    answer: str
    provider: str
    page: Path
    section: ReviewSection
    question: str
    saved_path: Path | None = None


def list_review_pages(workspace: ProjectWorkspace) -> tuple[Path, ...]:
    """List generated project pages that can be reviewed."""

    directory = workspace.vault_entity_directory
    if not directory.exists():
        return ()
    return tuple(
        path
        for path in sorted(directory.glob("*.md"), key=lambda item: item.name.casefold())
        if path.is_file()
    )


def parse_review_sections(page: Path) -> tuple[ReviewSection, ...]:
    """Parse Markdown headings and the bounded content beneath each heading."""

    lines = page.read_text(encoding="utf-8").splitlines()
    headings: list[tuple[int, int, str]] = []
    in_fence = False
    fence_marker: str | None = None

    for index, line in enumerate(lines):
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in {"```", "~~~"}:
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue
        match = HEADING_PATTERN.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))

    sections: list[ReviewSection] = []
    for position, (start, level, title) in enumerate(headings):
        end = len(lines)
        for next_start, next_level, _ in headings[position + 1 :]:
            if next_level <= level:
                end = next_start
                break
        text = "\n".join(lines[start:end]).strip()
        sections.append(
            ReviewSection(
                title=title,
                level=level,
                line=start + 1,
                text=text,
            )
        )
    return tuple(sections)


def select_review_page(
    workspace: ProjectWorkspace,
    value: str,
) -> Path:
    pages = list_review_pages(workspace)
    clean = value.strip().casefold()
    matches = [
        page
        for page in pages
        if clean in {page.name.casefold(), page.stem.casefold()}
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Research page {value!r} was not found for {workspace.name}."
        )
    return matches[0]


def select_review_section(
    page: Path,
    value: str,
) -> ReviewSection:
    sections = parse_review_sections(page)
    clean = value.strip().casefold()
    matches = [
        section
        for section in sections
        if clean in {section.title.casefold(), section.label.casefold()}
    ]
    if not matches:
        raise ValueError(f"Heading {value!r} was not found in {page.name}.")
    if len(matches) > 1:
        raise ValueError(
            f"Heading {value!r} appears more than once in {page.name}; "
            "use the guided menu to select the intended occurrence."
        )
    return matches[0]


def run_analyst_review(
    *,
    workspace: ProjectWorkspace,
    provider: TextProvider,
    page: Path,
    section: ReviewSection,
    question: str,
) -> AnalystReviewResult:
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Analyst question cannot be empty.")
    if page.resolve().parent != workspace.vault_entity_directory.resolve():
        raise ValueError("Review page must belong to the selected project.")
    if len(section.text) > MAX_SECTION_CHARACTERS:
        raise ValueError(
            f"The selected section is {len(section.text):,} characters. "
            "Select a more specific subheading so no context is truncated."
        )

    prompt = _build_prompt(
        workspace=workspace,
        page=page,
        section=section,
        question=clean_question,
    )
    response = provider.generate(
        prompt,
        working_directory=workspace.project_root,
    )
    return AnalystReviewResult(
        answer=response.text.strip(),
        provider=response.provider,
        page=page,
        section=section,
        question=clean_question,
    )


def save_analyst_review(
    *,
    workspace: ProjectWorkspace,
    result: AnalystReviewResult,
    now: datetime | None = None,
) -> AnalystReviewResult:
    """Save a non-canonical review without altering its source page."""

    timestamp = now or datetime.now(timezone.utc)
    directory = workspace.vault_root / REVIEW_FOLDER / workspace.name
    directory.mkdir(parents=True, exist_ok=True)
    base = (
        f"{timestamp.strftime('%Y%m%d-%H%M%S')}-"
        f"{slugify(result.page.stem)}-{slugify(result.section.title)}"
    )
    path = _unused_path(directory / f"{base}.md")
    source_link = _obsidian_source_link(workspace, result)
    text = (
        "---\n"
        'generated_by: "definalyzer_analyst_review"\n'
        f'entity: "{_yaml_text(workspace.name)}"\n'
        f'provider: "{_yaml_text(result.provider)}"\n'
        f'generated_at: "{timestamp.isoformat(timespec="seconds")}"\n'
        'data_class: "non_canonical_ai_explanation"\n'
        "---\n\n"
        f"# Analyst Review — {result.section.title}\n\n"
        f"- Source: {source_link}\n"
        f"- Source line: {result.section.line}\n"
        "- Scope: Selected section only\n"
        "- Status: AI explanation; not research evidence or verification\n\n"
        "## Question\n\n"
        f"{result.question}\n\n"
        "## Answer\n\n"
        f"{result.answer}\n\n"
        "## Use Limitation\n\n"
        "This explanation may contain model error. Refer to the linked source "
        "section and its verification status before relying on it.\n"
    )
    with path.open("x", encoding="utf-8", newline="\n") as file:
        file.write(text)
    return AnalystReviewResult(
        answer=result.answer,
        provider=result.provider,
        page=result.page,
        section=result.section,
        question=result.question,
        saved_path=path,
    )


def _build_prompt(
    *,
    workspace: ProjectWorkspace,
    page: Path,
    section: ReviewSection,
    question: str,
) -> str:
    return (
        "# DEFINALYZER Section-Scoped Analyst Review\n\n"
        "Answer the user's question using only the selected research section "
        "below. Do not use prior knowledge, browse, infer undocumented protocol "
        "facts, or treat an unverified claim as verified. Explain terminology "
        "and mechanics in plain language while preserving important caveats.\n\n"
        "If the section is insufficient, say exactly what cannot be answered "
        "and identify the kind of additional page or evidence needed. Clearly "
        "label any reasoning as `Inference`; label absent information as "
        "`Unknown`. Do not provide an investment recommendation. Keep the "
        "answer focused and concise.\n\n"
        f"Entity: {workspace.name}\n"
        f"Page: {page.name}\n"
        f"Selected heading: {section.label}\n"
        f"Local source line: {section.line}\n\n"
        f"Question:\n{question}\n\n"
        "--- SELECTED SECTION START ---\n"
        f"{section.text}\n"
        "--- SELECTED SECTION END ---\n"
    )


def _obsidian_source_link(
    workspace: ProjectWorkspace,
    result: AnalystReviewResult,
) -> str:
    entity_folder = {
        "protocol": "Protocols",
        "chain": "Chains",
        "token": "Tokens",
    }[str(workspace.document["entity_type"])]
    target = (
        f"{entity_folder}/{workspace.name}/{result.page.stem}"
        f"#{result.section.title}"
    )
    label = f"{result.page.stem} — {result.section.title}"
    return f"[[{target}\\|{label}]]"


def _unused_path(path: Path) -> Path:
    if not path.exists():
        return path
    for suffix in range(2, 10_000):
        candidate = path.with_name(f"{path.stem}-{suffix}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError("Could not allocate a unique analyst review path.")


def _yaml_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
