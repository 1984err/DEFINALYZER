import json
import re
import tempfile
import unittest
from pathlib import Path

from definalyzer.providers import ProviderResponse
from definalyzer.verification_planning import (
    _compact_candidate_json,
    _normalize_collector_request_aliases,
    _page_sections,
    _normalize_route_statuses,
    _strip_verification_planning_preamble,
    generate_verification_plan,
)
from definalyzer.workspace import WorkspaceManager


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


class VerificationPageSplittingTests(unittest.TestCase):
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
    def test_normalizes_manual_route_status_and_summary(self):
        page = (
            "## Summary\n\n| Status | Count |\n|---|---:|\n"
            "| Pending | 1 |\n| Manual review | 1 |\n\n"
            "### VR-GOV-001 — Authority\n\n"
            "| Field | Value |\n|---|---|\n"
            "| Status | Pending |\n| Check route | Manual |\n"
        )

        normalized = _normalize_route_statuses(page)

        self.assertIn("| Status | Manual review |", normalized)
        self.assertIn("| Pending | 0 |", normalized)
        self.assertIn("| Manual review | 1 |", normalized)

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

        self.assertTrue(job_exists)
        self.assertEqual(first.ready_requests, 1)
        self.assertEqual(first.manual_claims, 0)
        self.assertIn("[[Protocols/Example/Tokenomics\\|Tokenomics]]", page)
        self.assertIn("| Check route | Automated |", page)
        self.assertIn("| How to check |", page)
        self.assertEqual(provider.calls, calls)
        self.assertGreater(second.reused_calls, 0)


if __name__ == "__main__":
    unittest.main()
