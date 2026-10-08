# Fable P2 residual-closure review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

## Verdict: PASS

Fable verified all six binding requirements directly in code, tests, and
committed receipts.

- **R1 met:** the registered legacy schema requires exactly six fields, fixes
  the restricted namespace, and is additive to public-safety, blank-row, and
  exact-count checks in both construction and local validation.
- **R2 met:** schema types match the sealed rows; the exact upgraded replay
  matched the committed 873,236-row validation receipt and corpus hash
  `3914df98…604e2` without rewriting a receipt.
- **R3 met:** the registered restricted schema is explicitly refused by public
  generation publication, with a negative control.
- **R4 met:** valid, dangling, and malformed boss controls preserve a valid
  namespaced ID, redact bad values, increment the receipt counter, and prove
  the absent identifier is not in decompressed output bytes.
- **R5 met:** 26 schemas and 75 tests passed at review time; 2026-08-29 byte
  preservation remained green and the unrelated committee/IPEDS/container-gold
  residual stayed open.
- **R6 met:** no source, identity, analysis, LDA, Politico, consumer, or
  `STAFF_NET` gate moved. Boss namespace semantics have their own negative
  control.

## Non-blocking observations

1. Add load-side refusal as defense in depth against a hand-forged generation
   that names the restricted schema.
2. Avoid presenting the observed 179 valid boss links as receipt-bound; only
   the zero-redaction claim is a committed receipt field.
3. Reject float `boss_id` values rather than allowing `int()` to truncate them;
   extend the malformed fixture accordingly.

Codex accepted all three observations for immediate remediation before stage
closure. Fable made no file changes.
