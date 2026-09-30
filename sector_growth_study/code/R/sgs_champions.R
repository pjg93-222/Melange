# H5: champions' race toughness and industry money (05_industry_champions.xlsx, sheet `data`; R port of
# code/sgs/champions.py). Unit: board x champion x cycle.
#
# Loading happens at run time only (never cached). Every H5 test is NOT BUILT, with the reason, when
#   * 05_industry_champions.xlsx or build_receipt_05.json is missing (the receipt path is a run argument; default:
#     the parent of the input folder),
#   * the receipt or the workbook was written less than 10 minutes ago (05 is being rewritten), or either changed while
#     being read,
#   * the bytes read differ from the sha256 the receipt records for 05,
#   * the workbook fails validation (unreadable, formula-like cell, duplicate key board x bioguide x cycle),
#   * an expected column (the required columns, or every dependent-variable candidate) is missing.
# A single test is NOT BUILT when only its own column is missing (the sensitivity DV, a secondary regressor).
# The workbook is read into memory in one call and parsed from that copy: no handle stays open on a file that
# another lane may be replacing.
# Dependent variable: industry_money_primary_real_2025_usd if 05 has it, else direct_giving_real_2025_usd
# ("employee channel only"). Sample: up_for_election = 1; lost_primary = 1 rows only in the primary models. Design:
# focal; chamber, party (each other party vs R), seniority_years; cycle and board fixed effects; H5-within adds
# champion fixed effects. Columns adding no rank are dropped and named. Gate: >= 3 cycles, >= 30 member-cycles,
# non-zero focal variance (within champion for H5-within), focal identified, residual df >= 3, >= 2 champions.

SGS_H5_UNIT <- "board x champion x cycle"

.num <- function(v) suppressWarnings(as.numeric(v))

