# Fable C5 inclusive-datetime implementation review

- Meta LOOP recovery run: `run-20260830T1757394488997Z-487ca1218b`
- Stage: `C5-DATETIME-CODE-REVIEW`
- Reviewer: Fable / Claude
- Decision: `PROCEED`
- Reviewed: 2026-08-30

## Adjudication

- Microsecond-end dual anchor verified across exact cohort fetches, historical
  control, dynamic probes, union probe, empty-second probe, and offset probe.
- The pinned 2022 control is genuinely discriminating: counts 2, 1, and 3;
  exact timestamp sets; partition identity; and three fixed UUID/payload hashes.
- Endpoint leakage, widening, date truncation, multi-page cohorts, duplicate
  UUIDs, sub-second rows, missing legacy UUIDs, non-boundary repeats, and
  changed-payload repeats all have planted failures.
- Earlier R1--R10 and T1--T5 properties remain intact: seals, ordering proof,
  88-tie coverage, twin UUID/payload equality, count conservation, immutable
  roots, synced-root refusal, token scans, and CLOSED downstream gates.
- The failed `174300Z` generation is confirmed FAILED with zero completed
  windows and no PASS receipt.

Non-blocking recommendation adopted: schema-pin
`UTC_Z_MICROSECOND_END_INCLUSIVE` and the historical-control PASS properties so
the receipt is self-certifying as well as producer-enforced.

No files were modified and no network requests were made by the reviewer.
