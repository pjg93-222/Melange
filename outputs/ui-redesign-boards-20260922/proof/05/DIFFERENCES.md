# Build 05 (Cross-reference): differences from board B16

Built 2026-09-22 on `codex/mentat-crypto`, uncommitted. Paul's console on port 8806 was not touched; every capture comes from a read-only instance on port 8815.

**Frame.** `B16_cross_reference.webp` is 2000x1131: a 1600x904.8 CSS frame at 1.25x on both axes. Every board number below is board px / 1.25.

**Method.**
- Positions come from `getBoundingClientRect` (text boxes through a DOM Range) on the build, and from ink scans of the board.
- Colours are compared with one statistic on both images: the mean of the darkest 6% of pixels inside the same text box, with the build captured at the board's own scale (1600x900 at 1.25x).
- Status key: **fixed** = the build matches the board; **intended** = a deliberate difference, reason given; **open** = Paul or another lane has to act.

**Captures.** Two things are hidden in every proof image, and neither exists on Paul's console:
- the read-only preview line ("Read-only preview · the original console continues managing your active collection."), which only a `--read-only` instance prints;
- the shell's stale-build banner, which appears whenever another builder edits a file after the proof console started.

## A. Shell (other lanes' files)

| # | Difference | Status |
|---|---|---|
| A1 | B16 draws a 216px sidebar with icons and a dark plum active fill. The build has build 01's 200px text-only sidebar with the pale lilac active item. As a result the board's content starts at x 240.4 and the build's at 226, and the build's content is 14px wider. | intended: approved call 9 (one sidebar everywhere, M4's), owned by build 01 |
| A2 | Title text: the board reads "Cross-reference", the build "Cross-reference the evidence". The build's text is set in `app.js:67`, a file in build 02's set. | **open**: request R1 |
| A3 | Title size: the board's serif title has a 28px cap height (cap top 19.2, baseline 47.2), about 40px type. The build's shell title is 31px/34px (baseline about 40.9), which build 01 measured off M4. | **open**: B16 and M4 disagree on the shared title. Paul to rule: one shell size, or B16's size on this view. |
| A4 | Because of A3, the gap from the title baseline to the subtitle baseline is about 30px in the build, 24px on the board. The subtitle itself sits at the board's absolute position (baseline 71.2 against 71.0). | follows A3 |
| A5 | Fonts: Georgia and Arial stand in for Freight Text and Articulat. The largest visible effect: the active tab's "Contradictions" in Georgia Bold is 115px wide against 101px on the board, so its gold underline is 164px long against 149px, and its count sits 13px further right. Most other text runs a few px wider or narrower than the board. | intended: 00_README (fallback is the expected result; no web fonts) |
| A6 | Canvas: the board samples #fbf7f4; the build uses #f7f3ee (`--analysis-paper`, build 01b). | intended: build 01's shared canvas |
| A7 | The sidebar footer keeps "build … · port 8815 · up since …" on three lines. | intended: build 01's B2 |

## B. Header

| # | Difference | Status |
|---|---|---|
| B1 | Subtitle wording now matches the board: "Inspect saved contradictions, matched refunds and unusually large receipts. Read-only." (was "…matched refunds, and unusually large receipts."). 15px, baseline 71.2 (board 71.0), colour #525064 sampled from the board. | fixed |
| B2 | Refresh saved evidence: board box x 1400.0–1578.4, y 24.8–64.0; build 1399.5–1578, 25–64. 13px weight 500, 6px radius, border #e6e4e3 (board #eae9e5). Text colour measures identical to the board. | fixed |
| B3 | The visible status line ("Latest run · Saved evidence refreshed…") is gone. `#xref-refresh-status` is now the button's tooltip and a visually hidden live region: on all 17 captures the tooltip equals the status text. | fixed (prompt §1) |
| B4 | "Refreshing…" (muted, left of the button) shows only while a refresh runs: at once for a click (for at least 0.4 s), and for the 5-second poll only if the poll takes longer than 0.4 s, so the poll never blinks. A failed refresh leaves "Refresh failed" there until one succeeds. | intended: the board shows the idle state; the failure note keeps a failed refresh from being silent |

## C. Run strip

| # | Difference | Status |
|---|---|---|
| C1 | Card: board y 104.8–152.8; build y 104.8–152.8 exactly, 48px tall. Build x runs 226–1578 (A1). | fixed |
| C2 | Pill: board 191×23 starting 13.6px into the card; build 192×23 starting 14px in. Background #e9e3fc and text colour sampled from the board (text colour measures identical). | fixed |
| C3 | Facts start 235.8px into the card (board 235.6). The later facts drift right by 2–4px (font widths, A5). Separator "·" has 15.5px each side, colour #7d7d83. | fixed |
| C4 | "run 2026-09-21 05:51" is the run's start in UTC, read from its run id, as the board shows it. The tooltip adds the full run id, the report's generation time and "times in UTC". A run id without a time falls back to the generation time, then to the id itself. | intended (tooltip is an addition) |
| C5 | "Companies in scope ›" sits 19px from the card's right edge (board 20). It is a button that opens the company list inside the strip, and its chevron turns down when open. | intended: the board shows it closed |
| C6 | A visually hidden heading, "What this run covers", names the strip for screen readers. | intended: accessibility; it is also the heading `test_console_browser.cjs:242` waits on |

## D. Tabs

| # | Difference | Status |
|---|---|---|
| D1 | Label starts, measured from the content edge: board 0 / 192.0 / 360.8; build 0 / 188.1 / 363.4. | fixed within 4px (the remainder is A5) |
| D2 | Each count follows its label by 15px (board 15.2). Counts are 13px sans, as drawn. | fixed |
| D3 | Underline: 3px at y 203.8–206.8 (board 204.0–207.2), 8px above the tab rule, as on the board. Colour: the board's line samples a darker ochre (about #b08028); the build uses `--acu-gold` #eca91c. | intended: prompt §3 names `--acu-gold`, and M4's gold samples at that token, so the console keeps one gold |
| D4 | Tab rule: 1px #e1dfde at y 214.8 (board 215.2). | fixed |
| D5 | **Refunds count: the board shows "Refunds 0", the build "Refunds 43".** | intended: prompt §3 counts matched plus unmatched rows (0 + 43 in this run); the board's 0 equals matched refunds only. **Paul may prefer matched-only**: a one-line change, after which the tab would read 0 while still listing 43 unmatched adjustments. |
| D6 | Each tab reserves its bold width with a hidden bold twin, so choosing a tab never moves its neighbours (tested). | intended (behaviour, not on the static board) |

## E. Filter row

| # | Difference | Status |
|---|---|---|
| E1 | Widths: board 261.6 / 260.8 / 288 / 484px with gaps of about 15px; build 264 / 264 / 290.4 / 488.5px with 15px gaps (the same shares of a 14px wider row). Height 40px, y 235.8–275.8 (board 235.6–275.6). | fixed |
| E2 | The selects are build 01's `.chip-select` at the board's single-line size: its small label line is visually hidden, and the first option ("Company", "Cycle", "Description", "Entity") doubles as the label, as drawn. 13px text, 6px radius, border #e6e4e3 (board #e8e6e5). | intended: the primitive, sized to B16 |
| E3 | The chevron is the primitive's (about 8.5px wide; board 8). The search icon is 16px (board 15.2); placeholder colour #787885 sampled from the board. | fixed |
| E4 | Options come from the active tab's saved rows. A blank value is listed as "Company not stated" or "No receipt description saved". Each tab keeps its own filters and page. | intended |

## F. Table card

| # | Difference | Status |
|---|---|---|
| F1 | Card: board y 299.2–845.6; build y 299.2–846.2. The width cap of about 1,260px is gone: the card runs 226–1578. | fixed |
| F2 | Header row 51px, background #f8f8f8, rule #ebebeb, 13px labels at #414158 (colour measures identical). Label centre 326.3 (board 326.4). | fixed |
| F3 | Body rows are 43px (board 42.9): row 10 ends at 781.2 (board 780.0). Text centre 375 (board 374.8). Row rules #f1f1f1. | fixed within 1.2px |
| F4 | Column starts as a share of card width, build (board): Cycle 30.1% (30.1%), Description 37.8% (37.8%), Role 54.7% (54.7%), Amount's right edge 77.1% (77.0%), FEC record 81.8% (81.9%). | fixed |
| F5 | At 1440 the board's share for Amount (11.2%) is 134px, too narrow for "Amount removed". The column now keeps its content width (147px) and Company gives up the difference, so the header stays right-aligned over its figures. Below 900px of card width the table scrolls sideways inside the card. | intended: the board's proportions cannot hold the header at 1440 |
| F6 | **Record ids use the table's sans at 13px with tabular figures, not mono** (prompt §5 says mono 13px). They are shortened in the middle only above 22 characters (every saved id is 19 digits, so none is shortened today), with the full id in the tooltip. | intended: the board draws them in the sans face, and the board wins on type |
| F7 | External-link icon: 15px outline in the build, about 12.8px of ink on the board. Its right edge is 24px from the card's right edge (board 24.8). It opens `source_url` in a new tab with no referrer; an id whose URL fails the FEC link rule gets no icon. | fixed (size within 2px) |
| F8 | Rows scroll inside the card under a sticky header (tested: the header stays within 1px of the scroll box's top). At 900px tall, ten rows show above the pager, as on the board; at 1080px tall, fourteen. | intended: the board's ten visible rows, 25-row pager and sticky header |
| F9 | The board repeats one record id on seven rows, and its names and amounts are illustrative. | intended: Don't-copy; real data |

## G. Card footer

| # | Difference | Status |
|---|---|---|
| G1 | Pager buttons 34×34, starting 17px into the card (board 16.8), at y 796.7 (board 795.2); "Rows 1-25 of 177" in 12.5px. | fixed |
| G2 | On page 1 the Previous button is disabled (chevron #a09dad); the board draws it enabled. When Next becomes disabled while focused, focus moves to Previous. | intended: behaviour (there is no page before 1) |
| G3 | "How this list is built ⌄" is right-aligned, 13.5px, 19px from the card edge (board 19.2). It is a button that opens the explanatory text under the footer, inside the card. The text is today's, verbatim, under today's section headings: the lede; the contradiction sentence; "These receipts remain counted. Magnitude alone is not a contradiction and never excludes a receipt."; the run's own large-receipt rule (the digest's basis sentence: top 0.1% of the class and at least 20x its median); the refund sentence; and the negative-adjustment caution. | fixed (prompt §6) |
| G4 | When a list is capped, the footer says so (Banking: "4,783 reclassified receipts in this run. The 200 largest are listed here; the saved digest holds the rest."). The Credit Union run is not capped, so this note does not appear in the captures. | intended |

## H. States the board does not draw

- **H1. Refunds.** The card shows "No refund in this run is matched to the gift it reverses." in muted text, then the small heading "Negative adjustments without a matched original" over Company, Cycle, Description, Amount and FEC record. The zero-row state appears twice:
  - `05_refunds_*`: this run has no matched refunds, so that list is empty;
  - `05_refunds-empty_*`: a synthetic payload with both lists empty, since no saved run has zero unmatched rows.
- **H2. Filters.** A filter or search with no match says "No contradiction matches these filters." (or the tab's equivalent), and the pager reads "No rows".
- **H3. Other envelopes.** No digest, running, error and no-run-saved each get a message card. The no-digest and no-run cards show the lede in full.
- **H4. Narrow widths.** At 390, 900 and 1100px the page never overflows sideways. The filters wrap to two columns and then one, the tabs wrap below 761px, and the run facts stack one per line.
- **H5. Motion.** Choosing a tab raises the rows 6px while fading them in, and grows the underline, over 0.22–0.24 s. Both are off under `prefers-reduced-motion` (tested).

## I. D-040 (no totals)

- **In code.** `cross-reference.js` reads only single-row fields (`amount`, `refund_amount`, `original_amount`). The digest's four sums (`linked_amount`, `unlinked_amount`, `non_giving_amount`, `large_amount`) appear only in a comment saying they are never read. Every `total` in the code is a row count for the pager.
- **In the DOM.** On all 17 captures, 302 text nodes carry a dollar figure. Each is either a row amount (`td.number`) or the large-receipt threshold sentence inside "How this list is built" (for example "$10,000.00 or more from an individual"), which is a threshold, not a total. None sits anywhere else.
- **In tests.**
  - `test_cross_reference_view.cjs` renders every tab from a fixture whose sums differ from every row, and asserts that none of the sums is printed.
  - The same file's browser half re-checks the DOM.
- **Outside this view.** The API still sends the four sums (`cross_reference_data.py:161,165,171,175`); that file is not in build 05's set.

## Files

- **Changed:**
  - `mentat/app/templates/view_cross_reference.html` (lines 2–3; mixed endings kept: 5 CRLF + 1 LF);
  - `mentat/app/cross-reference.js` (rewritten, all CRLF);
  - `mentat/app/cross-reference.css` (rewritten, all LF);
  - `mentat/tests/test_cross_reference_view.cjs` (re-homed, all LF);
  - the golden `mentat/app/index.html`, via `render_console.py --write`.
- **Unchanged:** `test_cross_reference_scope_browser.cjs` passes as it was.
- **Proof folder:**
  - `05_<state>_<viewport>.png`: the 17 side-by-sides (board left at 1 CSS px per image px, build right);
  - `build-only\`: the raw captures;
  - `measurements.json` (ignored by git through the root `*.json` rule).
