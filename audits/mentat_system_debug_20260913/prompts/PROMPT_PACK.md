# Chart Studio prompt pack (renders first, then build)

Owner: Paul. Coordinator: Claude. Date: 2026-09-14.
Plan: `C:\Users\pgoff\.claude\plans\the-mentat-chart-system-breezy-wilkinson.md`.

How this pack is used
1. Each RENDER prompt goes to Higgsfield `gpt_image_2_5` (variant flare, 16:9, quality high,
   resolution 2k, background opaque, 5.5 credits) with the named reference passed as
   `image_references`. After-state only; the "before" is the live screen.
2. Paul answers per render with one line: `approve R#`, `approve with: <delta>`, or
   `reject: <reason>`. A delta means one more render that keeps everything and changes only the
   delta (the prior render becomes the reference). No build starts on silence.
3. Each IMPLEMENTATION prompt goes to a build agent (Claude executor or architect now; Codex when
   its quota returns) with the approved render as the visual contract.

Shared blocks (paste verbatim into every render prompt)

THEME: page paper #fcf7f4; panels ivory #f7ede4; cards white with 1px #e4d9d0 borders and 6px
corners; text deep plum #342649; muted text #716a64; selected states purple #57447b with ivory
text; exactly one gold #eca91c primary action per screen; lilac #d6c8e2 chips; teal #327a7a for
one secondary mark; light grid #e8e0da; negatives #bf3f36. UI text in a clean geometric sans
(Articulat CF character, Arial-like); headings in a warm transitional serif (Freight Text Pro
character, Georgia-like) at normal size (page title about 30px, chart title about 21px). Left
navigation rail 196px on ivory: bold sans wordmark MENTAT, tagline "Giving, in perspective.",
section labels WORKSPACE (Loading, Collection), ANALYSIS (Graph, Chart Studio, Cross-reference),
EVIDENCE (PAC evidence), with Chart Studio selected in purple.

STYLE: professional, dense but airy, pixel-perfect, straight edges, no perspective, no hands,
no monitor bezel, no watermark, no third-party logos, all text spelled exactly as written.
AVOID: no photographic scene, no hands or monitors, no lorem ipsum, no misspelled labels, no
Tableau or Salesforce logos, no dark mode, no emoji.

Shared implementation rules (paste verbatim into every implementation prompt)

RULES: work only in C:\Users\pgoff\Mentat\mentat\app (and its tests); before the first edit of a
file copy it to `<file>.bak-20260914-<fix>` and never overwrite an existing .bak; preserve each
file's line-ending class (census before writing: chart-studio.js CRLF, chart-studio-core.js mixed
mostly CRLF, chart-studio.css CRLF, chart-comparison.js CRLF, chart-studio-contributions.js LF,
chart-math.js LF, index.html mixed, server.py census required); no git add/commit/stash; do not
touch Paul's console processes; verify on your own `python server.py --port 8816 --read-only`
started via Start-Process and stopped by that PID; Write/Edit tools refuse this tree from the
Melange worktree, so use the exact-anchor patch engine pattern
(C:\Users\pgoff\Mentat\audits\mentat_system_debug_20260913\redesign\apply.js) and keep each
step file as the replayable edit log; keep the 114-id census green
(redesign\checkids.js); run `node --check` on every edited JS, `python -m py_compile` on every
edited .py (delete the pyc), `node --test mentat/app/tests/chart-studio-core.test.js` (77 today,
must not drop), plus the named Playwright test with
`MENTAT_NODE_MODULES=C:\Users\pgoff\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules`;
the approved render is the visual contract: match its labels, placement and states, colours only
from acu-theme.css tokens; STOP and report on any ambiguity instead of guessing; finish with a
receipt (files + before/after hashes, checks run, what was skipped and why).

------------------------------------------------------------------------------------------------

## R1 - Builder after-state: build stamp, click-to-add, data source ready line, wording
Covers F1 (stamp), F2, F3, F5. Reference: v2A_workbench.png (Higgsfield job 58c3d089-db24-48b8-ab67-a0be4a645379).
Rendered 2026-09-14 as job ecf1d418-d216-46aa-9b9c-87bc1a4ea2af.

