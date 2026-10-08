# Build 01 (console shell): differences from the boards

Corrected build, 2026-09-22.

- Nothing was committed. Paul's console on port 8806 was not touched.
- The orchestrator ruled that, where 01_shell.md's numbers disagree with the board, the board wins (00_README: "one-to-one replica"). This build follows that ruling. The first pass (a 208px sidebar at the 01 spec's sizes) is superseded; its two scale-reference images are kept in `superseded-208px-build\`.

**Frame used.** `M4_graph_default.webp` and `G1_compare_industry.webp` are 2000x1131: a 1600x900 CSS frame at **1.25x**, not the "about 1.7x" the prompt text gives. Boards 3 and 6 are 2688x1520 (1.68x). Every board number below is in that 1600x900 frame.

**How it was measured.**
- The build was captured on a read-only console on port 8812 at 1440x900, **1600x900** (the board's own frame) and 1920x1080.
- `01_graph_1600x900_full-frame.png` puts the whole M4 beside the whole build, pixel for pixel.
- Positions come from one ink-measuring routine run on both the board and the build: cap top, baseline and left/right ink.
- Layout numbers come from `getBoundingClientRect` (`measurements.json`).

**Status key.** **fixed**: the build now matches the board. **intended**: the difference is deliberate, and the reason is given. **open**: Paul needs to rule.

---

## A. Board versus build, sidebar and header (Graph at 1600x900)

Values are ink top / baseline, in CSS px.

| Element | M4 board | Build | Status |
|---|---|---|---|
| Sidebar border x | 200 | 199 (sidebar width 200px per the ruling, border inside it) | fixed (1px left of the board's) |
| Sidebar background | (243,239,234) | (243,239,234) | fixed |
| Wordmark MENTAT | 24 / 40, x 25-120 | 23 / 39, x 25-118 | fixed |
| Tagline | 52 / 61, x 25-145 | 51 / 61, x 25-146 | fixed |
| WORKSPACE | 89 / 95 | 87 / 94 | fixed (−1.5, see B5) |
| Loading | 108 / 118 | 108 / 118 | fixed |
| Collection | 133 / 142 | 133 / 143 | fixed |
| ANALYSIS | 172 / 178 | 173 / 180 | fixed (+1.5, see B5) |
| Active fill (Graph) | y 184-212 (28 tall), x ≈15.5-189 | y 186-214 (28 tall), x 16-189 | fixed (+2, see B5) |
| Chart Studio | 220 / 229 | 219 / 229 | fixed |
| Insights | 245 / 255 | 245 / 255 | fixed |
| Cross-reference | 270 / 280 | 270 / 280 | fixed |
| EVIDENCE | 312 / 318 | 310 / 317 | fixed (−1.5, see B5) |
| PAC evidence | 333 / 342 | 331 / 341 | fixed (−1.5, see B5) |
| Footer, line 1 | 806 / 814 | 806 / 814 | fixed |
| Footer, line 2 | 822 / 830 | 822 / 830 | fixed |
| Footer, line 3 | none | 838 / 846 | intended (B2) |
| Overline "Banking" | 14 / 23, x 228-270 | 14 / 23, x 227-269 | fixed |
| Title "Graph" | 32 / 55, x 227-312 | 31 / 54, x 227-312 | fixed |
| Card left / top / right | 226 / 71 / 1579 | 226 / 71 / 1577 | fixed (right edge −2, see B10) |

**CSS values that produce this** (all in build 01's block of `workspace-polish.css` and its tokens):

*Sidebar (1100px and wider)*
- Width 200px. The body rail is painted to 200px, and main and footer have a 200px left margin.
- Background `#f3efea` (`--sidebar-bg`) and border `#e4e0db` (`--sidebar-line`), both sampled from the board.
- Children inset 8px from 16px; right padding 10px.

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
- The first two lines sit exactly on M4's (806 and 822). The third ends 54px above the bottom of the frame, where M4's last line ends 70px above.

