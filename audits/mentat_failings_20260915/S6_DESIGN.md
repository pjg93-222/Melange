# S6 - PAC evidence v2: one scope bar, PAC panes, cross-industry comparison (design)

Session: Fable, 2026-09-17 (worktree pac-evidence-filters-724237; code in C:\Users\pgoff\Mentat,
branch codex/mentat-crypto, HEAD ea222fadb at design time). Status: DESIGN, awaiting Paul's rulings.
Nothing in the tree is edited by this document. Builds on S7 (categories, filter, corporate rows,
committed 882f1f93f) and takes the S6 slot the HANDOFF reserved for the two-pane model.

Paul's brief: "go over the UI for PAC Evidence and clean it up, we also want it to be similar to
Graph in that there are cross comparisons between different PAC's between Different Industries,
the aim is ease of use and depth of information" and "I don't want a video, I want a UI update".

## 1. What the tab is today (index.html 340-374, evidence-csv.js, app.js 395-560)

1. Two disjoint workspaces switched by a top select ("CSV file" / "Saved FEC snapshots"), each with
   its own headings ("PAC evidence", "Saved FEC snapshots", "Company -> PAC -> candidates"),
   controls, status lines and empty states. The split follows the data plumbing, not the question
   a reader asks (which PAC, what it received or spent, compared with what).
2. The import picker is injected by JS above the panel; file chooser, path box, Browse panel and
   the status line stack vertically. One status line carries scope facts, progress and errors.
3. One PAC at a time. No side-by-side view, no cross-import view. Comparison exists only in Graph
   (`#compare-panel`, `/api/comparison`: subjects x cycles x giving breakdown, chips, `mentat:graph`).
4. The results panel is one long column: title, scope sentence, totals cards, disclaimer, file
   details, rows table with pagination. Depth is there (rows) but no summary above it: no top
   contributors, no per-cycle shape.
5. Snapshot workspace: the collector form sits in a `<details>` at the top; "Follow Graph
   selection" hides in a select; the cash-estimate panel and candidate table are deep but unrelated
   to imports.
6. Wording drift: "FROM YOUR SELECTED FILE", "Reported activity", "need interpretation".

## 2. Proposed shape (mirrors Graph's scope grid + compare panel; keeps the console theme)

