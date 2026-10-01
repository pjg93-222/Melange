#!/usr/bin/env python3
"""Out-of-sample forecast evaluation against naive, seasonal-naive, historical-mean or supplied benchmarks.
Read-only: reads one CSV of actuals and forecasts; writes only its run folder.

Usage:
  python scripts/backtest_eval.py --data FILE.csv --actual y --forecast f1 [--forecast f2 ...] --time t
      [--group g] [--benchmark naive|seasonal:K|mean|col:COL] [--nested] [--h 1] [--windows 4]
      [--lower lo --upper hi --level 0.9] [--alpha 0.10] [--min-oos-r2 0.0] [--loss mse|mae]

The CSV may hold the whole history: rows with an empty forecast still feed the lag-based benchmarks.
  naive       actual h periods earlier in the same group (the no-change forecast made h periods ahead)
  seasonal:K  actual K*ceil(h/K) periods earlier (the seasonal naive forecast)
  mean        expanding mean of the group's actuals up to h periods earlier (Campbell & Thompson 2008)
  col:COL     a supplied benchmark column
Lags count rows within a group after sorting by --time. --time must be numbers or dates (mixed date formats
are parsed one by one); text is sorted as text only with --allow-text-time. Infinite values are refused.
Every model is scored on the common rows where the actual, the benchmark and every forecast are present.

Per model: MAE, RMSE, MAPE (only when every actual is on one side of 0), OOS R^2 = 1 - SSE_model/SSE_bench, the
Diebold-Mariano test with the Harvey-Leybourne-Newbold correction (or Clark-West with --nested, where the
benchmark must be the smaller, nested model), directional hit rate with a Wilson interval, and the share of
--windows contiguous sub-windows the model wins. With --lower/--upper: PICP, MPIW, Kupiec POF and
Christoffersen independence likelihood-ratio tests.
Panels (--group): each period's loss differential is averaged over the groups present that period and the
tests run on that series of period means, which is robust to shocks common to all groups on a date and
assumes dependence dies out after h-1 lags. Per-group OOS skill is reported too; n counts periods.

Verdict rules (thresholds are flags; fix them before looking at results):
  BT-ACC-<model>  fewer than --min-n periods: UNVERIFIED-HERE. Skill <= 0: KILLED (no better than the
                  benchmark). 0 < skill <= --min-oos-r2: WOUNDED. Otherwise SURVIVES only if the one-sided
                  test p < --alpha AND the model wins >= --min-window-share of the windows; else WOUNDED.
                  Skill = OOS R^2 under --loss mse, 1 - MAE_model/MAE_bench under --loss mae.
  BT-DIR-<model>  hit rate <= baseline (--hit-baseline majority = share of the commoner direction, or coin =
                  0.5): KILLED; Wilson lower bound (1 - alpha) > baseline: SURVIVES; else WOUNDED; fewer than
                  --min-n directional calls: UNVERIFIED-HERE. --direction none skips it.
  BT-GRP-<model>  (--group) share of groups with skill > 0 >= --min-window-share: SURVIVES, else WOUNDED.
  BT-COVER        (intervals) Kupiec p >= --alpha: SURVIVES; rejected with PICP < --level: KILLED (intervals
                  too narrow); rejected with PICP > --level: WOUNDED (too wide).
  BT-INDEP        (intervals) Christoffersen independence p >= --alpha: SURVIVES, else WOUNDED (misses cluster).
Power note: effective n = n * gamma0 / long-run variance (LRV) of the loss differential; minimum detectable
mean loss difference ~ (z(1-alpha) + z(--power)) * sqrt(LRV / n), and that divided by the mean benchmark loss
in skill units. A short backtest that fails is weak evidence of no effect; say so next to the verdict.

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
A KILLED printed by this script is a candidate verdict: record it only after a second independent reader confirms it.
"""
# Formula sources:
#   Diebold & Mariano (1995) JBES 13(3):253-263, doi:10.1080/07350015.1995.10524599
#   Harvey, Leybourne & Newbold (1997) Int. J. Forecasting 13(2):281-291, doi:10.1016/S0169-2070(96)00719-4
#   Clark & West (2007) J. Econometrics 138(1):291-311, doi:10.1016/j.jeconom.2006.05.023
#   Campbell & Thompson (2008) Review of Financial Studies 21(4):1509-1531, doi:10.1093/rfs/hhm055
#   Newey & West (1987) Econometrica 55(3):703, doi:10.2307/1913610 (Bartlett long-run variance)
#   Wilson (1927) JASA 22(158):209-212 (score interval for a proportion)
#   Kupiec (1995) J. Derivatives 3(2):73-84, doi:10.3905/jod.1995.407942
#   Christoffersen (1998) International Economic Review 39(4):841-862, doi:10.2307/2527341
from __future__ import annotations

