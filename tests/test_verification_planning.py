import json
import re
import tempfile
import unittest
from pathlib import Path

from definalyzer.providers import ProviderResponse
from definalyzer.verification_planning import (
    _compact_candidate_json,
    _normalize_collector_request_aliases,
    _normalize_research_links,
    _page_sections,
    _normalize_route_statuses,
    _strip_verification_planning_preamble,
    _validate_page,
    _verification_catalog,
    _validate_candidate_response,
    _candidate_prompt,
    _candidate_reduction_prompt,
    _final_prompt,
    generate_verification_plan,
)
from definalyzer.workspace import WorkspaceManager


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


class VerificationPageSplittingTests(unittest.TestCase):
    def test_documentation_gaps_are_not_claims_but_negative_claims_are(self):
        claims = [
            "Administrative authority is not documented in collected sources.",
            "Governance coverage is partial.",
            "The contract does not allow upgrades.",
            "One source says all stake is burned; another says part is burned.",
        ]
        rows = [{
            "claim": claim, "materiality": "Loss exposure",
            "category": "Governance", "research_note": "Governance.md",
            "claim_location": "Controls", "evidence_needed": "Current rules",
        } for claim in claims]
        result = _validate_candidate_response(json.dumps({"candidates": rows}))
        self.assertEqual([row["claim"] for row in result["candidates"]], claims[2:])

    def test_selection_rules_apply_at_every_planning_stage(self):
        for prompt in (
            _candidate_prompt("notes"),
            _candidate_reduction_prompt([]),
            _final_prompt(entity="Example", template="template", registry="{}", candidates=[]),
        ):
            self.assertIn("Manual Review is a route, not a", prompt)
            self.assertIn("never promote them", prompt)
            self.assertIn("preserve both documented assertions", prompt)

    def test_final_page_rejects_gap_before_publication(self):
        provider = FakePlanningProvider()
        page = provider.generate("final", working_directory=Path(".")).text
        page = page.replace(
            "| Claim | Token supply is material. |",
            "| Claim | Upgrade authority is not documented. |",
        )
        with self.assertRaisesRegex(ValueError, "documentation gap"):
            _validate_page(page, "Example")

    def test_new_plans_require_subject_categories_but_legacy_pages_still_read(self):
        page = FakePlanningProvider().generate("final", working_directory=Path(".")).text
        page = page.replace("## Token Supply and Economics", "## Manual Review")
        _validate_page(page, "Example")
        with self.assertRaisesRegex(ValueError, "Group verification claims by subject"):
            _validate_page(page, "Example", require_subject_categories=True)

    def test_normalizes_chain_research_links_to_chain_folder(self):
        page = Path("Architecture.md")
        normalized = _normalize_research_links(
            "| Research source | [[Architecture]] |\n",
            entity="Example Chain",
            entity_type="chain",
            research_pages=(page,),
        )

        self.assertIn(
            "[[Chains/Example Chain/Architecture\\|Architecture]]",
            normalized,
        )

    def test_splits_oversized_page_without_dropping_content(self):
        original = ("material fact\n\n" * 100).strip()
        sections = _page_sections("Security.md", original, 300)

        self.assertGreater(len(sections), 1)
        reconstructed = "".join(
            re.sub(
                r"^\s*## SOURCE NOTE: .*?\n\nPart \d+/\d+\n\n",
                "",
                section,
            ).strip()
            for section in sections
        )
        self.assertEqual(
            re.sub(r"\s+", "", reconstructed),
            re.sub(r"\s+", "", original),
        )


