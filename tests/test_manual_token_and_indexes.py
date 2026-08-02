import tempfile
import unittest
from pathlib import Path

from definalyzer.registry_workflow import (
    TokenRecord,
    project_tokens,
    upsert_manual_token,
)
from definalyzer.vault_indexes import generate_vault_indexes
from definalyzer.workspace import WorkspaceManager


class ManualTokenAndIndexTests(unittest.TestCase):
    def test_manual_token_entry_is_deterministic_and_refreshable(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            token = TokenRecord(
                name="Example Token",
                symbol="EX",
                token_type="Governance token",
                protocol_relationship="Native governance token",
                network="Ethereum",
                standard="ERC-20",
                address="0x1234567890abcdef1234567890abcdef12345678",
                supply="Not documented",
                maximum_supply="Not documented",
                circulating_supply="Not documented",
                emissions="No ongoing emissions documented",
                allocation="Not documented",
                unlocks="Not documented",
                mint_authority="Not documented",
                utility="Governance",
                source="https://docs.example.test/token",
            )
            first = upsert_manual_token(workspace=workspace, token=token)
            revised = TokenRecord(**{**token.__dict__, "utility": "Governance and fees"})
            second = upsert_manual_token(workspace=workspace, token=revised)
            stored_utility = project_tokens(workspace)[0].utility
            token_page_exists = second.token_pages[0].exists()

        self.assertEqual(len(first.tokens), 1)
        self.assertEqual(len(second.tokens), 1)
        self.assertEqual(stored_utility, "Governance and fees")
        self.assertTrue(token_page_exists)

    def test_indexes_link_projects_tokens_and_nested_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            token_directory = workspace.vault_root / "Tokens" / "EX"
            token_directory.mkdir(parents=True)
            (token_directory / "Index.md").write_text(
                '---\nentity: "EX"\nentity_type: "token"\n'
                'parent_protocol: "Example"\n---\n\n'
                "## Networks and Addresses\n\n"
                "| Network | Standard | Address | Source |\n"
                "|---|---|---|---|\n| Ethereum | ERC-20 | `0x0` | docs |\n",
                encoding="utf-8",
            )
            workspace.verification_page_path.write_text(
                "# Verification\n\n| Status | Count |\n|---|---:|\n"
                "| Pending | 2 |\n| Manual review | 1 |\n",
                encoding="utf-8",
            )
            paths = generate_vault_indexes(manager.root)
            research = paths[1].read_text(encoding="utf-8")
            tokens = paths[2].read_text(encoding="utf-8")
            verification = paths[3].read_text(encoding="utf-8")

        self.assertIn("[[Protocols/Example/Index\\|Example]]", research)
        self.assertIn("[[Tokens/EX/Index\\|EX]]", tokens)
        self.assertIn("| Example | Ethereum |", tokens)
        self.assertIn("[[Verification/Example/Index\\|Example]]", verification)
        self.assertIn("| 2 | 1 |", verification)


if __name__ == "__main__":
    unittest.main()
