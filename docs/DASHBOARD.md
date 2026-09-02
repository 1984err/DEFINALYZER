# Local Dashboard

The dashboard is a local visual shell over the same projects, Markdown, and
workflow functions used by the terminal. It does not import research into a
database and does not replace the portable `output/vault/` directory.

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
- follows project-local Obsidian links without changing the underlying files
- queues long analysis, crawl, extraction, registry, verification, market,
  Q&A, and Dune-assistant operations without freezing the page
- exposes official-source registration and collection, manual token entry,
  provider configuration/testing, and assessment approval forms
- shows job progress and errors in the activity panel

The standalone advanced evidence collector remains a terminal interface
because its request builder is an interactive power-user tool. Planned project
evidence collection is available directly in the dashboard.

## Local security boundary

The server binds only to this computer. Mutating requests require a random
session token held by the open dashboard page, and requests with non-loopback
origins or Host headers are rejected. Markdown is rendered by a restricted
local renderer: embedded HTML is displayed as text, not executed. The browser
never receives RPC URLs, `.env` values, or Hermes credentials.
