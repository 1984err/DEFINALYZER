# Blockchain Collector MVP Status

Status: **complete and live-verified for the first-version scope**

Last verification: **2026-09-01**

## Included

- Ethereum, Arbitrum One, and Base chain configuration
- Chain-ID validation before collection
- Registry provenance attached to address-based evidence
- Strict job, parameter, address, hash, and chain validation
- One pinned block per chain for requests using `latest`
- Raw JSON-RPC requests and responses
- Complete, partial, and failed request statuses
- Non-overwriting job and evidence files
- Contract code, native balance, storage, calls, blocks, logs, transactions,
  and receipts
- ERC-20 metadata, supply, selected balances, and chunked transfer history
- ERC-1967 implementation, admin, and beacon slots
- Mechanical ABI decoding for supported standard reads
- JSON CLI for agents and advanced users
- Guided terminal menu for standalone human use
- Human-readable Markdown evidence summaries
- Machine-readable capability manifest
- Structured verification-request importer with per-row manual-review routing
- Guided import-to-collection workflow for standalone human use

## Verified

- Full repository automated suite: 242 tests passing
- Python compilation check passing
- Capability manifest parses as JSON
- Ethereum WETH high-level token and contract snapshots collected live
- Live evidence contained two complete requests, zero partial requests, zero
  failed requests, and one recorded pinned block
- Guided terminal flow created a job, raw evidence, and Markdown summary using
  live Ethereum data
- Phase 5 Ethereum WETH smoke check collected three requests with zero partial
  or failed results
- Markdown verification request imported into a validated job and collected
  live Ethereum evidence with one complete request and no failures

## Intentional boundaries

The collector records evidence. It does not:

- decide whether a documentation claim is true
- determine whether a transfer is a mint or burn
- classify a contract as safe, immutable, or upgradeable
- decide whether an owner or administrator is acceptable
- reconcile token supply or tokenomics claims
- add verification markers to research notes
- write to the Obsidian knowledge base

Those decisions belong to later verification and orchestration agents.

## Deferred after MVP

- Live smoke tests for Arbitrum and Base endpoints
- Arbitrary ABI ingestion and general-purpose ABI encoding
- Explorer API integration and verified-source retrieval
- Automatic contract-creation transaction discovery
- Transaction execution traces and internal calls
- Non-EVM chains
- Standards beyond the included ERC-20 and ERC-1967 evidence recipes
- Automatic selection of scanner operations from unstructured verification
  prose or tables
- Automated evaluation of evidence against claims
- Automated Obsidian updates

Historical state and old event ranges may require an archive-capable RPC
provider. Provider limitations are recorded as collection or partial-evidence
errors rather than silently ignored.
