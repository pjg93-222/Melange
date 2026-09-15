# BUILD LANE F-client — receipt

Agent: architect. Date: 2026-09-14. Branch `codex/mentat-crypto`, HEAD `2f11d9490` at start.
Plan: `C:\Users\pgoff\.claude\plans\the-mentat-chart-system-breezy-wilkinson.md`
Prompt pack: `C:\Users\pgoff\Mentat\audits\mentat_system_debug_20260913\prompts\PROMPT_PACK.md`
Visual contract: `prompts\renders\R1_builder.png`, `R2_canvas_export.png`, `R3_reconcile.png`
Lane directory (step files, engine, smoke): this folder.

Build order executed: F0, F2, F3, F5, F6, F4 (as briefed). Every step written to disk and
verified before the next one started.

---

## 1. Files changed, before/after SHA-256

All backups are `<file>.bak-20260914-Fc`, taken before the first edit of each file; none
overwrote an existing backup.

### `C:\Users\pgoff\Mentat\mentat\app`

| file | before | after |
|---|---|---|
| chart-studio-core.js | cc5b888b5952466b7d926826d769765e10a73c720eaeb7d216f94e9691b9efb5 | 04d4f88c75557af6f61a77b88c3458ec1bc106fd51b7c30aff5de5caa071115b |
| chart-studio.js | 80dbd40b21805ff124d1cf74d8d23836df417a89385f00b0dea879b64675f975 | 21f3d67d2261d0298ce7c3e8e88bb1948aa4714a188366a2b66b10dbfbe110b8 |
| chart-studio-contributions.js | 4b66683d584884e3922ac24628b1a0a6ea426f81883fc0f8486b237aa1087f25 | c63edd5b59d9f6c4709bf1c28b0ef7dff9c7db9904c3444ef160084d24b7448c |
| index.html | c528124b670a95e7d4abe4c7d2a2c90e2cef972eeb6fb19e2408785081ec9ac4 | fd220c1111d5ad282839390f9504d60d6fdb44f276b897eeb4cb3118eb51ee98 |
| chart-studio.css | f22c540fad765542158323f5ad071f4ec7c5cf85b213bb819b14e7eaf26a65f7 | 81fe526f9e0014224d9da629333167065736e06bf61463e887307f4c7e8eee94 |
| graph.js | 94ea86ef9340f9f2029d65fed69c6b8dafe46bb782b9948af1c594abf6143619 | d33579f871a7376c8cb115d97655f1210110bcc120d0f5f4e5994942c57d08b3 |
| cross-reference.js | f306433de07209619d8a0b3d71559e68a4e0385dada35f75d569d3e20faa3ccb | ebbb08c5c2535fd57801b9884d4dd9c0e3b9603ebe8b29b492b67dfa705e3001 |
| **chart-comparison.js** | be3a3b58addeec34af273646ec59c4ae39e334252efe47528a89f2d231e7a197 | **unchanged (same hash)** — backed up, never edited |
| tests/chart-studio-core.test.js | 82e3d6753323e61e2039e0feb7bce9c031ec43268011006e258a1a91d3855560 | fda752d023c83105d1cc99f8362cdd92e5b6a0d7df1b1b5ad6a5b2fa460c2e06 |

### `C:\Users\pgoff\Mentat\mentat\tests`

| file | before | after |
|---|---|---|
| test_chart_studio_contributions.cjs | e98e51f41420dd5ee9070b4076378bd9d1f9a3590559bd2cd6bc35f71d662939 | 58942d4c55aa03790fd1258013a5dd3e994a849fe7263a5d5daaf5f8ec97a528 |
| test_cross_reference_view.cjs | 52b567b9118a0f3947b859d0c61daaf7e60cb4c3bf20ef7da9d7e86e2efc0af6 | be674261677cc5101380f09c832a2ef64c22f37f768107d7e848a42907639974 |
| test_original_studio_contributions_browser.cjs | (backed up `.bak-20260914-Fc`) | 91d7cdbea6e1ae8918a2df0b43f08b1061e000aa62fe3079a0cc0da96af5a257 |
| test_chart_comparison_browser.cjs | (backed up `.bak-20260914-Fc`) | 5586fac3f430e8ac1d224290865640c10f5a7655a300cf12448effa4bf3756cf |

