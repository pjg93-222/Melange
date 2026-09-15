/* Step 4 (lane E-server): three static allow-list entries.

   /chart-briefing.js and /chart-briefing.css are the parallel client lane's
   files; this lane only opens the routes. /vendor/pptxgen.bundle.js is the
   vendored PptxGenJS UMD bundle. The allow-list is an exact-key table, so a
   nested path opens no traversal: nothing but these literal keys resolves.

   Because two of the three files do not exist while the client lane is still
   working, an allow-listed file that is missing now answers 404 instead of
   raising FileNotFoundError into the 400 handler, which would have put a
   local filesystem path in the response body.

   Usage: node apply-e.js step4-assets.js [--check] */
'use strict';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  files: [{
    path: 'server.py',
    edits: [
      {find: "                 '/theme.js': ('theme.js', 'text/javascript')}\n",
       replace:
        "                 '/theme.js': ('theme.js', 'text/javascript'),\n" +
        "                 '/chart-briefing.js': ('chart-briefing.js', 'text/javascript'),\n" +
        "                 '/chart-briefing.css': ('chart-briefing.css', 'text/css'),\n" +
        "                 '/vendor/pptxgen.bundle.js': ('vendor/pptxgen.bundle.js', 'text/javascript')}\n"},

      {find: '                path = Path(__file__).parent / filename\n' +
             '                info = path.stat()\n',
       replace: '                path = Path(__file__).parent / filename\n' +
             '                if not path.is_file():\n' +
             '                    return self.send({"error": "Not found."}, 404)\n' +
             '                info = path.stat()\n'}
    ]
  }]
};
