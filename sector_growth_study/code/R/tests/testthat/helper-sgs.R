# Shared helpers of the testthat suite: load the R modules and build synthetic data (no real workbook is read by any
# test). R port of code/tests/helpers.py and synth_workbooks.py; the synthetic draws use R's generator, so the tests
# check the same properties as the Python tests, not the same numbers.

if (!requireNamespace("readxl", quietly = TRUE)) .libPaths(c("C:/Users/pgoff/AppData/Local/R/win-library/4.6", .libPaths()))
SGS_TEST_CODE_DIR <- normalizePath(file.path(testthat::test_path(), "..", ".."), winslash = "/", mustWork = TRUE)
for (m in c("sgs_config.R", "sgs_utils.R", "sgs_rng.R", "sgs_load.R", "sgs_panel.R", "sgs_registry.R", "sgs_sample.R",
            "sgs_gates.R", "sgs_estimate.R", "sgs_champions.R", "sgs_report.R", "sgs_summaries.R", "sgs_glassbox.R",
            "sgs_trends.R", "sgs_forecast.R", "sgs_review.R", "sgs_seats.R", "sgs_seats_race.R", "sgs_run.R")) {
  source(file.path(SGS_TEST_CODE_DIR, m), encoding = "UTF-8", local = FALSE)
}

SECTORS <- SGS$STUDY_SECTORS
TRUE_BETA <- c(growth_previous_year_pct = 0.8, pres_year = 1.5, midterm_year = -0.6, exp_dem_house = 2.0,
               exp_dem_senate = -1.0, cur_dem_house = 0.7, cur_dem_senate = -0.4)
L_CONTROLS <- SGS_L_CONTROLS
PARITY <- sgs_rules("python-parity")
PAUL <- sgs_rules("paul-2026-09-25")

national <- function(years, seed = 1) {
  set.seed(seed)
  out <- data.frame(year = as.numeric(years))
  out$pres_year <- as.numeric(out$year %% 4 == 0)
  out$midterm_year <- as.numeric(out$year %% 4 == 2)
  out$exp_dem_house <- runif(nrow(out), 0.05, 0.95)
  out$exp_dem_senate <- runif(nrow(out), 0.05, 0.95)
  out$cur_dem_house <- sample(0:1, nrow(out), replace = TRUE)
  out$cur_dem_senate <- sample(0:1, nrow(out), replace = TRUE)
  out$cur_dem_house[1] <- 0; out$cur_dem_house[2] <- 1
  out$cur_dem_senate[1] <- 1; out$cur_dem_senate[2] <- 0
  out
}

# Complete synthetic sector_year table with sector baselines a_i = 5 + 3 i and known coefficients (helpers.py).
sector_year_panel <- function(n_sectors = 6, years = 2014:2025, noise = 0.05, seed = 7, beta = NULL, dv = "contributions_real_m") {
  beta <- if (is.null(beta)) TRUE_BETA else beta
  nat <- national(years, seed + 1)
  set.seed(seed)
  rows <- list()
  for (i in seq_len(n_sectors)) {
    a <- 5.0 + 3.0 * (i - 1)
    for (j in seq_len(nrow(nat))) {
      rec <- list(study_sector = SECTORS[i], year = nat$year[j], partial_year = FALSE,
                  growth_previous_year_pct = rnorm(1, 2, 4), growth_same_year_pct = rnorm(1, 2, 4),
                  predicted_growth_pct = rnorm(1, 2, 3))
      for (c in c("pres_year", "midterm_year", "exp_dem_house", "exp_dem_senate", "cur_dem_house", "cur_dem_senate")) rec[[c]] <- nat[[c]][j]
      y <- a + sum(vapply(names(beta), function(k) beta[[k]] * rec[[k]], 0)) + rnorm(1, 0, noise)
      rec[[dv]] <- y
      rows[[length(rows) + 1L]] <- rec
    }
  }
  df <- do.call(rbind, lapply(rows, as.data.frame, stringsAsFactors = FALSE))
  for (col in c("contributions_real_m", "lobby_income_real_m", "lobby_expenses_real_m")) if (!col %in% names(df)) df[[col]] <- df[[dv]]
  df$exp_shift_house <- df$exp_dem_house - df$cur_dem_house
  df$exp_shift_senate <- df$exp_dem_senate - df$cur_dem_senate
  for (st in c("contributions_status", "lobby_income_status", "lobby_expenses_status", "growth_same_status",
               "growth_prev_status", "predicted_status", "controls_status", "exp_dem_house_status",
               "exp_dem_senate_status", "cur_dem_house_status", "cur_dem_senate_status", "exp_shift_house_status",
               "exp_shift_senate_status")) df[[st]] <- "observed"
  df
}

