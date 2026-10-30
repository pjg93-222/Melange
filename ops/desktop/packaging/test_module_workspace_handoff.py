"""Synthetic code-bound dual-frame tests; production dataset acceptance is separate."""
import base64
import copy
import hashlib
import io
from pathlib import Path
import struct
import tempfile
import unittest

from module_application_contracts import ApplicationContract, ProgramFile, ModuleInputError, DataIntakeBlocked, canonical, program_fingerprint
from module_data_handoff import emit_data_blocked
from module_workspace_handoff import prepare_workspace_handoff, close_workspace_handoff, PreparedWorkspace, emit_workspace_data_blocked


def frame(value):
    raw = value if type(value) is bytes else canonical(value)
    return io.BytesIO(struct.pack('>I', len(raw)) + raw)


class DualHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='dual Jos\u00e9 profile ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.roots = {name: self.root / name for name in ('profile', 'source', 'data', 'state', 'bootstrap')}
        for path in self.roots.values():
            path.mkdir()
        self.original = self.roots['data'] / 'user-output.txt'
        self.original.write_bytes(b'original user output')
        self.program = self.roots['source'] / 'consumer.py'
        self.program.write_bytes(b'# synthetic compiled consumer\n')
        programs = (ProgramFile('source', 'consumer.py', self.program.stat().st_size,
                                hashlib.sha256(self.program.read_bytes()).hexdigest()),)
        self.calls, self.closed = [], []
        self.fail_workspace = False
        self.block_workspace = False
        self.contracts = {}
        fingerprint = program_fingerprint(programs)
        for channel, contract_id in (('public', 'mentat.public-data.v1'), ('workspace', 'mentat.workspace.v1')):
            def prepare(*, channel=channel, **options):
                self.calls.append(channel)
                if channel == 'workspace' and self.fail_workspace:
                    raise ValueError('synthetic rejected workspace')
                if channel == 'workspace' and self.block_workspace:
                    raise DataIntakeBlocked('storage')
                owner = self
                class Reader:
                    def close(self):
                        owner.closed.append(channel)
                return {'appId': 'mentat', 'source': options['source'], 'readers': {'mentat.synthetic.' + channel: {'reader': Reader()}},
                        'coverage': {'completeKind': True, 'fullApplication': False}}
            self.contracts[contract_id] = ApplicationContract('mentat', contract_id, fingerprint, programs,
                ('mentat.synthetic.' + channel,), ('synthetic.reader',), ('synthetic.original-output',), prepare, lambda *args: None)
        self.options = dict(app_id='mentat', profile_root=self.roots['profile'], source_root=self.roots['source'],
            original_data_root=self.roots['data'], state_root=self.roots['state'], bootstrap_root=self.roots['bootstrap'],
            lookup=lambda app, name: self.contracts.get(name) if app == 'mentat' else None)
        messages = []
        for channel in ('public', 'workspace'):
            contract = self.contracts['mentat.' + ('public-data.v1' if channel == 'public' else 'workspace.v1')]
            source = {'schemaVersion': 1, 'appId': 'mentat', 'repository': 'pjg93-222/mentat', 'catalogSequence': 7,
                      'releaseTag': 'module-data-2026-10-30-synthetic-' + channel, 'releaseCommit': 'c' * 40,
                      'pointerDigest': ('a' if channel == 'public' else 'd') * 64,
                      'manifestSha256': ('b' if channel == 'public' else 'e') * 64,
                      'cacheRoot': str(self.roots['profile'] / 'packs' / ('github-module-data' if channel == 'public' else 'github-workspace-data'))}
            messages.append({'schemaVersion': 1, 'appId': 'mentat', 'contractId': contract.contract_id,
                'programFingerprint': fingerprint, 'profileRoot': str(self.roots['profile']), 'sourceRoot': str(self.roots['source']),
                'originalDataRoot': str(self.roots['data']), 'stateRoot': str(self.roots['state']),
                'source': source, 'launchNonce': base64.urlsafe_b64encode(b'n' * 32).rstrip(b'=').decode(),
                'binding': {'contractId': contract.contract_id, 'programFingerprint': fingerprint,
                            'sourceDigest': source['manifestSha256'], 'sourceFingerprint': hashlib.sha256(canonical(source)).hexdigest()}})
        self.value = {'schemaVersion': 1, 'publicInput': messages[0], 'workspaceInput': messages[1]}

    def tearDown(self):
        self.assertEqual(self.original.read_bytes(), b'original user output')

    def test_both_independent_program_verified_inputs_share_one_launch_and_close(self):
        prepared = prepare_workspace_handoff(frame(self.value), **self.options)
        self.assertIs(type(prepared), PreparedWorkspace)
        self.assertEqual(self.calls, ['public', 'workspace'])
        self.assertEqual(prepared.public.roots, prepared.workspace.roots)
        self.assertNotEqual(prepared.public.source['manifestSha256'], prepared.workspace.source['manifestSha256'])
        close_workspace_handoff(prepared)
        self.assertEqual(self.closed, ['workspace', 'public'])

    def test_mixed_profile_owner_launch_program_and_cache_reject_before_either_factory(self):
        for key in ('appId', 'profileRoot', 'sourceRoot', 'originalDataRoot', 'stateRoot', 'launchNonce', 'programFingerprint'):
            value = copy.deepcopy(self.value)
            value['workspaceInput'][key] += '-other'
            with self.subTest(field=key), self.assertRaises(ModuleInputError):
                prepare_workspace_handoff(frame(value), **self.options)
        value = copy.deepcopy(self.value)
        value['workspaceInput']['source']['cacheRoot'] = value['publicInput']['source']['cacheRoot']
        with self.assertRaises(ModuleInputError):
            prepare_workspace_handoff(frame(value), **self.options)
        self.assertEqual(self.calls, [])

    def test_program_mutation_is_checked_independently_and_failed_second_input_closes_first(self):
        self.program.write_bytes(b'# mutated program\n')
        with self.assertRaises(ModuleInputError):
            prepare_workspace_handoff(frame(self.value), **self.options)
        self.assertEqual(self.calls, [])
        self.program.write_bytes(b'# synthetic compiled consumer\n')
        self.fail_workspace = True
        with self.assertRaises(ModuleInputError):
            prepare_workspace_handoff(frame(self.value), **self.options)
        self.assertEqual(self.calls, ['public', 'workspace'])
        self.assertEqual(self.closed, ['public'])

    def test_typed_dual_data_failure_diagnostic_binds_both_sources_and_closes_public(self):
        self.block_workspace = True
        with self.assertRaises(DataIntakeBlocked) as raised:
            prepare_workspace_handoff(frame(self.value), **self.options)
        output = io.StringIO()
        self.assertTrue(emit_data_blocked(raised.exception, output))
        self.assertEqual(raised.exception.native_status['sourceDigests'], {'public': 'b' * 64, 'workspace': 'e' * 64})
        self.assertEqual(raised.exception.native_status['reason'], 'storage')
        self.assertNotIn(str(self.root), output.getvalue())
        self.assertEqual(self.closed, ['public'])

    def test_missing_extra_duplicate_fields_boolean_version_trailing_bytes_and_cancel_reject(self):
        invalid = []
        value = copy.deepcopy(self.value); del value['publicInput']; invalid.append(frame(value))
        value = copy.deepcopy(self.value); value['path'] = 'C:/untrusted'; invalid.append(frame(value))
        value = copy.deepcopy(self.value); value['schemaVersion'] = True; invalid.append(frame(value))
        invalid.append(frame(b'{"schemaVersion":1,"schemaVersion":1}'))
        invalid.append(io.BytesIO(frame(self.value).getvalue() + b'extra'))
        for stream in invalid:
            with self.assertRaises(ModuleInputError):
                prepare_workspace_handoff(stream, **self.options)
        with self.assertRaises(ModuleInputError):
            prepare_workspace_handoff(frame(self.value), **self.options, is_cancelled=lambda: True)
        self.assertEqual(self.calls, [])

    def test_late_data_failure_attaches_only_the_still_verified_dual_context(self):
        prepared = prepare_workspace_handoff(frame(self.value), **self.options)
        try:
            blocked = DataIntakeBlocked('integrity')
            output = io.StringIO()
            self.assertTrue(emit_workspace_data_blocked(blocked, prepared, output))
            self.assertEqual(blocked.native_status['sourceDigests'], {'public': 'b' * 64, 'workspace': 'e' * 64})
            self.assertNotIn(str(self.root), output.getvalue())
            self.program.write_bytes(b'# replaced program before late data failure\n')
            refused = io.StringIO()
            with self.assertRaises(ModuleInputError):
                emit_workspace_data_blocked(DataIntakeBlocked('storage'), prepared, refused)
            self.assertEqual(refused.getvalue(), '')
            self.assertFalse(emit_workspace_data_blocked(ValueError('unknown program exception'), prepared, refused))
        finally:
            close_workspace_handoff(prepared)


if __name__ == '__main__':
    unittest.main()
