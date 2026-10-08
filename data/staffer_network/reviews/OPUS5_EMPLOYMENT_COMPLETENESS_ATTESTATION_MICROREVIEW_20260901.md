# Opus 5 employment completeness/attestation micro-review

- Stage: `R0a2a4a2-opus5-employment-completeness-attestation`
- Model/effort: Claude Opus 5 / maximum
- Mode: read-only
- Verdict: `BLOCKED`

## Blocker

Person IDs were stripped/case-checked only for validity but emitted raw. Two
rows such as `lda:lobbyist:1` and ` LDA:LOBBYIST:1 ` could key as separate
people, evade duplicate detection, and permit a false corpus `PASS`
(`fec/staffer_network/employment_history.py:458-473,519-570`, pre-fix).

The coordinator accepted the blocker, made output use the same strip/case
normalization as identity comparison, strengthened the duplicate fixture with
a whitespace/case variant, and reran 47 focused tests plus the full 221-test
and 73-subtest Python suite with zero failures. The earlier identity-conflict
repair and this normalization repair are covered by one fresh post-fix review.

## Checks that passed

- Attributed, timezone-stamped, digest-bound exhaustive PASS attestation.
- Typed/legacy gap validation and fail-closed unresolved gaps.
- Duplicate and person-status accounting once rows share a normalized key.
- Contradictory row/receipt schema instances are rejected on the producer path.
- Zero-row and missing-ID corpora emit INCOMPLETE receipts.

## Nonblocking findings

The receipt lacks a corpus-level episode aggregate; two conservation equations
are algebraic self-checks; schemas are weaker than producer semantics for some
cross-field claims; duplicate COMPLETE rows lack a per-row duplicate marker;
non-mapping top-level input may abort before a receipt; an empty path list is a
typed caller error; and simultaneous legacy/new employment arrays use the new
field only.

This preserved BLOCKED verdict cannot be reversed by the local fix alone.
