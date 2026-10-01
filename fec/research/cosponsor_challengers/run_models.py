"""Temporal development, one frozen final test, and paired uncertainty analysis."""
from __future__ import annotations

import argparse
import datetime as dt
import gc
import json
import os
from pathlib import Path
import time

os.environ.setdefault("OMP_NUM_THREADS","4")
os.environ.setdefault("OPENBLAS_NUM_THREADS","4")
os.environ.setdefault("MKL_NUM_THREADS","4")
import joblib
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from audit_data import OUT,digest
from build_panel import FEATURES,BASE,ENHANCED,DYNAMIC,PUBLIC,get_bills,normalize_title

SEED=20260905
CHUNK=200000
MODELS={
    "logistic_base":("logistic",BASE),
    "logistic_history":("logistic",BASE+ENHANCED),
    "logistic_dynamic":("logistic",BASE+ENHANCED+DYNAMIC),
    "boosted_history":("boosted",BASE+ENHANCED),
    "boosted_dynamic":("boosted",BASE+ENHANCED+DYNAMIC),
    "time_to_sign":("hazard",BASE+ENHANCED+DYNAMIC),
    "logistic_public":("logistic",BASE+ENHANCED+DYNAMIC+PUBLIC),
    "boosted_public_coverage":("boosted",BASE+ENHANCED+DYNAMIC+[PUBLIC[i] for i in (0,1,4,7,8)]),
    "boosted_public":("boosted",BASE+ENHANCED+DYNAMIC+PUBLIC),
    "time_to_sign_public":("hazard",BASE+ENHANCED+DYNAMIC+PUBLIC),
}


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def log(message):
    line=stamp()+" "+str(message)
    print(line,flush=True)
    with (OUT/"model_run.log").open("a",encoding="utf-8") as f:
        f.write(line+"\n")


def load(cg):
    meta=pd.read_parquet(OUT/f"meta_{cg}.parquet")
    x=np.memmap(OUT/f"X_{cg}.f32",dtype=np.float32,mode="r",shape=(len(meta),len(FEATURES)))
    return x,meta


def training_sample(congresses,hazard=False):
    matrices,labels,weights,durations=[],[],[],[]
    for cg in congresses:
        x,m=load(cg)
        eligible=np.ones(len(m),dtype=bool) if hazard else m.mature.to_numpy().astype(bool)
        events=m.event.to_numpy().astype(bool)
        rng=np.random.default_rng(SEED+cg)
        inclusion_rate=.02 if hazard else .10
        selected=eligible & (events | (rng.random(len(m))<inclusion_rate))
        matrices.append(np.array(x[selected],dtype=np.float32))
        labels.append(m.event.to_numpy()[selected])
        weights.append(np.where(events[selected],1.0,1/inclusion_rate))
        durations.append(m.duration.to_numpy()[selected])
    return np.concatenate(matrices),np.concatenate(labels),np.concatenate(weights),np.concatenate(durations)


def hazard_design(x,feature_names,step):
    out=np.empty((len(x),len(feature_names)+5),dtype=np.float32)
    cols=[FEATURES.index(f) for f in feature_names]
    out[:,:len(cols)]=x[:,cols]
    offset=7*step
    if "bill_age" in feature_names:
        index=feature_names.index("bill_age")
        out[:,index]+=offset
    if "log_bill_age" in feature_names:
        out[:,feature_names.index("log_bill_age")]=np.log1p(x[:,FEATURES.index("bill_age")]+offset)
    out[:,len(cols):]=0
    out[:,len(cols)+step]=1
    return out


def prepare_hazard(x,y,w,duration,feature_names):
    xx,yy,ww=[],[],[]
    for step in range(5):
        lo,hi=7*step,min(30,7*(step+1))
        at_risk=duration>lo
        exposure=np.minimum(duration[at_risk],hi)-lo
        event=y[at_risk]*(duration[at_risk]<=hi)
        xx.append(hazard_design(x[at_risk],feature_names,step))
        yy.append(event/exposure)
        ww.append(w[at_risk]*exposure)
    return np.concatenate(xx),np.concatenate(yy),np.concatenate(ww)


