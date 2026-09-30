# R port only: the coordinator's revisions of 2026-09-26 (after Paul's fit question and the Codex methodology review of
# run analysis-R-20260926T070630Z), rule set paul-2026-09-25, on synthetic data: the SHIFT revert and the post-result
# EXPLORATORY minimum-base variants, the L-LV robustness family (matched to the base test's sample), incremental fit,
# Holm, the two-way sensitivity and temporal support, chronology (measured_at, STRICT, the strict backtest), the fit
# table against the previous run, and the Kalshi flag. The parity rule set has none of them.

# A LobbyView sheet (as the other R-only test files build it): banks and credit unions high confidence, crypto roster,
# property_casualty naics, credit_arms thin throughout (excluded from the primary series).
rev_lv_sheet <- function(years = 2006:2024, seed = 41, scale = c()) {
  set.seed(seed)
  conf <- c(commercial_banks = "high", credit_unions = "high", crypto = "roster", credit_arms = "naics", property_casualty = "naics")
  rows <- list()
  for (s in names(conf)) for (y in years) {
    amount <- (10 + 3 * match(s, names(conf)) + 0.2 * (y - 2006) + rnorm(1, 0, 0.8)) * 1e6
    if (s %in% names(scale)) amount <- amount * scale[[s]]
    thin <- s == "credit_arms"
    cov <- paste(c(if (y == 2024) "partial_year", if (thin) "thin"), collapse = ";")
    if (!nzchar(cov)) cov <- "ok"
    rows[[length(rows) + 1L]] <- list(source = "lobbyview", sector = s, confidence = conf[[s]], year = y, period = "annual",
                                      lobby_amount_undifferentiated_real_2025_usd = amount,
                                      lobby_amount_dedup_real_2025_usd = 0.8 * amount, dedup_ratio = 0.8,
                                      status = if (y == 2024) "partial" else "observed", study_sector = s, coverage_flag = cov)
  }
  .rows_df(rows)
}

rev_world <- function(folder, scale = c()) {
  synth_build(folder, expected_control = expected_control_sheet(), iem_last_year = 2022,
              extra_sheets = list(lobbying = setNames(list(rev_lv_sheet(scale = scale)), SGS$LOBBYVIEW_ALL_SHEET)))
}

REV_ONLY <- c("R-yearFE-L3-LV", "R-log-L3-LV", "R-logFE-L3-LV", "R-FD-L3-LV", "FDY-L3-LV", "FDY-LOSO-L3-LV", "FDY-LOYO-L3-LV",
              "R-LOSO-L3-LV", "STRICT-L3-LV", "SLOPES-L3-LV")

rev_env <- local({
  base <- tmp_dir()
  data <- rev_world(file.path(base, "data"))
  res <- file.path(base, "results")
  out1 <- quiet_run(data_dir = data, results_dir = res, B = 99, only = REV_ONLY, rules = PAUL, run_id = "analysis-R-20260101T000000Z")
  out2 <- quiet_run(data_dir = data, results_dir = res, B = 99, only = REV_ONLY, rules = PAUL, run_id = "analysis-R-20260102T000000Z")
  list(base = base, data = data, res = res, out = out1, out2 = out2,
       rows = setNames(out1$est_rows, vapply(out1$est_rows, `[[`, "", "test_id")))
})
rev_coef <- function(tid, name = "predicted_growth_pct", out = rev_env$out) {
  Filter(function(c) identical(c$test_id, tid) && identical(c$coefficient, name) && is.null(c$left_out), out$coef_rows)[[1]]
}
rev_sample <- function(tid = "L3-LV", out = rev_env$out) sgs_decision_chosen(out$decisions[[tid]])$sample$df

