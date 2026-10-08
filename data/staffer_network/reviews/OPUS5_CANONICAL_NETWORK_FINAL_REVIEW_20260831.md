# Opus 5 Canonical/Network Final Adversarial Review

**Date:** 2026-08-31 UTC  
**Final verdict:** **PASS**  
**Reviewed canonical generation:** `generation-20260831T042000Z`  
**Reviewed graph generation:** `generation-20260831T052000Z`

The final Opus 5 pass directly read the implementation modules and repository
schemas. Its Claude CLI permission layer could not open the Downloads attachment
or machine-local receipts during that pass; Codex separately schema-validated
both production receipts, recomputed loader hashes, and directly reviewed the
attached equations. Receipt claims below therefore combine Opus's direct code
review with independently executed production checks rather than pretending the
second reviewer read files it could not access.

## Blocker closure

Opus verified both prior blockers as closed.

1. **Repeated support is non-additive in scoring.** Evidence rows remain
   conserved, but `deduplicate_undirected_layer_edges` keys on unordered
   endpoint pair plus layer and retains the maximum support. The production
   receipt reconciles 5,258,369 primary evidence edges to 5,235,347 primary
   scoring keys, excluding exactly 23,022 repeats. `raw_strength` uses the same
   deduplicated arrays.
2. **Source activation is evidentiary.** Canonical generation requires and
   schema-validates the internal-analysis authority manifest, aborts unless all
   five inputs are explicitly enabled, seals the manifest SHA-256, and derives
   source states and redistribution posture from it rather than hardcoding
   them.

## Math ruling

- Direct structural support `1.0`, equal-active-layer transition allocation,
  and undirected connectedness traversal are internally consistent and
  honestly disclosed.
- PageRank is standard, handles dangling mass correctly, fails on
  nonconvergence, and converged at 0.70/0.85/0.95. Cross-kind scores are shaped
  by the entity-kind-balanced teleport prior; use within-kind connectedness for
  comparisons and do not call the result causal influence. Isolates retain
  positive teleport-only mass, so v6 emits primary/exploratory isolate flags and
  ranked reads must exclude the applicable isolate rows.
- Component-local eigenvector diagnostics are correct but not comparable
  across components. Four nonconverged components/585 nodes are null rather
  than approximate; this is a degree-normalized diagnostic, not standard
  Bonacich eigenvector centrality.
- Bridging is normalized Simpson diversity of layer-balanced walk mass, is null
  for isolates, and is not directly comparable across entity kinds with
  different feasible neighbor-kind sets.
- Equal-active-layer allocation is a strong modeling prior, not a neutral
  empirical estimate. The exploratory identity-candidate layer can receive a
  large fraction of a node's walk mass, which is why it remains excluded from
  primary scores and explicitly labeled exploratory.
- The null composite score is the correct decision; arbitrary global-max
  coefficients would mix units and double-count connectivity.

## Attached 2026-08-29 §6 ruling

Opus agreed the proposed temporal math is not implemented and must not be
implemented as written:

- `O_min` is a valid conservative interval-overlap concept.
- `w_work` must use the union of overlap intervals, not a cross-product sum over
  retained episodes.
- `w_x` creates circularity with the member graph and is rejected/removed for
  any study relating staff and member-network structure.
- the education term has an undefined coefficient/similarity distinction;
- `w_sup` needs a zero clamp and remains default-off because titles do not prove
  supervision;
- the shared-staffer overlay is primarily a sequential pipeline network and
  needs an office-size/tenure-preserving null model;
- `W_rev(m,f)` must bind persons to firm `f`, enforce Hill-exit-before-lobbying
  ordering, and use verified identity/employment facts;
- the `0.60/0.15/0.25` global-max composite is rejected.

## Contact and governance ruling

Opus accepted contact minimization: field-level exclusion is primary, regex
sanitization is defense in depth, fact identifiers are recomputed when literal
content changes, and empty source literals are counted separately from
contact-only exclusions. The final canonical receipt reports zero contact-only
facts, 68 empty LDA covered-position literals, and explicit contact-redaction
counts.

The authority is internal-analysis-only and makes no raw-redistribution claim.
Politico's v3 source policy is authorized and contact-free-derived-only. Exact
name links remain noncanonical and primary scores exclude all of them.

## Highest-value follow-up closure

Canonical v6 sets all 11,758 undated Politico member-role `STAFFS_FOR` facts to
`temporal_weight=0.0` and aborts generation if any `undated-only` fact has
nonzero temporal weight. The receipt zero is the result of that fail-closed
construction, not an independently estimated readiness measure. The graph is
structurally unchanged because it uses `structural_weight`. Co-tenure/as-of math
remains unbuilt until supported dated employment episodes and resolved identity
evidence exist; LDA filing dates are not employment episodes. The prior
undated-weight invariant defect itself is closed.
