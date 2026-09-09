# DEFINALYZER Development Handoff

Last updated: 2026-09-07

## Current state: surgical recovery of practical defaults

The user stopped the V2 redesign and approved only restoration of the retained
concise Analyze Project and earlier report workflows. That recovery is implemented.
Normal extraction, freshness checks, registry, verification and Q&A no longer
activate scope/fact processing from leftover V2 files. New dashboard reports use
schema 1; V2 preparation and report mutation controls are disabled. Existing V2
reports, source links and saved exports remain readable; implementation is dormant.
Crawler fidelity, cancellation/process cleanup, persistent job diagnostics, asset
identity/navigation and report presentation were retained. No user output changed.
Local validation: 532 Python tests (531 passed, one skipped), 20 JavaScript tests.
No Hermes calls, live crawl/extraction, production restart or live acceptance test.
A small live protocol test requires explicit user approval; restart the existing
dashboard before that test. Do not resume V2 development or the historical phases.

The material below is historical and does not authorize further work.

### Historical Phase D result


The user authorized Phase D with the dashboard closed. Read
[Phase D results](docs/EXTRACTION_PHASE_D_RESULTS.md) before continuing.
One real selected-source preparation ran in `tmp/phase-d-workspace` using four
full byte-identical Phase B snapshots and existing Hermes `gpt-5.6-sol` settings.
No expected fixture answers were sent to the model. No actual Pump research was
regenerated, moved or replaced, and no dashboard operation is required of the user.

The trial used all six provider dispatches (four returns, two timeouts), 97,125
prompt characters and 479.6 seconds of the eight-minute preparation allowance.
It saved 16 accepted claims; all 40 original claim/check references resolve.
Only two of five extraction batches completed. Scope timed out, all source blocks
remained qualified, and only the protocol identity was available. The later fee
exceptions and token methodology were not reached. The six-quantity fee row and
label-only correction worked; this is still not a demo acceptance pass.

All 1,819 readable original output files remained byte-identical; the held
dashboard lock was explicitly unreadable. No output entries were added/deleted.
Pump job `3c561d4de2511876` remains cancelled. No trial Python/Hermes processes
remained after completion. The existing dashboard backend was left alone.

Artifacts: `tmp/phase-d-live/run.json`, `progress.txt`, every live prompt/response,
`batch-plan.json`, `inspection.json` and `hermes-session-metadata.json`.
`scripts/run_extraction_phase_d.py` refuses to rerun an existing recorded trial;
`scripts/inspect_extraction_phase_d.py` performs only offline citation inspection.

Next recommendation: correct preparation planning before Phase E. Five material
batches require at least eleven scope/extract/check calls in the current design,
so merely imposing a six-call stop cannot deliver full coverage. Prioritize useful
fees and token rights, consolidate prompt/check overhead, retain separate token
identity and reserve check time/calls. The final extraction was dispatched with
only 12 seconds and no call left for its check. Repeated unresolved-scope wording
also burdens every fee claim. See the results document for the bounded correction
scope. Runtime was not altered during D. Do not reset this live budget, borrow
Phase E's four calls, run another trial, or proceed to Phase E/7 without the next
user instruction. No new live calls remain authorized by this completed trial.

### Phase C context (completed before D)

The user authorized Phase C. Read [Phase C changes](docs/EXTRACTION_PHASE_C_CHANGES.md)
before continuing. The report preparation action now selects saved documents and
shares a persisted six-call/144k-character/eight-minute budget across scope,
extraction and checks. Accepted partial research is published with its selection
and incomplete-coverage notice. The complete Analyze workflow remains separate;
its scope/fact stage has a 12-call research limit and stops later stages if partial.

Version 2 extraction fixes leading decimals, allows complete fee rows (up to 16
quantities), separates question-label correction from semantic support, repairs
ordered quote fragments to their actual original span, carries source introduction
context, and handles documented SDK spelling. One repair per batch, stable pending
repair identity and conservative duplicate suppression reduce repeated work.
Calculator/clickwrap blocks and unassessed fee images produce specific gaps.

Dashboard reports default to Brief. Brief reviews are at most 500 narrative words;
questions at most 180. They use a writer plus one combined original-support and
conclusion check within two calls. Standard full reviews retain bounded repair.
Reports never start extraction; known missing current measurements need no AI call.

No live Hermes calls, crawls, user-project research writes or dashboard restarts
were performed during C. Pump stays cancelled. Existing data/versions remain saved.
Validation: 531 Python tests ran (530 passed, one skipped); all 26 dashboard JS
tests passed. The 14-case source fixture retains its original hashes/anchors.
Phase D (High) was subsequently authorized and tested as recorded above.
Phase E (High) retains four calls for one report and one question but has not
started. Phase 7 and full Pump/NEAR reruns remain paused. The running dashboard
needs a restart before using the new Python preparation endpoint.

### Phase B context

