"""Reproducible development experiment; frozen v5 and production are read-only."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import numpy as np
from .data import ROOT, read_json, digest, write_ndjson
from .regression import save, clean_json
from .run_history import read_rows
from .freeze_v5 import verify_lock
from .chamber_annotations import build_annotations
from .chamber_work import temporal_features, term_on, chamber_at
from .chamber_expression import matched_expression
from .ordinal_degrees import OrdinalDegrees, sigmoid, training_indices, weighted_metrics, reviewed_display

HERE=Path(__file__).resolve().parent
OUT=ROOT/'outputs/member_personal_relationships/20260910_chamber_degrees_v6'
HISTORY=ROOT/'outputs/member_personal_relationships/20260910_full_history'
PREVIOUS=ROOT/'outputs/member_personal_relationships/20260910_original_work_context'
FROZEN=ROOT/'outputs/member_personal_relationships/20260910_frozen_v5'
CONTEXT=['same_party','same_state','dw1_distance','actor_dw1','target_dw1','actor_dw2','target_dw2',
         'issue_similarity','co_service_years','actor_log_interview_words','target_log_interview_words']
WORK=['direct_propensity','reverse_direct_propensity','weighted_shared_jaccard','log_shared_bills',
      'network_proximity','actor_bipartisan','target_bipartisan']
PERSONALITY=['actor_E','target_E','actor_A','target_A','similarity_E','similarity_A','similarity_O']
MODELS={
 'G0_chamber_baseline':dict(features=[],chamber_slopes=False),
 'G1_pooled_context_work':dict(features=CONTEXT+WORK,chamber_slopes=False),
 'G2_chamber_context_work':dict(features=CONTEXT+WORK,chamber_slopes=True),
 'G3_chamber_personality':dict(features=CONTEXT+WORK+PERSONALITY,chamber_slopes=True),
 'G4_chamber_joint_E':dict(features=CONTEXT+WORK+PERSONALITY+['joint_high_E','joint_high_E_D'],chamber_slopes=True),
}


def code_paths():
    return [HERE/n for n in ['CHAMBER_DEGREES_V6.md','ordinal_degrees.py','chamber_annotations.py',
            'chamber_work.py','chamber_expression.py','run_chamber_degrees.py']]


def hashes(paths):
    return {str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in paths}


def new_cotton_assessment():
    return dict(id='v6:cotton_welch_20231017',actor='C001095',target='W000800',pair=['C001095','W000800'],
        date='2023-10-17',episode_id='cotton_welch_20231017',evidence_ids=['source_row_153803_and_original_S5030_S5031'],
        affinity=2,affinity_range=[1,3],friction=None,friction_range=None,neutral_evidence=False,
        families=['cotton_welch_20231017','CREC:CREC-2023-10-17:2023-10-17'],
        source_urls=['https://www.govinfo.gov/content/pkg/CREC-2023-10-17/pdf/CREC-2023-10-17-senate.pdf'],
        assessment_basis='single_assistant_review_of_original_Congressional_Record_pages_S5030_S5031',
        inference_scope='dated_public_evidence_proxy; not enduring private feelings',
        confidence='provisional_single_reviewer',date_basis='dated_floor_exchange',venue='CREC',
        purpose='policy_disagreement_and_friendship_clarification',courtesy_reviewed=True,
        closeness_and_trust_note='Shared prior House service is stated; no intimate support account in this passage.',
        rationale='Cotton responds to Welch after Welch objects to S.3041, distinguishes their friendship from customary Senate language, and dates it to shared House service. Clear liking is supported; his generic description of senators disliking one another is not a named negative tie. The local row is truncated after naming Rosen; the original establishes Welch as the target.')


def prepare():
    lock=verify_lock();OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'prefit_manifest.json').exists():
        raise ValueError('Prepared v6 exists; verify rather than silently re-annotating')
    source_paths=code_paths()+[HISTORY/n for n in ('members.json','traits.json','bills.ndjson','reviewed_events.ndjson')]+[
        PREVIOUS/'graded_events.ndjson',PREVIOUS/'exchange_context.ndjson',
        FROZEN/'member_assignment.json',FROZEN/'development_reviewed_interactions.ndjson']
    before=hashes(source_paths)
    members=read_json(HISTORY/'members.json');traits=read_json(HISTORY/'traits.json')
    assignment=read_json(FROZEN/'member_assignment.json')
    rows=build_annotations(read_rows(PREVIOUS/'graded_events.ndjson'),read_rows(PREVIOUS/'exchange_context.ndjson'),read_rows(HISTORY/'reviewed_events.ndjson'))
    rows.append(new_cotton_assessment())
    for r in rows:
        assert all(assignment[a]['split']=='development' for a in r['pair'])
        r['names']=[members[r['actor']]['name'],members[r['target']]['name']]
        r['chamber']=chamber_at(members,r['actor'],r['target'],r['date'])
        if not r['chamber']:raise ValueError('Unresolved dated membership')
        r['display']=reviewed_display(r['affinity'],r['friction'],r['neutral_evidence'])
        r['coverage_tiers']=[assignment[a]['coverage_tier'] for a in (r['actor'],r['target'])]
    write_ndjson(OUT/'annotations.ndjson',rows)
    feature_rows,audit=temporal_features(members,read_rows(HISTORY/'bills.ndjson'),rows)
    for r in rows:
        a,b=r['actor'],r['target'];f=feature_rows[r['id']]
        ta,tb=term_on(members[a],r['date']),term_on(members[b],r['date'])
        f.update(id=r['id'],same_party=float(ta['party']==tb['party']),same_state=float(ta['state']==tb['state']))
        for role,who in [('actor',a),('target',b)]:
            for k in ('d1','d2'):f[role+'_dw'+k[-1]]=members[who].get(k)
            words=assignment[who].get('interview_words')
            f[role+'_log_interview_words']=np.log1p(words) if words is not None else None
            for t in 'EA':f[role+'_'+t]=traits[who].get(t)
        d1a,d1b=members[a].get('d1'),members[b].get('d1')
        f['dw1_distance']=abs(d1a-d1b) if d1a is not None and d1b is not None else None
        for t in 'EAO':
            u,v=traits[a].get(t),traits[b].get(t)
            f['similarity_'+t]=np.exp(-abs(u-v)) if u is not None and v is not None else None
        ea,eb=traits[a].get('E'),traits[b].get('E')
        f['joint_high_E']=sigmoid(ea)*sigmoid(eb) if ea is not None and eb is not None else None
        f['joint_high_E_D']=f['joint_high_E']*f['dw1_distance'] if f['joint_high_E'] is not None and f['dw1_distance'] is not None else None
    save(OUT/'features.json',feature_rows);save(OUT/'work_audit.json',audit)
    expr=matched_expression(read_rows(FROZEN/'development_reviewed_interactions.ndjson'),rows,members,traits)
    save(OUT/'expression_availability.json',expr)
    save(OUT/'coverage_audit.json',dict(assessments=len(rows),unique_pairs=len({tuple(r['pair']) for r in rows}),
        channels={q:dict(assessed=sum(r[q] is not None for r in rows),grades=dict(Counter(str(r[q]) for r in rows if r[q] is not None)),
                       by_chamber={c:sum(r[q] is not None and r['chamber']==c for r in rows) for c in ('House','Senate','cross_chamber')}) for q in ('affinity','friction')},
        neutral_assessments=sum(r['display']=='supported_neutral' for r in rows),
        representative_expression_contrasts=sum(r['status']=='available' for r in expr),
        assessed_low_endpoint_records=sum(any(t in ('low','unrecorded') for t in r['coverage_tiers']) for r in rows if r['affinity'] is not None or r['friction'] is not None),
        selection='Legacy and cue-enriched development evidence; not a probability sample and not population-weighted',
        personality_and_ideology_timing='Fixed retrospective measurements; no historical forecasting claim',
        source_label_leakage='Original-work features precede assessments; existing personality may still include labeling passages',
        independent_interrater_reliability=None))
    (OUT/'PLAN.md').write_text((HERE/'CHAMBER_DEGREES_V6.md').read_text(encoding='utf-8'),encoding='utf-8')
    assert hashes(source_paths)==before;assert verify_lock()['freeze_id']==lock['freeze_id']
    artifacts=[OUT/n for n in ('annotations.ndjson','features.json','work_audit.json','expression_availability.json','coverage_audit.json','PLAN.md')]
    save(OUT/'prefit_manifest.json',dict(prepared_utc=datetime.now(timezone.utc).isoformat(),inputs=before,
        prepared_artifacts=hashes(artifacts),models=MODELS,primary_penalty=1.,chamber_deviation_multiplier=4.,
        cutpoint_penalty=.01,frozen_v5_id=lock['freeze_id'],test_outcomes_used=False,development_only=True))
    print('Prepared v6',len(rows),'dated assessments',flush=True)


def verify_prepared():
    m=read_json(OUT/'prefit_manifest.json')
    for section in ('inputs','prepared_artifacts'):
        for p,h in m[section].items():
            if digest(ROOT/p)!=h:raise ValueError('Prepared input changed: '+p)
    assert verify_lock()['freeze_id']==m['frozen_v5_id']
    return m


def pair_weights(rows,indices):
    counts=Counter(tuple(rows[i]['pair']) for i in indices)
    return np.array([1/counts[tuple(rows[i]['pair'])] for i in indices])


def evaluate(rows,features,dimension,model_spec,penalty):
    names=model_spec['features'];x=np.array([[features[r['id']].get(n) for n in names] for r in rows],dtype=float)
    available=[i for i,r in enumerate(rows) if r[dimension] is not None]
    cache={};predictions=[]
    for held in available:
        train=tuple(i for i in training_indices(rows,held) if rows[i][dimension] is not None)
        if len(train)<3:raise ValueError('Insufficient independent training observations')
        if train not in cache:
            y=[rows[i][dimension] for i in train];ch=[rows[i]['chamber'] for i in train]
            cache[train]=OrdinalDegrees(penalty,model_spec['chamber_slopes']).fit(x[list(train)],y,ch,pair_weights(rows,train))
        model=cache[train];p=model.predict_proba(x[[held]],[rows[held]['chamber']])[0]
        lo,hi=rows[held][dimension+'_range']
        predictions.append(dict(id=rows[held]['id'],pair=rows[held]['pair'],names=rows[held]['names'],date=rows[held]['date'],
            chamber=rows[held]['chamber'],observed_grade=rows[held][dimension],reviewed_range=[lo,hi],
            probability_by_grade=p,expected_grade=p@np.arange(5),
            probability_mass_in_reviewed_range=float(p[lo:hi+1].sum()),
            train_indices=list(train),train_dyads=len({tuple(rows[i]['pair']) for i in train}),
            train_observed_grades=model.observed_grades_,gradient_norm=model.gradient_norm_))
    weights=pair_weights(rows,available)
    metrics=weighted_metrics([p['observed_grade'] for p in predictions],[p['probability_by_grade'] for p in predictions],weights)
    metrics['unique_dyads']=len({tuple(rows[i]['pair']) for i in available})
    metrics['weighted_mass_in_reviewed_range']=float(np.average([p['probability_mass_in_reviewed_range'] for p in predictions],weights=weights))
    by_chamber={}
    for c in ('House','Senate','cross_chamber'):
        idx=[j for j,p in enumerate(predictions) if p['chamber']==c]
        if idx:by_chamber[c]=weighted_metrics([predictions[j]['observed_grade'] for j in idx],
                                            [predictions[j]['probability_by_grade'] for j in idx],weights[idx])
    full=OrdinalDegrees(penalty,model_spec['chamber_slopes']).fit(x[available],[rows[i][dimension] for i in available],
        [rows[i]['chamber'] for i in available],weights)
    return dict(metrics=metrics,by_chamber=by_chamber,predictions=predictions,full_development_model=full.serializable(),
        features=names,unique_fits=len(cache),max_gradient_norm=max([m.gradient_norm_ for m in cache.values()]+[full.gradient_norm_]))


def fit():
    manifest=verify_prepared()
    if (OUT/'model_results.json').exists():raise ValueError('Results exist; preserve this run')
    rows=read_rows(OUT/'annotations.ndjson');features=read_json(OUT/'features.json');results={}
    for name,spec in MODELS.items():
        results[name]={}
        for q in ('affinity','friction'):
            results[name][q]=evaluate(rows,features,q,spec,1.)
            print(name,q,clean_json(results[name][q]['metrics']),flush=True)
        save(OUT/'model_results.json',results)
    sensitivity={}
    for name in ('G2_chamber_context_work','G3_chamber_personality'):
        sensitivity[name]={}
        for penalty in (.3,3.):
            sensitivity[name][str(penalty)]={q:evaluate(rows,features,q,MODELS[name],penalty) for q in ('affinity','friction')}
            print('Sensitivity',name,penalty,flush=True)
        save(OUT/'penalty_sensitivity.json',sensitivity)
    verify_prepared()
    save(OUT/'run_receipt.json',dict(completed_utc=datetime.now(timezone.utc).isoformat(),
        prefit_manifest_sha256=digest(OUT/'prefit_manifest.json'),
        results_sha256=hashes([OUT/'model_results.json',OUT/'penalty_sensitivity.json']),
        development_only=True,frozen_test_unchanged=True,production_changed=False,
        primary_models=5,independent_dimensions=2,neutral_accuracy=None,private_feelings_calibration=None))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','fit','verify'])
    args=parser.parse_args()
    if args.stage=='prepare':prepare()
    elif args.stage=='fit':fit()
    else:print(verify_prepared()['frozen_v5_id'])


if __name__=='__main__':main()
