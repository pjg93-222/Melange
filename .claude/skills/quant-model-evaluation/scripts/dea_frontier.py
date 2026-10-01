#!/usr/bin/env python3
"""Data envelopment analysis (DEA) with the checks the frontier literature asks for. Read-only: reads one
CSV (one row per unit, with input and output columns); writes only its run folder (report.md,
report.json, scores.csv).

What it computes
  * Radial efficiency from the envelopment LPs, solved with scipy.optimize.linprog (HiGHS):
      input orientation   min theta  s.t.  X'lam <= theta*x0,  Y'lam >= y0,      lam >= 0
      output orientation  max phi    s.t.  X'lam <= x0,        Y'lam >= phi*y0,  lam >= 0
    plus sum(lam) = 1 for variable returns to scale (VRS; Banker, Charnes & Cooper 1984); constant
    returns (CRS; Charnes, Cooper & Rhodes 1978) add nothing. Every score is on the Farrell (0, 1]
    scale: theta (input orientation) or 1/phi (output orientation).
  * CRS and VRS are both always solved: scale efficiency SE = eff_CRS / eff_VRS, and the returns-to-
    scale region (increasing / constant / decreasing) from a non-increasing-returns (NIRS) run.
  * A second LP per unit maximises the slack left at the radial optimum: a unit scored 1 that still
    has slack is only weakly efficient. Peers and lambdas come from that second LP.
  * --super: Andersen-Petersen (1993) super-efficiency (each unit leaves its own reference set), used
    for OUTLIER SCREENING, not ranking (Banker & Chang 2006). Under VRS the LP is infeasible for some
    extreme units; they are reported as "infeasible" and screened first. Then the influence check:
    drop the --influence-top most super-efficient units and re-score everyone else.
  * --bootstrap B: Simar-Wilson (1998) smoothed homogeneous bootstrap (bias, bias-corrected scores,
    confidence intervals). Use B >= 1000 (1999 recommended) for any interval you report; smaller B runs
    and is flagged, and B below 20 is refused. The variant implemented (steps in sw98_bootstrap()):
      - scale: the Farrell scores in (0, 1] (input theta; output 1/phi, the Shephard output distance),
        reflected about 1 as {eff, 2 - eff};
      - bandwidth: Silverman's rule of thumb h = 0.9 min(sd, IQR/1.34) n_h^(-1/5) on the reflected scores
        of the n_h units strictly inside the frontier (all units if fewer than 3), with no sd-ratio
        adjustment; --bandwidth overrides it;
      - draws: resampled from all 2n reflected scores, perturbed by h N(0, 1), variance-corrected by
        (1 + h^2/var)^(-1/2) and folded back below 1.
    It is NOT numerically identical to R Benchmarking::dea.boot, which reflects Shephard distances (>= 1)
    and adjusts the bandwidth differently (one 40-unit comparison, 2026-09-30: mean bias 0.058 here vs
    0.050, median 95% interval width 0.096 vs 0.081). Both variants appear in the literature; name this one
    when you quote its numbers.
  * Cost: every model solves n LPs with n + 1 variables (stacked 50 units per HiGHS call), so time grows
    about as n^2 (m + s). Measured on a laptop with 2 inputs and 2 outputs: --super at n = 100 / 400 / 800
    about 2 / 5 / 16 s; each bootstrap replication costs one extra model (about 0.05 s at n = 100), so
    B = 1999 at n = 100 takes a few minutes and grows as n^2 beyond that.

STANDING WARNING: do not regress these scores on explanatory variables with OLS or Tobit. DEA scores
are biased, correlated with each other through the estimated frontier, and not censored data, so naive
second stages are invalid (Simar & Wilson 2007). Use their truncated-regression bootstrap
(Algorithms 1-2) or conditional frontiers, and only where the separability condition is credible.

Usage:
  python scripts/dea_frontier.py --data units.csv --inputs staff,spend --outputs wins [--id name]
      [--rts crs|vrs] [--orientation input|output] [--super] [--bootstrap 1999] [--alpha 0.05]
  Recommended audit run: add --super --bootstrap 1999 (>= 1000).

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
"""
from __future__ import annotations

import csv
import io
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (Check, Report, UsageError, base_parser, run_main, require_file,  # noqa: E402
                     write_once, emit, SURVIVES, WOUNDED, UNVERIFIED)

import numpy as np  # noqa: E402  (no pandas: the csv module keeps start-up fast)
from scipy import sparse  # noqa: E402
from scipy.optimize import linprog  # noqa: E402

