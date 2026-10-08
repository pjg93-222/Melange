# Build 02 (Graph): differences from boards M4, G1-G5, approved boards 1 and 5

Built 2026-09-22 on `codex/mentat-crypto`, uncommitted. Phase 02a (default view) was half-applied at 11:14-11:24 by a builder Paul stopped; the finish run (16:12-19:30) applied 02a's graph.css, fixed the 390px overflow, and built 02b (compare modes). Fix round 1 (19:50-21:15) answered the review's defects R02-M1..M6, R02-m1..m13 and R02-1..6; what changed is in section K, and every row below is re-measured against the fixed build. Fix round 2 (22:10-) answered R02c-M1 (card heights, A14), R02c-m1 (C7, C8) and R02c-m2 (D14); section L. Paul's console on 8806 was not touched; every capture comes from a read-only instance on port 8813.

**Frame.** The 2026-09-22 boards are 2000x1131: a 1600x904.8 CSS frame at 1.25x. `approved_board5_downstream_drawer` is 2688x1520 (1.68x). Each side-by-side (`02_<state>_<width>.png`) shows the board scaled to 1 image px = 1 CSS px (1600 wide) beside the build captured at 1440x900 or 1920x1080, unscaled. The build is 160 CSS px narrower than the board frame at 1440 and 320 wider at 1920, so horizontal positions differ by design; everything below compares like with like. Fix round 1 also measured the boards' own 1600x900 frame (`measurements_fr1.json`).

**Captures.** `node capture.cjs 8813` then `python sbs02.py` regenerates every image and both measurement files. Two things are hidden in each capture and neither exists on Paul's console: the read-only preview line (only a `--read-only` instance prints it) and the stale-build banner (it appears whenever another builder edits an asset after the preview console started). They are hidden with CSSOM because the console's CSP refuses an injected `<style>`.

**Measurements.** `measurements_02a.json` (default view), `measurements_02b.json` (compare modes, Copy-link round trips, timings) and `measurements_fr1.json` (fix round 1: bars per half, chips, strip, card edges at 1440, 1600 and 1920; behaviour checks) come from `getBoundingClientRect`/`getComputedStyle` in the page; fix round 2 adds `measurements_fr2.json` (M4 card geometry before and after at 1440, 1600 and 1920 against the board's own numbers, and G1's By company names). All four are ignored by git through the root `*.json` rule. The summary is in section H.

Status key (README acceptance step 4): **fixed** = the build matches the board; **intended** = a deliberate difference whose reason is a Don't-copy item, real data, or a settled decision (D-0xx, the ten approved design calls, a README rule); **open** = Paul (or another lane) has to rule. A difference the build made on a session ruling (R1-R23 of the 02a/02b briefs) or on a measured fit is **open**, with that ruling named as the reason the build chose it (fix round 1, R02-4).

## A. Default view (board M4) - `02_M4_overview_*`

