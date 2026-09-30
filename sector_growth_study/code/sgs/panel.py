"""Tidy analysis tables (plan section 7) built from the loaded workbooks.

sector_year       one row per study sector x calendar year 2006-2026 (nine sectors x 21 years)
sector_year_tier  one row per study sector x year x job tier (Chief, Middle Management, Employee, Corporate)
industry_year     one row per 04 unit (every Mentat industry in 04 sector_year: the study sectors with a Mentat workbook
                  plus community_banks, which is not a study sector) x year: contributions and election-cycle controls
                  (H1-PV only)
dem_share         not built: raises NotBuilt (recipient chamber mapping not yet prepared)
Expected control (exp_dem_*): the IEM annual mean of 02 `data` where present; for calendar years 2023-2026, 02
`expected_control_markets` (when present) takes precedence, else the IEM value, else 02 `expected_control_2023_2026`
(expected_control()). The method, timing flag and source of every value are carried as exp_dem_*_method / _flag /
_source.

Status vocabulary of every *_status column:
  observed        value present in an observed source row (03 current control 2026 keeps its source label 'derived')
  partial         source row is partial (2026 through mid-year; LobbyView 2024 sliver); never used in estimation
  missing         the sector has a source series (or the input is national) but no usable value for the year
  not_applicable  no source series is mapped to the sector for this input, or the design withholds it
                  (telecom sector growth: the plan keeps the wireless and cable components separate)
Missing values are NaN, never 0, except one documented derivation: a tier absent from 04 tier_by_year in a
sector-year whose total giving is observed is 0 (the source keeps rows only where giving != 0 or gifts > 0).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

OBS, PARTIAL, MISSING, NA = "observed", "partial", "missing", "not_applicable"
USABLE_STATUSES = {OBS, "derived"}
TELECOM_COMPONENTS = ("telecom_wireless", "telecom_cable")


class PanelError(Exception):
    """Inputs are inconsistent in a way the panel cannot represent honestly."""


class NotBuilt(Exception):
    """The table or test is registered but not built yet."""


def _years():
    return list(range(config.PANEL_FIRST_YEAR, config.PANEL_LAST_YEAR + 1))


def _grid():
    g = pd.DataFrame([(s, y) for s in config.STUDY_SECTORS for y in _years()], columns=["study_sector", "year"])
    g["partial_year"] = g["year"].isin(config.PARTIAL_YEARS)
    return g


def _status_fill(df, col, has_series_sectors, row_status_col=None, value_col=None):
    """Fill a status column: row status where a source row exists, else missing / not_applicable."""
    out = []
    for _, r in df.iterrows():
        st = r.get(row_status_col) if row_status_col else None
        val = r.get(value_col) if value_col else None
        if isinstance(st, str) and st:
            if value_col is not None and pd.isna(val) and st in USABLE_STATUSES:
                out.append(MISSING)  # a row exists but the value cell is blank
            else:
                out.append(st)
        elif r["study_sector"] in has_series_sectors:
            out.append(MISSING)
        else:
            out.append(NA)
    df[col] = out


def _crosswalk(wbs):
    xw = wbs["crosswalk"].frames["data"]
    xw = xw[xw["study_sector"].isin(config.STUDY_SECTORS)].copy()
    absent = sorted(set(config.STUDY_SECTORS) - set(xw["study_sector"]))
    if absent:
        raise PanelError(f"sector_crosswalk.xlsx [data]: study sectors missing from the crosswalk: {absent}")
    return xw


def build_sector_year(wbs: dict) -> pd.DataFrame:
    g = _grid()
    xw = _crosswalk(wbs)

    # ---- controls (00): election-cycle indicators; the CPI status is kept for transparency only
    ctl = wbs["controls"].frames["data"][["year", "presidential_year", "midterm_year", "status"]].rename(
        columns={"presidential_year": "pres_year", "status": "cpi_status"})
    g = g.merge(ctl, on="year", how="left")
    g["controls_status"] = np.where(g["pres_year"].notna() & g["midterm_year"].notna(), OBS, MISSING)

    # ---- contributions (04 general giving): sum over companies, recipient categories, parties and funding sources
    d4 = wbs["spending"].frames["data"]
    d4 = d4[d4["study_sector"].isin(config.STUDY_SECTORS)]
    agg = (d4.groupby(["study_sector", "year"])["giving_real_2025_usd"].sum(min_count=1) / 1e6).rename(
        "contributions_real_m").reset_index()
    sy4 = wbs["spending"].frames["sector_year"]
    sy4 = sy4[sy4["study_sector"].isin(config.STUDY_SECTORS)][["study_sector", "year", "giving_real_2025_usd", "status"]]
    chk = sy4.merge(agg, on=["study_sector", "year"], how="left")
    bad = chk[chk["giving_real_2025_usd"].notna() &
              ((chk["contributions_real_m"] * 1e6 - chk["giving_real_2025_usd"]).abs() > 1.0)]
    if len(bad):
        raise PanelError("04_campaign_spending.xlsx: data-sheet sums disagree with sector_year by more than $1: "
                         + bad[["study_sector", "year"]].to_dict("records").__repr__())
    g = g.merge(agg, on=["study_sector", "year"], how="left")
    g = g.merge(sy4[["study_sector", "year", "status"]].rename(columns={"status": "_c_status"}),
                on=["study_sector", "year"], how="left")
    workbook_sectors = set(xw.loc[xw["mentat_industry"].notna(), "study_sector"])
    _status_fill(g, "contributions_status", workbook_sectors, "_c_status", "contributions_real_m")

    # ---- lobbying (01): LDA income and expenses (never summed); LobbyView undifferentiated amount (high confidence)
    lmap = xw.dropna(subset=["lda_lobbying_sector"]).set_index("lda_lobbying_sector")["study_sector"]
    if lmap.index.duplicated().any():
        raise PanelError("sector_crosswalk.xlsx [data] column lda_lobbying_sector: one LDA sector maps to two study sectors")
    lob = wbs["lobbying"].frames["data"].copy()
    lob["study_sector"] = lob["sector"].map(lmap)
    lda = lob[(lob["source"] == "lda_rebuild") & (lob["period"] == "annual") & lob["study_sector"].notna()]
    lda = lda[["study_sector", "year", "lobby_income_real_2025_usd", "lobby_expenses_real_2025_usd", "status"]].copy()
    lda["lobby_income_real_m"] = lda.pop("lobby_income_real_2025_usd") / 1e6
    lda["lobby_expenses_real_m"] = lda.pop("lobby_expenses_real_2025_usd") / 1e6
    g = g.merge(lda.rename(columns={"status": "_lda_status"}), on=["study_sector", "year"], how="left")
    lda_sectors = set(lmap.values)
    _status_fill(g, "lobby_income_status", lda_sectors, "_lda_status", "lobby_income_real_m")
    _status_fill(g, "lobby_expenses_status", lda_sectors, "_lda_status", "lobby_expenses_real_m")
    lv = lob[(lob["source"] == "lobbyview_adversary_spend") & (lob["period"] == "annual") &
             (lob["confidence"] == "high") & lob["study_sector"].notna()]
    lv = lv[["study_sector", "year", "lobby_amount_undifferentiated_real_2025_usd", "status"]].copy()
    lv["lobby_amount_undiff_real_m"] = lv.pop("lobby_amount_undifferentiated_real_2025_usd") / 1e6
    g = g.merge(lv.rename(columns={"status": "_lv_status"}), on=["study_sector", "year"], how="left")
    _status_fill(g, "lobby_undiff_status", set(lv["study_sector"]), "_lv_status", "lobby_amount_undiff_real_m")

    # ---- actual growth (07); telecom: components kept separate, sector growth withheld
    a7 = wbs["actual"].frames["data"]
    a7s = a7[a7["study_sector"].isin(config.STUDY_SECTORS) & (a7["study_sector"] != "telecom")]
    per = a7s.groupby("study_sector")["sector"].nunique()
    if (per > 1).any():
        raise PanelError(f"07_actual_industry_growth.xlsx [data]: several series map to one study sector: {per[per > 1].to_dict()}")
    a7v = a7s[["study_sector", "year", "growth_same_year_pct", "growth_previous_year_pct", "status"]]
    g = g.merge(a7v.rename(columns={"status": "_g_status"}), on=["study_sector", "year"], how="left")
    growth_sectors = set(a7v["study_sector"])
    _status_fill(g, "growth_same_status", growth_sectors, "_g_status", "growth_same_year_pct")
    _status_fill(g, "growth_prev_status", growth_sectors, "_g_status", "growth_previous_year_pct")
    for comp in TELECOM_COMPONENTS:
        c = a7[a7["sector"] == comp][["year", "growth_same_year_pct", "growth_previous_year_pct"]].rename(columns={
            "growth_same_year_pct": f"growth_same_year_pct_{comp}",
            "growth_previous_year_pct": f"growth_previous_year_pct_{comp}"})
        c["study_sector"] = "telecom"
        g = g.merge(c, on=["study_sector", "year"], how="left")
    tel = g["study_sector"] == "telecom"
    g.loc[tel, ["growth_same_year_pct", "growth_previous_year_pct"]] = np.nan
    g.loc[tel, ["growth_same_status", "growth_prev_status"]] = NA

    # ---- predicted growth (06 strict column only); vintage fields only where the strict value is used
    p6 = wbs["predicted"].frames["data"]
    p6 = p6[p6["study_sector"].isin(config.STUDY_SECTORS)][[
        "study_sector", "year", "predicted_growth_pct", "forecast_publication_month", "forecast_age_months", "status"]]
    g = g.merge(p6.rename(columns={"status": "predicted_source_status"}), on=["study_sector", "year"], how="left")
    has_p = g["predicted_growth_pct"].notna()
    g.loc[~has_p, ["forecast_publication_month", "forecast_age_months"]] = np.nan
    g["predicted_status"] = np.where(has_p, OBS, MISSING)

    # ---- expected control (02: IEM where present, 2023-2026 filled by expected_control()) and current control (03)
    ec = expected_control(wbs)
    for ch in ("House", "Senate"):
        s = ch.lower()
        e = ec[ec["chamber"] == ch][["year", "exp_dem", "status", "method", "flag", "source"]].rename(columns={
            "exp_dem": f"exp_dem_{s}", "status": f"_e_{s}", "method": f"exp_dem_{s}_method",
            "flag": f"exp_dem_{s}_flag", "source": f"exp_dem_{s}_source"})
        g = g.merge(e, on="year", how="left")
        for c in (f"exp_dem_{s}_method", f"exp_dem_{s}_flag", f"exp_dem_{s}_source"):
            g[c] = g[c].astype(object).where(g[c].notna(), None)  # blank text is None, never NaN
        _status_fill(g, f"exp_dem_{s}_status", set(config.STUDY_SECTORS), f"_e_{s}", f"exp_dem_{s}")
        cc = wbs["seats"].frames["current_control"]
        c = cc[cc["chamber"] == ch][["calendar_year", "dem_control", "status"]].rename(columns={
            "calendar_year": "year", "dem_control": f"cur_dem_{s}", "status": f"_cc_{s}"})
        g = g.merge(c, on="year", how="left")
        _status_fill(g, f"cur_dem_{s}_status", set(config.STUDY_SECTORS), f"_cc_{s}", f"cur_dem_{s}")
        ok = g[f"exp_dem_{s}"].notna() & g[f"cur_dem_{s}"].notna() & \
            g[f"exp_dem_{s}_status"].isin(USABLE_STATUSES) & g[f"cur_dem_{s}_status"].isin(USABLE_STATUSES)
        g[f"exp_shift_{s}"] = np.where(ok, g[f"exp_dem_{s}"] - g[f"cur_dem_{s}"], np.nan)
        g[f"exp_shift_{s}_status"] = np.where(ok, OBS, MISSING)
        # ---- final seat calls (02 seat_calls): election years only
        sc = wbs["election"].frames["seat_calls"]
        c = sc[sc["chamber"] == ch][["election_year", "pred_dem_net_change", "status"]].rename(columns={
            "election_year": "year", "pred_dem_net_change": f"pred_dem_seat_change_{s}", "status": f"_sc_{s}"})
        g = g.merge(c, on="year", how="left")
        _status_fill(g, f"seat_calls_{s}_status", set(config.STUDY_SECTORS), f"_sc_{s}", f"pred_dem_seat_change_{s}")
        odd = g["year"] % 2 == 1
        g.loc[odd, f"pred_dem_seat_change_{s}"] = np.nan
        g.loc[odd, f"seat_calls_{s}_status"] = NA

    g = g.drop(columns=[c for c in g.columns if c.startswith("_")])
    if g.duplicated(["study_sector", "year"]).any():
        raise PanelError("sector_year: duplicate study_sector x year rows after joins")
    if len(g) != len(config.STUDY_SECTORS) * len(_years()):
        raise PanelError(f"sector_year: {len(g)} rows, expected {len(config.STUDY_SECTORS) * len(_years())}")
    return g.sort_values(["study_sector", "year"], key=lambda s: s.map(
        {k: i for i, k in enumerate(config.STUDY_SECTORS)}) if s.name == "study_sector" else s).reset_index(drop=True)


def _txt(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and not v.strip()):
        return None
    return v


def market_annual(m: pd.DataFrame, years=config.EXPECTED_CONTROL_FILL_YEARS) -> dict:
    """02 `expected_control_markets` (daily rows: date, calendar_year, chamber, market, p_dem_control or p_rep_control,
    status; optional before_election_day) -> {(calendar_year, chamber): value row} for the fill years only: the mean
    of every usable daily p_dem (p_dem_control, else 1 - p_rep_control; status usable; before_election_day = 1 where
    that column exists) of the calendar year, all markets pooled. Flag when the last date used falls after the year."""
    label = f"02_election_forecasting.xlsx [{config.EXPECTED_CONTROL_MARKETS_SHEET}]"
    if "p_dem_control" not in m.columns and "p_rep_control" not in m.columns:
        raise PanelError(f"{label}: needs a p_dem_control or p_rep_control column")
    df = m.copy()
    if "p_dem_control" in df.columns:
        p = pd.to_numeric(df["p_dem_control"], errors="coerce")
    else:
        p = pd.Series(np.nan, index=df.index)
    if "p_rep_control" in df.columns:
        p = p.where(p.notna(), 1.0 - pd.to_numeric(df["p_rep_control"], errors="coerce"))
    ok = p.notna() & df["status"].isin(USABLE_STATUSES)
    if "before_election_day" in df.columns:
        ok &= pd.to_numeric(df["before_election_day"], errors="coerce") == 1
    df["_p"] = p
    df["_date"] = pd.to_datetime(df["date"].astype(str).str[:10], errors="coerce")
    ok &= df["_date"].notna()
    out = {}
    for (y, ch), grp in df[ok].groupby(["calendar_year", "chamber"]):
        y = int(y)
        if not (years[0] <= y <= years[1]):
            continue
        first, last = grp["_date"].min(), grp["_date"].max()
        flag = f"measured {last.strftime('%b %Y')}, after the year" if last.year > y else None
        mkts = ", ".join(sorted({str(v) for v in grp["market"]}))
        out[(y, ch)] = dict(year=y, chamber=ch, exp_dem=float(grp["_p"].mean()), status=OBS, method="market_daily_mean",
                            flag=flag, source=(f"02 {config.EXPECTED_CONTROL_MARKETS_SHEET}: {len(grp)} daily rows "
                                               f"{first.date()}..{last.date()} ({mkts})"))
    return out


def expected_control(wbs: dict) -> pd.DataFrame:
    """Expected Democratic control by calendar year x chamber: year, chamber, exp_dem, status, method, flag, source.
    Every year: the IEM annual mean of 02 `data` (method iem_annual_mean) where present and usable. For
    config.EXPECTED_CONTROL_FILL_YEARS (2023-2026), in order of precedence: 02 `expected_control_markets` when the sheet
    exists and has usable rows for the year x chamber; the IEM value; 02 `expected_control_2023_2026` (method and flag
    as the sheet states them). A year x chamber no source fills keeps the IEM row's status (missing)."""
    frames = wbs["election"].frames
    lo, hi = config.EXPECTED_CONTROL_FILL_YEARS
    rows = {}
    for r in frames["data"].to_dict("records"):
        y, ch = int(r["calendar_year"]), r["chamber"]
        usable = pd.notna(r["p_dem_expected"]) and r["status"] in USABLE_STATUSES
        rows[(y, ch)] = dict(year=y, chamber=ch, exp_dem=float(r["p_dem_expected"]) if usable else np.nan,
                             status=r["status"], method="iem_annual_mean" if usable else None, flag=None,
                             source="02 data (IEM annual mean)" if usable else None)
    fill = frames.get(config.EXPECTED_CONTROL_SHEET)
    markets = frames.get(config.EXPECTED_CONTROL_MARKETS_SHEET)
    mk = market_annual(markets) if markets is not None else {}
    for y in range(lo, hi + 1):
        for ch in ("House", "Senate"):
            key = (y, ch)
            if key in mk:
                rows[key] = mk[key]
                continue
            cur = rows.get(key)
            if cur is not None and pd.notna(cur["exp_dem"]):
                continue
            if fill is None:
                continue
            m = fill[(pd.to_numeric(fill["calendar_year"], errors="coerce") == y) & (fill["chamber"] == ch)]
            if not len(m):
                continue
            r = m.iloc[0]
            if pd.notna(r["exp_dem"]) and r["status"] in USABLE_STATUSES:
                rows[key] = dict(year=y, chamber=ch, exp_dem=float(r["exp_dem"]), status=r["status"],
                                 method=_txt(r["method"]), flag=_txt(r["flag"]),
                                 source=f"02 {config.EXPECTED_CONTROL_SHEET} ({_txt(r['source_id'])})")
    out = pd.DataFrame(list(rows.values()), columns=["year", "chamber", "exp_dem", "status", "method", "flag", "source"])
    return out.sort_values(["chamber", "year"]).reset_index(drop=True)


