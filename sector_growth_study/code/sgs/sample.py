"""Complete-case estimation samples and design matrices.

A value is usable when it is present and its status is observed (or 'derived'); partial rows and the partial
calendar year (2026) never enter unless include_partial is set. Nothing is imputed, recoded or silently dropped:
every excluded row is counted by reason, and the inputs that block whole years or whole sectors are named.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config
from .panel import STATUS_OF, USABLE_STATUSES

SECTOR_ORDER = {s: i for i, s in enumerate(config.STUDY_SECTORS)}


def years_text(years) -> str:
    """Compact year list: 2016-2019, 2021, 2023-2025."""
    ys = sorted({int(y) for y in years})
    if not ys:
        return "none"
    parts, start, prev = [], ys[0], ys[0]
    for y in ys[1:] + [None]:
        if y is not None and y == prev + 1:
            prev = y
            continue
        parts.append(f"{start}" if start == prev else f"{start}-{prev}")
        if y is not None:
            start = prev = y
    return ", ".join(parts)


@dataclass
class Sample:
    df: pd.DataFrame
    window: tuple
    candidate_rows: int
    exclusions: dict = field(default_factory=dict)
    diagnosis: list = field(default_factory=list)  # human-readable blockers (inputs x years / sectors)
    notes: list = field(default_factory=list)
    items: list = field(default_factory=list)  # structured blockers (diagnose_items)

    @property
    def n(self):
        return len(self.df)

    @property
    def years(self):
        return sorted(self.df["year"].unique().tolist()) if len(self.df) else []

    @property
    def sectors(self):
        return sorted(self.df["study_sector"].unique().tolist(), key=lambda s: SECTOR_ORDER.get(s, 99)) if len(self.df) else []


def _usable(frame: pd.DataFrame, var: str) -> pd.Series:
    ok = frame[var].notna()
    st = STATUS_OF.get(var)
    if st and st in frame.columns:
        ok &= frame[st].isin(USABLE_STATUSES)
    return ok


def build_sample(tables: dict, spec, window: tuple, include_partial: bool = False) -> Sample:
    tab = tables[spec.table]
    if spec.tiers is not None:
        tab = tab[tab["tier"].isin(spec.tiers)]
    lo, hi = window
    need = list(spec.required_vars)
    first = lo - 1 if spec.variant == "fd" else lo
    frame = tab[(tab["year"] >= first) & (tab["year"] <= hi)].copy()
    notes, excl = [], {}
    if not include_partial:
        part = frame["partial_year"].astype(bool)
        if part.any():
            excl["partial calendar year (2026)"] = int(part[frame["year"] >= lo].sum())
        frame = frame[~part]
    if spec.year_filter == "election_years":
        odd = frame["year"] % 2 == 1
        notes.append(f"election years only: {int(odd[frame['year'] >= lo].sum())} odd-year rows outside the design")
        frame = frame[~odd]
    keys = ["study_sector", "year"] + (["tier"] if "tier" in frame.columns and spec.table == "sector_year_tier" else [])
    ok = pd.DataFrame({v: _usable(frame, v) for v in need}, index=frame.index)
    if spec.variant == "fd":
        # Difference of consecutive calendar years within sector (and tier): the row for year t pairs with the row
        # for t-1; both levels must be usable. The lag year may precede the window.
        cur = pd.concat([frame[keys + need], ok.add_prefix("ok__")], axis=1)
        lag = cur.copy()
        lag["year"] = lag["year"] + 1
        m = cur.merge(lag, on=keys, how="left", suffixes=("", "__lag"))
        d = m[keys].copy()
        okd = pd.DataFrame(index=m.index)
        for v in need:
            d[v] = m[v].astype(float) - m[v + "__lag"].astype(float)
            okd[v] = m["ok__" + v].eq(True) & m["ok__" + v + "__lag"].eq(True)
        in_win = d["year"] >= lo
        frame, ok = d[in_win], okd[in_win]
    cand = len(frame)
    complete = ok.all(axis=1)
    for v in need:
        miss = int((~ok[v]).sum())
        if miss:
            excl[f"{v} unusable"] = miss
    df = frame[complete].copy()
    if spec.variant == "log":
        pos = df[spec.dv] > 0
        nz, nn = int((df[spec.dv] == 0).sum()), int((df[spec.dv] < 0).sum())
        if nz or nn:
            excl[f"{spec.dv} <= 0 (log variant; zeros {nz}, negatives {nn})"] = nz + nn
            notes.append(f"log variant: {nz} zero and {nn} negative {spec.dv} rows excluded, not altered")
        df = df[pos]
        df["y"] = np.log(df[spec.dv].astype(float))
    else:
        df["y"] = df[spec.dv].astype(float)
    df = df.sort_values(keys, key=lambda s: s.map(SECTOR_ORDER) if s.name == "study_sector" else s).reset_index(drop=True)
    smp = Sample(df=df, window=window, candidate_rows=cand, exclusions=excl, notes=notes)
    smp.items = diagnose_items(frame, ok, need, window)
    smp.diagnosis = diagnosis_text(smp.items)
    return smp


def diagnose_items(frame: pd.DataFrame, ok: pd.DataFrame, need, window) -> list:
    """Structured blockers: inputs absent for every sector in some years, years lost to scattered gaps, and
    sectors without any complete row."""
    items = []
    if not len(frame):
        return [{"kind": "empty", "window": window}]
    years = sorted(frame["year"].unique())
    complete = ok.all(axis=1)
    kept_years = set(frame.loc[complete, "year"])
    for v in need:
        none_years = [int(y) for y in years if not ok.loc[frame["year"] == y, v].any()]
        if none_years:
            items.append({"kind": "var_years", "var": v, "years": none_years})
    for y in [y for y in years if y not in kept_years]:
        if not any(not ok.loc[frame["year"] == y, v].any() for v in need):
            m = frame["year"] == y
            gaps = {v: int((~ok.loc[m, v]).sum()) for v in need if (~ok.loc[m, v]).any()}
            items.append({"kind": "year_scattered", "year": int(y), "rows": int(m.sum()), "gaps": gaps})
    for s in sorted(frame["study_sector"].unique(), key=lambda s: SECTOR_ORDER.get(s, 99)):
        m = frame["study_sector"] == s
        if not complete[m].any():
            items.append({"kind": "sector", "sector": s, "vars": [v for v in need if not ok.loc[m, v].any()]})
    return items


def diagnosis_text(items) -> list:
    out = []
    for it in items:
        if it["kind"] == "empty":
            out.append(f"no candidate rows in {it['window'][0]}-{it['window'][1]}")
        elif it["kind"] == "var_years":
            out.append(f"{it['var']}: no usable value for any sector in {years_text(it['years'])}")
        elif it["kind"] == "year_scattered":
            gaps = ", ".join(f"{v} ({k} of {it['rows']} rows)" for v, k in it["gaps"].items())
            out.append(f"{it['year']}: no row complete; gaps {gaps}")
        elif it["kind"] == "sector":
            if it["vars"]:
                out.append(f"sector {it['sector']} never complete: {', '.join(it['vars'])} unusable throughout")
            else:
                out.append(f"sector {it['sector']} never complete: gaps do not line up in any year")
    return out


def diagnose(frame: pd.DataFrame, ok: pd.DataFrame, need, window, spec) -> list:
    """Name the inputs that block years and sectors of the window (text)."""
    return diagnosis_text(diagnose_items(frame, ok, need, window))


@dataclass
class Design:
    y: np.ndarray
    X: np.ndarray
    names: list
    clusters: np.ndarray  # integer cluster (sector) index per row
    cluster_labels: list
    years: np.ndarray
    national: list  # names of year-level regressors in X
    intercept_spanned: bool  # fixed effects span the constant (False for first differences)
    nested_fe: int = 0  # fixed-effect columns nested within clusters (H5 champion FE); CR1 factor leaves them out

    @property
    def n(self):
        return self.X.shape[0]

    @property
    def p(self):
        return self.X.shape[1]


def build_design(df: pd.DataFrame, spec) -> Design:
    cols, names = [], []
    if spec.variant == "tier":
        for v, tier in spec.interactions:
            if v not in names:
                cols.append(df[v].to_numpy(float))
                names.append(v)
        for v, tier in spec.interactions:
            cols.append(df[v].to_numpy(float) * (df["tier"] == tier).to_numpy(float))
            names.append(f"{v}:{tier}")
        for c in spec.controls:
            cols.append(df[c].to_numpy(float))
            names.append(c)
    else:
        for c in spec.raw_regressors:
            cols.append(df[c].to_numpy(float))
            names.append(c)
    sectors = sorted(df["study_sector"].unique(), key=lambda s: SECTOR_ORDER.get(s, 99))
    if "sector" in spec.fe:
        for s in sectors:
            cols.append((df["study_sector"] == s).to_numpy(float))
            names.append(f"FE:{s}")
    if "sector_x_tier" in spec.fe:
        for s in sectors:
            for t in config.TIERS:
                m = ((df["study_sector"] == s) & (df["tier"] == t)).to_numpy(float)
                if m.any():
                    cols.append(m)
                    names.append(f"FE:{s}|{t}")
    if "year" in spec.fe:
        ys = sorted(df["year"].unique())
        for y in ys[1:]:
            cols.append((df["year"] == y).to_numpy(float))
            names.append(f"YFE:{y}")
    X = np.column_stack(cols) if cols else np.zeros((len(df), 0))
    cl = np.array([sectors.index(s) for s in df["study_sector"]], dtype=int)
    national = [n for n in names if n in config.NATIONAL_VARS]
    return Design(y=df["y"].to_numpy(float), X=X, names=names, clusters=cl, cluster_labels=list(sectors),
                  years=df["year"].to_numpy(int), national=national, intercept_spanned=bool(spec.fe))
