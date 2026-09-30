# Write the run outputs: results_<run>.xlsx (study format), report_<run>.md, estimability_<run>.md
# (R port of code/sgs/report.py), plus receipt_<run>.json (engine R, inputs and outputs with SHA-256).
#
# Workbook format: header in row 1, one table per sheet, values only (no formulas, styles, merged cells); missing is
# an empty cell, never 0; unbounded interval ends are blank numbers with the interval spelled out in ci_text.
# Every figure in the markdown names its window (or cycles) and its denominator (house rule).

sgs_label_text <- function(label) if (identical(label, "PREVIEW")) SGS$PREVIEW_FLAG else label

.md_escape <- function(s) gsub("\n", " ", gsub("|", "/", as.character(s), fixed = TRUE), fixed = TRUE)
.nz <- function(x) !is.null(x) && length(x) && !is.na(x) && !identical(x, "") && !identical(x, FALSE)
.g <- function(r, k) { v <- r[[k, exact = TRUE]]; if (is.null(v) || !length(v)) NA else v }

SGS_RESULT_DICTIONARY <- list(
  c("estimability", "test_id", "text", NA, "Registry id (registry.py)."),
  c("estimability", "family", "text", NA, "C, L, L-LV, H1, H4, H5, E1, T, core_reduced, robustness, DS."),
  c("estimability", "label", "text", NA, "CORE / EXTENSION / ROBUSTNESS / EXPLORATORY / DESCRIPTIVE (no inference) / PREVIEW (fixed window 2021-2025, below the 6-year minimum; printed 'PREVIEW - below the 6-year minimum')."),
  c("estimability", "status", "text", NA, "ESTIMABLE (window used) / NOT ESTIMABLE (reason) / NOT BUILT."),
  c("estimability", "window_used", "text", "years", "Window of the estimated sample (sector-year tests) or its cycles (H5); blank unless ESTIMABLE."),
  c("estimability", "window_kind", "text", NA, "default (2020-2025, >= 6 years); fallback (most recent 10 consecutive complete-case years of the most recent run of >= 10 within 2008-2025, only when the default fails); preview (fixed 2021-2025, >= 5 years, PREVIEW tests only); member-cycle gate (H5)."),
  c("estimability", "fallback_search", "text", NA, "The fallback search: complete-case years in 2008-2025, the runs of consecutive years, the run and the window used."),
  c("estimability", "n", "integer", "rows", "Complete-case rows of the estimated sample, or of the last attempted window (H5: board x champion x cycle rows)."),
  c("estimability", "n_window", "text", "years", "Window in which n, n_sectors, n_years and years were counted (H5: cycles)."),
  c("estimability", "n_sectors", "integer", "sectors", "Distinct sectors in that sample (blank for H5)."),
  c("estimability", "sectors", "text", NA, "Sectors in that sample."),
  c("estimability", "n_years", "integer", "years", "Distinct years in that sample (H5: distinct cycles)."),
  c("estimability", "years", "text", NA, "Years in that sample (H5: cycles)."),
  c("estimability", "resid_df", "integer", "df", "n minus design rank."),
  c("estimability", "reason_short", "text", NA, "Compact reason per attempted window: years found vs required, terms not identified, residual df, inputs no sector has (with years), sectors never complete; H5: cycles, member-cycles, variance, availability by cycle."),
  c("estimability", "reason", "text", NA, "Why NOT ESTIMABLE / NOT BUILT: each attempted window with its failed checks and blocking inputs."),
  c("estimability", "default_attempt", "text", NA, "Outcome of the default-window attempt."),
  c("estimability", "fallback_attempt", "text", NA, "Outcome of the fallback attempt (blank when not needed)."),
  c("estimability", "exclusions", "text", NA, "Rows excluded, by reason (counts)."),
  c("estimability", "dv / dv_column / dv_label", "text", NA, "Registry DV (H5: the DV role) / the workbook column used / its label (H5 fallback DV: 'employee channel only')."),
  c("estimability", "focal / controls / fixed_effects / variant / base_test / year_filter / tiers / note", "text", NA, "The registry entry."),
  c("estimability", "unit", "text", NA, "Unit of analysis: sector x year, sector x year x tier, or board x champion x cycle (H5)."),
  c("estimability", "n_champions / n_member_cycles / boards", "mixed", NA, "H5: champions (bioguide), distinct champion x cycle pairs, boards in the sample."),
  c("estimability", "cluster_by / n_clusters", "mixed", NA, "Inference clusters (study sector; H5: champion) and their number in the sample."),
  c("estimability", "gate_rule", "text", NA, "The estimability rule applied to the test."),
  c("estimability", "inference", "text", NA, "Wild cluster restricted bootstrap (by sector or champion), or none (DESCRIPTIVE)."),
  c("estimability", "flag", "text", NA, "Flags printed with every coefficient (e.g. employee channel only; outcome-contaminated; PREVIEW - below the 6-year minimum)."),
  c("estimability", "input_flags", "text", NA, "Expected-control inputs of the sample that are not IEM annual means: variable, year, method (forecaster_final_call_binary, market_snapshot, market_daily_mean) and timing flag (e.g. measured Nov 2024, after the year)."),
  c("coefficients", "test_id", "text", NA, "Test the row belongs to (derived H1/H4 rows name their source test in source_test)."),
  c("coefficients", "coefficient", "text", NA, "Regressor name; X:Chief / X:Middle Management are slope differences from Employee."),
  c("coefficients", "focal", "boolean", NA, "True for the test's focal coefficient(s)."),
  c("coefficients", "estimate", "decimal", "see unit", "OLS point estimate."),
  c("coefficients", "unit", "text", NA, "Unit of the estimate (DV in $M 2025 for sector-year tests, USD 2025 for H5, unless transformed)."),
  c("coefficients", "hc1_se", "decimal", "see unit", "HC1 heteroskedasticity-robust standard error (reference only)."),
  c("coefficients", "cr1_se", "decimal", "see unit", "CR1 cluster-robust standard error (by sector; H5 by champion) used in the bootstrap t; blank for DESCRIPTIVE tests."),
  c("coefficients", "t_cr1", "decimal", NA, "t statistic estimate / cr1_se."),
  c("coefficients", "boot_p", "decimal", "probability", "Wild cluster restricted bootstrap p-value for coefficient = 0 (two-sided, symmetric); blank for DESCRIPTIVE tests."),
  c("coefficients", "ci_low / ci_high", "decimal", "see unit", "95% interval by bootstrap test inversion; blank where unbounded or not computed (see ci_text)."),
  c("coefficients", "ci_text", "text", NA, "The interval as text, including infinite ends, or 'n/a (inference not available)'."),
  c("coefficients", "boot_draws", "integer", "draws", "Bootstrap draws (6**G when enumerated); 0 when no bootstrap was run."),
  c("coefficients", "boot_enumerated", "boolean", NA, "True when all 6**G Webb weight vectors were enumerated."),
  c("coefficients", "boot_note", "text", NA, "Bootstrap caveat, or the DESCRIPTIVE note ('2 sectors: wild cluster bootstrap cannot reach p < 0.056; inference not available')."),
  c("coefficients", "inference / flag", "text", NA, "Inference used; flags (employee channel only; outcome-contaminated: money affects margins)."),
  c("coefficients", "stratification", "text", NA, "STRATIFIED (k of G sectors or boards have a stratum-only estimate; see strata) or UNSTRATIFIED (reason)."),
  c("coefficients", "left_out / subfit_status / subfit_reason / subfit_flag", "text", NA, "Leave-one-out sub-fits: the sector or year left out and the sub-fit outcome."),
  c("coefficients", "window_used / n / n_sectors / n_years / years / unit_of_analysis / n_champions / n_member_cycles / cycles / dv_column", "mixed", NA, "Window (or cycles) and denominator of the estimate."),
  c("coefficients", "resid_df / sectors / boards / controls / fixed_effects", "mixed", NA, "Residual df of the fitted design (n minus rank), the sectors (or H5 boards) in the sample, and the specification's controls and fixed effects."),
  c("strata", "test_id / coefficient / study_sector / board", "text", NA, "Stratum-only regression of the same specification: one sector (sector baseline = intercept), or one board (H5, board fixed effects dropped)."),
  c("strata", "status", "text", NA, "estimated, or insufficient (residual df < 2, rank deficient, or focal not identified)."),
  c("strata", "estimate / hc1_se / cr1_se", "decimal", "see coefficients.unit", "Stratum OLS estimate, HC1 error, CR1 error by champion (H5)."),
  c("strata", "n / resid_df / years / cycles / n_champions / reason", "mixed", NA, "Denominator of the stratum estimate, or why it is insufficient."),
  c("samples", "test_id / window_used / study_sector / year / tier / y / board / bioguide / cycle", "mixed", NA, "Rows of every estimated sample (y = the DV as entered: $M 2025, ln, first difference; H5: USD 2025, log1p or 0/1)."),
  c("sector_year", "(columns)", "mixed", NA, "Analysis table study_sector x year; columns defined in the rows below."),
  c("sector_year_tier", "(columns)", "mixed", NA, "Analysis table study_sector x year x tier; same column definitions."),
  c("industry_year", "(columns)", "mixed", NA, "H1-PV table: every Mentat industry of 04 sector_year (seven study sectors plus community_banks, not a study sector; column study_sector holds the 04 unit) x year: contributions and pres_year / midterm_year."),
  c("champions", "(columns)", "mixed", NA, "05 data columns H5 reads, every row of 05 as read at run time (empty when 05 is NOT BUILT); definitions in 05's dictionary."),
  c("sources", "file / workbook / absolute_path / sha256 / size_bytes / mtime_utc / read_at_utc / sheets_read / rows_read / note", "mixed", NA, "Every input workbook read by the run (read-only), with its SHA-256; note = how 05 was read, or why it is NOT BUILT.")
)

