# Complete-case estimation samples and design matrices (R port of code/sgs/sample.py).
#
# A value is usable when it is present and its status is observed (or 'derived'); partial rows and the partial
# calendar year (2026) never enter unless include_partial is set. Nothing is imputed, recoded or silently dropped:
# every excluded row is counted by reason, and the inputs that block whole years or whole sectors are named.

.usable <- function(frame, var) {
  ok <- !is.na(frame[[var]])
  st <- unname(SGS_STATUS_OF[var])
  if (!is.na(st) && st %in% names(frame)) ok <- ok & frame[[st]] %in% SGS_USABLE_STATUSES
  ok
}

sgs_sample_years <- function(smp) if (nrow(smp$df)) sort(unique(smp$df$year)) else numeric(0)
sgs_sample_sectors <- function(smp) if (nrow(smp$df)) sgs_sort_sectors(smp$df$study_sector) else character(0)

.sort_rows <- function(df, keys) {
  cols <- lapply(keys, function(k) if (k == "study_sector") {
    r <- match(df[[k]], SGS$STUDY_SECTORS) - 1L  # SECTOR_ORDER.map: NaN (sorted last) outside the study sectors
    r
  } else df[[k]])
  o <- do.call(order, c(cols, list(na.last = TRUE, method = "radix")))
  df[o, , drop = FALSE]
}