The immediate user priority is to get the entire tool ready for a job-resume demo.
The user authorized Phase B with this constraint. Read
[the Phase B demo standard](docs/EXTRACTION_PHASE_B_STANDARD.md) for the current
acceptance scope: one Pump.fun / $PUMP demonstration, concise saved research,
protocol/token separation, a brief report, a saved-research question, source
inspection, export and Stop controls. Do not expand into a general research engine
before this works. Preparation may happen before presenting; generated demo work
must still come from the real application pipeline.

Phase B added a frozen 14-case evaluation fixture with 14 original source blocks
and seven byte-identical snapshots under `tests/fixtures/extraction_demo/`.
Six cases define demo content and eight cover focused regressions. The offline
checker `python scripts/check_extraction_demo_fixture.py` passed all provenance
checks, including 22 exact anchors. This is fixture integrity, not an application
or model-quality pass. No Hermes calls, runtime changes or research writes occurred.

The Phase B plan specified C (Extra high), limited to demo failures and necessary
regression protections. D/E retain a proposed total budget of ten live provider
calls; the standard allocates six to preparation and four to report/question
validation, with character/time caps. Phase C has since been authorized and
implemented as described above. Pump stays cancelled; Phase 7 and full reruns stay paused.

### Phase A context

The main redesign remains through Phase 6; Phase 7 is paused. The user authorized
Phase A of the separate extraction diagnosis roadmap after rejecting the long
Pump preparation run. Read [the Phase A audit](docs/EXTRACTION_PHASE_A_AUDIT.md)
before continuing. Diagnosis is complete, with no new Hermes/provider calls,
application-code changes, research regeneration or automatic resumption.

The saved run has 45 fact prompt records (24 in repair rounds), nine completed
batches out of 35 planned, and 63 accepted checkpoint claims. All original claim
references resolve. Confirmed problems include leading-decimal parsing, a hidden
four-quantity limit, full claim repair for question-label errors, brittle subject
naming/context, duplicated repair output and poor priority/budget discipline.
Some semantic checks correctly caught real errors and must be preserved.

The roadmap established in Phase A was B (High): define a useful extraction
standard and a small saved-source evaluation sample; C (Extra high): targeted implementation/local tests;
D (High): bounded live sample; E (High): report reuse validation. The proposed
live allowance is ten Hermes calls total across D/E, not authorization to run
them now. B is now complete as described above. Pump stays cancelled; no full Pump/NEAR rerun.

### Main redesign context

The user requested a fresh review followed by a phased redesign covering asset
identity/navigation, automatic subject scoping, source-traceable research, and a
replacement report experience suitable for eventual multi-source research.
The user authorized Phases 2, 3, 4, 5 and 6. Stable asset identity, corrected token
navigation/supply controls, scope routing, structured claims, original-source
support checking, incremental topic views and V2 reports are implemented.
Stop before Phase 7 unless requested. The full NEAR rerun remains explicitly deferred.

- Proposed contracts, migration, workflow, and phase gates:
  [Research design V2](docs/RESEARCH_DESIGN_V2.md).
- Fictional chain/protocol/token report examples and acceptance scenarios:
  [Phase 1 examples](docs/PHASE_1_EXAMPLES.md).
- The design remains the roadmap. Source scope is implemented by Phase 3;
  Phase 4 implements fact lineage; Phase 5 now implements the report replacement.
- The Uniswap project/source paths described in the historical incident below
  were absent when inspected during Phase 1. Do not assume that resumable state
  remains locally available. NEAR and other saved project corpora are present.

### Phase 2 outcome

- Implementation and user guide: [Asset identities](docs/ASSET_IDENTITIES.md).
- `definalyzer/asset_identity.py` owns a stable-ID catalog, deployment/context
  relationships, transaction history/recovery, migration, and asset research setup.
- Registry discovery now reruns on changed inputs even with existing tokens,
  preserves manual records and omitted assets, and reuses unchanged attempts.
- Dashboard Tokens/Coins display saved names/symbols and stay in the asset context;
  a dedicated research project is optional and creates no automatic provider job.
- Asset context pages are project-specific. Market caches and retrieval resolve
  asset identity, preserve non-EVM address case, and avoid unrelated ticker reuse.
- Existing V1 report evidence continues to recheck its original legacy retrieval
  scope; migration does not rewrite its evidence/approval/export packages.
- Applied migration: 10 assets across nine project registries; all 1,640
  pre-existing output files retained identical SHA-256 hashes. A repeated migration
  retained the same catalog. No ownership conflicts were found in this workspace.
- Migration evidence: `tmp/phase2-migration-result.json` and
  `tmp/phase2-original-output-hashes.json`; durable transactions are under
  `output/entities/history/`. These are additive files, not cleanup targets.
- Validation: 430 Python tests ran with one skipped, plus six dashboard JavaScript
  tests; syntax/diff checks passed. The live provider acceptance test remains due
  in Phase 6. No provider or external data calls were made by the migration.
- Restart an existing dashboard process to load the new Python routes/inventory.
  Phase 2 did not terminate a possibly running dashboard process.