SGS_PAUL_DICTIONARY <- list(
  c("sources", "engine", "text", NA, "Engine of the run: R and its version (the Python package code/sgs is the frozen parity reference)."),
  c("pac_overlap", "(columns)", "mixed", NA, "PAC double-count check (Paul's ruling 4): per 04 unit x year, general giving, the part given to the roster company's own PAC (04 recipient_category 'Company PAC', Mentat report.R company-alias + PAC match) and its share; nominal and real 2025 dollars."),
  c("multiyear_register", "(columns)", "mixed", NA, "Compliant (i): every 06 supplemental_observations / component_forecasts record, whether it is a crypto or fintech multi-year CAGR, its availability date, the spending year it serves (the year after publication) and whether the vintage rule uses it."),
  c("run", "key / value", "text", NA, "Run parameters: run id, engine, rule set, windows, seed, B, input folder, receipt of 05, rerun command."),
  c("coverage", "unit / mentat_book / family / status / reason / tests", "text", NA, "Rulings of 2026-09-26: every study sector and Mentat book x test family (ROBUSTNESS variants not counted): IN (in the sample of an ESTIMABLE test), IN* (in the complete-case sample, no test of the family ESTIMABLE yet), OUT or NOT BUILT with the reason, and the tests it rests on."),
  c("sector_year_banks", "(columns)", "mixed", NA, "Bank split (rulings of 2026-09-26): sector_year with commercial_banks (Mentat banking) renamed big_banks and a community_banks unit (04 community_banks contributions; 01 LobbyView rows when present); both banks carry the commercial-banking growth series (IBISWorld 52211) and the national controls."),
  c("samples", "chamber", "text", NA, "SHIFT-Chamber samples (rulings of 2026-09-26): the recipient chamber of the row (House / Senate); blank elsewhere."),
  c("shift_year", "(columns)", "mixed", NA, "SHIFT (rulings of 2026-09-26): one row per Mentat industry of 04 / 08 (the seven study sectors with a book plus community_banks) x year: the Democratic shares of House / Senate candidate-committee giving (08), with the Hill committees (08 sector_year_chamber_with_hill), and of all party-labelled 04 giving, with their dollar bases, the unit-year's general giving and the year-level terms; column definitions in the rows below."),
  c("shift_chamber", "(columns)", "mixed", NA, "SHIFT-Chamber: shift_year's House and Senate rows stacked (unit x year x chamber) with the expected and current Democratic control of the recipient's own chamber; column definitions in the rows below."),
  c("trends", "test_id / family / label / trend_group / coefficient / scope / window / n", "mixed", NA, "TRENDS (rulings of 2026-09-26): one row per focal term of every ESTIMABLE test, pooled (scope 'pooled') and per sector (scope = the sector, or 'board x' for H5: the stratum's own regression); trend_group = the test whose variants are compared (SHIFT: the main test; ROBUSTNESS / PREVIEW tests: the root of their base chain; H5: H5)."),
  c("trends", "sign / size / plain_value / plain_unit", "mixed", NA, "The sign (+ / - / 0) and the size in plain units: $M 2025, share points (0-1 shares x 100), USD 2025 per toughness point, percentage points of a probability (x 100), log points."),
  c("trends", "predicted_sign / matches_prediction", "text", NA, "The sign the stated hypothesis predicts (SHIFT expected control +, CONTRACT +, ASYM-SLOPES decline-year slopes -) and whether the estimate has it."),
  c("trends", "same_sign_across_variants / variants / n_variants", "mixed", NA, "Whether every ESTIMABLE test of the trend group gives the term (same name, telecom component suffix dropped; same scope) the same sign: yes / no / single test; the tests by sign."),
  c("trends", "sectors_plus_minus / identification", "text", NA, "Pooled rows: the signs of the per-sector estimates; SHIFT: how the year-level focal term is identified (SATURATED = no year-level residual df, the estimate a fixed contrast of the years named)."),
  c("trends", "estimate / unit / se / se_kind / boot_p / ci_low / ci_high / ci_text / boot_draws / flag", "mixed", NA, "As in coefficients (pooled: CR1 SE, bootstrap p and CI; per sector: the stratum's HC1 SE, no inference)."),
  c("forecast_backtest", "(columns)", "mixed", NA, "FORECAST backtest (rulings of 2026-09-26): one row per target sector-year x model: actual ($M 2025), last year's value (the anchor), the forecast, error = forecast - actual, beats_naive (|error| < the naive |error|), in_common_set (every model forecasts the sector-year; a DESCRIPTIVE forecast does not count), status / reason (why no forecast, or why the forecast is DESCRIPTIVE), the training rows, years and sectors of the model at that origin."),
  c("forecast_metrics", "(columns)", "mixed", NA, "Per backtest x set (common: sector-years every model forecasts; own: every sector-year the model forecasts; descriptive: the DESCRIPTIVE forecasts, kept out of the other two) x scope (pooled, sector, target year) x model: n, MAE, RMSE ($M 2025), the naive MAE on the same rows, MAE / naive MAE, the number and share of sector-years beating naive."),
  c("forecast_origins", "(columns)", "mixed", NA, "Per backtest x target year x change model (1)-(4): whether the training design passes the study's estimability gate (ok: identified, residual df >= 3 and year-level residual df >= 3), why not (reason), training rows and years; descriptive, dropped_terms, year_level_params, year_level_df and resid_df, below."),
  # owner-approved changes of 2026-09-30 (the model split, the DESCRIPTIVE forecasts, the scale-free metrics)
  c("forecast_backtest / forecast_metrics / forecast_origins", "model / model_label / prior_model_id", "text", NA, "Model ids: (0), (0s), (1), (2a), (2b), (3), (4). (2a) is new (2026-09-30): sector baseline + pres/midterm + predicted growth only, the strict-feasible growth model. (2b) is the earlier model (2), term for term (2a + prior-year growth). prior_model_id = the id a run before 2026-09-30 used for the row's model (\"2\" for (2b), blank for (2a)); (0), (0s), (1), (3), (4) keep their ids and specifications."),
  c("forecast_backtest", "descriptive", "text", NA, "TRUE = a DESCRIPTIVE forecast: the model's training design failed the study's estimability gate at this origin (not identified, or residual df < 3, or year-level residual df < 3); R8's wider training window cannot be found for an expanding window that already holds every earlier usable year, so the forecast is kept (fitted without the terms that add no rank, if any; named in reason). Kept out of the common and own sets and reported in set 'descriptive' of forecast_metrics."),
  c("forecast_backtest", "naive_scale", "decimal", "$M 2025", "The MASE scale of the row: the in-sample naive MAE of the sector at the origin (the mean absolute one-step change of its outcomes reported before the target year; blank when it has none)."),
  c("forecast_metrics", "rel_mae_by_sector", "decimal", "ratio", "Sector-equal relative MAE: the mean over the sectors of (the sector's MAE / the sector's naive MAE on the same rows); a sector with a naive MAE of 0 is left out of the mean (its ratio is undefined); a sector scope has one sector, so it equals rel_mae there. Below 1 = better than last year's value."),
  c("forecast_metrics", "mase", "decimal", "ratio", "Mean absolute scaled error: the mean over the rows of |error| / naive_scale (the in-sample naive MAE of the row's sector at its origin). Below 1 = better than the in-sample naive forecast."),
  c("forecast_origins", "descriptive / dropped_terms / year_level_params / year_level_df / resid_df", "mixed", NA, "descriptive: the design failed the gate and its forecast is kept as DESCRIPTIVE; dropped_terms: the terms that add no rank (coefficient 0); year_level_params: the common level plus the year-level terms of the design used; year_level_df: distinct training years minus the rank of those (0 = SATURATED); resid_df: training rows minus the design's columns."),
  # coordinator's revisions of 2026-09-26 (Paul's fit question; the Codex methodology review)
  c("forecast_backtest / forecast_metrics / forecast_origins", "timing", "text", NA, "retrospective (every predictor from the final-vintage panel; trains on earlier outcomes only) or strict (every value available by the origin, 1 February of the target year; sheet forecast_asof). Reported separately."),
  c("forecast_asof", "(columns)", "mixed", NA, "Strict backtest: per backtest x target year x variable, the availability rule, the target sector-years with a value and how many of those values were available by the origin, with the earliest and latest availability dates."),
  c("fit", "test_id / block / family / label", "text", NA, "One row per summary block (block = 'without <unit>' for a leave-one-out fit) of this run, then the blocks only the previous R run had."),
  c("fit", "adj_r2_printed / prev_adj_r2_printed / adj_r2_change / direction", "mixed", NA, "Adjusted R^2 exactly as summary() prints it (4 significant digits), in this run and in the previous R run (parsed from its summaries file), their difference and lower / higher / same / new test / newly estimable / not in this run."),
  c("fit", "reason", "text", NA, "Why the fit differs from the previous run's: new DV, specification changed (the lm() formula: terms added or removed), weights, label, sectors added or removed, years, n, or 'same DV, formula, sectors, years and n' with the input workbooks whose SHA-256 changed; 'unchanged' when nothing differs."),
  c("fit", "r2_printed / prev_r2_printed / r2_kind / n / prev_n / resid_df / prev_resid_df / dv / prev_dv / sectors / prev_sectors / years / prev_years / min_base_cells / flag / adj_r2 / r2 / previous_run", "mixed", NA, "Multiple R^2 as printed, how R computes it (centered; uncentered without an intercept; weighted), the sample of both runs, minimum-base cells left out (EXPLORATORY variants), the DESCRIPTIVE (SATURATED) flag, the unrounded values and the previous run id."),
  c("coefficients", "term_label", "text", NA, "DESCRIPTIVE (SATURATED): a saturated SHIFT term (no year-level residual df); DESCRIPTIVE (one sector cluster): a per-sector term; DESCRIPTIVE: a test without inference. Their bootstrap lines are reference only."),
  c("coefficients", "adj_r2_with / adj_r2_without / adj_r2_change / r2_with / r2_without / r2_increment / partial_r2", "decimal", "ratio", "Incremental fit of the focal term: R^2 and adjusted R^2 of the test's model with and without the term on the same rows (as summary.lm computes them), their changes, and the partial R^2 (share of the reduced model's residual sum of squares the term explains)."),
  c("coefficients", "se_2way / p_2way / df_2way / clusters_sector / clusters_year / twoway_note", "mixed", NA, "Common-year sensitivity: two-way cluster-robust SE by sector and year (H5: champion and cycle; V_sector + V_year - V_sector x year, each with its CR1 factor), its t-based p on min(G) - 1 df; computed with >= 3 clusters in both dimensions. Not the study's inference."),
  c("coefficients", "n_years_support / temporal_support", "mixed", NA, "Effective temporal support: the distinct years (cycles) of the sample and each one's share of the absolute OLS weight on the estimate; for a term constant within years, the years with each value."),
  c("coefficients", "holm_family / holm_p", "mixed", NA, "Holm-adjusted bootstrap p within the pre-specified family (sheet multiplicity); boot_p stays the unadjusted p."),
  c("multiplicity", "(columns)", "mixed", NA, "Holm's step-down adjustment within each pre-specified family: the family, its definition and members (NOT ESTIMABLE members named), each ESTIMABLE non-DESCRIPTIVE focal term's unadjusted and Holm p, and the number of terms adjusted."),
  c("codex_review_check", "(columns)", "mixed", NA, "The Codex methodology review's numbers (run analysis-R-20260926T070630Z) against this run: quantity, the review's value, this run's, the relative difference and MATCH / MISMATCH (tolerance 1e-6)."),
  c("expected_control_timing", "(columns)", "mixed", NA, "Every expected-control value (year x chamber, 2008 on): value, method, measured_at / available_at (02 last_price_date or measured_on), after_year (measured after 31 December of its year: retrospective) and where it is used (main series; STRICT variants leave the after-year values out)."),
  c("trends", "term_label / holm_family / holm_p / se_2way / p_2way / adj_r2_with / adj_r2_without", "mixed", NA, "As in coefficients: the DESCRIPTIVE label (DESCRIPTIVE (SATURATED) rows are out of the headline and the sign agreement), the Holm p, the two-way sensitivity and the incremental fit."),
  # SEATS (Paul's follow-up of 2026-09-26: the partisanship of the spending and the expected seat gain)
  c("seats_cycle_house / seats_cycle_senate", "(columns)", "mixed", NA, "SEATS-A (DESCRIPTIVE): Mentat industry x election cycle (cycle 2022 = calendar 2021-2022), per chamber: for each base (cand = the chamber's candidate committees, 08; all = all party-labelled 04 giving) the Democratic share D / (D + R), D and R dollars (nominal and $M 2025), the base D + R, its coverage of the unit's included receipts, the status, the prior-cycle share (_lag) and its change (_change); the forecast net Democratic seat gain (seat_net_gain: Crystal Ball final call; seat_net_gain_538: 538 Lite expected seats) and its change."),
  c("seats_coverage", "(columns)", "mixed", NA, "Every unit x cycle x base x chamber of SEATS-A: the share with its D$, R$, base and coverage, and the status (incomplete cycles named)."),
  c("seats_calls", "(columns)", "mixed", NA, "The forecast Democratic net seat gain per chamber x election: projected Democratic seats minus the seats before the election (03), or the call's stated net change; the definition used for each row."),
  c("seats_cells", "estimand / chamber / cell / status / reason / holm_family", "text", NA, "Every requested SEATS cell gated estimated / descriptive only / unavailable, with the reason and the named Holm family."),
  c("seats_w_estimates", "(columns)", "mixed", NA, "SEATS-W estimand A (EXPLORATORY): per chamber x source x weighting x availability x window x model x scope (x omitted sector): weeks, forecast updates, the estimate (pp per forecast seat), the fixed-X residual moving-block bootstrap within cycle (3- and 5-week blocks; conditional intervals, null-imposed p), the recursive block bootstrap for the lagged-outcome model (dynamic), HAC SEs (lags 2 / 4 / 8; secondary, no p), the Holm family and adjusted p, and per-cycle agreement. No bootstrap p is proof."),
  c("seats_w_support / seats_w_series", "(columns)", "mixed", NA, "The weekly series behind estimand A (09 aligned, availability verified): per chamber x source x cycle the surviving weeks, weeks with a prior-week change, forecast updates, units and post-primary weeks; and the chamber x source x week series itself (pooled-dollar and equal-sector shares in pp, expected Democratic seats and their change)."),
  c("seats_race_match", "(columns)", "mixed", NA, "Every distinct named 538 slot (cycle x chamber x race x party x name) and the recipient cand_id it matched (surname within cycle, chamber, state, district and party; given names break ties), matched / ambiguous / unmatched, with the rule (surname-only matches flagged)."),
  c("seats_race_exposure", "(columns)", "mixed", NA, "Recipient candidate x weekly origin (538 Lite, with Classic / Deluxe own probabilities): incumbency from dated service at the origin (with appointment, partial-first-term and nonconsecutive flags), the provisional FEC role, whether the candidate is named in the latest row available before the window, the own probability, the race favourite's probability and party, the 538 class of the race (favourite's probability; class538_own = candidate-relative sensitivity), the side, favored non-incumbent (p > 0.5; p > 0.6), same-party and multiparty flags, the row's dates, pre-matchup-final / pre-primary flags and why no probability."),
  c("seats_race_diag / seats_race_census / seats_race_favored / seats_race_nominee / seats_race_expert_support", "(columns)", "mixed", NA, "Race-level diagnostics: match and coverage counts; candidate-weeks by incumbency x 538 class; the favored non-incumbents; the date each race's named matchup became final (the nominee proxy); weeks with a primary- or extended-eligible expert rating."),
  c("seats_b_house / seats_b_senate / seats_c_estimates", "(columns)", "mixed", NA, "Estimands B (group weekly series: slopes and contrasts on the national forecast change; classification = fixed at the pre-spending origin (primary) or rolling (sensitivity); outcome in column weighting) and C (own lagged win-probability change, fixed candidate set); conditional intervals, Holm within the named families (fixed-origin rows)."),
  c("seats_b_series_house / seats_b_series_senate / seats_b_transitions", "(columns)", "mixed", NA, "The group weekly series behind estimand B (eligible candidates, gross D / R / total, refunds, net, shares, per-candidate dollars, the national forecast change) under both classifications, and the transition counts between the fixed-origin and the rolling groups.")
)

