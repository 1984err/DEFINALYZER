"""Explicit, bounded preparation of selected saved documentation for reports."""
from .operation_budget import BudgetProvider
from .research_scope import _inputs, _hash, _json, source_files, prepare_scope
from .research_facts import collect_facts, write_topic, TOPICS, VERSION


def preparation_sources(workspace):
    rows = []
    for path in source_files(workspace.sources_directory):
        relative = path.relative_to(workspace.sources_directory).as_posix()
        text = path.read_text(encoding='utf-8-sig')
        title = next((line[2:].strip() for line in text.splitlines() if line.startswith('# ')), path.stem.replace('-', ' '))
        # Recommendation only: selection is shown before the user dispatches it.
        priority = 0 if any(p in relative.lower() for p in ('fees_revenue', 'tokenomics', 'overview')) else 1 if path.name.lower() == 'readme.md' else 2
        rows.append({'path':relative, 'title':title[:160], 'characters':len(text), 'priority':priority})
    rows.sort(key=lambda r:(r['priority'], r['path']))
    recommended = {r['path'] for r in rows[:4]}
    return {'sources':[{**r, 'recommended':r['path'] in recommended} for r in rows],
            'limits':{'calls':6, 'characters':144000, 'seconds':480}}


def prepare_research(workspace, *, provider, selected_paths, progress=None):
    # Hold one operation lease across scope, facts and publication. Their
    # individual registry locks protect each write phase but not budget loading.
    from .app import _project_workflow_lock
    with _project_workflow_lock(workspace):
        return _prepare_research(workspace, provider=provider, selected_paths=selected_paths, progress=progress)


def _prepare_research(workspace, *, provider, selected_paths, progress=None):
    progress = progress or (lambda _:None)
    inputs = _inputs(workspace)
    if not isinstance(selected_paths, list) or not selected_paths or any(type(p) is not str or p not in inputs for p in selected_paths):
        raise ValueError('Choose one or more saved documents from this project.')
    selection = sorted(set(selected_paths))
    if len(selection) > 8:
        raise ValueError('Choose at most eight documents for one bounded preparation.')
    key = _hash(_json({'inputs':inputs, 'selection':selection, 'version':VERSION}))
    budget = BudgetProvider(provider, workspace.project_root/'facts'/'preparation-budgets'/f'{key}.json')
    progress(f'Preparing {len(selection)} selected saved documents. Limit: 6 AI calls and 8 minutes, including checks and repairs.')
    prepare_scope(workspace, provider=budget, call_budget=1, selected_paths=selection, progress=progress)
    facts, usage = collect_facts(workspace, provider=budget, progress=progress)
    for topic in TOPICS:
        write_topic(workspace, facts, topic, refresh=True)
    partial = facts['preparation']['status'] != 'complete'
    return {'status':'needs_attention' if partial else 'complete', 'usage':usage,
            'accepted_claims':len(facts['facts']), 'selected_paths':selection,
            'message':('Accepted research is saved. Preparation is incomplete; remaining coverage is shown in the research pages.' if partial else
                       'Selected-source research is ready. Return to Reports to generate a report; other documents were not assessed.')}
