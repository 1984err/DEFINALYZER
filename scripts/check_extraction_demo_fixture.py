"""Check frozen evaluation provenance offline; does not score model accuracy.

Run from any directory: python scripts/check_extraction_demo_fixture.py
Only reads the fixture. Never imports the app, initializes a provider or writes output.
"""
import hashlib
import json
from pathlib import Path


def check_fixture(directory):
    fixture = json.loads((directory / 'cases.json').read_text(encoding='utf-8'))
    if fixture['schema_version'] != 1:
        raise ValueError('Unsupported fixture version')
    blocks = fixture['blocks']
    snapshots = {}
    for alias, block in blocks.items():
        digest = block['snapshot_sha256']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError(f'{alias}: invalid snapshot digest')
        raw = (directory / 'snapshots' / f'{digest}.md').read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f'{alias}: snapshot bytes changed')
        lines = raw.decode('utf-8-sig').splitlines(keepends=True)
        start, end = block['start_line'], block['end_line']
        if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
            raise ValueError(f'{alias}: invalid source locator')
        context = ''.join(lines[start-1:end])
        if context != block['text'] or hashlib.sha256(context.encode()).hexdigest() != block['context_sha256']:
            raise ValueError(f'{alias}: block does not match original lines')
        snapshots[digest] = raw
    seen = set()
    anchor_count = 0
    for case in fixture['cases']:
        cid = case['id']
        if cid in seen:
            raise ValueError(f'Duplicate case: {cid}')
        seen.add(cid)
        if case['lane'] not in {'demo', 'regression'}:
            raise ValueError(f'{cid}: unknown lane')
        if not case['sources'] or any(s not in blocks for s in case['sources']):
            raise ValueError(f'{cid}: missing source block')
        if not case['must_capture'] or not case['behavior'] or not case['anchors']:
            raise ValueError(f'{cid}: incomplete acceptance criteria')
        for anchor in case['anchors']:
            if anchor['source'] not in case['sources'] or not anchor['quote'] or anchor['quote'] not in blocks[anchor['source']]['text']:
                raise ValueError(f'{cid}: anchor is not an exact original quote')
            anchor_count += 1
    referenced = {s for case in fixture['cases'] for s in case['sources']}
    if referenced != set(blocks):
        raise ValueError('Unreferenced evaluation blocks')
    return {'fixture_integrity': 'pass', 'cases': len(seen), 'blocks': len(blocks),
            'snapshots': len(snapshots), 'exact_anchors': anchor_count,
            'model_quality': 'not evaluated', 'application_acceptance': 'not evaluated',
            'provider_calls': 0}


if __name__ == '__main__':
    directory = Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'extraction_demo'
    print(json.dumps(check_fixture(directory), indent=2))
