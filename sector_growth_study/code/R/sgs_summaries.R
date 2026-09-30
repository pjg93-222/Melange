# Model summaries in standard R form (Paul, 2026-09-26: "when you show the regression's they should be presented to
# me as you would in any R-code"). For every ESTIMABLE test, the test's model is refitted with lm() on the test's
# gated complete-case sample, with named regressors and factor() fixed effects, and the real summary() output is
# printed (capture.output, never hand-formatted). Directly under it, a labelled block gives the study's own
# inference on the focal term(s) - the classical Std. Error / t / Pr(>|t|) of summary() are NOT the study's inference:
# CR1 standard error, wild cluster restricted bootstrap p and 95% interval (draws, clusters) and the strata line.
#
# Equivalence with the pipeline's design: sector (or sector x tier, board, cycle, champion) baselines enter as
# factor() terms with an intercept, which spans the same column space as the pipeline's one-dummy-per-level design,
# so the fitted values, the focal coefficients and the residual degrees of freedom are identical (the focal
# coefficients and the residual df are checked in every block; the file header reports the largest relative
# difference). First differences have no intercept (as in the
# pipeline). In H5 models the fixed-effect factors are listed first, so lm() leaves out ("not defined because of
# singularities") the same absorbed controls the pipeline drops and names.

SGS_SUMMARY_LABEL_ORDER <- c("CORE", "DESCRIPTIVE", "EXTENSION", "ROBUSTNESS", "EXPLORATORY", "PREVIEW")

.bt <- function(x) ifelse(make.names(x) == x, x, paste0("`", x, "`"))

# The lm() formula and data of a sector-year test (spec) on its sample data frame. Returns list(formula, data,
# terms = named vector pipeline coefficient -> lm coefficient name).
sgs_lm_sector_year <- function(spec, sdf) {
  fd <- identical(spec$variant, "fd")
  pref <- if (fd) "d_" else ""
  data <- data.frame(study_sector = sdf$study_sector, year = sdf$year, stringsAsFactors = FALSE)
  if (identical(spec$table, "shift_chamber")) data$chamber <- sdf$chamber
  terms <- character(0)
  rhs <- character(0)
  if (identical(spec$variant, "tier")) {
    xs <- unique(vapply(spec$interactions, `[[`, "", 1))
    for (x in xs) { data[[x]] <- as.numeric(sdf[[x]]); rhs <- c(rhs, .bt(x)); terms[x] <- x }
    for (it in spec$interactions) {
      tcol <- gsub("[^A-Za-z0-9]+", "_", it[2])
      data[[tcol]] <- as.numeric(sdf$tier == it[2])
      rhs <- c(rhs, paste0(.bt(it[1]), ":", tcol))
      terms[paste0(it[1], ":", it[2])] <- paste0(it[1], ":", tcol)
    }
    for (c in spec$controls) { data[[c]] <- as.numeric(sdf[[c]]); rhs <- c(rhs, .bt(c)); terms[c] <- c }
  } else if (identical(spec$variant, "slopes")) {
    # per-sector designs (SLOPES, CONTRACT-b, ASYM-SLOPES): y ~ v:factor(study_sector) [+ ...] + controls +
    # factor(study_sector), one row per sector for every focal variable
    for (g in spec$focal) {
      data[[g]] <- as.numeric(sdf[[g]])
      rhs <- c(rhs, paste0(.bt(g), ":factor(study_sector)"))
      for (s in sgs_sort_sectors(sdf$study_sector)) terms[paste0(g, ":", s)] <- paste0(g, ":factor(study_sector)", s)
    }
    for (c in spec$controls) { data[[c]] <- as.numeric(sdf[[c]]); rhs <- c(rhs, .bt(c)); terms[c] <- c }
  } else if (identical(spec$variant, "sector_interaction")) {
    # bank-only models: y ~ g + g:community_banks + controls + factor(study_sector), community_banks a 0/1 column
    xs <- unique(vapply(spec$interactions, `[[`, "", 1))
    for (x in xs) { data[[x]] <- as.numeric(sdf[[x]]); rhs <- c(rhs, .bt(x)); terms[x] <- x }
    for (it in spec$interactions) {
      ucol <- gsub("[^A-Za-z0-9_.]+", "_", it[2])
      data[[ucol]] <- as.numeric(sdf$study_sector == it[2])
      rhs <- c(rhs, paste0(.bt(it[1]), ":", ucol))
      terms[paste0(it[1], ":", it[2])] <- paste0(it[1], ":", ucol)
    }
    for (c in spec$controls) { data[[c]] <- as.numeric(sdf[[c]]); rhs <- c(rhs, .bt(c)); terms[c] <- c }
  } else {
    for (c in sgs_raw_regressors(spec)) {
      nm <- paste0(pref, c)
      data[[nm]] <- as.numeric(sdf[[c]])
      rhs <- c(rhs, .bt(nm))
      terms[c] <- nm
    }
  }
  # ASYM: the equality row is the difference of two lm() coefficients
  if (length(spec$equality) == 2L) {
    terms[paste0(spec$equality[2], " - ", spec$equality[1])] <- paste0(terms[[spec$equality[2]]], " - ", terms[[spec$equality[1]]])
  }
  dv <- spec$dv
  if (identical(spec$variant, "log")) {
    data[[dv]] <- as.numeric(sdf[[dv]])
    lhs <- paste0("log(", .bt(dv), ")")
  } else if (fd) {
    data[[paste0("d_", dv)]] <- as.numeric(sdf$y)
    lhs <- .bt(paste0("d_", dv))
  } else {
    data[[dv]] <- as.numeric(sdf$y)
    lhs <- .bt(dv)
  }
  fe <- character(0)
  if ("sector" %in% spec$fe && length(unique(data$study_sector)) > 1) fe <- c(fe, "factor(study_sector)")
  if ("sector_x_tier" %in% spec$fe) {
    data$sector_tier <- paste(sdf$study_sector, sdf$tier, sep = " | ")
    fe <- c(fe, "factor(sector_tier)")
  }
  if ("year" %in% spec$fe && length(unique(data$year)) > 1) fe <- c(fe, "factor(year)")
  # first differences with year effects (FDY): an intercept plus year effects, no sector baselines
  if ("year_full" %in% spec$fe && length(unique(data$year)) > 1) fe <- c(fe, "factor(year)")
  # SEATS-W: a linear week-of-cycle trend per election cycle (the cycle effects come from "year")
  if ("cycle_trend" %in% spec$fe) {
    data$week_of_cycle <- as.numeric(sdf$week_of_cycle)
    fe <- c(fe, if (length(unique(data$year)) > 1) "factor(year):week_of_cycle" else "week_of_cycle")
  }
  if ("sector_x_chamber" %in% spec$fe) {
    # SHIFT-Chamber: factor(chamber) + factor(study_sector) + their interaction = one baseline per unit x chamber, the
    # column space of the pipeline's unit x chamber dummies
    two_ch <- length(unique(data$chamber)) > 1; two_s <- length(unique(data$study_sector)) > 1
    fe <- c(fe, if (two_ch) "factor(chamber)", if (two_s) "factor(study_sector)", if (two_ch && two_s) "factor(study_sector):factor(chamber)")
  }
  rhs_all <- c(if (!length(spec$fe)) "0", rhs, fe)
  # SHIFT-*-W: weighted least squares, weights = the party-labelled dollars of each row
  w <- spec$weight_var %||% NA_character_
  weights <- NULL
  if (length(w) == 1L && !is.na(w)) { data[[w]] <- as.numeric(sdf[[w]]); weights <- w }
  list(formula = stats::as.formula(paste(lhs, "~", paste(rhs_all, collapse = " + "))), data = data, terms = terms,
       lhs = lhs, rhs = rhs_all, weights = weights)
}

