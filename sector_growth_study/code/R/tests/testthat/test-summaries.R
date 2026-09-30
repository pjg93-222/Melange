# R port only (Paul, 2026-09-26): results/summaries_<run>.txt prints summary(lm(...)) for every ESTIMABLE test,
# exactly as R prints it, with the study's inference under each; the lm() focal coefficient equals the pipeline's
# estimate.

sm_env <- local({
  base <- tmp_dir()
  data <- synth_build(file.path(base, "data"))
  write_champions(data, champions_frame(slope = 5000.0, noise = 500.0), age_minutes = 30)
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "results"), B = 99, run_id = "analysis-test-summaries",
                   only = c("C1", "L1", "T1", "R-log-C1", "R-yearFE-C1", "R-FD-C1", "R-LOSO-C1", "H1-C1", "H5-pooled",
                            "H5-within", "H1-PV"), rules = PARITY)
  list(out = out, txt = readLines(out$summaries, encoding = "UTF-8"))
})

test_that("every ESTIMABLE test has a summary block headed by its id and label, in label order", {
  est <- Filter(function(r) r$status == SGS_ESTIMABLE, sm_env$out$est_rows)
  expect_gt(length(est), 15)
  heads <- grep("^==== ", sm_env$txt, value = TRUE)
  for (r in est) {
    expect_true(any(startsWith(heads, paste0("==== ", r$test_id, "  [", r$label, "]"))), info = r$test_id)
  }
  lab <- sub("^==== \\S+  \\[([A-Z]+)\\].*$", "\\1", heads)
  expect_true(all(diff(match(lab, SGS_SUMMARY_LABEL_ORDER)) >= 0))  # CORE, DESCRIPTIVE, EXTENSION, ROBUSTNESS, EXPLORATORY, PREVIEW
  expect_true(any(grepl("R-LOSO-C1  [ROBUSTNESS]  - without commercial_banks", heads, fixed = TRUE)))
})

test_that("each block is the real summary.lm print followed by the study's inference", {
  txt <- sm_env$txt
  nb <- length(grep("^==== ", txt))
  for (pat in c("^Call:$", "^Residuals:$", "^Coefficients:", "^Signif\\. codes:", "^Residual standard error: .* on [0-9]+ degrees of freedom",
                "^Multiple R-squared: ", "^F-statistic: .* on [0-9]+ and [0-9]+ DF,  p-value: ", "^--- Study inference")) {
    expect_equal(length(grep(pat, txt)), nb, info = pat)
  }
  expect_true(any(grepl("^    CR1 SE ", txt)))
  expect_true(any(grepl("^    bootstrap p ", txt)))
  expect_true(any(grepl("^    bootstrap 95% CI ", txt)))
  expect_true(any(grepl("^    strata            STRATIFIED", txt)))
  expect_true(any(grepl("inference         none \\(DESCRIPTIVE\\)", txt)))  # L1-LV in the parity rule set
  expect_true(any(grepl("not defined because of singularities", txt)))       # H5-within: absorbed controls
  # not hand-formatted: the printed block equals capture.output(summary(lm())) of the same formula and data
  spec <- sm_env$out$registry[["C1"]]
  att <- sgs_decision_chosen(sm_env$out$decisions[["C1"]])
  op <- options(width = SGS_SUMMARY_WIDTH)   # the summaries print at this console width
  printed <- utils::capture.output(summary(sgs_fit_lm(sgs_lm_sector_year(spec, att$sample$df))))
  options(op)
  i <- which(startsWith(txt, "==== C1  [CORE]"))
  expect_equal(txt[(i + 5):(i + 4 + length(printed))], printed)
  flat <- gsub("\\s+", "", paste(printed, collapse = ""))
  expect_match(flat, "lm(formula=contributions_real_m~growth_previous_year_pct+pres_year+midterm_year+exp_dem_house+exp_dem_senate+factor(study_sector),data=sample)", fixed = TRUE)
})