sgs_load_champions <- function(data_dir = SGS$DATA_DIR, now = NULL, quiet_minutes = SGS$CHAMPIONS_QUIET_MINUTES,
                               receipt_path = NULL) {
  path <- file.path(data_dir, SGS$CHAMPIONS_FILE)
  rpath <- receipt_path %||% file.path(dirname(normalizePath(data_dir, winslash = "/", mustWork = FALSE)), SGS$CHAMPIONS_RECEIPT)
  now <- now %||% as.numeric(Sys.time())
  pname <- basename(path); rname <- basename(rpath)
  rec <- list(file = pname, workbook = "champions",
              absolute_path = normalizePath(path, winslash = "\\", mustWork = FALSE), sha256 = NA_character_,
              size_bytes = NA_real_, mtime_utc = NA_character_, read_at_utc = sgs_utc_iso(now), sheets_read = "",
              rows_read = "", note = "")
  not_built <- function(reason) {
    rec$note <- paste0("NOT BUILT: ", reason)
    list(ok = FALSE, reason = reason, frame = NULL, source = rec, notes = character(0), documented = character(0),
         receipt_path = rpath)
  }
  if (!file.exists(path)) return(not_built(paste0(pname, " not found at ", normalizePath(path, winslash = "\\", mustWork = FALSE))))
  if (!file.exists(rpath)) {
    return(not_built(paste0(rname, " not found at ", normalizePath(rpath, winslash = "\\", mustWork = FALSE),
                            ": cannot confirm that 05 is not being rewritten")))
  }
  r_mt <- sgs_mtime(rpath); f_mt <- sgs_mtime(path)
  rec$size_bytes <- as.numeric(file.info(path)$size)
  rec$mtime_utc <- sgs_utc_iso(f_mt)
  r_age <- (now - r_mt) / 60; f_age <- (now - f_mt) / 60
  if (r_age < quiet_minutes) {
    return(not_built(paste0(rname, " was written ", sgs_py_fixed(r_age, 1), " min ago (< ", sgs_py_g(quiet_minutes, 6),
                            " min): 05 is being rewritten")))
  }
  if (f_age < quiet_minutes) {
    return(not_built(paste0(pname, " was modified ", sgs_py_fixed(f_age, 1), " min ago (< ", sgs_py_g(quiet_minutes, 6),
                            " min): 05 is being rewritten")))
  }
  got <- tryCatch({
    receipt <- jsonlite::fromJSON(rpath, simplifyVector = FALSE)
    raw <- readBin(path, "raw", file.info(path)$size)
    list(receipt = receipt, raw = raw)
  }, error = function(e) e)
  if (inherits(got, "error")) return(not_built(paste0("05 or its receipt unreadable (", class(got)[1], ": ", conditionMessage(got), ")")))
  receipt <- got$receipt; raw <- got$raw
  sha <- sgs_sha256_raw(raw)
  rec$sha256 <- sha
  if (sgs_mtime(rpath) != r_mt || sgs_mtime(path) != f_mt) return(not_built("05 or its receipt changed while being read: 05 is being rewritten"))
  want <- NULL
  for (k in c("target", "file")) {
    v <- receipt[[k]]
    if (is.list(v) && !is.null(v$sha256) && nzchar(v$sha256)) { want <- v$sha256; break }
  }
  notes <- character(0)
  if (is.null(want)) {
    notes <- c(notes, paste0(rname, " records no sha256 for 05; bytes not compared with the receipt"))
  } else if (!identical(want, sha)) {
    return(not_built(paste0(pname, " sha256 ", substr(sha, 1, 16), " differs from the receipt's ", substr(want, 1, 16),
                            ": 05 changed after its receipt was written")))
  } else {
    notes <- c(notes, paste0("05 bytes equal the receipt's sha256 (", substr(sha, 1, 16), "); receipt run_id ",
                             receipt$run_id %||% "None", ", written_at ", receipt$written_at %||% "None"))
  }
  tmp <- tempfile("sgs05_", fileext = ".xlsx")
  on.exit(unlink(tmp), add = TRUE)
  writeBin(raw, tmp)
  parsed <- tryCatch({
    present <- sgs_values_only_guard(tmp, pname)
    if (!"data" %in% present) {
      list(missing_data = paste0(pname, " [data]: sheet missing (present: ", sgs_py_list_repr(sort(present, method = "radix")), ")"))
    } else {
      raw_d <- .read_sheet_raw(tmp, "data")
      frame <- sgs_frame_from_raw(raw_d, pname, "data")
      dic <- if ("dictionary" %in% present) sgs_frame_from_raw(.read_sheet_raw(tmp, "dictionary"), pname, "dictionary") else NULL
      list(frame = frame, dic = dic, present = present, n_data = nrow(raw_d) - 1L,
           n_dic = if (!is.null(dic)) attr(dic, "raw_rows") - 1L else NA)
    }
  }, error = function(e) e)
  if (inherits(parsed, "error")) {
    cls <- setdiff(class(parsed), c("error", "condition", "simpleError"))[1]
    if (is.na(cls)) cls <- "Error"
    return(not_built(paste0(pname, " failed to load: ", cls, ": ", conditionMessage(parsed))))
  }
  if (!is.null(parsed$missing_data)) return(not_built(parsed$missing_data))
  frame <- parsed$frame
  missing <- SGS$H5_REQUIRED[!SGS$H5_REQUIRED %in% names(frame)]
  if (!any(SGS$H5_DV_PRIMARY %in% names(frame))) missing <- c(missing, paste(SGS$H5_DV_PRIMARY, collapse = " or "))
  if (length(missing)) return(not_built(paste0("expected columns missing from ", pname, " [data]: ", paste(missing, collapse = ", "))))
  v <- tryCatch(sgs_validate_frame(frame, .sheet_spec(SGS$H5_REQUIRED, SGS$H5_KEY), pname, "data"), error = function(e) e)
  if (inherits(v, "error")) return(not_built(conditionMessage(v)))
  frame <- v
  documented <- character(0)
  if (!is.null(parsed$dic) && all(c("sheet", "column") %in% names(parsed$dic))) {
    documented <- as.character(parsed$dic$column[parsed$dic$sheet %in% "data"])
  } else {
    notes <- c(notes, "05 has no readable dictionary sheet; columns taken from the data header")
  }
  sheets_read <- c("data", "dictionary")[c("data", "dictionary") %in% parsed$present]
  rows_read <- c(paste0("data=", parsed$n_data), if ("dictionary" %in% parsed$present) paste0("dictionary=", parsed$n_dic))
  rec$sheets_read <- paste(sheets_read, collapse = ", ")
  rec$rows_read <- paste(rows_read, collapse = ", ")
  rec$note <- paste0("read at run time; ", paste(notes, collapse = "; "))
  list(ok = TRUE, reason = "", frame = frame, source = rec, notes = notes, documented = documented, receipt_path = rpath)
}

