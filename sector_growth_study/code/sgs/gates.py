"""Estimability gates of the sector-year tests (Paul's rule R8) and the primary-then-fallback window decision.

A test is ESTIMABLE in a window only if its complete-case sample has
  * at least `min_years` distinct years (6 in the primary window; the fallback window is 10 consecutive years),
  * at least 2 sectors (every sector with complete data enters; none is selected out),
  * a full-column-rank design, with the year-level (national) regressors checked separately against the number
    of distinct years (sector baselines span a common level, so K national regressors need K + 1 independent years),
  * residual degrees of freedom of at least 3.
The primary window (2020-2025) is tried first. Only when it fails, the fallback window is searched for: the most recent
run of at least 10 consecutive calendar years within 2008-2025 in which the test's complete-case sample exists; the
window used is that run's most recent 10 years (config.FALLBACK_WHOLE_RUN = True uses the whole run). The search, the
runs found and the window used are recorded on the Decision (fallback_search).
H5 (champions) has its own member-cycle gate in champions.py; this module does not gate it.
PREVIEW tests (spec.gate == "preview") are gated on the fixed window config.PREVIEW_WINDOW (2021-2025) with
config.PREVIEW_MIN_YEARS (5) distinct years and no fallback; their full core specification is also NOT IDENTIFIED when
its year-level parameters are as many as the distinct years (saturation_check).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config
from .panel import NotBuilt, build_dem_share
from .sample import Design, Sample, build_design, build_sample, years_text

ESTIMABLE, NOT_ESTIMABLE, NOT_BUILT = "ESTIMABLE", "NOT ESTIMABLE", "NOT BUILT"


def _normalised(M: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(M, axis=0)
    norms[norms == 0] = 1.0
    return M / norms


def rank_of(M: np.ndarray) -> int:
    if M.size == 0:
        return 0
    return int(np.linalg.matrix_rank(_normalised(np.asarray(M, float))))


def dependent_columns(M: np.ndarray, names: list, order: list | None = None) -> list:
    """Columns (in `order`) that add no rank given the columns kept before them."""
    order = order if order is not None else list(range(M.shape[1]))
    kept, dep, r = [], [], 0
    for j in order:
        r2 = rank_of(M[:, kept + [j]])
        if r2 > r:
            kept.append(j)
            r = r2
        else:
            dep.append(names[j])
    return dep


def check_order(design: Design) -> list:
    """Fixed effects first, then controls, then focal-like columns last, so non-identification is attributed to
    the regressors rather than to the baselines."""
    fe = [i for i, n in enumerate(design.names) if n.startswith(("FE:", "YFE:"))]
    nat = [i for i, n in enumerate(design.names) if n in design.national]
    rest = [i for i in range(len(design.names)) if i not in fe and i not in nat]
    return fe + nat + rest


def year_level_check(design: Design) -> tuple:
    if not design.national:
        return True, ""
    idx = [design.names.index(n) for n in design.national]
    Z = pd.DataFrame(design.X[:, idx], columns=design.national)
    Z["year"] = design.years
    Zy = Z.groupby("year").first()
    names = list(design.national)
    M = Zy.to_numpy(float)
    if design.intercept_spanned:
        M = np.column_stack([np.ones(len(Zy)), M])
        names = ["common level of the sector baselines"] + names
    k, t = M.shape[1], M.shape[0]
    r = rank_of(M)
    if r == k:
        return True, ""
    dep = dependent_columns(M, names)
    yrs = years_text(Zy.index)
    return False, (f"year-level design not identified: {k} year-level parameters ({', '.join(names)}) on "
                   f"{t} distinct years ({yrs}), rank {r}; not identified: {', '.join(dep)}")


def full_rank_check(design: Design) -> tuple:
    r = rank_of(design.X)
    if r == design.p:
        return True, "", r
    dep = dependent_columns(design.X, design.names, check_order(design))
    return False, f"design rank {r} < {design.p} columns; not identified: {', '.join(dep)}", r


@dataclass
class Attempt:
    kind: str
    window: tuple
    min_years: int
    ok: bool
    reasons: list
    n: int
    years: list
    sectors: list
    resid_df: int | None
    sample: Sample | None = field(default=None, repr=False)
    design: Design | None = field(default=None, repr=False)
    compact_parts: list = field(default_factory=list)
    search: str = ""  # fallback only: the run search that produced (or failed to produce) this window
    is_search: bool = False  # True when no qualifying run was found: `window` is then the searched span

    def compact(self) -> str:
        w = f"{self.window[0]}-{self.window[1]}"
        if self.ok:
            return f"{self.kind} {w}: passes"
        if self.is_search:
            return f"fallback search {w}: " + "; ".join(self.compact_parts)
        return f"{self.kind} {w}: " + "; ".join(self.compact_parts)

    def text(self) -> str:
        w = f"{self.window[0]}-{self.window[1]}"
        if self.is_search:
            return f"fallback search {w} (needs a run of >= {self.min_years} consecutive years): " + "; ".join(self.reasons)
        need = (f"needs >= {self.min_years} years" if self.kind != "fallback"
                else f"most recent run of >= {self.min_years} consecutive complete-case years; {self.search}")
        if self.ok:
            return f"{self.kind} {w}: passes (n={self.n}, {len(self.sectors)} sectors, {len(self.years)} years)" + (
                f" [{self.search}]" if self.search else "")
        return f"{self.kind} {w} ({need}): " + "; ".join(self.reasons)


def assess(sample: Sample, spec, min_years: int, kind: str = "default", check_years: bool = True) -> Attempt:
    reasons = []
    years, sectors = sample.years, sample.sectors
    design, resid_df = None, None
    short = False
    if sample.n == 0:
        reasons.append("complete-case sample is empty")
        short = True
    else:
        if check_years and len(years) < min_years:
            reasons.append(f"{len(years)} distinct years ({years_text(years)}) < {min_years} required")
            short = True
        if len(sectors) < config.MIN_SECTORS:
            reasons.append(f"{len(sectors)} sector(s) ({', '.join(sectors)}) < {config.MIN_SECTORS} required")
            short = True
        design = build_design(sample.df, spec)
        ok_y, why_y = year_level_check(design)
        if not ok_y:
            reasons.append(why_y)
        ok_r, why_r, r = full_rank_check(design)
        if not ok_r:
            reasons.append(why_r)
        resid_df = design.n - r
        if resid_df < config.MIN_RESID_DF:
            reasons.append(f"residual df {resid_df} < {config.MIN_RESID_DF}")
    if short and sample.diagnosis:
        reasons.append("blocking inputs: " + "; ".join(sample.diagnosis))
    compact = []
    if reasons:
        if sample.n == 0:
            compact.append("empty complete-case sample")
        else:
            if check_years and len(years) < min_years:
                compact.append(f"{len(years)} of {min_years} years ({years_text(years)})")
            if len(sectors) < config.MIN_SECTORS:
                compact.append(f"{len(sectors)} sector(s)")
            for r in reasons:
                if r.startswith("year-level design not identified"):
                    compact.append("year-level terms not identified: " + r.split("; not identified: ")[-1])
                elif r.startswith("design rank") and not any(c.startswith("year-level") for c in compact):
                    compact.append("not identified: " + r.split("; not identified: ")[-1])
                elif r.startswith("residual df"):
                    compact.append(r.replace("residual df", "resid df"))
        if short:
            compact += _gap_parts(sample)
    return Attempt(kind=kind, window=sample.window, min_years=min_years, ok=not reasons, reasons=reasons,
                   n=sample.n, years=years, sectors=sectors, resid_df=resid_df, sample=sample, design=design,
                   compact_parts=compact)


def _gap_parts(sample: Sample) -> list:
    out = []
    gaps = [f"{it['var']} {years_text(it['years'])}" for it in sample.items if it["kind"] == "var_years"]
    if gaps:
        out.append("no sector has " + ", ".join(gaps))
    never = [it["sector"] for it in sample.items if it["kind"] == "sector"]
    if never:
        out.append("never complete: " + ", ".join(never))
    return out


@dataclass
class Decision:
    status: str
    window: tuple | None = None
    window_kind: str | None = None
    attempts: list = field(default_factory=list)
    reason: str = ""
    fallback_search: str = ""  # the fallback run search (blank when the primary window passed or no fallback)

    @property
    def chosen(self) -> Attempt | None:
        for a in self.attempts:
            if a.ok:
                return a
        return None


def sample_spec(spec):
    """Leave-one-out tests are gated on their parent (level) sample."""
    if spec.variant in ("loso", "loyo"):
        return dataclasses.replace(spec, variant="level")
    return spec


def year_runs(years) -> list:
    """Maximal runs of consecutive calendar years, oldest first."""
    runs = []
    for y in sorted({int(v) for v in years}):
        if runs and y == runs[-1][-1] + 1:
            runs[-1].append(y)
        else:
            runs.append([y])
    return runs


def _runs_text(runs) -> str:
    if not runs:
        return "none"
    return ", ".join(f"{r[0]}-{r[-1]} ({len(r)} years)" if len(r) > 1 else f"{r[0]} (1 year)" for r in runs)


def fallback_window(tables: dict, sspec, search: tuple, include_partial: bool = False,
                    min_years: int = config.MIN_YEARS_FALLBACK, whole_run: bool = config.FALLBACK_WHOLE_RUN):
    """Search `search` for the most recent run of >= min_years consecutive calendar years with a complete-case sample.
    Returns (window or None, the complete-case sample of the searched span, a text record of the search)."""
    smp = build_sample(tables, sspec, search, include_partial=include_partial)
    runs = year_runs(smp.years)
    qualifying = [r for r in runs if len(r) >= min_years]
    head = (f"complete-case years in {search[0]}-{search[1]}: {years_text(smp.years)}; "
            f"runs of consecutive years: {_runs_text(runs)}")
    if not qualifying:
        return None, smp, head + f"; no run of >= {min_years} consecutive years"
    run = qualifying[-1]
    window = (run[0], run[-1]) if whole_run else (run[-1] - min_years + 1, run[-1])
    how = "the whole run" if whole_run else f"its most recent {min_years} years"
    return window, smp, (head + f"; most recent run of >= {min_years}: {run[0]}-{run[-1]}; window used: {how}, "
                                f"{window[0]}-{window[1]}")


def _no_run_attempt(smp: Sample, search: tuple, min_years: int, search_txt: str) -> Attempt:
    reasons = [f"no run of >= {min_years} consecutive calendar years with a complete-case sample ({search_txt})"]
    if smp.diagnosis:
        reasons.append("blocking inputs: " + "; ".join(smp.diagnosis))
    compact = [f"no run of >= {min_years} consecutive complete-case years (complete-case years "
               f"{years_text(smp.years)})"] + _gap_parts(smp)
    return Attempt(kind="fallback", window=tuple(search), min_years=min_years, ok=False, reasons=reasons, n=smp.n,
                   years=smp.years, sectors=smp.sectors, resid_df=None, sample=smp, design=None, compact_parts=compact,
                   search=search_txt, is_search=True)


def saturation_check(design: Design) -> tuple:
    """PREVIEW full core specification: (ok, reason). NOT IDENTIFIED when the year-level parameters (the common level of
    the sector baselines plus the national regressors) are at least as many as the distinct years: the national terms
    then saturate the years (no year-level residual variation; they span the year fixed effects), so their coefficients
    carry no information beyond the year means. The test is reported, not forced."""
    if not design.national:
        return True, ""
    names = (["common level of the sector baselines"] if design.intercept_spanned else []) + list(design.national)
    k, t = len(names), len({int(y) for y in design.years})
    if k >= t:
        return False, (f"NOT IDENTIFIED: {k} year-level parameters ({', '.join(names)}) on {t} distinct years "
                       f"({years_text(design.years)}): the national terms saturate the years (no year-level residual "
                       "variation; equivalent to year fixed effects); not forced")
    return True, ""


def decide_preview(spec, tables: dict, include_partial: bool = False) -> Decision:
    """PREVIEW gate: the fixed window config.PREVIEW_WINDOW with >= config.PREVIEW_MIN_YEARS distinct years and the
    other R8 checks; no fallback; plus the saturation check for the full core specification."""
    win = tuple(config.PREVIEW_WINDOW)
    sspec = sample_spec(spec)
    smp = build_sample(tables, sspec, win, include_partial=include_partial)
    att = assess(smp, sspec, config.PREVIEW_MIN_YEARS, kind="preview")
    if spec.saturation_check and att.design is not None:
        ok_s, why_s = saturation_check(att.design)
        if not ok_s:
            att.reasons.insert(0, why_s)
            k = why_s.split(" year-level parameters")[0].replace("NOT IDENTIFIED: ", "")
            att.compact_parts.insert(0, f"NOT IDENTIFIED: {k} year-level parameters on {len(att.years)} distinct years "
                                        "(national terms saturate the years; not forced)")
            att.ok = False
    if att.ok:
        return Decision(status=ESTIMABLE, window=win, window_kind="preview", attempts=[att])
    return Decision(status=NOT_ESTIMABLE, attempts=[att], reason=att.text())


def decide(spec, tables: dict, default_window=config.DEFAULT_WINDOW, fallback_search=config.FALLBACK_SEARCH,
           include_partial: bool = False, whole_run: bool = config.FALLBACK_WHOLE_RUN) -> Decision:
    """Primary window first; if it fails and fallback_search is not None, the flexible fallback window.
    PREVIEW tests (spec.gate == "preview") use decide_preview: the fixed PREVIEW window, never a fallback."""
    if spec.variant == "not_built":
        try:
            build_dem_share()
        except NotBuilt as exc:
            return Decision(status=NOT_BUILT, reason=f"NotBuilt: {exc}")
    if getattr(spec, "gate", "r8") == "preview":
        return decide_preview(spec, tables, include_partial=include_partial)
    sspec = sample_spec(spec)
    smp = build_sample(tables, sspec, default_window, include_partial=include_partial)
    att = assess(smp, sspec, config.MIN_YEARS_DEFAULT, kind="default")
    attempts = [att]
    if att.ok:
        return Decision(status=ESTIMABLE, window=tuple(default_window), window_kind="default", attempts=attempts)
    if fallback_search is None:
        return Decision(status=NOT_ESTIMABLE, attempts=attempts, reason=" || ".join(a.text() for a in attempts))
    window, ssmp, search_txt = fallback_window(tables, sspec, fallback_search, include_partial,
                                               config.MIN_YEARS_FALLBACK, whole_run)
    if window is None:
        attempts.append(_no_run_attempt(ssmp, fallback_search, config.MIN_YEARS_FALLBACK, search_txt))
    else:
        fsmp = build_sample(tables, sspec, window, include_partial=include_partial)
        fatt = assess(fsmp, sspec, config.MIN_YEARS_FALLBACK, kind="fallback")
        fatt.search = search_txt
        attempts.append(fatt)
        if fatt.ok:
            return Decision(status=ESTIMABLE, window=tuple(window), window_kind="fallback", attempts=attempts,
                            fallback_search=search_txt)
    return Decision(status=NOT_ESTIMABLE, attempts=attempts, reason=" || ".join(a.text() for a in attempts),
                    fallback_search=search_txt)
