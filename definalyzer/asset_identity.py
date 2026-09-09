"""Portable asset identities and additive, recoverable legacy migration.

The catalog is the commit point. Existing research/registries/reports are never
rewritten by migration. OS locks release on process exit; transaction after-images
allow a killed writer to finish without choosing new identities on restart.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading
from functools import wraps
from uuid import uuid4

from .workspace import ProjectWorkspace, slugify

_LOCK = threading.RLock()
_REGISTRY_LOCKS = {}
ID = re.compile(r"^[a-f0-9]{32}$")
MISSING = {"", "-", "none", "unknown", "not documented", "not applicable", "n/a"}
CHAINS = {"ethereum": "eip155:1", "arbitrum": "eip155:42161",
          "arbitrum one": "eip155:42161", "base": "eip155:8453",
          "optimism": "eip155:10", "solana": "solana:mainnet",
          "near": "near:mainnet"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def safe_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise ValueError("Asset path escapes workspace.")
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("Asset storage cannot traverse filesystem links.")
    return path


def load_catalog(root: Path) -> dict:
    path = safe_path(root, "entities/catalog.json")
    if not path.exists():
        return {"schema_version": 1, "entities": {}, "projects": {}, "page_hashes": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported asset catalog schema.")
    for key in ("entities", "projects", "page_hashes"):
        if not isinstance(data.get(key), dict):
            raise ValueError("Invalid asset catalog.")
    for identifier, entity in data["entities"].items():
        if not ID.fullmatch(identifier) or entity.get("entity_id") != identifier:
            raise ValueError("Invalid stable asset ID.")
        safe_path(root, entity["path"])
    return data


def _atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def registry_writer(function):
    """Keep read/merge/write atomic against other registry jobs for this project."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        workspace = kwargs.get("workspace") or args[0]
        with _LOCK:
            local = _REGISTRY_LOCKS.setdefault(str(workspace.project_root), threading.Lock())
        if not local.acquire(blocking=False):
            raise RuntimeError("Another registry operation is running for this project.")
        try:
            path = safe_path(workspace.root, f"projects/{workspace.slug}/.asset-registry.lock")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a+b") as stream:
                stream.seek(0, 2)
                if not stream.tell():
                    stream.write(b"0")
                    stream.flush()
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    return function(*args, **kwargs)
                finally:
                    stream.seek(0)
                    if os.name == "nt":
                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(stream, fcntl.LOCK_UN)
        finally:
            local.release()
    return wrapped


@contextmanager
def _locked(root):
    with _LOCK:
        path = safe_path(root, "entities/.write.lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as stream:
            stream.seek(0, 2)
            if not stream.tell():
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                _recover(root)
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)


def _recover(root):
    pending = safe_path(root, "entities/pending.json")
    if not pending.exists():
        return
    transaction = json.loads(pending.read_text(encoding="utf-8"))
    # Never overwrite a file edited since the plan was committed.
    for item in transaction["writes"]:
        path = safe_path(root, item["path"])
        current = _digest(path.read_text(encoding="utf-8")) if path.exists() else None
        if current not in {item["before_sha256"], _digest(item["text"])}:
            raise ValueError(f"Asset recovery needs review of edited file: {item['path']}")
    for item in transaction["writes"]:
        path = safe_path(root, item["path"])
        if not path.exists() or _digest(path.read_text(encoding="utf-8")) != _digest(item["text"]):
            _atomic(path, item["text"])
    # Catalog is deliberately the final write in the transaction.
    pending.unlink()


def _commit(root, catalog, pages):
    transaction_id = uuid4().hex
    writes = []
    for relative, content in pages.items():
        path = safe_path(root, relative)
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing == content:
            continue
        known = catalog["page_hashes"].get(relative)
        if existing is not None and _digest(existing) != known:
            # Keep user prose and make the proposed regeneration reviewable.
            relative += ".proposed.md"
            path = safe_path(root, relative)
            existing = path.read_text(encoding="utf-8") if path.exists() else None
            if existing is not None and existing != content:
                relative += "." + transaction_id + ".md"
                path = safe_path(root, relative)
                existing = None
        else:
            catalog["page_hashes"][relative] = _digest(content)
        writes.append({"path": relative, "text": content,
                       "before_sha256": _digest(existing) if existing is not None else None})
    old = safe_path(root, "entities/catalog.json")
    old_text = old.read_text(encoding="utf-8") if old.exists() else None
    catalog_text = _json(catalog)
    if old_text == catalog_text and not writes:
        return
    writes.append({"path": "entities/catalog.json", "text": catalog_text,
                   "before_sha256": _digest(old_text) if old_text else None})
    history = safe_path(root, f"entities/history/{transaction_id}")
    history.mkdir(parents=True)
    for index, item in enumerate(writes):
        path = safe_path(root, item["path"])
        if path.exists():
            (history / f"before-{index}.txt").write_bytes(path.read_bytes())
    transaction = {"id": transaction_id, "created_at": _now(), "writes": writes}
    _atomic(history / "transaction.json", _json(transaction))
    _atomic(safe_path(root, "entities/pending.json"), _json(transaction))
    _recover(root)


