# Opus 5 C-5 Resume Code Review

Date: 2026-08-30

Reviewer model: `claude-opus-5` (canonical model reported by the Claude CLI; no Sonnet fallback)

Verdict: **PROCEED**

Correctness blockers: none.

The read-only adversarial review verified the following load-bearing controls in `lda_composite_repair.py` and its schemas/tests:

- the failed status is byte-hash pinned and its run contract fields are rechecked;
- the 2,033-page partial prefix is contiguous and aligned to the eight-request persistence boundary;
- saved pages are replayed through the original page-shape, bounds, ordering, UUID, boundary, and payload validators before the live tail begins at page 2,034;
- seam timestamps and deterministic tie cohorts are repaired and inventory-closed;
- every completed earlier twin is rehashed, replayed, and reconciled rather than trusted from its manifest alone;
- repeated resume failures retain the original partial-failure evidence;
- Twin B remains a complete independent fetch and exact UUID/payload comparison gate;
- final live per-year conservation, legacy before/after seal equality, and two token-negative scans remain mandatory;
- authority receipts are immutable, named by the failed-status SHA-256, and bound by path/bytes/SHA-256 into the terminal receipt;
- canonical identity, graph, analysis, publication, and `STAFF_NET` gates remain closed.

The reviewer noted two cheap additive hardenings. Both were applied before recovery execution: each resume-authority receipt is revalidated and rehashed immediately before sealing, and the terminal composite receipt is validated against its JSON Schema before it is written.

Residual non-blocking risks retained in the audit record:

- a hard process kill in the narrow interval between authority-receipt creation and the RUNNING status write fails closed and would require manual recovery;
- historical source backfill can cause the live filter-semantics replay or Twin B to reject a stale prefix;
- a layout-only page difference is reported while exact UUID and payload equality remains the acceptance gate;
- a source count move after the saved page 1 may surface as a generic count-movement error.

Local verification at review time: `98 passed, 65 subtests passed`.
