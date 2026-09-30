# Parity census: compare an R results workbook with the Python results workbook of the same inputs, cell by cell.
#
#   Rscript parity_census.R <python results.xlsx> <R results.xlsx> <out_dir> [python report.md] [R report.md]
#                            [python estimability.md] [R estimability.md]
#
# Every sheet the two workbooks share is compared: estimability (one row per test, all 40 columns), coefficients,
# strata, samples, the analysis tables, the dictionary and the sources (hash, size, sheets and rows read; paths, mtimes
# and read times are run-specific and listed separately). Text must be identical (a blank cell and an empty string
# are the same). Numbers: deterministic quantities within 1e-8 relative (or 1e-12 absolute); the bootstrap p of a
# random-draw test (6^G > B) within 4 sqrt(p (1 - p) / 9999) + 1 / 9999 of the Python p. Outputs:
#   parity_cells.csv   every compared cell that is not identical (numbers: with the deviation and the verdict)
#   parity_tests.csv   the census of every test: status, window, n, clusters, df, label, flags and every coefficient
#   parity_summary.md  the summary (maximum deviations per sheet and field, mismatches)

if (!requireNamespace("readxl", quietly = TRUE)) .libPaths(c("C:/Users/pgoff/AppData/Local/R/win-library/4.6", .libPaths()))

REL_TOL <- 1e-8
ABS_TOL <- 1e-12
if (!exists("%||%")) `%||%` <- function(x, y) if (is.null(x) || length(x) == 0L || (length(x) == 1L && is.na(x))) y else x

.read_sheet <- function(path, sheet) {
  if (!sheet %in% readxl::excel_sheets(path)) return(NULL)
  raw <- suppressWarnings(readxl::read_excel(path, sheet = sheet, col_names = FALSE, col_types = "list", trim_ws = FALSE,
                                             na = character(), .name_repair = "minimal"))
  if (!nrow(raw)) return(data.frame())
  hdr <- vapply(raw[1, ], function(v) as.character(v[[1]]), "")
  cols <- lapply(seq_along(raw), function(j) {
    vals <- raw[[j]][-1]
    kinds <- vapply(vals, function(v) if (is.null(v) || length(v) == 0L || (length(v) == 1L && is.na(v))) "blank" else class(v)[1], "")
    real <- unique(kinds[kinds != "blank"])
    if (!length(real)) return(rep(NA, length(vals)))
    if (all(real %in% c("numeric", "integer"))) {
      out <- rep(NA_real_, length(vals)); out[kinds != "blank"] <- vapply(vals[kinds != "blank"], as.numeric, 0); return(out)
    }
    if (identical(real, "logical")) {
      out <- rep(NA, length(vals)); out[kinds != "blank"] <- vapply(vals[kinds != "blank"], as.logical, TRUE); return(out)
    }
    out <- rep(NA_character_, length(vals))
    for (i in which(kinds != "blank")) out[i] <- as.character(vals[[i]])
    out
  })
  names(cols) <- hdr
  df <- as.data.frame(cols, stringsAsFactors = FALSE, check.names = FALSE)
  df
}

.norm_text <- function(v) {
  if (is.logical(v)) v <- ifelse(is.na(v), NA, ifelse(v, "TRUE", "FALSE"))
  v <- as.character(v)
  v[!is.na(v) & !nzchar(v)] <- NA
  v
}

.key <- function(df, cols) do.call(paste, c(lapply(cols, function(c) {
  v <- df[[c]]
  if (is.null(v)) return(rep("", nrow(df)))
  if (is.numeric(v)) v <- ifelse(is.na(v), "", sprintf("%.17g", v))
  v <- as.character(v); v[is.na(v)] <- ""
  v
}), sep = "\r"))

