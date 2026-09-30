# Port of code/tests/test_gates.py: estimability gates (Paul's rule) and the primary-then-flexible-fallback window
# logic, on synthetic panels.

SEARCH <- c(2008, 2025)
tabs <- function(df) list(sector_year = df)

test_that("TestGates.test_passes_with_six_years_and_enough_sectors", {
  df <- sector_year_panel(n_sectors = 4, years = 2020:2025)
  d <- sgs_decide(tspec(), tabs(df), c(2020, 2025), NULL)
  expect_equal(d$status, SGS_ESTIMABLE)
  expect_equal(d$window, c(2020, 2025))
})

test_that("TestGates.test_rejects_fewer_than_six_years", {
  df <- sector_year_panel(n_sectors = 4, years = 2020:2025)
  df$contributions_real_m[df$year == 2020] <- NA
  d <- sgs_decide(tspec(), tabs(df), c(2020, 2025), NULL)
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "5 distinct years (2021-2025) < 6 required", fixed = TRUE)
  expect_match(d$reason, "contributions_real_m: no usable value for any sector in 2020", fixed = TRUE)
})

test_that("TestGates.test_rejects_rank_deficient_national_design", {
  df <- sector_year_panel(n_sectors = 4, years = 2020:2025)
  d <- sgs_decide(tspec(controls = L_CONTROLS), tabs(df), c(2020, 2025), NULL)
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "year-level design not identified: 7 year-level parameters", fixed = TRUE)
  expect_match(d$reason, "on 6 distinct years", fixed = TRUE)
})

test_that("TestGates.test_rejects_collinear_national_regressors_and_names_them", {
  df <- sector_year_panel(n_sectors = 4, years = 2016:2025)
  df$exp_dem_senate <- df$exp_dem_house
  d <- sgs_decide(tspec(), tabs(df), c(2016, 2025), NULL)
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "not identified: exp_dem_senate", fixed = TRUE)
})

test_that("TestGates.test_rejects_fewer_than_two_sectors", {
  df <- sector_year_panel(n_sectors = 3, years = 2020:2025)
  df$growth_previous_year_pct[df$study_sector != df$study_sector[1]] <- NA
  d <- sgs_decide(tspec(), tabs(df), c(2020, 2025), NULL)
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "1 sector(s)", fixed = TRUE)
})

test_that("TestGates.test_rejects_residual_df_below_three", {
  df <- sector_year_panel(n_sectors = 2, years = 2020:2025)
  s2 <- unique(df$study_sector)[2]
  df$contributions_real_m[df$study_sector == s2 & df$year > 2020] <- NA  # n = 7, p = 7
  d <- sgs_decide(tspec(), tabs(df), c(2020, 2025), NULL)
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "residual df 0 < 3", fixed = TRUE)
})

test_that("TestGates.test_partial_year_never_enters", {
  df <- sector_year_panel(n_sectors = 3, years = 2021:2026)
  df$partial_year[df$year == 2026] <- TRUE
  d <- sgs_decide(tspec(), tabs(df), c(2021, 2026), NULL)
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "5 distinct years (2021-2025)", fixed = TRUE)
  df$contributions_status[df$year == 2021] <- "partial"
  d <- sgs_decide(tspec(), tabs(df), c(2021, 2026), NULL)
  expect_match(d$reason, "4 distinct years (2022-2025)", fixed = TRUE)
})

test_that("TestFallback.test_default_window_used_when_it_passes", {
  df <- sector_year_panel(n_sectors = 4, years = 2014:2025)
  d <- sgs_decide(tspec(), tabs(df), c(2020, 2025), SEARCH)
  expect_equal(list(d$status, d$window, d$window_kind, length(d$attempts)), list(SGS_ESTIMABLE, c(2020, 2025), "default", 1L))
  expect_equal(d$fallback_search, "")
})

test_that("TestFallback.test_fallback_used_when_default_fails", {
  df <- sector_year_panel(n_sectors = 4, years = 2014:2025)
  d <- sgs_decide(tspec(controls = L_CONTROLS), tabs(df), c(2020, 2025), SEARCH)
  expect_equal(d$status, SGS_ESTIMABLE)
  expect_equal(list(d$window, d$window_kind, length(d$attempts)), list(c(2016, 2025), "fallback", 2L))
  expect_false(d$attempts[[1]]$ok)
  expect_equal(sgs_decision_chosen(d)$years, as.numeric(2016:2025))
  expect_match(d$fallback_search, "complete-case years in 2008-2025: 2014-2025", fixed = TRUE)
  expect_match(d$fallback_search, "window used: its most recent 10 years, 2016-2025", fixed = TRUE)
})

