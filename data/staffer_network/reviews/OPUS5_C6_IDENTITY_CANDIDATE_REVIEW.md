# Opus 5 C6 LDA identity-candidate review

`VERDICT: STOP`

Fable was quota-blocked with HTTP 429, so the user directed the same read-only packet to Claude Opus 5. Opus inspected the implementation, schemas, tests, upstream producers, and publication path without file modification or network access.

## Required fixes

1. Candidate schemas must be explicitly restricted from public-generation publication, with a negative test.
2. Zero-confidence, zero-merge, review-required, schema, semantic, and file counts must be measured by rereading/validating emitted rows before a PASS receipt, not asserted as literals.
3. Government-term triage must use the upstream LDA definition rather than a narrower local tuple.
4. Collision notation must expose total cross-source target multiplicity as well as within-source multiplicity.
5. The method name must say normalized-name equality, record a normalizer version, and disclose lossy normalization rules.
6. Each candidate must carry paired raw LDA/target name evidence with its basis; separate unpaired sets are insufficient for human review.

## Non-blocking hardening

- Stage the entire output directory before promotion.
- Bind candidate IDs to corpus digests and method version.
- Permit an empty, valid result rather than encoding non-emptiness as safety.
- Check exact upstream schema IDs and zero-merge/closed-gate properties.
- Add a byte-determinism twin.
- Convert raw key errors to the module's domain error.

## Acceptance state at review

| Criterion | State |
|---|---|
| Zero merge | Conditional; build did not validate its own rows |
| No confidence | Conditional; build did not validate its own rows |
| Normalized-name-only | Matching core passes, method label overclaims raw exactness |
| Deterministic output | By construction, not twin-evidenced |
| Collision notation | Fail; cross-source multiplicity absent |
| Upstream byte/receipt binding | Pass |
| Conservation | Arithmetic present, only enforced on publication path |
| Closed downstream gates | Fail at inspected snapshot |

No live candidate corpus may be built until the six required fixes pass tests and reconciliation.