def fit_model(name,config,sample):
    kind,feature_names=MODELS[name]
    x,y,w,duration=sample
    cols=[FEATURES.index(f) for f in feature_names]
    if kind=="hazard":
        design,target,weight=prepare_hazard(x,y,w,duration,feature_names)
        scaler=StandardScaler().fit(design,sample_weight=weight)
        design=scaler.transform(design).astype(np.float64)
        model=PoissonRegressor(alpha=config["alpha"],max_iter=250,tol=1e-7,solver="newton-cholesky")
        model.fit(design,target,sample_weight=weight)
    elif kind=="logistic":
        design=x[:,cols]
        scaler=StandardScaler().fit(design,sample_weight=w)
        design=scaler.transform(design).astype(np.float64)
        model=LogisticRegression(C=config["C"],solver="newton-cholesky",max_iter=150,tol=1e-7,random_state=SEED)
        model.fit(design,y,sample_weight=w)
    else:
        scaler=None
        model=HistGradientBoostingClassifier(learning_rate=.06,max_leaf_nodes=config["max_leaf_nodes"],
                                             max_iter=config["max_iter"],l2_regularization=10,min_samples_leaf=50,
                                             early_stopping=False,random_state=SEED)
        model.fit(x[:,cols],y,sample_weight=w)
    return dict(kind=kind,features=feature_names,scaler=scaler,model=model,config=config)


def predict(artifact,x):
    values=np.empty(len(x),dtype=np.float32)
    feature_names=artifact["features"]
    cols=[FEATURES.index(f) for f in feature_names]
    for start in range(0,len(x),CHUNK):
        block=np.asarray(x[start:start+CHUNK])
        if artifact["kind"]=="hazard":
            total=np.zeros(len(block))
            for step in range(5):
                design=hazard_design(block,feature_names,step)
                design=artifact["scaler"].transform(design)
                rate=artifact["model"].predict(design)
                total+=np.clip(rate,0,100)*(7 if step<4 else 2)
            p=-np.expm1(-total)
        else:
            design=block[:,cols]
            if artifact["scaler"] is not None:
                design=artifact["scaler"].transform(design)
            p=artifact["model"].predict_proba(design)[:,1]
        values[start:start+len(block)]=np.clip(p,1e-8,1-1e-8)
    return values


def configs(kind):
    if kind=="logistic":
        return [{"C":.1},{"C":1.0}]
    if kind=="hazard":
        return [{"alpha":.00001},{"alpha":.000001}]
    return [{"max_leaf_nodes":leaves,"max_iter":iterations} for leaves in (7,15) for iterations in (100,200)]


def platt_fit(y,p):
    design=logit(np.clip(p,1e-7,1-1e-7)).reshape(-1,1)
    cal=LogisticRegression(C=1e6,solver="lbfgs",max_iter=100)
    cal.fit(design,y)
    # A reversed ordering is a failed ranking model, not a calibration opportunity.
    if cal.coef_[0,0]<0:
        return {"intercept":float(logit(np.mean(y))),"slope":0.0}
    return {"intercept":float(cal.intercept_[0]),"slope":float(cal.coef_[0,0])}


def calibrate(p,cal):
    return expit(cal["intercept"]+cal["slope"]*logit(np.clip(p,1e-7,1-1e-7))).astype(np.float32)


def basic_metrics(y,p):
    p=np.clip(np.asarray(p,dtype=np.float64),1e-8,1-1e-8)
    return dict(rows=len(y),events=int(np.sum(y)),base_rate=float(np.mean(y)),
                average_precision=float(average_precision_score(y,p)),brier=float(brier_score_loss(y,p)),
                log_loss=float(log_loss(y,p,labels=[0,1])),roc_auc=float(roc_auc_score(y,p)))


