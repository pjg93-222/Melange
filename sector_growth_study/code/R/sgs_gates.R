# Estimability gates of the sector-year tests (Paul's rule R8) and the primary-then-fallback window decision
# (R port of code/sgs/gates.py).
#
# A test is ESTIMABLE in a window only if its complete-case sample has
#   * at least `min_years` distinct years (6 in the primary window; the fallback window is 10 consecutive years),
#   * at least 2 sectors (every sector with complete data enters; none is selected out),
#   * a full-column-rank design, with the year-level (national) regressors checked separately against the number of
#     distinct years (sector baselines span a common level, so K national regressors need K + 1 independent years),
#   * residual degrees of freedom of at least 3.
# The primary window (2020-2025) is tried first. Only when it fails, the fallback window is searched for: the most
# recent run of at least 10 consecutive calendar years within 2008-2025 in which the test's complete-case sample
# exists; the window used is that run's most recent 10 years (the whole run for tests with fallback_whole_run, the
# LobbyView family under Paul's rulings). PREVIEW tests use the fixed window 2021-2025 (>= 5 years, no fallback);
# their full core specification is NOT IDENTIFIED when its year-level parameters are as many as the distinct years.
# H5 (champions) has its own member-cycle gate in sgs_champions.R.

.normalised <- function(M) {
  norms <- sqrt(colSums(M * M))
  norms[norms == 0] <- 1
  sweep(M, 2, norms, "/")
}

# numpy.linalg.matrix_rank of the column-normalised matrix (SVD, tolerance max(s) * max(dim) * eps).
sgs_rank_of <- function(M) {
  M <- as.matrix(M)
  if (!length(M) || !nrow(M) || !ncol(M)) return(0L)
  d <- svd(.normalised(M), nu = 0, nv = 0)$d
  tol <- max(d) * max(dim(M)) * .Machine$double.eps
  as.integer(sum(d > tol))
}

# Columns (in `order`, 1-based) that add no rank given the columns kept before them.
sgs_dependent_columns <- function(M, names, order = seq_len(ncol(M))) {
  kept <- integer(0); dep <- character(0); r <- 0L
  for (j in order) {
    r2 <- sgs_rank_of(M[, c(kept, j), drop = FALSE])
    if (r2 > r) { kept <- c(kept, j); r <- r2 } else dep <- c(dep, names[j])
  }
  dep
}

# R^2 of column j of X on the other columns of X plus a constant (the constant is redundant, and aliased by the pivoting
# QR, when the other columns already span it, as fixed-effect designs do). A column with no variation has R^2 = 1.
sgs_aux_r2 <- function(X, j) {
  x <- as.numeric(X[, j])
  tss <- sum((x - mean(x))^2)
  if (!(tss > 0)) return(1)
  r <- qr.resid(qr(cbind(1, X[, -j, drop = FALSE])), x)
  1 - sum(r^2) / tss
}

# Near-collinearity rule (rulings of 2026-09-26): among `candidates` (columns of X that may be dropped: controls),
# repeatedly drop the one whose R^2 on every other kept column is highest, while that R^2 is >= threshold. Exact
# dependencies are removed before this rule runs, so every R^2 here is below 1 in exact arithmetic. Returns the dropped
# names (in drop order) and their R^2.
sgs_near_collinear_columns <- function(X, candidates, threshold) {
  keep <- colnames(X); dropped <- character(0); r2s <- numeric(0)
  if (!is.finite(threshold)) return(list(dropped = dropped, r2 = r2s))
  repeat {
    cand <- intersect(candidates, keep)
    if (!length(cand) || length(keep) < 2) break
    Xk <- X[, keep, drop = FALSE]
    r2 <- vapply(cand, function(cn) sgs_aux_r2(Xk, match(cn, keep)), 0)
    k <- which.max(r2)
    if (!(r2[k] >= threshold)) break
    dropped <- c(dropped, cand[k]); r2s <- c(r2s, unname(r2[k])); keep <- setdiff(keep, cand[k])
  }
  list(dropped = dropped, r2 = r2s)
}

