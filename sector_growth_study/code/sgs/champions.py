"""H5: champions' race toughness and industry money (05_industry_champions.xlsx, sheet `data`).

Unit: board x champion x cycle.

Loading happens at run time only (never cached). Every H5 test is NOT BUILT, with the reason, when
  * 05_industry_champions.xlsx or build_receipt_05.json (study folder) is missing,
  * the receipt or the workbook was written less than config.CHAMPIONS_QUIET_MINUTES (10) minutes ago (05 is being
    rewritten), or either changed while being read,
  * the bytes read differ from the sha256 the receipt records for 05,
  * the workbook fails validation (unreadable, formula-like cell, duplicate key board x bioguide x cycle),
  * an expected column (config.H5_REQUIRED, or every dependent-variable candidate) is missing.
A single test is NOT BUILT when only its own column is missing (the sensitivity DV, a secondary regressor).
The workbook is read into memory in one call and parsed from memory: no handle stays open on a file that another
lane may be replacing.

Dependent variable: industry_money_primary_real_2025_usd if 05 has it, else direct_giving_real_2025_usd, labelled
"employee channel only". Sensitivity DV: industry_money_with_trade_real_2025_usd if present.
Sample: up_for_election = 1 (retiring rows carry 0 there, so that flag excludes them); lost_primary = 1 rows only in
the primary models (spec.keep_lost_primary). A DV value enters only where the row status is observed or partial and
the DV's own status column (e.g. direct_giving_status), when there is one, is observed or observed_zero:
'no_authorized_committee' zeros are 0 by construction, not observations (counted and excluded); 2020 money is missing.
Design: focal regressor; controls chamber (Senate vs House), party (each other party vs R), seniority_years; cycle
fixed effects; board fixed effects; H5-within adds champion (bioguide) fixed effects. Columns that add no rank given
the fixed effects (e.g. chamber or party inside champion fixed effects) are dropped and named; a focal regressor
that adds no rank is not identified.
Gate (member-cycle based, not the 6-year sector-year gate): >= 3 cycles, >= 30 member-cycles (distinct bioguide x
cycle), non-zero variance of the focal regressor (within champion for H5-within), focal identified, residual df >= 3,
>= 2 champion clusters.
Inference: OLS; HC1 (reference only); CR1 by champion (champion fixed effects, nested in the clusters, are left out of
the small-sample factor's parameter count); wild cluster restricted bootstrap by champion (Webb weights), 95%
interval by test inversion. Strata: the same model fitted within each board (house rule: strata or UNSTRATIFIED).
"""
from __future__ import annotations

import collections
import dataclasses
import datetime as _dt
import hashlib
import io
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from . import config, load
from .estimate import TestResult, boot_coefficient, ols, seed_for
from .gates import ESTIMABLE, NOT_BUILT, NOT_ESTIMABLE, dependent_columns, rank_of
from .sample import Design

UNIT = "board x champion x cycle"


def _utc(ts: float) -> str:
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cycles_text(cycles) -> str:
    cs = sorted({int(c) for c in cycles})
    return ", ".join(str(c) for c in cs) if cs else "none"


@dataclass
class ChampionsData:
    ok: bool
    reason: str = ""
    frame: pd.DataFrame | None = None
    source: dict | None = None
    notes: list = field(default_factory=list)
    documented: set = field(default_factory=set)  # columns the 05 dictionary documents for sheet `data`

    @property
    def columns(self) -> set:
        return set(self.frame.columns) if self.frame is not None else set()


