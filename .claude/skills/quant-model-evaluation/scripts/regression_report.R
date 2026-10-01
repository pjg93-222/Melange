#!/usr/bin/env Rscript
# regression_report.R -- quant-model-evaluation 1.0.0
#
# The regression presentation contract. Prints, in this order:
#   1. the real print(summary(lm(...))), verbatim
#   2. "=== Inference block: <vcov> (G = <clusters>, <bootstrap desc>) ===": estimate, SE, t, p and CI per
#      term under the chosen robust covariance, plus wild-bootstrap p and CI when the bootstrap runs
#   3. "=== Diagnostics ===": N vs G, few-cluster warning, collinearity, VIF, RESET, Breusch-Pagan,
#      Cook's distance, residual autocorrelation (--time), per-stratum signs (--strata)
#   4. one "Trend: " line (sign, size, consistency across strata, then uncertainty)
# Read-only: reads --data; writes only report.md and report.json in a fresh run folder under --out.
# Run with --help for every option and the verdict rules.
#
# Formula sources (hand-built paths; sandwich/lmtest are used instead when installed, and the report says so):
#   HC1/HC3: White (1980) Econometrica 48(4):817-838; MacKinnon & White (1985) J. Econometrics 29(3):305-325.
#   CR1: Liang & Zeger (1986) Biometrika 73(1):13-22, with the small-sample factor G/(G-1)*(N-1)/(N-K)
#        (Stata's; Cameron, Gelbach & Miller 2008, REStat 90(3):414-427, doi:10.1162/rest.90.3.414).
#   Two-way CR1: V1 + V2 - V12, Cameron, Gelbach & Miller (2011) JBES 29(2):238-249, doi:10.1198/jbes.2010.07136.
#   CR2 (Bell & McCaffrey 2002, Survey Methodology 28(2):169-181; UNVERIFIED in CrossRef/OpenAlex as of 2026-09-30):
#        only via sandwich::vcovCL(type = "HC2"); with its default cadjust this equals the (I - H_gg)^(-1/2) CR2
#        computed by hand (checked 2026-09-30, sandwich 3.1.3).
#   Newey-West, Bartlett weights 1 - l/(L+1): Newey & West (1987) Econometrica 55(3):703, doi:10.2307/1913610;
#        default lag floor(4*(N/100)^(2/9)): Newey & West (1994) REStud 61(4):631-653.
#   Wild cluster restricted (WCR) bootstrap: Cameron, Gelbach & Miller (2008); the closed-form algebra and the
#        test-inversion CI follow Roodman, Nielsen, MacKinnon & Webb (2019) Stata Journal 19(1):4-60; Webb
#        six-point weights for G <= 11: Webb (2023) Canadian J. Economics 56(3):839-858; practice guide:
#        MacKinnon, Nielsen & Webb (2023) J. Econometrics 232(2):272-299, doi:10.1016/j.jeconom.2022.04.001.
#   RESET: Ramsey (1969) JRSS-B 31(2):350-371. Studentized Breusch-Pagan: Breusch & Pagan (1979) Econometrica
#        47(5):1287-1294; Koenker (1981) J. Econometrics 17(1):107-112. Breusch-Godfrey: Breusch (1978)
#        Australian Economic Papers 17(31):334-355; Godfrey (1978) Econometrica 46(6):1293-1301.
#   GVIF: Fox & Monette (1992) JASA 87(417):178-183. Cook's distance: Cook (1977) Technometrics 19(1):15-18.

# Rscript reads a file one top-level expression at a time, which makes the large main() below slow to load
# (~0.35 s), and byte-compiling it on first call costs ~0.3 s more. Parse the whole file once and evaluate it
# (the final quit() ends the process inside this block); the JIT is off because main() runs only once.
if (!exists(".qme_parsed", inherits = FALSE)) {
  .qme_parsed <- TRUE
  .qme_self <- sub("^--file=", "", grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE))
  if (length(.qme_self) == 1L) for (.qme_e in parse(.qme_self, keep.source = FALSE)) eval(.qme_e, globalenv())
}
options(warn = 1)
invisible(compiler::enableJIT(0))

SCRIPT <- "regression_report"
.run_id <- sprintf("qme-%s-%s-%d", SCRIPT, format(Sys.time(), "%Y%m%dT%H%M%SZ", tz = "UTC"), Sys.getpid())
.src <- paste0("quant-model-evaluation/", SCRIPT)
.t0 <- Sys.time()
.script_path <- local({
  fa <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", fa[grepl("^--file=", fa)])
  if (length(f)) normalizePath(f[1L], winslash = "/", mustWork = FALSE) else file.path(getwd(), "regression_report.R")
})
source(file.path(dirname(.script_path), "_glassbox.R"))
.started <- .qme_iso()

HELP <- "regression_report.R - regression print + robust inference + diagnostics (quant-model-evaluation).
Read-only: reads --data; writes only report.md and report.json in a fresh run folder under --out.

Usage:
  Rscript scripts/regression_report.R --data FILE.csv --formula \"y ~ x1 + x2\" [options]

Stdout, in this order:
  1. print(summary(lm(...))), verbatim
  2. === Inference block: <vcov> (G = <clusters>, <bootstrap desc>) ===  estimate, SE, t, p, CI per term
     (+ wild-bootstrap p and CI when the bootstrap runs)
  3. === Diagnostics ===
  4. Trend: sign, size, consistency across strata, then uncertainty, in one line

Options:
  --data FILE        CSV (or .tsv) with one row per observation                       (required)
  --formula F        R model formula, e.g. \"y ~ x1 + log(x2) + factor(year)\"         (required)
                     it must be one two-sided formula; it is parsed (never evaluated as text) and its
                     functions are limited to an allowlist (arithmetic, comparisons, I, log/exp/sqrt/abs,
                     poly, factor, relevel, scale, offset, cut, pmin/pmax, ifelse, splines::ns/bs, ...);
                     anything else is refused, so no other code from the arguments is ever run
  --cluster COL      cluster id (the independent units); --cluster2 COL adds a second dimension (two-way)
  --vcov V           HC1 | HC3 | CR1 | CR2 | NW   (default CR1 with --cluster, else HC1)
                     CR2 needs the sandwich package; NW needs --time with one row per time value
  --nw-lag L         Newey-West lag (default floor(4*(N/100)^(2/9)))
  --boot B           wild | none (default wild when a clustered vcov has G < --min-clusters, else none)
  --B N              bootstrap replications (default 999)
  --weights COL      analytic (WLS) weights, >= 0 (zero-weight rows are dropped)
  --time COL         time index: Durbin-Watson and Breusch-Godfrey(1) (lagged within cluster for panels)
  --strata COL       refit the model in each stratum and compare the focal term's sign
  --term NAME        focal coefficient for the Trend line and strata (default: first non-intercept term)
  --level P          confidence level for intervals (default 0.95)
  --out DIR          output root (default qme_out)   --seed N (default 20260930)   --no-glassbox   --help

Criteria (flags, fixed before the run):
  --alpha 0.05            rejection level for RESET, Breusch-Pagan, Breusch-Godfrey
  --min-clusters 42       G below this: few-cluster warning, wild bootstrap by default
  --descriptive-below 10  G below this: inference labelled DESCRIPTIVE
  --collinear-r2 0.9999   auxiliary R^2 at or above this: near-collinear
  --vif-max 10            VIF (GVIF^(1/df) for multi-column terms) above this: WOUNDED
  --cook-max 1            max Cook's distance above this: WOUNDED (row named)
  --min-stratum-n 10      strata with fewer usable rows are skipped
  --min-sign-share 0.8    share of strata agreeing with the pooled sign needed for SURVIVES
  --parity-tol 1e-6       max relative SE gap between sandwich and the hand-built path

Verdict rules (a check that cannot be computed is recorded UNVERIFIED-HERE with the reason, never left out):
  LM-UNITS      G >= --min-clusters SURVIVES; below it WOUNDED (read the wild-bootstrap columns); below
                --descriptive-below WOUNDED and inference DESCRIPTIVE; no --cluster (or a vcov that ignores it)
                UNVERIFIED-HERE: rows are assumed independent and nothing in one table can show that; with
                --vcov NW UNVERIFIED-HERE too: one series, stationarity and weak dependence are assumed, not tested.
  LM-LEVERAGE   no row with leverage h >= 1 - 1e-8: SURVIVES. Otherwise WOUNDED: such a row (e.g. a one-row
                dummy) is fitted exactly, so robust SEs are unreliable for the coefficients it identifies (named).
  LM-COLLINEAR  aliased (exactly collinear) terms, or max auxiliary R^2 >= --collinear-r2: WOUNDED.
  LM-VIF        max term VIF <= --vif-max SURVIVES, else WOUNDED.
  LM-RESET      p >= --alpha SURVIVES, else WOUNDED (functional form).
  LM-BP         p >= --alpha SURVIVES, else WOUNDED: the classical SEs in the summary print are unreliable;
                read the inference block.
  LM-COOK       max Cook's distance <= --cook-max SURVIVES, else WOUNDED; rows where it is undefined
                (leverage 1) are named and count as WOUNDED.
  LM-SERIAL     (--time) Breusch-Godfrey(1) p >= --alpha SURVIVES; a rejection with HC1/HC3 is WOUNDED;
                with NW/CR1/CR2 it SURVIVES because the chosen vcov covers it (said in the detail).
  LM-STRATA     (--strata) share of estimable strata whose focal sign matches the pooled sign:
                >= --min-sign-share SURVIVES, >= 0.5 WOUNDED, < 0.5 KILLED; fewer than 2 strata UNVERIFIED-HERE.
  LM-CR2        CR2 requested without sandwich: UNVERIFIED-HERE (CR2 needs sandwich); CR1 is shown instead.
  LM-HC3        HC3 undefined (a row with leverage 1): UNVERIFIED-HERE; HC1 is shown instead.
  LM-PARITY     (sandwich installed) sandwich and hand-built SEs agree within --parity-tol: SURVIVES, else WOUNDED.
  Collinearity and VIF do not apply to a model with no regressor besides the intercept (said under Diagnostics).

