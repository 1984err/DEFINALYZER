# DEFINALYZER

DEFINALYZER creates concise, fact-first DeFi research notes and can collect raw
EVM evidence for selected material claims. Research remains useful when
verification is skipped or unavailable.

## Current status

- Unified project and output interface: available
- Documentation crawler: available
- Human and agent blockchain collector: available
- Structured verification-request importer: available
- Streamlined extraction and verification prompts: available
- Automated Hermes prompt execution: available
- Resumable full-document chunk extraction: available
- Categorized, resumable verification planning: available
- Deterministic keyless CoinGecko supply enrichment: available
- Section-scoped, read-only AI explanations: available
- Human-approved evidence evaluation and Obsidian link insertion: available

## Install

Python 3.11 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
crawl4ai-setup
```

Copy `.env.example` to `.env` and add only the RPC endpoints you use.

`crawl4ai-setup` installs the browser runtime used by the documentation
crawler. The blockchain collector and project manager do not require it when
used independently.

Hermes is installed and authenticated separately. DEFINALYZER does not store
Hermes credentials. Configure and test the connection once:

```powershell
python main.py provider configure
python main.py provider test
```

## Guided use

Run the application without a command:

```powershell
python main.py
```

The menu supports project creation, complete-workflow status, separate
workflow stages, crawling, blockchain collection, manual token records,
vault indexes, and project status.

**Run complete workflow** now executes the usable research pipeline:
documentation collection, all missing research pages, registry generation,
deterministic CoinGecko supply enrichment, source-coverage reporting, and—when
the project was created with verification requested—the categorized
verification checklist. Existing sources, pages, and resumable extraction
ledgers are reused by default.

## Power-user commands

```powershell
python main.py init "Example Protocol" --docs-url https://docs.example.org
python main.py all example-protocol
python main.py crawl example-protocol
python main.py source add example-protocol --category tokenomics --url https://example.org/token
python main.py source crawl example-protocol --category tokenomics
python main.py source list example-protocol
python main.py extract example-protocol --template protocol-overview
python main.py registry example-protocol
python main.py market-data example-protocol
python main.py ask example-protocol --page Governance --heading "Material Permissions" --question "What can this role do?"
python main.py verification-plan example-protocol
python main.py evaluate example-protocol
python main.py review example-protocol
python main.py status example-protocol
python main.py collect example-protocol
```

Rerun `python main.py all <project>` after an interruption to resume from
existing outputs. Use `--refresh` only when you intentionally want to recrawl
the primary documentation and replace every generated research page:

```powershell
python main.py all example-protocol --refresh
```

Verification remains optional. Projects created with verification status
`not_requested` or `unsupported` finish with analysis-ready research and an
explicit “verification skipped” message. Projects configured as `pending`
continue through verification planning; manual-review checks are a successful
workflow result, not a pipeline failure.

## Using DEFINALYZER without AI

The source collector is independently useful and makes no AI calls. Create a
project and choose **Crawl documentation**, or run:

```powershell
python main.py init "Example Protocol" --docs-url https://docs.example.org
python main.py crawl example-protocol
```

The cleaned local Markdown remains under
`output/sources/example-protocol/`. Copy that folder, open it in an editor, or
send the files to any model or program you choose. No special export step or
DEFINALYZER prompt is required. Concise research-page generation does require
an AI provider because it selects and restructures decision-relevant facts.
For a manual AI extraction, the reusable prompts are plainly available under
`prompts/`: combine `prompts/master_prompt.md` with one file from
`prompts/templates/`, then provide the collected source Markdown. See
`prompts/README.md` for the exact sequence, output filenames, and save
locations.

These functions also work without AI:

- project creation, status, and Obsidian navigation indexes
- website or public-GitHub Markdown collection
- official-source registration and collection
- manual native/protocol-issued token entry
- exact-address CoinGecko supply and FDV refresh
- raw blockchain RPC evidence collection for an existing request
- human maintenance of an existing verification checklist

The verification page has value without AI as a categorized analyst to-do
list: it preserves the material claim, why it matters, what evidence is
needed, how to check it, and where to look. Creating that checklist from
research notes currently uses AI; following it and adding analyst notes does
not. Evidence collection records raw facts and does not itself confirm or deny
claims. Research extraction, new verification-plan generation, evidence
interpretation proposals, and scoped Q&A require the configured AI provider.

Extraction mode defaults to `auto`: a small source set uses one provider call;
a larger set is split into resumable fact-ledger batches and consolidated.
Power users may force a mode with `--mode single` or `--mode chunked`.

For large projects, the first extraction creates a categorized shared research
corpus under `output/projects/<project>/extraction/shared-research/`. Later
research templates reuse that corpus instead of rescanning every source page.
Fenced implementation examples are excluded from AI input but remain intact in
the locally saved source Markdown.

Documentation discovery is layered. It first uses the conventional `/docs/`
filter and, when that finds nothing, retries across the configured
documentation domain. This supports both path-based documentation and
dedicated documentation domains without protocol-specific crawler rules.
Obvious branding, privacy, legal-boilerplate, and media-index pages remain
saved locally but are excluded from AI research input.

A documentation root is not assumed to cover every decision-relevant topic.
Projects track official sources separately for technical documentation,
tokenomics, fees/revenue, and governance/security. Missing categories are
shown on every generated research page and mean **not assessed**, not
nonexistent. Add and crawl exact official pages through **Manage official
sources** in the menu or the `source` commands above. Collected sources join
the normal extraction corpus; the output format stays uniform across
protocols.

Public GitHub documentation repositories use a separate importer; the website
crawler is not modified or emulated. Set the project documentation URL to the
repository root, such as `https://github.com/owner/public-docs`, and run the
normal **Crawl documentation** action. The importer downloads Markdown only,
pins the import to an immutable commit, preserves repository paths, and records
file URLs and hashes in `github-import.json`. Code, IDLs, binaries, issues, and
pull requests are not imported. Existing imports are reused unless refresh is
requested; refresh may replace or remove only files owned by the prior import
manifest. A branch, tag, or commit may be selected with `--ref`:

