"""Small-memory ablations; choose on 2023, assess 2024 development afterward."""
import argparse
import datetime as dt
import gc
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from common import CODE, OLD, OUT, digest, log, read_json, stamp, write_json
from build_panel import FEATURES, BASE, ENHANCED, DYNAMIC, PUBLIC
from build_extra_features import TEXT, DEMOGRAPHIC
from member_network import NAMES as NETWORK
from external_context import LOBBY, STAFF
from run_models import SEED, platt_fit, calibrate, metrics, topk_vectors

EARLY_END=dt.date(2024,1,1).toordinal()
DYN=BASE+ENHANCED+DYNAMIC
COV=DYN+[PUBLIC[i] for i in [0,1,4,7,8]]
ALL_NAMES=FEATURES+NETWORK+TEXT+DEMOGRAPHIC+LOBBY+STAFF
MODELS={
 'logistic_text_gate':('logistic','logistic_dynamic',DYN,'gate'),
 'boosted_text_gate':('boosted','boosted_dynamic',DYN,'gate'),
 'logistic_text_added':('logistic','logistic_dynamic',DYN+TEXT,'add'),
 'boosted_text_added':('boosted','boosted_dynamic',DYN+TEXT,'add'),
 'boosted_network':('boosted','boosted_public_coverage',COV+NETWORK,'add'),
 'boosted_demographic':('boosted','boosted_public_coverage',COV+DEMOGRAPHIC,'add'),
 'boosted_lobbying':('boosted','boosted_public_coverage',COV+LOBBY,'add'),
 'boosted_context':('boosted','boosted_public_coverage',COV+NETWORK+DEMOGRAPHIC+LOBBY,'add'),
 'boosted_all':('boosted','boosted_public_coverage',COV+TEXT+NETWORK+DEMOGRAPHIC+LOBBY,'add'),
 'logistic_all':('logistic','logistic_dynamic',COV+TEXT+NETWORK+DEMOGRAPHIC+LOBBY,'add'),
 'boosted_staff_exploratory':('boosted','boosted_public_coverage',COV+TEXT+NETWORK+DEMOGRAPHIC+LOBBY+STAFF,'add'),
}


class Panel:
    def __init__(self,cg):
        if cg not in [117,118]:raise ValueError('Only historical development panels are permitted')
        self.meta=pd.read_parquet(OLD/f'meta_{cg}.parquet')
        n=len(self.meta)
        specs=[(OLD/f'X_{cg}.f32',FEATURES),(OUT/f'member_network_v2_{cg}.f32',NETWORK),
               (OUT/f'extra_{cg}.f32',TEXT+DEMOGRAPHIC),(OUT/f'external_{cg}.f32',LOBBY+STAFF)]
        self.columns={}
        for path,names in specs:
            a=np.memmap(path,mode='r',dtype=np.float32,shape=(n,len(names)))
            for i,name in enumerate(names):self.columns[name]=(a,i)

    def design(self,indices,names,mode='add'):
        result=np.empty((len(indices),len(names)),dtype=np.float32)
        for i,name in enumerate(names):
            a,j=self.columns[name];result[:,i]=a[indices,j]
        if mode=='gate':
            a,j=self.columns['text_body_close'];close=a[indices,j]
            for name in ['analogue_similarity','analogue_available','signed_analogue','sponsored_analogue']:
                if name in names:result[:,names.index(name)]*=close
        return result


def predict(artifact,panel,indices):
    p=np.empty(len(indices),dtype=np.float32)
    for start in range(0,len(indices),100000):
        idx=indices[start:start+100000]
        x=panel.design(idx,artifact['features'],artifact['mode'])
        if artifact['scaler'] is not None:x=artifact['scaler'].transform(x).astype(np.float64)
        p[start:start+len(idx)]=artifact['model'].predict_proba(x)[:,1]
    return np.clip(p,1e-8,1-1e-8)


def selective(m,p,early):
    top=np.zeros(len(m),dtype=bool);top[topk_vectors(m,m.y.to_numpy(),p,8)]=True
    code,bills=pd.factorize(m.bill)
    n=len(bills);w=np.random.default_rng(219).multinomial(n,np.full(n,1/n),size=1200)
    out=[]
    for fraction in [1,.5,.25,.1,.05,.01]:
        cutoff=float(np.quantile(p[top&early],1-fraction))
        selected=top & (~early) & (p>=cutoff)
        rows=int(selected.sum());hits=int(m.y.to_numpy()[selected].sum())
        h=np.bincount(code[selected],weights=m.y.to_numpy()[selected],minlength=n)
        d=np.bincount(code[selected],minlength=n);denom=w@d;valid=denom>0
        precision=(w@h)[valid]/denom[valid]
        out.append(dict(target_retained_2023=fraction,cutoff=cutoff,recommendations_2024=rows,hits_2024=hits,
          precision_2024=hits/rows if rows else None,ci95=np.quantile(precision,[.025,.975]).tolist() if len(precision) else None,
          bills_2024=int(m.bill[selected].nunique()),members_2024=int(m.member[selected].nunique())))
    return out


