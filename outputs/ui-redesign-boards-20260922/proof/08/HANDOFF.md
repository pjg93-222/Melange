# Build 08 (Collection) handoff - 2026-09-23

Collection monitor rebuilt to board B22: header status pill, folder tabs, one run card (title, subtitle, overall bar with percent and time left, four-step stepper, per-company table, Pause/Stop/Resume + Open working folder + gold View partial results), the note under the card, quiet disclosures below it, the empty state and compact History/Archived cards. Nothing is committed. Paul reviews `DIFFERENCES.md` and the `08_*.png` side-by-sides, then commits.

**No server change, no restart, no new static file.** `/api/runs` and `/api/run` already carry every field used (B22 needs no new data). `app.js` and `style.css` are served from disk and `/` is rendered from the templates per request, so Paul's 8806 picks the build up on a reload with the cache bypassed. STATIC_ASSETS unchanged.

## How this build ran

The first build-08 session (00:43-01:08) wrote the template, app.js and style.css block, rendered index.html and captured proof, then stopped before its suites, test re-homes and write-up. This session (01:12 on) verified those files still carried that session's recorded hashes (`scratchpad\mentat\build08\ledger.json`, "current"), found no other writer, and finished: two re-homed test assertions, a proof re-capture (the popover had been shot mid-fade), side-by-sides, suites, this handoff. Pre-build copies: `scratchpad\mentat\build08\pre\`.

## Files

| File | Lines vs pre-build | sha256 | Endings |
|---|---|---|---|
| mentat/app/templates/view_collection.html | +39 -16 | ed1d219eb0438026c760c57e9ae4d02326453dc740af82232472360ab6fbbc93 | CRLF (as before, 44 lines) |
| mentat/app/app.js | +207 -12 | 4822edffc5ecba643c8541d9775d3b6e9175c953287b620ca529d03e1b0d75c7 | CRLF (as before, 0 LF-only) |
| mentat/app/style.css | +156 appended (LF) | c20d8e36b2fbbedbf350adbddf3713245f0365dcb17bc94b9f09bfe94f4fb48e | mixed; the 12 CRLF lines kept; the pre-build bytes are an exact prefix |
| mentat/tests/test_console_browser.cjs | +6 -2 (lines 232-238) | 2bdd83d39462d974b36241c674b64834cb2eb77135ac0639ee54a8d45191ad70 | mixed 500 CRLF / 2 LF (new lines CRLF like their neighbours; the 2 LF lines untouched) |
| mentat/app/index.html | re-rendered (`render_console.py --write`) | 6e5b6e9a66c4eacb59ce1b560ed63eb1d87f3ce8eb66168f2f6c83d032d2ae45 (92,631 bytes) | LF |

style.css is not in this build's owned list; it follows build 07's precedent (prompt 08 names no stylesheet; acu-theme.css and workspace-polish.css are single-writer). Every new rule is `body[data-view] #view-collection ...` or `body[data-view=collection] #stage...`, appended after build 07's Loading block, so it touches no other view. test_collection_console.py, test_run_archive.py and test_app_lazy_startup_browser.cjs needed no change. None of the changed or proof files is git-ignored except `proof\08\measurements.json` (`*.json`).

## What changed