SCRIPT = "dea_frontier"
SRC = f"quant-model-evaluation/{SCRIPT}"
CHUNK = 50  # units per stacked HiGHS call (bounds memory; results do not depend on it)
SECOND_STAGE_WARNING = (
    "Do not regress these DEA scores on explanatory variables with OLS or Tobit. The scores are biased "
    "and correlated with each other through the estimated frontier, and they are not censored data, so "
    "naive second-stage regressions are invalid (Simar & Wilson 2007, J. Econometrics 136(1):31-64, "
    "doi:10.1016/j.jeconom.2005.07.009). Use the Simar-Wilson truncated-regression bootstrap "
    "(Algorithms 1-2) or conditional frontiers (Daraio & Simar 2005), and only where separability is credible.")


def build_parser():
    p = base_parser(__doc__)
    p.add_argument("--data", required=True, help="CSV with one row per unit (decision-making unit)")
    p.add_argument("--inputs", required=True, help="comma-separated input columns (non-negative numbers)")
    p.add_argument("--outputs", required=True, help="comma-separated output columns (non-negative numbers)")
    p.add_argument("--id", help="unit id column (default: row1, row2, ...)")
    p.add_argument("--rts", choices=["crs", "vrs"], default="vrs",
                   help="returns to scale of the reported score (default vrs); both are always solved")
    p.add_argument("--orientation", choices=["input", "output"], default="input", help="default input")
    p.add_argument("--super", action="store_true",
                   help="Andersen-Petersen super-efficiency outlier screen plus the influence check")
    p.add_argument("--bootstrap", type=int, default=0, metavar="B",
                   help="Simar-Wilson (1998) smoothed bootstrap with B replications: >= 1000 (1999 recommended) for "
                        "reported intervals; 0 = off; values below 20 are refused")
    p.add_argument("--alpha", type=float, default=0.05, help="1 - confidence level of bootstrap intervals")
    p.add_argument("--bandwidth", type=float, default=None,
                   help="kernel bandwidth for the bootstrap (default: Silverman rule on reflected scores)")
    p.add_argument("--influence-top", type=int, default=1,
                   help="with --super: how many of the most super-efficient units to drop (default 1)")
    p.add_argument("--influence-tol", type=float, default=0.05,
                   help="a score 'changes' when it moves by more than this (default 0.05)")
    p.add_argument("--influence-max-share", type=float, default=0.10,
                   help="SURVIVES if at most this share of the other units change (default 0.10)")
    p.add_argument("--max-ci-width", type=float, default=0.10,
                   help="bootstrap check SURVIVES if the median interval width is at most this (default 0.10)")
    p.add_argument("--max-frontier-share", type=float, default=0.5,
                   help="dimensionality check also fails if more than this share of units score 1 (default 0.5)")
    p.add_argument("--eff-tol", type=float, default=1e-6, help="a score >= 1 - eff-tol counts as 1")
    p.add_argument("--slack-tol", type=float, default=1e-6,
                   help="a unit scored 1 is weakly efficient when its slack, summed in units of each column's mean, "
                        "exceeds this (default 1e-6)")
    return p


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #
def _cols(text: str, flag: str) -> list[str]:
    cols = [c.strip() for c in str(text).split(",") if c.strip()]
    if not cols:
        raise UsageError(f"{flag} needs at least one column name")
    if len(set(cols)) != len(cols):
        raise UsageError(f"{flag} repeats a column: {cols}")
    return cols


def _num(cell):
    try:
        return float(cell)
    except ValueError:
        return math.nan


def load_units(args):
    src = require_file(args.data, "--data")
    try:
        with open(src, encoding="utf-8-sig", newline="") as fh:
            rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise UsageError(f"cannot read --data as CSV: {exc}") from None
    if len(rows) < 2:
        raise UsageError("--data has no rows")
    header, body = [h.strip() for h in rows[0]], rows[1:]
    ins, outs = _cols(args.inputs, "--inputs"), _cols(args.outputs, "--outputs")
    if set(ins) & set(outs):
        raise UsageError(f"a column cannot be both input and output: {sorted(set(ins) & set(outs))}")
    missing = [c for c in ins + outs + ([args.id] if args.id else []) if c not in header]
    if missing:
        raise UsageError(f"columns not in --data: {missing}; available: {header}")
    pos = [header.index(c) for c in ins + outs]
    arr = np.array([[_num(r[j].strip()) if j < len(r) else math.nan for j in pos] for r in body])
    bad = np.flatnonzero(~np.isfinite(arr).all(axis=1))
    if bad.size:
        raise UsageError(f"missing or non-numeric input/output values on data rows {(bad + 1).tolist()[:5]} "
                         "(1-based, header excluded)")
    if (arr < 0).any():
        raise UsageError("DEA needs non-negative inputs and outputs; transform or drop negative values first")
    X, Y = arr[:, :len(ins)], arr[:, len(ins):]
    if (X.max(axis=1) <= 0).any() or (Y.max(axis=1) <= 0).any():
        raise UsageError("every unit needs at least one positive input and one positive output")
    j = header.index(args.id) if args.id else None
    ids = [r[j].strip() if j < len(r) else "" for r in body] if args.id else [f"row{i + 1}" for i in range(len(body))]
    if len(set(ids)) != len(ids):
        raise UsageError(f"--id column {args.id!r} has duplicate values")
    if len(ids) < 2:
        raise UsageError("DEA needs at least 2 units")
    return src, ids, ins, outs, X, Y