sgs_resolve_dv <- function(cd, role) {
  cands <- if (identical(role, "industry_money_primary")) SGS$H5_DV_PRIMARY else SGS$H5_DV_TRADE
  for (c in cands) {
    if (c %in% names(cd$frame)) {
      flag <- if (identical(c, "direct_giving_real_2025_usd")) SGS$H5_DV_FALLBACK_FLAG else ""
      return(list(col = c, label = unname(SGS$H5_DV_LABELS[c]) %||% c, flag = flag, reason = ""))
    }
  }
  list(col = NA_character_, label = "", flag = "",
       reason = paste0("dependent variable absent from 05 [data]: none of ", paste(cands, collapse = ", ")))
}

sgs_dv_status_column <- function(cd, dv_col) {
  st <- sub("_real_2025_usd", "_status", dv_col, fixed = TRUE)
  if (st %in% names(cd$frame) && st != dv_col) st else NA_character_
}

sgs_h5_cycles <- function(smp) if (nrow(smp$df)) sort(unique(as.integer(smp$df$cycle))) else integer(0)
sgs_h5_champions <- function(smp) if (nrow(smp$df)) sgs_sorted(smp$df$bioguide) else character(0)
sgs_h5_member_cycles <- function(smp) if (nrow(smp$df)) nrow(unique(smp$df[, c("bioguide", "cycle")])) else 0L
sgs_h5_boards <- function(smp) if (nrow(smp$df)) sgs_sorted(smp$df$board) else character(0)

