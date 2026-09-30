"""Fixed configuration of the sector growth study analysis (plan of 2026-09-25, Paul's rulings R1-R9 and the
rulings of the second run: uniform `study_sector` column, flexible fallback window, LobbyView option (a), H5; third
run: expected control 2023-2026 from 02 `expected_control_2023_2026`, PREVIEW tests on 2021-2025).

Every number that changes a result lives here, so a run is reproducible from this file plus the inputs.
Paths can be redirected with environment variables (tests use temporary folders):
  SGS_STUDY_ROOT   study folder (default C:\\Users\\pgoff\\Mentat\\sector_growth_study)
  SGS_GLASSBOX_DIR Glass Box event folder (default C:\\Users\\pgoff\\.claude\\glassbox\\events)
"""
from __future__ import annotations

import os
from pathlib import Path

STUDY_ROOT = Path(os.environ.get("SGS_STUDY_ROOT", r"C:\Users\pgoff\Mentat\sector_growth_study"))
DATA_DIR = STUDY_ROOT / "data"
RESULTS_DIR = STUDY_ROOT / "results"
GLASSBOX_EVENTS_DIR = Path(os.environ.get("SGS_GLASSBOX_DIR", r"C:\Users\pgoff\.claude\glassbox\events"))
GLASSBOX_LANE = "claude"
GLASSBOX_SOURCE = "sector-growth-analysis"

# The nine study sectors of the plan (section 1), in the plan's order. community_banks is not a study sector.
STUDY_SECTORS = (
    "commercial_banks",
    "credit_unions",
    "life_insurance",
    "auto_manufacturing",
    "crypto",
    "credit_arms",
    "fintech",
    "property_casualty",
    "telecom",
)
PANEL_FIRST_YEAR = 2006
PANEL_LAST_YEAR = 2026
PARTIAL_YEARS = (2026,)  # incomplete calendar year: marked partial, excluded from estimation by default

# Window rule of the sector-year tests.
# Primary (R8, unchanged): 2020-2025 with at least 6 distinct sample years.
# Fallback (ruling of 2026-09-25, second run), tried only when the primary fails: the most recent run of at least 10
# consecutive calendar years within 2008-2025 in which the test's complete-case sample exists (a year counts when at
# least one complete-case row falls in it). The window used is the most recent 10 years of that run
# (FALLBACK_WHOLE_RUN = False; the ruling's worked example: LobbyView complete 2008-2022 -> window 2013-2022). Set
# FALLBACK_WHOLE_RUN = True to use the whole run instead. The fixed 2016-2025 fallback of the first run is retired.
DEFAULT_WINDOW = (2020, 2025)
MIN_YEARS_DEFAULT = 6
FALLBACK_SEARCH = (2008, 2025)
MIN_YEARS_FALLBACK = 10  # consecutive calendar years
FALLBACK_WHOLE_RUN = False
MIN_SECTORS = 2
MIN_RESID_DF = 3
MIN_STRATUM_RESID_DF = 2

# PREVIEW tests (Paul, 2026-09-25: "yes, run the preview too"): a fixed window of 5 full years, below the 6-year minimum
# of R8, never a fallback. Every PREVIEW output carries PREVIEW_FLAG. The full core specification is run as well and is
# reported NOT IDENTIFIED when its year-level parameters (the common level of the sector baselines plus the national
# terms) are as many as the distinct years: the national terms then saturate the years (not forced).
PREVIEW_WINDOW = (2021, 2025)
PREVIEW_MIN_YEARS = 5
PREVIEW_FLAG = "PREVIEW - below the 6-year minimum"

# Expected control (02). exp_dem_* = the IEM annual mean (02 `data`) where present; for calendar years
# EXPECTED_CONTROL_FILL_YEARS a sheet `expected_control_markets` (Polymarket/Kalshi daily history), when 02 has one,
# takes precedence; otherwise 02 `expected_control_2023_2026` (Paul's ruling of 2026-09-25: Crystal Ball final call
# for the 2024 election, market snapshot of 24-25 Sep 2026 for the 2026 election) fills the years IEM leaves blank.
EXPECTED_CONTROL_FILL_YEARS = (2023, 2026)
EXPECTED_CONTROL_SHEET = "expected_control_2023_2026"
EXPECTED_CONTROL_MARKETS_SHEET = "expected_control_markets"

