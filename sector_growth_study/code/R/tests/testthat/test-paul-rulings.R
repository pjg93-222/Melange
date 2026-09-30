# R port only: Paul's rulings of 2026-09-25 night (rule set paul-2026-09-25), on synthetic workbooks.

lv_all_sheet <- function(dedup = TRUE, years = 2006:2024) {
  set.seed(71)
  conf <- c(commercial_banks = "high", credit_unions = "high", crypto = "roster", credit_arms = "naics",
            property_casualty = "naics")
  rows <- list()
  for (s in names(conf)) for (y in years) {
    amount <- (10 + 3 * match(s, names(conf)) + rnorm(1, 0, 0.5)) * 1e6
    thin <- s == "credit_arms" || (s == "crypto" && y < 2015)
    cov <- paste(c(if (y == 2024) "partial_year", if (thin) "thin"), collapse = ";")
    if (!nzchar(cov)) cov <- "ok"
    row <- list(source = "lobbyview", sector = s, confidence = conf[[s]], year = y, period = "annual",
                lobby_amount_undifferentiated_real_2025_usd = amount, status = if (y == 2024) "partial" else "observed",
                study_sector = s, coverage_flag = cov)
    if (dedup) { row$lobby_amount_dedup_real_2025_usd <- 0.8 * amount; row$dedup_ratio <- 0.8 }
    rows[[length(rows) + 1L]] <- row
    if (s == "commercial_banks") {
      low <- row; low$confidence <- "low"; low$lobby_amount_undifferentiated_real_2025_usd <- 9e9
      if (dedup) low$lobby_amount_dedup_real_2025_usd <- 9e9
      rows[[length(rows) + 1L]] <- low
    }
  }
  .rows_df(rows)
}

sheet538 <- function() {
  rows <- lapply(2008:2026, function(y) list(year = y, chamber = "House", series = "generic_ballot_margin",
                                             value = if (y <= 2024) (y - 2015) / 2 + sin(y) else NA, n_days = 300, method = "within"))
  rows[[length(rows) + 1L]] <- list(year = 2018, chamber = "House", series = "house_control_lite", value = 0.9, n_days = 150,
                                    method = "within")
  .rows_df(rows)
}

multiyear_sheets <- function() {
  supp <- data.frame(observation_id = c("cr_a", "cr_b", "cr_c", "cr_d", "auto_x"),
                     sector = c("crypto", "crypto", "crypto", "crypto", "auto"),
                     study_sector = c("crypto", "crypto", "crypto", "crypto", "auto_manufacturing"),
                     known_available_by = c("2022-11-04", "2023-04-24", "2023-07-29", NA, NA),
                     publication_date_or_month = c(NA, NA, NA, "2024-02", "2011-10"),
                     growth_measure = c("multiyear CAGR; CAGR 2022-2030", "multiyear CAGR; CAGR 2023-2030",
                                        "multiyear CAGR; CAGR 2023-2027", "annual revenue growth",
                                        "annual revenue growth forecast made 2-5 years ahead"),
                     growth_pct = c(28.3, 12, 15.19, 3, 7.9), label = "separate; not comparable annual inputs",
                     status = "observed", stringsAsFactors = FALSE)
  comp <- data.frame(record_source = c("fintech_broad_multiyear", "fintech_broad_multiyear", "fintech_component", "telecom_component_selected"),
                     record_key = c(NA, NA, NA, "51721:2009"), study_sector = c("Fintech", "Fintech", "Fintech", "Telecom"),
                     observation_id = c("ft_a", "ft_b", "ft_c", NA), provider = c("BlueWeave", "BCG", "Statista", NA),
                     known_available_by = c("2021-12-28", "2023-06-02", "2024-02-26", NA),
                     forecast_period_start = c(2021, 2021, NA, NA), forecast_period_end = c(2027, 2030, NA, NA),
                     published_cagr_pct = c(10.1, 17, NA, NA), published_growth_pct = c(NA, NA, 17.98, NA),
                     forecast_target_year = c(NA, NA, 2025, NA), metric_status = c(NA, NA, "component", NA),
                     predicted_growth_pct = c(NA, NA, NA, 3.7), publication_date = c(NA, NA, NA, "2008-09-18"),
                     label = "component or multi-year; not the broad annual column", status = "observed", stringsAsFactors = FALSE)
  list(supplemental_observations = supp, component_forecasts = comp)
}

