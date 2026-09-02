# Prompt Workflow

The prompt set produces compact factual research pages and a separate
verification workflow.

## Research extraction

All reusable prompts are ordinary Markdown files in this visible `prompts/`
folder. They can be copied, opened, or supplied to any AI provider; they are
not hidden inside the application.

For a manual research-page run:

1. Open `prompts/master_prompt.md`.
2. Choose one research template from `prompts/templates/`, such as
   `template_protocol_overview.md` or `template_tokenomics.md`.
3. Give the AI the complete master prompt followed by the complete selected
   template. Do not substitute the registry or verification templates.
4. Attach or paste the collected Markdown files from
   `output/sources/<project>/`. The `_official/` subfolder contains any
   separately registered official sources and should be included when present.
5. Ask the AI to return Markdown only, following both prompt files.
6. Save the answer in the project's Obsidian folder under
   `output/vault/Protocols/<project>/`, `Chains/<project>/`, or
   `Tokens/<project>/`, as applicable.

Run one topic template at a time. The returned filenames follow the template:
`Protocol-Overview.md`, `Architecture.md`, `Tokenomics.md`, `Governance.md`,
`Security.md`, `Risk-Assessment.md`, `Revenue-Model.md`, `Liquidity.md`,
`Integrations-Dependencies.md`, and `Competitive-Analysis.md`.

Research pages contain only decision-relevant facts, documented risks or
constraints, and material unknowns.

The topic templates deliberately omit:

- analyst commentary
- repeated key takeaways
- verification sections
- automation sections

## Registry extraction

Use `templates/protocol_registry_extraction.md` to create the normalized
address and technical-reference inventory. Supply it after the research pages
exist, together with those research pages and relevant official source
Markdown. It is not a substitute for a research topic template.

## Verification planning

After the research pages and registry are complete, provide them to
`templates/template_verification_page.md`. It creates:

- one categorized verification page per protocol, chain, or token
- separate claim type, evidence availability, recommended method, route, and status
- an analyst route, short procedure, and likely source for every check
- stable Obsidian block links for material claims
- a link-insertion map
- the strict machine-readable block accepted by the blockchain collector

The verification planner is an analyst checklist with an optional automated
evidence layer. `Manual` describes a route, not a result. A private, legal, or
undocumented claim is classified separately and is never treated as false just
because public evidence is unavailable. The planner selects evidence requests
but does not evaluate claims. Evidence evaluation and research-link insertion
are later workflow steps.

When a public on-chain history or aggregate check is marked `Dune candidate`,
the application may offer its optional copy/paste query dialogue. This is not
automatic Dune execution and does not make a verification decision.
