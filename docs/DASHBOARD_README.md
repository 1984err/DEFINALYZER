# Dashboard Guide

To stop an operation, click **Stop** in the progress banner or its Activity row.
**Stopping** means cleanup is still in progress; **Stopped** means the worker has
ended. An in-flight network request may take a little longer to finish. Saved
progress remains, and the operation will not restart unless you explicitly start
it again. You can also stop a queued operation before it starts.

The dashboard is the simplest way to use DEFINALYZER. Everything stays on your computer, and the research pages remain ordinary Markdown files.

## Basic workflow

1. Select **New project** and enter the project name, type, and primary official documentation URL.
2. Leave **Start the complete analysis after setup** selected to continue directly into research, or clear it when you only want to prepare the project first.
3. Select the project from **Protocols**, **Tokens**, **Coins**, or **Chains** whenever you want to return to it.
4. Read the generated pages from the Research navigation.
5. Open **Project Controls** when you want to run an individual step, ask a research question, or work through verification.

## Navigation

- **Protocols, Tokens, Coins, and Chains** contain your available research.
- **Research** contains the extracted decision-relevant pages.
- **Verification** contains checks that may affect the analysis.
- **Tokens** contains protocol-native token pages and supply snapshots.
- **Coins** contains chain-native coin pages and supply snapshots.
- **Q&A** contains answers you chose to save.
- **Reports** contains narrative research reports and companion Analyst Notes.
  Analyst Notes hold coverage details and follow-up work; material limitations
  remain visible in the report itself.
- **Activity** shows work that is queued, running, completed, or failed. Numbered workflows show their current stage and progress; other active tools show an animated working bar and the time of their latest update.

Select a token and use **Refresh token supply** above its research page to update
that asset from CoinGecko. Native coin pages show **Refresh coin supply**. The
page updates when the job finishes; other assets in the project are not refreshed.

## Research scope

Analyze project classifies saved documentation before generating notes. Use
**Project Controls → Research scope** to run just that step. The scope card shows
the subject, related systems and unresolved attribution. **Scope and extraction
plan** exposes the finite call budget and optional corrections. Existing pages
stay readable and are flagged when they predate the new scope.

## Important notes

- Select **Expand page** above a research page to hide the side panels and use
  the full dashboard for reading. Select **Restore layout** or press **Esc** to return.
- Wide tables scroll sideways using the scrollbar below each table. You can
  also click the table area and use the keyboard's left/right arrows.

- New projects start the complete analysis by default. Clear that option when you want setup only; you can later select **Analyze project** from Project Controls.
- You can use individual project tools without rerunning the complete workflow.
- Use **Reports → New report** for **Full review** or **Answer a question**.
  **Generate report** prepares, writes, checks, and attempts bounded repairs
  automatically. New reports need source-supported research from Analyze project.
- **Request a revision**, **Edit wording**, and **Compare versions** keep earlier
  versions available. **Use latest research** creates another version using the
  latest prepared research, without rerunning source collection.
- Finalization requires your explicit approval. Separate recommendation approval
  appears only when the report includes one.
- Final exports include Markdown, HTML, PDF, and separate Analyst Notes. Optional
  charts are selected from validated dated quantities using readable labels.
  Existing V1 reports retain their original controls and export behavior.
- See [Reports V2](REPORTS_V2.md) for readiness, manual edits and recovery.
- Deleting a project is permanent. The dashboard requires you to type its exact name first.
- Keep the dashboard terminal window open while using the dashboard. Closing it stops the local dashboard but does not delete any research.

## Workspace controls

- **AI Provider** checks or configures the connection used for AI-assisted extraction and questions.
- **Refresh dashboard** reloads the latest projects, pages, tokens, and activity into the screen.
- **Rebuild Index Pages** regenerates the portable Markdown index pages from existing research. It does not delete research.
