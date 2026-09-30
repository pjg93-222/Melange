# Port of code/tests/test_estimate.py: OLS recovery, HC1 / CR1 errors, and the fast wild-cluster-restricted algebra
# against brute force. Added for the R port: the OLS coefficients against lm().

.design_of <- function(df, sp, window = c(2016, 2025)) {
  smp <- sgs_build_sample(list(sector_year = df), sp, window)
  list(smp = smp, d = sgs_build_design(smp$df, sp))
}

test_that("TestRecovery.test_known_coefficients_recovered_exactly_without_noise", {
  df <- sector_year_panel(n_sectors = 6, noise = 0.0)
  x <- .design_of(df, tspec(controls = L_CONTROLS))
  fit <- sgs_ols(x$d)
  for (k in c("growth_previous_year_pct", L_CONTROLS)) expect_equal(sgs_fit_coef(fit, k), TRUE_BETA[[k]], tolerance = 1e-8, info = k)
  for (i in seq_along(x$d$cluster_labels)) {
    expect_equal(sgs_fit_coef(fit, paste0("FE:", x$d$cluster_labels[i])), 5.0 + 3.0 * (i - 1), tolerance = 1e-8)
  }
})

test_that("TestRecovery.test_known_coefficients_recovered_with_noise", {
  df <- sector_year_panel(n_sectors = 6, noise = 0.05, seed = 11)
  fit <- sgs_ols(.design_of(df, tspec(controls = L_CONTROLS))$d)
  expect_lt(abs(sgs_fit_coef(fit, "growth_previous_year_pct") - 0.8), 0.02)
  expect_lt(abs(sgs_fit_coef(fit, "pres_year") - 1.5), 0.1)
})

test_that("TestRecovery.test_hc1_and_cr1_match_the_textbook_formulas (statsmodels in Python)", {
  df <- sector_year_panel(n_sectors = 5, noise = 0.5, seed = 3)
  d <- .design_of(df, tspec())$d
  fit <- sgs_ols(d)
  X <- d$X; y <- d$y; n <- nrow(X); p <- ncol(X)
  XtXi <- solve(crossprod(X))
  u <- as.vector(y - X %*% (XtXi %*% crossprod(X, y)))
  hc1 <- sqrt(diag(XtXi %*% crossprod(X * u) %*% XtXi) * n / (n - p))
  G <- length(unique(d$clusters))
  S <- rowsum(X * u, d$clusters)
  cr1 <- sqrt(diag(XtXi %*% crossprod(S) %*% XtXi) * G / (G - 1) * (n - 1) / (n - p))
  expect_equal(unname(fit$se_hc1), unname(hc1), tolerance = 1e-8)
  expect_equal(unname(fit$se_cr1), unname(cr1), tolerance = 1e-8)
})

test_that("R port: OLS coefficients equal lm() on the same design (sector, tier, year-FE and first-difference designs)", {
  df <- sector_year_panel(n_sectors = 6, noise = 0.7, seed = 12)
  for (sp in list(tspec(controls = L_CONTROLS), tspec(controls = character(0), fe = c("sector", "year"), variant = "year_fe"),
                  tspec(controls = c("pres_year", "midterm_year"), fe = character(0), variant = "fd"))) {
    smp <- sgs_build_sample(list(sector_year = df), sp, c(2016, 2025))
    d <- sgs_build_design(smp$df, sp)
    fit <- sgs_ols(d)
    X <- d$X
    m <- stats::lm(d$y ~ 0 + X)
    expect_equal(unname(fit$beta), unname(stats::coef(m)), tolerance = 1e-10)
    expect_equal(unname(fit$resid), unname(stats::residuals(m)), tolerance = 1e-10)
    # HC1 against lm(): (n / (n - p)) * (X'X)^-1 X' diag(u^2) X (X'X)^-1 with lm's own residuals
    V <- summary(m)$cov.unscaled
    e <- stats::residuals(m)
    hc1 <- sqrt(diag(V %*% crossprod(X * e) %*% V) * nrow(X) / (nrow(X) - ncol(X)))
    expect_equal(unname(fit$se_hc1), unname(hc1), tolerance = 1e-8)
  }
})

