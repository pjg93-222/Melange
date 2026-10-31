"""Bootstrap refreshes must not silently repin independently shipped source trees."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import refresh_module_inventory as refresh


def declarations(rendered):
    python_text = next(value for path, value in rendered.items() if path.suffix == '.py')
    namespace = {}
    exec(compile(python_text, '<generated-inventory>', 'exec'), namespace)
    python_specs = json.loads(json.dumps({app: {key: [dict(row) for row in value] if key == 'programFiles' else value
        for key, value in spec.items()} for app, spec in namespace['APPLICATION_SPECS'].items()}))
    js_text = next(value for path, value in rendered.items() if path.suffix == '.cjs')
    javascript_specs = json.JSONDecoder().raw_decode(js_text.split('const APPLICATION_SPECS=freeze(', 1)[1])[0]
    return python_specs, javascript_specs


class RefreshInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='module-bootstrap-refresh-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.here = self.base / 'packaging'
        self.source = self.base / 'source'
        self.here.mkdir()
        self.source.mkdir()
        self.specs = {}
        for app in ('melange', 'mentat'):
            self.specs[app] = {'appId': app, 'programFingerprint': '0' * 64, 'programFiles': [
                {'root': 'bootstrap', 'path': 'old_bootstrap.py', 'bytes': 1, 'sha256': '1' * 64},
                {'root': 'source', 'path': app + '/app.py', 'bytes': 9, 'sha256': '2' * 64},
            ]}
            (self.source / app).mkdir()
            (self.source / app / 'app.py').write_bytes(b'changed source')
        (self.here / 'module_application_inventory.py').write_text('APPLICATION_SPECS = ' + repr(self.specs), encoding='utf-8')
        (self.here / 'old_bootstrap.py').write_bytes(b'changed bootstrap')
        (self.here / 'terrier_standalone.py').write_bytes(b'new standalone boundary')
        (self.here / 'desktop_credentials.py').write_bytes(b'new Windows identity helper')
        (self.here / 'terrier_github_snapshot.py').write_bytes(b'reviewed public snapshot activation')
        (self.here / 'module_catalogue_cache.py').write_bytes(b'reviewed user-bound validation cache')
        (self.here / 'desktop_workspace.py').write_bytes(b'reviewed trusted workspace interface')
        (self.here / 'workspace_data_contract.py').write_bytes(b'fixed passive workspace roles')
        (self.here / 'module_workspace_handoff.py').write_bytes(b'bounded native dual handoff')
        self.workspace_helpers = ('workspace_archive.py','workspace_sqlite.py','workspace_graph.py','workspace_cache.py',
            'module_workspace_inputs.py','workspace_melange.py','workspace_mentat.py','module_workspace_installers.py',
            'module_workspace_render.py','module_workspace_ui_templates.py','module_workspace_combined_ui.py','module_workspace_industry_ui.py')
        for name in self.workspace_helpers:
            (self.here / name).write_bytes(('reviewed fixed helper '+name).encode())
        (self.source / 'new_source.py').write_bytes(b'new reviewed source')
        for target, value in (('HERE', self.here), ('ROOT', self.source), ('ADDITIONS', {'melange': ('new_source.py',)})):
            instance = patch.object(refresh, target, value)
            instance.start()
            self.addCleanup(instance.stop)

    def test_bootstrap_only_retains_source_rows_without_accessing_source_root(self):
        class SourceMustNotBeAccessed:
            def __truediv__(self, _):
                raise AssertionError('Bootstrap-only refresh accessed backend source')
        with patch.object(refresh, 'ROOT', SourceMustNotBeAccessed()):
            python_specs, javascript_specs = declarations(refresh.outputs(bootstrap_only=True))
        self.assertEqual(python_specs, javascript_specs)
        for app, spec in python_specs.items():
            self.assertEqual([row for row in spec['programFiles'] if row['root'] == 'source'],
                             [row for row in self.specs[app]['programFiles'] if row['root'] == 'source'])
            self.assertEqual(spec['programFingerprint'], hashlib.sha256(refresh.encoded(spec['programFiles'])).hexdigest())
            bootstrap = {row['path']: row for row in spec['programFiles'] if row['root'] == 'bootstrap'}
            expected = {'old_bootstrap.py', 'terrier_standalone.py', 'desktop_credentials.py', 'terrier_github_snapshot.py',
                        'desktop_workspace.py', 'workspace_data_contract.py', 'module_workspace_handoff.py'}
            expected.update(self.workspace_helpers)
            if app == 'melange':
                expected.add('module_catalogue_cache.py')
            self.assertEqual(set(bootstrap), expected)
            for name, row in bootstrap.items():
                raw = (self.here / name).read_bytes()
                self.assertEqual((row['bytes'], row['sha256']), (len(raw), hashlib.sha256(raw).hexdigest()))

    def test_full_refresh_rehashes_source_and_includes_explicit_bootstrap_addition(self):
        python_specs, javascript_specs = declarations(refresh.outputs())
        self.assertEqual(python_specs, javascript_specs)
        for app, spec in python_specs.items():
            files = {(row['root'], row['path']): row for row in spec['programFiles']}
            self.assertIn(('bootstrap', 'terrier_standalone.py'), files)
            self.assertIn(('bootstrap', 'desktop_workspace.py'), files)
            self.assertEqual(('bootstrap', 'module_catalogue_cache.py') in files, app == 'melange')
            self.assertEqual(files[('source', app + '/app.py')]['sha256'], hashlib.sha256(b'changed source').hexdigest())
            self.assertEqual(('source', 'new_source.py') in files, app == 'melange')

    def test_workspace_declarations_pin_same_union_without_promoting_coverage(self):
        rendered = refresh.outputs(bootstrap_only=True)
        python_text = next(value for path, value in rendered.items() if path.suffix == '.py')
        namespace = {}
        exec(compile(python_text, '<generated-inventory>', 'exec'), namespace)
        js = next(value for path, value in rendered.items() if path.suffix == '.cjs')
        javascript = json.JSONDecoder().raw_decode(js.split('const WORKSPACE_APPLICATION_SPECS=freeze(', 1)[1])[0]
        for app in ('melange', 'mentat'):
            public, workspace = namespace['APPLICATION_SPECS'][app], namespace['WORKSPACE_APPLICATION_SPECS'][app]
            self.assertEqual(workspace['programFingerprint'], public['programFingerprint'])
            self.assertEqual(workspace['programFiles'], public['programFiles'])
            self.assertEqual(workspace['contractId'], app + '.workspace.v1')
            self.assertNotEqual(workspace['requiredKinds'], public.get('requiredKinds'))
            self.assertNotIn('coverage', workspace)
            self.assertEqual(javascript[app]['programFiles'], [dict(row) for row in workspace['programFiles']])

    def test_app_selection_preserves_other_app_and_missing_bootstrap_is_refused(self):
        python_specs, _ = declarations(refresh.outputs(('melange',), bootstrap_only=True))
        self.assertEqual(python_specs['mentat'], self.specs['mentat'])
        (self.here / 'terrier_standalone.py').unlink()
        with self.assertRaisesRegex(ValueError, 'Reviewed program input is unavailable'):
            refresh.outputs(bootstrap_only=True)

    def test_district_refresh_retains_sealed_source_rows_and_uses_only_explicit_bootstrap_roster(self):
        source = {'root': 'source', 'path': 'server/app.py', 'bytes': 9, 'sha256': '3' * 64}
        table = {'terrier': {'schemaVersion': 1, 'appId': 'terrier',
                            'programFiles': [source], 'programFingerprint': '0' * 64}}
        with (self.here / 'module_application_inventory.py').open('a', encoding='utf-8') as handle:
            handle.write('\nDISTRICT_PROGRAM_SPECS = ' + repr(table))
        (self.here / 'build_runtime.py').write_text("BOOTSTRAP_FILES = ('old_bootstrap.py', 'module_application_inventory.py')\n", encoding='utf-8')
        (self.here / 'unreviewed.py').write_bytes(b'not discovered')
        rendered = refresh.outputs(bootstrap_only=True)
        namespace = {}
        exec(compile(next(value for file, value in rendered.items() if file.suffix == '.py'), '<district-inventory>', 'exec'), namespace)
        spec = namespace['DISTRICT_PROGRAM_SPECS']['terrier']
        rows = [dict(row) for row in spec['programFiles']]
        self.assertEqual([row for row in rows if row['root'] == 'source'], [source])
        self.assertEqual([row['path'] for row in rows if row['root'] == 'bootstrap'], ['old_bootstrap.py'])
        self.assertEqual(spec['programFingerprint'], hashlib.sha256(refresh.encoded(rows)).hexdigest())
        javascript = next(value for file, value in rendered.items() if file.suffix == '.cjs')
        js = json.JSONDecoder().raw_decode(javascript.split('const DISTRICT_PROGRAM_SPECS=freeze(', 1)[1])[0]
        self.assertEqual(js['terrier']['programFiles'], rows)
        (self.here / 'old_bootstrap.py').unlink()
        with self.assertRaisesRegex(ValueError, 'Reviewed district helper is unavailable'):
            refresh.outputs(bootstrap_only=True)


if __name__ == '__main__':
    unittest.main()
