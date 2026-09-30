# Coordinator's revisions of 2026-09-26, after Paul's fit question ("look at the adjusted r-squared") and the Codex
# methodology review of run analysis-R-20260926T070630Z (rule set paul-2026-09-25 only). Nothing here changes an
# estimate or a p-value of a test; it adds, for every focal term:
#   * incremental fit: R^2 and adjusted R^2 with and without the term on the same rows (as summary.lm computes them:
#     centered when the design spans an intercept, uncentered without one, weighted for -W), the R^2 increment and the
#     partial R^2 (the share of the reduced model's residual sum of squares the term explains);
#   * a common-year sensitivity: the two-way cluster-robust standard error by sector and year (Cameron, Gelbach and
#     Miller 2011: V = V_sector + V_year - V_sector x year, each with its CR1 factor G/(G-1) (n-1)/(n-p)) and a t-based
#     p-value with min(G_sector, G_year) - 1 df, computed when both dimensions have >= 3 clusters (a sensitivity, not
#     the study's inference: two-way clustering with this few groups is itself fragile);
#   * effective temporal support: the distinct years and each year's share of the absolute OLS weight on the estimate
#     (b = sum_i w_i y_i); for a term constant within years, the years with each value (H1-PV: pres_year = 1 in 1 year);
#   * the DESCRIPTIVE term labels: a saturated SHIFT term (no year-level residual df) and a per-sector term resting on
#     one sector cluster; their bootstrap lines are reference only;
# and, for the report: Holm-adjusted p within the pre-specified families, the L-LV robustness table with the review's
# numbers reproduced, the chronology of expected control and the measurement of the money.

SGS_COEF_DIAG_COLS <- c("term_label", "adj_r2_with", "adj_r2_without", "adj_r2_change", "r2_with", "r2_without",
                        "r2_increment", "partial_r2", "se_2way", "p_2way", "df_2way", "clusters_sector", "clusters_year",
                        "twoway_note", "n_years_support", "temporal_support", "holm_family", "holm_p")
SGS_TWOWAY_MIN_CLUSTERS <- 3L

# The Codex methodology review's numbers (C:/Users/pgoff/Documents/Codex/2026-09-26/loo/outputs/methodology_evidence/
# model_diagnostics.csv and growth_family_multiplicity.csv, run analysis-R-20260926T070630Z): the pipeline must
# reproduce them (report section "Codex methodology review: reproduction").
SGS_CODEX_REVIEW <- list(
  `L1-LV` = c(base = 0.0546242468488647, base_n = 94, yearfe = -0.001399922111908, logfe = -8.96030309612581e-05,
              fdy = -0.0321550216615069, fdy_n = 88, adj_with = 0.886286710232235, adj_without = 0.887446151177937,
              partial = 0.00201953547451957, p = 0.745874587458746, holm = 1),
  `L2-LV` = c(base = -0.028466949587963, base_n = 95, yearfe = -0.0175248881597487, logfe = 0.00246956625731751,
              fdy = 0.04771327930623, fdy_n = 89, adj_with = 0.886176891297038, adj_without = 0.88747502631687,
              partial = 0.000650768742520776, p = 0.952695269526953, holm = 1),
  `L3-LV` = c(base = 0.352479253388368, base_n = 77, yearfe = -0.47651166591925, logfe = -0.00632361114003213,
              fdy = -0.536713438327155, fdy_n = 71, adj_with = 0.884716943364369, adj_without = 0.884689648813057,
              partial = 0.015617678894196, p = 0.0375037503750375, holm = 0.112511251125113))
SGS_CODEX_REVIEW_TOL <- 1e-6   # relative

