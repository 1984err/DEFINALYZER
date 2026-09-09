# Phase A: saved Pump extraction audit

Date: 2026-09-07. Status: diagnosis complete; implementation not started.

The saved run demonstrates fixable problems in validation, entity naming, repair
handling and work prioritization. It does not establish that the extraction model
is broadly incapable of extracting useful research. Correct information was
sometimes rejected by our code; some actual model mistakes were correctly caught.
Removing the checks wholesale would therefore be the wrong remedy.

## Scope and evidence

Read the existing Pump scope, immutable source snapshots, extraction/check prompts,
saved responses and batch checkpoints. No Hermes/provider calls, fresh crawl,
research rerun, application-code changes or changes to saved research were made.
Pump remains cancelled; Phase 7 and the NEAR rerun remain deferred.

Reproduction scripts:

- `tmp/pump_phase_a_audit.py`: inventory, prompt/response accounting and resolution
  of every accepted claim's original source reference.
- `tmp/pump_phase_a_replay.py`: replay seven saved numerical validation failures
  without a provider. All seven failures reproduced. All 126 scope/checkpoint
  files had identical SHA-256 hashes before and after that replay.
- `tmp/pump-phase-a/summary.json`, `calls.json`, `feedback.json`, `accepted.json`,
  `proposals.json`, `checks.json`, `offline-replay.json`: detailed audit evidence.
  Batch numbers below map to exact checkpoint directories and source block IDs in
  `summary.json`. Feedback entries preserve the actual prompt/state location.

These are local audit artifacts, not regenerated project research.

## What the stopped run actually did

| Measure | Observed value |
| --- | ---: |
| Saved source pages / source blocks | 22 / 167 |
| Scope calls recorded | 8 |
| Planned fact batches | 35 |
| Started / completed fact batches | 10 / 9 |
| Fact prompt records / saved responses | 45 / 44 |
| Extraction / support-check prompt records | 22 / 23 |
| Calls in repair rounds | 24 of 45 (53%) |
| Fact prompt input characters | 741,047 |
| Accepted claims in checkpoints | 63 |
| Accepted claims with primary Pump.fun subject ID | 19 |
| Accepted claims with broken original references | 0 |

There are 53 recorded/reserved invocations including scope, with one fact response
missing at cancellation. This is not an exact provider billing count. The earlier
945-call figure was a theoretical bound, not what actually ran. Prompt characters
are not tokens or dollars. Repeated repair calls are not all unnecessary calls.

Saved fact prompt-to-response modification-time intervals total approximately
46.1 minutes. They are a timing proxy, not precise provider latency. The job's
recorded start-to-cancellation interval was 72 minutes 55 seconds; that includes
scope preparation and other work.

## Confirmed causes

### 1. A numeric parser bug rejects a correct fee

`research_facts.py:27` and `_number_set` parse `.1%` as `1%`, while `0.1%` is
parsed correctly. Batch 3 quotes the saved fee page's additional mobile fee of up
to `.1%`. The extractor preserved the value correctly on all three attempts.
Validation rejected it three times as a typed-value mismatch.

The offline replay confirms both the parser defect and the actual saved
rejections. This also weakens the numeric comparison guard: `.1%` and `1%` appear
equal to it. No published incorrect claim has been established by this audit.

### 2. Undocumented output limits reject useful table extraction

`validate_proposal` allows only four typed quantities per claim. The extraction
prompt does not explain that limit, and rejection says only “Invalid typed
quantities.” Batch 2 has four such rejection events.

One example is a single SOL fee tier: two market-cap bounds plus creator,
protocol, LP and total fees require six quantities. Those values appear in the
saved source row. The extractor also attempted overly large multi-row summaries;
those should be represented or split deliberately, with an actionable contract.
Repeated generation cannot reliably repair an undisclosed constraint.

### 3. Correct statements are regenerated to fix their question labels

Five of the 13 saved `needs_qualification` decisions explicitly say the statement
is supported and both subject/context checks pass, but one question ID is wrong.
Examples include the documented revenue allocation and market-cap calculations.

The batch loop puts these into the same extraction-and-check repair path used for
incorrect claims. Repairing a classification label should not require rewriting
and rechecking the complete economic statement and source batch.

### 4. Subject naming and local context are too brittle

Scope retained 124 of 167 blocks as unresolved: 83 after validation failures and
41 with provider-classified unresolved status. The 83 failures comprise 31
subject-name, 37 applicability, 14 quote-match and one missing-subject/evidence
failure. Raw scope responses were not retained, so these counts do not prove all
83 were false rejections.