tspec <- function(...) {
  kw <- list(...)
  base <- list(id = "TEST", family = "C", label = "CORE", dv = "contributions_real_m", focal = "growth_previous_year_pct",
               controls = c("pres_year", "midterm_year", "exp_dem_house", "exp_dem_senate"))
  for (k in names(kw)) base[k] <- list(kw[[k]])
  do.call(sgs_test_spec, base)
}

# ---- synthetic study workbooks (synth_workbooks.build) -----------------------------------------------------------------

.rows_df <- function(rows) {
  if (!length(rows)) return(data.frame())
  cols <- unique(unlist(lapply(rows, names)))
  sgs_rows_df(rows, cols)
}

synth_build <- function(folder, seed = 5, years = 2006:2026, sectors = c("commercial_banks", "credit_unions", "crypto",
                        "credit_arms", "property_casualty"), slope = 0.3, lobbyview = TRUE, contrib_years = NULL,
                        extra_units = character(0), iem_last_year = NULL, expected_control = NULL, markets = NULL,
                        extra_sheets = list(), company_pac_share = 0) {
  dir.create(folder, recursive = TRUE, showWarnings = FALSE)
  set.seed(seed)
  ys <- years
  ctl <- data.frame(year = ys, presidential_year = as.numeric(ys %% 4 == 0), midterm_year = as.numeric(ys %% 4 == 2),
                    status = ifelse(ys == 2026, "missing", "observed"), stringsAsFactors = FALSE)
  exp_ <- lapply(ys, function(y) runif(2, 0.1, 0.9)); names(exp_) <- ys
  cur <- lapply(ys, function(y) sample(0:1, 2, replace = TRUE)); names(cur) <- ys
  e_rows <- list(); c_rows <- list(); s_rows <- list()
  for (y in ys) for (j in 1:2) {
    ch <- c("House", "Senate")[j]
    blank <- !is.null(iem_last_year) && y > iem_last_year
    e_rows[[length(e_rows) + 1L]] <- list(calendar_year = y, chamber = ch, p_dem_expected = if (blank) NA else exp_[[as.character(y)]][j],
                                          status = if (blank) "missing" else "observed")
    c_rows[[length(c_rows) + 1L]] <- list(calendar_year = y, chamber = ch, dem_control = cur[[as.character(y)]][j], status = "observed")
    if (y %% 2 == 0) s_rows[[length(s_rows) + 1L]] <- list(chamber = ch, election_year = y,
                                                          pred_dem_net_change = as.numeric(sample(-20:19, 1)), status = "observed")
  }
  g_rows <- list(); p_rows <- list(); d_rows <- list(); sy_rows <- list(); t_rows <- list(); l_rows <- list(); xw <- list()
  lda_map <- c(commercial_banks = "bank", credit_unions = "credit_union", crypto = "crypto", fintech = "fintech")
  for (i in seq_along(SGS$STUDY_SECTORS)) {
    s <- SGS$STUDY_SECTORS[i]; i0 <- i - 1
    xw[[length(xw) + 1L]] <- list(study_sector = s, mentat_industry = if (s %in% sectors) s else NA,
                                  lda_lobbying_sector = if (s %in% names(lda_map)) lda_map[[s]] else NA)
    if (!s %in% sectors) next
    growth <- setNames(rnorm(length(ys) + 1, 2, 4), c(ys[1] - 1, ys))
    for (y in ys) {
      gy <- growth[[as.character(y)]]; gp <- growth[[as.character(y - 1)]]
      g_rows[[length(g_rows) + 1L]] <- list(sector = s, study_sector = s, year = y, growth_same_year_pct = gy,
                                            growth_previous_year_pct = gp, status = "observed")
      p_rows[[length(p_rows) + 1L]] <- list(sector = s, study_sector = s, year = y, predicted_growth_pct = rnorm(1, 2, 3),
                                            forecast_publication_month = paste0(y - 1, "-11"), forecast_age_months = 2, status = "observed")
      pres <- ctl$presidential_year[ctl$year == y]
      total <- 5 + 2 * i0 + slope * gp + 1.0 * pres + rnorm(1, 0, 0.2)
      part <- y == 2026
      parts <- c(0.6 * total, 0.4 * total)
      if (!is.null(contrib_years) && !part && !(y %in% contrib_years)) {
        sy_rows[[length(sy_rows) + 1L]] <- list(study_sector = s, year = y, giving_real_2025_usd = NA, status = "missing")
        parts <- NULL
      }
      if (!is.null(parts)) {
        for (k in 1:2) {
          comp <- c("Co A", "Co B")[k]
          share_pac <- if (company_pac_share > 0) company_pac_share else 0
          d_rows[[length(d_rows) + 1L]] <- list(year = y, study_sector = s, company = comp, recipient_category = "Candidate",
                                                party = "D", funding_source = "employee_original",
                                                giving_real_2025_usd = if (part) NA else parts[k] * (1 - share_pac) * 1e6,
                                                giving_nominal_usd = if (part) 1 else parts[k] * (1 - share_pac) * 1e6,
                                                status = if (part) "partial" else "observed")
          if (share_pac > 0) {
            d_rows[[length(d_rows) + 1L]] <- list(year = y, study_sector = s, company = comp, recipient_category = "Company PAC",
                                                  party = "Other / Unclassified", funding_source = "employee_original",
                                                  giving_real_2025_usd = if (part) NA else parts[k] * share_pac * 1e6,
                                                  giving_nominal_usd = if (part) 1 else parts[k] * share_pac * 1e6,
                                                  status = if (part) "partial" else "observed")
          }
          for (ti in seq_along(SGS$TIERS)) {
            share <- c(0.1, 0.2, 0.6, 0.1)[ti]
            t_rows[[length(t_rows) + 1L]] <- list(year = y, study_sector = s, company = comp, employee_tier = SGS$TIERS[ti],
                                                  giving_real_2025_usd = if (part) NA else parts[k] * share * 1e6, gifts = 3,
                                                  status = if (part) "partial" else "observed")
          }
        }
        sy_rows[[length(sy_rows) + 1L]] <- list(study_sector = s, year = y, giving_real_2025_usd = if (part) NA else total * 1e6,
                                                status = if (part) "partial" else "observed")
      }
      if (s %in% names(lda_map)) {
        l_rows[[length(l_rows) + 1L]] <- list(source = "lda_rebuild", sector = lda_map[[s]], confidence = NA, year = y, period = "annual",
                                              lobby_income_real_2025_usd = if (part) NA else (3 + i0 + 0.2 * gp) * 1e6,
                                              lobby_expenses_real_2025_usd = if (part) NA else (6 + i0 - 0.1 * gp) * 1e6,
                                              lobby_amount_undifferentiated_real_2025_usd = NA,
                                              status = if (part) "partial" else "observed")
      }
      if (lobbyview && s %in% c("commercial_banks", "credit_unions") && y <= 2024) {
        l_rows[[length(l_rows) + 1L]] <- list(source = "lobbyview_adversary_spend", sector = lda_map[[s]], confidence = "high",
                                              year = y, period = "annual", lobby_income_real_2025_usd = NA,
                                              lobby_expenses_real_2025_usd = NA,
                                              lobby_amount_undifferentiated_real_2025_usd = (20 + 5 * i0 + 0.5 * gp + rnorm(1, 0, 0.1)) * 1e6,
                                              status = if (y == 2024) "partial" else "observed")
      }
    }
  }
  for (u in extra_units) {
    xw[[length(xw) + 1L]] <- list(study_sector = u, mentat_industry = u, lda_lobbying_sector = NA)
    for (y in ys) {
      part <- y == 2026
      has <- part || is.null(contrib_years) || y %in% contrib_years
      total <- 3 + 1.0 * ctl$presidential_year[ctl$year == y] + rnorm(1, 0, 0.2)
      if (has && !part) {
        d_rows[[length(d_rows) + 1L]] <- list(year = y, study_sector = u, company = "Co U", recipient_category = "Candidate",
                                              party = "D", funding_source = "employee_original", giving_real_2025_usd = total * 1e6,
                                              status = "observed")
      }
      sy_rows[[length(sy_rows) + 1L]] <- list(study_sector = u, year = y, giving_real_2025_usd = if (has && !part) total * 1e6 else NA,
                                              status = if (part) "partial" else (if (has) "observed" else "missing"))
    }
  }
  sgs_write_xlsx(file.path(folder, "00_controls.xlsx"), list(data = ctl))
  sheets01 <- list(data = .rows_df(l_rows))
  if (!is.null(extra_sheets$lobbying)) sheets01 <- c(sheets01, extra_sheets$lobbying)
  sgs_write_xlsx(file.path(folder, "01_lobbying_expenditures.xlsx"), sheets01)
  e_sheets <- list(data = .rows_df(e_rows), seat_calls = .rows_df(s_rows))
  if (!is.null(expected_control)) e_sheets$expected_control_2023_2026 <- expected_control
  if (!is.null(markets)) e_sheets$expected_control_markets <- markets
  if (!is.null(extra_sheets$election)) e_sheets <- c(e_sheets, extra_sheets$election)
  sgs_write_xlsx(file.path(folder, "02_election_forecasting.xlsx"), e_sheets)
  sgs_write_xlsx(file.path(folder, "03_actual_seat_gain.xlsx"), list(current_control = .rows_df(c_rows)))
  sgs_write_xlsx(file.path(folder, "04_campaign_spending.xlsx"), list(data = .rows_df(d_rows), sector_year = .rows_df(sy_rows),
                                                                      tier_by_year = .rows_df(t_rows)))
  sheets06 <- list(data = .rows_df(p_rows))
  if (!is.null(extra_sheets$predicted)) sheets06 <- c(sheets06, extra_sheets$predicted)
  sgs_write_xlsx(file.path(folder, "06_predicted_industry_growth.xlsx"), sheets06)
  sgs_write_xlsx(file.path(folder, "07_actual_industry_growth.xlsx"), list(data = .rows_df(g_rows)))
  sgs_write_xlsx(file.path(folder, "sector_crosswalk.xlsx"), list(data = .rows_df(xw)))
  if (!is.null(extra_sheets$chamber)) sgs_write_xlsx(file.path(folder, SGS$CHAMBER_FILE), extra_sheets$chamber)
  folder
}