# Pre-specified families for the Holm adjustment (coordinator's revision of 2026-09-26). Only ESTIMABLE, non-DESCRIPTIVE
# focal terms enter; each family is adjusted over the members present in the run, and its NOT ESTIMABLE members are
# listed. Minimal families: they do not correct for the study's whole specification search.
SGS_HOLM_FAMILIES <- list(
  list(family = "C growth timing", tests = c("C1", "C2", "C3"),
       definition = paste0("the three core contribution tests of the plan: contributions on prior-year (C1), same-year (C2) and ",
                           "predicted (C3) growth, one focal term each")),
  list(family = "L-LV growth timing", tests = c("L1-LV", "L2-LV", "L3-LV"),
       definition = "LobbyView lobbying on the same three growth measures, one focal term each (the Codex review's minimal family)"),
  list(family = "L income growth timing", tests = c("L1-income", "L2-income", "L3-income"),
       definition = "LDA outside-firm lobbying income on the three growth measures"),
  list(family = "L expenses growth timing", tests = c("L1-expenses", "L2-expenses", "L3-expenses"),
       definition = "LDA self-filer lobbying expenses on the three growth measures"),
  list(family = "SHIFT (pre-specified)", tests = c("SHIFT-House", "SHIFT-Senate", "SHIFT-Chamber", "SHIFT-All", "SHIFT-All-House",
                                                   "SHIFT-All-Senate"),
       definition = paste0("the six pre-specified SHIFT models of Paul's partisan-allocation hypothesis, every focal term ",
                           "(SHIFT-All: exp_dem_house and exp_dem_senate), main window")),
  list(family = "SHIFT preview (pre-specified)", tests = paste0(c("SHIFT-House", "SHIFT-Senate", "SHIFT-Chamber", "SHIFT-All",
                                                                  "SHIFT-All-House", "SHIFT-All-Senate"), "-PV"),
       definition = paste0("the 2021-2025 previews of the six pre-specified SHIFT models; a ", SGS$SATURATED_LABEL, " term has no ",
                           "inference and is not in the family")))

# Diagnostics of the focal terms of one fitted design. design_fit = the design the fit used (weighted rows scaled by
# sqrt(w)); design_raw = the unweighted design (years, clusters, the terms' own values); intercept = the design spans an
# intercept (fixed effects). Returns a named list (one element per term).
sgs_term_diagnostics <- function(design_fit, fit, terms, intercept, design_raw = design_fit, time_word = "years") {
  X <- design_fit$X; yv <- design_fit$y
  n <- nrow(X); p <- ncol(X)
  w <- if (isTRUE(design_fit$weighted)) design_fit$w else rep(1, n)
  y0 <- design_raw$y
  tss <- if (intercept) sum(w * (y0 - sum(w * y0) / sum(w))^2) else sum(w * y0^2)
  rss <- sum(fit$resid^2)
  dfint <- if (intercept) 1 else 0
  adj <- function(r2, rdf) if (rdf > 0) 1 - (1 - r2) * ((n - dfint) / rdf) else NaN
  r2f <- 1 - rss / tss
  adjf <- adj(r2f, n - p)
  yrs <- design_raw$years
  sec <- design_raw$clusters
  Gs <- length(unique(sec)); Gt <- length(unique(yrs))
  u <- fit$resid
  crv <- function(g) {
    G <- length(unique(g))
    S <- rowsum(X * u, g, reorder = TRUE)
    (G / (G - 1)) * ((n - 1) / (n - p)) * fit$A %*% crossprod(S) %*% fit$A
  }
  two <- if (Gs >= SGS_TWOWAY_MIN_CLUSTERS && Gt >= SGS_TWOWAY_MIN_CLUSTERS && n > p) {
    crv(sec) + crv(yrs) - crv(paste(sec, yrs))
  } else NULL
  Wt <- fit$A %*% t(X)
  sw <- sqrt(w)
  out <- list()
  for (term in terms) {
    k <- match(term, fit$names)
    if (is.na(k)) next
    Xr <- X[, -k, drop = FALSE]
    rss_r <- if (ncol(Xr)) sum(qr.resid(qr(Xr, tol = 1e-12, LAPACK = FALSE), yv)^2) else sum(yv^2)
    r2r <- 1 - rss_r / tss
    adjr <- adj(r2r, n - (p - 1))
    se2 <- NA_real_; p2 <- NA_real_; df2 <- NA_real_; note2 <- ""
    if (is.null(two)) {
      note2 <- paste0("not computed: ", Gs, " sector and ", Gt, " ", sub("s$", "", time_word), " clusters (needs >= ",
                      SGS_TWOWAY_MIN_CLUSTERS, " of each)")
    } else {
      v <- two[k, k]
      if (!is.finite(v) || v <= 0) {
        note2 <- "two-way variance not positive (V_sector + V_year - V_sector x year <= 0)"
      } else {
        se2 <- sqrt(v); df2 <- min(Gs, Gt) - 1
        p2 <- 2 * stats::pt(-abs(fit$beta[k] / se2), df2)
        note2 <- paste0("two-way CR1 (", Gs, " sector x ", Gt, " ", sub("s$", "", time_word), " clusters), t with ", df2, " df")
      }
    }
    # temporal support: each year's share of the absolute OLS weight on the estimate (weighted fits: on the unscaled y)
    a <- as.vector(Wt[k, ]) * sw
    sh <- tapply(abs(a), yrs, sum)
    sh <- sh / sum(sh)
    o <- order(-sh, as.numeric(names(sh)))
    top <- utils::head(o, 5)
    txt <- paste0(length(sh), " distinct ", time_word, " (", sgs_years_text(as.numeric(names(sh))), "); share of the absolute ",
                  "OLS weight: ", paste0(names(sh)[top], " ", vapply(100 * sh[top], sgs_py_fixed, "", d = 1), "%", collapse = ", "),
                  if (length(o) > 5) paste0(", the other ", length(o) - 5, " ", sgs_py_fixed(100 * sum(sh[o[-(1:5)]]), 1), "%") else "")
    xk <- design_raw$X[, k]
    wy <- tapply(xk, yrs, function(v) max(v) - min(v))
    if (all(wy <= 1e-12 * max(1, max(abs(xk))))) {
      v1 <- tapply(xk, yrs, function(v) v[1])
      if (all(v1 %in% c(0, 1))) {
        txt <- paste0(txt, "; ", term, " = 1 in ", sum(v1 == 1), " of ", length(v1), " ", time_word,
                      if (any(v1 == 1)) paste0(" (", sgs_years_text(as.numeric(names(v1))[v1 == 1]), ")") else "")
      } else {
        txt <- paste0(txt, "; ", term, " varies only by ", sub("s$", "", time_word), " (", length(unique(round(v1, 12))),
                      " distinct values)")
      }
    }
    out[[term]] <- list(adj_r2_with = adjf, adj_r2_without = adjr, adj_r2_change = adjf - adjr, r2_with = r2f, r2_without = r2r,
                        r2_increment = r2f - r2r, partial_r2 = if (rss_r > 0) (rss_r - rss) / rss_r else NA_real_,
                        se_2way = se2, p_2way = p2, df_2way = df2, clusters_sector = Gs, clusters_year = Gt, twoway_note = note2,
                        n_years_support = length(sh), temporal_support = txt)
  }
  out
}