sgs_build_h5_sample <- function(cd, spec, dv_col, dv_label, dv_flag) {
  df <- cd$frame
  df$cycle <- .num(df$cycle)
  excl <- list(); notes <- character(0)
  up <- .num(df$up_for_election) %in% 1
  excl[["up_for_election != 1 (not up for election, including the retiring rows)"]] <- sum(!up)
  df <- df[up, , drop = FALSE]
  lost <- .num(df$lost_primary) %in% 1
  if (isTRUE(spec$keep_lost_primary)) {
    notes <- c(notes, paste0("lost-renomination rows kept (primary model): ", sum(lost)))
  } else {
    excl[["lost_primary = 1 (lost renomination; such rows enter only the primary models)"]] <- sum(lost)
    df <- df[!lost, , drop = FALSE]
  }
  if (length(spec$drop_cycles)) {
    m <- df$cycle %in% spec$drop_cycles
    excl[[paste0("cycle ", paste(sgs_int_str(spec$drop_cycles), collapse = ", "), " excluded by the specification")]] <- sum(m)
    df <- df[!m, , drop = FALSE]
  }
  cand <- nrow(df)
  ok <- list()
  dv <- .num(df[[dv_col]])
  row_ok <- df$status %in% SGS$H5_USABLE_ROW_STATUS
  st_col <- sgs_dv_status_column(cd, dv_col)
  st_ok <- if (!is.na(st_col)) df[[st_col]] %in% SGS$H5_USABLE_DV_STATUS else rep(TRUE, nrow(df))
  ok[[dv_col]] <- !is.na(dv) & row_ok & st_ok
  bad <- !ok[[dv_col]]
  if (any(bad)) {
    a <- as.character(df$status[bad]); a[is.na(a)] <- "nan"
    b <- if (!is.na(st_col)) as.character(df[[st_col]][bad]) else rep("-", sum(bad))
    b[is.na(b)] <- "nan"
    pairs <- unique(data.frame(a = a, b = b, stringsAsFactors = FALSE))
    pairs <- pairs[order(pairs$a, pairs$b, method = "radix"), , drop = FALSE]
    cnt <- vapply(seq_len(nrow(pairs)), function(i) sum(a == pairs$a[i] & b == pairs$b[i]), 0)
    notes <- c(notes, paste0(dv_col, " unusable by (row status / ", if (!is.na(st_col)) st_col else "no DV status column", "): ",
                             paste0(pairs$a, "/", pairs$b, ": ", cnt, collapse = "; ")))
  }
  for (f in spec$focal) ok[[f]] <- !is.na(.num(df[[f]]))
  for (c in spec$controls) {
    if (c == "chamber") ok[[c]] <- df[[c]] %in% c("House", "Senate")
    else if (c == "party") ok[[c]] <- !is.na(df[[c]]) & trimws(as.character(df[[c]])) != ""
    else ok[[c]] <- !is.na(.num(df[[c]]))
  }
  avail <- lapply(ok, function(o) sort(unique(as.integer(df$cycle[o & !is.na(df$cycle)]))))
  for (v in names(ok)) {
    k <- sum(!ok[[v]])
    if (k) excl[[paste0(v, " unusable")]] <- k
  }
  all_ok <- Reduce(`&`, ok)
  out <- df[all_ok, , drop = FALSE]
  y <- .num(out[[dv_col]])
  if (identical(spec$dv_transform, "log1p")) {
    neg <- y < 0
    if (any(neg)) excl[["DV < 0 (log1p variant; excluded, never altered)"]] <- sum(neg)
    out <- out[!neg, , drop = FALSE]; y <- y[!neg]
    out$y <- log1p(y)
  } else if (identical(spec$dv_transform, "any")) {
    out$y <- as.numeric(y > 0)
  } else {
    out$y <- y
  }
  for (f in spec$focal) out[[f]] <- .num(out[[f]])
  if ("seniority_years" %in% names(out)) out$seniority_years <- .num(out$seniority_years) else out$seniority_years <- NA_real_
  out <- out[order(out$board, out$bioguide, out$cycle, method = "radix"), , drop = FALSE]
  rownames(out) <- NULL
  list(df = out, dv_col = dv_col, dv_label = dv_label, dv_flag = dv_flag, candidate_rows = cand, exclusions = excl,
       notes = notes, availability = avail)
}

sgs_build_h5_design <- function(df, spec) {
  cols <- list(); nms <- character(0); kinds <- character(0)
  add <- function(v, name, kind) { cols[[length(cols) + 1L]] <<- as.numeric(v); nms <<- c(nms, name); kinds <<- c(kinds, kind) }
  champs <- sgs_sorted(df$bioguide)
  if ("champion" %in% spec$fe) for (b in champs) add(df$bioguide == b, paste0("FE:champion=", b), "champion_fe")
  if ("board" %in% spec$fe) for (b in sgs_sorted(df$board)) add(df$board == b, paste0("FE:board=", b), "fe")
  if (!"champion" %in% spec$fe && !"board" %in% spec$fe) add(rep(1, nrow(df)), "FE:constant", "fe")
  if ("cycle" %in% spec$fe) {
    cyc <- sort(unique(df$cycle))
    for (c in cyc[-1]) add(df$cycle == c, paste0("YFE:cycle=", sgs_int_str(c)), "fe")
  }
  for (c in spec$controls) {
    if (c == "chamber") {
      add(df$chamber == "Senate", "chamber=Senate", "control")
    } else if (c == "party") {
      pv <- as.character(df$party)
      for (lvl in setdiff(sgs_sorted(pv), SGS$H5_PARTY_REFERENCE)) add(pv == lvl, paste0("party=", lvl), "control")
    } else {
      add(df[[c]], c, "control")
    }
  }
  for (f in spec$focal) add(df[[f]], f, "focal")
  X <- if (length(cols)) matrix(unlist(cols), nrow = nrow(df), ncol = length(cols)) else matrix(0, nrow(df), 0)
  colnames(X) <- nms
  dep <- if (nrow(df)) sgs_dependent_columns(X, nms) else nms
  # near-collinearity rule (rule set paul-2026-09-25, rulings of 2026-09-26): after the exact dependencies, a control
  # whose R^2 on the fixed effects plus the other regressors is >= spec$near_collinear_r2 is dropped and named too
  near <- list(dropped = character(0), r2 = numeric(0))
  thr <- spec$near_collinear_r2 %||% NA_real_
  if (nrow(df) && length(thr) == 1L && is.finite(thr)) {
    k0 <- which(!nms %in% dep)
    near <- sgs_near_collinear_columns(X[, k0, drop = FALSE], nms[k0][kinds[k0] == "control"], thr)
  }
  keep <- which(!nms %in% c(dep, near$dropped))
  info <- list(dropped_controls = nms[nms %in% dep & kinds == "control"],
               absorbed_fe = nms[nms %in% dep & kinds %in% c("fe", "champion_fe")],
               near_collinear_controls = near$dropped, near_collinear_r2 = near$r2,
               near_collinear_threshold = if (length(thr) == 1L && is.finite(thr)) thr else NA_real_,
               focal_identified = all(!spec$focal %in% dep),
               champion_fe = sum(kinds[keep] == "champion_fe"))
  Xk <- X[, keep, drop = FALSE]
  design <- list(y = as.numeric(df$y), X = Xk, names = nms[keep], clusters = match(df$bioguide, champs) - 1L,
                 cluster_labels = champs, years = as.numeric(df$cycle), national = character(0), intercept_spanned = TRUE,
                 nested_fe = info$champion_fe)
  list(design = design, info = info)
}

