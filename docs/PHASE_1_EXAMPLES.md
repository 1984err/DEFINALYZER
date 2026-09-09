# Phase 1 worked examples

Companion to [RESEARCH_DESIGN_V2.md](RESEARCH_DESIGN_V2.md).

All entities, passages, dates, and behavior below are fictional design fixtures.
They are not findings about live chains, protocols, or tokens. Short IDs such as
`S-1` and `F-1` are readable aliases for this document, not production identity
keys. The report examples are deliberately short to make their support inspectable.

## 1. One ecosystem, distinct research subjects

```text
Chains
  Northstar
Coins
  Northstar Coin (NSC)
Protocols
  Harbor Lending
Tokens
  Harbor Governance (HBR)
```

Relationships: NSC is native to Northstar; Harbor Lending is deployed on Northstar;
HBR governs Harbor Lending. These are separate sourced relationships, not folder
inheritance. A related bridge is visible within Northstar's related systems; it
does not silently become part of base-chain security or another research job.

Opening HBR shows **Harbor Governance (HBR)** as the title, a token research
workspace, and a link to Harbor Lending. The protocol is not listed under Tokens.
Opening the protocol can show **Related assets: Harbor Governance (HBR)**.

If an unrelated issuer creates **Harbor Rewards (HBR)**, it gets a separate entity
ID and page. Neither asset's name, source, market data, or verification status
overwrites the other. A second project referring to Harbor Governance reuses its
entity ID while retaining that project's evidence and scope.

## 2. Original evidence for the examples

These are complete mini-passages, equivalent to saved blocks. Each is captured
at `2026-09-06T09:00:00Z`; no source publication/effective date is known except
where explicitly stated. Capture time does not prove that these describe current
deployed behavior. The application assigns content and excerpt hashes on save.

| Alias | Source and locator | Exact saved passage |
|---|---|---|
| S-1 | Northstar technical manual, Consensus, lines 1–2 | Northstar uses proof-of-stake consensus. Validators order transactions and produce blocks. |
| S-2 | Northstar developer manual, Cross-contract calls, lines 1–2 | Cross-contract calls execute through separate receipts. Failure of a later receipt does not revert a successfully executed earlier receipt. |
| S-3 | Northstar ecosystem guide, Gateway Bridge, lines 1–2 | Gateway Bridge transfers are authorized by an external signer committee. Gateway is an optional application and is not required for Northstar consensus. |
| S-4 | Harbor Lending manual, Revenue, lines 1–3 | Borrowers pay interest to lending pools. A reserve factor allocates part of borrower interest to the protocol treasury. The remaining interest is allocated to suppliers. |
| S-5 | Harbor Lending manual, Liquidation, lines 1–2 | A position becomes eligible for liquidation when its collateral ratio falls below the configured threshold. Eligibility depends on prices reported by the configured oracle. |
| S-6 | Harbor Governance token manual, Rights, lines 1–3 | HBR holders can vote on treasury spending proposals. Holding HBR does not grant a contractual entitlement to protocol fees. The treasury may fund token repurchases if a governance proposal authorizes them. |
| S-7 | Harbor Lending manual, Controls, lines 1–2 | Governance can change reserve factors and approved oracle configurations. The manual does not specify a mandatory execution delay for those changes. |

S-1 and S-2 describe the chain. S-3 describes a related application and the exact
limit on propagating its risks. S-4, S-5, and S-7 describe the protocol. S-6 describes
the token's relationship and rights. A token report can consult the protocol's
revenue mechanism without attributing that revenue automatically to token holders.

## 3. Scope the application presents

For the Northstar chain project:

> **Researching:** Northstar's base-chain execution and consensus.
>
> **Related systems:** Gateway Bridge, an optional application with separate
> authorization assumptions.
>
> **Coverage:** Architecture documented. Current validator distribution and
> usage have not been collected.

No classification confirmation is required. **Adjust scope** is available.
The bridge still appears under related-system exposure, and its committee risk
can appear when the report question concerns bridged assets. It cannot become a
statement that the chain's consensus is controlled by that committee.

If S-2 appears inside a developer tutorial, its execution caveat is retained.
If the same page also explains Gateway withdrawals, extraction assigns those
blocks to Gateway. Classification is not one indivisible label for the whole file.

If a document merely says “Gateway powers the ecosystem,” the application cannot
infer consensus dependence. It searches other saved passages and leaves the
relationship unresolved if no actual mechanism is documented.

