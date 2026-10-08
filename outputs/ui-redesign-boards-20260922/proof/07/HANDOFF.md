# Build 07 (Loading) handoff - 2026-09-22

Loading's four-step flow (boards B20, L1, L2, L3) and the Saved FEC coverage grid (L4). Nothing is committed. Paul reviews `DIFFERENCES.md` and the `07_*.png` side-by-sides, then commits.

**No server change and no restart needed.** `/api/roster` and `/api/upload` readiness already carry names: `duplicate_companies` is a list of company names, `cross_company_variants` is `[{variant, companies:[names]}]`, `parse_errors` are messages (`mentat/tools/validate_industry_coverage.py:188-221`). `app.js`, `coverage-view.js` and `style.css` are served from disk and `/` is rendered from the templates per request, so Paul's 8806 picks the build up on a reload with the cache bypassed. STATIC_ASSETS unchanged; no new static file.

## Files (pre-build copies and the sha256 ledger: `scratchpad\mentat\build07\pre\`, `ledger.json`)

| File | Lines vs pre-build | sha256 | Endings |
|---|---|---|---|
| mentat/app/templates/view_loading.html | +58 -20 | 765aa5994f574775a177610cf6f6810ba1098c3c5253471826d181daef05c11e | CRLF (as before) |
| mentat/app/app.js | +487 -43 | 2436d75b96ad7b1a291922521387b7118d72449bf2871b1b8be75747d1f48c69 | CRLF (as before) |
| mentat/app/coverage-view.js | +68 -1 | 180fe6539f0d3840994f23800481d39c7974d5b1862b4d734fab79034449f2eb | CRLF (as before) |
| mentat/app/style.css | +257 appended (LF, ASCII) | 618e4cceb0aa6bcb84d640070b863626601e4067c87e126e00f690d9ad95f8b7 | mixed; the 12 CRLF lines kept |
| mentat/tests/test_console_browser.cjs | +6 -2 (lines 63-72) | 0fa3d80c94a471eed2d603a10dfaf87f845a15fe833663ec1f5ea6ef895e2ef9 | mixed; 496 CRLF / 2 LF, new lines CRLF like their neighbours |
| mentat/tests/test_coverage_view.cjs | +30 | 7497db76b17b4b0134979285d6c66840409c932d96c50d7345ab929ad4ae549c | LF |
| mentat/app/index.html | re-rendered (`render_console.py --write`) | - | LF |

`test_collection_console.py` needed no change (no server change). Why style.css: prompt 07 names no stylesheet and the later sheets are single-writer (acu-theme.css, workspace-polish.css) or other lanes'; style.css is where Loading's styles already lived. Every new rule is `body[data-view] #view-loading ...` with new `loading-*` / `coverage-grid` names, so it outranks the older Loading rules in workspace-polish.css without `!important` and touches no other view. The dead `#view-loading .loading-grid/.company-entry/...` rules in workspace-polish.css (lines 21-38, 152-153) are now unused; the holder of that file may delete them.

## What changed