test_that("registry: SHIFT reverted (pre-specified models primary, no minimum base); post-result minimum-base variants EXPLORATORY", {
  rp <- sgs_registry(PAUL)
  main <- c("SHIFT-House", "SHIFT-Senate", "SHIFT-Chamber", "SHIFT-All", "SHIFT-All-House", "SHIFT-All-Senate")
  expect_equal(unname(vapply(rp[main], `[[`, "", "label")), rep("CORE", 6))
  expect_equal(names(rp)[names(rp) %in% main], main)                          # the order of run analysis-R-20260926T070630Z
  expect_true(all(vapply(rp[c(main, paste0(main, "-PV"), paste0(main, "-W"), paste0(main, "-FD"))],
                         function(s) is.na(s$min_base) && !isTRUE(s$strict_time), TRUE)))
  for (b in names(SGS$SHIFT_MIN_BASE_EXPLORATORY)) {
    for (m in main) {
      s <- rp[[paste0(m, "-", b)]]; spv <- rp[[paste0(m, "-", b, "-PV")]]
      expect_equal(s$label, "EXPLORATORY", info = s$id)
      expect_match(s$flag, SGS$POST_RESULT_FLAG, fixed = TRUE)
      expect_equal(spv$label, "PREVIEW")
      expect_match(spv$flag, SGS$POST_RESULT_FLAG, fixed = TRUE)
      expect_equal(s$min_base, SGS$SHIFT_MIN_BASE_EXPLORATORY[[b]])
      expect_equal(s$trend_group, paste0(m, "-minbase"))
      expect_match(s$note, "proposed on 2026-09-26 after the preview results were seen", fixed = TRUE)
    }
  }
  expect_equal(SGS$SHIFT_MIN_BASE_EXPLORATORY, c(B25K = 25000, B10K = 10000, B50K = 50000))
  expect_true(all(vapply(rp[paste0(main, "-STRICT")], function(s) isTRUE(s$strict_time) && s$label == "ROBUSTNESS", TRUE)))
  expect_match(SGS_SHIFT_WEIGHT_NOTE, "not evidence that small bases are noise", fixed = TRUE)
  expect_false(any(grepl("PRIMARY partisan test|SUPPORTING", vapply(rp, `[[`, "", "note"))))
  # the L-LV family (matched to the base test's sample) and the STRICT core variants
  for (k in 1:3) {
    b <- paste0("L", k, "-LV")
    ids <- paste0(c("R-yearFE-", "R-log-", "R-logFE-", "R-LOSO-", "R-LOYO-", "R-FD-", "FDY-", "FDY-LOSO-", "FDY-LOYO-"), b)
    expect_true(all(ids %in% names(rp)))
    expect_true(all(vapply(rp[ids], function(s) isTRUE(s$matched) && identical(s$base, b), TRUE)))
    expect_equal(rp[[paste0("FDY-", b)]]$fe, "year_full")
    expect_equal(rp[[paste0("FDY-", b)]]$inference, "none")
    expect_equal(rp[[paste0("FDY-", b)]]$label, "EXPLORATORY")
    expect_equal(rp[[paste0("R-logFE-", b)]]$fe, c("sector", "year"))
    expect_equal(rp[[paste0("R-FD-", b)]]$matched_transform, "fd_pairs")
    expect_true(isTRUE(rp[[paste0("STRICT-", b)]]$strict_time))
    expect_true(isTRUE(rp[[paste0("STRICT-C", k)]]$strict_time))
  }
  rq <- sgs_registry(PARITY)
  expect_false(any(vapply(rq, function(s) isTRUE(s$matched) || isTRUE(s$strict_time) || !is.na(s$min_base), TRUE)))
  expect_false(any(grepl("^(FDY|STRICT)-|-B(25|10|50)K", names(rq))))
})

test_that("the Kalshi co-founder attribution (Paul's option A) is in the flag, verbatim", {
  expect_identical(SGS$SHIFT_FLAGS[[1]]$text,
                   paste0("fintech Senate 2026: partial year; $501,549.59 of fintech-sector giving to the NRSC, of which $500,000.00 ",
                          "from Kalshi's co-founders MANSOUR, TAREK and LARA, LUANA LOPES (verified from donor-level rows); 04 shows ",
                          "$600,000 from Kalshi employees to Republican party committees"))
  expect_match(SGS$SHIFT_FLAGS[[2]]$text, "^fintech 2026: partial year; \\$501,549\\.59 of fintech-sector giving to the NRSC, of which")
  dic <- readxl::read_excel(rev_env$out$xlsx, sheet = "dictionary")
  expect_true(any(grepl(SGS$SHIFT_FLAGS[[1]]$text, dic$definition, fixed = TRUE)))   # the shift_flag_* definition
})

