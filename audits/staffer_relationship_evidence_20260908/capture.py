"""Read-only, reproducible baseline/live comparison for the evidence audit."""
import argparse
import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FILES = [
    'fec/surfaces/staffer_identity_auto.py',
    'fec/surfaces/staffer_payroll_identity.py',
    'fec/surfaces/staffer_overlap_routes.py',
    'fec/surfaces/staffer_routing.py',
    'fec/surfaces/staffer_live_service.py',
    'fec/surfaces/staffer_live/staffer-route.js',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def get(endpoint):
    with urllib.request.urlopen('http://127.0.0.1:8841' + endpoint, timeout=60) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['before', 'after'])
    args = parser.parse_args()
    folder = OUT / args.phase
    folder.mkdir(exist_ok=False)
    receipt = {'time': datetime.now(timezone.utc).isoformat(),
               'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'files': {}, 'inputs': {}}
    for name in FILES:
        content = (ROOT / name).read_bytes()
        dest = folder / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        receipt['files'][name] = sha(content)
    for name in ('staffer_payroll_identity.json',):
        path = ROOT / 'fec/surfaces' / name
        receipt['inputs'][str(path.relative_to(ROOT))] = sha(path.read_bytes())
    for generation, pattern in (
        ('hill_personnel_spine_20260908_v8_primary', '*receipt*.json'),
        ('staffer_social_network_20260908_v8_math_primary', '*receipt*.json'),
        ('payroll_identity_20260908_v8_primary', '*receipt*.json')):
        for path in (ROOT / 'audits/staffer_network' / generation).glob(pattern):
            receipt['inputs'][str(path.relative_to(ROOT))] = sha(path.read_bytes())
    performance = get('/api/staffer-performance')
    assert performance['ready'] and not performance['errors'], performance
    receipt['performance'] = performance
    index = get('/api/staffer-network-index?scope=network')
    assert index['ready'] and index['complete_inventory'] and index['reconciliation']['balance_holds']
    (folder / 'index.json').write_text(json.dumps(index), encoding='utf-8')
    receipt['inventory'] = {'people': len(index['people']), 'aliases': len(index['identity_aliases']),
                            'reconciliation': index['reconciliation']}
    if args.phase == 'after':
        before = json.loads((OUT / 'before/receipt.json').read_text(encoding='utf-8'))
        old_index = json.loads((OUT / 'before/index.json').read_text(encoding='utf-8'))
        receipt['inputs_unchanged'] = before['inputs'] == receipt['inputs']
        old_alias, new_alias = old_index['identity_aliases'], index['identity_aliases']
        receipt['aliases_removed'] = {k: v for k, v in old_alias.items() if new_alias.get(k) != v}
        receipt['aliases_added'] = {k: v for k, v in new_alias.items() if old_alias.get(k) != v}
    (folder / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('files', 'performance')}, indent=2))


if __name__ == '__main__':
    main()