test_that("TestFallback.test_most_recent_ten_years_of_a_longer_run", {
  df <- sector_year_panel(n_sectors = 3, years = 2006:2025)
  df$exp_dem_house[df$year > 2022] <- NA
  df$exp_dem_house_status[df$year > 2022] <- "missing"
  d <- sgs_decide(tspec(controls = L_CONTROLS), tabs(df), c(2020, 2025), SEARCH)
  expect_equal(list(d$status, d$window, d$window_kind), list(SGS_ESTIMABLE, c(2013, 2022), "fallback"))
  expect_match(d$fallback_search, "complete-case years in 2008-2025: 2008-2022", fixed = TRUE)
  expect_match(d$fallback_search, "most recent run of >= 10: 2008-2022", fixed = TRUE)
  expect_equal(sgs_decision_chosen(d)$years, as.numeric(2013:2022))
})

test_that("TestFallback.test_whole_run_switch", {
  df <- sector_year_panel(n_sectors = 3, years = 2006:2025)
  df$exp_dem_house[df$year > 2022] <- NA
  d <- sgs_decide(tspec(controls = L_CONTROLS), tabs(df), c(2020, 2025), SEARCH, whole_run = TRUE)
  expect_equal(list(d$status, d$window), list(SGS_ESTIMABLE, c(2008, 2022)))
  expect_equal(length(sgs_decision_chosen(d)$years), 15)
})

test_that("TestFallback.test_most_recent_qualifying_run_is_used_not_the_latest_short_run", {
  df <- sector_year_panel(n_sectors = 3, years = 2006:2025)
  df$contributions_real_m[df$year == 2020] <- NA
  d <- sgs_decide(tspec(controls = L_CONTROLS), tabs(df), c(2020, 2025), SEARCH)
  expect_equal(list(d$status, d$window), list(SGS_ESTIMABLE, c(2010, 2019)))
  expect_match(d$fallback_search, "2008-2019 (12 years), 2021-2025 (5 years)", fixed = TRUE)
})

test_that("TestFallback.test_no_run_of_ten_consecutive_years", {
  df <- sector_year_panel(n_sectors = 4, years = 2008:2025)
  df$contributions_real_m[df$year %in% c(2017, 2021)] <- NA
  d <- sgs_decide(tspec(controls = L_CONTROLS), tabs(df), c(2020, 2025), SEARCH)
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_equal(length(d$attempts), 2)
  expect_true(d$attempts[[2]]$is_search)
  expect_match(d$reason, "no run of >= 10 consecutive calendar years", fixed = TRUE)
  expect_match(d$reason, "2008-2016 (9 years), 2018-2020 (3 years), 2022-2025 (4 years)", fixed = TRUE)
  expect_match(sgs_attempt_compact(d$attempts[[2]]), "fallback search 2008-2025", fixed = TRUE)
})

test_that("TestFallback.test_search_span_limits_the_run", {
  df <- sector_year_panel(n_sectors = 3, years = 2000:2019)
  d <- sgs_decide(tspec(controls = L_CONTROLS), tabs(df), c(2020, 2025), SEARCH)
  expect_equal(list(d$status, d$window), list(SGS_ESTIMABLE, c(2010, 2019)))
  expect_match(d$fallback_search, "complete-case years in 2008-2025: 2008-2019", fixed = TRUE)
})

test_that("TestFallback.test_fallback_needs_ten_consecutive_years", {
  df <- sector_year_panel(n_sectors = 4, years = 2018:2025)
  d <- sgs_decide(tspec(controls = L_CONTROLS), tabs(df), c(2020, 2025), SEARCH)
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_equal(length(d$attempts), 2)
  expect_match(d$reason, "complete-case years in 2008-2025: 2018-2025", fixed = TRUE)
  expect_match(d$reason, "no run of >= 10 consecutive calendar years", fixed = TRUE)
  expect_match(d$reason, "default 2020-2025", fixed = TRUE)
})

test_that("TestFallback.test_fallback_can_be_disabled", {
  df <- sector_year_panel(n_sectors = 4, years = 2014:2025)
  d <- sgs_decide(tspec(controls = L_CONTROLS), tabs(df), c(2020, 2025), NULL)
  expect_equal(list(d$status, length(d$attempts)), list(SGS_NOT_ESTIMABLE, 1L))
})

test_that("TestFallback.test_year_runs", {
  expect_equal(sgs_year_runs(c(2012, 2008, 2009, 2010, 2014)), list(2008:2010, 2012L, 2014L))
  expect_equal(sgs_year_runs(numeric(0)), list())
})
