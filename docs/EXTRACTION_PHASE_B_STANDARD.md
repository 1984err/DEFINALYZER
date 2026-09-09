# Phase B: resume demo acceptance standard

Date: 2026-09-07. Status: standard and frozen evaluation sample complete.
Phase C implementation and live acceptance have not started.

## Product target

The immediate goal is a credible five-minute resume demonstration of DEFINALYZER:
turn saved official documentation into useful research, explain a protocol and
its token separately, and produce a short answer with inspectable sources.
The demo should make the engineering visible through a smooth workflow, clear
evidence and bounded operations. Broad chain coverage and exhaustive research
are later goals.

Use Pump.fun / $PUMP as the first demonstration because the saved corpus already
exposes the problems we need to fix. The prepared demo should clearly identify its
selected saved documents and their dates. These historical snapshots cannot certify
current fees, prices, live revenue or on-chain execution.

Preparation happens before the presentation. A prepared demo must still be the
output of the real application pipeline. Fixture expectations are test annotations,
not approved facts to inject into the app or canned answers to present as generated.

## Five-minute demonstration

| Step | Visible result | Acceptance condition |
| --- | --- | --- |
| Open Pump.fun | Concise overview and fees from saved documentation | Useful content appears immediately; no surprise preparation job |
| Open $PUMP under Tokens | Token rights and linked protocol economics | No empty duplicate research page; protocol revenue does not become holder income |
| Open a brief review | A short, readable research report | At most 500 words of main narrative; supported content survives localized gaps |
| Ask “Does holding $PUMP entitle me to Pump.fun revenue?” | Direct answer, explanation and source links | At most 180 words; uses prepared research without re-extraction |
| Open a citation | Original passage with source and date/context | Claim, number and entity match the passage |
| Export the brief review | A shareable report from the same saved version | Export opens, preserves the report and its references, and makes no new provider calls |
| Show a limitation or Stop control | A clear, manageable state | Current price is unavailable from these sources; an operation can be stopped |

The brief review should cover what Pump.fun does, who receives fees, what the docs
say about $PUMP rights and purchases, and up to three material limitations. Use a
small fee table where helpful. Source details can expand separately. Do not fill
the overview with SDK setup, cookie banners, legal boilerplate or repeated caveats.
The specific token-rights restriction is material and must remain visible.

Proposed brief-review prompt: “Explain Pump.fun's documented fee model and its
relationship to $PUMP. Distinguish protocol revenue, purchases/burns, and token
holder rights. Highlight the important limits of these saved sources.”

Boundary question: “What is $PUMP's price right now?” The correct result is a short
statement that current market data is not available in these saved sources. Do not
turn the illustrative calculator into live metrics, launch a crawl, or refuse all
other research because that one input is missing.

## What counts as useful extraction

A useful research item preserves the answer and the conditions that change its
meaning: entity, mechanism, fee recipients, numeric units, pool type, dates and
exceptions. It keeps a source passage that can be opened directly. It need not
copy the source wording, match a particular JSON layout or fit a profile question
perfectly. Equivalent wording and a compact table are acceptable.

Coverage is measured against the frozen expected meanings below, not the number
of claims generated. A known material fact omitted because of a parser error is a
failure. An explicit unknown for information absent from the input is a correct
outcome. Duplicate paraphrases do not count as additional coverage.

Separate these outcomes in the implementation:

| Outcome | Required handling |
| --- | --- |
| Supported useful claim | Save once with its conditions and provenance |
| Supported claim, wrong question label | Correct/drop the label without regenerating the claim |
| Supported meaning, malformed quote | Repair the reference to original text; preserve claim identity |
| Wrong meaning or attribution | Reject or perform one targeted repair with the original evidence |
| Source wording is ambiguous | Keep a localized uncertainty; do not silently resolve it |
| Needed input was not captured | Name the specific gap; keep other supported answers usable |
| Boilerplate or off-topic implementation detail | Retain source access, omit it from the general summary |

Reports can use accepted claims and their stored original passages. A source-wide
re-reading, recrawl or extraction run is not part of a question/report request.
Looking up the specific saved passage behind a claim remains legitimate support
checking. The user should not have to inspect every claim to obtain a useful answer.

## Frozen test set

`tests/fixtures/extraction_demo/cases.json` contains 14 annotated cases referencing
14 source blocks from seven byte-identical snapshots. Six cases define the demo's
content; eight protect the fixes and existing checks. All come from already saved
Pump documents. No web retrieval or provider generation was used in Phase B.

| Case | Acceptance focus | Use |
| --- | --- | --- |
| B01 | Creation/graduation fees, fee recipients and pool distinctions | Demo |
| B02 | Correct 0.1% mobile exception and conditional wording | Demo |
| B03 | Preserve six quantities in a canonical SOL fee tier | Demo |
| B04 | Token rights, revenue allocation and source-specific date exceptions | Demo |
| B05 | Hypothetical calculator values never become current metrics | Demo |
| B06 | Correct a question label without full claim repair | Offline regression |
| B07 | SDK spelling/context without creating another protocol/token | Offline regression |
| B08 | Resolve “both programs” through the cited introduction | Offline regression |
| B09 | Reject the real wrapped-account/raw-IDL meaning error | Offline regression |
| B10 | Preserve one research item through duplicate repair attempts | Offline regression |
| B11 | Repair a noncontiguous quote without losing the valid claim | Offline regression |
| B12 | Keep a source double negative as localized ambiguity | Offline regression |
| B13 | Clickwrap does not count as token metrics or headline research | Demo |
| B14 | Image-only table stays a specific input gap | Offline regression |

