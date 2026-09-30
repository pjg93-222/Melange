# Run the whole study: load -> panel -> registry -> gates -> estimate -> report (R port of code/sgs/run_all.run()),
# with Glass Box events and a run receipt. The command-line entry point is run_all.R.

SGS_PY_BUILD_NOTES <- c(
  paste0("Labels not fixed by the brief are this build's assignment: H1/H4 read-outs, H1-phase-only, E1, T, DS, H5-pooled and ",
         "H5-within = EXTENSION; C1-C3 and L1-L3 (nine DV runs) = CORE; H4-shift, H4-seatcalls, core_reduced and the H5 ",
         "secondary regressors = EXPLORATORY; R-* and the H5 variants = ROBUSTNESS; L1-LV..L3-LV = DESCRIPTIVE (Paul's option (a))."),
  paste0("Fallback window (ruling of 2026-09-25): only when the primary 2020-2025 window fails, the most recent run of >= 10 ",
         "consecutive calendar years within 2008-2025 in which the test's complete-case sample exists; the window used is that ",
         "run's most recent 10 years (config.FALLBACK_WHOLE_RUN = False, matching the ruling's LobbyView example 2013-2022). ",
         "The fixed 2016-2025 fallback is retired. Each test records its search (fallback_search)."),
  paste0("L1-LV..L3-LV use lobby_amount_undiff_real_m (LobbyView, high confidence: commercial_banks and credit_unions, ",
         "2006-2023): L-test controls, sector baselines, DESCRIPTIVE (estimate and HC1 error only; 2 sectors, so the wild ",
         "cluster bootstrap cannot reach p < 0.056). They are never added to LDA amounts; the LDA L tests are unchanged."),
  paste0("L tests carry 6 national regressors, i.e. 7 year-level parameters with the sector baselines; 6 distinct years cannot ",
         "identify them, so L tests can only pass in a fallback window."),
  paste0("H4-seatcalls uses election years only, so its sample never holds consecutive calendar years: it cannot pass the ",
         "fallback, and holds at most 3 distinct years in 2020-2025."),
  "H4-shift in lobbying models keeps cur_dem, so exp_shift reparametrises exp_dem and returns the same coefficients.",
  paste0("Leave-one-year-out sub-fits have one year fewer than the window minimum by construction; they are flagged diagnostic. ",
         "Leave-one-out tests are gated on their parent sample."),
  "First differences pair year t with t-1 inside each sector; the lag level may come from the year before the window.",
  paste0("Telecom sector growth is withheld (components kept separate per the plan); wireless and cable component growth are ",
         "carried as separate sector_year columns and enter no test."),
  paste0("04 names its study-sector column `study_sector` (renamed from `sector`, 2026-09-25); the loader now requires ",
         "`study_sector` in every sheet that carries study sectors."),
  paste0("Expected control 2023-2026 (Paul's ruling of 2026-09-25): exp_dem_* = the IEM annual mean (02 data) where present, ",
         "else 02 expected_control_2023_2026: 2023-2024 = 1 if the Crystal Ball final call for the 2024 election (4 Nov 2024) ",
         "projects >= 218 Democratic House / >= 51 Democratic Senate seats, else 0 (method forecaster_final_call_binary; 2023 ",
         "flagged 'measured Nov 2024, after the year'); 2025-2026 = 1 - p_rep_control, the normalized mean of Kalshi and ",
         "Polymarket read 24-25 Sep 2026 (method market_snapshot; 2025 flagged 'measured Sep 2026, after the year'). A future ",
         "02 sheet expected_control_markets (daily history) takes precedence for 2023-2026 when present. Method and flag are ",
         "carried into the panel (exp_dem_*_method, exp_dem_*_flag) and listed per test (input_flags)."),
  paste0("PREVIEW (Paul: 'yes, run the preview too'): C1-PV..C3-PV on contributions_real_m and H1-PV, fixed window 2021-2025 ",
         "(5 full years, BELOW the 6-year minimum; no fallback). Specifications: (i) reduced = sector FE + pres_year + ",
         "midterm_year + focal growth; (ii) year FE = sector FE + year FE + focal growth; the full core specification (with ",
         "exp_dem) is NOT IDENTIFIED when its year-level parameters are as many as the distinct years (not forced). H1-PV: ",
         "every Mentat industry of 04 (seven study sectors plus community_banks). Every PREVIEW output carries 'PREVIEW - ",
         "below the 6-year minimum'."),
  paste0("H5 (05 data sheet, unit board x champion x cycle) has its own gate: >= 3 cycles, >= 30 member-cycles, non-zero focal ",
         "variance (member-cycle based, not the 6-year sector-year gate). Sample up_for_election = 1; lost-renomination rows ",
         "only in the primary models; 'no_authorized_committee' zeros (0 by construction) and 2020 (no money collected) do not ",
         "enter. Clusters: champions (bioguide); CR1 plus wild cluster restricted bootstrap. 05 is read at run time only and is ",
         "NOT BUILT when missing, when its receipt or file is younger than 10 minutes, when its bytes differ from its receipt, ",
         "or when expected columns are missing.")
)