def _check_args(args, n: int) -> None:
    if not 0 < args.alpha < 1:
        raise UsageError("--alpha must be in (0, 1)")
    if args.bootstrap < 0 or 0 < args.bootstrap < 20:
        raise UsageError("--bootstrap must be 0 (off) or at least 20")
    if args.bandwidth is not None and not args.bandwidth > 0:
        raise UsageError("--bandwidth must be positive")
    if args.super and not 1 <= args.influence_top <= n - 2:
        raise UsageError(f"--influence-top must be between 1 and n-2 = {n - 2}")
    if not (args.influence_tol > 0 and 0 <= args.influence_max_share <= 1 and args.max_ci_width > 0
            and 0 <= args.max_frontier_share <= 1 and 0 < args.eff_tol < 0.01 and args.slack_tol >= 0):
        raise UsageError("thresholds out of range: need influence-tol > 0, max-ci-width > 0, shares in "
                         "[0, 1], 0 < eff-tol < 0.01, slack-tol >= 0")


# --------------------------------------------------------------------------- #
# Linear programs
# --------------------------------------------------------------------------- #
def _block(Xr, Yr, x0, y0, rts, orient, excl):
    """Dense pieces of one envelopment LP. Variables: [score, lam_1 .. lam_r]."""
    m, s, r = Xr.shape[1], Yr.shape[1], Xr.shape[0]
    if orient == "input":  # min theta:  X'lam - theta*x0 <= 0 ;  -Y'lam <= -y0
        a = np.vstack([np.hstack([-x0[:, None], Xr.T]), np.hstack([np.zeros((s, 1)), -Yr.T])])
        b, c = np.r_[np.zeros(m), -y0], np.r_[1.0, np.zeros(r)]
    else:                  # max phi:  X'lam <= x0 ;  phi*y0 - Y'lam <= 0
        a = np.vstack([np.hstack([np.zeros((m, 1)), Xr.T]), np.hstack([y0[:, None], -Yr.T])])
        b, c = np.r_[x0, np.zeros(s)], np.r_[-1.0, np.zeros(r)]
    ones = np.r_[0.0, np.ones(r)][None, :]
    if rts == "nirs":      # non-increasing returns: sum(lam) <= 1
        a, b = np.vstack([a, ones]), np.r_[b, 1.0]
    aeq, beq = (ones, np.array([1.0])) if rts == "vrs" else (np.zeros((0, r + 1)), np.zeros(0))
    bounds = np.column_stack([np.zeros(r + 1), np.full(r + 1, np.inf)])
    if excl >= 0:          # Andersen-Petersen: the unit may not reference itself
        bounds[1 + excl, 1] = 0.0
    return c, a, b, aeq, beq, bounds


def _solve(pieces):
    """Solve one LP, or several independent LPs stacked block-diagonally, with HiGHS."""
    def stack(i):
        mats = [p[i] for p in pieces]
        if all(mt.shape[0] == 0 for mt in mats):
            return None
        return sparse.block_diag([sparse.coo_array(mt) for mt in mats], format="csr")
    a_ub, a_eq = stack(1), stack(3)
    return linprog(np.concatenate([p[0] for p in pieces]),
                   A_ub=a_ub, b_ub=np.concatenate([p[2] for p in pieces]) if a_ub is not None else None,
                   A_eq=a_eq, b_eq=np.concatenate([p[4] for p in pieces]) if a_eq is not None else None,
                   bounds=np.vstack([p[5] for p in pieces]), method="highs")


