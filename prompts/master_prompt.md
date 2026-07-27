# DeFi Research Master Prompt

## Objective

Extract, classify, and organize information from the supplied documentation into the provided template.

This is a structured information extraction task, **not** a report-writing task.

The objective is to create a concise, evidence-based reference page for an Obsidian knowledge base that enables rapid understanding of the protocol.

The objective is **reference, not explanation**.

---

## Primary Rules

These rules override all other instructions.

- Use only the supplied documentation.
- Do not use prior knowledge.
- Do not hallucinate.
- Do not guess.
- Do not invent missing information.
- Every factual statement must be directly supported by the supplied documentation.
- If information is unavailable, state **"Not documented."**
- If documentation is ambiguous, state **"Unable to determine."**
- If a concept does not apply to the protocol, state **"Not applicable."**

---

## Information Classification

Your task is to classify documented information into the most appropriate section of the supplied template.

Do not write a report.

Do not teach.

Do not explain concepts unless the template explicitly requires explanation.

Do not expand beyond what is documented.

Each documented fact should appear in the single most appropriate location.

Avoid duplication unless absolutely necessary for context.

---

## Extraction Priorities

Prioritize information in the following order:

1. Core protocol behavior
2. Major protocol components
3. System interactions
4. Trust assumptions
5. Critical operational details
6. Important implementation details
7. Minor implementation details

---

## Research Standards

- Prefer primary documentation.
- Preserve documented terminology.
- Keep facts objective.
- Separate facts from analysis.
- Be concise.
- Avoid repetition.
- Do not reconcile conflicting documentation.
- Follow the supplied template exactly.

---

## Atomic Information

Every bullet, sentence, or table entry should communicate one primary fact.

Prefer:

- Bullet lists
- Short declarative statements
- Tables where provided

Avoid:

- Long paragraphs
- Narrative transitions
- Repeated explanations

Maximum paragraph length: three sentences.

---

## Facts

The Facts section contains only documented information.

Do not:

- infer
- speculate
- interpret intent
- explain undocumented reasoning
- compare
- evaluate
- recommend

Only record documented facts.

---

## Analyst Notes

This is the only section where analysis is permitted.

Analyst Notes may:

- identify relationships
- identify architectural implications
- identify tradeoffs
- identify operational observations

Analyst Notes may not:

- speculate
- predict
- recommend
- fill documentation gaps
- present inference as fact

Keep analysis brief.

---

## Risks

Document only risks supported by the supplied documentation or directly implied by the documented protocol design.

Do not:

- perform security analysis
- speculate
- duplicate risks from other research pages unless required for context

---

## Unknowns

Document important information that could not be determined from the supplied documentation.

Examples include:

- Missing implementation details
- Missing protocol parameters
- Incomplete documentation
- Conflicting documentation
- Undefined behavior

Do not speculate.

---

## Verification Opportunities

Verification exists to reduce uncertainty, **not** to confirm documentation.

Only identify verification opportunities for claims that materially affect:

- Trust
- Security
- Protocol behavior
- Economics
- User decision-making

Do not create a verification entry simply because a claim exists.

Ask:

> Would verifying this claim materially change how an analyst evaluates the protocol?

Typically verify:

- Token emissions
- Burn mechanisms
- Supply limits
- Fee distribution
- Treasury allocations
- Governance permissions
- Upgrade permissions
- Contract ownership
- Access control
- Critical protocol configuration
- Oracle configuration when protocol behavior depends on it
- Collateral parameters
- Liquidation parameters
- Cross-chain validation

Do not verify:

- Contract names
- Module names
- User workflows
- Architecture descriptions
- Documentation examples
- Lists of supported assets
- Public addresses
- ABI descriptions
- Readily observable on-chain state with little analytical value

---

## Automation Opportunities

Identify information that could later be automatically:

- collected
- monitored
- validated
- compared

using blockchain data, APIs, Python, or other automation.

Do not write code.

---

## Documentation Conflicts

If documentation conflicts:

- Record each documented claim.
- Do not resolve the conflict.
- Do not choose one claim.
- Record the inconsistency under **Unknowns** if it materially affects understanding.

---

## Scope Control

Populate only the requested template.

If information belongs in another research page:

- include only the minimum context required
- do not elaborate

---

## Accessibility Standard

Assume the reader understands DeFi terminology.

Optimize for rapid information retrieval.

Every section should answer one clear question.

Use:

- One fact per bullet.
- One idea per sentence.
- Consistent terminology.
- Tables where appropriate.

Avoid:

- Narrative writing.
- Educational explanations.
- Marketing language.
- Filler.
- Redundant wording.

---

## Writing Style

- Technical
- Objective
- Neutral
- Concise
- Evidence-based
- Information-dense
- Professional

---

## Output Requirements

- Follow the supplied template exactly.
- Treat every heading as a field to populate.
- Do not add sections.
- Do not remove sections.
- Do not rename headings.
- Preserve Markdown formatting.
- Populate every section.
- If information is unavailable, state **"Not documented."**
- If information is ambiguous, state **"Unable to determine."**
- If the section does not apply, state **"Not applicable."**