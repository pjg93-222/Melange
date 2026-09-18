# UI clean-up: Graph and Chart Studio

**Lane:** mentat-failings (audits/mentat_failings_20260915), UI pass after S5.
**Date:** 2026-09-17. **Status:** ACCEPTED by Paul 2026-09-17 ("Looks great" on the recommendation). Rulings (Paul, 2026-09-17: "Graph B, Chart Studio A, the C Board can be used for multiple charts together"): R1 Graph B; R2 Chart Studio A (no Show Me popover); R3 party colour only when the payload carries party; R4 sparklines allowed, one request per registered cycle, filled after first paint; R5 Split by next pass; R6 Board NOW, as the second build of this pass after the chrome build is reviewed, contract  v2 first. Build one (chrome) by the Opus architect in progress.
**Roles:** design and reasoning by Fable in the session; build by the Opus architect in one pass; review by Fable inline with reproduction; commit by Paul; console restart by the launcher.

**Brief (Paul, verbatim):** "Go over the Chart Studio and Graph and clean up the UI it looks good, the aim is ease of use, conciseness, symmetry, de-cluttering, and depth of visualization." Follow-up question: "how does it handle multiple charts?" (section 4).

**Mockups:** `UI_CLEANUP_MOCKUPS_2026-09-17.html` beside this file (full-fidelity HTML in the ACU theme: Graph A, Graph B, Chart Studio A, Chart Studio B, Chart Studio C board, plus a "what changes" note). Higgsfield renders are pending: the connected account is the free plan, its only accepted model (`z_image`) failed the first job, and the account with credits needs Paul to re-authorize the connector.

**Correction (2026-09-17, after reading `index.html` 163 to 337):** the first draft listed a "layout picker" among today's toolbar controls and a "Chart variant select". Neither exists. The board picker is a proposal (option C); the Show Me tiles sit at the top of the Inspector's Marks pane and are toggled from the toolbar. The census below is the corrected one.

## 1. Census (console 8806 at ea222fadb, Banking, 2026-09-17)

From `index.html`, `graph.js`, `graph.css`, `chart-studio.js`, `chart-studio.css`, `workspace.css` and screenshots. Control counts are the scout's and are re-measured by the build's before/after receipt.

**Graph** (`#view-graph`, index.html lines 79 to 161):
- Header title plus a sentence that restates the filter values already shown in the selects.
- Filter row: Industry, Company, Employee level, Election cycle, Giving mode, Reset, and a global "Rows per chart" number input that governs every panel at once.
- Tabs: Overview, Recipients, Candidates, Companies; the Candidate view select appears once a report is chosen (S5 ruling A(ii)).
- Three KPI figures with unequal chrome (net giving; direct to candidates; recipient organizations; the two parts differ from the net by the candidate-category receipts with no unique authorized candidate link, today explained in a helper sentence).
- Panels: recipient-type bars, a text-only candidates list, a company table, an employee-level table. Each has its own header layout, its own helper sentence, and its own export row of six controls (target select, format select, four buttons).
- About 48 visible controls on the Overview.

**Chart Studio** (`#view-chart-studio`, index.html lines 163 to 337):
- Header row: title, scope chip and note, "Data source" button, "Company overview" toggle, segmented "Builder | Canvas only", "Inspector" toggle with a count badge.
- Toolbar row: Undo, Redo, Swap, Sort ascending, Sort descending, Show mark labels, Fit select, Clear, Duplicate sheet, Export menu (PNG, SVG, CSV, Copy image, Print chart, Add to briefing, Save view, Open view), an "Add to briefing" button with a badge, "Show Me" toggle, "Classic builder".
- Middle column: three shelves (Columns, Rows, Filters), then an h2 that reads "Chart Studio" until a chart is drawn, a reconciliation line, a note line, then the canvas and the group pager.
- Data pane (260 px): a Data source disclosure with mode, report, basis, state-view selects and a refresh button; field search; a "Fields from" select; Dimensions; Measures.
- Inspector (300 px): tabs Marks, Analytics, Filters. The Marks pane starts with the Show Me tiles, then Mark type, the five properties, a note, map layers, Pages with a pager, Parameters (row range, row limit, group limit, bin width, two checkboxes). Two vertical scrollbars because the pane's 74vh cap sits inside a scrolling column.
- The Fit select renders full width (layout bug). Show Me is reachable twice (toolbar toggle and the pane section). "Add to briefing" appears twice (menu item and button).
- Multiple charts today: one sheet at a time on the canvas; sheet tabs and "+ New sheet" at the bottom; "Duplicate sheet"; the Pages shelf steps one chart through a dimension's members; the Company overview is a fixed grid of charts for one company; the Briefing collects charts as slides (PowerPoint, print, share bundle). No two sheets are ever visible together.
- About 87 visible controls.