# Fixed effects first, then national controls, then the rest, so non-identification is attributed to the regressors.
sgs_check_order <- function(design) {
  fe <- which(startsWith(design$names, "FE:") | startsWith(design$names, "YFE:"))
  nat <- which(design$names %in% design$national)
  rest <- setdiff(seq_along(design$names), c(fe, nat))
  c(fe, nat, rest)
}

# SHIFT designs (rulings of 2026-09-26) carry their identifying cells (years, or year x chamber in the stacked table):
# the regressors constant within cells plus the levels the baselines span (common level; chamber level) need full
# column rank across the distinct cells. Every other design keeps the year-level check below unchanged.
sgs_cell_level_matrix <- function(design) {
  cells <- design$cells
  uc <- sort(unique(cells), method = "radix")
  first <- match(uc, cells)
  Z <- NULL; zn <- character(0)
  if ("common level" %in% design$cell_spanned) { Z <- cbind(Z, rep(1, length(uc))); zn <- c(zn, "common level") }
  if ("chamber level" %in% design$cell_spanned) { Z <- cbind(Z, as.numeric(grepl("Senate$", uc))); zn <- c(zn, "chamber level") }
  for (v in design$cell_vars) { Z <- cbind(Z, design$X[first, match(v, design$names)]); zn <- c(zn, v) }
  if (is.null(Z)) Z <- matrix(0, length(uc), 0)
  colnames(Z) <- zn
  list(Z = Z, names = zn, cells = uc)
}

sgs_cell_level_check <- function(design) {
  cm <- sgs_cell_level_matrix(design)
  k <- ncol(cm$Z)
  if (!k) return(list(ok = TRUE, why = ""))
  r <- sgs_rank_of(cm$Z)
  if (r == k) return(list(ok = TRUE, why = ""))
  word <- if (any(grepl(" ", cm$cells))) "year x chamber cells" else "distinct years"
  dep <- sgs_dependent_columns(cm$Z, cm$names)
  list(ok = FALSE, why = paste0("year-level design not identified: ", k, " year-level parameters (", paste(cm$names, collapse = ", "),
                                ") on ", length(cm$cells), " ", word, " (", paste(cm$cells, collapse = ", "), "), rank ", r,
                                "; not identified: ", paste(dep, collapse = ", ")))
}

sgs_year_level_check <- function(design) {
  if (!is.null(design$cells)) return(sgs_cell_level_check(design))
  if (!length(design$national)) return(list(ok = TRUE, why = ""))
  idx <- match(design$national, design$names)
  yrs <- sort(unique(design$years))
  first <- match(yrs, design$years)
  M <- design$X[first, idx, drop = FALSE]
  nm <- design$national
  if (isTRUE(design$intercept_spanned)) {
    M <- cbind(1, M)
    nm <- c("common level of the sector baselines", nm)
  }
  k <- ncol(M); t <- nrow(M)
  r <- sgs_rank_of(M)
  if (r == k) return(list(ok = TRUE, why = ""))
  dep <- sgs_dependent_columns(M, nm)
  list(ok = FALSE, why = paste0("year-level design not identified: ", k, " year-level parameters (", paste(nm, collapse = ", "),
                                ") on ", t, " distinct years (", sgs_years_text(yrs), "), rank ", r, "; not identified: ",
                                paste(dep, collapse = ", ")))
}

sgs_full_rank_check <- function(design) {
  p <- ncol(design$X)
  r <- sgs_rank_of(design$X)
  if (r == p) return(list(ok = TRUE, why = "", rank = r))
  dep <- sgs_dependent_columns(design$X, design$names, sgs_check_order(design))
  list(ok = FALSE, why = paste0("design rank ", r, " < ", p, " columns; not identified: ", paste(dep, collapse = ", ")), rank = r)
}

.win_text <- function(w) paste0(sgs_int_str(w[1]), "-", sgs_int_str(w[2]))