test_that("L-LV robustness: every variant is fitted on the base test's gated sample and equals lm() on it", {
  r <- rev_env$rows
  expect_equal(r[["L3-LV"]]$status, SGS_ESTIMABLE)                     # added to the run as the matched variants' base
  df <- rev_sample("L3-LV")
  g <- "predicted_growth_pct"
  for (id in c("R-yearFE-L3-LV", "R-log-L3-LV", "R-logFE-L3-LV", "R-LOSO-L3-LV")) {
    expect_equal(r[[id]]$status, SGS_ESTIMABLE, info = id)
    expect_equal(r[[id]]$window_used, r[["L3-LV"]]$window_used, info = id)
    expect_match(r[[id]]$window_kind, "matched to L3-LV", fixed = TRUE)
  }
  expect_equal(r[["R-yearFE-L3-LV"]]$n, nrow(df))
  f <- lm(y ~ predicted_growth_pct + factor(study_sector) + factor(year), data = df)
  expect_equal(rev_coef("R-yearFE-L3-LV")$estimate, unname(coef(f)[g]), tolerance = 1e-9)
  f <- lm(log(lobby_lv_real_m) ~ predicted_growth_pct + factor(study_sector) + factor(year), data = df)
  expect_equal(rev_coef("R-logFE-L3-LV")$estimate, unname(coef(f)[g]), tolerance = 1e-9)
  f <- lm(log(lobby_lv_real_m) ~ predicted_growth_pct + pres_year + midterm_year + exp_dem_house + exp_dem_senate +
            cur_dem_house + cur_dem_senate + factor(study_sector), data = df)
  expect_equal(rev_coef("R-log-L3-LV")$estimate, unname(coef(f)[g]), tolerance = 1e-9)
  # first differences: the pairs of consecutive years both in the base sample
  o <- df[order(df$study_sector, df$year), ]
  j <- which(o$study_sector[-1] == o$study_sector[-nrow(o)] & diff(o$year) == 1) + 1L
  fd <- data.frame(study_sector = o$study_sector[j], year = o$year[j], dy = o$y[j] - o$y[j - 1],
                   dg = o[[g]][j] - o[[g]][j - 1])
  for (v in SGS_L_CONTROLS) fd[[paste0("d_", v)]] <- o[[v]][j] - o[[v]][j - 1]
  expect_equal(r[["FDY-L3-LV"]]$n, nrow(fd))
  f <- lm(dy ~ dg + factor(year), data = fd)
  c0 <- rev_coef("FDY-L3-LV")
  expect_equal(c0$estimate, unname(coef(f)["dg"]), tolerance = 1e-9)
  expect_true(is.nan(c0$boot_p))                                          # EXPLORATORY: no inference by design
  expect_equal(c0$boot_note, SGS_NO_INFERENCE_NOTE)
  expect_equal(r[["FDY-L3-LV"]]$label, "EXPLORATORY")
  frm <- as.formula(paste("dy ~ 0 + dg +", paste0("d_", SGS_L_CONTROLS, collapse = " + ")))
  f <- lm(frm, data = fd)
  expect_equal(rev_coef("R-FD-L3-LV")$estimate, unname(coef(f)["dg"]), tolerance = 1e-9)
  # leave one year out of the differences, leave one sector out of the base sample
  sub <- Filter(function(c) identical(c$test_id, "FDY-LOYO-L3-LV") && !is.null(c$left_out), rev_env$out$coef_rows)
  expect_equal(sort(vapply(sub, `[[`, "", "left_out")), sort(sgs_int_str(unique(fd$year))))
  for (s in sub) {
    z <- fd[fd$year != as.numeric(s$left_out), ]
    expect_equal(s$estimate, unname(coef(lm(dy ~ dg + factor(year), data = z))["dg"]), tolerance = 1e-9, info = s$left_out)
    expect_true(is.nan(s$boot_p))
  }
  sub <- Filter(function(c) identical(c$test_id, "R-LOSO-L3-LV") && !is.null(c$left_out), rev_env$out$coef_rows)
  expect_equal(length(sub), length(unique(df$study_sector)))
  s1 <- sub[[1]]
  z <- df[df$study_sector != s1$left_out, ]
  f <- lm(y ~ predicted_growth_pct + pres_year + midterm_year + exp_dem_house + exp_dem_senate + cur_dem_house + cur_dem_senate +
            factor(study_sector), data = z)
  expect_equal(s1$estimate, unname(coef(f)[g]), tolerance = 1e-9)
  # the lm() blocks of the summaries equal the pipeline for the matched variants too
  chk <- rev_env$out$summary_checks
  expect_true(all(chk$agree[chk$test_id %in% c("R-yearFE-L3-LV", "R-logFE-L3-LV", "FDY-L3-LV", "R-FD-L3-LV")]))
})

test_that("a matched variant of a base that is not estimable is not estimable, and says why", {
  spec <- sgs_registry(PAUL)[["FDY-L3-LV"]]
  bd <- sgs_decision(SGS_NOT_ESTIMABLE, attempts = list(), reason = "too few years")
  d <- sgs_decide_matched(spec, bd, built = list(lobbyview_all = list(built = TRUE)))
  expect_equal(d$status, SGS_NOT_ESTIMABLE)
  expect_match(d$reason, "matched to L3-LV, which is NOT ESTIMABLE", fixed = TRUE)
  d <- sgs_decide_matched(spec, bd, built = list())
  expect_equal(d$status, SGS_NOT_BUILT)
})

