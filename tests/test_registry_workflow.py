import json
import tempfile
import unittest
from pathlib import Path

from definalyzer.providers import ProviderResponse
from definalyzer.source_coverage import (
    add_official_source,
    update_source_status,
)
from definalyzer.registry_workflow import (
    TokenRecord,
    _enrich_tokens_from_documented_addresses,
    _extract_documented_addresses,
    _extract_token_catalog_addresses,
    discover_native_tokens,
    link_token_references,
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


class PlaceholderTokenProvider:
    name = "fake"

    def generate(self, prompt, *, working_directory):
        row = {
            "name": "Not documented",
            "symbol": "NOT DOCUMENTED",
            "token_type": "Protocol-issued coin",
            "protocol_relationship": "Assets are created by protocol users",
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
            "utility": "Not documented",
            "source": "Tokenomics.md",
        }
        return ProviderResponse(
            text=json.dumps({"tokens": [row]}),
            provider="fake",
            command=("fake",),
        )


class UnsafeTokenProvider(FakeTokenProvider):
    def generate(self, prompt, *, working_directory):
        document = json.loads(
            super().generate(prompt, working_directory=working_directory).text
        )
        document["tokens"][0]["symbol"] = "../AAVE"
        document["tokens"][0]["source"] = "https://invented.example/source"
        return ProviderResponse(
            text=json.dumps(document),
            provider="fake",
            command=("fake",),
        )


class RegistryWorkflowTests(unittest.TestCase):
    def test_chain_discovery_requests_only_native_coin_and_allows_no_address(self):
        class ChainCoinProvider:
            name = "fake"

            def __init__(self):
                self.prompt = ""

            def generate(self, prompt, *, working_directory):
                self.prompt = prompt
                row = {
                    "name": "Example Coin",
                    "symbol": "EXC",
                    "token_type": "Native coin",
                    "protocol_relationship": "Gas and staking",
                    "network": "Example Chain",
                    "standard": "Native",
                    "address": "Not applicable",
                    "supply": "Not documented",
                    "maximum_supply": "Not documented",
                    "circulating_supply": "Not documented",
                    "emissions": "Epoch issuance",
                    "allocation": "Not documented",
                    "unlocks": "Not documented",
                    "mint_authority": "Protocol rules",
                    "utility": "Gas and staking",
                    "source": "ignored",
                }
                return ProviderResponse(text=json.dumps({"tokens": [row]}), provider="fake", command=("fake",))

        provider = ChainCoinProvider()
        coins = discover_native_tokens(
            provider=provider,
            tokenomics="# Tokenomics\n\nEXC is the native coin.",
            working_directory=Path("."),
            entity_type="chain",
        )

        self.assertEqual(coins[0].address, "Not applicable")
        self.assertIn("chain's native coin", provider.prompt)
        self.assertIn("no contract address", provider.prompt)

    def test_rejects_unsafe_ai_token_symbol(self):
        with self.assertRaisesRegex(ValueError, "token symbol"):
            discover_native_tokens(
                provider=UnsafeTokenProvider(),
                tokenomics="# Tokenomics\n\nAAVE is documented.",
                working_directory=Path("."),
            )

    def test_ai_cannot_override_deterministic_token_source(self):
        provider = FakeTokenProvider()
        response = json.loads(
            provider.generate("", working_directory=Path(".")).text
        )
        response["tokens"][0]["source"] = "https://invented.example/source"

        class AlteredSourceProvider:
            name = "fake"

            def generate(self, prompt, *, working_directory):
                return ProviderResponse(
                    text=json.dumps(response),
                    provider="fake",
                    command=("fake",),
                )

        tokens = discover_native_tokens(
            provider=AlteredSourceProvider(),
            tokenomics="# Tokenomics\n\nAAVE is documented.",
            working_directory=Path("."),
        )

        self.assertEqual(tokens[0].source, "Tokenomics.md")

    def test_rejects_placeholder_token_identity_and_requests_empty_list(self):
        provider = PlaceholderTokenProvider()

        tokens = discover_native_tokens(
            provider=provider,
            tokenomics=(
                "# Tokenomics\n\nNo protocol token is documented. Users "
                "create their own assets."
            ),
            working_directory=Path("."),
        )

        self.assertEqual(tokens, ())

    def test_removes_stale_generated_placeholder_token_page(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="No Token Protocol")
            (workspace.vault_entity_directory / "Tokenomics.md").write_text(
                "# Tokenomics\n\nNo protocol token is documented.",
                encoding="utf-8",
            )
            source = add_official_source(
                workspace,
                category="tokenomics",
                url="https://example.test/tokenomics",
            )
            update_source_status(
                workspace,
                source_id=source.source_id,
                status="collected",
            )
            stale = workspace.vault_root / "Tokens" / "NOT DOCUMENTED" / "Index.md"
            stale.parent.mkdir(parents=True)
            stale.write_text(
                'generated_by: "definalyzer_registry"\n'
                'parent_protocol: "No Token Protocol"\n',
                encoding="utf-8",
            )
            protocol_index = workspace.vault_entity_directory / "Index.md"
            protocol_index.write_text(
                protocol_index.read_text(encoding="utf-8")
                + "\n## Linked Data\n\n"
                "- [[Tokens/NOT DOCUMENTED/Index|NOT DOCUMENTED]]\n",
                encoding="utf-8",
            )

            result = run_registry_workflow(
                workspace=workspace,
                provider=PlaceholderTokenProvider(),
            )
            refreshed = run_registry_workflow(
                workspace=workspace,
                provider=None,
            )

            self.assertEqual(result.tokens, ())
            self.assertEqual(refreshed.tokens, ())
            self.assertFalse(stale.exists())
            self.assertNotIn(
                "NOT DOCUMENTED",
                protocol_index.read_text(encoding="utf-8"),
            )

    def test_parses_gitbook_address_lists_with_chain_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deployments.md").write_text(
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

    def test_parses_chain_address_bridge_tables_with_section_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "contracts.md").write_text(
                "## \n"
                "Example Vault\n"
                "[](https://docs.example/contracts#example-vault)\n"
                "| Chain | Token Address | Bridge |\n"
                "|---|---|---|\n"
                "| Ethereum | 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | "
                "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb |\n"
                "| Derive | 0xcccccccccccccccccccccccccccccccccccccccc | "
                "0xdddddddddddddddddddddddddddddddddddddddd |\n",
                encoding="utf-8",
            )

            records = _extract_documented_addresses(root)

        ethereum_token = next(
            row
            for row in records
            if row.chain == "Ethereum" and row.component_type == "Token"
        )
        ethereum_bridge = next(
            row
            for row in records
            if row.chain == "Ethereum" and row.component_type == "Bridge"
        )
        derive_token = next(
            row
            for row in records
            if row.chain == "Derive" and row.component_type == "Token"
        )
        self.assertEqual(ethereum_token.name, "Example Vault")
        self.assertEqual(ethereum_token.chain_id, 1)
        self.assertEqual(ethereum_token.status, "documented")
        self.assertEqual(ethereum_bridge.name, "Example Vault Bridge")
        self.assertEqual(derive_token.chain_id, 957)
        self.assertEqual(derive_token.status, "documented_unresolved")

    def test_ignores_addresses_embedded_in_formula_description_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "math.md").write_text(
                "| Name | Description | Formula |\n"
                "|---|---|---|\n"
                "| Market | 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | x + y |\n",
                encoding="utf-8",
            )

            records = _extract_documented_addresses(root)

        self.assertEqual(records, ())

    def test_documented_token_address_uses_explorer_chain_and_enriches_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bridge.md").write_text(
                "2. Input PENDLE token address if it isn't listed\n"
                "[0x808507121B80c02388fAd14726482e061B8da827]"
                "(https://etherscan.io/address/"
                "0x808507121B80c02388fAd14726482e061B8da827)\n",
                encoding="utf-8",
            )
            records = _extract_documented_addresses(root)
            token = TokenRecord(
                name="PENDLE",
                symbol="PENDLE",
                token_type="Native protocol token",
                protocol_relationship="Governance",
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
                utility="Governance",
                source="Tokenomics.md",
            )

            enriched = _enrich_tokens_from_documented_addresses([token], list(records))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].chain, "Ethereum")
        self.assertEqual(enriched[0].network, "Ethereum")
        self.assertEqual(
            enriched[0].address,
            "0x808507121B80c02388fAd14726482e061B8da827",
        )

    def test_parses_network_columns_and_excludes_testnet_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "contracts.md").write_text(
                "## Governance\n"
                "| Contract | Ethereum | Goerli |\n"
                "|---|---|---|\n"
                "| Governor | 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | "
                "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb |\n"
                "# \n"
                "Testnet\n"
                "## Example Token\n"
                "| Chain | Token Address | Bridge |\n"
                "|---|---|---|\n"
                "| Ethereum | 0xcccccccccccccccccccccccccccccccccccccccc | "
                "0xdddddddddddddddddddddddddddddddddddddddd |\n",
                encoding="utf-8",
            )

            records = _extract_documented_addresses(root)

        self.assertEqual(len(records), 2)
        mainnet = next(row for row in records if row.chain == "Ethereum")
        testnet = next(row for row in records if row.chain == "Goerli")
        self.assertEqual(mainnet.name, "Governor")
        self.assertEqual(mainnet.status, "documented")
        self.assertEqual(testnet.name, "Governor")
        self.assertEqual(testnet.status, "documented_unresolved")

    def test_excludes_bulk_address_catalogs_and_tutorials_from_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "learn").mkdir()
            (root / "learn" / "governance.md").write_text(
                "| Governance contract | "
                "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |\n",
                encoding="utf-8",
            )
            (root / "developers" / "contracts").mkdir(parents=True)
            (root / "developers" / "contracts" / "addresses.md").write_text(
                "| Helper | 0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb |\n",
                encoding="utf-8",
            )
            (root / "tutorials").mkdir()
            (root / "tutorials" / "example.md").write_text(
                "| Example | 0xcccccccccccccccccccccccccccccccccccccccc |\n",
                encoding="utf-8",
            )

            records = _extract_documented_addresses(root)

        self.assertEqual(
            [record.address for record in records],
            ["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
        )

    def test_reads_only_exact_token_rows_from_token_catalog_section(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.mkdir(exist_ok=True)
            (root / "addresses.md").write_text(
                "## Core contracts\n"
                "| MORPHO | 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |\n"
                "## MORPHO Token\n"
                "| MORPHO | [0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb]"
                "(https://etherscan.io/address/"
                "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb) |\n"
                "| MORPHO wrapper | "
                "0xcccccccccccccccccccccccccccccccccccccccc |\n",
                encoding="utf-8",
            )
            from definalyzer.registry_workflow import TokenRecord

            token_row = json.loads(
                FakeTokenProvider().generate("", working_directory=root).text
            )["tokens"][0]
            token_row["name"] = "MORPHO"
            token_row["symbol"] = "MORPHO"
            records = _extract_token_catalog_addresses(
                root,
                [TokenRecord(**token_row)],
            )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].chain, "Ethereum")
        self.assertEqual(
            records[0].address,
            "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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

    def test_registry_catalog_hashes_sources_and_links_official_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            (workspace.vault_entity_directory / "Tokenomics.md").write_text(
                "# Tokenomics\n\nAAVE is the governance token.",
                encoding="utf-8",
            )
            source = workspace.sources_directory / "contracts.md"
            source.write_text(
                '---\nsource: "https://docs.example.test/contracts"\n---\n\n'
                "## Ethereum\n\n"
                "| Component | Contract address |\n"
                "|---|---|\n"
                "| Treasury | 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |\n",
                encoding="utf-8",
            )

            result = run_registry_workflow(
                workspace=workspace,
                provider=FakeTokenProvider(),
            )
            document = json.loads(result.registry_path.read_text(encoding="utf-8"))
            registry_page = result.address_page.read_text(encoding="utf-8")

        catalog = document["source_catalog"]
        self.assertEqual(catalog[0]["path"], "contracts.md")
        self.assertEqual(
            catalog[0]["source_url"],
            "https://docs.example.test/contracts",
        )
        self.assertRegex(catalog[0]["sha256"], r"^[a-f0-9]{64}$")
        self.assertIn(
            "[contracts.md#L9](https://docs.example.test/contracts)",
            registry_page,
        )

    def test_github_source_provenance_keeps_exact_line_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="GitHub Example")
            (workspace.vault_entity_directory / "Tokenomics.md").write_text(
                "# Tokenomics\n\nAAVE is the governance token.",
                encoding="utf-8",
            )
            source = workspace.sources_directory / "contracts.md"
            source.write_text(
                "<!-- definalyzer-source: "
                "https://github.com/example/docs/blob/abc/contracts.md -->\n\n"
                "## Ethereum\n\n"
                "| Component | Contract address |\n"
                "|---|---|\n"
                "| Treasury | 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |\n",
                encoding="utf-8",
            )

            result = run_registry_workflow(
                workspace=workspace,
                provider=FakeTokenProvider(),
            )
            registry_page = result.address_page.read_text(encoding="utf-8")

        self.assertIn(
            "(https://github.com/example/docs/blob/abc/contracts.md#L7)",
            registry_page,
        )

    def test_token_linking_skips_frontmatter_headings_and_code_fences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "Overview.md"
            page.write_text(
                '---\ntitle: "AAVE reference"\n---\n\n'
                "# AAVE Overview\n\n"
                "```solidity\ncontract AAVE {}\n```\n\n"
                "AAVE controls governance.\n",
                encoding="utf-8",
            )
            token = TokenRecord(
                name="Aave",
                symbol="AAVE",
                token_type="Governance",
                protocol_relationship="Native",
                network="Ethereum",
                standard="ERC-20",
                address="Not documented",
                supply="Not documented",
                maximum_supply="Not documented",
                circulating_supply="Not documented",
                emissions="Not documented",
                allocation="Not documented",
                unlocks="Not documented",
                mint_authority="Not documented",
                utility="Governance",
                source="Tokenomics.md",
            )

            link_token_references(root, [token])
            text = page.read_text(encoding="utf-8")

        self.assertIn('title: "AAVE reference"', text)
        self.assertIn("# AAVE Overview", text)
        self.assertIn("contract AAVE {}", text)
        self.assertIn("[[Tokens/AAVE/Index|AAVE]] controls governance.", text)


if __name__ == "__main__":
    unittest.main()