# The restricted lm() of a joint test of a per-sector design: kind "zero" drops the v:factor(study_sector) term,
# kind "equal" replaces it with one common v term.
sgs_lm_restricted <- function(sl, var, kind) {
  term <- paste0(.bt(var), ":factor(study_sector)")
  rhs <- if (identical(kind, "zero")) setdiff(sl$rhs, term) else replace(sl$rhs, sl$rhs == term, .bt(var))
  list(formula = stats::as.formula(paste(sl$lhs, "~", paste(rhs, collapse = " + "))), data = sl$data, terms = sl$terms,
       weights = sl$weights)
}

# The lm() formula and data of an H5 test (spec, decision d).
sgs_lm_h5 <- function(spec, d) {
  sdf <- d$sample$df
  dv <- d$dv_col
  data <- data.frame(board = sdf$board, bioguide = sdf$bioguide, cycle = sdf$cycle, stringsAsFactors = FALSE)
  data[[dv]] <- as.numeric(sdf[[dv]])
  lhs <- switch(spec$dv_transform, log1p = paste0("log1p(", .bt(dv), ")"), any = paste0("as.numeric(", .bt(dv), " > 0)"), .bt(dv))
  rhs <- character(0)
  if ("champion" %in% spec$fe) rhs <- c(rhs, "factor(bioguide)")
  if ("board" %in% spec$fe && length(unique(data$board)) > 1) rhs <- c(rhs, "factor(board)")
  if ("cycle" %in% spec$fe && length(unique(data$cycle)) > 1) rhs <- c(rhs, "factor(cycle)")
  terms <- character(0)
  # controls the pipeline dropped as nearly collinear (named in the model note) are left out of the formula; exactly
  # collinear ones stay in, and lm() reports them as "not defined because of singularities"
  near <- d$info$near_collinear_controls %||% character(0)
  for (c in spec$controls) {
    if (c == "chamber") {
      if ("chamber=Senate" %in% near) next
      data$chamber <- factor(sdf$chamber, levels = c(SGS$H5_CHAMBER_REFERENCE, setdiff(sort(unique(sdf$chamber)), SGS$H5_CHAMBER_REFERENCE)))
      if (nlevels(droplevels(data$chamber)) > 1) rhs <- c(rhs, "chamber")
    } else if (c == "party") {
      lv <- sort(unique(as.character(sdf$party)))
      pn <- sub("^party=", "", near[startsWith(near, "party=")])
      if (length(pn)) {
        for (l in setdiff(setdiff(lv, SGS$H5_PARTY_REFERENCE), pn)) {
          col <- paste0("party", l)
          data[[col]] <- as.numeric(as.character(sdf$party) == l)
          rhs <- c(rhs, .bt(col))
        }
        next
      }
      data$party <- factor(as.character(sdf$party), levels = c(intersect(SGS$H5_PARTY_REFERENCE, lv), setdiff(lv, SGS$H5_PARTY_REFERENCE)))
      if (nlevels(data$party) > 1) rhs <- c(rhs, "party")
    } else {
      if (c %in% near) next
      data[[c]] <- as.numeric(sdf[[c]])
      rhs <- c(rhs, .bt(c))
      terms[c] <- c
    }
  }
  for (f in spec$focal) { data[[f]] <- as.numeric(sdf[[f]]); rhs <- c(rhs, .bt(f)); terms[f] <- f }
  list(formula = stats::as.formula(paste(lhs, "~", paste(rhs, collapse = " + "))), data = data, terms = terms)
}

# lm() with the formula written into the call, so summary() prints "Call: lm(formula = <the formula>, data = sample)".
sgs_fit_lm <- function(spec_lm) {
  sample <- spec_lm$data
  if (!is.null(spec_lm$weights)) {
    # weighted variants: "Call:" shows weights = <the dollar-base column>
    return(eval(bquote(stats::lm(.(spec_lm$formula), data = sample, weights = .(as.name(spec_lm$weights))))))
  }
  eval(bquote(stats::lm(.(spec_lm$formula), data = sample)))
}

.study_term_lines <- function(c, clusters_txt, draws_word = "draws") {
  enum <- isTRUE(c$boot_enumerated)
  descriptive <- startsWith(.txt0(c$inference), "none")
  L <- c(paste0("  ", c$coefficient),
         paste0("    estimate          ", sgs_fmt(c$estimate), "  (", c$unit, ")"))
  if (descriptive) {
    L <- c(L, paste0("    HC1 SE            ", sgs_fmt(c$hc1_se), "  (reference only)"),
           paste0("    inference         none (DESCRIPTIVE): ", .txt0(c$boot_note)))
  } else {
    L <- c(L,
           paste0("    CR1 SE            ", sgs_fmt(c$cr1_se), "  (cluster-robust, ", clusters_txt, ")"),
           paste0("    HC1 SE            ", sgs_fmt(c$hc1_se), "  (reference only)"),
           paste0("    bootstrap p       ", sgs_fmt(c$boot_p), "  (wild cluster restricted, Webb six-point weights, ",
                  sgs_py_fixed(c$boot_draws, 0, comma = TRUE), " draws", if (enum) ", all 6^G enumerated" else
                    paste0(", seed ", sgs_int_str(SGS$SEED)), ")"),
           paste0("    bootstrap 95% CI  ", sgs_ci_text(c$ci_low, c$ci_high), "  (test inversion)"))
    if (nzchar(.txt0(c$boot_note))) L <- c(L, paste0("    note              ", c$boot_note))
  }
  L
}

.strata_lines <- function(strata, coef) {
  rows <- Filter(function(s) identical(s$coefficient, coef), strata)
  out <- character(0)
  for (s in rows) {
    name <- if (!is.null(s$board)) paste0("board ", s$board) else s$study_sector
    out <- c(out, if (identical(s$status, "estimated")) {
      paste0("      ", name, ": b = ", sgs_fmt(s$estimate), " (HC1 se ", sgs_fmt(s$hc1_se),
             if (!is.null(s$cr1_se)) paste0(", CR1 se ", sgs_fmt(s$cr1_se)) else "", "; n = ", sgs_py_str(s$n),
             if (!is.null(s$cycles)) paste0(", cycles ", s$cycles) else paste0(", years ", s$years),
             ", residual df ", sgs_py_str(s$resid_df), ")")
    } else paste0("      ", name, ": insufficient (", s$reason, ")"))
  }
  out
}

# The lm-vs-pipeline check. Two fits of the same model agree when their coefficients differ by less than 1e-8
# relative, or, for a coefficient that is zero in exact arithmetic (for example a constant outcome), when both are
# zero to rounding on the outcome's own scale: |b| and |difference| below 1e-10 x rms(y) / rms(x), i.e. the term moves
# the fitted values by less than 1e-10 of the outcome's size. A relative difference between two rounding noises
# (1e-17 against 5e-17) is meaningless, which is why the second leg exists.
SGS_SUMMARY_REL_TOL <- 1e-8
SGS_SUMMARY_ZERO_TOL <- 1e-10
# Console width of the printed summaries: wide enough that a coefficient table with long names (SLOPES:
# growth_previous_year_pct:factor(study_sector)property_casualty) prints as one table, as in a wide R console.
SGS_SUMMARY_WIDTH <- 150