### Phase 3 outcome

- Guide and limitations: [Automatic research scope](docs/RESEARCH_SCOPE.md).
- `research_scope.py`: immutable original snapshots, exact block locators, bounded
  classification, cited subject/applicability validation, omission rescue,
  checkpoints, cumulative budgets, revision history and manual corrections.
- Scope runs automatically before new extraction. Scope revisions invalidate
  stale research; output metadata records which revision generated a page.
- Dashboard scope card and optional adjustments preserve existing navigation;
  token research and Refresh token supply were checked in an isolated browser UI.
- Exact-page crawling no longer expands to its parent. Sitemap results are
  host/pattern constrained; docs-root fallback uses observed navigation.
- Aave enrichment fetching is an explicit supplemental-source registration with
  immutable response snapshots, isolated from subject classification.
- NEAR measurement: 130 documents / 324 blocks, 23 planned classification calls
  with bounded excerpts; default cumulative limit 32. No full live corpus run.
- Three single-call Hermes smoke checks on four saved NEAR blocks caught and
  corrected a base-chain attribution ambiguity. One intermediate response failed
  citation validation. Final result separated chain mechanics, signing, intents
  and bridge context. Diagnostic outputs remain under `tmp/phase3-live-*`.
- User source pages, generated notes and reports were not regenerated or moved.
  Scope will be prepared in their actual projects when they run Research scope
  or Analyze project. An isolated UI fixture lives under `tmp/phase3-ui-workspace`.
- Scope routing does not independently verify claims. Enforced fact lineage is
  Phase 4; full corpus/provider/report acceptance remains later work.

### Phase 4 outcome

- Guide, storage contract, bounds and limitations: [Source-supported research](docs/RESEARCH_FACTS.md).
- `research_facts.py` accepts documented claims only, with exact immutable source
  references, literal/subject/scope checks and a separate original-source AI check.
  At most two targeted repairs per affected batch; failed/dropped candidates become
  gaps. Supported work is retained, and interrupted attempts keep their budget use.
- `research_profiles.py` defines versioned chain/protocol/token questions and
  separate observation needs. Conflicts, evidence, documented periods and unknown
  freshness remain separate. Docs never certify current measurements.
- Active research pages render accepted facts deterministically. Source opens the
  original passage and surrounding context. Legacy/manual notes stay byte-identical;
  a supported version is the default topic view with Original notes and Compare
  changes. Edited proposed versions are preserved too. No duplicate generated
  topic navigation. Comparisons omit internal metadata and revision hashes.
- Changed source files invalidate affected extraction batches. Unchanged facts,
  supported pages and unrelated topic fingerprints are reused. New contradictory
  documents are considered. Qualitative conflict checks are bounded, with failures
  disclosed. Source changes during a run prevent a stale commit.
- Q&A can retrieve immutable originals. Q&A, verification planning and newly built
  legacy report evidence use active topic views. Fact views have one writer;
  verification links remain in the verification page. Existing V1 frozen packages
  and approvals stay intact. V2 reports remain entirely Phase 5.
- Validation: 465 Python tests run (464 passed, one skipped), 13 JavaScript tests
  passed; `tmp/phase4-final-tests.txt`. Browser fixture checked original-source
  popups, comparison and existing token context/supply navigation. A false stale
  scope notice and noisy diff were found and corrected with regression tests.
- Live Hermes smoke: synthetic chain/bridge source, three supported claims, four
  calls (one targeted repair), 33,980 input characters, 65.4 seconds. Saved under
  `tmp/phase4-live-*`; no NEAR/provider jobs touched the user's research.
- Preservation: all 1,640 original files remain byte-identical, recorded in
  `tmp/phase4-preservation.json`. No actual dashboard was stopped or restarted;
  only this turn's isolated fixture process was stopped after testing.
- Restart the real dashboard to load the code. Existing NEAR research stays mixed
  until the user chooses the deferred rerun. Do not run it merely to finish this
  update. Full corpus quality, workload tuning and explicit exhausted-budget retry
  controls remain Phase 6; another ordinary resume does not refill failed budgets.

### Phase 5 outcome

- Guide: [Reports V2](docs/REPORTS_V2.md). New report creation defaults to schema
  version 2; V1 packages and their existing lifecycle/export handlers are retained.
- `report_v2_store.py`, `report_v2_evidence.py`, `report_v2_writing.py`,
  `report_v2.py`, and `report_v2_export.py` implement isolated V2 packages, frozen
  original evidence, request-relative readiness, narrative/assertion coverage,
  original-source and conclusion checks, at most two repair rounds, durable resume,
  exact approval bindings, and immutable Markdown/HTML/PDF exports.
- Dashboard has a direct Reports button. Full review / Answer a question use one
  Generate report action. Paragraph, section and whole-report revisions, exact
  manual wording, saved Markdown reconciliation, edited notes checks, version
  comparison and readable chart choices replace manual internal-field controls.
