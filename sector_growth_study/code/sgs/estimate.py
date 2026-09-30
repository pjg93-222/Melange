"""OLS with sector baselines, HC1 errors (reference only), wild cluster restricted bootstrap by sector, strata.

Inference for every focal coefficient: wild cluster restricted (WCR) bootstrap-t with Webb six-point weights,
clusters = sectors, CR1 cluster-robust standard error in the t statistic. The null beta_k = beta0 is imposed on the
bootstrap DGP; all 6**G weight vectors are enumerated when 6**G <= B (config.BOOT_B = 9,999), else B draws from a
seeded generator. p-value: share of bootstrap |t*| >= |t| (symmetric, two-sided). The 95% CI is the set of beta0
not rejected at 5%, found by test inversion. Bootstrap statistics are linear-fractional in beta0, so each p(beta0)
evaluation reuses the same draws in O(B) (the algebra of Roodman, MacKinnon, Nielsen and Webb 2019, "fast and wild").
With enumeration the two draws w = +1 and w = -1 reproduce |t| exactly, so p >= 2 / 6**G; with G = 2 no value can be
rejected at 5% and the interval is unbounded.
DESCRIPTIVE tests (spec.inference == "none", the LobbyView tests: 2 sectors) report the estimate and the HC1 error as a
reference only, with the note that no inference is available; no bootstrap is run for them.
Fixed effects nested within clusters (H5 champion fixed effects, clusters = champions) are left out of the CR1
small-sample factor's parameter count (design.nested_fe), as for a within estimator; the bootstrap p-value and interval
do not depend on that factor (it scales t and every t* alike).
"""
from __future__ import annotations

import dataclasses
import itertools
import zlib
from dataclasses import dataclass, field

import numpy as np

from . import config
from .gates import full_rank_check, rank_of, year_level_check
from .sample import build_design, years_text

WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


@dataclass
class OLSFit:
    names: list
    beta: np.ndarray
    resid: np.ndarray
    A: np.ndarray  # (X'X)^-1
    n: int
    p: int
    G: int
    se_hc1: np.ndarray
    se_cr1: np.ndarray

    @property
    def df_resid(self):
        return self.n - self.p

    def coef(self, name):
        return float(self.beta[self.names.index(name)])


def ols(design) -> OLSFit:
    X, y = design.X, design.y
    n, p = X.shape
    Q, R = np.linalg.qr(X)
    beta = np.linalg.solve(R, Q.T @ y)
    Rinv = np.linalg.inv(R)
    A = Rinv @ Rinv.T
    u = y - X @ beta
    df = n - p
    Xu = X * u[:, None]
    if df > 0:
        V_hc1 = (n / df) * A @ (Xu.T @ Xu) @ A
        se_hc1 = np.sqrt(np.clip(np.diag(V_hc1), 0, None))
    else:
        se_hc1 = np.full(p, np.nan)
    G = int(design.clusters.max()) + 1 if n else 0
    if G > 1 and df > 0:
        S = np.zeros((G, p))
        np.add.at(S, design.clusters, Xu)
        c = cr1_factor(G, n, p, getattr(design, "nested_fe", 0))
        V_cr1 = c * A @ (S.T @ S) @ A
        se_cr1 = np.sqrt(np.clip(np.diag(V_cr1), 0, None))
    else:
        se_cr1 = np.full(p, np.nan)
    return OLSFit(names=list(design.names), beta=beta, resid=u, A=A, n=n, p=p, G=G, se_hc1=se_hc1, se_cr1=se_cr1)


def cr1_factor(G: int, n: int, p: int, nested_fe: int = 0) -> float:
    """CR1 small-sample factor G/(G-1) * (n-1)/(n-k), k = parameters minus fixed effects nested within clusters."""
    return G / (G - 1) * (n - 1) / (n - (p - nested_fe))


def seed_for(seed: int, *parts: str) -> np.random.SeedSequence:
    return np.random.SeedSequence([int(seed)] + [zlib.crc32(str(p).encode("utf-8")) for p in parts])


def webb_draws(G: int, B: int, rng: np.random.Generator):
    if 6 ** G <= B:
        return np.array(list(itertools.product(WEBB, repeat=G))), True
    return rng.choice(WEBB, size=(B, G)), False


