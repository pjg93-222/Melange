# R port only: the rulings of 2026-09-26 (coordinator for Paul), rule set paul-2026-09-25, on synthetic data:
# SHIFT (Paul's partisan-allocation hypothesis), TRENDS (sign and size first) and the FORECAST backtest. The parity rule
# set keeps none of them.

# ---- a synthetic SHIFT world ---------------------------------------------------------------------------------------
# Five study sectors with a Mentat book plus community_banks; contributions (04) and 08 in contrib_years (2026 partial);
# current control as in the live data (03 rewritten); expected control 2023-2026 from the fill sheet. The shares follow
# a known model, so the estimates can be checked against it:
#   08 own-chamber share = 0.30 + 0.05 unit + 0.10 Senate + beta_own * exp_own + 0.10 * cur_own + noise
#   04 all-giving share  = 0.40 + 0.03 unit + beta_h * exp_dem_house + beta_s * exp_dem_senate + noise
# 04 rows are split into D / R / Other / Unclassified parts with that share (totals unchanged, so every 04 check
# holds); company Co B's R part is funding_source non_giving ("other receipt"), which must stay in.
SHIFT_SECTORS <- c("commercial_banks", "credit_unions", "crypto", "credit_arms", "fintech")
SHIFT_BETA <- c(own = 0.25, h = 0.30, s = -0.20)

shift_world <- function(folder, contrib_years = 2021:2025, noise = 0.001, seed = 11, hill = TRUE, zero_base = FALSE) {
  data <- synth_build(folder, sectors = SHIFT_SECTORS, contrib_years = contrib_years, extra_units = "community_banks",
                      expected_control = expected_control_sheet(), iem_last_year = 2022)
  # 03: current control as in the live data (House D 2019-2022, Senate D 2021-2024)
  cc <- expand.grid(chamber = c("House", "Senate"), calendar_year = 2006:2026, stringsAsFactors = FALSE)
  cc$dem_control <- ifelse(cc$chamber == "House", as.numeric(cc$calendar_year %in% c(2007:2010, 2019:2022)),
                           as.numeric(cc$calendar_year %in% c(2007:2014, 2021:2024)))
  cc$status <- "observed"
  sgs_write_xlsx(file.path(data, "03_actual_seat_gain.xlsx"),
                 list(current_control = cc[, c("calendar_year", "chamber", "dem_control", "status")]))
  wbs <- sgs_load_all(data, PAUL)
  sy <- sgs_build_sector_year(wbs, PAUL)
  yl <- sy[sy$study_sector == "commercial_banks", ]
  units <- c(SHIFT_SECTORS, "community_banks")
  set.seed(seed)
  rows <- list(); hrows <- list()
  st_of <- function(y) if (y == 2026) "partial" else if (y %in% contrib_years) "observed" else "missing"
  for (i in seq_along(units)) for (y in 2019:2026) for (ch in c("House", "Senate")) {
    s <- tolower(ch); st <- st_of(y); k <- match(y, yl$year)
    share <- 0.30 + 0.05 * i + 0.10 * (ch == "Senate") + SHIFT_BETA[["own"]] * yl[[paste0("exp_dem_", s)]][k] +
      0.10 * yl[[paste0("cur_dem_", s)]][k] + rnorm(1, 0, noise)
    tot <- 1e5 * i + 2e4 * (y - 2018)
    dem <- tot * share; rep <- tot - dem
    if (zero_base && units[i] == "credit_unions" && y == 2022 && ch == "Senate") { dem <- 0; rep <- 0 }
    miss <- st == "missing"
    r <- list(study_sector = units[i], year = y, chamber = ch, dem_usd = if (miss) NA else dem, rep_usd = if (miss) NA else rep,
              other_usd = if (miss) NA else 100, dem_real_m = if (miss || y == 2026) NA else dem / 1e6,
              rep_real_m = if (miss || y == 2026) NA else rep / 1e6,
              dem_share = if (miss || dem + rep <= 0) NA else dem / (dem + rep), n_rows = if (miss) NA else 10, status = st)
    rows[[length(rows) + 1L]] <- r
    h <- r
    if (!miss) {  # the Hill sheet: the chamber's two party committees added (D +5,000, R +15,000)
      h$dem_usd <- dem + 5000; h$rep_usd <- rep + 15000
      h$dem_real_m <- if (y == 2026) NA else h$dem_usd / 1e6; h$rep_real_m <- if (y == 2026) NA else h$rep_usd / 1e6
      h$dem_share <- h$dem_usd / (h$dem_usd + h$rep_usd)
    }
    hrows[[length(hrows) + 1L]] <- h
  }
  sheets08 <- list(sector_year_chamber = .rows_df(rows))
  if (hill) sheets08[[SGS$CHAMBER_HILL_SHEET]] <- .rows_df(hrows)
  sgs_write_xlsx(file.path(data, SGS$CHAMBER_FILE), sheets08)
  # 04: split every data row into D / R / Other with the unit-year's all-giving share
  p04 <- file.path(data, "04_campaign_spending.xlsx")
  sh <- lapply(c("data", "sector_year", "tier_by_year"), function(s) as.data.frame(readxl::read_excel(p04, sheet = s)))
  names(sh) <- c("data", "sector_year", "tier_by_year")
  d <- sh$data
  share_all <- function(u, y) {
    k <- match(y, yl$year)
    0.40 + 0.03 * match(u, units) + SHIFT_BETA[["h"]] * yl$exp_dem_house[k] + SHIFT_BETA[["s"]] * yl$exp_dem_senate[k]
  }
  set.seed(seed + 1)
  eps <- list()
  out <- list()
  for (j in seq_len(nrow(d))) {
    key <- paste(d$study_sector[j], d$year[j])
    if (is.null(eps[[key]])) eps[[key]] <- rnorm(1, 0, noise)
    s <- share_all(d$study_sector[j], d$year[j]) + eps[[key]]
    o <- 0.2
    for (p in c("D", "R", "Other / Unclassified")) {
      f <- switch(p, D = s * (1 - o), R = (1 - s) * (1 - o), o)
      r <- d[j, , drop = FALSE]
      r$party <- p
      r$giving_real_2025_usd <- d$giving_real_2025_usd[j] * f
      r$giving_nominal_usd <- d$giving_nominal_usd[j] * f
      if (p == "R" && d$company[j] == "Co B") r$funding_source <- "non_giving"
      out[[length(out) + 1L]] <- r
    }
  }
  sh$data <- do.call(rbind, out)
  sgs_write_xlsx(p04, sh)
  data
}

shift_env <- local({
  base <- tmp_dir()
  data <- shift_world(file.path(base, "data"))
  stages <- character(0)
  out <- sgs_run(data_dir = data, results_dir = file.path(base, "results"), B = 99, run_id = "analysis-test-shift",
                 only = c("SHIFT", "L1-LV"), rules = PAUL, log = function(...) NULL,
                 progress = function(stage, summary) stages <<- c(stages, stage))
  list(data = data, out = out, stages = stages, rows = setNames(out$est_rows, vapply(out$est_rows, `[[`, "", "test_id")))
})
shift_coef <- function(tid, name, env = shift_env) Filter(function(c) c$test_id == tid && c$coefficient == name, env$out$coef_rows)

test_that("registry: 90 SHIFT tests under Paul's rule set (373 in all), none under the parity rule set; no giving-only variant", {
  rp <- sgs_registry(PAUL); rq <- sgs_registry(PARITY)
  expect_equal(length(rp), 373)  # 28 SEATS-A (test-seats-0926.R) + 264 of the first SHIFT round + 12 SHIFT STRICT + 36 minimum-base + 27 L-LV robustness + 6 STRICT-C / -L-LV
  expect_equal(length(rq), 139)
  sh <- Filter(function(s) s$family %in% c("SHIFT", "SHIFT-PV"), rp)
  expect_length(sh, 90)
  expect_false(any(vapply(rq, function(s) s$family %in% c("SHIFT", "SHIFT-PV"), TRUE)))
  ids <- names(sh)
  main <- c("SHIFT-House", "SHIFT-Senate", "SHIFT-Chamber", "SHIFT-All", "SHIFT-All-House", "SHIFT-All-Senate")
  expect_true(all(main %in% ids))
  expect_true(all(paste0(main, "-PV") %in% ids))
  expect_true(all(paste0(c("SHIFT-House", "SHIFT-Senate", "SHIFT-Chamber"), "-Hill") %in% ids))
  expect_true(all(paste0(main, "-FD") %in% ids) && all(paste0(main, "-W") %in% ids))
  expect_false(any(grepl("-GO", ids, fixed = TRUE)))                 # "Keep those receipts": no giving-only variant
  expect_equal(unname(vapply(rp[main], `[[`, "", "label")), rep("CORE", 6))
  expect_true(all(vapply(sh[grepl("-(Hill|FD|W|STRICT)$", ids)], `[[`, "", "label") == "ROBUSTNESS"))
  expect_true(all(vapply(sh[endsWith(ids, "-PV")], function(s) s$label == "PREVIEW" && s$gate == "preview" &&
                           startsWith(s$flag, SGS$PREVIEW_FLAG), TRUE)))
  expect_equal(rp[["SHIFT-All"]]$focal, c("exp_dem_house", "exp_dem_senate"))
  expect_equal(rp[["SHIFT-All"]]$controls, c("pres_year", "midterm_year"))
  expect_equal(rp[["SHIFT-All-House"]]$controls, c("cur_dem_house", "pres_year", "midterm_year"))
  expect_equal(rp[["SHIFT-Chamber"]]$fe, "sector_x_chamber")
  expect_equal(rp[["SHIFT-House-W"]]$weight_var, "dem_share_house_base_real_m")
  expect_equal(rp[["SHIFT-Chamber-FD-PV"]]$preview_min_years, 4L)
  expect_true(all(vapply(sh, function(s) all(s$predicted_sign == "+") && isTRUE(s$identification), TRUE)))
  expect_equal(unique(vapply(sh[grepl("^SHIFT-All", ids) & !grepl("-B(25|10|50)K", ids)], `[[`, "", "trend_group")), "SHIFT-All")
  expect_true(all(vapply(sh, function(s) !any(sgs_is_growth_var(sgs_required_vars(s))) && !grepl(SGS$POPULATION_NOTE, s$flag, fixed = TRUE), TRUE)))
})

