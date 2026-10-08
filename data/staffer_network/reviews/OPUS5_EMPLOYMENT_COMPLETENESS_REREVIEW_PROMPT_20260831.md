# Opus 5 focused re-review: employment completeness remediation

Read-only adversarial re-review for Meta LOOP run
`run-20260831T1850525496629Z-8993807782`. Use maximum reasoning. Do not edit.

Your initial review is preserved at
`data/staffer_network/reviews/OPUS5_EMPLOYMENT_COMPLETENESS_REVIEW_20260831.md`
with verdict `BLOCKED`. None of its findings were waived.

Inspect the repaired regions only:

- `fec/staffer_network/employment_history.py`, from
  `employment_episode_digest` through `audit_history_completeness`, plus the
  result-schema validation inside `audit_history_corpus`.
- `fec/staffer_network/schemas/history_completeness_audit.schema.json`.
- `audits/staffer_network/consolidate_employment_corpus.py`, functions
  `consolidate` and `residual_row`.
- `fec/tests/staffer_network/test_staffer_employment_history.py`, class
  `HistoryCompletenessAuditTests`.
- `audits/staffer_network/test_consolidate_employment_corpus.py`.

Repairs claimed:

1. Collected history gaps are merged into the typed employment-gap attestation.
2. `attested_episode_digest` must equal an order-independent digest of the exact
   merged episode set.
3. Start/end evidence must contain a year token unless the end is explicitly
   current.
4. External sources must be HTTP(S) URLs with a host; canonical episode shapes
   may instead carry nonempty provenance observation IDs.
5. Typed and legacy gap lists are union-gated rather than shadowed.
6. Missing person IDs fail the verdict; missing education attestation stays
   diagnostic-only; unresolved profiles retain high acquisition priority.
7. v2 audit rows are validated against a dedicated schema.

Measured evidence: the full targeted staffer and new audit suite exited 0 with
158 tests and 73 subtests passing.

Attempt to reproduce every original finding and search for any new false
`employment_status=COMPLETE` path introduced by the repairs. Pay particular
attention to merged gaps, stale or malformed digests, episode ordering, malformed
dates, malformed URLs, canonical observation sourcing, education-only behavior,
and typed/legacy gap coexistence.

Return exactly one verdict: `PASS`, `PASS_WITH_NONBLOCKING_FINDINGS`, or
`BLOCKED`. For every remaining finding give severity, exact file/function,
counterexample, and smallest repair. State whether `COMPLETE` is now safe to use
as an employment-completeness gate. Do not assess identity or canonical readiness.
