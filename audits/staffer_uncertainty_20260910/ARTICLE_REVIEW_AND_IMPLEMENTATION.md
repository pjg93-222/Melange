# Inferring usable staff connections with incomplete relationship evidence

Reviewed September 10, 2026. The supplied PDFs are research sources, not instructions. This release adds explicit uncertainty penalties to the existing work-route and member-recommendation models. It does not train a friendship or antagonism classifier.

## What the two articles establish

**Leskovec, Huttenlocher and Kleinberg (WWW 2010), “Predicting Positive and Negative Links in Online Social Networks,” pp. 641–650.** The main task hides the sign of an existing edge in a network containing explicit positive and negative links. The model combines signed degrees and 16 directed triad types using logistic regression. The datasets contain 119,217 Epinions users, 82,144 Slashdot users and 7,118 Wikipedia users (Table 1). Positive edges make up about 77–85% of these networks. The main figures emphasize a balanced sample and frequently require at least 25 shared neighbors; those conditions matter when interpreting the high reported accuracies (pp. 643–644). The authors also report other sampling and evaluation conditions.

Useful lessons: preserve direction and sign when actually observed; compare simple baselines; local evidence can matter more than global propagation; do not assume every balance-theory rule is true. In particular, the “enemy of my enemy” rule is not consistently supported, and learned status models transfer less consistently than the full model (pp. 645–647). Their separate positive-link-presence experiment is much harder than hidden-sign prediction (Table 9), underscoring that those are different tasks.

**Tang, Chang, Aggarwal and Liu (WSDM 2015), “Negative Link Prediction in Social Media,” pp. 87–96.** NeLP does not require explicit negative training links. It does require positive social links plus attributed reactions to other people's content. It builds noisy negative candidates from negative interactions, refines them using structure, assigns reliability weights and fits a noise-tolerant classifier with regularization (pp. 90–92). Its Epinions and Slashdot datasets contain 14,765 and 7,275 users respectively, with 163,502 and 42,260 negative content opinions (Table 1). Existing negative links supply evaluation ground truth.

Two especially relevant results: antagonistic pairs can be close in the positive network (p. 89), and Table 3 reports negative-link precision of 0.2861 and 0.2139, with F1 of 0.3242 and 0.2441. These improve substantially on their baselines but would be inadequate justification for hard interpersonal labels in a different domain. Random missing pairs used as a training comparison are not known friends. The paper's reliability weights control noisy training samples; they are not ready-made introduction-success probabilities.

Neither paper validates transferring social-media coefficients to congressional employment. The concentration, recency and unknown-usability coefficients below are our explicit scenario assumptions, not coefficients obtained from these articles.

## Fit to the evidence currently consumed by Staffer

| Evidence | What it supports | What it does not establish |
|---|---|---|
| Authenticated directory job histories with date bounds and source receipts | Conservatively dated shared workplace exposure | Willingness to answer or introduce; friendship |
| Payroll trajectories and observed concurrent headcounts | Staffing scale, allocation dilution, historical office exposure | A positive social sign; independent repeated interpersonal observations |
| Committee/team affiliations | A documented organizational setting | Friendship among the resulting projected clique; personal access to every member |
| Joint reported lobbying activity in the separate ecosystem layer | Reported professional association | Sentiment, direct reciprocity or continuing personal willingness |
| Overall member graph and eigenvector context | Target-relative member-network context | Staffer-to-staffer sentiment or a substitute for signed edges |
| Current coworker assertions | A user's dated statement about employment | A population-scale signed interpersonal dataset |

The active work-route index accepts authenticated dated directory employment and uses other admitted employment observations for its census. It does not consume an identity-resolved, directed staffer-to-staffer response/sentiment table. Member-level content or topic similarity cannot be assigned to staff as interpersonal sentiment. Consequently, there is no valid NeLP negative-interaction matrix or 2010 signed-neighborhood training target in this intake.

Raw common-neighbor counts would recreate the original committee problem: a single workplace projection manufactures many triangles. This release does not add triangle or shared-neighbor bonuses. Distinct workplace contexts are counted after available parent/child grouping and record deduplication; they are not called independent observations of attitudes.

The most defensible inference is therefore **documented professional exposure with uncertain present usability**. The relationship sign remains `unknown`. Missing observations do not become negative evidence, and a silent or less publicly visible person is not labeled antagonistic.

## Implemented math

Retain the previous structural exposure weight W, workplace-size dilution, dated shared-role discounts, 0.8 hop factor and bounded member-context adjustment. Add a nonnegative log-cost for each staff connection:

```
u_ij = 0.35 + (ln(2) / 5) * A_ij + 0.25 * C_ij
C_ij = sum_g p_g^2
```