class FakePlanningProvider:
    name = "fake"

    def __init__(self):
        self.calls = 0

    def generate(self, prompt, *, working_directory):
        self.calls += 1
        if "Material Verification Candidate Selection" in prompt:
            text = json.dumps(
                {
                    "candidates": [
                        {
                            "claim": "Token supply is material.",
                            "materiality": "Unexpected minting changes dilution.",
                            "category": "Token Supply and Economics",
                            "research_note": "Tokenomics.md",
                            "claim_location": "Supply",
                            "evidence_needed": "Current total supply.",
                        }
                    ]
                }
            )
        else:
            text = f"""# Example — Verification

## Summary

| Status | Count |
|---|---:|
| Pending | 1 |
| Manual review | 0 |

## Token Supply and Economics

### VR-TOKEN-001 — Supply snapshot

| Field | Value |
|---|---|
| Status | Pending |
| Claim | Token supply is material. |
| Materiality | Unexpected minting changes dilution. |
| Research source | [[Protocols/Example/Tokenomics\\|Tokenomics]] |
| Registry target | EXM |
| Claim type | On-chain state/events |
| Evidence availability | Public |
| Recommended method | Direct RPC |
| Check route | Automated |
| How to check | Read totalSupply at a pinned block. |
| Likely source | Published token contract and Ethereum RPC. |
| Evidence required | Current total supply. |
| Collector request | vr-token-001 |
| Evidence | Not collected |
| Last checked | Never |
| Result | Not evaluated |

^vr-token-001

## Collector Requests

```definalyzer-verification
{{
  "schema_version": 1,
  "name": "example-verification",
  "requests": [
    {{
      "id": "vr-token-001",
      "claim": "Token supply is material.",
      "why_verify": "Unexpected minting changes dilution.",
      "chain": "ethereum",
      "operation": "erc20_snapshot",
      "parameters": {{"block": "latest"}},
      "target": {{
        "target_name": "EXM",
        "role": "governance token",
        "address": "{ADDRESS}",
        "chain": "Ethereum",
        "chain_id": 1,
        "source": "registry.json"
      }}
    }}
  ]
}}
```
"""
        return ProviderResponse(text=text, provider="fake", command=("fake",))


