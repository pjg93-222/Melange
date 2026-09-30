# Port of code/tests/test_preview.py: PREVIEW tests C1-PV..C3-PV and H1-PV: fixed window 2021-2025, labels, the NOT
# IDENTIFIED rule for the full core specification, wild cluster bootstrap enumeration, and H1-PV over every Mentat
# industry.

REG_P <- sgs_registry(PARITY)
PV <- Filter(function(t) t$label == "PREVIEW", REG_P)

test_that("TestPreviewRegistry.test_ten_preview_tests", {
  expect_equal(unname(vapply(PV, `[[`, "", "id")), c("C1-PV-reduced", "C1-PV-yearFE", "C1-PV-core", "C2-PV-reduced",
                                                     "C2-PV-yearFE", "C2-PV-core", "C3-PV-reduced", "C3-PV-yearFE",
                                                     "C3-PV-core", "H1-PV"))
  for (t in PV) expect_equal(list(t$gate, t$flag, t$dv), list("preview", "PREVIEW - below the 6-year minimum", "contributions_real_m"))
  expect_equal(list(REG_P[["C1-PV-reduced"]]$controls, REG_P[["C1-PV-reduced"]]$fe), list(c("pres_year", "midterm_year"), "sector"))
  expect_equal(list(REG_P[["C2-PV-yearFE"]]$controls, REG_P[["C2-PV-yearFE"]]$fe), list(character(0), c("sector", "year")))
  expect_equal(REG_P[["C3-PV-core"]]$controls, SGS_C_CONTROLS)
  expect_true(REG_P[["C3-PV-core"]]$saturation_check)
  expect_equal(list(REG_P[["H1-PV"]]$table, REG_P[["H1-PV"]]$focal), list("industry_year", c("pres_year", "midterm_year")))
  expect_equal(SGS$PREVIEW_WINDOW, c(2021, 2025))
})

test_that("TestSaturation.test_five_year_level_parameters_on_five_years_are_not_identified", {
  df <- sector_year_panel(n_sectors = 4, years = 2021:2025)
  tables <- list(sector_year = df)
  core <- REG_P[["C1-PV-core"]]
  d <- sgs_decide(core, tables)
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_true(startsWith(d$reason, "preview 2021-2025"))
  expect_match(d$reason, paste0("NOT IDENTIFIED: 5 year-level parameters (common level of the sector baselines, pres_year, ",
                                "midterm_year, exp_dem_house, exp_dem_senate) on 5 distinct years"), fixed = TRUE)
  smp <- sgs_build_sample(tables, core, c(2021, 2025))
  expect_equal(sgs_year_level_check(sgs_build_design(smp$df, core)), list(ok = TRUE, why = ""))
  red <- REG_P[["C1-PV-reduced"]]
  expect_equal(sgs_decide(red, tables)$status, SGS_ESTIMABLE)
  sc <- sgs_saturation_check(sgs_build_design(sgs_build_sample(tables, red, c(2021, 2025))$df, red))
  expect_true(sc$ok, info = sc$why)
})

test_that("TestSaturation.test_fixed_window_ignores_the_window_arguments", {
  df <- sector_year_panel(n_sectors = 3, years = 2014:2025)
  d <- sgs_decide(REG_P[["C1-PV-reduced"]], list(sector_year = df), default_window = c(2016, 2025), fallback_search = c(2008, 2025))
  expect_equal(list(d$status, d$window, d$window_kind, length(d$attempts)), list(SGS_ESTIMABLE, c(2021, 2025), "preview", 1L))
})

test_that("TestSaturation.test_four_years_are_not_enough", {
  df <- sector_year_panel(n_sectors = 3, years = 2014:2025)
  df$contributions_status[df$year == 2021] <- "missing"
  d <- sgs_decide(REG_P[["C1-PV-reduced"]], list(sector_year = df))
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "4 distinct years (2022-2025) < 5 required", fixed = TRUE)
})

# TestPreviewEndToEnd: synthetic inputs shaped like the real ones.
pv_env <- local({
  base <- tmp_dir()
  data <- synth_build(file.path(base, "data"), contrib_years = 2021:2025, extra_units = "community_banks",
                      iem_last_year = 2022, expected_control = expected_control_sheet())
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "results"), B = 9999, run_id = "analysis-test-pv",
                   only = c("C1-PV", "H1-PV", "C1"), rules = PARITY)
  rows <- setNames(out$est_rows, vapply(out$est_rows, `[[`, "", "test_id"))
  pv_ids <- vapply(PV, `[[`, "", "id")
  coefs <- Filter(function(c) c$test_id %in% pv_ids, out$coef_rows)
  list(out = out, rows = rows, coefs = coefs)
})