.h5_decision <- function(status, reason = "", reason_short = "", sample = NULL, design = NULL, info = list(),
                         dv_col = "", dv_label = "", dv_flag = "", resid_df = NA_integer_, identifying_champions = NA_integer_) {
  list(status = status, reason = reason, reason_short = reason_short, sample = sample, design = design, info = info,
       dv_col = dv_col, dv_label = dv_label, dv_flag = dv_flag, resid_df = resid_df,
       identifying_champions = identifying_champions)
}

sgs_decide_h5 <- function(spec, cd) {
  if (is.null(cd) || !isTRUE(cd$ok)) {
    why <- if (!is.null(cd)) cd$reason else "05 not loaded"
    return(.h5_decision(SGS_NOT_BUILT, reason = paste0("NotBuilt: ", why), reason_short = paste0("NotBuilt: ", why)))
  }
  dv <- sgs_resolve_dv(cd, spec$dv)
  if (is.na(dv$col)) return(.h5_decision(SGS_NOT_BUILT, reason = paste0("NotBuilt: ", dv$reason), reason_short = paste0("NotBuilt: ", dv$reason)))
  absent <- spec$focal[!spec$focal %in% names(cd$frame)]
  if (length(absent)) {
    why <- paste0("column ", paste(absent, collapse = ", "), " absent from 05 [data]")
    return(.h5_decision(SGS_NOT_BUILT, reason = paste0("NotBuilt: ", why), reason_short = paste0("NotBuilt: ", why),
                        dv_col = dv$col, dv_label = dv$label, dv_flag = dv$flag))
  }
  smp <- sgs_build_h5_sample(cd, spec, dv$col, dv$label, dv$flag)
  reasons <- character(0); short <- character(0)
  cyc <- sgs_h5_cycles(smp); mc <- sgs_h5_member_cycles(smp)
  if (length(cyc) < SGS$H5_MIN_CYCLES) {
    reasons <- c(reasons, paste0(length(cyc), " cycles (", sgs_cycles_text(cyc), ") < ", SGS$H5_MIN_CYCLES, " required"))
    short <- c(short, paste0(length(cyc), " of ", SGS$H5_MIN_CYCLES, " cycles (", sgs_cycles_text(cyc), ")"))
  }
  if (mc < SGS$H5_MIN_MEMBER_CYCLES) {
    reasons <- c(reasons, paste0(mc, " member-cycles < ", SGS$H5_MIN_MEMBER_CYCLES, " required"))
    short <- c(short, paste0(mc, " of ", SGS$H5_MIN_MEMBER_CYCLES, " member-cycles"))
  }
  within <- "champion" %in% spec$fe
  ident <- NA_integer_
  design <- NULL; info <- list(); resid_df <- NA_integer_
  n <- nrow(smp$df)
  if (n) {
    for (f in spec$focal) {
      v <- smp$df[[f]]
      if (within) {
        dev <- v - ave(v, smp$df$bioguide, FUN = mean)
        ident <- sum(tapply(v, smp$df$bioguide, function(z) length(unique(z)) > 1))
        if (mean((dev - mean(dev))^2) <= 0) {
          reasons <- c(reasons, paste0(f, ": zero within-champion variance (no champion's value varies across cycles)"))
          short <- c(short, paste0(f, " has no within-champion variation"))
        }
      } else if (mean((v - mean(v))^2) <= 0) {
        reasons <- c(reasons, paste0(f, ": zero variance in the sample"))
        short <- c(short, paste0(f, " has zero variance"))
      }
    }
    bd <- sgs_build_h5_design(smp$df, spec)
    design <- bd$design; info <- bd$info
    if (!info$focal_identified) {
      reasons <- c(reasons, paste0("focal ", paste(spec$focal, collapse = ", "), " not identified given the fixed effects and controls"))
      short <- c(short, "focal not identified")
    }
    resid_df <- nrow(design$X) - sgs_rank_of(design$X)
    if (resid_df < SGS$MIN_RESID_DF) {
      reasons <- c(reasons, paste0("residual df ", resid_df, " < ", SGS$MIN_RESID_DF))
      short <- c(short, paste0("resid df ", resid_df))
    }
    if (length(sgs_h5_champions(smp)) < 2) reasons <- c(reasons, paste0(length(sgs_h5_champions(smp)), " champion cluster(s) < 2"))
  } else {
    reasons <- c(reasons, "complete-case sample is empty")
    short <- c(short, "empty complete-case sample")
  }
  if (length(reasons)) {
    vv <- names(smp$availability)[names(smp$availability) %in% c(dv$col, spec$focal)]
    av <- paste(vapply(vv, function(v) paste0(v, " usable in cycles ", sgs_cycles_text(smp$availability[[v]])), ""), collapse = "; ")
    reasons <- c(reasons, paste0("availability among up-for-election rows: ", av))
    short <- c(short, av)
  }
  .h5_decision(if (length(reasons)) SGS_NOT_ESTIMABLE else SGS_ESTIMABLE, reason = paste(reasons, collapse = "; "),
               reason_short = paste(short, collapse = "; "), sample = smp, design = design, info = info, dv_col = dv$col,
               dv_label = dv$label, dv_flag = dv$flag, resid_df = resid_df, identifying_champions = ident)
}

