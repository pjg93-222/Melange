# R port only: the rulings of 2026-09-26 (coordinator, relaying Paul), rule set paul-2026-09-25, on synthetic data:
# near-collinearity (H5 seniority), telecom combined growth, one-year growth values, singletons, ASYM, DECEL, SLOPES,
# H4 read-outs of the LobbyView tests, the bank split and the coverage table. The parity rule set keeps none of them.

ext_lv_sheet <- function(years = 2006:2024, community = FALSE) {
  set.seed(91)
  conf <- c(commercial_banks = "high", credit_unions = "high", crypto = "roster", credit_arms = "naics",
            property_casualty = "naics")
  if (community) conf <- c(conf, community_banks = "roster", commercial_banks_ex_community = "high")
  rows <- list()
  for (s in names(conf)) for (y in years) {
    amount <- (10 + 3 * match(s, names(conf)) + rnorm(1, 0, 0.5)) * 1e6
    thin <- s == "credit_arms" || (s == "community_banks" && y %% 2 == 0)
    cov <- paste(c(if (y == 2024) "partial_year", if (thin) "thin", if (s == "community_banks" && y <= 2007) "id_merge"), collapse = ";")
    if (!nzchar(cov)) cov <- "ok"
    rows[[length(rows) + 1L]] <- list(source = "lobbyview", sector = s, confidence = conf[[s]], year = y, period = "annual",
                                      lobby_amount_undifferentiated_real_2025_usd = amount,
                                      lobby_amount_dedup_real_2025_usd = 0.8 * amount, dedup_ratio = 0.8,
                                      status = if (y == 2024) "partial" else "observed", study_sector = s, coverage_flag = cov)
  }
  .rows_df(rows)
}

ext_build <- function(folder, community_lv = FALSE, extra_units = "community_banks", predicted = NULL) {
  extra <- list(lobbying = setNames(list(ext_lv_sheet(community = community_lv)), SGS$LOBBYVIEW_ALL_SHEET))
  if (!is.null(predicted)) extra$predicted <- predicted
  synth_build(folder, expected_control = expected_control_sheet(), iem_last_year = 2022, extra_sheets = extra,
              extra_units = extra_units)
}

ext_env <- local({
  base <- tmp_dir()
  data <- ext_build(file.path(base, "data"))
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "results"), B = 99, run_id = "analysis-test-ext",
                   only = c("L1-LV", "ASYM-L1-LV", "DECEL-L1-LV", "SLOPES-L1-LV", "H4-L1-LV", "C1", "BS-C1", "BANK-C1",
                            "BS-L1-LV", "ASYM-C1", "L1-income", "CONTRACT-a-L1-LV", "CONTRACT-b-L1-LV",
                            "ASYM-SLOPES-L1-LV"), rules = PAUL)
  list(data = data, out = out, rows = setNames(out$est_rows, vapply(out$est_rows, `[[`, "", "test_id")),
       coefs = out$coef_rows)
})
coef_of <- function(env, tid, name) Filter(function(c) c$test_id == tid && c$coefficient == name, env$coefs)

test_that("registry: 51 new tests under Paul's rule set; the parity registry is unchanged", {
  rp <- sgs_registry(PAUL); rq <- sgs_registry(PARITY)
  expect_equal(length(rp), 373)  # 222 + the 90 SHIFT tests, the 33 revision tests and the 28 SEATS-A tests of 2026-09-26 (test-shift-trends-forecast.R, test-review-0926.R, test-seats-0926.R)
  expect_true(all(c("CONTRACT-a-L1-LV", "CONTRACT-b-L1-LV", "ASYM-SLOPES-L1-LV", "CONTRACT-a-C1", "CONTRACT-b-C1",
                    "ASYM-SLOPES-C1") %in% names(rp)))
  expect_match(rp[["ASYM-SLOPES-L1-LV"]]$note, "predicts a NEGATIVE decline-year slope", fixed = TRUE)
  expect_match(rp[["CONTRACT-b-L1-LV"]]$note, "identified by one sector cluster", fixed = TRUE)
  expect_equal(length(rq), 139)
  fam <- table(vapply(rp, `[[`, "", "family"))
  expect_equal(as.integer(fam[c("ASYM", "DECEL", "SLOPES", "BANKSPLIT", "telecom", "CONTRACT", "ASYM-SLOPES")]),
               c(6L, 6L, 6L, 12L, 12L, 4L, 2L))
  expect_true(all(paste0("H4-L", 1:3, "-LV") %in% names(rp)))
  expect_true(all(vapply(rq, function(s) !isTRUE(s$drop_singletons) && is.na(s$near_collinear_r2), TRUE)))
  expect_true(all(vapply(Filter(function(s) identical(s$table, "champions"), rp), function(s) s$near_collinear_r2 == 0.9999, TRUE)))
  expect_match(rp[["ASYM-L1-LV"]]$flag, SGS$POPULATION_NOTE, fixed = TRUE)   # derived growth columns carry the note
  expect_match(rp[["R-TW-C1"]]$flag, SGS$POPULATION_NOTE, fixed = TRUE)
})