def load_champions(data_dir=None, now: float | None = None,
                   quiet_minutes: float = config.CHAMPIONS_QUIET_MINUTES) -> ChampionsData:
    data_dir = Path(data_dir or config.DATA_DIR)
    path = data_dir / config.CHAMPIONS_FILE
    rpath = data_dir.parent / config.CHAMPIONS_RECEIPT
    now = time.time() if now is None else now
    rec = dict(file=path.name, workbook="champions", absolute_path=str(path), sha256=None, size_bytes=None,
               mtime_utc=None, read_at_utc=_utc(now), sheets_read="", rows_read="", note="")

    def not_built(reason):
        rec["note"] = "NOT BUILT: " + reason
        return ChampionsData(ok=False, reason=reason, source=rec)

    if not path.exists():
        return not_built(f"{path.name} not found at {path}")
    if not rpath.exists():
        return not_built(f"{rpath.name} not found at {rpath}: cannot confirm that 05 is not being rewritten")
    r_st, f_st = rpath.stat(), path.stat()
    rec.update(size_bytes=f_st.st_size, mtime_utc=_utc(f_st.st_mtime))
    r_age, f_age = (now - r_st.st_mtime) / 60.0, (now - f_st.st_mtime) / 60.0
    if r_age < quiet_minutes:
        return not_built(f"{rpath.name} was written {r_age:.1f} min ago (< {quiet_minutes:g} min): 05 is being rewritten")
    if f_age < quiet_minutes:
        return not_built(f"{path.name} was modified {f_age:.1f} min ago (< {quiet_minutes:g} min): 05 is being rewritten")
    try:
        receipt = json.loads(rpath.read_text(encoding="utf-8"))
        raw = path.read_bytes()
    except (OSError, ValueError) as exc:
        return not_built(f"05 or its receipt unreadable ({type(exc).__name__}: {exc})")
    sha = hashlib.sha256(raw).hexdigest()
    rec["sha256"] = sha
    if rpath.stat().st_mtime != r_st.st_mtime or path.stat().st_mtime != f_st.st_mtime:
        return not_built("05 or its receipt changed while being read: 05 is being rewritten")
    want = next((v.get("sha256") for k in ("target", "file") for v in [receipt.get(k)]
                 if isinstance(v, dict) and v.get("sha256")), None)
    notes = []
    if want is None:
        notes.append(f"{rpath.name} records no sha256 for 05; bytes not compared with the receipt")
    elif want != sha:
        return not_built(f"{path.name} sha256 {sha[:16]} differs from the receipt's {want[:16]}: 05 changed after its "
                         "receipt was written")
    else:
        notes.append(f"05 bytes equal the receipt's sha256 ({sha[:16]}); receipt run_id {receipt.get('run_id')}, "
                     f"written_at {receipt.get('written_at')}")
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=False)
        try:
            all_rows = {ws.title: load._sheet_rows(ws, path.name) for ws in wb.worksheets}
        finally:
            wb.close()
        if "data" not in all_rows:
            return not_built(f"{path.name} [data]: sheet missing (present: {sorted(all_rows)})")
        frame = load._frame(all_rows["data"], path.name, "data")
        dic = load._frame(all_rows["dictionary"], path.name, "dictionary") if "dictionary" in all_rows else None
    except Exception as exc:  # any unreadable or invalid workbook makes H5 NOT BUILT rather than failing the run
        return not_built(f"{path.name} failed to load: {type(exc).__name__}: {exc}")
    missing = [c for c in config.H5_REQUIRED if c not in frame.columns]
    if not any(c in frame.columns for c in config.H5_DV_PRIMARY):
        missing.append(" or ".join(config.H5_DV_PRIMARY))
    if missing:
        return not_built(f"expected columns missing from {path.name} [data]: {', '.join(missing)}")
    try:
        frame = load.validate_frame(frame, load.SheetSpec(config.H5_REQUIRED, config.H5_KEY), path.name, "data")
    except load.LoadError as exc:
        return not_built(str(exc))
    documented = set()
    if dic is not None and {"sheet", "column"} <= set(dic.columns):
        documented = set(dic.loc[dic["sheet"] == "data", "column"].astype(str))
    else:
        notes.append("05 has no readable dictionary sheet; columns taken from the data header")
    rec.update(sheets_read=", ".join(s for s in ("data", "dictionary") if s in all_rows),
               rows_read=", ".join(f"{s}={len(all_rows[s]) - 1}" for s in ("data", "dictionary") if s in all_rows),
               note="read at run time; " + "; ".join(notes))
    return ChampionsData(ok=True, frame=frame, source=rec, notes=notes, documented=documented)


