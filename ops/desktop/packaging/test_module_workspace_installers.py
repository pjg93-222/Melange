"""Fixed adapter boundary fixtures; not production data/native acceptance."""
import hashlib
from pathlib import Path
import sys
import tempfile
from types import MappingProxyType, ModuleType
import unittest
from unittest.mock import patch

import module_application_contracts as contracts
from module_application_contracts import ApplicationContract, ModuleInputError, ProgramFile, program_fingerprint
from module_data_handoff import PreparedHandoff, planned_original_root
import module_workspace_installers as installers
from workspace_data_contract import WORKSPACE_KINDS, WORKSPACE_READERS, WORKSPACE_PRIVATE_BOUNDARIES


class WorkspaceAdapterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='workspace-adapter-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.roots = {key: str(self.root / name) for key, name in
            (('sourceRoot', 'source'), ('originalDataRoot', 'original'), ('stateRoot', 'state'), ('profileRoot', 'profile'))}
        for path in self.roots.values():
            Path(path).mkdir()
        self.bootstrap = self.root / 'bootstrap'
        self.bootstrap.mkdir()
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        files = (ProgramFile('source', 'fixture.py', 0, hashlib.sha256(b'').hexdigest()),)
        self.contract = ApplicationContract('mentat', 'mentat.workspace.v1', program_fingerprint(files), files,
            WORKSPACE_KINDS['mentat'], WORKSPACE_READERS['mentat'], WORKSPACE_PRIVATE_BOUNDARIES['mentat'],
            installers.prepare_workspace_readers, installers.install_workspace_readers)
        class WorkspaceComponent:
            def __init__(self): self.valid = True
            def verify(self): return self.valid
            def close(self): self.valid = False
        class WorkspaceBinding:
            def __init__(self, server): self.server, self.valid = server, True
            def verify(self): return self.valid
            def handle_request(self, handler): return handler.server is self.server
        self.component_type, self.binding_type = WorkspaceComponent, WorkspaceBinding
        self.module = ModuleType('module_workspace_inputs')
        self.module.WorkspaceComponent, self.module.WorkspaceBinding = WorkspaceComponent, WorkspaceBinding
        def bind(server, prepared):
            self.binding = WorkspaceBinding(server)
            return dict.fromkeys(WORKSPACE_READERS['mentat'], self.binding)
        self.module.bind_mentat_console = bind
        self.module.bind_melange_service = lambda *_: self.fail('Wrong app binder')
        patcher = patch.dict(sys.modules, {'module_workspace_inputs': self.module})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.readers = {kind: {'appId': 'mentat', 'kind': kind, 'reader': WorkspaceComponent(),
            'coverage': {'completeKind': True, 'fullApplication': False}} for kind in WORKSPACE_KINDS['mentat']}
        plans = tuple(planned_original_root(self.roots[key], self.roots[key], protected_roots=(str(self.cache),))
                      for key in ('originalDataRoot', 'stateRoot'))
        self.prepared = PreparedHandoff(self.contract, {'cacheRoot': str(self.cache)}, self.roots,
            self.readers, {}, 'fixture-nonce', str(self.bootstrap), plans)

    def test_fixed_consumers_preserve_exact_native_original_capabilities(self):
        server = object()
        originals = installers.capture_workspace_originals(self.prepared, server)
        installed = installers.install_workspace_readers(self.prepared, server, MappingProxyType(originals))
        self.assertIs(installed.application, server)
        self.assertEqual(set(installed.public_readers), set(WORKSPACE_READERS['mentat']))
        self.assertTrue(all(installed.private_boundaries[key] is originals[key] for key in originals))
        self.assertTrue(installed.verify())
        self.readers[WORKSPACE_KINDS['mentat'][0]]['reader'].valid = False
        with self.assertRaises(ModuleInputError): installed.verify()

    def test_instance_callback_override_and_false_full_app_claim_are_rejected(self):
        reader = self.readers[WORKSPACE_KINDS['mentat'][0]]['reader']
        reader.verify = lambda: True
        with self.assertRaises(ModuleInputError): installers.workspace_components(self.prepared)
        del reader.verify
        self.readers[WORKSPACE_KINDS['mentat'][0]]['coverage']['fullApplication'] = True
        with self.assertRaises(ModuleInputError): installers.workspace_components(self.prepared)

    def test_installed_routes_require_same_server_and_current_binding(self):
        from types import SimpleNamespace
        server = object()
        originals = installers.capture_workspace_originals(self.prepared, server)
        installers.install_workspace_readers(self.prepared, server, MappingProxyType(originals))
        self.assertTrue(installers.handle_workspace_request(SimpleNamespace(server=server), self.prepared))
        with self.assertRaises(ModuleInputError):
            installers.handle_workspace_request(SimpleNamespace(server=object()), self.prepared)
        self.binding.verify = lambda: True
        with self.assertRaises(ModuleInputError):
            installers.handle_workspace_request(SimpleNamespace(server=server), self.prepared)

    def test_wrapper_forces_workspace_registry_and_binds_profile_program(self):
        captured = []
        self.module.prepare_component = lambda snapshot, **options: captured.append((snapshot, options)) or 'prepared'
        options = dict(app_id='mentat', required_kinds=WORKSPACE_KINDS['mentat'], profile={'approved': 'fixture'})
        def launch(**arguments):
            self.assertIs(arguments['workspace'], True)
            self.assertEqual(set(arguments['reader_registry']), set(WORKSPACE_KINDS['mentat']))
            return arguments['reader_registry'][WORKSPACE_KINDS['mentat'][0]]('snapshot', source={'bound': True}, is_cancelled=lambda: False)
        with patch.object(installers, 'application_contract', return_value=self.contract), patch('module_data_launch.prepare_module_readers', side_effect=launch):
            self.assertEqual(installers.prepare_workspace_readers(**options), 'prepared')
        self.assertIs(captured[0][1]['profile'], options['profile'])
        self.assertEqual(captured[0][1]['program_fingerprint'], self.contract.program_fingerprint)
        for additional in ({'workspace': False}, {'reader_registry': {}}, {'required_kinds': ('mentat.unknown.v1',)}):
            with self.assertRaises(ModuleInputError): installers.prepare_workspace_readers(**{**options, **additional})