```powershell
python main.py crawl example-protocol --ref main
```

If a provider call fails, rerunning the same extraction reuses completed
ledgers. A changed source crawl or changed prompt intentionally invalidates that
state rather than mixing different source versions. Estimate the initial work
without calling AI:

```powershell
python main.py extract example-protocol --template protocol-overview --plan
```

Only one complete workflow may run for a project at a time. A second launch is
rejected instead of writing concurrently or duplicating provider calls. A
project whose crawl is `partial`, `blocked`, or still incomplete is recrawled;
the complete workflow will not treat a few surviving source files as a valid
corpus for AI extraction.

The existing tools remain independently available:

```powershell
python -m crawler.crawler
python -m crawler.github_importer "Example Protocol" https://github.com/owner/public-docs --output output/sources/example-protocol
python -m blockchain_collector.menu
python -m blockchain_collector.capabilities
```

## Output and Obsidian

The application creates:

```text
output/
├── projects/<project>/
│   ├── project.json
│   ├── jobs/
│   └── evidence/
├── sources/<project>/
├── registries/<project>/
└── vault/
    ├── Protocols/
    ├── Chains/
    ├── Tokens/
    ├── Verification/
    ├── Analyst Reviews/
    └── Indexes/
```

Open `output/vault/` directly in Obsidian or synchronize that directory.
Generated output is ignored by Git.

`Indexes/Home.md`, `Research.md`, `Tokens.md`, and `Verification.md` are
generated vault-wide navigation pages. Choose **Refresh Obsidian vault
indexes** after adding or changing projects; this uses no AI. Each verification page is stored at
`Verification/<project>/Index.md`, leaving its project folder available for
related analyst evidence. Saved **Analyst Reviews** are optional,
non-canonical scratch notes; no extraction, registry, verification, or index
operation depends on them, so deleting one does not affect future entries.