def asset_kind(row, project_type="protocol"):
    if row.get("asset_kind") in {"token", "coin"}:
        return row["asset_kind"]
    description = str(row.get("token_type", "")).casefold()
    if project_type == "coin" or (project_type == "chain" and
            any(word in description for word in ("native", "coin", "gas")) and
            str(row.get("address", "")).casefold() in MISSING):
        return "coin"
    return "token"


def deployment_key(row):
    network = str(row.get("network") or "").strip().casefold()
    address = str(row.get("address") or "").strip()
    if address.casefold() in MISSING or not network or network in MISSING or ";" in network:
        return None
    chain = CHAINS.get(network, "documented:" + network)
    # Only EVM addresses are case-insensitive.
    if re.fullmatch(r"0x[a-fA-F0-9]{40}", address):
        address = address.lower()
    return (chain, address)


def _same_local(left, right):
    if left.get("asset_id") and right.get("asset_id"):
        return left["asset_id"] == right["asset_id"]
    lk, rk = deployment_key(left), deployment_key(right)
    if lk and rk:
        return lk == rk
    ln, rn = str(left.get("network", "")).casefold(), str(right.get("network", "")).casefold()
    if ln not in MISSING and rn not in MISSING and ";" not in ln + rn and CHAINS.get(ln, ln) != CHAINS.get(rn, rn):
        return False
    return (str(left.get("name", "")).casefold(), str(left.get("symbol", "")).casefold()) == (
        str(right.get("name", "")).casefold(), str(right.get("symbol", "")).casefold())


def merge_tokens(existing, discovered, *, manual=False):
    """Never replace by ticker; discoveries cannot overwrite a manual record."""
    result = list(existing)
    for candidate in discovered:
        matches = [i for i, row in enumerate(result) if _same_local(asdict(row), asdict(candidate))]
        if len(matches) > 1:
            raise ValueError("Asset identity is ambiguous; select its stable asset ID.")
        if matches:
            index = matches[0]
            old = result[index]
            if old.origin == "manual" and not manual:
                continue
            result[index] = replace(candidate, asset_id=old.asset_id,
                                    origin="manual" if manual else candidate.origin)
        else:
            result.append(replace(candidate, origin="manual" if manual else candidate.origin))
    return tuple(result)


def _label(entity):
    name, symbol = entity["name"], entity["symbol"]
    return f"{name} ({symbol})" if name != symbol else name


def _escape(value):
    return re.sub(r"[\[\]<>|\r\n]", " ", str(value)).strip()


def _overview(entity, catalog):
    title = _escape(_label(entity))
    lines = ["---", 'generated_by: "definalyzer_asset_identity"',
             f'asset_id: "{entity["entity_id"]}"', f'entity_type: "{entity["kind"]}"',
             "---", "", f"# {title}", "", "## Identity", "",
             f"- Name: {_escape(entity['name'])}", f"- Symbol: {_escape(entity['symbol'])}",
             f"- Identity: {entity['identity_status']}", "", "## Networks and Addresses", "",
             "| Network | Address | Source |", "|---|---|---|"]
    for deployment in entity["deployments"]:
        lines.append(f"| {_escape(deployment['network'])} | `{_escape(deployment['address'])}` | {_escape(deployment['source'])} |")
    if not entity["deployments"]:
        lines.append("| Not documented | Not documented | Not documented |")
    lines.extend(["", "## Related Research", ""])
    for slug, context in sorted(entity["contexts"].items()):
        project = catalog["projects"].get(slug)
        if project is None:
            continue
        target = context["page"].removeprefix("vault/").removesuffix(".md")
        if project.get("archived"):
            lines.append(f"- [[{target}|Archived research from {_escape(project['name'])}]]")
            continue
        project_target = project["page"].removeprefix("vault/").removesuffix(".md")
        lines.append(f"- [[{project_target}|{_escape(project['name'])}]]: {_escape(context['record'].get('protocol_relationship', ''))}")
        lines.append(f"  [[{target}|Documented mechanics and evidence from {_escape(project['name'])}]]")
    lines.extend(["", "Identity and documented relationships are not independent verification.", ""])
    return "\n".join(lines)


