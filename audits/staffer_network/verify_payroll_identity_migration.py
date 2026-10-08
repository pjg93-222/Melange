"""Independent, source-row-based verification of a payroll identity migration.

The sealed native bundle supplies unchanged employment facts; new spine source
rows supply identity assignments. No builder helpers or ID map are used to
derive expected identities. Split episodes are rejected unless rebuilt facts
can be reconstructed without inventing their interval boundaries.
"""
import argparse
import copy
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        yield from map(json.loads, stream)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked_sources(bundle):
    for source in bundle['sources']:
        require(sha(ROOT / source['path']) == source['sha256'], 'Source hash mismatch: ' + source['path'])


def row_owners(spans):
    result = {}
    for span in spans:
        for row in span['source_row_ids']:
            require(row not in result, 'Repeated source row: ' + row)
            result[row] = 'person:' + span['spine_person_id']
    return result


def expected_episodes(episodes, owners):
    """Map from row identities and union only exact service intervals.

    This migration's native v6 episodes each have a single v8 target. A future
    split inside one native episode needs independent raw-date reconstruction;
    copying its whole date range into each target is explicitly forbidden.
    """
    grouped = defaultdict(list)
    for person, employer, title, start, end, basis, rows in episodes:
        targets = {owners[row] for row in rows}
        require(len(targets) == 1, 'Native episode split requires raw date reconstruction')
        grouped[(next(iter(targets)), employer, title, basis)].append((start, end, rows))
    expected = []
    for (person, employer, title, basis), intervals in grouped.items():
        merged = []
        for start, end, rows in sorted(intervals):
            if merged and ((basis == 'printed_service_dates' and start <= merged[-1][1]) or
                           (basis == 'presence_within_report' and [start, end] == merged[-1][:2])):
                merged[-1][1] = max(end, merged[-1][1])
                merged[-1][2].extend(rows)
            else:
                merged.append([start, end, list(rows)])
        expected.extend([person, employer, title, start, end, basis, rows]
                        for start, end, rows in merged)
    return expected


def episode_counter(episodes):
    return Counter(json.dumps([*ep[:6], sorted(ep[6])], sort_keys=True) for ep in episodes)