sgs_h5_unit_of <- function(spec, coef) {
  base <- c(level = "USD 2025", log1p = "log1p points of USD 2025", any = "probability (0-1) of any money > 0")[[spec$dv_transform]]
  u <- c(toughness_general = paste0(base, " per point of toughness_general (0 safe ... 3 toss-up)"),
         primary_contested = paste0(base, ", contested vs uncontested primary"),
         primary_margin = paste0(base, " per unit of primary margin (vote share 0-1)"),
         general_margin = paste0(base, " per unit of general-election margin (vote share 0-1)"))
  if (coef %in% names(u)) unname(u[coef]) else paste0(base, " per unit of ", coef)
}

.h5_flags <- function(spec, d) paste(Filter(nzchar, c(d$dv_flag, spec$flag)), collapse = "; ")

sgs_fit_h5_strata <- function(spec, smp, coef) {
  rows <- list()
  sspec <- spec; sspec$fe <- setdiff(spec$fe, "board")
  for (b in sgs_h5_boards(smp)) {
    sub <- smp$df[smp$df$board == b, , drop = FALSE]
    rownames(sub) <- NULL
    base <- list(board = b, coefficient = coef, n = nrow(sub), cycles = sgs_cycles_text(sub$cycle),
                 n_champions = length(unique(sub$bioguide)))
    bd <- sgs_build_h5_design(sub, sspec)
    rdf <- nrow(bd$design$X) - sgs_rank_of(bd$design$X)
    base$resid_df <- rdf
    if (!bd$info$focal_identified) {
      rows[[length(rows) + 1L]] <- c(base, list(status = "insufficient", reason = "focal not identified within the board"))
      next
    }
    if (rdf < SGS$MIN_STRATUM_RESID_DF) {
      rows[[length(rows) + 1L]] <- c(base, list(status = "insufficient", reason = paste0("residual df ", rdf, " < ", SGS$MIN_STRATUM_RESID_DF)))
      next
    }
    f <- sgs_ols(bd$design)
    k <- match(coef, f$names)
    rows[[length(rows) + 1L]] <- c(base, list(status = "estimated", estimate = f$beta[k], hc1_se = f$se_hc1[k],
                                              cr1_se = f$se_cr1[k], reason = ""))
  }
  rows
}

