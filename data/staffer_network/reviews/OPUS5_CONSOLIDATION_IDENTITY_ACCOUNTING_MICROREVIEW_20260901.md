# Opus 5 consolidation identity/accounting micro-review

- Stage: `R0a2a4b2-opus5-consolidation-identity-accounting`
- Model/effort: Claude Opus 5 / maximum
- Mode: read-only
- Verdict: `PASS`
- Blockers: none

## Accepted checks

- Blank and whitespace IDs cannot key a merge.
- Sentinel `UNRESOLVED` variants cannot key a merge.
- Conflicting IDs are rejected rather than assigned to either person.
- Every unidentified input row is deterministically preserved with global and
  source ordinals, row hash, and rejection reason.
- Whitespace-normalized duplicate IDs are counted.
- Identified-consumed plus unidentified rows conserve the input exactly; output
  person IDs are independently checked for uniqueness.

Evidence:
`audits/staffer_network/consolidate_employment_corpus.py:99-138,308-379` and
`audits/staffer_network/test_consolidate_employment_corpus.py:163-276`.

## Nonblocking findings

The legacy `consolidate()` wrapper discards accounting outputs; conservation
flags are reported in the scoped function and enforced later; one
classification conservation field is tautological; `dropped_input_rows` is a
misleading alias for preserved unidentified rows; case-sensitive identity
comparison can over-split; non-string/zero-width IDs receive coarse reasons;
and no negative fixture drives duplicate output person IDs. These are
fail-closed or observability/test-hardening items, not merge-authority leaks.

This PASS covers identity/accounting code only, not actual identity
adjudication, employment completeness, or canonical promotion.
