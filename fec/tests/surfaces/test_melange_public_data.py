"""Passive consumer tests; every document/row is generated synthetic fixture."""
import copy
import base64
import hashlib
import http.client
import json
import os
import io
import shutil
import struct
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'ops/desktop/packaging'))
import melange_public_provenance as p
import melange_public_payroll_projection as projection
import module_data_snapshot as boundary
from test_melange_public_payroll_normalize import actual_fixture
from fec.surfaces import melange_public_data as public
from fec.surfaces import staffer_live_server as live


class PublicDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.originals, self.source, self.snapshot_root = (self.root / n for n in ('originals', 'program', 'snapshot'))
        for path in (self.originals, self.source, self.snapshot_root):
            path.mkdir()
        self.output = self.snapshot_root / 'public-data'
        self.output.mkdir()
        self.plan, _ = actual_fixture(self.originals)
        self.data_file, self.receipt_file = self.output / 'observations.ndjson', self.output / 'receipt.json'
        with p.validated_inputs(self.originals, self.plan) as verified:
            self.receipt = projection.project_observations(verified, self.data_file)
        self.receipt_file.write_bytes(p.canonical(self.receipt) + b'\n')
        self.registry = patch.dict(boundary.KINDS, {public.KIND: ('melange', {
            'observations': ('public-data/observations.ndjson', public.MAX_BYTES),
            'receipt': ('public-data/receipt.json', p.MAX_JSON_BYTES)})})
        self.registry.start()
        self.reader = None

    def tearDown(self):
        if self.reader:
            self.reader.close()
        self.registry.stop()
        self.tmp.cleanup()

    def prepare(self, **kwargs):
        files = {'observations': self.data_file, 'receipt': self.receipt_file}
        objects = []
        for role, path in files.items():
            raw = path.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            objects.append({'role': role, 'bytes': len(raw), 'sha256': sha,
                'segments': [{'asset': role + '.bin', 'bytes': len(raw), 'sha256': sha}]})
        snapshot = boundary.Snapshot({'appId': 'melange', 'kind': public.KIND, 'sourceRoot': str(self.source),
            'snapshotRoot': str(self.snapshot_root), 'files': {k: str(v) for k, v in files.items()}, 'objects': objects})
        self.reader = public.prepare_public_data(snapshot, **kwargs)
        return self.reader

    def rewrite(self, rows=None, mutate_receipt=None):
        if rows is not None:
            raw = b''.join(p.canonical(r) + b'\n' for r in rows)
            self.data_file.write_bytes(raw)
            self.receipt['output'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), records=len(rows))
        if mutate_receipt:
            mutate_receipt(self.receipt)
        self.receipt_file.write_bytes(p.canonical(self.receipt) + b'\n')

    def test_catalogue_provenance_and_pages_are_detached_and_source_only(self):
        reader = self.prepare()
        self.assertEqual([s['id'] for s in reader.catalogue()['sources']], list(public.ROLES))
        first = reader.observations(public.ROLES[0], 0, 1)
        self.assertEqual(first['nextOffset'], 1)
        second = reader.observations(public.ROLES[0], first['nextOffset'], 1, revision=reader.revision)
        self.assertIsNone(second['nextOffset'])
        self.assertEqual(first['records'][0]['literalTokens']['payee'], 'DO.')
        before = reader.provenance()
        changed = reader.provenance()
        changed['sourceManifest']['documents'].clear()
        self.assertEqual(reader.provenance(), before)
        self.assertNotIn(str(self.originals), json.dumps(before))
        self.assertFalse(before['coverage']['fullApplication'])

    def test_hostile_pagination_and_stale_revision_are_rejected(self):
        reader = self.prepare()
        for source, offset, limit in [('private-graph', 0, 1), (public.ROLES[0], True, 1),
            (public.ROLES[0], -1, 1), (public.ROLES[0], 3, 1), (public.ROLES[0], 0, 201),
            (public.ROLES[0], 0, '100')]:
            with self.subTest(source=source, offset=offset, limit=limit), self.assertRaises(ValueError):
                reader.observations(source, offset, limit)
        with self.assertRaises(ValueError):
            reader.observations(public.ROLES[0], revision='0' * 64)

    def test_source_partition_order_is_producer_order_and_reversal_fails(self):
        rows = [p.strict_json(v) for v in self.data_file.read_bytes().splitlines()]
        rows[1], rows[2] = rows[2], rows[1]
        self.rewrite(rows)
        with self.assertRaises(ValueError):
            self.prepare()

    def long_rows(self):
        original = [p.strict_json(v) for v in self.data_file.read_bytes().splitlines()]
        expanded = [original[0]]
        template = original[1]
        for ordinal in range(1, 131):
            row = copy.deepcopy(template)
            row['source']['locator']['dataRow'] = ordinal
            row['recordId'] = 'government-observation:' + hashlib.sha256(p.canonical([
                row['sourceRole'], row['source']['sha256'], row['source']['locator']])).hexdigest()
            expanded.append(row)
        expanded.extend(original[2:])
        self.receipt['recordCounts']['house-observations'] = 131
        self.receipt['normalizationCounts']['houseCsvFieldEquivalentRows'] = 130
        for source in self.receipt['sourceManifest']['inputs']:
            if source['role'] == 'house-observations':
                source['records'] = 131
        self.receipt['inputManifestDigest'] = hashlib.sha256(p.canonical(self.receipt['sourceManifest'])).hexdigest()
        return expanded

    def test_sparse_index_seeks_across_block_and_source_boundaries(self):
        expanded = self.long_rows()
        self.rewrite(expanded)
        reader = self.prepare()
        page = reader.observations(public.ROLES[0], 127, 4)
        self.assertEqual([r['source']['locator']['dataRow'] for r in page['records']], [127, 128, 129, 130])
        self.assertIsNone(page['nextOffset'])
        self.assertEqual(reader.observations(public.ROLES[1], 0, 2)['records'][0]['sourceRole'], public.ROLES[1])

    def test_variable_utf8_and_crlf_byte_offsets_cross_sparse_boundary(self):
        rows = self.long_rows()
        for i, row in enumerate(rows):
            if row['source']['locator']['kind'] == 'csv-data-row':
                title = 'é' * (1 + i % 9)
                row['sourceExtracted']['title'] = row['literalTokens']['title'] = title
        raw = b''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode('utf8')
                       + (b'\r\n' if i % 2 else b'\n') for i, row in enumerate(rows))
        self.data_file.write_bytes(raw)
        self.receipt['output'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), records=len(rows))
        self.rewrite()
        reader = self.prepare()
        page = reader.observations(public.ROLES[0], 127, 4)
        self.assertEqual([r['source']['locator']['dataRow'] for r in page['records']], [127, 128, 129, 130])
        self.assertEqual(page['records'][1]['sourceExtracted']['title'], rows[128]['sourceExtracted']['title'])

    def test_unknown_private_fields_promotions_and_untrusted_urls_fail(self):
        original = [p.strict_json(v) for v in self.data_file.read_bytes().splitlines()]
        for mutate in (lambda r: r.update(private_note='Do not export'),
            lambda r: r['review'].update(identityPromoted=0),
            lambda r: r['source'].update(url='https://evil.invalid/a'),
            lambda r: r['extractionStatus'].update(method='UNREVIEWED_MERGE')):
            rows = copy.deepcopy(original)
            mutate(rows[0])
            self.rewrite(rows)
            with self.assertRaises(ValueError):
                self.prepare()

    def test_receipt_private_path_code_claim_and_count_drift_fail(self):
        original = copy.deepcopy(self.receipt)
        for mutate in (lambda r: r.update(originalPath='C:/private'),
            lambda r: r['canonicalPromotions'].update(identity=False),
            lambda r: r['normalizationCounts'].update(housePdfCandidateJoins=0),
            lambda r: r['currentMapperFiles'].update(private_mapper='0' * 64)):
            self.receipt = copy.deepcopy(original)
            self.rewrite(mutate_receipt=mutate)
            with self.assertRaises(ValueError):
                self.prepare()

    def test_input_path_and_handle_changes_are_refused_and_preserved(self):
        reader = self.prepare()
        self.data_file.write_bytes(self.data_file.read_bytes() + b'CHANGED')
        before = self.data_file.read_bytes(), self.data_file.stat().st_mtime_ns
        with self.assertRaises(ValueError):
            reader.catalogue()
        self.assertEqual(before, (self.data_file.read_bytes(), self.data_file.stat().st_mtime_ns))

    def test_cancelled_prepare_closes_owned_handles_without_writes(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.output.iterdir()}
        with self.assertRaises(ValueError):
            self.prepare(cancelled=lambda: True)
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.output.iterdir()})

    def test_forged_snapshot_or_direct_constructor_cannot_grant_authority(self):
        with self.assertRaises(ValueError):
            public.prepare_public_data({'approved': True})
        with self.assertRaises(ValueError):
            public.PublicDataCatalogue(None, None)
        with self.assertRaises(ValueError):
            self.prepare(validation_cache={'validated': True})

    def validation_cache(self, *, profile=None, fingerprint='a' * 64, source=None):
        from module_catalogue_cache import validation_cache
        profile = profile or self.root / 'profile'
        profile.mkdir(exist_ok=True)
        cache = validation_cache(profile=profile, program_fingerprint=fingerprint,
            source=source or {'manifestSha256': 'b' * 64, 'pointerDigest': 'c' * 64})
        self.assertIsNotNone(cache)
        return cache

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows DPAPI required')
    def test_protected_warm_index_skips_scan_but_pages_keep_row_checks(self):
        self.rewrite(self.long_rows())
        cache = self.validation_cache()
        cold = self.prepare(validation_cache=cache)
        expected = {(role, offset): cold.observations(role, offset, 4)
            for role in public.ROLES for offset in (0, max(0, cold._counts[role] - 4))}
        expected[public.ROLES[0], 127] = cold.observations(public.ROLES[0], 127, 4)
        self.assertFalse(cold._validation_cache_hit)
        cold.close()
        with patch.object(public, '_row', wraps=public._row) as row_check:
            warm = self.prepare(validation_cache=cache)
            self.assertTrue(warm._validation_cache_hit)
            self.assertEqual(row_check.call_count, 0)
            for (role, offset), page in expected.items():
                self.assertEqual(warm.observations(role, offset, 4), page)
            self.assertGreater(row_check.call_count, 0)

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows DPAPI required')
    def test_cache_ciphertext_owner_code_source_and_data_changes_require_scan(self):
        from module_catalogue_cache import KIND
        import native_access_state as protected
        cache = self.validation_cache()
        cold = self.prepare(validation_cache=cache)
        cold.close()
        raw = cache._target.read_bytes()
        # The same ciphertext cannot authorize a second profile.
        other = self.validation_cache(profile=self.root / 'other-profile')
        other._target.write_bytes(raw)
        reader = self.prepare(validation_cache=other)
        self.assertFalse(reader._validation_cache_hit)
        reader.close()
        for changed in (self.validation_cache(fingerprint='d' * 64),
                        self.validation_cache(source={'manifestSha256': 'e' * 64})):
            cache._target.write_bytes(raw)
            reader = self.prepare(validation_cache=changed)
            self.assertFalse(reader._validation_cache_hit)
            reader.close()
        cache._target.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        reader = self.prepare(validation_cache=cache)
        self.assertFalse(reader._validation_cache_hit)
        reader.close()
        value = protected.read(cache._profile, KIND)
        self.assertEqual(value['binding']['windowsSid'], protected.windows_sid())
        # Even an authenticated record with a wrong account identity is a miss.
        value['binding']['windowsSid'] = 'S-1-0-0'
        protected.write(cache._profile, KIND, value)
        reader = self.prepare(validation_cache=cache)
        self.assertFalse(reader._validation_cache_hit)
        reader.close()
        rows = [p.strict_json(v) for v in self.data_file.read_bytes().splitlines()]
        rows[0]['sourceExtracted']['title'] = 'changed synthetic title'
        self.rewrite(rows)
        reader = self.prepare(validation_cache=cache)
        self.assertFalse(reader._validation_cache_hit)

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows DPAPI required')
    def test_malformed_authenticated_offsets_are_misses_and_writes_are_optional(self):
        from module_catalogue_cache import KIND
        import native_access_state as protected
        self.rewrite(self.long_rows())
        cache = self.validation_cache()
        self.prepare(validation_cache=cache).close()
        original = protected.read(cache._profile, KIND)
        for mutate in (lambda v: v['index'][public.ROLES[0]].__setitem__(0, True),
                       lambda v: v['binding'].__setitem__('indexSchema', True),
                       lambda v: v['index'][public.ROLES[0]].__setitem__(1, 0),
                       lambda v: v['index'][public.ROLES[0]].append(1),
                       lambda v: v['index'][public.ROLES[1]].__setitem__(0, public.MAX_BYTES),
                       lambda v: v['counts'].__setitem__(public.ROLES[1], True),
                       lambda v: v.update(untrustedPath='C:/outside')):
            value = copy.deepcopy(original)
            mutate(value)
            protected.write(cache._profile, KIND, value)
            reader = self.prepare(validation_cache=cache)
            self.assertFalse(reader._validation_cache_hit)
            reader.close()
        cache._target.write_bytes(b'not a protected record')
        with patch('module_catalogue_cache.os.replace', side_effect=OSError('synthetic disk failure')):
            reader = self.prepare(validation_cache=cache)
            self.assertFalse(reader._validation_cache_hit)
            self.assertEqual(reader.catalogue()['status'], 'available')
        self.assertEqual(list(cache._profile.glob('*.tmp')), [])

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows DPAPI required')
    def test_warm_read_cancellation_and_changed_opened_content_refuse(self):
        from module_catalogue_cache import ValidationCache
        cache = self.validation_cache()
        self.prepare(validation_cache=cache).close()
        calls = 0
        def cancelled():
            nonlocal calls
            calls += 1
            return calls >= 2
        with self.assertRaises(ValueError):
            self.prepare(validation_cache=cache, cancelled=cancelled)
        original_load = ValidationCache.load
        def changed(instance, *args, **kwargs):
            result = original_load(instance, *args, **kwargs)
            raw = self.data_file.read_bytes()
            self.data_file.write_bytes(raw.replace(b'DO.', b'NO.', 1))
            return result
        with patch.object(ValidationCache, 'load', changed), self.assertRaises(ValueError):
            self.prepare(validation_cache=cache)

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows DPAPI required')
    def test_verified_parent_handoff_runs_real_public_wrapper_and_profile_bound_cache(self):
        # Generated parent/protocol fixture; real reader and DPAPI, no network.
        from module_application_contracts import (ApplicationContract, ProgramFile,
            ModuleInputError, canonical, program_fingerprint)
        from module_data_handoff import prepare_handoff
        from module_data_launch import APPS
        from module_public_input_installers import (prepare_public_readers, install_public_readers,
            PUBLIC_IDS, PRIVATE_IDS)
        self.prepare().close()
        profile = self.root / 'parent-profile'
        profile.mkdir()
        cache = profile / 'packs/github-module-data'
        for name in ('pointers', 'manifests', 'snapshots'):
            (cache / name).mkdir(parents=True)
        repository, purpose = APPS['melange']
        objects = []
        for role, path in (('observations', self.data_file), ('receipt', self.receipt_file)):
            raw = path.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            objects.append({'role': role, 'bytes': len(raw), 'sha256': sha,
                'segments': [{'asset': role + '.bin', 'bytes': len(raw), 'sha256': sha}]})
        tag = 'module-data-2026-10-22-fixture'
        dataset_id = '11111111-1111-4111-8111-111111111111'
        manifest = {'schemaVersion': 1, 'purpose': purpose + 'sets', 'appId': 'melange',
            'repository': repository, 'releaseTag': tag, 'datasets': [{'datasetId': dataset_id,
            'revisionId': '22222222-2222-4222-8222-222222222222', 'kind': public.KIND,
            'adapterVersion': 1, 'objects': objects, 'counts': {'files': 2}}]}
        manifest_raw = canonical(manifest)
        manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
        pointer = {'schemaVersion': 1, 'purpose': purpose, 'appId': 'melange', 'repository': repository,
            'catalogSequence': 1, 'releaseTag': tag, 'releaseCommit': 'a' * 40,
            'manifest': {'asset': 'manifest.json', 'bytes': len(manifest_raw), 'sha256': manifest_sha}}
        pointer_raw = canonical(pointer)
        pointer_sha = hashlib.sha256(pointer_raw).hexdigest()
        envelope = {'schemaVersion': 1, 'keyId': 'synthetic-native-key',
            'payload': base64.b64encode(pointer_raw).decode(), 'signature': base64.b64encode(b'\0' * 64).decode()}
        (cache / 'pointers' / (pointer_sha + '.json')).write_bytes(canonical(envelope))
        (cache / 'manifests' / (manifest_sha + '.json')).write_bytes(manifest_raw)
        target = cache / 'snapshots' / manifest_sha / dataset_id / 'public-data'
        target.mkdir(parents=True)
        shutil.copy2(self.data_file, target / self.data_file.name)
        shutil.copy2(self.receipt_file, target / self.receipt_file.name)
        source = {'schemaVersion': 1, 'appId': 'melange', 'repository': repository, 'catalogSequence': 1,
            'releaseTag': tag, 'releaseCommit': 'a' * 40, 'manifestSha256': manifest_sha,
            'pointerDigest': pointer_sha, 'cacheRoot': str(cache)}
        actual_source = ROOT / 'fec/surfaces/melange_public_data.py'
        raw = actual_source.read_bytes()
        files = (ProgramFile('source', 'fec/surfaces/melange_public_data.py', len(raw), hashlib.sha256(raw).hexdigest()),)
        contract = ApplicationContract('melange', 'melange.public-data.v1', program_fingerprint(files), files,
            (public.KIND,), PUBLIC_IDS['melange'], PRIVATE_IDS['melange'], prepare_public_readers, install_public_readers)
        data, state = self.root / 'handoff-data', self.root / 'handoff-state'
        data.mkdir(); state.mkdir()
        binding = {'contractId': contract.contract_id, 'programFingerprint': contract.program_fingerprint,
            'sourceDigest': manifest_sha, 'sourceFingerprint': hashlib.sha256(canonical(source)).hexdigest()}
        message = {'schemaVersion': 1, 'appId': 'melange', 'contractId': contract.contract_id,
            'programFingerprint': contract.program_fingerprint, 'profileRoot': str(profile), 'sourceRoot': str(ROOT),
            'originalDataRoot': str(data), 'stateRoot': str(state), 'source': source, 'binding': binding,
            'launchNonce': base64.urlsafe_b64encode(b'x' * 32).rstrip(b'=').decode()}
        def run(value):
            raw = canonical(value)
            return prepare_handoff(io.BytesIO(struct.pack('>I', len(raw)) + raw), app_id='melange',
                profile_root=profile, source_root=ROOT, original_data_root=data, state_root=state,
                bootstrap_root=ROOT / 'ops/desktop/packaging')
        with patch('module_application_contracts.application_contract', return_value=contract), \
             patch('module_data_handoff.application_contract', return_value=contract), \
             patch.object(sys.modules['fec'], '__path__', [str(ROOT / 'fec')]), \
             patch.object(sys.modules['fec.surfaces'], '__path__', [str(ROOT / 'fec/surfaces')]):
            first = run(message).readers[public.KIND]['reader']
            self.assertFalse(first._validation_cache_hit)
            expected = first.observations(public.ROLES[0], 0, 2)
            first.close()
            second = run(message).readers[public.KIND]['reader']
            self.assertTrue(second._validation_cache_hit)
            self.assertEqual(second.observations(public.ROLES[0], 0, 2), expected)
            second.close()
            for changed in ({**message, 'profileRoot': str(self.root)},
                            {**message, 'programFingerprint': '0' * 64},
                            {**message, 'source': {**source, 'manifestSha256': '0' * 64}}):
                with patch('module_catalogue_cache.validation_cache') as make_cache, self.assertRaises(ModuleInputError):
                    run(changed)
                make_cache.assert_not_called()

    def test_fixed_route_seam_uses_only_installed_public_reader(self):
        reader = self.prepare()
        responses = []
        handler = SimpleNamespace(send_bytes=lambda body, mime, status=200: responses.append((body, mime, status)))
        self.assertTrue(public.handle_public_data_request(handler, '/api/public-data/catalogue', '', reader))
        self.assertEqual(json.loads(responses[-1][0])['status'], 'available')
        self.assertTrue(public.handle_public_data_request(handler, '/api/public-data/observations',
            'source=house-observations&offset=0&limit=1', reader))
        self.assertEqual(len(json.loads(responses[-1][0])['records']), 1)
        self.assertTrue(public.handle_public_data_request(handler, '/api/public-data/observations',
            'source=private-graph&path=C:/private', reader))
        self.assertEqual(responses[-1][2], 400)
        self.assertTrue(public.handle_public_data_request(handler, '/api/public-data/provenance', '', None))
        self.assertEqual(responses[-1][2], 503)
        count = len(responses)
        self.assertFalse(public.handle_public_data_request(handler, '/api/staffer-person', '', reader))
        self.assertEqual(len(responses), count)

    def test_assets_come_from_fixed_program_root_without_workspace_reads(self):
        responses = []
        handler = SimpleNamespace(send_bytes=lambda body, mime, status=200: responses.append((body, mime, status)))
        for path in ('/public-data/', '/public-data/public-data.js', '/public-data/public-data.css'):
            self.assertTrue(public.handle_public_data_request(handler, path, '', None))
            self.assertTrue(responses[-1][0])
        self.assertFalse(public.handle_public_data_request(handler, '/public-data/../../private', '', None))