Each case records expected meanings, forbidden conclusions, required behavior,
exact source anchors and the Phase A observation. These are reviewed annotations,
not output from a new live trial. The seven complete snapshots exist to verify
context; only the selected blocks needed by each case belong in its model input.
Do not send all snapshots or the expected answers to the extraction model.

One integrity command works without the user workspace, credentials or the app:

```powershell
python scripts/check_extraction_demo_fixture.py
```

It checks source bytes, exact line ranges, block hashes and quote anchors. Its
success proves fixture integrity only; it does not establish model accuracy or
application readiness.

## Pass/fail gates for C–E

For this deliberately small demo set, all six demo cases must satisfy every
expected meaning with zero forbidden conclusions. Meaning can be distributed
across research items; a brief report need not repeat every detailed table value.
All eight regression cases must pass focused offline tests in Phase C. SDK cases
do not require more live calls or a wider demo corpus.

Report acceptance is separate: the main narrative has at most 500 words, the
question answer at most 180, and all material factual claims resolve to their
original support. There must be no duplicate research point, transferred token
entitlement, invented current metric or global refusal caused by a localized gap.
One short disclosure of saved-source scope is sufficient.

Also smoke-check the surrounding tool in Phase E: project/source selection leads
to the intended bounded preparation, token navigation reaches the rich token
research, Refresh token supply remains visible in the token context, saved work
survives reopening/restarting, and one existing export format opens correctly.
Capture source collection/preparation during rehearsal so the demo can show the
real input-to-output flow without waiting for collection during the presentation.
Use the existing collection fixture/tests where possible; a fresh crawl or market
data refresh is not required by this acceptance sample. Broken navigation, lost
research, an unusable export or an operation that cannot be stopped blocks demo
readiness even if the extraction cases pass.

Record exact source/fixture revision, application revision, model/provider,
call count including failures/retries, prompt characters, elapsed time, expected
meanings captured/missed, forbidden conclusions, broken references and actual
screens/report outputs. Evaluate generated answers against meanings, not an exact
wording match. Save a failed run too; do not silently repeat until it looks good.

| Operation | Proposed demo acceptance budget |
| --- | --- |
| Phase D selected-source preparation | At most 6 provider calls total, 144,000 input characters and 8 minutes elapsed |
| Phase E one brief report plus one supported question | At most 4 additional provider calls total, 96,000 input characters and 4 minutes elapsed |
| Total D + E | At most 10 calls and 240,000 input characters, including scope, checks, repairs and failures |
| Reopen unchanged research, report or citation | Zero provider calls |
| Current-price question with a known missing input | No extraction/crawl; preferably a local response with zero provider calls |
| Stop | Show Stopping promptly, dispatch no further calls, retain completed work, then show Stopped |

These are proposed ceilings to validate, not measured performance or promises.
Stop when any budget is reached; do not borrow from E to conceal D overruns or
automatically extend the run. Reserve budget before dispatch, including any
conflict checks. Keep a finite provider timeout within the remaining time budget.
Cancellation must be checked at every dispatch boundary. A cancelled or
budget-limited run must not claim full preparation.

For Stop, reuse the existing deterministic cancellation tests and a local slow
provider fixture; spending a live model call merely to demonstrate cancellation
is unnecessary. Validate app state as well as process exit.

## Keep Phase C small enough for the demo

Implement numeric parsing and table handling, separate metadata/citation repair,
repair identity/deduplication, bounded preparation and a usable publication path
for the explicitly selected demo documents. Accepted research may become usable
once that declared selection is complete, without waiting on unrelated SDK docs.
If an incomplete run exposes accepted work, label its coverage accurately and
retain unresolved work for an explicit later action.

Use controlled source context and documented relationships for the observed
subject failures. Avoid redesigning the entire entity model for this demo. Keep
existing protocol/token navigation, source lineage, report storage and Stop
controls unless a failing acceptance case requires a targeted fix. Preserve old
research and invalidate changed extraction checkpoints by version rather than
silently treating old and new outputs as equivalent.

Defer full Pump/NEAR reruns, a general entity-resolution system, exhaustive SDK
research, OCR, additional data connectors and broad chain/token benchmarks.
Phase 7 remains paused. Once D/E pass, polish the README, screenshots and short
demo narrative around the actual demonstrated capabilities as a separately
requested packaging step; this is not a prerequisite for extraction repair.

## Phase B outcome

The standard, frozen source sample and offline integrity checker are complete.
No runtime code, saved research or provider settings changed. No live acceptance
run occurred, and no current application pass rate is claimed. Phase C is next
at Extra high effort, constrained to these demo requirements; it has not started.