def build_industry_year(wbs: dict) -> pd.DataFrame:
    """H1-PV table: every unit of 04 sector_year (the eight Mentat industries: seven study sectors plus community_banks)
    x calendar year 2006-2026, with contributions (04 general giving, $M 2025) and pres_year / midterm_year (00)."""
    sy4 = wbs["spending"].frames["sector_year"]
    units = sorted(dict.fromkeys(sy4["study_sector"]),
                   key=lambda u: (config.STUDY_SECTORS.index(u) if u in config.STUDY_SECTORS else 99, str(u)))
    g = pd.DataFrame([(u, y) for u in units for y in _years()], columns=["study_sector", "year"])
    g["partial_year"] = g["year"].isin(config.PARTIAL_YEARS)
    if "mentat_industry" in sy4.columns:
        mi = sy4.drop_duplicates("study_sector").set_index("study_sector")["mentat_industry"]
    else:
        mi = pd.Series({u: u for u in units})
    g["mentat_industry"] = g["study_sector"].map(mi)
    g["is_study_sector"] = g["study_sector"].isin(config.STUDY_SECTORS)
    ctl = wbs["controls"].frames["data"][["year", "presidential_year", "midterm_year"]].rename(
        columns={"presidential_year": "pres_year"})
    g = g.merge(ctl, on="year", how="left")
    g["controls_status"] = np.where(g["pres_year"].notna() & g["midterm_year"].notna(), OBS, MISSING)
    d4 = wbs["spending"].frames["data"]
    agg = (d4.groupby(["study_sector", "year"])["giving_real_2025_usd"].sum(min_count=1) / 1e6).rename(
        "contributions_real_m").reset_index()
    chk = sy4[["study_sector", "year", "giving_real_2025_usd"]].merge(agg, on=["study_sector", "year"], how="left")
    bad = chk[chk["giving_real_2025_usd"].notna() &
              ((chk["contributions_real_m"] * 1e6 - chk["giving_real_2025_usd"]).abs() > 1.0)]
    if len(bad):
        raise PanelError("04_campaign_spending.xlsx: data-sheet sums disagree with sector_year by more than $1: "
                         + repr(bad[["study_sector", "year"]].to_dict("records")))
    g = g.merge(agg, on=["study_sector", "year"], how="left")
    g = g.merge(sy4[["study_sector", "year", "status"]].rename(columns={"status": "_c_status"}),
                on=["study_sector", "year"], how="left")
    _status_fill(g, "contributions_status", set(units), "_c_status", "contributions_real_m")
    g = g.drop(columns=[c for c in g.columns if c.startswith("_")])
    if g.duplicated(["study_sector", "year"]).any():
        raise PanelError("industry_year: duplicate unit x year rows")
    return g.reset_index(drop=True)


