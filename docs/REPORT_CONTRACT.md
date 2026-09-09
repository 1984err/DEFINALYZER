# Evidence-Backed Report Contract

This document defines the first report-system boundary. It does not generate a
report. Later phases must use this contract rather than inventing storage or
claim rules inside the terminal menu or dashboard.

## Product boundary

A DEFINALYZER report is an analyst product built from project research, saved
source passages, market snapshots, verification records, blockchain evidence,
and explicit analyst input. It is separate from the concise extraction pages.

The system may automate investigation and writing. It must not present source
agreement as independent verification, turn missing information into a fact,
or silently strengthen a conclusion. A recommendation is an interpretation,
not a verified fact. Finalization is an explicit human action.

The report stores concise, user-facing analytical rationale. It never requests
or stores hidden chain-of-thought, private model reasoning, provider secrets, or
wallet credentials.

## Report modes

- `question`: answers one required research question.
- `full_review`: evaluates the project broadly; a guiding question is optional.

Both modes use the same evidence and quality contracts. A full review is not a
license to copy every research page.

## Package layout

Each package is portable and belongs to exactly one project:

```text
output/vault/Reports/<Project>/<report-id>/
  report.json
  evidence.json
  claims.json
  draft.json                # validated generation bundle and recovery source
  Report.md                 # answer-first management report when support permits
  Analyst-Notes.md          # researcher-facing coverage and follow-up companion
  quality.json              # committed machine-readable quality review
  Quality.md                # readable quality findings
  approval.json             # exact human approval record for a final report
  Assets/                   # data-backed charts and illustrations
  Revisions/                # immutable report snapshots
  Exports/                  # immutable publication bundles by revision
```

`Report.md` is the editable management report. `Analyst-Notes.md` separately
records evidence gaps, weak elements, retrieval caveats, and recommended
follow-up. Its companion JSON files carry lifecycle state and the audit trail.
Report creation refuses to overwrite
an existing package. Deleting a project also deletes its report packages after
the existing exact-name confirmation.

## Lifecycle

1. `scoped`: the request and storage package exist.
2. `evidence_ready`: the bounded evidence package is complete enough to draft,
   or explicitly records why evidence is insufficient.
3. `draft`: an answer-first report and Analyst Notes have been generated, or
   insufficient evidence has produced Analyst Notes only.
4. `quality_reviewed`: citation, number, support, and conclusion-strength checks
   have run; this status does not prove source claims true.
5. `final`: a human explicitly finalized the report.

The quality status is tracked separately as `not_run`, `passed`, or
`issues_found`. A report cannot enter `quality_reviewed` or `final` without a
committed quality result.

Answer readiness is also separate from lifecycle status:

- `ready`: every selected assertion is directly supported by its saved evidence.
- `partial`: the report answers the supported scope, but one or more selected
  assertions is qualified, conflicted, or only partially supported.
- `insufficient`: no substantive management report is created; Analyst Notes
  identify the missing support and recommended follow-up.

## Evidence contract

Every evidence record has a stable `E-001` identifier, source type, path or
credential-free URL, precise heading/line/block locator, capture timestamp,
content SHA-256, and concise summary. An optional `as_of` timestamp records the
freshness of changing data.

Allowed source types are research, source documentation, verification,
blockchain evidence, market data, and analyst input. Evidence records show what
was consulted. They do not automatically confirm a claim.

## Assertion contract

Every material assertion has a stable `C-001` identifier and is classified as:

- `documented_fact`: faithfully represents a cited source.
- `collected_evidence`: reports a cited deterministic observation.
- `interpretation`: explains implications supported by cited evidence.
- `recommendation`: provides a qualified analytical recommendation supported
  by cited evidence.
- `uncertainty`: records an unresolved gap or conflict and may stand without an
evidence reference when the absence itself is the point.

### Phase 2 retrieval boundary

`definalyzer.report_evidence` prepares this ledger locally without calling an
AI provider, the web, an RPC, or CoinGecko. The saved corpus is the boundary:

- generated project research and only the token/coin pages registered to it
- the project's verification page
- saved Markdown documentation
- saved market snapshots
- saved blockchain evidence summaries and structured records

Question reports use lexical retrieval and return an insufficient-evidence
result rather than unrelated fallback text when nothing matches. Related risk
and limitation passages from matching files are included when space permits.
Full reviews interleave files and source types so one long manual cannot occupy
the entire allowance. Neither method proves completeness.

Limits apply to files scanned, bytes scanned, passage size, passage count, and
total characters. Tables and JSON snapshots are kept whole or explicitly
omitted; they are never clipped into misleading fragments. The ledger records
the source inventory, limits, omission counts, selected source types, missing
source types, and warnings. Source-coverage metadata remains a retrieval
qualification and never becomes evidence about the subject.

Evidence packages exclude unsafe filesystem links, known credential-bearing
blocks and URLs, administrative crawler instructions, unrelated project data,
and non-canonical Q&A notes. This is defense in depth, not a general-purpose
secret scanner. The report writer must treat every source excerpt as untrusted
data rather than an instruction.

