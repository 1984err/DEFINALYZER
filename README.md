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
- Optional keyless CoinGecko token snapshots: available
- Section-scoped, read-only AI explanations: available
- Automated evidence evaluation and Obsidian link insertion: deferred

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
workflow stages, crawling, blockchain collection, and project status.

## Power-user commands

```powershell
python main.py init "Example Protocol" --docs-url https://docs.example.org
python main.py crawl example-protocol
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

If a provider call fails, rerunning the same extraction reuses completed
ledgers. A changed source crawl or changed prompt intentionally invalidates that
state rather than mixing different source versions. Estimate the initial work
without calling AI:

```powershell
python main.py extract example-protocol --template protocol-overview --plan
```

The existing tools remain independently available:

```powershell
python -m crawler.crawler
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

Registry token pages are intentionally narrow: they cover only a chain or
protocol's native/governance token and protocol-issued tokens with material
economics (for example, AAVE and GHO). Reserve assets, collateral, wrappers,
receipt tokens, and external dependencies do not receive token pages. Research
pages link the first meaningful reference to each qualifying token; repeated
mentions remain plain text to keep the notes readable.

Market snapshots are optional and independent of registry generation. Run
**Refresh token market data** from the main menu, or use `python main.py
market-data <project>`. CoinGecko matching uses a registered network and
contract address rather than a token name or symbol. Results are cached for one
hour and display price, market cap, FDV, volume, supply, source, and timestamps
in a clearly labeled third-party section. Missing listings, unsupported native
assets without contract addresses, and network failures remain visible without
blocking research or verification. Use `--refresh` to ignore a recent cache.

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
