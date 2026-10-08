# Lane L3 - Hawaii inset clip + browser-suite temp folders (2026-09-26) - run id lane-l3-20260926

Repo C:\Users\pgoff\Mentat, branch codex/mentat-crypto, HEAD fadd2c751. No git writes. Every repo write
went through apply_edits.py (spec + sha256 guard + backup + atomic replace + per-span EOL check),
create_file.py (one new test) or install_geo.py (20 geo files, plus a check that each live target was
exactly what the unchanged tools rebuild). RECEIPT.json lists 33 writes with sha before/after and
backup; all 33 were re-hashed at the close and are still as written. Unified diffs of the code edits
are in diffs\.

## Status: DONE (2 of 2), one decision for the lead

### Item 1 - Hawaii inset clip
- Premise check (probe_hawaii.json, probe_extent.json): the Hawaii fit is width-bound on the 20m main
  islands, so the layout box (258, 512, 352, 602) is tight on them. In the 500k layers the Big Island
  reaches x 352.135 (Cape Kumukahi), Kaula sits at x 252.87, and the hexagons over the islands span
  x 241.71..362.69. Clipping to the layout box would have cut the Big Island in six files, dropped
  Kaula, cut 13 hexagons and dropped 2 more - against "main islands byte-identical".
- Chosen extent: REGIONS['hawaii']['clip'] = (247, 497, 371, 610), the canvas round the Hawaii box one
  pixel clear of the Alaska (x 246), lower-48 (y 496) and Samoa (x 372) boxes. d3's own Hawaii
  clipExtent is likewise wider than its islands (about 5 px) and abuts Alaska's. One constant.
- Code: build_district_geo (clip_ring, in_clip, project_rings_counted, projection block records the
  clip), build_state_legislative_geo (clipped_rings per district), build_zip_centroids (project_point
  None outside), build_geo_layers (Frame.clip in albers_features / compat_rings / write_hex; clipped
  and clipped_rings only where non-zero; VERSION .2), map-layers.js (projectFrame null outside).
- Proof: current tools rebuilt == installed (old 111 files, v2 866 files). Clipping tools vs that:
  old - cd116/118/119 projection block only; sld HI 15025/15051 lose 5 drawn NWHI rings each;
  sld/index clipped_rings {15025:15}/{15051:15}, offcanvas_rings {}. v2 - 13 files + index; every
  non-Hawaiian feature identical (Alaska included; county.json is one valid coverage again); kept
  Hawaiian rings byte-identical; one hexagon (h50:-94:30, over Kaula, which reached into the Alaska
  box) cut at x 247; tract 15003981200 (all NWHI) listed as clipped, not written.
- Installed 20: cd116/118/119.json, sld/upper/HI, sld/lower/HI, sld/index; v2 detail/HI county,
  sldl, sldu, state, tract; national/HI sldl, sldu, tract; national county, state; hex/HI/hex10,
  hex25, hex50; v2/index.json (last). verify_tree(v2) OK.
- Tests: test_state_legislative_geo NWHI test re-pinned (before: offcanvas_rings keys [15025] /
  [15051]; after: offcanvas_rings {} and clipped_rings {15025: 15} / {15051: 15}). map-layers.test.js:
  FRAME pin gains 'clip'; new Hawaii test. New tests/test_hawaii_inset_clip.py (5 tests).
- Negative controls: new test on the pre-clip files FAILS 3/5 (648 points outside the clip, 626 in
  the Alaska box); passes 5/5 on the rebuilt files (54,595 points, 0/0). Node pre-change FAILS 2/3,
  clipping PASS 3/3. SLD test fails pre, passes post.
- PNGs: png\hi_county_{before,after}.png, _inset.png, _kenai.png (8x on French Frigate Shoals).

### Item 2 - browser-suite temp folders
- Same async cleanupPath as the strip suite in studio_board, ui_cleanup, studio_industry, p4b
  (evidence_map_interaction), s8 (evidence_map); every finally awaits it. No shared helper exists.
- Found: studio_industry's page run never removed its mentat-studio-industry-data-reports-* folder
  (the finally cleaned dataRoot only). Fixed.
- Runs under the venv (MENTAT_PYTHON): board 20/20, ui_cleanup 12/12, industry 10/10, p4b 23/23,
  s8 27/27 - no new folder, no cleanup error.
- Removed 10 EMPTY report folders (p4b x2, s8 x1, studio-board x2, studio-industry-data x3,
  ui-cleanup x2). Left in place: 11 older non-empty data/fixture folders of these suites and
  mentat-ui-cleanup-r-reports-20260920 (3 files; not a suite folder).

## Tests (live tree, after install)
System Python: test_district_geo 27, test_zip_centroids 19, test_state_legislative_geo 25,
test_geo_v2_alignment 10 (states/cd 0.000 px, sld 99.9557%), test_geo_v2_assign 16,
test_hawaii_inset_clip 5 - all OK. Venv: test_geo_lookup 14, test_evidence_geo 55,
test_map_layers_server 15 - all OK. Node app/tests 622/622. Browser: evidence_map_render PASS.
No test wrote into mentat/state, app/geo, .cache/geo, tests or app/tests (tests\snap_*.json).

## Open for the lead
- DECISION: clip extent (247, 497, 371, 610) vs the literal layout box (see Item 1).
- test_evidence_panes_browser.cjs (s6) and test_navigation_scope_browser.cjs have the same sync rmSync
  cleanup; not in L2's five, no leftovers of theirs seen. Same fix applies.
- Only Hawaii is clipped; d3 clips every inset.
- contribution-map.js (equirectangular composite, own Hawaii inset) untouched.

## Brain draft (for Paul to apply)
- STATE: Hawaii inset clipped 2026-09-26 (lane L3): REGIONS['hawaii']['clip'] = (247, 497, 371, 610)
  in build_district_geo, applied by every tool and map-layers.js; the Northwestern Hawaiian Islands
  no longer draw in the Alaska box; 20 geo files reinstalled; main islands byte-identical.
- DEADENDS candidate: clipping Hawaii to its layout box - the fit is width-bound on the 20m main
  islands, so 500k geometry (Cape Kumukahi +0.135 px, Kaula -5 px) and hexagons overrun it.
