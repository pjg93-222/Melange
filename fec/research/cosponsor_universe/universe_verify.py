"""Post-freeze V3 verification; writes only verification_receipt.json.

Do not run until selection, results and statistics have all frozen. This is
read-only for sources, models, predictions, earlier experiments and snapshots.
One fitted artifact at a time; no fitting or Congress119 outcome inspection.
"""
from __future__ import annotations

import collections
import datetime as dt
import gc
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

import universe_models as models
from universe_gold_cohort import load_gold_ids

ROOT = Path(__file__).resolve().parents[3]
CODE = Path(__file__).resolve().parent
OUT = ROOT / "outputs/cosponsor_universe_20260905"
OLD = ROOT / "outputs/cosponsor_challengers_20260905"
PREVIOUS = ROOT / "outputs/cosponsor_refinement_20260905"
RECEIPT = OUT / "verification_receipt.json"
CHECKS = {}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check(name, condition, detail=None):
    CHECKS[name] = bool(condition)
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def close(actual, expected, name, atol=1e-9):
    if actual is None or expected is None:
        check(name, actual is None and expected is None, (actual, expected))
    else:
        check(name, np.isclose(actual, expected, rtol=1e-8, atol=atol), (actual, expected))


def summary(frame, total_events):
    count = len(frame)
    hits = int(frame.y.sum())
    return dict(recommendations=count, hits=hits,
                precision=hits / count if count else None,
                recall=hits / max(1, total_events),
                bills=int(frame.bill.nunique()), members=int(frame.member.nunique()))


def compare_summary(actual, expected, name):
    for key, value in actual.items():
        close(value, expected[key], name + ":" + key)


def pandas_top(frame, probabilities, k=8):
    # Independently reproduce the ranking without run_models.topk_vectors.
    ranked = frame.copy()
    ranked["probability"] = np.asarray(probabilities)
    ranked = ranked.sort_values(["group", "probability", "member"],
                                ascending=[True, False, True], kind="mergesort")
    return ranked.groupby("group", sort=False).head(k)


def manual_metrics(frame, probabilities, reported, name):
    y = frame.y.to_numpy(dtype=np.float64)
    p = np.clip(np.asarray(probabilities, dtype=np.float64), 1e-8, 1 - 1e-8)
    actual = dict(rows=len(y), events=int(y.sum()), base_rate=float(y.mean()),
                  brier=float(np.mean((p - y) ** 2)),
                  log_loss=float(-np.mean(y * np.log(p) + (1 - y) * np.log1p(-p))),
                  bills=int(frame.bill.nunique()), bill_dates=int(frame.group.nunique()))
    for key, value in actual.items():
        close(value, reported[key], name + ":" + key)
    top8 = pandas_top(frame, probabilities, 8)
    for k, top in [(8, top8), (25, pandas_top(frame, probabilities, 25))]:
        hits = int(top.y.sum())
        for key, value in {f"hits_at_{k}": hits, f"slots_at_{k}": len(top),
                           f"precision_at_{k}": hits / len(top),
                           f"recall_at_{k}": hits / max(1, int(y.sum()))}.items():
            close(value, reported[key], name + ":" + key)
    actual.update(hits_at_8=int(top8.y.sum()), slots_at_8=len(top8),
                  precision_at_8=float(top8.y.mean()))
    return actual, top8


