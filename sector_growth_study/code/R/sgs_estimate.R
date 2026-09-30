# OLS with sector baselines, HC1 errors (reference only), wild cluster restricted bootstrap by sector, strata
# (R port of code/sgs/estimate.py; base R qr / crossprod only).
#
# Inference for every focal coefficient: wild cluster restricted (WCR) bootstrap-t with Webb six-point weights,
# clusters = sectors, CR1 cluster-robust standard error in the t statistic. The null beta_k = beta0 is imposed on the
# bootstrap DGP; all 6^G weight vectors are enumerated when 6^G <= B (9,999), else B draws of the seeded numpy stream
# (sgs_rng.R reproduces numpy's SeedSequence + PCG64 + Generator.choice exactly). p-value: share of bootstrap
# |t*| >= |t| (symmetric, two-sided). The 95% CI is the set of beta0 not rejected at 5%, found by test inversion.
# Bootstrap statistics are linear-fractional in beta0, so each p(beta0) evaluation reuses the same draws in O(B)
# (the algebra of Roodman, MacKinnon, Nielsen and Webb 2019, "fast and wild"). With enumeration the draws w = +1 and
# w = -1 reproduce |t| exactly, so p >= 2 / 6^G; with G = 2 no value can be rejected at 5% and the interval is
# unbounded. DESCRIPTIVE tests report the estimate and the HC1 error only. Fixed effects nested within clusters (H5
# champion fixed effects) are left out of the CR1 small-sample factor's parameter count.

SGS_WCR_MAX_STEP_EXP <- 20

# QR without column pivoting (numpy.linalg.qr): R's LINPACK Householder QR with tol = 0 never pivots.
.qr_nopivot <- function(X) qr(X, tol = 0, LAPACK = FALSE)

sgs_cr1_factor <- function(G, n, p, nested_fe = 0) G / (G - 1) * (n - 1) / (n - (p - nested_fe))

sgs_ols <- function(design) {
  X <- design$X; y <- design$y
  n <- nrow(X); p <- ncol(X)
  q <- .qr_nopivot(X)
  R <- qr.R(q)
  Q <- qr.Q(q)
  beta <- as.vector(backsolve(R, crossprod(Q, y)))
  Rinv <- backsolve(R, diag(p))
  A <- Rinv %*% t(Rinv)
  u <- as.vector(y - X %*% beta)
  df <- n - p
  Xu <- X * u
  if (df > 0) {
    V_hc1 <- (n / df) * A %*% crossprod(Xu) %*% A
    se_hc1 <- unname(sqrt(pmax(diag(V_hc1), 0)))
  } else {
    se_hc1 <- rep(NaN, p)
  }
  G <- if (n) as.integer(max(design$clusters)) + 1L else 0L
  if (G > 1 && df > 0) {
    S <- rowsum(Xu, design$clusters, reorder = TRUE)
    cfac <- sgs_cr1_factor(G, n, p, design$nested_fe %||% 0)
    V_cr1 <- cfac * A %*% crossprod(S) %*% A
    se_cr1 <- unname(sqrt(pmax(diag(V_cr1), 0)))
  } else {
    se_cr1 <- rep(NaN, p)
  }
  list(names = design$names, beta = beta, resid = u, A = A, n = n, p = p, G = G, se_hc1 = se_hc1, se_cr1 = se_cr1)
}

sgs_fit_coef <- function(fit, name) fit$beta[match(name, fit$names)]

