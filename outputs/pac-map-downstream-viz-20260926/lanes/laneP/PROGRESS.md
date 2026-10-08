# Lane P progress (maps as marks-card layers; boards #47 #48 #49 #53 #54 #55)

Started 2026-09-25 23:17 EDT. Mentat HEAD at start: 3cec985249b098478868b8729e33b5b4ab31752e (codex/mentat-crypto).
Port 8852. Glass Box run_id lane-p-20260925 source maps-layers. No git writes. Paul commits.
Writes to C:\Users\pgoff\Mentat only through laneP\apply_edit.py (lane M's writer, adapted:
sha-checked, backup, atomic, EOL-preserving per region, RECEIPT.json + diffs/).

## Inputs read (23:17-23:40)
- BUILD_PACKET s0/s2/s3; tableau_maps_research s1-s10; studio_maps_census; offline_basemap_research.
- Boards b54 b55 b47 b48 b49 b53 + frames board6 board7 M13 S1.
- Lane receipts: M (landed, marksCards v3 with source/geography hooks), G (v2 in STAGING, not installed),
  B (F12 LANDED 22:59:57: evidence_geo.py sha b380252ccea3.. -> I may edit evidence_geo.py after re-checking sha),
  F (flow landed; (c) Chart Studio Flow mark still pending -> expect chart-studio*.js drift), V (Mentat venv at
  C:\Users\pgoff\AppData\Local\Mentat\venv has Jinja2 -> render_console runs there).

## Don't copy (from the brief)
- #47 sidebar reorder; #48/#55 tinting no-data states (keep plain base); #55 crediting a state with only its
  largest candidate (sum every candidate, support and oppose kept apart); #54 base-layer ticks that disagree with
  the drawing. Board numbers are invented except #55's candidate figures.

## Status log
- 23:40 inputs read; next: read code (core/studio marks tab, contribution-map, evidence-map, evidence.js, server
  STATIC_ASSETS/CSP/save_view, evidence_geo scan, geo v2 staging index, contracts).
