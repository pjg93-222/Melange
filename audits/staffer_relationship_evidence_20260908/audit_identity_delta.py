"""Run both identity implementations on one source snapshot, without queue writes.

The ordinary source loader and its hash gates are retained. The web queue is
replaced with a SQLite read-only reader; startup stops before enqueue or any
background workers. This compares computation on fixed inputs, not name truth.
"""
import importlib.util
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from fec.surfaces import staffer_live_service as live
from fec.surfaces import staffer_identity_records as records
from fec.surfaces import staffer_identity_auto as current
from fec.surfaces.staffer_graph_snapshot import StaticGraph
from fec.surfaces.staffer_identity_web import actual_subject


class AuditComplete(BaseException):
    pass


class ReadOnlyReferences:
    def __init__(self, root):
        self.path = root / 'audits/staffer_live_runtime/identity_reference_v1.sqlite'
        with sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True) as db:
            documents = [json.loads(row[0]) for row in db.execute('SELECT payload FROM documents')]
            row = db.execute("SELECT value FROM metadata WHERE key='reference_revision'").fetchone()
            self._revision = row[0] if row else '0'
        self._references = [r for r in documents if actual_subject(r.get('text', ''), r.get('name', ''))]

    def revision(self):
        return self._revision

    def references(self):
        return self._references

    def enqueue_people(self, *args, **kwargs):
        raise AuditComplete()


def main():
    spec = importlib.util.spec_from_file_location('fec.surfaces.identity_before', OUT / 'before/fec/surfaces/staffer_identity_auto.py')
    before = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(before)
    captured = {}
    def resolve(nodes, episodes, references, confirmed, denied):
        print(f'Comparing {len(nodes)} nodes and {len(episodes)} episodes', flush=True)
        captured['before'] = before.resolve_identities(nodes, episodes, references, confirmed, denied, resolved_at='audit')
        captured['labels'] = {i: n.get('label') for i, n in nodes.items()}
        captured['counts'] = {'nodes': len(nodes), 'episodes': len(episodes), 'references': len(references),
                              'date_evidence': dict(Counter(e.get('date_evidence', 'not_specified') for e in episodes))}
        return current.resolve_identities(nodes, episodes, references, confirmed, denied, resolved_at='audit')

    consolidate = records.consolidate_record_pairs
    def combine(resolved, *args, **kwargs):
        with patch.object(records, 'compatible', before.compatible):
            old = consolidate(captured['before'], *args, **kwargs)
        new = consolidate(resolved, *args, **kwargs)
        a, b = old['identity_aliases'], new['identity_aliases']
        delta = {'status': 'PASS' if a == b else 'REVIEW_REQUIRED', 'counts': captured['counts'],
                 'automatic_aliases_before': len(a), 'automatic_aliases_after': len(b),
                 'aliases_removed': {k: v for k, v in a.items() if b.get(k) != v},
                 'aliases_added': {k: v for k, v in b.items() if a.get(k) != v},
                 'reference_revision': service.identity_web.revision()}
        touched = set(delta['aliases_removed']) | set(delta['aliases_added']) | set(delta['aliases_removed'].values()) | set(delta['aliases_added'].values())
        delta['affected_labels'] = {i: captured['labels'].get(i) for i in sorted(touched)}
        (OUT / 'identity_delta.json').write_text(json.dumps(delta, indent=2), encoding='utf-8')
        print(json.dumps(delta, indent=2), flush=True)
        return new

    service = live.LiveService(ROOT, StaticGraph(ROOT))
    with patch.object(live, 'IdentityWebIndex', ReadOnlyReferences), patch.object(live, 'resolve_identities', resolve), patch.object(live, 'consolidate_record_pairs', combine):
        try:
            service._run()
        except AuditComplete:
            pass
        else:
            raise RuntimeError({'stage': service.stage, 'errors': service.errors, 'reason': 'audit did not reach its explicit stop'})
    service.route_executor.shutdown(wait=False)


if __name__ == '__main__':
    main()
