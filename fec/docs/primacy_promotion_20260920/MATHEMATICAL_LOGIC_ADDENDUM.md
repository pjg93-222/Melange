# Mathematical logic review — September 20, 2026

Historical pre-repair findings follow. The boundary repairs subsequently shipped in `78dc3ea8a`; see [MATHEMATICAL_REPAIRS.md](MATHEMATICAL_REPAIRS.md) for their verification and [LOGIC_AND_RATIONALE.md](LOGIC_AND_RATIONALE.md) for the modeling questions that remain open.

Paul clarified that he is happy with the current rankings and wants the mathematical logic examined. The current published board is the accepted regression baseline. Individual placements and agreement with ACU are not optimization targets for this review. No production code, weights, classifications or rankings changed.

This addendum supersedes the *priority* of further member grading, not the historical evidence recorded in earlier reports. It checks algebra, boundary behavior and the distinction between implementation defects and modeling choices. It makes no new statistical-validity claim.

## Results that are sound

The active shrinkage is a convex combination of the member's observed factor and the roster baseline. At fixed evidence mass and baseline, increasing the observed factor cannot lower the result. It stays between the observed factor and baseline. The previously removed uncertainty dock violated the first property; the adopted K=0 method repairs it.

The current board score is `P * (.8 + .2G)`, where G is the grade percentile. For P >= 0, the score increases with either P or G. The modifier ranges from .8 to 1, so grade can raise a positive score by at most 25% relative to its grade-zero value. All 533 current P values are positive (minimum .177189, maximum .762939). Their grade percentiles are within [0,1], and every member has dated service information. These facts establish present-domain consistency, not correctness for every possible future input.

The media ratio uses nonnegative intensity weights and bounded signed relevance, so its unrounded value lies in [-1,1]. Multiplying every admitted intensity by the same positive constant cancels in that ratio. Changing the relative units of different channels does not cancel. The production loader also rounds numerator and denominator before division, so exact numerical scale invariance is only approximate after rounding; the fixed corpus and its hash bind the current calculation.

Policy-area weights total 17.45 rather than 1. This is not a bug: the common positive total cancels at the later grade-percentile step. Press is repeated inside the weighted-area sum, but its effective grade blend remains 20% after normalizing by that common total. Repeated percentile transformations mean this is not a promise that press controls exactly 4% of the final score or that grade can move at most 20% of ranks. Percentiles preserve relative ordering, not distances or causal attribution percentages.

## Definite implementation problems at the boundaries

**Constraints do not compose.** Evidence and conduct restrictions are currently applied in successive seating passes. The second pass can seat someone prohibited by the first. The production function reproduces a three-member counterexample in the receipt. Also, if too few members qualify, the helper appends the remaining candidates and its caller assigns tiers by index, silently violating the intended floor.

**Recommended first repair:** form each member's required minimum slot from the maximum of all applicable constraints, then seat once. If fixed slots cannot be filled, report infeasibility rather than manufacturing qualification. A scratch implementation passed feasible/infeasible toy cases and reproduced **all 533 current ranks with zero movers**, with all current floors respected. It is not integrated or shipped; broader implementation tests remain necessary before promotion.

**Negative-factor behavior is undefined in the intended sense.** At P=-.5, improving G from 0 to 1 changes score from -.4 to -.5. Thus a better grade becomes a penalty. This is latent on the current positive-factor roster. The score should either explicitly guard its supported domain or receive a separately specified signed-domain extension. Clipping genuine opposition to zero would change its meaning and is not assumed to be a repair.

**Missing tenure receives the shortest denominator.** The .5-year fallback can inflate an annualized rate when service dates are absent. This is inactive for all 533 current members. Unknown tenure should be distinguishable from a known short tenure; a publication guard can catch it without changing the current board.

## Modeling choices that need an explicit contract

| Question | Verified behavior | Mathematical decision needed |
|---|---|---|
| Direction and intensity | The legislative multiplier uses a signed CU cell inside `1 + .5*cell`, in addition to the act's direction. Matched sponsor fixtures give +.6 versus -.2. | Is a 3:1 support/opposition asymmetry intentional? If equal magnitudes are intended, the present rule fails that property. The question is pending with Paul; no alternative is assumed. |
| Insufficient media | Fewer than five occurrences becomes numeric zero before percentile ranking. A negative record can improve when hidden below the threshold; the synthetic example moves from bottom to top of a two-member chamber. | Distinguish absence, insufficient observation, observed neutrality and observed opposition. A hard threshold is a legitimate policy only if this discontinuity is intended. Current below-threshold count: 243 members. |
| Evidence depth | Shrinkage pulls thin records toward the average; annualized legislative activity also enters grade. | Depth already affects confidence and performance through separate paths. Decide the role of each rather than calling all volume effects confidence. More repetitions need not increase a below-average estimate. |
| Units across components | Factor uses amendment half-mass and sponsor/original/cosponsor weights 1/.5/.25; grade uses .4/.25/.15 and no amendment adjustment. | Different estimands can legitimately use different units, but an asserted universal half-amendment rule must be reconciled with grade. Relative role weights are not merely a common rescaling. |
| Relative versus absolute merit | Within-chamber percentiles and first-tie ranking can give zero activity a positive relative position when others have negative scores. | A percentile is standing among peers, not proof of positive advocacy, an absolute quantity, or a probability. Retain evidence-presence information alongside it. |
| Qualification meaning | The CU-primary credit floor counts relevant role mass without requiring positive direction; letters occupy a separate mix category. | Decide whether the floor means relevant evidence, supportive legislative action, or all direct advocacy. The arithmetic must follow that stated definition. |

## Recommended sequence

1. Use the accepted current board as the regression baseline. Harden joint constraints and missing/domain handling first; verify zero current movement for each repair.
2. Ratify the direction-symmetry and missing-evidence contracts. Then test targeted counterexamples before any alternative weighting comparison.
3. Review units and normalization as distinct mathematical choices. Any later candidate must explain its changed behavior across the roster; matching favorite placements is not evidence that its equations are sound.

Evidence: [mathematical_logic_receipt.json](mathematical_logic_receipt.json). The scratch script is `tmp/primacy_promotion_20260920/mathematical_logic_check.py`; it reads live artifacts and executes AST-extracted pure production functions for the counterexamples, plus the read-only tier loader for the seating comparison. The five published-authority/surface hashes were identical before and after. Source functions are in `fec/engine/primacy_factors.py`, `fec/engine/per_area_grade.py`, `fec/engine/primacy_press.py` and `fec/tier_util.py`. Earlier frozen findings remain in the original mathematical audit; the removed dock and old off-topic grade-credit issue must not be reported as still active defects.
