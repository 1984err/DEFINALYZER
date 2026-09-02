"""Deterministic third-party token and native-coin supply snapshots.

Tokens are matched by exact contract or mint address. Addressless native coins
use an unambiguous CoinGecko identity match. Snapshots remain separate from
documented research facts and raw on-chain evidence.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .workspace import ProjectWorkspace


COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
CACHE_MAX_AGE = timedelta(days=1)
PLATFORM_IDS = {
    "arbitrum": "arbitrum-one",
    "arbitrum one": "arbitrum-one",
    "base": "base",
    "ethereum": "ethereum",
    "solana": "solana",
}
NETWORK_PRIORITY = ("ethereum", "arbitrum", "arbitrum one", "base", "solana")
MISSING_ADDRESS_VALUES = {"", "-", "n/a", "none", "not applicable", "not documented"}


@dataclass(frozen=True)
class MarketSnapshot:
    status: str
    provider: str
    symbol: str
    network: str | None
    platform_id: str | None
    contract_address: str | None
    coin_id: str | None
    matched_name: str | None
    matched_symbol: str | None
    fully_diluted_valuation_usd: float | int | None
    circulating_supply: float | int | None
    total_supply: float | int | None
    max_supply: float | int | None
    provider_updated_at: str | None
    collected_at: str
    source_url: str | None
    detail: str | None


@dataclass(frozen=True)
class MarketRefreshResult:
    snapshots: tuple[MarketSnapshot, ...]
    refreshed: int
    reused: int


JsonFetcher = Callable[[str], Any]
SleepFunction = Callable[[float], None]


def refresh_market_data(
    *,
    workspace: ProjectWorkspace,
    force: bool = False,
    fetch_json: JsonFetcher | None = None,
    sleep: SleepFunction = time.sleep,
    now: datetime | None = None,
) -> MarketRefreshResult:
    """Refresh conservative CoinGecko snapshots for registered assets."""

    registry_path = workspace.registry_directory / "registry.json"
    if not registry_path.exists():
        raise FileNotFoundError(
            "Project registry is required before market data can be refreshed."
        )
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    tokens = registry.get("tokens")
    addresses = registry.get("addresses")
    if not isinstance(tokens, list) or not isinstance(addresses, list):
        raise ValueError("Project registry has invalid token or address data.")

    current = now or datetime.now(timezone.utc)
    fetcher = fetch_json or (
        lambda url: _fetch_json_with_backoff(url, sleep=sleep)
    )
    snapshots: list[MarketSnapshot] = []
    refreshed = 0
    reused = 0
    coin_list: Any = None
    coin_list_loaded = False

    for token in tokens:
        if not isinstance(token, dict):
            continue
        symbol = str(token.get("symbol") or "").strip()
        if not symbol:
            continue
        network, address = _select_contract(token, addresses)
        native_coin = workspace.document["entity_type"] == "chain" and not address
        if native_coin:
            documented_network = str(token.get("network") or "").strip()
            network = (
                documented_network
                if documented_network.casefold() not in {"", "not documented"}
                else workspace.name
            )
        if network and network.casefold() == "not documented":
            network = None
        cache_path = market_snapshot_path(workspace, symbol)
        cached = _load_snapshot(cache_path)
        if (
            not force
            and cached
            and _is_fresh(cached, current)
            and _snapshot_matches_contract(cached, network, address)
        ):
            snapshots.append(cached)
            reused += 1
            continue

        platform_id = PLATFORM_IDS.get(network.casefold()) if network else None
        discovery_detail = None
        if address and not platform_id:
            try:
                if not coin_list_loaded:
                    coin_list = fetcher(
                        f"{COINGECKO_BASE_URL}/coins/list"
                        "?include_platform=true"
                    )
                    coin_list_loaded = True
                match = _match_platform_by_address(coin_list, address)
                if match:
                    platform_id, matched_network = match
                    network = network or matched_network
                else:
                    discovery_detail = (
                        "CoinGecko did not return one unambiguous platform "
                        "match for the exact contract or mint address."
                    )
            except (HTTPError, OSError, TimeoutError, ValueError) as exc:
                discovery_detail = _safe_error(exc)

        native_coin_id = None
        if native_coin:
            try:
                if not coin_list_loaded:
                    coin_list = fetcher(
                        f"{COINGECKO_BASE_URL}/coins/list?include_platform=true"
                    )
                    coin_list_loaded = True
                native_coin_id = _match_native_coin_by_identity(
                    coin_list,
                    name=str(token.get("name") or ""),
                    symbol=symbol,
                )
            except (HTTPError, OSError, TimeoutError, ValueError) as exc:
                discovery_detail = _safe_error(exc)

        if native_coin and native_coin_id:
            source_url = f"{COINGECKO_BASE_URL}/coins/{quote(native_coin_id, safe='')}"
            try:
                document = fetcher(source_url)
                snapshot = _snapshot_from_response(
                    symbol=symbol,
                    network=network,
                    address=None,
                    platform_id=None,
                    source_url=source_url,
                    document=document,
                    collected_at=current,
                )
            except (HTTPError, OSError, TimeoutError, ValueError) as exc:
                snapshot = _unavailable_snapshot(
                    symbol=symbol,
                    network=network,
                    address=None,
                    platform_id=None,
                    collected_at=current,
                    source_url=source_url,
                    detail=_safe_error(exc),
                )
        elif not platform_id or not address:
            snapshot = _unavailable_snapshot(
                symbol=symbol,
                network=network,
                address=address,
                platform_id=platform_id,
                collected_at=current,
                detail=(
                    discovery_detail
                    or (
                        "CoinGecko did not return one unique exact identity or "
                        "native-symbol match for this coin."
                        if native_coin else
                        "No documented contract or mint address was available "
                        "for exact-address matching."
                    )
                ),
            )
        else:
            source_url = (
                f"{COINGECKO_BASE_URL}/coins/{quote(platform_id, safe='')}"
                f"/contract/{quote(address, safe='')}"
            )
            try:
                document = fetcher(source_url)
                snapshot = _snapshot_from_response(
                    symbol=symbol,
                    network=network,
                    address=address,
                    platform_id=platform_id,
                    source_url=source_url,
                    document=document,
                    collected_at=current,
                )
            except (HTTPError, OSError, TimeoutError, ValueError) as exc:
                snapshot = _unavailable_snapshot(
                    symbol=symbol,
                    network=network,
                    address=address,
                    platform_id=platform_id,
                    collected_at=current,
                    source_url=source_url,
                    detail=_safe_error(exc),
                )

        _write_snapshot(cache_path, snapshot)
        snapshots.append(snapshot)
        refreshed += 1

    return MarketRefreshResult(
        snapshots=tuple(snapshots),
        refreshed=refreshed,
        reused=reused,
    )


def market_snapshot_path(
    workspace: ProjectWorkspace,
    symbol: str,
) -> Path:
    safe_symbol = "".join(
        character
        for character in symbol.upper()
        if character.isalnum() or character in {"-", "_"}
    )
    return workspace.registry_directory / "market-data" / f"{safe_symbol}.json"


def load_market_snapshot(
    workspace: ProjectWorkspace,
    symbol: str,
) -> MarketSnapshot | None:
    return _load_snapshot(market_snapshot_path(workspace, symbol))


def _select_contract(
    token: dict[str, Any],
    addresses: list[Any],
) -> tuple[str | None, str | None]:
    symbol = str(token.get("symbol") or "").strip().casefold()
    candidates: list[tuple[str, str]] = []
    for row in addresses:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip().casefold()
        if not symbol or not (
            name == symbol
            or name.startswith(f"{symbol} ")
            or name.startswith(f"{symbol}(")
            or f"{symbol}_underlying" in name
        ):
            continue
        network = str(row.get("chain") or "").strip()
        address = str(row.get("address") or "").strip()
        if (
            network.casefold() in PLATFORM_IDS
            and address.casefold() not in MISSING_ADDRESS_VALUES
        ):
            candidates.append((network, address))

    token_network = str(token.get("network") or "").strip()
    token_address = str(token.get("address") or "").strip()
    if token_address.casefold() not in MISSING_ADDRESS_VALUES:
        candidates.append((token_network, token_address))

    def priority(item: tuple[str, str]) -> tuple[int, str]:
        key = item[0].casefold()
        try:
            rank = NETWORK_PRIORITY.index(key)
        except ValueError:
            rank = len(NETWORK_PRIORITY)
        return rank, item[1].casefold()

    return min(candidates, key=priority) if candidates else (None, None)


def _match_platform_by_address(
    document: Any,
    address: str,
) -> tuple[str, str] | None:
    if not isinstance(document, list):
        raise ValueError("CoinGecko coin list returned a non-list response.")
    target = address.casefold()
    matches: set[str] = set()
    for coin in document:
        if not isinstance(coin, dict):
            continue
        platforms = coin.get("platforms")
        if not isinstance(platforms, dict):
            continue
        for platform_id, candidate in platforms.items():
            if (
                isinstance(platform_id, str)
                and isinstance(candidate, str)
                and candidate.strip().casefold() == target
            ):
                matches.add(platform_id)
    if len(matches) != 1:
        return None
    platform_id = next(iter(matches))
    network = next(
        (
            label
            for label, configured_id in PLATFORM_IDS.items()
            if configured_id == platform_id and label != "arbitrum one"
        ),
        platform_id,
    )
    return platform_id, network.title()


def _match_native_coin_by_identity(
    document: Any,
    *,
    name: str,
    symbol: str,
) -> str | None:
    """Return one unambiguous CoinGecko identity for an addressless coin."""

    if not isinstance(document, list):
        raise ValueError("CoinGecko coin list returned a non-list response.")
    target_name = name.strip().casefold()
    target_symbol = symbol.strip().casefold()
    exact_matches = {
        str(row["id"])
        for row in document
        if isinstance(row, dict)
        and isinstance(row.get("id"), str)
        and str(row.get("name") or "").strip().casefold() == target_name
        and str(row.get("symbol") or "").strip().casefold() == target_symbol
    }
    if len(exact_matches) == 1:
        return next(iter(exact_matches))
    # Documentation may call ETH "Ether" while CoinGecko calls it
    # "Ethereum". Fall back only when one addressless/native listing has the
    # exact symbol; token contracts with the same symbol remain excluded.
    native_symbol_matches = {
        str(row["id"])
        for row in document
        if isinstance(row, dict)
        and isinstance(row.get("id"), str)
        and str(row.get("symbol") or "").strip().casefold() == target_symbol
        and not any(
            isinstance(address, str) and address.strip()
            for address in (
                row.get("platforms", {}).values()
                if isinstance(row.get("platforms"), dict)
                else ()
            )
        )
    }
    return (
        next(iter(native_symbol_matches))
        if len(native_symbol_matches) == 1
        else None
    )


def _snapshot_from_response(
    *,
    symbol: str,
    network: str,
    address: str | None,
    platform_id: str | None,
    source_url: str,
    document: dict[str, Any],
    collected_at: datetime,
) -> MarketSnapshot:
    if not isinstance(document, dict):
        raise ValueError("CoinGecko returned a non-object response.")
    market = document.get("market_data")
    if not isinstance(market, dict):
        raise ValueError("CoinGecko response did not include market_data.")

    return MarketSnapshot(
        status="available",
        provider="CoinGecko",
        symbol=symbol,
        network=network,
        platform_id=platform_id,
        contract_address=address,
        coin_id=_optional_text(document.get("id")),
        matched_name=_optional_text(document.get("name")),
        matched_symbol=_optional_text(document.get("symbol")),
        fully_diluted_valuation_usd=_nested_number(
            market, "fully_diluted_valuation", "usd"
        ),
        circulating_supply=_number(market.get("circulating_supply")),
        total_supply=_number(market.get("total_supply")),
        max_supply=_number(market.get("max_supply")),
        provider_updated_at=_optional_text(
            document.get("last_updated") or market.get("last_updated")
        ),
        collected_at=collected_at.isoformat(timespec="seconds"),
        source_url=source_url,
        detail=None,
    )


def _unavailable_snapshot(
    *,
    symbol: str,
    network: str | None,
    address: str | None,
    platform_id: str | None,
    collected_at: datetime,
    detail: str,
    source_url: str | None = None,
) -> MarketSnapshot:
    return MarketSnapshot(
        status="unavailable",
        provider="CoinGecko",
        symbol=symbol,
        network=network,
        platform_id=platform_id,
        contract_address=address,
        coin_id=None,
        matched_name=None,
        matched_symbol=None,
        fully_diluted_valuation_usd=None,
        circulating_supply=None,
        total_supply=None,
        max_supply=None,
        provider_updated_at=None,
        collected_at=collected_at.isoformat(timespec="seconds"),
        source_url=source_url,
        detail=detail,
    )


def _fetch_json_with_backoff(
    url: str,
    *,
    sleep: SleepFunction,
    attempts: int = 3,
) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "DEFINALYZER/1.0",
        },
    )
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code != 429 or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 2**attempt
            except ValueError:
                delay = 2**attempt
            sleep(min(max(delay, 0), 30))
    raise RuntimeError("CoinGecko retry loop ended unexpectedly.")


def _load_snapshot(path: Path) -> MarketSnapshot | None:
    if not path.exists():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        return MarketSnapshot(**document)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _write_snapshot(path: Path, snapshot: MarketSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(asdict(snapshot), indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _is_fresh(snapshot: MarketSnapshot, now: datetime) -> bool:
    try:
        collected = datetime.fromisoformat(snapshot.collected_at)
    except ValueError:
        return False
    if collected.tzinfo is None:
        collected = collected.replace(tzinfo=timezone.utc)
    return timedelta(0) <= now - collected <= CACHE_MAX_AGE


def _snapshot_matches_contract(
    snapshot: MarketSnapshot,
    network: str | None,
    address: str | None,
) -> bool:
    cached_address = (snapshot.contract_address or "").strip().casefold()
    selected_address = (address or "").strip().casefold()
    if cached_address != selected_address:
        return False
    if network:
        return (snapshot.network or "").strip().casefold() == network.casefold()
    return True


def _nested_number(
    document: dict[str, Any],
    parent: str,
    child: str,
) -> float | int | None:
    value = document.get(parent)
    return _number(value.get(child)) if isinstance(value, dict) else None


def _number(value: Any) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    return value


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        if exc.code == 404:
            return "CoinGecko has no listing for this network and address."
        if exc.code == 429:
            return "CoinGecko rate limit remained active after retries."
        return f"CoinGecko returned HTTP {exc.code}."
    if isinstance(exc, URLError):
        return "CoinGecko could not be reached."
    return str(exc)