sgs_paul_build_notes <- function() c(
  paste0("Engine: R (this run). The Python package code/sgs is frozen as the parity reference; the R port reproduces its 139 ",
         "tests exactly on the snapshot of run analysis-20260925T223615Z (rule set python-parity), including the bootstrap draws ",
         "(numpy's SeedSequence + PCG64 + Generator.choice are reimplemented in sgs_rng.R)."),
  paste0("Labels: C1-C3 and L1-L3 (nine DV runs), L1-LV..L3-LV and SHIFT-House / -Senate / -Chamber / -All / -All-House / ",
         "-All-Senate = CORE; H1/H4 read-outs, H1-phase-only, E1, T, DS = EXTENSION; ",
         "H4-shift, H4-seatcalls, core_reduced, MY (compliant (i)), the H5 secondary regressors, FDY-* and the SHIFT minimum-base ",
         "variants -B25K / -B10K / -B50K (post-result exploratory choices) = EXPLORATORY; R-* (with the L-LV family), STRICT-*, ",
         "H4-538, DS+Hill, SHIFT-*-Hill / -FD / -W / -STRICT and the H5 variants = ROBUSTNESS; PREVIEW as before (SHIFT-*-PV ",
         "included). A LobbyView test with 2 sector clusters would be DESCRIPTIVE; so is a saturated or one-cluster term."),
  SGS_PY_BUILD_NOTES[2],
  SGS_PY_BUILD_NOTES[c(4:8, 10)],
  paste0("Telecom (Paul's ask of 2026-09-26; the plan kept the components separate): telecom's growth is the revenue-weighted ",
         "combination of the wireless (IBISWorld 51721) and cable (51711a) components, in every growth test: actual growth ",
         "(07) = growth of the summed component revenue (the components' growth weighted by year t-1 revenue in 07's common ",
         "constant-2024-USD basis), previous-year growth = the combined same-year growth of t-1; predicted growth (06 ",
         "component_forecasts) = the components' one-year forecasts weighted by each report's same-vintage baseline revenue ",
         "(06 marks the components aggregation_authorized = False: report scope changes move the weights). R-TW-* and R-TC-* ",
         "(ROBUSTNESS) use the wireless or the cable component alone. The weights, years and sources are in the ",
         "'Paul's rulings in this run' list below."),
  paste0("One-year growth values (rulings of 2026-09-26: 'use every sector-year that has one'): crypto and fintech have no ",
         "annual growth series (06 and 07 hold multi-year projections); the one-year values 06 does hold outside the strict ",
         "column (06 data collected_forecast_growth_pct with a one-year horizon; 06 component_forecasts one-year component ",
         "growth) enter predicted_growth_pct, flagged per sector-year (predicted_growth_flag, input_flags)."),
  paste0("Singleton sectors (rulings of 2026-09-26): a sector with one complete sector-year in a fixed-effect sample is left ",
         "out and counted in the exclusions: its sector fixed effect absorbs the row, which carries no information but would ",
         "count as a cluster."),
  paste0("Near-collinearity (rulings of 2026-09-26): after exact collinearity, a control whose R^2 on the fixed effects plus ",
         "the other regressors is >= ", sgs_py_repr_float(SGS$NEAR_COLLINEAR_R2), " is dropped and named in the model note, as ",
         "exactly collinear controls are (H5: seniority_years in the within-champion models, where it is champion entry plus ",
         "calendar time by construction; the pooled models keep it)."),
  paste0("New families (rulings of 2026-09-26), for L1-LV..L3-LV and C1-C3 (the C variants are gated like C1-C3 and become ",
         "estimable with them once the Mentat 2020 cycle lands): ASYM (g split into g_pos = max(g, 0) and g_neg = min(g, 0), ",
         "the bootstrap test g_pos = g_neg, declines counted per sector), DECEL (g, 1[g_t < g_{t-1}] and its interaction), ",
         "SLOPES (a growth slope per sector, with the bootstrap F test that all are equal; each slope rests on one sector ",
         "cluster, so its CR1 error and bootstrap are unreliable), H4-L1-LV..H4-L3-LV (exp_dem and cur_dem with the study's ",
         "inference), the bank split BS-* / BANK-* (big banks = Mentat banking and community banks as two sectors sharing ",
         "the commercial-banking growth series; the LobbyView versions need community_banks rows in 01)."),
  paste0("Paul's hypothesis (2026-09-26: \"if the industry contracted, they would spend more to meet their policy ",
         "objectives\"), for L1-LV now and C1 once 2020 lands: CONTRACT-a (contracted_prior = 1(growth_previous_year_pct < 0), ",
         "the level shift in the year after a contraction, with the L1 / C1 controls; the hypothesis predicts > 0), CONTRACT-b ",
         "(contracted_prior x factor(study_sector), with the joint tests that all are zero and all equal) and ASYM-SLOPES ",
         "(each sector's growth-year and decline-year slopes; the hypothesis predicts a NEGATIVE decline-year slope, since a ",
         "deeper contraction is a more negative g_neg; joint test that all decline-year slopes are zero). Per-sector terms rest ",
         "on one sector cluster each (unreliable CR1 / bootstrap, stated in the notes)."),
  paste0("Expected control (Paul, 2026-09-25 night): exp_dem_* = the IEM annual mean (02 data) for 2008-2022; 2023-2026 = 02 ",
         "expected_control_2023_2026 (2023-2024: 1 if the Crystal Ball final call for the 2024 election projects >= 218 Democratic ",
         "House / >= 51 Democratic Senate seats, else 0; 2025-2026: 1 - p_rep_control of the Kalshi/Polymarket snapshot read ",
         "24-25 Sep 2026), with its method and timing flag carried (2023: 'measured Nov 2024, after the year'; Paul: \"We have ",
         "the data for the 2023\"). 02 expected_control_markets is never read (Paul: \"Why are we using Polymarket and ",
         "Kalshi\"); it stays in the workbook."),
  paste0("H4-538 (robustness only, never the main measure): the 538 House generic-ballot margin (02 expected_control_538, series ",
         "generic_ballot_margin, within-year mean of 538's daily average, D minus R, points; 2025-2026 blank) replaces ",
         "exp_dem_house in each core test. 538's historical file (generic_topline_historical.csv) was generated in September ",
         "2020: a retrospective series, not a contemporaneous archive. The house_control_* / senate_control_* forecast rows ",
         "(2018, 2020, 2022 only) are not used."),
  paste0("LobbyView (Paul: \"no Lobbyview can go all the way\"): L1-LV..L3-LV read 01 lobbyview_sector_year_all, every study ",
         "sector and year, one row per sector-year (confidence other than low), partial 2024 excluded, thin sector-years ",
         "excluded; normal window rule with the whole qualifying fallback run (no 10-year cap); bootstrap inference with >= 3 ",
         "sector clusters. LobbyView and LDA stay separate series and families, never added together."),
  SGS$LOBBYVIEW_LIMITATIONS,
  paste0("Champions money (Paul, confirmed): direct employee giving plus company-PAC giving, trade PACs separate; unchanged."),
  paste0("PAC double counting (Paul, approved): sheet pac_overlap gives, per 04 unit x year, the share of general giving that ",
         "goes to the roster company's own PAC (04 recipient_category 'Company PAC'); R-dedup-C1..C3 rerun C1-C3 without those ",
         "gifts (ROBUSTNESS)."),
  paste0("Population mismatch (Paul, approved as a stated limitation): every test with a growth regressor carries the flag \"",
         SGS$POPULATION_NOTE, "\"."),
  paste0("Compliant (i), plan section 9: MY-C3, MY-L3-income, MY-L3-expenses, MY-L3-LV use each multi-year crypto / fintech ",
         "CAGR of 06 (supplemental_observations, component_forecasts) only for the spending year right after its publication, ",
         "the latest projection available by 31 December winning (sheet multiyear_register lists every record and why it is ",
         "used or not); NOT ESTIMABLE when too few observations. 06 component_forecasts labels 'Fintech' / 'Telecom' are read ",
         "as the study sectors fintech / telecom."),
  paste0("DS-House-C1..C3 and DS-Senate-C1..C3 (replacing the DS stubs): the Democratic share of general giving to House / ",
         "Senate candidate committees by sector-year (08_contributions_by_chamber.xlsx, sector_year_chamber, dem_share as ",
         "built; ActBlue and WinRed conduit money outside both), focal and controls as in C1-C3. Only 5.6% of general-giving ",
         "dollars reach House or Senate candidate committees (08 notes n11): every DS test reports its n and dollar base. ",
         "DS+Hill (robustness: DCCC and DSCC to D, NRCC and NRSC to R) reads 08 ", SGS$CHAMBER_HILL_SHEET, " (added 2026-09-26) ",
         "when it is present; without it, it needs per-committee columns in 08 other_recipients (NOT BUILT otherwise)."),
  paste0("SHIFT (Paul, 2026-09-26: \"does that money shift more toward the party in favor to take control?\"; CORE): the ",
         "Democratic share D / (D + R) of contributions on expected Democratic control; the hypothesis predicts a POSITIVE ",
         "coefficient. SHIFT-House / SHIFT-Senate: 08 House / Senate candidate committees on exp_dem of the chamber + its current ",
         "control + pres_year + midterm_year + unit baselines; SHIFT-Chamber: both chambers stacked on the own chamber's expected ",
         "and current control, timing, one baseline per unit x chamber (factor(chamber) + factor(study_sector) + their ",
         "interaction); SHIFT-All: all party-labelled 04 giving (party D / R) on exp_dem_house and exp_dem_senate jointly (with ",
         "timing; current control left out, since with both current-control terms the joint model has 7 year-level parameters, ",
         "more than any window's 5-6 years) and each alone (with its chamber's current control). ROBUSTNESS: -Hill (08 ",
         SGS$CHAMBER_HILL_SHEET, "), -FD (first differences) and -W (weighted by the D + R dollars). Units: every Mentat ",
         "industry of 04 / 08 (the seven study sectors with a book plus community_banks), clustered by unit. Main window ",
         "2020-2025 by the standard gate (on by itself once 2020 lands); PREVIEW 2021-2025 now (first-difference previews: >= 4 ",
         "year-to-year changes from the 5 preview years). Expected control varies only by year, so each focal term is identified ",
         "from 5-6 yearly values; every SHIFT block states the year-level parameters, the year-level residual df and each year's ",
         "OLS weight (SATURATED = no year-level df: the estimate is a fixed contrast of years). Every 04 funding source stays in ",
         "(Paul: \"Keep those receipts\"; the non_giving 'other receipt' rows are kept; no giving-only variants). Coordinator's ",
         "rulings of 2026-09-26: the unweighted models are primary (-W = ROBUSTNESS; weighting changes the population and the ",
         "question, so a -W difference is not evidence that small bases are noise); SHIFT-Chamber is the primary reading of the ",
         "preview; the saturated previews are ", SGS$SATURATED_LABEL, " (blocks kept and marked, out of the SHIFT table and the ",
         "Trends headline). Coordinator's revision after the Codex methodology review: the six pre-specified models stay primary ",
         "exactly as in run analysis-R-20260926T070630Z (no minimum base; the earlier proposal to make SHIFT-All primary and to ",
         "drop small-base shares, made after the results were seen, is withdrawn); the minimum-base variants -B25K / -B10K / ",
         "-B50K exist only as EXPLORATORY variants flagged '", SGS$POST_RESULT_FLAG, "'; -STRICT leaves out the expected-control ",
         "values measured after their year. The fintech 2026 flag's Kalshi co-founder attribution is verified from the ",
         "donor-level rows of the pinned fintech analytics index (Paul's option A)."),
  paste0("TRENDS (Paul: \"Doesn't matter if it is significant if the trend is there\"): sheet trends and the Trends section ",
         "give every focal term of every ESTIMABLE test, pooled and per sector, sign and size first in plain units ($M 2025, ",
         "share points, USD per toughness point), whether the hypothesis' sign holds, and whether the sign is the same across the ",
         "test's variants; p and CI after. A ", SGS$SATURATED_LABEL, " test keeps its rows in the sheet and takes no part in ",
         "the headline or the sign agreement; a ", SGS$ONE_CLUSTER_LABEL, " term shows no p or CI in the headline."),
  paste0("FIT (coordinator's ruling of 2026-09-26, after Paul: \"look at the adjusted r-squared\"): sheet fit and the Model fit ",
         "section give every summary block's multiple and adjusted R^2 as summary() prints them, next to the previous R run's ",
         "(read from its summaries file), with the reason for any difference (new DV, changed formula, sectors added or ",
         "removed, other years, a different n, a new or newly estimable test, changed inputs)."),
  paste0("Codex methodology review (coordinator's revision of 2026-09-26; the review of run analysis-R-20260926T070630Z, adopted ",
         "by the coordinator): (B) L1-LV..L3-LV get the robustness family of the core tests - R-yearFE, R-log, R-logFE (ln DV with ",
         "sector + year effects), R-LOSO, R-LOYO, R-FD - on the base test's gated sample, and first differences with year effects ",
         "(FDY, with its LOSO / LOYO; EXPLORATORY, no inference); the review's numbers are reproduced in the report. (C) every ",
         "focal term: adjusted R^2 with and without it on the same rows (sheet coefficients, section Incremental fit). (D) Holm-",
         "adjusted p within the pre-specified families (sheet multiplicity); the unadjusted p stays. (E) saturated and one-",
         "cluster terms are DESCRIPTIVE; a two-way (sector + year) cluster-robust sensitivity and the effective temporal support ",
         "of every focal term. (F) every expected-control value carries measured_at / available_at; the main series stays as ",
         "Paul ruled, labelled '", SGS$RETRO_LABEL, "'; STRICT variants (SHIFT, C1-C3, L1-LV..L3-LV) leave out values measured ",
         "after their year; the forecast backtest is reported retrospective and strict (every value available by the origin, 1 ",
         "February of the target year). (G) the 04 measure is labelled precisely: ", SGS$MONEY_LABEL, "."),
  paste0("FORECAST backtest (the Mentat Insights upgrade test): rolling-origin one-step-ahead forecasts, each target year ",
         "fitted only on the years before it: (0) naive, (0s) seasonal naive by cycle position, (1) + sector baseline + ",
         "pres/midterm, (2a) + predicted growth only (the strict-feasible growth model; new 2026-09-30), (2b) = the earlier model ",
         "(2): (2a) + prior-year growth (same-year growth is excluded; in the strict timing prior-year growth is unavailable at the origin as well unless its 07 ",
         "report vintage is dated by then: sheet forecast_asof counts the target sector-years that have it; runs before ",
         "2026-09-30 carry the id 2 for (2b), column prior_model_id), (3) + expected and current control, (4) + the ",
         "contraction indicator; models (1)-(4) predict the one-year change. A change model whose training design fails the ",
         "study's estimability gate at an origin (not identified, or fewer than ", SGS$MIN_RESID_DF, " residual df, or fewer than ",
         SGS$MIN_RESID_DF, " year-level residual df) is not dropped: ",
         "R8's wider window cannot be found for an expanding window that already starts in the first year of the panel, so its ",
         "forecast is kept, labelled DESCRIPTIVE, with the reason, outside the common set and each model's own set (the headline ",
         "sets are the origins that pass). LobbyView ",
         "(L-LV sectors) targets 2014-2023 now; contributions targets 2023-2025 once 2020 lands (FEW TARGETS). MAE, RMSE and the ",
         "share of sector-years beating naive, pooled and per sector, with the sector-equal MAE / naive MAE and the MASE (sheets ",
         "forecast_backtest, forecast_metrics, forecast_origins, forecast_asof), retrospective (final-vintage predictors) and ",
         "strict (available at the origin) reported separately."),
  SGS_PY_BUILD_NOTES[12:13]
)

SGS_FLAG_COLUMNS <- list(
  exp_dem_house = c("exp_dem_house_method", "exp_dem_house_flag"),
  exp_dem_senate = c("exp_dem_senate_method", "exp_dem_senate_flag"),
  exp_shift_house = c("exp_dem_house_method", "exp_dem_house_flag"),
  exp_shift_senate = c("exp_dem_senate_method", "exp_dem_senate_flag"),
  exp_dem_own_chamber = c("exp_dem_own_chamber_method", "exp_dem_own_chamber_flag")
)