sgs_shift_dictionary <- function() list(
  study_sector = c("text", NA, "Mentat industry of 04 / 08 (study sector, or community_banks)."),
  chamber = c("text", NA, "shift_chamber: House or Senate (the recipient's chamber)."),
  mentat_industry = c("text", NA, "04 mentat_industry of the unit."),
  is_study_sector = c("boolean", NA, "False for community_banks."),
  dem_share_house = c("decimal", "ratio 0-1", "08 sector_year_chamber dem_share, House: D / (D + R) of giving to House candidate committees (as supplied; blank when D + R <= 0)."),
  dem_share_senate = c("decimal", "ratio 0-1", "As dem_share_house, Senate."),
  dem_share_hill_house = c("decimal", "ratio 0-1", "08 sector_year_chamber_with_hill dem_share, House: DCCC added to D and NRCC to R."),
  dem_share_hill_senate = c("decimal", "ratio 0-1", "As dem_share_hill_house, Senate: DSCC added to D and NRSC to R."),
  `dem_share_*_status` = c("text", "status", "08 row status (observed / partial / missing); missing where the share is blank."),
  `dem_share_*_base_usd` = c("decimal", "USD, nominal", "dem_usd + rep_usd: the dollars the share is computed from."),
  `dem_share_*_base_real_m` = c("decimal", "$M, 2025 dollars", "dem_real_m + rep_real_m: the weight of the -W variants."),
  dem_share_all = c("decimal", "ratio 0-1", "04 all party-labelled general giving: D / (D + R) with party D / R ('Other / Unclassified' outside both), every recipient category and funding source (non_giving rows included), nominal dollars; blank when D + R <= 0."),
  dem_share_all_status = c("text", "status", "04 sector_year status; missing where the share is blank."),
  dem_share_all_d_real_m = c("decimal", "$M, 2025 dollars", "04 giving with party D."),
  dem_share_all_r_real_m = c("decimal", "$M, 2025 dollars", "04 giving with party R."),
  dem_share_all_other_real_m = c("decimal", "$M, 2025 dollars", "04 giving with party 'Other / Unclassified' (outside both)."),
  dem_share_all_dr_share = c("decimal", "ratio 0-1", "The D + R share of dollars: (D + R) / all general giving of the unit-year."),
  general_giving_real_m = c("decimal", "$M, 2025 dollars", "All 04 general giving of the unit-year (every recipient category, party and funding source)."),
  general_giving_non_giving_real_m = c("decimal", "$M, 2025 dollars", "04 giving with funding_source non_giving ('other receipt'), kept in every test (Paul: \"Keep those receipts\")."),
  exp_dem_own_chamber = c("decimal", "probability 0-1", "shift_chamber: exp_dem_house on House rows, exp_dem_senate on Senate rows (with _status / _method / _flag / _source)."),
  cur_dem_own_chamber = c("integer", "1/0", "shift_chamber: cur_dem_house on House rows, cur_dem_senate on Senate rows."),
  dem_share = c("decimal", "ratio 0-1", "shift_chamber: dem_share_house on House rows, dem_share_senate on Senate rows (with _status / _base_usd / _base_real_m); dem_share_hill likewise from the Hill sheet."),
  `shift_flag_*` = c("text", NA, paste0("Flags of the unit-year (shift_flag_house / _senate / _all; shift_chamber: shift_flag), ",
                                         "verified facts only, e.g. ", SGS$SHIFT_FLAGS[[1]]$text, ".")),
  `exp_dem_*_measured_at / _available_at / _after_year` = c("mixed", "date / boolean", "Chronology of expected control (rule set paul-2026-09-25): when the value was measured (= available): 02 last_price_date of the IEM annual mean, or 02 expected_control_2023_2026 measured_on; after_year = measured after 31 December of its year (retrospective; left out by the STRICT variants).")
)

