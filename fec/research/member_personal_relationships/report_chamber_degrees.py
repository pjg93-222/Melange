"""Report completed graded development experiment without binary accuracy claims."""
from collections import Counter
from datetime import datetime,timezone
import numpy as np
from .data import read_json,digest,write_ndjson
from .run_history import read_rows
from .regression import save
from .run_chamber_degrees import OUT,verify_prepared
from .ordinal_degrees import weighted_metrics


def main():
    verify_prepared();rows=read_rows(OUT/'annotations.ndjson');features=read_json(OUT/'features.json')
    results=read_json(OUT/'model_results.json');coverage=read_json(OUT/'coverage_audit.json')
    routine=read_json(OUT/'routine_retrieval_audit.json');reviews=read_rows(OUT/'routine_reviewed.ndjson')
    model='G3_chamber_personality'
    predictions={q:{r['id']:r for r in results[model][q]['predictions']} for q in ('affinity','friction')}
    support={q:dict(unseen_observed_grade_folds=[dict(id=r['id'],names=r['names'],observed_grade=r['observed_grade'],
                      train_grades=r['train_observed_grades'],p_observed=r['probability_by_grade'][r['observed_grade']])
                      for r in results[model][q]['predictions'] if r['observed_grade'] not in r['train_observed_grades']],
                   neutral_grade_observed=False) for q in ('affinity','friction')}
    save(OUT/'grade_support_audit.json',support)
    # A descriptive, explicitly post-hoc robustness check, not a replacement fit:
    # add half a pseudo-count per grade to each held-out predictive distribution.
    smoothing={}
    for name,res in results.items():
        smoothing[name]={}
        for q in ('affinity','friction'):
            ps=res[q]['predictions'];counts=Counter(tuple(r['pair']) for r in ps)
            p=np.array([(r['train_dyads']*np.array(r['probability_by_grade'])+.5)/(r['train_dyads']+2.5) for r in ps])
            smoothing[name][q]=weighted_metrics([r['observed_grade'] for r in ps],p,[1/counts[tuple(r['pair'])] for r in ps])
    save(OUT/'posthoc_probability_smoothing.json',dict(reason='One mild-friction grade disappears entirely in its member/source-purged training fold; raw probabilities nearly collapse.',
        formula='p_smoothed[k] = (N_training_dyads * p_raw[k] + 0.5) / (N_training_dyads + 2.5)',
        status='Post-hoc probability-floor diagnostic; no coefficients refitted and not a calibrated prior or a replacement primary result',results=smoothing))
    profiles=[]
    for row in rows:
        profile=dict(row,original_work=features[row['id']],model=model,development_predictions={})
        for q in ('affinity','friction'):
            p=predictions[q].get(row['id'])
            profile['development_predictions'][q]=None if p is None else dict(expected_grade=p['expected_grade'],
                probability_by_grade=p['probability_by_grade'],validation='held_out_endpoints_and_source_families',
                observed_grade_present_in_training=p['observed_grade'] in p['train_observed_grades'])
        profiles.append(profile)
    write_ndjson(OUT/'dated_relationship_profiles.ndjson',profiles)
    lines=['**Chamber-aware relationship degrees: implementation and development results**','',
        'The model now estimates affinity and personal friction independently on ordered 0–4 scales, with date-aware House, Senate, and cross-chamber contexts. Original cosponsorship history precedes the assessed date. Unknown remains unknown; an absent friendship or antagonism label is never a zero.','',
        '**Result:** personality improves on the chamber-aware context/work model, but none of the richer primary models beats the simple chamber-only baseline on ordinal log loss. The chamber split and richer representation are implemented; predictive superiority is not demonstrated.','',
        f'There are {coverage["assessments"]} dated directed assessment records for {coverage["unique_pairs"]} unordered pairs. Affinity has 35 assessed records across 30 dyads; friction has 12 across 11. Twenty-six records remain unassessable on both dimensions. These are single-assistant assessments of reviewed public evidence, not independent human gold labels or direct measures of private feelings.','',
        '| Primary model | Affinity log loss | Affinity mean absolute grade error | Friction log loss | Friction mean absolute grade error |',
        '|---|---:|---:|---:|---:|']
    for name,result in results.items():
        a,h=result['affinity']['metrics'],result['friction']['metrics']
        lines.append(f'| {name} | {a["ordinal_log_loss"]:.3f} | {a["mean_absolute_grade_error"]:.3f} | {h["ordinal_log_loss"]:.3f} | {h["mean_absolute_grade_error"]:.3f} |')
    lines += ['', 'Lower is better. Errors are measured in the chosen grade coding; a one-grade difference is not a known unit of private emotional distance. Validation excludes both members and transitively shared source families. Each unordered dyad has total weight one across its assessed directions/episodes. Models use identical scored records, train-only imputation/scaling, and a penalty fixed before fitting. The reference baseline learns chamber-specific grade distributions. These metrics cannot be compared directly with the earlier binary classification accuracy.','',
        '**The rare-grade failure matters.** Comer→Goldman is the only mild-friction (grade 1) assessment. Holding out Comer and the shared source leaves only grades 2 and 3 in that training fold. The G3 model assigns the observed grade probability about 2.7×10⁻¹¹. That single case dominates friction log loss even though average grade error is much smaller. The raw result is retained, not dropped. Grade coverage, rather than a single accuracy percentage, is essential.','',
        'A separate, explicitly post-hoc smoothing diagnostic adds half a pseudo-count per grade to each prediction, scaled by the number of training dyads. It tests sensitivity to unsupported grade probabilities; it does not validate neutrality or change fitted coefficients. See `posthoc_probability_smoothing.json`. Regularization sensitivities at 0.3 and 3.0 are also preserved.','',
        '**Chamber and neutrality coverage**','',
        '| Dated chamber | Assessed affinity records | Assessed friction records |',
        '|---|---:|---:|',
        '| House | 20 | 9 |','| Senate | 15 | 1 |','| Cross-chamber | 0 | 2 |','',
        'There are no affirmative neutral labels, no affinity grade 0 labels, no friction grade 0 or 4 labels, and no jointly assessed mixed relationships. The model supports those states, but their accuracy is unmeasured. The lone Senate friction case cannot validate a separate Senate antagonism model. Chamber slopes share regularized information instead of being freely estimated from one example. Predictions of unsupported grades depend on assumptions and must not become confident relationship labels.','',
        '**Original work and personality**','',
        'House and Senate work matrices are separate. Bills enter strictly before each assessment date; each original signature requires introduction-day service eligibility. Distinct bill IDs and original signers who later withdrew are retained. There is no 30-day joining cutoff. Cross-chamber same-bill work is missing by construction, not zero affinity. Before-2019 relationship accounts have missing work history. Shared original coalitions, directed original support rates, issue-profile similarity and within-chamber network proximity are retained. Bipartisan propensity uses contemporaneous D/R affiliation and excludes the focal partner.','',
        'Ideology and geography are estimated contextual predictors and can contribute positively. Personality includes endpoint E/A levels, E/A/O similarity and an experimental joint-high-E × ideological-distance term. Neither low extraversion nor low agreeableness is treated as proof of sincerity. Fixed-roster personality, coverage and ideology measurements are retrospective; these results are not historical forecasts. Existing personality may still contain the passages used to establish relationships.','',
        'Chamber/venue/purpose/speaker-matched expression code is implemented with source exclusion and an explicit encounter denominator. No current assessment has an adequate systematic, context-reviewed baseline, so expression interactions remain unavailable. Selected lexical hits and cue-enriched reviews are not substituted for the denominator.','',
        '**Evidence checks**','',
        'Three 2017 records involving Roger Marshall or Lisa Blunt Rochester receive House context even though those members are now senators. Durbin→Tim Scott remains unassessable on personal closeness from the reviewed floor passage. The system retains the observed courtesy without assigning private friendship or neutrality.','',
        'One newly verified Senate example was added: Cotton explicitly distinguishes his friendship with Welch from customary Senate language and refers to their prior House service. The surrounding exchange identifies Welch as the target. The local transcript fragment had cut off near a reference to Rosen; the original prevents a mistaken target or antagonism label. Affinity is provisionally graded 2, with a plausible range of 1–3; personal friction remains unknown. [Congressional Record, October 17, 2023, S5030–S5031](https://www.govinfo.gov/content/pkg/CREC-2023-10-17/pdf/CREC-2023-10-17-senate.pdf).','',
        f'The cue-independent search covered all {routine["queried_development_pairs"]} sampled development pairs, yielding {routine["candidate_turns"]} candidate turns for {routine["pairs_with_returned_turns"]} pairs. Full-packet review found work references, ceremonial language, political evaluations and source defects; none established a neutral private relationship. The full-name search and latest-two-turn cap are narrow retrieval choices, so no-match is nonresponse, not evidence that a relationship is absent. These reviews were completed after the primary fit and were not used to change its labels.','',
        'The source defects include an unrelated headline appended to a Crow interview, historical John F. Kennedy footage misretrieved as the current senator in a Lankford transcript, an appended reporter transition after a Schumer utterance, and three interviews whose dates need verification. They are excluded from relationship labeling in the new review output. No original database rows or personality files were rewritten. These findings require source-attribution checks beyond numerical personality activation gates.','',
        '**Files and reproducibility**','',
        '`PLAN.md` gives the frozen development specification; `prefit_manifest.json` fixes the code, annotations and features before fitting. `model_results.json` contains every held-out prediction and training indices. `dated_relationship_profiles.ndjson` keeps observed grades, plausible ranges, source rationale and model predictions separate. `PAIRS.md` is the readable evidence table. `routine_reviewed.ndjson` records all 23 new dispositions. `run_receipt.json` and the final verification receipt record integrity checks.','',
        'The previous frozen v5 test remains unchanged and no held-out outcome labels were used. Population accuracy, independent inter-rater agreement, calibrated private-friendship probabilities and neutral/mixed-state accuracy remain unmeasured. The completed run is a development result, not a production promotion.','']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    table=['**Dated evidence grades and independent development predictions**','',
        'Grades are provisional public-evidence assessments, not private-feeling probabilities. Unknown is not neutral. Predictions shown are G3 out-of-fold expected grades; source independence and endpoint holdout apply. Shared original bills are counted strictly before the assessment date.','',
        '| Direction | Date / chamber | Observed affinity | Observed friction | Predicted affinity | Predicted friction | Prior shared originals | Evidence |',
        '|---|---|---:|---:|---:|---:|---:|---|']
    def number(v):return 'unknown' if v is None else f'{v:.2f}'
    for r in profiles:
        a=r['development_predictions']['affinity'];h=r['development_predictions']['friction']
        link=f'[source]({r["source_urls"][0]})' if r['source_urls'] else 'local reviewed source'
        note=r['rationale'].replace('|','/')
        table.append(f'| {" → ".join(r["names"])} | {r["date"]} / {r["chamber"]} | {number(r["affinity"])} | {number(r["friction"])} | {number(a["expected_grade"] if a else None)} | {number(h["expected_grade"] if h else None)} | {number(r["original_work"]["shared_original_bills"])} | {link}: {note} |')
    (OUT/'PAIRS.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
    save(OUT/'report_receipt.json',dict(completed_utc=datetime.now(timezone.utc).isoformat(),code_sha256=digest(__file__),
        files_sha256={n:digest(OUT/n) for n in ('REPORT.md','PAIRS.md','dated_relationship_profiles.ndjson','grade_support_audit.json','posthoc_probability_smoothing.json')},
        original_results_replaced=False))
    print('Report completed. Primary results retained; no population accuracy claim.',flush=True)


if __name__=='__main__':main()
