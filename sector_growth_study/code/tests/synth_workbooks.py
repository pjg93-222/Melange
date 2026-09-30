"""Write a complete set of synthetic study workbooks (same file names, sheets and key columns as the real ones),
and optionally a synthetic 05 (champions) with its receipt."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from helpers import SECTORS  # noqa: F401  (sets sys.path)
from sgs import config


def write_xlsx(path: Path, sheets: dict):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, df in sheets.items():
        ws = wb.create_sheet(name)
        ws.append(list(df.columns))
        for row in df.itertuples(index=False, name=None):
            ws.append([None if (isinstance(v, float) and np.isnan(v)) else (v.item() if hasattr(v, "item") else v)
                       for v in row])
    wb.save(path)


def build(folder: Path, seed: int = 5, years=range(2006, 2027), sectors=("commercial_banks", "credit_unions",
          "crypto", "credit_arms", "property_casualty"), slope=0.3, lobbyview=True, contrib_years=None, extra_units=(),
          iem_last_year=None, expected_control=None, markets=None):
    """Dense synthetic inputs: contributions depend on prior growth with slope `slope` ($M per point).
    lobbyview: LobbyView high-confidence rows for commercial_banks and credit_unions, observed 2006-2023, 2024 partial.
    contrib_years: calendar years with contributions (others: 04 sector_year status missing, no data rows); 2026 stays
    partial. extra_units: 04 units that are not study sectors (e.g. community_banks), contributions = 3 + 1.0 * pres_year
    + noise. iem_last_year: IEM p_dem_expected blank (status missing) after that year, as in the real 02.
    expected_control / markets: DataFrames written as 02 sheets expected_control_2023_2026 / expected_control_markets."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    ys = list(years)
    ctl = pd.DataFrame({"year": ys, "presidential_year": [int(y % 4 == 0) for y in ys],
                        "midterm_year": [int(y % 4 == 2) for y in ys],
                        "status": ["missing" if y == 2026 else "observed" for y in ys]})
    exp = {y: (rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)) for y in ys}
    cur = {y: (int(rng.integers(0, 2)), int(rng.integers(0, 2))) for y in ys}
    e_rows, c_rows, s_rows = [], [], []
    for y in ys:
        for j, ch in enumerate(("House", "Senate")):
            blank = iem_last_year is not None and y > iem_last_year
            e_rows.append({"calendar_year": y, "chamber": ch, "p_dem_expected": None if blank else exp[y][j],
                           "status": "missing" if blank else "observed"})
            c_rows.append({"calendar_year": y, "chamber": ch, "dem_control": cur[y][j], "status": "observed"})
            if y % 2 == 0:
                s_rows.append({"chamber": ch, "election_year": y, "pred_dem_net_change": float(rng.integers(-20, 20)),
                               "status": "observed"})
    g_rows, p_rows, d_rows, sy_rows, t_rows, l_rows = [], [], [], [], [], []
    xw = []
    lda_map = {"commercial_banks": "bank", "credit_unions": "credit_union", "crypto": "crypto", "fintech": "fintech"}
    for i, s in enumerate(config.STUDY_SECTORS):
        xw.append({"study_sector": s, "mentat_industry": s if s in sectors else None,
                   "lda_lobbying_sector": lda_map.get(s)})
        if s not in sectors:
            continue
        growth = {y: rng.normal(2, 4) for y in [ys[0] - 1] + ys}
        for y in ys:
            g_rows.append({"sector": s, "study_sector": s, "year": y, "growth_same_year_pct": growth[y],
                           "growth_previous_year_pct": growth[y - 1], "status": "observed"})
            p_rows.append({"sector": s, "study_sector": s, "year": y, "predicted_growth_pct": rng.normal(2, 3),
                           "forecast_publication_month": f"{y - 1}-11", "forecast_age_months": 2, "status": "observed"})
            total = 5 + 2 * i + slope * growth[y - 1] + 1.0 * ctl.loc[ctl.year == y, "presidential_year"].item() \
                + rng.normal(0, 0.2)
            part = y == 2026
            parts = [0.6 * total, 0.4 * total]
            if contrib_years is not None and not part and y not in contrib_years:
                sy_rows.append({"study_sector": s, "year": y, "giving_real_2025_usd": None, "status": "missing"})
                parts = None
            for k, comp in enumerate(("Co A", "Co B") if parts is not None else ()):
                d_rows.append({"year": y, "study_sector": s, "company": comp, "recipient_category": "Candidate",
                               "party": "D", "funding_source": "employee_original",
                               "giving_real_2025_usd": None if part else parts[k] * 1e6,
                               "status": "partial" if part else "observed"})
                for t, share in zip(config.TIERS, (0.1, 0.2, 0.6, 0.1)):
                    t_rows.append({"year": y, "study_sector": s, "company": comp, "employee_tier": t,
                                   "giving_real_2025_usd": None if part else parts[k] * share * 1e6, "gifts": 3,
                                   "status": "partial" if part else "observed"})
            if parts is not None:
                sy_rows.append({"study_sector": s, "year": y, "giving_real_2025_usd": None if part else total * 1e6,
                                "status": "partial" if part else "observed"})
            if s in lda_map:
                l_rows.append({"source": "lda_rebuild", "sector": lda_map[s], "confidence": None, "year": y,
                               "period": "annual", "lobby_income_real_2025_usd": None if part else (3 + i + 0.2 * growth[y - 1]) * 1e6,
                               "lobby_expenses_real_2025_usd": None if part else (6 + i - 0.1 * growth[y - 1]) * 1e6,
                               "lobby_amount_undifferentiated_real_2025_usd": None,
                               "status": "partial" if part else "observed"})
            if lobbyview and s in ("commercial_banks", "credit_unions") and y <= 2024:
                lv_part = y == 2024
                l_rows.append({"source": "lobbyview_adversary_spend", "sector": lda_map[s], "confidence": "high",
                               "year": y, "period": "annual", "lobby_income_real_2025_usd": None,
                               "lobby_expenses_real_2025_usd": None,
                               "lobby_amount_undifferentiated_real_2025_usd": (20 + 5 * i + 0.5 * growth[y - 1]
                                                                               + rng.normal(0, 0.1)) * 1e6,
                               "status": "partial" if lv_part else "observed"})
    for u in extra_units:
        xw.append({"study_sector": u, "mentat_industry": u, "lda_lobbying_sector": None})
        for y in ys:
            part = y == 2026
            has = part or contrib_years is None or y in contrib_years
            total = 3 + 1.0 * ctl.loc[ctl.year == y, "presidential_year"].item() + rng.normal(0, 0.2)
            if has and not part:
                d_rows.append({"year": y, "study_sector": u, "company": "Co U", "recipient_category": "Candidate",
                               "party": "D", "funding_source": "employee_original", "giving_real_2025_usd": total * 1e6,
                               "status": "observed"})
            sy_rows.append({"study_sector": u, "year": y, "giving_real_2025_usd": total * 1e6 if has and not part else None,
                            "status": "partial" if part else ("observed" if has else "missing")})
    write_xlsx(folder / "00_controls.xlsx", {"data": ctl})
    write_xlsx(folder / "01_lobbying_expenditures.xlsx", {"data": pd.DataFrame(l_rows)})
    e_sheets = {"data": pd.DataFrame(e_rows), "seat_calls": pd.DataFrame(s_rows)}
    if expected_control is not None:
        e_sheets["expected_control_2023_2026"] = expected_control
    if markets is not None:
        e_sheets["expected_control_markets"] = markets
    write_xlsx(folder / "02_election_forecasting.xlsx", e_sheets)
    write_xlsx(folder / "03_actual_seat_gain.xlsx", {"current_control": pd.DataFrame(c_rows)})
    write_xlsx(folder / "04_campaign_spending.xlsx", {"data": pd.DataFrame(d_rows), "sector_year": pd.DataFrame(sy_rows),
                                                      "tier_by_year": pd.DataFrame(t_rows)})
    write_xlsx(folder / "06_predicted_industry_growth.xlsx", {"data": pd.DataFrame(p_rows)})
    write_xlsx(folder / "07_actual_industry_growth.xlsx", {"data": pd.DataFrame(g_rows)})
    write_xlsx(folder / "sector_crosswalk.xlsx", {"data": pd.DataFrame(xw)})
    return folder


