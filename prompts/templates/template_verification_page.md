# Verification Page Planning

## Objective

Using the completed research pages and protocol registry, create one concise,
categorized analyst verification checklist for the protocol, chain, or token.

Select only claims whose accuracy could materially change an investment,
trust, security, economic, or operational assessment. Do not verify routine
facts merely because they are observable.

This page is an analyst work queue. Automation should remove routine work when
possible, but analyst-routed entries are expected and useful. This step plans
evidence collection; it does not decide whether a claim is true. Keep claim
type, evidence availability, recommended method, and result status separate.

## Selection Rules

Include claims concerning:

- token supply, minting, burns, allocation custody, emissions, or vesting
- fee rates, fee recipients, revenue distribution, or treasury control
- governance execution, ownership, upgrades, timelocks, or emergency authority
- collateral, liquidation, solvency, withdrawal, or critical configuration
- oracle, bridge, cross-chain, or required external dependency configuration
- measurable claims that materially affect the investment thesis

Exclude:

- collection gaps, `Not documented` placeholders, and assessments that source
  coverage is missing or partial; retain these under research Material Unknowns
- names, addresses, ABI descriptions, and component lists
- ordinary user workflows and interface behavior
- low-impact configuration
- marketing claims without a measurable evidence request

When documented statements differ, keep both assertions and source references
and request clarification. Do not assert that different wording proves a
contradiction. Never invent a factual claim from missing information.

Collector support determines the Check route, not whether a material claim
qualifies. Keep manual checks in their subject categories, including on
unsupported chains. `Manual Review` is not a subject category or a shared quota.

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
| Confirmed | |
| Contradicted | |
| Inconclusive | |
| Public evidence unavailable | |

Populate only current counts. New pages normally begin with pending entries.

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

For every claim, use this compact structure:

## <Category>

### <ID> — <Short title>

| Field | Value |
|---|---|
| Status | Pending |
| Claim | Exact concise claim |
| Materiality | One sentence explaining what assessment could change |
| Research source | Obsidian note and heading |
| Registry target | Component name and address, when applicable |
| Claim type | On-chain state/events, Smart contract/code, Governance, Legal/regulatory, Organizational/private, Off-chain operational, or Market/external data |
| Evidence availability | Public, Restricted/private, Not documented, or Unknown |
| Recommended method | Direct RPC, Dune candidate, Official source, External database, Analyst review, or Public evidence unavailable |
| Optional Dune query | Available; include this row only for Dune candidate methods |
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
`Status` independent from that route: all new checks begin as `Pending`.
Use `Public evidence unavailable` only when the required evidence is known not
to be publicly accessible; lack of documentation alone is not enough. Keep
`Materiality`, `How to check`, and `Likely source` concise. Do not add
explanatory paragraphs.

Use `Dune candidate` conservatively for public on-chain history or aggregate
questions that can reasonably be expressed as SQL over indexed blockchain
data. Do not use it for legal, private, organizational, undocumented,
forward-looking, or source-code judgment claims. The marker only offers an
optional query-writing assistant; it does not run Dune or verify the claim.

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

Use only `ethereum`, `arbitrum`, or `base` in collector requests. Set Check route
to Manual for other chains, retaining their subject categories. Preserve registry
provenance. Do not add expected values, verdicts, or
interpretation fields.

## Output Rules

- Output only the verification page.
- Do not repeat general research facts.
- Do not claim that collected evidence verifies anything.
- Treat the page as an analyst checklist, not a guarantee of automated
  verification.
- Never imply that Dune is required or that every manual check is Dune-eligible.
- For analyst-routed items, provide useful checking instructions and likely official
  sources instead of leaving an unexplained failure.
- Do not create entries simply to populate categories.
- Do not add an Automation Opportunities section.
