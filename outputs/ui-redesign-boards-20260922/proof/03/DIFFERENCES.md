# Build 03 (Chart Studio, board S1) - differences, board vs build

Board: `boards\S1_chart_studio.webp` (2000x1131 = a 1600x900 CSS frame at 1.25x; read at 1.25 on both axes, per the README's build-01 notes). Build: read-only console on port 8817, 2026-09-22 late evening. Side-by-sides: `03_<state>_1440.png` and `03_<state>_1920.png` (board left scaled to CSS px, build right, 1 image px = 1 CSS px). Captures and in-page measurements: `capture03.cjs` -> `shots\`, `measurements.json` (1440x900, 1920x1080, every state), `measurements_1600x900.json` (the board's own frame). Every number below is `getBoundingClientRect` in CSS px at 1600x900 unless it says otherwise; board numbers are ink/edge positions read off the board at 1/1.25.

States captured (both sizes): builder_default, source_popover, compare_cycle (second scope added through "+ Compare with..."), note_before_match, note_after_match, why_open, inspector_collapsed, canvas_mode, and (final fix round, section E) compare_company, new_sheet.

## A. Acceptance checks (measured, every state, both sizes)

| Check | Result |
|---|---|
| One gold element | Builder states: exactly one, `#studio-showme-toggle`. Canvas mode: none (Show Me is Builder chrome). |
| Chrome above the chart is exactly two rows | `chromeRows` = `[[24,54],[83,114]]` in every Builder state at 1440 and 1920 (header row, toolbar row). Canvas: `[[22,56],[83,114]]`. |
| No red text in the builder | `redText` = `[]` in every state; `.studio-reconcile-differ` count inside the note line = 0 (asserted in test_studio_reconciliation_browser.cjs). |
| Board-size buttons only in Canvas | `boardButtonsVisible` = `[false,false,false]` in Builder, `[true,true,true]` in Canvas. |
| Match Graph scope | Before: note "This sheet covers all cycles. Graph shows 2025-2026." After: sheet filter `cycle = 2025-2026`, Studio $12,003,181.12 = Graph $12,003,181.12, "Agree.", note hidden. |
| Inspector collapse | 302px column -> 56px rail (three icon buttons); `localStorage['mentat-chart-studio-inspector-collapsed']` = `"1"`. |
| Page errors | none in any state. |
| Horizontal overflow | none at 1440, 1600, 1920, 1168 (scrollWidth = viewport). |

## B. Geometry at 1600x900 (board frame)

