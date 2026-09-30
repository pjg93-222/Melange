"""Synthetic data for the tests (no real workbook is read by any test)."""
from __future__ import annotations

import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from sgs import config  # noqa: E402
from sgs.registry import TestSpec  # noqa: E402

SECTORS = config.STUDY_SECTORS
TRUE = {"growth_previous_year_pct": 0.8, "pres_year": 1.5, "midterm_year": -0.6, "exp_dem_house": 2.0,
        "exp_dem_senate": -1.0, "cur_dem_house": 0.7, "cur_dem_senate": -0.4}


def national(years, seed=1):
    rng = np.random.default_rng(seed)
    out = pd.DataFrame({"year": list(years)})
    out["pres_year"] = (out["year"] % 4 == 0).astype(int)
    out["midterm_year"] = (out["year"] % 4 == 2).astype(int)
    out["exp_dem_house"] = rng.uniform(0.05, 0.95, len(out))
    out["exp_dem_senate"] = rng.uniform(0.05, 0.95, len(out))
    out["cur_dem_house"] = rng.integers(0, 2, len(out))
    out["cur_dem_senate"] = rng.integers(0, 2, len(out))
    out.loc[0, "cur_dem_house"] = 0
    out.loc[1, "cur_dem_house"] = 1
    out.loc[0, "cur_dem_senate"] = 1
    out.loc[1, "cur_dem_senate"] = 0
    return out


def sector_year_panel(n_sectors=6, years=range(2014, 2026), noise=0.05, seed=7, beta=None, dv="contributions_real_m"):
    """Complete synthetic sector_year table with sector baselines and known coefficients."""
    beta = dict(TRUE if beta is None else beta)
    rng = np.random.default_rng(seed)
    nat = national(years, seed + 1)
    rows = []
    for i, s in enumerate(SECTORS[:n_sectors]):
        a = 5.0 + 3.0 * i
        for _, r in nat.iterrows():
            g_prev = rng.normal(2.0, 4.0)
            rec = {"study_sector": s, "year": int(r["year"]), "partial_year": False,
                   "growth_previous_year_pct": g_prev, "growth_same_year_pct": rng.normal(2.0, 4.0),
                   "predicted_growth_pct": rng.normal(2.0, 3.0)}
            for c in ("pres_year", "midterm_year", "exp_dem_house", "exp_dem_senate", "cur_dem_house", "cur_dem_senate"):
                rec[c] = r[c]
            y = a + sum(beta.get(k, 0.0) * rec[k] for k in beta) + rng.normal(0, noise)
            rec[dv] = y
            rows.append(rec)
    df = pd.DataFrame(rows)
    for col in ("contributions_real_m", "lobby_income_real_m", "lobby_expenses_real_m"):
        if col not in df:
            df[col] = df[dv]
    df["exp_shift_house"] = df["exp_dem_house"] - df["cur_dem_house"]
    df["exp_shift_senate"] = df["exp_dem_senate"] - df["cur_dem_senate"]
    for st in ("contributions_status", "lobby_income_status", "lobby_expenses_status", "growth_same_status",
               "growth_prev_status", "predicted_status", "controls_status", "exp_dem_house_status",
               "exp_dem_senate_status", "cur_dem_house_status", "cur_dem_senate_status", "exp_shift_house_status",
               "exp_shift_senate_status"):
        df[st] = "observed"
    return df


def spec(**kw):
    base = dict(id="TEST", family="C", label="CORE", dv="contributions_real_m", focal=("growth_previous_year_pct",),
                controls=("pres_year", "midterm_year", "exp_dem_house", "exp_dem_senate"))
    base.update(kw)
    return TestSpec(**base)


L_CONTROLS = ("pres_year", "midterm_year", "exp_dem_house", "exp_dem_senate", "cur_dem_house", "cur_dem_senate")