A. SCOPE BAR, one panel, one grid row (Graph's `graph-filter-grid` pattern):
   Source (imports labelled by industry: "Crypto - Spending Overview - 6,343 rows", "Credit Union
   - ...", "Snapshot - Coinbase 2024-2026") | Committee type | Find a PAC | PAC | Cycle |
   [Add pane] | [Import file v] drawer (choose file / path / browse) | [New snapshot v] drawer
   (the collector form; disabled without a key). Below it a chip row of the open panes
   ("FAIRSHAKE - Crypto - 2024" x), like Graph's category chips. One `role=status` region for
   progress and errors only; scope facts move into the pane headers. "Follow Graph" is a toggle in
   the bar: when on, pane A tracks Graph's company and cycle through the snapshot catalog (the
   existing `mentat:graph` consumer), and the chip says so.

B. PANE GRID (`.evidence-panes`, grid auto-fit minmax(320px, 1fr), up to 4 panes; one column in
   Split-with-Graph): each pane card =
   - header: PAC name, ID, category badge (source on hover), industry/file label, per-pane cycle
     select (defaults to the bar's cycle), remove, "Rows" toggle;
   - figures for the pane's cycle: channel totals (Receipts; Disbursements, Independent spending
     support/oppose when present), supported / excluded counts, and a per-cycle mini bar row
     (2022 / 2024 / 2026) so the shape across cycles reads at a glance;
   - top counterparties (top 5 by amount with amounts): for imports the contributors to this
     recipient (people and companies); for snapshots the company receipts, transfers and a
     candidate-activity summary (support / oppose totals and counts);
   - provenance line (file name, sha short, warnings count) opening the existing file-details text;
   - the existing paginated rows table, collapsed inside the pane; excluded rows carry a visible
     badge "excluded by the workbook" instead of small text.

C. COMPARISON STRIP (appears with 2+ panes; Graph's "Compare funding" idiom): a table, rows =
   metrics, columns = panes, each numeric cell with an inline bar normalised per row so magnitude
   differences across industries read honestly (Fairshake $178M next to CULAC $37K stays a long
   bar next to a sliver, with the number beside it). Metrics: Receipts (bar cycle), Receipts by
   cycle (2022/2024/2026), other channels when present, rows supported / excluded, top
   counterparty, category, source. "Send to Chart Studio" is phase 2.

D. URL STATE (D-039; HANDOFF prefix rule): prefixed pane keys `a.source, a.id, a.committee,
   a.cycle` ... `d.*`, plus the existing `category` (same vocabulary as Graph) for the bar's type
   filter; search text stays transient. The single-pane keys `evidence, id, committee, offset,
   limit` reserved for S6 are superseded by the prefixed set (never written). Only scope.js writes;
   replaceState; defaults absent. Contract url_scope.json v2 with examples and negative controls.

E. SERVER (small, additive): (1) `GET /api/evidence-csv?id&committee&cycle&summary=1` ->
   `{committee, cycles, totals_by_cycle, counterparties[top 10: name, amount, rows], counts}`
   computed from the import's sqlite for that committee (bounded by its row count; ACTBLUE's 2,155
   rows are milliseconds); (2) the listing gains `industry` derived from the Mentat workbook name
   pattern `<Industry> Industry Spending Overview|Data.xlsx` (blank otherwise); (3) nothing else;
   the comparison is client-side from pane summaries. Contract evidence-csv-import.json v4.

F. CLEANUP: one heading; the CSV/snapshot select and the JS-injected picker go; import controls
   into the drawer; one status region; per-pane "About these figures" popover replaces the
   repeated disclaimer paragraphs; consistent number formatting; chips and remove buttons keyboard
   operable and labelled; 44px targets; empty state names the two actions (import a file, choose a
   snapshot). The console's own palette and type stay (acu-theme.css); no retheme.

G. NOT IN THIS LANE (phase 2, S6b): registering ready imports as Chart Studio data sources
   (committee, category, cycle, channel, amount, date, counterparty), and any change to the
   collector itself.

H. MAP MENU (Paul, 2026-09-17: "an instant map menu, where we match it to its congressional
   district using GeoPy and politicsnlp"). Checked: `politicsnlp` (PyPI 0.0.21, 2023) is a
   vocabulary library for political concepts; it does no geocoding and knows no districts, so it
   cannot do this job. `geopy` is a geocoder client (Nominatim, ArcGIS, ...) and returns
   coordinates, not districts. Neither is installed in either console Python. The stack that does
   the job, all free:
   - Money TO candidates: the FEC candidate master already in the repo
     (`inputs/fec_beneficiary/cn22|cn24|cn26`, CAND_OFFICE_ST + CAND_OFFICE_DISTRICT) for
     Candidate-category recipients and for IE targets in snapshots. Local, exact, instant.
   - Money FROM contributors, instant layer: ZIP -> district through the Census ZCTA-to-119th-CD
     relationship file (shipped with the console); a ZIP that straddles districts is split by the
     file's shares and marked "split". Local, instant, approximate and labelled so.
   - Money FROM contributors, precise layer: street address (the Data workbook carries Street 1/2,
     City, State, Contributor ZIP) -> the Census Geocoder `geographies` endpoint, which returns
     the 119th Congressional District directly (no key; ~2 requests/s; cached by normalised address
     under the console data root; one background job per import, resumable, never blocks the page).
     GeoPy is optional here: with `geopy` installed the same job can use Nominatim or ArcGIS for
     coordinates and a local point-in-polygon (shapely) against the Census cartographic district
     file; the Census endpoint needs neither package. Recommendation: Census Geocoder first; GeoPy
     as a fallback provider behind the same cache.
   - Drawing: 119th Congress boundaries from the Census cartographic file converted once (dev
     time) to static SVG paths in an Albers USA projection and shipped under `app/geo/`
     (`cd119.json`, about 1 MB); the client colours districts by amount and draws tooltips. No
     new JavaScript dependency, no network to draw.
   - UI (simplified on Paul's second look, 2026-09-17): a "Map" button on every pane and on the
     Compare strip opens one map with one switch, Raised (where the money came from) / Spent
     (where the money they spent went). Spent = the PAC's own giving and independent spending by
     the recipient candidate's state and district (candidate master; support and oppose kept
     apart; Senate and presidential races shown statewide); Raised = contributor geography (ZIP
     crosswalk, upgraded by geocoding). Beside the map one ranked list: district, who, amount,
     share. Match basis and boundary vintage live in one footnote line and a small settings
     popover, not in the bar. Hover tooltip (district, amount, rows, share, basis); click filters
     the pane's rows (`a.district` URL key); Compare gains a "Top districts" row. Real example on
     the canvas: Fairshake 2024 spent $40.7M across 28 districts, CA-SEN oppose Porter
     $10,041,119, CA-45 support Steel $2,791,716, CO-08 Caraveo $2,270,929, NY-16 oppose Bowman
     $2,078,023 ...; $2,280,606 on candidate ids the master does not carry (shown as unmatched,
     never dropped).
   - ALL SPEND (Paul, 2026-09-17: "a heatmap visualization on spending amounts, and all spend
     should be showcased"): Spent maps every disbursement the committee reported, in four kinds,
     each with its own geography basis, summing to the FEC financial summary and saying so:
     candidates (independent spending, Schedule E, and direct contributions, Schedule B line 23)
     by the candidate's district; transfers to committees (line 22) by the recipient committee's
     registered state from the committee master; operating payments (line 21B) by the payee's
     state and ZIP; asset conversions (in-kind crypto liquidations filed as operating, identified
     by the description and a receipt-side in-kind twin) as their own kind, in the total, off the
     heat by default. Anything the bases cannot place is an "unlocated" bucket, never dropped.
     Measured on Fairshake 2024: 40,661,821 + 86,250,000 + 5,413,951 + 63,499,995 = 195,826,511 =
     disbursements as reported. Heat: one continuous ramp (lilac to plum) on a log scale with real
     stops in the legend ($1,000 / $10,000 / $100,000 / $1,000,000 / $10,000,000+); candidate
     spending heats the district, Senate and presidential races, transfers and operating heat the
     state; support and oppose stay apart in the list and tooltip. Layer chips toggle each kind and
     the summary line always shows reported, located and unlocated totals. For company PACs the
     same four kinds come from the workbook's downstream sheets and the bulk pas2/oppexp files.
   - Data rules for Paul: (0) default heat layers = candidates + transfers + operating, asset
     conversions listed but off; (1) ZIP-level attribution shown as approximate with the split shares;
     (2) boundary vintage per cycle (2025-2026 -> 119th; 2023-2024 -> 118th; 2021-2022 -> 117th)
     or one vintage with a note; (3) installing `shapely` (and `geopy` if wanted) into the launcher
     Python is Paul's yes, as python-calamine was; (4) geocoding leaves the machine (Census or the
     GeoPy provider) with contributor addresses, so it runs only on Paul's explicit start per
     import, never automatically.
   - Lane: S8 (district map), after S6 lands; the S6 pane and Compare markup leave the "Map"
     button slot in place so S8 adds no layout change.

## 3. Mockup

Design artifact "PAC Evidence v2 Mockup" (real figures from a scratch console on the S7 code, both
workbooks re-imported): Crypto FAIRSHAKE $177,980,393.39 / 28 rows (2024 $125.5M, 2026 $52.5M;
Coinbase, Coinbase Commerce, Armstrong); Crypto COINBASE INNOVATION PAC $537,499.47 / 1,373 rows;
Crypto CHAMBER OF DIGITAL COMMERCE PAC $69,425.03 / 8 rows (Trade Association from the FEC master);
Credit Union CULAC $36,870.31 / 594 rows (SchoolsFirst, Mountain America); DCCC in both industries
(Crypto $147,900 / 10 rows vs Credit Union $3,480 / 48 rows); snapshot Coinbase -> Fairshake /
Defend American Jobs / Protect Progress with IE totals.

## 4. Rulings (Paul, 2026-09-17: "That looks great" on the mockup, then "Go")
Every recommendation stands:
1. Panes mix imports and saved snapshots in one grid.
2. Up to 4 panes.
3. Comparison metrics as listed in C.
4. URL keys: prefixed `a.*`-`d.*` (the HANDOFF rule).
5. Chart Studio data source deferred to S6b.
6. Collector form moves into a drawer; "Follow Graph" becomes a bar toggle.
7. Map ships as lane S8 after S6; S6 leaves a disabled Map button slot on every pane and on Compare.
8. ZIP matches shown as approximate with split shares.
9. Boundary vintage per cycle (2026 -> 119th, 2024 -> 118th, 2022 -> 117th).
10. Geocoding runs only on Paul's explicit Start per import.
11. `shapely` into the launcher Python for S8; `geopy` only as an optional provider.
12. Default heat layers = candidates + transfers + operating; asset conversions listed, off.

Build after the rulings: one Opus architect build on this design and the mockup, Fable review on a
scratch console, browser steps for add/remove pane, comparison strip, URL round-trip; then Paul
commits and re-runs the launcher.
