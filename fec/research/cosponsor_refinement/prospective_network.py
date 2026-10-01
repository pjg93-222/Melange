"""Refit the fixed network challenger and append an immutable prospective forecast."""
import datetime as dt
import gc

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

from common import CODE, OLD, OUT, digest, log, read_json, stamp, write_json
from fit_extensions import Panel, COV, NETWORK
from member_network import prior_graph, exposure
from prospective import SNAPSHOT, current_bills, serving_roster
from build_panel import get_bills, FEATURES
from run_models import SEED, calibrate

NAME='boosted_network_refit'


def run():
    result_path=SNAPSHOT/'network_forecast_manifest.json'
    if result_path.exists():raise RuntimeError('Network forecast already issued')
    original=read_json(SNAPSHOT/'forecast_manifest.json')
    if dt.datetime.now(dt.timezone.utc).date().isoformat()!=original['forecast_date']:
        raise RuntimeError('The network forecast must be issued on the original forecast day')
    for f,k in [('features.npy','features_sha256'),('forecasts.parquet','forecasts_sha256')]:
        if digest(SNAPSHOT/f)!=original[k]:raise RuntimeError('Original prospective inputs changed')
    selection=read_json(OUT/'extension_selection.json')
    candidates={k:v for k,v in selection['models'].items() if k.startswith('boosted_') and not v['exploratory_staff']}
    winner=max(candidates,key=lambda k:candidates[k]['selection_2023']['precision_at_8'])
    if winner!='boosted_network':raise RuntimeError(f'Prespecified best boosted variant changed: {winner}')
    old=joblib.load(OUT/'extension_models/boosted_network.joblib');names=COV+NETWORK
    blocks=[];labels=[];weights=[];counts={}
    for cg in [117,118]:
        panel=Panel(cg);y=panel.meta.y.to_numpy();mature=panel.meta.mature.to_numpy().astype(bool)
        eligible=mature & ((y>0)|(np.random.default_rng(SEED+cg).random(len(y))<.1))
        idx=np.flatnonzero(eligible);blocks.append(panel.design(idx,names));labels.append(y[idx]);weights.append(np.where(y[idx]>0,1.,10.))
        counts[cg]=dict(sampled_rows=len(idx),positive_rows=int(y[idx].sum()),mature_rows=int(mature.sum()))
        del panel;gc.collect()
    x=np.vstack(blocks);y=np.concatenate(labels);weight=np.concatenate(weights);del blocks,labels,weights;gc.collect()
    log(f'Prospective network refit: {len(y):,} sampled mature 117/118 rows')
    model=HistGradientBoostingClassifier(learning_rate=.06,max_leaf_nodes=15,max_iter=200,
         l2_regularization=10,min_samples_leaf=50,early_stopping=False,random_state=SEED)
    model.fit(x,y,sample_weight=weight);del x,y,weight;gc.collect()
    artifact=dict(model=model,features=names,calibration=old['calibration_2023'],training_congresses=[117,118],configuration=old['config'])
    modelpath=SNAPSHOT/'boosted_network_refit.joblib';joblib.dump(artifact,modelpath)
    frame=pd.read_parquet(SNAPSHOT/'forecasts.parquet');day=dt.date.fromisoformat(original['forecast_date']).toordinal()
    # The new graph consumes no 119 outcomes: all historical edges are from 118 only.
    history=[b for b in get_bills() if b['congress']<=118]
    graphs={ch:prior_graph(history,119,ch) for ch in ['House','Senate']}
    bills={b['key']:b for b in current_bills()};roster=serving_roster();parties={mid:r['party'] for mid,r in roster.items()}
    net=np.zeros((len(frame),len(NETWORK)),dtype=np.float32);missing=0
    for key,idx in frame.groupby('bill',sort=False).indices.items():
        b=bills[key];g=graphs[b['chamber']];joined={mid:d for mid,d in b['joins'].items() if d<day}
        if b['intro']<day:joined[b['sponsor']]=b['intro']
        table=exposure(g,joined,day,b['sponsor'],parties)
        codes=np.array([g['index'].get(mid,-1) for mid in frame.member.iloc[idx]])
        valid=codes>=0;net[idx[valid]]=table[codes[valid]]
        net[idx[~valid],NETWORK.index('network_isolate')]=1;missing+=int((~valid).sum())
    np.save(SNAPSHOT/'network_features.npy',net)
    base=np.load(SNAPSHOT/'features.npy',mmap_mode='r')
    design=np.column_stack([base[:,[FEATURES.index(n) for n in COV]],net])
    p=calibrate(model.predict_proba(design)[:,1],artifact['calibration'])
    result=frame[['bill','member']].copy();result[NAME]=p
    result[NAME+'_rank']=result.groupby('bill')[NAME].rank(method='first',ascending=False).astype(int)
    path=SNAPSHOT/'network_forecasts.parquet';result.to_parquet(path,index=False)
    result[result[NAME+'_rank']<=8].merge(frame[['bill','member','member_name','chamber','bill_age']],on=['bill','member'],validate='one_to_one').sort_values(NAME,ascending=False).to_csv(SNAPSHOT/'network_top_eight.csv',index=False)
    write_json(result_path,dict(issued_utc=stamp(),forecast_date=original['forecast_date'],outcome_end=original['outcome_end'],
        status='PENDING_OUTCOMES',model_name=NAME,rows=len(result),bills=result.bill.nunique(),model_sha256=digest(modelpath),
        forecasts_sha256=digest(path),features_sha256=digest(SNAPSHOT/'network_features.npy'),missing_prior_network_rows=missing,
        feature_names=names,training=counts,calibration_calendar_year=2023,original_forecast_manifest_sha256=digest(SNAPSHOT/'forecast_manifest.json'),
        development_selection_sha256=digest(OUT/'extension_selection.json'),protocol_sha256=digest(CODE/'PROTOCOL.md'),code_sha256=digest(__file__),
        note='Independent future comparison of the fixed strongest boosted extension on 2023. Refit 117/118; graph only preceding Congress; no staff or member-contact assumptions.'))
    log(f'Prospective network challenger issued on {len(result):,} frozen candidate rows')


if __name__=='__main__':
    with threadpool_limits(limits=2):run()
