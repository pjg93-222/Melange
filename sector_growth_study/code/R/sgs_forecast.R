# FORECAST backtest (rulings of 2026-09-26; the Mentat Insights upgrade test): rolling-origin one-step-ahead forecasts
# of sector spending. For each target year T, every model is fitted only on sector-years before T and forecasts each
# sector's spending in T ($M 2025):
#   (0)  naive: last year's value, y_{T-1};
#   (0s) seasonal naive: the last value in the same election-cycle position before T (presidential, midterm or odd
#        year; the previous odd year for an odd target, four years back for an even one);
#   (1)  y_{T-1} + the predicted one-year change, the change modelled on a sector baseline (each sector's own drift) +
#        pres_year + midterm_year;
#   (2a) (1) + predicted_growth_pct (the strict-feasible growth model: the 06 predicted growth of a sector-year that has one
#        is dated before its origin; added 2026-09-30, owner-approved);
#   (2b) (2a) + growth_previous_year_pct (same-year actual growth is not known at forecast time and is never used). This is
#        the earlier model (2), term for term: runs before 2026-09-30 carry model id "2" for it (SGS_FC_MODEL_PRIOR_ID,
#        sgs_fc_model_from_prior, column prior_model_id of the three sheets);
#   (3)  (2b) + exp_dem_house + exp_dem_senate + cur_dem_house + cur_dem_senate (expected control is measured differently by
#        year, as recorded in 02 and in sheet expected_control_timing: 2008-2022 the IEM annual mean, dated by its last price;
#        2023 and 2024 the binary final call for the 2024 election, measured 2024-11-04 (after its year for 2023); 2025-2026
#        the market snapshot of 2026-09-25 (after its year for 2025); so model (3) takes within-year or later inputs and is
#        a nowcast, not a strict forecast);
#   (4)  (3) + contracted_prior.
# Models (1)-(4) are OLS on the change y_t - y_{t-1} with no intercept and one baseline per sector; they are nested in
# the naive forecast (all coefficients zero). Errors are forecast - actual. MAE, RMSE, MAE relative to the naive MAE on the
# same rows, and the share of sector-years where a model beats the naive forecast (a strictly smaller absolute error) are
# given on the common set (the sector-years every model forecasts) and on each model's own set, pooled, per sector and per
# target year. Two scale-free summaries sit beside the dollar MAE (owner-approved 2026-09-30): the sector-equal relative MAE
# (the mean over sectors of the sector's MAE / the sector's naive MAE on the same rows, so a large sector does not
# dominate; a sector whose naive MAE is 0 has no ratio and is left out of the mean) and the MASE (each absolute error divided by the in-sample naive MAE of its sector at that origin, the mean
# absolute one-step change of the outcomes reported before the target year; the mean over the rows). Nothing is imputed: a
# sector-year enters only with a usable actual value and a usable previous-year value.
#
# Estimability gate and DESCRIPTIVE forecasts (owner-approved 2026-09-30, Paul's R8: an origin is not dropped, the window is
# widened; the coordinator's ruling of 2026-09-30 fixed the stricter reading below). An origin of a change model is below the
# study's own gate (SGS$MIN_RESID_DF = 3, as in sgs_assess) when its training design is not identified (rank deficient: the
# year-level terms included), OR its residual df (training rows less the design's columns) is below the minimum, OR its
# YEAR-LEVEL residual df is below the minimum: the distinct training years less the rank of the common level the sector
# baselines span plus the year-level (national) terms of the design (0 = SATURATED, as the SHIFT designs are labelled). R8's
# remedy would be a wider training window (the primary 6-year minimum, then a run of 10 years searched in 2008-2025,
# sgs_fallback_window), but an expanding window that starts in the first year of the panel cannot be widened backwards
# (nothing earlier is usable) or forwards (look-ahead), so the forecast is never dropped: it is kept as a DESCRIPTIVE one. The
# terms that add no rank, if any, are dropped and named (their coefficient is 0), the rest is fitted on the same rows, and
# the row carries descriptive = TRUE and the reason. DESCRIPTIVE forecasts are reported (set "descriptive" of forecast_metrics,
# their own table in the report) and are kept out of the headline sets: in_common_set treats them as not forecast, and
# neither the common nor the own set counts them, so the headline sets are the origins that pass the gate. A missing input,
# or a sector without a complete training row, is not a design that failed the gate: no forecast, as before. The year-level
# residual df of the design used is reported per origin next to the residual df.
#
# Timing (coordinator's revision of 2026-09-26, after the Codex methodology review): the backtest above trains only on
# outcomes before the target year but reads every predictor from the final-vintage panel: it is RETROSPECTIVE (a final-
# vintage, pseudo-out-of-sample exercise), not evidence of a forecast available at the time. The STRICT backtest adds
# the information cutoff: the forecast origin of target year T is 1 February of T (SGS$FORECAST_ORIGIN_MMDD, after the
# prior year's LDA fourth-quarter reports, due 20 January, and FEC year-end reports, due 31 January), and every value a
# model uses - on the training rows and on the target row - must have been available by the origin:
#   outcome of year t (the anchor y_{T-1} and the training changes): 20 January (lobbying) / 31 January (contributions)
#     of t + 1, the filing deadline (the values are the current vintage, later amendments included);
#   pres_year, midterm_year: the election calendar, known in advance;
#   growth_previous_year_pct, contracted_prior: the 07 report vintage of the sector's series (end of that month);
#   predicted_growth_pct: the 06 forecast publication month (end of that month);
#   exp_dem_house / exp_dem_senate: 02 measured_at (the IEM annual mean's last price date; the fill sheet's measured_on);
#   cur_dem_house / cur_dem_senate: 31 January of the year (the majority seated in January).
# A value without a date is not available. The origin and these rules were fixed before any strict result was seen;
# nothing is tuned to the held-out outcomes. Strict and retrospective results are reported separately (column timing).
SGS_FC_TIMINGS <- c(retrospective = "retrospective (final-vintage predictors)",
                    strict = "strict (every value available by the origin, 1 February of the target year)")

