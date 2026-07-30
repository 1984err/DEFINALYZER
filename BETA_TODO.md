# DEFINALYZER Restart-to-Beta Checklist

Use this checklist after restarting the computer. Complete the phases in
order. Do not begin another protocol run until the local environment passes
Phase 1.

## Phase 1 — Post-Restart Health Check

- [ ] Open PowerShell in the DEFINALYZER project directory.
- [ ] Confirm the system Python installation:

  ```powershell
  python --version
  ```

- [ ] Test the existing virtual-environment executable:

  ```powershell
  .\.venv\Scripts\python.exe --version
  ```

- [ ] If Windows still returns `Access is denied`, preserve `.env`, remove
  only the disposable `.venv` directory, and recreate it:

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  crawl4ai-setup
  ```

- [ ] Confirm the application starts:

  ```powershell
  .\.venv\Scripts\python.exe main.py --help
  ```

- [ ] Confirm Hermes is configured and callable through DEFINALYZER:

  ```powershell
  .\.venv\Scripts\python.exe main.py provider test
  ```

- [ ] Run the automated test suite:

  ```powershell
  .\.venv\Scripts\python.exe -m unittest discover -s tests
  ```

- [ ] Confirm all existing project status records remain readable:

  ```powershell
  .\.venv\Scripts\python.exe main.py status
  ```

## Phase 2 — Existing-Project Regression Check

- [ ] Confirm the Aave V3, USD.ai, Pump, and Morpho generated notes still open
  correctly in `output/vault/`.
- [ ] Check Obsidian links containing aliases inside tables.
- [ ] Confirm token pages keep current supply statistics separate from
  protocol tokenomics.
- [ ] Confirm a registry rerun does not reintroduce large deployment catalogs
  or example addresses.
- [ ] Confirm source coverage is correctly categorized when one official
  documentation root contains multiple research categories.
- [ ] Confirm rerunning an existing project without `--refresh` reuses saved
  sources, research pages, and extraction ledgers.
- [ ] Confirm no existing generated note is silently overwritten by a
  read-only or status command.

## Phase 3 — Derive Compatibility Test

- [ ] Create Derive as a new project using its primary official documentation
  URL.
- [ ] Run a crawl plan or initial crawl and inspect the discovered source
  scope before invoking Hermes.
- [ ] Confirm API catalogs, tutorials, examples, and unrelated pages do not
  dominate the research corpus.
- [ ] Run the complete workflow without manual intervention:

  ```powershell
  .\.venv\Scripts\python.exe main.py all derive
  ```

- [ ] Review:
  - [ ] Protocol overview accuracy and brevity
  - [ ] Architecture and product-model handling
  - [ ] Networks and dependencies
  - [ ] Native or protocol-issued token identification
  - [ ] CoinGecko supply enrichment
  - [ ] Registry relevance
  - [ ] Source-coverage accuracy
  - [ ] Verification checklist quality
  - [ ] Automated versus manual verification routing
- [ ] Fix only general extraction or workflow defects. Do not add
  Derive-specific logic unless it is an optional official-source adapter.
- [ ] Rerun only affected stages and then run the full automated test suite.

## Phase 4 — Non-EVM Extraction Test

- [ ] Select one documented Solana protocol.
- [ ] Run documentation extraction and token-page generation.
- [ ] Confirm the tool clearly distinguishes:
  - [ ] Research extraction support
  - [ ] Token-market-data support
  - [ ] Unsupported Solana blockchain evidence collection
- [ ] Ensure unsupported verification tasks become explicit analyst
  instructions rather than failures or invented confirmations.
- [ ] Do not expand the blockchain scanner to Solana unless separately
  approved as beta scope.

## Phase 5 — Clean Installation Test

- [ ] Test from a clean clone or clean copied project directory.
- [ ] Follow only the public README instructions.
- [ ] Create a new virtual environment and install dependencies.
- [ ] Configure Hermes without exposing or storing credentials in the
  repository.
- [ ] Configure one test RPC endpoint.
- [ ] Run one small EVM protocol from the guided menu.
- [ ] Confirm a basic user can find:
  - [ ] The research notes
  - [ ] The token page
  - [ ] The verification checklist
  - [ ] The Obsidian vault directory
  - [ ] Project status and recovery instructions
- [ ] Record every undocumented step or confusing message.

## Phase 6 — Failure and Recovery Testing

- [ ] Interrupt a crawl and confirm it can be safely rerun.
- [ ] Interrupt a Hermes extraction and confirm completed ledgers are reused.
- [ ] Test an unavailable or malformed documentation URL.
- [ ] Test a site with no sitemap.
- [ ] Test a CoinGecko miss or temporary network failure.
- [ ] Test a missing RPC configuration.
- [ ] Test an unsupported chain verification request.
- [ ] Test a verification page containing only manual-review tasks.
- [ ] Confirm failures leave usable partial research and actionable messages.
- [ ] Confirm no command silently deletes user-created files or notes.

## Phase 7 — Human Interface Review

- [ ] Complete one project using only `python main.py` and its guided menu.
- [ ] Ensure each menu choice explains its outcome in plain language.
- [ ] Ensure long-running operations display progress and resume guidance.
- [ ] Make manual-review tasks understandable without reading source code.
- [ ] Confirm separate tools remain callable by power users.
- [ ] Add a clear “research without verification” workflow.
- [ ] Verify that the menu never implies manual claims were automatically
  confirmed.

## Phase 8 — Documentation and Release Cleanup

- [ ] Add a five-minute Quick Start section at the top of `README.md`.
- [ ] Add Windows virtual-environment and Hermes troubleshooting.
- [ ] Repair broken character encoding in documentation and generated labels.
- [ ] Separate beginner instructions from advanced architecture details.
- [ ] Document supported chains and scanner operations.
- [ ] Document limitations and manual-review behavior.
- [ ] Document the `output/vault/` Obsidian workflow.
- [ ] Add one compact example project or example output set.
- [ ] Confirm `.env`, credentials, local caches, evidence, generated output,
  and `.venv` are excluded from Git.
- [ ] Review dependencies and remove anything no longer used.

## Phase 9 — Beta Acceptance Gate

Call the release beta only when all of the following are true:

- [ ] The virtual environment can be created from scratch using documented
  commands.
- [ ] Hermes can be configured and tested using documented commands.
- [ ] The guided complete workflow succeeds on a normal EVM protocol without
  developer intervention.
- [ ] Derive completes without protocol-specific extraction patches.
- [ ] A non-EVM protocol produces useful research with honest scanner
  limitations.
- [ ] Interrupted workflows resume safely.
- [ ] Registry output contains relevant addresses rather than exhaustive
  developer catalogs.
- [ ] CoinGecko supply enrichment works independently of AI and fails visibly.
- [ ] Verification tasks clearly separate scanner-ready checks from analyst
  work.
- [ ] Obsidian output is readable, linked, concise, and free of broken table
  formatting.
- [ ] The complete automated test suite passes.
- [ ] A clean-install tester can operate the tool using only its documentation.

## Recommended Beta Definition

DEFINALYZER beta provides reliable, concise documentation extraction,
protocol-token discovery, deterministic supply enrichment, Obsidian-ready
research, structured analyst verification checklists, and raw evidence
collection for supported EVM operations. Unsupported or protocol-specific
claims are routed to explicit manual review rather than interpreted,
confirmed, or silently omitted.

