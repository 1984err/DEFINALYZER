"""Registry-stage entity discovery, enrichment, and Obsidian linking."""

from __future__ import annotations

import json
import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

from .extraction import research_source_files
from .market_data import MarketSnapshot, load_market_snapshot
from .providers import TextProvider
from .source_coverage import (
    ensure_source_coverage,
    token_coverage_complete,
)
from .workspace import ProjectWorkspace


AAVE_ADDRESS_BOOK_URL = (
    "https://raw.githubusercontent.com/aave-dao/"
    "aave-address-book/main/src/AaveV3Ethereum.sol"
)
AAVE_GRAPHQL_URL = "https://api.v3.aave.com/graphql"
TOKEN_SCOPE = (
    "Include only the protocol's native/governance token and tokens issued by "
    "the protocol with their own material economics. Exclude reserve assets, "
    "collateral assets, external dependencies, generic reward assets, aTokens, "
    "debt tokens, vault shares, wrappers, receipt tokens, LP tokens, and "
    "assets created by protocol users."
)
PLACEHOLDER_IDENTITIES = {
    "-",
    "n/a",
    "none",
    "not applicable",
    "not documented",
    "tbd",
    "unknown",
}
AAVE_CORE_COMPONENTS = frozenset(
    {
        "POOL_ADDRESSES_PROVIDER",
        "POOL",
        "POOL_CONFIGURATOR",
        "ORACLE",
        "ACL_ADMIN",
        "ACL_MANAGER",
        "AAVE_PROTOCOL_DATA_PROVIDER",
        "POOL_IMPL",
        "POOL_CONFIGURATOR_IMPL",
        "DEFAULT_INCENTIVES_CONTROLLER",
        "EMISSION_MANAGER",
        "COLLECTOR",
        "DEFAULT_A_TOKEN_IMPL",
        "DEFAULT_VARIABLE_DEBT_TOKEN_IMPL",
        "RISK_STEWARD",
        "CONFIG_ENGINE",
        "POOL_ADDRESSES_PROVIDER_REGISTRY",
        "GHO_DIRECT_MINTER",
    }
)
DOCUMENTED_CHAINS = {
    "arbitrum": ("Arbitrum", 42161),
    "base": ("Base", 8453),
    "ethereum": ("Ethereum", 1),
    "plasma": ("Plasma", None),
    "solana": ("Solana", None),
}
AUTO_COLLECTOR_CHAINS = {"Arbitrum", "Base", "Ethereum"}
EVM_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
SOLANA_ADDRESS_PATTERN = re.compile(
    r"(?<![1-9A-HJ-NP-Za-km-z])"
    r"[1-9A-HJ-NP-Za-km-z]{32,44}"
    r"(?![1-9A-HJ-NP-Za-km-z])"
)


@dataclass(frozen=True)
class TokenRecord:
    name: str
    symbol: str
    token_type: str
    protocol_relationship: str
    network: str
    standard: str
    address: str
    supply: str
    maximum_supply: str
    circulating_supply: str
    emissions: str
    allocation: str
    unlocks: str
    mint_authority: str
    utility: str
    source: str


@dataclass(frozen=True)
class AddressRecord:
    name: str
    component_type: str
    role: str
    address: str
    chain: str
    chain_id: int | None
    deployment_block: int | None
    status: str
    source: str
    provenance: str


@dataclass(frozen=True)
class RegistryResult:
    registry_path: Path
    network_page: Path | None
    token_pages: tuple[Path, ...]
    linked_pages: tuple[Path, ...]
    tokens: tuple[TokenRecord, ...]
    addresses: tuple[AddressRecord, ...]
    address_page: Path | None