**B3. `#connection`'s dot. Status: intended.**
- The "●" in "● Local connection" is a text character in `app.js`'s connection status.
- M4 separates the two footer items with "·" and shows no dot. The status text is unchanged. The two items now share one line, as on M4.

**B4. Footer layout. Status: fixed.**
- The sidebar is a grid at 1100px and wider. "Local only" and `#connection` share a row pinned to the bottom, with the stamp beneath. No markup changed.

**B5. Nav rows. Status: fixed, within ±2px.**
- M4's rows are not evenly spaced: 24px apart in Workspace, 25-26px in Analysis.
- The build uses one 25.5px pitch. Every row lands within 2px of the board.

**B6. Graph sidebar `padding-top`. Status: open.**
- `test_workspace_polish_browser.cjs` pins Graph's sidebar `padding-top` at 28px ("Graph keeps its user-restored desktop navigation rhythm"). That pin encodes the Graph rollback, which call 9 supersedes. Build 01 was not cleared to edit that test.
- So the padding stays 28px, and the wordmark carries `margin-top:-9px` to sit where M4 has it (19px from the top).
- **Paul to rule:** retire or re-pin that test. The CSS would then become a plain 19px `padding-top`.

**B7. Page background. Status: open.**
- M4 samples about `#f7f3ed`; the build keeps `--analysis-paper` `#faf8f6`.
- This is a canvas change on every view, outside the shell tokens, so it was left for a ruling. It is one line to change.