New files (created, no prior version):

| file | sha256 |
|---|---|
| test_studio_click_to_add_browser.cjs | 1b3ebd01006e151313ba9d6fe42b4e6b63e92f13df6854c1fc76b379e3cc864c |
| test_studio_data_source_browser.cjs | f8229cefdbe05a3704b178bff7a6cec45c83a07065557a4db43221fde0e2fdb7 |
| test_studio_reconciliation_browser.cjs | 58304bba473e6c298233e810fcfb0f8d10d2c69f72bb698fba539397cc762d95 |
| test_studio_wording.cjs | 2b9418a6e677ab273e0200ddf80ca2749907dcf765c700148f66486375f4a3c3 |
| test_studio_canvas_only_browser.cjs | 058e947df66674ace5be8c13a83429cdfac2e7d293ba8d95b97170c72a82dae4 |

Nothing outside my file set was touched, with two exceptions recorded in §5.

---

## 2. Per-fix status and the ride steps each satisfies

| fix | status | ride steps |
|---|---|---|
| F0 cycle carry | DONE; confirmed against the live index, not only the source (§2b) | 17 (and the F4 15–19 block depends on it) |
| F2 click-to-add | DONE; 2 defects of my own found in review and fixed (§4.5, §4.10) | 07–10 |
| F3 data source always findable | DONE; 3 defects found and fixed (§4.1, §4.2, §4.6, §4.8) | 11–14 |
| F5 wording | DONE (approved WAS/NOW table; one deviation, §6.1) | 20–21 |
| F6 Canvas only + Inspector toggle | DONE; 1 pre-existing defect found and fixed (§4.3) | 22–24 |
| F4 same numbers (a–e) | DONE (approved REASON NAMES table verbatim); 3 defects fixed (§4.4, §4.7, §4.9); both scopes agree to the cent on live data (§2b) | 15–19 |

Ten defects were found and fixed while building — four of them latent in code this lane did not
introduce (§4.3 the Inspector drawer, §4.8 the async `toggle`, §5.2 the comparison labels) and
the rest in my own work, all caught by the tests I wrote for the fixes rather than left for
Ride 1.

### F0 — cycle carry (`chart-studio-core.js`, `chart-studio.js`, core tests)
Confirmed cause: `graph.js:73` renders cycle option **values** as the end year, while
`contribution_data.py:322` stores `f'{cycle-1}-{cycle}'`. New pure
`core.carriedFilterValue(fieldId, value)` maps `'2024' -> '2023-2024'` for `cycle` only and
leaves every other field untouched; `core.graphCycleValue(label)` is the reverse, returning
`''` for anything that is not a consecutive pair. `graphScope()` translates before pushing the
carried filter. Proven in the browser: a hand-off now fires
`filters: [{company eq 'Alpha Bank'}, {cycle eq '2023-2024'}]` and draws the company's money
instead of "No matching observations".

**Confirmed against live data, not only against the source.** A real query on my own read-only
instance (`POST /api/contributions/query`, dataset Banking, dimension `cycle`) returns the
cycle values the index actually holds:

    cycle='2021-2022'  amount_cents=1665245877
    cycle='2023-2024'  amount_cents=2610720416
    cycle='2025-2026'  amount_cents=1200318112

Graph's option values for those same cycles are `2022`, `2024`, `2026`. The old code carried
`'2024'` — a string this index never stores — which is exactly the "No matching observations"
Paul reported.

### F2 — click-to-add (`chart-studio-core.js`, `chart-studio.js`, `chart-studio.css`)
New pure `core.quickAddZone(field, sheet)`: a dimension goes to Columns if Columns is empty,
otherwise Rows; a measure goes to Rows if Rows is empty, otherwise Columns. It reads the
shelves only. A click on a Data-pane pill runs `commit(() => place(zone, field.index))` — the
same path a drop uses, so one click is one undo step and one query — then writes
"Added &lt;field&gt; to &lt;zone&gt;." to the status line. The Enter menu gains a first entry
"Add to &lt;zone&gt;". Pill title and aria-label lead with
"Click to add · drag to place · Enter for actions". A drawn `+` appears on hover/focus-visible
(`::after`, `pointer-events:none`, so the pill keeps one tab stop). Show Me now reads the
shelves (`showMeSelection(..., [])`). Drag handlers and drop zones untouched.

