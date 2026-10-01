"""Clustered comparison, coverage-aware precision, and matched-budget diagnostics."""
import gc
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from universe_common import OLD, OUT, digest, log, read_json, stamp, write_json
from universe_models import EARLY_END, menu
from paired_extensions import families
from run_models import topk_vectors, basic_metrics

# With79 contrasts,100k draws leave about32 order statistics in each adjusted tail.
REPS=100000


def selected_summary(meta,y,idx):
    hits=int(y[idx].sum());n=len(idx)
    return dict(recommendations=n,hits=hits,precision=hits/n if n else None,
       recall=hits/max(1,int(y.sum())),bills=int(meta.iloc[idx].bill.nunique()),members=int(meta.iloc[idx].member.nunique()))


def intervals(matrix,numerator,denominator,alpha=.05):
    values=[]
    for start in range(0,len(matrix),1000):
        w=matrix[start:start+1000].astype(np.float64);d=w@denominator
        v=w@numerator;values.extend((v[d>0]/d[d>0]).tolist())
    return np.quantile(values,[alpha/2,1-alpha/2]).tolist() if values else [None,None]


def run():
    if (OUT/'universe_statistics.json').exists():raise RuntimeError('Statistics already frozen')
    result=read_json(OUT/'universe_results.json');model_names=list(result['models']);specs=menu()
    new=[name for name,spec in specs.items() if spec['role']=='challenger']
    m=pd.read_parquet(OLD/'meta_118.parquet')
    member_ids=read_json(OLD/'identifiers.json')['members'];gold=set(read_json(OUT/'gold_cohort.json')['member_ids'])
    included=np.array([mid in gold for mid in member_ids])[m.member.to_numpy()]
    m=m[m.mature.astype(bool)&included].reset_index(drop=True)
    early=m.day.to_numpy()<EARLY_END;late=~early;me=m[early].reset_index(drop=True);ml=m[late].reset_index(drop=True)
    codes,n=families(ml);y=ml.y.to_numpy();ye=me.y.to_numpy()
    rng=np.random.default_rng(2090507)
    weights=rng.multinomial(n,np.full(n,1/n),size=REPS).astype(np.uint16)
    pairs=[(name,base) for name in new for base in ['boosted_dynamic','boosted_public_coverage','boosted_network','boosted_context']]
    pairs += [('boosted_language','boosted_language_coverage'),('boosted_universe','logistic_universe'),
              ('boosted_language','boosted_language_placebo'),('boosted_universe','boosted_universe_no_language'),
              ('boosted_universe','boosted_universe_no_media'),
              ('boosted_reconstructed_context','logistic_reconstructed_context')]
    pairs += [(name,'boosted_dynamic') for name,spec in specs.items() if spec['role']=='refit_control']
    pairs += [('logistic_history','logistic_base')]
    assert len(pairs)==79 and len(set(pairs))==79
    write_json(OUT/'universe_statistics_plan.json',dict(created_utc=stamp(),pairs=pairs,comparisons=len(pairs),replicates=REPS,
        code_sha256=digest(__file__),selection_sha256=digest(OUT/'universe_selection.json'),
        uncertainty=f'Whole legislative families resampled, all member rows and forecast dates kept together. Bonferroni percentile intervals over all{len(pairs)} comparisons per endpoint (precision primary, Brier secondary). Descriptive development only; intervals cannot repair coverage selection bias.'))
    hist={};slots={};brier={};selective={};strata={};ordering={};probabilities={}
    rowcounts=np.bincount(codes,minlength=n)
    # Cutoff policies come from earlier-year probabilities; indices are ranked only
    # within each bill-date. Party strata keep the original eight slots, never reselect.
    for name in model_names:
        p=np.load(OUT/f'predictions/{name}.npy');assert len(p)==len(m)
        pe=p[early];pl=p[late];te=topk_vectors(me,ye,pe,8);tl=topk_vectors(ml,y,pl,8)
        hist[name]=np.bincount(codes[tl],weights=y[tl],minlength=n)
        slots[name]=np.bincount(codes[tl],minlength=n)
        brier[name]=np.bincount(codes,weights=(pl-y)**2,minlength=n)
        ordering[name]=tl[np.lexsort((ml.member.to_numpy()[tl],ml.group.to_numpy()[tl],-pl[tl]))]
        probabilities[name]=pl[ordering[name]]
        selective[name]=[]
        for fraction in [1.,.5,.25,.1,.05,.01]:
            cutoff=float(np.quantile(pe[te],1-fraction));idx=tl[pl[tl]>=cutoff]
            summary=selected_summary(ml,y,idx)
            h=np.bincount(codes[idx],weights=y[idx],minlength=n);d=np.bincount(codes[idx],minlength=n)
            summary.update(target_fraction_2023=fraction,cutoff_2023=cutoff,ci95=intervals(weights,h,d))
            selective[name].append(summary)
        strata[name]={}
        masks={'House':ml.senate.to_numpy()==0,'Senate':ml.senate.to_numpy()==1,
               'Democratic':ml.democrat.to_numpy()==1,'non_Democratic':ml.democrat.to_numpy()==0}
        for label,mask in masks.items():
            idx=tl[mask[tl]];summary=selected_summary(ml,y,idx)
            summary['recall']=int(y[idx].sum())/max(1,int(y[mask].sum()))
            summary['candidate_rows']=int(mask.sum());summary['candidate_events']=int(y[mask].sum())
            summary['candidate_metrics']=basic_metrics(y[mask],pl[mask])
            strata[name][label]=summary
        log(f'Cluster/coverage statistics accumulated for {name}')
        del p,pe,pl;gc.collect()
    paired={}
    for challenger,base in pairs:
        assert np.array_equal(slots[challenger],slots[base]),'Unequal comparison budget'
        delta=hist[challenger]-hist[base];bd=brier[challenger]-brier[base]
        paired[challenger+' vs '+base]=dict(extra_hits=int(delta.sum()),delta_precision=float(delta.sum()/slots[base].sum()),
          ci95=intervals(weights,delta,slots[base]),adjusted_interval=intervals(weights,delta,slots[base],alpha=.05/len(pairs)),
          delta_brier=float(bd.sum()/rowcounts.sum()),brier_ci95=intervals(weights,bd,rowcounts),
          brier_adjusted_interval=intervals(weights,bd,rowcounts,alpha=.05/len(pairs)))
    # Matched retained counts are descriptive budgets fixed before results. They
    # do not inherit the probability cutoffs and are not prospective policies.
    matched={}
    for count in [250,500,1000,2000,5000]:
        matched[count]={name:selected_summary(ml,y,ordering[name][:count]) for name in model_names}
    chosen=result['chosen_on_2023']
    all_counts=ml.groupby('group').y.sum().to_numpy();oracle_hits=int(np.minimum(all_counts,8).sum())
    output=dict(completed_utc=stamp(),status='retrospective_continuing_member_development',cohort_members=len(gold),
      gold_cohort_sha256=digest(OUT/'gold_cohort.json'),families=n,replicates=REPS,comparisons=len(pairs),
      chosen_on_2023=chosen,rows_2024=len(ml),events_2024=int(y.sum()),slots_2024=int(slots[chosen].sum()),
      bill_dates_2024=int(ml.group.nunique()),bills_2024=int(ml.bill.nunique()),
      forced_top8_oracle=dict(hits=oracle_hits,precision=oracle_hits/int(slots[chosen].sum()),
          zero_event_bill_dates=int((all_counts==0).sum())),
      paired=paired,selective=selective,matched_retained_counts=matched,strata=strata,
      note='Family clusters cover bill reintroductions/related short titles; remaining member-level dependence and historical model-selection optimism are not removed. Intervals are not confirmatory p-values. Non-Democratic combines Republicans/independents as encoded in frozen metadata.')
    write_json(OUT/'universe_statistics.json',output)
    log('Whole-family uncertainty and matched-count comparisons complete')


if __name__=='__main__':
    with threadpool_limits(limits=2):run()
