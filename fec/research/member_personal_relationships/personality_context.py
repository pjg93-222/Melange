"""Development-only test of similarity x politics x bipartisan-work interactions."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
from itertools import combinations
from pathlib import Path
import numpy as np
from .data import ROOT,read_json,write_json,write_ndjson,digest
from .run_history import load_all,read_rows
from .regression import (MODELS as OLD_MODELS,SIM,PENALTIES,finite,clean_json,save,
                         matrices,nested_cv,Fitter,components,metrics)
from .regression_bias_controls import EXTRA
from .regression_diagnostics import leave_two_cases_out,resample_oof
from .freeze_v5 import verify_lock

HERE=Path(__file__).resolve().parent
OLD=ROOT/'outputs/member_personal_relationships/20260910_regression'
INPUT=ROOT/'outputs/member_personal_relationships/20260910_full_history'
OUT=ROOT/'outputs/member_personal_relationships/20260910_personality_context'
BASE=OLD_MODELS['combined_visibility']+EXTRA+['bipartisan_pair']
MODELS={'R0_main_effects':BASE,'R1_similarity_distance':BASE+['S_D'],
        'R2_distance_bipartisanship':BASE+['S_D','S_B','D_B','S_D_B'],
        'R3_party_bipartisanship':BASE+['S_P','S_B','P_B','S_P_B']}


def pair_similarity(a,b,traits,letters='EAO'):
    if not all(finite(traits[x].get(t)) for x in (a,b) for t in letters):
        return None
    return float(np.mean([np.exp(-abs(traits[a][t]-traits[b][t])) for t in letters]))


def bipartisan_propensity(i,j,ids,members,w):
    """Exclude focal partner in both opportunity groups; unknown never means centrist."""
    party=members[ids[i]]['party']
    if party not in ('Democrat','Republican'):
        return dict(value=None,reason='independent_or_other_party_not_recoded',counts={})
    counts={}
    for group in ('same','cross'):
        js=[k for k,a in enumerate(ids) if k not in (i,j)
            and members[a]['party'] in ('Democrat','Republican')
            and (members[a]['party']==party)==(group=='same')]
        joined=float(np.nansum(w['direct'][i,js]))
        opportunity=float(np.nansum(w['direct_opportunities'][i,js]))
        if joined > opportunity+1e-8:
            raise ValueError('Joins exceed eligible bill opportunities')
        counts[group]=dict(joins=joined,opportunities=opportunity,
            rate=joined/opportunity if opportunity else None,
            smoothed_rate=(joined+.5)/(opportunity+1) if opportunity else None)
    if not all(c['opportunities']>0 for c in counts.values()) or not sum(c['joins'] for c in counts.values()):
        return dict(value=None,reason='insufficient_observed_work',counts=counts)
    cross=counts['cross']['smoothed_rate'];same=counts['same']['smoothed_rate']
    return dict(value=cross/(cross+same),reason=None,counts=counts,
                raw_cross_signature_share=counts['cross']['joins']/sum(c['joins'] for c in counts.values()))


def interaction_features(S,D,P,B):
    def product(*values):
        return float(np.prod(values)) if all(finite(v) for v in values) else None
    return dict(S_D=product(S,D),S_B=product(S,B),D_B=product(D,B),S_D_B=product(S,D,B),
                S_P=product(S,P),P_B=product(P,B),S_P_B=product(S,P,B))


def add_features(cases,members,traits,ids,w,old_rows):
    index={a:i for i,a in enumerate(ids)};rows={};pair_rows=[]
    for case in cases:
        a,b=case['pair'];S=pair_similarity(a,b,traits)
        ia,ib=index[a],index[b]
        ba=bipartisan_propensity(ia,ib,ids,members,w)
        bb=bipartisan_propensity(ib,ia,ids,members,w)
        B=(ba['value']+bb['value'])/2 if ba['value'] is not None and bb['value'] is not None else None
        D=abs(members[a]['d1']-members[b]['d1']) if finite(members[a].get('d1')) and finite(members[b].get('d1')) else None
        P=float(members[a]['party']!=members[b]['party'])
        inter=interaction_features(S,D,P,B)
        pair_rows.append(dict(pair=case['pair'],names=case['names'],sign=case['sign'],y=case['y'],
            EAO_similarity=S,all_five_similarity=pair_similarity(a,b,traits,'OCEAN'),
            trait_similarities={t:pair_similarity(a,b,traits,t) for t in 'OCEAN'},
            ideology_distance=D,different_party=P,bipartisan_pair=B,
            bipartisan_lower_endpoint=min(ba['value'],bb['value']) if B is not None else None,
            bipartisan_endpoints={a:ba,b:bb},traits={a:traits[a],b:traits[b]},
            shared_bills=float(w['shared'][ia,ib]),**inter))
        for actor,target in case['directions']:
            row=dict(old_rows[(actor,target)])
            for prefix,who in [('actor',actor),('target',target)]:
                row[prefix+'_dw1']=members[who].get('d1');row[prefix+'_dw2']=members[who].get('d2')
                row[prefix+'_republican']=float(members[who]['party']=='Republican')
                row[prefix+'_senator']=float(members[who]['chamber']=='Senate')
            row.update(bipartisan_pair=B,EAO_similarity=S,**inter)
            rows[(actor,target)]=row
    return rows,pair_rows


def profile_description(members,traits,ids,w):
    names={m['name']:a for a,m in members.items()}
    a,b=names['Nancy Mace'],names['Jasmine Crockett']
    table=[]
    for t in 'OCEAN':
        population=np.asarray([traits[k][t] for k in ids if finite(traits[k].get(t))])
        row=dict(trait=t,Nancy_Mace=traits[a][t],Jasmine_Crockett=traits[b][t],
                 absolute_difference=abs(traits[a][t]-traits[b][t]),observed_roster_n=len(population))
        for label,key in [('Mace',a),('Crockett',b)]:
            value=traits[key][t]
            row[label+'_percentile']=float(np.mean(population<value)+.5*np.mean(population==value))
        table.append(row)
    similarities={}
    for letters in ('EAO','OCEAN'):
        population=[pair_similarity(x,y,traits,letters) for x,y in combinations(ids,2)]
        population=np.asarray([v for v in population if v is not None]);value=pair_similarity(a,b,traits,letters)
        similarities[letters]=dict(value=value,percentile=float(np.mean(population<value)+.5*np.mean(population==value)),
                                   complete_pairs=len(population))
    return dict(pair=[a,b],traits=table,similarities=similarities,
                ideology_distance=abs(members[a]['d1']-members[b]['d1']),
                reading='Same direction of some traits, but not a particularly close numerical personality match')


def describe_groups(pair_rows):
    groups={}
    for P in (0,1):
        for y in (0,1):
            rows=[r for r in pair_rows if r['different_party']==P and r['y']==y]
            cols=['EAO_similarity','all_five_similarity','ideology_distance','bipartisan_pair']
            values={}
            for k in cols:
                observed=[r[k] for r in rows if finite(r[k])]
                values[k]=dict(observed_n=len(observed),median=float(np.median(observed)) if observed else None)
            groups[f'{"cross_party" if P else "same_party"}_{"positive" if y else "negative"}']=dict(n=len(rows),**values)
    return groups


def raw_coefficients(model,names):
    return {name:float(model.beta_[k+1]/model.scale_[k]) for k,name in enumerate(names)}


def moderation(raw,name,B):
    return raw.get('S_'+name,0.)+B*raw.get('S_'+name+'_B',0.)


def fit_stability(cases,x,names,kind,b_quantiles,n=300):
    fitter=Fitter(cases,x);indices=list(range(len(cases)))
    penalty,inner,count=fitter.select(indices,'members',PENALTIES)
    model=fitter.fit(indices,penalty);raw=raw_coefficients(model,names)
    groups=components(cases);rng=np.random.default_rng(610923);draws=[]
    for _ in range(n):
        multiplicity=Counter(i for k in rng.integers(0,len(groups),len(groups)) for i in groups[k])
        train=sorted(multiplicity)
        if len({cases[k]['y'] for k in train})<2:
            continue
        fit=fitter.fit(train,penalty,multiplicity);coef=raw_coefficients(fit,names)
        draws.append({k:coef[k] for k in names if k.startswith('S_') or k in ('D_B','P_B')}|
                     {'moderation_low_B':moderation(coef,kind,b_quantiles[0]),
                      'moderation_high_B':moderation(coef,kind,b_quantiles[1])})
    effects={}
    for k in draws[0]:
        values=np.array([d[k] for d in draws])
        point=(moderation(raw,kind,b_quantiles[0]) if k=='moderation_low_B' else
               moderation(raw,kind,b_quantiles[1]) if k=='moderation_high_B' else raw[k])
        effects[k]=dict(raw_coefficient_or_moderation=point,stability_interval=np.quantile(values,[.025,.5,.975]),
                       positive_fraction=float(np.mean(values>0)))
    return dict(penalty=penalty,inner_log_loss=inner,inner_scored_pairs=count,
                model=model.serializable(),raw_coefficients=raw,interaction_effects=effects,
                resamples=len(draws),bipartisan_quartiles=b_quantiles,
                resampling='Source components at fixed penalty; descriptive stability, not valid confidence intervals',
                in_sample=metrics([c['y'] for c in cases],[float(model.predict(v).mean()) for v in x]))


def main():
    frozen=verify_lock()
    if OUT.exists() and any(OUT.iterdir()):
        raise ValueError('Exploration output already exists; inspect it rather than silently refitting')
    sources=[HERE/'PERSONALITY_CONTEXT_EXPLORATION.md',Path(__file__),
             HERE/'regression.py',HERE/'regression_diagnostics.py',HERE/'regression_bias_controls.py',
             INPUT/'members.json',INPUT/'traits.json',INPUT/'work_matrices.npz',
             OLD/'cases.json',OLD/'features.json']
    hashes={str(p.relative_to(ROOT)):digest(p) for p in sources}
    OUT.mkdir(parents=True,exist_ok=False)
    spec=dict(started_utc=datetime.now(timezone.utc).isoformat(),inputs=hashes,models=MODELS,
              penalties=PENALTIES,development_only=True,previous_outcomes_already_inspected=True,
              frozen_test_unchanged=frozen['freeze_id'],new_test_outcomes_used=False,
              hypothesis='Similarity may interact with ideological/party separation; bipartisan work may moderate that interaction')
    save(OUT/'analysis_spec.json',spec)
    (OUT/'PLAN.md').write_text((HERE/'PERSONALITY_CONTEXT_EXPLORATION.md').read_text(encoding='utf-8'),encoding='utf-8')
    members,traits,ids,w=load_all();cases=read_json(OLD/'cases.json')
    old_rows={(r['actor'],r['target']):r for r in read_json(OLD/'features.json')['composite']}
    rows,pairs=add_features(cases,members,traits,ids,w,old_rows)
    save(OUT/'cases.json',cases);save(OUT/'features.json',list(rows.values()));save(OUT/'pair_descriptions.json',pairs)
    save(OUT/'mace_crockett_profile.json',profile_description(members,traits,ids,w))
    save(OUT/'group_descriptions.json',describe_groups(pairs))
    frame=read_json(ROOT/'outputs/member_personal_relationships/20260910_frozen_v5/member_assignment.json')
    if any(frame[a]['split']!='development' for c in cases for a in c['pair']):
        raise ValueError('A frozen test member entered the development exploration')
    results={};ranking={};sensitivity={}
    trigger={a for a,m in members.items() if m['name'] in ('Nancy Mace','Jasmine Crockett')}
    reduced=[c for c in cases if not trigger.intersection(c['pair'])]
    bq=np.quantile([p['bipartisan_pair'] for p in pairs if p['bipartisan_pair'] is not None],[.25,.75])
    fitted={}
    for name,names in MODELS.items():
        print('Fitting',name,'features',len(names),flush=True)
        x=matrices(cases,names,rows)
        results[name]=nested_cv(cases,x,'members')
        save(OUT/'model_results.json',results)
        print(name,results[name]['metrics'],flush=True)
        ranking[name]=leave_two_cases_out(cases,x,'members')
        save(OUT/'same_fit_auc.json',ranking)
        print(name,'same-fit AUC',ranking[name]['auc'],flush=True)
        sensitivity[name]=nested_cv(reduced,matrices(reduced,names,rows),'members')
        save(OUT/'without_mace_crockett.json',sensitivity)
        kind='P' if name.startswith('R3') else 'D'
        fitted[name]=fit_stability(cases,x,names,kind,bq)
        save(OUT/'coefficient_stability.json',fitted)
    gains={}
    for name in list(MODELS)[1:]:
        gains[name]=resample_oof(cases,{'context_work':results['R0_main_effects'],'combined':results[name]},n=2000)
    save(OUT/'gain_stability.json',gains)
    assert all(digest(ROOT/p)==h for p,h in hashes.items()),'Exploration inputs changed while fitting'
    assert verify_lock()['freeze_id']==frozen['freeze_id']
    save(OUT/'run_receipt.json',dict(finished_utc=datetime.now(timezone.utc).isoformat(),inputs=hashes,
        models=list(MODELS),cases=len(cases),positive=sum(c['y'] for c in cases),
        development_only=True,old_regression_unchanged=True,frozen_test_unchanged=True,
        test_outcomes_used=False,same_fit_comparisons={k:v['comparisons'] for k,v in ranking.items()},
        deleted_motivating_member_cases=len(cases)-len(reduced)))


if __name__=='__main__':main()
