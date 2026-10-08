# Opus 5 employment identity-conflict post-fix review

Use Claude Opus 5 maximum effort, read-only. Inspect only the final person-ID
resolution block of `audit_history_completeness` in
`fec/staffer_network/employment_history.py` and
`test_conflicting_top_level_and_nested_person_ids_fail_closed` in
`fec/tests/staffer_network/test_staffer_employment_history.py`.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, and exact file/line `EVIDENCE`.

Check only that nonblank top-level and nested LDA person IDs are compared after
the same strip/case normalization used for output; disagreement always makes
employment completeness INCOMPLETE; blank, missing, whitespace, and UNRESOLVED
still fail closed; normalized IDs are emitted so whitespace/case variants key
the same corpus person and trigger duplicate-row blocking; and the chosen
output ID cannot erase a conflict failure. Measured local evidence: 47 focused
tests and 221 staffer tests plus 73 subtests passed after both repairs. This
does not adjudicate identity or bind actual histories.