test_that("near-collinearity: the auxiliary R^2 and the drop rule", {
  set.seed(3)
  X <- cbind(fe1 = rep(c(1, 0), each = 10), fe2 = rep(c(0, 1), each = 10), a = rnorm(20), b = rnorm(20))
  X <- cbind(X, c = X[, "a"] + 1e-4 * rnorm(20))   # c is a + tiny noise: R^2 ~ 1
  r2 <- sgs_aux_r2(X, match("b", colnames(X)))
  expect_equal(r2, summary(lm(X[, "b"] ~ X[, c("fe1", "a", "c")]))$r.squared, tolerance = 1e-10)
  nc <- sgs_near_collinear_columns(X, c("a", "b", "c"), 0.9999)
  expect_equal(length(nc$dropped), 1)                 # a and c are near duplicates: one goes, then the other stays
  expect_true(nc$dropped %in% c("a", "c"))
  expect_gt(nc$r2, 0.9999)
  expect_length(sgs_near_collinear_columns(X, c("a", "b", "c"), NA_real_)$dropped, 0)
})

test_that("near-collinearity: seniority dropped from H5-within (Paul), kept in H5-pooled and in the parity rule set", {
  base <- tmp_dir()
  data <- synth_build(file.path(base, "data"))
  fr <- champions_frame(slope = 5000.0, noise = 500.0)
  key <- paste(fr$bioguide, fr$cycle)
  set.seed(17)
  eps <- setNames(rnorm(length(unique(key)), 0, 0.02), unique(key))
  fr$seniority_years <- fr$seniority_years + unname(eps[key])   # seniority = champion + cycle up to 0.02 years
  write_champions(data, fr, age_minutes = 30)
  op <- quiet_run(data_dir = data, results_dir = file.path(base, "rp"), B = 99, run_id = "t-near-p", only = c("H5-pooled", "H5-within"), rules = PAUL)
  oq <- quiet_run(data_dir = data, results_dir = file.path(base, "rq"), B = 99, run_id = "t-near-q", only = c("H5-pooled", "H5-within"), rules = PARITY)
  rp <- setNames(op$est_rows, vapply(op$est_rows, `[[`, "", "test_id"))
  rq <- setNames(oq$est_rows, vapply(oq$est_rows, `[[`, "", "test_id"))
  expect_match(rp[["H5-within"]]$note, "controls nearly collinear with the fixed effects and the other regressors (R^2 >= 0.9999) and dropped: seniority_years (R^2 0.9999", fixed = TRUE)
  expect_false(grepl("nearly collinear", rp[["H5-pooled"]]$note, fixed = TRUE))
  expect_false(grepl("nearly collinear", rq[["H5-within"]]$note, fixed = TRUE))
  expect_equal(rp[["H5-within"]]$resid_df, rq[["H5-within"]]$resid_df + 1)
  expect_equal(rp[["H5-pooled"]]$resid_df, rq[["H5-pooled"]]$resid_df)
  expect_false("seniority_years" %in% op$decisions[["H5-within"]]$design$names)
  expect_true("seniority_years" %in% oq$decisions[["H5-within"]]$design$names)
  # the summary's lm() formula leaves seniority_years out, and its focal coefficient equals the pipeline's
  txt <- readLines(op$summaries, encoding = "UTF-8")
  i <- which(startsWith(txt, "==== H5-within  ["))
  j <- which(startsWith(txt, "==== ") & seq_along(txt) > i)
  blk <- txt[i:(if (length(j)) j[1] - 1 else length(txt))]
  call <- paste(blk[which(blk == "Call:") + 1:3], collapse = " ")
  expect_false(grepl("seniority_years", call, fixed = TRUE))
  expect_true(all(op$summary_checks$agree))
})