def run_registry_workflow(
    *,
    workspace: ProjectWorkspace,
    provider: TextProvider | None,
    fetch_text: Callable[[str], str] | None = None,
    fetch_json: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> RegistryResult:
    tokenomics = workspace.vault_entity_directory / "Tokenomics.md"
    if not tokenomics.exists():
        raise FileNotFoundError(
            "Tokenomics research page is required before registry generation."
        )

    registry_path = workspace.registry_directory / "registry.json"
    tokens = list(_clear_previous_address_enrichment(_load_existing_tokens(registry_path)))
    discovery_complete = _token_discovery_complete(
        registry_path,
        coverage_complete=token_coverage_complete(workspace),
        tokenomics_digest=_file_digest(tokenomics),
    )
    if not tokens and not discovery_complete:
        if provider is None:
            raise RuntimeError(
                "An AI provider is required for initial token discovery."
            )
        tokens = list(
            discover_native_tokens(
                provider=provider,
                tokenomics=tokenomics.read_text(encoding="utf-8"),
                working_directory=workspace.project_root,
            )
        )
    networks: list[dict[str, Any]] = []
    addresses = list(_extract_documented_addresses(workspace.sources_directory))
    addresses.extend(
        _extract_token_catalog_addresses(workspace.sources_directory, tokens)
    )
    network_page: Path | None = None
    address_page: Path | None = None
    sources: list[str] = []

    if workspace.slug == "aave-v3":
        text_fetcher = fetch_text or _fetch_text
        json_fetcher = fetch_json or _fetch_json
        address_book = text_fetcher(AAVE_ADDRESS_BOOK_URL)
        tokens = list(_enrich_aave_tokens(tokens, address_book))
        addresses.extend(_parse_aave_core_addresses(address_book))
        network_response = json_fetcher(
            AAVE_GRAPHQL_URL,
            {"query": "query Chains { chains { name chainId } }"},
        )
        networks = _parse_aave_chains(network_response)
        sources.extend((AAVE_ADDRESS_BOOK_URL, AAVE_GRAPHQL_URL))
        network_page = _write_network_page(workspace, networks)

    addresses = list(_merge_address_records(addresses))
    tokens = list(_enrich_tokens_from_documented_addresses(tokens, addresses))
    if addresses:
        address_page = _write_address_page(workspace, addresses)

    registry_document = {
        "schema_version": 1,
        "entity": workspace.name,
        "entity_type": workspace.document["entity_type"],
        "generated_at": _timestamp(),
        "tokenomics_digest": _file_digest(tokenomics),
        "token_discovery_status": (
            "complete"
            if token_coverage_complete(workspace)
            else "incomplete_source_coverage"
        ),
        "source_coverage": ensure_source_coverage(workspace).status,
        "scope": (
            "Protocol-native/governance and protocol-issued economic tokens "
            "only; external and reserve assets excluded."
        ),
        "tokens": [asdict(token) for token in tokens],
        "addresses": [asdict(address) for address in addresses],
        "networks": networks,
        "sources": sources,
    }
    _write_generated_json(registry_path, registry_document)

    token_pages = tuple(
        _write_token_page(workspace, token, addresses) for token in tokens
    )
    _remove_stale_token_pages(workspace, tokens)
    linked_pages = link_token_references(
        workspace.vault_entity_directory,
        tokens,
    )
    _update_protocol_index(
        workspace,
        tokens,
        network_page,
        address_page,
    )
    return RegistryResult(
        registry_path=registry_path,
        network_page=network_page,
        token_pages=token_pages,
        linked_pages=linked_pages,
        tokens=tuple(tokens),
        addresses=tuple(addresses),
        address_page=address_page,
    )


def discover_native_tokens(
    *,
    provider: TextProvider,
    tokenomics: str,
    working_directory: Path,
) -> tuple[TokenRecord, ...]:
    prompt = (
        "# Native and Protocol-Issued Token Discovery\n\n"
        f"{TOKEN_SCOPE}\n\n"
        "Use only the supplied Tokenomics page. Do not use prior knowledge. "
        "A qualifying token must have a specifically documented name or "
        "symbol and protocol-level economics. Tokens created by users of the "
        "protocol do not qualify merely because the protocol creates them. "
        "If no qualifying token is documented, return exactly "
        '{"tokens":[]}. Never create a placeholder token. '
        "Return strict JSON with this shape:\n"
        '{"tokens":[{"name":"","symbol":"","token_type":"",'
        '"protocol_relationship":"","network":"Not documented",'
        '"standard":"Not documented","address":"Not documented",'
        '"supply":"Not documented","maximum_supply":"Not documented",'
        '"circulating_supply":"Not documented","emissions":"Not documented",'
        '"allocation":"Not documented","unlocks":"Not documented",'
        '"mint_authority":"Not documented","utility":"Not documented",'
        '"source":"Tokenomics.md"}]}\n\n'
        "Use one object per qualifying token. Keep fields concise. Do not "
        "include Markdown or commentary.\n\n"
        "---\n\n"
        f"{tokenomics.strip()}\n"
    )
    response = provider.generate(prompt, working_directory=working_directory)
    document = _parse_json_object(response.text)
    rows = document.get("tokens")
    if not isinstance(rows, list):
        raise ValueError("Token discovery output must contain a tokens list.")

    tokens = []
    seen = set()
    required = tuple(TokenRecord.__dataclass_fields__)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each discovered token must be a JSON object.")
        values = {}
        for field in required:
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Discovered token has invalid field {field!r}."
                )
            values[field] = value.strip()
        symbol = values["symbol"].upper()
        if (
            values["name"].casefold() in PLACEHOLDER_IDENTITIES
            or symbol.casefold() in PLACEHOLDER_IDENTITIES
        ):
            continue
        if symbol in seen:
            continue
        seen.add(symbol)
        values["symbol"] = symbol
        tokens.append(TokenRecord(**values))
    return tuple(tokens)