| Element | S1 | Build | Status |
|---|---|---|---|
| Page title (serif 40) | ink x 232-430, y 22-50 | box x 230-454.5, y 15-63 (ink ~232-452) | intended: Georgia fallback is wider than the board face (README fonts note) |
| Source chip | x 454-742, y 24-54 (30 tall) | x 478.5-803, y 24-54 | intended: starts 24.5px right (wider title) and is 37px wider (Arial) |
| "+ Compare with..." | x 761-926, two lines | x 813-944, one line, 30 tall | intended (Don't-copy: one line) |
| Ready | x 944-988 | x 954-1004 | fixed within 10px |
| Builder / Company overview / Canvas | x 1284-1581, 30 tall | x 1277-1578, 30 tall | fixed |
| Toolbar card | x 206-1592, y 73.6-124 | x 206-1592, y 73-123 | fixed |
| Show Me (gold) | x 1101-1178, 31 tall | x 1046-1124, 31 tall | intended: the right-hand labels set in Arial are wider, so the group starts 55px further left |
| Panes (Fields, centre, Inspector) | y 138.4-820.8 | y 137-819 | fixed (1.5px) |
| Fields card | x 216-420.8 | x 216-421 | fixed |
| Search box | x 226-411, y 150-185 | x 227-411, y 149-184 | fixed |
| Shelves card | x 434-1270, y 140-266 | x 434-1270, y 137-263.8 | fixed |
| Chart select ("Chart: Bar") | x 1144-1256 | chip x 1142-1255 | fixed |
| Canvas card | x 434-1270, y 278-820 | x 434-1270, y 275.8-819 | fixed |
| Chart title (serif 28) | ink y 291-316 | box y 282.8-316.8 | fixed |
| Figures row | values ink y 353-369 | row y 350.8-396.8, dividers between | fixed |
| Note line | x 444-1260, y 764-804 | x 453-1251, y 762-802 | fixed |
| Inspector card | x 1282.4-1584.8 | x 1283-1585 | fixed |
| Collapse button | x 1502-1574, y 149-178 | x 1488-1575, y 147.5-176.5 | fixed |
| Marks tab (bottom of underline) | y 226 | y 225 | fixed |
| Colour drop zone | x 1396-1574, y 249.6-288 | x 1396-1575, y 248.6-286.6 | fixed |
| Marks row pitch | 65.2 | 65.2 | fixed |
| Sheet tabs + status bar | y 834.4-878.4 | y 832.6-876.6 | fixed |

## C. Visible differences

Fixed (found against S1 during the build and corrected):
- C1 Toolbar wrapped to two rows at 1440 (baseline: 91px for a 32px control; test_studio_board_browser step 1 red). Now one row at 1440, 1600 and 1920 (1100-1499px tightens paddings).
- C2 Sort was two buttons and turned gold when pressed; now one "Sort" menu (Ascending, Descending, None), and nothing but Show Me is gold.
- C3 "Show mark labels" -> "Labels"; Undo/Redo/Swap/Clear/Duplicate carry S1's line icons.
- C4 Fit select restyled as S1's "Fit: Standard" with its icon; board-size buttons stay Canvas-only.
- C5 The source controls moved from the Fields pane into a popover under the source chip (ids unchanged); the Fields pane now starts with "Search 102 fields".
- C6 DIMENSIONS / MEASURES as headed lists with Abc / calendar / pin / # glyphs and a 6px purple dot on every field in use (on any shelf, filter or mark).
- C7 Chart variant select moved to the end of the Columns row ("Chart: Bar"); "Primary measure aggregation" left the canvas (element kept, hidden; each measure pill keeps its aggregation menu).
- C8 The chart panel's own "Net amount" heading is gone for a one-measure sheet (the serif canvas title names it); bars at S1's pitch (28px, 17px bars); axis in round steps with the end value ("$0 $2.0M ... $10.0M $11.2M"); value labels at the bar ends in whole dollars ("$11,246,552").
- C9 The red reconciliation box is now S1's lilac note line (#f3f2fb, radius 8, padding 6px 12px 6px 14px) with "Match Graph scope", "Why" and "Groups 1-10 of 10 · View source records" at its right; group arrows appear only when there is another page.
- C10 Inspector: serif "Inspector" 24px with "Collapse ›", Marks rows with line icons and dashed "Drop a field here" zones, Show Me / Pages / Parameters as chevron rows; the Show Me hint text is not shown in the Inspector (S1 has none).
- C11 Sheet tabs and the status line share one bar; status reads "592,570 source observations · 10 groups · reconciles to the workbook" (the query count moved to its title).
- C13 The Why popover named Graph's pinned cycle by its end year ("All companies · 2026", as the old strip did); it now reads "2025-2026", like the note line.
- C14 Compared series use the pills' own colours: pills rgb(87,68,123) / rgb(50,122,122), bars #57447b / #327a7a (measurements.json compare_cycle, `pills` and `barColours`).
- C12 The chart is drawn at the canvas's own width, so its text is 13.5px at 1440 and at 1920 (it was scaled to ~10px at 1440); a width change (window, Inspector collapse, Canvas mode) redraws from the held answer, no query.

Intended:
- I1 Fonts: Georgia and Arial fallbacks (brand faces not installed; D-050). Every horizontal offset in section B traces to this.
- I2 "From: All related tables ▾" row under the search box (prompt item 4: not on S1, keeps the control); the field list starts 28px lower.
- I3 The field list is the real 102-field verified catalog, not S1's eleven illustrative dimensions; amounts and names are real (Don't-copy).
- I4 The shell footer (46px, build 01) sits below the fold: the page is 962px tall at 1440x900 and 1600x900 and 1142px at 1920x1080 (the workspace keeps the shell's 40px bottom padding, which test_workspace_polish_browser.cjs holds equal on every view). S1 has no footer; the panes keep S1's geometry.
- I5 Undo and Redo are drawn disabled (nothing to undo on arrival); S1 shows them enabled.
- I6 Labels' pressed state is a purple icon, no fill (S1 shows none; a toggle needs one). A new sheet starts with Labels on, as S1 draws values; saved sheets keep their own setting.
- I7 The popover's first line is the old Data source summary ("Banking · Published included receipts · ✓ Ready"): the ready mark and the chip list stay where tests and screen readers find them.
- I8 Show Me uses `--acu-gold` (#eca91c), the one gold token Graph's gold button uses; S1 renders #e6b652.
- I9 Segmented selected fill #362d74 (sampled from S1) rather than the sidebar's #2f2452.
- I10 Note line when the scopes agree but the totals do not: it stays, reading "Same scope as Graph; the totals differ by $X." with Why. The prompt says the note hides when the scopes agree; it hides only when the totals agree too, so a difference is never silent. No red either way.
- I11 Employee level (ruling): Match Graph scope sets cycle, company and giving type, never employee level; when Graph has a level set the note says "Graph also narrows to the <level> employee level, which verified data cannot match." and Match's title says so.
- I12 Compare state (no board draws it): pills in the chip coloured --scope-1/2/3 with "+" for a third and "Clear" (accessible name "Clear comparison"); grouped bars in the pill colours with the legend inside the SVG; subtitle "... · compared: A vs B"; figures per report for industries (a dot per scope), one combined figure labelled "· combined" for cycles and companies; note line "Graph reconciliation pauses while this sheet compares scopes."; Data (CSV), Add to briefing and View source records are disabled for industries, with titles saying why (each report has its own provenance), and a bar opens its own scope's records.
- I13 Below 1300px wide the header and the toolbar may wrap (no sideways scroll at 1168, asserted by test_workspace_polish_browser.cjs); S1 is a 1600 frame.
- I14 Canvas mode: the chart fills the wider card; the note line and sheet bar stay (D-061 board control only here).

Open (Paul's call):
- O1 Bar colour: `--acu-teal` #327a7a (the chart palette's first token) vs S1's #2b9b99. Matching S1 needs a new token or a palette change that reaches every chart.
- O2 Long company names in the chart's label column are cut with "…" ("JP Morgan Chase Bank …") because Arial is wider than the board face (label column 185px).
- O4 At 1920x1080 the chart leaves space under its axis (ten groups at S1's pitch); S1 is drawn for 1600x900 only.
- O5 At 1440 the note sentence wraps to two lines inside the note line (the canvas card is 160px narrower than at 1600).
- O6 Giving type is carried as `funding_source` with Graph's own sparkline mapping (personal -> employee_original, corporate -> corporate_original, graph.js sparkRequest). Graph's filter itself is `tier == 'Corporate'` on report rows (graph_data.py:547), so rows in other buckets count as "personal" on Graph but are not in the carried filter; any residual is shown as a named total difference in Why.
- O7 While comparing, two bars per group outgrow the chart region at 900px tall; the drawing scrolls inside its region (title, figures and note line stay put).
- (O3 was fixed during the build; see C13.)

## E. Final fix round (review 03, 2026-09-23)

Captures re-taken for every state above plus two new ones, `03_compare_company_*` (Company x SUM sheet, "+ Compare with..." -> Another company -> first offered) and `03_new_sheet_*` (+ New sheet). `measurements.json` now also records `chipFit`, `hitAtClear`, `canvasScroll`, `axisTicks`, `categoryLabels`, `title`/`subtitle`/`figures` and `noteLineHeight` per state. The reviewer's own walk (`review03.cjs`, unchanged, FULL=1 COMPANY=1) was re-run on the fixed bytes: 0 console errors, 0 page errors, 0 off-origin, 0 failed requests.

Fixed:
- C15 (R03-1) Header with compare pills at 1440: the compare block shrinks (`flex:0 1 auto; min-width:0`), pills cap at 150px with an ellipsis, Ready no longer shrinks, and the source chip gives way first (`flex-shrink:4`, min 130px). Two companies: `elementFromPoint` at Clear's centre = `studio-compare-clear` (Clear 1014-1042, Ready 1050-1101, segmented 1117-1418); three companies: the same, pills 710-1006. 1920: Clear 1138-1167, hit = Clear. The header stays one 56px row (`min-height:56px`, no fixed height).
- C16 (R03-2) Note line after Match Graph scope: with the note hidden, the caveat sits on the note line's free left side (two lines at most, 12px, full text in `#studio-note`'s title) instead of a row of its own. 1440 `canvasScroll` after Match = 357/357 (was 350/296), axis ticks `$0 ... $2.0M $2.6M` in view; note line 40px.
- C17 (R03-3) Source chip: one block line (`display:block`, line-height 28px) so `text-overflow` gives an ellipsis before the chevron; the 250px cap at 1100-1499 is gone (base 420px). 1440 default: scrollWidth 323 = clientWidth 323, full text "Banking · All cycles · Published included receipts" (after Match: 332 = 332). With two company pills it cuts to "Banking · All cycles · Publish…" (226px) with a visible ellipsis.
- C18 (R03-4) "+ Compare with..." never offers scope 1: cycle lists 2021-2022, 2023-2024 (not 2025-2026); company lists from Bank of America NA (not Goldman Sachs Bank NA). One pick now gives two pills (no "Choose a second..." step).
- C19 (R03-5) Comparing companies on the Company sheet: each bar carries its company's name (`categoryLabels` = Goldman Sachs Bank NA, Bank of America NA), title "Published included receipts by Company"; never "Selected population".
- C20 (R03-6) Escape closes Why with focus on the Why button (probe: hidden true, focus stays on `studio-reconcile-why`); asserted in test_studio_reconciliation_browser.cjs.
- C21 (R03-7) Filters: the placeholder is centred in its dashed box (`align-content:center`) and the box ends at x 974 like Columns/Rows (`#studio-filters` 544-974); the empty Columns/Rows placeholders on a new sheet are centred the same way.
- C22 (R03-8) Axis end value at every width: when the end value would collide with the last round tick, that tick gives way (1440: `... $6.0M $8.0M $11.2M`; 1920: `... $10.0M $11.2M`). C8's "with the end value" now holds at 1440 too.
- C23 (R03-9) Comparing industries: the counter reads "Groups 10 · 10" (the per-industry ranges are in its title); note sentence on one line, note line 40px (was 65px).
- C24 (R03-10) + New sheet: the empty sheet shows no title, figures, counter or status from Sheet 1; the guidance "Add a dollar or count measure to Rows or Columns." is the muted subtitle; `redText` = [] and `#studio-error` hidden. Other errors (compare refusals, a failed query) still clear the old answer and still show in the red error box.
- C25 (found in this round) At 1440 the default chart overflowed its region by 6px (350/344) because the two-line note makes the note line 47px; the canvas card's bottom padding is 10px at 1100-1499px, so it is 350/350 (no scrollbar in a browser that shows classic scrollbars).

Intended:
- I15 At 1300-1499px the header keeps one row while comparing (it does not wrap): wrapping would push the panes, whose height is tied to the viewport, down by a row. Pills and the chip ellipsize instead; hover a pill for its tooltip. Below 1300px the header still wraps (I13).

Open (Paul's call):
- O5 (updated) At 1440 the note sentence still wraps to two lines in the note line before Match (47px); the chart region now absorbs it without scrolling (C25).
- O8 In the capture run, clicking "+ New sheet" left the 962px page (I4) scrolled 62px to its footer at both sizes; the reviewer's walk did not see it. Not changed here; the `new_sheet` capture scrolls back to the top before the screenshot.

## D. Rulings applied (orchestrator, under Paul's "Reconcile; go to completion")

- Compare data: POST /api/contributions/query only; cycle and company as ONE query with an `in` filter (the compared field is added to the dimensions when absent); industry as one query per report; merged in the browser under a browser-only `scope` series (never sent: contribution_semantics.py validate refuses unknown dimensions). --scope-1 (purple) and --scope-2 (teal) are an explicit colour map (`spec.colorMap`, contribution-plot.js), resolved from the CSS tokens at draw time so exported SVGs keep them.
- Drill-down, CSV, totals, reconcile and briefing: handled per scope or disabled with an explicit state (I12).
- Match Graph scope: everything except employee level (I11), read through `MentatScope.read()` (Graph's controls when that module is absent).
- ui-state.js: `MentatState.recall(key)` / `remember(key, value)`, both try/catch; key `mentat-chart-studio-inspector-collapsed`.
- No compare keys in the URL (the compare state is per sheet, in the tab; `url` in measurements.json shows `?industry=Banking` only).
- GRAPH_NOT_CARRIED inconsistency resolved with evidence: giving type IS verified data (`funding_source`, "Funding source", contribution_data.py:57; decision bucket, contribution_data.py:375; Graph filters it for its sparklines, graph.js:1382-1383). It is now carried by "Open in Chart Studio" and by Match Graph scope and was removed from GRAPH_NOT_CARRIED; employee level stays "not carried (not in verified data)".