expected_control_sheet <- function(house = c(1, 1, 0.9144, 0.9144), senate = c(0, 0, 0.6386, 0.6386)) {
  rows <- list()
  for (ch in c("House", "Senate")) {
    vals <- if (ch == "House") house else senate
    for (k in 1:4) {
      y <- 2022 + k
      final <- y <= 2024
      rows[[length(rows) + 1L]] <- list(calendar_year = y, chamber = ch, election_targeted = if (final) 2024 else 2026,
                                        exp_dem = vals[k], method = if (final) "forecaster_final_call_binary" else "market_snapshot",
                                        measured_on = if (final) "2024-11-04" else "2026-09-24/25",
                                        flag = c("2023" = "measured Nov 2024, after the year", "2025" = "measured Sep 2026, after the year")[as.character(y)],
                                        status = "observed",
                                        source_id = if (final) (if (ch == "House") "hsc_predicted_house" else "hsc_predicted_senate")
                                                    else "hsc_current_2026_control_probabilities")
    }
  }
  df <- .rows_df(rows)
  df$flag <- unname(df$flag)
  df
}

markets_frame <- function() {
  rows <- list()
  add <- function(date, year, ch, market, p_dem = NA, p_rep = NA, before = 1, status = "observed") {
    rows[[length(rows) + 1L]] <<- list(date = date, calendar_year = year, chamber = ch, market = market, p_dem_control = p_dem,
                                       p_rep_control = p_rep, before_election_day = before, status = status)
  }
  add("2023-03-01", 2023, "House", "kalshi", p_dem = 0.40)
  add("2023-03-01", 2023, "House", "polymarket", p_dem = 0.44)
  add("2023-09-01", 2023, "House", "kalshi", p_dem = 0.48)
  add("2024-06-01", 2024, "House", "kalshi", p_dem = 0.50)
  add("2024-11-10", 2024, "House", "kalshi", p_dem = 0.99, before = 0)
  add("2025-05-01", 2025, "House", "kalshi", p_dem = 0.70)
  add("2026-01-15", 2025, "House", "kalshi", p_dem = 0.80)
  add("2023-03-01", 2023, "Senate", "kalshi", p_rep = 0.70)
  add("2023-06-01", 2023, "Senate", "polymarket", p_rep = 0.60)
  add("2024-06-01", 2024, "Senate", "kalshi", p_rep = 0.75, status = "missing")
  add("2021-06-01", 2021, "House", "kalshi", p_dem = 0.01)
  .rows_df(rows)
}