.joint_lines <- function(c) {
  restricted <- if (identical(c$joint_kind %||% "equal", "zero")) paste0("no ", c$joint_var, " term") else
    if (grepl("slopes equal$", c$coefficient)) "one common slope" else paste0("one common ", c$joint_var, " term")
  c(paste0("  ", c$coefficient),
    paste0("    F statistic       ", sgs_fmt(c$estimate), "  (", c$unit, ")"),
    paste0("    bootstrap p       ", sgs_fmt(c$boot_p), "  (wild cluster restricted bootstrap of the F statistic by sector, ",
           "Webb six-point weights, ", sgs_py_fixed(c$boot_draws, 0, comma = TRUE), " draws",
           if (isTRUE(c$boot_enumerated)) ", all 6^G enumerated" else paste0(", seed ", sgs_int_str(SGS$SEED)),
           "; restricted model: ", restricted, ")"),
    paste0("    classical F p     ", sgs_fmt(c$joint_p_classical %||% NA_real_), "  (reference only; the anova() print above)"))
}

# One block: header, the captured summary(), the study-inference block, and the lm-vs-pipeline check rows.
# extra_print: more R output printed after summary() (the anova() of a SLOPES model against its one-slope model);
# joint_F: that anova's F, checked against the pipeline's joint test; extra_line: a count line (ASYM / DECEL, DS base).
.summary_block <- function(header, fit, terms, coefs, strata, clusters_txt, sample_line, flag_line = "", pipeline_df = NA_real_,
                           extra_print = character(0), joint_F = NA_real_, extra_line = "", diag_of = function(term) NULL) {
  op <- options(width = SGS_SUMMARY_WIDTH); on.exit(options(op), add = TRUE)
  lm_df <- fit$df.residual
  pipeline_df <- suppressWarnings(as.numeric(pipeline_df))
  df_ok <- !is.na(pipeline_df) && isTRUE(lm_df == pipeline_df)
  # R's own warnings from summary() are printed under it, as an R console would show them, not lost on stderr
  warn <- character(0)
  s <- withCallingHandlers(utils::capture.output(summary(fit)),
                           warning = function(w) { warn <<- c(warn, conditionMessage(w)); invokeRestart("muffleWarning") })
  if (length(warn) == 1L) s <- c(s, "Warning message:", paste0("In summary.lm(fit) : ", warn))
  if (length(warn) > 1L) s <- c(s, "Warning messages:", paste0(seq_along(warn), ": In summary.lm(fit) : ", warn))
  lmc <- stats::coef(fit)
  mm <- stats::model.matrix(fit)
  rms <- function(v) sqrt(mean(as.numeric(v)^2))
  y_rms <- rms(stats::model.response(stats::model.frame(fit)))
  checks <- list()
  inf <- c("", "--- Study inference for the focal term(s): the Std. Error, t value and Pr(>|t|) above are classical OLS",
           "--- and are NOT the study's inference, which is:")
  for (c in coefs) {
    if (identical(c$test, "joint")) {
      # the joint test of a per-sector model: its F equals the anova() F of the restricted model against this one
      jf <- if (!is.null(names(joint_F)) && c$coefficient %in% names(joint_F)) unname(joint_F[c$coefficient]) else unname(joint_F[1])
      rel <- abs(jf - c$estimate) / max(abs(jf), abs(c$estimate), 1e-300)
      agree <- isTRUE(rel < SGS_SUMMARY_REL_TOL) && df_ok
      checks[[length(checks) + 1L]] <- data.frame(term = c$coefficient, lm_term = "anova() F", lm_estimate = jf,
                                                  pipeline_estimate = c$estimate, rel_diff = rel, zero_both = FALSE,
                                                  lm_resid_df = lm_df, pipeline_resid_df = pipeline_df, agree = agree,
                                                  stringsAsFactors = FALSE)
      inf <- c(inf, .joint_lines(c),
               paste0("    check             anova() F = ", sgs_py_repr_float(jf), "; pipeline F = ", sgs_py_repr_float(c$estimate),
                      "; relative difference ", formatC(rel, format = "e", digits = 2), if (!agree) "; MISMATCH" else ""))
      next
    }
    lm_name <- unname(terms[c$coefficient])
    # R names an interaction's columns in the order its variables first appear in the formula: the second per-sector
    # variable of an ASYM-SLOPES model prints as factor(study_sector)<s>:<v>, not <v>:factor(study_sector)<s>
    if (!is.na(lm_name) && !lm_name %in% names(lmc) && grepl(":factor(study_sector)", lm_name, fixed = TRUE)) {
      parts <- strsplit(lm_name, ":factor(study_sector)", fixed = TRUE)[[1]]
      alt <- paste0("factor(study_sector)", parts[2], ":", parts[1])
      if (alt %in% names(lmc)) lm_name <- alt
    }
    diff_term <- !is.na(lm_name) && grepl(" - ", lm_name, fixed = TRUE)
    if (diff_term) {
      ab <- strsplit(lm_name, " - ", fixed = TRUE)[[1]]
      lm_est <- if (all(ab %in% names(lmc))) unname(lmc[ab[1]] - lmc[ab[2]]) else NA_real_
    } else {
      lm_est <- if (!is.na(lm_name) && lm_name %in% names(lmc)) unname(lmc[lm_name]) else NA_real_
    }
    absd <- abs(lm_est - c$estimate)
    rel <- absd / max(abs(lm_est), abs(c$estimate), 1e-300)
    scale <- if (!diff_term && !is.na(lm_name) && lm_name %in% colnames(mm)) y_rms / rms(mm[, lm_name]) else NA_real_
    zero_both <- is.finite(scale) && isTRUE(max(abs(lm_est), abs(c$estimate)) <= SGS_SUMMARY_ZERO_TOL * scale)
    agree <- (isTRUE(rel < SGS_SUMMARY_REL_TOL) || (zero_both && isTRUE(absd <= SGS_SUMMARY_ZERO_TOL * scale))) && df_ok
    checks[[length(checks) + 1L]] <- data.frame(term = c$coefficient, lm_term = lm_name %||% NA_character_,
                                                lm_estimate = lm_est, pipeline_estimate = c$estimate, rel_diff = rel,
                                                zero_both = zero_both, lm_resid_df = lm_df, pipeline_resid_df = pipeline_df,
                                                agree = agree, stringsAsFactors = FALSE)
    inf <- c(inf, .study_term_lines(c, clusters_txt))
    inf <- c(inf, paste0("    strata            ", .txt0(c$stratification)), .strata_lines(strata, c$coefficient))
    # coordinator's revision of 2026-09-26: the term's DESCRIPTIVE label, incremental fit, two-way sensitivity and
    # temporal support (sgs_review.R)
    dg <- diag_of(c$coefficient)
    if (!is.null(dg)) {
      f6 <- function(x) if (is.null(x) || is.na(x) || !is.finite(x)) "n/a" else sgs_py_fixed(x, 6)
      if (nzchar(.txt0(dg$term_label))) {
        inf <- c(inf, paste0("    term label        ", dg$term_label, ": the bootstrap lines above are reference only, not the ",
                             "study's inference"))
      }
      inf <- c(inf, paste0("    incremental fit   adjusted R^2 ", f6(dg$adj_r2_with), " with the term, ", f6(dg$adj_r2_without),
                           " without it (same rows), change ", f6(dg$adj_r2_change), "; R^2 increment ", f6(dg$r2_increment),
                           "; partial R^2 ", f6(dg$partial_r2)),
               paste0("    two-way SE        ", if (is.finite(dg$se_2way %||% NA_real_))
                 paste0(sgs_fmt(dg$se_2way), ", p ", sgs_fmt(dg$p_2way), " (", .txt0(dg$twoway_note), "; common-year shocks; a ",
                        "sensitivity, not the study's inference)") else paste0("n/a (", .txt0(dg$twoway_note), ")")),
               paste0("    temporal support  ", .txt0(dg$temporal_support)))
    }
    inf <- c(inf, paste0("    check             lm() coefficient ", lm_name, " = ", sgs_py_repr_float(lm_est),
                         "; pipeline estimate = ", sgs_py_repr_float(c$estimate),
                         "; relative difference ", formatC(rel, format = "e", digits = 2),
                         if (zero_both) "; both are zero to rounding on the outcome's scale" else "",
                         "; residual df lm() ", sgs_py_str(lm_df), ", pipeline ", if (is.na(pipeline_df)) "n/a" else sgs_py_str(pipeline_df),
                         if (!agree) "; MISMATCH" else ""))
  }
  inf <- c(inf, paste0("  sample            ", sample_line))
  # extra lines: one or more; a named element prints under its name (SHIFT: "minimum base", "dollar base",
  # "identification"), an unnamed one as "counts" (ASYM / DECEL / CONTRACT counts, the DS dollar base)
  el <- as.character(extra_line %||% character(0))
  labs <- names(extra_line) %||% rep("", length(el))
  for (i in which(!is.na(el) & nzchar(el))) {
    lab <- if (nzchar(labs[i])) labs[i] else "counts"
    inf <- c(inf, paste0("  ", lab, strrep(" ", max(1L, 18L - nchar(lab))), sub("^- ", "", el[i])))
  }
  if (nzchar(flag_line)) inf <- c(inf, paste0("  flags             ", flag_line))
  # the fit as summary() computes it (the fit table compares the printed values with the previous run's)
  sm <- suppressWarnings(summary(fit))
  fitrow <- data.frame(r2 = as.numeric(sm$r.squared %||% NA_real_), adj_r2 = as.numeric(sm$adj.r.squared %||% NA_real_),
                       nobs = length(stats::residuals(fit)), lm_resid_df = lm_df, stringsAsFactors = FALSE)
  list(lines = c(header, "", s, extra_print, inf, ""), checks = do.call(rbind, checks), fit = fitrow)
}