def envelopment(Xr, Yr, X0, Y0, rts, orient, exclude=None):
    """Radial score of every evaluated unit (rows of X0/Y0) against the reference units (Xr/Yr).

    The per-unit LPs are independent, so up to CHUNK of them are stacked block-diagonally per HiGHS call
    (the joint optimum is the collection of per-unit optima); chunking caps each call at CHUNK x (r+1)
    variables. If a joint LP is not optimal, typically because a VRS super-efficiency block is infeasible,
    each unit of that chunk is re-solved alone for its own status.
    Returns (score, lam, status): theta (input) or phi (output), NaN where not optimal; lambdas (k x r);
    linprog status per unit (0 optimal, 2 infeasible)."""
    k, r = X0.shape[0], Xr.shape[0]
    excl = np.full(k, -1) if exclude is None else np.asarray(exclude)
    score, lam, status = np.full(k, np.nan), np.zeros((k, r)), np.full(k, -1)
    for start in range(0, k, CHUNK):
        units = range(start, min(k, start + CHUNK))
        pieces = [_block(Xr, Yr, X0[o], Y0[o], rts, orient, int(excl[o])) for o in units]
        res = _solve(pieces)
        if res.status == 0:
            z = res.x.reshape(len(pieces), r + 1)
            score[units.start:units.stop], lam[units.start:units.stop] = z[:, 0], z[:, 1:]
            status[units.start:units.stop] = 0
            continue
        for o, piece in zip(units, pieces):
            res = _solve([piece])
            status[o] = res.status
            if res.status == 0:
                score[o], lam[o] = res.x[0], res.x[1:]
    return score, lam, status


def farrell(score, orient):
    """LP optimum -> Farrell (0, 1] scale (input theta; output 1/phi). phi <= 0 -> inf (no reference)."""
    if orient == "input":
        return np.asarray(score, dtype=float).copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(score > 1e-12, 1.0 / score, np.inf)
    return np.where(np.isnan(score), np.nan, out)


def max_slacks(X, Y, score, rts, orient):
    """Second phase at the radial optimum: maximise leftover input and output slack, each weighted by
    1/column mean so the objective is unit-free. Returns (lam, sx, sy, weighted slack sum, ok)."""
    n, m, s = X.shape[0], X.shape[1], Y.shape[1]
    wx, wy = 1.0 / np.maximum(X.mean(0), 1e-300), 1.0 / np.maximum(Y.mean(0), 1e-300)
    eq = np.vstack([np.hstack([X.T, np.eye(m), np.zeros((m, s))]),
                    np.hstack([Y.T, np.zeros((s, m)), -np.eye(s)])])
    if rts == "vrs":
        eq = np.vstack([eq, np.r_[np.ones(n), np.zeros(m + s)]])
    c = np.r_[np.zeros(n), -wx, -wy]
    bounds = np.column_stack([np.zeros(n + m + s), np.full(n + m + s, np.inf)])

    def piece(o, relax=0.0):
        if orient == "input":   # X'lam + sx = theta*x0 ; Y'lam - sy = y0
            rhs = np.r_[score[o] * X[o] * (1 + relax), Y[o]]
        else:                   # X'lam + sx = x0 ; Y'lam - sy = phi*y0
            rhs = np.r_[X[o], score[o] * Y[o] * (1 - relax)]
        if rts == "vrs":
            rhs = np.r_[rhs, 1.0]
        return c, np.zeros((0, n + m + s)), np.zeros(0), eq, rhs, bounds

    sol, ok = np.full((n, n + m + s), np.nan), np.zeros(n, dtype=bool)
    for start in range(0, n, CHUNK):
        units = range(start, min(n, start + CHUNK))
        res = _solve([piece(o) for o in units])
        if res.status == 0:
            sol[units.start:units.stop], ok[units.start:units.stop] = res.x.reshape(len(units), n + m + s), True
            continue
        for o in units:  # re-solve alone; relax the fixed score by 1e-9 if round-off made the equality infeasible
            for relax in (0.0, 1e-9):
                res = _solve([piece(o, relax)])
                if res.status == 0:
                    sol[o], ok[o] = res.x, True
                    break
    lam, sx, sy = sol[:, :n], sol[:, n:n + m], sol[:, n + m:]
    return lam, sx, sy, sx @ wx + sy @ wy, ok


def super_efficiency(X, Y, rts, orient):
    """Andersen & Petersen (1993): score each unit against all the others. inf = infeasible (no
    combination of the other units reaches it: an extreme unit, common under VRS)."""
    sc, _, status = envelopment(X, Y, X, Y, rts, orient, exclude=np.arange(X.shape[0]))
    sup = farrell(sc, orient)
    sup[status == 2] = np.inf
    return sup


def _sw98_draw(refl, var_r, h, n, rng, floor):
    """Steps 4a-4d of one replication: n smoothed pseudo-efficiencies from the reflected scores `refl`.
    Returns (pre-fold draws, folded draws). The pre-fold draws are symmetric about 1 (reflection) and keep
    the variance of `refl` (variance correction); the folded draws lie in (0, 1]."""
    beta = rng.choice(refl, size=n, replace=True)                                     # 4a
    pert = beta + h * rng.standard_normal(n)                                          # 4b
    smooth = beta.mean() + (pert - beta.mean()) / math.sqrt(1.0 + h * h / var_r)     # 4c
    return smooth, np.maximum(np.where(smooth <= 1.0, smooth, 2.0 - smooth), floor)  # 4d