Saving evidence is allowed only before report prose or assertions exist. It
updates the scoped package to `evidence_ready`, including when readiness is
explicitly `insufficient`; the writer must inspect that field before drafting.
The manifest commits a content fingerprint over the bounded snapshot. Loading
rejects changed excerpt hashes or an incomplete/tampered save. A read-only
freshness check can detect changes within the same bounded local scope, but it
does not establish that external data remains current.

### Phase 3 drafting boundary

Drafting uses a configured `TextProvider`; the report package contains no
Hermes-specific commands or credentials. Large evidence packages are analyzed
in bounded batches and then organized in a separate synthesis call. Both stages
receive explicit JSON schemas and treat saved evidence and intermediate
findings as untrusted data. Provider prompts remain below the Windows-safe
one-shot boundary.

The provider does not write Markdown. It proposes a small number of material,
typed findings and then selects their report placement and a qualified
conclusion. DEFINALYZER rejects unknown evidence IDs, repeated placements,
unsupported non-uncertainty assertions, source-only claims presented as
independently collected evidence, invalid report stances, and full-review
recommendations without a selected risk or uncertainty. If retrieval is
insufficient, no polished management report is created; deterministic Analyst
Notes explain what is missing without an AI call.

After validation, DEFINALYZER assigns stable `C-001` assertion IDs and renders
portable management Markdown with ordinary evidence footnotes. Research-process
warnings and per-assertion limitations are rendered in `Analyst-Notes.md`, not
repeated through the management report. Model-supplied text is
escaped so it cannot introduce report headings, HTML, images, or links. The
The dashboard carries lifecycle status rather than inserting software-state
warnings into publication prose. A question answer is classified as an
interpretation; only a full review can contain a
recommendation assertion.

`draft.json` is the commit and recovery bundle. It binds the draft to the exact
evidence fingerprint and contains the readiness classification, validated
claims, management Markdown, Analyst Notes, and their hashes. `Report.md` is
intentionally editable, and such
edits are detected but not overwritten. Machine-readable claim edits are
rejected. Interrupted materialization of missing Markdown or initial empty
claims and Analyst Notes can be repaired from the committed bundle. Draft creation never
replaces an existing report and concurrent attempts are locked out.

Support is independently recorded as directly supported, partially supported,
unsupported, or conflicted. Facts cannot be marked unsupported. Assertions
other than uncertainties require evidence. Each assertion also contains a
short public rationale and explicit limitations.

The Markdown writer uses ordinary footnotes such as `[^E-001]` so published
reports remain readable outside DEFINALYZER. The assertion ledger is
the machine-checkable map used to detect unsupported or stale prose.

### Phase 4 quality-review boundary

`definalyzer.report_quality` performs an independent representation audit of a
committed, unedited draft. It does not change `Report.md`, `claims.json`, or
`evidence.json`, and it does not determine whether an underlying protocol claim
is true. Human-edited prose must first be reconciled with the assertion ledger
by the revision workflow.

Deterministic checks compare the Markdown, assertion ledger, and evidence
ledger for missing sections, internal research-process language, missing or
unknown citations, duplicate or unused
evidence notes, claim statements absent from prose, untraced numeric values,
dated changing-data language, recommendation source class, and changes to the
bounded local source corpus. Local source freshness means only that the saved
scope still matches; it is not an online freshness guarantee.

Assertions with evidence then receive a bounded, provider-neutral semantic
review. Each prompt contains only an assertion and its exact saved excerpts,
marks them as untrusted data, forbids browsing and tool use, and requests a
strict relationship (`supports`, `contradicts`, `context_only`, or `unclear`)
plus a qualified reasoning assessment. Provider responses must return every
case and evidence ID exactly once and are rejected before any quality result is
committed if their structure is invalid. An insufficient-evidence result stops
at Analyst Notes and cannot enter quality review or publication.

`quality.json` is the commit and recovery record. It binds the review to hashes
of the report, claims, and evidence snapshot, records public issue explanations
and limitations, and contains the deterministically rendered `Quality.md`.
Interrupted Markdown materialization can be repaired from that committed JSON.
Quality review is immutable for the current draft and concurrent attempts are
locked out. Any warning or error yields `issues_found`; a clean automated audit
yields `passed`, which still requires human review and is not verification.

### Phase 5 revision and finalization boundary

`definalyzer.report_lifecycle` turns a reconciled edit into a new numbered
revision. Manual edits require the complete matching claims ledger; report text
cannot silently drift away from stable assertion IDs, citations, or evidence
notes. The preceding manifest, evidence, claims, draft, report, quality result,
approval record, and assets are copied into `Revisions/0000`, `0001`, and so on
before the active revision changes. Revision writes use atomic file replacement,
rollback on an ordinary write failure, and a lifecycle lock. A new revision
returns to `draft`, clears the active quality and approval state, and therefore
must pass quality review again.

A provider-assisted revision is intentionally narrow: the analyst selects one
existing assertion and supplies the edit request. The provider receives that
assertion, its exact saved excerpts, and relevant quality findings in one
bounded prompt. It may propose only the assertion's statement, rationale,
support, limitations, and a public change summary. It cannot choose new
evidence, add or remove assertions, write Markdown, change verification, or
finalize. DEFINALYZER validates and escapes the response, renders the edited
assertion, and saves it as another non-final draft. Existing uncommitted human
prose is never overwritten by an AI revision.