SGS_FC_TIMING <- c("pres_year", "midterm_year")
SGS_FC_GROWTH <- c("growth_previous_year_pct", "predicted_growth_pct")
SGS_FC_CONTROL <- c("exp_dem_house", "exp_dem_senate", "cur_dem_house", "cur_dem_senate")
SGS_FC_MODELS <- list(
  list(id = "0", kind = "naive", terms = character(0), label = "(0) naive: last year's value"),
  list(id = "0s", kind = "seasonal", terms = character(0),
       label = "(0s) seasonal naive: last value in the same cycle position (presidential / midterm / odd year)"),
  list(id = "1", kind = "change", terms = SGS_FC_TIMING, label = "(1) naive + sector baseline + pres/midterm"),
  list(id = "2a", kind = "change", terms = c(SGS_FC_TIMING, "predicted_growth_pct"),
       label = "(2a) (1) + predicted growth"),
  list(id = "2b", kind = "change", terms = c(SGS_FC_TIMING, SGS_FC_GROWTH),
       label = "(2b) (2a) + prior-year growth (the earlier model (2))"),
  list(id = "3", kind = "change", terms = c(SGS_FC_TIMING, SGS_FC_GROWTH, SGS_FC_CONTROL),
       label = "(3) (2b) + expected and current control"),
  list(id = "4", kind = "change", terms = c(SGS_FC_TIMING, SGS_FC_GROWTH, SGS_FC_CONTROL, "contracted_prior"),
       label = "(4) (3) + contraction indicator")
)
# Model ids of the runs before 2026-09-30: (2) was split into (2a) and (2b), and (2b) is the earlier (2), term for term. This
# maps each current id to the id such a run used ("" = the model did not exist); sgs_fc_model_from_prior maps back.
SGS_FC_MODEL_PRIOR_ID <- c("0" = "0", "0s" = "0s", "1" = "1", "2a" = "", "2b" = "2", "3" = "3", "4" = "4")
sgs_fc_model_from_prior <- function(x) {
  x <- as.character(x)
  has <- SGS_FC_MODEL_PRIOR_ID[SGS_FC_MODEL_PRIOR_ID != ""]
  i <- match(x, unname(has))
  ifelse(is.na(i), x, names(has)[i])
}
SGS_FC_ROW_COLS <- c("backtest", "timing", "flag", "target_year", "study_sector", "model", "model_label", "actual",
                     "anchor_prev_year", "forecast", "error", "abs_error", "beats_naive", "in_common_set", "status", "reason",
                     "n_train", "train_years", "train_sectors", "descriptive", "naive_scale", "prior_model_id")
SGS_FC_METRIC_COLS <- c("backtest", "timing", "flag", "set", "scope", "model", "model_label", "n", "mae", "rmse", "naive_mae",
                        "rel_mae", "n_beats_naive", "share_beats_naive", "rel_mae_by_sector", "mase", "prior_model_id")
SGS_FC_ORIGIN_COLS <- c("backtest", "timing", "target_year", "model", "ok", "reason", "n_train", "train_years", "descriptive",
                        "dropped_terms", "year_level_params", "year_level_df", "resid_df", "prior_model_id")
SGS_FC_TERMS <- unique(c(SGS_FC_TIMING, SGS_FC_GROWTH, SGS_FC_CONTROL, "contracted_prior"))

# When each value of a backtest panel row became available (Date; NA = no date, so never available in the strict
# backtest). d = the sector_year rows of the panel; outcome_mmdd = the outcome's filing deadline in the next year.
.fc_available <- function(d, v, outcome_mmdd) {
  n <- nrow(d)
  if (!n) return(as.Date(character(0)))   # paste0() of an empty year would give one string ("-01-20"), not zero
  dt <- function(s) as.Date(vapply(as.list(s), sgs_date_text, ""))
  if (identical(v, "y")) return(as.Date(paste0(as.integer(d$year) + 1L, "-", outcome_mmdd)))
  if (v %in% SGS_FC_TIMING) return(rep(as.Date("1900-01-01"), n))
  if (v %in% c("growth_previous_year_pct", "contracted_prior")) {
    return(if ("growth_vintage" %in% names(d)) dt(d$growth_vintage) else rep(as.Date(NA), n))
  }
  if (identical(v, "predicted_growth_pct")) {
    return(if ("forecast_publication_month" %in% names(d)) dt(d$forecast_publication_month) else rep(as.Date(NA), n))
  }
  if (v %in% c("exp_dem_house", "exp_dem_senate")) {
    col <- paste0(v, "_available_at")
    return(if (col %in% names(d)) dt(d[[col]]) else rep(as.Date(NA), n))
  }
  if (v %in% c("cur_dem_house", "cur_dem_senate")) return(as.Date(paste0(as.integer(d$year), "-", SGS$AVAILABLE_CONTROL_MMDD)))
  rep(as.Date(NA), n)
}

.fc_position <- function(pres, mid) ifelse(pres %in% 1, "presidential", ifelse(mid %in% 1, "midterm", "odd"))

# The backtest panel: one row per sector x outcome year (years[1] ... years[2]) with the usable actual y, the usable
# previous-year value y_lag (which may come from years[1] - 1), the change dy and every model term as usable values
# (NA where the input is missing, partial or not applicable).
sgs_fc_panel <- function(sy, dv, sectors, years, outcome_mmdd = SGS$AVAILABLE_LDA_MMDD) {
  st <- SGS_STATUS_OF[[dv]]
  d <- sy[sy$study_sector %in% sectors & sy$year >= years[1] - 1 & sy$year <= years[2], , drop = FALSE]
  d <- d[!(as.logical(d$partial_year) %in% TRUE), , drop = FALSE]
  y <- ifelse(!is.na(d[[dv]]) & d[[st]] %in% SGS_USABLE_STATUSES, as.numeric(d[[dv]]), NA_real_)
  key <- paste(d$study_sector, d$year)
  lagi <- match(paste(d$study_sector, d$year - 1), key)
  out <- data.frame(study_sector = d$study_sector, year = as.numeric(d$year), y = y, y_lag = y[lagi], stringsAsFactors = FALSE)
  out$dy <- out$y - out$y_lag
  terms <- unique(unlist(lapply(SGS_FC_MODELS, `[[`, "terms")))
  for (v in terms) out[[v]] <- if (v %in% names(d)) ifelse(.usable(d, v), as.numeric(d[[v]]), NA_real_) else rep(NA_real_, nrow(out))
  out$position <- .fc_position(d$pres_year, d$midterm_year)
  # availability dates for the strict backtest (outcome: the filing deadline of the next year)
  out$avail__y <- .fc_available(d, "y", outcome_mmdd)
  for (v in terms) out[[paste0("avail__", v)]] <- .fc_available(d, v, outcome_mmdd)
  out <- out[out$year >= years[1] - 1, , drop = FALSE]
  rownames(out) <- NULL
  out
}

