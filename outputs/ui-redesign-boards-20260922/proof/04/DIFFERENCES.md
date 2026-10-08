# Build 04 (Insights, board I1): differences from the board

Build 04, 2026-09-22. Nothing was committed. Paul's console on port 8806 was not touched; every capture comes from this build's own read-only console (`server.py --port 8814 --read-only`).

**History of this build.** A first builder (session 8a67e999) rewrote the Insights template, script, stylesheet and both Insights browser suites between 11:40 and 12:20, passed both suites at 12:08, and stopped at 12:43 on a usage limit while polishing. This build compared those bytes with the pre-edit copies and **resumed** them rather than restoring (the evidence is in `HANDOFF.md`). It was itself interrupted at 16:44 and resumed at 17:29. Every edit after 12:20 is listed in `HANDOFF.md` with its hash.

**Fix round 1 (19:13-20:00).** Two reviewers' defects were fixed or re-recorded; `HANDOFF.md` §8 maps each defect id to its action. Rows changed in this round carry "(fix round 1)". The default capture at 1600x900 is unchanged except the rail switches (D9): every other rect in `measurements.json` (`g_default_1600`) equals the earlier capture.

**Frame used.** `boards\I1_insights.webp` is 2000x1131, a 1600x900 CSS frame at 1.25x on both axes, so the board is 904.8 CSS px tall. Board numbers below are CSS px in that frame. Build numbers come from `getBoundingClientRect` at a 1600x900 viewport (`measurements.json`, capture `g_default_1600`, taken in fix round 1; it equals the earlier `f_default_1600` except the rail switches), unless a row says otherwise. Ink measurements (cap tops, ink widths) use one routine on both images.

**Captures.**
- The read-only instance shows its runtime notice ("This preview runs an older build", `#stale-banner`) because other builders are editing assets. The capture script hides it before each screenshot, as build 01 did. It is not part of any board.
- Each changed asset is fetched with `cache: 'reload'` before the page loads.
- Browser storage for the analysis switches is cleared, so every capture opens on the core three.

**Status key.** **fixed**: the build matches the board. **intended**: the difference is deliberate, with the reason. **open**: Paul needs to rule, or another owner needs to act.

**The 8px shell offset (applies to every x value below).** On I1 the sidebar is 208px wide. The console's sidebar is 200px wide: build 01 measured it from M4, and design call 9 is "One sidebar everywhere". So the whole Insights content column starts 8px further left than on I1: cards start at 226 (board 235.2) and end at 1578 (board 1577.6). Status: **intended (build-01 ruling, design call 9)**. Horizontal positions are compared after allowing for that offset.

---

## A. Shell and page header

