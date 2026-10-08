# Fable C5 acceleration plan review

- Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`
- Stage: `C5-ACCEL-PLAN`
- Reviewer: Fable / Claude
- Decision: `REVISE`
- Reviewed: 2026-08-30

## Adjudication

The composite-repair architecture is sound and, once revised, is strictly
stronger evidence than finishing the anonymous full sweep. The current
proposal has three validity gaps that could yield a count-equal but
identity-wrong corpus, plus one tooling misstatement.

The receipt arithmetic supports localization for the static 2022--2025
corpora: endpoint counts were stable, objects fetched equaled the advertised
count, and the unique-UUID shortfall equaled the repeated-UUID count. That
localization is conditional on an offline proof that the legacy pages are
monotone in the ordering key and that all repeats occur inside the identified
tie groups. The remaining anonymous replay is not itself a gold standard
because it does not specify an explicit ordering and can reproduce the same
tie-group instability.

## Binding requirements

1. **R1 -- offline ordering proof before any fetch.** Verify per year that
   sealed legacy results are monotone across page sequence; record direction;
   verify all 88 duplicate pairs fall within same-key tie groups on the seven
   identified dates. If monotonicity fails, block the composite route and fall
   back to a full ordered sweep.
2. **R2 -- full date-bounded 2026 refetch.** Because the legacy 2026 sweep had
   source-count drift, refetch the full 2026 cohort through a fixed cutoff in
   two ordered, temporally disjoint passes. Do not rely on a July 20 bucket plus
   August delta patchwork.
3. **R3 -- per-year post-sweep gap coverage.** For every year 2021--2025,
   query the date window after the legacy sweep cutoff through the fixed
   collection cutoff. Any nonempty window receives a twinned ordered fetch.
4. **R4 -- validate date-filter semantics.** Empirically prove inclusivity,
   date/datetime and timezone behavior, combination with `filing_year`, and a
   partition identity. A silently ignored filter fails closed.
5. **R5 -- set-level twin criteria.** The second pass starts after the first
   completes. Require identical counts, UUID sets, and per-UUID canonical
   payload hashes under explicit ordering. Page-layout equality is required
   only if the ordering is proven total; otherwise record layout differences.
6. **R6 -- explicit payload dispositions.** Enumerate every difference between
   a legacy and fresh payload for an overlapping UUID with vintage evidence and
   an append-only disposition. Fresh supersession is permitted only as an
   explicit per-record decision. A legacy UUID absent from fresh results fails
   closed pending adjudication, such as `DELETED_UPSTREAM`.
7. **R7 -- seal discipline.** The legacy tree inventory must equal
   `d7304591ee11a5d5c58ab7ff636d429509f8332cd473faca4dd5e7a15594961e`
   before and after every fetch phase and be embedded in the receipt. Keep the
   repair outside synced roots and rerun full-composite global duplicate and
   cross-year collision checks.
8. **R8 -- normal implementation gate.** The existing anonymous wrapper cannot
   run the repair. New registered collection capability must reuse the existing
   fetch/pacer/redirect-refusal/atomic-write primitives, use one shared pacer at
   no more than 120 requests/minute across both twins, place the token only in
   the Authorization header, and scan every emitted artifact for the token
   before sealing.
9. **R9 -- honest supersession receipt.** Explicitly supersede the prior
   terminal criterion with a dated, user-ratified composite criterion: sealed
   legacy plus ordered twin repairs and gap windows through a fixed cutoff.
   Preserve the deliberately stopped partial anonymous replay as corroborating
   evidence. Keep all downstream identity, graph, analysis, publication, and
   `STAFF_NET` gates closed.
10. **R10 -- fail-closed terminality.** Any twin mismatch, count movement,
    filter anomaly, or unexplained per-year shortfall/excess ends in `FAILED`
    with no partial promotion.

## Reviewer conclusion

The composite route may replace the remaining full replay once R1--R10 are
implemented. The proof against count-equal-but-identity-wrong output is the
combination of offline monotonicity/localization, closed per-year gap windows,
validated filter semantics, twin-stable UUID sets and payload hashes, and
explicit per-UUID divergence dispositions. Pages outside repaired windows
remain single-fetch evidence; this residual is acceptable and no weaker than a
completed conventional full sweep.

No files were modified by the reviewer.
