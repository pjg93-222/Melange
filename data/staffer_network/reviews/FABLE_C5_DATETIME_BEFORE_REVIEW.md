# Fable C5 historical datetime-before remediation review

- Meta LOOP recovery run: `run-20260830T1757394488997Z-487ca1218b`
- Parent run: `run-20260830T0416179390616Z-17a7cf4477` (`FAILED`)
- Stage: `C5-DATETIME-BEFORE-REMEDIATION`
- Reviewer: Fable / Claude
- Decision: `PROCEED`
- Reviewed: 2026-08-30

## Binding findings

1. No full ordered sweep is required. The incorrect boundary assumption failed
   closed before any window completed, no PASS receipt was emitted, and the
   legacy seal was untouched.
2. The dynamic 2026 1/0/1 probe had no row on an endpoint and therefore could
   not distinguish inclusive from exclusive `before`. Add the fixed sealed
   2022 adjacent-second control as the load-bearing discriminator.
3. Query exact seconds with `[T,T+0.999999s]`, but validate against conceptual
   `[T,T+1s)` and continue requiring every returned timestamp to equal T.
4. Convert the dynamic exact-second, empty, and offset-equivalence probes to
   the same microsecond-end convention.
5. Preserve date-bound validation as-is. A future date-midnight endpoint hazard
   must fail loudly rather than be absorbed.
6. Pin and record historical control UUIDs and canonical payload hashes so any
   upstream change is immediately diagnosable.
7. Preserve both failed generations; add endpoint-leakage and widened-filter
   planted failures; obtain another Fable code-review pass before retrying in a
   fresh immutable root.

No files were modified and no network requests were made by the reviewer.
