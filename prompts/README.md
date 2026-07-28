# Prompt Workflow

The prompt set produces compact factual research pages and a separate
verification workflow.

## Research extraction

Combine `master_prompt.md` with one topic template from `templates/`. Research
pages contain only decision-relevant facts, documented risks or constraints,
and material unknowns.

The topic templates deliberately omit:

- analyst commentary
- repeated key takeaways
- verification sections
- automation sections

## Registry extraction

Use `templates/protocol_registry_extraction.md` to create the normalized
address and technical-reference inventory.

## Verification planning

After the research pages and registry are complete, provide them to
`templates/template_verification_page.md`. It creates:

- one categorized verification page per protocol, chain, or token
- stable Obsidian block links for material claims
- a link-insertion map
- the strict machine-readable block accepted by the blockchain collector

The verification planner selects evidence requests but does not evaluate
claims. Evidence evaluation and research-link insertion are later workflow
steps.