def build_sector_year_tier(wbs: dict, sector_year: pd.DataFrame) -> pd.DataFrame:
    t4 = wbs["spending"].frames["tier_by_year"]
    t4 = t4[t4["study_sector"].isin(config.STUDY_SECTORS)].copy()
    t4["employee_tier"] = t4["employee_tier"].where(t4["employee_tier"].notna(), "(blank)")
    unknown = sorted(set(t4["employee_tier"]) - set(config.TIERS) - {"(blank)"})
    if unknown:
        raise PanelError(f"04_campaign_spending.xlsx [tier_by_year] column employee_tier: unknown tiers {unknown}")
    rank = {OBS: 0, "derived": 0, PARTIAL: 1, MISSING: 2}
    agg = t4.groupby(["study_sector", "year", "employee_tier"]).agg(
        contributions_real_m=("giving_real_2025_usd", lambda s: s.sum(min_count=1) / 1e6),
        gifts=("gifts", "sum") if "gifts" in t4.columns else ("giving_real_2025_usd", "size"),
        _st=("status", lambda s: max(s, key=lambda v: rank.get(v, 3)))).reset_index()
    # reconcile: tiers (including any blank tier) add up to the sector-year total
    tot = agg.groupby(["study_sector", "year"])["contributions_real_m"].sum(min_count=1).rename("_tier_total").reset_index()
    chk = sector_year[["study_sector", "year", "contributions_real_m", "contributions_status"]].merge(
        tot, on=["study_sector", "year"], how="left")
    chk = chk[chk["contributions_status"] == OBS]
    bad = chk[(chk["_tier_total"].fillna(0.0) - chk["contributions_real_m"]).abs() > 1e-6]
    if len(bad):
        raise PanelError("04 tier_by_year totals disagree with the data sheet by more than $1: "
                         + repr(bad[["study_sector", "year"]].to_dict("records")))
    rows = [(s, y, t) for s in config.STUDY_SECTORS for y in _years() for t in config.TIERS]
    grid = pd.DataFrame(rows, columns=["study_sector", "year", "tier"])
    grid = grid.merge(agg.rename(columns={"employee_tier": "tier"}), on=["study_sector", "year", "tier"], how="left")
    grid["tier_row_present"] = grid["_st"].notna()
    base = sector_year.set_index(["study_sector", "year"])
    cst = base.loc[list(zip(grid["study_sector"], grid["year"])), "contributions_status"].to_numpy()
    zero = (~grid["tier_row_present"]) & (cst == OBS)
    grid.loc[zero, "contributions_real_m"] = 0.0
    grid.loc[zero, "gifts"] = 0
    grid["contributions_status"] = np.where(grid["tier_row_present"], grid["_st"], cst)
    grid.loc[zero, "contributions_status"] = OBS
    grid = grid.drop(columns=["_st"])
    carry = [c for c in sector_year.columns if c not in (
        "contributions_real_m", "contributions_status", "lobby_income_real_m", "lobby_expenses_real_m",
        "lobby_amount_undiff_real_m", "lobby_income_status", "lobby_expenses_status", "lobby_undiff_status")]
    out = grid.merge(sector_year[carry], on=["study_sector", "year"], how="left")
    if out.duplicated(["study_sector", "year", "tier"]).any():
        raise PanelError("sector_year_tier: duplicate study_sector x year x tier rows")
    return out