sgs_panel_dictionary <- function() {
  d <- list(
    study_sector = c("text", NA, "Study sector (plan of 2026-09-25): the nine sectors of config.STUDY_SECTORS."),
    year = c("integer", "calendar year", "Calendar year 2006-2026."),
    tier = c("text", NA, "Job tier of 04 tier_by_year: Chief, Middle Management, Employee, Corporate."),
    partial_year = c("boolean", NA, "True for 2026 (incomplete calendar year); excluded from estimation by default."),
    pres_year = c("integer", "1/0", "00 presidential_year."),
    midterm_year = c("integer", "1/0", "00 midterm_year; odd years are the reference category."),
    cpi_status = c("text", "status", "00 row status (CPI availability); informational."),
    controls_status = c("text", "status", "observed when pres_year and midterm_year are present."),
    contributions_real_m = c("decimal", "$M, 2025 dollars", "04 general giving (Include in Analysis amount, all recipient categories, parties and funding sources) summed over companies; giving_real_2025_usd / 1e6. Tier table: the tier's share."),
    contributions_status = c("text", "status", "04 sector_year status (tier table: tier_by_year status; a tier absent in an observed sector-year is a derived 0)."),
    gifts = c("integer", "count", "Tier table: 04 tier_by_year gifts summed over companies."),
    tier_row_present = c("boolean", NA, "Tier table: False where 04 has no row for the tier (value 0 in observed sector-years)."),
    lobby_income_real_m = c("decimal", "$M, 2025 dollars", "01 LDA rebuild income_total (outside-firm fees), via crosswalk lda_lobbying_sector; never added to expenses."),
    lobby_expenses_real_m = c("decimal", "$M, 2025 dollars", "01 LDA rebuild expenses_total (self-filer in-house expenses); never added to income."),
    lobby_income_status = c("text", "status", "01 LDA row status."),
    lobby_expenses_status = c("text", "status", "01 LDA row status."),
    lobby_amount_undiff_real_m = c("decimal", "$M, 2025 dollars", "01 LobbyView undifferentiated amount, confidence = high only; LobbyView sector labels mapped through the crosswalk lda_lobbying_sector (same label set). A separate measure: never spliced onto LDA."),
    lobby_undiff_status = c("text", "status", "01 LobbyView row status (2024 is a partial sliver in the source)."),
    growth_same_year_pct = c("decimal", "percentage points", "07 growth_same_year_pct (same-vintage revenue growth t-1 to t). Telecom: blank (components kept separate)."),
    growth_previous_year_pct = c("decimal", "percentage points", "07 growth_previous_year_pct (growth t-2 to t-1). Telecom: blank."),
    growth_same_status = c("text", "status", "Status of growth_same_year_pct."),
    growth_prev_status = c("text", "status", "Status of growth_previous_year_pct."),
    growth_same_year_pct_telecom_wireless = c("decimal", "percentage points", "07 telecom_wireless component (telecom rows only)."),
    growth_previous_year_pct_telecom_wireless = c("decimal", "percentage points", "07 telecom_wireless component, one-year lag."),
    growth_same_year_pct_telecom_cable = c("decimal", "percentage points", "07 telecom_cable component (telecom rows only)."),
    growth_previous_year_pct_telecom_cable = c("decimal", "percentage points", "07 telecom_cable component, one-year lag."),
    predicted_growth_pct = c("decimal", "percentage points", "06 predicted_growth_pct (the plan's strict annual column only)."),
    forecast_publication_month = c("text", "YYYY-MM", "06 publication month of the forecast used; blank where predicted_growth_pct is blank."),
    forecast_age_months = c("integer", "months", "06 forecast age at January of the target year; blank where predicted_growth_pct is blank."),
    predicted_source_status = c("text", "status", "06 row status verbatim (partial = only the broader collected value exists)."),
    predicted_status = c("text", "status", "observed when predicted_growth_pct is present, else missing."),
    exp_dem_house = c("decimal", "probability 0-1 (0/1 for the forecaster final call)", "Expected Democratic House control: 02 IEM p_dem_expected where present (2008-2022); 2023-2026: 02 expected_control_markets when that sheet exists, else 02 expected_control_2023_2026 (2023-2024: 1 if the Crystal Ball final call of 4 Nov 2024 projects >= 218 Democratic seats, else 0; 2025-2026: 1 - p_rep_control, Kalshi/Polymarket read 24-25 Sep 2026)."),
    exp_dem_senate = c("decimal", "probability 0-1 (0/1 for the forecaster final call)", "As exp_dem_house for the Senate (final-call threshold: >= 51 Democratic seats)."),
    exp_dem_house_status = c("text", "status", "Status of the 02 row used (IEM data or the fill sheet)."),
    exp_dem_senate_status = c("text", "status", "Status of the 02 row used (IEM data or the fill sheet)."),
    exp_dem_house_method = c("text", NA, "iem_annual_mean / forecaster_final_call_binary / market_snapshot / market_daily_mean; blank where exp_dem_house is blank."),
    exp_dem_senate_method = c("text", NA, "As exp_dem_house_method, Senate."),
    exp_dem_house_flag = c("text", NA, "Timing flag of the value, e.g. 'measured Nov 2024, after the year' (2023), 'measured Sep 2026, after the year' (2025); blank otherwise."),
    exp_dem_senate_flag = c("text", NA, "As exp_dem_house_flag, Senate."),
    exp_dem_house_source = c("text", NA, "02 sheet (and source_id) the value comes from."),
    exp_dem_senate_source = c("text", NA, "02 sheet (and source_id) the value comes from, Senate."),
    mentat_industry = c("text", NA, "industry_year: 04 mentat_industry of the unit."),
    is_study_sector = c("boolean", NA, "industry_year: False for community_banks (a Mentat industry, not a study sector)."),
    cur_dem_house = c("integer", "1/0", "03 current_control dem_control, House (1 = Democratic majority most of the year)."),
    cur_dem_senate = c("integer", "1/0", "03 current_control dem_control, Senate."),
    cur_dem_house_status = c("text", "status", "03 row status (2026 derived)."),
    cur_dem_senate_status = c("text", "status", "03 row status (2026 derived)."),
    exp_shift_house = c("decimal", "probability shift", "exp_dem_house - cur_dem_house."),
    exp_shift_senate = c("decimal", "probability shift", "exp_dem_senate - cur_dem_senate."),
    exp_shift_house_status = c("text", "status", "observed when both inputs are usable."),
    exp_shift_senate_status = c("text", "status", "observed when both inputs are usable."),
    pred_dem_seat_change_house = c("decimal", "seats", "02 seat_calls pred_dem_net_change for the election of the calendar year (even years only)."),
    pred_dem_seat_change_senate = c("decimal", "seats", "02 seat_calls pred_dem_net_change, Senate (even years only)."),
    seat_calls_house_status = c("text", "status", "02 seat_calls status; not_applicable in odd years."),
    seat_calls_senate_status = c("text", "status", "02 seat_calls status; not_applicable in odd years.")
  )
  d
}

