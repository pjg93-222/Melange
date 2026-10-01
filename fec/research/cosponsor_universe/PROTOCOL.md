# Whole-system evidence audit: continuing-member benchmark

The user requested a Melange-wide search for useful cosponsorship evidence, then directed: **“Just use the people that have stuck around as the gold.”** This revision implements that instruction as a fixed continuing-member cohort. Actual dated signatures are the outcome reference; membership does not establish gold-standard psychological traits or causal lobbying effects.

## Cohort and scope

Freeze the intersection of members appearing in the Congress117 and118 risk panels and still serving in the verified September5 official roster snapshot: **377 Bioguide IDs**. Use exactly these IDs for training, calibration, selection and assessment. Do not select members using labels, language coverage, future prediction success or model scores. The immutable cohort receipt binds its source rosters, member codes and dates. Conclusions are conditional on this continuing-member cohort; they do not generalize automatically to departed members or new entrants.

All forecast eligibility, bill identities, labels, dates and underlying feature arrays remain those of the earlier frozen panels. Keep their original row positions while applying cohort masks, so no memmap loses alignment. The target is a first cosponsorship in the next30 days for unsigned, serving, same-chamber nonsponsors; finance-at-introduction HR/S bills, forecast ages0/35/70/105/140/175 days. No Congress119 outcomes enter fitting or selection. Prior September5 issued forecasts remain byte-identical.

Inventory all80 declared stores and323 discovered data path families, distinguishing observations, scores, composites, simulations, media, operational artifacts and duplicates. Metadata counts are not independent observation counts. Secrets/browser profiles remain unopened. Raw audio/video are represented by existing transcript/measurement/source families; this audit does not claim every byte was semantically reviewed.

## Source interpretation

Historical text/media availability is strongly conditioned on the current roster. The continuing-member restriction implements the user's intended population and removes the departed-versus-current comparison from this benchmark; it does not establish complete historical collection or contemporaneous ingestion. Use only raw dated pre-cutoff language, public evidence and shared-broadcast observations. Current behavior-trained Big Five, receptivity, later cohort scalers and all-history composites remain excluded. Audio D-013 and failed latent-state/personality findings remain documented. Shared broadcasts are not verified personal interaction, and simulated influence probabilities are not observed treatment effects.

New reconstructed families:21 prior-Congress conduct features,8 earlier current activity features,6 corrected bill-stage features,8 election/history features,9 amendment-history features,24 observed language/exposure features and18 media-graph features. Prior cosponsor network, introduced-text similarity, dated census context and formal bill-attention context remain available. Later-source records filtered by event date are explicitly retrospective reconstruction, not historical ingestion-time replay. Retain source missingness flags and coverage caveats.

The old Passage-type feature was constant zero because raw actions use Floor and CRS codes. Corrected stage features use earlier bill-passage codes8000/17000, reporting5000/14000 and failure9000/18000, excluding same-day/future events and unrelated rule passage. Earlier artifacts are not overwritten.

## Fixed comparison

Refit **24 models** on the same continuing-member cohort. Eight controls: basic logistic, history logistic, dynamic logistic, weekly time-to-sign, dynamic trees, public-coverage trees, network trees and context trees. Sixteen challengers: dynamic base plus conduct, activity, stages, elections or amendments separately; public-coverage base plus observed language, language coverage, media or all new families; all new plus previous context with trees/logistic; the latter trees removing language/media; member-permuted language; and all reconstructed non-public context with trees/logistic.

No old whole-population prediction array serves as a refitted control. Train all learners on mature Congress117 rows from this cohort, retaining every positive and the same deterministic10% negative sample (weight10). The weekly model uses those same rows, expanding observed duration into7/7/7/7/2-day bins with exposure-weighted Poisson likelihood. Trees:15 leaves,200 iterations,learning rate.06,L2=10,minleaf50,no early stopping. All logistic models:C=1. Weekly model:alpha=1e-5, the prior selected value. Weighted scaling uses training rows only. No hyperparameter expansion based on later results.

Undefined numeric values become zero with explicit source-missing flags; no metadata identity/name is a predictor. The language placebo permutes the complete24-column vector only among the377 cohort members, within Congress/chamber blocks, preserving the two chamber-switchers' separate block and cohort marginal distributions. It is artificial and ineligible to win; it does not test or repair all source-selection bias.

Calibrate on2023 only. Freeze all24 prediction files and the best2023 precision-at-eight model among the23 non-placebo models before computing any new2024 metrics. Controls can win. Both years remain development because earlier work already used Congress118. Report all models, not only the winner.

## Evaluation

Primary comparator: refitted dynamic trees. Other matched-cohort controls are public-coverage, network and context trees. Compare16 challengers against these four controls (64 contrasts), six direct algorithm/feature/placebo contrasts, all eight refitted controls against dynamic trees (including the zero self-check), and history versus basic logistic: **79 contrasts**.

Primary endpoint: precision at8 within bill-date. Also report AP, Brier/calibration, event recall and chamber/party strata. Strata retain the original top-eight picks, without reselection. Resample whole legislative families with all their dates/member rows together using100,000 deterministic bootstrap draws. Show ordinary95% and Bonferroni percentile intervals across79 contrasts separately per endpoint (precision primary, Brier secondary). These are descriptive development intervals; extreme-tail Monte Carlo error, remaining member dependence, source incompleteness and historical model-selection optimism remain limitations.

Selective cutoffs are2023 top-eight score quantiles applied unchanged in2024. Every precision includes recommendations retained, hits, event recall, bills and members. Also compare fixed matched retained counts250/500/1000/2000/5000, labeled descriptive ranking budgets rather than issued probability policies. Do not present the tiny best subgroup as overall success.

## Review, provenance and revision history

Independent reviewers check source identities/dates, duplicate episodes/elections/amendments, cohort intersection, original-row alignment, exposure accounting, placebo distribution, metrics and artifact hashes. Code, input, cohort and protocol hashes are frozen before this run. Preserve earlier manifests and issued forecasts. Prepare a Brain update draft inside this output directory; do not change the external Brain or production models/dashboards.

The initial full-population attempt completed only conduct/activity2023 selection summaries; its third fit was interrupted when source-coverage bias was discovered. No new2024 assessment occurred. Exact artifacts/code are archived in pre_coverage_review. The subsequent design excluded text/media from challenger selection but was never fit; its code/protocol are archived in pre_gold_review. This user-directed cohort revision supersedes those designs and restarts all models, including controls.

No outreach, external publication, production deployment or scheduler is part of this research. Independent confirmation requires newly observed outcomes under immutable forecasts; the existing September5 window ends October5 and cannot be scored before October6.
