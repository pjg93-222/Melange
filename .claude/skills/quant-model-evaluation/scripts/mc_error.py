#!/usr/bin/env python3
"""Monte-Carlo error, convergence and decision stability of a stochastic model's replications. Read-only:
reads one CSV of replication outputs; writes only its run folder (report.md, report.json, metrics.csv).

Input shapes (one row per replication in file order, or ordered by --rep):
  wide    columns = metrics                              --data reps.csv [--metrics a,b] [--rep rep]
  long    one row per (replication, metric)              --rep rep --metric name --value value
  top-K   one row per (replication, entity) with a score --rep rep --entity unit --score score --topk K

Per metric: mean; Monte-Carlo standard error (MCSE) three ways: iid sd/sqrt(n), batch means, and
autocorrelation-adjusted sd/sqrt(ESS) with ESS from Geyer's (1992) initial monotone sequence (capped at
n*log10(n)); the replications needed to reach the target precision; a running-mean table; a drift z-score
(first 10% vs last 50% of replications, the Geweke 1992 windows). The precision verdict uses sd/sqrt(n),
switching to the ESS-adjusted MCSE for any column whose replications fail the Ljung-Box independence test.
--compare A,B: paired difference per replication, so common random numbers (CRN) are credited through
the covariance; the gap is resolved when |mean(A-B)| > z * MCSE(A-B) (Koehler, Brown & Haneuse 2009;
Morris, White & Crowther 2019 on reporting Monte-Carlo error).
--topk K: the top-K set by mean score, re-derived on bootstrap resamples of the replications: P(same
set), Kendall tau-b (scipy.stats.kendalltau) between full and resampled mean scores, per-entity inclusion
frequency, and the paired gap between the K-th and (K+1)-th entity.

Verdicts: precision met -> SURVIVES, else WOUNDED (with replications needed); fewer than --min-reps
replications -> UNVERIFIED-HERE. Gap > z*MCSE -> SURVIVES, else WOUNDED. Top-K: P(same set) >=
--min-stability and boundary gap > z*MCSE -> SURVIVES; P(same set) < --kill-below -> KILLED (the
decision is set by the seed, not the model); otherwise WOUNDED. Autocorrelated replications (Ljung-Box
test, Bonferroni over columns at family-wise --indep-alpha) or drift between early and late replications
(z-test, family-wise --drift-alpha) -> WOUNDED: independent replications should show neither.
Degenerate replications: a column whose values are identical in every replication (range within
--degenerate-rtol) gets MC-DEGENERATE WOUNDED: either the model is deterministic (Monte Carlo is
unnecessary) or the seed/randomness never reached it. Such a column never passes: its precision check is
UNVERIFIED-HERE, it is left out of the independence and drift tests, and a comparison or top-K boundary
built only from constant columns is UNVERIFIED-HERE.

Usage:
  python scripts/mc_error.py --data reps.csv --target-rel 0.01 --compare policy_a,policy_b
  python scripts/mc_error.py --data scores.csv --rep rep --entity member --score p_flip --topk 10

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
"""
from __future__ import annotations

import csv
import io
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (Check, Report, UsageError, base_parser, run_main, require_file, write_once,  # noqa: E402
                     SURVIVES, WOUNDED, KILLED, UNVERIFIED)

import numpy as np  # noqa: E402  (no pandas: the csv module keeps start-up fast)
from scipy import special  # noqa: E402  (scipy.special, not scipy.stats: half the start-up time)

SCRIPT = "mc_error"


