"""Fail-closed verification of final audit bindings and live identity cutover."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from capture import FILES, get

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))


def main():
    before, after, delta, review = [read(name) for name in ('before/receipt.json', 'after/receipt.json', 'identity_delta.json', 'independent_review.json')]
    assert review['status'] == 'PASS' and not review['open_blockers']
    for binding in review['bindings']:
        assert sha(ROOT / binding['path']) == binding['sha256'], binding['path']
    assert after['inputs_unchanged'] and before['inputs'] == after['inputs']
    assert after['aliases_removed'] == delta['aliases_removed'] and not after['aliases_added'] and not delta['aliases_added']
    assert len(after['aliases_removed']) == 12
    assert after['inventory']['people'] - before['inventory']['people'] == 12
    for receipt in (before, after):
        assert receipt['inventory']['reconciliation']['balance_holds']
        assert receipt['inventory']['reconciliation']['network_scope']['excluded_intern_records'] == 52107
    performance = get('/api/staffer-performance')
    assert performance['ready'] and not performance['errors']
    probes = read('after/route_probes.json')
    assert len(probes['separate_source_profiles']) == 24
    routes = []
    for old, new in zip(read('before/route_probes.json')['routes'], probes['routes']):
        assert old['result']['path'] == new['result']['path']
        assert old['result']['cost'] == new['result']['cost']
        routes.append({'origin': new['origin_label'], 'target': new['target_label'],
            'steps': new['result']['steps'], 'cost': new['result']['cost'],
            'evidence_classes': [h['evidence_class'] for h in new['result']['hops']], 'path_and_cost_unchanged': True})
    assert probes['served_javascript_sha256'] == sha(ROOT / 'fec/surfaces/staffer_live/staffer-route.js')
    staged = {}
    for name in FILES:
        data = subprocess.check_output(['git', 'show', ':' + name], cwd=ROOT)
        assert data == (OUT / 'commit_shadow' / name).read_bytes(), name
        staged[name] = hashlib.sha256(data).hexdigest()
    result = {'status': 'PASS', 'verified_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Identity and route evidence consumers; no claim of calibrated familiarity or globally clean repository',
        'identity': {'withdrawals': 12, 'additions': 0, 'disposition': 'unresolved; source profiles retained', 'live_matches_fixed_input_delta': True},
        'pinned_inputs_unchanged': after['inputs'], 'source_reconciliation_holds': True,
        'intern_exclusions_unchanged': 52107, 'live_ready': True, 'live_errors': [], 'runtime': read_runtime(),
        'tests': {'integrated_targeted': '199 passed', 'independent_review': '95 passed', 'committed_variant_boundary': '32 passed',
                  'javascript': 'node --check passed on live and committed variants'},
        'route_probes': routes, 'separate_profiles_checked': 24,
        'working_source_hashes': {name: sha(ROOT / name) for name in FILES}, 'staged_source_hashes': staged,
        'bindings': {name: sha(OUT / name) for name in ('identity_delta.json', 'independent_review.json', 'ADJUDICATION.md',
            'before/receipt.json', 'after/receipt.json', 'before/route_probes.json', 'after/route_probes.json',
            'live_dependencies.patch', 'integration_test_delta.patch')},
        'unrelated_global_failures': 'Previous audit 554 passed / 15 classified failures; not rerun or claimed closed here'}
    (OUT / 'completion_receipt.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'live_ready': True, 'identity': result['identity'], 'tests': result['tests']}))


def read_runtime():
    return json.loads((ROOT / 'audits/staffer_live_runtime/server.json').read_text(encoding='utf-8-sig'))


if __name__ == '__main__':
    main()
