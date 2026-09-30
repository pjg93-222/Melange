# Port of code/tests/test_bootstrap.py: seeded reproducibility and the null p-value distribution (G = 6).

.boot_fit <- function(n_sectors, seed, beta = NULL, noise = 1.0, years = 2016:2025) {
  df <- sector_year_panel(n_sectors = n_sectors, noise = noise, seed = seed, beta = beta, years = years)
  sp <- tspec(controls = c("pres_year", "midterm_year"))
  smp <- sgs_build_sample(list(sector_year = df), sp, c(min(years), max(years)))
  d <- sgs_build_design(smp$df, sp)
  list(d = d, fit = sgs_ols(d))
}

test_that("TestReproducible.test_same_seed_same_result_random_draws", {
  x <- .boot_fit(7, seed = 21)  # 6^7 > 9,999: random draws
  a <- sgs_boot_coefficient(x$d, x$fit, "growth_previous_year_pct", SGS$BOOT_B, sgs_seed_entropy(42, "T", "g"))
  b <- sgs_boot_coefficient(x$d, x$fit, "growth_previous_year_pct", SGS$BOOT_B, sgs_seed_entropy(42, "T", "g"))
  expect_false(a$boot_enumerated)
  expect_equal(a$boot_draws, SGS$BOOT_B)
  for (key in c("boot_p", "ci_low", "ci_high")) expect_identical(a[[key]], b[[key]])
  c3 <- sgs_boot_coefficient(x$d, x$fit, "growth_previous_year_pct", SGS$BOOT_B, sgs_seed_entropy(43, "T", "g"))
  expect_false(identical(c(a$ci_low, a$ci_high), c(c3$ci_low, c3$ci_high)))
})

test_that("TestReproducible.test_enumeration_when_small", {
  x <- .boot_fit(5, seed = 22)
  r <- sgs_boot_coefficient(x$d, x$fit, "growth_previous_year_pct", SGS$BOOT_B, sgs_seed_entropy(1, "x"))
  expect_true(r$boot_enumerated)
  expect_equal(r$boot_draws, 6^5)
})

test_that("TestReproducible.test_null_pvalues_roughly_uniform_g6", {
  reps <- as.integer(Sys.getenv("SGS_NULL_REPS", "200"))
  beta0 <- c(growth_previous_year_pct = 0.0, pres_year = 1.0, midterm_year = -0.5)
  ps <- numeric(reps)
  for (r in seq_len(reps)) {
    x <- .boot_fit(6, seed = 1000 + r, beta = beta0, noise = 1.0)
    k <- match("growth_previous_year_pct", x$fit$names)
    w <- sgs_wcr(x$d, x$fit, k, SGS$BOOT_B, sgs_seed_entropy(SGS$SEED, "null", as.character(r)))
    ps[r] <- w$pvalue(0.0)
  }
  rate5 <- mean(ps < 0.05); rate10 <- mean(ps < 0.10)
  grid <- seq(0, 1, length.out = 201)
  ks <- max(abs(findInterval(grid, sort(ps)) / length(ps) - grid))
  message(sprintf("NULL_SIMULATION G=6 reps=%d B=%d: rejection rate at 5%% = %.3f, at 10%% = %.3f; KS distance to uniform = %.3f",
                  reps, SGS$BOOT_B, rate5, rate10, ks))
  expect_lte(rate5, 0.10)
  expect_gte(rate5, 0.005)
  expect_lt(ks, 0.15)
})