# Wild cluster restricted bootstrap for coefficient k (1-based) of a design: returns an object with tstat, tstar,
# pvalue and ci closures.
sgs_wcr <- function(design, fit, k, B, entropy) {
  X <- design$X; y <- design$y; cl <- design$clusters
  n <- nrow(X); p <- ncol(X); G <- fit$G
  bk <- fit$beta[k]
  A <- fit$A
  q <- as.vector(X %*% A[, k])
  xk <- X[, k]
  Xmk <- X[, -k, drop = FALSE]
  if (ncol(Xmk)) {
    Qm <- qr.Q(.qr_nopivot(Xmk))
    r0 <- as.vector(y - Qm %*% crossprod(Qm, y))
    r1 <- as.vector(xk - Qm %*% crossprod(Qm, xk))
  } else {
    r0 <- as.numeric(y); r1 <- as.numeric(xk)
  }
  Qg <- rowsum(X * q, cl, reorder = TRUE)
  QA <- Qg %*% A
  parts <- function(u) {
    a <- as.vector(rowsum(q * u, cl, reorder = TRUE))
    S <- rowsum(X * u, cl, reorder = TRUE)
    list(a = a, C = diag(a, G) - QA %*% t(S))
  }
  P0 <- parts(r0); P1 <- parts(r1)
  cfac <- sgs_cr1_factor(G, n, p, design$nested_fe %||% 0)
  s <- as.vector(rowsum(q * fit$resid, cl, reorder = TRUE))
  se <- sqrt(cfac * sum(s^2))
  dr <- sgs_webb_draws(G, B, entropy)
  V <- dr$V
  N0 <- as.vector(V %*% P0$a); N1 <- as.vector(V %*% P1$a)
  D0 <- V %*% t(P0$C); D1 <- V %*% t(P1$C)
  s00 <- rowSums(D0 * D0); s01 <- rowSums(D0 * D1); s11 <- rowSums(D1 * D1)
  tstat <- function(b0) (bk - b0) / se
  tstar <- function(b0) {
    num <- N0 - b0 * N1
    den2 <- pmax(cfac * (s00 - 2.0 * b0 * s01 + b0 * b0 * s11), 0.0)
    num / sqrt(den2)
  }
  pvalue <- function(b0 = 0.0) {
    t <- abs(tstat(b0))
    ats <- abs(tstar(b0))
    ats[is.nan(ats)] <- Inf  # 0/0 draws count as extreme (conservative)
    mean(ats >= t * (1.0 - 1e-9))
  }
  ci <- function(alpha = SGS$ALPHA) {
    step <- if (is.finite(se) && se > 0) se else max(abs(bk), 1.0)
    bound <- function(direction) {
      inside <- bk; outside <- NULL
      for (e in -3:SGS_WCR_MAX_STEP_EXP) {
        x <- bk + direction * step * (2.0^e)
        if (pvalue(x) < alpha) { outside <- x; break }
        inside <- x
      }
      if (is.null(outside)) return(direction * Inf)
      for (i in 1:200) {
        mid <- 0.5 * (inside + outside)
        if (pvalue(mid) < alpha) outside <- mid else inside <- mid
        if (abs(outside - inside) <= 1e-7 * step) break
      }
      0.5 * (inside + outside)
    }
    c(bound(-1.0), bound(1.0))
  }
  list(G = G, k = k, bk = bk, se = se, c = cfac, draws = nrow(V), enumerated = dr$enumerated, V = V,
       tstat = tstat, tstar = tstar, pvalue = pvalue, ci = ci)
}

.dv_unit <- function(spec) {
  du <- spec$dv_unit %||% NA_character_
  if (length(du) == 1L && !is.na(du)) return(du)             # SEATS: the DV states its own unit
  if (identical(spec$variant, "log")) return("log points")
  if (startsWith(spec$dv, "dem_share")) return("Democratic share (0-1)")
  "$M 2025"
}

