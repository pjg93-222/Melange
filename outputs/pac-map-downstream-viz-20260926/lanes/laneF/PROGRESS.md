# Lane F PROGRESS (Flow Sankey, boards #44 #45 #46)

Port 8853. Glass Box run_id lane-f-20260925 source flow-sankey. Repo C:\Users\pgoff\Mentat branch codex/mentat-crypto.
Mentat HEAD at start: 3cec985249b098478868b8729e33b5b4ab31752e (21:17 EDT 2026-09-25).
No git writes. Writes to Mentat only via laneF\apply_edit.py (sha-checked, backup, atomic, EOL-preserving, RECEIPT.json).

## Status log
- 21:17 started. Read packet s0+s4, boards b44 b45 b46 B19 board6.
- 21:18 lane C NOT landed (PROGRESS: graph.js next). Lane M NOT landed (UI next). evidence.js untouchable for now.

## Next
- read money facts (s20/s21, laneD v02), downstream.py, server.py evidence-network route, evidence.js (read-only until lane C lands)
- 21:55 flow_data.py installed (mentat/app, new) + server.py /api/flow hunk (after /api/evidence-network block).
- 22:20 contracts/flow.json v1 CREATED (gitignored *.json -> Paul must git add -f); mentat/tests/test_flow_route.py 15/15 on system py + codex runtime py.
  FAIRSHAKE 2024 identity reproduces to the cent (217,423,880.52 = 54.55M + 31.7M + 40,661,820.61 + 3,267,861.97 + 87,244,197.94).
  SLF 2024 loops: back from AC 1,305,577.91 / AF 5,000,000 / NHA 1,000,000; AC returned-to stub 1.3M; CAP->AF date_order_ok false.
- NEXT: flow-layout.js + node tests; flow-chart.js; evidence-flow.js; industry flow + graph-flow.js; templates; browser pass.
- 22:30 installed: flow-layout.js/flow-chart.js (+tests 17/17), evidence-flow.js, graph-flow.js, flow.css, STATIC_ASSETS hunk, page_head.html tags, index.html re-rendered (--check OK).
- 22:35 industry flow (root=industry) in flow_data; server route resolves workbooks like /api/graph (run=published-reports).
- 22:45 coordinator F12 heads-up: producer made regime-tolerant (uncounted sink, date_unverified passthrough), tests take downstream figures from the measurement. py 19/19.
- PENDING: evidence.js hook (lane C finishing: last write 22:10, HUNKS_FINAL written); console 8853 + browser proof; lane M check for (c).
- 22:40 evidence.js hook applied (7 hunks, pinned to lane C sha 4ee9408b); lane C wrote again 22:40:11 on top (b859873f->e9f3b45a), hunks intact.
- 22:55 label-aware layout, two-line labels, tooltip shares; console restarted; final captures 1440 + 1920 all OK (shots/final_*).
- 23:05 proof/side_*.png composed. Suites: node 568/568, py 70/70, render_console --check OK. Console 8853 STOPPED.
- DONE except (c) Chart Studio Flow mark: lane M not landed (final sweep) -> pending. F12 (lane B) not landed: producer + tests regime-tolerant.
- 23:25 COINBASE BREAKDOWN (read-only) DONE; full text goes in the final report. Key figures (evidence: laneF/q02_out.json, q04_out.txt):
  published 2023-2024 Coinbase->FAIRSHAKE $125,511,179.52 = (a) cash 11AI $6,001,179.52 + (b) in-kind 11AI $63,504,995.00
  + (c) line-17 sale proceeds COINBASE COMMERCE (EXCHANGE) $40,505,000.00 + (e) line-17 memo X re-counts $15,500,005.00 ($15.5M DISCLOSEDON memo + $5 unitemized); (d) 2026-filed memos $0.
  flow $69,506,174.52 = (a)+(b); gap $56,005,005.00 = (c)+(e). D-040(c) rows ($19,767,475) are 2025-26 FAIRSHAKE x3 + CLF, none in the gap.
  Replay of TODAY's R export (copy of the Crypto db): 2023-2024 = $202,011,174.52 (sale proceeds dropped, but all 7 disclosure memos $132,505,000 counted: memo plan now needs an FEC back-reference, schema.R:958-990).