chamber_book <- function(split_hill = FALSE) {
  set.seed(81)
  rows <- list(); orr <- list()
  for (s in c("commercial_banks", "credit_unions", "crypto", "credit_arms", "property_casualty")) for (y in 2019:2026) {
    for (ch in c("House", "Senate")) {
      dem <- runif(1, 1e5, 9e5); rep <- runif(1, 1e5, 9e5)
      rows[[length(rows) + 1L]] <- list(study_sector = s, year = y, chamber = ch, dem_usd = dem, rep_usd = rep, other_usd = 100,
                                        dem_real_m = dem / 1e6, rep_real_m = rep / 1e6, dem_share = dem / (dem + rep), n_rows = 50,
                                        status = if (y == 2026) "partial" else "observed")
    }
    o <- list(study_sector = s, year = y, not_house_senate_usd = 5e6, of_which_hill_committees_usd = 4e5,
              status = if (y == 2026) "partial" else "observed")
    if (split_hill) { o$of_which_dccc_usd <- 1e5; o$of_which_nrcc_usd <- 1e5; o$of_which_dscc_usd <- 1e5; o$of_which_nrsc_usd <- 1e5 }
    orr[[length(orr) + 1L]] <- o
  }
  list(sector_year_chamber = .rows_df(rows), other_recipients = .rows_df(orr))
}

paul_build <- function(folder, dedup = TRUE, with_lv = TRUE, with_538 = TRUE, with_08 = TRUE, split_hill = FALSE, markets = TRUE) {
  extra <- list(predicted = multiyear_sheets())
  if (with_lv) extra$lobbying <- setNames(list(lv_all_sheet(dedup)), SGS$LOBBYVIEW_ALL_SHEET)
  if (with_538) extra$election <- setNames(list(sheet538()), SGS$EXPECTED_CONTROL_538_SHEET)
  if (with_08) extra$chamber <- chamber_book(split_hill)
  synth_build(folder, expected_control = expected_control_sheet(), markets = if (markets) markets_frame() else NULL,
              iem_last_year = 2022, extra_sheets = extra, company_pac_share = 0.25)
}

paul_env <- local({
  base <- tmp_dir()
  data <- paul_build(file.path(base, "data"))
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "results"), B = 199, run_id = "analysis-test-paul", rules = PAUL)
  list(data = data, out = out, rows = setNames(out$est_rows, vapply(out$est_rows, `[[`, "", "test_id")))
})

test_that("Paul registry: DS stubs replaced, new families added, every Python test id otherwise kept", {
  rp <- sgs_registry(PAUL); rq <- sgs_registry(PARITY)
  expect_equal(length(rp), 373)  # 171 of 2026-09-25, the 51 tests of the rulings of 2026-09-26 (test-extensions-0926.R), the 90 SHIFT tests (test-shift-trends-forecast.R), the 33 revision tests (test-review-0926.R) and the 28 SEATS-A tests (test-seats-0926.R)
  expect_false(any(c("DS-House", "DS-Senate") %in% names(rp)))
  expect_true(all(setdiff(names(rq), c("DS-House", "DS-Senate")) %in% names(rp)))
  for (id in c(paste0("DS-", rep(c("House", "Senate"), each = 3), "-C", 1:3), paste0("H4-538-", c("C1", "L3-expenses")),
               paste0("R-dedup-C", 1:3), paste0("R-LV-", c("undiff", "thin"), "-L1"), "MY-C3", "MY-L3-LV", "DS+Hill-House-C1")) {
    expect_true(id %in% names(rp), info = id)
  }
  expect_false(anyDuplicated(names(rp)) > 0)
})

test_that("ruling 1: 2023-2026 from expected_control_2023_2026 (2023 filled); the markets sheet is never read", {
  sy <- paul_env$out$tables$sector_year
  v <- function(y, c) sy[[c]][sy$study_sector == "commercial_banks" & sy$year == y]
  expect_equal(v(2023, "exp_dem_house"), 1.0)
  expect_equal(v(2023, "exp_dem_house_method"), "forecaster_final_call_binary")
  expect_equal(v(2023, "exp_dem_house_flag"), "measured Nov 2024, after the year")
  expect_equal(v(2025, "exp_dem_house"), 0.9144, tolerance = 1e-9)
  expect_equal(v(2021, "exp_dem_house_method"), "iem_annual_mean")
  # an invalid markets sheet does not even fail the load: the sheet is not parsed
  bad <- markets_frame(); bad$market <- NULL
  d2 <- synth_build(tmp_dir(), iem_last_year = 2022, markets = bad, expected_control = expected_control_sheet())
  wbs <- sgs_load_all(d2, PAUL)
  expect_false(SGS$EXPECTED_CONTROL_MARKETS_SHEET %in% names(wbs$election$frames))
  expect_true(SGS$EXPECTED_CONTROL_MARKETS_SHEET %in% wbs$election$sheets_present)
  # the fill sheet decides 2023-2026 even where IEM has a value
  d3 <- synth_build(tmp_dir(), expected_control = expected_control_sheet())
  ec <- sgs_expected_control(sgs_load_all(d3, PAUL), PAUL)
  expect_equal(ec$exp_dem[ec$year == 2023 & ec$chamber == "House"], 1.0)
  expect_equal(ec$method[ec$year == 2021 & ec$chamber == "House"], "iem_annual_mean")
})

