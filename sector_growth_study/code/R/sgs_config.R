# Fixed configuration of the sector growth study analysis: the R port of code/sgs/config.py (plan of 2026-09-25,
# Paul's rulings R1-R9, the second-run rulings and the third-run expected-control fill), plus the rule sets.
#
# Every number that changes a result lives here, so a run is reproducible from this file plus the inputs.
# Paths are run arguments (run_all.R --data-dir / --results-dir / --receipt-05); these defaults can also be
# redirected with environment variables (the tests use temporary folders):
#   SGS_STUDY_ROOT   study folder (default C:\Users\pgoff\Mentat\sector_growth_study)
#   SGS_GLASSBOX_DIR Glass Box event folder (default C:\Users\pgoff\.claude\glassbox\events)
#
# Rule sets (sgs_rules):
#   "python-parity"   the behaviour of the frozen Python package code/sgs (139 tests), used to prove the port;
#   "paul-2026-09-25" the default: Paul's rulings of 2026-09-25 night (see sgs_rules below and the report's Build
#                     notes); the Python package does not implement them.

sgs_env_path <- function(name, default) {
  v <- trimws(Sys.getenv(name, unset = ""))
  if (nzchar(v)) v else default
}

SGS <- list(
  VERSION = "R-0.5.0",
  STUDY_ROOT = sgs_env_path("SGS_STUDY_ROOT", "C:/Users/pgoff/Mentat/sector_growth_study"),
  GLASSBOX_EVENTS_DIR = sgs_env_path("SGS_GLASSBOX_DIR", "C:/Users/pgoff/.claude/glassbox/events"),
  GLASSBOX_LANE = "claude",
  GLASSBOX_SOURCE = "sector-growth-analysis",

  # The nine study sectors of the plan (section 1), in the plan's order. community_banks is not a study sector.
  STUDY_SECTORS = c("commercial_banks", "credit_unions", "life_insurance", "auto_manufacturing", "crypto",
                    "credit_arms", "fintech", "property_casualty", "telecom"),
  PANEL_FIRST_YEAR = 2006,
  PANEL_LAST_YEAR = 2026,
  PARTIAL_YEARS = 2026,  # incomplete calendar year: marked partial, excluded from estimation by default

  # Window rule of the sector-year tests. Primary (R8): 2020-2025 with at least 6 distinct sample years. Fallback
  # (ruling of 2026-09-25, second run), tried only when the primary fails: the most recent run of at least 10
  # consecutive calendar years within 2008-2025 in which the test's complete-case sample exists; the window used is
  # that run's most recent 10 years (FALLBACK_WHOLE_RUN = FALSE; TRUE uses the whole run).
  DEFAULT_WINDOW = c(2020, 2025),
  MIN_YEARS_DEFAULT = 6,
  FALLBACK_SEARCH = c(2008, 2025),
  MIN_YEARS_FALLBACK = 10,
  FALLBACK_WHOLE_RUN = FALSE,
  MIN_SECTORS = 2,
  MIN_RESID_DF = 3,
  MIN_STRATUM_RESID_DF = 2,

  # PREVIEW tests (Paul: "yes, run the preview too"): a fixed window of 5 full years, below the 6-year minimum, never
  # a fallback. Every PREVIEW output carries PREVIEW_FLAG.
  PREVIEW_WINDOW = c(2021, 2025),
  PREVIEW_MIN_YEARS = 5,
  PREVIEW_FLAG = "PREVIEW - below the 6-year minimum",

  # Expected control (02).
  EXPECTED_CONTROL_FILL_YEARS = c(2023, 2026),
  EXPECTED_CONTROL_SHEET = "expected_control_2023_2026",
  EXPECTED_CONTROL_MARKETS_SHEET = "expected_control_markets",
  EXPECTED_CONTROL_538_SHEET = "expected_control_538",

  # Inference: wild cluster restricted bootstrap, Webb six-point weights; clusters = sectors (sector-year tests) or
  # champions (H5, bioguide).
  SEED = 20260925,
  BOOT_B = 9999,  # random draws when 6^G > BOOT_B; all 6^G draws are enumerated otherwise
  ALPHA = 0.05,
  CI_LEVEL = 0.95,

  # Job tiers of 04 tier_by_year. Employee is the reference tier of the pooled tier model; Corporate is separate.
  TIERS = c("Chief", "Middle Management", "Employee", "Corporate"),
  TIER_MODEL_TIERS = c("Chief", "Middle Management", "Employee"),
  TIER_REFERENCE = "Employee",
  TIER_INTERACTED = c("Chief", "Middle Management"),
  CORPORATE_TIER = "Corporate",

  # Year-level ("national") regressors: identical for every sector in a year.
  NATIONAL_VARS = c("pres_year", "midterm_year", "exp_dem_house", "exp_dem_senate", "cur_dem_house",
                    "cur_dem_senate", "exp_shift_house", "exp_shift_senate", "pred_dem_seat_change_house",
                    "pred_dem_seat_change_senate", "gb538_margin_house"),

  DV_LABELS = c(
    contributions_real_m = "general giving (04), all recipient categories, $M 2025",
    lobby_income_real_m = "LDA outside-firm lobbying income (01), $M 2025",
    lobby_expenses_real_m = "LDA self-filer lobbying expenses (01), $M 2025",
    lobby_amount_undiff_real_m = "LobbyView undifferentiated amount, high confidence (01), $M 2025"
  ),

  # ---- H5, industry champions (05 `data` sheet; unit = board x champion x cycle) --------------------------------
  CHAMPIONS_FILE = "05_industry_champions.xlsx",   # in the input folder
  CHAMPIONS_RECEIPT = "build_receipt_05.json",     # default location: the parent of the input folder
  CHAMPIONS_QUIET_MINUTES = 10,
  H5_KEY = c("board", "bioguide", "cycle"),
  H5_REQUIRED = c("board", "bioguide", "cycle", "status", "up_for_election", "lost_primary", "chamber", "party",
                  "seniority_years", "toughness_general"),
  H5_DV_PRIMARY = c("industry_money_primary_real_2025_usd", "direct_giving_real_2025_usd"),
  H5_DV_TRADE = c("industry_money_with_trade_real_2025_usd"),
  H5_DV_LABELS = c(
    industry_money_primary_real_2025_usd = "industry money, primary definition (05), USD 2025",
    direct_giving_real_2025_usd = paste0("direct giving to the champion's authorized committees (05), USD 2025 - ",
                                         "employee channel only"),
    industry_money_with_trade_real_2025_usd = "industry money including trade associations (05), USD 2025"
  ),
  H5_DV_FALLBACK_FLAG = "employee channel only",
  H5_USABLE_DV_STATUS = c("observed", "observed_zero"),
  H5_USABLE_ROW_STATUS = c("observed", "partial"),
  H5_PARTIAL_CYCLES = 2026,
  H5_MIN_CYCLES = 3,
  H5_MIN_MEMBER_CYCLES = 30,
  H5_PARTY_REFERENCE = "R",
  H5_CHAMBER_REFERENCE = "House",
  H5_GENERAL_MARGIN_FLAG = "outcome-contaminated: money affects margins",

  # ---- Paul's rulings of 2026-09-25 night (rule set "paul-2026-09-25") --------------------------------------------
  LOBBYVIEW_ALL_SHEET = "lobbyview_sector_year_all",       # 01 sheet: LobbyView for every study sector, every year
  LOBBYVIEW_DEDUP_COLUMN = "lobby_amount_dedup_real_2025_usd",  # primary LobbyView amount once 01 has it
  LOBBYVIEW_MIN_CLUSTERS_INFERENCE = 3,                    # >= 3 sector clusters: bootstrap inference, else DESCRIPTIVE
  LOBBYVIEW_LIMITATIONS = c(
    paste0("LobbyView NAICS sectors (life_insurance, auto_manufacturing, credit_arms, property_casualty, telecom) cover ",
           "NAICS-coded listed companies only, with no trade associations; telecom lacks Comcast, Charter and Cox."),
    paste0("LobbyView roster sectors (crypto, fintech) rest on name matching, which has small false matches; they are ",
           "listed in build_receipt_01_lobbyview_all.json."),
    paste0("The undifferentiated LobbyView sum double counts the outside-firm fees of self-filers (a median 9-26% by ",
           "sector); the primary series is the de-duplicated amount once 01 carries it, the undifferentiated sum a ",
           "robustness variant."),
    paste0("Thin sector-years (coverage_flag 'thin': fewer than 5 reporting clients) are excluded from the primary ",
           "LobbyView sample, which drops credit_arms entirely and crypto before 2015 (name-match artifacts); a ",
           "robustness variant keeps them.")),
  CHAMBER_FILE = "08_contributions_by_chamber.xlsx",
  CHAMBER_SHEET = "sector_year_chamber",
  COMPANY_PAC_CATEGORY = "Company PAC",                    # 04 recipient_category of gifts to the roster company's PAC
  POPULATION_NOTE = "growth = whole industry (IBISWorld); spending = 10-company roster",
  MULTIYEAR_FLAG = paste0("compliant (i): multi-year projection used only for the spending year right after its ",
                          "publication (vintage rule); not the comparable annual input"),

  # ---- rulings of 2026-09-26 (coordinator for Paul; rule set paul-2026-09-25 only) --------------------------------
  # Near-collinearity: a control whose R^2 on the fixed effects plus the other regressors is >= this is dropped and
  # named, as exactly collinear controls are (models that drop controls: H5).
  NEAR_COLLINEAR_R2 = 0.9999,
  # Telecom growth: 07 / 06 carry wireless (51721) and cable (51711a) components; Paul's ask combines them by revenue.
  TELECOM_COMPONENT_CODES = c(telecom_wireless = "51721", telecom_cable = "51711a"),
  TELECOM_COMPONENT_TAGS = c(telecom_wireless = "tw", telecom_cable = "tc"),
  # Bank split: Mentat "banking" (big banks) and community_banks as two sectors sharing the commercial-banking
  # (IBISWorld 52211) growth series.
  BANK_SPLIT_BIG = "big_banks",
  BANK_SPLIT_COMMUNITY = "community_banks",
  # Mentat books (the 04 units) and the study sector each one is (the coverage table).
  MENTAT_BOOKS = c(banking = "Banking", community_banks = "Community Banks", credit_union = "Credit Union",
                   credit_arms = "Credit Arms", crypto = "Crypto", fintech = "Fintech",
                   property_casualty_insurance = "P&C", telecom = "Telecom"),

  # ---- SHIFT, TRENDS, FORECAST (coordinator for Paul, 2026-09-26; rule set paul-2026-09-25 only) -----------------
  # SHIFT (Paul: "does that money shift more toward the party in favor to take control?"): the Democratic share of
  # contributions on expected Democratic control. Units = every Mentat industry of 04 / 08 (the seven study sectors
  # with a Mentat book plus community_banks). 08 sheets: sector_year_chamber (candidate committees) and
  # sector_year_chamber_with_hill (DCCC / DSCC added to D, NRCC / NRSC to R). Every 04 funding source stays in (Paul:
  # "Keep those receipts": the non_giving "other receipt" rows are never dropped; there are no giving-only variants).
  CHAMBER_HILL_SHEET = "sector_year_chamber_with_hill",
  SHIFT_PARTIES = c(D = "D", R = "R"),     # 04 party values counted; "Other / Unclassified" is outside both
  # Flags carried on the shift tables' rows (sheet shift_year / shift_chamber, column shift_flag) and printed where a
  # sample holds the row. chamber = NA: the unit-year's all-giving (04) row. Verifiable facts only (coordinator's rulings
  # of 2026-09-26): 08 hill_committees_sector_year (NRSC, fintech, 2026), 04 data (Kalshi, Party Committee, party R) and
  # the donor-level rows of the pinned fintech analytics index (facts, committee C00027466 "NRSC", 2026): MANSOUR, TAREK
  # (KALSHI, 2026-04-28) and LARA, LUANA LOPES (KALSHI, 2026-04-29), each $250,000.00 in three rows of $44,300.00,
  # $72,800.00 and $132,900.00; the same contributors' other 2026 Kalshi rows give their occupations as CEO/CO-FOUNDER and
  # CO-FOUNDER (Paul's option A).
  SHIFT_FLAGS = list(
    list(study_sector = "fintech", year = 2026, chamber = "Senate",
         text = paste0("fintech Senate 2026: partial year; $501,549.59 of fintech-sector giving to the NRSC, of which $500,000.00 ",
                       "from Kalshi's co-founders MANSOUR, TAREK and LARA, LUANA LOPES (verified from donor-level rows); 04 shows ",
                       "$600,000 from Kalshi employees to Republican party committees")),
    list(study_sector = "fintech", year = 2026, chamber = NA_character_,
         text = paste0("fintech 2026: partial year; $501,549.59 of fintech-sector giving to the NRSC, of which $500,000.00 from ",
                       "Kalshi's co-founders MANSOUR, TAREK and LARA, LUANA LOPES (verified from donor-level rows); 04 shows ",
                       "$600,000 from Kalshi employees to Republican party committees"))),
  # SHIFT minimum base: a share whose nominal D + R base is below the threshold is left out (unit x year x chamber cells;
  # unit x year for SHIFT-All). The thresholds were chosen after the preview results were seen, so they exist only as
  # EXPLORATORY variants flagged POST_RESULT_FLAG (coordinator's revision of 2026-09-26, after the Codex methodology
  # review); the pre-specified SHIFT models have no minimum base.
  SHIFT_MIN_BASE_EXPLORATORY = c(B25K = 25000, B10K = 10000, B50K = 50000),
  POST_RESULT_FLAG = "EXPLORATORY: post-result exploratory choice",
  # Term labels (coordinator's revision of 2026-09-26): a saturated SHIFT term (no year-level residual df) and a
  # per-sector term resting on one sector cluster are DESCRIPTIVE: estimate shown, their bootstrap lines reference only.
  SATURATED_LABEL = "DESCRIPTIVE (SATURATED)",
  ONE_CLUSTER_LABEL = "DESCRIPTIVE (one sector cluster)",
  # Chronology (coordinator's revision of 2026-09-26): expected control is measured at 02 last_price_date (IEM annual
  # mean) or 02 expected_control_2023_2026 measured_on; a value measured after 31 December of its year is
  # retrospective. The main series stays as Paul ruled, labelled RETRO_LABEL; the STRICT variants leave such values out.
  RETRO_LABEL = "expected control = RETROSPECTIVE / NOWCAST series (Paul's ruling kept)",
  # What 04 general giving measures (coordinator's revision of 2026-09-26, the review's measurement audit).
  MONEY_LABEL = paste0("included receipts: 04 general giving, every recipient category and every funding_source - ",
                       "employee_original, organization_unverified, non_giving and the rest, kept per Paul (\"Keep those ",
                       "receipts\") - so not verified employee or corporate giving; gifts through the ActBlue / WinRed conduits can ",
                       "also appear on the candidate's report (08 notes n6), so conduit and candidate receipts can overlap"),
  EXP_VARS = c("exp_dem_house", "exp_dem_senate", "exp_dem_own_chamber"),
  # Strict forecast backtest: the forecast origin of target year T is 1 February of T (after the prior year's LDA fourth-
  # quarter reports, due 20 January, and FEC year-end reports, due 31 January); a predictor value enters a strict
  # forecast only if it was available by the origin (fixed before any strict result was seen; nothing is tuned).
  # SEATS (Paul's follow-up, 2026-09-26: "What about the partisanship of the spending as it correlates to expected seat
  # gain for a party in the upcoming election?"): the party share of each election cycle's spending on the forecast
  # Democratic net seat gain for that election, House and Senate separately. Cycles are election years (cycle 2022 =
  # calendar 2021-2022); both calendar years must be complete, so the partial 2026 cycle never enters.
  SEATS_WINDOW = c(2020, 2024),
  SEATS_W_FILE = "09_weekly_partisan_seat_forecasts.xlsx",
  SEATS_W_PRIMARY = "538 lite",
  SEATS_W_SOURCES = c(lite = "538 lite", classic = "538 classic", deluxe = "538 deluxe", cb = "crystal_ball"),
  SEATS_W_WINDOW = c(2016, 2024),
  SEATS_W_QUIET_MINUTES = 10,
  # SEATS race level (coordinator's contract of 2026-09-26, after the Codex reviews): workbook 10 (recipient
  # classification and dated service terms) and workbook 11 (the verified 538 House district and Senate state forecasts
  # with available_at, and the dated expert ratings), both read-only. A 538 row is available at the latest of its forecast
  # date, the date of its run timestamp, its available_at and the 2022 public model launch (30 June 2022: earlier dated
  # records were run later), and it enters a spending window only when available strictly before the window's first day.
  SEATS_10_FILE = "10_recipient_classification.xlsx",
  SEATS_11_FILE = "11_race_forecasts_and_ratings.xlsx",
  SEATS_538_LAUNCH = c("2022" = "2022-06-30"),
  # the first Monday after the last state primary of the cycle (2022: 13 September), from the coordinator's review; the
  # windows from it on are the national post-primary sensitivity (2022: 7 weeks, DESCRIPTIVE)
  SEATS_POST_PRIMARY_START = c("2022" = "2022-09-19"),
  SEATS_FAVORED_P = 0.5,             # forecast-favored: the candidate's own named 538 Lite probability above one half
  SEATS_FAVORED_P_SENS = 0.6,        # sensitivity
  SEATS_MIN_WEEKS = 12,              # weekly regressions with fewer usable weeks are DESCRIPTIVE only
  FORECAST_ORIGIN_MMDD = "02-01",
  AVAILABLE_LDA_MMDD = "01-20",       # a lobbying year's amount: available on 20 January of the next year
  AVAILABLE_FEC_MMDD = "01-31",       # a contribution year's amount: available on 31 January of the next year
  AVAILABLE_CONTROL_MMDD = "01-31",   # current control of year t: the majority seated by January of t
  # FORECAST backtest (the Mentat Insights upgrade test): rolling-origin one-step-ahead forecasts. LobbyView: outcome
  # years 2008-2023 (a lag level may come from 2007), targets 2014-2023. Contributions: outcome years 2020-2025 (lag
  # 2019), targets 2023-2025, run only once the 2020 cycle is in 04.
  FORECAST_LV_YEARS = c(2008, 2023),
  FORECAST_LV_TARGETS = 2014:2023,
  FORECAST_C_YEARS = c(2020, 2025),
  FORECAST_C_TARGETS = 2023:2025,
  FORECAST_FEW_TARGETS_FLAG = "FEW TARGETS"
)