# The strict view of a backtest panel at the origin of target year T: every value not available by the origin is set
# to NA (a predictor), and an outcome not yet reported leaves the training changes. Returns list(panel, origin).
.fc_strict_view <- function(panel, T) {
  origin <- as.Date(paste0(T, "-", SGS$FORECAST_ORIGIN_MMDD))
  p <- panel
  for (v in SGS_FC_TERMS) {
    a <- panel[[paste0("avail__", v)]]
    if (is.null(a) || !v %in% names(p)) next
    p[[v]][is.na(a) | a > origin] <- NA
  }
  ya <- panel$avail__y
  if (!is.null(ya)) {
    late <- is.na(ya) | ya > origin
    p$y[late] <- NA
    lagi <- match(paste(p$study_sector, p$year - 1), paste(p$study_sector, p$year))
    p$y_lag <- p$y[lagi]
    p$dy <- p$y - p$y_lag
  }
  list(panel = p, origin = origin)
}

# The year-level part of a design: the common level that the sector baselines span plus the year-level (national) terms, on
# one row per distinct training year. params = its number of columns, df = the distinct years minus its rank (0 = SATURATED).
.fc_year_level <- function(tr, terms) {
  nat <- intersect(terms, SGS$NATIONAL_VARS)
  yrs <- sort(unique(tr$year))
  M <- cbind(rep(1, length(yrs)), if (length(nat)) as.matrix(tr[match(yrs, tr$year), nat, drop = FALSE]) else NULL)
  list(params = ncol(M), years = length(yrs), df = length(yrs) - sgs_rank_of(M))
}

# One change model fitted on the training rows (years < T): OLS of dy on one baseline per sector plus the model's terms, no
# intercept. The design is assessed against the study's estimability gate (sgs_assess): identified, with at least
# SGS$MIN_RESID_DF residual degrees of freedom and at least SGS$MIN_RESID_DF year-level residual degrees of freedom (the
# coordinator's stricter reading, 2026-09-30). ok = the gate passes. When it fails and there is a training row the fit is
# still made, as a DESCRIPTIVE one: the terms that add no rank (sgs_dependent_columns: the baselines come first, so it is
# always a term) are dropped and named, the rest is fitted on the same rows. Returns list(ok, reason, descriptive, beta,
# sectors, n, years, dropped, terms_used, resid_df, year_level_params, year_level_df).
.fc_fit_change <- function(train, terms) {
  keep <- !is.na(train$dy)
  for (v in terms) keep <- keep & !is.na(train[[v]])
  tr <- train[keep, , drop = FALSE]
  if (!nrow(tr)) {
    return(list(ok = FALSE, reason = "no complete training row", descriptive = FALSE, n = 0L, years = "none", sectors = character(0),
                dropped = character(0), terms_used = terms, resid_df = NA_real_, year_level_params = NA_real_, year_level_df = NA_real_))
  }
  secs <- sgs_sort_sectors(tr$study_sector)
  S <- matrix(0, nrow(tr), length(secs))
  for (j in seq_along(secs)) S[, j] <- as.numeric(tr$study_sector == secs[j])
  X <- cbind(S, if (length(terms)) as.matrix(tr[, terms, drop = FALSE]) else NULL)
  colnames(X) <- c(paste0("baseline:", secs), terms)
  info <- list(n = nrow(tr), years = sgs_years_text(tr$year), sectors = secs)
  reason <- character(0); dropped <- character(0); Xu <- X
  # the rank rule of the gates (sgs_rank_of: SVD of the column-normalised matrix, numpy's tolerance)
  rk <- sgs_rank_of(X)
  if (rk < ncol(X)) {
    dep <- sgs_dependent_columns(X, colnames(X))
    reason <- paste0("training design not identified: rank ", rk, " < ", ncol(X), " terms on ", nrow(tr), " rows (", info$years,
                     "); not identified: ", paste(dep, collapse = ", "))
    dropped <- intersect(dep, terms)
    Xu <- X[, !colnames(X) %in% dropped, drop = FALSE]
  }
  used <- setdiff(terms, dropped)
  resid <- nrow(tr) - ncol(Xu)
  if (resid < SGS$MIN_RESID_DF) {
    reason <- c(reason, paste0("residual df ", resid, " < ", SGS$MIN_RESID_DF, " (", nrow(tr), " training rows for ", ncol(Xu), " terms)"))
  }
  beta <- qr.coef(qr(Xu, tol = 0, LAPACK = FALSE), tr$dy)  # full rank: QR without pivoting, as sgs_ols
  names(beta) <- colnames(Xu)
  yl <- .fc_year_level(tr, used)
  if (yl$df < SGS$MIN_RESID_DF) {
    spec <- if (length(dropped)) {
      ys <- .fc_year_level(tr, terms)
      paste0("; as specified ", ys$params, " parameters on ", ys$years, " years")
    } else ""
    reason <- c(reason, paste0("year-level residual df ", sgs_int_str(yl$df), " < ", SGS$MIN_RESID_DF, " (", yl$params,
                               " year-level parameters on ", yl$years, " distinct years", spec, if (yl$df == 0) "; SATURATED" else "", ")"))
  }
  ok <- !length(reason)
  c(info, list(ok = ok, reason = paste(reason, collapse = "; "), descriptive = !ok, beta = beta, dropped = dropped,
               terms_used = used, resid_df = resid, year_level_params = yl$params, year_level_df = yl$df))
}

# The reason text of a DESCRIPTIVE forecast: why the design failed the gate (the reasons include the year-level residual df,
# 0 = SATURATED), what was dropped, and why no wider training window can be used (R8's remedy).
.fc_descriptive_note <- function(f) {
  paste0("DESCRIPTIVE: ", f$reason,
         if (length(f$dropped)) paste0("; fitted without ", paste(f$dropped, collapse = ", "), " (coefficient set to 0)") else "",
         "; no wider training window: R8's ", SGS$MIN_YEARS_DEFAULT, "-year minimum and ", SGS$MIN_YEARS_FALLBACK,
         "-year fallback (searched in ", .win_text(SGS$FALLBACK_SEARCH), ") cannot add years, the window (", f$years,
         ") already holds every earlier usable year of the panel and later years would look ahead")
}

