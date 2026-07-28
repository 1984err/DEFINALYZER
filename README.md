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
- Automated LLM prompt execution: awaiting provider integration
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
python main.py status example-protocol
python main.py collect example-protocol
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
    └── Indexes/
```

Open `output/vault/` directly in Obsidian or synchronize that directory.
Generated output is ignored by Git.

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
