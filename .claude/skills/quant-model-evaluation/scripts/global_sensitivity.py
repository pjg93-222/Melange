#!/usr/bin/env python3
"""Global sensitivity analysis in two steps; this script NEVER runs your model. Read-only: reads a problem
JSON and, for analysis, the design CSV plus your model's outputs CSV; writes only its run folder.

  1. design    --problem p.json --method sobol|morris|oat --design-only [--N N]   -> design.csv
  2. you run YOUR model once per design row (keep the run_id column, or the row order)
  3. analysis  --problem p.json --method <same> --design design.csv --outputs outputs.csv [--output-col y]

Methods
  sobol   Saltelli et al. (2010) scheme on a scrambled Sobol' sequence (scipy.stats.qmc): N*(d+2) runs laid out
          in SALib's block order (A, AB_1..AB_d, B). First-order S1 (Saltelli et al. 2010 estimator) and
          total-order ST (Jansen 1999 estimator), bootstrap confidence half-widths. Keep N a power of 2.
  morris  Elementary effects on N trajectories of a p-level grid (Morris 1991): mu* (Campolongo et al.
          2007), mu, sigma; screening, N*(d+1) runs. Needs uniform parameters.
  oat     One-at-a-time tornado: each parameter to its low and high value with the others at nominal
          (2d+1 runs). Quick screening only: blind to interactions (Saltelli & Annoni 2010).

Engine: SALib's analyzers when SALib is installed, with the numpy estimators run as a second computation
path that must agree; numpy alone otherwise. The report says which ran.

Problem JSON: {"names": [...], "bounds": [[lo, hi], ...], "dists": [...], "status": [...], "nominal": [...]}
  or {"parameters": [{"name", "bounds", "dist", "status", "nominal"}, ...]}. dists: unif [lo, hi] (default),
  norm [mean, sd], lognorm [meanlog, sdlog], triang [lo, hi, mode]. status: ratified | literature | fitted |
  arbitrary (the model card's constant classes). oat uses the 5%/95% quantiles of non-uniform parameters.

Verdicts per parameter, on importance = ST (sobol), mu*/sum(mu*) (morris) or swing share (oat):
  importance > --st-threshold and status in --uncalibrated-status -> WOUNDED "decision-relevant
  uncalibrated parameter"; influential but no status given, or importance not computable -> UNVERIFIED-HERE;
  otherwise SURVIVES. Also: sobol precision (--max-conf) and consistency (--max-sum-s1), SALib/numpy
  agreement (--path-tol), Morris trajectory count (--min-trajectories), OAT non-monotone responses. A constant
  output, or (sobol) a zero variance on the A and B rows, gives GSA-VAR UNVERIFIED-HERE: no index exists.
Design mode adds GSA-DESIGN: the design is regenerated from the same --seed and must be byte-identical.
Problem keys outside the format are listed as ignored (a dependent parameter belongs inside the model).

Usage:
  python scripts/global_sensitivity.py --problem p.json --method sobol --design-only --N 1024
  python scripts/global_sensitivity.py --problem p.json --method sobol --design design.csv --outputs out.csv

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (Check, Report, UsageError, base_parser, run_main, require_file, write_once,  # noqa: E402
                     emit, optional_import, pkg_version, SURVIVES, WOUNDED, UNVERIFIED)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from scipy.stats import qmc  # noqa: E402

SCRIPT = "global_sensitivity"
SRC = f"quant-model-evaluation/{SCRIPT}"
STATUSES = ("ratified", "literature", "fitted", "arbitrary")
ARITY = {"unif": 2, "norm": 2, "lognorm": 2, "triang": 3}
PARAM_KEYS = {"name", "bounds", "dist", "status", "nominal"}
LIST_KEYS = {"names", "bounds", "dists", "status", "nominal"}


def build_parser():
    p = base_parser(__doc__)
    p.add_argument("--problem", required=True, help="problem JSON (names, bounds, optional dists/status/nominal)")
    p.add_argument("--method", required=True, choices=["sobol", "morris", "oat"])
    p.add_argument("--design-only", action="store_true", help="write design.csv and stop (step 1)")
    p.add_argument("--N", type=int, default=None,
                   help="sobol: base sample size (default 1024); morris: trajectories (default 20)")
    p.add_argument("--levels", type=int, default=4, help="morris grid levels p, even (default 4)")
    p.add_argument("--design", help="design.csv from step 1 (analysis mode)")
    p.add_argument("--outputs", help="CSV with your model's output per design row (analysis mode)")
    p.add_argument("--output-col", help="output column (default: the only numeric column besides run_id)")
    p.add_argument("--boot", type=int, default=500, help="bootstrap resamples for confidence (default 500)")
    p.add_argument("--conf", type=float, default=0.95, help="confidence level (default 0.95)")
    p.add_argument("--st-threshold", type=float, default=0.1,
                   help="importance above this is decision-relevant (default 0.1)")
    p.add_argument("--uncalibrated-status", default="arbitrary,literature",
                   help="statuses that count as not calibrated to this system (default arbitrary,literature)")
    p.add_argument("--max-conf", type=float, default=0.1,
                   help="sobol precision check: largest ST confidence half-width allowed (default 0.1)")
    p.add_argument("--max-sum-s1", type=float, default=1.1,
                   help="sobol consistency check: largest sum of first-order indices allowed (default 1.1)")
    p.add_argument("--min-trajectories", type=int, default=10,
                   help="morris: fewer trajectories -> GSA-R WOUNDED (default 10)")
    p.add_argument("--path-tol", type=float, default=1e-6,
                   help="SALib vs numpy point estimates must agree within this (default 1e-6)")
    return p


# --------------------------------------------------------------------------- #
# Problem
# --------------------------------------------------------------------------- #
def load_problem(path):
    src = require_file(path, "--problem")
    try:
        raw = json.loads(src.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise UsageError(f"--problem is not valid JSON: {exc}") from None
    if isinstance(raw, dict) and isinstance(raw.get("parameters"), list) and raw["parameters"]:
        ps = raw["parameters"]
        if not all(isinstance(q, dict) for q in ps):
            raise UsageError("--problem 'parameters' must be a list of objects")
        names, bounds = [q.get("name") for q in ps], [q.get("bounds") for q in ps]
        dists, status = [q.get("dist") or "unif" for q in ps], [q.get("status") for q in ps]
        nominal = [q.get("nominal") for q in ps]
        extra = {k for q in ps for k in q} - PARAM_KEYS
        ignored = sorted({f"parameters[].{k}" for k in extra} | (set(raw) - {"parameters"}))
    elif isinstance(raw, dict) and isinstance(raw.get("names"), list) and isinstance(raw.get("bounds"), list):
        names, bounds, d = raw["names"], raw["bounds"], len(raw["names"])
        dists = raw.get("dists") or ["unif"] * d
        status, nominal = raw.get("status") or [None] * d, raw.get("nominal") or [None] * d
        ignored = sorted(set(raw) - LIST_KEYS)
    else:
        raise UsageError("--problem needs {\"names\": [...], \"bounds\": [...]} or {\"parameters\": [...]}")
    d = len(names)
    if d < 1 or any(len(v) != d for v in (bounds, dists, status, nominal)):
        raise UsageError("--problem lists (names, bounds, dists, status, nominal) must have equal length >= 1")
    if not all(isinstance(nm, str) and nm.strip() for nm in names) or len(set(names)) != d:
        raise UsageError("--problem parameter names must be unique non-empty strings")
    if "run_id" in names:
        raise UsageError("'run_id' is reserved for the design row id; rename that parameter")
    clean_b, clean_s = [], []
    for nm, b, dist, st in zip(names, bounds, dists, status):
        if dist not in ARITY:
            raise UsageError(f"parameter {nm!r}: dist must be one of {sorted(ARITY)}, got {dist!r}")
        try:
            b = [float(v) for v in b]
        except (TypeError, ValueError):
            raise UsageError(f"parameter {nm!r}: bounds must be numbers") from None
        if len(b) != ARITY[dist] or not all(math.isfinite(v) for v in b):
            raise UsageError(f"parameter {nm!r}: {dist} needs {ARITY[dist]} finite bound values")
        if (dist in ("unif", "triang") and not b[1] > b[0]) or (dist in ("norm", "lognorm") and not b[1] > 0) \
                or (dist == "triang" and not b[0] <= b[2] <= b[1]):
            raise UsageError(f"parameter {nm!r}: invalid {dist} bounds {b}")
        s = None if st in (None, "") else str(st).strip().lower()
        if s is not None and s not in STATUSES:
            raise UsageError(f"parameter {nm!r}: status must be one of {STATUSES}, got {st!r}")
        clean_b.append(b)
        clean_s.append(s)
    try:
        nominal = [None if v is None else float(v) for v in nominal]
    except (TypeError, ValueError):
        raise UsageError("--problem nominal values must be numbers or null") from None
    return src, {"names": names, "bounds": clean_b, "dists": list(dists), "status": clean_s, "nominal": nominal,
                 "ignored": ignored}


def ppf(u, dist, b):
    """Unit-interval values -> parameter values (inverse CDF)."""
    if dist == "unif":
        return b[0] + u * (b[1] - b[0])
    u = np.clip(u, 1e-12, 1 - 1e-12)
    if dist == "norm":
        return stats.norm.ppf(u, loc=b[0], scale=b[1])
    if dist == "lognorm":
        return np.exp(stats.norm.ppf(u, loc=b[0], scale=b[1]))
    return stats.triang.ppf(u, (b[2] - b[0]) / (b[1] - b[0]), loc=b[0], scale=b[1] - b[0])


def oat_levels(prob):
    lo, hi, nom = [], [], []
    for b, dist, nv in zip(prob["bounds"], prob["dists"], prob["nominal"]):
        q = [b[0], b[1], (b[0] + b[1]) / 2] if dist == "unif" else ppf(np.array([0.05, 0.95, 0.5]), dist, b)
        lo.append(q[0])
        hi.append(q[1])
        nom.append(q[2] if nv is None else nv)
    return np.array(lo), np.array(hi), np.array(nom)


# --------------------------------------------------------------------------- #
# Designs (unit hypercube, then per-parameter inverse CDF)
# --------------------------------------------------------------------------- #
def design_sobol(d, N, rng):
    with warnings.catch_warnings():  # scipy warns when N is not a power of 2; reported as check GSA-N instead
        warnings.simplefilter("ignore")
        try:
            sob = qmc.Sobol(d=2 * d, scramble=True, rng=rng)
        except TypeError:  # scipy < 1.15 names the argument seed
            sob = qmc.Sobol(d=2 * d, scramble=True, seed=rng)
        base = sob.random(N)
    A, B = base[:, :d], base[:, d:]
    U = np.repeat(A[:, None, :], d + 2, axis=1)     # N x (d+2) x d; every row starts as A
    for i in range(d):
        U[:, 1 + i, i] = B[:, i]                      # AB_i = A with column i taken from B
    U[:, d + 1, :] = B
    return U.reshape(N * (d + 2), d)


def design_morris(d, r, p, rng):
    """r Morris (1991) trajectories: d+1 grid points each, one factor moving by +-delta per step."""
    delta = p / (2.0 * (p - 1))
    grid = np.arange(p) / (p - 1)
    starts = grid[grid <= 1 - delta + 1e-12]
    out = np.empty((r, d + 1, d))
    for t in range(r):
        base, sign = rng.choice(starts, size=d), rng.choice([-1.0, 1.0], size=d)
        x = base + np.where(sign < 0, delta, 0.0)     # a factor moving down starts at base + delta
        out[t, 0] = x
        for step, i in enumerate(rng.permutation(d), start=1):
            x = x.copy()
            x[i] += sign[i] * delta
            out[t, step] = x
    return np.clip(out.reshape(r * (d + 1), d), 0.0, 1.0)


def design_oat(prob):
    lo, hi, nom = oat_levels(prob)
    rows = [nom.copy()]
    for i in range(nom.size):
        for v in (lo[i], hi[i]):
            row = nom.copy()
            row[i] = v
            rows.append(row)
    return np.array(rows)


def check_structure(X, method, d):
    """Refuse designs whose rows were re-ordered or edited: the estimators depend on the layout."""
    close = lambda a, b: np.allclose(a, b, rtol=1e-7, atol=1e-12)  # noqa: E731
    n = X.shape[0]
    if method == "sobol":
        if n % (d + 2) or n == 0:
            raise UsageError(f"sobol design needs N*(d+2) rows with d = {d}; got {n}")
        Z = X.reshape(-1, d + 2, d)
        for i in range(d):
            want = Z[:, 0].copy()
            want[:, i] = Z[:, d + 1, i]
            if not close(Z[:, 1 + i], want):
                raise UsageError("design rows are not in the Saltelli block order (A, AB_1..AB_d, B); "
                                 "do not sort, filter or edit design.csv")
    elif method == "morris":
        if n % (d + 1) or n == 0:
            raise UsageError(f"morris design needs N*(d+1) rows with d = {d}; got {n}")
        moved = np.abs(np.diff(X.reshape(-1, d + 1, d), axis=1)) > 1e-12
        if not ((moved.sum(axis=2) == 1).all() and (moved.sum(axis=1) == 1).all()):
            raise UsageError("design rows are not Morris trajectories (one factor moving per step); "
                             "do not sort, filter or edit design.csv")
    else:
        if n != 2 * d + 1:
            raise UsageError(f"oat design needs 2d+1 = {2 * d + 1} rows; got {n}")
        for i in range(d):
            for row in X[1 + 2 * i:3 + 2 * i]:
                if not close(np.delete(row, i), np.delete(X[0], i)):
                    raise UsageError("oat design rows are out of order (row 0 = nominal, then low/high per "
                                     "parameter); do not sort or edit design.csv")


# --------------------------------------------------------------------------- #
# Estimators (numpy path)
# --------------------------------------------------------------------------- #
def sobol_np(Y, d, n_boot, conf, rng):
    """S1: Saltelli et al. (2010) estimator mean(f_B (f_ABi - f_A)) / V; ST: Jansen (1999) estimator
    mean((f_A - f_ABi)^2) / (2V), V = var(f_A, f_B). Y is centred and scaled first, exactly as SALib does
    (the S1 estimator is not shift-invariant in finite samples). Half-widths: z * sd of bootstrap estimates."""
    Yc = (Y - Y.mean()) / Y.std()
    Z = Yc.reshape(-1, d + 2)
    A, B, AB = Z[:, 0], Z[:, d + 1], Z[:, 1:d + 1]

    def est(a, b, ab):
        var = np.var(np.concatenate([a, b], axis=-1), axis=-1)[..., None]
        return (np.mean(b[..., None] * (ab - a[..., None]), axis=-2) / var,
                0.5 * np.mean((a[..., None] - ab) ** 2, axis=-2) / var)

    s1, st = est(A, B, AB)
    idx = rng.integers(0, A.size, size=(n_boot, A.size))
    parts = [est(A[c], B[c], AB[c]) for c in np.array_split(idx, max(1, n_boot // 100))]
    z = stats.norm.ppf(0.5 + conf / 2)
    return {"S1": s1, "ST": st, "S1_conf": z * np.vstack([q[0] for q in parts]).std(0, ddof=1),
            "ST_conf": z * np.vstack([q[1] for q in parts]).std(0, ddof=1)}


def morris_np(U, Y, d, n_boot, conf, rng):
    """Elementary effects EE_i = dy / du_i in unit-cube coordinates (Morris 1991); mu* = mean |EE|
    (Campolongo et al. 2007); sigma = sd(EE) with ddof 1; mu* half-width from resampled trajectories."""
    Ut, Yt = U.reshape(-1, d + 1, d), Y.reshape(-1, d + 1)
    r = Yt.shape[0]
    du, dy = np.diff(Ut, axis=1), np.diff(Yt, axis=1)
    col = np.abs(du).argmax(axis=2)
    step = np.take_along_axis(du, col[..., None], axis=2)[..., 0]
    ee = np.empty((r, d))
    ee[np.arange(r)[:, None], col] = dy / step
    boot = np.abs(ee)[rng.integers(0, r, size=(n_boot, r))].mean(axis=1)
    return {"mu": ee.mean(0), "mu_star": np.abs(ee).mean(0),
            "sigma": ee.std(0, ddof=1) if r > 1 else np.full(d, np.nan),
            "mu_star_conf": stats.norm.ppf(0.5 + conf / 2) * boot.std(0, ddof=1), "delta": float(np.abs(step).mean())}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def _load_runs(args, names):
    dsrc, osrc = require_file(args.design, "--design"), require_file(args.outputs, "--outputs")
    try:
        D, O = pd.read_csv(dsrc), pd.read_csv(osrc)
    except Exception as exc:
        raise UsageError(f"cannot read --design/--outputs as CSV: {exc}") from None
    missing = [c for c in names if c not in D.columns]
    if missing:
        raise UsageError(f"design lacks parameter columns {missing}")
    cands = [c for c in O.columns if c != "run_id" and pd.api.types.is_numeric_dtype(O[c])]
    col = args.output_col or (cands[0] if len(cands) == 1 else None)
    if col is None or col not in O.columns:
        raise UsageError(f"choose --output-col from {list(O.columns)}")
    if "run_id" in D.columns and "run_id" in O.columns:
        if D["run_id"].duplicated().any() or O["run_id"].duplicated().any():
            raise UsageError("run_id must be unique in both --design and --outputs")
        merged = D[["run_id"] + names].merge(O[["run_id", col]], on="run_id", how="left")
        if merged[col].isna().any():
            gone = merged.loc[merged[col].isna(), "run_id"].tolist()
            raise UsageError(f"{len(gone)} design rows have no (or a missing) output, e.g. run_id {gone[:5]}")
        X, y = merged[names], merged[col]
    elif len(D) == len(O):
        X, y = D[names], O[col]
    else:
        raise UsageError(f"--design has {len(D)} rows but --outputs has {len(O)}; add run_id to align them")
    X = X.apply(pd.to_numeric, errors="coerce").to_numpy(float)
    y = pd.to_numeric(y, errors="coerce").to_numpy(float)
    if not np.isfinite(X).all():
        raise UsageError("design has missing or non-numeric parameter values")
    if not np.isfinite(y).all():
        raise UsageError(f"{int((~np.isfinite(y)).sum())} outputs are missing/non-numeric; rerun those rows "
                         "(the estimators need every row of the design)")
    return dsrc, osrc, X, y, col


def _param_checks(report, prob, imp, conf, label, thr, uncal):
    for i, nm in enumerate(prob["names"]):
        st, v = prob["status"][i], float(imp[i])
        border = conf is not None and v > thr and v - conf[i] <= thr
        extra = f" (confidence interval reaches below {thr:g}: borderline)" if border else ""
        if not math.isfinite(v):  # an undefined index is never a pass, whatever the status (CR-22)
            verdict, why = UNVERIFIED, f"{label} is not finite: the importance of {nm} could not be estimated"
        elif v <= thr:
            verdict, why = SURVIVES, f"{label} {v:.3g} <= {thr:g}: not decision-relevant at this threshold"
        elif st is None:
            verdict, why = UNVERIFIED, (f"influential ({label} {v:.3g}) but no calibration status given; add "
                                        "status (ratified/literature/fitted/arbitrary) to the problem JSON")
        elif st in uncal:
            verdict, why = WOUNDED, (f"decision-relevant uncalibrated parameter: status {st}, {label} {v:.3g}. "
                                     "Calibrate it, bound it from data, or carry its range into every reported result")
        elif st == "ratified":
            verdict, why = SURVIVES, f"owner-ratified; drives {label} {v:.3g}, so the owner should know its weight"
        else:
            verdict, why = SURVIVES, f"fitted; drives {label} {v:.3g}: propagate its estimation uncertainty"
        report.add(Check(id=f"GSA-P{i + 1:02d}", title=f"Parameter {nm} (status {st or 'not given'})",
                         verdict=verdict, value=round(v, 4), detail=why + extra,
                         criterion=f"{label} > {thr:g} with status in {sorted(uncal)} -> WOUNDED"))


def _status_table(prob, imp):
    rows = ["| status | parameters | sum importance | max importance |", "|---|---|---|---|"]
    for st in STATUSES + (None,):
        sel = [i for i, s in enumerate(prob["status"]) if s == st]
        if sel:
            rows.append(f"| {st or 'not given'} | {', '.join(prob['names'][i] for i in sel)} | "
                        f"{float(np.sum(imp[sel])):.3g} | {float(np.max(imp[sel])):.3g} |")
    return "\n".join(rows)


def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    src, prob = load_problem(args.problem)
    report.add_input(src)
    report.note_packages(["numpy", "pandas", "scipy", "SALib"])
    names, d, method = prob["names"], len(prob["names"]), args.method
    analysis = bool(args.design or args.outputs)
    if args.design_only == analysis or (analysis and not (args.design and args.outputs)):
        raise UsageError("use either --design-only, or --design and --outputs together")
    if not (0 < args.conf < 1 and args.boot >= 10 and args.st_threshold > 0 and args.max_conf > 0
            and args.max_sum_s1 > 0 and args.min_trajectories >= 2 and args.path_tol > 0):
        raise UsageError("need 0 < --conf < 1, --boot >= 10, --st-threshold > 0, --max-conf > 0, --max-sum-s1 > 0, "
                         "--min-trajectories >= 2, --path-tol > 0")
    uncal = {s.strip().lower() for s in args.uncalibrated_status.split(",") if s.strip()}
    if not uncal <= set(STATUSES):
        raise UsageError(f"--uncalibrated-status must use {STATUSES}")
    if method in ("morris",) and any(dist != "unif" for dist in prob["dists"]):
        raise UsageError("morris needs uniform parameters; use --method sobol for distributions")
    rng = np.random.default_rng(args.seed)
    lo, hi = np.array([b[0] for b in prob["bounds"]]), np.array([b[1] for b in prob["bounds"]])

    if prob["ignored"]:
        report.section("Ignored problem keys", "These keys in the problem JSON are not part of the format and were "
                       f"ignored: {', '.join(prob['ignored'])}. A dependent parameter (e.g. w2 = 1 - w1) must be "
                       "computed inside your model from the independent one, not listed here.")
    if args.design_only:  # ---------------------------------------------------------------- design
        N = args.N or (1024 if method == "sobol" else 20 if method == "morris" else None)
        if method == "sobol" and N < 2:
            raise UsageError("--N must be >= 2")
        if method == "morris" and (N < 2 or args.levels < 2 or args.levels % 2):
            raise UsageError("morris needs --N >= 2 trajectories and an even --levels >= 2")

        def build(seed):  # the whole design from one fresh generator, so it can be regenerated for GSA-DESIGN
            gen = np.random.default_rng(seed)
            if method == "sobol":
                U = design_sobol(d, N, gen)
                X = np.column_stack([ppf(U[:, i], prob["dists"][i], prob["bounds"][i]) for i in range(d)])
            elif method == "morris":
                X = lo + design_morris(d, N, args.levels, gen) * (hi - lo)
            else:
                X = design_oat(prob)
            df = pd.DataFrame(X, columns=names)
            df.insert(0, "run_id", np.arange(len(df)))
            return df.to_csv(index=False, lineterminator="\n"), len(df)

        text, rows = build(args.seed)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        same = build(args.seed)[0] == text
        report.add(Check(id="GSA-DESIGN", title="Design is reproducible from --seed", value=f"sha256 {digest[:12]}",
                         verdict=SURVIVES if same else WOUNDED,
                         criterion="regenerating the design from the same --seed gives a byte-identical design.csv",
                         detail="" if same else "the design generator is not deterministic: record the file itself"))
        if method == "sobol":
            pow2 = N & (N - 1) == 0
            report.add(Check(id="GSA-N", title="Sobol' base sample size is a power of two",
                             verdict=SURVIVES if pow2 else WOUNDED, value=N, criterion="N = 2^k",
                             detail="" if pow2 else "Sobol' balance properties need N = 2^k; the estimates will "
                                                    f"be noisier than they should be (next power: {1 << N.bit_length()})"))
        elif method == "morris":
            report.add(Check(id="GSA-R", title="Enough Morris trajectories for a stable mu* ranking",
                             verdict=SURVIVES if N >= args.min_trajectories else WOUNDED, value=N,
                             criterion=f"N >= --min-trajectories {args.min_trajectories}"))
        path = write_once(run_dir / "design.csv", text)
        meta = {"method": method, "N": N, "levels": args.levels if method == "morris" else None, "d": d,
                "rows": rows, "seed": args.seed, "sha256": digest, "names": names, "bounds": prob["bounds"],
                "dists": prob["dists"],
                "layout": {"sobol": "blocks of d+2 rows: A, AB_1..AB_d, B (SALib order)",
                           "morris": "trajectories of d+1 rows, one factor moving per step",
                           "oat": "row 0 nominal, then low/high for each parameter in order"}[method]}
        write_once(run_dir / "design_meta.json", json.dumps(meta, indent=2))
        report.section("Design", f"{rows} runs written to `{path.name}` ({meta['layout']}). Run your model on "
                       "every row, then call this script again with --design and --outputs. This script never "
                       "runs the model itself.")
        report.data.update({"mode": "design", "method": method, "rows": rows, "design": str(path),
                            "design_sha256": digest, "ignored_keys": prob["ignored"]})
        return

    dsrc, osrc, X, Y, col = _load_runs(args, names)  # ------------------------------------ analysis
    report.add_input(dsrc)
    report.add_input(osrc)
    check_structure(X, method, d)
    salib = optional_import("SALib")
    engine = f"SALib {pkg_version('SALib')} (numpy cross-check)" if salib else "numpy (SALib not installed)"
    emit("stage", "running", f"{method} analysis of {len(Y)} runs with {engine}", run_id=run_id, source=SRC)
    scale = 1e-12 * max(1.0, float(np.abs(Y).max()))
    if np.ptp(Y) <= scale:
        report.add(Check(id="GSA-VAR", title="Model output varies over the design", verdict=UNVERIFIED,
                         criterion="output range > 1e-12 x max(1, max |output|)", value=0.0,
                         detail="the output is constant on every run: no sensitivity can be attributed"))
        report.data.update({"mode": "analysis", "method": method, "engine": engine})
        return
    if method == "sobol":  # the Sobol' variance is var(f_A, f_B); if it is 0 every index is 0/0 (CR-22)
        Z = Y.reshape(-1, d + 2)
        if np.ptp(np.r_[Z[:, 0], Z[:, d + 1]]) <= scale:
            report.add(Check(id="GSA-VAR", title="Model output varies over the design", verdict=UNVERIFIED,
                             criterion=("range of f_A, f_B > 1e-12 x max(1, max |output|) (their variance divides "
                                        "every Sobol' index)"), value=0.0,
                             detail="the output is constant on the A and B rows although other rows vary, so every "
                                    "index is undefined; check that the outputs are aligned with the design rows"))
            report.data.update({"mode": "analysis", "method": method, "engine": engine})
            return
    sp = {"num_vars": d, "names": names, "bounds": [[0.0, 1.0]] * d}
    table = pd.DataFrame({"parameter": names, "status": [s or "not given" for s in prob["status"]]})
    conf, agree = None, None
    if method == "sobol":
        res = sobol_np(Y, d, args.boot, args.conf, rng)
        if salib:
            from SALib.analyze import sobol as sal_sobol
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                sres = sal_sobol.analyze(sp, Y, calc_second_order=False, num_resamples=args.boot,
                                         conf_level=args.conf, seed=args.seed)
            agree = max(float(np.max(np.abs(np.asarray(sres[k]) - res[k]))) for k in ("S1", "ST"))
            res = {k: np.asarray(sres[k], dtype=float) for k in ("S1", "ST", "S1_conf", "ST_conf")} | {
                "np_S1": res["S1"], "np_ST": res["ST"]}
        for k, v in res.items():
            table[k] = v
        imp, conf, label = res["ST"], res["ST_conf"], "ST"
        worst = float(np.max(res["ST_conf"]))
        report.add(Check(id="GSA-PREC", title="Sobol' indices estimated precisely enough to rank parameters",
                         verdict=SURVIVES if worst <= args.max_conf else WOUNDED, value=round(worst, 4),
                         criterion=f"largest ST {100 * args.conf:g}% half-width <= {args.max_conf:g}",
                         detail=f"N = {len(Y) // (d + 2)} base samples; increase N (x4 halves the half-width)"))
        slack = np.maximum(res["S1_conf"], res["ST_conf"])
        bad = [names[i] for i in range(d) if res["S1"][i] > res["ST"][i] + slack[i]]
        tot = float(np.sum(res["S1"]))
        report.add(Check(id="GSA-CONSIST", title="Sobol' estimates internally consistent",
                         verdict=SURVIVES if not bad and tot <= args.max_sum_s1 else WOUNDED, value=round(tot, 4),
                         criterion=(f"S1 <= ST (within half-widths) for every parameter and sum(S1) <= --max-sum-s1 "
                                    f"{args.max_sum_s1:g}"),
                         detail=(f"sum S1 = {tot:.3f}: {max(0.0, 1 - tot):.3f} of the variance comes from "
                                 "interactions" + (f"; S1 > ST for {bad}: estimator noise, increase N" if bad else ""))))
    elif method == "morris":
        U = (X - lo) / (hi - lo)
        res = morris_np(U, Y, d, args.boot, args.conf, rng)
        p = int(round(2 * res["delta"] / (2 * res["delta"] - 1))) if res["delta"] > 0.5 else args.levels
        if salib:
            from SALib.analyze import morris as sal_morris
            sres = sal_morris.analyze(sp, U, Y, num_resamples=args.boot, conf_level=args.conf,
                                      num_levels=p, seed=args.seed)
            agree = max(float(np.nanmax(np.abs(np.asarray(sres[k], dtype=float) - res[k])))
                        for k in ("mu", "mu_star", "sigma"))
            res = {k: np.asarray(sres[k], dtype=float) for k in ("mu", "mu_star", "sigma", "mu_star_conf")} | {
                "np_mu_star": res["mu_star"]}
        for k in ("mu", "mu_star", "sigma", "mu_star_conf", "np_mu_star"):
            if k in res:
                table[k] = res[k]
        total = float(np.sum(res["mu_star"]))
        imp, label = (res["mu_star"] / total if total > 0 else np.zeros(d)), "mu* share"
        table["mu_star_share"] = imp
        r = len(Y) // (d + 1)
        report.add(Check(id="GSA-R", title="Enough Morris trajectories for a stable mu* ranking",
                         verdict=SURVIVES if r >= args.min_trajectories else WOUNDED, value=r,
                         criterion=f"N >= --min-trajectories {args.min_trajectories}",
                         detail="sigma/mu* near or above 1 marks non-linear or interacting parameters"))
    else:
        base, ylo, yhi = Y[0], Y[1::2], Y[2::2]
        swing = np.abs(yhi - ylo)
        total = float(swing.sum())
        imp, label = (swing / total if total > 0 else np.zeros(d)), "swing share"
        tol = 1e-9 * max(1.0, float(np.abs(Y).max()))
        nonmono = (base < np.minimum(ylo, yhi) - tol) | (base > np.maximum(ylo, yhi) + tol)
        for k, v in {"y_low": ylo, "y_high": yhi, "swing": swing, "swing_share": imp, "non_monotone": nonmono}.items():
            table[k] = v
        bad = [names[i] for i in np.flatnonzero(nonmono)]
        report.add(Check(id="GSA-MONO", title="OAT swings are not hiding non-monotone responses",
                         verdict=SURVIVES if not bad else WOUNDED, value=len(bad),
                         criterion=("nominal output lies between the low and high outputs for every parameter "
                                    "(margin 1e-9 x max(1, max |output|))"),
                         detail=(f"non-monotone: {bad}; their swing understates their effect, use morris or sobol"
                                 if bad else "OAT still cannot see interactions; confirm with morris or sobol")))
    if agree is not None:
        report.add(Check(id="GSA-PATH", title="SALib and numpy estimators agree (second computation path)",
                         verdict=SURVIVES if agree <= args.path_tol else WOUNDED, value=agree,
                         criterion=f"max absolute difference of point estimates <= --path-tol {args.path_tol:g}"))
    _param_checks(report, prob, imp, conf, label, args.st_threshold, uncal)
    table["importance"] = imp
    shown = [c for c in table.columns if not c.startswith("np_")]
    lines = ["| " + " | ".join(shown) + " |", "|" + "---|" * len(shown)]
    for _, row in table.sort_values("importance", ascending=False, kind="stable").iterrows():
        lines.append("| " + " | ".join(f"{row[c]:.4g}" if isinstance(row[c], (float, np.floating)) else str(row[c])
                                       for c in shown) + " |")
    report.section(f"Sensitivity ({method}, engine: {engine}, output column {col!r}, {len(Y)} runs)",
                   "\n".join(lines))
    if any(s is not None for s in prob["status"]):
        report.section("Importance by calibration status", _status_table(prob, imp))
    report.data.update({"mode": "analysis", "method": method, "engine": engine, "runs": int(len(Y)),
                        "output_col": col, "salib_numpy_max_diff": agree,
                        "indices": {c: [None if isinstance(v, float) and not math.isfinite(v) else v
                                        for v in table[c].tolist()] for c in table.columns}})


if __name__ == "__main__":
    sys.exit(run_main(SCRIPT, main, build_parser()))
