# Opus 5 structural-math micro-review — 2026-09-01

**Verdict:** `PASS`  
**Mode:** read-only static review, maximum effort

## Equation disposition

- Unit/max-deduplicated structural support matches implementation.
- The noisy-OR combiner is tested but is not wired into graph production and
  is labeled evidence strength, not identity probability.
- Equal-active-layer transition allocation, within-layer proportional mass,
  dangling redistribution, kind-balanced teleport, and PageRank mass are
  coherent.
- Isolates receive teleport-only connectedness, are flagged, and are excluded
  from ranked outputs.
- Eigenvectors use `(P + P.T)/2` per component, L1-normalize within component,
  emit nonconvergence as null, and are not globally compared.
- Bridging implements normalized Simpson diversity separately from strength or
  connectedness.
- No composite influence score is emitted.

## Nonblocking findings

1. Eigenvector convergence uses an absolute per-entry tolerance after
   component-local L1 normalization, so relative precision varies with
   component size.
2. `layer_balanced_transition` relies on caller-side deduplication; an
   undeduplicated future caller could make within-layer mass reflect row count.
3. Exact bridge invariance/isolate/single-kind and nonuniform within-layer
   proportional rules lack direct tests.
4. The PageRank test checks mass after final renormalization and does not
   exercise the dangling path.
5. Candidate-exclusion behavior is correct by trace but not tested by comparing
   builds with candidate inclusion toggled.
6. `network_math.py` uses the phrase “connectedness influence” in its module
   docstring despite the governing non-causal label.
7. `raw_strength` and `connectedness_within_kind` need explicit documentation;
   within-kind values over isolate-only kinds need a clearer caveat.
8. The entity display-name re-read should assert the canonical ID order.

These findings do not invalidate emitted structural values, but they belong in
the implementation backlog and diagnostic. Structural PASS does not authorize
identity, temporal, canonical, or causal claims.
