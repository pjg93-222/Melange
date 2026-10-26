"""Pre-import parent framing and authenticated health; generated contexts only."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.request
from urllib.error import HTTPError

import desktop_backend as backend
from module_application_contracts import ModuleInputError
from module_data_handoff import (server_installation,complete_server_installation,server_installed_health)
import test_module_public_input_installers as fixtures


class BackendInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='module-backend-input-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve()
        for name in ('source','profile'):(self.base/name).mkdir()
        self.data=self.base/'new-original-data';self.state=self.base/'new-original-state'
        self.argv=['desktop_backend','--app','mentat','--port','2000','--source-root',str(self.base/'source'),
                   '--data-root',str(self.data),'--state-root',str(self.state)]

    def test_profile_cli_and_module_mode_are_paired_and_terrier_cannot_select_it(self):
        with (patch.dict(os.environ,{'DESKTOP_LAUNCH_TOKEN':'x'*32}),patch.object(backend,'contain_windows_children'),
              patch.object(backend,'run') as run):
            for extra in (['--profile-root',str(self.base/'profile')],['--desktop-module-input'],
                          ['--desktop-module-input','--profile-root',str(self.base/'profile'),'--app','terrier']):
                with patch('sys.argv',self.argv+extra),self.assertRaises(SystemExit):backend.main()
            run.assert_not_called()
        self.assertFalse(self.data.exists());self.assertFalse(self.state.exists())

    def test_invalid_real_frame_fails_before_run_or_original_mkdir_and_suppresses_bytecode(self):
        source=SimpleNamespace(buffer=io.BytesIO(b'\x00\x01\x00\x01'))
        with (patch.dict(os.environ,{'DESKTOP_LAUNCH_TOKEN':'x'*32}),patch.object(backend,'contain_windows_children'),
              patch.object(backend,'run') as run,patch('sys.stdin',source),patch('sys.stderr',io.StringIO()) as error,
              patch('sys.dont_write_bytecode',False),patch('sys.argv',self.argv+['--desktop-module-input','--profile-root',str(self.base/'profile')])):
            self.assertEqual(backend.main(),1);self.assertTrue(__import__('sys').dont_write_bytecode)
            self.assertEqual(error.getvalue(),'Native module input is unavailable.\n');run.assert_not_called()
        self.assertFalse(self.data.exists());self.assertFalse(self.state.exists())

    def test_ordinary_startup_never_reads_pipe_or_requires_profile(self):
        class NeverRead:
            @property
            def buffer(self):raise AssertionError('ordinary startup must not read stdin')
        with (patch.dict(os.environ,{'DESKTOP_LAUNCH_TOKEN':'x'*32}),patch.object(backend,'contain_windows_children'),
              patch('sys.stdin',NeverRead()),patch('sys.argv',self.argv),patch.object(backend,'run') as run):
            backend.main();self.assertIsNone(run.call_args.kwargs['module_inputs'])

    def test_prepared_failure_is_disposed_without_any_generic_startup_fallback(self):
        sentinel=object()
        with (patch.dict(os.environ,{'DESKTOP_LAUNCH_TOKEN':'x'*32}),patch.object(backend,'contain_windows_children'),
              patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO(b''))),patch('sys.stderr',io.StringIO()),
              patch('sys.argv',self.argv+['--desktop-module-input','--profile-root',str(self.base/'profile')]),
              patch('module_data_handoff.prepare_handoff',return_value=sentinel),
              patch('module_data_handoff.close_handoff') as close,patch.object(backend,'run',side_effect=RuntimeError('refused')) as run):
            self.assertEqual(backend.main(),1);self.assertEqual(run.call_count,1);close.assert_called_once_with(sentinel)

    def test_authenticated_module_health_refuses_unarmed_or_changed_actual_server(self):
        fixture=fixtures.InstallerTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        prepared,original,latch=fixture.make('mentat')
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),backend.guarded_handler(Handler,'x'*32,'mentat',module_installation=latch))
        self.addCleanup(server.server_close)
        # Same exact actual server, with the genuine generated Console attached;
        # rebuilding/mutating a dictionary cannot arm the latch.
        server.app=original.app
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        def stop():server.shutdown();worker.join()
        self.addCleanup(stop)
        url='http://127.0.0.1:'+str(server.server_port)+backend.HEALTH_PATH
        def request(token='x'*32):
            return urllib.request.urlopen(urllib.request.Request(url,headers={backend.TOKEN_HEADER:token}),timeout=5)
        for token,status in (('wrong',403),('x'*32,503)):
            with self.assertRaises(HTTPError) as error:request(token)
            self.assertEqual(error.exception.code,status)
        complete_server_installation(latch,server)
        with request() as response:
            result=json.load(response)
            self.assertEqual(set(result),{'appId','pid','moduleData'})
            self.assertEqual(result['pid'],os.getpid())
            self.assertEqual(set(result['moduleData']),{'schemaVersion','contractId','programFingerprint','sourceDigest','sourceFingerprint','launchNonce','coverageDigest'})
        server.moduleData=result['moduleData'];server.app.report_cache={}
        with self.assertRaises(HTTPError) as error:request()
        self.assertEqual(error.exception.code,503)


if __name__=='__main__':unittest.main()
