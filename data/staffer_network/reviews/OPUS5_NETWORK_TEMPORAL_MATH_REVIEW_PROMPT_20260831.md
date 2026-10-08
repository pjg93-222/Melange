# Opus 5 focused adversarial review: network and temporal math

Read-only review for Meta LOOP run
`run-20260831T1850525496629Z-8993807782`. Use maximum reasoning. Do not edit.

Inspect:

- `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md`
- `fec/staffer_network/network_math.py`
- `fec/staffer_network/graph_build.py`, lines 180-470
- `fec/staffer_network/employment_history.py`, lines 1160-1585
- `fec/tests/staffer_network/test_staffer_canonical_graph.py`, lines 30-105
- `fec/tests/staffer_network/test_staffer_employment_history.py`, lines
  470-550

Adversarially check unit support/max-deduplication, the tested-but-unwired
noisy-OR statement, equal-active-layer transition, PageRank and dangling
mass, kind-balanced teleport, isolate handling, component-local eigenvectors,
bridging, half-open uncertain intervals, union-before-overlap, duration
transform, transition ordering, unique-person revolving weights, and gap
decay. Look for double counting, inverted bounds, unsupported causal language,
or disagreement between prose and implementation.

Return exactly one verdict: `PASS`, `PASS_WITH_NONBLOCKING_FINDINGS`, or
`BLOCKED`. For each finding give severity, exact function, counterexample, and
smallest repair. Formulas being correct does not open identity, temporal, or
canonical gates over review-candidate evidence.

