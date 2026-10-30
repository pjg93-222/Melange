import copy
import json
import tempfile
import unittest

from module_data_snapshot import Snapshot, load_source
from module_data_test_helpers import graph_fixture
from workspace_data_contract import DISPLAY_GRAPH_KIND
from workspace_graph import VerifiedDisplayInput, canonical_sha


def fixture(directory):
    result = graph_fixture(directory)
    parent = json.loads(result.path('graph-receipt').read_bytes())
    for entry in parent['files']:
        entry['records'] = {'staffer_social_edges':1,'staffer_social_node_scores':2}.get(entry['role'],0)
    result.write('graph-receipt',parent)
    original_hash=result.spec('graph-receipt')['sha256']
    verification=json.loads(result.path('graph-verification').read_bytes())
    verification['twin_byte_identity'][0].update(primary_sha256=original_hash,twin_sha256=original_hash)
    result.write('graph-verification',verification)
    verification_hash=result.spec('graph-verification')['sha256']
    result.kind=result.request['kind']=DISPLAY_GRAPH_KIND
    files={role:{**{key:result.spec(role)[key] for key in ('bytes','sha256')},
                 'records':{'edges':1,'node-scores':2}.get(role,0)}
           for role in result.request['files'] if role not in ('graph-receipt','graph-verification')}
    projected={'schemaVersion':1,'kind':DISPLAY_GRAPH_KIND,
        'parent':{'receipt':{'originalSha256':original_hash,'projectedSha256':canonical_sha(parent),'document':parent},
                  'verification':{'originalSha256':verification_hash,'projectedSha256':canonical_sha(verification),'document':verification}},
        'projection':{'method':'first-10000-emitted-co-tenure-rows','sourceRecords':1,'displayRecords':1,
                      'roleLocationProjection':{'/nodes/*/label_provenance/path':'hill_member_office_index'},
                      'sourceEdgesSha256':result.spec('edges')['sha256']},'files':files}
    result.write('graph-receipt',projected)
    proof={'schemaVersion':1,'kind':DISPLAY_GRAPH_KIND,'status':'PASS','failures':[],
        'receiptSha256':result.spec('graph-receipt')['sha256'],
        'comparisons':dict.fromkeys(('nodeIds','edgeIds','searchRanks','pageBoundaries','layerCounts','sourceBounds'),True),
        'deterministicBuild':{role:spec['sha256'] for role,spec in files.items()}}
    result.write('graph-verification',proof)
    return result


class DisplayGraphTests(unittest.TestCase):
    def test_real_static_graph_uses_verified_projection_without_relabelling_parent_twin(self):
        with tempfile.TemporaryDirectory() as directory:
            f=fixture(directory);snapshot=Snapshot(f.request);display=VerifiedDisplayInput(snapshot)
            source=load_source(snapshot.source_file('fec/surfaces/staffer_graph_snapshot.py'))
            graph=source.StaticGraph('/never-read-original-workspace',display_input=display)
            graph.load()
            self.assertEqual(graph.errors,[])
            self.assertEqual(set(graph.nodes),{'person:fixture1','person:fixture2'})
            self.assertEqual(graph.root.as_posix(),'/never-read-original-workspace/audits/staffer_network')
            result=graph.view('',20)
            self.assertFalse(result['display_projection']['fullGraphExport'])
            self.assertNotEqual(display.summary['parentReceiptSha256'],display.summary['receiptSha256'])
            self.assertEqual(graph.verification['twin_byte_identity'][0]['primary_sha256'],display.summary['parentReceiptSha256'])
            self.assertEqual(result['bounds']['co_tenure_sample_rows'],10000)

    def test_foreign_input_parent_relabelling_bool_counts_and_incomplete_parity_rejected(self):
        for change in ('parent','count','comparison'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                f=fixture(directory)
                if change=='comparison':
                    proof=json.loads(f.path('graph-verification').read_bytes());proof['comparisons']={'arbitrary':True}
                    f.write('graph-verification',proof)
                else:
                    receipt=json.loads(f.path('graph-receipt').read_bytes())
                    if change=='parent':receipt['parent']['receipt']['originalSha256']='a'*64
                    else:receipt['projection']['displayRecords']=True
                    f.write('graph-receipt',receipt)
                with self.assertRaises(ValueError):VerifiedDisplayInput(Snapshot(f.request))
        with tempfile.TemporaryDirectory() as directory:
            f=fixture(directory);snapshot=Snapshot(f.request)
            source=load_source(snapshot.source_file('fec/surfaces/staffer_graph_snapshot.py'))
            with self.assertRaises(ValueError):source.StaticGraph('/unused',display_input={'path':'untrusted'})


if __name__=='__main__':unittest.main()
