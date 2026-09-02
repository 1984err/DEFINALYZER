"""Insert compact verification links at exact mapped research sections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


START_MARKER = "<!-- definalyzer-verification-links:start -->"
END_MARKER = "<!-- definalyzer-verification-links:end -->"


@dataclass(frozen=True)
class LinkInsertionResult:
    changed_pages: tuple[Path, ...]
    inserted_links: int
    unresolved_mappings: tuple[str, ...]


@dataclass(frozen=True)
class _Mapping:
    verification_id: str
    note_stem: str
    location: str
    block_id: str
    claim: str = ""


def insert_verification_links(
    *,
    verification_page: Path,
    research_directory: Path,
) -> LinkInsertionResult:
    mappings = _parse_link_map(
        verification_page.read_text(encoding="utf-8")
    )
    by_note: dict[str, list[_Mapping]] = {}
    for mapping in mappings:
        by_note.setdefault(mapping.note_stem.casefold(), []).append(mapping)

    changed: list[Path] = []
    unresolved: list[str] = []
    inserted = 0
    verification_target = _verification_target(verification_page)

    for note_key, note_mappings in sorted(by_note.items()):
        path = _find_note(research_directory, note_key)
        if path is None:
            unresolved.extend(
                f"{mapping.verification_id}: note {mapping.note_stem}"
                for mapping in note_mappings
            )
            continue
        original = path.read_text(encoding="utf-8")
        clean = strip_generated_verification_links(original)
        lines = clean.splitlines()
        headings = _headings(lines)
        links_by_line: dict[int, set[tuple[str, str]]] = {}
        for mapping in note_mappings:
            heading_line = _match_location(
                mapping.location,
                headings,
                lines,
                claim=mapping.claim,
            )
            if heading_line is None:
                unresolved.append(
                    f"{mapping.verification_id}: "
                    f"{mapping.note_stem}#{mapping.location}"
                )
                continue
            links_by_line.setdefault(heading_line, set()).add(
                (mapping.verification_id, mapping.block_id)
            )

        if not links_by_line:
            if clean != original:
                _write_text_atomic(path, clean)
                changed.append(path)
            continue

        output: list[str] = []
        for index, line in enumerate(lines):
            output.append(line)
            rows = links_by_line.get(index)
            if not rows:
                continue
            links = " · ".join(
                f"[[{verification_target}#^{block_id}|"
                f"{verification_id}]]"
                for verification_id, block_id in sorted(rows)
            )
            output.extend(
                (
                    "",
                    f"Verification: {links}",
                    "",
                )
            )
            inserted += len(rows)
        updated = _normalize_markdown_spacing("\n".join(output)).rstrip() + "\n"
        if updated != original:
            _write_text_atomic(path, updated)
            changed.append(path)

    # A removed claim can leave its old page absent from the new link map.
    # Clear generated links on those pages as well, keeping the research intact.
    for path in sorted(research_directory.glob("*.md")):
        if path.stem.casefold() in by_note:
            continue
        original = path.read_text(encoding="utf-8")
        if f"[[{verification_target}#^" not in original:
            continue
        clean = strip_generated_verification_links(original)
        if clean != original:
            _write_text_atomic(path, clean)
            changed.append(path)

    return LinkInsertionResult(
        changed_pages=tuple(changed),
        inserted_links=inserted,
        unresolved_mappings=tuple(unresolved),
    )


def _verification_target(page: Path) -> str:
    parts = page.with_suffix("").parts
    folded = tuple(part.casefold() for part in parts)
    if "verification" not in folded:
        return page.stem
    return "/".join(parts[folded.index("verification") :])


def _parse_link_map(text: str) -> tuple[_Mapping, ...]:
    marker = "## Research Link Map"
    if marker not in text:
        raise ValueError("Verification page is missing its Research Link Map.")
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    claims = _claims_by_id(text)
    mappings = []
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [
            cell.strip()
            for cell in re.split(r"(?<!\\)\|", line.strip())[1:-1]
        ]
        if len(cells) != 4 or not cells[0].startswith("VR-"):
            continue
        note_match = re.search(
            r"\[\[(?:(?:Protocols|Chains|Tokens)/[^/]+/)?"
            r"(?P<note>[^#|\\\]]+)",
            cells[1],
        )
        block_match = re.search(r"#\^(?P<block>[a-z0-9-]+)", cells[3])
        if note_match is None or block_match is None:
            continue
        mappings.append(
            _Mapping(
                verification_id=cells[0],
                note_stem=Path(note_match.group("note")).stem,
                location=cells[2],
                block_id=block_match.group("block"),
                claim=claims.get(cells[0], ""),
            )
        )
    if not mappings:
        empty_plan = (
            "| Verification ID | Research Note | Claim Location | Obsidian Link |" in section
            and not re.search(r"(?m)^###\s+VR-|^\|\s*VR-", text)
        )
        if not empty_plan:
            raise ValueError("Verification Research Link Map has no usable rows.")
    return tuple(mappings)


def _claims_by_id(text: str) -> dict[str, str]:
    claims: dict[str, str] = {}
    sections = re.finditer(
        r"(?ms)^###\s+(?P<id>VR-[A-Z0-9-]+)\b.*?"
        r"(?=^###\s+VR-|^##\s+|\Z)",
        text,
    )
    for section in sections:
        claim = re.search(
            r"(?m)^\|\s*Claim\s*\|\s*(?P<claim>.*?)\s*\|\s*$",
            section.group(0),
        )
        if claim:
            claims[section.group("id")] = claim.group("claim")
    return claims


def _find_note(directory: Path, note_key: str) -> Path | None:
    for path in directory.glob("*.md"):
        if path.stem.casefold() == note_key:
            return path
    return None


def _headings(lines: list[str]) -> tuple[tuple[int, str], ...]:
    result = []
    for index, line in enumerate(lines):
        match = re.match(r"^#{1,6}\s+(?P<title>.+?)\s*$", line)
        if match:
            result.append((index, _normalize(match.group("title"))))
    return tuple(result)


def _match_heading(
    location: str,
    headings: tuple[tuple[int, str], ...],
) -> int | None:
    candidates = [
        _normalize(value)
        for value in re.split(r"\s*;\s*", location)
        if value.strip()
    ]
    for candidate in candidates:
        exact = [line for line, title in headings if title == candidate]
        if exact:
            return exact[0]
        prefix = [
            line
            for line, title in headings
            if candidate.startswith(title + " —")
            or candidate.startswith(title + " -")
            or candidate.startswith(title + ":")
        ]
        if prefix:
            return prefix[0]
    return None


def _match_location(
    location: str,
    headings: tuple[tuple[int, str], ...],
    lines: list[str],
    *,
    claim: str = "",
) -> int | None:
    """Resolve an exact heading or an exact unique phrase under a heading."""

    heading_line = _match_heading(location, headings)
    if heading_line is not None:
        return heading_line

    candidates = [
        _normalize(value)
        for value in re.split(r"\s*;\s*", location)
        if value.strip()
    ]
    for candidate in candidates:
        matches = [
            index
            for index, line in enumerate(lines)
            if candidate and candidate in _normalize(line)
        ]
        if len(matches) != 1:
            continue
        preceding = [
            line_number
            for line_number, _ in headings
            if line_number < matches[0]
        ]
        if preceding:
            return preceding[-1]
    return _match_section_content(
        location=location,
        claim=claim,
        headings=headings,
        lines=lines,
    )


def _match_section_content(
    *,
    location: str,
    claim: str,
    headings: tuple[tuple[int, str], ...],
    lines: list[str],
) -> int | None:
    """Map a planner paraphrase only when one section is a clear token match."""

    query = _meaningful_tokens(f"{location} {claim}")
    if len(query) < 2:
        return None
    scored: list[tuple[int, int]] = []
    for index, (line_number, heading_title) in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
        section = _meaningful_tokens(" ".join(lines[line_number:end]))
        heading_overlap = len(query & _meaningful_tokens(heading_title))
        scored.append((len(query & section) + heading_overlap, line_number))
    scored.sort(reverse=True)
    if not scored:
        return None
    best_score, best_line = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0
    minimum = max(2, (len(query) + 3) // 4)
    if best_score < minimum or best_score == second_score:
        return None
    return best_line


def _meaningful_tokens(value: str) -> set[str]:
    stopwords = {
        "a", "all", "an", "and", "are", "as", "at", "be", "by",
        "does", "for", "from", "in", "is", "it", "not", "of", "on",
        "or", "that", "the", "their", "this", "to", "with",
    }
    tokens = set()
    for token in re.findall(r"[a-z0-9]+", value.casefold()):
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        if token not in stopwords:
            tokens.add(token)
    return tokens


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _normalize_markdown_spacing(text: str) -> str:
    normalized: list[str] = []
    for line in text.splitlines():
        is_table = line.startswith("|") and line.endswith("|")
        previous_is_table = bool(
            normalized
            and normalized[-1].startswith("|")
            and normalized[-1].endswith("|")
        )
        if is_table and normalized and normalized[-1].strip() and not previous_is_table:
            normalized.append("")
        if (
            normalized
            and re.match(r"^#{1,6}\s+\S", normalized[-1])
            and line.strip()
        ):
            normalized.append("")
        normalized.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(normalized))


def strip_generated_verification_links(text: str) -> str:
    legacy_pattern = re.compile(
        rf"\n?{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}\n?",
        re.DOTALL,
    )
    cleaned = legacy_pattern.sub("\n", text)
    generated_line = re.compile(
        r"(?m)^\s*Verification:\s+"
        r"\[\[Verification/[^\r\n]+\]\]"
        r"(?:\s+·\s+\[\[Verification/[^\r\n]+\]\])*\s*$\r?\n?"
    )
    cleaned = generated_line.sub("", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def _write_text_atomic(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)
