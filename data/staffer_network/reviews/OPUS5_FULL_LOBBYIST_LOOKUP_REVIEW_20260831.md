# Opus 5 max final receipt review — full lobbyist lookup corpus

Model: `claude-opus-5`  
Effort: `max`  
Mode: read-only, no tools/network  
Date: 2026-08-31

## PASS

No blocking invariant failure.

### Adversarial checks

- **Conservation:** 6,527 + 2,957 + 15,856 = 25,340, matching both row count and
  person universe; no silent drop or double-count.
- **Identity closure:** 0 matches asserted, 0 merges, every row `REVIEW_REQUIRED`,
  `canonical_merge=false`, and `NOT_STARTED`. The artifact asserts no employment, identity,
  or date fact.
- **Provenance:** candidate IDs and the receipt source binding hash the upstream sealed
  receipt SHA-256; no row can be rebound to another source without changing its ID. The
  gzip is verified by exact bytes and hash.
- **Determinism:** a second immutable build reproduced the queue hash byte-for-byte under
  the pinned timestamp.
- **Containment:** both schemas are restricted, publication rejects restricted schemas, and
  discovery features are contract-barred from canonical facts.

### Binding boundary

1. The artifact is a work queue over the sealed receipt's person universe. “Complete” means
   complete relative to that binding; it inherits the upstream receipt's coverage and
   vintage, not the real-world staffer/lobbyist population.
2. It contains 25,340 distinct `source_person_id` values, not necessarily 25,340 distinct
   humans. One person with two upstream LDA IDs remains two review rows. That is queue-safe
   and must never be quoted as a deduplicated human headcount.
3. P0/P1/P2 are search-ordering priorities derived from discovery features. P0=6,527 does
   not mean 6,527 confirmed government employees; no bucket is evidence.
4. It is not employment history, accepted identity/date evidence, or a temporal graph.
   Every downstream use requires adjudication of a `REVIEW_REQUIRED` row.
