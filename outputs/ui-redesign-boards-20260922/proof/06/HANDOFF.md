# Build 06 (PAC evidence): handoff

Built on 2026-09-22 in `C:\Users\pgoff\Mentat` (branch `codex/mentat-crypto`).
- **Not committed.** No git command that changes state was run.
- **Paul's console on port 8806** was not touched.
- **Own read-only console** on port 8816 (pid 30660) was stopped at the end.

## Files changed

Every file was hunk-exact and sha-checked before each write. Each file's line endings were preserved: new lines take the ending of the lines around them, and mixed files stay mixed.

| File | Before (sha256) | After (sha256) | Lines (+ / −) | Line endings, before → after (CRLF / LF) |
|---|---|---|---|---|
| `mentat/app/templates/view_evidence.html` | d9f9af71…4e4b | 6159a81e464f7e332233ea9ccbb668e62b7c8a928f6f7404ca65f09031662dae | +24 / −21 | 44 / 0 → 47 / 0 |
| `mentat/app/evidence.js` | 7c933497…34a1 | f8dfd1915fae7bd4e33e6031d2d426db479f64be86e8575eb2866ee99d4f4b50 | +340 / −63 | 2488 / 196 → 2766 / 195 |
| `mentat/app/evidence-map.js` | 1a454e45…9e15 | ab9faae5df267acb1e34efa404bf088fab1075e06d36f528cf4c53ab5b6e9c3e | +48 / −8 | 905 / 186 → 924 / 207 |
| `mentat/app/workspace.css` | 7881f8dc…249e11 | 41baec5bdfd460b0d96590b2677b17a5d94ac2d0379b35c7c7924e5dd222bebc | +267 / −0 (append only) | 0 / 1148 → 0 / 1415 |
| `mentat/tests/test_evidence_panes_browser.cjs` | 53d9c9b9…367b | 51a16e1de6a32a5d9ed7bec07f952849a294dfbb5c21bbc2dbbb79df48db070f | +93 / −45 | 881 / 7 → 929 / 7 |
| `mentat/app/tests/evidence-map.test.js` | 5d00d679…48b3 | 0da9db46689aa8ec6171615e68706fa0ee5960f49a3e21f990bcab991343aa0e | +14 / −0 | 0 / 206 → 0 / 220 |

