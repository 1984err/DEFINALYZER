# Beta Scope and Limitations

DEFINALYZER is a research extraction and evidence-collection tool. It is not a
source of investment advice and it does not guarantee that protocol
documentation is complete or accurate.

## Research extraction

- Automated research-page generation currently uses the Hermes adapter. The
  internal provider boundary can support later adapters, but none are shipped
  in this beta.
- AI can omit or misstate information. Concise notes retain source provenance
  and explicit unknowns so an analyst can inspect material claims.
- Missing documentation means **not assessed**, not nonexistent.
- Login-protected, paywalled, inaccessible, or heavily interactive pages may
  need to be supplied manually.
- Public GitHub import collects Markdown documentation only. It does not audit
  source code, issues, pull requests, binaries, or program behavior.

## Tokens and market data

- Token pages are limited to native/governance tokens and protocol-issued
  tokens with material economics. Reserve and collateral assets are excluded.
- CoinGecko enrichment requires an exact documented contract or mint address.
  Chain-native coins without contracts use a unique identity match instead.
  A missing or ambiguous match remains visibly unavailable.
- CoinGecko supplies FDV and supply statistics only. Price, market cap, and
  short-term volume are intentionally excluded.
- Vesting, unlocks, mint controls, burns, and protocol utility come from
  documented token mechanics, not CoinGecko.

## Registries and verification

- Registry discovery is conservative. A blank field is preferred to a guessed
  address, chain, role, or token identity.
- Registry provenance shows where a value was documented; it is not proof that
  the documentation is current or truthful.
- Verification pages are analyst work queues with an optional automated layer.
  Manual-review entries are expected results, not failed checks.
- Raw evidence and mechanical decoding do not by themselves confirm or deny a
  claim. Evidence assessment remains separate and requires human approval.

## Blockchain collection

- Automated blockchain evidence supports Ethereum, Arbitrum One, and Base.
- Solana and other non-EVM protocols can still produce research and token
  pages, but their onchain checks are routed to manual instructions.
- Historical blocks and old log ranges may require an archive-capable RPC.
- The collector supports its published fixed operation set; it does not ingest
  arbitrary ABIs, execute transactions, trace internal calls, or discover
  deployment transactions automatically.
- DEFINALYZER never sends transactions or changes blockchain state.

## Local data and external services

- The dashboard is a loopback-only local interface. It must remain running in
  its terminal and is not a hosted multi-user service.
- The planned verification collector is available in the dashboard. The
  standalone advanced request builder remains terminal-only because it is an
  interactive power-user interface.
- `.env`, generated output, virtual environments, jobs, and evidence are
  ignored by Git in the supplied configuration. Users are still responsible
  for reviewing files before publishing a fork.
- Crawled documentation and generated research are stored locally under
  `output/`.
- AI-assisted extraction, Q&A, verification planning, and assessment send the
  selected prompt context to the configured Hermes inference provider.
- CoinGecko refreshes and RPC collection contact their respective external
  services.
- DEFINALYZER does not provide automatic backups. Back up or synchronize the
  `output/` directory if the research must be preserved.

## Beta expectation

The beta aims for stable, resumable workflows and honest partial results, not
uniform coverage of every protocol. Documentation formats and external APIs
will change over time, so minor crawler and extraction maintenance remains
normal.
