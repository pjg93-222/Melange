"""Public-mode behavior fixtures; exact signed-package acceptance is separate."""
import hashlib
from collections import defaultdict
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from fec.surfaces import staffer_live_service as service_module
from fec.surfaces.staffer_contacts import ContactIndex
from fec.surfaces.test_staffer_live_service import fixture_graph, ProfilesFixture
from workspace_melange import MelangeBinding
from test_workspace_melange import Handler


class PublicPeople(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for folder in ('program','signed-data'):
            directory=self.root/folder;directory.mkdir()
            (directory/'immutable.json').write_bytes(b'{"sealed":true}')
        self.before=self.tree()
        graph=fixture_graph()
        names={ident:ident.replace('person:','person:hill:',1) for ident in graph.nodes if ident.startswith('person:')}
        graph.nodes={names.get(ident,ident):{**node,'id':names.get(ident,ident)} for ident,node in graph.nodes.items()}
        graph.edges=[{**edge,'source':names.get(edge['source'],edge['source']),'target':names.get(edge['target'],edge['target'])} for edge in graph.edges]
        graph.adjacency=defaultdict(list)
        for i,edge in enumerate(graph.edges):
            graph.adjacency[edge['source']].append(i);graph.adjacency[edge['target']].append(i)
        with patch.object(service_module,'ContactIndex',side_effect=lambda:ContactIndex(records=[])):
            self.service=service_module.LiveService(self.root/'signed-data',graph)
        self.service.profiles=ProfilesFixture()
        self.service.static.nodes['office:test']={'id':'office:test','kind':'container','container_kind':'member_office','label':'Fixture office'}
        self.service.static.reindex()
        self.service.evidence={'episodes':[],'user_assertions':[]}
        self.service.inventory={'sourcecoverage':{},'counts':{}}
        self.binding=object.__new__(MelangeBinding)
        self.binding.service=self.service
        self.binding.verify=lambda:True  # Fixture substitutes only the separately tested source/lease boundary.
        self.binding.prepared=SimpleNamespace(source={'manifestSha256':'a'*64})
        self.service._desktop_workspace_inputs=self.binding
        for name in ('load_coworker_assertions','load_identity_resolution','IdentityWebIndex',
                     'record_coworker_decision','record_identity_decision','resolve_identities'):
            p=patch.object(service_module,name,side_effect=AssertionError('Private read/write/discovery: '+name))
            p.start();self.addCleanup(p.stop)

    def tree(self):
        return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file()}

    def test_real_public_snapshot_search_groups_records_routes_without_private_reads_or_new_merges(self):
        s=self.service
        s._index_identity_candidates()
        # Even an accidentally supplied worker may not begin new discovery.
        s.identity_web=SimpleNamespace();s._resolve_automatic_identities();s.identity_web=None
        s._refresh_profiles(force=True);s.ready=True;s.stage='Ready'
        self.assertEqual(s.evidence['user_assertions'],None)
        self.assertEqual(s.identity_aliases,{})
        self.assertEqual({n['id'] for n in s.search('Gordon')['nodes']},{'person:hill:gordon','person:hill:other-gordon'})
        self.assertTrue(s.snapshot('Gordon')['nodes'])
        self.assertTrue(s.person('person:hill:gordon')['node']['provenance'])
        route=s.route('person:hill:gordon','person:hill:stephanie')
        self.assertTrue(route['found']);self.assertFalse(route['canonical_weights_changed'])
        index=json.loads(s.network_index(compressed=False)[0])
        self.assertGreater(index['total'],0)
        groups=json.loads(s.groups_index(compressed=False)[0])
        self.assertGreater(len(groups['offices']),0)
        caps=s.overview_status()['workspace_capabilities']
        self.assertEqual(caps['mode'],'signed-public-read-only')
        self.assertFalse(caps['privateOverlay']['loaded']);self.assertFalse(caps['privateOverlay']['validated'])
        self.assertIsNone(s.identity_resolution['counts']['user_confirmed_aliases'])
        self.assertEqual(self.before,self.tree())
        self.assertFalse((self.root/'signed-data/fec/surfaces/staffer_user_assertions.json').exists())

    def test_private_actions_refuse_before_lock_or_disk_or_thread_side_effects(self):
        s=self.service
        s.lock=None  # A guard after the lock would fail this regression.
        for call in (lambda:s.assertion_decision({}),lambda:s.identity_decision('a',['b'],'merge'),
                     s._rebuild_identity):
            with self.assertRaisesRegex(ValueError,'unavailable'):
                call()
        self.assertEqual(self.before,self.tree())

    def test_truthful_capability_endpoint_and_absent_assertions_response(self):
        handler=Handler('/api/staffer-capabilities')
        self.assertTrue(self.binding.handle_request(handler));self.assertEqual(handler.result['status'],200)
        self.assertTrue(json.loads(handler.wfile.getvalue())['supported']['publicModelRead'])
        handler=Handler('/api/staffer-assertions')
        self.assertTrue(self.binding.handle_request(handler));self.assertEqual(handler.result['status'],409)
        value=json.loads(handler.wfile.getvalue())
        self.assertIsNone(value['assertions']);self.assertEqual(value['code'],'private_overlay_unavailable')

    def test_signed_inventory_never_reads_private_path_and_rejects_private_groups(self):
        from fec.surfaces import staffer_person_inventory
        self.binding._module=service_module
        inventory={'nodes':{'person:fixture':{'id':'person:fixture','weight':7}},
                   'sources':[],'identity_groups':[],'identity_aliases':{}}
        self.binding.analytics=SimpleNamespace(content=SimpleNamespace(data={'references':{'inventory':inventory}}))
        with patch.object(staffer_person_inventory,'USER_ASSERTIONS',self.root/'private-canary.json'), \
             patch.object(staffer_person_inventory,'sha',side_effect=AssertionError('Private file read')):
            result=self.binding.public_inventory(self.service.static)
        self.assertEqual(result['nodes'],inventory['nodes'])
        self.assertEqual(result['raw_nodes'],inventory['nodes'])
        self.assertEqual(result['sources'],[])
        inventory['identity_groups']=[{'status':'USER_CONFIRMED_SAME_PERSON'}]
        with self.assertRaises(ValueError):self.binding.public_inventory(self.service.static)

    def test_flag_environment_or_other_service_cannot_grant_mode(self):
        s=self.service
        for forged in (SimpleNamespace(service=s,mode='signed-public-read-only'),
                       object.__new__(MelangeBinding)):
            if type(forged) is MelangeBinding:forged.service=object()
            s._desktop_workspace_inputs=forged
            with self.assertRaisesRegex(ValueError,'not a native workspace capability'):
                s._native_workspace()
        del s._desktop_workspace_inputs
        s.mode='signed-public-read-only'
        with patch.dict('os.environ',{'MELANGE_PUBLIC_MODE':'1'}):
            self.assertIsNone(s._native_workspace())


if __name__=='__main__':unittest.main()
