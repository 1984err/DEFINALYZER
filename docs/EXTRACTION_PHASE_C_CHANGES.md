# Phase C: extraction and report fixes for the resume demo

Implemented 2026-09-07. This phase changes application behavior and validates it
offline. It does not run Hermes on Pump, refresh sources or claim the live demo is
ready. Phase D is the next bounded live check.

## User-visible changes

The report's **Prepare research** action now opens **Prepare saved research**.
Suggested documents are preselected and shown by title. The user can change the
selection (at most eight saved documents) before starting. This action performs
scope, extraction, support checking and research-page publication; it does not
start the complete analysis/crawl/registry workflow.

The selected preparation has a shared limit of six provider calls, 144,000 input
characters and eight minutes. Reservations survive interruptions. Repeating the
same preparation does not reset the allowance. Accepted claims remain in
checkpoints and can be published with an explicit partial-coverage notice if the
budget is reached. Research pages state which selection was prepared; unrelated
documents are not silently presented as assessed.

The full Analyze workflow remains separate. Its scope/fact preparation now shares
a 12-call, 288,000-character, eight-minute allowance. If that preparation is
incomplete, accepted pages are saved and later workflow stages are not started.
The later registry/evidence stages of a completed full analysis are not included
in that research budget; the resume demo uses the separate six-call action.

New reports default to Brief in the dashboard. Brief report narratives have a
500-word limit; question answers have a 180-word limit. Standard full reviews have
a 900-word limit. A brief report or question uses one writing call and one combined
source-support/conclusion review, within two calls, 48,000 input characters and
two minutes. It does not launch automatic repair rounds beyond that allowance.
An invalid result stays available as a failed draft/review or saved unfinished
step, with a specific issue for an explicit later revision. Standard full reviews
retain their bounded repair workflow.

Reports continue to use saved accepted facts and the specific original passages
behind them. Opening unchanged reports and source links makes no provider call.
A request for current price without observations returns a local missing-input
result. Source gaps remain localized; they do not automatically invalidate other
supported answers. An explicitly named related subject, such as $PUMP in a Pump.fun
question, can supply the answer under its own subject identity.

## Extraction changes

- Leading decimals now retain their value: `.1%` equals `0.1%`, and differs from
  `1%`. The same numeric guard protects report prose.
- Each claim can contain up to 16 typed quantities. The prompt and validation
  message state that limit and request complete fee-table rows rather than
  truncated quantities or oversized multi-row summaries.
- Semantic support and question labels are separate. A supported checker response
  can remove irrelevant labels without rewriting the statement or making another
  provider call. Checked labels feed coverage and report retrieval.
- Citation repair can restore missing intervening source lines when quoted lines
  uniquely occur in the same order. It saves the actual contiguous original span,
  with all restored conditions, and still requires independent semantic support.
- A preceding short introduction can be included as explicit cited subject context.
  Short source introductions are carried into later batches. Namespace/package
  spelling is associated only when both literal forms occur in the same saved file.
  Tokens, programs and protocols are not merged by shared branding.
- Each affected extraction batch has at most one repair. An unrelated replacement
  missing `repair_of` no longer becomes another repair branch. Already accepted
  claims are retained. Duplicate removal is deliberately conservative: matching
  subject, applicability, original references and wording, including movement of
  the adverb “exactly.” It does not equate arbitrary bags of words or merge subjects.
- Hypothetical calculator blocks and isolated welcome/age screens are omitted
  from fact extraction with specific input gaps. Mixed methodology/token-rights
  blocks remain available. Linked fee-table images are recorded as unassessed
  image content. The prompts also exclude boilerplate within mixed blocks.

Extraction schema/rule version is now 2. Changed fingerprints create new batch
history rather than rewriting old checkpoints. Existing notes, research versions,
reports and source snapshots are retained. No saved user project was migrated or
regenerated during this phase.

## Code and verification

Core code: `research_quality.py`, `operation_budget.py`, `research_preparation.py`,
`research_facts.py`, `research_scope.py`, the V2 report modules, and the dashboard
preparation route/form. The selection operation holds the existing project
workflow lease across scope, facts and publication; individual write stages retain
their registry locks. Provider calls check cancellation and remaining budget before
dispatch. Hermes receives a timeout capped by the remaining allowance and 120 seconds.

`tests/test_extraction_demo.py` exercises the Phase B cases with original frozen
passages and controlled provider responses. It also covers a real selected-source
pipeline, authenticated dashboard dispatch, budget persistence, character/time
limits, cancellation, operation locking, two-call reports, zero-call reopening,
and the missing-price boundary. These tests verify application behavior, not live
model accuracy. Existing workflow fixtures now supply valid claims where a test
expects preparation to succeed; incomplete preparation no longer counts as a
successful full analysis.

Validation logs are `tmp/phase-c-core-final.txt`, `tmp/phase-c-full-final.txt` and
`tmp/phase-c-js-final.txt`. The portable Phase B source-integrity checker also
passes. The full suite includes existing export, preservation, token navigation,
source collection and Stop-control regressions.

Final results: 531 Python tests ran, 530 passed and one skipped; all 26 dashboard
JavaScript tests passed. The focused core run passed 111 tests. Fixture integrity
passed for all 14 cases, 14 original blocks, seven snapshots and 22 quote anchors.

## Next step and limits

Phase D should use the real provider on the explicitly selected saved sample,
with the six-call preparation ceiling. Record actual accepted/missed meanings,
errors, calls, input characters and time; do not assume it passes from these mocks.
Phase E retains four calls for one brief report and one supported question. The
total proposed D/E allowance stays ten calls, including failures. No full Pump or
NEAR rerun is needed or authorized here.

Broader semantic deduplication, general entity resolution, OCR, new connectors and
full-corpus coverage remain deferred. A provider can still return invalid output
or use the entire budget before the selection is complete; the app must show that
honestly rather than silently retrying or claiming full preparation.

Restart a dashboard that was already running to load the changed Python routes.
Phase C did not restart the user's dashboard or resume the cancelled Pump job.
