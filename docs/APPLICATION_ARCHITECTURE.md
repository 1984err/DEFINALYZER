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
- optional, versioned Dune query dialogue
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

## Safety boundaries

- UI shells do not store Hermes or RPC credentials.
- Dune queries are drafted but never executed automatically.
- AI responses do not change verification status without the existing analyst
  approval step.
- Destructive actions retain exact project selection and confirmation in the
  user interface.
