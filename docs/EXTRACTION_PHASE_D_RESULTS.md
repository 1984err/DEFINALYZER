# Phase D: live saved-source preparation

Date: 2026-09-07. The user authorized this phase with the dashboard closed.
The live trial uses the real `prepare_research` pipeline and existing Hermes
configuration, in `tmp/phase-d-workspace`. Original Pump research is not replaced.
This is an acceptance test, not a full Pump/NEAR rerun or Phase E report test.

## Result: acceptance failed; bounded test completed

The app published 16 independently support-checked documented claims and marked
preparation incomplete. Two of five extraction batches completed. All 40 stored
claim/check references resolve to immutable source bytes without error. This
confirms citation integrity, not external verification of the documented claims.

| Measurement | Observed |
| --- | --- |
| Provider dispatches, including failures | 6 of 6 |
| Returned / timed out | 4 / 2 |
| Input prompt characters | 97,125 of 144,000 |
| Preparation elapsed (persisted budget) | 479.6 seconds of 480 |
| Whole harness elapsed, including preservation/setup | 492.9 seconds |
| Scope | Timed out; all 18 source blocks remained qualified/unresolved |
| Accepted claims | 16: eight announcement, eight first fee-section claims |
| Original references checked / broken | 40 / 0 |
| Existing output files | 1,820 entries before and after; 1,819 hash-verified unchanged |
| Hash-verification exception | Held `.dashboard-instance.lock`, explicitly unreadable |

No new output entries appeared in the user's workspace. Original Pump job
`3c561d4de2511876` remains cancelled. A read-only process inventory after completion
found no remaining Python/Hermes processes matching this trial. Hermes recorded
six matching sessions, four completed API calls and zero tool calls. A timed-out
dispatch is still charged to the test's call allowance; incomplete session usage
records do not prove that no upstream computation was consumed.

| Call | Purpose | Input characters | Seconds | Outcome |
| --- | --- | --- | --- | --- |
| 1 | Scope | 20,242 | 120.2 | Timeout |
| 2 | Announcement extraction | 11,531 | 86.7 | Returned |
| 3 | Announcement support check | 21,915 | 73.8 | Eight accepted; one label corrected |
| 4 | First fee-section extraction | 11,937 | 106.5 | Returned |
| 5 | First fee-section support check | 20,055 | 80.2 | Eight accepted |
| 6 | Second fee-section extraction | 11,445 | 12.1 | Timeout at remaining allowance |

The sixth call had only a 12-second timeout and no remaining call available for
its support check. It could not finish a useful checked batch even if extraction
had returned quickly. This is a planning failure, not a reason to raise the cap.

## Frozen demo-case assessment

Assessment below compares actual accepted statements with the Phase B meanings.
The offline inspection is saved in `tmp/phase-d-live/inspection.json`; report
behavior, navigation, export and live cancellation UI remain Phase E checks.

| Case | Result | Saved result / missing content |
| --- | --- | --- |
| B01: useful fees/overview | Partial | Creation, graduation, recipients, bonding fees and variable canonical fees captured. Noncanonical fee row and useful launchpad overview absent. |
| B02: mobile leading decimal | Fail: not reached | The `.1%` mobile exception is in the later fee section. No accepted claim covers it; this trial cannot validate the live decimal fix. |
| B03: six-quantity fee row | Pass | Canonical SOL 0–420 tier preserves both bounds, units and creator .300%, protocol .930%, LP .020%, total 1.250%, without invented inclusivity. |
| B04: economics versus token rights | Partial | No holder revenue/redemption rights, approximately 50% purchase estimate and pre-April-28 exception captured. Token methodology, burn allocation period and pre-April-29 exception absent. Only the protocol subject exists; no separate token research was produced. |
| B05: hypothetical values | Pass, extraction exclusion only | Calculator block excluded and explicit non-current-data gap saved. No illustrative price/cap/yield promoted into accepted facts. Later report handling untested. |
| B13: clickwrap | Pass, extraction exclusion only | Isolated terms screen excluded and missing-market-data gap saved. Age/terms not promoted into facts. Later report handling untested. |

Overall, three narrow cases pass, two are partial and one fails because its
source section was not reached. No full demo-readiness pass is claimed. The
real label-only correction and six-quantity row improvements worked, but they
do not compensate for missing essential coverage and token routing.

## Reproducibility and boundaries

- Trial runner: `scripts/run_extraction_phase_d.py`. It refuses to repeat an
  existing recorded trial. No extra provider smoke test preceded the trial.
- The four full byte-identical snapshots are the fees page, April 28 announcement,
  token page and token trading clickwrap from the frozen Phase B fixture. The
  evaluator's annotations/expected answers are never sent to the model.
- `tmp/phase-d-live/run.json` records each dispatch, timeout, prompt size, duration,
  source hashes, fixture hash, application Python file hashes and preservation.
- Every returned response and exact prompt is saved under the same audit folder.
  Model metadata is read only from Hermes sessions matching this test workspace.
- Existing configuration: Hermes / `openai-codex` / `gpt-5.6-sol`, medium reasoning.
  No provider/model setting was changed. Session metadata confirms the model.
- Six application provider dispatches maximum; 144,000 prompt characters; eight
  minutes for preparation. Failure and support-check calls count. Phase E's four
  calls are not available to extend this trial.
- Offline provenance checker passes: 14 cases, 14 blocks, seven snapshots and
  22 exact anchors. This is not a live model-quality score.

An initial setup attempt encountered the exclusively held dashboard lock while
hashing existing output. No provider call had been made. The runner was corrected
to record unreadable files explicitly and then started this single live trial.
The dashboard backend was left alone; the browser is unnecessary for Phase D.

## Observations

The first scope call timed out at 120 seconds. Scope retained all 18 blocks as
qualified/unresolved. Extraction then had only the protocol identity available;
the related token had not received its own identity in this fresh test workspace.

Four selected documents became five extraction batches: announcement; first fee
section; second fee section; token highlights; token methodology/rights. The
calculator and isolated clickwrap were excluded locally. The ordering is based
on source paths and batch sizes, not on the research questions' importance.

With one successful extraction and one support check per material batch, that
plan requires eleven calls including scope, before repairs or conflict checks.
The six-call stop prevents a runaway but does not make this plan fit its budget.
Navigation/context and per-proposal provenance also inflate prompt sizes.

The announcement generated eight claims, including material token rights and
purchase caveats but also several disclaimer points. Its support check corrected
the revenue question label without regenerating the claim. The fee extraction
included a six-quantity canonical SOL row, demonstrating that the previous
four-quantity proposal limit no longer prevents proposing that complete row.

The scope failure also leaked into repeated claim prose: fee proposals start
with "A source whose relationship to the core subject is unresolved". This
would burden the researcher even when useful source content is available.

## Required correction before continuing to report acceptance

1. Build a preparation plan that fits its budget before dispatch. Prioritize the
   overview, fee distinctions and token rights/methodology together; don't spend
   the early budget on every announcement caveat or every fee tier.
2. Reduce repeated prompt material and consolidate checks while retaining exact
   original passages and independent semantic decisions. Reserve enough calls
   and time to check proposed facts; avoid starting work that cannot be checked.
3. Resolve token identity from explicit source evidence within the bounded plan.
   A failed classifier must not turn all related-token research into protocol
   records. Keep uncertainty visible once, outside every claim's main wording.
4. Run another explicitly budgeted acceptance trial after those corrections.
   Do not silently repeat this trial or spend Phase E's allowance on extraction.

Runtime code was not altered during this acceptance test. Existing Phase C tests
remain prior offline evidence; they must not be presented as a live demo pass.
