# Opus 5 consolidation attestation post-fix micro-review

Use Claude Opus 5 maximum effort, read-only. Inspect only:

- `audits/staffer_network/consolidate_employment_corpus.py` functions
  `episodes`, `education`, and the gap/attestation block inside
  `_consolidate_identified`;
- the five attestation/gap consolidation tests, including
  `test_missing_or_null_typed_gap_field_cannot_be_laundered_to_empty` and
  `test_blank_gap_and_null_primary_history_fallback_are_preserved`; and
- `fec/staffer_network/employment_history.py` attestation gap validation inside
  `audit_history_completeness`.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, and exact file/line `EVIDENCE`.

Check only that consolidation cannot strengthen missing, null, malformed
typed, malformed legacy, blank-looking, stale, or narrower source gap evidence
into a clean empty list; non-dict source attestations fail closed;
all merged episodes and gaps remain bound to the recomputed audit; explicit
null primary fields correctly fall back to legacy employment/education fields;
and the changed path still fails closed without copying a stale COMPLETE.

Measured local evidence: 48 focused tests passed, followed by 222 staffer tests
plus 73 subtests with zero failures. This is code safety only, not actual corpus
completion or promotion authority.