Paths: sandwich/lmtest are used when installed (the inference block and report say which path ran); without
them every number comes from the base-R formulas in this file. QME_R_HAND_ONLY=1 forces the base-R path.

Exit codes: 0 all SURVIVES, 1 any WOUNDED/KILLED, 2 usage/input error, 3 UNVERIFIED-HERE present.
A KILLED printed by this script is a candidate verdict: record it only after a second independent reader confirms it.
"

VALUE_FLAGS <- c("data", "formula", "cluster", "cluster2", "vcov", "nw-lag", "boot", "B", "weights", "time",
                 "strata", "term", "level", "out", "seed", "alpha", "min-clusters", "descriptive-below",
                 "collinear-r2", "vif-max", "cook-max", "min-stratum-n", "min-sign-share", "parity-tol")
BOOL_FLAGS <- c("no-glassbox", "help")
S_OK <- "SURVIVES"; S_WD <- "WOUNDED"; S_KD <- "KILLED"; S_UV <- "UNVERIFIED-HERE"

qme_usage <- function(...) {
  stop(structure(class = c("qme_usage", "error", "condition"), list(message = paste0(...), call = NULL)))
}

# An R formula is code: lm() evaluates every call in it. Only these functions may appear, so the script never
# runs anything else that arrives through its arguments (build spec 5: no eval of user input).
FORMULA_FUNS <- c("~", "+", "-", "*", "/", ":", "^", "%in%", "(", "|", "&", "!", "==", "!=", "<", ">", "<=", ">=",
                  "I", "log", "log1p", "log2", "log10", "exp", "expm1", "sqrt", "abs", "sign", "round", "floor",
                  "ceiling", "trunc", "sin", "cos", "poly", "factor", "as.factor", "ordered", "relevel",
                  "as.numeric", "as.integer", "as.character", "scale", "offset", "cut", "pmin", "pmax", "ifelse",
                  "interaction", "c", "ns", "bs")
formula_calls <- function(e) {
  if (!is.call(e)) return(character(0))
  f <- e[[1L]]
  nm <- if (is.name(f)) as.character(f)
        else if (is.call(f) && identical(f[[1L]], as.name("::")) && as.character(f[[2L]]) %in% c("base", "stats", "splines"))
          as.character(f[[3L]]) else "<computed function>"
  c(nm, unlist(lapply(as.list(e)[-1L], formula_calls)))
}

parse_args <- function(argv) {
  a <- list()
  i <- 1L
  while (i <= length(argv)) {
    tok <- argv[[i]]
    if (!startsWith(tok, "--")) qme_usage("unexpected argument '", tok, "' (options start with --; see --help)")
    key <- substring(tok, 3L)
    val <- NULL
    eq <- regexpr("=", key, fixed = TRUE)
    if (eq > 0L) { val <- substring(key, eq + 1L); key <- substring(key, 1L, eq - 1L) }
    if (key %in% BOOL_FLAGS) {
      if (!is.null(val)) qme_usage("--", key, " takes no value")
      a[[key]] <- TRUE; i <- i + 1L; next
    }
    if (!(key %in% VALUE_FLAGS)) qme_usage("unknown option --", key, " (see --help)")
    if (is.null(val)) {
      if (i == length(argv)) qme_usage("--", key, " needs a value")
      val <- argv[[i + 1L]]; i <- i + 2L
    } else i <- i + 1L
    if (!is.null(a[[key]])) qme_usage("--", key, " given twice")
    a[[key]] <- val
  }
  a
}

num_arg <- function(a, key, default, lower = -Inf, upper = Inf, whole = FALSE) {
  v <- a[[key]]
  if (is.null(v)) return(default)
  x <- suppressWarnings(as.numeric(v))
  if (length(x) != 1L || !is.finite(x) || x < lower || x > upper || (whole && x != round(x)))
    qme_usage("--", key, " must be a ", if (whole) "whole " else "", "number in [", lower, ", ", upper,
              "]; got '", v, "'")
  x
}

read_data <- function(path) {
  if (grepl("://", path, fixed = TRUE)) qme_usage("--data must be a local file, not a URL: ", path)
  if (!file.exists(path) || dir.exists(path)) qme_usage("--data not found or not a file: ", path)
  sep <- if (grepl("\\.(tsv|tab)$", path, ignore.case = TRUE)) "\t" else ","
  df <- tryCatch(utils::read.csv(path, sep = sep, check.names = FALSE, stringsAsFactors = FALSE, encoding = "UTF-8",
                                 na.strings = c("", "NA", "NaN", "nan", "null", "NULL"), strip.white = TRUE),
                 error = function(e) qme_usage("cannot read --data as a table: ", conditionMessage(e)))
  if (!nrow(df) || !ncol(df)) qme_usage("--data has no rows or no columns: ", path)
  names(df)[1L] <- sub("^﻿", "", names(df)[1L])
  df
}

time_key <- function(v) {
  if (is.numeric(v)) return(list(key = as.numeric(v), how = "numeric"))
  d <- suppressWarnings(as.Date(as.character(v), optional = TRUE))
  if (!anyNA(d)) return(list(key = as.numeric(d), how = "date"))
  list(key = rank(as.character(v), ties.method = "min"), how = "text, lexicographic order")
}

# ---- covariance matrices (hand-built) ------------------------------------------------------------------
# Xs, us are the sqrt(weight)-scaled design and residuals, so the same formulas cover OLS and WLS.
cr_vcov <- function(Xs, us, XtXinv, cl, N, K) {
  S <- rowsum(Xs * us, cl, reorder = TRUE)            # G x K cluster score sums
  G <- nrow(S)
  (G / (G - 1)) * ((N - 1) / (N - K)) * (XtXinv %*% crossprod(S) %*% XtXinv)   # CR1; HC1 when G = N
}
hc3_vcov <- function(Xs, us, XtXinv, h) {
  if (any(1 - h < 1e-10)) return(NULL)
  XtXinv %*% crossprod(Xs * (us / (1 - h))) %*% XtXinv
}
nw_vcov <- function(Xs, us, XtXinv, ord, L) {
  E <- (Xs * us)[ord, , drop = FALSE]
  n <- nrow(E)
  S <- crossprod(E)
  for (l in seq_len(min(L, n - 1L))) {
    Gl <- crossprod(E[(l + 1L):n, , drop = FALSE], E[seq_len(n - l), , drop = FALSE])
    S <- S + (1 - l / (L + 1)) * (Gl + t(Gl))
  }
  XtXinv %*% S %*% XtXinv                              # = sandwich::NeweyWest(prewhite = FALSE, adjust = FALSE)
}
psd_fix <- function(V) {
  e <- eigen(V, symmetric = TRUE)
  if (all(e$values >= 0)) return(list(V = V, fixed = FALSE))
  W <- e$vectors %*% diag(pmax(e$values, 0), nrow(V)) %*% t(e$vectors)
  dimnames(W) <- dimnames(V)
  list(V = W, fixed = TRUE)
}