def link_token_references(
    protocol_directory: Path,
    tokens: list[TokenRecord] | tuple[TokenRecord, ...],
) -> tuple[Path, ...]:
    changed: list[Path] = []
    for path in sorted(protocol_directory.glob("*.md")):
        if path.name in {"Index.md", "Networks.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        lines = [_normalize_table_wikilinks(line) for line in text.splitlines()]
        for token in tokens:
            plain_link = f"[[Tokens/{token.symbol}/Index|{token.symbol}]]"
            table_link = (
                f"[[Tokens/{token.symbol}/Index\\|{token.symbol}]]"
            )
            if any(plain_link in line or table_link in line for line in lines):
                continue
            pattern = re.compile(
                rf"(?<![/\w\[\]|]){re.escape(token.symbol)}"
                rf"(?![/\w\[\]|])"
            )
            for index, line in enumerate(lines):
                if not pattern.search(line):
                    continue
                link = table_link if _is_markdown_table_row(line) else plain_link
                lines[index] = pattern.sub(lambda _: link, line, count=1)
                break
        lines = _remove_empty_trailing_table_columns(lines)
        updated = "\n".join(lines)
        if text.endswith("\n"):
            updated += "\n"
        if updated != text:
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed.append(path)
    return tuple(changed)


def _enrich_aave_tokens(
    tokens: list[TokenRecord],
    address_book: str,
) -> tuple[TokenRecord, ...]:
    addresses = {
        match.group("symbol"): match.group("address")
        for match in re.finditer(
            r"(?P<symbol>AAVE|GHO)_UNDERLYING\s*=\s*"
            r"(?P<address>0x[a-fA-F0-9]{40})",
            address_book,
        )
    }
    by_symbol = {token.symbol: token for token in tokens}
    official_defaults = {
        "AAVE": TokenRecord(
            name="Aave",
            symbol="AAVE",
            token_type="Governance and incentive token",
            protocol_relationship="Aave governance and protocol incentive token",
            network="Not documented",
            standard="Not documented",
            address="Not documented",
            supply="Not documented",
            maximum_supply="Not documented",
            circulating_supply="Not documented",
            emissions="Not documented",
            allocation="Not documented",
            unlocks="Not documented",
            mint_authority="Not documented",
            utility="Governance and documented protocol incentives",
            source="Tokenomics.md",
        ),
        "GHO": TokenRecord(
            name="GHO",
            symbol="GHO",
            token_type="Protocol-issued stablecoin",
            protocol_relationship="Stablecoin issued by the Aave protocol",
            network="Not documented",
            standard="Not documented",
            address="Not documented",
            supply="Not documented",
            maximum_supply="Not documented",
            circulating_supply="Not documented",
            emissions="Not documented",
            allocation="Not documented",
            unlocks="Not documented",
            mint_authority="Not documented",
            utility="Borrowable protocol asset and documented Umbrella staking asset",
            source="Tokenomics.md",
        ),
    }
    # The official Aave registry may add only these scoped, protocol-issued
    # economic tokens. Reserve and dependency tokens remain excluded.
    for symbol in addresses:
        if symbol not in by_symbol:
            by_symbol[symbol] = official_defaults[symbol]

    enriched = []
    for token in by_symbol.values():
        address = addresses.get(token.symbol, token.address)
        source = token.source
        if token.symbol in addresses:
            source = f"{source}; {AAVE_ADDRESS_BOOK_URL}"
        classification = {}
        if token.symbol == "AAVE":
            classification = {
                "token_type": "Governance and incentive token",
                "protocol_relationship": (
                    "Aave governance and protocol incentive token"
                ),
            }
        enriched.append(
            TokenRecord(
                **{
                    **asdict(token),
                    **classification,
                    "network": (
                        "Ethereum" if token.symbol in addresses else token.network
                    ),
                    "standard": (
                        "ERC-20" if token.symbol in addresses else token.standard
                    ),
                    "address": address,
                    "source": source,
                }
            )
        )
    return tuple(enriched)


def _parse_aave_chains(document: dict[str, Any]) -> list[dict[str, Any]]:
    data = document.get("data")
    rows = data.get("chains") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError("Aave chains response is missing data.chains.")
    parsed = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name, chain_id = row.get("name"), row.get("chainId")
        if not isinstance(name, str) or isinstance(chain_id, bool):
            continue
        if not isinstance(chain_id, int):
            continue
        parsed.append(
            {
                "name": name,
                "chain_id": chain_id,
                "environment": (
                    "testnet" if "sepolia" in name.lower() else "production"
                ),
                "status": "API-supported; active market not verified",
                "source": AAVE_GRAPHQL_URL,
            }
        )
    return sorted(parsed, key=lambda row: row["name"].lower())


def _parse_aave_core_addresses(address_book: str) -> tuple[AddressRecord, ...]:
    core_library = address_book.split(
        "library AaveV3EthereumAssets", 1
    )[0]
    pattern = re.compile(
        r"(?:[A-Za-z_][A-Za-z0-9_]*|address)\s+internal\s+constant\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
        r"(?:[A-Za-z_][A-Za-z0-9_]*\s*\(\s*)?"
        r"(?P<address>0x[a-fA-F0-9]{40})",
        re.MULTILINE,
    )
    records = []
    for match in pattern.finditer(core_library):
        name = match.group("name")
        if name not in AAVE_CORE_COMPONENTS:
            continue
        component_type, role = _classify_aave_component(name)
        records.append(
            AddressRecord(
                name=name,
                component_type=component_type,
                role=role,
                address=match.group("address"),
                chain="Ethereum",
                chain_id=1,
                deployment_block=None,
                status="published_current",
                source=AAVE_ADDRESS_BOOK_URL,
                provenance="official_registry",
            )
        )
    return tuple(records)


def _classify_aave_component(name: str) -> tuple[str, str]:
    if name.endswith("_IMPL"):
        return "Implementation", "Published implementation contract"
    if "ORACLE" in name:
        return "Oracle", "Protocol price-oracle component"
    if "ACL" in name or name == "EMISSION_MANAGER":
        return "Administrative role", "Protocol access-control component"
    if name == "COLLECTOR":
        return "Treasury or fee destination", "Protocol collector"
    if "INCENTIVES" in name:
        return "Staking or rewards", "Protocol incentives controller"
    if "DATA_PROVIDER" in name:
        return "Core contract", "Protocol data provider"
    if "POOL_CONFIGURATOR" in name or name == "CONFIG_ENGINE":
        return "Core contract", "Protocol configuration component"
    if "POOL_ADDRESSES_PROVIDER" in name:
        return "Core contract", "Protocol address-provider component"
    if name == "POOL":
        return "Pool", "Aave V3 lending pool"
    if name == "RISK_STEWARD":
        return "Administrative role", "Protocol risk-management component"
    if name == "GHO_DIRECT_MINTER":
        return "Token", "GHO minting component"
    return "Core contract", "Protocol component"


def _extract_documented_addresses(
    source_directory: Path,
) -> tuple[AddressRecord, ...]:
    if not source_directory.exists():
        return ()
    records = []
    # Address collection follows the same relevance boundary as research
    # extraction. This prevents exhaustive deployment catalogs, tutorials,
    # and SDK references from becoming an unusable scanner queue while still
    # retaining addresses in substantive protocol documentation.
    for path in research_source_files(source_directory):
        relative = path.relative_to(source_directory).as_posix()
        lines = path.read_text(encoding="utf-8").splitlines()
        in_code = False
        current_chain: tuple[str, int | None] | None = None
        previous_label: str | None = None
        for line_number, line in enumerate(lines, start=1):
            if line.lstrip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            heading = re.match(r"^##\s+(?P<heading>.+)$", line.strip())
            if heading:
                current_chain = _chain_from_heading(heading.group("heading"))
                previous_label = None
                continue
            evm_addresses = list(dict.fromkeys(EVM_ADDRESS_PATTERN.findall(line)))
            solana_addresses = (
                list(dict.fromkeys(SOLANA_ADDRESS_PATTERN.findall(line)))
                if current_chain and current_chain[0] == "Solana"
                else []
            )
            addresses = evm_addresses + solana_addresses
            if not addresses:
                candidate = _context_label(line)
                if candidate:
                    previous_label = candidate
                continue
            table_row = line.strip().startswith("|") and line.strip().endswith("|")
            visible_line = re.sub(r"\]\([^)]+\)", "]", line)
            visible_without_urls = re.sub(r"https?://\S+", "", visible_line)
            lowered = visible_without_urls.lower()
            linked_address = bool(
                re.search(
                    r"\[(?:0x[a-fA-F0-9]{40}|"
                    r"[1-9A-HJ-NP-Za-km-z]{32,44})\]\(https?://",
                    line,
                )
            )
            explicit = any(
                word in lowered
                for word in ("address", "contract", "deployment", "proxy")
            )
            contextual_link = linked_address and (
                current_chain is not None or explicit
            )
            if not table_row and not explicit and not contextual_link:
                continue
            label = (
                previous_label
                if linked_address and previous_label
                else _documented_address_label(line)
            )
            chain, chain_id = current_chain or ("Not documented", None)
            resolved = (
                chain in AUTO_COLLECTOR_CHAINS
                and label != "DOCUMENTED_ADDRESS"
            )
            for address in addresses:
                records.append(
                    AddressRecord(
                        name=label,
                        component_type="Documented contract",
                        role=f"Published {label} address",
                        address=address,
                        chain=chain,
                        chain_id=chain_id,
                        deployment_block=None,
                        status=(
                            "documented" if resolved else "documented_unresolved"
                        ),
                        source=f"{relative}#L{line_number}",
                        provenance="documented",
                    )
                )
    return tuple(records)


def _extract_token_catalog_addresses(
    source_directory: Path,
    tokens: list[TokenRecord],
) -> tuple[AddressRecord, ...]:
    """Read only token-specific sections from otherwise exhaustive catalogs."""
    records: list[AddressRecord] = []
    if not source_directory.exists() or not tokens:
        return ()
    for path in sorted(source_directory.rglob("addresses.md")):
        relative = path.relative_to(source_directory).as_posix()
        active: TokenRecord | None = None
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            heading = re.match(r"^##\s+(?P<heading>.+)$", line.strip())
            if heading:
                title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading["heading"])
                normalized = title.casefold()
                active = next(
                    (
                        token
                        for token in tokens
                        if "token" in normalized
                        and token.symbol.casefold() in normalized
                    ),
                    None,
                )
                continue
            if active is None or not line.strip().startswith("|"):
                continue
            addresses = EVM_ADDRESS_PATTERN.findall(line)
            if not addresses:
                continue
            label = _documented_address_label(line)
            token_names = {active.name.casefold(), active.symbol.casefold()}
            if label.casefold() not in token_names:
                continue
            chain, chain_id = _chain_from_explorer_link(line)
            for address in dict.fromkeys(addresses):
                records.append(
                    AddressRecord(
                        name=active.symbol,
                        component_type="Token",
                        role=f"{active.symbol} token contract",
                        address=address,
                        chain=chain,
                        chain_id=chain_id,
                        deployment_block=None,
                        status=(
                            "documented"
                            if chain in AUTO_COLLECTOR_CHAINS
                            else "documented_unresolved"
                        ),
                        source=f"{relative}#L{line_number}",
                        provenance="documented",
                    )
                )
    return tuple(records)


