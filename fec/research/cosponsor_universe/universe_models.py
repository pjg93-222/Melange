"""Frozen evidence-family comparisons on the same historical forecast rows."""
import gc
import datetime as dt

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from universe_common import CODE, OLD, PREVIOUS, OUT, digest, log, read_json, stamp, write_json
import build_panel
import run_models
import fit_extensions
from fit_extensions import Panel as PreviousPanel, COV, DYN, NETWORK, DEMOGRAPHIC, LOBBY, TEXT
from universe_conduct_features import HISTORY, ACTIVITY, STAGES
from universe_psychology_features import FEATURES as LANGUAGE
from run_models import SEED, metrics, platt_fit, calibrate, prepare_hazard, hazard_design
from build_panel import FEATURES, BASE, ENHANCED

EARLY_END=dt.date(2024,1,1).toordinal()
ELECTION=['election_share','election_margin','election_log_total_votes','election_uncontested',
          'election_years_ago','election_missing','prior_service_years','prior_service_missing']
LANGUAGE_COVERAGE=[x for x in LANGUAGE if any(x.endswith(t) for t in ['log_turns','log_words','log_packages','missing','thin_under_800_words'])]


def menu():
    media=read_json(OUT/'relational_panel_receipt.json')['features']
    amendments=read_json(OUT/'amendment_receipt.json')['features']
    new=HISTORY+ACTIVITY+STAGES+ELECTION+amendments+LANGUAGE+media
    universe=COV+new+NETWORK+DEMOGRAPHIC+LOBBY+TEXT
    models={name:dict(kind='boosted',features=COV+features,placebo=False) for name,features in {
      'boosted_conduct_history':HISTORY,'boosted_activity':ACTIVITY,'boosted_stages':STAGES,
      'boosted_elections':ELECTION,'boosted_amendments':amendments,'boosted_language':LANGUAGE,'boosted_language_coverage':LANGUAGE_COVERAGE,
      'boosted_media':media,'boosted_all_new':new}.items()}
    models.update({
      'boosted_universe':dict(kind='boosted',features=universe,placebo=False),
      'logistic_universe':dict(kind='logistic',features=universe,placebo=False),
      'boosted_universe_no_language':dict(kind='boosted',features=[f for f in universe if f not in LANGUAGE],placebo=False),
      'boosted_universe_no_media':dict(kind='boosted',features=[f for f in universe if f not in media],placebo=False),
      'boosted_language_placebo':dict(kind='boosted',features=COV+LANGUAGE,placebo=True)})
    # User requested a fixed continuing-member benchmark after the coverage audit.
    # Raw pre-cutoff language is eligible conditionally within this selected cohort;
    # current fitted trait scores remain excluded.
    clean=DYN+HISTORY+ACTIVITY+STAGES+ELECTION+amendments+NETWORK+DEMOGRAPHIC+LOBBY+TEXT
    models['boosted_reconstructed_context']=dict(kind='boosted',features=clean,placebo=False)
    models['logistic_reconstructed_context']=dict(kind='logistic',features=clean,placebo=False)
    for name,spec in models.items():
        public_free=name in ['boosted_conduct_history','boosted_activity','boosted_stages','boosted_elections','boosted_amendments',
                          'boosted_reconstructed_context','logistic_reconstructed_context']
        if public_free:spec['features']=[f for f in spec['features'] if f not in set(COV)-set(DYN)]
        spec['historical_selection_eligible']=not spec['placebo']
        spec['role']='challenger'
        spec['source_qualification']='continuing_member_conditional_reconstruction' if public_free else 'continuing_member_conditional_text_media'
        assert len(spec['features'])==len(set(spec['features']))
    controls={'logistic_base':('logistic',BASE),'logistic_history':('logistic',BASE+ENHANCED),
      'logistic_dynamic':('logistic',DYN),'time_to_sign':('hazard',DYN),'boosted_dynamic':('boosted',DYN),
      'boosted_public_coverage':('boosted',COV),'boosted_network':('boosted',COV+NETWORK),
      'boosted_context':('boosted',COV+NETWORK+DEMOGRAPHIC+LOBBY)}
    for name,(kind,features) in controls.items():
        models[name]=dict(kind=kind,features=features,placebo=False,historical_selection_eligible=True,
          role='refit_control',source_qualification='continuing_member_refit_control')
    return models


