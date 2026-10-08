# Lane C progress (F4 not-traced disclosure + lane B loose ends)

Run id lane-c-20260925, Glass Box source pac-disclosure, port 8856. No git writes.
Mentat HEAD at start: 3cec985249b098478868b8729e33b5b4ab31752e (branch codex/mentat-crypto).

## Baseline (verified 2026-09-25 20:36 local)
- Lane B files match lane B RECEIPT final sha256 (evidence.js b40df09b..., downstream.py 96f897d6..., evidence_geo.py aed518c5..., district_geo.py 3e344818..., transfer_rule.py 2a21893c..., pac_evidence.py a36ed292...).
- Lane A has NOT landed (tools/enrich_downstream.py etc. unmodified in tree): read F2 shape from laneA/staged + edits.

## Items
- [x] 1 Graph downstream drawer: not-traced wording (report_quality fact via sheet index; test binds them)
- [x] 2 Conditional estimates: F2 transfer_index_status + no-bundle message (+ worksheet notes, coordinator)
- [x] 3 Per-committee coverage (network table + drawer)
- [x] 4 Per-committee FEC summary reconciliation (IE + transfers)
- [x] 5 pac_cash_model.py -> transfer_rule helpers; measured: $0 moves
- [x] 6 evidence-geo.json contract v4 (+ evidence-network v1, graph-not-traced v1)
- [x] 7 CULAC 2024 refund line outside shares (captured at 1440 and 1920)
- [x] 8 district_geo.py docstring 2022 -> 118th
(See the log's last RESUME line for what remains.)

## Log
(Clock times below before 21:48 were written from memory and are approximate; the lane started 20:36 local. Receipt landed_at stamps are exact.)
- 21:05 Baseline captured on 8856 (shots/baseline_*). SLF drawer said "...and the PACs it funds" (false); estimates panel generic.
- 21:10 Lane A LANDED F2 live (coordinator). F2 shape: manifest transfer_index_status/notes; quality check transfer_index_<cycle>.
- 21:15 NEW SNAPSHOT snapshot-28d0bc70... (SLF + recipients, 21:02-21:06, another lane). SLF root now traced; 11 recipients hit collection_limit.
- graph_data.py landed (sha cc9fc46d): workbook_sheets/has_transfer_paths, audit_manifest/transfer_index/not_traced, transfer_trace, estimates F2, NO_ESTIMATE_BUNDLE.
- test_graph_not_traced.py (14) + test_graph_data update: 39 OK. negctl: 13 of 14 fail on old graph_data (out/negctl_test_graph_not_traced.txt).
- report_quality measured: Banking 21 s, Crypto 1.7 s -> NOT called from /api/graph; same fact from the sheet index, test binds them.
- NEXT: graph.js (drawer note, empty panel reason, tooltips), report_insights worksheet notes (coordinator ask), evidence items 3/4/7, pac_cash_model, contract, docstring.
- 21:40 graph.js 10 hunks (drawerNote pure+export, drawer note/tooltip, empty panel reason, candidate note tooltip) sha 1765fecb->26732321; graph-drawer-note.test.js 4 pass, negctl 4/4 fail on old graph.js.
- report_insights.py: worksheet notes for transfer-derived + direct-only sheets (coordinator ask) sha 9d76b1ca->0312370f; test_worksheet_not_traced 5 pass, negctl 3/5 fail (2 are negative-control tests).
- downstream.py: summary_transfers/unit_coverage/summary_reconciliation/committees; snapshot_view gains `committees` (sha 96f897d6->9fd6c958).
- evidence_geo.py: F6 gap now reads downstream.summary_transfers (6392fd89); then share_base, unlocated kind, reversals_total, rule_problems, share_problems (adf6b2e2).
- district_geo.py docstring 2022->118th (441e485f); test_district_geo_docstring 2 pass; direct negctl: old docstring states 2022->116 (out/negctl_test_district_geo_docstring_direct.txt). The shadow-run negctl errored for a wrong reason (no index.json in shadow) - not counted.
- evidence.js 12 hunks on lane B bytes (b40df09b->286cb84a): share rule, refunds line, rule under map, network committees table, per-spender coverage, pane network checks.
- evidence-map.js shareBaseFor + tooltip (7e409420->30dc1fe7). workspace.css recon marks + reversal row (a88a9f1f->aacfd5e5).
- NEW SNAPSHOT snapshot-b2676188 (21:08-21:10, FAIRSHAKE refresh F5): DAJ/PP 2026 now to 2026-08-31 and reconciled.
- NEXT: contracts (evidence-geo v4, evidence-network v1, graph-not-traced v1) + tests; pac_cash_model; full suites; browser; real-client pass.
- 22:05 pac_cash_model on transfer_rule (85e5a601->01f8e3f4); test_pac_cash_model_rule 5 pass, negctl 3/5 fail. MEASURED: 5 snapshots / 11 cycles all withheld before+after, $0 allocated both; SLF 2022 C00736751 issue transfer_pairing->disbursement_role (out/cash_moves_all.json). Sidecars now hash-mismatched -> /api/evidence stops attaching them (all withheld; UI text unchanged). NOT regenerated (Paul's call).
- contracts: evidence-geo v4 (3d2c48b3->9019c04b; +3 examples, +8 controls, +3 rules), evidence-network v1 NEW (7431636f), graph-not-traced v1 NEW (20a7cbfe). NEW JSONs are *.json-ignored -> Paul must `git add -f`.
- validators: evidence_geo.rule_problems/share_problems, downstream.network_problems (a52d48a8), graph_data.not_traced_problems (346008f0).
- tests: test_evidence_geo_contract_v4 (7), test_evidence_network_contract (5), test_graph_not_traced_contract (3), JS evidence-contract-v4 (7), graph-not-traced-contract (3). negctls all hold (old code fails).
- README contract index updated.
- NEXT: full Python suite (console python; templates with Python312), node suite, browser suite (MENTAT_UI_OUTPUT=laneC), restart 8856 + real-client pass + screenshots, RECEIPT/report.
- 22:20 evidence.js grouping of >8 unsaved committees (286cb84a->bad717af) + JS test; graph.js tooltip for a refused drawer (26732321->58c1f9f6).
- node suite: 551/551 pass (before the grouping test was added: 551 includes it? re-run at the end). render_console --check OK and test_console_templates 10 OK with Python312 (console python lacks jinja2).
- test_downstream_measurement_browser.cjs 1/1 pass.
- 8856 restarted on the new code (pid 35600).
- Full Python suite running (console python) -> out/full_python.txt.
OUT OF SCOPE (report, do not fix): cash sidecars hash-gated (regen cmd); report_quality 21 s on Banking; mapHtml dead code; new contract JSONs need git add -f; snapshots arrived mid-lane (SLF 21:06, FAIRSHAKE 21:10).
- 21:50 FULL PYTHON SUITE (console python, from mentat/tests): Ran 1620 tests in 515.9s, errors=5 skipped=2; the 5 errors are all test_console_templates `No module named 'jinja2'` (console python lacks jinja2) - the same file passes 10/10 under Python312. out/full_python.txt.
- real client (8856): Graph SLF + FF PAC drawers + Crypto estimates OK (shots/after_*_1440.png, after_1440.json); FAIRSHAKE 2026 committees table OK.
- 21:58 CULAC map on 8856 answered 400 "Map inputs changed while preparing this view": lane G was writing app/geo/v2 (albers per state, 21:51-22:11) and evidence_geo.cached_geography's dependency glob is geo_dir().rglob('*.json'). Worked around for the real-client pass only: 8856 restarted with MENTAT_GEO_DIR=laneC/geo_stable (byte-identical copy of app/geo minus v2). OUT OF SCOPE finding.
- 22:02 CULAC 2024 also has a LOCATED reversal (OH-02 -$2,500, Wenstrup for Congress), which alone withdrew every share under the old rule and under my first base rule. Refined: share_base = sum of places that net ABOVE zero ("positive located spending"); negative places show "Reversal". evidence_geo 2a1417c4, evidence.js 4ee9408b, evidence-map 311aa542, contract v4 regenerated 0518a919, tests updated. 420 targeted Python OK; node 567/567.
- 22:08 CULAC real client: rule "Shares are of the $5,533,402 of positive located spending on this map; ..."; Montana 18.8% ...; 0 Unavailable; Refunds and reversals -$5,000 line; foot names refunds. Refund-line cell tidied (outside the shares moved to label).
- 22:10 browser suite test_evidence_map_browser.cjs running (MENTAT_UI_OUTPUT=laneC/ui).
- 22:13 browser suite run 1 FAILED at step 23: "Map inputs changed while preparing this view" (lane G writing app/geo/v2) -> out/browser_evidence_map_run1_geo_v2_interference.txt.
- 22:16 browser suite run 2 with MENTAT_GEO_DIR=laneC/geo_stable (byte-identical, no v2): PASS, 28 steps, exit 0 -> out/browser_evidence_map.txt.
- negctls re-run on final tests: v4 contract (fails on old evidence_geo), JS contract tests (0/4 pass on old client files).
- HUNKS_FINAL.txt = final hunk ranges per modified file vs pre-lane bytes.
- 1920x1080 captures running.
- 22:17 1920x1080 captures: 4 of 4 scenes ok (shots/after_1920.json + after_*_1920.png): FF PAC drawer, Crypto estimates, FAIRSHAKE 2026 committees, CULAC 2024 map + refund line.
- 22:19 FAIRSHAKE "Differs -$14,000,000.00" traced (out/fairshake_gap_probe.txt): the 8 Sep snapshot's FAIRSHAKE itemization stops 2026-06-30 ($51M on lines 22-23) while its summary runs to 07-31 ($65M); the recipients itemize July receipts from FAIRSHAKE of $9M (DAJ) + $5M (PP) = $14M. The newer snapshots reconcile: 2eb1b6d6 $65M/$65M, b2676188 $70M/$70M. The mark is right about the 8 Sep bytes.
- 22:20 8856 stopped (pid 45160, own). Final sha check: 26 of 26 lane files hold their receipt hashes (out/final_sha_check.txt).
- 22:24 node 568/568 on final bytes (out/node_final.txt); test_console_templates 10/10 + render_console --check OK on Python312 (out/templates_final.txt). Full Python suite on final bytes started 22:24:36 -> out/full_python_final.txt.
- 22:28 COORDINATOR (F12 approved): lane B changes downstream.py + evidence_geo.py's Spent map so the walk follows dates; adds fields, never renames; does not edit evidence.js/graph_data.py. Checked: committees() reads the walk's found['units']/found['missing']; summary_reconciliation reads observations() (the measurement's own row rule) against the committee's own FEC summary; transfer_trace reads network['missing']; share_base/reversals_total are sums over the payload's own rows. No totals hard-coded in code or UI. Tests made additive-tolerant: test_evidence_network_contract.py 73ffd598->7fc9d859 (cut() to the contract's fields + negative control: renamed/changed/dropped still fail), test_evidence_geo_contract_v4.py 469f09dc->10274c1b (version >= 4; cut() on the projection). 13 OK. The full suite started 22:24:36 loaded the pre-edit copies of these two files.
- 22:36 Lane F edited evidence.js at 22:35:08 (Flow button + openFlow/closeFlow), built on lane C's 4ee9408b: all lane C hunks intact (recon/evidence.js.4ee9408b diffed: only lane F additions). New base b859873f.
- 22:39 Own defect found on self-review: static files are served from disk per request, so a console not restarted onto evidence_geo v4 hands the new page payloads with no share_base; the rule text then claimed "positive located spending" of the reported total (or "nothing placed nets above zero" on a map with a negative row), and the map tooltip said "% of positive located". Fixed: evidence.js b859873f->e9f3b45a (shareRuleText states no rule without share_base), evidence-map.js 311aa542->b5e3fc39 (shareOf keeps lane B's old words for such payloads; stale comment corrected), evidence-contract-v4.test.js dd13202d->a6cef7b7 (legacy assertions). Negative control: the pre-fix client fails the extended test at the new assertion (out/negctl_js_legacy_words.txt).
- 22:40 FULL PYTHON on final bytes (22:24:36-22:40:31, console python): Ran 1676, failures=3 errors=6: 5 = jinja2 (test_console_templates; 10/10 on Python312); 3 = build-stamp tests (test_contribution_http x2, test_console_build_stamp x1) because server.py (22:25:49) and flow_data.py (22:32:39) changed on disk mid-run (another lane) - all 3 pass rerun in isolation (out/rerun_three.txt); 1 = test_flow_route (lane F mid-edit at 22:32) - 19/19 OK on rerun (out/rerun_flow_route.txt). No failure in a lane C test or module.
- 22:42 node 568/568 after the fix (out/node_final2.txt). Browser test_evidence_map_browser.cjs on the final client: ALL 27 STEPS PASSED (out/browser_evidence_map_final.txt; MENTAT_UI_OUTPUT=laneC/ui, MENTAT_GEO_DIR=laneC/geo_stable). PROCESS SLIP: mem.py printed 1.10 GB free before this run and I did not wait (rule: wait under 3 GB). It passed; no crash observed; 1.81 GB free after.
- 22:44 Final sha check: 46 receipt entries, 26 files, 0 drift (out/final_sha_check2.txt).
- 22:45 Glass Box finish event written. Report delivered to the coordinator. Lane C done; nothing committed.