test_that("shift tables: eight units, 08 shares as supplied, 04 all-giving share with the non_giving rows kept, stacked chambers", {
  sy <- shift_env$out$tables$shift_year
  sc <- shift_env$out$tables$shift_chamber
  expect_equal(unique(sy$study_sector), c(SHIFT_SECTORS, "community_banks"))       # study-sector order, then the others
  expect_equal(nrow(sy), 6 * length(sgs_panel_years()))
  expect_equal(nrow(sc), 2 * nrow(sy))
  b08 <- readxl::read_excel(file.path(shift_env$data, SGS$CHAMBER_FILE), sheet = SGS$CHAMBER_SHEET)
  x <- b08[b08$study_sector == "community_banks" & b08$year == 2023 & b08$chamber == "Senate", ]
  r <- sy[sy$study_sector == "community_banks" & sy$year == 2023, ]
  expect_equal(r$dem_share_senate, x$dem_share)
  expect_equal(r$dem_share_senate_base_usd, x$dem_usd + x$rep_usd)
  expect_equal(r$dem_share_senate_base_real_m, x$dem_real_m + x$rep_real_m)
  expect_equal(r$dem_share_senate_status, "observed")
  expect_equal(sy$dem_share_house_status[sy$study_sector == "crypto" & sy$year == 2026], "partial")
  expect_equal(sy$dem_share_house_status[sy$study_sector == "crypto" & sy$year == 2020], "missing")
  # 04: D / (D + R) of party-labelled giving, Other / Unclassified outside both, non_giving rows kept
  d4 <- as.data.frame(readxl::read_excel(file.path(shift_env$data, "04_campaign_spending.xlsx"), sheet = "data"))
  k <- d4$study_sector == "fintech" & d4$year == 2024
  expect_true(any(d4$funding_source[k] == "non_giving"))
  dd <- sum(d4$giving_nominal_usd[k & d4$party == "D"]); rr <- sum(d4$giving_nominal_usd[k & d4$party == "R"])
  f <- sy[sy$study_sector == "fintech" & sy$year == 2024, ]
  expect_equal(f$dem_share_all, dd / (dd + rr), tolerance = 1e-12)
  rr_giving_only <- sum(d4$giving_nominal_usd[k & d4$party == "R" & d4$funding_source != "non_giving"])
  expect_false(isTRUE(all.equal(f$dem_share_all, dd / (dd + rr_giving_only))))       # dropping them would change it
  expect_equal(f$dem_share_all_dr_share, 0.8, tolerance = 1e-9)                      # 20% Other / Unclassified
  expect_equal(f$general_giving_real_m, sum(d4$giving_real_2025_usd[k]) / 1e6, tolerance = 1e-12)
  expect_gt(f$general_giving_non_giving_real_m, 0)
  # stacked: the own chamber's expected / current control on each row
  h <- sc[sc$study_sector == "fintech" & sc$year == 2024 & sc$chamber == "House", ]
  s <- sc[sc$study_sector == "fintech" & sc$year == 2024 & sc$chamber == "Senate", ]
  expect_equal(c(h$exp_dem_own_chamber, s$exp_dem_own_chamber), c(f$exp_dem_house, f$exp_dem_senate))
  expect_equal(c(h$cur_dem_own_chamber, s$cur_dem_own_chamber), c(f$cur_dem_house, f$cur_dem_senate))
  expect_equal(c(h$dem_share, s$dem_share), c(f$dem_share_house, f$dem_share_senate))
  expect_equal(c(h$dem_share_hill, s$dem_share_hill), c(f$dem_share_hill_house, f$dem_share_hill_senate))
  expect_equal(h$exp_dem_own_chamber_method, f$exp_dem_house_method)
  # the fintech Senate 2026 flag sits on its Senate rows only, in the coordinator's wording, with the Kalshi co-founder
  # attribution verified from the donor-level rows of the pinned analytics index (Paul's option A)
  expect_identical(sy$shift_flag_senate[sy$study_sector == "fintech" & sy$year == 2026],
                   paste0("fintech Senate 2026: partial year; $501,549.59 of fintech-sector giving to the NRSC, of which $500,000.00 ",
                          "from Kalshi's co-founders MANSOUR, TAREK and LARA, LUANA LOPES (verified from donor-level rows); 04 shows ",
                          "$600,000 from Kalshi employees to Republican party committees"))
  expect_false(any(grepl("dominated", c(sy$shift_flag_senate, sy$shift_flag_all, sc$shift_flag))))
  expect_true(is.na(sy$shift_flag_house[sy$study_sector == "fintech" & sy$year == 2026]))
  expect_match(sc$shift_flag[sc$study_sector == "fintech" & sc$year == 2026 & sc$chamber == "Senate"], "partial year", fixed = TRUE)
  expect_true(all(is.na(sy$shift_flag_senate[sy$year < 2026])))
  expect_true(all(c("shift_08", "shift_08_hill", "shift_04") %in% names(shift_env$out$built)))
  expect_true(all(vapply(shift_env$out$built[c("shift_08", "shift_08_hill", "shift_04")], function(b) isTRUE(b$built), TRUE)))
})

test_that("a zero D + R base is a missing share, never 0; no Hill sheet: the Hill variants are NOT BUILT", {
  base <- tmp_dir()
  data <- shift_world(file.path(base, "data"), hill = FALSE, zero_base = TRUE)
  wbs <- sgs_load_all(data, PAUL)
  sy <- sgs_build_sector_year(wbs, PAUL)
  st <- sgs_build_shift_tables(wbs, sy)
  r <- st$shift_year[st$shift_year$study_sector == "credit_unions" & st$shift_year$year == 2022, ]
  expect_true(is.na(r$dem_share_senate))
  expect_equal(r$dem_share_senate_status, "missing")
  expect_false(st$built$shift_08_hill$built)
  expect_match(st$built$shift_08_hill$note, "has no sheet sector_year_chamber_with_hill yet", fixed = TRUE)
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "r"), B = 99, only = c("SHIFT-House-Hill-PV", "SHIFT-Senate-PV"),
                   rules = PAUL)
  rr <- setNames(out$est_rows, vapply(out$est_rows, `[[`, "", "test_id"))
  expect_equal(rr[["SHIFT-House-Hill-PV"]]$status, SGS_NOT_BUILT)
  expect_equal(rr[["SHIFT-Senate-PV"]]$status, SGS_ESTIMABLE)
  expect_match(rr[["SHIFT-Senate-PV"]]$exclusions, "dem_share_senate unusable: 1", fixed = TRUE)
})

test_that("gates: the preview runs on 2021-2025 now; the main window needs 2020 and switches on by itself when it lands", {
  r <- shift_env$rows
  for (id in c("SHIFT-House", "SHIFT-Chamber", "SHIFT-All")) {
    expect_equal(r[[id]]$status, SGS_NOT_ESTIMABLE, info = id)
    expect_match(r[[id]]$reason_short, "5 of 6 years (2021-2025)", fixed = TRUE, info = id)
    expect_equal(r[[paste0(id, "-PV")]]$status, SGS_ESTIMABLE, info = id)
    expect_equal(r[[paste0(id, "-PV")]]$window_used, "2021-2025")
    expect_equal(r[[paste0(id, "-PV")]]$label, "PREVIEW")
  }
  expect_equal(r[["SHIFT-House-PV"]]$n, 30)                 # 6 units x 5 years
  expect_equal(r[["SHIFT-Chamber-PV"]]$n, 60)               # x 2 chambers
  expect_equal(r[["SHIFT-House-PV"]]$cluster_by, "Mentat industry")
  expect_equal(r[["SHIFT-House-PV"]]$n_clusters, 6)
  expect_equal(r[["SHIFT-House-FD-PV"]]$status, SGS_ESTIMABLE)   # 4 year-to-year changes from the 5 preview years
  expect_equal(r[["SHIFT-House-FD-PV"]]$years, "2022-2025")
  expect_match(r[["SHIFT-House-FD-PV"]]$gate_rule, ">= 4 year-to-year changes", fixed = TRUE)
  # 2020 in 04 / 08: the main window 2020-2025 passes
  base <- tmp_dir()
  data <- shift_world(file.path(base, "data"), contrib_years = 2020:2025)
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "r"), B = 99, only = c("SHIFT-House", "SHIFT-Chamber", "SHIFT-All-FD"),
                   rules = PAUL)
  rr <- setNames(out$est_rows, vapply(out$est_rows, `[[`, "", "test_id"))
  expect_equal(rr[["SHIFT-House"]]$status, SGS_ESTIMABLE)
  expect_equal(rr[["SHIFT-House"]]$window_used, "2020-2025")
  expect_equal(rr[["SHIFT-House"]]$label, "CORE")
  expect_equal(rr[["SHIFT-Chamber"]]$status, SGS_ESTIMABLE)
  expect_equal(rr[["SHIFT-All-FD"]]$status, SGS_NOT_ESTIMABLE)   # 5 changes (2021-2025) until 2019 is in: 5 of 6
  expect_false(isTRUE(out$results[["SHIFT-House"]]$identification$saturated))   # 6 years for 5 year-level parameters
  expect_equal(out$results[["SHIFT-House"]]$identification$df, 1)
})

test_that("estimates recover the known model; lm() = pipeline (weighted and stacked); the fixed-effect columns span unit x chamber", {
  e <- function(tid, v) shift_coef(tid, v)[[1]]$estimate
  expect_equal(e("SHIFT-House-PV", "exp_dem_house"), SHIFT_BETA[["own"]], tolerance = 0.1)
  expect_equal(e("SHIFT-Chamber-PV", "exp_dem_own_chamber"), SHIFT_BETA[["own"]], tolerance = 0.05)
  expect_equal(e("SHIFT-All-PV", "exp_dem_house"), SHIFT_BETA[["h"]], tolerance = 0.05)
  expect_equal(e("SHIFT-All-PV", "exp_dem_senate"), SHIFT_BETA[["s"]], tolerance = 0.05)
  chk <- shift_env$out$summary_checks
  sh <- chk[startsWith(chk$test_id, "SHIFT"), ]
  n_est <- sum(vapply(shift_env$out$est_rows, function(r) r$family %in% c("SHIFT", "SHIFT-PV") && r$status == SGS_ESTIMABLE, TRUE))
  expect_equal(n_est, 39)                                    # 21 previews + 18 minimum-base previews; STRICT previews: 3 years
  expect_equal(length(unique(sh$test_id)), n_est)
  expect_true(all(sh$agree))
  expect_lt(max(sh$rel_diff[!sh$zero_both]), 1e-8)
  # weighted: the pipeline equals lm(weights = the D + R dollars)
  att <- sgs_decision_chosen(shift_env$out$decisions[["SHIFT-House-W-PV"]])
  df <- att$sample$df
  f <- lm(dem_share_house ~ exp_dem_house + cur_dem_house + pres_year + midterm_year + factor(study_sector), data = df,
          weights = dem_share_house_base_real_m)
  expect_equal(unname(coef(f)["exp_dem_house"]), e("SHIFT-House-W-PV", "exp_dem_house"), tolerance = 1e-9)
  expect_false(isTRUE(all.equal(e("SHIFT-House-W-PV", "exp_dem_house"), e("SHIFT-House-PV", "exp_dem_house"))))
  # the weighted CR1 equals the WLS sandwich clustered by unit
  X <- model.matrix(f); w <- df$dem_share_house_base_real_m; u <- residuals(f)
  A <- solve(crossprod(X * sqrt(w)))
  S <- rowsum(X * (w * u), df$study_sector)
  G <- nrow(S); n <- nrow(X); p <- ncol(X)
  V <- G / (G - 1) * (n - 1) / (n - p) * A %*% crossprod(S) %*% A
  expect_equal(shift_coef("SHIFT-House-W-PV", "exp_dem_house")[[1]]$cr1_se, sqrt(V["exp_dem_house", "exp_dem_house"]), tolerance = 1e-8)
  # stacked: one baseline per unit x chamber
  d <- sgs_decision_chosen(shift_env$out$decisions[["SHIFT-Chamber-PV"]])$design
  expect_equal(sum(startsWith(d$names, "FE:")), 12)
  expect_true(all(grepl("\\|(House|Senate)$", d$names[startsWith(d$names, "FE:")])))
  txt <- readLines(shift_env$out$summaries, encoding = "UTF-8")
  flat <- gsub("\\s+", "", paste(txt, collapse = ""))
  expect_match(flat, "factor(chamber)+factor(study_sector)+factor(study_sector):factor(chamber),data=sample)", fixed = TRUE)
  expect_match(flat, "data=sample,weights=dem_share_house_base_real_m)", fixed = TRUE)
})

