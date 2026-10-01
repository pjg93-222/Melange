"""Report all exploratory interactions, including their failure to improve prediction."""
from itertools import combinations
from datetime import datetime,timezone
import numpy as np
from .personality_context import (OUT,HERE,ROOT,read_json,save,digest,load_all,
    pair_similarity,finite,verify_lock)


LABELS={'R0_main_effects':'Main effects + bipartisan work',
        'R1_similarity_distance':'Add similarity × ideological distance',
        'R2_distance_bipartisanship':'Add bipartisan moderation of ideological interaction',
        'R3_party_bipartisanship':'Party-separation interaction + bipartisan moderation'}


def fmt(v,places=3):
    return 'Unavailable' if v is None else f'{v:.{places}f}'


def roster_structure(members,traits,ids):
    result=dict(trait_ideology_within_party={},pair_similarity_by_party={})
    for party in ['Democrat','Republican']:
        result['trait_ideology_within_party'][party]={}
        for t in 'OCEAN':
            rows=[(traits[a][t],members[a]['d1']) for a in ids if members[a]['party']==party
                  and finite(traits[a].get(t)) and finite(members[a].get('d1'))]
            result['trait_ideology_within_party'][party][t]=dict(n=len(rows),r=float(np.corrcoef(np.asarray(rows).T)[0,1]))
    for label,parties in [('Democrat_Democrat',['Democrat','Democrat']),
                          ('Republican_Republican',['Republican','Republican']),
                          ('Democrat_Republican',['Democrat','Republican'])]:
        values=[pair_similarity(a,b,traits) for a,b in combinations(ids,2)
                if sorted([members[a]['party'],members[b]['party']])==parties]
        observed=[v for v in values if v is not None]
        result['pair_similarity_by_party'][label]=dict(total_pairs=len(values),complete_pairs=len(observed),
                                                      median_EAO_similarity=float(np.median(observed)))
    return result


