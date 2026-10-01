#!/usr/bin/env python3
"""Sensitivity of an estimate to unobserved confounding, in closed form (numpy/scipy only).
Read-only: reads numbers from the command line or one --table CSV; writes only its run folder.

Usage:
  python scripts/confounding_sensitivity.py --mode sensemakr --estimate B --se SE --dof DF [--q 1] [--alpha 0.05]
      [--r2dz-bench R2 --r2yz-bench R2 --kd 1,2,3 [--ky 1,2,3]] [--r2dz R2 --r2yz R2]
  python scripts/confounding_sensitivity.py --mode evalue --rr X [--lo L --hi H]
      | --or X [--rare] [--lo L --hi H] | --hr X [--rare] [--lo L --hi H] | --smd D --se SE
  python scripts/confounding_sensitivity.py --mode oster --beta-short B0 --r2-short R0 --beta-long B --r2-long R
      [--rmax RMAX | --rmax 1.3x]
  python scripts/confounding_sensitivity.py --table FILE.csv [--mode MODE]
      one scenario per row; columns named like the flags (r2dz-bench or r2dz_bench; or; kd as 1;2;3), optional
      'mode' and 'label' columns; empty cells fall back to the command-line values.

sensemakr (Cinelli & Hazlett 2020), from the treatment coefficient B, its SE and the residual df:
  partial R^2 of treatment with outcome, RV_q (a confounder whose partial R^2 with both treatment and outcome
  is RV_q removes 100q% of the estimate), RV_q,alpha (the same for losing significance at alpha), and
  bias-adjusted estimates for a confounder kd (treatment side) and ky (outcome side) times as strong as an
  observed benchmark covariate whose partial R^2s are --r2dz-bench (with treatment) and --r2yz-bench (with
  outcome). --r2dz/--r2yz evaluate one hypothetical confounder directly.
evalue (VanderWeele & Ding 2017): E-value of the point estimate and of the CI limit nearer the null. Odds and
  hazard ratios are converted to risk ratios (--rare keeps them as they are, for outcomes under ~15%); a
  standardized mean difference uses RR ~ exp(0.91 d).
oster (Oster 2019): delta (selection on unobservables relative to observables) that would bring the coefficient
  to 0, and the bias-adjusted beta* at delta = 1, from the short (no controls) and long (controls) regressions.
  Uses Oster's closed-form approximation beta* = b - delta (b0 - b)(Rmax - R)/(R - R0); the exact root needs
  var(Y), var(D) and var(D | controls), which this script does not take. --rmax 1.3x means min(1.3 R, 1).

Verdict rules (thresholds are flags; fix them before running):
  CS-RV     RV_q >= --rv-min: SURVIVES; else WOUNDED (fragile). RV_q,alpha is reported, not judged.
  CS-BENCH  bias-adjusted estimate keeps its sign for every --kd multiple: SURVIVES; the smallest multiple at
            which it reaches 0 or flips is <= --kd-kill: KILLED (a confounder no stronger than the benchmark
            reverses the sign); flips only at larger multiples: WOUNDED; no feasible multiple: UNVERIFIED-HERE.
  CS-HYPO   the hypothetical --r2dz/--r2yz confounder keeps the sign: SURVIVES; else WOUNDED.
  CS-EVALUE E-value >= --e-min and (no CI given, or the CI-limit E-value >= --e-min): SURVIVES; else WOUNDED.
            Set --e-min from the strongest measured confounder's risk ratio before running.
  CS-OSTER  delta >= --delta-min, or delta < 0 (controls moved the estimate away from 0): SURVIVES; else WOUNDED.
            Controls that do not raise R^2: UNVERIFIED-HERE (delta undefined).

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
A KILLED printed by this script is a candidate verdict: record it only after a second independent reader confirms it.
"""
# Formula sources:
#   Cinelli & Hazlett (2020) JRSS-B 82(1):39-67, doi:10.1111/rssb.12348 -- partial R^2 = t^2/(t^2 + df);
#     RV_q = (sqrt(f_q^4 + 4 f_q^2) - f_q^2)/2 with f_q = q|t|/sqrt(df); RV_q,alpha uses f_q - f*_alpha,df-1 and
#     (f_q^2 - f*^2)/(1 + f_q^2) when f_q > 1/f*; |bias| = se * sqrt(df * R2yz * R2dz / (1 - R2dz));
#     adjusted se = se * sqrt((1 - R2yz)/(1 - R2dz) * df/(df - 1)); benchmark bounds (Sec. 6.1):
#     R2dz = kd f2(D~Xj), R2(Z~Xj|D) = kd R2dxj^2/((1 - kd R2dxj)(1 - R2dxj)),
#     R2yz = ((sqrt(ky) + sqrt(R2(Z~Xj|D)))/sqrt(1 - R2(Z~Xj|D)))^2 f2(Y~Xj|D).
#   VanderWeele & Ding (2017) Annals of Internal Medicine 167(4):268-274, doi:10.7326/m16-2607 --
#     E = RR + sqrt(RR (RR - 1)) (RR < 1: use 1/RR); CI limit nearer 1, or 1 if the CI crosses 1;
#     SMD: RR ~ exp(0.91 d), CI exp(0.91 d -/+ 1.78 se).
#   VanderWeele (2017) Epidemiology 28(6):e58-e60 -- common outcome: RR ~ sqrt(OR).
#   VanderWeele (2020) Biometrics 76(3):746-752 -- common outcome: RR ~ (1 - 0.5^sqrt(HR))/(1 - 0.5^sqrt(1/HR)).
#   Oster (2019) JBES 37(2):187-204, doi:10.1080/07350015.2016.1227711 -- beta*(delta) and delta for beta = 0.
# Parity (checked 2026-09-30 against the R package sensemakr 0.1.6 on its Darfur example): partial R^2, RV_q,
#   RV_q,alpha, benchmark R2dz/R2yz and adjusted estimate/se/t agree to ~1e-12, and the adjusted CI equals
#   sensemakr::adjusted_ci() (critical value t(1 - alpha/2, df - 1)). sensemakr's own bounds table uses
#   qt(., df) instead, so its printed CI limits differ from these in the 7th significant digit.
from __future__ import annotations

