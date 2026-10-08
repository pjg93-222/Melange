# Lane I - F16: VERSION 6 FEC transfer index for cycle 2020 (production Mentat)

Approved by Paul 2026-09-26 ("Approve ... F16"). Build a cache (and possibly register a source); no commit, no git writes.
Glass Box run id: lane-i-20260926, source transfer-index-2020.

## Ground truth read before acting (2026-09-26 02:1x-02:26 -0400)
- Live writer mentat/tools/fec_transfer_graph.py sha256 75b7df47...0e53 = lane A's landed VERSION 6 count_all (RECEIPT land 20:53:26).
- Live reader mentat/R/fec_transfer_graph.R sha256 9341143f...19a5 = lane A's F12 land (02:03:35).
- Active FEC source: mentat/inputs/active_fec_sources.json -> C:\Users\pgoff\Mentat\mentat\.cache\repair-20260908-inputs (path only, no cycle list).
- R reader finds a cycle purely by path: <fec_beneficiary>/oth<yy>/transfer-info.json (+ itoth.txt hash check, edges sha check).
- fec_transfer_context: previous cycle of 2022 = 2020; previous stops = candidate_links[cycle == 2020 & A/P].
- export_crypto_spending_data.R:625 reads candidate_links for supported_cycles (2022/2024/2026) ONLY -> no 2020 stops in the export.
- active_fec_sources.json is git-IGNORED (.gitignore:68 mentat/inputs/), not tracked; D-048's tracked list does not name it.
- Sandbox (READ-ONLY): C:\melange-data\mentat_cycle_2020\data\fec-2020; oth20/itoth.txt 1,447,788,927 B sha d40374bf...834e,
  FEC Last-Modified Sun, 29 Dec 2024 22:09:53 GMT, downloaded 2026-09-25T21:39:40Z. Its v5a index + trio are DERIVED: not copied.
- Free RAM 9.86 GB, C: free 90 GB at 02:26.

## Plan
1. copy_raw.py: oth20/itoth.txt + source-receipt.json, ccl20/ccl.txt + source-receipt.json (sha-verified, atomic, RECEIPT).
   Not copied: cn20, pas220, cm20, leadership2020.csv (nothing on the 2020 carryover path reads them).
2. build_2020.py via wait_then_build.py (>= 3 GB free): live writer, cache pair beside itoth.txt, staged publish.
3. verify + probe; measure 2022 carryover from staging; install trio (edges, current, info last) if sound.
4. Console check (app/downstream.py reads saved snapshots only?).

## Log
- 02:29 copy_raw.py copy: oth20/itoth.txt (1,447,788,927 B, sha d40374bf335de015875f1d27dd62754c663de366bf648466e9a427e1a1ec834e) and
  ccl20/ccl.txt (289,255 B, sha e997b0646630f33bfb1953a1d731fed3e21deb67bdfb47cfff17b5e03f3d6712), each with its source-receipt.json
  byte-exact; source == receipt == manifest == copy; source re-hashed after copy (no drift); mtimes kept (2026-09-25 17:39).
- 02:30:51 wait_then_build.py: 4.87 GB free -> build_2020.py started (live writer, cache pair beside itoth.txt, staged publish).
  Cache name transfer-index-v6a-2020-d40374bf335de015875f-da097f766ede: header signature da097f766ede = the 2022-2026 builds'.
- FINDING (lane A's code, not edited): the export passes NO 2020 stops to the carryover walk (candidate_links read for
  supported_cycles only). measure_2022.R quantifies before / export / rule variants from the staged index before install.
- 02:37:41 build exit 0 in 406.3 s, peak WS 1.145 GB / private 1.24 GB. Cache pair in production oth20 (only files added);
  trio staged in laneI/staged_index_v6/oth20. VERSION 6 count_all; source_sha256 d40374bf... = copied itoth = receipt.
  184,307 edges (180,186 positive), 1,553,493 records, net $4,051,540,225.00, positive $4,055,027,904.00; unresolved 9 rows,
  7 sources, $57,700 withheld; unresolved_all_sources false. Header signature da097f766ede (= 2022-2026 builds).
  Cross-check vs the sandbox's own v5a (read-only): same 184,307 edges; v6 is $43,000 lower = 17 reload rows (F11).
