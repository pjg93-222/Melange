# Opus 5 adversarial review: employment-completeness core final

Act as a fresh read-only adversarial reviewer. Inspect only these files:

1. `fec/staffer_network/employment_history.py`
2. `fec/staffer_network/schemas/history_completeness_audit.schema.json`
3. `fec/staffer_network/schemas/history_completeness_audit_receipt.schema.json`
4. `fec/tests/staffer_network/test_staffer_employment_history.py`

The gate must fail closed. A person may be marked employment-complete only when every episode has a defensible start and end/current bound, source provenance resolves to an HTTP(S) URL, no employment gaps remain, and any override is digest-bound, attributed, reasoned, and time-stamped. Education is diagnostic and nonblocking. Name-only identity overlap, a bare observation ID, malformed dates, substring matches such as `currently`, missing IDs, empty corpora, and receipt-count ambiguity must not produce a complete verdict.

The local command already passed:

`python -m pytest -q fec/tests/staffer_network audits/staffer_network/test_consolidate_employment_corpus.py audits/staffer_network/test_build_employment_adjudication_priority_queue.py audits/staffer_network/test_merge_employment_candidate_coverage.py audits/staffer_network/test_build_lda_conservative_bounded_episode_candidates.py`

Result: 173 tests and 73 subtests passed.

Return exactly:

- `VERDICT: PASS` or `VERDICT: BLOCKED`
- `BLOCKERS:` with numbered, code-specific blockers; write `none` only if there is no route by which the audited code can falsely certify employment completeness or emit an invalid/ambiguous receipt.
- `NONBLOCKING_FINDINGS:` with concise hardening notes.
- `EVIDENCE:` cite file and line numbers.

Do not infer implementation outside the four files. Do not soften a blocker because tests pass. Do not edit files.