import csv
import io
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (Check, Report, UsageError, base_parser, run_main, require_file, write_once,  # noqa: E402
                     SURVIVES, WOUNDED, KILLED, UNVERIFIED)

from scipy.special import stdtrit  # noqa: E402  (Student t quantile; lighter to import than scipy.stats)

SCRIPT = "confounding_sensitivity"
MODES = ("sensemakr", "evalue", "oster")
NUM = ("estimate", "se", "dof", "q", "alpha", "r2dz_bench", "r2yz_bench", "r2dz", "r2yz", "rr", "odds_ratio", "hr",
       "smd", "lo", "hi", "beta_short", "r2_short", "beta_long", "r2_long")
TEXT = ("kd", "ky", "rmax", "rare", "mode", "label")


def build_parser():
    p = base_parser(__doc__)
    p.add_argument("--mode", choices=MODES, help="sensemakr | evalue | oster (a table may carry a 'mode' column)")
    p.add_argument("--table", help="CSV with one scenario per row, columns named like the flags")
    p.add_argument("--label", help="name for a single command-line scenario")
    g = p.add_argument_group("sensemakr")
    g.add_argument("--estimate", type=float, help="treatment coefficient")
    g.add_argument("--se", type=float, help="its standard error (also the SE of --smd)")
    g.add_argument("--dof", type=float, help="residual degrees of freedom of the full regression")
    g.add_argument("--q", type=float, default=1.0, help="share of the estimate to explain away (default 1)")
    g.add_argument("--alpha", type=float, default=0.05, help="significance level for RV_q,alpha and CIs (0.05)")
    g.add_argument("--r2dz-bench", type=float, help="benchmark covariate's partial R^2 with the treatment")
    g.add_argument("--r2yz-bench", type=float, help="benchmark covariate's partial R^2 with the outcome")
    g.add_argument("--kd", default="1,2,3", help="strength multiples on the treatment side (default 1,2,3)")
    g.add_argument("--ky", help="multiples on the outcome side (default: same as --kd)")
    g.add_argument("--r2dz", type=float, help="hypothetical confounder: partial R^2 with the treatment")
    g.add_argument("--r2yz", type=float, help="hypothetical confounder: partial R^2 with the outcome")
    g.add_argument("--rv-min", type=float, default=0.05, help="RV_q needed for SURVIVES (default 0.05)")
    g.add_argument("--kd-kill", type=float, default=1.0, help="a sign flip at kd <= this is KILLED (default 1)")
    g = p.add_argument_group("evalue")
    g.add_argument("--rr", type=float, help="risk ratio")
    g.add_argument("--or", dest="odds_ratio", type=float, help="odds ratio")
    g.add_argument("--hr", type=float, help="hazard ratio")
    g.add_argument("--rare", action="store_true", help="outcome is rare (< ~15%%): OR and HR approximate RR")
    g.add_argument("--smd", type=float, help="standardized mean difference (needs --se)")
    g.add_argument("--lo", type=float, help="lower CI limit on the ratio scale supplied")
    g.add_argument("--hi", type=float, help="upper CI limit on the ratio scale supplied")
    g.add_argument("--e-min", type=float, default=2.0, help="E-value needed for SURVIVES (default 2.0)")
    g = p.add_argument_group("oster")
    g.add_argument("--beta-short", type=float, help="treatment coefficient without controls")
    g.add_argument("--r2-short", type=float, help="R^2 without controls")
    g.add_argument("--beta-long", type=float, help="treatment coefficient with controls")
    g.add_argument("--r2-long", type=float, help="R^2 with controls")
    g.add_argument("--rmax", default="1.3x", help="R^2 of the hypothetical full regression, or '1.3x' (default)")
    g.add_argument("--delta-min", type=float, default=1.0, help="delta needed for SURVIVES (default 1)")
    return p