# Run one backtest. panel = sgs_fc_panel(...); targets = the target years; strict = TRUE applies the information cutoff of
# each origin (.fc_strict_view). Returns list(rows, metrics, origins).
sgs_fc_backtest <- function(panel, targets, name, flag = "", strict = FALSE) {
  timing <- if (strict) "strict" else "retrospective"
  rows <- list(); origins <- list()
  for (T in targets) {
    view <- if (strict) .fc_strict_view(panel, T) else list(panel = panel, origin = as.Date(NA))
    pv <- view$panel
    origin_txt <- if (strict) format(view$origin, "%Y-%m-%d") else ""
    tgt <- panel[panel$year == T & !is.na(panel$y) & !is.na(panel$y_lag), , drop = FALSE]   # actual and anchor of record
    train <- pv[pv$year < T, , drop = FALSE]
    fits <- list()
    for (m in SGS_FC_MODELS) {
      if (m$kind != "change") next
      f <- .fc_fit_change(train, m$terms)
      if (strict && !isTRUE(f$ok)) f$reason <- paste0(f$reason, " (strict: values available by ", origin_txt, ")")
      fits[[m$id]] <- f
      origins[[length(origins) + 1L]] <- list(backtest = name, timing = timing, target_year = T, model = m$id, ok = f$ok,
                                              reason = f$reason, n_train = f$n, train_years = f$years,
                                              descriptive = isTRUE(f$descriptive), dropped_terms = paste(f$dropped, collapse = ", "),
                                              year_level_params = f$year_level_params, year_level_df = f$year_level_df,
                                              resid_df = f$resid_df, prior_model_id = SGS_FC_MODEL_PRIOR_ID[[m$id]])
    }
    for (i in seq_len(nrow(tgt))) {
      r <- tgt[i, , drop = FALSE]
      s <- r$study_sector
      rp <- pv[pv$study_sector == s & pv$year == T, , drop = FALSE]   # the predictors as available at the origin
      anchor <- rp$y_lag
      # the MASE scale: the in-sample naive MAE of the sector, the mean absolute one-step change of the outcomes reported by the origin
      chg <- pv$dy[pv$study_sector == s & pv$year < T & !is.na(pv$dy)]
      scale <- if (length(chg)) mean(abs(chg)) else NA_real_
      for (m in SGS_FC_MODELS) {
        fc <- NA_real_; reason <- ""; ntr <- NA_integer_; tyr <- ""; tsec <- ""; descr <- FALSE
        if (m$kind == "naive") {
          fc <- anchor
          if (is.na(fc)) reason <- paste0("last year's value not reported by the origin ", origin_txt)
        } else if (m$kind == "seasonal") {
          prev <- pv[pv$study_sector == s & pv$year < T & pv$position == r$position & !is.na(pv$y), , drop = FALSE]
          if (nrow(prev)) fc <- prev$y[which.max(prev$year)] else reason <- paste0("no earlier ", r$position, "-year value")
        } else {
          f <- fits[[m$id]]
          ntr <- f$n; tyr <- f$years; tsec <- paste(f$sectors, collapse = ", ")
          used <- f$terms_used   # the model's terms, less those a DESCRIPTIVE fit had to drop
          miss <- used[vapply(used, function(v) is.na(rp[[v]]), TRUE)]
          late <- miss[vapply(miss, function(v) !is.na(r[[v]]), TRUE)]   # the value exists, but not yet at the origin
          if (!isTRUE(f$ok) && !isTRUE(f$descriptive)) {
            reason <- f$reason
          } else if (length(miss)) {
            reason <- if (strict && length(late)) {
              paste0("not available at the origin ", origin_txt, ": ", paste(paste0(late, " (available ",
                     vapply(late, function(v) { a <- r[[paste0("avail__", v)]]; if (is.na(a)) "undated" else format(a, "%Y-%m-%d") }, ""),
                     ")"), collapse = ", "), if (length(setdiff(miss, late))) paste0("; missing: ", paste(setdiff(miss, late), collapse = ", ")) else "")
            } else paste0("input not available in ", T, ": ", paste(miss, collapse = ", "))
          } else if (!paste0("baseline:", s) %in% names(f$beta)) {
            reason <- paste0(s, " has no complete training row (no baseline)")
          } else if (is.na(anchor)) {
            reason <- paste0("last year's value not reported by the origin ", origin_txt)
          } else {
            x <- c(1, if (length(used)) as.numeric(unlist(rp[1, used, drop = FALSE])) else numeric(0))
            b <- f$beta[c(paste0("baseline:", s), used)]
            fc <- anchor + sum(x * b)
            if (isTRUE(f$descriptive)) { descr <- TRUE; reason <- .fc_descriptive_note(f) }
          }
        }
        rows[[length(rows) + 1L]] <- list(backtest = name, timing = timing, flag = flag, target_year = T, study_sector = s,
                                          model = m$id, model_label = m$label, actual = r$y, anchor_prev_year = anchor,
                                          forecast = fc, error = fc - r$y, status = if (is.na(fc)) "not available" else "forecast",
                                          reason = reason, n_train = ntr, train_years = tyr, train_sectors = tsec,
                                          descriptive = descr, naive_scale = scale, prior_model_id = SGS_FC_MODEL_PRIOR_ID[[m$id]])
      }
    }
  }
  df <- sgs_rows_df(rows, setdiff(SGS_FC_ROW_COLS, c("abs_error", "beats_naive", "in_common_set")))
  if (!nrow(df)) {
    df <- sgs_rows_df(list(), SGS_FC_ROW_COLS)
    return(list(rows = df, metrics = sgs_rows_df(list(), SGS_FC_METRIC_COLS), origins = origins))
  }
  df$abs_error <- abs(df$error)
  key <- paste(df$target_year, df$study_sector)
  nv <- df$abs_error[df$model == "0"][match(key, key[df$model == "0"])]
  df$beats_naive <- ifelse(df$model == "0" | is.na(df$abs_error) | is.na(nv), NA, df$abs_error < nv)
  # the common set: the sector-years every model forecasts, among the models that forecast at least one sector-year of this
  # backtest (a model with no forecast at any origin - strict timing - is reported, not required). A DESCRIPTIVE forecast
  # counts as no forecast here: it is reported apart, not part of the headline sets.
  fc_ok <- !is.na(df$forecast) & !(df$descriptive %in% TRUE)
  live <- unique(df$model[fc_ok])
  avail <- tapply(fc_ok | !(df$model %in% live), key, all)
  df$in_common_set <- unname(avail[key])
  df <- df[, SGS_FC_ROW_COLS, drop = FALSE]
  list(rows = df, metrics = sgs_fc_metrics(df, name, flag, timing), origins = origins)
}

