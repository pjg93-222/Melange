"""Fixed route and transport regressions; not full native installation proof."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from module_data_snapshot import validate_snapshot,KINDS
from workspace_data_contract import INDUSTRY_PAGES_KIND,INDUSTRY_MEMBERS
from workspace_melange import MelangeBinding,_InputPath


class Handler:
    def __init__(self,path):self.path=path;self.headers={};self.result={};self.wfile=io.BytesIO()
    def send_response(self,status):self.result['status']=status
    def send_error(self,status):self.result['status']=status
    def send_header(self,name,value):self.result[name]=value
    def end_headers(self):pass


class Routes(unittest.TestCase):
    def invoke(self,path):
        # Exercise compiled routing only. Owner/lease installation is tested at
        # the separate real native boundary, not fabricated by this fixture.
        binding=object.__new__(MelangeBinding);binding.verify=lambda:True
        handler=Handler(path);self.assertTrue(binding.handle_request(handler));return handler.result

    def test_exact_member_and_staffer_tabs_keep_encoded_selector(self):
        cases={'/cu-member-desk.html?m=A%26B':'/?view=profile&m=A%26B',
               '/cu-member-desk.html':'/?view=members',
               '/staffer-network.html?s=A%20B':'/?view=people&s=A+B',
               '/staffer-network.html':'/?view=people',
               '/Moneyball%20Dashboard.html':'/?view=influence',
               '/Moneyball.html':'/',
               '/Moneyball.html?m=A%26B':'/?m=A%26B',
               '/Moneyball.html?v=staffer&s=A%20B':'/?v=staffer&s=A+B',
               '/Moneyball.html?v=industry':'/?v=industry'}
        for request,target in cases.items():
            with self.subTest(request=request):
                result=self.invoke(request);self.assertEqual(result['status'],302);self.assertEqual(result['Location'],target)

    def test_selector_cannot_change_redirect_origin_or_smuggle_headers(self):
        result=self.invoke('/staffer-network.html?s=https%3A%2F%2Fevil%2Fx%0D%0AX-Test%3Ayes')
        self.assertTrue(result['Location'].startswith('/?view=people&s='))
        self.assertNotIn('\r',result['Location']);self.assertNotIn('\n',result['Location'])
        self.assertEqual(self.invoke('/cu-member-desk.html?m=A&m=B')['status'],400)
        self.assertEqual(self.invoke('/staffer-network.html?s='+'a'*257)['status'],400)
        self.assertEqual(self.invoke('/Moneyball.html?m=A&m=B')['status'],400)
        self.assertEqual(self.invoke('/Moneyball.html?v=A&v=B')['status'],400)
        legacy=self.invoke('/Moneyball.html?m=https%3A%2F%2Fevil%2Fx%0D%0AX-Test%3Ayes')
        self.assertTrue(legacy['Location'].startswith('/?m='))
        self.assertNotIn('\r',legacy['Location']);self.assertNotIn('\n',legacy['Location'])

    def test_role_path_view_cannot_select_an_uncompiled_sibling_or_write(self):
        slot=_InputPath(Path('fixed.sqlite'),Path('receipt.json'),{})
        with self.assertRaises(ValueError):slot.with_suffix('.py')
        with self.assertRaises(ValueError):slot.open('wb')


class Preflight(unittest.TestCase):
    def make(self,root,*,wrong_inner=False):
        source=root/'source';source.mkdir();snapshot=root/'snapshot';snapshot.mkdir()
        path=snapshot/'industry/pages.data.zip';path.parent.mkdir()
        values={name:b'{"testOnly":true}' for name in INDUSTRY_MEMBERS if name!='derivation.json'}
        members={name:{'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in values.items()}
        if wrong_inner:members['champions.json']['sha256']='0'*64
        values['derivation.json']=json.dumps({'schemaVersion':1,'members':members}).encode()
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as output:
            for name,value in sorted(values.items()):output.writestr(name,value)
        raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        return {'appId':'melange','kind':INDUSTRY_PAGES_KIND,'sourceRoot':str(source),'snapshotRoot':str(snapshot),
                'files':{'pages':str(path)},'objects':[{'role':'pages','bytes':len(raw),'sha256':sha,
                'segments':[{'asset':'test-only.zip','bytes':len(raw),'sha256':sha}]}]}

    def test_new_workspace_kind_uses_closed_readonly_preflight(self):
        with tempfile.TemporaryDirectory(prefix='workspace preflight ') as folder:
            request=self.make(Path(folder));before=set(Path(folder).rglob('*'))
            self.assertTrue(validate_snapshot(request)['validated'])
            self.assertEqual(before,set(Path(folder).rglob('*')))

    def test_outer_hash_does_not_authorize_a_false_inner_roster(self):
        with tempfile.TemporaryDirectory(prefix='workspace preflight ') as folder:
            with self.assertRaises(ValueError):validate_snapshot(self.make(Path(folder),wrong_inner=True))


class NativeActivity(unittest.TestCase):
    def run_service(self,mode):
        sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
        try:from fec.surfaces import staffer_live_service as module
        finally:sys.path.pop(0)
        calls=[]
        class Missing:
            def is_file(self):return False
        class ActivityPath:
            def is_file(self):
                calls.append('original-activity-io')
                if mode!='legacy':raise AssertionError('Original activity path must not be read')
                return False
        class Root:
            def __truediv__(self,_value):return ActivityPath()
        service=module.LiveService.__new__(module.LiveService)
        service.source_root=Root();service.metrics={};service.errors=[]
        service.source_catalog=None;service.lda_catalog=None
        service.static=SimpleNamespace(load=lambda:None,reindex=lambda:None,errors=[],load_seconds=0,nodes={},edges=[])
        service._stop=SimpleNamespace(wait=lambda *_args:True)
        service._load_lda_employment=lambda:None;service._load_lda_sidecar=lambda:None
        service._cache_source_inventory=lambda:None;service._apply_inventory=lambda:None
        service._index_identity_candidates=lambda:None
        def stop(*_args,**_kwargs):raise RuntimeError('Stopped after activity selection')
        service._refresh_profiles=stop
        if mode!='legacy':
            binding=object.__new__(MelangeBinding) if mode!='forged' else SimpleNamespace()
            binding.service=service if mode!='other-service' else object()
            def activity(nodes):
                calls.append('native-activity');return SimpleNamespace(receipt={'counts':{'source_person_ids':7}})
            binding.activity_index=activity;service._desktop_workspace_inputs=binding
            binding.public_capabilities=lambda:{'mode':'signed-public-read-only'}
        with patch.object(module,'CATALOG',Missing()),patch.object(module,'LDA_CATALOG',Missing()), \
             patch.object(module,'load_evidence',return_value={}),patch.object(module,'load_inventory',return_value={}), \
             patch.object(module,'IdentityWebIndex',return_value=None):
            module.LiveService._run(service)
        return service,calls

    def test_native_activity_uses_only_its_closed_slot(self):
        service,calls=self.run_service('native')
        self.assertEqual(calls,['native-activity'])
        self.assertEqual(service.startup_error,'Stopped after activity selection')
        self.assertEqual(service.inventory['sourcecoverage']['lda']['routing_activity_source_ids'],7)

    def test_forged_and_other_service_capabilities_are_rejected(self):
        for mode in ('forged','other-service'):
            service,calls=self.run_service(mode)
            self.assertEqual(calls,[])
            self.assertIn('not a native workspace capability',service.startup_error)

    def test_legacy_unbound_activity_selection_is_preserved(self):
        service,calls=self.run_service('legacy')
        self.assertEqual(calls,['original-activity-io','original-activity-io'])
        self.assertIn('Complete LDA activity routing index unavailable; only indexed evidence is routable',service.errors)
        self.assertEqual(service.startup_error,'Stopped after activity selection')


if __name__=='__main__':unittest.main()