- Source-supported Phase 4 research is a prerequisite. Missing/stale research or
  requests requiring unavailable measurements produce a short explanation and
  concrete missing inputs. Report generation never crawls or analyzes a project.
  Explicit Use latest research reads the latest prepared facts into a new version.
- Every final revision binds prose, notes, assertions, review, scope/coverage and
  original evidence. Source changes mark earlier evidence without rewriting final
  publications. Edited copies cannot enter an export; approval/export manifest
  changes are detected. Recommendations are optional, with separate approval only
  when present. The first export freezes its validated chart selection.
- Browser fixture verified automatic creation/opening, exact source popups,
  paragraph revision, before/after comparison, finalization without a mandatory
  recommendation, and all four download links. Only fictional fixture data was
  finalized. The temporary browser and fixture server were closed afterward.
- Live Hermes smoke: six calls, one automatic repair, 174.9 seconds, six supported
  paragraphs separating Northstar consensus from Harbor Bridge authority. Evidence
  came from the isolated fictional Phase 4 corpus. Diagnostics:
  `tmp/phase5-live-result.json`, `tmp/phase5-live-log.txt` and the copied workspace.
- Two-page PDF rendered and visually inspected; citation wrapping was corrected.
  Development fixture exports under `tmp/phase5-*` predate some final integrity
  hardening and are disposable QA records, not user publications.
- Final validation: 487 Python tests ran (486 passed, one skipped), plus 18
  JavaScript tests passed. Logs: `tmp/phase5-verified-tests.txt` and
  `tmp/phase5-js-tests.txt`; syntax and diff checks passed. One earlier suite run
  hit a transient Windows localhost connection abort in a pre-existing HTTP test;
  the complete rerun passed after closing the temporary UI fixture. The initial
  new HTTP test harness also needed a corrected provider-factory attribute and
  job response shape; the final harness uses only its deterministic provider.
- Preservation audit `tmp/phase5-preservation.json`: all 1,640 original output
  files have identical SHA-256 hashes; none are missing. No actual saved research,
  source collection or NEAR rerun was performed. Restart the real dashboard to
  load these code changes. Phase 6 follow-up is documented below.

### Phase 6 outcome and acceptance record

- Guide and empirical evidence: [Phase 6 acceptance](docs/PHASE_6_ACCEPTANCE.md).
- Isolated live samples: Ethereum proof-of-stake documentation, Aave liquidations,
  AAVE governance, and a held-out fictional Cedar/Transit Bridge/Luma/LUMA corpus.
  No actual project was recollected, regenerated, moved or deleted.
- Fixed source loss in Crawl4AI text-only conversion: inline formatting tails
  contained liquidation eligibility conditions and voting/execution delays.
  Real HTML conversion now retains them, keeps short statements and bypasses
  converted-page caching when the application chooses to collect a page.
- Readable Markdown evidence resolves to exact original spans. Scope, facts and
  reports use the shared resolver; original hashes and context remain authoritative.
  Token subject aliases come from saved identities, including catalog bindings.
- Compact report prompts retain original passages and omit repeated metadata.
  Revisions receive saved review findings automatically. Malformed reviewer
  responses retry their checks within the existing limit without rewriting valid
  prose; counterevidence against unsupported claims becomes actionable feedback.
  Valid but unlinked supporting originals trigger a citation repair rather than
  another unchanged support check. Brief Windows checkpoint locks get bounded
  atomic-write retries without repeating completed provider requests.
- Dashboard jobs with unsuccessful results have terminal Needs attention status.
  Windows provider descendants share a Job Object lifetime, tested under timeout
  and hard owner termination. Interrupted jobs and attempts remain recoverable.
- Retry unfinished research preserves accepted work and original attempts, binds
  the saved collection, and refuses stale/rule-changed retry requests. Fix review
  issues starts a bounded report revision without requiring a typed repair prompt.
  Exhausted pending report runs no longer offer a futile Resume action.
- RPC acceptance passed on Ethereum, Arbitrum and Base: identity validation and
  pinned numbered-block retrieval. No transaction execution or Phase 7 adapter.
- The held-out corpus retained all eleven annotated checks in eight supported
  claims. Its focused report passed. The actual dashboard opened frozen original
  evidence in one click, displayed token supply controls under the token, and
  completed a live Ethereum full-report repair into a new reviewed revision.
- Preservation audit checked all 1,663 pre-Phase-6 output files and the earlier
  1,640-file baseline: identical SHA-256 hashes, none missing.
- Final live-case results, measured workload and regression totals are maintained
  in the acceptance guide. Test workspaces and failed attempts remain in `tmp/`.
- Final results: seven reports passed source and conclusion checks; 37 real-case
  accepted facts resolve to their originals. Some scope blocks remain unresolved
  and were safely retained for checked extraction, as detailed in the guide.
  505 Python tests ran (504 passed, one skipped), and 21 JavaScript tests passed.
  Development acceptance recorded 139 provider invocations, including failed and
  interrupted attempts; this is not a normal per-project cost estimate.
