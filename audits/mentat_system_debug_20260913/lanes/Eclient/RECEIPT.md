# Lane E-client receipt — Ride 2 client surfaces (E0, E1, E2, F6-followup, E5, E4, E3, E6)

Date: 2026-09-14. Agent: Claude architect. Authorised by Paul ("Execute the plan end to end").
Visual contract: `prompts\renders\R2_canvas_export.png` (Export menu) and `prompts\renders\R4_briefing.png` (briefing drawer).
Step files (replayable edit log): `...\scratchpad\lanes\Eclient\step1..step12` + `chart-briefing.src.js`,
`chart-briefing.test.src.js`, `test_studio_briefing_tray_browser.src.cjs`, `test_studio_copy_print_browser.src.cjs`.
Progress log: `...\scratchpad\lanes\Eclient\PROGRESS.md`.

## Correction to the task premise

The task said the previous attempt "stalled before writing anything". That is **false**: it had already
applied two steps to disk before stopping. Verified on disk before I touched anything:

- `chart-export.js` already carried `compose()` / `rasterize()` / `copy()` and `MentatExport={download,image,compose,rasterize,copy}` (mtime 02:27).
- `index.html` already carried the Export menu rename, the drawer, the print footer and the share dialog (mtime 02:29).

I built on those bytes rather than redoing them, and their `.bak-20260914-E` backups still hash to the
values in `hashes-before.txt` (checked; see the table below), so the before-state is intact and replayable.

## Files and hashes (SHA-256)

All "before" hashes are the `.bak-20260914-E` backups, each verified to still match `hashes-before.txt`.

| File | Before | After | EOL class before → after |
|---|---|---|---|
| `C:\Users\pgoff\Mentat\mentat\app\chart-export.js` | `4ae33213…1ec9c` (4,540 B) | `9430db34…cd74a` (6,797 B) | mixed → mixed |
| `C:\Users\pgoff\Mentat\mentat\app\index.html` | `fd220c11…1ee98` (54,919 B) | `6aa31929…3c0d8` (58,121 B) | mixed → mixed |
| `C:\Users\pgoff\Mentat\mentat\app\chart-studio.js` | `21f3d67d…110b8` (138,508 B) | `766f2169…bec72` (151,500 B) | CRLF → CRLF |
| `C:\Users\pgoff\Mentat\mentat\app\chart-studio.css` | `81fe526f…eee94` (33,423 B) | `021d508e…58887` (36,449 B) | CRLF → CRLF |
| `C:\Users\pgoff\Mentat\mentat\app\graph.js` | `d33579f8…d08b3` (22,698 B) | `2d2f2730…89f12` (24,188 B) | mixed → mixed |
| `C:\Users\pgoff\Mentat\mentat\app\charts.js` | `924b088c…7ac45` (34,056 B) | `1df31cb2…cfa9a` (34,882 B) | mixed → mixed |
| `C:\Users\pgoff\Mentat\mentat\app\chart-briefing.js` | NEW | `57b4ff99…21816` (27,384 B) | — → LF |
| `C:\Users\pgoff\Mentat\mentat\app\chart-briefing.css` | NEW | `b9593bac…10369` (6,828 B) | — → LF |
| `C:\Users\pgoff\Mentat\mentat\app\tests\chart-briefing.test.js` | NEW | `b2e0a183…ace2a` (2,761 B) | — → LF |
| `C:\Users\pgoff\Mentat\mentat\tests\test_studio_briefing_tray_browser.cjs` | NEW | `727b6d90…3e43a` (10,630 B) | — → LF |
| `C:\Users\pgoff\Mentat\mentat\tests\test_studio_copy_print_browser.cjs` | NEW | `6975cd2d…2e1d6` (9,745 B) | — → LF |
| `C:\Users\pgoff\Mentat\mentat\tests\test_contribution_export_browser.cjs` | `1a2ece7c…3f2a0` (7,240 B) | `511727bf…b9b52` (9,106 B) | LF → LF |
| `C:\Users\pgoff\Mentat\mentat\app\tests\chart-studio-core.test.js` | `fda752d0…c2f06` | **unchanged** | — |

Untouched, as required: `server.py`, `vendor/`, `tools/pocket`, `README.md`, `.gitignore`, all python tests.
(`server.py.bak-20260914-E` and `README.md.bak-20260914-E` exist from the parallel server lane; I did not
read-modify-write either file.)

## Per-item status

