# The cycle-aware 50/50 model on the R side (owner rulings 2026-10-07: "1. Yes 2. Keep senate in 3. We use the 50/50 4. Yes; Use the IBIS defaults, auto-recalculate").
# The bundle's optional `cycle_model` is produced from the fitted phase block and the pinned inputs; the oracles below are the independent re-fit of the build spec
# (modelspec/targets_1000.json: numpy / scipy on the exported panel, not this code), the build spec's section 4.1 and the 10-01 rebuild's final2_projections.csv.
# The estimation sample is the production one (frozen sample + the property and casualty pilot): the cycle model needs every industry the console offers.

ORACLE <- list(
  pac = list(phi = -0.025004444813599647, se = 0.04069113249489017, df = 15L, b0 = 0.1420506718282655, b1 = -0.05042481960946014, kmax = 3L, d1 = -0.04956364268768301, d2 = -0.08183552723773754,
             pairs = c(2014L, 2016L, 2018L, 2020L),
             step = list(commercial_banks = c(0.0057701438486077485, 4, 3.1824463052837078), credit_unions = c(0.00653943961814239, 4, 3.1824463052837078), property_casualty = c(0.015620883217006524, 4, 3.1824463052837078))),
  general = list(phi = 0.7380555183437122, se = 0.080198425650108, df = 23L, b0 = 0.21854812826899545, b1 = -0.07439625082635988, kmax = 5L, d1 = -0.21295012652389184, d2 = -0.2605637270527622,
                 pairs = c(2014L, 2016L, 2018L, 2020L, 2022L, 2024L),
                 step = list(commercial_banks = c(0.07470106921955001, 6, 2.5705818356363146), credit_unions = c(0.3632584812079982, 6, 2.5705818356363146), property_casualty = c(0.13627189657369346, 6, 2.5705818356363146))))
cycle_of <- function() test_bundle2_pilot()$cycle_model
cycle_controls <- function() Filter(function(c) identical(c$target, "models_cycle"), rf_negative_controls())
cycle_example <- function() jsonlite::fromJSON(file.path(rf_contracts_dir(), "giving-models-v2.cycle.example.json"), simplifyVector = FALSE)

test_that("the cycle model is selected, not assumed: the consistency rule picks the owner-adopted specifications, otherwise the build stops", {
  v <- test_v2_pilot()
  expect_identical(v$phase$pac$consistency$selection$choice, "PT-noG-damp-pool@x22")
  expect_identical(v$phase$general$consistency$selection$choice, "PT-noG-damp-pool")
  cm <- cycle_of()
  expect_identical(cm$measures$pac_to_candidates$candidate, "PT-noG-damp-pool@x22"); expect_identical(cm$measures$pac_to_candidates$handling_2022, "drop")
  expect_identical(cm$measures$general_giving$candidate, "PT-noG-damp-pool"); expect_identical(cm$measures$general_giving$handling_2022, "none")
  expect_identical(cm$measures$pac_to_candidates$open_cycle_layer, "BLEND"); expect_identical(cm$measures$general_giving$open_cycle_layer, "P1")
  bad <- v; bad$phase$pac$consistency$selection$choice <- "PT-G-full-pool"
  expect_error(rf_v2_cycle_model(bad), "not the owner-adopted PT-noG-damp-pool@x22 / PT-noG-damp-pool")
  bad <- v; bad$phase$general$consistency$selection$choice <- "PT-noG-damp-pool@x22"
  expect_error(rf_v2_cycle_model(bad), "owner-adopted")
})

test_that("phi, its standard error and degrees of freedom of both measures equal the independent re-fit (1e-6)", {
  for (nm in c("pac", "general")) {
    m <- cycle_of()$measures[[c(pac = "pac_to_candidates", general = "general_giving")[[nm]]]]; o <- ORACLE[[nm]]
    expect_lt(abs(m$phi - o$phi), 1e-6, label = paste(nm, "phi")); expect_lt(abs(m$phi_se - o$se), 1e-6, label = paste(nm, "SE"))
    expect_identical(m$phi_df, o$df)
  }
  expect_match(cycle_of()$notes[[4]], "phi_gen = 0.738 (the selected specification PT-noG-damp-pool).", fixed = TRUE)   # the Methods text carries 0.738, never the unselected 0.748
  expect_false(any(grepl("0.748", unlist(cycle_of()$notes), fixed = TRUE)))
})

