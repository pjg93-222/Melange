# Opus 5 consolidation attestation post-fix review

- Stage: `R0a2a4b1r-opus5-consolidation-attestation-postfix`
- Model/effort: Claude Opus 5 / maximum
- Verdict: `BLOCKED`

The prior typed-gap fixes passed, but non-list legacy `history_gaps`,
`unresolved_history_gaps`, or `known_gaps` values were still discarded as if
absent. A valid typed empty-list attestation plus a malformed legacy string
could therefore reach `COMPLETE` and drop off the residual queue.

The coordinator added explicit legacy-field type tracking, made malformed
legacy fields force the invalid-gap sentinel, made non-dict source attestations
fail closed, added a negative fixture, and reran 48 focused tests plus 222
staffer tests and 73 subtests with zero failures. A final post-fix review was
required.

Nonblocking findings retained: non-dict episode entries are filtered before the
core audit, invalid sentinels do not preserve all raw typed-gap text, non-list
primary employment fields do not fall back to legacy values, and optimistic
row scoring affects base selection but not recomputed completeness.