- No dashboard preparation or NEAR rerun is required to complete Phase 6. Restart
  the actual dashboard when ready to load the code. The temporary QA browser and
  server were closed; the actual dashboard was not stopped or restarted.

## Read this first

### Pump cancellation and Stop controls

The user explicitly rejected the long Pump run and requested immediate stop plus
an in-app Stop control. Job `3c561d4de2511876` was cancelled at
2026-09-07 10:21:42 UTC. Two old dashboard instances (actual worker PIDs 17400 and
25916, launcher PIDs 30248 and 3212) shared the workspace; both were terminated
to prevent continued dispatch. No user Hermes model-picker process was stopped.
Pump scope/fact checkpoints were retained. Only dashboard job metadata was
updated to record cancellation; its previous state is in
`tmp/pump-jobs-before-stop.json`. Do not resume Pump automatically.

Added authenticated `POST /api/jobs/{id}/cancel`, per-worker cancellation events,
queued cancellation, Stopping/Stopped states, and Stop buttons in Activity and
the progress banner. Active provider trees are terminated with cleanup; crawler
tasks are cancelled; synchronous network calls check cancellation before the next
request and may need their current request to finish/timeout. Completed writes
remain saved. Dashboard closure cancels jobs and waits for cleanup. An OS-held
workspace lease prevents duplicate dashboard owners and releases on exit/crash.
Tests cover real local provider-child shutdown, retained checkpoints, queued-job
suppression, subsequent independent jobs, async cleanup, HTTP retry suppression,
endpoint authentication, duplicate-instance protection and UI stop controls.
Validation: 514 Python tests ran, 513 passed and one skipped; 26 JS tests passed.
No live Hermes calls were used for this fix. The large-corpus batching/retry cost
problem is not solved by cancellation; it still needs focused work before another
full Pump or NEAR run. Phase 7 remains unauthorized.

### Post-Phase-6 Pump report UX correction

The user's Pump full review and question were blocked because `pump-fun` has
legacy research but no Phase 4 scope/facts. This was a preparation prerequisite,
not evidence that Pump documentation lacks useful information. No Pump analysis
or external AI call was run while correcting the UI.

Report summaries now derive an actionable recovery state from current research
without rewriting frozen attempts: Prepare research (explicit analysis form),
Generate report when ready, or visible missing inputs and Add research sources.
New-report requests on an already-known unprepared project open preparation
instead of adding another blocked attempt. Compare versions requires revision 1
or later; unchanged insufficient reports do not offer Use latest research.
New blocked report/notes files state the actual prerequisite and that review was
not run. Numeric space entities render as spaces without decoding encoded HTML.
Actual Pump summaries were checked read-only; existing Pump files were retained.
Validation: 507-test Python suite passed with one skip, 24 dashboard JS tests
passed; the final whitespace rendering change also has focused dashboard tests.
Restart the dashboard to load this fix. Preparing Pump remains a separate user
action and may use Hermes; NEAR and Phase 7 remain deferred.

DEFINALYZER is a local, AI-assisted DeFi research workspace. Its central purpose
is to turn official protocol, chain, or native-token documentation into concise,
fact-first research notes that are useful to a human analyst or another model.
It is not intended to reproduce documentation, write promotional summaries, or
claim that every statement can be verified automatically.

The current product direction is a focused demo that must reliably do four
things:

1. collect documentation from ordinary documentation sites and public GitHub
   repositories and preserve cleaned Markdown locally;
2. extract concise, decision-relevant research pages;
3. create categorized verification work and collect raw evidence where the
   existing EVM collector supports it;
4. answer project questions and produce reviewed, evidence-bounded reports that
   can be exported as Markdown, HTML, and PDF.

External quantitative datasets are intentionally deferred. Do not expand the
scope into DefiLlama, Tokenomist, Dune, or additional governance sources until
the current document-to-notes-to-verification-to-report flow is demonstrably
stable.

## User priorities and product rules

- Keep research pages compact and factual. They are data extraction pages, not
  essays, reports, or long copies of source documentation.
- Prefer blank or explicitly unavailable fields over guessed information.
- Never treat missing public evidence as proof that a claim is false.
- Verification is a categorized analyst to-do list with an automated layer for
  supported checks. It is not a promise to verify everything.
- Evidence collection must remain separate from interpretation. Raw collector
  output does not itself confirm or reject a claim.
- Evidence evaluation requires explicit human approval before verification
  status changes.
- Reports should answer the research question in polished management-facing
  prose. Research limitations belong primarily in separate Analyst Notes,
  although material uncertainty may still be disclosed in the report.
- Protocol projects should create pages only for protocol-native or
  protocol-issued tokens, not every asset used by the protocol.
- Chain-native assets belong under Coins; protocol-native assets belong under
  Tokens.
- The local dashboard is the preferred basic-user interface. Terminal commands
  and modules remain available to power users.
