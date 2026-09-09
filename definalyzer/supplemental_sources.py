"""Explicit legacy enrichment registrations, separate from subject scoping."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

AAVE_ADDRESS_BOOK_URL = "https://raw.githubusercontent.com/aave-dao/aave-address-book/main/src/AaveV3Ethereum.sol"
AAVE_GRAPHQL_URL = "https://api.v3.aave.com/graphql"
LEGACY_REGISTRATIONS = {"aave-v3": "aave-address-book-and-chains"}


def collect_registered_enrichment(workspace, *, fetch_text, fetch_json):
    registration = LEGACY_REGISTRATIONS.get(workspace.slug)
    if not registration:
        return None
    address_book = fetch_text(AAVE_ADDRESS_BOOK_URL)
    chains = fetch_json(AAVE_GRAPHQL_URL, {"query": "query Chains { chains { name chainId } }"})
    root = workspace.project_root / "supplemental-sources" / registration
    root.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for url, value, suffix in ((AAVE_ADDRESS_BOOK_URL, address_book, "sol"),
                               (AAVE_GRAPHQL_URL, json.dumps(chains, sort_keys=True), "json")):
        raw = value.encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        path = root / f"{digest}.{suffix}"
        if path.exists():
            if path.read_bytes() != raw:
                raise ValueError("Supplemental source snapshot integrity mismatch.")
        else:
            with path.open("xb") as stream:
                stream.write(raw)
        snapshots.append({"url": url, "sha256": digest, "path": path.name})
    record = {"registration": registration, "purpose": "Documented deployment and chain enrichment",
              "selection": "Explicit legacy Aave registration; not inferred by scope classifier",
              "collected_at": datetime.now(timezone.utc).isoformat(), "snapshots": snapshots}
    path = root / "source.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    temporary.replace(path)
    return address_book, chains, [AAVE_ADDRESS_BOOK_URL, AAVE_GRAPHQL_URL]
