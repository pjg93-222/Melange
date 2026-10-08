# Build 01 (console shell): differences from the boards

Corrected build, 2026-09-22, with the build-01b corrections (B6, B7) made the same day.

- Nothing was committed. Paul's console on port 8806 was not touched.
- The orchestrator ruled that, where 01_shell.md's numbers disagree with the board, the board wins (00_README: "one-to-one replica"). This build follows that ruling. The first pass (a 208px sidebar at the 01 spec's sizes) is superseded; its two scale-reference images are kept in `superseded-208px-build\`.
- **Build 01b** applied two rulings made under Paul's "the boards are binding one-to-one" and "proceed in the most optimal manner". B6: the sidebar's top padding moves to the board value. B7: the page background moves to the board's canvas colour. Both are fixed. Every file 01b replaced is kept in `superseded-before-01b\`.

**Frame used.** `M4_graph_default.webp` and `G1_compare_industry.webp` are 2000x1131: a 1600x900 CSS frame at **1.25x**, not the "about 1.7x" the prompt text gives. The scale is 1.25 on both axes, so the files are 905 CSS px tall, 5px more than a 900px viewport. Items pinned to the bottom of the sidebar are therefore compared from the bottom edge. Boards 3 and 6 are 2688x1520 (1.68x). Every board number below is in that frame.

**How it was measured.**
- The build was captured on a read-only console on port 8812 at 1440x900, **1600x900** (the board's own frame) and 1920x1080.
- `01_graph_1600x900_full-frame.png` puts the whole M4 beside the whole build, pixel for pixel.
- Positions come from one ink-measuring routine run on both the board and the build: cap top, baseline and left/right ink.
- **01b re-measure.** Build 01's routine resized M4 from 2000x1131 to 1600x900. That is 1/1.25 across but 1/1.2567 down, so every board row was lifted by 0.53% of its y: 0.5px at y 100, 1.8px at y 330, 4.3px at y 806. The board is now scaled by exactly 1/1.25 on both axes, and table A's board column is re-measured that way (B15).
- Layout numbers come from `getBoundingClientRect` (`measurements.json`).
- **01b captures.** Other builders were editing code and assets while these were taken. So the read-only instance showed its runtime notice, "This preview runs an older build" (`#stale-banner`), under the header. The notice is not part of any board. The capture script hid it (CSSOM `display:none`) before each screenshot, and `measurements.json` records that it would have shown (`staleBannerSuppressed`).
- In the 01b captures, the content below the header on Graph, Insights and Cross-reference may show the work in progress of builds 02, 04 and 05. Those images say so in their captions. None of it is build 01's.

**Status key.** **fixed**: the build now matches the board. **intended**: the difference is deliberate, and the reason is given. **open**: Paul needs to rule.

---

## A. Board versus build, sidebar and header (Graph at 1600x900)

Values are ink top / baseline, in CSS px. The board is at exactly 1.25x on both axes (01b).

