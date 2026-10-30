"""Generated parent-pipe fixtures; no production contracts or original inputs."""
import base64
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import module_application_contracts
from module_application_contracts import (ApplicationContract, ProgramFile, ModuleInputError, DataIntakeBlocked,
    application_contract, canonical, program_fingerprint, verify_program)
from module_data_handoff import (InstalledInputs, MAX_FRAME, installed_health,
    install_handoff, prepare_handoff, read_frame, planned_original_root, recheck_original_roots,
    server_installation, complete_server_installation, server_installed_health, emit_data_blocked)


def frame(value):
    raw = value if type(value) is bytes else canonical(value)
    return struct.pack('>I', len(raw)) + raw


class BlockingEOF(io.BytesIO):
    def __init__(self, raw):
        super().__init__(raw)
        self.release = threading.Event()

    def read(self, size=-1):
        raw = super().read(size)
        if not raw:
            self.release.wait(2)
        return raw


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='native-module-handoff-fixture-')
        self.root = Path(self.temporary.name)
        self.roots = {name: self.root / name for name in ('profile', 'source', 'data', 'state', 'bootstrap')}
        for root in self.roots.values():
            root.mkdir()
        self.original = self.roots['data'] / 'account.fixture'
        self.original.write_bytes(b'preserve original private fixture')
        self.events = []
        raw = b'# generated fixed consumer program\n'
        (self.roots['source'] / 'consumer.py').write_bytes(raw)
        programs = (ProgramFile('source', 'consumer.py', len(raw), hashlib.sha256(raw).hexdigest()),)
        self.kind = 'mentat.public-report-inputs.fixture.v1'
        def readers(**options):
            self.events.append(('prepare', options))
            return {'appId': 'mentat', 'source': dict(options['source']),
                    'readers': {self.kind: object()}, 'coverage': {'completeKind': True, 'fullApplication': False}}
        def installer(prepared, server, originals):
            self.events.append(('install', prepared))
            return InstalledInputs(server, {'mentat.report-source': prepared.readers[self.kind]}, dict(originals), lambda: True)
        self.contract = ApplicationContract('mentat', 'mentat.generated-pipe-fixture.v1', program_fingerprint(programs),
            programs, (self.kind,), ('mentat.report-source',), ('original.calibration', 'original.writable-roots'), readers, installer)
        source = {'schemaVersion': 1, 'appId': 'mentat', 'repository': 'pjg93-222/mentat', 'catalogSequence': 7,
                  'releaseTag': 'module-data-2026-10-22-fixture', 'releaseCommit': 'c' * 40,
                  'pointerDigest': 'a' * 64, 'manifestSha256': 'b' * 64,
                  'cacheRoot': str(self.roots['profile'] / 'packs' / 'github-module-data')}
        self.message = {'schemaVersion': 1, 'appId': 'mentat', 'contractId': self.contract.contract_id,
            'programFingerprint': self.contract.program_fingerprint, 'profileRoot': str(self.roots['profile']),
            'sourceRoot': str(self.roots['source']), 'originalDataRoot': str(self.roots['data']), 'stateRoot': str(self.roots['state']),
            'source': source, 'launchNonce': base64.urlsafe_b64encode(b'n' * 32).rstrip(b'=').decode(),
            'binding': {'contractId': self.contract.contract_id, 'programFingerprint': self.contract.program_fingerprint,
                        'sourceDigest': source['manifestSha256'], 'sourceFingerprint': hashlib.sha256(canonical(source)).hexdigest()}}
        self.options = dict(app_id='mentat', profile_root=self.roots['profile'], source_root=self.roots['source'],
            original_data_root=self.roots['data'], state_root=self.roots['state'], bootstrap_root=self.roots['bootstrap'],
            lookup=lambda app, name: self.contract if (app, name) == ('mentat', self.contract.contract_id) else None)
        self.before = (self.original.read_bytes(), self.original.stat().st_mtime_ns)
        module_application_contracts._VERIFIED.clear()
        self.addCleanup(module_application_contracts._VERIFIED.clear)
        self.stderr = io.StringIO()
        stderr = patch('sys.stderr', self.stderr)
        stderr.start()
        self.addCleanup(stderr.stop)

    def tearDown(self):
        self.assertEqual((self.original.read_bytes(), self.original.stat().st_mtime_ns), self.before)
        self.temporary.cleanup()

    def prepare(self, message=None, **options):
        return prepare_handoff(io.BytesIO(frame(self.message if message is None else message)), **{**self.options, **options})

    def test_only_typed_verified_data_failure_emits_bound_diagnostic_without_exception_text(self):
        def blocked(**_options):
            raise DataIntakeBlocked('integrity')
        self.contract = replace(self.contract, prepare_readers=blocked)
        with self.assertRaises(DataIntakeBlocked) as raised:
            self.prepare()
        output = io.StringIO()
        self.assertTrue(emit_data_blocked(raised.exception, output))
        line = output.getvalue()
        self.assertTrue(line.startswith('DESKTOP_DATA_BLOCKED '))
        value = json.loads(line.removeprefix('DESKTOP_DATA_BLOCKED '))
        self.assertEqual(value, {'schemaVersion': 1, 'appId': 'mentat', 'launchNonce': self.message['launchNonce'],
            'programFingerprint': self.contract.program_fingerprint, 'sourceDigests': {'public': 'b' * 64}, 'reason': 'integrity'})
        self.assertNotIn(str(self.root), line)
        self.assertFalse(emit_data_blocked(DataIntakeBlocked(), io.StringIO()))
        def unknown(**_options):
            raise ImportError('private source path must not enter diagnostic')
        self.contract = replace(self.contract, prepare_readers=unknown)
        with self.assertRaises(ModuleInputError) as unknown_error:
            self.prepare()
        self.assertIs(type(unknown_error.exception), ModuleInputError)
        self.assertFalse(emit_data_blocked(unknown_error.exception, io.StringIO()))

    def test_program_mutation_cannot_be_classified_as_data_blocked(self):
        def tampered(**_options):
            (self.roots['source'] / 'consumer.py').write_bytes(b'# mutated during data factory\n')
            raise DataIntakeBlocked('integrity')
        self.contract = replace(self.contract, prepare_readers=tampered)
        with self.assertRaises(ModuleInputError) as raised:
            self.prepare()
        self.assertIs(type(raised.exception), ModuleInputError)
        self.assertFalse(emit_data_blocked(raised.exception, io.StringIO()))

    def rejected(self, message):
        before = len(self.events)
        with self.assertRaises(ModuleInputError):
            self.prepare(message)
        self.assertEqual(len(self.events), before)

    def test_exact_parent_context_prepares_only_compiled_public_kind_and_preserves_original_roots(self):
        prepared = self.prepare()
        self.assertEqual(prepared.contract.required_kinds, (self.kind,))
        self.assertEqual(prepared.roots['originalDataRoot'], str(self.roots['data']))
        options = self.events[0][1]
        self.assertIs(options['native_verified'], True)
        self.assertNotIn('mentat.aggregate-forecast-core.v1', options['required_kinds'])
        self.assertEqual(dict(prepared.binding), self.message['binding'])
        with self.assertRaises(TypeError):
            prepared.source['cacheRoot'] = 'injected'

    def test_production_lookup_remains_unavailable_even_for_complete_looking_message(self):
        self.assertIsNone(application_contract('mentat', self.contract.contract_id))
        self.assertIsNone(application_contract('melange', 'melange.complete'))
        self.rejected({**self.message, 'complete': True})
        with self.assertRaises(ModuleInputError):
            self.prepare(lookup=None)
        self.assertEqual(self.events, [])

    def test_no_payload_native_verified_installer_kinds_or_environment_authority(self):
        for name, value in [('native_verified', True), ('installer', 'arbitrary.module'),
                            ('requiredKinds', ['mentat.aggregate-forecast-core.v1']), ('publicReaders', ['fake'])]:
            with self.subTest(name=name):
                self.rejected({**self.message, name: value})

    def test_wrong_cli_roots_app_contract_or_program_refuse_before_reader_callback(self):
        for key, value in [('appId', 'melange'), ('contractId', 'wrong'), ('programFingerprint', 'd' * 64),
                           ('profileRoot', str(self.roots['state'])), ('originalDataRoot', str(self.roots['source'])),
                           ('sourceRoot', str(self.roots['data'])), ('stateRoot', str(self.roots['profile']))]:
            with self.subTest(key=key):
                self.rejected({**self.message, key: value})

    def test_source_binding_is_recomputed_not_echoed_from_parent(self):
        for field in ('sourceDigest', 'sourceFingerprint', 'contractId', 'programFingerprint'):
            with self.subTest(field=field):
                self.rejected({**self.message, 'binding': {**self.message['binding'], field: 'wrong'}})
        self.rejected({**self.message, 'source': {**self.message['source'], 'repository': 'pjg93-222/melange'}})
        self.rejected({**self.message, 'source': {**self.message['source'], 'catalogSequence': True}})

    def test_launch_nonce_requires_exact_32_byte_canonical_base64url(self):
        for value in ('', 'n' * 42, 'n' * 44, '+' * 43, 'n' * 43, None):
            with self.subTest(value=value):
                self.rejected({**self.message, 'launchNonce': value})

    def test_missing_oversized_truncated_and_trailing_frames_refuse(self):
        for raw in (b'', b'\x00', struct.pack('>I', MAX_FRAME + 1), struct.pack('>I', 2) + b'{',
                    struct.pack('>I', 1) + b'0', frame(self.message) + b'extra'):
            with self.subTest(raw=raw[:10]), self.assertRaises(ModuleInputError):
                prepare_handoff(io.BytesIO(raw), **self.options)
        self.assertEqual(self.events, [])

    def test_oversized_header_is_refused_without_reading_or_allocating_its_body(self):
        class HeaderOnly:
            def __init__(self): self.reads = []
            def read(self, size):
                self.reads.append(size)
                if len(self.reads) > 1: raise AssertionError('Body must not be read')
                return struct.pack('>I', 2**32 - 1)
        stream = HeaderOnly()
        with self.assertRaises(ModuleInputError): read_frame(stream)
        self.assertEqual(stream.reads, [4])

    def test_invalid_utf8_duplicates_surrogates_nonfinite_and_excessive_depth_refuse(self):
        for raw in (b'\xff', b'{"schemaVersion":1,"schemaVersion":1}', b'{"x":NaN}', b'{"x":1.0}',
                    b'"\\ud800"', b'[' * 40 + b'0' + b']' * 40, b'{} trailing'):
            with self.subTest(raw=raw[:30]):
                self.rejected(raw)

    def test_noncanonical_valid_json_and_unsafe_integer_refuse_before_domain_imports(self):
        for raw in (json.dumps(self.message,indent=2).encode('utf-8'),
                    canonical(self.message).replace(b'"schemaVersion":1',b'"schemaVersion":1.0',1),
                    b'{"x":9007199254740992}'):
            self.rejected(raw)

    def test_source_fingerprint_preserves_unicode_and_original_descriptor_text(self):
        source={**self.message['source'],'cacheRoot':str(self.roots['profile']/'source-\u03bc'/'cache')}
        message={**self.message,'source':source,'binding':{**self.message['binding'],
            'sourceFingerprint':hashlib.sha256(canonical(source)).hexdigest()}}
        prepared=self.prepare(message)
        self.assertEqual(dict(prepared.source),source)
        self.assertEqual(prepared.binding['sourceFingerprint'],hashlib.sha256(canonical(source)).hexdigest())

    def test_missing_eof_has_real_finite_timeout_without_reader_or_state_work(self):
        stream = BlockingEOF(frame(self.message))
        started = time.monotonic()
        try:
            with self.assertRaises(ModuleInputError):
                prepare_handoff(stream, **self.options, timeout=0.03)
            self.assertLess(time.monotonic() - started, 1.0)
            self.assertEqual(self.events, [])
        finally:
            stream.release.set()

    def test_cancellation_interrupts_a_blocked_pipe_wait_and_never_prepares_readers(self):
        stream, cancelled = BlockingEOF(frame(self.message)), threading.Event()
        timer = threading.Timer(0.02, cancelled.set)
        timer.start()
        try:
            with self.assertRaises(ModuleInputError):
                prepare_handoff(stream, **self.options, timeout=0.5, is_cancelled=cancelled.is_set)
            self.assertEqual(self.events, [])
        finally:
            stream.release.set()
            timer.cancel()

    def test_changed_installed_program_refuses_before_domain_reader_import(self):
        path = self.roots['source'] / 'consumer.py'
        path.write_bytes(b'changed installed program')
        self.rejected(self.message)

    def test_program_change_during_reader_preparation_refuses_the_ready_context(self):
        original = self.contract.prepare_readers
        def changed(**options):
            result = original(**options)
            (self.roots['source'] / 'consumer.py').write_bytes(b'changed during reader preparation')
            return result
        self.contract = replace(self.contract, prepare_readers=changed)
        with self.assertRaises(ModuleInputError): self.prepare()

    def test_program_change_during_installer_never_issues_installed_health(self):
        original = self.contract.install_readers
        def changed(*options):
            result = original(*options)
            (self.roots['source'] / 'consumer.py').write_bytes(b'changed during actual installation')
            return result
        self.contract = replace(self.contract, install_readers=changed)
        prepared = self.prepare()
        with self.assertRaises(ModuleInputError):
            install_handoff(prepared, object(), {name: object() for name in self.contract.private_boundaries})

    def test_compiled_reader_cannot_claim_full_application_at_component_preflight(self):
        original = self.contract.prepare_readers
        def wrong(**options):
            result = original(**options)
            result['coverage']['fullApplication'] = True
            return result
        self.contract = replace(self.contract, prepare_readers=wrong)
        with self.assertRaises(ModuleInputError): self.prepare()

    def test_health_exists_only_after_exact_actual_installer_coverage_and_original_private_identity(self):
        prepared = self.prepare()
        with self.assertRaises(ModuleInputError): installed_health(prepared)
        originals = {name: object() for name in self.contract.private_boundaries}
        installed = install_handoff(prepared, object(), originals)
        health = installed_health(installed)
        self.assertEqual({key: health[key] for key in self.message['binding']}, self.message['binding'])
        self.assertEqual(health['launchNonce'], self.message['launchNonce'])
        self.assertEqual(len(health['coverageDigest']), 64)
        self.assertNotIn('cacheRoot', json.dumps(health))
        health['contractId'] = 'changed returned copy'
        self.assertEqual(installed_health(installed)['contractId'], self.contract.contract_id)

    def test_missing_extra_or_retargeted_original_private_context_never_issues_health(self):
        prepared = self.prepare()
        originals = {name: object() for name in self.contract.private_boundaries}
        for result in (InstalledInputs(object(), {}, originals),
                       InstalledInputs(object(), {'mentat.report-source': object()}, {name: object() for name in originals}),
                       {'fullApplication': True}):
            prepared_wrong = replace(prepared, contract=replace(self.contract, install_readers=lambda *_args, result=result: result))
            with self.subTest(result=type(result).__name__), self.assertRaises(ModuleInputError):
                install_handoff(prepared_wrong, object(), originals)

    def test_server_latch_health_requires_exact_once_actual_server_installation(self):
        prepared = self.prepare()
        originals = {name: object() for name in self.contract.private_boundaries}
        server = object()
        latch = server_installation(prepared, lambda actual: originals if actual is server else {})
        with self.assertRaises(ModuleInputError): server_installed_health(latch, server)
        complete_server_installation(latch, server)
        self.assertEqual(server_installed_health(latch, server)['launchNonce'], self.message['launchNonce'])
        with self.assertRaises(ModuleInputError): complete_server_installation(latch, server)
        with self.assertRaises(ModuleInputError): server_installed_health(latch, object())
        with self.assertRaises(ModuleInputError): server_installed_health({'complete': True}, server)
        with self.assertRaises(ModuleInputError): install_handoff(prepared, server, originals)

    def test_failed_actual_server_callback_cannot_be_reused_or_report_health(self):
        latch = server_installation(self.prepare(), lambda _server: {})
        server = object()
        with self.assertRaises(ModuleInputError): complete_server_installation(latch, server)
        with self.assertRaises(ModuleInputError): complete_server_installation(latch, server)
        with self.assertRaises(ModuleInputError): server_installed_health(latch, server)

    def test_installed_consumer_change_before_health_is_not_a_ready_result(self):
        ready = [True]
        original = self.contract.install_readers
        def installer(*args):
            return replace(original(*args), verify=lambda: ready[0])
        self.contract = replace(self.contract, install_readers=installer)
        prepared = self.prepare()
        installed = install_handoff(prepared, object(), {name: object() for name in self.contract.private_boundaries})
        self.assertEqual(installed_health(installed)['contractId'], self.contract.contract_id)
        ready[0] = False
        with self.assertRaises(ModuleInputError): installed_health(installed)

    def install(self):
        return install_handoff(self.prepare(), object(), {name: object() for name in self.contract.private_boundaries})

    def test_ordinary_health_reuses_install_verification(self):
        with patch('module_data_handoff.verify_program', wraps=verify_program) as scans:
            installed = self.install()
            self.assertEqual(scans.call_count, 4)  # prepare twice, install twice
            full = installed_health(installed)
            scans.reset_mock()
            for _ in range(50):
                self.assertEqual(installed_health(installed, full=False), full)
            self.assertEqual(scans.call_count, 0)
        self.assertEqual(self.stderr.getvalue().count('DESKTOP_PROGRAM_VERIFIED kind=module\n'), 2)
        self.assertNotIn(str(self.root), self.stderr.getvalue())

    def test_concurrent_ordinary_health_single_flight(self):
        installed = self.install()
        module_application_contracts._VERIFIED.clear()
        gate, started, calls, results, errors = threading.Event(), threading.Event(), [], [], []
        def slow(*args, **kwargs):
            calls.append(1)
            started.set()
            gate.wait(5)
            return verify_program(*args, **kwargs)
        def work():
            try:
                results.append(installed_health(installed, full=False))
            except Exception as error:
                errors.append(error)
        with patch('module_data_handoff.verify_program', side_effect=slow):
            threads = [threading.Thread(target=work) for _ in range(20)]
            for thread in threads:
                thread.start()
            self.assertTrue(started.wait(5))
            time.sleep(0.2)
            gate.set()
            for thread in threads:
                thread.join(10)
        self.assertEqual((len(calls), len(results), errors), (1, 20, []))

    def test_full_health_detects_change_and_poisons_generation(self):
        installed = self.install()
        self.assertEqual(installed_health(installed, full=False)['contractId'], self.contract.contract_id)
        with (self.roots['source'] / 'consumer.py').open('ab') as stream:
            stream.write(b'# appended after install\n')
        with patch('module_data_handoff.verify_program', wraps=verify_program) as scans:
            with self.assertRaises(ModuleInputError): installed_health(installed)
            self.assertEqual(scans.call_count, 1)
            scans.reset_mock()
            with self.assertRaises(ModuleInputError): installed_health(installed, full=False)
            self.assertEqual(scans.call_count, 0)  # the poisoned generation never re-verifies

    def test_ordinary_health_rejects_swapped_program_root(self):
        installed = self.install()
        source = self.roots['source']
        raw = (source / 'consumer.py').read_bytes()
        source.rename(source.with_name('source-moved'))
        source.mkdir()
        (source / 'consumer.py').write_bytes(raw)
        with self.assertRaises(ModuleInputError): installed_health(installed, full=False)

    def test_cache_never_crosses_launch_nonce(self):
        with patch('module_data_handoff.verify_program', wraps=verify_program) as scans:
            self.install()
            second = {**self.message, 'launchNonce': base64.urlsafe_b64encode(b'm' * 32).rstrip(b'=').decode()}
            prepared = self.prepare(second)
            scans.reset_mock()
            installed = install_handoff(prepared, object(), {name: object() for name in self.contract.private_boundaries})
            self.assertEqual(scans.call_count, 2)  # its own pre-install scan and its own generation scan
            scans.reset_mock()
            self.assertEqual(installed_health(installed, full=False)['launchNonce'], second['launchNonce'])
            self.assertEqual(scans.call_count, 0)
        self.assertEqual(len(module_application_contracts._VERIFIED), 2)

    def test_binding_change_still_fails_ordinary_health(self):
        ready = [True]
        original = self.contract.install_readers
        def installer(*args):
            return replace(original(*args), verify=lambda: ready[0])
        self.contract = replace(self.contract, install_readers=installer)
        installed = self.install()
        self.assertEqual(installed_health(installed, full=False)['contractId'], self.contract.contract_id)
        ready[0] = False
        with self.assertRaises(ModuleInputError): installed_health(installed, full=False)

    def test_installer_cannot_substitute_the_actual_server(self):
        original = self.contract.install_readers
        def wrong(prepared, server, originals):
            result = original(prepared, server, originals)
            return replace(result, application=object())
        self.contract = replace(self.contract, install_readers=wrong)
        prepared = self.prepare()
        with self.assertRaises(ModuleInputError):
            install_handoff(prepared, object(), {name: object() for name in self.contract.private_boundaries})

    def test_absent_original_writable_descendants_are_planned_without_mkdir(self):
        target = self.roots['data'] / 'new' / 'workspace'
        message = {**self.message, 'originalDataRoot': str(target)}
        prepared = self.prepare(message, original_data_root=target)
        self.assertFalse(target.exists())
        self.assertEqual(prepared.roots['originalDataRoot'], str(target))
        self.assertTrue(recheck_original_roots(prepared))
        target.mkdir(parents=True)
        self.assertTrue(recheck_original_roots(prepared))

    def test_original_planned_ancestor_replacement_refuses_before_owned_mkdir(self):
        ancestor=self.root/'future-parent';ancestor.mkdir();target=ancestor/'future-data'
        prepared=self.prepare({**self.message,'originalDataRoot':str(target)},original_data_root=target)
        ancestor.rename(self.root/'former-parent');ancestor.mkdir()
        with self.assertRaises(ModuleInputError):recheck_original_roots(prepared)
        self.assertFalse(target.exists())

    def test_unknown_planned_root_refuses_before_any_path_probe(self):
        from unittest.mock import patch
        with patch.object(Path, 'lstat', side_effect=AssertionError('No unapproved path probe')):
            with self.assertRaises(ModuleInputError):
                planned_original_root(str(self.roots['source'] / 'unknown'), str(self.roots['data']))

    def test_planned_root_overlap_and_unsafe_components_are_refused_read_only(self):
        for target in (str(self.roots['source']), str(self.roots['data'] / '..' / 'escape'),
                       str(self.roots['data'] / 'trailing.'), str(self.roots['data'] / 'NUL.txt')):
            with self.subTest(target=target), self.assertRaises(ModuleInputError):
                planned_original_root(target, target, protected_roots=(self.roots['source'],))

    @unittest.skipUnless(os.name=='nt','Actual Windows8.3 aliases require Windows')
    def test_actual_windows_short_protected_root_alias_refuses_future_original_overlap(self):
        import ctypes
        from ctypes import wintypes
        ancestor=self.root/'approved program directory long';ancestor.mkdir()
        call=ctypes.WinDLL('kernel32',use_last_error=True).GetShortPathNameW
        call.argtypes=(wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD);call.restype=wintypes.DWORD
        size=call(str(ancestor),None,0)
        if not size:self.skipTest('Windows volume did not provide an8.3 alias')
        buffer=ctypes.create_unicode_buffer(size+1)
        if not call(str(ancestor),buffer,len(buffer)) or buffer.value.casefold()==str(ancestor).casefold():
            self.skipTest('Windows volume8.3 name creation is unavailable')
        future=ancestor/'future-writable'
        with self.assertRaises(ModuleInputError):
            planned_original_root(str(future),str(future),protected_roots=(buffer.value,))
        self.assertFalse(future.exists())