**B8. `#split-view`. Status: intended (01: prompt 02 moves Graph's copy into its scope card).**
- It stays in the header row on Graph and PAC evidence with today's look.
- Its 40px box now overhangs the 34px title row by 3px above and below, so the card still starts at 71.

**B9. Insights page actions. Status: intended (shell alignment).**
- The Export, Sources and Refresh group (`.analysis-page-actions`) moved to top 8px and right 22px. It stays level with the new title row and the new right padding.
- Only its position changed.

**B10. Card right edge. Status: open (minor).**
- The build's right padding is 22px, so cards end at 1577. M4's end at about 1579 in the scope card and about 1575 in the panels.

**B11. View content below the header. Status: intended (prompts 02-08).**
- Scope card, chips, tabs, KPI tiles and panels are unchanged, and differ from M4 and G1. The exception is E1.

**B12. Narrow widths (below 1100px). Status: intended.**
- The sidebar turns into the existing top bar there. `workspace.css` line 105 (`.brand-caption,.nav-group{display:none}`) sits inside `@media(max-width:1099px)`, lines 103-112, the narrow top-bar breakpoint, and **stays**.
- The boards show desktop only. The 900px and 390px layouts pass the polish suite.

**B13. Focus and hover. Status: fixed (spec).**
- Focus: a 2px `--acu-purple` outline with a 2px offset. Before, the sidebar's focus ring was 3px gold (`acu-theme.css`, `header :focus-visible`).
- Hover: `rgba(214,200,226,.35)` on the same 28px shape as the active fill.
- The static boards show neither state.

**B14. Icons and second highlight. Status: intended (Don't-copy).** No icons, as on M4 and boards 3 and 6. Exactly one active item.

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
- **Fixed by 01:** the shell's only gold, the sidebar's gold keyboard-focus ring (now purple). The shell has no gold fill.
- **Later prompts:**
  - **03:** Chart Studio. Every pressed toolbar toggle turns gold, as do `.studio-overview-card.is-focused button` and the briefing deck buttons.
  - **06:** approved board 3 shows gold selected segments ("Summary" and "Raised") in each pane, up to four golds. That conflicts with the one-gold rule and with the plum-selected `.segmented`, and needs a ruling.
  - **02:** "Open in Chart Studio" stays the single gold.
- **Transient golds:** the `.stale-banner` whenever a console runs an older build than the one on disk (Paul's 8806 will show it until he restarts it), and Collection's `#progress` bar during a run.

## D. Scope deviations for Paul

**D1. Chart Studio toolbar rule. Status: open.**
- The rule: `@media(min-width:761px){#view-chart-studio .studio-toolbar{justify-content:flex-end}}`.
- **Why:** the new chrome still leaves Chart Studio narrower than before, so at 1440 its toolbar wraps "Views" to the far left. The right-anchored Views menu then opens outside `.studio{overflow:hidden}` and is clipped, and "Save view" cannot be clicked. `test_navigation_scope_browser.cjs` step 8 failed this way in the first pass.
- With the rule, the navigation suite passes 13/13 and the hit test lands on `#studio-save-view` at 1440, 1366, 1280 and 1920.
- **Visible effect:** the wrapped toolbar row is right-aligned.
- Prompt 03 owns this toolbar.
- Pre-existing and not caused by 01: at 1100px, "Save view" sits under the Inspector title.

**D2. Insights page-actions offset.** See B9.

## E. Files and line endings

Two files changed:
- **`mentat/app/acu-theme.css`**: +15 lines, 5,204 → 5,888 bytes. Tokens added: `--sidebar-bg`, `--sidebar-line`, `--card-border`, `--card-radius`, `--card-shadow`, `--scope-1`, `--scope-2`, `--scope-3`, `--tint-shared`, `--base-muted` and `--base-line`. Stayed all-CRLF: 91 → 106 CRLF lines, 0 LF-only.
- **`mentat/app/workspace-polish.css`**: +118 / −2 lines, 21,877 → 34,744 bytes. The 2026-09-21 hiding hunk (old lines 7-8, CRLF) was removed, and the build-01 block was appended. The file was already mixed (227 CRLF + 44 LF-only). The new block is LF like the tail; afterwards 225 CRLF + 162 LF-only. Every line before the block is byte-identical to the pre-edit file, checked before each write.

Unchanged:
- `templates/page_shell.html` and `index.html` are byte-identical to preflight. `render_console.py --check` passes.
- No test file changed, and no new static file was created.
- `measurements.json`, `measurements_before.json` and `specimen.json` are git-ignored by the root `*.json` rule.

## F. Measured checks (`measurements.json`: 7 views x 1440x900, 1600x900, 1920x1080)

| Check | Result |
|---|---|
| Sidebar width | 200px on all 21 captures |
| Elements with the active style | exactly 1 on all 21 |
| Items with `aria-selected=true` | 1 |
| Tagline and 3 group labels | visible on all 21 |
| Gap from header to first element | 10px on all 21 |
| Horizontal overflow | none (`scrollWidth` = viewport) |
| Title | 31px/34px serif; y 11, or 27 on Graph below the overline |
| Full document height | on Cross-reference (document 1910px) the body rail runs the full height: body 1910.1 = document 1910 |
| Nav column itself | fixed and viewport-high (900 / 1080), so it never scrolls away |

Full-page before and after captures: `before_/after_1440x900_cross-reference_full.png`.

## G. Suites

| Suite | Unmodified bytes | Final bytes |
|---|---|---|
| `render_console.py --check` | pass | pass |
| `test_console_templates.py` | 10 passed | 10 passed |
| `test_workspace_polish_browser.cjs` | pass | pass |
| `test_console_browser.cjs` | pass | pass |
| `test_navigation_scope_browser.cjs` | 13/13 | 13/13 |

- The polish suite ran with `MENTAT_UI_OUTPUT` pointed at the scratchpad.
- No red was pre-existing.
- The first pass had two reds, both caused by 01 and fixed in 01: a nav transition, and E1's clipped menu (D1).

## H. Proof files

- `01_<view>_<1440x900|1600x900|1920x1080>.png`: 21 side-by-sides. Left: M4's left 720 CSS px, sidebar and header, in the 1600 frame. Right: the build's left 720 px at 1 px = 1 CSS px.
- `01_graph_1600x900_full-frame.png`: the whole board beside the whole build.
- `before_/after_1440x900_cross-reference_full.png`: full-page captures.
- `specimen_primitives.png` and `specimen_primitives_focus.png`, with `specimen.json`.
- `measurements.json` (final) and `measurements_before.json` (before the build).