def build_dem_share(*_args, **_kwargs):
    raise NotBuilt("recipient chamber mapping not yet prepared")


# Status column of every analysis variable (used by the sample builder to exclude partial / unusable values).
STATUS_OF = {
    "contributions_real_m": "contributions_status",
    "lobby_income_real_m": "lobby_income_status",
    "lobby_expenses_real_m": "lobby_expenses_status",
    "lobby_amount_undiff_real_m": "lobby_undiff_status",
    "growth_same_year_pct": "growth_same_status",
    "growth_previous_year_pct": "growth_prev_status",
    "predicted_growth_pct": "predicted_status",
    "pres_year": "controls_status",
    "midterm_year": "controls_status",
    "exp_dem_house": "exp_dem_house_status",
    "exp_dem_senate": "exp_dem_senate_status",
    "cur_dem_house": "cur_dem_house_status",
    "cur_dem_senate": "cur_dem_senate_status",
    "exp_shift_house": "exp_shift_house_status",
    "exp_shift_senate": "exp_shift_senate_status",
    "pred_dem_seat_change_house": "seat_calls_house_status",
    "pred_dem_seat_change_senate": "seat_calls_senate_status",
}

PANEL_DICTIONARY = {
    "study_sector": ("text", None, "Study sector (plan of 2026-09-25): the nine sectors of config.STUDY_SECTORS."),
    "year": ("integer", "calendar year", "Calendar year 2006-2026."),
    "tier": ("text", None, "Job tier of 04 tier_by_year: Chief, Middle Management, Employee, Corporate."),
    "partial_year": ("boolean", None, "True for 2026 (incomplete calendar year); excluded from estimation by default."),
    "pres_year": ("integer", "1/0", "00 presidential_year."),
    "midterm_year": ("integer", "1/0", "00 midterm_year; odd years are the reference category."),
    "cpi_status": ("text", "status", "00 row status (CPI availability); informational."),
    "controls_status": ("text", "status", "observed when pres_year and midterm_year are present."),
    "contributions_real_m": ("decimal", "$M, 2025 dollars", "04 general giving (Include in Analysis amount, all recipient categories, parties and funding sources) summed over companies; giving_real_2025_usd / 1e6. Tier table: the tier's share."),
    "contributions_status": ("text", "status", "04 sector_year status (tier table: tier_by_year status; a tier absent in an observed sector-year is a derived 0)."),
    "gifts": ("integer", "count", "Tier table: 04 tier_by_year gifts summed over companies."),
    "tier_row_present": ("boolean", None, "Tier table: False where 04 has no row for the tier (value 0 in observed sector-years)."),
    "lobby_income_real_m": ("decimal", "$M, 2025 dollars", "01 LDA rebuild income_total (outside-firm fees), via crosswalk lda_lobbying_sector; never added to expenses."),
    "lobby_expenses_real_m": ("decimal", "$M, 2025 dollars", "01 LDA rebuild expenses_total (self-filer in-house expenses); never added to income."),
    "lobby_income_status": ("text", "status", "01 LDA row status."),
    "lobby_expenses_status": ("text", "status", "01 LDA row status."),
    "lobby_amount_undiff_real_m": ("decimal", "$M, 2025 dollars", "01 LobbyView undifferentiated amount, confidence = high only; LobbyView sector labels mapped through the crosswalk lda_lobbying_sector (same label set). A separate measure: never spliced onto LDA."),
    "lobby_undiff_status": ("text", "status", "01 LobbyView row status (2024 is a partial sliver in the source)."),
    "growth_same_year_pct": ("decimal", "percentage points", "07 growth_same_year_pct (same-vintage revenue growth t-1 to t). Telecom: blank (components kept separate)."),
    "growth_previous_year_pct": ("decimal", "percentage points", "07 growth_previous_year_pct (growth t-2 to t-1). Telecom: blank."),
    "growth_same_status": ("text", "status", "Status of growth_same_year_pct."),
    "growth_prev_status": ("text", "status", "Status of growth_previous_year_pct."),
    "growth_same_year_pct_telecom_wireless": ("decimal", "percentage points", "07 telecom_wireless component (telecom rows only)."),
    "growth_previous_year_pct_telecom_wireless": ("decimal", "percentage points", "07 telecom_wireless component, one-year lag."),
    "growth_same_year_pct_telecom_cable": ("decimal", "percentage points", "07 telecom_cable component (telecom rows only)."),
    "growth_previous_year_pct_telecom_cable": ("decimal", "percentage points", "07 telecom_cable component, one-year lag."),
    "predicted_growth_pct": ("decimal", "percentage points", "06 predicted_growth_pct (the plan's strict annual column only)."),
    "forecast_publication_month": ("text", "YYYY-MM", "06 publication month of the forecast used; blank where predicted_growth_pct is blank."),
    "forecast_age_months": ("integer", "months", "06 forecast age at January of the target year; blank where predicted_growth_pct is blank."),
    "predicted_source_status": ("text", "status", "06 row status verbatim (partial = only the broader collected value exists)."),
    "predicted_status": ("text", "status", "observed when predicted_growth_pct is present, else missing."),
    "exp_dem_house": ("decimal", "probability 0-1 (0/1 for the forecaster final call)", "Expected Democratic House control: 02 IEM p_dem_expected where present (2008-2022); 2023-2026: 02 expected_control_markets when that sheet exists, else 02 expected_control_2023_2026 (2023-2024: 1 if the Crystal Ball final call of 4 Nov 2024 projects >= 218 Democratic seats, else 0; 2025-2026: 1 - p_rep_control, Kalshi/Polymarket read 24-25 Sep 2026)."),
    "exp_dem_senate": ("decimal", "probability 0-1 (0/1 for the forecaster final call)", "As exp_dem_house for the Senate (final-call threshold: >= 51 Democratic seats)."),
    "exp_dem_house_status": ("text", "status", "Status of the 02 row used (IEM data or the fill sheet)."),
    "exp_dem_senate_status": ("text", "status", "Status of the 02 row used (IEM data or the fill sheet)."),
    "exp_dem_house_method": ("text", None, "iem_annual_mean / forecaster_final_call_binary / market_snapshot / market_daily_mean; blank where exp_dem_house is blank."),
    "exp_dem_senate_method": ("text", None, "As exp_dem_house_method, Senate."),
    "exp_dem_house_flag": ("text", None, "Timing flag of the value, e.g. 'measured Nov 2024, after the year' (2023), 'measured Sep 2026, after the year' (2025); blank otherwise."),
    "exp_dem_senate_flag": ("text", None, "As exp_dem_house_flag, Senate."),
    "exp_dem_house_source": ("text", None, "02 sheet (and source_id) the value comes from."),
    "exp_dem_senate_source": ("text", None, "02 sheet (and source_id) the value comes from, Senate."),
    "mentat_industry": ("text", None, "industry_year: 04 mentat_industry of the unit."),
    "is_study_sector": ("boolean", None, "industry_year: False for community_banks (a Mentat industry, not a study sector)."),
    "cur_dem_house": ("integer", "1/0", "03 current_control dem_control, House (1 = Democratic majority most of the year)."),
    "cur_dem_senate": ("integer", "1/0", "03 current_control dem_control, Senate."),
    "cur_dem_house_status": ("text", "status", "03 row status (2026 derived)."),
    "cur_dem_senate_status": ("text", "status", "03 row status (2026 derived)."),
    "exp_shift_house": ("decimal", "probability shift", "exp_dem_house - cur_dem_house."),
    "exp_shift_senate": ("decimal", "probability shift", "exp_dem_senate - cur_dem_senate."),
    "exp_shift_house_status": ("text", "status", "observed when both inputs are usable."),
    "exp_shift_senate_status": ("text", "status", "observed when both inputs are usable."),
    "pred_dem_seat_change_house": ("decimal", "seats", "02 seat_calls pred_dem_net_change for the election of the calendar year (even years only)."),
    "pred_dem_seat_change_senate": ("decimal", "seats", "02 seat_calls pred_dem_net_change, Senate (even years only)."),
    "seat_calls_house_status": ("text", "status", "02 seat_calls status; not_applicable in odd years."),
    "seat_calls_senate_status": ("text", "status", "02 seat_calls status; not_applicable in odd years."),
}
