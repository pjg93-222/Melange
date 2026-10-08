# Build 07 (Loading) - differences from the boards

Boards: `B20_loading_step1_typing`, `L1_loading_step1_upload`, `L2_loading_step2_review`, `L3_loading_step3_cycles`, `L4_loading_coverage_grid` (2000x1131 = a 1600x900 CSS frame; board px / 1.25 = CSS px). Build: `shots\*_1440x900.png` and `*_1920x1080.png` from `node capture.cjs 8818` (read-only console, every write answered by page.route); side-by-sides `07_<state>_<width>.png` (board left at 1:1 CSS, build right). Numbers are `getBoundingClientRect` values from `measurements.json`.

Proof data: names, counts and dates are fixtures (boards are illustrative). The L4 capture uses a board-like coverage fixture (one verified, one stale, one not-collected cell); `07_L4_real_*.png` shows this computer's own saved coverage (36 rows, all unverifiable, 12 sectors).

Status: **fixed** = changed to match the board; **intended** = kept on purpose (reason given); **open** = Paul's call.

## A. Page header and stepper (all five boards)

| # | Difference | Status |
|---|---|---|
| A1 | Sidebar is build 01's M4 sidebar (200px, tagline, lilac active item); B20 draws a plum pill and L1-L4 a 240px sidebar, so content starts at x=226 instead of 272. | intended (design call 9; prompt 07 "sidebar follows 01") |
| A2 | Page title "Load a sector" is the shell's (build 01): 31px serif, box y 11-45; the boards' title ink is y 24-51 and a few px larger. | intended (shell belongs to build 01) |
| A3 | Subtitle text box y 56-78 (board ink 70-84); stepper circles y 104-142 (board 112-150); cards start at y 174 (board 182.4). Everything below the header is 8px higher than the boards because the shell header is shorter. | intended (follows A2; the subtitle margin was raised 15px to bring the stepper and cards within 8px) |
| A4 | Stepper circles 38px (prompt: 36px; board: 48 board px = 38.4). | fixed (board wins) |
| A5 | Step positions at 1440: 226 / 563 / 900 / 1238; at 1920: 226 / 713 / 1200 / 1686. Board at 1600: 272 / 634 / 1010 / 1400. Steps 1-3 share the row equally with the 1px rule filling each; step 4 ends 6.5% short of the right edge as on the board. | intended (proportional; the board's own spacing is uneven) |
| A6 | Done steps draw the white check with a 2px CSS stroke; the board's check is slightly heavier. | intended |
| A7 | Fonts: Georgia and Arial (Freight Text Pro and Articulat CF are not installed; D-050 forbids web fonts). Georgia's old-style figures show in "2021-22". | intended (README note) |

## B. Step 1, typing names (B20)

| # | Difference | Status |
|---|---|---|
| B1 | The card's serif "Roster" title is replaced by the "Type names / Upload a spreadsheet" switch (L1's control and position); an `sr-only` h2 "Roster" keeps the heading. | intended (prompt item 3 puts the switch at the top of the left card in step 1; B20 and L1 disagree) |
| B2 | Sector is the existing text field `#sector` (maxlength 31) with a list of the saved sectors (datalist); the board draws a select with a chevron. Chrome's list indicator is shown instead of the chevron. | intended (a new sector must stay typeable; CSP `img-src 'self'` refuses a data: chevron) |
| B3 | Each "other name" chip carries a × (board: none). | intended (prompt: "× removes") |
| B4 | At 1440 the first row's two chips wrap (row 83px; board rows 58px at 1600). At 1920 every row is 58px. | intended (real width) |
| B5 | A row with no chips shows the placeholder "Add a name"; the "Add a company..." row shows "Press Enter to add" while focused. Neither is on the board. | intended (discoverability; nothing shows at rest) |
| B6 | Right card reads "3 companies · 8 names to search" (board: 7). The build counts each company's name plus its other names, as the server does. | intended (board numbers illustrative) |
| B7 | Gold "Review names ->" 43px tall, full card width (1051-1393 at 1440); board 43.2px. Back is not shown in step 1. | fixed |
| B8 | Card heights: both cards are at least 100vh - 242px (658px at 900 high); at 1440 B20's left card grows to 695px because of B4, so the draft line sits below the fold. | intended |

## C. Step 1 after an upload (L1)

| # | Difference | Status |
|---|---|---|
| C1 | At 1440 the four column-check chips take two rows (one row at 1920 and on the 1600 board). | intended (width) |
| C2 | Fix round: the preview's chip cells (Other names, Excluded) no longer wrap, rows are 36px (cell padding 3px 12px, chips 24px), type unchanged at 15px/13px. At 1440x900 the footer box is y 778-825 and the card ends at y 850, inside the frame (was 864-911, 11px cut). Only "JP Morgan Chase Bank NA" wraps in its company cell at 1440 (row 47px; board: one line); at 1920 every row is 36px. The preview scrolls inside its own box if a roster's chips are wider than the card. | fixed (R07-2) |
| C3 | Amber note: with two problems it reads "2 names need a decision. You can settle them in step 2."; with one, "<name> is listed under <A> and <B>. You can settle it in step 2." The board's "Citi is also a word in other bank names" describes substring matching the server does not check. | intended (the note states what /api/upload reported) |
| C4 | For an Excel upload the column check is inferred from what the server returned (the browser cannot read .xlsx headers); a CSV or TSV shows its real headers. A missing canonical_name shows the amber cross and the server's message. | intended |
| C5 | "18 rows · 10 companies · 1 sector" (fixture; board 31 rows). | intended (data) |

## D. Step 2, review names (L2)