def resolve_dv(cd: ChampionsData, role: str):
    """(column, label, flag, reason): the DV column for a role, or reason when absent."""
    cands = config.H5_DV_PRIMARY if role == "industry_money_primary" else config.H5_DV_TRADE
    for c in cands:
        if c in cd.columns:
            flag = config.H5_DV_FALLBACK_FLAG if c == "direct_giving_real_2025_usd" else ""
            return c, config.H5_DV_LABELS.get(c, c), flag, ""
    return None, "", "", f"dependent variable absent from 05 [data]: none of {', '.join(cands)}"


def dv_status_column(cd: ChampionsData, dv_col: str):
    st = dv_col.replace("_real_2025_usd", "_status")
    return st if st in cd.columns and st != dv_col else None


@dataclass
class H5Sample:
    df: pd.DataFrame
    dv_col: str
    dv_label: str
    dv_flag: str
    candidate_rows: int
    exclusions: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    availability: dict = field(default_factory=dict)  # variable -> cycles with a usable value among candidate rows

    @property
    def n(self):
        return len(self.df)

    @property
    def cycles(self):
        return sorted(int(c) for c in self.df["cycle"].unique()) if len(self.df) else []

    @property
    def champions(self):
        return sorted(self.df["bioguide"].unique().tolist()) if len(self.df) else []

    @property
    def member_cycles(self):
        return int(len(self.df[["bioguide", "cycle"]].drop_duplicates())) if len(self.df) else 0

    @property
    def boards(self):
        return sorted(self.df["board"].unique().tolist()) if len(self.df) else []


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def build_h5_sample(cd: ChampionsData, spec, dv_col: str, dv_label: str, dv_flag: str) -> H5Sample:
    df = cd.frame.copy()
    df["cycle"] = _num(df["cycle"]).astype("Int64")
    excl, notes = collections.OrderedDict(), []
    up = _num(df["up_for_election"]) == 1
    excl["up_for_election != 1 (not up for election, including the retiring rows)"] = int((~up).sum())
    df = df[up]
    lost = _num(df["lost_primary"]) == 1
    if spec.keep_lost_primary:
        notes.append(f"lost-renomination rows kept (primary model): {int(lost.sum())}")
    else:
        excl["lost_primary = 1 (lost renomination; such rows enter only the primary models)"] = int(lost.sum())
        df = df[~lost]
    if spec.drop_cycles:
        m = df["cycle"].isin(spec.drop_cycles)
        excl[f"cycle {', '.join(str(c) for c in spec.drop_cycles)} excluded by the specification"] = int(m.sum())
        df = df[~m]
    cand = len(df)
    ok = collections.OrderedDict()
    dv = _num(df[dv_col])
    row_ok = df["status"].isin(config.H5_USABLE_ROW_STATUS)
    st_col = dv_status_column(cd, dv_col)
    st_ok = df[st_col].isin(config.H5_USABLE_DV_STATUS) if st_col else pd.Series(True, index=df.index)
    ok[dv_col] = dv.notna() & row_ok & st_ok
    bad = ~ok[dv_col]
    if bad.any():
        detail = collections.Counter(zip(df.loc[bad, "status"].astype(str),
                                         df.loc[bad, st_col].astype(str) if st_col else ["-"] * int(bad.sum())))
        notes.append(f"{dv_col} unusable by (row status / {st_col or 'no DV status column'}): " +
                     "; ".join(f"{a}/{b}: {k}" for (a, b), k in sorted(detail.items())))
    for f in spec.focal:
        ok[f] = _num(df[f]).notna()
    for c in spec.controls:
        if c == "chamber":
            ok[c] = df[c].isin(["House", "Senate"])
        elif c == "party":
            ok[c] = df[c].notna() & (df[c].astype(str).str.strip() != "")
        else:
            ok[c] = _num(df[c]).notna()
    okdf = pd.DataFrame(ok, index=df.index)
    avail = {v: sorted(int(c) for c in df.loc[okdf[v], "cycle"].dropna().unique()) for v in okdf.columns}
    for v in okdf.columns:
        k = int((~okdf[v]).sum())
        if k:
            excl[f"{v} unusable"] = k
    out = df[okdf.all(axis=1)].copy()
    y = _num(out[dv_col]).astype(float)
    if spec.dv_transform == "log1p":
        neg = y < 0
        if neg.any():
            excl["DV < 0 (log1p variant; excluded, never altered)"] = int(neg.sum())
        out, y = out[~neg], y[~neg]
        out["y"] = np.log1p(y)
    elif spec.dv_transform == "any":
        out["y"] = (y > 0).astype(float)
    else:
        out["y"] = y
    for f in spec.focal:
        out[f] = _num(out[f]).astype(float)
    out["seniority_years"] = _num(out["seniority_years"]).astype(float) if "seniority_years" in out else np.nan
    out = out.sort_values(["board", "bioguide", "cycle"]).reset_index(drop=True)
    return H5Sample(df=out, dv_col=dv_col, dv_label=dv_label, dv_flag=dv_flag, candidate_rows=cand, exclusions=dict(excl),
                    notes=notes, availability=avail)