import math
import pathlib
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (Check, Report, UsageError, base_parser, run_main, require_file, write_once, emit,  # noqa: E402
                     SURVIVES, WOUNDED, KILLED, UNVERIFIED)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
# scipy.special instead of scipy.stats: same functions, much lighter import. stdtr(df, x) = Student t CDF,
# ndtr/ndtri = normal CDF/quantile, chdtrc(df, x) = chi-square upper tail; upper tails use stdtr(df, -x).
from scipy.special import chdtrc, ndtr, ndtri, stdtr, xlog1py, xlogy  # noqa: E402

SCRIPT = "backtest_eval"


def build_parser():
    p = base_parser(__doc__)
    p.add_argument("--data", required=True, help="CSV with actuals, forecasts and a time column")
    p.add_argument("--actual", required=True, help="column of realised values")
    p.add_argument("--forecast", required=True, action="append", help="forecast column; repeat for several models")
    p.add_argument("--time", required=True, help="time column: numbers or dates (mixed date formats are parsed)")
    p.add_argument("--allow-text-time", action="store_true",
                   help="sort a --time column that is neither numbers nor dates as text (refused otherwise)")
    p.add_argument("--group", help="series id when the file holds a panel of series")
    p.add_argument("--benchmark", default="naive", help="naive | seasonal:K | mean | col:COL (default naive)")
    p.add_argument("--nested", action="store_true", help="the models nest the benchmark: Clark-West, not DM-HLN")
    p.add_argument("--h", type=int, default=1, help="forecast horizon in periods (default 1)")
    p.add_argument("--windows", type=int, default=4, help="contiguous sub-windows for stability (default 4)")
    p.add_argument("--lower", help="lower bound of a prediction interval")
    p.add_argument("--upper", help="upper bound of a prediction interval")
    p.add_argument("--level", type=float, default=0.9, help="nominal coverage of [lower, upper] (default 0.9)")
    p.add_argument("--alpha", type=float, default=0.10, help="test level; intervals are 1 - alpha (default 0.10)")
    p.add_argument("--min-oos-r2", type=float, default=0.0, help="skill the model must exceed (default 0.0)")
    p.add_argument("--min-window-share", type=float, default=0.75,
                   help="share of windows (and groups) the model must win (default 0.75)")
    p.add_argument("--min-n", type=int, default=8, help="fewer evaluation periods: UNVERIFIED-HERE (default 8)")
    p.add_argument("--loss", choices=("mse", "mae"), default="mse", help="loss for skill and DM (default mse)")
    p.add_argument("--direction", choices=("change", "sign", "none"), default="change",
                   help="change: sign of y - y[t-h] vs f - y[t-h]; sign: sign of y vs f (default change)")
    p.add_argument("--hit-baseline", choices=("majority", "coin"), default="majority",
                   help="directional baseline (default majority)")
    p.add_argument("--power", type=float, default=0.8, help="power used in the detectable-skill note (default 0.8)")
    p.add_argument("--mape-eps", type=float, default=1e-6,
                   help="skip MAPE when min|actual| <= eps * max|actual| or the actuals change sign (default 1e-6)")
    return p


