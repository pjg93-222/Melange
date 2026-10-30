"""Generated context/negative-verdict tests; program verifier is explicitly mocked."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import module_application_contracts
from module_application_contracts import ModuleInputError
import terrier_runtime_handoff as handoff


class DistrictRuntimeHandoffTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='district-input-context-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        paths = {name: self.root / name for name in ('profile', 'source', 'data', 'state')}
        for value in paths.values():
            value.mkdir()
        self.options = SimpleNamespace(app='terrier', district='co-05', github_district_data=True,
            windows_session=False, source_root=paths['source'], data_root=paths['data'], state_root=paths['state'], profile_root=paths['profile'])
        key = 'co-cd005-123456abcdef'
        roles = sorted([*handoff.ROLES, *('snapshots/' + key + '/' + name for name in handoff.BASE_FILES)])
        files = []
        for role in roles:
            file = paths['data'] / role
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'{}')
            files.append({'role': role, 'path': 'co-05/data/' + role, 'bytes': 2, 'sha256': '1' * 64})
        names = {'profileRoot': paths['profile'], 'sourceRoot': paths['source'], 'dataRoot': paths['data'], 'stateRoot': paths['state']}
        values = {name: str(value) for name, value in names.items()}
        self.value = {'schemaVersion': 1, 'appId': 'terrier', 'district': 'co-05', 'launchNonce': 'a' * 43,
            'programFingerprint': '2' * 64, 'sourceDigest': handoff.digest({'district': 'co-05', 'files': files}),
            'rootsDigest': handoff.digest(values), 'commitToken': 'b' * 43, 'files': files, **values}
        self.program = patch.object(handoff, 'verify_district_program', return_value='2' * 64)
        self.verify_program = self.program.start()
        self.addCleanup(self.program.stop)
        module_application_contracts._VERIFIED.clear()
        self.addCleanup(module_application_contracts._VERIFIED.clear)

    def create(self):
        return handoff.DistrictRuntimeInput(copy.deepcopy(self.value), self.options)

    def test_context_nonce_roster_program_and_roots_cannot_be_forged(self):
        for field, bad in (('launchNonce', 'short'), ('programFingerprint', '3' * 64),
                           ('sourceDigest', '4' * 64), ('rootsDigest', '5' * 64)):
            value = copy.deepcopy(self.value)
            value[field] = bad
            with self.subTest(field=field), self.assertRaises(ModuleInputError):
                handoff.DistrictRuntimeInput(value, self.options)

    def test_negative_data_leaf_is_bound_and_redacted_but_import_or_program_failure_is_not(self):
        context = self.create()
        for error, reason in ((ValueError('private factual data'), 'integrity'), (OSError('private path'), 'storage')):
            with self.assertRaises(handoff.DistrictActivationBlocked) as caught:
                context.data_call(lambda: (_ for _ in ()).throw(error))
            output = io.StringIO()
            self.assertTrue(handoff.emit_district_blocked(caught.exception, output))
            text = output.getvalue()
            self.assertNotIn('private', text)
            self.assertNotIn(self.value['commitToken'], text)
            self.assertIn('"reason":"' + reason + '"', text)
        with self.assertRaises(ImportError):
            context.data_call(lambda: (_ for _ in ()).throw(ImportError('synthetic import')))
        self.verify_program.side_effect = ModuleInputError()
        with self.assertRaises(ModuleInputError):
            context.data_call(lambda: (_ for _ in ()).throw(ValueError('untrusted data')))

    def test_private_commit_is_single_use_and_actual_reader_status_changes_only_after_it(self):
        context = self.create()
        class Reader:
            committed = False
            def commit(self): self.committed = True
            def health(self): return {'snapshot': 'co-cd005-123456abcdef', 'phase': 'active' if self.committed else 'prepared'}
        context.reader = Reader()
        self.assertEqual(context.health()['phase'], 'prepared')
        self.assertFalse(context.commit('wrong'))
        self.assertFalse(context.reader.committed)
        self.assertTrue(context.commit(self.value['commitToken']))
        self.assertEqual(context.health()['phase'], 'active')
        self.assertFalse(context.commit(self.value['commitToken']))

    def test_district_health_poll_does_not_rehash(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            context = self.create()
        self.assertEqual(stderr.getvalue().count('DESKTOP_PROGRAM_VERIFIED kind=district\n'), 1)
        class Reader:
            def commit(self): pass
            def health(self): return {'snapshot': 'co-cd005-123456abcdef', 'phase': 'prepared'}
        context.reader = Reader()
        self.verify_program.reset_mock()
        for _ in range(10):
            self.assertEqual(context.health()['phase'], 'prepared')
        self.assertEqual(self.verify_program.call_count, 0)
        self.assertTrue(context.commit(self.value['commitToken']))
        self.assertGreaterEqual(self.verify_program.call_count, 1)

    def test_late_file_mutation_blocks_commit_without_changing_reader(self):
        context = self.create()
        context.reader = SimpleNamespace(commit=lambda: self.fail('No active commit permitted'))
        (self.options.data_root / 'density.json').write_bytes(b'{"changed":true}')
        with self.assertRaises(handoff.DistrictActivationBlocked):
            context.commit(self.value['commitToken'])


if __name__ == '__main__':
    unittest.main()