test_that("telecom: combined growth = growth of the summed component revenue; predicted by baseline revenue", {
  a7 <- data.frame(sector = rep(c("telecom_wireless", "telecom_cable"), each = 3), year = rep(2010:2012, 2),
                   growth_same_year_pct = c(5, 2, -1, 10, -4, 3), growth_previous_year_pct = NA_real_,
                   revenue_million_report_price_basis = c(105, 107.1, 106.029, 110, 105.6, 108.768),
                   revenue_price_basis = "constant 2024 USD", status = "observed", study_sector = "telecom",
                   stringsAsFactors = FALSE)
  ac <- .telecom_actual_combined(a7)
  expect_equal(ac$g_same, 100 * c(215 / 200 - 1, 212.7 / 215 - 1, 214.797 / 212.7 - 1), tolerance = 1e-9)
  expect_equal(ac$g_prev, c(NA, ac$g_same[1:2]))
  expect_match(ac$how[1], "revenue-weighted (07 revenue_million_report_price_basis, constant 2024 USD)", fixed = TRUE)
  a7$revenue_million_report_price_basis <- NA
  eq <- .telecom_actual_combined(a7)
  expect_equal(eq$g_same, c(7.5, -1, 1))
  expect_match(eq$how[1], "equal weights", fixed = TRUE)
  cf <- data.frame(record_source = "telecom_component_selected", study_sector = "Telecom",
                   component_code = c("51721", "51711a", "51721", "51711a", "51721"), target_year = c(2012, 2012, 2013, 2013, 2014),
                   predicted_growth_pct = c(4, -2, 1, 3, 9), baseline_revenue_same_vintage = c(300, 100, 200, NA, 50),
                   publication_precedes_target_year = "True", publication_date = c("2011-10", "2011-12", "2012-10", "2012-11", "2013-10"),
                   status = "observed", stringsAsFactors = FALSE)
  pc <- .telecom_predicted_combined(cf)
  expect_equal(pc$combined$year, c(2012, 2013))         # 2014 has no cable forecast: no combined value
  expect_equal(pc$combined$g_pred, c(0.75 * 4 + 0.25 * -2, 0.5 * 1 + 0.5 * 3))
  expect_match(pc$combined$how[2], "equal weights", fixed = TRUE)
  expect_equal(pc$comp$telecom_wireless$g, c(4, 1, 9))
})

test_that("one-year growth values: 06 one-year proxies fill blank predicted growth for crypto / fintech, flagged", {
  g <- data.frame(study_sector = c("crypto", "fintech", "fintech"), year = c(2025, 2025, 2024), predicted_growth_pct = NA_real_,
                  predicted_status = "missing", forecast_publication_month = NA_character_, stringsAsFactors = FALSE)
  p6 <- data.frame(study_sector = c("crypto", "fintech"), year = c(2025, 2024), predicted_growth_pct = NA_real_,
                   collected_forecast_growth_pct = c(-3.78, 5), forecast_horizon_years = c(1, 5), forecast_status = "separate_crypto_proxy",
                   forecast_method = "published_one_year_CAGR", forecast_known_available_by = "2024-12-26", status = "partial",
                   stringsAsFactors = FALSE)
  cf <- data.frame(record_source = "fintech_component", record_key = "ft_c", study_sector = "Fintech", provider = "Statista",
                   source_component = "Digital Assets market", known_available_by = "2024-02-26", published_growth_pct = 17.98,
                   forecast_target_year = 2025, published_cagr_pct = NA_real_, status = "observed", stringsAsFactors = FALSE)
  out <- .add_annual_proxies(g, list(predicted = list(frames = list(data = p6, component_forecasts = cf))))
  expect_equal(out$predicted_growth_pct, c(-3.78, 17.98, NA))   # the 5-year collected value is not a one-year value
  expect_equal(out$predicted_status[1:2], c("observed", "observed"))
  expect_match(out$predicted_growth_flag[1], "one-year", fixed = TRUE)
  expect_match(out$predicted_growth_flag[2], "not the broad sector", fixed = TRUE)
  expect_true(attr(out, "annual_proxies")$built)
})