| # | Element | Board I1 | Build | Status |
|---|---|---|---|---|
| A1 | Sidebar width | 208 | 200 | intended (build 01, design call 9; see the note above) |
| A2 | Wordmark "MENTAT" | wide tracking, about 23 CSS px caps | build 01's M4 wordmark | intended (build 01 owns the shell) |
| A3 | Sidebar footer | "build 2b1a62d · port 8800 · up since 04:28 PM" | "Local only · Local connection / build 862a6c4 · port 8814 · up since 04:20 PM" | intended (Don't copy item in prompt 04; real runtime values) |
| A4 | Page footer | none within the 905px frame | build 01's footer (MENTAT … FEC collection · canonical names + aliases) sits below the fold, so the page scrolls at every required viewport: 39px at 1440x900 and 1600x900 (scrollHeight 939) and 1px at 1920x1080 (scrollHeight 1081) | open (shell footer, build 01's file, single-writer holder: build 02; the Insights content itself ends at 853, the board's 852.8) |
| A5 | Page canvas | (247,245,244) sampled at 1590,580 | #f7f3ee | intended (build-01 ruling B7) |
| A6 | Title "Insights" | heavier serif (Freight Text) | 31px Georgia fallback, build 01's heading | intended (fonts are not installed; the 00_README says the fallback is expected) |
| A7 | Subtitle "Compare periods and explain observed changes." | cap C top 56.8, cap 10.4 tall, 321 px of ink | cap top 56, 10 tall, 290 px of ink | fixed (size and position); the 31px width difference is Articulat against the Arial fallback: intended (fonts) |
| A8 | Sources | 1300-1380 x 25.6-60 | 1299.2-1378.9 x 26-60 | fixed |
| A9 | Export with chevron | 1391-1476 x 25.6-60 | 1389.9-1477.5 x 26-60; one menu holding CSV (`#insights-export-csv`) and JSON (`#insights-export-json`) | fixed |
| A10 | Refresh | 1488-1577.6 x 25.6-60 | 1488.5-1578 x 26-60 | fixed |
| A11 | Refresh fill | (69,57,120) | plum #342649 (`.primary`) | intended (build-01 ruling: `.primary` keeps the plum look everywhere; gold is opt-in and not used on this screen) |

## B. Filter card

| # | Element | Board I1 | Build | Status |
|---|---|---|---|---|
| B1 | Card | 235.2-1577.6 x 92.8-172 | 226-1578 x 92-173 | fixed |
| B2 | Labels Industry / Company / Basis / Funding above each select | cap I top 105.6, 8.8 tall | cap top 104, 9 tall (12px) | fixed |
| B3 | Select height and text | 123-155.5; "Banking" cap 9.6 at 134.4 | 123-155; cap 9 at 134 | fixed |
| B4 | Select widths | Industry 252.5-465, Company 484-715, Basis 733.5-970, Funding 988.5-1221 | 245-448.5, 467.5-688.5, 707.5-933.2, 952.2-1174 | intended **if B8 stays** (open with B8): each select is 11-15px narrower, because the More options button (B8) takes 45px of the row |
| B5 | Period chips "2023-2024" → "2025-2026" | 1249.5-1358 and 1404-1512, y 116.5-150 | 1203-1311 and 1358-1466, y 116.5-149.5 (108 x 33) | fixed in size; they sit 46px further left because of B8 (intended if B8 stays; open with B8) |
| B6 | Arrow between the chips | thin → centred in 46px | → centred in 47px | fixed |
| B7 | Swap ⇄ (accessible name "Swap periods") | 1523-1561 | 1477-1514 x 116-150 | fixed in size; shifted with B5 (intended if B8 stays; open with B8) |
| B8 | More options ⋯ (`#insights-more-options`) | not on the board | 1522-1559, opens "Contributions through" (`#insights-as-of`) and "Compare industry" (`#insights-comparison-dataset`) | **open**: the two request fields `as_of` and `comparison_dataset` exist today and have no place on I1. The first builder kept them behind one icon button instead of dropping them. Paul rules: keep (as built; B4, B5 and B7 then stand as intended) or remove the button and both controls (the cutoff would always be today and relative preference would stay unavailable). Removing them also means dropping or re-homing, with Paul's consent, the steps in `test_insights_controls_browser.cjs` that exercise them (lines 69-76 after fix round 1: `#insights-more-options`, `#insights-comparison-dataset`, `#insights-as-of`). |
| B9 | Compare button `#insights-compare-open` | not on the board | removed; its test assertions were re-homed to the chips and `#insights-more-options` | fixed (prompt item 2) |

## C. Summary strip

| # | Element | Board I1 | Build | Status |
|---|---|---|---|---|
| C1 | Card | 235.2-1577.6 x 193.6-269.6 | 226-1578 x 192-270 | fixed |
| C2 | Cell rules | x ≈ 533, 833, 1136 | 526.5, 828.1, 1132.7 (four cells 280:300:303:424, as measured on I1) | fixed (within the 8px offset) |
| C3 | Labels | "Net giving 2023-2024", "Net giving 2025-2026" | "Net giving 2023-2024 · Employee giving", "Net giving 2025-2026 · Employee giving" | **open (Paul rules on the suffix)**. Why it is there: the engine keeps money channels separate and says "totals from different stages must not be added together", so there is no all-channel aggregate to show. The strip reports the largest giving channel and names it; a review channel is never the default (HANDOFF §2). If Paul prefers I1's plain label, the channel name moves to the cards' channel lines only. Narrow screens (fix round 1): the label no longer clips; where it does not fit (1366px and below), "· Employee giving" wraps as one unit onto a second line and the four values stay level (dd tops 239.5, 239.5, 239.5, 239.5 at 1366x768). At 1440, 1600 and 1920 the strip is unchanged (192-270, values at 224.5). |
| C4 | Values | $10,684,902 · $12,003,181 · +$1,318,279 +12.3% | $21,106,728 · $11,883,136 · −$9,223,592 −43.7% | intended (the board's amounts are illustrative). These are same-election-stage amounts: each cycle through the same date (2024-09-22 and 2026-09-22), from `changes.cards[].baseline_cents / current_cents`, which equal `trends.rows[].matched_amount_cents`. |
| C5 | Change colour | teal when up | `--chart-negative` (red) here because it is down; teal when up (see the swap capture) | fixed (prompt item 3) |
| C6 | Value type | semibold serif; digits cap 19.2 tall at 230.4 | 23px Georgia at weight 500 (renders 400); digits 20 tall at 230 | fixed in size; weight is a font difference, intended (fonts: Georgia has 400 and 700 only; 700 is far heavier than the board) |
| C7 | Recipients | "214 continuing · 61 new · 38 no longer observed" | "—", with the tooltip "This analysis does not report recipient counts by period." | **open (data)**: no field in the query response counts recipients by period. The nearest, `relationships.cards[]` (`continued_relationships`, `newly_observed`, `no_longer_observed`), counts company–recipient pairs, only when Relationships is switched on, so it would be mislabelled as recipients. Per prompt item 3 the cell is shown without the count. Request in HANDOFF. |

## D. Analyses rail

| # | Element | Board I1 | Build | Status |
|---|---|---|---|---|
| D1 | Card | 235.2-532.8 x 284-848 | 226-526 x 284-848 | fixed |
| D2 | Title "Analyses" | cap A 298.4-316.8 | 298-316 (25px serif) | fixed |
| D3 | First row label | "Favorites" | "Top recipients" | intended (Don't copy item: the rail label is "Top recipients") |
| D4 | Other labels | Trends, Changes, Concentration, Relationships, Company overlap, Timing, Recipient profiles, Outgoing spending, Legislative context, Forecasts | same | fixed |
| D5 | Row pitch | 39.8 | 40.3 | fixed |
| D6 | Label type | "Trends" cap 9.6 at 382.4 | cap 10 at 381 (12.5px) | fixed |
| D7 | Switch colour (on) | (27,134,135) | `--acu-teal` #327a7a | intended (theme token; the board's generator renders teal lighter) |
| D8 | Footer "Core three │ All" | cap 812-820 | 814-822 | fixed (+2) |
| D9 | Switch box (fix round 1) | 481.6-516.8 x 339.2-357.6 (35.2 x 18.4) | 473-508 x 338.3-356.3 (35 x 18, 14px knob, travel 17px); was 37 x 21 | fixed (within 1.3px after the 8px offset) |

## E. "Giving through the same point in each cycle"

| # | Element | Board I1 | Build | Status |
|---|---|---|---|---|
| E1 | Card | 545.6-1577.6 x 284.8-573.6 | 537-1578 x 284-573 | fixed |
| E2 | Title and (i) | cap top 298.4, 23.2 tall | 298, 22 tall (23px serif); (i) opens method and sources | fixed |
| E3 | Channel line "Employee giving ⌄" under the title | not on the board | select inside the card (323-343) | intended (prompt item 6: a card that offers channels carries its select inside the card, opening on the summary's channel) |
| E4 | Legend, top right | three 5px dashes + "2023-2024 cycle", a solid key + "2025-2026 cycle"; 63px of text ink | same keys (dashes redrawn this session); text 8.8px | fixed |
| E5 | Chart │ Table | 1428-1567.2 x 294.4-322.4 | 1428-1566 x 293-321 | fixed |
| E6 | Pressed segment fill | (76,63,129) | plum #342649 (build 01's `.segmented`) | intended (shared primitive; build 01 kept `.segmented` plum-selected everywhere except PAC panes) |
| E7 | Plot extent | axis 605.6 → "0" at 1493; y labels end at 591.2; top rule at 362.8, $0 at 521.5 | axis 606 → "0" at 1494; labels end at 590; top rule at 361, $0 at 520 (the plot sits under the channel line, E3) | fixed (this session moved the plot 13px left and ran the rules on under the Today label) |
| E8 | X axis | 600 on the left to 0 on the right, "Days before the election" | same; ticks 600,500,400,300,200,100,0 | fixed |
| E9 | Y axis | $0 to $14M in $2M steps | $0 to $25M in $5M steps | intended (real data) |
| E10 | Earlier cycle | dashed taupe | dashed `--acu-taupe` (5 on, 4 off) running to 0 days | fixed |
| E11 | Later cycle | solid teal ending at a dot "Today $12.0M" | solid `--acu-teal` ending at the dot "Today $11.9M" | fixed (value is real data) |
| E12 | Today rule | near 0 days | at 42 days: today is 2026-09-22 and the election is 2026-11-03 | intended (real date) |
| E13 | Shape | smooth rise to today | monthly points joined by straight segments; the later line is flat from about 120 days because little August–September activity is collected yet | intended (real data; prompt: join points, never smooth or fill) |
| E14 | "quarterly points" in the legend | n/a | not shown: the trends panel returns monthly `series` (133 points for Banking) | fixed (prompt adds it only when only quarterly points exist). Fix round 1 built the fallback: a channel with no monthly points uses `quarterly_series` (quarter-end points joined the same way) and the legend adds "quarterly points" (checked with a synthetic fixture: `build04\fix1_quarterly.log`, `shots\fix1_quarterly_only.png`). The engine never takes that path today: `analysis_metrics.py:363` gives the trends panel monthly `series`, and `quarterly_series` exists only on the timing panel (`:578`), both built from the same dated rows. |

## F. "What changed"

| # | Element | Board I1 | Build | Status |
|---|---|---|---|---|
| F1 | Card | 546.4-1043.2 x 588-852.8 | 537-1039.4 x 587-853.2 | fixed |
| F2 | Channel line | not on the board | "Employee giving ⌄" | intended (as E3) |
| F3 | Plot | top tick at 654.4; 0 line at 805; labels cap top 814.4 | top tick 654; 0 line at 805; labels at 814 (this session: +9px of plot) | fixed |
| F4 | Steps | Baseline $10.7M → Continuing +$0.9M → Newly observed +$1.6M → No longer observed −$1.2M → Current $12.0M | Baseline $21.1M → Continuing −$9.2M (red) → Newly observed $0 → No longer observed $0 → Current $11.9M | intended (real data: all ten Banking companies gave in both periods, so the engine's exact decomposition puts the whole change in Continuing; zero steps are drawn as hairlines) |
| F5 | Total bars | (75,64,129) | `--acu-purple` #57447b | intended (theme token) |
| F6 | Y ticks without $ | 16M … 0 | 25M … 0 | fixed |
| F7 | Connectors | dotted between steps | dashed 3/3 | fixed |
| F8 | Value labels at the edges (fix round 1) | n/a (I1's values sit clear of both edges) | A falling step that would put its label on the x labels (it ends at the axis) is labelled above its bar. A bar within 10px of the top tick adds one tick of head-room, so its label stays inside the plot. Synthetic fixtures, through the suite's own mock route: $10.0K → −$10.0K → $0, and $2.0K → +$8.0K → $10.0K. Result: 0 text overlaps and no text above the plot (`build04\fix1_wf_zero.log`, `shots\fix1_wf_A_fall_to_zero.png`). Before the fix, the reviewer measured "−$10.0K" at 667-681 over "Continuing" at 670-682. Banking is unchanged (25M top tick, same labels). | fixed |

## G. "Top recipients"

| # | Element | Board I1 | Build | Status |
|---|---|---|---|---|
| G1 | Card | 1056-1576.8 x 588-852 | 1051.4-1578 x 587-853.2 | fixed |
| G2 | Title | "Top recipients" (was "Favorite recipients") | same | fixed |
| G3 | Columns | # │ Recipient │ Amount │ Change | # │ Recipient │ Amount | **open (data)**: the favorites panel returns amounts over all observed cycles (`amount_cents`, `observed_cycles`), not per period, so there is no Change to show. Request in HANDOFF. |
| G4 | Note under the title | none | "Employee giving ⌄ · All observed cycles" | intended (the select per prompt item 6; the note states that the amounts are not period amounts) |
| G5 | Header row | cap top 642.4 | cap top 655 | intended (follows G4: the channel line takes 20px) |
| G6 | Row pitch | 23.2 | 21 (eight rows still end at 840) | intended (follows G4) |
| G7 | Type | header cap 8.8; "ACTBLUE" 44.8 x 8 of ink | header 12px; "ACTBLUE" 44 x 8 (set this session) | fixed |
| G8 | Amount column | left-aligned under "Amount" at about 1378, Change to its right | right-aligned at the card's content edge | intended (follows G3) |
| G9 | Names | short PAC names | real committee names, ellipsised with the full name in a tooltip | intended (real data) |
| G10 | Chart view | the ranked list, with Chart pressed | the ranked list, with Chart pressed; Table view holds the full returned table (25 rows) | **open (prompt vs board, Paul rules)**. Prompt 04 item 5 says "Chart view draws bars"; I1 shows the ranked list under a pressed Chart segment. The build follows the board (README: the board wins), so the "Chart" segment shows an 8-row ranked table and "Table" a different 25-row table. Options for Paul: keep as built; draw bars in Chart view (the prompt); or relabel the segment "Ranked │ Table" on this card. |

## H. States with no board of their own

| # | State | Build | Status |
|---|---|---|---|
| H1 | After Swap periods | Chips read 2025-2026 → 2023-2024. The strip reads Net giving 2025-2026 $11,883,136, Net giving 2023-2024 $21,106,728, Change +$9,223,592 +77.6% in teal (`insights-up`). The waterfall follows the chips: Baseline 2025-2026 → Continuing +$9.2M → Newly observed → No longer observed → Current 2023-2024. Each step is negated and newly / no longer observed trade places, exact on the returned cents. The running-total chart stays in time order (dashed 2023-2024, solid 2025-2026). The request is always sent in time order (earlier cycle as `baseline_cycle`), because the server refuses a later baseline (`analysis_data.py` `validate` and `_prepare`: "The baseline cycle must be earlier than the current cycle."). | **open (Paul rules on what Swap means)**. As built, Swap reverses the comparison's direction: the strip and waterfall read from the left chip to the right chip, so "+77.6%" in teal describes going back from 2025-2026 to 2023-2024, although giving fell 43.7% over time. Design call 10 makes teal-up mean growth. The alternative is that Swap only re-orders the chips while the strip and waterfall stay in time order. Either way, prompt 04 item 2 ("They drive `baseline_cycle` and `current_cycle`") holds only for an earlier → later pair: a later-first pair is re-ordered before it is sent. Deviation: intended (the engine forbids a later baseline), pending Paul's ruling. |
| H2 | Concentration switched on | A fourth card, "Concentration and breadth", full width below the three, with the same chrome and the channel select on Employee giving | fixed |
| H3 | Table view on each card | Every card's table opens on the card's channel: its rows first, other giving channels next, review channels last (server order kept within each; a column sort still wins). Top recipients shows "Showing 25 of 2,385 rows" under the table; no yellow banner. | fixed (this session: before, the running-total table opened on "Conflicting source evidence") |
| H4 | Empty scope (Company Citibank, Funding Conflicting source evidence) | Each card reads "No receipts in this period for this scope." in `--muted`, with Chart and Table disabled; the strip shows "—" | fixed |
| H5 | Failed query | Each card shows the message and a "Try again" link inside the card (asserted in `test_insights_browser.cjs`) | fixed |
| H6 | A chip set to the cycle the other chip shows (fix round 1; was a major defect) | Before: picking 2025-2026 on the left while the right chip was automatic (2025-2026), or 2023-2024 on the right while the left was automatic (2023-2024), pinned the other chip to the same cycle. The server answered 400 and every card read "The baseline cycle must be earlier than the current cycle." with a Try again that re-sent the same pair. Now the picked cycle exchanges the pair, as Swap does: the other chip takes this chip's previous cycle, or the neighbouring cycle when there is none. Both pick paths give chips 2025-2026 → 2023-2024 with all three cards ready and no failed request (8814, 1440x900: `build04\fix1_probe_1440x900.json` `equalLeft` / `equalRight`; capture `04_equal_*`). A pair the server would still refuse is never sent. This covers both chips forced to one cycle, and an explicit latest baseline with an automatic current, predicted with the server's own resolution rule. The cards instead read "Choose two different cycles to compare." (muted, no Try again) and the chips show the refused pair. `test_insights_controls_browser.cjs` now mirrors the server's rule in its mock and asserts that no request pairs a baseline with an equal or later current cycle. That suite fails on the pre-fix `insights.js` with `["2025-2026","2025-2026"]` (negative control). | fixed |
| H7 | All analyses on (fix round 1) | Cards keep their own height (`align-items:start`); only What changed and Top recipients still share a row height, so I1 is unchanged. At 1440x900 "Company portfolio overlap" is 470px tall beside the 887px Timing card; it was stretched to match. A title too long for a half-width card wraps inside its own column, and Chart │ Table stays on the title row. On a phone (≤760px) the title takes the full row again. Capture `04_all_*`. | fixed |
| H8 | Records view titles (fix round 1) | The records view is titled after the card it came from: "Continuing · What changed", and "2025-2026 · same-stage net through Today · Giving through the same point in each cycle". The header Sources button, which is not tied to a card, opens "Source records for the current scope". Before, it showed the server's panel titles ("Comparable-cycle trends", "Explain the change"). | fixed |
| H9 | Concentration group names (fix round 1) | "Company" and "Recipient" now sit above their bar groups. Before, the responsive figure's first repaint removed them, so both groups were unlabelled. `test_insights_browser.cjs` asserts 2 group titles after the repaint; it fails on the pre-fix `insights.js` (negative control). | fixed |
| H10 | An industry not prepared before (fix round 1) | The page polls every 1.5 s for a minute, then every 5 s, for about 16 minutes in all. After the first minute the card message adds "Preparing an industry for the first time can take several minutes; this page keeps checking." Before, it stopped after 120 polls (about 3 minutes); the reviewer measured cold builds of 248 s (Credit Arms) and 301 s (Property & Casualty). Not re-timed on a cold industry here: Banking was already prepared on 8814. | fixed (pre-existing behaviour) |

## I. Checks the prompt names

- **No card opens on a diagnostic channel.** Default capture: `Trend chart funding source=employee_original`, `Change chart funding source=employee_original`, `Top recipients funding source=employee_original`, and with Concentration on, `Concentration chart funding source=employee_original`. The review channels (Conflicting source evidence, Unverified funding, Unverified organization, Non-giving records) are ranked last in every select and table.
- **Export appears once.** One `#insights-export-menu` in the header; no per-card Export.
- **The running-total x axis ends at 0 on election day.** Ticks read 600, 500, 400, 300, 200, 100, 0 (`trendXTicks` in `measurements.json`); day 0 is computed as the Tuesday after the first Monday in November (2024-11-05, 2026-11-03).

## J. Overlaps and alignment (getBoundingClientRect)

`measurements.json` holds every rect and the pair checks for each capture: title vs (i) vs legend vs Chart │ Table in each card, chip vs chip vs swap vs ⋯, the Funding select vs the first chip, the rail vs the cards, every card pair, and the three header buttons. The overlap count for every capture is listed in `HANDOFF.md`. Supporting-card headings align within 2px (asserted in `test_insights_browser.cjs`).

## K. Proof images in this folder

`04_<state>_<viewport>.png`: board I1 left (scaled to its 1600x905 CSS frame), build right at its own CSS size. States: default, swap, equal (fix round 1: 2025-2026 picked on the left), concentration, all (fix round 1: every analysis on), table and empty, at 1440x900 and 1920x1080, plus default and swap at 1600x900 (the board's own frame). `_fullpage` variants show content below the fold (the fourth card, the All layout, and the table counts). Every image was re-captured in fix round 1, after the last edit.