# Metrics of a backtest's rows, per set (common, own; descriptive when there are DESCRIPTIVE forecasts) x scope (pooled, each
# sector, each target year) x model. The common and own sets leave the DESCRIPTIVE forecasts out. rel_mae_by_sector = the mean
# over the sectors of the sector's MAE / the sector's naive MAE on the same rows; mase = the mean of |error| / naive_scale.
sgs_fc_metrics <- function(df, name, flag = "", timing = "retrospective") {
  out <- list()
  labs <- setNames(vapply(SGS_FC_MODELS, `[[`, "", "label"), vapply(SGS_FC_MODELS, `[[`, "", "id"))
  key <- paste(df$target_year, df$study_sector)
  naive_err <- df$abs_error[df$model == "0"][match(key, key[df$model == "0"])]
  descr <- if ("descriptive" %in% names(df)) df$descriptive %in% TRUE else rep(FALSE, nrow(df))
  scl <- if ("naive_scale" %in% names(df)) as.numeric(df$naive_scale) else rep(NA_real_, nrow(df))
  one <- function(set, scope, sel, models = names(labs)) {
    for (m in models) {
      k <- sel & df$model == m & !is.na(df$forecast)
      e <- df$error[k]; ne <- naive_err[k]
      n <- length(e)
      hn <- !is.na(ne)   # the rows where the naive forecast exists: the naive-relative metrics use these rows only
      nn <- sum(hn)
      mae <- if (n) mean(abs(e)) else NA_real_
      nmae <- if (nn) mean(ne[hn]) else NA_real_
      nb <- if (m == "0" || !nn) NA_real_ else sum(abs(e[hn]) < ne[hn])
      # equal weight per sector: each sector's MAE over its own naive MAE (the same rows), then the mean over the sectors
      rs <- NA_real_
      if (nn) {
        ratio <- vapply(split(seq_len(nn), df$study_sector[k][hn]), function(ix) {
          d <- mean(ne[hn][ix]); if (isTRUE(d > 0)) mean(abs(e[hn][ix])) / d else NA_real_
        }, 0)
        if (any(!is.na(ratio))) rs <- mean(ratio, na.rm = TRUE)
      }
      sc <- scl[k]; hs <- !is.na(sc) & sc > 0   # a row with no in-sample change (or a constant series) has no MASE
      out[[length(out) + 1L]] <<- list(backtest = name, timing = timing, flag = flag, set = set, scope = scope, model = m,
                                       model_label = labs[[m]],
                                       n = n, mae = mae, rmse = if (n) sqrt(mean(e^2)) else NA_real_, naive_mae = nmae,
                                       rel_mae = if (nn && isTRUE(nmae > 0)) mean(abs(e[hn])) / nmae else NA_real_, n_beats_naive = nb,
                                       share_beats_naive = if (m == "0" || !nn) NA_real_ else nb / nn,
                                       rel_mae_by_sector = rs, mase = if (any(hs)) mean(abs(e[hs]) / sc[hs]) else NA_real_,
                                       prior_model_id = SGS_FC_MODEL_PRIOR_ID[[m]])
    }
  }
  for (set in c("common", "own")) {
    base <- (if (set == "common") df$in_common_set %in% TRUE else rep(TRUE, nrow(df))) & !descr
    one(set, "pooled", base)
    for (s in sgs_sort_sectors(df$study_sector)) one(set, s, base & df$study_sector == s)
    for (T in sort(unique(df$target_year))) one(set, paste0("target ", T), base & df$target_year == T)
  }
  dk <- descr & !is.na(df$forecast)
  if (any(dk)) {   # the DESCRIPTIVE forecasts, apart from the headline sets, for the models that have them
    dm <- intersect(names(labs), unique(df$model[dk]))
    one("descriptive", "pooled", dk, dm)
    for (s in sgs_sort_sectors(df$study_sector[dk])) one("descriptive", s, dk & df$study_sector == s, dm)
    for (T in sort(unique(df$target_year[dk]))) one("descriptive", paste0("target ", T), dk & df$target_year == T, dm)
  }
  sgs_rows_df(out, SGS_FC_METRIC_COLS)
}

# The sectors of the LobbyView backtest: the L-LV tests' sectors, i.e. those with a usable primary LobbyView amount and a
# usable growth series in some year of the window.
.fc_lv_sectors <- function(sy, years) {
  k <- sy$year >= years[1] & sy$year <= years[2] & .usable(sy, "lobby_lv_real_m") & .usable(sy, "growth_previous_year_pct")
  sgs_sort_sectors(sy$study_sector[k])
}

# The target years of a backtest that have at least one sector-year with an actual and a previous-year value, i.e. the years
# that get forecast rows.
.fc_target_years <- function(panel, targets) {
  sort(unique(panel$year[panel$year %in% targets & !is.na(panel$y) & !is.na(panel$y_lag)]))
}