- **Template**: title/subtitle as before; a stepper `#loading-steps` (1 Roster, 2 Review names, 3 Choose cycles, 4 Collect); two cards: `.loading-main` (step panes `#loading-step-roster`, `#upload-review`, `#loading-step-cycles`) and `.loading-setup` ("Collection setup": `#setup-summary`, `#setup-note`, Back `#roster-back`, and one gold button per step: `#review-roster`, `#choose-cycles`, `#start`); the coverage card keeps `.coverage-panel`, the `details.inline-help` (now a popover) and `#loading-coverage`. Kept ids: `#roster-panel`, `#roster-form`, `#sector`, `#company-editor`, `#add-company`, `#review-roster`, `#draft-status`, `#file`, `#upload-review`, `#roster-counts`, `#roster-list`, `input[name=cycle]` (2022/2024/2026), `#api-key`, `#key-hint`, `#save-keys`, `#start`, `#key-status`, `#loading-coverage`. Removed: `#review-placeholder`, `details.file-import`. New: `#new-company`, `#paste-roster`, `#roster-drop`, `#roster-mode-type/-upload`, `#roster-upload`, `#upload-*`, `#roster-decisions`, `#choose-cycles`, `#roster-back`, `#keys-toggle`, `#key-editor`, `#next-searches`, `#setup-summary`, `#setup-note`, `#sector-options`.
- **app.js**: the company table (rows `.company-entry` with `.company-name`, chips `.loading-alias` and `.company-alias-input`; Enter or comma adds a chip, × or Backspace removes; the "Add a company..." row; paste of tab/comma rows into a name cell or through "Paste from spreadsheet"); `draftData()` still returns exactly `{sector, companies:[{name, aliases}]}` and the draft key `mentat-roster-draft-v1` is unchanged; the upload pane (one read of the file: the same base64 goes to `/api/upload`, a CSV/TSV is also parsed for the column check and for decisions); step 2's decisions from readiness (`decisionsFor`) replace the raw-JSON line; step 3's cycle cards read the saved coverage; key status "N enabled · M disabled" with "Add or replace keys"; the coverage grid (`renderLoadingCoverage` -> `MentatCoverage.matrix/grid`, a clicked cell is remembered and keeps focus across the 3s poll).
- **coverage-view.js**: `select()` and `html()` are unchanged (Collection's `#collection-coverage` still uses `html()`); added `matrix`, `grid`, `detail`, `cycleLabel`, `formatDate`.
- **Decisions**: typed draft - Keep for <A> removes the name from the other companies' chips, Remove removes it everywhere, Merge folds a repeated company's chips into the first row and removes the repeats, then `/api/roster` runs again. The server refuses a draft with a repeated company name outright, so that repeat is detected in the browser and offered as a decision before anything is sent. Uploaded CSV/TSV - the same edits are made to the file's rows in the browser and the edited table is sent again to `/api/upload` under the same file name (payload shape unchanged). Excel uploads and parse errors - "Fix in step 1". Choose cycles stays disabled until readiness is `succeeded`, every group is `ready` and no decision is open.

## Suites

Before (on the unmodified bytes, before the first edit): render --check OK; test_collection_console 37 passed; test_console_templates 10 passed (+2 subtests); test_coverage_view passed; test_app_lazy_startup_browser 3/3; test_console_browser FAIL at line 289 (Graph, `'$1' !== '$0'`; its Loading lines 63-80 passed); test_workspace_polish_browser FAIL at line 142 (build 05's cross-reference open item; its Loading lines 97-105 passed).

After (final run, right after `render_console.py --write`): render --check OK before the suites; test_collection_console 37 passed; test_console_templates 10 passed (+2 subtests); test_coverage_view passed (30 new assertions for the grid); test_app_lazy_startup_browser 3/3; test_console_browser FAIL at line 300 (Graph candidates `$777.00` wait; an earlier run stopped at line 105 with ENOSPC: drive C: had 0.5 GB free for the suite's sparse 500 MB file) - its Loading assertions (lines 63-80, two re-homed) pass; test_workspace_polish_browser FAIL at line 120 (`#studio-clear`, Chart Studio) and, on the rerun before it, at line 84 via 126 (Chart Studio shell styling at 1168px) - build 03 is changing Chart Studio; the suite's Loading steps (lines 97-105: roster focus after remove, Review roster, `#upload-review` shown, `#start` reads "Start collection", Loading does not overflow at 1168/900/390) pass unchanged. This file is single-writer and was not edited.

`render_console.py --check` at the very end: first "out of date" because build 03 changed `view_chart_studio.html` during the run (the Clear comparison button); `--write` was run again and `--check` then reported up to date (89,794 bytes). Build 03 will re-render again when it finishes.

## Re-homed assertions

- test_console_browser.cjs:64 `/2026-06-30/` -> `/Jun 30, 2026/` (the chip writes the verified date as the board does: "Stale · to Jun 30, 2026", with `<time datetime="2026-06-30">`).
- test_console_browser.cjs:68 `doesNotMatch /2026-06-30/` after typing another sector -> the grid shows that sector as its own row (`/A different sector\s+This roster/`) and still shows the saved date (`/Jun 30, 2026/`): the grid is "what is already on this computer", no longer filtered to the typed sector. Line 69 (`/No saved collection evidence/`) passes unchanged: the typed sector's cell is selected by default and its detail says so.
- `Stale coverage`, `Unverifiable coverage`, `Current within policy` (test_console_browser.cjs:63-66, 73, 76; test_workspace_polish_browser.cjs:97) still match: each grid cell carries its full status in screen-reader text, and the detail panel's Status line uses the same words.

## Open items for Paul

1. DIFFERENCES C2: at 1440x900 the upload preview pushes the footer about 20px below the fold.
2. A comma now ends a chip, as prompt 07 asks, so an other-name containing a comma ("Acme, Inc.") cannot be typed as one chip; it can be pasted (paste splits only on tabs and line breaks). The server accepts such names (test_collection_console.py:89).
3. Excel uploads cannot be edited in the browser: their decisions say "Fix in step 1" (edit the workbook, then Replace). CSV/TSV uploads and typed rosters get the Keep/Remove/Merge buttons.
4. Every decision re-runs `/api/roster` or `/api/upload`, and each call saves a new roster folder (as every Review and upload did before); superseded rosters appear under Collection's "In progress" until archived.
5. workspace-polish.css lines 21-38 and 152-161 hold dead Loading rules (for the file's holder to remove).
6. Environment: drive C: at 0.5 GB free makes test_console_browser.cjs fail at line 105 for every builder.

## Proof

`proof\07\`: `07_<state>_<1440|1920>.png` for B20_typing, L1_upload, L2_decisions, L2_settled, L3_cycles, L4_grid, L4_real; `shots\`; `measurements.json` (boxes, gold count, overflow, request bodies, reload restore); `capture.cjs` and `sbs07.py` (re-runnable: `python mentat/app/server.py --port 8818 --read-only`, then `node capture.cjs 8818`, `python sbs07.py`); `status_before.txt`, `processes_before.txt`. Ignored by git: `measurements.json` (`*.json`), `status_before.txt` and `processes_before.txt` (`*.txt`). Port 8818 console stopped; no browser left running.

## Final fix round (2026-09-23)

Review defects R07-1..R07-3, all fixed. Pre-fix copies: `scratchpad\mentat\build07\fix1\`; the style.css edits were made by `fix1_style.py` / `fix1_style2.py` (byte-exact replacements, sha256-checked against `ledger.json` first) because style.css has mixed endings (12 CRLF lines kept, new lines LF like the Loading block); view_loading.html by the Edit tool (all CRLF, 64 lines, none LF-only).

- R07-1 (major, L4 chip truncates the verified date at 1440) -> fixed. style.css: `.coverage-grid td{padding:0 8px}` (was 14px), `.coverage-chip{padding:0 8px;font:400 14px/33px}` (was 10px, 15px). At 1440 every current/stale chip now fits, selected or not: scrollWidth = clientWidth 181 (selected 179); at 1920 214 (selected 212). DIFFERENCES F6 updated; `shots\L4_verified_*.png` shows Banking 2021-22 selected with "Verified · to Dec 31, 2022" whole.
- R07-2 (minor, L1 footer below the fold at 1440x900) -> fixed. style.css: the preview's chip cells (Other names, Excluded) are `white-space:nowrap` (the later rule `td:nth-child(2){white-space:normal}` was the one to change: same specificity, later wins), rows 36px (`td{height:36px;padding:3px 12px}`, `th{padding:0 12px}`), preview chips 24px with 8px gaps. Footer y 778-825 and the card ends at y 850 at 1440x900 (was 864-911); preview rows 36px except "JP Morgan Chase Bank NA", whose name wraps (47px). DIFFERENCES C2 now fixed. Open item 1 above is closed.
- R07-3 (minor, Enter in Sector / a company name no longer ran the review) -> fixed. view_loading.html: `<button type="submit" class="sr-only" tabindex="-1" aria-hidden="true">Review names</button>` as the last child of `#roster-form`, so implicit submission reaches the existing `submit` -> `reviewDraft()` handler (app.js:346). Verified by `capture.cjs` (enter_1440 / enter_1920): Enter in `#sector` -> step 2, Enter in `.company-name` -> step 2. Enter in an other-name field and in "Add a company..." keep their own behaviour (their keydown handlers call preventDefault, app.js:281, 297). app.js unchanged.

Files after the fix round (sha256): view_loading.html `156f93fbd41ec73a37b687dadb189a13f2beb5f0bfd7ecdecb5e37ed308f208c` (+1 line); style.css `4111e551c0fde59ef3c0e46fcd47e32a534bff6871aac8d22a7e6a84285bdaea` (+2 lines, 5 changed); index.html re-rendered (89,887 bytes, `--check` up to date). app.js, coverage-view.js and the tests are unchanged from the hashes in the table above. style.css is not in the fix round's owned list; the edits stay inside build 07's own `body[data-view] #view-loading` block.

Suites after the fix (`scratchpad\mentat\build07\suites_fix1.txt`, `suites_fix1_rerun.txt`; "before" = `suites_final.txt` on the identical pre-fix bytes): render --check OK; test_collection_console 37 passed; test_console_templates 10 passed (+2 subtests); test_coverage_view passed; test_app_lazy_startup_browser 3/3. test_console_browser FAIL at line 367 (Graph mobile chart label), rerun FAIL at line 300 (Graph candidates `$777.00`, as before the fix); test_workspace_polish_browser FAIL at line 153 (Cross-reference `.xref-adjustments` summary), rerun the same. Both are past their Loading assertions (console 63-80, polish 97-105), which pass; the failing views belong to other builds.

Proof re-captured (`node capture.cjs 8818` against a read-only console on 8818, now stopped; `python sbs07.py`): all `07_*_1440/1920.png`, `shots\`, `measurements.json` (new fields `foot`, `previewRows`, `covChips`, `L4_*.selected_*`, `enter_*`).