### F3 — data source always findable (`index.html`, `chart-studio.js`, `chart-studio.css`)
`<details id="studio-source-details" open>`; folded **once** by `settleSource()` after the first
load that produced fields, and never again if the reader reopens it. The header button is
permanent and now reads "Data source" (`hidden` dropped in the markup and the
`renderScopeChip` line that re-hid it removed). `renderSourceSummary()` writes the collapsed
line exactly as R1 draws it — verified live: `Data source · Banking · Published included
receipts · ready` — and mirrors the live status there while a load is running. An unavailable
report carries the server's `message` on its own `<option title>` and under the select in
`#studio-dataset-message` (`.studio-note.is-warning`); when no dataset is available the thrown
text now lists every per-dataset message. A prepare shows `#studio-progress` with the server's
message, `m:ss elapsed` on a 1 s timer, and Cancel, which aborts the live controller and leaves
the last good view on the canvas. Progress is reference-counted, so concurrent verified calls
(view, member lists, records) cannot hide it early.

### F5 — wording (approved WAS/NOW table)
"Contribution explorer" is gone from the client (`grep` asserts it in
`test_studio_wording.cjs`). Replacements name the real control, Data source:
`chart-studio-core.js` encoding refusal, extra-measures refusal, scatter-grouping refusal and
the numeric-filter note; `chart-studio-contributions.js:83` and `:92`;
`chart-studio-core.js` empty-sheet issue (both sites) -> "Add a grouping (company, recipient,
cycle) and a dollar measure."; `index.html` default note and the two runtime empty states ->
"Choose a verified report in the Data panel to begin." / "Choose a report worksheet in the Data
panel to begin." The core test that matched `/Drag a dimension/` was updated.

### F6 — Canvas only keeps Export; Inspector toggle (`chart-studio.css`, `index.html`, `chart-studio.js`)
`.studio-toolbar` removed from the Canvas-only hidden set; a new rule hides every toolbar child
except `#studio-download` and right-aligns the row. `#studio-inspector-count` badge added inside
the toggle, filled from `renderFilterRows()` along with an `aria-label` that names the count.
`aria-expanded` is now truthful from first paint, and below 1200px the Inspector closes when the
window crosses the breakpoint (see §4).

### F4 — same numbers
(a) Pure `contributions.reconcile(result, basis, graphView, filters)` -> `{graphCents,
studioCents, receiptCents, differenceCents, agree, reasonId, reason}`, reasons in the briefed
order: basis is not `receipt`; a Graph tier/giving filter with no verified field; workbook SHA
mismatch (`graphView.reports[].sha256` vs `result.provenance.workbook_sha256` — both are
SHA-256 of the workbook **contents**, `report_insights.digest_stamp` and
`contribution_data._hash`, so they are comparable); `reconciliation.aggregate_filters_applied`;
else `unexplained`. `chart-studio.js` adds `graphTotals(company, cycle)` (one `/api/graph`
request per scope key, `Map`-cached for the session, cycle converted with
`core.graphCycleValue`), `reconcileScope()` (fires only when the sheet's active row filters are
exactly a company and/or a cycle, each an exact single value — `equals`, or `in` with one
member — and nothing else) and `renderReconcile()`, which draws `#studio-reconcile` under the
title with "Agree." in teal or "Differ by $X because &lt;reason&gt;." in the negative colour,
plus the "Why Cross-reference differs" link. A failed Graph request or a scope Graph cannot
express leaves the strip away entirely; it is hidden in worksheet mode and on a query error.
(b) `#graph-basis-note` under `#graph-total`, filled by `graph.js` render().
(c) `#studio-scope-note` under the chip, fed by `appliedScope.notCarried`, built in
`graphScope()` from `GRAPH_NOT_CARRIED` plus any scope field the dataset lacks.
(d) Group counter now "1–N of M groups · totals cover all M". The Group-limit label reads
"40 per page (verified) · fold after 40 (worksheet); Graph and classic fold at 60" in both the
markup and the verified runtime override. **The limit itself is unchanged: `STUDIO_GROUP_LIMIT`
is still 40** (asserted in `test_studio_wording.cjs`).
(e) `cross-reference.js`: the 19 approved plain-word reason names added verbatim, the approved
$0 caption added under the money grid, and `metric()` prints "Cycles &lt;list&gt;" beside every
dollar metric (from `report.scope.cycles`, reset per render, absent when the run has none).