def verify_bindings(plan, selection, results, statistics, statistics_plan):
    check("selection_frozen", bool(selection.get("frozen_utc")))
    check("selection_plan_binding", selection["plan_sha256"] == sha(OUT / "universe_plan.json"))
    check("results_selection_binding", results["selection_sha256"] == sha(OUT / "universe_selection.json"))
    check("statistics_selection_binding", statistics_plan["selection_sha256"] == sha(OUT / "universe_selection.json"))
    check("model_code_binding", plan["code_sha256"] == sha(models.__file__))
    check("protocol_binding", plan["protocol_sha256"] == sha(CODE / "PROTOCOL.md"))
    check("statistics_code_binding", statistics_plan["code_sha256"] == sha(CODE / "universe_statistics.py"))
    check("freeze_chronology", selection["frozen_utc"] <= results["completed_utc"] <= statistics["completed_utc"])
    for key, base in [("supporting_code_sha256", CODE), ("input_sha256", OUT),
                      ("original_panel_sha256", OLD)]:
        for file, expected in plan[key].items():
            check(key + ":" + file, sha(base / file) == expected)
    for key in ("dependency_code_sha256", "previous_manifests"):
        for path, expected in plan[key].items():
            check(key + ":" + path, sha(path) == expected)
    # Recheck the independently reviewed direct-input/source receipts, including
    # prior network/text/demographic/LDA arrays not duplicated in the V3 input list.
    reviewed = read(OUT / "gold_model_review.json")
    for item in reviewed["source_receipt_verification"]["observed"]:
        check("source_receipt:" + item["path"], sha(item["path"]) == item["expected_sha256"])
    check("24_models_in_menu", len(plan["models"]) == 24)
    check("live_menu_equals_plan", models.menu() == plan["models"])
    check("all_24_models_frozen", set(selection["models"]) == set(results["models"]) == set(plan["models"]))
    check("statistics_79_unique_contrasts", statistics_plan["comparisons"] == len(statistics_plan["pairs"]) == 79
          and len({tuple(p) for p in statistics_plan["pairs"]}) == 79)
    chosen = max((name for name, spec in plan["models"].items() if spec["historical_selection_eligible"]),
                 key=lambda name: selection["models"][name]["selection_2023"]["precision_at_8"])
    check("winner_uses_2023_only", chosen == selection["chosen"] == results["chosen_on_2023"] == statistics["chosen_on_2023"])
    check("placebo_not_winner", chosen != "boosted_language_placebo")
    return chosen


def prospective_bindings():
    """Hash existing future-issued files without reading their outcomes/scores."""
    folder = PREVIOUS / "prospective_20260905"
    base = read(folder / "forecast_manifest.json")
    network = read(folder / "network_forecast_manifest.json")
    bound = {"source_receipt.json": base["source_receipt_sha256"],
             "features.npy": base["features_sha256"],
             "forecasts.parquet": base["forecasts_sha256"],
             "network_features.npy": network["features_sha256"],
             "network_forecasts.parquet": network["forecasts_sha256"],
             "boosted_network_refit.joblib": network["model_sha256"],
             "forecast_manifest.json": network["original_forecast_manifest_sha256"]}
    for filename, expected in bound.items():
        check("prospective_snapshot:" + filename, sha(folder / filename) == expected)
    return bound