- **Template** (`view_collection.html`): kept ids `data-run-group` buttons with `#run-count-progress/-history/-archived`, `#runs`, `#archive-run`, `#collection-directory`, `#completed-directory`, `#view-completed-reports`, `#run-title`, `#resume-setup`, `#run-readiness-note`, `#empty`, `#monitor`, `#freshness`, `#completed`, `#workers`, `#worker-detail`, `#failed`, `#eta`, `#elapsed`, `#quality-title`, `#quality-detail`, `#quality-checks`, `#clear-quality`, `#source-snapshots`, `#stop`, `#resume-run`, `#worker-target`, `#apply-workers`, `#stopping-banner`, `#progress`, `#phase-description`, `#industries`, `#lanes`, `#lane-summary`, `#checkpoints`, `#records`, `#events`, `#reports`, `#collection-coverage`, `#report-freshness`, `#run-controls`, `#worker-panel`, `#records-panel`, `#collection-coverage-details`, `#collection-freshness-details`. `details.working-folders` became the popover `div#working-folders` (same class). New: `#run-toolbar`, `#run-library-note`, `#run-history`, `#run-history-more`, `#empty-title`, `#empty-load-sector`, `#run-card`, `#run-subtitle`, `#run-setup-actions`, `#run-percent`, `#run-steps`, `#run-companies`, `#run-companies-note`, `#stop-label`, `#open-working-folder`, `#view-partial-results`, `#run-card-note`, `#run-details`, `#run-quality`, `#quality-summary`, `#collection-workers-details`, `#collection-activity-details`, `#collection-events-details`.
- **app.js**: header title "Collection" (was "Collection monitor"); `#stage` is the status pill (`data-run-state` running / stopped / failed / completed; Ready / Needs review / Loading for drafts); `renderRunCard()` (subtitle, bar, percent, stepper, company table, gold button); `etaText()` turns the timer's "About h:mm:ss" into "about N min left" and shows "Elapsed <t>" while there is no estimate; `renderRunHistory()` for History/Archived; the popover (click, Escape, outside click); `#view-partial-results` opens and focuses the Activity log; `#empty-load-sector` opens Loading. `#stop`/`#resume-run` handlers unchanged.
- **Stepper mapping** (stage names from `Start-MentatResilientIndustryReports.ps1` and `api_company_cycle_fanout.py`; the earliest active industry's stage wins): starting, pending, preparing, initializing -> **Search names** current; collecting, recovering, splitting, merging -> **Fetch receipts**; finalizing_database, coverage_gate, raw_data_gate -> **Verify**; generator_queued, pipelining, waiting_for_generators -> **Publish**; run or status `completed` -> all four done. A stopped/failed run shows its last stage as a grey "halted" ring. Caveat for Paul: the data has no separate name-search phase - each company/cycle task searches and fetches in one pass - so "Search names" stands for the setup stages that load the roster's names and build the search tasks; it is done as soon as collecting starts.
- **Per-company table**: companies from the roster readiness (so unstarted ones show), finished tasks from every worker's `lanes[].state.tasks` (rows summed, latest `ended_at`), plus the selected worker's in-flight checkpoint rows (`preview.progress`, `rows_seen`, `updated_at`) for tasks not yet finished. Progress = finished tasks / the run's cycles. The API returns checkpoint rows for the selected worker only, so with two or more workers a note under the table says in-flight receipts come from that worker (open item 3).
- **Pause / Stop / Resume**: `#stop` reads "Pause" while a run with worker lanes is active (a stop keeps lane data, so Resume continues it), "Stop" otherwise; it hides when the run ends and `#resume-run` ("Resume") shows for a resumable run. Same ids, same requests.

## Suites

Before (the first session, on the unmodified bytes, `scratchpad\mentat\build08\suites_before.txt`): render --check OK (89,887 bytes); pytest (test_collection_console + test_run_archive) 43 passed + 7 subtests; test_app_lazy_startup_browser 3/3; test_console_browser FAIL at line 300 (Graph candidates `$777.00` wait, not Collection).

Mid-run (build's bytes, before the re-homes; `suites_pre_edit_current.txt`): test_console_browser FAIL at line 236 (`#worker-metric-label` innerText empty inside the closed Workers disclosure) - fixed by the re-home below.

After (right after `render_console.py --write`; `suites_final.txt`): render --check OK (92,631 bytes); pytest test_collection_console + test_run_archive + test_console_templates + test_console_delivery + test_report_directory_console 68 passed + 9 subtests; test_app_lazy_startup_browser 3/3; **test_console_browser PASS** (whole file, including its Collection block 175-243 and the Graph line 300 that failed before); test_workspace_polish_browser FAIL at line 153 (Cross-reference `.xref-adjustments summary`, build 05's view; same failure build 07 reported), rerun once: same (`suites_polish_rerun.txt`). Its Collection steps (lines 110-115: History, coverage and freshness disclosures) pass. `render_console.py --check` at the very end: up to date (92,631 bytes).

## Re-homed assertions (test_console_browser.cjs)

- 232-233: `#stage` text `'stopped'` -> `'Stopped'` (the header pill writes the state in words, prompt item 1). Added 234: `#stage[data-run-state]` equals `stopped`; 235: exactly one visible `#view-collection .primary--gold` (prompt acceptance).
- 236-237 (added): the worker metrics are inside the collapsed "Workers" disclosure (prompt item 4), where `innerText` is empty; the test opens the disclosure before reading `#worker-metric-label` and `#workers`. The assertions themselves are unchanged.

## Open items for Paul

1. DIFFERENCES A2/A3: B22 draws the page title at about 41px and a taller header; the shell (build 01) uses 31px for every view, so the Collection content sits 15px higher than the board. A shell-holder change if Paul wants B22's header.
2. Stepper "Search names" is the setup stages, not a separate search phase (see the mapping).
3. Receipts for in-flight tasks come from the selected worker only (API shape); finished-task receipts come from all workers.
4. style.css used outside the owned list (build 07 precedent), for the orchestrator to ratify.

## Proof

`proof\08\`: `08_<state>_<1440|1600|1920>.png` for running, stopped, completed, empty, history, folder; `shots\` (also `history_full_*` and `mobile_390x844.png`); `measurements.json`; `capture.cjs` and `sbs08.py` (re-runnable: `python mentat/app/server.py --port 8819 --read-only`, then `node capture.cjs 8819`, `python sbs08.py`). Port 8819 console stopped; no browser left running.