def _chain_from_explorer_link(line: str) -> tuple[str, int | None]:
    lowered = line.casefold()
    domains = {
        "etherscan.io": ("Ethereum", 1),
        "arbiscan.io": ("Arbitrum", 42161),
        "basescan.org": ("Base", 8453),
    }
    return next(
        (chain for domain, chain in domains.items() if domain in lowered),
        ("Not documented", None),
    )


def _documented_address_label(line: str) -> str:
    without_address = re.sub(r"0x[a-fA-F0-9]{40}", "", line)
    cells = [cell.strip(" `*#:-") for cell in without_address.split("|")]
    label = next((cell for cell in cells if cell), "DOCUMENTED_ADDRESS")
    label = re.sub(r"\s+", " ", label).strip()
    return label[:100] or "DOCUMENTED_ADDRESS"


def _chain_from_heading(heading: str) -> tuple[str, int | None] | None:
    normalized = re.sub(r"\[.*?\]\(.*?\)", "", heading).casefold()
    for key, value in DOCUMENTED_CHAINS.items():
        if re.search(rf"\b{re.escape(key)}\b", normalized):
            return value
    return None


def _context_label(line: str) -> str | None:
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
    value = re.sub(r"[*_`#]", "", value).strip(" :|-")
    value = re.sub(r"\s+", " ", value).strip()
    if not value or "|" in value or value.casefold() in {"address", "contract"}:
        return None
    if len(value) > 100 or EVM_ADDRESS_PATTERN.search(value):
        return None
    return value


