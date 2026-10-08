# Fable C1 v4 document review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

Act as a fresh read-only adversarial reviewer. Return `PASS`, `REVISE`, or
`BLOCK`, with findings by severity. Do not edit files.

Read completely:

- `STAFFER_NETWORK_METRICS_20260830.md`
- `STAFFER_NETWORK_EXPANSION_DESIGN_20260830.md`
- `STAFFER_NETWORK_CORPUS_SPEC_20260830.md`
- `audits/STAFFER_NETWORK_IMPLEMENTATION_DIAGNOSTIC_20260830.md`
- `data/staffer_network/reviews/FABLE_C1_PLAN_REVIEW.md`
- `fec/tests/staffer_network/test_staffer_documents.py`

Verify the documents against the receipts named in the C1 plan. Pay special
attention to:

- the category 5 Donation / category 7 Lobbying correction and exact arithmetic;
- C-6, C-10a, Q-1, R-2, C-5, and new I-16 scopes;
- the required distinction between source-native readiness and canonical/
  analytical readiness;
- provisional legacy ratification, ShareAlike publication review, single-use
  model-labeled holdout, and LDA fail/running wording;
- Paul's legislator → staff → industry hierarchy as revised into term/office,
  temporal-person-role, organization/activity evidence;
- implementable code/artifact map, phase exits, and next backlog;
- preservation of the 2026-08-29 evidence set.

Current checks:

- `test_staffer_documents.py`: 3/3 pass.
- The test pins all four 2026-08-29 workspace hashes and asserts required v4
  counts/readiness qualifiers.
- The attached Downloads originals were not changed; their SHA-256 values remain
  `38bdd7e9…c46bae` (metrics) and `7369df96…b4d5c` (design).
- No live LDA page count is used as a completion denominator. C-5 is stated as
  FAIL / REMEDIATION RUNNING.

Decide whether the four documents form a coherent, implementation-ready metric
and design package without overstating corpus completion, identity validity,
license authority, or analysis readiness.
