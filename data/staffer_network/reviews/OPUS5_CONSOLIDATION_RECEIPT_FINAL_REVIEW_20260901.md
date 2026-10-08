# Opus 5 consolidation receipt final review

**Model:** Claude Opus 5, maximum effort, read-only  
**Verdict:** `PASS`

## Blockers

None. Every prior receipt blocker is re-derived from counts rather than trusted
from booleans, and the reviewed forgery paths fail closed.

## Re-tested identities

| Required check | Reviewed location | Result |
|---|---|---|
| input = identified + unidentified | `consolidate_employment_corpus.py:433-437` | present |
| dropped = unidentified | `:438-441` | present |
| accounted = consumed + dropped | `:442-446` | present |
| input = accounted | `:447-449` | present |
| identified = consumed | `:450-453` | present |
| unidentified reasons sum to unidentified rows | `:454-457` | present |
| duplicate IDs are bounded by duplicate rows, zero iff zero | `:458-466` | present |
| duplicate rows = consumed rows - processed people | `:467-471` | present |
| output duplicate count agrees with uniqueness flag | `:472-475` | present |
| status counts sum to processed people | `:476-481` | present |
| residual rows = processed people - complete people | `:482-485` | present |
| queue rows = processed + unseen people | `:490-493` | present |
| artifact count equals manifest length | `:494-496` | present |
| file inventory equals five fixed files + workers | `:497-499` | present |
| empty input prevents PASS | `:506-507`, `:402-403` | present |
| unseen queue people prevent PASS | `:508-509`, `:404-405`, `:681-683` | present |

The schema's nonnegative duplicate-row count plus the exact row-to-person bridge
forces `processed_people <= consumed_identified_input_rows <= input_rows`.
Inflated-people and false-residual forged receipts are rejected by dedicated
tests. Producer and validator incomplete-reason ordering agree. Receipt semantic
validation occurs before the receipt itself is written.

## Nonblocking findings

1. Three conservation-failure enum members are unreachable because hard
   semantic validation raises before such a receipt can be written. This is
   fail-closed but leaves dead enum/status branches.
2. Six inspected checks do not have isolated forgery tests: empty input, unseen
   queue people, queue conservation, artifact count, file inventory count, and
   duplicate-person-ID bounding.
3. The `row_loss` forgery mutates several fields and therefore proves the named
   check is present, not that it is the only independently sensitive check.
4. File and input-artifact inventory validation is cardinality-only; role
   uniqueness and artifact uniqueness are not enforced in this validator.
5. Unidentified-reason counts conserve totals, but their label space is not
   schema-enumerated.
6. LinkedIn-candidate, employment-episode, and education-episode counts are
   nonnegative but not semantically bounded by this validator.
7. Scope is receipt-internal semantic consistency. This function does not reopen
   artifacts, recompute hashes, or prove actual corpus completeness. A validation
   failure can leave already-written output artifacts without a receipt.

These findings are hardening work; none invalidates the scoped receipt-safety
PASS. They do not authorize canonical promotion or temporal publication.

## Evidence

- `audits/staffer_network/consolidate_employment_corpus.py:396-420` — status derivation.
- `audits/staffer_network/consolidate_employment_corpus.py:423-528` — receipt checks and reason re-derivation.
- `audits/staffer_network/consolidate_employment_corpus.py:313-318`, `:365-386`, `:608-616`, `:680-727` — source producers and validate-before-receipt-write path.
- `audits/staffer_network/test_consolidate_employment_corpus.py:246-447` — accounting tests and six forged receipts.
- `fec/staffer_network/schemas/working_history_corpus_receipt.schema.json:43-52`, `:74-147`, `:186-232`, `:240-277` — receipt schema constraints.
- `fec/staffer_network/schema_validation.py:117-226` — schema validator features.

## Scope boundary

The measured local evidence is 48 focused tests and 222 staffer-network tests
plus 73 subtests, all passing. The reviewer inspected code and did not run those
tests. This verdict is receipt semantic safety only, not completion of the
25,340-person employment-history corpus.
