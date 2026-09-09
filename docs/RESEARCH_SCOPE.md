# Automatic research scope — Phase 3

Research scope separates the subject being studied from related products and
dependencies before generating new notes. Existing pages are not rewritten by a
scope job. The dashboard identifies pages that predate the current scope; Analyze
project regenerates stale notes using the new routing.

## Using it

- Analyze project prepares scope automatically before determining which notes
  need regeneration. Generate one page also prepares or reuses scope first.
- Project Controls → Research scope classifies saved sources without crawling,
  regenerating notes, fetching supplemental sources, or creating reports.
- The scope card shows Researching, Related systems, and Needs attention. Its
  expanded plan shows the classification budget and retained material passages.
- Adjust scope is optional. Select a page, relationship and reason, with optional
  version/network/environment corrections. This applies to that page's current
  blocks. Corrections persist when those blocks recur. Changed blocks that no
  longer match a correction are flagged instead of silently inheriting it.
- Continue classification explicitly grants additional calls. Ordinary repeated
  runs do not refill the budget for unchanged source inputs.

CLI equivalents:

```powershell
python -m definalyzer scope near --index-only
python -m definalyzer scope near
python -m definalyzer scope near --extend --call-budget 8
```

Index-only creates immutable snapshots and a provisional plan without AI. Its
unresolved labels are not a completed classification. No page-by-page approval
is required for ordinary analysis; unresolved attribution stays qualified.

## Stored data and routing

Each project has a `scope` directory containing content-addressed original source
bytes, versioned block indexes, classification checkpoints, an active scope
pointer, revision history, and versioned manual overrides. Blocks retain source
URL when supplied, original relative path, title, heading, snapshot hash, and
exact start/end lines. Snapshot capture is additive and never deletes the crawl.
Block identifiers use path, content and occurrence rather than line number, so
inserting an earlier section does not discard an unchanged block's correction.

Relationship (`core`, `related_product`, `dependency`, `out_of_scope`, `unresolved`)
and content role are independent. Applicability values require supporting source
quotes; unspecified versions, networks, environments and dates stay unknown.
Manual applicability corrections are explicitly marked as manual.

The provider sees bounded excerpts for routing, including beginning/end context
and material lines. It cannot browse or execute documentation instructions. Every
accepted decision cites exact supplied text and names supported by those quotes.
Malformed decisions, unsupported names and unsupported applicability remain
unresolved. Unknown blocks are not evidence against the subject.

Extraction receives full retained blocks with subject, relationship,
applicability and locator labels. Core material is retained; mixed-subject core
blocks and related products/dependencies receive qualified routing. Reference,
tutorial and administrative material without a resolved relationship or material
content stays stored for retrieval. A deterministic omission scan rescues passages
about custody, withdrawals, fees, authorities, upgrades, restrictions and other
material issues; security/governance/economics classifications also retain context.
Ledger reduction and final generation must preserve attribution.

Related-product and unresolved addresses do not become main-subject scanner
targets. Explicitly named native assets can still be read from their own
documented catalog sections.

Scope revisions participate in research dependency fingerprints. New, changed or
removed source documents invalidate the prior inputs, including documents that
previously stayed in reference storage. Extraction rejects changed source bytes
when the saved scope is stale. Generated note metadata records the scope revision.

## Collection and supplemental sources

Exact page URLs stay exact pages. A trailing-slash section stays within its URL
pattern and host. If ordinary docs-root discovery fails, fallback uses observed
same-host root navigation rather than silently crawling the entire domain.
The inferred fallback boundary is saved with the crawl. Reference/API pages may
be collected so material controls are not discarded before inspection. GitHub
imports retain the existing repository/ref boundary.

The previous Aave enrichment is isolated in `supplemental_sources.py` under an
explicit legacy registration. Its address-book and chain responses receive
immutable snapshots and source records. Scope classification does not select
projects for enrichment and never triggers these network calls.

## Budget and validation

The default cumulative classification limit is 32 calls, each at most 24,000
prompt characters. Failed/interrupted requests count toward the limit. Progress
and decisions are checkpointed after each call. A provider or response-format
failure stops additional calls in that run; retained blocks remain qualified.
Interrupted extensions resume against the existing grant. This budget covers classification,
not the subsequent extraction and report calls.

The saved NEAR benchmark contains 130 source files and 324 blocks. Bounded
classification excerpts planned 23 calls and roughly 0.53 million input
characters; this is a measured plan, not a cost or quality guarantee. The default
leaves headroom without authorizing indefinite retries.

A live four-block Hermes smoke check initially over-attributed Chain Signatures
to the base chain. The prompt was tightened to distinguish base protocol mechanics
from separately operated signing, bridge, solver and application systems. The
final smoke result classified the chain overview as core and Chain Signatures,
Intents and Omni Bridge as related systems, with source-backed names and unknown
applicability preserved. One intermediate response failed citation validation;
the production path retains such decisions as unresolved.

This is scope routing, not independently verified fact attribution. Phase 4 now
adds [enforced fact-to-source lineage](RESEARCH_FACTS.md). Full corpus regeneration
and report acceptance remain later work. These checks did not regenerate user notes.