def build_parser():
    p = base_parser(__doc__)
    p.add_argument("--data", required=True, help="CSV of replication outputs")
    p.add_argument("--rep", help="replication id column (orders the rows; required for long and top-K input)")
    p.add_argument("--metrics", help="wide input: comma-separated metric columns (default: all numeric)")
    p.add_argument("--metric", help="long input: metric-name column")
    p.add_argument("--value", help="long input: value column")
    p.add_argument("--entity", help="top-K input: entity column")
    p.add_argument("--score", help="top-K input: score column")
    p.add_argument("--topk", type=int, help="top-K input: size of the selected set")
    p.add_argument("--smaller-better", action="store_true", help="top-K: rank ascending (costs, ranks)")
    tgt = p.add_mutually_exclusive_group()
    tgt.add_argument("--target-se", type=float, help="absolute MCSE target per metric")
    tgt.add_argument("--target-rel", type=float, help="MCSE target as a share of |mean| (default 0.01)")
    p.add_argument("--batch", type=int, help="batch size for batch-means MCSE (default floor(sqrt(n)))")
    p.add_argument("--compare", help="A,B: two metrics (or entities) to compare pairwise")
    p.add_argument("--z", type=float, default=2.0, help="gap must exceed z * MCSE (default 2)")
    p.add_argument("--boot", type=int, default=1000, help="bootstrap resamples for top-K stability (default 1000)")
    p.add_argument("--min-stability", type=float, default=0.9, help="top-K SURVIVES at P(same) >= this (default 0.9)")
    p.add_argument("--kill-below", type=float, default=0.5, help="top-K KILLED at P(same) < this (default 0.5)")
    p.add_argument("--min-reps", type=int, default=10, help="fewer replications -> UNVERIFIED-HERE (default 10)")
    p.add_argument("--indep-alpha", type=float, default=0.01,
                   help="family-wise level of the Ljung-Box independence check, Bonferroni over columns (default 0.01)")
    p.add_argument("--lb-lags", type=int, default=0,
                   help="Ljung-Box lags (default 0 = automatic: min(10, n // 5), at least 1)")
    p.add_argument("--drift-alpha", type=float, default=0.01,
                   help="family-wise level of the drift check, Bonferroni over columns (default 0.01)")
    p.add_argument("--drift-min-reps", type=int, default=20,
                   help="fewer replications -> the drift check is UNVERIFIED-HERE (default 20)")
    p.add_argument("--degenerate-rtol", type=float, default=1e-12,
                   help="a column is degenerate when its range <= this x max(1, max |value|) (default 1e-12)")
    return p


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #
def _num(cell):
    try:
        return float(cell)
    except ValueError:
        return math.nan


def _read(src):
    """Header (stripped names) and {column: [cell text]} via the csv module (no pandas: faster start-up)."""
    try:
        with open(src, encoding="utf-8-sig", newline="") as fh:
            rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise UsageError(f"cannot read --data as CSV: {exc}") from None
    if len(rows) < 2:
        raise UsageError("--data has no rows")
    header = [h.strip() for h in rows[0]]
    if len(set(header)) != len(header):
        raise UsageError(f"--data repeats a column name: {header}")
    return header, {h: [r[j].strip() if j < len(r) else "" for r in rows[1:]] for j, h in enumerate(header)}


def _rep_order(ids):
    """Row order by replication id: numeric when every id is a number, text otherwise."""
    nums = [_num(v) for v in ids]
    key = (lambda i: nums[i]) if all(math.isfinite(x) for x in nums) else (lambda i: ids[i])
    return sorted(range(len(ids)), key=key)


def _matrix(grid, what):
    """Cell text -> float matrix; missing or non-numeric and infinite values are usage errors (CR-12)."""
    M = np.array([[_num(c) for c in row] for row in grid], dtype=float).reshape(len(grid), -1)
    if np.isnan(M).any():
        raise UsageError(f"{what}: {int(np.isnan(M).sum())} values are missing or non-numeric; every replication "
                         "must report every value")
    if np.isinf(M).any():
        raise UsageError(f"{what}: {int(np.isinf(M).sum())} values are infinite (inf/-inf); fix or drop those "
                         "replications")
    return M


def _pivot(cols, rep, key, val, what):
    cells = {}
    for r_, k, v in zip(cols[rep], cols[key], cols[val]):
        if (r_, k) in cells:
            raise UsageError(f"{what}: some (replication, {key}) pairs appear more than once")
        cells[(r_, k)] = v
    ids, names = list(dict.fromkeys(cols[rep])), sorted(set(cols[key]))
    grid = [[cells.get((ids[i], nm), "") for nm in names] for i in _rep_order(ids)]
    return _matrix(grid, what), names