sgs_paul_panel_dictionary <- function() list(
  contributions_dedup_real_m = c("decimal", "$M, 2025 dollars", "04 general giving without recipient_category 'Company PAC' (gifts to the roster company's own PAC): the de-duplicated DV of R-dedup-C1..C3."),
  contributions_dedup_status = c("text", "status", "As contributions_status."),
  company_pac_real_m = c("decimal", "$M, 2025 dollars", "04 general giving to the roster company's own PAC (recipient_category 'Company PAC')."),
  company_pac_share = c("decimal", "ratio 0-1", "company_pac_real_m / contributions_real_m: the PAC double-count overlap of the sector-year."),
  gb538_margin_house = c("decimal", "points (D minus R)", "02 expected_control_538 series generic_ballot_margin, House: within-year mean of 538's daily generic-ballot average (H4-538 robustness only; 538's historical file was generated in September 2020)."),
  gb538_margin_house_status = c("text", "status", "observed where the 538 margin is present."),
  predicted_growth_multiyear_pct = c("decimal", "percentage points (CAGR)", "Compliant (i): a crypto or fintech multi-year CAGR of 06, placed in the spending year right after its publication (vintage rule); see sheet multiyear_register."),
  predicted_multiyear_record = c("text", NA, "06 sheet and record of the projection used, its measure and availability date."),
  predicted_multiyear_status = c("text", "status", "observed where a projection is placed; missing for crypto / fintech otherwise; not_applicable for other sectors."),
  dem_share_house = c("decimal", "ratio 0-1", "08 sector_year_chamber dem_share, House: dem_usd / (dem_usd + rep_usd) of general giving to House candidate committees (conduits outside)."),
  dem_share_senate = c("decimal", "ratio 0-1", "As dem_share_house, Senate."),
  dem_share_house_status = c("text", "status", "08 row status (copied from 04 sector_year)."),
  dem_share_senate_status = c("text", "status", "08 row status (copied from 04 sector_year)."),
  dem_share_house_base_usd = c("decimal", "USD, nominal", "dem_usd + rep_usd, House: the dollar base of the share."),
  dem_share_senate_base_usd = c("decimal", "USD, nominal", "dem_usd + rep_usd, Senate: the dollar base of the share."),
  dem_share_house_base_real_m = c("decimal", "$M, 2025 dollars", "dem_real_m + rep_real_m, House."),
  dem_share_senate_base_real_m = c("decimal", "$M, 2025 dollars", "dem_real_m + rep_real_m, Senate."),
  dem_share_hill_house = c("decimal", "ratio 0-1", "DS+Hill: House share with DCCC added to D and NRCC to R (blank: 08 does not split the Hill committees by sector-year)."),
  dem_share_hill_senate = c("decimal", "ratio 0-1", "DS+Hill: Senate share with DSCC added to D and NRSC to R (blank: as above)."),
  dem_share_hill_house_status = c("text", "status", "Status of dem_share_hill_house."),
  dem_share_hill_senate_status = c("text", "status", "Status of dem_share_hill_senate."),
  dem_share_hill_house_base_usd = c("decimal", "USD, nominal", "DS+Hill from 08 sector_year_chamber_with_hill (SHIFT rule): dem_usd + rep_usd of the Hill-inclusive House row; _senate likewise; _base_real_m in $M 2025."),
  telecom_growth_method = c("text", NA, "Telecom rows (rulings of 2026-09-26, Paul's ask; the plan kept the components separate): how growth_same_year_pct / growth_previous_year_pct combine the wireless and cable components of 07 (revenue-weighted, or equal weights)."),
  telecom_predicted_method = c("text", NA, "Telecom rows: how predicted_growth_pct combines the 06 component_forecasts of wireless and cable (baseline-revenue-weighted, or equal weights)."),
  predicted_growth_flag = c("text", NA, "Source of a one-year growth value 06 holds for crypto / fintech outside the strict column, placed in predicted_growth_pct (rulings of 2026-09-26); blank for the strict values."),
  growth_same_year_pct_tw = c("decimal", "percentage points", "growth_same_year_pct with telecom's value replaced by the wireless component (R-TW-* robustness); _tc: the cable component (R-TC-*). The previous-year and predicted columns follow the same pattern."),
  growth_previous_year_pct_pos = c("decimal", "percentage points", "ASYM: max(growth, 0); _neg = min(growth, 0) (so growth = _pos + _neg); same pattern for growth_same_year_pct and predicted_growth_pct."),
  growth_previous_year_pct_decel = c("decimal", "1/0", "DECEL: 1 when the growth variable is below its prior-year value in the same sector (both usable), else 0; _x_decel = growth x _decel; _decel_status = observed when both years are usable. Same pattern for the other growth variables."),
  contracted_prior = c("decimal", "1/0", "CONTRACT (Paul's hypothesis, 2026-09-26): 1 when growth_previous_year_pct < 0 (the industry contracted the year before), else 0; status of growth_previous_year_pct."),
  exp_dem_house_measured_at = c("text", "YYYY-MM-DD", "Chronology (coordinator's revision of 2026-09-26): when exp_dem_house was measured - 02 data last_price_date (IEM annual mean) or 02 expected_control_2023_2026 measured_on (a day range gives its last day); exp_dem_senate_measured_at likewise."),
  exp_dem_house_available_at = c("text", "YYYY-MM-DD", "Equal to measured_at (the value is public once measured); _senate likewise."),
  exp_dem_house_after_year = c("boolean", NA, "True when the value was measured after 31 December of its year (2023: the Nov 2024 final call; 2025: the Sep 2026 market snapshot): retrospective; the STRICT variants leave such rows out. _senate likewise."),
  growth_vintage = c("text", "YYYY-MM", "07 report_vintage of the sector's growth series (telecom: the later of its two components'): the availability date of growth_previous_year_pct / contracted_prior in the strict forecast backtest.")
)

SGS_EST_COLS <- c("test_id", "family", "label", "status", "window_used", "window_kind", "fallback_search", "n", "n_window",
                  "n_sectors", "sectors", "n_years", "years", "resid_df", "reason_short", "reason", "default_attempt",
                  "fallback_attempt", "exclusions", "dv", "dv_column", "dv_label", "focal", "controls", "fixed_effects", "variant",
                  "base_test", "year_filter", "tiers", "note", "unit", "n_champions", "n_member_cycles", "boards",
                  "cluster_by", "n_clusters", "gate_rule", "inference", "flag", "input_flags")
SGS_COEF_COLS <- c("test_id", "label", "source_test", "window_used", "n", "n_sectors", "n_years", "years", "unit_of_analysis",
                   "n_champions", "n_member_cycles", "cycles", "dv_column", "resid_df", "sectors", "boards", "controls",
                   "fixed_effects", "coefficient", "focal", "estimate", "unit",
                   "hc1_se", "cr1_se", "t_cr1", "boot_p", "ci_low", "ci_high", "ci_text", "boot_draws", "boot_enumerated",
                   "boot_note", "inference", "flag", "stratification", "left_out", "subfit_status", "subfit_reason",
                   "subfit_flag")
SGS_STRATA_COLS <- c("test_id", "coefficient", "study_sector", "board", "status", "estimate", "hc1_se", "cr1_se", "n",
                     "resid_df", "years", "cycles", "n_champions", "reason")
SGS_SAMPLE_COLS <- c("test_id", "window_used", "study_sector", "year", "tier", "y", "board", "bioguide", "cycle")
SGS_SOURCE_COLS <- c("file", "workbook", "absolute_path", "sha256", "size_bytes", "mtime_utc", "read_at_utc", "sheets_read",
                     "rows_read", "note", "engine")

# "" -> NA so empty text is a blank cell (as openpyxl leaves it); +-Inf -> NA (the interval is in ci_text).
.clean_frame <- function(df) {
  for (j in seq_along(df)) {
    v <- df[[j]]
    if (is.character(v)) v[!is.na(v) & !nzchar(v)] <- NA
    if (is.numeric(v)) v[!is.finite(v)] <- NA
    df[[j]] <- v
  }
  df
}

sgs_write_results_workbook <- function(path, est_rows, coef_rows, strata_rows, sample_df, tables, sources, extra_sheets = list(),
                                       paul = FALSE) {
  dic <- lapply(SGS_RESULT_DICTIONARY, function(r) list(sheet = r[1], column = r[2], type = r[3], unit = r[4], definition = r[5]))
  pd <- sgs_panel_dictionary()
  for (col in names(pd)) dic[[length(dic) + 1L]] <- list(sheet = "sector_year / sector_year_tier", column = col, type = pd[[col]][1],
                                                         unit = pd[[col]][2], definition = pd[[col]][3])
  if (paul) {
    for (r in SGS_PAUL_DICTIONARY) dic[[length(dic) + 1L]] <- list(sheet = r[1], column = r[2], type = r[3], unit = r[4], definition = r[5])
    ppd <- sgs_paul_panel_dictionary()
    for (col in names(ppd)) dic[[length(dic) + 1L]] <- list(sheet = "sector_year", column = col, type = ppd[[col]][1],
                                                           unit = ppd[[col]][2], definition = ppd[[col]][3])
    if ("shift_year" %in% names(extra_sheets)) {
      sd <- sgs_shift_dictionary()
      for (col in names(sd)) dic[[length(dic) + 1L]] <- list(sheet = "shift_year / shift_chamber", column = col, type = sd[[col]][1],
                                                            unit = sd[[col]][2], definition = sd[[col]][3])
    }
  }
  sheets <- list(
    estimability = sgs_rows_df(est_rows, SGS_EST_COLS),
    coefficients = sgs_rows_df(coef_rows, c(SGS_COEF_COLS, if (paul) SGS_COEF_DIAG_COLS)),
    strata = sgs_rows_df(strata_rows, SGS_STRATA_COLS),
    samples = sample_df[, c(SGS_SAMPLE_COLS, if (paul && "chamber" %in% names(sample_df)) "chamber"), drop = FALSE],
    sector_year = tables$sector_year,
    sector_year_tier = tables$sector_year_tier
  )
  if (!is.null(tables$industry_year)) sheets$industry_year <- tables$industry_year
  if (!is.null(tables$champions)) sheets$champions <- tables$champions
  for (nm in names(extra_sheets)) sheets[[nm]] <- extra_sheets[[nm]]
  sheets$dictionary <- sgs_rows_df(dic, c("sheet", "column", "type", "unit", "definition"))
  sheets$sources <- sgs_rows_df(sources, SGS_SOURCE_COLS)
  sheets <- lapply(sheets, .clean_frame)
  sgs_write_xlsx(path, sheets)
  invisible(sheets)
}