test_that("identification: year-level parameters, df, saturation and each year's OLS weight (weights reproduce the estimate)", {
  res <- shift_env$out$results
  idh <- res[["SHIFT-House-PV"]]$identification
  expect_true(idh$saturated)                                 # 5 year-level parameters on 5 years
  expect_equal(c(idh$cells, idh$K, idh$df), c(5, 5, 0))
  expect_match(idh$text[1], "SATURATED", fixed = TRUE)
  idc <- res[["SHIFT-Chamber-PV"]]$identification
  expect_false(idc$saturated)
  expect_equal(c(idc$cells, idc$K, idc$df), c(10, 6, 4))    # common, chamber, exp_own, cur_own, pres, mid on 10 cells
  # b = sum_i w_i y_i: on a balanced panel, b = sum over cells of the cell weight x the cell's mean share
  for (tid in c("SHIFT-House-PV", "SHIFT-Chamber-PV", "SHIFT-All-PV")) {
    att <- sgs_decision_chosen(shift_env$out$decisions[[tid]])
    df <- att$sample$df
    cells <- att$design$cells
    wl <- res[[tid]]$identification$weights
    for (f in names(wl)) {
      means <- tapply(df$y, cells, mean)[names(wl[[f]])]
      expect_equal(sum(wl[[f]] * means), shift_coef(tid, f)[[1]]$estimate, tolerance = 1e-9, info = paste(tid, f))
      # OLS weights: they sum to 0 (the common level) and weight the focal's own cell values to 1
      expect_equal(sum(wl[[f]]), 0, tolerance = 1e-9)
      xv <- tapply(att$design$X[, f], cells, mean)[names(wl[[f]])]
      expect_equal(sum(wl[[f]] * xv), 1, tolerance = 1e-9)
    }
  }
  # the cell-level check fails a design whose year-level terms cannot be separated (constant cur_dem_house)
  d <- sgs_decision_chosen(shift_env$out$decisions[["SHIFT-House-PV"]])$design
  d$X[, "cur_dem_house"] <- 1
  chk <- sgs_year_level_check(d)
  expect_false(chk$ok)
  expect_match(chk$why, "year-level design not identified", fixed = TRUE)
  expect_match(chk$why, "cur_dem_house", fixed = TRUE)
  # the note and the summary block carry the dollar base and the identification lines
  r <- shift_env$rows[["SHIFT-All-PV"]]
  expect_match(r$note, "party-labelled general giving D + R $", fixed = TRUE)
  expect_match(r$note, "non_giving 'other receipt' rows", fixed = TRUE)
  expect_match(r$note, "Identification: exp_dem_house varies only by year", fixed = TRUE)
  txt <- readLines(shift_env$out$summaries, encoding = "UTF-8")
  expect_true(any(startsWith(txt, "  dollar base       (30 unit-years of the estimated sample, 2021-2025): ")))
  expect_true(any(startsWith(txt, "  identification    exp_dem_own_chamber varies only by year and chamber")))
  i <- which(startsWith(txt, "==== SHIFT-House-PV  [PREVIEW]"))
  expect_false(grepl("Identification:", txt[i + 2], fixed = TRUE))   # the header keeps the note without the extra lines
})

test_that("first differences stay within unit and chamber; the flags and dollar bases are carried from year t", {
  att <- sgs_decision_chosen(shift_env$out$decisions[["SHIFT-Chamber-FD-PV"]])
  df <- att$sample$df
  sc <- shift_env$out$tables$shift_chamber
  x <- df[df$study_sector == "crypto" & df$year == 2024 & df$chamber == "Senate", ]
  lv <- function(y) sc$dem_share[sc$study_sector == "crypto" & sc$year == y & sc$chamber == "Senate"]
  expect_equal(x$dem_share, lv(2024) - lv(2023))
  expect_equal(x$dem_share_base_usd, sc$dem_share_base_usd[sc$study_sector == "crypto" & sc$year == 2024 & sc$chamber == "Senate"])
  expect_equal(x$exp_dem_own_chamber_method, "forecaster_final_call_binary")
  expect_equal(nrow(df), 6 * 4 * 2)
  expect_equal(sum(startsWith(att$design$names, "FE:")), 0)       # no intercept, no baselines
  fl <- shift_env$rows[["SHIFT-Chamber-FD-PV"]]$input_flags
  expect_match(fl, "exp_dem_own_chamber: House 2023 forecaster_final_call_binary (measured Nov 2024, after the year); Senate 2023 ",
               fixed = TRUE)                                      # the stacked table names the chamber of each flag
  expect_match(fl, "Senate 2025 market_snapshot (measured Sep 2026, after the year)", fixed = TRUE)
})

