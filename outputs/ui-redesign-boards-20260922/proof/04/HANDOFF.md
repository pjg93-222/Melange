# Build 04 (Insights, board I1): handoff

2026-09-22. Nothing was committed and no git command that changes state was run. Paul's console (8806) was not touched. This build's read-only console ran on 8814 and is stopped.

## 1. Resume or restore: RESUME

The census said the first builder (session 8a67e999) "died mid-rewrite". The files say otherwise.

- **Its rewrite was complete.** At 11:40 it wrote the whole new module in one pass: its scratch `spec_js.py` (120 KB), `new_dom.js` (63 KB), `new_insights.css` and `new_view_insights.html` all date from 11:33-11:40.
- **The partial message came earlier.** Its "Now let me write the new Insights DOM modu..." is from 11:32, before that pass.
- **It passed its suites and moved on to polish.** It ran both Insights browser suites green at 12:08, then spent 12:10-12:20 on screenshots and CSS polish (heading container query, legend placement). The 12:43 stop was a usage limit.
- **The bytes it left pass.** This build's baseline, run at 16:30 on those bytes (the 12:07-12:20 files), gave:
  - `test_insights_browser.cjs`: PASS (73 s).
  - `test_insights_controls_browser.cjs`: PASS (34 s).
  - `render_console.py --check`: up to date (75,998 bytes).
  - `test_console_templates.py`: 10/10 OK.
- **The code matches the prompt.** Reading it showed each of prompt 04's eight items implemented, and the Chart view followed I1. Most test-assertion changes are re-homings: `#insights-compare-open` became the period chips and `#insights-more-options`; the sub-tabs became the rail and `#insights-page-sources`; the per-card Export became the header menu; `#insights-retry` became the per-card Try again. **One assertion was replaced, not re-homed** (corrected in fix round 1). The 09-21 file's `assert.equal(await page.locator('.insights-chart svg').count(),3)` (its line 59) became two assertions: "Top recipients ranks the returned rows in Chart view" and "No dated series: no running-total curve is drawn from undated totals". The first fixture has no dated series and no change cards, so three charts cannot exist under the new design; the engine pass later in the file still asserts the drawn charts (legend spans, four waterfall totals).
- **Restoring would have cost the build.** It would have discarded a passing, board-aligned build and brought back the pre-redesign page.

