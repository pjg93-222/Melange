# Four-priority legislative candidate

The current user direction is **Primacy → Efficiency → Substance → Volume**. No fifth criterion is added. Institutional power is excluded from tier scoring. Role attribution and earlier participation are included in credited legislative activity.

This package supersedes the earlier P/E/V candidate's scoring proposal. Existing historical reports and completed generations are retained. The earlier 180-day conversion-rate metric is not used here: the 180-day parameter in this package is a cosponsorship-credit half-life, not an observation horizon.

## Metrics

Let `u_ib` be the accepted signed tensor CU relevance × direction for member i on measure b; `w_b` the recorded impact class (1, 5, or 10); and `r_ib` the role credit (sponsor 1, original cosponsor 0.5, later cosponsor 0.25). No confidence multiplier is added. Duplicate category selections cannot multiply one member's credit for a measure.

For later cosponsors, `t_ib = 2^(-d_ib / H)`, where d is days from introduction to first verified joining. Sponsor and original-cosponsor timing credit is 1. H defaults to the source's illustrative 180 days and remains a candidate setting. Withdrawal closes participation; rejoining does not reset the clock. Joining must be verified against service history. An active official sponsorship can receive later milestone credit without an additional service-exit discount, consistent with the source attribution rule.

1. **P: Primacy.** The authoritative published `factor_ranked`, with its existing meaning and precision.
2. **E: Progressive efficiency.** For each of BILL, AIC, ABC, PASS and LAW, sum `u_ib × r_ib × t_ib × w_b` over measures whose milestone occurred while the member's role was active. Divide each stage numerator by the sum of positive impact weights of **all eligible chamber measures** reaching that stage, then multiply the five-stage sum by `N_chamber / 5`. There are no additional stage multipliers. This is relative realized legislative output, not a success probability, time-to-passage measure, or per-attempt conversion rate.
3. **S: Substance.** Set `a_ib = max(u_ib, 0) × r_ib × t_ib` for each distinct beneficial law-capable engagement. Substance is `sum(a_ib × w_b) / sum(a_ib)`. It measures average recorded importance, so accumulating identical measures does not raise it. No beneficial portfolio means the mean is unavailable.
4. **V: Volume.** `sum(a_ib)` once per distinct beneficial law-capable member–measure engagement. No impact weight enters V. The unweighted distinct beneficial count and harmful, neutral and unknown counts are separately visible.

E, S and V are converted to percentiles among observed members in the same historical chamber: share strictly below divided by `n−1`, truncated to five decimals, with tied values sharing their first rank. The historical populations include replacements. Congresses are compared separately; current primacy is held fixed in these retrospective replays.

## Ordering and constraints

Use exact P descending, then E percentile descending, then S percentile descending, then V percentile descending. At a tie, known evidence precedes unavailable evidence. Once a member's dimension is unavailable, lower dimensions cannot improve that member's position; Bioguide resolves remaining ties. No weighted blend allows a lower priority to compensate for a higher one. Display rounding never creates scoring ties.

Preserve the baseline eligibility, CU-primary evidence floor 0.75, override rules, conduct ladder and seat counts 13/24/48. These constraints follow the analytical ordering. No committee, leadership, seniority, majority-status or institutional-power term enters tier scoring. Office possession alone earns no milestone.

## Evidence and chronology

- All source bill and impact rows remain available to the denominator calculation. Accepted CU selection restricts member numerators, never the chamber universe.
- The five documented 119th House reserved-number placeholders (H.R.2, 3, 5, 8 and 10) are excluded only when their exact title is `Reserved for the Speaker.`, actions are an empty list, and no accepted scoring evidence refers to them. The derived exclusions are listed in every generation; original source records are untouched.
- Official hearings before formal introduction remain in chamber activity when the source records them as reached milestones. They cannot earn retroactive member credit before joining. The record, dates and supporting action text are retained in the coverage receipt.
- Official Congress identity controls date-only records on the Congress's final January 3. The term ends at noon, so an introduction dated that day cannot be rejected solely by a midnight cutoff. Closing-day cases are diagnosed explicitly. Congress.gov confirms the example [118th H.R.10564, introduced January 3, 2025](https://www.congress.gov/bill/118th-congress/house-bill/10564).
- Unknown or contradictory alignment, role, impact or milestone evidence remains unknown. Incomplete denominator evidence blocks E for that chamber; incomplete accepted member scope prevents a falsely favorable complete member score.
- Letters with unverified dated signatures remain coverage records. No bill stages or signatures are invented for them.

## Substance limitation

Selected measures currently all carry provisional weight 5. The weighted mean is therefore exactly 5 wherever observed and provides **no ranking distinction**. A percentile of zero for a uniform class means a tie, not poor substantive work. The previous total-impact advocacy measure varied with role and volume; it was not inert. This new *mean-substance* dimension intentionally removes that volume effect.

The source's substance classes and deduplicated CU/trade-publication frequency evidence remain the intended basis for future reviewed weights. Incomplete publication coverage cannot be treated as no attention, and no new significance threshold or weight-10 classification is fabricated here.

## Verification and scope

The runner snapshots the baseline, imports only copied baseline helpers under an isolated root, verifies the 533-member published board, and records hashes before and after scoring. Core tests use hand-derived examples; adapter tests cover input scope, chronology, publication gates and output safety. Separate repeat generations must produce byte-identical analytical artifacts.

This is an executable candidate comparison, not production deployment. Production consumer integration and a full live pipeline run are outside this replay's verification. Neither deterministic tests nor historical rank comparisons establish empirical optimality or individual causal impact.

Sources: [original implementation plan](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/research/LEGISLATIVE_IMPACT_EFFECTIVENESS_IMPLEMENTATION_PLAN_2026-09-10.md>), [four-component source report](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/COMPOSITE_BOARDS_118.md>), and the user's corrections in this task.
