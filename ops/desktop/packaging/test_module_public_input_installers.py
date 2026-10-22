"""Generated passive program/row fixtures; no original data or production map."""
import base64
from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

from module_application_contracts import ApplicationContract, ProgramFile, ModuleInputError, canonical, program_fingerprint
from module_data_handoff import prepare_handoff, server_installation, complete_server_installation, server_installed_health
from module_data_snapshot import KINDS, Snapshot
from module_public_input_installers import (PUBLIC_KINDS, PUBLIC_IDS, PRIVATE_IDS, prepare_public_component,
    prepare_public_readers, public_reader, capture_originals, install_public_readers, private_program_guard)


PUBLIC_PROGRAM = '''from pathlib import Path
from contextlib import contextmanager
class Catalogue:
    def __init__(self): self._closed = False
    def catalogue(self): return {'fixture': True}
    def provenance(self, *args): return {'fixture': True}
    def rows(self, *args): return {'fixture': True}
    def observations(self, *args): return {'fixture': True}
    @contextmanager
    def download(self, *args): yield None
    def close(self): self._closed = True
PublicDataCatalogue = Catalogue
def prepare(root, *, source_digest, source_fingerprint): return Catalogue()
def prepare_public_data(snapshot, *, cancelled=lambda:False):
    from module_data_snapshot import Snapshot
    assert type(snapshot) is Snapshot
    assert not cancelled()
    return Catalogue()
'''
MENTAT_SERVER = '''from pathlib import Path
from http.server import ThreadingHTTPServer
ORIGINAL_MODEL_PATH = Path(__file__).parent / 'local-model.fixture'
class Console: pass
'''
MELANGE_SERVER = '''from http.server import ThreadingHTTPServer
class WorkspaceServer(ThreadingHTTPServer): pass
class IncrementalProfiles: pass
'''
MELANGE_SERVICE = '''class LiveService: pass
'''


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='public-installer-generated-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.roots = {key:self.base/key for key in ('source','profile','data','state','bootstrap')}
        for root in self.roots.values(): root.mkdir()
        self.saved = {key:value for key,value in sys.modules.items()
                      if key in ('public_data','server') or key == 'fec' or key.startswith('fec.')}
        for key in self.saved: del sys.modules[key]
        self.addCleanup(self.restore_modules)

    def restore_modules(self):
        for key in tuple(sys.modules):
            if key in ('public_data','server') or key == 'fec' or key.startswith('fec.'):
                del sys.modules[key]
        sys.modules.update(self.saved)

    def clear_modules(self):
        for key in tuple(sys.modules):
            if key in ('public_data','server') or key == 'fec' or key.startswith('fec.'):
                del sys.modules[key]

    def make(self, app):
        self.app = app
        source = self.roots['source']
        programs = ({'mentat/app/public_data.py':PUBLIC_PROGRAM, 'mentat/app/server.py':MENTAT_SERVER}
                    if app == 'mentat' else {'fec/__init__.py':'', 'fec/surfaces/__init__.py':'',
                        'fec/surfaces/melange_public_data.py':PUBLIC_PROGRAM,
                        'fec/surfaces/staffer_live_server.py':MELANGE_SERVER,
                        'fec/surfaces/staffer_live_service.py':MELANGE_SERVICE,
                        'fec/surfaces/staffer_graph_snapshot.py':'class StaticGraph: pass\n'})
        files = []
        for name, content in programs.items():
            raw = content.encode('utf-8'); path = source/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
            files.append(ProgramFile('source',name,len(raw),hashlib.sha256(raw).hexdigest()))
        kind = PUBLIC_KINDS[app]
        root = self.roots['profile']/'packs/github-module-data/snapshots/fixture/dataset'
        objects, paths = [], {}
        for index,(role,(name,_limit)) in enumerate(KINDS[kind][1].items()):
            path = root/name; path.parent.mkdir(parents=True,exist_ok=True); raw = f'generated-{index}\n'.encode(); path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest(); paths[role] = str(path)
            objects.append({'role':role,'bytes':len(raw),'sha256':digest,
                'segments':[{'asset':f'part-{index}.bin','bytes':len(raw),'sha256':digest}]})
        request = {'appId':app,'kind':kind,'sourceRoot':str(source),'snapshotRoot':str(root),'files':paths,'objects':objects}
        def prepare(**options):
            result = prepare_public_component(Snapshot(request),source=options['source'],is_cancelled=options['is_cancelled'])
            return {'appId':app,'source':dict(options['source']),'readers':{kind:result},
                    'coverage':{'completeKind':True,'fullApplication':False}}
        files = tuple(files)
        self.contract = ApplicationContract(app,app+'.generated-public-installer.v1',program_fingerprint(files),files,
            (kind,),PUBLIC_IDS[app],PRIVATE_IDS[app],prepare,install_public_readers)
        source_spec = {'schemaVersion':1,'appId':app,'repository':'pjg93-222/'+app,'catalogSequence':1,
            'releaseTag':'module-data-2026-10-22-fixture','releaseCommit':'a'*40,'pointerDigest':'b'*64,
            'manifestSha256':'c'*64,'cacheRoot':str(self.roots['profile']/'packs/github-module-data')}
        self.message = {'schemaVersion':1,'appId':app,'contractId':self.contract.contract_id,
            'programFingerprint':self.contract.program_fingerprint,'profileRoot':str(self.roots['profile']),
            'sourceRoot':str(source),'originalDataRoot':str(self.roots['data']),'stateRoot':str(self.roots['state']),
            'source':source_spec,'launchNonce':base64.urlsafe_b64encode(b'x'*32).rstrip(b'=').decode(),
            'binding':{'contractId':self.contract.contract_id,'programFingerprint':self.contract.program_fingerprint,
                'sourceDigest':source_spec['manifestSha256'],'sourceFingerprint':hashlib.sha256(canonical(source_spec)).hexdigest()}}
        raw = canonical(self.message)
        prepared = prepare_handoff(io.BytesIO(struct.pack('>I',len(raw))+raw),app_id=app,
            profile_root=self.roots['profile'],source_root=source,original_data_root=self.roots['data'],
            state_root=self.roots['state'],bootstrap_root=self.roots['bootstrap'],lookup=lambda *_args:self.contract)
        self.reader = public_reader(prepared)
        from module_public_input_installers import _program_module
        module = _program_module(source,app,server=True)
        if app == 'mentat':
            server = module.ThreadingHTTPServer.__new__(module.ThreadingHTTPServer)
            console = module.Console(); console.root = self.roots['state']/'console'; console.report_directory = self.roots['data']/'reports'
            console.report_cache = {}; console.public_data = self.reader; server.app = console
            self.private = console
            console_root, report_root = console.root, console.report_directory
            guard = private_program_guard(source)
            capture = lambda actual:capture_originals(prepared,actual,console_root=console_root,
                reports_root=report_root,program_guard=guard)
        else:
            from fec.surfaces.staffer_live_service import LiveService
            from fec.surfaces.staffer_graph_snapshot import StaticGraph
            server = module.WorkspaceServer.__new__(module.WorkspaceServer)
            service = LiveService(); service.source_root = self.roots['data']; service.static = StaticGraph()
            service.static.root = self.roots['data']/'audits/staffer_network'
            service.profiles = module.IncrementalProfiles()
            service.profiles.raw_dir = self.roots['data']/'audits/staffer_network/politico_profile_crawl_20260903_raw'
            service.profiles.path = service.profiles.raw_dir/'profiles.ndjson'
            server.dashboard = service; server.public_data = self.reader; self.private = service
            capture = lambda actual:capture_originals(prepared,actual)
        self.prepared, self.server, self.capture, self.module = prepared, server, capture, module
        return prepared, server, server_installation(prepared,capture)

    def test_both_actual_type_installations_seal_same_catalogue_and_original_contexts(self):
        for app in ('mentat','melange'):
            with self.subTest(app=app):
                if hasattr(self,'prepared'): self.clear_modules()
                prepared, server, latch = self.make(app)
                before = dict(vars(self.private))
                complete_server_installation(latch,server)
                health = server_installed_health(latch,server)
                expected = {'publicReaders':sorted(PUBLIC_IDS[app]),'privateBoundaries':sorted(PRIVATE_IDS[app])}
                self.assertEqual(health['coverageDigest'],hashlib.sha256(canonical(expected)).hexdigest())
                self.assertEqual(dict(vars(self.private)),before)
                self.assertEqual(public_reader(prepared),self.reader)

    def test_changed_public_attachment_cannot_keep_health(self):
        _prepared, server, latch = self.make('mentat'); complete_server_installation(latch,server)
        server.app.public_data = object()
        with self.assertRaises(ModuleInputError): server_installed_health(latch,server)

    def test_changed_private_cache_or_original_root_cannot_keep_health(self):
        _prepared, server, latch = self.make('mentat'); complete_server_installation(latch,server)
        server.app.report_cache = {}
        with self.assertRaises(ModuleInputError): server_installed_health(latch,server)

    def test_original_graph_reference_and_closed_reader_are_refused(self):
        _prepared, server, latch = self.make('melange'); complete_server_installation(latch,server)
        graph = server.dashboard.static; server.dashboard.static = object()
        with self.assertRaises(ModuleInputError): server_installed_health(latch,server)
        server.dashboard.static = graph; self.reader.close()
        with self.assertRaises(ModuleInputError): server_installed_health(latch,server)

    def test_same_private_graph_or_profile_object_cannot_retarget_nested_paths_to_public_cache(self):
        prepared,server,latch=self.make('melange');complete_server_installation(latch,server)
        graph,profiles=server.dashboard.static,server.dashboard.profiles
        for obj,key in ((graph,'root'),(profiles,'raw_dir'),(profiles,'path')):
            previous=getattr(obj,key)
            setattr(obj,key,Path(prepared.source['cacheRoot']))
            with self.subTest(key=key),self.assertRaises(ModuleInputError):server_installed_health(latch,server)
            self.assertIs(server.dashboard.static,graph);self.assertIs(server.dashboard.profiles,profiles)
            setattr(obj,key,previous)
        self.assertEqual(server_installed_health(latch,server)['sourceDigest'],prepared.binding['sourceDigest'])

    def test_preexisting_wrong_nested_original_graph_location_refuses_installation(self):
        prepared,server,latch=self.make('melange')
        server.dashboard.static.root=Path(prepared.source['cacheRoot'])
        with self.assertRaises(ModuleInputError):complete_server_installation(latch,server)

    def test_unknown_original_path_is_refused_without_retargeting(self):
        prepared,server,latch = self.make('mentat'); original = server.app.root
        server.app.root = self.roots['source']
        with self.assertRaises(ModuleInputError): complete_server_installation(latch,server)
        self.assertIs(server.app.root,self.roots['source'])
        self.assertNotEqual(server.app.root,original)

    def test_original_program_path_alias_guard_detects_replacement_without_reading_private_files(self):
        _prepared,server,latch = self.make('mentat'); guard = private_program_guard(self.roots['source'])
        with patch.object(Path,'open',side_effect=AssertionError('no private file reads')):
            self.assertTrue(guard()); self.module.ORIGINAL_MODEL_PATH = Path('changed.fixture'); self.assertFalse(guard())

    def test_original_model_path_alias_change_cannot_keep_installed_health(self):
        _prepared,server,latch=self.make('mentat');complete_server_installation(latch,server)
        self.module.ORIGINAL_MODEL_PATH=Path('changed.fixture')
        with self.assertRaises(ModuleInputError):server_installed_health(latch,server)

    def test_compiled_reader_method_replacement_cannot_keep_health(self):
        _prepared,server,latch = self.make('mentat'); complete_server_installation(latch,server)
        self.reader.catalogue = lambda:None
        with self.assertRaises(ModuleInputError): server_installed_health(latch,server)

    def test_component_kind_never_implies_legacy_core_or_full_application(self):
        for app,kind in PUBLIC_KINDS.items():
            with self.assertRaises(ModuleInputError): prepare_public_readers(app_id=app,required_kinds=(kind,'old.core'))
        from module_application_contracts import application_contract
        contract=application_contract('mentat','mentat.public-data.v1')
        self.assertEqual(contract.required_kinds,('mentat.public-fec-tables.v1',))
        from module_application_contracts import verify_program
        with self.assertRaises(ModuleInputError):
            verify_program(contract,source_root=self.roots['source'],bootstrap_root=self.roots['bootstrap'])

    def test_existing_different_program_module_is_refused(self):
        self.make('mentat')
        from module_public_input_installers import _program_module
        previous = self.reader.__class__.__module__
        module = sys.modules[previous]; name = module.__file__; module.__file__ = str(self.roots['data']/'public_data.py')
        try:
            with self.assertRaises((ModuleInputError,OSError)): _program_module(self.roots['source'],'mentat')
        finally: module.__file__ = name


if __name__ == '__main__': unittest.main()