sgs_attempt_compact <- function(a) {
  w <- .win_text(a$window)
  if (a$ok) return(paste0(a$kind, " ", w, ": passes"))
  if (isTRUE(a$is_search)) return(paste0("fallback search ", w, ": ", paste(a$compact_parts, collapse = "; ")))
  paste0(a$kind, " ", w, ": ", paste(a$compact_parts, collapse = "; "))
}

sgs_attempt_text <- function(a) {
  w <- .win_text(a$window)
  if (isTRUE(a$is_search)) {
    return(paste0("fallback search ", w, " (needs a run of >= ", a$min_years, " consecutive years): ",
                  paste(a$reasons, collapse = "; ")))
  }
  need <- if (a$kind != "fallback") paste0("needs >= ", a$min_years, " years") else
    paste0("most recent run of >= ", a$min_years, " consecutive complete-case years; ", a$search)
  if (a$ok) {
    return(paste0(a$kind, " ", w, ": passes (n=", a$n, ", ", length(a$sectors), " sectors, ", length(a$years), " years)",
                  if (nzchar(a$search)) paste0(" [", a$search, "]") else ""))
  }
  paste0(a$kind, " ", w, " (", need, "): ", paste(a$reasons, collapse = "; "))
}

.gap_parts <- function(smp) {
  out <- character(0)
  gaps <- character(0); never <- character(0)
  for (it in smp$items) {
    if (it$kind == "var_years") gaps <- c(gaps, paste0(it$var, " ", sgs_years_text(it$years)))
    if (it$kind == "sector") never <- c(never, it$sector)
  }
  if (length(gaps)) out <- c(out, paste0("no sector has ", paste(gaps, collapse = ", ")))
  if (length(never)) out <- c(out, paste0("never complete: ", paste(never, collapse = ", ")))
  out
}

sgs_assess <- function(smp, spec, min_years, kind = "default", check_years = TRUE) {
  reasons <- character(0)
  years <- sgs_sample_years(smp); sectors <- sgs_sample_sectors(smp)
  design <- NULL; resid_df <- NA_integer_
  short <- FALSE
  n <- nrow(smp$df)
  if (n == 0) {
    reasons <- c(reasons, "complete-case sample is empty"); short <- TRUE
  } else {
    if (check_years && length(years) < min_years) {
      reasons <- c(reasons, paste0(length(years), " distinct years (", sgs_years_text(years), ") < ", min_years, " required"))
      short <- TRUE
    }
    if (length(sectors) < SGS$MIN_SECTORS) {
      reasons <- c(reasons, paste0(length(sectors), " sector(s) (", paste(sectors, collapse = ", "), ") < ",
                                   SGS$MIN_SECTORS, " required"))
      short <- TRUE
    }
    design <- sgs_build_design(smp$df, spec)
    yl <- sgs_year_level_check(design)
    if (!yl$ok) reasons <- c(reasons, yl$why)
    fr <- sgs_full_rank_check(design)
    if (!fr$ok) reasons <- c(reasons, fr$why)
    resid_df <- nrow(design$X) - fr$rank
    if (resid_df < SGS$MIN_RESID_DF) reasons <- c(reasons, paste0("residual df ", resid_df, " < ", SGS$MIN_RESID_DF))
  }
  if (short && length(smp$diagnosis)) reasons <- c(reasons, paste0("blocking inputs: ", paste(smp$diagnosis, collapse = "; ")))
  compact <- character(0)
  if (length(reasons)) {
    if (n == 0) {
      compact <- c(compact, "empty complete-case sample")
    } else {
      if (check_years && length(years) < min_years) {
        compact <- c(compact, paste0(length(years), " of ", min_years, " years (", sgs_years_text(years), ")"))
      }
      if (length(sectors) < SGS$MIN_SECTORS) compact <- c(compact, paste0(length(sectors), " sector(s)"))
      for (r in reasons) {
        if (startsWith(r, "year-level design not identified")) {
          compact <- c(compact, paste0("year-level terms not identified: ", sub(".*; not identified: ", "", r)))
        } else if (startsWith(r, "design rank") && !any(startsWith(compact, "year-level"))) {
          compact <- c(compact, paste0("not identified: ", sub(".*; not identified: ", "", r)))
        } else if (startsWith(r, "residual df")) {
          compact <- c(compact, sub("residual df", "resid df", r, fixed = TRUE))
        }
      }
    }
    if (short) compact <- c(compact, .gap_parts(smp))
  }
  list(kind = kind, window = smp$window, min_years = min_years, ok = !length(reasons), reasons = reasons, n = n,
       years = years, sectors = sectors, resid_df = resid_df, sample = smp, design = design, compact_parts = compact,
       search = "", is_search = FALSE)
}