test_that("ruling 1: H4-538 uses the 538 generic-ballot margin in place of exp_dem_house; forecast rows ignored", {
  sy <- paul_env$out$tables$sector_year
  s538 <- sheet538()
  m <- s538[s538$series == "generic_ballot_margin", ]
  b <- sy[sy$study_sector == "commercial_banks", ]
  expect_equal(b$gb538_margin_house[match(2008:2024, b$year)], m$value[match(2008:2024, m$year)])
  expect_true(all(is.na(b$gb538_margin_house[b$year %in% c(2025, 2026)])))
  r <- paul_env$rows[["H4-538-C1"]]
  expect_true(r$status %in% c(SGS_ESTIMABLE, SGS_NOT_ESTIMABLE))
  expect_false("exp_dem_house" %in% strsplit(r$controls, ", ")[[1]])
  expect_true(grepl("gb538_margin_house", r$focal, fixed = TRUE))
  d2 <- paul_build(file.path(tmp_dir(), "data"), with_538 = FALSE)
  out2 <- quiet_run(data_dir = d2, results_dir = file.path(tmp_dir(), "r"), B = 99, only = "H4-538", rules = PAUL)
  expect_true(all(vapply(out2$est_rows, function(r) r$status == SGS_NOT_BUILT, TRUE)))
  expect_match(out2$est_rows[[1]]$reason, "expected_control_538 not present", fixed = TRUE)
})

test_that("ruling 2: LobbyView every sector and year, confidence other than low, thin excluded, dedup primary, bootstrap", {
  sy <- paul_env$out$tables$sector_year
  lv <- lv_all_sheet(TRUE)
  hi <- lv[lv$study_sector == "commercial_banks" & lv$confidence == "high" & lv$year == 2010, ]
  expect_equal(sy$lobby_lv_real_m[sy$study_sector == "commercial_banks" & sy$year == 2010], hi$lobby_amount_dedup_real_2025_usd / 1e6)
  expect_equal(sy$lobby_amount_undiff_real_m[sy$study_sector == "commercial_banks" & sy$year == 2010],
               hi$lobby_amount_undifferentiated_real_2025_usd / 1e6)
  expect_true(all(sy$lobby_lv_status[sy$study_sector == "credit_arms" & sy$year <= 2023] == "thin"))
  expect_equal(sy$lobby_lv_status[sy$study_sector == "crypto" & sy$year == 2014], "thin")
  expect_equal(sy$lobby_lv_status[sy$study_sector == "crypto" & sy$year == 2016], "observed")
  expect_equal(sy$lobby_lv_status[sy$study_sector == "commercial_banks" & sy$year == 2024], "partial")
  r <- paul_env$rows[["L1-LV"]]
  expect_equal(r$status, SGS_ESTIMABLE)
  expect_equal(c(r$label, r$window_used, r$window_kind), c("CORE", "2008-2023", "fallback"))
  expect_equal(r$sectors, "commercial_banks, credit_unions, crypto, property_casualty")
  expect_match(r$fallback_search, "window used: the whole run, 2008-2023", fixed = TRUE)
  expect_match(r$dv_label, "de-duplicated", fixed = TRUE)
  c1 <- Filter(function(c) c$test_id == "L1-LV", paul_env$out$coef_rows)[[1]]
  expect_equal(c(c1$boot_draws, c1$boot_enumerated), c(199, FALSE))  # B = 199 < 6^4: random draws (inference, not DESCRIPTIVE)
  expect_false(is.na(c1$boot_p))
  expect_equal(c1$inference, "wild cluster restricted bootstrap by sector")
  expect_equal(paul_env$rows[["R-LV-thin-L1"]]$sectors, "commercial_banks, credit_unions, crypto, credit_arms, property_casualty")
  expect_equal(paul_env$rows[["R-LV-undiff-L1"]]$status, SGS_ESTIMABLE)
  # dedup pending: undifferentiated amount labelled, the undifferentiated robustness NOT BUILT
  d2 <- paul_build(file.path(tmp_dir(), "data"), dedup = FALSE)
  out2 <- quiet_run(data_dir = d2, results_dir = file.path(tmp_dir(), "r"), B = 99, only = c("L1-LV", "R-LV-undiff-L1"), rules = PAUL)
  rr <- setNames(out2$est_rows, vapply(out2$est_rows, `[[`, "", "test_id"))
  expect_match(rr[["L1-LV"]]$dv_label, "undifferentiated, dedup pending", fixed = TRUE)
  expect_equal(rr[["R-LV-undiff-L1"]]$status, SGS_NOT_BUILT)
  # no sheet: NOT BUILT
  d3 <- paul_build(file.path(tmp_dir(), "data"), with_lv = FALSE)
  out3 <- quiet_run(data_dir = d3, results_dir = file.path(tmp_dir(), "r"), B = 99, only = "L1-LV", rules = PAUL)
  expect_equal(out3$est_rows[[1]]$status, SGS_NOT_BUILT)
  expect_match(out3$est_rows[[1]]$reason, "lobbyview_sector_year_all not present", fixed = TRUE)
})

