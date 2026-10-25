"""Paged public module contracts, the publication seam and a second-profile consumer."""
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'fec'))
sys.path.insert(0, str(ROOT / 'fec' / 'surfaces'))
import module_application_contracts as contracts
from module_application_contracts import (PAGED_MODULES, ModuleInputError, check_module_bytes,
                                         paged_module, split_pages)
import generation_publish as gp
from demand_data import ChunkCache, CacheError, load_generation_index, read_module
import generation_publish_hook

# Lexemes a float round trip would change; pages must carry them untouched.
ROSTER = (b'{"schema":"roster-v3","members":[{"bioguide":"A000001","share":0.1000000000000000055511,'
          b'"amount":123456789012345678901.50,"tiny":1E-7}],"counts":{"n":1}}')
BILLS = b''.join(b'{"congress": 118, "sponsor": "S%06d", "weight": 1.230000000001}\n' % n for n in range(40))


# What collect_official_rollcall_events --install leaves under the data root (manifest uses CRLF, as written).
ROLLCALL = {
    'manifest.json': b'{\r\n  "acceptance_passed": true,\r\n  "outputs": {},\r\n  "schema": "official-rollcall-staging-v1"\r\n}\r\n',
    'official_rollcall_aggregate.json': b'{"schema":"a","members":{"A000001":{"Payments":{"lean":0.3333333333333333}}},"cells":[]}',
    'official_rollcall_member_votes.ndjson': b'{"schema":"v","event_id":"119:house:1:5","bioguide_id":"A000001"}\n',
    'official_rollcall_event_ledger.ndjson': b'{"schema":"e","event_id":"119:house:1:5"}\n',
    'rollcall_measure_match_audit.ndjson': b'{"schema":"m","canonical_key":"119:hr:1"}\n',
    'rollcall_direction_audit.ndjson': b'{"schema":"d","canonical_key":"119:hr:1"}\n',
    'source_snapshots.ndjson': b'{"schema":"s","content_sha256":"00"}\n',
}


def install_rollcall(data):
    target = data / 'data' / 'legislation' / 'official_rollcall'
    target.mkdir(parents=True, exist_ok=True)
    for name, raw in ROLLCALL.items():
        (target / name).write_bytes(raw)
    return target


def fixture_root(base):
    data = base / 'data-root'
    (data / 'data' / 'engine').mkdir(parents=True)
    (data / 'data' / 'holistic').mkdir(parents=True)
    (data / 'data' / 'engine' / 'roster.json').write_bytes(ROSTER)
    (data / 'data' / 'holistic' / 'billcache_118.ndjson').write_bytes(BILLS)
    return data