def _register(catalog, workspace, rows):
    slug = workspace.slug
    project = catalog["projects"].setdefault(slug, {
        "subject_id": workspace.document.get("subject_id") or uuid4().hex,
        "name": workspace.name, "kind": workspace.document["entity_type"],
        "page": workspace.vault_entity_directory.relative_to(workspace.root).as_posix() + "/Index.md",
        "assets": []})
    result = []
    for row in rows:
        symbol = str(row.get("symbol", ""))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,19}", symbol):
            raise ValueError("Invalid asset symbol.")
        kind = asset_kind(row, project["kind"])
        identifier = row.get("asset_id") or ""
        if identifier and (not ID.fullmatch(identifier) or identifier not in catalog["entities"]):
            raise ValueError("Unknown asset ID; choose an existing asset or leave it blank.")
        if identifier and identifier not in project["assets"] and project["subject_id"] != identifier:
            raise ValueError("Asset ID is not associated with this project.")
        if not identifier:
            candidates = [eid for eid in project["assets"]
                          if _same_local(catalog["entities"][eid]["contexts"][slug]["record"], row)]
            if len(candidates) == 1:
                identifier = candidates[0]
            elif len(candidates) > 1:
                raise ValueError("Ambiguous asset identity.")
        if not identifier and deployment_key(row):
            candidates = [eid for eid, entity in catalog["entities"].items()
                          if entity["kind"] == kind and entity["name"].casefold() == row["name"].casefold()
                          and entity["symbol"].casefold() == symbol.casefold()
                          and any(deployment_key(c["record"]) == deployment_key(row)
                                  for c in entity["contexts"].values())]
            if len(candidates) == 1:
                identifier = candidates[0]
        if not identifier:
            identifier = uuid4().hex
            directory = f"vault/{'Coins' if kind == 'coin' else 'Tokens'}/{slugify(row['name'])}--{identifier}"
            catalog["entities"][identifier] = {
                "entity_id": identifier, "name": row["name"], "symbol": symbol,
                "kind": kind, "aliases": [], "identity_status": "documented" if deployment_key(row) else "provisional",
                "path": directory + "/Index.md", "deployments": [], "contexts": {}}
        entity = catalog["entities"][identifier]
        if entity["kind"] != kind:
            raise ValueError("Asset kind conflicts with its existing identity.")
        if row.get("origin") == "manual" and entity["name"] != row["name"]:
            entity["aliases"] = sorted(set(entity["aliases"] + [entity["name"]]))
            entity["name"] = row["name"]
            entity["symbol"] = symbol
        assigned = {**row, "asset_id": identifier, "asset_kind": kind}
        context = entity["contexts"].get(slug, {})
        page = entity["path"].removesuffix("Index.md") + f"Contexts/{slug}.md"
        history = context.get("history", [])
        if context.get("record") and context["record"] != assigned:
            history = history + [context["record"]]
        entity["contexts"][slug] = {"page": page, "record": assigned, "history": history}
        key = deployment_key(row)
        if key and not any((d["chain_ref"], d["normalized_address"]) == key for d in entity["deployments"]):
            entity["deployments"].append({"deployment_id": uuid4().hex, "chain_ref": key[0],
                "normalized_address": key[1], "network": row["network"], "address": row["address"],
                "source": row["source"]})
        elif kind == "coin" and not entity["deployments"]:
            entity["deployments"].append({"deployment_id": uuid4().hex, "chain_ref": None,
                "normalized_address": None, "network": row.get("network"), "address": "Native (no contract)",
                "source": row["source"]})
        if identifier not in project["assets"]:
            project["assets"].append(identifier)
        if project["kind"] in {"token", "coin"} and len(rows) == 1 and (
                workspace.document.get("subject_id") == identifier or
                workspace.name.casefold() in {row["name"].casefold(), symbol.casefold(), _label(entity).casefold()}):
            project["subject_id"] = identifier
        result.append(assigned)
    return result


def register_tokens(workspace, tokens):
    with _locked(workspace.root):
        catalog = load_catalog(workspace.root)
        rows = _register(catalog, workspace, [asdict(t) for t in tokens])
        pages = {e["path"]: _overview(e, catalog) for e in catalog["entities"].values()
                 if workspace.slug in e["contexts"]}
        _commit(workspace.root, catalog, pages)
    return tuple(replace(token, asset_id=row["asset_id"], asset_kind=row["asset_kind"])
                 for token, row in zip(tokens, rows))