.sy_sample_line <- function(r) {
  paste0("n = ", sgs_py_str(r$n), " rows, ", sgs_py_str(r$n_sectors), " sectors (", .txt0(r$sectors), "), ",
         sgs_py_str(r$n_years), " years (", .txt0(r$years), "); window ", .txt0(r$window_used), " (", .txt0(r$window_kind),
         "); residual df ", sgs_py_str(r$resid_df))
}

# Write results/summaries_<run>.txt. Returns (invisibly) the check table: every focal term of every block with the
# lm() coefficient, the pipeline estimate and their relative difference.
sgs_write_summaries <- function(path, run_id, order_, decisions, results, est_rows, engine, rules, term_diag = NULL) {
  op <- options(width = SGS_SUMMARY_WIDTH); on.exit(options(op), add = TRUE)
  rows <- setNames(est_rows, vapply(est_rows, `[[`, "", "test_id"))
  ids <- names(order_)[vapply(order_, function(t) identical(rows[[t$id]]$status, SGS_ESTIMABLE), TRUE)]
  lab <- vapply(ids, function(i) rows[[i]]$label, "")
  rank <- match(lab, SGS_SUMMARY_LABEL_ORDER); rank[is.na(rank)] <- length(SGS_SUMMARY_LABEL_ORDER) + 1
  ids <- ids[order(rank, match(ids, names(order_)))]
  blocks <- list(); checks <- list(); fits <- list(); errors <- character(0)
  for (id in ids) {
    t <- order_[[id]]; r <- rows[[id]]
    diag_of <- function(term) if (is.null(term_diag)) NULL else term_diag[[paste(id, term, sep = "\r")]]
    blk <- tryCatch({
      # a saturated SHIFT model is marked DESCRIPTIVE (SATURATED) in its header (coordinator's rulings of 2026-09-26)
      ninf <- grepl(SGS$SATURATED_LABEL, .txt0(r$flag), fixed = TRUE)
      header <- c(strrep("=", 100), paste0("==== ", id, "  [", r$label, "]", if (identical(r$label, "PREVIEW")) paste0("  ", SGS$PREVIEW_FLAG) else "",
                                           if (ninf) paste0("  ", SGS$SATURATED_LABEL) else ""),
                  paste0("DV: ", .txt0(r$dv_column), if (nzchar(.txt0(r$dv_label))) paste0(" (", r$dv_label, ")") else ""),
                  paste0("Model: ", .txt0(r$summary_note %||% r$note)), strrep("=", 100))
      if (identical(t$table, "champions")) {
        d <- decisions[[id]]
        sl <- sgs_lm_h5(t, d)
        fit <- sgs_fit_lm(sl)
        res <- results[[id]]
        list(.summary_block(header, fit, sl$terms, res$coefs, res$strata,
                            paste0("clustered by champion (bioguide), ", sgs_py_str(r$n_clusters), " clusters"),
                            paste0("n = ", sgs_py_str(r$n), " rows (", sgs_py_str(r$n_champions), " champions, ",
                                   sgs_py_str(r$n_member_cycles), " member-cycles), cycles ", .txt0(r$years), ", boards ",
                                   .txt0(r$boards), "; residual df ", sgs_py_str(r$resid_df)), .txt0(r$flag),
                            pipeline_df = r$resid_df, diag_of = diag_of))
      } else {
        src <- if (identical(t$variant, "derived")) t$base else id
        d <- decisions[[src]]
        att <- sgs_decision_chosen(d)
        res <- results[[src]]
        base_spec <- order_[[src]]
        clusters_txt <- paste0("clustered by ", .txt0(r$cluster_by), ", ", sgs_py_str(r$n_clusters), " clusters")
        if (base_spec$variant %in% c("loso", "loyo")) {
          loso <- identical(base_spec$variant, "loso")
          lspec <- base_spec; lspec$variant <- "level"
          out <- list()
          lo <- vapply(res$subfits, `[[`, "", "left_out")
          for (sf in split(res$subfits, factor(lo, levels = unique(lo)))) {
            u <- sf[[1]]$left_out
            sub <- att$sample$df[if (loso) att$sample$df$study_sector != u else att$sample$df$year != as.numeric(u), , drop = FALSE]
            h <- c(header[1], paste0(header[2], "  - without ", u), header[-(1:2)])
            if (!identical(sf[[1]]$status, "estimated")) {
              out[[length(out) + 1L]] <- list(lines = c(h, "", paste0("not estimable without ", u, ": ", sf[[1]]$reason), ""), checks = NULL)
              next
            }
            sl <- sgs_lm_sector_year(lspec, sub)
            fit <- sgs_fit_lm(sl)
            dsub <- sgs_build_design(sub, lspec)  # the pipeline's own subfit design, for its residual df
            out[[length(out) + 1L]] <- .summary_block(h, fit, sl$terms, sf, list(), paste0("clustered by study sector, ",
                                                      length(unique(sub$study_sector)), " clusters"),
                                                      paste0("n = ", nrow(sub), " rows (", sf[[1]]$n_sectors, " sectors, ",
                                                             sf[[1]]$n_years, " years: ", sf[[1]]$years, ")"),
                                                      .txt0(sf[[1]]$flag),
                                                      pipeline_df = nrow(dsub$X) - sgs_full_rank_check(dsub)$rank)
          }
          out
        } else {
          sl <- sgs_lm_sector_year(base_spec, att$sample$df)
          fit <- sgs_fit_lm(sl)
          # derived read-outs show the source model's coefficients they read; other tests their focal terms (for SLOPES the
          # per-sector slopes, then the joint test; for ASYM the two slopes, then their difference)
          coefs <- if (identical(t$variant, "derived")) Filter(function(c) c$coefficient %in% t$focal, res$coefs) else
            Filter(function(c) isTRUE(c$focal), res$coefs)
          coefs <- coefs[order(match(vapply(coefs, `[[`, "", "coefficient"), t$focal))]
          extra_print <- character(0); joint_F <- NA_real_
          if (identical(base_spec$variant, "slopes")) {
            # each joint test's restricted model against the per-sector model, as anova() prints it
            joint_F <- numeric(0)
            for (jc in Filter(function(c) identical(c$test, "joint"), coefs)) {
              fit0 <- sgs_fit_lm(sgs_lm_restricted(sl, jc$joint_var, jc$joint_kind))
              av <- stats::anova(fit0, fit)
              joint_F[jc$coefficient] <- av$F[2]
              lab <- if (identical(jc$joint_kind, "equal")) {
                if (length(base_spec$focal) == 1L && startsWith(jc$coefficient, "joint: all") && endsWith(jc$coefficient, "slopes equal"))
                  "anova(<one common slope>, <one slope per sector>):" else paste0("anova(<one common ", jc$joint_var, " term>, <one ", jc$joint_var, " term per sector>):")
              } else paste0("anova(<no ", jc$joint_var, " term>, <one ", jc$joint_var, " term per sector>):")
              extra_print <- c(extra_print, "", lab, utils::capture.output(av))
            }
          }
          list(.summary_block(header, fit, sl$terms, coefs, res$strata, clusters_txt, .sy_sample_line(r),
                              paste(Filter(nzchar, c(.txt0(r$flag), if (nzchar(.txt0(r$input_flags))) paste0("input flags: ", r$input_flags))),
                                    collapse = "; "), pipeline_df = r$resid_df, extra_print = extra_print, joint_F = joint_F,
                              extra_line = if (length(r$extra_lines)) r$extra_lines else .txt0(r$extra_line), diag_of = diag_of))
        }
      }
    }, error = function(e) {
      errors <<- c(errors, paste0(id, ": ", conditionMessage(e)))
      list(list(lines = c(strrep("=", 100), paste0("==== ", id, "  [", r$label, "]"), paste0("SUMMARY NOT PRODUCED: ", conditionMessage(e)), ""),
                checks = NULL))
    })
    for (b in blk) {
      blocks[[length(blocks) + 1L]] <- b$lines
      if (!is.null(b$checks)) checks[[length(checks) + 1L]] <- cbind(test_id = id, b$checks, stringsAsFactors = FALSE)
      if (!is.null(b$fit)) {
        wo <- regmatches(b$lines[2], regexec("  - without (.*)$", b$lines[2]))[[1]]
        fits[[length(fits) + 1L]] <- cbind(data.frame(test_id = id, block = if (length(wo)) paste0("without ", wo[2]) else "",
                                                      stringsAsFactors = FALSE), b$fit)
      }
    }
  }
  chk <- if (length(checks)) do.call(rbind, checks) else
    data.frame(test_id = character(0), term = character(0), lm_term = character(0), lm_estimate = numeric(0),
               pipeline_estimate = numeric(0), rel_diff = numeric(0), zero_both = logical(0), lm_resid_df = numeric(0),
               pipeline_resid_df = numeric(0), agree = logical(0))
  fit_df <- if (length(fits)) do.call(rbind, fits) else
    data.frame(test_id = character(0), block = character(0), r2 = numeric(0), adj_r2 = numeric(0), nobs = numeric(0),
               lm_resid_df = numeric(0), stringsAsFactors = FALSE)
  nz <- chk$rel_diff[!chk$zero_both]
  maxrel <- if (length(nz)) max(nz, na.rm = TRUE) else NA
  n_zero <- sum(chk$zero_both)
  bad <- unique(chk$test_id[!chk$agree])
  head <- c(paste0("Model summaries, run ", run_id, " (engine ", engine, ", rule set ", rules$name, ")"),
            paste0("Written ", sgs_utc_iso(Sys.time()), ". One block per ESTIMABLE test (", length(ids), "), ordered ",
                   paste(SGS_SUMMARY_LABEL_ORDER, collapse = ", "), "; registry order within a label."),
            "",
            "Each block prints summary(lm(...)) for the test's model on its gated complete-case sample, exactly as R prints it.",
            "Sector (sector x tier, board, cycle, champion) baselines are factor() terms with an intercept: the same column space",
            "as the pipeline's one-dummy-per-level design, so the same model and fitted values. First differences have no",
            "intercept. In H5 models the fixed-effect factors come first, so lm() leaves out (NA, \"not defined because of",
            "singularities\") the absorbed controls the pipeline drops; a control the pipeline drops as nearly collinear (R^2 >=",
            "0.9999 on the fixed effects and the other regressors, named in the Model line) is not in the formula. Per-sector",
            "blocks (SLOPES, CONTRACT-b, ASYM-SLOPES) add anova() of each joint test's restricted model against the per-sector",
            "model; a per-sector term that does not vary within its sector prints as NA. The classical Std. Error / t / Pr(>|t|) are NOT the",
            "study's inference: under every summary, the study's inference on the focal term(s) is given - CR1 standard error,",
            "wild cluster restricted bootstrap p and 95% interval by test inversion (draws, clusters), and the strata line.",
            if (isTRUE(rules$shift)) c(
              "SHIFT blocks (Paul's partisan-allocation hypothesis): the stacked SHIFT-Chamber model has factor(chamber) +",
              "factor(study_sector) + factor(study_sector):factor(chamber) (one baseline per unit x chamber, the pipeline's cell",
              "dummies); weighted variants (SHIFT-*-W) pass weights = the D + R dollars to lm(); the 'dollar base' line gives the",
              "dollars the shares rest on, and the 'identification' line the year-level parameters, the year-level residual df",
              "and each year's OLS weight on the estimate (expected control varies only by year; SATURATED = no year-level df).",
              "A saturated SHIFT block is marked DESCRIPTIVE (SATURATED) in its header and kept here; it is left out of the",
              "report's SHIFT table and the Trends headline (coordinator's rulings of 2026-09-26). The 'minimum base' line of an",
              "EXPLORATORY -B25K / -B10K / -B50K variant (a post-result exploratory choice) lists the cells whose nominal D + R",
              "base is below its threshold, left out of its sample; the pre-specified SHIFT models keep every share.")
            else character(0),
            paste0("Check: ", if (length(bad)) paste0("the lm() focal coefficient or residual df DIFFERS from the pipeline's in ", paste(bad, collapse = ", "))
                   else "the lm() focal coefficient and residual df equal the pipeline's in every block",
                   " (", nrow(chk), " focal terms; largest relative difference ",
                   if (is.na(maxrel)) "n/a" else formatC(maxrel, format = "e", digits = 2),
                   if (n_zero) paste0("; ", n_zero, " term(s) zero to rounding in both fits, compared on the outcome's scale") else "", ")",
                   if (length(errors)) paste0("; SUMMARY ERRORS: ", paste(errors, collapse = " | ")) else "", "."),
            "")
  lines <- c(head, unlist(blocks))
  sgs_write_lines_crlf(path, lines)
  attr(chk, "errors") <- errors
  attr(chk, "fits") <- fit_df
  invisible(chk)
}

