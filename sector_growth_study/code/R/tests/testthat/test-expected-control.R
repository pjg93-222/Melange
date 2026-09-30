# Port of code/tests/test_expected_control.py (the parity rule set): the 02 fill sheet, IEM first, and the precedence
# of a future expected_control_markets sheet for 2023-2026. Paul's rulings (never read the markets sheet; the fill
# sheet for 2023-2026) are tested in test-paul-rulings.R.

ec_panel_for <- function(folder, rules = PARITY, ...) {
  data <- synth_build(folder, ...)
  wbs <- sgs_load_all(data, rules)
  list(sy = sgs_build_sector_year(wbs, rules), wbs = wbs)
}

at <- function(sy, year, col) {
  v <- sy[[col]][sy$study_sector == "commercial_banks" & sy$year == year]
  stopifnot(length(v) == 1)
  v
}

ec_env <- local({
  base <- tmp_dir()
  list(iem_only = ec_panel_for(file.path(base, "iem"), iem_last_year = 2022)$sy,
       filled = ec_panel_for(file.path(base, "fill"), iem_last_year = 2022, expected_control = expected_control_sheet()),
       iem_full = ec_panel_for(file.path(base, "iemfull"), expected_control = expected_control_sheet())$sy,
       mk = ec_panel_for(file.path(base, "mk"), iem_last_year = 2022, expected_control = expected_control_sheet(),
                         markets = markets_frame())$sy)
})

test_that("TestExpectedControl.test_without_the_fill_sheet_2023_2025_stay_missing", {
  for (y in 2023:2025) {
    expect_true(is.na(at(ec_env$iem_only, y, "exp_dem_house")))
    expect_equal(at(ec_env$iem_only, y, "exp_dem_house_status"), "missing")
    expect_true(is.na(at(ec_env$iem_only, y, "exp_dem_house_method")))
  }
  expect_equal(at(ec_env$iem_only, 2022, "exp_dem_house_method"), "iem_annual_mean")
})

test_that("TestExpectedControl.test_fill_sheet_supplies_2023_2026_with_method_and_flag", {
  sy <- ec_env$filled$sy
  expect_equal(c(at(sy, 2023, "exp_dem_house"), at(sy, 2023, "exp_dem_senate")), c(1.0, 0.0))
  expect_equal(at(sy, 2023, "exp_dem_house_method"), "forecaster_final_call_binary")
  expect_equal(at(sy, 2023, "exp_dem_house_flag"), "measured Nov 2024, after the year")
  expect_true(is.na(at(sy, 2024, "exp_dem_house_flag")))
  expect_equal(at(sy, 2025, "exp_dem_house"), 0.9144, tolerance = 1e-7)
  expect_equal(at(sy, 2025, "exp_dem_senate_method"), "market_snapshot")
  expect_equal(at(sy, 2025, "exp_dem_senate_flag"), "measured Sep 2026, after the year")
  expect_equal(at(sy, 2023, "exp_dem_house_status"), "observed")
  expect_match(at(sy, 2023, "exp_dem_house_source"), "expected_control_2023_2026", fixed = TRUE)
  expect_equal(at(sy, 2023, "exp_shift_house"), 1.0 - at(sy, 2023, "cur_dem_house"), tolerance = 1e-7)
})

test_that("TestExpectedControl.test_iem_rows_unchanged_by_the_fill", {
  a <- ec_env$iem_only[ec_env$iem_only$year <= 2022, ]
  b <- ec_env$filled$sy[ec_env$filled$sy$year <= 2022, ]
  for (c in c("exp_dem_house", "exp_dem_senate", "exp_dem_house_status", "exp_dem_house_method")) expect_identical(a[[c]], b[[c]], info = c)
})

test_that("TestExpectedControl.test_iem_value_wins_over_the_fill_sheet_where_present", {
  sy <- ec_env$iem_full
  expect_false(isTRUE(all.equal(at(sy, 2023, "exp_dem_house"), 1.0)))
  expect_equal(at(sy, 2023, "exp_dem_house_method"), "iem_annual_mean")
})

test_that("TestExpectedControl.test_markets_sheet_takes_precedence_for_2023_2026", {
  sy <- ec_env$mk
  expect_equal(at(sy, 2023, "exp_dem_house"), (0.40 + 0.44 + 0.48) / 3, tolerance = 1e-7)
  expect_equal(at(sy, 2023, "exp_dem_house_method"), "market_daily_mean")
  expect_equal(at(sy, 2024, "exp_dem_house"), 0.50, tolerance = 1e-7)
  expect_equal(at(sy, 2023, "exp_dem_senate"), 1 - (0.70 + 0.60) / 2, tolerance = 1e-7)
  expect_equal(at(sy, 2025, "exp_dem_house"), 0.75, tolerance = 1e-7)
  expect_equal(at(sy, 2025, "exp_dem_house_flag"), "measured Jan 2026, after the year")
  expect_true(is.na(at(sy, 2023, "exp_dem_house_flag")))
  expect_equal(at(sy, 2024, "exp_dem_senate"), 0.0)
  expect_equal(at(sy, 2024, "exp_dem_senate_method"), "forecaster_final_call_binary")
  expect_equal(at(sy, 2026, "exp_dem_house"), 0.9144, tolerance = 1e-7)
  expect_equal(at(sy, 2026, "exp_dem_house_method"), "market_snapshot")
  expect_equal(at(sy, 2021, "exp_dem_house"), at(ec_env$iem_only, 2021, "exp_dem_house"))
  expect_equal(at(sy, 2021, "exp_dem_house_method"), "iem_annual_mean")
})

test_that("TestExpectedControl.test_flags_reach_the_tier_table", {
  syt <- sgs_build_sector_year_tier(ec_env$filled$wbs, ec_env$filled$sy)
  v <- syt$exp_dem_house_flag[syt$study_sector == "commercial_banks" & syt$year == 2023]
  expect_equal(unique(v), "measured Nov 2024, after the year")
})

test_that("TestExpectedControl.test_optional_sheets_validated_when_present", {
  bad <- markets_frame()
  bad$market <- NULL
  data <- synth_build(tmp_dir(), iem_last_year = 2022, markets = bad)
  err <- tryCatch(sgs_load_all(data, PARITY), LoadError = function(e) e)
  expect_s3_class(err, "LoadError")
  expect_match(conditionMessage(err), "[expected_control_markets] column market", fixed = TRUE)
})
