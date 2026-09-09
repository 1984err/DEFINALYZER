# Source-supported research (Phase 4)

Phase 6 adds **Retry unfinished research** to the project scope card when current
research contains exhausted failed batches. It retains checked findings and old
attempts, retries only unfinished batches, and allows at most two repairs in the
new attempt set. Refreshing the page does not add an allowance. Source, scope or
extraction-rule changes require normal analysis before a failed-work retry.

New research runs save structured claims before writing pages. Each claim must
resolve to an exact passage in the saved documentation and pass a separate AI
support check. The check asks whether the source actually supports that claim,
including its subject and conditions. It does not verify the source against the
real world.

## Using it

The existing **Analyze project** and research extraction actions use this flow
after preparing source scope. No new setup checklist is required. Installing the
code does not rerun research; restart the dashboard to load the new backend and UI.
The user has deferred the full NEAR rerun.

Research pages group claims by their named subject. **Source** opens the exact
saved passage, its file and lines, with surrounding context available underneath.
Related-system claims cannot fill the main subject's coverage questions.
Unanswered questions and unavailable current measurements remain explicit; a gap
is never presented as proof that a feature does not exist.

If an existing page predates this writer or has been edited, its bytes are kept.
A supported version becomes the topic's default reader page; **Original notes**
opens the preserved page and **Compare changes** shows a readable text diff.
There is one generated navigation entry per topic. Edited proposed pages are
also preserved, rather than silently replaced. Repeated unchanged runs reuse
the same supported page. These are portable Markdown files, not a database.

Token and coin navigation still opens the existing populated asset context.
The selected asset's supply action stays above that reader. This phase does not
rewrite asset identities, refresh live supply, or migrate historical token notes.

## Data and checks

`research_facts.py` owns documented-claim proposals, accepted revisions, topic
views and source resolution. `research_profiles.py` holds versioned chain,
protocol and token/coin research questions and separate observation requirements.

An accepted revision records its subject ID, predicate, statement, applicability,
typed documented quantities, question tags, original evidence, independent check,
schema version, recording time, content ID and superseded revisions. Its recording
time is not the statement's effective date. This AI path cannot create
`observed_value` or `analyst_statement` records.

Evidence resolves through the Phase 3 snapshot store. Resolution checks snapshot
bytes, full block context, exact quote and line range. Numeric literals must occur
in the quoted evidence; typed values and units must agree with their saved literal.
Subject IDs and coverage questions must belong to the supplied context. Declared
applicability must occur in the original context. A separate inference-only
provider call checks subject attribution, conditions, negation, quantities,
applicability and question relevance against original blocks.

The provider returns supported, needs qualification, contradicted or unclear.
Only supported proposals render as ordinary claims. Failed proposals are repaired
at most twice, with targeted feedback and an explicit repair ID. Dropped repairs
remain gaps. Attempts are reserved before calls, so interruption does not refill
their allowance. Successful proposals survive other failures in the batch.

Same-scope incompatible numeric values are conservatively flagged. Bounded
separate comparisons also check qualitative disagreement against original context.
Conflicting statements and both source references remain available; the system
does not choose which source is true. Different subjects, periods, versions or
environments are not automatically combined. Oversized or failed conflict checks
produce an unassessed conflict gap, not an assertion that no conflict exists.

Coverage records evidence availability, question references, conflict state,
documented periods, freshness, relevance and required observations separately.
Dated documentation remains dated documentation; undated claims have unknown
freshness. Documentation alone never establishes current supply, revenue,
liquidity, validator concentration or other measurements. No completeness or
confidence percentage is invented.

## Storage, refresh and compatibility

```text
projects/<slug>/scope/snapshots/<sha256>.md  immutable original source bytes
projects/<slug>/facts/
  current.json                            committed fact and coverage pointer
  history/<revision>.json                 prior committed fact sets
  revisions/<revision>.json               immutable individual claims
  batches/<input-fingerprint>/             prompts, responses, attempts, gaps
  conflict-checks/<fingerprint>/           bounded comparison records
  pages.json                              generated hashes and navigation views
  page-history/<sha256>.md                replaced generated versions
```

Per-project writer locks serialize commits. Source hashes and scope are checked
again before committing facts. Readers resolve immutable revisions. Rendering
verifies references again; tampered records or snapshots fail closed.

Batches stay within source files so adding another source does not shift all
later batches. The extraction/support prompt contract, scope metadata and content
participate in caching. Each changed batch is reconsidered, including newly added
contradictory material. Unaffected facts retain their revisions and unaffected
topic fingerprints remain stable. Generated pages have one writer: verification
planning keeps its links in its own page instead of modifying fact views or
preserved original notes.

Project Q&A can retrieve immutable original passages and treats generated views
as retrieval aids, not extra corroboration. Active research readers and new
legacy report retrieval prefer the active supported view over its preserved
original. Existing V1 report packages, hashes, approvals and exports are not
rewritten or relabelled. Full V2 report contracts and report UX remain Phase 5.
Legacy direct extraction on a workspace without source scope retains its old
compatibility path; normal application extraction prepares scope automatically.

## Bounds and remaining acceptance work

Prompts are capped at 24,000 characters; source batches at 9,000 serialized
characters; proposals at eight per attempt. Each source batch has an initial
attempt and at most two repairs. Support checks split to fit the prompt limit.
The conservative maximum is 27 extraction/support calls per batch (normally two
without repairs), plus one conflict call per comparable subject/topic/scope group.
The plan and batch progress are logged. Provider failures and exhausted attempts
are cached for that input fingerprint; ordinary resume does not silently grant
another repair budget. Explicit retry/budget-extension UX and broad workload
tuning belong to Phase 6. No automatic retry loop is added here.

Large blocks/groups and unrecognized subjects may leave disclosed gaps. The
subject map currently uses explicit scope names, with provisional IDs for related
documented systems; it does not infer global product ownership. Broader subprofile
selection, freshness policies for live measurements and additional adapters remain
future work. Semantic checking still depends on an AI model and cannot guarantee
perfect extraction or detect every contradiction.

Validation on 2026-09-07: 465 Python tests run, 464 passed and one skipped; 13
JavaScript tests passed. The isolated browser fixture exercised source context,
comparison, one-topic navigation, populated token context and its supply button.
A bounded live Hermes sample produced three correctly attributed claims from
synthetic chain/bridge documentation, using four calls and 33,980 input characters
in 65.4 seconds, including one targeted repair. This is a smoke test, not a full
corpus quality benchmark. All 1,640 original output files remain byte-identical.
