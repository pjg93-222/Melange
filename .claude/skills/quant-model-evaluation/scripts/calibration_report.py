#!/usr/bin/env python3
"""Probability calibration and baselines for a binary classifier. Read-only: reads one CSV of observed
outcomes and predicted probabilities; writes only its run folder.

Answers two questions a probability claim needs: can the scores be read as probabilities, and do they
beat the base rate? Reports the Brier score with its Murphy decomposition, expected and maximum
calibration error (ECE/MCE) from a reliability table, the calibration intercept (slope fixed at 1) and
slope from a logistic recalibration on logit(p), AUC and average precision against the base-rate
baseline, per-group metrics, and, for models trained with class weights or resampling, the closed-form
prior-shift correction with before/after metrics.

Usage:
  python scripts/calibration_report.py --data preds.csv --y outcome --p prob
      [--group COL] [--bins 10] [--strategy quantile|uniform]
      [--prior-train P --prior-target P] [--max-ece 0.05] [--slope-lo 0.8] [--slope-hi 1.2]
      [--max-intercept 0.2] [--alpha 0.05] [--resamples 500] [--min-group-n 50] [--clip 1e-6]

Verdict rules (the flags fix every threshold before the run):
  CAL-01 Brier vs base rate: model Brier >= base-rate Brier -> KILLED; lower, but the paired (1-alpha)
         CI of the difference reaches 0 -> WOUNDED; CI entirely below 0 -> SURVIVES.
  CAL-02 calibration-in-the-large (intercept, slope fixed at 1): |a| <= --max-intercept and CI
         half-width <= --max-intercept -> SURVIVES; outside and CI excludes 0 -> WOUNDED; otherwise
         UNVERIFIED-HERE (too few events to tell).
  CAL-03 calibration slope: same rule with the band [--slope-lo, --slope-hi] around 1. A slope below 1
         means the probabilities are too extreme (typical of overfitting); above 1, too timid.
  CAL-04 ECE <= --max-ece -> SURVIVES; above it and above the perfect-calibration noise floor
         (consistency resampling, p < alpha) -> WOUNDED; above it but within noise -> UNVERIFIED-HERE.
  CAL-05 discrimination: AUC <= 0.5 -> KILLED; lower CI bound <= 0.5 -> WOUNDED; else SURVIVES.
  CAL-06 per-group calibration-in-the-large (--group; groups with n >= --min-group-n and both
         outcomes): any group off -> WOUNDED; any imprecise -> UNVERIFIED-HERE; else SURVIVES.
  CAL-07 prior shift (--prior-train/--prior-target): raw probabilities calibrated in the large ->
         SURVIVES; off -> WOUNDED (the detail says whether the corrected p' repairs it).
  Class-weighted training: sklearn class_weight='balanced' fits as if the prior were 0.5, so pass
  --prior-train 0.5 --prior-target <population rate>; p' = p*r1 / (p*r1 + (1-p)*r0) with
  r1 = pi_t/pi_s and r0 = (1-pi_t)/(1-pi_s).

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
"""
from __future__ import annotations

import math
import pathlib
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (Check, Report, UsageError, base_parser, run_main, require_file, write_once, emit,
                     optional_import, SURVIVES, WOUNDED, KILLED, UNVERIFIED)

import numpy as np
import pandas as pd
from scipy import stats

SCRIPT = "calibration_report"
SOURCE = f"quant-model-evaluation/{SCRIPT}"
_TRUE = {"1", "1.0", "true", "t", "yes", "y"}
_FALSE = {"0", "0.0", "false", "f", "no", "n"}


def build_parser():
    p = base_parser(__doc__)
    p.add_argument("--data", required=True, help="CSV (or .tsv) with one row per scored case")
    p.add_argument("--y", required=True, help="observed binary outcome column (0/1, true/false, yes/no)")
    p.add_argument("--p", required=True, help="predicted probability column, values in [0, 1]")
    p.add_argument("--group", help="optional column for per-group (stratum) metrics")
    p.add_argument("--bins", type=int, default=10, help="reliability-table bins (default 10)")
    p.add_argument("--strategy", choices=("quantile", "uniform"), default="quantile",
                   help="bin edges at quantiles of p (equal counts, default) or equal-width on [0, 1]")
    p.add_argument("--prior-train", type=float,
                   help="positive-class prior the model was fitted under (0.5 for class_weight='balanced')")
    p.add_argument("--prior-target", type=float,
                   help="positive-class prior of the population the probabilities are used for")
    p.add_argument("--max-ece", type=float, default=0.05, help="ECE tolerance (default 0.05)")
    p.add_argument("--slope-lo", type=float, default=0.8, help="lower edge of the slope band (default 0.8)")
    p.add_argument("--slope-hi", type=float, default=1.2, help="upper edge of the slope band (default 1.2)")
    p.add_argument("--max-intercept", type=float, default=0.2,
                   help="tolerance for calibration-in-the-large, logit units (default 0.2)")
    p.add_argument("--alpha", type=float, default=0.05, help="1 - confidence level for all CIs (default 0.05)")
    p.add_argument("--resamples", type=int, default=500,
                   help="consistency resamples for the ECE noise floor; 0 skips it (default 500)")
    p.add_argument("--min-group-n", type=int, default=50, help="smallest group that gets a verdict (default 50)")
    p.add_argument("--clip", type=float, default=1e-6,
                   help="p is clipped to [clip, 1-clip] before logit and log loss (default 1e-6)")
    return p


