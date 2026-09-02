# DEFINALYZER

[MIT licensed](LICENSE)

DEFINALYZER creates concise, fact-first DeFi research notes and can collect raw
EVM evidence for selected material claims. Research remains useful when
verification is skipped or unavailable.

Start here:

- [Windows setup and troubleshooting](docs/WINDOWS_SETUP.md)
- [Beta scope and limitations](docs/LIMITATIONS.md)
- [Security and data handling](SECURITY.md)
- [Application architecture](docs/APPLICATION_ARCHITECTURE.md)
- [Local dashboard](docs/DASHBOARD.md)
- [Manual prompt workflow](prompts/README.md)
- [Blockchain collector reference](blockchain_collector/USAGE.md)
- [Compact fictional research output](examples/research_output/README.md)

## Five-minute Quick Start

Open PowerShell in the DEFINALYZER folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
crawl4ai-setup
python main.py
```

`crawl4ai-setup` installs browser runtimes and may download several hundred
megabytes on the first installation. This is normal. It is needed for website
crawling, but not for the standalone blockchain collector or project manager.

In the menu:

1. Choose **Set up a new project (setup only)** and enter the official
   documentation URL.
2. Accept the offer to continue, or choose **Analyze a project (complete
   research workflow)** afterward.
3. Open the displayed `output/vault/` directory as an Obsidian vault.

For the local dashboard instead of the terminal menu, run:

```powershell
python main.py dashboard
```

On Windows, you can also double-click `Start DEFINALYZER Dashboard.bat` in the
project folder. It uses the project's virtual environment and opens the local
dashboard without requiring a terminal command.

To permanently remove an incorrect or unwanted run, choose **Delete a project
and its generated data**. Type the exact project name to confirm. DEFINALYZER
removes that project's sources, state, registry, research, verification, and
analyst-review folders, removes token pages that no remaining project uses,
and refreshes the vault indexes.

Hermes is optional for crawling but required for automated research-page
generation. Install and authenticate Hermes separately, then verify it with:

```powershell
python main.py provider test
```

RPC endpoints are optional unless you use blockchain evidence collection.
Copy `.env.example` to `.env` and add only the endpoints you intend to use.

The research workflow supports protocol, chain, and token projects. Automated
blockchain evidence is currently limited to Ethereum, Arbitrum One, and Base;
other networks still receive research and explicit manual verification tasks.

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
- Local project dashboard and Markdown reader: available

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
Hermes credentials. Automated provider calls use an explicit empty toolset
allowlist, so crawled documentation is processed as text and cannot ask Hermes
to run terminal, browser, file, or other agent tools. Configure and test the
connection once:

```powershell
python main.py provider configure
python main.py provider test
```

Windows Command Prompt uses `.venv\Scripts\activate.bat`; `source` is not a
Windows activation command. Activation can also be skipped by calling
`.\.venv\Scripts\python.exe` directly. See the
[Windows guide](docs/WINDOWS_SETUP.md) for recovery instructions.

## Guided use

Run the application without a command:

```powershell
python main.py
```

For a new project, choose **Set up a new project (setup only)**. The menu then
offers to continue directly into **Analyze a project (complete research
workflow)**. After research and verification planning, it can optionally
continue through scanner-ready evidence collection, evidence-assessment
proposals. Human approval is deliberately separate under **Review and approve
assessments**. Every boundary requires confirmation; stopping returns the
remaining work to its numbered menu option. The collector warning
lists its supported chains dynamically (currently Ethereum, Arbitrum, and
Base). Unsupported networks and off-chain claims remain categorized manual
tasks rather than failed or disproven claims.

The menu supports project creation, project-analysis status, separate
workflow stages, crawling, blockchain collection, manual token records,
vault indexes, project deletion, and project status.

**Analyze a project** executes the usable research pipeline:
documentation collection, all missing research pages, registry generation,
deterministic CoinGecko supply enrichment, source-coverage reporting, and--when
the project was created with verification requested--the categorized
verification checklist. Existing sources, pages, and resumable extraction
ledgers are reused by default.

## Power-user commands

```powershell
python main.py init "Example Protocol" --docs-url https://docs.example.org
python main.py analyze example-protocol
python main.py crawl example-protocol
python main.py source add example-protocol --category tokenomics --url https://example.org/token
python main.py source crawl example-protocol --category tokenomics
python main.py source list example-protocol
python main.py extract example-protocol --template protocol-overview
python main.py registry example-protocol
python main.py market-data example-protocol
python main.py ask example-protocol --question "How does the protocol make money?"
python main.py ask example-protocol --question "How do liquidations work?" --deep
python main.py ask example-protocol --page Governance --heading "Material Permissions" --question "What can this role do?"
python main.py verification-plan example-protocol
python main.py dune example-protocol VR-FEE-001
python main.py dune example-protocol VR-FEE-001 --feedback-type error --feedback "Paste the exact Dune error"
python main.py evaluate example-protocol
python main.py review example-protocol
python main.py status example-protocol
python main.py collect example-protocol --planned
python main.py collect example-protocol  # standalone advanced collector
python main.py dashboard
```

Rerun `python main.py analyze <project>` after an interruption to resume from
existing outputs. Use `--refresh` only when you intentionally want to recrawl
the primary documentation and replace every generated research page:

```powershell
python main.py analyze example-protocol --refresh
```

The older `all` command remains an alias for `analyze`.

Verification remains optional. Projects created with verification status
`not_requested` or `unsupported` finish with analysis-ready research and an
explicit "verification skipped" message. Projects configured as `pending`
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

The terminal and local dashboard share the typed application boundary in
`definalyzer/application.py`. It exposes JSON-safe project snapshots, truthful
action availability, project lifecycle operations, Q&A, Dune dialogue, market
data, and local paths without duplicating research logic. See the
[application architecture](docs/APPLICATION_ARCHITECTURE.md).

## Advanced behavior

Extraction mode defaults to `auto`: a small source set uses one provider call;
a larger set is split into resumable fact-ledger batches and consolidated.
Power users may force a mode with `--mode single` or `--mode chunked`.

For large projects, the first extraction creates a categorized shared research
corpus under `output/projects/<project>/extraction/shared-research/`. Later
research templates reuse that corpus instead of rescanning every source page.
Fenced implementation examples are excluded from AI input but remain intact in
the locally saved source Markdown. Endpoint-by-endpoint catalogs such as FIX
message references, RPC method catalogs, and subscription-channel references
are also retained locally but excluded from routine investment extraction.
Conceptual architecture, risk, security, integration, and changelog pages stay
in the AI corpus. Each extraction reports selected and excluded source volume,
provider calls, reused calls, and approximate provider-input characters; the
same history is saved under
`output/projects/<project>/extraction/usage.json`.

When no protocol-native token or tokenomics source is identified, the
Tokenomics page is a compact coverage notice generated without an AI call. It
does not claim that no token exists and directs the analyst to add an official
source if token economics are material.

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

Only one project analysis may run for a project at a time. A second launch is
rejected instead of writing concurrently or duplicating provider calls. A
project whose crawl is `partial`, `blocked`, or still incomplete is recrawled;
project analysis will not treat a few surviving source files as a valid
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
|-- projects/<project>/
|   |-- project.json
|   |-- jobs/
|   `-- evidence/
|-- sources/<project>/
|-- registries/<project>/
`-- vault/
    |-- Protocols/
    |-- Chains/
    |-- Tokens/
    |-- Verification/
    |-- Analyst Reviews/
    `-- Indexes/