# --------------------------------------------------------------------------- closed forms
def rv_from_f(f: float) -> float:
    """Cinelli & Hazlett (2020): RV = (sqrt(f^4 + 4 f^2) - f^2) / 2, evaluated in the algebraically equal form
    2 / (1 + sqrt(1 + 4/f^2)). The textbook form cancels catastrophically for large f (it returns 0 for f >~ 3e8,
    review CR-09); this one is stable for every f and tends to 1 as f grows, as sensemakr's does."""
    if f <= 0:
        return 0.0
    return 2.0 / (1.0 + math.sqrt(1.0 + 4.0 / (f * f)))


def robustness_values(t: float, dof: float, q: float = 1.0, alpha: float = 0.05):
    """(partial R^2 of D with Y, RV_q, RV_q,alpha) from the treatment t-statistic and residual df."""
    tt = t * t
    r2yd = 1.0 / (1.0 + dof / tt) if tt > 0 else 0.0          # t^2/(t^2 + df), overflow-safe
    fq = q * abs(t) / math.sqrt(dof)
    fcrit = stdtrit(dof - 1, 1 - alpha / 2) / math.sqrt(dof - 1)
    fqa = fq - fcrit
    if fqa <= 0:
        rva = 0.0
    elif fq > 1 / fcrit:  # extreme regime: the bound is reached with R2(Y~Z|D,X) = 1
        r = fcrit / fq
        rva = (1.0 - r * r) / (1.0 + 1.0 / (fq * fq))        # (fq^2 - f*^2)/(1 + fq^2), overflow-safe
    else:
        rva = rv_from_f(fqa)
    return r2yd, rv_from_f(fq), rva


def adjusted(est, se, dof, r2dz, r2yz, alpha=0.05) -> dict:
    """Bias-adjusted estimate (moved toward 0), SE, t and CI for a confounder with partial R^2s r2dz, r2yz."""
    bias = se * math.sqrt(dof * r2yz * r2dz / (1 - r2dz))
    new = math.copysign(1.0, est) * (abs(est) - bias)
    new_se = se * math.sqrt((1 - r2yz) / (1 - r2dz)) * math.sqrt(dof / (dof - 1))
    tc = stdtrit(dof - 1, 1 - alpha / 2)
    return {"r2dz": r2dz, "r2yz": r2yz, "bias": bias, "estimate": new, "se": new_se,
            "t": new / new_se if new_se > 0 else math.copysign(math.inf, new), "lo": new - tc * new_se,
            "hi": new + tc * new_se, "flips": bias >= abs(est)}


