# Asset identities and navigation

Phase 2 adds stable asset identities while keeping existing projects, sources,
registries, and report packages readable. It does not implement the Phase 3
documentation classifier or the later report redesign.

## Using assets in the dashboard

Tokens and Coins list asset names and symbols. Protocols and Chains continue to
list their research projects. A token's originating protocol is a relationship
inside its page, rather than the token's navigation identity.

An asset overview lists documented deployments and related research. Each project
has its own context page, so another project cannot overwrite its mechanics or
evidence. Project verification status is not inherited as asset verification.

**Research this asset** creates a dedicated Token or Coin project without starting
a crawl or AI job. It reuses the asset identity and links the existing sourced
context. Add official asset documentation before analyzing it; the application
does not assume that all of a protocol's documentation belongs to the token.
Opening the asset thereafter uses its own research context and controls.

**Add or update asset** lets you choose an existing named asset or add a new one.
Select the existing asset to rename it or change its documented deployment.
Identical tickers alone do not identify the same asset. The terminal asks for a
stable ID when multiple existing records share a symbol.

Native coins can also be created as standalone Coin projects. A token recorded
within a chain project remains a token when its asset kind is Token.

## Migrating saved research

Preview the migration without changing any files:

```powershell
python main.py assets migrate
```

Apply it:

```powershell
python main.py assets migrate --apply
```

The preview lists proposed asset names, kinds, owning contexts, and any legacy
ownership problems. Migration copies attributable legacy asset pages into new
context locations and creates named overviews. Original files remain unchanged.
An uncertain or already-overwritten legacy page is not copied into another
project: a registry-backed context records the limitation instead.

The new commit point is `output/entities/catalog.json`. Stable IDs, subject
associations, deployment IDs, aliases from renames, and project contexts live there.
Pages are stored under `output/vault/Tokens/<name>--<id>/` or the Coins equivalent.
`Index.md` is the shared overview; `Contexts/<project>.md` contains that project's
documented mechanics. New registry outputs also carry asset IDs. Old registry
files do not have to be rewritten by migration.

Existing ticker paths remain legacy files. Dashboard links can resolve an
unambiguous ticker to the named asset; ambiguous tickers require a named selection.
The new context pages are the active editable copies. Later edits to legacy
copies are preserved but are not automatically propagated to the new context.

Transactions save before-images and after-images under `output/entities/history/`.
`pending.json` records an incomplete write. A later asset mutation or migration
resumes that exact plan with the same IDs. If a file was edited after the plan,
recovery stops with its path rather than overwriting the edit. Repeating a
completed migration preserves IDs and content.

If a generated context was edited, regeneration preserves it and writes a
`.proposed.md` sibling for comparison. Shared asset directories and migrated
contexts are not removed by project deletion; active navigation excludes deleted
projects. Unreferenced asset cleanup is a separate future operation.

## Discovery, market data, and reports

Discovery reruns when source content, Tokenomics, or the discovery version changes,
even if tokens are already registered. An unchanged completed attempt is reused,
including when it found no token. Missing tokens in a later response are retained.
Manual records keep their values; conflicting AI candidates are saved in the
registry and flagged on the context page. Provider-free registry enrichment does
not falsely record an unperformed discovery attempt as complete.

Market caches use stable asset IDs for migrated assets. A legacy ticker snapshot
is reused only for one matching identity and deployment. Changing an address does
not make its old snapshot applicable to the new deployment. EVM address matching
is case-insensitive; non-EVM addresses preserve case.

New Q&A/report retrieval uses the requesting project's asset context. Existing
report evidence without the identity retrieval version continues to check its
original legacy source scope. Migration does not rewrite report evidence, approval
hashes, or exports and does not certify old notes under the proposed V2 fact model.

## Boundaries

Cross-project automatic reuse requires a matching documented deployment, asset
name, symbol, and kind. Unknown identities remain provisional. Cross-chain
equivalence is not inferred merely from the same name or symbol. Explicit edits
to an identified asset can record additional sourced deployments while retaining
the previous deployment history.

The catalog uses a workspace OS lock and atomic replacement; project registry
read/merge/write operations also have their own OS lock. Normal exceptions and
process termination release these locks. No model call receives a writable agent
toolset, and migration itself makes no provider, crawler, or market-data calls.
