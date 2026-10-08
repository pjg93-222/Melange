# Build prompt 06 · PAC evidence: pane board (B19) and enlarged-map compare (M13)

**Builder:** one Opus architect or Codex agent, alone in the tree, after 01. **Read first:** `prompts\00_README.md`.

## Visual spec (binding)

- `boards\B19_pac_evidence_panes.webp`: the page with a picker rail and two panes.
- `boards\M13_pac_map_compare.webp`: the enlarged map comparing two cycles.
- Still binding from 2026-09-19: `boards\approved_board3_pac_panes.webp` (the pane design and the Compare table), `boards\approved_board6_map_enlarged.webp` and `boards\approved_board7_map_zoomed.webp` (the enlarged map). Where B19 and board 3 differ inside a pane, board 3 wins.

**Don't copy:** B19's rail reading "Banking" while its panes read "Community Banks", and its rail amounts that don't match the panes; the "2023-2023" label; M13's "Local deconnection" typo and near-identical invented maps; green change text (use teal); every amount.

## What exists today (verified 2026-09-22)

- Template `mentat/app/templates/view_evidence.html` (44 lines): `#evidence-source` (Source), `#evidence-type` (Committee type), `#evidence-find` (Find a PAC), `#evidence-pac` (PAC), `#evidence-cycle` (Cycle), `#evidence-add` ("Add pane", primary), `#evidence-import-open` ("Import a file"), `#evidence-snapshot-open` ("New snapshot"), `#evidence-follow-graph` (checkbox "Follow Graph selection"), an "Open panes" chip row, `#evidence-panes`, `section#evidence-compare`, `section#evidence-map`, `#evidence-empty` ("No PAC pane is open...").
- `mentat/app/evidence.js`: `paneStats()` 524-556, `thumbHtml()` 561-576, `paneHtml()` 578-635 (header; Summary | Map | Rows at 598-603; By cycle 614-617; Top contributors 620-623), `renderPanes()` 735-751, `compareRows()` 819-839, `renderCompare()` 841-863. Enlarged-map controls: `.map-direction` buttons (1726-1729), `#evidence-map-cycle` (1731), `#evidence-map-layer-select` (1455), `#evidence-map-back` ("Back to panes", 1733), the `.map-list` ranked list (1679-1691), `.map-clear-focus` (1678).
- `mentat/app/evidence-map.js` (new, untracked): SVG `.map-canvas` (223-226; keyboard pan and zoom), `.map-viewport`, layer groups, `.map-legend-card` (254) with the heat ramp and donor circles (buckets 1, 2-5, 6-10, 11+ at 45-50), the `.map-locator` inset (314-324). No two-map or compare code exists.
- `/api/evidence-geo` (`server.py` 2486-2493): parameters `source, id, committee, cycle, direction` (default `spent`); the response includes `by_state`, `by_zip`, `by_region`, `kinds`, `cycle`, `reported_total`, `located_total`, `unlocated_total`, `reconciles`.
- Tests: `test_pac_evidence.py`, `test_evidence_geo.py`, `test_evidence_csv.py`, `mentat/app/tests/evidence-map.test.js`, and the browser suite `test_evidence_panes_browser.cjs`.

## Build this, part 1: the pane board (B19)

1. **Layout:** header "PAC evidence" with "Split with Graph" (`#split-view`) at the right. Below it, a left picker-rail card (300px) and the panes area filling the rest.
2. **Picker rail:** the search "Find a PAC" (`#evidence-find`); three `.chip-select`s, Source (`#evidence-source`), Type (`#evidence-type`) and Cycle (`#evidence-cycle`); a switch "Follow Graph selection" (`#evidence-follow-graph`, same behaviour); then the chosen source's PACs ranked by receipts, each row a checkbox, the PAC name, and its receipts at the right (reuse the data behind `#evidence-pac`). Ticking a row opens its pane; unticking closes it; three panes at most (a fourth tick shows "Close a pane to open another." in `--muted`). The rail's footer holds the text links "Import a file" (`#evidence-import-open`) and "New snapshot" (`#evidence-snapshot-open`). The ticks replace `#evidence-add` and the "Open panes" chip row; keep `#evidence-add` hidden if a test drives it and re-home those assertions.
3. **Panes:** exactly board 3: overline "<SOURCE> · <KIND>", serif PAC name, type chip, committee id and cycle; the Summary | Map | Rows `.segmented` (with the gold active item as approved); the four figures (Receipts, Contributors, Rows in file, Cycles covered; no sub-captions); By cycle bars with one-line year labels; the "Where it came from" thumbnail with Raised | Spent; Top contributors in this file; the source line and "About these figures". Two panes split the area in halves, three in thirds.
4. **Compare table** under the panes: board 3's "Compare" card (metric rows Receipts · All cycles, one row per cycle, Rows supported, Rows excluded by the workbook, Top contributor, Category, Source; a thin bar per pane column; the "Top districts · Map" toggle). It exists in `renderCompare()`; restyle only.
5. **Empty state:** the rail stays; the panes area shows one quiet line, "Tick a PAC on the left to open it here." No large empty card.

## Build this, part 2: enlarged-map compare (M13 on boards 6 and 7)

6. **Toolbar** as board 6: Raised | Spent, the cycle select, the Layer `.segmented` (Region, State, Congressional district, State district, ZIP code), the search box "Find a state, district or ZIP", visible zoom buttons (+ and −, beside the existing keyboard zoom), "Reset view", and "Back to panes" (`#evidence-map-back`).
7. **Compare:** after Layer, "Compare [2025-2026 ▾] with [2023-2024 ▾]". When set, the map area shows two maps side by side at the same zoom and pan (moving one moves both), each with its cycle `.scope-pill` at the top left (first cycle `--scope-1`, second `--scope-2`); one shared legend card under both (Amount heat; Donors circles 1, 2-5, 6-10, 11+); and at the right a card "Biggest changes by state" (by the active layer: region, district or ZIP) listing places by absolute change: the name, two thin bars in the two cycle colours, and the signed change at the right (teal up, `--chart-negative` down), with "located $X · unlocated $Y" from the response at its foot. Choosing "None" in the compare select returns to board 6's single map.
8. **Data:** call `/api/evidence-geo` once per cycle with the same `source`, `id`, `committee` and `direction`, and compute per-place change in the browser. No map tiles (D-050): outlines only, as today.

## Acceptance
States at 1440x900 and 1920x1080 beside the boards: the pane board with two panes (B19, with board 3's pane details); the empty state; three panes; the enlarged single map (board 6); zoomed to a district (board 7); two cycles compared (M13); compare under reduced motion. Checks: the two maps keep identical zoom and pan after drag, wheel and keyboard; ticking a fourth PAC opens no pane; the network log shows no internet requests. Suites: `test_pac_evidence.py`, `test_evidence_geo.py`, `test_evidence_csv.py`, `evidence-map.test.js`, `test_evidence_panes_browser.cjs`, `render_console.py --check`.
