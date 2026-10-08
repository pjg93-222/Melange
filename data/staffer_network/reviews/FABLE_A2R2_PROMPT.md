# Fable A2R2 corrective review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

Re-review the A2 correction after your `FABLE_A2R_REVIEW.md` verdict of
`REVISE`. Return `PASS`, `REVISE`, or `BLOCK`. This is read-only. Do not inspect
raw packets, label logs, response staging, or holdout outcomes.

Inspect:

- `data/staffer_network/reviews/FABLE_A2R_REVIEW.md`
- `fec/staffer_network/politico_adjudication_run.py`
- `fec/tests/staffer_network/test_staffer_politico_adjudication_run.py`
- `data/staffer_network/receipts/politico_adjudication_framework_20260830.json`
- `data/staffer_network/receipts/politico_adjudication_results_20260830.json`

Corrections made:

1. `build_post_label_receipt` now re-hashes `split_seal.json` against the
   anchored framework receipt before reading partition assignments.
2. It verifies that the sealed split and allocation cover exactly the same
   candidates.
3. `_validated_labels` now rejects any label whose `partition` disagrees with
   the sealed split.
4. `append_label_batch` omits `outcome_counts` for `HOLDOUT` responses while
   retaining aggregate counts for calibration.
5. Negative tests now tamper with the split seal and with a recomputed,
   otherwise self-consistent label partition; both must fail closed.
6. The committed A1 and A2 receipt byte hashes are asserted directly in the
   test suite (`729c...e845` and `9d8b...9117`).
7. The full focused staffer-network suite now passes 53/53 tests.

The committed result receipt is intentionally unchanged because the new checks
validate the original sealed inputs and reproduce the same aggregate receipt.
Confirm that both mandatory findings are closed and that P1/P2 may proceed,
while holdout evaluation, source enablement, human-precision claims, and
canonical merges remain blocked. End with any residual obligations.