**Pre-edit copies kept.**
- The 09-21 originals: `...\8a67e999-...\scratchpad\build04\preedit\`.
- The 12:07-12:20 bytes this build started from: `...\5ab381bb-...\scratchpad\mentat\build04\preedit\`.
- Hashes are in that folder's `ledger.json`.

## 2. Data check (prompt 04, done first)

- **A dated running-total series exists.** `panels.trends.series` holds monthly net amounts per money channel: `{funding_source, month: "YYYY-MM", amount_cents, gross_cents, adjustment_cents, records}`. Banking has 133 of them. The chart builds each cycle's running total from 1 January of the cycle's first year:
  - Each month lands on its last day.
  - The later line ends at the cutoff, at the exact same-stage figure.
  - Points are joined by straight segments. Nothing is smoothed, and missing months stay missing.
  - It never draws from undated totals. With no series, Chart is disabled and the (i) says why; `test_insights_browser.cjs` asserts this.
- **A same-election-stage figure exists.** `panels.trends.rows[].matched_amount_cents` through `matched_through`: today's date mapped into each cycle, so 2024-09-22 and 2026-09-22 for 2023-2024 and 2025-2026. `panels.changes.cards[].baseline_cents / current_cents` carry the same amounts, reconciled exactly with three components.
  - The summary strip and the waterfall use them.
  - This is also the figure design call 5 names for Graph's future "Same point" compare. No Graph work was done here.
- **There is no all-channel aggregate.** The engine returns channels separately and says: "Money channels are calculated separately; totals from different stages must not be added together." So the default is the largest **giving** channel by magnitude, which is Employee giving for Banking, and it is named in the strip. The review channels (Conflicting source evidence, Unverified funding, Unverified organization, Non-giving records) are never a default.
- **Missing fields**, reported as the prompt asks:
  - Recipient counts by period (continuing / new / no longer observed).
  - Per-period recipient amounts and change for Top recipients.

## 3. Files (all under `C:\Users\pgoff\Mentat\mentat\`)

All five source files are untracked (never committed) and none is git-ignored. `view_insights.html` is un-ignored by `.gitignore:23`.

This table records the build as first handed off (18:14). **Fix round 1 changed four of these files; their current hashes are in §8.**

| File | sha256 (at 18:14) | Bytes | Lines | Line endings | This session's change |
|---|---|---|---|---|---|
| `app/templates/view_insights.html` | `e9eb98ca04635b1e5f756352398accffa6d96bcc06ea0757567e494985469231` | 6,283 | 50 | 49 CRLF, 1 LF (unchanged) | none (the first builder's 12:07 bytes) |
| `app/insights.js` | `6b9906f315bc0ff554cdb2fcd9f2af028608cbbe98c1690aaab345607aad207e` | 81,123 | 842 | 750 CRLF, 92 LF (was 738 / 92; only CRLF lines added) | +23 −11 lines (hunks js_a, js_b, js_c) |
| `app/insights.css` | `af6ea6adb8567a3444304cb268ad33ff343b9f1fe75886e12644d075875dda0c` | 25,434 | 232 | 231 CRLF, 1 LF (was 230 / 1) | +29 −23 lines against the 12:20 bytes (hunks css_a-css_e, including this build's first session at 16:39-16:42) |
| `tests/test_insights_browser.cjs` | `9195eb5a56b1efd217e88a88025dfc67cf6d91da49d3a00509e49038e11cbcc8` | 31,068 | 250 | 221 CRLF, 29 LF (unchanged) | none (the first builder's re-homed assertions, reviewed) |
| `tests/test_insights_controls_browser.cjs` | `69548b7d2b5c9b12f739e336a7bf3e5368c382dff7ae05dea379c74217f250bf` | 12,048 | 87 | 87 CRLF (unchanged) | none (reviewed) |
| `app/index.html` (golden) | `802d989fb1cb41b0d92aec9ed8c80d0f1a7dbc67c3b4bcfdf4bbca70e378554c` | 78,787 | 474 | LF (renderer) | `render_console.py --write` at 18:03, right before the final suite run. It includes the other builders' templates as they stood then, which is why it grew from 75,998 bytes. |

Against the 09-21 originals, the whole build is:
- `insights.js`: +496 −153 lines.
- `insights.css`: +219 −134.
- `view_insights.html`: +44 −31.
- `test_insights_browser.cjs`: +30 −32.
- `test_insights_controls_browser.cjs`: +6 −6.

**What this session changed.**
- **js_a:** Table view opens on the card's channel. Swapped chips draw the waterfall in the chips' order: each step negated, newly and no-longer observed swapped. It is exact on the returned integer cents.
- **js_b:** the waterfall is 9px taller, so its 0 line and labels sit where I1 has them.
- **js_c:** the running-total plot spans I1's 606-1493, and its rules run on under the Today label.
- **css_c:** legend keys as dashes.
- **css_d:** Top-recipients type.
- **css_e:** 8.8px legend text, a 28px Chart │ Table control, and 7px under the What changed card.

**Not touched:**
- `analysis_*.py`, which are read-only for this build.
- `server.py`: no new static file, so no `STATIC_ASSETS` change and no restart needed.
- `app.js`.
- The single-writer files (`acu-theme.css`, `workspace-polish.css`, `page_shell.html`, `page_head.html`, `test_workspace_polish_browser.cjs`).
- Paul's 09-22 citation edits.

**Proof files** (as first handed off; fix round 1 re-captured everything, see §8). `DIFFERENCES.md`, `HANDOFF.md`, 24 side-by-side PNGs (12 viewport and 12 full-page, captured 18:00-18:12, after the last edit at 17:59) and `measurements.json` (every rect; 218 overlap pair checks; 0 overlaps; no page errors; no HTTP failures) sit in `outputs\ui-redesign-boards-20260922\proof\04\`. `measurements.json` is git-ignored by `.gitignore:6` (`*.json`); the .md and .png files are not ignored.

## 4. Contracts exposed

- **Element ids used by tests.**
  - Header: `#insights-page-sources`, `#insights-export-menu`, `#insights-export-csv`, `#insights-export-json`, `#insights-refresh`.
  - Filters: `#insights-controls`, `#insights-dataset`, `#insights-company`, `#insights-basis`, `#insights-funding-source`.
  - Periods: `#insights-baseline-cycle`, `#insights-current-cycle`, `#insights-swap-periods`, `#insights-more-options`, `#insights-options`, `#insights-as-of`, `#insights-comparison-dataset`.
  - Summary: `#insights-summary-left|right|change|recipients` (plus `-label`).
  - Rail: `#insights-analyses`, `#insights-toggles`, `#insights-toggle-<panel>`, `#insights-core-only`, `#insights-enable-all`, `#insights-preference-note`.
  - Cards and status: `#insights-results`, `#insights-panel-<panel>`, `#insights-table-<panel>`, `#insights-status`.
  - Sources view: `#insights-sources`, `#insights-scope`, `#insights-sources-title|status|table|prev|next|retry|close`.
