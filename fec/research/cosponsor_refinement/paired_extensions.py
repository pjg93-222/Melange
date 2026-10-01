"""Paired whole-legislative-family uncertainty for later development shortlists."""
import gc

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from common import OLD, OUT, digest, log, read_json, stamp, write_json
from build_panel import get_bills, normalize_title
from fit_extensions import EARLY_END
from run_models import topk_vectors


def families(meta):
    ids=read_json(OLD/'identifiers.json')['bills'];parent={}
    def root(k):
        parent.setdefault(k,k)
        if parent[k]!=k:parent[k]=root(parent[k])
        return parent[k]
    def union(a,b):
        a,b=root(a),root(b);parent[max(a,b)]=min(a,b)
    for a,b in read_json(OLD/'analogue_links.json').items():
        if int(a.split(':')[0])<=118:union(a,b['prior_key'])
    titles={}
    for b in get_bills():
        if b['congress']>118:continue
        for title in b['short_titles']:
            title=normalize_title(title)
            if len(title.split())<4:continue
            if title in titles:union(b['key'],titles[title])
            titles[title]=b['key']
    mapping={code:root(ids[int(code)]) for code in meta.bill.unique()}
    codes,keys=pd.factorize(meta.bill.map(mapping),sort=True)
    return codes,len(keys)


def run():
    m=pd.read_parquet(OLD/'meta_118.parquet');m=m[m.mature.astype(bool)].reset_index(drop=True)
    late=m.day.to_numpy()>=EARLY_END;mm=m[late].reset_index(drop=True);del m;gc.collect()
    codes,n=families(mm);y=mm.y.to_numpy()
    baseline=np.load(OLD/'development_prediction_boosted_public_coverage.npy',mmap_mode='r')[late]
    chosen=topk_vectors(mm,y,baseline,8)
    h0=np.bincount(codes[chosen],weights=y[chosen],minlength=n)
    slots=np.bincount(codes[chosen],minlength=n)
    w=np.random.default_rng(823).multinomial(n,np.full(n,1/n),size=3000)
    denom=w@slots;results={}
    paths={p.stem:p for p in (OUT/'extension_predictions').glob('*.npy')}
    paths['lambdamart_activity']=OUT/'ranker_combined_probabilities_118.npy'
    if (OUT/'network_ranker_probabilities_118.npy').exists():paths['lambdamart_network']=OUT/'network_ranker_probabilities_118.npy'
    for name,path in paths.items():
        p=np.load(path,mmap_mode='r')[late];chosen=topk_vectors(mm,y,p,8)
        h=np.bincount(codes[chosen],weights=y[chosen],minlength=n);delta=w@(h-h0)/denom
        results[name]=dict(hits=int(h.sum()),extra_hits=int((h-h0).sum()),delta_precision=float((h-h0).sum()/slots.sum()),
             ci95=np.quantile(delta,[.025,.975]).tolist(),conservative_all_comparison_interval=np.quantile(delta,[.025/len(paths),1-.025/len(paths)]).tolist())
    write_json(OUT/'paired_extension_results.json',dict(completed_utc=stamp(),status='development_only',baseline='boosted_public_coverage',
        baseline_hits=int(h0.sum()),slots=int(slots.sum()),families=n,replicates=3000,models=results,
        note='Whole legislative families and all dates resampled together. Both ordinary and conservative all-comparison intervals are descriptive development uncertainty; no independent confirmation.'))
    log('Paired development uncertainty saved')


if __name__=='__main__':
    with threadpool_limits(limits=2):run()
