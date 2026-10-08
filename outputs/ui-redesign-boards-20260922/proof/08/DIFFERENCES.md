# Build 08 (Collection, board B22): differences

Board frame: `B22_collection_run_card.webp` is 2000x1131 for a 1600x900 CSS viewport (1.25 board px per CSS px). Board numbers below are ink extents from the board divided by 1.25 (`scratchpad\mentat\build08\measure.py`); build numbers are the same pixel tests on `shots\running_1600x900.png` (`measure_build.py`) and `getBoundingClientRect` boxes in `measurements.json` (every state at 1440x900, 1600x900, 1920x1080). All positions are CSS px.

Side-by-sides: `08_<state>_<1440|1600|1920>.png` (board left, build right) for running, stopped (resumable), completed, empty, history, folder (working-folder popover open).

## A. Page header and folders

| # | Difference | Board | Build | Status |
|---|---|---|---|---|
| A1 | Sidebar: B22 draws icons, a spaced wordmark and a filled plum active item | - | build 01's sidebar (tagline, pale lilac active item) | intended: settled design call 9 and "its sidebar follows 01"; the sidebar is 40px narrower than B22's, so everything right of it starts 38.8px further left (card x 264.8 on the board, 226 in the build) |
| A2 | Page title "Collection" smaller | ink 180.8 x 29.6 (about 41px type) | ink 136 x 23 (build 01's shared 31px title) | open (shell holder / Paul): the title is the shell's, one size for every view; M4 draws it at 31px, B22 at about 41px |
| A3 | Everything under the header sits 15px higher | title ink top 27.2, tabs text top 94.4, card top 150.4, card bottom 808, note top 823.2 | 15, 80, 135, 793, 807 | open, follows A2: the shell's header row is shorter than B22's. Spacing inside the view matches (tab text to card top 56.0 board / 55 build; card height 657.6 / 658) |
| A4 | Status pill | 95.2 x 29.6 at x 1480.8, teal | 99 x 30 at x 1479, `--acu-teal` | fixed (y follows A3). Grey "Stopped" (#7a7480), `--chart-negative` "Failed", plum "Completed" per prompt item 1 |
| A5 | Folder tabs | text 16.8px tall; History +157 / Archived +278 from the first tab | 15px; +152 / +273 | fixed within the font fallback (Arial for Articulat, README fonts note) |
| A6 | Active tab underline | 123 x 3.2, gold | 119 x 3, `--acu-gold` | fixed |
| A7 | Tab rule | 1px across the content width | 1px at y 109-110 | fixed |
| A8 | Run select + "Archive run" row | not drawn (one run) | `#run-toolbar` shows only when In progress holds two or more runs; "Archive run" / "Restore run" sits in the card footer as a secondary button whenever the run can be archived | intended: prompt item 2 ("stay reachable"); B22 shows a single running run, which cannot be archived, so the running state matches the board |

## B. Run card

| # | Difference | Board | Build | Status |
|---|---|---|---|---|
| B1 | Card surface | warm near-white (251,249,247) | white, build 01's `.card` | intended: build 01 token |
| B2 | Run title | ink 268 x 29.6 | ink 295 x 30 | intended: Georgia fallback for Freight Text is wider (README fonts note); size matches |
| B3 | Subtitle | "Started Sep 21, 3:04 PM · 10 companies · cycles 2022, 2024, 2026", 14.4px ink | same pattern, 14px ink | fixed; names, counts and times are illustrative (Don't copy) |
| B4 | Overall bar | 10.4px tall, track to x 1382.4 (rel. card) | 10px, track to 1386 | fixed (the board wins over the prompt's 8px) |
| B5 | Bar and pill teal | (44,137,138) | `--acu-teal` (50,122,122) | intended: shared token, not a new colour |
| B6 | Progress label | "64% · about 38 min left" at x 1397.6-1558.4 | "52% · about 38 min left" at 1402-1559 | fixed. Stopped reads "52% · Stopped", completed "100% · Finished"; "Elapsed <t>" appears while the timer is still estimating | 
| B7 | Stepper | marks 30px, columns at 0 / 29.7% / 56.8% / 86% of the content width | same fractions (grid 29.7fr 27.1fr 29.2fr 14fr), 30px marks (26px hollow), 2px teal line after a done step | fixed |
| B8 | Stepper "halted" state | not drawn | a stopped or failed run shows its last stage as a grey ring | intended: prompt states (stopped, failed) not on the board |
| B9 | Table columns | Progress / Receipts / Checkpoint at 27.8% / 58.3% / 80.4% of the card | 28.1% / 58.6% / 80.6% | fixed |
| B10 | Row pitch | 42.7px (separators 420 ... 719.2) | 42.7px (405 ... 704) | fixed |
| B11 | Row bars | 210 x 10.4 | 210 x 10 | fixed |
| B12 | Queued rows | dashes in Progress, Receipts and Checkpoint | empty track and "Queued"; Receipts and Checkpoint blank | intended: Don't-copy ("they read Queued"). A stopped or failed run says "Not started" instead, since nothing is queued |
| B13 | Row percentages | 100 / 100 / 82 / 64 / 40 | finished search tasks over the run's cycles (3 cycles: 100 / 100 / 67 / 67 / 33) | intended: prompt item 3 (tasks finished over the company's tasks); percentages move in thirds when a roster has three cycles |
| B14 | Failed tasks in a row | not drawn | "· N failed" after the percentage when a company's task failed | intended: real data |
| B15 | Footer buttons | Pause 122.4 x 40.8, folder 209.6 x 40.8, gold 180.8 x 40.8 | 123 x 40, 214 x 40, 178 x 40 | fixed |
| B16 | Gold button count | 1 | 1 in every state (measured: running, stopped, completed, history, folder = `#view-partial-results`; empty = `#empty-load-sector`) | fixed; asserted in test_console_browser.cjs |
| B17 | Completed runs | not drawn | the gold button reads "View records"; no Pause/Stop/Resume | intended: prompt states |
| B18 | Working-folder popover | not drawn | 480px popover above the button with both paths, the Explorer note and "View completed reports"; Escape and an outside click close it | intended: prompt item 3 |
| B19 | Note under the card | ink 246.4 x 12 | ink 236 x 11 | fixed within the font fallback; shown only while a run is active |

## C. Below the card, empty state, History

| # | Difference | Board | Build | Status |
|---|---|---|---|---|
| C1 | Disclosures | not drawn (below the fold) | "Coverage unverified · Details", Workers, Activity log, Run events, Coverage, Report freshness, all closed | intended: prompt item 4. The first begins at y 846 at 1440x900, under the fold like the board |
| C2 | Empty state | not drawn | "Start with a list of names." in a card with the gold "Load a sector" (opens Loading) | intended: prompt item 5 |
| C3 | History / Archived | not drawn | compact cards (title, created date, state pill, Reports link), newest first; the selected run opens in full in its place in the list | intended: prompt item 6 |

## D. Measured checks

- Overlaps among the footer buttons: 0 in every state and size. Horizontal overflow: none at 1440, 1600, 1920 or 390 (mobile).
- Console errors while capturing: 0.
- Queued rows read "Queued" (running) / "Not started" (stopped): `measurements.json` `rows`.
- `#stop` and `#resume-run` keep their ids, listeners and titles (app.js 672, 686); `#stop` reads "Pause" while a run with workers is active, "Stop" otherwise, and hides once the run ends; `#resume-run` shows for a resumable stopped/failed run.

## E. Open

A2 and A3 (the shell's page-title size and header height against B22). Nothing else is open.
