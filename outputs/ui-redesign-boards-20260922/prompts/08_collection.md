# Build prompt 08 · Collection monitor (B22)

**Builder:** one Opus architect or Codex agent, alone in the tree, after 01 and 07. **Read first:** `prompts\00_README.md`.

## Visual spec (binding)

- `boards\B22_collection_run_card.webp`. Its sidebar follows 01.

**Don't copy:** dashes in queued rows (they read "Queued"); every name, count and time.

## What exists today (verified 2026-09-22)

- Template `mentat/app/templates/view_collection.html` (20 lines): folder buttons `data-run-group` progress / history / archived with counts `#run-count-progress`, `#run-count-history`, `#run-count-archived`; `select#runs`; `#archive-run`; `details.working-folders` (`#collection-directory`, `#completed-directory`, `#view-completed-reports`); `h2#run-title`; `#resume-setup` ("Continue collection setup"); `#run-readiness-note`; `#empty` ("Start with a list of names."); `#monitor` with `#freshness`, the metrics `#completed` ("Search tasks processed"), `#workers`, `#worker-detail`, `#failed`, `#eta`, `#elapsed`; the quality panel (`#quality-title`, `#quality-detail`, `#quality-checks`, `#clear-quality`, `#source-snapshots`); run controls `#stop` ("Stop collection"), `#resume-run` ("Resume last run"), `#worker-target`, `#apply-workers`; `#stopping-banner`; `#progress`; `#phase-description`; `#industries`; the worker panel (`select#lanes`, `#lane-summary`, and the table `#checkpoints` with Company | Cycle | Search | Rows fetched | Source count | Checkpoint); `#records` (Activity Log); `#events` (Run events); `#reports`; `#collection-coverage` ("FEC data-through by sector and cycle"); `#report-freshness`.
- `mentat/app/app.js`: `renderRunLibrary()` 282-304 (folders, run select), `render(run)` 336-432 (monitor, controls, industries, lanes, checkpoints, records, events, reports), report freshness 376-382.
- `/api/runs` (`server.py` 1971-1994): `runs` (each run's own fields plus `archived`, `can_archive`, `resumable`, `resumed_from`), `archived_count`, `total_run_count`, `collection_directory`, `report_directory`, `coverage`, `key_configured`, `read_only`, and the key-status fields.
- Tests: `test_collection_console.py`, `test_run_archive.py`, `test_console_browser.cjs` (mocks `/api/run*`), `test_app_lazy_startup_browser.cjs`.

## Build this

1. **Header:** title "Collection" and, at the right, a status pill from the selected run's state: teal "Running", grey "Stopped", `--chart-negative` "Failed", plum "Completed".
2. **Folders as tabs:** "In progress <n>", "History <n>", "Archived <n>" (the existing buttons restyled as underline tabs, the active one with a 3px `--acu-gold` underline). The run select and "Archive run" stay reachable in a compact row under the tabs when a folder holds more than one run.
3. **Run card** (full width):
   - Serif title: the roster file name (for example "Banking roster.csv"); muted subtitle "Started <date, time> · <n> companies · cycles <list>".
   - Overall progress: an 8px teal bar on a pale track (`#progress`) with "<pct>% · about <eta> left" at the right (`#eta`; "Elapsed <t>" when there is no estimate).
   - Stage stepper: Search names -> Fetch receipts -> Verify -> Publish (done: teal check; current: ring; upcoming: hollow). Map each stage from the run state and the phrases `#phase-description` shows today, and list the mapping in your report. If a stage cannot be told apart in the data, leave it out and report.
   - Per-company table: Company | Progress (bar and %) | Receipts fetched | Last checkpoint. Aggregate the worker checkpoint rows by company: sum "Rows fetched", take the latest checkpoint time, and compute progress as finished search tasks over that company's tasks when the data has both; otherwise show the rows fetched and "In progress". Companies with no rows yet read "Queued".
   - Footer buttons: secondary "Pause" (`#stop`) while running when the run can be resumed afterwards, otherwise "Stop"; once stopped it becomes "Resume" (`#resume-run`); secondary "Open working folder" (shows the existing working-folder paths in a popover, since a browser cannot open Explorer); and gold "View partial results", which jumps to the Activity log of stored records (disabled with a tooltip until records exist).
   - Under the card, `--muted`: "Closing the browser does not stop collection."
4. **Details, collapsed under the card**, each an existing panel restyled as a quiet disclosure: "Workers" (the worker panel with the worker target and Apply), "Activity log", "Run events", "Coverage" (FEC data-through) and "Report freshness". The yellow quality box becomes one line, "Coverage unverified · Details", that expands to today's text.
5. **Empty state** (no run): today's "Start with a list of names." inside a card, with a gold "Load a sector" button that opens Loading.
6. **History and Archived:** compact run cards (title, dates, final state, reports link), newest first.

## Acceptance
States at 1440x900 and 1920x1080 beside B22: a running collection (use the mocked `/api/run*` approach of `test_console_browser.cjs` in a browser harness; never start a real collection); stopped and resumable; completed; the empty state; History. Checks: queued rows read "Queued"; exactly one gold button; Stop and Resume keep their ids and behaviour. Suites: `test_collection_console.py`, `test_run_archive.py`, `test_console_browser.cjs`, `test_app_lazy_startup_browser.cjs`, `render_console.py --check`.