# Both backtests. LobbyView: always (NOT RUN when 01 has no LobbyView sheet). Contributions: only once the 2020 cycle is
# in 04 (at least two sectors with usable 2020 contributions); labelled FEW TARGETS.
sgs_forecast_run <- function(tables, built = list(), strict = FALSE) {
  sy <- tables$sector_year
  runs <- list(); rows <- list(); metrics <- list(); origins <- list(); asof <- list()
  lv_ok <- isTRUE(built$lobbyview_all$built) && "lobby_lv_real_m" %in% names(sy)
  if (lv_ok) {
    secs <- .fc_lv_sectors(sy, SGS$FORECAST_LV_YEARS)
    p <- sgs_fc_panel(sy, "lobby_lv_real_m", secs, SGS$FORECAST_LV_YEARS, SGS$AVAILABLE_LDA_MMDD)
    bt <- sgs_fc_backtest(p, SGS$FORECAST_LV_TARGETS, "LobbyView (L-LV sectors)")
    rows$lv <- bt$rows; metrics$lv <- bt$metrics; origins <- c(origins, bt$origins)
    if (strict) {
      bs <- sgs_fc_backtest(p, SGS$FORECAST_LV_TARGETS, "LobbyView (L-LV sectors)", strict = TRUE)
      rows$lv_strict <- bs$rows; metrics$lv_strict <- bs$metrics; origins <- c(origins, bs$origins)
      asof <- c(asof, sgs_fc_asof(p, SGS$FORECAST_LV_TARGETS, "LobbyView (L-LV sectors)"))
    }
    runs$lv <- list(status = "RUN", sectors = secs, years = SGS$FORECAST_LV_YEARS, targets = SGS$FORECAST_LV_TARGETS,
                    note = paste0("DV lobby_lv_real_m (01 ", SGS$LOBBYVIEW_ALL_SHEET, ", de-duplicated, thin sector-years excluded), ",
                                  "$M 2025; sectors ", paste(secs, collapse = ", "), "; outcome years ", SGS$FORECAST_LV_YEARS[1], "-",
                                  SGS$FORECAST_LV_YEARS[2], " (a lag level may come from ", SGS$FORECAST_LV_YEARS[1] - 1,
                                  "); targets ", min(SGS$FORECAST_LV_TARGETS), "-", max(SGS$FORECAST_LV_TARGETS)))
  } else {
    runs$lv <- list(status = "NOT RUN", note = paste0("01 ", SGS$LOBBYVIEW_ALL_SHEET, " not present"))
  }
  c20 <- sy$year == SGS$FORECAST_C_YEARS[1] & .usable(sy, "contributions_real_m")
  if (sum(c20) >= 2) {
    secs <- sgs_sort_sectors(sy$study_sector[.usable(sy, "contributions_real_m") & sy$year >= SGS$FORECAST_C_YEARS[1] &
                                              sy$year <= SGS$FORECAST_C_YEARS[2]])
    p <- sgs_fc_panel(sy, "contributions_real_m", secs, SGS$FORECAST_C_YEARS, SGS$AVAILABLE_FEC_MMDD)
    tyrs <- .fc_target_years(p, SGS$FORECAST_C_TARGETS)   # the flag counts the target years actually forecast, not the configured ones
    flag <- paste0(SGS$FORECAST_FEW_TARGETS_FLAG, " (", length(tyrs), " target year", if (length(tyrs) != 1L) "s", ")")
    bt <- sgs_fc_backtest(p, SGS$FORECAST_C_TARGETS, "contributions (04)", flag = flag)
    rows$c <- bt$rows; metrics$c <- bt$metrics; origins <- c(origins, bt$origins)
    if (strict) {
      bs <- sgs_fc_backtest(p, SGS$FORECAST_C_TARGETS, "contributions (04)", flag = flag, strict = TRUE)
      rows$c_strict <- bs$rows; metrics$c_strict <- bs$metrics; origins <- c(origins, bs$origins)
      asof <- c(asof, sgs_fc_asof(p, SGS$FORECAST_C_TARGETS, "contributions (04)"))
    }
    runs$c <- list(status = "RUN", sectors = secs, years = SGS$FORECAST_C_YEARS, targets = SGS$FORECAST_C_TARGETS, flag = flag,
                   note = paste0("DV contributions_real_m (04 general giving), $M 2025; sectors ", paste(secs, collapse = ", "),
                                 "; outcome years ", SGS$FORECAST_C_YEARS[1], "-", SGS$FORECAST_C_YEARS[2], "; targets ",
                                 sgs_years_text(tyrs), "; ", flag))
  } else {
    yrs <- sort(unique(sy$year[.usable(sy, "contributions_real_m")]))
    runs$c <- list(status = "NOT RUN", note = paste0(
      "waits for the Mentat 2020 cycle: 04 has usable contributions for ", sgs_years_text(yrs), " only; the contributions ",
      "backtest (targets ", min(SGS$FORECAST_C_TARGETS), "-", max(SGS$FORECAST_C_TARGETS), ", labelled ", SGS$FORECAST_FEW_TARGETS_FLAG,
      ") runs by itself once 2020 is in 04"))
  }
  list(runs = runs, strict = strict, asof = sgs_rows_df(asof, SGS_FC_ASOF_COLS),
       rows = if (length(rows)) do.call(rbind, unname(rows)) else sgs_rows_df(list(), SGS_FC_ROW_COLS),
       metrics = if (length(metrics)) do.call(rbind, unname(metrics)) else sgs_rows_df(list(), SGS_FC_METRIC_COLS),
       origins = sgs_rows_df(origins, SGS_FC_ORIGIN_COLS))
}

SGS_FC_AVAIL_RULES <- c(
  y = "outcome of year t: the filing deadline in January of t + 1 (LDA fourth quarter 20 January; FEC year end 31 January)",
  pres_year = "election calendar: known in advance", midterm_year = "election calendar: known in advance",
  growth_previous_year_pct = "07 report vintage of the sector's series (end of that month)",
  predicted_growth_pct = "06 forecast publication month (end of that month)",
  exp_dem_house = "02 measured_at (IEM annual mean: last price date; fill sheet: measured_on)",
  exp_dem_senate = "02 measured_at (IEM annual mean: last price date; fill sheet: measured_on)",
  cur_dem_house = "31 January of the year (majority seated in January)",
  cur_dem_senate = "31 January of the year (majority seated in January)",
  contracted_prior = "as growth_previous_year_pct (07 report vintage)")
SGS_FC_ASOF_COLS <- c("backtest", "target_year", "origin", "variable", "availability_rule", "n_target", "n_with_value",
                      "n_available_at_origin", "earliest_available", "latest_available")

# The strict backtest's information table (sheet forecast_asof): per backtest x target year x variable, the target
# sector-years with a value, how many of those values were available by the origin, and their availability dates.
sgs_fc_asof <- function(panel, targets, name) {
  out <- list()
  for (T in targets) {
    origin <- as.Date(paste0(T, "-", SGS$FORECAST_ORIGIN_MMDD))
    tg <- panel[panel$year == T & !is.na(panel$y) & !is.na(panel$y_lag), , drop = FALSE]
    for (v in names(SGS_FC_AVAIL_RULES)) {
      if (identical(v, "y")) {
        # the anchor: last year's value, reported by the filing deadline
        lg <- panel[match(paste(tg$study_sector, T - 1), paste(panel$study_sector, panel$year)), , drop = FALSE]
        has <- !is.na(lg$y); a <- lg$avail__y
      } else {
        if (!v %in% names(tg)) next
        has <- !is.na(tg[[v]]); a <- tg[[paste0("avail__", v)]]
      }
      av <- has & !is.na(a) & a <= origin
      ah <- a[has & !is.na(a)]
      out[[length(out) + 1L]] <- list(backtest = name, target_year = T, origin = format(origin, "%Y-%m-%d"),
                                      variable = if (identical(v, "y")) "anchor: last year's value" else v,
                                      availability_rule = unname(SGS_FC_AVAIL_RULES[v]), n_target = nrow(tg), n_with_value = sum(has),
                                      n_available_at_origin = sum(av),
                                      earliest_available = if (length(ah)) format(min(ah), "%Y-%m-%d") else "",
                                      latest_available = if (length(ah)) format(max(ah), "%Y-%m-%d") else "")
    }
  }
  out
}

