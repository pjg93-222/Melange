# Institutional evidence: continuing-member development comparison

This separate experiment follows the user's instruction to test caucus membership, committee opportunities and issue-specific voting. It preserves all earlier code, data, forecasts and manifests. No production promotion or outreach is part of this run.

## Population and time

Keep the exact 377-member cohort in `outputs/cosponsor_universe_20260905/gold_cohort.json`. Use the original financial-bill risk sets, row ordering, serving-member exclusions, first-cosponsorship labels and 30-day horizons. Forecast bill ages remain 0, 35, 70, 105, 140 and 175 days. Train on mature Congress 117 rows using the identical deterministic negative sample and weights; calibrate and select on 2023; freeze every prediction and the selected model before calculating new 2024 performance.

Congress 118 has already been examined. Both years are development, and adjustment for these comparisons does not repair earlier model-search optimism, survivorship conditioning or residual member dependence. Congress 119 outcomes are excluded. Existing September 5 prospective predictions are not revised or represented as predictions of these new models.

The inherited split assigns rows by forecast date, not by the end of the 30-day outcome window. Late-December 2023 calibration forecasts can use outcomes in January 2024. Thus the selected/calibrated model is not claimed to have been operationally available on January 1, 2024. The later-date comparison preserves the existing development benchmark; it is not a purged temporal holdout.

## Evidence admission

Builders write float32 arrays aligned to every original metadata row, plus source hashes, normalized evidence and timing/identity checks. The cohort mask is applied only when fitting or scoring.

- Caucus membership is documented positive membership from dated announcements, distinct from prior-Congress officer roles. Partial rosters and unresolved names remain unknown. Current 2026 officer compilations are audit material only. Membership source coverage and leadership-only ablations distinguish the available caucus evidence. A name in an old announcement is not proof of continuous membership. Peer features use only strictly earlier signatures.
- Committee snapshots must precede the forecast. Past referrals, hearings and meetings remain distinct from actual attendance. Do not interpret hearing-member metadata as presence or speech. Malformed records and ambiguous cancellations are excluded. Warehouse update dates are not automatically original publication dates. Any event-dated hearing reconstruction with unverified operational availability is explicitly separated as a sensitivity feature group.
- Votes are raw dated member decisions, not fitted Voteview probabilities or whole-Congress ideology estimates. Distinguish substantive, procedural and amendment questions; procedural Yea is not called policy endorsement. Handle paired/announced, present and not-voting categories separately. Match stable member identities, Congress, chamber and roll number. All events must precede the forecast, including same-bill votes.

Final feature groups and source-admission decisions are frozen in the model plan before fitting; they are decided from evidence quality without consulting new forecast results.

## Models and comparisons

The new backbone combines the earlier public-coverage, cosponsorship-network and recent-signing-activity features. Fit the backbone; each new block separately; all three pairwise block combinations; all three blocks; logistic backbone and logistic all-blocks; and the earlier 197-feature universe plus the three primary blocks. Add a leadership-only caucus ablation when a membership block exists. If a separate hearing event-reconstruction block exists, add it to the primary all-blocks model as one sensitivity challenger.

Use the earlier fixed tree settings: 200 iterations, 15 leaves, learning rate 0.06, L2 10, minimum leaf 50, no early stopping and seed 20260905. Logistic regression uses the previous weighted scaler, C=1, Newton–Cholesky solver, tolerance 1e-7 and maximum 150 iterations. Fit monotone Platt calibration on 2023 only. Do not tune settings on 2024.

Reuse immutable, previously verified cohort-model forecasts for four references: activity trees, network trees, context trees and universe trees. These were trained on the same cohort, rows, weights and time split. Copies are hash-checked against the sealed generation; they are not full-population predictions relabeled as cohort refits. Every primary new model and all four references may win 2023 selection. A source-availability sensitivity model is displayed but cannot win primary selection.

Prespecify all new-versus-reference and new-versus-backbone contrasts, the three all-blocks versus leave-one-block-out contrasts, matched-feature tree-versus-logistic contrasts, and caucus leadership/full-evidence and hearing-sensitivity contrasts where available. Freeze the exact list and count in the plan. Report all results.

## Assessment

Primary endpoint: correct predictions divided by identical forced top-eight slots per bill-date. Resample whole legislative families 100,000 times, preserving their member rows and dates; report ordinary 95% and Bonferroni-adjusted intervals across the entire declared comparison family. Brier is a separately adjusted secondary endpoint. These are descriptive development intervals, not independent confirmatory p-values.

Also report average precision, probability calibration, chamber/party strata, matched retained counts 250/500/1,000/2,000/5,000, and unchanged 2023-derived probability cutoffs. Higher precision at narrower coverage must include counts and recall. Do not select a new winner from 2024 or infer causal influence from observed affiliations.

Independent review must check sources, temporal boundaries, original row indices, sampled predictions, metric recounts and final claims. Freeze a final manifest and exact code archive after verification and report review.
