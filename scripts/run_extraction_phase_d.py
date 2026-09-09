"""One bounded live acceptance run. Refuses to overwrite or repeat a prior run."""
import hashlib
import json
import sys
import time
import traceback
from copy import copy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from definalyzer.workspace import WorkspaceManager
from definalyzer.settings import SettingsManager
from definalyzer.providers import create_provider
from definalyzer.research_preparation import prepare_research


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output_hashes():
    values = {}
    for path in (ROOT / 'output').rglob('*'):
        if path.is_file():
            try:
                value = digest(path)
            except PermissionError:
                value = 'UNREADABLE: file access denied (not hash verified)'
            values[path.relative_to(ROOT / 'output').as_posix()] = value
    return values


def main():
    audit = ROOT / 'tmp' / 'phase-d-live'
    audit.mkdir(parents=True, exist_ok=True)
    if (audit / 'run.json').exists():
        raise RuntimeError('A prior Phase D run exists; refusing to reset its budget.')
    started = time.monotonic()
    state = {'started_at': datetime.now(timezone.utc).isoformat(), 'calls': [],
             'limits': {'calls': 6, 'characters': 144000, 'seconds': 480}}

    def save(name, value):
        (audit / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    def progress(message):
        line = f'{time.monotonic() - started:.1f}s {message}'
        print(line, flush=True)
        with (audit / 'progress.txt').open('a', encoding='utf-8') as stream:
            stream.write(line + '\n')

    originals = output_hashes()
    save('original-output-before.json', originals)
    fixture_path = ROOT / 'tests/fixtures/extraction_demo/cases.json'
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
    selected = {fixture['blocks'][name]['path']: fixture['blocks'][name]['snapshot_sha256']
                for name in ('fees', 'announcement', 'token', 'clickwrap')}
    ws = WorkspaceManager(ROOT / 'tmp/phase-d-workspace').create_project(
        name='Pump.fun', entity_type='protocol', docs_url='https://pump.fun')
    for relative, expected in selected.items():
        source = fixture_path.parent / 'snapshots' / (expected + '.md')
        assert digest(source) == expected
        target = ws.sources_directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    state.update({'workspace': str(ws.root), 'project': ws.slug,
                  'fixture_sha256': digest(fixture_path), 'sources': selected,
                  'application_sha256': {p.relative_to(ROOT).as_posix(): digest(p)
                                         for p in (ROOT / 'definalyzer').rglob('*.py')}})
    provider = create_provider(SettingsManager(ROOT / 'output').load()['llm'])
    state['provider'] = provider.name
    state['model'] = 'Existing Hermes configuration; no model override'
    save('run.json', state)

    class MeasuredProvider:
        name = provider.name
        timeout_seconds = provider.timeout_seconds

        def generate(self, prompt, **kwargs):
            if len(state['calls']) >= 6:
                raise RuntimeError('Phase D audit guard refused a seventh dispatch.')
            number = len(state['calls']) + 1
            record = {'number': number, 'characters': len(prompt), 'started_seconds': time.monotonic() - started,
                      'timeout_seconds': self.timeout_seconds, 'status': 'dispatched'}
            state['calls'].append(record)
            save('run.json', state)
            (audit / f'call-{number:02}-prompt.txt').write_text(prompt, encoding='utf-8')
            progress(f'Provider call {number}/6 started ({len(prompt)} prompt characters).')
            delegate = copy(provider)
            delegate.timeout_seconds = self.timeout_seconds
            call_started = time.monotonic()
            try:
                response = delegate.generate(prompt, **kwargs)
                (audit / f'call-{number:02}-response.txt').write_text(response.text, encoding='utf-8')
                record['status'] = 'returned'
                return response
            except BaseException as exc:
                record['status'] = 'failed'
                record['error'] = str(exc)
                raise
            finally:
                record['elapsed_seconds'] = time.monotonic() - call_started
                save('run.json', state)
                progress(f'Provider call {number}/6 {record["status"]} after {record["elapsed_seconds"]:.1f}s.')

    try:
        result = prepare_research(ws, provider=MeasuredProvider(), selected_paths=sorted(selected), progress=progress)
        state['result'] = result
        progress(f'Preparation finished: {result["status"]}; {result["accepted_claims"]} accepted claims.')
    except BaseException as exc:
        state['error'] = str(exc)
        (audit / 'traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
        progress(f'Preparation stopped: {type(exc).__name__}: {exc}')
    finally:
        after = output_hashes()
        state['original_output_preservation'] = {
            'files_before': len(originals), 'files_after': len(after),
            'changed_or_missing': [p for p, h in originals.items() if after.get(p) != h],
            'unreadable': [p for p, h in originals.items() if h.startswith('UNREADABLE:')],
            'added': sorted(set(after) - set(originals))}
        state['elapsed_seconds'] = time.monotonic() - started
        state['prompt_characters'] = sum(c['characters'] for c in state['calls'])
        save('run.json', state)
        print(json.dumps({k: state[k] for k in ('elapsed_seconds', 'prompt_characters', 'original_output_preservation')}), flush=True)


if __name__ == '__main__':
    main()
