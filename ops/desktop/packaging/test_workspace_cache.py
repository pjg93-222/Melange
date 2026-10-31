"""Native derived-cache fixtures; no claim about production model parity."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from module_application_contracts import DataIntakeBlocked
from workspace_archive import DomainArchive
from workspace_data_contract import ARCHIVE_MEMBERS, INDUSTRY_PAGES_KIND, REPORT_ANALYSIS_KIND, STAFFER_ANALYSIS_KIND
from workspace_sqlite import SCHEMAS
import workspace_cache as cache


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='derived native ü ')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.profile = self.base / 'profile ü with spaces'
        self.profile.mkdir()
        self.original, self.state = self.base / 'original', self.base / 'state'
        for root in (self.original, self.state):
            root.mkdir()
            (root / 'keep').write_bytes(b'untouched')
        self.archive = self.base / 'signed.data.zip'
        self.kind, self.app, self.role = INDUSTRY_PAGES_KIND, 'melange', 'pages'

    def make(self, *, bad_hash=False, bad_schema=False):
        payloads = {}
        for name in ARCHIVE_MEMBERS[(self.app, self.kind, self.role)][0]:
            if name == 'derivation.json':
                continue
            if name.endswith('.sqlite'):
                file = self.base / ('source-' + name.split('/')[0] + '.sqlite')
                db = sqlite3.connect(file)
                db.executescript('CREATE TABLE surprise(value);' if bad_schema else SCHEMAS['mentat-facts'])
                db.close()
                payloads[name] = file.read_bytes()
            else:
                payloads[name] = b'{"fixture":true}'
        descriptors = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                       for name, raw in payloads.items()}
        if bad_hash:
            descriptors[next(iter(descriptors))]['sha256'] = '0' * 64
        derivation = {'schemaVersion': 1, 'kind': self.kind, 'members': descriptors,
                      'fixtureProvenance': {'synthetic': True}}
        payloads['derivation.json'] = json.dumps(derivation, separators=(',', ':')).encode()
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, raw in payloads.items():
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                archive.writestr(info, raw)
        self.sha = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        return payloads

    def open(self, **options):
        return cache.prepare_cache(profile_root=str(self.profile), app_id=self.app, kind=self.kind,
                                   role=self.role, archive_path=self.archive, expected_sha256=self.sha, **options)

    def namespace(self):
        return self.profile / 'packs' / 'github-workspace-derived'

    def test_fresh_and_warm_reuse_verify_signed_members_without_reextracting(self):
        payloads = self.make()
        with self.open() as first:
            root = first.root
            self.assertEqual(root, self.namespace() / self.sha)
            self.assertEqual(set(first.paths), set(payloads))
            self.assertTrue(first.verify())
            self.assertEqual({name: file.read_bytes() for name, file in first.paths.items()}, payloads)
            with self.assertRaises(TypeError):
                first.paths['unreviewed'] = self.archive
            first.derivation['kind'] = 'mutated returned copy'
            self.assertEqual(first.derivation['kind'], self.kind)
        self.assertFalse(first.verify())
        opened = []
        original = DomainArchive.chunks
        def chunks(archive, name):
            opened.append(name)
            yield from original(archive, name)
        with patch.object(DomainArchive, 'chunks', chunks):
            with self.open() as second:
                self.assertTrue(second.verify())
                self.assertEqual(second.root, root)
        self.assertEqual(set(opened), {'derivation.json'})
        self.assertEqual((self.original / 'keep').read_bytes(), b'untouched')
        self.assertEqual((self.state / 'keep').read_bytes(), b'untouched')
        self.assertEqual(list(self.namespace().iterdir()), [root])

    def test_changed_existing_bytes_fail_even_when_timestamp_restored_and_are_preserved(self):
        self.make()
        with self.open() as prepared:
            file = prepared.paths['champions.json']
        before = file.stat()
        raw = file.read_bytes().replace(b'true', b'null')
        file.write_bytes(raw)
        os.utime(file, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaises(DataIntakeBlocked):
            self.open()
        self.assertEqual(file.read_bytes(), raw)

    def test_validated_json_is_decoded_once_and_transferred_without_shared_mutation(self):
        self.make()
        with patch.object(cache, 'parse', wraps=cache.parse) as parse:
            with self.open() as prepared:
                calls = parse.call_count
                self.assertNotIn('derivation.json', prepared._decoded_json)
                self.assertEqual(set(prepared._decoded_json), set(cache.INDUSTRY_MEMBERS) - {'derivation.json'})
                first = prepared.take_json('champions.json')
                self.assertEqual(first, {'fixture': True})
                first['fixture'] = 'consumer-owned mutation'
                with self.assertRaises(DataIntakeBlocked):
                    prepared.take_json('champions.json')
                self.assertEqual(parse.call_count, calls)
                self.assertEqual(json.loads(prepared.paths['champions.json'].read_bytes()), {'fixture': True})
                self.assertTrue(prepared.verify())
        with self.open() as other:
            fresh = other.take_json('champions.json')
            self.assertEqual(fresh, {'fixture': True})
            self.assertIsNot(first, fresh)

    def test_json_transfer_refuses_tampered_and_closed_leases_and_close_drops_cache(self):
        self.make()
        with self.open() as prepared:
            self.assertIn('champions.json', prepared._decoded_json)
            file = prepared.paths['champions.json']
            before = file.stat()
            file.write_bytes(file.read_bytes().replace(b'true', b'null'))
            os.utime(file, ns=(before.st_atime_ns, before.st_mtime_ns))
            with self.assertRaises(DataIntakeBlocked):
                prepared.take_json('champions.json')
        self.assertEqual(prepared._decoded_json, {})
        with self.assertRaises(DataIntakeBlocked):
            prepared.take_json('forecast.json')

    def test_native_melange_factory_consumes_validated_pages_without_reparsing(self):
        from module_data_snapshot import Snapshot
        import workspace_melange
        self.make()
        source, snapshot = self.base/'code', self.base/'snapshot'
        source.mkdir()
        archive = snapshot/'industry/pages.data.zip'
        archive.parent.mkdir(parents=True)
        shutil.copy2(self.archive, archive)
        size = archive.stat().st_size
        request = {'appId':self.app, 'kind':self.kind, 'sourceRoot':str(source),
            'snapshotRoot':str(snapshot), 'files':{'pages':str(archive)},
            'objects':[{'role':'pages', 'bytes':size, 'sha256':self.sha,
                        'segments':[{'asset':'fixture.zip','bytes':size,'sha256':self.sha}]}]}
        with patch.object(workspace_melange, '_json', side_effect=AssertionError('duplicate JSON decode')):
            component = workspace_melange.prepare(Snapshot(request), source={'appId':'melange'},
                profile=str(self.profile), program_fingerprint='a'*64)
        try:
            self.assertTrue(component.verify())
            pages = component.content.data['pages']
            self.assertEqual(set(pages), {'champions','forecast','bills','screen','interactions'})
            self.assertTrue(all(value == {'fixture':True} for value in pages.values()))
            self.assertNotIn('champions.json', component.content.resources[0]._decoded_json)
        finally:
            component.close()

    def test_unknown_cached_marker_and_hardlinks_cannot_confer_authority(self):
        self.make()
        with self.open() as prepared:
            root = prepared.root
            file = prepared.paths['champions.json']
        marker = root / 'accepted.json'
        marker.write_text('{"accepted":true}')
        with self.assertRaises(DataIntakeBlocked):
            self.open()
        marker.unlink()
        alias = self.base / 'outside hardlink'
        os.link(file, alias)
        with self.assertRaises(DataIntakeBlocked):
            self.open()
        self.assertEqual(alias.read_bytes(), file.read_bytes())

    def test_live_member_and_source_mutation_invalidate_readonly_lease(self):
        self.make()
        with self.open() as prepared:
            prepared.paths['screen.json'].write_bytes(b'{"changed":true}')
            self.assertFalse(prepared.verify())
        # Independent fresh fixture avoids ever repairing a failed cache.
        with tempfile.TemporaryDirectory(prefix='other verified profile ') as other:
            original_profile = self.profile
            self.profile = Path(other).resolve()
            with self.open() as prepared:
                self.archive.write_bytes(b'changed signed source')
                self.assertFalse(prepared.verify())
            self.profile = original_profile

    def test_inner_hash_failure_and_storage_failure_publish_nothing_and_clean_only_owned_stage(self):
        self.make(bad_hash=True)
        with self.assertRaises(DataIntakeBlocked):
            self.open()
        self.assertEqual(list(self.namespace().iterdir()), [])
        self.make()
        original = DomainArchive.chunks
        def broken(archive, name):
            if name == 'forecast.json':
                raise OSError('synthetic device failure')
            yield from original(archive, name)
        with patch.object(DomainArchive, 'chunks', broken):
            with self.assertRaises(DataIntakeBlocked) as error:
                self.open()
            self.assertEqual(error.exception.reason, 'storage')
        self.assertEqual(list(self.namespace().iterdir()), [])

    def test_concurrent_creator_winner_is_fully_verified_and_losing_stage_is_discarded(self):
        self.make()
        def winner(stage, target):
            shutil.copytree(stage, target)
            raise FileExistsError('concurrent creator won')
        with patch.object(cache, 'publish_owned', winner):
            with self.open() as prepared:
                self.assertTrue(prepared.verify())
                self.assertEqual(list(self.namespace().iterdir()), [prepared.root])

    def test_bad_concurrent_winner_is_preserved_and_never_replaced(self):
        self.make()
        def winner(stage, target):
            target.mkdir()
            (target / 'foreign').write_bytes(b'preserved')
            raise FileExistsError('concurrent invalid cache')
        with patch.object(cache, 'publish_owned', winner):
            with self.assertRaises(DataIntakeBlocked):
                self.open()
        target = self.namespace() / self.sha
        self.assertEqual((target / 'foreign').read_bytes(), b'preserved')
        self.assertEqual(list(self.namespace().iterdir()), [target])

    def test_cancellation_unknown_kind_and_bad_source_hash_do_not_create_cache(self):
        self.make()
        with self.assertRaises(DataIntakeBlocked):
            self.open(is_cancelled=lambda: True)
        self.sha = '0' * 64
        with self.assertRaises(DataIntakeBlocked):
            self.open()
        self.assertFalse((self.profile / 'packs').exists())
        self.kind = 'uncompiled-kind'
        with self.assertRaises(DataIntakeBlocked):
            self.open()

    def test_insufficient_space_is_storage_not_integrity_and_leaves_no_stage(self):
        self.make()
        with patch.object(cache.shutil, 'disk_usage', return_value=SimpleNamespace(free=0)):
            with self.assertRaises(DataIntakeBlocked) as error:
                self.open()
        self.assertEqual(error.exception.reason, 'storage')
        self.assertEqual(list(self.namespace().iterdir()), [])

    def test_exact_compiled_sqlite_schema_is_required_before_cache_publication(self):
        self.app, self.kind, self.role = 'mentat', REPORT_ANALYSIS_KIND, 'facts'
        self.make(bad_schema=True)
        with self.assertRaises(DataIntakeBlocked):
            self.open()
        self.assertEqual(list(self.namespace().iterdir()), [])

    def test_clean_fixed_schema_facts_database_lease_reopens_without_writes(self):
        self.app, self.kind, self.role = 'mentat', REPORT_ANALYSIS_KIND, 'facts'
        self.make()
        with self.open() as prepared:
            self.assertTrue(prepared.verify())
            source = prepared.paths['banking/index.sqlite']
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            with cache.readonly(source, 'mentat-facts') as database:
                self.assertEqual(database.execute('SELECT count(*) FROM facts').fetchone()[0], 0)
                with self.assertRaises(sqlite3.OperationalError):
                    database.execute('DELETE FROM facts')
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            self.assertTrue(prepared.verify())

    def test_extended_facts_schema_is_selected_only_for_the_compiled_mentat_archive(self):
        member = 'banking/index.sqlite'
        self.assertEqual(cache.sql_family(member, app_id='mentat', kind=REPORT_ANALYSIS_KIND, role='facts'), 'mentat-facts')
        self.assertEqual(cache.sql_family(member, app_id='mentat', kind='other', role='facts'), 'facts')
        self.assertEqual(cache.sql_family('source/catalog.sqlite', app_id='melange', kind=self.kind, role='records'), 'source')

    def test_large_factual_reference_json_cap_is_one_compiled_member_only(self):
        self.assertEqual(cache.json_limit('identity/references.json', app_id='melange', kind=STAFFER_ANALYSIS_KIND, role='records'), 256 * 1024 ** 2)
        for app, kind, role, member in [('melange', STAFFER_ANALYSIS_KIND, 'records', 'contacts/directory.json'),
                ('mentat', REPORT_ANALYSIS_KIND, 'facts', 'identity/references.json'),
                ('melange', INDUSTRY_PAGES_KIND, 'pages', 'identity/references.json')]:
            self.assertEqual(cache.json_limit(member, app_id=app, kind=kind, role=role), 32 * 1024 ** 2)


if __name__ == '__main__':
    unittest.main()
