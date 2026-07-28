# DeFi Research Extraction Rules

## Objective

Convert the supplied documentation into a compact, factual reference page for
investment research and later machine analysis.

This is data extraction, not report writing. Preserve decision-relevant facts;
do not reproduce the documentation.

## Source Rules

- Use only the supplied documentation.
- Do not use prior knowledge.
- Do not infer, reconcile, estimate, or fill gaps.
- Preserve documented terminology and material numbers exactly.
- Record conflicting claims separately.
- Use **Not documented** only for a material field requested by the template.
- Use **Unable to determine** when supplied sources are ambiguous or conflict.
- Use **Not applicable** only when the subject clearly does not apply.

## Materiality Filter

Include a fact only when it helps determine at least one of:

- what the protocol does and who uses it
- how value enters, moves through, or leaves the system
- token supply, distribution, incentives, or dilution
- governance, privileged authority, or upgrade control
- user-fund, collateral, liquidation, liquidity, or solvency exposure
- critical infrastructure, oracle, bridge, or protocol dependence
- operational constraints, failure conditions, or documented mitigations
- a meaningful competitive difference or documented limitation

Exclude:

- marketing language and unsupported superlatives
- tutorials, interface instructions, and routine user workflows
- exhaustive feature, asset, integration, or contract lists with no analytical
  significance
- examples that do not define actual protocol behavior
- repeated background explanations
- minor implementation details that do not affect behavior, trust, economics,
  or risk
- generic blockchain or DeFi explanations

## Compression Rules

- One fact per bullet or table row.
- Prefer compact tables for repeated fields.
- Use short declarative phrases; avoid narrative paragraphs.
- Do not restate the same fact in summaries, takeaways, or commentary.
- Combine fields only when doing so does not hide distinct facts.
- Preserve essential qualifications, conditions, units, dates, and scope.
- A page may be short. Do not add filler to populate a section.
- Omit empty optional sections instead of producing long placeholder lists.

## Output Classes

Each page may contain only:

1. **Facts** — directly documented, decision-relevant information.
2. **Documented Risks & Constraints** — risks, limitations, trust requirements,
   or failure conditions explicitly stated or mechanically inherent in the
   documented design. State the supporting mechanism; do not speculate.
3. **Material Unknowns** — missing or conflicting information whose absence
   limits investment analysis.

Do not produce:

- analyst commentary
- recommendations
- conclusions
- ratings or verdicts
- repetitive key takeaways
- verification opportunities
- automation opportunities

Verification is handled in a separate verification-planning workflow.

## Cross-Page Deduplication

- Place a fact in the single most specific page.
- The overview may reference a subject at a high level but must not repeat its
  mechanics.
- Architecture owns component interaction and system flow.
- Governance owns decision authority and governance processes.
- Security owns defensive controls and security-critical trust.
- Risk Assessment owns consolidated material exposure and failure scenarios.
- Tokenomics owns token supply, allocation, emissions, utility, and restrictions.
- Revenue Model owns fees, recipients, and value distribution.
- Liquidity owns liquidity sources, utilization, incentives, and constraints.
- Integrations & Dependencies owns required external systems and assets.
- Competitive Analysis owns documented comparisons and differentiators.

## Output Requirements

- Follow the supplied template headings and field structure.
- Do not output template instructions.
- Do not add introductory or closing prose.
- Do not cite a source unless the template requests source provenance.
- Return Markdown optimized for Obsidian and machine parsing.
