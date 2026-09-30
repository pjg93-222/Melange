# Gates G4-G9 and the decision (SPEC 3.13 with the rulings of 2026-09-30). The published bundle is v1 today, so G5 / G6 compare the
# refit with it; a v2 bundle published earlier supplies the same numbers through its recorded evidence. Comparisons against a bundle
# built on another platform (BLAS differs at ~1e-14) are tolerance-based, never byte-equal.

published_v1 <- function() v1_bundle()

test_that("G4 sample adequacy: a thin industry is withheld for that model with a stated reason (WARN), everything else adequate", {
  g4 <- test_v2()$adequacy
  expect_identical(g4$gate$status, "WARN")
  tab <- g4$table
  expect_true(all(tab$ok[tab$industry != "auto_light_duty_manufacturing" | tab$model != "lobbying"]))
  a <- tab[tab$industry == "auto_light_duty_manufacturing" & tab$model == "lobbying", ]
  expect_equal(a$n, 1L); expect_false(a$ok)
  w <- g4$withheld$auto_light_duty_manufacturing
  expect_identical(w[[1]]$model, "lobbying")
  expect_match(w[[1]]$reason, "sample adequacy: 1 annual pairs \\(need 5\\)")
  # 6 cycles (control) and 7 (PAC) per industry; pooled residual df and interaction df clear their floors
  expect_true(all(tab$n[tab$model == "pac"] == 7L)); expect_true(all(tab$n[tab$model == "control"] == 6L))
  expect_true(all(tab$pooled_df >= 3L)); expect_true(all(tab$interaction_df >= 2L))
})

test_that("G4 withholds a model whose sample is too small and names it (negative control)", {
  ctx <- test_ctx()
  small <- ctx
  small$pac_panel <- ctx$pac_panel[ctx$pac_panel$cycle_end >= 2020 | ctx$pac_panel$sector != "credit_unions", ]
  g4 <- rf_gate_adequacy(small)
  cu <- g4$table[g4$table$industry == "credit_unions" & g4$table$model == "pac", ]
  expect_equal(cu$n, 3L); expect_false(cu$ok)
  expect_identical(g4$gate$status, "WARN")
  expect_true(any(vapply(g4$withheld$credit_unions, function(w) w$model == "pac", logical(1))))
})

test_that("G5 stability against the published v1: pooled slopes and own slopes keep their signs; leave-one-out sign consistency is reported", {
  v <- test_v2(); b <- test_bundle2()
  g5 <- rf_gate_stability(v, b, published_v1())
  if (g5$gate$status != "PASS") print(g5$table[!g5$table$ok, ])
  tab <- g5$table
  expect_true(any(grepl("pooled slope sign: pac", tab$check)))
  expect_true(any(grepl("existing industry slope sign: PAC commercial_banks", tab$check)))
  expect_true(any(grepl("leave-one-election-out sign consistency: lobby_log", tab$check)))
  expect_true(all(tab$ok[grepl("pooled slope sign|existing industry slope sign", tab$check)]))
  # PAC: every fold keeps the sign (7 of 7 cycles)
  expect_equal(v$sign$pac$loeo$share, 1)
})

test_that("G5 fails a flipped slope and a low sign consistency (negative controls)", {
  v <- test_v2(); b <- test_bundle2()
  flipped <- b; flipped$pac_model$slopes$commercial_banks$applied$beta <- abs(flipped$pac_model$slopes$commercial_banks$applied$beta)
  g <- rf_gate_stability(v, flipped, published_v1())
  expect_identical(g$gate$status, "HOLD")
  expect_match(g$gate$detail, "existing industry slope sign: PAC commercial_banks")
  pub <- published_v1(); pub$pac_model$beta <- -pub$pac_model$beta
  expect_identical(rf_gate_stability(v, b, pub)$gate$status, "HOLD")
  weak <- v; weak$sign$pac$loeo$share <- 0.5
  g2 <- rf_gate_stability(weak, b, published_v1())
  expect_identical(g2$gate$status, "HOLD"); expect_match(g2$gate$detail, "sign consistency: pac")
})

test_that("G6 is the hard backtest gate: PAC improves for every existing industry, and the previous-cycle House share anchor is worse for banks", {
  v <- test_v2()
  g6 <- rf_gate_nondegradation(v, published_v1())
  tab <- g6$table
  pac <- tab[tab$term == "pac", ]
  expect_equal(nrow(pac), 3L)
  expect_true(all(pac$ok))
  expect_equal(pac$new_MAE[pac$industry == "commercial_banks"], 10.81, tolerance = 1e-3)
  expect_equal(pac$published_MAE[pac$industry == "commercial_banks"], 27.74, tolerance = 1e-3)
  expect_equal(pac$published_MAE[pac$industry == "credit_unions"], 15.88, tolerance = 1e-3)
  h <- tab[tab$term == "control_House" & tab$industry == "commercial_banks", ]
  expect_equal(h$new_MAE, 1.54, tolerance = 1e-2); expect_equal(h$published_MAE, 1.05, tolerance = 1e-2)
  expect_false(h$ok)
  expect_identical(g6$gate$status, "HOLD")
  expect_match(g6$gate$detail, "control_House / commercial_banks")
  expect_match(g6$baseline, "v1 calculator recomputed")
})

