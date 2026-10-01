"""Development-only original cosponsorship and trait-specific investigation."""
from collections import Counter
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
import json
import os
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
from .data import ROOT, read_json, digest
from .run_history import load_all, read_rows
from .history_work import full_work, network_proximity, served_on
from .personality_context import (MODELS as PREVIOUS_MODELS, add_features,
    raw_coefficients, describe_groups)
from .regression import save, finite, matrices, nested_cv, Fitter, PENALTIES, components
from .regression_diagnostics import leave_two_cases_out, resample_oof
from .freeze_v5 import verify_lock

HERE=Path(__file__).resolve().parent
INPUT=ROOT/'outputs/member_personal_relationships/20260910_full_history'
OLD=ROOT/'outputs/member_personal_relationships/20260910_regression'
PREVIOUS=ROOT/'outputs/member_personal_relationships/20260910_personality_context'
OUT=ROOT/'outputs/member_personal_relationships/20260910_original_work_context'
MODELS={k:list(v) for k,v in PREVIOUS_MODELS.items()}
BASE=MODELS['R0_main_effects']
MODELS.update(R4_separate_traits=BASE+['similarity_E_D','similarity_A_D','similarity_O_D'],
              R5_joint_low_agreeableness=BASE+['joint_low_A','joint_low_A_D'],
              R6_joint_high_extraversion=BASE+['joint_high_E','joint_high_E_D'])


def original_panel(bills,members):
    """Adapt the proven matrix builder to introduction-day eligibility."""
    panel=[];audit=Counter();details=[]
    for b in bills:
        original=set(b['original'])
        if not original.issubset(b['joins']):raise ValueError('Original flag without a valid signature')
        retained={a for a in original if a!=b['sponsor'] and
                  (a not in members or served_on(members[a],b['introduced'],b['chamber']))}
        for a in original-retained:
            details.append(dict(bill=b['key'],member=a,reason='not_eligible_at_introduction'))
        joins={a:d for a,d in b['joins'].items() if a in retained}
        withdrawals={a:d for a,d in b['withdrawals'].items() if a in retained}
        audit['bills']+=1;audit['all_valid_signatures']+=len(b['joins'])
        audit['original_signatures']+=len(joins)
        audit['original_roster_signatures']+=sum(a in members for a in joins)
        audit['original_withdrawals']+=len(withdrawals)
        audit['bills_with_originals']+=bool(joins)
        audit['original_non_introduction_dates']+=sum(d!=b['introduced'] for d in joins.values())
        # A one-day interval implements served_on(introduced), not a join cutoff.
        panel.append(dict(b,joins=joins,original=sorted(retained),withdrawals=withdrawals,
            size=len(joins),end=(date.fromisoformat(b['introduced'])+timedelta(days=1)).isoformat()))
    return panel,dict(audit),details


def audit_xml_flags():
    """Verify upstream missingness without changing the frozen extraction."""
    manifest=read_json(ROOT/'outputs/cosponsor_challengers_20260905/data_audit.json')
    receipts=[];totals=Counter();anomalies=[];changed=[]
    for source in manifest['sources']:
        if not source['path'].lower().endswith('.zip'):continue
        path=Path(source['path']);before=digest(path)
        if before!=source['sha256']:
            changed.append(dict(path=str(path),snapshot_sha256=source['sha256'],current_sha256=before,
                action='Not substituted for frozen snapshot; exact upstream missingness unverified for this archive'))
            print('Updated upstream archive; retaining frozen extraction:',path.name,flush=True)
            continue
        counts=Counter()
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.lower().endswith('.xml'):continue
                root=ET.fromstring(z.read(name));bill=root if root.tag=='bill' else root.find('bill')
                counts['bills']+=1
                introduced=bill.findtext('introducedDate')
                for c in bill.findall('cosponsors/item'):
                    v=(c.findtext('isOriginalCosponsor') or '').strip().lower()
                    counts['true' if v=='true' else 'false' if v=='false' else 'missing_or_invalid']+=1
                    if v=='true' and c.findtext('sponsorshipDate')!=introduced:
                        anomalies.append(dict(archive=path.name,xml=name,member=c.findtext('bioguideId'),
                            introduced=introduced,joined=c.findtext('sponsorshipDate'),original=True))
        totals.update(counts);receipts.append(dict(path=str(path),sha256=before,counts=dict(counts)))
        print('Original flag audit',path.name,dict(counts),flush=True)
    if totals['missing_or_invalid']:raise ValueError('Unknown original flags require explicit missingness handling')
    return dict(totals=dict(totals),archives=receipts,date_anomalies=anomalies,changed_archives=changed,
        limitation='Only unchanged archives certify source-field completeness. True extracted flags require explicit XML true even in changed archives; old false flags may have represented absent fields.')


