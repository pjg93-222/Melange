# Lane Z - commit plan for the uncommitted Mentat work (2026-09-26)

Repo `C:\Users\pgoff\Mentat` (a worktree of the Melange Systems repository), branch `codex/mentat-crypto`,
HEAD `3cec985249b098478868b8729e33b5b4ab31752e`. Lane Z made no write, no git write and no stash in that
repo; everything below was done in `laneZ\clone`, `laneZ\simclone*` and scratch folders. Nothing is applied:
the commits are Paul's to make.

## 0. Bottom line

- The whole uncommitted set - 92 modified tracked files, 538 new files, and lane G's geo ignore rule
  (631 paths) - committed together in a throwaway clone, exported with D-048's dials and byte-checked
  (1,121/1,121 files equal their blobs), is a working tree and a working console. Clean export: node
  619/619, cjs 14/14, R 32/32, PowerShell 6/6, render --check, Python 128/130 modules (1,759 tests) with
  gitignored inputs supplied by name, browser 48/50; the read-only console passed every smoke check with
  zero page errors. The live tree's own bytes (a mirror) give the same results.
- Four reds, none from a missing file: two browser suites that no lane re-pinned (red on live too,
  introduced by the Z5 lanes - section 6.3), and two pre-existing (an EOL size pin that fails on any LF
  export of HEAD, and a pytest-style module unittest cannot see).
- Six commits are proposed, each made only of byte states that really existed (the lanes' own pre-write
  backups), in the only order those states allow. Both apply routes were rehearsed end to end on a copy of
  Paul's checkout and produced the six tested trees exactly, with `git status` clean afterwards.
- Stage with the DEFAULT add (system `core.autocrlf=true`), not `-c core.autocrlf=false`: see section 6.1.

## 1. Inventory (git status --porcelain=v1 -uall at 3cec98524: 92 ` M`, 2,010 `??`)

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

(A file counts once per owner; `attribution_table.md`, `plan_scc.json` sequences.)

- 31 files carry more than one owner. Nine mix E with our lanes (METHODOLOGY.md, README.md,
  chart-studio-contributions.js, chart-studio.css, chart-studio.js, charts.js, contribution-charts.js,
  contribution-plot.js, graph.js); 16 mix two or more of our lanes. Every change block and its owners:
  `hunk_lists.md` (from `hunks.json`). Chains were checked write by write: each write's pre-image is the
  previous write's result, and no write by anyone outside the receipts was found once lane A's `stage`
  rows (its scratch copies, not live writes) were set aside; the one unmatched step is index.html,
  re-rendered by lane P's `render_console --write` (in its receipt). The files only E touched all have
  mtimes at or before 09-25 03:53, before the first lane wrote.
- New files our lanes created: 67 (list with `git check-ignore -v` in `ignored_scan.json`). Three are
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
  growth lane), `.impeccable/`, `DESIGN.md`, `PRODUCT.md`.

## 2. The proof (D-048 / DE-031)

- `laneZ\clone`: `git clone --no-local --depth 1 --branch codex/mentat-crypto file:///C:/Users/pgoff/Mentat`
  (origin removed, no hooks), at 3cec98524. The 630 live files copied byte-for-byte (sha256 before/after
  the copy, `commit_set.json`) plus lane G's rule appended to `mentat/app/geo/.gitignore` in the clone only.