def build_h5_design(df: pd.DataFrame, spec) -> tuple:
    """(Design, info): FE (champion, board, cycle), controls, focal; columns adding no rank are dropped and named."""
    cols, names, kinds = [], [], []

    def add(v, name, kind):
        cols.append(np.asarray(v, dtype=float))
        names.append(name)
        kinds.append(kind)

    champs = sorted(df["bioguide"].unique().tolist())
    if "champion" in spec.fe:
        for b in champs:
            add(df["bioguide"] == b, f"FE:champion={b}", "champion_fe")
    if "board" in spec.fe:
        for b in sorted(df["board"].unique().tolist()):
            add(df["board"] == b, f"FE:board={b}", "fe")
    if "champion" not in spec.fe and "board" not in spec.fe:
        add(np.ones(len(df)), "FE:constant", "fe")
    if "cycle" in spec.fe:
        for c in sorted(df["cycle"].unique().tolist())[1:]:
            add(df["cycle"] == c, f"YFE:cycle={int(c)}", "fe")
    for c in spec.controls:
        if c == "chamber":
            add(df["chamber"] == "Senate", "chamber=Senate", "control")
        elif c == "party":
            for lvl in sorted(set(df["party"].astype(str)) - {config.H5_PARTY_REFERENCE}):
                add(df["party"].astype(str) == lvl, f"party={lvl}", "control")
        else:
            add(df[c], c, "control")
    for f in spec.focal:
        add(df[f], f, "focal")
    X = np.column_stack(cols) if cols else np.zeros((len(df), 0))
    dep = set(dependent_columns(X, names)) if len(df) else set(names)
    keep = [i for i, n in enumerate(names) if n not in dep]
    info = dict(
        dropped_controls=[n for n, k in zip(names, kinds) if n in dep and k == "control"],
        absorbed_fe=[n for n, k in zip(names, kinds) if n in dep and k in ("fe", "champion_fe")],
        focal_identified=all(f not in dep for f in spec.focal),
        champion_fe=sum(1 for i in keep if kinds[i] == "champion_fe"),
    )
    Xk = X[:, keep]
    nk = [names[i] for i in keep]
    cl = np.array([champs.index(b) for b in df["bioguide"]], dtype=int)
    design = Design(y=df["y"].to_numpy(float), X=Xk, names=nk, clusters=cl, cluster_labels=champs,
                    years=df["cycle"].to_numpy(int), national=[], intercept_spanned=True,
                    nested_fe=info["champion_fe"])
    return design, info