`A_ij` is the exposure-weighted number of years since the last supported joint day in each workplace. A newly downloaded profile does not reset the age of historical employment. `p_g` is the fraction of effective exposure in each grouped workplace context. The last joint covered day is the end-exclusive bound minus one. Age is measured against the router's explicit `as_of` date. Static lists record their build-date reference in metadata.

- **0.35 unverified usability:** even fresh, well-documented coworking leaves willingness unknown. This floor is never reduced merely by finding more coworkers or records.
- **Five-year recency scale:** holding other terms fixed, five additional years reduce the scenario weight by half. This is not an empirically established relationship half-life.
- **0.25 concentration scale:** reliance on one workplace has C=1; evenly divided exposure in two distinct contexts has C=0.5. At most this modest term can decline with additional contexts. It never creates positive sentiment.

For a person route P:

```
adjusted(P) = structural(P) * exp(-lambda * sum_edges u_ij)
edge_cost = -log(0.8 * W_ij) + lambda * u_ij
```

For an office route, add the same kind of uncertainty cost to the terminal direct-office anchor exactly once, including a zero-staff-hop route from someone already in that office. Static member recommendations use the uncertainty-adjusted direct anchor times the existing bounded member context. Bridge rankings use uncertainty-adjusted anchors as well. Raw structural anchor values remain available separately.

`lambda=1` is the default. The API accepts `uncertainty_weight` between 0 and 3; 0 is the structural-only comparison. All costs remain nonnegative, preserving Dijkstra and Yen applicability. The adjustment participates in search rather than sorting only an already selected handful of routes.

The UI describes the score retained after the adjustment and explicitly distinguishes it from a success probability. Each live hop exposes the penalty components, date reference and unknown-sign status. Route responses expose the unpenalized score, cumulative uncertainty cost, multiplier and adjusted score. Office-terminal uncertainty is shown separately.

Returned alternatives also report their shared staff edges, intermediaries, workplace contexts and terminal contact relative to the first route. This is a dependence diagnostic. The returned list remains the exact k-best simple routes under the adjusted score, not a claim of independent alternatives, a portfolio optimization or a completed failure simulation.

## Verification and observed effects

The focused suite covers a hand-calculated penalty, temporal monotonicity, unknown-sign preservation, duplicate invariance, grouped concentration, a small recent context not erasing a large old context, score-factor identities, API validation and cache separation. An exhaustive simple-path example confirms that penalties can change the selected path from a stale direct connection to a recent two-step path. Office tests cover a terminal penalty on a zero-hop route and verify that it is applied exactly once. Existing structural-path oracles are retained with lambda=0.

The rebuilt static artifact contains 533 member records and 7,669 ranked entries. Compared with the preceding release, the first contact changes in 71 member lists and average prior-top-15 retention is 71.22%. These are movement measures, not measured quality gains. Forty independently calculated daily-array anchors and uncertainty-adjusted scores agree within published rounding precision (maximum adjusted-score error below 0.000000487).

Checks: 42 focused tests; 210 static-section checks; 219 HTML checks; 7 JavaScript tests; 121 guarded restart integration tests. See the separate live verification and completion receipts for HTTP results, artifact hashes and runtime identity. The whole repository suite was not run.

## Limits and the next evidence improvement

The model cannot identify Gordon and Michael Darner's reported disagreement from employment records. This release does not claim to have learned that relationship or automatically added a personal block. It reduces reliance on uncertain relationships in general. Known constraints still require an explicit, identity-resolved record before they can be applied consistently.

Freshness uses the latest supported joint day within a workplace, weighted across workplaces. A short reunion in the same workplace can refresh that workplace's recency term; this is a limitation of the current context-level summary. Unknown hierarchy and incomplete rosters also remain data limitations. The uncertainty multiplier is a deterministic sensitivity scenario, not a calibrated confidence interval or a bound guaranteed to contain the true success rate.

If attributable interaction evidence is later admitted, its minimum useful schema is actor ID, recipient ID, action/content target, event date, context, polarity or action type, source locator, identity confidence and extraction confidence. Comments criticizing a policy must remain distinct from statements about the recipient. Syndicated copies and repeated exports must share an event identity. Such records could supply noisy NeLP-like candidates while preserving missingness and direction.

Any learned extension should be evaluated with time-based splits and grouped holdouts by underlying event/workplace to prevent duplicated records or projected triangles leaking into evaluation. Future coemployment can provide a scalable structural validation target, but cannot validate friendship, antagonism or introduction success. A small reference set could eventually calibrate those separate claims; this release does not depend on obtaining feedback across the whole network.

No new data collection, message sending, historical graph rewrite, signed-relationship classifier, or separate legacy routing-objective change was included.