def _validate(a):
    if a.h < 1:
        raise UsageError("--h must be >= 1")
    if a.windows < 1:
        raise UsageError("--windows must be >= 1")
    for name, v, top in (("--level", a.level, 1), ("--power", a.power, 1), ("--min-window-share", a.min_window_share, 2)):
        if not 0 < v < top or (top == 2 and v > 1):
            raise UsageError(f"{name} must be in (0, 1{']' if top == 2 else ')'}")
    if not 0 < a.alpha < 0.5:
        raise UsageError("--alpha must be in (0, 0.5)")
    if a.min_n < 2:
        raise UsageError("--min-n must be >= 2")
    if bool(a.lower) != bool(a.upper):
        raise UsageError("--lower and --upper go together")
    if a.nested and a.loss != "mse":
        raise UsageError("Clark-West (--nested) is defined for squared-error loss; drop --loss mae")
    if len(set(a.forecast)) != len(a.forecast):
        raise UsageError("a --forecast column is repeated")


def _time_key(s: pd.Series, allow_text: bool):
    if pd.api.types.is_numeric_dtype(s):
        key = s.astype(float)
        if not np.isfinite(key.to_numpy()).all():
            raise UsageError("--time has non-finite values")
        return key, "numeric"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dt = pd.to_datetime(s, errors="coerce")
        if dt.isna().any():                  # one inferred format failed somewhere: parse element by element
            dt = pd.to_datetime(s, errors="coerce", format="mixed")
    if dt.notna().all():
        return (dt - dt.min()).dt.total_seconds().astype(float), "date"
    if not allow_text:
        raise UsageError(f"--time values are neither numbers nor dates (e.g. '{s[dt.isna()].iloc[0]}'); text order "
                         "would scramble the lags, so fix the column or pass --allow-text-time to sort it as text")
    return s.astype(str), "text (sorted as text, --allow-text-time)"


def load(src: pathlib.Path, a):
    try:
        df = pd.read_csv(src)
    except Exception as exc:  # unreadable, empty, bad encoding
        raise UsageError(f"cannot read --data as CSV: {exc}")
    if df.empty:
        raise UsageError("--data has no rows")
    bench_col = a.benchmark[4:] if a.benchmark.startswith("col:") else None
    need = [a.actual, a.time, *a.forecast] + [c for c in (a.group, a.lower, a.upper, bench_col) if c]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise UsageError(f"columns not in --data: {', '.join(missing)} (have: {', '.join(map(str, df.columns))})")
    for c in [a.actual, *a.forecast] + [c for c in (a.lower, a.upper, bench_col) if c]:
        num = pd.to_numeric(df[c], errors="coerce")
        bad = int((num.isna() & df[c].notna()).sum())
        if bad:
            raise UsageError(f"column {c} has {bad} non-numeric values")
        inf = int(np.isinf(num.to_numpy(dtype=float)).sum())
        if inf:
            raise UsageError(f"column {c} has {inf} infinite values; remove them or leave the cells empty (missing)")
        df[c] = num.astype(float)
    if df[a.time].isna().any():
        raise UsageError(f"--time column {a.time} has missing values")
    key, how = _time_key(df[a.time], a.allow_text_time)
    df["_t"] = key
    df["_g"] = df[a.group].astype(str) if a.group else "_all"
    dup = df.duplicated(["_g", "_t"])
    if dup.any():
        r = df.loc[dup].iloc[0]
        raise UsageError(f"duplicate time '{r[a.time]}' within group '{r['_g']}'; one row per group and period "
                         "(pass --group for a panel)")
    df = df.sort_values(["_g", "_t"], kind="mergesort").reset_index(drop=True)
    notes = [f"time order: {how}"]
    if not how.startswith("text"):
        gaps = [np.diff(s.to_numpy()) for _, s in df.groupby("_g")["_t"] if s.size > 2]
        irregular = sum(1 for g in gaps if np.ptp(g) > 0.25 * np.median(g))   # months (28-31 days) count as regular
        if irregular:
            notes.append(f"irregular time spacing in {irregular} group(s): lag benchmarks use the previous row, "
                         "not the previous calendar period")
    return df, notes


