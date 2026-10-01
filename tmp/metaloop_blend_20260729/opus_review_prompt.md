# Independent Opus review: Moneyball primacy/orientation/influence blend

You are the independent read-only reviewer in Meta LOOP run
`run-20260729T1901383987513Z-e701e02ddb`.

## Objective

Reconcile whether the production allocation engine's general-priority term
should remain discrete primacy tier only or become a principled blend that
captures:

1. demonstrated credit-union beneficiary primacy and conduct accountability;
2. how a member broadly and issue-specifically feels about credit unions;
3. practical legislative/network influence.

The user explicitly wants an improved production design, not a rhetorical
answer. Challenge the existing approach and recommend an exact implementable
policy only if it survives the checks below.

## Current state to inspect

Read these local files directly:

- `fec/moneyball_core.py`
- `fec/tier_util.py`
- `fec/flip_model.py`
- `fec/per_topic_flip.py`
- `fec/per_topic_coalition.py`
- `fec/budget_frontier.py`
- `fec/money_response.py`
- `fec/surfaces/build_dashboard_bundle.py`
- `fec/surfaces/make_member_desk.py`
- `fec/optimize.py`
- `fec/stance/per_category_stance.py`
- `category_stance.json`
- `ranks_python.json`
- `primacy_factors.json`
- `dashboard_data.json`
- `optimize_result.json`
- `tier_overrides.json`
- `fec/verify_greenlit_primacy_integration.py`

The current general-priority policy is:

`T1=1, T2=2/3, T3=1/3, untiered=0`

and the flip target is approximately:

`(direct_issue_engagement + 0.15 * tier_priority)
 * issue_persuadability * bridge * delivery`.

Official reporting ranks are unchanged. The question is whether tier alone is
too coarse because it does not capture a member's overall CU orientation.

## Required analysis

1. Identify what each existing term actually measures and where sentiment,
   action, influence, and movability are already represented.
2. Detect double-counting risks. In particular, do not count issue stance
   twice merely by adding an orientation prior to a term already multiplied by
   issue persuadability.
3. Determine whether one blend can serve both:
   - persuasion/flip targeting; and
   - coalition/frontier seed selection.
   Prefer mode-aware formulas if the objectives differ.
4. Do not average ordinal rank numbers. If influence belongs in the engine,
   specify the normalized underlying input and why it is not a sentiment proxy.
5. Preserve direct issue evidence so an untiered member with strong relevant
   evidence is not mechanically erased.
6. Specify exact weights/scales, normalization, missing-data behavior, and
   conduct handling. Avoid arbitrary precision.
7. State falsifiable acceptance tests:
   allocation turnover, rank invariance, stance monotonicity, Tier-1 behavior,
   opponent/ally leakage, mode differentiation, and Python/JavaScript parity.
8. Recommend either:
   - keep tier-only;
   - tier + orientation;
   - tier + orientation + influence; or
   - a better alternative.
9. Audit legislative participation strength separately from beneficiary
   direction. Production currently assigns role mass of `sponsor=1.00`,
   `original cosponsor=0.50`, and `later cosponsor=0.25`. Letters have a
   ratified authorship rule of `documented joint lead=1.00` and `ordinary
   signatory=0.50`. Determine whether these relative weights are coherent,
   whether the code actually preserves that distinction, and whether any
   change is warranted. Do not silently treat letter signers as bill
   cosponsors.

## Constraints

- Read-only. Do not edit any file.
- Local evidence only; no browser, web search, or external source collection.
- Do not call another model or API.
- Treat CFPB direction as already ratified: restraining CFPB is positive and
  expanding CFPB reach is negative.
- No fixed member placements.
- Return a concise but technically complete JSON object with keys:
  `verdict`, `measurement_map`, `recommended_policy`, `exact_formulas`,
  `normalization`, `double_counting_controls`, `failure_modes`,
  `acceptance_tests`, and `implementation_notes`.
