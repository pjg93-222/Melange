"""Optimize within-bill shortlists and evaluate selective recommendations honestly."""
import datetime as dt
import gc
import json
import sys

from common import CODE, OLD, OUT, digest, log, read_json, stamp, write_json
sys.path.insert(0, str(OUT / "vendor"))
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from build_panel import FEATURES, BASE, ENHANCED, DYNAMIC
from run_models import load, topk_vectors, calibrate, metrics

NAMES = BASE + ENHANCED + DYNAMIC
COLS = [FEATURES.index(n) for n in NAMES]
GROUP_NAMES = ["sponsor_d1", "sponsor_d2", "sponsor_ideology_missing", "senate", "sponsor_majority", "finance_referrals"] + [n for n in BASE if n.startswith("topic_")] + [n for n in DYNAMIC if n not in {"coparty_join_share", "prior_collaborator_share"}]
GROUP_COLS = [FEATURES.index(n) for n in GROUP_NAMES]
EARLY_END = dt.date(2024, 1, 1).toordinal()


def shortlist_metrics(m, p):
    y = m.y.to_numpy()
    selected = topk_vectors(m, y, p, 8)
    g = m.groupby("group").y.agg(["sum", "count"])
    return dict(rows=len(m), groups=len(g), positive_groups=int(g["sum"].gt(0).sum()), events=int(y.sum()),
                hits=int(y[selected].sum()), slots=len(selected), precision=float(y[selected].mean()),
                recall=float(y[selected].sum()/max(1,y.sum())), oracle_precision=float(g["sum"].clip(upper=8).sum()/len(selected)))


def group_design(x, m):
    group, first, inverse = np.unique(m.group.to_numpy(), return_index=True, return_inverse=True)
    event_counts = np.bincount(inverse, weights=m.y.to_numpy())
    return np.asarray(x[first][:, GROUP_COLS]), (event_counts > 0).astype(int), inverse


def selection_summary(m, probabilities, mask):
    mm = m.iloc[np.flatnonzero(mask)]
    if len(mm) == 0:
        return dict(recommendations=0, hits=0, precision=None, bills=0, members=0)
    return dict(recommendations=len(mm), hits=int(mm.y.sum()), precision=float(mm.y.mean()),
                bills=int(mm.bill.nunique()), members=int(mm.member.nunique()), mean_probability=float(probabilities[mask].mean()))