test_that("G6 passes when the refit equals the published calculator within 1e-9 and fails a hair above it (boundary controls)", {
  v <- test_v2(); b <- test_bundle2()
  self <- rf_gate_nondegradation(v, b)                    # a v2 bundle published earlier supplies its recorded MAE
  expect_identical(self$gate$status, "PASS")
  expect_match(self$baseline, "published bundle")
  pub <- b
  mae <- pub$pac_model$evidence$calculator_path_loeo_mae_by_industry$commercial_banks
  pub$pac_model$evidence$calculator_path_loeo_mae_by_industry$commercial_banks <- mae - 5e-10     # published slightly better, inside the 1e-9 slack
  expect_identical(rf_gate_nondegradation(v, pub)$gate$status, "PASS")
  pub$pac_model$evidence$calculator_path_loeo_mae_by_industry$commercial_banks <- mae - 2e-9      # published better by more than the slack
  expect_identical(rf_gate_nondegradation(v, pub)$gate$status, "HOLD")
})

test_that("G7 validates the bundle against the contract and fails a bad one", {
  b <- test_bundle2()
  expect_identical(rf_gate_bundle(b, test_ctx()$reg)$status, "PASS")
  bad <- b; bad$share_models$seats_House <- list(id = "seats_House")
  expect_identical(rf_gate_bundle(bad, test_ctx()$reg)$status, "FAIL")
  bad <- b; bad$lobby_model$log_refit$beta <- NaN
  expect_identical(rf_gate_bundle(bad, test_ctx()$reg)$status, "FAIL")
  bad <- b; bad$industries$commercial_banks$capabilities$pac <- FALSE; bad$industries$commercial_banks$withheld <- list()
  g <- rf_gate_bundle(bad, test_ctx()$reg)
  expect_identical(g$status, "FAIL"); expect_match(g$detail, "capability 'pac' is false with no withheld reason")
})

test_that("G8 holds until a v2-capable calculator is configured, and follows the command's exit status", {
  p <- file.path(tempdir(), "g8_bundle.json"); writeLines("{}", p)
  expect_identical(rf_gate_consumer(p, cmd = "")$status, "HOLD")
  expect_match(rf_gate_consumer(p, cmd = "")$detail, "HOLD until the v2 calculator exists")
  skip_on_os("windows")
  expect_identical(rf_gate_consumer(p, cmd = "test -n \"$MENTAT_GIVING_MODELS\"")$status, "PASS")
  expect_identical(rf_gate_consumer(p, cmd = "exit 3")$status, "HOLD")
})

test_that("G9 is a warning only: a calculator path that does not beat last-period naive is reported, not blocked", {
  g9 <- rf_gate_naive(test_v2())
  expect_true(g9$status %in% c("PASS", "WARN"))
  expect_false(g9$status %in% c("HOLD", "FAIL"))
  lose <- test_v2(); lose$backtests$MAE[lose$backtests$term == "pac" & lose$backtests$rule == "naive_prev"] <- 1
  g <- rf_gate_naive(lose)
  expect_identical(g$status, "WARN"); expect_match(g$detail, "pac")
})

test_that("decision: any FAIL is FAIL, else any HOLD is HOLD, else PUBLISH; WARN never blocks", {
  mk <- function(...) data.frame(gate = paste0("G", seq_along(c(...))), status = c(...), detail = "", stringsAsFactors = FALSE)
  expect_identical(rf_decision(mk("PASS", "WARN", "PASS")), "PUBLISH")
  expect_identical(rf_decision(mk("PASS", "HOLD", "WARN")), "HOLD")
  expect_identical(rf_decision(mk("HOLD", "FAIL", "PASS")), "FAIL")
})

test_that("all gates of today's refit: HOLD because G6 (House banks, previous-cycle share anchor) and G8 (no v2 calculator) hold; nothing FAILs", {
  v <- test_v2(); b <- test_bundle2()
  base <- data.frame(gate = c("G0 environment", "G1 inputs", "G2 parity", "G3 panel validity"), status = "PASS", detail = "", stringsAsFactors = FALSE)
  g <- rf_gates(v, b, published = published_v1(), base = base, bundle_path = NULL, consumer_cmd = "")
  expect_identical(g$decision, "HOLD")
  st <- stats::setNames(g$gates$status, substr(g$gates$gate, 1, 2))
  expect_identical(st[["G4"]], "WARN"); expect_identical(st[["G5"]], "PASS"); expect_identical(st[["G6"]], "HOLD")
  expect_identical(st[["G7"]], "PASS"); expect_identical(st[["G8"]], "HOLD")
  expect_false(any(g$gates$status == "FAIL"))
  # the finalized bundle carries its own gate summary and still validates against the contract
  b2 <- rf_bundle_v2(v, g$gates)
  expect_identical(b2$gates$decision, "HOLD")
  expect_identical(rf_validate_bundle(b2), character(0))
})

test_that("the default G8 command is MENTAT_G8_CMD when set, else the smoke script when the console's calculator sits beside the pipeline", {
  withr_env <- Sys.getenv("MENTAT_G8_CMD", unset = NA)
  on.exit(if (is.na(withr_env)) Sys.unsetenv("MENTAT_G8_CMD") else Sys.setenv(MENTAT_G8_CMD = withr_env), add = TRUE)
  Sys.setenv(MENTAT_G8_CMD = "exit 0"); expect_identical(rf_g8_default_cmd(), "exit 0")
  Sys.unsetenv("MENTAT_G8_CMD")
  app <- file.path(dirname(dirname(rf_home())), "app", "giving_forecast.py")
  if (file.exists(app) && nzchar(Sys.which("python"))) expect_match(rf_g8_default_cmd(), "g8_consumer_smoke.py", fixed = TRUE)
  else expect_identical(rf_g8_default_cmd(), "")        # a pod snapshot carries mentat/forecast only: G8 holds there, with the reason stated
})
