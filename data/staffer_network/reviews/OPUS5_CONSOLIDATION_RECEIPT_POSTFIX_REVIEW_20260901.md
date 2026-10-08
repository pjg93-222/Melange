# Opus 5 consolidation receipt post-fix review

**Model:** Claude Opus 5, maximum effort, read-only  
**Verdict:** `BLOCKED`

## Blocking findings

1. The receipt did not prove the row-to-person bridge. The producer identity is
   `duplicate_identified_input_rows == consumed_identified_input_rows - processed_people`.
   Without it, either an inflated people count or laundered duplicate rows could
   satisfy the remaining receipt checks.
2. `residual_incomplete_rows` was not re-derived. The producer identity is
   `residual_incomplete_rows == processed_people - complete_people`.

These are exact identities of the receipt producer, not heuristic thresholds.

## Disposition

The findings were accepted. Both identities and adversarial forged-receipt
tests were added before the next review. This review is preserved as a blocking
constituent and is not retroactively treated as a pass.

## Scope

Receipt semantic safety only. This verdict does not assess or claim completion
of the 25,340-person employment-history corpus.