class Panel(PreviousPanel):
    def __init__(self,cg):
        super().__init__(cg)
        self.cg=cg;self.ids=read_json(OLD/'identifiers.json')['members'];self.static={};self.missing={}
        gold=set(read_json(OUT/'gold_cohort.json')['member_ids'])
        self.gold=np.array([mid in gold for mid in self.ids])[self.meta.member.to_numpy()]
        specs=[('conduct_history.csv','member',HISTORY),('psychology_history.csv','member',LANGUAGE),
               ('election_history.csv','memberBioguide',ELECTION),
               ('amendment_history.csv','member',read_json(OUT/'amendment_receipt.json')['features'])]
        for file,key,names in specs:
            frame=pd.read_csv(OUT/file);frame=frame[frame.congress==cg].set_index(key)
            assert frame.index.is_unique
            frame=frame.reindex(self.ids)
            for name in names:
                values=frame[name].to_numpy(dtype=np.float32)
                # No recorded source means unavailable, not a measured zero-rate.
                default=1 if ('missing' in name or 'thin_under' in name) else 0
                self.static[name]=np.nan_to_num(values,nan=default,posinf=default,neginf=default)
            used=np.unique(self.meta.member.to_numpy()[self.gold])
            self.missing[file]=int(frame.iloc[used][names].isna().all(axis=1).sum())
        for file,names in [(f'conduct_dynamic_{cg}.f32',ACTIVITY+STAGES),
                           (f'relational_panel_{cg}.f32',read_json(OUT/'relational_panel_receipt.json')['features'])]:
            a=np.memmap(OUT/file,dtype=np.float32,mode='r',shape=(len(self.meta),len(names)))
            for j,name in enumerate(names):self.columns[name]=(a,j)
        self.permutation=np.arange(len(self.ids))
        # A member cannot occupy two chambers simultaneously in these frozen panels;
        # members who switched chambers are grouped separately for the placebo.
        member_chambers=self.meta[self.gold].groupby('member').senate.agg(['min','max'])
        rng=np.random.default_rng(SEED+500+cg)
        for (lo,hi),block in member_chambers.groupby(['min','max']):
            idx=block.index.to_numpy(dtype=int)
            self.permutation[idx]=rng.permutation(idx)

    def design(self,indices,names,placebo=False):
        result=np.empty((len(indices),len(names)),dtype=np.float32)
        member=self.meta.member.to_numpy()[indices]
        for j,name in enumerate(names):
            if name in self.static:
                idx=self.permutation[member] if placebo and name in LANGUAGE else member
                result[:,j]=self.static[name][idx]
            else:
                a,k=self.columns[name];result[:,j]=a[indices,k]
        if not np.isfinite(result).all():raise ValueError('Nonfinite feature matrix')
        return result


def predict(artifact,panel,indices):
    result=np.empty(len(indices),dtype=np.float32)
    for start in range(0,len(indices),100000):
        idx=indices[start:start+100000]
        if artifact['kind']=='hazard':
            x=panel.design(idx,FEATURES);total=np.zeros(len(idx))
            for step in range(5):
                xx=hazard_design(x,artifact['features'],step)
                rate=artifact['model'].predict(artifact['scaler'].transform(xx).astype(np.float64))
                total+=np.clip(rate,0,100)*(7 if step<4 else 2)
            result[start:start+len(idx)]=-np.expm1(-total)
            continue
        x=panel.design(idx,artifact['features'],artifact['placebo'])
        if artifact['scaler'] is not None:x=artifact['scaler'].transform(x).astype(np.float64)
        result[start:start+len(idx)]=artifact['model'].predict_proba(x)[:,1]
    return np.clip(result,1e-8,1-1e-8)