test_that("incremental fit: adjusted R^2 with and without the focal term equal summary(lm()) on the same rows", {
  df <- rev_sample("L3-LV")
  full <- lm(y ~ predicted_growth_pct + pres_year + midterm_year + exp_dem_house + exp_dem_senate + cur_dem_house +
               cur_dem_senate + factor(study_sector), data = df)
  red <- update(full, . ~ . - predicted_growth_pct)
  c0 <- rev_coef("L3-LV")
  expect_equal(c0$adj_r2_with, summary(full)$adj.r.squared, tolerance = 1e-10)
  expect_equal(c0$adj_r2_without, summary(red)$adj.r.squared, tolerance = 1e-10)
  expect_equal(c0$r2_increment, summary(full)$r.squared - summary(red)$r.squared, tolerance = 1e-10)
  expect_equal(c0$partial_r2, (deviance(red) - deviance(full)) / deviance(red), tolerance = 1e-10)
  # no intercept (R-FD) and weights: the same formulas as summary.lm
  set.seed(3)
  n <- 40
  d <- data.frame(y = rnorm(n), x = rnorm(n), z = rnorm(n), s = rep(c("a", "b", "c", "d"), each = 10), yr = rep(2011:2020, 4),
                  w = runif(n, 0.5, 2))
  for (case in c("uncentered", "weighted")) {
    X <- if (case == "uncentered") cbind(x = d$x, z = d$z) else cbind(x = d$x, z = d$z, sapply(c("a", "b", "c", "d"), function(v) as.numeric(d$s == v)))
    colnames(X) <- if (case == "uncentered") c("x", "z") else c("x", "z", paste0("FE:", c("a", "b", "c", "d")))
    raw <- list(y = d$y, X = X, names = colnames(X), clusters = match(d$s, c("a", "b", "c", "d")) - 1L, years = d$yr,
                intercept_spanned = case == "weighted", w = if (case == "weighted") d$w else NULL)
    dfit <- sgs_weighted_design(raw)
    fit <- sgs_ols(dfit)
    dg <- sgs_term_diagnostics(dfit, fit, "x", intercept = case == "weighted", design_raw = raw)$x
    m <- if (case == "uncentered") lm(y ~ 0 + x + z, data = d) else lm(y ~ x + z + factor(s), data = d, weights = w)
    m0 <- if (case == "uncentered") lm(y ~ 0 + z, data = d) else lm(y ~ z + factor(s), data = d, weights = w)
    expect_equal(dg$adj_r2_with, summary(m)$adj.r.squared, tolerance = 1e-10, info = case)
    expect_equal(dg$adj_r2_without, summary(m0)$adj.r.squared, tolerance = 1e-10, info = case)
  }
})

test_that("two-way (sector + year) sensitivity and temporal support of a focal term", {
  df <- rev_sample("L3-LV")
  f <- lm(y ~ predicted_growth_pct + pres_year + midterm_year + exp_dem_house + exp_dem_senate + cur_dem_house + cur_dem_senate +
            factor(study_sector), data = df)
  X <- model.matrix(f); u <- residuals(f); A <- solve(crossprod(X)); n <- nrow(X); p <- ncol(X)
  cr <- function(cl) { G <- length(unique(cl)); S <- rowsum(X * u, cl); G / (G - 1) * (n - 1) / (n - p) * A %*% crossprod(S) %*% A }
  V <- cr(df$study_sector) + cr(df$year) - cr(paste(df$study_sector, df$year))
  c0 <- rev_coef("L3-LV")
  expect_equal(c0$se_2way, sqrt(V["predicted_growth_pct", "predicted_growth_pct"]), tolerance = 1e-8)
  G <- min(length(unique(df$study_sector)), length(unique(df$year)))
  expect_equal(c0$df_2way, G - 1)
  expect_equal(c0$p_2way, 2 * pt(-abs(c0$estimate / c0$se_2way), G - 1), tolerance = 1e-12)
  expect_match(c0$temporal_support, paste0("^", length(unique(df$year)), " distinct years"))
  # the year shares of the absolute OLS weight sum to 100%
  w <- (A %*% t(X))["predicted_growth_pct", ]
  sh <- tapply(abs(w), df$year, sum) / sum(abs(w))
  top <- names(sort(-sh))[1]
  expect_match(c0$temporal_support, paste0("share of the absolute OLS weight: ", top, " "), fixed = TRUE)
  # a year-level indicator names its years (H1-PV: pres_year = 1 in one year)
  raw <- list(y = rnorm(20), X = cbind(pres_year = rep(c(0, 0, 0, 1, 0), 4), `FE:a` = rep(c(1, 0), each = 10), `FE:b` = rep(c(0, 1), each = 10)),
              names = c("pres_year", "FE:a", "FE:b"), clusters = rep(0:1, each = 10), years = rep(2021:2025, 4), intercept_spanned = TRUE)
  fit <- sgs_ols(raw)
  dg <- sgs_term_diagnostics(raw, fit, "pres_year", intercept = TRUE)$pres_year
  expect_match(dg$temporal_support, "pres_year = 1 in 1 of 5 years (2024)", fixed = TRUE)
  expect_match(dg$twoway_note, "not computed: 2 sector and 5 year clusters", fixed = TRUE)
  expect_true(is.na(dg$se_2way))
})

