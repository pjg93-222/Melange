"""Expected socket disconnects are contained across the entire desktop request."""
from http.server import BaseHTTPRequestHandler
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from desktop_backend import guarded_handler


class DesktopDisconnectTests(unittest.TestCase):
    def make_handler(self, *, workspace=True):
        class NativeHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.native_calls += 1
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'native response')

            def log_message(self, *_args):
                pass

        options = dict(module_installation=object(), workspace_installation=object(),
                       workspace_inputs=object()) if workspace else {}
        cls = guarded_handler(NativeHandler, 'x' * 32, 'mentat', **options)
        handler = cls.__new__(cls)
        handler.rfile = io.BytesIO(('GET /api/graph HTTP/1.1\r\nHost: localhost\r\n'
                                   'X-Desktop-Token: ' + 'x' * 32 + '\r\n\r\n').encode())
        handler.wfile = io.BytesIO()
        handler.client_address = ('127.0.0.1', 1)
        handler.server = SimpleNamespace(server_name='localhost', server_port=1)
        handler.native_calls = 0
        return handler

    @staticmethod
    def workspace_response(handler, _prepared):
        handler.send_response(200)
        handler.end_headers()
        handler.wfile.write(b'workspace response')
        return True

    def workspace_request(self, handler, callback=None):
        with patch('module_data_handoff.server_installed_health', return_value={}), \
                patch('module_workspace_installers.handle_workspace_request',
                      side_effect=callback or self.workspace_response) as route:
            handler.handle_one_request()
            route.assert_called_once()

    def test_workspace_parse_response_disconnects_are_contained(self):
        for error in (BrokenPipeError('closed'), ConnectionResetError('reset'),
                      ConnectionAbortedError(10053, 'aborted')):
            with self.subTest(error=type(error).__name__):
                handler = self.make_handler()
                handler.wfile = Mock()
                handler.wfile.write.side_effect = error
                self.workspace_request(handler)
                self.assertTrue(handler.close_connection)
                self.assertEqual(handler.wfile.write.call_count, 1)
                self.assertEqual(handler.native_calls, 0)

    def test_workspace_and_native_successful_responses_are_unchanged(self):
        handler = self.make_handler()
        self.workspace_request(handler)
        self.assertTrue(handler.wfile.getvalue().endswith(b'workspace response'))
        self.assertEqual(handler.native_calls, 0)
        native = self.make_handler(workspace=False)
        native.handle_one_request()
        self.assertTrue(native.wfile.getvalue().endswith(b'native response'))
        self.assertEqual(native.native_calls, 1)

    def test_generic_io_and_validation_errors_are_not_swallowed(self):
        for error in (OSError('unreadable source'), ValueError('invalid source')):
            with self.subTest(error=type(error).__name__):
                handler = self.make_handler()
                with self.assertRaises(type(error)):
                    self.workspace_request(handler, Mock(side_effect=error))

    def test_request_read_disconnect_is_contained_before_parsing(self):
        handler = self.make_handler(workspace=False)
        handler.rfile = Mock()
        handler.rfile.readline.side_effect = ConnectionAbortedError(10053, 'aborted')
        handler.handle_one_request()
        self.assertTrue(handler.close_connection)
        self.assertEqual(handler.native_calls, 0)


if __name__ == '__main__':
    unittest.main()