- **Retired ids**, with their assertions re-homed: `#insights-compare-open`, `#insights-analysis-overview|choose|sources`, `#insights-choose-view`, `#insights-disable-all`, `#insights-retry`.
- **Request body.** Unchanged: `dataset, basis, panels, company, funding_source, as_of, baseline_cycle, current_cycle, comparison_dataset, retry`. Swapped chips are sent in time order, earlier as `baseline_cycle`, because the engine only compares an earlier baseline with a later cycle.
- **URL and scope.** Insights reads and writes only `industry` through `MentatScope`. It never writes Graph's `cycle`, and it adds no query keys (D-039 unchanged).
- **Browser storage.** The `localStorage` key `mentat.insights.panels.v1` holds the enabled analyses.
- **Script API.**
  - `window.MentatInsights.setActive(bool)`.
  - Node exports from `insights.js`: `display, csvCell, exportCSV, PANELS, SHORT_TITLES, cycleEnd, electionDay, daysBefore, runningTotals, channelMagnitudes, rankChannels, defaultChannel, niceTicks, millions, tickMoney, DIAGNOSTIC_CHANNELS`.
- **Build 01 primitives used, not redefined:** `.card`, `.card-title`, `.segmented`, `.page-actions`, `.chip-select`, `.icon-button`, `.secondary`, `.primary`. The page gets one plum `.primary` (Refresh) and no gold.

## 5. Suites