- Markdown and JSON remain canonical and portable. The dashboard is a shell over
  those files, not a separate database-backed research product.
- Do not expose implementation-only text, frontmatter, internal request blocks,
  Obsidian terminology, or software link maps in the dashboard reader.
- The vault-compatible structure may remain internally, but dashboard-facing
  language should say research pages/folders rather than Obsidian.
- Preserve existing user data and unrelated working-tree changes. Do not delete
  or rewrite projects unless explicitly requested.

## Current release position

The project is a strong alpha / focused demo candidate, not yet beta. Unit and
integration coverage is substantial, but the most recent real-world Uniswap
acceptance run exposed a process-lifecycle and observability failure. Resolve
and retest that failure before calling the build beta-ready.

The README now contains a `Demo scope` section and an `Upcoming additions`
section. The planned future data sources are supplementary and must not make the
core documentation workflow dependent on a vendor.

## Main architecture

### Entry points

- `main.py` — main CLI entry point.
- `python main.py` — guided terminal menu.
- `python main.py dashboard` — local dashboard.
- `Start DEFINALYZER Dashboard.bat` — Windows dashboard launcher using the
  project virtual environment.
- `python -m blockchain_collector` — lower-level collector entry point.

### Core modules

- `definalyzer/app.py` — CLI parsing, guided menu, and orchestration helpers.
- `definalyzer/application.py` — UI-neutral application boundary shared by CLI
  and dashboard.
- `definalyzer/workspace.py` — project manifests and canonical output paths.
- `definalyzer/dashboard.py` — loopback-only HTTP dashboard, background jobs,
  Markdown rendering, and report routes.
- `definalyzer/dashboard_assets/` — dashboard HTML, CSS, JavaScript, and logo.
- `crawler/` — documentation discovery, website crawling, GitHub Markdown
  import, and source cleanup.
- `definalyzer/extraction.py` — single-call and resumable chunked research
  extraction.
- `definalyzer/registry_workflow.py` — registry and native-token extraction.
- `definalyzer/verification_planning.py` — categorized verification checklist
  and machine-readable planning state.
- `blockchain_collector/` — raw EVM evidence collection.
- `definalyzer/evaluation.py` — evidence assessment proposals and human review.
- `definalyzer/analyst_review.py` — project Q&A and optional saved answers.
- `definalyzer/report_contract.py` — report package schema and invariants.
- `definalyzer/report_evidence.py` — bounded local evidence preparation.
- `definalyzer/report_generation.py` — structured AI draft generation and
  deterministic Markdown rendering.
- `definalyzer/report_quality.py` — independent representation-quality review.
- `definalyzer/report_lifecycle.py` — targeted revisions and human finalization.
- `definalyzer/report_presentation.py` — management-facing report presentation.
- `definalyzer/report_export.py` — immutable Markdown/HTML/PDF export and
  evidence-derived charts.

### Canonical output layout

- `output/projects/<slug>/` — manifest, extraction state, jobs, evidence, and
  report state.
- `output/sources/<slug>/` — cleaned source Markdown and crawl report.
- `output/registries/<slug>/` — normalized registry data.
- `output/vault/Protocols/`, `Chains/`, `Tokens/`, `Coins/` — readable research
  pages.
- `output/vault/Verification/` — categorized verification pages.
- `output/vault/Reports/` — management reports, Analyst Notes, quality reviews,
  and exports.

## Provider boundary

Hermes is currently the implemented AI provider. DEFINALYZER invokes the Hermes
CLI in inference-only mode with an explicit empty toolset. Hermes credentials
are managed by Hermes and are not stored by DEFINALYZER.

Relevant implementation: `definalyzer/providers.py`.

- Default provider timeout: 900 seconds.
- Windows prompt size is constrained before calling Hermes.
- Normal Hermes non-zero exits, empty responses, startup failures, and timeouts
  raise `ProviderError` and should be caught by dashboard job handling.
- The last escalated `hermes doctor` check found OpenAI Codex authentication
  active and no core Python/SQLite/SSL problem.
- Hermes configuration schema is one version behind (`v37` to `v38`). Do not
  run `hermes doctor --fix` without user approval. Optional npm/build-tool
  advisories are not established as the cause of the interrupted run.

## Dashboard status

The dashboard is local-only and binds to loopback. It uses a per-process token
for mutating requests, rejects non-local origins/hosts, sanitizes Markdown, and
does not send `.env`, RPC endpoints, or Hermes credentials to the browser.

Recent UI work includes:

- black cyberpunk visual theme and supplied DEFINALYZER logo;
- project navigation grouped into Protocols, Tokens, Coins, and Chains;
- collapsible research-page groups;
- readable Markdown rendering without frontmatter or implementation blocks;
- full-width reader expansion and horizontally scrollable tables;
- dashboard guide under Workspace;
- project creation with optional immediate analysis;
- Project Controls for analysis stages, sources, manual assets, verification,
  Q&A, reports, and deletion;