def resolve_asset(workspace, row):
    catalog = load_catalog(workspace.root)
    project = catalog["projects"].get(workspace.slug, {})
    matches = [catalog["entities"][eid] for eid in project.get("assets", [])
               if _same_local(catalog["entities"][eid]["contexts"][workspace.slug]["record"], row)]
    return matches[0] if len(matches) == 1 else None


def asset_page(workspace, row, *, context=False):
    entity = resolve_asset(workspace, row)
    if entity:
        relative = entity["contexts"][workspace.slug]["page"] if context else entity["path"]
        return safe_path(workspace.root, relative)
    symbol = str(row.get("symbol", ""))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,19}", symbol):
        return None
    section = "Coins" if asset_kind(row, workspace.document["entity_type"]) == "coin" else "Tokens"
    if workspace.document["entity_type"] == "chain" and not row.get("token_type") and not row.get("asset_kind"):
        legacy_coin = safe_path(workspace.root, f"vault/Coins/{symbol}/Index.md")
        if legacy_coin.exists() and 'entity_type: "coin"' in legacy_coin.read_text(encoding="utf-8"):
            section = "Coins"
    path = safe_path(workspace.root, f"vault/{section}/{symbol}/Index.md")
    if path.exists():
        text = path.read_text(encoding="utf-8")
        parent = re.search(r'^parent_(?:protocol|chain):\s*"([^"\n]+)"', text, re.M)
        if parent and parent.group(1) != workspace.name:
            return None
    return path


def project_asset_pages(workspace):
    registry = workspace.registry_directory / "registry.json"
    if not registry.exists():
        return ()
    document = json.loads(registry.read_text(encoding="utf-8"))
    return tuple(dict.fromkeys(page for row in document.get("tokens", []) if isinstance(row, dict)
                              if (page := asset_page(workspace, row, context=True)) and page.exists()))


def save_context_page(workspace, token, text):
    with _locked(workspace.root):
        catalog = load_catalog(workspace.root)
        entity = catalog["entities"][token.asset_id]
        relative = entity["contexts"][workspace.slug]["page"]
        _commit(workspace.root, catalog, {relative: text, entity["path"]: _overview(entity, catalog)})
        return safe_path(workspace.root, relative)


def inventory(root):
    catalog = load_catalog(root)
    result = []
    for entity in catalog["entities"].values():
        projects = [s for s in entity["contexts"] if s in catalog["projects"]
                    and safe_path(root, f"projects/{s}/project.json").exists()]
        if not projects:
            continue
        result.append({"asset_id": entity["entity_id"], "symbol": entity["symbol"],
                       "title": _label(entity), "name": entity["name"], "aliases": entity["aliases"],
                       "kind": entity["kind"], "path": entity["path"].removeprefix("vault/"),
                       "projects": projects, "subject_projects": [s for s in projects
                         if catalog["projects"][s]["subject_id"] == entity["entity_id"]],
                       "contexts": [{"path": entity["contexts"][s]["page"].removeprefix("vault/"),
                                     "title": catalog["projects"][s]["name"], "group": "Related research",
                                     "project": s, "record": entity["contexts"][s]["record"]}
                                    for s in projects]})
    counts = {}
    for row in result:
        counts[row["title"]] = counts.get(row["title"], 0) + 1
    for row in result:
        if counts[row["title"]] > 1:
            row["title"] += " — " + ", ".join(catalog["projects"][s]["name"] for s in row["projects"])
    return sorted(result, key=lambda row: row["title"].casefold())


def _project_workspaces(manager):
    # WorkspaceManager.load_project also performs a legacy verification migration.
    # An identity preview must not trigger those unrelated writes.
    rows = []
    for path in sorted((manager.root / "projects").glob("*/project.json")):
        path = safe_path(manager.root, path.relative_to(manager.root).as_posix())
        document = json.loads(path.read_text(encoding="utf-8"))
        manager._validate_document(document)
        rows.append(ProjectWorkspace(manager.root, document))
    return rows


