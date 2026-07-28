import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPTS = PROJECT_ROOT / "prompts"
TEMPLATES = PROMPTS / "templates"
TOPIC_TEMPLATES = (
    "template_architecture.md",
    "template_competitive_analysis.md",
    "template_governance.md",
    "template_integrations_dependencies.md",
    "template_liquidity.md",
    "template_protocol_overview.md",
    "template_revenue_model.md",
    "template_risk_assessment.md",
    "template_security.md",
    "template_tokenomics.md",
)


class PromptStructureTests(unittest.TestCase):
    def test_topic_templates_do_not_restore_redundant_sections(self):
        forbidden_headings = (
            "# Analyst Notes",
            "# Key Takeaways",
            "# Verification Opportunities",
            "# Automation Opportunities",
        )

        for filename in TOPIC_TEMPLATES:
            text = (TEMPLATES / filename).read_text(encoding="utf-8")

            with self.subTest(filename=filename):
                for heading in forbidden_headings:
                    self.assertNotIn(heading, text)

    def test_topic_templates_are_fact_first_and_track_material_unknowns(self):
        for filename in TOPIC_TEMPLATES:
            text = (TEMPLATES / filename).read_text(encoding="utf-8")

            with self.subTest(filename=filename):
                self.assertIn("# Material Unknowns", text)
                self.assertIn(
                    "TEMPLATE INSTRUCTIONS — DO NOT INCLUDE IN OUTPUT",
                    text,
                )

    def test_verification_template_is_categorized_and_import_compatible(self):
        text = (
            TEMPLATES / "template_verification_page.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Token Supply and Economics", text)
        self.assertIn("Governance and Administrative Control", text)
        self.assertIn("Manual Review", text)
        self.assertEqual(text.count("```definalyzer-verification"), 1)
        self.assertIn('"schema_version": 1', text)
        self.assertIn("^<lowercase-id>", text)

    def test_registry_uses_one_canonical_address_inventory(self):
        text = (
            TEMPLATES / "protocol_registry_extraction.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(text.count("## Address Inventory"), 1)
        self.assertNotIn("## Verification Targets", text)
        self.assertNotIn("## Core Contracts", text)

    def test_old_duplicate_research_template_is_removed(self):
        self.assertFalse((PROMPTS / "research.md").exists())


if __name__ == "__main__":
    unittest.main()
