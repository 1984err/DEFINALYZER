# Application Architecture

DEFINALYZER keeps research Markdown and project JSON as portable, local data.
Terminal menus, power-user commands, and the local dashboard are user
interfaces over the same application and domain functions; they must not
implement separate extraction or verification logic.

## Shared application boundary

`definalyzer.application.DefinalyzerApplication` is the UI-neutral entry point
for reading project state and invoking reusable interactive operations. It
provides:

- project creation, loading, listing, deletion, and vault-index refresh
- JSON-safe project snapshots with schema versioning
- action availability and a human-readable reason for every disabled action
- research-page inventory and pending-assessment counts
- provider-backed project Q&A
- deterministic CoinGecko supply refresh

`ProjectSnapshot.to_dict()` is safe to return from a local HTTP endpoint. Paths
remain explicit local paths, and action state is computed from actual files and
workflow readiness rather than assumed from menu order.

Long-running crawl, extraction, registry, evidence, and evaluation operations
continue to use their existing tested domain implementations. The dashboard
calls those operations through a single-worker background queue and publishes
structured progress; it does not copy their logic into web routes.

The dashboard is implemented with the Python standard library and bundled
static assets. It binds only to loopback, requires a random per-process token
for mutations, rejects non-local origins and Host headers, and never exposes
Hermes or RPC credentials to the browser.

## Canonical data

- Research Markdown remains canonical and usable without the dashboard.
- Project manifests and generated JSON remain machine-readable state.
- `verification-catalog.json` provides a structured verification index, but is
  refreshed from the canonical verification Markdown after approved changes.
- Dashboard metadata may use a local database later, but research content must
  remain exportable as ordinary Markdown.
- Evidence-backed reports use the provider-neutral package and validation rules
  in [REPORT_CONTRACT.md](REPORT_CONTRACT.md). Report Markdown remains separate
  from concise extraction pages, with companion evidence and assertion ledgers.
- Report evidence preparation is an offline domain operation over a bounded,
  project-owned source allowlist. Its saved snapshot and omissions are
  auditable; retrieval success is not verification or factual completeness.
- Report drafting uses the shared provider boundary but validates structured
  findings and a report plan before deterministically rendering Markdown. Its
  committed bundle supports interruption recovery without silently replacing
  human-edited prose.
- Report quality review is a separate provider-neutral domain step over the
  committed report, assertion ledger, and exact saved evidence. Deterministic
  citation/provenance checks and bounded semantic support checks write an
  immutable recoverable quality record; they neither edit report claims nor
  replace independent verification and human approval.
- Report lifecycle operations archive complete numbered revisions and require
  reconciled assertion ledgers for human edits. A bounded provider may revise
  one analyst-selected assertion but cannot control Markdown or approval.
  Finalization is deterministic, requires an unchanged passing quality review
  plus explicit human approval, and binds that approval to content hashes.
- Final report export is another UI-neutral domain operation. It creates
  immutable Markdown, HTML, and PDF publication bundles only from validated
  final reports. Optional visuals extract named numeric fields directly from
  dated saved JSON evidence and retain their SVG, data, provenance, units, and
  limitations; absence of suitable data produces no graph.
- The dashboard report workspace calls these same application-domain methods
  for every lifecycle transition. It lists only active report and quality
  Markdown in the reader, runs AI steps through the existing single-worker job
  queue, requires explicit approval inputs for finalization, and rechecks
  export file hashes before serving local HTML, PDF, Markdown, or SVG files.

## Safety boundaries

- UI shells do not store Hermes or RPC credentials.
- Indexed-query integrations such as Dune are deferred until an authenticated
  API adapter can execute queries and preserve result provenance.
- AI responses do not change verification status without the existing analyst
  approval step.
- Destructive actions retain exact project selection and confirmation in the
  user interface.
