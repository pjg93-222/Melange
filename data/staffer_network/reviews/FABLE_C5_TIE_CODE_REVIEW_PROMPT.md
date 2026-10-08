# Fable C5 tie-remediation implementation review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

Act as a fresh adversarial read-only reviewer. Review the implementation of
your binding T1--T5 revisions and planted-failure controls before any new live
registered collection is allowed.

Read these files in full:

1. `fec/staffer_network/lda_composite_repair.py`
2. `fec/tests/staffer_network/test_staffer_ingest_contracts.py`
3. `fec/staffer_network/schemas/lda_composite_reconciliation_receipt.schema.json`
4. `data/staffer_network/reviews/FABLE_C5_TIE_REMEDIATION_REVIEW.md`
5. `data/staffer_network/reviews/FABLE_C5_ACCEL_PLAN_REVIEW.md`

Evidence already obtained: the complete staffer-network test suite now reports
86/86 passing across 13 modules. No live API retry has occurred since the
preserved fail-closed generation.

Adjudicate specifically:

- whether nondecreasing `dt_posted` validation plus same-timestamp boundary
  localization implements T1 without tolerating a count-equal/identity-wrong
  base pass;
- whether the exact-second cohort response gate proves all of `count <= 25`,
  `next == null`, `len(results) == count`, unique UUIDs, and exact timestamps;
- whether every window uses the repair discipline and static repair windows
  directly prove legacy split-cohort containment;
- whether reconstructed payloads and twin comparison operate on repaired
  UUID/payload inventories rather than unstable raw page layouts;
- whether the extended filter probe genuinely detects ignored/date-truncated
  datetime filters and proves offset equivalence using the same UTC-Z
  serialization as repairs;
- whether all seven requested planted-failure paths are present and meaningful;
- whether schemas and terminal receipts contain enough audit evidence;
- any fail-open path, data-loss path, secret leakage, mutable-root issue, or
  mismatch with R1--R10.

Return exactly one verdict: `PROCEED`, `REVISE`, or `BLOCK`, followed by concise
binding findings. Do not modify files and do not make network requests.
