# Fable C5 historical datetime-before remediation review

Meta LOOP recovery run: `run-20260830T1757394488997Z-487ca1218b`

Parent run `run-20260830T0416179390616Z-17a7cf4477` is preserved terminal
`FAILED` with its collector evidence.

The registered retry failed closed in its first exact-second cohort. Preserve
and inspect this evidence read-only:

1. `C:/Users/pgoff/AppData/Local/Melange/staffer_network/raw/lda/composite-repair-generation-20260830T174300Z/generation_status.json`
2. `C:/Users/pgoff/AppData/Local/Melange/staffer_network/raw/lda/composite-repair-generation-20260830T174300Z/filter_semantics_receipt.json`
3. `fec/staffer_network/lda_composite_repair.py`
4. `fec/tests/staffer_network/test_staffer_ingest_contracts.py`
5. `data/staffer_network/reviews/FABLE_C5_TIE_CODE_R2_REVIEW.md`

Empirical diagnosis, obtained with registered read-only requests:

- Filing year 2022, after `2023-01-20T14:31:13Z`, before
  `2023-01-20T14:31:14Z`: count 3; two rows at `09:31:13-05:00` and one row
  exactly at `09:31:14-05:00`.
- The same start with before `2023-01-20T14:31:13.999999Z`: count 2; both
  rows are exactly the intended `:13` timestamp.
- No PASS receipt was emitted; the generation status is FAILED and the sealed
  legacy was never modified.

Proposed revision:

1. Treat datetime `filing_dt_posted_before` as empirically inclusive.
2. Query an exact second as `[T, T+0.999999s]` using UTC-Z microsecond
   serialization, but validate returned rows against the conceptual half-open
   interval `[T,T+1s)` and still require every row's timestamp equals T.
3. Extend preflight with a fixed sealed historical boundary control at this
   known adjacent-second cohort: exact T count 2, next-second count 1, union
   count 3, set/hash-compatible timestamp membership, and partition identity.
4. Change the dynamic 2026 exact-second and empty controls to microsecond-end
   bounds; retain offset-equivalence and date-level probes.
5. Add planted failures for a collector that treats microsecond before as
   ignored/widened and for endpoint leakage.
6. Preserve the failed generation and retry only in a new immutable root after
   all tests and another Fable code review pass.

Adjudicate whether this is a sound fail-closed remediation or whether a full
ordered sweep is now required. Return exactly `PROCEED`, `REVISE`, or `BLOCK`,
then concise binding findings. Do not modify files and do not make network
requests.
