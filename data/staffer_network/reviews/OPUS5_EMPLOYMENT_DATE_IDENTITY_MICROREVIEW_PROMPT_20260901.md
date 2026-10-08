# Opus 5 employment date/identity micro-review

Use Claude Opus 5 maximum effort, read-only. Inspect only
`fec/staffer_network/employment_history.py:83-259` and the identity/date logic
used by `audit_history_completeness` at `:277-485`, plus directly relevant
tests at `fec/tests/staffer_network/test_staffer_employment_history.py:270-293`
and `:346-642`. Do not read consolidation, temporal, graph, or acquisition
code.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, and exact file/line `EVIDENCE`.

Check only:

1. malformed, prose, impossible, future, inverted, or unsupported-date
   evidence cannot produce `COMPLETE`;
2. raw/current markers require a real as-of bound, and as-of before start
   cannot pass;
3. each episode requires an HTTP(S) source and defensibly bounded employment
   dates;
4. blank, whitespace, sentinel `UNRESOLVED`, missing, or conflicting person
   identities cannot pass; and
5. no accepted route converts a validation failure into completeness.

A PASS covers code-level fail-closed date/identity safety only, not actual
history completion, identity adjudication, or canonical promotion.
