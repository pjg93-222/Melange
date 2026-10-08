# Fable C5 bounded-concurrency acceleration review

Meta LOOP recovery run: `run-20260830T1757394488997Z-487ca1218b`

The corrected registered collector is currently healthy but sequential HTTP
latency limits it to about 40 pages/minute despite the registered 120/minute
ceiling. Review this proposed performance-only change before it is implemented
or the current generation is stopped.

Read in full:

1. `fec/staffer_network/lda_composite_repair.py`
2. `fec/lobbying/collect_lda_filings.py` (`RequestPacer` and `_fetch_url`)
3. `fec/tests/staffer_network/test_staffer_ingest_contracts.py`
4. `data/staffer_network/reviews/FABLE_C5_DATETIME_CODE_REVIEW.md`

Proposal:

1. Add a thread-safe shared pacer using one lock and a monotonic next-request
   deadline, spacing request starts by at least 0.5 seconds across all workers.
   All twins, pages, probes, and cohort repairs use this single instance.
2. Keep Twin A and Twin B strictly sequential. Keep exact-second cohort repairs
   sequential after each base pass.
3. Fetch base pages in bounded batches after page 1 establishes the advertised
   count: compute `ceil(count/25)`, issue at most four in-flight page requests,
   and process/validate/write each completed batch in ascending page order.
   Do not hold the whole window in memory.
4. Require every page count equals page 1; page numbers below N must have
   non-null `next`, page N must have null `next`; every nonterminal page must
   contain exactly 25 results; the terminal page length must equal the
   advertised remainder (or 25 when divisible). Preserve all existing row
   bounds, nondecreasing timestamp, boundary-repeat, exact-cohort, count,
   UUID/payload, seal, and twin gates.
5. On any worker or validation error, fail the immutable generation; no partial
   receipt is promoted. A current sequential generation would be deliberately
   stopped and preserved only after this design, code, tests, and a second
   Fable review return PROCEED.
6. Add deterministic tests for maximum in-flight <=4, aggregate request-start
   spacing >=0.5 seconds, page-count/next/result-length shape failures, ordered
   post-fetch validation, and identical sequential-vs-batched repaired
   inventories.

Adjudicate whether this preserves R1--R10/T1--T5 validity and whether any extra
conditions are required. Return exactly `PROCEED`, `REVISE`, or `BLOCK`, then
concise binding findings. Do not modify files and do not make network requests.