class ContractTests(unittest.TestCase):
    def test_every_contract_names_a_public_data_path_and_bounded_pages(self):
        self.assertGreaterEqual(len(PAGED_MODULES), 13)
        for module_id, module in PAGED_MODULES.items():
            with self.subTest(module_id):
                self.assertEqual(module.module_id, module_id)
                self.assertTrue(module.source.startswith('data/'))
                self.assertNotIn('approved', module.source)
                if module.format == 'json':
                    self.assertLessEqual(module.max_source_bytes, contracts.MAX_PAGE_BYTES)
                for partition in module.partitions:
                    self.assertNotIn('{', module.path(partition))

    def test_holistic_caches_are_partitioned_by_congress(self):
        for name in ('melange.holistic-sectorcache.v1', 'melange.holistic-billcache.v1'):
            module = paged_module(name)
            self.assertEqual((module.partition_key, module.partitions), ('congress', ('117', '118', '119')))
        module = paged_module('melange.holistic-billcache.v1')
        self.assertEqual(check_module_bytes(module, '118', BILLS), 40)
        with self.assertRaises(ModuleInputError):  # a row from another congress
            check_module_bytes(module, '117', BILLS)
        with self.assertRaises(ModuleInputError):
            check_module_bytes(module, '120', BILLS)

    def test_schema_size_and_strictness_refusals(self):
        roster = paged_module('melange.roster.v1')
        self.assertEqual(check_module_bytes(roster, '', ROSTER), 1)
        bills = paged_module('melange.holistic-billcache.v1')
        for module, partition, raw in [
                (roster, '', b'{"schema":1}'),                      # required key missing
                (roster, '', b'\xef\xbb\xbf' + ROSTER),             # BOM
                (roster, '', b'{"schema":1,"schema":2,"members":[]}'),  # duplicate key
                (roster, '', b'{"schema":NaN,"members":[]}'),        # non-finite
                (roster, '', b'[]'),
                (roster, '', b'x' * (roster.max_source_bytes + 1)),
                (bills, '118', BILLS[:-1]),                          # torn last record
                (bills, '118', BILLS.replace(b'\n', b'\r\n')),
                (bills, '118', b'{"congress": "118"}\n')]:            # partition lexeme type
            with self.subTest(raw=raw[:30]), self.assertRaises((ModuleInputError, ValueError)):
                check_module_bytes(module, partition, raw)
        with self.assertRaises(ModuleInputError):
            paged_module('melange.private-assertions.v1')

    def test_each_contract_schema_partition_and_size_limit(self):
        for module_id, module in PAGED_MODULES.items():
            for partition in module.partitions:
                with self.subTest(module_id=module_id, partition=partition):
                    row = {key: (int(partition) if key == module.partition_key else 1) for key in module.required_keys}
                    raw = json.dumps(row).encode() + (b'\n' if module.format == 'ndjson' else b'')
                    self.assertEqual(check_module_bytes(module, partition, raw), 1)
                    for key in module.required_keys:
                        broken = json.dumps({k: v for k, v in row.items() if k != key}).encode()
                        with self.assertRaises(ModuleInputError):
                            check_module_bytes(module, partition, broken + (b'\n' if module.format == 'ndjson' else b''))
                    with self.assertRaises(ModuleInputError):
                        check_module_bytes(module, partition, b' ' * (module.max_source_bytes + 1))

    @unittest.skipUnless(os.environ.get('MELANGE_CANONICAL_DATA_ROOT'), 'canonical data root not provided')
    def test_canonical_data_conforms_without_copying_it(self):
        root = Path(os.environ['MELANGE_CANONICAL_DATA_ROOT'])
        collected = {m for ids in contracts.COLLECTOR_MODULES.values() for m in ids}
        for module_id, module in PAGED_MODULES.items():
            for partition in module.partitions:
                if module_id in collected and not (root / module.path(partition)).exists():
                    continue  # installed only once its collector has run with install
                with self.subTest(module_id=module_id, partition=partition):
                    raw = (root / module.path(partition)).read_bytes()
                    self.assertGreater(check_module_bytes(module, partition, raw), 0)
                    self.assertEqual(b''.join(split_pages(module, raw)), raw)

    def test_collector_modules_are_registered_at_the_collectors_install_paths(self):
        from legislation import collect_official_rollcall_events as RC
        self.assertEqual(set(contracts.COLLECTOR_MODULES), {'official-rollcall', 'fec-money'})
        rollcall = {paged_module(m).path() for m in contracts.COLLECTOR_MODULES['official-rollcall']}
        self.assertEqual(rollcall, {(RC.INSTALL_DIR / name).as_posix() for name in (*RC.OUTPUT_NAMES, 'manifest.json')})
        self.assertEqual(paged_module('melange.fec-money-refresh.v1').path(), 'data/money/fec_refresh_current.json')
        for module_id in contracts.COLLECTOR_MODULES['official-rollcall']:
            module = paged_module(module_id)
            raw = ROLLCALL[module.path().rsplit('/', 1)[1]]
            self.assertEqual(check_module_bytes(module, '', raw), 1)
            self.assertEqual(split_pages(module, raw), [raw])

    def test_pages_are_original_bytes_split_on_record_ends(self):
        bills = paged_module('melange.holistic-billcache.v1')
        pages = split_pages(bills, BILLS, page_bytes=200)
        self.assertGreater(len(pages), 1)
        self.assertEqual(b''.join(pages), BILLS)
        self.assertTrue(all(len(page) <= 200 and page.endswith(b'\n') for page in pages))
        self.assertEqual(split_pages(paged_module('melange.roster.v1'), ROSTER), [ROSTER])