def expected_control_sheet(house=(1, 1, 0.9144, 0.9144), senate=(0, 0, 0.6386, 0.6386)):
    """02 expected_control_2023_2026 in the study format (values as in the real sheet unless given)."""
    rows = []
    for ch, vals in (("House", house), ("Senate", senate)):
        for y, v in zip((2023, 2024, 2025, 2026), vals):
            final = y <= 2024
            rows.append({"calendar_year": y, "chamber": ch, "election_targeted": 2024 if final else 2026, "exp_dem": v,
                         "method": "forecaster_final_call_binary" if final else "market_snapshot",
                         "measured_on": "2024-11-04" if final else "2026-09-24/25",
                         "flag": {2023: "measured Nov 2024, after the year", 2025: "measured Sep 2026, after the year"}.get(y),
                         "status": "observed",
                         "source_id": ("hsc_predicted_house" if ch == "House" else "hsc_predicted_senate") if final
                         else "hsc_current_2026_control_probabilities"})
    return pd.DataFrame(rows)


# ---- synthetic 05 (champions) --------------------------------------------------------------------------------------

def champions_frame(n_members=40, cycles=(2020, 2022, 2024, 2026), boards=("bank", "credit_union", "crypto"),
                    slope=5000.0, member_corr=0.0, noise=0.0, seed=3, primary_dv=False, trade=False):
    """Synthetic 05 data rows. DV = board + cycle + member effects + slope * toughness_general + controls + noise.
    member_corr > 0 makes the member effect proportional to the member's mean toughness (pooled OLS then biased;
    champion fixed effects remove it). Seniority grows one-for-one with the cycle (absorbed by champion + cycle FE)."""
    rng = np.random.default_rng(seed)
    rows = []
    b_eff = {b: 1000.0 * (k + 1) for k, b in enumerate(boards)}
    c_eff = {c: 300.0 * k for k, c in enumerate(cycles)}
    for m in range(n_members):
        bio = f"M{m:06d}"
        my_boards = [boards[m % len(boards)]] + ([boards[(m + 1) % len(boards)]] if m % 3 == 0 and len(boards) > 1
                                               else [])
        chamber = "Senate" if m % 4 == 0 else "House"
        party = "I" if m == 5 else ("D" if m % 2 else "R")
        sen0 = float(rng.integers(0, 20))
        tough = {c: float(rng.choice([0.0, 1 / 3, 2 / 3, 1.0, 5 / 3, 2.0, 7 / 3, 3.0])) for c in cycles}
        mean_t = float(np.mean([tough[c] for c in cycles if c != cycles[0]]))
        m_eff = member_corr * 20000.0 * mean_t + rng.normal(0, 500.0 if member_corr else 0.0)
        for b in my_boards:
            for c in cycles:
                up = 0 if (m % 11 == 0 and c == 2024) else 1
                lost = 1 if (m == 7 and c == 2026) else (0 if up else None)
                sen = sen0 + (c - cycles[0])
                dv = (b_eff[b] + c_eff[c] + m_eff + slope * tough[c] + 800.0 * (chamber == "Senate")
                      + 150.0 * (party == "D") + 40.0 * sen + rng.normal(0, noise))
                missing = c == 2020
                row = {"board": b, "rank": m + 1, "bioguide": bio, "name": f"Member {m}", "cycle": c,
                       "status": "missing" if missing else ("partial" if c == 2026 else "observed"),
                       "chamber": chamber, "party": party, "up_for_election": up, "retiring": 0 if up else None,
                       "lost_primary": lost, "seniority_years": sen,
                       "toughness_general": None if (not up or lost == 1) else tough[c],
                       "direct_giving_status": "missing" if missing else "observed",
                       "direct_giving_real_2025_usd": None if missing else dv,
                       "primary_contested": (int(rng.integers(0, 2)) if c in (2020, 2022) and up else None),
                       "primary_margin": (float(rng.uniform(0, 1)) if c in (2020, 2022) and up else None),
                       "general_margin": (float(rng.uniform(0, 1)) if c in (2020, 2022, 2024) and up and lost != 1
                                          else None)}
                if primary_dv:
                    row["industry_money_primary_real_2025_usd"] = None if missing else dv + 1.0
                if trade:
                    row["industry_money_with_trade_real_2025_usd"] = None if missing else dv * 1.1
                rows.append(row)
    return pd.DataFrame(rows)


def write_champions(data_dir: Path, frame: pd.DataFrame, age_minutes: float = 30.0, receipt_sha: str | None = None,
                    write_receipt: bool = True):
    """Write 05 and its receipt; mtimes set `age_minutes` in the past (0 = just written, i.e. being rewritten)."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / config.CHAMPIONS_FILE
    dic = pd.DataFrame([{"sheet": "data", "column": c, "type": "text", "unit": None, "definition": f"synthetic {c}"}
                        for c in frame.columns])
    write_xlsx(path, {"data": frame, "dictionary": dic})
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    rpath = data_dir.parent / config.CHAMPIONS_RECEIPT
    if write_receipt:
        rpath.write_text(json.dumps({"run_id": "synthetic-05", "written_at": "synthetic",
                                     "target": {"path": str(path), "sha256": receipt_sha or sha}}), encoding="utf-8")
    t = time.time() - age_minutes * 60.0
    os.utime(path, (t, t))
    if write_receipt:
        os.utime(rpath, (t, t))
    return path, rpath