| # | Difference | Status |
|---|---|---|
| D1 | Decision text "Citi is listed under Citibank and Citizens Bank" (prompt wording) vs the board's "... and would also match CITIZENS BANK". | intended (prompt item 4; `cross_company_variants` means the same search name under two companies) |
| D2 | Buttons "Keep for Citibank", "Keep for Citizens Bank", "Remove" (the board shows one Keep). At 1440 the three buttons wrap to two lines inside the row. A name that is itself a company's name offers only "Keep for <that company>"; if it is two companies' names, only "Fix in step 1". | intended (prompt item 4) |
| D3 | A repeated company is named as the server reports it ("Wells Fargo Bank NA appears twice") and its amber dot sits on the company name; the board puts the dot on a chip. | intended (the problem is the company row) |
| D4 | Company names weight 500 (the prompt says bold; the board draws regular-to-medium). | intended (board wins) |
| D5 | "and 4 more companies" is a button that shows the rest ("Show fewer companies" folds it again). | intended |
| D6 | With no open decisions the note reads "Every name is settled. Choose cycles next." and gold "Choose cycles ->" is enabled (`07_L2_settled_*`). The board has no settled state. | intended (acceptance state) |
| D7 | Back is 137px at 1440 (40% of the narrower card); 155px at 1920 as on the board. | intended |

## E. Step 3, choose cycles (L3)

| # | Difference | Status |
|---|---|---|
| E1 | Beside unverifiable and not-collected lines the build draws a hatched square and a dashed circle, not the board's check marks. | intended (prompt Don't-copy) |
| E2 | In the proof, 2025-26 reads "Saved: coverage unverifiable" (the fixture holds an unverifiable Banking 2026 row); the board shows "Not collected yet", which the build draws with a dashed circle when nothing is saved. | intended (data) |
| E3 | "21 enabled · 1 disabled" is this computer's real key status (board 16 / 4). With no enabled keys the key field opens by itself. | intended |
| E4 | At 1440 the status lines wrap to three lines in each cycle card (cards 234 wide; board 266 at 1600). | intended (width) |
| E5 | Gold "Start collection" 189px at 1440 (331 at 1920); board 240 at 1600. | intended (flex, card width) |

## F. Saved FEC coverage (L4)

| # | Difference | Status |
|---|---|---|
| F1 | No "Observed" chip and no "Observed · limited" legend entry; the latest observed transaction is in the detail panel. The legend adds "Stale · behind the policy date". | intended (prompt Don't-copy and item 6) |
| F2 | Detail "Status:" uses the policy wording ("Unverifiable coverage", "Stale coverage", "Current within policy") instead of the board's "Unverifiable". | intended (the console's coverage vocabulary; suites pin it) |
| F3 | Detail adds "Observed only; does not establish coverage." under the latest observed transaction, and "· 10 companies" after the roster name when known. | intended (keeps the old table's caveat) |
| F4 | A roster sector with nothing saved gets its own row marked "This roster"; a roster sector that matches a saved one (ignoring case) marks that row. | intended (step 1's sector is visible against what is saved) |
| F5 | The grid always shows all three cycles; the old table followed the ticked cycles. | intended (prompt item 6) |
| F6 | Chips are at most 216px wide and centred (1440: cells 200px; 1920: 216px); the board's fill ~200px of 232px cells. Fix round: at 1440 the date had been cut ("Verified · to Dec 31,…", scrollWidth 189 > clientWidth 167). Chip type is now 14px (board-close; was 15px), chip padding 0 8px and cell padding 0 8px, so every chip shows its whole date: 1440 unselected scrollWidth = clientWidth = 181 for both "Verified · to Dec 31, 2022" and "Stale · to Jun 30, 2024", selected (2px border) 179 = 179; 1920 214 = 214, selected 212 = 212 (`measurements.json` L4_*.covChips / selected_*; `shots\L4_verified_*.png`). | fixed (R07-1); chip width intended |
| F7 | At 1440 the legend takes two lines. | intended (width) |
| F8 | Each cell's button also carries hidden screen-reader text: "<Sector>, <cycle>: <status>." | intended (a11y; invisible) |
| F9 | Card title 36px serif (board ~38px by cap height). | intended (rounded) |

## G. Measurements (1440x900 unless noted)

- Stepper circles 38x38 at y 104; labels 16px, active weight 600.
- Cards: left 784 wide, right 392 (2:1, gap 16); both 174 to 832 (min-height 100vh - 242px); 1920: 1104 / 552, 174 to 1012.
- Gold: one visible per step (goldCount 1 in every state): #review-roster 342x43, #choose-cycles 189x43 (disabled while decisions are open), #start 189x43.
- No horizontal overflow in any state at 1440 or 1920 (`overflowX` false; the sr-only file input had widened the page by 50px before `#file{width:1px}`).
- Coverage card at 1440: grid 751 wide, detail 365 wide, starting 71px below the card top (board ~70).

## H. Behaviour checked (measurements.json)

- `/api/upload` bodies `{filename, content}` only; `/api/start` `{id, cycles:[2022,2024,2026], api_key}`; `/api/roster` keeps `{sector, companies:[{name, aliases}]}` (driven by test_workspace_polish_browser.cjs:103 against the real fixture server).
- Choose cycles disabled with two open decisions, enabled after "Keep for Citibank" re-sent the edited table (725 bytes vs 729: the Citizens Bank "Citi" cell cleared).
- Start collection opens Collection and Loading returns to step 1.
- A reload restores the typed draft exactly (sector and every company with its chips).
- Fix round (R07-3): Enter in `#sector` or in a company-name field runs the review again, as before the build (the form holds a hidden submit button, `sr-only`, `tabindex=-1`, `aria-hidden`); `measurements.json` enter_1440 / enter_1920: both reach step 2. Enter in an other-name field still adds a chip and Enter in "Add a company..." still adds the row (both handlers call preventDefault).
