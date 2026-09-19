# Contribution query performance

All eight datasets now have verified query views and cached responses for the original interface's default company chart. The monetary accounting engine, published reports and authoritative contribution indexes are unchanged. Every original index retained its exact SHA-256 fingerprint.

## Measured Banking results

| Workload | Previous SQL plan | New, uncached configuration | Repeated public query |
| --- | ---: | ---: | ---: |
| Election cycle | 1.767 s | 0.693 s | 0.051 s |
| ZIP and state | 1.830 s | 0.496 s | 0.054 s |
| Company, filtered to 2023–2024 | 1.331 s | 0.484 s | 0.061 s |
| Recipient category and distinct donors | 1.908 s | 0.974 s | 0.050 s |

These measurements use the same validated Banking index and compare every returned row, money total and distinct donor count. Each new configuration was confirmed absent from the response cache before measurement. They do not claim that operating-system file caches were cleared. The previous-plan column measures SQL execution; new timings include the public Python query call. Guarded HTTP and browser timings are measured separately by the application checks.

The initial profile also exposed substantial cold file access: the first cycle request spent 22.935 seconds in its population summary and 11.269 seconds grouping, falling to 1.966 and 1.166 seconds on immediate repetition. Moving temporary SQLite work into memory did not improve that workload and was not adopted.

See [query-acceleration-validation.json](query-acceleration-validation.json) and [query-latency-profile.json](query-latency-profile.json) for the requests, timings, query plans and provenance.

## What changed

Common charts read a 63,631,360-byte fact table containing cycle, company, contribution date, ZIP, state, donor identity and the existing monetary measures. Longer detail fields are stored separately and joined only when the requested fields or filters need them. The original Banking index remains 537,477,120 bytes and is used for source records and audit detail.

This is a projection of existing observations. It does not reclassify, deduplicate, discard or recalculate contributions. Every copied field is checked against its original row identifier. Donor identity strings are encoded one-to-one for counting, preserving both missing and empty-string semantics. Population summaries are reused across chart configurations with the same basis, filters and measures; complete responses are cached independently.

Banking's one-time verified projection preparation took 17.302 seconds. All eight projections and the exact default interface request were prepared before delivery. Repeated public Python requests across those eight datasets took 0.047–0.061 seconds. Changed source indexes require a fresh derived view. See [query-prewarm-validation.json](query-prewarm-validation.json) and [query-projection-validation.json](query-projection-validation.json).

## Correctness and concurrency

Cache identities include the authoritative index, query code and projection code fingerprints. Queries recheck source and projection stability, including nonempty WAL or journal files, before publishing results. Complete results are written atomically; concurrent requests coordinate within a process and across processes. Returned objects are independent copies. Malformed or corrupted cache files are rebuilt from the authoritative index.

Response caching is bounded to 32 MiB of in-process payloads, with at most 128 saved responses and 128 MiB per response namespace. The derived views are separate from the authoritative indexes and do not change their accounting fingerprints.

The 21 focused query tests passed. Coverage includes more than 100 equivalence comparisons, every detail dimension, signed money, distinct identities, row and aggregate filters, pagination, source drift, derivative WAL mutation, projection mutation during SQL, malformed cache envelopes, corrupted derivatives, concurrent threads and concurrent processes. Independent review found the WAL and malformed-envelope cases, and both now have regression tests.
