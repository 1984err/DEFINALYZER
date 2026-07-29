import json
import tempfile
import unittest
from pathlib import Path

from definalyzer.providers import ProviderResponse
from definalyzer.registry_workflow import (
    _extract_documented_addresses,
    run_registry_workflow,
)
from definalyzer.workspace import WorkspaceManager


class FakeTokenProvider:
    name = "fake"

    def generate(self, prompt, *, working_directory):
        tokens = []
        # Deliberately omit GHO: the official Aave address registry must add
        # qualifying protocol-issued tokens missed by document extraction.
        for name, symbol, token_type in (
            ("Aave", "AAVE", "Governance token"),
        ):
            tokens.append(
                {
                    "name": name,
                    "symbol": symbol,
                    "token_type": token_type,
                    "protocol_relationship": "Issued by or native to Aave",
                    "network": "Not documented",
                    "standard": "Not documented",
                    "address": "Not documented",
                    "supply": "Not documented",
                    "maximum_supply": "Not documented",
                    "circulating_supply": "Not documented",
                    "emissions": "Not documented",
                    "allocation": "Not documented",
                    "unlocks": "Not documented",
                    "mint_authority": "Not documented",
                    "utility": "Documented protocol utility",
                    "source": "Tokenomics.md",
                }
            )
        return ProviderResponse(
            text=json.dumps({"tokens": tokens}),
            provider="fake",
            command=("fake",),
        )


class RegistryWorkflowTests(unittest.TestCase):
    def test_parses_gitbook_address_lists_with_chain_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "addresses.md").write_text(
                "## Arbitrum (Hub)\n"
                "Contract\nAddress\nEXM\n"
                "[0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa]"
                "(https://arbiscan.io/address/"
                "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa)\n"
                "## Solana\nEXM (NTT)\n"
                "[chipCAT7vi5CZtbZsn9z7iMPXvFwyAnKz3QFu8XVuHm]"
                "(https://solscan.io/token/"
                "chipCAT7vi5CZtbZsn9z7iMPXvFwyAnKz3QFu8XVuHm)\n",
                encoding="utf-8",
            )
            (root / "reference.md").write_text(
                "Read the price at https://arbiscan.io/token/"
                "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb#readContract\n",
                encoding="utf-8",
            )

            records = _extract_documented_addresses(root)

        arbitrum = next(row for row in records if row.chain == "Arbitrum")
        solana = next(row for row in records if row.chain == "Solana")
        self.assertEqual(arbitrum.name, "EXM")
        self.assertEqual(arbitrum.chain_id, 42161)
        self.assertEqual(arbitrum.status, "documented")
        self.assertEqual(solana.name, "EXM (NTT)")
        self.assertEqual(solana.status, "documented_unresolved")
        self.assertFalse(
            any(
                row.address.casefold()
                == "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                for row in records
            )
        )

    def test_creates_only_scoped_token_pages_networks_and_links(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Aave V3")
            tokenomics = workspace.vault_entity_directory / "Tokenomics.md"
            tokenomics.write_text(
                "# Tokenomics\n\nAAVE, GHO, and external USDC.",
                encoding="utf-8",
            )
            (workspace.sources_directory / "deployments.md").write_text(
                "| Component | Contract address |\n"
                "|---|---|\n"
                "| Unknown helper | "
                "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |\n",
                encoding="utf-8",
            )
            overview = workspace.vault_entity_directory / "Overview.md"
            overview.write_text(
                "# Overview\n\n"
                "| Field | Value |   |\n|---|---|---|\n"
                "| Governance | AAVE is used. AAVE appears again. |   |\n\n"
                "GHO exists.",
                encoding="utf-8",
            )
            address_book = (
                "IPoolAddressesProvider internal constant "
                "POOL_ADDRESSES_PROVIDER =\n"
                "IPoolAddressesProvider("
                "0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e);\n"
                "AAVE_UNDERLYING = "
                "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9;\n"
                "GHO_UNDERLYING = "
                "0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f;"
            )
            result = run_registry_workflow(
                workspace=workspace,
                provider=FakeTokenProvider(),
                fetch_text=lambda url: address_book,
                fetch_json=lambda url, body: {
                    "data": {
                        "chains": [
                            {"name": "Ethereum", "chainId": 1},
                            {"name": "Base Sepolia", "chainId": 84532},
                        ]
                    }
                },
            )
            # Generated artifacts can be refreshed without another model call.
            result = run_registry_workflow(
                workspace=workspace,
                provider=FakeTokenProvider(),
                fetch_text=lambda url: address_book,
                fetch_json=lambda url, body: {
                    "data": {
                        "chains": [
                            {"name": "Ethereum", "chainId": 1},
                            {"name": "Base Sepolia", "chainId": 84532},
                        ]
                    }
                },
            )
            linked = overview.read_text(encoding="utf-8")
            networks_text = result.network_page.read_text(encoding="utf-8")
            index_text = (
                workspace.vault_entity_directory / "Index.md"
            ).read_text(encoding="utf-8")
            address_page_exists = result.address_page.exists()

        self.assertEqual({token.symbol for token in result.tokens}, {"AAVE", "GHO"})
        self.assertEqual(len(result.token_pages), 2)
        self.assertIn("[[Tokens/AAVE/Index\\|AAVE]]", linked)
        self.assertEqual(linked.count("[[Tokens/AAVE/Index\\|AAVE]]"), 1)
        self.assertIn("AAVE appears again", linked)
        self.assertNotIn("[[Tokens/AAVE/Index|AAVE]]", linked)
        self.assertNotIn("| Field | Value |   |", linked)
        self.assertIn("| Field | Value |", linked)
        self.assertNotIn("Tokens/USDC", linked)
        self.assertIn("testnet", networks_text)
        self.assertIn("[[Tokens/GHO/Index|GHO]]", index_text)
        self.assertEqual(
            {
                record.name
                for record in result.addresses
                if record.provenance == "official_registry"
            },
            {"POOL_ADDRESSES_PROVIDER"},
        )
        self.assertTrue(
            any(
                record.provenance == "documented"
                and record.status == "documented_unresolved"
                for record in result.addresses
            )
        )
        self.assertTrue(address_page_exists)


if __name__ == "__main__":
    unittest.main()