def run():
    result_path = OUT / "ranker_development.json"
    if result_path.exists():
        raise RuntimeError("Ranker development already completed; do not overwrite")
    model_dir = OUT / "ranker_models"
    model_dir.mkdir(exist_ok=True)
    x, m = load(117)
    mature = m.mature.to_numpy().astype(bool)
    train_meta = m[mature].reset_index(drop=True)
    group_total = train_meta.groupby("group").y.transform("sum").to_numpy()
    train_rows = np.flatnonzero(mature)[group_total > 0]
    train_rank = m.iloc[train_rows].reset_index(drop=True)
    order = np.lexsort((train_rank.member.to_numpy(), train_rank.group.to_numpy()))
    train_rows = train_rows[order]
    train_rank = train_rank.iloc[order].reset_index(drop=True)
    train_x = np.asarray(x[train_rows][:,COLS])
    sizes = train_rank.groupby("group", sort=True).size().to_numpy()
    y = train_rank.y.to_numpy().astype(int)
    # Activity learns on ALL complete training query groups, including no-join queries.
    activity_x, activity_y, _ = group_design(x[np.flatnonzero(mature)], train_meta)
    activity = HistGradientBoostingClassifier(max_leaf_nodes=7, max_iter=150, min_samples_leaf=20,
                learning_rate=.05, l2_regularization=10, early_stopping=False, random_state=913)
    activity.fit(activity_x, activity_y)
    joblib.dump(dict(model=activity, features=GROUP_NAMES), model_dir/"activity.joblib")
    del x, m, group_total
    gc.collect()
    xv, mv = load(118)
    complete = mv.mature.to_numpy().astype(bool)
    mval = mv[complete].reset_index(drop=True)
    val_x = np.asarray(xv[np.flatnonzero(complete)][:,COLS])
    early = mval.day.to_numpy() < EARLY_END
    late = ~early
    early_meta = mval[early].reset_index(drop=True)
    log(f"Ranker: {len(train_rank):,} rows in {len(sizes):,} positive training queries; {len(mval):,} development rows, {early.sum():,} in 2023")
    candidates = []
    best = None
    # Fit each leaf count once; evaluate fixed tree-count checkpoints.
    for leaves in [7,15,31]:
        model = lgb.LGBMRanker(objective="lambdarank", n_estimators=600, num_leaves=leaves,
                 learning_rate=.05, min_child_samples=50, reg_lambda=10, random_state=913,
                 n_jobs=4, verbosity=-1, deterministic=True, force_col_wise=True,
                 lambdarank_truncation_level=8, lambdarank_norm=True, label_gain=[0,1])
        model.fit(train_x, y, group=sizes)
        for trees in [100,300,600]:
            score = model.predict(val_x, num_iteration=trees).astype(np.float32)
            metric = shortlist_metrics(early_meta,score[early])
            config = dict(leaves=leaves, trees=trees)
            candidates.append(dict(config=config, selection_2023=metric))
            log(f"Ranker {config}: 2023 P@8={metric['precision']:.5f}, hits={metric['hits']}")
            if best is None or metric["hits"] > best["selection_hits"]:
                model.booster_.save_model(str(model_dir/"selected_ranker.txt"),num_iteration=trees)
                best = dict(config=config,selection_hits=metric["hits"])
                np.save(OUT/"ranker_scores_118.npy",score)
        del model
        gc.collect()
    score = np.load(OUT/"ranker_scores_118.npy")
    gx, gy, inverse = group_design(xv[np.flatnonzero(complete)], mval)
    activity_probability = activity.predict_proba(gx)[:,1][inverse]
    # Within-query standardized ranking has a comparable scale across query sizes.
    gs = pd.Series(score).groupby(mval.group)
    standardized = (score-gs.transform("mean").to_numpy())/np.maximum(gs.transform("std").fillna(1).to_numpy(),.1)
    design = np.column_stack([standardized, logit(np.clip(activity_probability,1e-5,1-1e-5))])
    scaler = StandardScaler().fit(design[early])
    cal = LogisticRegression(C=1.0,solver="newton-cholesky",max_iter=150)
    cal.fit(scaler.transform(design[early]),mval.y.to_numpy()[early])
    if cal.coef_[0,0] <= 0:
        raise RuntimeError("Ranker calibration reversed within-bill ordering")
    probabilities = cal.predict_proba(scaler.transform(design))[:,1].astype(np.float32)
    joblib.dump(dict(model=cal,scaler=scaler,features=["within_query_standardized_score","activity_logit"],
                     trained_calendar_year=2023), model_dir/"member_calibration.joblib")
    np.save(OUT/"ranker_combined_probabilities_118.npy",probabilities)
    np.save(OUT/"activity_probability_118.npy",activity_probability.astype(np.float32))
    development = read_json(OLD/"development_results.json")
    control_predictions = {name:calibrate(np.load(OLD/f"development_prediction_{name}.npy"), development['models'][name]['calibration'])
                           for name in ['logistic_dynamic','boosted_dynamic','boosted_public_coverage']}
    control_predictions['lambdamart_activity'] = probabilities
    models = {}
    for name,p in control_predictions.items():
        models[name] = dict(all_118=shortlist_metrics(mval,p),
                           year_2023=shortlist_metrics(early_meta,p[early]),
                           year_2024=shortlist_metrics(mval[late].reset_index(drop=True),p[late]))
    top8 = np.zeros(len(mval),dtype=bool)
    top8[topk_vectors(mval,mval.y.to_numpy(),score,8)] = True
    # Fixed probability thresholds, set before looking at 2024 outcomes.
    thresholds = [.005,.01,.02,.05,.10,.20,.30,.50]
    curves = []
    for threshold in thresholds:
        chosen = top8 & (probabilities >= threshold)
        curves.append(dict(threshold=threshold, year_2023=selection_summary(mval,probabilities,chosen & early),
                            year_2024=selection_summary(mval,probabilities,chosen & late)))
    # Select numerical cutoffs using only 2023 score quantiles; apply unchanged in 2024.
    budget_curves=[]
    for fraction in [1.,.5,.25,.10,.05,.01]:
        threshold=float(np.quantile(probabilities[top8 & early],1-fraction))
        chosen=top8 & (probabilities>=threshold)
        budget_curves.append(dict(retained_fraction_target_2023=fraction,threshold=threshold,
            year_2023=selection_summary(mval,probabilities,chosen & early),year_2024=selection_summary(mval,probabilities,chosen & late)))
    group_list = sorted(mval.loc[late,'group'].unique())
    # Paired bootstrap of whole bills (all their forecast dates), never individual rows.
    bill_codes, unique_bills=pd.factorize(mval.bill)
    n=len(unique_bills)
    w=np.random.default_rng(917).multinomial(n,np.full(n,1/n),size=2000)
    paired={}
    rank_selected=topk_vectors(mval,mval.y.to_numpy(),score,8)
    rank_selected=rank_selected[late[rank_selected]]
    rh=np.bincount(bill_codes[rank_selected],weights=mval.y.to_numpy()[rank_selected],minlength=n)
    rs=np.bincount(bill_codes[rank_selected],minlength=n)
    for name,p in control_predictions.items():
        if name=='lambdamart_activity': continue
        chosen=topk_vectors(mval,mval.y.to_numpy(),p,8);chosen=chosen[late[chosen]]
        h=np.bincount(bill_codes[chosen],weights=mval.y.to_numpy()[chosen],minlength=n)
        delta=w@(rh-h)/np.maximum(w@rs,1)
        paired[name]=dict(delta_precision=float((rh-h).sum()/rs.sum()),ci95=np.quantile(delta,[.025,.975]).tolist(),
                         note="Descriptive paired bill bootstrap on 2024 development rows; configurations selected on 2023")
    result=dict(completed_utc=stamp(),status="development_only",selected=best,candidates=candidates,
        train_rows=len(train_rank),train_positive_queries=len(sizes),features=NAMES,models=models,
        selective_thresholds=curves,selective_budgets=budget_curves,paired_2024=paired,
        calibration_2023=dict(coefficients=cal.coef_.tolist(),intercept=cal.intercept_.tolist()),
        protocol_sha256=digest(CODE/"PROTOCOL.md"),script_sha256=digest(__file__),
        original_panel_sha256=digest(OLD/"panel_receipt.json"),
        model_hashes={p.name:digest(p) for p in model_dir.iterdir() if p.is_file()},
        scores_sha256=digest(OUT/"ranker_scores_118.npy"))
    write_json(result_path,result)
    log(f"Ranker development complete; selected {best}; 2024 {models['lambdamart_activity']['year_2024']}")


if __name__ == "__main__":
    with threadpool_limits(limits=4):
        run()