def _enrich_tokens_from_documented_addresses(
    tokens: list[TokenRecord],
    addresses: list[AddressRecord],
) -> tuple[TokenRecord, ...]:
    enriched = []
    for token in tokens:
        matches = [
            record
            for record in addresses
            if _is_token_deployment(record.name, token)
        ]
        if not matches:
            enriched.append(token)
            continue
        preferred = sorted(
            matches,
            key=lambda row: (
                {"Ethereum": 0, "Arbitrum": 1, "Base": 2}.get(row.chain, 9),
                row.name.casefold(),
            ),
        )[0]
        networks = "; ".join(dict.fromkeys(row.chain for row in matches))
        source = token.source
        if preferred.source not in source:
            source = f"{source}; {preferred.source}"
        enriched.append(
            TokenRecord(
                **{
                    **asdict(token),
                    "network": (
                        networks
                        if token.network.casefold() == "not documented"
                        else token.network
                    ),
                    "address": preferred.address,
                    "source": source,
                }
            )
        )
    return tuple(enriched)


def _clear_previous_address_enrichment(
    tokens: tuple[TokenRecord, ...],
) -> tuple[TokenRecord, ...]:
    """Remove address data derived during an earlier registry pass."""
    cleaned = []
    for token in tokens:
        source_parts = [part.strip() for part in token.source.split(";")]
        derived = [part for part in source_parts[1:] if re.search(r"#L\d+$", part)]
        if not derived:
            cleaned.append(token)
            continue
        cleaned.append(
            TokenRecord(
                **{
                    **asdict(token),
                    "network": "Not documented",
                    "address": "Not documented",
                    "source": source_parts[0],
                }
            )
        )
    return tuple(cleaned)


def _is_token_deployment(label: str, token: TokenRecord) -> bool:
    normalized = re.sub(r"\s+", " ", label).strip().casefold()
    names = {token.name.casefold(), token.symbol.casefold()}
    return normalized in names or any(
        normalized in {f"{name} (oft)", f"{name} (ntt)"}
        for name in names
    )