# ---- synthetic 05 (champions) ---------------------------------------------------------------------------------------

champions_frame <- function(n_members = 40, cycles = c(2020, 2022, 2024, 2026), boards = c("bank", "credit_union", "crypto"),
                            slope = 5000.0, member_corr = 0.0, noise = 0.0, seed = 3, primary_dv = FALSE, trade = FALSE) {
  set.seed(seed)
  rows <- list()
  b_eff <- setNames(1000 * seq_along(boards), boards)
  c_eff <- setNames(300 * (seq_along(cycles) - 1), cycles)
  tvals <- c(0, 1 / 3, 2 / 3, 1, 5 / 3, 2, 7 / 3, 3)
  for (m in 0:(n_members - 1)) {
    bio <- sprintf("M%06d", m)
    my_boards <- c(boards[(m %% length(boards)) + 1], if (m %% 3 == 0 && length(boards) > 1) boards[((m + 1) %% length(boards)) + 1])
    chamber <- if (m %% 4 == 0) "Senate" else "House"
    party <- if (m == 5) "I" else if (m %% 2 == 1) "D" else "R"
    sen0 <- as.numeric(sample(0:19, 1))
    tough <- setNames(tvals[sample.int(8, length(cycles), replace = TRUE)], cycles)
    mean_t <- mean(tough[as.character(cycles[-1])])
    m_eff <- member_corr * 20000 * mean_t + rnorm(1, 0, if (member_corr != 0) 500 else 0)
    for (b in my_boards) for (cy in cycles) {
      up <- if (m %% 11 == 0 && cy == 2024) 0 else 1
      lost <- if (m == 7 && cy == 2026) 1 else if (up == 1) 0 else NA
      sen <- sen0 + (cy - cycles[1])
      dv <- b_eff[[b]] + c_eff[[as.character(cy)]] + m_eff + slope * tough[[as.character(cy)]] + 800 * (chamber == "Senate") +
        150 * (party == "D") + 40 * sen + rnorm(1, 0, noise)
      missing <- cy == 2020
      row <- list(board = b, rank = m + 1, bioguide = bio, name = paste0("Member ", m), cycle = cy,
                  status = if (missing) "missing" else if (cy == 2026) "partial" else "observed", chamber = chamber, party = party,
                  up_for_election = up, retiring = if (up == 1) 0 else NA, lost_primary = lost, seniority_years = sen,
                  toughness_general = if (up == 0 || isTRUE(lost == 1)) NA else tough[[as.character(cy)]],
                  direct_giving_status = if (missing) "missing" else "observed",
                  direct_giving_real_2025_usd = if (missing) NA else dv,
                  primary_contested = if (cy %in% c(2020, 2022) && up == 1) as.numeric(sample(0:1, 1)) else NA,
                  primary_margin = if (cy %in% c(2020, 2022) && up == 1) runif(1) else NA,
                  general_margin = if (cy %in% c(2020, 2022, 2024) && up == 1 && !isTRUE(lost == 1)) runif(1) else NA)
      if (primary_dv) row$industry_money_primary_real_2025_usd <- if (missing) NA else dv + 1.0
      if (trade) row$industry_money_with_trade_real_2025_usd <- if (missing) NA else dv * 1.1
      rows[[length(rows) + 1L]] <- row
    }
  }
  .rows_df(rows)
}

