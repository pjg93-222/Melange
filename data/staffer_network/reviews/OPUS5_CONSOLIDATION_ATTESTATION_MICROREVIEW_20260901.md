# Opus 5 consolidation merged-attestation micro-review

- Stage: `R0a2a4b1-opus5-consolidation-attestation`
- Model/effort: Claude Opus 5 / maximum
- Mode: read-only
- Returned verdict: `PASS`
- Returned blockers: none

## Accepted checks

- Evidence merge is deterministic by signature and sorted keys/sources.
- The completeness audit is rerun after the complete merged episode, gap, and
  attestation set is assembled.
- Added episodes, legacy gaps, and typed gaps invalidate stale/narrower source
  attestations.
- Malformed typed gaps fail closed.
- Completion status is derived from the recomputed audit, not copied from an
  input row.

Primary evidence:
`audits/staffer_network/consolidate_employment_corpus.py:183-303` and
`audits/staffer_network/test_consolidate_employment_corpus.py:45-160`.

## Returned conditional finding and adjudication

The reviewer found that absent or null typed-gap fields were normalized to an
empty list. It explicitly said this escalates to blocking if the core audit
rejects missing/null gap fields. The core audit does reject them at
`fec/staffer_network/employment_history.py:428-441` with
`UNRESOLVED_EMPLOYMENT_GAPS_INVALID`. The review also noted that blank-looking
gaps were filtered and explicit-null primary episode fields shadowed populated
legacy fields.

Therefore the coordinator did **not** treat the returned PASS as terminal. The
conditional finding was escalated, the consolidator was repaired, two focused
tests were added, 46 focused tests and then 220 staffer tests plus 73 subtests
passed, and a fresh post-fix review was required.

Other nonblocking findings retained: missing positive COMPLETE control,
diagnostic loss when no base attestation exists, input-order tie behavior,
first-wins handling for non-signature episode fields, and fail-loud unhashable
LegiStorm IDs.