class ServerSeamTests(unittest.TestCase):
    def setUp(self):
        self.fixture = PublicDataTests()
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def request(self, server, path, host=None):
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        try:
            connection.request('GET', path, headers={'Host': host or f'127.0.0.1:{server.server_port}'})
            response = connection.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            connection.close()

    def served(self, reader, inspect):
        class PrivateContext:
            def __getattribute__(self, name):
                raise AssertionError('Public route accessed the original private service')
        server = live.WorkspaceServer(('127.0.0.1', 0), live.Handler)
        server.dashboard = PrivateContext()
        server.public_data = reader
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
        thread.start()
        try:
            return inspect(server)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)

    def test_actual_http_fixed_routes_and_program_assets_do_not_read_private_context(self):
        reader = self.fixture.prepare()
        def inspect(server):
            status, raw, _ = self.request(server, '/api/public-data/catalogue')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw), reader.catalogue())
            status, raw, _ = self.request(server, '/api/public-data/provenance')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw), reader.provenance())
            status, raw, _ = self.request(server, '/api/public-data/observations?source=house-observations&offset=0&limit=1')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw), reader.observations(public.ROLES[0], 0, 1))
            for endpoint, name in (('/public-data/', 'index.html'),
                ('/public-data/public-data.js', 'public-data.js'), ('/public-data/public-data.css', 'public-data.css')):
                status, raw, headers = self.request(server, endpoint)
                self.assertEqual(status, 200)
                self.assertEqual(raw, (Path(public.__file__).parent / 'public_data' / name).read_bytes())
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        # The public UI is installed program content even when the old dashboard
        # points at a different original asset root.
        with patch.object(live, 'ASSETS', self.fixture.originals / 'unused-private-assets'):
            self.served(reader, inspect)

    def test_actual_http_host_and_fixed_query_guards_precede_private_lookup(self):
        def inspect(server):
            for endpoint in ('/public-data/', '/api/public-data/catalogue', '/api/public-data/observations?source=house-observations'):
                self.assertEqual(self.request(server, endpoint, host='foreign.invalid')[0], 403)
            for query in ('source=private-graph', 'source=house-observations&party=D',
                'source=house-observations&source=house-observations', 'source=house-observations&limit=201',
                'source=house-observations&offset=-1', 'source=house-observations&path=../../private'):
                self.assertEqual(self.request(server, '/api/public-data/observations?' + query)[0], 400)
            self.assertEqual(self.request(server, '/api/public-data/catalogue?path=private')[0], 400)
        self.served(self.fixture.prepare(), inspect)

    def test_actual_http_without_public_reader_is_explicitly_unavailable(self):
        def inspect(server):
            for endpoint in ('/api/public-data/catalogue', '/api/public-data/provenance',
                             '/api/public-data/observations?source=house-observations'):
                status, raw, _ = self.request(server, endpoint)
                self.assertEqual(status, 503)
                self.assertEqual(json.loads(raw)['error'], 'Verified public data is not loaded.')
            self.assertEqual(self.request(server, '/public-data/')[0], 200)
        self.served(None, inspect)

    def launch(self, reader=None, hook=None):
        events, objects = [], {}
        original_root = self.fixture.originals
        class Graph:
            def __init__(self, root):
                events.append('graph')
                self.root = root
                objects['graph'] = self
        class Service:
            def __init__(self, root, graph):
                events.append('service')
                self.root, self.graph = root, graph
                objects['service'] = self
            def start(self):
                events.append('start')
        class Server:
            def __init__(self, address, handler):
                events.append('server')
                self.address, self.handler, self.closed = address, handler, False
                objects['server'] = self
            def serve_forever(self):
                events.append('serve')
            def server_close(self):
                self.closed = True
                events.append('close')
        def callback(server):
            events.append('callback')
            self.assertIs(server, objects['server'])
            self.assertIs(server.public_data, reader)
            self.assertIs(server.dashboard, objects['service'])
            self.assertIs(server.dashboard.graph, objects['graph'])
            self.assertEqual(server.dashboard.root, original_root)
            self.assertEqual(server.dashboard.graph.root, original_root)
            self.assertEqual(server.dashboard_file, 'Moneyball_Redesign.html')
            self.assertEqual(events, ['graph', 'service', 'server', 'callback'])
            if hook:
                hook(server)
        with patch.dict(sys.modules, {
            'fec.surfaces.staffer_graph_snapshot': SimpleNamespace(StaticGraph=Graph),
            'fec.surfaces.staffer_live_service': SimpleNamespace(LiveService=Service)}), \
            patch.object(live, 'WorkspaceServer', Server), \
            patch.object(sys, 'argv', ['server', '--source-root', str(original_root), '--port', '0',
                                     '--dashboard-file', 'Moneyball_Redesign.html']), \
            patch('builtins.print', side_effect=lambda *a, **k: events.append('print')):
            try:
                if hook is False:
                    live.main()
                else:
                    live.main(public_data=reader, on_server_ready=callback)
            finally:
                self.last_events, self.last_objects = events, objects
        return events, objects

    def test_main_callback_once_after_actual_context_attachment_before_start_and_serve(self):
        reader = self.fixture.prepare()
        events, objects = self.launch(reader)
        self.assertEqual(events, ['graph', 'service', 'server', 'callback', 'start', 'print', 'serve', 'close'])
        self.assertTrue(objects['server'].closed)
        self.assertEqual(reader.catalogue()['status'], 'available')

    def test_main_callback_failure_closes_only_new_server_without_start_or_readiness(self):
        reader = self.fixture.prepare()
        def refuse(server):
            raise ValueError('Program installation refused')
        with self.assertRaisesRegex(ValueError, 'Program installation refused'):
            self.launch(reader, refuse)
        self.assertEqual(self.last_events, ['graph', 'service', 'server', 'callback', 'close'])
        self.assertTrue(self.last_objects['server'].closed)
        self.assertEqual(reader.catalogue()['status'], 'available')

    def test_main_ordinary_defaults_preserve_original_service_root_and_no_public_reader(self):
        events, objects = self.launch(hook=False)
        self.assertEqual(events, ['graph', 'service', 'server', 'start', 'print', 'serve', 'close'])
        self.assertIsNone(objects['server'].public_data)
        self.assertEqual(objects['service'].root, self.fixture.originals)
        self.assertIs(objects['service'].graph, objects['graph'])

    def test_main_refuses_unprepared_data_and_nonprogram_hook_before_server_creation(self):
        with patch.object(live, 'WorkspaceServer', side_effect=AssertionError('Listener must not be constructed')):
            with self.assertRaises(ValueError):
                live.main(public_data={'snapshotRoot': 'untrusted'})
            with self.assertRaises(ValueError):
                live.main(on_server_ready='downloaded-hook')


if __name__ == '__main__':
    unittest.main()
