# Build prompt 03 · Chart Studio builder (S1)

**Builder:** one Opus architect or Codex agent, alone in the tree, after 01 and 02 have landed (this build reuses 02's compare menu). **Read first:** `prompts\00_README.md`.

## Visual spec (binding)

- `boards\S1_chart_studio.webp`: Builder mode, final.
- Context only: `boards\src_M8A_chart_studio_tidy.webp` (the base Paul liked) and `boards\src_B12_chart_studio_quiet.webp` (source of the compare chip, "Match Graph scope" and the Inspector collapse).

**Don't copy:** the compare chip wrapping onto two lines (it is one line: "+ Compare with..."); "U.S Bank NA"; every amount.

## What exists today (verified 2026-09-22)

Template `mentat/app/templates/view_chart_studio.html` (185 lines); logic in `mentat/app/chart-studio.js`, `chart-studio-core.js`, `chart-studio-contributions.js`, `chart-briefing.js`; styles in `chart-studio.css`.

- Modes: `#studio-view-builder` ("Builder"), `#studio-overview-toggle` ("Company overview"), `#studio-view-canvas` ("Canvas"); `setViewMode()` at `chart-studio.js:3041`.
- Source controls: `#studio-source-mode` (Data source), `#studio-dataset` (Report), `#studio-basis` (Accounting basis), `#studio-destination` (State location view), `#studio-refresh-data` ("Refresh verified data"), `#studio-rescan` ("Rescan columns").
- Toolbar (template lines 15-29, built by `renderToolbar()` at `chart-studio.js:2287`): `#studio-undo`, `#studio-redo`, `#studio-swap`, `#studio-sort-asc`, `#studio-sort-desc`, `#studio-labels` ("Show mark labels"), `#studio-fit`, `#studio-clear`, `#studio-duplicate`, `#studio-board-1/2/4`, `#studio-showme-toggle` ("Show Me"), `#studio-compare-sheets` ("Compare worksheets"), `#studio-download` (Export), `#studio-views` (Views), `#studio-briefing-add` ("Add to briefing").
- Fields: `#studio-search`, `#studio-field-table` ("Fields from"), `#studio-dimensions`, `#studio-measures`; `renderFields()` at `chart-studio.js:1149`.
- Shelves: `#studio-columns`, `#studio-rows`, `#studio-filters`; canvas `#studio-canvas`; note area `#studio-note`.
- Reconciliation box `#studio-reconcile`: text built at `chart-studio.js:2982` ("They differ by ... because ..."); red from `.studio-reconcile-differ` at `chart-studio.css:417`.
- Inspector: tabs `#studio-tab-marks`, `-analytics`, `-filters`; panes `#studio-pane-*`; drop zones `#studio-color`, `#studio-size`, `#studio-label`, `#studio-detail`, `#studio-tooltip`; sections `#studio-showme-details`, `#studio-pages-details`, `#studio-params-details`; `setInspectorTab()` 3048, `syncInspector()` 3283.
- Sheets `#studio-sheet-tabs`, `#studio-new-sheet`; status `#studio-status`.
- Worksheet comparison: `mentat/app/worksheet-comparison.js` (new, untracked) behind "Compare worksheets".
- Tests: `test_studio_board_browser.cjs` (236 id references), `test_studio_reconciliation_browser.cjs`, `test_studio_click_to_add_browser.cjs`, `test_studio_data_source_browser.cjs`, `test_studio_industry_browser.cjs`, `test_studio_wording.cjs` and other suites that read `index.html`.

## Build this (Builder mode)

1. **Header row:** title "Chart Studio" (serif 40px); a source chip "Banking · All cycles · Published included receipts ▾" (industry · cycle scope · basis label) that opens a popover holding the existing source controls: Data source, Report, Accounting basis, State location view, "Refresh verified data", "Rescan columns" (move the existing elements and keep their ids); a dashed one-line `.chip-add` "+ Compare with..."; a status "● Ready" (teal dot; reuse the existing ready indicator); right-aligned, the `.segmented` Builder | Company overview | Canvas.
2. **"+ Compare with..."** opens 02's menu (another industry, cycle or company). Choosing a value adds that scope to the current sheet as a series split, coloured `--scope-1` and `--scope-2`, with the pills shown in the chip as on Graph. Build it on the worksheet-comparison machinery. If that machinery cannot put a second scope on the same sheet without a new server path, stop and report what it can do; do not invent a data path.
3. **Toolbar, one row**, of labelled icon buttons: Undo, Redo | Swap | Sort ▾ (one menu button: Ascending = `#studio-sort-asc`, Descending = `#studio-sort-desc`, None) | Labels (`#studio-labels`) | "Fit: Standard ▾" (`#studio-fit`) | Clear, Duplicate | then right-aligned: gold "Show Me" (the only gold on the screen; Sort no longer turns gold), "Compare worksheets", "Export ▾", "Views ▾", "Add to briefing". The board-size buttons `#studio-board-1/2/4` show only in Canvas mode (D-061). The header row plus the toolbar row are the two rows D-041 allows.
4. **Fields pane (left, about 230px):** "Search 102 fields" at the top; DIMENSIONS and MEASURES as headed lists with type glyphs (Abc for text, a calendar for dates, a pin for places, # for measures) and a 6px `--acu-purple` dot on every field in use; dragging works as today. "Fields from" becomes a compact "From: All related tables ▾" under the search box (not on S1; an intended difference that keeps the control).
5. **Shelves:** Columns, Rows and Filters as on S1, with the chart-type select ("Chart: Bar ▾", the existing Chart variant select, moved) at the right end of the Columns row. The standalone "Primary measure aggregation" select leaves the canvas; aggregation stays available from each measure pill's menu (SUM, AVG and so on). Keep its element hidden if a test needs it.
6. **Canvas:** chart title (serif 28px, for example "Published included receipts by Company"), a muted subtitle, three figures (Selected net amount, Source observations, Reported donor identities), and the chart with value labels at the bar ends.
7. **Note line under the chart** (replaces the red box and keeps the id `#studio-reconcile`): background `rgba(214,200,226,.35)`, radius 8px, padding 10px 14px; text "This sheet covers all cycles. Graph shows 2025-2026." (built from the real scopes); a small secondary button "Match Graph scope"; a text link "Why" that opens a popover holding today's full explanation (including the "They differ by ..." sentence and the caveat paragraph now printed under the chart); and at the right end "Groups 1-10 of 10 · View source records" (previous and next arrows appear only when there are more groups). No red: stop applying `.studio-reconcile-differ` here. "Match Graph scope" sets the sheet's cycle, company, employee level and giving filters to Graph's current scope (read through `MentatScope`) and re-runs; when the scopes agree, the note hides. Update `test_studio_reconciliation_browser.cjs` assertion by assertion.
8. **Inspector (right, about 300px):** header "Inspector" (serif) with a "Collapse ›" button; tabs Marks / Analytics / Filters; Marks rows Colour, Size, Label, Detail and Tooltip, each with a line icon and a dashed drop zone "Drop a field here"; collapsible Show Me, Pages and Parameters. Collapse shrinks it to a 56px rail with three icon buttons (Marks, Analytics, Filters) that expand it again; remember the state per browser through `ui-state.js` (wrap storage in try/catch).
9. **Bottom:** sheet tabs "Data Source | Sheet 1 | + New sheet" and, right-aligned, the status line ("592,570 source observations · 10 groups · reconciles to the workbook").

Company overview and Canvas modes keep their content; only the shared header and toolbar change for them.

## Acceptance
States at 1440x900 and 1920x1080 beside S1: Builder default (Banking, all cycles, Company x SUM(Selected amount)); the source popover open; a second scope added through "+ Compare with..."; the note before and after "Match Graph scope"; the Inspector collapsed; Canvas mode showing the board-size buttons. Checks: one gold element; the chrome above the chart is exactly two rows; no red text in the builder. Suites: every studio browser suite listed above, `node --test mentat/app/tests/chart-studio-core.test.js`, `render_console.py --check`.
