"""One fixed network-aware LambdaMART challenger, with chunked scoring."""
import gc
import sys

from common import CODE, OLD, OUT, digest, log, read_json, stamp, write_json
sys.path.insert(0,str(OUT/'vendor'))
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from fit_extensions import Panel, COV, NETWORK, EARLY_END, selective
from run_models import metrics


def run():
    path=OUT/'network_ranker_results.json'
    if path.exists():raise RuntimeError('Fixed network ranker already evaluated')
    names=COV+NETWORK;train=Panel(117)
    idx=np.flatnonzero(train.meta.mature.to_numpy());m=train.meta.iloc[idx].reset_index(drop=True)
    idx=idx[m.groupby('group').y.transform('sum').to_numpy()>0];m=train.meta.iloc[idx]
    order=np.lexsort((m.member.to_numpy(),m.group.to_numpy()));idx=idx[order];m=train.meta.iloc[idx]
    x=train.design(idx,names);y=m.y.to_numpy();sizes=m.groupby('group',sort=True).size().to_numpy()
    config=dict(objective='lambdarank',n_estimators=600,num_leaves=7,learning_rate=.05,
        min_child_samples=50,reg_lambda=10,random_state=913,n_jobs=2,verbosity=-1,deterministic=True,
        force_col_wise=True,lambdarank_truncation_level=8,lambdarank_norm=True,label_gain=[0,1])
    plan=dict(created_utc=stamp(),features=names,config=config,protocol_sha256=digest(CODE/'PROTOCOL.md'),
              early_year=2023,later_year=2024,status='development_only',training_rows=len(y),training_queries=len(sizes))
    write_json(OUT/'network_ranker_plan.json',plan)
    log(f'Fixed network LambdaMART: {len(y):,} training rows, {len(names)} features')
    model=lgb.LGBMRanker(**config);model.fit(x,y,group=sizes)
    modelpath=OUT/'ranker_models/network_ranker.txt';model.booster_.save_model(str(modelpath))
    del x,y,m,train;gc.collect()
    val=Panel(118);idx=np.flatnonzero(val.meta.mature.to_numpy());m=val.meta.iloc[idx].reset_index(drop=True)
    score=np.empty(len(idx),dtype=np.float32)
    for start in range(0,len(idx),100000):
        block=idx[start:start+100000];score[start:start+len(block)]=model.predict(val.design(block,names))
    np.save(OUT/'network_ranker_scores_118.npy',score)
    early=m.day.to_numpy()<EARLY_END
    g=pd.Series(score).groupby(m.group)
    standardized=(score-g.transform('mean').to_numpy())/np.maximum(g.transform('std').fillna(1).to_numpy(),.1)
    activity=np.load(OUT/'activity_probability_118.npy')
    design=np.column_stack([standardized,logit(np.clip(activity,1e-5,1-1e-5))])
    scaler=StandardScaler().fit(design[early]);cal=LogisticRegression(C=1.,solver='newton-cholesky',max_iter=150)
    cal.fit(scaler.transform(design[early]),m.y.to_numpy()[early])
    if cal.coef_[0,0]<=0:raise RuntimeError('Rank ordering reversed in calibration')
    p=cal.predict_proba(scaler.transform(design))[:,1].astype(np.float32)
    predpath=OUT/'network_ranker_probabilities_118.npy';np.save(predpath,p)
    calpath=OUT/'ranker_models/network_member_calibration.joblib'
    joblib.dump(dict(model=cal,scaler=scaler,trained_calendar_year=2023),calpath)
    freeze=dict(frozen_utc=stamp(),prediction_sha256=digest(predpath),model_sha256=digest(modelpath),calibration_sha256=digest(calpath),
        selection_2023=metrics(m[early].reset_index(drop=True),p[early]),plan_sha256=digest(OUT/'network_ranker_plan.json'))
    write_json(OUT/'network_ranker_freeze.json',freeze)
    result=dict(completed_utc=stamp(),status='development_only',year_2023=freeze['selection_2023'],
        year_2024=metrics(m[~early].reset_index(drop=True),p[~early]),selective_2024=selective(m,p,early),
        freeze_sha256=digest(OUT/'network_ranker_freeze.json'),code_sha256=digest(__file__))
    write_json(path,result);log(f"Network ranker complete: 2024 P@8={result['year_2024']['precision_at_8']:.5f}")


if __name__=='__main__':
    with threadpool_limits(limits=2):run()