@dataclass
class H5Decision:
    status: str
    reason: str = ""
    reason_short: str = ""
    sample: H5Sample | None = None
    design: Design | None = None
    info: dict = field(default_factory=dict)
    dv_col: str = ""
    dv_label: str = ""
    dv_flag: str = ""
    resid_df: int | None = None
    identifying_champions: int | None = None


def decide_h5(spec, cd: ChampionsData) -> H5Decision:
    if cd is None or not cd.ok:
        why = cd.reason if cd is not None else "05 not loaded"
        return H5Decision(status=NOT_BUILT, reason=f"NotBuilt: {why}", reason_short=f"NotBuilt: {why}")
    dv_col, dv_label, dv_flag, why = resolve_dv(cd, spec.dv)
    if dv_col is None:
        return H5Decision(status=NOT_BUILT, reason=f"NotBuilt: {why}", reason_short=f"NotBuilt: {why}")
    absent = [c for c in spec.focal if c not in cd.columns]
    if absent:
        why = f"column {', '.join(absent)} absent from 05 [data]"
        return H5Decision(status=NOT_BUILT, reason=f"NotBuilt: {why}", reason_short=f"NotBuilt: {why}",
                          dv_col=dv_col, dv_label=dv_label, dv_flag=dv_flag)
    smp = build_h5_sample(cd, spec, dv_col, dv_label, dv_flag)
    reasons, short = [], []
    cyc, mc = smp.cycles, smp.member_cycles
    if len(cyc) < config.H5_MIN_CYCLES:
        reasons.append(f"{len(cyc)} cycles ({cycles_text(cyc)}) < {config.H5_MIN_CYCLES} required")
        short.append(f"{len(cyc)} of {config.H5_MIN_CYCLES} cycles ({cycles_text(cyc)})")
    if mc < config.H5_MIN_MEMBER_CYCLES:
        reasons.append(f"{mc} member-cycles < {config.H5_MIN_MEMBER_CYCLES} required")
        short.append(f"{mc} of {config.H5_MIN_MEMBER_CYCLES} member-cycles")
    within = "champion" in spec.fe
    ident = None
    design, info, resid_df = None, {}, None
    if smp.n:
        for f in spec.focal:
            v = smp.df[f]
            if within:
                dev = v - v.groupby(smp.df["bioguide"]).transform("mean")
                ident = int((v.groupby(smp.df["bioguide"]).nunique() > 1).sum())
                if float(np.var(dev.to_numpy(float))) <= 0:
                    reasons.append(f"{f}: zero within-champion variance (no champion's value varies across cycles)")
                    short.append(f"{f} has no within-champion variation")
            elif float(np.var(v.to_numpy(float))) <= 0:
                reasons.append(f"{f}: zero variance in the sample")
                short.append(f"{f} has zero variance")
        design, info = build_h5_design(smp.df, spec)
        if not info["focal_identified"]:
            reasons.append(f"focal {', '.join(spec.focal)} not identified given the fixed effects and controls")
            short.append("focal not identified")
        resid_df = design.n - rank_of(design.X)
        if resid_df < config.MIN_RESID_DF:
            reasons.append(f"residual df {resid_df} < {config.MIN_RESID_DF}")
            short.append(f"resid df {resid_df}")
        if len(smp.champions) < 2:
            reasons.append(f"{len(smp.champions)} champion cluster(s) < 2")
    else:
        reasons.append("complete-case sample is empty")
        short.append("empty complete-case sample")
    if reasons:
        av = "; ".join(f"{v} usable in cycles {cycles_text(c)}" for v, c in smp.availability.items()
                       if v in (dv_col,) + tuple(spec.focal))
        reasons.append("availability among up-for-election rows: " + av)
        short.append(av)
    status = NOT_ESTIMABLE if reasons else ESTIMABLE
    return H5Decision(status=status, reason="; ".join(reasons), reason_short="; ".join(short), sample=smp,
                      design=design, info=info, dv_col=dv_col, dv_label=dv_label, dv_flag=dv_flag, resid_df=resid_df,
                      identifying_champions=ident)