Notes on the table:
- **`evidence.js` LF count 196 → 195.** One LF-only line (the old cycle-option line in the map toolbar) was replaced.
- **`evidence-map.js` new lines.** `unionDomain`/`rangeFor` sit in an LF region; `mirror` sits in a CRLF region.
- **Pre-edit copies and the write ledger** are in the build-06 scratch folder (`pre\`, `ledger.json`).
- **The golden `mentat/app/index.html`** was already rendered with this template by another builder at 18:03. `render_console.py --write` then reported it up to date: 78,787 bytes, sha256 802d989f….

**Kept byte-identical (Paul's 09-22 citation work):**
- `evidence_geo.py` and `test_evidence_geo.py`: hashes unchanged since the start.
- `evidence-citations.test.js`: unchanged.
- `evidence.js` lines 61–126 (the comment at 61, `sourceAnchor` at 63, `filingLedger`, `filingCitations` to 126): byte-identical to the pre-build file, 3,636 bytes, after fix round 1 too.
- `workspace.css`: the old file is an exact byte prefix of the new one, so lines 880–887 (`.fec-citations`, `.record-links`) are untouched.

**A root-cause fix in `evidence-map.js` `flyTo`, found by the final run.**
- **The fault.** An animation frame's timestamp can come before the `performance.now()` taken when the fly starts. The elapsed time was then negative, the ease went below zero, and the scale was pushed under 0.
- **What it did.** Circles were drawn with a negative `r`. The console error was `<circle> attribute r: A negative value is not valid. ("-13.5204")`, which is the 11px donor radius at scale −0.81.
- **The fix.** The fly's progress is now clamped at 0.
- **Where it showed.** The re-homed interaction suite, in its one-map ZIP-list step. The error depends on timing: two earlier runs of the same code were clean.

**No new files in the repo.** `server.py` `STATIC_ASSETS` is unchanged, and nothing needs a console restart beyond the usual reload.

## What it does

**Pane board (B19 with board 3's pane)**
- **Picker rail (270px card).**
  - Contents, top to bottom:
    - "Find a PAC";
    - three `.chip-select`s: Source, Type, Cycle;
    - a "Follow Graph selection" switch;
    - the source's PACs as ticks;
    - the status line;
    - the "Import a file" and "New snapshot" links.
  - A tick opens that PAC's pane on the rail's cycle, and an untick closes it.
  - The rail allows three panes. A fourth tick opens nothing and shows "Close a pane to open another."
  - Import and New snapshot open their drawers at the top of the panes area.
  - The "Open panes" chip row is gone.
- **Panes.** Board 3's content:
  - overline, name, and a tag row (chip · id · cycle);
  - Summary | Map | Rows with the approved gold, plus ×;
  - four figures with no sub-captions (each note moves to the figure's title and to About these figures);
  - By cycle with one-line labels;
  - Where it came from;
  - Top contributors (three rows with a NAME / AMOUNT header);
  - the source line and About these figures.
- **Layout.** Two panes split the area in halves and three in thirds. Compare is restyled only.
- **Empty state.** One line: "Tick a PAC on the left to open it here."

**Enlarged map (boards 6 and 7)**
- The panel chrome is gone. The overline and a 40px serif name sit on the page, with Back to panes at the right.
- **Toolbar:** Raised | Spent (40px), cycle, LAYER segments (Region, State, Congressional district, State district, ZIP code), "Compare with [None]", search ("Find a state, district or ZIP"), round + and −, Reset view, Enlarge.
- The breadcrumb shows only when a place is selected.

**Two-cycle compare (M13)**
- **Picker.** "Compare [A] with [B]". "None" returns to one map.
- **Maps.** Two map cards under `--scope-1` and `--scope-2` cycle pills.
  - Same zoom and pan: each map mirrors the other's transform on drag, wheel, keyboard, buttons, search and reset.
  - One shared heat range: the union of both cycles over the visible area.
  - One legend under both.
- **"Biggest changes by <layer>".** Places ranked by absolute change (A − B): two bars in the cycle colours, teal up, `--chart-negative` down, and each cycle's located/unlocated at the foot.
- **Data.** The second payload comes from `/api/evidence-geo` with the same source, id, committee and direction. The change is computed in the browser.

## Contracts exposed (tests and other code may rely on these)

**Pane board**
- **Rail ticks:** `#evidence-list input[type=checkbox][value="<committee id>"]`.
  - Checked when a pane with (source, id, committee, rail cycle) is open.
  - A `change` event opens or closes that pane.
  - Rows are `.evidence-rail-row` (`.on` when ticked).
- **Rail note:** `#evidence-rail-note`, `role=status`.
- **`#evidence-pac` and `#evidence-add`** stay in the page, hidden (`.evidence-picker-data[hidden]`).
  - They are still filled and enabled or disabled exactly as before: the rail's data and the `openCommittee` path.
  - Playwright cannot `selectOption` or `click` a hidden element, so suites that drive them must tick the rail instead (see requests 1 and 2).
- **Pane figures:** `.pane-figure[data-note]` and `.pane-figure[title]` carry each figure's former sub-caption.
- **Pane limit:** `MAX_PANES` is 3. The URL keeps the a–d prefixes, so a stale `d.*` is still cleared. The status suffix is "3 panes open · close one to open another". `MentatEvidence.openCommittee` says "Three panes are open. Close a pane to open …".
- **Source options:**
  - each option's `label` is the industry or company (what the 80px chip shows);
  - `textContent` is unchanged ("Crypto · 8 rows" and so on);
  - the blank option's label is "Source".

**Map**
- **Compare picker:** `#evidence-map-compare`. Value `""` means None, otherwise a concrete cycle. `#evidence-map.comparing` is set while comparing.
- **Map hosts:** `.map-compare-card--a` / `--b`. The first `.map-canvas-host` is still map A, so `mapCanvas()` and every existing selector keep working. `.map-canvas-host--b` is map B.
- **Also:** `.map-cycle-pill`, `.map-compare-legend`, `.map-changes .map-change[data-focus][data-focus-kind]`, `.map-change-value.up` / `.down`.

**`evidence-map.js`**
- `MentatEvidenceMap.mirror(host, {scale, x, y})`: sets the transform silently, with no `onView` echo back.
- `unionDomain` and `rangeFor` are exported for the unit tests.
- View options: `companion` (the other map's view; this map then paints to the shared range) and `onLegend(card)`.

## Requests to other owners

1. **`mentat/tests/test_evidence_map_browser.cjs` and `mentat/tests/test_evidence_map_interaction_browser.cjs`.**
   - Evidence-lane suites that are not on build 06's owned list, so I did not edit them.
   - Each drives `selectOption('#evidence-pac')` and `click('#evidence-add')`, and both elements are now hidden by the prompt.
   - Patches: `requests\test_evidence_map_browser.patch` (2 hunks) and `requests\test_evidence_map_interaction_browser.patch` (2 hunks). Each replaces the select and click with a tick of the same committee in the rail.
   - Run from scratch against the build, the re-homed copies pass: **23/23** and **22/22**. Unpatched, both fail at their "add the pane" step (see the suite table in the report).
   - **Ruling needed:** who applies them. Build 06 can apply them if granted.
2. **`mentat/tests/test_workspace_polish_browser.cjs`.**
   - Single-writer file; build 02 is the holder.
   - One hunk at lines 158–159, `requests\test_workspace_polish_browser.patch`: wait for a rail tick, then check the first one (the snapshot fixture's PAC), in place of the `#evidence-add` wait and click.
3. **Server (import catalog), for B19's receipts in the rail.**
   - `evidence_csv.py` builds each import's `committees` with row counts only.
   - Adding `receipts` (all cycles) and `receipts_by_cycle` per committee, read from the sqlite `totals` table (the lead channel per committee, as the pane's first figure uses), lets the rail rank imports by receipts with no client change: `receiptsOf()` already reads both fields.
   - Today imports rank by rows in file and show "N rows". Saved snapshots already show receipts.
   - Fetching one summary per PAC instead was measured: 2.1 s for Community Banks, 5.1 s for Credit Union and 9.4 s for Crypto of server work per source. It was rejected.
4. **`mentat/app/scope.js` (build 02), optional.**
   - For the compare cycle to survive a permalink under D-039, add `compare` to `PANE_FIELDS`, validated as a four-digit cycle.
   - evidence.js would then write `<pane>.compare` in `writeScope` and read it in `restorePanes`. That is a small follow-up, not done here.

## Suites

"Before" ran on the unmodified bytes at 16:21–16:26. "After" is the final bytes at 18:07–18:24.

| Suite | Before | After |
|---|---|---|
| `test_pac_evidence.py`, `test_evidence_geo.py`, `test_evidence_csv.py` | 71 passed, 105 subtests | 71 passed, 105 subtests |
| `evidence-map.test.js`, `evidence-citations.test.js` | 20/20 | 21/21 (one new test: the shared compare range) |
| All `app/tests/*.test.js` | not run | 284/285 at 18:2x (a `scope.test.js` contract failure from build 02's work in progress, since resolved: 321/321 at the start of fix round 1, 324/324 after it) |
| `test_evidence_panes_browser.cjs` (owned, re-homed) | 33/33 | 33/33 |
| `test_evidence_map_render.cjs` | pass | pass |
| `test_evidence_map_browser.cjs`, live and not patched | 23/23 | fails at step 5, `selectOption('#evidence-pac')` on the now-hidden select (expected; request 1) |
| … re-homed copy (request 1 patch) | — | 23/23 |
| `test_evidence_map_interaction_browser.cjs`, live and not patched | 22/22 | fails at step 4, the same cause (expected; request 1) |
| … re-homed copy (request 1 patch) | — | 22/22, after the `flyTo` fix above |
| `test_console_browser.cjs` (shared) | not run | first run red at line 296, Graph's `#graph-candidates` wait (build 02's view; the evidence block at lines 84–170 had already passed). Rerun once: **passed** |
| `test_workspace_polish_browser.cjs` (build 02's) | not run | red at line 142, Cross-reference `.xref-adjustments summary` (build 05's view). That is before its evidence step at lines 156–159. The re-homed copy stops at the same line |
| `test_console_templates.py` | 10 passed | 10 passed |
| `render_console.py --check` | up to date | up to date (78,787 bytes) |

## Open items

- **A11:** rail figures for imports are row counts until request 3 lands.
- **C12:** the compare cycle is not in the URL (request 4).
- **B4:** at 1440 and 1600 the map toolbar takes two rows, because it keeps Find, Enlarge and the compare picker. It is one row at 1920.
- **Paul to rule:**
  - B8: the default map layer stays Congressional district (the map contract's pin); M13 and board 6 draw State.
  - B14: the zoomed title stays the PAC name (a test asserts it); board 7 retitles to the district.

---

## Fix round 1 (2026-09-22, 19:38–21:10)

Reviewer defects R06-01…R06-16 and D1…D11. Every one is mapped to its action at the end of `DIFFERENCES.md`; the short form is below. Nothing committed; no git command that changes state; Paul's console on 8806 untouched; my read-only console on 8816 stopped at the end.

### Files changed this round

Each file was sha-checked against the ledger before each write. A new line takes the line ending of the line it sits beside, and no unchanged line changed its ending (checked line by line against the round-start bytes, which were rebuilt exactly by replaying the build's own edit specs and matching their sha256).

| File | Round start (sha256) | Now (sha256) | Lines this round (+ / −) | Line endings now (CRLF / LF) |
|---|---|---|---|---|
| `mentat/app/evidence.js` | f8dfd191…4b50 | c89eaf0a8b97ba22eea835154b3793255476fe48b0fc5b0a8dfebc1b83bdc45b | +153 / −89 | 2830 / 195 |
| `mentat/app/evidence-map.js` | ab9faae5…9c3e | 7e409420c2ab0de005b20836641df9599768d336df1a56ee7278fb9825ec1625 | +73 / −13 | 958 / 233 |
| `mentat/app/workspace.css` (build-06 block only; the pre-build file is still an exact byte prefix, so Paul's 880–887 hunk is untouched) | 41baec5b…bebc | 9ce5e1fd6cac742d2c0d6e973d73e2bec10001cd33532940df08b102a9d53778 | +101 / −18 | 0 / 1498 |
| `mentat/app/evidence_csv.py` (server: the import listing) | a549e95d…624d | 0cb8dd0d8f533d03c76b2744f1edc45acaec66c3c5ccbf873e9dcaf6d386b256 | +67 / −6 | 2570 / 0 |
| `mentat/tests/test_evidence_csv.py` | d7c11116…9e6a | 7910b02564a43500f9576ba021fef38d2baca54dfb30ee1e78c90c155e4f2987 | +34 / −0 | 188 / 0 |
| `mentat/tests/test_evidence_panes_browser.cjs` | 51a16e1d…070f | c36e3614167615ecad47e71389dd2bd378d7247811574ce69d4f73dd5f80cb45 | +88 / −4 | 1013 / 7 |
| `mentat/tests/test_evidence_map_browser.cjs` (D1: granted by the fix round) | ce1ff259…849c | f0c52a72b916b77086f38f0eeb8c28ffdd2952cc64c9a15d9892fa79ee889aca | +58 / −9 | 614 / 21 |
| `mentat/tests/test_evidence_map_interaction_browser.cjs` (D1) | dc309e4c…3d97 | 3b5c80ae1ee9f5d200f01b10d930345b13c224824f76c84e226bab63bf66eaf9 | +21 / −10 | 671 / 46 |

Unchanged this round: `templates/view_evidence.html` (6159a81e…), `app/tests/evidence-map.test.js` (0da9db46…), and Paul's `evidence_geo.py` (d4342f5f…), `test_evidence_geo.py` (63a0de47…), `evidence-citations.test.js` (1466827d…), `test_pac_evidence.py` (e2efda74…). No template changed, so `index.html` did not change for this build: `render_console.py --write` then `--check` report it up to date (78,796 bytes, another builder's render). `evidence_csv.py` changed, so **a console restart** is needed before the rail shows receipts on Paul's console (8806 is down and was not touched).

### What changed

- **R06-01 (blocker), both maps fly together.** `evidence-map.js`: `render(host, view)` honours `view.quiet` (its closing transform is not echoed through `onView`); `mirror` leaves alone a map already flying to the leader's target (the leader's `onView` now carries `target`). `evidence.js` renders map B quiet. Zoom 1.96 → Reset 1.000/1.000 → Find "TX" 2.593/2.593 at 1440, 1600 and 1920; the negative control (B not quiet) reproduces 1.96/1.96.
- **R06-02, receipts in the rail.** `Store.committee_figures(identifier)` reads the import's sqlite `totals` once per listing (cached by size and mtime; 15 ms for the 523-PAC Crypto import) and gives each listed committee `receipts` (its lead channel over all cycles: the figure its pane opens on), `receipts_channel` and `receipts_by_cycle`. The rail ranks by it; a PAC with no figure in the chosen cycle reads "—" and sorts last.
- **R06-03, ticks are PACs.** A tick follows the PAC's open pane whatever the Cycle chip says; untick closes it; an open PAC is never refused.
- **R06-04 / R06-14, one toolbar row.** No Find (Enter searches); "Compare with…" is one select; Enlarge / Collapse is an icon at the map card's bottom right.
- **R06-05 / R06-06, nothing between toolbar and map; board wording.** RULING A's note is screen-reader text plus the cycle chip's title; the kind toggle is a "Shown" group in the legend; the legend reads "Amount (heat)" / "Donors (circles)" and sits compact at the map card's bottom left.
- **R06-07 / R06-08 (Paul to confirm).** Default layer State; zoomed to a place, the place is the title ("IN-05: Congressional District 5") and the PAC's name the overline; the trail drops the region step.
- **R06-10, M13 cards** keep 444:470 with the map centred. **R06-11** Source chip full width. **R06-13** four figures across to 400px. **R06-15** one-line changes foot. **R06-16 / D2** one-line rail status, sticky rail, "Filter, sort and pin" folded at the ranked card's foot.
- **D6** the refusal note clears when a pane closes. **Found while testing:** the rail cleared while a saved snapshot is read (a tick in that window opened the wrong committee); the map is one column again at 390px.

### Contracts changed this round (tests and other code may rely on these)

- Import listing (`GET /api/evidence-csv`): each `sources[].committees[]` item gains `receipts` (number or null), `receipts_channel` (string) and `receipts_by_cycle` ({cycle: number}, only cycles with supported rows). Additive; an import being re-read goes without.
- `MentatEvidenceMap.render(host, view)`: `view.quiet`; `view.kinds` ([{kind, label, total, off, colour}]) draws the legend's "Shown" group of `.layer` toggles (`data-layer`, `aria-pressed`). `onView` payloads carry `target` while flying.
- `#evidence-map-find` is gone. `#evidence-map-enlarge` is still the Enlarge / Collapse control (an icon; `aria-label` "Enlarge the map" / "Collapse the map"). `#evidence-map-list-search`, `#evidence-map-list-sort` and `#evidence-map-pin` sit in `details.map-list-menu` (open it first).
- The map's `.map-note` is `.sr-only`; `#evidence-map-cycle[title]` carries the same sentence. `.map-trail-layer` is `.sr-only`. `.map-layers` no longer exists.
- Rail: a tick means "this PAC has a pane open in this source" (any cycle); `.evidence-rail-row[title]` ends "· open on <cycle>" when that differs from the chip. `#evidence-status.is-scope` is the one-line scope status (its `title` is the full text); `say()` text (progress, errors) is shown whole.
- `evidence.js` writes `<pane>.compare` and restores it once `scope.js` knows the key.

### Suites (this round)

"Before" is the round-start bytes at 19:43–19:47; "after" is the final bytes at 20:45–20:52.

| Suite | Before | After |
|---|---|---|
| `test_pac_evidence.py`, `test_evidence_geo.py`, `test_evidence_csv.py` | 71 passed, 105 subtests | 72 passed, 107 subtests (one new test; red on the old `evidence_csv.py`) |
| `test_console_templates.py` | 10 passed | 10 passed |
| `evidence-map.test.js` + `evidence-citations.test.js` | 21/21 | 21/21 |
| All `app/tests/*.test.js` | 321/321 | 324/324 (other lanes' units moved too) |
| `test_evidence_panes_browser.cjs` | 33/33 | 34/34 (new step 20; step 31 re-homed) |
| `test_evidence_map_browser.cjs` (live) | red at step 5 (the hidden `#evidence-pac`) | 25/25 (D1 applied; State-default step; legend `.layer`; compare step 23) |
| `test_evidence_map_interaction_browser.cjs` (live) | red at step 4 (same cause) | 22/22 (D1 applied; re-homes for State default, Enter search, the place title, the list menu) |
| the two re-homed scratch copies (previous round) | 23/23, 22/22 | superseded by the live suites |
| `test_evidence_map_render.cjs` | pass | pass |
| `test_console_browser.cjs` | not run | pass |
| `test_workspace_polish_browser.cjs` (build 02's) | red at line 142 (previous round) | red at line 142 twice (Cross-reference `.xref-adjustments summary`, build 05's view), before its evidence step; reported, not fixed |
| `render_console.py --check` | up to date | up to date (78,796 bytes) |

### Requests to other owners (this round)

1. **`mentat/app/scope.js` + `mentat/app/tests/scope.test.js` + `audits/…/contracts/url_scope.json` (build 02):** `requests\scope_pane_compare.patch` adds `compare` to `PANE_FIELDS` (validated as a four-digit cycle), a test, and the four `x.compare` contract keys. In a scratch mirror: 79/79; the new test is red on today's `scope.js`. With it, a compare permalink round-trips (evidence.js already writes and reads the key).
2. **`mentat/app/workspace-polish.css` (single writer):** `requests\workspace_polish_split_view.patch`, one rule: `body[data-view=evidence] #split-view{margin-right:0}` puts Split with Graph flush right (1463–1578 at 1600, checked by inserting the rule through the CSSOM).
3. **`mentat/tests/test_workspace_polish_browser.cjs` (build 02):** `requests\test_workspace_polish_browser.patch` still stands (tick the rail instead of `#evidence-add`); it works with this round's rail (the rail is empty until a chosen snapshot is read, then the first tick opens it).
4. `requests\test_evidence_map_browser.patch` and `requests\test_evidence_map_interaction_browser.patch` are **applied** (D1); kept as the record.

### Open for Paul

- **B8 / R06-07:** the map now opens on State (boards 6 and M13). Reverting is one line (`layer: 'state'` in `mapStateFor`) plus the two suites' "opens on State" assertions.
- **B14 / R06-08:** zoomed to a place, the place is the title and the PAC's name is the overline (board 7 shows no PAC name at all).
- **R06-03 behaviour change:** one rail row is one PAC. Opening the same PAC on a second cycle is no longer a rail action (a permalink, Graph's `openCommittee` and the hidden `#evidence-add` path still do it); the two cycles of one PAC compare on the pane's By cycle bars and on the map's Compare.
- **B18:** the ranked card shows about 6 rows at 1600 (board 6: 10) because the reconciliation line and the geocoding note (both tested wording) sit under the list.

---

## Final fix round (fix round 2, 2026-09-22, 22:06–22:40)

Reviewer defects R06b-01…R06b-07 (review of fix round 1). Nothing committed; no git command that changes state; Paul's console on 8806 untouched (not listening before or after); my read-only console on 8816 (`server.py --port 8816 --read-only`) stopped at the end (8816 not listening after), and every probe and suite browser closed.

### Files changed this round

Each file was sha-checked against the ledger (`ledger.json`, scratch) before its write, written by the EOL-preserving patcher, and recorded after. Round-start copies are in the scratch folder `fr2\start\`.

| File | Round start (sha256) | Now (sha256) | Lines (+ / −) | Line endings now (CRLF / LF) |
|---|---|---|---|---|
| `mentat/tests/test_evidence_panes_browser.cjs` | c36e3614…cb45 | 13e4f9396ef79a7491905f5fd6aa985ace1b21113e1d1162a8e68a66934b35cf | +7 / −0 | 1020 / 7 |
| `mentat/app/evidence.js` | c89eaf0a…c45b | 5b89e696b37275b1487f084503a39ce0853403c1809e09612d9406e741be89fc | +2 / −2 (two table tags gain `class="map-donors"`) | 2830 / 195 |
| `mentat/app/workspace.css` (appended to the build-06 block) | 9ce5e1fd…3778 | b8bcc2786e68cdc49ae9f9fd76a0e6f6dde6162d8571e8b73a3ab2464aa305f7 | +32 / −0 | 0 / 1530 |

Unchanged this round: `evidence-map.js` (7e409420…), `templates/view_evidence.html` (6159a81e…), `app/tests/evidence-map.test.js`, both map suites, `evidence_csv.py`, `test_evidence_csv.py`. Paul's work is byte-identical: `evidence_geo.py` d4342f5f, `test_evidence_geo.py` 63a0de47, `evidence-citations.test.js` 1466827d, `test_pac_evidence.py` e2efda74; `evidence.js` pre-build lines 56–122 = lines 61–127 now; the pre-build `workspace.css` (and the round-start one) is an exact byte prefix of the new file, so 880–887 is untouched. No template changed: `render_console.py --write` then `--check` report `index.html` up to date (78,796 bytes). No console restart needed (static assets only).

### Final fix round: id → action

- **R06b-01 (major) → fixed.** Cause confirmed: step 3's `waitStatus(/Nothing imported yet|snapshot/)` is already met by the template's first status "Finding imported files and saved snapshots…" while `#evidence-list` is empty. The step now waits for `#evidence-list .evidence-list-empty` to read "Choose a source above…" or "Nothing imported yet…" before reading the rail. Three consecutive runs on the final bytes: 34/34, 34/34, 34/34.
- **R06b-02 (major) → fixed.** Both focused-place tables are `table.map-donors`: auto layout, `overflow-wrap:normal`, headers `nowrap`, links still breakable. At 1440 the headers are 106 / 86 / 119 / 96 px, one line each (38px); a word-by-word range-rect check finds no split word in any header or cell at 1440, 1600 or 1920, and the table does not scroll sideways (408 / 470 / 594 px wide).
- **R06b-03 → fixed.** At ≥1100px the changes list is a flex column. Each row's basis is 61px and it can shrink to its content (38px: 16px name line, two 6px bars). The compare card's heading and foot are tighter. Result: 8 of 8 rows above the foot at 1440 (39px each), 1600 (45px) and 1920 (57px), and also on the district layer at 1440.
- **R06b-04 → fixed.** A compare card is now as tall as its map, not 444:470. The geography fills 72% / 76% / 80% of card A's height at 1440 / 1600 / 1920 (was 52% at 1440). Blank above is the 56px pill band; blank below is 21–27px. Cards: 376×289, 456×339 and 616×439. DIFFERENCES C3 is corrected (round 1's "fixed" was wrong).
- **R06b-05 → named, and the locator moved.** DIFFERENCES B16 is **fixed**: the locator now sits at the map's bottom right, 14px in, as on board 7 (it was top right). The positioning is pure CSS: a width-relative margin puts it at the 975:610 map's bottom, and enlarged mode uses a set height. These are **intended**, each with its reason:
  - B19: the source-details line;
  - B20: "Clear";
  - B21: "Source page N · cycle", Previous/Next source page and the "not all donors" count, all asserted by the interaction suite;
  - B22: the legend titles. **Paul to rule** whether board 7's "District funding (raised)" / "Donor ZIP locations" should replace them on the district layer.
- **R06b-06 → still open, other owner.** `scope.js:26` `PANE_FIELDS` still lacks `compare`. `requests\scope_pane_compare.patch` (build 02) is unchanged and not applied. evidence.js already writes and reads `<pane>.compare`.
- **R06b-07 → still open, other owner.** `workspace-polish.css` is single-writer (line 218 still sets `#split-view{margin-right:260px}` on evidence). `requests\workspace_polish_split_view.patch` is unchanged and not applied. It is deliberately not overridden from `workspace.css`: one control should have one source of truth.

### Proof (this round)

- **Regenerated side-by-sides.** Board left, build right, at 1440×900, 1600×900 and 1920×1080:
  - `06_map-single_*`
  - `06_map-zoomed_*` (board 7)
  - `06_map-compare_*` (M13)
- **Also regenerated:** `06_map-compare-reduced-motion_1440x900` and `build-only_06_map-compare_full_1440x900`.
- **Capture checks.** Every capture page had 0 page errors, 0 console errors and 0 off-origin requests. No horizontal overflow at any size.
- **Reduced motion.** A fly lands instantly and in step: `same: true`, scale 2.593 on both maps.
- **`measurements.json`.** This round's map, zoomed, compare and reduced keys are merged over round 1's. The pane board did not change.
- **Probe JSONs and PNGs.** In scratch `fr2\probe\`. `F*` is the final bytes; `G1440` is the district-layer check.

### Suites

"Before" is the round-start bytes, taken from the reviewer's runs on those exact bytes (review06 `r2_*`). "After" is the final bytes, 22:27–22:35.

| Suite | Before | After |
|---|---|---|
| pytest `test_pac_evidence.py`, `test_evidence_geo.py`, `test_evidence_csv.py`, `test_console_templates.py` | 82 passed, 109 subtests | 82 passed, 109 subtests |
| node `evidence-map.test.js` + `evidence-citations.test.js` | 21/21 | 21/21 |
| node all `app/tests/*.test.js` | 324/324 | 324/324 |
| `test_evidence_panes_browser.cjs` | red at step 3, three runs of three | **34/34 three runs of three** |
| `test_evidence_map_browser.cjs` | 25/25 | 25/25 |
| `test_evidence_map_interaction_browser.cjs` | 22/22 | 22/22 |
| `test_evidence_map_render.cjs` | pass | pass |
| `test_console_browser.cjs` | pass (round 1) | pass |
| `render_console.py --check` | up to date (78,796 bytes) | up to date (78,796 bytes) |

`test_workspace_polish_browser.cjs` (build 02's) was not rerun this round: nothing it drives in the evidence view changed, and its round-1 red was at line 142, in build 05's view.

### Still open for Paul (after this round)

- B8, B14, R06-03 and B18, as above.
- **B22:** legend titles on the district layer (board 7 wording, or keep one wording).
- **C12 / R06b-06:** apply `requests\scope_pane_compare.patch` (build 02 or Paul).
- **A34 / R06b-07:** apply `requests\workspace_polish_split_view.patch` (the `workspace-polish.css` holder).