- report lifecycle controls and export links;
- project/page search;
- activity panel and job status display.

### Dune removal

The unfinished copy/paste Dune query assistant was removed from the dashboard,
guided menu, and public CLI. Internal Dune modules/application methods remain so
they can be reused later when authenticated Dune API execution and result
ingestion are designed. Do not re-expose the old dialogue during the current
demo phase.

## Report subsystem

Reports are intentionally separate from concise research pages.

Current lifecycle:

1. create a focused question or full-review report scope;
2. prepare a bounded evidence package from project-owned local sources;
3. ask the configured provider for structured findings and a report plan;
4. deterministically render a management-facing report and separate Analyst
   Notes;
5. run an independent quality review against exact saved evidence;
6. optionally revise one selected assertion without expanding its evidence;
7. explicitly approve the reviewed revision;
8. export immutable Markdown, HTML, and PDF files.

Charts are allowed only when their values are read from dated structured saved
evidence. The model or user must not type chart values into the report. If no
suitable structured evidence exists, export without a chart.

A live Aave report test previously reached a passing quality review after
revision. Report prose was subsequently improved so supported findings render
as narrative paragraphs rather than an outline of bullets. Full reports must
remain polished answers; missing information belongs primarily in Analyst
Notes.

## Uniswap acceptance-test incident

Project: `output/projects/uniswap/`

Primary documentation URL:
`https://developers.uniswap.org/docs`

Observed state:

- crawl completed with 335 saved pages and no recorded crawl failures;
- shared research extraction planned 85 source batches;
- batches 1 through 67 were saved successfully;
- `output/projects/uniswap/extraction/shared-research/state.json` remains
  `in_progress`;
- batch 68 and later remain pending;
- the last successful output was
  `extraction/shared-research/ledgers/chunk-0067.md` at approximately
  2026-09-04 19:38 local time;
- immediately afterward Hermes updated its plugin-toolset cache, consistent with
  starting the next invocation;
- the dashboard Python process subsequently ceased to exist;
- no Python application-crash event, Windows memory-exhaustion event, or normal
  caught provider error was preserved;
- the browser stayed open and showed an old `13s ago` timestamp, making the dead
  process appear frozen.

Important conclusion: this was not diagnosed as a normal slow model response.
The parent dashboard process terminated. The exact external cause cannot be
reconstructed because the old dashboard kept job state only in RAM. Possible
causes such as terminal closure, forced termination, or a hard process failure
cannot be distinguished from the surviving files. Do not claim a more precise
cause without new evidence.

### Incident fixes already implemented

- Added a prominent progress strip above the workspace.
- Batch messages such as `[67/85] Saved chunk-0067` drive measurable progress.
- The visible timestamp refreshes continuously.
- Five minutes without a progress message produces a `possibly stalled`
  warning.
- Loss of the dashboard server produces `Dashboard connection lost` instead of
  leaving a frozen timestamp.
- Dashboard activity is persisted to `output/dashboard-jobs.json` after every
  submit, update, and progress message.
- On startup, persisted `queued` or `running` jobs are changed to
  `interrupted`, preserving their last progress and explaining that the prior
  dashboard process ended.
- Unexpected exceptions in the dashboard server write
  `output/dashboard-crash.log` before being re-raised.
- The activity panel recognizes and renders `interrupted` jobs.

These changes improve diagnosis and recovery but do not prove or eliminate the
original external termination cause. A process forcibly terminated by Windows,
the user, or another application cannot be made immortal; the correct product
behavior is durable state, truthful interruption reporting, and safe resume.

### Required next test

Do not blindly resume the 85-batch Uniswap run and call the issue solved.

First perform a controlled, short provider-backed extraction through a freshly
started dashboard:

1. restart the dashboard so the new assets and persistence code are loaded;
2. verify the prominent progress strip appears;
3. run a small existing project operation that requires only one or a few Hermes
   calls;
4. confirm the progress strip updates, the job finishes, and
   `output/dashboard-jobs.json` contains its terminal state;
5. intentionally stop and restart the dashboard during a disposable test job
   only if a safe interruption test is needed; confirm it becomes
   `interrupted` on restart;
6. only then decide whether to resume Uniswap without refresh.

If Uniswap is resumed, the extraction state should reuse batches 1–67 and begin
with batch 68. Do not enable refresh and do not delete the project. Treat the
very broad 335-page source set and 85 provider batches as a separate scope and
efficiency concern. Determine whether `developers.uniswap.org/docs` is an
umbrella corpus that includes materially separate products (for example
Unichain and API integration material) before accepting it as a normal
single-protocol workload.

## Testing status

Most recent complete suite before the interruption-diagnostic additions:

- 413 tests passed;
- 1 Windows symlink test skipped because the host did not grant symlink
  creation; its simulated traversal-equivalent test passed.

Most recent focused dashboard suite after the progress, persistence, and crash
diagnostic changes:

- 26 dashboard tests passed;
- JavaScript syntax check passed;
- `git diff --check` passed.