test_that("DESCRIPTIVE term labels: per-sector slopes rest on one cluster; the trends headline shows no p for them", {
  cs <- Filter(function(c) identical(c$test_id, "SLOPES-L3-LV") && is.null(c$left_out) && !identical(c$test, "joint"), rev_env$out$coef_rows)
  expect_true(length(cs) >= 3)
  expect_true(all(vapply(cs, function(c) identical(c$term_label, SGS$ONE_CLUSTER_LABEL), TRUE)))
  expect_equal(rev_coef("L3-LV")$term_label, "")
  expect_equal(rev_coef("FDY-L3-LV")$term_label, "DESCRIPTIVE")
  md <- sgs_trends_md(rev_env$out$trends)
  row <- md[startsWith(md, "| SLOPES-L3-LV |")][1]
  expect_match(row, paste0("EXTENSION; ", SGS$ONE_CLUSTER_LABEL), fixed = TRUE)
  expect_match(row, "| n/a (DESCRIPTIVE) | n/a (DESCRIPTIVE) |", fixed = TRUE)
  txt <- readLines(rev_env$out$summaries, encoding = "UTF-8")
  expect_true(any(startsWith(txt, paste0("    term label        ", SGS$ONE_CLUSTER_LABEL))))
  expect_true(any(startsWith(txt, "    incremental fit   adjusted R^2 ")))
  expect_true(any(startsWith(txt, "    two-way SE        ")))
  expect_true(any(startsWith(txt, "    temporal support  ")))
})

test_that("Holm within pre-specified families: p.adjust over the ESTIMABLE, non-DESCRIPTIVE terms; unadjusted p kept", {
  est <- list(list(test_id = "L1-LV", status = SGS_ESTIMABLE), list(test_id = "L2-LV", status = SGS_ESTIMABLE),
              list(test_id = "L3-LV", status = SGS_ESTIMABLE), list(test_id = "C1", status = SGS_NOT_ESTIMABLE),
              list(test_id = "C2", status = SGS_ESTIMABLE), list(test_id = "C3", status = SGS_ESTIMABLE))
  cr <- function(id, p, lab = "") list(test_id = id, coefficient = "g", focal = TRUE, boot_p = p, term_label = lab)
  coef <- list(cr("L1-LV", 0.745874587458746), cr("L2-LV", 0.952695269526953), cr("L3-LV", 0.0375037503750375),
               cr("C2", 0.02), cr("C3", 0.04, "DESCRIPTIVE"))
  h <- sgs_holm_table(est, coef)
  lv <- h[h$family == "L-LV growth timing", ]
  expect_equal(lv$holm_p, p.adjust(c(0.745874587458746, 0.952695269526953, 0.0375037503750375), "holm"))
  expect_equal(lv$holm_p[lv$test_id == "L3-LV"], 0.112511251125113, tolerance = 1e-12)   # the Codex review's number
  expect_equal(lv$p_unadjusted[lv$test_id == "L3-LV"], 0.0375037503750375)
  cc <- h[h$family == "C growth timing", ]
  expect_equal(cc$not_estimable_members[1], "C1")
  expect_equal(cc$holm_p[cc$test_id == "C2"], 0.02)                      # C3 is DESCRIPTIVE: not in the family, m = 1
  expect_true(is.na(cc$holm_p[cc$test_id == "C3"]))
  expect_match(cc$note[cc$test_id == "C3"], "no inference, not in the family", fixed = TRUE)
  expect_true(all(h$note[h$family == "SHIFT (pre-specified)"] == "no ESTIMABLE member in this run") || !any(h$family == "SHIFT (pre-specified)"))
  # the live run's Holm p is attached to the coefficient rows and the trends
  c0 <- rev_coef("L3-LV")
  expect_equal(c0$holm_family, "L-LV growth timing")
  expect_true(is.finite(c0$holm_p))
})

