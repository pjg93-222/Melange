# Port of code/tests/test_loo_tier.py: leave-one-out loops and the tier-interaction coding (Employee reference).

.direct_coef <- function(sub, sp) {
  sub$y <- sub$contributions_real_m
  lsp <- sp; lsp$variant <- "level"
  sgs_fit_coef(sgs_ols(sgs_build_design(sub, lsp)), "growth_previous_year_pct")
}

test_that("TestLeaveOneOut.test_leave_one_sector_out", {
  df <- sector_year_panel(n_sectors = 5, years = 2016:2025, noise = 0.3, seed = 31)
  sp <- tspec(id = "R-LOSO-X", variant = "loso")
  d <- sgs_decide(sp, list(sector_year = df), c(2016, 2025), NULL)
  expect_equal(d$status, SGS_ESTIMABLE)
  res <- sgs_estimate(sp, sgs_decision_chosen(d), B = 999)
  expect_equal(vapply(res$subfits, `[[`, "", "left_out"), SECTORS[1:5])
  for (r in res$subfits) {
    expect_equal(r$status, "estimated")
    sub <- df[df$study_sector != r$left_out, , drop = FALSE]
    expect_equal(r$estimate, .direct_coef(sub, sp), tolerance = 1e-10)
    expect_equal(r$n_sectors, 4)
  }
})

test_that("TestLeaveOneOut.test_leave_one_year_out_flags_the_minimum", {
  df0 <- sector_year_panel(n_sectors = 5, years = 2016:2025, noise = 0.3, seed = 31)
  df <- df0[df0$year >= 2020, , drop = FALSE]
  sp <- tspec(id = "R-LOYO-X", variant = "loyo", controls = c("pres_year", "midterm_year"))
  d <- sgs_decide(sp, list(sector_year = df), c(2020, 2025), NULL)
  expect_equal(d$status, SGS_ESTIMABLE)
  res <- sgs_estimate(sp, sgs_decision_chosen(d), B = 999)
  expect_equal(vapply(res$subfits, `[[`, "", "left_out"), as.character(2020:2025))
  for (r in res$subfits) {
    expect_equal(r$n_years, 5)
    expect_match(r$flag, "diagnostic: 5 years < the 6-year minimum", fixed = TRUE)
    if (r$status == "estimated") {
      sub <- df[df$year != as.numeric(r$left_out), , drop = FALSE]
      expect_equal(r$estimate, .direct_coef(sub, sp), tolerance = 1e-10)
    }
  }
  mid <- Filter(function(r) r$left_out == "2022", res$subfits)[[1]]
  expect_equal(mid$status, "not estimable")
  expect_match(mid$reason, "midterm_year", fixed = TRUE)
})

tier_panel <- function(n_sectors = 4, years = 2016:2025, seed = 3, slopes = NULL) {
  slopes <- slopes %||% c(Employee = 1.0, Chief = 3.0, `Middle Management` = 2.0, Corporate = 5.0)
  nat <- national(years, seed)
  set.seed(seed)
  rows <- list()
  for (i in seq_len(n_sectors)) for (j in seq_len(nrow(nat))) {
    x <- rnorm(1, 2, 3)
    for (ti in seq_along(SGS$TIERS)) {
      t <- SGS$TIERS[ti]
      y <- 1.0 + (i - 1) + 0.5 * (ti - 1) + slopes[[t]] * x + 1.2 * nat$pres_year[j] - 0.4 * nat$exp_dem_house[j]
      rows[[length(rows) + 1L]] <- list(study_sector = SECTORS[i], year = nat$year[j], tier = t, partial_year = FALSE,
                                        growth_previous_year_pct = x, contributions_real_m = y, pres_year = nat$pres_year[j],
                                        midterm_year = nat$midterm_year[j], exp_dem_house = nat$exp_dem_house[j],
                                        exp_dem_senate = nat$exp_dem_senate[j], contributions_status = "observed",
                                        growth_prev_status = "observed", controls_status = "observed",
                                        exp_dem_house_status = "observed", exp_dem_senate_status = "observed")
    }
  }
  do.call(rbind, lapply(rows, as.data.frame, stringsAsFactors = FALSE))
}

test_that("TestTierModel.test_employee_is_the_reference_tier", {
  x <- "growth_previous_year_pct"
  sp <- tspec(id = "T1", table = "sector_year_tier", focal = c(x, paste0(x, ":Chief"), paste0(x, ":Middle Management")),
              fe = "sector_x_tier", variant = "tier", tiers = SGS$TIER_MODEL_TIERS,
              interactions = list(c(x, "Chief"), c(x, "Middle Management")))
  tab <- list(sector_year_tier = tier_panel())
  smp <- sgs_build_sample(tab, sp, c(2016, 2025))
  expect_setequal(unique(smp$df$tier), c("Chief", "Middle Management", "Employee"))
  d <- sgs_build_design(smp$df, sp)
  expect_true(x %in% d$names)
  expect_true(paste0(x, ":Chief") %in% d$names)
  expect_true(paste0(x, ":Middle Management") %in% d$names)
  expect_false(paste0(x, ":Employee") %in% d$names)
  expect_equal(sum(startsWith(d$names, "FE:")), 4 * 3)
  fit <- sgs_ols(d)
  expect_equal(sgs_fit_coef(fit, x), 1.0, tolerance = 1e-8)
  expect_equal(sgs_fit_coef(fit, paste0(x, ":Chief")), 2.0, tolerance = 1e-8)
  expect_equal(sgs_fit_coef(fit, paste0(x, ":Middle Management")), 1.0, tolerance = 1e-8)
  dec <- sgs_decide(sp, tab, c(2016, 2025), NULL)
  expect_equal(dec$status, SGS_ESTIMABLE)
  res <- sgs_estimate(sp, sgs_decision_chosen(dec), B = 999)
  expect_equal(vapply(res$coefs, `[[`, "", "coefficient"), sp$focal)
})

test_that("TestTierModel.test_corporate_fitted_separately", {
  x <- "growth_previous_year_pct"
  sp <- tspec(id = "T1-corporate", table = "sector_year_tier", tiers = SGS$CORPORATE_TIER)
  smp <- sgs_build_sample(list(sector_year_tier = tier_panel()), sp, c(2016, 2025))
  expect_setequal(unique(smp$df$tier), "Corporate")
  fit <- sgs_ols(sgs_build_design(smp$df, sp))
  expect_equal(sgs_fit_coef(fit, x), 5.0, tolerance = 1e-8)
})