| Suite | Before (16:30-16:37, on the 12:20 bytes) | Mid (17:32, stale golden) | After (18:03-18:08, after `--write`) |
|---|---|---|---|
| `test_insights_browser.cjs` | PASS | FAIL at line 239: `Cannot read properties of null (reading 'addEventListener')` at `evidence.js:2415` (build 06's script against the stale golden). The same page rendered from current templates had no error. | **PASS** (91 s) |
| `test_insights_controls_browser.cjs` | PASS | PASS | **PASS** (48 s) |
| `render_console.py --check` | up to date (75,998 B) | out of date (build 02's `view_graph.html`) | **up to date (78,787 B)** |
| `test_console_templates.py` | 10/10 OK | 2 FAIL (stale golden) | **10/10 OK** |
| `test_analysis_http.py` | not run | not run | **3/3 OK** (after only) |
| `test_workspace_polish_browser.cjs` | FAIL: "graph must not overflow at 390" (build 02), then FAIL at line 142 `.xref-adjustments` | not run | FAIL at line 142 `.xref-adjustments` (Cross-reference). The Insights capture at line 139 (1168, 900, 390, no overflow) passed before it. Rerun: see §7. Not build 04's. |
| `test_console_browser.cjs` | FAIL at line 164 (Graph → Chart Studio → evidence split) | not run | FAIL at line 296 (`#graph-candidates`, the Graph view build 02 is changing). Rerun: see §7. Not build 04's. |

## 6. Open items and requests

**For Paul** (fix round 1 added 3-4 and sharpened 1):
1. **More options ⋯** (DIFFERENCES B8, with B4, B5 and B7): keep it (as built), or remove the "Contributions through" and "Compare industry" controls. Removing them also drops or re-homes the `test_insights_controls_browser.cjs` steps at lines 69-76, which need your consent.
2. **The summary names its channel** ("· Employee giving", C3). Is that acceptable in place of I1's plain "Net giving 2023-2024"? An all-channel total is refused by the engine.
3. **What Swap means** (H1). As built, Swap reverses the comparison: after a swap the strip reads "+$9,223,592 +77.6%" in teal, going from 2025-2026 back to 2023-2024. The alternative is that Swap only re-orders the chips while the strip and waterfall stay in time order. Either way, the request is sent in time order, because the engine refuses a later baseline.
4. **Top recipients Chart view** (G10): the board's ranked list (as built), the prompt's bars, or relabel that card's segment "Ranked │ Table".

**For the analysis owner** (`analysis_metrics.py` is read-only for this build):
5. **Recipient counts** (C7): per channel, in `changes.cards[]`, add recipient-level `continuing_recipients`, `newly_observed_recipients` and `no_longer_observed_recipients` under the same-stage cutoffs. The Recipients cell then reads "N continuing · N new · N no longer observed". Today it shows "—".
6. **Top recipients Change** (G3): add per-period `baseline_cents / current_cents / change_cents` per recipient, under the same-stage cutoffs of the selected cycles, to `favorites` or a sibling panel. The Change column (teal up, red down) is not drawn until then.

**For the shell / single-writer holder** (build 02 now):
7. **Shell footer below the fold** (A4): build 01's footer makes the page scroll at every required viewport: scrollHeight 939 at 1440x900 and 1600x900 (39px), and 1081 at 1920x1080 (1px). I1 shows no footer, and the Insights content ends at 853 as on the board. **Request to the shell's single-writer holder:** move the footer into the viewport flow, or correct the main `min-height` calc, so a page whose content fits does not scroll. The reviewer traced it to `page_shell.html` and `workspace.css:88-101`. `workspace.css` is build 06's file in this workflow and carries Paul's 09-22 edits, so it is a request, not a change. Insights needs no change of its own.
8. **Colours** (A11, E6): `.primary` and `.segmented` stay plum by build 01's ruling, where I1 draws a lighter indigo. No change requested.

**For builds 02 and 06:** the golden `index.html` was re-rendered at 18:03 with your templates as they stood then. Re-render after your next template edit.

## 7. Suite reruns (other builders' views)

One rerun at 18:08-18:11 on the same bytes gave the same results, so they are reported, not fixed:

- `render_console.py --check`: up to date (78,787 B).
- `test_console_templates.py`: 10/10.
- `test_analysis_http.py`: 3/3.
- `test_workspace_polish_browser.cjs`: FAIL again at line 142, waiting on `.xref-adjustments` in Cross-reference. It passed the Insights capture at 1168, 900 and 390 wide first.
- `test_console_browser.cjs`: FAIL again at line 296, where `waitForFunction` waits for `#graph-candidates` to contain $777.00 in the Graph view that build 02 is changing. The Insights assertions come later in that file (line 465), so this run does not reach them.

Neither failure is in an Insights file. Both suites were red on the baseline too, at Graph and Cross-reference points.

## 8. Fix round 1 (2026-09-22, 19:13-19:45)

Two reviews came back. **Review A** is the list with ten ids, backed by `review04\run_1440.log`, `run_quick.log` and `wf_zero.cjs`. **Review B** is the list with six ids, backed by `review04\probe.json` and `probe3.cjs`. Both reviews used the id R04-1, for the same defect. Every defect was confirmed on the bytes; none needed disproving. Below, `build04\` means `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-melange-ui-redesign-372c43\5ab381bb-9ad1-45b2-b970-3c0b108c263b\scratchpad\mentat\build04\`. Nothing was committed, and no git command that changes state was run. The read-only console ran on 8814 only and is stopped. 8806 was not touched.

**Defect → action**

| Defect | Severity | Action | Where it is recorded |
|---|---|---|---|
| A R04-1 = B R04-1: equal period pair from the chips, 400, looping Try again | major | **Fixed.** Picking the cycle the other chip shows now exchanges the pair, as Swap does. The other chip takes this chip's previous cycle, or the neighbouring one when there is none. `load()` also predicts the server's automatic resolution (`analysis_data.py` `_prepare`) and never sends a pair the server would refuse: every card reads "Choose two different cycles to compare.", muted, with no Try again. The pin rule for a later-first pair now uses strict `>` / `<`. The controls suite's mock now refuses such pairs as the server does, and the suite asserts that no request pairs a baseline with an equal or later current cycle. On the pre-fix `insights.js` it fails: "The chips sent a pair the server refuses: [\"2025-2026\",\"2025-2026\"]". | DIFFERENCES H6 |
| A R04-2: Swap semantics; H1 marked fixed | minor | **Re-recorded, no code change.** H1 is now open for Paul, stating the as-built behaviour (Swap reverses direction) and the prompt item 2 deviation (a later-first pair is sent in time order). | DIFFERENCES H1; §6 item 3 |
| A R04-3: waterfall labels on the x labels / above the plot | minor | **Fixed.** A falling step that would reach the x labels is labelled above its bar. A bar within 10px of the top tick adds one tick of head-room. The reviewer's fixture ($10.0K → −$10.0K → $0) and a rise-to-top fixture give 0 overlaps and no text above the plot. | DIFFERENCES F8 |
| A R04-4: records-view titles use the server panel titles | minor | **Fixed.** The title uses `cardTitle()`, so it names the card the reader came from; the header Sources button gets "Source records for the current scope". | DIFFERENCES H8 |
| A R04-5: switch 37x21 vs I1's 35.2x18.4 | minor | **Fixed.** The switch is now 35x18 with a 14px knob (travel 17px), measured at 473-508 x 338.3-356.3. | DIFFERENCES D9 |
| A R04-6: page scrolls at every viewport (shell footer) | minor | **Re-recorded, no Insights change.** A4 now names 1440x900 and 1600x900 (939) and 1920x1080 (1081). The request goes to the shell's single-writer holder. | DIFFERENCES A4; §6 item 7 |
| A R04-7: All layout stretches cards; heading control wraps | minor | **Fixed.** The results grid uses `align-items:start`; only What changed and Top recipients keep equal height, as on I1. A long title wraps in its own column and Chart │ Table stays on the title row; on a phone the title takes the full row. | DIFFERENCES H7; `04_all_*` |
| A R04-8: G10 marked fixed despite prompt/board conflict | minor | **Re-recorded, no code change.** G10 is now open for Paul. The labels stay "Chart │ Table" as on I1; "Ranked │ Table" is offered as an option. | DIFFERENCES G10; §6 item 4 |
| A R04-9: cold-industry polling cap (pre-existing) | minor | **Fixed (optional).** The page polls at 1.5 s for a minute, then at 5 s, for about 16 minutes in all. The card message says the page keeps checking. Not re-timed on a cold industry. | DIFFERENCES H10 |
| A R04-10: strip labels clip at 1366 and below | minor | **Fixed** (C3 itself stays open). The label wraps, with "· Employee giving" kept as one unit, and the values stay level. 1440, 1600 and 1920 are unchanged. | DIFFERENCES C3 |
| B R04-2: More options vs I1 (chip shift, narrower selects) | major (Paul's ruling) | **Re-recorded, no code change.** B4, B5 and B7 are now "intended if B8 stays; open with B8". B8 names the test steps (controls suite lines 69-76) that removal would drop. | DIFFERENCES B4-B8; §6 item 1 |
| B R04-3: concentration group titles removed by the repaint | minor | **Fixed.** The title sits in a `.insights-bar-group` wrapper outside the responsive figure. `test_insights_browser.cjs` asserts 2 titles after two animation frames; it fails on the pre-fix `insights.js`. Live Banking shows "Company" and "Recipient". | DIFFERENCES H9 |
| B R04-4: strip suffix vs I1 | minor (Paul's ruling) | **Re-recorded.** C3 was "intended" in DIFFERENCES but open in this file; it is now open in both. | DIFFERENCES C3; §6 item 2 |
| B R04-5: no quarterly-only fallback | minor | **Built and recorded.** A channel with no monthly points uses `quarterly_series` at quarter ends, and the legend adds "quarterly points" (synthetic fixture: `build04\fix1_quarterly.log`). The engine never returns that case today (`analysis_metrics.py:363` vs `:578`). | DIFFERENCES E14 |
| B R04-6: HANDOFF said "re-homings, not drops" | minor | **Corrected.** §1 now says the three-svg assertion was replaced. | §1 |

**Files after fix round 1** (all under `C:\Users\pgoff\Mentat\mentat\`). Each file was checked against its last recorded sha256 immediately before each edit; there was no other writer. Edits were byte-exact hunks from `build04\specs\fix1_*.py`, applied by `build04\hunk.py`. Pre-edit copies are in `build04\preedit_fix1\`, and the ledger is `build04\ledger.json`.

| File | sha256 | Bytes | Lines | Line endings | Fix-round change |
|---|---|---|---|---|---|
| `app/insights.js` | `0df2f4b19df33553977edd2bb9466aadcc5459dd2cacfbe20764270f2ae36128` | 85,432 | 881 | 789 CRLF, 92 LF (LF lines unchanged; only CRLF lines added) | +62 −23 |
| `app/insights.css` | `5592c724aae6c4895133ebd9cf22651c12c401b95029ce66894190303ad37cb8` | 25,556 | 234 | 233 CRLF, 1 LF | +11 −9 |
| `tests/test_insights_browser.cjs` | `e31c87d3ce3b8a66f1dc19ca63d25582213dba15895a862062ce6fbbbc592708` | 31,367 | 252 | 223 CRLF, 29 LF | +2 |
| `tests/test_insights_controls_browser.cjs` | `5d1fba9bd65522c6dd6ebe13c086b476cf7963d36765e5a11ccdf082f798ee52` | 15,644 | 110 | 110 CRLF | +25 −2 |
| `app/templates/view_insights.html` | `e9eb98ca04635b1e5f756352398accffa6d96bcc06ea0757567e494985469231` | 6,283 | 50 | 49 CRLF, 1 LF | none |
| `app/index.html` (golden) | `802d989fb1cb41b0d92aec9ed8c80d0f1a7dbc67c3b4bcfdf4bbca70e378554c` | 78,787 | 474 | LF | `render_console.py --write` right before the final suite run found it already up to date; `--check` up to date |

Not touched: `analysis_*.py`, `server.py`, `app.js`, the single-writer files and Paul's 09-22 citation files.

**Contracts added.** None of these changes an id or the request body.
- **Card state.** A card can carry `data-state="invalid"`, for a refused period pair.
- **New classes.** `.insights-summary-channel` is the strip's channel phrase. `.insights-bar-group` wraps each concentration group and its `.insights-bar-group-title`. `.insights-legend-quarterly` is the quarterly legend entry.
- **Records view title.** It is `<label> · <card title>`, or just the label for the header Sources button.

**Suites.**

| Suite | Before (19:15-19:18, on the 18:14 bytes) | After (19:39-19:41, after `--write`) |
|---|---|---|
| `test_insights_browser.cjs` | PASS | **PASS** (re-run directly: PASS, 29 s) |
| `test_insights_controls_browser.cjs` | PASS | **PASS**, with the new period-chip block (re-run directly: PASS, 61 s) |
| `render_console.py --check` | up to date (78,787 B) | **up to date (78,787 B)** |
| `test_console_templates.py` | 10/10 OK | **10/10 OK** |
| `test_analysis_http.py` | 3/3 OK | **3/3 OK** |
| `test_workspace_polish_browser.cjs` | FAIL at line 142 (`.xref-adjustments`, Cross-reference) | FAIL at line 142, the same failure; one rerun gave the same result. `.xref-adjustments` is written by `cross-reference.js:250`, not an Insights file. |
| `test_console_browser.cjs` | PASS | **PASS** (its Insights assertions now run) |

**Negative controls.** The new test code was run against the pre-fix `insights.js`, in a scratch copy of `app/` (`build04\negctl\`):
- The controls suite fails on the equal pair.
- `test_insights_browser.cjs` fails at the concentration-title assertion.

**Proof.** 16 captures were taken after the last code edit and turned into 32 side-by-sides (16 viewport, 16 full-page) plus `measurements.json`. States: default, swap, equal, concentration, all, table and empty at 1440x900 and 1920x1080, plus default and swap at 1600x900. The measurements hold 408 overlap pair checks: 0 overlaps, no page errors, no HTTP failures. The default capture at 1600x900 matches the 18:14 capture rect for rect, except the switches. Probes in `build04\`: `fix1_probe_1440x900.json` (equal picks, refused pair, records titles, concentration, All), `fix1_narrow.json` (strip at 1920 down to 390), `fix1_wf_zero.log` and `fix1_quarterly.log`.

**Risks checked.**
- **Exchange semantics break an existing flow.** No: the console pass that picks 2023-2024 and then 2025-2026 explicitly (`test_insights_browser.cjs:211-212`) still passes, since neither pick equals the other chip's cycle.
- **The request guard refuses a pair the server would accept.** It predicts with the server's own rule: the option cycles, which are the server's `options.cycles`, filtered by the as-of year, then the latest cycle and the latest cycle before it. It refuses only a baseline at or after current, which the server rejects anyway. With no options loaded yet it never refuses.
- **Longer polling keeps a stale job alive.** No: any scope change calls `invalidate()`, which clears `pollTimer` and bumps the revision.
- **The strip wrap moves the board layout.** No: the strip is unchanged at 1440, 1600 and 1920, with values at 224.5. Only the dd moved to `margin-top:auto`, with 17.5px under it, replacing 12px of padding plus 5.5px of free space.