# The diagnostics of every focal term of every ESTIMABLE test (derived read-outs: the terms they read from their source
# model; leave-one-out tests: none, their sub-fits are diagnostics). Returns a named list keyed "test\rterm".
sgs_term_diag_table <- function(order_, decisions, results) {
  out <- list()
  for (t in order_) {
    src <- if (identical(t$variant, "derived")) t$base else t$id
    d <- decisions[[src]]
    spec <- order_[[src]] %||% t
    if (is.null(d) || !identical(d$status, SGS_ESTIMABLE) || spec$variant %in% c("loso", "loyo")) next
    raw <- if (identical(spec$table, "champions")) d$design else sgs_decision_chosen(d)$design
    if (is.null(raw)) next
    dfit <- sgs_weighted_design(raw)
    fit <- sgs_ols(dfit)
    terms <- if (identical(t$variant, "derived")) t$focal else sgs_focal_names(spec, fit$names)
    terms <- terms[terms %in% fit$names]
    if (!length(terms)) next
    res <- results[[src]]
    dg <- sgs_term_diagnostics(dfit, fit, terms, intercept = isTRUE(raw$intercept_spanned), design_raw = raw,
                               time_word = if (identical(spec$table, "champions")) "cycles" else "years")
    for (term in names(dg)) {
      lab <- if (isTRUE(res$identification$saturated)) SGS$SATURATED_LABEL else
        if (identical(spec$variant, "slopes") && grepl(":", term, fixed = TRUE)) SGS$ONE_CLUSTER_LABEL else
          if (isTRUE(res$descriptive)) "DESCRIPTIVE" else ""
      out[[paste(t$id, term, sep = "\r")]] <- c(list(test_id = t$id, coefficient = term, term_label = lab), dg[[term]])
    }
  }
  out
}

# Holm-adjusted p within the pre-specified families. coef_rows carry term_label (DESCRIPTIVE terms are left out).
SGS_HOLM_COLS <- c("family", "definition", "members", "not_estimable_members", "test_id", "coefficient", "p_unadjusted",
                   "holm_p", "m", "note")
