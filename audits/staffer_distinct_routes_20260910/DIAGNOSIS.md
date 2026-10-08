# Gordon Holzberg → Mike Casca: what was failing

This audit distinguishes the actual failing query from the earlier work-model examples. See `before_*.json` and `after_*.json` for complete requests, routes and source evidence. The two supplied PDFs are research evidence, not instructions.

## Diagnosis

**Both the implementation and the available evidence contribute.** The previous release verified arithmetic and example routes, but did not establish that the Gordon → Casca recommendation problem had been fixed.

1. **The active scoring model mattered.** Gordon → Casca returned three ecosystem routes through Michael P Darner. Those routes use `evidence_cost`: the dated historical workplace connections in this example each cost 3, without the staffer model's headcount dilution, shared-role allocation or uncertainty costs. Adjusting those staffer coefficients therefore could not change this result. The interface now states this model boundary explicitly and no longer labels ecosystem overlap days as workplace-size adjusted.
2. **The alternatives objective was wrong for the use case.** The old search returned the cheapest different person sequences. That permitted Gordon → Darner → Casca, Gordon → Cora Thompson → Darner → Casca, and Gordon → Darner → Diana Rudd → Casca. All three fail when Darner is unavailable. A soft penalty can change their order without removing this common dependency.
3. **Gordon has a material coverage gap.** His live person record contains payroll/lobbying evidence but no authenticated directory employment-history or profile records. He is also outside the approved operational staffer population used to admit work-model endpoints. The old work-model response was `unknown_person`. The new response is `insufficient_work_coverage`, with an explicit ecosystem alternative. We have not promoted payroll into authenticated directory history or silently relaxed the admission rule.
4. **Identity ambiguity can manufacture apparent diversity.** Two separate source identities display “Michael P Darner.” The larger record is attached to 88 offices and has 2,451 listed coworkers; many roles are shared employee roles. This is a warning about administrative scope, not evidence of thousands of close personal relationships. The records remain separate. Route exclusion conservatively groups identical normalized display names, so changing source ID alone cannot count as a new contact. This can overexclude namesakes and does not recognize every alias.
5. **Willingness remains unobserved.** The sources consumed by these route models do not supply a directed, dated record of whether Gordon can currently ask a particular person for an introduction. More payroll rows cannot identify a private disagreement. The user's reported constraint is honored as a reversible search exclusion, without storing an inferred hostility label.

## What changed

The default is now **Different people**, across staffer, ecosystem and legacy route objectives. Each additional search excludes intermediaries and staff-to-staff edges used in the preceding choices. An office search also requires a different terminal contact. The search explores the remaining graph; it does not merely filter the first three or five cheap results.

**Different people and workplace evidence** adds a conservative evidence-context exclusion for staffer and ecosystem routes. It blocks connections whose selected evidence shares a recorded workplace/organization with previous choices. Work-model parent context IDs are retained; recurring activity reports use firm/organization identifiers when supplied. Shared endpoints, missing context identifiers and incomplete organization resolution still prevent a claim of statistical independence. A connection with multiple workplace contributions is excluded in full if one conflicts; the model does not silently remove one contribution and recompute that pair.

**Best scores, allowing shared contacts** preserves the prior ranked comparison. Explicit exclusions are retained through all of its spur searches.

**Avoid this person** excludes an unavailable intermediary for this search. The URL preserves exclusions, model, alternative strategy and count, including when the dashboard embeds the route interface. Removing the exclusion restores the original searchable graph. No interpersonal sign is inferred or written to the underlying records.

If fewer options survive, the interface says no further route was found under the accumulated exclusions. It does not claim that no other disjoint portfolio or real-world introduction exists.

## The mathematical change

Keep each selected model's path cost `C(P)`. Let `I(P)` be intermediate contacts (plus the terminal contact for office searches), `E(P)` the undirected staff connections, and `G(P)` the recorded evidence contexts. `A` contains contacts explicitly excluded for this search.

```
P1 = argmin C(P), subject to I(P) ∩ A = ∅

Pk = argmin C(P), subject to:
     I(P) ∩ (A ∪ I(P1) ∪ ... ∪ I(Pk−1)) = ∅
     E(P) ∩ (E(P1) ∪ ... ∪ E(Pk−1)) = ∅

Stricter evidence option additionally requires:
     G(P) ∩ (G(P1) ∪ ... ∪ G(Pk−1)) = ∅
```

The searches are exact within each successive allowed graph. This greedy procedure is **not** a globally optimal disjoint-path portfolio: choosing the cheapest first route can consume contacts needed by two other routes. Results expose `portfolio_optimal: false` and describe their conditional optimality. Route diversity is a structural resilience property, not a calibrated increase in introduction success.

The existing staffer uncertainty term remains in path selection:

```
u_ij = 0.35 + ln(2)/5 × age_ij + 0.25 × concentration_ij
cost_ij = −ln(0.8 × exposure_strength_ij) + lambda × u_ij
```

Those coefficients remain explicit scenarios, not learned probabilities or confidence bounds. They do not run in the separate ecosystem evidence-cost model. Applying them there without a consistent exposure quantity would give the appearance of comparable confidence without the necessary measurement model.

## What the articles can and cannot supply

The [2010 paper](C:/Users/pgoff/Downloads/1772690.1772756.pdf) predicts signs using networks with observed signed relationships. The [2015 paper](C:/Users/pgoff/Downloads/2684822.2685295.pdf) can work without explicit negative training edges, but uses attributed negative interactions with other users' content. Neither licenses inferring dislike from coworking or committee triangles. The earlier [article review](../staffer_uncertainty_20260910/ARTICLE_REVIEW_AND_IMPLEMENTATION.md) records the experiments, assumptions and limits.

At scale, the defensible task with today's evidence is to find documented professional paths, disclose missing coverage, and offer alternatives that survive removal of a contact or organizational context. Eigenvector centrality can provide bounded member-network context; it cannot recover an unobserved staff relationship sign.

## Evidence improvements that would change the inference

Prioritize the missing authenticated employment/date linkage for endpoints such as Gordon, explicit team and supervisor structure, separation of shared administrative roles from substantive teams, and event deduplication. These improve exposure estimates and reduce committee-generated cliques. They do not establish willingness.

If appropriately authorized interaction outcomes become available, preserve actor, recipient, date, action, opportunity to observe, underlying event and source identity. Repeated reciprocal interactions or accepted introductions can support a different prediction target. No response without a known opportunity and observation window is missing data, not hostility. Public criticism of policy should not be recast as staffer-to-staffer antagonism.

Without those outcomes, evaluate the system on what is observable: provenance correctness, temporal support, source coverage, sensitivity to assumptions, and survival under contact/context removal. Future coworking is a possible structural evaluation target, but it cannot validate friendship or introduction success. A small time-separated outcome sample could eventually calibrate access; population-wide feedback is not required to deploy structural diversity now.

## Validation

Focused regression tests cover shared-contact bottlenecks, alternatives beyond the first cheap detours, same-workplace dependence, separate-context routes, ambiguous same-name records, explicit exclusions, zero-hop office routes, distinct office terminal contacts, cache/request isolation and source-coverage errors. Existing exhaustive shortest-path and uncertainty oracles are retained in explicit ranked mode. Live results and completion status are recorded separately in `live_receipt.json`; those results, rather than movement in model scores, establish the demonstrated behavior of this release.