| Element | M4 board | Build | Status |
|---|---|---|---|
| Sidebar border x | 200 | 199 (sidebar width 200px per the ruling, border inside it) | fixed (1px left of the board's) |
| Sidebar background | (243,239,234) | (243,239,234) | fixed |
| Page background | (247,243,238) | (247,243,238) | fixed (B7) |
| Wordmark MENTAT | 24 / 40, x 25-120 | 24 / 40, x 25-118 | fixed (B6) |
| Tagline | 52 / 62, x 25-145 | 52 / 62, x 25-146 | fixed |
| WORKSPACE | 89 / 96 | 88 / 95 | fixed (−1) |
| Loading | 109 / 118 | 109 / 119 | fixed (+1 at the baseline) |
| Collection | 133 / 143 | 134 / 144 | fixed (+1) |
| ANALYSIS | 173 / 179 | 174 / 181 | fixed (+1 / +2, see B5) |
| Active fill (Graph) | y 185-213 (28 tall), x ≈15.5-189 | y 187-215 (28 tall), x 16-189 | fixed (+2, see B5) |
| Chart Studio | 221 / 231 | 220 / 230 | fixed (−1) |
| Insights | 246 / 256 | 246 / 256 | fixed |
| Cross-reference | 272 / 282 | 271 / 281 | fixed (−1) |
| EVIDENCE | 314 / 320 | 311 / 318 | open (−3 / −2, see B15) |
| PAC evidence | 335 / 344 | 332 / 342 | open (−3 / −2, see B15) |
| Footer, line 1 | 810 / 818, baseline 87 above the frame's bottom | 806 / 814, 86 above | fixed (pinned to the bottom; 1px lower) |
| Footer, line 2 | 827 / 834, 71 above | 822 / 830, 70 above | fixed (pinned to the bottom; 1px lower) |
| Footer, line 3 | none | 838 / 846 | intended (B2) |
| Overline "Banking" | 14 / 23, x 228-270 | 14 / 23, x 227-269 | fixed |
| Title "Graph" | 32 / 55, x 227-312 | 31 / 54, x 227-312 | fixed (−1) |
| Card left / top / right | 226 / 71 / 1579 | 226 / 71 / 1577 | fixed (right edge −2, see B10) |

**CSS values that produce this** (build 01's block of `workspace-polish.css` and its tokens; the canvas token is at line 197 of that file):

*Sidebar (1100px and wider)*
- Width 200px. The body rail is painted to 200px, and main and footer have a 200px left margin.
- Background `#f3efea` (`--sidebar-bg`) and border `#e4e0db` (`--sidebar-line`), both sampled from the board.
- Padding 20px 10px 50px 16px. The 20px top is the board value (B6). Children inset 8px from 16px.

*Page canvas (every width)*
- `#f7f3ee` (`--analysis-paper`), sampled from the board (B7). It paints `.workspace` and the body, beside and under the sidebar rail.

*Sidebar text*

| Element | Font (fallback face) | Spacing | Colour |
|---|---|---|---|
| Wordmark | 500 22px/26px | tracking .06em | plum |
| Tagline | 12.5px/16px | 4px below the wordmark | `#6c6d6e` |
| Group labels | 700 8.5px/11px, uppercase | tracking 1px; 20px above, 4px below | `#7e7c7b` |
| Nav items | 13px/16px on 25.5px rows | — | `#2f3236` |
| Footer | 11px/16px | — | `#7e7c7b` |

*Active item*
- A 28px `#e9e2f2` fill with a 3px `#2f2452` bar. It is drawn by `::before`, 1.25px beyond the 25.5px row, so the rows themselves never overlap: `test_console_browser.cjs` asserts that.
- Text `#2f273f`, weight 600.

*Header*
- Workspace padding 11px 22px 40px 26px.
- Overline 12px/16px `#69696e`.
- Title Georgia 31px/34px `#1d173b`.
- 10px between the header and the first card.

**Spec values replaced by board values** (01_shell.md → build):

| Element | 01_shell.md | Build (board) |
|---|---|---|
| Sidebar width | 208 | 200 |
| Sidebar padding | 28px 20px 20px | 20px 10px 50px 16px (top: B6) |
| Nav items | 15px, 38px rows | 13px, 25.5px rows with a 28px active fill |
| Wordmark | 26px / 600 / .2em | 22px / 500 / .06em |
| Tagline | 14px | 12.5px |
| Group labels | 11px / .16em / #817987, 28px above and 8px below | 8.5px bold / 1px / #7e7c7b, 20px above and 4px below |
| Footer | 12px | 11px |
| Overline | 13px | 12px |
| Title | 40px/44px | 31px/34px |
| Header to first card | 20px | 10px |
| Nav text colour | plum | `#2f3236` |
| Active bar colour | purple | `#2f2452` |
| Active fill | `#ebe4f1` | `#e9e2f2` |
| Tagline and overline colour | `--muted` | `#6c6d6e` / `#69696e` |
| Footer colour | `--muted` | `#7e7c7b` |
| Title colour | plum | `#1d173b` |
| Sidebar border | `--line` | `#e4e0db` |
| Sidebar background | `#f4efea` | `#f3efea` |

## B. Remaining differences

**B1. Fonts. Status: intended (D-050).**
- Articulat CF and Freight Text Pro are not installed on this machine, so the console falls back to Arial and Georgia.
- D-050 bars web fonts at runtime, so nothing was loaded.
- Georgia has no 500 weight, so the title renders at 400. Weight 500 on the wordmark renders Arial Regular. The active item's 600 renders Arial Bold.
- Letterforms differ from the board's geometric sans and Freight-like serif. Arial runs a little wider, so line lengths differ by a few px. For example, footer line 1 is 146px here against 131px on the board.
- Installing the licensed fonts locally would switch the faces without any code change.

**B2. `#build-stamp` keeps "up since". Status: intended.**
- `test_app_lazy_startup_browser.cjs` asserts the stamp text `build … · port … · up since …`.
- At the board's 11px, that text wraps inside the 165px column. So the footer has three lines where M4 has two.
- The footer is pinned to the bottom, so it is compared from the bottom edge. The first two baselines sit 86 and 70px above the bottom of the viewport, where M4's sit 87 and 71px above the bottom of its frame. The third line ends 54px above the bottom.

**B3. `#connection`'s dot. Status: intended.**
- The "●" in "● Local connection" is a text character in `app.js`'s connection status.
- M4 separates the two footer items with "·" and shows no dot. The status text is unchanged. The two items now share one line, as on M4.

**B4. Footer layout. Status: fixed.**
- The sidebar is a grid at 1100px and wider. "Local only" and `#connection` share a row pinned to the bottom, with the stamp beneath. No markup changed.

**B5. Nav rows. Status: fixed within ±2px, except the Evidence group (B15).**
- M4's rows are not evenly spaced: 24px apart in Workspace and 25-26px in Analysis. Its EVIDENCE label also sits 2px further below Cross-reference (42px) than its ANALYSIS label sits below Collection (40px).
- The build uses one 25.5px pitch and one group gap.
- At the 01b re-measure every row lands within 2px of the board, except EVIDENCE and PAC evidence: 3px high at the cap top, 2px at the baseline.

**B6. Graph sidebar `padding-top`. Status: fixed (01b).**
- Ruling (2026-09-22): the 28px Graph pin in `test_workspace_polish_browser.cjs` moves to the board value.
- **Board value, measured on M4 at 1.25x.** The wordmark's cap top is at 24.80 CSS px and its baseline at 40.05 (sub-pixel ink edges, `wordmark_b6.json`).
- The console's wordmark (Arial fallback, 500 22px/26px) sets its baseline 20.0px below the top of its box (20.2px at a 1.25 device scale), and its cap top 4.0-4.2px below.
- So the box top that lands the wordmark on M4's is 19.9px by the baseline, 20.6px by the cap top and 20.2px by the middle of the capitals: **20px**. The fallback's capitals are 0.7px taller than the board's, so the two edges cannot both match.
- Build 01's "19px from the top" came from the squeezed board image (B15).
- **CSS.** `.app-navigation` padding is now `20px 10px 50px 16px` (it was 28px at the top). The wordmark's `margin-top:-9px` nudge and its comment are gone: the sidebar top is plain padding.
- The wordmark's box now starts at 20px instead of 19px. The tagline, labels and items moved down 1px with it. The footer is pinned to the bottom and did not move.
- **Checked on all 21 captures:** computed `padding-top` 20px and the wordmark's box top at 20px on every view. At 1600x900 the wordmark's ink is 24 / 40 at a 1x device scale, and 24.01 / 39.99 at 1.25x, against M4's 24.80 / 40.05.
- **Test, line 83, the one assertion changed.** It still runs only on Graph at 1100px and wider (1168px in the suite). Nothing else in the test changed.

Before:

```js
if(width>=1100)assert.equal(shell.navigationPadding.split(' ')[0],'28px',`Graph keeps its user-restored desktop navigation rhythm at ${width}px`);
```

After:

```js
if(width>=1100)assert.equal(shell.navigationPadding.split(' ')[0],'20px',`Graph's desktop sidebar keeps board M4's 20px top padding at ${width}px`);
```

**B7. Page background. Status: fixed (01b).**
- Ruling (2026-09-22): the page background moves to the board's canvas colour.
- **Board sample (`canvas_samples.json`).** 16,844 points on M4, in six canvas regions:
  - beside the title;
  - the gutter between the sidebar and the cards;
  - the right margin;
  - below the last card;
  - two gaps between cards.
- A point counts only if its 5x5 neighbourhood is flat, so text and edges drop out.
- Median: **(247,243,238), `#f7f3ee`**. The regions beside the title, in the gutter and below the last card have exactly that median. The right margin and the two narrow gaps between cards are within one level per channel (`#f7f4ee`, `#f8f4ef`, `#f6f3ef`). The 10th-90th percentiles sit within 2 levels.
- Cross-checks: G1 gives `#f6f4f0` (14,207 points) and S1 gives `#f6f4f0` (7,697 points). Both are 1-2 levels from M4 (red −1, green +1, blue +2). M4 is build 01's binding board, so its median is used.
- The same method on M4's blank sidebar gives `#f3efea`, which is build 01's `--sidebar-bg`.
- **Source.** The canvas was `--analysis-paper:#FAF8F6`, defined at `workspace-polish.css` line 197. That token paints `.workspace` (line 198) and the body's base colour under the sidebar rail (build 01's block). It is now `#F7F3EE`, changed in place.
- **One rule added to build 01's block:** `body[data-view]{background-color:var(--analysis-paper)}`.
  - Below 1100px the body took `workspace.css` line 2's literal `body{background:#faf8f6}`. Without the rule, a short view would show a `#faf8f6` strip under the workspace and behind the footer (Collection at 900px, for example).
  - The narrow top bar already uses the token (`workspace.css` line 5), so it matches the page.
- **Unchanged.** The sidebar keeps `--sidebar-bg` `#f3efea`. The root element's `--acu-paper` (`#fcf7f4`) never shows, because the body is at least as tall as the viewport on every view (900.5 on 900, 1080.5 on 1080).
- **Checked on all 21 captures (`measurements.json`, `pixcheck.json`).**
  - The computed background of body and `.workspace` is rgb(247,243,238), and the sidebar's is rgb(243,239,234).
  - At six canvas points per capture, the painting element is `.workspace` or body.
  - Screenshot pixels: every sampled canvas pixel is exactly (247,243,238). The samples cover the gutter between the sidebar and the content (x 204-221), the strip above the title and the right margin.
  - The only other values are the soft shadows of the white panels on Graph and Cross-reference, within 15px of a panel edge. They fade from (241,237,233) at the edge to the canvas.
  - Blank sidebar pixels are exactly (243,239,234).

**B8. `#split-view`. Status: intended (01: prompt 02 moves Graph's copy into its scope card).**
- It stays in the header row on Graph and PAC evidence with today's look.
- Its 40px box now overhangs the 34px title row by 3px above and below, so the card still starts at 71.

**B9. Insights page actions. Status: intended (shell alignment).**
- The Export, Sources and Refresh group (`.analysis-page-actions`) moved to top 8px and right 22px. It stays level with the new title row and the new right padding.
- Only its position changed.

**B10. Card right edge. Status: open (minor).**
- The build's right padding is 22px, so cards end at 1577. M4's end at about 1579 in the scope card and about 1575 in the panels.

**B11. View content below the header. Status: intended (prompts 02-08).**
- Scope card, chips, tabs, KPI tiles and panels are other prompts' work and differ from M4 and G1. The exception is E1.
- In the 01b captures, Graph's content shows build 02's work in progress (build 02 was editing Graph at the time). Insights and Cross-reference may show builds 04 and 05's.

**B12. Narrow widths (below 1100px). Status: intended.**
- The sidebar turns into the existing top bar there. `workspace.css` line 105 (`.brand-caption,.nav-group{display:none}`) sits inside `@media(max-width:1099px)`, lines 103-112, the narrow top-bar breakpoint, and **stays**.
- The boards show desktop only. The 900px and 390px layouts pass the polish suite.
- Since 01b the page canvas is `#f7f3ee` at these widths too (B7).

**B13. Focus and hover. Status: fixed (spec).**
- Focus: a 2px `--acu-purple` outline with a 2px offset. Before, the sidebar's focus ring was 3px gold (`acu-theme.css`, `header :focus-visible`).
- Hover: `rgba(214,200,226,.35)` on the same 28px shape as the active fill.
- The static boards show neither state.

**B14. Icons and second highlight. Status: intended (Don't-copy).** No icons, as on M4 and boards 3 and 6. Exactly one active item.

**B15. Board rows re-measured at 1.25x on both axes (01b). Status: open for the Evidence group; the rest fixed.**
- Build 01's ink routine (`ink.py`) squeezed M4's 1131 rows into 900. The README's 1 CSS px = 1.25 board px holds on both axes.
- With the board scaled correctly, table A's board rows moved down: 0-1px above y 200, 1-2px down to y 350, and 4-5px in the footer. The footer's shift is the board's taller frame (905 CSS px), so the footer still matches from the bottom edge.
- After B6's 1px, every sidebar row lands within 2px of M4, except the EVIDENCE label and the PAC evidence item. Those two sit 3px high at the cap top and 2px at the baseline.
- M4 leaves 42px from Cross-reference to EVIDENCE but 40px from Collection to ANALYSIS. The build uses one group gap (40px).
- Matching it needs a margin on that one group, a nudge outside B6 and B7, so 01b left it. **Paul to rule** whether to add it.

## C. Primitives and gold

**C1. `.primary` keeps today's look everywhere. Status: fixed (orchestrator ruling).**
- It is plum on its five buttons: `#review-roster`, `#start`, `#evidence-add`, `#evidence-collect` and `#insights-refresh`.
- `.primary--gold` is new: gold background, plum text, 40px, 8px radius, 600 14px. It works on any button, at most one per screen. Build 02 will put it on `#graph-open-builder`.
- Specimen: `.primary--gold` is `rgb(236,169,28)`. A plain `.primary` inside a card stays `rgb(52,38,73)`.

**C2. `.secondary`. Status: intended.** The new look (white, 1px `var(--line)`, 8px radius, 40px) applies only inside `.card` or `.page-actions`, until each view's prompt moves its buttons.

**C3. Primitive geometry. Status: open, for prompt 02.**
- The primitives follow 01_shell.md's geometry. In the 1600 frame, M4 measures the Industry chip at about 40px tall (spec 48) and its buttons at about 33-34px (spec 40), and G1's pills at about 18px (spec 24).
- Nothing visible in 01 uses the primitives. Prompt 02 should size them to its boards.
- `--card-border` is set to M4's scope-card border, `#e8e6e5`.

**C4. One-gold audit.**
- Method: a DOM census of visible elements whose computed background is `#eca91c` or `#f2bb4b`, before and after the build, on live data.
- **Before and after (identical):**
  - Graph: 1 (`#graph-open-builder`).
  - Chart Studio: up to 2 (the pressed `#studio-sort-desc` toggle and `#studio-showme-toggle`). Which appear depends on load timing.
  - Loading, Collection, Insights, Cross-reference and PAC evidence: 0.
- **Re-run in 01b** on all 21 captures: identical (the hidden `#stale-banner` aside).
- **Fixed by 01:** the shell's only gold, the sidebar's gold keyboard-focus ring (now purple). The shell has no gold fill.
- **Later prompts:**
  - **03:** Chart Studio. Every pressed toolbar toggle turns gold, as do `.studio-overview-card.is-focused button` and the briefing deck buttons.
  - **06:** approved board 3's gold selected segments (Summary | Map | Rows inside the PAC panes; "Summary" and "Raised" on the board, up to four golds) are **allowed by ruling**. Paul ruled approved board 3 binding on 2026-09-19, and the 00_README Colour rule excepts these segments from the one-gold rule. `.segmented` stays plum-selected everywhere else. Status: intended (ruling).
  - **02:** "Open in Chart Studio" stays the single gold.
- **Transient golds:** the `.stale-banner` whenever a console runs an older build than the one on disk, and Collection's `#progress` bar during a run. Paul's 8806 will show the banner until he restarts it, and so did 01b's 8812 while other builders were editing.

## D. Scope deviations for Paul

**D1. Chart Studio toolbar rule. Status: intended (build-01 ruling, 2026-09-22). It stays until prompt 03 replaces Chart Studio's toolbar.**
- The rule: `@media(min-width:761px){#view-chart-studio .studio-toolbar{justify-content:flex-end}}`.
- **Why:** the new chrome still leaves Chart Studio narrower than before, so at 1440 its toolbar wraps "Views" to the far left. The right-anchored Views menu then opens outside `.studio{overflow:hidden}` and is clipped, and "Save view" cannot be clicked. `test_navigation_scope_browser.cjs` step 8 failed this way in the first pass.
- With the rule, the navigation suite passes 13/13 and the hit test lands on `#studio-save-view` at 1440, 1366, 1280 and 1920.
- **Visible effect:** the wrapped toolbar row is right-aligned.
- Prompt 03 owns this toolbar.
- Pre-existing and not caused by 01: at 1100px, "Save view" sits under the Inspector title.

**D2. Insights page-actions offset.** See B9.

## E. Files and line endings

**Build 01b** changed two files:
- **`mentat/app/workspace-polish.css`**: +8 / −5 lines in a line diff (387 → 390 lines), 34,744 → 34,885 bytes.
  - Line 197 (CRLF) changed in place: `--analysis-paper:#FAF8F6` → `#F7F3EE` (B7).
  - In build 01's block (LF):
    - four lines added: a two-line comment, the body rule and a blank line (B7);
    - the `.app-navigation` padding changed in place, 28px → 20px (B6);
    - the two-line nudge comment and the wordmark's `margin:-9px 0 0` became a one-line comment and `margin:0` (B6).
  - Line endings kept: 225 CRLF (unchanged) and 165 LF-only (was 162).
- **`mentat/tests/test_workspace_polish_browser.cjs`**: +1 / −1 (line 83, LF), 16,612 → 16,614 bytes. Still 140 CRLF and 32 LF-only.
- Every other byte of both files is identical to its pre-edit copy (line diff against the copies saved before the write). Both were written at 10:47:15 on 2026-09-22, after a SHA-256 check just before the write.
- `mentat/app/acu-theme.css` is unchanged by 01b.

**Build 01** changed two files:
- **`mentat/app/acu-theme.css`**: +15 lines, 5,204 → 5,888 bytes. Tokens added: `--sidebar-bg`, `--sidebar-line`, `--card-border`, `--card-radius`, `--card-shadow`, `--scope-1`, `--scope-2`, `--scope-3`, `--tint-shared`, `--base-muted` and `--base-line`. Stayed all-CRLF: 91 → 106 CRLF lines, 0 LF-only.
- **`mentat/app/workspace-polish.css`**: +118 / −2 lines, 21,877 → 34,744 bytes. The 2026-09-21 hiding hunk (old lines 7-8, CRLF) was removed, and the build-01 block was appended. The file was already mixed (227 CRLF + 44 LF-only). The new block is LF like the tail; afterwards 225 CRLF + 162 LF-only. Every line before the block is byte-identical to the pre-edit file, checked before each write.

Unchanged:
- `templates/page_shell.html` and `index.html` are untouched by 01 and 01b. No new static file was created.
- `measurements.json`, `measurements_before.json`, `specimen.json`, `canvas_samples.json`, `pixcheck.json` and `wordmark_b6.json` are git-ignored by the root `*.json` rule.

## F. Measured checks (`measurements.json`: 7 views x 1440x900, 1600x900, 1920x1080; 01b capture)

| Check | Result |
|---|---|
| Sidebar width | 200px on all 21 captures |
| Sidebar `padding-top` | 20px on all 21; wordmark box top 20px (B6) |
| Page background | body and `.workspace` rgb(247,243,238) on all 21; sidebar rgb(243,239,234) (B7) |
| Elements with the active style | exactly 1 on all 21 |
| Items with `aria-selected=true` | 1 |
| Tagline and 3 group labels | visible on all 21 |
| Gap from header to first element | 10px on all 21 |
| Horizontal overflow | none (`scrollWidth` = viewport) |
| Title | 31px/34px serif; y 11, or 27 on Graph below the overline |
| Full document height | the body runs the full document height on every capture: Graph at 1440, body 1702.7 = document 1703 |
| Nav column itself | fixed and viewport-high (900 / 1080), so it never scrolls away |

Full-page captures: `before_1440x900_cross-reference_full.png` (before build 01) and `after_1440x900_cross-reference_full.png` (01b). Cross-reference's content has changed since build 01 (build 05's work), so the two differ below the header too.

## G. Suites

| Suite | Unmodified bytes (01b baseline) | Final bytes |
|---|---|---|
| `render_console.py --check` | pass | pass right after the edit; fails at the end, on other builders' templates (below) |
| `test_console_templates.py` | 10 passed | 10 passed right after the edit; 8 passed, 2 failed at the end, same cause |
| `test_workspace_polish_browser.cjs` | pass | pass (asserts 20px, B6) |
| `test_console_browser.cjs` | pass | red in Graph areas, attributed to load and to build 02's work in progress (below) |
| `test_navigation_scope_browser.cjs` | 13/13 | 13/13 |

- The 01b baseline ran on build 01's final bytes, 10:33-10:38. The final run was 10:49-10:52, after the 10:47:15 write, with reruns and probes until 11:37.
- The polish suite ran with `MENTAT_UI_OUTPUT` pointed at the scratchpad.
- **`render_console.py --check` and `test_console_templates.py` at the end (11:37).** Both fail because `index.html` no longer matches the templates. `view_graph.html` (build 02, 11:18) and `view_cross_reference.html` (build 05, 11:12) changed after `index.html` was last rendered (01:21). 01b changed no template and did not run `--write`, which would have baked their work in progress into the golden.
- **`test_console_browser.cjs`, not fixed (Graph is build 02's):**
  - Line 296: `waitForFunction` for `#graph-candidates` to include `$777.00` after `#graph-mode` is set to `activity`, under a 15s timeout. It timed out in the final run and again in the one rerun.
  - A direct query of that page state ran on the same fixture (`graph_state_probe.cjs`). It ran once with the 01b stylesheets and once with the pre-01b stylesheets served in their place. The state is reached both times (`$777.00` present, same request URL). The `mode=activity` `/api/graph` call took 4.4s and 18.6s. Verdict: a possible load timeout.
  - Later whole-suite runs failed elsewhere in Graph or on load:
    - line 52, `page.goto` timeout (01b stylesheets);
    - line 363, a null chart-label box at 390px (pre-01b stylesheets). The direct query found the box present immediately (height 20) with both.
  - The last run, at 11:33, failed at line 164: the page scrolls sideways at 390px after the Graph | PAC evidence split (`scrollWidth` 425). A direct query (`overflow_probe.cjs`) finds the same 425px with the pre-01b stylesheets. The elements past the edge are `label.chip-select` (right edge 425) and `#graph-funding` (424), inside `#view-graph`. That is build 02's new scope markup, `view_graph.html`, written at 11:18.
  - Build 02 also wrote `graph_data.py` at 10:49:27, between the green baseline and the first red run. Four builders were running Chrome and servers on this machine.
  - A change to the page colour and the sidebar's top padding does not alter the Graph API's answers, its timing, or layout below 1100px apart from the body colour.

## H. Proof files

- `01_<view>_<1440x900|1600x900|1920x1080>.png`: 21 side-by-sides, all regenerated in 01b, so none shows the old canvas.
  - Left: M4's left 720 CSS px, sidebar and header, in the 1600 frame at 1.25x on both axes.
  - Right: the build's left 720px at 1 px = 1 CSS px.
  - Graph, Insights and Cross-reference images carry a caption: their content below the header may be the work in progress of build 02, 04 or 05.
- `01_graph_1600x900_full-frame.png`: the whole M4 beside the whole build. M4 shows its top 900 CSS rows scaled by exactly 1/1.25; build 01's copy squeezed all 1131 rows into 900.
- `before_1440x900_cross-reference_full.png` (before build 01) and `after_1440x900_cross-reference_full.png` (01b): full-page captures.
- `specimen_primitives.png` and `specimen_primitives_focus.png`, with `specimen.json` (build 01; 01b changed no primitive).
- `measurements.json` (01b) and `measurements_before.json` (before build 01).
- 01b evidence: `canvas_samples.json` (B7, board), `pixcheck.json` (B7, build pixels) and `wordmark_b6.json` (B6).
- `superseded-before-01b\`: the 22 images, `measurements.json`, `after_1440x900_cross-reference_full.png` and this file as they stood before 01b.
- `superseded-208px-build\`: the first pass's scale-reference images.