sgs_holm_table <- function(est_rows, coef_rows) {
  st <- setNames(vapply(est_rows, function(r) as.character(r$status), ""), vapply(est_rows, function(r) as.character(r$test_id), ""))
  out <- list()
  for (f in SGS_HOLM_FAMILIES) {
    present <- f$tests[f$tests %in% names(st)]
    if (!length(present)) next
    est <- present[st[present] == SGS_ESTIMABLE]
    ne <- setdiff(present, est)
    cs <- Filter(function(c) c$test_id %in% est && isTRUE(c$focal) && is.null(c$left_out) &&
                   !(c$test %||% "") %in% c("joint", "equality"), coef_rows)
    desc <- vapply(cs, function(c) nzchar(as.character(c$term_label %||% "")), TRUE)
    pv <- vapply(cs, function(c) as.numeric(c$boot_p %||% NA_real_), 0)
    keep <- !desc & is.finite(pv)
    h <- if (any(keep)) stats::p.adjust(pv[keep], "holm") else numeric(0)
    base <- list(family = f$family, definition = f$definition, members = paste(present, collapse = ", "),
                 not_estimable_members = paste(ne, collapse = ", "))
    if (!length(cs)) {
      out[[length(out) + 1L]] <- c(base, list(test_id = "", coefficient = "", p_unadjusted = NA_real_, holm_p = NA_real_, m = 0,
                                              note = "no ESTIMABLE member in this run"))
      next
    }
    j <- 0L
    for (i in seq_along(cs)) {
      c <- cs[[i]]
      if (keep[i]) j <- j + 1L
      out[[length(out) + 1L]] <- c(base, list(
        test_id = c$test_id, coefficient = c$coefficient, p_unadjusted = pv[i], holm_p = if (keep[i]) h[j] else NA_real_,
        m = sum(keep), note = if (desc[i]) paste0(c$term_label, ": no inference, not in the family") else
          if (!is.finite(pv[i])) "no bootstrap p" else if (length(ne)) paste0("adjusted over the ", sum(keep), " ESTIMABLE term(s); ",
                                                                           "NOT ESTIMABLE now: ", paste(ne, collapse = ", ")) else ""))
    }
  }
  sgs_rows_df(out, SGS_HOLM_COLS)
}

.r4 <- function(x) if (is.null(x) || length(x) != 1L || is.na(x)) "n/a" else sgs_fmt(x)
.r6 <- function(x) if (is.null(x) || length(x) != 1L || is.na(x) || !is.finite(x)) "n/a" else sgs_py_fixed(x, 6)

sgs_holm_md <- function(holm) {
  L <- c(paste0("Holm's step-down adjustment (stats::p.adjust(p, \"holm\")) of the wild cluster bootstrap p-values within each ",
                "pre-specified family; the unadjusted p stays shown. A family is adjusted over its ESTIMABLE, non-DESCRIPTIVE ",
                "terms in this run (its NOT ESTIMABLE members are named). These are minimal families: they do not correct for ",
                "the study's whole search over specifications and variants, and no multiplicity correction repairs a dependence ",
                "structure the sector-cluster bootstrap misses (common-year shocks; see the sensitivity section)."), "")
  for (fam in unique(holm$family)) {
    x <- holm[holm$family == fam, , drop = FALSE]
    L <- c(L, paste0("**", fam, "**: ", x$definition[1], ". Members: ", x$members[1],
                     if (nzchar(.txt0(x$not_estimable_members[1]))) paste0(" (NOT ESTIMABLE now: ", x$not_estimable_members[1], ")") else "",
                     "."), "")
    if (all(!nzchar(x$test_id))) { L <- c(L, "- no ESTIMABLE member in this run", ""); next }
    L <- c(L, "| test | term | p (unadjusted) | Holm p | terms in the family | note |", "|---|---|---:|---:|---:|---|")
    for (i in seq_len(nrow(x))) {
      L <- c(L, paste0("| ", x$test_id[i], " | ", x$coefficient[i], " | ", .r4(x$p_unadjusted[i]), " | ", .r4(x$holm_p[i]), " | ",
                       sgs_py_str(x$m[i]), " | ", .md_escape(.txt0(x$note[i])), " |"))
    }
    L <- c(L, "")
  }
  L
}

# Incremental fit of every focal term (report section).
sgs_incremental_md <- function(coef_rows) {
  cs <- Filter(function(c) !is.null(c$adj_r2_with) && is.finite(c$adj_r2_with %||% NA_real_), coef_rows)
  L <- c(paste0("For every focal term of every ESTIMABLE test: adjusted R^2 of the test's model with the term and without it on ",
                "the same rows, their change, the R^2 increment and the partial R^2 (the share of the reduced model's residual ",
                "variation the term explains). A high total R^2 comes mostly from the sector baselines and the year terms; it is ",
                "not evidence for the focal regressor (the Codex review: L3-LV adjusted R^2 0.884717 with predicted growth, ",
                "0.884690 without, on the same 77 rows). First-difference models without an intercept use R's uncentered R^2."), "",
         "| test | term | n | adj. R^2 with | adj. R^2 without | change | R^2 increment | partial R^2 | term label |",
         "|---|---|---:|---:|---:|---:|---:|---:|---|")
  for (c in cs) {
    L <- c(L, paste0("| ", c$test_id, " | ", c$coefficient, " | ", sgs_py_str(c$n %||% NA), " | ", .r6(c$adj_r2_with), " | ",
                     .r6(c$adj_r2_without), " | ", .r6(c$adj_r2_change), " | ", .r6(c$r2_increment), " | ", .r6(c$partial_r2), " | ",
                     .txt0(c$term_label), " |"))
  }
  L
}