- 02:39 probe_2020.R (live reader) on the staged dir: 2020 "indexed", 184,307 edges; SLF 2020 outflow $166,842,500 to 9.
- 02:40-02:47 measure_2022.R (staged 2020, production 2022, lane A crypto_roots 72): 
  before: unknown, 72 missing, 9,243 edges $915,434,878.00 (= lane A's F12 export exactly)
  export-as-written (no 2020 stops): known, 2,314 carryover committees, 48,052 edges $1,558,956,637.00
  rule (ccl20 P/A stops, = real_gates.R/.py): known, 777 carryover committees, 23,295 edges $1,203,117,884.00
  (first run's seed lists were empty: fec_transfer_network returns no `seeds`; fixed to gate_source == "carryover"; rerun.)
- 02:5x install_2020.py check: no problems; production oth20/itoth.txt re-hashed d40374bf... = info source_sha256 = receipt.
  busy() refined: the sandbox chain names production only for the shared fec-api-budget.sqlite (not a blocker); lane
  scripts that open the active source by an in-script path (lane A's f15 bench, running now) are invisible to it.
- Side effects of the raw copy ALONE (trio not installed): build_industry_report.ps1:475 fingerprints every itoth.txt,
  transfer-*.json/csv and source-receipt.json under the active source by full SHA256 (Get-CombinedFingerprint :215), so
  every industry's next report build is a cache miss and hashes +1.45 GB; enrich_downstream.py:351 lists every
  */source-receipt.json in source_freshness, so payloads gain oth 2020 and ccl 2020 rows. Export numbers unchanged
  until transfer-info.json is installed (reader: missing_transfer_source).
- Rerun (seeds fixed): export-as-written 2,314 seeds, of which 987 are 2022 P/A candidate committees and 1,118 are 2020
  P/A candidate committees -> the walk starts from candidate committees. DECISION: HOLD the install (trio staged,
  install_2020.py ready); orchestrator rules.
- 03:0x R == Python (real_gates_2020.py, live arrival_gates): identical gate sets, rule 1,522 gates / 777 seeds,
  no-stops 3,418 / 2,314 (parity_r_python_2022.json). Rule seeds in 2022 P/A: 2; in 2020 P/A: 0.
- Console (console_carry.py): saved units 2022:12, 2024:15, 2026:8 (no 2020). snapshot_view FAIRSHAKE 2024 carryover
  unknown (missing 2022 unit); SLF 2022 unknown (missing 2020 unit). flow_data.flow SLF 2022 raises
  ValueError "Negative flow donor:WEIRMAN ROBERT -> committee:C00571703 (receipt)" (not lane I's; reported).
- test_transfer_index_contract: 5/5 OK. Sandbox untouched (sizes, mtimes). git: lane I paths all under ignored mentat/.cache/.
- Also found: tools/runtime_inputs.py regex (22|24|26) treats oth20/ccl20 as shared -> console runs copy them always.
- END: HELD. Install = python install_2020.py install ; revert = python install_2020.py uninstall.

## Follow-up 1 (coordinator 03:0x): runtime_inputs.py
- mentat/tools/runtime_inputs.py (+ tests/test_runtime_inputs.py): committed 97eaa7581 / b9ad2a56f / 236a42058; only caller
  app/server.py:94,1524 (console runtime staging). OTHER EDITOR: the Sector-growth session's worktree
  C:\Users\pgoff\Mentat-wt\cycles-2020 (branch claude/mentat-cycles-2020, uncommitted) changes the same regex lines
  (identical text to mine) + the supported-cycle check (config/cycles.json via cycle_config) + INSTALL_HINT.
- edits/e1_runtime_inputs.py staged hunk-exact; test_staged.py: new/new 9 OK; old module + new tests FAIL (12 F, 3 E);
  new module + old test FAIL 4 (it pinned "files exist iff selected"; C-1 ccl/oth now follow a selection) -> test updated.
- 03:1x land.py land: runtime_inputs.py ebe6040e -> 896eabaf, test f216fa8d -> ac84671c; PURE_LF kept; backups laneI/backup.
  Live: test_runtime_inputs 9/9 OK; test_collection_console 39/39 OK.
- Real source, per selection (real_selection_check.txt): 2024-only no longer carries oth20/ccl20, carries oth22/ccl22;
  2026-only +2.16 GB (oth24 incl. its 3.28 GB itoth.txt); 2022+2026 +3.5 GB (per-cycle C-1 adds 2024).
- build_industry_report.ps1:475: over-inclusive (all cycles' itoth/transfer files + all receipts), never stale -> not
  plainly wrong; one-time miss; recurring +~2 GB hashed per build; ccl<C-1>/ccl.txt covered only via its receipt.

## Follow-up 2: wait for lane A's C-1 stops fix, then install + re-measure
- 03:1x lane A STAGED (not landed) F15 + F13 memo-reason at 03:01:51 (fec_transfer_graph.R 3ff17573, fec_beneficiary.R
  a838bda9, export 97ca7803); export line 625 (candidate_links for supported_cycles) unchanged in that stage -> not the fix.
  Lane A's export_crypto_f15 (mirror_f15pre, pid 5500) is READING production fec_beneficiary now -> no install.
- watch_laneA.py armed (background; exits on any RECEIPT.json / PROGRESS.md change). laneA/PROGRESS.md absent so far.
- 03:25 lane A LANDED F15 + F13 memo reason (fec_transfer_graph.R 3ff17573, export 97ca7803, fec_beneficiary.R a838bda9). NOT the C-1 stops fix: export:636-639 still reads candidate_links for supported_cycles; fec_transfer_graph.R:427 previous_stops from it. Watching again.
- 03:27 lane A STAGED the C-1 stops fix (fec_transfer_graph.R d45a4491, with F14): fec_transfer_context reads the previous
  cycle's ccl itself when candidate_links lack it; unreadable -> previous_index "missing_candidate_links", carryover unknown.
- 03:3x DRY RUN (scratch copy: staged 2020 trio + production oth22 edges/info + ccl20; lane A's STAGED R; export-style
  candidate_links 2022-2026): known, 777 committees, 0 missing, 23,295 edges, $1,203,117,884.00 = rule figures exactly.
- 03:31:52 lane A LANDED the fix (fec_transfer_graph.R d45a4491 = the tree I dry-ran; writer 878b504e changes reachable()
  only (F14); transfer_index/publish_index and VERSION 6 count_all unchanged -> the 2020 index stays valid). Lane A suites
  03:33 all green. Lane A's own f16 check (its dir2022 copy of my staged trio): fix 777 / 23,295 / $1,203,117,884.
- 03:33:57 install_2020.py install REFUSED (guard worked): lane A f16/carryover_measure.R reading production (2024 runs).
  wait_install.py armed: installs after 3 quiet checks 20 s apart.
- 03:45:13 INSTALLED (install_2020.py install; no production reader running at 03:44:59; edges, current, info last;
  sha verified). uninstall-check: ready (all three match the install record).
- NOTE: production oth20/transfer-edges.csv is a HARD LINK shared with lane A's f16/dir2022/oth20/transfer-edges.csv
  (lane A linked my staged file for its dry run; os.replace moved that inode into production). Reads are harmless;
  lane A must delete its name (unlink), never write into it.
- 03:45-03:47 probe_2020.R on production: indexed, raw_source_available TRUE (1.45 GB hash checked), 184,307 edges.
  measure_2022_fixed.R (live tree: fec_transfer_graph.R d45a4491, fec_beneficiary.R a838bda9; export-style
  candidate_links 2022-2026): known, 777 carried over, 0 missing, previous_index indexed, 23,295 edges,
  $1,203,117,884.00 -> matches the rule figures exactly.