def load(args):
    src = require_file(args.data, "--data")
    header, cols = _read(src)
    topk = any(v is not None for v in (args.entity, args.score, args.topk))
    long = any(v is not None for v in (args.metric, args.value))
    need = [args.rep, args.entity, args.score] if topk else [args.rep, args.metric, args.value] if long else []
    if (topk or long) and (None in need or (topk and args.topk is None)):
        raise UsageError("top-K input needs --rep --entity --score --topk; long input needs --rep --metric --value")
    missing = [c for c in need + [args.rep] if c and c not in cols]
    if missing:
        raise UsageError(f"columns not in --data: {missing}; available: {header}")
    if topk:
        return (src, "topk", *_pivot(cols, args.rep, args.entity, args.score, "top-K input"))
    if long:
        return (src, "metrics", *_pivot(cols, args.rep, args.metric, args.value, "long input"))
    order = list(range(len(cols[header[0]])))
    if args.rep:
        if len(set(cols[args.rep])) != len(cols[args.rep]):
            raise UsageError(f"--rep column {args.rep!r} has duplicate ids in wide input")
        order = _rep_order(cols[args.rep])
    numeric = [h for h in header if h != args.rep and any(cols[h]) and
               all(not math.isnan(_num(c)) or c.lower() == "nan" for c in cols[h] if c)]
    names = [c.strip() for c in args.metrics.split(",") if c.strip()] if args.metrics else numeric
    missing = [c for c in names if c not in cols]
    if missing or not names:
        raise UsageError(f"metric columns not found: {missing or 'no numeric columns'}; available: {header}")
    return src, "metrics", _matrix([[cols[nm][i] for nm in names] for i in order], "wide input"), names


# --------------------------------------------------------------------------- #
# Monte-Carlo error estimators
# --------------------------------------------------------------------------- #
def acov(x):
    """Biased (divide-by-n) autocovariances at lags 0..n-1, via zero-padded FFT."""
    n = x.size
    f = np.fft.rfft(x - x.mean(), n=2 * n)
    return np.fft.irfft(f * np.conj(f), n=2 * n)[:n] / n


def ess_geyer(x):
    """ESS of the mean: n * gamma_0 / sigma2, with the asymptotic variance sigma2 = -gamma_0 + 2 * sum Gamma_k,
    Gamma_k = gamma_2k + gamma_2k+1 summed while positive and forced non-increasing (Geyer 1992, initial
    monotone sequence). Capped at n*log10(n) for strongly antithetic series. Returns (ess, sigma2)."""
    n = x.size
    g = acov(x)
    if n < 4 or g[0] <= 0:
        return float(n), float(max(g[0], 0.0))
    m = (n - 1) // 2
    pairs = g[0:2 * m:2] + g[1:2 * m:2]
    stop = np.flatnonzero(pairs <= 0)
    pairs = np.minimum.accumulate(pairs[:stop[0] if stop.size else pairs.size])
    cap = n * math.log10(max(n, 10))
    sigma2 = max(-g[0] + 2.0 * pairs.sum(), n * g[0] / cap)
    return float(n * g[0] / sigma2), float(sigma2)


def mcse_batch(x, b):
    """Batch means: sd of the a = n // b non-overlapping batch means, divided by sqrt(a)."""
    a = x.size // b
    if a < 2:
        return float("nan")
    return float(x[:a * b].reshape(a, b).mean(axis=1).std(ddof=1) / math.sqrt(a))


def summarize(x, batch, lags, alpha, ncols=1):
    """Mean and MCSE three ways. The MCSE used for verdicts is the canonical sd/sqrt(n) unless the series fails
    the Ljung-Box independence test (Bonferroni over ncols series at family-wise alpha); then it is the larger
    of the iid and ESS-adjusted values. (Geyer's ESS alone is too noisy on truly independent replications.)"""
    n = x.size
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    ess, sigma2 = ess_geyer(x)
    iid, adj = sd / math.sqrt(n), math.sqrt(sigma2 / n)
    q, p = ljung_box(x, lags) if n >= 4 else (float("nan"), 1.0)
    p_adj = min(1.0, p * ncols)
    dependent = p_adj < alpha
    return {"n": n, "mean": float(x.mean()), "sd": sd, "mcse_iid": iid, "mcse_batch": mcse_batch(x, batch),
            "mcse_ess": adj, "ess": ess, "ljung_box_q": q, "ljung_box_p_adj": p_adj,
            "mcse_rule": "ESS-adjusted" if dependent else "iid", "mcse": max(iid, adj) if dependent else iid}


def ljung_box(x, lags):
    """Ljung & Box (1978) portmanteau test of no autocorrelation up to `lags`: Q ~ chi2(lags) under
    independence. Returns (Q, p-value)."""
    n, g = x.size, acov(x)
    if g[0] <= 0:
        return 0.0, 1.0
    k = np.arange(1, lags + 1)
    q = float(n * (n + 2) * np.sum((g[k] / g[0]) ** 2 / (n - k)))
    return q, float(special.gammaincc(lags / 2.0, q / 2.0))  # chi-square(lags) upper tail