test_that("the damped drift: b0, b1, k_max, the pairs, and d_h = b0 + b1 (k_max + sum of 0.8^j) for h = 1, 2", {
  for (nm in c("pac", "general")) {
    m <- cycle_of()$measures[[c(pac = "pac_to_candidates", general = "general_giving")[[nm]]]]; o <- ORACLE[[nm]]; dr <- m$drift
    expect_identical(dr$kind, "damped_linear_trend"); expect_equal(dr$damp, 0.8); expect_identical(dr$k_max, o$kmax)
    expect_identical(as.integer(unlist(dr$pair_cycles)), o$pairs)
    expect_lt(abs(dr$b0 - o$b0), 1e-6); expect_lt(abs(dr$b1 - o$b1), 1e-6)
    for (h in 1:2) {
      expect_lt(abs(dr$d[[as.character(h)]] - (dr$b0 + dr$b1 * (dr$k_max + sum(0.8^seq_len(h))))), 1e-12)
      expect_lt(abs(dr$d[[as.character(h)]] - o[[paste0("d", h)]]), 1e-6)
    }
  }
})

test_that("the anchored-step residual variance per industry equals the independent re-fit (1e-7), with df = pairs - 1 and the t critical value", {
  for (nm in c("pac", "general")) {
    m <- cycle_of()$measures[[c(pac = "pac_to_candidates", general = "general_giving")[[nm]]]]; o <- ORACLE[[nm]]
    expect_setequal(names(m$step), names(o$step))
    for (id in names(o$step)) {
      s <- m$step[[id]]
      expect_lt(abs(s$sigma2 - o$step[[id]][1]), 1e-7, label = paste(nm, id)); expect_identical(s$pairs, as.integer(o$step[[id]][2]))
      expect_identical(s$df, s$pairs - 1L); expect_lt(abs(s$critical_95 - stats::qt(0.975, s$df)), 1e-12); expect_lt(abs(s$critical_95 - o$step[[id]][3]), 1e-9)
    }
  }
})

test_that("with the budget growth at zero the cycle chain reproduces the 10-01 rebuild's projections: banks PAC 5,782,539.48 and general giving 10,423,757.31 (relative 1e-6)", {
  # anchors of giving-anchors-v1.json (2026-10-07): banks 2024 roster PAC 5,692,500 and general giving 25,915,482.79 nominal, CPI multiplier of the 2024 cycle 1.0410737386804656
  m24 <- 1.0410737386804656
  cm <- cycle_of()
  proj <- function(level, mid) { m <- cm$measures[[mid]]; level * m24 * exp(m$phi * (0 - 1) + m$drift$d$`1`) }       # Pres(2026) - Pres(2024) = -1; x = 0 so the 50/50 factor is 1
  expect_equal(proj(5692500, "pac_to_candidates"), 5782539.48, tolerance = 1e-6)
  expect_equal(proj(25915482.79, "general_giving"), 10423757.31, tolerance = 1e-6)
  # the same through the model's own chain function (the rebuild's route)
  v <- test_v2_pilot()
  G0 <- c(`2024` = 0, `2026` = 0)
  for (k in list(list("pac", 5692500, 5782539.48), list("general", 25915482.79, 10423757.31))) {
    b <- v$phase[[k[[1]]]]
    ch <- rf_ph_chain(b$params, b$step_variance, "commercial_banks", c(2024, 2026), G0)
    expect_equal(k[[2]] * m24 * exp(ch[["log_change"]]), k[[3]], tolerance = 1e-6, label = k[[1]])
  }
})

