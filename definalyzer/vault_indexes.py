"""Deterministic Obsidian navigation indexes; no provider calls."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .workflow_status import (
    verification_status_label,
    workflow_status_document,
)
from .workspace import ProjectWorkspace


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
    coins = directory / "Coins.md"
    verification = directory / "Verification.md"

    _write_index(
        home,
        _frontmatter("DEFINALYZER Vault")
        + "# DEFINALYZER Vault\n\n"
        + "- [[Indexes/Research|Research projects]]\n"
        + "- [[Indexes/Tokens|Protocol and project tokens]]\n"
        + "- [[Indexes/Coins|Chain-native coins]]\n"
        + "- [[Indexes/Verification|Verification queue]]\n\n"
        + "Research notes remain usable when verification is unavailable or "
        + "not requested.\n",
    )
    _write_index(research, _research_index(projects, output))
    _write_index(tokens, _token_index(vault, projects))
    _write_index(coins, _coin_index(vault, projects))
    _write_index(verification, _verification_index(projects, vault, output))
    return (home, research, tokens, verification, coins)


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


def _research_index(projects: tuple[dict, ...], root: Path) -> str:
    rows = []
    folders = {"protocol": "Protocols", "chain": "Chains", "token": "Tokens"}
    for project in projects:
        entity_type = str(project.get("entity_type", "protocol"))
        folder = folders.get(entity_type, "Protocols")
        name = str(project["name"])
        try:
            workspace = ProjectWorkspace(
                root=root,
                document=project,
            )
            status = workflow_status_document(workspace)
            ready = int(status["ready_stages"])
            total = int(status["required_stages"])
            verification = str(status["verification_summary"])
            next_action = str(status["next_action"])
        except (KeyError, TypeError, ValueError):
            ready = 0
            total = 0
            verification = str(project.get("verification_status", "unknown"))
            next_action = "Repair the project manifest before continuing."
        rows.append(
            f"| {_table_wikilink(f'{folder}/{name}/Index', name)} | "
            f"{_cell(entity_type.title())} | {ready}/{total} | "
            f"{_cell(verification)} | {_cell(next_action)} |\n"
        )
    return (
        _frontmatter("Research Projects")
        + "# Research Projects\n\n"
        + "| Project | Type | Ready stages | Verification | Next action |\n"
        + "|---|---|---:|---|---|\n"
        + ("".join(rows) or "| None | - | 0/0 | - | - |\n")
    )


def _token_index(vault: Path, projects: tuple[dict, ...]) -> str:
    return _asset_index(
        vault,
        projects,
        section="Tokens",
        entity_type="token",
        parent_keys=("parent_protocol", "parent_project"),
        title="Tokens",
        heading="Protocol and Project Tokens",
        column="Token",
    )


def _coin_index(vault: Path, projects: tuple[dict, ...]) -> str:
    return _asset_index(
        vault,
        projects,
        section="Coins",
        entity_type="coin",
        parent_keys=("parent_chain", "parent_project"),
        title="Coins",
        heading="Chain-Native Coins",
        column="Coin",
    )


def _asset_index(
    vault: Path,
    projects: tuple[dict, ...],
    *,
    section: str,
    entity_type: str,
    parent_keys: tuple[str, ...],
    title: str,
    heading: str,
    column: str,
) -> str:
    rows = []
    parents = {
        str(project.get("name", "")): _entity_folder(
            str(project.get("entity_type", "protocol"))
        )
        for project in projects
    }
    for page in sorted((vault / section).glob("*/Index.md")):
        text = page.read_text(encoding="utf-8")
        if f'entity_type: "{entity_type}"' not in text:
            continue
        symbol = _frontmatter_value(text, "entity") or page.parent.name
        parent = next(
            (
                value
                for key in parent_keys
                if (value := _frontmatter_value(text, key))
            ),
            "Not documented",
        )
        network = _token_network(text) or "Not documented"
        parent_cell = _cell(parent)
        if parent in parents:
            parent_cell = _table_wikilink(
                f"{parents[parent]}/{parent}/Index",
                parent,
            )
        rows.append(
            f"| {_table_wikilink(f'{section}/{page.parent.name}/Index', symbol)} | "
            f"{parent_cell} | {_cell(network)} |\n"
        )
    return (
        _frontmatter(title)
        + f"# {heading}\n\n"
        + f"| {column} | Parent | Network |\n"
        + "|---|---|---|\n"
        + ("".join(rows) or "| None | - | - |\n")
    )


def _verification_index(
    projects: tuple[dict, ...],
    vault: Path,
    root: Path,
) -> str:
    rows = []
    for project in projects:
        name = str(project["name"])
        page = vault / "Verification" / name / "Index.md"
        try:
            status = verification_status_label(
                ProjectWorkspace(root=root, document=project)
            )
        except (KeyError, TypeError, ValueError):
            status = str(project.get("verification_status", "unknown"))
        if page.exists():
            target = _table_wikilink(f"Verification/{name}/Index", name)
            text = page.read_text(encoding="utf-8")
            manual = len(
                re.findall(
                    r"(?mi)^\|\s*Check route\s*\|\s*Manual\s*\|",
                    text,
                )
            )
            if not manual:
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
        + "| Project | Status | Pending | Analyst route |\n"
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


def _table_wikilink(target: str, alias: str) -> str:
    return f"[[{target}\\|{_cell(alias)}]]"


def _entity_folder(entity_type: str) -> str:
    return {
        "protocol": "Protocols",
        "chain": "Chains",
        "token": "Tokens",
    }.get(entity_type, "Protocols")
