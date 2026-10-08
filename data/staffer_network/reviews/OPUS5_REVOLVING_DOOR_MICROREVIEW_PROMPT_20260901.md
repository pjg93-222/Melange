# Opus 5 revolving-door micro-review

Use Opus 5 maximum effort, read-only. Inspect only:

- `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md` sections 7–9;
- `fec/staffer_network/employment_history.py` function
  `transition_gap_bounds` and the revolving-door portion of
  `build_temporal_sidecar`;
- `fec/staffer_network/publication.py` temporal path/edge/receipt validation;
- `fec/staffer_network/schemas/temporal_path.schema.json`;
- `fec/staffer_network/schemas/temporal_edge.schema.json`;
- `fec/staffer_network/schemas/temporal_build_receipt.schema.json`;
- the revolving and `INTERVAL_BLOCKED` tests in
  `fec/tests/staffer_network/test_staffer_employment_history.py`; and
- `audits/staffer_network/M1_MATH_ADVERSARIAL_AUDIT_20260901.md`.

Do not inspect acquisition, graph centrality, consolidation, or unrelated
identity code. Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then
`BLOCKERS`, `NONBLOCKING_FINDINGS`, `EQUATION_CHECKS`, and exact file/line
`EVIDENCE`.

Check only:

1. only ACTIVE episodes with ACCEPTED identity and container enter candidate
   construction;
2. a primary revolving path requires guaranteed Hill-before-industry order;
3. uncertain bounds produce sound ordered `gap_min <= gap_max` bounds;
4. possible-only and wrong-order paths contribute zero primary weight;
5. missing interval bounds produce exactly one deterministic
   `INTERVAL_BLOCKED` path per person/member/organization/role key, with null
   gap bounds, zero weights, conserved receipt count, no edge, and no crash;
6. candidate selection is deterministic and cannot allow one person to count
   twice on the same member/organization/predicate edge;
7. raw edge weight is the number of unique qualifying people and gap-decay
   lower/upper sums use `2**(-gap/730.485)` only for sensitivity, with lower
   no greater than upper;
8. registrant employment and client-activity participation remain distinct
   predicates and roles;
9. schemas and publication validation reject invalid endpoints, leaked
   weights, inverted gaps, self-loops, and receipt non-conservation.

Correct revolving-door math does not authorize using review-candidate
identities, incomplete employment histories, or causal language.
