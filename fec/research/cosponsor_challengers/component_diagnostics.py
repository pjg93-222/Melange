"""Paired, pre-specified component comparisons for member shortlists."""
import json
import numpy as np
from audit_data import OUT
from run_models import load,cluster_codes,topk_vectors

CONTRASTS={
    "history_added_to_logistic":("logistic_base","logistic_history"),
    "timing_added_to_logistic":("logistic_history","logistic_dynamic"),
    "trees_vs_logistic_same_history":("logistic_history","boosted_history"),
    "trees_vs_logistic_same_dynamic_inputs":("logistic_dynamic","boosted_dynamic"),
    "survival_vs_dynamic_logistic":("logistic_dynamic","time_to_sign"),
}


def run():
    _,meta=load(119)
    meta=meta[meta.mature.eq(1)].reset_index(drop=True)
    y=meta.y.to_numpy()
    codes,nfamily=cluster_codes(meta)
    weights=np.random.default_rng(302).multinomial(nfamily,np.full(nfamily,1/nfamily),size=3000)
    slots=None
    hits={}
    for name in sorted({name for pair in CONTRASTS.values() for name in pair}):
        p=np.load(OUT/f"final_predictions/{name}.npy")
        selected=topk_vectors(meta,y,p,8)
        hits[name]=np.bincount(codes[selected],weights=y[selected],minlength=nfamily)
        if slots is None:
            slots=np.bincount(codes[selected],minlength=nfamily)
    denominator=weights@slots
    results={}
    for key,(base,challenger) in CONTRASTS.items():
        delta=weights@(hits[challenger]-hits[base])/denominator
        results[key]=dict(baseline=base,challenger=challenger,delta_precision_at_8=float((hits[challenger]-hits[base]).sum()/slots.sum()),
                          additional_hits=int((hits[challenger]-hits[base]).sum()),ci95=np.quantile(delta,[.025,.975]).tolist(),
                          five_comparison_familywise_interval=np.quantile(delta,[.005,.995]).tolist())
    (OUT/"component_diagnostics.json").write_text(json.dumps(dict(comparisons=results,bootstrap_replicates=3000,families=nfamily,
        note="Five planned input/algorithm contrasts, descriptive secondary diagnostics. Paired resampling of complete legislative families; these intervals do not assess across-Congress generalization."),indent=2))
    print(json.dumps(results,indent=2),flush=True)


if __name__=="__main__":
    run()