SGS$DATA_DIR <- file.path(SGS$STUDY_ROOT, "data")
SGS$RESULTS_DIR <- file.path(SGS$STUDY_ROOT, "results")

# Status vocabulary (panel.py)
SGS_OBS <- "observed"
SGS_PARTIAL <- "partial"
SGS_MISSING <- "missing"
SGS_NA <- "not_applicable"
SGS_USABLE_STATUSES <- c("observed", "derived")
SGS_TELECOM_COMPONENTS <- c("telecom_wireless", "telecom_cable")

# Estimability statuses (gates.py)
SGS_ESTIMABLE <- "ESTIMABLE"
SGS_NOT_ESTIMABLE <- "NOT ESTIMABLE"
SGS_NOT_BUILT <- "NOT BUILT"

SGS_RULESETS <- c("paul-2026-09-25", "python-parity")

# The behaviour switches of a rule set. Every switch is FALSE / "python" in the parity rule set, so that rule set
# reproduces code/sgs exactly.
sgs_rules <- function(name = "paul-2026-09-25") {
  name <- match.arg(name, SGS_RULESETS)
  paul <- identical(name, "paul-2026-09-25")
  list(
    name = name,
    # 1. expected control: Python reads 02 expected_control_markets first for 2023-2026 when the sheet exists; Paul
    #    ("Why are we using Polymarket and Kalshi"): never read it. 2008-2022 = IEM annual means; 2023-2026 = 02
    #    expected_control_2023_2026 (method and flag carried). 02 expected_control_538, when present, feeds the
    #    robustness family H4-538 (House generic-ballot margin in place of exp_dem_house), never the main measure.
    read_markets = !paul,
    fill_sheet_first = paul,
    h4_538 = paul,
    # 2. LobbyView ("no Lobbyview can go all the way"): 01 lobbyview_sector_year_all, every study sector and year;
    #    the normal window rule without the 10-year cap on the fallback window; bootstrap inference with >= 3 sector
    #    clusters, DESCRIPTIVE with 2. NOT BUILT until the sheet exists. Python: 01 data LobbyView rows (banks and
    #    credit unions, high confidence), DESCRIPTIVE.
    lobbyview = if (paul) "all_sectors" else "python",
    # 4. PAC double counting: overlap table and the de-duplicated DV (no gifts to a roster company's own PAC).
    pac_dedup = paul,
    # 5. population mismatch stated on every growth test.
    population_note = paul,
    # 6. compliant (i): multi-year projections (06 crypto and fintech CAGRs) as a separate family.
    multiyear = paul,
    # 7. DS-House / DS-Senate from 08 sector_year_chamber replace the DS stubs.
    ds_chamber = paul,
    # 8. 06 component_forecasts study_sector "Fintech" / "Telecom" read as the study sectors fintech / telecom.
    normalise_06_labels = paul,
    # Rulings of 2026-09-26 (coordinator, relaying Paul):
    # 9. a control with R^2 >= 0.9999 on the fixed effects plus the other regressors is dropped and named (H5-within:
    #    seniority_years is champion + cycle by construction).
    near_collinear_r2 = if (paul) SGS$NEAR_COLLINEAR_R2 else NA_real_,
    # 10. telecom growth = the revenue-weighted wireless + cable components (07 actual, 06 component forecasts), with
    #     component-level ROBUSTNESS variants; crypto / fintech one-year growth values of 06 enter predicted growth.
    telecom_combined = paul,
    annual_proxies = paul,
    # 11. a sector with a single complete sector-year is left out of fixed-effect samples (its sector fixed effect
    #     absorbs it: no information, but it would count as a cluster).
    drop_singletons = paul,
    # 12. new families: ASYM (declines), DECEL (deceleration), SLOPES (a growth slope per sector), H4 read-outs of the
    #     LobbyView tests, the bank split (big vs community banks) and the telecom component robustness.
    extensions_0926 = paul,
    # 13. SHIFT: the Democratic share of contributions (08 House / Senate candidate committees, stacked chambers, and all
    #     party-labelled 04 giving) on expected Democratic control, with Hill / first-difference / dollar-weighted
    #     robustness and a 2021-2025 preview; DS+Hill reads 08 sector_year_chamber_with_hill when it is present.
    shift = paul,
    # 14. TRENDS: sign and size of every focal term of every estimable test first (pooled and per sector), whether the
    #     sign agrees across the test's variants, then p and CI (Paul: "Doesn't matter if it is significant if the trend
    #     is there").
    trends = paul,
    # 15. FORECAST: the rolling-origin one-step-ahead backtest of the spending models (LobbyView now; contributions once
    #     2020 lands).
    forecast = paul,
    # Coordinator's revisions of 2026-09-26 (after Paul's fit question and the Codex methodology review):
    # 16. FIT: every summary block's adjusted R^2 next to the previous R run's, with the reason for any difference.
    fit = paul,
    # 17. L-LV robustness: year-FE, log, log with year FE, LOSO, LOYO and FD variants of L1-LV..L3-LV on the base test's
    #     gated sample, and first differences with year effects (EXPLORATORY, no inference) with LOSO / LOYO.
    lv_robustness = paul,
    # 18. inference diagnostics of every focal term: adjusted R^2 with and without it on the same rows, two-way (sector
    #     and year) cluster-robust sensitivity, effective temporal support, DESCRIPTIVE term labels, Holm-adjusted p
    #     within the pre-specified families.
    inference_diag = paul,
    # 19. chronology: measured_at / available_at of every expected-control value, the RETROSPECTIVE / NOWCAST label, the
    #     STRICT variants and the strict (available-at-origin) forecast backtest.
    chronology = paul,
    # 20. SEATS (Paul's follow-up on forecast seat gains): SEATS-A, sector x election cycle, DESCRIPTIVE (the final Crystal
    #     Ball call against the cycle's party share and D$ / R$); SEATS-W, dated weekly giving against the prior 538
    #     forecast (09 workbook), EXPLORATORY, NOT BUILT until 09 exists.
    seats = paul
  )
}
