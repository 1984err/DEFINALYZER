import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from definalyzer.market_data import refresh_market_data
from definalyzer.registry_workflow import refresh_token_pages_from_registry
from definalyzer.workspace import WorkspaceManager


def registry_document():
    token = {
        "name": "Example",
        "symbol": "EXM",
        "token_type": "Governance token",
        "protocol_relationship": "Native token",
        "network": "Not documented",
        "standard": "Not documented",
        "address": "Not documented",
        "supply": "Documented supply",
        "maximum_supply": "Not documented",
        "circulating_supply": "Not documented",
        "emissions": "No emissions documented",
        "allocation": "Documented allocation",
        "unlocks": "Documented unlocks",
        "mint_authority": "Not documented",
        "utility": "Governance",
        "source": "Tokenomics.md",
    }
    return {
        "tokens": [token],
        "addresses": [
            {
                "name": "EXM",
                "component_type": "token",
                "role": "Protocol token",
                "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "chain": "Arbitrum",
                "chain_id": 42161,
                "deployment_block": None,
                "status": "documented",
                "source": "deployments.md",
                "provenance": "documented",
            }
        ],
    }


class MarketDataTests(unittest.TestCase):
    def make_workspace(self, root):
        manager = WorkspaceManager(Path(root) / "output")
        workspace = manager.create_project(name="Example Protocol")
        (workspace.registry_directory / "registry.json").write_text(
            json.dumps(registry_document()),
            encoding="utf-8",
        )
        return workspace

    def test_matches_by_address_caches_and_renders_separate_snapshot(self):
        calls = []
        response = {
            "id": "example",
            "name": "Example",
            "symbol": "exm",
            "market_cap_rank": 42,
            "last_updated": "2026-07-30T00:00:00Z",
            "market_data": {
                "current_price": {"usd": 1.25},
                "market_cap": {"usd": 1_000_000},
                "fully_diluted_valuation": {"usd": 1_250_000},
                "total_volume": {"usd": 25_000},
                "price_change_percentage_24h": -2.5,
                "circulating_supply": 800_000,
                "total_supply": 1_000_000,
                "max_supply": None,
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(directory)

            def fetch(url):
                calls.append(url)
                return response

            first = refresh_market_data(
                workspace=workspace,
                fetch_json=fetch,
                now=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            second = refresh_market_data(
                workspace=workspace,
                fetch_json=fetch,
                now=datetime(2026, 7, 30, 0, 30, tzinfo=timezone.utc),
            )
            page = refresh_token_pages_from_registry(workspace)[0]
            text = page.read_text(encoding="utf-8")

        self.assertEqual(len(calls), 1)
        self.assertIn("/coins/arbitrum-one/contract/0xaaaaaaaa", calls[0])
        self.assertEqual(first.refreshed, 1)
        self.assertEqual(second.reused, 1)
        self.assertIn("## Current Supply Data — CoinGecko", text)
        self.assertIn("| Fully diluted valuation | $1,250,000 |", text)
        self.assertNotIn("| Price (USD)", text)
        self.assertNotIn("| 24h volume", text)
        self.assertNotIn("| Market cap (USD)", text)
        self.assertNotIn("| Supply | Documented supply |", text)
        self.assertIn("never filled by AI", text)

    def test_chain_coin_uses_unique_exact_coingecko_identity_without_address(self):
        document = registry_document()
        document["addresses"] = []
        document["tokens"][0].update({
            "name": "Example Gas Coin",
            "symbol": "EXC",
            "token_type": "Native coin",
            "protocol_relationship": "Gas and staking",
            "network": "Example Chain",
            "standard": "Native",
            "address": "Not applicable",
        })
        calls = []

        def fetch(url):
            calls.append(url)
            if "/coins/list" in url:
                return [{
                    "id": "example-coin",
                    "name": "Example Coin",
                    "symbol": "exc",
                    "platforms": {},
                }]
            return {
                "id": "example-coin",
                "name": "Example Coin",
                "symbol": "exc",
                "market_data": {
                    "fully_diluted_valuation": {"usd": 10_000},
                    "circulating_supply": 500,
                    "total_supply": 1_000,
                    "max_supply": 1_000,
                },
            }

        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example Chain", entity_type="chain")
            (workspace.registry_directory / "registry.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            result = refresh_market_data(
                workspace=workspace,
                fetch_json=fetch,
                now=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            page = refresh_token_pages_from_registry(workspace)[0]
            text = page.read_text(encoding="utf-8")

        self.assertEqual(result.snapshots[0].status, "available")
        self.assertEqual(result.snapshots[0].coin_id, "example-coin")
        self.assertEqual(calls[-1].rsplit("/", 1)[-1], "example-coin")
        self.assertIn("| CoinGecko identity | Example Coin (exc) |", text)
        self.assertNotIn("Exact address match", text)

    def test_unlisted_token_is_visible_without_raising(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(directory)

            def missing(url):
                raise HTTPError(url, 404, "Not Found", {}, None)

            result = refresh_market_data(
                workspace=workspace,
                fetch_json=missing,
                now=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            page = refresh_token_pages_from_registry(workspace)[0]
            text = page.read_text(encoding="utf-8")

        self.assertEqual(result.snapshots[0].status, "unavailable")
        self.assertIn("CoinGecko has no listing", text)

    def test_temporary_network_failure_is_visible_and_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(directory)

            def unavailable(url):
                raise URLError("temporary DNS failure")

            result = refresh_market_data(
                workspace=workspace,
                fetch_json=unavailable,
                now=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            page = refresh_token_pages_from_registry(workspace)[0]
            text = page.read_text(encoding="utf-8")

        self.assertEqual(result.snapshots[0].status, "unavailable")
        self.assertIn("could not be reached", text)
        self.assertIn("retry", text.casefold())

    def test_missing_supported_contract_does_not_make_network_request(self):
        document = registry_document()
        document["addresses"] = []
        document["tokens"][0]["address"] = "Not documented"
        calls = []

        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(directory)
            (workspace.registry_directory / "registry.json").write_text(
                json.dumps(document),
                encoding="utf-8",
            )
            result = refresh_market_data(
                workspace=workspace,
                fetch_json=lambda url: calls.append(url),
                now=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )

        self.assertEqual(calls, [])
        self.assertEqual(result.snapshots[0].status, "unavailable")
        self.assertIn(
            "No documented contract or mint",
            result.snapshots[0].detail,
        )

    def test_discovers_platform_from_exact_address_when_network_is_missing(self):
        document = registry_document()
        document["addresses"] = []
        document["tokens"][0]["address"] = "So1anaExactMint"
        calls = []

        def fetch(url):
            calls.append(url)
            if "/coins/list" in url:
                return [
                    {
                        "id": "example-solana",
                        "symbol": "exm",
                        "name": "Example",
                        "platforms": {"solana": "So1anaExactMint"},
                    }
                ]
            return {
                "id": "example-solana",
                "name": "Example",
                "symbol": "exm",
                "last_updated": "2026-07-30T00:00:00Z",
                "market_data": {
                    "fully_diluted_valuation": {"usd": 2_000_000},
                    "circulating_supply": 400_000,
                    "total_supply": 1_000_000,
                    "max_supply": 1_000_000,
                },
            }

        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(directory)
            (workspace.registry_directory / "registry.json").write_text(
                json.dumps(document),
                encoding="utf-8",
            )
            result = refresh_market_data(
                workspace=workspace,
                fetch_json=fetch,
                now=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )

        self.assertEqual(result.snapshots[0].status, "available")
        self.assertEqual(result.snapshots[0].platform_id, "solana")
        self.assertEqual(result.snapshots[0].network, "Solana")
        self.assertIn("/coins/list?include_platform=true", calls[0])
        self.assertIn("/coins/solana/contract/So1anaExactMint", calls[1])

    def test_newly_discovered_address_invalidates_fresh_unavailable_cache(self):
        document = registry_document()
        document["addresses"] = []
        document["tokens"][0]["address"] = "Not documented"
        calls = []

        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(directory)
            registry_path = workspace.registry_directory / "registry.json"
            registry_path.write_text(json.dumps(document), encoding="utf-8")
            first = refresh_market_data(
                workspace=workspace,
                fetch_json=lambda url: calls.append(url),
                now=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            document["tokens"][0]["address"] = (
                "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            )
            registry_path.write_text(json.dumps(document), encoding="utf-8")

            def fetch(url):
                calls.append(url)
                if "/coins/list" in url:
                    return [{
                        "id": "example",
                        "platforms": {
                            "ethereum": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                        },
                    }]
                return {
                    "id": "example",
                    "name": "Example",
                    "symbol": "exm",
                    "market_data": {},
                }

            second = refresh_market_data(
                workspace=workspace,
                fetch_json=fetch,
                now=datetime(2026, 7, 30, 0, 30, tzinfo=timezone.utc),
            )

        self.assertEqual(first.snapshots[0].status, "unavailable")
        self.assertEqual(second.reused, 0)
        self.assertEqual(second.refreshed, 1)
        self.assertEqual(second.snapshots[0].status, "available")
        self.assertEqual(len(calls), 2)
        self.assertIn("/coins/list?include_platform=true", calls[0])
        self.assertIn(
            "/coins/ethereum/contract/0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            calls[1],
        )


if __name__ == "__main__":
    unittest.main()
