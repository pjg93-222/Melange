# Opus 5 C5 eight-in-flight deadline review

`VERDICT: PROCEED`, subject to binding conditions.

Opus 5 found that the single `SharedRequestPacer(120)`—not worker count—controls aggregate starts. Its lock reserves unique 0.5-second slots, all retries re-enter it, workers transport immutable bytes only, caller-thread processing remains ascending and single-writer, twins remain sequential, and a cap of eight adds only a few buffered pages. The expected gain is about 33% under measured latency, not a doubling, but it lands on the dominant full-2026 twin window and justifies restarting after the small repair windows.

## Binding conditions

1. Move only the four LDA pins together: module cap, composite receipt schema, publication semantics, and contract tests. Leave the independent Politico cap at four.
2. Use ten pages in the integration fixture so page 1 is alone, pages 2–9 exercise exactly eight workers, and page 10 exercises a partial final batch.
3. Fix the synthetic opener delay for pages above five.
4. Add a contended shared-pacer cursor test and extend deterministic reservation spacing to eight.
5. Keep the comparison arm genuinely sequential (`max_in_flight_requests=1`).
6. Confirm no sealed PASS receipt with cap four needs current-schema revalidation. None exists; all prior four-request generations are incomplete/failed and preserved.
7. Before interruption, capture generation ID, completed windows, partial-window inventory, and reason; retain the root and mark it failed/superseded out of band.
8. Run the full suite and a negative bound control that rejects nine.

All binding code/test conditions were subsequently implemented. A scheduler-dependent observed-concurrency assertion initially exposed only 3–5 workers; it was replaced with an eight-party barrier that deterministically exercises eight. Final evidence: three targeted concurrency tests plus six subtests pass; full staffer suite 94 tests plus 47 subtests passes; a request for nine is rejected before transport.

Non-blocking hardening: propagate a source `Retry-After` delay into the shared pacer cursor and record observed rolling-minute request starts in future receipt versions.
