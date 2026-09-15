/* F1b correction. Measured: draining a client-declared Content-Length blocks
   the handler thread when the client never sends those bytes.
   test_invalid_json_shape_length_and_unknown_routes_fail declares 7000001 and
   sends 2 bytes; the suite went 0.7 s -> 8.7 s and failed 10/10 on the client's
   own socket timeout. ThreadingHTTPServer gives a thread per connection, so an
   unbounded drain is a cheap local thread-exhaustion vector that the pre-fix
   code did not have. The drain is now bounded in time as well as in bytes, and
   a body larger than this server would ever accept is not drained at all. */
'use strict';

const helper = `    def discard_body(self):
        """Read and drop an unread request body before an early refusal.

        Closing a socket that still has inbound data queued makes Windows send
        RST, and the client can lose the 4xx it is already reading.

        Only a body this server would otherwise have accepted is drained, and
        only briefly. A client that declares a length it never sends must not
        hold this thread: ThreadingHTTPServer gives it a thread per connection.
        A missing, malformed or oversized Content-Length is left alone, because
        there is then no body this server would have read either.
        """
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except (TypeError, ValueError):
            return
        if length < 1 or length > 7_000_000:
            return
        previous = self.connection.gettimeout()
        self.connection.settimeout(2)
        try:
            while length > 0:
                chunk = self.rfile.read(min(length, 65_536))
                if not chunk:
                    return
                length -= len(chunk)
        except OSError:
            return
        finally:
            try:
                self.connection.settimeout(previous)
            except OSError:
                pass

    def valid_host(self):`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat',
  eol: 'lf',
  files: [
    {path: 'app/server.py', eol: 'crlf', edits: [
      {from: '    def discard_body(self):', to: '    def valid_host(self):', replace: helper.slice(0, helper.length - '    def valid_host(self):'.length)}
    ]},
    {path: 'tests/test_contribution_http.py', eol: 'lf', edits: [
      {find: '        status, _, _ = self.request("/api/contributions/query", method="POST", raw=b"{}", headers={"Content-Length": "7000001"})\n' +
             '        self.assertEqual(status, 400)',
       replace: '        # Declares a length it never sends: the refusal must answer at once,\n' +
             '        # never wait for bytes that are not coming.\n' +
             '        started = time.monotonic()\n' +
             '        status, _, _ = self.request("/api/contributions/query", method="POST", raw=b"{}", headers={"Content-Length": "7000001"})\n' +
             '        self.assertEqual(status, 400)\n' +
             '        self.assertLess(time.monotonic() - started, 3, "an oversized declaration must not stall the handler")'},
      {find: 'import tempfile\nimport threading', replace: 'import tempfile\nimport threading\nimport time'}
    ]}
  ]
};
