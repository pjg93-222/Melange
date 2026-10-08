# Live panels: Staffer people-network latency work (landing_v2, landing_v3_ids, landing_v4)

Two read-only live panels were run against the production sidecar on 127.0.0.1:8841 (HTTP GET only; each harness enforces a
read-endpoint allow-list and never starts, stops or restarts a process). This file keeps their key tables so the packet stands
alone. The raw payloads, CSVs and harness scripts stay in the session scratchpad (`live_panel`, `live_panel_v4`) and are not
part of the packet.

How the tables were made. Panel 1 is `live_panel/final_tables.md` copied verbatim (line endings normalised to LF). Panel 2 has
no report file, so its tables come from the panel's own offline `report.py` (run on a copy of the folder, output copied
verbatim) and from small tables computed here from `step0_log.json`, `final_performance.json`, `panel_rows.csv`,
`scan2_summary.json`, `scan2_console.log`, `typeahead_rows.csv`, `typeahead_extra_rows.csv`, `typeahead_summary.json`,
`end_state.json` and `baseline.json`. Nothing was re-measured when this file was written. Times are wall-clock seconds unless a
column says ms.

## Panel 1: 2026-10-03, route latency by scenario

The 2026-10-03 post-landing panel (sidecar PID 35320, started 14:59 local on 2026-10-03). Scenarios use the UI defaults (objective
`work_time`, route_count 3, distinct alternatives) except the rows marked rc=1, which ask for one route; async mode, 100 ms polling,
one request in flight at a time. `final_tables.py` applies a timing offset to requests whose server-side elapsed time at the first
progress report exceeded the client's clock by more than 2 s; the table is reproduced as written.

| scenario | n (found/other) | first route s: p50/p95/p99/max (found) | final s: p50/p95/p99/max (all) | final s (found only) | server elapsed_ms s: p50/p95/p99/max (all) | median expanded (first search / sum over routes), median nbr checks (found) | peak WS growth MB p50/max (all) |
|---|---|---|---|---|---|---|---|
| office default (case+large+varied) | 21 (6/15) | 11.64 / 39.17 / 39.17 / 39.17 | 1.17 / 60.73 / 90.69 / 90.69 | 40.45 / 90.69 / 90.69 / 90.69 | 0.92 / 60.61 / 90.75 / 90.75 | 799.0 / 4649.0 ; 139901.5 | 4 / 429 |
|   office cases.json (directory offices) | 8 (0/8) | n/a | 0.84 / 40.36 / 40.36 / 40.36 | n/a | 0.58 / 40.20 / 40.20 / 40.20 | None / None ; None | 4 / 429 |
|   office large rosters | 5 (3/2) | 35.65 / 39.17 / 39.17 / 39.17 | 59.01 / 90.69 / 90.69 / 90.69 | 60.73 / 90.69 / 90.69 / 90.69 | 58.93 / 90.75 / 90.75 / 90.75 | 1567.0 / 7662.0 ; 527984.0 | 11 / 29 |
|   office varied | 8 (3/5) | 3.06 / 11.64 / 11.64 / 11.64 | 0.50 / 40.45 / 40.45 / 40.45 | 17.20 / 40.45 / 40.45 / 40.45 | 0.44 / 40.00 / 40.00 / 40.00 | 379.0 / 1542.0 ; 65569.0 | 3 / 24 |
| office cache-hit repeats | 3 (3/0) | 0.37 / 1.70 / 1.70 / 1.70 | 0.37 / 1.70 / 1.70 / 1.70 | 0.37 / 1.70 / 1.70 / 1.70 | 58.93 / 90.75 / 90.75 / 90.75 | 1567.0 / 7662.0 ; 527984.0 | 0 / 0 |
| office rc=1 cases.json (1,4,5,8) | 4 (0/4) | n/a | 0.54 / 0.59 / 0.59 / 0.59 | n/a | 0.44 / 0.51 / 0.51 / 0.51 | None / None ; None | 3 / 4 |
| office rc=1 on found cases (warm) | 4 (4/0) | 0.61 / 2.49 / 2.49 / 2.49 | 0.61 / 2.49 / 2.49 / 2.49 | 0.61 / 2.49 / 2.49 / 2.49 | 0.50 / 1.90 / 1.90 / 1.90 | 799.0 / None ; 0.0 | 4 / 4 |
| person default (readme+receipt+cases+varied) | 17 (9/8) | 4.77 / 28.47 / 28.47 / 28.47 | 7.47 / 74.29 / 74.29 / 74.29 | 18.84 / 74.29 / 74.29 / 74.29 | 7.16 / 74.21 / 74.21 / 74.21 | 523.0 / 1719.0 ; 37837.0 | 4 / 33 |
|   person cases.json | 8 (1/7) | 1.83 / 1.83 / 1.83 / 1.83 | 0.66 / 18.84 / 18.84 / 18.84 | 18.84 / 18.84 / 18.84 / 18.84 | 0.50 / 18.56 / 18.56 / 18.56 | 118.0 / 888.0 ; 17187.0 | 2 / 7 |
|   person varied + readme + receipt | 9 (8/1) | 4.77 / 28.47 / 28.47 / 28.47 | 16.46 / 74.29 / 74.29 / 74.29 | 16.46 / 74.29 / 74.29 / 74.29 | 15.58 / 74.21 / 74.21 / 74.21 | 643.0 / 2307.0 ; 65405.0 | 11 / 33 |
| person extras (rc=1) | 2 (2/0) | 0.23 / 2.74 / 2.74 / 2.74 | 0.23 / 2.74 / 2.74 / 2.74 | 0.23 / 2.74 / 2.74 / 2.74 | 0.14 / 2.67 / 2.67 / 2.67 | 207.0 / None ; 71828.5 | 4 / 4 |
| supp office | 7 (7/0) | 0.50 / 3.24 / 3.24 / 3.24 | 2.73 / 8.16 / 8.16 / 8.16 | 2.73 / 8.16 / 8.16 / 8.16 | 2.64 / 7.89 / 7.89 / 7.89 | 366.0 / 1996.5 ; 31371.0 | 4 / 7 |
| supp person | 4 (4/0) | 0.65 / 3.22 / 3.22 / 3.22 | 3.07 / 6.86 / 6.86 / 6.86 | 3.07 / 6.86 / 6.86 / 6.86 | 3.05 / 6.78 / 6.78 / 6.78 | 1033.0 / 4468.5 ; 40975.5 | 5 / 6 |

