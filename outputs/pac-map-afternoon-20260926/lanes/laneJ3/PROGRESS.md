# Lane J3 PROGRESS: follow-ups to lane J2 (lane-j3-20260926)

Status: DONE, 2026-09-26 (about 15:45 EDT). Three change sets are applied LIVE to C:\Users\pgoff\Mentat (branch
codex/mentat-crypto, HEAD fadd2c751). Nothing is committed; no git writes; the lead commits.
Every write went through laneJ3\apply_changeset.py (lane J2's writer): sha256 checked before writing (abort on
drift), original backed up to laneJ3\backup\, atomic write, each region's own line endings kept, recorded in
RECEIPT.json (sha before/after, backup, EOL census, changed ranges; unified diffs in diffs\). Each change set was
pre-flighted on a mirror (laneJ3\mirror) and negative-controlled on a second mirror holding J2's code
(laneJ3\mirror_old). Close-out re-hash: all 14 files still as written.
Before writing, p00_drift.py confirmed every file J2 wrote was still at J2's last sha (no drift).

## Change sets (live)
| CS | what | files (sha before -> after) |
|---|---|---|
| 1 | Task 1: revert J2's same-day narrowing of F13; the approved rule is back (on or before, latest-dated then lowest sub_id). J2's other changes kept (back-reference `back_reference_amount_differs`, giving_rulings/H3, Flow sold_asset, date-ordered refund netting, the memo_link_unproven columns). | schema.R f6bb4d84->563759a1; pac_evidence.py 938287ed->50770612; collect.R c385150f->d5d53920 (comment); export_crypto_spending_data.R f41d7e67->151b5ac1 (comment); fec_receipt_rules.json 6046287f->640adee8 (disclosure_rule text); METHODOLOGY.md c8823c4f->563c0d00 (lines 58, 102); fixture memo_redisclosure_cases.json fb2d4436->6e4fb754; test_memo_redisclosure.py 5f1ae01e->a8cc4438; test_memo_redisclosure.R 072162b1->9f125234; test_export_memo_reason.R ecfcf62b->805721ab |
| 2 | Task 2: "NON CONTRIBUTION" leaves non_giving_exact_descriptions, so a line-17 receipt whose text is exactly NON-CONTRIBUTION counts, flagged receipt_role_unverified (reason unverified_other_receipt). Both twins read the list; each twin got the same comment. | fec_receipt_rules.json 640adee8->ad8b954f; collect.R d5d53920->00998ec4; pac_evidence.py 50770612->55e0d45e; METHODOLOGY.md 563c0d00->6f45e38a (line 66); test_pac_evidence.py 001257e7->7da5e167; test_receipt_roles.R 0273ba2a->b285b2e7 |
| 3 | Task 3: L3's retrying async cleanupPath (verbatim; identical to the text in L3's suites), awaited in each finally. | test_evidence_panes_browser.cjs 2442c92a->ef784907; test_navigation_scope_browser.cjs 693e518b->3a71a149 |
Code check: the F13 function bodies in schema.R and pac_evidence.py, and summarize()'s F13 lines, are identical to the
pre-J2 originals, comments aside (p07_twin_vs_prej2.py).

## Figures (before = live J2 state, after = J3), existing caches only
| surface | before | after |
|---|---|---|
| Crypto workbook, Coinbase, all cycles | 146,127,010.40 | 130,627,010.40 |
| Coinbase 2024 | 95,237,364.72 | 79,737,364.72 |
| Foris Dax Inc, all cycles (2026) | 3,725,442.74 (3,702,594.00) | 38,725,442.74 (38,702,594.00) |
| Gemini, all cycles | 1,393,290.32 | 1,393,290.32 (see premise correction) |
| Flow totals.in FAIRSHAKE 2024 / 2026 | 217,423,880.52 / 201,949,015.24 | same (whole payload identical) |
| Flow totals.in SLF 2022 / 2024 / 2026 | 291,585,189.02 / 299,928,947.50 / 259,424,418.59 | same |
| Saved FAIRSHAKE evidence.json (H2) | sha e0e4a597..., 7 memos counted, 155,499,995 | byte-identical |
Crypto replay: 5 of 14,839 rows change. Memo 4021420241824800143 ($15.5M) is removed as
memo_redisclosure_of_counted_parent against 4021420241824800115. Foris DAX's four MAGA Inc. rows (SA17.4519
2025-02-14 $10M, SA17.4920 2025-09-12 $10M, SA17.4959 2025-10-22 $10M, SA17.5207 2026-01-23 $5M) now count,
flagged; recipient category Carey. Their FEC type 10 is "Contribution to a Super PAC, hybrid PAC or non-federal
account" in inputs/fec_transaction_types.json. No other copy of that money is in the Crypto DB (p03).
A fresh summary held only in memory (not saved; H2) would remove all 7 FAIRSHAKE memos, $155,499,995. ARK INVEST's
$156,915.82 and $522.62 memos (2023-12-13) are removed against their 2023-12-12 in-kind parents.

## Premise correction (Gemini, $45,000)
SUB_ID 4041620251184328235, Serbian American PAC: the donor is an individual, PETKOVICH, GORAN M (employer GEMINI
TRANSPORT). The collector's persistent override rejected the Gemini match (persistent_override:reject, which is an
explicit rejection prefix). The export therefore removes it as R3 explicit_source_exclusion, a D-040 contradiction,
before any role rule applies. Its filing form is blank, so its role is unverified_receipt_role in any case. The
label rule never removed it, and Gemini's total does not move. J2's probe p23 forced filing_form F3X, which is why
it was listed. test_receipt_roles.R now pins it as a negative control.

