# Lane T - follow-ups to lane Z and the refreshed commit plan (2026-09-26)

Run id `lane-t-20260926` (Glass Box source `final-fixes`). Brief: four small fixes that lane Z's final
verification found, then refresh lane Z's commit plan around them, re-test Z5 and Z6, regenerate and rehearse the
apply kit, and copy it and every lane's receipts to a durable folder. No git write and no stash in
C:\Users\pgoff\Mentat; nothing committed. The six commits are Paul's to make.

## Status: DONE

## 1. Fixes (live tree, uncommitted; writer `apply_edit.py`, specs `specs\t1..t4`, backups `backup\`)

| # | file | sha256 before -> after | lines | what |
| --- | --- | --- | --- | --- |
| 1 | mentat/tests/test_studio_strip_removed_browser.cjs | f8a7bb71 -> a95aef8e | 367-370 | url_scope pin 6 -> 7, with the reason (lane F's v7 adds only `<pane>.flow`; studioPane unchanged) |
| 2 | mentat/tests/test_console_browser.cjs | 95afa414 -> 5f890a08 | 312-316 | the estimates refusal awaited in `#graph-candidates .graph-empty` (lane C, F4), plus: the note under the panel does not repeat it |
| 3 | mentat/tests/test_flow_route.py | cbc48a08 -> 3d813197 | 675-683 | IndustryRefunds skips, naming the missing pinned Banking payload/manifest, instead of erroring |
| 4 | mentat/METHODOLOGY.md | 29bb8693 -> f7b7709b | 104 | transfer row: index v6 / PAS2 parser v9 (was v5 / v6) and F11's reload rule |

- Drift: before writing, all 630 files lane Z tested and all 2,102 status entries were unchanged; after, exactly
  these four moved (`drift_*.json`). Every edit ran first on scratch copies; line endings kept per line
  (METHODOLOGY's row stays one of its three LF lines; the console suite's block stays CRLF) (`selftest*.json`).
- No other stale version statement in METHODOLOGY.md (url_scope, studio_api, evidence-geo, flow and receipt rules
  are not named there; the header "Version 5, September 12, 2026" is the document's own version).
- Fix 3 on the LIVE tree: IndustryRefunds 2/2 ok with both pinned files present; all 48,532 files under the
  live mentat/ unchanged by the run (`live_proof.json`). Bare export: skipped, naming both files; supplied: runs.

## 2. Plan refresh

- Fresh shallow clone `clone\` at 3cec98524 (autocrlf off, origin removed, hooks off). Lane Z's build_set.py re-run:
  633 paths (631 + the two browser suites), only lane T's four entries differ from lane Z's commit_set.json.
  zB' tree 89977f4e.
- Lane Z's build_plan.py with lane T in group 5 (Z5): no problems; tip tree == zB' tree. Z1-Z4 trees identical to
  lane Z's tested trees (38420b12, b308b2be, 552b7a92, 79063e8f). Z5 035dbb1e (118 paths), Z6 89977f4e; each differs
  from lane Z's only in lane T's four files. Commit structure unchanged: six commits, same order and subjects.
- Kit `kit\`: bundle (tip 6c12b631f, requires 3cec98524, verifies against the real repo), both apply scripts (new
  tip; everything read from `$PSScriptRoot`, param -Kit; one new check: mentat/app/geo/.gitignore must be
  unedited, because the apply rewrites it and the file check skips it), messages (Z1 and Z5 updated), lists,
  plan_states.

## 3. Tests (clean D-048 exports, inputs supplied by name as hard links to lane Z's verified copies)

- Z5: node 619/619, cjs 14/14, R 32/32, PS 6/6, render ok; Python 121/123 under the venv (1,661 tests) + the six
  pid-holding modules and the prewarm trio 9/9 under system Python; the two re-pinned browser suites 2/2.
- Z6 (final): node 619/619, cjs 14/14, R 32/32, PS 6/6, render pass; Python 128/130 modules (1,759 tests, 15 skipped); browser 50/50.
- Reds left: test_state_legislative_geo (EOL size pin, pre-existing) and test_split_telecom_workbook (pytest-style,
  NO TESTS RAN) - both lane Z's pre-existing classes.
- Negative control: both re-pinned suites FAIL on the Z4 export (strip: step 5 "url_scope is v7"; console: timeout
  at line 315, the re-pinned wait).
- No process left naming a lane T export after any run (the one "LEFT" line after each label is the checker's own
  PowerShell).

## 4. Rehearsals (from the durable folder, on fresh copies set up like Paul's checkout)

- Final kit: `simA2` route A (`apply_plan.ps1`) and `simB2` route B (`apply_plan_porcelain.ps1`): check OK,
  execute OK, six commits with the six tested trees, messages equal to messages\Zk.txt, Paul Goff as author,
  parent 3cec98524, `git status --porcelain=v1 -uall` empty afterwards (`rehearsal_A_simA2.json`,
  `rehearsal_B_simB2.json`). The same passed on `simA`/`simB` before the geo check was added.
- Geo check negative control: `simC` with an edit in mentat/app/geo/.gitignore - both scripts refuse in check
  mode, nothing written (`negctl_geo_guard.out`).
- Both check modes run from the packet folder against the REAL repo: pass at 11:29 and again at 11:42 UTC, after
  every test and rehearsal (`real_check.out` holds the 11:42 run).

## 5. Durable packet

`C:\Users\pgoff\Mentat\outputs\pac-map-downstream-viz-20260926\` (MANIFEST.sha256 lists every file): README.md,
COMMIT_PLAN.md (lanes Z and T), the kit (plan_states as plan_states.zip), lanes\<lane>\ with each lane's RECEIPT*
and PROGRESS* files (lane Z: its original COMMIT_PLAN.md and runs_summary.json; lane D has only PROGRESS.md;
lanes A, B, E only RECEIPT.json; V2's receipts are RECEIPT.jsonl and RECEIPT2.json).

## 6. Open, for the orchestrator

- `mentat/README.md:151` (an E line) still says "OTH transfer index v5 and PAS2 parser v6". Not in the brief, not
  touched. Its last writer is V2, so a fix belongs in Z6 or later.
- test_studio_strip_removed_browser's own cleanup of its temp report folder fails with EPERM on Windows
  (pre-existing; lane Z's runs show it too), leaving `%TEMP%\mentat-strip-reports-*` folders.
- Lane Z's kit (laneZ\zPlan.bundle, tip 77d64bfce) is superseded; the durable packet is the one to apply.
- The packet lives inside the repo: the root rules hide its .json/.txt/.jsonl files; the rest shows as untracked
  (34 MB, of which the bundle is 15.8 MB and plan_states.zip 17.4 MB).

## 7. Brain draft (for Paul to apply)

- STATE: Mentat commit plan refreshed by lane T (2026-09-26): six commits Z1-Z6 on codex/mentat-crypto from
  3cec98524, tip tree 89977f4e, 633 paths; packet and apply kit at
  C:\Users\pgoff\Mentat\outputs\pac-map-downstream-viz-20260926 (README.md = how to apply). Z1-Z4 as lane Z
  tested; Z5 carries lane T's two browser re-pins, the test_flow_route skip and METHODOLOGY's transfer row
  (index v6 / PAS2 parser v9, F11). Not applied.
- DEADENDS candidate: a Python heredoc in the Bash tool collapsed `\\` to `\`, so Windows paths in a string
  turned `\r` and `\n` into control characters in a generated document; write scripts with the Write tool
  (confirms the existing shell-heredoc memory).