# run_all.input_flags: expected-control inputs of the estimated (or last attempted) sample that do not come from the IEM
# annual mean: variable, year, method and timing flag (in the stacked SHIFT table: chamber and year).
sgs_input_flags <- function(spec, att) {
  if (is.null(att) || is.null(att$sample) || !nrow(att$sample$df)) return("")
  df <- att$sample$df
  parts <- character(0)
  for (v in sgs_required_vars(spec)) {
    fc <- SGS_FLAG_COLUMNS[[v]]
    if (is.null(fc) || !fc[1] %in% names(df)) next
    ch <- if ("chamber" %in% names(df) && identical(spec$table, "shift_chamber")) paste0(df$chamber, " ") else rep("", nrow(df))
    u <- unique(data.frame(c = ch, y = as.integer(df$year), m = df[[fc[1]]], f = df[[fc[2]]], stringsAsFactors = FALSE))
    u <- u[order(u$y, u$c, method = "radix"), , drop = FALSE]
    seen <- character(0)
    for (i in seq_len(nrow(u))) {
      if (is.na(u$m[i]) || u$m[i] == "iem_annual_mean") next
      seen <- c(seen, paste0(u$c[i], u$y[i], " ", u$m[i], if (!is.na(u$f[i]) && nzchar(u$f[i])) paste0(" (", u$f[i], ")") else ""))
    }
    if (length(seen)) parts <- c(parts, paste0(v, ": ", paste(seen, collapse = "; ")))
  }
  # rulings of 2026-09-26: growth inputs that are not a sector's strict series (telecom combined or one component;
  # one-year proxies of 06)
  for (v in sgs_required_vars(spec)) {
    if (!sgs_is_growth_var(v)) next
    base <- sub("_(pos|neg|decel|x_decel|tw|tc)$", "", v)
    tag <- regmatches(v, regexec("_(tw|tc)$", v))[[1]]
    seen <- character(0)
    tel <- df$study_sector == "telecom"
    if (any(tel)) {
      what <- if (length(tag)) paste0(names(SGS$TELECOM_COMPONENT_TAGS)[SGS$TELECOM_COMPONENT_TAGS == tag[2]], " component only")
              else "revenue-weighted wireless + cable components"
      if (length(tag) || any(c("telecom_growth_method", "telecom_predicted_method") %in% names(df))) {
        seen <- c(seen, paste0("telecom ", sgs_years_text(df$year[tel]), " ", what))
      }
    }
    if (identical(base, "predicted_growth_pct") && "predicted_growth_flag" %in% names(df)) {
      fl <- df$predicted_growth_flag
      k <- which(!is.na(fl) & !tel)
      for (s in sgs_sort_sectors(df$study_sector[k])) {
        ks <- k[df$study_sector[k] == s]
        seen <- c(seen, paste0(s, " ", sgs_years_text(df$year[ks]), " ", fl[ks][1]))
      }
    }
    if (length(seen)) parts <- c(parts, paste0(v, ": ", paste(seen, collapse = "; ")))
  }
  paste(parts, collapse = " | ")
}

# ASYM / DECEL (rulings of 2026-09-26): the sector-years with g < 0 (declines) or g_t < g_{t-1} (decelerations) per
# sector of the estimated (or last attempted) sample; a sector with none says so.
.count_text <- function(spec, att) {
  v <- spec$count_var %||% NA_character_
  if (is.na(v) || is.null(att) || is.null(att$sample) || !nrow(att$sample$df)) return("")
  df <- att$sample$df
  kind <- spec$count_kind %||% "decline"
  hit <- if (kind %in% c("decline", "contraction")) df[[v]] < 0 else df[[paste0(v, "_decel")]] %in% 1
  hit[is.na(hit)] <- FALSE
  none <- switch(kind, decline = "no declines", contraction = "no contraction years", "no decelerations")
  parts <- vapply(sgs_sort_sectors(df$study_sector), function(s) {
    m <- df$study_sector == s
    k <- sum(hit[m])
    paste0(s, " ", k, " of ", sum(m), if (k == 0) paste0(" (", none, ")") else paste0(" (", sgs_years_text(df$year[m & hit]), ")"))
  }, "")
  paste0(switch(kind, decline = paste0("Declines (", v, " < 0)"),
                contraction = paste0("Contraction years (contracted_prior = 1: ", v, " < 0, the industry contracted the year before)"),
                paste0("Decelerations (", v, " below its prior-year value)")),
         " per sector in the ", if (isTRUE(att$ok)) "estimated" else "last attempted", " sample: ",
         paste(parts, collapse = "; "), ".")
}

.attempt_fields <- function(att) {
  if (is.null(att)) return(list(n = NA, n_window = "", n_sectors = NA, sectors = "", n_years = NA, years = "", resid_df = NA))
  list(n = att$n, n_window = paste0(sgs_int_str(att$window[1]), "-", sgs_int_str(att$window[2])), n_sectors = length(att$sectors),
       sectors = paste(att$sectors, collapse = ", "), n_years = length(att$years), years = sgs_years_text(att$years),
       resid_df = att$resid_df)
}

.excl_text <- function(att) {
  if (is.null(att) || is.null(att$sample)) return("")
  paste(c(sgs_kv(att$sample$exclusions), att$sample$notes), collapse = "; ")
}

# Dollar base of a DS test's sample (Paul's ruling 7 and the 08 note: report n and the dollar base of every DS test).
.ds_base_text <- function(spec, att) {
  if (is.null(att) || is.null(att$sample) || !nrow(att$sample$df)) return("")
  ch <- sub("^dem_share_(hill_)?", "", spec$dv)
  df <- att$sample$df
  hill <- startsWith(spec$dv, "dem_share_hill_") && paste0(spec$dv, "_base_usd") %in% names(df)
  bu <- df[[paste0(if (hill) spec$dv else paste0("dem_share_", ch), "_base_usd")]]
  br <- df[[paste0(if (hill) spec$dv else paste0("dem_share_", ch), "_base_real_m")]]
  if (is.null(bu)) return("")
  cm <- df$contributions_real_m
  paste0("Dollar base (", nrow(df), " sector-years of the ", if (isTRUE(att$ok)) "estimated" else "last attempted",
         " sample): D + R to ", if (ch == "house") "House" else "Senate", " candidate committees",
         if (hill) paste0(" and the ", if (ch == "house") "DCCC / NRCC" else "DSCC / NRSC") else "", " $",
         sgs_py_fixed(sum(bu, na.rm = TRUE), 0, comma = TRUE), " nominal = $", sgs_fmt(sum(br, na.rm = TRUE)), "M 2025",
         if (!is.null(cm) && sum(cm, na.rm = TRUE) > 0) paste0(", ", sgs_py_fixed(100 * sum(br, na.rm = TRUE) / sum(cm, na.rm = TRUE), 2),
                                                             "% of the same sector-years' general giving ($",
                                                             sgs_fmt(sum(cm, na.rm = TRUE)), "M 2025)") else "",
         ".")
}

# Chronology (coordinator's revision of 2026-09-26): the years of the (last attempted) sample whose expected-control value
# was measured after its year.
.late_exp_years <- function(spec, att) {
  if (is.null(att) || is.null(att$sample) || is.null(att$sample$df) || !nrow(att$sample$df)) return("")
  df <- att$sample$df
  yrs <- numeric(0)
  for (v in intersect(sgs_required_vars(spec), SGS$EXP_VARS)) {
    ay <- paste0(v, "_after_year")
    if (ay %in% names(df)) yrs <- c(yrs, df$year[df[[ay]] %in% TRUE])
  }
  if (!length(yrs)) "" else sgs_years_text(sort(unique(yrs)))
}

# SHIFT minimum base (EXPLORATORY post-result variants): the cells of the (last attempted) sample whose nominal D + R base
# is below the test's threshold, each with its base.
.shift_min_base_cells_text <- function(cells) {
  if (is.null(cells) || !nrow(cells)) return("")
  paste0(cells$study_sector, " ", sgs_int_str(cells$year), ifelse(is.na(cells$chamber), "", paste0(" ", cells$chamber)), " $",
         vapply(cells$base_usd, sgs_py_fixed, "", d = 0, comma = TRUE), collapse = "; ")
}
.shift_min_base_text <- function(spec, att) {
  mbr <- if (!is.null(att) && !is.null(att$sample)) att$sample$min_base else NULL
  if (is.null(mbr)) return("")
  cells <- mbr$cells
  paste0("Minimum base $", sgs_py_fixed(mbr$threshold, 0, comma = TRUE), " (nominal D + R, column ", mbr$var, "): ", nrow(cells),
         " cell(s) of the ", if (isTRUE(att$ok)) "estimated" else "last attempted", " window left out",
         if (nrow(cells)) paste0(": ", .shift_min_base_cells_text(cells)) else "", ".")
}

# SHIFT (rulings of 2026-09-26): the dollars the shares of a SHIFT sample rest on. 08 tests: D + R to the chamber's
# candidate committees (Hill variants: plus the chamber's two party committees) and their share of the same unit-years'
# general giving; 04 tests: the party-labelled (D + R) dollars, their share of general giving ("the D + R share of
# dollars"), overall and by unit, the 'Other / Unclassified' dollars outside both and the non_giving rows kept.
.shift_base_text <- function(spec, att) {
  if (is.null(att) || is.null(att$sample) || !nrow(att$sample$df)) return("")
  df <- att$sample$df
  bu <- df[[paste0(spec$dv, "_base_usd")]]; br <- df[[paste0(spec$dv, "_base_real_m")]]
  if (is.null(bu) || is.null(br)) return("")
  what <- if (identical(spec$table, "shift_chamber")) "rows (unit x year x chamber)" else "unit-years"
  uy <- !duplicated(paste(df$study_sector, df$year))
  gg <- sum(df$general_giving_real_m[uy], na.rm = TRUE)
  pct <- function(a, b) if (is.finite(b) && b > 0) paste0(sgs_py_fixed(100 * a / b, 2), "%") else "n/a"
  lead <- paste0("Dollar base (", nrow(df), " ", what, " of the ", if (isTRUE(att$ok)) "estimated" else "last attempted", " sample, ",
                 sgs_years_text(df$year), "): ")
  small <- sum(bu < 1e4, na.rm = TRUE)
  cell_txt <- paste0(df$study_sector, " ", sgs_int_str(df$year), if ("chamber" %in% names(df)) paste0(" ", df$chamber) else "", " $",
                     vapply(bu, sgs_py_fixed, "", d = 0, comma = TRUE))
  tail_ <- paste0("; median base $", sgs_py_fixed(stats::median(bu, na.rm = TRUE), 0, comma = TRUE), ", ", small,
                  " under $10,000 (smallest: ", paste(utils::head(cell_txt[order(bu)], 2), collapse = ", "), ")")
  if (identical(spec$dv, "dem_share_all")) {
    oth <- sum(df$dem_share_all_other_real_m[uy], na.rm = TRUE)
    ng <- if ("general_giving_non_giving_real_m" %in% names(df)) sum(df$general_giving_non_giving_real_m[uy], na.rm = TRUE) else NA_real_
    by_unit <- vapply(sgs_sort_sectors(df$study_sector), function(s) {
      k <- df$study_sector == s & uy
      paste0(s, " ", pct(sum(br[k], na.rm = TRUE), sum(df$general_giving_real_m[k], na.rm = TRUE)))
    }, "")
    return(paste0(lead, "party-labelled general giving D + R $", sgs_fmt(sum(br, na.rm = TRUE)), "M 2025 ($",
                  sgs_py_fixed(sum(bu, na.rm = TRUE), 0, comma = TRUE), " nominal) = ", pct(sum(br, na.rm = TRUE), gg),
                  " of the same unit-years' general giving ($", sgs_fmt(gg), "M 2025); 'Other / Unclassified' $", sgs_fmt(oth),
                  "M 2025 is outside both", if (is.finite(ng)) paste0("; non_giving 'other receipt' rows ($", sgs_fmt(ng),
                                                                     "M 2025) are kept (Paul: \"Keep those receipts\")") else "",
                  ". D + R share of dollars by unit: ", paste(by_unit, collapse = ", "), tail_, "."))
  }
  hill <- grepl("hill", spec$dv, fixed = TRUE)
  ch <- if (identical(spec$table, "shift_chamber")) "House and Senate" else if (grepl("house", spec$dv, fixed = TRUE)) "House" else "Senate"
  paste0(lead, "D + R to ", ch, " candidate committees", if (hill) " plus the chamber's party committees (DCCC / NRCC, DSCC / NRSC)" else "",
         " $", sgs_py_fixed(sum(bu, na.rm = TRUE), 0, comma = TRUE), " nominal = $", sgs_fmt(sum(br, na.rm = TRUE)), "M 2025, ",
         pct(sum(br, na.rm = TRUE), gg), " of the same unit-years' general giving ($", sgs_fmt(gg), "M 2025)", tail_, ".")
}

