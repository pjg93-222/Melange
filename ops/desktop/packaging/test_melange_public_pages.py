"""Real source-row fixtures, requested-page I/O and native contract parity."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import melange_public_provenance as p
import melange_public_payroll_projection as projection
from module_data_snapshot import Snapshot
from module_public_input_installers import validate_public_snapshot, prepare_public_component
from test_melange_public_payroll_normalize import actual_fixture

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from fec.surfaces import melange_public_data as legacy
from fec.surfaces import melange_public_pages as pages
from fec.surfaces.demand_data import ChunkCache


class PagedPayrollTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        original = self.base / 'original'; original.mkdir()
        self.program = self.base / 'program'; self.program.mkdir()
        self.snapshot_root = self.base / 'snapshot'; (self.snapshot_root / 'public-data').mkdir(parents=True)
        projection_file = self.base / 'projection.ndjson'
        plan, _ = actual_fixture(original)
        with p.validated_inputs(original, plan) as inputs:
            receipt = projection.project_observations(inputs, projection_file)
        self.receipt_raw = p.canonical(receipt) + b'\n'
        self.raw_rows = projection_file.read_bytes().splitlines(keepends=True)
        self.rows = [p.strict_json(row) for row in self.raw_rows]
        starts = dict.fromkeys(legacy.ROLES, 0)
        self.remote = {}; chunks = []
        for raw, row in zip(self.raw_rows, self.rows):
            sha = hashlib.sha256(raw).hexdigest(); role = row['sourceRole']
            chunks.append({'id': f'page-{len(chunks)}', 'asset': sha + '.ndjson', 'bytes': len(raw),
                'sha256': sha, 'selectors': {'sourceRole': role, 'start': starts[role], 'count': 1}})
            self.remote[sha] = raw; starts[role] += 1
        self.index = {'schemaVersion': 1, 'appId': 'melange', 'kind': pages.KIND,
            'repository': pages.REPOSITORY, 'releaseTag': 'module-data-2026-10-22-pages', 'generation': 7,
            'receiptSha256': hashlib.sha256(self.receipt_raw).hexdigest(), 'format': 'strict-utf8-ndjson',
            'recordCounts': receipt['recordCounts'], 'chunks': chunks}
        self.native_cache = self.base / 'native-cache'; self.native_cache.mkdir()
        self.source = {'appId': 'melange', 'repository': 'pjg93-222/melange',
            'releaseTag': self.index['releaseTag'], 'catalogSequence': 7, 'cacheRoot': str(self.native_cache),
            'manifestSha256': '0' * 64}
        self.calls = []
        def fetch(chunk, output):
            self.calls.append(chunk['sha256']); output.write(self.remote[chunk['sha256']])
        self.cache = ChunkCache(self.native_cache / 'pages', max_bytes=64 * 1024, fetch=fetch)

    def snapshot(self):
        files, objects = {}, []
        for role, raw in [('index', p.canonical(self.index)), ('receipt', self.receipt_raw)]:
            target = self.snapshot_root / 'public-data' / (role + '.json'); target.write_bytes(raw)
            sha = hashlib.sha256(raw).hexdigest(); files[role] = str(target)
            objects.append({'role': role, 'bytes': len(raw), 'sha256': sha,
                'segments': [{'asset': role + '.bin', 'bytes': len(raw), 'sha256': sha}]})
        return Snapshot({'appId': 'melange', 'kind': pages.KIND, 'sourceRoot': str(self.program),
            'snapshotRoot': str(self.snapshot_root), 'files': files, 'objects': objects})

    def reader(self):
        value = pages.prepare_public_pages(self.snapshot(), self.source, cache=self.cache)
        self.addCleanup(value.close); return value

    def test_catalogue_and_provenance_require_zero_page_downloads(self):
        value = self.reader()
        self.assertEqual(value.catalogue()['sources'][0]['records'], 2)
        self.assertEqual(value.provenance(), p.strict_json(self.receipt_raw))
        self.assertEqual(self.calls, [])

    def test_only_requested_source_pages_download_and_response_matches_legacy(self):
        value = self.reader(); role = legacy.ROLES[0]
        first = value.observations(role, 0, 1)
        self.assertEqual(first['records'], self.rows[:1]); self.assertEqual(first['nextOffset'], 1)
        self.assertEqual(self.calls, [self.index['chunks'][0]['sha256']])
        second = value.observations(role, 0, 2)
        self.assertEqual(second['records'], self.rows[:2]); self.assertIsNone(second['nextOffset'])
        self.assertEqual(self.calls, [c['sha256'] for c in self.index['chunks'][:2]])
        # Cached pages remain usable when the network becomes unavailable.
        self.remote.clear()
        self.assertEqual(value.observations(role, 0, 2), second)

    def test_revision_and_pagination_refused_before_network(self):
        value = self.reader()
        for args, kwargs in [((legacy.ROLES[0], 0, 201), {}), ((legacy.ROLES[0], 3, 1), {}),
                             ((legacy.ROLES[0], 0, 1), {'revision': '0' * 64})]:
            with self.assertRaises(ValueError): value.observations(*args, **kwargs)
        self.assertEqual(self.calls, [])

    def test_corrupt_remote_bytes_never_return_rows(self):
        value = self.reader(); sha = self.index['chunks'][0]['sha256']
        self.remote[sha] = b'X' * len(self.remote[sha])
        with self.assertRaises((ValueError, OSError)): value.observations(legacy.ROLES[0], 0, 1)

    def test_index_rejects_gaps_overlap_totals_untrusted_destination_and_oversize(self):
        original = copy.deepcopy(self.index)
        for mutate in [lambda i: i['chunks'][0]['selectors'].update(start=1),
                       lambda i: i['chunks'][1]['selectors'].update(start=0),
                       lambda i: i['recordCounts'].update({'house-observations': 3}),
                       lambda i: i.update(repository='other/private'),
                       lambda i: i['chunks'][0].update(asset='../private'),
                       lambda i: i['chunks'][0].update(bytes=pages.MAX_PAGE_BYTES + 1)]:
            self.index = copy.deepcopy(original); mutate(self.index)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.reader()
        self.assertEqual(self.calls, [])

    def test_native_probe_checks_metadata_without_acquiring_any_pages(self):
        with patch('module_public_input_installers._program_module', return_value=legacy):
            validate_public_snapshot(self.snapshot())
        self.assertEqual(self.calls, [])

    def test_native_factory_dispatch_retains_public_component_type(self):
        with patch('module_public_input_installers._program_module', return_value=legacy):
            component = prepare_public_component(self.snapshot(), source=self.source)
        self.addCleanup(component['reader'].close)
        self.assertIs(type(component['reader']), pages.PagedPublicDataCatalogue)
        self.assertEqual(component['coverage'], {'completeKind': True, 'fullApplication': False})


if __name__ == '__main__': unittest.main()
