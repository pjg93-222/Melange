"""Windows-only local access preserves old accounts and survives interrupted binding."""
import copy
import unittest
from unittest.mock import patch

import test_terrier_standalone as fixture


class WindowsDesktopTests(unittest.TestCase):
    setUpClass = classmethod(fixture.StandaloneDesktopTests.setUpClass.__func__)
    tearDownClass = classmethod(fixture.StandaloneDesktopTests.tearDownClass.__func__)
    request = fixture.StandaloneDesktopTests.request

    def setUp(self):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('DROP TABLE IF EXISTS desktop_windows_local_binding')
        fixture.StandaloneDesktopTests.setUp(self)
        import terrier_standalone as standalone
        standalone.configure_settings(windows_session=True)
        self.native = {'schemaVersion': 1, 'userSid': 'S-1-5-21-100-200-300-1001',
                       'accountName': 'FIXTURE\\WindowsUser', 'sessionId': 1, 'locked': False}
        self.record = None
        self.fail_ready = False
        def write(_root, kind, record):
            self.assertEqual(kind, 'windows-account')
            if self.fail_ready and record['phase'] == 'ready':
                self.fail_ready = False
                raise OSError('synthetic final-write interruption')
            self.record = copy.deepcopy(record)
        for target, replacement in (
                ('terrier_standalone.current_windows_identity', lambda: dict(self.native)),
                ('native_access_state.read', lambda _root, _kind: copy.deepcopy(self.record)),
                ('native_access_state.write', write)):
            instance = patch(target, replacement)
            instance.start()
            self.addCleanup(instance.stop)

    def prepare(self):
        from terrier_standalone import prepare_windows_account, StandaloneBoundary
        from desktop_backend import GuardedWSGI
        binding = prepare_windows_account(self.root / 'state')
        self.boundary = StandaloneBoundary('co-05', 12345, windows_account=binding)
        self.application = GuardedWSGI(self.wsgi, 't'*40, 'terrier', desktop_boundary=self.boundary)
        return binding

    def test_fresh_windows_account_opens_without_password_invitation_or_managed_grant(self):
        from django.contrib.auth.models import User
        from server.research.models import DesktopPrincipalBinding, Invitation
        User.objects.all().delete()
        binding = self.prepare()
        owner = User.objects.get(pk=binding['userId'])
        self.assertFalse(owner.has_usable_password())
        self.assertTrue(owner.is_staff)
        self.assertFalse(owner.is_superuser)
        self.assertEqual(Invitation.objects.count(), 0)
        self.assertEqual(DesktopPrincipalBinding.objects.count(), 0)
        status, session = self.request('/api/auth/session')
        self.assertEqual(status, 200)
        self.assertTrue(session['authenticated'])
        self.assertTrue(session['administrator'])
        self.assertEqual(session['authentication'], 'windows')
        self.assertEqual(session['windowsAccountDisplayName'], self.native['accountName'])
        self.assertNotIn('userSid', session)
        self.assertEqual(self.request('/api/accounts')[0], 200)

    def test_multiple_old_accounts_and_views_are_preserved_and_copied_once(self):
        from django.contrib.auth.models import User
        from server.research.models import SavedView
        viewer = User.objects.create_user('existing_viewer', password='Synthetic-Previous-Password', is_staff=False)
        views = [SavedView.objects.create(owner=owner, name='Saved area', config={'fixture': owner.username}) for owner in (self.user, viewer)]
        before = list(User.objects.order_by('pk').values('pk', 'username', 'password', 'is_active', 'is_staff', 'is_superuser'))
        binding = self.prepare()
        self.assertEqual(list(User.objects.filter(pk__in=[row['pk'] for row in before]).order_by('pk').values(*before[0])), before)
        self.assertEqual(list(SavedView.objects.filter(pk__in=[view.pk for view in views]).values_list('owner_id', flat=True)), [self.user.pk, viewer.pk])
        copied = list(SavedView.objects.filter(owner_id=binding['userId']).order_by('pk').values('name', 'config'))
        self.assertEqual(copied, [{'name': view.name, 'config': view.config} for view in views])
        self.assertEqual(self.prepare(), binding)
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(SavedView.objects.count(), 4)

    def test_interrupted_final_binding_write_recovers_without_duplicate_accounts_or_views(self):
        from django.contrib.auth.models import User
        from server.research.models import SavedView
        SavedView.objects.create(owner=self.user, name='Before upgrade', config={'fixture': True})
        self.fail_ready = True
        with self.assertRaisesRegex(OSError, 'interruption'):
            self.prepare()
        self.assertEqual(self.record['phase'], 'pending')
        self.assertEqual((User.objects.count(), SavedView.objects.count()), (2, 2))
        recovered = self.prepare()
        self.assertEqual(recovered['phase'], 'ready')
        self.assertEqual((User.objects.count(), SavedView.objects.count()), (2, 2))
        self.assertEqual(len(recovered['savedViews']), 1)

    def test_copy_failure_rolls_back_account_and_retries_from_pending_binding(self):
        from django.contrib.auth.models import User
        from server.research.models import SavedView
        original = SavedView.objects.create(owner=self.user, name='Original', config={'fixture': True})
        with patch.object(SavedView.objects, 'create', side_effect=OSError('synthetic interrupted copy')):
            with self.assertRaisesRegex(OSError, 'interrupted copy'):
                self.prepare()
        self.assertEqual(self.record['phase'], 'pending')
        self.assertEqual((User.objects.count(), SavedView.objects.count()), (1, 1))
        self.assertEqual(SavedView.objects.get(pk=original.pk).owner_id, self.user.pk)
        self.prepare()
        self.assertEqual((User.objects.count(), SavedView.objects.count()), (2, 2))

    def test_lock_sid_change_missing_native_token_and_forged_headers_are_refused(self):
        self.prepare()
        self.native['locked'] = True
        self.assertEqual(self.request('/api/auth/session')[0], 403)
        self.native['locked'] = False
        self.assertEqual(self.request('/api/auth/session')[0], 200)
        self.native['userSid'] = 'S-1-5-21-100-200-300-2002'
        self.assertEqual(self.request('/api/auth/session')[0], 403)
        self.native['userSid'] = 'S-1-5-21-100-200-300-1001'
        for headers in ({'HTTP_X_DESKTOP_TOKEN': ''}, {'HTTP_X_FORWARDED_FOR': '127.0.0.1'}, {'HTTP_ORIGIN': 'https://example.invalid'}):
            self.assertEqual(self.request('/api/auth/session', headers=headers)[0], 403)

    def test_disabled_binding_cannot_reprovision_or_elevate_and_login_cannot_claim_another_user(self):
        from django.contrib.auth.models import User
        binding = self.prepare()
        status, session = self.request('/api/auth/session')
        self.assertEqual(status, 200)
        self.assertEqual(self.request('/api/auth/login', method='POST', data={'username': self.user.username, 'password': self.password},
            headers={'HTTP_X_CSRFTOKEN': session['csrf']})[0], 403)
        User.objects.filter(pk=binding['userId']).update(is_active=False)
        self.assertEqual(self.request('/api/auth/session')[0], 403)
        with self.assertRaisesRegex(ValueError, 'disabled'):
            self.prepare()
        self.assertEqual(User.objects.count(), 2)

    def test_existing_similarly_named_account_is_not_claimed_and_other_sid_cannot_rebind(self):
        import hashlib
        from django.contrib.auth.models import User
        username = 'windows_' + hashlib.sha256(self.native['userSid'].encode()).hexdigest()[:40]
        existing = User.objects.create_user(username, password='Synthetic-Unrelated-Password', is_staff=False)
        before = (existing.pk, existing.password, existing.is_staff)
        with self.assertRaisesRegex(ValueError, 'cannot claim'):
            self.prepare()
        existing.refresh_from_db()
        self.assertEqual((existing.pk, existing.password, existing.is_staff), before)
        self.assertEqual(User.objects.count(), 2)
        self.native['userSid'] = 'S-1-5-21-100-200-300-2002'
        with self.assertRaisesRegex(ValueError, 'binding is invalid'):
            self.prepare()
        self.assertEqual(User.objects.count(), 2)


if __name__ == '__main__':
    unittest.main()