class WCR:
    """Wild cluster restricted bootstrap for one coefficient of one design."""

    def __init__(self, design, fit: OLSFit, k: int, B: int, seed_seq: np.random.SeedSequence):
        X, y, cl = design.X, design.y, design.clusters
        n, p = X.shape
        G = fit.G
        self.G, self.k = G, k
        self.bk = float(fit.beta[k])
        A = fit.A
        q = X @ A[:, k]
        xk = X[:, k]
        Xmk = np.delete(X, k, axis=1)
        if Xmk.shape[1]:
            Qm, _ = np.linalg.qr(Xmk)
            r0 = y - Qm @ (Qm.T @ y)
            r1 = xk - Qm @ (Qm.T @ xk)
        else:
            r0, r1 = y.astype(float).copy(), xk.astype(float).copy()
        Qg = np.zeros((G, p))
        np.add.at(Qg, cl, X * q[:, None])
        QA = Qg @ A

        def parts(u):
            a = np.bincount(cl, weights=q * u, minlength=G)
            S = np.zeros((G, p))
            np.add.at(S, cl, X * u[:, None])
            C = np.diag(a) - QA @ S.T
            return a, C

        a0, C0 = parts(r0)
        a1, C1 = parts(r1)
        self.c = cr1_factor(G, n, p, getattr(design, "nested_fe", 0))
        uhat = fit.resid
        s = np.bincount(cl, weights=q * uhat, minlength=G)
        self.se = float(np.sqrt(self.c * np.sum(s ** 2)))
        rng = np.random.default_rng(seed_seq)
        V, self.enumerated = webb_draws(G, B, rng)
        self.draws = V.shape[0]
        self.N0, self.N1 = V @ a0, V @ a1
        D0, D1 = V @ C0.T, V @ C1.T
        self.s00 = np.sum(D0 * D0, axis=1)
        self.s01 = np.sum(D0 * D1, axis=1)
        self.s11 = np.sum(D1 * D1, axis=1)

    def tstat(self, b0: float) -> float:
        return (self.bk - b0) / self.se

    def tstar(self, b0: float) -> np.ndarray:
        num = self.N0 - b0 * self.N1
        den2 = np.maximum(self.c * (self.s00 - 2.0 * b0 * self.s01 + b0 * b0 * self.s11), 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            return num / np.sqrt(den2)

    def pvalue(self, b0: float = 0.0) -> float:
        t = abs(self.tstat(b0))
        ats = np.abs(self.tstar(b0))
        ats[np.isnan(ats)] = np.inf  # 0/0 draws count as extreme (conservative)
        return float(np.mean(ats >= t * (1.0 - 1e-9)))

    # Outward search limit: 2**20 (about a million) cluster-robust standard errors. Beyond it the interval is reported
    # as unbounded; the limit also keeps b0**2 terms clear of floating-point residue in the enumerated identity draw.
    MAX_STEP_EXP = 20

    def ci(self, alpha: float = config.ALPHA):
        step = self.se if (np.isfinite(self.se) and self.se > 0) else max(abs(self.bk), 1.0)

        def bound(direction):
            inside, outside = self.bk, None
            for e in range(-3, self.MAX_STEP_EXP + 1):
                x = self.bk + direction * step * (2.0 ** e)
                if self.pvalue(x) < alpha:
                    outside = x
                    break
                inside = x
            if outside is None:
                return direction * np.inf
            for _ in range(200):
                mid = 0.5 * (inside + outside)
                if self.pvalue(mid) < alpha:
                    outside = mid
                else:
                    inside = mid
                if abs(outside - inside) <= 1e-7 * step:
                    break
            return 0.5 * (inside + outside)

        return bound(-1.0), bound(1.0)


def unit_of(coef: str, spec) -> str:
    dv_u = "log points" if spec.variant == "log" else "$M 2025"
    base = coef.split(":")[0]
    if base in ("growth_previous_year_pct", "growth_same_year_pct", "predicted_growth_pct"):
        if ":" in coef:
            return f"difference from the Employee slope, {dv_u} per percentage point of growth"
        return f"{dv_u} per percentage point of growth"
    return {
        "pres_year": f"{dv_u}, presidential-election year vs odd year",
        "midterm_year": f"{dv_u}, midterm year vs odd year",
        "exp_dem_house": f"{dv_u} per unit (0-1) of expected Democratic House control",
        "exp_dem_senate": f"{dv_u} per unit (0-1) of expected Democratic Senate control",
        "exp_shift_house": f"{dv_u} per unit of expected-minus-current Democratic House control",
        "exp_shift_senate": f"{dv_u} per unit of expected-minus-current Democratic Senate control",
        "cur_dem_house": f"{dv_u}, Democratic vs Republican House",
        "cur_dem_senate": f"{dv_u}, Democratic vs Republican Senate",
        "pred_dem_seat_change_house": f"{dv_u} per predicted Democratic House seat gained",
        "pred_dem_seat_change_senate": f"{dv_u} per predicted Democratic Senate seat gained",
    }.get(coef, f"{dv_u} per unit of {coef}")


def boot_coefficient(design, fit, name, B, seed_seq, alpha=config.ALPHA) -> dict:
    k = fit.names.index(name)
    out = {"coefficient": name, "estimate": float(fit.beta[k]), "hc1_se": float(fit.se_hc1[k]),
           "cr1_se": float(fit.se_cr1[k])}
    if fit.G < 2 or not np.isfinite(fit.se_cr1[k]) or fit.se_cr1[k] <= 0:
        out.update(boot_p=np.nan, ci_low=np.nan, ci_high=np.nan, boot_draws=0, boot_enumerated=None,
                   boot_note="bootstrap not computable (fewer than 2 clusters or zero cluster-robust variance)")
        return out
    w = WCR(design, fit, k, B, seed_seq)
    lo, hi = w.ci(alpha)
    out.update(t_cr1=w.tstat(0.0), boot_p=w.pvalue(0.0), ci_low=lo, ci_high=hi, boot_draws=w.draws,
               boot_enumerated=w.enumerated, boot_note="")
    if not np.isfinite(lo) or not np.isfinite(hi):
        if w.enumerated and 2 / w.draws >= alpha:
            out["boot_note"] = (f"interval unbounded: with G={fit.G} clusters the smallest attainable p is "
                                f"{2 / w.draws:.4f} >= {alpha}, so no value can be rejected")
        else:
            out["boot_note"] = (f"interval unbounded on at least one side (no rejection within "
                                f"2^{WCR.MAX_STEP_EXP} cluster-robust standard errors)")
    return out


def fit_strata(sample_df, spec, coef_names) -> list:
    rows = []
    for s in sorted(sample_df["study_sector"].unique(), key=lambda v: config.STUDY_SECTORS.index(v)
                    if v in config.STUDY_SECTORS else 99):
        sub = sample_df[sample_df["study_sector"] == s]
        d = build_design(sub, spec)
        r = rank_of(d.X)
        base = {"study_sector": s, "n": d.n, "years": years_text(sub["year"]), "resid_df": d.n - d.p}
        if r < d.p:
            for c in coef_names:
                rows.append({**base, "coefficient": c, "status": "insufficient",
                             "reason": f"rank {r} < {d.p} parameters within the sector"})
            continue
        if d.n - d.p < config.MIN_STRATUM_RESID_DF:
            for c in coef_names:
                rows.append({**base, "coefficient": c, "status": "insufficient",
                             "reason": f"residual df {d.n - d.p} < {config.MIN_STRATUM_RESID_DF}"})
            continue
        f = ols(d)
        for c in coef_names:
            if c in f.names:
                k = f.names.index(c)
                rows.append({**base, "coefficient": c, "status": "estimated", "estimate": float(f.beta[k]),
                             "hc1_se": float(f.se_hc1[k]), "reason": ""})
            else:
                rows.append({**base, "coefficient": c, "status": "insufficient", "reason": "term absent in sector"})
    return rows


def stratification_label(strata_rows, coef) -> str:
    rel = [r for r in strata_rows if r["coefficient"] == coef]
    est = [r for r in rel if r["status"] == "estimated"]
    if est:
        return f"STRATIFIED: {len(est)} of {len(rel)} sectors estimated"
    if not rel:
        return "UNSTRATIFIED: no strata computed"
    return "UNSTRATIFIED: no sector has a sector-only estimate (" + rel[0]["reason"] + ")"


@dataclass
class TestResult:
    coefs: list = field(default_factory=list)
    strata: list = field(default_factory=list)
    subfits: list = field(default_factory=list)
    notes: list = field(default_factory=list)


def descriptive_note(G: int) -> str:
    """The DESCRIPTIVE note: the smallest p the enumerated wild cluster bootstrap can reach with G clusters."""
    return f"{G} sectors: wild cluster bootstrap cannot reach p < {2 / 6 ** G:.3f}; inference not available"


def descriptive_coefficient(fit, name) -> dict:
    k = fit.names.index(name)
    return {"coefficient": name, "estimate": float(fit.beta[k]), "hc1_se": float(fit.se_hc1[k]), "cr1_se": np.nan,
            "t_cr1": np.nan, "boot_p": np.nan, "ci_low": np.nan, "ci_high": np.nan, "boot_draws": 0,
            "boot_enumerated": None, "boot_note": descriptive_note(fit.G),
            "inference": "none (DESCRIPTIVE): estimate and HC1 error (reference only)"}


def estimate(spec, attempt, B=config.BOOT_B, seed=config.SEED, alpha=config.ALPHA, extra_coefs=()) -> TestResult:
    """Fit an ESTIMABLE test on its gated sample (attempt = the passing gates.Attempt)."""
    res = TestResult()
    smp, design = attempt.sample, attempt.design
    if spec.variant in ("loso", "loyo"):
        return leave_one_out(spec, attempt, B, seed, alpha)
    fit = ols(design)
    if spec.inference == "none":
        names = list(spec.focal)
        res.strata = fit_strata(smp.df, spec, names)
        for c in names:
            row = descriptive_coefficient(fit, c)
            row.update(unit=unit_of(c, spec), focal=True, stratification=stratification_label(res.strata, c))
            res.coefs.append(row)
        res.notes.append(descriptive_note(fit.G))
        return res
    names = list(spec.focal) + [c for c in extra_coefs if c in fit.names and c not in spec.focal]
    res.strata = fit_strata(smp.df, spec, names) if spec.variant != "year_fe" else [
        {"study_sector": s, "coefficient": c, "status": "insufficient", "n": None, "years": "", "resid_df": None,
         "reason": "year fixed effects leave no within-sector variation in a sector-only regression"}
        for s in smp.sectors for c in names]
    for c in names:
        row = boot_coefficient(design, fit, c, B, seed_for(seed, spec.id, c), alpha)
        by = "Mentat industry" if spec.table == "industry_year" else "sector"
        row.update(unit=unit_of(c, spec), focal=c in spec.focal, inference=f"wild cluster restricted bootstrap by {by}",
                   stratification=stratification_label(res.strata, c))
        res.coefs.append(row)
    return res


def leave_one_out(spec, attempt, B, seed, alpha) -> TestResult:
    res = TestResult()
    lspec = dataclasses.replace(spec, variant="level")
    df = attempt.sample.df
    col = "study_sector" if spec.variant == "loso" else "year"
    units = attempt.sample.sectors if spec.variant == "loso" else attempt.sample.years
    for u in units:
        sub = df[df[col] != u]
        yrs = sorted(sub["year"].unique())
        secs = sorted(sub["study_sector"].unique())
        info = {"left_out": str(u), "n": len(sub), "n_sectors": len(secs), "n_years": len(yrs),
                "years": years_text(yrs)}
        why = []
        if len(secs) < config.MIN_SECTORS:
            why.append(f"{len(secs)} sector(s) left")
        d = build_design(sub, lspec) if len(sub) else None
        if d is not None:
            ok_y, wy = year_level_check(d)
            ok_r, wr, r = full_rank_check(d)
            if not ok_y:
                why.append(wy)
            if not ok_r:
                why.append(wr)
            if d.n - r < config.MIN_RESID_DF:
                why.append(f"residual df {d.n - r} < {config.MIN_RESID_DF}")
        else:
            why.append("empty")
        flag = ""
        if len(yrs) < attempt.min_years:
            flag = f"diagnostic: {len(yrs)} years < the {attempt.min_years}-year minimum of the gated window"
        if why:
            for c in spec.focal:
                res.subfits.append({**info, "coefficient": c, "status": "not estimable", "reason": "; ".join(why),
                                    "flag": flag})
            continue
        fit = ols(d)
        for c in spec.focal:
            row = boot_coefficient(d, fit, c, B, seed_for(seed, spec.id, c, str(u)), alpha)
            row.update(info)
            row.update(status="estimated", reason="", flag=flag, unit=unit_of(c, lspec),
                       stratification="UNSTRATIFIED: leave-one-out sub-fit")
            res.subfits.append(row)
    return res