.brute_force_tstars <- function(d, fit, k, b0, V) {
  X <- d$X; y <- d$y; cl <- d$clusters
  n <- nrow(X); p <- ncol(X); G <- fit$G
  Xmk <- X[, -k, drop = FALSE]
  yr <- y - b0 * X[, k]
  g <- qr.coef(qr(Xmk), yr)
  u_r <- as.vector(yr - Xmk %*% g)
  fitted <- y - u_r
  A <- solve(crossprod(X))
  cc <- G / (G - 1) * (n - 1) / (n - p)
  apply(V, 1, function(v) {
    ys <- fitted + u_r * v[cl + 1]
    bs <- A %*% crossprod(X, ys)
    us <- as.vector(ys - X %*% bs)
    S <- rowsum(X * us, cl)
    se <- sqrt(cc * (A %*% crossprod(S) %*% A)[k, k])
    (bs[k] - b0) / se
  })
}

.wcr_setup <- function() {
  df <- sector_year_panel(n_sectors = 4, noise = 1.0, seed = 5, years = 2016:2025)
  x <- .design_of(df, tspec())
  fit <- sgs_ols(x$d)
  list(d = x$d, fit = fit, k = match("growth_previous_year_pct", fit$names))
}

test_that("TestWildClusterAlgebra.test_fast_equals_brute_force", {
  s <- .wcr_setup()
  w <- sgs_wcr(s$d, s$fit, s$k, 9999, sgs_seed_entropy(1, "t"))
  expect_true(w$enumerated)
  expect_equal(w$draws, 6^4)
  V <- sgs_webb_draws(4, 9999, NULL)$V
  for (b0 in c(0.0, 0.3, -2.0, sgs_fit_coef(s$fit, "growth_previous_year_pct"))) {
    fast <- w$tstar(b0)
    brute <- .brute_force_tstars(s$d, s$fit, s$k, b0, V)
    expect_true(all(abs(fast - brute) <= 1e-9 + 1e-7 * abs(brute)), info = paste("b0", b0))
  }
})

test_that("TestWildClusterAlgebra.test_se_is_cr1", {
  s <- .wcr_setup()
  w <- sgs_wcr(s$d, s$fit, s$k, 9999, sgs_seed_entropy(1, "t"))
  expect_equal(w$se, s$fit$se_cr1[s$k], tolerance = 1e-10)
})

test_that("TestWildClusterAlgebra.test_identity_draw_reproduces_t_and_bounds_p", {
  s <- .wcr_setup()
  w <- sgs_wcr(s$d, s$fit, s$k, 9999, sgs_seed_entropy(1, "t"))
  ones <- which(apply(w$V == 1.0, 1, all))[1]
  for (b0 in c(0.0, 1.7, -5.0)) {
    expect_equal(w$tstar(b0)[ones], w$tstat(b0), tolerance = 1e-8)
    expect_gte(w$pvalue(b0), 2 / 6^4 - 1e-12)
  }
})

test_that("TestWildClusterAlgebra.test_ci_is_test_inversion", {
  s <- .wcr_setup()
  w <- sgs_wcr(s$d, s$fit, s$k, 9999, sgs_seed_entropy(1, "t"))
  ci <- w$ci(0.05)
  expect_lt(ci[1], w$bk)
  expect_gt(ci[2], w$bk)
  eps <- 1e-4 * w$se
  expect_gte(w$pvalue(ci[1] + eps), 0.05)
  expect_lt(w$pvalue(ci[1] - eps), 0.05)
  expect_gte(w$pvalue(ci[2] - eps), 0.05)
  expect_lt(w$pvalue(ci[2] + eps), 0.05)
})

test_that("TestWildClusterAlgebra.test_two_clusters_give_unbounded_interval", {
  df <- sector_year_panel(n_sectors = 2, noise = 1.0, seed = 9, years = 2016:2025)
  d <- .design_of(df, tspec(controls = "pres_year"))$d
  fit <- sgs_ols(d)
  row <- sgs_boot_coefficient(d, fit, "growth_previous_year_pct", 9999, sgs_seed_entropy(1, "x"))
  expect_equal(row$boot_draws, 36)
  expect_gte(row$boot_p, 2 / 36 - 1e-12)
  expect_true(is.infinite(row$ci_low) && is.infinite(row$ci_high))
})
