"""Native-only display projection, distinct from the full graph generation.

Parent verification is preserved as parent evidence. It never masquerades as
a twin-byte verification of the projected artifacts; the new receipt binds
those artifacts independently under the signed workspace channel.
"""
import hashlib
import json
from module_data_snapshot import Snapshot, exact, require
from melange_module_data import GRAPH_FILES, UPSTREAM
from workspace_data_contract import DISPLAY_GRAPH_KIND

_HEX = frozenset('0123456789abcdef')


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def sha(value):
    require(isinstance(value, str) and len(value) == 64 and not set(value) - _HEX)
    return value


class VerifiedDisplayInput:
    __slots__ = ('snapshot', 'receipt', 'verification', 'summary', '_files')

    def __init__(self, snapshot):
        require(type(snapshot) is Snapshot and snapshot.kind == DISPLAY_GRAPH_KIND and snapshot.app == 'melange')
        receipt, proof = snapshot.json('graph-receipt'), snapshot.json('graph-verification')
        exact(receipt, ('schemaVersion', 'kind', 'parent', 'projection', 'files'))
        require(type(receipt['schemaVersion']) is int and receipt['schemaVersion'] == 1 and receipt['kind'] == DISPLAY_GRAPH_KIND)
        exact(receipt['parent'], ('receipt', 'verification'))
        parents = {}
        for name in ('receipt', 'verification'):
            entry = receipt['parent'][name]
            exact(entry, ('originalSha256', 'projectedSha256', 'document'))
            sha(entry['originalSha256']); require(canonical_sha(entry['document']) == sha(entry['projectedSha256']))
            require(isinstance(entry['document'], dict))
            parents[name] = entry['document']
        parent, verification = parents['receipt'], parents['verification']
        require(parent.get('schema_id') == 'staffer-network-social-receipt-v1' and parent.get('status') == 'PASS')
        require(verification.get('schema_id') == 'staffer-network-social-verification-receipt-v1'
                and verification.get('status') == 'PASS' and not verification.get('failures'))
        require(not parent.get('canonical_employment_promotions') and not parent.get('canonical_identity_promotions'))
        checks = verification.get('twin_byte_identity')
        require(isinstance(checks, list) and all(isinstance(row, dict) for row in checks))
        checks = [row for row in checks if row.get('path') == 'staffer_social_network_receipt.json']
        require(len(checks) == 1 and checks[0].get('identical') is True
                and checks[0].get('primary_sha256') == checks[0].get('twin_sha256') == receipt['parent']['receipt']['originalSha256'])
        projection = receipt['projection']
        exact(projection, ('method', 'sourceRecords', 'displayRecords', 'sourceEdgesSha256', 'roleLocationProjection'))
        require(projection['roleLocationProjection'] == {'/nodes/*/label_provenance/path':'hill_member_office_index'})
        require(projection['method'] == 'first-10000-emitted-co-tenure-rows'
                and type(projection['displayRecords']) is int and 0 <= projection['displayRecords'] <= 10000
                and type(projection['sourceRecords']) is int and projection['sourceRecords'] >= 0
                and projection['displayRecords'] == min(10000, projection['sourceRecords']))
        source_files = parent.get('files')
        require(isinstance(source_files, list) and all(isinstance(row, dict) for row in source_files))
        require(len(source_files) == len(GRAPH_FILES) and {row.get('role') for row in source_files} == set(GRAPH_FILES))
        edge_sources = [row for row in source_files if row.get('role') == 'staffer_social_edges']
        require(len(edge_sources) == 1 and type(edge_sources[0].get('records')) is int
                and edge_sources[0].get('sha256') == sha(projection['sourceEdgesSha256'])
                and edge_sources[0].get('records') == projection['sourceRecords'])
        roles = set(snapshot.files) - {'graph-receipt', 'graph-verification'}
        exact(receipt['files'], roles)
        for role, spec in receipt['files'].items():
            exact(spec, ('sha256', 'bytes', 'records'))
            sha(spec['sha256']); require(type(spec['bytes']) is int and spec['bytes'] >= 0
                                       and type(spec['records']) is int and spec['records'] >= 0)
            snapshot.matches(role, spec)
        require(receipt['files']['edges']['records'] == projection['displayRecords'])
        exact(proof, ('schemaVersion', 'kind', 'status', 'failures', 'receiptSha256', 'comparisons', 'deterministicBuild'))
        require(type(proof['schemaVersion']) is int and proof['schemaVersion'] == 1
                and proof['kind'] == DISPLAY_GRAPH_KIND and proof['status'] == 'PASS'
                and proof['failures'] == [] and proof['receiptSha256'] == snapshot.objects['graph-receipt']['sha256'])
        exact(proof['comparisons'], ('nodeIds','edgeIds','searchRanks','pageBoundaries','layerCounts','sourceBounds'))
        require(all(value is True for value in proof['comparisons'].values()))
        exact(proof['deterministicBuild'], roles)
        require(all(value == receipt['files'][role]['sha256'] for role, value in proof['deterministicBuild'].items()))
        self.snapshot, self.receipt, self.verification, self._files = snapshot, parent, verification, receipt['files']
        self.summary = {**projection, 'schemaVersion': 1, 'kind': DISPLAY_GRAPH_KIND,
                        'parentReceiptSha256': receipt['parent']['receipt']['originalSha256'],
                        'parentVerificationSha256': receipt['parent']['verification']['originalSha256'],
                        'receiptSha256': snapshot.objects['graph-receipt']['sha256'],
                        'verificationSha256': snapshot.objects['graph-verification']['sha256'],
                        'fullGraphExport': False,
                        'verificationScope': 'Projected input integrity; numerical checks refer to the original full-generation parent.'}

    def layout(self, graph):
        require(getattr(graph, '_native_display', None) is self)
        graph.receipt, graph.verification = self.receipt, self.verification
        graph.display_projection = self.summary
        graph._verified(self.snapshot.files['graph-receipt'], self.snapshot.objects['graph-receipt'], 'graph_receipt')
        def artifact(name):
            require(name in GRAPH_FILES)
            role, _leaf = GRAPH_FILES[name]
            return graph._verified(self.snapshot.files[role], self._files[role], name)
        def upstream(name):
            require(name in UPSTREAM)
            role, _tail = UPSTREAM[name]
            return graph._verified(self.snapshot.files[role], self._files[role], name)
        return artifact, upstream