| # | Difference | Status |
|---|---|---|
| A1 | Fonts: Arial and Georgia stand in for Articulat and Freight Text, so every text run is a few px wider or narrower than the board. | intended: 00_README note (D-050, no web fonts) |
| A2 | Scope chips are 40px tall (build-01 primitive: 48px), their values 13px (primitive 14px), buttons 32px (primitive 40px). | fixed to board; primitive defaults 48/14/40px |
| A3 | The scope bar holds a More button (⋯) between Reset and "Split with PAC evidence"; M4 has none. It keeps Sources & freshness, Source folder and Advanced comparison reachable (`02_more_menu_*`). | intended: prompt item 1 |
| A4 | At 1440 the chips are narrower than M4's (Industry 105, Company 124, Employee level 113, Cycle 112, Giving 108px): the build's row is 160px narrower than the board's. Every caption and value is whole at 1440, 1600 and 1920; "Employee level" was cut to "Employee le…" at 1440 by 1px and now runs into the chevron's column (the chevron sits at mid height, below the caption line). | fixed (fix round 1, R02-m11) |
| A5 | Headline values are 16px/600 tabular; the prompt says 20px. | fixed to board (M4 measures 15-16px) |
| A6 | Tabs are 14px (prompt 15px); the active tab has a 3px `--acu-gold` underline (measured). | fixed to board |
| A7 | The share tracks under the part figures and the basis note are hidden; the Net giving tooltip carries "<exact amount> · <receipt groups> · local data · <basis note>". | intended: prompt item 1 |
| A8 | Card rows are 23px apart in every card (measured), M4's pitch. Rows keep cents ($2,838,522.75); M4 shows cents too. | fixed |
| A9 | Company comparison and By company rows carry no dot; M4 draws a blue dot before every company. | intended: Don't-copy (companies have no party); 0 dots measured in every state |
| A10 | Company comparison's footer reads "…sparkline 2025-Q1–2026-Q3 · observed quarters; gaps are missing, not zero" (two lines at 1440, 1600 and 1920: 12px of row 2's height, A14) where M4 reads "sparkline 2022 · 2024 · 2026". | intended: real data (the sparklines are quarterly since 09-19) |
| A11 | Employee level's legend wraps "Chief $689,968 · 5.8%" onto a second line at 1440 (the card is 607px against M4's 686px); one line at 1920. | open: measured fit at 1440 (the legend keeps M4's amounts; dropping them at 1440 would keep one line) |
| A12 | By company: 10 rows, the Employee level card's Top N (10), in Company comparison's order (measured); three shares per row, as on M4. | fixed |
| A13 | At 1920 the page content starts at x=306 (the workspace keeps its 1560px cap and centres); M4 is a 1600 frame with content at x=226. | intended: settled layout (`body[data-view=graph] .workspace`, 2026-09-19), no 1920 board |
| A14 | Card heights (fix round 2 re-measure, `measurements_fr2.json`; identical at 1440, 1600 and 1920 unless named). First card row 198-538 (340px; M4 200.8-536.8, 336px); second row 550-882 at 1600 and 1920 (332px; M4 549.6-861.6, 312px) and 550-886 at 1440 (the Employee level legend wraps, A11). Each card's foot zone is now M4's: the chart ends 6px under its last row (was 29), the candidate note sits 2px under the chart, the footer is one 24px row (count, i, Export at the right; it was 50px because the page's `.graph-panels details{margin-top:16px}` caught the Export menu), and the overview's cards no longer carry the 6-12px of blank grid gap an empty subgrid track left. Recipient type: last row bottom 473 -> Export 503-527 -> card bottom 538 (M4: 471 -> 502.4-526.4 -> 536.8). The 20px row 2 keeps over M4: Company comparison's footer is two lines (the sparkline range and the missing-quarters rule, A10: 12px) and M4 draws that card's rows at a 22.3px pitch starting 4px higher (8px). Page: no vertical scroll at 1920x1080 (scrollHeight 1080; was 1153); at 1600x900 the cards end at 882 inside the frame and Details & methodology and the footer sit below it (M4's frame shows neither). #graph-export, #graph-copy-image and #graph-briefing did not move. | fixed (fix round 2, R02c-M1); the 20px left in row 2 is open: real data (A10) and measured fit (the 23px pitch is M4's first-row pitch, used in every card) |
| A15 | Amounts, names and the candidate list are real Banking 2025-2026 data. | intended: boards' amounts are illustrative |
| A16 | While the runs and the first scope are read, the status line under row 2 says "Reading saved report sources…" then "Reading saved giving data…"; the template's "Choose a report source." shows only on a console with no run. | fixed (fix round 1, R02-m5) |

## B. More menu - `02_more_menu_*`

| # | Difference | Status |
|---|---|---|
| B1 | M4 has no More button; the menu (Sources & freshness, Source folder select, Advanced comparison) opens under ⋯ at 220px wide. "Advanced comparison" (#compare-open, was "Compare subjects") still opens the old #compare-panel. | intended: prompt item 1 (R9 names the label) |

## C. The drawer (approved board 5) - `02_drawer_default_*`, `02_drawer_compare_*`

| # | Difference | Status |
|---|---|---|
| C1 | Board 5's sidebar (Graph sub-navigation with icons) and its "Back to all recipients" placement predate build 01's shell. | intended: approved call 9 (one sidebar everywhere), owned by build 01 |
| C2 | With the drawer open, Recipients is two columns, Top organizations and the drawer (570 : 610px at 1440, board 5's ~1 : 1.07); the recipient-type card steps aside until the drawer closes. It was three columns, the recipient-type card squeezed to 297px with its 13px labels scaled to 9px. Top organizations' labels now render at their drawn size (15px line box for 13px text, measured). | fixed (fix round 1, R02-M5) |
| C3 | The drawer's title reads "Where this PAC’s money went next · 2025–2026", board 5's wording (graph.js applyDrawer and the template's h2; test_downstream_measurement_browser.cjs re-homed). It read "Saved downstream PAC activity", which predates build 02. | fixed (fix round 1, R02-M6). Reversible in two strings if Paul prefers the older "Saved …" wording |
| C4 | While comparing, the drawer header carries the opening scope's pill ("Credit Union", measured) above the title, and the drawer reads that scope's own request. | fixed (prompt item 11) |
| C5 | While comparing, Recipients is the drill-down table (1.4fr) with the drawer beside it (1fr); long PAC names give way at 200px with an ellipsis ("THE GOLDMAN SACHS GROUP, INC. POLIT…", button 200px, text 430px), so the amounts and Difference stay visible. | open: R20/R21 of brief_02b (board 5 shows no table) |
| C6 | The compare drawer shown is Credit Union's top recipient; its drawer says "Downstream activity is unavailable: no saved activity…" when that scope has none. | intended: real data |
| C7 | Clicking a Top organizations row narrows the whole page to that recipient: the url gains `recipient=C00401224&drawer=C00401224&drawerDirection=Oppose`, a recipient chip ("ACTBLUE ×") takes a second scope-bar row (scope card bottom 240.5 against 186 in M4), the headline becomes the recipient's own totals ($2,241,495 / $0 / $2,241,495) and Top organizations lists that one recipient ("All 1 values"). Board 5 keeps the full ranked list with the clicked row highlighted. The narrowing predates build 02 (graph.js at HEAD:266 `organizations:id=>{recipient=id;refresh();}`, now line 925 with the drawer added) and test_graph_lazy_tables_browser.cjs:111-112 asserts the page's read names the recipient (`02_drawer_default_*`). | **open (Paul)**: keep the narrowing, or keep the list, highlight the clicked row and leave the scope alone as board 5 draws it (changes the url state and that suite) |
| C8 | The drawer opens on the direction with the largest amount (ActBlue: Oppose, rows PAXTON, LETLOW …); board 5 opens on Contributions. The pick predates build 02 (the `best.direction` choice, proof\02\before graph.js:804-813, now graph.js:1575-1584). | **open (Paul)**: largest amount (current) or Contributions first as board 5 shows |

## D. Industry compare (G1) - `02_G1_industry_*`

| # | Difference | Status |
|---|---|---|
| D1 | "Split with PAC evidence" and "Open in Chart Studio" stay at the right end of the scope card; G1 puts them in the page header. | intended: Don't-copy (M4 keeps them in the scope card) |
| D2 | The Industry chip holds the two pills (18px, 61 and 84px wide, text whole at 1440, 1600 and 1920), a "+" and M4's chevron; clicking the chip opens "Another industry". Every other chip keeps its caption whole at 1440 (Company 94, Employee level 103, Cycle 110, Giving 60px; values "All co…", "All", "2025–2026", "All"). | fixed (fix round 1, R02-M3: the chips were 64px, "In… B…") |
| D3 | The Company chip is disabled while industries are compared ("All companies", title "Clear the comparison to choose a company"); G1 and G4 draw a normal "All companies" chip. A company belongs to one industry, so scope 2 cannot share scope 1's company. | **open (Paul)**: 02b state model (brief_02b R4); the alternative is a company within scope 1's industry and "—" for the other industries (R02-m12) |
| D4 | A Layout: Grid \| Stacked switch sits at the tab row's right end; G1 has none. | open: prompt item 9 says Stacked is optional with two scopes; R19 shows the switch whenever comparing |
| D5 | Headline figures: one line per scope after an 8px dot, value 15px at 1440 and 16px at 1600 and up, 18px lines, all on the tab row; G1's values are about 17px on ~19px lines. With two scopes the scope card is exactly as tall as M4's (bottom 186px on Paul's console, at 1440, 1600 and 1920, in M4, G1, G2 and G3). | fixed (fix round 1, R02-M2); the 1px line and the 15px value at 1440 are open: measured fit (R7c) |
| D6 | Top N selects read "Top 6"; G1's read "Top 10" over six rows. | open: prompt item 8 makes 6 the compare default; R14 prints what is shown |
| D7 | Recipient-type halves: label, bar, amount; at 1440 (254px halves) the share column goes (it stays in each row's title and in the footer), at 1600 and 1920 it is printed as on G1. Longest bar per half: 70 / 87px at 1440 (was 24 / 24), 71 / 79px at 1600 (was 42; G1 draws ~92px), 101 / 118px at 1920 (was 66). No category name is cut at any size. | fixed (fix round 1, R02-M1); the share column at 1440 is open: measured fit |
| D8 | Top candidates halves keep a bar (G1's have none; G3 draws them): longest bar 68 / 67px at 1440, 78 / 78px at 1600, 88 / 88px at 1920; names get what the bar leaves, ~105px at 1440 ("WARNER, MA… · D" style cuts at 1440, whole names at 1920 except the longest). | open: approved call 2 ("same rows and colours") against G1's bar-less candidate halves; G3 draws bars |
| D9 | Company comparison halves: name, amount, share (1600 and up), and the quarterly sparkline at the row end, as G1 draws them; no bar while a half is under 380px (every two-scope size, and thirds at 1440). Sparklines are drawn wherever the scope's industry has a verified quarterly dataset (Banking yes; Credit Union has none, so its slots stay empty). | fixed (fix round 1, R02-m7: halves drew a 24-32px bar and no sparkline) |
| D10 | Category halves list the same categories in scope 1's order; a category a scope lacks shows "—" (Credit Union: Other PAC). Row tops align across halves within 0.1px (measured). | fixed (prompt item 8) |
| D11 | Employee level halves: stacked bar, legend with shares, and "By company" with each half's own first four companies, three shares each; G1 shows two shares per company. | intended: prompt item 3 and M4 show all three levels |
| D14 | By company names in the halves: at 1440 the name column is 87px, so a name that does not fit prints `nameForms()`' longest short form that does ("Goldman Sachs", "Wells Fargo", "Morgan Stanley", "JP Morgan", "SchoolsFirst", "Navy Federal", "America First", "Mountain"); it read "Goldman Sach…", "Wells Fargo Ba…". 1600 (108px) keeps longer forms ("Wells Fargo Bank NA", "JP Morgan Chase"), 1920 (130px) most whole names. The row's title and spoken label keep the whole name; 0 names cut at any size (measured). | fixed (fix round 2, R02c-m2); "Mountain" for Mountain America Credit Union at 1440 is open: measured fit |
| D12 | Footers give each scope's own coverage: "Showing 6 per scope · Banking 96.8% · Credit Union 44.6% of net giving"; G1 reads "Showing 6 of 6 · 100.0%" (its halves are illustrative). Employee level keeps "Showing 3 of 3 · 100.0% of the shown levels", true of every scope. | fixed (fix round 1, R02-m13: the footer described scope 1 only) |
| D13 | Credit Union's figures and rows are real data (G1's are illustrative). | intended: real data |

## E. Cycle compare (G2) - `02_G2_cycle_*`

| # | Difference | Status |
|---|---|---|
| E1 | G2 regroups the scope bar ("Scope" group, a separate "Cycle" group) and adds "Full cycles \| Same point". The build keeps M4's five chips in place with the Cycle chip holding the pills, and renders no Same point switch. | intended: approved call 1 (the scope bar never moves) and call 5 (Same point needs data work; Phase B) |
| E2 | Pills read "2023–2024" and "2025–2026 · to date" at 1600 and 1920; at 1440, where the row is full, "2023–24" and "2025–26 · to date" (whole labels in their titles). | fixed (R5 wording); the short form at 1440 is open: measured fit (R02-M3) |
| E3 | G2's overline is small caps ("BANKING · COMPARING CYCLES"); the build prints "Banking · comparing cycles" in build 01's overline style. | intended: build 01 owns the overline style (README "Notes from build 01") |
| E4 | The headline figures stay on the tab row at every size. At 1440 each line drops its printed share ("· 18.0%", kept in the value's title) so value and plum change chip fit beside the tabs; at 1600 and 1920 the share is printed as on G2. | fixed (fix round 1, R02-M2: at 1440 the figures took a second row and the cards moved down 58px) |
| E5 | The headline change chip ("↓−54.0%") is plum, rgb(87,68,123) = `--acu-purple`, like the row chips (measured; asserted in test_navigation_scope_browser.cjs step 17). | fixed (fix round 1, R02-M4: it was `--muted` grey) |
| E6 | Recipient-type rows keep their bars; G2's are bar-less. Longest bar: 81px in 2023–2024 and 30px in 2025–2026 at 1440 (that half gives its share column to the change chips), 73 / 58px at 1600, 112 / 97px at 1920. | intended: Don't-copy (bars); the 30px bar at 1440 is open: measured fit |
| E7 | Top candidates halves in cycle mode are bar-less under 380px, as G2 draws them: name, amount, change chip or "new". A bar there was a 38px swatch beside a four-letter name. | fixed (fix round 1, R02-M1 follow-on) |
| E8 | Change chips (plum, "↑ +17.7%") sit in the share column of the latest cycle's half only; every aligned category row carries one (Super PAC had a share instead when it fell outside 2025-2026's own top six; fixed in fix round 1). | fixed (design calls 2 and 10) |
| E9 | Names present in both cycles get the shared tint; names only in 2025-2026 get "new". At 1440 (half ~270px) the "new" tag sits in the chip column, at 1920 after the name as on G2. | open: measured fit (R16) |
| E10 | G2's "new" tags on WARNER and GOLDMAN: in the build they appear in both cycles and get the tint. | intended: Don't-copy |
| E11 | Employee level "By company" aligns both halves on 2023-2024's first four companies. | fixed (prompt item 8) |
| E12 | Picking "Another cycle" from 2025–2026 makes 2025–2026 pill 1 and the earlier cycle pill 2 (prompt item 5: the current value is pill 1); G2 draws 2023–2024 first. A permalink keeps the order it names, so `cycle=2024&cycle=2026` reproduces G2 exactly. The change chip always sits on the latest cycle. | **open (Paul)**: R02-m4. Ordering chronologically would make the older cycle scope 1, which the URL, the other views (mentat:graph) and a reload of both scopes would follow |

## F. Company compare (G3) - `02_G3_company_*`

| # | Difference | Status |
|---|---|---|
| F1 | At 1440 the pills read "Goldman" and "JP Morgan" (whole names in their titles) and every other chip keeps its caption whole (Industry 94, Employee level 106, Cycle 113, Giving 63px). At 1600 and 1920 the pills read "Goldman Sachs Bank NA" and "JP Morgan Chase Bank NA" (150 and 159px) as on G3. | fixed (fix round 1, R02-M3 / R02-1: the chips were 64px, "In… B…", and the pills "Goldman Sach…"); the short pill names at 1440 are open: measured fit |
| F2 | G3 omits the Giving chip; the build keeps all five. | intended: prompt item 1 |
| F3 | Headline lines carry the company shortened by whole words, "Goldman" and "JP Morgan", as G3 prints them (no ellipsis; the column is as wide as the longer name). | fixed (fix round 1, R02-m9: "Goldman…") |
| F4 | Company comparison does not split: every bar is taupe except the two compared companies in their scope colours, their rows tinted, footer "Compared companies highlighted". | fixed (design call 3) |
| F5 | Top candidates halves use the category palette; G3 shades them plum and teal. | intended: Don't-copy |
| F6 | Employee level halves show the bar and legend inline and no By company; G3 lists the legend one level per line. | open: R1b (one legend component in every mode) |
| F7 | "Another company" from All companies starts from the top company: its list leaves that company out and its heading reads "Compare Goldman Sachs Bank NA (top company) with…". | fixed (fix round 1, R02-m3: the start was silent) |

## G. Three scopes (G4) and the table (G5) - `02_G4_three_*`, `02_G5_candidates_table_*`

| # | Difference | Status |
|---|---|---|
| G1 | G4's Industry chip shows a boxed "+" beside three pills; the build shows none at three (the maximum). | open: R13 (three is the maximum, so there is nothing to add) |
| G2 | At 1440, three industry pills do not fit beside four chips and the actions, so the pill chip takes a row of its own in the scope card (pills whole; the scope card is 48px taller than at 1600: bottom 251 against 203px). At 1600 and 1920 it is one row, as on G4. | open: measured fit (R02-M3's own fallback); the alternative is three pills cut to ~2 letters |
| G3 | G4's headline is one horizontal row of two figures; the build stacks three lines under each of three figures. | open: prompt item 7 and R7c (one line per scope) |
| G4 | Layout is Stacked with Grid disabled (title "Three scopes need the stacked layout"); cards are full width, one per row, in G4's order, each in thirds; row tops align across thirds within 0.1px. | fixed (design call 4, prompt item 9) |
| G5 | Candidate thirds draw bars (G4: none; 88-93px at 1440); company thirds end in sparklines, and draw bars too from 1600 (thirds ≥ 380px); G4's "ConpMAN" typo. | open: approved call 2 against G4's bar-less candidates; Don't-copy for the typo |
| G6 | G5's headline reads "$12,003,181 / $8,114,902" on one line for two figures; the build keeps the stacked lines of the Overview for all three figures. | intended: approved call 1 (the headline never moves between tabs) |
| G7 | G5's pills show their "×" at all times; the build shows it on hover and on keyboard focus. G1, G2, G3 and G4 draw the same pills with no "×" at all, so a permanent "×" would match one board and break four. | **open (Paul)**: R13; R02-m2 asks for the permanent "×" |
| G8 | G5 opens with "Funded by both" selected; the build opens on "All". | open: R20 (the default filter is All; the board shows a chosen filter) |
| G9 | G5's Export is a menu ("Export ▾"); the build's is one button that saves the filtered, sorted rows as CSV. | open: R20 |
| G10 | The sorted column shows ▼/▲ where G5 draws a double arrow. | open: R20 (aria-sort plus a one-direction arrow) |
| G11 | Table geometry matches G5 at 1.25x: header 38px, rows ~41px, filter chips 30px, search and select 34px, pager buttons 34px. The Layout switch is hidden while a table shows. | fixed |
| G12 | Counts (All 598, Funded by both 33, Only Banking 549, Only Credit Union 16) are real data; G5's (742/214/368/160) are illustrative. | intended: real data |

## H. Measured checks (measurements_02a.json, measurements_02b.json, measurements_fr1.json)

| Check | Result |
|---|---|
| No vertical scroll at 1920 on the default Overview | met (fix round 2): scrollHeight 1080 at 1920x1080 (was 1153); cards end at 882, Details & methodology 900-960, footer to 1080. The shell's own footer had every view scrolling 1px (main reserved 100vh - 45px for a 46px footer; workspace-polish.css now reserves 46px) |
| Card rows vs M4 (fix round 2) | row 1 198-538 (M4 200.8-536.8); row 2 550-882 at 1600/1920, 550-886 at 1440 (M4 549.6-861.6); gap 12 (M4 12.8); chart 6px under its last row; footer one 24px row; Export 503-527 in row 1 (M4 502.4-526.4) (A14) |
| First card row fully visible at 1440 | bottom 538 ≤ 900; second row bottom 886 ≤ 900 |
| Scope bar one row, no overlaps | every state and size except three scopes at 1440 (G2 in section G: the pill chip on its own row); 0 overlaps |
| Captions whole while comparing (1440, 1600, 1920) | every chip, every state; values cut only as "All co…" (Company) at 1440 |
| Scope card bottom | 186px in M4, G1, G2 and G3 at 1440, 1600 and 1920 (identical; read-only preview line hidden, as on Paul's console); three scopes 203px at 1600 and 1920 (one more figure line), 251px at 1440 (and the pill row) |
| Tab row while comparing | y identical to M4 in every mode and size (tabs keep M4's place; only the strip's bottom edge grows, and with two scopes it does not) |
| Longest bar per half, recipient types (G1) | 70 / 87px at 1440, 71 / 79px at 1600, 101 / 118px at 1920 (was 24 / 24, 42, 66) |
| Longest bar per half, candidates (G1) | 68 / 67px at 1440, 78 / 78px at 1600, 88 / 88px at 1920 (was 24) |
| Headline change chip colour (G2) | rgb(87,68,123) = `--acu-purple` |
| Drawer, Recipients (board 5) | two columns 570 / 610px at 1440; the recipient-type card hidden; Top organizations' 13px labels unscaled |
| One gold element per screen | exactly one (#graph-open-builder) in every capture |
| No party dot on a company row | 0 in every state (whole card, halves, highlighted list, By company, Companies table) |
| Row tops across halves (and thirds) | 0.0px in every split card, every size |
| Headline type | label 12px `--muted`; value 16px/600 tabular (M4); compare lines 15px (1440) / 16px (1600+) on 18px lines |
| Tab underline | 3px, rgb(236,169,28) = `--acu-gold` |
| Row pitch | 23px in every M4 card; 27px in compare halves |
| By company | 10 rows = level Top N 10, same order as Company comparison |
| #split-view | on Graph: inside #graph-actions, just before #graph-open-builder; on Chart Studio: back in .workspace-heading |
| Copy link reopens each compare state | G1, G2, G3, G4 at both sizes: pills, compare, layout, overline, the five selects and the tab identical on a fresh page |
| A failed scope | its halves say "This scope could not be read." (was the browser's "Failed to fetch"); the other scope still renders |
| Card Export while comparing | Data (CSV) writes one column per scope ("Comparing: Industry: Banking \| Credit Union", each scope's report SHA-256); the image, copy, briefing and full-table items are disabled with a title saying why |
| 390px, 820px while comparing | no horizontal overflow (console and polish suites) |
| Reduced motion | halves enter with no animation |

## I. Retired in workspace-polish.css (this build is the file's current holder)

The 2026-09-19 Graph rollback rules that graph.css's build-02 block supersedes were removed, with a comment where they stood. A computed-style census of every element in #view-graph at 1440 (Overview, industry compare, Candidates table), 820 and 390 found no difference before and after, except the inert `grid-template-columns` of the (flex) chip row.

- In the 760px block: `#view-graph .graph-filter-grid{grid-template-columns}`, `.graph-filter-grid label:last-child{grid-column}`, `.graph-panel-tools{margin-left:0}` (already overridden by the later rule), `.analysis-tabs{gap}`, `.analysis-tabs button{padding}`.
- The rollback block: `.graph-controls{padding}`, `.graph-header`, `.graph-filter-grid`, `.graph-actions{margin-left}`, `.analysis-strip{margin}`, `.analysis-tabs`, `.analysis-tabs button`, `.graph-metrics`, `.graph-metrics strong{font-size:26px}`, `.graph-metrics>div:first-child strong{font-size:28px}` (it outranked the compare headline lines), `.graph-panels[data-analysis=overview]`, `.graph-panels>.panel{padding}`, `.graph-panels h2`, `.graph-panel>.panel-heading`, `.graph-panel-tools .graph-text-button{min-height}`, `.graph-filter-grid label`, `.graph-filter-grid :is(select,input)`.
- `@media(max-width:760px){#view-graph .graph-panels[data-analysis=overview]{grid-template-columns}}`.
- Kept: the #view-graph palette line, `.graph-panel-tools{margin-left:auto;flex-wrap:wrap}`, `.graph-panel-foot{margin-top:auto}`.

## J. Data notes

- Headline figures come from each scope's own `/api/graph` `totals` (the Overview's basis); `/api/comparison` is not used (R2).
- Same point for cycles (Phase B, not built): Insights already computes a same-election-stage net in the trends analysis (`mentat/app/analysis_*.py`, the `as_of` request field); a same-point Graph total could come from there on Paul's go.

## K. Fix round 1 (2026-09-22, 19:50-21:15): defect -> action

| Defect | Action |
|---|---|
| R02-M1 bars at the 24px floor | fixed: `compactColumns()` reserves a quarter of the half for the bar and measures the widest name, so the label takes only what it needs (never below 3/10 of the half); halves under 285px drop the share column (G2's earlier cycle has none). Bars: D7, D8, E6, H. Pinned in graph-layout.test.js (3 new tests) |
| R02-M2 figures wrapped at 1440 | fixed: `fitStrip()` shortens before it moves (share dropped, then Layout caption and tab gaps); two-scope lines are 18px so the strip keeps M4's 55px; scope card bottom identical in M4/G1/G2/G3 (H) |
| R02-M3 / R02-1 64px chips | fixed: chips keep a measured floor (whole caption, short value); the pill group gives way instead (tighter gaps, short forms "Goldman", "2025–26", then an ellipsis); three scopes at 1440 put the pill chip on its own row (G2, open). A4/F1 re-marked |
| R02-M4 grey headline chip | fixed: plum rule in graph.css; asserted in test_navigation_scope_browser.cjs step 17 |
| R02-M5 three-column drawer | fixed: Recipients with the drawer open is board 5's two columns (C2) |
| R02-M6 drawer title | fixed to board 5's wording (C3); reversible |
| R02-m1 "Failed to fetch" | fixed: network and parse failures read "This scope could not be read."; server messages are kept |
| R02-m2 pill "×" on hover | not changed: G1-G4 draw no "×", G5 draws it always; hover and focus reveal is the one state consistent with all five. Open for Paul (G7) |
| R02-m3 silent top company | fixed: the list heading names the starting company (or newest cycle) and the list leaves it out (F7). `MentatCompareMenu.open` gained an optional `captions` option (additive) |
| R02-m4 cycle pill order | not changed: prompt item 5 against G2, and ordering by date would move scope 1 (E12, open for Paul) |
| R02-m5 status while loading | fixed (A16) |
| R02-m6 hard-clipped PAC names | fixed: the ellipsis is on the name's own button (C5) |
| R02-m7 no sparklines in company halves | fixed (D9) |
| R02-m8 / R02-6 73px at 1920 | not changed: open for Paul with the fix described (A14) |
| R02-m9 "Goldman…" | fixed (F3) |
| R02-m10 tab row moving | fixed: tabs keep M4's y in every mode (H) |
| R02-m11 "Employee le…" | fixed (A4) |
| R02-m12 Company chip locked | documented as open for Paul (D3) |
| R02-m13 scope-1 footers | fixed (D12) |
| R02-2 drawer title | as R02-M6 |
| R02-3 line endings | fixed: the 13 unchanged graph.js lines got their original endings back (0 flips against proof\02\before and the 02b pre-copy, measured); hk.py now aligns a hunk's lines by text so a kept line keeps its own ending |
| R02-4 status vocabulary | fixed: every row resting on a session ruling or a measured fit is now open, with the ruling named |
| R02-5 card export while comparing | fixed: Data (CSV) carries every scope; image items disabled with a title (H) |

## L. Fix round 2 (2026-09-22, 22:10-): defect -> action

| Defect | Action |
|---|---|
| R02c-M1 card heights (M4) | fixed: the chart ends 6px under its last row (graph.js `draw()`: the single-line tail was 29px); the Export menu loses the page's 16px `details` margin, so the footer is one 24px row with Export at the right; the candidate note sits 2px under the chart; the overview's cards drop the parent's 12px row gap between their subgrid tracks (the cards keep 12px between card rows). Row 1 198-538 (M4 200.8-536.8), row 2 550-882 (M4 549.6-861.6); no vertical scroll at 1920x1080. A14 replaced with the card-height row; H re-measured. The 1px every view scrolled at 1920x1080 was the shell's (main reserved 100vh - 45px for a 46px footer): workspace-polish.css reserves 46px. #graph-export, #graph-copy-image, #graph-briefing unmoved |
| R02c-m1 drawer default | documented, not changed: C7 (a clicked organization narrows the page to that recipient; board 5 keeps the full list with the row highlighted) and C8 (the drawer opens on the largest direction; board 5 on Contributions), both open for Paul. Both predate build 02, and C7's url state is asserted by test_graph_lazy_tables_browser.cjs |
| R02c-m2 By company names cut at 1440 | fixed: a name too long for its column takes `nameForms()`' longest short form that fits ("Goldman Sachs", "Wells Fargo"); the row's title and label keep the whole name; 0 cut names at 1440, 1600, 1920 (D14) |
