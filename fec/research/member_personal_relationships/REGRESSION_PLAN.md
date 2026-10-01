# Multivariable relationship regression: declared analysis plan

This is an exploratory analysis declared before fitting this version, not an independent preregistration. Existing labels and earlier model results have already been inspected.

Use the frozen `20260910_full_history` inputs. Keep all available 116th–119th Congress HR/S cosponsorship history, without a 30-day limit. Do not change production profiles or the existing network.

The outcome is positive versus negative **among manually reviewed, documented ties**. Include explicit personal friendship statements and the existing person-directed antagonism labels. Exclude contextual warmth, unknown pairs, and rule-inferred affinity from primary labels. Group every direction and episode of an unordered pair. Each pair has total training weight one. Do not infer reciprocal declarations.

Fit ridge logistic regression with training-only weighted mean imputation and standardization, and explicit missingness indicators. Choose the penalty from 0.03, 0.1, 0.3, 1, 3 using inner-fold log loss. Compare a prevalence baseline, context controls, context plus work, work plus E/A/O similarity, work plus individual E/A levels, the combined model, and the combined model plus C/N similarity. Report every model, not just the best result.

Context controls: same party, same state, same chamber, absolute DW-NOMINATE dimension-one distance, issue similarity, actor and target party leadership, and shared service Congresses. Their coefficients adjust comparisons; they are not negative friendship scores. Work: forward/reverse direct cosponsorship propensity, weighted shared-cosponsor Jaccard, log(1 + shared bills), and network-profile cosine proximity. Personality compatibility: exp(-absolute trait difference), separately for each trait. Individual levels: actor and target E and A.

Outer validation: (1) hold out each pair and the transitive component of pairs sharing source families; (2) also remove every training pair containing either held-out member. Apply the same exclusion policy in inner penalty selection. Work-network features use no relationship labels and are fixed, transductive descriptions of the observed legislative network. Member holdout excludes members' relationship labels, not their work or trait measurements.

Report pair-level AUC, accuracy, balanced accuracy, log loss, Brier score and confusion counts. Average predictions across documented directions before scoring a pair. Give coefficients and odds ratios per training standard deviation, with 500 source-component bootstrap stability resamples at the final selected penalty. These are descriptive stability intervals, not valid dyadic confidence intervals or causal effects.

Sensitivity analyses: add public visibility and text-volume controls; remove A; use text-only and observer-only profiles, plus floor-only and interview-only observer scores; use unordered endpoint-averaged features; leave influential members out; exclude strategic/secondhand negative anchors; include weak warmth labels only as a separately labeled sensitivity. Genre ablations do not certify source independence. Do not feed the labeling statements or unpurged target-specific rhetoric back into the predictor.

Audit label/source balance, overlap of members, sample-versus-roster coverage, trait missingness, feature correlations, weak external trait validity, and future information in retrospective features. Do not call scores calibrated population friendship probabilities, interpret absence of cooperation as dislike, or infer actual sincerity from personality. Do not report ordinary independent-row p-values.
