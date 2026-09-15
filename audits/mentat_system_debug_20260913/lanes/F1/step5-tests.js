/* F1 step 5 - tests. All three files are pure LF.
   - test_contribution_http.py: health build fields, restart refusals, the
     launcher command Console.restart builds, and Console.busy itself.
   - test_desktop_launcher.py: an idle stale server gives its port back; a busy,
     read-only or too-old server is left running. Existing cases untouched.
   - test_app_lazy_startup_browser.cjs: banner + stamp, no extra startup call. */
'use strict';
const fs = require('fs');
const path = require('path');

const read = name => fs.readFileSync(path.join(__dirname, name), 'utf8').split('\r\n').join('\n');

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\tests',
  eol: 'lf',
  files: [
    {path: 'test_contribution_http.py', eol: 'lf', edits: [
      {find: 'import json\nfrom pathlib import Path', replace: 'import json\nimport os\nfrom pathlib import Path'},
      {find: '        cls.console = SimpleNamespace(token="contribution-test-token", read_only=True, report_directory=cls.report_root)',
       replace: '        cls.console = SimpleNamespace(token="contribution-test-token", read_only=True, report_directory=cls.report_root,\n' +
                '                                      configured_root=str(cls.report_root), root=cls.report_root)'},
      {find: '        self.assertEqual(self.request("/../server.py")[0], 404)\n\n\nif __name__ == "__main__": unittest.main()\n',
       replace: read('step5-http-tests.txt')}
    ]},
    {path: 'test_desktop_launcher.py', eol: 'lf', edits: [
      {find: 'import subprocess\nimport tempfile\nimport unittest',
       replace: 'import subprocess\nimport sys\nimport tempfile\nimport unittest'},
      {find: "@unittest.skipUnless(os.name == 'nt', 'Windows desktop launcher')\nclass DesktopLauncherTests(unittest.TestCase):\n",
       replace: read('step5-launcher-helpers.txt')},
      {find: "                    server.shutdown();server.server_close();worker.join()\n\n\nif __name__ == '__main__':\n    unittest.main()\n",
       replace: "                    server.shutdown();server.server_close();worker.join()\n\n" + read('step5-launcher-tests.txt')}
    ]},
    {path: 'test_app_lazy_startup_browser.cjs', eol: 'lf', edits: [
      {find: " assert.equal(await page.locator('#evidence-mode').inputValue(),'graph');assert.equal(await page.locator('#evidence-source').inputValue(),'snapshot');assert.deepEqual(errors,[]);\n});\n",
       replace: " assert.equal(await page.locator('#evidence-mode').inputValue(),'graph');assert.equal(await page.locator('#evidence-source').inputValue(),'snapshot');assert.deepEqual(errors,[]);\n});\n" + read('step5-cjs-test.txt')}
    ]}
  ]
};
