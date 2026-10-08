# Opus 5 micro-review: employment audit core

Read-only maximum-effort review for Meta LOOP
`run-20260831T1850525496629Z-8993807782`. Do not edit.

Inspect only:

- `fec/staffer_network/employment_history.py`, from
  `employment_episode_digest` through the return of
  `audit_history_completeness`, plus the few lines in `audit_history_corpus`
  that load and apply the result schema.
- `fec/staffer_network/schemas/history_completeness_audit.schema.json`.
- `fec/tests/staffer_network/test_staffer_employment_history.py`, class
  `HistoryCompletenessAuditTests` only.

The initial blocked review is at
`data/staffer_network/reviews/OPUS5_EMPLOYMENT_COMPLETENESS_REVIEW_20260831.md`.
Re-test its core findings F3-F7 and F9: malformed dates, malformed external
sources, canonical provenance sourcing, typed/legacy gap coexistence, stale or
malformed episode digests, missing person IDs, result-schema validation, and
education remaining nonblocking. Search for any new false
`employment_status=COMPLETE` path.

Measured evidence: the combined targeted suite passed 158 tests and 73
subtests.

Return exactly `PASS`, `PASS_WITH_NONBLOCKING_FINDINGS`, or `BLOCKED`, followed
by concise findings with severity, exact function, counterexample, and smallest
repair. State whether this core verdict can safely gate employment completeness.
Do not inspect consolidation, identity, acquisition, or canonical readiness.