# Compare two frames aligned by `key` (or by row order when key is NULL). Returns list(cells, stats).
compare_frames <- function(py, r, sheet, key = NULL, random_p = NULL, skip = character(0)) {
  cells <- list(); stats <- list()
  if (is.null(py) || is.null(r)) {
    return(list(cells = data.frame(sheet = sheet, key = "", column = "(sheet)", python = if (is.null(py)) "absent" else "present",
                                   r = if (is.null(r)) "absent" else "present", abs_dev = NA, rel_dev = NA, verdict = "MISMATCH",
                                   stringsAsFactors = FALSE), stats = data.frame()))
  }
  kp <- if (is.null(key)) as.character(seq_len(nrow(py))) else .key(py, key)
  kr <- if (is.null(key)) as.character(seq_len(nrow(r))) else .key(r, key)
  only_py <- setdiff(kp, kr); only_r <- setdiff(kr, kp)
  for (k in only_py) cells[[length(cells) + 1L]] <- list(sheet, k, "(row)", "present", "absent", NA, NA, "MISMATCH")
  for (k in only_r) cells[[length(cells) + 1L]] <- list(sheet, k, "(row)", "absent", "present", NA, NA, "MISMATCH")
  if (anyDuplicated(kp) || anyDuplicated(kr)) {
    cells[[length(cells) + 1L]] <- list(sheet, "", "(key)", paste(sum(duplicated(kp)), "duplicate keys"),
                                        paste(sum(duplicated(kr)), "duplicate keys"), NA, NA, "MISMATCH")
  }
  common <- intersect(kp, kr)
  ip <- match(common, kp); ir <- match(common, kr)
  cols_py <- setdiff(names(py), skip); cols_r <- setdiff(names(r), skip)
  for (c in setdiff(cols_py, cols_r)) cells[[length(cells) + 1L]] <- list(sheet, "", c, "column present", "column absent", NA, NA, "MISMATCH")
  for (c in setdiff(cols_r, cols_py)) cells[[length(cells) + 1L]] <- list(sheet, "", c, "column absent", "column present", NA, NA, "R-ONLY")
  for (c in intersect(cols_py, cols_r)) {
    a <- py[[c]][ip]; b <- r[[c]][ir]
    num <- (is.numeric(a) || all(is.na(a))) && (is.numeric(b) || all(is.na(b))) && (is.numeric(a) || is.numeric(b))
    n_cmp <- length(common); n_bad <- 0L; max_rel <- 0; max_abs <- 0
    if (num) {
      a <- suppressWarnings(as.numeric(a)); b <- suppressWarnings(as.numeric(b))
      for (i in seq_along(common)) {
        if (is.na(a[i]) && is.na(b[i])) next
        if (is.na(a[i]) != is.na(b[i])) {
          n_bad <- n_bad + 1L
          cells[[length(cells) + 1L]] <- list(sheet, common[i], c, as.character(a[i]), as.character(b[i]), NA, NA, "MISMATCH")
          next
        }
        d <- abs(a[i] - b[i]); rel <- d / max(abs(a[i]), abs(b[i]), 1e-300)
        if (d > ABS_TOL) max_rel <- max(max_rel, rel)
        max_abs <- max(max_abs, d)
        tol_ok <- d <= ABS_TOL || rel <= REL_TOL
        verdict <- if (d == 0) NA else if (tol_ok) "within 1e-8" else "MISMATCH"
        if (!is.null(random_p) && c == "boot_p" && isTRUE(random_p[ip[i]])) {
          p <- a[i]; tol <- 4 * sqrt(p * (1 - p) / 9999) + 1 / 9999
          verdict <- if (d == 0) NA else if (d <= tol) "within the random-draw tolerance" else "MISMATCH"
        }
        if (!is.na(verdict)) {
          cells[[length(cells) + 1L]] <- list(sheet, common[i], c, sprintf("%.17g", a[i]), sprintf("%.17g", b[i]), d, rel, verdict)
          if (verdict == "MISMATCH") n_bad <- n_bad + 1L
        }
      }
    } else {
      at <- .norm_text(a); bt <- .norm_text(b)
      same <- (is.na(at) & is.na(bt)) | (!is.na(at) & !is.na(bt) & at == bt)
      for (i in which(!same)) {
        n_bad <- n_bad + 1L
        cells[[length(cells) + 1L]] <- list(sheet, common[i], c, at[i], bt[i], NA, NA, "MISMATCH")
      }
    }
    stats[[length(stats) + 1L]] <- list(sheet = sheet, column = c, type = if (num) "number" else "text", compared = n_cmp,
                                        mismatches = n_bad, max_rel_dev = if (num) max_rel else NA, max_abs_dev = if (num) max_abs else NA)
  }
  cdf <- if (length(cells)) as.data.frame(do.call(rbind, lapply(cells, function(x) {
    data.frame(sheet = x[[1]], key = x[[2]], column = x[[3]], python = as.character(x[[4]]), r = as.character(x[[5]]),
               abs_dev = as.numeric(x[[6]]), rel_dev = as.numeric(x[[7]]), verdict = x[[8]], stringsAsFactors = FALSE)
  }))) else data.frame(sheet = character(0), key = character(0), column = character(0), python = character(0), r = character(0),
                       abs_dev = numeric(0), rel_dev = numeric(0), verdict = character(0))
  sdf <- if (length(stats)) do.call(rbind, lapply(stats, as.data.frame, stringsAsFactors = FALSE)) else data.frame()
  list(cells = cdf, stats = sdf)
}