sgs_unit_of <- function(coef, spec) {
  dv_u <- .dv_unit(spec)
  # rulings of 2026-09-26: ASYM / DECEL / telecom-component / SLOPES / bank-split coefficient names
  gv <- "(growth_previous_year_pct|growth_same_year_pct|predicted_growth_pct)"
  pp <- paste0(dv_u, " per percentage point of growth")
  if (grepl(paste0("^", gv, "_neg - ", gv, "_pos$"), coef)) {
    return(paste0("difference of the two slopes (decline years minus growth years), ", pp))
  }
  if (identical(coef, "contracted_prior")) {
    return(paste0(dv_u, ", year after the industry contracted (prior-year growth < 0) vs not"))
  }
  if (startsWith(coef, "contracted_prior:")) {
    return(paste0(dv_u, ", year after the industry contracted (prior-year growth < 0) vs not, ",
                  sub("^contracted_prior:", "", coef), " only"))
  }
  ms <- regmatches(coef, regexec(paste0("^", gv, "_(pos|neg):(.+)$"), coef))[[1]]
  if (length(ms)) {
    return(paste0(pp, if (ms[3] == "pos") ", growth years (g >= 0), " else ", decline years (g < 0), ", ms[4], " only"))
  }
  m <- regmatches(coef, regexec(paste0("^", gv, "_(pos|neg|decel|x_decel|tw|tc)$"), coef))[[1]]
  if (length(m)) {
    return(switch(m[3],
                  pos = paste0(pp, ", growth years (g >= 0)"),
                  neg = paste0(pp, ", decline years (g < 0)"),
                  decel = paste0(dv_u, ", year in which growth fell from the prior year (g_t < g_{t-1}) vs not"),
                  x_decel = paste0("difference in the slope in years when growth fell from the prior year, ", pp),
                  tw = paste0(pp, " (telecom: wireless component only)"),
                  tc = paste0(pp, " (telecom: cable component only)")))
  }
  if (grepl(paste0("^", gv, ":"), coef)) {
    other <- sub(paste0("^", gv, ":"), "", coef)
    if (identical(other, SGS$BANK_SPLIT_COMMUNITY)) {
      return(paste0("difference of the community-bank slope from the big-bank slope, ", pp))
    }
    if (!other %in% SGS$TIERS) return(paste0(pp, ", ", other, " only"))
  }
  base <- strsplit(coef, ":", fixed = TRUE)[[1]][1]
  if (base %in% c("growth_previous_year_pct", "growth_same_year_pct", "predicted_growth_pct")) {
    if (grepl(":", coef, fixed = TRUE)) return(paste0("difference from the Employee slope, ", dv_u, " per percentage point of growth"))
    return(paste0(dv_u, " per percentage point of growth"))
  }
  u <- c(
    pres_year = paste0(dv_u, ", presidential-election year vs odd year"),
    midterm_year = paste0(dv_u, ", midterm year vs odd year"),
    exp_dem_house = paste0(dv_u, " per unit (0-1) of expected Democratic House control"),
    exp_dem_senate = paste0(dv_u, " per unit (0-1) of expected Democratic Senate control"),
    exp_dem_own_chamber = paste0(dv_u, " per unit (0-1) of expected Democratic control of the recipient's own chamber"),
    cur_dem_own_chamber = paste0(dv_u, ", Democratic vs Republican control of the recipient's own chamber"),
    exp_shift_house = paste0(dv_u, " per unit of expected-minus-current Democratic House control"),
    exp_shift_senate = paste0(dv_u, " per unit of expected-minus-current Democratic Senate control"),
    cur_dem_house = paste0(dv_u, ", Democratic vs Republican House"),
    cur_dem_senate = paste0(dv_u, ", Democratic vs Republican Senate"),
    pred_dem_seat_change_house = paste0(dv_u, " per predicted Democratic House seat gained"),
    pred_dem_seat_change_senate = paste0(dv_u, " per predicted Democratic Senate seat gained"),
    gb538_margin_house = paste0(dv_u, " per point of the 538 House generic-ballot margin (D minus R)"),
    predicted_growth_multiyear_pct = paste0(dv_u, " per percentage point of projected multi-year growth (CAGR)"),
    seat_net_gain = paste0(dv_u, " per forecast Democratic seat gained (the chamber's final Crystal Ball call)"),
    seat_net_gain_538 = paste0(dv_u, " per forecast Democratic seat gained (538 Lite expected seats)"),
    seat_net_gain_change = paste0(dv_u, " per seat of change in the forecast Democratic gain from the previous cycle")
  )
  if (coef %in% names(u)) return(unname(u[coef]))
  paste0(dv_u, " per unit of ", coef)
}

sgs_boot_coefficient <- function(design, fit, name, B, entropy, alpha = SGS$ALPHA) {
  k <- match(name, fit$names)
  out <- list(coefficient = name, estimate = fit$beta[k], hc1_se = fit$se_hc1[k], cr1_se = fit$se_cr1[k])
  if (fit$G < 2 || !is.finite(fit$se_cr1[k]) || fit$se_cr1[k] <= 0) {
    out <- c(out, list(boot_p = NaN, ci_low = NaN, ci_high = NaN, boot_draws = 0, boot_enumerated = NA,
                       boot_note = "bootstrap not computable (fewer than 2 clusters or zero cluster-robust variance)"))
    return(out)
  }
  w <- sgs_wcr(design, fit, k, B, entropy)
  ci <- w$ci(alpha)
  out <- c(out, list(t_cr1 = w$tstat(0.0), boot_p = w$pvalue(0.0), ci_low = ci[1], ci_high = ci[2], boot_draws = w$draws,
                     boot_enumerated = w$enumerated, boot_note = ""))
  if (!is.finite(ci[1]) || !is.finite(ci[2])) {
    if (w$enumerated && 2 / w$draws >= alpha) {
      out$boot_note <- paste0("interval unbounded: with G=", fit$G, " clusters the smallest attainable p is ",
                              sgs_py_fixed(2 / w$draws, 4), " >= ", sgs_py_repr_float(alpha), ", so no value can be rejected")
    } else {
      out$boot_note <- paste0("interval unbounded on at least one side (no rejection within 2^", SGS_WCR_MAX_STEP_EXP,
                              " cluster-robust standard errors)")
    }
  }
  out
}

