# Opus 5 employment-core terminal micro-review

Use Claude Opus 5 maximum effort, read-only. Inspect only:

- `fec/staffer_network/employment_history.py` through the employment-history
  completeness audit (exclude temporal-sidecar code);
- `fec/staffer_network/schema_validation.py`;
- `fec/staffer_network/schemas/history_completeness_audit.schema.json`;
- `fec/staffer_network/schemas/history_completeness_audit_receipt.schema.json`;
- `fec/staffer_network/schemas/employment_episode.schema.json`; and
- directly related tests in
  `fec/tests/staffer_network/test_staffer_employment_history.py`.

The pinned code hashes are:

- `employment_history.py`:
  `1add7ddbaf1be16fcd336af7f4f0e84e11b5f070c8fa7a33428fd48667484447`;
- `schema_validation.py`:
  `33196c224798bc75ea6f5fb854dde4a81d11a5054618820810807b25337ff172`;
- history audit row schema:
  `263a3b21b239c208389e6901967774e2f6366c0aff351de7a43196a340eb392f`;
- history audit receipt schema:
  `14ea71fd94a70eadde1dd2acedd1f2126c7f18a5843ba45f388e59078eaa9db4`;
- tests:
  `cdc4ccf86422ef968edfe2b197d83307f4da23dfab647dfc1e15da270ab49862`.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, and exact file/line `EVIDENCE`.

Re-test only these prior blocking routes:

1. malformed, prose, impossible, future, or inverted employment dates fail;
2. current markers require an as-of bound and as-of cannot precede start;
3. blank, whitespace, sentinel `UNRESOLVED`, or conflicting identities fail;
4. duplicate person rows make the corpus incomplete and all people/episode
   counts are conserved; and
5. `COMPLETE`/`PASS` requires every sourced bounded episode, an attributed
   timezone-stamped exhaustive PASS attestation digest-bound to the exact
   episode set, and no typed or legacy employment gaps.

Education remains nonblocking. A core PASS is code-safety only and does not
assert that any actual lobbyist has a complete history or authorize canonical
promotion.