**E0 export foundation — DONE.** `compose()/rasterize()` split and `image()` kept as the download wrapper
were already on disk from the stalled attempt; I verified the four existing callers
(`charts.js`, `graph.js`, `contribution-studio.js`, `chart-studio.js`) are untouched and still call `image()`.
Added in this session: `currentChart()` in `chart-studio.js` (`{svg,title,scope,chip,note,basis,sheetId,
sheetName,source,provenance}`) and the CSV `['Note', el('note').textContent]` row on the worksheet path.
Menu summary is "Export", ids unchanged (`#studio-download`, `#studio-download-png/-svg/-csv`).
`chip` is an addition to the specified shape: the R4 card shows the short scope chip, while `scope`
stays the full provenance line the slide and print sheet need.

**E1 copy image — DONE.** `MentatExport.copy` guards `isSecureContext && clipboard.write && ClipboardItem`,
passes the `rasterize()` Promise unawaited into `ClipboardItem` (so the user activation is not spent while
the PNG draws), and maps `NotAllowedError`. Entries: studio Export menu (`#studio-copy-image` →
status `Copied 600x709 PNG with title and scope caption.`), Graph export row (`#graph-copy-image`), classic
builder (`#chart-copy-image`). `graph.js` gained `exportSubject()` so download, copy and briefing read one
description of the chart instead of three.

**E2 print chart — DONE.** `@media print` block in `chart-studio.css`; `printChart()` fills
`#studio-print-title/-scope/-source` from `currentChart()` (title, scope+note, basis · Source · Workbook
SHA-256 · Printed <date>) plus the `MENTAT` mark, sets `body.studio-printing`, prints, and cleans up on
`afterprint` with a 60 s backstop for dialogs that never fire it.

**F6 follow-up — DONE.** Per R2, Canvas only now keeps the header "Inspector" button with its filter-count
badge at every width, gold-bordered while closed, opening the Inspector as a fixed drawer over the chart.
`.studio-options-hidden .studio-inspector` was removed from the blanket `display:none` set and replaced by
`[hidden]`-driven rules; `setOptionsHidden()` and `syncInspector()` now agree on when it is closed.

**E5 saved views (client) — DONE.** `saveView()` uses the sheet-rename inline-input pattern with default
`"<sheet> · <dataset>"`; `openViews()` uses `popup()` with the "This source" / "Other sources" groups and
lists unopenable views disabled with the reason; `openView()` selects another contributions dataset via
`selectContributionDataset()` then `commit()`s the sheets exactly like `restore()`; a one-time
`mentat-chart-studio-migrated-v1` migration posts `readStore()` entries as
`"Recovered · <source> · N sheets"` only when the server list is empty, and does **not** set the flag if a
post fails. Read-only refusal shown verbatim (live evidence below).

**E4 briefing tray — DONE.** New `chart-briefing.js` IIFE exposes
`MentatBriefing.{capture,add,move,remove,list,exportPrint,exportHtml,exportPptx}` (+ `open`, `close`,
`model`). Drawer markup per R4 with the verbatim labels "Briefing", "<n> items", "Move up", "Move down",
"Remove", gold "Export PowerPoint", "Print briefing", "Share bundle", "Save view", and the note
"Every slide carries its scope, basis and source SHA-256." "Add to briefing" with a purple badge sits in
the studio toolbar, the Graph export row and the classic builder. Server-backed with an in-memory fallback
and a stated notice. Exports: Print briefing (page per item on the E2 sheet), HTML bundle (self-contained,
inline SVGs, captions, provenance table, print CSS), PowerPoint.

**E3 PowerPoint — DONE.** `exportPptx()` lazy-loads `/vendor/pptxgen.bundle.js` as a same-origin script tag
and reads `window.PptxGenJS`; `LAYOUT_WIDE`; per item: title 0.5,0.35 12.3×0.7 in 22 pt Georgia #342649;
chart PNG from `rasterize()` at 1.5× at 0.5,1.15 12.3×5.0 in `sizing:{type:'contain'}`; 1 pt gold #ECA91C
rule at y 6.15; scope 0.5,6.3 9 pt Arial #716A64; source note 0.5,6.8 8 pt
`Source: <workbook> · SHA-256 <12> · basis <label> · exported <date> from Mentat Chart Studio`; MENTAT
right-aligned 12 pt Georgia plum; speaker notes carry title, chip, full scope, note, provenance and the
console URL; file `mentat-briefing-<yyyy-mm-dd>.pptx` via `MentatExport.download`.