def topk_vectors(meta,y,p,k):
    group=meta.group.to_numpy()
    order=np.lexsort((meta.member.to_numpy(),-p,group))
    ordered_group=group[order]
    starts=np.r_[True,ordered_group[1:]!=ordered_group[:-1]]
    rank=np.arange(len(order))-np.maximum.accumulate(np.where(starts,np.arange(len(order)),0))
    chosen=order[rank<k]
    return chosen


def metrics(meta,p,subgroups=False):
    y=meta.y.to_numpy()
    result=basic_metrics(y,p)
    result["bills"]=int(meta.bill.nunique())
    result["bill_dates"]=int(meta.group.nunique())
    for k in (8,25):
        chosen=topk_vectors(meta,y,p,k)
        hits=int(y[chosen].sum())
        result[f"precision_at_{k}"]=hits/len(chosen)
        result[f"recall_at_{k}"]=hits/max(1,int(y.sum()))
        result[f"hits_at_{k}"]=hits
        result[f"slots_at_{k}"]=len(chosen)
    bins=np.array([0,.001,.0025,.005,.01,.02,.05,.1,.2,.5,1.00001])
    code=np.digitize(p,bins)-1
    result["calibration"]=[dict(low=float(bins[i]),high=float(bins[i+1]),rows=int((code==i).sum()),
                                predicted=float(np.mean(p[code==i])),observed=float(np.mean(y[code==i])))
                            for i in range(len(bins)-1) if (code==i).any()]
    if subgroups:
        sets={"House":meta.senate.eq(0),"Senate":meta.senate.eq(1),"Democratic":meta.democrat.eq(1),
              "non_Democratic":meta.democrat.eq(0),"zero_prior_joiners":meta.n_joined.eq(0),"some_prior_joiners":meta.n_joined.gt(0)}
        for age in sorted(meta.age.unique()):
            sets[f"age_{age}"]=meta.age.eq(age)
        result["subgroups"]={key:basic_metrics(y[mask],p[mask]) for key,mask in sets.items() if mask.sum() and y[mask].sum()>0}
    return result


def develop():
    outdir=OUT/"models"
    outdir.mkdir(exist_ok=True)
    xval,mval=load(118)
    mask=mval.mature.to_numpy().astype(bool)
    xv=xval
    mv=mval[mask].reset_index(drop=True)
    samples={"binary":training_sample([117]),"hazard":training_sample([117],True)}
    log(f"Development: {len(mv):,} complete rows, {int(mv.y.sum()):,} events; train samples { {k:len(v[0]) for k,v in samples.items()} }")
    path=OUT/"development_results.json"
    results=json.loads(path.read_text()) if path.exists() else {"created_utc":stamp(),"models":{}}
    for name,(kind,_) in MODELS.items():
        if name in results["models"]:
            log(f"Reusing completed development {name}")
            continue
        candidates=[]
        best=None
        for config in configs(kind):
            started=time.perf_counter()
            log(f"Fitting development {name} {config}")
            artifact=fit_model(name,config,samples["hazard" if kind=="hazard" else "binary"])
            p=predict(artifact,xv)[mask]
            measured=basic_metrics(mv.y.to_numpy(),p)
            candidates.append(dict(config=config,metrics=measured,elapsed_seconds=round(time.perf_counter()-started,2)))
            log(f"Development {name} {config}: AP={measured['average_precision']:.6f}, Brier={measured['brier']:.6f}")
            if best is None or measured["average_precision"]>best[0]:
                best=(measured["average_precision"],artifact,p)
            gc.collect()
        cal=platt_fit(mv.y.to_numpy(),best[2])
        joblib.dump(best[1],outdir/f"development_{name}.joblib")
        np.save(OUT/f"development_prediction_{name}.npy",best[2])
        results["models"][name]=dict(selected=best[1]["config"],candidates=candidates,calibration=cal,
                                      selected_metrics=metrics(mv,calibrate(best[2],cal)))
        path.write_text(json.dumps(results,indent=2),encoding="utf-8")
    existing=np.isfinite(mv.existing_score.to_numpy())
    cal=platt_fit(mv.y.to_numpy()[existing],mv.existing_score.to_numpy()[existing])
    results["existing_production"]=dict(calibration=cal,rows=int(existing.sum()),
                                        metrics=metrics(mv[existing].reset_index(drop=True),calibrate(mv.existing_score.to_numpy()[existing],cal)))
    results["frozen_utc"]=stamp()
    results["protocol_sha256"]=digest(Path(__file__).parent/"PROTOCOL.md")
    results["runner_sha256"]=digest(__file__)
    path.write_text(json.dumps(results,indent=2),encoding="utf-8")
    log("DEVELOPMENT COMPLETE; configurations and calibration locked")


