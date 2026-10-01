"""Render the fitted results and methodological limits as readable artifacts."""
from .regression import ROOT,OUT,MODELS,read_json,save

LABELS={'context':'Initial context controls','context_work':'Controls + shared work',
    'work_similarity':'Work + E/A/O similarity','work_levels':'Work + individual E/A levels',
    'combined':'Work + similarity + individual levels','combined_all_five':'Combined + C/N similarity',
    'work_visibility':'Work + visibility','combined_visibility':'Combined + visibility',
    'combined_no_A':'Combined without Agreeableness',
    'expanded_work':'Expanded controls + work','expanded_combined':'Expanded controls + work + personality',
    'expanded_work_visibility':'Expanded controls + work + visibility',
    'expanded_combined_visibility':'Expanded controls + work + visibility + personality'}


def table(rows,heads):
    return '\n'.join(['| '+' | '.join(heads)+' |','| '+' | '.join(['---']*len(heads))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def write(name,text):(OUT/name).write_text(text.strip()+'\n',encoding='utf-8')


def main():
    original=read_json(OUT/'model_results.json');ranks=read_json(OUT/'same_fit_auc.json')
    expanded=read_json(OUT/'expanded_controls_results.json');erank=read_json(OUT/'expanded_controls_same_fit_auc.json')
    cases=read_json(OUT/'cases.json');audit=read_json(OUT/'bias_audit.json')
    sensitivity=read_json(OUT/'sensitivity_results.json');corr=read_json(OUT/'trait_bias_correlations.json')
    final=expanded['expanded_combined_visibility']['members']['metrics']
    control=expanded['expanded_work_visibility']['members']['metrics']
    def result_table(results,auc):
        rows=[]
        for name,result in results.items():
            m=result['members']['metrics'];f=result['family']['metrics']
            rows.append([LABELS[name],f"{m['accuracy']:.1%}",f"{m['balanced_accuracy']:.1%}",
                f"{auc[name]['auc']:.3f}",f"{m['auc']:.3f}",f"{m['log_loss']:.3f}",
                f"{m['true_negative']}/9",f"{f['accuracy']:.1%}"])
        return table(rows,['Model','Member-holdout accuracy','Balanced accuracy','Same-fit AUC',
            'Pooled AUC','Log loss','Antagonisms detected','Pair/source holdout accuracy'])
    report=f"""# Multivariable congressional relationship regression — September 10, 2026

The regression is fitted. Shared work carries useful information. Personality adds some ranking information, but the size of its contribution depends on ideological and exposure controls. Personality similarity by itself did not improve on work. The earlier large personality improvement does not survive every bias check.

The most fully adjusted exploratory model scores **{final['true_positive']+final['true_negative']}/29 pairs correctly ({final['accuracy']:.1%})**, with **same-fit AUC {erank['expanded_combined_visibility']['auc']:.3f}** and log loss **{final['log_loss']:.3f}**. The comparable work-and-visibility model without personality also gets **{control['accuracy']:.1%}** correct, with AUC **{erank['expanded_work_visibility']['auc']:.3f}** and log loss **{control['log_loss']:.3f}**. Personality improves ranking and probability scoring in that comparison, not the count of correct classifications. Always choosing the majority positive class would get 20/29, or 69.0%, correct.

This is a retrospective test of **positive versus negative signs among 29 documented ties**: 20 friendship pairs and 9 publicly antagonistic pairs, 33 documented directions, 42 members, and 25 connected source components. It is not a test of whether an arbitrary unreviewed pair are friends, nor a calibrated probability of private affection or dislike. Inferred affinity and eight weak-only warmth pairs were excluded from primary labels.

## What was fitted

Ridge logistic regression uses the full frozen 116th–119th Congress HR/S history: 61,085 bills, including late cosponsorships, repeated titles as separate bills, and ever-joined signatures. There is no 30-day limit. Predictor blocks are forward/reverse direct cosponsorship propensity, shared cosponsorship, network proximity, E/A/O similarities, and each member's E/A levels. C/N similarity is a separate test.

Initial controls: same party, same state, same chamber, absolute DW-NOMINATE dimension-one distance, issue similarity, each endpoint's leadership, and shared service Congresses. Expanded controls additionally include each endpoint's DW dimensions 1 and 2, Republican indicator, and Senate indicator. Visibility models add each endpoint's log interview-word count and role-adjusted public visibility.

Ideology and geography enter as adjustment variables, not predetermined negative friendship weights. Same state is a coarse geography control; district distance, office proximity, committee/caucus incentives, and historical changes in ideology and leadership remain incomplete. Conditioning on measured variables does not establish that all incentives have been held constant.

## Results, including unsuccessful variants

All rows below hold out the focal members' relationship labels and all connected source-family labels. Each penalty is selected using training-only inner validation. Accuracy uses one held-out dyad at a time. Same-fit AUC holds out one positive dyad and one negative dyad together, with all of their members and source connections removed, and compares predictions from the same fit. There are 180 such comparisons per model; none were skipped.

{result_table(original,ranks)}

The two bias checks below were added after inspecting initial results, and are explicitly exploratory. No outer-test score was used to pick a penalty. Trying multiple feature sets on these same 29 labels still creates selection risk, so the strongest row is not an independent confirmation.

{result_table(expanded,erank)}

The combined original model gets 29/29 correct **in sample**. That perfect training fit is not predictive accuracy. Holding members out reduces it to 22/29. The expanded visibility model gets 24/29 held out: 19/20 positive pairs and 5/9 antagonistic pairs. Four antagonistic pairs remain missed, so inferred dislikes are the weaker part of the model.

## Main weaknesses and bias findings

1. **Trait estimates contain ideological structure.** Roster correlations with DW1 are O {corr['O']['correlations']['dw1']['r']:.3f}, C {corr['C']['correlations']['dw1']['r']:.3f}, E {corr['E']['correlations']['dw1']['r']:.3f}, A {corr['A']['correlations']['dw1']['r']:.3f}, and N {corr['N']['correlations']['dw1']['r']:.3f}. These are associations, not proof of estimator bias. However, ideological distance alone does not control political asymmetry at each endpoint. After adding endpoint controls, personality's same-fit AUC gain without exposure controls shrinks from 0.056 to 0.006; log loss actually worsens from 0.529 to 0.600. With exposure controlled, the AUC increment is 0.033 and log loss improves from 0.513 to 0.461. Its incremental value is therefore specification-sensitive; the extra parameters also add estimation variance.

2. **Visibility and coverage selection are substantial.** Median interview words are {audit['label_visibility']['median_interview_words']:,.0f} among labeled members versus {audit['roster_visibility']['median_interview_words']:,.0f} across the roster, a {audit['label_visibility']['median_interview_words']/audit['roster_visibility']['median_interview_words']:.1f}× difference. Agreeableness is observed for 41/42 labeled members but only 316/532 current members. A classifier validated on highly visible people cannot yet establish performance for quiet, poorly covered members.

3. **Agreeableness carries much of the personality signal, with possible measurement overlap.** The composite A score weights observer-language A at 90% and inverse interview antagonism at 10%. Public hostility helps define negative labels, so A and the outcome may partly measure the same behavior. The observer corpus may contain labeling episodes; exact source-purged profiles are unavailable in these aggregate snapshots. Extraversion also incorporates visibility, dominance and role-related measurements. Holding out tie labels does not purge their underlying speech from fixed trait measurements.

4. **Source and label selection are asymmetric.** Strict labeled events include nine positive versus three negative floor-record events, but one positive versus six negative interview events. Prompted cross-party friendship nominations and conspicuous public conflicts are oversampled. Some negative episodes may primarily describe strategic disputes. Removing Cruz–McConnell and Comer–Jeffries lifts the original model's pooled member-holdout AUC from 0.828 to 0.964 on the remaining 27 cases; that sensitivity is evidence of unstable label composition, not permission to discard difficult cases from the headline result.

5. **Subgroups are too thin for broad claims.** There is only one negative Senate–Senate pair and no negative same-state pair. The original model misses all three currently mixed-chamber cases; chamber changes over time complicate their work histories. Neither geographic fairness nor reliable Senate-dislike detection is established. The original 42 labeled members cover only 7.9% of the current roster. We did not infer demographic attributes from names or audit demographic error rates without verified labels.

6. **The sample is small and dependent.** Twenty initial predictors, later expanded to 32, are fitted to just 29 dyads; missingness indicators add columns, although many are constant. Regularization limits coefficients, but cannot create independent examples. Removing Katie Britt's three positive dyads reduces the original pooled member-holdout AUC to 0.758. Direct/shared-work features are correlated: reverse direct propensity and weighted shared Jaccard correlate at 0.920. Network proximity has little stable independent contribution once shared work is included; a negative partial coefficient is not evidence that proximity causes dislike.

7. **Temporal and construct limits remain.** Events span July 2015–April 2026; legislative features include later behavior through the frozen September 2026 snapshot. Personality measures are also contemporary. These are retrospective associations, not a prospective prediction test. Public antagonism and private dislike differ; friendship statements are evidence, not an infallible ground truth. The low-E/low-A “my friend” sincerity hypothesis requires independently labeled sincerity or later corroboration and has not been validated by this regression. Unpurged target-specific warmth and hostility were deliberately excluded from predictors.

## Personality source checks

These keep the same 29 labels and original controls. They are alternate measurements, not independent datasets. Floor-only/interview-only scores reduce genre mixing but do not remove exact source overlap.

"""
    source_rows=[]
    for name in ['text_only','observer_only','floor_observer','interview_observer','unordered_features','weak_warmth_included']:
        m=sensitivity[name]['combined']['members']['metrics']
        source_rows.append([name,m['n'],f"{m['accuracy']:.1%}",f"{m['auc']:.3f}",f"{m['log_loss']:.3f}"])
    report+=table(source_rows,['Sensitivity','Pairs','Accuracy','Pooled member-holdout AUC','Log loss'])
    report+="""

Observer-only scores perform better than the shipped composite in this selected sample, but their source overlap prevents interpreting that result as stronger independent personality validation. The common-complete-case reruns are included in `sensitivity_results.json`; they keep an identical 28-pair sample across composite, text-only and observer-only profiles. C and N have weaker external support than E/A: C has academic-panel r = −0.039 and fails discriminant dominance in both panels; N has academic-panel r = 0.123. Neither consistently improves relationship validation.

## What the model can support now

Use the fully adjusted model as a candidate ranking tool alongside explicit statements, co-sponsorship receipts and event dates. Keep documented friendship and public antagonism distinct from model inference. Do not turn a low score, low cooperation, or an absent trait estimate into a negative relationship label. The next evidence improvement is a new, independently reviewed test set with more same-party, same-state and Senate antagonisms, less-visible members, and trait measurements that exclude each evaluation episode and later text. That would test whether the apparent gain survives source separation and sampling balance.

All model results, unsuccessful variants, per-pair held-out predictions, coefficients, 500 source-component coefficient resamples, and 2,000 attempted source/member resamples of prediction stability are saved. Stability ranges are descriptive, not independent-row confidence intervals or causal significance tests. Original pooled AUC gains include zero in both source and member resampling ranges. No ordinary logistic p-values are reported.

See [the exact math](MATH.md), [coefficients](COEFFICIENTS.md), [held-out predictions](PREDICTIONS.md), `bias_audit.json`, `trait_bias_correlations.json`, and the source-hash receipts. The frozen legislative, speech and production personality inputs were unchanged.
"""
    write('REPORT.md',report)
    math=r"""# Exact regression math and validation

This analysis estimates the sign of an already documented tie. Let dyad d have reviewed label y_d=1 for a personal friendship declaration and y_d=0 for person-directed public antagonism. Unknown, merely cordial and rule-inferred ties have no primary y. Mixed-sign pairs are excluded. The same unordered pair is never both a training and held-out case.

For documented direction i→j:

\[
p_{ij}=\sigma(\alpha+\gamma^T C_{ij}+\beta^T W_{ij}+\delta^T S_{ij}+\eta^T L_{ij}+\nu^T V_{ij}+\rho^T M_{ij}),\quad
\sigma(x)=1/(1+e^{-x}).
\]

C is the context block. W is shared work. S contains E/A/O similarities. L contains actor E, target E, actor A and target A. V is included only in visibility specifications. M contains missingness indicators. All continuous and binary columns, including varying missingness indicators, are standardized using training-only weights. No sign is forced and context coefficients are not interpreted as negative friendship penalties.

**Work definitions.** For bill b, A_ib indicates ever joining as a valid cosponsor, E_ib indicates an eligible service opportunity, and sponsor(b) identifies the sponsor. Eligible service uses dated same-chamber overlap from introduction through Congress end or the data cutoff. It does not require a complete 30-day window. Withdrawal does not erase a historical join.

\[
D_{ij}=\sum_b A_{ib}1\{sponsor(b)=j\},\quad N_{ij}=\sum_b E_{ib}1\{sponsor(b)=j\},\quad P_{ij}=D_{ij}/N_{ij}.
\]

Undefined denominators remain missing. Shared third-party cosponsorship is H_ij=Σ_b A_ib A_jb. Bill weights are w_b=1/max(1,n_b−1), where n_b counts all historical cosponsors, including members outside the current roster. The weighted shared score and eligible union are:

\[
H^w_{ij}=\sum_b w_b A_{ib}A_{jb},\quad
U^w_{ij}=\sum_b w_b(E_{ib}A_{jb}+E_{jb}A_{ib}-A_{ib}A_{jb}),\quad J^w_{ij}=H^w_{ij}/U^w_{ij}.
\]

The work vector is (P_ij,P_ji,Jw_ij,log(1+H_ij),Q_ij). Q is cosine similarity between the two members' weighted-shared-work profiles, excluding both focal endpoints. It uses only observed legislative behavior, never personal-relationship labels. The full derivation, historical eligibility and retained bill counts are in `research/MEMBER_PERSONAL_RELATIONSHIPS_V3_MATH.md`.

**Personality.** For trait t, S_tij=exp(−|z_ti−z_tj|). This is a positive compatibility measure; its regression association is estimated rather than assumed. C/N similarities are a separate extension. Source-specific genre profiles are scaled on the fixed measurement roster without using relationship labels. The later regression preprocessing is still training-only. Similarity or low A/E cannot establish the truth of a particular statement.

**Weighting and fitting.** If a dyad has m_d documented directions, each has weight 1/m_d. Every dyad therefore contributes total weight one, regardless of reciprocal declarations or repeated episodes. With n training dyads, the optimization is:

\[
\min_{\alpha,\theta}\;{1\over n}\sum_d {1\over m_d}\sum_{(i,j)\in d}
[-y_d\log p_{ij}-(1-y_d)\log(1-p_{ij})]+{\lambda\over2}\|\theta\|_2^2.
\]

The intercept is unpenalized. Missing feature values are replaced with the weighted training mean over observed values; an all-missing training column uses zero. A missingness indicator is retained. Weighted training means and standard deviations then standardize all columns; constant columns use scale one. Newton optimization uses a line search and must finish with maximum absolute gradient ≤1e−7. The penalty grid is 0.03, 0.1, 0.3, 1, 3; smaller penalty means less shrinkage. Selection minimizes inner held-out dyad log loss. Exact ties favor larger penalties. No outer-held-out outcome selects its own penalty or preprocessing.

The final coefficient tables use all reviewed dyads and select λ through pair/source-family inner validation. Their training fit is not validation. Odds ratios are exp(beta) per one weighted training standard deviation, holding other measured predictors fixed. For binary columns this is a standardized increment, not the full 0→1 contrast. Context is neither removed from fitted probability nor manually subtracted to fabricate a population “friendship probability.”

**Exclusions.** Pair/source holdout excludes both directions of the focal pair and the transitive connected component of pairs sharing a source family. Source families from weaker episodes of an otherwise strict pair also enter the exclusion graph. Member holdout initially removes every pair containing either focal endpoint, then removes every source-connected case. Inner folds follow the same rule within their training pool. Legislative and trait observations for held-out people remain available: this is transductive member-label holdout, not unseen-person measurement prediction.

**Metrics.** The dyad prediction is the mean of predicted probabilities across its actually documented directions. Accuracy uses threshold 0.5. Balanced accuracy averages positive and negative recalls. Log loss is −mean[y log(p)+(1−y)log(1−p)]. Brier score is mean[(p−y)^2]. Neither accuracy nor AUC measures population calibration.

Pooling scores from different leave-one-out fits can distort AUC through differences in class balance and fitted intercepts. The training-prevalence baseline illustrates this: pooled AUC is near zero even though a constant score within a fit has AUC 0.5. We retain pooled AUC for reproducibility and add a same-fit check. For every positive dyad d+ and negative dyad d−, exclude both dyads, all their endpoints' labeled ties, and all connected source families; tune and fit on the remainder; compare the two held-out predictions from that one fit:

\[
\widehat{AUC}_{same-fit}={1\over20\cdot9}\sum_{d^+,d^-}
[1\{p_{d^+}>p_{d^-}\}+\tfrac12 1\{p_{d^+}=p_{d^-}\}].
\]

All 180 comparisons were scored. AUC and one-dyad-holdout accuracy thus use different training exclusions, explicitly shown in the tables. The same-fit check addresses cross-fit ranking distortion; it does not eliminate dyadic dependence, sparse training data, source overlap in traits or case-selection bias. See [Airola et al., A comparison of AUC estimators in small-sample studies](https://proceedings.mlr.press/v8/airola10a.html). Nested tuning separates selection and assessment within a declared model family; examining many families still needs a new test set for confirmation. See [Cawley and Talbot, model-selection overfitting](https://www.jmlr.org/papers/v11/cawley10a.html).

**Uncertainty.** Coefficient stability draws 500 bootstrap samples of the 25 connected source components and refits at the final selected penalty, preserving pair weights. Coefficients are transformed back onto the original fit's standard-deviation units before taking quantiles. This fixes the penalty and does not capture all tuning uncertainty or shared-member dependence. Separate resampling of existing held-out predictions uses source components and member multiplicities: a dyad receives weight equal to the product of its endpoints' bootstrap multiplicities. These ranges are descriptive stability diagnostics. They do not refit the full CV procedure, guarantee confidence coverage or establish a p-value.

All feature families and failed sensitivity results are retained. The initial plan preceded the first fit of this version; the same-fit ranking and expanded endpoint-control checks were later diagnostic additions, not retrospective preregistration. Source-specific profile evaluations are not source-purged prospective validation.
"""
    write('MATH.md',math)
    ctext='# Coefficients and descriptive stability\n\nAll odds ratios are per one training standard deviation with other measured predictors held fixed. Positive values predict a positive label among documented ties. Intercepts and scales are available in the corresponding JSON files. Intervals below are source-component bootstrap stability ranges, not inferential confidence intervals.\n'
    for title,filename in [('Declared initial combined model','coefficients.json'),
                           ('Expanded endpoint controls','expanded_combined_coefficients.json'),
                           ('Expanded endpoint and visibility controls','expanded_combined_visibility_coefficients.json')]:
        fit=read_json(OUT/filename)
        ctext+=f"\n## {title}\n\nPenalty λ = {fit['model']['penalty']}; intercept = {fit['model']['beta'][0]:.4f}; {fit['bootstrap_n']} successful bootstrap fits.\n\n"
        ctext+=table([[r['feature'],f"{r['beta']:.4f}",f"{r['odds_ratio']:.3f}",
                       f"[{r['stability_beta_low']:.3f}, {r['stability_beta_high']:.3f}]",f"{r['bootstrap_positive_fraction']:.1%}"]
                     for r in fit['coefficients'] if not r['feature'].endswith('__missing')],
                     ['Feature','Standardized beta','Odds ratio','95% stability beta range','Bootstrap beta > 0'])+'\n'
    write('COEFFICIENTS.md',ctext)
    ptext='# Predictions with both members’ relationship labels held out\n\nScores are conditional positive-label probabilities in this selected case set, not population friendship probabilities. Reviewed evidence remains the label when a model disagrees. Each model was trained without the focal endpoints’ labeled ties and connected sources.\n\n'
    prows=[];export=[]
    for i,c in enumerate(cases):
        o=original['combined']['members']['predictions'][i]['p']
        e=expanded['expanded_combined_visibility']['members']['predictions'][i]['p']
        prows.append([' / '.join(c['names']),c['sign'],f'{o:.3f}',f'{e:.3f}','yes' if (e>=.5)==bool(c['y']) else 'no'])
        export.append(dict(**c,initial_combined_heldout=o,expanded_visibility_heldout=e,
                           correct=(e>=.5)==bool(c['y'])))
    ptext+=table(prows,['Members','Reviewed sign','Initial model','Expanded + visibility','Expanded correct'])
    write('PREDICTIONS.md',ptext);save(OUT/'named_predictions.json',export)
    print('Reports written to',OUT)


if __name__=='__main__':main()
