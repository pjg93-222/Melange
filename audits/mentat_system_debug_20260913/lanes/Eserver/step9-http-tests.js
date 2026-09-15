/* Step 9 (lane E-server): the vendor bundle and the briefing routes in
   test_contribution_http.py.

   The bundle test asserts the hash of the bytes the server actually served, not
   the hash of the file on disk: the claim being defended is that the browser
   receives the pinned PptxGenJS 4.0.1 UMD build over a same-origin route under
   the console's CSP, and only a served-bytes comparison can defend it.

   The allow-list test is written so it stays true on both sides of the parallel
   client lane landing chart-briefing.js/.css: the route must be allow-listed
   with the right media type either way, and a file that is not on disk yet
   answers 404 rather than leaking a filesystem path through the 400 handler.

   Usage: node apply-e.js step9-http-tests.js [--check] */
'use strict';

const TESTS =
  '    def test_the_vendor_powerpoint_bundle_is_served_at_its_pinned_hash(self):\n' +
  '        status, headers, body = self.request(\'/vendor/pptxgen.bundle.js\')\n' +
  '        self.assertEqual(status, 200)\n' +
  "        self.assertEqual(headers['Content-Type'], 'text/javascript')\n" +
  "        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')\n" +
  '        self.assertIn("script-src \'self\'", headers["Content-Security-Policy"])\n' +
  '        self.assertIn("frame-ancestors \'none\'", headers["Content-Security-Policy"])\n' +
  '        # The bytes the browser receives, not the bytes on disk.\n' +
  '        self.assertEqual(hashlib.sha256(body).hexdigest(), PPTXGENJS_SHA256)\n' +
  '\n' +
  '    def test_the_briefing_and_vendor_routes_are_allow_listed_with_their_media_types(self):\n' +
  "        directory = Path(app.__file__).resolve().parent\n" +
  "        for route, mime in (('/chart-briefing.js', 'text/javascript'),\n" +
  "                            ('/chart-briefing.css', 'text/css'),\n" +
  "                            ('/vendor/pptxgen.bundle.js', 'text/javascript')):\n" +
  '            with self.subTest(route=route):\n' +
  '                filename, declared = app.STATIC_ASSETS[route]\n' +
  '                self.assertEqual(declared, mime)\n' +
  '                status, headers, body = self.request(route)\n' +
  '                # The two chart-briefing files belong to the parallel client\n' +
  '                # lane. Until they land the route answers 404, not a 400\n' +
  '                # carrying a local path; once they land it serves them.\n' +
  '                if (directory / filename).is_file():\n' +
  '                    self.assertEqual(status, 200)\n' +
  "                    self.assertEqual(headers['Content-Type'], mime)\n" +
  '                    self.assertGreater(len(body), 50)\n' +
  '                else:\n' +
  "                    self.assertEqual((status, body), (404, {'error': 'Not found.'}))\n" +
  '\n';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\tests',
  files: [{
    path: 'test_contribution_http.py',
    edits: [
      {find: 'import http.client\nimport importlib.util\n',
       replace: 'import hashlib\nimport http.client\nimport importlib.util\n'},

      {find: 'spec.loader.exec_module(app)\n',
       replace: 'spec.loader.exec_module(app)\n' +
                '\n' +
                '# PptxGenJS 4.0.1 UMD browser bundle, MIT, from the npm registry tarball\n' +
                '# (registry dist.shasum verified on download). Vendored at\n' +
                '# mentat/app/vendor/pptxgen.bundle.js; the console serves it to the\n' +
                '# briefing exporter and nothing rewrites it, so the served bytes are pinned.\n' +
                "PPTXGENJS_SHA256 = '4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8'\n"},

      {find: '    def test_busy_reports_console_owned_work_only(self):\n',
       replace: TESTS + '    def test_busy_reports_console_owned_work_only(self):\n'}
    ]
  }]
};
