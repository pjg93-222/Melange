/* F1 step 6 - close the fixture's stdout pipe once the port is read, so the
   launcher suite runs without ResourceWarning noise. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\tests',
  eol: 'lf',
  files: [{
    path: 'test_desktop_launcher.py',
    eol: 'lf',
    edits: [{
      find: "    port = int(process.stdout.readline().strip())\n",
      replace: "    port = int(process.stdout.readline().strip())\n    process.stdout.close()\n"
    }]
  }]
};
