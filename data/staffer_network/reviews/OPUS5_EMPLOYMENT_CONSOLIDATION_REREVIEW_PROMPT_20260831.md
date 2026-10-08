# Opus 5 micro-review: employment consolidation and attestation propagation

Read-only maximum-effort review for Meta LOOP
`run-20260831T1850525496629Z-8993807782`. Do not edit.

Inspect only:

- `audits/staffer_network/consolidate_employment_corpus.py`, functions
  `row_score`, `consolidate`, and `residual_row`.
- `fec/staffer_network/employment_history.py`, functions
  `employment_episode_digest` and `audit_history_completeness` only as the
  called contract.
- `audits/staffer_network/test_consolidate_employment_corpus.py`.

The initial blocked review is at
`data/staffer_network/reviews/OPUS5_EMPLOYMENT_COMPLETENESS_REVIEW_20260831.md`.
Re-test its consolidation findings F1, F2, and F8: all source-row employment
gaps must reach the typed attestation; one row's attestation must not certify a
larger merged episode union; malformed existing typed gaps must remain
fail-closed; unresolved seen profiles must remain acquisition-prioritized.
Search for any new false `employment_status=COMPLETE` path caused by merging.

Measured evidence: the combined targeted suite passed 175 tests and 73
subtests after the core was hardened to require attributed, time-stamped,
digest-bound attestations and resolvable HTTP(S) provenance.

Return exactly `VERDICT: PASS` or `VERDICT: BLOCKED`, followed by
`BLOCKERS:`, `NONBLOCKING_FINDINGS:`, and `EVIDENCE:`. Give exact function,
counterexample, and smallest repair for every blocker. State whether
consolidation preserves the safety of the core employment gate. Do not assess
identity, acquisition, or canonical readiness.