sgs_build_sample <- function(tables, spec, window, include_partial = FALSE) {
  tab <- tables[[spec$table]]
  if (is.null(tab)) sgs_raise("SampleError", paste0("analysis table ", spec$table, " not built"))
  if (!is.null(spec$tiers)) tab <- tab[tab$tier %in% spec$tiers, , drop = FALSE]
  if (!is.null(spec$sectors)) tab <- tab[tab$study_sector %in% spec$sectors, , drop = FALSE]
  lo <- window[1]; hi <- window[2]
  need <- sgs_required_vars(spec)
  first <- if (identical(spec$variant, "fd")) lo - 1 else lo
  frame <- tab[tab$year >= first & tab$year <= hi, , drop = FALSE]
  notes <- character(0); excl <- list()
  if (!include_partial) {
    part <- as.logical(frame$partial_year)
    if (any(part)) excl[["partial calendar year (2026)"]] <- sum(part[frame$year >= lo])
    frame <- frame[!part, , drop = FALSE]
  }
  if (identical(spec$year_filter, "election_years")) {
    odd <- frame$year %% 2 == 1
    notes <- c(notes, paste0("election years only: ", sum(odd[frame$year >= lo]), " odd-year rows outside the design"))
    frame <- frame[!odd, , drop = FALSE]
  }
  keys <- c("study_sector", "year", if ("tier" %in% names(frame) && identical(spec$table, "sector_year_tier")) "tier",
            if ("chamber" %in% names(frame) && identical(spec$table, "shift_chamber")) "chamber")
  ok <- as.data.frame(setNames(lapply(need, function(v) .usable(frame, v)), need), check.names = FALSE)
  # STRICT (coordinator's revision of 2026-09-26): a row whose expected-control value was measured after its year
  # (column <var>_after_year) leaves the sample, counted apart; a first difference needs both years in time.
  strict_ok <- NULL
  if (isTRUE(spec$strict_time)) {
    late <- rep(FALSE, nrow(frame))
    for (v in intersect(need, SGS$EXP_VARS)) {
      ay <- paste0(v, "_after_year")
      if (ay %in% names(frame)) late <- late | (frame[[ay]] %in% TRUE)
    }
    strict_ok <- !late
  }
  # SHIFT minimum base (EXPLORATORY variants only): a usable share whose nominal D + R base (spec$base_var) is below
  # spec$min_base leaves the sample; a first difference needs both years above it. The cells are recorded.
  mb <- spec$min_base %||% NA_real_
  bv <- spec$base_var %||% NA_character_
  base_ok <- NULL; small <- NULL
  if (length(mb) == 1L && !is.na(mb) && length(bv) == 1L && !is.na(bv) && bv %in% names(frame)) {
    bval <- suppressWarnings(as.numeric(frame[[bv]]))
    below <- ok[[spec$dv]] & !is.na(bval) & bval < mb
    base_ok <- !below
    small <- data.frame(study_sector = frame$study_sector[below], year = as.numeric(frame$year[below]),
                        chamber = if ("chamber" %in% names(frame)) as.character(frame$chamber[below]) else rep(NA_character_, sum(below)),
                        base_usd = bval[below], stringsAsFactors = FALSE)
    small <- small[order(sgs_sector_rank(small$study_sector), small$study_sector, small$year, small$chamber, method = "radix"), , drop = FALSE]
    rownames(small) <- NULL
  }
  if (identical(spec$variant, "fd")) {
    # difference of consecutive calendar years within sector (and tier, or chamber): the row for year t pairs with the
    # row for t-1; both levels must be usable. The lag year may precede the window. `carry` columns (SHIFT: dollar
    # bases, input flags) are kept from the year-t row, not differenced.
    carry <- setdiff(intersect(spec$carry %||% character(0), names(frame)), c(keys, need))
    cur <- cbind(frame[, c(keys, need, carry), drop = FALSE], setNames(ok, paste0("ok__", need)))
    if (!is.null(base_ok)) cur$ok__base__ <- base_ok
    if (!is.null(strict_ok)) cur$ok__strict__ <- strict_ok
    lag <- cur
    lag$year <- lag$year + 1
    m <- sgs_left_join(cur, lag, keys, suffixes = c("", "__lag"))
    d <- m[, keys, drop = FALSE]
    okd <- data.frame(row.names = seq_len(nrow(m)))
    for (v in need) {
      d[[v]] <- as.numeric(m[[v]]) - as.numeric(m[[paste0(v, "__lag")]])
      okd[[v]] <- (m[[paste0("ok__", v)]] %in% TRUE) & (m[[paste0("ok__", v, "__lag")]] %in% TRUE)
    }
    for (v in carry) d[[v]] <- m[[v]]
    if (!is.null(base_ok)) base_ok <- (m$ok__base__ %in% TRUE) & (m$ok__base____lag %in% TRUE)
    if (!is.null(strict_ok)) strict_ok <- (m$ok__strict__ %in% TRUE) & (m$ok__strict____lag %in% TRUE)
    in_win <- d$year >= lo
    frame <- d[in_win, , drop = FALSE]
    ok <- okd[in_win, , drop = FALSE]
    if (!is.null(base_ok)) base_ok <- base_ok[in_win]
    if (!is.null(strict_ok)) strict_ok <- strict_ok[in_win]
  } else if (!is.null(small)) {
    small <- small[small$year >= lo, , drop = FALSE]
  }
  rownames(frame) <- NULL
  rownames(ok) <- NULL
  cand <- nrow(frame)
  complete <- if (length(need)) Reduce(`&`, ok) else rep(TRUE, cand)
  if (!length(complete)) complete <- logical(0)
  if (!is.null(strict_ok)) {
    ns <- sum(complete & !strict_ok)
    if (ns) excl[["expected control measured after its year (STRICT)"]] <- ns
    complete <- complete & strict_ok
  }
  if (!is.null(base_ok)) {
    nb <- sum(complete & !base_ok)
    if (nb) excl[[paste0("D + R base below $", sgs_py_fixed(mb, 0, comma = TRUE), " (nominal)")]] <- nb
    complete <- complete & base_ok
  }
  for (v in need) {
    miss <- sum(!ok[[v]])
    if (miss) excl[[paste0(v, " unusable")]] <- miss
  }
  df <- frame[complete, , drop = FALSE]
  if (identical(spec$variant, "log")) {
    y0 <- as.numeric(df[[spec$dv]])
    pos <- y0 > 0
    nz <- sum(y0 == 0); nn <- sum(y0 < 0)
    if (nz || nn) {
      excl[[paste0(spec$dv, " <= 0 (log variant; zeros ", nz, ", negatives ", nn, ")")]] <- nz + nn
      notes <- c(notes, paste0("log variant: ", nz, " zero and ", nn, " negative ", spec$dv, " rows excluded, not altered"))
    }
    df <- df[pos, , drop = FALSE]
    df$y <- log(as.numeric(df[[spec$dv]]))
  } else {
    df$y <- as.numeric(df[[spec$dv]])
  }
  # rulings of 2026-09-26: a sector with one complete sector-year is left out of a fixed-effect sample (its sector fixed
  # effect absorbs the row, which carries no information but would count as a cluster)
  singletons <- character(0)
  if (isTRUE(spec$drop_singletons) && any(c("sector", "sector_x_tier") %in% spec$fe) && nrow(df)) {
    ny <- tapply(df$year, df$study_sector, function(v) length(unique(v)))
    one <- names(ny)[ny == 1]
    if (length(one)) {
      one <- sgs_sort_sectors(one)
      singletons <- setNames(vapply(one, function(s) sgs_int_str(unique(df$year[df$study_sector == s])), ""), one)
      m <- df$study_sector %in% one
      excl[["singleton sector (one complete sector-year, absorbed by its sector fixed effect)"]] <- sum(m)
      notes <- c(notes, paste0("singleton sectors left out (one complete sector-year each, absorbed by the sector fixed ",
                               "effect): ", paste(names(singletons), singletons, collapse = ", ")))
      df <- df[!m, , drop = FALSE]
    }
  }
  # SHIFT-Chamber (one baseline per unit x chamber): a unit x chamber cell with one complete row is absorbed by its
  # baseline in the same way; it is left out and named (the unit stays when its other chamber has rows)
  if (isTRUE(spec$drop_singletons) && "sector_x_chamber" %in% spec$fe && nrow(df)) {
    cell <- paste(df$study_sector, df$chamber, sep = " | ")
    ny <- tapply(df$year, cell, function(v) length(unique(v)))
    one <- names(ny)[ny == 1]
    if (length(one)) {
      one <- one[order(sgs_sector_rank(sub(" \\| .*$", "", one)), one, method = "radix")]
      m <- cell %in% one
      singletons <- c(singletons, setNames(vapply(one, function(u) sgs_int_str(unique(df$year[cell == u])), ""), one))
      excl[["singleton unit x chamber (one complete row, absorbed by its unit x chamber baseline)"]] <- sum(m)
      notes <- c(notes, paste0("singleton unit x chamber cells left out (one complete row each, absorbed by the unit x chamber ",
                               "baseline): ", paste(one, singletons[one], collapse = ", ")))
      df <- df[!m, , drop = FALSE]
    }
  }
  df <- .sort_rows(df, keys)
  rownames(df) <- NULL
  smp <- list(df = df, window = window, candidate_rows = cand, exclusions = excl, notes = notes, singletons = singletons)
  if (!is.null(small)) smp$min_base <- list(threshold = mb, var = bv, cells = small)
  smp$items <- sgs_diagnose_items(frame, ok, need, window)
  smp$diagnosis <- sgs_diagnosis_text(smp$items)
  smp
}