test_that("ruling 2: two sector clusters make a LobbyView test DESCRIPTIVE; three run the bootstrap", {
  df <- sector_year_panel(n_sectors = 2, years = 2008:2025, dv = "lobby_lv_real_m")
  df$lobby_lv_status <- "observed"
  sp <- sgs_registry(PAUL)[["L1-LV"]]
  d <- sgs_decide(sp, list(sector_year = df), built = list(lobbyview_all = list(built = TRUE)))
  res <- sgs_estimate(sp, sgs_decision_chosen(d), B = 99)
  expect_true(res$descriptive)
  df3 <- sector_year_panel(n_sectors = 3, years = 2008:2025, dv = "lobby_lv_real_m")
  df3$lobby_lv_status <- "observed"
  d3 <- sgs_decide(sp, list(sector_year = df3), built = list(lobbyview_all = list(built = TRUE)))
  res3 <- sgs_estimate(sp, sgs_decision_chosen(d3), B = 9999)
  expect_false(res3$descriptive)
  expect_equal(res3$coefs[[1]]$boot_draws, 6^3)  # 6^3 <= B: every weight vector enumerated
  expect_true(res3$coefs[[1]]$boot_enumerated)
})

test_that("ruling 4: PAC overlap share and the de-duplicated DV drop gifts to the roster company's own PAC", {
  sy <- paul_env$out$tables$sector_year
  b <- sy[sy$study_sector == "commercial_banks" & sy$year == 2015, ]
  expect_equal(b$contributions_dedup_real_m, 0.75 * b$contributions_real_m, tolerance = 1e-12)
  expect_equal(b$company_pac_share, 0.25, tolerance = 1e-12)
  pac <- paul_env$out$sheets$pac_overlap
  expect_true(all(abs(pac$company_pac_share_nominal[pac$is_study_sector & pac$year < 2026] - 0.25) < 1e-12))
  r <- paul_env$rows[["R-dedup-C1"]]
  expect_equal(r$status, SGS_ESTIMABLE)
  c1 <- Filter(function(c) c$test_id == "R-dedup-C1", paul_env$out$coef_rows)[[1]]
  expect_lt(abs(c1$estimate - 0.75 * 0.3), 0.05)
})