def bench_bound(r2dxj: float, r2yxj: float, kd: float, ky: float):
    """Cinelli & Hazlett (2020) Sec. 6.1: implied (R2dz, R2yz) for a confounder kd/ky times a benchmark.
    Returns (r2dz, r2yz, capped) or None when the multiple is impossible (implied R^2 >= 1)."""
    r2dz = kd * r2dxj / (1 - r2dxj)
    if r2dz >= 1:
        return None
    r2zxj = kd * r2dxj ** 2 / ((1 - kd * r2dxj) * (1 - r2dxj))
    if r2zxj >= 1:
        return None
    r2yz = ((math.sqrt(ky) + math.sqrt(r2zxj)) / math.sqrt(1 - r2zxj)) ** 2 * (r2yxj / (1 - r2yxj))
    return r2dz, min(r2yz, 1.0), r2yz > 1


def evalue_rr(rr: float) -> float:
    """VanderWeele & Ding (2017): E = RR + sqrt(RR (RR - 1)); for RR < 1 use 1/RR."""
    rr = 1 / rr if rr < 1 else rr
    return rr + math.sqrt(rr * (rr - 1))


def to_rr(kind: str, x: float, rare: bool) -> float:
    if kind == "rr" or rare:
        return x
    if kind == "odds_ratio":
        return math.sqrt(x)
    return (1 - 0.5 ** math.sqrt(x)) / (1 - 0.5 ** math.sqrt(1 / x))  # hazard ratio, common outcome


def oster_delta(b0: float, r0: float, b: float, r: float, rmax: float):
    """Oster (2019) closed-form approximation: (delta for beta = 0, beta* at delta = 1)."""
    if b0 == b:
        return math.inf, b
    beta_star = b - (b0 - b) * (rmax - r) / (r - r0)
    delta = b * (r - r0) / ((b0 - b) * (rmax - r))
    return delta, beta_star


# --------------------------------------------------------------------------- scenarios
def _num(p: dict, key: str, what: str, lo=-math.inf, hi=math.inf, lo_open=False, hi_open=False):
    v = p.get(key)
    if v is None:
        raise UsageError(f"{what}: --{key.replace('_', '-')} is required")
    if (not math.isfinite(v) or v < lo or v > hi or (lo_open and v == lo) or (hi_open and v == hi)):
        raise UsageError(f"{what}: --{key.replace('_', '-')} = {v} is outside its range")
    return v


def _mults(text: str, what: str, flag: str):
    try:
        vals = [float(x) for x in str(text).replace(";", ",").replace("|", ",").split(",") if x.strip()]
    except ValueError:
        raise UsageError(f"{what}: {flag} must be numbers like 1,2,3")
    if not vals or any(v <= 0 or not math.isfinite(v) for v in vals):
        raise UsageError(f"{what}: {flag} must be positive numbers")
    return vals


