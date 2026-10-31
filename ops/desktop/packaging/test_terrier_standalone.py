"""Real local Django sign-in without a server approval or owner impersonation."""
import json
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
from wsgiref.util import setup_testing_defaults


class StandaloneDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='terrier-standalone-test-')
        cls.root = Path(cls.temporary.name)
        sys.path.insert(0, os.environ['TERRIER_TEST_SOURCE'])
        os.environ.update(DJANGO_SETTINGS_MODULE='server.settings', CU_DEPLOYMENT='desktop-standalone',
                          CU_LOCAL_ADMIN='0', CU_DATA_DIR=str(cls.root/'data'), CU_STATE_DIR=str(cls.root/'state'),
                          CU_DISTRICT='co-05', CU_SECRET_KEY='synthetic-standalone-test-only', CU_ALLOWED_HOSTS='127.0.0.1')
        import django
        django.setup()
        from terrier_standalone import configure_settings, StandaloneBoundary
        configure_settings()
        from django.core.management import call_command
        call_command('migrate', interactive=False, verbosity=0)
        from django.core.wsgi import get_wsgi_application
        from desktop_backend import GuardedWSGI
        cls.wsgi = get_wsgi_application()
        cls.boundary = StandaloneBoundary('co-05', 12345)
        cls.application = GuardedWSGI(cls.wsgi, 't'*40, 'terrier', desktop_boundary=cls.boundary)

    @classmethod
    def tearDownClass(cls):
        from django.db import connections
        connections.close_all()
        cls.temporary.cleanup()

    def setUp(self):
        from django.contrib.auth.models import User
        from server.research.models import DesktopPrincipalBinding, Invitation, LoginAttempt
        DesktopPrincipalBinding.objects.all().delete()
        Invitation.objects.all().delete()
        User.objects.all().delete()
        LoginAttempt.objects.all().delete()
        self.cookies = SimpleCookie()
        self.password = 'Synthetic-Local-Password-491!'
        self.user = User.objects.create_user('recipient_existing', password=self.password, is_staff=True)

    def request(self, path, *, method='GET', data=None, headers=None, application=None):
        environment = {}
        setup_testing_defaults(environment)
        parsed = urlsplit(path)
        body = json.dumps(data or {}).encode() if method == 'POST' else b''
        environment.update(REQUEST_METHOD=method, PATH_INFO=parsed.path, QUERY_STRING=parsed.query,
            CONTENT_TYPE='application/json', CONTENT_LENGTH=str(len(body)), HTTP_HOST='127.0.0.1:12345',
            SERVER_NAME='127.0.0.1', SERVER_PORT='12345', REMOTE_ADDR='127.0.0.1')
        environment['wsgi.input'] = io.BytesIO(body)
        environment.update(HTTP_X_DESKTOP_TOKEN='t'*40, HTTP_COOKIE=self.cookies.output(header='', sep=';').strip())
        environment.update(headers or {})
        captured = {}
        def start(status, fields, exc_info=None):
            captured.update(status=int(status.split()[0]), fields=fields)
        result = (application or self.application)(environment, start)
        try:
            content = b''.join(result)
        finally:
            if hasattr(result, 'close'):
                result.close()
        for name, value in captured['fields']:
            if name.lower() == 'set-cookie':
                self.cookies.load(value)
        try:
            payload = json.loads(content)
        except ValueError:
            payload = None
        return captured['status'], payload

    def sign_in(self):
        status, session = self.request('/api/auth/session')
        self.assertEqual(status, 200)
        return self.request('/api/auth/login', method='POST', data={'username': self.user.username, 'password': self.password},
                            headers={'HTTP_X_CSRFTOKEN': session['csrf']})

    def test_existing_recipient_keeps_password_and_role_without_remote_binding(self):
        from django.conf import settings
        from server.research.models import DesktopPrincipalBinding
        original = (self.user.pk, self.user.password, self.user.is_staff, self.user.is_superuser)
        self.assertFalse(settings.LOCAL_ADMIN_ACCESS)
        self.assertFalse(settings.DESKTOP_BOUNDARY)
        self.assertEqual(self.request('/api/accounts')[0], 401)
        status, session = self.sign_in()
        self.assertEqual(status, 200)
        self.assertTrue(session['authenticated'] and session['administrator'] and session['local_admin_access'])
        self.assertEqual(self.request('/api/auth/session')[1]['username'], 'recipient_existing')
        self.user.refresh_from_db()
        self.assertEqual(original, (self.user.pk, self.user.password, self.user.is_staff, self.user.is_superuser))
        self.assertEqual(DesktopPrincipalBinding.objects.count(), 0)

    def test_viewer_sign_in_does_not_gain_local_administrator(self):
        self.user.is_staff = False
        self.user.save(update_fields=['is_staff'])
        status, session = self.sign_in()
        self.assertEqual(status, 200)
        self.assertTrue(session['authenticated'])
        self.assertFalse(session['administrator'] or session['local_admin_access'])
        self.assertEqual(self.request('/api/accounts')[0], 403)

    def test_launch_token_origin_loopback_and_private_marker_are_required(self):
        for headers in ({'HTTP_X_DESKTOP_TOKEN': ''}, {'REMOTE_ADDR': '203.0.113.4'},
                        {'HTTP_ORIGIN': 'https://untrusted.invalid'}, {'HTTP_X_FORWARDED_FOR': '127.0.0.1'}):
            self.assertEqual(self.request('/api/auth/session', headers=headers)[0], 403)
        self.assertEqual(self.request('/api/auth/session', application=self.wsgi)[0], 403)

    def test_empty_install_invites_first_owner_and_requires_password_acceptance(self):
        from django.contrib.auth.models import User
        from server.research.models import DesktopPrincipalBinding
        from terrier_standalone import prepare_accounts
        User.objects.all().delete()
        invitation = prepare_accounts(self.root/'state')
        self.assertTrue(invitation.startswith('/#invite='))
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(self.request('/api/accounts')[0], 401)
        session = self.request('/api/auth/session')[1]
        status, accepted = self.request('/api/auth/accept', method='POST',
            data={'token': invitation.partition('=')[2], 'password': self.password}, headers={'HTTP_X_CSRFTOKEN': session['csrf']})
        self.assertEqual(status, 200)
        self.assertTrue(accepted['authenticated'] and accepted['administrator'] and accepted['local_admin_access'])
        owner = User.objects.get(username='owner')
        self.assertTrue(owner.check_password(self.password))
        self.assertFalse(owner.is_superuser)
        self.assertEqual(DesktopPrincipalBinding.objects.count(), 0)

    def test_existing_accounts_are_not_replaced_or_reinvited(self):
        from django.contrib.auth.models import User
        from server.research.models import Invitation
        from terrier_standalone import prepare_accounts
        before = list(User.objects.values_list('id', 'username', 'password', 'is_staff', 'is_superuser'))
        self.assertIsNone(prepare_accounts(self.root/'state'))
        self.assertEqual(before, list(User.objects.values_list('id', 'username', 'password', 'is_staff', 'is_superuser')))
        self.assertEqual(Invitation.objects.count(), 0)


if __name__ == '__main__':
    unittest.main()