class VerificationPlanningTests(unittest.TestCase):
    def test_migrates_manual_route_status_without_losing_manual_route(self):
        page = (
            "## Summary\n\n| Status | Count |\n|---|---:|\n"
            "| Pending | 1 |\n| Manual review | 1 |\n\n"
            "### VR-GOV-001 — Authority\n\n"
            "| Field | Value |\n|---|---|\n"
            "| Status | Pending |\n| Check route | Manual |\n"
        )

        normalized = _normalize_route_statuses(page)

        self.assertIn("| Status | Pending |", normalized)
        self.assertIn("| Check route | Manual |", normalized)
        self.assertIn("| Pending | 1 |", normalized)
        self.assertNotIn("| Manual review | 1 |", normalized)

    def test_catalog_separates_route_availability_method_and_status(self):
        page = (
            "# Example — Verification\n\n## Legal and Organization\n\n"
            "### VR-LEGAL-001 — Registration\n\n"
            "| Field | Value |\n|---|---|\n"
            "| Status | Pending |\n"
            "| Claim | The entity is registered. |\n"
            "| Claim type | Legal/regulatory |\n"
            "| Evidence availability | Public |\n"
            "| Recommended method | Official source |\n"
            "| Check route | Manual |\n"
        )

        entry = _verification_catalog(page, entity="Example")["entries"][0]

        self.assertEqual(entry["claim_type"], "Legal/regulatory")
        self.assertEqual(entry["evidence_availability"], "Public")
        self.assertEqual(entry["recommended_method"], "Official source")
        self.assertEqual(entry["check_route"], "Manual")
        self.assertEqual(entry["status"], "Pending")

    def test_dune_candidate_is_optional_public_metadata(self):
        page = f"""# Example — Verification

## Fees and Value Accrual

### VR-FEE-001 — Historical fees

| Field | Value |
|---|---|
| Status | Pending |
| Claim type | On-chain state/events |
| Evidence availability | Public |
| Recommended method | Dune candidate |
| Optional Dune query | Available |
| Check route | Manual |
| How to check | Aggregate documented fee events. |
| Likely source | Dune indexed Ethereum data. |

## Collector Requests

```definalyzer-verification
{{"schema_version":1,"name":"example-verification","requests":[]}}
```
"""

        validated = _validate_page(page, "Example")
        entry = _verification_catalog(validated, entity="Example")["entries"][0]

        self.assertTrue(entry["dune_eligible"])

    def test_dune_candidate_rejects_nonpublic_evidence(self):
        page = f"""# Example — Verification

## Fees and Value Accrual

### VR-FEE-001 — Internal accounting

| Field | Value |
|---|---|
| Status | Pending |
| Claim type | Organizational/private |
| Evidence availability | Restricted/private |
| Recommended method | Dune candidate |
| Optional Dune query | Available |
| Check route | Manual |
| How to check | Request internal records. |
| Likely source | Protocol operator. |

## Collector Requests

```definalyzer-verification
{{"schema_version":1,"name":"example-verification","requests":[]}}
```
"""

        with self.assertRaisesRegex(ValueError, "public evidence"):
            _validate_page(page, "Example")

    def test_compacts_candidate_json_without_losing_fields(self):
        original = json.dumps(
            {
                "candidates": [
                    {
                        "claim": "Material claim",
                        "materiality": "Material reason",
                    }
                ]
            },
            indent=2,
        )

        compact = _compact_candidate_json(original)

        self.assertEqual(json.loads(compact), json.loads(original))
        self.assertLess(len(compact), len(original))

    def test_normalizes_standard_call_method_alias(self):
        page = (
            "```definalyzer-verification\n"
            '{"schema_version":1,"name":"example","requests":['
            '{"operation":"standard_call","parameters":'
            '{"method":"totalSupply","block":"latest"}}]}\n'
            "```"
        )

        normalized = _normalize_collector_request_aliases(page)

        self.assertIn('"function": "totalSupply"', normalized)
        self.assertNotIn('"method"', normalized)

    def test_normalizes_collector_job_name_from_project_slug(self):
        page = (
            "```definalyzer-verification\n"
            '{"schema_version":1,"name":"Project Name verification",'
            '"requests":[]}\n```'
        )

        normalized = _normalize_collector_request_aliases(
            page,
            job_name="project-name-verification",
        )

        self.assertIn('"name": "project-name-verification"', normalized)

    def test_strips_echoed_planning_template_before_entity_page(self):
        page = (
            "# Verification Page Planning\n\nInstructions\n\n"
            "# Example — Verification\n\n## Summary\n"
        )

        normalized = _strip_verification_planning_preamble(
            page,
            entity="Example",
        )

        self.assertTrue(normalized.startswith("# Example — Verification"))
        self.assertNotIn("Verification Page Planning", normalized)

    def test_creates_page_validated_job_and_reuses_ledgers(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(Path(directory) / "output")
            workspace = manager.create_project(name="Example")
            (workspace.vault_entity_directory / "Tokenomics.md").write_text(
                "# Tokenomics\n\nThe token supply is material.",
                encoding="utf-8",
            )
            workspace.registry_directory.mkdir(parents=True, exist_ok=True)
            (workspace.registry_directory / "registry.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "tokens": [
                            {
                                "symbol": "EXM",
                                "address": ADDRESS,
                                "network": "Ethereum",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            prompts = Path(__file__).resolve().parents[1] / "prompts"
            provider = FakePlanningProvider()
            first = generate_verification_plan(
                workspace=workspace,
                provider=provider,
                prompts_root=prompts,
            )
            calls = provider.calls
            second = generate_verification_plan(
                workspace=workspace,
                provider=provider,
                prompts_root=prompts,
            )
            page = first.page_path.read_text(encoding="utf-8")
            job_exists = first.job_path.exists()
            catalog_exists = first.catalog_path.exists()

        self.assertTrue(job_exists)
        self.assertTrue(catalog_exists)
        self.assertEqual(first.ready_requests, 1)
        self.assertEqual(first.manual_claims, 0)
        self.assertIn("[[Protocols/Example/Tokenomics\\|Tokenomics]]", page)
        self.assertIn("| Check route | Automated |", page)
        self.assertIn("| How to check |", page)
        self.assertEqual(provider.calls, calls)
        self.assertGreater(second.reused_calls, 0)


if __name__ == "__main__":
    unittest.main()
