# Port of code/tests/test_lobbyview.py: LobbyView tests L1-LV..L3-LV (Paul's option (a), the parity rule set).

LV_NOTE_TXT <- "2 sectors: wild cluster bootstrap cannot reach p < 0.056; inference not available"

lv_panel <- function(noise = 0.02, seed = 4) {
  beta <- c(growth_previous_year_pct = 0.5, pres_year = 1.0, midterm_year = -0.3, exp_dem_house = 0.8,
            exp_dem_senate = -0.6, cur_dem_house = 0.2, cur_dem_senate = -0.1)
  df <- sector_year_panel(n_sectors = 2, years = 2006:2025, noise = noise, seed = seed, beta = beta, dv = "lobby_amount_undiff_real_m")
  df$lobby_undiff_status <- "observed"
  df$lobby_undiff_status[df$year == 2024] <- "partial"
  df$lobby_amount_undiff_real_m[df$year == 2025] <- NA
  df$lobby_undiff_status[df$year == 2025] <- "missing"
  for (c in c("exp_dem_house", "exp_dem_senate")) {
    df[[c]][df$year >= 2023] <- NA
    df[[paste0(c, "_status")]][df$year >= 2023] <- "missing"
  }
  df
}

REG_PARITY <- sgs_registry(PARITY)

test_that("TestRegistry.test_three_descriptive_lobbyview_tests", {
  lv <- Filter(function(t) t$family == "L-LV", REG_PARITY)
  expect_equal(unname(vapply(lv, `[[`, "", "id")), c("L1-LV", "L2-LV", "L3-LV"))
  for (i in 1:3) {
    t <- lv[[i]]
    expect_equal(list(t$label, t$dv, t$focal, t$controls, t$fe, t$inference),
                 list("DESCRIPTIVE", "lobby_amount_undiff_real_m", unname(SGS_GROWTH[i]), SGS_L_CONTROLS, "sector", "none"))
    expect_match(t$note, LV_NOTE_TXT, fixed = TRUE)
  }
})

test_that("TestRegistry.test_lda_l_tests_unchanged_and_never_mixed", {
  l_lda <- Filter(function(t) t$family == "L", REG_PARITY)
  expect_equal(length(l_lda), 6)
  expect_setequal(unique(vapply(l_lda, `[[`, "", "dv")), c("lobby_income_real_m", "lobby_expenses_real_m"))
  expect_true(all(vapply(l_lda, function(t) t$label == "CORE" && t$inference == "wcr", TRUE)))
  expect_length(Filter(function(t) isTRUE(t$base %in% c("L1-LV", "L2-LV", "L3-LV")), REG_PARITY), 0)
})

test_that("TestLobbyViewPath.test_gated_through_the_fallback_window", {
  d <- sgs_decide(REG_PARITY[["L1-LV"]], list(sector_year = lv_panel()))
  expect_equal(list(d$status, d$window, d$window_kind), list(SGS_ESTIMABLE, c(2013, 2022), "fallback"))
  expect_false(d$attempts[[1]]$ok)
  expect_equal(sgs_decision_chosen(d)$sectors, c("commercial_banks", "credit_unions"))
  expect_match(d$fallback_search, "complete-case years in 2008-2025: 2008-2022", fixed = TRUE)
})

test_that("TestLobbyViewPath.test_descriptive_output_no_inference", {
  sp <- REG_PARITY[["L1-LV"]]
  d <- sgs_decide(sp, list(sector_year = lv_panel()))
  res <- sgs_estimate(sp, sgs_decision_chosen(d), B = 999)
  expect_equal(length(res$coefs), 1)
  c1 <- res$coefs[[1]]
  expect_equal(c1$coefficient, "growth_previous_year_pct")
  expect_lt(abs(c1$estimate - 0.5), 0.05)
  expect_true(is.finite(c1$hc1_se) && c1$hc1_se > 0)
  for (k in c("boot_p", "ci_low", "ci_high", "cr1_se")) expect_true(is.nan(c1[[k]]), info = k)
  expect_equal(c1$boot_draws, 0)
  expect_equal(c1$boot_note, LV_NOTE_TXT)
  expect_true(startsWith(c1$inference, "none (DESCRIPTIVE)"))
  expect_true(startsWith(c1$stratification, "STRATIFIED") || startsWith(c1$stratification, "UNSTRATIFIED"))
  expect_equal(sgs_descriptive_note(2), LV_NOTE_TXT)
})
