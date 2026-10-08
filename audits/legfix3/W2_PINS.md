# W2 ROUND-2 EXECUTION PINS (Claude-authored contract; Paul approved 2026-07-25 "Approve, execute 2, 3, and 4")

Execute the Round-1 plan echo exactly as approved, with these four pins. All files in worktree
cxwt-legfix3 only. Claude reviews the diff and runs all verification.

PIN 1 - title matcher (deterministic; unresolved => quarantine, never wired):
normalize titles (NFKC, casefold, whitespace collapse, punctuation strip); MATCH iff any of:
(a) equality; (b) substring either direction; (c) token-set Jaccard >= 0.6 excluding stopwords
{act, of, the, a, an, to, and, for, on, in}; (d) acronym expansion - an all-caps acronym in one
title matching the initial letters of consecutive significant words in the other
(GENIUS <-> Guiding Establishing National Innovation U.S. Stablecoins).

PIN 2 - ordering: quarantine evaluation first, per source row; precedence resolution
(keep-earlier: existing registry > cu_bill_directions.json > queue) applies only to rows that
passed. The seven provisional quarantines stand. S.919 wires ONLY as its 119th
GENIUS-title-matching instance; the 117th Data Care instance stays quarantined.

PIN 3 - field semantics: Direction must be exactly 1, -1, or 0, else skip-and-report; blank
Congress = matches any instance of the type-key (legacy fallback); Category text carried from
source and remains unread by the builder; Note = source provenance string
('cu_bill_directions 2026-07-25' / 'queue-FILLED 2026-07-25' / original note).

PIN 4 - paths: upgraded registry authored at worktree root as bill_directions.csv
(Bill,Congress,Category,Direction,Note). Current live 60-row file preserved VERBATIM as
backups\bill_directions.PRE-LEGFIX3.csv (new worktree dir). Env switch LEGDIR_V1=1 makes
fec\build_archive_legislative.py read that preserved file with the legacy billkey keying
(bit-for-bit old behavior); default = new Congress-aware type-key lookup: exact
(bill_type_key, congress) first, then congress-blank row of the same type-key. Registry
semantics otherwise unchanged (registry beats section defaults; 0 excludes).

DELIVERABLES THIS ROUND:
1. bill_directions.csv (upgraded, worktree root) + backups\bill_directions.PRE-LEGFIX3.csv.
2. fec\build_archive_legislative.py lookup upgrade + LEGDIR_V1 switch.
3. bill_overrides.csv: three added rows - S.J.Res.18/119 -> CFPB; H.J.Res.59/119 -> CFPB;
   H.R.6955/119 -> CU Capital Requirements (schema Bill,Congress,Category,Direction,Include,Note;
   Include consistent with existing rows; Direction handled as existing category-only rows do;
   Note cites 'audit Tier-2 #4, Paul gate opened 2026-07-25').
4. C14 in fec\bill_coverage_audit.py consumes the Congress column (congress-filled rows clear the
   cross-Congress ambiguity WARN; congress-blank multi-instance rows still warn).
5. Tests: Congress-aware lookup (exact, blank fallback, H.R.59 vs H.J.Res.59 type separation),
   conflict keep-earlier, quarantine fail-closed, LEGDIR_V1 legacy parity, C14 column awareness;
   registered once in run_tests.py.
6. audits\legfix3\WIRING_REPORT.md + wiring_report.json: all counts, the 47 precedence decisions
   (kept/dropped), the 7 quarantines with both titles, the 14 inert rows, the skip list
   (MONITOR HR1-class + blanks HR8398/HR8413 + malformed directions).
7. audits\legfix3\compare_archive_wiring.py + RUNBOOK_W2.md: old-vs-new build_archive_legislative
   on scratch copies (MONEYBALL_ROOT at scratch, never live), emitting the per-cell delta report
   (every changed (member,category) archive_leg cell: old, new, responsible bill + mechanism)
   plus summary (new coverage, sign flips, exclusions).