# ---- Fit table (coordinator's ruling of 2026-09-26, after Paul: "these tests seem to be getting worse and worse, look
# at the adjusted r-squared") -------------------------------------------------------------------------------------------
# Every summary block's multiple and adjusted R^2 exactly as summary() printed them (4 significant digits), next to the
# previous R run's, with the reason for each difference. The previous run is read from its own files: the summaries
# (printed R^2, DV, lm() formula, sample line, minimum-base line), the estimability report (the status of a test that
# had no block) and the receipt (input SHA-256).

SGS_FIT_COLS <- c("test_id", "block", "family", "label", "adj_r2_printed", "prev_adj_r2_printed", "adj_r2_change", "direction",
                  "reason", "r2_printed", "prev_r2_printed", "r2_kind", "n", "prev_n", "resid_df", "prev_resid_df", "dv",
                  "prev_dv", "sectors", "prev_sectors", "years", "prev_years", "min_base_cells", "flag", "adj_r2", "r2",
                  "previous_run")
SGS_FIT_PARSE_COLS <- c("test_id", "block", "label", "dv", "formula", "weights", "r2_printed", "adj_r2_printed", "n", "sectors",
                        "years", "window", "resid_df", "min_base_cells", "not_informative")

.fit_num <- function(s) suppressWarnings(as.numeric(s))
.fit_grab <- function(s, re) {
  if (length(s) != 1L || is.na(s)) return(NA_character_)
  g <- regmatches(s, regexec(re, s))[[1]]
  if (length(g) >= 2L) g[2] else NA_character_
}

