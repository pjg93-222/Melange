# Fable C5 bounded-concurrency code review

You are the read-only adversarial reviewer for the active staffer-network LDA composite repair. Review the implementation, tests, schema, and publication semantics in the repository rooted at `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`.

Inspect these files directly:

- `fec/staffer_network/lda_composite_repair.py`
- `fec/tests/staffer_network/test_staffer_ingest_contracts.py`
- `fec/staffer_network/schemas/lda_composite_reconciliation_receipt.schema.json`
- `fec/staffer_network/publication.py`
- `data/staffer_network/reviews/FABLE_C5_CONCURRENCY_PLAN_REVIEW.md`
- `data/staffer_network/reviews/FABLE_C5_DATETIME_CODE_REVIEW.md`

The full staffer-network suite reports `92 passed, 45 subtests passed`. The implementation fetches page 1 alone, derives `N=max(1,ceil(count/25))`, transports later pages in bounded batches of at most four workers, uses a single shared 120-RPM monotonic start pacer, and decodes/validates/writes strictly in ascending page order on the caller thread. A worker failure cancels and drains the batch by executor shutdown and no window manifest is emitted. Production uses a fresh opener per request. Exact-second tie-cohort repair stays sequential. The receipt and schema pin page size 25, maximum in-flight four, and the transport mode. The sealed legacy page-shape audit is being rerun independently before launch.

Adversarially check every binding condition from your plan review, especially global start spacing under retries, first-worker-failure behavior, page-count drift, terminal/divisible-by-25 page shapes, deterministic sequential/batched equivalence, ordering preservation, and whether any manifest/receipt could overclaim. Distinguish a true blocker from a non-blocking hardening suggestion.

Return exactly:

1. `VERDICT: PROCEED` or `VERDICT: STOP`
2. Findings ordered by severity with file and line references.
3. Binding launch conditions, if any.
4. A concise evidence table mapping each earlier binding condition to PASS/FAIL.

Do not modify files and do not use network access.