poll-to-poll gaps over all 62 route requests: n=1691 p50=244 ms p95=872 ms p99=1398 ms max=16427 ms

found rc=3 requests: first route time / final time:
  O10_large2                   first=39.17s final=90.69s  route1 search=38.14s  alternatives (2 more routes) server ~52.61s
  O12_large4                   first=35.65s final=59.01s  route1 search=34.75s  alternatives (2 more routes) server ~24.18s
  O13_large5                   first=12.01s final=60.73s  route1 search=11.94s  alternatives (2 more routes) server ~48.67s
  O15_var3                     first=1.88s final=4.82s  route1 search=1.72s  alternatives (2 more routes) server ~2.52s
  O17_var14                    first=3.06s final=17.20s  route1 search=2.91s  alternatives (2 more routes) server ~14.13s
  O19_var30                    first=11.64s final=40.45s  route1 search=11.52s  alternatives (2 more routes) server ~28.48s
  R01_readme_gordon_grace      first=4.77s final=16.46s  route1 search=4.22s  alternatives (2 more routes) server ~11.36s
  R02_receipt_gordon_casca     first=1.57s final=9.50s  route1 search=1.24s  alternatives (2 more routes) server ~8.06s
  R10_case8_person             first=1.83s final=18.84s  route1 search=1.61s  alternatives (2 more routes) server ~16.95s
  V01_house_to_house           first=16.70s final=43.35s  route1 search=16.36s  alternatives (2 more routes) server ~26.73s
  V02_senate_to_house          first=28.47s final=74.29s  route1 search=28.12s  alternatives (2 more routes) server ~46.09s
  V03_lobbyist_to_house        first=18.16s final=27.37s  route1 search=18.02s  alternatives (2 more routes) server ~9.03s
  V04_senate_to_lobbyist       first=6.62s final=20.90s  route1 search=5.03s  alternatives (2 more routes) server ~15.58s
  V05_lobbyist_to_lobbyist     first=0.98s final=8.73s  route1 search=0.84s  alternatives (2 more routes) server ~7.64s
  V06_reverse_casca_gordon     first=0.62s final=7.47s  route1 search=0.34s  alternatives (2 more routes) server ~6.82s
  S00_large162_tyler           first=3.24s final=8.16s  route1 search=2.98s  alternatives (2 more routes) server ~4.90s
  S01_then_rc3_83              first=0.23s final=2.73s  route1 search=0.11s  alternatives (2 more routes) server ~2.54s
  S02_then_rc3_45              first=0.26s final=3.97s  route1 search=0.12s  alternatives (2 more routes) server ~3.82s
  S03_then_rc3_20              first=0.26s final=3.05s  route1 search=0.11s  alternatives (2 more routes) server ~2.89s
  S01_person_payroll_pair      first=3.22s final=6.86s  route1 search=3.00s  alternatives (2 more routes) server ~3.78s
  S02_person_payroll_pair      first=0.58s final=4.14s  route1 search=0.52s  alternatives (2 more routes) server ~3.33s
  S03_person_payroll_pair      first=0.65s final=2.29s  route1 search=0.17s  alternatives (2 more routes) server ~1.95s
  S04_person_payroll_pair      first=0.89s final=3.07s  route1 search=0.83s  alternatives (2 more routes) server ~2.22s

## Panel 2: 2026-10-04, post-landing (v4) panel

Sidecar PID 36412, restarted 03:17:41 local (2026-10-04 07:17:41 UTC). The panel ran 102 route requests (70 of them a scan from one origin), 10 + 6
typeahead requests and a coverage scan of 404 offices. Its harness stops if host available RAM falls below 400 MiB or the sidecar
grows more than 1.5 GB above the post-prewarm baseline; neither limit was hit (`aborted`, `error` and `release_status` are empty,
`capped` and `released` are 0, and every final response was HTTP 200, in all 102 route rows).

### 2.1 Prewarm timeline

| event | UTC | seconds since process start |
|---|---|---|
| sidecar process started | 2026-10-04 07:17:41.559 | 0 |
| initial ready (server metric `initial_ready_ms`) | | 246.87 |
| prewarm queued | 2026-10-04 07:21:49.832 | 248.27 |
| prewarm started (waited 0 ms) | 2026-10-04 07:21:49.833 | 248.27 |
| prewarm finished | 2026-10-04 07:22:51.468 | 309.91 |
| first panel poll saw Ready with the prewarm done | 2026-10-04 03:30:32 local | 771.3 |

| prewarm stage | duration s |
|---|---|
| work index (`done`) | 15.92 |
| network index (`done`) | 35.57 |
| garbage collection | 10.15 |
| total, queued to finished | 61.63 |

Router revision `784eea6c8c4da2295fa4`, as of 2026-10-04, prewarm sequence 1, earlier prewarms: 0.
Network index: 131,207 people, 10,654,440 bytes, built in 35.56 s. Snapshot: 533,684 bytes on the wire, 1,455,858 uncompressed.
Memory at the panel's first reading after the prewarm (03:30:33): working set 4023 MB, private bytes 7422 MB, OS peak working set 6834 MB, host available 4719 MB of 33864 MB (MB = 10^6 bytes).

First route request after the prewarm (case O15_var3, Dante Cutrona to DOUG LAMALFA, an office with 1 staff member, UI defaults): status found, first route 2.02 s, final 2.83 s, server elapsed 2.49 s, 72 expansions.

### 2.2 Cold searches, 2026-10-03 against 2026-10-04

The same five cases in the same order (O10, O12, O13, then Gordon R01 and R02), each a single cold run with the UI defaults. Panel 1
values are the `found rc=3` lines of the Panel 1 text above; Panel 2 values are `panel_rows.csv`, unadjusted. The two panels ran
different sidecar builds, so the ratio is indicative, not a controlled benchmark.

