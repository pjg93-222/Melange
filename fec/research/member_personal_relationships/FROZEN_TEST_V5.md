# Frozen relationship test, version 5

This is a prospective freeze of the next analysis rules and sample, after inspecting the earlier 29-pair results. It is not an independent preregistration or a claim that existing measurements were collected prospectively. No outcomes from the new held-out sample may be used to change these rules.

## User decisions

Ideological similarity can contribute to compatibility. Shared geography, party, interests and leadership incentives are context to adjust for; none receives a predetermined negative friendship weight. Same-party objections to leadership challenges may explain antagonism. Record a challenger's action and the other member's leadership alignment separately, with dated sources; do not infer either from an insult. A dispute can have both a political explanation and a personal component.

Keep current personality measurements if they satisfy their existing activation rules. Recheck the published numerical gates without changing their thresholds or calling that a new external validation. Retain the distinction between one-panel association support and two-panel discriminant support. Retain missing measurements as missing. Trait validation does not establish independence from the relationship-labeling corpus.

Personal warmth and hostility relative to the speaker's usual behavior belong in the personality interpretation. Their interaction weights are learned in development data, not imposed as sincerity multipliers.

## Sample and allocation (fixed before drawing)

Seed: 20260910. Frame: the frozen 532-member relationship roster. Split 25% of previously unlabeled members within coverage-bucket × chamber × party cells into a held-out member pool using a reproducible seeded random draw. Every member in any previously reviewed relationship or hearing pilot stays in development, including weak and rejected cases. Never move members in response to new labels. Pairs crossing the split are outside this test's frame.

Coverage is the existing interview-word count, divided at the one-third and two-thirds quantiles separately within each chamber. Missing interview coverage is explicitly `unrecorded`; it enters the low-coverage sampling bucket to ensure review attention, never as a low personality value. Tied word counts stay together. These are coverage strata, not classifications of private sociability.

Draw 180 new development pairs and 120 held-out pairs without replacement. Pair coverage buckets LL, LM, LH, MM, MH, HH receive shares 30%, 25%, 15%, 10%, 10%, 10%, respectively. This allocates exactly 50% of sampled endpoint slots to the low/unrecorded coverage bucket. Within each bucket, balance same/different party × House/House, House/Senate, Senate/Senate cells, respecting available capacity. If a requested bucket lacks enough eligible pairs, fail rather than silently change the design. Same-state and ideology-distance distributions are reported, not used to reject selected pairs.

For a sampled pair in cell h, the conditional inclusion probability is n_h/N_h and the design weight is N_h/n_h. These weights describe the eligible, split-specific pair frame conditional on the member split, NOT every congressional pair. Report unweighted, coverage-balanced and design-weighted results separately. No weighting can reconstruct unobserved relationships or correct unmeasured annotation nonresponse. Do not assign design weights to old anchors or the separate cue-enriched development arm.

Also create a development-only discovery queue of at most 24 new pairs with existing warmth/hostility retrieval cues, balanced 8/8/8 by the lower endpoint's coverage bucket. Exclude known reviewed pairs, old source families and all held-out members. Selection is explicitly evidence-enriched and cannot estimate prevalence. This queue develops annotation feasibility; it is not the frozen probability sample or the test set.

## Evidence and annotation

Preserve two directed evidence dimensions, affinity and personal antagonism. Both can be supported for one pair. Unknown, ambiguous and no-found-evidence remain distinct from explicit counterevidence. A procedural disagreement, ideological opposition, leadership challenge, low cooperation or personality difference alone never establishes personal dislike.

Record original text/video/transcript locator, date, author, target, source family, root episode, target verification, quotation status, promptedness, ritual versus substantive wording, personal act, escalation, reciprocity, repair, and political/leadership explanation. Apply the existing hearing escalation protocol. Repeated clips and retellings count as one root episode. Reciprocity requires separately attributed evidence in both directions. Include routine named-member interactions to measure each speaker's baseline; keyword hits alone are not the denominator.

The first collection pass uses the same frozen local corpus search for every probability-sampled pair. Report zero-result searches and ambiguity. No replacement for a pair that yields no usable evidence. Additional acquisition must follow a declared common search effort for each coverage stratum and remain versioned. Never label unsearched, unmatched, or silent pairs as hostile.

Reviews must be completed without model scores or personality values. The initial assistant review is identified as such; do not claim independent human coding or inter-rater reliability. Source review and adjudication can add evidence, but cannot change the sample or frozen feature families. Held-out evidence stays outside development review packets.

## Speaker-relative expression

