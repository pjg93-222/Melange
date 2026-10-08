# Opus 5 employment completeness/attestation micro-review

Use Claude Opus 5 maximum effort, read-only. Inspect only
`fec/staffer_network/employment_history.py:260-600`,
`fec/staffer_network/schema_validation.py`, the two history-completeness
schemas, and tests at
`fec/tests/staffer_network/test_staffer_employment_history.py:193-345` and
`:643-754`. Do not read consolidation, temporal, graph, or acquisition code.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, and exact file/line `EVIDENCE`.

Check only:

1. `COMPLETE` requires an attributed, timezone-stamped exhaustive PASS
   attestation whose digest binds the exact normalized episode set;
2. typed and legacy employment gaps must both be empty;
3. duplicate person rows make the person/corpus incomplete rather than
   inflating complete counts;
4. row, person, episode, duplicate, and missing-ID counts conserve exactly;
5. contradictory COMPLETE/PASS schema instances are rejected; and
6. empty or missing-ID corpora fail closed with an INCOMPLETE receipt rather
   than crashing.

Education remains nonblocking. A PASS is code/receipt safety only, not evidence
that the actual 25,340-person corpus is complete or promotion-ready.
