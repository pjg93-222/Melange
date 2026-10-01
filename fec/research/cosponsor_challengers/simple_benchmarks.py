"""Freeze simple historical-rule comparators before inspecting final performance."""
import argparse
import datetime as dt
import json

import numpy as np

from audit_data import OUT,digest
from build_panel import FEATURES
from run_models import load,platt_fit,calibrate,metrics

RULES={"member_propensity":"prior_sign_rate","sponsor_affinity":"affinity_rate","prior_analogue_support":"signed_analogue"}


def freeze():
    if (OUT/"final_results.json").exists():
        raise RuntimeError("Additional comparator freeze must precede final performance inspection")
    xv,mv=load(118)
    xt,mt=load(119)
    val=mv.mature.to_numpy().astype(bool)
    test=mt.mature.to_numpy().astype(bool)
    result={"rule_definition":"Single prior-history feature, no model selection. Probability mapping fitted only on Congress 118.","rules":{}}
    for name,feature in RULES.items():
        pv=np.asarray(xv[:,FEATURES.index(feature)])[val]
        pt=np.asarray(xt[:,FEATURES.index(feature)])[test]
        cal=platt_fit(mv.y.to_numpy()[val],pv)
        path=OUT/f"simple_prediction_{name}.npy"
        np.save(path,calibrate(pt,cal))
        result["rules"][name]=dict(feature=feature,calibration=cal,development=metrics(mv[val].reset_index(drop=True),calibrate(pv,cal)),sha256=digest(path))
    result["frozen_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
    (OUT/"simple_benchmark_freeze.json").write_text(json.dumps(result,indent=2))
    print("SIMPLE COMPARATORS FROZEN",result["frozen_utc"],flush=True)


def evaluate():
    freeze=json.loads((OUT/"simple_benchmark_freeze.json").read_text())
    x,meta=load(119)
    meta=meta[meta.mature.eq(1)].reset_index(drop=True)
    common=np.isfinite(meta.existing_score.to_numpy())
    results={}
    for name in RULES:
        path=OUT/f"simple_prediction_{name}.npy"
        assert digest(path)==freeze["rules"][name]["sha256"]
        p=np.load(path)
        results[name]=dict(full=metrics(meta,p),production_common=metrics(meta[common].reset_index(drop=True),p[common]))
    (OUT/"simple_benchmark_results.json").write_text(json.dumps(results,indent=2))
    print(json.dumps({k:{'AP':v['full']['average_precision'],'P8':v['full']['precision_at_8']} for k,v in results.items()},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("phase",choices=["freeze","evaluate"])
    args=parser.parse_args()
    freeze() if args.phase=="freeze" else evaluate()