sgs_fit_strata <- function(sample_df, spec, coef_names) {
  rows <- list()
  for (s in sgs_sort_sectors(sample_df$study_sector)) {
    sub <- sample_df[sample_df$study_sector == s, , drop = FALSE]
    d <- sgs_weighted_design(sgs_build_design(sub, spec))  # weighted variants: the unit's own weighted regression
    r <- sgs_rank_of(d$X)
    n <- nrow(d$X); p <- ncol(d$X)
    base <- list(study_sector = s, n = n, years = sgs_years_text(sub$year), resid_df = n - p)
    if (r < p) {
      for (c in coef_names) rows[[length(rows) + 1L]] <- c(base, list(coefficient = c, status = "insufficient",
                                                                        reason = paste0("rank ", r, " < ", p, " parameters within the sector")))
      next
    }
    if (n - p < SGS$MIN_STRATUM_RESID_DF) {
      for (c in coef_names) rows[[length(rows) + 1L]] <- c(base, list(coefficient = c, status = "insufficient",
                                                                        reason = paste0("residual df ", n - p, " < ", SGS$MIN_STRATUM_RESID_DF)))
      next
    }
    f <- sgs_ols(d)
    for (c in coef_names) {
      if (c %in% f$names) {
        k <- match(c, f$names)
        rows[[length(rows) + 1L]] <- c(base, list(coefficient = c, status = "estimated", estimate = f$beta[k],
                                                  hc1_se = f$se_hc1[k], reason = ""))
      } else {
        rows[[length(rows) + 1L]] <- c(base, list(coefficient = c, status = "insufficient", reason = "term absent in sector"))
      }
    }
  }
  rows
}

sgs_stratification_label <- function(strata_rows, coef, unit_word = "sectors", unit_one = "sector") {
  rel <- Filter(function(r) identical(r$coefficient, coef), strata_rows)
  est <- Filter(function(r) identical(r$status, "estimated"), rel)
  if (length(est)) return(paste0("STRATIFIED: ", length(est), " of ", length(rel), " ", unit_word, " estimated"))
  if (!length(rel)) return("UNSTRATIFIED: no strata computed")
  paste0("UNSTRATIFIED: no ", unit_one, " has a ", unit_one, "-only estimate (", rel[[1]]$reason, ")")
}

sgs_descriptive_note <- function(G) {
  paste0(G, " sectors: wild cluster bootstrap cannot reach p < ", sgs_py_fixed(2 / 6^G, 3), "; inference not available")
}

sgs_descriptive_coefficient <- function(fit, name, note = sgs_descriptive_note(fit$G)) {
  k <- match(name, fit$names)
  list(coefficient = name, estimate = fit$beta[k], hc1_se = fit$se_hc1[k], cr1_se = NaN, t_cr1 = NaN, boot_p = NaN,
       ci_low = NaN, ci_high = NaN, boot_draws = 0, boot_enumerated = NA, boot_note = note,
       inference = "none (DESCRIPTIVE): estimate and HC1 error (reference only)")
}

# A test without inference by design (inference = "none") that has enough clusters for the bootstrap: the EXPLORATORY
# first differences with year effects of the Codex review (no confirmatory p-value); fewer clusters keep the G note.
SGS_NO_INFERENCE_NOTE <- paste0("EXPLORATORY, no inference by design (coordinator's revision of 2026-09-26 after the Codex ",
                                "methodology review: a post-result check; no confirmatory p-value)")
# SEATS-A: the forecast varies only by election cycle, so the sector count is not the reason (with 8 sectors the G note
# would print "cannot reach p < 0.000"); the independent units are the cycles.
SGS_SEATS_A_NO_INFERENCE_NOTE <- paste0("DESCRIPTIVE by design: the forecast varies only by election cycle (independent forecasts = ",
                                        "cycles, not sectors x cycles); no inference")
sgs_no_inference_note <- function(spec, G) {
  if (identical(spec$family, "SEATS-A")) return(SGS_SEATS_A_NO_INFERENCE_NOTE)
  if (identical(spec$inference, "none") && !is.na(G) && G >= 3 && isTRUE(spec$matched)) SGS_NO_INFERENCE_NOTE else sgs_descriptive_note(G)
}