test_that("the IBISWorld growth paths are REAL, computed from the pinned inputs (banks / credit unions: level ratios; property and casualty: the 2024-11 edition's reported change), one P&C path", {
  g <- cycle_of()$budget_rule$growth
  expect_identical(cycle_of()$budget_rule$weight_model, 0.5); expect_identical(cycle_of()$budget_rule$growth_basis, "real"); expect_identical(cycle_of()$budget_rule$lag_years, 1L)
  expect_setequal(names(g), c("commercial_banks", "credit_unions", "property_casualty"))
  want <- list(commercial_banks = c(0.3592419282, 0.0576696913, -0.0285550820, -0.0283718916, 0.0017896963), credit_unions = c(0.2444760060, 0.1254325563, 0.0401437881, 0.0025697882, 0.0076342784),
               property_casualty = c(0.057, 0.027, 0.026, 0.015, 0.014))
  for (id in names(want)) {
    expect_identical(names(g[[id]]$annual), as.character(2023:2027))
    expect_lt(max(abs(unlist(g[[id]]$annual) - want[[id]])), 1e-9, label = id)
    expect_match(g[[id]]$price_basis, "^CONSTANT_USD")
    expect_match(g[[id]]$source_sha256, "^[0-9a-f]{64}$")
  }
  expect_identical(g$property_casualty$edition, "2024-11"); expect_identical(g$property_casualty$report_id, "52412")
  expect_identical(g$commercial_banks$source_sha256, "86c96b9b0e9c4408784bdfb0b3a987e1fd563cc7e09ad5c09c43b5037a15ccbb")
  expect_identical(g$property_casualty$source_sha256, "83ca21f4726dde52dce37fdd44adb138ff6fef1dafcb41e9f24d6331941e3f0a")
  gp <- cycle_of()$g_prior
  expect_lt(abs(gp$commercial_banks$`2028` - (-1.5495783815)), 1e-9); expect_lt(abs(gp$credit_unions$`2028` - 10.2943295918), 1e-9)
  expect_lt(abs(gp$property_casualty$`2028` - 4.7676613486), 1e-9)                       # the 2024-11 edition's own levels (coordinator ruling: one P&C path), not the constant trajectory's 7.035
})

test_that("the pace series are the pinned roster files in dollars, and the input roles are pinned in the manifest and resolve", {
  p <- cycle_of()$pace
  expect_identical(unlist(p$months), c(`15` = "03-31", `18` = "06-30", `21` = "09-30"))
  expect_identical(names(p$series), c("commercial_banks", "credit_unions"))
  b <- p$series$commercial_banks$cycles
  expect_identical(names(b), as.character(seq(2012, 2024, by = 2)))
  expect_equal(b$`2024`$F, 5692500); expect_equal(b$`2024`$O18, 4497500); expect_equal(b$`2012`$F, 6178695)
  expect_equal(p$series$credit_unions$cycles$`2024`$F, 80800)
  expect_identical(p$series$commercial_banks$sha256, "f847a1a691169183fa4f00c3d4e1d9bdbff68e57b79dfe01dcda979b214eac69")
  expect_identical(p$series$credit_unions$sha256, "161c29111a8ecb795e88a10a4bfd4db12b4cbc76f478d6e93be029befaeb7661")
  inp <- test_inputs()
  roles <- c("cycle:ibis_captured_paths", "cycle:ibis_pc_2024_11", "cycle:pace_banks", "cycle:pace_credit_unions")
  expect_true(all(roles %in% inp$role)); expect_true(all(inp$status[match(roles, inp$role)] %in% c("ok", "ok_from_vault")))
  expect_true(all(inp$purpose[match(roles, inp$role)] == "raw"))
  expect_identical(rf_roots()$CYCLE, file.path(rf_home(), "inputs", "cycle_model"))
  old <- Sys.getenv("RF_ROOT_CYCLE", unset = NA); on.exit(if (is.na(old)) Sys.unsetenv("RF_ROOT_CYCLE") else Sys.setenv(RF_ROOT_CYCLE = old), add = TRUE)
  Sys.setenv(RF_ROOT_CYCLE = "C:/elsewhere"); expect_identical(rf_roots()$CYCLE, "C:/elsewhere")
  Sys.unsetenv("RF_ROOT_CYCLE")
  umb <- Sys.getenv("RF_INPUT_ROOT", unset = NA); on.exit(if (is.na(umb)) Sys.unsetenv("RF_INPUT_ROOT") else Sys.setenv(RF_INPUT_ROOT = umb), add = TRUE)
  Sys.setenv(RF_INPUT_ROOT = "C:/umbrella"); expect_identical(rf_roots()$CYCLE, file.path(rf_home(), "inputs", "cycle_model"))       # the umbrella case keeps the code-side folder
})

