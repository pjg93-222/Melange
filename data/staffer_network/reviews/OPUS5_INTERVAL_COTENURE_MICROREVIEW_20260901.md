# Opus 5 interval/co-tenure micro-review

- Run: `run-20260831T1850525496629Z-8993807782`
- Stage: `R0b2a-opus5-interval-cotenure-microreview`
- Model/effort: Claude Opus 5 / maximum
- Mode: read-only
- Dispatch job: `job-20260831T2335539381063Z-437002908a`
- Duration: 281.250 seconds

## Verdict

`VERDICT: PASS`

`BLOCKERS: none`

This verdict is confined to interval normalization, interval union and
intersection, co-tenure bounds, and the duration transform. It does not open
review-candidate identities or incomplete employment histories for temporal
scoring.

## Equation and implementation checks

1. **Half-open precision: PASS.** `normalize_source_date`
   (`fec/staffer_network/employment_history.py:1488-1523`) fails closed on
   unknown precision and on a dated end without an inclusive/exclusive
   convention (`:1501-1506`). Inclusive ends add one day to both bounds
   (`:1521-1522`); exclusive ends pass through (`:1523`). Month and year
   widths use calendar arithmetic (`:1510-1518`). Boundary-touching cores
   produce zero guaranteed days (`test_staffer_employment_history.py:997-1002`).
2. **Union before overlap: PASS.** `co_tenure_bounds` unions each side's core
   and envelope before intersection (`employment_history.py:1592-1601`).
   `intersect_ranges` receives sorted, disjoint union output (`:1540-1552`),
   while `range_days` re-unions defensively (`:1556`). Adjacent half-open
   ranges merge without changing their day count (`:1533`).
3. **Guaranteed no greater than possible: PASS.** Interval construction
   enforces ordered earliest/latest starts and ends
   (`fec/staffer_network/intervals.py:32-35`); union and intersection preserve
   inclusion. The runtime guard remains at `employment_history.py:1604-1605`.
4. **Duration transform: PASS.** `duration_weight`
   (`employment_history.py:1559-1562`) rejects negative days and non-finite or
   non-positive tau. `1-exp(-days/365.2425)` is increasing, concave, bounded
   in `[0,1]`, and equals zero at zero days, matching the adjudication at
   `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md:104-108`.
5. **No repeated-observation inflation: PASS.** Duplicate and adjacent ranges
   collapse before overlap. The standalone union test
   (`test_staffer_employment_history.py:986-991`) produces one 19-day union
   rather than summing 28 days.

## Nonblocking findings

1. The review prompt used the conceptual names `normalize_bound_to_half_open`
   and `intersection_days`; the shipped equivalents are
   `normalize_source_date`, `intersect_ranges`, and `range_days`.
2. `duration_weight` lacks a direct unit test for monotonicity, bounds,
   `f(0)=0`, and its three guards; correctness passed inspection.
3. The inverted co-tenure guard and several negative date-normalization paths
   lack direct tests; correctness passed inspection.
4. Multi-row union is tested standalone but not through `co_tenure_bounds`.
5. Right-censored episodes without end bounds are dropped from both calendars.
   This is fail-closed for primary weight but can understate the possible upper
   bound unless the upstream as-of clamp supplies an end. Therefore production
   scoring remains closed for incomplete histories.
6. The math document's older focused-test count is stale and must be revised.

## Disposition

The interval/co-tenure mathematics is accepted. The coverage exposure is
tracked as a test and data-readiness backlog; it is not treated as authority
to promote or score incomplete evidence.
