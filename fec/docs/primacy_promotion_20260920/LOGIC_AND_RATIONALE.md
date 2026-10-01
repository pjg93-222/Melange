# Logic and rationale — mathematical repair review, September 20, 2026

The current rankings are Paul's accepted regression baseline. This review repairs invalid behavior and clarifies what the model measures. It does not optimize weights to preserve particular members or to maximize agreement with ACU. External recognition is useful evidence to investigate, not an answer key.

## The model's job

The leading question is **how much of a member's observed, classified portfolio advances credit-union interests?** It is not their overall political power or the percentage of everything they do in Congress. The denominator and source coverage limit that interpretation.

Five quantities should remain distinguishable:

| Quantity | Lobbying meaning | Mathematical discipline |
|---|---|---|
| CU dedication | Consistent attention to CU interests | A defined, weighted portfolio and explicit treatment of opposition |
| Confidence | How well the record establishes that dedication | Depth, coverage and dependence between observations |
| Leadership and action | Initiating, advancing and delivering relevant work | A declared action unit and opportunity denominator |
| Strategic usefulness | Value of engaging the office on the next objective | A separate decision about access, authority and persuadability |
| Conduct | Specific unresolved breaches and earned remedies | Transparent restrictions, enforced together with eligibility |

A powerful office can deserve lobbying attention without earning a champion designation. A dedicated ally can deserve recognition without being the next persuasion priority. Combining those objectives into one number would obscure the distinction the user has repeatedly drawn.

## What the current equations say

The dedication factor is a signed weighted average, shrunk toward the roster baseline:

`P = baseline + min(1, mass / 15) × (observed − baseline)`

With the adopted additional uncertainty penalty set to zero, this is a convex combination. At fixed mass and baseline, better alignment cannot lower P. Until mass reaches 15, more evidence moves the estimate toward the member's observed record; it raises an above-baseline estimate and lowers a below-baseline one. At 15 the factor is fully unshrunk, not statistically certain. That is a declared reliability convention, not a universal bonus for activity. The shrinkage coefficient is not a calibrated probability of correctness, and role-weighted mass is not a count of statistically independent observations.

The fixed-mass condition matters. Replacing an act with a more CU-aligned act of the same weight must not reduce dedication. Adding a new, partially relevant positive act can nevertheless lower an already purer observed share: a raw portfolio averaging 1.0 becomes .75 when an equally weighted .5 act is added. That is consistent with a portfolio-share objective, even though total supportive activity grew. Action volume and dedication answer different questions; the full shrunk/composite score can also change through its other inputs.

The CU board score is `P × (.8 + .2G)`, where G is the grade percentile. For nonnegative P and G in [0,1], the score never decreases when either input increases. Grade changes the multiplier from .8 to 1: for P > 0, a maximum 25% increase relative to the grade-zero score. At P = 0, the score stays zero. This does not bound rank movement. Subsequent percentiles and seating constraints preserve neither absolute distances nor an interpretation of “20% of the final ranking.” The repaired implementation refuses unsupported negative P in this product; signed factors remain supported by the separate factor-only mode.

For interpretation, a future explanation can display weighted supportive contribution and weighted opposing contribution separately, alongside their net. For example, .60 support with no opposition and .80 support with .20 opposition both net .60, but describe different relationships. This disclosure would not require another ranking formula.

## Repairs and their boundary

CU evidence and conduct floors must apply simultaneously. Combine each member's minimum permitted slot by maximum, then seat once. If a compact fixed-size layout is infeasible, publication must explain that fact rather than silently admit an ineligible member. Unknown service dates must not acquire the favorable denominator reserved for a documented short tenure. Nonfinite numbers and booleans must be rejected before conversion can turn them into apparently valid evidence.

A refresh must also be a fixed point when facts are unchanged. Incremental discovery is not the full evidence universe: an accepted sponsorship must not vanish merely because the verifier now finds it already present. Cumulative verified admissions supply that persistence; current withdrawals, role corrections and scope exclusions still determine which historical facts earn present credit. This invariant takes precedence over preserving a preferred numerical placement. Its correction preserves the accepted CU top 50 and tiers here, but legitimately changes other positions.