champions_data_from <- function(frame) list(ok = TRUE, reason = "", frame = frame, source = list(), notes = character(0),
                                            documented = names(frame))

write_champions <- function(data_dir, frame, age_minutes = 30, receipt_sha = NULL, write_receipt = TRUE, allow_formulas = FALSE) {
  dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)
  path <- file.path(data_dir, SGS$CHAMPIONS_FILE)
  dic <- data.frame(sheet = "data", column = names(frame), type = "text", unit = NA_character_,
                    definition = paste0("synthetic ", names(frame)), stringsAsFactors = FALSE)
  sgs_write_xlsx(path, list(data = frame, dictionary = dic), allow_formulas = allow_formulas)
  sha <- sgs_sha256_file(path)
  rpath <- file.path(dirname(normalizePath(data_dir, winslash = "/")), SGS$CHAMPIONS_RECEIPT)
  if (write_receipt) {
    writeLines(as.character(jsonlite::toJSON(list(run_id = "synthetic-05", written_at = "synthetic",
                                                  target = list(path = path, sha256 = receipt_sha %||% sha)), auto_unbox = TRUE)), rpath)
  }
  t <- Sys.time() - age_minutes * 60
  Sys.setFileTime(path, t)
  if (write_receipt) Sys.setFileTime(rpath, t)
  list(path = path, receipt = rpath)
}

tmp_dir <- function() {
  d <- tempfile("sgstest")
  dir.create(d, recursive = TRUE)
  d
}

quiet_run <- function(...) sgs_run(..., log = function(...) NULL)