## Pins changed (before/after/reason for each is in RECEIPT.json, 20 records)
- Fixture v2->v3. The rule text is back to the approved text. The pre-J2 values of three cases are restored:
  fairshake_15_5m, d040c memo F13-M9 and several_parents F13-M23. J2's boundary case is renamed
  parent_dated_the_day_before_is_its_parent and now pins removal. J2's two same-day cases still hold unchanged.
- test_memo_redisclosure.py: J2's "15.5M stays counted" test is replaced by one pinning its removal as
  memo_redisclosure_of_counted_parent. The restated-pairs list and the included total are back to pre-J2. The
  negative control now flips the $15.5M memo to J2's verdict.
- test_memo_redisclosure.R: the negative control is changed the same way. J2's "earlier parent is a clue" check now
  pins removal against the latest earlier parent. The database-path ids are back to 6.
- test_export_memo_reason.R: the example inputs name back_reference_amount_differs instead of the retired reason.
  It is the same check, not weaker.
- test_pac_evidence.py: NON-CONTRIBUTION moves from other_receipt to unverified_other_receipt in 2 places. New
  NonContributionLabel class (2 tests: the real Foris rows, plus a negative control on explicit text).
- test_receipt_roles.R: in specials, row 4 is now unverified_other_receipt and countable. The exact-caption list
  loses NON-CONTRIBUTION. New checks cover the Foris rows, the explicit-text negative controls and the Petkovich row.
Negative controls: J2's code fails the CS1 pins (8 Python failures; the R fixture fails on the 4 re-pinned cases).
The 09-17 rules fail the CS2 pins (3 Python failures; R fails at specials). Outputs are in negctl\.

## Version / cache decision
fec_receipt_rules.json stays at v7. No code reads the version number: only three test pins do. Every
rules-dependent cache keys on the file's bytes and re-keys by itself: build_industry_report.ps1 data-input
fingerprint, contribution_data.py RULE_PATHS, and run_cross_reference.py rule_fingerprints (provenance only). Saved
evidence is never re-summarized (H2). There is nothing to rebuild under DE-033/DE-034.
Stale until rebuilt, for scheduling (Paul's call; data-mutating):
- The published Crypto workbook: only Crypto's numbers change.
- Any running console, until it restarts (D-029).
Caveat: J2's v7 was never committed. Commit J2's and J3's rules edits together, or "v7" will name two contents in history.

## Tests (live tree)
- py-core: 126 ran, 0 failures.
- py-flow: 55 ran, 0 failures. IndustryRefunds (2) was left out under the RAM rule, and it cannot move: the Flow skips memos, does not tell other_receipt from unverified_other_receipt, and the Banking DB holds no bare-label row (p04).
- py-downstream: 92 ran, 0 failures.
- Extra sweep: test_cross_reference_data, _store, test_raw_contribution_columns, test_receipt_metadata_hydration: 41 ran, 0 failures.
- R: test_memo_redisclosure, test_receipt_roles, test_rules, test_export_memo_reason, test_report, test_tidy_stage, test_raw_contribution_columns, test_reconcile: all PASS.
- node --test flow-layout, flow-chart, studio-flow: 40/40.
- Browser under the venv: evidence_panes 35/35 and navigation_scope 17/17, with no new %TEMP% folder and no cleanup message. navigation_scope's own teardown printed "browser.close() exceeded its 20000ms bound" after its pass line; that is before the cleanup code, and the run shared the CPU with the replay.
- git status is identical before and after the sweep.
Left in place: four older, non-empty %TEMP% folders from the evidence-panes suite (mentat-s6-data-G7YBRS and mentat-s6-fixtures-3cWQr2 from 09-20; mentat-s6-data-Ol4ZBx and mentat-s6-fixtures-H7y9O6 from 09-22).

## Open (lead / Paul)
1. Publication: the Crypto workbook needs a rebuild to show Coinbase 130,627,010.40 and Foris DAX 38,725,442.74.
2. Adjacent, not changed (outside the brief): "NON-CONTRIBUTION AMOUNT" stays an exact non-giving caption. It is the same kind of bare label. The saved Crypto rows have none; other DBs were not counted.
3. J2's brain draft named "an F13 parent on or before the memo" as a dead end. That draft is now wrong; see below.

## Brain drafts (for Paul to apply)
- DECISIONS (amend J2's draft "Money leaves a count only on proof..."):
  - Proof includes F13: the memo's own re-disclosure statement plus a counted parent (same company, recipient, contributor and amount, dated on or before the memo).
  - A bare "NON-CONTRIBUTION" on line 17 counts as the named donor's giving, flagged receipt_role_unverified. It is no longer excluded as a stated non-giving role (the 09-17 codification in 7d364883e is reversed).
- DEADENDS: replace J2's draft with "Requiring an F13 parent dated the same day as the memo" (lane J2, reverted by lane J3 the same day).
  - Failure mode: it discarded the filer's own re-disclosure statement and counted Coinbase's $15.5M USDC gift twice. ARK INVEST's $157,438.44 in two memos would also be counted twice in any fresh summary.
  - Root cause: the proof is the statement plus the counted parent, not the date.
  - Would reconsider if: Paul rules that a filer's statement is not proof.
- STATE: lane J3 is applied, uncommitted. RECEIPT.json lists 14 files. The Crypto workbook rebuild is pending.