---

## 2b. The lane's acceptance question, answered on real Banking data

The plan's acceptance is "Graph and Studio agree to the cent on Scope A and Scope B". I put that
question to the live workbook through my own read-only instance on 8817, rather than waiting for
Ride 1 to discover it.

**Scope A — Banking · All cycles · All companies**

| side | figure |
|---|---|
| Graph `totals.giving` | 54,762,844.05 |
| Studio `totals.amount`, receipt basis | 5,476,284,405 cents = $54,762,844.05 |
| verdict | **agree to the cent** |

**Scope B — Banking · Cycle 2025-2026 · Bank of America NA** (9 recipient-category groups)

| side | figure |
|---|---|
| Graph `totals.giving` (cycle=`2026`) | 1,459,371.05 |
| Studio `totals.amount` (cycle=`2025-2026`) | 145,937,105 cents = $1,459,371.05 |
| `comparison.receipt` | 145,937,105 — same figure |
| `reconciliation.receipt_matches_workbook` | `true` |
| verdict | **agree to the cent** |

**And the bug F0 fixes, reproduced on the same live data.** Repeating Scope B with the cycle
spelled the way Graph spells it — the value the old code carried:

    filters: [company eq 'Bank of America NA', cycle eq '2026']
    -> group_count = 0, totals.amount = 0

which is precisely the "No matching observations" Paul reported after a hand-off. With F0 the
same hand-off carries `2025-2026` and returns the 9 groups and $1,459,371.05 above.

So the two numbers behind ride steps 15–19 already agree; what Ride 1 still has to confirm is
that the strip *says so* on Paul's own console.

## 2c. Final sweep, on the exact bytes recorded in §1

Nineteen suites, all green, run after the last source change:

    chart-studio-core.test.js                       81 pass  0 fail   (77 before this lane)
    test_chart_studio_contributions.cjs             13 pass  0 fail   (12 before)
    test_studio_wording.cjs                         10 pass  0 fail   (new)
    test_cross_reference_view.cjs                   ok               (+17 assertions)
    test_chart_math.cjs                             20 pass  0 fail
    test_studio_click_to_add_browser.cjs             1 pass  0 fail   (new)
    test_studio_data_source_browser.cjs              1 pass  0 fail   (new)
    test_studio_reconciliation_browser.cjs           1 pass  0 fail   (new)
    test_studio_canvas_only_browser.cjs              1 pass  0 fail   (new)
    test_original_studio_contributions_browser.cjs   1 pass  0 fail
    test_studio_temporal_regression_browser.cjs      1 pass  0 fail
    test_studio_inspection_regression_browser.cjs    1 pass  0 fail
    test_chart_comparison_browser.cjs                1 pass  0 fail   (was RED at HEAD, see §5.2)
    test_chart_builder_browser.cjs                   2 pass  0 fail
    test_contribution_export_browser.cjs             1 pass  0 fail
    test_contribution_studio_state_browser.cjs       2 pass  0 fail
    test_contribution_charts_browser.cjs             1 pass  0 fail
    test_contribution_map_browser.cjs                1 pass  0 fail
    test_contribution_plot_readability_browser.cjs   1 pass  0 fail

    id census: 126 ids referenced, 0 missing from index.html
    node --check: 16/16 edited JS files ok

## 3. Checks run

