# Local Dashboard

Running and queued operations have a **Stop** button in Activity and the active
progress banner. Queued work is cancelled before execution. Running work shows
**Stopping** until cleanup finishes, then **Stopped**. Hermes and its child
processes are terminated; crawlers are cancelled with resource cleanup. A
synchronous HTTP request already in flight may need to finish or reach its
timeout before stopping. No subsequent workflow steps are started.

Completed files and saved checkpoints remain. Cancellation does not undo work
already committed, and there is no automatic restart. Starting the operation
again is explicit; existing checkpoint/budget rules still apply. Closing the
dashboard requests cancellation of its jobs. Only one dashboard may own a given
workspace at a time, preventing two windows from running conflicting queues.

The dashboard is a local visual shell over the same projects, Markdown, and
workflow functions used by the terminal. It does not import research into a
database and does not replace the portable `output/vault/` directory.

Tokens and Coins use asset names and symbols, independently of their originating
projects. Open an asset for its overview and related research, or choose **Research
this asset** to create its own research context. Existing workspaces can use the
[additive identity migration](ASSET_IDENTITIES.md); restart the dashboard after
updating the Python code so the new routes and asset inventory are loaded.

## Source-supported pages

New research pages offer **Source** beside each checked claim. It opens the exact
saved passage and surrounding context. Existing authored notes are preserved;
**Original notes** and **Compare changes** remain available when a supported
version is shown. There is one generated sidebar entry per topic. Unanswered
questions and missing current measurements remain visible. See
[Source-supported research](RESEARCH_FACTS.md).

## Start

From the project folder with the virtual environment active:

```powershell
python main.py dashboard
```

The application selects an available local port and opens the resulting
`http://127.0.0.1:<port>/` address. This avoids conflicts with ports reserved
by Windows or another local tool. Keep the terminal open while using the
dashboard. Press `Ctrl+C` in that terminal to stop it. To request a specific
port or avoid opening the browser automatically:

```powershell
python main.py dashboard --port 9000
python main.py dashboard --no-open
```

The dashboard can also be launched from option 20 in the guided menu.

## What it does

- creates, selects, and permanently deletes projects
- shows the seven workflow stages and truthful action availability
- reads project research, verification, token, and analyst-review Markdown
- follows project-local research links without changing the underlying files
- queues long analysis, crawl, extraction, registry, verification, market,
  Q&A, and report operations without freezing the page
- exposes official-source registration and collection, manual token entry,
  provider configuration/testing, and assessment approval forms
- shows the active job in a prominent progress strip and repeats detailed
  progress and errors in the activity panel; extraction batches advance the
  bar as each saved batch completes
- warns when no progress has been recorded for five minutes and clearly marks
  a lost dashboard connection instead of leaving an old timestamp frozen
- manages evidence-backed reports from scope through evidence retrieval,
  drafting, quality review, targeted revision, human finalization, and export
- opens finalized Markdown, HTML, and PDF publication files only after their
  saved integrity hashes have been checked

## Reports

Open **Project Controls**, then **Reports**. A focused report answers one
required question; a full project review produces a qualified recommendation.
The dashboard shows only actions valid for the report's current lifecycle:

1. create the report scope
2. prepare bounded evidence locally
3. ask the configured AI provider to draft from that evidence
4. run the independent representation-quality review
5. revise one selected assertion when necessary
6. explicitly approve and finalize the reviewed revision
7. export editable Markdown, standalone HTML, and PDF together

Only one project operation can be active at a time. If a report step is
selected out of order, the dashboard explains which prerequisite is missing
without adding a failed job to the activity panel. A failed provider-backed
step leaves the last valid report state intact and can be retried.

Optional charts are created during export. Enter a dated structured evidence
ID and one `Label=path` JSON field per line. The dashboard never asks the user
or AI to type chart values; the exporter reads them from the saved evidence.
If suitable structured evidence is unavailable, leave the chart fields blank.

Management reports, researcher-facing **Analyst Notes**, and quality reviews
appear in the normal page reader under **Reports**. The report card shows answer
readiness. Insufficient evidence produces Analyst Notes instead of a polished
report. Final publication downloads remain attached to the report card.
Finalization and export do not change the concise extraction pages.

The standalone advanced evidence collector remains a terminal interface
because its request builder is an interactive power-user tool. Planned project
evidence collection is available directly in the dashboard.

## Local security boundary

The server binds only to this computer. Mutating requests require a random
session token held by the open dashboard page, and requests with non-loopback
origins or Host headers are rejected. Markdown is rendered by a restricted
local renderer: embedded HTML is displayed as text, not executed. The browser
never receives RPC URLs, `.env` values, or Hermes credentials.
Final report files are served only from their recorded export manifest and are
hashed again before the dashboard opens them. Exported HTML cannot run scripts.