## 2. Critique against the five aims

- **Ease of use.** Graph: opening the scope in Chart Studio is one button among many. Chart Studio: the chart starts below the fold at 1440 by 900 because the header, toolbar, shelves, title and two status lines precede it.
- **Conciseness.** Graph: the scope sentence repeats the selects; the export row repeats per panel. Chart Studio: two entry points for briefing, two for Show Me, and Save/Open view buried in Export.
- **Symmetry.** Graph: four panel headers, four layouts. Chart Studio: side columns 260 and 300 wide with different padding and label styles.
- **De-cluttering.** Helper sentences and status lines carry facts that belong in tooltips, footers and chips.
- **Depth of visualization.** No share of scope on any bar, no party signal on candidates, no across-cycle shape, no hover detail; candidates are a list, not a chart; one chart at a time in the studio.

## 3. Plan

### Graph, option A (concise)
1. One header line: title, the filter row (Industry, Company, Employee level, Election cycle, Giving), Reset as a text button, then at the right the gold primary "Open in Chart Studio" and an overflow menu holding every other header action the census lists.
2. The scope sentence goes; the global "Rows per chart" input goes; each panel gets its own "Top N" select (default 10) that sets that panel's request limit.
3. Underline tabs with one caption at the right (the group count the API already returns and "local data").
4. KPI strip: three equal tiles; the two part figures carry a share bar and "x% of net giving"; the excluded-receipts sentence becomes a tooltip on the candidates panel footer.
5. Every panel shares one chrome: title left; at the right the panel's measure select if it has one, "Top N", "View all"; body; footer "Showing n of N", an information mark for the panel's note, "Export" as one menu (targets and formats inside it).
6. Candidates become a bar chart in the same style as recipient types. Every bar carries its value and its share of the KPI the panel belongs to (recipient types over net giving; candidates over direct to candidates).
7. One slim export line for the whole view: Details and methodology, Copy image, Add to briefing, Export.

### Graph, option B (A plus depth)
8. The Overview becomes a two by two bento: recipient types, candidates, company comparison, employee level, each in the shared chrome, so the four analyses sit on one screen; the tabs still open each in full.
9. Party colour dot on each candidate row, only if the contributions payload carries party (R3).
10. Sparkline per company across the registered cycles (R4: needs per-cycle totals, one request per cycle or a per-cycle field in the response).
11. Employee level as one stacked bar with a legend, with the personal-versus-corporate note in the panel subtitle.
12. Hover detail on every bar: name, value, share, and for companies the per-cycle figures.

