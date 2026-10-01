"""Explicit follow-up to the observed ideology/personality correlations."""
import numpy as np
from .regression import (ROOT,OUT,INPUT,MODELS,VISIBILITY,read_json,save,finite,lookup,normalized_keys,
    matrices,nested_cv,Fitter,PENALTIES,stability,digest)
from .regression_diagnostics import leave_two_cases_out,resample_oof

EXTRA=['actor_dw1','target_dw1','actor_dw2','target_dw2','actor_republican','target_republican',
       'actor_senator','target_senator']


def main():
    members=read_json(INPUT/'members.json');traits=read_json(INPUT/'traits.json')
    communication=normalized_keys(read_json(ROOT/'communication_style.json')['members'])
    cases=read_json(OUT/'cases.json');rows={(r['actor'],r['target']):r for r in read_json(OUT/'features.json')['composite']}
    for (a,b),r in rows.items():
        for label,person in [('actor',members[a]),('target',members[b])]:
            r[label+'_dw1']=person.get('d1');r[label+'_dw2']=person.get('d2')
            r[label+'_republican']=float(person['party']=='Republican')
            r[label+'_senator']=float(person['chamber']=='Senate')
    correlations={}
    for t in 'OCEAN':
        groups={};corr={}
        for party in sorted({m['party'] for m in members.values()}):
            values=[traits[a][t] for a,m in members.items() if m['party']==party and finite(traits[a].get(t))]
            groups[party]=dict(n=len(values),mean=np.mean(values) if values else None)
        for k in ['dw1','log_interview_words']:
            values=[]
            for a,m in members.items():
                v=m.get('d1') if k=='dw1' else lookup(communication,m['name']).get('raw_text',{}).get('interview_words')
                if finite(v) and finite(traits[a].get(t)):
                    values.append((traits[a][t],np.log1p(v) if k=='log_interview_words' else v))
            corr[k]=dict(n=len(values),r=float(np.corrcoef(np.array(values).T)[0,1]))
        correlations[t]=dict(correlations=corr,party_means=groups)
    save(OUT/'trait_bias_correlations.json',correlations)
    names={'expanded_work':MODELS['context_work']+EXTRA,'expanded_combined':MODELS['combined']+EXTRA,
           'expanded_work_visibility':MODELS['context_work']+EXTRA+VISIBILITY,
           'expanded_combined_visibility':MODELS['combined']+EXTRA+VISIBILITY}
    save(OUT/'expanded_controls_spec.json',dict(post_fit_diagnostic=True,models=names,
        reason='Pairwise absolute ideology distance and same-party status do not control each endpoint ideology or chamber. Added after observing trait/ideology correlations.',
        no_causal_or_complete_geography_claim=True))
    results={};ranking={}
    for name,cols in names.items():
        print('Expanded controls',name,flush=True);x=matrices(cases,cols,rows)
        results[name]={mode:nested_cv(cases,x,mode) for mode in ['family','members']}
        print(name,results[name]['members']['metrics'],flush=True)
        save(OUT/'expanded_controls_results.json',results)
        ranking[name]=leave_two_cases_out(cases,x,'members')
        print('Same-fit AUC',ranking[name]['auc'],flush=True)
        save(OUT/'expanded_controls_same_fit_auc.json',ranking)
    for name in ['expanded_combined','expanded_combined_visibility']:
        x=matrices(cases,names[name],rows);fitter=Fitter(cases,x)
        penalty,loss,count=fitter.select(list(range(len(cases))),'family',PENALTIES)
        fit=stability(cases,x,names[name],penalty)
        fit.update(selection_log_loss=loss,selection_scored_pairs=count)
        save(OUT/(name+'_coefficients.json'),fit)
    save(OUT/'expanded_controls_stability.json',resample_oof(cases,
        {'context_work':results['expanded_work']['members'],'combined':results['expanded_combined']['members']}))
    save(OUT/'expanded_controls_receipt.json',dict(code_sha256=digest(__file__),models=list(names),
        all_comparisons_scored=all(v['comparisons']==180 for v in ranking.values())))


if __name__=='__main__':main()