class FlakyTransport(gp.LocalDirectoryTransport):
    def get(self, name, limit):
        raw = super().get(name, limit)
        return raw[:-1] + bytes([raw[-1] ^ 1]) if name.endswith('.ndjson') else raw


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.data = fixture_root(self.base)
        self.modules = ('melange.roster.v1', 'melange.holistic-billcache.v1')
        self.tag = 'module-data-2026-10-23-pages-fixture'

    def publish(self, transport, staging='staging', **options):
        return gp.publish_generation(self.data, self.base / staging, transport, release_tag=self.tag,
                                     generation=3, modules=self.modules, partitions={'melange.holistic-billcache.v1': ('118',)},
                                     page_bytes=512, **options)

    def test_publication_written_last_and_only_after_every_readback(self):
        remote = self.base / 'remote'
        publication = self.publish(gp.LocalDirectoryTransport(remote))
        staging = self.base / 'staging'
        self.assertEqual(publication['status'], 'published')
        seal = json.loads((staging / 'seal.json').read_bytes())
        self.assertEqual(publication['verifiedAssets'], len(seal['assets']) + 1)  # plus seal.json
        self.assertEqual({a['asset'] for a in seal['assets']} | {'seal.json'}, {p.name for p in remote.iterdir()})
        # Ordering is pinned by test_corrupt_readback_never_marks_published; mtimes can tie on coarse filesystems.
        self.assertEqual({p.name for p in staging.iterdir()} - {a['asset'] for a in seal['assets']} - {'seal.json'},
                         {'publication.json'})
        index = json.loads((staging / 'index.json').read_bytes())
        self.assertLessEqual(len((staging / 'index.json').read_bytes()), contracts.MAX_MODULE_INDEX_BYTES)
        self.assertEqual(index['contractId'], 'melange.public-data.pages.v1')
        self.assertEqual(publication['indexSha256'], hashlib.sha256((staging / 'index.json').read_bytes()).hexdigest())

    def test_corrupt_readback_never_marks_published(self):
        with self.assertRaises(gp.PublicationError):
            self.publish(FlakyTransport(self.base / 'remote'))
        self.assertTrue((self.base / 'staging' / 'seal.json').exists())
        self.assertFalse((self.base / 'staging' / 'publication.json').exists())

    def test_contract_violation_leaves_no_seal(self):
        (self.data / 'data' / 'holistic' / 'billcache_118.ndjson').write_bytes(BILLS + b'{"congress": 117}\n')
        with self.assertRaises((ModuleInputError, gp.PublicationError)):
            self.publish(gp.LocalDirectoryTransport(self.base / 'remote'))
        self.assertFalse((self.base / 'staging' / 'seal.json').exists())
        self.assertFalse((self.base / 'remote').exists())

    def test_existing_staging_or_conflicting_remote_bytes_are_refused(self):
        (self.base / 'staging').mkdir()
        with self.assertRaises(gp.PublicationError):
            self.publish(gp.LocalDirectoryTransport(self.base / 'remote'))
        remote = self.base / 'remote2'
        self.publish(gp.LocalDirectoryTransport(remote), staging='s2')
        victim = next(remote.glob('*.ndjson'))
        victim.write_bytes(b'tampered\n')
        with self.assertRaises(gp.PublicationError):
            self.publish(gp.LocalDirectoryTransport(remote), staging='s3')

    def hook_config(self, modules=()):
        config = self.base / 'publish.json'
        config.write_text(json.dumps({'transport': {'kind': 'local', 'root': str(self.base / 'remote')},
            'stagingRoot': str(self.base / 'stagings'), 'modules': list(modules),
            'partitions': {'melange.holistic-billcache.v1': ['118']}, 'pageBytes': 512}), encoding='utf-8')
        return patch.dict(os.environ, {generation_publish_hook.ENVIRONMENT: str(config)})

    def test_hook_refuses_a_collection_whose_own_output_is_missing(self):
        installed = install_rollcall(self.data)
        (installed / 'official_rollcall_aggregate.json').unlink()
        with self.hook_config(self.modules), self.assertRaisesRegex(gp.PublicationError, 'not installed'):
            generation_publish_hook.after_collection('official-rollcall', self.data, generation=12)
        with self.hook_config(self.modules), self.assertRaisesRegex(gp.PublicationError, 'not installed'):
            generation_publish_hook.after_collection('fec-money', self.data, generation=13)
        with self.hook_config(self.modules), self.assertRaisesRegex(gp.PublicationError, 'No paged module'):
            generation_publish_hook.after_collection('fixture-scrape', self.data, generation=14)
        self.assertFalse((self.base / 'stagings').exists())
        self.assertFalse((self.base / 'remote').exists())

    def test_fixture_collection_publishes_and_second_profile_reads_exact_bytes(self):
        remote = self.base / 'remote'
        installed = install_rollcall(self.data)
        with self.hook_config(self.modules):
            publication = generation_publish_hook.after_collection('official-rollcall', self.data, generation=11)
        self.assertEqual(publication['status'], 'published')
        staging = Path(publication['staging'])
        index_raw = (staging / 'index.json').read_bytes()
        index = load_generation_index(index_raw, publication['indexSha256'])
        self.assertEqual(set(index['modules']), {*contracts.COLLECTOR_MODULES['official-rollcall'], *self.modules})
        fetched = []
        def fetch(chunk, output):
            fetched.append(chunk['asset']); output.write((remote / chunk['asset']).read_bytes())
        # A different profile: its own empty cache directory, fed only by the transport.
        profile_cache = ChunkCache(self.base / 'second-profile' / 'pages', max_bytes=4096, fetch=fetch)
        roster = read_module(index, 'melange.roster.v1', '', profile_cache)
        bills = read_module(index, 'melange.holistic-billcache.v1', '118', profile_cache)
        self.assertEqual((roster, bills), (ROSTER, BILLS))
        for module_id in contracts.COLLECTOR_MODULES['official-rollcall']:  # the collector's own output
            name = paged_module(module_id).path().rsplit('/', 1)[1]
            self.assertEqual(read_module(index, module_id, '', profile_cache), (installed / name).read_bytes())
        aggregate = json.loads(read_module(index, 'melange.official-rollcall-aggregate.v1', '', profile_cache),
                               parse_float=Decimal)
        self.assertEqual(str(aggregate['members']['A000001']['Payments']['lean']), '0.3333333333333333')
        value = json.loads(roster, parse_float=Decimal)
        self.assertEqual(str(value['members'][0]['share']), '0.1000000000000000055511')
        self.assertEqual(str(value['members'][0]['amount']), '123456789012345678901.50')
        self.assertEqual(str(value['members'][0]['tiny']), '1E-7')
        self.assertEqual(str(json.loads(bills.splitlines()[0], parse_float=Decimal)['weight']), '1.230000000001')
        # Offline reuse: the same profile answers from cache without the transport.
        offline = ChunkCache(self.base / 'second-profile' / 'pages', max_bytes=4096)
        self.assertEqual(read_module(index, 'melange.holistic-billcache.v1', '118', offline), BILLS)
        # Never-fetched data in a third profile is reported missing, not invented.
        with self.assertRaisesRegex(CacheError, 'not cached'):
            read_module(index, 'melange.roster.v1', '', ChunkCache(self.base / 'third' / 'pages', max_bytes=4096))

    def test_hook_is_inert_without_configuration(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(generation_publish_hook.ENVIRONMENT, None)
            self.assertIsNone(generation_publish_hook.after_collection('fec-money', self.data))
        self.assertFalse(any(self.base.glob('stag*')))


class FakeGitHub:
    def __init__(self, existing=None):
        self.calls, self.existing, self.uploads = [], existing, []
    def request(self, endpoint, method='GET', data=None, missing_ok=False):
        self.calls.append((method, endpoint, data))
        if endpoint.endswith('/releases/tags/t'):
            return self.existing
        if '?per_page=100' in endpoint and '/assets' not in endpoint:
            return []
        if endpoint.endswith('/commits/main'):
            return {'sha': 'a' * 40}
        if method == 'POST':
            return {'id': 7, 'draft': data['draft'], 'tag_name': data['tag_name']}
        if '/assets' in endpoint:
            return [{'name': name, 'size': 3, 'id': n} for n, name in enumerate(self.uploads)]
        raise AssertionError(endpoint)
    def upload(self, repository, tag, path):
        self.uploads.append(Path(path).name)


class GitHubDraftTransportTests(unittest.TestCase):
    def test_creates_only_a_draft_and_never_patches_it_public(self):
        api = FakeGitHub()
        transport = gp.GitHubDraftTransport('pjg93-222/Melange', 't', api=api)
        self.assertEqual(transport.describe()['releaseId'], 7)
        posts = [data for method, _endpoint, data in api.calls if method == 'POST']
        self.assertEqual(posts[0]['draft'], True)
        self.assertFalse(any(method == 'PATCH' for method, _e, _d in api.calls))
        with tempfile.TemporaryDirectory() as root:
            asset = Path(root) / 'x.json'; asset.write_bytes(b'abc')
            transport.put('x.json', asset, {'bytes': 3}); transport.put('x.json', asset, {'bytes': 3})
        self.assertEqual(api.uploads, ['x.json'])

    def test_refuses_to_add_assets_to_a_published_release(self):
        with self.assertRaises(gp.PublicationError):
            gp.GitHubDraftTransport('pjg93-222/Melange', 't', api=FakeGitHub({'id': 1, 'draft': False}))


if __name__ == '__main__':
    unittest.main()