Registry token pages are intentionally narrow: they cover only a chain or
protocol's native/governance token and protocol-issued tokens with material
economics (for example, AAVE and GHO). Reserve assets, collateral, wrappers,
receipt tokens, and external dependencies do not receive token pages. Research
pages link the first meaningful reference to each qualifying token; repeated
mentions remain plain text to keep the notes readable.

Use **Add or update a token manually** when official documentation identifies
a qualifying token but automated discovery misses it. The menu records its
identity, relationship, address, mechanics, and official source without AI,
then regenerates the token page and links. Current supply fields cannot be
entered there: they remain exclusively owned by deterministic CoinGecko
enrichment. Re-entering the same symbol updates that record instead of
creating a duplicate.

Current supply enrichment runs automatically after registry generation and is
also independently refreshable through **Refresh current token supply data**
or `python main.py market-data <project>`. It does not use AI. CoinGecko
matching uses an exact contract or mint address, discovering the platform when
the official network field is absent. Results are cached for one day and
display only FDV, circulating supply, total supply, maximum supply, source, and
timestamp in a clearly labeled third-party section. Price, market cap, and
short-term volume are intentionally omitted. Missing or ambiguous matches and
network failures remain visible without blocking research or verification.
Use `--refresh` to ignore the cache.

The research and token-index roles are intentionally separate. `Tokenomics.md`
records protocol-linked mechanics such as utility, value rights, issuance
controls, allocation, vesting and unlocks, emissions, burns, incentives, and
restrictions. It does not contain current circulating, total, or maximum
supply statistics. The token index is the concise identity-and-statistics page;
its current supply fields and FDV come only from deterministic CoinGecko
enrichment, never from AI.

For help interpreting a research entry, choose **Explain a research-page
entry** from the main menu. Select one project page and one Markdown heading,
then ask a focused question. Hermes receives only that complete section, its
page identity, and the question. It is instructed to distinguish facts,
inference, and unknown information and to avoid outside knowledge or investment
recommendations. Oversized sections are rejected rather than silently
truncated. The answer is read-only unless the user explicitly saves it under
`output/vault/Analyst Reviews/<project>/`; saved answers are labeled
non-canonical AI explanations and link back to the selected source section.

Extraction detail is decision-aware rather than capped by row count. Core
mechanisms retain their material flows, controls, dependencies, and failure
conditions. Supporting systems are compressed to their economics, authority,
restrictions, and material uncertainty unless the documentation shows that
they are central to adoption, liquidity, revenue, distribution, solvency, or
continued operation.

Core-contract discovery is layered but conservative. Exact addresses from
official documentation are retained, and official machine-readable registries
may enrich them. Only non-conflicting targets with a resolved supported chain
are eligible for automatic collector requests. Unresolved or conflicting
records remain visible for manual review instead of being guessed.

Verification planning inserts compact Obsidian links at exact mapped research
sections. The verification page is an analyst checklist: each material item
states whether its route is automated, assisted, or manual, how to perform the
check, and the likely official source. Manual review is an expected work-queue
item rather than a failed automation result. For a manual evidence check,
choose **Collect blockchain evidence**
from the main menu and then **Select a project registry target**. The collector
fills the documented address, chain, role, and provenance before asking which
supported read to run.

Evidence evaluation is a separate human-approved stage. `evaluate` creates
immutable Hermes proposals without changing claim status. `review` displays
the claim, proposed status, reason, scope, and evidence path in the terminal.
Only an explicit approval or inconclusive override updates the verification
page; rejection and unattended automation leave it unchanged.

Verification status is explicit and does not affect whether research can be
used:

- `not_requested`
- `unsupported`
- `pending`
- `evidence_collected`
- `manual_review`
- `supported`
- `contradicted`
- `inconclusive`

## Prompt workflow

See `prompts/README.md` for fact extraction, normalized registry generation,
categorized verification pages, and scanner request generation.