**E6 phone snapshot (client) — DONE.** "Share bundle" opens the dialog, fills a dataset multi-select from
`/api/contributions/catalog` (unavailable reports disabled with the server's reason), posts
`/api/publish/pocket {datasets}`, polls `/api/publish/pocket?id=` every 1.5 s with elapsed seconds and a
15-minute stop, shows `output_path` on success, and carries the note
"Uploading to the private phone link is the coordinator's step."

## Judgment calls Paul should rule on

1. **"HTML bundle" moved into the Share bundle dialog.** R4's footer has exactly four buttons
   (Export PowerPoint / Print briefing / Share bundle / Save view) and E4 also requires an HTML-bundle
   export. Rather than add a fifth button the approved render does not show, the HTML bundle is
   "Download HTML bundle" inside the Share bundle dialog, beside "Publish phone snapshot" — both are
   bundles. `#studio-briefing-html` kept its id. Say the word and it moves back to the footer.
2. **`<n> items` pluralises.** The chip reads "1 item" / "2 items" rather than a literal "1 items".
3. **`chip` added to `currentChart()`** (see E0 above).

## Checks run

- `node --check`: `chart-export.js`, `chart-studio.js`, `chart-briefing.js`, `graph.js`, `charts.js`,
  `chart-briefing.test.js`, `chart-studio-core.test.js`, `test_studio_briefing_tray_browser.cjs`,
  `test_studio_copy_print_browser.cjs`, `test_contribution_export_browser.cjs` — all clean.
- Id census (`redesign\checkids.js`): **131 → 135 ids referenced, missing from index.html: none** (green).
- `node --test mentat/app/tests/chart-studio-core.test.js` — **81 pass, 0 fail** (baseline 81; did not drop).
- `node --test mentat/app/tests/chart-briefing.test.js` — **7 pass** (order, immutability, move off both
  ends, remove, cap 40 refusal keeping the oldest, room after a removal).
- `test_studio_briefing_tray_browser.cjs` — **2 pass**: drawer labels read out of the shipped `index.html`;
  add/reorder/remove; "2 items"; badge "2"; read-only notice; HTML bundle has one section and one root
  `<svg>` per chart, both surviving titles, the removed title absent, the workbook SHA in the provenance
  table, no `<script>`. PowerPoint case loads the vendored bundle via `addScriptTag`, exports a two-item
  tray, inflates the ZIP central directory with `zlib.inflateRawSync` and asserts `ppt/slides/slide1.xml`,
  `slide2.xml` and `ppt/notesSlides/notesSlide1.xml` exist and contain the titles and the SHA string, plus
  embedded `ppt/media/*`.
- `test_studio_copy_print_browser.cjs` — **4 pass** at a secure `http://localhost` route with
  clipboard-read/write granted: a real `navigator.clipboard.read()` returns `image/png` whose pixels are the
  whole composed drawing; the missing-capability message is verbatim; `emulateMedia({media:'print'})` gives
  `display:none` on side/toolbar/inspector/shelves/sheets/status/nav/note, `block` on the provenance footer,
  `max-height:none` on the chart and `overflow:visible` on the wrap, and `page.pdf()` returns > 1000 bytes;
  Canvas only at 1440 px shows the Inspector button, the badge, the gold closed border and the fixed drawer.
- `test_contribution_export_browser.cjs` — **1 pass**, with the new case: `compose()` + `rasterize()` perform
  no anchor click, the downloaded SVG is byte-identical to what `compose()` built, and `{caption:false}`
  yields the bare chart height with no baked-in text.
- Regression sweep, all green: `test_studio_canvas_only_browser.cjs` (1), `test_chart_builder_browser.cjs`
  (2), `test_console_browser.cjs` (1), `test_chart_comparison_browser.cjs` (1),
  `test_chart_studio_contributions.cjs` (14).
- **Live console.** `python server.py --port 8819 --read-only --data-root <scratchpad>` started via
  `Start-Process` (pid 47112) and stopped by that pid; port confirmed free afterwards. No console process of
  Paul's was touched, and the scratch data root means nothing in `LOCALAPPDATA\Mentat\console` was read or
  written. Results:
  - `/chart-briefing.js` 200 (27,384 B), `/chart-briefing.css` 200 (6,828 B),
    `/vendor/pptxgen.bundle.js` 200 (460,889 B) — the parallel server lane's allow-list is already live.
  - `GET /api/studio/views` → `200 {"views":[]}`; `GET /api/studio/briefing` → `200 {"items":[]}`;
    `POST /api/studio/views`, `POST /api/studio/briefing/add`, `POST /api/publish/pocket` → `403`;
    `GET /api/publish/pocket?id=nothing` → `400`.
  - Page probe (`probe8819.cjs`), **zero console errors / page errors**: Export menu reads
    `Image (PNG), Image (SVG), Data (CSV), Copy image, Print chart, Add to briefing, Save view, Open view`;
    drawer title "Briefing", count "0 items", footer
    `Export PowerPoint, Print briefing, Share bundle, Save view`, note verbatim, `chart-briefing.css`
    applied (`position: fixed`); share dialog `Close, Publish phone snapshot, Download HTML bundle`;
    `MentatStudioPane` exposes `currentChart, saveView, openViews`; Add to briefing →
    `"Not saved in a read-only preview: this briefing is kept in this tab only."`; Open view → popup
    `This source / No saved views for this source yet / Other sources / None`; Save view → inline input →
    `"Saved views are read-only in this preview console; save from the original console. \"Ride B\" is kept
    in this tab only."`

## Ride steps satisfied (by test or live probe; none clicked by hand)

- **22–24 (F6)** — `test_studio_canvas_only_browser.cjs` still green, plus the new desktop-width case:
  Canvas only keeps Export, hides every other toolbar child, and shows the Inspector button with its badge.
- **25 (E1)** — real clipboard round-trip at localhost; the paste itself into Word/Teams is Paul's step.
- **26 (E2)** — print media assertions + a non-empty PDF.
- **27–28 (E4)** — add on two sheets, badge "2", reorder, remove, list with title/scope/basis/time.
  "order persists after reload" is **not** exercised (needs a writable console; see limits).
- **29 (E3)** — deck written, slides and notes inspected from the ZIP. Opening it in PowerPoint on Paul's
  machine is his step.
- **30 (E5)** — save/open wired and the read-only refusal shown; the round trip through a writable console
  and the mirror console is **not** exercised (see limits).
- **31 (E4/E6)** — the Share bundle dialog opens and lists reports; the publish job itself is **not**
  exercised (403 in a read-only console, and the extractor is the server lane's file).

## What I could not exercise, and why

1. **Writable-console persistence.** I verified against a read-only console only, deliberately: a writable
   run would have to point at a real data root, and Paul's console processes are off limits. So the server
   round trip (views saved to `<data root>\studio\views\*.json`, briefing `index.json` + `<id>.svg`, order
   persisting across reload, the mirror console seeing the same view) is **claimed by contract, not
   observed**. Every degraded path *is* observed.
2. **The pocket publish job** (ride step 31's output file) — 403 under read-only, and `tools\pocket` belongs
   to the parallel lane.
3. **The one-time localStorage migration** — it needs a writable console and a non-empty legacy store;
   it is covered by code review only, not by a test.
4. **`node --test mentat/app/tests` (directory form)** fails on this box with `MODULE_NOT_FOUND` under
   Node v24.18.0 — a pre-existing Node-version behaviour, not something this lane introduced. Passing the
   two files explicitly works: **88 pass, 0 fail**.
5. **Line endings, one blemish.** `chart-export.js` kept its *class* (mixed → mixed), but five lines whose
   text is unchanged from the backup now end LF where they ended CRLF: lines 51, 75, 77, 85, 94
   (`  }` ×3, `if (format !== 'png') …`, `try {`). This came from the stalled attempt's step 1, where the
   restructuring of `image()` defeated the patch engine's line pairing. `index.html`, `graph.js` and
   `charts.js` drifted on **zero** lines. I left the five bytes alone rather than hand-editing endings
   after the fact; say the word if you want them restored.
6. **A replay hazard, found and fixed.** `step11` originally both created files and *inserted* the new case
   into `test_contribution_export_browser.cjs`. Re-running it duplicated that insert three times. I restored
   the file from `.bak-20260914-E` (hash back to `1a2ece7c…`, verified), split the insert into
   `step12-export-test-case.js`, and applied it once. `step11` is now creates-only and safe to replay;
   `step12` is marked single-shot in its header.
7. **Not touched:** `chart-studio-core.test.js` needed no change, so it is byte-identical to its backup.
   No git operation of any kind was run.