# One row per block of a summaries_<run>.txt (columns SGS_FIT_PARSE_COLS): test id, sub-block ("without <unit>" for a
# leave-one-out fit), label, DV, the lm() formula and weights of the Call, the multiple and adjusted R^2 as printed, the
# sample line's n / sectors / years / window / residual df, the minimum-base cell count, and whether the block is marked
# DESCRIPTIVE (SATURATED) (header or flags line).
sgs_parse_summaries <- function(path) {
  x <- sub("\r$", "", readLines(path, warn = FALSE, encoding = "UTF-8"))
  hdr <- grep("^==== ", x)
  rows <- vector("list", length(hdr))
  for (k in seq_along(hdr)) {
    i <- hdr[k]
    j <- if (k < length(hdr)) hdr[k + 1L] - 1L else length(x)
    m <- regmatches(x[i], regexec("^==== (\\S+)  \\[([^]]*)\\](.*)$", x[i]))[[1]]
    if (length(m) != 4L) next
    b <- if (j > i) x[(i + 1L):j] else character(0)
    one <- function(re) { h <- grep(re, b); if (length(h)) b[h[1]] else NA_character_ }
    wo <- .fit_grab(m[4], "  - without (.*)$")
    ci <- which(b == "Call:")
    call <- NA_character_
    if (length(ci)) {
      e <- ci[1] + 1L
      while (e <= length(b) && nzchar(trimws(b[e]))) e <- e + 1L
      if (e > ci[1] + 1L) call <- gsub("\\s+", " ", trimws(paste(b[(ci[1] + 1L):(e - 1L)], collapse = " ")))
    }
    rl <- one("^Multiple R-squared:")
    smp <- one("^  sample   ")
    if (!is.na(smp)) smp <- sub("^  sample\\s+", "", smp)
    fl <- one("^  flags   ")
    yrs <- .fit_grab(smp, "\\d+ years \\(([^)]*)\\)")
    if (is.na(yrs)) yrs <- .fit_grab(smp, "\\d+ years: ([^)]*)\\)")
    rows[[k]] <- data.frame(
      test_id = m[2], block = if (is.na(wo)) "" else paste0("without ", wo), label = m[3],
      dv = .fit_grab(one("^DV: "), "^DV: (\\S+)"),
      formula = .fit_grab(call, "formula = (.*), data = sample"), weights = .fit_grab(call, "weights = ([^,)]+)"),
      r2_printed = trimws(.fit_grab(rl, "^Multiple R-squared:\\s*([^,]+),")),
      adj_r2_printed = .fit_grab(rl, "Adjusted R-squared:\\s*(\\S+)"),
      n = .fit_num(.fit_grab(smp, "n = (\\d+) rows")), sectors = .fit_grab(smp, "\\d+ sectors \\(([^)]*)\\)"), years = yrs,
      window = .fit_grab(smp, "window (\\S+)"), resid_df = .fit_num(.fit_grab(smp, "residual df (\\d+)")),
      min_base_cells = .fit_num(.fit_grab(one("^  minimum base   "), ": (\\d+) cell\\(s\\)")),
      not_informative = grepl(SGS$SATURATED_LABEL, x[i], fixed = TRUE) ||
        (!is.na(fl) && grepl(SGS$SATURATED_LABEL, fl, fixed = TRUE)),
      stringsAsFactors = FALSE)
  }
  rows <- Filter(Negate(is.null), rows)
  if (!length(rows)) {
    return(data.frame(setNames(lapply(SGS_FIT_PARSE_COLS, function(c) if (c %in% c("n", "resid_df", "min_base_cells")) numeric(0)
                                      else if (c == "not_informative") logical(0) else character(0)), SGS_FIT_PARSE_COLS),
                      stringsAsFactors = FALSE))
  }
  do.call(rbind, rows)
}

# The previous R run in results_dir: the greatest run id sorting before run_id (run ids are analysis-R-<UTC stamp>, so
# their order is time order) that has a summaries file; NULL when there is none.
sgs_previous_run <- function(results_dir, run_id) {
  f <- list.files(results_dir, pattern = "^summaries_.+\\.txt$")
  ids <- setdiff(sub("^summaries_(.+)\\.txt$", "\\1", f), run_id)
  if (!length(ids)) return(NULL)
  s <- sort(unique(c(ids, run_id)), method = "radix")
  before <- s[seq_len(match(run_id, s) - 1L)]
  if (!length(before)) return(NULL)
  prev <- before[length(before)]
  p <- function(kind, ext) { q <- file.path(results_dir, paste0(kind, "_", prev, ext)); if (file.exists(q)) q else NA_character_ }
  list(run_id = prev, summaries = p("summaries", ".txt"), estimability = p("estimability", ".md"), receipt = p("receipt", ".json"))
}

# test id -> status from an estimability_<run>.md ("## Every test" table).
.fit_prev_status <- function(path) {
  none <- setNames(character(0), character(0))
  if (length(path) != 1L || is.na(path) || !file.exists(path)) return(none)
  x <- sub("\r$", "", readLines(path, warn = FALSE, encoding = "UTF-8"))
  s <- which(x == "## Every test")
  if (!length(s)) return(none)
  r <- grep("^\\| [^|]+ \\| [^|]* \\| (ESTIMABLE|NOT ESTIMABLE|NOT BUILT) \\|", x[s[1]:length(x)], value = TRUE)
  if (!length(r)) return(none)
  p <- strsplit(r, " | ", fixed = TRUE)
  setNames(vapply(p, `[`, "", 3), trimws(sub("^\\|\\s*", "", vapply(p, `[`, "", 1))))
}