## 4. Fact and coverage examples

One illustrative fact revision, with hash placeholders to be computed from the
saved bytes during implementation:

```json
{
  "schema_version": 2,
  "fact_id": "F-2",
  "revision": 1,
  "subject_id": "northstar-chain",
  "kind": "documented_claim",
  "predicate": "cross_contract_atomicity",
  "statement": "Failure of a later receipt does not revert a successfully executed earlier receipt.",
  "applicability": {
    "version": null,
    "network": null,
    "environment": null,
    "effective_at": null
  },
  "evidence_refs": [{
    "snapshot_id": "S-2",
    "locator": {"kind": "lines", "start": 1, "end": 2},
    "excerpt_sha256": "COMPUTED_FROM_SAVED_EXCERPT"
  }],
  "support_check": {
    "status": "supported",
    "meaning": "faithful representation of S-2; not independent verification"
  },
  "conflicts_with": []
}
```

The fact is documented behavior with unknown deployed version. It is not an
observed transaction outcome. A later collector result would be a separate
`observed_value` fact with chain, block, request, and observation time.

| Research question | Support in this fixture | What the application should conclude |
|---|---|---|
| Are cross-contract operations atomic? | S-2 | Documented non-atomic behavior; no deployed-runtime test collected |
| Does Gateway's committee control consensus? | S-3 | The source explicitly says Gateway is not required for consensus |
| How does Harbor earn revenue? | S-4 | Documented share of borrower interest |
| How much revenue did Harbor earn last month? | None | Measured revenue missing; do not substitute the fee mechanism |
| Does HBR ownership entitle a holder to fees? | S-6 | The source explicitly denies a contractual entitlement; repurchases are discretionary |
| Is HBR undervalued? | No valuation/liquidity/supply observations | Insufficient evidence for valuation; token utility does not answer the question |
| Can governance execute immediately? | S-7 describes no specified delay | Delay unknown; absence of a documented delay does not prove immediate execution |

## 5. Example chain report

**Northstar: execution and dependency assessment**
Evidence captured 6 September 2026; deployed version unconfirmed.

Northstar's documented architecture separates base-chain consensus from
application-level execution risks. Validators produce blocks under proof of
stake, while cross-contract work executes through separate receipts. Application
design therefore needs to account for partial completion: a later failure does
not undo an earlier successful receipt. [S-1, S-2]

Gateway introduces an additional authorization assumption for users of its bridge.
Its external signer committee is described as separate from consensus, so the
committee should be assessed as a bridge exposure rather than attributed to
Northstar's block-production model. [S-3]

The documentation supports a clear distinction between consensus, asynchronous
application behavior, and bridge authorization. It does not establish how
decentralized or operationally reliable the deployed chain is. Validator
distribution and operational evidence would be needed to extend this assessment
into those questions.

**Analyst Notes, separate from the report:** No observed validator distribution,
incident history, or runtime test is present in this fixture. The last paragraph's
evidence-limit statement comes from the bounded source inventory, not a claim that
such evidence does not exist publicly. Check deployment applicability before
making current-state assertions. All technical assertions resolve to S-1–S-3.

**Expected review:** Partial for a broad chain assessment; suitable for the narrower
documented-architecture question. No unsupported “secure” or “decentralized” verdict.

## 6. Example protocol report

**Harbor Lending: revenue mechanism and control risks**
Evidence captured 6 September 2026; current parameters not measured.

Harbor's documented revenue mechanism takes a reserve share of borrower interest
for the treasury while allocating the remainder to suppliers. This establishes
how revenue is collected, but assessing the amount or persistence of that revenue
would also require evidence of borrowing activity and applicable reserve factors.
[S-4]

The mechanism operates alongside material pricing and governance dependencies.
Liquidation eligibility uses prices from the configured oracle, and governance
can change oracle configurations as well as reserve factors. Those controls can
affect both the conditions for liquidation and the allocation of interest. The
manual leaves the execution delay unspecified, so it does not establish how much
notice users receive before a change takes effect. [S-5, S-7]

Harbor therefore has a documented route from borrower payments to treasury
revenue, with governance controlling important parameters. Its realized economics
remain unmeasured in this evidence set. A stronger assessment would require dated
borrowing and revenue data, applicable deployment settings, and evidence of how
configuration changes are executed.

