/* F1b - every POST refusal reads and discards the request body before it
   answers. Closing a socket with inbound data still queued makes Windows send
   RST, and the client loses the 4xx it is already reading. Status codes and
   messages are unchanged; only the draining is new. */
'use strict';

const helper = `    def discard_body(self):
        """Read and drop an unread request body before an early refusal.

        Closing a socket that still has inbound data queued makes Windows send
        RST, and the client can lose the 4xx it is already reading. Bounded by
        the same 7 MB limit the accepted path uses, and a missing or malformed
        Content-Length is tolerated: there is then no length to drain.
        """
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except (TypeError, ValueError):
            return
        remaining = min(length, 7_000_000) if length > 0 else 0
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65_536))
            if not chunk:
                return
            remaining -= len(chunk)

    def valid_host(self):`;

const refusals = `    def do_POST(self):
        analytical_paths = {'/api/contributions/query', '/api/contributions/records', '/api/contributions/geography'}
        if getattr(self.server.app, 'read_only', False) and self.path not in analytical_paths | {'/api/evidence-csv'}:
            self.discard_body()
            return self.send({"error":"This preview is read-only while the original console manages collection."}, 403)
        if not self.valid_host() or not secrets.compare_digest(self.headers.get("X-Mentat-Token", ""), self.server.app.token):
            self.discard_body()
            return self.send({"error": "Refresh the app before continuing."}, 403)
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://localhost:{self.server.server_port}", f"http://127.0.0.1:{self.server.server_port}"):
            self.discard_body()
            return self.send({"error": "Local access only."}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 7_000_000:
                self.discard_body()
                raise ValueError("Request is empty or too large.")`;

const test = `    def test_a_refused_post_with_a_large_body_answers_cleanly(self):
        # A refusal that closed the socket with a megabyte still queued made
        # Windows send RST, and this client lost the response it was reading.
        payload = json.dumps({"dataset": "Banking", "filler": "x" * 1_000_000}).encode()
        self.assertGreater(len(payload), 1_000_000)
        for label, path, headers in (("read-only", "/api/upload", None),
                                     ("wrong token", "/api/contributions/query", {"X-Mentat-Token": "wrong-token"}),
                                     ("foreign origin", "/api/contributions/query", {"Origin": "https://evil.example"})):
            with self.subTest(refusal=label):
                self.console.read_only = label == "read-only"
                status, _, body = self.request(path, method="POST", raw=payload, headers=headers)
                self.assertEqual(status, 403)
                self.assertIn("error", body)
        self.query.assert_not_called()
        self.records.assert_not_called()

    def test_busy_reports_console_owned_work_only(self):`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat',
  eol: 'lf',
  files: [
    {path: 'app/server.py', eol: 'crlf', edits: [
      {find: '    def valid_host(self):', replace: helper},
      {find: `    def do_POST(self):
        analytical_paths = {'/api/contributions/query', '/api/contributions/records', '/api/contributions/geography'}
        if getattr(self.server.app, 'read_only', False) and self.path not in analytical_paths | {'/api/evidence-csv'}:
            return self.send({"error":"This preview is read-only while the original console manages collection."}, 403)
        if not self.valid_host() or not secrets.compare_digest(self.headers.get("X-Mentat-Token", ""), self.server.app.token):
            return self.send({"error": "Refresh the app before continuing."}, 403)
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://localhost:{self.server.server_port}", f"http://127.0.0.1:{self.server.server_port}"):
            return self.send({"error": "Local access only."}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 7_000_000:
                raise ValueError("Request is empty or too large.")`,
       replace: refusals}
    ]},
    {path: 'tests/test_contribution_http.py', eol: 'lf', edits: [
      {find: '    def test_busy_reports_console_owned_work_only(self):', replace: test}
    ]}
  ]
};