- NEXT (coordinator 23:20): part (c) Chart Studio Flow mark (lane M landed), (i) scope.js Flow URL key + url_scope.json, (ii) regenerate flow contract after lane B F12.
- 23:55 F12 in flow: gated citations, before-gate stubs (disclosed, no ribbon), date_unverified; contract v2 (12 neg controls); py 19/19 both pythons, JS 17/17. SLF: CAP->AF out, AF $5M now a donor, before-gate $8,126,723.65 disclosed. NEXT: evidence.js map text (F12), then (c), (i), carryover labels when lane B lands.
- 00:10 evidence.js F12 wording (6 hunks on lane C's e9f3b45a -> 74c88773) + app/tests/evidence-date-rule.test.js 4/4 incl. negative control; lane B F6 test 3/3 still green.
- (clock correction: the three notes above marked 23:25/23:55/00:10 were written at about 23:05/23:15/23:29 EDT)
- (i) DONE: scope.js <pane>.flow (reported|attributed), url_scope.json v7 (+1 example, +1 negative control), version pins in scope.test.js + graph-navigation.test.js (90/90), evidence.js writeScope/restorePanes/openFlow, evidence-flow.js basis+onChange. NEXT: part (c) Chart Studio Flow mark.
- 00:35 (c) model/renderer/hooks INSTALLED: core 0add1c9c (Flow card type + flow options + compileFlow/flowSwitch/quickAddZone/swapShelves;
  lane P's map-layer lines context only), studio-flow.js NEW, chart-studio.js c13609ca (6 hooks), server 65600605 (_flow_ok, VIEW_* |= flow,
  /studio-flow.js), page_head 34987b6b, index.html b2656f54 (render --check OK), flow.css f013b01a, flow-layout otherMembers/keyed ribbons,
  flow-chart text sizes/recolour/legend/formats. app/tests/studio-flow.test.js 17/17 (2 negative controls).
- 00:55 CARRYOVER (b) landed (lane B): flow_data carryover_of/carry_notes/carry_summary (gate_source on committee nodes, carryover label +
  opened_by, prior_cash stub carries the label, notes in the measurement's words, payload.carryover); flow-chart tooltip, flow-layout
  subline "· carried over"; evidence.js carryClause on the Spent map line. Root-inflow rule now sets aside the disclosed 'Not in the summary'
  stub (FAIRSHAKE 2026 false positive, identical with carryover on/off). Contract rule: carried-over label consistency (py+js parity).
  flow.json v3 (641725bb): +FAIRSHAKE 2025-2026 real example, +1 negative control (13). Recon equal: FAIRSHAKE 2024 (219,291,906.56;
  identity 217,423,880.52 holds; carryover unknown), FAIRSHAKE 2026 (Walkinshaw 1,012,792.00, Pekarsky 10,241.45), SLF 2024
  (before-gate 7,792,186.24 = 8,126,723.65 - 334,537.41; American Crossroads carried over, 'gate opened by 2021-2022 transfers').
  py test_flow_route 24/24; JS flow 37/37; evidence-date-rule 6/6. Gates are never re-derived in the flow (gate_of + observations(gate=)).
- NEXT: (c) real-client pass (first try failed: #studio-source-mode hidden in a folded panel), contract studio_api v4, pins, suites.
- 01:40 (c) DONE. Real client on 8853 (laneF/studio_capture.cjs): Crypto Overview 2023-2024, Flow tile, 4 stages, Size SUM(Analysis Amount):
  13 nodes, 29 ribbons, $145,462,078.45 reconciles to the worksheet's SUM over 3,383 rows; saved view (real save_view write), reopened in a
  FRESH browser context from Views > Open view: identical; options (Gradient/top 5/alphabetical/65%) and Colour: Employee Tier (41 ribbons,
  Ribbon colour locked with reason); no page errors. Side-by-sides: proof/side_b46_studio_flow_{1440,1920,colour_1920}.png.
  studio_api.json (df402508; version stays 3 as lane P did) + marks_card_flow/views_save_marks_flow/views_get_marks_flow + 9 lane-F controls;
  lane M counts 14->23 (JS+py). New tests: app/tests/studio-flow.test.js 18, tests/test_studio_flow_contract.py 4.
  (i) browser: a.flow=reported permalink reopens Flow; Attributed writes a.flow=attributed (409 offered back); Back clears the key.
  Carryover in browser: FAIRSHAKE 2026 Protect Progress tooltip + 'carried over from 2023-2024' line + foot; Spent map line clause.
- Suites: node 615/615; py 92/92 (flow, studio contracts, templates, contribution_http, map_layers_server); codex py 28/28;
  render --check OK; browser: sections-freedom 3/3, board 20/20. Console 8853 STOPPED.
- 02:20 LANE I DEFECT (SLF 2022 "Negative flow donor:WEIRMAN ROBERT"): ledger() nets a contributor's negative entries against
  its receipts in the window; <= 0 never drawn; below zero = refunds_to_donors (intake gross; root "Refunded to donors" sink
  with details; elsewhere the kept remainder); zero-net disclosed; note "Refunds to donors $X". flow_data 234103ee.
  Sweep (sweep.py via 8853): 42 snapshot units x (Top 8, top 0, attributed) = 126 answers, 0 bad after fixes. Found: negative
  line-16 entries (CULAC refunds from candidate committees $31K/22K/6.5K; America Fund 2024 state PACs $1,383,041.72) - words now
  say "negative entries as filed" with each line; SLF 2026 Top 8 carryover mark left on a stub merged into Other -> group()
  drops it (py+js parity), members keep the label. flow.json v4 (b30b9778, 10 examples, 14 controls). py 29/29, JS flow 40/40.
- 03:05 industry sweep found 3 x 409 conservation at bucket:candidates (Banking 2022 $265, 2024 $50, P&C 2022 $66.50): company-
  recipient pairs below zero were undrawn but the bucket passed on the recipient's NET total. Now each pair nets on its own; the
  bucket passes on what it drew; "Refunds from candidates $X" note. Full sweep again: 42 snapshot units + 24 industry roots =
  150 answers, 0 bad. flow_data e53b5d02; flow.json v4 ba4d16a2. py test_flow_route 31/31; JS 617/617; codex py 35/35.
  Real client (refund_capture.cjs): SLF 2022/2024/2026, FAIRSHAKE 2024/2026 drawn, validate clean, 0 negative links, recon equal,
  FAIRSHAKE 2024 totals.in 217,423,880.52; SLF 2022 sink tooltip shows $60,000 filed + $5,500 negative receipts (Dyke, Weirman).
- 03:15 test_evidence_map_interaction_browser.cjs: step 6 now Summary|Map|Flow|Rows; new step 7 opens Flow and returns to Map
  (import pane: Flow says it reads a saved FEC snapshot, as the Spent map does, and asks /api/flow nothing; evidence-flow 186e0e9a).
  23/23 green with MENTAT_UI_OUTPUT=laneF/ui-output, zero console errors. Console 8853 STOPPED.