Unit: one reviewed directed target interaction per root episode and venue. Deduplicate repeats; preserve authored substantive warmth/hostility separately from ritual, quoted, ambiguous or procedural content. Remove every labeling episode and its retellings from expression predictors, including the focal episode from other-target baselines. For a dated prediction, additionally exclude material at or after that date.

For speaker i, target j and venue v, let n be reviewed target episodes and w be episodes with substantive warmth. Let n_o,w_o be the corresponding reviewed episodes involving other targets. With n>0 and n_o>0, set p_o=(w_o+0.5)/(n_o+1), p_ij=(w+5 p_o)/(n+5), and d_ij=logit(p_ij)-logit(p_o). The fixed strength 5 shrinks sparse target counts toward the speaker's own baseline. If either denominator is absent, the contrast is unavailable. Report denominators and shrinkage n/(n+5). Compute hostility contrasts analogously.

Keep d, d×E_i and d×A_i as separate features with learned signs. Reciprocal warmth uses min(max(d_ij,0),max(d_ji,0)) only when both directions are observed in the same venue. Do not copy a direction or turn any of these quantities into a sincerity probability. The current raw cue statistics are retrieval diagnostics; they are never substituted for reviewed expression counts.

For a single model row, average each available contrast/interaction equally across venues; preserve the number of contributing venues and the episode counts in the audit. If no venue has the required target and other-target observations, that feature stays missing. More heavily televised venues do not receive an automatic larger weight.

## Frozen models and evaluation

M0: measured context + direct and reverse cosponsorship propensity + weighted shared Jaccard + log shared bills. Context includes endpoint DW1/DW2, exp(-absolute DW1 difference), same party/state/chamber, issue similarity, common service, endpoint leadership, measured leadership tension and endpoint interview coverage. Missing leadership-challenge evidence remains missing; it is not an assumed zero. Historical committee/caucus and geography detail remain incomplete and must be disclosed.

M1: M0 + endpoint E/A levels. M2: M1 + reviewed speaker-relative warmth/hostility, warmth×E, warmth×A, hostility×A and observed reciprocal warmth. M3: M1 + E/A/O similarities. M4: M1 + network proximity. All five trait profiles are retained; C/N retain their weaker validation status and do not generate additional post-hoc primary model searches.

Primary comparisons: M1 versus M0, M2 versus M1, M3 versus M1, M4 versus M1. No best-test-model selection. Ridge logistic penalties are 0.03, 0.1, 0.3, 1, 3, selected by development-only member/source-grouped inner log loss. Fit preprocessing on training data only. The existing 29 labels are development information, not another validation set.

For comparability, the signed-tie benchmark classifies affinity-supported versus antagonism-supported pairs conditional on one unambiguous documented sign. Mixed or unknown relationships are reported separately, never silently assigned to a class. This benchmark does not estimate link existence or the probability of private friendship. The graph retains both directed evidence dimensions regardless of benchmark eligibility.

Hold all sampled test members out of development labels. Hold entire root episodes and connected source families out, including cross-pair retellings. Labelers' relationship excerpts must not also be expression predictors. Existing aggregate personality has unresolved source overlap: it remains eligible for the explicitly retrospective measurement track, but independent-personality-gain claims require traceable exclusion of evaluation evidence or an independently measured trait source.

Before opening test results: finish the declared review pass, freeze development models and predictions, and record source exclusions. A descriptive signed-tie run requires at least 20 development examples of each sign and 10 test examples of each sign. These are minimum reporting floors, not power calculations. If unmet, report insufficient labeled evidence without replacing the sample or weakening thresholds. Never treat the 300 sampled pairs as 300 labeled ties.

Report all prespecified comparisons: log loss (primary), Brier, same-fit held-out AUC, balanced accuracy, confusion counts and both class recalls at 0.5; counts and missingness for every coverage, party and chamber subgroup; label yield and both evidence dimensions in the full reviewed sample. Design-weighted sign metrics remain conditional on successfully labeled ties and do not cure annotation selection. Report member/source-cluster stability with its limitations. Do not claim calibrated population probabilities. New hypotheses after test inspection require a new test version.

## Freeze enforcement

Hash this plan, the executable sampling/expression code, frozen inputs, member assignment, sampling frame summary, drawn pair IDs and annotation schema. A rerun verifies the manifest and returns the existing draw. Refuse changed inputs or a modified plan rather than silently redrawing. Analysis artifacts, discovery reviews and software-test receipts are versioned separately from the locked sample. No production personality profile or graph is modified by this study preparation.