The non-CU boards have a different existing contract: primary evidence gets seating priority, but only Tier 1 has the mandatory qualification check. The current bank, crypto and fintech boards have 23, 40 and 6 qualified members respectively, fewer than 85. Preserving those boards requires stating that policy explicitly in their own seating implementation. It does not justify weakening the strict CU constraint helper. Redesigning non-CU tier sizes or adding vacancies is a separate decision.

## Decisions worth making next

| Decision | Recommendation | Reason and adoption test |
|---|---|---|
| Equal support versus opposition | Start with equal magnitude for equally consequential acts; keep conduct separate | The current signed tensor yields +.60 versus −.20 on matched fixtures. An unsigned intensity multiplier with direction applied once is a candidate, not an adopted correction. Require sign symmetry and monotonicity across the full valid domain; examine all movers. An explicit harm multiplier is an alternative if opposition should count more. |
| Repeated publications | Count one substantive commitment; disclose repetition as communication effort | A crosspost is additional reach, not necessarily another independent commitment. Define event identity before deduplicating. Compare current occurrences with an event-based candidate across the whole corpus. |
| Thin media | Separate absent, observed-thin, neutral and negative records | The five-occurrence floor converts 243 current members' media values to zero. Crossing that threshold can produce a discontinuity. A smooth reliability blend needs a declared reference value and a defensible evidence unit; do not choose a curve just to protect placements. |
| Role and amendment units | Declare whether factor measures portfolio ownership while grade measures leadership | The two use different role ratios; the factor halves amendment mass, while grade does not. These can be distinct estimands, but cannot be described as the same units or a universal half-amendment rule. |
| Eligibility — implemented | Keep 13 Tier 1 seats, with a stronger affirmative-support gate | Paul selected this direction on September 20. The existing .75 threshold now also requires affirmative CU-primary contribution, with effective direction applied once, and positive raw portfolio alignment. Neutral and adverse acts cannot qualify as affirmative evidence. Existing approved primary leadership credits remain. No pin bypasses this gate, and infeasible seating raises an error. Frozen-input thresholds .5, .75 and 1.0 produce identical current placements; the existing .75 is retained rather than chosen to fit a member. |
| Chamber comparison | Retain approved chamber seating during repairs; disclose raw values beside relative standing | A percentile answers “relative to whom?” It is not a probability or proof of positive advocacy. Any pooled alternative needs an explicit House/Senate opportunity model. |

The recommended sequence is to resolve direction symmetry and the substantive-event unit first, then evaluate media reliability and qualification. Every candidate should pass algebraic and edge-case tests before its ranking is inspected. Publish sensitivity across a reasonable parameter range, all member movements and source-coverage limitations. ACU agreement and the named diagnostic members remain useful external checks, without deciding the coefficients.

The signed-tensor question has a current instance: of 15 active CU cells, 14 are positive and one is negative. The negative cell is S.Amdt.2239 in the 119th Congress; the baseline routing admits Josh Hawley's sponsorship with direction −1 and a crypto-primary beneficiary classification. Its negative cell makes the current multiplier .5. This establishes active attenuation of an adverse act, not a measured rank impact of a replacement formula. The +.60/−.20 matched pair above is a hypothetical illustration. The [cell census and frozen-input join](math_repair_tensor_census.json) bind this observation to the accepted grade's source hashes.

The affirmative eligibility rule is the one additional methodology choice implemented from this table, following Paul's instruction. The other proposals remain unadopted. The implementation and verification receipt separately state what actually shipped.

The [proposed validation contract](PROSPECTIVE_VALIDATION.md) separates algebraic correctness, construct validity and future predictive usefulness. It also explains why ACU recognition is partially dependent corroboration: some ACU policy positions already enter upstream scoring.
