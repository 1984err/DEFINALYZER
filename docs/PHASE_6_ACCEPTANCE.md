# Phase 6 acceptance

Acceptance completed on 2026-09-07. All live development runs used isolated workspaces
under `tmp/phase6-*`. User research, including the deferred NEAR rerun, is outside
this acceptance run. Phase 7 is not authorized by Phase 6.

## What the run found and changed

- **Missing original text:** Crawl4AI's text-only conversion discarded text after
  inline emphasis. This removed Aave liquidation conditions and governance
  timelines. Documentation collection now preserves HTML text around formatting,
  retains short passages, and bypasses the crawler's hidden converted-page cache.
  The application's explicit saved-file skip/refresh policy still controls reuse.
  A regression uses the real HTML scraper and Markdown generator, without network
  access, to check threshold conditions, timelocks and negation.
- **Citation formatting:** readable Markdown quotes now resolve deterministically
  to unique, exact spans in the original source. Saved evidence retains the
  original Markdown and hashes. Paraphrases, changed negation and ambiguous
  matches remain invalid. Scope, facts and report support use the same resolver.
  A separate regression covers bold labels inside bulleted lists: the list marker
  must not consume the emphasis delimiter or its following conditions.
- **Identity:** token research obtains names and symbols from its saved asset
  identity, including projects whose catalog identity differs from the older
  project manifest. A protocol name is not automatically a token alias.
- **Unnecessary repairs:** extraction instructions distinguish spelled-out
  numbers and years from typed quantities, allow supported facts without a
  matching profile question, and reserve gaps for uncaptured source material.
  Report prompts avoid repeated metadata while retaining complete original
  passages. Identical report limitations collapse into one issue.
  Original-source review runs before conclusion review. The latter evaluates the
  checked narrative rather than a shortened fact index that may omit supported
  detail. Malformed review responses retry their check without rewriting prose;
  counterevidence against unsupported claims remains actionable. Supported
  assertions still require their own linked originals.
  Valid support from an unlinked original triggers a paragraph citation repair;
  it is not mistaken for malformed checker output and retried without a fix.
- **Recovery:** provider subprocesses run in a Windows Job Object. Timeout,
  interruption and owner-process exit clean up their descendants. Jobs returning
  nonzero exit codes or an unresolved workflow result have a terminal
  `needs_attention` status. Keyboard interruption is durable immediately.
  Checkpoint writes also retry brief Windows replacement locks within a fixed
  allowance, preserving the previous file on failure and never repeating an AI
  request merely because a checkpoint destination was temporarily locked.
- **Explicit retries:** Retry unfinished research preserves accepted claims and
  original attempt files. Only exhausted, unsuccessful batches get a new bounded
  attempt set. Ordinary runs reuse completed work. Retry requests bind the saved
  collection state so a stale request cannot silently add another allowance.

## Evaluation corpus

These are narrow documentation samples, not comprehensive assessments of the
named chains, protocols or assets. They do not establish deployed behavior or
current measurements.