test_that("source: window, panel hash (the bytes of the exported panel) and inflation", {
  s <- cycle_of()$source
  expect_identical(as.integer(unlist(s$window_cycles)), c(2012L, 2024L))
  expect_identical(s$panel_sha256, rf_cycle_panel_sha256(test_ctx_pilot()$pac_panel))
  expect_identical(s$panel_sha256, "782a79c3db443f9a17ddde9c943f846dcd879c4da6e502f3f750eb4cc768ea49")      # sha256 of modelspec/panel.csv, the panel the oracles were fitted on
  expect_equal(cycle_of()$inflation$annual_rate, 0.025726436); expect_identical(cycle_of()$inflation$base_year, 2025L)
  expect_identical(cycle_of()$inflation$convention, "cycle_midpoint")
  expect_gte(length(cycle_of()$notes), 4L)
  txt <- paste(unlist(cycle_of()$notes), collapse = " ")
  for (pat in c("No backtest covers the 50/50 overlay", "price basis is inferred as constant dollars", "untested on general giving", "phi_gen = 0.738")) expect_match(txt, pat, fixed = TRUE)
  expect_match(unlist(cycle_of()$measures$general_giving$notes)[2], "two complete cycles (2022, 2024), fewer than the three the pace test needs", fixed = TRUE)
  expect_identical(cycle_of()$measures$pac_to_candidates$notes, list())
})

test_that("the built cycle_model passes the R validator and the contract's Python validator; every models_cycle control is rejected on the example and on the writer's output", {
  b <- test_bundle2_pilot()
  expect_false(is.null(b$cycle_model))
  expect_identical(rf_validate_bundle(b), character(0))
  parsed <- rf_canonical_json(b)
  expect_identical(rf_validate_parsed(parsed), character(0))
  ex <- cycle_example()
  expect_identical(rf_validate_parsed(ex), character(0))                                       # the contract's cycle example is valid under the R validator too
  ctls <- cycle_controls()
  expect_gte(length(ctls), 8L)                                                                  # C01-C08
  for (ctl in ctls) {
    expect_gt(length(rf_validate_parsed(rf_apply_control(ex, ctl))), 0L, label = paste("example", ctl$id, ctl$why))
    expect_gt(length(rf_validate_parsed(rf_apply_control(parsed, ctl))), 0L, label = paste("writer", ctl$id, ctl$why))
  }
  py <- Sys.which(c("python3", "python")); py <- py[nzchar(py)][1]
  skip_if(is.na(py), "no Python on this machine")
  p <- file.path(tempdir(), "bundle_v2_cycle_py.json")
  rf_write_json_atomic(b, p)
  out <- suppressWarnings(system2(py, c(shQuote(file.path(.RF_HOME, "tools", "check_bundle_contract.py")), shQuote(p), shQuote(rf_contracts_dir())), stdout = TRUE, stderr = TRUE))
  status <- attr(out, "status") %||% 0L
  if (status != 0L) print(out)
  expect_identical(status, 0L); expect_true(any(grepl("problems: 0", out, fixed = TRUE))); expect_true(any(grepl("negative controls accepted (must be none): []", out, fixed = TRUE)))
})

test_that("the R mirror of the cycle invariants flags each cross-field break by itself (d_2, a missing offered industry, a growth of -100%, the weight, the pace order, the Senate term)", {
  b <- rf_canonical_json(test_bundle2_pilot())
  one <- function(f) { x <- b; x <- f(x); rf_validate_parsed(x) }
  expect_problem <- function(f, pat) expect_true(any(grepl(pat, one(f), fixed = TRUE)), info = pat)
  expect_problem(function(x) { x$cycle_model$measures$general_giving$drift$d$`2` <- x$cycle_model$measures$general_giving$drift$d$`2` + 1e-6; x }, "does not follow from b0, b1, k_max and damp")
  expect_problem(function(x) { x$cycle_model$measures$pac_to_candidates$step$credit_unions$df <- 2L; x }, "df is not pairs - 1")
  expect_problem(function(x) { x$cycle_model$measures$general_giving$step$property_casualty <- NULL; x }, "no entry for property_casualty")
  expect_problem(function(x) { x$cycle_model$budget_rule$growth$credit_unions$annual$`2025` <- -1; x }, "-100%")
  expect_problem(function(x) { x$cycle_model$budget_rule$weight_model <- 0.6; x }, "must be 0.5")
  expect_problem(function(x) { x$cycle_model$pace$series$commercial_banks$cycles$`2024`$O15 <- 1e9; x }, "needs 0 < O15 <= O18 <= O21 <= F")
  expect_problem(function(x) { x$share_models$control_Senate$terms <- Filter(function(t) t != "Pres", x$share_models$control_Senate$terms); x }, "Pres is required")
})

test_that("the Senate share model keeps the presidential-cycle term (owner: \"2. Keep senate in\"); the House model has it too", {
  b <- test_bundle2_pilot()
  expect_true("Pres" %in% unlist(b$share_models$control_Senate$terms)); expect_true("Pres" %in% unlist(b$share_models$control_House$terms))
  expect_identical(b$share_models$control_Senate$formula, "RShare ~ sector + RMajNow + Forecast + G_prior + Pres")
  expect_match(b$share_models$control_Senate$specification, "presidential-cycle term")
})