# ---- wild (cluster) restricted bootstrap, closed form -------------------------------------------------
# For H0: beta_j = b0 the restricted residuals are u(b0) = r_y - b0 * r_x, with r_y, r_x the residuals of y
# and x_j on the other regressors. With s = X (X'X)^-1 e_j, every bootstrap numerator and every bootstrap
# cluster score is linear in b0, so five B-vectors give t*(b0) for any b0 (Roodman et al. 2019).
wild_prep <- function(j, Xs, ys, us, XtXinv, clb, Gb, B, vals, seed, adj) {
  aj <- XtXinv[j, ]
  s <- drop(Xs %*% aj)
  Xm <- Xs[, -j, drop = FALSE]
  if (ncol(Xm)) { q <- qr(Xm); ry <- qr.resid(q, ys); rx <- qr.resid(q, Xs[, j]) } else { ry <- ys; rx <- Xs[, j] }
  dy <- rowsum(s * ry, clb)[, 1L]; dx <- rowsum(s * rx, clb)[, 1L]
  Sy <- t(rowsum(Xs * ry, clb)); Sx <- t(rowsum(Xs * rx, clb))       # K x G
  C <- rowsum(Xs * s, clb) %*% XtXinv                                  # G x K
  se_obs <- sqrt(adj * sum(rowsum(s * us, clb)^2))                    # CR1 (HC1) SE of beta_j
  ny <- nx <- qyy <- qxy <- qxx <- numeric(B)
  m <- max(1L, min(B, floor(4e6 / Gb)))
  starts <- seq(1L, B, by = m)
  for (ci in seq_along(starts)) {
    idx <- starts[ci]:min(B, starts[ci] + m - 1L)
    set.seed(seed + ci)                                               # same draws for every coefficient
    V <- matrix(sample(vals, Gb * length(idx), replace = TRUE), Gb, length(idx))
    ny[idx] <- colSums(dy * V); nx[idx] <- colSums(dx * V)
    Py <- dy * V - C %*% (Sy %*% V); Px <- dx * V - C %*% (Sx %*% V)
    qyy[idx] <- colSums(Py * Py); qxy[idx] <- colSums(Py * Px); qxx[idx] <- colSums(Px * Px)
  }
  list(ny = ny, nx = nx, qyy = qyy, qxy = qxy, qxx = qxx, se = se_obs, adj = adj)
}
wild_p <- function(pr, bj, b0) {
  tobs <- abs((bj - b0) / pr$se)
  den <- sqrt(pmax(pr$adj * (pr$qyy - 2 * b0 * pr$qxy + b0^2 * pr$qxx), 1e-300))
  mean(abs((pr$ny - b0 * pr$nx) / den) >= tobs - 1e-10 * max(1, tobs))   # symmetric p; ties count as extreme
}
wild_ci <- function(pr, bj, a, crit) {
  f <- function(b0) wild_p(pr, bj, b0) - a
  bound <- function(dir) {
    far <- bj + dir * 2 * max(pr$se * crit, 1e-12 * max(1, abs(bj)))
    k <- 0L
    while (f(far) > 0 && k < 40L) { far <- bj + 2 * (far - bj); k <- k + 1L }
    if (f(far) > 0) return(dir * Inf)
    near <- bj
    for (it in 1:60) { mid <- (near + far) / 2; if (f(mid) > 0) near <- mid else far <- mid }
    (near + far) / 2
  }
  c(bound(-1), bound(1))
}

# ---- diagnostics (hand-built) -------------------------------------------------------------------------
collin_diag <- function(fit, X) {
  mm <- stats::model.matrix(fit)
  asg <- attr(mm, "assign")[match(colnames(X), colnames(mm))]
  tl <- attr(stats::terms(fit), "term.labels")
  has_int <- "(Intercept)" %in% colnames(X)
  keep <- colnames(X) != "(Intercept)"
  Xn <- X[, keep, drop = FALSE]; an <- asg[keep]; p <- ncol(Xn)
  aux <- stats::setNames(numeric(p), colnames(Xn))
  for (k in seq_len(p)) {
    xk <- Xn[, k]
    others <- cbind(if (has_int) rep(1, nrow(Xn)) else NULL, Xn[, -k, drop = FALSE])
    tss <- if (has_int) sum((xk - mean(xk))^2) else sum(xk^2)
    if (tss <= 0) { aux[k] <- 1; next }
    rss <- if (ncol(others)) sum(qr.resid(qr(others), xk)^2) else tss
    aux[k] <- max(0, 1 - rss / tss)
  }
  vif <- numeric(0)
  R <- if (p >= 2) tryCatch(stats::cor(Xn), warning = function(w) NULL, error = function(e) NULL) else NULL
  for (tt in unique(an)) {
    idx <- which(an == tt)
    nm <- if (tt >= 1 && tt <= length(tl)) tl[tt] else colnames(Xn)[idx[1L]]
    v <- if (length(idx) == 1L) 1 / max(1 - aux[idx], 1e-16)
         else if (p == length(idx)) 1
         else if (is.null(R)) NA_real_
         else (det(R[idx, idx, drop = FALSE]) * det(R[-idx, -idx, drop = FALSE]) / det(R))^(1 / length(idx))
    vif[nm] <- v
  }
  list(aux = aux, vif = vif)
}
reset_hand <- function(Xs, ys, fv, sw) {
  f <- fv / max(abs(fv), 1e-300)                     # scaling leaves the RESET F unchanged
  q0 <- qr(Xs); q1 <- qr(cbind(Xs, sw * f^2, sw * f^3))
  df1 <- q1$rank - q0$rank; df2 <- nrow(Xs) - q1$rank
  if (df1 < 1) return(list(ok = FALSE, why = paste("the powers of the fitted values add no new column (constant fitted",
                                                     "values, e.g. an intercept-only model)")))
  if (df2 < 1) return(list(ok = FALSE, why = "no residual degrees of freedom are left once the powers are added"))
  rss0 <- sum(qr.resid(q0, ys)^2); rss1 <- sum(qr.resid(q1, ys)^2)
  if (rss1 <= 0) return(list(ok = FALSE, why = "the augmented model fits exactly (zero residual sum of squares)"))
  Fs <- ((rss0 - rss1) / df1) / (rss1 / df2)
  list(ok = TRUE, stat = Fs, df1 = df1, df2 = df2, p = stats::pf(Fs, df1, df2, lower.tail = FALSE), path = "hand-built")
}
bp_hand <- function(X, us) {
  Z <- cbind(1, X[, colnames(X) != "(Intercept)", drop = FALSE])
  e2 <- us^2; qz <- qr(Z); tss <- sum((e2 - mean(e2))^2)
  if (qz$rank < 2) return(list(ok = FALSE, why = "no regressor besides the intercept to test the residual variance against"))
  if (tss <= 0) return(list(ok = FALSE, why = "the squared residuals are constant (e.g. an exact fit)"))
  LM <- length(e2) * sum((qr.fitted(qz, e2) - mean(e2))^2) / tss   # Koenker's studentized form: N * R^2
  list(ok = TRUE, stat = LM, df = qz$rank - 1, p = stats::pchisq(LM, qz$rank - 1, lower.tail = FALSE), path = "hand-built")
}
redact_home <- function(x) {        # same rule as _common._redact_home: the home prefix carries the account name
  home <- Sys.getenv("USERPROFILE", Sys.getenv("HOME", ""))
  if (nchar(home) < 3) return(x)
  vapply(as.character(x), function(s) {
    for (h in unique(c(home, gsub("\\", "/", home, fixed = TRUE))))
      if (startsWith(tolower(s), tolower(h))) return(paste0("~", substring(s, nchar(h) + 1L)))
    s
  }, "", USE.NAMES = FALSE)
}
serial_hand <- function(us, Xs, key, cl) {
  N <- length(us)
  panel <- !is.null(cl) && anyDuplicated(key) > 0
  if (!panel && anyDuplicated(key)) return(list(ok = FALSE, why = "--time repeats and no --cluster separates the units"))
  ord <- if (panel) order(cl, key) else order(key)
  e <- us[ord]; g <- if (panel) cl[ord] else rep(1L, N)
  same <- c(FALSE, g[-1L] == g[-N])
  elag <- c(0, e[-N]); elag[!same] <- 0
  lag_full <- numeric(N); lag_full[ord] <- elag
  dw <- sum(((e[-1L] - e[-N])[same[-1L]])^2) / sum(e^2)
  rss <- sum(qr.resid(qr(cbind(Xs, lag_full)), us)^2)
  LM <- N * (1 - rss / sum(us^2))                                   # BG LM(1), lagged residual filled with 0
  list(ok = TRUE, mode = if (panel) "panel, lag within cluster" else "series", dw = dw,
       rho = sum(e * elag) / sum(e^2), stat = LM, p = stats::pchisq(LM, 1, lower.tail = FALSE), path = "hand-built",
       dup_within = panel && anyDuplicated(paste(cl, key)) > 0)
}

fmt <- function(x, d = 4) ifelse(is.na(x), "NA", trimws(formatC(x, digits = d, format = "g")))
fp <- function(p, B = NA) vapply(p, function(x) if (is.na(x)) "NA" else if (!is.na(B) && x == 0) sprintf("< %.2g", 1 / B)
                                 else if (x < 1e-16) "< 1e-16" else trimws(formatC(x, digits = 3, format = "g")), "")
ptxt <- function(s) if (startsWith(s, "<")) paste0("p ", s) else paste0("p = ", s)
sanitize <- function(x) {
  if (is.data.frame(x)) { x[] <- lapply(x, sanitize); return(x) }
  if (is.list(x)) return(lapply(x, sanitize))
  if (is.numeric(x)) x[!is.finite(x)] <- NA
  x
}
md_cell <- function(s) gsub("\n", " ", gsub("|", "\\|", as.character(s), fixed = TRUE), fixed = TRUE)

