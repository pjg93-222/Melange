# Port of code/tests/test_champions.py: H5 (champions, 05): slope recovery with and without champion fixed effects,
# the member-cycle gate, and NOT BUILT when 05 is missing, being rewritten, or lacks expected columns.

REG_C <- sgs_registry(PARITY)
POOLED <- REG_C[["H5-pooled"]]
WITHIN <- REG_C[["H5-within"]]

test_that("TestRecovery.test_pooled_and_within_recover_the_slope_without_member_effects", {
  cd <- champions_data_from(champions_frame(slope = 5000.0, member_corr = 0.0, noise = 0.0))
  for (spec in list(POOLED, WITHIN)) {
    d <- sgs_decide_h5(spec, cd)
    expect_equal(d$status, SGS_ESTIMABLE, info = d$reason)
    res <- sgs_estimate_h5(spec, d, B = 999)
    expect_equal(res$coefs[[1]]$estimate, 5000.0, tolerance = 1e-9, info = spec$id)
    expect_equal(sgs_h5_cycles(d$sample), c(2022L, 2024L, 2026L))
  }
})

test_that("TestRecovery.test_within_recovers_the_slope_when_member_effects_track_toughness", {
  cd <- champions_data_from(champions_frame(slope = 5000.0, member_corr = 1.0, noise = 0.0, seed = 8))
  dw <- sgs_decide_h5(WITHIN, cd)
  expect_equal(dw$status, SGS_ESTIMABLE, info = dw$reason)
  bw <- sgs_estimate_h5(WITHIN, dw, B = 999)$coefs[[1]]$estimate
  expect_equal(bw, 5000.0, tolerance = 1e-9)
  dp <- sgs_decide_h5(POOLED, cd)
  bp <- sgs_estimate_h5(POOLED, dp, B = 999)$coefs[[1]]$estimate
  expect_gt(abs(bp - 5000.0), 500.0)
  expect_true("seniority_years" %in% dw$info$dropped_controls)
  expect_true("chamber=Senate" %in% dw$info$dropped_controls)
  expect_equal(dw$design$nested_fe, length(sgs_h5_champions(dw$sample)))
  expect_gt(dw$identifying_champions, 0)
})

test_that("TestRecovery.test_noisy_recovery_inference_and_strata", {
  cd <- champions_data_from(champions_frame(n_members = 60, slope = 5000.0, noise = 2000.0, seed = 11))
  d <- sgs_decide_h5(POOLED, cd)
  res <- sgs_estimate_h5(POOLED, d, B = 999)
  c1 <- res$coefs[[1]]
  expect_lt(abs(c1$estimate - 5000.0), 1000.0)
  expect_true(c1$ci_low < 5000.0 && 5000.0 < c1$ci_high)
  expect_lt(c1$boot_p, 0.05)
  expect_equal(c1$boot_draws, 999)
  expect_true(startsWith(c1$stratification, "STRATIFIED"))
  expect_equal(sort(unique(vapply(res$strata, `[[`, "", "board"))), c("bank", "credit_union", "crypto"))
  expect_match(c1$flag, "employee channel only", fixed = TRUE)
})

test_that("TestRecovery.test_sample_rules", {
  frame <- champions_frame()
  cd <- champions_data_from(frame)
  d <- sgs_decide_h5(POOLED, cd)
  df <- d$sample$df
  expect_true(all(df$up_for_election == 1))
  expect_false(any(df$lost_primary %in% 1))
  expect_true("lost_primary = 1 (lost renomination; such rows enter only the primary models)" %in% names(d$sample$exclusions))
  smp <- sgs_build_h5_sample(cd, REG_C[["H5-primary_contested"]], "direct_giving_real_2025_usd", "", "")
  expect_true(any(grepl("lost-renomination rows kept", smp$notes, fixed = TRUE)))
  dl <- sgs_decide_h5(REG_C[["H5-pooled-log1p"]], cd)
  expect_equal(dl$sample$df$y, log1p(dl$sample$df$direct_giving_real_2025_usd), tolerance = 1e-12)
  da <- sgs_decide_h5(REG_C[["H5-pooled-any"]], cd)
  expect_true(all(unique(da$sample$df$y) %in% c(0, 1)))
})

test_that("TestGate.test_excluding_2026_leaves_two_cycles", {
  d <- sgs_decide_h5(REG_C[["H5-pooled-no2026"]], champions_data_from(champions_frame()))
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "2 cycles (2022, 2024) < 3 required", fixed = TRUE)
})

test_that("TestGate.test_too_few_member_cycles", {
  d <- sgs_decide_h5(POOLED, champions_data_from(champions_frame(n_members = 8, boards = "bank")))
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "member-cycles < 30 required", fixed = TRUE)
})

test_that("TestGate.test_zero_variance_focal", {
  f <- champions_frame()
  f$toughness_general[!is.na(f$toughness_general)] <- 1.0
  d <- sgs_decide_h5(POOLED, champions_data_from(f))
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "toughness_general: zero variance", fixed = TRUE)
})