test_that("a context that lacks an offered industry (the frozen v1 sample has no property and casualty pilot) builds no cycle_model, and the reason is stated", {
  v <- test_v2()
  expect_match(paste(rf_cycle_model_gap(v), collapse = " "), "property_casualty: no general-giving step variance")
  expect_null(test_bundle2()$cycle_model)
  expect_error(rf_v2_cycle_model(v))
  expect_length(rf_cycle_model_gap(test_v2_pilot()), 0L)
})

test_that("RF_CYCLE_MODEL=0 reproduces the bundle published before the cycle model (rf_bundle_diff over the model blocks), and says so in its context", {
  pub <- published_before_cycle()
  if (!is.list(pub)) skip("this tree's publish directory holds no bundle published before the cycle model (versions/7bc7bcf1...)")
  old <- Sys.getenv("RF_CYCLE_MODEL", unset = NA); on.exit(if (is.na(old)) Sys.unsetenv("RF_CYCLE_MODEL") else Sys.setenv(RF_CYCLE_MODEL = old), add = TRUE)
  Sys.setenv(RF_CYCLE_MODEL = "0")
  expect_false(rf_cycle_model_on())
  v0 <- memo("v2_pilot_off", { v <- rf_v2_context(test_ctx_pilot(), run_id = "unit", packages = RF_TEST_PKGS, built_at_utc = "2026-10-07T12:00:00Z", b_random = 999L, frozen_ctx = test_ctx()); v$adequacy <- rf_gate_adequacy(test_ctx_pilot()); v })
  b0 <- rf_bundle_v2(v0)
  expect_null(v0$phase); expect_false(v0$cycle_model_on); expect_null(b0$cycle_model)
  expect_false("Pres" %in% unlist(b0$share_models$control_Senate$terms))
  expect_null(b0$pac_model$evidence$phase)
  Sys.setenv(RF_CYCLE_MODEL = "1"); expect_true(rf_cycle_model_on())
  # the model blocks equal the published bundle's; the random-draw evidence (the published p-values used 99,999 draws, the unit run 999), the run identity, sources and gates are not model content
  keep <- c("schema_version", "currency", "deflator", "anchor_contract", "industries", "pac_model", "share_models", "lobby_model", "political_inputs", "saved_outlook", "backtests", "validation_metrics", "industry_slopes", "inference", "validation", "interval_labels")
  a <- rf_canonical_json(b0)[keep]; p <- pub[keep]
  d <- rf_bundle_diff(a, p, ignore = c("built_at_utc", "model_version", "run_id", "code_sha256", "R_version", "packages", "note", "as_of", "evidence"))
  if (nrow(d)) print(utils::head(d, 12))
  # the one text that differs is code text, not model content: the anchor-contract label of the general-giving measure gained its exclusion clause ("excluding receipts Mentat marks non-giving ...")
  # in the writer after 2026-09-30, the day the published bundle was built
  known <- "$.anchor_contract.pac.measures[1].label"
  expect_true(all(d$path == known), info = paste(setdiff(d$path, known), collapse = "; "))
  if (nrow(d)) expect_match(d$a, "^Mentat general giving \\(included receipt amount, all channels\\)")
  expect_lt(attr(d, "max_dev"), 1e-9)
})

test_that("general giving stays on the model plus observed conditioning (P1): BLEND needs three dated cycles and the pace of a 2-cycle series is undefined (NA)", {
  s2 <- data.frame(cycle = c(2022, 2024), F_cents = c(100, 200), O15_cents = c(50, 90), O18_cents = c(60, 110), O21_cents = c(80, 150))
  base <- data.frame(design = c("loeo", "chrono"), target = 2024, d_hat = 0.1, half = 0.3, pairs = 4)
  r <- rf_blend_total(s2, base, c(`2022` = 1, `2024` = 1), month = 18L, targets = list(loeo = 2024L, chrono = 2024L))
  bl <- r[r$candidate %in% c("PACE", "BLEND"), ]
  expect_gt(nrow(bl), 0L); expect_true(all(is.na(bl$F_hat)))                                      # one training cycle: no pace (n < 2), BLEND undefined
  expect_match(cycle_of()$measures$general_giving$open_cycle_layer, "P1")
})