def unit_of(spec, coef: str) -> str:
    base = {"level": "USD 2025", "log1p": "log1p points of USD 2025", "any": "probability (0-1) of any money > 0"}[
        spec.dv_transform]
    return {
        "toughness_general": f"{base} per point of toughness_general (0 safe ... 3 toss-up)",
        "primary_contested": f"{base}, contested vs uncontested primary",
        "primary_margin": f"{base} per unit of primary margin (vote share 0-1)",
        "general_margin": f"{base} per unit of general-election margin (vote share 0-1)",
    }.get(coef, f"{base} per unit of {coef}")


def _flags(spec, d: H5Decision) -> str:
    return "; ".join(x for x in (d.dv_flag, spec.flag) if x)


def fit_h5_strata(spec, smp: H5Sample, coef: str) -> list:
    rows = []
    sspec = dataclasses.replace(spec, fe=tuple(x for x in spec.fe if x != "board"))
    for b in smp.boards:
        sub = smp.df[smp.df["board"] == b].reset_index(drop=True)
        base = dict(board=b, coefficient=coef, n=len(sub), cycles=cycles_text(sub["cycle"]),
                    n_champions=int(sub["bioguide"].nunique()))
        design, info = build_h5_design(sub, sspec)
        rdf = design.n - rank_of(design.X)
        base["resid_df"] = rdf
        if not info["focal_identified"]:
            rows.append({**base, "status": "insufficient", "reason": "focal not identified within the board"})
            continue
        if rdf < config.MIN_STRATUM_RESID_DF:
            rows.append({**base, "status": "insufficient", "reason": f"residual df {rdf} < {config.MIN_STRATUM_RESID_DF}"})
            continue
        f = ols(design)
        k = f.names.index(coef)
        rows.append({**base, "status": "estimated", "estimate": float(f.beta[k]), "hc1_se": float(f.se_hc1[k]),
                     "cr1_se": float(f.se_cr1[k]), "reason": ""})
    return rows


def stratification_label(strata, coef) -> str:
    rel = [r for r in strata if r["coefficient"] == coef]
    est = [r for r in rel if r["status"] == "estimated"]
    if est:
        return f"STRATIFIED: {len(est)} of {len(rel)} boards estimated"
    if not rel:
        return "UNSTRATIFIED: no strata computed"
    return "UNSTRATIFIED: no board has a board-only estimate (" + rel[0]["reason"] + ")"


def estimate_h5(spec, d: H5Decision, B=config.BOOT_B, seed=config.SEED, alpha=config.ALPHA) -> TestResult:
    res = TestResult()
    fit = ols(d.design)
    for c in spec.focal:
        res.strata.extend(fit_h5_strata(spec, d.sample, c))
        row = boot_coefficient(d.design, fit, c, B, seed_for(seed, spec.id, c), alpha)
        row.update(unit=unit_of(spec, c), focal=True, flag=_flags(spec, d),
                   inference="wild cluster restricted bootstrap by champion (bioguide), Webb weights; CR1 by champion",
                   stratification=stratification_label(res.strata, c))
        res.coefs.append(row)
    return res


