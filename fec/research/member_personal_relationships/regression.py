"""Auditable, nested multivariable analysis of documented relationship signs.

No production files are changed. Every fitted outcome comes from reviewed
evidence, never from the earlier network rules or an absence of cosponsorship.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import exp
import argparse
import json
import numpy as np
from .data import ROOT, read_json, write_json, write_ndjson, digest
from .run_history import load_all, read_rows

INPUT = ROOT / 'outputs/member_personal_relationships/20260910_full_history'
OUT = ROOT / 'outputs/member_personal_relationships/20260910_regression'
PENALTIES = (.03, .1, .3, 1., 3.)
CONTEXT = ['same_party','same_state','same_chamber','dw1_distance','issue_similarity',
           'actor_leader','target_leader','co_service_congresses']
WORK = ['direct_propensity','reverse_direct_propensity','weighted_shared_jaccard',
        'log_shared_bills','network_proximity']
SIM = ['similarity_E','similarity_A','similarity_O']
LEVEL = ['actor_E','target_E','actor_A','target_A']
VISIBILITY = ['actor_log_interview_words','target_log_interview_words',
              'actor_role_adjusted_visibility','target_role_adjusted_visibility']
MODELS = {
    'context': CONTEXT,
    'context_work': CONTEXT+WORK,
    'work_similarity': CONTEXT+WORK+SIM,
    'work_levels': CONTEXT+WORK+LEVEL,
    'combined': CONTEXT+WORK+SIM+LEVEL,
    'combined_all_five': CONTEXT+WORK+SIM+LEVEL+['similarity_C','similarity_N'],
    'work_visibility': CONTEXT+WORK+VISIBILITY,
    'combined_visibility': CONTEXT+WORK+SIM+LEVEL+VISIBILITY,
    'combined_no_A': CONTEXT+WORK+['similarity_E','similarity_O','actor_E','target_E'],
}


def finite(v):
    return v is not None and np.isfinite(v)


def clean_json(v):
    if isinstance(v,dict): return {str(k):clean_json(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)): return [clean_json(x) for x in v]
    if isinstance(v,(np.integer,)): return int(v)
    if isinstance(v,(float,np.floating)): return float(v) if np.isfinite(v) else None
    if isinstance(v,np.bool_): return bool(v)
    return v


def save(path,v): write_json(path,clean_json(v))


def build_cases(events, include_weak=False):
    groups=defaultdict(list)
    for e in events:
        if e.get('review_status')!='assistant_reviewed' or e.get('sign') not in ('positive','negative'):
            continue
        groups[tuple(sorted((e['actor'],e['target'])))].append(e)
    out=[]
    for pair,rows in sorted(groups.items()):
        # Even a weak conflicting sign prevents a clean binary gold label.
        if len({e['sign'] for e in rows})!=1: continue
        strict=[e for e in rows if e['sign']=='negative' or include_weak or
                e.get('evidence_level','personal_statement')=='personal_statement']
        if not strict: continue
        out.append(dict(pair=list(pair),sign=strict[0]['sign'],y=int(strict[0]['sign']=='positive'),
            directions=[list(p) for p in sorted({(e['actor'],e['target']) for e in strict})],
            families=sorted({e['source_family'] for e in rows}),
            first=min(e['event_date'] for e in strict),last=max(e['event_date'] for e in strict),
            evidence_ids=[e['evidence_id'] for e in strict],
            episodes=sorted({e.get('episode_id',e['source_family']) for e in strict})))
    return out


def training_indices(cases, held, mode='family', pool=None):
    pool=list(range(len(cases))) if pool is None else list(pool)
    endpoints=set(cases[held]['pair']); excluded={held}
    if mode=='members':
        excluded.update(i for i in pool if endpoints.intersection(cases[i]['pair']))
    families={f for i in excluded for f in cases[i]['families']}
    changed=True
    while changed:
        changed=False
        for i in pool:
            if i in excluded or families.intersection(cases[i]['families']):
                before=(len(excluded),len(families))
                excluded.add(i);families.update(cases[i]['families'])
                changed |= before!=(len(excluded),len(families))
    return [i for i in pool if i not in excluded]


def components(cases):
    remaining=set(range(len(cases)));out=[]
    while remaining:
        held=min(remaining)
        group=sorted(set(range(len(cases)))-set(training_indices(cases,held)))
        out.append(group);remaining.difference_update(group)
    return out


def coefficient_names(names): return list(names)+[n+'__missing' for n in names]


class RidgeLogit:
    def __init__(self,penalty=1.): self.penalty=float(penalty)

    def fit(self,x,y,weights=None):
        x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
        if x.ndim!=2 or len(x)!=len(y) or not np.isin(y,[0,1]).all() or len(set(y))!=2:
            raise ValueError('Fit requires two explicit binary classes; unknown is not negative')
        w=np.ones(len(y)) if weights is None else np.asarray(weights,dtype=float)
        if not np.isfinite(w).all() or (w<=0).any(): raise ValueError('Invalid weights')
        w=w/w.sum();valid=np.isfinite(x)
        self.mean_=np.divide((np.where(valid,x,0)*w[:,None]).sum(0),(valid*w[:,None]).sum(0),
                             out=np.zeros(x.shape[1]),where=(valid*w[:,None]).sum(0)>0)
        raw=np.column_stack([np.where(valid,x,self.mean_),~valid]).astype(float)
        self.center_=(raw*w[:,None]).sum(0)
        self.scale_=np.sqrt(((raw-self.center_)**2*w[:,None]).sum(0))
        self.scale_=np.where(self.scale_>1e-8,self.scale_,1.)
        z=np.column_stack([np.ones(len(x)),self.transform(x)])
        reg=np.array([0.]+[self.penalty]*(z.shape[1]-1));beta=np.zeros(z.shape[1])
        beta[0]=np.log((w@y)/(1-w@y))
        def objective(b):
            eta=z@b
            return float(w@(np.logaddexp(0,eta)-y*eta)+.5*np.sum(reg*b*b))
        for iteration in range(100):
            p=self.sigmoid(z@beta)
            grad=z.T@(w*(p-y))+reg*beta
            if max(abs(grad))<1e-9: break
            h=z.T@((w*p*(1-p))[:,None]*z)+np.diag(reg)+np.eye(len(beta))*1e-12
            step=np.linalg.solve(h,grad);old=objective(beta);factor=1.
            while objective(beta-factor*step)>old-1e-4*factor*(grad@step):
                factor*=.5
                if factor<1e-10: break
            beta-=factor*step
        self.beta_=beta;self.iterations_=iteration+1
        self.gradient_norm_=float(max(abs(z.T@(w*(self.sigmoid(z@beta)-y))+reg*beta)))
        if self.gradient_norm_>1e-7: raise ArithmeticError('Logit did not converge')
        return self

    def transform(self,x):
        x=np.asarray(x,dtype=float);valid=np.isfinite(x)
        raw=np.column_stack([np.where(valid,x,self.mean_),~valid]).astype(float)
        return (raw-self.center_)/self.scale_

    @staticmethod
    def sigmoid(eta): return np.exp(-np.logaddexp(0,-np.asarray(eta)))

    def predict(self,x): return self.sigmoid(self.beta_[0]+self.transform(x)@self.beta_[1:])

    def serializable(self):
        return dict(penalty=self.penalty,beta=self.beta_,mean=self.mean_,center=self.center_,scale=self.scale_,
                    iterations=self.iterations_,gradient_norm=self.gradient_norm_)


def metrics(y,p):
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float)
    if len(y)==0:return dict(n=0)
    p=np.clip(p,1e-12,1-1e-12);yes=y==1;pred=p>=.5
    tp=int((pred&yes).sum());tn=int((~pred&~yes).sum())
    fp=int((pred&~yes).sum());fn=int((~pred&yes).sum())
    auc=float(np.mean([(a>b)+.5*(a==b) for a in p[yes] for b in p[~yes]])) if yes.any() and (~yes).any() else None
    return dict(n=len(y),positive=int(yes.sum()),negative=int((~yes).sum()),
        accuracy=float((pred==yes).mean()),balanced_accuracy=.5*(tp/(tp+fn)+tn/(tn+fp)) if tp+fn and tn+fp else None,
        auc=auc,log_loss=float(np.mean(-y*np.log(p)-(1-y)*np.log1p(-p))),
        brier=float(np.mean((p-y)**2)),true_positive=tp,true_negative=tn,false_positive=fp,false_negative=fn,
        positive_recall=tp/(tp+fn) if tp+fn else None,negative_recall=tn/(tn+fp) if tn+fp else None)


class Fitter:
    def __init__(self,cases,x): self.cases=cases;self.x=x;self.cache={}

    def fit(self,indices,penalty,multiplicity=None):
        key=(tuple(indices),penalty)
        if multiplicity is None and key in self.cache:return self.cache[key]
        y=[];w=[];x=[]
        for i in indices:
            n=len(self.x[i]);x.extend(self.x[i]);y.extend([self.cases[i]['y']]*n)
            w.extend([(multiplicity[i] if multiplicity is not None else 1)/n]*n)
        model=RidgeLogit(penalty).fit(x,y,w)
        if multiplicity is None:self.cache[key]=model
        return model

    def select(self,pool,mode,penalties):
        losses={p:[] for p in penalties}
        for held in pool:
            train=training_indices(self.cases,held,mode,pool)
            if len({self.cases[i]['y'] for i in train})!=2:continue
            for penalty in penalties:
                p=float(self.fit(train,penalty).predict(self.x[held]).mean())
                losses[penalty].append(metrics([self.cases[held]['y']],[p])['log_loss'])
        means={p:float(np.mean(v)) for p,v in losses.items() if v}
        selected=min(means,key=lambda p:(means[p],-p)) if means else 1.
        return selected,means,min((len(v) for v in losses.values()),default=0)


def nested_cv(cases,x,mode='family',penalties=PENALTIES):
    fitter=Fitter(cases,x);rows=[]
    for held,c in enumerate(cases):
        train=training_indices(cases,held,mode)
        if len({cases[i]['y'] for i in train})!=2:raise ValueError('Outer fold has only one class')
        penalty,inner,count=fitter.select(train,mode,penalties)
        model=fitter.fit(train,penalty);p=float(model.predict(x[held]).mean())
        rows.append(dict(pair=c['pair'],sign=c['sign'],y=c['y'],p=p,train_cases=train,
                         penalty=penalty,inner_log_loss=inner,inner_scored_pairs=count))
    return dict(metrics=metrics([c['y'] for c in cases],[r['p'] for r in rows]),predictions=rows,
                penalty_counts=dict(Counter(str(r['penalty']) for r in rows)),unique_fits=len(fitter.cache))


def normalized_keys(d):
    from .data import normalize
    return {' '.join(normalize(k).split()):v for k,v in d.items()}


def lookup(d,name):
    from .data import normalize
    return d.get(' '.join(normalize(name).split()),{})


def source_profiles(members,composite):
    blue=read_json(ROOT/'data/members/big5_blue_validated.json')
    pink=read_json(ROOT/'data/members/big5_llm_opus.json')
    b=normalized_keys(blue['traits']);p=normalized_keys(pink['traits']);g=normalized_keys(pink['genre_scores'])
    sources={'composite':composite,'text_only':{},'observer_only':{},'floor_observer':{},'interview_observer':{}}
    for a,m in members.items():
        sources['text_only'][a]={t:lookup(b,m['name']).get(t) for t in 'OCEAN'}
        z=lookup(p,m['name']).get('raw_z',{})
        sources['observer_only'][a]={t:(-z['ES'] if t=='N' and finite(z.get('ES')) else z.get(t)) for t in 'OCEAN'}
        for name,genre in [('floor_observer','CREC'),('interview_observer','INTERVIEW')]:
            r=lookup(g,m['name']).get(genre,{})
            sources[name][a]={t:(-r['ES'] if t=='N' and finite(r.get('ES')) else r.get(t)) for t in 'OCEAN'}
    # Source-specific trait units use the fixed measurement roster, without tie labels.
    for source in ('floor_observer','interview_observer'):
        for t in 'OCEAN':
            values=[v[t] for v in sources[source].values() if finite(v[t])]
            mean,sd=np.mean(values),np.std(values)
            for v in sources[source].values():
                if finite(v[t]):v[t]=(v[t]-mean)/sd if sd>1e-8 else 0.
    return sources


def features(a,b,members,traits,index,w,communication):
    i,j=index[a],index[b];ma,mb=members[a],members[b];ta,tb=traits[a],traits[b]
    d=dict(same_party=float(ma['party']==mb['party']),same_state=float(ma['state']==mb['state']),
        same_chamber=float(ma['chamber']==mb['chamber']),
        dw1_distance=abs(ma['d1']-mb['d1']) if finite(ma.get('d1')) and finite(mb.get('d1')) else None,
        actor_leader=float(ma['leader']),target_leader=float(mb['leader']),
        issue_similarity=w['issue_similarity'][i,j],co_service_congresses=w['co_service_congresses'][i,j],
        direct_propensity=w['direct_rate'][i,j],reverse_direct_propensity=w['direct_rate'][j,i],
        weighted_shared_jaccard=w['weighted_jaccard'][i,j],log_shared_bills=np.log1p(w['shared'][i,j]),
        network_proximity=w['network_proximity'][i,j])
    for t in 'OCEAN':
        d['similarity_'+t]=exp(-abs(ta[t]-tb[t])) if finite(ta.get(t)) and finite(tb.get(t)) else None
        d['actor_'+t]=ta.get(t);d['target_'+t]=tb.get(t)
    for label,m in [('actor',ma),('target',mb)]:
        c=lookup(communication,m['name']);raw=c.get('raw_text',{});v=raw.get('interview_words')
        d[label+'_log_interview_words']=np.log1p(v) if finite(v) else None
        d[label+'_role_adjusted_visibility']=c.get('public_exposure',{}).get('role_adjusted_visibility_z')
    return d


def matrices(cases,names,feature_rows,symmetric=False):
    out=[]
    for c in cases:
        dirs=c['directions'] if not symmetric else [c['pair'],list(reversed(c['pair']))]
        raw=np.array([[feature_rows[tuple(pair)].get(n) for n in names] for pair in dirs],dtype=float)
        if symmetric:
            count=np.isfinite(raw).sum(0)
            raw=np.divide(np.where(np.isfinite(raw),raw,0).sum(0),count,
                          out=np.full(raw.shape[1],np.nan),where=count>0)[None,:]
        out.append(raw)
    return out


def stability(cases,x,names,penalty,n_boot=500,seed=1947):
    fitter=Fitter(cases,x);all_indices=list(range(len(cases)));full=fitter.fit(all_indices,penalty)
    rng=np.random.default_rng(seed);groups=components(cases);betas=[]
    for _ in range(n_boot):
        counts=Counter(i for k in rng.integers(0,len(groups),len(groups)) for i in groups[k])
        indices=sorted(counts)
        if len({cases[i]['y'] for i in indices})<2:continue
        m=fitter.fit(indices,penalty,counts)
        # Put bootstrap effects on the original full-sample standard deviation.
        betas.append(m.beta_[1:]/m.scale_*full.scale_)
    betas=np.array(betas);coeff=[]
    for k,n in enumerate(coefficient_names(names)):
        lo,hi=np.quantile(betas[:,k],[.025,.975])
        coeff.append(dict(feature=n,beta=full.beta_[k+1],odds_ratio=np.exp(full.beta_[k+1]),
            stability_beta_low=lo,stability_beta_high=hi,
            stability_or_low=np.exp(lo),stability_or_high=np.exp(hi),
            bootstrap_positive_fraction=float(np.mean(betas[:,k]>0)),
            scale=full.scale_[k],center=full.center_[k]))
    return dict(model=full.serializable(),features=coefficient_names(names),coefficients=coeff,
                bootstrap_n=len(betas),source_components=len(groups),
                in_sample=metrics([c['y'] for c in cases],[float(full.predict(v).mean()) for v in x]))


def audit(cases,events,members,traits,rows,communication,results):
    used={a for c in cases for a in c['pair']};counts=Counter(a for c in cases for a in c['pair'])
    categories=defaultdict(lambda:Counter())
    for c in cases:
        a,b=c['pair'];ma,mb=members[a],members[b]
        for k in [f"chamber:{ma['chamber'] if ma['chamber']==mb['chamber'] else 'mixed'}",
                  f"party:{'same' if ma['party']==mb['party'] else 'different'}",
                  f"state:{'same' if ma['state']==mb['state'] else 'different'}",
                  f"leader:{bool(ma['leader'] or mb['leader'])}"]:
            categories[k][c['sign']]+=1
    source_counts=defaultdict(Counter)
    ids={e for c in cases for e in c['evidence_ids']}
    for e in events:
        if e['evidence_id'] in ids:
            urls=' '.join(e.get('source_urls',[]))
            source=e.get('source') or ('CREC' if 'CREC-' in urls else 'INTERVIEW' if 'transcripts.cnn' in urls else 'media_or_official_web')
            source_counts[source][e['sign']]+=1
    def coverage(pool):
        return {t:dict(n=sum(finite(traits[a].get(t)) for a in pool),total=len(pool)) for t in 'OCEAN'}
    def visibility(pool):
        values=[lookup(communication,members[a]['name']).get('raw_text',{}).get('interview_words') for a in pool]
        return dict(median_interview_words=float(np.median([v for v in values if finite(v)])))
    x=matrices(cases,MODELS['combined'],rows)
    # Pair means serve this diagnostic only; model training retains documented directions.
    means=[]
    for v in x:
        count=np.isfinite(v).sum(0)
        means.append(np.divide(np.where(np.isfinite(v),v,0).sum(0),count,out=np.full(v.shape[1],np.nan),where=count>0))
    pair_x=np.array(means);corr=[]
    for i,a in enumerate(MODELS['combined']):
        for j in range(i+1,pair_x.shape[1]):
            ok=np.isfinite(pair_x[:,i])&np.isfinite(pair_x[:,j]);v=pair_x[ok][:,[i,j]]
            if len(v)>=5 and min(v.std(0))>1e-8:
                r=float(np.corrcoef(v.T)[0,1])
                if abs(r)>=.7:corr.append(dict(a=a,b=MODELS['combined'][j],r=r,n=int(ok.sum())))
    subgroup={}
    for mode in ['family','members']:
        preds=results['combined'][mode]['predictions'];sg={}
        for category in categories:
            selected=[]
            for i,c in enumerate(cases):
                a,b=c['pair'];ma,mb=members[a],members[b]
                keys=[f"chamber:{ma['chamber'] if ma['chamber']==mb['chamber'] else 'mixed'}",
                    f"party:{'same' if ma['party']==mb['party'] else 'different'}",
                    f"state:{'same' if ma['state']==mb['state'] else 'different'}",
                    f"leader:{bool(ma['leader'] or mb['leader'])}"]
                if category in keys:selected.append(i)
            sg[category]=metrics([cases[i]['y'] for i in selected],[preds[i]['p'] for i in selected])
        subgroup[mode]=sg
    gold=read_json(ROOT/'data/stance/big5_gold_anchored.json')
    validation={t:{k:v for k,v in row.items() if k in ['status','coverage_n','selected_weights','supporting_panels','strict_discriminant_panels']}|
                    {'panels':row['validation']['panels']} for t,row in gold['traits'].items()}
    return dict(pairs=len(cases),directions=sum(len(c['directions']) for c in cases),
        positive=sum(c['y'] for c in cases),negative=sum(1-c['y'] for c in cases),
        distinct_members=len(used),source_components=len(components(cases)),
        composition=dict(categories),source_event_counts=dict(source_counts),
        member_frequency=[dict(id=a,name=members[a]['name'],pairs=n,negative_pairs=sum(a in c['pair'] and not c['y'] for c in cases))
                          for a,n in counts.most_common()],
        label_member_coverage=coverage(used),roster_coverage=coverage(list(members)),
        label_visibility=visibility(used),roster_visibility=visibility(list(members)),
        pair_feature_missing={n:int(np.sum(~np.isfinite(pair_x[:,i]))) for i,n in enumerate(MODELS['combined'])},
        high_feature_correlations=sorted(corr,key=lambda v:-abs(v['r'])),subgroups=subgroup,
        personality_validation=validation,first_event=min(c['first'] for c in cases),last_event=max(c['last'] for c in cases))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bootstrap',type=int,default=500)
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    source_files=[INPUT/f for f in ['members.json','traits.json','work_matrices.npz','matrix_index.json','reviewed_events.ndjson']]
    source_files += [ROOT/f for f in ['data/members/big5_blue_validated.json','data/members/big5_llm_opus.json',
                                     'communication_style.json','data/stance/big5_gold_anchored.json']]
    hashes={str(p.relative_to(ROOT)):digest(p) for p in source_files}
    save(OUT/'analysis_spec.json',dict(started_utc=datetime.now(timezone.utc).isoformat(),models=MODELS,
        penalties=PENALTIES,plan_sha256=digest(ROOT/'fec/research/member_personal_relationships/REGRESSION_PLAN.md'),
        inputs=hashes,bootstrap=args.bootstrap,endpoint='positive vs negative among documented ties',
        primary_model='combined',source='composite',primary_validation='members',secondary_validation='family'))
    members,traits,ids,w=load_all();index={a:i for i,a in enumerate(ids)}
    events=read_rows(INPUT/'reviewed_events.ndjson');cases=build_cases(events)
    for c in cases:c['names']=[members[a]['name'] for a in c['pair']]
    save(OUT/'cases.json',cases)
    communication=normalized_keys(read_json(ROOT/'communication_style.json')['members'])
    profiles=source_profiles(members,traits)
    allcases=build_cases(events,True);pairs={tuple(c['pair']) for c in allcases}
    pairs |= {(b,a) for a,b in list(pairs)}
    feature_sets={source:{(a,b):features(a,b,members,t,index,w,communication) for a,b in pairs} for source,t in profiles.items()}
    save(OUT/'features.json',{s:[dict(actor=a,target=b,**clean_json(r)) for (a,b),r in sorted(rows.items())] for s,rows in feature_sets.items()})
    rows=feature_sets['composite'];results={}
    for name,names in MODELS.items():
        x=matrices(cases,names,rows);results[name]={}
        for mode in ['family','members']:
            print('Fitting',name,mode,flush=True)
            results[name][mode]=nested_cv(cases,x,mode)
            print(results[name][mode]['metrics'],flush=True)
        save(OUT/'model_results.json',results)
    baseline={}
    for mode in ['family','members']:
        p=[float(np.mean([cases[j]['y'] for j in training_indices(cases,i,mode)])) for i in range(len(cases))]
        baseline[mode]=metrics([c['y'] for c in cases],p)
    save(OUT/'baseline.json',dict(fold_training_prevalence=baseline,constant_majority_accuracy=sum(c['y'] for c in cases)/len(cases)))
    sensitivities={}
    def run_sensitivity(name,subset,source='composite',symmetric=False,models=('context_work','combined')):
        print('Sensitivity',name,'pairs',len(subset),flush=True)
        sensitivities[name]={}
        for model_name in models:
            x=matrices(subset,MODELS[model_name],feature_sets[source],symmetric)
            sensitivities[name][model_name]={mode:nested_cv(subset,x,mode) for mode in ['family','members']}
        save(OUT/'sensitivity_results.json',sensitivities)
    for source in ['text_only','observer_only','floor_observer','interview_observer']:
        run_sensitivity(source,cases,source,models=('combined',))
    run_sensitivity('unordered_features',cases,symmetric=True)
    run_sensitivity('weak_warmth_included',allcases)
    weak_episodes={'comer_jeffries_20251120','cruz_mcconnell_20150724'}
    # Match event labels robustly by endpoints; inspect/export exactly what is excluded.
    weak_pairs={tuple(sorted(('C001108','J000294'))),tuple(sorted(('C001098','M000355')))}
    robust=[c for c in cases if tuple(c['pair']) not in weak_pairs]
    run_sensitivity('exclude_strategic_or_secondhand_negative',robust)
    counts=Counter(a for c in cases for a in c['pair'])
    most_negative=Counter(a for c in cases if not c['y'] for a in c['pair'])
    influence_ids=list(dict.fromkeys([most_negative.most_common(1)[0][0]]+[a for a,n in counts.most_common(3)]))
    for a in influence_ids:run_sensitivity('exclude_member_'+a,[c for c in cases if a not in c['pair']])
    # Source comparison on an identical complete-case set avoids different missingness masks.
    sources_to_compare=['composite','text_only','observer_only']
    complete=[c for c in cases if all(all(finite(feature_sets[s][tuple(d)].get(n)) for n in SIM+LEVEL)
              for s in sources_to_compare for d in c['directions'])]
    for source in sources_to_compare:run_sensitivity('common_complete_'+source,complete,source)
    x=matrices(cases,MODELS['combined'],rows);fitter=Fitter(cases,x)
    penalty,loss,count=fitter.select(list(range(len(cases))),'family',PENALTIES)
    print('Final coefficients and bootstrap',penalty,flush=True)
    coef=stability(cases,x,MODELS['combined'],penalty,args.bootstrap)
    coef.update(selection_log_loss=loss,selection_scored_pairs=count)
    save(OUT/'coefficients.json',coef)
    save(OUT/'bias_audit.json',audit(cases,events,members,traits,rows,communication,results))
    after={str(p.relative_to(ROOT)):digest(p) for p in source_files}
    if hashes!=after:raise RuntimeError('Input sources changed during analysis; rerun from a fixed snapshot')
    save(OUT/'run_receipt.json',dict(finished_utc=datetime.now(timezone.utc).isoformat(),inputs_unchanged=True,
         inputs=hashes,code_sha256=digest(__file__),models=len(MODELS),sensitivity_sets=list(sensitivities),
         strict_pairs=len(cases),weak_included_pairs=len(allcases),common_complete_pairs=len(complete),
         excluded_negative_pairs=[c for c in cases if tuple(c['pair']) in weak_pairs],
         influence_members=[dict(id=a,name=members[a]['name']) for a in influence_ids]))
    print('Saved',OUT,flush=True)


if __name__=='__main__':main()