test_that("singletons: a sector with one complete sector-year leaves a fixed-effect sample, named in the exclusions", {
  df <- sector_year_panel(n_sectors = 3, years = 2014:2025)
  df$growth_previous_year_pct[df$study_sector == SECTORS[3] & df$year != 2021] <- NA
  sp <- tspec(drop_singletons = TRUE)
  smp <- sgs_build_sample(list(sector_year = df), sp, c(2016, 2025))
  expect_false(SECTORS[3] %in% smp$df$study_sector)
  expect_equal(unname(smp$singletons), "2021")
  expect_true(any(grepl("singleton sector", names(smp$exclusions), fixed = TRUE)))
  smq <- sgs_build_sample(list(sector_year = df), tspec(), c(2016, 2025))   # parity behaviour: kept
  expect_true(SECTORS[3] %in% smq$df$study_sector)
})

test_that("ASYM: g_pos + g_neg = g, the equality test is the difference of the two slopes, declines counted per sector", {
  sy <- ext_env$out$tables$sector_year
  g <- sy$growth_previous_year_pct
  ok <- !is.na(g)
  expect_equal(sy$growth_previous_year_pct_pos[ok] + sy$growth_previous_year_pct_neg[ok], g[ok])
  expect_true(all(sy$growth_previous_year_pct_neg[ok] <= 0))
  r <- ext_env$rows[["ASYM-L1-LV"]]
  expect_equal(r$status, SGS_ESTIMABLE)
  cp <- coef_of(ext_env, "ASYM-L1-LV", "growth_previous_year_pct_pos")[[1]]
  cn <- coef_of(ext_env, "ASYM-L1-LV", "growth_previous_year_pct_neg")[[1]]
  cd <- coef_of(ext_env, "ASYM-L1-LV", "growth_previous_year_pct_neg - growth_previous_year_pct_pos")[[1]]
  expect_equal(cd$estimate, cn$estimate - cp$estimate, tolerance = 1e-9)
  expect_true(cd$boot_p >= 0 && cd$boot_p <= 1)
  expect_match(cd$inference, "test of growth_previous_year_pct_pos = growth_previous_year_pct_neg", fixed = TRUE)
  expect_match(r$note, "Declines (growth_previous_year_pct < 0) per sector in the estimated sample: ", fixed = TRUE)
  for (s in strsplit(r$sectors, ", ")[[1]]) expect_match(r$note, paste0(s, " "), fixed = TRUE)
  # a sector without declines says so
  att <- list(ok = TRUE, sample = list(df = data.frame(study_sector = c("a", "a", "b", "b"), year = c(2010, 2011, 2010, 2011),
                                                       growth_previous_year_pct = c(1, 2, -1, 3), stringsAsFactors = FALSE)))
  ct <- .count_text(sgs_registry(PAUL)[["ASYM-L1-LV"]], att)
  expect_match(ct, "a 0 of 2 (no declines)", fixed = TRUE)
  expect_match(ct, "b 1 of 2 (2010)", fixed = TRUE)
})

test_that("DECEL: the indicator is g_t < g_{t-1} within the sector, with its interaction", {
  sy <- ext_env$out$tables$sector_year
  b <- sy[sy$study_sector == "commercial_banks", ]
  b <- b[order(b$year), ]
  k <- which(b$year == 2015)
  expect_equal(b$growth_previous_year_pct_decel[k], as.numeric(b$growth_previous_year_pct[k] < b$growth_previous_year_pct[k - 1]))
  expect_equal(b$growth_previous_year_pct_x_decel[k], b$growth_previous_year_pct[k] * b$growth_previous_year_pct_decel[k])
  expect_true(is.na(b$growth_previous_year_pct_decel[b$year == 2006]))
  expect_equal(ext_env$rows[["DECEL-L1-LV"]]$status, SGS_ESTIMABLE)
  expect_match(ext_env$rows[["DECEL-L1-LV"]]$note, "Decelerations (growth_previous_year_pct below its prior-year value)", fixed = TRUE)
})