sgs_decision <- function(status, window = NULL, window_kind = NA_character_, attempts = list(), reason = "",
                         fallback_search = "") {
  list(status = status, window = window, window_kind = window_kind, attempts = attempts, reason = reason,
       fallback_search = fallback_search)
}

sgs_decision_chosen <- function(d) {
  for (a in d$attempts) if (isTRUE(a$ok)) return(a)
  NULL
}

# Leave-one-out tests are gated on their parent (level) sample.
sgs_sample_spec <- function(spec) {
  if (spec$variant %in% c("loso", "loyo")) spec$variant <- "level"
  spec
}

# Maximal runs of consecutive calendar years, oldest first.
sgs_year_runs <- function(years) {
  runs <- list()
  for (y in sort(unique(as.integer(years)))) {
    if (length(runs) && y == tail(runs[[length(runs)]], 1) + 1L) runs[[length(runs)]] <- c(runs[[length(runs)]], y)
    else runs[[length(runs) + 1L]] <- y
  }
  runs
}

.runs_text <- function(runs) {
  if (!length(runs)) return("none")
  paste(vapply(runs, function(r) if (length(r) > 1) paste0(r[1], "-", tail(r, 1), " (", length(r), " years)")
                else paste0(r[1], " (1 year)"), ""), collapse = ", ")
}

sgs_fallback_window <- function(tables, sspec, search, include_partial = FALSE, min_years = SGS$MIN_YEARS_FALLBACK,
                                whole_run = SGS$FALLBACK_WHOLE_RUN) {
  smp <- sgs_build_sample(tables, sspec, search, include_partial = include_partial)
  yrs <- sgs_sample_years(smp)
  runs <- sgs_year_runs(yrs)
  qualifying <- Filter(function(r) length(r) >= min_years, runs)
  head <- paste0("complete-case years in ", .win_text(search), ": ", sgs_years_text(yrs), "; runs of consecutive years: ",
                 .runs_text(runs))
  if (!length(qualifying)) {
    return(list(window = NULL, sample = smp, text = paste0(head, "; no run of >= ", min_years, " consecutive years")))
  }
  run <- qualifying[[length(qualifying)]]
  last <- tail(run, 1)
  window <- if (whole_run) c(run[1], last) else c(last - min_years + 1, last)
  how <- if (whole_run) "the whole run" else paste0("its most recent ", min_years, " years")
  list(window = window, sample = smp,
       text = paste0(head, "; most recent run of >= ", min_years, ": ", run[1], "-", last, "; window used: ", how, ", ",
                     .win_text(window)))
}

.no_run_attempt <- function(smp, search, min_years, search_txt) {
  reasons <- paste0("no run of >= ", min_years, " consecutive calendar years with a complete-case sample (", search_txt, ")")
  if (length(smp$diagnosis)) reasons <- c(reasons, paste0("blocking inputs: ", paste(smp$diagnosis, collapse = "; ")))
  compact <- c(paste0("no run of >= ", min_years, " consecutive complete-case years (complete-case years ",
                      sgs_years_text(sgs_sample_years(smp)), ")"), .gap_parts(smp))
  list(kind = "fallback", window = search, min_years = min_years, ok = FALSE, reasons = reasons, n = nrow(smp$df),
       years = sgs_sample_years(smp), sectors = sgs_sample_sectors(smp), resid_df = NA_integer_, sample = smp,
       design = NULL, compact_parts = compact, search = search_txt, is_search = TRUE)
}