def cluster_codes(meta):
    ids=json.loads((OUT/"identifiers.json").read_text())
    parent={}
    def root(k):
        parent.setdefault(k,k)
        if parent[k]!=k:
            parent[k]=root(parent[k])
        return parent[k]
    def union(a,b):
        ra,rb=root(a),root(b)
        parent[max(ra,rb)]=min(ra,rb)
    links=json.loads((OUT/"analogue_links.json").read_text())
    for a,link in links.items():
        union(a,link["prior_key"])
    title_index={}
    for b in get_bills():
        for title in b["short_titles"]:
            nt=normalize_title(title)
            if len(nt.split())>=4:
                if nt in title_index:
                    union(b["key"],title_index[nt])
                title_index[nt]=b["key"]
    bill_to_cluster={i:root(key) for i,key in enumerate(ids["bills"])}
    families=meta.bill.map(bill_to_cluster)
    code,unique=pd.factorize(families,sort=True)
    return code,len(unique)


def uncertainty(meta,preds,baseline="logistic_base",reps=1200):
    """Paired family bootstrap; AP intervals use explicitly labeled quantile bins."""
    codes,ncluster=cluster_codes(meta)
    y=meta.y.to_numpy()
    rng=np.random.default_rng(SEED)
    weights=rng.multinomial(ncluster,np.full(ncluster,1/ncluster),size=reps).astype(np.float64)
    sizes=np.bincount(codes,minlength=ncluster)
    denominator=weights@sizes
    stats={}
    for name,p in preds.items():
        log(f"Bootstrap {name}, {ncluster} legislative families")
        p=np.clip(p,1e-7,1-1e-7)
        brier_totals=np.bincount(codes,weights=(p-y)**2,minlength=ncluster)
        loss_totals=np.bincount(codes,weights=-(y*np.log(p)+(1-y)*np.log1p(-p)),minlength=ncluster)
        brier=weights@brier_totals/denominator
        loss=weights@loss_totals/denominator
        # Exact shortlist statistic: resample complete bill/date groups within families.
        chosen=topk_vectors(meta,y,p,8)
        hits=np.bincount(codes[chosen],weights=y[chosen],minlength=ncluster)
        slots=np.bincount(codes[chosen],minlength=ncluster)
        precision=weights@hits/(weights@slots)
        edges=np.unique(np.quantile(p,np.linspace(0,1,2049)))
        if len(edges)<2:
            edges=np.array([float(p[0])-1e-8,float(p[0])+1e-8])
        bins=np.searchsorted(edges[1:-1],p,side="right")
        nbins=len(edges)-1
        flat=codes*nbins+bins
        counts=np.bincount(flat,minlength=ncluster*nbins).reshape(ncluster,nbins)[:,::-1]
        positives=np.bincount(flat,weights=y,minlength=ncluster*nbins).reshape(ncluster,nbins)[:,::-1]
        bc=weights@counts
        bp=weights@positives
        cumpos=np.cumsum(bp,axis=1)
        cumall=np.cumsum(bc,axis=1)
        ap=np.sum(bp*np.divide(cumpos,cumall,out=np.zeros_like(cumpos),where=cumall>0),axis=1)/np.maximum(1,bp.sum(axis=1))
        original_p=positives.sum(axis=0)
        original_n=counts.sum(axis=0)
        binned_point=float(np.sum(original_p*np.cumsum(original_p)/np.maximum(1,np.cumsum(original_n)))/max(1,y.sum()))
        stats[name]=dict(brier=brier,log_loss=loss,precision_at_8=precision,average_precision_binned=ap,
                         binned_ap_point=binned_point,exact_ap=float(average_precision_score(y,p)))
    comparisons={}
    ncomparisons=max(1,len(preds)-1)
    for name in preds:
        if name==baseline:
            continue
        comparison={}
        for metric in ("brier","log_loss","precision_at_8","average_precision_binned"):
            delta=stats[name][metric]-stats[baseline][metric]
            comparison[metric]=dict(delta_mean=float(delta.mean()),ci95=np.quantile(delta,[.025,.975]).tolist(),
                                    familywise_interval=np.quantile(delta,[.025/ncomparisons,1-.025/ncomparisons]).tolist())
        comparison["ap_binning_error"]=stats[name]["binned_ap_point"]-stats[name]["exact_ap"]
        comparisons[name]=comparison
    # Crossed member-by-family sensitivity for Brier differences; no row independence assumption.
    member_codes,nmembers=pd.factorize(meta.member,sort=True)
    nmembers=len(nmembers)
    member_weights=rng.multinomial(nmembers,np.full(nmembers,1/nmembers),size=reps)
    flat=codes*nmembers+member_codes
    cross_counts=np.bincount(flat,minlength=ncluster*nmembers).reshape(ncluster,nmembers)
    cross_den=np.sum((weights@cross_counts)*member_weights,axis=1)
    base_error=(preds[baseline]-y)**2
    for name,p in preds.items():
        if name==baseline:
            continue
        cross_error=np.bincount(flat,weights=(p-y)**2-base_error,minlength=ncluster*nmembers).reshape(ncluster,nmembers)
        delta=np.sum((weights@cross_error)*member_weights,axis=1)/cross_den
        comparisons[name]["crossed_member_family_brier"]=dict(ci95=np.quantile(delta,[.025,.975]).tolist(),
                                                              familywise_interval=np.quantile(delta,[.025/ncomparisons,1-.025/ncomparisons]).tolist())
    return dict(replicates=reps,clusters=ncluster,baseline=baseline,comparisons=comparisons,
                ap_interval_note="Bootstrap AP uses at most 2048 score-quantile bins. Exact AP is reported as the point metric; binning error is disclosed. Top-8 and Brier bootstrap statistics are exact for resampled clusters.")