test_that("the Codex review's numbers: MATCH within 1e-6, MISMATCH otherwise", {
  est <- list(); coef <- list()
  for (id in names(SGS_CODEX_REVIEW)) {
    k <- sub("^L([123])-LV$", "\\1", id); g <- SGS_GROWTH[[k]]; ref <- SGS_CODEX_REVIEW[[id]]
    est[[length(est) + 1L]] <- list(test_id = id, n = ref[["base_n"]], status = SGS_ESTIMABLE)
    est[[length(est) + 1L]] <- list(test_id = paste0("FDY-", id), n = ref[["fdy_n"]], status = SGS_ESTIMABLE)
    coef[[length(coef) + 1L]] <- list(test_id = id, coefficient = g, estimate = ref[["base"]], boot_p = ref[["p"]],
                                      adj_r2_with = ref[["adj_with"]], adj_r2_without = ref[["adj_without"]], partial_r2 = ref[["partial"]])
    coef[[length(coef) + 1L]] <- list(test_id = paste0("R-yearFE-", id), coefficient = g, estimate = ref[["yearfe"]])
    coef[[length(coef) + 1L]] <- list(test_id = paste0("R-logFE-", id), coefficient = g, estimate = ref[["logfe"]] * (1 + 1e-9))
    coef[[length(coef) + 1L]] <- list(test_id = paste0("FDY-", id), coefficient = g, estimate = ref[["fdy"]])
  }
  holm <- data.frame(family = "L-LV growth timing", test_id = names(SGS_CODEX_REVIEW),
                     holm_p = vapply(SGS_CODEX_REVIEW, function(r) r[["holm"]], 0), stringsAsFactors = FALSE)
  chk <- sgs_codex_check(est, coef, holm)
  expect_equal(nrow(chk), 33)
  expect_true(all(chk$verdict == "MATCH"))
  coef[[4]]$estimate <- SGS_CODEX_REVIEW[["L1-LV"]][["fdy"]] * 1.01
  chk <- sgs_codex_check(est, coef, holm)
  expect_equal(chk$verdict[chk$test == "L1-LV" & grepl("FDY\\)$", chk$quantity)], "MISMATCH")
  expect_true(any(grepl("## Codex methodology review: reproduction of its numbers", readLines(rev_env$out$report), fixed = TRUE)))
})

test_that("chronology: measured_at / available_at / after_year of expected control; STRICT leaves the late values out", {
  expect_equal(sgs_date_text("2026-09-24/25"), "2026-09-25")
  expect_equal(sgs_date_text("2024-11-04"), "2024-11-04")
  expect_equal(sgs_date_text("2026-08"), "2026-08-31")
  expect_equal(sgs_date_text("2024-02"), "2024-02-29")
  expect_equal(sgs_date_text(as.Date("2021-12-31")), "2021-12-31")
  expect_true(is.na(sgs_date_text(NA)))
  sy <- rev_env$out$tables$sector_year
  r <- function(y) sy[sy$study_sector == "commercial_banks" & sy$year == y, ]
  expect_equal(r(2023)$exp_dem_house_measured_at, "2024-11-04")
  expect_true(r(2023)$exp_dem_house_after_year)
  expect_false(r(2024)$exp_dem_senate_after_year)
  expect_equal(r(2025)$exp_dem_senate_measured_at, "2026-09-25")
  expect_true(r(2025)$exp_dem_senate_after_year)
  expect_equal(r(2025)$exp_dem_senate_available_at, r(2025)$exp_dem_senate_measured_at)
  # the base test carries the retrospective label (2023 is in its sample); the STRICT variant drops 2023
  expect_match(rev_env$rows[["L3-LV"]]$flag, SGS$RETRO_LABEL, fixed = TRUE)
  expect_match(rev_env$rows[["L3-LV"]]$flag, "measured after their year in this sample: 2023", fixed = TRUE)
  st <- rev_env$rows[["STRICT-L3-LV"]]
  expect_match(st$flag, "STRICT timing", fixed = TRUE)
  ss <- sgs_decision_chosen(rev_env$out$decisions[["STRICT-L3-LV"]])$sample$df
  expect_false(any(ss$exp_dem_house_after_year %in% TRUE))
  expect_false(2023 %in% ss$year)
  expect_true(2023 %in% rev_sample("L3-LV")$year)
  tm <- readxl::read_excel(rev_env$out$xlsx, sheet = "expected_control_timing")
  expect_equal(sort(tm$year[tm$after_year %in% c(TRUE, "TRUE")]), c(2023, 2023, 2025, 2025))
  # the parity rule set has no chronology columns
  wbs <- sgs_load_all(rev_env$data, PARITY)
  expect_false("exp_dem_house_measured_at" %in% names(sgs_build_sector_year(wbs, PARITY)))
})

