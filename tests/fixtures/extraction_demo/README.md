# Saved-source extraction demo fixture

This is evaluation material for the resume demonstration, not generated project
research. See `docs/EXTRACTION_PHASE_B_STANDARD.md` from the repository root for
the demo script, rubric, proposed run budgets and phase boundaries.

`cases.json` holds 14 reviewed cases, original block locators and exact quote
anchors. `snapshots/` holds seven unmodified saved Markdown originals. Keep source
dates and hypotheses intact: these files do not establish current market facts.

Run `python scripts/check_extraction_demo_fixture.py` from the repository root.
This reads files only, needs no credentials and verifies provenance integrity.
It does not call a model or score extraction accuracy.

Use selected `blocks` as evaluation inputs and `cases` as the evaluator's rubric.
Never include the expected answers in extraction prompts. Do not copy annotations
into application research as though the pipeline generated and checked them.

For each later run record case IDs, fixture/app revisions, provider/model, actual
calls, characters, timing, observed output paths, missed meanings and forbidden
conclusions. A case is PASS only when every expected meaning and behavior holds
and no forbidden conclusion appears. Use FAIL or NOT RUN explicitly; fixture
integrity PASS is not a substitute for a model or UI result.