def run():
    if (OUT/'universe_results.json').exists():raise RuntimeError('New evaluation is already frozen')
    models=menu();(OUT/'models').mkdir(exist_ok=True);(OUT/'predictions').mkdir(exist_ok=True)
    receipts=['conduct_receipt.json','psychology_history_receipt.json','election_history.receipt.json','relational_panel_receipt.json','amendment_receipt.json','gold_cohort.json','gold_cohort.receipt.json']
    features=['conduct_history.csv','psychology_history.csv','election_history.csv','amendment_history.csv']
    features += [f'{prefix}_{cg}.f32' for cg in [117,118] for prefix in ['conduct_dynamic','relational_panel']]
    plan=dict(created_utc=stamp(),models=models,boosted_config=dict(max_leaf_nodes=15,max_iter=200,learning_rate=.06,l2_regularization=10,min_samples_leaf=50),
      logistic_config=dict(C=1.,max_iter=150,solver='newton-cholesky',tol=1e-7),training=117,selection=2023,assessment=2024,
      hazard_config=dict(alpha=1e-5,max_iter=250,tol=1e-7,solver='newton-cholesky'),
      status='retrospective_continuing_member_development',protocol_sha256=digest(CODE/'PROTOCOL.md'),code_sha256=digest(__file__),
      supporting_code_sha256={f:digest(CODE/f) for f in ['universe_common.py','universe_conduct_features.py',
          'universe_psychology_features.py','universe_election_features.py','universe_relational_features.py',
          'universe_relational_panel.py','universe_statistics.py','universe_amendment_features.py','universe_gold_cohort.py']},
      dependency_code_sha256={module.__file__:digest(module.__file__) for module in [build_panel,run_models,fit_extensions]},
      original_panel_sha256={f:digest(OLD/f) for f in ['identifiers.json','meta_117.parquet','meta_118.parquet','X_117.f32','X_118.f32']},
      input_sha256={f:digest(OUT/f) for f in receipts+features},previous_manifests={str(p):digest(p) for p in [OLD/'experiment_manifest.json',PREVIOUS/'experiment_manifest.json']})
    plan_path=OUT/'universe_plan.json'
    if plan_path.exists():
        existing=read_json(plan_path)
        for key in ['models','protocol_sha256','code_sha256','supporting_code_sha256','dependency_code_sha256','original_panel_sha256','input_sha256','previous_manifests']:assert existing[key]==plan[key],key
    else:write_json(plan_path,plan)
    train=Panel(117);val=Panel(118)
    y=train.meta.y.to_numpy();eligible=train.meta.mature.to_numpy().astype(bool)&train.gold
    selected=eligible & ((y>0)|(np.random.default_rng(SEED+117).random(len(y))<.1))
    indices=np.flatnonzero(selected);target=y[indices];weight=np.where(target>0,1.,10.)
    vi=np.flatnonzero(val.meta.mature.to_numpy().astype(bool)&val.gold);m=val.meta.iloc[vi].reset_index(drop=True)
    early=m.day.to_numpy()<EARLY_END;me=m[early].reset_index(drop=True)
    selection_path=OUT/'universe_selection.json'
    selection=read_json(selection_path) if selection_path.exists() else dict(started_utc=stamp(),plan_sha256=digest(plan_path),models={},
       training_rows=len(indices),training_events=int(target.sum()),panel_missing_rows={117:train.missing,118:val.missing})
    assert selection['plan_sha256']==digest(plan_path),'Selection is not bound to this frozen plan'
    for name,spec in models.items():
        if name in selection['models']:
            recorded=selection['models'][name]
            assert digest(OUT/f'predictions/{name}.npy')==recorded['prediction_sha256']
            assert digest(OUT/f'models/{name}.joblib')==recorded['model_sha256']
            continue
        log(f'Fitting {name}: {len(indices):,} weighted rows; {len(spec["features"])} features')
        x=train.design(indices,spec['features'],spec['placebo']);scaler=None
        if spec['kind']=='boosted':
            model=HistGradientBoostingClassifier(**plan['boosted_config'],early_stopping=False,random_state=SEED)
            model.fit(x,target,sample_weight=weight)
        elif spec['kind']=='logistic':
            scaler=StandardScaler().fit(x,sample_weight=weight)
            xx=scaler.transform(x).astype(np.float64)
            model=LogisticRegression(**plan['logistic_config'],random_state=SEED)
            model.fit(xx,target,sample_weight=weight);del xx
        else:
            del x
            full=train.design(indices,FEATURES)
            xx,yy,ww=prepare_hazard(full,target,weight,train.meta.duration.to_numpy()[indices],spec['features']);del full
            scaler=StandardScaler().fit(xx,sample_weight=ww)
            xx=scaler.transform(xx).astype(np.float64)
            model=PoissonRegressor(**plan['hazard_config']);model.fit(xx,yy,sample_weight=ww)
            del xx,yy,ww;x=None
        del x
        artifact={**spec,'model':model,'scaler':scaler}
        raw=predict(artifact,val,vi);cal=platt_fit(m.y.to_numpy()[early],raw[early]);p=calibrate(raw,cal)
        artifact['calibration_2023']=cal
        np.save(OUT/f'predictions/{name}.npy',p);joblib.dump(artifact,OUT/f'models/{name}.joblib')
        measured=metrics(me,p[early]);selection['models'][name]=dict(selection_2023=measured,
          prediction_sha256=digest(OUT/f'predictions/{name}.npy'),model_sha256=digest(OUT/f'models/{name}.joblib'))
        write_json(selection_path,selection)
        log(f'2023 selection {name}: P@8={measured["precision_at_8"]:.6f}; AP={measured["average_precision"]:.6f}')
        del model,artifact,raw,p;gc.collect()
    if 'frozen_utc' not in selection:
        winner=max((n for n,s in models.items() if s['historical_selection_eligible']),key=lambda n:selection['models'][n]['selection_2023']['precision_at_8'])
        selection.update(chosen=winner,frozen_utc=stamp());write_json(selection_path,selection)
    # All new predictions and selection frozen before loading later-period metrics.
    results=dict(completed_utc=stamp(),selection_sha256=digest(selection_path),chosen_on_2023=selection['chosen'],
                 status='development_only_not_independent_confirmation',models={})
    for name in models:
        p=np.load(OUT/f'predictions/{name}.npy')
        qualification=models[name]['source_qualification']
        results['models'][name]=dict(source_qualification=qualification,year_2023=metrics(me,p[early]),year_2024=metrics(m[~early].reset_index(drop=True),p[~early]))
        log(f'2024 development {name}: P@8={results["models"][name]["year_2024"]["precision_at_8"]:.6f}')
        del p;gc.collect()
    write_json(OUT/'universe_results.json',results)


if __name__=='__main__':
    with threadpool_limits(limits=4):run()
