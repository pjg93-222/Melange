# Opus 5 consolidation receipt/determinism micro-review

- Stage: `R0a2a4b3-opus5-consolidation-receipt-determinism`
- Model/effort: Claude Opus 5 / maximum
- Mode: read-only
- Verdict: `BLOCKED`

## Blockers

1. Receipt validation trusted row-conservation booleans without re-deriving
   `input_rows == accounted_input_rows` and
   `identified_input_rows == consumed_identified_input_rows`, so a forged PASS
   could hide lost rows.
2. `unidentified_reason_counts` did not have to sum to unidentified rows.
3. Duplicate-person counts were not coupled to duplicate-row counts or the
   output-uniqueness boolean.

The coordinator accepted all three blockers and added independent cross-field
checks, forged-receipt fixtures, empty-input and unseen-queue blocking, queue
row conservation, and artifact/file inventory counts. The Python verification
then passed 47 focused tests and 221 staffer tests plus 73 subtests. A fresh
post-fix Opus review is required.

## Checks that passed

Status derivation itself was evidence-based; schema PASS requires no incomplete
reasons; producer file hashes are calculated after writes; canonical JSON and
gzip mtime make the producer deterministic; and primary/twin tests compare raw
bytes.

## Nonblocking findings

Output hashes are not independently reopened by the standalone semantic
validator; output file row counts are not in the receipt; the existing
determinism fixture is small; and writes are non-atomic. These remain hardening
items and do not supersede the repaired forged-PASS blockers.

This preserved BLOCKED verdict covers receipt safety only.
