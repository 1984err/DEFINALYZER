import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError

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
        self.assertIn("## Market Snapshot (Third Party)", text)
        self.assertIn("| Price (USD) | $1.25 |", text)
        self.assertIn("| Supply | Documented supply |", text)
        self.assertIn("does not overwrite documented tokenomics", text)

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
        self.assertIn("No supported network", result.snapshots[0].detail)


if __name__ == "__main__":
    unittest.main()