sgs_estimate_h5 <- function(spec, d, B = SGS$BOOT_B, seed = SGS$SEED, alpha = SGS$ALPHA) {
  res <- list(coefs = list(), strata = list(), subfits = list(), notes = character(0), descriptive = FALSE)
  fit <- sgs_ols(d$design)
  for (c in spec$focal) {
    res$strata <- c(res$strata, sgs_fit_h5_strata(spec, d$sample, c))
    row <- sgs_boot_coefficient(d$design, fit, c, B, sgs_seed_entropy(seed, spec$id, c), alpha)
    row <- c(row, list(unit = sgs_h5_unit_of(spec, c), focal = TRUE, flag = .h5_flags(spec, d),
                       inference = "wild cluster restricted bootstrap by champion (bioguide), Webb weights; CR1 by champion",
                       stratification = sgs_stratification_label(res$strata, c, "boards", "board")))
    res$coefs[[length(res$coefs) + 1L]] <- row
  }
  res
}

sgs_h5_est_row <- function(spec, d) {
  smp <- d$sample
  info <- d$info %||% list()
  notes <- character(0)
  if (length(info$dropped_controls)) notes <- c(notes, paste0("controls not identified and dropped: ", paste(info$dropped_controls, collapse = ", ")))
  if (length(info$near_collinear_controls)) {
    notes <- c(notes, paste0("controls nearly collinear with the fixed effects and the other regressors (R^2 >= ",
                             sgs_py_repr_float(info$near_collinear_threshold), ") and dropped: ",
                             paste0(info$near_collinear_controls, " (R^2 ", vapply(info$near_collinear_r2, sgs_py_fixed, "", d = 7), ")",
                                    collapse = ", ")))
  }
  if (length(info$absorbed_fe)) {
    af <- info$absorbed_fe
    notes <- c(notes, paste0("fixed-effect columns absorbed: ", length(af), " (", paste(head(af, 6), collapse = ", "),
                             if (length(af) > 6) ", ..." else "", ")"))
  }
  if (!is.na(d$identifying_champions)) {
    notes <- c(notes, paste0("champions whose ", paste(spec$focal, collapse = ", "), " varies across cycles: ", d$identifying_champions))
  }
  excl <- if (!is.null(smp)) paste(c(sgs_kv(smp$exclusions), smp$notes), collapse = "; ") else ""
  est <- identical(d$status, SGS_ESTIMABLE)
  cyc <- if (!is.null(smp)) sgs_h5_cycles(smp) else integer(0)
  list(test_id = spec$id, family = spec$family, label = spec$label, status = d$status,
       window_used = if (est) paste0("cycles ", sgs_cycles_text(cyc)) else "", window_kind = if (est) "member-cycle gate" else "",
       n = if (!is.null(smp)) nrow(smp$df) else NA, n_window = if (!is.null(smp)) "cycles" else "", n_sectors = NA, sectors = "",
       n_years = if (!is.null(smp)) length(cyc) else NA, years = if (!is.null(smp)) sgs_cycles_text(cyc) else "",
       resid_df = d$resid_df, reason = if (!est) d$reason else "", reason_short = if (!est) d$reason_short else "",
       default_attempt = "", fallback_attempt = "", fallback_search = "", exclusions = excl, dv = spec$dv,
       dv_column = d$dv_col, dv_label = d$dv_label, focal = paste(spec$focal, collapse = ", "),
       controls = paste(spec$controls, collapse = ", "), fixed_effects = paste(spec$fe, collapse = ", "),
       variant = paste0(spec$variant, " (", spec$dv_transform, ")"), base_test = if (is.na(spec$base)) "" else spec$base,
       year_filter = "", tiers = "",
       # the parity rule set joins the notes with a space, as Python does; Paul's rule set (which may add the
       # near-collinearity note) separates them with "; " so each reads on its own
       note = paste0(spec$note, if (length(notes)) {
         if (is.finite(info$near_collinear_threshold %||% NA_real_)) paste0(" ", paste(notes, collapse = "; "), ".")
         else paste0(" ", paste(notes, collapse = " "))
       } else ""),
       unit = SGS_H5_UNIT, n_champions = if (!is.null(smp)) length(sgs_h5_champions(smp)) else NA,
       n_member_cycles = if (!is.null(smp)) sgs_h5_member_cycles(smp) else NA,
       boards = if (!is.null(smp)) paste(sgs_h5_boards(smp), collapse = ", ") else "", cluster_by = "bioguide (champion)",
       n_clusters = if (!is.null(smp)) length(sgs_h5_champions(smp)) else NA, gate_rule = spec$window_rule,
       inference = if (identical(spec$inference, "wcr")) "wild cluster restricted bootstrap by champion" else spec$inference,
       flag = .h5_flags(spec, d), input_flags = "")
}

