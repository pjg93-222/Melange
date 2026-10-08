# Lanes Z and T - commit plan for the uncommitted Mentat work (2026-09-26)

Repo `C:\Users\pgoff\Mentat` (a worktree of the Melange Systems repository), branch `codex/mentat-crypto`,
HEAD `3cec985249b098478868b8729e33b5b4ab31752e`. Lane Z wrote this plan. Lane T then fixed the four small
things lane Z's verification found (section 1a) and refreshed the plan around them; this is the refreshed text
(lane Z's original is `lanes/laneZ/COMMIT_PLAN_laneZ_original.md` in the packet). Neither lane made a git write
or a stash in that repo. Lane T's only writes there are its four hunks and the packet folder
`outputs/pac-map-downstream-viz-20260926/`. Nothing is applied: the commits are Paul's to make.

## 0. Bottom line

- The whole uncommitted set - 94 modified tracked files, 535 new files, and lane G's geo ignore rule
  (633 paths) - committed as six commits in a throwaway clone, exported with D-048's dials and byte-checked
  (the final tree: 1,121/1,121 files equal their blobs), is a working tree. Final tree (Z6), gitignored inputs
  supplied by name: node 619/619, cjs 14/14, R 32/32, PowerShell 6/6, render --check, Python 128/130 modules (1,759 tests, 15 skipped),
  browser 50/50. Lane Z's read-only console smoke (section 4) ran on lane Z's final tree, which differs
  from this one only in lane T's four files (three tests and one doc row), so it carries over unchanged.
- Two reds remain, both pre-existing and not this set: an EOL size pin that fails on any LF export of HEAD,
  and a pytest-style module unittest cannot see. Lane Z's two browser reds are re-pinned (lane T), and
  test_flow_route now skips, naming the missing file, on a checkout without the Banking pinned source.
- Six commits, each made only of byte states that really existed, in the only order those states allow.
  Z1-Z4 are byte-identical to the trees lane Z tested (rebuilt independently in lane T's fresh clone); Z5
  carries lane T's four files (118 paths: lane Z's 116 plus the two browser suites); Z6 is the final tree. Both apply routes were rehearsed from the
  packet folder on fresh copies set up like Paul's checkout: six commits, each tree = the tested tree,
  `git status` empty afterwards.
- Stage with the DEFAULT add (system `core.autocrlf=true`), not `-c core.autocrlf=false`: see section 6.1.

## 1. Inventory (git status --porcelain=v1 -uall at 3cec98524: 94 ` M`, 2,010 `??`)

Owners (from the lanes' receipts; `E` = the 09-20..09-25 sessions' uncommitted work, found as the state
before our first lane wrote):

| owner | what | modified files | new files |
| --- | --- | --- | --- |
| E | 09-20..09-25 sessions: graph-quirks palette, peer batch 2, 12 review fixes, native scanner, docs | 21 | 14 |
| A | F1/F2, F11, F12 R port, F13 memo reason, F14, F15, C-1 stops | 19 | 9 |
| B | F6, F7, F8, F11 console, F12 walk + carryover | 9 | 7 |
| C | F4 not-traced disclosure, evidence contracts v4/v1, cash model rule | 14 | 12 |
| F | Flow Sankey (a, b, c), url_scope v7, refund netting | 12 | 16 |
| G | geo v2 build tools + tree (457 committed files) + ignore rule | 0 | 464 |
| H | F13 memo re-disclosure (receipt rules v6) | 8 | 4 |
| I | F16 runtime_inputs C-1 selection | 2 | 0 |
| M | Marks v3 (boards #50-#52) | 16 | 3 |
| P | maps as marks-card layers (boards #47-#55) | 10 | 12 |
| V | Mentat venv (requirements, launcher interpreter order) | 6 | 2 |
| V2 | one-process venv launches | 11 | 4 |
| T | 09-26 follow-ups to lane Z: two browser re-pins, test_flow_route skip, METHODOLOGY transfer row | 3 | 1 |

(A file counts once per owner; lane Z's `attribution_table.md`, `plan_scc.json` sequences.)

- 31 files carry more than one owner (lane Z's count); lane T adds one, test_flow_route.py (F, T), and joins
  METHODOLOGY.md (E, H, T). Nine files mix E with our lanes (METHODOLOGY.md, README.md,
  chart-studio-contributions.js, chart-studio.css, chart-studio.js, charts.js, contribution-charts.js,
  contribution-plot.js, graph.js). Every change block and its owners: lane Z's `hunk_lists.md` (from
  `hunks.json`); lane T's blocks are in section 1a. Chains were checked write by write: each write's pre-image
  is the previous write's result, and no write by anyone outside the receipts was found once lane A's `stage`
  rows (its scratch copies, not live writes) were set aside; the one unmatched step is index.html, re-rendered
  by lane P's `render_console --write` (in its receipt). The files only E touched all have mtimes at or before
  09-25 03:53, before the first lane wrote. Lane T's writes started from exactly the bytes lane Z recorded:
  all 630 files of lane Z's set and all 2,102 status entries were unchanged at 10:53 and 10:55 UTC on 09-26
  (`laneT\drift_pre_edit.json`, `drift_pre_write.json`).
- New files our lanes created: 67 (list with `git check-ignore -v` in lane Z's `ignored_scan.json`). Three are
  hidden by the root `*.json` rule and need `git add -f`: `audits/mentat_failings_20260915/contracts/`
  `evidence-network.json`, `flow.json`, `graph-not-traced.json`. The test fixtures are admitted by the new
  `mentat/tests/fixtures/.gitignore` (`!*.json`), `requirements-console.txt` by `!requirements*.txt`, and
  geo v2 by `mentat/app/geo/.gitignore` (`!*.json`).
- Earlier sessions' new files (14, all under mentat/): records_sidecar.py, test_records_sidecar.py,
  test_query_building.py, chart-pie-fit.test.js, contribution-studio-pending.test.js, theme-palette.test.js,
  test_studio_pie_refit_browser.cjs, INSIGHTS.md, native/mentat-scan (4 files), benchmark_native_ui.py,
  build_native.ps1.
- NOT to commit (generated / runtime): `mentat/app/geo/v2/albers/detail/`, `v2/wgs84/z5/`, `v2/wgs84/z10/`
  (410 files, 131 MB; the Z3 rule ignores them); everything under `mentat/.cache` (geo, geo_build/v2 staging,
  basemap incl. the 112 MB pmtiles, industry-report payloads, pac-evidence snapshots, repair-20260908-inputs
  incl. the 2020 v6 index, transfer-index backups) and `mentat/state` (both already ignored); lane proof
  outputs (all in the session scratchpad, none in the repo).
- Outside this plan (1,065 untracked paths, other owners): `outputs/` UI proof folders (09-20..09-22),
  `audits/` packets of 09-20/21 (incl. the two README.md links to, 5.5), `sector_growth_study/` (the sector
  growth lane), `.impeccable/`, `DESIGN.md`, `PRODUCT.md`; and now this packet folder.

## 1a. Lane T's four fixes (09-26, uncommitted, in Z5)

Written by `laneT\apply_edit.py` (lane H's writer: drift check against the sha256 lane Z recorded, byte-exact
backup, atomic write, each region keeps its own line endings); first run on scratch copies, then live.

| file | lines (after) | change | endings |
| --- | --- | --- | --- |
| mentat/tests/test_studio_strip_removed_browser.cjs | 367-370 | step 5 pins `url_scope.version` 7, not 6; the comment says v7 (lane F) adds only the `<pane>.flow` keys and the studioPane entry is unchanged | LF file, LF |
| mentat/tests/test_console_browser.cjs | 312-316 | the estimates refusal is awaited as the sentence "Saved estimates cover the whole industry" inside `#graph-candidates .graph-empty`, where lane C's F4 puts it (graph.js paintPanel -> emptyPanel); a new assertion checks the note under the panel does not repeat it | mixed file (519 CRLF, 2 LF), the block CRLF |
| mentat/tests/test_flow_route.py | 675-683 | IndustryRefunds.setUpClass raises SkipTest naming the missing files when the Banking workbook's pinned full report source (`graph_data.transfer_source`: industry_data-<fp>.json and manifest-<fp>.json under the gitignored `.cache/industry-report/banking`) is absent; if transfer_source names no source, the case still runs and errors | LF |
| mentat/METHODOLOGY.md | 104 | transfer row: "OTH index v6 and PAS2 parser v9" (was v5 / v6) and F11's reload rule: an FEC reload - the same record loaded again under a second sub-ID, equal in committee, report type, transaction ID, file number, counterparty, amount, date, type, name and memo code - counts once | the row's own LF (lines 5, 104, 107 are the file's three LF lines) |

- METHODOLOGY.md: line 104 was an E line (E rewrote it on 09-20..25); lane T changed only the version pair and
  added the F11 clause. E's lines 5 and 107 and lane H's line 102 are byte-identical before and after. No
  other version statement in the file is stale: the only others are generic, and the document's own header
  "Version 5, September 12, 2026" is the document's version (E, H and T all left it; Paul's call).
- Found in passing, NOT fixed (outside the brief): `mentat/README.md:151` (an E line) repeats "OTH transfer
  index v5 and PAS2 parser v6". README.md's last writer is lane V2 (Z6), so a fix there belongs in Z6 or later,
  not in Z5.
- Proof that fix 3 still runs where its input exists, on the LIVE tree: `python -m unittest -v
  test_flow_route.IndustryRefunds` (venv, PYTHONDONTWRITEBYTECODE=1) in C:\Users\pgoff\Mentat\mentat\tests:
  both pinned files present, 2 tests ok, and a stat snapshot of all 48,532 files under the live mentat/ before
  and after shows 0 changed, 0 added, 0 removed (`laneT\live_proof.json`). On the bare Z5 export (nothing
  supplied) the case is `skipped "the Banking workbook's pinned full report source is not on this machine:
  ...industry_data-4abdea581b99cec1.json, ...manifest-4abdea581b99cec1.json"` and the module is OK (29 run, 15
  skipped) where lane Z's bare run was `FAILED (errors=1)`; with the inputs supplied, 31/31 run.
- Negative control for the two re-pins: copied into the Z4 export (before lanes C and F), both re-pinned
  suites fail at exactly the re-pinned assertion: test_studio_strip_removed_browser fails at step 5 ("url_scope is v7 ...": Z4's contract is v6), and test_console_browser gets through every earlier step and then times out at line 315, the re-pinned wait (Z4's Graph puts the refusal in the note and a generic sentence in the panel) (`laneT\runs\negctl_Z4`).

## 2. The proof (D-048 / DE-031)

- Lane Z: `laneZ\clone`, `git clone --no-local --depth 1 --branch codex/mentat-crypto file:///C:/Users/pgoff/Mentat`
  (origin removed, no hooks), at 3cec98524; zA `7b0fd9f45` (`-c core.autocrlf=false add -f`) and zB `9a38eaa73`
  (`-c core.autocrlf=true add -f`) of the 631-path set; they differ only in the line endings of 50 files.
- Lane T: a fresh `laneT\clone` made the same way (`-c core.autocrlf=false` at clone time, origin removed,
  hooks pointed at an empty folder). Lane Z's `build_set.py` re-run there took the 633-path set (lane Z's 631 +
  the two browser suites) and re-copied every file (sha256 before/after the copy); against lane Z's
  `commit_set.json` exactly four entries differ (lane T's) and the excluded lists are identical. zB' `8914864b6`
  (tree `89977f4e`) differs from lane Z's zB tree only in lane T's four files.
- Exports: `git -c core.autocrlf=false -c core.eol=lf archive <sha> mentat audits/mentat_failings_20260915/contracts`
  to a tar, extracted, every file's blob id compared with `git ls-tree -r` both ways. Z4 1,063, Z5 1,119, Z6
  1,121 files: 0 missing, 0 extra, 0 blob mismatches (`laneT\export_plan_Z*_verify.json`). Z6 against the live
  working tree: 582 identical + 51 differing only in CRLF + 0 different.
- No committed `eol=` attribute exists (root .gitattributes has only `-text`/`binary`), so D-048's caveat
  does not bite.
- No drift: before lane T wrote, the real repo still had every sha256 lane Z tested; after, exactly lane T's
  four files differ (`laneT\drift_post_write.json`); branch and HEAD unchanged. Re-run the check mode of either
  apply script immediately before applying: it refuses if anything moved.

## 3. Suites

Runner `run_matrix.py` (lane Z's; lane T's copy adds exact-name selection): one process per suite, output to
a file, bounded wait + tree kill, >= 3 GB free before each suite, PYTHONDONTWRITEBYTECODE=1, MENTAT_PYTHON = the
venv, MENTAT_UI_OUTPUT = <lane>\ui\<run>\<suite>, browser suites strictly one at a time. Python under
C:\Users\pgoff\AppData\Local\Mentat\venv. Results: `runs\<label>\results.json` + logs; totals
`runs_summary.json` (lane Z: `laneZ\runs`; lane T: `laneT\runs`).

Inputs supplied BY NAME to every export (lane T: hard links to lane Z's own copies in `laneZ\export_B`, each
re-hashed against lane Z's recorded sha256 first: 2,044 files, 2.08 GB; nothing in the commit): .cache/geo
(Census), the FAIRSHAKE and SLF saved snapshots, the Banking and Crypto pinned report payloads, the geo v2
detail tiers, .cache/basemap, the FEC committee and candidate masters, and inputs/active_fec_sources.json
(a path into the live .cache, read-only).

The trees lane T changed (Z5, Z6), tested again:

| tree | node --test | cjs | R | PowerShell | render --check | Python modules (tests) | browser |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Z5 (lane T) | 619/619 | 14/14 | 32/32 | 6/6 | pass | 121/123 under the venv (1,661; 15 skipped) + the 6 pid-holding modules and the 3 prewarm modules their names match, 9/9 under system Python (133 tests; 2 skipped) (see below) | the two re-pinned suites 2/2 (strip suite 6 of 6 steps; console suite passes) |
| Z6 = final (lane T) | 619/619 | 14/14 | 32/32 | 6/6 | pass | 128/130 under the venv (1,759; 15 skipped; the six pid-holding modules pass here) | 50/50 |

Lane Z's results for the unchanged trees Z1-Z4 stand (same trees, byte for byte):

| commit | node --test | cjs | R | PS | render | Python modules | the two browser suites (old pins) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Z1 earlier sessions | 461/461 | 14/14 | 28/28 | 6/6 | pass | 100/108 | both pass |
| Z2 + lane M | 533/533 | 14/14 | 28/28 | 6/6 | pass | 101/109 | - |
| Z3 + lane G | 533/533 | 14/14 | 28/28 | 6/6 | pass | 104/112 | - |
| Z4 + lane I | 533/533 | 14/14 | 28/28 | 6/6 | pass | 104/112 | both pass |

Every red left, classified:

| red | final export | live | class |
| --- | --- | --- | --- |
| test_state_legislative_geo (1 of 25) | red | green | EXPORT-ONLY, pre-existing, not this set: sld/index.json pins the CRLF-checkout size of sld/upper/AK.json (149,572) and the eol=lf export writes the LF blob (149,571). Same red on a clean export of HEAD 3cec98524. |
| test_split_telecom_workbook | "NO TESTS RAN" | same | Not a red: a pytest-style module (bare `def test_`, since 07-23); under pytest (system Python) 1 passed on lane Z's export B. The venv has no pytest. |

Resolved by lane T: the two browser reds (both stale pins; section 1a) and test_flow_route's bare-export error
(now a named skip). The geo reds of a bare export (test_geo_v2_alignment, test_geo_v2_assign) are EXPORT-ONLY,
gitignored Census inputs, green once supplied (lane Z).

The 8 Python reds lane Z saw under the venv at Z1-Z5 are the two pre-existing ones above and six pid-holding
suites (test_analysis_data_protocol, test_desktop_launcher, test_prewarm, test_proclock,
test_startup_performance, test_warmer_process) that fail only under the venv interpreter because a venv's
python.exe starts the real interpreter as a second process (bpo-35797); Z6 (lane V2) is the fix. Lane T ran
those six (and the prewarm modules their names match) at Z5 under system Python 3.12 instead: 9/9, and no
process was left behind; at Z6 they run under the venv with the rest.

## 4. Console smoke (lane Z, on its final tree; read-only, venv, port 8860)

`smoke.py` / `smoke.cjs`; evidence `laneZ\smoke_http.json`, `smoke_browser.json`, `smoke_shots\`, `console.log`.
Lane T's changes touch no file the console serves (three test files and one doc row), so these results hold
for the refreshed final tree.

| check | result |
| --- | --- |
| `/` rendered by Jinja2 | 200; no "serving the golden index.html" line in the log; served bytes == console_page.render() (the strict door) == golden index.html (LF) |
| /api/flow FAIRSHAKE 2024 (b2676188) | 200 in 0.77 s; totals.in = counted_in = **217,423,880.52**; 25 nodes, 33 links |
| /api/evidence-network | 200; 19 edges, 87 relationships, 3 missing units (C00412791, C00824607, C00880187) |
| /api/evidence-geo (spent, 2024) | 200; layers by_state 41, by_region 4, by_zip 0, share_base, date_rule |
| /geo/v2/index.json | 200; 866 files listed; a committed tier file and a supplied detail file both served, sha256 = index |
| pmtiles Range | `Range: bytes=0-16383` -> 206, `Content-Range: bytes 0-16383/112291455`, magic PMTiles; past the end -> 416 `bytes */112291455` |
| read-only | POST /api/studio/views -> 403 |
| Chart Studio Marks strip + Flow tile | lane F's saved Flow view (Crypto 2023-2024 worksheet): strip = core.MARK_STRIP (14 tiles), Flow tile enabled and chosen, Sankey 13 nodes / 29 ribbons |
| dual-axis card | fixture data (contributions API stubbed in the browser, as lane M's client): Dual axis chip on, cards All + SUM(Selected amount) + Contributors, drawing has bar and line cards |
| map sheet + Layer control | FAIRSHAKE Spent map -> Open in Chart Studio: 2 layer cards; toolbar Layer control lists Opposition (hatch) and Spending by state, each with eye and pointer |
| PAC evidence Flow tab | FAIRSHAKE 2024: 21 nodes, 33 ribbons, heading "Where FAIRSHAKE's money came from, and where it went" |
| PAC evidence Layer control | Opposition, Spending by state, State borders |
| Graph follow-the-money | Crypto 2024: 22 nodes, 41 ribbons |
| page errors | **0** page errors and 0 console errors in all six scenes |

Found on the way (not a commit defect): in any tree other than C:\Users\pgoff\Mentat the Crypto
contributions dataset is unavailable ("Pinned report source evidence is unavailable."), because its
recovered-database manifest (`.cache/receipt-metadata-repair-20260910/crypto/mentat.db.hydration.json`)
pins an absolute path under the live .cache; the default Chart Studio load then indexed Banking (2.1 GB).
The Chart Studio scenes therefore stubbed the contributions API; lane P's saved Crypto map views could not
be opened on the export for the same reason.

## 5. The plan: six commits

### 5.1 Order, and why this is the finest split

For every file, the chronological order of its writers (receipts, UTC) must be the commit order, or a
commit would contain a state that never existed. Edges X -> Y where X wrote a file before Y did; lanes in
one cycle must share a commit (lane Z's `plan_scc.py`, `plan_scc.json`):

- E precedes everything (the earlier sessions' state is what our lanes started from).
- M wrote first on all its files -> separable (Z2), as the orchestrator expected.
- A, B, C, F, P, V form one cycle: server.py (M, F, V, P, F, P), evidence.js (B, C, F, C, F, P, F),
  evidence_geo.py (B, C, B, P, B), studio_api.json (M, P, F, P), downstream.py (B, C, B), graph_data.py and
  report_insights.py (C, A), build_industry_report.ps1 (A, V), arrival_gates_cases.json (B, A).
  H joins them: pac_evidence.py (B, H) and lane A's F13 memo reason builds on H's rule.
  "Lane P with or before lane F" is satisfied by P and F sharing Z5.
- G and I touch nothing else (G before Z5 because lane P's maps read geo v2); V2 follows V and G.
- T (lane T) wrote last, and only files whose other writers are in Z5 or earlier (METHODOLOGY.md: E, H;
  test_flow_route.py: F; the two browser suites: nobody since HEAD). Its changes re-pin and describe Z5's
  own changes, so it joins Z5 (`build_plan.py` GROUP_OF T = 5). V2 (Z6) touches none of the four files, so
  every per-file order still holds.

| commit | subject | paths | staged from working tree / from an earlier real state |
| --- | --- | --- | --- |
| Z1 | Record the 09-20..09-25 Chart Studio, query and palette work left uncommitted | 35 | 26 / 9 (the 9 shared files at their pre-lane state) |
| Z2 | Give Chart Studio Tableau-style marks cards (Marks v3, boards #50-#52) | 19 | 11 / 8 (lane M's end state of files P and F later changed) |
| Z3 | Build geo v2 map layers from the Census files with GeoPandas | 464 | 462 / 2 (geo/.gitignore with the new rule; test_geo_lookup.py before V2's docstring) |
| Z4 | Stage the previous cycle's FEC files only for the cycles a run selects | 2 | 2 / 0 |
| Z5 | Trace PAC money downstream, draw it as Sankey flows and layered maps | 118 | 116 / 2 (Start-MentatApp.ps1, mentat_python.psm1 before V2) |
| Z6 | Launch Mentat's venv Python as one process (bpo-35797) | 15 | 15 / 0 |

Trees (`plan_trees.txt`): Z1 `38420b12`, Z2 `b308b2be`, Z3 `552b7a92`, Z4 `79063e8f` (all four identical to lane
Z's), Z5 `035dbb1e` (lane Z's `a1bbae6d` + lane T's four files), Z6 `89977f4e` (= zB', the whole set in one
commit). File lists: `plan_paths_<k>.nul` (Z5 gains the two browser suites; Z1-Z4 and Z6 identical to lane Z's);
staging lists `plan_add_<k>.nul` and `plan_cacheinfo_<k>.txt`; full messages `messages\Z1..Z6.txt` (Z1 and Z5
updated for lane T); the bytes of every staged state `plan_states.zip`. Rehearsed commits: `laneT\clone` branch
zPlan `ebe10897d`..`6c12b631f`, bundled as `zPlan.bundle` (15.8 MB, requires 3cec98524, verifies against the real
repo).

Apply Z5 and Z6 together (or squash Z6 into Z5): V and V2 are one venv change. Between them the launcher
prefers the venv but still launches it as two processes, so anything that later kills "its" pid kills the
venv's launcher stub and leaves the real Python running. Measured by lane Z: under the venv, every run of
tests/test_desktop_launcher.py at Z1..Z5 left 5 console servers alive (30 in all, stopped by lane Z; their
%TEMP%\MENTAT keep/stale data roots are listed in `laneZ\orphan_data_roots.txt`); at Z6 none.

### 5.2 How to apply (both routes rehearsed; pick one)

Plain-words steps for Paul: the packet's `README.md`. Both scripts read everything from their own folder
(`$PSScriptRoot`, parameter `-Kit`), so they run from the packet folder as they are.

Route A - exact trees, no hooks (`apply_plan.ps1`): fetches `zPlan.bundle`, recreates each commit with
`git commit-tree <tested tree> -p <parent> -F messages\Zk.txt` (Paul's configured identity), moves the
branch with `git update-ref ... <new> 3cec98524`, `git read-tree <new>` (index only), `git checkout --
mentat/app/geo/.gitignore` (the only working-tree write), `git update-index -q --refresh`. Hooks do not run,
so push the mirror by hand afterwards (`git -C C:\Users\pgoff\Mentat push mirror codex/mentat-crypto`, which is
what the post-commit hook runs).

Route B - porcelain (`apply_plan_porcelain.ps1`), per commit k:

```
git -C C:\Users\pgoff\Mentat fetch --no-tags <packet>\zPlan.bundle zPlan                  # once: brings the earlier-state blobs
git -C C:\Users\pgoff\Mentat add -f --pathspec-from-file=<packet>\plan_add_k.nul --pathspec-file-nul
git -C C:\Users\pgoff\Mentat update-index --add --cacheinfo <mode>,<blob>,<path>           # each line of plan_cacheinfo_k.txt
git -C C:\Users\pgoff\Mentat commit -F <packet>\messages\Zk.txt                            # hooks run (mirror push)
git -C C:\Users\pgoff\Mentat rev-parse HEAD^{tree}                                          # must equal plan_trees.txt
```
then `git checkout -- mentat/app/geo/.gitignore` and `git update-index -q --refresh`.

Both scripts default to CHECK ONLY (branch, HEAD, no index.lock, nothing staged, mentat/app/geo/.gitignore
unedited, bundle verifies, all 632 files unchanged since they were tested) and stop on the first failure. The
geo ignore-file check is lane T's addition: the apply rewrites that one file from the commit and the file check
skips it (its commit-set hash is the committed version), so without it an edit made there after 09-26 would be
overwritten silently; with an edit in place, both scripts refuse in check mode (`laneT\negctl_geo_guard.out`).
Run from the packet folder against the real repository at 11:29 UTC and again at 11:42 UTC (after every test and
rehearsal), both check modes passed (`laneT\real_check.out` holds the 11:42 run).

Rehearsals (lane T), each script run FROM THE PACKET FOLDER with `-Repo <copy>` on a fresh depth-1 clone checked
out under the system autocrlf=true, hooks off, Paul's user.name/email, with the live bytes of the 632 files and the
410 geo v2 detail files copied in (status under mentat/ and the contracts identical, entry for entry, to the real
repo's: 94 ` M`, 945 `??`). Final kit: `laneT\simA2` (route A) and `laneT\simB2` (route B); the same passed on
`simA`/`simB` before the geo check was added. Route A: check OK, then six commits whose trees are the six tested
trees, messages equal to messages\Zk.txt, author and committer Paul Goff, parent 3cec98524, the branch moved, only
mentat/app/geo/.gitignore written, and `git status --porcelain=v1 -uall` EMPTY. Route B: the same six trees,
checked after every commit, and `git status` EMPTY (`laneT\rehearsal_A_simA2.json`, `laneT\rehearsal_B_simB2.json`).
Single-commit fallback (same final tree, no split): append lane G's lines to mentat/app/geo/.gitignore
(`laneZ\build_set.py` GEO_IGNORE_ADD), then `git add -f --pathspec-from-file=paths.nul --pathspec-file-nul`
(that is exactly zB').

### 5.3 Files mixing our hunks with the earlier sessions' hunks

The nine shared files CAN be split and need no hand-cut hunk: Z1 stages each one's real pre-lane state
(the backup the first of our lanes took), Z2/Z5/Z6 stage the lanes' states. Only two blocks carry lines
from both E and a lane (chart-studio-contributions.js and contribution-plot.js, one block each - lane M's
two "char-merge" lines); the chronological states settle them. METHODOLOGY.md line 104 is now an E+T block:
Z1 stages E's line (index v5 / parser v6, as it stood), Z5 lane T's correction. Hunk lists: lane Z's
`hunk_lists.md`. Evidence that the split is sound: Z1 and Z2 exported and tested on their own (section 3).

### 5.4 Re-pins Paul must ratify (existing test expectations changed; census lane Z's `repins.json`)

- Z1 (earlier sessions): chart-engine-r3.test.js:267 pie labels are percentages inside the pie.
- Z2 (lane M): studio_api version 2 -> 3 (studio-contract.test.js:247, test_studio_contract_examples.py:170,
  test_studio_board_browser.cjs:621-622); mark menu 26 -> 30 and folds + enc-shape/path/angle
  (test_studio_sections_freedom_browser.cjs:99,186,279); chart-studio-core.test.js:164 new types -> dot view.
- Z4 (lane I): test_runtime_inputs.py:24-51 - C-1 files follow the selection (2020 included).
- Z5: transfer index version 5 -> 6 (test_downstream_review.R:31, test_downstream_system.R:44,
  test_transfer_evidence.R:66); PAS2 parser '8' -> '9' and cross-filing identities both counted
  (test_transfer_evidence.R:192, 218-222); F11 reload counted once, 200 -> 100 / record_count 2 -> 1
  (test_transfer_graph.py:264-290); F2 blanks instead of an unresolved 100% (test_downstream_enrichment.py:
  12-39, test_downstream_review.py:67); evidence-geo contract 3 -> 4 (test_evidence_geo.py:512); receipt
  rules 5 -> 6 (test_receipt_roles.R:168); url_scope 6 -> 7 (scope.test.js:58, graph-navigation.test.js:152,
  and lane T: test_studio_strip_removed_browser.cjs:370); the Graph's estimates refusal is asserted in its
  empty candidates panel and not in the candidate note (lane T: test_console_browser.cjs:312-316); pane header
  Summary|Map|Flow|Rows (test_evidence_map_interaction_browser.cjs:231-240); the Graph no-bundle note
  (test_graph_data.py:335-337); lane M's studio-marks contract counts 14 -> 23 once F's cards join (P's 15
  controls kept apart).
- Z6 (lane V2): harness only - children launched through python_child (5 suites), test_startup_performance
  also scans tools/.
- Additive only (no expectation changed): test_contribution_http, test_district_geo, test_downstream_network,
  test_app_lazy_startup_browser, test_contribution_studio_map_browser; test_pac_evidence imports one more name;
  test_flow_route's IndustryRefunds gains a skip (lane T).

### 5.5 Recorded, not ratified (D-051) - named in the Z1 and Z5 messages

H1 (review-state memo parents), H2 (re-summarize saved PAC snapshots), H3 (FAIRSHAKE's amended bitcoin
sale proceeds); saved cash-estimate sidecars no longer match pac_cash_model.py and are withheld until
regenerated; Senate opposition listed, not hatched, on the District map; the Alaska inset scale (pre-existing);
F15 per-company gates (no approval found in the receipts - confirm); README links to two untracked audit
packets. (Lane Z's two further items are closed by lane T: METHODOLOGY's transfer row and the two browser
suites.)

### 5.6 .gitignore

- Required (in Z3): `mentat/app/geo/.gitignore` gains `v2/albers/detail/`, `v2/wgs84/z5/`, `v2/wgs84/z10/`
  (after its `!*.json`). Without it `git status` lists 410 untracked detail files forever.
- Recommended, not in the tested trees: `!audits/mentat_failings_20260915/contracts/*.json` in the root
  .gitignore, so a new contract is seen instead of needing `git add -f` (lanes C and F both hit this).
- Nothing else: the fixtures rule is a new tracked file in Z5; .cache and state are already ignored; the
  venv lives in %LOCALAPPDATA%.
- The packet folder itself: the root rules hide its `*.json`, `*.txt` and `*.jsonl` files (commit_set.json,
  plan_trees.txt, plan_cacheinfo_*.txt, messages\*.txt, the lane receipts), which the scripts need; the rest
  (.md, .ps1, .bundle, .nul, .zip) shows as untracked. Commit it only with `git add -f`, if at all.

## 6. Disagreements and risks for the orchestrator

6.1 **Do not stage with `-c core.autocrlf=false`.** The brief asked for it. Mentat's blobs are LF (1,600
i/lf, one `-text` file i/crlf); 51 files of the set are CRLF or mixed only in the working tree (lane Z's 50 +
test_console_browser.cjs). Measured by lane Z on its 631-path set, the byte-faithful commit rewrites them:
184,107 changed lines against 105,771 (collect.R 3,072/3,069 instead of 6/3; build_industry_report.ps1
1,147/1,127 instead of 21/1). Both forms were committed and exported by lane Z; the plan stages the default way
(system autocrlf=true). The choice costs nothing in behaviour: export A (the byte-faithful commit) and export B
gave the same results on every non-browser suite, and the live mirror carries A's bytes.

6.2 **Lane M is separable only chronologically.** At block level 6 of its files mix with P and F; its real
end states are still clean commits because it wrote first everywhere. **P and F (and A, B, C, H, V, T) are
not separable** without inventing states nobody ran.

6.3 Closed by lane T: the two browser suites lane Z found red on the export AND on live were stale pins; both
are re-pinned in Z5 and pass at Z5 and Z6, and the re-pinned forms fail on Z4 (section 1a).

6.4 Hermeticity: the Python suites write into the tree they run in (912 query-cache responses, 96 views,
drawer sidecars, prewarm/access.sqlite under mentat/state, `.cache/geo/geopy_cities.json`). Running them in
the live tree would write into the running consoles' caches and the prewarm ranking, so full runs used
exports and lane Z's byte mirror; lane T's one live run (IndustryRefunds, two tests) was checked against a
stat snapshot of the whole live mentat/ tree: nothing written.

6.5 Closed by lane T: test_flow_route's IndustryRefunds skips, naming the missing pinned files, instead of
erroring when the Banking workbook exists but its pinned payload under .cache does not.

## 7. Evidence index

- Lane T (`laneT\`): RECEIPT.json (hunks, specs, drift checks, live proof, plan, exports, runs, rehearsals,
  packet copy), PROGRESS.md, apply_edit.py + specs\ + backup\ (pre-write bytes of the four files), selftest.py
  (scratch run; line endings per line), drift_check.py + drift_*.json, live_proof.py/.json/.log, clone\ (zB,
  zPlan), build_set.py, build_plan.py, porcelain_lists.py, export_and_verify.py, supply_links.py,
  run_matrix.py, run_all.py/.log, runs\, export_plan_Z4/Z5/Z6\ (+ _verify.json, _supplied.json), negctl_Z4.json,
  make_kit.py + kit\, sim_prepare.py/.json, simA\, simB\, simA2\, simB2\, simC\, rehearse.py,
  rehearsal_A/B.out/.json (first round), rehearsal_A_simA2 / rehearsal_B_simB2 .out/.json (final kit),
  negctl_geo_guard.out, real_check.py/.out/.json, stage_durable.py, durable_stage\, durable.json.
- Lane Z (`laneZ\`): inventory (status_porcelain.txt, inventory.py/json, chains.json, hunks.py/json,
  hunk_lists.md, plan_scc.json, attribution_table.md, ignored_scan.json, repins.json,
  numstat_autocrlf_true/false.txt, ls_files_eol_*.txt), proof (clone\ zA/zB/zPlan, export_A\, export_B\,
  export_HEAD\, export_plan_Z1..Z5\, live_mirror\, runs\, runs_summary.json), console smoke, BRAIN_DRAFT.md,
  orphan_data_roots.txt. Lane Z's kit (zPlan.bundle, tip `77d64bfce`) is superseded: do not apply it.
- The packet (`C:\Users\pgoff\Mentat\outputs\pac-map-downstream-viz-20260926\`): README.md, this plan, the
  refreshed kit, and every lane's RECEIPT/PROGRESS files under lanes\.
