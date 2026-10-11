"""Bounded-memory integrity and independent eligibility checks; no refits."""
import datetime as dt
import gc
import subprocess
import sys

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from common import CODE, OLD, OUT, digest, log, read_json, stamp, write_json, safe_to_unpickle
from prospective import SNAPSHOT, current_bills, serving_roster, CONTROL_MODELS
from run_models import predict, calibrate


def run():
    report={'verified_utc':stamp(),'checks':{}}
    test=subprocess.run([sys.executable,str(CODE/'test_refinement.py')],capture_output=True,text=True)
    (OUT/'boundary_test_output.txt').write_text(test.stdout+test.stderr,encoding='utf-8')
    assert test.returncode==0,test.stderr
    report['checks']['boundary_tests']='17 passed'
    original=read_json(OLD/'experiment_manifest.json')
    for name,expected in original['artifact_sha256'].items():
        assert digest(OLD/name)==expected,f'Original artifact changed: {name}'
    for name,expected in original['code_sha256'].items():
        assert digest(CODE.parent/'cosponsor_challengers'/name)==expected,f'Original code changed: {name}'
    report['checks']['phase_one_original_artifacts_and_code_unchanged']=True
    inputs={}
    specifications=[('member_network_receipt_v2.json','member_network_v2_{}'),('extra_feature_receipt.json','extra_{}'),('external_context_receipt.json','external_{}'),('marginal_coverage_receipt.json','marginal_coverage_{}')]
    for receipt,stem in specifications:
        r=read_json(OUT/receipt)
        for cg,s in r['splits'].items():
            path=OUT/(stem.format(cg)+'.f32');assert digest(path)==s['sha256']
            a=np.memmap(path,mode='r',dtype=np.float32,shape=(s['rows'],len(r['features'])))
            for start in range(0,len(a),100000):assert np.isfinite(a[start:start+100000]).all()
            inputs[path.name]=dict(shape=list(a.shape),sha256=s['sha256'],finite=True);del a
    report['inputs']=inputs
    selection=read_json(OUT/'extension_selection.json');result=read_json(OUT/'extension_results.json')
    assert result['selection_sha256']==digest(OUT/'extension_selection.json')
    m=pd.read_parquet(OLD/'meta_118.parquet');n=int(m.mature.sum());del m;gc.collect()
    frozen_models={**selection['models'],**read_json(OUT/'network_mechanism_freeze.json')['models']}
    for name,r in frozen_models.items():
        path=OUT/'extension_predictions'/f'{name}.npy'
        assert digest(path)==r['prediction_sha256']
        assert digest(OUT/'extension_models'/f'{name}.joblib')==r['model_sha256']
        p=np.load(path,mmap_mode='r');assert p.shape==(n,) and np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
    report['checks']['all_extension_predictions_and_models_match_freeze']=True
    manifest=read_json(SNAPSHOT/'forecast_manifest.json');sources=read_json(SNAPSHOT/'source_receipt.json')
    assert digest(SNAPSHOT/'source_receipt.json')==manifest['source_receipt_sha256']
    for name,r in sources['sources'].items():assert digest(SNAPSHOT/name)==r['sha256']
    archive=SNAPSHOT/f"issue_code_{manifest['code_sha256']}.py"
    assert digest(archive)==manifest['code_sha256']
    assert digest(SNAPSHOT/'features.npy')==manifest['features_sha256']
    assert digest(SNAPSHOT/'forecasts.parquet')==manifest['forecasts_sha256']
    frame=pd.read_parquet(SNAPSHOT/'forecasts.parquet');bills={b['key']:b for b in current_bills()};roster=serving_roster()
    day=dt.date.fromisoformat(manifest['forecast_date']).toordinal()
    assert not frame.duplicated(['bill','member']).any()
    for key,mid in frame[['bill','member']].itertuples(index=False,name=None):
        b=bills[key]
        assert 0<=day-b['intro']<=175 and b['finance_at_introduction'] and b['enacted']>day
        assert mid in roster and roster[mid]['chamber']==b['chamber'] and mid!=b['sponsor'] and b['joins'].get(mid,10**9)>day
    x=np.load(SNAPSHOT/'features.npy',mmap_mode='r');idx=np.random.default_rng(112).choice(len(x),size=2000,replace=False)
    assert np.isfinite(x).all() and x.shape==(len(frame),len(manifest['feature_names']))
    for name in CONTROL_MODELS:
        path=OLD/'models'/f'final_{name}.joblib';assert digest(path)==manifest['model_sha256'][name]
        if not safe_to_unpickle(path):raise SystemExit(f'refusing to unpickle {path}: it fails its integrity sidecar')
        artifact=joblib.load(path);expected=calibrate(predict(artifact,x[idx]),artifact['calibration'])
        np.testing.assert_allclose(frame[name].to_numpy()[idx],expected,atol=1e-7,rtol=1e-6)
        rank=frame.groupby('bill')[name].rank(method='first',ascending=False).astype(int)
        assert np.array_equal(rank,frame[name+'_rank'])
    report['checks']['prospective_all_rows_independently_eligible']=len(frame)
    report['checks']['prospective_control_repredictions_checked']=2000*len(CONTROL_MODELS)
    addon=read_json(SNAPSHOT/'network_forecast_manifest.json')
    assert digest(SNAPSHOT/'forecast_manifest.json')==addon['original_forecast_manifest_sha256']
    assert digest(SNAPSHOT/'network_forecasts.parquet')==addon['forecasts_sha256']
    assert digest(SNAPSHOT/'network_features.npy')==addon['features_sha256']
    assert digest(SNAPSHOT/'boosted_network_refit.joblib')==addon['model_sha256']
    assert dt.datetime.fromisoformat(addon['issued_utc']).date().isoformat()==manifest['forecast_date']
    nf=pd.read_parquet(SNAPSHOT/'network_forecasts.parquet');assert nf[['bill','member']].equals(frame[['bill','member']])
    name=addon['model_name'];assert np.isfinite(nf[name]).all() and nf[name].between(0,1).all()
    assert np.array_equal(nf.groupby('bill')[name].rank(method='first',ascending=False).astype(int),nf[name+'_rank'])
    from fit_extensions import COV
    network=np.load(SNAPSHOT/'network_features.npy',mmap_mode='r')
    design=np.column_stack([x[idx][:,[manifest['feature_names'].index(n) for n in COV]],network[idx]])
    refit_path=SNAPSHOT/'boosted_network_refit.joblib'
    if not safe_to_unpickle(refit_path):raise SystemExit(f'refusing to unpickle {refit_path}: it fails its integrity sidecar')
    artifact=joblib.load(refit_path)
    expected=calibrate(artifact['model'].predict_proba(design)[:,1],artifact['calibration'])
    np.testing.assert_allclose(nf[name].to_numpy()[idx],expected,atol=1e-7,rtol=1e-6)
    rankfreeze=read_json(OUT/'network_ranker_freeze.json')
    assert digest(OUT/'network_ranker_probabilities_118.npy')==rankfreeze['prediction_sha256']
    assert digest(OUT/'ranker_models/network_ranker.txt')==rankfreeze['model_sha256']
    policy=read_json(SNAPSHOT/'shortlist_policy.json')
    assert policy['control_prediction_sha256']==manifest['forecasts_sha256']
    assert policy['network_prediction_sha256']==addon['forecasts_sha256']
    assert dt.datetime.fromisoformat(policy['issued_utc']).date().isoformat()==manifest['forecast_date']
    report['checks']['prospective_network_same_candidates_and_frozen_sources']=True
    report['status']='passed';write_json(OUT/'verification_receipt.json',report)
    log('Refinement integrity checks passed; original experiment unchanged')


if __name__=='__main__':
    with threadpool_limits(limits=2):run()