sgs_saturation_check <- function(design) {
  if (!length(design$national)) return(list(ok = TRUE, why = ""))
  nm <- c(if (isTRUE(design$intercept_spanned)) "common level of the sector baselines", design$national)
  k <- length(nm); t <- length(unique(as.integer(design$years)))
  if (k >= t) {
    return(list(ok = FALSE, why = paste0(
      "NOT IDENTIFIED: ", k, " year-level parameters (", paste(nm, collapse = ", "), ") on ", t, " distinct years (",
      sgs_years_text(design$years), "): the national terms saturate the years (no year-level residual variation; ",
      "equivalent to year fixed effects); not forced")))
  }
  list(ok = TRUE, why = "")
}

sgs_decide_preview <- function(spec, tables, include_partial = FALSE) {
  win <- SGS$PREVIEW_WINDOW
  sspec <- sgs_sample_spec(spec)
  smp <- sgs_build_sample(tables, sspec, win, include_partial = include_partial)
  min_years <- spec$preview_min_years %||% NA_integer_
  if (length(min_years) != 1L || is.na(min_years)) min_years <- SGS$PREVIEW_MIN_YEARS
  att <- sgs_assess(smp, sspec, min_years, kind = "preview")
  if (isTRUE(spec$saturation_check) && !is.null(att$design)) {
    sc <- sgs_saturation_check(att$design)
    if (!sc$ok) {
      att$reasons <- c(sc$why, att$reasons)
      k <- sub("NOT IDENTIFIED: ", "", strsplit(sc$why, " year-level parameters", fixed = TRUE)[[1]][1], fixed = TRUE)
      att$compact_parts <- c(paste0("NOT IDENTIFIED: ", k, " year-level parameters on ", length(att$years),
                                    " distinct years (national terms saturate the years; not forced)"), att$compact_parts)
      att$ok <- FALSE
    }
  }
  if (att$ok) return(sgs_decision(SGS_ESTIMABLE, window = win, window_kind = "preview", attempts = list(att)))
  sgs_decision(SGS_NOT_ESTIMABLE, attempts = list(att), reason = sgs_attempt_text(att))
}

# Matched variants (coordinator's revision of 2026-09-26; L-LV robustness): gated on the base test's decision. The
# variant is fitted on the base test's gated sample (sgs_build_matched_sample), in the base test's window, and must pass
# the same design checks (rank, year-level terms, residual df) and the base window's minimum years (one fewer for first
# differences, which lose the first year of each run).
sgs_decide_matched <- function(spec, base_decision, built = list()) {
  for (req in spec$requires) {
    b <- built[[req]]
    if (is.null(b) || !isTRUE(b$built)) {
      return(sgs_decision(SGS_NOT_BUILT, reason = paste0("NotBuilt: ", (b$note %||% paste0("input ", req, " not built")))))
    }
  }
  batt <- if (!is.null(base_decision)) sgs_decision_chosen(base_decision) else NULL
  if (is.null(batt)) {
    st <- base_decision$status %||% "not decided"
    why <- paste0("matched to ", spec$base, ", which is ", st, ": the variant is fitted on the base test's gated sample")
    ba <- base_decision$attempts %||% list()
    win <- if (length(ba) && !is.null(ba[[length(ba)]]$window)) ba[[length(ba)]]$window else SGS$FALLBACK_SEARCH
    att <- list(kind = "matched", window = win, min_years = NA_integer_, ok = FALSE, reasons = why, n = 0L, years = numeric(0),
                sectors = character(0), resid_df = NA_integer_, sample = NULL, design = NULL,
                compact_parts = paste0("base ", spec$base, " ", st), search = "", is_search = FALSE)
    return(sgs_decision(if (identical(st, SGS_NOT_BUILT)) SGS_NOT_BUILT else SGS_NOT_ESTIMABLE, attempts = list(att), reason = why))
  }
  smp <- sgs_build_matched_sample(batt$sample, spec)
  fd <- identical(spec$matched_transform, "fd_pairs")
  att <- sgs_assess(smp, sgs_sample_spec(spec), batt$min_years - if (fd) 1L else 0L, kind = batt$kind)
  kind <- paste0(base_decision$window_kind, ", matched to ", spec$base)
  if (att$ok) {
    return(sgs_decision(SGS_ESTIMABLE, window = base_decision$window, window_kind = kind, attempts = list(att),
                        fallback_search = base_decision$fallback_search %||% ""))
  }
  sgs_decision(SGS_NOT_ESTIMABLE, attempts = list(att), reason = sgs_attempt_text(att))
}