def make_benchmark(df: pd.DataFrame, a):
    grp = df.groupby("_g", sort=False)[a.actual]
    spec = a.benchmark
    if spec == "naive":
        return grp.shift(a.h), f"naive (actual {a.h} period(s) earlier)"
    if spec.startswith("seasonal:"):
        try:
            k = int(spec.split(":", 1)[1])
        except ValueError:
            raise UsageError("--benchmark seasonal:K needs a whole number K >= 1")
        if k < 1:
            raise UsageError("--benchmark seasonal:K needs K >= 1")
        m = k * math.ceil(a.h / k)
        return grp.shift(m), f"seasonal naive (actual {m} periods earlier, K = {k})"
    if spec == "mean":
        return (grp.transform(lambda s: s.expanding().mean().shift(a.h)),
                f"historical mean (expanding mean up to {a.h} period(s) earlier)")
    if spec.startswith("col:"):
        return df[spec[4:]], f"supplied column {spec[4:]}"
    raise UsageError("--benchmark must be naive, seasonal:K, mean or col:COL")


def _lrv(x: np.ndarray, lags: int, kernel: str):
    """Long-run variance of x: gamma0 + 2 sum_k w_k gamma_k (w = 1 rectangular, 1 - k/(lags+1) Bartlett)."""
    n = len(x)
    xc = x - x.mean()
    gam = [float(xc[k:] @ xc[:n - k]) / n for k in range(min(lags, n - 1) + 1)]
    w = [1.0 if kernel == "rectangular" else 1.0 - k / (lags + 1) for k in range(len(gam))]
    return gam[0] + 2.0 * sum(wk * g for wk, g in zip(w[1:], gam[1:])), gam[0]


def compare(d: np.ndarray, h: int, kind: str) -> dict:
    """Test mean(d) > 0 (the model is more accurate). kind 'DM-HLN': Diebold-Mariano with h-1 rectangular lags
    (DM 1995; Bartlett if that variance is not positive) times the HLN (1997) factor
    sqrt((n + 1 - 2h + h(h-1)/n) / n), referred to t(n-1). kind 'Clark-West': t-statistic of the CW (2007)
    adjusted MSPE differential with Newey-West (h-1 lags), referred to N(0,1), one-sided."""
    n = len(d)
    dbar = float(d.mean())
    kernel = "rectangular" if kind == "DM-HLN" else "bartlett"
    lrv, g0 = _lrv(d, h - 1, kernel)
    if kind == "DM-HLN" and lrv <= 0 < g0:
        lrv, g0 = _lrv(d, h - 1, "bartlett")
        kernel = "bartlett (rectangular variance was not positive)"
    out = {"kind": kind, "n": n, "mean": dbar, "gamma0": g0, "lrv": lrv, "kernel": kernel, "note": ""}
    if g0 <= 1e-24 * max(dbar * dbar, 1e-300) or lrv <= 0:
        if dbar == 0.0 or abs(dbar) <= 1e-12 * float(np.abs(d).max(initial=0.0)):
            out.update(stat=0.0, p_one=0.5, p_two=1.0, note="loss differential identically zero: equal accuracy")
        else:
            out.update(stat=math.copysign(math.inf, dbar), p_one=0.0 if dbar > 0 else 1.0, p_two=0.0,
                       note="loss differential constant (zero variance): the ordering is exact, not estimated")
        return out
    stat = dbar / math.sqrt(lrv / n)
    if kind == "DM-HLN":
        stat *= math.sqrt(max((n + 1 - 2 * h + h * (h - 1) / n) / n, 0.0))
        out.update(stat=stat, p_one=float(stdtr(n - 1, -stat)), p_two=float(2 * stdtr(n - 1, -abs(stat))))
    else:
        out.update(stat=stat, p_one=float(ndtr(-stat)), p_two=float(2 * ndtr(-abs(stat))))
    return out


