/* F1 step 3 - app.js: build stamp in the header, gold out-of-date banner with
   Restart, and a 60 s /api/health poll while the tab is visible. Startup makes
   no extra request: the light session now carries the build block.
   app.js is genuinely mixed CRLF/LF; new lines take LF like its tail. */
'use strict';
const fs = require('fs');
const path = require('path');

const block = fs.readFileSync(path.join(__dirname, 'step3-block.txt'), 'utf8').split('\r\n').join('\n');

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'lf',
  files: [{
    path: 'app.js',
    eol: 'lf',
    edits: [
      // 1. Render the stamp from the session that init already fetches.
      {find: "  try { const session = await api('/api/session?light=1'); token = session.token; readOnly=!!session.read_only;\n" +
             "    evidenceCollectionAvailable=!!session.evidence_collection_available;",
       replace: "  try { const session = await api('/api/session?light=1'); token = session.token; readOnly=!!session.read_only;\n" +
             "    try { renderBuild(session); scheduleBuildPoll(); } catch { }\n" +
             "    evidenceCollectionAvailable=!!session.evidence_collection_available;"},
      // 2. Declare the guard before init() runs, so no let sits in its TDZ.
      {find: "restoreDraft();\nshowView(location.hash.slice(1));\ninit();",
       replace: block + "restoreDraft();\nshowView(location.hash.slice(1));\ninit();"}
    ]
  }]
};