# Is the test estimated DESCRIPTIVE (no inference)? The parity DESCRIPTIVE tests always; under Paul's rulings the
# LobbyView tests when they have fewer than min_clusters_inference sector clusters.
sgs_is_descriptive <- function(spec, G) {
  identical(spec$inference, "none") || (!is.na(spec$min_clusters_inference) && G < spec$min_clusters_inference)
}

# Focal coefficient names of a fitted design: the per-sector terms of a per-sector design (SLOPES, CONTRACT-b,
# ASYM-SLOPES: <var>:<sector> for every focal variable), else the spec's focal terms.
sgs_focal_names <- function(spec, fit_names) {
  if (identical(spec$variant, "slopes")) {
    hit <- Reduce(`|`, lapply(spec$focal, function(v) startsWith(fit_names, paste0(v, ":"))))
    return(fit_names[hit])
  }
  spec$focal
}

# ASYM (rulings of 2026-09-26): the equality test of two focal slopes a and b. The model is reparametrised with a + b in
# place of a, so the coefficient of b becomes beta_b - beta_a, and the study's wild cluster restricted bootstrap tests it
# = 0 (the restricted model is the model with one common slope); its interval is the interval of the difference.
sgs_equality_row <- function(spec, design, a, b, B, seed, alpha, descriptive = FALSE) {
  ia <- match(a, design$names); ib <- match(b, design$names)
  if (anyNA(c(ia, ib))) return(NULL)
  d2 <- design
  d2$X[, ia] <- design$X[, ia] + design$X[, ib]
  d2$names[ia] <- paste0(a, " + ", b)
  colnames(d2$X) <- d2$names
  fit2 <- sgs_ols(d2)
  nm <- paste0(b, " - ", a)
  row <- if (descriptive) sgs_descriptive_coefficient(fit2, b) else
    sgs_boot_coefficient(d2, fit2, b, B, sgs_seed_entropy(seed, spec$id, nm), alpha)
  row$coefficient <- nm
  c(row, list(unit = sgs_unit_of(nm, spec), focal = TRUE, test = "equality",
              inference = if (descriptive) "none (DESCRIPTIVE): estimate and HC1 error (reference only)" else
                paste0("wild cluster restricted bootstrap test of ", a, " = ", b, " by sector (restricted model: one common slope)"),
              stratification = "n/a (difference of two slopes of the pooled model)"))
}

# Joint tests of per-sector designs (rulings of 2026-09-26). kind "equal": every per-sector term of `cols` is equal
# (restricted model: one common term, the sum of the columns); kind "zero": every one is zero (restricted model: the
# columns left out). F statistic of the restricted model against the unrestricted one, and its wild cluster restricted
# bootstrap by sector: y* = X_r b_r + u_r * v_g (Webb weights, all 6^G enumerated when 6^G <= B). The fitted part
# lies in both column spaces, so each draw's residual sums of squares are those of u_r * v_g. p = share of F* >= F.
# The classical F p-value is returned for reference.
sgs_joint_test <- function(design, cols, kind, B, entropy) {
  X <- design$X; y <- design$y; cl <- design$clusters
  S <- match(cols, design$names)
  Xr <- if (identical(kind, "equal")) cbind(rowSums(X[, S, drop = FALSE]), X[, -S, drop = FALSE]) else X[, -S, drop = FALSE]
  Qu <- qr.Q(.qr_nopivot(X)); Qr <- qr.Q(.qr_nopivot(Xr))
  res_of <- function(Q, V) V - Q %*% crossprod(Q, V)
  ur <- as.vector(res_of(Qr, y)); uu <- as.vector(res_of(Qu, y))
  n <- nrow(X); pu <- ncol(X); q <- length(S) - if (identical(kind, "equal")) 1L else 0L
  dfu <- n - pu
  Fs <- ((sum(ur^2) - sum(uu^2)) / q) / (sum(uu^2) / dfu)
  G <- as.integer(max(cl)) + 1L
  dr <- sgs_webb_draws(G, B, entropy)
  E <- ur * t(dr$V[, cl + 1L, drop = FALSE])  # n x draws
  rr <- colSums(res_of(Qr, E)^2); ru <- colSums(res_of(Qu, E)^2)
  Fb <- ((rr - ru) / q) / (ru / dfu)
  Fb[is.nan(Fb)] <- Inf
  list(F = Fs, q = q, df = dfu, p = mean(Fb >= Fs * (1 - 1e-9)), draws = nrow(dr$V), enumerated = dr$enumerated,
       p_classical = stats::pf(Fs, q, dfu, lower.tail = FALSE), G = G)
}