def run():
    if RECEIPT.exists():
        raise RuntimeError("Verification receipt already frozen; never silently overwrite")
    required = ["universe_plan.json", "universe_selection.json", "universe_results.json",
                "universe_statistics_plan.json", "universe_statistics.json"]
    if not all((OUT / name).exists() for name in required):
        raise RuntimeError("Wait for model selection, results and statistics to freeze before running")
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    protected = [OUT / name for name in required]
    protected += list((PREVIOUS / "prospective_20260905").iterdir())
    protected = [p for p in protected if p.is_file()]
    before = {str(p): sha(p) for p in protected}
    plan, selection, result, stat_plan, stat = [read(OUT / n) for n in required]
    chosen = verify_bindings(plan, selection, result, stat, stat_plan)
    prospective = prospective_bindings()
    gold = set(load_gold_ids())
    check("gold377", len(gold) == 377)
    ids = read(OLD / "identifiers.json")["members"]
    # Reproduce the mature binary sampling contract; this also checks hazard uses
    # the same rows and weights rather than the older all-censoring sample.
    tm = pd.read_parquet(OLD / "meta_117.parquet", columns=["member", "mature", "y", "duration"])
    tg = np.array([mid in gold for mid in ids])[tm.member.to_numpy()]
    eligible = tm.mature.to_numpy().astype(bool) & tg
    ty = tm.y.to_numpy()
    sampled = eligible & ((ty > 0) | (np.random.default_rng(models.SEED + 117).random(len(tm)) < .1))
    ti = np.flatnonzero(sampled)
    check("sample_has_only_mature_gold", bool(np.all(eligible[ti])))
    check("sample_preserves_positives", bool(np.all(sampled[eligible & (ty > 0)])))
    check("sample_matches_frozen_selection", len(ti) == selection["training_rows"]
          and int(ty[ti].sum()) == selection["training_events"])
    train_receipt = dict(rows=len(ti), events=int(ty[ti].sum()),
                         indices_sha256=hashlib.sha256(ti.astype("<i8").tobytes()).hexdigest())
    check("sample_index_binding", train_receipt["indices_sha256"] ==
          read(OUT / "gold_model_review.json")["behavioral_test_run"]["panels"]["117"]["sample_indices_sha256"])
    del tm, tg, eligible, ty, sampled, ti
    panel = models.Panel(118)
    direct_gold = np.array([mid in gold for mid in ids])[panel.meta.member.to_numpy()]
    check("prediction_cohort_mask", np.array_equal(panel.gold, direct_gold))
    original_indices = np.flatnonzero(panel.meta.mature.to_numpy().astype(bool) & direct_gold)
    m = panel.meta.iloc[original_indices][["bill", "member", "group", "day", "y", "senate", "democrat"]].reset_index(drop=True)
    check("all_prediction_members_gold", {ids[int(code)] for code in m.member.unique()} == gold)
    early = m.day.to_numpy() < models.EARLY_END
    me, ml = m[early].reset_index(drop=True), m[~early].reset_index(drop=True)
    check("validation_rows_match_review", (len(m), len(me), len(ml)) == (2907161, 1858229, 1048932))
    positions = np.sort(np.random.default_rng(905633).choice(len(m), size=min(2000, len(m)), replace=False))
    source_indices = original_indices[positions]
    check("reprediction_original_indices_gold", bool(np.all(panel.gold[source_indices])))
    per_model = {}
    for name, spec in plan["models"].items():
        pp, mp = OUT / f"predictions/{name}.npy", OUT / f"models/{name}.joblib"
        frozen = selection["models"][name]
        check(name + ":prediction_hash", sha(pp) == frozen["prediction_sha256"])
        check(name + ":model_hash", sha(mp) == frozen["model_sha256"])
        p = np.load(pp, mmap_mode="r")
        check(name + ":prediction_length", p.ndim == 1 and len(p) == len(m))
        check(name + ":probability_range", bool(np.isfinite(p).all() and np.all((p >= 0) & (p <= 1))))
        artifact = joblib.load(mp)
        for key in ("kind", "features", "placebo"):
            check(name + ":artifact_" + key, artifact[key] == spec[key])
        reproduced = models.calibrate(models.predict(artifact, panel, source_indices), artifact["calibration_2023"])
        error = float(np.max(np.abs(reproduced.astype(float) - p[positions].astype(float))))
        check(name + ":sample_reprediction", error <= 2e-6, error)
        a23, top23 = manual_metrics(me, p[early], result["models"][name]["year_2023"], name + ":2023")
        a24, top24 = manual_metrics(ml, p[~early], result["models"][name]["year_2024"], name + ":2024")
        close(a23["precision_at_8"], frozen["selection_2023"]["precision_at_8"], name + ":selection_precision")
        ranked24 = top24.sort_values(["probability", "group", "member"],
                                    ascending=[False, True, True], kind="mergesort")
        total_events = int(ml.y.sum())
        for count in (250, 500, 1000, 2000, 5000):
            expected = stat["matched_retained_counts"][str(count)][name]
            compare_summary(summary(ranked24.head(count), total_events), expected, name + f":matched_{count}")
        for row in stat["selective"][name]:
            fraction = row["target_fraction_2023"]
            cutoff = float(np.quantile(top23.probability.to_numpy(), 1 - fraction))
            close(cutoff, row["cutoff_2023"], name + f":cutoff_{fraction}", atol=1e-7)
            # The recorded cutoff is authoritative after numeric-equivalence check.
            picked = top24[top24.probability >= row["cutoff_2023"]]
            compare_summary(summary(picked, total_events), row, name + f":selective_{fraction}")
        masks = {"House": ml.senate.eq(0), "Senate": ml.senate.eq(1),
                 "Democratic": ml.democrat.eq(1), "non_Democratic": ml.democrat.eq(0)}
        for label, mask in masks.items():
            picked = top24.loc[top24.index.intersection(ml.index[mask])]
            expected = stat["strata"][name][label]
            compare_summary(summary(picked, int(ml.loc[mask, "y"].sum())), expected, name + ":stratum_" + label)
            close(int(mask.sum()), expected["candidate_rows"], name + ":stratum_rows_" + label)
        per_model[name] = dict(reprediction_rows=len(positions), reprediction_max_absolute_error=error,
                               year_2023=a23, year_2024=a24,
                               prediction_sha256=frozen["prediction_sha256"], model_sha256=frozen["model_sha256"])
        print(f"Verified {name}: {len(positions)} re-predictions; independent full-period counts match", flush=True)
        del artifact, reproduced, p, top23, top24, ranked24
        gc.collect()
    for challenger, base in stat_plan["pairs"]:
        left, right = per_model[challenger]["year_2024"], per_model[base]["year_2024"]
        expected = stat["paired"][challenger + " vs " + base]
        check("paired_budget:" + challenger + ":" + base, left["slots_at_8"] == right["slots_at_8"])
        close(left["hits_at_8"] - right["hits_at_8"], expected["extra_hits"], "paired_hits:" + challenger + ":" + base)
        close((left["hits_at_8"] - right["hits_at_8"]) / right["slots_at_8"], expected["delta_precision"], "paired_precision:" + challenger + ":" + base)
        close(left["brier"] - right["brier"], expected["delta_brier"], "paired_brier:" + challenger + ":" + base)
    close(len(ml), stat["rows_2024"], "statistics_row_count")
    close(int(ml.y.sum()), stat["events_2024"], "statistics_event_count")
    oracle_hits = int(ml.groupby("group").y.sum().clip(upper=8).sum())
    close(oracle_hits, stat["forced_top8_oracle"]["hits"], "forced_top8_oracle_hits")
    after = {str(p): sha(p) for p in protected}
    check("prior_snapshots_and_frozen_results_unchanged", before == after)
    output = dict(schema="cosponsor-gold-postfit-verification-v1", status="PASS",
                  started_utc=started, completed_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  verifier_code_sha256=sha(__file__), chosen_on_2023=chosen,
                  cohort_members=len(gold), training_sample=train_receipt,
                  validation_rows=len(m), selection_rows_2023=len(me), assessment_rows_2024=len(ml),
                  reprediction_original_indices_sha256=hashlib.sha256(source_indices.astype("<i8").tobytes()).hexdigest(),
                  checks=CHECKS, check_count=len(CHECKS), models=per_model,
                  protected_before=before, protected_after=after, prospective_manifest_bindings=prospective,
                  limitations=["No historical model refitted. Only existing frozen models re-predicted.",
                               "Independent pandas ordering and arithmetic verify counts, Brier/log loss and paired point differences; bootstrap intervals are not independently rerun.",
                               "Membership conditions on later survival. Both outcome periods remain development, not independent confirmation.",
                               "Congress119 prospective files are checked by hashes only; their outcomes are not loaded."])
    RECEIPT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status="PASS", checks=len(CHECKS), models=len(per_model), receipt=str(RECEIPT))), flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        run()