```

Open `output/vault/` directly in Obsidian or synchronize that directory.
Generated output is ignored by Git.

`Indexes/Home.md`, `Research.md`, `Tokens.md`, and `Verification.md` are
generated vault-wide navigation pages. Choose **Refresh Obsidian vault
indexes** after adding or changing projects; this uses no AI. The Research
index reports effective readiness and the next valid action rather than merely
repeating saved stage labels. Token parent links follow the project's actual
Protocol, Chain, or Token folder. Each verification page is stored at
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

For help interpreting the research, choose **Ask a question about project
research** from the main menu. By default, DEFINALYZER searches every generated
research page, the verification checklist, and related native/protocol token
pages locally, then sends only the strongest matching passages to Hermes. Deep
search also searches all collected source Markdown without sending the entire
documentation corpus. Page-and-heading restriction remains optional for a
question that intentionally concerns one entry. Hermes distinguishes documented
facts, inference, and unknown information and cites the retrieved passages; it
does not use outside knowledge or provide investment recommendations. The
answer is read-only unless the user explicitly saves it under
`output/vault/Analyst Reviews/<project>/`; saved answers are labeled
non-canonical AI explanations and link to every consulted vault source.

Retrieval itself is deterministic and uses no AI. Both normal and deep search
package at most roughly 20,000 characters of source context so large projects do
not turn every question into a full-document model call. Deep mode costs more
local search time, not necessarily more model tokens, and is useful when the
streamlined research notes may have omitted the detail behind a question.

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

Each generated registry JSON also records the selected local source path, its
official source URL when present, and a SHA-256 hash of the exact saved input.
Address and token source cells link back to the official web or commit-pinned
GitHub page. These provenance records are deterministic metadata and do not
make the concise research pages longer.

Verification planning inserts compact Obsidian links at exact mapped research
sections. The verification page is an analyst checklist: each material item
states whether its route is automated, assisted, or manual, how to perform the
check, and the likely official source. Claim type, evidence availability,
recommended method, work route, and result status are stored separately.
Manual review is an expected work route rather than a failed automation result
or a verdict about the claim. For a manual evidence check,
choose **Collect blockchain evidence**
from the main menu and then **Select a project registry target**. The collector
fills the documented address, chain, role, and provenance before asking which
supported read to run.

Checks conservatively classified as public `Dune candidate` entries show an
optional Dune-query action. DEFINALYZER asks Hermes for one read-only query and
saves the draft under the matching verification folder. The user runs it in
Dune and may paste an exact error, additional context, or a result summary/link
back into the dialogue for a revised query. Every version is retained. No Dune
API key is used, no query is executed by DEFINALYZER, and neither a query nor a
pasted result changes verification status automatically.

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

## Release checks

Run these from the activated project environment before publishing a change:

```powershell
python -m pip check
python -m unittest discover -s tests
python -m blockchain_collector.capabilities
python main.py --help
```

For dashboard changes, also run the optional Node.js UI-state tests:

```text
node --test tests/dashboard_reader.test.cjs
```

No RPC or AI call is made by those checks. A beta release also requires a live
Hermes provider test and, when scanner behavior changed, a read-only RPC smoke
test using a disposable evidence output path.

## License

DEFINALYZER is available under the [MIT License](LICENSE).
