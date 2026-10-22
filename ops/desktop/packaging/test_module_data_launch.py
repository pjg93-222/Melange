"""Launch protocol fixtures only: no original datasets, models or calculations."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import uuid

from module_data_snapshot import KINDS, Snapshot
from module_data_launch import APPS, canonical, prepare_module_readers


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve()
        self.profile=self.base/'profile';self.profile.mkdir()
        self.code=self.base/'program';self.code.mkdir()
        self.data=self.base/'original-data';self.data.mkdir()
        self.state=self.profile/'state';self.state.mkdir()
        self.account=self.state/'account.fixture';self.account.write_bytes(b'original account state')
        self.output=self.data/'report-output.fixture';self.output.write_bytes(b'original output')
        self.make('mentat')

    def make(self, app_id, role_bytes=None):
        self.app=app_id;repository,purpose=APPS[app_id]
        self.cache=self.profile/'packs/github-module-data'
        if self.cache.exists():shutil.rmtree(self.cache)
        for leaf in ('pointers','manifests','snapshots'):(self.cache/leaf).mkdir(parents=True,exist_ok=True)
        self.manifest={'schemaVersion':1,'purpose':purpose+'sets','appId':app_id,'repository':repository,
                       'releaseTag':'module-data-2026-10-21-fixture','datasets':[]}
        self.contents={}
        for index,(kind,(app,roles)) in enumerate(KINDS.items()):
            if app!=app_id:continue
            objects=[]
            for role,(_relative,_limit) in roles.items():
                raw=(role_bytes or {}).get((kind,role),('synthetic '+role).encode())
                objects.append({'role':role,'bytes':len(raw),'sha256':sha(raw),
                                'segments':[{'asset':f'part-{index}-{role}.bin','bytes':len(raw),'sha256':sha(raw)}]})
                self.contents[(kind,role)]=raw
            self.manifest['datasets'].append({'datasetId':str(uuid.uuid4()),'revisionId':str(uuid.uuid4()),
                'kind':kind,'adapterVersion':1,'objects':objects,'counts':{'files':len(roles)}})
        self.pointer={'schemaVersion':1,'purpose':purpose,'appId':app_id,'repository':repository,
                      'catalogSequence':1,'releaseTag':self.manifest['releaseTag'],'releaseCommit':'a'*40,'manifest':{}}
        self.snapshot=None;self.rebind()
        self.options={'app_id':app_id,'profile':str(self.profile),'source_root':str(self.code),
            'original_data_root':str(self.data),'state_root':str(self.state),'source':self.source,'native_verified':True}

    def rebind(self, raw_manifest=None, raw_payload=None):
        raw_manifest=canonical(self.manifest) if raw_manifest is None else raw_manifest
        self.pointer['manifest']={'asset':'manifest.json','bytes':len(raw_manifest),'sha256':sha(raw_manifest)}
        raw_payload=canonical(self.pointer) if raw_payload is None else raw_payload
        envelope={'schemaVersion':1,'keyId':'synthetic-native-key','payload':base64.b64encode(raw_payload).decode(),
                  'signature':base64.b64encode(b'\0'*64).decode()}
        self.source={'schemaVersion':1,'appId':self.app,'repository':APPS[self.app][0],'catalogSequence':1,
            'releaseTag':self.pointer['releaseTag'],'releaseCommit':self.pointer['releaseCommit'],
            'pointerDigest':sha(raw_payload),'manifestSha256':sha(raw_manifest),'cacheRoot':str(self.cache)}
        self.envelope=self.cache/'pointers'/(sha(raw_payload)+'.json');self.envelope.write_bytes(canonical(envelope))
        (self.cache/'manifests'/(sha(raw_manifest)+'.json')).write_bytes(raw_manifest)
        old=self.snapshot;self.snapshot=self.cache/'snapshots'/sha(raw_manifest)
        if not self.snapshot.exists():
            if old is not None:shutil.copytree(old,self.snapshot)
            else:
                for dataset in self.manifest['datasets']:
                    for role,(relative,_limit) in KINDS[dataset['kind']][1].items():
                        p=self.snapshot/dataset['datasetId']/relative;p.parent.mkdir(parents=True,exist_ok=True)
                        p.write_bytes(self.contents[(dataset['kind'],role)])
        if hasattr(self,'options'):self.options['source']=self.source

    def configured(self, request):
        Snapshot(request)
        return {'appId':request['appId'],'kind':request['kind'],
                'coverage':{'completeKind':True,'fullApplication':False},'fixture_reader':lambda:'synthetic'}

    def launch(self, **changes):
        with patch('melange_module_data.configure_readers',side_effect=self.configured),patch('mentat_module_data.configure_readers',side_effect=self.configured):
            return prepare_module_readers(**{**self.options,**changes})

    def role(self):
        dataset=self.manifest['datasets'][0];relative=next(iter(KINDS[dataset['kind']][1].values()))[0]
        return self.snapshot/dataset['datasetId']/relative

    def inventory(self):
        return [(p.relative_to(self.base).as_posix(),p.stat().st_size,p.stat().st_mtime_ns,sha(p.read_bytes()))
                for p in sorted(self.base.rglob('*')) if p.is_file()]

    def test_both_app_compiled_closures_are_read_only_and_accurately_native_verified(self):
        for app in APPS:
            self.make(app);before=self.inventory();source=copy.deepcopy(self.source)
            result=self.launch()
            self.assertEqual(result['signatureVerification'],'native-js')
            self.assertEqual(result['coverage'],{'completeKind':True,'fullApplication':False})
            self.assertEqual(set(result['readers']),{kind for kind,(owner,_roles) in KINDS.items() if owner==app})
            self.assertEqual(result['source'],source);self.assertEqual(self.inventory(),before)
            self.assertEqual(self.account.read_bytes(),b'original account state');self.assertEqual(self.output.read_bytes(),b'original output')

    def test_native_verification_cannot_come_from_downloaded_json_or_truthy_values(self):
        for value in (False,None,1,'true'):
            with self.assertRaises(ValueError):self.launch(native_verified=value)
        changed={**self.source,'native_verified':True}
        with self.assertRaises(ValueError):self.launch(source=changed)

    def test_optional_trusted_signature_callback_receives_exact_payload_and_must_return_true(self):
        calls=[]
        result=self.launch(verify_signature=lambda *args:calls.append(args) or True)
        self.assertEqual(result['signatureVerification'],'python-callback');self.assertEqual(len(calls),1)
        self.assertEqual(sha(calls[0][1]),self.source['pointerDigest']);self.assertEqual(len(calls[0][2]),64)
        for verdict in (False,1,None):
            with self.assertRaises(ValueError):self.launch(verify_signature=lambda *_args:verdict)

    def test_all_source_marker_fields_are_bound_to_native_cache_or_exact_pointer(self):
        changes={'schemaVersion':2,'appId':'melange','repository':'untrusted/repo','catalogSequence':2,
            'releaseTag':'module-data-2026-10-22','releaseCommit':'b'*40,'pointerDigest':'c'*64,
            'manifestSha256':'d'*64,'cacheRoot':str(self.data)}
        for field,value in changes.items():
            with self.subTest(field=field),self.assertRaises((ValueError,OSError)):
                self.launch(source={**self.source,field:value})

    def test_strict_json_pointer_canonical_encoding_and_manifest_hash_are_required(self):
        raw=self.envelope.read_bytes();self.envelope.write_bytes(b'{"schemaVersion":1,"schemaVersion":1}')
        with self.assertRaises(ValueError):self.launch()
        self.envelope.write_bytes(raw)
        raw_payload=json.dumps(self.pointer,indent=2).encode();self.rebind(raw_payload=raw_payload)
        with self.assertRaises(ValueError):self.launch()
        self.rebind();p=self.cache/'manifests'/(self.source['manifestSha256']+'.json');p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.launch()

    def test_app_purpose_release_and_manifest_linkage_cannot_cross_scope(self):
        for field,value in (('purpose','melange-public-module-datasets'),('repository','other/repo'),('releaseTag','module-data-2026-10-22')):
            original=copy.deepcopy(self.manifest);self.manifest[field]=value;self.rebind()
            with self.assertRaises(ValueError):self.launch()
            self.manifest=original;self.rebind()

    def test_exact_roles_counts_segments_and_safe_assets_are_checked_before_readers(self):
        original=copy.deepcopy(self.manifest)
        mutations=[lambda d:d['objects'].pop(),lambda d:d['objects'][0].update(role='accounts'),
            lambda d:d['counts'].update(files=True),lambda d:d['objects'][0]['segments'][0].update(asset='../account'),
            lambda d:d['objects'][0]['segments'][0].update(asset='NUL.bin'),lambda d:d['objects'][0]['segments'][0].update(bytes=1024**3+1),
            lambda d:d['objects'][0].update(bytes=d['objects'][0]['bytes']+1)]
        for mutate in mutations:
            self.manifest=copy.deepcopy(original);mutate(self.manifest['datasets'][0]);self.rebind()
            with self.assertRaises(ValueError):self.launch()

    def test_compiled_required_kinds_cannot_be_removed_or_replaced(self):
        with self.assertRaises(ValueError):self.launch(required_kinds=['mentat.unknown.v1'])
        self.make('melange');self.manifest['datasets'].pop();self.rebind()
        with self.assertRaises(ValueError):self.launch()

    def test_extra_snapshot_files_and_empty_directories_are_refused(self):
        extra=self.snapshot/'unlisted';extra.mkdir()
        with self.assertRaises(ValueError):self.launch()
        extra.rmdir();extra.write_bytes(b'unlisted')
        with self.assertRaises(ValueError):self.launch()

    def test_account_overlap_and_arbitrary_cache_root_are_refused_without_writes(self):
        before=self.inventory()
        with self.assertRaises(ValueError):self.launch(original_data_root=str(self.profile))
        with self.assertRaises(ValueError):self.launch(protected_roots=[str(self.cache)])
        with self.assertRaises(ValueError):self.launch(source={**self.source,'cacheRoot':str(self.base/'arbitrary')})
        self.assertEqual(self.inventory(),before)

    def test_hardlinked_role_cannot_read_account_bytes(self):
        p=self.role();raw=p.read_bytes();account=self.data/'account-role.fixture';account.write_bytes(raw);p.unlink();os.link(account,p)
        with self.assertRaises(ValueError):self.launch()
        self.assertEqual(account.read_bytes(),raw)

    def test_windows_path_and_handle_ctime_semantics_remain_separately_stable(self):
        original=os.fstat
        def different_time(descriptor):
            info=original(descriptor)
            class HandleInfo:
                st_ctime_ns=info.st_ctime_ns+1000
                def __getattr__(self,name):return getattr(info,name)
            return HandleInfo()
        with patch('module_data_launch.os.fstat',side_effect=different_time):
            self.assertEqual(self.launch()['signatureVerification'],'native-js')

    def test_role_swapped_to_account_hardlink_during_open_is_refused(self):
        target=self.role();account=self.data/'open-race-account.fixture';raw=target.read_bytes();account.write_bytes(raw)
        original=os.open;swapped=False
        def raced(file,*args,**kwargs):
            nonlocal swapped
            if Path(file)==target and not swapped:
                swapped=True;target.unlink();os.link(account,target)
            return original(file,*args,**kwargs)
        with patch('module_data_launch.os.open',side_effect=raced),self.assertRaises(ValueError):self.launch()
        self.assertTrue(swapped);self.assertEqual(account.read_bytes(),raw)

    def test_hardlinked_metadata_and_directory_reparse_points_are_refused(self):
        raw=self.envelope.read_bytes();account=self.data/'metadata.fixture';account.write_bytes(raw);self.envelope.unlink();os.link(account,self.envelope)
        with self.assertRaises(ValueError):self.launch()
        self.envelope.unlink();self.envelope.write_bytes(raw)
        parent=self.role().parent;outside=self.data/'outside-role';shutil.move(parent,outside)
        if os.name=='nt':
            import subprocess
            subprocess.run(['cmd','/c','mklink','/J',str(parent),str(outside)],check=True,capture_output=True)
        else:parent.symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):self.launch()

    def test_reader_mutation_or_inflated_coverage_is_not_a_successful_launch(self):
        original=self.configured
        def changed(request):
            result=original(request);self.role().write_bytes(b'x'*self.role().stat().st_size);return result
        with patch.object(self,'configured',side_effect=changed),self.assertRaises(ValueError):self.launch()
        self.make('mentat')
        with patch.object(self,'configured',return_value={'appId':'mentat','kind':self.manifest['datasets'][0]['kind'],'coverage':{'completeKind':True,'fullApplication':True}}),self.assertRaises(ValueError):self.launch()

    def test_native_localappdata_choice_is_app_scoped(self):
        local=self.base/'local';local.mkdir()
        new=local/'MelangeData'/'mentat'/'github-module-data';new.parent.mkdir(parents=True);shutil.move(self.cache,new)
        with patch.dict(os.environ,{'LOCALAPPDATA':str(local)}):
            result=self.launch(source={**self.source,'cacheRoot':str(new)})
            self.assertEqual(result['source']['cacheRoot'],str(new))
            with self.assertRaises(ValueError):self.launch(source={**self.source,'cacheRoot':str(new.parent.parent/'melange'/'github-module-data')})

    def test_actual_graph_and_payroll_configurers_use_synthetic_sources_only(self):
        from module_data_test_helpers import graph_fixture,payroll_fixture
        self.make('melange');source=Path(__file__).resolve().parents[3];contents={}
        for builder in (graph_fixture,payroll_fixture):
            folder=self.base/builder.__name__;folder.mkdir();fixture=builder(folder)
            for role,file in fixture.request['files'].items():contents[(fixture.kind,role)]=Path(file).read_bytes()
        self.make('melange',contents)
        result=prepare_module_readers(**{**self.options,'source_root':str(source)})
        graph=result['readers']['melange.staffer-graph-core.v1'];payroll=result['readers']['melange.payroll-identity-core.v1']
        self.assertIs(graph['graph_factory'](self.data),graph['graph'])
        self.assertEqual(payroll['payroll_loader'](self.data)['counts'],{'episodes':0})
        self.assertFalse(result['coverage']['fullApplication']);self.assertEqual(self.account.read_bytes(),b'original account state')


if __name__=='__main__':unittest.main()
