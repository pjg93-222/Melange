"""Freeze optional confidence cutoffs now; never choose them from future outcomes."""
import datetime as dt

import joblib
import numpy as np
import pandas as pd

from common import OLD, OUT, digest, log, read_json, stamp, write_json
from prospective import SNAPSHOT
from fit_extensions import EARLY_END
from run_models import topk_vectors, calibrate


def run():
    path=SNAPSHOT/'shortlist_policy.json'
    if path.exists():raise RuntimeError('Prospective shortlist policy already frozen')
    original=read_json(SNAPSHOT/'forecast_manifest.json')
    if dt.datetime.now(dt.timezone.utc).date().isoformat()!=original['forecast_date']:
        raise RuntimeError('Shortlist policy must be issued on forecast day')
    m=pd.read_parquet(OLD/'meta_118.parquet');m=m[m.mature.astype(bool)].reset_index(drop=True)
    early=m.day.to_numpy()<EARLY_END
    probabilities={}
    name='boosted_public_coverage';artifact=joblib.load(OLD/'models'/f'final_{name}.joblib')
    probabilities[name]=calibrate(np.load(OLD/f'development_prediction_{name}.npy'),artifact['calibration'])
    probabilities['boosted_network_refit']=np.load(OUT/'extension_predictions/boosted_network.npy')
    controls=pd.read_parquet(SNAPSHOT/'forecasts.parquet');network=pd.read_parquet(SNAPSHOT/'network_forecasts.parquet')
    rows=controls[['bill','member','member_name']].merge(network,on=['bill','member'],validate='one_to_one')
    rows[name]=controls[name];rows[name+'_rank']=controls[name+'_rank']
    policy={}
    for name,p in probabilities.items():
        top=np.zeros(len(m),dtype=bool);top[topk_vectors(m,m.y.to_numpy(),p,8)]=True
        policy[name]=[]
        for fraction in [1.,.5,.25,.1,.05,.01]:
            cutoff=float(np.quantile(p[top&early],1-fraction)) if fraction<1 else 0.
            chosen=(rows[name+'_rank']<=8)&(rows[name]>=cutoff)
            policy[name].append(dict(target_retained_2023=fraction,cutoff=cutoff,issued_recommendations=int(chosen.sum()),
                issued_bills=int(rows.bill[chosen].nunique()),issued_members=int(rows.member[chosen].nunique())))
            if name=='boosted_network_refit' and fraction==.05:
                rows[chosen].sort_values(name,ascending=False).to_csv(SNAPSHOT/'network_selective_shortlist.csv',index=False)
    write_json(path,dict(issued_utc=stamp(),forecast_date=original['forecast_date'],status='PENDING_OUTCOMES',policies=policy,
        control_prediction_sha256=digest(SNAPSHOT/'forecasts.parquet'),network_prediction_sha256=digest(SNAPSHOT/'network_forecasts.parquet'),
        note='Cutoffs determined from 2023 score quantiles, then applied unchanged to today. They control score selectivity, not guaranteed future precision. Cutoff calibration follows each issued artifact.'))
    log('Prospective confidence cutoffs frozen; no future outcomes evaluated')


if __name__=='__main__':run()