# Most frequent blocking inputs / checks across NOT ESTIMABLE sector-year tests, per window kind. Ties are ordered by
# first appearance (Python iterates a set here, so its tie order depends on string hashing).
sgs_blocking_summary <- function(attempts_by_test) {
  out <- list()
  for (kind in c("default", "fallback", "preview")) {
    cnt <- integer(0)
    for (atts in attempts_by_test) {
      for (a in atts) {
        if (!identical(a$kind, kind) || isTRUE(a$ok)) next
        items <- character(0)
        for (r in a$reasons) {
          if (startsWith(r, "blocking inputs: ")) {
            items <- c(items, strsplit(substring(r, nchar("blocking inputs: ") + 1), "; ", fixed = TRUE)[[1]])
          } else if (startsWith(r, "no run of")) {
            items <- c(items, strsplit(r, " (", fixed = TRUE)[[1]][1])
          } else if (grepl("distinct years", r, fixed = TRUE) && grepl("<", r, fixed = TRUE)) {
            items <- c(items, "fewer distinct years than required")
          } else if (startsWith(r, "year-level design not identified")) {
            items <- c(items, paste0("year-level design not identified: ", sub(".*; not identified: ", "", r)))
          } else {
            items <- c(items, strsplit(r, ";", fixed = TRUE)[[1]][1])
          }
        }
        for (it in unique(items)) cnt[it] <- if (is.na(cnt[it])) 1L else cnt[it] + 1L
      }
    }
    o <- order(-cnt, seq_along(cnt))
    top <- head(cnt[o], 12)
    out[[kind]] <- top
  }
  out
}

.denominator <- function(r) {
  if (identical(.g(r, "unit"), SGS_H5_UNIT)) {
    if (is.na(.g(r, "n"))) return("n/a")
    yrs <- .g(r, "years"); if (is.na(yrs) || !nzchar(yrs)) yrs <- "none"
    return(paste0(sgs_py_str(r$n), " rows (", sgs_py_str(.g(r, "n_champions")), " champions, ",
                  sgs_py_str(.g(r, "n_member_cycles")), " member-cycles) in cycles ", yrs))
  }
  if (is.na(.g(r, "n"))) return("n/a")
  paste0(sgs_py_str(r$n), " (", sgs_py_str(.g(r, "n_sectors")), " x ", sgs_py_str(.g(r, "n_years")), ") in ",
         (if (is.na(.g(r, "n_window"))) "" else r$n_window))
}

.txt0 <- function(x) if (is.null(x) || !length(x) || is.na(x)) "" else as.character(x)

sgs_write_estimability_md <- function(path, run_id, est_rows, attempts_by_test, windows) {
  st <- vapply(est_rows, function(r) r$status, "")
  fb <- windows$fallback
  fb_text <- if (!is.null(fb)) paste0("only if the default fails, the most recent run of >= ", SGS$MIN_YEARS_FALLBACK,
                                      " consecutive calendar years within ", fb[1], "-", fb[2], " in which the test's complete-case sample exists, using ",
                                      if (SGS$FALLBACK_WHOLE_RUN) "the whole run" else paste0("its most recent ", SGS$MIN_YEARS_FALLBACK, " years"))
             else "no fallback"
  L <- c(paste0("# Estimability, run ", run_id), "",
         paste0("Sector-year tests (Paul's R8 and the fallback ruling of 2026-09-25): default ", windows$default[1], "-", windows$default[2],
                " needs >= ", SGS$MIN_YEARS_DEFAULT, " distinct years; fallback: ", fb_text, "; >= ", SGS$MIN_SECTORS, " sectors (every ",
                "sector with complete data enters); full-rank design with the year-level regressors checked against the distinct ",
                "years; residual df >= ", SGS$MIN_RESID_DF, ". 2026 is partial and excluded."), "",
         paste0("H5 (champions, unit ", SGS_H5_UNIT, "): member-cycle gate, not the 6-year sector-year gate: >= ", SGS$H5_MIN_CYCLES,
                " cycles, >= ", SGS$H5_MIN_MEMBER_CYCLES, " member-cycles, non-zero variance of the focal regressor (within champion ",
                "for H5-within), focal identified, residual df >= ", SGS$MIN_RESID_DF, "."), "",
         paste0("PREVIEW tests (", SGS$PREVIEW_FLAG, "): fixed window ", SGS$PREVIEW_WINDOW[1], "-", SGS$PREVIEW_WINDOW[2],
                " (5 full years), >= ", SGS$PREVIEW_MIN_YEARS, " distinct years, >= ", SGS$MIN_SECTORS, " sectors, full rank, ",
                "residual df >= ", SGS$MIN_RESID_DF, ", no fallback; the full core specification is NOT IDENTIFIED when its ",
                "year-level parameters are as many as the distinct years (not forced)."), "",
         paste0("Tests: ", length(est_rows), ". ESTIMABLE ", sum(st == SGS_ESTIMABLE), "; NOT ESTIMABLE ", sum(st == SGS_NOT_ESTIMABLE),
                "; NOT BUILT ", sum(st == SGS_NOT_BUILT), "."), "",
         paste0("## Most frequent blockers of the sector-year tests (tests blocked; derived H1/H4 read-outs count with their ",
                "source test)"), "")
  bs <- sgs_blocking_summary(attempts_by_test)
  for (kind in names(bs)) {
    L <- c(L, paste0(kind, " window:"), "")
    items <- bs[[kind]]
    for (i in seq_along(items)) L <- c(L, paste0("- ", items[[i]], " tests: ", .md_escape(names(items)[i])))
    L <- c(L, "")
  }
  h5 <- Filter(function(r) identical(.g(r, "unit"), SGS_H5_UNIT) && r$status != SGS_ESTIMABLE, est_rows)
  if (length(h5)) {
    L <- c(L, "H5 (member-cycle gate):", "")
    for (r in h5) {
      why <- if (nzchar(.txt0(r$reason_short))) r$reason_short else .txt0(r$reason)
      L <- c(L, paste0("- ", r$test_id, ": ", r$status, ": ", .md_escape(why)))
    }
    L <- c(L, "")
  }
  L <- c(L, "## Every test", "",
         paste0("n = complete-case rows (sectors x distinct years) of the estimated sample, or of the last window attempted, ",
                "counted in the window named after it; H5: board x champion x cycle rows, champions and member-cycles. The full ",
                "reason, with every sector-level gap, is in the `reason` column of the results workbook."), "",
         "| test | label | status | window used | n in window | reason |", "|---|---|---|---|---|---|")
  for (r in est_rows) {
    wtxt <- .txt0(r$window_used)
    if (identical(.g(r, "window_kind"), "fallback") && nzchar(.txt0(r$fallback_search))) wtxt <- paste0(wtxt, " (fallback)")
    why <- if (nzchar(.txt0(r$reason_short))) r$reason_short else .txt0(r$reason)
    L <- c(L, paste0("| ", r$test_id, " | ", sgs_label_text(r$label), " | ", r$status, " | ", wtxt, " | ", .denominator(r), " | ",
                     .md_escape(why), " |"))
  }
  sgs_write_lines_crlf(path, L)
}

# ---- coverage table (rulings of 2026-09-26): every study sector and Mentat book x test family, IN or OUT with the reason

SGS_COVERAGE_FAMILIES <- list(
  list(key = "C", label = "C (contributions)", families = "C"),
  list(key = "C-PV", label = "C preview 2021-2025", families = "C-PV"),
  list(key = "L", label = "L (LDA lobbying)", families = "L"),
  list(key = "L-LV", label = "L-LV (LobbyView)", families = "L-LV"),
  list(key = "T", label = "T (tiers)", families = "T"),
  list(key = "DS", label = "DS (Democratic share)", families = "DS"),
  list(key = "ASYM", label = "ASYM", families = "ASYM"),
  list(key = "DECEL", label = "DECEL", families = "DECEL"),
  list(key = "SLOPES", label = "SLOPES", families = "SLOPES"),
  list(key = "CONTRACT", label = "CONTRACT", families = "CONTRACT"),
  list(key = "ASYM-SLOPES", label = "ASYM-SLOPES", families = "ASYM-SLOPES"),
  list(key = "BANKSPLIT", label = "Bank split", families = "BANKSPLIT"),
  list(key = "H1-PV", label = "H1-PV (industry preview)", families = "H1-PV"),
  list(key = "H5", label = "H5 (champions)", families = "H5"),
  list(key = "SHIFT", label = "SHIFT (partisan share, 2020-2025)", families = "SHIFT"),
  list(key = "SHIFT-PV", label = "SHIFT preview 2021-2025", families = "SHIFT-PV")
)
SGS_COVERAGE_UNITS <- c(SGS$STUDY_SECTORS, "community_banks")
SGS_H5_BOARD_SECTOR <- c(bank = "commercial_banks", banking = "commercial_banks", credit_union = "credit_unions",
                         crypto = "crypto", fintech = "fintech", community_banks = "community_banks",
                         credit_arms = "credit_arms", property_casualty = "property_casualty", telecom = "telecom")