def final_test():
    selection_path=OUT/"development_results.json"
    selection=json.loads(selection_path.read_text())
    if "frozen_utc" not in selection:
        raise RuntimeError("Development must be complete before final test")
    final_dir=OUT/"models"
    x,m=load(119)
    mask=m.mature.to_numpy().astype(bool)
    xx=x
    mm=m[mask].reset_index(drop=True)
    pred_dir=OUT/"final_predictions"
    pred_dir.mkdir(exist_ok=True)
    freeze_path=OUT/"final_prediction_freeze.json"
    if not freeze_path.exists():
        samples={"binary":training_sample([117,118]),"hazard":training_sample([117,118],True)}
        for name,(kind,_) in MODELS.items():
            if (pred_dir/f"{name}.npy").exists() and (final_dir/f"final_{name}.joblib").exists():
                log(f"Reusing already frozen final predictions {name}")
                continue
            config=selection["models"][name]["selected"]
            log(f"Final refit {name} {config}; test outcomes unopened by metrics")
            artifact=fit_model(name,config,samples["hazard" if kind=="hazard" else "binary"])
            raw=predict(artifact,xx)[mask]
            artifact["calibration"]=selection["models"][name]["calibration"]
            joblib.dump(artifact,final_dir/f"final_{name}.joblib")
            np.save(pred_dir/f"{name}.npy",calibrate(raw,artifact["calibration"]))
            gc.collect()
        del samples
        gc.collect()
        freeze=dict(frozen_utc=stamp(),selection_sha256=digest(selection_path),rows=len(mm),
                    protocol_sha256=digest(Path(__file__).parent/"PROTOCOL.md"),runner_sha256=digest(__file__),
                    predictions={name:digest(pred_dir/f"{name}.npy") for name in MODELS})
        freeze_path.write_text(json.dumps(freeze,indent=2))
        log("ALL FINAL PREDICTIONS FROZEN; beginning the single final evaluation")
    preds={name:np.load(pred_dir/f"{name}.npy") for name in MODELS}
    result_path=OUT/"final_results.json"
    result=json.loads(result_path.read_text()) if result_path.exists() else dict(evaluated_utc=stamp(),models={})
    for name,p in preds.items():
        if name not in result["models"]:
            result["models"][name]=metrics(mm,p,True)
            log(f"FINAL {name}: AP {result['models'][name]['average_precision']:.6f}, P@8 {result['models'][name]['precision_at_8']:.6f}")
            result_path.write_text(json.dumps(result,indent=2))
    public_covered=((xx[:,FEATURES.index("public_topic_mentions_365d")]>0)|(xx[:,FEATURES.index("public_bill_mentions_365d")]>0))[mask]
    result["public_coverage"]=dict(rows=int(public_covered.sum()),events=int(mm.y.to_numpy()[public_covered].sum()),
                                   fraction=float(public_covered.mean()),explicit_bill_support_rows=int((xx[:,FEATURES.index("public_bill_support_365d")][mask]>0).sum()))
    result["public_covered_metrics"]={name:metrics(mm[public_covered].reset_index(drop=True),p[public_covered]) for name,p in preds.items()}
    common=np.isfinite(mm.existing_score.to_numpy())
    cm=mm[common].reset_index(drop=True)
    existing=calibrate(cm.existing_score.to_numpy(),selection["existing_production"]["calibration"])
    common_preds={name:p[common] for name,p in preds.items()}
    common_preds["existing_production"]=existing
    result["existing_common_population"]={name:metrics(cm,p) for name,p in common_preds.items()}
    result["existing_coverage"]=dict(rows=int(common.sum()),fraction=float(common.mean()),bills=int(cm.bill.nunique()))
    result_path.write_text(json.dumps(result,indent=2))
    if "uncertainty" not in result:
        result["uncertainty"]=uncertainty(mm,preds)
        result_path.write_text(json.dumps(result,indent=2))
    if "existing_common_uncertainty" not in result:
        chosen={k:common_preds[k] for k in ("existing_production","logistic_base","logistic_history","boosted_dynamic","time_to_sign","boosted_public_coverage","boosted_public")}
        result["existing_common_uncertainty"]=uncertainty(cm,chosen,baseline="existing_production")
        result_path.write_text(json.dumps(result,indent=2))
    # Explicit paired ablations answer whether public text and timing add value.
    if "public_ablation_uncertainty" not in result:
        result["public_ablation_uncertainty"]=uncertainty(mm,{k:preds[k] for k in ("boosted_dynamic","boosted_public_coverage","boosted_public")},baseline="boosted_dynamic")
        result["public_direction_ablation_uncertainty"]=uncertainty(mm,{k:preds[k] for k in ("boosted_public_coverage","boosted_public")},baseline="boosted_public_coverage")
        result_path.write_text(json.dumps(result,indent=2))
    output_meta=mm.copy()
    for name,p in preds.items():
        output_meta[name]=p
    output_meta.to_parquet(OUT/"scored_final_forecasts.parquet",index=False)
    log("FINAL TEST COMPLETE")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("phase",choices=["develop","final"])
    args=parser.parse_args()
    with threadpool_limits(limits=4):
        develop() if args.phase=="develop" else final_test()
