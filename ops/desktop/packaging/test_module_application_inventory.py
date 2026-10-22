"""Compiled declarations cannot substitute for installed program verification."""
import ast
from pathlib import Path
from types import MappingProxyType
import tempfile
import unittest
from unittest.mock import patch

import module_application_inventory as inventory
from module_application_contracts import (ModuleInputError, application_contract, program_fingerprint, verify_program)
from module_public_input_installers import PUBLIC_KINDS, PUBLIC_IDS, PRIVATE_IDS


class CompiledInventoryTests(unittest.TestCase):
    def test_fixed_declarations_have_exact_contracts_factories_coverage_and_fingerprints(self):
        for app in ('melange','mentat'):
            contract=application_contract(app,app+'.public-data.v1')
            self.assertEqual(contract.program_fingerprint,program_fingerprint(contract.program_files))
            self.assertEqual(contract.required_kinds,(PUBLIC_KINDS[app],))
            self.assertEqual(contract.public_readers,PUBLIC_IDS[app])
            self.assertEqual(contract.private_boundaries,PRIVATE_IDS[app])
            self.assertEqual(contract.startup_timeout_ms,600000 if app=='melange' else 300000)
            self.assertEqual(contract.prepare_readers.__name__,'prepare_public_readers')
            self.assertEqual(contract.install_readers.__name__,'install_public_readers')

    def test_literal_inventory_contains_no_imported_factory_or_executable_builder(self):
        tree=ast.parse(Path(inventory.__file__).read_bytes())
        self.assertFalse(any(isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,
            ast.Lambda,ast.ListComp,ast.DictComp,ast.SetComp,ast.GeneratorExp)) for node in ast.walk(tree)))
        calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)]
        self.assertTrue(all(isinstance(node.func,ast.Name) and node.func.id=='MappingProxyType' for node in calls))

    def test_every_declaration_layer_is_immutable(self):
        with self.assertRaises(TypeError):inventory.APPLICATION_SPECS['new']={}
        for spec in inventory.APPLICATION_SPECS.values():
            with self.assertRaises(TypeError):spec['startupTimeoutMs']=1
            self.assertIs(type(spec['programFiles']),tuple)
            with self.assertRaises(TypeError):spec['programFiles'][0]['sha256']='0'*64
            for key in ('requiredKinds','publicReaders','privateBoundaries'):
                self.assertIs(type(spec[key]),tuple)

    def test_unknown_or_cross_app_contract_never_selects_a_factory(self):
        for app,contract in (('terrier','terrier.public-data.v1'),('melange','mentat.public-data.v1'),
            ('mentat','mentat.aggregate-forecast-core.v1'),('mentat','downloaded.factory'),('','')):
            self.assertIsNone(application_contract(app,contract))

    def changed(self,mutate):
        specs=dict(inventory.APPLICATION_SPECS);spec=dict(specs['mentat']);mutate(spec)
        specs['mentat']=MappingProxyType(spec)
        with patch.object(inventory,'APPLICATION_SPECS',MappingProxyType(specs)):
            with self.assertRaises(ModuleInputError):application_contract('mentat','mentat.public-data.v1')

    def test_downloaded_authority_fields_and_legacy_kinds_are_refused(self):
        for mutate in (lambda s:s.update(factory='anything'),lambda s:s.update(schemaVersion=True),
            lambda s:s.update(requiredKinds=('mentat.aggregate-forecast-core.v1',)),
            lambda s:s.update(publicReaders=('mentat.downloaded-reader',)),
            lambda s:s.update(privateBoundaries=()),lambda s:s.update(startupTimeoutMs=300001)):
            with self.subTest(mutate=mutate):self.changed(mutate)

    def test_fingerprint_drift_missing_critical_ui_and_recursive_declaration_are_refused(self):
        def drop_ui(spec):
            spec['programFiles']=tuple(row for row in spec['programFiles'] if row['path']!='mentat/app/public_data.js')
        def recursive(spec):
            spec['programFiles']=(*spec['programFiles'],MappingProxyType({'root':'bootstrap',
                'path':'module_application_inventory.py','bytes':0,'sha256':'0'*64}))
        for mutate in (lambda s:s.update(programFingerprint='0'*64),drop_ui,recursive):
            with self.subTest(mutate=mutate):self.changed(mutate)

    def test_declared_table_does_not_activate_missing_installed_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';bootstrap=root/'bootstrap';source.mkdir();bootstrap.mkdir()
            before=tuple(root.rglob('*'))
            for app in ('melange','mentat'):
                with self.assertRaises(ModuleInputError):
                    verify_program(application_contract(app,app+'.public-data.v1'),source_root=source,bootstrap_root=bootstrap)
            self.assertEqual(tuple(root.rglob('*')),before)


if __name__=='__main__':unittest.main()