def replace_work_rows(old_rows,ids,w):
    index={a:i for i,a in enumerate(ids)};rows={}
    for (a,b),old in old_rows.items():
        i,j=index[a],index[b]
        rows[(a,b)]=dict(old,direct_propensity=w['direct_rate'][i,j],
            reverse_direct_propensity=w['direct_rate'][j,i],
            weighted_shared_jaccard=w['weighted_jaccard'][i,j],log_shared_bills=np.log1p(w['shared'][i,j]),
            network_proximity=w['network_proximity'][i,j],issue_similarity=w['issue_similarity'][i,j],
            co_service_congresses=w['co_service_congresses'][i,j])
    return rows


def specific_traits(a,b,traits,D):
    def logistic(x):return float(np.exp(-np.logaddexp(0,-x)))
    out={}
    for t in 'EAO':
        out['similarity_'+t+'_D']=(np.exp(-abs(traits[a][t]-traits[b][t]))*D
            if all(finite(v) for v in (traits[a].get(t),traits[b].get(t),D)) else None)
    for key,t,sign in [('joint_low_A','A',-1),('joint_high_E','E',1)]:
        v=logistic(sign*traits[a][t])*logistic(sign*traits[b][t]) if all(finite(traits[k].get(t)) for k in (a,b)) else None
        out[key]=v;out[key+'_D']=v*D if finite(v) and finite(D) else None
    return out


def coefficient_audit(cases,x,names,n=300):
    fitter=Fitter(cases,x);pool=list(range(len(cases)))
    penalty,inner,count=fitter.select(pool,'members',PENALTIES)
    fit=fitter.fit(pool,penalty);raw=raw_coefficients(fit,names)
    wanted=[k for k in names if k.startswith(('S_','joint_')) or k.endswith('_D')]
    rng=np.random.default_rng(731610);groups=components(cases);draws=[]
    for _ in range(n):
        mult=Counter(i for g in rng.integers(0,len(groups),len(groups)) for i in groups[g]);train=sorted(mult)
        if len({cases[k]['y'] for k in train})<2:continue
        coef=raw_coefficients(fitter.fit(train,penalty,mult),names)
        draws.append([coef[k] for k in wanted])
    values=np.array(draws)
    effects={k:dict(raw_coefficient=raw[k],stability_quantiles=np.quantile(values[:,j],[.025,.5,.975]),
                   positive_fraction=float(np.mean(values[:,j]>0))) for j,k in enumerate(wanted)}
    return dict(penalty=penalty,inner_loss=inner,inner_pairs=count,raw_coefficients=raw,
        effects=effects,model=fit.serializable(),resamples=len(draws),
        interpretation='Source-component resampling at fixed penalty; descriptive stability, not confidence intervals')


