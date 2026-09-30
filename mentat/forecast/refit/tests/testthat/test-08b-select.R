# Rule auto-pick (Paul's ruling 2026-09-30): for each term run the no-leakage backtests for R0 pooled / R1 own / R2 DL blend in
# BOTH designs (leave-one-election-out and chronological; lobbying has its one rolling-origin design), choose the rule with the
# lowest MAE in both designs, use R2 when the designs disagree, and report R0 when R2 resolves to the pooled slope.
# Library code: not wired into the v1 parity bundle.

test_that("the SPEC section 8 comparison table is returned for PAC, with R1 chosen in both designs", {
  sp <- test_specs()
  sel <- rf_select_rule(sp$pac, path = "prevchg")
  expect_identical(sel$choice, "R1")
  expect_identical(sel$reported_rule, "R1")
  expect_identical(sort(sel$designs), c("chrono", "loeo"))
  tab <- sel$table
  get <- function(ds, rule) tab$MAE[tab$design == ds & tab$rule == rule]
  expect_equal(round(c(get("loeo", "R0"), get("loeo", "R1"), get("loeo", "R2"), get("loeo", "naive_prev")), 3), c(21.918, 10.765, 14.349, 12.712))
  expect_equal(round(c(get("chrono", "R0"), get("chrono", "R1"), get("chrono", "R2"), get("chrono", "naive_prev")), 3), c(32.481, 14.314, 21.585, 12.337))
  expect_identical(sel$winner_by_design[["loeo"]], "R1")
  expect_identical(sel$winner_by_design[["chrono"]], "R1")
  expect_match(sel$reason, "lowest MAE in both designs")
  expect_true(all(c("term", "design", "rule", "n", "folds", "MAE", "RMSE", "units") %in% names(tab)))
})

test_that("on today's data control_House has disagreeing designs, so R2 is used and resolves to the pooled slope (reported R0)", {
  sp <- test_specs()
  sel <- rf_select_rule(sp$control_House.selected, path = "calc")
  expect_identical(sel$winner_by_design[["loeo"]], "R1")      # own slopes win leave-one-election-out ...
  expect_identical(sel$winner_by_design[["chrono"]], "R2")    # ... the blend wins chronologically
  expect_identical(sel$choice, "R2")                          # designs disagree -> R2
  expect_identical(sel$tau2_full_sample, 0)                   # full-sample tau2 = 0, so R2 == R0 ...
  expect_identical(sel$reported_rule, "R0")                   # ... and the pooled slope is reported
  expect_match(sel$reason, "disagree")
})

test_that("the literal rule picks own slopes for control_Senate and lobbying on today's data (margins of 1.2% and 0.8%)", {
  sp <- test_specs()
  sen <- rf_select_rule(sp$control_Senate.selected, path = "calc")
  expect_identical(unname(sen$winner_by_design), c("R1", "R1"))
  expect_identical(sen$choice, "R1")
  lob <- rf_select_rule(sp$lobby, path = "calc")
  expect_identical(lob$designs, "rolling")
  expect_identical(lob$choice, "R1")
  # the measured margins behind that statement
  g <- function(sel, ds, rule) sel$table$MAE[sel$table$design == ds & sel$table$rule == rule]
  expect_equal(g(sen, "loeo", "R0"), 6.118, tolerance = 1e-3); expect_equal(g(sen, "loeo", "R1"), 6.044, tolerance = 1e-3)
  expect_equal(g(lob, "rolling", "R0"), 4.304, tolerance = 1e-3); expect_equal(g(lob, "rolling", "R1"), 4.271, tolerance = 1e-3)
})

test_that("with a 5% clear-winner margin the choices are R1 for PAC and pooled for control and lobbying", {
  sp <- test_specs()
  expect_identical(rf_select_rule(sp$pac, path = "prevchg", min_gain = 0.05)$reported_rule, "R1")
  for (k in c("control_House.selected", "control_Senate.selected", "lobby")) {
    sel <- rf_select_rule(sp[[k]], path = "calc", min_gain = 0.05)
    expect_identical(sel$choice, "R2", info = k)
    expect_identical(sel$reported_rule, "R0", info = k)
  }
})

test_that("an exact R0 / R2 tie is reported as R0, and ties never hand the win to a rule that did not earn it (unit)", {
  mk <- function(mae) data.frame(design = rep(c("loeo", "chrono"), each = 4), rule = rep(c("R0", "R1", "R2", "naive_prev"), 2), MAE = mae, stringsAsFactors = FALSE)
  # R0 and R2 tie in both designs, R1 worse: choice is R2 (simplest of the tied pair is R0)
  r <- rf_choose_rule(mk(c(2, 3, 2, 4, 2, 3, 2, 4)), designs = c("loeo", "chrono"))
  expect_identical(r$choice, "R0")
  # R1 lowest in one design only -> disagree -> R2
  r2 <- rf_choose_rule(mk(c(2, 1, 2, 4, 2, 3, 2, 4)), designs = c("loeo", "chrono"))
  expect_identical(r2$choice, "R2")
  # R1 lowest in both -> R1
  r3 <- rf_choose_rule(mk(c(2, 1, 2, 4, 2, 1, 2, 4)), designs = c("loeo", "chrono"))
  expect_identical(r3$choice, "R1")
  # a single design decides alone
  r4 <- rf_choose_rule(mk(c(2, 1, 2, 4, 2, 1, 2, 4))[1:4, ], designs = "loeo")
  expect_identical(r4$choice, "R1")
})

test_that("the selection table and choice are deterministic and independent of call order (negative control)", {
  sp <- test_specs()
  a <- rf_select_rule(sp$pac, path = "prevchg")
  b <- rf_select_rule(sp$pac, path = "prevchg")
  expect_identical(a$table, b$table)
  expect_identical(a$choice, b$choice)
})
