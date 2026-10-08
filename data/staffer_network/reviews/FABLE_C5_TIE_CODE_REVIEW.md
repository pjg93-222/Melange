# Fable C5 tie-remediation implementation review

- Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`
- Stage: `C5-TIE-CODE-REVIEW`
- Reviewer: Fable / Claude (fresh adversarial pass)
- Decision: `REVISE`
- Reviewed: 2026-08-30

## Binding findings

1. **F1 — Prove split-cohort coverage at runtime.** The six dedicated static
   repair dates exclude the seventh duplicate date in 2026, which is intended
   to be covered by the full-2026 window. Fail closed unless every
   audit-localized duplicate timestamp falls inside at least one window that
   receives its required legacy UUID set. Pass window-bounded legacy split
   cohorts to repair, gap, and full-year windows.
2. **F2 — Exercise T1 directly.** The non-tie repeat negative fixture fails on
   descending timestamp order before reaching the repeat-localization branch.
   Add a same-boundary repeated UUID with a changed payload and assert the T1
   error.
3. **F3 — Remove a stale PASS receipt on post-seal token failure.** If the
   second token scan fails after the receipt is written, unlink the receipt
   before failing the generation. Also make the secret-scan test actually span
   a chunk boundary.

## Additional rulings

- Enforce that the immutable generation root is outside synced roots, or record
  this as explicit operator discipline.
- Treat fresh-payload supersession as a ratified policy choice. Per-record
  enumeration and changed JSON-pointer paths are auditable, but the policy must
  be explicit.

## Adjudicated sound

- T1 repeat tolerance is structurally correct inside covered windows.
- The exact-second cohort fetch proves the five required one-page properties.
- Tie repair is intrinsic to every window kind.
- Reconstructed payloads and twin comparison use repaired UUID/payload
  inventories and do not require unstable page layouts.
- The filter probe proves date and exact-second half-open identities, an empty
  exact-second control, and offset equivalence for UTC-Z second serialization.
- Six of seven planted failures are meaningful as written; the T1 branch needs
  the direct F2 control.
- Schema, seals, one shared 120-rpm pacer, header-only token handling,
  immutable-root refusal, and downstream CLOSED gates are otherwise sound.

No files were modified by the reviewer.
