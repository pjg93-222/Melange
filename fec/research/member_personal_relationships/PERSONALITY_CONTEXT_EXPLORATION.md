# Personality, political separation, and bipartisan work: development exploration

Declared in response to the user's mirror-personality hypothesis, before fitting these new interactions. The original 29 relationships and earlier results have already been inspected. This is exploratory reanalysis of development data, not an independent accuracy test. The v5 held-out sample, plan and outcomes remain unchanged and unopened. This analysis does not alter its feature families or its test.

## Questions

1. Does E/A/O personality similarity have a less favorable association with a documented tie's sign as ideological distance grows?
2. Does willingness to cosponsor other-party members' bills weaken that interaction?
3. Does the pattern concern continuous ideology, different party affiliation, or both?
4. Are Mace and Crockett actually close in the measured traits, rather than simply on the same side of the mean? Do observed cross-party friendships contradict a blanket conflict rule?

Outcome y=1 is an existing documented positive tie, y=0 an existing documented personal-antagonism tie. Absence of a label never supplies a negative case. There are 29 dyads, 20 positive and 9 negative, from the original model. New exploratory source discoveries are not added. Each dyad has total training weight one across its documented directions. Friendship and antagonism in the evidence graph remain separate dimensions; this signed-tie benchmark is conditional on these selected cases.

## Features

S = mean of exp(-|trait_i-trait_j|) over E, A, O, requiring all three traits for both people. All-five and per-trait similarities are descriptive diagnostics, not additional primary model searches. Report endpoint trait levels and same-direction profiles separately: two people can both have above-average E yet differ greatly in its magnitude. E is not equated with dominance.

D = absolute DW-NOMINATE dimension-one distance, with each endpoint's DW1/DW2 and other original controls retained. P = 1 for different recorded party affiliation, 0 otherwise. Independent is a separate recorded party, not silently recoded as a Democrat. Personality/ideology associations are descriptive, not proof of causation or measurement bias.

For member i, remove focal partner j from BOTH bipartisan-work denominators and numerators. Among current-roster Democratic/Republican sponsors other than i and j, sum eligible sponsored bills N_same and N_cross and actual ever-joined signatures J_same and J_cross from the frozen full-history work panel. q_g=(J_g+0.5)/(N_g+1). B_i=q_cross/(q_same+q_cross). B_i is missing when either opportunity denominator is zero, no signatures are observed, or i is not recorded as a Democrat/Republican. B_ij=(B_i+B_j)/2 when both are observed. 0.5 means equal per-bill propensity across the two groups, not 50% of cosponsorships. The lower endpoint value, raw cross-party signature share, and actor/target propensities are descriptive checks only.

This operationalizes cross-party legislative cooperation, not personal tolerance, ideological moderation or friendship. It uses current party classification and current-roster sponsors, includes historical service opportunities and late joins, and does not cover former sponsors. It is retrospective, can reflect relationship effects, and does not establish that bipartisan behavior causes lower hostility. Same/cross party opportunity ratios and counts accompany every value. Missing independent-member values remain missing.

## Four prespecified comparisons

R0: previous expanded-controls + work + personality similarity/levels + visibility specification, plus B_ij. Its endpoint political controls include DW1, DW2, party and chamber indicators. Individual E/A levels and separate E/A/O similarities remain main effects, so the main effect of their mean S is already in their span. No duplicate S main-effect column is added.

R1: R0 + S*D.

R2: R1 + S*B + D*B + S*D*B. All lower-order terms are retained. The hypothesized signs in a friendship-positive model are beta_SD<0 and beta_SDB>0; both are tested rather than imposed. The relevant distance moderation of similarity is beta_SD + B*beta_SDB in raw feature units.

R3: R0 + S*P + S*B + P*B + S*P*B. P's main effect is already spanned by intercept and same_party. This tests party separation as an alternative to continuous ideological moderation. Do not put both highly correlated three-way structures into one model on 29 cases.

Use existing ridge logistic implementation, training-only imputation/scaling, and penalties [0.03,0.1,0.3,1,3] selected only in inner member/source-grouped validation. Outer folds exclude all labels involving either focal member and connected source families. Report all four models, not a selected winner. Compute same-fit positive/negative ranking AUC with both dyads and all their member/source connections held out together. Pooled fold AUC is secondary because fold prevalence varies.

Repeat all four member-holdout comparisons after excluding every case involving Mace or Crockett; do not change features or select the best variant from this sensitivity. It checks whether the motivating example alone drives the pattern. Examine Mace-Crockett held-out predictions from each fit but never fit or tune specifically to fix their classification.

Report log loss, Brier, accuracy, balanced accuracy, both sign recalls and same-fit AUC. Fit the final development models with internally selected penalties, and report raw interaction coefficients plus 300 source-component bootstrap stability resamples with fixed selected penalties. These are descriptive stability ranges, not valid independent-row confidence intervals or classical p-values. Report moderation at the observed development-pair 25th/75th percentiles of B. Mixed mechanism signs, degraded accuracy or unstable resamples count against the hypothesis.

## Interpretation and provenance

Preserve all observed cross-party friendships as positive cases with their full evidence weight. Cross-party work does not erase personal antagonism, and distance does not lower the evidentiary value of an explicit personal friendship. Warm language should eventually be evaluated using the separately implemented speaker-relative, source-separated expression measurement; raw 'my friend' cue counts do not enter this regression.

Personality retains its existing measurement gates, but source overlap with relationship episodes remains unresolved. Fixed work and personality measurements make the member-label holdout transductive and retrospective. Trait distribution descriptions can use the fixed roster; no v5 test outcomes or model selection based on that sample are permitted.

Research context: Tiedens & Fragale (2003), doi:10.1037/0022-3514.84.3.558, found more liking/comfort for complementary rather than matching dominant/submissive nonverbal behavior in two experiments. That concerns interaction behavior, not proof that similar Big Five profiles across ideology cause dislike. Santoro & Broockman (2022), doi:10.1126/sciadv.abn5515, experimentally found cross-party conversations about nonpolitical personal topics could reduce affective polarization, while conversations emphasizing partisan disagreement did not; effects had limits and decay. Neither supplies congressional regression coefficients or proves this proposed mechanism.
