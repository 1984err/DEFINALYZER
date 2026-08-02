# Verification Page Planning

## Objective

Using the completed research pages and protocol registry, create one concise,
categorized analyst verification checklist for the protocol, chain, or token.

Select only claims whose accuracy could materially change an investment,
trust, security, economic, or operational assessment. Do not verify routine
facts merely because they are observable.

This page is an analyst work queue. Automation should remove routine work when
possible, but manual entries are expected and useful. This step plans evidence
collection; it does not decide whether a claim is true.

## Selection Rules

Include claims concerning:

- token supply, minting, burns, allocation custody, emissions, or vesting
- fee rates, fee recipients, revenue distribution, or treasury control
- governance execution, ownership, upgrades, timelocks, or emergency authority
- collateral, liquidation, solvency, withdrawal, or critical configuration
- oracle, bridge, cross-chain, or required external dependency configuration
- measurable claims that materially affect the investment thesis

Exclude:

- names, addresses, ABI descriptions, and component lists
- ordinary user workflows and interface behavior
- low-impact configuration
- marketing claims without a measurable evidence request
- claims for which the available collector cannot gather relevant evidence;
  place these under **Manual Review** instead

## Identifier Rules

- Assign one stable ID per claim.
- Use `VR-<CATEGORY>-<NNN>`, for example `VR-TOKEN-001`.
- Use the lowercase ID as the collector request ID and Obsidian block ID, for
  example `vr-token-001`.
- Do not create duplicate entries for the same claim. Link every affected
  research page to the single canonical entry.

# <Entity Name> — Verification

## Summary

| Status | Count |
|---|---:|
| Pending | |
| Evidence collected | |
| Manual review | |
| Supported | |
| Contradicted | |
| Inconclusive | |

Populate only current counts. New pages normally begin with pending and manual
review entries.

Create only categories that contain at least one claim, using this order:

1. Token Supply and Economics
2. Fees and Value Accrual
3. Governance and Administrative Control
4. Upgradeability and Ownership
5. Critical Protocol Configuration
6. Oracles and External Dependencies
7. Collateral, Liquidation, and Solvency
8. Treasury and Asset Allocation
9. Cross-Chain Components
10. Measurable Competitive Claims
11. Manual Review

For every claim, use this compact structure:

## <Category>

### <ID> — <Short title>

| Field | Value |
|---|---|
| Status | Pending for Automated or Assisted; Manual review for Manual |
| Claim | Exact concise claim |
| Materiality | One sentence explaining what assessment could change |
| Research source | Obsidian note and heading |
| Registry target | Component name and address, when applicable |
| Check route | Automated, Assisted, or Manual |
| How to check | Short, actionable procedure an analyst can follow |
| Likely source | Official contract, explorer, governance system, API, or documentation location |
| Evidence required | Exact state, event range, transaction, or configuration |
| Collector request | Lowercase request ID, or Manual |
| Evidence | Not collected |
| Last checked | Never |
| Result | Not evaluated |

^<lowercase-id>

Use `Automated` only when the included collector request can directly gather
the required evidence. Use `Assisted` when automation gathers only part of the
evidence. Use `Manual` when no collector request is safe or sufficient. Keep
`Status` consistent with that route: use `Manual review` for a Manual route
and `Pending` for an Automated or Assisted route. Keep
`Materiality`, `How to check`, and `Likely source` concise. Do not add
explanatory paragraphs.

`Research source` and every Research Link Map `Claim Location` must use an
exact Markdown heading from the named research note. Do not use a table-row
label or an invented subsection name.

## Research Link Map

| Verification ID | Research Note | Claim Location | Obsidian Link |
|---|---|---|---|

Use links in this form:

```text
[[<Entity Name> - Verification#^<lowercase-id>|verification]]
```

The link map is an insertion plan for a later script or agent. Do not rewrite
the research page in this output.

## Collector Requests

Add exactly one fenced `definalyzer-verification` JSON block. Include only
requests the collector can execute without guessing.

Supported evidence recipes:

- `contract_snapshot`: code, native balance, ERC-1967 slots, optional `owner()`
- `erc20_snapshot`: name, symbol, decimals, total supply, selected balances
- `eip1967_slots`: implementation, admin, and beacon slots
- `erc20_transfers`: Transfer logs over an explicit deployment-derived range
- `standard_call`: `totalSupply`, `balanceOf`, `allowance`, `owner`, `name`,
  `symbol`, or `decimals`
- `get_transaction` and `get_transaction_receipt`: documented transaction hash
- raw collector operations only when all calldata, slots, topics, addresses,
  and ranges are explicitly available

For `standard_call`, use the parameter key `function`, for example:
`{"function": "totalSupply", "block": "latest"}`. Do not use `method`.

The JSON object must follow this exact shape:

````text
```definalyzer-verification
{
  "schema_version": 1,
  "name": "<collector-compatible-page-name>",
  "requests": [
    {
      "id": "<lowercase-verification-id>",
      "claim": "<exact concise claim>",
      "why_verify": "<one-sentence materiality>",
      "chain": "ethereum",
      "operation": "contract_snapshot",
      "parameters": {
        "block": "latest",
        "include_owner_call": false
      },
      "target": {
        "target_name": "<registry component>",
        "role": "<documented role or null>",
        "address": "<registry-derived address>",
        "chain": "Ethereum",
        "chain_id": 1,
        "source": "<registry source>"
      }
    }
  ]
}
```
````

Use only `ethereum`, `arbitrum`, or `base`. Route other chains to Manual
Review. Preserve registry provenance. Do not add expected values, verdicts, or
interpretation fields.

## Output Rules

- Output only the verification page.
- Do not repeat general research facts.
- Do not claim that collected evidence verifies anything.
- Treat the page as an analyst checklist, not a guarantee of automated
  verification.
- For manual items, provide useful checking instructions and likely official
  sources instead of leaving an unexplained failure.
- Do not create entries simply to populate categories.
- Do not add an Automation Opportunities section.
