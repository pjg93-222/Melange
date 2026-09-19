# Contribution query and build performance — 2026-09-12

The parent observed a 1,324-second Banking cold build (849,399 facts), staging shrinkage from roughly 2.18 GB to 723 MB, and an amount-only ZIP query exceeding two minutes while other builds were doing I/O. This lane used code inspection, SQLite query plans, deterministic VM counts and small disposable fixtures. It did not run another production build or alter any source, evidence store, monetary index or existing cache.

## Query defect and implemented correction

The frozen `contribution_data._query_ready` evaluated the same grouped subquery three times: group count, sorted page, and retained-group amount. Even an amount-only view calculated private `COUNT(DISTINCT contributor_key)` within each group on all three executions. SQLite `EXPLAIN` shows the otherwise unused `AggStep count(1)` in the outer-count query. Totals, accounting comparison and ZIP coverage added three more population scans.

An unfiltered `GROUP BY zip5` can choose `facts_zip`, a noncovering index, and read the wide fact row once for every source through that index. Under concurrent build I/O, that is substantially different from one sequential scan.

The separate, read-only `mentat/app/contribution_query.py` now:

- Materializes the grouping and aggregate-filtered selection once, then derives the page, group count and retained-group amount from it.
- Computes group contributor counts only when a selected measure, aggregate filter or sort needs them. The distinct population total remains available.
- Computes population totals, comparisons and ZIP coverage in one compatible scan, preserving basis-zero exclusion and pre-aggregate-filter semantics.
- Uses sequential table scans for unfiltered/nonselective aggregate requests; selective equality/IN filters on indexed company, ZIP, state or committee fields retain planner index access.
- Preserves the request/result shape, explicit index-retry behavior and accounting decisions. It adds a query-engine SHA to provenance, rejects changed code until restart, and labels the supported basis as a gross subset.

No monetary index token changed. The existing `contribution_data.query` compatibility path remains intact; root wires the server to the new explicit API.

Ten focused tests passed, covering more than 100 equivalent request combinations across every basis and measure, median, row and aggregate filters, sort, missing/zero/negative values, empty results, page offsets, invalid requests, retry and query plans. A 6,004-fact fixture used **368,300 VM instructions versus 514,700** for the reference (**28.44% fewer**), with identical monetary/count results. This is deterministic work evidence, not a production latency forecast. Root owns the live endpoint benchmark.

## Cold-build findings

No obvious quadratic SQL join was found in the reviewed staging path:

- Receipt lookup uses the primary-key index.
- Company partition lookup uses `canonical_company`.
- Missing-receipt reconciliation scans the narrow receipt index and probes the fact primary-key index.
- The cross-company filing-family guard scans canonical rows twice and uses the header primary key plus an automatic covering index. Its toy VM counts were exactly linear: 224,000 / 448,000 / 896,000 / 1,792,000 instructions at 4k / 8k / 16k / 32k rows. Wall-clock ratios alone were noisier under concurrent load.
- Existing ledger source/decision ordered reads have explicit source-ID indexes in `run_cross_reference.write_ledger`.

`PRAGMA auto_vacuum=FULL`, the intermediate `executescript` commits, and dropping staging tables explain the observed file shrinkage. A 12,000-row fixture shrank from roughly 54 MB to 6 MB with FULL auto-vacuum; the equivalent no-vacuum file retained its free pages at 54 MB. Measured cleanup was 0.358 seconds versus 0.109 seconds in that fixture. It establishes compaction work and the storage tradeoff, **not** that compaction caused the 1,324-second build.

Future build optimization should start with phase timings for payload projection, source staging, coalescing, evidence resolution, fact insertion, compaction and integrity checks. Two bounded candidates are staging in a separate temporary database and building secondary fact indexes after bulk insertion. Both need exact-result benchmarks before changing the frozen builder. No speculative builder edit was made.

Reproduction: `build-performance-probe.py`; full toy output: `build-performance-probe.jsonl`. Runtime query tests: `mentat/tests/test_contribution_query.py`.
