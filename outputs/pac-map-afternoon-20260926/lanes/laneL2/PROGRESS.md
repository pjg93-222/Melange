# Lane L2 - leftovers (2026-09-26) - run id lane-l2-20260926

Repo C:\Users\pgoff\Mentat, branch codex/mentat-crypto, HEAD fadd2c751. No git writes. Every repo write went
through apply_edits.py (spec + sha256 guard + backup + atomic replace + per-line EOL check), install_geo.py
(28 generated geo files, same guards) or create_file.py (one new test). RECEIPT.json lists 42 files, each
with its sha before and after and its backup; all 42 were re-hashed at the end and are still as written.

## Status: DONE (6 of 6)

1. README.md:151 - index v5 / parser v6 -> v6 / v9 (fec_transfer_graph.py:21 VERSION=6,
   fec_beneficiary.R:365 parser "9"). Line kept LF. Spec specs/s1_readme_151.json.
2. METHODOLOGY.md:3 - the header numbers the standard itself (0c3234e17 created it as "version 5,
   2026-09-12" while the body said index v3). Now: "Version 5 of this standard, dated September 12, 2026;
   last revised September 26, 2026. The OTH transfer index and PAS2 parser versions named below are the
   software's own and are numbered separately." Version number kept (a Version 6 is Paul's call). CRLF kept.
3. Strip suite temp folders - cause measured: venv launcher (bpo-35797) + server cwd = report folder + Node
   24 rmSync EPERM with no effective retry (rmsync_mechanism.out: threw after 1 ms). cleanupPath now retries
   with real waits and the finally awaits it. Runs: venv x2 pass, forced fail (bad channel) exit 1, system
   python pass - 0 folders left each time; pre-fix venv runs left one each (2 of 2). Removed 10 EMPTY
   %TEMP%\mentat-strip-reports-* folders (none had files).
4. Alaska inset - cause: build_district_geo.Albers did not wrap lon - l0; the Near Islands (east of 180)
   projected to the far side of the cone and the Alaska fit shrank to 254.24 (0.2363 x). Wrap added in
   build_district_geo.Albers, build_geo_layers.Frame.project and map-layers.js projectFrame; FRAME carries
   the new placement (376.541954 = 0.35 x 1075.834155, translate 147.942585, 565.23175). Rebuilt in scratch
   mirrors (geo/base = committed tools reproduce every shipped old-format file byte for byte; geo/fixed =
   Alaska-only differences), installed 7 old + 21 v2 files. National county.json needed
   build_geo_layers.simplify_regions (NW Hawaiian Islands overlap the enlarged Alaska -> per-region coverage,
   all non-Alaska counties byte-identical). d3 check: same shape and scale, constant offset (-15.707, +46.6).
   PNGs in png\ (state before/after + insets, county before/after).
5. Chart Studio busy canvas - lane P's report ("a stale render never clears the busy mark it set").
   Reproduced on a Data source switch (probe_busy_prefix.json: aria-busy true, opacity .45, pointer-events
   none). Fix in chart-studio.js: the render records canvas.__busyTicket; a stale render clears the mark it
   still owns. New suite tests/test_studio_busy_mark_browser.cjs 4/4; fails at step 2 on the pre-fix script.
6. C-1 raw copy - nothing to change: runtime_inputs.py stages only C-1 ccl/oth; the raw itoth.txt lets
   fec_transfer_index_read catch a stale C-1 index. test_runtime_inputs 9/9. Merge risk: the peer worktree
   Mentat-wt\cycles-2020 has a runtime_inputs.py without the C-1 rule.

## Tests (targeted; the full sweep is a later lane's)
System Python: test_district_geo 27, test_zip_centroids 19, test_state_legislative_geo 25,
test_geo_v2_alignment 10, test_geo_v2_assign 16 - all OK. Venv: test_geo_lookup 14, test_evidence_geo 55,
test_map_layers_server 15, test_runtime_inputs 9 - all OK. Node app/tests 621/621. Browser: strip suite,
busy-mark suite, studio_pending, studio_data_source, evidence_map_render - all pass. No test wrote into
mentat/state, app/geo, .cache/geo or the test folders (tests/snap_before_py.json vs snap_after_py.json).

## Open for the orchestrator
- NW Hawaiian Islands drawn inside the Alaska box by the Hawaii conic (pre-existing); clipping = Hawaii moves.
- Alaska stays box-fitted, (-15.7, +46.6) px from where d3's anchor would put it.
- Five sibling browser suites leave *-reports-* folders under the venv (same cleanupPath fix applies).
- Browser suites that draw Alaska beyond evidence_map_render were not re-run.

## Brain draft (for Paul to apply)
- DEADENDS candidate: Node 24's fs.rmSync does not retry a folder another process holds as its working
  directory (EPERM "Permission denied" after 1 ms despite maxRetries/retryDelay); retry in JS with real
  waits. Seen with venv-launched consoles (bpo-35797) in the browser suites.
- STATE: Alaska inset fixed 2026-09-26 (lane L2): longitude wrap in the Albers frame; Alaska 0.35 x lower 48
  as d3; 28 geo files rebuilt, Hawaii and lower 48 byte-identical.
