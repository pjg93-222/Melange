# Fable read-only C5 tie-remediation review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

You are the fresh adversarial reviewer. Read these files completely:

1. `data/staffer_network/reviews/FABLE_C5_ACCEL_PLAN_REVIEW.md`
2. `fec/staffer_network/lda_composite_repair.py`
3. `fec/tests/staffer_network/test_staffer_ingest_contracts.py`
4. `%LOCALAPPDATA%/Melange/staffer_network/raw/lda/composite-repair-generation-20260830T171300Z/generation_status.json`
5. `%LOCALAPPDATA%/Melange/staffer_network/raw/lda/composite-repair-generation-20260830T171300Z/legacy_ordering_audit.json`
6. `%LOCALAPPDATA%/Melange/staffer_network/raw/lda/composite-repair-generation-20260830T171300Z/filter_semantics_receipt.json`

The first registered composite attempt failed closed at the first 2022 repair
window because the API did not honor `filing_uuid` as a secondary ordering
field. The date filter probe passed. The generation is preserved and was not
promoted.

Proposed remediation:

1. Use the official documented ordering `dt_posted,registrant__name`.
2. Validate nondecreasing `dt_posted`, but do not pretend this is a total key.
3. Record every adjacent page boundary whose last/first result share the same
   exact timestamp. Allow only identical repeated UUID payloads in the base
   pass.
4. Refetch every split exact-timestamp cohort with datetime
   `filing_dt_posted_after=<timestamp>` and
   `filing_dt_posted_before=<timestamp+1 second>`. Require the cohort to fit on
   one page (count <= 25), contain only that exact timestamp, and have unique
   UUIDs. Replace all base-pass rows at that timestamp with the complete cohort.
5. Require the repaired unique UUID count to equal the source-advertised window
   count. Any unresolved shortfall, group over 25, filter anomaly, conflicting
   repeat, or nonmonotonic timestamp fails closed.
6. Run pass B only after A completes. Accept only identical advertised counts,
   UUID sets, and per-UUID canonical payload hashes. Record page-layout and tie
   repair evidence but do not require page-layout equality because the order is
   not total.
7. Extend the filter probe to verify datetime filtering with an exact-second
   cohort before collection.
8. Keep the single registered 120/min pacer, immutable roots, legacy seal, token
   scan, and all R1-R10 requirements unchanged.

Adjudicate `PROCEED`, `REVISE`, or `BLOCK`. Specifically determine whether the
exact-timestamp replacement plus independent twin set/hash equality is enough
to eliminate the pagination-boundary miss, and name any missing negative
controls. Do not edit files.