# Inference sensitivity: common-year shocks and temporal support (report section).
sgs_sensitivity_md <- function(coef_rows) {
  cs <- Filter(function(c) !is.null(c$temporal_support), coef_rows)
  L <- c(paste0("The study's inference clusters by sector (Mentat industry for SHIFT; champion for H5): it allows dependence ",
                "within a sector over time but not shocks common to every sector in a year. The two-way cluster-robust error (sector ",
                "and year; H5: champion and cycle) with a t reference on min(G) - 1 df is a small-sample sensitivity for those ",
                "common-year shocks, computed where both dimensions have >= 3 clusters; with this few years it is itself fragile ",
                "and is not the study's inference. Temporal support: the distinct years of the sample and each year's share of the ",
                "absolute OLS weight on the estimate (a year-level term: the years with each value). A ", SGS$SATURATED_LABEL,
                " term (no year-level residual df) and a ", SGS$ONE_CLUSTER_LABEL, " term are DESCRIPTIVE: their bootstrap ",
                "lines are reference only."), "",
         "| test | term | term label | estimate | CR1 SE | bootstrap p | two-way SE | two-way p (df) | temporal support |",
         "|---|---|---|---:|---:|---:|---:|---|---|")
  for (c in cs) {
    tw <- if (is.finite(c$p_2way %||% NA_real_)) paste0(.r4(c$p_2way), " (", sgs_py_str(c$df_2way), ")") else .txt0(c$twoway_note)
    L <- c(L, paste0("| ", c$test_id, " | ", c$coefficient, " | ", .txt0(c$term_label), " | ", .r4(c$estimate), " | ",
                     .r4(c$cr1_se %||% NA_real_), " | ", .r4(c$boot_p %||% NA_real_), " | ", .r4(c$se_2way), " | ", .md_escape(tw), " | ",
                     .md_escape(.txt0(c$temporal_support)), " |"))
  }
  L
}

# The L-LV robustness table and the reproduction of the Codex review's numbers (report section).
sgs_lv_robustness_md <- function(est_rows, coef_rows) {
  rows <- setNames(est_rows, vapply(est_rows, function(r) as.character(r$test_id), ""))
  pooled <- function(id, g) {
    x <- Filter(function(c) identical(c$test_id, id) && identical(c$coefficient, g) && is.null(c$left_out), coef_rows)
    if (length(x)) x[[1]] else NULL
  }
  subfits_of <- function(id, g) Filter(function(c) identical(c$test_id, id) && identical(c$coefficient, g) && !is.null(c$left_out) &&
                                         identical(c$subfit_status %||% c$status, "estimated"), coef_rows)
  cell <- function(id, g) {
    r <- rows[[id]]
    if (is.null(r)) return("not in the run")
    if (!identical(r$status, SGS_ESTIMABLE)) return(r$status)
    c <- pooled(id, g)
    if (is.null(c)) return("n/a")
    paste0(sgs_fmt(c$estimate), " (n ", sgs_py_str(r$n), if (is.finite(c$boot_p %||% NA_real_)) paste0(", p ", sgs_fmt(c$boot_p)) else "", ")")
  }
  range_cell <- function(id, g) {
    r <- rows[[id]]
    if (is.null(r)) return("not in the run")
    if (!identical(r$status, SGS_ESTIMABLE)) return(r$status)
    s <- subfits_of(id, g)
    if (!length(s)) return("n/a")
    e <- vapply(s, function(c) c$estimate, 0)
    paste0(sgs_fmt(min(e)), " to ", sgs_fmt(max(e)), " (", sum(e > 0), " +, ", sum(e < 0), " - of ", length(e), ")")
  }
  L <- c(paste0("L1-LV..L3-LV with the robustness family the core tests have (coordinator's revision of 2026-09-26, after the ",
                "Codex methodology review found the LobbyView tests - the currently estimable growth family - had none). Every ",
                "variant is fitted on the base test's gated sample (the same sector-years), except that first differences use ",
                "the pairs of consecutive years both in it. Estimates in $M 2025 per percentage point of growth (log variants: ",
                "log points); p = wild cluster restricted bootstrap by sector. FDY (first differences with year effects) is ",
                "EXPLORATORY and descriptive: a new, narrower question about changes across successive years, not a test of ",
                "contraction causality; no p-value. STRICT drops the expected-control values measured after their year."), "",
         "| variant | L1-LV (prior-year growth) | L2-LV (same-year growth) | L3-LV (predicted growth) |", "|---|---|---|---|")
  specs <- list(c("base (CORE)", ""), c("R-yearFE (sector + year FE)", "R-yearFE-"), c("R-log (ln DV, base controls)", "R-log-"),
                c("R-logFE (ln DV, sector + year FE)", "R-logFE-"), c("R-FD (first differences, controls differenced)", "R-FD-"),
                c("FDY (first differences + year effects; EXPLORATORY, descriptive)", "FDY-"), c("STRICT (timing)", "STRICT-"))
  for (s in specs) {
    L <- c(L, paste0("| ", s[1], " | ", paste(vapply(c("1", "2", "3"), function(k) {
      base <- paste0("L", k, "-LV")
      cell(paste0(s[2], base), SGS_GROWTH[[k]])
    }, ""), collapse = " | "), " |"))
  }
  for (s in list(c("R-LOSO (leave one sector out): range", "R-LOSO-"), c("R-LOYO (leave one year out): range", "R-LOYO-"),
                 c("FDY-LOSO: range", "FDY-LOSO-"), c("FDY-LOYO: range", "FDY-LOYO-"))) {
    L <- c(L, paste0("| ", s[1], " | ", paste(vapply(c("1", "2", "3"), function(k) range_cell(paste0(s[2], "L", k, "-LV"), SGS_GROWTH[[k]]), ""),
                                          collapse = " | "), " |"))
  }
  L
}

