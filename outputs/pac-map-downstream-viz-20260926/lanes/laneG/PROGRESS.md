# Lane G progress (geography build, GeoPandas) - run_id lane-g-20260925 - DONE 2026-09-25 ~23:10

Repo C:\Users\pgoff\Mentat, branch codex/mentat-crypto, HEAD 3cec98524 (unchanged). No git writes.
System Python (GeoPandas): C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe
Console Python: %USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
GeoPy: NOT installed in system Python -> step skipped, counts reported.

## State now
- NEW files (installed via laneG/install.py, receipt laneG/RECEIPT.json; sources of truth laneG/src/*):
  mentat/tools/build_geo_layers.py, mentat/tools/geo_assign.py, mentat/app/geo_lookup.py,
  mentat/tests/test_geo_v2_alignment.py, test_geo_v2_assign.py, test_geo_lookup.py. No foreign file edited.
- OUTPUT TREE IS IN STAGING: mentat/.cache/geo_build/v2 (866 files, 204.7 MB, verified vs index sha256).
  NOT installed: installing (one rename) kept /api/evidence-geo at 200 but slowed cached requests from
  52-147 ms to 408-998 ms (evidence_geo.py:70 signs every *.json under app/geo: 930 files, 213 ms/scan).
  Coordinator order: leave in staging; lane P narrows the scan, then runs
    python mentat/tools/build_geo_layers.py --install
- Tools default to staging and REFUSE to write into mentat/app/geo/v2.
- Bulk-assign caches: mentat/state/geography/assigned-v2/*.json (5 PAC snapshots; ignored runtime state).
- Tests: console Python test_geo_lookup 14 OK; system Python alignment+assign 25 OK (default paths read
  staging while app/geo/v2 is absent).

## Resume after a reboot
- Nothing is running. To rebuild: build_geo_layers.py (~21 min), geo_assign.py tables (~4 min),
  geo_assign.py assign --snapshot <dir> per snapshot. All write staging / state only.

## Key findings (for the report)
- Alignment: v2 compat state + cd116/118/119 paths byte-identical to shipped (worst 0.000 px);
  projection pin 0.0 px on 3,059 vertices; SLD 99.957% of 992,406 shipped vertices within 0.5 px.
- Pre-existing Alaska defect kept on purpose (Near Islands unwrapped; inset scale 254.24 vs 376.54).
- Census tract codes: Connecticut 2020 codes (geocoder vintage 420) vs 2022 planning-region codes in
  cb_2024 files -> geo_lookup matches by TRACTCE (852 codes). 312 water tracts added census-only.
- Overlay (500k tract x 20m CD) vs Census whole tracts: 157,568 agree / 3,111 disagree (98.06%);
  Census answer wins in the tables. Uptown Charlotte tract 37119000101 = NC-14 (118th), NC-12 (119th).
- City-only leftovers across 5 snapshots: 22 names / 165 rows; GeoPy not installed -> 0 matched.
- Peaks: layers 472.5 MB; tables 528 MB; assign (CULAC, 320 MB snapshot) 763 MB after trimming parse.
