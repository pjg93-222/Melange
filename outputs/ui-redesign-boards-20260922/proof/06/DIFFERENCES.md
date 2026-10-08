# Build 06 (PAC evidence): differences from the boards

Built 2026-09-22 against `prompts\06_pac_evidence.md` and the 11:44 `00_README.md` (sha256 9bc887f4…), including its "Notes from build 01". Nothing was committed. Paul's console on port 8806 was not touched; every capture came from a read-only console on port 8816.

**Boards.** Part 1: `B19_pac_evidence_panes` (the page) with `approved_board3_pac_panes` (the pane; "where B19 and board 3 differ inside a pane, board 3 wins"). Part 2: `approved_board6_map_enlarged`, `approved_board7_map_zoomed` and `M13_pac_map_compare`.

**Frame.** B19 and M13 are 2000x1131: a 1600x905 CSS frame at 1.25x on both axes. Boards 3, 6 and 7 are 2688x1520; they are read in the same 1600x905 frame (1.68x), as build 01 did. Their sidebar is 249/2000 of the width, the same as M4's 200px.

**Method.**
- Board positions come from gridded crops at the frame scale (`board_probe.py` in the build-06 scratch folder).
- Build positions come from `getBoundingClientRect` (`measurements.json`, every state at 1440x900, 1920x1080 and 1600x900).
- The side-by-sides put the board at its 1600-px frame on the left and the build at 1 image px = 1 CSS px on the right.

**Capture notes.**
- The read-only console always shows "Read-only preview · the original console continues…" (`#error`), and it showed the stale-build banner (`#stale-banner`) while builders were editing.
- Neither is on any board. The capture script hid both through the CSSOM before each screenshot, and `measurements.json` records it (`*_hidden`).
- Sample data: Community Banks workbook. The panes are AMERICAN BANKERS ASSOCIATION PAC (C00004275), TEXAS BANKERS ASSOCIATION PAC (C00196444) and MORTGAGE BANKERS ASSOCIATION PAC (C00004812). The maps use MORPAC for 2025–2026, compared with 2023–2024.
- Amounts and names are real data; the boards' amounts are illustrative.

**Status key.**
- **fixed**: the build matches the board.
- **intended**: deliberate, with the reason given.
- **open**: needs a ruling or another owner.

---

## A. Pane board: B19's page, board 3's pane (1600x900 unless stated)