# Matched variants (coordinator's revision of 2026-09-26; the L-LV robustness family, as the Codex methodology review
# fitted it): the sample is the base test's gated sample (base_smp), transformed by spec$matched_transform:
#   "none"      the same rows (y = the DV as entered);
#   "log"       y = ln(DV); rows with DV <= 0 are counted and left out, never altered;
#   "fd_pairs"  the difference of consecutive calendar years both in the base sample, within sector: the row takes the
#               later year, every regressor and the DV are differenced (y = the change in the DV).
sgs_build_matched_sample <- function(base_smp, spec) {
  df <- base_smp$df
  n0 <- nrow(df)
  excl <- list()
  notes <- paste0("matched: the gated sample of ", spec$base, " (", n0, " rows)")
  tr <- spec$matched_transform %||% "none"
  if (identical(tr, "log")) {
    y0 <- as.numeric(df[[spec$dv]])
    pos <- !is.na(y0) & y0 > 0
    if (any(!pos)) {
      excl[[paste0(spec$dv, " <= 0 (log variant)")]] <- sum(!pos)
      notes <- c(notes, paste0("log variant: ", sum(!pos), " rows with ", spec$dv, " <= 0 excluded, not altered"))
    }
    df <- df[pos, , drop = FALSE]
    df$y <- log(as.numeric(df[[spec$dv]]))
  } else if (identical(tr, "fd_pairs")) {
    o <- df[order(sgs_sector_rank(df$study_sector), df$study_sector, df$year, method = "radix"), , drop = FALSE]
    prev <- match(paste(o$study_sector, o$year - 1), paste(o$study_sector, o$year))
    k <- which(!is.na(prev))
    d <- data.frame(study_sector = o$study_sector[k], year = as.numeric(o$year[k]), stringsAsFactors = FALSE)
    for (v in unique(c(spec$dv, sgs_raw_regressors(spec)))) d[[v]] <- as.numeric(o[[v]][k]) - as.numeric(o[[v]][prev[k]])
    d$y <- d[[spec$dv]]
    if (n0 - length(k)) {
      excl[["first year of a run of consecutive years in the base sample (no previous year to difference)"]] <- n0 - length(k)
    }
    notes <- c(notes, paste0("first differences: ", length(k), " pairs of consecutive years both in the base sample"))
    df <- d
  } else {
    df$y <- as.numeric(df$y)
  }
  df <- .sort_rows(df, c("study_sector", "year"))
  rownames(df) <- NULL
  list(df = df, window = base_smp$window, candidate_rows = n0, exclusions = excl, notes = notes, singletons = character(0),
       items = list(), diagnosis = character(0))
}

