import json
import os
from pathlib import Path
import tempfile
import ast
import importlib
import sys
import hashlib
import types
import unittest
from unittest.mock import patch

from mentat_layout import prepare_workspace, load_connections, workspace_path, canonical_root, bind_analytics_paths, CODE_DIRS, DATA_DIRS


class MentatLayoutTests(unittest.TestCase):
    def test_index_identity_preserved_with_installed_code_and_selected_data(self):
        engine = Path(os.environ['MENTAT_TEST_ENGINE'])
        tree = ast.parse(engine.read_text(encoding='utf-8'))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {'_token','_portable'}]
        with tempfile.TemporaryDirectory(prefix='mentat-index-layout-') as folder:
            root = Path(folder).resolve()
            code, data, state = root/'installed',root/'selected',root/'profile/state'
            for name in CODE_DIRS: (code/name).mkdir(parents=True)
            (code/'inputs').mkdir()
            (code/'mentat.R').write_text('# entrypoint')
            for name in ('fec_receipt_rules.json','fec_transaction_types.json'):
                (code/'inputs'/name).write_text('{}')
            (code/'tools/rules.py').write_text('# immutable rules')
            (code/'app/contribution_data.py').write_bytes(engine.read_bytes())
            workspace = prepare_workspace(code,data,state)
            source = {'ledger':None}
            for key in ('workbook','database','payload','manifest'):
                file = data/('.cache/industry-report/sample/'+key)
                file.parent.mkdir(parents=True,exist_ok=True); file.write_text(key)
                source[key] = file
            module = types.ModuleType('fixture_engine')
            module.__file__ = str(code/'app/contribution_data.py')
            # _token validates the report publication through its sibling module; load the engine's own copy.
            # Keep any report_publication another test module already cached from shadowing the engine's sibling.
            cached = sys.modules.pop('report_publication', None)
            sys.path.insert(0,str(engine.parent))
            try: report_publication = importlib.import_module('report_publication')
            finally:
                sys.path.remove(str(engine.parent))
                sys.modules.pop('report_publication', None)
                if cached is not None: sys.modules['report_publication'] = cached
            module.__dict__.update(Path=Path,hashlib=hashlib,json=json,PROJECT=data,report_publication=report_publication)
            module._stamp = lambda path: (str(path),Path(path).stat().st_size,Path(path).stat().st_mtime_ns)
            module._rule_digest_stamped = lambda stamp: hashlib.sha256(Path(stamp[0]).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            module.RULE_PATHS = [code/'tools/rules.py',code/'inputs/fec_receipt_rules.json',Path(module.__file__)]
            module.LOADED_RULE_STAMPS = [module._stamp(path) for path in module.RULE_PATHS]
            exec(compile(ast.Module(body=functions,type_ignores=[]),str(engine),'exec'),module.__dict__)
            expected = module._token(dict(source))
            module.PROJECT = workspace
            bind_analytics_paths(module,code,workspace,data)
            self.assertEqual(module._token(dict(source)),expected)
            required = [path for path in module.RULE_PATHS if path != Path(module.__file__)]
            self.assertEqual([path.relative_to(workspace).as_posix() for path in required],
                             ['tools/rules.py','inputs/fec_receipt_rules.json'])
            (data/'inputs/fec_receipt_rules.json').write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError,'Accounting code changed'):
                module._token(dict(source))
            module.RULE_PATHS = [code/'inputs/fec_receipt_rules.json']
            with self.assertRaisesRegex(ValueError,'differ'):
                bind_analytics_paths(module,code,workspace,data)

    def test_installed_code_and_own_data_have_distinct_verified_targets(self):
        with tempfile.TemporaryDirectory(prefix='mentat-layout-test-') as folder:
            root = Path(folder)
            code, data, state = root/'installed', root/'data', root/'profile'/'state'
            for name in CODE_DIRS:
                (code/name).mkdir(parents=True)
            (code/'inputs').mkdir()
            (code/'mentat.R').write_text('# immutable entrypoint', encoding='utf-8')
            for name in ('fec_receipt_rules.json','fec_transaction_types.json'):
                (code/'inputs'/name).write_text('{}', encoding='utf-8')
            workspace = prepare_workspace(code, data, state)
            for name in CODE_DIRS:
                self.assertEqual((workspace/name).resolve(), (code/name).resolve())
            for name in DATA_DIRS:
                self.assertEqual((workspace/name).resolve(), (data/name).resolve())
            (data/'inputs'/'fec_receipt_rules.json').write_text('{"user":"preserved"}', encoding='utf-8')
            self.assertEqual(prepare_workspace(code,data,state), workspace)
            self.assertEqual(json.loads((data/'inputs'/'fec_receipt_rules.json').read_text()), {'user':'preserved'})
            with self.assertRaisesRegex(ValueError, 'separate'):
                prepare_workspace(code, code/'userdata', state)
            other_data = root / 'other-data'
            other_workspace = prepare_workspace(code, other_data, state)
            self.assertNotEqual(other_workspace, workspace)
            for name in DATA_DIRS:
                self.assertEqual((workspace/name).resolve(), (data/name).resolve())
                self.assertEqual((other_workspace/name).resolve(), (other_data/name).resolve())
            if os.name == 'nt':
                self.assertEqual(workspace_path(str(code).upper(), str(data).upper(), state), workspace)

    def test_upgrade_preserves_legacy_workspace_and_selected_data(self):
        with tempfile.TemporaryDirectory(prefix='mentat-upgrade-layout-') as folder:
            root = Path(folder).resolve()
            old_code, new_code = root/'installed-1.0.27', root/'installed-1.0.28'
            data, state = root/'selected-data', root/'profile/state'
            for code in (old_code, new_code):
                for name in (*CODE_DIRS, 'inputs'):
                    (code/name).mkdir(parents=True)
                (code/'mentat.R').write_text(code.name, encoding='utf-8')
                for name in ('fec_receipt_rules.json', 'fec_transaction_types.json'):
                    (code/'inputs'/name).write_text('{}', encoding='utf-8')
            previous = prepare_workspace(old_code, data, state)
            # Reproduce the data-only cache left by an older installed version.
            legacy = previous.parent/hashlib.sha256(canonical_root(data).encode('utf-8')).hexdigest()[:24]
            self.assertTrue(previous.is_relative_to(root))
            self.assertEqual(legacy.parent, previous.parent)
            if previous != legacy:
                previous.rename(legacy)
            marker = legacy/'preserved.txt'
            marker.write_text('legacy workspace', encoding='utf-8')
            private_file = data/'state/private.txt'
            private_file.write_text('selected data', encoding='utf-8')
            rules = data/'inputs/fec_receipt_rules.json'
            rules.write_text('{"user":"preserved"}', encoding='utf-8')

            previous = prepare_workspace(old_code, data, state)
            current = prepare_workspace(new_code, data, state)
            self.assertEqual(len({legacy, previous, current}), 3)
            self.assertEqual(prepare_workspace(new_code, data, state), current)
            self.assertEqual(prepare_workspace(old_code, data, state), previous)
            for workspace, code in ((legacy, old_code), (previous, old_code), (current, new_code)):
                for name in CODE_DIRS:
                    self.assertEqual((workspace/name).resolve(), (code/name).resolve())
                for name in DATA_DIRS:
                    self.assertEqual((workspace/name).resolve(), (data/name).resolve())
                self.assertEqual((workspace/'mentat.R').read_text(encoding='utf-8'), code.name)
            # Even a conflicting existing cache must fail closed, never repoint links.
            with patch('mentat_layout.workspace_path', return_value=previous):
                with self.assertRaisesRegex(ValueError, 'unexpected target: app'):
                    prepare_workspace(new_code, data, state)
            self.assertEqual((previous/'app').resolve(), (old_code/'app').resolve())
            self.assertEqual(marker.read_text(encoding='utf-8'), 'legacy workspace')
            self.assertEqual(private_file.read_text(encoding='utf-8'), 'selected data')
            self.assertEqual(json.loads(rules.read_text(encoding='utf-8')), {'user':'preserved'})

    def test_explicit_connections_reject_wrong_selection_and_binary_overlap(self):
        with tempfile.TemporaryDirectory(prefix='mentat-connection-test-') as folder:
            root = Path(folder)
            code, data, state = root/'installed'/'code', root/'project', root/'profile'/'state'
            reports, console, app_data = root/'reports', root/'console', data/'app'/'data'
            for directory in (code, data, state, reports, console, app_data):
                directory.mkdir(parents=True, exist_ok=True)
            config = state.parent/'workspace-connection.json'
            value = {'schemaVersion':1, 'dataRoot':str(data), 'consoleRoot':str(console), 'reportsRoot':str(reports), 'appDataRoot':str(app_data)}
            config.write_text(json.dumps(value), encoding='utf-8')
            paths = load_connections(code, data, state, [root/'installed'])
            self.assertEqual(paths, {'console':console, 'reports':reports, 'app_data':app_data, 'receipt_roots':[]})
            with self.assertRaisesRegex(ValueError, 'selected data root'):
                load_connections(code, root/'different-project', state)
            value['consoleRoot'] = str(code)
            config.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'overlaps installed'):
                load_connections(code, data, state, [root/'installed'])
            value['consoleRoot'] = str(root)
            config.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'overlaps installed'):
                load_connections(code, data, state, [root/'installed'])


if __name__=='__main__':
    unittest.main()