# The review's numbers against this run: MATCH when the relative difference is <= SGS_CODEX_REVIEW_TOL.
SGS_CODEX_CHECK_COLS <- c("test", "quantity", "codex_review", "this_run", "rel_diff", "verdict")
sgs_codex_check <- function(est_rows, coef_rows, holm) {
  rows <- setNames(est_rows, vapply(est_rows, function(r) as.character(r$test_id), ""))
  get <- function(id, g, field = "estimate") {
    x <- Filter(function(c) identical(c$test_id, id) && identical(c$coefficient, g) && is.null(c$left_out), coef_rows)
    if (length(x)) as.numeric(x[[1]][[field]] %||% NA_real_) else NA_real_
  }
  out <- list()
  add <- function(test, q, ref, val) {
    rel <- if (is.finite(ref) && is.finite(val)) abs(val - ref) / max(abs(ref), 1e-12) else NA_real_
    out[[length(out) + 1L]] <<- list(test = test, quantity = q, codex_review = ref, this_run = val, rel_diff = rel,
                                     verdict = if (is.na(rel)) "NOT COMPUTED" else if (rel <= SGS_CODEX_REVIEW_TOL) "MATCH" else "MISMATCH")
  }
  for (id in names(SGS_CODEX_REVIEW)) {
    k <- sub("^L([123])-LV$", "\\1", id); g <- SGS_GROWTH[[k]]; ref <- SGS_CODEX_REVIEW[[id]]
    add(id, "coefficient, original specification", ref[["base"]], get(id, g))
    add(id, "n, original specification", ref[["base_n"]], as.numeric(rows[[id]]$n %||% NA))
    add(id, "coefficient, sector + year fixed effects (R-yearFE)", ref[["yearfe"]], get(paste0("R-yearFE-", id), g))
    add(id, "coefficient, ln DV with sector + year fixed effects (R-logFE)", ref[["logfe"]], get(paste0("R-logFE-", id), g))
    add(id, "coefficient, first differences with year effects (FDY)", ref[["fdy"]], get(paste0("FDY-", id), g))
    add(id, "adjacent pairs, FDY", ref[["fdy_n"]], as.numeric(rows[[paste0("FDY-", id)]]$n %||% NA))
    add(id, "adjusted R^2 with the growth term", ref[["adj_with"]], get(id, g, "adj_r2_with"))
    add(id, "adjusted R^2 without it, same rows", ref[["adj_without"]], get(id, g, "adj_r2_without"))
    add(id, "partial R^2 of the growth term", ref[["partial"]], get(id, g, "partial_r2"))
    add(id, "bootstrap p, original specification", ref[["p"]], get(id, g, "boot_p"))
    hp <- if (!is.null(holm) && nrow(holm)) holm$holm_p[holm$family == "L-LV growth timing" & holm$test_id == id] else numeric(0)
    add(id, "Holm p within L1-LV..L3-LV", ref[["holm"]], if (length(hp)) hp[1] else NA_real_)
  }
  sgs_rows_df(out, SGS_CODEX_CHECK_COLS)
}