Finalization is deterministic and requires an explicit human approval action.
The current draft and Analyst Notes must be unedited, its quality result must be `passed`, and the
bounded local evidence scope must still match the reviewed snapshot. A full
review also requires separate approval of its recommendation; a question report
cannot claim recommendation approval. `approval.json` binds the exact report,
Analyst Notes, claims, quality result, revision number, and finalization time, while its digest
is committed in the manifest. Loading a final report rejects changed prose,
claims, quality, or approval data. Revising a final report archives the approved
state and creates a new draft rather than replacing the final history.

### Phase 6 publication-export boundary

`definalyzer.report_export` is a provider-free publication step. It accepts
only an integrity-checked `final` report, then creates an immutable
`Exports/revision-0000` bundle. A bundle can include portable Markdown, a
styled standalone HTML page, and a paginated PDF. Every export also carries
editable `Analyst-Notes.md` for the researcher; it is not inserted into the
management PDF. `export.json` binds every output to the exact approved report,
Analyst Notes, claims, quality, and approval hashes.
Re-exporting the same revision refuses to overwrite the existing publication.

The publication Markdown removes the obsolete draft warning, records the
finalization time, and remains the editable source for use in another editor or
publishing platform. HTML escapes embedded markup and permits only the
renderer-controlled report structures. PDF generation uses ReportLab and adds
consistent typography, page numbers, and restrained publication styling. The
PDF dependency is declared in `requirements.txt`; no online service is used.

Charts are optional. The caller names a saved `market_data` or
`blockchain_evidence` record and dotted JSON fields; it cannot supply the
numeric values. DEFINALYZER reads the values directly from that exact evidence
excerpt and requires an `as_of` timestamp, units, provenance, a no-arithmetic
transformation record, and a limitation. It saves both SVG and JSON chart
sources beside the exports. Missing, undated, non-numeric, non-finite, or
unstructured data is rejected. When no suitable structured evidence is
selected, the publication contains no chart rather than an inferred visual.

The UI layer can call the same provider-free operation directly:

```python
from definalyzer.report_export import ChartRequest, export_final_report

chart = ChartRequest.from_fields(
    title="Supply Snapshot",
    evidence_id="E-004",
    fields={
        "Circulating": "supply.circulating",
        "Maximum": "supply.maximum",
    },
    unit="tokens",
)
export_final_report(
    workspace=workspace,
    report_id="supply-review",
    charts=[chart],
)
```

The example does not tell the chart what the values are. It tells the exporter
where to read them from the already saved evidence record.

### Phase 7 dashboard boundary

The local dashboard exposes the report lifecycle through
`DefinalyzerApplication`; it does not reimplement report validation in browser
code. Report cards reveal only currently valid actions and submit long-running
draft, review, and revision work to the existing single-worker queue. Report
and quality Markdown remain readable in the normal page reader.

Finalization requires a separate form with explicit human approval. Full
reviews also require recommendation approval. The export form creates all
three publication formats together and may specify one optional evidence-backed
chart using JSON field paths, never typed values. Publication links are served
only from files listed in `export.json`; each file's SHA-256 is checked before
it is opened and exported HTML is delivered with scripts disabled.

### Phase 8 acceptance boundary

The dashboard rejects an unknown report, an out-of-order lifecycle action, or
a second mutation while that project already has an active job before creating
a background job. Domain validation remains authoritative, but routine user
mistakes therefore appear immediately instead of producing a misleading failed
activity entry.

Release acceptance exercises the complete HTTP-controlled lifecycle from
scope through evidence, drafting, quality review, explicit finalization, and
all-format export with a deterministic test provider. It also confirms that a
served publication still matches its export manifest, that local-origin and
session-token restrictions remain active, and that failure does not advance a
report's state. Live provider and RPC smoke tests remain separate because they
consume external services and are not prerequisites for offline regression
tests.

## Required report shape

Generated reports will contain, at minimum:

1. title and evidence date
2. executive summary
3. question and scope, or full-review scope
4. analysis
5. risks and strongest counterarguments
6. material unknowns and evidence limitations
7. qualified recommendation, including what would change it
8. evidence notes

Mechanics, economics, governance, security, comparisons, and visuals are added
only when relevant. Empty boilerplate sections are omitted.

## Visual and revision rules

Charts must be generated from explicit saved data. Every chart records its data
source, as-of date, transformation, units, and limitations. AI may recommend a
visual but cannot invent values. Decorative visuals must never imply evidence.

Targeted edits create a new revision and preserve the complete previous report
state. They do not alter evidence records or silently retain approval. Final
reports cannot be replaced in place; revising one archives the approval and
creates a new draft revision.

## Trust boundary

Quality review checks whether the report accurately represents its evidence. It
does not establish that official documentation, third-party data, or protocol
claims are true. Independent verification keeps its existing meaning and human
approval boundary. A quality pass is neither verification nor publication
approval. Insufficient evidence should produce a narrower conclusion or an
explicit abstention.