# ---- input ----
def read_table(path: pathlib.Path) -> pd.DataFrame:
    sep = "\t" if path.suffix.lower() in (".tsv", ".tab") else ","
    try:
        df = pd.read_csv(path, sep=sep, low_memory=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise UsageError(f"cannot read {path.name} as a table: {exc}") from None
    if df.empty:
        raise UsageError(f"{path.name} has no data rows")
    return df


def to_binary(s: pd.Series, flag: str) -> np.ndarray:
    """Outcome as float 0/1 with NaN for missing; any other value is a usage error."""
    if pd.api.types.is_bool_dtype(s):
        return s.astype(float).to_numpy()
    if pd.api.types.is_numeric_dtype(s):
        v = s.astype(float).to_numpy()
    else:
        txt = s.astype("string").str.strip().str.lower()
        is_t = np.asarray(txt.isin(_TRUE), dtype=bool)
        is_f = np.asarray(txt.isin(_FALSE), dtype=bool)
        present = np.asarray(txt.notna(), dtype=bool)
        bad = present & ~is_t & ~is_f
        if bad.any():
            raise UsageError(f"{flag} must be a binary outcome; found values like "
                             f"{sorted(set(txt[bad].astype(str)))[:5]}")
        v = np.where(is_t, 1.0, np.where(is_f, 0.0, np.nan))
    ok = ~np.isnan(v)
    odd = set(np.unique(v[ok])) - {0.0, 1.0}
    if odd:
        raise UsageError(f"{flag} must be 0/1; found values like {sorted(odd)[:5]}")
    return v


# ---- metrics ----
def logit(p: np.ndarray, eps: float) -> np.ndarray:
    q = np.clip(p, eps, 1.0 - eps)
    return np.log(q) - np.log1p(-q)


def assign_bins(p: np.ndarray, bins: int, strategy: str) -> tuple[np.ndarray, np.ndarray]:
    """Bin index per row (lower-inclusive bins) and the edges actually used."""
    if strategy == "uniform":
        edges = np.linspace(0.0, 1.0, bins + 1)
        idx = np.clip(np.floor(p * bins).astype(int), 0, bins - 1)
        return idx, edges
    edges = np.unique(np.quantile(p, np.linspace(0.0, 1.0, bins + 1)))
    if len(edges) < 2:  # constant predictions: one bin
        return np.zeros(len(p), dtype=int), np.array([p.min(), p.max()])
    idx = np.clip(np.searchsorted(edges[1:-1], p, side="right"), 0, len(edges) - 2)
    return idx, edges


def bin_sums(y, p, idx, nb):
    return (np.bincount(idx, minlength=nb).astype(float), np.bincount(idx, weights=p, minlength=nb),
            np.bincount(idx, weights=y, minlength=nb))


def ece_mce(y, p, idx, nb) -> tuple[float, float]:
    # ECE = sum_k (n_k/N)|obs_k - mean_p_k| = sum_k |sum_y_k - sum_p_k| / N  (Guo et al. 2017, ICML)
    n_k, sp, sy = bin_sums(y, p, idx, nb)
    nz = n_k > 0
    gaps = np.abs(sy[nz] - sp[nz]) / n_k[nz]
    return float(np.abs(sy[nz] - sp[nz]).sum() / len(y)), float(gaps.max())


def murphy(y, p, idx, nb) -> dict:
    """Brier = reliability - resolution + uncertainty (Murphy 1973, J. Applied Meteorology 12:595).
    With continuous p the identity holds only up to within-bin terms (Stephenson, Coelho & Jolliffe
    2008, Weather and Forecasting 23:752); they are reported as `within_bin` so nothing is hidden."""
    n = len(y)
    n_k, sp, sy = bin_sums(y, p, idx, nb)
    nz = n_k > 0
    pbar, obar = sp[nz] / n_k[nz], sy[nz] / n_k[nz]
    base = y.mean()
    brier = float(np.mean((p - y) ** 2))
    rel = float(np.sum(n_k[nz] * (pbar - obar) ** 2) / n)
    res = float(np.sum(n_k[nz] * (obar - base) ** 2) / n)
    unc = float(base * (1 - base))
    return {"brier": brier, "reliability": rel, "resolution": res, "uncertainty": unc,
            "within_bin": brier - (rel - res + unc)}


def ece_noise(p, idx, nb, reps, rng) -> np.ndarray:
    """ECE of outcomes drawn from the model's own p: its distribution under perfect calibration
    (consistency resampling; Brocker & Smith 2007, Weather and Forecasting 22:651)."""
    n_k = np.bincount(idx, minlength=nb)
    sp = np.bincount(idx, weights=p, minlength=nb)
    out = np.empty(reps)
    for r in range(reps):
        sy = np.bincount(idx, weights=(rng.random(len(p)) < p).astype(float), minlength=nb)
        out[r] = np.abs(sy[n_k > 0] - sp[n_k > 0]).sum() / len(p)
    return out


def wilson(k: float, n: float, z: float) -> tuple[float, float]:
    if n <= 0:
        return math.nan, math.nan
    ph = k / n
    den = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / den
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def auc_delong(y, s) -> tuple[float, float]:
    """AUC (Mann-Whitney with midranks) and its DeLong standard error via placement values
    (DeLong, DeLong & Clarke-Pearson 1988, Biometrics 44:837; midrank algorithm of Sun & Xu 2014)."""
    pos, neg = s[y == 1], s[y == 0]
    m, n = len(pos), len(neg)
    if m == 0 or n == 0:
        return math.nan, math.nan
    tz = stats.rankdata(np.concatenate([pos, neg]))
    v10 = (tz[:m] - stats.rankdata(pos)) / n
    v01 = 1.0 - (tz[m:] - stats.rankdata(neg)) / m
    auc = float(v10.mean())
    var = (v10.var(ddof=1) / m if m > 1 else 0.0) + (v01.var(ddof=1) / n if n > 1 else 0.0)
    return auc, float(math.sqrt(max(var, 0.0)))


def auc_ci(auc, se, z) -> tuple[float, float]:
    """Wald interval on the logit scale, which respects the [0, 1] bounds."""
    if not math.isfinite(se) or se == 0 or auc <= 0 or auc >= 1:
        return auc, auc
    lg, d = math.log(auc / (1 - auc)), z * se / (auc * (1 - auc))
    return 1 / (1 + math.exp(-(lg - d))), 1 / (1 + math.exp(-(lg + d)))


def average_precision(y, s) -> float:
    """Step-wise AP = sum_k (R_k - R_{k-1}) P_k over distinct thresholds (no interpolation; the same
    definition as scikit-learn's average_precision_score). Its no-skill value is the prevalence."""
    order = np.argsort(-s, kind="mergesort")
    ss, yy = s[order], y[order]
    last = np.r_[np.nonzero(np.diff(ss))[0], len(ss) - 1]
    tps = np.cumsum(yy)[last]
    if tps[-1] == 0:
        return math.nan
    precision = tps / (last + 1)
    recall = tps / tps[-1]
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def prior_shift(p, pi_s: float, pi_t: float) -> np.ndarray:
    """Bayes re-weighting of posteriors from training prior pi_s to target prior pi_t
    (Saerens, Latinne & Decaestecker 2002, Neural Computation 14:21): odds scale by
    [pi_t/(1-pi_t)] / [pi_s/(1-pi_s)], i.e. logit shifts by a constant."""
    r1, r0 = pi_t / pi_s, (1 - pi_t) / (1 - pi_s)
    return p * r1 / (p * r1 + (1 - p) * r0)


def glm_calibration(y, lp, alpha: float, slope: bool = True) -> dict:
    """Calibration-in-the-large a (logit P(y=1) = a + offset logit(p)) and the recalibration slope b
    (logit P(y=1) = a' + b logit(p)); Cox 1958, Biometrika 45:562; Van Calster et al. 2019, BMC
    Medicine 17:230. Wald CIs from statsmodels GLM (binomial, logit link)."""
    sm = optional_import("statsmodels.api")
    if sm is None:
        return {"error": "statsmodels is not installed"}
    n, out = len(y), {}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            m0 = sm.GLM(y, np.ones((n, 1)), family=sm.families.Binomial(), offset=lp).fit()
            ci = np.asarray(m0.conf_int(alpha))[0]
            out.update(intercept=float(np.asarray(m0.params)[0]), intercept_ci=(float(ci[0]), float(ci[1])))
        except Exception as exc:  # separation or numerical failure: reported, never a pass
            out["intercept_error"] = f"{type(exc).__name__}: {exc}"
        if slope:
            if float(np.std(lp)) < 1e-12:
                out["slope_error"] = "predictions are constant, so the slope is undefined"
            else:
                try:
                    m1 = sm.GLM(y, np.column_stack([np.ones(n), lp]), family=sm.families.Binomial()).fit()
                    ci = np.asarray(m1.conf_int(alpha))[1]
                    out.update(slope=float(np.asarray(m1.params)[1]), slope_ci=(float(ci[0]), float(ci[1])))
                except Exception as exc:
                    out["slope_error"] = f"{type(exc).__name__}: {exc}"
    trouble = [str(w.message) for w in caught
               if any(k in str(w.message).lower() for k in ("separation", "converge", "overflow"))]
    if trouble:
        out["warnings"] = trouble[:3]
    for key in ("intercept", "slope"):
        vals = [out.get(key)] + list(out.get(f"{key}_ci", ()))
        if out.get(key) is not None and not all(math.isfinite(v) for v in vals):
            out[f"{key}_error"] = "non-finite estimate"
    return out


def band_status(est, ci, ideal: float, lo: float, hi: float) -> str:
    """'ok': estimate inside [lo, hi] and the CI no wider than the band; 'off': outside the band with
    the CI excluding the ideal value; 'imprecise': anything else (the data cannot tell)."""
    half, band_half = (ci[1] - ci[0]) / 2, (hi - lo) / 2
    inside = lo <= est <= hi
    if inside and half <= band_half:
        return "ok"
    if not inside and not (ci[0] <= ideal <= ci[1]):
        return "off"
    return "imprecise"


STATUS_VERDICT = {"ok": SURVIVES, "off": WOUNDED, "imprecise": UNVERIFIED}


def f3(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:.3f}"


def core_metrics(y, p, idx, nb, eps) -> dict:
    lp = logit(p, eps)
    q = np.clip(p, eps, 1 - eps)
    base = float(y.mean())
    ece, mce = ece_mce(y, p, idx, nb)
    return {"n": int(len(y)), "events": int(y.sum()), "prevalence": base, "mean_p": float(p.mean()),
            "oe_ratio": float(y.sum() / p.sum()) if p.sum() > 0 else math.nan,
            "brier": float(np.mean((p - y) ** 2)), "brier_base_rate": base * (1 - base),
            "log_loss": float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q))),
            "ece": ece, "mce": mce, "lp": lp}