sgs_codex_check_md <- function(chk) {
  nm <- sum(chk$verdict == "MATCH"); nx <- sum(chk$verdict == "MISMATCH"); nn <- sum(chk$verdict == "NOT COMPUTED")
  L <- c(paste0("The Codex methodology review (C:/Users/pgoff/Documents/Codex/2026-09-26/loo/outputs, run analysis-R-20260926T070630Z) ",
                "against this run: ", nm, " MATCH, ", nx, " MISMATCH, ", nn, " not computed (relative tolerance ",
                sgs_py_repr_float(SGS_CODEX_REVIEW_TOL), "). The review's diagnostics are post-result checks, not preregistered ",
                "evidence; reproducing them does not make them confirmatory."), "",
         "| test | quantity | Codex review | this run | relative difference | verdict |", "|---|---|---:|---:|---:|---|")
  for (i in seq_len(nrow(chk))) {
    L <- c(L, paste0("| ", chk$test[i], " | ", chk$quantity[i], " | ", sgs_py_repr_float(chk$codex_review[i]), " | ",
                     if (is.finite(chk$this_run[i])) sgs_py_repr_float(chk$this_run[i]) else "n/a", " | ",
                     if (is.finite(chk$rel_diff[i])) formatC(chk$rel_diff[i], format = "e", digits = 2) else "n/a", " | ",
                     chk$verdict[i], " |"))
  }
  L
}

# Expected control: when each value was measured (sheet expected_control_timing, report section).
SGS_TIMING_COLS <- c("year", "chamber", "exp_dem", "method", "measured_at", "available_at", "after_year", "flag", "used_in")
sgs_expected_control_timing <- function(sy) {
  out <- list()
  yrs <- sort(unique(sy$year[sy$year >= SGS$FALLBACK_SEARCH[1]]))
  for (ch in c("House", "Senate")) {
    s <- tolower(ch)
    for (y in yrs) {
      r <- sy[sy$year == y, , drop = FALSE][1, , drop = FALSE]
      v <- r[[paste0("exp_dem_", s)]]
      if (is.null(v) || is.na(v)) next
      ay <- r[[paste0("exp_dem_", s, "_after_year")]] %in% TRUE
      out[[length(out) + 1L]] <- list(
        year = y, chamber = ch, exp_dem = v, method = .txt0(r[[paste0("exp_dem_", s, "_method")]]),
        measured_at = .txt0(r[[paste0("exp_dem_", s, "_measured_at")]]), available_at = .txt0(r[[paste0("exp_dem_", s, "_available_at")]]),
        after_year = ay, flag = .txt0(r[[paste0("exp_dem_", s, "_flag")]]),
        used_in = if (ay) paste0("main series (", SGS$RETRO_LABEL, "); left out of the STRICT variants") else "main series and STRICT variants")
    }
  }
  sgs_rows_df(out, SGS_TIMING_COLS)
}

sgs_chronology_md <- function(timing, est_rows) {
  late <- timing[timing$after_year %in% TRUE, , drop = FALSE]
  st <- Filter(function(r) grepl("-STRICT(-PV)?$", r$test_id) || startsWith(r$test_id, "STRICT-"), est_rows)
  L <- c(paste0("Every expected-control value with the date it was measured (02 data last_price_date for the IEM annual means; ",
                "02 expected_control_2023_2026 measured_on for the fill years); available_at = measured_at. The main series stays ",
                "as Paul ruled and is labelled: ", SGS$RETRO_LABEL, " - an IEM annual mean is a within-year average (a nowcast of ",
                "the year, not information held at its start), and the values below measured after their year are retrospective. ",
                "A final-seat call (2023-2024) is a 0/1 winner call, not a calibrated probability. The STRICT variants leave out ",
                "the values measured after their year."), "",
         paste0("- Measured after their year: ", if (nrow(late)) paste0(late$chamber, " ", late$year, " (", late$method, ", measured ",
                                                                         late$measured_at, ")", collapse = "; ") else "none", "."),
         "", "| year | chamber | exp_dem | method | measured_at | after its year |", "|---:|---|---:|---|---|---|")
  for (i in seq_len(nrow(timing))) {
    x <- timing[i, , drop = FALSE]
    L <- c(L, paste0("| ", sgs_int_str(x$year), " | ", x$chamber, " | ", sgs_fmt(x$exp_dem), " | ", x$method, " | ", x$measured_at,
                     " | ", if (isTRUE(x$after_year)) "yes (retrospective)" else "no", " |"))
  }
  if (length(st)) {
    L <- c(L, "", "STRICT variants in this run:", "", "| test | status | window | n | exclusions (ESTIMABLE) / reason |", "|---|---|---|---:|---|")
    for (r in st) {
      L <- c(L, paste0("| ", r$test_id, " | ", r$status, " | ", .txt0(r$window_used), " | ", sgs_py_str(r$n), " | ",
                       .md_escape(if (identical(r$status, SGS_ESTIMABLE)) .txt0(r$exclusions) else .txt0(r$reason_short)), " |"))
    }
  }
  L
}