# Markdown of the backtest (report section).
sgs_forecast_md <- function(fc) {
  f4 <- function(x) if (is.na(x)) "n/a" else sgs_py_fixed(x, 3, comma = TRUE)
  pct <- function(x) if (is.na(x)) "n/a" else paste0(sgs_py_fixed(100 * x, 1), "%")
  f3 <- function(x) if (is.na(x)) "n/a" else sgs_py_fixed(x, 3)
  pooled_head <- "| model | n | MAE | RMSE | naive MAE (same rows) | MAE / naive MAE | sector-equal MAE / naive MAE | MASE | beats naive |"
  pooled_sep <- "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
  pooled_row <- function(x, m, nn) {
    paste0("| ", x$model_label, " | ", x$n, " | ", f4(x$mae), " | ", f4(x$rmse), " | ", f4(x$naive_mae), " | ", f3(x$rel_mae), " | ",
           f3(x$rel_mae_by_sector), " | ", f3(x$mase), " | ",
           if (m == "0") "(reference)" else if (is.na(x$share_beats_naive)) "n/a" else
             paste0(pct(x$share_beats_naive), " (", sgs_py_str(x$n_beats_naive), " of ", nn, ")"), " |")
  }
  L <- c(paste0("Rolling-origin, one-step-ahead: for each target year every model is fitted only on the years before it. ",
                "Models (1)-(4) (with (2) split into (2a) and (2b), below) predict the one-year change and add it to last year's value (nested in the naive forecast); ",
                "same-year actual growth is never used; expected control is measured differently by year (per-year dates in sheet ",
                "expected_control_timing): the IEM annual mean for 2008-2022, the binary final call for the 2024 election (measured ",
                "2024-11-04) for 2023 and 2024, and the market snapshot of 2026-09-25 for 2025-2026, so it is a within-year or later input. ",
                "Errors in $M 2025 (forecast - actual). 'Beats naive' = a strictly smaller absolute error than last year's ",
                "value on the same sector-year. Common set = the sector-years every model forecasts (among the models that ",
                "forecast at least one); own set = every sector-year the model forecasts. Per-target-year metrics are in ",
                "sheet forecast_metrics, every forecast in sheet forecast_backtest."), "",
         paste0("Model ids (owner-approved 2026-09-30): (2a) is new: the sector baseline + pres/midterm + predicted growth only, the ",
                "strict-feasible growth model (the 06 predicted growth of a sector-year that has one is dated before the origin). (2b) ",
                "is the earlier model (2), term for term: (2a) + prior-year growth; runs before 2026-09-30 carry the id \"2\" for it ",
                "(column prior_model_id of the three forecast sheets). Models (0), (0s), (1), (3) and (4) keep their ids and specifications."), "",
         paste0("Two scale-free summaries sit beside the dollar MAE: the sector-equal MAE / naive MAE (the mean over the sectors of ",
                "the sector's MAE over the sector's naive MAE on the same rows, so a large sector does not dominate) and the MASE ",
                "(each absolute error over the in-sample naive MAE of its sector at that origin, the mean absolute one-step change ",
                "of the outcomes reported before the target year; averaged over the rows). Below 1 = better than last year's value."), "",
         paste0("Estimability gate (the study's own, minimum ", SGS$MIN_RESID_DF, "): an origin of a change model whose training design is ",
                "not identified, or has fewer than ", SGS$MIN_RESID_DF, " residual degrees of freedom, or fewer than ", SGS$MIN_RESID_DF,
                " YEAR-LEVEL residual degrees of freedom (the distinct training years less the common level and the year-level terms; ",
                "0 = SATURATED), is not dropped: R8's wider training window cannot be found (an expanding window from the first year ",
                "of the panel has nothing earlier to add, and later years would look ahead), so its forecast is kept as DESCRIPTIVE ",
                "(the terms that add no rank, if any, are dropped and named; the reason is on the row) and is reported in its own ",
                "table, not in the common set or each model's own set: the headline sets are the origins that pass the gate."), "",
         if (isTRUE(fc$strict)) c(paste0(
           "Timing (coordinator's revision of 2026-09-26, after the Codex methodology review): the RETROSPECTIVE backtest ",
           "trains only on earlier outcomes but reads every predictor from the final-vintage panel (a pseudo-out-of-sample ",
           "exercise, not evidence of a forecast available at the time: 07 growth comes from 2024-2026 report vintages, and ",
           "expected control is measured during - for 2023 and 2025 after - the target year). The STRICT backtest admits a ",
           "value only if it was available by the origin, 1 February of the target year (after the prior year's LDA ",
           "fourth-quarter reports, due 20 January, and FEC year-end reports, due 31 January); availability dates per ",
           "variable and target year are in sheet forecast_asof. The origin and the availability rules were fixed before any ",
           "strict result was seen; nothing is tuned to the held-out outcomes. The two are reported separately below."), "")
         else character(0))
  for (nm in names(fc$runs)) {
    r <- fc$runs[[nm]]
    title <- if (nm == "lv") "LobbyView lobbying (L-LV sectors)" else "Contributions (04)"
    L <- c(L, paste0("### ", title, ": ", r$status), "", paste0("- ", r$note))
    if (!identical(r$status, "RUN")) { L <- c(L, ""); next }
    bname <- if (nm == "lv") "LobbyView (L-LV sectors)" else "contributions (04)"
    for (timing in c("retrospective", if (isTRUE(fc$strict)) "strict")) {
    if (isTRUE(fc$strict)) L <- c(L, "", paste0("#### ", SGS_FC_TIMINGS[[timing]]), "")
    tm <- function(df) if ("timing" %in% names(df)) df$timing %in% timing else rep(TRUE, nrow(df))
    mt <- fc$metrics[fc$metrics$backtest == bname & tm(fc$metrics), , drop = FALSE]
    rw <- fc$rows[fc$rows$backtest == bname & tm(fc$rows), , drop = FALSE]
    if (!"descriptive" %in% names(rw)) rw$descriptive <- rep(FALSE, nrow(rw))   # rows of a run before the DESCRIPTIVE label
    nc <- sum(rw$model == "0" & rw$in_common_set %in% TRUE)
    nt <- sum(rw$model == "0")
    none <- setdiff(vapply(SGS_FC_MODELS, `[[`, "", "id"), unique(rw$model[!is.na(rw$forecast)]))
    L <- c(L, paste0("- Target sector-years with an actual and a previous-year value: ", nt, "; in the common set (every model ",
                     "that forecasts at all forecasts them): ", nc, "."))
    if (length(none)) {
      why <- vapply(none, function(m) { x <- rw$reason[rw$model == m & nzchar(rw$reason)]; if (length(x)) x[1] else "" }, "")
      L <- c(L, paste0("- No forecast at any origin: ", paste0("(", none, ") - ", why, collapse = "; "), "."))
    }
    if (identical(timing, "strict") && !is.null(fc$asof) && nrow(fc$asof)) {
      # what was available at the origins: per variable, the target sector-years whose value was available by then
      a <- fc$asof[fc$asof$backtest == bname, , drop = FALSE]
      if (nrow(a)) {
        parts <- vapply(unique(a$variable), function(v) {
          x <- a[a$variable == v, , drop = FALSE]
          rng <- c(x$earliest_available[nzchar(x$earliest_available)], x$latest_available[nzchar(x$latest_available)])
          paste0(v, " ", sum(x$n_available_at_origin), " of ", sum(x$n_with_value),
                 if (length(rng)) paste0(" (available ", min(rng), " to ", max(rng), ")") else "")
        }, "")
        L <- c(L, paste0("- Values available by the origin, over all target sector-years (sheet forecast_asof): ",
                         paste(parts, collapse = "; "), "."))
      }
    }
    og <- fc$origins[fc$origins$backtest == bname & tm(fc$origins) & !(fc$origins$ok %in% TRUE), , drop = FALSE]
    dsc <- if ("descriptive" %in% names(og)) og$descriptive %in% TRUE else rep(FALSE, nrow(og))
    if (nrow(og)) {
      for (m in unique(og$model)) {
        o <- og[og$model == m, , drop = FALSE]
        od <- dsc[og$model == m]
        for (kd in c(FALSE, TRUE)) {
          ok_ <- o[od == kd, , drop = FALSE]
          if (!nrow(ok_)) next
          L <- c(L, if (!kd) {
            paste0("- Model (", m, ") not identified at origin(s) ", paste(ok_$target_year, collapse = ", "), ": ",
                   ok_$reason[1], if (nrow(ok_) > 1) " (first of them)" else "", ".")
          } else {
            # per origin: the terms it dropped (an origin that is only below the year-level df drops nothing) and its year-level df
            per <- paste0(ok_$target_year, " (dropped ", ifelse(nzchar(ok_$dropped_terms), ok_$dropped_terms, "nothing"),
                          "; year-level residual df ", sgs_int_str(ok_$year_level_df), ")", collapse = ", ")
            paste0("- Model (", m, ") fails the estimability gate at origin(s) ", paste(ok_$target_year, collapse = ", "), ". Per origin: ",
                   per, ". Reason at ", ok_$target_year[1], ": ", ok_$reason[1], ". The forecasts are kept, labelled DESCRIPTIVE.")
          })
        }
      }
    }
    for (set in c("common", "own")) {
      L <- c(L, "", paste0("**", if (set == "common") "Common set" else "Each model's own set", ", pooled**"), "", pooled_head, pooled_sep)
      for (m in vapply(SGS_FC_MODELS, `[[`, "", "id")) {
        x <- mt[mt$set == set & mt$scope == "pooled" & mt$model == m, , drop = FALSE]
        if (!nrow(x) || !isTRUE(x$n > 0)) next
        # the rows behind the share: the model's forecast rows of this set that have a naive forecast (beats_naive is NA elsewhere)
        nn <- sum(!is.na(rw$beats_naive[rw$model == m & !is.na(rw$forecast) & !(rw$descriptive %in% TRUE) &
                                          (set == "own" | rw$in_common_set %in% TRUE)]))
        L <- c(L, pooled_row(x, m, nn))
      }
    }
    xd <- mt[mt$set == "descriptive" & mt$scope == "pooled", , drop = FALSE]
    if (nrow(xd)) {
      L <- c(L, "", paste0("**DESCRIPTIVE forecasts (the design fails the estimability gate at the origin; kept, not in the common set ",
                           "or each model's own set), pooled**"), "", pooled_head, pooled_sep)
      for (m in vapply(SGS_FC_MODELS, `[[`, "", "id")) {
        x <- xd[xd$model == m, , drop = FALSE]
        if (!nrow(x) || !isTRUE(x$n > 0)) next
        nn <- sum(!is.na(rw$beats_naive[rw$model == m & !is.na(rw$forecast) & (rw$descriptive %in% TRUE)]))
        L <- c(L, pooled_row(x, m, nn))
      }
      dr <- rw[rw$descriptive %in% TRUE & !is.na(rw$forecast), , drop = FALSE]
      L <- c(L, "", paste0("- DESCRIPTIVE forecasts: ", nrow(dr), " (models ", paste(unique(dr$model), collapse = ", "), "; target years ",
                           sgs_years_text(dr$target_year), "). Reason of the first: ", dr$reason[1], "."))
    }
    secs <- setdiff(unique(mt$scope[mt$set == "common"]), c("pooled", grep("^target ", unique(mt$scope), value = TRUE)))
    if (length(secs)) {
      L <- c(L, "", "**Common set, per sector: MAE (share of sector-years beating naive)**", "",
             paste0("| sector | n | ", paste(vapply(SGS_FC_MODELS, function(m) paste0("(", m$id, ")"), ""), collapse = " | "), " |"),
             paste0("|---|---:|", paste(rep("---:", length(SGS_FC_MODELS)), collapse = "|"), "|"))
      for (s in secs) {
        cells <- vapply(SGS_FC_MODELS, function(m) {
          x <- mt[mt$set == "common" & mt$scope == s & mt$model == m$id, , drop = FALSE]
          if (!nrow(x) || !x$n) return("n/a")
          paste0(f4(x$mae), if (m$id == "0") "" else paste0(" (", pct(x$share_beats_naive), ")"))
        }, "")
        nn <- mt$n[mt$set == "common" & mt$scope == s & mt$model == "0"]
        L <- c(L, paste0("| ", s, " | ", if (length(nn)) nn else 0, " | ", paste(cells, collapse = " | "), " |"))
      }
      L <- c(L, "", "**Common set, per sector: MASE (each error over the sector's in-sample naive MAE at its origin)**", "",
             paste0("| sector | ", paste(vapply(SGS_FC_MODELS, function(m) paste0("(", m$id, ")"), ""), collapse = " | "), " |"),
             paste0("|---|", paste(rep("---:", length(SGS_FC_MODELS)), collapse = "|"), "|"))
      for (s in secs) {
        cells <- vapply(SGS_FC_MODELS, function(m) {
          x <- mt[mt$set == "common" & mt$scope == s & mt$model == m$id, , drop = FALSE]
          if (!nrow(x) || !x$n) return("n/a")
          f3(x$mase)
        }, "")
        L <- c(L, paste0("| ", s, " | ", paste(cells, collapse = " | "), " |"))
      }
      L <- c(L, "", "**Own set, per sector: MAE (share of sector-years beating naive; n)**", "",
             paste0("| sector | ", paste(vapply(SGS_FC_MODELS, function(m) paste0("(", m$id, ")"), ""), collapse = " | "), " |"),
             paste0("|---|", paste(rep("---:", length(SGS_FC_MODELS)), collapse = "|"), "|"))
      for (s in secs) {
        cells <- vapply(SGS_FC_MODELS, function(m) {
          x <- mt[mt$set == "own" & mt$scope == s & mt$model == m$id, , drop = FALSE]
          if (!nrow(x) || !x$n) return("n/a")
          paste0(f4(x$mae), " (", if (m$id == "0") "" else paste0(pct(x$share_beats_naive), "; "), "n ", x$n, ")")
        }, "")
        L <- c(L, paste0("| ", s, " | ", paste(cells, collapse = " | "), " |"))
      }
    }
    L <- c(L, "")
    }
  }
  L
}