def sw98_bootstrap(X, Y, eff, rts, orient, B, alpha, rng, h, tol, tick=None):
    """Simar & Wilson (1998) smoothed homogeneous bootstrap on the Farrell (0, 1] scale.

    Variant implemented (state it with any number it produces): reflection of the Farrell scores
    (input theta, output 1/phi = Shephard output distance) about 1, and the bandwidth rule of step 3 with no
    sd-ratio adjustment. R Benchmarking::dea.boot reflects Shephard distances (>= 1) and adjusts the
    bandwidth differently, so the two differ numerically (one 40-unit comparison, 2026-09-30: mean bias
    0.058 here vs 0.050, median 95% interval width 0.096 vs 0.081). Both variants appear in the literature.

    Algorithm (SW98 sections 3-4; restated in Simar & Wilson 2000, "A general methodology for bootstrapping in
    non-parametric frontier models", J. Applied Statistics 27(6):779-802):
      1. eff_i: DEA estimate of every unit (input theta or output 1/phi), all in (0, 1].
      2. Reflection (Silverman 1986): R = {eff_i} U {2 - eff_i}, 2n values symmetric about 1, so the kernel
         estimate of the score density has no boundary bias at 1.
      3. Bandwidth h: Silverman's rule of thumb 0.9 * min(sd, IQR/1.34) * n_h^(-1/5) on the reflected scores
         of the n_h units strictly inside the frontier (all units when fewer than 3 are inside). Frontier
         units are left out of this step only: their point mass at 1 would shrink the IQR, and so h,
         towards zero. --bandwidth overrides.
      4. For b = 1..B (steps a-d in _sw98_draw):
         a. draw beta*_1..beta*_n with replacement from R;
         b. perturb: beta** = beta* + h * eps, eps ~ N(0, 1);
         c. variance correction, so the draws keep var(R) rather than var(R) + h^2:
            theta~ = mean(beta*) + (beta** - mean(beta*)) / sqrt(1 + h^2 / var(R));
         d. fold back into the support: theta* = theta~ if theta~ <= 1 else 2 - theta~;
         e. pseudo-data on each unit's own frontier ray, with efficiency theta*_i:
              input:  x*_i = x_i * eff_i / theta*_i (outputs kept);  output: y*_i = y_i * theta*_i / eff_i;
         f. eff*_ib: the ORIGINAL unit (x_i, y_i) scored against the pseudo-sample frontier.
      5. bias_i = mean_b(eff*_ib) - eff_i;  bias-corrected score eff_bc_i = eff_i - bias_i.
      6. Interval: q_lo, q_hi = alpha/2 and 1 - alpha/2 quantiles of (eff*_ib - eff_i); the (1 - alpha)
         interval for the true score is [eff_i - q_hi, eff_i - q_lo] (SW98 percentile form).
    The pseudo-frontier lies inside the estimated one, so eff*_ib >= eff_i: bias >= 0 (DEA overstates
    efficiency) and the interval usually sits below eff_i. The correction adds variance; use eff_bc only
    when |bias| > sd/sqrt(3) (a rule of thumb; attribution UNVERIFIED). Returns None when every unit scores
    1 (no spread to smooth)."""
    n = eff.size
    refl = np.r_[eff, 2.0 - eff]
    var_r = refl.var(ddof=1)
    if not np.isfinite(var_r) or var_r <= 1e-14:
        return None
    if h is None:
        inner = eff[eff < 1.0 - tol]
        base = inner if inner.size >= 3 else eff
        rb = np.r_[base, 2.0 - base]
        q75, q25 = np.percentile(rb, [75, 25])
        spread = min(rb.std(ddof=1), (q75 - q25) / 1.34)
        h = 0.9 * (spread if spread > 0 else rb.std(ddof=1)) * base.size ** -0.2
    floor = 1e-3 * eff.min()                                   # keeps pseudo-data positive in far tails
    boot = np.full((B, n), np.nan)
    for b in range(B):
        _, star = _sw98_draw(refl, var_r, h, n, rng, floor)                  # 4a-4d
        if orient == "input":                                                # 4e
            xs, ys = X * (eff / star)[:, None], Y
        else:
            xs, ys = X, Y * (star / eff)[:, None]
        sc, _, _ = envelopment(xs, ys, X, Y, rts, orient)                    # 4f
        boot[b] = farrell(sc, orient)
        if tick:
            tick(b + 1, B)
    boot[~np.isfinite(boot)] = np.nan
    bias = np.nanmean(boot, axis=0) - eff                                    # 5
    sd = np.nanstd(boot, axis=0, ddof=1)
    diff = boot - eff
    q_lo, q_hi = np.nanquantile(diff, alpha / 2, axis=0), np.nanquantile(diff, 1 - alpha / 2, axis=0)
    return {"h": float(h), "bias": bias, "eff_bc": eff - bias, "ci_low": eff - q_hi, "ci_high": eff - q_lo,
            "sd": sd, "bc_advisable": np.abs(bias) > sd / math.sqrt(3),
            "failed_share": float(np.isnan(boot).mean())}