# Structured blockers: inputs absent for every sector in some years, years lost to scattered gaps, and sectors
# without any complete row.
sgs_diagnose_items <- function(frame, ok, need, window) {
  items <- list()
  if (!nrow(frame)) return(list(list(kind = "empty", window = window)))
  years <- sort(unique(frame$year))
  complete <- Reduce(`&`, ok)
  kept_years <- unique(frame$year[complete])
  for (v in need) {
    none_years <- years[vapply(years, function(y) !any(ok[[v]][frame$year == y]), TRUE)]
    if (length(none_years)) items[[length(items) + 1L]] <- list(kind = "var_years", var = v, years = none_years)
  }
  for (y in years[!years %in% kept_years]) {
    m <- frame$year == y
    if (!any(vapply(need, function(v) !any(ok[[v]][m]), TRUE))) {
      gaps <- list()
      for (v in need) if (any(!ok[[v]][m])) gaps[[v]] <- sum(!ok[[v]][m])
      items[[length(items) + 1L]] <- list(kind = "year_scattered", year = y, rows = sum(m), gaps = gaps)
    }
  }
  for (s in sgs_sort_sectors(frame$study_sector)) {
    m <- frame$study_sector == s
    if (!any(complete[m])) {
      items[[length(items) + 1L]] <- list(kind = "sector", sector = s,
                                          vars = need[vapply(need, function(v) !any(ok[[v]][m]), TRUE)])
    }
  }
  items
}

sgs_diagnosis_text <- function(items) {
  out <- character(0)
  for (it in items) {
    if (it$kind == "empty") {
      out <- c(out, paste0("no candidate rows in ", it$window[1], "-", it$window[2]))
    } else if (it$kind == "var_years") {
      out <- c(out, paste0(it$var, ": no usable value for any sector in ", sgs_years_text(it$years)))
    } else if (it$kind == "year_scattered") {
      gaps <- paste(paste0(names(it$gaps), " (", unlist(it$gaps), " of ", it$rows, " rows)"), collapse = ", ")
      out <- c(out, paste0(sgs_int_str(it$year), ": no row complete; gaps ", gaps))
    } else if (it$kind == "sector") {
      if (length(it$vars)) {
        out <- c(out, paste0("sector ", it$sector, " never complete: ", paste(it$vars, collapse = ", "), " unusable throughout"))
      } else {
        out <- c(out, paste0("sector ", it$sector, " never complete: gaps do not line up in any year"))
      }
    }
  }
  out
}