# gates.decide. `built` (Paul's rulings): named list of list(built, note) for the inputs a test `requires`.
sgs_decide <- function(spec, tables, default_window = SGS$DEFAULT_WINDOW, fallback_search = SGS$FALLBACK_SEARCH,
                       include_partial = FALSE, whole_run = SGS$FALLBACK_WHOLE_RUN, built = list()) {
  if (identical(spec$variant, "not_built")) {
    return(sgs_decision(SGS_NOT_BUILT, reason = "NotBuilt: recipient chamber mapping not yet prepared"))
  }
  for (req in spec$requires) {
    b <- built[[req]]
    if (is.null(b) || !isTRUE(b$built)) {
      return(sgs_decision(SGS_NOT_BUILT, reason = paste0("NotBuilt: ", (b$note %||% paste0("input ", req, " not built")))))
    }
  }
  if (identical(spec$gate, "preview")) return(sgs_decide_preview(spec, tables, include_partial = include_partial))
  # SEATS (Paul's follow-up): gated on election cycles / weeks, not on the 6-year sector-year window (sgs_seats.R)
  if (identical(spec$gate, "seats")) return(sgs_decide_seats(spec, tables, include_partial = include_partial))
  if (isTRUE(spec$fallback_whole_run)) whole_run <- TRUE
  sspec <- sgs_sample_spec(spec)
  smp <- sgs_build_sample(tables, sspec, default_window, include_partial = include_partial)
  att <- sgs_assess(smp, sspec, SGS$MIN_YEARS_DEFAULT, kind = "default")
  attempts <- list(att)
  if (att$ok) return(sgs_decision(SGS_ESTIMABLE, window = default_window, window_kind = "default", attempts = attempts))
  if (is.null(fallback_search)) {
    return(sgs_decision(SGS_NOT_ESTIMABLE, attempts = attempts,
                        reason = paste(vapply(attempts, sgs_attempt_text, ""), collapse = " || ")))
  }
  fw <- sgs_fallback_window(tables, sspec, fallback_search, include_partial, SGS$MIN_YEARS_FALLBACK, whole_run)
  if (is.null(fw$window)) {
    attempts[[2]] <- .no_run_attempt(fw$sample, fallback_search, SGS$MIN_YEARS_FALLBACK, fw$text)
  } else {
    fsmp <- sgs_build_sample(tables, sspec, fw$window, include_partial = include_partial)
    fatt <- sgs_assess(fsmp, sspec, SGS$MIN_YEARS_FALLBACK, kind = "fallback")
    fatt$search <- fw$text
    attempts[[2]] <- fatt
    if (fatt$ok) {
      return(sgs_decision(SGS_ESTIMABLE, window = fw$window, window_kind = "fallback", attempts = attempts,
                          fallback_search = fw$text))
    }
  }
  sgs_decision(SGS_NOT_ESTIMABLE, attempts = attempts, reason = paste(vapply(attempts, sgs_attempt_text, ""), collapse = " || "),
               fallback_search = fw$text)
}