def migrate_assets(manager, *, preview=True):
    workspaces = _project_workspaces(manager)
    def build(catalog):
        pages, notes = {}, []
        for workspace in workspaces:
            registry = workspace.registry_directory / "registry.json"
            if not registry.exists():
                continue
            document = json.loads(registry.read_text(encoding="utf-8"))
            rows = document.get("tokens", [])
            if not isinstance(rows, list):
                raise ValueError(f"Invalid registry: {workspace.slug}")
            if document.get("token_discovery_status") == "manual_entries":
                rows = [{"origin": "manual", **row} for row in rows]
            assigned = _register(catalog, workspace, rows)
            for row in assigned:
                entity = catalog["entities"][row["asset_id"]]
                context = entity["contexts"][workspace.slug]["page"]
                if safe_path(workspace.root, context).exists():
                    continue
                section = "Coins" if row["asset_kind"] == "coin" else "Tokens"
                legacy = safe_path(workspace.root, f"vault/{section}/{row['symbol']}/Index.md")
                content = legacy.read_text(encoding="utf-8") if legacy.exists() else ""
                parent = re.search(r'^parent_(?:protocol|chain):\s*"([^"\n]+)"', content, re.M)
                if content and parent and parent.group(1) == workspace.name:
                    # Byte-preserving legacy copy; V1 report sources remain untouched.
                    pages[context] = content
                else:
                    notes.append(f"{workspace.slug}/{row['symbol']}: legacy page missing or ownership uncertain; registry-backed context created.")
                    lines = [f"# {_escape(_label(entity))}", "", "## Documented Registry", "",
                             "| Field | Value |", "|---|---|"]
                    lines.extend(f"| {_escape(key.replace('_', ' ').title())} | {_escape(value)} |"
                                 for key, value in row.items() if key not in {"asset_id", "origin", "asset_kind"})
                    lines.extend(["", "Legacy page ownership could not be established. Values above are preserved registry data, not newly verified facts.", ""])
                    pages[context] = "\n".join(lines)
        pages.update({e["path"]: _overview(e, catalog) for e in catalog["entities"].values()})
        return pages, notes
    if preview:
        catalog = deepcopy(load_catalog(manager.root))
        pages, notes = build(catalog)
        return {"preview": True, "assets": len(catalog["entities"]), "projects": len(catalog["projects"]),
                "planned_pages": len(pages), "notes": notes,
                "identities": [{"name": e["name"], "symbol": e["symbol"], "kind": e["kind"],
                                "projects": sorted(e["contexts"])} for e in catalog["entities"].values()]}
    with _locked(manager.root):
        catalog = load_catalog(manager.root)
        pages, notes = build(catalog)
        _commit(manager.root, catalog, pages)
    return {"preview": False, "assets": len(catalog["entities"]), "projects": len(catalog["projects"]),
            "notes": notes, "catalog": str(manager.root / "entities/catalog.json")}


def start_asset_research(manager, asset_id):
    """Explicit, idempotent creation; no crawl or AI call and no inferred sources."""
    with _locked(manager.root):
        catalog = load_catalog(manager.root)
        if not ID.fullmatch(asset_id) or asset_id not in catalog["entities"]:
            raise ValueError("Asset was not found.")
        for slug, project in catalog["projects"].items():
            if project["subject_id"] == asset_id and safe_path(manager.root, f"projects/{slug}/project.json").exists():
                return manager.load_project(slug)
        entity = catalog["entities"][asset_id]
        name = _label(entity)
        if (manager.root / "projects" / slugify(name) / "project.json").exists():
            name += " " + asset_id[:8]
        # If a process stopped after creating the manifest, reuse that exact ID.
        existing = next((w for w in _project_workspaces(manager) if w.document.get("subject_id") == asset_id), None)
        workspace = existing or manager.create_project(name=name, entity_type=entity["kind"], subject_id=asset_id)
        records = list(entity["contexts"].values())
        row = deepcopy(records[0]["record"])
        row["asset_id"] = asset_id
        assigned = _register(catalog, workspace, [row])[0]
        pages = {entity["path"]: _overview(entity, catalog),
                 f"registries/{workspace.slug}/registry.json": _json({
                     "schema_version": 1, "entity": workspace.name, "entity_type": entity["kind"],
                     "tokens": [assigned], "addresses": [], "networks": [],
                     "source_contexts": [r["page"] for r in records]})}
        context_path = entity["contexts"][workspace.slug]["page"]
        source_target = records[0]["page"].removeprefix("vault/").removesuffix(".md")
        pages[context_path] = (f"# {_escape(name)}\n\n"
            f"Identity and documented mechanics were registered from [[{source_target}|existing sourced research]].\n\n"
            "Add official asset documentation in Project Controls before analyzing this asset. "
            "Creating this research context has not collected sources or verified any claims.\n")
        _commit(manager.root, catalog, pages)
        return workspace


def archive_project_context(root, slug):
    """Retain shared context records after the project is removed from navigation."""
    if slug not in load_catalog(root)["projects"]:
        return
    with _locked(root):
        catalog = load_catalog(root)
        catalog["projects"][slug]["archived"] = True
        pages = {e["path"]: _overview(e, catalog) for e in catalog["entities"].values()
                 if slug in e["contexts"]}
        _commit(root, catalog, pages)