test_that("SLOPES: one slope per sector with inference, and the bootstrap F test of equal slopes (= anova's F)", {
  r <- ext_env$rows[["SLOPES-L1-LV"]]
  expect_equal(r$status, SGS_ESTIMABLE)
  secs <- strsplit(r$sectors, ", ")[[1]]
  for (s in secs) {
    c0 <- coef_of(ext_env, "SLOPES-L1-LV", paste0("growth_previous_year_pct:", s))
    expect_length(c0, 1)
    expect_false(is.na(c0[[1]]$boot_p))
  }
  j <- Filter(function(c) c$test_id == "SLOPES-L1-LV" && identical(c$test, "joint"), ext_env$coefs)[[1]]
  expect_equal(j$ci_text, "n/a (joint test)")
  att <- sgs_decision_chosen(ext_env$out$decisions[["SLOPES-L1-LV"]])
  spec <- ext_env$out$registry[["SLOPES-L1-LV"]]
  f1 <- sgs_fit_lm(sgs_lm_sector_year(spec, att$sample$df))
  l0 <- spec; l0$variant <- "level"
  f0 <- sgs_fit_lm(sgs_lm_sector_year(l0, att$sample$df))
  expect_equal(j$estimate, anova(f0, f1)$F[2], tolerance = 1e-9)
  expect_true(j$boot_p >= 0 && j$boot_p <= 1)
  chk <- ext_env$out$summary_checks
  expect_true(all(chk$agree[chk$test_id == "SLOPES-L1-LV"]))
  expect_true(any(chk$lm_term[chk$test_id == "SLOPES-L1-LV"] == "anova() F"))
  txt <- readLines(ext_env$out$summaries, encoding = "UTF-8")
  expect_true(any(grepl("growth_previous_year_pct:factor(study_sector)", txt, fixed = TRUE)))
  expect_true(any(grepl("^anova\\(<one common slope>, <one slope per sector>\\):$", txt)))
})

test_that("CONTRACT: the year-after-contraction shift, pooled (a) and per sector (b), with joint tests = anova()", {
  sy <- ext_env$out$tables$sector_year
  ok <- !is.na(sy$growth_previous_year_pct)
  expect_equal(sy$contracted_prior[ok], as.numeric(sy$growth_previous_year_pct[ok] < 0))
  ra <- ext_env$rows[["CONTRACT-a-L1-LV"]]
  expect_equal(ra$status, SGS_ESTIMABLE)
  expect_match(ra$note, "Contraction years (contracted_prior = 1: growth_previous_year_pct < 0", fixed = TRUE)
  ca <- coef_of(ext_env, "CONTRACT-a-L1-LV", "contracted_prior")
  expect_length(ca, 1)
  expect_false(is.na(ca[[1]]$boot_p))
  rb <- ext_env$rows[["CONTRACT-b-L1-LV"]]
  expect_equal(rb$status, SGS_ESTIMABLE)
  for (s in strsplit(rb$sectors, ", ")[[1]]) expect_length(coef_of(ext_env, "CONTRACT-b-L1-LV", paste0("contracted_prior:", s)), 1)
  jb <- Filter(function(c) c$test_id == "CONTRACT-b-L1-LV" && identical(c$test, "joint"), ext_env$coefs)
  expect_setequal(vapply(jb, `[[`, "", "joint_kind"), c("zero", "equal"))
  # the "equal" restriction is CONTRACT-a's model: its F is anova(CONTRACT-a, CONTRACT-b)
  att <- sgs_decision_chosen(ext_env$out$decisions[["CONTRACT-b-L1-LV"]])
  sb <- ext_env$out$registry[["CONTRACT-b-L1-LV"]]; sa <- ext_env$out$registry[["CONTRACT-a-L1-LV"]]
  fb <- sgs_fit_lm(sgs_lm_sector_year(sb, att$sample$df)); fa <- sgs_fit_lm(sgs_lm_sector_year(sa, att$sample$df))
  je <- Filter(function(c) identical(c$joint_kind, "equal"), jb)[[1]]
  expect_equal(je$estimate, anova(fa, fb)$F[2], tolerance = 1e-9)
  chk <- ext_env$out$summary_checks
  for (tid in c("CONTRACT-a-L1-LV", "CONTRACT-b-L1-LV", "ASYM-SLOPES-L1-LV")) {
    expect_true(any(chk$test_id == tid), info = tid)
    expect_true(all(chk$agree[chk$test_id == tid]), info = tid)
  }
  expect_equal(sum(chk$test_id == "CONTRACT-b-L1-LV" & chk$lm_term == "anova() F"), 2)
})