def run_sensemakr(p, a, tag, what):
    est = _num(p, "estimate", what)
    se = _num(p, "se", what, 0, lo_open=True)
    dof = _num(p, "dof", what, 1, lo_open=True)
    q = _num(p, "q", what, 0, lo_open=True)
    alpha = _num(p, "alpha", what, 0, 1, True, True)
    t = est / se
    r2yd, rv, rva = robustness_values(t, dof, q, alpha)
    checks, row = [], {"t": t, "r2yd": r2yd, "rv_q": rv, "rv_q_alpha": rva}
    checks.append(Check(id=f"CS-RV{tag}", title="robustness value of the estimate (Cinelli-Hazlett)",
                        verdict=SURVIVES if rv >= a.rv_min else WOUNDED, value=rv, criterion=f"RV_q >= {a.rv_min:g} (q = {q:g})",
                        detail=(f"t = {t:.4g}, df = {dof:g}; partial R^2 of treatment with outcome = {r2yd:.4g} (a confounder "
                                f"explaining all residual outcome variance would need this much of the treatment); RV_q = "
                                f"{rv:.4g}: a confounder with partial R^2 >= RV_q with both treatment and outcome removes "
                                f"{100 * q:g}% of the estimate; RV_q,alpha = {rva:.4g} (alpha {alpha:g}) for losing significance.")))
    if p.get("r2dz_bench") is not None or p.get("r2yz_bench") is not None:
        r2dxj = _num(p, "r2dz_bench", what, 0, 1, hi_open=True)
        r2yxj = _num(p, "r2yz_bench", what, 0, 1, hi_open=True)
        kds = _mults(p.get("kd") or a.kd, what, "--kd")
        kys = _mults(p.get("ky") or a.ky or ",".join(map(str, kds)), what, "--ky")
        if len(kys) != len(kds):
            raise UsageError(f"{what}: --ky needs as many values as --kd")
        bounds, skipped = [], []
        for kd, ky in zip(kds, kys):
            bb = bench_bound(r2dxj, r2yxj, kd, ky)
            if bb is None:
                skipped.append(kd)
                continue
            adj = adjusted(est, se, dof, bb[0], bb[1], alpha)
            adj.update(kd=kd, ky=ky, r2yz_capped=bb[2])
            bounds.append(adj)
        row["bounds"] = bounds
        flips = [bd["kd"] for bd in bounds if bd["flips"]]
        done = ",".join(f"{bd['kd']:g}" for bd in bounds) or "none"
        crit = (f"sign kept for kd in {done}; flip at kd <= {a.kd_kill:g} KILLED, at larger kd WOUNDED"
                + (f" (kd {','.join(f'{k:g}' for k in skipped)} impossible given the benchmark's partial R^2, "
                   "not evaluated)" if skipped else ""))
        desc = "; ".join(f"{bd['kd']:g}x: R2dz {bd['r2dz']:.4g}, R2yz {bd['r2yz']:.4g}{' (capped at 1)' if bd['r2yz_capped'] else ''}"
                         f" -> adjusted {bd['estimate']:.4g} (CI {bd['lo']:.4g} to {bd['hi']:.4g})" for bd in bounds)
        if skipped:
            desc += f"; impossible multiples skipped: {', '.join(f'{k:g}' for k in skipped)}"
        if not bounds:
            v = UNVERIFIED
        elif not flips:
            v = SURVIVES
        else:
            v = KILLED if min(flips) <= a.kd_kill else WOUNDED
        checks.append(Check(id=f"CS-BENCH{tag}", title="estimate keeps its sign under benchmark-bounded confounding",
                            verdict=v, value=min(flips) if flips else None, criterion=crit,
                            detail=f"benchmark partial R^2: treatment {r2dxj:g}, outcome {r2yxj:g}. {desc}."))
    if p.get("r2dz") is not None or p.get("r2yz") is not None:
        r2dz = _num(p, "r2dz", what, 0, 1, hi_open=True)
        r2yz = _num(p, "r2yz", what, 0, 1)
        adj = adjusted(est, se, dof, r2dz, r2yz, alpha)
        row["hypothetical"] = adj
        checks.append(Check(id=f"CS-HYPO{tag}", title="estimate keeps its sign under the stated hypothetical confounder",
                            verdict=WOUNDED if adj["flips"] else SURVIVES, value=adj["estimate"],
                            criterion="bias-adjusted estimate keeps the original sign",
                            detail=(f"R2dz {r2dz:g}, R2yz {r2yz:g}: bias {adj['bias']:.4g}, adjusted estimate "
                                    f"{adj['estimate']:.4g}, se {adj['se']:.4g}, t {adj['t']:.4g}, CI {adj['lo']:.4g} to {adj['hi']:.4g}.")))
    return checks, row