| # | Element | Board | Build | Status |
|---|---|---|---|---|
| A1 | Page title "PAC evidence" | about 37px serif, at y 20–60 | 31px Georgia at y 11, the shell's (build 01, M4) | intended (one shell on every view, build 01) |
| A2 | First card top | 72 | 55: the shell's 10px under the title | intended (follows from A1) |
| A3 | Sidebar icons, tall purple active item | drawn | text-only, one lilac item | intended (build 01 B14, call 9) |
| A4 | Rail left edge | 218 | 226, the shell content edge | intended (M4 content edge, build 01) |
| A5 | Rail width | 270 | 270 (the prompt says 300) | fixed (board over prompt) |
| A6 | Rail padding | 9px sides, 12px top | 8px sides, 12px top | fixed (8px leaves the chips 80px, B19's 78–79) |
| A7 | "Find a PAC" search | 32px tall, magnifier, placeholder "Find a PAC" | 32px (252x32), same | fixed |
| A8 | Source, Type and Cycle chips | 78–79 x 31 in one row, no labels | Source 252 x 31 on its own row; Type and Cycle 123 x 31 under it; labels are screen-reader only | intended (fix round 1, R06-11: three 80px chips cut "Community Banks" to "Comm…"; the name needs about 125px) |
| A9 | Source chip text | "Banking" | the import's industry, whole ("Community Banks"); the full option text is also on the chip's title | fixed in fix round 1 (R06-11; B19's "Banking" is a Don't-copy item) |
| A10 | "Follow Graph selection" | not drawn | a switch under the chips (26x15) | intended (prompt 06, item 2) |
| A11 | Rail row figure | receipts ("$11,950"), rows ranked by receipts | receipts, ranked by receipts: "$137,779", "$100,000" … for the Community Banks import (each committee's lead figure, the one its pane opens on, now in the import listing); a snapshot's receipts as reported; "—" last where a PAC has no figure in the chosen cycle | fixed in fix round 1 (R06-02 / D4) |
| A12 | Rail rows | 33.6px pitch, tick, name, figure at the right; ticked rows on a lilac band | 33.6px pitch; band `#f0eaf1` (board 240,234,240); plum tick | fixed |
| A13 | Rail foot | empty | one line of counts ("174 PACs in file · 174 shown · 3,978 rows in file · …", whole text on its title; progress and errors still show whole), then "Import a file" and "New snapshot". The rail is one viewport tall and sticky, so the foot is on screen at every scroll position (links bottom 810 at 1440 and 1600, 990 at 1920) | intended (prompt item 2 puts the links there; tests read the status region). Fix round 1: R06-16, D2 |
| A14 | Fourth tick | not drawn | opens nothing; the rail shows "Close a pane to open another." in `--muted` (rgb 98,89,110) | fixed (prompt) |
| A15 | Two panes | 497 and 574 wide (unequal) | 532 and 532 (halves); 452 each at 1440, 692 at 1920 | intended (prompt: "two panes split the area in halves") |
| A16 | Three panes | not drawn | thirds: 352 at 1600, 298 at 1440, 458 at 1920 | fixed (prompt) |
| A17 | Overline | 12px uppercase | 12px uppercase, .03em tracking | fixed |
| A18 | Pane title | B19: 26px title case (illustrative); board 3: about 21px, the FEC name in capitals | 21px/24px serif; the data's own name, clamped to two lines, with the full name on the title attribute | intended (board 3 wins inside a pane; names are data) |
| A19 | Tag row | B19: chip · id. Board 3: chip, id · "All cycles" | board 3's: category chip (21px, `#e7e0ec`), committee id · cycle | fixed (board 3) |
| A20 | Summary \| Map \| Rows | 32px tall, 169px wide | 32px tall, 189px wide | intended (Arial fallback is wider, README fonts note) |
| A21 | Close (×) button | board 3 only | 32x32 beside the segments | intended (board 3 wins) |
| A22 | Gold selected segment | B19 `#e2bf6e`, board 3 `#eac670` | `#eac670` on Summary and on Raised | fixed (approved board-3 exception to one-gold, 00_README Colour rule) |
| A23 | Header on narrow panes (≤440px content: two panes at 1440, three anywhere) | not drawn | the view buttons move above the overline | intended (the title would otherwise get 170px) |
| A24 | Figures box | 71px, four across, no sub-captions | 76px, four across down to a 400px pane (two panes at 1440: 416 x 70, four across); 2 x 2 below 400 (three panes) | fixed (fix round 1, R06-13 / D8). The notes are on each figure's title, `data-note` and About these figures |
| A25 | By cycle labels | two lines ("2025– / 2026") | one line ("2025–2026") | intended (prompt item 3, "one-line year labels") |
| A26 | Where it came from | 198 x 145, Raised gold | 230 x 145; stacks under By cycle on narrow panes | fixed |
| A27 | Top contributors | NAME / AMOUNT header, 3 rows | the same (3 rows; the rest listed in About) | fixed |
| A28 | Source line and About these figures | board 3 only | present, as board 3 | intended (board 3 wins) |
| A29 | Pane height | 490 (72–562) | 558 | intended (A24 +5, A28 +35, taller name and tags) |
| A30 | Compare card | "Compare" 28px serif, a "Top districts · Map" button, one-line caption, METRIC header row, 4px bars, row pitch about 20px | the same; row pitch 20px | fixed |
| A31 | Compare rows | B19 omits "Rows excluded by the workbook" | shown | intended (board 3 and prompt item 4) |
| A32 | Card colour | `#fcfaf8` | white (build 01's `.card`) | intended (shared primitive; 3 levels) |
| A33 | Empty state | not drawn | the rail stays; the panes area shows one line, "Tick a PAC on the left to open it here.", and no card | fixed (prompt item 5) |
| A34 | Split with Graph | bordered, 31px, flush right (x 1460–1576) | the shell's `#split-view` (40px) at x 1203–1318, 260px in from the edge (`workspace-polish.css:218`) | **open**: build-01/02's file; `requests\workspace_polish_split_view.patch` puts it at 1463–1578 (checked by injecting the rule through the CSSOM on :8816) |
| A35 | Fonts | Freight Text, Articulat | Georgia and Arial fallbacks | intended (D-050; README fonts note) |

## B. Enlarged map: boards 6 and 7 (1600x900)

| # | Element | Board | Build | Status |
|---|---|---|---|---|
| B1 | Head | overline, PAC name about 40px serif, Back to panes at the right; no card | overline (12.5px caps) and 40px serif name on the page; Back to panes 127 x 37; the panel chrome is gone | fixed |
| B2 | Name | one line (illustrative "Mortgage Bankers Association PAC") | the FEC name wraps to two lines | intended (data) |
| B3 | Head position | overline cap top about y 30 | box y 26 | fixed |
| B4 | Toolbar | one row: Raised \| Spent, cycle, LAYER segments, search, + −, Reset view (Collapse on board 7) | one row (76px) at 1440, 1600 and 1920, single and compare: Raised \| Spent, cycle, LAYER, "Compare with…" (one select), search, + −, Reset view. No Find button (Enter searches); Enlarge is an icon on the map card. Search 197 / 225 / 545px wide | fixed in fix round 1 (R06-04 / D3). At 1440 the row is tightened (segments 8px padding, 12.5px text) |
| B5 | Control sizes | Raised \| Spent 40px, Layer 34px with a LAYER caption, selects and search 37px, round ± 37px, + first | the same | fixed |
| B6 | Layer label | "ZIP code" | "ZIP code" (was "ZIP points") | fixed |
| B7 | Zoom readout "1.0×" | none | kept for screen readers, visually hidden | fixed |
| B8 | Default layer | State | State | fixed in fix round 1 (R06-07): applied under the README's binding-board rule; the map suites choose Congressional district themselves. **Paul to confirm** (one line, `mapStateFor`, if the district default should return) |
| B9 | Kinds line ("All receipts … · Contributors $17,575") | none | gone: RULING A's note is screen-reader text and the cycle chip's title; the kind toggle is a legend group; the reconciliation is the ranked card's foot | fixed in fix round 1 (R06-05 / D5a) |
| B10 | Map and ranked cards | 806:514 | 816:520 | fixed |
| B11 | Filter / Sort / Pin card above the ranked list | none | folded into "Filter, sort and pin" at the foot of the ranked card (closed by default); place names are not underlined | intended (tested features kept out of sight; fix round 1, R06-16 / D5b) |
| B12 | Legend | a card at the map card's bottom left, under the geography | a compact card (555 x 96) at the map card's bottom left, under the geography, inside the map card | fixed in fix round 1 (R06-06 / D5c). The interaction suite's "heat index never overlaps geography" still holds (legend top ≥ svg bottom) |
| B13 | Legend wording | "Amount (heat)" over "$1K – $100K+", "Donors (circles)" 1 2–5 6–10 11+ | "Amount (heat)" over the view's own range ("$250 – $10,950"), "Donors (circles)" 1 2–5 6–10 11+, and a third group "Shown" with the kind toggle ("Contributors · $17,575"); "visible map · logarithmic scale" and "Rose: net reversal · Unfilled: no mapped amount" are on the card's title and in screen-reader text | fixed (wording); the "Shown" group is intended (R06-05 moved the kind toggle there) |
| B14 | Zoomed (board 7) | ← Back › United States › Texas › TX-19, district as the title | "← Back United States › Indiana › IN-05", title "IN-05: Congressional District 5", the PAC's name as the overline; no region step, no "District" tag (screen-reader text only) | fixed in fix round 1 (R06-08). **Paul to confirm**: the overline keeps "whose money" on screen; the interaction suite asserts it there |
| B15 | Zoomed right card | Donors in TX-19: contributor, city · ZIP, employer, amount; no word broken | the same, with each row's FEC filing link or "FEC filing link unavailable" under the amount. Columns size to their content (`table.map-donors`, auto layout) and wrap only between words: at 1440 the four headers are 106 / 86 / 119 / 96 px and one line (38px) each, and no word in any header or cell is split across lines (checked word by word with range rects at 1440, 1600 and 1920); no sideways scroll | fixed in fix round 2 (R06b-02; was "CONTRIBUTO/R", "MERCHANT/S"). Paul's 09-22 citation work kept. Names and employers stay in the FEC's capitals and wrap between words where the card is narrower than board 7's |
| B16 | Locator inset | bottom right of the map | bottom right of the map, 14px in from the map's right and bottom edges (1440: x 550, y 337, 112 x 71 in a 676px plot whose map ends at y 423); shown only when zoomed in; hidden while comparing and on phones | fixed in fix round 2 (R06b-05; was top right) |
| B17 | Enlarge / Collapse | board 6 ends the row with "Collapse" | a 34px icon at the map card's bottom right (hidden while comparing and on phones) | intended (fix round 1, R06-14: the row cannot hold it beside the compare picker; the zoom-survives-enlarge feature stays tested) |
| B18 | Ranked card | 10 rows and "located $17,575 · unlocated $0" | the card is the map card's height and its list scrolls inside it (about 6 rows at 1600, under the reconciliation line, the geocoding note and "Filter, sort and pin"); a one-page list shows no pager | open (minor): the reconciliation and geocoding lines are tested wording |
| B19 | Source line under the map card | none | "▸ Census congressional and state boundaries · Congress 119. Source details" (a closed disclosure; its text follows the layer, e.g. "ZIP/ZCTA internal points · Approximate locations, not donor addresses") on boards 6, 7 and M13 states (1440 single: y 804–833) | intended (fix round 2, R06b-05): pre-existing geography provenance; the boundary vintage and the "not donor addresses" caveat must stay on screen, and the map controls help sits inside it |
| B20 | "Clear" on the zoomed right card | none (board 7 leaves the place with "← Back" in the trail) | a "Clear" link at the card's top right, beside "Donors in IN-05"; "← Back" is in the trail as well | intended (fix round 2, R06b-05): pre-existing control that drops the place focus without leaving the zoom; both map suites click it (`.map-clear-focus`) |
| B21 | Zoomed card pager and count | "Showing 14 of 14 · click a circle to filter" | "Source page 1 · cycle 2026", "Previous source page" / "Next source page", and "85 matches on this 100-row source page, not all donors in this place. Source has 103 rows in this cycle. · $17,575 located + $0 unlocated = $17,575 reported receipts" | intended (fix round 2, R06b-05): an imported file's rows reach the browser 100 at a time, so the card cannot honestly say "14 of 14"; the pager and the "not all donors" wording are asserted by the interaction suite (steps at lines 378–381) |
| B22 | Legend titles on the zoomed screen | "District funding (raised)" / "Donor ZIP locations" | "Amount (heat)" / "Donors (circles)" (and "Shown") | intended (fix round 2, R06b-05): one wording on boards 6, 7 and M13; board 6 and M13 use "Amount (heat)" / "Donors (circles)", and the zoomed screen is the same map, so its legend does not change words when you zoom. **Paul to rule** if board 7's layer-specific titles should replace them on the district layer |

## C. Two-cycle compare: board M13 (1600x900)

| # | Element | Board | Build | Status |
|---|---|---|---|---|
| C1 | Compare control | "Compare [2025-2026 ▾] with [2023-2024 ▾]" after Layer | the same; the cycle select moves into the phrase. "None" returns to board 6's single map | fixed |
| C2 | Map cards | 444 and 455 wide, pills 131 x 34 at the top left | 456 and 456; pills 131 x 34 (`--scope-1` purple, `--scope-2` teal, 19px bold) | fixed |
| C3 | Map card height | 444 x 470, the map filling the card | the card is as tall as its map: the cycle pill's 56px band, then the map at the card's full inner width, then 12px. Geography box inside card A: 1440 card 376 x 289, map 328 x 209 at y 59 (21px below); 1600 456 x 339, map 403 x 256 at y 60 (23px below); 1920 616 x 439, map 554 x 352 at y 61 (27px below). The map fills 72 / 76 / 80% of the card's height and 87–90% of its width | fixed in fix round 2 (R06b-04). Round 1's "fixed" was wrong: the 444:470 card left 113px blank above and 77px below a map filling 52% of it. The 975x610 projection cannot fill a 444:470 card without cropping (`slice` would cut the coasts); M13's invented maps are drawn taller than that projection, so the card now follows the map's proportion rather than the board's |
| C4 | Zoom and pan | the same on both maps | identical transforms after a drag on map B, a ctrl-wheel on map A, and ArrowLeft and + on map B (scratch `mapq.log`); reduced motion lands a fly instantly and in step (`measurements.json` `reduced`) | fixed |
| C5 | Heat scale | one legend | both maps paint to ONE range, the union of the two cycles over the visible area (`rangeFor`/`unionDomain`, unit-tested), so their colours compare | fixed |
| C6 | Shared legend | under both maps | a copy of the first map's legend card under both (925 x 131); the per-map legends and locator are hidden | fixed |
| C7 | Changes card | "Biggest changes by state", 415 wide, 8 rows above the foot: name, two bars, signed change | the same, 415 wide; all 8 rows sit above the foot with no scrolling at 1440 (8 x 39px), 1600 (8 x 45px) and 1920 (8 x 57px). A row keeps M13's 61px pitch when the card has room and gives it up to its content (38px: 16px name line, two 6px bars) when it has not; the card is the map column's height, so with the shorter compare cards (C3) the pitch is what gives. The title follows the layer ("by district", "by ZIP code") | fixed in fix round 2 (R06b-03; round 1 held 6 of 8 at 1440, row 7 cut mid-row). Also measured on the district layer at 1440: "Biggest changes by district" stays one line (32px) and 8 of 8 rows fit (8 x 39px). A title long enough to wrap would take 32px from the list, which would then scroll |
| C8 | Change bars | both purple shades | `--scope-1` and `--scope-2`, the pills' colours | intended (prompt item 7: "two thin bars in the two cycle colours") |
| C9 | Change colours | green up, red down | teal (`--acu-teal`) up, `--chart-negative` down | intended (Don't-copy: "green change text (use teal)") |
| C10 | Card foot | one line, "located $X · unlocated $Y" | one line, the first cycle's ("2025–2026 located $17,575 · unlocated $0"); both cycles are on its title | fixed in fix round 1 (R06-15) |
| C11 | "8 of 11 places that changed" | none | on the heading's title and in screen-reader text | fixed in fix round 1 (R06-15) |
| C12 | Compare in the URL | not drawn | evidence.js writes `<pane>.compare` and restores it (only a cycle the pane's source records); scope.js drops the key until it lists it | **open**: build 02's `scope.js`; `requests\scope_pane_compare.patch` (scope.js, scope.test.js, url_scope.json: 79/79 in a scratch mirror, the new test red on today's scope.js) |
| C13 | M13 typo "Local deconnection", near-identical invented maps | — | not copied | intended (Don't-copy) |
| C14 | Reset view and Find while comparing | both maps move | both maps fly together: zoom 1.96/1.96 → Reset 1.000/1.000 (at 300ms and 2.8s) → Find "TX" 2.593/2.593 at 1440, 1600 and 1920 | fixed in fix round 1 (R06-01); a negative control with the second map's render not quiet reproduces the old 1.96/1.96 |

## D. Checks the prompt names

- **Identical zoom and pan after drag, wheel and keyboard:** yes (C4).
- **A fourth tick opens no pane:**
  - panes stay at 3, and the refused tick is taken back;
  - the note reads "Close a pane to open another.";
  - checked in the panes suite (step 19) and in the proof captures (`fourth_*`).
- **No internet requests:**
  - every proof page blocked and counted non-local requests: 0 (`report.json`, scratch);
  - the panes suite's off-origin check still passes.
- **Horizontal overflow:** none at 1440, 1600 or 1920 (`scroll.doc == scroll.view` in every state).
  - At 390px, the map's first cut overflowed by 16px. The Layer segments showed and a heading was too wide. It is fixed with a phone rule and re-measured: scroll 358 = width 358.

## E. What was not changed

- `evidence_geo.py`: no server change.
- Paul's 09-22 citation work, byte-identical:
  - `evidence.js` lines 63–126;
  - `workspace.css` lines 880–887;
  - `test_evidence_geo.py` and `evidence-citations.test.js`.
- `workspace.css` is append-only: the pre-edit file is an exact byte prefix of the new one.

---

## Fix round 1 (2026-09-22, evening)

Reviewer defects R06-01…R06-16 and D1…D11, each with its action. Captures and measurements are regenerated (`measurements.json`, every image in this folder; new states `06_cycle-chip-changed_*` and `06_three-panes-scrolled_*`).

| Defect | Action |
|---|---|
| R06-01 (blocker) | fixed. Root cause as reported: `renderMap` re-rendered map B, whose closing transform echoed through `onView` and mirrored B's stale view onto A, cancelling A's fly. `evidence-map.js` `render` takes `view.quiet` (no echo) and `mirror` leaves a fly already heading to the same target; `evidence.js` renders map B quiet. Browser step added (`test_evidence_map_browser.cjs` step 23). Negative control: without `quiet`, Reset stays 1.96/1.96 |
| R06-02, D4 | fixed. `evidence_csv.Store.committee_figures` (sqlite `totals`, cached by size and mtime) adds `receipts`, `receipts_channel`, `receipts_by_cycle` to each committee in the import listing; the rail ranks and shows them. Unit test added; red on the old code |
| R06-03 | fixed. A tick is the PAC: it follows the PAC's open pane whatever the Cycle chip says (the row's title says "open on …"); untick closes it; no refusal for an open PAC. Panes-suite step 20; step 31 re-homed (the second cycle of one PAC is added through the hidden `#evidence-add` path) |
| R06-04, D3 | fixed (B4) |
| R06-05, D5a | fixed (B9); `.layer` assertion re-homed to `.map-legend-card .layer` |
| R06-06, D5c, D5d | fixed (B12, B13) |
| R06-07 | applied, Paul to confirm (B8) |
| R06-08 | applied, Paul to confirm (B14) |
| R06-09 | evidence.js side done; scope.js is build 02's (C12, request patch) |
| R06-10, D9 | fixed (C3) |
| R06-11, D7 | fixed (A8, A9) |
| R06-12 | open, request patch to the workspace-polish.css holder (A34) |
| R06-13, D8 | fixed (A24) |
| R06-14 | fixed (B17) |
| R06-15 | fixed (C10, C11) |
| R06-16, D5b | fixed (A13, B11) |
| D1 | applied: both map suites now tick the rail (the request patches' hunks), plus the re-homes above; 25/25 and 22/22 |
| D2 | fixed (A13): sticky rail, one viewport tall |
| D6 | fixed: `removePane` takes the note down below the ceiling; panes-suite step 20 closes a pane with its × and asserts it |
| D10 | B8 and B14 applied (above); C12 requested; the panes suite now asserts the note's colour equals the resolved `--muted` |
| D11 | disproved in part: Paul's citation block was and is at `evidence.js` 61–126 (`sourceAnchor` 63, `filingCitations` 100–126), byte-identical to the pre-build file (3,636 bytes); the unit-suite line in HANDOFF is corrected (324/324 now, 321/321 before this round) |

Also found and fixed while running the suites: choosing a saved snapshot left the previous source's PACs ticked-able in the rail while the snapshot was read, so a tick in that window opened a pane for a committee the snapshot does not hold (the panes suite's snapshot step passed only because its first row happened to be CULAC in both sources). The rail now says "Reading the saved snapshot…" until the snapshot is read. At 390px the map is one column again (the ranked card had been squeezed to 133px beside it).

---

## Final fix round (fix round 2, 2026-09-22, night)

Reviewer defects R06b-01…R06b-07. The map captures and their side-by-sides are regenerated (`06_map-single_*`, `06_map-zoomed_*`, `06_map-compare_*`, `06_map-compare-reduced-motion_1440x900`, `build-only_06_map-compare_full_1440x900`); `measurements.json` has the new map, zoomed, compare and reduced keys merged over round 1's (pane keys are round 1's; the pane board did not change). Every proof page: 0 page errors, 0 console errors, 0 off-origin requests.

| Defect | Action |
|---|---|
| R06b-01 (major) | fixed. Cause confirmed as reported: the step's `waitStatus` is already satisfied by the template's first "Finding imported files and saved snapshots…" while `#evidence-list` is still empty. Step 3 now waits for `#evidence-list .evidence-list-empty` to read "Choose a source above…" or "Nothing imported yet…" before reading the rail. Three consecutive runs recorded in HANDOFF |
| R06b-02 (major) | fixed (B15): `table.map-donors` (both focused-place tables) uses auto layout and wraps between words only; no header or cell word is split at 1440, 1600 or 1920 |
| R06b-03 | fixed (C7): 8 of 8 rows above the foot at 1440 (39px pitch), 1600 (45px) and 1920 (57px) |
| R06b-04 | fixed (C3): the compare cards follow the map's proportion; the geography fills 72–80% of the card's height (was 52%) |
| R06b-05 | named: B16 (locator, now bottom right: fixed), B19 (source line: intended), B20 (Clear: intended), B21 (source pager and count: intended), B22 (legend titles: intended, Paul to rule) |
| R06b-06 | still **open**, other owner: `scope.js` is build 02's (`PANE_FIELDS` at line 26 still lacks `compare`); `requests\scope_pane_compare.patch` unchanged and not applied here (C12) |
| R06b-07 | still **open**, other owner: `workspace-polish.css` is single-writer; `requests\workspace_polish_split_view.patch` unchanged and not applied here (A34). Not overridden from `workspace.css`, which would give one control two sources of truth |