- Two commits of the same set: zA `7b0fd9f45` (`-c core.autocrlf=false add -f`, byte-faithful) and zB
  `9a38eaa73` (`-c core.autocrlf=true add -f`, the repo's i/lf convention). They differ only in the line
  endings of 50 files.
- Exports: `git -c core.autocrlf=false -c core.eol=lf archive <sha> mentat audits/mentat_failings_20260915/contracts`
  to a tar, extracted: export_A and export_B each 1,121 files, 0 missing, 0 extra, 0 blob mismatches
  (`export_A_verify.json`, `export_B_verify.json`). export_A = the live bytes for all 631 paths; export_B =
  581 identical, 50 differing only in CRLF.
- No committed `eol=` attribute exists (root .gitattributes has only `-text`/`binary`), so D-048's caveat
  does not bite.
- No drift: the real repo's 630 files still had the tested sha256 mid-run and again at 06:39 on 09-26
  (apply_plan.ps1 check mode, read-only); branch and HEAD unchanged; `git status` still 92 ` M` / 2,010 `??`.
  Re-run the check mode immediately before applying: it refuses if anything moved.

## 3. Suites on the clean export, against live

Runner `run_matrix.py`: one process per suite, output to a file, bounded wait + tree kill, >= 3 GB free
before each suite, PYTHONDONTWRITEBYTECODE=1, MENTAT_PYTHON = the venv, MENTAT_UI_OUTPUT = laneZ\ui\<run>\<suite>,
browser suites strictly one at a time. Python under C:\Users\pgoff\AppData\Local\Mentat\venv. Results:
`runs\<label>\results.json` + logs; totals `runs_summary.json`.

Inputs supplied BY NAME to the export (copies, `export_B_supplied.json`; nothing in the commit): .cache/geo
(Census), the FAIRSHAKE and SLF saved snapshots, the Banking and Crypto pinned report payloads, the geo v2
detail tiers, .cache/basemap, the FEC committee and candidate masters, and inputs/active_fec_sources.json
(a path into the live .cache, read-only: 22,845 live files in that source, inputs and state had identical
size and mtime before and after, `live_snapshot_*.json`).

| tree | node --test | cjs | R | PowerShell | render --check | Python modules (tests) | browser |
| --- | --- | --- | --- | --- | --- | --- | --- |
| export B, bare | 619/619 | 14/14 | 32/32 | 6/6 | pass | 125/130 (1,749; 41 skipped) | - |
| export B, inputs supplied | - | - | - | - | - | 128/130 (1,759; 16 skipped; with the FEC source pointer 0 skips in its 5 readers) | 48/50 |
| live mirror (byte copy of the live mentat/ + contracts, same inputs) | 619/619 | 14/14 | 32/32 | 6/6 | pass | 129/130 (1,759; 15 skipped; 0 fail) | the 2 export reds re-run: both red |
| export A (byte-faithful commit, same inputs minus the FEC masters) | 619/619 | 14/14 | 32/32 | 6/6 | pass | 128/130 (1,759; 18 skipped; same 2 reds) | - |

Every red, classified:

| red | export B | live | class |
| --- | --- | --- | --- |
| test_flow_route, test_geo_v2_alignment, test_geo_v2_assign (bare) | red | green | EXPORT-ONLY, gitignored inputs (the Banking pinned payload under .cache/industry-report; the Census zips under .cache/geo); green once supplied by name (31/31, 9/9, 10/10). Nothing is missing from the commit. |
| test_state_legislative_geo (1 of 25) | red | green | EXPORT-ONLY, pre-existing, not this set: sld/index.json pins the CRLF-checkout size of sld/upper/AK.json (149,572) and the eol=lf export writes the LF blob (149,571). Same red on a clean export of HEAD 3cec98524. |
| test_split_telecom_workbook | "NO TESTS RAN" | same | Not a red: a pytest-style module (bare `def test_`, since 07-23); under pytest (system Python) 1 passed on export B. The venv has no pytest. |
| browser test_studio_strip_removed_browser (step 5 of 5) | red | red (mirror) | BOTH - stale url_scope v6 pin (6.3); passes at Z4, fails from Z5 |
| browser test_console_browser (line 312) | red | red (mirror) | BOTH - the estimates refusal moved to the Graph's empty panel (6.3); passes at Z4, fails from Z5 |

No FLAKE: no red changed between runs.

Intermediate commits of the plan, each exported and run the same way (`runs\plan_Z1..Z5`):

| commit | node --test | cjs | R | PS | render | Python modules | the two browser reds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Z1 earlier sessions | 461/461 | 14/14 | 28/28 | 6/6 | pass | 100/108 | both pass |
| Z2 + lane M | 533/533 | 14/14 | 28/28 | 6/6 | pass | 101/109 | - |
| Z3 + lane G | 533/533 | 14/14 | 28/28 | 6/6 | pass | 104/112 | - |
| Z4 + lane I | 533/533 | 14/14 | 28/28 | 6/6 | pass | 104/112 | both pass |
| Z5 + A,B,C,F,H,P,V | 619/619 | 14/14 | 32/32 | 6/6 | pass | 121/129 | both fail |
| Z6 = final (export B) | 619/619 | 14/14 | 32/32 | 6/6 | pass | 128/130 | 48/50 browser |

The 8 Python reds of Z1-Z5 are the same 8 every time: the two pre-existing ones above, and six pid-holding
suites (test_analysis_data_protocol, test_desktop_launcher, test_prewarm, test_proclock,
test_startup_performance, test_warmer_process) that fail only under the venv interpreter because a venv's
python.exe starts the real interpreter as a second process (bpo-35797). Under system Python 3.12 all six
pass at Z1, Z2, Z3, Z4 and Z5 (9/9 modules each, `runs\plan_Z*_syspy`); Z6 (lane V2) is the fix, and at
Z6 they pass under the venv too.

## 4. Console smoke on the clean export (read-only, venv, port 8860)

`smoke.py` / `smoke.cjs`; evidence `smoke_http.json`, `smoke_browser.json`, `smoke_shots\`, `console.log`.
Console: `export_B\mentat\app\server.py --read-only --port 8860 --data-root laneZ\console-data`,
MENTAT_PREWARM=0; killed afterwards (port free, no lane Z process left).

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
one cycle must share a commit (`plan_scc.py`, `plan_scc.json`):

- E precedes everything (the earlier sessions' state is what our lanes started from).
- M wrote first on all its files -> separable (Z2), as the orchestrator expected.
- A, B, C, F, P, V form one cycle: server.py (M, F, V, P, F, P), evidence.js (B, C, F, C, F, P, F),
  evidence_geo.py (B, C, B, P, B), studio_api.json (M, P, F, P), downstream.py (B, C, B), graph_data.py and
  report_insights.py (C, A), build_industry_report.ps1 (A, V), arrival_gates_cases.json (B, A).
  H joins them: pac_evidence.py (B, H) and lane A's F13 memo reason builds on H's rule.
  "Lane P with or before lane F" is satisfied by P and F sharing Z5.
- G and I touch nothing else (G before Z5 because lane P's maps read geo v2); V2 follows V and G.

| commit | subject | paths | staged from working tree / from an earlier real state |
| --- | --- | --- | --- |
| Z1 | Record the 09-20..09-25 Chart Studio, query and palette work left uncommitted | 35 | 26 / 9 (the 9 shared files at their pre-lane state) |
| Z2 | Give Chart Studio Tableau-style marks cards (Marks v3, boards #50-#52) | 19 | 11 / 8 (lane M's end state of files P and F later changed) |
| Z3 | Build geo v2 map layers from the Census files with GeoPandas | 464 | 462 / 2 (geo/.gitignore with the new rule; test_geo_lookup.py before V2's docstring) |
| Z4 | Stage the previous cycle's FEC files only for the cycles a run selects | 2 | 2 / 0 |
| Z5 | Trace PAC money downstream, draw it as Sankey flows and layered maps | 116 | 114 / 2 (Start-MentatApp.ps1, mentat_python.psm1 before V2) |
| Z6 | Launch Mentat's venv Python as one process (bpo-35797) | 15 | 15 / 0 |

File lists: `plan_paths_<k>.nul`; staging lists `plan_add_<k>.nul` and `plan_cacheinfo_<k>.txt`; trees
`plan_trees.txt`; full messages `messages\Z1..Z6.txt`; the bytes of every staged state `plan_states\`.
Rehearsed commits: `laneZ\clone` branch zPlan `a021c8b7b`..`77d64bfce`, bundled as `zPlan.bundle`
(15.8 MB, requires 3cec98524, verifies against the real repo). The Z6 tree `403d33eb807d` is identical to
zB's tree (the fully tested one).

Apply Z5 and Z6 together (or squash Z6 into Z5): V and V2 are one venv change. Between them the launcher
prefers the venv but still launches it as two processes, so anything that later kills "its" pid kills the
venv's launcher stub and leaves the real Python running. Measured: under the venv, every run of
tests/test_desktop_launcher.py at Z1..Z5 left 5 console servers alive (30 in all, stopped by lane Z; their
%TEMP%\MENTAT keep/stale data roots are listed in `orphan_data_roots.txt`); at Z6 none.

### 5.2 How to apply (both routes rehearsed; pick one)

Route A - exact trees, no hooks (`apply_plan.ps1`): fetches `zPlan.bundle`, recreates each commit with
`git commit-tree <tested tree> -p <parent> -F messages\Zk.txt` (Paul's configured identity), moves the
branch with `git update-ref ... <new> 3cec98524`, `git read-tree <new>` (index only), `git checkout --
mentat/app/geo/.gitignore` (the only working-tree write), `git update-index -q --refresh`. Hooks do not run,
so push the mirror by hand afterwards.

Route B - porcelain (`apply_plan_porcelain.ps1`), per commit k:

```
git -C C:\Users\pgoff\Mentat fetch --no-tags <laneZ>\zPlan.bundle zPlan                  # once: brings the earlier-state blobs
git -C C:\Users\pgoff\Mentat add -f --pathspec-from-file=<laneZ>\plan_add_k.nul --pathspec-file-nul
git -C C:\Users\pgoff\Mentat update-index --add --cacheinfo <mode>,<blob>,<path>          # each line of plan_cacheinfo_k.txt
git -C C:\Users\pgoff\Mentat commit -F <laneZ>\messages\Zk.txt                            # hooks run (mirror push)
git -C C:\Users\pgoff\Mentat rev-parse HEAD^{tree}                                         # must equal plan_trees.txt
```
then `git checkout -- mentat/app/geo/.gitignore` and `git update-index -q --refresh`.

Both scripts default to CHECK ONLY (branch, HEAD, no index.lock, nothing staged, bundle verifies, all 630
files unchanged since lane Z copied them) and stop on the first failure. Rehearsals: `simclone` (route A)
and `simclone2` (route B), each a fresh clone checked out under autocrlf=true with the live bytes copied in:
six commits, tree after each = the tested tree, final `git status --porcelain -uall` empty.
Single-commit fallback (same final tree, no split): `git add -f --pathspec-from-file=laneZ\paths.nul
--pathspec-file-nul` after appending the three lines to mentat/app/geo/.gitignore (that is exactly zB).

### 5.3 Files mixing our hunks with the earlier sessions' hunks

The nine shared files CAN be split and need no hand-cut hunk: Z1 stages each one's real pre-lane state
(the backup the first of our lanes took), Z2/Z5/Z6 stage the lanes' states. Only two blocks carry lines
from both E and a lane (chart-studio-contributions.js and contribution-plot.js, one block each - lane M's
two "char-merge" lines); the chronological states settle them. Hunk lists: `hunk_lists.md`. Evidence that
the split is sound: Z1 and Z2 exported and tested on their own (section 3).

### 5.4 Re-pins Paul must ratify (existing test expectations changed; census `repins.json`)

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
  rules 5 -> 6 (test_receipt_roles.R:168); url_scope 6 -> 7 (scope.test.js:58, graph-navigation.test.js:152);
  pane header Summary|Map|Flow|Rows (test_evidence_map_interaction_browser.cjs:231-240); the Graph no-bundle
  note (test_graph_data.py:335-337); lane M's studio-marks contract counts 14 -> 23 once F's cards join
  (P's 15 controls kept apart).
- Z6 (lane V2): harness only - children launched through python_child (5 suites), test_startup_performance
  also scans tools/.
- Additive only (no expectation changed): test_contribution_http, test_district_geo, test_downstream_network,
  test_app_lazy_startup_browser, test_contribution_studio_map_browser; test_pac_evidence imports one more name.

### 5.5 Recorded, not ratified (D-051) - named in the Z1 and Z5 messages

H1 (review-state memo parents), H2 (re-summarize saved PAC snapshots), H3 (FAIRSHAKE's amended bitcoin
sale proceeds); saved cash-estimate sidecars no longer match pac_cash_model.py and are withheld until
regenerated; Senate opposition listed, not hatched, on the District map; the Alaska inset scale (pre-existing);
F15 per-company gates (no approval found in the receipts - confirm); README links to two untracked audit
packets; METHODOLOGY's transfer row (index v5 / parser v6) is stale after Z5 (v6 / parser 9, F11);
the two browser suites left un-re-pinned (6.3).

### 5.6 .gitignore

- Required (in Z3): `mentat/app/geo/.gitignore` gains `v2/albers/detail/`, `v2/wgs84/z5/`, `v2/wgs84/z10/`
  (after its `!*.json`). Without it `git status` lists 410 untracked detail files forever.
- Recommended, not in the tested trees: `!audits/mentat_failings_20260915/contracts/*.json` in the root
  .gitignore, so a new contract is seen instead of needing `git add -f` (lanes C and F both hit this).
- Nothing else: the fixtures rule is a new tracked file in Z5; .cache and state are already ignored; the
  venv lives in %LOCALAPPDATA%.

## 6. Disagreements and risks for the orchestrator

6.1 **Do not stage with `-c core.autocrlf=false`.** The brief asked for it. Mentat's blobs are LF (1,600
i/lf, one `-text` file i/crlf); 50 files of the set are CRLF or mixed only in the working tree. The
byte-faithful commit rewrites them: 184,107 changed lines against 105,771 (collect.R 3,072/3,069 instead of
6/3; build_industry_report.ps1 1,147/1,127 instead of 21/1). Both forms were committed and exported; the
plan stages the default way (system autocrlf=true). The choice costs nothing in behaviour: export A
(the byte-faithful commit) and export B give the same results on every non-browser suite (section 3),
and the live mirror carries A's bytes.

6.2 **Lane M is separable only chronologically.** At block level 6 of its files mix with P and F; its real
end states are still clean commits because it wrote first everywhere. **P and F (and A, B, C, H, V) are not
separable** without inventing states nobody ran.

6.3 **Two browser suites are red on the export AND on live (BOTH), both stale pins that no lane re-ran;
both pass at Z1 and first fail at Z5.** They need a one-line re-pin each (or Paul decides the old
behaviour must come back):
- `tests/test_studio_strip_removed_browser.cjs:368` asserts `url_scope.version == 6`; lane F moved
  url_scope to v7 (adds only `<pane>.flow`) and re-pinned scope.test.js and graph-navigation.test.js but not
  this suite. Step 5 of 5 fails: "url_scope is v6 ... 7 !== 6".
- `tests/test_console_browser.cjs:312` waits for the estimates-mode refusal "Saved estimates cover the
  whole industry..." in `#graph-candidate-note`. Lane C's Graph change (empty-panel reason) now shows that
  sentence in the Graph's empty panel and leaves the candidate note empty; a probe at the failing step read
  resultsHidden false, mode estimates, candidate note "", empty panel "Saved estimates cover the whole
  industry. Select all companies, all levels and all giving to view them." The refusal still reaches the
  reader; only its place moved. (Lane M saw this red in live on 09-25 22:40 and ascribed it to another
  lane's Graph work.)

6.4 Hermeticity: the Python suites write into the tree they run in (912 query-cache responses, 96 views,
drawer sidecars, prewarm/access.sqlite under mentat/state, `.cache/geo/geopy_cities.json`). Running them in
the live tree would have written into the running consoles' caches and the prewarm ranking, so the "live"
run used a byte mirror of the live mentat/ tree (section 3).

6.5 test_flow_route's IndustryRefunds errors (not skips) when the Banking workbook exists but its pinned
payload under .cache does not - a clean checkout on this machine hits it. Suggest skipping on the pinned
source too (lane F's test).

## 7. Evidence index (all under laneZ\)

- Inventory: status_porcelain.txt, inventory.py/json, chains.json, hunks.py/json, hunk_lists.md,
  plan_scc.json, attribution_table.md, ignored_scan.json, repins.json, numstat_autocrlf_true/false.txt,
  ls_files_eol_*.txt.
- Proof: commit_set.json, paths.nul, paths_excluded.json, clone\ (zA, zB, zPlan), export_A\, export_B\,
  export_HEAD\, export_plan_Z1..Z5\, live_mirror\, export_*_verify.json, export_B_supplied.json,
  live_snapshot_*.json, runs\<label>\results.json + logs, runs_summary.json, ui\<label>\.
- Console: smoke.py, smoke.cjs, smoke_http.json, smoke_browser.json, smoke_shots\, console.log,
  make_probe.py (the console-browser probe).
- Apply kit (copy it somewhere durable before this session's scratchpad is purged): zPlan.bundle,
  apply_plan.ps1, apply_plan_porcelain.ps1, messages\Z1..Z6.txt, commit_set.json, plan_trees.txt,
  plan_add_*.nul, plan_cacheinfo_*.txt, plan_paths_*.nul, plan_states\ (the staged bytes, for review).
  Rehearsals: simclone\ (route A), simclone2\ (route B), plan_build.json.
- BRAIN_DRAFT.md: two DEADENDS drafts (autocrlf=false commit; live-tree suite runs), a D-048 caveat, a
  STATE bullet - for Paul to apply.
- orphan_data_roots.txt: temp data roots of the 30 test consoles lane Z stopped.