def run_evalue(p, a, tag, what):
    kinds = [k for k in ("rr", "odds_ratio", "hr", "smd") if p.get(k) is not None]
    if len(kinds) != 1:
        raise UsageError(f"{what}: give exactly one of --rr, --or, --hr, --smd")
    kind, rare = kinds[0], bool(p.get("rare"))
    lo, hi = p.get("lo"), p.get("hi")
    if kind == "smd":
        if lo is not None or hi is not None:
            raise UsageError(f"{what}: with --smd give --se, not --lo/--hi")
        d, se = p["smd"], _num(p, "se", what, 0, lo_open=True)
        est, lo, hi = math.exp(0.91 * d), math.exp(0.91 * d - 1.78 * se), math.exp(0.91 * d + 1.78 * se)
        conv = "RR ~ exp(0.91 d), CI exp(0.91 d -/+ 1.78 se)"
    else:
        raw = _num(p, kind, what, 0, lo_open=True)
        for nm, v in (("lo", lo), ("hi", hi)):
            if v is not None and not (math.isfinite(v) and v > 0):
                raise UsageError(f"{what}: --{nm} must be a positive ratio")
        if (lo is not None and lo > raw) or (hi is not None and hi < raw):
            raise UsageError(f"{what}: need --lo <= estimate <= --hi")
        est = to_rr(kind, raw, rare)
        lo = None if lo is None else to_rr(kind, lo, rare)
        hi = None if hi is None else to_rr(kind, hi, rare)
        conv = {"rr": "risk ratio, no conversion", "odds_ratio": "RR ~ OR (rare outcome)" if rare else
                "RR ~ sqrt(OR) (common outcome)", "hr": "RR ~ HR (rare outcome)" if rare else
                "RR ~ (1 - 0.5^sqrt(HR))/(1 - 0.5^sqrt(1/HR)) (common outcome)"}[kind]
    e = evalue_rr(est)
    e_ci = None
    if est > 1 and lo is not None:
        e_ci = 1.0 if lo <= 1 else evalue_rr(lo)
    elif est < 1 and hi is not None:
        e_ci = 1.0 if hi >= 1 else evalue_rr(hi)
    elif est == 1 and (lo is not None or hi is not None):
        e_ci = 1.0
    ok = e >= a.e_min and (e_ci is None or e_ci >= a.e_min)
    ci_txt = "no CI given, so only the point estimate is assessed" if e_ci is None else f"CI-limit E-value {e_ci:.4g}"
    detail = (f"{conv}; RR = {est:.4g}. E-value {e:.4g} ({ci_txt}): an unmeasured confounder would need a risk-ratio "
              f"association of at least {e:.4g} with both treatment and outcome, beyond the measured covariates, to "
              "explain the estimate away; weaker confounding could not.")
    check = Check(id=f"CS-EVALUE{tag}", title="E-value against unmeasured confounding (VanderWeele-Ding)",
                  verdict=SURVIVES if ok else WOUNDED, value=e,
                  criterion=f"E-value >= {a.e_min:g} for the estimate and, when given, the CI limit nearer 1",
                  detail=detail)
    return [check], {"rr": est, "rr_lo": lo, "rr_hi": hi, "evalue": e, "evalue_ci": e_ci, "conversion": conv}


def run_oster(p, a, tag, what):
    b0, b = _num(p, "beta_short", what), _num(p, "beta_long", what)
    r0 = _num(p, "r2_short", what, 0, 1)
    r = _num(p, "r2_long", what, 0, 1)
    spec = str(p.get("rmax") or a.rmax).strip().lower()
    try:
        rmax = min(float(spec[:-1]) * r, 1.0) if spec.endswith("x") else float(spec)
    except ValueError:
        raise UsageError(f"{what}: --rmax must be a number or a multiple like 1.3x")
    if not (r < rmax <= 1):
        raise UsageError(f"{what}: --rmax ({rmax:g}) must exceed --r2-long ({r:g}) and be at most 1")
    row = {"rmax": rmax}
    if r <= r0:
        return [Check(id=f"CS-OSTER{tag}", title="coefficient stability under proportional selection (Oster)",
                      verdict=UNVERIFIED, value=None, criterion=f"delta >= {a.delta_min:g} or delta < 0",
                      detail="the controls did not raise R^2, so the selection ratio delta is undefined")], row
    delta, beta_star = oster_delta(b0, r0, b, r, rmax)
    row.update(delta=delta, beta_star=beta_star)
    ok = delta >= a.delta_min or delta < 0
    note = ("controls moved the estimate away from 0, so selection on unobservables in the same direction cannot "
            "reach 0" if delta < 0 else f"unobservables would need {delta:.4g} times the selection on observables to "
            "bring the coefficient to 0")
    return [Check(id=f"CS-OSTER{tag}", title="coefficient stability under proportional selection (Oster)",
                  verdict=SURVIVES if ok else WOUNDED, value=delta, criterion=f"delta >= {a.delta_min:g} or delta < 0",
                  detail=(f"beta short {b0:g} (R^2 {r0:g}) -> long {b:g} (R^2 {r:g}), Rmax {rmax:.4g}: delta = {delta:.4g}; "
                          f"beta* at delta = 1 is {beta_star:.4g} (identified set {min(b, beta_star):.4g} to "
                          f"{max(b, beta_star):.4g}); {note}. Closed-form approximation."))], row


