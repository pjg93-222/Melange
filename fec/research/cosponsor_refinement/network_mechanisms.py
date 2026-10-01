"""Separate eigenvector/structure, dynamic exposure, and marginal coverage."""
import gc

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

from common import CODE, OLD, OUT, digest, log, read_json, stamp, write_json
from fit_extensions import Panel, COV, NETWORK, EARLY_END, predict, selective
from influence_coverage import NAME
from run_models import SEED, platt_fit, calibrate, metrics

CONFIGS={
 'boosted_static_network':COV+NETWORK[:9],
 'boosted_dynamic_exposure':COV+NETWORK[9:],
 'boosted_network_no_eigen':COV+[n for n in NETWORK if n not in ['network_eigenvector_component','network_sponsor_eigenvector','network_active_centrality_share']],
 'boosted_network_marginal':COV+NETWORK+[NAME],
}


def run():
    resultpath=OUT/'network_mechanism_results.json'
    if resultpath.exists():raise RuntimeError('Mechanisms already evaluated')
    train=Panel(117);val=Panel(118)
    for cg,panel in [(117,train),(118,val)]:
        a=np.memmap(OUT/f'marginal_coverage_{cg}.f32',mode='r',dtype=np.float32,shape=(len(panel.meta),1))
        panel.columns[NAME]=(a,0)
    y=train.meta.y.to_numpy();idx=np.flatnonzero(train.meta.mature.to_numpy() & ((y>0)|(np.random.default_rng(SEED+117).random(len(y))<.1)))
    weight=np.where(y[idx]>0,1.,10.);vidx=np.flatnonzero(val.meta.mature.to_numpy());m=val.meta.iloc[vidx].reset_index(drop=True)
    early=m.day.to_numpy()<EARLY_END
    freeze=dict(started_utc=stamp(),protocol_sha256=digest(CODE/'PROTOCOL.md'),models={})
    write_json(OUT/'network_mechanism_plan.json',dict(configurations=CONFIGS,leaves=15,trees=200,learning_rate=.06,
         protocol_sha256=digest(CODE/'PROTOCOL.md'),coverage_receipt_sha256=digest(OUT/'marginal_coverage_receipt.json')))
    for name,names in CONFIGS.items():
        log(f'Network mechanism diagnostic: {name}')
        x=train.design(idx,names)
        model=HistGradientBoostingClassifier(learning_rate=.06,max_leaf_nodes=15,max_iter=200,l2_regularization=10,min_samples_leaf=50,early_stopping=False,random_state=SEED)
        model.fit(x,y[idx],sample_weight=weight);del x
        artifact=dict(model=model,scaler=None,features=names,mode='add')
        raw=predict(artifact,val,vidx);cal=platt_fit(m.y.to_numpy()[early],raw[early]);artifact['calibration_2023']=cal
        p=calibrate(raw,cal);np.save(OUT/'extension_predictions'/f'{name}.npy',p)
        joblib.dump(artifact,OUT/'extension_models'/f'{name}.joblib')
        freeze['models'][name]=dict(year_2023=metrics(m[early].reset_index(drop=True),p[early]),
            prediction_sha256=digest(OUT/'extension_predictions'/f'{name}.npy'),model_sha256=digest(OUT/'extension_models'/f'{name}.joblib'))
        del raw,p,artifact,model;gc.collect()
    freeze['frozen_utc']=stamp();write_json(OUT/'network_mechanism_freeze.json',freeze)
    result=dict(status='development_only',freeze_sha256=digest(OUT/'network_mechanism_freeze.json'),models={})
    for name in CONFIGS:
        p=np.load(OUT/'extension_predictions'/f'{name}.npy')
        result['models'][name]=dict(year_2023=freeze['models'][name]['year_2023'],year_2024=metrics(m[~early].reset_index(drop=True),p[~early]),selective_2024=selective(m,p,early))
    result['completed_utc']=stamp();write_json(resultpath,result);log('Network mechanism diagnostics complete')


if __name__=='__main__':
    with threadpool_limits(limits=2):run()