test_that("TestGate.test_within_needs_within_champion_variation", {
  f <- champions_frame()
  has <- !is.na(f$toughness_general)
  f$toughness_general[has] <- as.numeric(as.integer(substring(f$bioguide[has], 2)) %% 4)
  expect_equal(sgs_decide_h5(POOLED, champions_data_from(f))$status, SGS_ESTIMABLE)
  d <- sgs_decide_h5(WITHIN, champions_data_from(f))
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "zero within-champion variance", fixed = TRUE)
})

test_that("TestGate.test_secondary_regressor_blocked_by_cycles", {
  d <- sgs_decide_h5(REG_C[["H5-primary_contested"]], champions_data_from(champions_frame()))
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "1 cycles (2022) < 3 required", fixed = TRUE)
  expect_match(d$reason, "primary_contested usable in cycles 2020, 2022", fixed = TRUE)
})

.data_dir <- function() {
  base <- tmp_dir()
  d <- file.path(base, "data")
  dir.create(d)
  d
}

test_that("TestLoadingAndNotBuilt.test_missing_05_is_not_built", {
  cd <- sgs_load_champions(.data_dir())
  expect_false(cd$ok)
  expect_match(cd$reason, "05_industry_champions.xlsx not found", fixed = TRUE)
  d <- sgs_decide_h5(POOLED, cd)
  expect_equal(d$status, SGS_NOT_BUILT)
  expect_true(startsWith(d$reason, "NotBuilt: "))
})

test_that("TestLoadingAndNotBuilt.test_missing_receipt_is_not_built", {
  dd <- .data_dir()
  write_champions(dd, champions_frame(), write_receipt = FALSE)
  cd <- sgs_load_champions(dd)
  expect_false(cd$ok)
  expect_match(cd$reason, "build_receipt_05.json not found", fixed = TRUE)
})

test_that("TestLoadingAndNotBuilt.test_fresh_receipt_means_being_rewritten", {
  dd <- .data_dir()
  write_champions(dd, champions_frame(), age_minutes = 2.0)
  cd <- sgs_load_champions(dd)
  expect_false(cd$ok)
  expect_match(cd$reason, "min ago (< 10 min): 05 is being rewritten", fixed = TRUE)
  expect_equal(sgs_decide_h5(WITHIN, cd)$status, SGS_NOT_BUILT)
})

test_that("TestLoadingAndNotBuilt.test_bytes_differing_from_the_receipt", {
  dd <- .data_dir()
  write_champions(dd, champions_frame(), receipt_sha = strrep("0", 64))
  cd <- sgs_load_champions(dd)
  expect_false(cd$ok)
  expect_match(cd$reason, "differs from the receipt", fixed = TRUE)
})

test_that("TestLoadingAndNotBuilt.test_missing_expected_column", {
  dd <- .data_dir()
  f <- champions_frame(); f$toughness_general <- NULL
  write_champions(dd, f)
  cd <- sgs_load_champions(dd)
  expect_false(cd$ok)
  expect_match(cd$reason, "expected columns missing from 05_industry_champions.xlsx [data]: toughness_general", fixed = TRUE)
})

test_that("TestLoadingAndNotBuilt.test_no_dependent_variable_column", {
  dd <- .data_dir()
  f <- champions_frame(); f$direct_giving_real_2025_usd <- NULL
  write_champions(dd, f)
  cd <- sgs_load_champions(dd)
  expect_false(cd$ok)
  expect_match(cd$reason, "industry_money_primary_real_2025_usd or direct_giving_real_2025_usd", fixed = TRUE)
})

test_that("TestLoadingAndNotBuilt.test_loaded_and_dv_choice", {
  dd <- .data_dir()
  write_champions(dd, champions_frame())
  cd <- sgs_load_champions(dd)
  expect_true(cd$ok, info = cd$reason)
  expect_equal(nchar(cd$source$sha256), 64)
  dv <- sgs_resolve_dv(cd, "industry_money_primary")
  expect_equal(c(dv$col, dv$flag), c("direct_giving_real_2025_usd", "employee channel only"))
  expect_match(dv$label, "employee channel only", fixed = TRUE)
  trade <- sgs_decide_h5(REG_C[["H5-pooled-trade"]], cd)
  expect_equal(trade$status, SGS_NOT_BUILT)
  expect_match(trade$reason, "industry_money_with_trade_real_2025_usd", fixed = TRUE)
})

test_that("TestLoadingAndNotBuilt.test_primary_money_column_preferred_when_present", {
  dd <- .data_dir()
  write_champions(dd, champions_frame(primary_dv = TRUE, trade = TRUE))
  cd <- sgs_load_champions(dd)
  dv <- sgs_resolve_dv(cd, "industry_money_primary")
  expect_equal(c(dv$col, dv$flag), c("industry_money_primary_real_2025_usd", ""))
  d <- sgs_decide_h5(REG_C[["H5-pooled-trade"]], cd)
  expect_equal(c(d$status, d$dv_col), c(SGS_ESTIMABLE, "industry_money_with_trade_real_2025_usd"))
})

test_that("TestLoadingAndNotBuilt.test_formula_cell_is_not_built", {
  dd <- .data_dir()
  f <- champions_frame()
  f$name[1] <- "=A1"
  write_champions(dd, f, allow_formulas = TRUE)
  cd <- sgs_load_champions(dd)
  expect_false(cd$ok)
  expect_match(cd$reason, "value starts with '='", fixed = TRUE)
})
