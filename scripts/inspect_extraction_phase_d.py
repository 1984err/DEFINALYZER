"""Offline inspection of the one saved Phase D run; never calls a provider."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from definalyzer.workspace import WorkspaceManager
from definalyzer.research_facts import load_facts, resolve_reference


def main():
    ws = WorkspaceManager(ROOT / 'tmp/phase-d-workspace').load_project('pump-fun')
    facts = load_facts(ws)
    if not facts:
        raise SystemExit('No published fact revision exists.')
    refs, errors = 0, []
    claims = []
    for fact in facts['facts']:
        for ref in fact['evidence'] + fact['support_check']['evidence']:
            refs += 1
            try:
                resolve_reference(ws, ref)
            except (ValueError, KeyError, OSError) as exc:
                errors.append({'proposal_id': fact['proposal_id'], 'error': str(exc)})
        claims.append({k: fact.get(k) for k in ('proposal_id', 'subject_id', 'topic', 'statement',
                                               'applicability', 'quantities', 'checked_question_ids')})
    result = {'revision': facts['revision'], 'preparation': facts['preparation'],
              'subjects': facts['subjects'], 'claims': claims, 'coverage': facts['coverage'],
              'references_checked': refs, 'reference_errors': errors,
              'note': 'Reference integrity only; semantic/demo acceptance requires review of the saved claims.'}
    target = ROOT / 'tmp/phase-d-live/inspection.json'
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