def kendall_taus(x, rows):
    """Kendall tau-b between x and every row of `rows`, one scipy.stats.kendalltau call per row: O(E log E)
    time and O(E) memory per resample, so large entity sets stay feasible. Imported here so the other modes
    keep the lighter start-up; constant rows give NaN."""
    import warnings
    from scipy.stats import kendalltau
    out = np.full(rows.shape[0], np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # constant-input warnings: the NaN is reported as such
        for b, row in enumerate(rows):
            out[b] = kendalltau(x, row, method="asymptotic")[0]
    return out


def drift_z(x, mcse_full):
    """(mean of first 10% - mean of last 50%) / combined standard error, on the Geweke (1992) windows.
    Each window's error uses the pooled full-series variance n * MCSE^2 (valid under the no-drift null and
    far steadier than a 2-point window's own sd)."""
    n = x.size
    a, b = x[:max(2, n // 10)], x[n - n // 2:]
    sigma2 = n * mcse_full ** 2
    den = math.sqrt(sigma2 / a.size + sigma2 / b.size)
    return float((a.mean() - b.mean()) / den) if den > 0 else 0.0


def _clean(v):
    """JSON-safe copy: NaN/inf -> None, numpy scalars -> Python."""
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, (float, np.floating)):
        return float(v) if math.isfinite(v) else None
    if isinstance(v, np.integer):
        return int(v)
    return v


def running_table(x, final_mcse):
    rows = []
    for f in (0.1, 0.25, 0.5, 0.75, 1.0):
        k = max(2, int(round(f * x.size)))
        m = float(x[:k].mean())
        rows.append({"reps": k, "mean": m, "mcse_iid": float(x[:k].std(ddof=1) / math.sqrt(k)),
                     "dist_to_final_in_mcse": abs(m - float(x.mean())) / final_mcse if final_mcse > 0 else 0.0})
    return rows


def paired_gap(a, b, batch, lags, alpha):
    d = summarize(a - b, batch, lags, alpha)
    sa, sb = summarize(a, batch, lags, alpha), summarize(b, batch, lags, alpha)
    unpaired = math.hypot(sa["mcse"], sb["mcse"])
    rho = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else float("nan")
    return d, unpaired, rho


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def _fmt(v):
    return f"{v:.4g}" if isinstance(v, (float, np.floating)) else str(v)


def _cell(v):
    """metrics.csv cell: empty for None/NaN, full precision for floats."""
    if v is None or (isinstance(v, (float, np.floating)) and math.isnan(v)):
        return ""
    return repr(float(v)) if isinstance(v, (float, np.floating)) else str(v)


def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    src, mode, M, names = load(args)
    report.add_input(src)
    report.note_packages(["numpy", "scipy"])
    n = M.shape[0]
    if n < 2:
        raise UsageError("need at least 2 replications")
    if not (args.z > 0 and args.boot >= 100 and 0 < args.kill_below <= args.min_stability <= 1
            and args.min_reps >= 2 and 0 < args.indep_alpha < 1 and 0 < args.drift_alpha < 1
            and args.lb_lags >= 0 and args.drift_min_reps >= 4 and args.degenerate_rtol >= 0):
        raise UsageError("need z > 0, boot >= 100, 0 < kill-below <= min-stability <= 1, min-reps >= 2, "
                         "0 < indep-alpha < 1, 0 < drift-alpha < 1, lb-lags >= 0, drift-min-reps >= 4, "
                         "degenerate-rtol >= 0")
    for v, flag in ((args.target_se, "--target-se"), (args.target_rel, "--target-rel")):
        if v is not None and not v > 0:
            raise UsageError(f"{flag} must be positive")
    target_rel = args.target_rel if args.target_se is None and args.target_rel is not None else \
        (0.01 if args.target_se is None else None)
    batch = args.batch or max(1, int(math.sqrt(n)))
    if batch < 1 or batch > n // 2:
        raise UsageError(f"--batch must be between 1 and n/2 = {n // 2}")
    enough = n >= args.min_reps
    lags = args.lb_lags or max(1, min(10, n // 5))
    if lags >= n:
        raise UsageError(f"--lb-lags must be below the number of replications ({n})")
    # A column that is identical in every replication carries no Monte-Carlo information (CR-01): it is kept
    # out of the independence/drift families and none of its checks may pass.
    degen = {nm: float(np.ptp(M[:, j])) <= args.degenerate_rtol * max(1.0, float(np.abs(M[:, j]).max()))
             for j, nm in enumerate(names)}
    varying = [nm for nm in names if not degen[nm]]
    summ = {nm: summarize(M[:, j], batch, lags, args.indep_alpha, max(1, len(varying)))
            for j, nm in enumerate(names)}
    for j, nm in enumerate(names):
        s = summ[nm]
        s["degenerate"] = degen[nm]
        s["drift_z"] = drift_z(M[:, j], s["mcse"]) if n >= args.drift_min_reps else float("nan")
        tgt = args.target_se if args.target_se is not None else target_rel * abs(s["mean"])
        s["target_se"] = tgt
        s["reps_needed"] = int(math.ceil(n * (s["mcse"] / tgt) ** 2)) if tgt > 0 else None
    flat = [nm for nm in names if degen[nm]]
    report.add(Check(
        id="MC-DEGENERATE", title="Every column varies across replications", verdict=WOUNDED if flat else SURVIVES,
        value=len(flat), criterion=(f"range across replications > {args.degenerate_rtol:g} x max(1, max |value|) "
                                    "for every column"),
        detail=(f"zero variance across {n} replications in {len(flat)} of {len(names)} column(s) {flat[:10]}: either "
                "the model is deterministic (Monte Carlo unnecessary) or the seed/randomness never reached it"
                if flat else "")))

    if mode == "metrics":  # ------------------------------------------------ per-metric precision
        rule = (f"--target-se {args.target_se:g}" if args.target_se is not None
                else f"--target-rel {target_rel:g} x |mean|")
        for j, nm in enumerate(names):
            s = summ[nm]
            info = (f"mean {s['mean']:.4g}, sd {s['sd']:.4g}; MCSE iid {s['mcse_iid']:.3g}, batch {s['mcse_batch']:.3g}, "
                    f"ESS-adjusted {s['mcse_ess']:.3g} (ESS {s['ess']:.0f} of {n})")
            if degen[nm]:
                verdict, why = UNVERIFIED, (f"zero variance across {n} replications (MC-DEGENERATE): precision cannot "
                                            f"be judged; {info}")
            elif not enough:
                verdict, why = UNVERIFIED, f"only {n} replications (< --min-reps {args.min_reps}); {info}"
            elif s["target_se"] <= 0:
                verdict, why = UNVERIFIED, f"relative target undefined at mean 0: give --target-se; {info}"
            elif s["mcse"] <= s["target_se"]:
                verdict, why = SURVIVES, info
            else:
                verdict, why = WOUNDED, f"{info}; about {s['reps_needed']} replications needed for the target"
            report.add(Check(id=f"MC-PREC-{j + 1:02d}", title=f"Monte-Carlo precision of {nm}", verdict=verdict,
                             value=s["mcse"], detail=f"{why}; MCSE rule used: {s['mcse_rule']}",
                             criterion=(f"MCSE <= {rule} (sd/sqrt(n); ESS-adjusted if the column fails the "
                                        "independence test)")))

    # Independence and drift (varying columns only) ------------------------------------------------------
    excluded = f"; {len(flat)} constant column(s) left out (MC-DEGENERATE)" if flat else ""
    indep_rule = (f"Ljung-Box (lags 1..{lags}) Bonferroni-adjusted p >= {args.indep_alpha:g} for every varying "
                  "column")
    if not varying or not enough:
        report.add(Check(id="MC-INDEP", title="Replications behave as independent draws", verdict=UNVERIFIED,
                         criterion=indep_rule,
                         detail="every column has zero variance" if not varying else f"only {n} replications"))
    else:
        low = [nm for nm in varying if summ[nm]["ljung_box_p_adj"] < args.indep_alpha]
        ratio = {nm: summ[nm]["ess"] / n for nm in varying}
        report.add(Check(id="MC-INDEP", title="Replications behave as independent draws",
                         verdict=WOUNDED if low else SURVIVES, criterion=indep_rule,
                         value=round(min(summ[nm]["ljung_box_p_adj"] for nm in varying), 6),
                         detail=(("autocorrelated: " + ", ".join(f"{nm} (ESS/n {ratio[nm]:.2f})" for nm in low[:10])
                                  + "; independent replications should not be: check seeding and state carried "
                                    "between replications (precision uses the ESS-adjusted MCSE)") if low else
                                 f"lowest ESS/n {min(ratio.values()):.2f}") + excluded))
    if n >= args.drift_min_reps and varying:
        zcrit = float(-special.ndtri(args.drift_alpha / (2 * len(varying))))
        drifting = [nm for nm in varying if abs(summ[nm]["drift_z"]) > zcrit]
        report.add(Check(id="MC-DRIFT", title="No drift between early and late replications",
                         verdict=WOUNDED if drifting else SURVIVES,
                         value=round(max(abs(summ[nm]["drift_z"]) for nm in varying), 3),
                         criterion=(f"|z(first 10% vs last 50% of replications)| <= {zcrit:.2f} for every varying "
                                    f"column (two-sided, Bonferroni family-wise {args.drift_alpha:g})"),
                         detail=(f"drifting: {drifting[:10]}" if drifting else "") + excluded))
    else:
        report.add(Check(id="MC-DRIFT", title="No drift between early and late replications", verdict=UNVERIFIED,
                         criterion=f"needs >= --drift-min-reps {args.drift_min_reps} replications and a varying column",
                         detail="every column has zero variance" if not varying else f"only {n} replications"))

    # Paired comparison --------------------------------------------------------------------------------
    comp = None
    if args.compare:
        pair = [c.strip() for c in args.compare.split(",")]
        if len(pair) != 2 or pair[0] == pair[1] or any(c not in names for c in pair):
            raise UsageError(f"--compare needs two different names from {names[:20]}")
        a, b = M[:, names.index(pair[0])], M[:, names.index(pair[1])]
        d, unpaired, rho = paired_gap(a, b, batch, lags, args.indep_alpha)
        z = d["mean"] / d["mcse"] if d["mcse"] > 0 else (math.inf if d["mean"] else 0.0)
        need = int(math.ceil(n * (args.z * d["mcse"] / d["mean"]) ** 2)) if d["mean"] else None
        comp = {"a": pair[0], "b": pair[1], "gap": d["mean"], "mcse_paired": d["mcse"], "mcse_unpaired": unpaired,
                "corr": rho, "z": z, "reps_needed": need}
        gain = (unpaired / d["mcse"]) ** 2 if d["mcse"] > 0 else math.inf
        both_flat = degen[pair[0]] and degen[pair[1]]
        report.add(Check(
            id="MC-GAP", title=f"Gap {pair[0]} - {pair[1]} resolved by the Monte-Carlo run",
            verdict=UNVERIFIED if not enough or both_flat else (SURVIVES if abs(z) > args.z else WOUNDED),
            value=round(z, 3) if math.isfinite(z) else "inf", criterion=f"|mean(A-B)| > {args.z:g} x paired MCSE",
            detail=(("both metrics are constant across replications (MC-DEGENERATE): the gap is not Monte-Carlo "
                     "evidence; " if both_flat else "")
                    + f"gap {d['mean']:.4g}, paired MCSE {d['mcse']:.3g}; unpaired it would be {unpaired:.3g} (corr "
                    f"{rho:.3f}), so pairing on common random numbers is worth x{gain:.3g} replications"
                    + ("" if abs(z) > args.z or need is None else f"; about {need} replications to resolve this gap"))))

    # Top-K stability ------------------------------------------------------------------------------------
    topk = None
    if mode == "topk":
        K, E = args.topk, len(names)
        if not 1 <= K < E:
            raise UsageError(f"--topk must be between 1 and {E - 1} (entities: {E})")
        sgn = -1.0 if args.smaller_better else 1.0
        mu = M.mean(axis=0)
        order = np.argsort(-sgn * mu, kind="stable")
        top = set(order[:K].tolist())
        d = summarize(sgn * (M[:, order[K - 1]] - M[:, order[K]]), batch, lags, args.indep_alpha)
        z = d["mean"] / d["mcse"] if d["mcse"] > 0 else (math.inf if d["mean"] > 0 else 0.0)
        rng = np.random.default_rng(args.seed)
        W = rng.multinomial(n, np.full(n, 1.0 / n), size=args.boot) / n
        mub = W @ M
        tops = np.argsort(-sgn * mub, axis=1, kind="stable")[:, :K]
        same = np.array([set(t.tolist()) == top for t in tops])
        taus = kendall_taus(mu, mub)
        incl = np.zeros(E)
        np.add.at(incl, tops.ravel(), 1.0)
        incl /= args.boot
        p_same = float(same.mean())
        contested = [names[i] for i in np.argsort(-incl) if 0.05 < incl[i] < 0.95]
        finite_taus = taus[np.isfinite(taus)]
        topk = {"k": K, "entities": E, "top": [names[i] for i in order[:K]], "p_same": p_same,
                "tau_median": float(np.median(finite_taus)) if finite_taus.size else float("nan"),
                "tau_p05": float(np.quantile(finite_taus, 0.05)) if finite_taus.size else float("nan"),
                "boundary": [names[order[K - 1]], names[order[K]]], "boundary_gap": d["mean"],
                "boundary_mcse": d["mcse"], "boundary_z": z, "contested": contested,
                "inclusion": {names[i]: float(incl[i]) for i in np.argsort(-incl)[:2 * K]}}
        ok_gap = z > args.z
        flat_edge = degen[names[order[K - 1]]] and degen[names[order[K]]]
        verdict = UNVERIFIED if not enough or not varying or flat_edge else (
            KILLED if p_same < args.kill_below else SURVIVES if p_same >= args.min_stability and ok_gap else WOUNDED)
        why_flat = ("every entity's score is constant across replications (MC-DEGENERATE): stability is not "
                    "Monte-Carlo evidence; " if not varying else
                    "the boundary pair has constant scores (MC-DEGENERATE): the gap cannot be judged; "
                    if flat_edge else "")
        report.add(Check(
            id="MC-TOPK", title=f"Top-{K} set stable under Monte-Carlo resampling", verdict=verdict,
            value=round(p_same, 4),
            criterion=(f"P(same set) >= {args.min_stability:g} and boundary gap > {args.z:g} x MCSE -> SURVIVES; "
                       f"P(same set) < {args.kill_below:g} -> KILLED"),
            detail=(why_flat + f"boundary {names[order[K - 1]]} vs {names[order[K]]}: gap {d['mean']:.4g}, z {z:.2f}; "
                    f"Kendall tau median {topk['tau_median']:.3f} (5% {topk['tau_p05']:.3f}); contested entities "
                    f"{contested[:10]}; {args.boot} bootstrap resamples of {n} replications"
                    + ("; the selected set is decided by the seed, not the model" if verdict == KILLED else ""))))

    # Artifacts and report ------------------------------------------------------------------------------
    keys = ("n", "mean", "sd", "degenerate", "mcse_iid", "mcse_batch", "mcse_ess", "ess", "ljung_box_p_adj",
            "mcse_rule", "mcse", "target_se", "reps_needed", "drift_z")
    table = [{"metric": nm, **{k: summ[nm][k] for k in keys}} for nm in names]
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["metric", *keys])
    writer.writerows([_cell(row[k]) for k in ("metric", *keys)] for row in table)
    write_once(run_dir / "metrics.csv", buf.getvalue())
    show = (sorted(table, key=lambda r: r["mean"], reverse=not args.smaller_better)[:2 * args.topk]
            if mode == "topk" else table)
    cols = ["metric", "mean", "sd", "mcse_iid", "mcse_batch", "mcse_ess", "ess", "mcse_rule", "reps_needed"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(_fmt(r[c]) for c in cols) + " |" for r in show[:40]]
    report.section(f"Monte-Carlo error ({n} replications, batch size {batch})", "\n".join(lines))
    run_rows = {nm: running_table(M[:, j], summ[nm]["mcse"]) for j, nm in enumerate(names[:8])}
    body = ["| column | reps | running mean | MCSE (iid) | distance to final mean, in final MCSEs |",
            "|---|---|---|---|---|"]
    body += [f"| {nm} | {r['reps']} | {r['mean']:.4g} | {r['mcse_iid']:.3g} | {r['dist_to_final_in_mcse']:.2f} |"
             for nm, rows in run_rows.items() for r in rows]
    report.section("Running-mean convergence (first 8 columns)", "\n".join(body))
    report.data.update(_clean({"mode": mode, "replications": n, "batch": batch, "target_rel": target_rel,
                               "target_se": args.target_se, "metrics": summ, "running": run_rows,
                               "compare": comp, "topk": topk}))


if __name__ == "__main__":
    sys.exit(run_main(SCRIPT, main, build_parser()))