def expected_pairs(pairs, owners):
    result = []
    collapsed = 0
    for old in pairs:
        pair = copy.deepcopy(old)
        for record in pair['records']:
            record['person_id'] = owners[record['row_id']]
        pair['records'].sort(key=lambda r: r['person_id'])
        pair['node_ids'] = [r['person_id'] for r in pair['records']]
        if len(set(pair['node_ids'])) == 1:
            collapsed += 1
        else:
            result.append(pair)
    return result, collapsed


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def pair_components(pairs):
    parent = {}
    def find(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node
    for pair in pairs:
        a, b = pair['node_ids']
        parent[find(a)] = find(b)
    return {node: find(node) for node in list(parent)}


def verify(old_pin, primary, twin, spine, migration, assertions, release, out):
    out = Path(out)
    require(not out.exists(), 'Verification output already exists')
    release_data = json.loads(Path(release).read_text())
    require(release_data['status'] == 'PASS' and release_data['generation'] == Path(spine).name,
            'Spine release is not verified for the requested generation')
    checked_sources(release_data)
    require(any(Path(s['path']).resolve() == Path(migration).resolve() and s['sha256'] == sha(migration)
                for s in release_data['sources']), 'Migration map is not bound by verified release')
    pin = json.loads(Path(old_pin).read_text())
    old_path = ROOT / pin['path']
    require(sha(old_path) == pin['sha256'], 'Native bundle pin mismatch')
    old = json.load(gzip.open(old_path, 'rt', encoding='utf-8'))
    new = json.load(gzip.open(primary, 'rt', encoding='utf-8'))
    checked_sources(old)
    checked_sources(new)
    require(sha(primary) == sha(twin), 'Primary/twin mismatch')
    receipt_path = Path(spine) / 'hill_personnel_spine_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    spans_path = Path(spine) / 'hill_person_office_spans.ndjson.gz'
    require(sha(spans_path) == receipt['files'][spans_path.name]['sha256'], 'Spine span hash mismatch')
    require(any(Path(s['path']).name == spans_path.name and s['sha256'] == sha(spans_path)
                for s in new['sources']), 'Bundle binds wrong spine spans')
    owners = row_owners(read(spans_path))
    old_owners = row_owners(read(ROOT / old['sources'][1]['path']))
    require(set(owners) == set(old_owners), 'Admitted source population changed')
    for episode in old['episodes']:
        require(all(old_owners[r] == episode[0] for r in episode[6]), 'Native episode source assignment mismatch')
    for pair in old['record_pairs']:
        require(all(old_owners[r['row_id']] == r['person_id'] for r in pair['records']), 'Native pair source assignment mismatch')
    expected = expected_episodes(old['episodes'], owners)
    require(episode_counter(expected) == episode_counter(new['episodes']), 'Employment fact/identity mismatch')
    pairs, collapsed = expected_pairs(old['record_pairs'], owners)
    require(Counter(json.dumps(p, sort_keys=True) for p in pairs) ==
            Counter(json.dumps(p, sort_keys=True) for p in new['record_pairs']), 'Record pair fact/identity mismatch')
    require(all(owners[r] == e[0] for e in new['episodes'] for r in e[6]), 'New episode crosses identities')
    require(all(owners[r['row_id']] == r['person_id'] for p in new['record_pairs'] for r in p['records']), 'New pair crosses identities')
    for key in ('source_rows_read', 'rows_not_admitted_by_spine', 'invalid_or_absent_service_dates'):
        require(new['counts'][key] == old['counts'][key], 'Source count drift: ' + key)
    require(new['counts']['episodes'] == len(new['episodes']) and
            new['counts']['employment_people'] == len({e[0] for e in new['episodes']}) and
            new['counts']['record_pairs'] == len(new['record_pairs']), 'Bundle counts mismatch')
    native_raw = {str(Path(s['path']).resolve()): s['sha256'] for s in old['sources'][2:]}
    new_raw = {str(Path(s['path']).resolve()): s['sha256'] for s in new['sources'][2:]}
    require(native_raw == new_raw, 'Underlying payroll sources changed')
    split_targets = [{'old': r['source_person_id'], 'targets': r['target_person_ids']}
                     for r in read(migration) if r['relation'] == 'SPLIT_REQUIRES_SOURCE_ROW']
    components = pair_components(new['record_pairs'])
    for split in split_targets:
        nodes = ['person:' + t for t in split['targets']]
        require(len({components.get(n, n) for n in nodes}) == len(nodes), 'Undated split remerged by pair evidence')
        split['episode_counts'] = {t: sum(e[0] == 'person:' + t for e in new['episodes']) for t in split['targets']}
    assertion_data = json.loads(Path(assertions).read_text())
    hill_ids = sorted({s for s in strings(assertion_data) if s.startswith(('hill:person:', 'person:hill:person:'))})
    require(not hill_ids, 'Hill assertions require explicit migration adjudication')
    sources = [old_pin, old_path, primary, twin, receipt_path, spans_path, migration, assertions, release,
               Path(__file__), Path(__file__).with_name('rebuild_payroll_identity.py'),
               ROOT / 'fec/surfaces/staffer_identity_auto.py', ROOT / 'fec/surfaces/staffer_payroll_identity.py']
    report = {'status': 'PASS', 'method': 'INDEPENDENT_SOURCE_ROW_REASSIGNMENT_OF_SEALED_NATIVE_FACTS',
              'generation': Path(spine).name, 'counts': new['counts'],
              'native_counts': old['counts'], 'native_pair_collapses': collapsed,
              'native_episode_identity_changes': sum(len({owners[r] for r in e[6]}) == 1 and owners[e[6][0]] != e[0]
                                                     for e in old['episodes']),
              'admitted_source_rows': len(owners), 'split_checks': split_targets,
              'user_assertions': {'status': 'UNCHANGED_LDA_ONLY', 'hill_id_references': hill_ids},
              'canonical_promotions': 0, 'live_selector_changed': False,
              'sources': [{'path': str(Path(p).resolve()), 'sha256': sha(p)} for p in sources]}
    out.mkdir(parents=True)
    (out / 'payroll_identity_migration_receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    replacement = {'version': new['version'], 'path': str(Path(primary).resolve().relative_to(ROOT)), 'sha256': sha(primary)}
    (out / 'staffer_payroll_identity.proposed.json').write_text(json.dumps(replacement, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('old-pin', 'primary', 'twin', 'spine', 'migration', 'assertions', 'release', 'out'):
        parser.add_argument('--' + key, required=True, type=Path)
    verify(**vars(parser.parse_args()))
