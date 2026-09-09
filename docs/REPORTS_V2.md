# Reports V2

Blocked reports distinguish **Research needs preparation** from **More evidence
needed**. Existing legacy notes do not mean that source-checked report research
has been prepared. **Prepare research** opens an explicit analysis form, with
source refresh off; it does not run automatically. Return to Reports afterward.
If the request is now supported, the saved attempt offers **Generate report**.
Otherwise the card lists the missing inputs and offers **Add research sources**.
Asking for another report while preparation is still pending opens the same
preparation form instead of adding another blocked attempt.

**Compare versions** appears only after a second saved version. **Use latest
research** appears when research changed or a substantive attempt exhausted its
repair allowance, not as a retry for unchanged insufficient evidence. Existing
attempts and frozen files remain intact. New blocked report files explain their
missing inputs directly and do not claim that source review was performed.

Phase 6 adds **Fix review issues** for saved drafts that need attention. It passes
the existing findings into a bounded revision, preserving earlier versions. You
do not need to retype the review. A malformed reviewer response retries the check
without rewriting otherwise valid prose. Exhausted incomplete generations use
**Use latest research** to explicitly start another attempt; Resume is shown only
while an existing run has an allowance left.

Phase 5 replaces the default report workflow. Existing V1 reports keep their
saved evidence, approvals, exports, and original controls.

## Using reports

1. Select a project and open **Reports → New report**.
2. Choose **Full review** or **Answer a question**, then **Generate report**.
   Audience, length, and an optional recommendation are under Writing preferences.
3. The application prepares the evidence, writes the report, checks original
   source support and conclusion strength, and attempts at most two repairs.
   The completed report opens automatically.
4. Read the report. Click a citation to see the original passage saved with that
   version. Analyst notes contain coverage gaps and supporting detail.
5. Use **Request a revision** for a paragraph, section, or whole report. **Edit
   wording** keeps your exact wording and checks it. **Compare versions** shows
   wording and supporting-evidence changes and links to earlier versions.
6. **Finalize** records approval of the exact reviewed version. A separate
   recommendation checkbox appears only when one is included. **Export** creates
   Markdown, standalone HTML, PDF, and separate Markdown analyst notes.

Readiness describes the requested answer. Documentation can support a mechanics
explanation. A broad review remains qualified when measurements are missing.
Valuation, current or historical measurement, and comparison requests currently
stop with a short explanation and missing inputs because V2 has no approved
observation adapter yet. It does not turn documented utility into a valuation.

New reports require Phase 4 source-supported research. If it has not been prepared
or the source files have changed, the report explains that analysis is needed.
Generating a report does not crawl or rerun a project. **Use latest research**
creates another version from the latest prepared research; it does not collect
new sources. Existing final versions remain available with their original evidence.
The NEAR rerun remains a separate, deferred user action.

## Manual edits and recovery

The package's top-level `Report.md` and `Analyst-Notes.md` are editable copies.
External edits are preserved and block finalization until **Review my saved
edits** succeeds. Keep the report title, source citations, and Sources section;
place prose under its section headings. New evidence requires a research refresh.
Edited analyst notes receive a separate check against the original passages and
retain their wording. Unsupported edits remain readable and cannot be finalized.
The dashboard reader uses the committed version until a new version is saved.

**Resume generation** retains the pending request, original evidence, completed
responses, and consumed repair rounds, including an interrupted revision request.
An interrupted provider call consumes its attempt. The system does not silently
repeat it with a fresh allowance. Exhausted work shows Needs attention. An explicit
new research refresh starts a new run and leaves prior work available.

## Implementation and integrity

V2 packages live at `vault/Reports/<project>/V2/<report-id>/`:

| Location | Purpose |
| --- | --- |
| `report.json` | Current revision pointer, request, lifecycle, final approval hashes |
| `Runs/<run-id>/` | Frozen inputs, consumed rounds, writing/review checkpoints and responses |
| `Revisions/revision-N/` | Immutable evidence, draft assertions, report, notes, review and commit |
| `Revisions/revision-N/approval.json` | Explicit approval bound to exact reviewed file hashes |
| `Preserved/` | Original externally edited bytes retained when a new version is committed |
| `Exports/revision-N/` | Immutable publication formats, original evidence and approval records |

Evidence selection uses question/profile topics, subject attribution, and lexical
matching. Related failure/dependency facts are included as context. Connected
conflict groups are retained together or omitted together with a visible gap.
Every selected fact embeds its checked original snapshot locators and context.
Several facts sharing a source locator retain all relevant original sentences.

Every narrative paragraph, including the opening assessment and conclusion, maps
to an assertion. Numeric/date literals must occur in that paragraph's original
evidence. An independent AI pass checks original passages, subject attribution,
conditions, negations, and analytical implications. A separate whole-report pass
checks title/headings, request relevance, decisive limits, conflicts, and conclusion
strength. This checks source support, not independent truth or deployed behavior.
Material failures prevent finalization; disclosed non-decisive gaps may be advisory.

Defaults: at most 512 facts scanned, 24 facts selected, 12,000 characters of
selected source/context material, 20 prose paragraphs, 12,000 prose characters,
24,000 characters per provider prompt, and two report-wide repair rounds.
Complete original context is never truncated to make an unsupported claim fit.
Unchanged review prompts reuse saved responses. Revision writers receive frozen
checked statements; the independent support reviewer receives original passages.

The project writer lock serializes report mutations with registry/research work.
Immutable revision files are written before switching the active pointer. Readers
verify committed file hashes, draft/evidence review bindings, and original passage
hashes. Final approval also binds analyst notes and the evidence's scope/coverage.
Later research changes flag old reports as using earlier evidence; they do not
rewrite or invalidate the saved final publication. Editable copies cannot alter
the content used for final exports.

Exports create all formats together, bind the export manifest to the final
revision, and verify hashes on download and reuse. Optional chart
choices come only from compatible dated structured documented quantities with
explicit network labels, the same subject/definition/unit/period, and no selected
conflict. Values are copied directly; no raw JSON paths or invented values are
requested from the user. The first export freezes its chart selection. Charts
describe documented parameters, not live observations.

## Phase 5 verification

Fixtures cover chain/protocol/token full reviews, focused mechanics questions,
insufficient valuation/current-state requests, manual edits, revision recovery,
bounded repairs, recommendation approval, tamper rejection, and frozen exports.
The browser fixture exercises generation, original-source inspection, targeted
revision, version comparison, finalization, and export controls. The PDF sample
was rendered and inspected across both pages.

One bounded live Hermes report check used the fictional Northstar/Harbor Bridge
corpus retained from Phase 4: six provider calls, one automatic repair, about
175 seconds. The final six-paragraph answer preserved the chain/bridge authority
boundary and source-period qualifications and passed original-source review.
This is a small smoke test. Fresh real-project acceptance and broader quality/cost
measurement remain Phase 6; live/on-chain source expansion remains later work.