test_that("TestPreviewEndToEnd.test_reduced_and_year_fe_estimable_on_2021_2025", {
  for (tid in c("C1-PV-reduced", "C1-PV-yearFE")) {
    r <- pv_env$rows[[tid]]
    expect_equal(list(r$status, r$label, r$window_used, r$window_kind, r$n_years), list("ESTIMABLE", "PREVIEW", "2021-2025", "preview", 5L), info = tid)
    c1 <- Filter(function(c) c$test_id == tid, pv_env$coefs)[[1]]
    expect_lt(abs(c1$estimate - 0.3), 0.1)
    expect_equal(c1$resid_df, r$resid_df)
  }
  expect_equal(pv_env$rows[["C1"]]$status, "NOT ESTIMABLE")
})

test_that("TestPreviewEndToEnd.test_core_spec_reported_not_identified", {
  r <- pv_env$rows[["C1-PV-core"]]
  expect_equal(r$status, "NOT ESTIMABLE")
  expect_true(startsWith(r$reason_short, "preview 2021-2025: NOT IDENTIFIED: 5 year-level parameters on 5 distinct years"),
              info = r$reason_short)
  expect_match(r$input_flags, "2023 forecaster_final_call_binary (measured Nov 2024, after the year)", fixed = TRUE)
  expect_length(Filter(function(c) c$test_id == "C1-PV-core", pv_env$coefs), 0)
})

test_that("TestPreviewEndToEnd.test_every_preview_output_is_labeled", {
  expect_gt(length(pv_env$coefs), 0)
  for (c in pv_env$coefs) expect_match(c$flag, "PREVIEW - below the 6-year minimum", fixed = TRUE)
  for (tid in intersect(vapply(PV, `[[`, "", "id"), names(pv_env$rows))) {
    expect_equal(pv_env$rows[[tid]]$flag, "PREVIEW - below the 6-year minimum")
  }
  md <- paste(readLines(pv_env$out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, "### C1-PV-reduced (PREVIEW - below the 6-year minimum): ESTIMABLE", fixed = TRUE)
  expect_match(md, "### C1-PV-core (PREVIEW - below the 6-year minimum): NOT ESTIMABLE", fixed = TRUE)
  emd <- paste(readLines(pv_env$out$estimability, encoding = "UTF-8"), collapse = "\n")
  expect_match(emd, "| H1-PV | PREVIEW - below the 6-year minimum | ESTIMABLE | 2021-2025 |", fixed = TRUE)
})

test_that("TestPreviewEndToEnd.test_bootstrap_enumerates_all_draws_when_small", {
  c1 <- Filter(function(c) c$test_id == "C1-PV-reduced", pv_env$coefs)[[1]]
  G <- pv_env$rows[["C1-PV-reduced"]]$n_sectors
  expect_equal(G, 5)
  expect_equal(list(c1$boot_draws, c1$boot_enumerated), list(6^G, TRUE))
  expect_gte(c1$boot_p, 2 / 6^G)
})

test_that("TestPreviewEndToEnd.test_h1_pv_covers_every_mentat_industry_and_matches_ols", {
  r <- pv_env$rows[["H1-PV"]]
  expect_equal(r$status, "ESTIMABLE")
  expect_match(r$sectors, "community_banks", fixed = TRUE)
  expect_equal(list(r$n_sectors, r$n), list(6L, 30L))
  expect_equal(r$cluster_by, "Mentat industry")
  df <- sgs_decision_chosen(pv_env$out$decisions[["H1-PV"]])$sample$df
  units <- sort(unique(df$study_sector))
  X <- cbind(df$pres_year, df$midterm_year, sapply(units, function(u) as.numeric(df$study_sector == u)))
  b <- qr.coef(qr(X), df$y)
  got <- setNames(Filter(function(c) c$test_id == "H1-PV", pv_env$coefs),
                  vapply(Filter(function(c) c$test_id == "H1-PV", pv_env$coefs), `[[`, "", "coefficient"))
  expect_equal(unname(got$pres_year$estimate), unname(b[1]), tolerance = 1e-9)
  expect_equal(unname(got$midterm_year$estimate), unname(b[2]), tolerance = 1e-9)
  expect_lt(abs(b[1] - 1.0), 1.0)
  expect_true(startsWith(got$pres_year$stratification, "STRATIFIED"))
  iy <- pv_env$out$tables$industry_year
  expect_false(any(iy$is_study_sector[iy$study_sector == "community_banks"]))
})