test_that("ruling 5: every growth test carries the population note; tests without growth do not", {
  note <- SGS$POPULATION_NOTE
  expect_match(paul_env$rows[["C1"]]$flag, note, fixed = TRUE)
  expect_match(paul_env$rows[["MY-C3"]]$flag, note, fixed = TRUE)
  expect_match(paul_env$rows[["C1-PV-reduced"]]$flag, note, fixed = TRUE)
  expect_false(grepl(note, paul_env$rows[["H1-phase-contributions"]]$flag, fixed = TRUE))
  expect_false(grepl(note, paul_env$rows[["H5-pooled"]]$flag, fixed = TRUE))
  md <- paste(readLines(paul_env$out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, note, fixed = TRUE)
})

test_that("ruling 6: compliant (i) places each multi-year CAGR in the spending year after publication (latest wins)", {
  reg <- paul_env$out$built$multiyear$register
  use <- reg[reg$use == "yes", ]
  expect_setequal(paste(use$study_sector, use$spending_year, use$record),
                  c("crypto 2023 cr_a", "crypto 2024 cr_c", "fintech 2022 ft_a", "fintech 2024 ft_b"))
  expect_match(reg$why[reg$record %in% "cr_b"], "superseded by the later projection cr_c", fixed = TRUE)
  expect_equal(reg$why[reg$record %in% "cr_d"], "not a multi-year CAGR")
  expect_equal(reg$why[reg$record %in% "ft_c"], "not a multi-year CAGR")
  expect_equal(reg$why[reg$record %in% "auto_x"], "not a crypto or fintech projection")
  expect_equal(unique(reg$study_sector[reg$study_sector_raw %in% "Fintech"]), "fintech")  # ruling 8: label normalised
  sy <- paul_env$out$tables$sector_year
  expect_equal(sy$predicted_growth_multiyear_pct[sy$study_sector == "crypto" & sy$year == 2024], 15.19)
  expect_true(is.na(sy$predicted_growth_multiyear_pct[sy$study_sector == "crypto" & sy$year == 2025]))
  expect_equal(paul_env$rows[["MY-C3"]]$status, SGS_NOT_ESTIMABLE)  # 4 observations: too few
  expect_match(paul_env$rows[["MY-C3"]]$flag, "compliant (i)", fixed = TRUE)
})

test_that("ruling 7: DS-House / DS-Senate from 08 with n and dollar base; DS+Hill needs the split Hill committees", {
  r <- paul_env$rows[["DS-House-C1"]]
  expect_equal(r$status, SGS_ESTIMABLE)
  expect_match(r$note, "Dollar base (", fixed = TRUE)
  expect_match(r$note, "D + R to House candidate committees $", fixed = TRUE)
  expect_equal(r$dv, "dem_share_house")
  sy <- paul_env$out$tables$sector_year
  cb <- chamber_book()$sector_year_chamber
  x <- cb[cb$study_sector == "crypto" & cb$year == 2022 & cb$chamber == "Senate", ]
  expect_equal(sy$dem_share_senate[sy$study_sector == "crypto" & sy$year == 2022], x$dem_share)
  expect_equal(paul_env$rows[["DS+Hill-House-C1"]]$status, SGS_NOT_BUILT)
  expect_match(paul_env$rows[["DS+Hill-House-C1"]]$reason, "one combined total per sector-year", fixed = TRUE)
  d2 <- paul_build(file.path(tmp_dir(), "data"), split_hill = TRUE)
  out2 <- quiet_run(data_dir = d2, results_dir = file.path(tmp_dir(), "r"), B = 99, only = "DS+Hill-House-C1", rules = PAUL)
  expect_true(out2$est_rows[[1]]$status %in% c(SGS_ESTIMABLE, SGS_NOT_ESTIMABLE))
  d3 <- paul_build(file.path(tmp_dir(), "data"), with_08 = FALSE)
  out3 <- quiet_run(data_dir = d3, results_dir = file.path(tmp_dir(), "r"), B = 99, only = "DS-House-C1", rules = PAUL)
  expect_equal(out3$est_rows[[1]]$status, SGS_NOT_BUILT)
  expect_match(out3$est_rows[[1]]$reason, "08_contributions_by_chamber.xlsx not present", fixed = TRUE)
})

test_that("outputs: engine R receipt, run sheet, rerun command, extra sheets; nothing is overwritten", {
  out <- paul_env$out
  sheets <- readxl::excel_sheets(out$xlsx)
  for (s in c("pac_overlap", "multiyear_register", "run", "dictionary", "sources")) expect_true(s %in% sheets, info = s)
  src <- readxl::read_excel(out$xlsx, sheet = "sources")
  expect_true(all(startsWith(src$engine, "R ")))
  rc <- jsonlite::fromJSON(out$receipt)
  expect_true(startsWith(rc$engine, "R "))
  expect_equal(rc$ruleset, "paul-2026-09-25")
  expect_equal(nrow(rc$inputs), length(out$sources))
  md <- paste(readLines(out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, "## Rerun", fixed = TRUE)
  expect_match(md, "Rscript.exe", fixed = TRUE)
  expect_match(md, "538's historical file (generic_topline_historical.csv) was generated in September 2020", fixed = TRUE)
  expect_error(quiet_run(data_dir = paul_env$data, results_dir = dirname(out$xlsx), B = 99, only = "C1", run_id = out$run_id, rules = PAUL),
               "refusing to overwrite")
})