RENDER PROMPT R1:
Ultra-crisp 16:9 screenshot of the MENTAT console web app on its Chart Studio screen, same
layout as the reference image, keep everything the reference shows unless named here. Header
row: serif "Chart Studio", a lilac chip "Banking · All cycles", a small outlined button "Data
source" beside it, then on the right a button "Company overview" and a segmented control
"Builder | Canvas only" with Builder selected in purple. Comparison toolbar beneath: segmented
"1 chart | 2 charts | 3 charts | 4 charts" (1 chart selected), a toggle "Linked filters". Sheet
toolbar: "Undo", "Redo", "Swap", "Sort ascending", "Sort descending", "Show mark labels",
"Fit: Standard", "Clear", "Duplicate sheet", "Export", "Show Me", and far right a dashed
"Classic builder". Left "Data" panel on ivory: a one-line summary "Data source · Banking ·
Published included receipts · ready" with a chevron, then "Search fields", then DIMENSIONS with
pills "Company" (Abc), "Recipient category" (Abc), "Election cycle" (small drawn calendar glyph),
"Contributor state" (drawn map-pin glyph), and MEASURES with pills "Selected amount" (#),
"Observation count" (#). The "Recipient category" pill is hovered: a small purple "+" button
shows at its right end and a tooltip reads "Click to add · drag to place · Enter for actions".
Centre white card: shelf strip rows "Columns" holding pill "Company", "Rows" holding pill
"SUM(Selected amount)", "Filters" reading "Drop a field to filter"; serif title "Published
included receipts by Company" at about 21px; a vertical bar chart of ten bank names in plum with
the tallest bar gold, axis $0 to $16M, light grid. Right "Inspector" card with tabs "Marks |
Analytics | Filters" (Marks active), a Show Me grid of small chart tiles, and "Mark type: Bar".
Bottom: sheet tabs "Data Source | Sheet 1 | + New sheet". Status bar at the very bottom, small
muted text: "592,570 source observations · 10 groups · Included receipts reconcile to the
workbook. · 1 verified query this session · build e666f95 · :8802 · started 15:20 · pid 41288".
THEME block. STYLE block. AVOID block.

GATE R1: approve R1 | approve with: <delta> | reject: <reason>

IMPLEMENTATION PROMPTS bound to R1:

F0 (no render needed; ships with F2)
Files: chart-studio-core.js (add pure `carriedFilterValue(fieldId, value)`: for fieldId 'cycle'
map /^\d{4}$/ to `${v-1}-${v}`, keep everything else; add `graphCycleValue(cycleLabel)` reverse
map), chart-studio.js `graphScope()` (:1989-1996) uses it before pushing filters, tests/
chart-studio-core.test.js (+2 tests: '2024' -> '2023-2024', '2023-2024' unchanged). Acceptance:
ride step 17 (Graph cycle 2025-2026 + company -> Open in Chart Studio shows the company's
2025-2026 receipts, not "No matching observations"). RULES block.

F1 build stamp + stale guard + restart
Files: server.py (module constants CODE_TREE_SHA256 over sorted app/*.py including server.py,
ASSET_TREE_SHA256 over the allow-listed static files, GIT_SHA via `git rev-parse --short HEAD`
with 'unknown' fallback, STARTED_AT; /api/health and /api/session?light=1 add git_sha,
code_sha256, assets_sha256, on_disk_code_sha256_now, on_disk_assets_sha256_now, started_at,
port, pid, busy; keep server_code_sha256; hashes cached by (size, mtime_ns); new POST
/api/restart returning 403 when read_only, 409 when busy, else Popen of Start-MentatApp.ps1
-NoBrowser -Port <port> detached and {restarting:true}), Start-MentatApp.ps1 (hash the same
app/*.py set; in the port loop, when health matches identity but not the hash and busy is false
and the pid's Win32_Process CommandLine contains server.py: print "Stopping stale MENTAT server
pid N on port P", Stop-Process, wait up to 5 s, start on the SAME port; read-only or busy or
foreign servers untouched with a printed notice; add -NoBrowser), index.html (:21 span
#build-stamp; #stale-banner hidden), app.js (init: render stamp from session.build; poll
/api/health every 60 s when the tab is visible; code mismatch -> gold banner "This console is
running an older build. Restart" with a Restart button calling /api/restart then polling health
until pid changes then location.reload(); assets-only mismatch -> "Interface files changed.
Reload"), workspace.css (banner + stamp styles), README.md :106-109 (launcher contract now
"replaces an idle stale server on the same port"). Tests: tests/test_contribution_http.py
(health fields present; restart 403 read-only and 409 busy with subprocess.Popen patched),
tests/test_desktop_launcher.py (new stale-server case: byte-modified copy of server.py running
on port P, launcher -Port P -> new pid, current hash, old pid dead; existing cases unchanged),
mentat/tests/test_app_lazy_startup_browser.cjs (session stub with a mismatching build block ->
banner text; the recorded startup calls stay identical). Acceptance: ride steps 04-06. Hard rule:
never stop a busy server. RULES block.

F2 click-to-add
Files: chart-studio-core.js (pure `quickAddZone(field, sheet)` -> 'columns'|'rows': dimension
-> columns if empty else rows; measure -> rows if empty else columns; export it),
chart-studio.js (:459-471 replace the selection-only branch with
`commit(() => place(core.quickAddZone(field, sheet()), field.index))` plus a status line "Added
<field> to <zone>"; keep the filters branch; Show Me selection reads shelves only; pill title and
aria-label "Click to add · drag to place · Enter for actions"; the Enter menu gains a first item
"Add to <zone>"), chart-studio.css (`.studio-fields .studio-pill::after` small "+" visible on
hover/focus-visible, purple). Drag handlers and the drop zones untouched. Tests: core (+4 zone
cases), new mentat/tests/test_studio_click_to_add_browser.cjs (fixture pattern of
test_original_studio_contributions_browser.cjs:10-24: click a dimension pill -> pill in
#studio-columns and one query fired; Undo empties it). Acceptance: ride steps 07-10. RULES block.

F3 data source always findable
Files: index.html (:197 `<details open>`; :168 permanent header button "Data source" (id
studio-scope-change, drop hidden); `<p id="studio-dataset-message" class="studio-note" hidden>`
after the dataset select; `<div id="studio-progress" hidden>` with message, elapsed, Cancel after
:235), chart-studio.js (:1811 never hide the button; :243 option.title = message; after :244
render dataset()?.message into #studio-dataset-message; :245 include per-dataset messages in the
thrown text; collapse the details once after the first successful load (flag sourceSettled) at
:256 and :223; contributionReady :235 shows #studio-progress with result.message and a 1 s
elapsed timer while status is preparing/building/queued, Cancel aborts the existing controller
(:304-305) and keeps the last good view; status() :148 also mirrors into #studio-status when the
details is closed), chart-studio.css (.studio-note.is-warning on ivory #fdf5e4; .studio-progress
row). Tests: new mentat/tests/test_studio_data_source_browser.cjs (catalog fixture with one
available:false + message -> message text and option title; query fixture returning
{status:'preparing', message, retry_after_ms:50} twice -> progress visible then hidden; details
open before load, closed after). Acceptance: ride steps 11-14. RULES block.

F5 wording (no render; approve from the was/now table below)
Files: chart-studio-core.js :178,:278,:280,:296 ("contribution explorer" -> "Verified
contributions (Data source, Verified contributions)"), index.html :235 default note -> "Choose a
verified report in the Data panel to begin.", chart-studio-core.js :197/:227 and
chart-studio-contributions.js :83, :92 per the table; tests that match the old strings updated.
Acceptance: ride steps 20-21. RULES block.

WAS / NOW table for Paul (F5):
| was | now |
|---|---|
| "Use the contribution explorer or remove this field." | "Switch Data source to Verified contributions, or remove this field." |
| "Choose a report worksheet in the Data panel to begin." (default, wrong mode) | "Choose a verified report in the Data panel to begin." |
| "Drag a dimension onto Columns or Rows and a measure onto the other shelf." | "Add a grouping (company, recipient, cycle) and a dollar measure." |
| "Place a measure on Columns or Rows to build a view." | "Add a dollar or count measure to Rows or Columns." |
| "This mark needs individual values. Use the report worksheet mode for that chart type." | "This chart type needs individual receipts. Switch Data source to Report worksheet." |

------------------------------------------------------------------------------------------------

## R1b - Out-of-date banner (delta on R1)
Covers F1 banner. Reference: v2A (R1 once approved). Rendered as job 1f45d873-b49e-4c97-a2f3-4b1ef43f0bc7.

RENDER PROMPT R1b:
Same MENTAT Chart Studio screenshot as the reference, keep everything exactly, add one change:
directly under the header row, a full-width gold #eca91c banner with plum text reading "This
console is running an older build. Close this tab and open http://127.0.0.1:8802, or press
Restart." and a plum button "Restart" at its right end. The status bar stamp at the bottom reads
"build 2906980 · :8803 · started 22:23 · pid 79412" in muted text. THEME block. STYLE block.
AVOID block.

GATE R1b: approve R1b | approve with: <delta> | reject: <reason>

------------------------------------------------------------------------------------------------

## R2 - Canvas only with the Export menu open
Covers F6, E1, E2. Reference: v2A (R1 once approved). Rendered as job 6b855fc3-70ea-47fe-9739-f22315c78b9b.

RENDER PROMPT R2:
Same MENTAT Chart Studio screen as the reference but in "Canvas only" mode: the Data panel, the
shelf strip, the sheet toolbar and the Inspector are gone; the header row remains with the serif
"Chart Studio", the lilac chip "Banking · Cycle 2025-2026 · Bank of America NA", the "Data
source" button, and on the right the segmented control "Builder | Canvas only" with Canvas only
selected in purple, an outlined "Inspector" button with a small purple badge "2", and an "Export"
button whose menu is OPEN showing rows "Image (PNG)", "Image (SVG)", "Data (CSV)", "Copy image",
"Print chart", "Add to briefing". The white card fills the width: serif title "Published included
receipts by Recipient category", a horizontal bar chart in plum with value labels ($4.8M, $3.1M,
$2.2M, $1.6M, $1.1M, $0.7M) for Company PAC, Candidate, Party Committee, Trade Association, Super
PAC, Leadership PAC, a dashed purple average line labelled "Avg $2.25M", and under the chart a
muted caption "Banking · Cycle 2025-2026 · Bank of America NA · Published included receipts ·
workbook SHA-256 842ba7a2". Sheet tabs "Data Source | Sheet 1 | + New sheet" remain under the
card. Status bar as in the reference. THEME block. STYLE block. AVOID block.

GATE R2: approve R2 | approve with: <delta> | reject: <reason>

IMPLEMENTATION PROMPTS bound to R2:

F6 Canvas only keeps Export; Inspector toggle
Files: chart-studio.css (:50 remove .studio-toolbar from the hidden set; add
`.studio-options-hidden .studio-toolbar > :not(#studio-download){display:none!important}` and
right-align the toolbar; <=1200px: `.studio-inspector-toggle[aria-expanded=false]` gold border),
chart-studio.js (:1969 set aria-expanded on the toggle; renderFilterRows :1782 mirrors the active
filter count into the toggle badge). Tests: new
mentat/tests/test_studio_canvas_only_browser.cjs (Canvas only -> #studio-download visible,
.studio-toolbar other children hidden; viewport 1100 -> toggle visible, click opens
#studio-inspector). Acceptance: ride steps 22-24. RULES block.

E0 export foundation (ships with E1)
Files: chart-export.js (split image() :9-57 into compose(source,title,context) -> {svg,width,
height} and rasterize(composed,{scale}) -> Promise<Blob>; image() stays the download wrapper so
charts.js:330, graph.js:216, contribution-studio.js:297, chart-studio.js:386,:1590 are
untouched; export MentatExport={download,image,compose,rasterize,copy}), chart-studio.js
(currentChart() -> {svg,title,scope,note,sheetId,sheetName,source,provenance}; CSV header gains
['Note', el('note').textContent]), index.html :187 menu summary "Export" (ids unchanged). Tests:
mentat/tests/test_contribution_export_browser.cjs keeps its expectations; +1 case compose text ==
downloaded SVG and rasterize returns image/png without an anchor click. RULES block.

E1 copy image
Files: chart-export.js (copy(source,title,context): guard window.isSecureContext &&
navigator.clipboard?.write && ClipboardItem else throw "Copy needs Chrome or Edge at localhost.
Download the PNG instead."; navigator.clipboard.write([new ClipboardItem({'image/png':
rasterize(compose(...))})]) passing the Promise; NotAllowedError -> "Click the chart, then copy
again, or download the PNG."), index.html :187 "Copy image" entry, chart-studio.js :1895 handler
with status "Copied WxH PNG with title and scope caption.", graph.js :209-218 and charts.js
:328-332 gain the same entry. Tests: Playwright with permissions clipboard-read/write at
http://localhost route (secure context): copy -> clipboard.read() has image/png; clipboard
undefined -> fallback message. Acceptance: ride step 25. RULES block.

E2 print chart
Files: chart-studio.css (@media print: hide nav, header, toolbar, shelves, side, inspector,
sheet tabs, status; .studio-canvas-wrap overflow visible; svg max-height none, width 100%;
@page landscape 14mm; .studio-print-only shown), index.html (print-only footer after
#studio-note), chart-studio.js (printChart(): fill footer from currentChart(): title, scope,
basis, source SHA-256, date, MENTAT; body.studio-printing; window.print(); cleanup on
afterprint), index.html :187 "Print chart". Tests: Playwright emulateMedia print -> computed
display none on .studio-side/.studio-toolbar, svg max-height none, page.pdf length > 1000.
Acceptance: ride step 26. RULES block.

------------------------------------------------------------------------------------------------

## R3 - Reconciliation strip on Scope B
Covers F4 (a, b, c, d). Reference: v2A (R1 once approved). Rendered as job b6f6fb89-08c6-4e73-904e-1796f957f563.

RENDER PROMPT R3:
Same MENTAT Chart Studio builder screen as the reference with these changes. Header chip reads
"Carried from Graph · Banking · Cycle 2025-2026 · Bank of America NA" followed by a small muted
line "Employee level: not carried (verified data has no level field)". Under the serif chart
title "Published included receipts by Recipient category" a thin ivory strip with 1px #e4d9d0
border reads: "Basis: Published included receipts. Graph shows $12,090,412 for Bank of America
NA · 2025-2026 (workbook receipts). Studio total $12,090,412. Agree." with the word "Agree." in
teal #327a7a and a small link "Why Cross-reference differs". The Filters shelf shows two lilac
pills "Company: Bank of America NA" and "Election cycle: 2025-2026" each with an x. The group
counter under the chart reads "1-8 of 8 groups · totals cover all 8". Everything else as the
reference. THEME block. STYLE block. AVOID block.

GATE R3: approve R3 | approve with: <delta> | reject: <reason>

IMPLEMENTATION PROMPT bound to R3:

F4 same numbers
Files: chart-studio-contributions.js (pure reconcile(result, basis, graphView, filters) ->
{graphCents, studioCents, agree, reason}; reasons in order: basis is not 'receipt'; Graph tier or
giving filter set (no verified field); workbook sha mismatch (graph.reports[].sha256 vs
result.provenance.workbook_sha256); reconciliation.aggregate_filters_applied; else
"Unexplained, report this"), chart-studio.js (graphTotals(company, cycle) -> api('/api/graph?'+
params) with id 'published-reports', industry from dataset(), cycle as end year via
core.graphCycleValue; Map-cached per scope key; fired only when the sheet filters are exactly
company/cycle equals; render `<p id="studio-reconcile">` after :326 with the "Why Cross-reference
differs" link opening the cross-reference tab; scopeText() :1787-1807 appends the not-carried
line from appliedScope; group counter :328 -> "1-N of M groups · totals cover all M"), index.html
(the reconcile paragraph after :237; :99 `<small id="graph-basis-note">`), graph.js (:82 footnote
"Workbook included receipts, net. Same figure as Chart Studio's Published included receipts
basis."), index.html :274 Parameters placeholder "40 per page (verified) · fold after 40
(worksheet); Graph and classic fold at 60". Cross-reference: cross-reference.js (:19-32 add the
19 engine reason keys with the plain-word names from the table Paul approves; :96-97 caption
"Rows with an unresolved company attribution are counted at $0 in every total above; memo,
transfer, earmark and role reviews stay inside Observed original giving until resolved."; :52
metric() prints "Cycles 2022, 2024, 2026" beside every dollar figure). Tests:
mentat/tests/test_chart_studio_contributions.cjs (reconcile: agree, basis reason, tier reason,
sha reason), new test_studio_reconciliation_browser.cjs (Graph fixture + query fixture -> strip
"Agree"; mismatched -> names the reason), test_cross_reference_view.cjs (new label + "Cycles"
inside the money grid). Acceptance: ride steps 15-19; Scope A and Scope B agree to the cent.
Paul rules: the reason names, the caption text, whether worksheet default group limit moves
40 -> 60. RULES block.

REASON NAMES for Paul (cross-reference):
| engine key | proposed label |
|---|---|
| company_attribution_unresolved | Donor not yet matched to a listed company (counted at $0) |
| attribution_unresolved | Attribution not settled (counted at $0) |
| company_attribution_not_accepted | Company match not accepted |
| memo_parent_not_established | Memo entry without a proven parent receipt |
| original_source_of_transfer_unresolved | Transfer whose original donor is unresolved |
| earmark_counterpart_not_unique | Earmark with more than one possible counterpart |
| earmark_destination_ambiguous | Earmark destination ambiguous |
| overlapping_or_cyclic_earmark_links | Earmark links overlap or loop |
| observed_filing_versions_unresolved | Amended filings not reconciled |
| latest_filing_transaction_replacement_missing | Latest filing lacks the replacing transaction |
| latest_filing_manifest_not_corroborated | Latest filing not corroborated by its manifest |
| linked_refunds_exceed_original_gift | Refunds exceed the original gift |
| receipt_date_missing | Receipt date missing |
| excluded_source_metadata_conflict | Source metadata conflict |
| superseded_in_observed_filing_family | Superseded by a later filing |
| same_original_gift_at_conduit_and_destination | Same gift seen at conduit and destination |
| explicit_same_filing_memo_reference | Memo references its own filing |
| explicit_observed_refund | Observed refund |
| linked_refund | Linked refund adjustment |

------------------------------------------------------------------------------------------------

## R4 - Briefing drawer
Covers E4, E3, E6. Reference: v2A (R1 once approved). Rendered as job 3e2bc310-ca9d-4aca-94fd-00708f12219c.

RENDER PROMPT R4:
Same MENTAT Chart Studio builder screen as the reference, but a right-hand drawer 340px wide
titled in serif "Briefing" overlays the Inspector, ivory #f7ede4 with a 1px #e4d9d0 border and a
lilac count chip "3 items". Each item is a white card with a 96px chart thumbnail on the left,
a serif title, and two muted lines: card 1 "Published included receipts by Recipient category" /
"Banking · Cycle 2025-2026 · Bank of America NA" / "Published included receipts · added 22:41";
card 2 "Giving by election cycle" / "Banking · All cycles" / "Published included receipts · added
22:43"; card 3 "Top recipients" / "Banking · Cycle 2025-2026" / "Published included receipts ·
added 22:44". Each card has small text buttons "Move up", "Move down", "Remove". Drawer footer:
a gold #eca91c primary button "Export PowerPoint", secondary outlined buttons "Print briefing",
"Share bundle", "Save view", and a muted note "Every slide carries its scope, basis and source
SHA-256." The sheet toolbar shows "Add to briefing" with a purple badge "3". Everything else
identical to the reference. THEME block. STYLE block. AVOID block.

GATE R4: approve R4 | approve with: <delta> | reject: <reason>

IMPLEMENTATION PROMPTS bound to R4:

E5 saved views (approve from text; no render)
Files: server.py (Console.list_views/get_view/save_view/delete_view over
<data root>\studio\views\<32hex>.json via read_json :73 + atomic_json :216 under Console.lock
:369; validation name 1-80 chars, 1-24 sheets, active int, payload <= 512 KB; routes GET
/api/studio/views[?id=], POST /api/studio/views and /api/studio/views/delete before :1312;
read-only branch before :1292 returning "Saved views are read-only in this preview console; save
from the original console."), chart-studio.js (saveView() with the inline rename pattern
:1201-1225, default name "<sheet> · <dataset>"; openViews() via popup() :475 grouped "This source"
/ "Other sources"; opening a contributions view on another dataset selects it via
selectContributionDataset() :250-256 then commit() the sheets like restore() :84; worksheet views
on a different report listed disabled with reason; one-time migration flag
mentat-chart-studio-migrated-v1 posting readStore() entries as "Recovered · <name> · N sheets"
when the server has none), index.html (menu entries "Save view", "Open view"). Tests: python
tests/test_studio_views.py (save/list/get/delete, limits -> 400, read-only -> 403, files on disk),
Playwright fixture Save then Open restores shelves and active sheet. Acceptance: ride step 30.
Paul rules: read-only refusal (recommended yes), duplicate names allowed, automatic migration.
RULES block.

E4 briefing tray
Files: new chart-briefing.js + chart-briefing.css (allow-list entries in server.py :1240-1269;
index.html includes; console restart once), index.html (toolbar #studio-briefing-add, drawer
#studio-briefing with the verbatim labels of R4), chart-studio.js (one hook:
MentatBriefing.capture(currentChart())), graph.js and charts.js (format entry "Add to
briefing"), server.py (GET /api/studio/briefing, GET /api/studio/briefing/item?id=, POST
add/remove/order; store <data root>\studio\briefing\index.json + <id>.svg; cap 40; SVG > 6 MB
refused client-side "Narrow the view before adding it"; read-only -> 403 and the tray stays in
memory with the notice "not saved in a read-only preview"). Exports: Print briefing (E2 sheet
with page-break per item), HTML bundle (self-contained file with inline SVGs, captions,
provenance table, print CSS), PowerPoint (E3). Tests: mentat/app/tests/chart-briefing.test.js
(pure add/move/remove/cap), new test_studio_briefing_tray_browser.cjs (add two, reorder, remove,
export HTML -> blob has two <svg> and both titles), python endpoint tests. Acceptance: ride steps
27-28, 31. Paul rules: single shared tray per data root for v1; include Graph charts. RULES block.

E3 PowerPoint
Files: mentat/app/vendor/pptxgen.bundle.js (PptxGenJS UMD, MIT; download with PowerShell
System.Net.WebClient from the pinned release, record version + SHA-256 in README and assert the
served hash in tests/test_contribution_http.py), vendor/LICENSE-pptxgenjs.md, server.py allow-list
entry, chart-briefing.js (exportPptx(): lazy same-origin <script> load; LAYOUT_WIDE 16:9; per
item: title 0.5,0.35 12.3x0.7 in 22pt Georgia plum #342649; chart PNG from rasterize at 1.5x
0.5,1.15 12.3x5.0 sizing contain; scope 0.5,6.3 9pt Arial #716a64; source note 0.5,6.8 8pt
"Source: <workbook> · SHA-256 <12> · basis <label> · exported <date> from Mentat Chart Studio";
1pt gold rule above the footer; wordmark MENTAT right-aligned 12pt Georgia plum; speaker notes
with full title, scope, note, provenance, console URL; file mentat-briefing-<date>.pptx via
MentatExport.download). Tests: Playwright loads the bundle, exports a two-item tray, the .cjs
inflates the ZIP central directory and asserts ppt/slides/slide1.xml, slide2.xml,
ppt/notesSlides/notesSlide1.xml exist and contain the title and the SHA string; python: vendor
route 200 + pinned hash + CSP header. Acceptance: ride step 29 (deck opens in PowerPoint on
Paul's machine). Paul rules: slide wording. RULES block.

E6 phone snapshot publish
Files: mentat/tools/pocket/ (move extract_pocket_data.py, build_page.py, selfcheck.py,
negative_control.py, render_harness.js and the page template from the audit packet; template
becomes a full document; .gitignore exception `!mentat/tools/pocket/*.html`; extractor gains
--out-dir, --companies, --cycles), server.py (Console.publish_pocket(data) modelled on
collect_evidence :687-712: job dir <data root>\publish\<id>\job.json, Popen of the extractor
against the console's own port with CREATE_NO_WINDOW, then build_page; GET
/api/publish/pocket?id= status; one job at a time; read-only -> 403; server.app.port set from
options.port), chart-briefing.js ("Share bundle" -> "Publish phone snapshot" with dataset
multi-select, progress, output path, and the note that uploading to the private artifact link is
the coordinator's step). Tests: python validation (dataset ids from the catalog, single job,
read-only 403), build_page marker idempotence, the moved selfcheck/negative_control still guard
the page. Acceptance: ride step 31. Industries-only scope first. RULES block.

------------------------------------------------------------------------------------------------

## Batching, budget, order
Renders: R1, R1b, R2, R3, R4 = 5 x 5.5 = 27.5 credits (spent 2026-09-14); up to 4 delta
re-renders; cap 9 renders / 49.5 credits. Build order after approvals: F0, F1, F6, F2, F3, F4, F5
(Ride 1), then E0, E1, E2, E5, E4, E3, E6 (Ride 2). Commits per lane by explicit path on
codex/mentat-crypto, Paul's go.
