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
from module_data_launch import APPS, canonical, prepare_module_readers, _native_cache_root


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def melange_source():
    """The root holding Melange's real fec/: MODULE_DATA_MELANGE_SOURCE when set, else this repository when it is Melange's."""
    chosen=os.environ.get('MODULE_DATA_MELANGE_SOURCE')
    root=Path(chosen) if chosen else Path(__file__).resolve().parents[3]
    return root if (root/'fec/surfaces/staffer_graph_snapshot.py').is_file() else None


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
            if app!=app_id or kind not in ('melange.staffer-graph-core.v1','melange.payroll-identity-core.v1','mentat.aggregate-forecast-core.v1'):continue
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
            'original_data_root':str(self.data),'state_root':str(self.state),'source':self.source,'native_verified':True,
            'required_kinds':tuple(d['kind'] for d in self.manifest['datasets']),
            'reader_registry':{d['kind']:self.configure_snapshot for d in self.manifest['datasets']}}

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

    def configure_snapshot(self,snapshot,**_options):
        self.assertIs(type(snapshot),Snapshot)
        return self.configured({'appId':snapshot.app,'kind':snapshot.kind,'sourceRoot':str(snapshot.source),
            'snapshotRoot':str(snapshot.root),'files':{key:str(path) for key,path in snapshot.files.items()},
            'objects':list(snapshot.objects.values())})

    def launch(self, **changes):
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
            self.assertEqual(set(result['readers']),set(self.options['required_kinds']))
            self.assertEqual(result['source'],source);self.assertEqual(self.inventory(),before)
            self.assertEqual(self.account.read_bytes(),b'original account state');self.assertEqual(self.output.read_bytes(),b'original output')

    def test_workspace_namespace_requires_its_own_purpose_and_never_reuses_public_cache(self):
        from workspace_data_contract import WORKSPACE_PURPOSES
        with self.assertRaises(ValueError):
            prepare_module_readers(**self.options, workspace=True)
        old_cache = self.cache
        self.cache = self.profile / 'packs/github-workspace-data'
        old_cache.rename(self.cache)
        self.snapshot = self.cache / self.snapshot.relative_to(old_cache)
        self.pointer['purpose'] = WORKSPACE_PURPOSES[self.app]
        self.manifest['purpose'] = WORKSPACE_PURPOSES[self.app] + 'sets'
        self.rebind()
        self.options['source'] = self.source
        with self.assertRaises(ValueError):
            prepare_module_readers(**self.options)
        result = prepare_module_readers(**self.options, workspace=True)
        self.assertEqual(result['source']['cacheRoot'], str(self.cache))
        self.assertFalse(result['coverage']['fullApplication'])
        self.pointer['purpose'] = APPS[self.app][1]
        self.rebind()
        self.options['source'] = self.source
        with self.assertRaises(ValueError):
            prepare_module_readers(**self.options, workspace=True)
        self.assertEqual(self.account.read_bytes(), b'original account state')
        self.assertEqual(self.output.read_bytes(), b'original output')

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

    def test_no_implicit_core_registry_or_downloaded_registry_authority(self):
        for changes in ({'required_kinds':None},{'reader_registry':None},{'reader_registry':{}},
                        {'reader_registry':{self.options['required_kinds'][0]:True}}):
            with (self.subTest(changes=changes),patch.object(Path,'lstat',side_effect=AssertionError('must not probe')),
                    self.assertRaises(ValueError)):
                self.launch(**changes)

    def test_absent_original_descendants_are_not_created_by_reader_preparation(self):
        future=self.base/'new-original'/'data'
        result=self.launch(original_data_root=str(future))
        self.assertFalse(future.parent.exists())
        self.assertEqual(result['source'],self.source)

    def test_cancellation_is_checked_before_cache_or_domain_reads(self):
        with patch.object(Path,'lstat',side_effect=AssertionError('must not probe')),self.assertRaises(ValueError):
            self.launch(is_cancelled=lambda:True)

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

    def test_fixed_transparently_redirected_cache_uses_physical_read_view_and_preserves_source(self):
        local=self.base/'local';local.mkdir()
        lexical=local/'MelangeData'
        physical=local/'Packages/fixture/LocalCache/Local/MelangeData'
        new=physical/'mentat/github-module-data';new.parent.mkdir(parents=True);shutil.move(self.cache,new)
        original_resolve,original_lstat=Path.resolve,Path.lstat
        def mapped(path):
            return physical/path.relative_to(lexical) if path==lexical or path.is_relative_to(lexical) else path
        def resolve(path,*args,**kwargs):return original_resolve(mapped(path),*args,**kwargs)
        def lstat(path,*args,**kwargs):return original_lstat(mapped(path),*args,**kwargs)
        source={**self.source,'cacheRoot':str(new)};before=self.inventory()
        with patch.dict(os.environ,{'LOCALAPPDATA':str(local)}),patch.object(Path,'resolve',resolve),patch.object(Path,'lstat',lstat):
            result=self.launch(source=source)
            self.assertEqual(result['source'],source)
            self.assertEqual(result['snapshotRoot'],str(new/'snapshots'/self.source['manifestSha256']))
            with self.assertRaisesRegex(ValueError,'Unapproved'):
                self.launch(source={**source,'cacheRoot':str(lexical/'mentat/github-module-data')})
            with self.assertRaisesRegex(ValueError,'Unapproved'):
                self.launch(source={**source,'cacheRoot':str(local/'Packages/arbitrary')})
        self.assertEqual(self.inventory(),before)
        self.assertEqual(self.account.read_bytes(),b'original account state')

    def test_native_cache_root_rejects_replacement_during_resolution(self):
        root=self.profile/'packs/github-module-data';backup=root.with_name('original-cache')
        original=Path.resolve;changed=False
        def raced(path,*args,**kwargs):
            nonlocal changed
            if path==root and not changed:
                changed=True;root.rename(backup);root.mkdir()
            return original(path,*args,**kwargs)
        with patch.object(Path,'resolve',raced),self.assertRaisesRegex(ValueError,'identity|changed'):
            _native_cache_root(self.profile,root)
        self.assertTrue(changed);self.assertTrue(backup.is_dir());self.assertEqual(list(root.iterdir()),[])

    def test_native_cache_root_refuses_transparent_resolution_outside_approved_base(self):
        local=self.base/'local';local.mkdir();requested=local/'MelangeData/mentat/github-module-data';requested.mkdir(parents=True)
        outside=self.base/'outside';outside.mkdir();original=Path.resolve
        def redirected(path,*args,**kwargs):
            return outside if path==requested else original(path,*args,**kwargs)
        with patch.object(Path,'resolve',redirected),self.assertRaisesRegex(ValueError,'boundary|unsafe'):
            _native_cache_root(local,requested)
        self.assertTrue(outside.is_dir());self.assertTrue(requested.is_dir())

    def test_actual_graph_and_payroll_configurers_use_synthetic_sources_only(self):
        from module_data_test_helpers import graph_fixture,payroll_fixture
        source=melange_source()
        if source is None:self.skipTest('Set MODULE_DATA_MELANGE_SOURCE to a Melange source root holding fec/surfaces')
        self.make('melange');contents={}
        for builder in (graph_fixture,payroll_fixture):
            folder=self.base/builder.__name__;folder.mkdir();fixture=builder(folder)
            for role,file in fixture.request['files'].items():contents[(fixture.kind,role)]=Path(file).read_bytes()
        self.make('melange',contents)
        from melange_module_data import configure_readers
        def legacy_component(snapshot,**_options):
            return configure_readers({'appId':snapshot.app,'kind':snapshot.kind,'sourceRoot':str(snapshot.source),
                'snapshotRoot':str(snapshot.root),'files':{key:str(path) for key,path in snapshot.files.items()},
                'objects':list(snapshot.objects.values())})
        result=prepare_module_readers(**{**self.options,'source_root':str(source),
            'reader_registry':{kind:legacy_component for kind in self.options['required_kinds']}})
        graph=result['readers']['melange.staffer-graph-core.v1'];payroll=result['readers']['melange.payroll-identity-core.v1']
        self.assertIs(graph['graph_factory'](self.data),graph['graph'])
        self.assertEqual(payroll['payroll_loader'](self.data)['counts'],{'episodes':0})
        self.assertFalse(result['coverage']['fullApplication']);self.assertEqual(self.account.read_bytes(),b'original account state')


if __name__=='__main__':unittest.main()
