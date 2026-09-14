# Chart Studio redesign spec (A layout + D inspector + C company overview)

Owner: Paul. Coordinator: Claude (this session). Builder: architect agent.
Tree: C:\Users\pgoff\Mentat\mentat\app (branch codex/mentat-crypto, dirty with other lanes'
uncommitted work). Build on top of the four applied patches (S1-S4). Nothing is committed by
agents; Paul commits.

Paul's words (2026-09-13): "Apply the four patches, go with A plus the D inspector. I do also
like the C multi view for a single company as its own mode, lets put that in. Once done, give it
a test ride, we also want to be able to include filters, change measures and data types, all
like Tableau would but streamlined for political money."

The reference renders (v2A_workbench.png, v2A_split.png, v2C_commandbar.png, v2D_inspector.png)
live in C:\Users\pgoff\Mentat\audits\mentat_system_debug_20260913\drafts\. Read them (the Read
tool renders PNGs) before building. They are mockups: layout and controls are the contract,
their numbers are not.

## 0. Hard constraints

- Theme: use the existing tokens only (acu-theme.css): --acu-paper #fcf7f4 page, --acu-ivory
  #f7ede4 panels, white cards, --line #e4d9d0 borders, --acu-plum #342649 text and chart ink,
  --acu-purple #57447b selected states, --acu-gold #eca91c for the single primary action,
  --acu-lilac #d6c8e2 chips, --acu-teal #327a7a secondary mark, --muted #716a64. Fonts stay
  var(--font-sans) for UI and var(--font-serif) for headings; the studio chart title stays at
  the existing 21px serif (chart-studio.css:268); no oversized titles.
- No new dependencies, no build step, no external loads. Plain HTML/CSS/JS in the existing files
  (index.html, chart-studio.js, chart-studio-core.js, chart-studio.css, chart-comparison.js,
  chart-studio-contributions.js) plus at most one new file if a module genuinely needs it (then
  add it to server.py's static allow-list - remember that requires a console restart).
- Keep every existing capability working: worksheet mode and verified-contributions mode, the
  classic builder link, sheet tabs, undo/redo, export/download, drag and drop onto shelves,
  keyboard "Press Enter for actions" on field pills, localStorage persistence keys, and the
  `MentatStudioPane` iframe protocol used by the comparison grid.
- Keep the S4 honest-refusal behaviour: an Analytics control that cannot act on the current mark
  type / source / shelves is disabled with its reason shown; never a silent no-op.
- One writer per file: back up each file you edit as `<file>.bak-20260913-redesign` before the
  first edit. Preserve each file's line-ending class (chart-studio.js, chart-studio-core.js,
  tests are CRLF; chart-math.js is LF; index.html is mixed - check before writing).
- Tests: extend mentat\app\tests\chart-studio-core.test.js (node --test) for every pure-logic
  addition (filter model, measure/aggregation model, data-type coercion, company-overview spec
  builder). Suite must stay green; report the new count.
- Accessibility: every control needs an accessible name; segmented controls are role=tablist or
  radio groups; the Inspector tabs are real tabs (aria-selected); focus order left to right.
- Product law (brain D-022 item 7): simple to use, concise, minimal duplication, current data
  first. Streamlined for political money: the vocabulary is companies, cycles, recipients,
  recipient categories, committees, parties, employee levels, contributor geography - not
  generic BI terms.

## 1. Layout (draft A skeleton, draft D inspector)

Top of the studio view, one header row:
- Left: existing serif heading "Chart Studio".
- Next to it: the scope chip. When the studio was opened from the Graph tab through the S1
  hand-off (pendingScope), render a lilac chip "Carried from Graph · <Industry> · <Cycle or All
  cycles> · <Company or All companies>" plus a small "Change scope" link that opens the Data
  source disclosure in the left panel. When opened directly, the chip reads
  "<Industry> · <cycle filter or All cycles>" from the current dataset and filters.