- 23:50 P01 evidence_geo.py scan narrowed (b380252ccea3 -> 413a4a2c2bfd; F12 had landed, sha matched lane B's last):
  geo.glob('*.json') + (geo/'sld').rglob('*.json'). test_evidence_geo + contract_v4 62/62 before and after.
- 23:53 v2 INSTALLED: build_geo_layers.py --install (system Python), staging -> mentat/app/geo/v2, 867 files.
  Scan cost with v2 present (venv Python, best of 5): old rglob 930 paths 147.5 ms; new scope 113 paths 14.4 ms
  (proof/scan_cost_after_install.txt). geo tests OK.
- Architecture chosen (details in the report): new modules map-layers.js (pure model/aggregate/hex/density/MapLibre
  compile), map-engine.js (SVG Albers multi-layer + density canvas + Layer control + legends + export hook),
  map-streets.mjs (MapLibre adapter), map-studio.js (Chart Studio UI), map.css; small hunks in chart-studio.js,
  chart-studio-core.js, chart-studio-contributions.js, server.py, evidence-map.js, evidence.js, templates.
  Aggregation is client-side from existing routes (contributions query with industry=; /api/evidence-geo) plus the
  v2 lookup tables; no second money calculation on the server.
- 00:10 P02 tools/build_basemap_style.mjs installed and run: .cache/basemap/style/{light,dark}.json (71 layers, all URLs
  same-origin, fonts only Regular/Medium). P03 server.py 40288dd095de -> 1acedd342154 (7 hunks: STATIC_ASSETS +6,
  CONSOLE_CSP + geo v2/basemap routes + byte_range/send_ranged, VIEW_* map constants, _card_ok map checks +
  _map_source_ok/_card_map_ok/_sheet_map_ok, validate_view_marks map branch, CSP x2, do_GET dispatch).
  Suites: studio_marks_contract + contract_examples + views_industry + contribution_http 49 OK.
- 00:25 P04 chart-studio-core.js 0889d0f85391 -> acf786cd3bd3 (11 hunks; mapModel, CARD_KEYS+map, cardFault
  layerFault, marksCardsFault map branch, normalize/serialize/hasV3/adopt carry map, mapLayersOn, dualAxisOn
  excludes maps, compileReport guard, export). P05 map-layers.js new. JS suite 576/576.
- 00:40 map-layers.test.js 10/10 (hex pins 1000/1000 worst 5e-5 m; frame projection 33k ZCTAs worst <=0.1 px;
  conservation at every level; PAC payload: state layer == by_state and == located_total, oppose kept apart).
  rowsFromEvidence: state/cd from the server's kinds (street > ZIP shares > state); finer Raised levels from by_zip,
  residual listed "placed by its state or street address, not by a ZIP"; default-off kinds listed, not dropped.
- NEXT: map-engine.js (SVG Albers surface: base/density canvas/marks SVGs, Layer control, legends, scale, search,
  export hook), map-streets.mjs, map-studio.js, map.css; then chart-studio.js/contributions/evidence hooks, templates.
- 00:55 installed: map-engine.js, map-studio.js, map-streets.mjs, map-evidence.js, map.css (new); chart-studio.js
  c13609ca347d -> e51e7820f263 (12 hunks, on top of lane F's 00:33 Flow hunks); chart-studio-contributions.js 1 hunk;
  evidence-map.js 2 hunks (internals + onSettle); evidence.js 4 hunks (on lane F's dac9a595); server.py +map-evidence
  asset (on lane F's 65600605); page_head.html 2 edits (+ map-evidence); index.html re-rendered (render_console
  --write, --check OK). Console 8852 = venv Python (console.py start/stop; only its own PID).
- NEXT: browser pass on 8852 (Chart Studio: build 3-layer map, save/reopen; Streets; PAC evidence Layers +
  handoff), fix, then contracts (studio_api v3 map examples + controls), server tests (Range, routes, validation),
  node tests, browser suite, proofs at 1440x900 and 1920x1080.
- 01:00-05:15 browser pass on 8852 (Chart Studio map sheets, 4 layers from 3 sources; Map Layers pane; Layer control;
  MapLibre loads under CSP with attribution). Fixes synced through sync.py (engine label creation, cache reload,
  level-aware rowsFromEvidence, shelf hiding, render ticket, Streets container height). Console restarted once after
  a Banking density query took the child to ~3.7 GB (free RAM 1.66 GB); Banking avoided since.
- 05:20 P14 studio_api.json c2a68bc0ce3b -> 84be795e5aca: +7 map examples (producers: gen_contract_map.js), +15 lane-P
  controls (refusal cards|map). Lane M filters (P15/P16) exclude lane P: their counts stay 23 (M 14 + F 9).
- 05:27 NEW tests/test_map_layers_server.py (14 OK: byte_range units, 206/416/200/If-Range, whitelist + traversal 404s,
  CSP, assets, map examples byte-intact, 15 controls with their sentence, validator, evidence_geo scan excludes v2).
  Negative controls (negctl_server.py): byte_range ignored, CSP without worker/connect, validator accepts all, old
  rglob scan: each FAILS the suite (teeth).
- 05:29 NEW app/tests/map-layers-contract.test.js (6 OK); negctl_contract.js: producer default changed -> fails; gate
  accepts all -> fails. map-layers.test.js presets expectation corrected (spent = 1 fill card; hatch is an overlay).
- NEXT: full node + python suites, render_console --check; Streets + PAC evidence browser checks; real-client pass
  (Playwright, 8852); side-by-side proofs; Glass Box; report.
- 05:40-07:00 browser fixes found by the real client (all lane P files, synced via sync.py): empty Streets banner hidden;
  snapshots labelled with save date (three Coinbase networks); level words keep acronyms (ZIP code); Add layer icon
  sized; density drawn as an <image> in its own layer group (card order = draw order; exported as PNG data URL);
  Streets draws ZIP/county circles anywhere from lookup centres; evidence Layer control rows top-first (= handoff card
  order); Tract tile (disabled, reason) in Aggregate by; Layer control starts closed (opens from the toolbar); Map
  layers pane rows compact; menus flip above near the bottom; Streets reports status; map sheets hide the builder's
  single-source totals/scope strip (view class) and clear a stale busy mark. A view.bump() attempt was reverted: it
  made layer queries restart forever (releaseFlight) on a cold console.
- 07:00 real client (real_client.cjs, console 8852, fresh contexts): 18/18 at 1440x900 and 18/18 at 1920x1080,
  0 page errors (proof/real_client_*.json, proof/shots). Side-by-sides: proof/side (14).
- 07:05 RECEIPT closing check: 6 files changed after lane P by other writers (evidence_geo, chart-studio-core,
  evidence.js, studio_api.json, lane M's two contract tests); lane P's hunks verified present in each.
- NEXT: suite sweep (run_suites.py -> proof/suites.json), Glass Box finish, stop 8852, report.
- 07:15 sweep (run_suites.py): 30 suites, 28 green. test_evidence_map_browser step 24 failed on lane P (the Layers
  button cost the board 6 toolbar row 81 px at 1600): button moved onto the map (top right, map-evidence.js +
  map.css); suite now ALL 27 STEPS PASSED. test_evidence_map_interaction_browser fails at step 6 on lane F's Flow
  segment (Summary|Map|Flow|Rows); with only that tolerated (flow_tolerant.cjs preload) ALL 22 STEPS PASSED.
- 07:20 real client re-run after the move: 18/18 at both sizes; composites rebuilt. RECEIPT closed (closing_check).
  Glass Box finish written. Console 8852 stopped. Report delivered.

## Polish pass (2026-09-26, 03:30-04:30 EDT): four gaps
- 03:35 Glass Box polish-start. Probe (probe_board.cjs, probe_svgbg.cjs) found: in Chart Studio the rule
  `.studio-canvas svg {background:white; height:auto}` reached the map's own SVGs - the white marks surface hid the
  whole base (land, coast, washout, data layer, county/district lines) and every icon was a white square on a pressed
  button (pointer state unreadable) - in the builder, Board tiles and Canvas alike; duplicate id="mm-control" with two
  maps on a Board; the status line ignored the viewer's eyes. Snapshot of pre-polish assets: negctl/before/.
- 03:50-04:05 code: map-layers.js (stance + pattern: sourceFault/cardMapFault/layerFault, rowsFromEvidence side rows,
  aggregate dollar line for sides, compileLayer pattern legend, evidenceLayers/evidencePresets with the Opposition card,
  paneLabel, csv badge 'Imported file', Senate reason), map-engine.js (unique control ids, hatch pattern per SVG,
  pattern legend, side tooltip, status on toggles), map-streets.mjs (fill-pattern image + fallback; __maplibre on its
  container for checks), map-studio.js ("Imported PAC files" group + importMenu, side rows, Pattern/Side selects,
  keepPatternValid, handle pruning, scopeChip), map-evidence.js (Opposition drawn from its compiled card via
  E.drawOverlay into a scratch group then swapped; row as the card with pointer; legend swatch), map.css (studio svg
  override, hatch swatch, choices). server.py 053c0b569fae -> 7d08ce48c423 (6 edits: VIEW_MAP_STANCES/PATTERNS,
  _map_source_ok stance, _card_map_ok pattern, _card_fills, _card_ok). chart-studio.js e51e7820f263 -> e0efbf946aa2
  (3 edits: renderScopeChip parts/basis/title, currentChart chip).
- 04:05 CONTRACT INCIDENT + REPAIR: the old build_contract_map.py (written before lane F appended its parts) dropped
  lane F's owner suffix "; Lane F (flow cards)" and lane F's description note, and moved foreign entries (write
  df402508d009 -> 096f4ba47326). Rewrote the builder to merge IN PLACE (order-preserving) and rebuilt from the pre-write
  backup (backup/studio_api.json.df402508.orig); repair_contract.py asserts every non-lane-P part equals the pre-write
  file, then installed 096f4ba47326 -> ac8009d40a6a (6 hunks, lane P only). Lane F's owner and note verified present.
- 04:10 tests: map-layers.test.js +2 tests (sides never netted, conservation over evidence-geo.json Spent examples;
  faults/labels/legend), presets test updated; map-layers-contract.test.js 19 controls (+4: stance 'net', stance on
  Raised, pattern 'plaid', hatch on a circle), +views_save_map_opposition; test_map_layers_server.py 19 controls,
  +test_one_side_and_the_hatch_are_mirrored_on_save. node 18/18, py 32 OK. Negative controls: negctl_polish_model.cjs
  (pre-polish map-layers.js -> 5 tests fail), negctl_polish_server.py (4 mutations, all TEETH).
- 04:25 real client (scenes build,reopen,pane,aggregate,streets,evidence,board,csv,spent): 53/53 at 1440x900 and
  53/53 at 1920x1080, 0 errors. NEGCTL=1 (pre-polish assets routed): 21/33, every new assert fails
  (proof/real_client_1440x900_negctl_keep.json). The fixture workbook was imported through the PAC evidence tab into
  8852's data root (csv-2498a1f9705742847702e6142e0c9c24; proof/real_client_1440x900_first_import.json).
- 04:30-05:05 full sweep (run_suites.py): 30 suites, 0 failing (JS 619/619; evidence_map 27/27, interaction 23/23 -
  lane F's Flow expectation is now in that suite, panes 35/35, board 20/20). proof/suites_polish.json + .log.
- 05:05 refinement: the hatch keeps its screen size when zooming (map-engine.js scaleHatch in settleView; map-evidence.js
  rescale calls it). map-engine.js 864e276a66f1 -> 5aeee81d7fa0, map-evidence.js 21e650e3d90e -> 7e2d8fd877b8. Re-ran
  the touched suites (evidence_map, interaction, panes, studio_board, all js/cjs: 12 suites, 0 failing) and the real
  client: 54/54 at 1440x900 and 54/54 at 1920x1080, 0 errors. Focused negative control (the 864e276a engine routed):
  the zoom check FAILS (pattern width stays 6 at x2.18) - proof/real_client_1440x900_negctl_zoom.json.
- 05:10 compose.cjs: 22 side-by-sides (4 new: b55opp, b55oppstudio, b49board, b47csv). finalize_receipt.py: every file
  of this pass "as lane P left it"; 5 files touched in the first pass were changed later by other writers
  (evidence_geo, chart-studio-core, evidence.js, lane M's two contract tests) - not touched here. Console 8852 stopped.
- Polish writes: 12 files, 18 writes (polish_writes.py). Open for the orchestrator: (1) on District the Opposition card
  is by district, so Senate opposition ($11.57M for FAIRSHAKE 2023-2024) is listed in its legend, not hatched on the
  state (the old overlay hatched Senate states there; the District fill already leaves Senate out); (2) Region is still
  handed over by state (no region level); (3) kinds switched off on the evidence map are not carried to Chart Studio;
  (4) the evidence map's Add data > Another committee still lists snapshots only (imports are in Chart Studio's picker).