# The input workbooks whose SHA-256 differs from the previous receipt's (or that are new / no longer read); NULL
# when the previous receipt is missing or unreadable.
.fit_input_changes <- function(sources, receipt_path) {
  if (length(receipt_path) != 1L || is.na(receipt_path) || !file.exists(receipt_path)) return(NULL)
  rc <- tryCatch(jsonlite::fromJSON(receipt_path, simplifyVector = FALSE), error = function(e) NULL)
  if (is.null(rc) || is.null(rc$inputs)) return(NULL)
  nm <- function(l, f) vapply(l, function(s) as.character(s[[f]] %||% ""), "")
  prev <- setNames(nm(rc$inputs, "sha256"), nm(rc$inputs, "file"))
  cur <- setNames(nm(sources, "sha256"), nm(sources, "file"))
  both <- intersect(names(cur), names(prev))
  added <- setdiff(names(cur), names(prev)); gone <- setdiff(names(prev), names(cur))
  c(both[cur[both] != prev[both]], if (length(added)) paste0(added, " (new)"), if (length(gone)) paste0(gone, " (not read now)"))
}

.fit_terms <- function(f) {
  if (length(f) != 1L || is.na(f)) return(list(lhs = NA_character_, rhs = character(0)))
  p <- strsplit(f, " ~ ", fixed = TRUE)[[1]]
  list(lhs = trimws(p[1]), rhs = if (length(p) > 1L) trimws(strsplit(p[2], " + ", fixed = TRUE)[[1]]) else character(0))
}
.fit_list <- function(s) if (length(s) != 1L || is.na(s) || !nzchar(s)) character(0) else trimws(strsplit(s, ",", fixed = TRUE)[[1]])
.fit_same <- function(a, b) identical(if (length(a) && !is.na(a)) a else NA, if (length(b) && !is.na(b)) b else NA)

# Why a block's fit differs from (or equals) the previous run's block of the same test.
.fit_reason <- function(c, p, inputs) {
  why <- character(0)
  if (!is.na(c$dv) && !is.na(p$dv) && c$dv != p$dv) why <- c(why, paste0("new DV (", p$dv, " -> ", c$dv, ")"))
  if (!is.na(c$formula) && !is.na(p$formula) && c$formula != p$formula) {
    tc <- .fit_terms(c$formula); tp <- .fit_terms(p$formula)
    add <- setdiff(tc$rhs, tp$rhs); drop <- setdiff(tp$rhs, tc$rhs)
    what <- c(if (!identical(tc$lhs, tp$lhs)) paste0("outcome ", tp$lhs, " -> ", tc$lhs),
              if (length(add)) paste0("terms added: ", paste(add, collapse = ", ")),
              if (length(drop)) paste0("terms removed: ", paste(drop, collapse = ", ")))
    why <- c(why, paste0("specification changed (", if (length(what)) paste(what, collapse = "; ") else "term order", ")"))
  }
  if (!.fit_same(c$weights, p$weights)) {
    why <- c(why, paste0("weights ", if (is.na(p$weights)) "none" else p$weights, " -> ", if (is.na(c$weights)) "none" else c$weights))
  }
  if (!.fit_same(c$label, p$label)) why <- c(why, paste0("label ", p$label, " -> ", c$label))
  sc <- .fit_list(c$sectors); sp <- .fit_list(p$sectors)
  if (length(sc) && length(sp)) {
    a <- setdiff(sc, sp); d <- setdiff(sp, sc)
    if (length(a)) why <- c(why, paste0(paste(a, collapse = ", "), " added"))
    if (length(d)) why <- c(why, paste0(paste(d, collapse = ", "), " removed"))
  }
  if (!is.na(c$years) && !is.na(p$years) && c$years != p$years) why <- c(why, paste0("years ", p$years, " -> ", c$years))
  if (!is.na(c$n) && !is.na(p$n) && c$n != p$n) {
    mb <- !is.na(c$min_base_cells) && c$min_base_cells > 0 && (is.na(p$min_base_cells) || p$min_base_cells != c$min_base_cells)
    why <- c(why, paste0("n ", sgs_py_str(p$n), " -> ", sgs_py_str(c$n),
                         if (mb) paste0(" (minimum base: ", sgs_py_str(c$min_base_cells), " cell(s) left out)") else ""))
  }
  if (length(why)) return(paste(why, collapse = "; "))
  if (.fit_same(c$adj_r2_printed, p$adj_r2_printed) && .fit_same(c$r2_printed, p$r2_printed)) return("unchanged")
  paste0("same DV, formula, sectors, years and n; ", if (length(inputs)) paste0("inputs changed: ", paste(inputs, collapse = ", "))
         else "no input workbook changed")
}

.fit_direction <- function(cur, prev) {
  a <- .fit_num(cur); b <- .fit_num(prev)
  if (.fit_same(cur, prev)) return("same")
  if (!is.finite(a) || !is.finite(b)) return("n/a")
  if (a < b) "lower" else if (a > b) "higher" else "same"
}

