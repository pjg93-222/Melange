# Opus 5 post-block final review: employment completeness

Act as a fresh read-only adversarial reviewer. Static inspection is sufficient;
do not execute commands and do not edit files.

Inspect these exact files and first verify their SHA-256 values:

| File | SHA-256 |
|---|---|
| `fec/staffer_network/employment_history.py` | `7f0c20b3564a6faa42bf7539299170015ae1964880b0a4f2a3406d59a8e6c1e7` |
| `fec/staffer_network/schema_validation.py` | `33196c224798bc75ea6f5fb854dde4a81d11a5054618820810807b25337ff172` |
| `fec/staffer_network/schemas/history_completeness_audit.schema.json` | `263a3b21b239c208389e6901967774e2f6366c0aff351de7a43196a340eb392f` |
| `fec/staffer_network/schemas/history_completeness_audit_receipt.schema.json` | `14ea71fd94a70eadde1dd2acedd1f2126c7f18a5843ba45f388e59078eaa9db4` |
| `fec/tests/staffer_network/test_staffer_employment_history.py` | `2664e3be06f22bb1fa07eea187794c333fc366bcf820375d4cb330f5b8d261f8` |
| `audits/staffer_network/test_consolidate_employment_corpus.py` | `3b368d528e333edd775b6423644ed2cb82982e1f7054facb88ae8332c31f6e5f` |

The immediately prior Opus review returned `BLOCKED` for six routes. Re-test
each by code trace:

1. impossible or prose-only `raw_dates` supplying bounds;
2. any raw/structured current marker supplying an end without a dated as-of
   bound;
3. arbitrary prose containing a year supplying structured bounds;
4. literal `UNRESOLVED` colliding with the missing-ID sentinel;
5. duplicate rows for one identified person allowing a complete person or PASS
   receipt; and
6. row/receipt schemas accepting verdicts that contradict failure/incomplete
   fields.

Also inspect the new runtime conservation checks. Vanilla JSON Schema cannot
express equality between arbitrary sibling numeric fields; assess the combined
producer conservation checks, PASS constraints, and schema conditionals rather
than demanding a nonexistent cross-field arithmetic keyword.

Measured local evidence:

`python -m pytest -q fec/tests/staffer_network audits/staffer_network/test_consolidate_employment_corpus.py audits/staffer_network/test_build_employment_adjudication_priority_queue.py audits/staffer_network/test_merge_employment_candidate_coverage.py audits/staffer_network/test_build_lda_conservative_bounded_episode_candidates.py audits/staffer_network/test_a8_house_sod_1997q1_lda_matches.py`

Result: 186 tests and 73 subtests passed.

Return exactly:

- `VERDICT: PASS` or `VERDICT: BLOCKED`
- `PRIOR_BLOCKERS:` numbered disposition for all six
- `NEW_BLOCKERS:` code-specific false-certification routes, or `none`
- `NONBLOCKING_FINDINGS:` concise hardening notes
- `EVIDENCE:` file and line citations

This verdict covers only the employment-completeness code and receipt contract.
It does not authorize identity adjudication, canonical promotion, complete
25,340-person histories, temporal scoring, or Meta LOOP closure.