# The report's SHIFT section: the hypothesis, the dollars the shares rest on, the flags, and one line per SHIFT test and
# focal term (b on the 0-1 share scale and in share points, p, CI, identification), NOT ESTIMABLE tests with their reason.
sgs_shift_md <- function(order_, est_rows, coef_rows, results, shift) {
  ids <- names(order_)[vapply(order_, function(t) t$family %in% c("SHIFT", "SHIFT-PV"), TRUE)]
  if (!length(ids) || is.null(shift)) return(character(0))
  rows <- setNames(est_rows, vapply(est_rows, `[[`, "", "test_id"))
  sy <- shift$shift_year
  win <- sy$year >= SGS$PREVIEW_WINDOW[1] & sy$year <= SGS$PREVIEW_WINDOW[2]
  pct <- function(a, b) if (is.finite(b) && b > 0) paste0(sgs_py_fixed(100 * a / b, 1), "%") else "n/a"
  k4 <- win & sy$dem_share_all_status %in% SGS_USABLE_STATUSES
  by_unit <- vapply(sgs_sort_sectors(sy$study_sector[k4]), function(s) {
    k <- k4 & sy$study_sector == s
    paste0(s, " ", pct(sum(sy$dem_share_all_base_real_m[k], na.rm = TRUE), sum(sy$general_giving_real_m[k], na.rm = TRUE)))
  }, "")
  k8 <- win & sy$dem_share_house_status %in% SGS_USABLE_STATUSES & sy$dem_share_senate_status %in% SGS_USABLE_STATUSES
  gg8 <- sum(sy$general_giving_real_m[k8], na.rm = TRUE)
  flags <- unique(stats::na.omit(c(sy$shift_flag_house, sy$shift_flag_senate, sy$shift_flag_all)))
  L <- c(paste0(SGS_SHIFT_HYPOTHESIS, " ", SGS_SHIFT_UNITS_NOTE), "",
         paste0("- Units in the SHIFT tables: ", paste(shift$units, collapse = ", "), "."),
         paste0("- D + R share of dollars, ", SGS$PREVIEW_WINDOW[1], "-", SGS$PREVIEW_WINDOW[2], " (04 party-labelled giving / all ",
                "general giving, every funding source): ", pct(sum(sy$dem_share_all_base_real_m[k4], na.rm = TRUE),
                                                                sum(sy$general_giving_real_m[k4], na.rm = TRUE)),
                " overall; ", paste(by_unit, collapse = ", "), ". The rest is 'Other / Unclassified' (party committees, PACs, ",
                "conduits and super PACs whose party 04 does not state)."),
         paste0("- 08 House + Senate candidate committees, same years: ", pct(sum(sy$dem_share_house_base_real_m[k8] + sy$dem_share_senate_base_real_m[k8], na.rm = TRUE), gg8),
                " of general giving (D + R)."),
         if (length(flags)) paste0("- Flag: ", flags) else character(0))
  est <- ids[vapply(ids, function(i) identical(rows[[i]]$status, SGS_ESTIMABLE), TRUE)]
  sat <- est[vapply(est, function(i) isTRUE(results[[i]]$identification$saturated), TRUE)]
  dfs <- setdiff(est, sat)
  # a first-difference estimate that equals its level model's estimate is the same contrast of the same years (a
  # saturated design on a balanced panel), not independent evidence
  same <- character(0)
  for (i in est[grepl("-FD(-PV)?$", est)]) {
    lv <- sub("-FD", "", i, fixed = TRUE)
    if (!lv %in% est) next
    a <- vapply(results[[i]]$coefs, `[[`, 0, "estimate"); b <- vapply(results[[lv]]$coefs, `[[`, 0, "estimate")
    if (length(a) == length(b) && length(a) && all(abs(a - b) <= 1e-9 * pmax(abs(a), abs(b), 1e-12))) same <- c(same, paste0(i, " = ", lv))
  }
  if (length(same)) {
    L <- c(L, paste0("- First differences repeat the level estimate exactly (the same saturated contrast of the same years on a ",
                     "balanced panel, so not independent evidence): ", paste(same, collapse = "; "), "."))
  }
  # the minimum-base variants (EXPLORATORY, post-result): the cells each ESTIMABLE one left out, tests with the same
  # threshold, column and cells grouped
  mb <- vapply(est, function(i) { el <- rows[[i]]$extra_lines; if (!is.null(el) && "minimum base" %in% names(el)) el[["minimum base"]] else "" }, "")
  mb_lines <- character(0)
  for (txt in unique(mb[nzchar(mb)])) {
    mb_lines <- c(mb_lines, paste0("  - ", txt, " Tests: ", paste(est[mb == txt], collapse = ", "), "."))
  }
  L <- c(L, paste0("- Primary reading: ", SGS_SHIFT_PREVIEW_READING, " ", SGS_SHIFT_WEIGHT_NOTE),
         paste0("- Minimum-base variants (", SGS$POST_RESULT_FLAG, "; thresholds $25,000 / $10,000 / $50,000 nominal D + R, chosen ",
                "after the preview results were seen): the cells each ESTIMABLE variant left out (the pre-specified models keep ",
                "every share):"),
         if (length(mb_lines)) mb_lines else "  - none",
         paste0("- Identification: ", SGS_SHIFT_ID_NOTE, " SATURATED (as many year-level parameters as years or cells, no ",
                   "year-level residual df; the estimate is a fixed contrast of the years, named in the identification line of ",
                   "its summary block): ", if (length(sat)) paste(sat, collapse = ", ") else "none", ". With year-level residual df: ",
                   if (length(dfs)) paste0(dfs, " (", vapply(dfs, function(i) sgs_py_str(results[[i]]$identification$df), ""),
                                           " df on ", vapply(dfs, function(i) sgs_py_str(results[[i]]$identification$cells), ""),
                                           " cells)", collapse = ", ") else "none", "."),
         paste0("- ", SGS$SATURATED_LABEL, " (coordinator's rulings of 2026-09-26): the saturated tests are left out of the table ",
                "below and of the Trends headline; their summary blocks stay in the summaries file, marked: ",
                if (length(sat)) paste(sat, collapse = ", ") else "none", "."),
         "", "| test | label | status | window | n | term | b (0-1 share) | share points | p | 95% CI | identification |",
         "|---|---|---|---|---:|---|---:|---:|---:|---|---|")
  for (id in ids) {
    r <- rows[[id]]
    if (is.null(r) || id %in% sat) next
    lab <- paste0(sgs_label_text(r$label), if (grepl(SGS$POST_RESULT_FLAG, .txt0(r$flag), fixed = TRUE)) " (post-result exploratory)" else "")
    if (!identical(r$status, SGS_ESTIMABLE)) {
      L <- c(L, paste0("| ", id, " | ", lab, " | ", r$status, " | | | | | | | | ",
                       .md_escape(if (nzchar(.txt0(r$reason_short))) r$reason_short else .txt0(r$reason)), " |"))
      next
    }
    ident <- results[[id]]$identification$short %||% character(0)
    for (c in Filter(function(c) identical(c$test_id, id) && is.null(c$left_out) && !identical(c$test, "joint"), coef_rows)) {
      L <- c(L, paste0("| ", id, " | ", lab, " | ", r$status, " | ", .txt0(r$window_used),
                       " | ", sgs_py_str(r$n), " | ", c$coefficient, " | ", sgs_fmt(c$estimate), " | ", sgs_fmt(100 * c$estimate),
                       " | ", sgs_fmt(c$boot_p), " | ", .md_escape(c$ci_text %||% ""), " | ",
                       .md_escape(if (c$coefficient %in% names(ident)) ident[[c$coefficient]] else ""), " |"))
    }
  }
  L
}

# The folder this file was sourced from (source() keeps the path in its frame as `ofile`): the run receipt hashes the code
# that actually ran. "" when unknown (the receipt then reads <study root>/code/R).
.sgs_sourced_dir <- function() {
  for (fr in rev(sys.frames())) {
    f <- get0("ofile", envir = fr, inherits = FALSE, ifnotfound = "")
    if (length(f) == 1L && is.character(f) && nzchar(f) && file.exists(f)) return(dirname(normalizePath(f, winslash = "/")))
  }
  ""
}
SGS_ENGINE_CODE_DIR <- .sgs_sourced_dir()

# The receipt's map of the engine: the hash of every code/R/*.R file by file name, list(<algorithm> = list(<file> = <hash>)).
# sha256 by digest when it is installed, else by openssl; with neither, md5 (tools::md5sum) under the key "md5".
sgs_engine_code_hashes <- function(code_dir = SGS_ENGINE_CODE_DIR) {
  if (!nzchar(code_dir)) code_dir <- file.path(SGS$STUDY_ROOT, "code", "R")
  files <- list.files(code_dir, pattern = "\\.R$", full.names = TRUE)
  files <- files[order(basename(files), method = "radix")]
  have_digest <- requireNamespace("digest", quietly = TRUE)
  have_openssl <- requireNamespace("openssl", quietly = TRUE)
  hash <- function(f) {
    if (have_digest) return(digest::digest(file = f, algo = "sha256"))
    if (have_openssl) return(unclass(as.character(openssl::sha256(file(f)))))   # unclass: the hash class breaks toJSON
    unname(tools::md5sum(f))
  }
  setNames(list(setNames(lapply(files, hash), basename(files))), if (have_digest || have_openssl) "sha256" else "md5")
}

