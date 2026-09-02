"""Project-wide, retrieval-backed AI explanations for generated research."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .providers import TextProvider
from .workspace import ProjectWorkspace


MAX_CONTEXT_CHARACTERS = 20_000
MAX_PASSAGE_CHARACTERS = 4_500
REVIEW_FOLDER = "Analyst Reviews"
HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
WORD_PATTERN = re.compile(r"[a-z0-9][a-z0-9_.:/-]*", re.IGNORECASE)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do",
    "does", "for", "from", "how", "i", "in", "is", "it", "me", "of",
    "on", "or", "that", "the", "this", "to", "what", "when", "where",
    "which", "who", "why", "with",
}
QUERY_EXPANSIONS = {
    "money": ("fees", "revenue", "income", "economics", "value accrual"),
    "earn": ("yield", "revenue", "fees", "rewards"),
    "risk": ("security", "constraint", "failure", "trust", "unknown"),
    "safe": ("security", "risk", "audit", "trust", "control"),
    "control": ("governance", "admin", "permission", "authority", "owner"),
    "upgrade": ("proxy", "implementation", "governance", "admin"),
    "token": ("tokenomics", "emissions", "unlock", "vesting", "supply"),
    "chain": ("network", "deployment", "bridge"),
    "liquidation": ("collateral", "oracle", "solvency", "health factor"),
}


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
class ReviewPassage:
    path: Path
    display_path: str
    heading: str
    line: int
    text: str
    source_type: str
    score: float = 0.0


@dataclass(frozen=True)
class AnalystReviewResult:
    answer: str
    provider: str
    question: str
    passages: tuple[ReviewPassage, ...]
    scope: str
    deep: bool
    saved_path: Path | None = None


def list_review_pages(workspace: ProjectWorkspace) -> tuple[Path, ...]:
    """List generated project pages that can be reviewed."""

    directory = workspace.vault_entity_directory
    if not directory.exists():
        return ()
    return tuple(
        path
        for path in sorted(directory.glob("*.md"), key=lambda item: item.name.casefold())
        if path.is_file() and path.name != "Index.md"
    )


def parse_review_sections(page: Path) -> tuple[ReviewSection, ...]:
    """Parse Markdown headings and the content beneath each heading."""

    lines = page.read_text(encoding="utf-8").splitlines()
    headings = _headings(lines)
    sections: list[ReviewSection] = []
    for position, (start, level, title) in enumerate(headings):
        end = len(lines)
        for next_start, next_level, _ in headings[position + 1 :]:
            if next_level <= level:
                end = next_start
                break
        text = "\n".join(lines[start:end]).strip()
        if _section_has_content(text):
            sections.append(
                ReviewSection(title=title, level=level, line=start + 1, text=text)
            )
    return tuple(sections)


def select_review_page(workspace: ProjectWorkspace, value: str) -> Path:
    pages = list_review_pages(workspace)
    clean = value.strip().casefold()
    matches = [
        page for page in pages if clean in {page.name.casefold(), page.stem.casefold()}
    ]
    if len(matches) != 1:
        raise ValueError(f"Research page {value!r} was not found for {workspace.name}.")
    return matches[0]


def select_review_section(page: Path, value: str) -> ReviewSection:
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


def retrieve_review_passages(
    *,
    workspace: ProjectWorkspace,
    question: str,
    deep: bool = False,
    page: Path | None = None,
    section: ReviewSection | None = None,
    maximum_characters: int = MAX_CONTEXT_CHARACTERS,
) -> tuple[ReviewPassage, ...]:
    """Search project material locally and return a bounded context package."""

    if maximum_characters < 1_000:
        raise ValueError("Review context allowance is too small.")
    if (page is None) != (section is None):
        raise ValueError("A page and heading must be supplied together.")

    if page is not None and section is not None:
        candidates = (
            ReviewPassage(
                path=page,
                display_path=_display_path(workspace, page),
                heading=section.title,
                line=section.line,
                text=section.text,
                source_type="research",
            ),
        )
    else:
        candidates = tuple(_project_passages(workspace, deep=deep))
    if not candidates:
        raise ValueError("No searchable project material exists.")

    ranked = _rank_passages(question, candidates)
    selected: list[ReviewPassage] = []
    used = 0
    for passage in ranked:
        remaining = maximum_characters - used
        if remaining < 500:
            break
        text = passage.text
        if len(text) > remaining:
            if selected:
                continue
            text = text[:remaining].rsplit("\n", 1)[0].rstrip()
        selected.append(
            ReviewPassage(
                path=passage.path,
                display_path=passage.display_path,
                heading=passage.heading,
                line=passage.line,
                text=text,
                source_type=passage.source_type,
                score=passage.score,
            )
        )
        used += len(text)
    return tuple(selected)


def run_analyst_review(
    *,
    workspace: ProjectWorkspace,
    provider: TextProvider,
    question: str,
    deep: bool = False,
    page: Path | None = None,
    section: ReviewSection | None = None,
) -> AnalystReviewResult:
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Analyst question cannot be empty.")
    if page is not None and page.resolve().parent != workspace.vault_entity_directory.resolve():
        raise ValueError("Review page must belong to the selected project.")

    passages = retrieve_review_passages(
        workspace=workspace,
        question=clean_question,
        deep=deep,
        page=page,
        section=section,
    )
    scope = (
        f"{page.name} > {section.title}"
        if page is not None and section is not None
        else ("project research and collected documentation" if deep else "project research")
    )
    response = provider.generate(
        _build_prompt(
            workspace=workspace,
            passages=passages,
            question=clean_question,
            scope=scope,
        ),
        working_directory=workspace.project_root,
    )
    return AnalystReviewResult(
        answer=response.text.strip(),
        provider=response.provider,
        question=clean_question,
        passages=passages,
        scope=scope,
        deep=deep,
    )


def save_analyst_review(
    *,
    workspace: ProjectWorkspace,
    result: AnalystReviewResult,
    now: datetime | None = None,
) -> AnalystReviewResult:
    """Save a non-canonical review without altering source material."""

    timestamp = now or datetime.now(timezone.utc)
    directory = workspace.vault_root / REVIEW_FOLDER / workspace.name
    directory.mkdir(parents=True, exist_ok=True)
    path = _unused_path(
        directory / _review_filename(result.question)
    )
    source_lines = "\n".join(
        f"- **Source {index}:** {_obsidian_source_link(workspace, passage)} "
        f"^source-{index}"
        for index, passage in enumerate(result.passages, start=1)
    )
    linked_answer = _link_source_citations(
        result.answer,
        source_count=len(result.passages),
    )
    text = (
        "---\n"
        'generated_by: "definalyzer_analyst_review"\n'
        f'entity: "{_yaml_text(workspace.name)}"\n'
        f'provider: "{_yaml_text(result.provider)}"\n'
        f'generated_at: "{timestamp.isoformat(timespec="seconds")}"\n'
        'data_class: "non_canonical_ai_explanation"\n'
        "---\n\n"
        f"# Analyst Review - {result.question}\n\n"
        f"- Scope: {result.scope}\n"
        "- Status: AI explanation; not research evidence or verification\n\n"
        "## Question\n\n"
        f"{result.question}\n\n"
        "## Sources Consulted\n\n"
        f"{source_lines}\n\n"
        "## Answer\n\n"
        f"{linked_answer}\n\n"
        "## Use Limitation\n\n"
        "This explanation may contain model error. Refer to the linked sources "
        "and their verification status before relying on it.\n"
    )
    with path.open("x", encoding="utf-8", newline="\n") as file:
        file.write(text)
    return AnalystReviewResult(
        answer=result.answer,
        provider=result.provider,
        question=result.question,
        passages=result.passages,
        scope=result.scope,
        deep=result.deep,
        saved_path=path,
    )


def repair_analyst_review_citations(workspace: ProjectWorkspace) -> tuple[Path, ...]:
    """Add navigable source anchors to previously generated review notes."""

    directory = workspace.vault_root / REVIEW_FOLDER / workspace.name
    if not directory.exists():
        return ()
    changed = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if 'generated_by: "definalyzer_analyst_review"' not in text:
            continue
        updated = _repair_review_text(text)
        if updated == text:
            continue
        temporary = path.with_suffix(".md.tmp")
        temporary.write_text(updated, encoding="utf-8", newline="\n")
        temporary.replace(path)
        changed.append(path)
    return tuple(changed)


def _repair_review_text(text: str) -> str:
    marker = "## Sources Consulted\n\n"
    answer_marker = "\n\n## Answer\n\n"
    if marker not in text or answer_marker not in text:
        return text
    prefix, remainder = text.split(marker, 1)
    source_text, suffix = remainder.split(answer_marker, 1)
    lines = source_text.splitlines()
    numbered = []
    source_count = 0
    for line in lines:
        if not line.startswith("- "):
            numbered.append(line)
            continue
        source_count += 1
        if re.match(r"^- \*\*Source \d+:\*\* ", line):
            numbered.append(line)
            continue
        numbered.append(
            f"- **Source {source_count}:** {line[2:]} ^source-{source_count}"
        )
    answer, limitation = (
        suffix.split("\n\n## Use Limitation", 1)
        if "\n\n## Use Limitation" in suffix
        else (suffix, None)
    )
    answer = _link_source_citations(answer, source_count=source_count)
    repaired_suffix = answer
    if limitation is not None:
        repaired_suffix += "\n\n## Use Limitation" + limitation
    return (
        prefix
        + marker
        + "\n".join(numbered)
        + answer_marker
        + repaired_suffix
    )


def _link_source_citations(answer: str, *, source_count: int) -> str:
    def replace(match: re.Match[str]) -> str:
        number = int(match.group(1))
        if number < 1 or number > source_count:
            return match.group(0)
        return f"[[#^source-{number}|Source {number}]]"

    return re.sub(r"\[Source\s+(\d+)\]", replace, answer, flags=re.IGNORECASE)


def _project_passages(
    workspace: ProjectWorkspace, *, deep: bool
) -> list[ReviewPassage]:
    paths: list[tuple[Path, str]] = [
        *((path, "research") for path in list_review_pages(workspace)),
    ]
    if workspace.verification_page_path.exists():
        paths.append((workspace.verification_page_path, "verification"))
    paths.extend((path, "token") for path in _project_token_pages(workspace))
    if deep and workspace.sources_directory.exists():
        paths.extend(
            (path, "documentation")
            for path in sorted(workspace.sources_directory.rglob("*.md"))
            if path.is_file()
        )

    passages: list[ReviewPassage] = []
    seen: set[Path] = set()
    for path, source_type in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        passages.extend(_file_passages(workspace, path, source_type))
    return passages


def _project_token_pages(workspace: ProjectWorkspace) -> tuple[Path, ...]:
    registry = workspace.registry_directory / "registry.json"
    if not registry.exists():
        return ()
    try:
        document = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    rows = document.get("tokens") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        return ()
    pages = []
    for row in rows:
        symbol = row.get("symbol") if isinstance(row, dict) else None
        if isinstance(symbol, str) and symbol.strip():
            page = workspace.vault_root / "Tokens" / symbol.strip() / "Index.md"
            if page.exists():
                pages.append(page)
    return tuple(pages)


def _file_passages(
    workspace: ProjectWorkspace, path: Path, source_type: str
) -> list[ReviewPassage]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    headings = _headings(lines)
    blocks: list[tuple[int, str, str]] = []
    if not headings:
        blocks.append((1, path.stem, "\n".join(lines).strip()))
    else:
        prefix = "\n".join(lines[: headings[0][0]]).strip()
        if _content_text(prefix):
            blocks.append((1, path.stem, prefix))
        for index, (start, _level, title) in enumerate(headings):
            end = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
            content = "\n".join(lines[start:end]).strip()
            if _section_has_content(content):
                blocks.append((start + 1, title, content))

    passages = []
    for line, heading, block in blocks:
        for offset, piece in enumerate(_split_passage(block, MAX_PASSAGE_CHARACTERS)):
            passages.append(
                ReviewPassage(
                    path=path,
                    display_path=_display_path(workspace, path),
                    heading=heading if offset == 0 else f"{heading} (continued)",
                    line=line,
                    text=piece,
                    source_type=source_type,
                )
            )
    return passages


def _rank_passages(
    question: str, passages: tuple[ReviewPassage, ...]
) -> tuple[ReviewPassage, ...]:
    query_tokens = _query_tokens(question)
    document_tokens = [_tokens(f"{row.heading} {row.text}") for row in passages]
    frequencies = Counter(token for tokens in document_tokens for token in set(tokens))
    total = len(passages)
    ranked = []
    for row, tokens in zip(passages, document_tokens):
        counts = Counter(tokens)
        score = 0.0
        for token in query_tokens:
            if token not in counts:
                continue
            inverse = math.log((total + 1) / (frequencies[token] + 1)) + 1
            score += inverse * (1 + math.log(counts[token]))
            if token in _tokens(row.heading):
                score += inverse * 1.5
        phrase = " ".join(_tokens(question))
        if phrase and phrase in f"{row.heading} {row.text}".casefold():
            score += 5
        if row.source_type == "research":
            score += 0.25
        ranked.append(
            ReviewPassage(
                path=row.path,
                display_path=row.display_path,
                heading=row.heading,
                line=row.line,
                text=row.text,
                source_type=row.source_type,
                score=score,
            )
        )
    return tuple(
        sorted(
            ranked,
            key=lambda row: (-row.score, row.display_path.casefold(), row.line),
        )
    )


def _query_tokens(question: str) -> tuple[str, ...]:
    base = list(_tokens(question))
    expanded = list(base)
    for token in base:
        for phrase in QUERY_EXPANSIONS.get(token, ()):
            expanded.extend(_tokens(phrase))
    return tuple(dict.fromkeys(expanded))


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in (match.group(0).casefold() for match in WORD_PATTERN.finditer(text))
        if token not in STOP_WORDS and len(token) > 1
    )


def _headings(lines: list[str]) -> list[tuple[int, int, str]]:
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
    return headings


def _section_has_content(text: str) -> bool:
    lines = text.splitlines()[1:]
    return bool(_content_text("\n".join(lines)))


def _content_text(text: str) -> str:
    return "\n".join(
        line
        for line in text.splitlines()
        if line.strip()
        and not HEADING_PATTERN.match(line)
        and not line.strip().startswith("<!--")
        and not line.strip().endswith("-->")
    ).strip()


def _split_passage(text: str, maximum: int) -> tuple[str, ...]:
    if len(text) <= maximum:
        return (text,)
    pieces: list[str] = []
    active = ""
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) > maximum:
            if active:
                pieces.append(active)
                active = ""
            for start in range(0, len(paragraph), maximum):
                pieces.append(paragraph[start : start + maximum])
            continue
        candidate = f"{active}\n\n{paragraph}" if active else paragraph
        if len(candidate) > maximum:
            pieces.append(active)
            active = paragraph
        else:
            active = candidate
    if active:
        pieces.append(active)
    return tuple(pieces)


def _build_prompt(
    *,
    workspace: ProjectWorkspace,
    passages: tuple[ReviewPassage, ...],
    question: str,
    scope: str,
) -> str:
    context = "\n\n".join(
        f"--- SOURCE {index} ---\n"
        f"Path: {row.display_path}\nHeading: {row.heading}\n"
        f"Source type: {row.source_type}\nLine: {row.line}\n\n{row.text}"
        for index, row in enumerate(passages, start=1)
    )
    return (
        "# DEFINALYZER Project Research Q&A\n\n"
        "Answer the user's question from the retrieved project material below. "
        "The retrieval searched the project, but the supplied passages may still "
        "be incomplete. Do not use prior knowledge or browse. Do not treat an "
        "unverified claim as verified. Explain terminology and mechanics in plain "
        "language while preserving material caveats.\n\n"
        "Synthesize across passages when necessary. Cite supporting material inline "
        "as `[Source N]`. Clearly label reasoning as `Inference` and absent or "
        "insufficient information as `Unknown`. If the passages do not answer the "
        "question, say so directly. Do not provide an investment recommendation.\n\n"
        f"Entity: {workspace.name}\nSearch scope: {scope}\n\n"
        f"Question:\n{question}\n\n"
        "--- RETRIEVED MATERIAL START ---\n"
        f"{context}\n"
        "--- RETRIEVED MATERIAL END ---\n"
    )


def _display_path(workspace: ProjectWorkspace, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.root.resolve()).as_posix()
    except ValueError:
        return path.name


def _obsidian_source_link(workspace: ProjectWorkspace, passage: ReviewPassage) -> str:
    try:
        relative = passage.path.resolve().relative_to(workspace.vault_root.resolve())
    except ValueError:
        return f"`{passage.display_path}` - {passage.heading} (line {passage.line})"
    target = relative.with_suffix("").as_posix()
    label = f"{passage.path.stem} - {passage.heading}"
    return f"[[{target}#{passage.heading}\\|{label}]]"


def _unused_path(path: Path) -> Path:
    if not path.exists():
        return path
    for suffix in range(2, 10_000):
        candidate = path.with_name(f"{path.stem} - {suffix}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError("Could not allocate a unique analyst review path.")


def _review_filename(question: str) -> str:
    """Create a readable, Windows-safe Obsidian note name from a question."""

    title = re.sub(r'[<>:"/\\|?*]+', "", question)
    title = re.sub(r"\s+", " ", title).strip(" .-")
    if not title:
        title = "Analyst Review"
    return f"{title[:90].rstrip()}.md"


def _yaml_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