# Inference: wild cluster restricted (WCR) bootstrap, Webb six-point weights; clusters = sectors (sector-year tests)
# or champions (H5, bioguide).
SEED = 20260925
BOOT_B = 9999  # random draws when 6**G > BOOT_B; all 6**G draws are enumerated otherwise
ALPHA = 0.05
CI_LEVEL = 0.95

# Job tiers of 04 tier_by_year. Employee is the reference tier of the pooled tier model; Corporate is fitted separately.
TIERS = ("Chief", "Middle Management", "Employee", "Corporate")
TIER_MODEL_TIERS = ("Chief", "Middle Management", "Employee")
TIER_REFERENCE = "Employee"
TIER_INTERACTED = ("Chief", "Middle Management")
CORPORATE_TIER = "Corporate"

# Year-level ("national") regressors: identical for every sector in a year.
NATIONAL_VARS = (
    "pres_year",
    "midterm_year",
    "exp_dem_house",
    "exp_dem_senate",
    "cur_dem_house",
    "cur_dem_senate",
    "exp_shift_house",
    "exp_shift_senate",
    "pred_dem_seat_change_house",
    "pred_dem_seat_change_senate",
)

DV_LABELS = {
    "contributions_real_m": "general giving (04), all recipient categories, $M 2025",
    "lobby_income_real_m": "LDA outside-firm lobbying income (01), $M 2025",
    "lobby_expenses_real_m": "LDA self-filer lobbying expenses (01), $M 2025",
    "lobby_amount_undiff_real_m": "LobbyView undifferentiated amount, high confidence (01), $M 2025",
}

# ---- H5, industry champions (05 `data` sheet; unit = board x champion x cycle) ---------------------------------------
CHAMPIONS_FILE = "05_industry_champions.xlsx"          # in DATA_DIR
CHAMPIONS_RECEIPT = "build_receipt_05.json"            # in the study folder (the parent of the data folder)
CHAMPIONS_QUIET_MINUTES = 10  # 05 counts as being rewritten while its receipt (or the file) is younger than this
H5_KEY = ("board", "bioguide", "cycle")
H5_REQUIRED = ("board", "bioguide", "cycle", "status", "up_for_election", "lost_primary", "chamber", "party",
               "seniority_years", "toughness_general")
# Dependent variable, first column present wins; the fallback carries the label "employee channel only".
H5_DV_PRIMARY = ("industry_money_primary_real_2025_usd", "direct_giving_real_2025_usd")
H5_DV_TRADE = ("industry_money_with_trade_real_2025_usd",)
H5_DV_LABELS = {
    "industry_money_primary_real_2025_usd": "industry money, primary definition (05), USD 2025",
    "direct_giving_real_2025_usd": ("direct giving to the champion's authorized committees (05), USD 2025 - "
                                    "employee channel only"),
    "industry_money_with_trade_real_2025_usd": "industry money including trade associations (05), USD 2025",
}
H5_DV_FALLBACK_FLAG = "employee channel only"
H5_USABLE_DV_STATUS = ("observed", "observed_zero")  # row-level DV status where the workbook has one
H5_USABLE_ROW_STATUS = ("observed", "partial")        # 05 row status; 'missing' (2020) never enters
H5_PARTIAL_CYCLES = (2026,)  # cycle in progress: current (not final) ratings, money to mid-2026
H5_MIN_CYCLES = 3
H5_MIN_MEMBER_CYCLES = 30
H5_PARTY_REFERENCE = "R"
H5_CHAMBER_REFERENCE = "House"
H5_GENERAL_MARGIN_FLAG = "outcome-contaminated: money affects margins"