def _merge_address_records(
    records: list[AddressRecord] | tuple[AddressRecord, ...],
) -> tuple[AddressRecord, ...]:
    deduplicated: dict[tuple[str, str, str], AddressRecord] = {}
    for record in records:
        key = (
            record.name.casefold(),
            record.chain.casefold(),
            record.address.casefold(),
        )
        existing = deduplicated.get(key)
        if existing is None or (
            existing.provenance == "documented"
            and record.provenance == "official_registry"
        ):
            deduplicated[key] = record
    values = list(deduplicated.values())
    identities: dict[tuple[str, str], set[str]] = {}
    for record in values:
        identities.setdefault(
            (record.name.casefold(), record.chain.casefold()), set()
        ).add(record.address.casefold())
    merged = []
    for record in values:
        conflict = len(
            identities[(record.name.casefold(), record.chain.casefold())]
        ) > 1
        merged.append(
            AddressRecord(
                **{
                    **asdict(record),
                    "status": "conflicting" if conflict else record.status,
                }
            )
        )
    return tuple(
        sorted(
            merged,
            key=lambda row: (
                row.chain.casefold(),
                row.component_type.casefold(),
                row.name.casefold(),
                row.address.casefold(),
            ),
        )
    )


def _write_token_page(
    workspace: ProjectWorkspace,
    token: TokenRecord,
    addresses: list[AddressRecord] | tuple[AddressRecord, ...] = (),
) -> Path:
    directory = workspace.vault_root / "Tokens" / token.symbol
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "Index.md"
    deployments = [
        record
        for record in addresses
        if _is_token_deployment(record.name, token)
    ]
    if deployments:
        address_rows = "".join(
            f"| {record.chain} | "
            f"{_token_standard_from_label(record.name, token.standard, record.chain)} | "
            f"`{record.address}` | {record.source} |\n"
            for record in deployments
        )
    else:
        address_rows = (
            f"| {token.network} | {token.standard} | "
            f"`{token.address}` | {token.source} |\n"
        )
    market_snapshot = load_market_snapshot(workspace, token.symbol)
    market_section = _render_market_snapshot(market_snapshot)
    text = (
        "---\n"
        'generated_by: "definalyzer_registry"\n'
        f'entity: "{token.symbol}"\n'
        'entity_type: "token"\n'
        f'parent_protocol: "{workspace.name}"\n'
        f'verification_status: "{workspace.document["verification_status"]}"\n'
        f'generated_at: "{_timestamp()}"\n'
        "---\n\n"
        f"# {token.symbol}\n\n"
        "## Identity\n\n"
        "| Field | Value |\n|---|---|\n"
        f"| Name | {token.name} |\n"
        f"| Symbol | {token.symbol} |\n"
        f"| Type | {token.token_type} |\n"
        f"| Protocol relationship | {token.protocol_relationship} |\n"
        f"| Parent protocol | [[Protocols/{workspace.name}/Index\\|"
        f"{workspace.name}]] |\n\n"
        "## Networks and Addresses\n\n"
        "| Network | Standard | Address | Source |\n|---|---|---|---|\n"
        f"{address_rows}\n"
        "## Documented Token Mechanics\n\n"
        "| Field | Value |\n|---|---|\n"
        f"| Mint authority | {token.mint_authority} |\n"
        f"| Allocation | {token.allocation} |\n"
        f"| Emissions | {token.emissions} |\n"
        f"| Unlocks or vesting | {token.unlocks} |\n\n"
        f"{market_section}"
        "## Utility\n\n"
        f"- {token.utility}\n\n"
        "## Data Status\n\n"
        "- Address provenance is registry data, not verification.\n"
        "- `Not documented` fields remain open for official-source or "
        "onchain enrichment.\n"
    )
    _write_generated_markdown(path, text, legacy_markers=("parent_protocol:",))
    return path


def refresh_token_pages_from_registry(
    workspace: ProjectWorkspace,
) -> tuple[Path, ...]:
    """Rewrite generated token pages after an optional enrichment refresh."""

    registry_path = workspace.registry_directory / "registry.json"
    if not registry_path.exists():
        raise FileNotFoundError("Project registry is required.")
    document = json.loads(registry_path.read_text(encoding="utf-8"))
    token_rows = document.get("tokens")
    address_rows = document.get("addresses")
    if not isinstance(token_rows, list) or not isinstance(address_rows, list):
        raise ValueError("Project registry has invalid token or address data.")
    tokens = tuple(TokenRecord(**row) for row in token_rows)
    addresses = tuple(AddressRecord(**row) for row in address_rows)
    return tuple(
        _write_token_page(workspace, token, addresses) for token in tokens
    )


