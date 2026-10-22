"""The live-server refusal runs before any socket or sqlite use, and --allow-live needs a CLAUDE TEST name."""
import contextlib
import io
import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import auth_roundtrip


class LiveRefusal(unittest.TestCase):
    def main(self, trust_url, *argv):
        with tempfile.TemporaryDirectory() as folder:
            trust = Path(folder) / 'trust.json'
            trust.write_text(json.dumps({'purpose': 'melange-desktop-trust', 'url': trust_url, 'tlsSpkiSha256': '0' * 64}))
            with mock.patch.object(sys, 'argv', ['auth_roundtrip', '--trust', str(trust), *argv]), \
                 mock.patch.object(socket, 'socket', side_effect=AssertionError('network before refusal')), \
                 mock.patch.object(auth_roundtrip, 'Admin', side_effect=AssertionError('admin before refusal')):
                return auth_roundtrip.main()

    def test_refused_without_allow_live(self):
        local = 'https://127.0.0.1:38444'
        for trust_url, argv in ((local.upper(), ['--origin', 'HTTPS://BORE.PUB:38443', '--dashboard', 'x']),
                                ('https://bore.pub:38443', ['--origin', local, '--dashboard', 'x']),
                                (local, ['--origin', local, '--dashboard', 'http://127.0.0.1:38443/#bootstrap=x']),
                                (local, ['--origin', local, '--dashboard', 'http://127.0.0.1:51234/#bootstrap=x']),
                                (local, ['--origin', local, '--dashboard', str(auth_roundtrip.LIVE_STATE).upper() if os.name == 'nt' else str(auth_roundtrip.LIVE_STATE)])):
            with self.subTest(argv=argv):
                self.assertEqual(self.main(trust_url, *argv), 2)

    def test_state_directory_of_another_server_stops_before_any_request(self):
        paths = []

        class OtherServer:
            server_id = 'live-server'

            def post(self, path, value):
                paths.append(path)
                return 200, {'requests': [], 'grants': [], 'invites': []}
        local = 'https://127.0.0.1:38444'
        with tempfile.TemporaryDirectory() as folder:
            trust = Path(folder) / 'trust.json'
            trust.write_text(json.dumps({'purpose': 'melange-desktop-trust', 'url': local, 'tlsSpkiSha256': '0' * 64,
                                         'serverId': 'isolated-server'}))
            argv = ['auth_roundtrip', '--trust', str(trust), '--origin', local, '--dashboard', folder, '--issue-invite']
            output = io.StringIO()
            with mock.patch.object(sys, 'argv', argv), mock.patch.object(auth_roundtrip, 'Admin', return_value=OtherServer()), \
                 mock.patch.object(auth_roundtrip, 'Recipient', side_effect=AssertionError('recipient call')), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(auth_roundtrip.main(), 1)
        self.assertIn('belongs to a different server', output.getvalue())
        self.assertEqual(set(paths), {'/dashboard'})   # cleanup's read-only listing only: no invite, no request

    def test_allow_live_requires_claude_test_name(self):
        self.assertEqual(self.main('https://bore.pub:38443', '--origin', 'https://bore.pub:38443', '--dashboard', 'x',
                                   '--allow-live', '--display-name', 'Tester laptop'), 2)


if __name__ == '__main__':
    unittest.main()