| case | 10-03 first route s | 10-03 final s | 10-04 first route s | 10-04 final s | final-time ratio (10-03 / 10-04) |
|---|---|---|---|---|---|
| O10_large2 | 39.17 | 90.69 | 12.75 | 24.59 | 3.7 |
| O12_large4 | 35.65 | 59.01 | 14.09 | 19.05 | 3.1 |
| O13_large5 | 12.01 | 60.73 | 3.70 | 18.94 | 3.2 |
| R01_readme_gordon_grace | 4.77 | 16.46 | 1.55 | 2.12 | 7.8 |
| R02_receipt_gordon_casca | 1.57 | 9.50 | 0.99 | 1.42 | 6.7 |

#### Detail of the 2026-10-04 cold searches (report.py, verbatim)

| case | route 1 wall s | final wall s | server elapsed s | first expansion ms | expanded (route 1 / sum) | neighbor_checks (route 1 / sum) | pairs_scored (route 1 / sum) | steps (3 routes) | cost (3 routes) |
|---|---|---|---|---|---|---|---|---|---|
| O10_large2 | 12.75 | 24.59 | 24.47 | 478.0 | 1566 / 7661 | 527325 / 1101622 | 190053 / 353715 | 3/4/4 | 9.708713 / 10.872059 / 11.267565 |
| O12_large4 | 14.09 | 19.05 | 18.96 | 489.9 | 2705 / 9412 | 541562 / 743097 | 208469 / 269636 | 3/4/4 | 10.870680 / 11.426531 / 11.434939 |
| O13_large5 | 3.70 | 18.94 | 18.22 | 553.8 | 538 / 4728 | 166423 / 702624 | 62522 / 231768 | 3/4/4 | 8.849047 / 10.559138 / 12.454438 |
| R01_readme_gordon_grace | 1.55 | 2.12 | 1.94 | 631.6 | 523 / 1719 | 40384 / 71551 | 15644 / 24562 | 6/5/5 | 8.689908 / 9.278097 / 10.344728 |
| R02_receipt_gordon_casca | 0.99 | 1.42 | 1.26 | 667.2 | 287 / 1062 | 15812 / 35578 | 6042 / 12935 | 3/5/5 | 6.144159 / 6.508575 / 7.180866 |

### 2.3 Unreachable reasons

22 unreachable requests (13 office_without_work_records, 3 origin_without_work_connections, 6 target_without_work_connections); suggested objective in every payload: evidence_cost; wall time 130 to 741 ms (median 224 ms).

#### Every unreachable payload (report.py, verbatim; scenarios s2*, UI defaults, route_count=3, distinct, async=1)