.coverage_book <- function(unit, xw) {
  if (unit == "community_banks") return(unname(SGS$MENTAT_BOOKS["community_banks"]))
  mi <- xw$mentat_industry[match(unit, xw$study_sector)]
  if (is.na(mi)) return("no Mentat book")
  b <- SGS$MENTAT_BOOKS[mi]
  if (is.na(b)) mi else unname(b)
}

# Why a unit is not in a test's sample: the unit's own blocking inputs, in plain words.
.coverage_reason <- function(unit, smp, tables, spec) {
  tab <- tables[[spec$table]]
  u <- if (identical(spec$table, "sector_year_banks") && unit == "commercial_banks") SGS$BANK_SPLIT_BIG else unit
  if (is.null(tab) || !u %in% tab$study_sector) {
    if (spec$table %in% c("industry_year", SGS_SHIFT_TABLES, SGS_SEATS_TABLES)) return("no Mentat contribution workbook (04 / 08 have no book for this sector)")
    if (unit == "community_banks") return("not a study sector: enters only the bank split (BS, BANK), H1-PV and SHIFT")
    return("not in the analysis table of this family")
  }
  if (!is.null(spec$sectors) && !u %in% spec$sectors) return("outside the bank-only sample")
  if (!is.null(smp) && u %in% names(smp$singletons %||% character(0))) {
    return(paste0("one complete sector-year (", smp$singletons[[u]], ") only: absorbed by its sector fixed effect"))
  }
  vars <- character(0)
  if (!is.null(smp)) for (it in smp$items) if (identical(it$kind, "sector") && identical(it$sector, u)) vars <- it$vars
  if (!length(vars)) return(paste0("no complete sector-year in the window ", if (!is.null(smp)) paste(smp$window, collapse = "-") else ""))
  why <- character(0)
  for (v in vars) {
    w <- if (v %in% c("contributions_real_m", "contributions_dedup_real_m") && unit %in% c("life_insurance", "auto_manufacturing")) {
      "no Mentat contribution workbook (04 has no book for this sector)"
    } else if (sgs_is_growth_var(v) && unit %in% c("crypto", "fintech")) {
      sy <- tables$sector_year
      yp <- sy$year[sy$study_sector == unit & !is.na(sy$predicted_growth_pct)]
      paste0("no annual growth series in the window (06 / 07 hold multi-year projections",
             if (length(yp)) paste0("; one-year values only for ", sgs_years_text(yp)) else "", ")")
    } else if (v %in% c("lobby_lv_real_m", "lobby_amount_undiff_real_m") && unit == "credit_arms") {
      "LobbyView coverage thin in every sector-year (fewer than 5 reporting clients: Ally only); R-LV-thin keeps it"
    } else if (v %in% c("lobby_lv_real_m", "lobby_amount_undiff_real_m")) {
      "no usable LobbyView amount in the window (thin or partial sector-years excluded)"
    } else if (v %in% c("lobby_income_real_m", "lobby_expenses_real_m")) {
      "no LDA series (01 data covers banks and credit unions only)"
    } else if (startsWith(v, "dem_share_all")) {
      "no party-labelled (D / R) 04 giving"
    } else if (startsWith(v, "dem_share")) {
      "no usable 08 Democratic share"
    } else if (sgs_is_growth_var(v)) {
      paste0(v, " unusable throughout the window")
    } else {
      paste0(v, " unusable throughout the window")
    }
    why <- c(why, w)
  }
  paste(unique(why), collapse = "; ")
}

# The coverage table: data.frame(unit, mentat_book, family, status, reason, tests). status: IN (in the sample of an
# ESTIMABLE test of the family), IN* (in the complete-case sample of the family's tests, none ESTIMABLE yet), OUT,
# NOT BUILT. ROBUSTNESS variants (which change samples on purpose) are left out.
sgs_coverage_table <- function(order_, decisions, est_rows, tables, xw) {
  rows <- setNames(est_rows, vapply(est_rows, `[[`, "", "test_id"))
  out <- list()
  for (fam in SGS_COVERAGE_FAMILIES) {
    ids <- names(order_)[vapply(order_, function(t) t$family %in% fam$families && !identical(t$label, "ROBUSTNESS") &&
                                  !identical(t$variant, "derived"), TRUE)]
    if (!length(ids)) next
    fam_reason <- ""
    for (id in ids) if (!identical(rows[[id]]$status, SGS_ESTIMABLE)) { fam_reason <- .txt0(rows[[id]]$reason_short); break }
    for (u in SGS_COVERAGE_UNITS) {
      est_in <- character(0); att_in <- character(0); built_any <- FALSE; why <- character(0); nb <- ""
      for (id in ids) {
        t <- order_[[id]]; d <- decisions[[id]]
        if (identical(d$status, SGS_NOT_BUILT)) { if (!nzchar(nb)) nb <- .txt0(d$reason); next }
        built_any <- TRUE
        if (identical(t$table, "champions")) {
          smp <- d$sample
          secs <- if (!is.null(smp) && nrow(smp$df)) unique(unname(SGS_H5_BOARD_SECTOR[as.character(smp$df$board)])) else character(0)
          if (u %in% secs) { if (identical(d$status, SGS_ESTIMABLE)) est_in <- c(est_in, id) else att_in <- c(att_in, id) }
          else why <- c(why, "no champions board in 05")
          next
        }
        att <- sgs_decision_chosen(d) %||% (if (length(d$attempts)) d$attempts[[length(d$attempts)]] else NULL)
        smp <- att$sample
        uu <- if (identical(t$table, "sector_year_banks") && u == "commercial_banks") SGS$BANK_SPLIT_BIG else u
        if (!is.null(smp) && uu %in% smp$df$study_sector) {
          if (identical(d$status, SGS_ESTIMABLE)) est_in <- c(est_in, id) else att_in <- c(att_in, id)
        } else {
          why <- c(why, .coverage_reason(u, smp, tables, t))
        }
      }
      status <- if (length(est_in)) "IN" else if (length(att_in)) "IN*" else if (!built_any) "NOT BUILT" else "OUT"
      reason <- switch(status, IN = "", `IN*` = paste0("in the complete-case sample; no test of the family is ESTIMABLE yet: ", fam_reason),
                       `NOT BUILT` = nb, OUT = paste(unique(why), collapse = "; "))
      out[[length(out) + 1L]] <- list(unit = u, mentat_book = .coverage_book(u, xw), family = fam$label, status = status,
                                      reason = reason, tests = paste(c(est_in, att_in), collapse = ", "))
    }
  }
  sgs_rows_df(out, c("unit", "mentat_book", "family", "status", "reason", "tests"))
}

# Markdown: one row per unit, one column per family; OUT cells point to numbered reasons.
sgs_coverage_md <- function(cov) {
  fams <- unique(cov$family)
  reasons <- unique(cov$reason[cov$status %in% c("OUT", "NOT BUILT") & nzchar(cov$reason)])
  cell <- function(r) {
    if (r$status %in% c("OUT", "NOT BUILT")) paste0(r$status, " (", match(r$reason, reasons), ")") else r$status
  }
  L <- c(paste0("| sector (Mentat book) | ", paste(fams, collapse = " | "), " |"),
         paste0("|", paste(rep("---", length(fams) + 1), collapse = "|"), "|"))
  for (u in unique(cov$unit)) {
    sub <- cov[cov$unit == u, , drop = FALSE]
    cells <- vapply(fams, function(f) { k <- which(sub$family == f); if (!length(k)) "" else cell(sub[k[1], , drop = FALSE]) }, "")
    L <- c(L, paste0("| ", u, " (", sub$mentat_book[1], ") | ", paste(cells, collapse = " | "), " |"))
  }
  star <- unique(cov[cov$status == "IN*", c("family", "reason"), drop = FALSE])
  c(L, "", "IN = in the sample of an ESTIMABLE test of the family; IN* = in the complete-case sample, but no test of the family is ESTIMABLE yet; OUT / NOT BUILT (n) = reason n below. ROBUSTNESS variants are not counted (R-LV-thin keeps thin LobbyView sector-years, e.g. credit_arms).",
    "", paste0("- (", seq_along(reasons), ") ", .md_escape(reasons)),
    if (nrow(star)) c("", paste0("- IN* ", star$family, ": ", .md_escape(sub("^in the complete-case sample; no test of the family is ESTIMABLE yet: ", "", star$reason))))
    else character(0))
}

