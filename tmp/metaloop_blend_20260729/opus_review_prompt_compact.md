# Independent Opus review: bounded engine-policy reconciliation

You are the independent reviewer in Meta LOOP run
`run-20260729T1901383987513Z-e701e02ddb`. Two earlier execution packets
failed operationally before returning any answer. This packet is
self-contained: do not use tools or read files. Review the supplied production
facts and return the requested JSON in at most 900 words. Prioritize the exact
formula verdict, role weights, letter multiplier, and acceptance tests.

Facts already measured from production:

- Tiers are fixed-size 13/24/48 and are computed from legislative percentile
  times a shrunk beneficiary-primacy factor, followed by the conduct ladder.
- The beneficiary factor is a role-mass-weighted average of act direction and
  beneficiary class, then shrunk toward the roster baseline with
  `lambda=min(1, agenda_credit/15)`. Tier order uses
  `legislative_percentile * factor_shrunk`.
- General tier priority is T1=1, T2=2/3, T3=1/3, untiered=0.
- Flip target value is currently
  `(issue_engagement + 0.15*tier_priority) * issue_PERS *
  bridge * delivery`.
- Issue `PERS` is movability, not pro/anti direction. The issue label still
  controls whether a member is an ally, opponent, or neutral candidate.
  Network adjacency/cascade physics and bipartisan factors already model
  influence; a separate delivery multiplier discounts say-do gaps.
- `category_stance.json` supplies continuous per-category signed scores in
  [-1,1], with missing cells represented as zero. There are 18 categories.
- A fixed-importance weighted full-record orientation has production range
  -0.247..0.594, median 0.134. Missing evidence therefore remains centered at
  zero if the denominator includes all category importance.
- Candidate design from the Codex lane:
  `signed_orientation_loo(member, topic) =
  sum(IMP[c]*score[c] for c != topic) / sum(IMP[c] for c != topic)`;
  `flip_priority = clip(tier_priority + 0.15*orientation_loo,0,1)`;
  `coalition_priority =
  clip(tier_priority + 0.25*orientation_loo,0,1)`.
  For the synthetic overall layer, use all categories. This is centered:
  missing orientation changes nothing. Leave-one-topic-out prevents the
  current issue stance from entering both priority and PERS.
- Official rank and tier assignments would remain unchanged; only allocation
  engine priority would change.
- Bill/primacy role mass is sponsor=1.00, original cosponsor=0.50, later
  cosponsor=0.25. The production bundle contains 576/1,953/2,943 such
  non-letter rows. Letters encode 11 documented leads as sponsor and 276
  ordinary signers as original; there are no letter `cosponsor` rows.
- The ratified CU-tax letter has `letter_weight_override=1.0`, so leads receive
  1.00 evidence mass and signers 0.50. Other letters retain the default 0.60
  instrument multiplier.

Audit the candidate against:

1. construct separation: demonstrated primacy, holistic orientation,
   issue-specific movability, influence, and delivery;
2. double counting and missing-data behavior;
3. whether persuasion and coalition should use different orientation strength;
4. whether influence should be added again (do not use ordinal ranks);
5. whether role weights 1/.5/.25 and letter lead/signatory encoding are
   coherent;
6. whether the default 0.60 letter multiplier creates a separate unresolved
   issue from role strength;
7. falsifiable acceptance tests and any exact formula adjustment.

CFPB direction is ratified: restraining CFPB is positive, expanding CFPB reach
is negative. No fixed member placements. Do not call tools, browse, or call
another model.

Return only one concise JSON object with keys:
`verdict`, `candidate_assessment`, `recommended_formulas`,
`role_weight_assessment`, `letter_assessment`,
`double_counting_controls`, `acceptance_tests`, and `implementation_notes`.