| # | scenario | request | status | reason | suggested_objective | uncovered | expanded | nbr_checks | wall ms | server ms | message id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | s2_dir_office | O01_case1 Tyler Hardy -> House Permanent Select Committee on Intelligen | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 218 | 40.11 | M1 |
| 3 | s2_dir_office | O03_case3 Dante Cutrona -> Senate Appropriations Committee Energy and Wat | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 197 | 50.55 | M1 |
| 4 | s2_dir_office | O05_case5 Andrew Perlstein -> Rep. Tim Kennedy | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 204 | 46.52 | M1 |
| 5 | s2_dir_office | O08_case8 Nick Hawatmeh -> House Appropriations Committee | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 196 | 39.12 | M1 |
| 6 | s2_dir_office | O11_large3 Brad Howard -> Sen. Chuck Schumer | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 248 | 58.81 | M1 |
| 7 | s2_politico_target | R05_case3_person Dante Cutrona -> Kathleen Williams | unreachable | target_without_work_connections | evidence_cost | n/a | 2 | 0 | 479 | 51.82 | M2 |
| 8 | s2_politico_target | R06_case4_person Sydney Dahiyat -> Brianna Lounsbury | unreachable | target_without_work_connections | evidence_cost | n/a | 2 | 349 | 347 | 124.17 | M2 |
| 9 | s2_politico_target | R07_case5_person Andrew Perlstein -> Evelyn Williams | unreachable | target_without_work_connections | evidence_cost | n/a | 2 | 92 | 406 | 100.23 | M2 |
| 10 | s2_origin_teixeira | R04_case2_person Joey Teixeira -> Leah Dunne | unreachable | origin_without_work_connections | evidence_cost | n/a | 1 | 0 | 208 | 49.03 | M3 |
| 11 | s2_origin_teixeira | O09_large1 Joey Teixeira -> COMMITTEE ON APPROPRIATIONS | unreachable | origin_without_work_connections | evidence_cost | 0 | 1 | 0 | 248 | 152.09 | M3 |
| 12 | s2_origin_teixeira | O21_var93 Joey Teixeira -> COMMITTEE ON OVERSIGHT AND ACCOUNTABILITY | unreachable | origin_without_work_connections | evidence_cost | 0 | 1 | 0 | 364 | 150.72 | M3 |
| 18 | s2x_dir_office_extra | O02_case2 Joey Teixeira -> Senate Commerce, Science and Transportation Co | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 741 | 87.32 | M1 |
| 19 | s2x_dir_office_extra | O04_case4 Sydney Dahiyat -> House Natural Resources Committee (Minority St | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 231 | 40.73 | M1 |
| 20 | s2x_dir_office_extra | O06_case6 Karen Wasielewski -> House Agriculture Committee for Rep. G.T. Thom | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 130 | 16.06 | M1 |
| 21 | s2x_dir_office_extra | O07_case7 Brad Howard -> House Education and the Workforce Committee fo | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 257 | 25.69 | M1 |
| 22 | s2x_dir_office_extra | O14_var1 Porter Tucker -> House Select Strategic Competition Between the | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 348 | 31.07 | M1 |
| 23 | s2x_dir_office_extra | O16_var9 Nick Hawatmeh -> Senate Special Committee on Aging (Main Office | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 201 | 64.12 | M1 |
| 24 | s2x_dir_office_extra | O18_var20 Sydney Dahiyat -> Senate Environment and Public Works Committee  | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 327 | 86.1 | M1 |
| 25 | s2x_dir_office_extra | O20_var55 Lauren Edwards -> Senate Finance Committee (Minority Staff) | unreachable | office_without_work_records | evidence_cost | 0 | 0 | 0 | 139 | 14.11 | M1 |
| 26 | s2x_politico_target_extra | R03_case1_person Tyler Hardy -> Tara Westby | unreachable | target_without_work_connections | evidence_cost | n/a | 2 | 0 | 140 | 27.58 | M2 |
| 27 | s2x_politico_target_extra | R08_case6_person Karen Wasielewski -> Sofia Jones | unreachable | target_without_work_connections | evidence_cost | n/a | 2 | 0 | 148 | 30.0 | M2 |
| 28 | s2x_politico_target_extra | R09_case7_person Brad Howard -> Jenna Berger | unreachable | target_without_work_connections | evidence_cost | n/a | 2 | 80 | 135 | 24.37 | M2 |

M1: No Staffer route: none of this office's current staff have dated employment at this office in the records this model uses.
M2: No Staffer route: the person you want to reach has no workplace connections this search can use.
M3: No Staffer route: the person you start with has no workplace connections this search can use.

### 2.4 Coverage

Offices whose roster includes staff whose records do not meet the model's authenticated staffer coverage requirements
(`uncovered_staff_count`). The scan starts every search from Joey Teixeira, who has no work connections, so each search ends at once and the
interesting field is the count in the payload. It probed directory-roster offices largest first until three showed uncovered staff:
404 of 1,257 candidate offices probed in 110.5 s (median 144.2 ms, maximum 726.9 ms per probe); statuses unreachable/office_without_work_records 142, unreachable/origin_without_work_connections 262.

| office | id | staff | uncovered | scan status | scan reason | probe ms |
|---|---|---|---|---|---|---|
| HON. BRITTANY PETTERSEN | container:office:house:HON:P000620 | 16 | 1 | unreachable | origin_without_work_connections | 241.4 |
| HON. RASHIDA TLAIB | container:office:house:HON:T000481 | 16 | 1 | unreachable | origin_without_work_connections | 144.6 |
| HON. MIKE BOST | container:office:house:HON:B001295 | 15 | 1 | unreachable | origin_without_work_connections | 109.4 |

Real searches to those three offices (UI defaults, from Tyler Hardy), and one control: a person route to the uncovered staff member of the first office.

| request | origin | target | staff | uncovered | status | routes | first route s | final s | expanded (route 1) |
|---|---|---|---|---|---|---|---|---|---|
| COV1_P000620_from_Tyler | Tyler Hardy | HON. BRITTANY PETTERSEN | 16 | 1 | found | 3 | 1.90 | 2.85 | 1256 |
| COV2_T000481_from_Tyler | Tyler Hardy | HON. RASHIDA TLAIB | 16 | 1 | found | 3 | 1.00 | 3.14 | 689 |
| COV3_B001295_from_Tyler | Tyler Hardy | HON. MIKE BOST | 15 | 1 | found | 3 | 0.49 | 0.89 | 372 |
| CTRL_person_to_uncovered_of_P000620 | Tyler Hardy | (uncovered staff of HON. BRITTANY PETTERSEN) | n/a | n/a | insufficient_work_coverage | 0 | n/a | 0.12 | n/a |

Control payload message: These people are known, but their records do not meet this model's authenticated staffer coverage requirements. Try Ecosystem for documented associations.

Joey Teixeira scan inside the route panel (UI defaults): 70 requests, 17 unreachable/office_without_work_records, 53 unreachable/origin_without_work_connections, wall median 158 ms, maximum 854 ms.

Index coverage in `final_performance.json` (the `/api/staffer-performance` metrics):

| measure | value |
|---|---|
| searchable person nodes | 180,215 |
| people in the network index | 131,207 |
| people with person facts | 180,215 |
| interns excluded from the network | 52,107 |
| current staff | 14,216 |
| review assertion coverage | PASS (declared 100,256, served unique 100,256, promoted 0) |
| contacts matched | 4,511 of 5,777 source people |
| payroll employment people | 135,039 |

### 2.5 Typeahead

Ten requests (people two-character, people full name, offices): p50 56.8 ms, p95 494.6 ms, maximum 494.6 ms. Six more, the fifth after 45 s idle: 77.0 ms, 109.0 ms, 95.7 ms, 122.1 ms, 126.5 ms, 25.4 ms.
`visible` is the number of results whose visible text contains the query; `not explained` is the harness's count of results whose match is not
explained by visible text (0 for every people query, consistent with the D-083 rule that matches come from human-readable fields).

| # | group | query | http | ms | results | visible | not explained |
|---|---|---|---|---|---|---|---|
| 1 | people_2char | co | 200 | 494.6 | 20 | 20 | 0 |
| 2 | people_2char | po | 200 | 99.9 | 20 | 20 | 0 |
| 3 | people_2char | li | 200 | 56.8 | 20 | 20 | 0 |
| 4 | people_2char | ma | 200 | 40.2 | 20 | 20 | 0 |
| 5 | people_fullname | Tyler Hardy | 200 | 134.4 | 1 | 1 | 0 |
| 6 | people_fullname | Mike Casca | 200 | 105.0 | 1 | 1 | 0 |
| 7 | people_fullname | Karen Wasielewski | 200 | 7.2 | 1 | 1 | 0 |
| 8 | office | judiciary | 200 | 123.7 | 20 | 20 | n/a |
| 9 | office | house appropriations | 200 | 32.9 | 20 | 20 | n/a |
| 10 | office | tim kennedy | 200 | 21.7 | 2 | 1 | n/a |

### 2.6 Memory and idle state

#### Memory per request (report.py, verbatim; WS = working set, priv = private bytes, MB)

| seq | scenario | name | wall ms | WS before | WS peak-before | WS after-before | WS peak - baseline(6834) | priv before | priv peak-before | host free min |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s1_first_after_prewarm | O15_var3 | 2827 | 2885 | 189 | 189 | -3760 | 7429 | 5 | 2671 |
| 2 | s2_dir_office | O01_case1 | 218 | 2907 | 0 | 0 | -3927 | 7434 | 0 | 1629 |
| 3 | s2_dir_office | O03_case3 | 197 | 2908 | 1 | -1 | -3925 | 7436 | 0 | 1692 |
| 4 | s2_dir_office | O05_case5 | 204 | 2907 | 0 | 0 | -3927 | 7434 | 0 | 1687 |
| 5 | s2_dir_office | O08_case8 | 196 | 2908 | 1 | 1 | -3926 | 7434 | 0 | 1613 |
| 6 | s2_dir_office | O11_large3 | 248 | 2910 | 1 | 1 | -3924 | 7435 | -1 | 1407 |
| 7 | s2_politico_target | R05_case3_person | 479 | 2810 | 0 | 0 | -4024 | 7434 | 0 | 1246 |
| 8 | s2_politico_target | R06_case4_person | 347 | 2814 | 1 | 1 | -4019 | 7438 | 1 | 1160 |
| 9 | s2_politico_target | R07_case5_person | 406 | 2813 | 1 | 1 | -4020 | 7434 | 0 | 1136 |
| 10 | s2_origin_teixeira | R04_case2_person | 208 | 2814 | 0 | 0 | -4020 | 7434 | 0 | 1291 |
| 11 | s2_origin_teixeira | O09_large1 | 248 | 2814 | 6 | 6 | -4014 | 7434 | 0 | 1243 |
| 12 | s2_origin_teixeira | O21_var93 | 364 | 2821 | 7 | 7 | -4007 | 7434 | 2 | 1150 |
| 13 | s4_cold | O10_large2 | 24594 | 2722 | 8 | -170 | -4104 | 7436 | 6 | 3816 |
| 14 | s4_cold | O12_large4 | 19048 | 2552 | 10 | -52 | -4272 | 7436 | 8 | 3137 |
| 15 | s4_cold | O13_large5 | 18940 | 2462 | 23 | 7 | -4349 | 7442 | 16 | 2587 |
| 16 | s4_cold | R01_readme_gordon_grace | 2120 | 2469 | 0 | -1 | -4365 | 7457 | 4 | 2366 |
| 17 | s4_cold | R02_receipt_gordon_casca | 1419 | 2469 | 1 | -1 | -4365 | 7461 | 0 | 1929 |
| 18 | s2x_dir_office_extra | O02_case2 | 741 | 2444 | 2 | 0 | -4388 | 7489 | 2 | 6301 |
| 19 | s2x_dir_office_extra | O04_case4 | 231 | 2444 | 0 | 0 | -4390 | 7489 | 0 | 6240 |
| 20 | s2x_dir_office_extra | O06_case6 | 130 | 2444 | 0 | -31 | -4390 | 7489 | 0 | 6516 |
| 21 | s2x_dir_office_extra | O07_case7 | 257 | 2414 | 0 | 0 | -4420 | 7489 | 0 | 6375 |
| 22 | s2x_dir_office_extra | O14_var1 | 348 | 2414 | 0 | 0 | -4420 | 7489 | 0 | 5527 |
| 23 | s2x_dir_office_extra | O16_var9 | 201 | 2414 | 0 | 0 | -4420 | 7489 | 0 | 4985 |
| 24 | s2x_dir_office_extra | O18_var20 | 327 | 2414 | 0 | 0 | -4420 | 7489 | 1 | 4958 |
| 25 | s2x_dir_office_extra | O20_var55 | 139 | 2414 | 0 | 0 | -4420 | 7489 | 0 | 5240 |
| 26 | s2x_politico_target_extra | R03_case1_person | 140 | 2415 | 0 | 0 | -4420 | 7489 | 0 | 5029 |
| 27 | s2x_politico_target_extra | R08_case6_person | 148 | 2415 | 0 | 0 | -4420 | 7489 | 0 | 6203 |
| 28 | s2x_politico_target_extra | R09_case7_person | 135 | 2415 | 0 | 0 | -4420 | 7489 | 0 | 6194 |
| 30 | s3_scan_teixeira | SCAN_002 | 372 | 2415 | 4 | 0 | -4415 | 7489 | 4 | 5381 |
| 40 | s3_scan_teixeira | SCAN_012 | 153 | 2417 | 1 | 0 | -4416 | 7489 | 1 | 3977 |
| 50 | s3_scan_teixeira | SCAN_022 | 129 | 2427 | 1 | 1 | -4407 | 7499 | 1 | 7033 |
| 60 | s3_scan_teixeira | SCAN_032 | 135 | 2433 | 0 | 0 | -4401 | 7504 | 0 | 7509 |
| 70 | s3_scan_teixeira | SCAN_042 | 128 | 2434 | 0 | 0 | -4401 | 7504 | 0 | 7910 |
| 80 | s3_scan_teixeira | SCAN_052 | 190 | 2436 | 0 | -2 | -4398 | 7506 | 0 | 7649 |
| 90 | s3_scan_teixeira | SCAN_062 | 154 | 2434 | 0 | 0 | -4400 | 7504 | 0 | 7709 |
| 99 | s3_real_uncovered | COV1_P000620_from_Tyler | 2854 | 2447 | 9 | 4 | -4379 | 7509 | 6 | 5000 |
| 100 | s3_real_uncovered | COV2_T000481_from_Tyler | 3135 | 2450 | 3 | 3 | -4381 | 7509 | 0 | 4356 |
| 101 | s3_real_uncovered | COV3_B001295_from_Tyler | 894 | 2454 | 2 | 2 | -4378 | 7509 | 0 | 4546 |
| 102 | s3_control_person | CTRL_person_to_uncovered_of_P000620 | 121 | 2457 | 0 | 0 | -4378 | 7509 | 0 | 6878 |

route requests: 102; peak WS growth per request MB: p50 0, max 189; peak private growth per request MB: p50 0, max 16
heavy (>1.5 s) requests: 7; their peak WS growth MB: [189, 8, 10, 23, 0, 9, 3]; private growth MB: [5, 6, 8, 16, 4, 6, 0]

End state at 03:55:17 local: working set 2,518 MB, private bytes 7,531 MB, OS peak working set 6,834 MB, host available 6,536 MB, 21 threads; idle CPU over 30 s: 17.9% (six 5 s windows: 21.2, 20.9, 8.1, 18.9, 17.8, 20.6), as recorded in `end_state.json`.

## Panel 3: v4.1 panel (2026-10-04)

The third read-only live panel (HTTP GET only, as for Panels 1 and 2), run against the production sidecar on 127.0.0.1:8841 after
landing_v4_1 was applied and the sidecar restarted: PID 66688, process started 18:33:08 UTC (14:33:08 local) on 2026-10-04. The opening paragraph of
this file describes the first two panels only. This is the second attempt at this panel; the first attempt stopped on a host-memory
floor (3.1). The second attempt sent 14 route requests and 10 typeahead requests, measured 30 s of idle CPU with no requests and ended
with 1 performance request, between 15:06 and 15:10 local, one request in flight at a time. Its memory policy: before each request wait
while host available RAM is below 700 MiB (resuming at 1,000 MiB), stop below 300 MiB or when the sidecar's private bytes grow more than
1.5 GB above their value at the start of the run; none of these happened (memory waits 0, aborts 0, client caps hit 0, every final
response HTTP 200).

How the tables were made. Sections 3.2 to 3.9 are `live_panel_v4_1/r2_report.txt` (written by the panel's offline `compare2.py`, which
compares the second attempt with Panel 2) copied verbatim in the order of its sections (line endings normalised to LF), each in a code
block so that the column alignment survives.
Section 3.1 is computed from `ABORT.json` and `step0_partial_summary.json`. Nothing was re-measured when this text was written. In the
tables, "v4" is Panel 2 (sidecar PID 36412, section 2) and "v4.1" is this panel; as in 2.2, the two panels ran different sidecar
builds, so the ratios are indicative, not a controlled benchmark. Times are wall-clock seconds unless a column says ms.

### 3.1 First attempt: stopped on the host-memory floor

The first attempt (`step0.py`) began while the sidecar was still starting up. At 14:41:32 local, 8 min 23 s after the process started,
it stopped itself before its next request because host available RAM was 372,449,280 B (372 MB of 33,864 MB), below its floor of 419,430,400 B
(400 MiB); the sidecar then held 7,277,953,024 B of private bytes, 6,713,475,072 B of working set and 24 threads (`ABORT.json`). It sent no route request.
The stop came from the harness's own guard, not from the sidecar: all 33 requests it had sent returned HTTP 200.

| item | value |
|---|---|
| requests sent before the stop | 33: 23 ready polls, 2 performance polls, 8 typeahead probes |
| server `initial_ready_ms` | 453,639.43 ms (7.56 min after the process started) |
| Ready poll | poll 23 at 14:40:47 local, 459.1 s after the restart, stage `Ready` |
| host available at the ready polls | 4,079.5 MB at poll 1, 1,004.5 MB at poll 16 (14:39:49 local, the lowest), 1,175.5 MB at the Ready poll |
| sidecar private bytes at the ready polls | 4,813.1 MB at poll 1, 6,899.7 MB at the Ready poll |
| prewarm record 0.38 s and 34.7 s after Ready | seq 1 `running`, queued 18:40:43.739 UTC, started 18:40:44.060 UTC, waited 0 ms, no stage recorded yet |
| typeahead during the prewarm | 8 probes; probe 4 (`q=ma`, 7.2 s after Ready) took 27.43 s; median before it 0.209 s, after it 0.911 s |
| passive watch after the stop | 14:46:34 to 14:47:45 local: host available 857 to 2,673 MB, sidecar CPU mean 5.8% (maximum 24.8%) |

`step0.py` stopped before it wrote `step0_log.json`, so `step0_partial_summary.json` was rebuilt from `step0_console.log`, `ABORT.json`,
`step0_raw/` and `passive_watch_rows.csv` (its own note). The second attempt, below, was run after the stop with the memory policy
described above.

### 3.2 Unreachable reasons (report step 1)

```text
STEP 1  unreachable reasons (UI defaults, one holder token)
case               reason (v4 = v4.1)                 status    msg=v4   expl=msg sugg      v4: expl==msg / v4.1 wall ms, srv ms (v4 wall, srv)
O01_case1          office_without_work_records =      unreachable True     True     True      False / 653, 384.6 (218, 40.1)
O11_large3         office_without_work_records =      unreachable True     True     True      False / 200, 111.1 (248, 58.8)
R05_case3_person   target_without_work_connections =  unreachable True     True     True      False / 154, 146.1 (479, 51.8)
R04_case2_person   origin_without_work_connections =  unreachable True     True     True      False / 262, 31.1 (208, 49.0)
   O01_case1 message: No Staffer route: none of this office's current staff have dated employment at this office in the records this model uses.
   R05_case3_person message: No Staffer route: the person you want to reach has no workplace connections this search can use.
   R05 counters: v4 expanded/nbr/pairs = 2/0/0 ; v4.1 = 2/241/133
```

### 3.3 Coverage from Tyler Hardy, default and directory-only modes (report step 2)

```text
STEP 2  coverage, origin Tyler Hardy (v4 reference: COV rows, default mode)
run                        status     found  routes steps uncov uncovered_basis  work_src   uncovered ids same as v4 / paths same as v4 (route1..3) / wall s (v4) / srv s (v4) / exp (v4) / nbr (v4) / pairs (v4)
COV1_P000620_default       found      True   3      5     1    payroll_or_roster payroll_and_directory True / True,True,True / 10.78 (2.85) / 10.30 (2.69) / 1256 (1256) / 212976 (87807) / 85500 (29430)
COV2_T000481_default       found      True   3      4     1    payroll_or_roster payroll_and_directory True / True,True,True / 5.03 (3.14) / 4.95 (2.88) / 689 (689) / 52588 (36982) / 19484 (11469)
COV3_B001295_default       found      True   3      4     1    payroll_or_roster payroll_and_directory True / True,True,True / 2.10 (0.89) / 1.86 (0.74) / 372 (372) / 30649 (23539) / 13995 (10314)
COV1_P000620_directory     found      True   3      5     1    roster           directory  - / - / 11.34 / 11.08 / 1294 / 70012 / 36438
COV2_T000481_directory     found      True   3      7     1    roster           directory  - / - / 1.07 / 0.91 / 1231 / 13919 / 6707
COV3_B001295_directory     found      True   3      5     1    roster           directory  - / - / 0.53 / 0.47 / 375 / 7761 / 3981
```

### 3.4 Cold searches, v4 against v4.1 (report step 3)

```text
STEP 3  cold searches, UI defaults: seconds; v4 -> v4.1
case                       1st route s       final s           server s          expanded (top/sum)  neighbor_checks     pairs_scored        cache_hit / status 
O10_large2                 12.75 -> 5.15     24.59 -> 11.59    24.47 -> 11.41    1566/7661 -> 1566/7661 527325 -> 344607    190053 -> 112424    False / found
O13_large5                 3.70 -> 2.72      18.94 -> 10.96    18.22 -> 10.75    538/4728 -> 538/4728 166423 -> 165194    62522 -> 61938      False / found
R01_readme_gordon_grace    1.55 -> 0.61      2.12 -> 1.46      1.94 -> 1.13      523/1719 -> 523/1719 40384 -> 19870      15644 -> 8174       False / found
R02_receipt_gordon_casca   0.99 -> 0.52      1.42 -> 0.67      1.26 -> 0.64      287/1062 -> 287/1062 15812 -> 11715      6042 -> 4352        False / found
```

### 3.5 Paths and costs, route by route (report step 3)

```text
STEP 3  paths and costs, route by route (v4 raw final vs v4.1 raw final); as_of v4 / v4.1
O10_large2: as_of 2026-10-04 / 2026-10-04 ; routes 3 / 3 ; top-level cost 9.708712532301991 / 9.708712532301991 ; equal=True
   route 1: path_identical=True  steps 3/3  cost_identical=True (v4 9.708712532301991, v4.1 9.708712532301991, diff 0.0)  route exp 1566 -> 1566, nbr 527325 -> 344607, pairs 190053 -> 112424
   route 2: path_identical=True  steps 4/4  cost_identical=True (v4 10.872058914321538, v4.1 10.872058914321538, diff 0.0)  route exp 2865 -> 2865, nbr 391233 -> 358812, pairs 117508 -> 101901
   route 3: path_identical=True  steps 4/4  cost_identical=True (v4 11.267564783124472, v4.1 11.267564783124472, diff 0.0)  route exp 3230 -> 3230, nbr 183064 -> 176675, pairs 46154 -> 43223
O13_large5: as_of 2026-10-04 / 2026-10-04 ; routes 3 / 3 ; top-level cost 8.849047159905918 / 8.849047159905918 ; equal=True
   route 1: path_identical=True  steps 3/3  cost_identical=True (v4 8.849047159905918, v4.1 8.849047159905918, diff 0.0)  route exp 538 -> 538, nbr 166423 -> 165194, pairs 62522 -> 61938
   route 2: path_identical=True  steps 4/4  cost_identical=True (v4 10.559137690388235, v4.1 10.559137690388235, diff 0.0)  route exp 1232 -> 1232, nbr 162688 -> 161195, pairs 56600 -> 56755
   route 3: path_identical=True  steps 4/4  cost_identical=True (v4 12.454437833649703, v4.1 12.454437833649703, diff 0.0)  route exp 2958 -> 2958, nbr 373513 -> 361038, pairs 112646 -> 105194
R01_readme_gordon_grace: as_of 2026-10-04 / 2026-10-04 ; routes 3 / 3 ; top-level cost 8.689908111039204 / 8.689908111039204 ; equal=True
   route 1: path_identical=True  steps 6/6  cost_identical=True (v4 8.689908111039204, v4.1 8.689908111039204, diff 0.0)  route exp 523 -> 523, nbr 40384 -> 19870, pairs 15644 -> 8174
   route 2: path_identical=True  steps 5/5  cost_identical=True (v4 9.278097197334798, v4.1 9.278097197334798, diff 0.0)  route exp 576 -> 576, nbr 12705 -> 11587, pairs 3600 -> 3267
   route 3: path_identical=True  steps 5/5  cost_identical=True (v4 10.344728429012658, v4.1 10.344728429012658, diff 0.0)  route exp 620 -> 620, nbr 18462 -> 17398, pairs 5318 -> 4769
R02_receipt_gordon_casca: as_of 2026-10-04 / 2026-10-04 ; routes 3 / 3 ; top-level cost 6.144158734612402 / 6.144158734612402 ; equal=True
   route 1: path_identical=True  steps 3/3  cost_identical=True (v4 6.144158734612402, v4.1 6.144158734612402, diff 0.0)  route exp 287 -> 287, nbr 15812 -> 11715, pairs 6042 -> 4352
   route 2: path_identical=True  steps 5/5  cost_identical=True (v4 6.508575136979742, v4.1 6.508575136979742, diff 0.0)  route exp 338 -> 338, nbr 4199 -> 4087, pairs 1771 -> 1794
   route 3: path_identical=True  steps 5/5  cost_identical=True (v4 7.1808661993092, v4.1 7.1808661993092, diff 0.0)  route exp 437 -> 437, nbr 15567 -> 15567, pairs 5122 -> 5222
```

### 3.6 Typeahead (report step 4)

```text
STEP 4  typeahead (v4.1 | v4), seconds
    1 people_2char     co                     n=20  0.0544 | 0.4946   in_label=20 visible=20 (v4 20 20)
    2 people_2char     po                     n=20  0.0451 | 0.0999   in_label=20 visible=20 (v4 20 20)
    3 people_2char     li                     n=20  0.0905 | 0.0568   in_label=20 visible=20 (v4 20 20)
    4 people_2char     ma                     n=20  0.0671 | 0.0402   in_label=20 visible=20 (v4 20 20)
    5 people_fullname  Tyler Hardy            n=1   0.1567 | 0.1344   in_label=1 visible=1 (v4 1 1)
    6 people_fullname  Mike Casca             n=1   0.2131 | 0.1050   in_label=1 visible=1 (v4 1 1)
    7 people_fullname  Karen Wasielewski      n=1   0.0385 | 0.0072   in_label=1 visible=1 (v4 1 1)
    8 office           judiciary              n=20  0.1521 | 0.1237   in_label=20 visible=20 (v4 20 20)
    9 office           house appropriations   n=20  0.0254 | 0.0329   in_label=20 visible=20 (v4 20 20)
   10 office           tim kennedy            n=2   0.0290 | 0.0217   in_label=1 visible=1 (v4 1 1)
   all 10: p50 0.0544 (v4 0.0568)  max 0.2131 (v4 0.4946)  p95 0.2131 (v4 0.4946)  median 0.0608 (v4 0.0784)
   people_2char     p50 0.0544 (v4 0.0568)  max 0.0905 (v4 0.4946)
   people_fullname  p50 0.1567 (v4 0.1050)  max 0.2131 (v4 0.1344)
   office           p50 0.0290 (v4 0.0329)  max 0.1521 (v4 0.1237)
```

### 3.7 Memory per request and run-wide totals (report memory and run-wide blocks)

```text
MEMORY per request (MB decimal): peak private growth over the run start, peak working-set delta, min host available (MiB), polls sent below 700 MiB, waits
   #1   O01_case1                    dPriv(run start)     3.3  dWS    81.5  minfree  5663 MiB  lowpolls 0  waits 0
   #2   O11_large3                   dPriv(run start)     6.4  dWS     5.9  minfree  5607 MiB  lowpolls 0  waits 0
   #3   R05_case3_person             dPriv(run start)     3.3  dWS    10.2  minfree  5555 MiB  lowpolls 0  waits 0
   #4   R04_case2_person             dPriv(run start)     3.3  dWS     0.0  minfree  5521 MiB  lowpolls 0  waits 0
   #5   COV1_P000620_default         dPriv(run start)     7.3  dWS   436.2  minfree  5235 MiB  lowpolls 0  waits 0
   #6   COV2_T000481_default         dPriv(run start)    11.7  dWS    14.0  minfree  4554 MiB  lowpolls 0  waits 0
   #7   COV3_B001295_default         dPriv(run start)     9.2  dWS     4.8  minfree  4730 MiB  lowpolls 0  waits 0
   #8   COV1_P000620_directory       dPriv(run start)    28.1  dWS  1001.4  minfree  3958 MiB  lowpolls 0  waits 0
   #9   COV2_T000481_directory       dPriv(run start)    26.1  dWS     2.6  minfree  3987 MiB  lowpolls 0  waits 0
   #10  COV3_B001295_directory       dPriv(run start)    32.4  dWS     1.6  minfree  4033 MiB  lowpolls 0  waits 0
   #11  O10_large2                   dPriv(run start)    50.1  dWS     8.8  minfree  4533 MiB  lowpolls 0  waits 0
   #12  O13_large5                   dPriv(run start)    61.6  dWS    15.5  minfree  4858 MiB  lowpolls 0  waits 0
   #13  R01_readme_gordon_grace      dPriv(run start)    66.5  dWS     5.7  minfree  5057 MiB  lowpolls 0  waits 0
   #14  R02_receipt_gordon_casca     dPriv(run start)    64.6  dWS     1.4  minfree  5259 MiB  lowpolls 0  waits 0
```

```text
RUN-WIDE
   route requests 14, HTTP GETs for them 217 (first GET + polls), typeahead GETs 10, performance GETs 1; all final_http 200: True; client caps hit 0; aborts 0; memory waits 0 (waits.jsonl exists: False)
   max request wall 11.6 s; min host available during any request 3959 MiB (4151 MB); polls sent below 700 MiB 0
   run-start private bytes 7487.7 MB; max peak private growth over the run start during a route request 66.5 MB (R01_readme_gordon_grace; ceiling 1500 MB); largest single-request private growth 21.0 MB; max peak working-set delta 1001.4 MB (COV1_P000620_directory)
   work totals COV1-3 + O10                     wall s v4 31.5 -> v4.1 29.5 ; neighbor_checks 675653 -> 640820 ; pairs_scored 241266 -> 231403
   work totals COV1-3 + O10 + O13 + R01 + R02   wall s v4 54.0 -> v4.1 42.6 ; neighbor_checks 898272 -> 837599 ; pairs_scored 325474 -> 305867
```

### 3.8 Memory and idle CPU with no requests (report step 5)

```text
STEP 5  memory and idle CPU (no requests)
   end of step 5 (2026-10-04T15:10:27): private 7581.9 MB (7230.7 MiB), working set 3452.0 MB, OS peak working set 6827.1 MB, host available 4885.8 MB, threads 21, private growth over run start 94.2 MB
   v4 end state: private 7531 MB, working set 2518 MB, OS peak working set 6834 MB, host available 6536 MB, threads 21
   idle CPU over 30.0 s: 19.2% of one core (v4 17.9%); 5 s windows [15.3, 21.9, 21.2, 7.5, 24.1, 25.3] (v4 [21.2, 20.9, 8.1, 18.9, 17.8, 20.6]); user 2.80 s, kernel 2.97 s
   per-thread CPU over the window: [(71104, 5.359, 17.85, 'user 2.41/kernel 2.95'), (49164, 0.344, 1.14, 'user 0.34/kernel 0.00'), (7884, 0.016, 0.05, 'user 0.00/kernel 0.02')] ; threads with CPU > 0.05 s: 2 of 21 ; established TCP connections to the sidecar: {'n': 1, 'by_status': {'LISTEN': 1}, 'established_remote_ports': []}
```

### 3.9 Performance metrics and prewarm (report step 6)

```text
STEP 6  GET /api/staffer-performance
   http 200 in 0.0230 s, ready True, stage Ready, errors []
   metrics.prewarm v4.1: {"seq": 1, "status": "done", "router_revision": "b33813c7ad686645f61f", "as_of": "2026-10-04", "queued_utc": "2026-10-04T18:40:43.739083+00:00", "stages": {"work_index": {"status": "done", "ms": 63097.71}, "network_index": {"status": "done", "ms": 15746.33}}, "waited_ms": 0.0, "started_utc": "2026-10-04T18:40:44.060691+00:00", "total_ms": 78874.14, "finished_utc": "2026-10-04T18:42:02.935288+00:00", "enabled": true, "earlier": []}
   gc_ms present in metrics.prewarm: False ; gc_ms key anywhere in the payload: False ; the raw response bytes contain "gc_ms": False
   v4 prewarm: total_ms 61634.37, work_index 15918.79 ms, network_index 35569.05 ms, gc_ms 10145.99 ; v4.1: total_ms 78874.14, work_index 63097.71 ms, network_index 15746.33 ms, gc_ms absent ; initial_ready_ms v4 246869.9, v4.1 453639.43
```