- `node --check` on every edited JS: 16/16 ok (7 app files, 9 test files).
- ID census `redesign\checkids.js`: **126 ids referenced, 0 missing** (114 before; +12 new ids:
  `studio-dataset-message`, `studio-progress`, `studio-progress-message`,
  `studio-progress-elapsed`, `studio-progress-cancel`, `studio-source-summary` (now referenced),
  `studio-source-details`, `studio-reconcile`, `studio-scope-note`, `studio-inspector-count`,
  and the two already-present ids the new code reaches). No id was removed.
- `node --test mentat/app/tests/chart-studio-core.test.js`: **81 pass, 0 fail** (77 before, +4:
  2 for `quickAddZone`, 2 for the cycle maps). The 77 did not drop.
- `node --test mentat/tests/test_chart_studio_contributions.cjs`: 13 pass (12 before, +1 reconcile).
- `node mentat/tests/test_cross_reference_view.cjs`: passed (17 new assertions).
- `node --test mentat/tests/test_studio_wording.cjs`: 10 pass.
- `test_chart_math.cjs` 20 pass, `test_contribution_plot.cjs` 12 pass, `test_coverage_view.cjs` 1 pass.
- Playwright, all with
  `MENTAT_NODE_MODULES=C:\Users\pgoff\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules`:
  `test_studio_click_to_add_browser.cjs`, `test_studio_data_source_browser.cjs`,
  `test_studio_reconciliation_browser.cjs`, `test_studio_canvas_only_browser.cjs` — all pass,
  each asserting `errors` is empty (zero page errors).
  Backstop: `test_original_studio_contributions_browser.cjs`,
  `test_studio_temporal_regression_browser.cjs`,
  `test_studio_inspection_regression_browser.cjs`, `test_chart_comparison_browser.cjs`,
  `test_chart_builder_browser.cjs`, `test_contribution_export_browser.cjs` — all pass
  (full final sweep logged at `..\..\tasks\b20y7wyt2.output`).
- Theme discipline: every colour in the new CSS is an `acu-theme.css` token
  (`--acu-plum`, `--acu-purple`, `--acu-teal`, `--acu-ivory`, `--acu-paper`, `--acu-gold`,
  `--line`, `--muted`, `--chart-negative`). One literal remains — `#fdf5e4` on
  `.studio-note.is-warning` — which is the value the prompt pack names for it and the same gold
  tint `.studio-drop.is-over` already uses in this stylesheet. One correction along the way: my
  first draft wrote `var(--ink, #342649)`; `--ink` is not a token in this project, so it is now
  `var(--acu-plum)`.
- CSP (`default-src 'self'`): the diff adds **no** inline `style=` attribute and **no** `data:`
  URI; the `+` affordance is a CSS `::after` in the served stylesheet, and every new node is
  built with `document.createElement` and `textContent`.
- Line-ending class preserved in every file (byte census before and after):
  pure CRLF — `chart-studio.js`, `chart-studio.css`, `chart-comparison.js`;
  mixed mostly CRLF — `index.html` (2 lone LF), `chart-studio-core.js` (48), `graph.js` (22),
  `tests/chart-studio-core.test.js` (82);
  pure LF — `chart-studio-contributions.js`, `cross-reference.js`, every `mentat\tests\*.cjs`.
  `chart-studio-core.js` lone-LF count moved 52 -> 48 because four of the lines I replaced
  happened to be LF-terminated; edited lines take the file's default by design of the patch
  engine. The class (mixed, mostly CRLF) is unchanged.
