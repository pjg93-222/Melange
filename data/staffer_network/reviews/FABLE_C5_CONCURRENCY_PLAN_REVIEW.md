# Fable C5 bounded-concurrency acceleration review

- Meta LOOP recovery run: `run-20260830T1757394488997Z-487ca1218b`
- Stage: `C5-CONCURRENCY-PLAN`
- Reviewer: Fable / Claude
- Decision: `PROCEED`
- Reviewed: 2026-08-30

## Binding conditions

1. Fetch page 1 alone, set `N=max(1,ceil(count/25))`, and explicitly handle
   count zero and divisible-by-25 terminal shapes.
2. Workers perform transport only. Decode, validate, mutate state, detect
   boundaries, and write atomically on one thread in ascending page order.
3. Add a new thread-safe pacer in the composite module; do not change the
   legacy collector pacer. Compute deadlines under a lock and sleep outside it;
   retries must re-enter the same pacer.
4. Use a fresh opener per request/worker; do not share an opener director.
5. On first worker failure, cancel or drain all in-flight work and re-raise; no
   thread exception may be swallowed and no window manifest may be written.
6. Add controls for count zero, divisible remainder, mid-batch count drift,
   raising worker, max in-flight, 0.5-second aggregate spacing, ordered
   validation, and sequential/batched inventory equivalence.
7. Offline-check the sealed legacy sweep's page-shape assumption before the
   first live batched run.

Twin A and B remain sequential, exact-second cohort repairs remain sequential,
and all R1--R10/T1--T5 evidence is preserved when batched transport results are
processed in ascending page order.

No files were modified and no network requests were made by the reviewer.