def wilson(x: int, n: int, conf: float):
    """Wilson (1927) score interval for a binomial proportion."""
    if n == 0:
        return float("nan"), float("nan")
    z = ndtri(1 - (1 - conf) / 2)
    p = x / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def kupiec(x: int, n: int, p: float):
    """Kupiec (1995) proportion-of-failures LR: -2[ln L(p) - ln L(x/n)] ~ chi2(1), 0*log(0) = 0."""
    phat = x / n
    ll0 = xlog1py(n - x, -p) + xlogy(x, p)
    ll1 = xlog1py(n - x, -phat) + xlogy(x, phat)
    lr = max(-2.0 * (ll0 - ll1), 0.0)
    return lr, float(chdtrc(1, lr))


def christoffersen(viol_by_group):
    """Christoffersen (1998) independence LR from first-order transition counts (summed over groups)."""
    n = np.zeros((2, 2))
    for v in viol_by_group:
        v = np.asarray(v, dtype=int)
        for i, j in zip(v[:-1], v[1:]):
            n[i, j] += 1
    n00, n01, n10, n11 = n[0, 0], n[0, 1], n[1, 0], n[1, 1]
    tot = n.sum()
    if tot == 0:
        return float("nan"), float("nan"), n
    pi = (n01 + n11) / tot
    p01 = n01 / (n00 + n01) if n00 + n01 else 0.0
    p11 = n11 / (n10 + n11) if n10 + n11 else 0.0
    l0 = xlog1py(n00 + n10, -pi) + xlogy(n01 + n11, pi)
    l1 = xlog1py(n00, -p01) + xlogy(n01, p01) + xlog1py(n10, -p11) + xlogy(n11, p11)
    lr = max(-2.0 * (l0 - l1), 0.0)
    return lr, float(chdtrc(1, lr)), n


def _skill(lm: np.ndarray, lb: np.ndarray) -> float:
    sb = float(lb.sum())
    if sb <= 0:
        return 0.0 if float(lm.sum()) <= 0 else -math.inf
    return 1.0 - float(lm.sum()) / sb


def _f(v, d=3) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    if isinstance(v, float) and math.isinf(v):
        return "inf" if v > 0 else "-inf"
    return f"{v:.{d}g}"


