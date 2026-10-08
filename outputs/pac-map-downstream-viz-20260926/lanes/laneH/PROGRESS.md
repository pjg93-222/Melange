# Lane H PROGRESS (F13: memo re-disclosure rule, approved by Paul 2026-09-26 "Approve F13")

Repo C:\Users\pgoff\Mentat, branch codex/mentat-crypto, HEAD 3cec985249b098478868b8729e33b5b4ab31752e at start (01:48 EDT 2026-09-26).
No git writes. No commits. Lane A owns R/fec_transfer_graph.R, R/fec_beneficiary.R, tools/export_crypto_spending_data.R: NOT touched.
Writes only via laneH\apply_edit.py (sha/drift-checked, byte backups in backup\, atomic, region EOL kept, RECEIPT.json, diffs\).
Glass Box: run lane-h-20260926 source memo-redisclosure.

## Status log
- 01:48 started. schema.R / collect.R / report.R clean vs HEAD at start (git status).
- 01:50 FAIRSHAKE rows read (h01_out.json): the four 2024-12-20 $23M memos DO state a re-disclosure
  ("236.20702457 Bitcoins (BTC) contribution - previously disclosed (aggregate YTD from 2024)") -> F13 covers them.
  $5 memo "5 USDC CONTRIBUTION PREVIOUSLY DISCLOSED (UNITEMIZED)" has no itemized parent -> stays counted, flagged.
- 02:00 census of memo texts in all 8 industry DBs (h03), static scan (h04/h06): phrases attested = PREVIOUSLY DISCLOSED,
  CONTRIBUTION DISCLOSED(ON) ON LINE 11(A), ORIGINAL CONTRIBUTION AS PREVIOUSLY REPORTED, PREVIOUSLY REPORTED CONTRIBUTION,
  AS ORIGINALLY REPORTED, ORIGINALLY DISCLOSED IN M06 REPORT. Bare PREVIOUSLY REPORTED only in JFC "SOME ALLOCATIONS
  PREVIOUSLY REPORTED" memos -> left out. No re-disclosure memos for Ripple/a16z/Jump/Winklevoss/Kraken.
- 02:12 BEFORE replay (pre-F13 code, h07_replay.R before): FAIRSHAKE 2023-2024 $202,011,174.52 (reproduces lane F), 0 memo
  duplicates, 14 disclosure memos counted. Baseline suites: 11 R + 12 py (278 tests) all PASS (suites_before).
- 02:35 edits applied (12 specs; RECEIPT.json). Coordinator note: lane A landed F12-R; replay is the receipt stage only
  (paths/schema/ingest/collect/fec_api/report), so before/after differ by F13 alone.
- 02:40 new suites: R test_memo_redisclosure.R (26 cases, 28 statements, precedence, DB path) PASS; py 9 tests PASS.
  Negative controls (h09): with F13 switched off the R suite fails and 22 py checks fail.
- 02:45 AFTER replay: FAIRSHAKE 2023-2024 $69,506,179.52 = $69,506,174.52 + $5 unitemized memo (flagged). 13 memos out
  ($132,541,695.00); DB global-plan flags = export plan flags (13 = 13); every parent kept, same company, same cycle.
  Other Crypto moves: GMI PAC 2022 -25,000; Coinbase Innovation PAC 2022 -9,900; Trump National Committee JFC 2024 -1,800.
- 02:50 all suites after: 12 R + 13 py PASS (suites_after); system Python 3.12: 104 tests OK.
- 03:00 static scan with the live Python twin (h11): Banking 10 memos out ($25,545), 15 counted+flagged (review status or no
  parent); Credit Arms 2 out ($4,500); Telecom 2 flagged; Community Banks 1 flagged; P&C, Fintech, Credit Union none.
  Saved PAC evidence (h12): snapshot-b2676188 would drop 7 memos ($155,499,995; 3 more 2026-filed $23M memos than the DB
  copy); snapshot-2eb1b6d6 (cycle 2026 only, parent not in it) keeps its 5 memos flagged. Saved evidence NOT rewritten.
- 03:10 perf (h14, 900k synthetic rows): F13 alone 10.3 s -> 0.7 s after the subset rewrite; replay byte-identical.

## Map: where memo rows count today
- R: collect.R fec_receipt_role -> memo + disclosure_pattern => unverified_disclosure_memo (countable, flagged disclosure_memo_unmatched).
  schema.R mentat_memo_duplicate_plan: FEC back-reference, and now F13; apply_amendment_versioning persists duplicate_memo;
  report.R spending_raw_report_rows recomputes the plan on export; collect.R fec_receipt_row_eligible drops duplicate_memo==1;
  export writes inclusion_reason "Memo duplicate: <reason>; retained source <parent>"; report_source_guard checks the parent is included.
- Python console: downstream.py / flow_data.py / evidence_geo.py skip EVERY memo row -> F13 changes nothing there.
  tools/pac_evidence.py summarize(): receipts -> F13 mirror (included_company_contribution False + duplicate_of_sub_id/duplicate_reason).
  tools/cross_reference_engine.py analyze(): F13 mirror (exclude, link kind memo) -> Contribution Studio ledgers.
  graph_data.report_facts / report_insights read the workbook's include_in_analysis / Analysis Amount -> follow the R export.

## Open for the coordinator / Paul
- Saved .cache/pac-evidence evidence.json files predate F13 (display in /api/evidence); re-summarize needs a go (lanes pin them).
- Running consoles raise "Accounting code changed. Restart the app" for contribution datasets until restarted (rules/pac_evidence edits).
- Export's receipt_role_reason still says disclosure_memo_unmatched on EXCLUDED memos (export file = lane A's).