### Chart Studio, option A (concise)
1. Row one: title, scope chips (industry, cycle, dataset), "Change data" (opens the Data source disclosure), then at the right one segmented control "Builder | Company overview | Canvas" (today's toggle and two-way segment merged) and the Inspector toggle.
2. Row two, one toolbar in groups: Undo, Redo; Swap, Sort, Sort, Labels; Fit at intrinsic width; Clear, Duplicate; a spacer; gold "Show Me"; "Export" (images, data, copy, print); "Views" (Save view, Open view); "Add to briefing" once. Classic builder moves under Export.
3. Columns 280, flexible, 280 with one padding and one section-label style on both sides.
4. Data pane: source as chips with a ready mark (the selects stay inside the disclosure, closed by default once a report is chosen), field search, Dimensions, Measures.
5. Canvas: the shelves, an editable title sentence ("Selected amount by Company") with the scope as a subtitle, the chart, one footer line that merges the reconciliation and status lines. The h2 never reads "Chart Studio".
6. Inspector: tabs Marks, Analytics, Filters; Mark type and the five properties first; then collapsed disclosures "Show Me" (the tiles move below the properties and open from the toolbar button), "Map layers" when a map is drawn, "Pages", "Parameters". The pane is the scroll container, so one scrollbar.
7. The Fit select width bug is fixed by the toolbar grouping (no full-width rule applies inside the group).

### Chart Studio, option B (A plus depth)
8. Show Me opens as a popover anchored to its toolbar button, with the tiles and one suggestion line derived from the shelves.
9. A "Split by" shelf renders small multiples: one chart per member of the split dimension, shared scale, each with its total in its header; the sheet keeps one `split` field (R5 decides whether saved views persist it).
10. Hover detail on every mark: exact figure, share of its group, share of the split member.

## 4. Multiple charts

**Today.** A view is a list of sheets; one sheet is on the canvas at a time (`chart-studio.js` renders the active sheet into the single `#studio-canvas` with module-level result state). Ways to see more than one chart: switch sheet tabs; step the Pages shelf through a dimension; open the Company overview grid; or collect charts into the Briefing and export slides. Saved views persist `sheets[]` and the active index.

**Option C, board (mockup "Chart Studio C").** Canvas mode becomes a board of 1, 2 or 4 tiles chosen from a "Board" control in the toolbar. Each tile shows one sheet, picked from a select in the tile header; the selected tile has the outline and is what the Inspector, Show Me, Export and "Add to briefing" act on; "Views" gains "Add board to briefing" (one slide per tile). Each tile keeps its title sentence, scope subtitle and reconciliation footer, so every figure keeps its denominator. Builder mode is unchanged (one sheet, shelves, Inspector).

**Cost.** The render path in `chart-studio.js` (about lines 550 to 598) keeps one result, one title, one request key and one geometry cache for the active sheet. A board needs that state per tile and one contribution query per tile (2 or 4 requests on refresh, cached by request key as today). Saved views gain an optional top-level `board` object `{tiles, slots}` (tiles 1, 2 or 4; slots exactly tiles entries, each a sheet index or null, no repeats), written only when a 2- or 4-tile board was chosen so v1 views stay byte-identical. `studio_api.json` moves to v2 (additive; three examples, six negative controls). Console.save_view must add `board` to its record whitelist (today an unknown top-level key is silently dropped, see v1 negative control 5) and reject a malformed board with 400; chart-studio-core.js gains `normalizeBoard`. This is the one server.py hunk of the pass; it is cut hunk-exact so the collector-slowdown session's server.py work is untouched. Tests: the studio browser passes keep working in Builder mode; a new board step asserts two tiles render two different titles and two reconciliation lines.

**Recommendation.** Option B's "Split by" answers the common case (the same chart across cycles or companies) with one query and no state refactor. The board answers "two different charts side by side". If Paul wants the board, it is its own pass after this one; if he wants it now, this pass becomes two Opus builds (chrome first, board second) with a review between.

## 5. What does not change
Data, routes, contracts (unless R5 or R6), `scope.js` and the URL vocabulary (S5), the industry parameter (S4), ACU theme tokens and fonts, the stale-build banner, the Cross-reference view, the `#run-controls` block and `app.js` and `server.py` (the collector-slowdown session owns those edits), `graph_data.py` and `fec_beneficiary.R` (S5 ruling B).

## 6. Files owned by this pass
`mentat/app/index.html` (only `#view-graph` and `#view-chart-studio`), `graph.js`, `graph.css`, `chart-studio.js`, `chart-studio.css`, `workspace.css` (shared layout rules `.workspace`, `.graph-panels`, `.studio-grid`); `chart-studio-core.js` only for option B's split or option C's board. Tests whose selectors the restructure touches: `tests/test_console_browser.cjs`, `test_studio_industry_browser.cjs`, `test_navigation_scope_browser.cjs`, `test_contributor_detail_header.cjs`. New: `tests/test_ui_cleanup_browser.cjs`.

## 7. Acceptance
- Screenshot receipts before and after at 1440 by 900 and 1280 by 800 for both views; a control-count receipt per view (buttons, selects, inputs, links with a button role) before and after.
- Graph Overview shows the filter row, tabs, KPI strip and its panels (two in A, four in B) without scrolling at 1440 by 900.
- Chart Studio shows the top of the chart without scrolling at 1440 by 900; the Inspector has one vertical scrollbar; the Fit select is at most 160 px wide; "Add to briefing" appears once; Show Me appears once.
- Percent labels use the panel's KPI as denominator and the visible rows sum within rounding.
- Every existing browser test green; node and python suites unchanged; `test_navigation_scope_browser.cjs` 13 of 13 (URL scope unchanged).
- No new localStorage or sessionStorage keys (D-039).
- Option C only: two tiles render two different titles and two reconciliation lines; a saved view with `board` reopens with the same tiles; a saved view without `board` opens as one sheet.

## 8. Rulings for Paul
- **R1** Graph: A or B.
- **R2** Chart Studio: A or B.
- **R3** Party colour: only when the payload carries party; omit silently otherwise.
- **R4** Sparklines: allow one request per registered cycle for the company panel, or defer.
- **R5** Persist `split` in saved views (contract `studio_api.json` v2, additive) or keep it session-only.
- **R6** Board (option C): now, as a second build in this pass; next pass; or not at all.

**Recommendation:** Graph B; Chart Studio A plus the Show Me popover from B; "Split by" and the board as the next pass. Graph B's depth comes from data already in the payload except sparklines; the split shelf and the board both touch the core render path and the saved-view contract and deserve their own review.

## 9. Method
Contract before code where a contract moves (R5, R6). Build prompt names the write path (python scripts through Bash; Edit and Write refuse the Mentat tree from this worktree). One Opus build; Fable review reproducing each finding against the real page; sweep in parallel; patch cut once as bytes after `git log -1` (DE-025); Paul commits; launcher restarts 8806.

## 10. Build result (2026-09-17)

Built: Graph option A plus B (items 1 to 12) and Chart Studio option A (items 13 to 18).
NOT built and deferred to a second pass: the Show Me popover (ruled out; the toolbar button
opens the Inspector disclosure instead), `Split by` small multiples, and the Board.

| Measure | Before | After |
| --- | --- | --- |
| Chart Studio visible controls | 66 | 47 |
| Chart Studio canvas top at 1440x900 | 787px | 613px |
| Chart Studio canvas top at 1280x800 | 805px | 645px |
| Graph Overview visible controls | 23 | 32 |
| Fit select width | full column | 119px |
| Inspector scroll containers | 2 | 1 |

Graph's control count rises because option B puts four panels on the Overview where there
were two, each with its own Top N and Export menu. Conciseness was the Chart Studio aim;
Graph traded control count for all four analyses on one screen, which is what option B is.

Tests: node unit suite 178/178; `tests/test_ui_cleanup_browser.cjs` 12/12 (new, 620 lines);
`test_navigation_scope_browser.cjs` green, so the S5 URL vocabulary is unchanged. Receipts in
`receipts/UI1_*`: baseline, before and after screenshots at 1440x900 and 1280x800, control
counts, foreign-lane state, test output. The `UI1_after_*` screenshots and the after counts were
taken before the last three fixes (an em-dash entity and two escape sequences made literal, and
test-only edits); none of those change layout, so the images are representative but not byte-current.

Patch: `patches/UI1_graph_studio_cleanup.patch`, cut hunk-exact as bytes (DE-025), proven with
`git apply --cached --check` against HEAD a9ed5c236. 12 files, +1810/-138. Two files are shared
with the PAC evidence lane and carry only this lane's hunks: `index.html` 6 of 7 hunks (the
`#view-evidence` hunk is theirs) and `workspace.css` 3 of 7 (the four evidence hunks are theirs).
