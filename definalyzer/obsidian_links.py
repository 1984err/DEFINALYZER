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
    verification_name = verification_page.stem

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
            heading_line = _match_heading(mapping.location, headings)
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
                path.write_text(clean, encoding="utf-8", newline="\n")
                changed.append(path)
            continue

        output: list[str] = []
        for index, line in enumerate(lines):
            output.append(line)
            rows = links_by_line.get(index)
            if not rows:
                continue
            links = " · ".join(
                f"[[Verification/{verification_name}#^{block_id}|"
                f"{verification_id}]]"
                for verification_id, block_id in sorted(rows)
            )
            output.extend(
                (
                    "",
                    f"Verification: {links}",
                )
            )
            inserted += len(rows)
        updated = "\n".join(output).rstrip() + "\n"
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed.append(path)

    return LinkInsertionResult(
        changed_pages=tuple(changed),
        inserted_links=inserted,
        unresolved_mappings=tuple(unresolved),
    )


def _parse_link_map(text: str) -> tuple[_Mapping, ...]:
    marker = "## Research Link Map"
    if marker not in text:
        raise ValueError("Verification page is missing its Research Link Map.")
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
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
            r"\[\[(?:Protocols/[^/]+/)?(?P<note>[^#|\\\]]+)",
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
            )
        )
    if not mappings:
        raise ValueError("Verification Research Link Map has no usable rows.")
    return tuple(mappings)


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
        ]
        if prefix:
            return prefix[0]
    return None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


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
    return generated_line.sub("", cleaned)
