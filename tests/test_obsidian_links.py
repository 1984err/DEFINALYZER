import tempfile
import unittest
from pathlib import Path

from definalyzer.obsidian_links import (
    insert_verification_links,
    strip_generated_verification_links,
)


class ObsidianLinkTests(unittest.TestCase):
    def test_removed_claim_clears_old_generated_link_but_keeps_analyst_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root / "research"
            research.mkdir()
            note = research / "Security.md"
            note.write_text(
                "# Security\n\nVerification: [[Verification/Example/Index#^vr-1|VR-1]]\n\n"
                "Analyst note: investigate permissions.\n",
                encoding="utf-8",
            )
            verification = root / "Verification" / "Example" / "Index.md"
            verification.parent.mkdir(parents=True)
            verification.write_text(
                "## Research Link Map\n\n"
                "| Verification ID | Research Note | Claim Location | Obsidian Link |\n"
                "|---|---|---|---|\n\n## Collector Requests\n",
                encoding="utf-8",
            )
            result = insert_verification_links(
                verification_page=verification, research_directory=research,
            )
            content = note.read_text(encoding="utf-8")
        self.assertNotIn("VR-1", content)
        self.assertIn("Analyst note: investigate permissions.", content)
        self.assertEqual(result.inserted_links, 0)

    def test_strips_generated_line_with_multiple_link_separators(self):
        text = (
            "## Control\n\n"
            "Verification: [[Verification/Example/Index#^vr-1|VR-1]] · "
            "[[Verification/Example/Index#^vr-2|VR-2]]\n\n"
            "| Fact | Value |\n"
        )

        cleaned = strip_generated_verification_links(text)

        self.assertNotIn("Verification:", cleaned)
        self.assertIn("| Fact | Value |", cleaned)

    def test_inserts_compact_links_at_exact_headings_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root / "Protocols" / "Example"
            research.mkdir(parents=True)
            architecture = research / "Architecture.md"
            architecture.write_text(
                "# Architecture\n\n"
                "## Upgrade and Control Model\n\n"
                "| Fact | Value |\n|---|---|\n| Upgrade | Governed |\n",
                encoding="utf-8",
            )
            verification = root / "Verification" / "Example" / "Index.md"
            verification.parent.mkdir(parents=True)
            verification.write_text(
                "# Example — Verification\n\n"
                "## Research Link Map\n\n"
                "| Verification ID | Research Note | Claim Location | "
                "Obsidian Link |\n"
                "|---|---|---|---|\n"
                "| VR-GOV-001 | "
                "[[Protocols/Example/Architecture\\|Architecture]] | "
                "Upgrade and Control Model: proxy authority; "
                "Critical Trust Boundaries | "
                "[[Example - Verification#^vr-gov-001\\|verification]] |\n\n"
                "## Collector Requests\n",
                encoding="utf-8",
            )

            first = insert_verification_links(
                verification_page=verification,
                research_directory=research,
            )
            second = insert_verification_links(
                verification_page=verification,
                research_directory=research,
            )
            text = architecture.read_text(encoding="utf-8")

        self.assertEqual(first.inserted_links, 1)
        self.assertEqual(second.inserted_links, 1)
        self.assertEqual(text.count("VR-GOV-001"), 1)
        self.assertNotIn("definalyzer-verification-links", text)
        self.assertIn("VR-GOV-001]]\n\n| Fact | Value |", text)
        self.assertIn(
            "[[Verification/Example/Index#^vr-gov-001|"
            "VR-GOV-001]]",
            text,
        )
        self.assertEqual(first.unresolved_mappings, ())

    def test_reports_unknown_heading_without_guessing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root / "research"
            research.mkdir()
            (research / "Security.md").write_text(
                "# Security\n\n## Audits\n",
                encoding="utf-8",
            )
            verification = root / "Verification.md"
            verification.write_text(
                "## Research Link Map\n\n"
                "| Verification ID | Research Note | Claim Location | "
                "Obsidian Link |\n"
                "|---|---|---|---|\n"
                "| VR-SEC-001 | [[Security]] | Missing Heading | "
                "[[Verification#^vr-sec-001\\|verification]] |\n\n"
                "## Collector Requests\n",
                encoding="utf-8",
            )
            result = insert_verification_links(
                verification_page=verification,
                research_directory=research,
            )

        self.assertEqual(result.inserted_links, 0)
        self.assertEqual(len(result.unresolved_mappings), 1)

    def test_maps_unique_table_phrase_to_its_enclosing_heading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root / "research"
            research.mkdir()
            tokenomics = research / "Tokenomics.md"
            tokenomics.write_text(
                "# Tokenomics\n\n"
                "## Allocation and Vesting\n\n"
                "| Group | Status |\n|---|---|\n"
                "| Team and Investors | Fully vested |\n",
                encoding="utf-8",
            )
            verification = root / "Verification.md"
            verification.write_text(
                "## Research Link Map\n\n"
                "| Verification ID | Research Note | Claim Location | "
                "Obsidian Link |\n"
                "|---|---|---|---|\n"
                "| VR-TOKEN-001 | [[Tokenomics]] | Team and Investors | "
                "[[Verification#^vr-token-001\\|verification]] |\n\n"
                "## Collector Requests\n",
                encoding="utf-8",
            )

            result = insert_verification_links(
                verification_page=verification,
                research_directory=research,
            )
            text = tokenomics.read_text(encoding="utf-8")

        self.assertEqual(result.inserted_links, 1)
        self.assertEqual(result.unresolved_mappings, ())
        self.assertIn("## Allocation and Vesting\n\nVerification:", text)

    def test_accepts_chain_research_links_and_writes_idempotently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root / "Chains" / "Example Chain"
            research.mkdir(parents=True)
            architecture = research / "Architecture.md"
            architecture.write_text(
                "# Architecture\n\n## Consensus\n\n| Fact | Value |\n|---|---|\n",
                encoding="utf-8",
            )
            verification = root / "Verification" / "Example Chain" / "Index.md"
            verification.parent.mkdir(parents=True)
            verification.write_text(
                "# Verification\n\n## Research Link Map\n\n"
                "| Verification ID | Research Note | Claim Location | Obsidian Link |\n"
                "|---|---|---|---|\n"
                "| VR-ARC-001 | "
                "[[Chains/Example Chain/Architecture\\|Architecture]] | "
                "Consensus | [[Example Chain - Verification#^vr-arc-001\\|verification]] |\n\n"
                "## Collector Requests\n",
                encoding="utf-8",
            )

            first = insert_verification_links(
                verification_page=verification,
                research_directory=research,
            )
            second = insert_verification_links(
                verification_page=verification,
                research_directory=research,
            )
            text = architecture.read_text(encoding="utf-8")

        self.assertEqual(first.unresolved_mappings, ())
        self.assertEqual(second.unresolved_mappings, ())
        self.assertEqual(text.count("VR-ARC-001"), 1)


if __name__ == "__main__":
    unittest.main()
