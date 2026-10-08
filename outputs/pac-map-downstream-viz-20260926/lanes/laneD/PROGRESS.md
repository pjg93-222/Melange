# Lane D PROGRESS (F3 SLF + F5 FAIRSHAKE 2026 collections)

Started 2026-09-25 ~20:40 local. No code changes, no git writes.

## Status
- [ ] Read server.py POST /api/evidence-collect route + pac_evidence.py + transfer_rule.py
- [ ] Decide invocation (CLI vs route) and Python
- [ ] F3 SLF C00571703 cycles 2022,2024,2026 (max-units 60)
- [ ] F5 FAIRSHAKE 2026 refresh (max-units 20)
- [ ] Read-only console 8855: /api/evidence-network + /api/evidence-geo
- [ ] FEC re-check GETs
- [ ] Kill consoles; final report

## Log

### 20:40-21:00 reading + pre-flight (no collector run yet)
- Route (server.py Console.collect_evidence, now :1560-1617; file is being edited by another lane, 20:42): validates, snapshot-<uuid4> under mentat/.cache/pac-evidence, collection.json job, Popen [sys.executable tools/pac_evidence.py --company=C --aliases=a|b --committees .. --cycles .. --output root], NO --max-units (always default 30). Listing = any */evidence.json version 1.
- Company: route + form REQUIRE one (server.py:1565, index.html:526 required). No company-free path exists. Company only filters receipts (contributor name) -> receipts, temporal_routes, cash estimates, and labels the picker. Network (downstream.py) and map ignore it.
  -> SLF: company "Senate Leadership Fund", aliases SENATE LEADERSHIP FUND|SENATE LEADERSHIP FUND PAC|SLF PAC (the 3 names filers use for C00571703 in bulk OTH). FAIRSHAKE: reuse Coinbase + COINBASE|COINBASE COMMERCE EXCHANGE (both prior FAIRSHAKE snapshots).
- Launcher laneD/run_collection.py = the route's collect() verbatim + --max-units + Glass Box heartbeats. Console Python 3.12.14 imports the collector fine (stdlib only).
- Offline BFS sim on bulk v4c edges (k06_bfs_sim.py): uncapped SLF network = ~1,450 units (reaches NRCC at #36, RNC at #60, state parties); FAIRSHAKE 2024+2026 reaches CA Dem Party #9, DNC #14. => max-units 60 would collect NRCC/RNC (100k+ row Schedule A -> 1000-page failure each).
  -> SLF budget 24 (roots 3 + 18 direct recipients + ACC 2022, America Fund 2024, ALRINO 2022); cut = America Fund 2024's 11 recipients (CLF 185 pages, MAGA Inc, WFW...).
  -> FAIRSHAKE: cycles 2024,2026 (F10's $250,857 = LGBTQ VF + Democrats Serve are PP **2024** recipients; 2026-only cannot reach them), budget 8.
- openFEC schedule_a is returning 504s now (MAGA Inc, WFW all 4 attempts). Pre-flight requests so far: 30.

### 21:02 F3 SLF collection STARTED (background, launcher pid in F3-SLF.status.json)
- snapshot-28d0bc70c5bb44b799b0a4cbb3522aee under C:\Users\pgoff\Mentat\mentat\.cache\pac-evidence
- argv: --company=Senate Leadership Fund --aliases=SENATE LEADERSHIP FUND|SENATE LEADERSHIP FUND PAC|SLF PAC --committees C00571703 --cycles 2022,2024,2026 --max-units 24
- 21:04: 111 responses saved. Next: F5 FAIRSHAKE (C00835959, 2024+2026, max-units 8) ONLY after F3 exits.
- If the machine reboots: a half-written snapshot has collection.json state collecting and no evidence.json; the console reports it "interrupted" and lists nothing. Re-run into the SAME dir reuses source-cache (no repeat requests).

### 21:06 F3 SLF DONE: snapshot-28d0bc70c5bb44b799b0a4cbb3522aee (3.8 min, 247 saved responses, exit 0, all IE totals reconcile)
- 24 units; uncollected 12 (ALRINO 2022 + America Fund 2024's 11 recipients incl. CLF, MAGA Inc). ALRINO was displaced by 75 PAC 2026 (SLF $44.46 in-kind, no type, line 23 -> line fallback followed it).
- SLF 2024 -> 7 = $67,437,000.00 exact; 2022 -> 9 = $26,590,000.00 exact; SLF IE 2024 $211,093,032.88, 2026 $6,450,359.90 exact.
- Loops into SLF: AC 2024 $1.3M, America Fund 2024 $5M, White Mountain 2022 $2.14M, KKG 2026 $830.30.
- SURPRISE: SLF -> Conservative Americans PAC $895,000 on 2023-12-04, but CA terminated 2023-02-10 with $0 receipts; CA's only onward row (-> America Fund $41,727.99) is dated 2023-02-08, BEFORE the SLF money. The America Fund branch is reached through a date-impossible route.
### 21:10 F5 FAIRSHAKE starting next (C00835959, 2024+2026, max-units 8; 09-08 rows predict exactly FS/DAJ/PP x2 + LGBTQ VF 2024 + DS 2024)

### 21:10 F5 FAIRSHAKE DONE: snapshot-b26761887a1f44d58cc38fdb8b720a78 (2.0 min, 191 saved responses, exit 0, all IE totals reconcile)
- 8 units exactly as predicted; uncollected 5 (CA Dem Party, SD County Dem, Fair Wisconsin, Forward Together, Tomorrow's Jobs - all 2024).
- 2026 exact to the cent: FS -> DAJ $37M, PP $33M; DAJ IE $32,518,094.42; PP $27,646,756.62; FS $13,296,611.79. F10 closed: LGBTQ VF + DS 2024 = $250,858.13.
### 21:11-21:20 verification (read-only console 8855, pid 36588, MENTAT_PREWARM=0, own data root) - KILLED, ports 8854/8855 closed
- Network + spent map queried for SLF 2022/2024/2026 and FAIRSHAKE 2026/2024 (verify\*.json, v01_console_verify.txt). FEC re-check 11 GETs (fec\*.json, v03_fec_recheck.txt): every figure unchanged.
- Loop: network visits each committee/cycle once (back-edges listed in edges only); map removes internal transfers both ways: SLF 2024 outflow $410,098,199.91 = $483,876,927.90 reported - $73,778,727.99 internal (hand-checked).
- Requests: pre-flight 30 (10 were 504s) + 247 + 191 + re-check 11 = 479 counted; collector retries are not logged; the collector does not write fec-api-budget.sqlite.
- Side effect: console wrote 2 snapshot-index sidecars in mentat/state/drawer-sidecars/snapshot-index (runtime cache).
## LANE D COMPLETE 21:20 - no code changes, no git writes.
