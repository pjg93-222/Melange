# Fable C5 tie-remediation review

- Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`
- Stage: `C5-TIE-REMEDIATION`
- Reviewer: Fable / Claude (fresh adversarial pass)
- Decision: `REVISE`
- Reviewed: 2026-08-30

## Core determination

Exact-timestamp cohort replacement is sound, conditional on proving datetime
filter semantics and binding every tolerated base-pass repeat to a recorded
same-timestamp page boundary. With a static corpus ordered nondecreasing by
`dt_posted`, a pagination miss can occur only in a timestamp cohort that
straddles a page boundary. Such a cohort necessarily appears as
`last(page N).dt_posted == first(page N+1).dt_posted`. Refetching that exact
second into one complete page removes the pagination-boundary failure mode.
Twin UUID-set and per-UUID payload-hash equality plus advertised-count equality
then verify stability; page-layout equality is not required because the order
within a timestamp cohort is not total.

## Binding revisions

1. **T1 — Localize base repeats.** Tolerate a repeated UUID only when it occurs
   across a recorded same-timestamp page boundary, has that exact timestamp on
   both occurrences, and has an identical payload. Any other repeat fails
   closed.
2. **T2 — Prove datetime semantics.** Before collection, prove second-level
   half-open behavior with `[T,T+1s) + [T+1s,T+2s) == [T,T+2s)`, prove a known
   empty exact-second window returns zero, and prove or pin the timezone-offset
   serialization used by repair queries.
3. **T3 — Repair every window.** Make boundary detection and exact-second
   cohort replacement intrinsic to `fetch_window`, including full 2026 and all
   post-sweep gap windows.
4. **T4 — Direct legacy containment.** In static-year repair windows, require
   every legacy UUID at a repaired split timestamp to appear in the refetched
   cohort. Any absence requires an R6 disposition or fails closed.
5. **T5 — Exact single-page proof.** An exact-second cohort is complete only
   when `next == null`, `len(results) == count`, and `count <= 25` in the same
   response.

## Required planted-failure controls

1. A straddling synthetic cohort with one repeated and one missed UUID is
   correctly replaced and passes the repaired count identity.
2. A cohort response advertising or returning 26 rows fails.
3. A cohort containing a foreign timestamp fails.
4. A cohort with a duplicate UUID fails.
5. An identical repeat at a non-tie boundary fails.
6. A datetime filter that is ignored or truncated to date fails the probe.
7. A sub-second timestamp inside the exact-second cohort window fails the
   exact-timestamp gate.

## Accepted elements

- Use documented ordering `dt_posted,registrant__name`; validity depends only
  on nondecreasing `dt_posted`.
- Compare twins by advertised count, UUID set, and per-UUID canonical payload
  hash; record but do not require page-layout equality.
- Keep the shared registered-mode pacer, immutable generation roots, legacy
  seal checks, token scan, explicit divergence dispositions, and R1–R10
  fail-closed rules.
- If any exact-second cohort exceeds 25 rows, fail closed. The only sanctioned
  fallback is the earlier full-ordered-sweep route, not an improvised
  partition.

No files were modified by the reviewer.