test_that("strict backtest: a value not available by the origin never enters a strict forecast (changing it changes nothing)", {
  set.seed(9)
  mk <- function(bump = 0) {
    rows <- list()
    for (s in c("a_sector", "b_sector", "c_sector")) {
      y <- 10 * match(s, c("a_sector", "b_sector", "c_sector"))
      for (t in 2008:2023) {
        pres <- as.numeric(t %% 4 == 0); mid <- as.numeric(t %% 4 == 2)
        g <- sin(t + nchar(s)) + bump * cos(3 * t)   # not absorbed by a sector baseline or a rescaling
        y <- y + 0.4 + 2 * pres - 1.1 * mid + 0.3 * g + rnorm(1, 0, 0.3)
        rows[[length(rows) + 1L]] <- list(study_sector = s, year = t, y = y, pres_year = pres, midterm_year = mid,
                                          growth_previous_year_pct = g, predicted_growth_pct = cos(t))
      }
    }
    d <- .rows_df(rows)
    d$y_lag <- d$y[match(paste(d$study_sector, d$year - 1), paste(d$study_sector, d$year))]
    d$dy <- d$y - d$y_lag
    for (v in c("exp_dem_house", "exp_dem_senate", "cur_dem_house", "cur_dem_senate", "contracted_prior")) d[[v]] <- NA_real_
    d$position <- .fc_position(d$pres_year, d$midterm_year)
    d$avail__y <- as.Date(paste0(d$year + 1, "-01-20"))
    for (v in SGS_FC_TERMS) d[[paste0("avail__", v)]] <- as.Date(NA)
    d$avail__pres_year <- as.Date("1900-01-01"); d$avail__midterm_year <- as.Date("1900-01-01")
    d$avail__growth_previous_year_pct <- as.Date("2026-08-31")               # a 2026 vintage: after every origin
    d$avail__predicted_growth_pct <- as.Date(paste0(d$year - 1, "-11-30"))
    d
  }
  set.seed(9); p0 <- mk(0)
  set.seed(9); p1 <- mk(5)                                                  # the late growth values differ (and y, reset below)
  p1$y <- p0$y; p1$y_lag <- p0$y_lag; p1$dy <- p0$dy                        # keep the outcomes identical
  s0 <- sgs_fc_backtest(p0, 2014:2023, "toy", strict = TRUE)$rows
  s1 <- sgs_fc_backtest(p1, 2014:2023, "toy", strict = TRUE)$rows
  expect_equal(s0$forecast, s1$forecast)                                    # strict: the late growth values never enter
  expect_true(all(s0$timing == "strict"))
  m2 <- s0[s0$model == "2b", ]                                              # (2b) = the earlier model (2): needs prior-year growth
  expect_true(all(is.na(m2$forecast)))
  expect_match(m2$reason[1], "strict: values available by", fixed = TRUE)
  expect_true(all(!is.na(s0$forecast[s0$model %in% c("0", "0s", "1", "2a")])))   # (2a): predicted growth is dated before every origin
  r0 <- sgs_fc_backtest(p0, 2014:2023, "toy")$rows
  r1 <- sgs_fc_backtest(p1, 2014:2023, "toy")$rows
  expect_false(isTRUE(all.equal(r0$forecast[r0$model == "2b"], r1$forecast[r1$model == "2b"])))   # retrospective: they do
  expect_true(isTRUE(all.equal(r0$forecast[r0$model == "2a"], r1$forecast[r1$model == "2a"])))    # (2a) never reads prior-year growth
  # the live run reports both timings and the as-of table
  fc <- rev_env$out$forecast
  expect_true(isTRUE(fc$strict))
  expect_setequal(unique(fc$rows$timing), c("retrospective", "strict"))
  expect_true(all(c("variable", "n_available_at_origin", "origin") %in% names(fc$asof)))
  expect_true(all(fc$asof$origin == paste0(fc$asof$target_year, "-02-01")))
  md <- paste(readLines(rev_env$out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, "#### strict (every value available by the origin, 1 February of the target year)", fixed = TRUE)
  expect_match(md, "#### retrospective (final-vintage predictors)", fixed = TRUE)
})

test_that("fit table: every block's adjusted R^2 against the previous run, with the reason for a difference", {
  fit2 <- rev_env$out2$fit
  info <- attr(fit2, "info")
  expect_equal(info$previous_run, "analysis-R-20260101T000000Z")
  expect_true(all(fit2$direction == "same"))
  expect_true(all(fit2$reason == "unchanged"))
  expect_equal(nrow(fit2), info$blocks)
  f1 <- rev_env$out$fit
  expect_true(all(f1$direction == "no previous run"))
  # printed values: as summary() prints them
  txt <- readLines(rev_env$out$summaries, encoding = "UTF-8")
  i <- which(startsWith(txt, "==== L3-LV  [CORE]"))
  rl <- txt[i:length(txt)][grep("^Multiple R-squared", txt[i:length(txt)])[1]]
  expect_match(rl, paste0("Adjusted R-squared:  ", f1$adj_r2_printed[f1$test_id == "L3-LV"]), fixed = TRUE)
  expect_equal(f1$adj_r2[f1$test_id == "L3-LV"], rev_coef("L3-LV")$adj_r2_with, tolerance = 1e-12)
  # a third run on changed inputs: the reason names the changed workbook
  # the same input files, except 01 with the credit-union LobbyView amounts scaled (the xlsx bytes of a rebuilt world differ)
  data3 <- file.path(rev_env$base, "data3")
  dir.create(data3)
  file.copy(list.files(rev_env$data, full.names = TRUE), data3)
  p01 <- file.path(data3, "01_lobbying_expenditures.xlsx")
  d01 <- as.data.frame(readxl::read_excel(p01, sheet = "data"))
  sgs_write_xlsx(p01, setNames(list(d01, rev_lv_sheet(scale = c(credit_unions = 1.3))), c("data", SGS$LOBBYVIEW_ALL_SHEET)))
  out3 <- quiet_run(data_dir = data3, results_dir = rev_env$res, B = 99, only = "L3-LV", rules = PAUL, run_id = "analysis-R-20260103T000000Z")
  f3 <- out3$fit
  expect_equal(attr(f3, "info")$previous_run, "analysis-R-20260102T000000Z")
  x <- f3[f3$test_id == "L3-LV", ]
  expect_match(x$reason, "same DV, formula, sectors, years and n; inputs changed: 01_lobbying_expenditures.xlsx", fixed = TRUE)
  expect_true(x$direction %in% c("lower", "higher", "same"))
  expect_true(all(f3$direction[f3$test_id != "L3-LV"] == "not in this run"))
  # the parser reads the summaries file back
  ps <- sgs_parse_summaries(rev_env$out$summaries)
  expect_true(all(c("L3-LV", "FDY-L3-LV", "R-yearFE-L3-LV") %in% ps$test_id))
  expect_equal(ps$formula[ps$test_id == "FDY-L3-LV"], "d_lobby_lv_real_m ~ d_predicted_growth_pct + factor(year)")
  expect_true(any(ps$block[ps$test_id == "FDY-LOYO-L3-LV"] != ""))
})

test_that("money: the 04 measure is labelled included receipts, with its composition and the conduit caveat", {
  expect_match(rev_env$rows[["L3-LV"]]$dv_label, "LobbyView", fixed = TRUE)
  wbs <- sgs_load_all(rev_env$data, PAUL)
  md <- sgs_money_md(wbs)
  expect_match(md[1], SGS$MONEY_LABEL, fixed = TRUE)
  expect_true(any(grepl("^- By funding_source: employee_original", md)))
  expect_true(any(grepl("SHIFT-All is D / (D + R) within the party-labelled 100.00% of the dollars", md, fixed = TRUE)))
  expect_true(any(grepl("08 notes n6", md, fixed = TRUE)))
  expect_match(SGS$MONEY_LABEL, "organization_unverified, non_giving", fixed = TRUE)
  expect_match(sgs_registry(PAUL)[["R-dedup-C1"]]$dv_label, "excluding own-PAC receipts", fixed = TRUE)
})

test_that("outputs of the revision: sheets, receipt fields and Glass Box stage; the parity rule set has none", {
  sh <- readxl::excel_sheets(rev_env$out$xlsx)
  for (s in c("fit", "multiplicity", "codex_review_check", "expected_control_timing", "forecast_asof", "trends")) expect_true(s %in% sh, info = s)
  co <- readxl::read_excel(rev_env$out$xlsx, sheet = "coefficients")
  expect_true(all(SGS_COEF_DIAG_COLS %in% names(co)))
  rc <- jsonlite::fromJSON(rev_env$out$receipt)
  expect_true(is.null(rc$fit$previous_run) || is.na(rc$fit$previous_run))
  expect_equal(rc$codex_review$checks, 33)
  expect_equal(rc$multiplicity$sheet, "multiplicity")
  expect_true(length(rc$chronology$measured_after_year) >= 4)
  expect_equal(rc$forecast$timings, c("retrospective", "strict"))
  rc2 <- jsonlite::fromJSON(rev_env$out2$receipt)
  expect_equal(rc2$fit$previous_run, "analysis-R-20260101T000000Z")
  base <- tmp_dir()
  oq <- quiet_run(data_dir = rev_env$data, results_dir = file.path(base, "r"), B = 99, only = "L1-LV", rules = PARITY)
  expect_null(oq$fit); expect_null(oq$holm)
  shq <- readxl::excel_sheets(oq$xlsx)
  expect_false(any(c("fit", "multiplicity", "codex_review_check", "expected_control_timing") %in% shq))
  expect_false(any(SGS_COEF_DIAG_COLS %in% names(readxl::read_excel(oq$xlsx, sheet = "coefficients"))))
})