test_that("ASYM-SLOPES: each sector's growth-year and decline-year slope; joint test that all decline slopes are zero", {
  r <- ext_env$rows[["ASYM-SLOPES-L1-LV"]]
  expect_equal(r$status, SGS_ESTIMABLE)
  for (s in strsplit(r$sectors, ", ")[[1]]) for (v in c("_pos", "_neg")) {
    expect_length(coef_of(ext_env, "ASYM-SLOPES-L1-LV", paste0("growth_previous_year_pct", v, ":", s)), 1)
  }
  j <- Filter(function(c) c$test_id == "ASYM-SLOPES-L1-LV" && identical(c$test, "joint"), ext_env$coefs)
  expect_length(j, 1)
  expect_equal(j[[1]]$joint_kind, "zero")
  expect_equal(j[[1]]$joint_var, "growth_previous_year_pct_neg")
  txt <- readLines(ext_env$out$summaries, encoding = "UTF-8")
  expect_true(any(grepl("anova(<no growth_previous_year_pct_neg term>, <one growth_previous_year_pct_neg term per sector>):", txt, fixed = TRUE)))
  # a sector whose term does not vary within it has no estimable term: left out of the design and named
  df <- sector_year_panel(n_sectors = 3, years = 2012:2023)
  df$contracted_prior <- as.numeric(df$growth_previous_year_pct < 0)
  df$contracted_prior[df$study_sector == SECTORS[2]] <- 0
  sp <- sgs_registry(PAUL)[["CONTRACT-b-L1-LV"]]
  d <- sgs_build_design(df, sp)
  expect_false(paste0("contracted_prior:", SECTORS[2]) %in% d$names)
  expect_equal(d$unestimable, paste0("contracted_prior:", SECTORS[2]))
})

test_that("H4-L1-LV: exp_dem and cur_dem read from L1-LV with the study's inference", {
  r <- ext_env$rows[["H4-L1-LV"]]
  expect_equal(r$status, SGS_ESTIMABLE)
  for (v in c("exp_dem_house", "exp_dem_senate", "cur_dem_house", "cur_dem_senate")) {
    c0 <- coef_of(ext_env, "H4-L1-LV", v)
    expect_length(c0, 1)
    expect_equal(c0[[1]]$source_test, "L1-LV")
    expect_false(is.na(c0[[1]]$boot_p))
    expect_false(is.na(c0[[1]]$cr1_se))
  }
  expect_true(any(startsWith(readLines(ext_env$out$summaries, encoding = "UTF-8"), "==== H4-L1-LV  [EXTENSION]")))
})