def _read_table(path: pathlib.Path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise UsageError("--table has no data rows")
    out, ignored = [], set()
    for i, r in enumerate(rows, start=1):
        rec = {}
        for k, v in r.items():
            if k is None:
                raise UsageError(f"--table row {i} has more cells than the header")
            key = k.strip().lower().lstrip("-").replace("-", "_")
            key = "odds_ratio" if key == "or" else key
            v = (v or "").strip()
            if key in NUM:
                if v:
                    try:
                        rec[key] = float(v)
                    except ValueError:
                        raise UsageError(f"--table row {i}: {k} = {v!r} is not a number")
            elif key in TEXT:
                if v:
                    rec[key] = v.lower() in ("1", "true", "yes", "y") if key == "rare" else v
            else:
                ignored.add(k)
        out.append(rec)
    return out, sorted(ignored)


def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    report.note_packages(["numpy", "scipy"])
    cli = {k: getattr(args, k) for k in NUM if getattr(args, k, None) is not None}
    for k in ("kd", "ky", "rmax"):
        if getattr(args, k, None) is not None:
            cli[k] = getattr(args, k)
    cli["q"], cli["alpha"], cli["rare"] = args.q, args.alpha, args.rare
    for name in ("rv_min", "e_min", "delta_min", "kd_kill"):
        if not (getattr(args, name) > 0 and math.isfinite(getattr(args, name))):
            raise UsageError(f"--{name.replace('_', '-')} must be positive")
    if args.table:
        src = require_file(args.table, "--table")
        report.add_input(src)
        rows, ignored = _read_table(src)
        scen = [{**cli, **r} for r in rows]
        if ignored:
            report.section("Ignored table columns", ", ".join(ignored))
    else:
        scen = [dict(cli, label=args.label)] if args.label else [cli]
    results = []
    for i, p in enumerate(scen, start=1):
        mode = (p.get("mode") or args.mode or "").strip().lower()
        what = f"row {i}" if args.table else "input"
        if mode not in MODES:
            raise UsageError(f"{what}: --mode must be one of {', '.join(MODES)} (or a 'mode' column in --table)")
        label = p.get("label") or (str(i) if args.table else "")
        tag = f"[{label}]" if label else ""
        runner = {"sensemakr": run_sensemakr, "evalue": run_evalue, "oster": run_oster}[mode]
        checks, row = runner(p, args, tag, what)
        for c in checks:
            report.add(c)
        results.append({"label": label or "-", "mode": mode, **{k: v for k, v in row.items() if not isinstance(v, (list, dict))},
                        "verdicts": " ".join(f"{c.id}={c.verdict}" for c in checks)})
        report.data.setdefault("scenarios", []).append({"label": label, "mode": mode, "inputs": p, "results": row})
    cols = []
    for r in results:
        cols += [k for k in r if k not in cols]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    w.writerows([[_cell(r.get(k)).replace("\\|", "|") for k in cols] for r in results])
    write_once(run_dir / "results.csv", buf.getvalue())
    table = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    table += ["| " + " | ".join(_cell(r.get(k)) for k in cols) + " |" for r in results]
    report.section("Scenarios", "\n".join(table))
    report.data = _json_safe(report.data)            # strict JSON: non-finite numbers (delta = inf) become null
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


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v).replace("|", "\\|")


if __name__ == "__main__":
    sys.exit(run_main(SCRIPT, main, build_parser()))
