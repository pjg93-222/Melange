import io
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import desktop_credentials as credentials


class WindowsIdentityTests(unittest.TestCase):
    def fake(self, *, active=True, usable=True, sid='S-1-5-21-100-200-300-1001', session=1):
        return SimpleNamespace(token_identity=lambda: (sid, 'FIXTURE\\Account', session),
                               session_active=lambda _: active, input_desktop_usable=lambda: usable)

    @unittest.skipUnless(os.name == 'nt', 'Windows native identity required')
    def test_real_process_sid_matches_dpapi_identity_and_ignores_environment_names(self):
        from native_access_state import windows_sid
        with patch.dict(os.environ, {'USERNAME': 'ForgedUser', 'USERDOMAIN': 'ForgedDomain'}):
            result = credentials.current_windows_identity()
        self.assertTrue(credentials.valid_session(result))
        self.assertEqual(result['userSid'], windows_sid())
        self.assertNotEqual(result['accountName'], 'ForgedDomain\\ForgedUser')
        self.assertIs(type(result['locked']), bool)

    def test_active_session_and_default_input_desktop_are_both_required(self):
        with patch.object(credentials.os, 'name', 'nt'):
            for active, usable, locked in ((True, True, False), (False, True, True), (True, False, True), (False, False, True)):
                with self.subTest(active=active, usable=usable), patch.object(credentials, '_Windows', return_value=self.fake(active=active, usable=usable)):
                    self.assertEqual(credentials.current_windows_identity()['locked'], locked)
            for api in (self.fake(sid='S-1-5-18'), self.fake(session=0), self.fake(sid='claimed-user')):
                with patch.object(credentials, '_Windows', return_value=api), self.assertRaises(credentials.WindowsSessionError):
                    credentials.current_windows_identity()

    def test_native_errors_and_untrusted_identity_payload_never_authorize(self):
        with patch.object(credentials.os, 'name', 'nt'), patch.object(credentials, '_Windows', side_effect=OSError('fixture')):
            with self.assertRaises(OSError):
                credentials.current_windows_identity()
        output = io.StringIO()
        incoming = SimpleNamespace(buffer=io.BytesIO(b'{"userSid":"S-1-5-21-100-200-300-1001"}'))
        with patch('sys.stdin', incoming), patch('sys.stdout', output), patch.object(credentials, 'current_windows_identity') as lookup:
            self.assertEqual(credentials.main(), 1)
        lookup.assert_not_called()
        self.assertEqual(json.loads(output.getvalue()), {'error': 'Windows sign-in is unavailable.'})


if __name__ == '__main__':
    unittest.main()
