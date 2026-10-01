# Original cosponsorship and specific personality hypotheses

This is a development analysis requested after the earlier results were seen. The 29 existing documented dyads, all earlier predictions, and the v5 frozen test remain unchanged. No new test labels or test-member narrative sources enter this analysis. This specification is saved before fitting.

## Work measurement

Use the explicit source original-cosponsor flag. Retain distinct H.R./S. bill IDs from Congresses 116–119 in the existing September 10 snapshot, including bills with no original cosponsors. Do not infer originality from a short elapsed-time window. Verify the flag against the preserved GPO XML archives, because the old extraction parser maps an absent flag to false.

For bill b, O_ib is one only when i is a recorded original cosponsor; E_ib is one when i served in that chamber on the introduction date and was not the sponsor. Original propensity toward sponsor j is sum_b O_ib I(sponsor_b=j) / sum_b E_ib I(sponsor_b=j). A later entrant has no original-cosponsorship opportunity on an earlier bill. A subsequent withdrawal does not erase participation at introduction; active original counts are additional descriptive fields. Preserve the existing exclusions for invalid dates/service, and disclose discrepancies.

Shared original work is sum_b O_ib O_jb. Let w_b=1/max(1, original coalition size minus 1), including former members in coalition size. Weighted overlap divides sum_b w_b O_ib O_jb by sum_b w_b(E_ib O_jb + E_jb O_ib - O_ib O_jb). Sponsor–cosponsor and shared third-party coalitions remain separate. Network proximity is cosine similarity between the original weighted-overlap rows, omitting the focal endpoints. Issue selectivity also uses original participation and introduction opportunities. Bipartisanship uses original direct propensities, excluding the focal partner from numerator and denominator, with the existing half-count smoothing and missingness rules. Geography, ideology, party, leadership, service and visibility remain estimated controls; no predetermined negative weights.

## Comparisons fixed before fitting

R0–R3 repeat the four preceding specifications with all work-derived inputs replaced consistently. The completed all-cosponsor fits are the comparator, rather than a new fit tuned to these results. The same 29 dyads, directions, member/source exclusions, nested penalty grid and 0.5 classification threshold are used.

R4 permits separate E, A and O similarity × ideological-distance coefficients, instead of forcing the three trait interactions to share one coefficient. R5 adds joint low agreeableness, defined as sigmoid(-A_i) sigmoid(-A_j), and its ideological-distance interaction. R6 adds joint high extraversion, sigmoid(E_i) sigmoid(E_j), and its distance interaction. Each includes its lower-order main effect; endpoint E/A levels and ideology already belong to the base. R5/R6 are behavioral-disposition hypotheses, not claims that E measures dominance or A measures sincerity. C/N remain descriptive in the source-linked case profiles, not newly selected predictor terms after inspecting outcomes.

Report every specification, log loss, Brier score, accuracy, both class recalls, and same-fit positive–negative ranking. Repeat without the motivating Mace/Crockett dyad. Source-component resampling at the selected penalty describes coefficient stability; it does not establish population confidence or causality. Do not promote the best development model to the frozen test.

## Personal exchanges and competitive context

Create a separate, source-linked event coding table with trait profiles and original work measures. Code observable antecedents (procedural disagreement, policy/accountability challenge, direct personal disrespect, personal support), institutional roles, person-directed content, reply direction, persistence after a boundary, reciprocity and repair. Do not infer competition or leadership allegiance merely from party membership. Include personal warmth and ritual/ambiguous controls, not just confrontations.

The episode that establishes a relationship sign cannot also serve as an independent predictor for that sign. Event coding is initially a descriptive mechanism audit. Only separately sourced or earlier exposure-adjusted behavior may later enter a predictive model. Missing roles, exposure, reciprocity and repair remain missing. A fight establishes public personal escalation; a friendly exchange is evaluated on its content. Neither alone reveals an enduring private emotional state.

## Verification

Check explicit-flag handling, introduction-time eligibility, sponsor exclusion, withdrawals, coalition weighting, zero-opportunity missingness, and complete replacement of work features. Reconcile new shared-original counts with the preserved original_shared matrix where source eligibility agrees. Verify all old/frozen input hashes after execution and retain a new output directory and receipt.