def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    _validate(args)
    src = require_file(args.data, "--data")
    report.add_input(src)
    report.note_packages(["numpy", "pandas", "scipy"])
    df, notes = load(src, args)
    emit("stage", "running", "scoring forecasts against the benchmark", run_id=run_id,
         source=f"quant-model-evaluation/{SCRIPT}")
    bench, bdesc = make_benchmark(df, args)
    origin = df.groupby("_g", sort=False)[args.actual].shift(args.h)
    mask = df[args.actual].notna() & bench.notna() & df[args.forecast].notna().all(axis=1)
    ev = df.loc[mask].copy()
    if ev.empty:
        raise UsageError("no rows where the actual, the benchmark and every forecast are all present "
                         "(lag benchmarks need history rows before the first forecast)")
    ev["_b"] = bench[mask].to_numpy()
    ev["_o"] = origin[mask].to_numpy()
    notes.append(f"benchmark: {bdesc}; {int(mask.sum())} of {len(df)} rows scored")
    y = ev[args.actual].to_numpy()
    b = ev["_b"].to_numpy()
    periods = np.array(sorted(ev["_t"].unique()))
    T = len(periods)
    grouped = bool(args.group)
    loss = (lambda e: e * e) if args.loss == "mse" else np.abs
    lb = loss(y - b)
    kind = "Clark-West" if args.nested else "DM-HLN"
    n_win = min(args.windows, max(1, T // 2))
    if n_win < args.windows:
        notes.append(f"--windows reduced from {args.windows} to {n_win} ({T} periods)")
    blocks = np.array_split(periods, n_win)
    pm = lambda v: pd.Series(v, index=ev["_t"].to_numpy()).groupby(level=0).mean().reindex(periods).to_numpy()  # noqa: E731
    z_sum = ndtri(1 - args.alpha) + ndtri(args.power)
    near0 = (float(np.abs(y).min()) <= args.mape_eps * max(float(np.abs(y).max()), 1e-300)
             or not (np.all(y > 0) or np.all(y < 0)))
    if near0:
        notes.append("MAPE skipped: the actuals reach zero or change sign (MAPE needs a ratio scale)")
    rows, win_rows, grp_rows, summary = [], [], [], []
    rows.append({"model": f"benchmark ({args.benchmark})", "n_rows": len(y), "n_periods": T,
                 "MAE": float(np.mean(np.abs(y - b))), "RMSE": float(np.sqrt(np.mean((y - b) ** 2))),
                 "MAPE": None if near0 else float(np.mean(np.abs((y - b) / y)) * 100)})
    report.data["models"] = {}
    for fc in args.forecast:
        f = ev[fc].to_numpy()
        lm = loss(y - f)
        sk = _skill(lm, lb)
        r2 = _skill((y - f) ** 2, (y - b) ** 2)
        if args.nested:  # Clark & West (2007): e_b^2 - [e_m^2 - (f_b - f_m)^2]
            series = pm((y - b) ** 2 - ((y - f) ** 2 - (b - f) ** 2))
        else:
            series = pm(lb - lm)
        res = compare(series, args.h, kind) if T >= 2 else {"stat": math.nan, "p_one": math.nan, "p_two": math.nan,
                                                            "lrv": math.nan, "gamma0": math.nan, "note": "one period"}
        wins = []
        for i, blk in enumerate(blocks):
            sel = np.isin(ev["_t"].to_numpy(), blk)
            s_w = _skill(lm[sel], lb[sel])
            wins.append(s_w > 0)
            win_rows.append({"model": fc, "window": i + 1, "first": ev.loc[sel, args.time].iloc[0],
                             "last": ev.loc[sel, args.time].iloc[-1], "rows": int(sel.sum()), "skill": s_w})
        share_w = float(np.mean(wins))
        lrv, g0 = res.get("lrv", math.nan), res.get("gamma0", math.nan)
        mean_lb = float(np.mean(pm(lb)))
        if lrv and lrv > 0 and mean_lb > 0:
            n_eff, mde_loss = T * g0 / lrv, z_sum * math.sqrt(lrv / T)
            mde = mde_loss / mean_lb
        else:
            n_eff, mde_loss, mde = math.nan, math.nan, math.nan
        power_txt = (f"n = {T} periods ({len(y)} rows), effective n ~ {_f(n_eff, 3)}; a one-sided test at alpha "
                     f"{args.alpha:g} with power {args.power:g} detects a mean loss difference of about "
                     f"{_f(mde_loss)} ({args.loss}), i.e. skill of about {_f(mde)}")
        stat_txt = f"{kind} = {_f(res['stat'])}, one-sided p = {_f(res['p_one'])}"
        if T < args.min_n:
            v, why = UNVERIFIED, f"only {T} evaluation periods (< {args.min_n}); nothing can be concluded"
        elif not math.isfinite(sk) or sk <= 0:
            v, why = KILLED, "no better than the benchmark out of sample"
        elif sk <= args.min_oos_r2:
            v, why = WOUNDED, f"beats the benchmark but not by the pre-set margin {args.min_oos_r2:g}"
        elif res["p_one"] < args.alpha and share_w >= args.min_window_share:
            v, why = SURVIVES, "beats the benchmark, significantly and in most windows"
        else:
            v, why = WOUNDED, ("beats the benchmark in the point estimate but " +
                               ("not significantly" if not res["p_one"] < args.alpha else "not stably across windows"))
        skill_name = "OOS R^2" if args.loss == "mse" else "MAE skill"
        line = (f"{fc}: {skill_name} = {_f(sk)} vs {args.benchmark}; wins {sum(wins)} of {n_win} windows; "
                f"{stat_txt}; {power_txt}.")
        summary.append(line)
        report.add(Check(id=f"BT-ACC-{fc}", title=f"{fc} beats the {args.benchmark} benchmark out of sample",
                         verdict=v, value=sk,
                         criterion=(f"skill > max(0, {args.min_oos_r2:g}), one-sided {kind} p < {args.alpha:g}, "
                                    f"wins >= {args.min_window_share:g} of windows; >= {args.min_n} periods"),
                         detail=f"{why}. {line} {res.get('note', '')}".strip()))
        m = {"n_rows": len(y), "n_periods": T, "MAE": float(np.mean(np.abs(y - f))),
             "RMSE": float(np.sqrt(np.mean((y - f) ** 2))),
             "MAPE": None if near0 else float(np.mean(np.abs((y - f) / y)) * 100), "oos_r2": r2, "skill": sk,
             "test": res, "windows_won": int(sum(wins)), "windows": n_win, "n_eff": n_eff, "mde_loss": mde_loss,
             "mde_skill": mde}
        rows.append({"model": fc, "n_rows": len(y), "n_periods": T, "MAE": m["MAE"], "RMSE": m["RMSE"],
                     "MAPE": m["MAPE"], "oos_r2": r2, "skill": sk, "test": kind, "stat": res["stat"],
                     "p_one_sided": res["p_one"], "windows_won": f"{sum(wins)}/{n_win}"})
        if args.direction != "none":
            if args.direction == "change":
                ok = ~np.isnan(ev["_o"].to_numpy())
                o = ev["_o"].to_numpy()[ok]
                act, pred = np.sign(y[ok] - o), np.sign(f[ok] - o)
            else:
                act, pred = np.sign(y), np.sign(f)
            keep = act != 0
            act, pred = act[keep], pred[keep]
            nd, hits = len(act), int((act == pred).sum())
            up = float(np.mean(act > 0)) if nd else math.nan
            base = max(up, 1 - up) if args.hit_baseline == "majority" else 0.5
            rate = hits / nd if nd else math.nan
            lo_w, hi_w = wilson(hits, nd, 1 - args.alpha)
            if nd < args.min_n:
                dv = UNVERIFIED
            elif rate <= base:
                dv = KILLED
            else:
                dv = SURVIVES if lo_w > base else WOUNDED
            report.add(Check(id=f"BT-DIR-{fc}", title=f"{fc} calls the direction ({args.direction}) better than the baseline",
                             verdict=dv, value=rate,
                             criterion=(f"Wilson {100 * (1 - args.alpha):g}% lower bound > {args.hit_baseline} baseline; "
                                        f"rate <= baseline KILLED; >= {args.min_n} calls"),
                             detail=(f"{hits}/{nd} hits = {_f(rate)} (Wilson {_f(lo_w)} to {_f(hi_w)}); baseline "
                                     f"{args.hit_baseline} = {_f(base)} (share of up moves {_f(up)}).")))
            m["direction"] = {"calls": nd, "hits": hits, "rate": rate, "wilson": [lo_w, hi_w], "baseline": base}
        if grouped:
            gs = []
            for gname, idx in ev.groupby("_g").indices.items():
                if len(idx) >= 2:
                    s_g = _skill(lm[idx], lb[idx])
                    gs.append(s_g > 0)
                    grp_rows.append({"model": fc, "group": gname, "rows": len(idx), "skill": s_g})
            if len(gs) >= 2:
                share_g = float(np.mean(gs))
                report.add(Check(id=f"BT-GRP-{fc}", title=f"{fc} beats the benchmark in most groups",
                                 verdict=SURVIVES if share_g >= args.min_window_share else WOUNDED, value=share_g,
                                 criterion=f"share of groups with skill > 0 >= {args.min_window_share:g}",
                                 detail=f"wins in {sum(gs)} of {len(gs)} groups (groups with >= 2 scored rows)."))
        report.data["models"][fc] = m
    if args.lower:
        iv = df[df[args.actual].notna() & df[args.lower].notna() & df[args.upper].notna()]
        if (iv[args.lower] > iv[args.upper]).any():
            raise UsageError(f"{int((iv[args.lower] > iv[args.upper]).sum())} rows have --lower above --upper")
        inside = ((iv[args.lower] <= iv[args.actual]) & (iv[args.actual] <= iv[args.upper])).to_numpy()
        n_i, x_i = len(inside), int((~inside).sum())
        picp = float(inside.mean()) if n_i else math.nan
        mpiw = float((iv[args.upper] - iv[args.lower]).mean()) if n_i else math.nan
        lr_k, p_k = kupiec(x_i, n_i, 1 - args.level) if n_i else (math.nan, math.nan)
        lr_c, p_c, trans = christoffersen([(~inside)[ix] for ix in iv.reset_index(drop=True).groupby("_g").indices.values()])
        if n_i < args.min_n:
            kv = cv = UNVERIFIED
        else:
            kv = SURVIVES if p_k >= args.alpha else (KILLED if picp < args.level else WOUNDED)
            cv = UNVERIFIED if math.isnan(p_c) else (SURVIVES if p_c >= args.alpha else WOUNDED)
        cover_txt = (f"PICP {_f(picp)} vs nominal {args.level:g} ({x_i} misses in {n_i}); MPIW {_f(mpiw)}; "
                     f"Kupiec LR {_f(lr_k)}, p {_f(p_k)}")
        report.add(Check(id="BT-COVER", title="interval coverage matches the nominal level (Kupiec POF)", verdict=kv,
                         value=picp, criterion=(f"Kupiec p >= {args.alpha:g}; rejected with PICP < level KILLED, "
                                                f"> level WOUNDED; >= {args.min_n} intervals"), detail=cover_txt))
        report.add(Check(id="BT-INDEP", title="interval misses do not cluster (Christoffersen independence)",
                         verdict=cv, value=p_c, criterion=f"independence LR p >= {args.alpha:g}",
                         detail=(f"LR {_f(lr_c)}, p {_f(p_c)}; transitions 00/01/10/11 = "
                                 f"{int(trans[0, 0])}/{int(trans[0, 1])}/{int(trans[1, 0])}/{int(trans[1, 1])}")))
        report.data["intervals"] = {"n": n_i, "misses": x_i, "picp": picp, "mpiw": mpiw, "level": args.level,
                                    "kupiec_lr": lr_k, "kupiec_p": p_k, "christoffersen_lr": lr_c,
                                    "christoffersen_p": p_c}
        report.section("Intervals", cover_txt + f"; Christoffersen independence LR {_f(lr_c)}, p {_f(p_c)}.")
    if grouped:
        notes.append("panel: tests run on the per-period mean loss differential across groups (robust to common "
                     "shocks on a date); per-group skill in the Groups table")
    metrics = pd.DataFrame(rows)
    write_once(run_dir / "metrics.csv", metrics.to_csv(index=False, lineterminator="\n"))
    report.data.update({"benchmark": bdesc, "n_rows": len(y), "n_periods": T, "test": kind, "loss": args.loss,
                        "horizon": args.h, "notes": notes})
    report.section("Summary (trend first: skill, stability, then the test and its power)",
                   "\n".join(f"- {s}" for s in summary))
    report.section("Accuracy", _md(metrics))
    report.section("Windows (skill per contiguous sub-window)", _md(pd.DataFrame(win_rows)))
    if grp_rows:
        report.section("Groups (skill per series)", _md(pd.DataFrame(grp_rows)))
    report.section("Notes", "\n".join(f"- {n}" for n in notes))
    report.data = _json_safe(report.data)            # strict JSON: non-finite numbers become null
    for c in report.checks:
        c.value = _json_safe(c.value)


def _json_safe(o):
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, dict):
        return {k: _json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_safe(v) for v in o]
    return o


def _md(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(none)"
    cells = [[_f(v, 4) if isinstance(v, float) else ("" if v is None else str(v)) for v in r]
             for r in frame.itertuples(index=False)]
    return "\n".join(["| " + " | ".join(map(str, frame.columns)) + " |", "|" + "---|" * len(frame.columns)]
                     + ["| " + " | ".join(c) + " |" for c in cells])


if __name__ == "__main__":
    sys.exit(run_main(SCRIPT, main, build_parser()))
