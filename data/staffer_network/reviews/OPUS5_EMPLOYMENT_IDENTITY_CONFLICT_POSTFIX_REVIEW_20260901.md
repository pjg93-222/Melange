# Opus 5 employment identity-conflict post-fix review

- Stage: `R0a2a4a1r-opus5-employment-identity-conflict-postfix`
- Model/effort: Claude Opus 5 / maximum
- Mode: read-only
- Verdict: `PASS`
- Blockers: none

The reviewer confirmed that top-level and nested nonblank IDs use identical
`strip().casefold()` normalization; disagreement appends an irreversible
failure; missing/blank/whitespace/`UNRESOLVED` remain fail-closed; emitted IDs
are normalized before corpus keys; and the normalized whitespace/case duplicate
fixture triggers duplicate-row blocking
(`fec/staffer_network/employment_history.py:454-554`, tests `:367-388,675-698`).

Nonblocking findings: a blank string at the top level can suppress use of a
valid nested ID in the safe direction; a non-string top-level value with a
valid nested ID does not receive a dedicated malformed-type code; and the
suite lacks a direct assertion of the emitted normalized string. These remain
fail-closed/diagnostic test backlog.

Measured Python evidence bound to the repair: 47 focused tests and 221 staffer
tests plus 73 subtests passed. This PASS covers code safety only.
