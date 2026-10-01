# Cosponsorship challengers: frozen analysis plan

User authorized the data audit, prior-research review, construction, testing, and improvement on 2026-09-05. This plan is written before challenger outcome metrics are computed. All artifacts stay in the research output directory; no production model, ranking, workbook, or scheduler is changed.

## Question and population

Predict first recorded cosponsorship within the next **30 days**, conditional on being a serving, same-chamber, non-sponsor member who has not previously signed at the forecast date. A signature subsequently withdrawn still counts as a first-sign event. Original/day-zero cosponsors are already signed and never forecast as future joins.

Use HR and S bills referred at introduction to House Financial Services, Senate Banking, House Agriculture, or Senate Agriculture. Include zero-cosponsor bills. Do not select using eventual cosponsor counts or subsequently filed lobbying reports. Evaluate at bill ages 0, 35, 70, 105, 140, and 175 days, providing nonoverlapping 30-day windows over the first six months. This first experiment does not validate forecasts for older bills. The time-to-sign model estimates weekly hazards within each window (four 7-day intervals plus a final 2-day interval).

## Information boundaries

- Prior member, sponsor, network, and policy histories use only the completed previous Congress.
- Historical eligibility and party/state use dated service terms, not today's roster.
- Dynamic bill actions, earlier joins, and statements are strictly earlier than the forecast day. Same-day joins are excluded from candidates conservatively; they are not supplied as features until the next day.
- Titles must be explicitly marked as introduced. Fixed rules derive policy topics from introduced titles; no current aggregate stance scores or personality features enter.
- Bill analogues use only prior-Congress introduced titles and a predetermined similarity rule. Similarity does not establish identical legislative effect.
- Dated public evidence is reconstructed from published dates and source text. Historical first-observed timestamps are not comprehensively available. This is a retrospective event-time backtest, **not proof of a real historical deployment**. Statements coded by current learned/gold stance models are not used as ground truth; the first experiment uses explicit, auditable text rules.
- Full 30-day observation is required for binary scoring. Death, departure, end of Congress, or data cutoff censors survival exposure. Such rows are excluded from binary metrics when their horizon is incomplete, even when an early positive is known, to avoid outcome-conditioned selection.

## Splits and models

Train on Congress 117 (2021-22), develop and choose configurations on Congress 118 (2023-24), then refit on completed Congresses 117+118 and evaluate once on Congress 119. The final test cutoff is 2026-09-03, conservatively preceding the current bulk extraction date. Freeze source hashes, rows, features, model settings, and predictions. Do not tune on final test outcomes.

1. Baseline logistic: prior signing volume, sponsor relationship, prior network/ideology, party/state/chamber and seniority, introduction referral/topic information.
2. Enhanced logistic: baseline + prior member-policy rates + predecessor/near-identical-title support.
3. Time-to-sign: piecewise-exponential hazard in weekly intervals, enhanced features + bill age + past actions and coalition development; integrate survival to the same 30-day horizon, holding observed covariates at their forecast values. Before model fitting, the implementation was specified as a Poisson likelihood with exposure weights instead of a logistic interval likelihood: this handles exact event/censor times and the final two-day interval without treating partial weeks as complete weeks. Regularization alpha in {0.000001, 0.00001} is selected on development only; the scale reflects a per-day event rate and the Poisson implementation's mean-loss normalization.
4. Boosted decision trees: scikit-learn histogram gradient boosting, identical enhanced inputs; then dynamic-feature improvement evaluated in development.
5. Public-position additions: compare otherwise identical models with and without dated statement features. Include a coverage/mention-only boosted control without support/oppose indicators, so collection volume is not mistaken for directional stance information. Report coverage and a source-covered subset as well as the whole population. Missing evidence is missing coverage, not opposition. The expanded source audit adds raw hearing sequences and full social-post text before fitting; the chamber/service/party guard and stricter actor attribution are tested before replacing the preliminary public columns.
6. Existing production logistic: use its actually emitted out-of-time raw scores for Congresses 118 and 119 on their common covered population. Calibrate its eventual-sign score to this 30-day endpoint on development data only. Its existing count-based bill eligibility and committee-timing caveat remain explicit; it is a coverage-limited comparator, not silently substituted by the new baseline.

Prespecified small development grid: logistic C in {0.1, 1.0}; boosting max_leaf_nodes in {7, 15}, max_iter in {100, 200}, learning_rate=0.06, l2_regularization=10, min_samples_leaf=50, early_stopping=False. Select by development average precision; ties favor simpler models. Sample at most 10% of mature negative training rows deterministically while retaining all positives, with inverse inclusion weights. Development and final test metrics use every eligible row; no balancing. Numerical/resource corrections may change computation without changing the estimand and must be receipted.

## Evidence required

Before fitting, a shared-host memory allocation failure in metadata conversion required streaming that conversion. The hazard learner uses 2% of negative landmark rows (inverse weights 50) and all events, within the prespecified at-most-10% bound; binary learners use 10% (inverse weights 10). Validation/test remain complete and unweighted. Feature arrays are memory-mapped and scored in chunks.

Primary selection metric: average precision on the complete eligible risk set. Also report Brier score, log loss, precision and recall at 8 and 25 within bill/date groups, and calibration bins. Freeze ties by member identifier. Display House/Senate, party, bill age, zero-signature-at-forecast, and statement-coverage breakdowns. Compare all models on exactly the same rows in each declared population.

Use paired bill/family-cluster bootstrap intervals for metric differences, with member-cluster sensitivity for proper-score improvements. There is one fixed final evaluation, not a search for a significant subgroup. For headline significance across the primary challenger family, use simultaneous/conservative multiplicity-aware intervals; exploratory intervals remain labeled. A practical improvement and uncertainty must both be reported. No individual forecast or feature coefficient is called a causal lobbying effect.

## Prior research

- Russo et al. (ACL 2023), *Helping a Friend or Supporting a Cause?* https://aclanthology.org/2023.acl-long.166/ : bill text, speeches and relational graph representations for cosponsorship. Their >10-cosponsor selection and task/split differ from our unbalanced 30-day future-join population; their F1 cannot be imported as our expected accuracy.
- Brandenberger (2018), *Trading Favors*, Social Networks 54:238-253. https://doi.org/10.1016/j.socnet.2018.02.001 : event-ordered congressional reciprocity and time to cosponsorship.
- *Timing Their Positions: Cosponsorship in the State Legislature*. https://www.cambridge.org/core/journals/state-politics-and-policy-quarterly/article/timing-their-positions-cosponsorship-in-the-state-legislature/BDFFF37FE5D8355DC5867387682D3FA7 : Cox duration analysis, a state-level methodological precedent.
- Nay (2017), *Predicting and understanding law-making with word vectors and an ensemble model*. https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0176999 : legislative text and ensemble prediction of enactment, an adjacent outcome rather than individual signatures.
- Scikit-learn histogram gradient boosting implementation: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html
