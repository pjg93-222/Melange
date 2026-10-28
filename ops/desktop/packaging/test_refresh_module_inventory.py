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
    javascript_specs = json.loads(js_text.split('const APPLICATION_SPECS=freeze(', 1)[1].split(');\nmodule.exports', 1)[0])
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
            self.assertEqual(set(bootstrap), {'old_bootstrap.py', 'terrier_standalone.py', 'desktop_credentials.py', 'terrier_github_snapshot.py'})
            for name, row in bootstrap.items():
                raw = (self.here / name).read_bytes()
                self.assertEqual((row['bytes'], row['sha256']), (len(raw), hashlib.sha256(raw).hexdigest()))

    def test_full_refresh_rehashes_source_and_includes_explicit_bootstrap_addition(self):
        python_specs, javascript_specs = declarations(refresh.outputs())
        self.assertEqual(python_specs, javascript_specs)
        for app, spec in python_specs.items():
            files = {(row['root'], row['path']): row for row in spec['programFiles']}
            self.assertIn(('bootstrap', 'terrier_standalone.py'), files)
            self.assertEqual(files[('source', app + '/app.py')]['sha256'], hashlib.sha256(b'changed source').hexdigest())
            self.assertEqual(('source', 'new_source.py') in files, app == 'melange')

    def test_app_selection_preserves_other_app_and_missing_bootstrap_is_refused(self):
        python_specs, _ = declarations(refresh.outputs(('melange',), bootstrap_only=True))
        self.assertEqual(python_specs['mentat'], self.specs['mentat'])
        (self.here / 'terrier_standalone.py').unlink()
        with self.assertRaisesRegex(ValueError, 'Reviewed program input is unavailable'):
            refresh.outputs(bootstrap_only=True)


if __name__ == '__main__':
    unittest.main()