def _render_market_snapshot(snapshot: MarketSnapshot | None) -> str:
    if snapshot is None:
        return (
            "## Current Supply Data — CoinGecko\n\n"
            "| Field | Value |\n|---|---|\n"
            "| Fully diluted valuation | Not collected |\n"
            "| Circulating supply | Not collected |\n"
            "| Total supply | Not collected |\n"
            "| Maximum supply | Not collected |\n"
            "| Updated | Never |\n\n"
            "Run **Refresh current token supply data** to request these "
            "fields from CoinGecko. This section is never filled by AI.\n\n"
        )
    if snapshot.status != "available":
        detail = snapshot.detail or "No supply data was returned."
        return (
            "## Current Supply Data — CoinGecko\n\n"
            f"- Status: Unavailable — {detail}\n"
            f"- Attempted: {snapshot.collected_at}\n"
            "- Run **Refresh current token supply data** to retry.\n"
            "- This section is never filled by AI.\n\n"
        )

    def display(value: float | int | None) -> str:
        if value is None:
            return "Not available"
        return f"{value:,.2f}".rstrip("0").rstrip(".")

    def currency(value: float | int | None) -> str:
        return f"${display(value)}" if value is not None else "Not available"

    source = snapshot.source_url or "Not available"
    return (
        "## Current Supply Data — CoinGecko\n\n"
        "| Field | Value |\n|---|---|\n"
        "| Fully diluted valuation | "
        f"{currency(snapshot.fully_diluted_valuation_usd)} |\n"
        f"| Circulating supply | {display(snapshot.circulating_supply)} |\n"
        f"| Total supply | {display(snapshot.total_supply)} |\n"
        f"| Maximum supply | {display(snapshot.max_supply)} |\n"
        f"| Exact address match | {snapshot.network}: "
        f"`{snapshot.contract_address}` |\n"
        f"| Updated | {snapshot.provider_updated_at or snapshot.collected_at} |\n"
        f"| Source | [CoinGecko]({source}) |\n\n"
        "> Deterministic third-party supply data. This section is never "
        "filled by AI and does not overwrite documented token mechanics.\n\n"
    )


def _token_standard_from_label(
    label: str,
    fallback: str,
    chain: str,
) -> str:
    match = re.search(r"\((OFT|NTT)\)", label, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    if chain in AUTO_COLLECTOR_CHAINS:
        return "ERC-20"
    return fallback


def _write_network_page(
    workspace: ProjectWorkspace,
    networks: list[dict[str, Any]],
) -> Path:
    path = workspace.vault_entity_directory / "Networks.md"
    rows = "\n".join(
        f"| {row['name']} | {row['chain_id']} | {row['environment']} | "
        f"{row['status']} |"
        for row in networks
    )
    text = (
        "---\n"
        'generated_by: "definalyzer_registry"\n'
        f'entity: "{workspace.name}"\n'
        'data_class: "registry_snapshot"\n'
        f'snapshot_at: "{_timestamp()}"\n'
        "---\n\n"
        "# Networks\n\n"
        "Aave's static documentation states 14+ deployments but directs "
        "clients to its GraphQL `chains` query for the current supported-chain "
        "list. API support does not independently prove an active production "
        "market.\n\n"
        "| Chain | Chain ID | Environment | Status |\n"
        "|---|---:|---|---|\n"
        f"{rows}\n\n"
        f"Source: {AAVE_GRAPHQL_URL}\n"
    )
    _write_generated_markdown(path, text, legacy_markers=('data_class: "registry_snapshot"',))
    return path


def _write_address_page(
    workspace: ProjectWorkspace,
    addresses: list[AddressRecord],
) -> Path:
    path = workspace.vault_entity_directory / "Registry.md"
    rows = "\n".join(
        f"| {record.name} | {record.component_type} | {record.role} | "
        f"`{record.address}` | {record.chain} | {record.provenance} | "
        f"{record.status} | {record.source} |"
        for record in addresses
    )
    text = (
        "---\n"
        'generated_by: "definalyzer_registry"\n'
        f'entity: "{workspace.name}"\n'
        'data_class: "address_registry"\n'
        f'generated_at: "{_timestamp()}"\n'
        "---\n\n"
        "# Contract Registry\n\n"
        "Only exact addresses from official documentation or an official "
        "machine-readable registry are included. `documented_unresolved` "
        "records lack enough chain or role information for automatic "
        "collection. `conflicting` records require manual review.\n\n"
        "| Name | Type | Role | Address | Chain | Provenance | Status | Source |\n"
        "|---|---|---|---|---|---|---|---|\n"
        f"{rows}\n"
    )
    _write_generated_markdown(
        path,
        text,
        legacy_markers=('data_class: "address_registry"',),
    )
    return path


def _update_protocol_index(
    workspace: ProjectWorkspace,
    tokens: list[TokenRecord],
    network_page: Path | None,
    address_page: Path | None,
) -> None:
    path = workspace.vault_entity_directory / "Index.md"
    text = path.read_text(encoding="utf-8")
    entries = []
    if network_page:
        entries.append(f"[[Protocols/{workspace.name}/Networks|Networks]]")
    if address_page:
        entries.append(
            f"[[Protocols/{workspace.name}/Registry|Contract Registry]]"
        )
    entries.extend(f"[[Tokens/{token.symbol}/Index|{token.symbol}]]" for token in tokens)
    valid_symbols = {token.symbol.casefold() for token in tokens}
    updated = re.sub(
        r"(?m)^- \[\[Tokens/([^/\]]+)/Index\|[^\]]+\]\]\n?",
        lambda match: (
            match.group(0)
            if match.group(1).casefold() in valid_symbols
            else ""
        ),
        text,
    )
    if "## Linked Data" not in updated:
        updated = updated.rstrip() + "\n\n## Linked Data\n\n"
    else:
        updated = re.sub(
            r"(?m)^(## Linked Data)\n(?=- )",
            r"\1\n\n",
            updated,
        )
    for entry in entries:
        if entry not in updated:
            updated = updated.rstrip() + f"\n- {entry}\n"
    if updated != text:
        path.write_text(updated, encoding="utf-8", newline="\n")


def _parse_json_object(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    try:
        document = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Token discovery returned invalid JSON: {exc.msg}"
        ) from exc
    if not isinstance(document, dict):
        raise ValueError("Token discovery output must be a JSON object.")
    return document


def _is_markdown_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _normalize_table_wikilinks(line: str) -> str:
    if not _is_markdown_table_row(line):
        return line
    return re.sub(
        r"\[\[\s*([^|\]\\]+?)\s*(?:\\)?\|\s*([^\]]+?)\s*\]\]",
        lambda match: (
            f"[[{match.group(1).strip()}\\|{match.group(2).strip()}]]"
        ),
        line,
    )


def _remove_empty_trailing_table_columns(lines: list[str]) -> list[str]:
    repaired = list(lines)
    index = 0
    while index < len(repaired):
        if not _is_markdown_table_row(repaired[index]):
            index += 1
            continue
        end = index
        while end < len(repaired) and _is_markdown_table_row(repaired[end]):
            end += 1
        rows = [_split_table_row(line) for line in repaired[index:end]]
        content_rows = [
            row for row in rows if not _is_table_separator(row)
        ]
        trimmed = [_trim_empty_cells(row) for row in content_rows]
        desired = max((len(row) for row in trimmed), default=0)
        if desired and any(len(row) > desired for row in rows):
            for offset, row in enumerate(rows):
                repaired[index + offset] = (
                    "| " + " | ".join(cell.strip() for cell in row[:desired]) + " |"
                )
        index = end
    return repaired


def _split_table_row(line: str) -> list[str]:
    return re.split(r"(?<!\\)\|", line.strip())[1:-1]


def _trim_empty_cells(cells: list[str]) -> list[str]:
    result = list(cells)
    while result and not result[-1].strip():
        result.pop()
    return result


def _is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r"\s*:?-{3,}:?\s*", cell) for cell in cells
    )


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"Accept": "text/plain"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def _fetch_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        document = json.loads(response.read())
    if not isinstance(document, dict):
        raise ValueError("Registry API returned a non-object response.")
    return document


