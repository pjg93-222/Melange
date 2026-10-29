"""Real native Windows requests reach ordinary district selectors; synthetic data only."""
import copy
import hashlib
from unittest.mock import patch
import unittest

import test_terrier_windows as windows_fixture


class WindowsDistrictRoutesTests(unittest.TestCase):
    request = windows_fixture.WindowsDesktopTests.request
    setUp = windows_fixture.WindowsDesktopTests.setUp
    prepare = windows_fixture.WindowsDesktopTests.prepare

    @classmethod
    def setUpClass(cls):
        windows_fixture.WindowsDesktopTests.setUpClass.__func__(cls)
        from django.conf import settings
        from tools import build_walk
        from server.research import walk_testkit
        from server.research import walk_store
        cls.addClassCleanup(windows_fixture.WindowsDesktopTests.tearDownClass.__func__, cls)
        cls.world = walk_testkit.write_minimal_stores(cls.root / 'synthetic-walk-world')
        result = build_walk.build(cls.world.source_csv, cls.world.directory, force=True)
        if not result['replaced']:
            raise AssertionError('The synthetic selector store was not built.')
        cls.data_override = patch.object(settings, 'DATA_DIR', cls.world.directory)
        cls.data_override.start()
        cls.addClassCleanup(cls.data_override.stop)
        cls.addClassCleanup(walk_store.reset)
        walk_store.reset()

    @classmethod
    def tearDownClass(cls):
        from server.research import walk_store
        walk_store.reset()

    @staticmethod
    def routes():
        return ['/api/v3/walk/options?level=' + level for level in ('ss', 'sh', 'precinct')]

    def dataset_identity(self):
        return {file.name: (file.stat().st_size, file.stat().st_mtime_ns,
                           hashlib.sha256(file.read_bytes()).hexdigest())
                for file in self.world.directory.glob('*.sqlite3')}

    def test_windows_account_reads_senate_house_and_precinct_choices_without_data_writes(self):
        from django.conf import settings
        self.prepare()
        before = self.dataset_identity()
        expected = {'ss': ['010', '011'], 'sh': ['018', '019', '021'],
                    'precinct': ['5200021301', '5200021302', '5200021417']}
        for level, identifiers in expected.items():
            with self.subTest(level=level):
                status, payload = self.request('/api/v3/walk/options?level=' + level)
                self.assertEqual(status, 200, payload)
                self.assertEqual(payload['level'], level)
                self.assertEqual([item['id'] for item in payload['options']], identifiers)
        self.assertEqual(self.dataset_identity(), before)
        self.assertFalse(settings.LOCAL_ADMIN_ACCESS)
        self.assertFalse(settings.DESKTOP_BOUNDARY)

    def test_routes_refuse_missing_launch_boundary_bad_origin_forwarding_and_remote_requests(self):
        self.prepare()
        for route in self.routes():
            for headers in ({'HTTP_X_DESKTOP_TOKEN': ''}, {'REMOTE_ADDR': '192.0.2.10'},
                            {'HTTP_HOST': '127.0.0.1:54321'}, {'HTTP_ORIGIN': 'https://outside.invalid'},
                            {'HTTP_X_FORWARDED_FOR': '127.0.0.1'}):
                with self.subTest(route=route, headers=headers):
                    self.assertEqual(self.request(route, headers=headers)[0], 403)
            self.assertEqual(self.request(route, application=self.wsgi)[0], 403)

    def test_routes_refuse_locked_wrong_windows_owner_or_inactive_and_nonstaff_accounts(self):
        from django.contrib.auth.models import User
        binding = self.prepare()
        original_sid = self.native['userSid']
        for route in self.routes():
            self.native['locked'] = True
            self.assertEqual(self.request(route)[0], 403)
            self.native['locked'] = False
            self.native['userSid'] = 'S-1-5-21-100-200-300-2002'
            self.assertEqual(self.request(route)[0], 403)
            self.native['userSid'] = original_sid
            for field in ('is_active', 'is_staff'):
                User.objects.filter(pk=binding['userId']).update(**{field: False})
                self.assertEqual(self.request(route)[0], 403)
                User.objects.filter(pk=binding['userId']).update(**{field: True})

    def test_routes_refuse_hosted_managed_password_and_inconsistent_desktop_modes(self):
        from django.conf import settings
        self.prepare()
        for changed in ({'HOSTED': True}, {'DESKTOP_BOUNDARY': True}, {'LOCAL_ADMIN_ACCESS': True},
                        {'DESKTOP_STANDALONE': False}, {'DESKTOP_WINDOWS_SESSION': False}):
            with patch.multiple(settings, **changed):
                for route in self.routes():
                    with self.subTest(mode=changed, route=route):
                        self.assertEqual(self.request(route)[0], 403)

    def test_capability_requires_both_opaque_markers_and_the_bound_account_not_just_a_flag(self):
        import terrier_standalone as standalone
        self.prepare()
        captured = {}
        original = standalone.standalone_administrator_authorized
        def observe(request):
            captured['request'] = request
            return original(request)
        with patch.object(standalone, 'standalone_administrator_authorized', side_effect=observe):
            self.assertEqual(self.request(self.routes()[0])[0], 200)
        request = captured['request']
        self.assertTrue(original(request))
        for change in ('flag', 'account', 'native-issuer', 'district', 'windows-issuer',
                       'windows-account', 'windows-name', 'missing-native', 'missing-windows'):
            altered = copy.copy(request)
            altered.META = dict(request.META)
            native = request.META[standalone.MARKER]
            windows = request.META[standalone.WINDOWS_MARKER]
            if change == 'flag':
                altered.local_admin_access = False
            elif change == 'account':
                altered.user = self.user  # Another authenticated staff user is not this Windows binding.
            elif change == 'native-issuer':
                altered.META[standalone.MARKER] = (object(), *native[1:])
            elif change == 'district':
                altered.META[standalone.MARKER] = (native[0], 'ct-01', native[2])
            elif change == 'windows-issuer':
                altered.META[standalone.WINDOWS_MARKER] = (object(), *windows[1:])
            elif change == 'windows-account':
                altered.META[standalone.WINDOWS_MARKER] = (windows[0], self.user.pk, *windows[2:])
            elif change == 'windows-name':
                altered.META[standalone.WINDOWS_MARKER] = (*windows[:2], self.user.username, windows[3])
            elif change == 'missing-native':
                altered.META.pop(standalone.MARKER)
            else:
                altered.META.pop(standalone.WINDOWS_MARKER)
            with self.subTest(change=change):
                self.assertFalse(original(altered))


if __name__ == '__main__':
    unittest.main()