Run the full suite before release or commit:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --check definalyzer/dashboard_assets/app.js
git diff --check
```

The virtual-environment Python may require normal host permissions in Codex due
to Windows execution restrictions. Do not mistake a sandbox `Access is denied`
message for a project test failure.

## Git and working-tree state

There is a substantial uncommitted development set containing the report
subsystem, dashboard work, documentation changes, and tests. Inspect with:

```powershell
git status --short
git diff --stat
git diff --check
```

Do not discard or reset these changes. The repository also has an untracked
`tmp/` directory; inspect it before deciding whether it is disposable. Do not
delete it merely to make `git status` clean.

No commit or push was requested for the latest demo-scope, report, or dashboard
diagnostic work.

## Deferred roadmap

After the core demo passes fresh end-to-end acceptance tests, planned additions
may include:

- provider-neutral external-data adapters with dated snapshots and provenance;
- DefiLlama protocol, chain, TVL, yield, and fee/revenue data;
- authenticated Dune API query execution, error handling, and result ingestion;
- Tokenomist unlock and vesting data;
- Sourcify verified-contract metadata;
- optional Chainlink, L2BEAT, and official issuer feeds;
- a comparison feature built from stable normalized research/report contracts.

Governance data has no chosen universal official input yet. Leave it based on
collected official documentation and explicit analyst gaps until a reliable
adapter source is selected.

## Recommended continuation order

1. Read this handoff, `README.md`, `docs/LIMITATIONS.md`,
   `docs/APPLICATION_ARCHITECTURE.md`, `docs/DASHBOARD.md`, and
   `docs/REPORT_CONTRACT.md`.
2. Inspect `git status --short` and preserve all current work.
3. Run the full automated test suite.
4. Perform the controlled short dashboard/provider test described above.
5. If stable, assess whether Uniswap's source scope should be narrowed by
   general source-selection rules rather than a protocol-specific adapter.
6. Resume Uniswap without refresh only after that decision.
7. Inspect the generated research pages for concision, missing material facts,
   malformed tables/links, empty headings, token discovery, and misleading
   verification requests.
8. Run one supported verification path and confirm raw evidence, proposal,
   human review, and visible status behave correctly.
9. Ask one useful project question and generate a management report; run quality
   review, approve, and export it.
10. Only then decide whether the focused demo is ready to label beta.

## Avoid these mistakes

- Do not dismiss a failed or frozen real-world run merely because extraction is
  resumable.
- Do not add protocol-specific enrichment just to make one test look complete.
- Do not silently broaden a supplied documentation URL into unrelated products.
- Do not turn missing documentation into an invented claim requiring
  verification.
- Do not let AI fill deterministic market/supply fields that belong to a data
  source.
- Do not expose Dune query generation before the authenticated API design.
- Do not call a report evidence-complete merely because local notes exist.
- Do not put technical uncertainty commentary throughout a management report
  when it belongs in Analyst Notes.
- Do not make destructive cleanup decisions on behalf of the user.
- Do not proceed through multiple development phases without stating the needed
  reasoning level and stopping between phases when the user requests phased
  control.

## Phase 2 navigation correction (2026-09-06)

User identified that token clicks opened sparse identity pages while populated
content was under Related asset research. Corrected the dashboard to open the
saved context page directly, retain the token heading, and omit the duplicate
Assets section from project navigation. Identity files remain intact internally.
No research was regenerated or moved. Validated all 10 saved assets and their
project links, 27 dashboard tests and 7 JavaScript tests. All 1,640 baseline output
files remain byte-identical. Restart dashboard and refresh browser to load both
Python navigation and JavaScript changes. Further phases remain paused.

## Token supply action (2026-09-07)

Refresh token supply now appears above the populated token research page; native
coin pages show Refresh coin supply. Removed the project-wide entry from Project
Controls. The action submits the selected stable asset ID and displayed research
context's project, refreshes only that asset's snapshot and rich page, and reloads
the reader after completion. Existing CLI project-wide refresh remains supported.
Validated selected-asset isolation with duplicate tickers, button visibility,
job routing, and reader refresh. Python suite: 431 run, one skipped; the sole
initial failure was an outdated mock call expectation, corrected and rerun
successfully. JavaScript: 10 passing. No live supply jobs were run on user data.
Restart dashboard and refresh browser to load backend and UI changes.

Phase 3 final validation: 445 Python tests ran (444 passed, one skipped), 11
JavaScript tests passed, and diff checks passed. Browser validation covered the
scope card, optional correction form, preserved rich token page and supply
button using an isolated fixture. The final NEAR plan is 23 classification calls
and 526,822 prompt characters; maximum prompt 23,986. All 1,640 original output
files remain byte-identical (`tmp/phase3-benchmark-and-preservation.json`).
Final test log: `tmp/phase3-final-tests.txt`. Restart the dashboard to load the
new scope actions and card. Phase 4 was subsequently implemented; see the current outcome above.
