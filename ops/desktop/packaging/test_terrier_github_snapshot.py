"""Real summary validation and Django activation using the backend's synthetic v4 world."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest


class PublicSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='terrier-public-snapshot-test-')
        cls.root = Path(cls.temp.name).resolve()
        cls.source = Path(os.environ['TERRIER_TEST_SOURCE'])
        sys.path.insert(0, str(cls.source))
        (cls.root / 'data').mkdir()
        (cls.root / 'state').mkdir()
        os.environ.update(DJANGO_SETTINGS_MODULE='server.settings', CU_DEPLOYMENT='desktop-standalone',
                          CU_LOCAL_ADMIN='0', CU_DATA_DIR=str(cls.root / 'data'), CU_STATE_DIR=str(cls.root / 'state'),
                          CU_DISTRICT='co-05', CU_SECRET_KEY='synthetic-snapshot-test-only', CU_ALLOWED_HOSTS='testserver')
        import django
        django.setup()
        from django.core.management import call_command
        call_command('migrate', interactive=False, verbosity=0)

    @classmethod
    def tearDownClass(cls):
        from django.db import connections
        connections.close_all()
        cls.temp.cleanup()

    def setUp(self):
        from django.conf import settings
        from server.research.models import Snapshot, AuditEvent, SavedView
        from django.contrib.auth.models import User
        from test_terrier_snapshot_fixture import build_world
        from tools import districts
        Snapshot.objects.all().delete()
        AuditEvent.objects.all().delete()
        SavedView.objects.all().delete()
        User.objects.all().delete()
        self.temporary = tempfile.TemporaryDirectory(prefix='snapshot-case-', dir=self.root)
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.data, self.state = root / 'data', root / 'state'
        self.data.mkdir()
        self.state.mkdir()
        old_data, old_state = settings.DATA_DIR, settings.STATE_DIR
        settings.DATA_DIR, settings.STATE_DIR = self.data, self.state
        self.addCleanup(lambda: setattr(settings, 'DATA_DIR', old_data))
        self.addCleanup(lambda: setattr(settings, 'STATE_DIR', old_state))
        self.world = build_world(self.data)
        self.payload = copy.deepcopy(self.world.payload)
        self.payload['manifest.json']['source_sha256'] = districts.get('co-05')['sha256']
        self.key = self.payload['manifest.json']['snapshot']
        self.snapshot = self.data / 'snapshots' / self.key
        self.write_snapshot(self.snapshot, self.payload)
        self.user = User.objects.create_user('existing-local-owner', password='Synthetic-Existing-481!', is_staff=True)
        self.view = SavedView.objects.create(owner=self.user, name='Existing local view', config={'snapshot': 'previous-local'})

    def write_snapshot(self, directory, payload):
        directory.mkdir(parents=True)
        for name, value in payload.items():
            (directory / name).write_text(json.dumps(value), encoding='utf-8')

    def activate(self):
        from terrier_github_snapshot import activate_snapshot
        return activate_snapshot(self.source, self.data, self.state, 'co-05')

    def test_fresh_profile_activates_real_summary_and_menu_metadata(self):
        from django.http import HttpRequest, QueryDict
        from server.research.models import Snapshot, SavedView
        from server.research.v3_area_views import meta
        before_password = self.user.password
        result = self.activate()
        self.assertTrue(result['activated'])
        self.assertEqual(Snapshot.objects.get(active=True).key, self.key)
        request = HttpRequest()
        request.method, request.path = 'GET', '/api/v3/meta'
        request.GET = QueryDict('demo=1')
        request.user = self.user
        response = meta(request)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn(b'No row-framework snapshot', response.content)
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, before_password)
        self.assertTrue(self.user.is_staff)
        self.assertEqual(SavedView.objects.get(pk=self.view.pk).config, {'snapshot': 'previous-local'})
        self.assertTrue((self.state / 'snapshots' / self.key / 'rows.json').is_file())

    def test_repeat_start_is_idempotent_and_preserves_snapshot_bytes(self):
        from server.research.models import Snapshot, AuditEvent
        self.activate()
        target = self.state / 'snapshots' / self.key / 'rows.json'
        before = target.read_bytes(), target.stat().st_mtime_ns
        self.activate()
        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
        self.assertEqual(Snapshot.objects.filter(active=True).count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action='snapshot.import').count(), 1)

    def test_nonmatching_historical_snapshot_is_not_selected(self):
        other = copy.deepcopy(self.payload)
        other['manifest.json']['snapshot'] = 'co-cd005-ffffffffffff'
        other['manifest.json']['row_framework']['area_table_sha256'] = 'f' * 64
        self.write_snapshot(self.data / 'snapshots' / other['manifest.json']['snapshot'], other)
        self.assertEqual(self.activate()['snapshot'], self.key)

    def test_missing_ambiguous_or_wrong_source_summary_never_fabricates_snapshot(self):
        from server.research.models import Snapshot
        from terrier_github_snapshot import select_snapshot
        original = (self.snapshot / 'manifest.json').read_bytes()
        bad = copy.deepcopy(self.payload['manifest.json'])
        bad['source_sha256'] = '0' * 64
        (self.snapshot / 'manifest.json').write_text(json.dumps(bad))
        with self.assertRaises(ValueError):
            self.activate()
        self.assertFalse(Snapshot.objects.exists())
        (self.snapshot / 'manifest.json').write_bytes(original)
        other = copy.deepcopy(self.payload)
        other['manifest.json']['snapshot'] = 'co-cd005-ffffffffffff'
        self.write_snapshot(self.data / 'snapshots' / other['manifest.json']['snapshot'], other)
        with self.assertRaises(ValueError):
            select_snapshot(self.source, self.data, 'co-05')
        self.assertFalse(Snapshot.objects.exists())

    def test_invalid_summary_and_conflicting_existing_state_leave_active_user_snapshot(self):
        from server.research.models import Snapshot
        prior = Snapshot.objects.create(key='co-cd005-000000000000', manifest={'schema': 'cu-summary-v4'}, active=True)
        rows = self.snapshot / 'rows.json'
        original = rows.read_bytes()
        rows.write_text('{}')
        with self.assertRaises((ValueError, KeyError, TypeError)):
            self.activate()
        self.assertEqual(Snapshot.objects.get(active=True).pk, prior.pk)
        rows.write_bytes(original)
        target = self.state / 'snapshots' / self.key
        shutil.copytree(self.snapshot, target)
        (target / 'rows.json').write_text('{}')
        with self.assertRaises(ValueError):
            self.activate()
        self.assertEqual(Snapshot.objects.get(active=True).pk, prior.pk)
        self.assertEqual((target / 'rows.json').read_text(), '{}')


if __name__ == '__main__':
    unittest.main()