# One joint-test row. j = list(kind = "equal" | "zero", var, label, key): label names the terms ("slopes" keeps the
# SLOPES wording "joint: all k slopes equal"), key the bootstrap seed stream.
sgs_joint_row <- function(spec, design, cols, j, B, seed) {
  label <- j$label %||% paste0(j$var, " terms")
  key <- j$key %||% paste0("joint: ", j$kind, " ", j$var)
  jt <- sgs_joint_test(design, cols, j$kind, B, sgs_seed_entropy(seed, spec$id, key))
  restricted <- if (identical(j$kind, "equal")) paste0("one common ", j$var, " term") else paste0("no ", j$var, " term")
  list(coefficient = paste0("joint: all ", length(cols), " ", label, " ", j$kind), estimate = jt$F, hc1_se = NA_real_,
       cr1_se = NA_real_, t_cr1 = NA_real_, boot_p = jt$p, ci_low = NA_real_, ci_high = NA_real_, boot_draws = jt$draws,
       boot_enumerated = jt$enumerated,
       boot_note = paste0("F(", jt$q, ", ", jt$df, ") = ", sgs_fmt(jt$F), "; classical F p = ", sgs_fmt(jt$p_classical),
                          " (reference only); wild cluster restricted bootstrap by sector, ", jt$G, " clusters"),
       unit = paste0("F statistic on (", jt$q, ", ", jt$df, ") degrees of freedom"), focal = TRUE, test = "joint",
       joint_kind = j$kind, joint_var = j$var, joint_q = jt$q, joint_df = jt$df, joint_p_classical = jt$p_classical,
       inference = paste0("wild cluster restricted bootstrap F test by sector (restricted model: ",
                          if (identical(label, "slopes")) "one common growth slope" else restricted, ")"),
       stratification = "n/a (joint test)")
}

sgs_estimate <- function(spec, attempt, B = SGS$BOOT_B, seed = SGS$SEED, alpha = SGS$ALPHA, extra_coefs = character(0)) {
  res <- list(coefs = list(), strata = list(), subfits = list(), notes = character(0), descriptive = FALSE)
  smp <- attempt$sample; design <- sgs_weighted_design(attempt$design)
  if (spec$variant %in% c("loso", "loyo")) return(sgs_leave_one_out(spec, attempt, B, seed, alpha))
  fit <- sgs_ols(design)
  focal <- sgs_focal_names(spec, fit$names)
  if (isTRUE(spec$identification)) res$identification <- sgs_shift_identification(spec, attempt$design, fit, focal, design)
  slopes <- identical(spec$variant, "slopes")
  strata_of <- function(nm) {
    if (!slopes) return(sgs_fit_strata(smp$df, spec, nm))
    # SLOPES: the stratum of sector s answers the slope of sector s (the sector's own regression on the common growth
    # variable); national extras keep their per-sector strata
    lspec <- spec; lspec$variant <- "level"
    st <- sgs_fit_strata(smp$df, lspec, c(spec$focal, setdiff(nm, focal)))
    out <- list()
    for (s in st) {
      if (s$coefficient %in% spec$focal) s$coefficient <- paste0(s$coefficient, ":", s$study_sector)
      out[[length(out) + 1L]] <- s
    }
    out
  }
  # year effects leave no within-sector variation in a sector-only regression (R-yearFE; the L-LV year-effect variants)
  year_effects <- identical(spec$variant, "year_fe") || any(c("year", "year_full") %in% spec$fe)
  no_strata <- function(nm) {
    out <- list()
    for (s in sgs_sample_sectors(smp)) for (c in nm) {
      out[[length(out) + 1L]] <- list(
        study_sector = s, coefficient = c, status = "insufficient", n = NA, years = "", resid_df = NA,
        reason = "year fixed effects leave no within-sector variation in a sector-only regression")
    }
    out
  }
  if (sgs_is_descriptive(spec, fit$G)) {
    nm <- focal
    res$strata <- if (year_effects && !identical(spec$variant, "year_fe")) no_strata(nm) else strata_of(nm)
    for (c in nm) {
      row <- sgs_descriptive_coefficient(fit, c, note = sgs_no_inference_note(spec, fit$G))
      row <- c(row, list(unit = sgs_unit_of(c, spec), focal = TRUE, stratification = sgs_stratification_label(res$strata, c)))
      res$coefs[[length(res$coefs) + 1L]] <- row
    }
    if (length(spec$equality) == 2L) {
      eq <- sgs_equality_row(spec, design, spec$equality[1], spec$equality[2], B, seed, alpha, descriptive = TRUE)
      if (!is.null(eq)) res$coefs[[length(res$coefs) + 1L]] <- eq
    }
    res$notes <- c(res$notes, sgs_no_inference_note(spec, fit$G))
    res$descriptive <- TRUE
    return(res)
  }
  nm <- c(focal, extra_coefs[extra_coefs %in% fit$names & !extra_coefs %in% focal])
  if (!year_effects) {
    res$strata <- strata_of(nm)
  } else {
    res$strata <- no_strata(nm)
  }
  by <- if (spec$table %in% c("industry_year", SGS_SHIFT_TABLES, SGS_SEATS_TABLES)) "Mentat industry" else "sector"
  for (c in nm) {
    row <- sgs_boot_coefficient(design, fit, c, B, sgs_seed_entropy(seed, spec$id, c), alpha)
    row <- c(row, list(unit = sgs_unit_of(c, spec), focal = c %in% focal,
                       inference = paste0("wild cluster restricted bootstrap by ", by),
                       stratification = sgs_stratification_label(res$strata, c)))
    res$coefs[[length(res$coefs) + 1L]] <- row
  }
  if (length(spec$equality) == 2L) {
    eq <- sgs_equality_row(spec, design, spec$equality[1], spec$equality[2], B, seed, alpha)
    if (!is.null(eq)) res$coefs[[length(res$coefs) + 1L]] <- eq
  }
  if (slopes) {
    for (j in spec$joint %||% list()) {
      cols <- focal[startsWith(focal, paste0(j$var, ":"))]
      if (length(cols) >= (if (identical(j$kind, "equal")) 2L else 1L)) {
        res$coefs[[length(res$coefs) + 1L]] <- sgs_joint_row(spec, design, cols, j, B, seed)
      }
    }
  }
  res
}