# The fit table of the current run (its summaries file at summaries_path) against the previous R run in results_dir.
# fits = attr(<sgs_write_summaries result>, "fits") (the unrounded R^2); sources = the run's input workbooks (file,
# sha256); est_rows = the run's estimability rows (family, status). attr "info": the previous run, its files, the
# changed inputs and the counts.
sgs_fit_table <- function(summaries_path, run_id, results_dir, sources = list(), est_rows = list(), fits = NULL,
                          prev = sgs_previous_run(results_dir, run_id)) {
  cur <- sgs_parse_summaries(summaries_path)
  rows <- setNames(est_rows, vapply(est_rows, function(r) as.character(r$test_id), ""))
  fam <- function(id) { r <- rows[[id]]; if (is.null(r)) NA_character_ else .txt0(r$family) }
  pv <- if (!is.null(prev) && !is.na(prev$summaries)) sgs_parse_summaries(prev$summaries) else NULL
  pst <- if (!is.null(prev)) .fit_prev_status(prev$estimability) else character(0)
  inputs <- if (!is.null(prev)) .fit_input_changes(sources, prev$receipt) else NULL
  prev_id <- if (is.null(prev)) NA_character_ else prev$run_id
  key <- function(d) paste(d$test_id, d$block, sep = "\r")
  kind <- function(f, w) if (!is.na(w)) "weighted (lm weights)" else if (!is.na(f) && grepl("~ 0 +", f, fixed = TRUE))
    "uncentered (no intercept)" else "centered"
  out <- list()
  for (i in seq_len(nrow(cur))) {
    c <- cur[i, , drop = FALSE]
    f <- if (!is.null(fits) && nrow(fits)) fits[fits$test_id == c$test_id & fits$block == c$block, , drop = FALSE] else NULL
    p <- if (!is.null(pv)) pv[key(pv) == key(c), , drop = FALSE] else NULL
    has_p <- !is.null(p) && nrow(p) == 1L
    if (is.null(prev)) {
      dir <- "no previous run"; why <- "no earlier R run with a summaries file in the results folder"
    } else if (!has_p) {
      if (c$test_id %in% names(pst)) {
        dir <- "newly estimable"; why <- paste0("newly estimable (", pst[[c$test_id]], " in ", prev_id, ")")
      } else {
        dir <- "new test"; why <- paste0("new test (not in ", prev_id, ")")
      }
      if (nzchar(c$block)) why <- paste0(why, "; sub-fit ", c$block)
    } else {
      dir <- .fit_direction(c$adj_r2_printed, p$adj_r2_printed)
      why <- .fit_reason(c, p, inputs)
    }
    out[[length(out) + 1L]] <- list(
      test_id = c$test_id, block = c$block, family = fam(c$test_id), label = c$label, adj_r2_printed = c$adj_r2_printed,
      prev_adj_r2_printed = if (has_p) p$adj_r2_printed else NA_character_,
      adj_r2_change = if (has_p) .fit_num(c$adj_r2_printed) - .fit_num(p$adj_r2_printed) else NA_real_, direction = dir,
      reason = why, r2_printed = c$r2_printed, prev_r2_printed = if (has_p) p$r2_printed else NA_character_,
      r2_kind = kind(c$formula, c$weights), n = c$n, prev_n = if (has_p) p$n else NA_real_, resid_df = c$resid_df,
      prev_resid_df = if (has_p) p$resid_df else NA_real_, dv = c$dv, prev_dv = if (has_p) p$dv else NA_character_,
      sectors = c$sectors, prev_sectors = if (has_p) p$sectors else NA_character_, years = c$years,
      prev_years = if (has_p) p$years else NA_character_, min_base_cells = c$min_base_cells,
      flag = if (isTRUE(c$not_informative)) SGS$SATURATED_LABEL else "",
      adj_r2 = if (!is.null(f) && nrow(f) == 1L) f$adj_r2 else NA_real_, r2 = if (!is.null(f) && nrow(f) == 1L) f$r2 else NA_real_,
      previous_run = prev_id)
  }
  gone <- if (!is.null(pv)) pv[!key(pv) %in% key(cur), , drop = FALSE] else NULL
  for (i in seq_len(if (is.null(gone)) 0L else nrow(gone))) {
    p <- gone[i, , drop = FALSE]
    st <- rows[[p$test_id]]$status %||% NA_character_
    out[[length(out) + 1L]] <- list(
      test_id = p$test_id, block = p$block, family = fam(p$test_id), label = p$label, adj_r2_printed = NA_character_,
      prev_adj_r2_printed = p$adj_r2_printed, adj_r2_change = NA_real_, direction = "not in this run",
      reason = paste0("no block in this run (", if (is.na(st)) "not in this run's registry" else st, ")"), r2_printed = NA_character_,
      prev_r2_printed = p$r2_printed, r2_kind = kind(p$formula, p$weights), n = NA_real_, prev_n = p$n, resid_df = NA_real_,
      prev_resid_df = p$resid_df, dv = NA_character_, prev_dv = p$dv, sectors = NA_character_, prev_sectors = p$sectors,
      years = NA_character_, prev_years = p$years, min_base_cells = NA_real_, flag = "", adj_r2 = NA_real_, r2 = NA_real_,
      previous_run = prev_id)
  }
  df <- sgs_rows_df(out, SGS_FIT_COLS)
  dirs <- df$direction
  like <- dirs %in% c("lower", "higher", "same") & !grepl("new DV|specification changed|weights | added| removed|years |n [0-9]", df$reason)
  attr(df, "info") <- list(
    previous_run = prev_id, previous_summaries = if (is.null(prev)) NA_character_ else basename(prev$summaries),
    inputs_changed = inputs, receipt_found = !is.null(prev) && !is.na(prev$receipt), blocks = nrow(cur),
    previous_blocks = if (is.null(pv)) NA_integer_ else nrow(pv), unchanged = sum(df$reason == "unchanged"),
    lower = sum(dirs == "lower"), higher = sum(dirs == "higher"), same = sum(dirs == "same"), new_tests = sum(dirs == "new test"),
    newly_estimable = sum(dirs == "newly estimable"), not_in_this_run = sum(dirs == "not in this run"),
    like_for_like_lower = df$test_id[like & dirs == "lower"])
  df
}

# Markdown: what the table compares, the counts, then one row per block (the current summaries order; blocks only in
# the previous run last).
sgs_fit_md <- function(fit) {
  info <- attr(fit, "info") %||% list()
  prev <- info$previous_run %||% NA_character_
  inp <- info$inputs_changed
  lead <- paste0("Adjusted R^2 of every model summary block exactly as summary(lm()) prints it (4 significant digits), next to ",
                 if (is.na(prev)) "the previous R run's (none: no earlier R run with a summaries file in the results folder)" else
                   paste0("the previous R run's (", prev, ", read from ", info$previous_summaries, ")"),
                 ", with the reason for each difference: a new DV, a changed specification (the lm() formula: terms added or ",
                 "removed, weights), sectors added or removed, other years, a different n (SHIFT: the minimum base), a new or ",
                 "newly estimable test, or changed inputs",
                 if (is.na(prev)) "" else if (!isTRUE(info$receipt_found)) " (no previous receipt: inputs not compared)" else
                   paste0(" (SHA-256 of the input workbooks against the previous receipt: ",
                          if (length(inp)) paste(inp, collapse = ", ") else "none changed", ")"), ".")
  read <- paste0("Reading R^2: first-difference models have no intercept, so R prints the uncentered R^2 (r2_kind; not ",
                 "comparable with a level model's); -W models print the weighted R^2. R^2 is not the study's test: a SHIFT ",
                 "estimate rests on the 5-6 yearly values of expected control whatever the R^2 (identification lines), and a ",
                 "saturated SHIFT preview is ", SGS$SATURATED_LABEL, " at any R^2.")
  L <- c(lead, "", read, "")
  if (!is.na(prev)) {
    ids_of <- function(d) {
      k <- fit$test_id[fit$direction == d]
      if (!length(k)) return("")
      tab <- table(factor(k, levels = unique(k)))
      paste0(" (", paste0(names(tab), ifelse(tab > 1, paste0(" x ", as.integer(tab), " blocks"), ""), collapse = ", "), ")")
    }
    L <- c(L, paste0("- Blocks: ", info$blocks, " now, ", info$previous_blocks, " in ", prev, ". In both: ",
                     info$lower + info$higher + info$same, " (", info$unchanged, " unchanged; adjusted R^2 lower in ", info$lower,
                     ", higher in ", info$higher, ", the same in ", info$same, "). New tests: ", info$new_tests, ids_of("new test"),
                     ". Newly estimable: ", info$newly_estimable, ids_of("newly estimable"), ". No block now: ",
                     info$not_in_this_run, ids_of("not in this run"), "."),
           paste0("- Lower adjusted R^2 with the same DV, formula, sectors, years and n (like for like): ",
                  if (length(info$like_for_like_lower)) paste(info$like_for_like_lower, collapse = ", ") else "none", "."), "")
  }
  L <- c(L, "| test | label | adj. R^2 now | previous | change | R^2 now | previous | n now | previous | R^2 kind | reason |",
         "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
  for (i in seq_len(nrow(fit))) {
    x <- fit[i, , drop = FALSE]
    nm <- paste0(x$test_id, if (nzchar(.txt0(x$block))) paste0(" (", x$block, ")") else "",
                 if (nzchar(.txt0(x$flag))) paste0(" ", x$flag) else "")
    L <- c(L, paste0("| ", nm, " | ", .txt0(x$label), " | ", .txt0(x$adj_r2_printed), " | ", .txt0(x$prev_adj_r2_printed), " | ",
                     if (is.finite(x$adj_r2_change)) formatC(x$adj_r2_change, format = "f", digits = 4, flag = "+") else "", " | ",
                     .txt0(x$r2_printed), " | ", .txt0(x$prev_r2_printed), " | ", if (is.na(x$n)) "" else sgs_py_str(x$n), " | ",
                     if (is.na(x$prev_n)) "" else sgs_py_str(x$prev_n), " | ", .txt0(x$r2_kind), " | ", .md_escape(x$reason), " |"))
  }
  L
}
