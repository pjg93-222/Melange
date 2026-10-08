"""Read-only verification of the published v8 staffer consumers and live service."""
import gzip
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fec.surfaces.melange_dashboard import integrate
OUT = Path(__file__).resolve().parent
GENERATION = 'staffer_social_network_20260908_v8_math_primary'
SPINE = 'hill_personnel_spine_20260908_v8_primary'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def get(endpoint):
    with urllib.request.urlopen('http://127.0.0.1:8841' + endpoint, timeout=90) as response:
        return json.load(response)


def refs(value):
    found = set()
    if isinstance(value, str) and value.startswith('person:hill:person:'):
        found.add(value)
    elif isinstance(value, dict):
        for key, child in value.items():
            found.update(refs(key))
            found.update(refs(child))
    elif isinstance(value, list):
        for child in value:
            found.update(refs(child))
    return found


def main():
    with gzip.open(ROOT / 'audits/staffer_network' / SPINE / 'hill_person_spine.ndjson.gz', 'rt', encoding='utf-8') as stream:
        ids = {'person:' + json.loads(line)['spine_person_id'] for line in stream if line.strip()}
    assert len(ids) == 144692
    checks = {}
    performance = get('/api/staffer-performance')
    assert performance['ready'] and not performance['errors']
    payroll = performance['metrics']['payroll_identity']
    assert (payroll['episodes'], payroll['employment_people'], payroll['record_pairs']) == (425825, 135039, 231)
    checks['ready'] = True
    checks['payroll_counts'] = payroll
    snapshot = get('/api/staffer-live?limit=50')
    graph_source = next(s for s in snapshot['sources'] if s['role'] == 'graph_receipt')
    expected = ROOT / 'audits/staffer_network' / GENERATION / 'staffer_social_network_receipt.json'
    assert Path(graph_source['path']) == expected and graph_source['sha256'] == sha(expected)
    checks['graph_receipt'] = graph_source
    index = get('/api/staffer-network-index?scope=network')
    assert index['ready'] and index['complete_inventory'] and index['reconciliation']['balance_holds']
    id_column = index['fields'].index('id')
    live_ids = {row[id_column] for row in index['people']}
    alias_ids = refs(index['identity_aliases'])
    live_payroll_ids = {key for key in live_ids if key.startswith('person:hill:person:')}
    assert not (live_payroll_ids | alias_ids) - ids
    assert ids <= live_payroll_ids | alias_ids
    checks['network_inventory'] = {'people': len(live_ids), 'payroll_profiles': len(live_payroll_ids),
                                   'payroll_ids_in_profiles_or_aliases': len(live_payroll_ids | alias_ids),
                                   'invalid_payroll_ids': [], 'reconciliation': index['reconciliation']}
    groups = get('/api/staffer-groups-index')
    group_ids = refs(groups)
    assert groups['ready'] and not group_ids - ids
    checks['live_groups'] = {'counts': groups['counts'], 'distinct_payroll_ids': len(group_ids), 'invalid_payroll_ids': []}
    migration = json.loads((ROOT / 'audits/staffer_network/payroll_identity_20260908_v8_verification_final/payroll_identity_migration_receipt.json').read_text())
    split_checks = []
    for split in migration['split_checks']:
        targets = {'person:' + value for value in split['targets']}
        returned = []
        for target in sorted(targets):
            person = get('/api/staffer-person?' + urllib.parse.urlencode({'id': target}))
            node = person['node']
            assert person['ready'] and node['id'] == target
            assert not node['canonical_eligible'] and not node['canonical_employment_promoted']
            assert GENERATION in node['provenance']['path'] and SPINE in node['provenance']['identity_path']
            assert not refs(person) - ids
            returned.append({'id': node['id'], 'label': node['label'], 'ranking_math_version': node['ranking_math_version'],
                             'source': node['provenance'], 'stints': len(node.get('stints', []))})
        assert {row['id'] for row in returned} == targets
        split_checks.append({'old': split['old'], 'distinct_targets': returned})
    checks['preserved_splits'] = split_checks
    consumer = json.loads((OUT / 'v8_consumer_validation.json').read_text())
    published = []
    for entry in consumer['files']:
        path = ROOT / 'data/engine' / Path(entry['path']).name
        assert sha(path) == entry['sha256']
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['meta']['generation'] == GENERATION and not refs(data) - ids
        published.append({'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size})
    checks['published_data'] = published
    decoder = json.JSONDecoder()
    pages = []
    for name in ('staffer-network.html', 'Moneyball_Redesign.html'):
        path = ROOT / name
        html = path.read_text(encoding='utf-8')
        islands = {}
        for variable in ('SDATA', 'GDATA', 'ODATA', 'CDATA'):
            matches = list(re.finditer(r'\bconst\s+' + variable + r'\s*=\s*', html))
            assert len(matches) == 1, (name, variable, len(matches))
            data, _ = decoder.raw_decode(html, matches[0].end())
            assert data['meta']['generation'] == GENERATION and not refs(data) - ids
            islands[variable] = {'generation': data['meta']['generation'], 'distinct_payroll_ids': len(refs(data))}
        pages.append({'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size, 'data_islands': islands})
    with urllib.request.urlopen('http://127.0.0.1:8841/Moneyball.html', timeout=90) as response:
        digest = hashlib.sha256()
        count = 0
        for block in iter(lambda: response.read(1024 * 1024), b''):
            digest.update(block)
            count += len(block)
    expected_response = integrate((ROOT / 'Moneyball_Redesign.html').read_bytes(),
                                  (ROOT / 'cu-member-desk-profiles.js').read_bytes())
    assert digest.hexdigest() == hashlib.sha256(expected_response).hexdigest()
    assert b'<script src="/cu-member-desk-profiles.js"></script>' in expected_response
    with urllib.request.urlopen('http://127.0.0.1:8841/cu-member-desk-profiles.js', timeout=90) as response:
        profile_digest = hashlib.sha256()
        for block in iter(lambda: response.read(1024 * 1024), b''):
            profile_digest.update(block)
    assert profile_digest.hexdigest() == sha(ROOT / 'cu-member-desk-profiles.js')
    checks['published_pages'] = pages
    checks['http_dashboard'] = {'url': 'http://127.0.0.1:8841/Moneyball.html', 'served_file': 'Moneyball_Redesign.html',
                                 'sha256': digest.hexdigest(), 'bytes': count,
                                 'transform': 'Local navigation shell and identical member profiles served as a sibling script',
                                 'member_profiles_sha256': profile_digest.hexdigest()}
    result = {'status': 'PASS', 'checked_at': datetime.now(timezone.utc).isoformat(), 'generation': GENERATION,
              'spine': SPINE, 'checks': checks,
              'limitations': ['Historical source-ID provenance is preserved; invalid current v8 IDs are rejected.',
                              'Canonical Moneyball.html is locked by Carbonite; the live route serves the verified Moneyball_Redesign.html.']}
    (OUT / 'live_cutover_validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'generation': GENERATION, 'checks': list(checks)}))


if __name__ == '__main__':
    main()