- Right: the view segmented control "Builder | Canvas only". This REPLACES the visible wording
  of the S3 "Hide/Show chart options" control and drives the same state
  (studio-options-hidden). "Canvas only" hides Data panel, shelves and Inspector; the segmented
  control itself and the sheet tabs are never hidden (the S3 patch's sticky restore rule stays).
- Second row = the comparison toolbar from chart-comparison.js, restyled: segmented
  "1 chart | 2 charts | 3 charts | 4 charts", the "Linked filters" switch, and a new mode
  toggle "Company overview" (section 3). Keep the S2 blocked-pane status line.

Three columns beneath (CSS grid: 260px | 1fr | 300px; collapses to two columns under 1200px
with the Inspector becoming a drawer toggled from the header):

LEFT - "Data" panel (ivory):
- A "Data source" disclosure (collapsed by default once a source is loaded) holding the
  existing selects: mode (Verified contributions / Report worksheet), report/dataset,
  accounting basis, state view, worksheet controls, refresh button, status line.
- "Search fields" box and the "Fields from" table select stay.
- Dimensions list, then Measures list, as pills. Each pill shows a type glyph on the left: "Abc"
  for text, "#" for numbers, a small calendar-style glyph made in CSS/SVG (no emoji) for dates,
  a geography glyph (text or inline SVG only) for state/city/ZIP.
- Pills keep drag-and-drop and the Enter-for-actions menu; the menu gains the data-type actions
  of section 4.3.

CENTER - canvas card (white):
- A compact shelf strip at the top of the card, one row each: "Columns", "Rows", "Filters"
  (draft D style: label, then pills). "Pages" and the Marks shelves (Color, Size, Label, Detail,
  Tooltip) move to the Inspector's Marks tab; the underlying state is unchanged.
- Serif title (existing), the chart, the existing note line, scope line, pager, table toggle.
- Sheet tabs remain under the card.

RIGHT - "Inspector" card (white) with three tabs: "Marks", "Analytics", "Filters".
- Marks tab: the Show Me grid (existing tiles, existing disabled-with-reason idiom) at the top,
  then the Marks shelves (Color, Size, Label, Detail, Tooltip) as drop rows, then chart
  parameters (Group limit, Split multi-value, Subject, bin width - the existing "Parameters"
  controls), then the existing "Show identifier fields" checkbox.
- Analytics tab: the seven analytics objects as switch rows (draft D): name, one-line hint,
  switch on the right; transforms are a single-select group (radio semantics) - Period totals,
  Year-over-year %, Period change, Same-phase forecast - followed by Totals, Average line, Median
  line switches, then the transform parameters (Period: cycle/year; Forecast horizon stepper).
  Disabled rows show the S4 refusal reason in place of the hint. Switches must stay draggable
  onto shelves if the current code supports that; otherwise drop the drag.
- Filters tab: section 4.1.

The gold primary button: exactly one per view. In the builder it is "Show Me" only if the tile
grid is collapsed; otherwise no gold button on the canvas. In Company overview it is
"Open in builder" on the focused card. Do not add more gold.

## 2. Comparison (split view) - keep, polish

The 1-4 chart grid stays iframe-based (S2 patch). Each pane gets a small purple tag "Chart A/B/
C/D" at its top-left (draft v2A_split). Linked filters continue to sync the Filters shelf across
panes through the existing MentatStudioPane protocol. A blocked pane keeps the S2 status line.

## 3. Company overview mode (draft C, one company, four preset charts)

Toggle "Company overview" in the comparison toolbar. Behaviour:
- Requires verified-contributions mode (it uses the contributions query API). In worksheet mode
  the toggle is disabled with reason "Company overview uses verified contributions".
- Company picker: a select populated from the `company` facet of the current dataset; defaults
  to the scope chip's company if one was carried from the Graph, else the first company.
  Cycle: honours the current Filters shelf cycle filter if present, else all cycles, and says so
  in the header line ("<Company> · Banking · Cycle 2025-2026" or "· All cycles").
- Renders a 2x2 bento grid of four cards, each with a serif caption and a small "Open in
  builder" action:
  1. "Recipient categories" - horizontal bars, dimension recipient_category, measure
     SUM(amount), sorted descending, group limit 10.
  2. "Giving by election cycle" - line, dimension cycle, measure SUM(amount).
  3. "Top recipients" - vertical columns, dimension recipient, SUM(amount), top 8 (limit 8).
  4. "Party split" - doughnut, dimension party, SUM(amount) (the mockup showed employee level;
     the contributions catalog has no employee-tier field, so use party; put a one-line note
     under the card saying the split is by recipient party).
  Render in-page (NO iframes) by reusing the existing compile -> query -> paint path of
  renderContributionView(); factor a `renderPreset(spec, container)` helper if needed. Charts
  are read-only in this mode (no shelves); clicking "Open in builder" loads that preset into the
  current sheet (columns/rows/filters/mark type) and switches back to Builder.
- Command palette (Cmd/Ctrl+K) from draft C: OPTIONAL, only if cheap - a searchable list of
  actions (add field to Columns/Rows, set mark type, toggle analytics, add pane, show builder).
  If you build it, it must call the same functions the buttons call. Skip it if it costs more
  than an hour; note it as follow-up.

## 4. Filters, measures, data types - Tableau-like, streamlined

### 4.1 Filters
- Filters shelf accepts any field (existing). Clicking a filter pill (or Enter -> "Edit filter")
  opens a popover anchored to the pill:
  - Categorical field: searchable checklist of members (use the existing members() facet fetch
    for verified mode; distinct column values for worksheet mode), "All / None" links,
    Include / Exclude toggle, an "Only top N by <measure>" option when a measure is on Rows.
  - Numeric measure: min/max inputs with the field's observed range shown as placeholder.
  - Date/cycle field: cycle multi-select for `cycle`; for `date` a from/to pair; for `year`
    a checklist.
  - Apply / Cancel; Apply commits through commit() so undo works.
- Inspector "Filters" tab lists active filters as rows (field · operator · summary such as
  "3 of 10 values", ">= $1,000", "2023-2026") with edit and remove actions, plus an "Add filter"
  select listing all fields. It is the same model as the shelf; no duplication of state.
- Scope chip filters (industry/company/cycle carried from the Graph) are ordinary filter pills.

### 4.2 Measures and aggregation
- Each measure pill on Rows/Columns shows its aggregation prefix "SUM(...)", "AVG(...)",
  "COUNT(...)", "COUNT DISTINCT(...)", "MEDIAN(...)", "MIN(...)", "MAX(...)". The pill's menu
  (click caret or Enter) offers "Aggregation" with those choices and "Replace measure"
  listing the other measures. Only offer aggregations the active engine supports: confirm in
  chart-studio-core.js / chart-math.js (worksheet) and contribution_query.py (verified); hide
  unsupported ones rather than failing at query time.
- Political-money presets in the measure menu: "Total giving" (SUM amount), "Gift count"
  (COUNT), "Average gift" (AVG amount), "Distinct contributors" (COUNT DISTINCT contributor)
  where the field exists.

### 4.3 Data types
- Field pill menu gains "Treat as: Dimension | Measure" (a numeric column such as ZIP or
  committee ID can be used as a dimension; a count-like text column cannot become a measure -
  refuse with reason), and for date-like fields "Date part: Election cycle | Year | Quarter |
  Month". In verified mode map these onto the catalog's derived fields (cycle, year, quarter,
  month, weekday, amount_bin) so the query stays server-side; in worksheet mode implement via
  chart-studio-core's column classification and the existing time transforms.