test_that("TRENDS: sign and size in plain units, the hypothesis' sign, sign agreement across variants, then p and CI", {
  tr <- shift_env$out$trends
  expect_true(all(SGS_TREND_COLS %in% names(tr)))
  p <- tr[tr$scope == "pooled", ]
  est <- Filter(function(c) is.null(c$left_out) && !identical(c$test, "joint"), shift_env$out$coef_rows)
  expect_equal(nrow(p), length(est))
  x <- p[p$test_id == "SHIFT-House-PV" & p$coefficient == "exp_dem_house", ]
  c0 <- shift_coef("SHIFT-House-PV", "exp_dem_house")[[1]]
  expect_equal(x$plain_value, 100 * c0$estimate)
  expect_match(x$plain_unit, "^share points of the Democratic share per unit \\(0-1\\) of expected Democratic House control")
  expect_match(x$size, " per 0.1)", fixed = TRUE)
  expect_equal(x$sign, if (c0$estimate > 0) "+" else "-")
  expect_equal(x$predicted_sign, "+")
  expect_equal(x$matches_prediction, if (c0$estimate > 0) "yes" else "no")
  expect_equal(x$trend_group, "SHIFT-House")
  expect_equal(x$boot_p, c0$boot_p)
  expect_equal(x$ci_text, c0$ci_text)
  expect_match(x$identification, "^SATURATED")
  expect_equal(x$term_label, SGS$SATURATED_LABEL)
  # saturated variants take no part in the sign agreement; the non-saturated stacked previews do
  g <- p[p$trend_group == "SHIFT-House" & p$coefficient == "exp_dem_house", ]
  expect_equal(sort(g$test_id), sort(c("SHIFT-House-PV", "SHIFT-House-Hill-PV", "SHIFT-House-FD-PV", "SHIFT-House-W-PV")))
  expect_true(all(g$same_sign_across_variants == paste0("n/a (", SGS$SATURATED_LABEL, ")")))
  gc <- p[p$trend_group == "SHIFT-Chamber" & p$coefficient == "exp_dem_own_chamber", ]
  expect_equal(sort(gc$test_id), sort(c("SHIFT-Chamber-PV", "SHIFT-Chamber-Hill-PV", "SHIFT-Chamber-FD-PV", "SHIFT-Chamber-W-PV")))
  same <- length(unique(gc$sign)) == 1
  expect_true(all(gc$same_sign_across_variants == if (same) "yes" else "no"))
  expect_true(all(gc$n_variants == 4))
  expect_true(all(p$trend_group[grepl("-B(25|10|50)K-PV$", p$test_id)] %in% paste0("SHIFT-", c("House", "Senate", "Chamber", "All", "All-House", "All-Senate"), "-minbase")))
  # per-sector rows come from the strata (the stacked model has 4 residual df per unit)
  s <- tr[tr$test_id == "SHIFT-Chamber-PV" & tr$scope != "pooled", ]
  expect_equal(sort(s$scope), sort(c(SHIFT_SECTORS, "community_banks")))
  expect_true(all(is.na(s$boot_p)))
  expect_match(p$sectors_plus_minus[p$test_id == "SHIFT-Chamber-PV"], " of 6 estimated$")
  # the sheet and the report section
  expect_true("trends" %in% readxl::excel_sheets(shift_env$out$xlsx))
  md <- paste(readLines(shift_env$out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, "## Trends: sign and size first, then p and CI", fixed = TRUE)
  expect_match(md, "| test | label | term | sign | size (plain units) | hypothesis | same sign across variants | sectors | p | 95% CI |", fixed = TRUE)
})

test_that("coordinator's rulings of 2026-09-26: unweighted primary, SHIFT-Chamber the primary preview reading, SATURATED kept", {
  rp <- sgs_registry(PAUL)
  for (id in c("SHIFT-House", "SHIFT-Chamber-PV", "SHIFT-All", "SHIFT-House-W", "SHIFT-All-Senate-W-PV")) {
    expect_match(rp[[id]]$note, SGS_SHIFT_WEIGHT_NOTE, fixed = TRUE, info = id)
  }
  expect_match(SGS_SHIFT_WEIGHT_NOTE, "unweighted model (every unit-year counts equally) is the primary SHIFT model", fixed = TRUE)
  expect_match(SGS_SHIFT_WEIGHT_NOTE, "-W variant is ROBUSTNESS only", fixed = TRUE)
  expect_equal(unique(vapply(rp[grepl("^SHIFT-.*-W$", names(rp))], `[[`, "", "label")), "ROBUSTNESS")
  md <- paste(readLines(shift_env$out$report, encoding = "UTF-8"), collapse = "\n")
  tr <- sub("## Model fit.*$", "", sub("^.*## Trends: ", "", md))    # the TRENDS section only
  expect_match(tr, "SHIFT-Chamber is the primary reading of the preview", fixed = TRUE)
  expect_match(tr, paste0("labelled ", SGS$SATURATED_LABEL), fixed = TRUE)
  expect_match(md, paste0("- Primary reading: SHIFT preview (coordinator's rulings of 2026-09-26): the six pre-specified SHIFT ",
                          "models are primary"), fixed = TRUE)
  expect_true(any(grepl("the unweighted models are primary (-W = ROBUSTNESS; weighting changes the population and the",
                        sgs_paul_build_notes(), fixed = TRUE)))
  # the SATURATED label stays on the saturated previews, and SHIFT-Chamber keeps its year-level df
  p <- shift_env$out$trends
  expect_match(p$identification[p$test_id == "SHIFT-House-PV" & p$scope == "pooled"], "^SATURATED")
  expect_match(p$identification[p$test_id == "SHIFT-Chamber-PV" & p$scope == "pooled"], "^4 cell-level residual df")
  # the dictionary states the flag in the same verified terms (the Kalshi co-founder attribution, Paul's option A)
  dic <- readxl::read_excel(shift_env$out$xlsx, sheet = "dictionary")
  expect_true(any(grepl(SGS$SHIFT_FLAGS[[1]]$text, dic$definition, fixed = TRUE)))
})

test_that("TRENDS: the stated hypotheses' signs (SHIFT +, CONTRACT +, ASYM-SLOPES decline-year slopes -)", {
  rp <- sgs_registry(PAUL)
  expect_equal(rp[["CONTRACT-a-L1-LV"]]$predicted_sign, c(contracted_prior = "+"))
  expect_equal(rp[["CONTRACT-b-C1"]]$predicted_sign, c(contracted_prior = "+"))
  expect_equal(rp[["ASYM-SLOPES-L1-LV"]]$predicted_sign, c(growth_previous_year_pct_neg = "-"))
  expect_equal(.trend_predicted(rp[["CONTRACT-b-L1-LV"]], "contracted_prior:telecom"), "+")
  expect_equal(.trend_predicted(rp[["ASYM-SLOPES-L1-LV"]], "growth_previous_year_pct_neg:commercial_banks"), "-")
  expect_equal(.trend_predicted(rp[["ASYM-SLOPES-L1-LV"]], "growth_previous_year_pct_pos:commercial_banks"), "")
  expect_equal(.trend_predicted(rp[["L1-LV"]], "growth_previous_year_pct"), "")
  expect_equal(.trend_predicted(rp[["SHIFT-All-W-PV"]], "exp_dem_senate"), "+")
  expect_length(sgs_registry(PARITY)[["C1"]]$predicted_sign, 0)
})

test_that("Glass Box progress: every 25th test emits, also when it is a derived read-out", {
  base <- tmp_dir()
  data <- synth_build(file.path(base, "data"))
  seen <- character(0)
  out <- sgs_run(data_dir = data, results_dir = file.path(base, "r"), B = 99, only = c("C1", "C2", "C3", "L1", "L2", "L3", "H1", "H4"),
                 rules = PAUL,
                 log = function(...) NULL, progress = function(stage, summary) if (stage == "estimate") seen <<- c(seen, summary))
  ids <- vapply(out$registry, `[[`, "", "id")
  expect_identical(out$registry[[25]]$variant, "derived")          # the 25th test is a derived read-out
  expect_true(paste0("25 of ", length(ids), " tests decided") %in% seen)
  expect_equal(length(seen), length(ids) %/% 25)
})

test_that("TRENDS helpers: plain units, variant groups and zero signs", {
  a <- sgs_trend_plain(0.123, "Democratic share (0-1) per unit (0-1) of expected Democratic House control")
  expect_equal(a$value, 12.3)
  expect_match(a$text, "^\\+12\\.3000 share points of the Democratic share per unit \\(0-1\\) of expected Democratic House control \\(\\+1\\.2300 per 0\\.1\\)$")
  b <- sgs_trend_plain(-0.35, "$M 2025 per percentage point of growth")
  expect_equal(b$text, "-0.3500 $M 2025 per percentage point of growth")
  expect_equal(sgs_trend_plain(0.0761, "probability (0-1) of any money > 0 per point of toughness_general (0 safe ... 3 toss-up)")$value, 7.61)
  expect_equal(sgs_trend_plain(4045.46, "USD 2025 per point of toughness_general (0 safe ... 3 toss-up)")$value, 4045.46)
  expect_equal(.trend_sign(1e-17), "0")
  expect_equal(.trend_sign(-2e-3), "-")
  reg <- sgs_registry(PAUL)
  grp <- function(id) sgs_trend_group(reg[[id]], reg)
  expect_equal(grp("R-LV-thin-L1"), "L1-LV")
  expect_equal(grp("R-TW-L1-LV"), "L1-LV")
  expect_equal(grp("C1-PV-reduced"), "C1")
  expect_equal(grp("SHIFT-Chamber-W-PV"), "SHIFT-Chamber")
  expect_equal(grp("SHIFT-All-Senate-FD"), "SHIFT-All")
  expect_equal(grp("H5-within-log1p"), "H5")
  expect_equal(grp("ASYM-L1-LV"), "ASYM-L1-LV")
  expect_equal(grp("DS+Hill-House-C1"), "DS-House-C1")
  expect_equal(.trend_key("growth_previous_year_pct_tw"), "growth_previous_year_pct")
  expect_equal(.trend_key("growth_previous_year_pct_neg:telecom"), "growth_previous_year_pct_neg:telecom")
})

# ---- FORECAST backtest ------------------------------------------------------------------------------------------------

# 2007 is the lag year, as in the live panel: the first change is 2008, so the origin 2014 has six training years.
fc_toy <- function(years = 2007:2023, sectors = c("a_sector", "b_sector"), noise = 0, seed = 5) {
  set.seed(seed)
  rows <- list()
  for (i in seq_along(sectors)) {
    y <- 10 * i
    for (t in years) {
      pres <- as.numeric(t %% 4 == 0); mid <- as.numeric(t %% 4 == 2)
      y <- y + 0.5 * i + 3 * pres - 1.3 * mid + rnorm(1, 0, noise)   # the change: sector drift + cycle position (never 0)
      rows[[length(rows) + 1L]] <- list(study_sector = sectors[i], year = t, y = y, pres_year = pres, midterm_year = mid)
    }
  }
  d <- .rows_df(rows)
  d$y_lag <- d$y[match(paste(d$study_sector, d$year - 1), paste(d$study_sector, d$year))]
  d$dy <- d$y - d$y_lag
  for (v in c("growth_previous_year_pct", "predicted_growth_pct", "exp_dem_house", "exp_dem_senate", "cur_dem_house",
              "cur_dem_senate", "contracted_prior")) d[[v]] <- NA_real_
  d$position <- .fc_position(d$pres_year, d$midterm_year)
  d
}

test_that("backtest: naive, seasonal naive and a change model on a known series; no forecast uses the target year or later", {
  p <- fc_toy()
  bt <- sgs_fc_backtest(p, 2014:2023, "toy")
  rw <- bt$rows
  n0 <- rw[rw$model == "0", ]
  expect_equal(n0$forecast, n0$anchor_prev_year)
  expect_equal(n0$anchor_prev_year, p$y[match(paste(n0$study_sector, n0$target_year - 1), paste(p$study_sector, p$year))])
  s <- rw[rw$model == "0s" & rw$target_year == 2016 & rw$study_sector == "a_sector", ]   # presidential: 2012
  expect_equal(s$forecast, p$y[p$study_sector == "a_sector" & p$year == 2012])
  s <- rw[rw$model == "0s" & rw$target_year == 2017 & rw$study_sector == "a_sector", ]   # odd: 2015
  expect_equal(s$forecast, p$y[p$study_sector == "a_sector" & p$year == 2015])
  m1 <- rw[rw$model == "1", ]
  expect_true(all(abs(m1$error) < 1e-9))            # the true model: exact forecasts
  expect_true(all(m1$beats_naive))
  for (id in c("2a", "2b")) {                       # growth inputs missing: no forecast, and why (not a DESCRIPTIVE origin)
    m2 <- rw[rw$model == id, ]
    expect_true(all(is.na(m2$forecast)), info = id)
    expect_match(m2$reason[1], "no complete training row", fixed = TRUE)
    expect_false(any(m2$descriptive), info = id)
  }
  # the common set: models that forecast no sector-year at all (2a)-(4) are reported, not required
  expect_true(all(rw$in_common_set))
  expect_true(all(rw$timing == "retrospective"))
  # no look-ahead: changing the target year and every later year leaves the forecasts of a target unchanged
  for (T in c(2015, 2019, 2023)) {
    q <- p
    fut <- q$year >= T
    q$y[fut] <- q$y[fut] + 1000
    q$y_lag <- q$y[match(paste(q$study_sector, q$year - 1), paste(q$study_sector, q$year))]
    q$dy <- q$y - q$y_lag
    b2 <- sgs_fc_backtest(q, T, "toy")$rows
    a <- rw[rw$target_year == T, ]
    expect_equal(b2$forecast[b2$model != "0"], a$forecast[a$model != "0"], info = T)
    expect_equal(b2$forecast[b2$model == "0"], a$forecast[a$model == "0"], info = T)   # the anchor is T - 1
  }
})

test_that("backtest: a rank-deficient training design keeps its forecasts as DESCRIPTIVE (J) and says why; metrics on the common and own sets", {
  p <- fc_toy(noise = 0.5)
  p$exp_dem_house <- ifelse(p$year >= 2016, 0.4 + 0.01 * (p$year - 2016), 0.5)   # constant before 2016: not identified
  p$exp_dem_senate <- 0.3 + 0.02 * (p$year %% 7)
  p$cur_dem_house <- as.numeric(p$year %in% 2019:2022); p$cur_dem_senate <- as.numeric(p$year %in% c(2008:2014, 2021:2024))
  p$growth_previous_year_pct <- sin(p$year + nchar(p$study_sector)); p$predicted_growth_pct <- cos(p$year)
  p$contracted_prior <- as.numeric(p$growth_previous_year_pct < 0)
  bt <- sgs_fc_backtest(p, 2014:2023, "toy")
  rw <- bt$rows
  m3 <- rw[rw$model == "3" & rw$target_year == 2014, ]
  expect_true(all(!is.na(m3$forecast)))                     # J: the origin is not dropped
  expect_true(all(m3$descriptive))
  expect_match(m3$reason[1], "training design not identified", fixed = TRUE)
  og <- sgs_rows_df(bt$origins, c("backtest", "target_year", "model", "ok", "reason", "n_train", "train_years"))
  expect_false(og$ok[og$model == "3" & og$target_year == 2014])   # the design as specified still fails the gate
  expect_true(og$ok[og$model == "3" & og$target_year == 2023])
  # metrics: MAE / RMSE and the share beating naive, from the rows
  mt <- bt$metrics
  k <- rw$model == "2b" & !is.na(rw$forecast) & !rw$descriptive
  x <- mt[mt$set == "own" & mt$scope == "pooled" & mt$model == "2b", ]
  expect_equal(x$mae, mean(abs(rw$error[k])))
  expect_equal(x$rmse, sqrt(mean(rw$error[k]^2)))
  nv <- rw$abs_error[rw$model == "0"][match(paste(rw$target_year[k], rw$study_sector[k]),
                                            paste(rw$target_year[rw$model == "0"], rw$study_sector[rw$model == "0"]))]
  expect_equal(x$n_beats_naive, sum(abs(rw$error[k]) < nv))
  expect_equal(x$share_beats_naive, mean(abs(rw$error[k]) < nv))
  cs <- rw[rw$in_common_set, ]
  expect_true(all(tapply(!is.na(cs$forecast) & !cs$descriptive, paste(cs$target_year, cs$study_sector), all)))
  xc <- mt[mt$set == "common" & mt$scope == "pooled" & mt$model == "0", ]
  expect_equal(xc$n, sum(cs$model == "0"))
  expect_true(all(c("pooled", "a_sector", "b_sector", "target 2023") %in% mt$scope))
})

test_that("backtest metrics: a missing naive forecast leaves the naive-relative metrics to the rows that have one (S-1: no error)", {
  p <- fc_toy(noise = 0.5)
  rw <- sgs_fc_backtest(p, 2014:2018, "toy")$rows
  # the naive forecast is absent on one sector-year (its forecast, error and absolute error are NA); model (1) still forecasts it
  gone <- rw$model == "0" & rw$target_year == 2016 & rw$study_sector == "a_sector"
  expect_equal(sum(gone), 1)
  rw[gone, c("forecast", "error", "abs_error")] <- NA_real_
  x <- sgs_fc_metrics(rw, "toy")
  x <- x[x$set == "own" & x$scope == "pooled" & x$model == "1", ]
  key <- paste(rw$target_year, rw$study_sector)
  nv <- rw$abs_error[rw$model == "0"][match(key, key[rw$model == "0"])]
  k <- rw$model == "1" & !is.na(rw$forecast)
  kn <- k & !is.na(nv)
  expect_equal(sum(k) - sum(kn), 1)
  expect_equal(x$n, sum(k))                                    # n, MAE and RMSE keep every forecast row
  expect_equal(x$mae, mean(abs(rw$error[k])))
  expect_equal(x$rmse, sqrt(mean(rw$error[k]^2)))
  expect_equal(x$naive_mae, mean(nv[kn]))                      # the naive-relative metrics use the rows where the naive forecast exists
  expect_equal(x$rel_mae, mean(abs(rw$error[kn])) / mean(nv[kn]))
  expect_equal(x$n_beats_naive, sum(abs(rw$error[kn]) < nv[kn]))
  expect_equal(x$share_beats_naive, mean(abs(rw$error[kn]) < nv[kn]))
  # a strict origin before the 20 January filing deadline: no last-year value is reported, so the naive forecast is absent
  # everywhere, while the seasonal naive forecast (an older year) is not
  q <- fc_toy(noise = 0.5)
  q$avail__y <- as.Date(paste0(q$year + 1L, "-01-20"))
  old <- get("SGS", envir = globalenv())
  early <- old; early$FORECAST_ORIGIN_MMDD <- "01-15"
  assign("SGS", early, envir = globalenv())
  bs <- tryCatch(sgs_fc_backtest(q, 2016:2018, "contributions (04)", strict = TRUE), finally = assign("SGS", old, envir = globalenv()))
  expect_equal(get("SGS", envir = globalenv())$FORECAST_ORIGIN_MMDD, "02-01")
  expect_true(all(is.na(bs$rows$forecast[bs$rows$model == "0"])))
  expect_true(any(!is.na(bs$rows$forecast[bs$rows$model == "0s"])))
  y <- bs$metrics[bs$metrics$set == "own" & bs$metrics$scope == "pooled" & bs$metrics$model == "0s", ]
  expect_true(y$n > 0 && is.finite(y$mae))
  expect_true(is.na(y$naive_mae) && is.na(y$rel_mae) && is.na(y$n_beats_naive) && is.na(y$share_beats_naive))
  # the report table shows n/a for the naive-relative columns instead of a Python None
  b0 <- sgs_fc_backtest(q, 2016:2018, "contributions (04)")
  fcx <- list(runs = list(c = list(status = "RUN", note = "toy")), strict = TRUE, asof = NULL, rows = rbind(b0$rows, bs$rows),
              metrics = rbind(b0$metrics, bs$metrics),
              origins = sgs_rows_df(c(b0$origins, bs$origins), c("backtest", "timing", "target_year", "model", "ok", "reason",
                                                                 "n_train", "train_years")))
  md <- paste(sgs_forecast_md(fcx), collapse = "\n")
  expect_false(grepl("None of", md, fixed = TRUE))
  expect_match(md, "| (0s) seasonal naive: last value in the same cycle position (presidential / midterm / odd year) | ", fixed = TRUE)
})

test_that("backtest report: the beats-naive cell counts the rows that have a naive forecast when the naive coverage is partial (S-1)", {
  q <- fc_toy(noise = 0.5)
  q$avail__y <- as.Date(paste0(q$year + 1L, "-01-20"))
  q$avail__y[q$study_sector == "a_sector" & q$year == 2015] <- as.Date("2016-03-01")   # one anchor reported after the 2016 origin
  bs <- sgs_fc_backtest(q, 2014:2019, "contributions (04)", strict = TRUE)
  rw <- bs$rows
  x <- bs$metrics[bs$metrics$set == "own" & bs$metrics$scope == "pooled" & bs$metrics$model == "0s", ]
  k <- rw$model == "0s" & !is.na(rw$forecast)
  nn <- sum(!is.na(rw$beats_naive[k]))                     # the forecast rows that have a naive forecast to beat
  expect_equal(c(x$n, nn), c(sum(k), sum(k) - 1))          # 12 forecasts, 11 of them with a naive forecast
  expect_equal(x$share_beats_naive, x$n_beats_naive / nn)  # the share is over the naive rows, not over n
  fcx <- list(runs = list(c = list(status = "RUN", note = "toy")), strict = TRUE, asof = NULL, rows = rw, metrics = bs$metrics,
              origins = sgs_rows_df(bs$origins, c("backtest", "timing", "target_year", "model", "ok", "reason", "n_train", "train_years")))
  md <- paste(sgs_forecast_md(fcx), collapse = "\n")
  pct <- sgs_py_fixed(100 * x$share_beats_naive, 1)
  cell <- paste0("| ", pct, "% (", x$n_beats_naive, " of ", nn, ") |")                     # the count behind the share
  expect_equal(length(gregexpr(cell, md, fixed = TRUE)[[1]]), 2L)                          # in the common-set and the own-set table
  expect_false(grepl(paste0("| ", pct, "% (", x$n_beats_naive, " of ", x$n, ") |"), md, fixed = TRUE))
})

test_that("backtest panel: a zero-row sector-year table gives a zero-row panel and an empty backtest (S-2: no scalar NA into an empty column)", {
  z <- data.frame(study_sector = character(0), year = numeric(0), partial_year = logical(0), contributions_real_m = numeric(0),
                  contributions_status = character(0), pres_year = numeric(0), midterm_year = numeric(0), stringsAsFactors = FALSE)
  pz <- sgs_fc_panel(z, "contributions_real_m", character(0), c(2020, 2025))   # the growth, control and contraction columns are absent
  expect_equal(nrow(pz), 0L)
  expect_true(all(c("y", "y_lag", "dy", "position", SGS_FC_TERMS, "avail__y", paste0("avail__", SGS_FC_TERMS)) %in% names(pz)))
  bz <- sgs_fc_backtest(pz, 2023:2025, "empty")
  expect_equal(nrow(bz$rows), 0L)
  expect_equal(nrow(bz$metrics), 0L)
})

# ---- FORECAST backtest, owner-approved changes of 2026-09-30: (I) model (2) split into (2a) / (2b), (J) DESCRIPTIVE origins that
# fail the estimability gate are kept, (K) sector-equal relative MAE and MASE ------------------------------------------------

# A backtest panel with every model term present (2007 is the lag year, outcome years 2008-2023, three sectors): the change
# depends on the sector drift, the cycle position, predicted growth and prior-year growth, so (2a), (2b), (3) and (4) can be
# checked. Current Senate control is constant through 2014, as in the live data.
fc_toy_full <- function(years = 2007:2023, sectors = c("a_sector", "b_sector", "c_sector"), noise = 0.05, seed = 11) {
  set.seed(seed)
  ctl <- data.frame(year = years, exp_dem_house = round(runif(length(years)), 3), exp_dem_senate = round(runif(length(years)), 3),
                    cur_dem_house = as.numeric(years %in% c(2007:2010, 2019:2022)),
                    cur_dem_senate = as.numeric(years <= 2014 | years %in% 2021:2022))
  rows <- list()
  for (i in seq_along(sectors)) {
    y <- 10 * i
    for (t in years) {
      pres <- as.numeric(t %% 4 == 0); mid <- as.numeric(t %% 4 == 2)
      pg <- cos(t + i); gp <- sin(2 * t + i)
      y <- y + 0.5 * i + 3 * pres - 1.3 * mid + 0.8 * pg + 0.5 * gp + rnorm(1, 0, noise)
      cc <- ctl[ctl$year == t, ]
      rows[[length(rows) + 1L]] <- list(study_sector = sectors[i], year = t, y = y, pres_year = pres, midterm_year = mid,
                                        growth_previous_year_pct = gp, predicted_growth_pct = pg,
                                        exp_dem_house = cc$exp_dem_house, exp_dem_senate = cc$exp_dem_senate,
                                        cur_dem_house = cc$cur_dem_house, cur_dem_senate = cc$cur_dem_senate,
                                        contracted_prior = as.numeric(gp < 0))
    }
  }
  d <- .rows_df(rows)
  d$y_lag <- d$y[match(paste(d$study_sector, d$year - 1), paste(d$study_sector, d$year))]
  d$dy <- d$y - d$y_lag
  d$position <- .fc_position(d$pres_year, d$midterm_year)
  d
}

# The availability dates of the strict backtest for that world: prior-year growth carries a 2026 vintage (after every origin),
# predicted growth is dated the November before its year, current control 31 January, the outcome 20 January of the next year.
fc_toy_full_dates <- function(d) {
  d$avail__y <- as.Date(paste0(d$year + 1, "-01-20"))
  for (v in SGS_FC_TERMS) d[[paste0("avail__", v)]] <- as.Date(NA)
  d$avail__pres_year <- as.Date("1900-01-01"); d$avail__midterm_year <- as.Date("1900-01-01")
  d$avail__growth_previous_year_pct <- as.Date("2026-08-31")
  d$avail__contracted_prior <- as.Date("2026-08-31")
  d$avail__predicted_growth_pct <- as.Date(paste0(d$year - 1, "-11-30"))
  d$avail__cur_dem_house <- as.Date(paste0(d$year, "-01-31")); d$avail__cur_dem_senate <- as.Date(paste0(d$year, "-01-31"))
  d
}

fc_origins_df <- function(bt) {
  sgs_rows_df(bt$origins, c("backtest", "timing", "target_year", "model", "ok", "reason", "n_train", "train_years", "descriptive",
                            "dropped_terms", "year_level_params", "year_level_df", "resid_df", "prior_model_id"))
}

test_that("I: model (2) is split into (2a) predicted growth only and (2b) = the earlier (2); the other ids stay; a mapping keeps old runs comparable", {
  ids <- vapply(SGS_FC_MODELS, `[[`, "", "id")
  expect_equal(ids, c("0", "0s", "1", "2a", "2b", "3", "4"))
  trm <- setNames(lapply(SGS_FC_MODELS, `[[`, "terms"), ids)
  expect_equal(trm[["2a"]], c(SGS_FC_TIMING, "predicted_growth_pct"))
  expect_equal(trm[["2b"]], c(SGS_FC_TIMING, SGS_FC_GROWTH))         # the earlier model (2), term for term
  expect_equal(trm[["3"]], c(SGS_FC_TIMING, SGS_FC_GROWTH, SGS_FC_CONTROL))
  expect_equal(trm[["4"]], c(SGS_FC_TIMING, SGS_FC_GROWTH, SGS_FC_CONTROL, "contracted_prior"))
  lab <- setNames(vapply(SGS_FC_MODELS, `[[`, "", "label"), ids)
  expect_true(startsWith(lab[["2a"]], "(2a) ") && startsWith(lab[["2b"]], "(2b) "))
  expect_match(lab[["2b"]], "prior-year growth", fixed = TRUE)
  expect_false(grepl("prior-year growth", lab[["2a"]], fixed = TRUE))
  expect_true(startsWith(lab[["3"]], "(3) ") && startsWith(lab[["4"]], "(4) "))
  # the id mapping: runs before 2026-09-30 carry model "2", which is (2b) now; (2a) has no earlier id
  expect_equal(sgs_fc_model_from_prior(c("0", "0s", "1", "2", "3", "4")), c("0", "0s", "1", "2b", "3", "4"))
  expect_equal(SGS_FC_MODEL_PRIOR_ID[["2b"]], "2")
  expect_equal(SGS_FC_MODEL_PRIOR_ID[["2a"]], "")
  p <- fc_toy_full()
  bt <- sgs_fc_backtest(p, 2014:2023, "toy")
  rw <- bt$rows
  expect_equal(unique(rw$prior_model_id[rw$model == "2b"]), "2")
  expect_equal(unique(rw$prior_model_id[rw$model == "2a"]), "")
  expect_equal(unique(rw$prior_model_id[rw$model == "3"]), "3")
  expect_equal(unique(bt$metrics$prior_model_id[bt$metrics$model == "2b"]), "2")
  expect_equal(unique(fc_origins_df(bt)$prior_model_id[fc_origins_df(bt)$model == "2b"]), "2")
  expect_equal(sort(unique(rw$model)), sort(ids))
})

test_that("I: (2a) forecasts with predicted growth alone (exact on its true model), never reads prior-year growth, and (2b) still needs both", {
  p <- fc_toy_full(noise = 0)
  # the change depends on predicted growth and prior-year growth: (2b) is exact, (2a) is not
  bt <- sgs_fc_backtest(p, 2016:2023, "toy")
  rw <- bt$rows
  expect_true(all(abs(rw$error[rw$model == "2b"]) < 1e-8))
  expect_true(all(!is.na(rw$forecast[rw$model == "2a"])))
  expect_true(any(abs(rw$error[rw$model == "2a"]) > 1e-3))
  # a world whose change depends on predicted growth only: (2a) is exact
  q <- p
  q$y <- ave(3 * q$pres_year - 1.3 * q$midterm_year + 0.8 * q$predicted_growth_pct + 0.5 * as.numeric(factor(q$study_sector)),
             q$study_sector, FUN = cumsum)
  q$y_lag <- q$y[match(paste(q$study_sector, q$year - 1), paste(q$study_sector, q$year))]; q$dy <- q$y - q$y_lag
  ra <- sgs_fc_backtest(q, 2016:2023, "toy")$rows
  expect_true(all(abs(ra$error[ra$model == "2a"]) < 1e-8))
  # prior-year growth never enters (2a): scrambling it changes (2b) and leaves (2a) alone
  q2 <- p; q2$growth_previous_year_pct <- rev(q2$growth_previous_year_pct)
  rb <- sgs_fc_backtest(q2, 2016:2023, "toy")$rows
  expect_equal(rb$forecast[rb$model == "2a"], rw$forecast[rw$model == "2a"])
  expect_false(isTRUE(all.equal(rb$forecast[rb$model == "2b"], rw$forecast[rw$model == "2b"])))
  # (2a) is the change model on sector baselines + pres + midterm + predicted growth: the same as lm() on those columns
  tr <- p[p$year < 2020 & !is.na(p$dy), ]
  fit <- lm(dy ~ 0 + study_sector + pres_year + midterm_year + predicted_growth_pct, data = tr)
  tg <- p[p$year == 2020, ]
  expect_equal(rw$forecast[rw$model == "2a" & rw$target_year == 2020],
               unname(tg$y_lag + predict(fit, newdata = tg))[match(rw$study_sector[rw$model == "2a" & rw$target_year == 2020], tg$study_sector)],
               tolerance = 1e-9)
})

test_that("I: strict timing - (2a) forecasts from predicted growth dated by the origin; (2b), (3), (4) need prior-year growth and do not", {
  p <- fc_toy_full_dates(fc_toy_full())
  bs <- sgs_fc_backtest(p, 2014:2023, "toy", strict = TRUE)
  rw <- bs$rows
  expect_true(all(!is.na(rw$forecast[rw$model %in% c("0", "0s", "1", "2a")])))
  expect_true(all(is.na(rw$forecast[rw$model %in% c("2b", "3", "4")])))
  expect_match(rw$reason[rw$model == "2b"][1], "strict: values available by", fixed = TRUE)
  expect_false(any(rw$descriptive))                         # a missing input is not a design that failed the gate
  # a late predicted-growth value (after the origin) leaves that sector-year without a (2a) forecast, and says why
  q <- p
  q$avail__predicted_growth_pct[q$study_sector == "b_sector" & q$year == 2018] <- as.Date("2018-03-15")
  r2 <- sgs_fc_backtest(q, 2014:2023, "toy", strict = TRUE)$rows
  x <- r2[r2$model == "2a" & r2$target_year == 2018 & r2$study_sector == "b_sector", ]
  expect_true(is.na(x$forecast))
  expect_match(x$reason, "not available at the origin 2018-02-01: predicted_growth_pct (available 2018-03-15)", fixed = TRUE)
  # the strict common set now includes (2a): that sector-year leaves it for every model
  cs <- r2[r2$target_year == 2018 & r2$study_sector == "b_sector", ]
  expect_false(any(cs$in_common_set))
  expect_true(all(r2$in_common_set[r2$target_year == 2018 & r2$study_sector == "a_sector"]))
  # nothing later than the origin enters (2a): the 2018 values arrive after the 2018 origin, so scrambling them changes no
  # forecast of a target year up to 2018 (they are neither the target row's predictor nor a training row before it)
  q3 <- p; q3$avail__predicted_growth_pct[q3$year == 2018] <- as.Date("2018-03-15")
  q4 <- q3; q4$predicted_growth_pct[q4$year == 2018] <- 99
  r3 <- sgs_fc_backtest(q3, 2014:2023, "toy", strict = TRUE)$rows
  r4 <- sgs_fc_backtest(q4, 2014:2023, "toy", strict = TRUE)$rows
  expect_true(all(is.na(r3$forecast[r3$model == "2a" & r3$target_year == 2018])))
  expect_equal(r3$forecast[r3$target_year <= 2018], r4$forecast[r4$target_year <= 2018])
  expect_false(isTRUE(all.equal(r3$forecast[r3$model == "2a" & r3$target_year == 2019], r4$forecast[r4$model == "2a" & r4$target_year == 2019])))
})

test_that("J: an origin below the estimability gate (unidentified, or year-level residual df < 3) keeps its forecasts as DESCRIPTIVE, with the reason", {
  p <- fc_toy_full()
  bt <- sgs_fc_backtest(p, 2014:2023, "toy")
  rw <- bt$rows
  for (m in c("3", "4")) {
    d <- rw[rw$model == m & rw$target_year %in% 2014:2015, ]        # not identified (cur_dem_senate is constant through 2014)
    expect_equal(nrow(d), 6L)
    expect_true(all(!is.na(d$forecast)), info = m)
    expect_true(all(d$descriptive), info = m)
    expect_true(all(d$status == "forecast"), info = m)
    expect_true(startsWith(d$reason[1], "DESCRIPTIVE: training design not identified"), info = m)
    expect_match(d$reason[1], "not identified: cur_dem_senate", fixed = TRUE)
    expect_match(d$reason[1], "fitted without cur_dem_senate", fixed = TRUE)
    # R8 widening (the study's fallback window, sgs_fallback_window) cannot apply: the window is already every year since the start
    expect_match(d$reason[1], "no wider training window", fixed = TRUE)
    expect_match(d$reason[1], "2008-2013", fixed = TRUE)
    expect_match(d$reason[1], "year-level residual df 0 < 3 (6 year-level parameters on 6 distinct years; as specified 7 parameters on 6 years; SATURATED)", fixed = TRUE)
    expect_false(any(grepl("df -", rw$reason, fixed = TRUE)))                # no negative df is ever shown to a reader
    expect_false(any(d$in_common_set), info = m)
    # identified, but year-level residual df 1 (2016: 7 parameters on 8 years) and 2 (2017: 9 years): DESCRIPTIVE too, nothing dropped
    for (T in 2016:2017) {
      e <- rw[rw$model == m & rw$target_year == T, ]
      expect_true(all(e$descriptive) && all(!is.na(e$forecast)), info = paste(m, T))
      expect_true(startsWith(e$reason[1], paste0("DESCRIPTIVE: year-level residual df ", T - 2015, " < 3 (7 year-level parameters on ", T - 2008, " distinct years)")), info = paste(m, T))
      expect_false(grepl("fitted without", e$reason[1], fixed = TRUE))
      expect_false(any(e$in_common_set))
    }
    later <- rw[rw$model == m & rw$target_year >= 2018, ]        # year-level residual df 3 and more: passes the gate
    expect_true(all(!later$descriptive) && all(!is.na(later$forecast)), info = m)
    expect_equal(later$reason, rep("", nrow(later)))
  }
  expect_false(any(rw$descriptive[!rw$model %in% c("3", "4")]))
  # the forecast is the change model without the non-identified term (an independent lm() on the same rows)
  tr <- p[p$year < 2014 & !is.na(p$dy), ]
  fit <- lm(dy ~ 0 + study_sector + pres_year + midterm_year + growth_previous_year_pct + predicted_growth_pct + exp_dem_house +
              exp_dem_senate + cur_dem_house, data = tr)
  tg <- p[p$year == 2014, ]
  ex <- unname(tg$y_lag + predict(fit, newdata = tg))
  got <- rw$forecast[rw$model == "3" & rw$target_year == 2014]
  expect_equal(got, ex[match(rw$study_sector[rw$model == "3" & rw$target_year == 2014], tg$study_sector)], tolerance = 1e-9)
  # origins: not ok as specified, DESCRIPTIVE, the dropped term, and the year-level residual df
  og <- fc_origins_df(bt)
  o <- og[og$model == "3" & og$target_year == 2014, ]
  expect_false(o$ok); expect_true(o$descriptive); expect_equal(o$dropped_terms, "cur_dem_senate")
  expect_equal(o$year_level_params, 6); expect_equal(o$year_level_df, 0)       # 6 years, level + pres + mid + exp_h + exp_s + cur_h
  expect_equal(o$resid_df, nrow(tr) - 10)
  o <- og[og$model == "3" & og$target_year == 2016, ]
  expect_false(o$ok); expect_true(o$descriptive); expect_equal(o$dropped_terms, "")   # identified, but year-level residual df 1 < 3
  expect_equal(o$year_level_params, 7); expect_equal(o$year_level_df, 1)
  o <- og[og$model == "3" & og$target_year == 2017, ]
  expect_false(o$ok); expect_true(o$descriptive); expect_equal(o$year_level_df, 2)
  o <- og[og$model == "3" & og$target_year == 2018, ]
  expect_true(o$ok); expect_false(o$descriptive); expect_equal(o$year_level_df, 3)     # the first origin that passes
  expect_true(all(og$ok[og$model %in% c("1", "2a", "2b")]) && !any(og$descriptive[og$model %in% c("1", "2a", "2b")]))   # 3 or more year-level df
  expect_equal(og$year_level_df[og$model == "1" & og$target_year == 2014], 3)   # 6 years - (level + pres + midterm)
  # metrics: the headline sets leave the DESCRIPTIVE forecasts out; they are reported in a set of their own
  mt <- bt$metrics
  expect_setequal(unique(mt$set), c("common", "own", "descriptive"))
  k3 <- rw$model == "3" & !is.na(rw$forecast)
  own <- mt[mt$set == "own" & mt$scope == "pooled" & mt$model == "3", ]
  expect_equal(own$n, sum(k3 & !rw$descriptive))
  expect_equal(own$mae, mean(abs(rw$error[k3 & !rw$descriptive])))
  ds <- mt[mt$set == "descriptive" & mt$scope == "pooled" & mt$model == "3", ]
  expect_equal(ds$n, sum(k3 & rw$descriptive))
  expect_equal(ds$mae, mean(abs(rw$error[k3 & rw$descriptive])))
  expect_setequal(unique(mt$model[mt$set == "descriptive"]), c("3", "4"))
  expect_true(all(c("target 2014", "target 2015", "target 2016", "target 2017", "a_sector") %in% mt$scope[mt$set == "descriptive"]))
  expect_false("target 2018" %in% mt$scope[mt$set == "descriptive"])
  expect_equal(ds$n, 4 * 3)
  # the common set: 2014-2017 stay out (every model must forecast them outside the DESCRIPTIVE ones); 2018 on is in
  expect_setequal(unique(rw$target_year[rw$in_common_set]), 2018:2023)
  expect_equal(mt$n[mt$set == "common" & mt$scope == "pooled" & mt$model == "0"], 6 * 3)
})

test_that("J: year-level residual df 1 or 2 alone makes an origin DESCRIPTIVE (plenty of total residual df; nothing unidentified); 3 passes", {
  # model (1) on three sectors: 3 year-level parameters (common level, pres, midterm). A four-year window: year-level df 1.
  q <- fc_toy_full(years = 2007:2012)
  r <- sgs_fc_backtest(q, 2012, "narrow")$rows
  m1 <- r[r$model == "1", ]
  expect_true(all(!is.na(m1$forecast)) && all(m1$descriptive))
  expect_true(startsWith(m1$reason[1], "DESCRIPTIVE: year-level residual df 1 < 3 (3 year-level parameters on 4 distinct years)"))
  expect_false(grepl("training design not identified", m1$reason[1], fixed = TRUE))
  expect_false(grepl("; residual df", m1$reason[1], fixed = TRUE))            # the total residual df (7) is fine
  og <- fc_origins_df(sgs_fc_backtest(q, 2012, "narrow"))
  o <- og[og$model == "1", ]
  expect_false(o$ok); expect_true(o$descriptive); expect_equal(o$year_level_df, 1); expect_equal(o$resid_df, 12 - 5)   # 7 total residual df
  # (in this one-origin world no change model passes the gate, so none is live: the common set is that of (0) and (0s); the
  # multi-origin world above shows the sector-years of a DESCRIPTIVE origin leaving the common set)
  # five years: year-level df 2, still DESCRIPTIVE; six years: 3, passes
  for (yrs in list(2007:2013, 2007:2014)) {
    T <- max(yrs); w <- sgs_fc_backtest(fc_toy_full(years = yrs), T, "w")
    o <- fc_origins_df(w); o <- o[o$model == "1", ]
    expect_equal(o$year_level_df, length(yrs) - 2 - 3, info = as.character(T))
    expect_equal(o$descriptive, o$year_level_df < 3, info = as.character(T))
    expect_equal(o$ok, o$year_level_df >= 3, info = as.character(T))
    rr <- w$rows[w$rows$model == "1", ]
    expect_equal(all(rr$descriptive), o$year_level_df < 3, info = as.character(T))
  }
  # the gate is the study's own constant, not a literal
  old <- get("SGS", envir = globalenv())
  lax <- old; lax$MIN_RESID_DF <- 1
  assign("SGS", lax, envir = globalenv())
  w <- tryCatch(sgs_fc_backtest(q, 2012, "narrow"), finally = assign("SGS", old, envir = globalenv()))
  expect_false(any(w$rows$descriptive[w$rows$model == "1"]))             # year-level df 1 passes a minimum of 1
  expect_equal(get("SGS", envir = globalenv())$MIN_RESID_DF, 3)
})

test_that("J: a training window without a complete row, or without the sector's baseline, is still not a forecast (not DESCRIPTIVE)", {
  p <- fc_toy_full()
  p$predicted_growth_pct[p$study_sector == "c_sector"] <- NA_real_               # the sector has no predicted growth at all
  rw <- sgs_fc_backtest(p, 2014:2023, "toy")$rows
  x <- rw[rw$model %in% c("2a", "2b", "3", "4") & rw$study_sector == "c_sector", ]
  expect_true(all(is.na(x$forecast)) && !any(x$descriptive))
  expect_true(all(!is.na(rw$forecast[rw$model == "2a" & rw$study_sector == "a_sector"])))
  # an exactly determined design (as many training rows as parameters) is a DESCRIPTIVE forecast too, never dropped
  q <- fc_toy_full(years = 2007:2011, sectors = c("a_sector", "b_sector"))
  r <- sgs_fc_backtest(q, 2011, "tiny")$rows
  m2a <- r[r$model == "2a", ]                                                   # 3 training years (2008-2010): 6 rows for 2 + 3 = 5 terms
  expect_true(all(!is.na(m2a$forecast)))
  expect_true(all(m2a$descriptive))                                             # identified, but 1 residual df < the study's minimum of 3
  expect_true(startsWith(m2a$reason[1], "DESCRIPTIVE: residual df 1 < 3 (6 training rows for 5 terms); year-level residual df 0 < 3"))
  expect_false(any(is.na(m2a$forecast) & m2a$descriptive))
  # exactly as many rows as terms ((2b): 2 baselines + 4 terms on the same 6 rows): 0 residual df, still a forecast
  m2b <- r[r$model == "2b", ]
  expect_true(all(!is.na(m2b$forecast)) && all(m2b$descriptive))
  expect_true(startsWith(m2b$reason[1], "DESCRIPTIVE: residual df 0 < 3 (6 training rows for 6 terms); year-level residual df 0 < 3"))
})

test_that("K: sector-equal relative MAE and MASE next to the pooled dollar MAE; the existing columns keep their values", {
  p <- fc_toy_full(noise = 0.4)
  bt <- sgs_fc_backtest(p, 2014:2023, "toy")
  rw <- bt$rows; mt <- bt$metrics
  expect_true(all(c("rel_mae_by_sector", "mase") %in% names(mt)))
  expect_equal(names(mt)[1:14], c("backtest", "timing", "flag", "set", "scope", "model", "model_label", "n", "mae", "rmse", "naive_mae",
                                  "rel_mae", "n_beats_naive", "share_beats_naive"))   # the earlier columns stay where they were
  expect_true("naive_scale" %in% names(rw))
  key <- paste(rw$target_year, rw$study_sector)
  nv <- rw$abs_error[rw$model == "0"][match(key, key[rw$model == "0"])]
  scale_of <- function(s, T) mean(abs(p$dy[p$study_sector == s & p$year < T & !is.na(p$dy)]))
  sc <- mapply(scale_of, rw$study_sector, rw$target_year)
  expect_equal(rw$naive_scale, unname(sc), tolerance = 1e-12)   # the in-sample naive MAE of the sector at the origin
  for (m in c("0", "0s", "1", "2a", "2b", "3", "4")) {
    k <- rw$model == m & !is.na(rw$forecast) & !rw$descriptive
    x <- mt[mt$set == "own" & mt$scope == "pooled" & mt$model == m, ]
    kn <- k & !is.na(nv)
    r <- vapply(split(which(kn), rw$study_sector[kn]), function(ix) mean(abs(rw$error[ix])) / mean(nv[ix]), 0)
    expect_equal(x$rel_mae_by_sector, mean(r), info = m)                  # the mean over sectors of sector MAE / sector naive MAE
    expect_equal(x$mase, mean(abs(rw$error[k]) / sc[k]), info = m)         # each error scaled by its sector's in-sample naive MAE
    expect_equal(x$mae, mean(abs(rw$error[k])), info = m)                  # the dollar MAE is unchanged
    # a sector scope has one sector: the sector-equal ratio is the ratio of that sector
    y <- mt[mt$set == "own" & mt$scope == "a_sector" & mt$model == m, ]
    expect_equal(y$rel_mae_by_sector, y$rel_mae, info = m)
  }
  x <- mt[mt$set == "own" & mt$scope == "pooled" & mt$model == "0", ]
  expect_equal(x$rel_mae_by_sector, 1)
  # equal weight per sector differs from the pooled ratio when the sectors' naive errors differ
  x1 <- mt[mt$set == "own" & mt$scope == "pooled" & mt$model == "1", ]
  expect_false(isTRUE(all.equal(x1$rel_mae, x1$rel_mae_by_sector)))
  # a target-year scope: the sectors present that year, equally weighted
  t1 <- mt[mt$set == "own" & mt$scope == "target 2018" & mt$model == "1", ]
  kk <- rw$model == "1" & rw$target_year == 2018
  expect_equal(t1$rel_mae_by_sector, mean(abs(rw$error[kk]) / nv[kk]))
  expect_equal(t1$mase, mean(abs(rw$error[kk]) / sc[kk]))
})

test_that("K: a sector whose naive MAE is 0 is left out of the sector-equal mean (its ratio is undefined), and says so in the dictionary", {
  p <- fc_toy_full(noise = 0.4)
  cs <- p$study_sector == "c_sector"
  p$y[cs] <- 50; p$y_lag[cs] <- ifelse(is.na(p$y_lag[cs]), NA, 50); p$dy[cs] <- ifelse(is.na(p$dy[cs]), NA, 0)   # a constant series: naive error 0
  bt <- sgs_fc_backtest(p, 2018:2023, "flat")
  rw <- bt$rows; mt <- bt$metrics
  key <- paste(rw$target_year, rw$study_sector)
  nv <- rw$abs_error[rw$model == "0"][match(key, key[rw$model == "0"])]
  expect_true(all(nv[rw$study_sector == "c_sector"] == 0, na.rm = TRUE))
  for (m in c("1", "2a")) {
    x <- mt[mt$set == "own" & mt$scope == "pooled" & mt$model == m, ]
    k <- rw$model == m & !is.na(rw$forecast) & !rw$descriptive & rw$study_sector %in% c("a_sector", "b_sector")
    r <- vapply(split(which(k), rw$study_sector[k]), function(ix) mean(abs(rw$error[ix])) / mean(nv[ix]), 0)
    expect_equal(x$rel_mae_by_sector, mean(r), info = m)                  # the two sectors with a naive MAE above 0; c_sector is out
    y <- mt[mt$set == "own" & mt$scope == "c_sector" & mt$model == m, ]
    expect_true(is.na(y$rel_mae_by_sector) && is.na(y$rel_mae), info = m)  # and on its own it has no ratio
  }
  dic <- paste(vapply(Filter(function(r) identical(r[2], "rel_mae_by_sector"), SGS_PAUL_DICTIONARY), function(r) paste(r, collapse = " | "), ""), collapse = "\n")
  expect_match(dic, "naive MAE of 0 is left out of the mean", fixed = TRUE)
})

test_that("K: the MASE scale uses only the outcomes reported by the origin (strict) and a missing scale leaves the row out of MASE", {
  q <- fc_toy_full_dates(fc_toy_full(noise = 0.4))
  q$avail__y[q$study_sector == "a_sector" & q$year == 2015] <- as.Date("2016-03-01")   # one outcome reported after the 2016 origin
  bs <- sgs_fc_backtest(q, 2016:2018, "toy", strict = TRUE)
  rw <- bs$rows
  a <- q[q$study_sector == "a_sector", ]
  s16 <- unique(rw$naive_scale[rw$target_year == 2016 & rw$study_sector == "a_sector"])
  expect_equal(s16, mean(abs(a$dy[a$year %in% 2008:2014])), tolerance = 1e-12)     # the 2015 outcome (and its change) were not reported yet
  s17 <- unique(rw$naive_scale[rw$target_year == 2017 & rw$study_sector == "a_sector"])
  expect_equal(s17, mean(abs(a$dy[a$year %in% 2008:2016])), tolerance = 1e-12)     # by 2017-02-01 both 2015 (2016-03-01) and 2016 are reported
  # no in-sample change at all: the scale is NA and the row is left out of MASE, not of MAE
  fx <- sgs_fc_metrics(transform(rw, naive_scale = NA_real_), "toy", "", "strict")
  expect_true(all(is.na(fx$mase)))
  expect_true(all(is.finite(fx$mae[fx$n > 0])))
  # a zero scale (a constant series) gives no MASE either
  fz <- sgs_fc_metrics(transform(rw, naive_scale = 0), "toy", "", "strict")
  expect_true(all(is.na(fz$mase)))
})

test_that("report: the tables carry the sector-equal relative MAE and MASE, the DESCRIPTIVE forecasts, and the model-id mapping", {
  p <- fc_toy_full(noise = 0.4)
  b0 <- sgs_fc_backtest(p, 2014:2023, "LobbyView (L-LV sectors)")
  fcx <- list(runs = list(lv = list(status = "RUN", note = "toy")), strict = FALSE, asof = NULL, rows = b0$rows, metrics = b0$metrics,
              origins = sgs_rows_df(b0$origins, c("backtest", "timing", "target_year", "model", "ok", "reason", "n_train", "train_years",
                                                  "descriptive", "dropped_terms", "year_level_params", "year_level_df", "resid_df",
                                                  "prior_model_id")))
  md <- paste(sgs_forecast_md(fcx), collapse = "\n")
  expect_match(md, "| model | n | MAE | RMSE | naive MAE (same rows) | MAE / naive MAE | sector-equal MAE / naive MAE | MASE | beats naive |", fixed = TRUE)
  expect_match(md, "**DESCRIPTIVE forecasts", fixed = TRUE)                       # 2014-2015 of (3) and (4), reported apart
  expect_match(md, "not in the common set or each model's own set", fixed = TRUE)
  expect_match(md, "(2b) is the earlier model (2)", fixed = TRUE)                   # the mapping, stated
  expect_match(md, "(2a) is new", fixed = TRUE)
  expect_match(md, "| sector | n | (0) | (0s) | (1) | (2a) | (2b) | (3) | (4) |", fixed = TRUE)
  expect_match(md, "**Common set, per sector: MASE (each error over the sector's in-sample naive MAE at its origin)**", fixed = TRUE)
  expect_match(md, "| sector | (0) | (0s) | (1) | (2a) | (2b) | (3) | (4) |", fixed = TRUE)
  x <- b0$metrics[b0$metrics$set == "common" & b0$metrics$scope == "a_sector" & b0$metrics$model == "1", ]
  expect_match(md, paste0("| a_sector | ", sgs_py_fixed(b0$metrics$mase[b0$metrics$set == "common" & b0$metrics$scope == "a_sector" & b0$metrics$model == "0"], 3), " | "), fixed = TRUE)
  expect_match(md, paste0(" | ", sgs_py_fixed(x$mase, 3), " | "), fixed = TRUE)
  expect_false(grepl("| (2) ", md, fixed = TRUE))
  # the DESCRIPTIVE table names the reason of the first origin
  expect_match(md, "not identified: cur_dem_senate", fixed = TRUE)
  # D2: dropped terms and year-level residual df are listed per origin (2016 and 2017 dropped nothing)
  expect_match(md, "Model (3) fails the estimability gate at origin(s) 2014, 2015, 2016, 2017. Per origin: ", fixed = TRUE)
  expect_match(md, "2014 (dropped cur_dem_senate; year-level residual df 0), 2015 (dropped cur_dem_senate; year-level residual df 1), 2016 (dropped nothing; year-level residual df 1), 2017 (dropped nothing; year-level residual df 2)", fixed = TRUE)
  expect_false(grepl("dropped: cur_dem_senate; year-level residual df 0, 1, 1, 2", md, fixed = TRUE))
})

test_that("documentation: the build note and the sheet dictionary carry the model split, the DESCRIPTIVE label and the new metrics", {
  note <- grep("^FORECAST backtest", sgs_paul_build_notes(), value = TRUE)
  expect_length(note, 1L)
  expect_match(note, "(2a) + predicted growth only", fixed = TRUE)
  expect_match(note, "(2b) = the earlier model (2)", fixed = TRUE)
  expect_match(note, "labelled DESCRIPTIVE", fixed = TRUE)
  expect_match(note, "sector-equal MAE / naive MAE and the MASE", fixed = TRUE)
  fc_rows <- Filter(function(r) grepl("^forecast", r[1]), SGS_PAUL_DICTIONARY)
  dic <- paste(vapply(fc_rows, function(r) paste(r, collapse = " | "), ""), collapse = "\n")
  for (col in c("prior_model_id", "rel_mae_by_sector", "mase", "naive_scale", "year_level_df", "dropped_terms", "descriptive")) {
    expect_match(dic, col, fixed = TRUE, info = col)
  }
  expect_match(dic, "(2b) is the earlier model (2), term for term", fixed = TRUE)
})

test_that("build notes: model (2) does not imply that prior-year growth is known at the forecast origin (S-5)", {
  note <- grep("^FORECAST backtest", sgs_paul_build_notes(), value = TRUE)
  expect_length(note, 1L)
  expect_false(grepl("same-year growth excluded: not known at forecast time", note, fixed = TRUE))
  expect_match(note, "same-year growth is excluded; in the strict timing prior-year growth is unavailable at the origin as well",
               fixed = TRUE)
})

test_that("engine code hashes: the openssl and md5 fallbacks give plain strings under their own key (S-6)", {
  d <- tmp_dir()
  writeLines("x <- 1", file.path(d, "a.R")); writeLines("not code", file.path(d, "b.txt"))
  hashes <- function(mask) {   # sgs_engine_code_hashes() as if the masked packages were not installed
    f <- sgs_engine_code_hashes
    environment(f) <- list2env(list(requireNamespace = function(package, ..., quietly = FALSE) {
      if (package %in% mask) FALSE else base::requireNamespace(package, ..., quietly = quietly)
    }), parent = globalenv())
    f(d)
  }
  sha <- digest::digest(file = file.path(d, "a.R"), algo = "sha256")
  h <- hashes(character(0))
  expect_equal(h, list(sha256 = list(a.R = sha)))                       # only *.R files
  skip_if_not_installed("openssl")
  h <- hashes("digest")
  expect_equal(names(h), "sha256")
  expect_equal(h$sha256[["a.R"]], sha)
  expect_match(as.character(jsonlite::toJSON(h, auto_unbox = TRUE)), sha, fixed = TRUE)   # no S3 class left on the string
  h <- hashes(c("digest", "openssl"))
  expect_equal(names(h), "md5")
  expect_equal(h$md5[["a.R"]], unname(tools::md5sum(file.path(d, "a.R"))))
})

# A LobbyView sheet for the backtest world (as the other R-only test files build it): credit_arms thin throughout.
fc_lv_sheet <- function(years = 2006:2024) {
  set.seed(93)
  conf <- c(commercial_banks = "high", credit_unions = "high", crypto = "roster", credit_arms = "naics", property_casualty = "naics")
  rows <- list()
  for (s in names(conf)) for (y in years) {
    amount <- (10 + 3 * match(s, names(conf)) + 0.2 * (y - 2006) + rnorm(1, 0, 0.5)) * 1e6
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

test_that("backtest on the synthetic study: LobbyView runs (L-LV sectors); contributions wait for 2020, then run with FEW TARGETS", {
  fc <- shift_env$out$forecast
  expect_equal(fc$runs$lv$status, "NOT RUN")                         # the SHIFT world has no LobbyView sheet
  expect_equal(fc$runs$c$status, "NOT RUN")
  expect_match(fc$runs$c$note, "waits for the Mentat 2020 cycle", fixed = TRUE)
  base <- tmp_dir()
  data <- synth_build(file.path(base, "data"), expected_control = expected_control_sheet(), iem_last_year = 2022,
                      extra_sheets = list(lobbying = setNames(list(fc_lv_sheet()), SGS$LOBBYVIEW_ALL_SHEET)))  # contributions 2006-2025
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "r"), B = 99, only = "L1-LV", rules = PAUL)
  f2 <- out$forecast
  expect_equal(f2$runs$lv$status, "RUN")
  expect_equal(f2$runs$lv$sectors, c("commercial_banks", "credit_unions", "crypto", "property_casualty"))
  expect_equal(sort(unique(f2$rows$target_year[f2$rows$backtest == "LobbyView (L-LV sectors)"])), 2014:2023)
  expect_equal(f2$runs$c$status, "RUN")
  expect_equal(f2$runs$c$flag, "FEW TARGETS (3 target years)")
  cr <- f2$rows[f2$rows$backtest == "contributions (04)", ]
  expect_equal(sort(unique(cr$target_year)), 2023:2025)
  expect_true(all(cr$flag == "FEW TARGETS (3 target years)"))
  # S-3: the flag counts the target years actually forecast: without the 2025 contributions there are two
  sy2 <- out$tables$sector_year
  sy2$contributions_status[sy2$year == 2025] <- "missing"
  f3 <- sgs_forecast_run(list(sector_year = sy2), built = list(lobbyview_all = list(built = FALSE)))
  expect_equal(sort(unique(f3$rows$target_year)), 2023:2024)
  expect_equal(f3$runs$c$flag, "FEW TARGETS (2 target years)")
  expect_true(all(f3$rows$flag == "FEW TARGETS (2 target years)"))
  expect_match(f3$runs$c$note, "targets 2023-2024; FEW TARGETS (2 target years)", fixed = TRUE)
  # every forecast of target T uses training rows before T only
  ok <- f2$rows[f2$rows$model %in% c("1", "2a", "2b", "3", "4") & f2$rows$status == "forecast", ]
  last <- as.numeric(sub("^.*-", "", sub(",.*$", "", sapply(strsplit(ok$train_years, ", "), function(v) tail(v, 1)))))
  expect_true(all(last < ok$target_year))
  sh <- readxl::excel_sheets(out$xlsx)
  expect_true(all(c("forecast_backtest", "forecast_metrics", "forecast_origins") %in% sh))
  md <- paste(readLines(out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, "## Forecast backtest (the Mentat Insights upgrade test)", fixed = TRUE)
  expect_match(md, "### Contributions (04): RUN", fixed = TRUE)
  expect_match(md, "**Common set, pooled**", fixed = TRUE)
  # S-4: expected control is described per year as recorded (not "the year's annual mean" for every year)
  expect_false(grepl("the year's annual mean", md, fixed = TRUE))
  expect_match(md, paste0("expected control is measured differently by year (per-year dates in sheet expected_control_timing): ",
                          "the IEM annual mean for 2008-2022, the binary final call for the 2024 election (measured 2024-11-04) ",
                          "for 2023 and 2024, and the market snapshot of 2026-09-25 for 2025-2026"), fixed = TRUE)
})

test_that("DS+Hill reads 08 sector_year_chamber_with_hill when it is present", {
  sy <- shift_env$out$tables$sector_year
  h08 <- readxl::read_excel(file.path(shift_env$data, SGS$CHAMBER_FILE), sheet = SGS$CHAMBER_HILL_SHEET)
  x <- h08[h08$study_sector == "crypto" & h08$year == 2022 & h08$chamber == "House", ]
  r <- sy[sy$study_sector == "crypto" & sy$year == 2022, ]
  expect_equal(r$dem_share_hill_house, x$dem_share)
  expect_equal(r$dem_share_hill_house_base_usd, x$dem_usd + x$rep_usd)
  expect_true(shift_env$out$built$dem_share_hill$built)
  expect_match(shift_env$out$built$dem_share_hill$note, "DS+Hill reads this sheet", fixed = TRUE)
  expect_false("community_banks" %in% sy$study_sector)            # DS stays on the study sectors
})

test_that("outputs: sheets, report sections, receipt fields and Glass Box stages; the parity rule set has none of them", {
  out <- shift_env$out
  sh <- readxl::excel_sheets(out$xlsx)
  for (s in c("shift_year", "shift_chamber", "trends", "forecast_backtest", "forecast_metrics", "forecast_origins", "coverage")) {
    expect_true(s %in% sh, info = s)
  }
  smp <- readxl::read_excel(out$xlsx, sheet = "samples")
  expect_true("chamber" %in% names(smp))
  expect_setequal(unique(stats::na.omit(smp$chamber)), c("House", "Senate"))
  cov <- readxl::read_excel(out$xlsx, sheet = "coverage")
  sv <- cov[cov$family == "SHIFT preview 2021-2025", ]
  expect_equal(sv$status[sv$unit == "community_banks"], "IN")
  expect_equal(sv$status[sv$unit == "life_insurance"], "OUT")
  expect_match(sv$reason[sv$unit == "life_insurance"], "no Mentat contribution workbook", fixed = TRUE)
  md <- paste(readLines(out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, "## SHIFT: partisan allocation of contributions on expected control (Paul's hypothesis)", fixed = TRUE)
  expect_match(md, "D + R share of dollars", fixed = TRUE)
  expect_match(md, "Flag: fintech Senate 2026: partial year", fixed = TRUE)
  expect_match(md, "SATURATED (as many year-level parameters as years or cells", fixed = TRUE)
  expect_match(md, "First differences repeat the level estimate exactly", fixed = TRUE)
  rc <- jsonlite::fromJSON(out$receipt)
  expect_equal(rc$shift$tests, 90)
  expect_equal(rc$shift$estimable, 39)
  expect_equal(rc$shift$units, c(SHIFT_SECTORS, "community_banks"))
  expect_true(rc$trends$pooled_rows > 0)
  expect_equal(rc$forecast$runs$c$status, "NOT RUN")
  # S-6: the receipt keeps engine_code as it was and adds the sha256 of every code/R/*.R file that ran
  expect_equal(rc$engine_code, "code/R (sgs R port)")
  expect_equal(names(rc$engine_code_files), "sha256")
  mods <- list.files(SGS_TEST_CODE_DIR, pattern = "\\.R$")
  expect_setequal(names(rc$engine_code_files$sha256), mods)
  expect_true(all(c("run_all.R", "sgs_forecast.R", "sgs_run.R") %in% names(rc$engine_code_files$sha256)))
  for (m in mods) {
    expect_equal(rc$engine_code_files$sha256[[m]], digest::digest(file = file.path(SGS_TEST_CODE_DIR, m), algo = "sha256"), info = m)
  }
  expect_true(all(c("load", "panel", "summaries", "trends", "forecast") %in% shift_env$stages))
  # parity rule set: no SHIFT / TRENDS / FORECAST, no chamber column
  base <- tmp_dir()
  oq <- quiet_run(data_dir = shift_env$data, results_dir = file.path(base, "r"), B = 99, only = "C1", rules = PARITY)
  expect_null(oq$trends); expect_null(oq$forecast); expect_null(oq$shift)
  shq <- readxl::excel_sheets(oq$xlsx)
  expect_false(any(c("shift_year", "trends", "forecast_backtest") %in% shq))
  expect_false("chamber" %in% names(readxl::read_excel(oq$xlsx, sheet = "samples")))
})