sgs_h5_coef_rows <- function(spec, d, res) {
  smp <- d$sample
  cyc <- sgs_h5_cycles(smp)
  lapply(res$coefs, function(c) {
    c(c, list(test_id = spec$id, label = spec$label, source_test = "", window_used = paste0("cycles ", sgs_cycles_text(cyc)),
              n = nrow(smp$df), n_sectors = NA, n_years = length(cyc), years = sgs_cycles_text(cyc),
              unit_of_analysis = SGS_H5_UNIT, n_champions = length(sgs_h5_champions(smp)),
              n_member_cycles = sgs_h5_member_cycles(smp), cycles = sgs_cycles_text(cyc), dv_column = d$dv_col,
              resid_df = d$resid_df, boards = paste(sgs_h5_boards(smp), collapse = ", "),
              controls = paste(spec$controls, collapse = ", "), fixed_effects = paste(spec$fe, collapse = ", "),
              ci_text = sgs_ci_text(c$ci_low, c$ci_high)))
  })
}

sgs_h5_sample_rows <- function(spec, d) {
  df <- d$sample$df
  wtxt <- paste0("cycles ", sgs_cycles_text(sgs_h5_cycles(d$sample)))
  data.frame(test_id = rep(spec$id, nrow(df)), window_used = rep(wtxt, nrow(df)), study_sector = NA_character_,
             year = as.numeric(df$cycle), tier = NA_character_, y = as.numeric(df$y), board = df$board, bioguide = df$bioguide,
             cycle = as.numeric(df$cycle), stringsAsFactors = FALSE)
}

SGS_CHAMPION_PANEL_COLS <- c("board", "bioguide", "name", "cycle", "status", "up_for_election", "retiring", "lost_primary",
                             "chamber", "party", "seniority_years", "toughness_general", "rating_status", "primary_status",
                             "primary_contested", "primary_margin", "general_status", "general_margin")

sgs_champion_panel_table <- function(cd) {
  if (is.null(cd) || !isTRUE(cd$ok)) {
    return(as.data.frame(setNames(replicate(length(SGS_CHAMPION_PANEL_COLS), logical(0), simplify = FALSE),
                                  SGS_CHAMPION_PANEL_COLS), check.names = FALSE))
  }
  extra <- c(SGS$H5_DV_PRIMARY, SGS$H5_DV_TRADE)
  extra <- extra[extra %in% names(cd$frame)]
  st <- vapply(extra, function(c) sgs_dv_status_column(cd, c), "")
  extra <- c(extra, st[!is.na(st)])
  cols <- c(SGS_CHAMPION_PANEL_COLS[SGS_CHAMPION_PANEL_COLS %in% names(cd$frame)], extra)
  cd$frame[, cols, drop = FALSE]
}
