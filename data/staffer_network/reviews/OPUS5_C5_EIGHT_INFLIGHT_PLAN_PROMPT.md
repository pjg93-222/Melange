# Opus 5 C5 eight-in-flight deadline review

Review one proposed operational change to the already reviewed LDA composite collector in `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`.

Current facts:

- `SharedRequestPacer(120)` reserves every request start under one lock at a global 0.5-second interval; every retry re-enters it.
- Workers perform transport only. Decode, validation, state mutation, and writes occur in ascending page order on one caller thread.
- Production uses a fresh opener per request. Page 1 remains alone; page count and all shape/count/order checks remain unchanged.
- Current cap is four in-flight transports. Measured API/TLS latency causes batches of four to finish about every four seconds, using only roughly 60 of the permitted 120 starts/minute.
- The user imposed a hard two-hour completion window and explicitly prefers fast collection while respecting the source rate.
- Proposed change: raise only `MAX_IN_FLIGHT_REQUESTS` from 4 to 8. Keep the single 120-RPM pacer and every other invariant unchanged. Pin 8 in status, receipt, schema, and publication semantics. Expand the deterministic contract test from four pages/four workers to eight pages/eight workers, prove maximum in-flight ≤8 and at least 4, preserve start spacing, sequential/batched content equality, count drift, failure/no-manifest controls, and rerun the full suite.
- Because the running process loaded the four-worker code, a reviewed change requires deliberate interruption, preservation/supersession receipt, and a fresh immutable generation. No bytes are reused.

Inspect the current collector, tests, schema, publication semantics, Fable concurrency reviews, and this proposal. Decide whether an eight-request concurrency cap under the same single 120-RPM start pacer is respectful, deterministic, fail-closed, and justified by the hard deadline.

Return exactly:

1. `VERDICT: PROCEED` or `VERDICT: STOP`.
2. Safety analysis covering aggregate rate, retries, transport concurrency, memory/state ownership, failure draining, twin semantics, and immutable supersession.
3. Binding test/launch conditions.
4. Whether the expected throughput gain justifies restarting after three completed windows.

Do not modify files and do not use network access.
