# Mentat console redesign: build packet (2026-09-22)

Paul approved this set on 2026-09-22 ("Go") after two rounds of boards:

- Round 1 review page: https://claude.ai/artifact/FFSK1XiZQ2wBkgjhCQtkXP
- Round 2 review page: https://claude.ai/artifact/5d2woUWVQUAagBgYzygf5R

Brief: ease of use, flexibility in what is compared, little clutter. Every screen must end up a one-to-one replica of its board(s). Amounts and names in the boards are illustrative; layout, chrome, type, colour, spacing, wording and behaviour are binding.

Packet root: `C:\Users\pgoff\Mentat\outputs\ui-redesign-boards-20260922\` (boards in `boards\`, today's screens in `current\`, prompts in `prompts\`, your proof goes in `proof\`).

## Build order

Run the prompts one at a time, in this order, in `C:\Users\pgoff\Mentat` (branch `codex/mentat-crypto`). Paul reviews each build's side-by-side proof before the next one starts.

| # | Prompt | Binding boards (in `boards\`) |
|---|---|---|
| 01 | `01_shell.md`: sidebar, page header, scope bar, compare pills, shared tokens | `M4_graph_default`, `G1_compare_industry` |
| 02 | `02_graph.md`: default view and five compare modes | `M4_graph_default`, `G1`–`G5`, `approved_board1_graph_rows`, `approved_board5_downstream_drawer` |
| 03 | `03_chart_studio.md` | `S1_chart_studio` |
| 04 | `04_insights.md` | `I1_insights` |
| 05 | `05_cross_reference.md` | `B16_cross_reference` |
| 06 | `06_pac_evidence.md`: panes and enlarged-map compare | `B19_pac_evidence_panes`, `M13_pac_map_compare`, `approved_board3_pac_panes`, `approved_board6_map_enlarged`, `approved_board7_map_zoomed` |
| 07 | `07_loading.md`: four-step flow and coverage grid | `B20_loading_step1_typing`, `L1`–`L4` |
| 08 | `08_collection.md` | `B22_collection_run_card` |

01 goes first because every later prompt uses its sidebar, header and scope-bar component. Builders may run in parallel only when their file sets are disjoint (Paul, 2026-09-22: "Proceed in the most optimal manner"). 03 waits for 02 (it reuses 02's compare menu); 07 and 08 wait for 02 (all three edit `app.js`), and 08 waits for 07. `acu-theme.css`, `workspace-polish.css`, `page_shell.html` and `page_head.html` have one writer (the build-01 session); ask it for changes there instead of editing them. The golden `mentat/app/index.html` is written only by `render_console.py --write`: run `--write` right before your final suite run and `--check` at the end, and expect other builders to re-render it. If a browser suite fails in a view another builder is changing, rerun it once, then report it rather than fix it. Each builder uses its own read-only port (8812 build 01, 8813 build 02, 8814 build 04, 8815 build 05, 8816 build 06, 8817 build 03, 8818 build 07, 8819 build 08).

Files named `src_*` are the boards a merge was made from (context only). Files named `approved_board*` are the 2026-09-19 boards Paul ruled binding; the new boards extend them and never override them silently. `current\today_*` are read-only captures of the live console (port 8806, 2026-09-21) for before/after comparison; the live tree may have moved since.

## The ten design calls Paul approved with "Go"

1. Compare lives inside the chip being compared: the Industry, Cycle or Company chip holds two or three coloured pills; "+ Compare with..." chooses which. The scope bar and the headline figures never move between the default view and comparing.
2. The graphs stay one-to-one with M4: same rows and colours, split into halves under coloured pills. Change chips appear only when comparing cycles, in plum, so they cannot be read as party colours.
3. Comparing companies highlights the two companies inside the whole Company comparison card instead of splitting it.
4. Three or more scopes stack the cards full width, with a Grid | Stacked switch.
5. "Same point" for cycles needs data work: Graph data is by full cycle today; Insights already computes a same-election-stage figure that could feed it.
6. Drill-down tabs (Recipients, Candidates, Companies) become sortable tables when comparing, with "Funded by both" and "Only ..." filters.
7. Loading turns name conflicts into decisions with buttons (today it prints the server's raw JSON); Choose cycles stays disabled until they are settled.
8. Saved FEC coverage becomes a sector x cycle grid.
9. One sidebar everywhere: M4's tagline and pale lilac active item (as in approved boards 3 and 6).
10. Insights keeps teal-up, red-down for changes (no party dots on that page); Graph keeps plum change chips.

## Rules for every build

**Settled decisions (project brain; do not reopen):**
- D-039: the URL fragment names the tab and the query string carries the scope with the Graph API's key names (`industry`, `company`, `cycle`, `mode`, `direction`, `tier`, `funding`, `category`, `recipient`, plus `saved`; see `KEYS` in `mentat/app/scope.js`). New state (compare, layout) is added as more flat query keys, never as JSON in the URL.
- D-040: Cross-reference publishes no totals.
- D-041: Graph's Overview shows its four analyses at once in one shared panel chrome, each panel owning its row limit; Chart Studio keeps its chrome above the chart within two rows.
- D-050: the console is local-only; no internet map tiles, fonts or scripts at runtime.
- D-061: the Board (Canvas mode) is Chart Studio's only multi-chart surface; no linked filters.
- Ruling C (2026-09-19): Back stays inside the console (in-app Back only).
- Motion (2026-09-19): expressive, and every animation respects `prefers-reduced-motion`.
- Colour: at most one gold (`--acu-gold`) filled button per screen, except the gold selected segments (Summary | Map | Rows) inside PAC panes, which approved board 3 shows and Paul ruled binding on 2026-09-19; party colours only for party (`--party-dem`, `--party-rep`); companies never get party dots.

**Repo mechanics (each line is a past incident):**
- Markup lives in `mentat/app/templates/` (flat folder, unique basenames: `page_shell.html`, `page_head.html`, `view_*.html`). After editing a template, run `python mentat/tools/render_console.py --write` (it writes LF endings) to regenerate the golden `mentat/app/index.html`; `--check` must then pass. Nineteen test files read `index.html` from disk (for example `mentat/tests/test_console_templates.py`, `test_studio_wording.cjs`), so both change together.
- Static files are served only if listed in `STATIC_ASSETS` in `mentat/app/server.py` (around lines 101-169). A new JS/CSS file needs an entry there and a console restart, and 404s on Paul's live console until then. Prefer extending existing files; if a new file is unavoidable, name it in your report and do not restart anything.
- The Mentat root `.gitignore` ignores `*.html`, `*.txt` and `*.json` (templates are un-ignored by a negation). Run `git check-ignore -v` on every new file and report the ignored ones.
- Stylesheets load in this order: `style.css`, `graph.css`, `comparison.css`, `acu-theme.css`, `cross-reference.css`, `workspace.css`, `chart-studio.css`, `chart-briefing.css`, `insights.css`, `workspace-polish.css`. Later files win; put new shared rules where the order makes them win without `!important`.
- Preserve each file's line endings (several JS files are CRLF, `index.html` is written LF by the renderer). Edit hunk-exact; never rewrite a shared file whole; never restore lines another lane deleted.
- If your Write/Edit tool refuses a path under `C:\Users\pgoff\Mentat`, write through a small Python script that reads and writes bytes and keeps the existing line endings.
- Element ids that tests use are contracts. If you must change one, update each test assertion one by one: re-home it, never drop it.
- Python suites run from inside `mentat/tests` (sibling imports). Node unit suites: `node --test` on `mentat/app/tests/*.test.js`. Browser suites: the `*_browser.cjs` files under `mentat/tests`, which use the Playwright install under `%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules` with `chromium.launch({channel: 'chrome'})`.

**Coordination:**
- Before your first edit, run `git -C C:\Users\pgoff\Mentat status --short` and list running `codex.exe`, `node.exe` and `python.exe` processes. If another builder is active, or a file you plan to touch changes during your run, stop and report.
- Never restart, stop or write to Paul's console on port 8806. For screenshots start your own read-only instance, `python mentat/app/server.py --port 8812 --read-only`, and stop it when you finish.
- Do not commit. Paul commits after reviewing your proof.

## Acceptance protocol (every build)

1. Run the suites your files touch before you edit (baseline) and after (result). A red suite is yours only if it is green on the unmodified bytes; say which.
2. Screenshot every state the prompt lists at 1440x900 and 1920x1080 on your 8812 instance. Load each changed asset with `fetch(url, {cache: 'reload'})` before navigating; the browser keeps old JS.
3. Put each screenshot beside its board (one image, board left, build right) in `proof\<prompt-number>\`.
4. Write `proof\<prompt-number>\DIFFERENCES.md`: every visible difference between board and build, named ("title 2 px larger", "legend below the map instead of inside it"), each marked fixed, intended (with the reason: a Don't-copy item, real data, or a settled decision), or open. "Minor differences" is not an entry.
5. Measure overlaps and alignment with `getBoundingClientRect`, never by eye from a screenshot.
6. Report: files changed with line counts, suites before and after, the proof folder, open differences, and anything you stopped on.

## Notes from build 01 (2026-09-22), binding for 02-08

- Board scale: every file in `boards\` is 2000x1131 WebP for a 1600x900 CSS viewport (1 CSS px = 1.25 board px). Measure against that, not the 2688px originals. The scale is the same on both axes, so a board's 1131 rows cover 904.8 CSS px; do not squeeze them into 900 (build 01's first measurements did and drifted by up to 4 px near the footer; build 01b corrected it).
- Gold is opt-in: `.primary` keeps today's plum look everywhere (five buttons use it: #evidence-add, #evidence-collect, #insights-refresh, #review-roster, #start). The gold button is `class="primary primary--gold"`, at most one per screen (build 02 puts it on #graph-open-builder). The new white `.secondary` look applies inside `.card` or `.page-actions` only. Never restyle `.primary` globally.
- The board wins over any number in these prompts. Build 01 measured M4 at 1.25x and built to it: sidebar 200px, nav 13px text on 25.5px rows, a 28px lilac active fill, wordmark 22px, group labels 8.5px bold, footer 11px, overline 12px, page title 31px, card edge at 226px, 10px from header to first card. Board geometry for 02: scope chips are about 40px tall (not 48), buttons about 34px (not 40), scope pills about 18px (not 24). Measure your own board and record each deviation from the prompt in DIFFERENCES.md.
- Build-01 rulings (2026-09-22, made under Paul's "boards are binding" and "proceed in the most optimal manner"): B6, the 28px Graph sidebar-padding pin in `test_workspace_polish_browser.cjs` moves to the board value (20px, measured by build 01b); B7, the page background moves to the board's canvas colour (`#f7f3ee`, set through `--analysis-paper` in `workspace-polish.css`); D1, the interim Chart Studio toolbar rule stays until prompt 03 replaces it; approved board 3's gold selected segments stay (see the Colour rule).
- Shared tokens and primitives from build 01 live in `acu-theme.css` (`--sidebar-bg`, `--card-*`, `--scope-1/2/3`, `--tint-shared`, `--base-muted`, `--base-line`) and at the end of `workspace-polish.css` (`.card`, `.card-stack`, `.card-title`, `.page-overline`, `.page-actions`, `.chip-select`, `.chip-add`, `.scope-pill`, `.change-chip`, `.new-tag`, `.segmented`, `.icon-button`). Use them; do not add parallel versions.
- Fonts: the boards draw Freight Text and Articulat. The console asks for `Freight Text Pro` and `Articulat CF` with Georgia and Arial fallbacks, and D-050 forbids loading web fonts; if they are not installed on this machine, the fallback is the expected result, not a difference to fix.
