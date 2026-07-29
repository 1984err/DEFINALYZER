import tempfile
import unittest
from pathlib import Path

from definalyzer.obsidian_links import insert_verification_links


class ObsidianLinkTests(unittest.TestCase):
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
            verification = root / "Verification" / "Example - Verification.md"
            verification.parent.mkdir()
            verification.write_text(
                "# Example — Verification\n\n"
                "## Research Link Map\n\n"
                "| Verification ID | Research Note | Claim Location | "
                "Obsidian Link |\n"
                "|---|---|---|---|\n"
                "| VR-GOV-001 | "
                "[[Protocols/Example/Architecture\\|Architecture]] | "
                "Upgrade and Control Model; Critical Trust Boundaries | "
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
        self.assertIn(
            "[[Verification/Example - Verification#^vr-gov-001|"
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


if __name__ == "__main__":
    unittest.main()