sgs_rerun_command <- function(code_dir = file.path(SGS$STUDY_ROOT, "code", "R")) {
  paste0("& \"C:\\Program Files\\R\\R-4.6.0\\bin\\Rscript.exe\" \"",
         normalizePath(file.path(code_dir, "run_all.R"), winslash = "\\", mustWork = FALSE), "\"")
}

sgs_run <- function(window = SGS$DEFAULT_WINDOW, fallback = SGS$FALLBACK_SEARCH, seed = SGS$SEED, only = NULL,
                    B = SGS$BOOT_B, data_dir = SGS$DATA_DIR, results_dir = SGS$RESULTS_DIR, include_partial = FALSE,
                    run_id = NULL, log = function(...) message(...), now = NULL, rules = sgs_rules(), receipt_05 = NULL,
                    progress = NULL, command = NULL) {
  started <- Sys.time()
  paul <- identical(rules$name, "paul-2026-09-25")
  run_id <- run_id %||% paste0("analysis-R-", sgs_utc_stamp(started))
  dir.create(results_dir, recursive = TRUE, showWarnings = FALSE)
  emit <- function(stage, summary) if (is.function(progress)) progress(stage, summary)
  wbs <- sgs_load_all(data_dir, rules)
  emit("load", paste0("loaded ", length(wbs), " workbooks from ", data_dir))
  sy <- sgs_build_sector_year(wbs, rules)
  built <- attr(sy, "built") %||% list()
  syt <- sgs_build_sector_year_tier(wbs, sy)
  iy <- sgs_build_industry_year(wbs)
  tables <- list(sector_year = sy, sector_year_tier = syt, industry_year = iy)
  if (isTRUE(rules$extensions_0926)) {
    syb <- sgs_build_sector_year_banks(wbs, sy)
    tables$sector_year_banks <- syb
    built <- c(built, attr(syb, "built"))
  }
  shift <- NULL
  if (isTRUE(rules$shift)) {
    # SHIFT (Paul's partisan-allocation hypothesis): unit x year and the stacked unit x year x chamber tables
    shift <- sgs_build_shift_tables(wbs, sy)
    tables$shift_year <- shift$shift_year
    tables$shift_chamber <- shift$shift_chamber
    built <- c(built, shift$built)
  }
  seats <- NULL
  if (isTRUE(rules$seats) && !is.null(shift)) {
    # SEATS (Paul's follow-up of 2026-09-26): the party share of the spending on the forecast seat gain; the cycle tables,
    # 09 (the weekly national series) and the race level (10, 11), each NOT BUILT with its reason when absent
    seats <- sgs_build_seats(wbs, shift, data_dir, now)
    for (tn in SGS_SEATS_TABLES) tables[[tn]] <- seats$tables[[tn]]
    built <- c(built, seats$built)
    emit("seats", paste0("SEATS: weekly ", if (isTRUE(seats$weekly_ok)) "read" else paste0("NOT BUILT (", seats$weekly_reason, ")"),
                         "; race level ", if (isTRUE(seats$race$ok)) "built" else paste0("NOT BUILT (", seats$race$reason, ")")))
  }
  emit("panel", paste0("built ", paste(names(tables), collapse = ", ")))

  registry <- sgs_registry(rules)
  chosen_ids <- names(sgs_select(registry, only))
  for (t in registry) if (t$id %in% chosen_ids && (identical(t$variant, "derived") || isTRUE(t$matched))) chosen_ids <- union(chosen_ids, t$base)
  order_ <- registry[names(registry) %in% chosen_ids]
  extra <- list()
  for (t in order_) if (identical(t$variant, "derived")) extra[[t$base]] <- unique(c(extra[[t$base]], t$focal))
  champ <- NULL
  if (any(vapply(order_, function(t) identical(t$table, "champions"), TRUE))) {
    champ <- sgs_load_champions(data_dir, now = now, receipt_path = receipt_05)
    log(paste0("  05 champions: ", if (champ$ok) "loaded" else paste0("NOT BUILT: ", champ$reason)))
  }

  decisions <- list(); results <- list()
  k <- 0
  for (t in order_) {
    k <- k + 1
    # derived read-outs are decided with their source test; the progress count below still includes them (every 25th
    # test emits, derived or not)
    if (identical(t$table, "champions") && !identical(t$variant, "derived")) {
      d <- sgs_decide_h5(t, champ)
      decisions[[t$id]] <- d
      if (d$status == SGS_ESTIMABLE) results[[t$id]] <- sgs_estimate_h5(t, d, B = B, seed = seed)
      log(paste0("  ", t$id, ": ", d$status, if (d$status == SGS_ESTIMABLE) paste0(" (cycles ", sgs_cycles_text(sgs_h5_cycles(d$sample)), ")") else ""))
    } else if (!identical(t$variant, "derived")) {
      # matched variants (L-LV robustness) are fitted on their base test's gated sample
      d <- if (isTRUE(t$matched)) sgs_decide_matched(t, decisions[[t$base]], built = built) else
        sgs_decide(t, tables, window, fallback, include_partial = include_partial, built = built)
      decisions[[t$id]] <- d
      if (d$status == SGS_ESTIMABLE) {
        results[[t$id]] <- sgs_estimate(t, sgs_decision_chosen(d), B = B, seed = seed, extra_coefs = extra[[t$id]] %||% character(0))
      }
      log(paste0("  ", t$id, ": ", d$status, if (!is.null(d$window)) paste0(" (", d$window[1], "-", d$window[2], ")") else ""))
    }
    if (k %% 25 == 0) emit("estimate", paste0(k, " of ", length(order_), " tests decided"))
  }

  est_rows <- list(); coef_rows <- list(); strata_rows <- list(); sample_parts <- list(); attempts_by_test <- list()
  for (t in order_) {
    if (identical(t$table, "champions")) {
      d <- decisions[[t$id]]
      attempts_by_test[[t$id]] <- list()
      est_rows[[length(est_rows) + 1L]] <- sgs_h5_est_row(t, d)
      if (d$status == SGS_ESTIMABLE) {
        r <- results[[t$id]]
        coef_rows <- c(coef_rows, sgs_h5_coef_rows(t, d, r))
        strata_rows <- c(strata_rows, lapply(r$strata, function(s) c(s, list(test_id = t$id))))
        sample_parts[[length(sample_parts) + 1L]] <- sgs_h5_sample_rows(t, d)
      }
      next
    }
    src <- if (identical(t$variant, "derived")) t$base else t$id
    d <- decisions[[src]]
    att <- sgs_decision_chosen(d) %||% (if (length(d$attempts)) d$attempts[[length(d$attempts)]] else NULL)
    attempts_by_test[[t$id]] <- d$attempts
    reason <- if (d$status != SGS_ESTIMABLE) d$reason else ""
    iflags <- sgs_input_flags(t, att)
    short <- ""
    if (d$status == SGS_NOT_ESTIMABLE) short <- paste(vapply(d$attempts, sgs_attempt_compact, ""), collapse = " || ")
    else if (d$status == SGS_NOT_BUILT) short <- d$reason
    if (identical(t$variant, "derived") && nzchar(reason)) {
      reason <- paste0("from ", src, ": ", reason)
      short <- paste0("from ", src, ": ", short)
    }
    r <- results[[src]]
    descriptive <- isTRUE(r$descriptive)
    label <- if (descriptive && !identical(t$inference, "none")) "DESCRIPTIVE" else t$label
    dv_label <- if (!is.na(t$dv_label)) t$dv_label else (unname(SGS$DV_LABELS[t$dv]) %||% "")
    if (is.na(dv_label)) dv_label <- ""
    if (paul && t$dv %in% c("lobby_lv_real_m", "lobby_lv_thin_real_m") && nzchar(built$lobbyview_all$label %||% "")) {
      dv_label <- paste0(built$lobbyview_all$label, ", every study sector, ",
                         if (t$dv == "lobby_lv_real_m") "thin sector-years excluded" else "thin sector-years kept", ", $M 2025")
    }
    if (paul && identical(t$dv, "lobby_amount_undiff_real_m")) {
      dv_label <- paste0("LobbyView undifferentiated amount (01 ", SGS$LOBBYVIEW_ALL_SHEET, "), every study sector, thin ",
                         "sector-years excluded, $M 2025")
    }
    note <- t$note
    extra_line <- ""
    if (paul && t$family %in% c("DS", "DS+Hill")) {
      bt <- .ds_base_text(t, att)
      if (nzchar(bt)) { note <- paste0(note, " ", bt); extra_line <- paste0("- ", bt) }
    }
    if (paul && !is.na(t$count_var %||% NA_character_)) {
      ct <- .count_text(t, att)
      if (nzchar(ct)) { note <- paste0(note, " ", ct); extra_line <- paste0("- ", ct) }
    }
    extra_lines <- character(0)
    summary_note <- NULL
    tflag <- t$flag
    if (paul && t$dv %in% c("contributions_real_m")) dv_label <- paste0(SGS$MONEY_LABEL, ", $M 2025")
    if (isTRUE(rules$chronology) && any(sgs_required_vars(t) %in% SGS$EXP_VARS)) {
      # coordinator's revision of 2026-09-26: the main expected-control series is labelled retrospective / nowcast; a
      # STRICT test names the values it left out instead
      late <- .late_exp_years(t, att)
      tflag <- paste(Filter(nzchar, c(tflag, if (isTRUE(t$strict_time)) {
        "STRICT timing: expected-control values measured after their year left out"
      } else paste0(SGS$RETRO_LABEL, if (nzchar(late)) paste0("; measured after their year in this sample: ", late) else ""))),
      collapse = "; ")
    }
    if (paul && t$family %in% c("SHIFT", "SHIFT-PV")) {
      # SHIFT: the minimum-base cells left out (EXPLORATORY variants), the dollar base of the sample and how the year-level
      # focal term is identified (all also in the note; the summaries print them on their own lines under the model, so
      # their header keeps the note without them). A saturated model is DESCRIPTIVE (SATURATED) (coordinator's rulings).
      summary_note <- note
      mbt <- .shift_min_base_text(t, att)
      bt <- .shift_base_text(t, att)
      idt <- if (identical(d$status, SGS_ESTIMABLE)) paste(r$identification$text %||% character(0), collapse = " ") else ""
      if (nzchar(mbt)) note <- paste0(note, " ", mbt)
      if (nzchar(bt)) note <- paste0(note, " ", bt)
      if (nzchar(idt)) note <- paste0(note, " Identification: ", idt)
      extra_lines <- c(`minimum base` = sub("^Minimum base ", "", mbt), `dollar base` = sub("^Dollar base ", "", bt), identification = idt)
      extra_lines <- extra_lines[nzchar(extra_lines)]
      if (identical(d$status, SGS_ESTIMABLE) && isTRUE(r$identification$saturated)) {
        tflag <- paste(Filter(nzchar, c(tflag, SGS$SATURATED_LABEL)), collapse = "; ")
      }
    }
    af <- .attempt_fields(att)
    est_rows[[length(est_rows) + 1L]] <- c(
      list(test_id = t$id, family = t$family, label = label, status = d$status,
           window_used = if (!is.null(d$window)) paste0(sgs_int_str(d$window[1]), "-", sgs_int_str(d$window[2])) else "",
           window_kind = if (is.na(d$window_kind)) "" else d$window_kind),
      af,
      list(reason = reason, reason_short = short,
           default_attempt = if (length(d$attempts)) sgs_attempt_text(d$attempts[[1]]) else "",
           fallback_attempt = if (length(d$attempts) > 1) sgs_attempt_text(d$attempts[[2]]) else "",
           fallback_search = d$fallback_search, exclusions = .excl_text(att), dv = t$dv, dv_column = t$dv,
           dv_label = dv_label, focal = paste(t$focal, collapse = ", "), controls = paste(t$controls, collapse = ", "),
           fixed_effects = paste(t$fe, collapse = ", "), variant = t$variant, base_test = if (is.na(t$base)) "" else t$base,
           year_filter = if (is.na(t$year_filter)) "" else t$year_filter, tiers = if (length(t$tiers)) paste(t$tiers, collapse = ", ") else "",
           note = note, unit = if (!identical(t$table, "sector_year_tier")) t$unit else "sector x year x tier",
           n_champions = NA, n_member_cycles = NA, boards = "",
           cluster_by = if (!identical(t$table, "dem_share")) (if (t$table %in% c("industry_year", SGS_SHIFT_TABLES, SGS_SEATS_TABLES)) "Mentat industry" else "study sector") else "",
           n_clusters = if (!is.null(att)) length(att$sectors) else NA, gate_rule = t$window_rule,
           inference = if (identical(t$inference, "none") || descriptive) "none (DESCRIPTIVE)" else
             if (t$table %in% SGS_SHIFT_TABLES) "wild cluster restricted bootstrap by Mentat industry" else "wild cluster restricted bootstrap by sector",
           flag = tflag, input_flags = iflags, extra_line = extra_line, extra_lines = extra_lines, summary_note = summary_note))
    if (d$status != SGS_ESTIMABLE) next
    wtxt <- paste0(sgs_int_str(d$window[1]), "-", sgs_int_str(d$window[2]))
    common <- list(label = label, window_used = wtxt, unit_of_analysis = est_rows[[length(est_rows)]]$unit, dv_column = t$dv,
                   resid_df = att$resid_df, sectors = paste(att$sectors, collapse = ", "), controls = paste(t$controls, collapse = ", "),
                   fixed_effects = paste(t$fe, collapse = ", "), n = af$n, n_sectors = af$n_sectors, n_years = af$n_years, years = af$years)
    cflag <- paste(Filter(nzchar, c(tflag, if (nzchar(iflags)) paste0("input flags: ", iflags) else "")), collapse = "; ")
    coefs <- r$coefs
    if (identical(t$variant, "derived")) {
      coefs <- Filter(function(c) c$coefficient %in% t$focal, r$coefs)
      coefs <- coefs[order(match(vapply(coefs, function(c) c$coefficient, ""), t$focal))]
    }
    merge_row <- function(base, over) { for (nm in names(over)) base[nm] <- list(over[[nm]]); base }
    for (c in coefs) {
      if (!identical(t$variant, "derived") && !isTRUE(c$focal)) next
      row <- merge_row(common, c)
      row <- merge_row(row, list(test_id = t$id, source_test = if (src != t$id) src else "", flag = cflag,
                                 ci_text = if (identical(t$inference, "none") || descriptive) "n/a (inference not available)"
                                           else if (identical(c$test, "joint")) "n/a (joint test)"
                                           else sgs_ci_text(c$ci_low, c$ci_high)))
      coef_rows[[length(coef_rows) + 1L]] <- row
    }
    for (c in r$subfits) {
      row <- merge_row(common, c)
      row <- merge_row(row, list(test_id = t$id, source_test = "", n = c$n, n_sectors = c$n_sectors, n_years = c$n_years,
                                 years = c$years, subfit_status = c$status, subfit_reason = c$reason, subfit_flag = c$flag,
                                 ci_text = sgs_ci_text(c$ci_low %||% NA, c$ci_high %||% NA)))
      coef_rows[[length(coef_rows) + 1L]] <- row
    }
    if (!identical(t$variant, "derived")) {
      strata_rows <- c(strata_rows, lapply(r$strata, function(s) c(s, list(test_id = t$id))))
      sdf <- att$sample$df
      sample_parts[[length(sample_parts) + 1L]] <- data.frame(
        test_id = rep(t$id, nrow(sdf)), window_used = rep(wtxt, nrow(sdf)), study_sector = sdf$study_sector,
        year = as.numeric(sdf$year), tier = if ("tier" %in% names(sdf)) sdf$tier else NA_character_, y = sdf$y,
        board = NA_character_, bioguide = NA_character_, cycle = NA_real_,
        chamber = if ("chamber" %in% names(sdf)) sdf$chamber else NA_character_, stringsAsFactors = FALSE)
    }
  }
  sample_parts <- lapply(sample_parts, function(p) { if (!"chamber" %in% names(p)) p$chamber <- NA_character_; p })  # H5 rows
  sample_df <- if (length(sample_parts)) do.call(rbind, sample_parts) else
    data.frame(test_id = character(0), window_used = character(0), study_sector = character(0), year = numeric(0),
               tier = character(0), y = numeric(0), board = character(0), bioguide = character(0), cycle = numeric(0),
               chamber = character(0))
  term_diag <- NULL; holm <- NULL
  if (isTRUE(rules$inference_diag)) {
    # coordinator's revision of 2026-09-26 (Codex methodology review): incremental fit, the two-way (sector + year)
    # sensitivity, temporal support and the DESCRIPTIVE term labels of every focal term, and Holm-adjusted p within the
    # pre-specified families; nothing here changes an estimate or a p-value
    term_diag <- sgs_term_diag_table(order_, decisions, results)
    for (i in seq_along(coef_rows)) {
      cr <- coef_rows[[i]]
      if (!is.null(cr$left_out)) next
      dg <- term_diag[[paste(cr$test_id, cr$coefficient, sep = "\r")]]
      if (is.null(dg)) next
      for (nm in setdiff(names(dg), c("test_id", "coefficient"))) coef_rows[[i]][nm] <- list(dg[[nm]])
    }
    holm <- sgs_holm_table(est_rows, coef_rows)
    for (i in seq_len(nrow(holm))) {
      if (!nzchar(holm$test_id[i]) || !is.finite(holm$holm_p[i])) next
      for (j in seq_along(coef_rows)) {
        cr <- coef_rows[[j]]
        if (identical(cr$test_id, holm$test_id[i]) && identical(cr$coefficient, holm$coefficient[i]) && is.null(cr$left_out)) {
          coef_rows[[j]]$holm_family <- holm$family[i]
          coef_rows[[j]]$holm_p <- holm$holm_p[i]
        }
      }
    }
    emit("diagnostics", paste0("inference diagnostics for ", length(term_diag), " focal terms; Holm over ",
                               length(unique(holm$family)), " families"))
  }

  engine <- paste0("R ", as.character(getRversion()))
  sources <- lapply(wbs, function(w) list(
    file = w$file, workbook = w$name, absolute_path = w$path, sha256 = w$sha256, size_bytes = w$size_bytes,
    mtime_utc = w$mtime_utc, read_at_utc = w$read_at_utc, sheets_read = paste(names(w$frames), collapse = ", "),
    rows_read = paste0(names(w$frames), "=", vapply(w$frames, nrow, 0), collapse = ", "), note = "", engine = engine))
  names(sources) <- NULL
  if (!is.null(champ) && !is.null(champ$source)) sources[[length(sources) + 1L]] <- c(champ$source, list(engine = engine))
  if (!is.null(seats)) for (s in seats$source) sources[[length(sources) + 1L]] <- c(s, list(engine = engine))
  tables_out <- tables
  if (!is.null(champ)) tables_out$champions <- sgs_champion_panel_table(champ)
  windows <- list(default = window, fallback = fallback)
  xlsx <- file.path(results_dir, paste0("results_", run_id, ".xlsx"))
  md <- file.path(results_dir, paste0("report_", run_id, ".md"))
  emd <- file.path(results_dir, paste0("estimability_", run_id, ".md"))
  rcp <- file.path(results_dir, paste0("receipt_", run_id, ".json"))
  smry <- file.path(results_dir, paste0("summaries_", run_id, ".txt"))
  for (p in c(xlsx, md, emd, rcp, smry)) if (file.exists(p)) stop("refusing to overwrite an existing result file: ", p, call. = FALSE)
  # summary(lm()) of every ESTIMABLE test with the study's inference under it (Paul, 2026-09-26)
  summary_checks <- sgs_write_summaries(smry, run_id, order_, decisions, results, est_rows, paste0("R ", as.character(getRversion())), rules,
                                        term_diag = term_diag)
  emit("summaries", paste0("wrote ", basename(smry), " (", length(unique(summary_checks$test_id)), " tests)"))
  command <- command %||% sgs_rerun_command()
  # TRENDS (sign and size first) and the FORECAST backtest (rulings of 2026-09-26)
  trends <- NULL; fc <- NULL
  if (isTRUE(rules$trends)) {
    trends <- sgs_trends_table(order_, est_rows, coef_rows, strata_rows, results, registry)
    emit("trends", paste0("trends: ", sum(trends$scope == "pooled"), " pooled and ", sum(trends$scope != "pooled"),
                          " per-sector rows"))
  }
  if (isTRUE(rules$forecast)) {
    fc <- sgs_forecast_run(tables, built, strict = isTRUE(rules$chronology))
    emit("forecast", paste0("forecast backtest: LobbyView ", fc$runs$lv$status, ", contributions ", fc$runs$c$status,
                            " (", nrow(fc$rows), " forecasts)"))
  }
  # FIT (coordinator's ruling of 2026-09-26, after Paul's "look at the adjusted r-squared"): every summary block's adjusted
  # R^2 next to the previous R run's, with the reason for any difference
  fit <- NULL
  if (isTRUE(rules$fit)) {
    fit <- sgs_fit_table(smry, run_id, results_dir, sources = sources, est_rows = est_rows, fits = attr(summary_checks, "fits"))
    fi <- attr(fit, "info")
    emit("fit", paste0("fit table: ", fi$blocks, " blocks against ", if (is.na(fi$previous_run)) "no previous R run" else fi$previous_run,
                       " (adjusted R^2 lower in ", fi$lower, ", higher in ", fi$higher, ", same in ", fi$same, "; new ",
                       fi$new_tests + fi$newly_estimable, ")"))
  }
  extra_sheets <- list()
  extra_sections <- character(0)
  if (paul) {
    new_sections <- character(0)
    if (!is.null(shift)) {
      extra_sheets$shift_year <- shift$shift_year
      extra_sheets$shift_chamber <- shift$shift_chamber
      new_sections <- c(new_sections, "## SHIFT: partisan allocation of contributions on expected control (Paul's hypothesis)", "",
                        sgs_shift_md(order_, est_rows, coef_rows, results, shift), "")
    }
    if (!is.null(seats)) {
      for (tn in SGS_SEATS_TABLES) extra_sheets[[tn]] <- seats$tables[[tn]]
      extra_sheets$seats_coverage <- seats$coverage
      extra_sheets$seats_calls <- seats$calls
      extra_sheets$seats_cells <- sgs_seats_cells(seats, est_rows)
      if (!is.null(seats$w)) {
        extra_sheets$seats_w_estimates <- seats$w$estimates
        extra_sheets$seats_w_support <- seats$w$support
        if (!is.null(seats$w$series) && nrow(seats$w$series)) {
          extra_sheets$seats_w_series <- .seats_text_dates(seats$w$series)
          tryCatch(sgs_seats_w_plot(seats$w$series, file.path(results_dir, paste0("seats_w_series_", run_id, ".png"))), error = function(e) NULL)
        }
      }
      extra_sheets <- c(extra_sheets, sgs_seats_race_sheets(seats$race))
      new_sections <- c(new_sections, "## SEATS: partisanship of the spending and the expected seat gain (Paul's follow-up)", "",
                        sgs_seats_md(order_, est_rows, coef_rows, results, seats), "")
    }
    if (!is.null(trends)) {
      extra_sheets$trends <- trends
      new_sections <- c(new_sections, "## Trends: sign and size first, then p and CI (Paul: \"Doesn't matter if it is significant if the trend is there\")", "",
                        sgs_trends_md(trends), "")
    }
    if (!is.null(fit)) {
      extra_sheets$fit <- fit
      new_sections <- c(new_sections, "## Model fit: adjusted R^2 against the previous run (Paul: \"look at the adjusted r-squared\")", "",
                        sgs_fit_md(fit), "")
    }
    if (isTRUE(rules$lv_robustness) || isTRUE(rules$inference_diag)) {
      codex <- sgs_codex_check(est_rows, coef_rows, holm)
      extra_sheets$codex_review_check <- codex
      new_sections <- c(new_sections, "## Codex methodology review: reproduction of its numbers", "", sgs_codex_check_md(codex), "")
    }
    if (isTRUE(rules$lv_robustness)) {
      new_sections <- c(new_sections, "## L1-LV..L3-LV robustness (year FE, log, LOSO, LOYO, FD; FDY exploratory)", "",
                        sgs_lv_robustness_md(est_rows, coef_rows), "")
    }
    if (isTRUE(rules$inference_diag)) {
      extra_sheets$multiplicity <- holm
      new_sections <- c(new_sections,
                        "## Incremental fit: adjusted R^2 with and without each focal term (same rows)", "", sgs_incremental_md(coef_rows), "",
                        "## Multiplicity: Holm-adjusted p within pre-specified families", "", sgs_holm_md(holm), "",
                        "## Inference sensitivity: common-year shocks, temporal support, DESCRIPTIVE terms", "", sgs_sensitivity_md(coef_rows), "")
    }
    if (isTRUE(rules$chronology)) {
      timing <- sgs_expected_control_timing(tables$sector_year)
      extra_sheets$expected_control_timing <- timing
      new_sections <- c(new_sections, "## Chronology: when each expected-control value was measured", "",
                        sgs_chronology_md(timing, est_rows), "",
                        "## What the money measures (04 included receipts)", "", sgs_money_md(wbs), "")
    }
    if (!is.null(fc)) {
      extra_sheets$forecast_backtest <- fc$rows
      extra_sheets$forecast_metrics <- fc$metrics
      extra_sheets$forecast_origins <- fc$origins
      if (isTRUE(fc$strict)) extra_sheets$forecast_asof <- fc$asof
      new_sections <- c(new_sections, "## Forecast backtest (the Mentat Insights upgrade test)", "", sgs_forecast_md(fc))
    }
    pac <- sgs_pac_overlap(wbs)
    extra_sheets$pac_overlap <- pac
    reg <- built$multiyear$register
    if (!is.null(reg) && nrow(reg)) extra_sheets$multiyear_register <- reg
    pooled <- attr(pac, "pooled")
    st_pac <- pac[pac$is_study_sector & pac$year >= 2021 & pac$year <= 2025, , drop = FALSE]
    lv_lines <- character(0)
    lvsh <- wbs$lobbying$frames[[SGS$LOBBYVIEW_ALL_SHEET]]
    if (!is.null(lvsh)) {
      lv_lines <- c("", "## LobbyView: stated limitations and de-duplication", "", paste0("- ", SGS$LOBBYVIEW_LIMITATIONS))
      if ("dedup_ratio" %in% names(lvsh)) {
        thin <- grepl("thin", as.character(lvsh$coverage_flag %||% rep(NA, nrow(lvsh))), fixed = TRUE)
        k <- !(lvsh$confidence %in% "low") & lvsh$study_sector %in% SGS$STUDY_SECTORS & !is.na(lvsh$dedup_ratio) &
          lvsh$status %in% SGS_USABLE_STATUSES & !thin & lvsh$year >= SGS$PANEL_FIRST_YEAR
        med <- tapply(lvsh$dedup_ratio[k], lvsh$study_sector[k], stats::median)
        yrs <- tapply(lvsh$year[k], lvsh$study_sector[k], function(v) sgs_years_text(v))
        med <- med[order(sgs_sector_rank(names(med)))]
        all_lv <- unique(lvsh$study_sector[!(lvsh$confidence %in% "low") & lvsh$study_sector %in% SGS$STUDY_SECTORS])
        none <- setdiff(all_lv, names(med))
        lv_lines <- c(lv_lines, paste0("- dedup_ratio (de-duplicated / undifferentiated amount), median over the primary ",
                                       "LobbyView sector-years (usable, not thin, ", SGS$PANEL_FIRST_YEAR, " on) of 01 ",
                                       SGS$LOBBYVIEW_ALL_SHEET, ": ",
                                       paste0(names(med), " ", vapply(med, sgs_py_fixed, "", d = 3), " (", yrs[names(med)], ")",
                                              collapse = "; "),
                                       if (length(none)) paste0("; no primary sector-year (all thin): ", paste(none, collapse = ", ")) else "",
                                       "."))
      }
    }
    cov_lines <- character(0); tel_lines <- character(0)
    if (isTRUE(rules$extensions_0926)) {
      cov <- sgs_coverage_table(order_, decisions, est_rows, tables, wbs$crosswalk$frames$data)
      extra_sheets$coverage <- cov
      if (!is.null(tables$sector_year_banks)) extra_sheets$sector_year_banks <- tables$sector_year_banks
      cov_lines <- c("", "## Coverage: every study sector and Mentat book x test family", "", sgs_coverage_md(cov))
      for (t in order_) {
        if (identical(t$variant, "derived") || identical(t$table, "champions")) next
        if (!any(sgs_is_growth_var(sgs_required_vars(t)))) next
        d <- decisions[[t$id]]
        att <- sgs_decision_chosen(d) %||% (if (length(d$attempts)) d$attempts[[length(d$attempts)]] else NULL)
        sdf <- att$sample$df
        if (is.null(sdf) || !nrow(sdf) || !any(sdf$study_sector == "telecom")) next
        k <- sdf$study_sector == "telecom"
        tel_lines <- c(tel_lines, paste0("- ", t$id, " (", d$status, "): telecom ", sum(k), " of n = ", nrow(sdf), " rows (",
                                         sgs_years_text(sdf$year[k]), "), ", length(unique(sdf$study_sector)), " sectors in the ",
                                         if (identical(d$status, SGS_ESTIMABLE)) "estimated" else "last attempted", " sample"))
      }
      tel_lines <- c("", "## Telecom in the growth tests (Paul's ask of 2026-09-26; the plan kept the components separate)", "",
                     paste0("- ", built$telecom_combined$note %||% "telecom combination not built"),
                     if (length(tel_lines)) tel_lines else "- telecom enters no growth test sample")
    }
    extra_sections <- c(
      new_sections,
      "## Paul's rulings in this run (rule set paul-2026-09-25)", "",
      paste0("- ", vapply(names(built), function(b) paste0(b, ": ", if (isTRUE(built[[b]]$built)) "BUILT" else "NOT BUILT", " - ",
                                                            built[[b]]$note %||% ""), "")),
      lv_lines,
      "", "## PAC double-count check (04 gifts to the roster company's own PAC)", "",
      paste0("- 2021-2025 nominal: ", sgs_py_fixed(100 * pooled$all_units, 2), "% of general giving across every 04 unit (the audit's ",
             "8.84%), ", sgs_py_fixed(100 * pooled$study_sectors, 2), "% across the study sectors; per sector-year in sheet pac_overlap."),
      paste0("- Study-sector sector-years 2021-2025: share of general giving to the own company PAC ranges ",
             sgs_py_fixed(100 * min(st_pac$company_pac_share_nominal, na.rm = TRUE), 2), "%-",
             sgs_py_fixed(100 * max(st_pac$company_pac_share_nominal, na.rm = TRUE), 2), "% (n = ", nrow(st_pac), ")."),
      "- R-dedup-C1..C3 rerun C1-C3 on general giving without those gifts.",
      cov_lines, tel_lines,
      "", "## Model summaries", "",
      paste0("- summary(lm(...)) of every ESTIMABLE test, as R prints it, with the study's inference on the focal term(s) ",
             "under each (CR1 SE, wild cluster restricted bootstrap p and 95% interval, draws, clusters, strata): ",
             basename(smry), ". The lm() focal coefficient equals the pipeline estimate in every block (",
             nrow(summary_checks), " focal terms; largest relative difference ",
             if (nrow(summary_checks)) formatC(max(summary_checks$rel_diff, na.rm = TRUE), format = "e", digits = 2) else "n/a", ")."),
      "", "## Rerun", "",
      "After new inputs land (e.g. the 2020 contributions of the Mentat 2020 run linked into 04), rerun the whole study with one command (a new run id; nothing is overwritten):",
      "", "```powershell", command, "```")
  }
  paul_notes <- if (paul) sgs_paul_build_notes() else SGS_PY_BUILD_NOTES
  sheets <- sgs_write_results_workbook(xlsx, est_rows, coef_rows, strata_rows, sample_df, tables_out, sources,
                                       extra_sheets = if (paul) c(extra_sheets, list(run = data.frame(
                                         key = c("run_id", "engine", "ruleset", "default_window", "fallback_search", "seed", "B",
                                                 "data_dir", "receipt_05", "rerun_command"),
                                         value = c(run_id, engine, rules$name, paste(window, collapse = "-"),
                                                   if (is.null(fallback)) "none" else paste(fallback, collapse = "-"), sgs_int_str(seed),
                                                   sgs_int_str(B), normalizePath(data_dir, winslash = "\\", mustWork = FALSE),
                                                   if (!is.null(champ)) normalizePath(champ$receipt_path, winslash = "\\", mustWork = FALSE) else "",
                                                   command), stringsAsFactors = FALSE))) else list(),
                                       paul = paul)
  specs <- order_
  sgs_write_report_md(md, run_id, est_rows, coef_rows, strata_rows, specs, sources, windows, list(B = B, seed = seed),
                      paul_notes, extra_sections = extra_sections,
                      engine_line = if (paul) paste0("- Engine: ", engine, " (code/R, rule set ", rules$name, "); rerun: ", command) else NULL)
  sgs_write_estimability_md(emd, run_id, est_rows, attempts_by_test, windows)
  st <- vapply(est_rows, function(r) r$status, "")
  counts <- c(ESTIMABLE = sum(st == SGS_ESTIMABLE), `NOT ESTIMABLE` = sum(st == SGS_NOT_ESTIMABLE), `NOT BUILT` = sum(st == SGS_NOT_BUILT))
  finished <- Sys.time()
  outputs <- lapply(c(xlsx, md, emd, smry), function(p) list(file = basename(p), path = normalizePath(p, winslash = "\\"),
                                                       sha256 = sgs_sha256_file(p), size_bytes = as.numeric(file.info(p)$size)))
  receipt <- list(run_id = run_id, engine = engine, engine_code = "code/R (sgs R port)", engine_code_files = sgs_engine_code_hashes(),
                  ruleset = rules$name,
                  started_utc = sgs_utc_iso(started), finished_utc = sgs_utc_iso(finished),
                  duration_s = round(as.numeric(difftime(finished, started, units = "secs")), 1),
                  command = command, parameters = list(default_window = window, fallback_search = fallback, seed = seed, B = B,
                                                       include_partial = include_partial, only = only %||% "all"),
                  counts = as.list(counts), tests = length(est_rows),
                  inputs = lapply(sources, function(s) s[c("file", "workbook", "absolute_path", "sha256", "size_bytes", "mtime_utc",
                                                           "read_at_utc", "sheets_read", "rows_read", "note")]),
                  built = lapply(built, function(b) list(built = isTRUE(b$built), note = b$note %||% "")),
                  outputs = outputs)
  if (!is.null(shift)) {
    sh_rows <- Filter(function(r) r$family %in% c("SHIFT", "SHIFT-PV"), est_rows)
    sst <- vapply(sh_rows, `[[`, "", "status")
    sh_est <- vapply(sh_rows[sst == SGS_ESTIMABLE], `[[`, "", "test_id")
    # the minimum-base cells each ESTIMABLE exploratory variant left out, and the saturated (DESCRIPTIVE) tests
    mb_est <- sh_est[vapply(sh_est, function(i) !is.null(sgs_decision_chosen(decisions[[i]])$sample$min_base), TRUE)]
    mb_cells <- lapply(mb_est, function(i) {
      mbr <- sgs_decision_chosen(decisions[[i]])$sample$min_base
      list(threshold = mbr$threshold, cells = nrow(mbr$cells),
           left_out = if (!nrow(mbr$cells)) I(character(0)) else I(strsplit(.shift_min_base_cells_text(mbr$cells), "; ", fixed = TRUE)[[1]]))
    })
    names(mb_cells) <- mb_est
    receipt$shift <- list(tests = length(sh_rows), estimable = sum(sst == SGS_ESTIMABLE), not_estimable = sum(sst == SGS_NOT_ESTIMABLE),
                          not_built = sum(sst == SGS_NOT_BUILT), units = shift$units, estimable_tests = I(sh_est),
                          descriptive_saturated = I(sh_est[vapply(sh_est, function(i) isTRUE(results[[i]]$identification$saturated), TRUE)]),
                          min_base_exploratory = list(flag = SGS$POST_RESULT_FLAG,
                                                      thresholds_usd = as.list(SGS$SHIFT_MIN_BASE_EXPLORATORY), by_test = mb_cells),
                          sheets = c("shift_year", "shift_chamber"))
  }
  if (!is.null(seats)) {
    se_rows <- Filter(function(r) identical(r$family, "SEATS-A"), est_rows)
    sest <- vapply(se_rows, `[[`, "", "status")
    cells <- sgs_seats_cells(seats, est_rows)
    png <- file.path(results_dir, paste0("seats_w_series_", run_id, ".png"))
    receipt$seats <- list(
      question = SGS_SEATS_QUESTION,
      seats_a = list(tests = length(se_rows), estimable = sum(sest == SGS_ESTIMABLE), not_estimable = sum(sest == SGS_NOT_ESTIMABLE),
                     not_built = sum(sest == SGS_NOT_BUILT), label = "DESCRIPTIVE", window = SGS$SEATS_WINDOW),
      weekly = list(built = isTRUE(seats$weekly_ok), reason = seats$weekly_reason,
                    estimates = if (!is.null(seats$w)) nrow(seats$w$estimates) else 0L,
                    plot = if (file.exists(png)) list(file = basename(png), sha256 = sgs_sha256_file(png)) else NULL),
      race = list(built = isTRUE(seats$race$ok), reason = seats$race$reason %||% "", recipients_10 = isTRUE(seats$race$have10),
                  forecasts_11 = isTRUE(seats$race$have11),
                  chambers = lapply(seats$race$chambers, function(z) list(built = isTRUE(z$ok), reason = z$reason %||% "",
                                                                        estimand_b = isTRUE(z$b$ok), estimand_c = isTRUE(z$c$ok))),
                  money = list(built = isTRUE(seats$race$money$ok), reason = seats$race$money$reason %||% "")),
      cells = as.list(table(factor(cells$status, levels = c("estimated", "descriptive only", "unavailable")))),
      inference = list(primary = "no lagged outcome (levels, changes); fixed-X residual moving-block bootstrap within cycle, conditional",
                       blocks_weeks = SGS_SEATS_BLOCKS, draws = SGS_SEATS_BOOT_B, hac_lags_secondary = SGS_SEATS_HAC_LAGS,
                       lagged_outcome = "sensitivity: fixed-X conditional and recursive (dynamic) block bootstrap",
                       min_weeks = SGS$SEATS_MIN_WEEKS),
      sheets = I(intersect(c(SGS_SEATS_TABLES, "seats_coverage", "seats_calls", "seats_cells", "seats_w_estimates", "seats_w_support",
                             "seats_w_series", names(sgs_seats_race_sheets(seats$race))), c(SGS_SEATS_TABLES, names(extra_sheets)))))
  }
  if (isTRUE(rules$lv_robustness) || isTRUE(rules$inference_diag)) {
    ck <- sgs_codex_check(est_rows, coef_rows, holm)
    receipt$codex_review <- list(source = "C:/Users/pgoff/Documents/Codex/2026-09-26/loo/outputs (run analysis-R-20260926T070630Z)",
                                 checks = nrow(ck), match = sum(ck$verdict == "MATCH"), mismatch = sum(ck$verdict == "MISMATCH"),
                                 not_computed = sum(ck$verdict == "NOT COMPUTED"), sheet = "codex_review_check")
  }
  if (!is.null(holm)) {
    receipt$multiplicity <- list(sheet = "multiplicity", families = I(unique(holm$family)),
                                 adjusted_terms = sum(is.finite(holm$holm_p)))
  }
  if (isTRUE(rules$chronology)) {
    tm <- sgs_expected_control_timing(tables$sector_year)
    receipt$chronology <- list(sheet = "expected_control_timing", retro_label = SGS$RETRO_LABEL,
                               measured_after_year = I(paste0(tm$chamber[tm$after_year %in% TRUE], " ", tm$year[tm$after_year %in% TRUE],
                                                              " (measured ", tm$measured_at[tm$after_year %in% TRUE], ")")),
                               strict_tests = I(vapply(Filter(function(r) grepl("STRICT", r$test_id, fixed = TRUE), est_rows),
                                                       function(r) paste0(r$test_id, ": ", r$status), "")),
                               forecast_origin = paste0("1 February of the target year (", SGS$FORECAST_ORIGIN_MMDD, ")"))
  }
  if (!is.null(fit)) {
    fi <- attr(fit, "info")
    receipt$fit <- list(sheet = "fit", previous_run = fi$previous_run, blocks = fi$blocks, previous_blocks = fi$previous_blocks,
                        unchanged = fi$unchanged, lower = fi$lower, higher = fi$higher, same = fi$same, new_tests = fi$new_tests,
                        newly_estimable = fi$newly_estimable, not_in_this_run = fi$not_in_this_run,
                        like_for_like_lower = I(fi$like_for_like_lower), inputs_changed = I(fi$inputs_changed %||% character(0)))
  }
  if (!is.null(trends)) {
    receipt$trends <- list(pooled_rows = sum(trends$scope == "pooled"), per_sector_rows = sum(trends$scope != "pooled"),
                           sheet = "trends")
  }
  if (!is.null(fc)) {
    receipt$forecast <- list(sheets = c("forecast_backtest", "forecast_metrics", "forecast_origins", if (isTRUE(fc$strict)) "forecast_asof"),
                             timings = I(if (isTRUE(fc$strict)) c("retrospective", "strict") else "retrospective"),
                             runs = lapply(fc$runs, function(r) list(status = r$status, note = r$note)))
  }
  writeLines(enc2utf8(as.character(jsonlite::toJSON(receipt, auto_unbox = TRUE, pretty = TRUE, null = "null", na = "null", digits = NA))),
             rcp, useBytes = TRUE)
  list(run_id = run_id, counts = counts, xlsx = xlsx, report = md, estimability = emd, receipt = rcp, summaries = smry,
       summary_checks = summary_checks, est_rows = est_rows,
       coef_rows = coef_rows, strata_rows = strata_rows, sample_df = sample_df, tables = tables_out, decisions = decisions,
       results = results, attempts_by_test = attempts_by_test, champions = champ, sources = sources, built = built,
       registry = order_, sheets = sheets, shift = shift, trends = trends, forecast = fc, fit = fit, term_diag = term_diag,
       holm = holm, seats = seats)
}