.md_lines <- function(path) {
  if (is.null(path) || !file.exists(path)) return(NULL)
  x <- readLines(path, warn = FALSE, encoding = "UTF-8")
  x
}

.norm_md <- function(x, run_id) {
  x <- gsub(run_id, "<run>", x, fixed = TRUE)
  x <- gsub("read_at_utc [^;)]*", "read_at_utc <t>", x)
  x
}

run_census <- function(py_xlsx, r_xlsx, out_dir, md = list()) {
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  res <- list()
  est_py <- .read_sheet(py_xlsx, "estimability"); est_r <- .read_sheet(r_xlsx, "estimability")
  res$estimability <- compare_frames(est_py, est_r, "estimability", key = "test_id")
  co_py <- .read_sheet(py_xlsx, "coefficients"); co_r <- .read_sheet(r_xlsx, "coefficients")
  random_p <- !is.na(co_py$boot_enumerated) & co_py$boot_enumerated %in% FALSE & co_py$boot_draws > 0
  res$coefficients <- compare_frames(co_py, co_r, "coefficients", key = c("test_id", "coefficient", "left_out"), random_p = random_p)
  res$strata <- compare_frames(.read_sheet(py_xlsx, "strata"), .read_sheet(r_xlsx, "strata"), "strata",
                               key = c("test_id", "coefficient", "study_sector", "board"))
  res$samples <- compare_frames(.read_sheet(py_xlsx, "samples"), .read_sheet(r_xlsx, "samples"), "samples",
                                key = c("test_id", "study_sector", "year", "tier", "board", "bioguide", "cycle"))
  res$sector_year <- compare_frames(.read_sheet(py_xlsx, "sector_year"), .read_sheet(r_xlsx, "sector_year"), "sector_year",
                                    key = c("study_sector", "year"))
  res$sector_year_tier <- compare_frames(.read_sheet(py_xlsx, "sector_year_tier"), .read_sheet(r_xlsx, "sector_year_tier"),
                                         "sector_year_tier", key = c("study_sector", "year", "tier"))
  res$industry_year <- compare_frames(.read_sheet(py_xlsx, "industry_year"), .read_sheet(r_xlsx, "industry_year"), "industry_year",
                                      key = c("study_sector", "year"))
  res$champions <- compare_frames(.read_sheet(py_xlsx, "champions"), .read_sheet(r_xlsx, "champions"), "champions",
                                  key = c("board", "bioguide", "cycle"))
  res$dictionary <- compare_frames(.read_sheet(py_xlsx, "dictionary"), .read_sheet(r_xlsx, "dictionary"), "dictionary")
  res$sources <- compare_frames(.read_sheet(py_xlsx, "sources"), .read_sheet(r_xlsx, "sources"), "sources", key = "file",
                                skip = c("absolute_path", "mtime_utc", "read_at_utc"))
  cells <- do.call(rbind, lapply(res, `[[`, "cells"))
  stats <- do.call(rbind, lapply(res, `[[`, "stats"))
  # per-test census
  tests <- list()
  fields <- c("status", "label", "window_used", "window_kind", "n", "n_window", "n_sectors", "sectors", "n_years", "years",
              "resid_df", "n_clusters", "reason", "reason_short", "default_attempt", "fallback_attempt", "fallback_search",
              "exclusions", "flag", "input_flags", "note", "dv_label")
  for (i in seq_len(nrow(est_py))) {
    tid <- est_py$test_id[i]
    j <- match(tid, est_r$test_id)
    row <- list(test_id = tid, python_status = est_py$status[i], r_status = if (is.na(j)) NA else est_r$status[j])
    bad_fields <- character(0)
    if (!is.na(j)) {
      for (f in fields) {
        a <- est_py[[f]][i]; b <- est_r[[f]][j]
        if (is.numeric(a) || is.numeric(b)) {
          same <- (is.na(a) && is.na(b)) || (!is.na(a) && !is.na(b) && abs(as.numeric(a) - as.numeric(b)) <= ABS_TOL)
        } else {
          a <- .norm_text(a); b <- .norm_text(b)
          same <- (is.na(a) && is.na(b)) || (!is.na(a) && !is.na(b) && a == b)
        }
        if (!same) bad_fields <- c(bad_fields, f)
      }
    } else bad_fields <- "(missing in R)"
    cp <- co_py[co_py$test_id == tid, , drop = FALSE]
    cr <- co_r[co_r$test_id == tid, , drop = FALSE]
    maxrel <- 0; coef_bad <- character(0)
    for (q in seq_len(nrow(cp))) {
      m <- which(cr$coefficient == cp$coefficient[q] & .norm_text(cr$left_out) %in% .norm_text(cp$left_out[q]))
      if (!length(m)) { coef_bad <- c(coef_bad, paste0(cp$coefficient[q], " missing")); next }
      for (f in c("estimate", "hc1_se", "cr1_se", "t_cr1", "boot_p", "ci_low", "ci_high", "boot_draws")) {
        a <- as.numeric(cp[[f]][q]); b <- as.numeric(cr[[f]][m[1]])
        if (is.na(a) && is.na(b)) next
        if (is.na(a) != is.na(b)) { coef_bad <- c(coef_bad, paste0(cp$coefficient[q], ".", f, " NA")); next }
        d <- abs(a - b); rel <- d / max(abs(a), abs(b), 1e-300)
        if (d > ABS_TOL) maxrel <- max(maxrel, rel)
        if (!(d <= ABS_TOL || rel <= REL_TOL)) coef_bad <- c(coef_bad, paste0(cp$coefficient[q], ".", f))
      }
      for (f in c("boot_enumerated", "ci_text", "boot_note", "stratification", "flag", "unit", "inference")) {
        if (!identical(.norm_text(cp[[f]][q]), .norm_text(cr[[f]][m[1]]))) coef_bad <- c(coef_bad, paste0(cp$coefficient[q], ".", f))
      }
    }
    if (nrow(cr) != nrow(cp)) coef_bad <- c(coef_bad, paste0("coefficient rows ", nrow(cp), " vs ", nrow(cr)))
    row$fields_differing <- paste(bad_fields, collapse = ", ")
    row$coefficients <- nrow(cp)
    row$coef_max_rel_dev <- if (nrow(cp)) maxrel else NA
    row$coef_differing <- paste(coef_bad, collapse = ", ")
    row$verdict <- if (!length(bad_fields) && !length(coef_bad)) "MATCH" else "MISMATCH"
    tests[[length(tests) + 1L]] <- row
  }
  tdf <- do.call(rbind, lapply(tests, as.data.frame, stringsAsFactors = FALSE))
  mdres <- list()
  for (nm in names(md)) {
    p <- md[[nm]]
    a <- .md_lines(p$python); b <- .md_lines(p$r)
    if (is.null(a) || is.null(b)) next
    a <- .norm_md(a, p$python_run); b <- .norm_md(b, p$r_run)
    n <- max(length(a), length(b))
    length(a) <- n; length(b) <- n
    diff <- which(!(a %in% NA & b %in% NA) & (is.na(a) | is.na(b) | a != b))
    mdres[[nm]] <- list(lines = n, differing = diff, python = a[diff], r = b[diff])
  }
  utils::write.csv(cells, file.path(out_dir, "parity_cells.csv"), row.names = FALSE, fileEncoding = "UTF-8")
  utils::write.csv(tdf, file.path(out_dir, "parity_tests.csv"), row.names = FALSE, fileEncoding = "UTF-8")
  utils::write.csv(stats, file.path(out_dir, "parity_stats.csv"), row.names = FALSE, fileEncoding = "UTF-8")
  list(cells = cells, stats = stats, tests = tdf, md = mdres)
}

if (sys.nframe() == 0L) {
  a <- commandArgs(trailingOnly = TRUE)
  md <- list()
  if (length(a) >= 5) md$report <- list(python = a[4], r = a[5], python_run = a[8] %||% "", r_run = a[9] %||% "")
  out <- run_census(a[1], a[2], a[3], md)
  cat("tests:", nrow(out$tests), " MATCH:", sum(out$tests$verdict == "MATCH"), " MISMATCH:", sum(out$tests$verdict != "MATCH"), "\n")
  print(table(out$cells$sheet, out$cells$verdict))
}
