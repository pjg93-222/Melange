# Build 03 (Chart Studio, board S1) handoff - 2026-09-22/23

Chart Studio's Builder rebuilt to board S1 (M8-A with B12's compare chip, "Match Graph scope" and the Inspector collapse), with "+ Compare with..." built on build 02's `window.MentatCompareMenu`. Nothing is committed. Paul reviews `DIFFERENCES.md` and the `03_*.png` side-by-sides, then commits. `build03.patch` holds exactly build 03's changes on top of the tree (cut from this lane's byte pre-copies; `git -c core.autocrlf=false apply -R --check` exit 0); `mentat/app/index.html` is not in it - regenerate with `python mentat/tools/render_console.py --write` after applying.

**No restart needed for the markup** (`/` renders the templates live) and no new static asset (STATIC_ASSETS unchanged). chart-studio.js, contribution-plot.js, ui-state.js, chart-studio-core.js, chart-studio.css and workspace-polish.css are served from disk: reload with the cache bypassed.

## How this build ran

- Session 5ab381bb, one Opus architect, port 8817 read-only (stopped at the end). Other builders (07 loading, 08 collection) were active in the tree; they re-rendered index.html twice while this ran, carrying this build's template too (index.html is derived).
- Every edit went through `scratchpad\mentat\build03\hk.py` (bytes, anchored single-occurrence hunks, sha256-guarded against `ledger.json`, each replaced line keeps its own ending). Pre-copies: `scratchpad\mentat\build03\pre\`. No file changed under this lane between its reads and writes; line endings of unchanged lines are untouched (LF counts of the CRLF files unchanged).
- workspace-polish.css: build 01's interim D1 rule (the 5-line comment + `@media(min-width:761px){#view-chart-studio .studio-toolbar{justify-content:flex-end}}`) was replaced exactly by the build-03 block (LF, comment header). test_workspace_polish_browser.cjs: only Chart Studio assertions were touched.
- Paul's 09-22 Codex edits (evidence_geo.py, evidence.js, workspace.css, their tests, graph_data.py hunks) were not touched. graph.js / graph.css (build 02) were read, not edited.

## Files (final sha256 after the final fix round, line endings kept)

| File | +/- | sha256 | Endings |
|---|---|---|---|
| mentat/app/chart-studio.js | +540 -24 | 0ec4b385ef04703a8caaaa2eb20228e34f037383b81e0a942296efab332ce217 | 3910 CRLF / 14 LF |
| mentat/app/workspace-polish.css | +266 -5 | 51c9f2064987187904df8674f5d705d995e44a29bb9a0d870694222adcb65cfe | 220 CRLF / 413 LF |
| mentat/app/templates/view_chart_studio.html | +50 -42 | c3ac9f811575c9bd2ac72ca1e15f97ce24e0de360b0e85d98aaa69ab5c2837ee | 189 CRLF / 11 LF |
| mentat/app/contribution-plot.js | +35 -9 | 777c4af4bf82c29deb53a63017e2707fbf4085386efa9125bdb36c43056db194 | 132 CRLF / 19 LF |
| mentat/app/ui-state.js | +10 -1 | a0782725221c5dadc4a932dedc47fd431fd33a724e1ffde7ff70bad1a6a0c860 | LF |
| mentat/app/chart-studio.css | +9 | a9407400db91a088df681c247063943db788fada46572164e83be091513e54c1 | 820 CRLF / 24 LF |
| mentat/app/chart-studio-core.js | +3 -1 | 8a51f133b665e7fe9352dbf006b11a26f0b358c9a6d0c712166003e3d40df2f9 | 1157 CRLF / 18 LF |
| mentat/app/tests/chart-studio-contributions-sort.test.js | +2 | bc846b8a7ca88d6250c269af931b89f117ba429653a9006d867ffe631f0a1de3 | LF |
| mentat/tests/test_studio_reconciliation_browser.cjs | +36 -4 | 719a9e526accbfe617165af4c5c26e0df01bde9472c906c239c47fcc646d8c43 | LF |
| mentat/tests/test_workspace_polish_browser.cjs | +12 -1 | 1038af34fcdfaecb085038e57f175d36d2641417fbaa3f4919227d414db0db6c | 147 CRLF / 36 LF |
| mentat/tests/test_original_studio_contributions_browser.cjs | +10 | 482ce8deaececae511a266b8309c468beec7856ed1c70c8481fe4ae4c724d66c | LF |
| mentat/tests/test_studio_wording.cjs | +9 -5 | 5f2ac9b04ac5a0b082a51f5723746f8a06d3eee63cfae9185ef41d2827ec1634 | LF |
| mentat/tests/test_studio_data_source_browser.cjs | +6 -1 | e82705cf336bb48ca57c5a8af6626d89f2222d0c7775886e5352632a2117cb52 | LF |
| mentat/tests/test_studio_board_browser.cjs | +2 -2 | 5ccb3dfe44dd8bf26555b12954998215d6611f6480cf553c05ef300835adbb2c | LF |
| mentat/tests/test_studio_industry_browser.cjs | +2 -1 | 32e0da8ed60bde75d41b8fbe95a948bb4b0d1780c65294efd55e213e622fdd76 | LF |
| mentat/tests/test_studio_worksheet_guard_browser.cjs | +4 | 35d3277c4f56655c81371b3942b488412ff9ae46b1c0f6b92d96cc7a8dcb9ed1 | LF |
| mentat/tests/test_ui_cleanup_browser.cjs | +2 | a0797aa63824d84b92eac191a8ef32a0b7a4065463bd52a2fd60edb928da2344 | LF |
| mentat/tests/test_studio_ride1_browser.cjs | +5 -2 | 9838453ce51293d5b9a2652d3c7bd69f1bce7c3918b08b3dafc6e99448c55808 | LF |
| mentat/app/index.html (generated, not in the patch) | re-rendered | render --check: up to date | LF |

Not changed (owned, not needed): chart-studio-contributions.js, chart-briefing.js, worksheet-comparison.js, test_console_templates.py (its 10 tests pass unchanged). Git-ignored proof files: `measurements.json`, `measurements_1600x900.json` (`*.json`), `status_*`/`processes_*` snapshots (`*.txt`). Not ignored: the PNGs, `capture03.cjs`, `sbs03.py`, `build03.patch`, the two .md files.

## What was built (prompt 03 items 1-9)

1. Header row beside the page title (the h1 floats at >=1100px; S1's serif 40px): source chip `#studio-scope-change` = "Banking · All cycles · Published included receipts ▾" opening `#studio-source-popover` with every source control (ids kept; the disclosure stays open, its summary is the popover's first line; Escape and a click outside close it); `#studio-compare-add` "+ Compare with..." (one line); `#studio-ready` "● Ready" (the source summary's own state); `.segmented` Builder | Company overview | Canvas. `#studio-progress` (prepare + Cancel) moved to the header so it shows with the popover closed.
2. Compare: see "Contracts" below.
3. Toolbar, one row: Undo, Redo | Swap, Sort ▾ (`#studio-sort` menu: `#studio-sort-asc`, `#studio-sort-desc`, new `#studio-sort-none`), Labels, "Fit: Standard ▾" | Clear, Duplicate | right: gold Show Me (the only gold), Compare worksheets, Export ▾, Views ▾, Add to briefing. Board size buttons Canvas-only.
4. Fields: "Search N fields" (N = the catalog's field count), compact "From: All related tables ▾", headed lists with glyphs and in-use dots.
5. Shelves with "Chart: Bar ▾" (`#studio-mark`) at the end of Columns; `#studio-aggregation` hidden in place.
6. Canvas: serif 28 title, muted subtitle, three figures, bars with value labels at the ends (drawn at the canvas's width; redrawn from the held answer on a width change).
7. Note line (`#studio-reconcile` kept): lilac, "This sheet covers all cycles. Graph shows 2025-2026.", `#studio-match-graph`, `#studio-reconcile-why` opening `#studio-reconcile-detail` (the old sentence, "Why Cross-reference differs", and the caveat paragraph that was under the chart), and "Groups 1-10 of 10 · View source records" at the right. No red. Board tiles keep their own (unchanged) strip.
8. Inspector: serif head, `#studio-inspector-collapse` "Collapse ›" -> 56px rail `#studio-inspector-rail` (`#studio-rail-marks/-analytics/-filters`), remembered through `MentatState.remember/recall` (ui-state.js, try/catch), key `mentat-chart-studio-inspector-collapsed`. The narrow-screen drawer (`#studio-inspector-toggle`/`-close`) is unchanged.
9. Sheet tabs and `#studio-status` in one bar.

## Contracts exposed / changed

- **Compare (Chart Studio)**: per sheet, in the tab, never in the URL. Kinds industry | cycle | company from `MentatCompareMenu.open(anchor, {kinds, valuesFor, exclude, onPick})`; pills `MentatCompareMenu.pills(#studio-compare-pills, {kind, values, max: 3, onRemove, onAdd})`; `.compare-clear` "Clear" (aria-label "Clear comparison"). Scope 1 = the sheet's report / its one cycle (else the newest) / its one company (else its largest drawn company). Data: cycle and company = ONE POST /api/contributions/query with `{field, op:'in', value:[...]}` (field added to the dimensions when absent); industry = one query per report; merged under a browser-only `scope` series (never sent). Refusals are explicit: non-bar/line/area/circle/table marks, a period analysis, or a Colour field already on the sheet.
- **contribution-plot.js** (all opt-in; other callers unchanged, test_contribution_plot and the readability suite pass): `spec.colorMap` (value -> colour, legend order), `spec.labelDimensions` (one category label per cluster), `spec.barPitch`, `spec.niceTicks`, `spec.panelTitles === false`, `spec.width` + `spec.barLeft` (bars drawn one unit per CSS px, marked `svg[data-native]`, value labels at the bar ends in whole dollars).
- **ui-state.js**: `MentatState.recall(key)` -> string|null, `MentatState.remember(key, value)` -> boolean; both swallow storage errors.
- **chart-studio-core.js**: `createSheet()` now starts `showLabels: true` (S1 draws values). Saved sheets keep their stored value.
- **Carried Graph scope**: giving type is carried as `funding_source` (personal -> employee_original, corporate -> corporate_original, Graph's own sparkline mapping) by "Open in Chart Studio" and by Match Graph scope; GRAPH_NOT_CARRIED lost its "Giving type: not in verified data" row (evidence: contribution_data.py:57 and :375, graph.js:1382-1383). `reconcileScope()` accepts one funding_source value.
- **Status / counter wording**: `#studio-group-count` "Groups 1–10 of 10" (title "Totals cover all 10 groups"); `#studio-status` "... · reconciles to the workbook" (query count in its title).

## Re-homed assertions (one by one, each commented "Build 03")

- test_studio_reconciliation_browser.cjs: the explanation is read from `#studio-reconcile-detail`; the agreeing note is asserted hidden; group counter `^Groups 1–1 of 1$` + title; basis sentence from the detail and the note "Same scope as Graph; the totals differ by $". Added: the employee-level note, Match hidden, no `.studio-reconcile-differ`; a Match Graph scope round trip (note text, click, the query's filters become `[cycle eq 2023-2024]`, Match hides).
- test_studio_wording.cjs: the header test now asserts the source chip markup and the popover wrapping `#studio-source-details`; the counter test asserts the new template literals.
- test_studio_data_source_browser.cjs: the chip's `aria-controls` + inner `#studio-scope-chip` instead of the text "Change data"; the popover is closed before a field pill is clicked.
- test_studio_industry_browser.cjs, test_studio_worksheet_guard_browser.cjs, test_original_studio_contributions_browser.cjs, test_ui_cleanup_browser.cjs, test_workspace_polish_browser.cjs: open the source popover (the chip) before touching a source control, close it before clicking under it; Sort items via the Sort menu; the Labels toggle clicked twice (new default on); polish: the chip opens the popover (not the fields drawer), Escape returns focus to the chip, and Chart Studio's title is asserted 40px while the rest of the shell must still match the other views.
- test_studio_ride1_browser.cjs: the carried-scope test reads the explanation from `#studio-reconcile-detail` and asserts the agreeing note hidden.
- test_studio_board_browser.cjs: the two counter regexes read "Groups 1–3 ..." (the old `^1.{1,3}3 ` wait would have passed vacuously).
- chart-studio-contributions-sort.test.js: "off" sets `showLabels = false` explicitly.

## Suites

Runner: `scratchpad\mentat\build03\run_suites.py` (logs in `logs\before__*`, `logs\final__*`). Before = unmodified bytes (run 22:46-23:00 on 09-22, before any code edit; the template edit landed mid-run but no suite reads the template, and index.html was unchanged then). After = the `final` run (00:05-00:23 on 09-23, right after `render_console.py --write`), plus the single reruns noted.

| Suite | Before | After |
|---|---|---|
| render_console --check | OK | OK (and again at the end: up to date) |
| test_console_templates.py | 10 OK | 10 OK |
| chart-studio-core.test.js | 100/100 | 100/100 |
| chart-briefing / contributions-sort / studio-contract / studio-worksheet-sheet / worksheet-comparison / reconcile-cycle / compare-menu | 8 / 7 / 28 / 3 / 3 / 7 / 13, all pass | same counts, all pass |
| test_studio_wording / contribution_plot / chart_studio_contributions / contribution_studio / chart_math | 10 / 12 / 14 / 9 / 20, all pass | same counts, all pass |
| test_studio_board_browser | FAIL 3/19 (step 1: toolbar two rows, 91px) | 19/19 (the full run once showed step 11 red under load; rerun alone 19/19) |
| test_studio_reconciliation_browser | PASS | PASS (with the new Match Graph scope assertions) |
| test_studio_click_to_add / data_source / industry | PASS / PASS / 10/10 | PASS / PASS / 10/10 |
| test_workspace_polish_browser | FAIL at the xref `<details>` step (build 05's view) | FAIL at the same xref step (line 153 now); every Chart Studio check before it passes, incl. 1168/900/390px |
| test_studio_canvas_only / strip_removed | PASS / 6/6 | PASS / 6/6 |
| test_studio_ride1_browser | 1 pass, 1 FAIL (line 181, drawer vs toolbar) | 2/2 (rerun after the re-home; the full run's one red was the note-line assertion now re-homed) |
| test_studio_briefing_tray / copy_print / inspection_regression / temporal_regression | PASS x4 | PASS x4 |
| test_studio_worksheet_guard_browser | 2 pass, 1 FAIL ("a fresh load ... arms it again") | 2 pass, 1 FAIL, same assertion (pre-existing; rerun alone twice) |
| test_worksheet_comparison / contribution_studio_state / chart_builder / plot_readability / contribution_charts / contribution_export / contribution_studio_map | PASS x7 | PASS x7 |
| test_original_studio_contributions_browser | FAIL at the map step (verified on the pre-build bytes in a scratch copy: line 139) | FAIL at the same map step (line 147 after the re-home lines) |
| test_ui_cleanup_browser | PASS (build 02's run on these Chart Studio bytes, 12/12) | 12/12 |

No suite is red because of this build. Pre-existing reds: workspace_polish (xref, build 05), worksheet_guard (guard re-arm), original_studio_contributions (map step). Turned green: studio_board, studio_ride1, and Graph-independent Chart Studio chrome at 1440.

## Open items

1. DIFFERENCES O1 (bar colour token), O2 (label truncation with Arial), O4-O7, and O6 (giving-type mapping width) are Paul's calls.
2. The three pre-existing reds above belong to other lanes/older code (xref: build 05; guard re-arm and the map step predate this build).
3. index.html: other builders re-rendered it while this ran; `render_console.py --check` is up to date at the end (89,887 bytes).
4. For the single-writer files: build 03 now holds workspace-polish.css and test_workspace_polish_browser.cjs; the D1 interim rule is gone (replaced by the build-03 block).

## Final fix round (review 03, 2026-09-23)

Same lane rules: every edit through `scratchpad\mentat\build03\hk.py` (sha-guarded against `ledger.json`, bytes only, each line keeps its ending; scripts `e70_final_css.py`, `e71_final_js.py`, `e72_final_css2.py`, `e73_final_css3.py`), one Edit-tool edit bracketed by `hk.py pre/post` (test_studio_reconciliation_browser.cjs, LF kept). All owned files were still at their HANDOFF sha before the first edit. Template untouched, so index.html was not re-rendered (`render_console.py --check`: up to date, 92,631 bytes). Own console 8817 read-only, stopped at the end; 8806 not touched. `build03.patch` re-cut (sha256 077b7548..., 153,115 bytes; `git -c core.autocrlf=false apply -R --check` exit 0). Proof re-captured (all states, both sizes, plus `compare_company` and `new_sheet`); DIFFERENCES section E has the numbers.

- R03-1 (major) -> FIXED. workspace-polish.css: `.studio-compare{flex:0 1 auto;min-width:0}`, its pills/note shrink, other children `flex:none`; `.scope-pill` max 150px (ellipsis from build 02's `.scope-pill-text`); `.studio-ready{flex:none}`; the source anchor gives way first (`flex:0 4 auto; min-width:130px`); header `min-height:56px` instead of `height:56px`. `flex-wrap:nowrap` KEPT at >=1300px on purpose (wrapping would push the viewport-tied panes down a row); 1100-1299 still wraps. Evidence: two and three company pills, `elementFromPoint` at Clear = `studio-compare-clear` at 1440 and 1920.
- R03-2 (major) -> FIXED. With the note hidden, `.studio-foot` becomes one flex row: the caveat (2 lines max, 12px, full text in `#studio-note`'s title, set in renderContributionView's finally) on the left, the counter on the right. After Match at 1440: canvas 357/357 (was 350/296), axis in view.
- R03-3 (major) -> FIXED. Chip is `display:block` with a 28px line box, so the ellipsis applies; the 250px cap at 1100-1499 removed. 1440: 323 = 323, full S1 text.
- R03-4 (minor) -> FIXED. `openCompare` (now async, guarded by a token) adds `compareBase(kind)` to `exclude` for cycle and company. Menus: cycles 2021-2022, 2023-2024; companies from Bank of America NA.
- R03-5 (minor) -> FIXED. `labelDimensions: plotted.length ? plotted : ['scope']`; title "... by Company" (or "by Industry").
- R03-6 (minor) -> FIXED. Escape listener on `#studio-reconcile` (acts only while the detail is open); new assertion in test_studio_reconciliation_browser.cjs.
- R03-7 (minor) -> FIXED. `#studio-filters{align-content:center;margin:3px 0}`; all shelf drops `align-content:center` (the empty sheet's Columns/Rows too). Filters 544-974 = Columns 544-974.
- R03-8 (minor) -> FIXED. contribution-plot.js: the end value is always drawn; the last round tick is dropped when within 56px. test_contribution_plot 12/12.
- R03-9 (minor) -> FIXED. Two/three reports: "Groups 10 · 10" (per-industry ranges in the title); note line 40px, sentence on one line.
- R03-10 (minor) -> FIXED. Error path clears title, subtitle, figures, counter and status; the no-measure guidance is the muted subtitle and never the red box (other errors keep the red box). New sheet: redText [], no Sheet 1 figures.
- Extra (cheap, found here): at 1100-1499 the canvas card's bottom padding is 10px so the default 1440 chart (350px) fits its region with the two-line note (was 350/344, a 6px scroll).

Suites after the fix round (`logs\fixround__*` and `logs\fixround_rerun__*`, 09-23, run after the proof re-capture on the final bytes):

| Suite | Result |
|---|---|
| render_console --check | OK (up to date) |
| test_console_templates.py | 10 OK |
| node unit: chart-studio-core / chart-briefing / contributions-sort / studio-contract / studio-worksheet-sheet / worksheet-comparison / reconcile-cycle / compare-menu | 100 / 8 / 7 / 28 / 3 / 3 / 7 / 13, all pass |
| node: test_studio_wording / contribution_plot / chart_studio_contributions / contribution_studio / chart_math | 10 / 12 / 14 / 9 / 20, all pass |
| test_studio_board_browser | full run 18/19 (step 11: its `until(/of 8/)` is already true on the stale "1–8 of 8" label before the 3-per-page query lands, the load flake the first round saw); rerun alone 19/19 |
| test_studio_reconciliation_browser (with the R03-6 assertion) / click_to_add / data_source / industry | PASS / PASS / PASS / 10/10 |
| test_workspace_polish_browser | FAIL at line 153, the xref `<details>` step (build 05's view), as before; every Chart Studio check before it passes |
| canvas_only / strip_removed / ride1 / briefing_tray / copy_print / inspection_regression / temporal_regression | PASS / 6/6 / PASS / PASS / PASS / PASS / PASS |
| test_studio_worksheet_guard_browser | 2 pass, 1 FAIL, the same pre-existing "a fresh load ... arms it again" |
| worksheet_comparison / contribution_studio_state / chart_builder / plot_readability / contribution_charts / contribution_export / contribution_studio_map | PASS x7 |
| test_original_studio_contributions_browser | FAIL at the same pre-existing map step (line 147) |
| test_ui_cleanup_browser | 12/12 |

Open after this round: DIFFERENCES O1, O2, O4-O8 (O8: the new-sheet click scrolled the 962px page 62px in the capture run; not changed). Pre-existing reds unchanged: workspace_polish (xref, build 05), worksheet_guard (guard re-arm), original_studio_contributions (map step), plus the studio_board step-11 load flake (a test-side race, not touched).