# sample.Design as a list: y, X (n x p), names, clusters (0-based index), cluster_labels, years, national,
# intercept_spanned, nested_fe.
sgs_build_design <- function(df, spec) {
  cols <- list(); nms <- character(0)
  add <- function(v, name) { cols[[length(cols) + 1L]] <<- as.numeric(v); nms <<- c(nms, name) }
  if (identical(spec$variant, "tier")) {
    for (it in spec$interactions) if (!it[1] %in% nms) add(df[[it[1]]], it[1])
    for (it in spec$interactions) add(as.numeric(df[[it[1]]]) * as.numeric(df$tier == it[2]), paste0(it[1], ":", it[2]))
    for (c in spec$controls) add(df[[c]], c)
  } else if (identical(spec$variant, "sector_interaction")) {
    # growth x one unit (bank-only models: g + g:community_banks)
    for (it in spec$interactions) if (!it[1] %in% nms) add(df[[it[1]]], it[1])
    for (it in spec$interactions) add(as.numeric(df[[it[1]]]) * as.numeric(df$study_sector == it[2]), paste0(it[1], ":", it[2]))
    for (c in spec$controls) add(df[[c]], c)
  } else if (identical(spec$variant, "slopes")) {
    # one term per sector for every focal variable (SLOPES, CONTRACT-b, ASYM-SLOPES): v:<sector>, no common term. A
    # variable that does not vary within a sector (e.g. no contraction year) has no estimable term there: that column
    # is left out and named in unestimable (lm() prints it as NA)
    unest <- character(0)
    for (v in spec$focal) for (s in sgs_sort_sectors(df$study_sector)) {
      m <- df$study_sector == s
      x <- as.numeric(df[[v]])
      if (length(unique(x[m])) < 2L) { unest <- c(unest, paste0(v, ":", s)); next }
      add(x * as.numeric(m), paste0(v, ":", s))
    }
    for (c in spec$controls) add(df[[c]], c)
  } else {
    for (c in sgs_raw_regressors(spec)) add(df[[c]], c)
  }
  sectors <- sgs_sort_sectors(df$study_sector)
  if ("sector" %in% spec$fe) for (s in sectors) add(df$study_sector == s, paste0("FE:", s))
  if ("sector_x_tier" %in% spec$fe) {
    for (s in sectors) for (t in SGS$TIERS) {
      m <- df$study_sector == s & df$tier == t
      if (any(m)) add(m, paste0("FE:", s, "|", t))
    }
  }
  if ("sector_x_chamber" %in% spec$fe) {
    # SHIFT-Chamber: one baseline per unit x chamber (spans the unit baselines, the chamber baseline and their interaction)
    for (s in sectors) for (ch in c("House", "Senate")) {
      m <- df$study_sector == s & df$chamber == ch
      if (any(m)) add(m, paste0("FE:", s, "|", ch))
    }
  }
  if ("year" %in% spec$fe) {
    ys <- sort(unique(df$year))
    for (y in ys[-1]) add(df$year == y, paste0("YFE:", sgs_int_str(y)))
  }
  if ("year_full" %in% spec$fe) {
    # first differences with year effects (no sector baselines): one dummy per year, i.e. an intercept plus year effects
    for (y in sort(unique(df$year))) add(df$year == y, paste0("YFE:", sgs_int_str(y)))
  }
  if ("intercept" %in% spec$fe) {
    # SEATS-A lagged-allocation model: a common level without unit baselines (the prior-cycle share carries the unit)
    add(rep(1, nrow(df)), "FE:(common)")
  }
  if ("cycle_trend" %in% spec$fe) {
    # SEATS-W: a linear trend in week-of-cycle for every election cycle present (cycle x week-of-cycle controls)
    for (y in sort(unique(df$year))) add(as.numeric(df$week_of_cycle) * (df$year == y), paste0("TREND:", sgs_int_str(y)))
  }
  X <- if (length(cols)) matrix(unlist(cols), nrow = nrow(df), ncol = length(cols)) else matrix(0, nrow(df), 0)
  colnames(X) <- nms
  d <- list(y = as.numeric(df$y), X = X, names = nms, clusters = match(df$study_sector, sectors) - 1L,
            cluster_labels = sectors, years = as.numeric(df$year), national = nms[nms %in% SGS$NATIONAL_VARS],
            intercept_spanned = length(spec$fe) > 0, nested_fe = 0L)
  if (identical(spec$variant, "slopes")) d$unestimable <- unest
  if (isTRUE(spec$identification)) {
    # SHIFT: the cells that identify the year-level terms (years; year x chamber in the stacked table), the regressors
    # constant within cells, and the cell-level levels the baselines span (the gate checks the cell-level design)
    stacked <- "chamber" %in% names(df) && identical(spec$table, "shift_chamber")
    d$cells <- if (stacked) paste(sgs_int_str(df$year), df$chamber) else sgs_int_str(df$year)
    isfe <- startsWith(nms, "FE:") | startsWith(nms, "YFE:")
    d$cell_vars <- nms[!isfe & vapply(seq_along(nms), function(j) {
      if (!nrow(X)) return(FALSE)
      r <- tapply(X[, j], d$cells, function(v) max(v) - min(v))
      all(r <= 1e-12 * max(1, max(abs(X[, j]))))
    }, TRUE)]
    d$cell_spanned <- c(if (length(spec$fe)) "common level", if ("sector_x_chamber" %in% spec$fe) "chamber level")
  }
  # weighted variants (SHIFT-*-W): the row weights; sgs_weighted_design applies them at estimation, so the gates see the
  # unweighted design (positive row weights leave every rank unchanged)
  w <- spec$weight_var %||% NA_character_
  if (length(w) == 1L && !is.na(w)) d$w <- as.numeric(df[[w]])
  d
}

# Weighted least squares as OLS on sqrt(w)-scaled rows: the CR1 errors and the wild cluster restricted bootstrap of the
# scaled model are those of the weighted model (weights = the party-labelled dollars of SHIFT-*-W). Unweighted designs
# pass through unchanged.
sgs_weighted_design <- function(d) {
  if (is.null(d$w) || isTRUE(d$weighted)) return(d)
  if (length(d$w) != nrow(d$X) || any(!is.finite(d$w)) || any(d$w <= 0)) {
    sgs_raise("EstimationError", "weights must be positive and finite for every row")
  }
  sw <- sqrt(d$w)
  d$X <- d$X * sw
  colnames(d$X) <- d$names
  d$y <- d$y * sw
  d$weighted <- TRUE
  d
}