def _load_existing_tokens(path: Path) -> tuple[TokenRecord, ...]:
    if not path.exists():
        return ()
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("tokens") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        return ()
    fields = tuple(TokenRecord.__dataclass_fields__)
    tokens = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if all(isinstance(row.get(field), str) for field in fields):
            token = TokenRecord(**{field: row[field] for field in fields})
            if (
                token.name.strip().casefold() in PLACEHOLDER_IDENTITIES
                or token.symbol.strip().casefold() in PLACEHOLDER_IDENTITIES
            ):
                continue
            tokens.append(token)
    return tuple(tokens)


def registry_needs_token_discovery(workspace: ProjectWorkspace) -> bool:
    path = workspace.registry_directory / "registry.json"
    tokenomics = workspace.vault_entity_directory / "Tokenomics.md"
    if not tokenomics.exists():
        return True
    if _token_discovery_complete(
        path,
        coverage_complete=token_coverage_complete(workspace),
        tokenomics_digest=_file_digest(tokenomics),
    ):
        return False
    return not bool(_load_existing_tokens(path))


def _token_discovery_complete(
    path: Path,
    *,
    coverage_complete: bool,
    tokenomics_digest: str,
) -> bool:
    if not path.exists():
        return False
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(
        coverage_complete
        and
        isinstance(document, dict)
        and document.get("token_discovery_status") == "complete"
        and document.get("tokenomics_digest") == tokenomics_digest
    )


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _remove_stale_token_pages(
    workspace: ProjectWorkspace,
    tokens: list[TokenRecord] | tuple[TokenRecord, ...],
) -> None:
    current_symbols = {token.symbol.casefold() for token in tokens}
    tokens_root = workspace.vault_root / "Tokens"
    if not tokens_root.exists():
        return
    for page in tokens_root.glob("*/Index.md"):
        try:
            text = page.read_text(encoding="utf-8")
        except OSError:
            continue
        if 'generated_by: "definalyzer_registry"' not in text:
            continue
        if f'parent_protocol: "{workspace.name}"' not in text:
            continue
        if page.parent.name.casefold() in current_symbols:
            continue
        page.unlink()
        try:
            page.parent.rmdir()
        except OSError:
            pass


def _write_generated_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(document, file, indent=2)
        file.write("\n")
    temporary.replace(path)


def _write_generated_markdown(
    path: Path,
    text: str,
    *,
    legacy_markers: tuple[str, ...],
) -> None:
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        generated = 'generated_by: "definalyzer_registry"' in existing
        legacy_generated = all(marker in existing for marker in legacy_markers)
        if not generated and not legacy_generated:
            raise FileExistsError(
                f"Refusing to overwrite a user-owned page: {path}"
            )
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