test_that("the lm() focal coefficient equals the pipeline estimate for every focal term of every block", {
  chk <- sm_env$out$summary_checks
  expect_length(attr(chk, "errors"), 0)
  expect_false(anyNA(chk$lm_estimate))
  expect_true(all(chk$agree))
  expect_lt(max(chk$rel_diff[!chk$zero_both]), 1e-8)
  # zero-to-rounding is only the synthetic 'any' outcome: every synthetic champion gives, so as.numeric(dv > 0) is
  # constant and its slopes are 0 in exact arithmetic (both fits print ~1e-17 rounding noise)
  expect_true(all(chk$test_id[chk$zero_both] %in% c("H5-pooled-any", "H5-within-any")))
  expect_true(any(grepl("both are zero to rounding on the outcome's scale", sm_env$txt, fixed = TRUE)))
  # summary()'s own warning on the constant synthetic outcome is printed in the block, as R prints it
  expect_true(any(grepl("^In summary\\.lm\\(fit\\) : essentially perfect fit: summary may be unreliable$", sm_env$txt)))
  expect_false(any(grepl("MISMATCH", sm_env$txt, fixed = TRUE)))
  expect_true(any(grepl("^Check: the lm\\(\\) focal coefficient and residual df equal the pipeline's in every block", sm_env$txt)))
  # the residual df of every lm() fit (LOSO subfits included) equals the pipeline's
  expect_false(anyNA(chk$pipeline_resid_df))
  expect_equal(chk$lm_resid_df, chk$pipeline_resid_df)
  expect_true(any(chk$test_id == "R-LOSO-C1"))
  est_ids <- vapply(Filter(function(r) r$status == SGS_ESTIMABLE, sm_env$out$est_rows), `[[`, "", "test_id")
  expect_setequal(unique(chk$test_id), est_ids)
  for (tid in c("C1", "T1", "R-log-C1", "R-yearFE-C1", "R-FD-C1", "H1-PV", "H5-pooled", "H5-within", "H5-pooled-any", "H1-C1")) {
    rows <- chk[chk$test_id == tid, ]
    expect_gt(nrow(rows), 0)
    pipe <- Filter(function(c) c$test_id == tid && is.null(c$left_out), sm_env$out$coef_rows)
    for (p in pipe) {
      m <- rows[rows$term == p$coefficient, ]
      expect_equal(nrow(m), 1, info = paste(tid, p$coefficient))
      expect_equal(m$lm_estimate, p$estimate, tolerance = 1e-8, info = paste(tid, p$coefficient))
    }
  }
  expect_equal(sort(unique(chk$term[chk$test_id == "T1"])),
               sort(c("growth_previous_year_pct", "growth_previous_year_pct:Chief", "growth_previous_year_pct:Middle Management")))
  expect_true(all(chk$lm_term[chk$test_id == "R-FD-C1"] == "d_growth_previous_year_pct"))
})

test_that("the check flags a focal coefficient or a residual df that differs (negative control)", {
  spec <- sm_env$out$registry[["C1"]]
  att <- sgs_decision_chosen(sm_env$out$decisions[["C1"]])
  sl <- sgs_lm_sector_year(spec, att$sample$df)
  fit <- sgs_fit_lm(sl)
  c0 <- Filter(function(c) c$coefficient %in% spec$focal, sm_env$out$results[["C1"]]$coefs)
  ok <- .summary_block("h", fit, sl$terms, c0, list(), "x", "s", pipeline_df = fit$df.residual)
  expect_true(all(ok$checks$agree))
  expect_false(any(grepl("MISMATCH", ok$lines, fixed = TRUE)))
  off <- c0; off[[1]]$estimate <- off[[1]]$estimate * (1 + 1e-6)
  b1 <- .summary_block("h", fit, sl$terms, off, list(), "x", "s", pipeline_df = fit$df.residual)
  expect_false(b1$checks$agree[1])
  expect_true(any(grepl("; MISMATCH$", b1$lines)))
  b2 <- .summary_block("h", fit, sl$terms, c0, list(), "x", "s", pipeline_df = fit$df.residual + 1)
  expect_false(any(b2$checks$agree))
  b3 <- .summary_block("h", fit, sl$terms, c0, list(), "x", "s")  # df unknown: not a pass
  expect_false(any(b3$checks$agree))
})

test_that("the summaries file is a run output: in the receipt, and never overwritten", {
  rc <- jsonlite::fromJSON(sm_env$out$receipt)
  expect_true(basename(sm_env$out$summaries) %in% rc$outputs$file)
  expect_match(basename(sm_env$out$summaries), "^summaries_analysis-test-summaries\\.txt$")
  # an existing summaries file of the same run id alone blocks the run, and is left as it was
  base <- tmp_dir()
  data <- synth_build(file.path(base, "data"))
  write_champions(data, champions_frame(slope = 5000.0, noise = 500.0), age_minutes = 30)
  res <- file.path(base, "results")
  dir.create(res, recursive = TRUE, showWarnings = FALSE)
  clash <- file.path(res, "summaries_analysis-test-clash.txt")
  writeLines("kept", clash)
  expect_error(quiet_run(data_dir = data, results_dir = res, B = 99, run_id = "analysis-test-clash", only = "C1", rules = PARITY),
               "refusing to overwrite an existing result file")
  expect_equal(readLines(clash), "kept")
  expect_false(file.exists(file.path(res, "results_analysis-test-clash.xlsx")))
})