# ---- main ----
def validate(args) -> None:
    if args.bins < 2:
        raise UsageError("--bins must be at least 2")
    if not 0 < args.alpha < 1:
        raise UsageError("--alpha must be in (0, 1)")
    if not args.slope_lo <= 1.0 <= args.slope_hi or args.slope_lo >= args.slope_hi:
        raise UsageError("--slope-lo must be below --slope-hi and the band must contain 1")
    if args.max_ece <= 0 or args.max_intercept <= 0:
        raise UsageError("--max-ece and --max-intercept must be positive")
    if args.resamples < 0 or args.min_group_n < 1:
        raise UsageError("--resamples must be >= 0 and --min-group-n >= 1")
    if not 0 < args.clip < 0.5:
        raise UsageError("--clip must be in (0, 0.5)")
    if (args.prior_train is None) != (args.prior_target is None):
        raise UsageError("give --prior-train and --prior-target together")
    for flag, v in (("--prior-train", args.prior_train), ("--prior-target", args.prior_target)):
        if v is not None and not 0 < v < 1:
            raise UsageError(f"{flag} must be strictly between 0 and 1")


def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    validate(args)
    src = require_file(args.data, "--data")
    report.add_input(src)
    report.note_packages(["numpy", "pandas", "scipy", "statsmodels"])
    df = read_table(src)
    missing = [c for c in (args.y, args.p, args.group) if c and c not in df.columns]
    if missing:
        raise UsageError(f"--data has no column(s) {missing}; columns are {list(map(str, df.columns))[:30]}")
    y_all = to_binary(df[args.y], "--y")
    p_all = pd.to_numeric(df[args.p], errors="coerce").to_numpy(dtype=float)
    unparsed = int((np.isnan(p_all) & df[args.p].notna().to_numpy()).sum())
    if unparsed:
        raise UsageError(f"--p has {unparsed} non-numeric value(s)")
    if np.isinf(p_all).any():  # an infinity is an input error, not a missing value
        raise UsageError(f"--p has {int(np.isinf(p_all).sum())} infinite value(s); probabilities lie in [0, 1]")
    keep = ~np.isnan(y_all) & ~np.isnan(p_all)
    y, p = y_all[keep], p_all[keep]
    if len(y) and (p.min() < 0 or p.max() > 1):
        raise UsageError(f"--p must hold probabilities in [0, 1]; range is [{p.min():.4g}, {p.max():.4g}]")
    n, events = len(y), int(y.sum())
    if n < 10:
        raise UsageError(f"only {n} complete rows; calibration needs at least 10")
    if events in (0, n):
        raise UsageError("--y holds a single outcome; calibration and AUC need both 0 and 1")
    dropped = int(len(y_all) - n)
    rng = np.random.default_rng(args.seed)
    z = float(stats.norm.ppf(1 - args.alpha / 2))
    conf = f"{100 * (1 - args.alpha):g}%"

    idx, edges = assign_bins(p, args.bins, args.strategy)
    nb = len(edges) - 1
    m = core_metrics(y, p, idx, nb, args.clip)
    mur = murphy(y, p, idx, nb)
    base = m["prevalence"]

    # CAL-01 Brier against the in-sample base rate (the best constant forecast for this sample, so the
    # comparison is conservative). Paired differences d_i = (p_i-y_i)^2 - (base-y_i)^2; normal CI.
    d = (p - y) ** 2 - (base - y) ** 2
    dm, dse = float(d.mean()), float(d.std(ddof=1) / math.sqrt(n))
    dlo, dhi = dm - z * dse, dm + z * dse
    bss = 1 - m["brier"] / m["brier_base_rate"]
    if dm >= 0:
        v1 = KILLED
    elif dhi >= 0:
        v1 = WOUNDED
    else:
        v1 = SURVIVES
    report.add(Check("CAL-01", "Brier score beats the base-rate forecast", v1,
                     criterion=f"model Brier < base-rate Brier with the paired {conf} CI of the difference below 0",
                     value=round(bss, 6),
                     detail=f"Brier {f3(m['brier'])} vs base rate {f3(m['brier_base_rate'])} (prevalence "
                            f"{f3(base)}); skill score {f3(bss)}; difference {dm:+.4f} [{dlo:+.4f}, {dhi:+.4f}]"
                            + ("; the probabilities score no better than predicting the base rate" if v1 == KILLED else "")))

    # CAL-02 / CAL-03 logistic recalibration
    emit("stage", "running", "logistic recalibration fits", run_id=run_id, source=SOURCE)
    cal = glm_calibration(y, m["lp"], args.alpha)
    tol = args.max_intercept
    if "intercept" in cal and "intercept_error" not in cal and not cal.get("warnings"):
        st2 = band_status(cal["intercept"], cal["intercept_ci"], 0.0, -tol, tol)
        a_lo, a_hi = cal["intercept_ci"]
        report.add(Check("CAL-02", "Calibration-in-the-large (intercept, slope fixed at 1)", STATUS_VERDICT[st2],
                         criterion=f"|a| <= {tol:g} logit with {conf} CI half-width <= {tol:g}; off = outside and CI excludes 0",
                         value=round(cal["intercept"], 6),
                         detail=f"a = {cal['intercept']:+.3f} [{a_lo:+.3f}, {a_hi:+.3f}]; observed/expected events "
                                f"{f3(m['oe_ratio'])} ({events} vs {p.sum():.1f}); mean p {f3(m['mean_p'])} vs "
                                f"prevalence {f3(base)}" + ("" if st2 != "imprecise" else "; too few events to judge at this tolerance")))
    else:
        report.add(Check("CAL-02", "Calibration-in-the-large (intercept, slope fixed at 1)", UNVERIFIED,
                         criterion=f"|a| <= {tol:g} logit", detail=cal.get("intercept_error") or cal.get("error")
                         or "; ".join(cal.get("warnings", [])) or "fit failed"))
    lo, hi = args.slope_lo, args.slope_hi
    if "slope" in cal and "slope_error" not in cal and not cal.get("warnings"):
        st3 = band_status(cal["slope"], cal["slope_ci"], 1.0, lo, hi)
        s_lo, s_hi = cal["slope_ci"]
        if s_lo <= 0:
            shape = "unrelated to the outcome once rescaled (slope not above 0)"
        else:
            shape = "too extreme (overconfident)" if cal["slope"] < 1 else "too timid (underconfident)"
        report.add(Check("CAL-03", "Calibration slope of logit(p)", STATUS_VERDICT[st3],
                         criterion=f"slope in [{lo:g}, {hi:g}] with {conf} CI half-width <= {(hi - lo) / 2:g}; off = outside and CI excludes 1",
                         value=round(cal["slope"], 6),
                         detail=f"b = {cal['slope']:.3f} [{s_lo:.3f}, {s_hi:.3f}]" +
                                (f"; probabilities are {shape}" if st3 == "off" else "") +
                                ("; too few events to judge at this tolerance" if st3 == "imprecise" else "")))
    else:
        report.add(Check("CAL-03", "Calibration slope of logit(p)", UNVERIFIED, criterion=f"slope in [{lo:g}, {hi:g}]",
                         detail=cal.get("slope_error") or cal.get("error") or "; ".join(cal.get("warnings", [])) or "fit failed"))

    # CAL-04 ECE with its noise floor under perfect calibration
    if args.resamples:
        emit("stage", "running", f"ECE noise floor, {args.resamples} consistency resamples", run_id=run_id, source=SOURCE)
        null = ece_noise(p, idx, nb, args.resamples, rng)
        p_noise = float((1 + np.sum(null >= m["ece"])) / (args.resamples + 1))
        floor95 = float(np.quantile(null, 0.95))
    else:
        null, p_noise, floor95 = None, 0.0, math.nan
    if m["ece"] <= args.max_ece:
        v4 = SURVIVES
    elif p_noise < args.alpha:
        v4 = WOUNDED
    else:
        v4 = UNVERIFIED
    report.add(Check("CAL-04", "Expected calibration error (reliability table)", v4,
                     criterion=f"ECE <= {args.max_ece:g}; above it, WOUNDED only if beyond the perfect-calibration noise (p < {args.alpha:g})",
                     value=round(m["ece"], 6),
                     detail=f"ECE {m['ece']:.4f}, MCE {m['mce']:.4f} over {nb} {args.strategy} bins; "
                            + (f"noise floor (95th pct under perfect calibration) {floor95:.4f}, p = {p_noise:.3f}"
                               if null is not None else "noise floor skipped (--resamples 0)")
                            + ("; the excess is within sampling noise: use fewer bins or more rows" if v4 == UNVERIFIED else "")))

    # CAL-05 discrimination against the base-rate baseline (AUC 0.5, AP = prevalence)
    auc, auc_se = auc_delong(y, p)
    a_lo, a_hi = auc_ci(auc, auc_se, z)
    ap = average_precision(y, p)
    v5 = KILLED if auc <= 0.5 else (WOUNDED if a_lo <= 0.5 else SURVIVES)
    report.add(Check("CAL-05", "Discrimination beats the base-rate baseline (AUC > 0.5)", v5,
                     criterion=f"AUC {conf} CI (DeLong) lower bound > 0.5; AUC <= 0.5 is KILLED",
                     value=round(auc, 6),
                     detail=f"AUC {auc:.3f} [{a_lo:.3f}, {a_hi:.3f}]; average precision {ap:.3f} vs no-skill "
                            f"{base:.3f} (lift {ap / base:.2f}x)"))

    # Reliability table
    n_k, sp, sy = bin_sums(y, p, idx, nb)
    rows = []
    for k in range(nb):
        if n_k[k] == 0:
            continue
        clo, chi = wilson(sy[k], n_k[k], z)
        mp, ob = sp[k] / n_k[k], sy[k] / n_k[k]
        rows.append({"bin": k + 1, "lo": float(edges[k]), "hi": float(edges[k + 1]), "n": int(n_k[k]),
                     "mean_p": float(mp), "observed": float(ob), "ci_lo": clo, "ci_hi": chi,
                     "gap": float(ob - mp), "outside_ci": bool(mp < clo or mp > chi)})
    rel_df = pd.DataFrame(rows)
    write_once(run_dir / "reliability.csv", rel_df.to_csv(index=False, lineterminator="\n"))
    table = [f"| bin | p range | n | mean p | observed | {conf} Wilson CI | gap |", "|---|---|---|---|---|---|---|"]
    table += [f"| {r['bin']} | {r['lo']:.3f}-{r['hi']:.3f} | {r['n']} | {r['mean_p']:.3f} | {r['observed']:.3f} | "
              f"{r['ci_lo']:.3f}-{r['ci_hi']:.3f} | {r['gap']:+.3f}{' *' if r['outside_ci'] else ''} |" for r in rows]
    table.append("\n`*` mean p lies outside the Wilson interval of the observed rate.")

    # CAL-06 per-group metrics
    groups_out = []
    if args.group:
        labels = df[args.group][keep].astype("string").fillna("<missing>").to_numpy(dtype=object)
        status = {"ok": [], "off": [], "imprecise": [], "small": []}
        for lab in sorted(set(labels), key=str):
            g = labels == lab
            yg, pg = y[g], p[g]
            gm = core_metrics(yg, pg, idx[g], nb, args.clip)
            row = {k: v for k, v in gm.items() if k != "lp"}
            row["group"] = str(lab)
            row["brier_skill"] = (1 - gm["brier"] / gm["brier_base_rate"]) if 0 < gm["prevalence"] < 1 else math.nan
            row["auc"] = auc_delong(yg, pg)[0] if 0 < gm["events"] < gm["n"] else math.nan
            if gm["n"] >= args.min_group_n and 0 < gm["events"] < gm["n"]:
                gc = glm_calibration(yg, gm["lp"], args.alpha, slope=False)
                if "intercept" in gc and "intercept_error" not in gc and not gc.get("warnings"):
                    row["intercept"], row["intercept_ci"] = gc["intercept"], list(gc["intercept_ci"])
                    st = band_status(gc["intercept"], gc["intercept_ci"], 0.0, -tol, tol)
                else:
                    st = "imprecise"
            else:
                st = "small"
            row["status"] = st
            status[st].append(str(lab))
            groups_out.append(row)
        if status["off"]:
            v6 = WOUNDED
        elif status["imprecise"] or not status["ok"]:
            v6 = UNVERIFIED
        else:
            v6 = SURVIVES
        report.add(Check("CAL-06", f"Per-group calibration-in-the-large ({args.group})", v6,
                         criterion=f"each group with n >= {args.min_group_n} and both outcomes: |a| <= {tol:g} logit (CAL-02 rule)",
                         value=f"{len(status['off'])} off / {len(status['ok'])} ok / {len(status['imprecise'])} imprecise",
                         detail="; ".join(f"{k}: {', '.join(v[:8])}{' ...' if len(v) > 8 else ''}"
                                          for k, v in status.items() if v)))
        gdf = pd.DataFrame(groups_out)
        write_once(run_dir / "groups.csv", gdf.drop(columns=["intercept_ci"], errors="ignore")
                   .to_csv(index=False, lineterminator="\n"))

    # CAL-07 prior-shift correction for class-weighted or resampled training
    shift = None
    if args.prior_train is not None:
        pi_s, pi_t = args.prior_train, args.prior_target
        p2 = prior_shift(p, pi_s, pi_t)
        idx2, edges2 = assign_bins(p2, args.bins, args.strategy)
        m2 = core_metrics(y, p2, idx2, len(edges2) - 1, args.clip)
        c2 = glm_calibration(y, m2["lp"], args.alpha)
        shift = {"prior_train": pi_s, "prior_target": pi_t,
                 "logit_shift": math.log(pi_t / (1 - pi_t)) - math.log(pi_s / (1 - pi_s)),
                 "before": {k: v for k, v in m.items() if k != "lp"} | {k: cal.get(k) for k in ("intercept", "slope")},
                 "after": {k: v for k, v in m2.items() if k != "lp"} | {k: c2.get(k) for k in ("intercept", "slope")}}
        ok_raw = "intercept" in cal and "intercept_error" not in cal and not cal.get("warnings")
        ok_new = "intercept" in c2 and "intercept_error" not in c2 and not c2.get("warnings")
        st_raw = band_status(cal["intercept"], cal["intercept_ci"], 0.0, -tol, tol) if ok_raw else "imprecise"
        st_new = band_status(c2["intercept"], c2["intercept_ci"], 0.0, -tol, tol) if ok_new else "imprecise"
        if st_raw == "off":
            fix = ("the corrected p' is calibrated in the large: use p' as the probability" if st_new == "ok" else
                   "the correction does not repair it: the miscalibration is not only a prior shift")
        elif st_raw == "ok":
            fix = ("applying the stated priors would miscalibrate them (was the correction already applied, or are the priors wrong?)"
                   if st_new == "off" else "the prior shift is immaterial here")
        else:
            fix = "too few events to tell whether the raw probabilities carry the training prior"
        report.add(Check("CAL-07", "Probabilities free of the training-prior shift (class weights / resampling)",
                         STATUS_VERDICT[st_raw],
                         criterion=f"raw calibration-in-the-large within {tol:g} logit (CAL-02 rule); p' = p*r1/(p*r1+(1-p)*r0)",
                         value=f"{f3(cal.get('intercept'))} -> {f3(c2.get('intercept'))}",
                         detail=f"pi_train {pi_s:g} -> pi_target {pi_t:g} shifts logit(p) by {shift['logit_shift']:+.3f}; "
                                f"Brier {m['brier']:.4f} -> {m2['brier']:.4f}, ECE {m['ece']:.4f} -> {m2['ece']:.4f}, "
                                f"mean p {m['mean_p']:.3f} -> {m2['mean_p']:.3f} (prevalence {base:.3f}); {fix}"))

    # Sections and machine-readable results
    trend = (f"Brier {m['brier']:.4f} vs base rate {m['brier_base_rate']:.4f} (skill {bss:+.3f}); "
             f"intercept {f3(cal.get('intercept'))}, slope {f3(cal.get('slope'))}; ECE {m['ece']:.4f}; "
             f"AUC {auc:.3f}, AP {ap:.3f} vs prevalence {base:.3f}. Units: probability; denominator {n} rows "
             f"({events} events), {dropped} row(s) dropped for missing y or p.")
    unc = (f"{conf} CIs: Brier difference [{dlo:+.4f}, {dhi:+.4f}]; AUC [{a_lo:.3f}, {a_hi:.3f}]"
           + (f"; slope [{cal['slope_ci'][0]:.3f}, {cal['slope_ci'][1]:.3f}]" if "slope_ci" in cal else "")
           + (f"; intercept [{cal['intercept_ci'][0]:+.3f}, {cal['intercept_ci'][1]:+.3f}]" if "intercept_ci" in cal else ""))
    power = ("Precision: " + (f"slope CI half-width {(cal['slope_ci'][1] - cal['slope_ci'][0]) / 2:.3f} vs band "
                              f"half-width {(hi - lo) / 2:g}" if "slope_ci" in cal else "slope not estimable")
             + (f"; ECE noise floor {floor95:.4f} vs tolerance {args.max_ece:g}" if null is not None else ""))
    report.section("Trend", "\n\n".join([trend, unc, power]))
    report.section("Reliability table", "\n".join(table))
    report.section("Brier decomposition (Murphy)",
                   "| component | value |\n|---|---|\n" + "\n".join(
                       f"| {k} | {v:.5f} |" for k, v in mur.items())
                   + f"\n| base-rate Brier | {m['brier_base_rate']:.5f} |\n| log loss | {m['log_loss']:.5f} |"
                   + "\n\nBrier = reliability - resolution + uncertainty + within_bin; within_bin is 0 when p is"
                     " constant inside each bin.")
    if groups_out:
        gl = ["| group | n | events | mean p | observed | O/E | Brier skill | AUC | intercept | status |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        gl += [f"| {g['group']} | {g['n']} | {g['events']} | {g['mean_p']:.3f} | {g['prevalence']:.3f} | "
               f"{f3(g['oe_ratio'])} | {f3(g['brier_skill'])} | {f3(g['auc'])} | {f3(g.get('intercept'))} | {g['status']} |"
               for g in groups_out]
        report.section("Per-group metrics (strata)", "\n".join(gl))
    if shift:
        keys = ("mean_p", "oe_ratio", "brier", "log_loss", "ece", "intercept", "slope")
        sl = ["| metric | raw p | corrected p' |", "|---|---|---|"]
        sl += [f"| {k} | {f3(shift['before'].get(k))} | {f3(shift['after'].get(k))} |" for k in keys]
        sl.append("\nA prior shift moves logit(p) by a constant, so it changes the intercept and leaves the slope"
                  " (and AUC) unchanged.")
        report.section("Prior-shift correction", "\n".join(sl))
    report.section("Notes", "\n".join([
        "- The base-rate baseline uses this sample's prevalence, the best constant forecast in-sample; beating it"
        " is a floor, not a benchmark against a competing model.",
        "- ECE is biased upward in small bins; the noise floor shows what perfect calibration would score here.",
        "- Calibration measured on the data the model was fitted on is optimistic; use held-out rows."]))
    report.data.update({
        "n": n, "events": events, "prevalence": base, "rows_dropped": dropped,
        "brier": m["brier"], "brier_base_rate": m["brier_base_rate"], "brier_skill": bss,
        "brier_diff": dm, "brier_diff_ci": [dlo, dhi], "murphy": mur, "log_loss": m["log_loss"],
        "ece": m["ece"], "mce": m["mce"], "ece_noise_p": p_noise if null is not None else None,
        "ece_noise_floor95": floor95 if null is not None else None,
        "bins": {"strategy": args.strategy, "requested": args.bins, "used": nb, "edges": edges.tolist()},
        "calibration": {k: v for k, v in cal.items()}, "oe_ratio": m["oe_ratio"],
        "auc": auc, "auc_se": auc_se, "auc_ci": [a_lo, a_hi], "average_precision": ap,
        "reliability_table": rows, "groups": groups_out, "prior_shift": shift})


if __name__ == "__main__":
    sys.exit(run_main(SCRIPT, main, build_parser()))