# --------------------------------------------------------------------------- #
# Report helpers
# --------------------------------------------------------------------------- #
def _peers(lam_row, ids):
    idx = [j for j in np.argsort(-lam_row) if lam_row[j] > 1e-6]
    return ";".join(f"{ids[j]}:{lam_row[j]:.4g}" for j in idx)


def _clean(v):
    if isinstance(v, (float, np.floating)):
        return float(v) if math.isfinite(v) else None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def _md(table: dict, cols: list[str], order=None, max_rows: int = 40) -> str:
    """Markdown rows of the column table (dict name -> sequence), in `order` or file order."""
    idx = list(range(len(table["id"]))) if order is None else list(order)
    shown = idx if len(idx) <= max_rows else idx[:max_rows // 2] + idx[-(max_rows // 2):]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for i in shown:
        cells = [f"{v:.4g}" if isinstance(v, (float, np.floating)) else str(v) for v in (table[c][i] for c in cols)]
        lines.append("| " + " | ".join(cells) + " |")
    if len(idx) > max_rows:
        lines.append(f"\n({len(idx) - max_rows} middle rows omitted; full table in scores.csv)")
    return "\n".join(lines)


def _csv_text(table: dict) -> str:
    def fmt(v):
        if isinstance(v, (bool, np.bool_)):
            return "True" if v else "False"
        if isinstance(v, (float, np.floating)):
            return "" if math.isnan(v) else repr(float(v))  # repr gives 'inf' and exact round-trips
        return str(v)
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(list(table))
    writer.writerows([fmt(col[i]) for col in table.values()] for i in range(len(table["id"])))
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    src, ids, ins, outs, X, Y = load_units(args)
    report.add_input(src)
    report.note_packages(["numpy", "scipy"])
    n, m, s = X.shape[0], X.shape[1], Y.shape[1]
    _check_args(args, n)
    orient, rts, tol = args.orientation, args.rts, args.eff_tol

    emit("stage", "running", f"envelopment LPs for {n} units (CRS, VRS, NIRS)", run_id=run_id, source=SRC)
    raw = {}
    for model in ("crs", "vrs", "nirs"):
        sc, lam, status = envelopment(X, Y, X, Y, model, orient)
        if (status != 0).any():  # cannot happen for validated data: lam = own unit is always feasible
            raise RuntimeError(f"{model.upper()} LP not solved for units "
                               f"{[ids[i] for i in np.flatnonzero(status != 0)][:5]}")
        raw[model] = (sc, lam)
    eff = {k: farrell(v[0], orient) for k, v in raw.items()}
    e = eff[rts]
    scale = eff["crs"] / eff["vrs"]
    region = np.where(np.abs(scale - 1) <= tol, "constant",
                      np.where(np.abs(eff["nirs"] - eff["vrs"]) <= tol, "decreasing", "increasing"))
    lam2, sx, sy, wslack, ok2 = max_slacks(X, Y, raw[rts][0], rts, orient)
    lam_use = np.where(ok2[:, None], lam2, raw[rts][1])
    frontier = e >= 1 - tol
    weak = frontier & ok2 & (wslack > args.slack_tol)

    table = {"id": ids, "eff": e, "eff_crs": eff["crs"], "eff_vrs": eff["vrs"], "scale_eff": scale,
             "rts_region": region.tolist(), "weakly_efficient": weak.tolist()}
    for j, col in enumerate(ins):
        table[f"slack_{col}"] = np.where(ok2, sx[:, j], np.nan)
    for j, col in enumerate(outs):
        table[f"slack_{col}"] = np.where(ok2, sy[:, j], np.nan)
    table["peers"] = [_peers(lam_use[o], ids) for o in range(n)]

    # Dimensionality and discrimination --------------------------------------------------------
    rule = max(m * s, 3 * (m + s))
    share = float(frontier.mean())
    ok_dim = n >= rule and share <= args.max_frontier_share
    report.add(Check(
        id="DEA-DIM", title="Enough units for the number of inputs and outputs", verdict=SURVIVES if ok_dim else WOUNDED,
        criterion=f"n >= max(m*s, 3(m+s)) = {rule} and frontier share <= {args.max_frontier_share:g}",
        value=f"n={n}, m={m}, s={s}, frontier share={share:.2f}",
        detail=(f"{int(frontier.sum())} of {n} units score 1 ({rts.upper()}, {orient} orientation). Count rules are "
                f"minimums (Cooper, Seiford & Tone 2007). VRS-DEA converges at n^(-2/(m+s+1)) (Kneip, Park & Simar "
                f"1998), roughly the rate a root-n estimator reaches with {n ** (4 / (m + s + 1)):.0f} units. "
                + ("" if ok_dim else "Scores discriminate poorly: cut inputs/outputs or add units."))))
    weak_ids = [ids[i] for i in np.flatnonzero(weak)]

    # Super-efficiency and influence -------------------------------------------------------------
    influence = None
    if args.super:
        emit("stage", "running", "super-efficiency and influence screen", run_id=run_id, source=SRC)
        sup = super_efficiency(X, Y, rts, orient)
        table["super_eff"] = sup
        table["super_status"] = ["infeasible" if np.isinf(v) else "optimal" for v in sup]
        order = np.argsort(-np.where(np.isnan(sup), -np.inf, sup), kind="stable")
        top, keep = order[:args.influence_top], np.sort(order[args.influence_top:])
        sc_red, _, st_red = envelopment(X[keep], Y[keep], X[keep], Y[keep], rts, orient)
        if (st_red != 0).any():  # cannot happen: every remaining unit can reference itself (CR-32)
            raise RuntimeError(f"influence re-scoring LP not solved for units "
                               f"{[ids[keep[i]] for i in np.flatnonzero(st_red != 0)][:5]}")
        delta = np.abs(farrell(sc_red, orient) - e[keep])
        changed = delta > args.influence_tol
        ch_share = float(changed.mean())
        worst = int(np.nanargmax(delta))
        influence = {"removed": [ids[i] for i in top], "removed_super_eff": [_clean(sup[i]) for i in top],
                     "changed_share": ch_share, "changed": [ids[keep[i]] for i in np.flatnonzero(changed)],
                     "max_change": _clean(delta[worst]), "max_change_unit": ids[keep[worst]]}
        report.add(Check(
            id="DEA-INFLUENCE", title="Scores robust to dropping the most super-efficient unit(s)",
            verdict=SURVIVES if ch_share <= args.influence_max_share else WOUNDED,
            criterion=(f"share of remaining units whose score moves > {args.influence_tol:g} after dropping the top "
                       f"{args.influence_top} super-efficient unit(s) <= {args.influence_max_share:g}"),
            value=round(ch_share, 4),
            detail=(f"dropped {', '.join(f'{ids[i]} (super-eff {sup[i]:.3g})' for i in top)}; {int(changed.sum())} of "
                    f"{keep.size} units moved; largest move {delta[worst]:.3f} ({ids[keep[worst]]}). "
                    f"{int(np.isinf(sup).sum())} unit(s) have infeasible super-efficiency (extreme units). "
                    "A frontier set by one or two units makes every score hostage to their data: verify those rows. "
                    "Super-efficiency screens outliers; it is not a ranking (Banker & Chang 2006).")))

    # Simar-Wilson bootstrap ----------------------------------------------------------------------
    boot = None
    if args.bootstrap:
        B = args.bootstrap
        step = max(1, B // 10)

        def tick(b, total):
            if b % step == 0 or b == total:
                emit("stage", "running", f"Simar-Wilson bootstrap {b}/{total}", run_id=run_id, source=SRC,
                     current=b, total=total)

        boot = sw98_bootstrap(X, Y, e, rts, orient, B, args.alpha, np.random.default_rng(args.seed),
                              args.bandwidth, tol, tick)
        if boot is None:
            report.add(Check(id="DEA-BOOT-CI", title="Bootstrap intervals narrow enough to rank units",
                             verdict=UNVERIFIED, criterion=f"median interval width <= {args.max_ci_width:g}",
                             detail="every unit scores 1: no spread of scores to smooth, bootstrap not run"))
        else:
            for key in ("bias", "eff_bc", "ci_low", "ci_high"):
                table[key] = boot[key]
            table["boot_sd"], table["bc_advisable"] = boot["sd"], boot["bc_advisable"].tolist()
            width = boot["ci_high"] - boot["ci_low"]
            med = float(np.nanmedian(width))
            failed = boot["failed_share"]
            note = "" if B >= 1000 else f" B = {B} is low for interval endpoints; use >= 1000 (1999 recommended)."
            report.add(Check(
                id="DEA-BOOT-CI", title="Bootstrap intervals narrow enough to rank units",
                verdict=UNVERIFIED if failed > 0 else (SURVIVES if med <= args.max_ci_width else WOUNDED),
                criterion=(f"median {100 * (1 - args.alpha):g}% interval width <= {args.max_ci_width:g}, with every "
                           "bootstrap LP solved"),
                value=round(med, 4),
                detail=((f"{failed:.1%} of the bootstrap LPs failed, so the intervals rest on an incomplete "
                         "resample: not judged; " if failed > 0 else "")
                        + f"widest interval {np.nanmax(width):.3f}; median bias {np.nanmedian(boot['bias']):.3f}; "
                        f"{int(np.sum(boot['bc_advisable']))} of {n} units have |bias| > sd/sqrt(3) (bias correction "
                        f"worth its variance); h = {boot['h']:.4g}, B = {B}. "
                        "Intervals sit below the DEA score because DEA overstates efficiency in finite samples."
                        + note)))

    for col, vals in table.items():  # strip LP round-off (1.0000000000000002, -0.0) before ranking and writing
        if isinstance(vals, np.ndarray) and vals.dtype.kind == "f":
            table[col] = np.round(vals, 10) + 0.0
    table["rank"] = [1 + int(np.sum(table["eff"] > v)) for v in table["eff"]]  # 1 = best, ties share a rank
    write_once(run_dir / "scores.csv", _csv_text(table))

    # Sections and machine-readable data ----------------------------------------------------------
    show = ["id", "eff", "eff_crs", "eff_vrs", "scale_eff", "rts_region", "peers"]
    report.section(f"Scores ({rts.upper()}, {orient} orientation, Farrell scale 0-1)", _md(table, show)
                   + (f"\n\nWeakly efficient (score 1 but slack left): {', '.join(weak_ids)}" if weak_ids else ""))
    if args.super:
        ranked = sorted(range(n), key=lambda i: -np.nan_to_num(table["super_eff"][i], nan=-np.inf))[:10]
        report.section("Super-efficiency outlier screen (Andersen & Petersen 1993)",
                       _md(table, ["id", "eff", "super_eff", "super_status"], order=ranked))
    if boot is not None:
        report.section(f"Simar-Wilson (1998) bootstrap: B = {args.bootstrap}, h = {boot['h']:.4g}, "
                       f"alpha = {args.alpha:g}", _md(table, ["id", "eff", "bias", "eff_bc", "ci_low", "ci_high",
                                                              "bc_advisable"]))
    report.section("Second-stage warning", SECOND_STAGE_WARNING)
    report.section("Method", (
        "Envelopment LPs (Charnes, Cooper & Rhodes 1978; Banker, Charnes & Cooper 1984) solved with "
        "scipy.optimize.linprog/HiGHS; second-phase max-slack LP for peers and weak efficiency; scale efficiency "
        "= eff_CRS/eff_VRS with the region from a NIRS run. Output-orientation scores are 1/phi. "
        "Rules of thumb for n are minimums; prefer bootstrap interval width as the precision evidence."
        + ("" if boot is None else
           " Bootstrap variant: Simar-Wilson (1998) smoothed homogeneous bootstrap with the Farrell (0, 1] scores "
           "reflected about 1; bandwidth = Silverman's rule 0.9 min(sd, IQR/1.34) n_h^(-1/5) on the reflected "
           "scores of the n_h units inside the frontier, no sd-ratio adjustment"
           + (" (overridden by --bandwidth)" if args.bandwidth is not None else "")
           + "; draws resampled from the reflected set, variance-corrected by (1 + h^2/var)^(-1/2) and folded "
           "below 1; percentile intervals [eff - q_hi, eff - q_lo]. Not numerically identical to R "
           "Benchmarking::dea.boot (Shephard-scale reflection, different bandwidth adjustment): quote the variant "
           "with the numbers.")))
    report.data.update({
        "settings": {"rts": rts, "orientation": orient, "inputs": ins, "outputs": outs, "n": n,
                     "super": bool(args.super), "bootstrap": args.bootstrap, "alpha": args.alpha},
        "dimensionality": {"n": n, "m": m, "s": s, "rule": rule, "frontier_share": share},
        "weakly_efficient": weak_ids,
        "influence": influence,
        "bootstrap": None if boot is None else {"h": boot["h"], "failed_share": boot["failed_share"]},
        "scores": [{k: _clean(col[i]) for k, col in table.items()} for i in range(n)],
        "warnings": [SECOND_STAGE_WARNING],
    })


if __name__ == "__main__":
    sys.exit(run_main(SCRIPT, main, build_parser()))