# SHIFT (rulings of 2026-09-26): how a year-level focal term is identified. The cells are the distinct years (year x
# chamber in the stacked table). The cell-level design holds the levels the baselines span (common level; chamber
# level) and every regressor constant within cells: K parameters (its rank) on T cells, T - K cell-level residual df.
# 0 df = SATURATED: as many year-level parameters as cells (equivalent to year fixed effects), so the estimate is a fixed
# contrast of the cells and no year-level residual variation tests the model. The OLS weight of a cell on the estimate b
# of a focal term = the sum over the cell's rows of w_i in b = sum_i w_i y_i (w = the focal row of (X'X)^-1 X'; in a
# weighted fit times sqrt(weight), so that the y_i are the unweighted shares). design = the unweighted design (cells),
# design_fit = the design the fit used (weighted or not).
sgs_shift_identification <- function(spec, design, fit, focal, design_fit = design) {
  empty <- list(text = character(0), short = character(0), saturated = NA, cells = 0L, K = NA_integer_, df = NA_integer_,
                weights = list())
  if (is.null(design$cells) || !nrow(design$X)) return(empty)
  cm <- sgs_cell_level_matrix(design)
  K <- sgs_rank_of(cm$Z); Tn <- length(cm$cells); df <- Tn - K
  stacked <- any(grepl(" ", cm$cells, fixed = TRUE))
  word <- if (stacked) "year x chamber cells" else "years"
  one <- if (stacked) "cell" else "year"
  sat <- df == 0
  sw <- if (isTRUE(design_fit$weighted)) sqrt(design_fit$w) else rep(1, nrow(design_fit$X))
  ww <- fit$A %*% t(design_fit$X)
  out <- character(0); short <- character(0); wl <- list()
  cell_txt <- if (stacked) paste(cm$cells, collapse = ", ") else sgs_years_text(as.numeric(cm$cells))
  for (f in focal) {
    k <- match(f, fit$names)
    if (is.na(k)) next
    a <- as.vector(ww[k, ]) * sw
    wc <- tapply(a, design$cells, sum)[cm$cells]
    wc[abs(wc) <= 1e-9 * max(abs(wc), 1e-300)] <- 0
    wl[[f]] <- setNames(as.numeric(wc), cm$cells)
    wtxt <- paste0(cm$cells, " ", ifelse(wc > 0, "+", ifelse(wc < 0, "-", "")),
                   vapply(abs(as.numeric(wc)), function(x) if (x == 0) "0" else sgs_fmt(x), ""), collapse = "; ")
    nz <- which(wc != 0)
    out <- c(out, paste0(
      f, " varies only by ", if (stacked) "year and chamber" else "year", ", so it is identified from the ", Tn, " ", word, " (",
      cell_txt, "), not from the ", nrow(design$X), " rows: ", if (stacked) "cell" else "year", "-level design of ", length(cm$names),
      " parameters (", paste(cm$names, collapse = ", "), "), rank ", K, ", ", if (stacked) "cell" else "year", "-level residual df ", df,
      if (sat) paste0(" - SATURATED: as many year-level parameters as ", word, " (equivalent to ", if (stacked) "year x chamber" else "year",
                      " fixed effects), so the estimate is the fixed contrast of the ", word, " with non-zero weight below, no ",
                      "year-level residual variation tests the model, and its bootstrap reflects variation across units only") else "",
      ". OLS weight of each ", one, " on the estimate (the sum over its rows of w_i in b = sum_i w_i y_i): ", wtxt, "."))
    short <- c(short, paste0(if (sat) "SATURATED (0 year-level df): the contrast " else paste0(df, " ", one, "-level residual df; weights "),
                             paste0(cm$cells[nz], " ", ifelse(wc[nz] > 0, "+", "-"), vapply(abs(as.numeric(wc[nz])), sgs_fmt, ""), collapse = ", ")))
  }
  names(short) <- focal[focal %in% fit$names]
  list(text = out, short = short, saturated = sat, cells = Tn, K = K, df = df, weights = wl)
}