test_that("bank split: big and community banks as two sectors sharing the banking growth series", {
  syb <- ext_env$out$tables$sector_year_banks
  expect_true(all(c("big_banks", "community_banks") %in% syb$study_sector))
  expect_false("commercial_banks" %in% syb$study_sector)
  bb <- syb[syb$study_sector == "big_banks", ]; cb <- syb[syb$study_sector == "community_banks", ]
  expect_equal(cb$growth_previous_year_pct[match(2015, cb$year)], bb$growth_previous_year_pct[match(2015, bb$year)])
  expect_false(isTRUE(all.equal(cb$contributions_real_m, bb$contributions_real_m)))
  r <- ext_env$rows[["BS-C1"]]
  expect_equal(r$status, SGS_ESTIMABLE)
  expect_true(all(c("big_banks", "community_banks") %in% strsplit(r$sectors, ", ")[[1]]))
  rb <- ext_env$rows[["BANK-C1"]]
  expect_equal(rb$label, "DESCRIPTIVE")   # two sector clusters
  expect_length(coef_of(ext_env, "BANK-C1", "growth_previous_year_pct:community_banks"), 1)
  expect_equal(ext_env$rows[["BS-L1-LV"]]$status, SGS_NOT_BUILT)
  expect_match(ext_env$rows[["BS-L1-LV"]]$reason, "has no commercial_banks_ex_community / community_banks rows yet", fixed = TRUE)
  # with the split LobbyView rows the LobbyView bank split runs: big_banks = commercial_banks_ex_community, community banks'
  # thin years kept and their id_merge years excluded; the main L1-LV keeps the old commercial_banks series
  d2 <- ext_build(file.path(tmp_dir(), "data"), community_lv = TRUE)
  o2 <- quiet_run(data_dir = d2, results_dir = file.path(tmp_dir(), "r"), B = 99, only = c("BS-L1-LV", "L1-LV"), rules = PAUL)
  r2 <- setNames(o2$est_rows, vapply(o2$est_rows, `[[`, "", "test_id"))
  expect_equal(r2[["BS-L1-LV"]]$status, SGS_ESTIMABLE)
  expect_true(all(c("big_banks", "community_banks") %in% strsplit(r2[["BS-L1-LV"]]$sectors, ", ")[[1]]))
  expect_match(r2[["BS-L1-LV"]]$note, "their thin years are KEPT", fixed = TRUE)
  syb <- o2$tables$sector_year_banks
  lv <- ext_lv_sheet(community = TRUE)
  cb <- syb[syb$study_sector == "community_banks", ]
  expect_equal(cb$lobby_lv_status[cb$year == 2010], "observed")          # a thin year: kept
  expect_equal(cb$lobby_lv_status[cb$year == 2007], "id_merge")          # an id_merge year: excluded
  bb <- syb[syb$study_sector == "big_banks", ]
  ex <- lv[lv$study_sector == "commercial_banks_ex_community" & lv$year == 2012, ]
  expect_equal(bb$lobby_lv_real_m[bb$year == 2012], ex$lobby_amount_dedup_real_2025_usd / 1e6)
  sy <- o2$tables$sector_year
  old <- lv[lv$study_sector == "commercial_banks" & lv$year == 2012, ]
  expect_equal(sy$lobby_lv_real_m[sy$study_sector == "commercial_banks" & sy$year == 2012], old$lobby_amount_dedup_real_2025_usd / 1e6)
  expect_false(any(c("community_banks", "commercial_banks_ex_community") %in% sy$study_sector))
  s2 <- sgs_decision_chosen(o2$decisions[["BS-L1-LV"]])$sample$df
  expect_false(2007 %in% s2$year[s2$study_sector == "community_banks"])
  expect_true(2010 %in% s2$year[s2$study_sector == "community_banks"])
})

test_that("coverage table: every study sector and Mentat book x family, IN / IN* / OUT with a reason", {
  cov <- ext_env$out$sheets$coverage
  expect_setequal(unique(cov$unit), c(SGS$STUDY_SECTORS, "community_banks"))
  expect_true(all(cov$status %in% c("IN", "IN*", "OUT", "NOT BUILT")))
  expect_true(all(nzchar(cov$reason[cov$status != "IN"])))
  lv <- cov[cov$family == "L-LV (LobbyView)", ]
  expect_equal(lv$status[lv$unit == "commercial_banks"], "IN")
  expect_equal(lv$status[lv$unit == "credit_arms"], "OUT")
  expect_match(lv$reason[lv$unit == "credit_arms"], "thin", fixed = TRUE)
  expect_match(lv$reason[lv$unit == "community_banks"], "not a study sector", fixed = TRUE)
  bs <- cov[cov$family == "Bank split", ]
  expect_equal(bs$status[bs$unit == "community_banks"], "IN")
  md <- paste(readLines(ext_env$out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, "## Coverage: every study sector and Mentat book x test family", fixed = TRUE)
  expect_match(md, "| sector (Mentat book) |", fixed = TRUE)
})