def est_row(spec, d: H5Decision) -> dict:
    smp = d.sample
    info = d.info or {}
    notes = []
    if info.get("dropped_controls"):
        notes.append("controls not identified and dropped: " + ", ".join(info["dropped_controls"]))
    if info.get("absorbed_fe"):
        notes.append(f"fixed-effect columns absorbed: {len(info['absorbed_fe'])} ({', '.join(info['absorbed_fe'][:6])}"
                     + (", ..." if len(info["absorbed_fe"]) > 6 else "") + ")")
    if d.identifying_champions is not None:
        notes.append(f"champions whose {', '.join(spec.focal)} varies across cycles: {d.identifying_champions}")
    excl = "; ".join([f"{k}: {v}" for k, v in (smp.exclusions.items() if smp else [])] + (smp.notes if smp else []))
    return dict(
        test_id=spec.id, family=spec.family, label=spec.label, status=d.status,
        window_used=(f"cycles {cycles_text(smp.cycles)}" if d.status == ESTIMABLE else ""),
        window_kind=("member-cycle gate" if d.status == ESTIMABLE else ""),
        n=smp.n if smp else None, n_window="cycles" if smp else "", n_sectors=None, sectors="",
        n_years=len(smp.cycles) if smp else None, years=cycles_text(smp.cycles) if smp else "",
        resid_df=d.resid_df, reason=(d.reason if d.status != ESTIMABLE else ""),
        reason_short=(d.reason_short if d.status != ESTIMABLE else ""), default_attempt="", fallback_attempt="",
        fallback_search="", exclusions=excl, dv=spec.dv, dv_column=d.dv_col, dv_label=d.dv_label,
        focal=", ".join(spec.focal), controls=", ".join(spec.controls), fixed_effects=", ".join(spec.fe),
        variant=f"{spec.variant} ({spec.dv_transform})", base_test=spec.base or "", year_filter="", tiers="",
        note=spec.note + (" " + " ".join(notes) if notes else ""), unit=UNIT,
        n_champions=len(smp.champions) if smp else None, n_member_cycles=smp.member_cycles if smp else None,
        boards=", ".join(smp.boards) if smp else "", cluster_by="bioguide (champion)",
        n_clusters=len(smp.champions) if smp else None, gate_rule=spec.window_rule,
        inference=("wild cluster restricted bootstrap by champion" if spec.inference == "wcr" else spec.inference),
        flag=_flags(spec, d))


def coef_rows(spec, d: H5Decision, res: TestResult) -> list:
    smp = d.sample
    out = []
    for c in res.coefs:
        out.append({**c, "test_id": spec.id, "label": spec.label, "source_test": "",
                    "window_used": f"cycles {cycles_text(smp.cycles)}", "n": smp.n, "n_sectors": None,
                    "n_years": len(smp.cycles), "years": cycles_text(smp.cycles), "unit_of_analysis": UNIT,
                    "n_champions": len(smp.champions), "n_member_cycles": smp.member_cycles,
                    "cycles": cycles_text(smp.cycles), "dv_column": d.dv_col, "resid_df": d.resid_df,
                    "boards": ", ".join(smp.boards), "controls": ", ".join(spec.controls),
                    "fixed_effects": ", ".join(spec.fe),
                    "ci_text": f"[{_fmt(c.get('ci_low'))}, {_fmt(c.get('ci_high'))}]"})
    return out


def sample_rows(spec, d: H5Decision) -> list:
    return [dict(test_id=spec.id, window_used=f"cycles {cycles_text(d.sample.cycles)}", study_sector=None,
                 year=int(r["cycle"]), tier=None, y=float(r["y"]), board=r["board"], bioguide=r["bioguide"],
                 cycle=int(r["cycle"])) for r in d.sample.df.to_dict("records")]


CHAMPION_PANEL_COLS = ("board", "bioguide", "name", "cycle", "status", "up_for_election", "retiring", "lost_primary",
                       "chamber", "party", "seniority_years", "toughness_general", "rating_status", "primary_status",
                       "primary_contested", "primary_margin", "general_status", "general_margin")


def panel_table(cd: ChampionsData) -> pd.DataFrame:
    """The 05 columns H5 reads (every row of 05 data), for the results workbook."""
    if cd is None or not cd.ok:
        return pd.DataFrame(columns=list(CHAMPION_PANEL_COLS))
    extra = [c for c in config.H5_DV_PRIMARY + config.H5_DV_TRADE if c in cd.columns]
    extra += [s for s in (dv_status_column(cd, c) for c in extra) if s]
    cols = [c for c in CHAMPION_PANEL_COLS if c in cd.columns] + extra
    return cd.frame[cols].copy()


def _fmt(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    if isinstance(x, float) and np.isinf(x):
        return "-inf" if x < 0 else "+inf"
    return f"{x:.4g}" if abs(x) < 1e-3 and x != 0 else f"{x:,.4f}"
