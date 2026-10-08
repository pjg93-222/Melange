# Opus 5 consolidation merged-attestation micro-review

Use Claude Opus 5 maximum effort, read-only. Inspect only
`audits/staffer_network/consolidate_employment_corpus.py:139-307` and
`audits/staffer_network/test_consolidate_employment_corpus.py:32-162`.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, and exact file/line `EVIDENCE`.

Check only that: evidence is deterministically merged; the completeness audit
is rerun over the complete merged episode/gap set; an attestation for a stale
or narrower input row cannot certify added episodes or gaps; malformed typed
gaps fail closed; and status is derived from the recomputed audit rather than
copied or hardcoded. Education is nonblocking. A PASS is code safety only.