The subsequent fact stage had ten subject-absence rejection events. Concrete
examples include `pump_rust_client` versus the documented `pump-rust-client`
package spelling, and a section describing “both programs” whose identities are
in the preceding introduction.

The subject catalog contains 63 IDs, including Pump, Pump.fun, Pump Program,
program names, functions and SDK namespaces. The 63 accepted checkpoint claims
are spread across ten subjects; only 19 use the primary ID. This is a usability
and attribution concern, not proof that the other 44 are wrong. PumpSwap and
$PUMP must retain their actual boundaries; aliases, programs, functions and
products need explicit relationships rather than indiscriminate merging.

### 5. Repair output can duplicate already accepted knowledge

Batch 8 produced six rejections for replacements lacking the required `repair_of`
link. Those new candidates themselves entered later repair feedback. Its final
checkpoint contains 12 accepted statements, including repeated BuyV2 account-order
and wrapped-account guidance, sometimes under different subjects.

The loop appends accepted facts and does not perform semantic deduplication.
Repairs need to stay attached to the affected claim, preserve accepted work and
avoid adding alternate wording as new research.

### 6. The run optimizes for processing documents rather than useful coverage

`_batch_blocks` traverses the scoped source sequence, grouping by file and a
9,000-character source allowance. Extraction is capped at eight proposed facts
per attempt. The full profile question catalog and subject payload are repeatedly
sent through extraction and checking; across the saved fact prompts these two
components alone total 147,184 characters.

There is no practical whole-run fact-call budget comparable to the scope budget.
Batch-level bounds still permit a long project-wide operation. Conflict checks
and publication follow the source-batch loop and could add further work.

Two developer integration documents (batches 7 and 8) consumed 14 calls and about
17.5 minutes of the saved response intervals before the run reached later core
program documents. This material can matter for technical research, but should
not automatically receive that priority for every general review.

The saved token trading page supplied clickwrap material rather than market data;
its four accepted claims include age/terms and generic price-risk language. The
extractor therefore spent effort on low-value material for a protocol review.
The fee-program document also references a fee-tier image: image contents are not
present in its Markdown text. More checking cannot recover information that was
never captured as readable input.

There is no `facts/current.json` for this run. The 63 accepted checkpoint claims
are retained, but publication occurs after the whole loop and subsequent work.
That explains why lengthy preparation did not yet yield usable prepared research.

## Checks that were useful

Do not interpret every rejection as a validator fault. The saved evidence includes:

- An actual meaning error: a proposal said the SDK's wrapped state re-exports
  shared the raw IDL type's legacy-account failure. The source distinguishes them:
  the wrappers zero-pad older accounts. The support check correctly rejected it.
- An imprecise fee-tier algorithm description that did not preserve the code's
  specific threshold comparison.
- A source disclaimer containing a double negative. The extractor silently
  normalized it; the checker appropriately identified the unresolved ambiguity.
- A quote assembled from separated heading/bullets as though contiguous. Its
  underlying claim may be correct, but its citation still needs repair.

All accepted original references resolve against immutable bytes. This establishes
traceability, not completeness or independent real-world verification. Selected
accepted statements about fees, token-rights restrictions and SDK behavior were
also inspected against their supplied passages; this was not an exhaustive
semantic certification of all 63 claims.

## Decisions for the next phases

Phase A is complete. The next step is Phase B at **High** effort: define a small,
explicit evaluation sample from these saved sources before changing extraction.
It should include leading-decimal fees, fee tables, token/protocol boundaries,
cross-section references, aliases, genuine meaning errors, source ambiguity,
duplicates, boilerplate and image-only information. Record which useful facts
should survive, which claims must fail and which gaps must remain visible.

Phase C (**Extra high**) should implement fixes against that standard: numeric
parsing; a consistent table/quantity contract; separate metadata and citation
repair from claim repair; controlled entity/context handling; bounded targeted
repairs; deduplication; relevance and whole-run budgets. Decide explicitly how
partially completed but accepted research becomes usable without implying full
coverage. Preserve immutable provenance and genuine semantic checks.

Phase D (**High**) is a bounded live sample. Phase E (**High**) checks that reports
reuse saved research and produce concise useful answers without repeating a full
corpus extraction. The proposed live allowance is ten Hermes calls total across
D/E, subject to authorization at that stage. No full Pump or NEAR rerun is needed
to begin B or C. None of B–E has been started by this audit.

Remaining uncertainty: full-corpus recall, current website coverage, actual token
usage, scope model's discarded raw responses and how much time each proposed fix
will save. Measure these with the evaluation sample; do not claim a speedup or
complete extraction before testing it.