.coef_line <- function(c, r) {
  if (identical(c$test, "joint")) {
    return(paste0("- ", c$coefficient, ": F = ", sgs_fmt(c$estimate), " (", c$unit, "); wild cluster restricted bootstrap p = ",
                  sgs_fmt(.g(c, "boot_p")), " (", sgs_py_str(.g(c, "boot_draws")), " draws",
                  if (isTRUE(.g(c, "boot_enumerated"))) ", enumerated" else "", "); ", .txt0(c$boot_note), "."))
  }
  h5 <- identical(.g(r, "unit"), SGS_H5_UNIT)
  where <- if (h5) {
    paste0("cycles ", .txt0(r$years), ", n = ", sgs_py_str(r$n), " (", sgs_py_str(.g(r, "n_champions")), " champions, ",
           sgs_py_str(.g(r, "n_member_cycles")), " member-cycles), residual df ", sgs_py_str(.g(r, "resid_df")))
  } else {
    paste0("window ", .txt0(r$window_used), ", n = ", sgs_py_str(r$n), " (", sgs_py_str(.g(r, "n_sectors")), " sectors x ",
           sgs_py_str(.g(r, "n_years")), " years: ", .txt0(.g(r, "years")), "), residual df ", sgs_py_str(.g(r, "resid_df")))
  }
  flag <- if (.nz(.g(c, "flag"))) paste0(" Flag: ", c$flag, ".") else ""
  if (startsWith(.txt0(.g(c, "inference")), "none")) {
    return(paste0("- ", c$coefficient, ": b = ", sgs_fmt(c$estimate), " (", c$unit, "); HC1 se ", sgs_fmt(.g(c, "hc1_se")),
                  " (reference only); ", where, ". ", sgs_py_str(.g(c, "boot_note")), ". ", c$stratification, ".", flag))
  }
  enum <- .g(c, "boot_enumerated")
  paste0("- ", c$coefficient, ": b = ", sgs_fmt(c$estimate), " (", c$unit, "); bootstrap 95% CI ", c$ci_text, ", p = ",
         sgs_fmt(.g(c, "boot_p")), " (", sgs_py_str(.g(c, "boot_draws")), " draws", if (isTRUE(enum)) ", enumerated" else "",
         "); CR1 se ", sgs_fmt(.g(c, "cr1_se")), "; HC1 se ", sgs_fmt(.g(c, "hc1_se")), "; ", where, ". ", c$stratification, ".",
         flag, if (.nz(.g(c, "boot_note"))) paste0(" ", c$boot_note) else "")
}

sgs_write_report_md <- function(path, run_id, est_rows, coef_rows, strata_rows, specs, sources, windows, params, notes,
                                extra_sections = character(0), engine_line = NULL) {
  st <- vapply(est_rows, function(r) r$status, "")
  fb <- windows$fallback
  L <- c(paste0("# Sector growth and political spending: analysis run ", run_id), "",
         "Exploratory observational study (plan of 2026-09-25). Associations only; no causal reading. Numbers only below.", "",
         "## Run", "",
         paste0("- Sector-year windows: default ", windows$default[1], "-", windows$default[2], " (>= ", SGS$MIN_YEARS_DEFAULT,
                " years); fallback ",
                if (!is.null(fb)) paste0("(only if the default fails) the most recent ", SGS$MIN_YEARS_FALLBACK, " consecutive years of the most recent ",
                                         "run of >= ", SGS$MIN_YEARS_FALLBACK, " consecutive complete-case years within ", fb[1], "-", fb[2])
                else "none",
                "; >= ", SGS$MIN_SECTORS, " sectors; residual df >= ", SGS$MIN_RESID_DF, "."),
         paste0("- H5 gate (member-cycle based): >= ", SGS$H5_MIN_CYCLES, " cycles, >= ", SGS$H5_MIN_MEMBER_CYCLES, " member-cycles, ",
                "non-zero focal variance."),
         paste0("- Inference: wild cluster restricted bootstrap (by sector; H5 by champion), Webb six-point weights, B = ",
                sgs_py_fixed(params$B, 0, comma = TRUE), " (all 6^G draws enumerated when 6^G <= B), seed ", sgs_int_str(params$seed),
                ", 95% interval by test inversion; ", "HC1 errors for reference only. DESCRIPTIVE tests: estimate and HC1 only."),
         paste0("- PREVIEW tests: fixed window ", SGS$PREVIEW_WINDOW[1], "-", SGS$PREVIEW_WINDOW[2], " (5 full years); every PREVIEW ",
                "output reads '", SGS$PREVIEW_FLAG, "'."),
         paste0("- Tests: ", length(est_rows), "; ESTIMABLE ", sum(st == SGS_ESTIMABLE), ", NOT ESTIMABLE ", sum(st == SGS_NOT_ESTIMABLE),
                ", NOT BUILT ", sum(st == SGS_NOT_BUILT), "."))
  if (!is.null(engine_line)) L <- c(L, engine_line)
  L <- c(L, "- Inputs (SHA-256, first 16 hex):")
  for (s in sources) {
    sha <- if (is.na(.g(s, "sha256"))) "n/a" else substr(s$sha256, 1, 16)
    L <- c(L, paste0("  - ", s$file, ": ", sha, if (.nz(.g(s, "note"))) paste0(" (", s$note, ")") else ""))
  }
  if (length(notes)) L <- c(L, "", "## Build notes", "", paste0("- ", notes))
  if (length(extra_sections)) L <- c(L, "", extra_sections)
  by_test <- split(coef_rows, vapply(coef_rows, function(c) c$test_id, ""))
  st_key <- vapply(strata_rows, function(s) paste(s$test_id, s$coefficient, sep = "\r"), "")
  L <- c(L, "", "## Tests", "")
  for (r in est_rows) {
    spec <- specs[[r$test_id]]
    h5 <- identical(.g(r, "unit"), SGS_H5_UNIT)
    L <- c(L, paste0("### ", r$test_id, " (", sgs_label_text(r$label), "): ", r$status), "")
    dvc <- if (nzchar(.txt0(r$dv_column))) r$dv_column else spec$dv
    dv <- paste0(dvc, if (nzchar(.txt0(r$dv_label))) paste0(" (", r$dv_label, ")") else "")
    L <- c(L, paste0("- DV: ", dv, "; focal: ", if (length(spec$focal)) paste(spec$focal, collapse = ", ") else "n/a",
                     "; controls: ", if (length(spec$controls)) paste(spec$controls, collapse = ", ") else "none",
                     "; fixed effects: ", if (length(spec$fe)) paste(spec$fe, collapse = ", ") else "none",
                     "; variant: ", if (nzchar(.txt0(r$variant))) r$variant else spec$variant, "; unit: ",
                     if (nzchar(.txt0(r$unit))) r$unit else spec$unit,
                     if (!is.na(spec$base)) paste0("; source test: ", spec$base) else ""))
    note <- if (nzchar(.txt0(r$note))) r$note else spec$note
    if (nzchar(note)) L <- c(L, paste0("- Note: ", note))
    if (r$status != SGS_ESTIMABLE) {
      L <- c(L, paste0("- Reason: ", .txt0(r$reason)), "")
      next
    }
    if (h5) {
      L <- c(L, paste0("- Gate: ", r$gate_rule, "."))
      L <- c(L, paste0("- Sample: cycles ", r$years, "; n = ", sgs_py_str(r$n), " rows (", sgs_py_str(r$n_champions),
                       " champions = clusters, ", sgs_py_str(r$n_member_cycles), " member-cycles, boards ", r$boards,
                       "); residual df ", sgs_py_str(r$resid_df), "."))
    } else {
      L <- c(L, paste0("- Window: ", r$window_used, " (", r$window_kind,
                       if (nzchar(.txt0(r$fallback_search))) paste0("; ", r$fallback_search) else "",
                       "); denominator: n = ", sgs_py_str(r$n), " rows, ", sgs_py_str(r$n_sectors), " sectors (", r$sectors, "), ",
                       sgs_py_str(r$n_years), " years (", r$years, "); residual df ", sgs_py_str(r$resid_df), "."))
    }
    if (nzchar(.txt0(r$exclusions))) L <- c(L, paste0("- Exclusions: ", r$exclusions))
    if (nzchar(.txt0(r$input_flags))) L <- c(L, paste0("- Input flags (expected control not from the IEM annual mean): ", r$input_flags))
    if (nzchar(.txt0(.g(r, "extra_line")))) L <- c(L, r$extra_line)
    cs <- by_test[[r$test_id]] %||% list()
    for (c in cs) {
      if (.nz(.g(c, "left_out"))) next
      L <- c(L, .coef_line(c, r))
      src <- if (.nz(.g(c, "source_test"))) c$source_test else r$test_id
      for (s in strata_rows[st_key == paste(src, c$coefficient, sep = "\r")]) {
        name <- if (.nz(.g(s, "board"))) paste0("board ", s$board) else s$study_sector
        if (identical(s$status, "estimated")) {
          extra <- if (.nz(.g(s, "board"))) {
            paste0(", CR1 se ", sgs_fmt(.g(s, "cr1_se")), "; n = ", sgs_py_str(s$n), ", ", sgs_py_str(.g(s, "n_champions")),
                   " champions, cycles ", .txt0(.g(s, "cycles")))
          } else paste0("; n = ", sgs_py_str(s$n), ", years ", s$years)
          L <- c(L, paste0("  - stratum ", name, ": b = ", sgs_fmt(s$estimate), " (HC1 se ", sgs_fmt(s$hc1_se), extra,
                           ", residual df ", sgs_py_str(s$resid_df), ")"))
        } else {
          L <- c(L, paste0("  - stratum ", name, ": insufficient (", s$reason, ")"))
        }
      }
    }
    for (c in cs) {
      if (!.nz(.g(c, "left_out"))) next
      if (identical(.g(c, "subfit_status"), "estimated")) {
        L <- c(L, paste0("- without ", c$left_out, ": ", c$coefficient, " b = ", sgs_fmt(c$estimate), " (", c$unit, "), CI ", c$ci_text,
                         ", p = ", sgs_fmt(.g(c, "boot_p")), "; n = ", sgs_py_str(c$n), " (", sgs_py_str(c$n_sectors), " sectors, ",
                         sgs_py_str(c$n_years), " years: ", c$years, "). ", .txt0(.g(c, "subfit_flag"))))
      } else {
        L <- c(L, paste0("- without ", c$left_out, ": ", c$coefficient, " not estimable (", .txt0(.g(c, "subfit_reason")), "). ",
                         .txt0(.g(c, "subfit_flag"))))
      }
    }
    L <- c(L, "")
  }
  sgs_write_lines_crlf(path, L)
}
