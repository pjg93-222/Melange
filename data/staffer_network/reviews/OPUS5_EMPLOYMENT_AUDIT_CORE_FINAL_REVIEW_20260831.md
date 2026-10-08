# Opus 5 employment-audit core final review — 2026-08-31

**Model:** Claude Opus 5, maximum effort  
**Mode:** read-only static review  
**Verdict returned:** `BLOCKED`

The reviewer reported that execution and temporary writes were denied in its
`dontAsk` session, so its findings were static traces rather than independent
probe runs. The local Codex lane subsequently converted every blocking
counterexample into a regression test.

## Blocking findings returned

1. `raw_dates` used year-token presence instead of strict date validation, so
   impossible date ranges could supply both bounds.
2. Open-ended `raw_dates` current markers could supply an end without an as-of
   bound. This finding described the snapshot read before the local
   `raw_current_marker` patch completed; the current code requires an as-of
   bound and the finding was re-tested.
3. `_has_date_evidence` accepted arbitrary prose containing a year, including
   speculative or explicitly unknown bounds.
4. Literal person ID `UNRESOLVED` could collide with the missing-ID sentinel and
   escape the missing-ID failure.
5. Multiple complete rows for one person could leave the person and receipt
   complete despite mutually exclusive exhaustiveness claims.
6. The row and receipt schemas did not constrain `COMPLETE`/`PASS` against
   contradictory failure and incomplete counts.

## Nonblocking findings returned

- Retrieval time and source-as-of time are not equally strong currentness
  evidence.
- A single valid HTTP(S) URL is sufficient even if other URL values are bad;
  HTTP, localhost, and unreachable hosts are structurally accepted.
- `display_name` is not typed.
- The receipt does not use the same `failures` array convention as sibling
  receipts.
- Negative tests did not cover several of the above counterexamples.
- The CLI collapses exceptions to a short error without a traceback.

## Binding disposition

The `BLOCKED` verdict was accepted. The local lane then:

- replaced arbitrary year-token rescue with strict date-atom/range parsing;
- required an as-of bound for all raw or structured current markers;
- reserved `UNRESOLVED` as an invalid identity value;
- made any duplicate identified-person row receipt-incomplete;
- added conditional schema constraints for verdict consistency;
- extended the dependency-free schema validator for `allOf` and
  `if`/`then`/`else`; and
- added measured counterexample tests.

No PASS is inferred from the repair or passing local tests. A fresh Opus review
of the post-repair files is required.
