# Fable C-5 accelerated reconciliation preflight

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

Act as a read-only adversarial reviewer. Return `PROCEED`, `REVISE`, or
`BLOCK` with binding acceptance requirements. Do not edit files.

Read completely:

- `data/staffer_network/receipts/lda_reconciliation_20260829.json`
- `fec/staffer_network/lda_contract.py`
- `fec/staffer_network/run_lda_generation.py`
- `fec/lobbying/collect_lda_filings.py`
- `STAFFER_NETWORK_METRICS_20260830.md`
- `audits/STAFFER_NETWORK_IMPLEMENTATION_DIAGNOSTIC_20260830.md`

## New evidence

- The sealed legacy store has 21,599/21,599 hash-valid pages, 539,870 objects,
  539,782 unique UUIDs, 88 identical repeats, zero conflicting repeats, and
  zero cross-year UUID collisions. It is 2,329,092,781 bytes and remains sealed
  at inventory SHA-256 `d7304591…961e`.
- 2021 already passes exactly: 90,778 objects and unique UUIDs.
- The 88 repeats are pagination-boundary overlaps and are localized to seven
  posting dates: 2023-01-20 (filing year 2022); 2024-01-19 and 2024-01-22
  (2023); 2025-01-20 and 2025-01-21 (2024); 2026-01-20 (2025); and
  2026-07-20 (2026). Re-fetching all seven complete day buckets is estimated at
  1,914 pages.
- The active anonymous full sweep has reached 2022 page 1,160+ with a stable
  count of 93,513, zero duplicates, and zero UUIDs absent from the legacy store
  so far. It has not yet reached the first overlap at page 3,282.
- Official LDA v1 documentation exposes `filing_dt_posted_after`,
  `filing_dt_posted_before`, `filing_year`, `ordering`, and `page_size` filters;
  page size is capped at 25. Official limits are 120/minute registered and
  15/minute anonymous.
- Paul's local API-key repository has one verified Senate LDA token. The token
  must never be logged or copied into a receipt.

## Proposed accelerated path

1. Preserve the legacy store and the active partial generation byte-for-byte.
   Stop the anonymous full sweep only after this review; allow its wrapper to
   record a superseded/failed terminal status and verify the legacy after-seal.
2. Build a new immutable composite-repair generation outside synced roots.
   Use the registered token at no more than 120/minute, with a single shared
   pacer, retry/backoff, redirect refusal, and token-redacted logs.
3. Fetch each of the seven complete affected posting-day buckets with explicit
   year/date filters and deterministic ordering. Collect two independent twins
   per bucket; require stable counts, page inventories, zero duplicate UUIDs,
   identical UUID sets, and identical per-UUID canonical payload hashes.
4. Fetch the 2026 delta from 2026-08-01 through the last complete UTC date
   before collection, also as independent twins. Keep the cohort date-bounded
   so newly arriving filings cannot move the denominator.
5. Construct a deterministic composite UUID inventory from sealed legacy
   records plus repair/delta rows. Identical legacy repeats receive explicit
   `PAGINATION_BOUNDARY_REPEAT` dispositions; repair rows supersede only the
   repeated/missing bucket evidence, never mutate the legacy bytes.
6. Require per-year and global conservation against fresh, date-bounded API
   counts; zero unresolved shortfall, zero conflicting payloads, zero cross-year
   UUID collision, complete repair-page hashes, and exact legacy before/after
   identity. Fail closed if counts or twin sets drift.
7. Emit a registered composite-reconciliation receipt and retain raw repair
   pages locally. Do not enable identity, graph, analysis, publication, or
   `STAFF_NET`; C-5 passes only for the declared date-bounded source-native LDA
   cohort.

Decide whether this can validly replace the remaining full sweep and identify
any additional proof needed to avoid a merely count-equal but identity-wrong
corpus.