def run():
    result_path=OUT/'extension_results.json'
    if result_path.exists() and 'completed_utc' in read_json(result_path):raise RuntimeError('Extension evaluation already complete')
    modeldir=OUT/'extension_models';modeldir.mkdir(exist_ok=True)
    preddir=OUT/'extension_predictions';preddir.mkdir(exist_ok=True)
    selection_path=OUT/'extension_selection.json'
    old=read_json(OLD/'development_results.json')
    train=Panel(117);val=Panel(118)
    y=train.meta.y.to_numpy();eligible=train.meta.mature.to_numpy().astype(bool)
    sampled=eligible & ((y>0) | (np.random.default_rng(SEED+117).random(len(y))<.1))
    indices=np.flatnonzero(sampled);target=y[indices];weight=np.where(target>0,1.,10.)
    vindices=np.flatnonzero(val.meta.mature.to_numpy());m=val.meta.iloc[vindices].reset_index(drop=True)
    early=m.day.to_numpy()<EARLY_END;me=m[early].reset_index(drop=True)
    selection=read_json(selection_path) if selection_path.exists() else dict(started_utc=stamp(),models={},protocol_sha256=digest(CODE/'PROTOCOL.md'))
    plan=dict(created_utc=stamp(),models={name:dict(kind=kind,configuration_from=base,features=names,mode=mode) for name,(kind,base,names,mode) in MODELS.items()},
          training_congress=117,selection_calendar_year=2023,assessment_calendar_year=2024,independent_final_test=False,
          protocol_sha256=digest(CODE/'PROTOCOL.md'),script_sha256=digest(__file__),
          source_receipts={f:digest(OUT/f) for f in ['predecessor_audit_v2.json','member_network_receipt_v2.json','extra_feature_receipt.json','external_context_receipt.json']})
    if not (OUT/'extension_plan.json').exists():write_json(OUT/'extension_plan.json',plan)
    else:
        prior_plan=read_json(OUT/'extension_plan.json')
        assert prior_plan['source_receipts']==plan['source_receipts'] and prior_plan['models']==plan['models']
    for name,(kind,base,names,mode) in MODELS.items():
        if name in selection['models']:continue
        config=old['models'][base]['selected']
        log(f'Fitting {name}: {len(indices):,} weighted training rows, {len(names)} features, {config}')
        x=train.design(indices,names,mode)
        scaler=None
        if kind=='logistic':
            scaler=StandardScaler().fit(x,sample_weight=weight)
            xx=scaler.transform(x).astype(np.float64)
            model=LogisticRegression(C=config['C'],solver='newton-cholesky',max_iter=150,tol=1e-7,random_state=SEED)
            model.fit(xx,target,sample_weight=weight);del xx
        else:
            model=HistGradientBoostingClassifier(learning_rate=.06,max_leaf_nodes=config['max_leaf_nodes'],
                   max_iter=config['max_iter'],l2_regularization=10,min_samples_leaf=50,early_stopping=False,random_state=SEED)
            model.fit(x,target,sample_weight=weight)
        del x
        artifact=dict(model=model,scaler=scaler,features=names,mode=mode,kind=kind,config=config)
        raw=predict(artifact,val,vindices)
        cal=platt_fit(m.y.to_numpy()[early],raw[early]);p=calibrate(raw,cal);artifact['calibration_2023']=cal
        np.save(preddir/f'{name}.npy',p);joblib.dump(artifact,modeldir/f'{name}.joblib')
        measured=metrics(me,p[early]);selection['models'][name]=dict(configuration=config,selection_2023=measured,
                 prediction_sha256=digest(preddir/f'{name}.npy'),model_sha256=digest(modeldir/f'{name}.joblib'),
                 exploratory_staff='staff' in name)
        write_json(selection_path,selection)
        log(f"Selected-period {name}: P@8={measured['precision_at_8']:.5f}; AP={measured['average_precision']:.5f}")
        del artifact,raw,p,model;gc.collect()
    # Freeze every prediction and the winner before assessing the later development year.
    primary=[name for name in MODELS if 'staff' not in name]
    chosen=max(primary,key=lambda name:selection['models'][name]['selection_2023']['precision_at_8'])
    if 'frozen_utc' not in selection:
        selection.update(chosen=chosen,frozen_utc=stamp());write_json(selection_path,selection)
    result=read_json(result_path) if result_path.exists() else dict(assessed_utc=stamp(),chosen_on_2023=chosen,selection_sha256=digest(selection_path),status='development_only',models={})
    for name in [*MODELS,'logistic_dynamic','boosted_dynamic','boosted_public_coverage']:
        if name in result['models']:continue
        if name in MODELS:p=np.load(preddir/f'{name}.npy')
        else:
            raw=np.load(OLD/f'development_prediction_{name}.npy')
            p=calibrate(raw,platt_fit(m.y.to_numpy()[early],raw[early]));del raw
        result['models'][name]=dict(year_2023=metrics(me,p[early]),year_2024=metrics(m[~early].reset_index(drop=True),p[~early]),
                                  selective_2024=selective(m,p,early),exploratory_staff='staff' in name)
        write_json(OUT/'extension_results.json',result)
        log(f"2024 development {name}: P@8={result['models'][name]['year_2024']['precision_at_8']:.5f}")
        del p;gc.collect()
    result['completed_utc']=stamp();write_json(OUT/'extension_results.json',result)
    log(f'Extension comparison complete. 2023-selected challenger: {chosen}')


if __name__=='__main__':
    with threadpool_limits(limits=4):run()