def main():
    lock=verify_lock();receipt=read_json(OUT/'run_receipt.json')
    results=read_json(OUT/'model_results.json');ranking=read_json(OUT/'same_fit_auc.json')
    sensitivity=read_json(OUT/'without_mace_crockett.json');fitted=read_json(OUT/'coefficient_stability.json')
    profile=read_json(OUT/'mace_crockett_profile.json');pairs=read_json(OUT/'pair_descriptions.json')
    members,traits,ids,_=load_all()
    structure=roster_structure(members,traits,ids);save(OUT/'roster_political_structure.json',structure)
    table=[];reduced=[]
    for name,result in results.items():
        m=result['metrics'];s=sensitivity[name]['metrics']
        table.append(f"| {LABELS[name]} | {m['true_positive']+m['true_negative']}/29 ({100*m['accuracy']:.1f}%) | {100*m['balanced_accuracy']:.1f}% | {ranking[name]['auc']:.3f} | {m['log_loss']:.3f} | {m['true_positive']}/20 | {m['true_negative']}/9 |")
        reduced.append(f"| {LABELS[name]} | {100*s['accuracy']:.1f}% | {s['log_loss']:.3f} | {s['true_negative']}/8 |")
    trait_rows=[f"| {r['trait']} | {r['Nancy_Mace']:+.2f} | {r['Jasmine_Crockett']:+.2f} | {r['absolute_difference']:.2f} |" for r in profile['traits']]
    focus=next(p for p in pairs if 'Nancy Mace' in p['names'])
    focal_predictions=[]
    for name,r in results.items():
        p=next(p for p in r['predictions'] if set(p['pair'])==set(focus['pair']))
        focal_predictions.append(f"| {LABELS[name]} | {p['p']:.4f} | {'Positive' if p['p']>=.5 else 'Antagonistic'} |")
    s1=fitted['R1_similarity_distance']['interaction_effects']['S_D']
    s2=fitted['R2_distance_bipartisanship']['interaction_effects']['S_D_B']
    party_rows=[]
    for t in 'OCEAN':
        left=structure['trait_ideology_within_party']['Democrat'][t]
        right=structure['trait_ideology_within_party']['Republican'][t]
        party_rows.append(f"| {t} | {left['r']:+.3f} ({left['n']}) | {right['r']:+.3f} ({right['n']}) |")
    body=f'''# Personality similarity, ideological separation, and bipartisan work

The current development evidence does **not support imposing a general rule that similar personalities clash across ideological lines**. Cross-party friendships show greater median cross-party legislative cooperation than cross-party antagonisms, but adding the proposed personality/politics interactions did not improve prediction. This is an exploratory test of the existing 29 documented ties, not a result from the frozen 120-pair test.

## Mace–Crockett: shared tendencies, substantially different levels

Both measured profiles have above-average Extraversion, below-average Agreeableness and above-average Neuroticism. They are not particularly close numerically. Their E/A/O similarity is at the **{100*profile['similarities']['EAO']['percentile']:.1f}th percentile** among complete measured pairs; their all-five similarity is at the **{100*profile['similarities']['OCEAN']['percentile']:.1f}th percentile**. Higher percentiles mean closer profiles. Only 49,770 pairs have complete scores, so these ranks describe that measured subset.

| Trait | Nancy Mace | Jasmine Crockett | Absolute difference in standardized score units |
| --- | ---: | ---: | ---: |
{chr(10).join(trait_rows)}

These are the existing public-language personality estimates, not self-reports or measurements of motives. Their DW1 distance is **0.848**. An ideological confrontation between people who share some behavioral tendencies is a plausible question; an exact mirror-personality account is not a good description of these measurements. Extraversion should not be equated with dominance, competitiveness or aggression.

The full-history panel contains **59 shared third-party bills** for this pair. Cooperation therefore coexists with their documented personal confrontation. Our partner-excluded bipartisan-work index is **{focus['bipartisan_pair']:.3f}**, above the cross-party friendship sample's median of 0.177. That is a concrete counterexample to treating bipartisan work as immunity from personal conflict.

## What was fitted

The outcome is the sign of an already documented tie: positive friendship evidence versus personal antagonism. Geography, issue similarity, service overlap, work history, visibility, endpoint ideology, party, chamber and leadership remain in the baseline. The individual E/A levels and separate E/A/O similarities remain main effects. S is their mean similarity and D is absolute DW1 distance. All five trait profiles are retained as data, with their existing validation qualifications.

For member i, exclude focal partner j. Within same-party and other-party current-roster Democratic/Republican sponsors, compute q_g=(joined_bills_g+0.5)/(eligible_bills_g+1). Define B_i=q_cross/(q_cross+q_same), then average the two endpoints to obtain B. At B_i=0.5, the two per-bill joining propensities are equal. This is an opportunity-adjusted cooperation measure, not the raw percentage of cross-party cosponsors or a personality score. One independent-member dyad lacks B; missingness is retained. Sponsor party uses the current snapshot, which is an imperfect historical classification.

The distance moderation model adds:

    eta = eta_main + beta_SD S D + beta_SB S B + beta_DB D B + beta_SDB S D B

Here eta is the log-odds of a positive sign conditional on a documented tie. The proposed mechanism would require unfavorable distance moderation of similarity at lower B, weakening at higher B. The relevant term is:

    change in similarity's association as distance rises = beta_SD + B beta_SDB

The party model replaces D in these added terms with P, an indicator for different recorded party affiliation. Both formulations retain every lower-order main effect. No coefficient sign was forced. They were specified before these new fits and estimated separately to limit redundant interactions.

Ridge penalties were selected in inner development folds. Every outer comparison removes all relationship labels involving either focal member and connected source families. Same-fit AUC additionally holds a positive and negative dyad out together: all 180 comparisons were scored for each model. Fixed work/personality measurements make this retrospective, transductive member-label validation. The 33–37 predictors and only 29 labels leave considerable instability despite regularization.

## Results, including the unsuccessful interactions

| Model | Accuracy | Balanced accuracy | Same-fit AUC | Log loss ↓ | Positive ties detected | Antagonisms detected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(table)}

The new baseline includes B in addition to the previous expanded model. Its 82.8% accuracy equals the previous result. Relative to the old model, same-fit AUC moves from 0.900 to 0.911, while log loss moves from 0.461 to 0.466. Thus the added cooperation measure is not a clear overall predictive improvement either.

The simple S×D coefficient is **{s1['raw_coefficient_or_moderation']:+.3f}**, whereas the blanket clash hypothesis predicted a negative value. Its 300 source-component resamples span **[{s1['stability_interval'][0]:+.3f}, {s1['stability_interval'][2]:+.3f}]**. The S×D×B coefficient is **{s2['raw_coefficient_or_moderation']:+.3f}**, spanning **[{s2['stability_interval'][0]:+.3f}, {s2['stability_interval'][2]:+.3f}]**. Both directions are unstable. A positive three-way point estimate does not establish attenuation of a negative effect that the fit did not establish in the first place. These are descriptive fixed-penalty stability ranges, not valid confidence intervals or significance tests.

Removing Mace and Crockett before repeating all comparisons gives:

| Model | Accuracy on remaining 28 | Log loss ↓ | Antagonisms detected |
| --- | ---: | ---: | ---: |
{chr(10).join(reduced)}

The interaction models still do not improve. This result does not hinge on simply classifying the motivating example incorrectly.

Mace–Crockett's member-label-held-out scores are below. These are conditional benchmark scores, **not probabilities of private friendship**:

| Model | Positive-sign score | Classification at 0.5 |
| --- | ---: | --- |
{chr(10).join(focal_predictions)}

The baseline classifies their documented antagonism correctly. The larger interactions move the score closer to the classification boundary. Changing one pair's score would not by itself validate a general psychological mechanism.

## What the broader descriptive patterns say

There are 14 different-recorded-party positive pairs and six negative pairs. Thirteen positive pairs have B, and thirteen have complete E/A/O similarity; the missing cases are not necessarily the same pair. Median B is **0.177** for the positive group and **0.122** for the negative group. Median E/A/O similarity is **0.504** versus **0.392**, respectively. These selected-case comparisons are consistent with studying cross-party cooperation and personality compatibility; they do not establish prevalence, causation or independent predictive value. Sanders–Warren is different by recorded party even though both caucus with Democrats; no silent party recoding was used.

Examples that must retain their positive evidence include Burchett–Moskowitz (S=0.862, D=0.891, 29 shared bills), Booker–Scott (S=0.598, D=1.187, 82 shared bills), and Durbin–Grassley (S=0.735, D=0.701, 147 shared bills). Arrington–Khanna has low S=0.184 and high D=1.104, illustrating that friendship does not require a close personality match. These are previously reviewed positive anchors, not new claims derived from legislative statistics. All original warm friendship labels keep their weight; no ideological-distance penalty rewrites them.

Across the measured roster, median E/A/O similarity is 0.467 within Democratic pairs, 0.426 within Republican pairs, and 0.404 for Democratic–Republican pairs. Trait coverage differs, so these describe complete-score pairs rather than every member relationship.

The earlier whole-roster Openness–DW1 correlation of about -0.50 falls to **-0.118 within Democrats** and **-0.137 within Republicans**. Much of the pooled association therefore reflects differences between the groups. Correlations for all traits are:

| Estimated trait | Within Democrats r (n) | Within Republicans r (n) |
| --- | ---: | ---: |
{chr(10).join(party_rows)}

Agreeableness estimates also track position within each party: closer-to-center positions correlate with higher estimated A in both groups. This may reflect behavior, source language, visibility, or measurement overlap. It does not establish that ideology causes personality or that a political group truly has a particular disposition. It is a reason to retain endpoint ideology and source-bias checks when interpreting personality interactions.

## Research interpretation and next use

Experimental research gives a narrower basis for the user's intuition. Matching dominant nonverbal behavior was less comfortable than complementary dominant/submissive behavior in two studies; this concerned interaction behavior, not shared Big Five profiles or congressional enemies. [Tiedens and Fragale, 2003](https://pubmed.ncbi.nlm.nih.gov/12635916/).

Cross-party conversations about nonpolitical personal experiences reduced affective polarization in experiments, while conversations emphasizing partisan disagreement did not show that benefit; persistence was limited. That supports distinguishing humanizing personal contact from merely debating or working across parties. [Santoro and Broockman, 2022](https://pubmed.ncbi.nlm.nih.gov/35731881/).

The resulting working hypothesis should be **trait- and context-specific**: shared confrontational tendencies might matter differently from shared warmth, and competitive settings might matter differently from supportive personal exchanges. This exploration does not establish that narrower mechanism. A separate future study would need direct measures of interaction style, actual personal warmth, status competition and independently coded leadership challenges; these cannot be recovered by relabeling all Big Five similarity as a clash risk.

Keep the new interactions experimental. Preserve source-backed warmth and personal antagonism as separate directed evidence dimensions. Cross-party work can change expectations, but cannot erase a fight or discount an explicit friendship. Existing personality source overlap, visibility selection and the small dependent sample still limit interpretation. The v5 frozen test and production graph were unchanged.

See [the prespecified exploratory plan](PLAN.md), [all pair comparisons](PAIR_COMPARISONS.md), [coefficients and stability](coefficient_stability.json), [held-out predictions](model_results.json), [gain stability](gain_stability.json), and [run provenance](run_receipt.json). Software verification is saved separately from these statistical results.
'''
    (OUT/'REPORT.md').write_text(body,encoding='utf-8')
    lines=['# Existing documented pairs: personality, politics, and work','',
           'These descriptions do not create new labels. B excludes the focal partner; all work is retrospective.','',
           '| Pair | Existing sign | E/A/O similarity | All-five similarity | DW1 distance | Bipartisan work B | Shared bills |',
           '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for p in pairs:
        lines.append(f"| {' — '.join(p['names'])} | {p['sign']} | {fmt(p['EAO_similarity'])} | {fmt(p['all_five_similarity'])} | {fmt(p['ideology_distance'])} | {fmt(p['bipartisan_pair'])} | {int(p['shared_bills'])} |")
    (OUT/'PAIR_COMPARISONS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    save(OUT/'report_receipt.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        report_code_sha256=digest(__file__),outputs={name:digest(OUT/name) for name in
             ['REPORT.md','PAIR_COMPARISONS.md','roster_political_structure.json']},
        frozen_test_unchanged=lock['freeze_id'],new_test_accuracy_claimed=False))
    print('Wrote development exploration report; frozen test unchanged')


if __name__=='__main__':main()