- HTTP smoke on my own instance: `python server.py --port 8817 --read-only`, started with
  `Start-Process` (pid recorded, stopped by pid at the end; Paul's consoles and the other
  builder's 8816 instance were never touched). `GET /` -> 200 (54,919 bytes). **All 29 assets
  referenced by `index.html` -> 200.**
- Real-server browser smoke against 8817 (`smoke8817.cjs`): **0 page errors, 0 console errors,
  0 failed requests**; the folded summary reads `Data source · Banking · Published included
  receipts · ready`, the header button reads "Data source" and is visible, the default note is
  the new one, and the Group-limit label is the approved sentence.

---

## 4. Defects found while building, and fixed

1. **F3 — a prepare nobody could see.** The progress row lives inside the Data source panel,
   which F3 folds away after the first load, so the message, the elapsed timer and the Cancel
   button were all invisible exactly when a long prepare made them matter. `showProgress()` now
   opens the panel for the duration and `clearProgress()` returns it to where it was.
   (`step-f3-progress-visible.js`)
2. **F3 — a cancelled prepare could flash back.** The poll loop only checked its abort signal
   after the wait, so one more poll could re-show the row. It now checks before polling too.
   (`step-f3-abort.js`)
3. **F6 — the Inspector drawer covered its own toggle.** Below 1200px the Inspector is a
   `position:fixed` drawer; the rule that closes it was applied once at first paint, so a window
   resized down from wide left the drawer open on top of the toggle, which then could not be
   clicked at all. The same rule is now applied whenever the window crosses the breakpoint, and
   `aria-expanded` follows. (`step-f6-resize.js`)
4. **F4(c) — a false "not carried" line.** `graph-direction` defaults to `Support` (its first
   option; graph.js hides the control entirely while the candidate view is `direct`), so
   treating `''` as its default reported "Support or opposition: not carried" on every ordinary
   hand-off. Its default is now `Support`. (`step-f4-direction.js`)
5. **F2 — a click could put one field on two shelves.** Found in my own diff review and
   reproduced before fixing: with Columns `[Company]` and Rows `[SUM(amount)]`, clicking the
   Company pill in the Data pane chose zone `rows` (Columns is not empty) and `place()` only
   dedupes *within the target shelf*, so Company ended up on Columns **and** Rows — a state a
   drag can never produce, because the drop handler removes the pill from its source shelf
   first. A field that is already on Columns or Rows now answers a click with
   "&lt;Field&gt; is already on &lt;shelf&gt;." and is not duplicated; drag and the menu's Place
   group still move it. This is a small addition to the briefed F2 rule, made because the
   briefed rule alone produces an invalid shelf state. (`step-f2-dedupe.js`; asserted in
   `test_studio_click_to_add_browser.cjs`.)
6. **F3 — a prepare could close a panel the reader had just opened.** `showProgress()` opens the
   Data source panel and `clearProgress()` closes it again. If the reader pressed the header's
   Data source button while a prepare was running, that close still fired. An explicit open now
   clears the flag and wins. (`step-f2-dedupe.js`)
7. **F4 — an un-awaited `renderReconcile()`.** It is fired without `await` from
   `renderContributionView`, so anything throwing inside it after the Graph request would have
   become an unhandled rejection and could leave a stale strip on screen. A failure now hides
   the strip. (`step-f2-dedupe.js`)
8. **F3 — the `<details>` `toggle` event is asynchronous.** The summary line was refreshed only
   from that event, which the HTML spec queues as a task rather than firing synchronously, so
   code that opened or closed the panel itself left the summary describing the previous state
   until a later task ran — briefly showing the folded line over an open panel. It was latent
   until the F2 dedupe change shifted the timing and the data-source test caught it. Every place
   that changes `.open` now refreshes the summary itself; the `toggle` listener stays for the
   reader's own clicks. (`step-f3-toggle-race.js`)
9. **F4 — a stale Graph total could sit beside a fresh Studio total.** `graphTotalsCache` is
   keyed by the scope (run, industry, company, cycle, tier, funding) — exactly the key that does
   **not** change when "Refresh verified data" picks up a new workbook. The strip would then put
   a fresh Studio figure next to a cached Graph figure, which is the precise confusion it exists
   to remove. Refresh now clears it alongside `contributionCache` and `memberCache`.
   (`step-f4-refresh-cache.js`)
10. **F2 — the menu contradicted the click it mirrors.** After the dedupe, the Enter menu's
    first entry still read "Add to Rows" for a field already on Columns, and pressing it
    answered "… is already on Columns." One `placedOn()` helper now answers "where is it?" for
    both, and the menu entry says so up front in the popup's own disabled-with-a-reason idiom.
    (`step-f2-menu-consistency.js`)
11. **My own error, caught and repaired before it shipped.** The F6 badge rule was inserted at an
   anchor that turned out to be the second half of a grouped selector
   (`.studio-overview-toggle,\n.studio-inspector-toggle {`), which handed the overview button the
   badge's geometry and stripped the Inspector toggle's shared styling. Repaired in
   `step-f6-fix.js`; the full stylesheet diff against the backup is now purely additive.

---

## 5. Work outside the named file set (flagged for the coordinator)

1. `mentat\tests\test_original_studio_contributions_browser.cjs` — **my regression.** It drives
   `#studio-refresh-data` and `#studio-source-mode`, which now sit inside the folded Data source
   panel. The test opens the panel with the permanent header button, the way a reader does. Two
   inserted lines; behaviour otherwise unchanged. Backed up.
2. `mentat\tests\test_chart_comparison_browser.cjs` — **not my regression.** This suite was
   already red at HEAD: the `2906980d1` redesign renamed its toolbar control to "Canvas only in
   every chart" / "Builder in every chart" and the test still looked for "Hide all options" /
   "Show all options". `chart-comparison.js` is byte-identical to its pre-lane backup and to
   HEAD, so nothing in lane F-client caused it. I fixed the five label strings and opened the
   Data source panel before its two `#studio-destination` selects, so the backstop signal is
   usable. **If the coordinator would rather this stay with the redesign lane, revert it from
   `.bak-20260914-Fc` — the suite then goes back to red for a reason that predates this lane.**

---

## 6. Deviations from the brief, and what Paul may want to rule on

1. **F5 row 5 keeps its tail.** The approved NOW text is "This chart type needs individual
   receipts. Switch Data source to Report worksheet." The shipped string was longer than the
   table's WAS column quoted; I applied the approved sentence and kept the original's surviving
   clause, giving: *"This chart type needs individual receipts. Switch Data source to Report
   worksheet, or select Bar, Line, Circle, Text or Map."* The tail is the only place the console
   names the marks that do work here. **Say the word and I will strike it.**
2. **The reconciliation strip prints cents.** R3 draws "$12,090,412"; the shipped formatter
   (`contributionPlot.format`) renders currency with two decimals, so the strip reads
   "$12,090,412.00". The acceptance is agreement *to the cent*, so showing them is the honest
   choice, and a non-zero remainder can never hide. Trivial to elide if Paul prefers the render.
3. **R2 shows the export menu labelled "Export"; it still says "Download".** The rename is E0's
   (`index.html:187`), in the Export lane, not F6's. Deliberately left alone.
4. **R2 shows the Inspector button in Canvas only at desktop width; it is not shown.** The
   toggle is `display:none` above 1200px and `.studio-options-hidden .studio-inspector` is
   `display:none !important` — both pre-existing. F6's brief covers only `aria-expanded` and the
   badge, so I did not widen it. Worth a ruling before Ride 1 step 22–24.
5. **Group-limit label placement.** The brief said "Parameters placeholder". A number input's
   `placeholder` only shows while the box is empty and would clip a sentence, and the misleading
   claim ("default 40") lived in the `title`. I put the approved sentence in the `title` in both
   the markup and the verified runtime override, and left `placeholder="40"`. The number is
   unchanged.
6. **`selection` is now dead state.** F2 removes the only writer of the field-selection array
   (plain and ctrl-click), so `selection` is permanently `[]`; it is still reset in three places
   and read for the inert `.is-selected` class. I left it in place rather than widen the diff
   into `scan()` and `selectContributionDataset()`. A later lane should remove it, or restore
   ctrl-click multi-select if Paul wants that gesture back. **Ctrl-click multi-select for Show
   Me is gone** — that is what "Show Me selection reads shelves only" means in the brief, but
   it is a gesture a reader may have been using, so it is called out here rather than buried.
7. **The strip asks Graph its own question.** `graphTotals` sends the studio's company and
   cycle with the Graph's current tier and funding, but not Graph's in-page drill-down
   (`category`, `recipient`), which live only inside `graph.js` and are unreachable. If a reader
   has drilled into a category on the Graph tab, the strip's "Graph shows $X" is the undrilled
   figure for the scope it names. The strip states the scope, so it is not wrong — but it can
   differ from the number on the Graph screen.

---

## 6b. Adversarial pass on the money-critical part (F4), with each risk's status

| failure mode | status |
|---|---|
| float error turning a real difference into "Agree" | **not exposed.** `Math.round(giving * 100)` is exact for the 2-dp values `graph_data.money()` emits at any realistic total (cents stay far below 2^53); the Studio side is already integer cents. |
| "Agree" claimed across different questions | **not exposed.** `agree` requires basis `receipt` **and** a zero difference; the strip fires only when the sheet's row filters are exactly company/cycle; and `graphTotals` sends the Graph's own tier/funding, so a narrowed Graph shows as a difference with reason `graph_filter`, never as agreement. |
| a stale Graph total beside a fresh Studio total | **was exposed, now fixed** — see §4.9. |
| a strip left on screen after the view moves on | **not exposed.** The strip is hidden at the top of every `renderReconcile`, on a query error, and in worksheet mode; a late Graph response is dropped by the `contributionRevision` ticket, leaving it hidden rather than stale. |
| the strip spending the reader's query budget | **not exposed.** It calls the local read-only `/api/graph`, once per scope key, session-cached; `queryRequests` (the "verified queries this session" counter) is only incremented by `contributionAPI`, so the count still means what it says. |
| the reader's Graph drill-down changing the comparison silently | **partly exposed, reported** — see §6.7. `category` and `recipient` live only inside `graph.js` and cannot be read, so the strip names the scope it *did* ask for. |
| "totals cover all M" over-claiming under a grouped filter | **bounded.** `result.totals` describes row-filtered observations before the aggregate filter (`contribution_query.py:174`), so with a grouped filter the totals cover **at least** all M retained groups — the sentence stays true but reads more exact than it is. The engine's own caveat and "Grouped filters apply after aggregation." are already in the note beneath. Flagged rather than reworded, because the sentence is the briefed one. |

## 7. Skips and limits

- `chart-comparison.js` was backed up but **not edited** — nothing in F0–F6 needed it.
- The Graph footnote (`#graph-basis-note`) is asserted statically in `test_studio_wording.cjs`
  (markup id + the sentence in `graph.js`). Driving `graph.js` render() needs a full Graph view
  fixture; that belongs with the Graph lane's own browser test, not this one.
- No Python file was touched, so no `py_compile` was needed.
- No git command was run. No console process was started, stopped or inspected beyond a
  read-only census; the other builder's 8816 instance and the 8841 staffer server were left alone.
- `test_studio_wording.cjs` is a plain `node:test` file, not a Playwright test. It reads the
  shipped sources and exercises the pure modules, which catches a wording regression anywhere in
  the client without a browser. It needs no `MENTAT_NODE_MODULES`.
- Every new test is self-contained, following the house pattern of
  `test_original_studio_contributions_browser.cjs`; I did not add a shared fixture module.

## 8. Step files (replayable edit log, in order)

`apply.js` (this lane's copy of `redesign\apply.js` with the backup suffix parameterised), then:
`step-f0.js`, `step-f2.js`, `step-f2-tests.js`, `step-f3.js`, `step-f5.js`, `step-f6.js`,
`step-f6-fix.js`, `step-f4.js` (wrote `chart-studio-contributions.js`, then stopped on a stale
index.html anchor — **do not replay it**), `step-f4b.js` (the remainder, anchor corrected),
`step-f4-tests.js`, `step-f3-abort.js`, `step-f3-progress-visible.js`, `step-f4-direction.js`,
`step-f6-resize.js`, `step-backstop.js`, `step-f2-dedupe.js`, `step-f2-order.js`,
`step-f3-toggle-race.js`. New test files were authored under `newtests\` and copied into
`mentat\tests` with LF endings; `smoke8817.cjs` is the real-server smoke.

The hashes in §1 are final: recomputed after the last step, with `chart-studio.js`,
`test_studio_click_to_add_browser.cjs` and `test_studio_data_source_browser.cjs` updated to their
post-fix values. 13 `.bak-20260914-Fc` backups are on disk (9 under `mentatpp`, 1 under
`mentatpp	ests`, 3 under `mentat	ests`); none overwrote an existing backup.
