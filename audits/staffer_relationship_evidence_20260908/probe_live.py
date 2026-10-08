"""Bounded real-user route probes and identity split verification."""
import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))
from capture import get


def query(endpoint, **params):
    return get(endpoint + '?' + urllib.parse.urlencode(params))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['before', 'after'])
    phase = parser.parse_args().phase
    index = json.loads((OUT / 'before/index.json').read_text(encoding='utf-8'))
    named = {row[1].casefold(): row[0] for row in index['people']}
    pairs = [('Gordon Holzberg', 'Stephanie Belk', 'overlap_balanced'),
             ('Gordon Holzberg', 'Gregory Mesack', 'overlap_balanced'),
             ('Gordon Holzberg', 'Grace Ryan', 'overlap_fewest_steps')]
    probes = []
    for a, b, objective in pairs:
        result = query('/api/staffer-route', origin=named[a.casefold()], target=named[b.casefold()],
            objective=objective, include_user_asserted=1, include_policy=1, **{'async': 1})
        deadline = time.monotonic() + 240
        while result.get('status') in ('searching', 'queued'):
            assert time.monotonic() < deadline, 'Route probe timeout'
            time.sleep(.5)
            result = query('/api/staffer-route-result', id=result['search_id'])
        assert result.get('ready') and result.get('optimal'), result.get('status')
        if phase == 'after':
            assert result['strength_model'] == 'ordered-person-overlap-v5-dated-work'
            assert not result['personal_familiarity_established']
            for hop in result.get('hops', []):
                assert not hop['personal_familiarity_established']
                if hop['evidence_class'] == 'shared_background_only':
                    assert not hop['temporal_overlap_established'] and hop['temporal_status'] == 'overlap_unconfirmed'
                if hop['evidence_class'] == 'observed_report_core_overlap':
                    assert hop['modeled_overlap'] and not hop['temporal_overlap_established']
                    assert hop['work_evidence']['overlap_duration_days'] is None
        probes.append({'origin_label': a, 'target_label': b, 'result': result})
        print(a, '->', b, result['status'], result.get('steps'), flush=True)
    receipt = {'phase': phase, 'routes': probes}
    if phase == 'after':
        delta = json.loads((OUT / 'identity_delta.json').read_text(encoding='utf-8'))
        ids = set(delta['aliases_removed']) | set(delta['aliases_removed'].values())
        checked = []
        for ident in sorted(ids):
            result = query('/api/staffer-person', id=ident)
            assert result['ready'] and result['node']['id'] == ident, ident
            assert not result['node'].get('canonical_eligible')
            checked.append({'id': ident, 'label': result['node']['label']})
        receipt['separate_source_profiles'] = checked
        with urllib.request.urlopen('http://127.0.0.1:8841/staffer-live/staffer-route.js') as response:
            script = response.read()
        assert script == (ROOT / 'fec/surfaces/staffer_live/staffer-route.js').read_bytes()
        assert b'Connection strength:' not in script and b'Shared-background score:' in script
        receipt['served_javascript_sha256'] = hashlib.sha256(script).hexdigest()
    (OUT / f'{phase}/route_probes.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