class WorkspaceContractTests(unittest.TestCase):
    def test_closed_workspace_dispatch_uses_same_program_union_and_fixed_consumers(self):
        from module_public_input_installers import PUBLIC_KINDS, PUBLIC_IDS, PRIVATE_IDS
        from module_application_inventory import APPLICATION_SPECS
        required = set(contracts._SHARED) | {'module_workspace_installers.py', 'module_workspace_inputs.py',
            'workspace_archive.py', 'workspace_sqlite.py', 'workspace_graph.py', 'workspace_cache.py', 'workspace_mentat.py', 'mentat_module_data.py'}
        files = tuple(ProgramFile(root, path, 0, hashlib.sha256(b'').hexdigest())
            for root, paths in (('bootstrap', required), ('source', contracts._APPLICATION['mentat'])) for path in sorted(paths))
        rows = tuple(MappingProxyType({'root': item.root, 'path': item.path, 'bytes': item.bytes, 'sha256': item.sha256}) for item in files)
        base = MappingProxyType({'schemaVersion': 1, 'appId': 'mentat', 'contractId': 'mentat.public-data.v1',
            'programFiles': rows, 'programFingerprint': program_fingerprint(files), 'requiredKinds': (PUBLIC_KINDS['mentat'],),
            'publicReaders': PUBLIC_IDS['mentat'], 'privateBoundaries': PRIVATE_IDS['mentat'], 'startupTimeoutMs': 300000})
        with patch('module_application_inventory.APPLICATION_SPECS', MappingProxyType({**APPLICATION_SPECS, 'mentat': base})):
            public = contracts.application_contract('mentat', 'mentat.public-data.v1')
            workspace = contracts.application_contract('mentat', 'mentat.workspace.v1')
            self.assertEqual(public.program_fingerprint, workspace.program_fingerprint)
            self.assertEqual(workspace.required_kinds, WORKSPACE_KINDS['mentat'])
            self.assertIs(workspace.install_readers, installers.install_workspace_readers)
            self.assertIsNone(contracts.application_contract('mentat', 'mentat.workspace.v2'))
        for corrupt in ({'contractId': 'mentat.downloaded.v1'}, {'requiredKinds': ('mentat.unknown.v1',)}):
            with patch('module_application_inventory.APPLICATION_SPECS', MappingProxyType({'mentat': MappingProxyType({**base, **corrupt})})):
                with self.assertRaises(ModuleInputError): contracts.application_contract('mentat', 'mentat.workspace.v1')


if __name__ == '__main__': unittest.main()
