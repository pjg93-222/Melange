/* Step 11 (lane E-server): README paragraphs for the four new server surfaces.

   The file carries no section headings below its title -- 544 lines, one `#` --
   so these follow the house shape: prose paragraphs, bold lead-ins, backticked
   paths. It is also mixed (356 CRLF, 188 lone LF), so the engine pairs lines
   against the backup and new lines take CRLF, the majority class.

   Usage: node apply-e.js step11-readme.js [--check] */
'use strict';

const TAIL = 'The benchmark follows the [seasonal naïve method](https://otexts.com/fpp3/simple-methods.html).\n';

const SECTION =
  '\n' +
  '**Saved views** live under the console data root at `studio\\views\\<32 hex>.json`, so a\n' +
  'second console opened on the same data root lists the same views. `GET /api/studio/views`\n' +
  'returns them newest first with a sheet count in place of the sheets; `GET\n' +
  '/api/studio/views?id=` returns one view with its sheets and its active sheet; `POST\n' +
  '/api/studio/views` saves one and `POST /api/studio/views/delete` removes one. A view needs\n' +
  'a name of 1 to 80 characters and 1 to 24 named sheets, and its request body may not exceed\n' +
  '512 KB. Duplicate names are allowed. Deleting a view that is already gone still reports\n' +
  'success, so a repeated click is not an error. A read-only preview console refuses both\n' +
  'writes with "Saved views are read-only in this preview console; save from the original\n' +
  'console." and still answers the reads.\n' +
  '\n' +
  '**The briefing tray** is one shared tray per data root: an ordered\n' +
  '`studio\\briefing\\index.json` beside one `<id>.svg` per item, capped at 40 items. `POST\n' +
  '/api/studio/briefing/add` takes the caption fields and the chart itself as an SVG string of\n' +
  'at most 6 MB; a forty-first item is refused with 409, and a chart that is oversized or does\n' +
  'not begin `<svg` with 400. `POST /api/studio/briefing/remove` and `POST\n' +
  '/api/studio/briefing/order` maintain the tray, and an order has to be a permutation of the\n' +
  'tray it reorders. `GET /api/studio/briefing/item?id=` returns the stored chart as\n' +
  '`text/plain`, never as `image/svg+xml`: an SVG served from this origin under an image type\n' +
  'is script-capable, and these are assembled from report text. The tray is read-only in a\n' +
  'preview console.\n' +
  '\n' +
  '**The PowerPoint bundle** `vendor\\pptxgen.bundle.js` is PptxGenJS 4.0.1 (MIT), the UMD\n' +
  'browser build from the npm registry tarball, copied unmodified; `vendor/LICENSE-pptxgenjs.md`\n' +
  'carries its licence. SHA-256\n' +
  '`4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8`. The offline checks\n' +
  'assert that hash against the bytes the console serves at `/vendor/pptxgen.bundle.js`, not\n' +
  'against the file on disk. Load it with a plain script tag and read `window.PptxGenJS`; it\n' +
  'defines `window.JSZip` as a side effect and is not `require()`-able from Node.\n' +
  '\n' +
  '**Publish phone snapshot** writes one self-contained page. `POST /api/publish/pocket` takes\n' +
  'dataset ids from the contribution catalog, runs `tools\\pocket\\extract_pocket_data.py`\n' +
  'against this console own port and then `tools\\pocket\\build_page.py`, and writes\n' +
  '`mentat-pocket.html` into a `pocket` folder inside the configured report folder, beside the\n' +
  '`pocket-data.json` and `pocket-integrity.json` it was built from. The repository template\n' +
  '`tools\\pocket\\mentat-pocket.html` is read, never overwritten. Job state lives at `<data\n' +
  'root>\\publish\\<id>\\job.json` and is read back with `GET /api/publish/pocket?id=`; the\n' +
  'child output is kept beside it in `publish.log`. One publication runs at a time, a second is\n' +
  'refused with 409, and the console reports itself busy while one runs, so a restart will not\n' +
  'interrupt it. Uploading the finished page to a private link remains a manual step.\n';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  files: [{
    path: 'README.md',
    eol: 'crlf',
    edits: [{find: TAIL, replace: TAIL + SECTION}]
  }]
};
