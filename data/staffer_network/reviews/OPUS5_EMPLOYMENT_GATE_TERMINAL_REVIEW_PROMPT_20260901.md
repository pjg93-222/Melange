# Opus 5 terminal employment-gate review

Use Claude Opus 5 at maximum effort. Read-only; do not edit. You may use
`sha256sum` only to verify these pins:

| File | SHA-256 |
|---|---|
| `fec/staffer_network/employment_history.py` | `1add7ddbaf1be16fcd336af7f4f0e84e11b5f070c8fa7a33428fd48667484447` |
| `fec/staffer_network/schema_validation.py` | `33196c224798bc75ea6f5fb854dde4a81d11a5054618820810807b25337ff172` |
| `fec/staffer_network/schemas/history_completeness_audit.schema.json` | `263a3b21b239c208389e6901967774e2f6366c0aff351de7a43196a340eb392f` |
| `fec/staffer_network/schemas/history_completeness_audit_receipt.schema.json` | `14ea71fd94a70eadde1dd2acedd1f2126c7f18a5843ba45f388e59078eaa9db4` |
| `fec/tests/staffer_network/test_staffer_employment_history.py` | `cdc4ccf86422ef968edfe2b197d83307f4da23dfab647dfc1e15da270ab49862` |
| `audits/staffer_network/consolidate_employment_corpus.py` | `e276ad325e13aeef221462e6c143e8fa343d73c9286bdd02853b93194f110aa7` |
| `audits/staffer_network/test_consolidate_employment_corpus.py` | `efc88fdaf9cae975b7a4cc87e958dbe31d0a0d557a06c22fca9878faf86f38f9` |
| `fec/staffer_network/schemas/working_history_corpus_receipt.schema.json` | `f6ba663a7aba8d65e1c56ca7958f2877354be90dbd1ddb368be8947753683b4b` |

This is a narrow terminal re-test of every blocking route found in the two
prior Opus reviews:

1. malformed/prose/raw/future/inverted employment dates;
2. current markers without as-of bounds or as-of before start;
3. `UNRESOLVED`/blank/whitespace/conflicting identities;
4. duplicate person rows and count conservation;
5. contradictory COMPLETE/PASS schemas;
6. consolidation attestations over merged/gapped episode sets;
7. hardcoded consolidation PASS over unresolved people;
8. silently dropped identity-less rows or sentinel cross-person merges; and
9. receipt schema/semantic validation and deterministic unidentified-row
   accounting.

Trace both positive and negative paths. The gate may mark employment COMPLETE
only when every episode is sourced and defensibly bounded, the exact episode
set is digest-bound to an attributed time-stamped exhaustive PASS attestation,
all typed/legacy gaps are empty, identity is non-sentinel, and the corpus has
no duplicate or unidentified rows. Education remains nonblocking.

Measured local evidence: 218 tests plus 73 subtests passed; 11 focused
consolidation tests passed; synthetic primary/twin outputs were byte-identical
and a forged consolidation PASS was rejected.

Return exactly:

- `VERDICT: PASS` or `VERDICT: BLOCKED`
- `PRIOR_BLOCKERS:` numbered disposition for all nine routes
- `NEW_BLOCKERS:` or `none`
- `NONBLOCKING_FINDINGS:`
- `EVIDENCE:` exact file/line citations

This verdict covers code-level employment-completeness and receipt safety only.
It does not assert that the actual 25,340-person corpus is complete, adjudicate
identity, authorize canonical promotion, open temporal scoring, or close the
Meta LOOP.
