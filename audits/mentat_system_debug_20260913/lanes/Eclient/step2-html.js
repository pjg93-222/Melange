/* Lane E-client markup: the Export menu of R2, the briefing drawer of R4, the
   print-only footer E2 fills, the phone-snapshot dialog E6 opens, and the two
   "Copy image" / "Add to briefing" entries the Graph export row and the classic
   builder gain. Every label that appears in R2 or R4 is verbatim. */
'use strict';

const MENU =
'<details class="studio-menu" id="studio-download"><summary>Export</summary><div>' +
'<button id="studio-download-png" type="button">Image (PNG)</button>' +
'<button id="studio-download-svg" type="button">Image (SVG)</button>' +
'<button id="studio-download-csv" type="button">Data (CSV)</button>' +
'<hr>' +
'<button id="studio-copy-image" type="button">Copy image</button>' +
'<button id="studio-print-chart" type="button">Print chart</button>' +
'<hr>' +
'<button id="studio-briefing-menu-add" type="button">Add to briefing</button>' +
'<hr>' +
'<button id="studio-save-view" type="button">Save view</button>' +
'<button id="studio-open-views" type="button">Open view</button>' +
'</div></details>' +
'<button id="studio-briefing-add" class="studio-briefing-add" type="button" aria-controls="studio-briefing" ' +
'title="Put this chart in the briefing tray">Add to briefing' +
'<span id="studio-briefing-badge" class="studio-briefing-badge" hidden></span></button>';

const PRINT_FOOTER =
'\n<div id="studio-print-footer" class="studio-print-only" aria-hidden="true">' +
'<p id="studio-print-title" class="studio-print-title"></p>' +
'<p id="studio-print-scope" class="studio-print-line"></p>' +
'<p id="studio-print-source" class="studio-print-line"></p>' +
'<p class="studio-print-mark">MENTAT</p>' +
'</div>';

const DRAWER =
'<aside class="studio-briefing" id="studio-briefing" hidden aria-label="Briefing">\n' +
'<div class="studio-briefing-head"><h3 class="studio-briefing-title">Briefing</h3>' +
'<span id="studio-briefing-count" class="studio-briefing-count"></span>' +
'<button id="studio-briefing-close" class="studio-briefing-close" type="button">Close</button></div>\n' +
'<p id="studio-briefing-notice" class="studio-briefing-notice" role="status" hidden></p>\n' +
'<div id="studio-briefing-items" class="studio-briefing-items"></div>\n' +
'<div class="studio-briefing-foot">\n' +
'<button id="studio-briefing-pptx" class="studio-briefing-primary" type="button">Export PowerPoint</button>\n' +
'<div class="studio-briefing-actions">' +
'<button id="studio-briefing-print" type="button">Print briefing</button>' +
'<button id="studio-briefing-html" type="button">HTML bundle</button>' +
'<button id="studio-briefing-share" type="button">Share bundle</button></div>\n' +
'<button id="studio-briefing-save-view" type="button">Save view</button>\n' +
'<p class="studio-briefing-note">Every slide carries its scope, basis and source SHA-256.</p>\n' +
'</div>\n</aside>\n' +
'<dialog id="studio-share" class="studio-share" aria-labelledby="studio-share-title">\n' +
'<div class="studio-share-head"><h3 id="studio-share-title">Share bundle</h3>' +
'<button id="studio-share-close" type="button">Close</button></div>\n' +
'<p class="studio-note">Choose the reports the phone snapshot should carry.</p>\n' +
'<div id="studio-share-datasets" class="studio-share-datasets" role="group" aria-label="Reports"></div>\n' +
'<button id="studio-share-publish" class="studio-share-publish" type="button">Publish phone snapshot</button>\n' +
'<p id="studio-share-progress" class="studio-note" role="status"></p>\n' +
'<p id="studio-share-output" class="studio-note" hidden></p>\n' +
'<p class="studio-note">Uploading to the private phone link is the coordinator\u2019s step.</p>\n' +
'</dialog>\n';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-E',
  eol: 'crlf',
  files: [
    {
      path: 'index.html',
      eol: 'crlf',
      edits: [
        {find: '<link rel="stylesheet" href="/chart-studio.css">',
         replace: '<link rel="stylesheet" href="/chart-studio.css"><link rel="stylesheet" href="/chart-briefing.css">'},
        {find: '<script src="/chart-studio.js" defer></script>',
         replace: '<script src="/chart-studio.js" defer></script><script src="/chart-briefing.js" defer></script>'},
        {find: '<button id="graph-export" class="secondary" type="button">Export chart</button>',
         replace: '<button id="graph-export" class="secondary" type="button">Export chart</button>' +
           '<button id="graph-copy-image" class="secondary" type="button">Copy image</button>' +
           '<button id="graph-briefing" class="secondary" type="button">Add to briefing</button>'},
        {find: '<button id="chart-save-csv" class="secondary" type="button">Export data CSV</button>',
         replace: '<button id="chart-save-csv" class="secondary" type="button">Export data CSV</button>' +
           '<button id="chart-copy-image" class="secondary" type="button">Copy image</button>' +
           '<button id="chart-briefing" class="secondary" type="button">Add to briefing</button>'},
        {find: '<details class="studio-menu" id="studio-download"><summary>Download</summary><div>' +
           '<button id="studio-download-png" type="button">Image (PNG)</button>' +
           '<button id="studio-download-svg" type="button">Image (SVG)</button>' +
           '<button id="studio-download-csv" type="button">Data (CSV)</button></div></details>',
         replace: MENU},
        {find: '<p id="studio-note" class="studio-note">Choose a verified report in the Data panel to begin.</p>',
         replace: '<p id="studio-note" class="studio-note">Choose a verified report in the Data panel to begin.</p>' + PRINT_FOOTER},
        {find: '<div class="studio-overview" id="studio-overview" hidden aria-label="Company overview">',
         replace: DRAWER + '<div class="studio-overview" id="studio-overview" hidden aria-label="Company overview">'}
      ]
    }
  ]
};
