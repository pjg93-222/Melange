# Opus 5 structural-math micro-review

Use Opus 5 maximum effort, read-only. Inspect only:

- `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md` sections 1–5 and 8;
- `fec/staffer_network/network_math.py`;
- `fec/staffer_network/graph_build.py` functions that aggregate structural
  edges, build transitions/teleport, PageRank, eigenvectors, and bridge scores;
- `fec/tests/staffer_network/test_staffer_canonical_graph.py`.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, `EQUATION_CHECKS`, and exact file/line `EVIDENCE`.

Check only:

1. unit structural support and maximum dedup by unordered endpoint/layer;
2. noisy-OR is tested but not wired/labeled as identity probability;
3. equal-active-layer transition allocation, within-layer proportional mass,
   dangling redistribution, kind-balanced teleport, and PageRank mass
   conservation;
4. isolates receive teleport only and are excluded from ranked outputs;
5. eigenvectors use the symmetrized graph per component, L1 normalize only
   within component, and are never globally compared;
6. bridge score is normalized Simpson diversity and is not strength,
   connectedness, influence, access, or causation; and
7. zero/NaN/division/component-scale/double-counting counterexamples.

Do not inspect acquisition or temporal code. Correct structural math does not
open identity, temporal, canonical, or causal gates.