| Subject | Original page | Material checks |
|---|---|---|
| Ethereum, chain | [Proof of stake](https://ethereum.org/developers/docs/consensus-mechanisms/pos/) | Checkpoint justification/finalization; two-thirds stake; one-third preventing finality; inactivity leak after more than four epochs; distinguish fork choice and reversal from finality. Preserve the source's separate 66% wording rather than silently reconciling it. |
| Aave, protocol | [Liquidations](https://aave.com/help/borrowing/liquidations) | Eligibility below health factor 1; the 50% versus 100% conditions including health factor 0.95 and $2,000 balances; the $1,000 remaining collateral/debt condition; no universally safe health factor. |
| Aave Governance Token / AAVE | [Voting](https://aave.com/help/governance/voting) | Nonbinding Snapshot votes; voting from held/delegated assets on Ethereum mainnet; quorum and majority; activation delay; separate Short/Long Executor voting and execution delays. Do not convert governance rights into fee entitlement. |
| Cedar, held-out fictional mixed corpus | `tests/fixtures/phase6/mixed.md`, with `annotations.json` | Separate Cedar, Transit Bridge, Luma Protocol and LUMA; preserve all eleven annotated checks, including version-specific delays, delegation, fee boundaries and recovery/pause restrictions. |

The held-out run retained eight supported claims covering all eleven annotated
checks. Its focused report passed original-source and conclusion review after
repair. Every assertion can be traced to the frozen original evidence. Release
1 and release 2 restrictions remain distinct facts; they are not treated as
contradictory measurements of one deployment.

## Collector and lifecycle checks

The configured Ethereum, Arbitrum and Base RPC endpoints passed fresh read-only
chain-ID validation, block-height retrieval and retrieval of that exact numbered
block. Raw responses, chain identity and collection timestamps are retained in
`tmp/phase6-collector.json`; endpoint credentials are not included. No transactions
were signed or sent. Existing collector tests cover wrong-chain rejection and
transport/error handling. This does not introduce the Phase 7 observation adapter.

Windows regression tests exercise both a timed-out provider with a child holding
stdout open and a forcibly terminated provider owner. The descendant heartbeat
stops in both cases. Live acceptance also encountered the deliberately shorter
120-second test timeout; this does not change the user's configured provider
timeout. Interrupted reservations and failed runs remain in the acceptance history.

## Evidence and measurements

- `tmp/phase6-workspace/acceptance-metrics.json`: actual provider calls, input and
  output characters, elapsed time, errors, retained facts and unchanged reuse.
- `tmp/phase6-report-recheck.json`: separate Ethereum full-report recheck following
  the report prompt fix.
- `tmp/phase6-heldout/metrics.json`: separate held-out classification, extraction
  and report calls, including failed attempts.
- `tmp/phase6-recrawl.json`: recollection of the Aave samples after the source fix.
- `tmp/phase6-fresh-chain.json`: a fresh Ethereum crawl retained all five critical
  passage checks after the same collector fix.
- `tmp/phase6-final-reports.json`: the final Aave/AAVE report checks after diagnosed
  quote-format and review-order fixes.
- `tmp/phase6-dashboard-provider.json`: live dashboard repair calls.
- `tmp/phase6-aave-recovery.json`: earlier rechecks, including failed attempts.
- `tmp/phase6-link-repair.json`: bounded Aave revision after diagnosing missing
  citation repair routing.
- `tmp/phase6-audit.json`: report status, source integrity, assertion counts,
  prose length and aggregate measurements.
- `tmp/phase6-verified-tests-final.txt`, `tmp/phase6-js-tests.txt`: regression results.
- `tmp/phase6-preservation.json`: original-output SHA-256 comparisons.

Input characters are measured workload, not billed tokens or a dollar-cost
estimate. No researcher had to classify pages, approve individual facts or edit
source claims during these runs. Developer intervention was needed to fix the
issues above and restart the affected acceptance attempts; those costs remain
in the measurements rather than being omitted from the results.

The initial real-case allowance was 60 calls, extended to 80 while correcting
observed failures. The held-out allowance was 14 calls and the separate full-report
recheck allowance nine. These are development acceptance limits, not automatic
per-project production budgets. The dashboard repair had nine calls available;
an earlier Aave recheck had eighteen. After diagnosing the bold-list resolver and
review-order failures, four fresh reports received a separate 24-call allowance
with a 180-second test timeout. The user's provider settings were not changed.
The final missing-citation recovery check had a separate nine-call allowance.

One full-suite run encountered a Windows localhost connection abort in an
existing origin-rejection HTTP test. After closing the temporary dashboard
browser and server, the full rerun passed. The security rule was unchanged.

The preservation audit compared **all 1,663 pre-Phase-6 output files**, plus the
original **1,640-file Phase 2 baseline**. No file was missing or changed.

## Remaining boundaries

This small corpus provides regression evidence, not a general accuracy guarantee.
Source fidelity and checked assertions do not guarantee that every material claim
in a large corpus is captured. Omitted evidence and incomplete comparisons stay
visible. Old saved source pages are not silently recollected by this update;
they receive the collection fixes when explicitly refreshed. NEAR remains deferred.

The saved real-case scope runs still contain conservatively unresolved blocks
(Ethereum 11 of 16, Aave 4 of 6, AAVE 8 of 8), including rejected applicability
labels. Those blocks were retained for qualified extraction, not discarded or
silently classified as core. The downstream accepted claims passed their own
subject and original-source checks. These samples therefore demonstrate safe
retention and checked extraction, not uniformly successful initial classification.
Model retries also remain a real latency cost; passing this development corpus
does not imply that every future report will pass on its first attempt.

## Final results

All seven selected reports passed both original-source and conclusion review.
They remain drafts ready for human review, not finalized publications. A partial
readiness assessment describes limited coverage; it is separate from whether the
claims that the report actually makes passed their checks.

| Report | Checked paragraphs | Prose words, including headings | Coverage readiness |
|---|---:|---:|---|
| Ethereum focused question | 4 | 362 | Partial |
| Ethereum full review, revision 1 | 5 | 500 | Partial |
| Aave liquidation question | 5 | 391 | Ready |
| Aave full review, revision 1 | 8 | 773 | Partial |
| AAVE governance question | 5 | 475 | Ready |
| AAVE full review | 6 | 526 | Partial |
| Cedar held-out question | 4 | 373 | Ready |

Every frozen report bundle and original-source link passed integrity checks.
All 37 accepted real-case facts (22 Ethereum, eight Aave, seven AAVE) resolve to
their original references. Each immediate unchanged extraction reused saved work
with zero additional provider calls. Manual review checked the critical material
conditions listed in the corpus table; it also found that the focused AAVE report
repeats its undated-documentation qualification more than necessary. That is a
remaining prose-quality limitation, not a reason to present the timelines as
verified current settings.

Regression validation: **505 Python tests ran, 504 passed and one was skipped;
21 dashboard JavaScript tests passed.** The final diff whitespace check passed.
The preservation audit again found all 1,663 pre-Phase-6 files unchanged, including
the 1,640-file Phase 2 baseline. The isolated dashboard browser and server were
closed after UI acceptance; live provider runners exited successfully.

Across the retained development runs, **139 provider invocations** were recorded:
133 completed, two failed and four were interrupted while loading diagnosed fixes.
They supplied **2,030,100 input characters** and recorded **6,946.19 seconds** of
summed call duration. Interrupted calls may lack a complete duration; concurrent
calls overlap, so this is neither wall-clock time nor a billing measurement.
Completed provider calls include outputs that subsequently failed research or
report validation. Earlier unsuccessful reports and checkpoints remain retained.

The final four Aave/AAVE report cases used 22 calls including the explicit Aave
citation repair: three for the Aave question, eight across the Aave full-review
attempt and repair, seven for the AAVE question, and four for the AAVE full review.
These supplied 318,889 input characters and recorded 1,610.03 seconds of summed
call duration. The focused Aave report passed on its first attempt; the other
cases needed bounded repairs or a retried check. These small-sample results should
not be extrapolated as a full-corpus cost estimate.

Phase 6 requires no manual dashboard cleanup or NEAR rerun. Restart the actual
dashboard when ready to load the code; existing saved research stays unchanged.
Phase 7, including selection of the first additional data adapter, awaits a new
user instruction.