main <- function(argv) {
  a <- parse_args(argv)
  if (isTRUE(a[["help"]])) { cat(HELP); return(0L) }
  if (isTRUE(a[["no-glassbox"]])) qme_disable_glassbox()
  qme_emit("task", "started", paste(SCRIPT, "started"), run_id = .run_id, source = .src)
  if (is.null(a[["data"]])) qme_usage("--data is required (see --help)")
  if (is.null(a[["formula"]])) qme_usage("--formula is required, e.g. --formula \"y ~ x1 + x2\"")
  if (!requireNamespace("jsonlite", quietly = TRUE)) qme_usage("the jsonlite package is needed to write report.json")
  alpha <- num_arg(a, "alpha", 0.05, 1e-6, 0.5); level <- num_arg(a, "level", 0.95, 0.5, 0.9999)
  min_cl <- num_arg(a, "min-clusters", 42, 2, 1e9, TRUE); desc_below <- num_arg(a, "descriptive-below", 10, 2, 1e9, TRUE)
  col_r2 <- num_arg(a, "collinear-r2", 0.9999, 0, 1); vif_max <- num_arg(a, "vif-max", 10, 1, Inf)
  cook_max <- num_arg(a, "cook-max", 1, 0, Inf); min_sn <- num_arg(a, "min-stratum-n", 10, 2, 1e9, TRUE)
  min_share <- num_arg(a, "min-sign-share", 0.8, 0.5, 1); par_tol <- num_arg(a, "parity-tol", 1e-6, 0, 1)
  B <- num_arg(a, "B", 999, 9, 1e6, TRUE); seed <- num_arg(a, "seed", 20260930, -2147483647, 2147483647, TRUE)
  nw_lag_arg <- if (is.null(a[["nw-lag"]])) NA else num_arg(a, "nw-lag", 0, 0, 1e9, TRUE)
  out <- if (is.null(a[["out"]])) "qme_out" else a[["out"]]
  vc_req <- if (is.null(a[["vcov"]])) (if (is.null(a[["cluster"]])) "HC1" else "CR1") else toupper(a[["vcov"]])
  if (!(vc_req %in% c("HC1", "HC3", "CR1", "CR2", "NW"))) qme_usage("--vcov must be HC1, HC3, CR1, CR2 or NW; got '", a[["vcov"]], "'")
  if (vc_req %in% c("CR1", "CR2") && is.null(a[["cluster"]])) qme_usage("--vcov ", vc_req, " needs --cluster")
  if (vc_req == "NW" && is.null(a[["time"]])) qme_usage("--vcov NW needs --time")
  boot_arg <- if (is.null(a[["boot"]])) NULL else tolower(a[["boot"]])
  if (!is.null(boot_arg) && !(boot_arg %in% c("wild", "none"))) qme_usage("--boot must be wild or none")

  path <- a[["data"]]
  df <- read_data(path)
  n_read <- nrow(df)
  rc <- list()
  for (r in c("cluster", "cluster2", "weights", "time", "strata")) {
    v <- a[[r]]
    if (is.null(v)) next
    if (!(v %in% names(df))) qme_usage("--", r, " column '", v, "' not in --data (columns: ", paste(names(df), collapse = ", "), ")")
    rc[[r]] <- v
  }
  if (!is.null(rc[["cluster2"]]) && is.null(rc[["cluster"]])) qme_usage("--cluster2 needs --cluster")
  role_cols <- unique(unlist(rc, use.names = FALSE))
  # Parse only; never as.formula(<string>): for a top-level `(` or `{` call, stats:::formula.character eval()s
  # the text (a deprecated path), which would run code before any check. The allowlist is applied to the parse
  # tree, and the formula object is then assembled without evaluating anything.
  fe <- tryCatch(str2lang(a[["formula"]]), error = function(e) qme_usage("cannot parse --formula: ", conditionMessage(e)))
  if (!(is.call(fe) && identical(fe[[1L]], as.name("~")) && length(fe) == 3L))
    qme_usage("--formula must be a two-sided formula like y ~ x1 + x2")
  bad_fun <- setdiff(unique(formula_calls(fe)), FORMULA_FUNS)
  if (length(bad_fun)) qme_usage("--formula calls functions outside the allowed list: ", paste(bad_fun, collapse = ", "),
                                 " (allowed: ", paste(FORMULA_FUNS[-(1:18)], collapse = ", "), ", arithmetic and comparisons)")
  fml <- structure(fe, class = "formula", .Environment = globalenv())   # what `~` returns, built without eval
  if ("." %in% all.vars(fml)) {        # expand '.' over the columns that are not cluster/weights/time/strata
    fml <- stats::formula(stats::terms(fml, data = df[, setdiff(names(df), role_cols), drop = FALSE]))
    environment(fml) <- globalenv()
  }
  fvars <- all.vars(fml)
  unknown <- setdiff(fvars, names(df))
  unknown <- unknown[!vapply(unknown, exists, logical(1), envir = baseenv())]
  if (length(unknown)) qme_usage("--formula uses names not in --data: ", paste(unknown, collapse = ", "))
  wcol <- rc[["weights"]]
  if (!is.null(wcol) && !is.numeric(df[[wcol]])) qme_usage("--weights column must be numeric: ", wcol)
  bad <- rep(FALSE, n_read); why <- character(0)
  for (cn in unique(c(intersect(fvars, names(df)), role_cols))) {
    v <- df[[cn]]
    nb <- if (is.numeric(v)) !is.finite(v) else is.na(v)
    if (any(nb)) why <- c(why, sprintf("missing/non-finite %s (%d)", cn, sum(nb)))
    bad <- bad | nb
  }
  if (!is.null(wcol)) {
    if (any(df[[wcol]][!bad] < 0)) qme_usage("--weights must be >= 0")
    zw <- !bad & df[[wcol]] == 0
    if (any(zw)) { why <- c(why, sprintf("zero weight (%d)", sum(zw))); bad <- bad | zw }
  }
  dat <- df[!bad, , drop = FALSE]; orig_row <- which(!bad)
  if (nrow(dat) < 3L) qme_usage("fewer than 3 usable rows after dropping missing values (", paste(why, collapse = "; "), ")")
  for (r in c("cluster", "cluster2")) if (!is.null(rc[[r]]) && vc_req %in% c("CR1", "CR2") &&
                                            length(unique(dat[[rc[[r]]]])) < 2L) qme_usage("--", r, " has fewer than 2 clusters")
  if (vc_req == "NW" && anyDuplicated(dat[[rc[["time"]]]]))
    qme_usage("--vcov NW needs one row per --time value (a single series); for panels use --cluster")

  fit_expr <- function(dname) {
    if (is.null(wcol)) bquote(lm(.(fml), data = .(as.name(dname))))
    else bquote(lm(.(fml), data = .(as.name(dname)), weights = .(as.name(wcol))))
  }
  fit <- tryCatch(eval(fit_expr("dat")), error = function(e) qme_usage("lm() failed: ", conditionMessage(e)))
  if (is.matrix(stats::model.response(stats::model.frame(fit)))) qme_usage("a multivariate response is not supported")
  if (!is.null(fit$na.action)) {       # rows the formula's transforms turned into NA (e.g. log of a negative)
    di <- as.integer(fit$na.action)
    why <- c(why, sprintf("formula transform gave NA (%d)", length(di)))
    dat <- dat[-di, , drop = FALSE]; orig_row <- orig_row[-di]
  }
  if (fit$df.residual < 1) qme_usage("no residual degrees of freedom (N = ", nrow(dat), ", parameters = ", fit$rank, ")")
  est_names <- names(stats::coef(fit))[!is.na(stats::coef(fit))]
  focal <- if (is.null(a[["term"]])) { nn <- setdiff(est_names, "(Intercept)"); if (length(nn)) nn[1L] else est_names[1L] } else a[["term"]]
  if (!(focal %in% est_names)) qme_usage("--term '", focal, "' is not an estimated coefficient; choose one of: ", paste(est_names, collapse = ", "))

  # ---- 1. the verbatim summary print: always the first thing on stdout ----
  sm <- summary(fit)
  print(sm)
  sm_txt <- utils::capture.output(print(sm))

  cf <- stats::coef(fit); est_ok <- !is.na(cf); aliased <- names(cf)[!est_ok]
  X <- stats::model.matrix(fit)[, est_ok, drop = FALSE]; b <- cf[est_ok]
  N <- nrow(X); K <- ncol(X)
  wts <- stats::weights(fit); sw <- if (is.null(wts)) rep(1, N) else sqrt(wts)
  Xs <- X * sw; us <- as.numeric(stats::residuals(fit)) * sw; ys <- drop(Xs %*% b) + us
  XtXinv <- sm$cov.unscaled[names(b), names(b), drop = FALSE]
  resp <- paste(deparse(fml[[2L]]), collapse = "")
  checks <- list(); notes <- character(0)
  add <- function(id, title, verdict, criterion, value = NULL, detail = "")
    checks[[length(checks) + 1L]] <<- list(id = id, title = title, verdict = verdict, criterion = criterion,
                                           value = value, evidence = "[RUN]", detail = detail)
  cl1 <- if (is.null(rc[["cluster"]])) NULL else as.integer(factor(as.character(dat[[rc[["cluster"]]]])))
  cl2 <- if (is.null(rc[["cluster2"]])) NULL else as.integer(factor(as.character(dat[[rc[["cluster2"]]]])))
  G1 <- if (is.null(cl1)) NA_integer_ else max(cl1); G2 <- if (is.null(cl2)) NA_integer_ else max(cl2)
  tk <- if (is.null(rc[["time"]])) NULL else time_key(dat[[rc[["time"]]]])
  clustered <- vc_req %in% c("CR1", "CR2"); two_way <- clustered && !is.null(cl2)
  if (!clustered && !is.null(cl1)) notes <- c(notes, sprintf("--cluster given but --vcov %s ignores it; clustered SEs need --vcov CR1 or CR2.", vc_req))
  nw_lag <- NA
  if (vc_req == "NW") nw_lag <- as.integer(min(if (is.na(nw_lag_arg)) floor(4 * (N / 100)^(2 / 9)) else nw_lag_arg, N - 1))

  # ---- 2. covariance: hand-built always; sandwich when installed (then compared) ----
  cr1 <- function(cl) cr_vcov(Xs, us, XtXinv, cl, N, K)
  cl12 <- if (two_way) as.integer(factor(paste(cl1, cl2, sep = "\r"))) else NULL
  Vh <- switch(vc_req, HC1 = cr1(seq_len(N)), HC3 = hc3_vcov(Xs, us, XtXinv, stats::hatvalues(fit)),
               CR1 = , CR2 = if (two_way) cr1(cl1) + cr1(cl2) - cr1(cl12) else cr1(cl1),
               NW = nw_vcov(Xs, us, XtXinv, order(tk$key), nw_lag))
  if (two_way) { pf_ <- psd_fix(Vh); Vh <- pf_$V
    if (pf_$fixed) notes <- c(notes, "two-way CR1 was not positive semi-definite; negative eigenvalues set to 0 (CGM 2011).") }
  hand_only <- identical(Sys.getenv("QME_R_HAND_ONLY", "0"), "1")      # testing switch: force the base-R path
  has_sw <- !hand_only && requireNamespace("sandwich", quietly = TRUE)
  has_lt <- !hand_only && requireNamespace("lmtest", quietly = TRUE)
  Vp <- NULL
  if (has_sw) {
    clv <- if (is.null(cl2)) cl1 else data.frame(c1 = cl1, c2 = cl2)
    Vp <- tryCatch({
      r <- switch(vc_req, HC1 = sandwich::vcovHC(fit, type = "HC1"), HC3 = sandwich::vcovHC(fit, type = "HC3"),
                  CR1 = sandwich::vcovCL(fit, cluster = clv, type = "HC1"),
                  CR2 = sandwich::vcovCL(fit, cluster = clv, type = "HC2"),
                  NW = sandwich::NeweyWest(fit, lag = nw_lag, prewhite = FALSE, adjust = FALSE, order.by = tk$key))
      r <- r[names(b), names(b), drop = FALSE]
      if (any(!is.finite(r))) stop("non-finite entries")
      r
    }, error = function(e) { notes <<- c(notes, paste("sandwich failed; hand-built path used:", conditionMessage(e))); NULL })
  }
  vc_used <- vc_req; cov_path <- if (is.null(Vp)) "hand-built" else "sandwich"
  if (vc_req == "CR2" && is.null(Vp)) {
    vc_used <- "CR1"
    add("LM-CR2", "CR2 (Bell-McCaffrey) covariance", S_UV, "CR2 is computed only via sandwich::vcovCL(type = 'HC2')",
        NULL, "CR2 needs sandwich (not installed here); CR1 is shown instead.")
  }
  if (vc_req == "HC3" && is.null(Vh) && is.null(Vp)) {
    vc_used <- "HC1"; Vh <- cr1(seq_len(N))
    add("LM-HC3", "HC3 covariance", S_UV, "every row has leverage < 1", NULL,
        "HC3 is undefined here (a row has leverage 1, e.g. a dummy with one member); HC1 is shown instead.")
  }
  V <- if (!is.null(Vp)) Vp else Vh
  se_h <- if (is.null(Vh) || vc_req == "CR2") NULL else sqrt(pmax(diag(Vh), 0))
  if (!is.null(Vp) && !is.null(se_h)) {
    se_p <- sqrt(pmax(diag(Vp), 0)); rel <- max(abs(se_p - se_h) / pmax(abs(se_h), 1e-300))
    add("LM-PARITY", "sandwich vs hand-built SE (second computation path)", if (rel <= par_tol) S_OK else S_WD,
        sprintf("max relative SE gap <= %g", par_tol), rel,
        sprintf("%s via sandwich and by hand; largest relative gap %.3g.", vc_req, rel))
  }
  G_eff <- if (vc_used %in% c("CR1", "CR2")) (if (two_way) min(G1, G2) else G1) else NA
  df_ref <- if (vc_used %in% c("CR1", "CR2")) G_eff - 1 else N - K
  se <- sqrt(pmax(diag(V), 0)); tv <- b / se; pv <- 2 * stats::pt(-abs(tv), df_ref); test_path <- "hand-built"
  if (has_lt) {
    ct <- tryCatch(lmtest::coeftest(fit, vcov. = V, df = df_ref), error = function(e) NULL)
    if (!is.null(ct) && all(names(b) %in% rownames(ct))) {
      se <- ct[names(b), 2]; tv <- ct[names(b), 3]; pv <- ct[names(b), 4]; test_path <- "lmtest::coeftest"
    }
  }
  crit <- stats::qt(1 - (1 - level) / 2, df_ref); lo <- b - crit * se; hi <- b + crit * se

  # ---- bootstrap ----
  if (vc_used %in% c("CR1", "CR2")) {
    use2 <- two_way && G2 < G1
    clb <- if (use2) cl2 else cl1; clb_name <- if (use2) rc[["cluster2"]] else rc[["cluster"]]
  } else { clb <- seq_len(N); clb_name <- NULL }
  Gb <- max(clb)
  boot <- if (is.null(boot_arg)) (if (vc_used %in% c("CR1", "CR2") && G_eff < min_cl) "wild" else "none") else boot_arg
  if (boot == "wild" && vc_used == "NW") {
    boot <- "none"
    notes <- c(notes, "wild bootstrap not run: it treats units as independent and would erase the serial correlation NW covers.")
  }
  webb <- boot == "wild" && Gb <= 11
  bp_ <- bl <- bh <- rep(NA_real_, K)
  if (boot == "wild") {
    vals <- if (webb) c(-sqrt(1.5), -1, -sqrt(0.5), sqrt(0.5), 1, sqrt(1.5)) else c(-1, 1)
    adj_b <- (Gb / (Gb - 1)) * ((N - 1) / (N - K))
    for (j in seq_len(K)) {
      pr <- wild_prep(j, Xs, ys, us, XtXinv, clb, Gb, B, vals, seed, adj_b)
      bp_[j] <- wild_p(pr, b[j], 0)
      ci <- wild_ci(pr, b[j], 1 - level, stats::qt(1 - (1 - level) / 2, Gb - 1)); bl[j] <- ci[1]; bh[j] <- ci[2]
    }
  }
  G_txt <- if (vc_used %in% c("CR1", "CR2")) (if (two_way) sprintf("%d x %d", G1, G2) else as.character(G1)) else "none"
  boot_txt <- if (boot != "wild") "no bootstrap" else sprintf("%s, %s weights, B = %d",
    if (vc_used %in% c("CR1", "CR2")) (if (two_way) paste0("wild cluster restricted bootstrap by ", clb_name) else "wild cluster restricted bootstrap")
    else "wild restricted bootstrap (observation level)", if (webb) "Webb six-point" else "Rademacher", B)
  header <- sprintf("=== Inference block: %s (G = %s, %s) ===", if (two_way) paste(vc_used, "two-way") else vc_used, G_txt, boot_txt)
  tab <- data.frame(term = names(b), estimate = fmt(b), `std.err` = fmt(se), t = fmt(tv, 3), `Pr(>|t|)` = fp(pv),
                    lo = fmt(lo), hi = fmt(hi), check.names = FALSE, stringsAsFactors = FALSE)
  names(tab)[6:7] <- c(sprintf("%g%% CI low", 100 * level), "CI high")
  if (boot == "wild") { tab[["boot p"]] <- fp(bp_, B); tab[["boot CI low"]] <- fmt(bl); tab[["boot CI high"]] <- fmt(bh) }
  cov_desc <- switch(cov_path, sandwich = switch(vc_used, HC1 = "sandwich::vcovHC(type = 'HC1')", HC3 = "sandwich::vcovHC(type = 'HC3')",
    CR1 = "sandwich::vcovCL(type = 'HC1')", CR2 = "sandwich::vcovCL(type = 'HC2')", NW = "sandwich::NeweyWest(prewhite = FALSE)"),
    `hand-built` = paste0("hand-built ", vc_used, if (hand_only) " (QME_R_HAND_ONLY=1)" else if (!has_sw) " (sandwich not installed)" else ""))
  # Rows with leverage 1 are fitted exactly: their residual is 0, so HC/CR "robust" SEs of the coefficients they alone
  # identify come out spuriously small (review CR-05). Name the rows and the terms that lose identification without them.
  hv <- stats::hatvalues(fit)
  lev1 <- which(is.finite(hv) & hv >= 1 - 1e-8)
  lev_terms <- character(0)
  if (length(lev1)) {
    lev_terms <- if (length(lev1) >= N) names(b) else tryCatch({
      red <- stats::lm.fit(Xs[-lev1, , drop = FALSE], ys[-lev1])
      names(b)[is.na(red$coefficients)] }, error = function(e) character(0))
  }
  rows_list <- function(r) paste0(paste(utils::head(r, 10), collapse = ", "), if (length(r) > 10) sprintf(" (+%d more)", length(r) - 10) else "")
  lev_rows_txt <- rows_list(orig_row[lev1])
  lev_terms_txt <- if (length(lev_terms)) paste(lev_terms, collapse = ", ") else "the coefficients those rows pin down jointly"
  inf_notes <- character(0)
  if (length(lev1)) inf_notes <- c(inf_notes, sprintf("Leverage-1 rows (data rows %s) are fitted exactly: robust SEs for %s are unreliable (LM-LEVERAGE).",
                                                     lev_rows_txt, lev_terms_txt))
  if (vc_used %in% c("CR1", "CR2") && G_eff < desc_below) inf_notes <- c(inf_notes, sprintf("Inference is DESCRIPTIVE: G = %d < %d.", G_eff, desc_below))
  if (webb) inf_notes <- c(inf_notes, sprintf("Webb six-point weights used because G = %d <= 11 (Rademacher has only 2^G distinct draws).", Gb))
  if (boot == "wild") inf_notes <- c(inf_notes, sprintf("Bootstrap: null imposed per term, t studentized with %sCR1 by %s, symmetric p, CI by test inversion, seed %d.",
                                                       if (two_way) "one-way " else "", if (is.null(clb_name)) "row" else clb_name, seed),
                                     if (two_way) "The bootstrap p and CI are one-way; the analytic columns are two-way." else NULL)
  if (vc_used == "NW") inf_notes <- c(inf_notes, sprintf("Newey-West lag %d (Bartlett weights), ordered by %s.", nw_lag, rc[["time"]]))
  if (length(aliased)) inf_notes <- c(inf_notes, paste("Aliased (not estimable) terms omitted:", paste(aliased, collapse = ", ")))
  cat("\n", header, "\n", sep = "")
  cat(sprintf("covariance: %s | tests: %s | reference t(%d) | %g%% intervals\n", cov_desc, test_path, as.integer(df_ref), 100 * level))
  op <- options(width = 250)
  inf_txt <- utils::capture.output(print(tab, row.names = FALSE, right = TRUE))
  options(op)
  cat(inf_txt, sep = "\n")
  if (length(inf_notes)) cat(inf_notes, sep = "\n")

  # ---- 3. diagnostics ----
  dl <- character(0); diag <- list()
  dl <- c(dl, sprintf("Rows: %d read, %d used, %d dropped%s. Parameters K = %d, residual df = %d.", n_read, N, n_read - N,
                      if (length(why)) paste0(" (", paste(why, collapse = "; "), ")") else "", K, as.integer(fit$df.residual)))
  if (vc_used %in% c("CR1", "CR2")) {
    sz <- as.numeric(table(cl1))
    dl <- c(dl, sprintf("Independent units: G = %d clusters (%s)%s; rows per cluster min %d, median %g, max %d. Inference rests on G, not N = %d.",
                        G1, rc[["cluster"]], if (two_way) sprintf(" x %d (%s)", G2, rc[["cluster2"]]) else "",
                        as.integer(min(sz)), stats::median(sz), as.integer(max(sz)), N))
    v <- if (G_eff >= min_cl) S_OK else S_WD
    det_ <- if (G_eff < desc_below) sprintf("G = %d < %d: inference DESCRIPTIVE; the wild-bootstrap columns are the least-bad reading.", G_eff, desc_below)
            else if (G_eff < min_cl) sprintf("G = %d < %d: few clusters; read the wild-bootstrap p and CI, not the asymptotic ones.", G_eff, min_cl)
            else sprintf("G = %d clusters.", G_eff)
    if (G_eff < min_cl) dl <- c(dl, paste("Few clusters:", det_))
    add("LM-UNITS", "Independent units (N rows vs G clusters)", v, sprintf("G >= %d (--min-clusters); G < %d DESCRIPTIVE", min_cl, desc_below), G_eff, det_)
  } else if (vc_used == "NW") {
    nw_txt <- sprintf("one time series; Newey-West (lag %d) allows serial correlation up to lag %d; stationarity is assumed.",
                      nw_lag, nw_lag)
    dl <- c(dl, sprintf("Dependence: N = %d rows, %s", N, nw_txt))
    add("LM-UNITS", "Independent units (N rows vs G clusters)", S_UV, "one stationary, weakly dependent series (NW)", N,
        paste(nw_txt, "See core-statistics.md for the ADF/KPSS checks."))
  } else {
    dl <- c(dl, sprintf("Independent units: N = %d rows treated as independent (no clustered vcov).", N))
    add("LM-UNITS", "Independent units (N rows vs G clusters)", S_UV, "rows independent, or --cluster with a CR vcov", N,
        "Rows are assumed independent; rows sharing a unit (legislator, firm, state, date) would make these SEs too small. Pass --cluster.")
  }
  hmax <- max(hv[is.finite(hv)], 0)
  if (length(lev1)) {
    dl <- c(dl, sprintf("Leverage: %d row(s) with h >= 1 - 1e-8 (data rows %s), fitted exactly; they alone identify %s.",
                        length(lev1), lev_rows_txt, lev_terms_txt))
    add("LM-LEVERAGE", "Rows with leverage 1 (fitted exactly)", S_WD, "no row with leverage h >= 1 - 1e-8", hmax,
        sprintf(paste("robust SEs are unreliable for coefficients identified by single rows (e.g. one-row dummies): %s",
                      "(data rows %s). Drop or merge those rows' categories, or report the terms as not estimable."),
                lev_terms_txt, lev_rows_txt))
  } else {
    dl <- c(dl, sprintf("Leverage: max h = %s; no row is fitted exactly.", fmt(hmax)))
    add("LM-LEVERAGE", "Rows with leverage 1 (fitted exactly)", S_OK, "no row with leverage h >= 1 - 1e-8", hmax,
        sprintf("max leverage %s", fmt(hmax)))
  }
  diag$leverage <- list(max = hmax, rows = I(orig_row[lev1]), terms = I(lev_terms))
  cd_ <- collin_diag(fit, X); vif_path <- "hand-built"
  if (!hand_only && length(cd_$vif) >= 2 && !length(aliased) && requireNamespace("car", quietly = TRUE)) {
    cv <- tryCatch(car::vif(fit), error = function(e) NULL)                 # car reports GVIF^(1/(2 Df))
    if (!is.null(cv)) {
      v2 <- if (is.matrix(cv)) cv[, ncol(cv)]^2 else cv
      if (all(names(cd_$vif) %in% names(v2))) { cd_$vif <- v2[names(cd_$vif)]; vif_path <- "car::vif" }
    }
  }
  if (length(cd_$aux) || length(aliased)) {
    mx <- if (length(cd_$aux)) max(cd_$aux) else 0; wx <- if (length(cd_$aux)) names(cd_$aux)[which.max(cd_$aux)] else "-"
    dl <- c(dl, sprintf("Collinearity: max auxiliary R^2 = %s (%s); aliased terms: %s.", fmt(mx), wx,
                        if (length(aliased)) paste(aliased, collapse = ", ") else "none"))
    add("LM-COLLINEAR", "Near-collinearity / aliased terms", if (length(aliased) || mx >= col_r2) S_WD else S_OK,
        sprintf("no aliased terms and max auxiliary R^2 < %g", col_r2), if (length(aliased)) 1 else mx,
        if (length(aliased)) paste("aliased (dropped by lm):", paste(aliased, collapse = ", ")) else sprintf("max auxiliary R^2 %.6g (%s)", mx, wx))
    diag$collinearity <- list(aux_r2 = as.list(cd_$aux), aliased = I(aliased))
  }
  if (length(cd_$vif)) {
    vm <- max(cd_$vif, na.rm = TRUE); vn <- names(cd_$vif)[which.max(cd_$vif)]
    dl <- c(dl, sprintf("VIF: max %s (%s) [criterion <= %g; GVIF^(1/df) for multi-column terms] [%s].", fmt(vm, 3), vn, vif_max, vif_path))
    add("LM-VIF", "Variance inflation (VIF / GVIF^(1/df))", if (is.finite(vm) && vm <= vif_max) S_OK else S_WD,
        sprintf("max term VIF <= %g", vif_max), vm, paste(sprintf("%s %.3g", names(cd_$vif), cd_$vif), collapse = "; "))
    diag$vif <- as.list(cd_$vif)
  }
  if (!length(cd_$aux) && !length(aliased)) dl <- c(dl, "Collinearity and VIF: not applicable (no regressor besides the intercept).")
  fv <- stats::fitted(fit)
  # The hand-built version decides whether RESET is defined at all: lmtest::resettest does not check the rank of the
  # augmented design and returns a number even when the powers of the fitted values add nothing (intercept-only).
  rs <- reset_hand(Xs, ys, fv, sw)
  if (isTRUE(rs$ok) && has_lt && is.null(wts)) rs <- tryCatch({ r <- lmtest::resettest(fit, power = 2:3, type = "fitted")
    if (!is.finite(r$p.value)) stop("non-finite p")
    list(ok = TRUE, stat = unname(r$statistic), df1 = unname(r$parameter[1]), df2 = unname(r$parameter[2]), p = r$p.value,
         path = "lmtest::resettest") }, error = function(e) rs)
  if (isTRUE(rs$ok)) {
    dl <- c(dl, sprintf("RESET (fitted^2, fitted^3): F = %s on (%d, %d) df, %s [%s].", fmt(rs$stat), as.integer(rs$df1), as.integer(rs$df2), ptxt(fp(rs$p)), rs$path))
    add("LM-RESET", "Functional form (Ramsey RESET)", if (rs$p >= alpha) S_OK else S_WD, sprintf("p >= %g", alpha), rs$p,
        if (rs$p < alpha) "Powers of the fitted values add explanatory power: curvature or missing interactions." else "")
  } else {
    dl <- c(dl, paste("RESET: not computable:", rs$why))
    add("LM-RESET", "Functional form (Ramsey RESET)", S_UV, sprintf("p >= %g", alpha), NULL, paste("not computable:", rs$why))
  }
  diag$reset <- rs
  bpt <- bp_hand(X, us)                              # decides definedness; lmtest supplies the number when installed
  if (isTRUE(bpt$ok) && has_lt && is.null(wts)) bpt <- tryCatch({ r <- lmtest::bptest(fit)
    if (!is.finite(r$p.value)) stop("non-finite p")
    list(ok = TRUE, stat = unname(r$statistic), df = unname(r$parameter), p = r$p.value, path = "lmtest::bptest") },
    error = function(e) bpt)
  if (isTRUE(bpt$ok)) {
    dl <- c(dl, sprintf("Breusch-Pagan (studentized): LM = %s on %d df, %s [%s].", fmt(bpt$stat), as.integer(bpt$df), ptxt(fp(bpt$p)), bpt$path))
    add("LM-BP", "Classical SEs usable (homoskedasticity, Breusch-Pagan)", if (bpt$p >= alpha) S_OK else S_WD, sprintf("p >= %g", alpha), bpt$p,
        if (bpt$p < alpha) "Heteroskedastic: the classical SEs in the summary print are unreliable; read the inference block." else "")
  } else {
    dl <- c(dl, paste("Breusch-Pagan: not computable:", bpt$why))
    add("LM-BP", "Classical SEs usable (homoskedasticity, Breusch-Pagan)", S_UV, sprintf("p >= %g", alpha), NULL,
        paste("not computable:", bpt$why))
  }
  diag$breusch_pagan <- bpt
  cdist <- stats::cooks.distance(fit)
  undef <- which(!is.finite(cdist))                  # 0/0 at leverage-1 rows: named, never silently dropped
  undef_txt <- if (length(undef)) sprintf("undefined (leverage 1) at data rows %s", rows_list(orig_row[undef])) else ""
  if (length(undef) == length(cdist)) {
    why_cd <- "Cook's distance is undefined for every row (every row has leverage 1, or the fit is exact)"
    dl <- c(dl, paste("Cook's distance: not computable:", why_cd))
    add("LM-COOK", "Influential rows (Cook's distance)", S_UV, sprintf("max Cook's D <= %g; none undefined", cook_max), NULL, why_cd)
  } else {
    cfin <- cdist; cfin[undef] <- NA
    im <- which.max(cfin); dm <- unname(cfin[im]); n4 <- sum(cfin > 4 / N, na.rm = TRUE)
    dl <- c(dl, sprintf("Cook's distance: max %s at data row %d (1 = first row after the header) [criterion <= %g]; %d rows above 4/N%s.",
                        fmt(dm), orig_row[im], cook_max, n4, if (length(undef)) paste(";", undef_txt) else ""))
    add("LM-COOK", "Influential rows (Cook's distance)", if (dm <= cook_max && !length(undef)) S_OK else S_WD,
        sprintf("max Cook's D <= %g; none undefined", cook_max), dm,
        paste0(sprintf("max at data row %d; %d rows above 4/N", orig_row[im], n4), if (length(undef)) paste0("; ", undef_txt, " (see LM-LEVERAGE)") else ""))
    diag$cooks <- list(max = dm, row = orig_row[im], above_4_over_n = n4, undefined_rows = I(orig_row[undef]))
  }
  if (!is.null(tk)) {
    sr <- NULL
    panel_t <- !is.null(cl1) && anyDuplicated(tk$key) > 0
    if (has_lt && is.null(wts) && !panel_t && !anyDuplicated(tk$key)) sr <- tryCatch({
      bg <- lmtest::bgtest(fit, order = 1, order.by = tk$key); dw <- lmtest::dwtest(fit, order.by = tk$key)
      h <- serial_hand(us, Xs, tk$key, NULL)
      list(ok = TRUE, mode = "series", dw = unname(dw$statistic), rho = h$rho, stat = unname(bg$statistic), p = bg$p.value,
           path = "lmtest::bgtest/dwtest", dup_within = FALSE) }, error = function(e) NULL)
    if (is.null(sr)) sr <- serial_hand(us, Xs, tk$key, cl1)
    if (!isTRUE(sr$ok)) {
      dl <- c(dl, paste("Serial correlation: not assessed:", sr$why))
      add("LM-SERIAL", "Residual serial correlation (Breusch-Godfrey order 1)", S_UV, sprintf("BG(1) p >= %g", alpha), NULL, sr$why)
    } else {
      covered <- vc_used %in% c("NW", "CR1", "CR2")
      v <- if (sr$p >= alpha || covered) S_OK else S_WD
      dl <- c(dl, sprintf("Serial correlation (--time %s, %s, %s order): DW = %s, rho1 = %s; Breusch-Godfrey LM(1) = %s, %s [%s].",
                          rc[["time"]], sr$mode, tk$how, fmt(sr$dw, 3), fmt(sr$rho, 3), fmt(sr$stat), ptxt(fp(sr$p)), sr$path))
      if (isTRUE(sr$dup_within)) notes <- c(notes, "--time repeats within a cluster; the within-cluster lag order is ambiguous.")
      add("LM-SERIAL", "Residual serial correlation (Breusch-Godfrey order 1)", v, sprintf("BG(1) p >= %g, or a vcov (NW/CR) that covers it", alpha), sr$p,
          if (sr$p < alpha && covered) sprintf("serially correlated residuals; covered by %s.", vc_used)
          else if (sr$p < alpha) sprintf("serially correlated residuals; %s assumes none: use --vcov NW (one series) or --cluster by unit.", vc_used) else "")
      diag$serial <- sr
    }
  }
  jf <- match(focal, names(b)); bf <- unname(b[jf])
  strata_df <- NULL; st_txt <- "consistency across strata not assessed (no --strata)"
  if (!is.null(rc[["strata"]])) {
    sv <- dat[[rc[["strata"]]]]; rows <- list()
    # Terms built from the strata column are constant inside a stratum: drop them from the within-stratum refits.
    tls <- attr(stats::terms(fml), "term.labels")
    drop_t <- tls[vapply(tls, function(t) rc[["strata"]] %in% all.vars(str2lang(t)), logical(1))]
    fml_full <- fml
    if (length(drop_t)) {       # ". ~ . - term1 - term2", assembled from parsed terms, never from a string
      rhs <- Reduce(function(acc, t) call("-", acc, str2lang(t)), drop_t, quote(.))
      fml <- stats::update(fml, structure(call("~", quote(.), rhs), class = "formula", .Environment = globalenv()))
      notes <- c(notes, paste("within-stratum refits drop the terms built from the strata column:", paste(drop_t, collapse = ", ")))
    }
    for (s in sort(unique(sv))) {
      ds <- dat[sv == s, , drop = FALSE]; est <- NA_real_; ses <- NA_real_; status <- "ok"
      if (nrow(ds) < min_sn) status <- sprintf("skipped: n < %d", min_sn) else {
        fs <- tryCatch(suppressWarnings(eval(fit_expr("ds"))), error = function(e) e)
        if (inherits(fs, "error")) status <- paste("fit failed:", conditionMessage(fs))
        else if (!(focal %in% names(stats::coef(fs))) || is.na(stats::coef(fs)[focal])) status <- "focal term not estimable"
        else { est <- unname(stats::coef(fs)[focal]); if (fs$df.residual > 0) ses <- summary(fs)$coefficients[focal, 2] }
      }
      rows[[length(rows) + 1L]] <- data.frame(stratum = as.character(s), n = nrow(ds), estimate = est, se = ses, status = status, stringsAsFactors = FALSE)
    }
    fml <- fml_full
    strata_df <- do.call(rbind, rows)
    ok_s <- !is.na(strata_df$estimate); nk <- sum(ok_s); agree <- sum(sign(strata_df$estimate[ok_s]) == sign(bf))
    share <- if (nk) agree / nk else NA_real_
    st_txt <- if (nk) sprintf("same sign in %d of %d strata", agree, nk) else "no stratum could estimate the focal term"
    dl <- c(dl, sprintf("Strata (--strata %s, focal %s): %s (share %s; %d skipped or failed).", rc[["strata"]], focal, st_txt, fmt(share, 3), sum(!ok_s)))
    op <- options(width = 250)
    dl <- c(dl, paste0("  ", utils::capture.output(print(transform(strata_df, estimate = fmt(estimate), se = fmt(se)), row.names = FALSE))))
    options(op)
    v <- if (nk < 2) S_UV else if (share >= min_share) S_OK else if (share >= 0.5) S_WD else S_KD
    add("LM-STRATA", sprintf("Focal term %s keeps the pooled sign across strata", focal), v,
        sprintf("share >= %g SURVIVES; >= 0.5 WOUNDED; < 0.5 KILLED; >= 2 estimable strata", min_share), share,
        sprintf("%s (pooled %s).", st_txt, fmt(bf)))
  }
  if (length(notes)) dl <- c(dl, paste("Note:", notes))
  cat("\n=== Diagnostics ===\n"); cat(dl, sep = "\n")

  # ---- 4. Trend line: sign, size, consistency, then uncertainty ----
  is01 <- all(X[, jf] %in% c(0, 1)) && length(unique(X[, jf])) == 2
  unit_txt <- if (focal == "(Intercept)") sprintf("level of %s when every regressor is 0", resp)
              else if (is01) sprintf("%s when %s = 1 vs 0", resp, focal) else sprintf("%s per unit of %s", resp, focal)
  sgn <- if (bf > 0) "positive" else if (bf < 0) "negative" else "zero"
  unc <- sprintf("%g%% CI %s to %s (%s%s)", 100 * level, fmt(lo[jf]), fmt(hi[jf]), vc_used,
                 if (vc_used %in% c("CR1", "CR2")) paste0(", G = ", G_txt) else "")
  if (boot == "wild") unc <- paste0(unc, sprintf("; wild-bootstrap%s %s, CI %s to %s",
                                                 if (two_way) sprintf(" (one-way by %s)", clb_name) else "",
                                                 ptxt(fp(bp_[jf], B)), fmt(bl[jf]), fmt(bh[jf])))
  else unc <- paste0(unc, "; ", ptxt(fp(pv[jf])))
  if (jf %in% match(lev_terms, names(b))) unc <- paste0(unc, "; SE unreliable: identified by leverage-1 rows")
  if (vc_used %in% c("CR1", "CR2") && G_eff < desc_below) unc <- paste0(unc, "; inference DESCRIPTIVE")
  trend <- sprintf("Trend: %s is %s (%s %s); %s; %s.", focal, sgn, fmt(bf), unit_txt, st_txt, unc)
  cat("\n", trend, "\n", sep = "")

  # ---- reports ----
  verd <- vapply(checks, function(ch) ch$verdict, "")
  counts <- stats::setNames(lapply(QME_VERDICTS, function(v) sum(verd == v)), QME_VERDICTS)
  pk <- function(p) tryCatch(as.character(utils::packageVersion(p)), error = function(e) NULL)   # reads, never loads
  inp <- normalizePath(path, winslash = "/", mustWork = TRUE); sha <- qme_sha256(inp)
  prov <- list(skill = QME_SKILL, skill_version = QME_VERSION, script = SCRIPT, argv = I(redact_home(c(.script_path, argv))),
               started_utc = .started, finished_utc = .qme_iso(), seed = seed, python = NULL, r = R.version.string,
               platform = paste(R.version$platform, utils::sessionInfo()$running),
               packages = list(stats = as.character(getRversion()), sandwich = pk("sandwich"), lmtest = pk("lmtest"),
                               jsonlite = pk("jsonlite"), digest = pk("digest")),
               inputs = list(list(path = redact_home(inp), bytes = file.size(inp), sha256 = sha)))
  infer <- data.frame(term = names(b), estimate = unname(b), se = unname(se), t = unname(tv), p = unname(pv), ci_low = unname(lo),
                      ci_high = unname(hi), boot_p = bp_, boot_ci_low = bl, boot_ci_high = bh, stringsAsFactors = FALSE)
  data <- list(formula = paste(deparse(fml, width.cutoff = 500L), collapse = " "), response = resp, focal_term = focal,
               rows = list(read = n_read, used = N, dropped = n_read - N, why = I(why)), parameters = K, aliased = I(aliased),
               df_residual = fit$df.residual,
               vcov = list(requested = vc_req, used = vc_used, covariance_path = cov_path, tests_path = test_path,
                           reference_df = df_ref, nw_lag = nw_lag, two_way = two_way, level = level),
               clusters = list(cluster = rc[["cluster"]], G = G1, cluster2 = rc[["cluster2"]], G2 = G2),
               bootstrap = list(type = boot, weights = if (boot == "wild") (if (webb) "webb6" else "rademacher") else NULL,
                                B = if (boot == "wild") B else NULL, seed = seed, cluster = clb_name, G = if (boot == "wild") Gb else NULL,
                                studentization = if (boot == "wild") "CR1 (one-way, bootstrap cluster)" else NULL),
               inference = infer, hand_built_se = if (is.null(se_h)) NULL else as.list(se_h),
               package_se = if (is.null(Vp)) NULL else as.list(sqrt(pmax(diag(Vp), 0))),
               diagnostics = diag, strata = strata_df, trend = trend, inference_header = header,
               summary_print = I(sm_txt), notes = I(notes))
  run_dir <- qme_run_dir(out, SCRIPT)
  js <- jsonlite::toJSON(sanitize(list(provenance = prov, counts = counts, checks = checks, data = data)), auto_unbox = TRUE,
                         pretty = TRUE, digits = NA, null = "null", na = "null")
  qme_write_once(file.path(run_dir, "report.json"), js)
  dot <- " · "
  md <- c(paste("#", SCRIPT, "report"), "",
          paste0("Provenance: ", QME_SKILL, " ", QME_VERSION, dot, SCRIPT, dot, "seed ", seed, dot, basename(inp), " sha256:",
                 substr(sha, 1, 12), dot, "R ", getRversion(), dot, .started), "",
          paste("Verdicts:", paste(names(counts), unlist(counts), collapse = ", ")), "",
          "| id | check | verdict | value | criterion | evidence |", "|---|---|---|---|---|---|")
  for (ch in checks) md <- c(md, sprintf("| %s | %s | %s | %s | %s | %s |", ch$id, md_cell(ch$title), ch$verdict,
                                         if (is.null(ch$value)) "" else md_cell(format(ch$value, digits = 6)), md_cell(ch$criterion), ch$evidence))
  det <- Filter(function(ch) nzchar(ch$detail), checks)
  if (length(det)) md <- c(md, "", "## Details", "", vapply(det, function(ch) sprintf("- **%s** (%s): %s", ch$id, ch$verdict, ch$detail), ""))
  md <- c(md, "", "## R summary(lm()) print", "", "```text", sm_txt, "```", "", "## Inference block", "", "```text", header,
          sprintf("covariance: %s | tests: %s | reference t(%d)", cov_desc, test_path, as.integer(df_ref)), inf_txt, inf_notes, "```",
          "", "## Diagnostics", "", "```text", dl, "```", "", "## Trend", "", trend)
  qme_write_once(file.path(run_dir, "report.md"), md)
  code <- qme_exit_code(verd)
  summ <- paste0(SCRIPT, ": ", paste(names(counts)[unlist(counts) > 0], unlist(counts)[unlist(counts) > 0], collapse = ", "))
  qme_emit("task", "completed", summ, run_id = .run_id, source = .src, detail = file.path(run_dir, "report.md"),
           duration_ms = as.integer(1000 * as.numeric(difftime(Sys.time(), .t0, units = "secs"))))
  cat("\nVerdicts: ", paste(names(counts), unlist(counts), collapse = ", "), "\n", sep = "")
  cat("report: ", file.path(run_dir, "report.md"), "\n", sep = "")
  code
}

.argv <- commandArgs(trailingOnly = TRUE)
if ("--no-glassbox" %in% .argv) qme_disable_glassbox()
.code <- tryCatch(main(.argv),
  qme_usage = function(e) {
    cat("usage error: ", conditionMessage(e), "\n", sep = "", file = stderr())
    qme_emit("task", "failed", paste0(SCRIPT, ": usage error"), run_id = .run_id, source = .src, detail = conditionMessage(e))
    QME_EXIT$usage
  },
  error = function(e) {
    cat("error: ", conditionMessage(e), "\n", sep = "", file = stderr())
    qme_emit("task", "failed", paste0(SCRIPT, ": error"), run_id = .run_id, source = .src, detail = conditionMessage(e))
    QME_EXIT$usage
  })
quit(save = "no", status = .code)