def main():
    frozen=verify_lock()
    if OUT.exists() and any(OUT.iterdir()):
        # Recover only the documented source-audit abort, before any data or fits.
        if {p.name for p in OUT.iterdir()} in ({'analysis_spec.json','PLAN.md'}, {'analysis_spec.json','PLAN.md','pre_fit_attempt.json'}):
            if not (OUT/'pre_fit_attempt.json').exists():
                save(OUT/'pre_fit_attempt.json',dict(previous_spec=read_json(OUT/'analysis_spec.json'),
                    reason='119th raw archives changed since extraction; audit now discloses unavailable provenance without replacing frozen data',
                    any_model_fitted=False))
        else:raise ValueError('Output exists; do not silently rerun')
    sources=[Path(__file__),HERE/'ORIGINAL_WORK_CONTEXT_PLAN.md',HERE/'history_work.py',
        HERE/'personality_context.py',HERE/'regression.py',HERE/'regression_diagnostics.py',
        INPUT/'bills.ndjson',INPUT/'members.json',INPUT/'traits.json',INPUT/'work_matrices.npz',
        OLD/'cases.json',OLD/'features.json',PREVIOUS/'model_results.json',
        ROOT/'outputs/cosponsor_challengers_20260905/data_audit.json']
    hashes={str(p.relative_to(ROOT)):digest(p) for p in sources}
    OUT.mkdir(parents=True,exist_ok=True)
    save(OUT/'analysis_spec.json',dict(started_utc=datetime.now(timezone.utc).isoformat(),models=MODELS,
        inputs=hashes,penalties=PENALTIES,development_only=True,previous_results_seen=True,
        frozen_test_id=frozen['freeze_id'],test_outcomes_used=False))
    (OUT/'PLAN.md').write_text((HERE/'ORIGINAL_WORK_CONTEXT_PLAN.md').read_text(encoding='utf-8'),encoding='utf-8')
    audit=audit_xml_flags();save(OUT/'source_flag_audit.json',audit)
    members,traits,ids,oldw=load_all();bills=read_rows(INPUT/'bills.ndjson')
    panel,counts,excluded=original_panel(bills,members)
    newids,w,by_congress,area=full_work(members,panel)
    assert ids==newids
    w['network_proximity']=network_proximity(w,{})[0]
    counts['new_eligibility_exclusions']=len(excluded)
    counts['shared_original_reconciles_to_previous']=bool(np.allclose(w['shared'],oldw['original_shared'],equal_nan=True))
    counts['introduced_opportunity_difference']=float(np.nansum(oldw['direct_opportunities']-w['direct_opportunities']))
    save(OUT/'work_audit.json',dict(counts=counts,excluded=excluded))
    np.savez_compressed(OUT/'work_matrices.npz',**w,
        **{f'c{c}_{k}':v for c,vs in by_congress.items() for k,v in vs.items()},
        area_signatures=area['signatures'],area_opportunities=area['opportunities'])
    save(OUT/'matrix_index.json',dict(ids=ids,areas=area['areas']))
    cases=read_json(OLD/'cases.json')
    oldrows={(r['actor'],r['target']):r for r in read_json(OLD/'features.json')['composite']}
    rows,pairs=add_features(cases,members,traits,ids,w,replace_work_rows(oldrows,ids,w))
    for (a,b),r in rows.items():r.update(specific_traits(a,b,traits,r['dw1_distance']))
    for pair in pairs:
        a,b=pair['pair'];i,j=ids.index(a),ids.index(b)
        pair.update(all_cosponsor_shared_bills=oldw['shared'][i,j],
            original_direct_a_to_b=w['direct'][i,j],original_opportunities_a_to_b=w['direct_opportunities'][i,j],
            original_direct_b_to_a=w['direct'][j,i],original_opportunities_b_to_a=w['direct_opportunities'][j,i],
            **specific_traits(a,b,traits,pair['ideology_distance']))
    save(OUT/'cases.json',cases);save(OUT/'features.json',list(rows.values()))
    save(OUT/'pair_descriptions.json',pairs);save(OUT/'group_descriptions.json',describe_groups(pairs))
    assignment=read_json(ROOT/'outputs/member_personal_relationships/20260910_frozen_v5/member_assignment.json')
    assert all(assignment[a]['split']=='development' for c in cases for a in c['pair'])
    trigger={'M000194','C001130'};reduced=[c for c in cases if not trigger.intersection(c['pair'])]
    results={};ranks={};sensitivity={};coefficients={}
    for name,names in MODELS.items():
        print('Fitting',name,len(names),'features',flush=True);x=matrices(cases,names,rows)
        results[name]=nested_cv(cases,x,'members');save(OUT/'model_results.json',results)
        print(name,results[name]['metrics'],flush=True)
        ranks[name]=leave_two_cases_out(cases,x,'members');save(OUT/'same_fit_auc.json',ranks)
        sensitivity[name]=nested_cv(reduced,matrices(reduced,names,rows),'members')
        save(OUT/'without_mace_crockett.json',sensitivity)
        coefficients[name]=coefficient_audit(cases,x,names);save(OUT/'coefficient_stability.json',coefficients)
    comparisons={'all_vs_original':resample_oof(cases,{'context_work':read_json(PREVIOUS/'model_results.json')['R0_main_effects'],
        'combined':results['R0_main_effects']},n=2000)}
    for name in list(MODELS)[1:]:
        comparisons[name]=resample_oof(cases,{'context_work':results['R0_main_effects'],'combined':results[name]},n=2000)
    save(OUT/'gain_stability.json',comparisons)
    assert all(digest(ROOT/p)==h for p,h in hashes.items())
    assert verify_lock()['freeze_id']==frozen['freeze_id']
    save(OUT/'run_receipt.json',dict(finished_utc=datetime.now(timezone.utc).isoformat(),inputs=hashes,
        cases=len(cases),models=list(MODELS),development_only=True,test_outcomes_used=False,
        old_inputs_unchanged=True,frozen_test_unchanged=True))
    print('Original work analysis complete',flush=True)


if __name__=='__main__':main()