# What the money is (coordinator's revision of 2026-09-26, the review's measurement audit): the composition of 04 general
# giving ("included receipts") over the preview years, the party-labelled share, the chamber and conduit shares of 08.
sgs_money_md <- function(wbs, years = SGS$PREVIEW_WINDOW) {
  d <- wbs$spending$frames$data
  if (is.null(d) || !nrow(d)) return(character(0))
  k <- !is.na(d$year) & d$year >= years[1] & d$year <= years[2]
  amt <- suppressWarnings(as.numeric(d$giving_nominal_usd[k]))
  tot <- sum(amt, na.rm = TRUE)
  pct <- function(x) vapply(x, function(v) paste0(sgs_py_fixed(100 * v / tot, 2), "%"), "")
  usd <- function(x) vapply(x, function(v) paste0("$", sgs_py_fixed(v, 0, comma = TRUE)), "")
  by <- function(col) { v <- tapply(amt, as.character(d[[col]][k]), sum, na.rm = TRUE); v[order(-v)] }
  fs <- by("funding_source"); pa <- by("party"); rc <- by("recipient_category")
  L <- c(paste0("The contributions measure (04 general giving, contributions_real_m) is ", SGS$MONEY_LABEL, ". Composition over ",
                years[1], "-", years[2], ", every Mentat unit of 04 (", length(unique(d$study_sector[k])), "), nominal: ", usd(tot), "."), "",
         paste0("- By funding_source: ", paste0(names(fs), " ", usd(fs), " (", vapply(fs, pct, ""), ")", collapse = "; "), "."),
         paste0("- By party: ", paste0(names(pa), " ", usd(pa), " (", vapply(pa, pct, ""), ")", collapse = "; "),
                ". SHIFT-All is D / (D + R) within the party-labelled ", pct(sum(pa[names(pa) %in% c("D", "R")])),
                " of the dollars, not the allocation of all money; its coverage varies by unit (SHIFT section)."),
         paste0("- By recipient_category: ", paste0(names(rc), " ", usd(rc), " (", vapply(rc, pct, ""), ")", collapse = "; "), "."))
  ch <- if (!is.null(wbs$chamber)) wbs$chamber$frames[[SGS$CHAMBER_SHEET]] else NULL
  if (!is.null(ch)) {
    kc <- !is.na(ch$year) & ch$year >= years[1] & ch$year <= years[2]
    cand <- sum(suppressWarnings(as.numeric(ch$dem_usd[kc])), na.rm = TRUE) + sum(suppressWarnings(as.numeric(ch$rep_usd[kc])), na.rm = TRUE) +
      (if ("other_usd" %in% names(ch)) sum(suppressWarnings(as.numeric(ch$other_usd[kc])), na.rm = TRUE) else 0)
    L <- c(L, paste0("- House + Senate candidate committees (08 ", SGS$CHAMBER_SHEET, "): ", usd(cand), " (", pct(cand), ")."))
  }
  orr <- if (!is.null(wbs$chamber)) wbs$chamber$frames$other_recipients else NULL
  if (!is.null(orr) && all(c("of_which_actblue_usd", "of_which_winred_usd") %in% names(orr))) {
    ko <- !is.na(orr$year) & orr$year >= years[1] & orr$year <= years[2]
    cd <- sum(suppressWarnings(as.numeric(orr$of_which_actblue_usd[ko])), na.rm = TRUE) +
      sum(suppressWarnings(as.numeric(orr$of_which_winred_usd[ko])), na.rm = TRUE)
    L <- c(L, paste0("- Receipts of the ActBlue / WinRed conduits (08 other_recipients): ", usd(cd), " (", pct(cd), ")."))
  }
  c(L, paste0("- Conduit overlap (08 notes n6): a gift earmarked through ActBlue or WinRed names the conduit as the recipient; when ",
              "the candidate's own report also carries it, that row is in 04 too, so conduit and candidate receipts can overlap. ",
              "The conduit total is the exposure to that path, not a verified duplicate amount. R-dedup-C1..C3 exclude own-PAC ",
              "receipts only (renamed 'excluding own-PAC receipts'): that is not transaction-level de-duplication and does not ",
              "resolve the conduit path."))
}