- The type glyph on the pill updates immediately; the change is per sheet and persisted with
  the sheet state.
- Number formatting: measures render as $ with thousands separators and M/K abbreviations on
  axes (existing money() helper); counts render as integers.

## 5. Things that must NOT regress

- The S1 hand-off ("Open in Chart Studio" on the Graph tab) still applies industry/company/
  cycle as visible, undoable filter pills.
- S2: blocked pane message; S3: restore control always visible; S4: refusal reasons.
- Worksheet mode users (report workbooks) keep every existing shelf and parameter.
- Query volume: while you are in chart-studio.js, examine the page-load storm (~160 POST
  /api/contributions/query on a fresh load with no interaction). Confirmed suspects: members()
  memoises before awaiting (chart-studio.js ~:530) but its .catch deletes the key (~:533) so a
  failing facet is re-fired on every render. If the code confirms a re-fire loop, fix it with a
  negative cache (remember failures for 30 s, then retry) and log the request count in the
  status line; if not confirmed, leave it and report what you saw. Do not exceed one query per
  distinct facet per 30 s from any render path.

## 6. Deliverables from the architect

1. The edits in place (with .bak-20260913-redesign copies) and `node --check` /
   `python -m py_compile` clean; the core test suite green with the new count.
2. A RECEIPT.md in the scratchpad studio\redesign\ folder: files touched with before/after
   hashes, what was built against each section number above, what was deliberately skipped and
   why, known limits, and the exact manual test script the coordinator should run on a fresh
   read-only instance (python server.py --port 8812 --read-only): 12-20 numbered steps with
   expected results.
3. No server restarts, no git add/commit, no edits outside mentat\app and its tests.
