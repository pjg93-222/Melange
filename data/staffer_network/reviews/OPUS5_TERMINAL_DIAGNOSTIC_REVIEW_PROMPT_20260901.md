# Opus 5 terminal diagnostic-package review

Use Claude Opus 5 at maximum effort. Perform a final read-only adversarial review; do not edit any file or infer a verdict from a missing result, timeout, test count, or earlier scoped `PASS`.

Read the implementation diagnostic and Claude handoff in full. For the four
governing documents, inspect only their authoritative `2026-09-01` addenda and
the exact sections those addenda supersede. For stage evidence, inspect only
the named status/count/hash tables and verdict blocks:

- `audits/staffer_network/STAFFER_NETWORK_EMPLOYMENT_IMPLEMENTATION_DIAGNOSTIC_20260901.md`
- `STAFFER_NETWORK_EXPANSION_DESIGN_20260830.md`
- `STAFFER_NETWORK_METRICS_20260830.md`
- `STAFFER_NETWORK_CORPUS_SPEC_20260830.md`
- `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md`
- `data/staffer_network/reviews/CLAUDE_OPUS5_EMPLOYMENT_IMPLEMENTATION_HANDOFF_20260901.md`
- the A5c status/count/hash section in the implementation diagnostic;
  `audits/staffer_network/A7_MACHINE_LOCAL_SOURCE_INVENTORY_DIAGNOSTIC_20260901.md`;
  `audits/staffer_network/A8_HOUSE_SOD_1997Q1_LDA_MATCH_VERIFICATION_20260901.md`;
  and `audits/staffer_network/A9_A7_A8_PRIORITY_SIDECAR_DIAGNOSTIC_20260901.md`
- `data/staffer_network/reviews/OPUS5_STRUCTURAL_MATH_MICROREVIEW_20260901.md`, `OPUS5_INTERVAL_COTENURE_MICROREVIEW_20260901.md`, and `OPUS5_REVOLVING_DOOR_MICROREVIEW_20260901.md`
- all five timeout non-verdict records: `data/staffer_network/reviews/OPUS5_NETWORK_TEMPORAL_MATH_FINAL_TIMEOUT_20260901.md`, `OPUS5_TEMPORAL_MATH_MICROREVIEW_TIMEOUT_20260901.md`, `OPUS5_EMPLOYMENT_GATE_TERMINAL_TIMEOUT_20260901.md`, `OPUS5_EMPLOYMENT_CORE_TERMINAL_TIMEOUT_20260901.md`, and `OPUS5_EMPLOYMENT_CONSOLIDATION_TERMINAL_TIMEOUT_20260901.md`
- the direct employment constituent result files, including `OPUS5_EMPLOYMENT_DATE_IDENTITY_MICROREVIEW_20260901.md`, `OPUS5_EMPLOYMENT_COMPLETENESS_ATTESTATION_MICROREVIEW_20260901.md`, `OPUS5_EMPLOYMENT_IDENTITY_CONFLICT_POSTFIX_REVIEW_20260901.md`, `OPUS5_CONSOLIDATION_ATTESTATION_MICROREVIEW_20260901.md`, `OPUS5_CONSOLIDATION_ATTESTATION_POSTFIX_REVIEW_20260901.md`, `OPUS5_CONSOLIDATION_ATTESTATION_FINAL_REVIEW_20260901.md`, and `OPUS5_CONSOLIDATION_IDENTITY_ACCOUNTING_MICROREVIEW_20260901.md`
- both receipt `BLOCKED` results, `OPUS5_CONSOLIDATION_RECEIPT_DETERMINISM_MICROREVIEW_20260901.md` and `OPUS5_CONSOLIDATION_RECEIPT_POSTFIX_REVIEW_20260901.md`, followed by the scoped final `PASS` in `OPUS5_CONSOLIDATION_RECEIPT_FINAL_REVIEW_20260901.md`
- any reconciliation verdict file, only if it exists when reviewed; absence is not a verdict
- the broad regression claim for `python -m pytest -q fec/tests/staffer_network audits/staffer_network`: 222 tests plus 73 subtests, zero failures

Compute SHA-256 only for files with embedded pins or verdict files cited by the
package. Compare on-disk values with those pins and flag every stale hash,
stale count, contradictory status, unsupported scope, or stronger-than-receipt
claim with exact file/line evidence. Do not broaden into code review; the task
is package truthfulness and terminal disposition.

Return exactly one package verdict: `VERDICT: PASS` or `VERDICT: BLOCKED`. `PASS` means only that the diagnostic package accurately distinguishes implementation/code/math readiness from actual-corpus incompleteness. Block if it fails to preserve any of these controls:

1. exact sealed scope of 25,340 IDs;
2. A9 evidence combinations FEC-only/A8-only/both/neither = 37/388/0/24,915, A8 moves 77/89/43 from P0/P1/P2 to P3, FEC moves zero, and revised P0/P1/P2/P3 = 11,643/4,843/1,741/7,113;
3. zero canonical employment and identity promotions, with every A7–A9 addition remaining review-only;
4. A5c as honest partial recovery: one acquired target quarter, 51 unacquired, 4,939 OCR candidates, and no full-history inference;
5. structural, interval, revolving, and any terminal-employment `PASS` as separately scoped code/math verdicts, never actual employment-corpus completion;
6. the receipt-review sequence as `BLOCKED`, `BLOCKED`, then scoped final `PASS`, without erasing either accepted blocker round;
7. all five recorded Opus timeouts as non-verdicts; and
8. the broad regression count as implementation evidence only, not completeness, adjudication, or publication authority.

Then return `META_LOOP_DISPOSITION: BLOCKED`. The package must recommend terminal Meta LOOP blockage—not success—until complete-lifetime employment evidence, exhaustive gap disposition, and identity/employer/container/chronology adjudication exist. Finish with `BLOCKERS`, `NONBLOCKING_FINDINGS`, `STALE_HASH_OR_CLAIM_FINDINGS`, and exact `EVIDENCE` citations. No verdict may authorize canonical promotion, temporal production scoring, causal claims, public release, or project closure.
