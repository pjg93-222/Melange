# Opus 5 consolidation identity/accounting micro-review

Use Claude Opus 5 maximum effort, read-only. Inspect only
`audits/staffer_network/consolidate_employment_corpus.py:99-138` and
`:308-379`, plus
`audits/staffer_network/test_consolidate_employment_corpus.py:163-276`.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, and exact file/line `EVIDENCE`.

Check only that: blank, whitespace, sentinel `UNRESOLVED`, and conflicting IDs
cannot merge people; identity-less inputs are deterministically preserved in a
separate ledger rather than dropped; normalized duplicates are counted; and
input rows equal identified-consumed plus unidentified rows with exact person
and duplicate conservation. A PASS is code/accounting safety only.
