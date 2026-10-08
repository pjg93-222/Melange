# Build prompt 01 · Console shell: sidebar, page header, shared components

**Builder:** one Opus architect or Codex agent, alone in the tree. **Read first:** `prompts\00_README.md`; its rules and acceptance protocol are part of this prompt.

## Visual spec (binding)

Open and study these before touching code (packet root `C:\Users\pgoff\Mentat\outputs\ui-redesign-boards-20260922\`):

- `boards\M4_graph_default.webp`: the sidebar, the page header (overline + serif title), the white scope card, chip selects, buttons and card chrome.
- `boards\G1_compare_industry.webp`: coloured scope pills inside a chip, and "Clear comparison".
- `boards\approved_board3_pac_panes.webp` and `boards\approved_board6_map_enlarged.webp`: the same sidebar on other pages (approved 2026-09-19).

Board files are 2000x1131 WebP showing a 1600x900 CSS viewport, so 1 CSS px = 1.25 board px. Amounts and names in them are illustrative.

**Don't copy:** the icons beside sidebar items in G1-G5 (M4 and boards 3/6 have none); any second highlighted nav item; the "port 8800" footer in M10/M13.

## Goal

Make the chrome that every view shares match M4 exactly, and add the shared CSS primitives that prompts 02-08 build on. Do not change any view's content area in this build.

## What exists today (verified 2026-09-22)

- `mentat/app/templates/page_shell.html` line 3: `<header class="app-navigation">` holds `<a class="wordmark">MENTAT</a>`, `<span class="brand-caption">Giving, in perspective.</span>`, a `nav.workspace-tabs` with `span.nav-group` labels (Workspace, Analysis, Evidence) and the tab buttons `#tab-loading`, `#tab-collection`, `#tab-graph`, `#tab-chart-studio`, `#tab-insights`, `#tab-cross-reference`, `#tab-evidence`; then `span.local-indicator` ("Local only") and `#connection`. Line 18: `.workspace-heading` with `h1#workspace-title` and `button#split-view`.
- The tagline and the group labels are in the markup but hidden: `workspace-polish.css` lines 7-8 (`body[data-view] .brand-caption, body[data-view] .nav-group{display:none}`, added by the 2026-09-21 tabs-polish lane) and `workspace.css` line 105 (inside a media query). Paul's approved call 9 (2026-09-22) shows them again; that supersedes the 2026-09-21 hiding. Remove the hiding hunk in `workspace-polish.css` only; keep the `workspace.css` rule if its media query is a narrow-screen breakpoint (check it and say what it is).
- Tokens: `mentat/app/acu-theme.css` `:root` has `--acu-plum #342649`, `--acu-purple #57447b`, `--acu-ivory #f7ede4`, `--acu-paper #fcf7f4`, `--acu-gold #eca91c`, `--acu-teal #327a7a`, `--acu-aqua #9ed4d5`, `--acu-mauve #8b6984`, `--acu-lilac #d6c8e2`, `--acu-taupe #bcaea1`, `--muted #62596e`, `--line #d9d4de`, `--chart-grid #e5e1e8`, `--chart-negative #bf3f36`, `--party-dem #3b6db5`, `--party-rep #b8433a`, `--font-sans` (Articulat CF) and `--font-serif` (Freight Text Pro).
- `workspace-polish.css` loads last, so shared rules placed there win without `!important`.

## Build this

### 1. Sidebar (every view)
- Width 208px, full document height (today it stops at 1,080px on tall views), background `#f4efea` (add `--sidebar-bg`), 1px right border `var(--line)`, padding 28px 20px 20px.
- Wordmark "MENTAT": `--font-sans`, 26px, weight 600, letter-spacing .2em, colour `--acu-plum`. Tagline "Giving, in perspective." 14px `--muted`, 4px below.
- Group labels WORKSPACE, ANALYSIS, EVIDENCE: 11px, weight 600, letter-spacing .16em, uppercase, colour `#817987`, 28px above, 8px below.
- Nav items: text only (no icons), 15px `--acu-plum`, row height 38px, padding 0 12px, radius 8px. Hover: background `rgba(214,200,226,.35)`. Active: background `#ebe4f1`, weight 600, a 3px `--acu-purple` bar on the left edge (inset box-shadow, so the text does not shift). Exactly one item active. Keyboard focus: 2px `--acu-purple` outline, offset 2px.
- Footer pinned to the bottom: "Local only · Local connection" and the build-stamp line ("build 862a6c4 · port 8806") in 12px `--muted`, two lines, as in M4. Reuse `.local-indicator`, `#connection` and the existing build-stamp element; do not invent new status sources.

### 2. Page header (every view)
- Overline (13px `--muted`, for example "Banking" on Graph) above the title; title `h1#workspace-title` in `--font-serif` 40px/44px weight 500 `--acu-plum`; 20px of space below the header before the first card.
- Keep `#split-view` where it is for every view except Graph (prompt 02 moves Graph's copy into its scope card). Do not change its behaviour or labels here.

### 3. Shared primitives (classes in `workspace-polish.css`, tokens in `acu-theme.css`)
Add these so later prompts share one vocabulary. When an existing class already does the same job, reuse it and say which.

- Tokens: `--sidebar-bg:#f4efea; --card-border:#e6e0e9; --card-radius:12px; --card-shadow:0 1px 2px rgba(52,38,73,.04),0 6px 18px rgba(52,38,73,.05); --scope-1:var(--acu-purple); --scope-2:var(--acu-teal); --scope-3:var(--acu-mauve); --tint-shared:rgba(214,200,226,.38);`
- `.card`: white, 1px `--card-border`, radius `--card-radius`, shadow `--card-shadow`, padding 20px 22px; cards sit 16px apart. Card title: `--font-serif` 22px/28px weight 500.
- `.chip-select`: the labelled select from M4's scope bar. White, 1px `#e2dce6`, radius 8px, height 48px, padding 6px 36px 6px 12px, label on top (11px `--muted`), value below (14px `--acu-plum`), chevron at the right. It wraps the real `<select>` and keeps its id and keyboard behaviour.
- `.chip-add`: dashed 1px `#cfc6d8`, radius 8px, height 48px, 14px `--acu-purple`, one line of text such as "+ Compare with..." (the menu is built in 02).
- `.scope-pill` with `--1`/`--2`/`--3` modifiers: height 24px, padding 0 12px, radius 999px, 13px weight 600, white text on `--scope-1`/`--scope-2`/`--scope-3`; an optional remove "×" inside (shown on hover and focus, accessible name "Remove <label>").
- `.change-chip`: 12px weight 600, colour `--acu-purple`, background `rgba(87,68,123,.08)`, radius 6px, padding 1px 6px, a thin arrow glyph before the signed value ("↑ +17.6%", "↓ −1.2%"). Never green or red.
- `.new-tag`: 11px weight 600 `--acu-purple` on `rgba(214,200,226,.6)`, radius 999px, padding 1px 8px.
- `.segmented`: 1px `var(--line)` border, radius 8px, 13px items, 32px tall; the selected item has a `--acu-plum` background and white text.
- Buttons: `.primary` (gold) = `--acu-gold` background, `--acu-plum` text, radius 8px, 14px weight 600, 40px tall; `.secondary` = white, 1px `var(--line)`, `--acu-plum` text, same size; `.icon-button` = 40x40 white, 1px `var(--line)`, radius 10px, an 18px line icon, a tooltip and an accessible name.
- One-gold audit: list every view where more than one gold element shows at once today; fix what this prompt owns (the shell) and list the rest for their prompts.

## Rules specific to this build
- Do not rename or remove any `#tab-*` id or `#workspace-title`; many browser tests click them.
- `test_workspace_polish_browser.cjs` may assert that the tagline or group labels are hidden. If so, update that assertion to the visible state (call 9) and say so; do not delete it.

## Acceptance
- Screenshots at 1440x900 and 1920x1080 of the sidebar and header on all seven views, each beside the M4 sidebar crop.
- Measured: sidebar width 208px; exactly one element with the active style; the sidebar spans the full document height on the tallest view (Cross-reference).
- Suites: `test_console_templates.py` (run from `mentat/tests`), `test_workspace_polish_browser.cjs`, `test_console_browser.cjs`, `test_navigation_scope_browser.cjs`, `render_console.py --check`.