class ProgramContractTests(unittest.TestCase):
    def test_program_paths_and_case_colliding_table_are_refused(self):
        for path in ('../secret.py', '/absolute.py', 'a//file.py', 'a\\file.py', 'C:/file.py'):
            with self.subTest(path=path), self.assertRaises(ModuleInputError):
                ProgramFile('source', path, 1, 'a' * 64)
        first = ProgramFile('source', 'One.py', 1, 'a' * 64)
        with self.assertRaises(ModuleInputError):
            program_fingerprint((first, replace(first, path='one.py')))

    def test_hardlinked_program_is_refused_read_only(self):
        import os
        with tempfile.TemporaryDirectory(prefix='module-program-fixture-') as directory:
            root = Path(directory)
            raw = b'synthetic program'
            (root / 'one.py').write_bytes(raw)
            os.link(root / 'one.py', root / 'two.py')
            files = (ProgramFile('source', 'one.py', len(raw), hashlib.sha256(raw).hexdigest()),)
            contract = ApplicationContract('mentat', 'fixture', program_fingerprint(files), files,
                ('mentat.public.fixture.v1',), ('reader',), ('original',), lambda: None, lambda: None)
            with self.assertRaises(ModuleInputError): verify_program(contract, source_root=root, bootstrap_root=root)
            self.assertEqual((root / 'one.py').read_bytes(), raw)
            self.assertEqual((root / 'one.py').stat().st_nlink, 2)


if __name__ == '__main__':
    unittest.main()
