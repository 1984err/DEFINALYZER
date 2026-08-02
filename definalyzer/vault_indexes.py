"""Deterministic Obsidian navigation indexes; no provider calls."""

from __future__ import annotations

import json
import re
from pathlib import Path


GENERATED_MARKER = 'generated_by: "definalyzer_vault_index"'


def generate_vault_indexes(root: str | Path) -> tuple[Path, ...]:
    output = Path(root).resolve()
    vault = output / "vault"
    directory = vault / "Indexes"
    directory.mkdir(parents=True, exist_ok=True)
    projects = _projects(output)

    home = directory / "Home.md"
    research = directory / "Research.md"
    tokens = directory / "Tokens.md"
    verification = directory / "Verification.md"

    _write_index(
        home,
        _frontmatter("DEFINALYZER Vault")
        + "# DEFINALYZER Vault\n\n"
        + "- [[Indexes/Research|Research projects]]\n"
        + "- [[Indexes/Tokens|Protocol and chain tokens]]\n"
        + "- [[Indexes/Verification|Verification queue]]\n\n"
        + "Research notes remain usable when verification is unavailable or "
        + "not requested.\n",
    )
    _write_index(research, _research_index(projects))
    _write_index(tokens, _token_index(vault))
    _write_index(verification, _verification_index(projects, vault))
    return (home, research, tokens, verification)


def _projects(root: Path) -> tuple[dict, ...]:
    rows = []
    for path in sorted((root / "projects").glob("*/project.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(document, dict) and isinstance(document.get("name"), str):
            rows.append(document)
    return tuple(rows)


def _research_index(projects: tuple[dict, ...]) -> str:
    rows = []
    folders = {"protocol": "Protocols", "chain": "Chains", "token": "Tokens"}
    for project in projects:
        entity_type = str(project.get("entity_type", "protocol"))
        folder = folders.get(entity_type, "Protocols")
        name = str(project["name"])
        stages = project.get("stages", {})
        complete = sum(
            isinstance(value, dict) and value.get("status") == "complete"
            for value in stages.values()
        ) if isinstance(stages, dict) else 0
        total = len(stages) if isinstance(stages, dict) else 0
        rows.append(
            f"| [[{folder}/{name}/Index\\|{_cell(name)}]] | "
            f"{_cell(entity_type.title())} | {complete}/{total} | "
            f"{_cell(str(project.get('verification_status', 'unknown')))} |\n"
        )
    return (
        _frontmatter("Research Projects")
        + "# Research Projects\n\n"
        + "| Project | Type | Completed stages | Verification |\n"
        + "|---|---|---:|---|\n"
        + ("".join(rows) or "| None | - | 0/0 | - |\n")
    )


def _token_index(vault: Path) -> str:
    rows = []
    for page in sorted((vault / "Tokens").glob("*/Index.md")):
        text = page.read_text(encoding="utf-8")
        if 'entity_type: "token"' not in text:
            continue
        symbol = _frontmatter_value(text, "entity") or page.parent.name
        parent = _frontmatter_value(text, "parent_protocol") or "Not documented"
        network = _token_network(text) or "Not documented"
        rows.append(
            f"| [[Tokens/{page.parent.name}/Index\\|{_cell(symbol)}]] | "
            f"{_cell(parent)} | {_cell(network)} |\n"
        )
    return (
        _frontmatter("Tokens")
        + "# Protocol and Chain Tokens\n\n"
        + "| Token | Parent | Network |\n"
        + "|---|---|---|\n"
        + ("".join(rows) or "| None | - | - |\n")
    )


def _verification_index(projects: tuple[dict, ...], vault: Path) -> str:
    rows = []
    for project in projects:
        name = str(project["name"])
        page = vault / "Verification" / name / "Index.md"
        status = str(project.get("verification_status", "unknown"))
        if page.exists():
            target = f"[[Verification/{name}/Index\\|{_cell(name)}]]"
            text = page.read_text(encoding="utf-8")
            manual = _summary_count(text, "Manual review")
            pending = _summary_count(text, "Pending")
        else:
            target = _cell(name)
            manual = 0
            pending = 0
        rows.append(
            f"| {target} | {_cell(status)} | {pending} | {manual} |\n"
        )
    return (
        _frontmatter("Verification Queue")
        + "# Verification Queue\n\n"
        + "| Project | Status | Pending | Manual review |\n"
        + "|---|---|---:|---:|\n"
        + ("".join(rows) or "| None | - | 0 | 0 |\n")
    )


def _frontmatter(title: str) -> str:
    return (
        "---\n"
        f"{GENERATED_MARKER}\n"
        f'title: "{title.replace(chr(34), chr(39))}"\n'
        "---\n\n"
    )


def _write_index(path: Path, text: str) -> None:
    if path.exists() and GENERATED_MARKER not in path.read_text(encoding="utf-8"):
        raise FileExistsError(f"Refusing to overwrite a user-owned index: {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def _frontmatter_value(text: str, key: str) -> str | None:
    match = re.search(rf'(?m)^{re.escape(key)}:\s*"(?P<value>.*)"\s*$', text)
    return match.group("value") if match else None


def _table_value(text: str, field: str) -> str | None:
    match = re.search(
        rf"(?m)^\|\s*{re.escape(field)}\s*\|\s*(?P<value>.*?)\s*\|$",
        text,
    )
    return match.group("value").strip(" `") if match else None


def _token_network(text: str) -> str | None:
    section = text.partition("## Networks and Addresses")[2]
    if not section:
        return None
    for line in section.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip(" `") for cell in line.strip("|").split("|")]
        if cells and cells[0] != "Network":
            return cells[0]
    return None


def _summary_count(text: str, label: str) -> int:
    match = re.search(
        rf"(?m)^\|\s*{re.escape(label)}\s*\|\s*(?P<count>\d+)\s*\|$",
        text,
    )
    return int(match.group("count")) if match else 0


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
