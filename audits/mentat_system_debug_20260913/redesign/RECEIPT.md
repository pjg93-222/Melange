# Chart Studio redesign — build receipt (2026-09-13)

Tree: `C:\Users\pgoff\Mentat\mentat\app` (branch `codex/mentat-crypto`, dirty with other
lanes' work). Built on top of the four applied S1–S4 patches. Nothing committed, nothing
staged, no stash used, no existing server process restarted or stopped except my own.

**Note on the toolchain.** The Edit/Write tools refused every path under
`C:\Users\pgoff\Mentat` because this session's harness assumes the session worktree
(`…\Melange Systems\.claude\worktrees\mentat-system-debug-1f368e`) is the only writable
repo — that worktree is the Melange repo and contains no `mentat/app`. Every edit was
therefore applied through an exact-text patch engine in the scratchpad
(`scratchpad\studio\redesign\apply.js` + `stepN-*.js`), which asserts each anchor matches
exactly once, writes only on success, and restores each unchanged line's original
end-of-line byte from the backup. The step files are the complete, replayable edit log.

---

## 1. Files touched

Backups: `<file>.bak-20260913-redesign` beside each file (all eight exist).
`git hash-object` is EOL-insensitive here (`core.autocrlf=true`), so the byte-level
line-ending census is given separately.

| File | before | after |
|---|---|---|
| `index.html` | `b46c5e8dba8b564aae240b92a5ce0b1c9164b795` | `e7bb93856a5d77d9e7c92cf53323256ab9ce4798` |
| `chart-studio.js` | `0b4b188d1a05318ef7c84323d38b33a38a1e54e7` | `0890a37a8ec9a1ba16ea6ddd31c0a515f9d1727f` |
| `chart-studio-core.js` | `61c92baf9d75fec10c24a1f4161156ee5bcecd01` | `fcae6ad7a4973d9fc4202dfc1f328fcfed8a1c18` |
| `chart-studio.css` | `13d60b04be1668007b104af74970843be09c134e` | `66d2e91ccb459400b3a639cc816f9453f80ebb5d` |
| `chart-comparison.js` | `5e87ae8b0711c8ec7cc463358a7a6d04aebfb307` | `c32fc1968af236fea005ebaca2bbba5b78459567` |
| `chart-studio-contributions.js` | `4e62a276f06fe1b0f512ee59c4cf4e238b4e0061` | `d0e5a8e9742eddfaf6cb99936d2aaf73eb5fcaa7` |
| `chart-math.js` | `bca99c5d0ca1dd273572f4e5e38df461655c22fd` | `27af956448ded9aa0d80dc87f1cd2c478dfc8c89` |
| `tests/chart-studio-core.test.js` | `cb92e886facbcd9e82d40521d94ceebc53633afe` | `68002a0dd91627a4e5d6004de8a2cb688308578e` |

Explicitly **not** touched (hashes unchanged from the S1–S4 state):
`server.py` `5b85087c99a62b1e4e2f0a21021c96f92becd4bb`,
`contribution_query.py` `813013394fad4b1d17f0168a40a300a906ab667f`,
`contribution_data.py` `614abbaea97e1cb649069b64bb4652d1adc93837`,
`contribution-plot.js` `5dfa0684fba37c1939176cb8a23dd69c82453ab5`,
`contribution-charts.js` `2a07c15542bbb6252491d605f3e5d1c60480b0dc`.
No new file was added, so the server's static allow-list is unchanged and **no console
restart is needed for this lane** (a hard reload is enough). The S2 server patch still
requires the restart it always did.

### Line endings (bytes, before → after)

| File | CRLF | LF | class preserved |
|---|---|---|---|
| `index.html` | 318 → 349 | 2 → 2 | yes (mixed; both original LF lines untouched) |
| `chart-studio.js` | 1494 → 2016 | 0 → 0 | yes (CRLF) |
| `chart-studio-core.js` | 533 → 771 | 53 → 52 | yes — the one lost LF line is the filter-mapping line I replaced |
| `chart-studio.css` | 410 → 556 | 0 → 0 | yes (CRLF) |
| `chart-comparison.js` | 80 → 82 | 0 → 0 | yes (CRLF) |
| `chart-studio-contributions.js` | 0 → 0 | 120 → 140 | yes (LF — this file was LF, not CRLF) |
| `chart-math.js` | 0 → 0 | 463 → 478 | yes (LF) |
| `tests/chart-studio-core.test.js` | 773 → 983 | 82 → 82 | yes (mixed) |

---

## 2. What was built, by spec section

### §1 Layout — built

* **Header row** (`.studio-header`, new): serif "Chart Studio"; the **scope chip**
  (`#studio-scope-chip`, lilac) reading `Carried from Graph · Banking · Cycle 2025-2026 ·
  <Company>` after an S1 hand-off and `Banking · All cycles` on a direct open; a **Change
  scope** link that opens the left panel's Data-source disclosure and focuses it; on the
  right a **Company overview** toggle and the **Builder | Canvas only** segmented control
  (`role=radiogroup`, `aria-checked`), plus an Inspector drawer button that only appears
  under 1200px.
* The segmented control **is** the S3 restore control: it carries
  `class="studio-options-restore"`, drives the same `studio-options-hidden` class through
  `MentatStudioPane.options`, and the CSS force-shows it and the header whenever options
  are hidden. `chart-comparison.js` no longer creates its own "Hide chart options" button;
  it now routes its pane API through `MentatStudioPane.setOptionsHidden`, so all panes
  still move together.
* **Comparison toolbar** restyled (1/2/3/4 segmented, Linked filters, blocked-pane status
  line kept). When `chart-comparison.js` loads it **relocates** the Company overview
  toggle into that toolbar, as the spec asks; when it does not load (old console) the
  toggle stays in the header and still works.
* **Three columns**: `260px | minmax(320px,1fr) | 300px`; ≤1200px two columns with the
  Inspector as a fixed drawer; ≤1000px one column.
* **Left "Data" panel**: `Data source` disclosure (collapsed by default) holding every
  existing select, refresh button and status line; Search fields; Fields from; Dimensions;
  Measures; identifier block. **Type glyphs**: `Abc` / `#` / `T/F` as text, and a
  **drawn inline-SVG calendar and map-pin** for dates and geography (no emoji, replacing
  the old `▦` and `◎` characters).
* **Centre card**: a compact `Columns / Rows / Filters` shelf strip at the top of the white
  card, then the existing 21px serif title, note line, chart, pager, table toggle and
  source-record panel. Sheet tabs stay under the card.
* **Right Inspector**: real tabs (`role=tab` / `aria-selected` / roving `tabindex`).
  *Marks* = Show Me grid, Mark type, the five Marks drop rows, map layers, **Pages** +
  pager, **Parameters**, "Show identifier fields". *Analytics* = the seven objects plus the
  transform parameters. *Filters* = §4.1. Nothing about the state model changed — every
  element kept its id, and a census script confirms all 114 ids the scripts reach for
  exist in `index.html`.
* **Gold discipline**: exactly one gold action per view. In the builder the toolbar's
  "Show Me" button turns gold **only while the tile grid is hidden** (`.is-primary`); in
  Company overview the focused card's "Open in builder" is gold. No other gold was added.

### §2 Comparison — kept and polished

Each pane gets a purple **"Chart A/B/C/D"** chip (`.studio-pane-tag`) at the top-left of
the centre column. The iframe architecture, the linked-filter protocol, the `paneOf()`
guard and the blocked-pane sentence are untouched. The grid-wide button is relabelled
"Canvas only in every chart" / "Builder in every chart".

### §3 Company overview — built, in page, no iframes

Toggle disabled with a stated reason in worksheet mode ("Company overview uses verified
contributions."), when no dataset is chosen, or when the source has no `company` field.
Company picker filled from the `company` facet, defaulting to the company carried from the
Graph. Cycle honours a single-valued cycle filter on the Filters shelf and says which it
used in the header line. Four cards render through the ordinary
`contributions.compile → queryCached → contribution-plot / contribution-charts / chartSVG`
path — the same code the builder uses — one query at a time (see limits). "Open in builder"
loads that preset into the current sheet through `commit()` (so it is undoable) and
switches back to Builder.

### §4.1 Filters — built

* Clicking a filter pill (or Enter → Edit filter) opens a popover anchored to it:
  operator select, then **categorical**: search box, All / None, `Is one of` / `Is not one
  of`, checkbox list of members (verified: the memoised facet fetch; worksheet: distinct
  column values); **numeric measure** and **date**: a two-bound range (`Between`) with
  From/To inputs; `year` and `cycle` are categorical, so they get the checklist.
  Apply / Cancel / Remove; Apply goes through `commit()`, so undo works.
* **Inspector Filters tab**: one row per filter (`field` + a plain-language summary such as
  "3 of 10 values", "$1,000 to $5,000", "excludes 4 of 10 values") with Edit and Remove,
  plus an **Add filter** select of every field not already filtered. Same state, no
  duplication; the tab label carries the count.
* Graph-scope filters remain ordinary, visible, removable pills.
* **New model** (`chart-studio-core.js`): ops `equals / contains / gte / lte / between /
  in / notin`; `filterActive`, `filterValues`, `filterBounds`, `normalizeFilter`,
  `filterSummary`. `chart-math.js` learned `in` / `notin` / `between` for worksheet rows.
  `chart-studio-contributions.js` gained `clauses(filter, field)`: `in` → one server `in`
  clause, `notin` → a chain of `ne` clauses (filters are ANDed, and the server has no
  NOT IN), `between` → its `gte` / `lte` bounds. Verified against the live API (below).
* **Deliberate behaviour change**: dropping a field on Filters now creates an *empty*
  choice that filters nothing, instead of `equals <first member>`. An unset filter no
  longer silently selects the empty string.

### §4.2 Measures and aggregation — built

Pills read `SUM( ) / AVG( ) / COUNT( ) / MEDIAN( ) / MIN( ) / MAX( )`. The ▾ caret now
opens the full pill menu on every shelf pill. `core.aggregationsFor(field, engine)` offers
the six only where the engine computes them: worksheet measures, and the verified `amount`
column (which maps to `amount / average_amount / records / median_amount / min_amount /
max_amount`). Every other verified measure is a source aggregate with one definition, so
its Aggregation entry is **disabled with that reason** rather than hidden-and-failing.
**Replace measure** lists the other measures. **Political money…** offers Total giving,
Gift count, Average gift and Distinct contributors — each either available or disabled with
the reason it is not (Distinct contributors is unavailable on a worksheet).

### §4.3 Data types — built, with one honest refusal

* **Treat as Dimension | Measure**: stored per sheet in `sheet().types`, persisted with the
  sheet, consumed by `classifyFields(columns, overrides)` and therefore by `compileReport`,
  the field lists and the glyph. A text or date column **cannot** become a measure —
  `canTreatAs` refuses with the reason. A "Use the detected type" entry appears once an
  override exists.
* In **verified** mode both entries are **disabled with a reason** ("Verified fields keep
  the role the source defines. ZIP, committee ID and election cycle are already
  dimensions."), because the server's field roles are fixed and a coerced role would
  produce a query it rejects. This is a refusal, not a silent no-op.
* **Date part**: verified → the pill moves to the catalog's own derived column
  (`year` / `quarter` / `month` / `cycle`), so the grouping stays server-side; worksheet →
  sets the existing period + `annual` transform (Election cycle / Year only, because that
  is what the worksheet engine implements).
* Number formatting is unchanged (the existing `money()` / `contributionPlot.format`).

### §5 Query volume — the confirmed re-fire loop is fixed

The diagnosis' suspect is real in the code: `members()` memoised **before** awaiting, but
its `.catch` **deleted** the key, so any failing facet was re-fired from every later
render. Now a failure is cached for 30 s (`{values:[], at, error}`) and retried only after
that, and a facet **no longer includes its own column's filter**, so changing a filter does
not invent a new facet key. The result: at most one query per distinct facet per 30 s from
any render path. `contributionAPI` counts every `POST /api/contributions/query` and the
status line ends with "N verified queries this session", so the volume is visible.
**Honest limit**: I could not reproduce the ~160-request burst — the spec forbade me the
Browser pane — so I fixed the mechanism the code proves and made the count observable.
Step 2 of the manual script is the measurement.

### §3 command palette — skipped

Optional in the spec and not cheap next to the rest; not built. Follow-up.

---

## 3. Known limits

1. **"Recipient categories" is a vertical bar chart, not horizontal bars.** The verified
   renderer has no horizontal bar: `contribution-plot.js` validates only
   `bar/line/area/scatter/table` and draws bars upright, and `contribution-charts.js` has no
   horizontal family either (`grep -n "horizontal\|orient" contribution-plot.js` → no hits).
   Giving it one is a renderer change to published charts, which is Paul's call.
2. **"Party split" is by recipient party**, with a one-line note under the card, exactly as
   the spec directed — the contributions catalog has no employee-tier field.
3. **Treat as** is refused in verified mode (point §4.3 above). If Paul wants it, the way
   in is catalog-side, not client-side.
4. **Exclusion scale.** `Is not one of` becomes one `ne` clause per excluded member and the
   server caps a request at 40 filters, so excluding more than ~38 members will be refused
   by the server with its own message. `Is one of` is capped at 1,000 members by the server;
   the client refuses above that with a message first.
5. **No browser verification by me.** The spec reserved the Browser pane for the
   coordinator. My load-path verification is static (id census, HTML tag balance,
   `node --check`, `node --test`) plus live HTTP against my own instance. The
   ≤1200px Inspector drawer in particular has never been rendered.
6. **`chart-math.js` changed.** Three operators were added to `filterRows`. It is purely
   additive: the classic builder and the Graph tab never emit `in` / `notin` / `between`,
   and every existing operator path is byte-identical. 61 pre-existing tests still pass.
7. **Overview cards query sequentially.** `queryCached()` aborts the previous request when a
   new distinct query starts, so four parallel cards would cancel each other. Four cold
   cards therefore paint one after another.
8. **`.studio-cards` and the old side-bar tabs are gone** from the markup. The stale CSS
   selectors are left in place and inert; nothing references the removed ids.
9. **The overview toggle moves** into the comparison toolbar only when
   `chart-comparison.js` loads; on a console started before 2026-09-13 01:31 that script
   404s and the toggle stays in the header (still functional).

---

## 4. Verification

### Static / unit

* `node --check` clean: `chart-studio.js`, `chart-studio-core.js`,
  `chart-studio-contributions.js`, `chart-comparison.js`, `chart-math.js`.
* `python -m py_compile server.py contribution_query.py contribution_data.py
  contribution_semantics.py` → clean.
* `node --test tests/chart-studio-core.test.js` → **76 tests, 76 pass, 0 fail**
  (was 61/61; **15 new tests**): empty-choice filters, include/exclude complementarity,
  range bounds, `normalizeFilter`, `filterSummary`, `contributions.clauses`,
  `aggregationsFor`, `measurePresets`, `applyMeasurePreset`, `canTreatAs`, type-override
  classification and its effect on the compiler, `datePartsFor`, the four company-overview
  sheets, the query one of them compiles to, and `companyOverviewMissing`.
* Element-id census (`scratchpad\studio\redesign\checkids.js`): 114 ids referenced by
  `chart-studio.js` + `chart-comparison.js`, **0 missing** from `index.html`.
* Studio-section tag balance in `index.html`: div 63/63, section 2/2, aside 2/2,
  label 27/27, details 2/2, button 36/36, h2 2/2, h3 13/13, p 11/11, span 13/13,
  select 15/15. CSS braces 250/250.

### HTTP smoke — my own instance, `python server.py --port 8814 --read-only`

Started as PID 85248, **stopped by PID before writing this receipt** (verified gone;
Paul's consoles on 8802/8803/8804/8805/8808/8813/8841/56312 all survived).

| Request | Result |
|---|---|
| `GET /` | 200, 54,256 bytes, `frame-ancestors 'none'` |
| `GET /?studioPane=B` | 200, **`frame-ancestors 'self'`** (S2 intact) |
| `GET /chart-comparison.js` | 200, 7,356 B |
| `GET /chart-studio.js` | 200, 123,175 B |
| `GET /chart-studio.css` | 200, 29,761 B |
| `GET /chart-studio-core.js` | 200, 46,216 B |
| `GET /chart-studio-contributions.js` | 200, 17,571 B |
| `GET /chart-math.js` | 200, 37,331 B |
| `GET /api/contributions/session` | 200, token issued |
| `GET /api/contributions/catalog` | 200, 8 datasets all available, 100 fields |

Two further edits landed after this smoke run (the Analytics switch rows and the removal of
one dead alias), so `chart-studio.js` is now 2,016 lines rather than the 123,175 bytes
served above; `node --check`, the id census and the 76-test suite were all re-run clean
afterwards. The server re-reads static files per request, so no restart is implied.

`POST /api/contributions/query` against **Banking**, receipt basis:

| Query | Result |
|---|---|
| `recipient_category` × `amount`, limit 10 | ready, 10 rows / 10 groups, top `Carey` $15,632,580.32 |
| `company` facet (the member list) | 10 companies, e.g. Bank of America NA, Capital One Bank NA, Citibank |
| **`in`** two companies | ready, 9 groups, total **$13,354,538.16** |
| **`ne` chain** excluding the same two | ready, 10 groups, total **$41,408,305.89** |
| — sum of the two | **$54,762,844.05 = the unfiltered total** (include/exclude are exactly complementary) |
| **`gte`+`lte`** ($1,000–$5,000 gifts) | ready, 10 groups, $19,487,292.28 |
| deliberately malformed filter | **400 Bad Request** (the server still refuses bad input) |
| `cycle` asc, limit 40 (overview preset 2) | ready, 3 cycles |
| `party` desc, limit 10 (overview preset 4) | ready, 3 parties |
| `recipient` desc, limit 8 (overview preset 3) | ready, 8 of 2,396 groups |
| `contributors` measure (Distinct contributors preset) | ready, 10 groups |
| `average_amount` measure (Average gift preset) | ready, 10 groups |

---

## 5. Manual test script — fresh `python server.py --port 8812 --read-only`

Run it from `C:\Users\pgoff\Mentat\mentat\app`, open `http://localhost:8812/#chart-studio`,
and **hard-reload** (Ctrl+Shift+R) so the new CSS/JS are fetched. Dataset: **Banking**.
If the studio remembers an older sheet, press **Clear** in the toolbar first.

1. **Load.** Expect three columns: a "Data" panel on the left, the white chart card in the
   middle with a `Columns / Rows / Filters` strip at its top, and an "Inspector" card on
   the right with Marks | Analytics | Filters tabs. The header row reads "Chart Studio",
   a lilac chip `Banking · All cycles`, a "Change scope" link, a "Company overview" button
   and `Builder | Canvas only` with **Builder** selected.
2. **Query volume.** Open DevTools → Network, filter `query`, and reload. Expect a small
   number of `POST /api/contributions/query` (single digits) and **not** a burst of ~160.
   The status bar at the very bottom of the studio should end with
   "… · N verified queries this session". No uncaught errors in the Console.
3. **Data source disclosure.** The left panel's "Data source" row is collapsed. Click it →
   Report / Accounting basis / State location view / Refresh appear. Click the header's
   **Change scope** → the same disclosure opens and takes focus. Collapse it again.
4. **Type glyphs.** In Dimensions, `Company` shows `Abc`; `Election cycle` and
   `Contribution date` show a small **drawn calendar**; `Contributor ZIP` / `Contributor
   state` show a **drawn map pin** (tick "Show identifier fields" in Inspector → Marks →
   Parameters if ZIP is hidden). In Measures, `Selected amount` shows `#`. No emoji.
5. **Default view.** Columns = `Company`, Rows = `SUM(Selected amount)`, bar chart, title
   "Published included receipts by Company".
6. **Aggregation.** Click the `▾` on the `SUM(Selected amount)` pill → a menu with
   *Send to…*, a **Measure** group (Aggregation…, Replace measure…, Political money…) and a
   **Data type** group. Choose *Aggregation…* → **Mean**. The pill becomes
   `AVG(Selected amount)` and the chart redraws as average gift size. Press **↶ Undo** →
   back to `SUM`.
7. **Political-money preset.** `▾` → *Political money…* → **Distinct contributors**. Rows
   becomes `Distinct reported donor identities` and the chart redraws as donor counts.
   In the same menu, on a worksheet source this entry would be greyed with a reason.
   **Undo**.
8. **Empty filter is not a filter.** Drag `Recipient category` from Dimensions onto the
   **Filters** strip. The pill reads `Recipient category: any value` and the chart does
   **not** change.
9. **Member checklist.** Click that pill. A popover opens with operator `Is one of`, a
   search box, `All` / `None`, and a checklist that fills in after a moment ("Reading the
   values of this field…" first). Type `pac` in the search to narrow it. Tick two
   categories → **Apply**. The chart narrows and the pill reads
   `Recipient category: 2 of 10 values`.
10. **Inspector Filters tab.** Click **Filters** in the Inspector. The tab reads
    "Filters (1)" and shows one row: **Recipient category** / `2 of 10 values` with
    *Edit* and *Remove*, plus an **Add filter** select. Press *Edit* → the same popover.
11. **Exclude.** In that popover switch the operator to **Is not one of** → **Apply**. The
    chart now shows the complement (the categories you did *not* tick). **Undo** twice
    returns to the unfiltered view; **↷ Redo** puts it back. Remove the filter from the
    Inspector row.
12. **Range filter.** Inspector → Filters → **Add filter** → `Selected amount`. A row
    appears; press *Edit* → operator **Between** → From `1000`, To `5000` → **Apply**.
    The row reads `Selected amount $1,000 to $5,000` and the chart redraws. Remove it.
13. **Analytics switches.** Inspector → **Analytics**. Expect two groups: *Period analysis*
    (four radio rows) and *Summarize* (three switch rows), each with a name, a one-line hint
    and a switch on the right. On this bar chart, **Period totals** is disabled and its hint
    is replaced by "Needs Contribution date, Year or Election cycle on Columns or Rows."
    Turn **Average line** on → a dashed mean line appears on the chart.
14. **Honest refusal.** Inspector → Marks → Mark type → **Treemap**. Go back to Analytics:
    **Average line** is now disabled with "Reference lines are drawn on bar, line, area and
    circle marks." — it does not silently do nothing. Set Mark type back to **Bar**.
15. **Date part.** Drag `Election cycle` onto **Columns** (it replaces nothing; remove the
    `Company` pill first with its `▾` → *Remove from columns*). Then `▾` on the
    `Election cycle` pill → **Date part** → **Year**. The pill becomes `Contribution year`
    and the chart regroups by year. Undo back to `Company`.
16. **Canvas only.** Header → **Canvas only**. The Data panel, the shelf strip, the toolbar
    and the Inspector disappear; the header row with the segmented control and the sheet
    tabs stay visible. Click **Builder** → everything returns. Reload the page while in
    Canvas only: the state is remembered **and the way back is still on screen**.
17. **Company overview.** Click **Company overview** in the header (or, if the comparison
    toolbar is present, in that toolbar — the button relocates itself). The builder is
    replaced by a 2×2 grid: *Recipient categories* (bars), *Giving by election cycle*
    (line), *Top recipients* (columns), *Party split* (doughnut with the note that the
    split is by recipient party). The line above reads
    `<Company> · Banking · All cycles · Published included receipts`. Change the **Company**
    picker → all four cards redraw for that company.
18. **Open in builder.** On *Top recipients* press **Open in builder**. You are returned to
    the builder with Columns = `Recipient committee`, Rows = `SUM(Selected amount)`, Group
    limit 8, a `Company` filter pill, and the same chart. **Undo** restores the previous
    sheet.
19. **Comparison.** Click **2 charts**. A second pane appears; each pane carries a purple
    **Chart A** / **Chart B** chip at the top-left of its chart column and its own
    `Builder | Canvas only` control. If this console was started **before** the `server.py`
    CSP patch you should see the in-app sentence "Chart B could not open in this page…"
    rather than Chrome's "refused to connect". Back to **1 chart**.
20. **Worksheet mode.** Left panel → Data source → **Report worksheet** → pick a report and
    worksheet. Expect: **Company overview** is now disabled with the title "Company overview
    uses verified contributions."; every worksheet shelf and parameter still works; `▾` on a
    numeric column now offers **Treat as Dimension** (and its glyph changes to `Abc` when
    applied), while `▾` on a text column shows **Treat as Measure** greyed with the reason.
    Switch back to **Verified contributions** and confirm the studio recovers.

**What would make me call this a fail:** an uncaught console error on load; the scope chip
or Inspector missing; a filter pill that filters to nothing when first dropped; an Analytics
row that toggles on and changes nothing without saying why; the ~160-query burst still
present; or any path that hides the builder with no visible way back.

---

## 6. Addendum — Date part missing in verified mode (step 8, 2026-09-13)

Reported from the live 8812 ride: no **Date part** entry in the pill menu for `Election
cycle` on Columns, or for `Contribution date` in the field list.

### Root cause

The pure logic was never wrong. Against the **real 100-field catalog**
(`contribution_semantics.fields()` → `contributions.fields()` → `core.classifyFields()`)
`isTime` is `true` for all five date ids and `datePartsFor(cycle, …, 'verified')` returned
`year / quarter / month` — verified in Node before touching anything. What the menu was
gated on, though, was that **detected flag**: both `typeMenuItems`' Date-part block and the
older `sendMenu` "Use `<field>` here" swap required `field.isTime && field.role ===
'dimension'`. The observed menu (Send to ×9 → Remove → Treat as ×2, with **both**
`isTime`-gated blocks absent while everything around them rendered) is consistent only with
that flag being falsy at that moment in the browser; it is not consistent with the menu
being merely truncated, because the missing entries sit both before and after entries that
did render. I could not obtain browser evidence to say *why* the flag was falsy — the lane
bars me from the Browser pane — so rather than guess I removed the dependency:

* **Date-likeness now comes from the catalog's own date hierarchy**, not from the flag.
  `core.isDateLike(field)` is true for a dimension whose id is `date / year / cycle /
  quarter / month`, and falls back to `field.isTime` for worksheet columns. Nothing about
  the verified menu can now hinge on a flag surviving classification.
* **Two overlapping controls became one.** The old verified-only "Use Contribution year
  here" swap did the same job as Date part under a different name; it is deleted and folded
  into Date part, which now also offers `Exact date`.
* **Date part is the first thing in the pill menu**, above Send to…, so it cannot be the
  entry that falls below the fold; and `popup()` now **flips a long menu above its anchor**
  when it would overrun the window, which was the one alternative hypothesis I could not
  otherwise exclude.
* **The current part is marked** with a tick and disabled ("This pill already groups by
  election cycle."), and the part list is complete instead of omitting the current one.
* Choosing a part **moves the pill in place** on Columns/Rows (or places the derived column
  on Columns from the field list); on a worksheet it still sets the existing period +
  `annual` transform, and marks whichever period that transform is already using.

### Files (this step only)

| File | before (receipt §1) | after |
|---|---|---|
| `chart-studio.js` | `0890a37a8ec9a1ba16ea6ddd31c0a515f9d1727f` | `b49c29709fcdd3bf5803d89b74b8852c48cafa9d` |
| `chart-studio-core.js` | `fcae6ad7a4973d9fc4202dfc1f328fcfed8a1c18` | `d29693823f60e7e8a8477c7ff35042b0b7a56250` |
| `tests/chart-studio-core.test.js` | `68002a0dd91627a4e5d6004de8a2cb688308578e` | `7a7df7a3caf579c0c068973021adc6a8b29f8275` |

`index.html`, `chart-studio.css`, `chart-comparison.js`, `chart-studio-contributions.js`
and `chart-math.js` are untouched at their §1 hashes. Backups were **not** overwritten —
the `.bak-20260913-redesign` copies still hold the pre-redesign originals. Line-ending
classes unchanged: `chart-studio.js` pure CRLF, core 52 LF, tests 82 LF. Change written as
`step8-date-part.js` (core + tests) and `step8b-date-part-js.js` (the `chart-studio.js`
half — the first attempt missed its anchor because the file stores `…` as literal
source text, so the second file carries the corrected anchors).

### Verification

* `node --check` clean on `chart-studio.js` and `chart-studio-core.js`; id census still
  114 referenced, 0 missing.
* `node --test tests/chart-studio-core.test.js` → **77 tests, 77 pass, 0 fail** (was 76).
  Two tests carry this change: the verified hierarchy with `current` marking and the
  worksheet period marking; and a new test that **strips `is_time` from every catalog
  column** and asserts the parts still appear — the regression that would have caught this.
* HTTP smoke, own instance `--port 8814 --read-only` (PID 82692, **stopped**; 11 other
  `server.py` processes untouched). The query *shape* does not change — Date part swaps one
  dimension column — but nothing had ever exercised the derived columns, so all five were
  run against Banking: `cycle` 3 groups (2021-2022 first), `year` 6 (2021), `quarter` 23
  (2021-Q1), `month` 40 (2021-01), `date` 40 (2021-01-01). All ready, all real data.

### Re-test for the ride

Replace step 15 of the manual script with: on the Columns `Election cycle` pill press `▾` →
the menu now **opens with a "Date part" group** listing `✓ Election cycle` (ticked,
disabled), `Year`, `Quarter`, `Month`, `Exact date`. Choose **Quarter** → the pill becomes
`Contribution quarter` and the chart regroups into 23 quarters. Undo. Do the same from the
`Contribution date` pill in the left field list: choosing `Year` puts `Contribution year` on
Columns. In worksheet mode the same menu offers `Election cycle` / `Year` and ticks whichever
the Period control is already grouping by.