sgs_leave_one_out <- function(spec, attempt, B, seed, alpha) {
  res <- list(coefs = list(), strata = list(), subfits = list(), notes = character(0), descriptive = FALSE)
  lspec <- spec; lspec$variant <- "level"
  df <- attempt$sample$df
  loso <- identical(spec$variant, "loso")
  col <- if (loso) "study_sector" else "year"
  units <- if (loso) sgs_sample_sectors(attempt$sample) else sgs_sample_years(attempt$sample)
  for (u in units) {
    sub <- df[df[[col]] != u, , drop = FALSE]
    yrs <- sort(unique(sub$year))
    secs <- unique(sub$study_sector)
    ustr <- if (loso) u else sgs_int_str(u)
    info <- list(left_out = ustr, n = nrow(sub), n_sectors = length(secs), n_years = length(yrs), years = sgs_years_text(yrs))
    why <- character(0)
    if (length(secs) < SGS$MIN_SECTORS) why <- c(why, paste0(length(secs), " sector(s) left"))
    d <- if (nrow(sub)) sgs_build_design(sub, lspec) else NULL
    if (!is.null(d)) {
      yl <- sgs_year_level_check(d)
      fr <- sgs_full_rank_check(d)
      if (!yl$ok) why <- c(why, yl$why)
      if (!fr$ok) why <- c(why, fr$why)
      if (nrow(d$X) - fr$rank < SGS$MIN_RESID_DF) why <- c(why, paste0("residual df ", nrow(d$X) - fr$rank, " < ", SGS$MIN_RESID_DF))
    } else {
      why <- c(why, "empty")
    }
    flag <- ""
    if (length(yrs) < attempt$min_years) {
      flag <- paste0("diagnostic: ", length(yrs), " years < the ", attempt$min_years, "-year minimum of the gated window")
    }
    if (length(why)) {
      for (c in spec$focal) res$subfits[[length(res$subfits) + 1L]] <- c(info, list(
        coefficient = c, status = "not estimable", reason = paste(why, collapse = "; "), flag = flag))
      next
    }
    fit <- sgs_ols(d)
    for (c in spec$focal) {
      # a leave-one-out test without inference (the EXPLORATORY first differences with year effects) reports the
      # estimate and HC1 error of each sub-fit only
      row <- if (identical(spec$inference, "none")) sgs_descriptive_coefficient(fit, c, note = sgs_no_inference_note(spec, fit$G)) else
        sgs_boot_coefficient(d, fit, c, B, sgs_seed_entropy(seed, spec$id, c, ustr), alpha)
      row <- c(row, info, list(status = "estimated", reason = "", flag = flag, unit = sgs_unit_of(c, lspec),
                               stratification = "UNSTRATIFIED: leave-one-out sub-fit"))
      res$subfits[[length(res$subfits) + 1L]] <- row
    }
  }
  res
}