**Analyst Notes, separate from the report:** S-4 supports the fee allocation;
S-5 and S-7 support the controls and their implications. No conclusion about
profitability, bad debt, market share, or comparative safety is supported. The
missing execution delay is an unresolved parameter, not a zero-delay observation.

**Expected review:** Ready for the stated mechanism-and-controls question;
partial for a full economic review. No invented quantitative section or chart.

## 7. Example token report

**Harbor Governance: rights and potential value accrual**
Evidence captured 6 September 2026; valuation outside the supported scope.

HBR's documented rights are governance rights over treasury spending. The token
manual explicitly separates those rights from a contractual claim on protocol
fees. It allows treasury-funded repurchases following a governance proposal,
which makes repurchases a discretionary decision rather than an automatic
entitlement of token ownership. [S-6]

Harbor Lending directs part of borrower interest to its treasury, but that
protocol revenue should not be treated as direct token-holder income. Whether
it benefits HBR holders through repurchases depends on the governance mechanism
described in the token manual. [S-4, S-6]

The supported assessment is consequently about the nature of HBR's rights:
governance influence and possible discretionary repurchases. It cannot establish
an attractive valuation without market and supply evidence. Evidence of enacted
repurchase decisions and their execution would also be needed to assess realized
value accrual.

**Analyst Notes, separate from the report:** No market price, supply, allocation,
liquidity, or executed repurchase records were supplied. Their absence in this
fixture is not proof they are publicly unavailable. An investment recommendation
is neither requested nor supported. Protocol revenue and holder entitlement are
different predicates on different entities.

**Expected review:** Ready for the rights question; partial as a token review.
For “Is HBR undervalued?”, readiness is insufficient and the application gives a
short explanation with specific needed inputs instead of presenting this text as
a valuation answer.

## 8. Required failure and update scenarios

| Scenario | Expected behavior |
|---|---|
| Second unrelated HBR discovered | Separate asset ID and page; no ticker merge or market-data reuse |
| Same asset referenced by protocol and token projects | One navigation identity; separate project context and sourced relationships |
| Chain documentation lists an application token | It remains a token, not a coin because its parent project is a chain |
| New docs add an issued stablecoin | Discovery runs despite existing HBR; existing manual records survive |
| Existing manual asset conflicts with discovery | Keep manual provenance and record conflicting candidate; no silent replacement |
| Source omits a previously discovered token | Keep identity/history and mark source support changed; do not delete the asset |
| Tutorial includes a withdrawal restriction | Material block is extracted with conditions despite the tutorial label |
| Mixed page covers chain and bridge | Facts get separate subjects; no bridge committee attributed to consensus |
| Docs describe a testnet parameter | Preserve testnet applicability; do not report it as mainnet state |
| Later-version source changes a fee | Keep both versions and effective context; not necessarily a contradiction |
| Two same-version sources disagree on token rights | Preserve both references, mark conflict, qualify the conclusion |
| New source contradicts an unchanged selected fact | Reopen affected topic retrieval and review; do not reuse the old conclusion unchecked |
| AI note invents a token fee entitlement | Original-source review rejects it even if report prose accurately repeats the note |
| Several notes repeat S-6 | One provenance root; repetition does not count as corroboration |
| Snapshot captured today contains old supply data | Preserve the old as-of date; capture time does not renew freshness |
| Two metric sources use incompatible time windows | Keep separate; no summed/averaged value without defined transformation |
| Governance delay is not documented | Show unknown; do not invent a zero-delay security finding |
| Provider fails during support review | Save successful work, surface failed batch, resume without regenerating everything |
| Report check fails twice | Present the specific unresolved issue; no unbounded calls or auto-approval |
| User changes generated Markdown | Preserve edit and show regeneration diff; reconcile changed claims before reuse |
| Source changes after human report approval | Old export stays intact and dated; new draft has new evidence and needs approval |
| Asset migration interrupted | Active index remains valid or recovers from journal; retry preserves stable IDs |
| Old ticker page already overwritten | Recover only what registry/source evidence supports; preserve uncertainty and surviving file |
| Project deleted while another references its asset | Shared asset and surviving evidence remain available |
| Only missing evidence is supplied for the question | Explain insufficiency; no padded report and no claim that the subject failed |

These examples specify behavior for future implementation and evaluation. They
are not test results. Phase 1 does not run a live provider, migrate data, or change
existing report approval states.
