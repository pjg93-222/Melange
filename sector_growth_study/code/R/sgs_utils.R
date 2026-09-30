# Shared helpers of the R port: Python-exact number formatting, pandas-like joins and sums, row lists to data
# frames, a values-only .xlsx writer, hashing and time stamps.
#
# Why exact formatting: R's sprintf goes through the C runtime, which on this machine is not correctly rounded
# (sprintf("%.4f", 0.00005) gives "0.0000", sprintf("%.4f", 0.00025) gives "0.0002"; Python gives "0.0001" and
# "0.0003"). Every number printed into a text field goes through sgs_py_fixed / sgs_py_g, which round the exact
# binary value half-to-even, as Python's format() does.

`%||%` <- function(x, y) if (is.null(x) || length(x) == 0L) y else x

# A date cell as "YYYY-MM-DD" (Date, POSIXct or text; a day range "2026-09-24/25" gives its last day; "2026-08" gives the
# month's last day, the conservative availability date of a month-dated source); NA when it cannot be read.
sgs_date_text <- function(x) {
  if (is.null(x) || !length(x)) return(NA_character_)
  x <- x[[1]]
  if (inherits(x, "Date")) return(format(x, "%Y-%m-%d"))
  if (inherits(x, "POSIXt")) return(format(x, "%Y-%m-%d", tz = "UTC"))
  s <- trimws(as.character(x))
  if (is.na(s) || !nzchar(s)) return(NA_character_)
  m <- regmatches(s, regexec("^(\\d{4})-(\\d{2})-(\\d{2})(?:/(\\d{2}))?", s, perl = TRUE))[[1]]
  if (length(m)) return(paste0(m[2], "-", m[3], "-", if (!is.na(m[5]) && nzchar(m[5])) m[5] else m[4]))
  m <- regmatches(s, regexec("^(\\d{4})-(\\d{2})$", s))[[1]]
  if (length(m)) {
    first_next <- as.Date(sprintf("%s-%s-01", m[2], m[3])) + 32
    return(format(as.Date(format(first_next, "%Y-%m-01")) - 1, "%Y-%m-%d"))
  }
  NA_character_
}

require_package <- function(package) {
  if (!requireNamespace(package, quietly = TRUE)) {
    stop("Required installed package is unavailable: ", package, call. = FALSE)
  }
  invisible(TRUE)
}

# Conditions with a class (LoadError, PanelError, NotBuilt, RegistryError), like the Python exceptions.
sgs_condition <- function(class, msg) {
  structure(class = c(class, "error", "condition"), list(message = msg, call = NULL))
}
sgs_raise <- function(class, msg) stop(sgs_condition(class, msg))

# ---- exact decimal expansion of a double ---------------------------------------------------------------------------

.sgs_limbs_of <- function(M) {  # M: integer-valued double < 2^53 -> base-1e6 limbs, least significant first
  out <- numeric(0)
  while (M > 0) {
    q <- floor(M / 1e6)
    out <- c(out, M - q * 1e6)
    M <- q
  }
  if (!length(out)) out <- 0
  out
}

.sgs_limbs_mul <- function(v, m) {  # v * m for m < 2^31; limbs stay below 1e6, every product is exact
  v <- v * m
  repeat {
    q <- floor(v / 1e6)
    if (all(q == 0)) break
    v <- v - q * 1e6
    n <- length(v)
    v <- v + c(0, q[-n])
    if (q[n] > 0) v <- c(v, q[n])
  }
  v
}

.sgs_limbs_string <- function(v) {
  v <- rev(v)
  while (length(v) > 1L && v[1] == 0) v <- v[-1]
  paste0(sprintf("%d", as.integer(v[1])), paste0(sprintf("%06d", as.integer(v[-1])), collapse = ""))
}

# |x| = digits * 10^(-scale), exactly (x finite).
sgs_exact_decimal <- function(x) {
  neg <- (x < 0) || (x == 0 && 1 / x < 0)
  a <- abs(x)
  if (a == 0) return(list(neg = neg, digits = "0", scale = 0L))
  e <- floor(log2(a))
  s <- 52 - e
  M <- if (s > 1000) a * 2^(s - 1000) * 2^1000 else a * 2^s
  while (M >= 2^53) { e <- e + 1; M <- M / 2 }
  while (M < 2^52) { e <- e - 1; M <- M * 2 }
  k <- 52 - e  # a = M * 2^-k
  while (k > 0 && M %% 2 == 0) { M <- M / 2; k <- k - 1 }
  v <- .sgs_limbs_of(M)
  if (k > 0) {
    left <- k
    while (left > 0) { st <- min(left, 13); v <- .sgs_limbs_mul(v, 5^st); left <- left - st }
    scale <- k
  } else {
    left <- -k
    while (left > 0) { st <- min(left, 30); v <- .sgs_limbs_mul(v, 2^st); left <- left - st }
    scale <- 0
  }
  list(neg = neg, digits = .sgs_limbs_string(v), scale = as.integer(scale))
}

.sgs_inc_digits <- function(d) {  # add 1 to a string of decimal digits
  ch <- strsplit(d, "", fixed = TRUE)[[1]]
  i <- length(ch)
  repeat {
    if (i == 0) { ch <- c("1", ch); break }
    if (ch[i] == "9") { ch[i] <- "0"; i <- i - 1 } else { ch[i] <- as.character(as.integer(ch[i]) + 1L); break }
  }
  paste(ch, collapse = "")
}

.sgs_round_up <- function(rest, last_digit) {  # round half to even on the exact remainder digits
  if (!nzchar(rest)) return(FALSE)
  f <- substr(rest, 1, 1)
  if (f > "5") return(TRUE)
  if (f < "5") return(FALSE)
  if (grepl("[1-9]", substring(rest, 2))) return(TRUE)
  as.integer(last_digit) %% 2L == 1L
}

.sgs_group3 <- function(ip) {
  n <- nchar(ip)
  if (n <= 3) return(ip)
  first <- n %% 3
  parts <- character(0)
  if (first > 0) parts <- substr(ip, 1, first)
  starts <- seq(first + 1, n, by = 3)
  paste(c(parts, substring(ip, starts, starts + 2)), collapse = ",")
}

# Python f"{x:.{d}f}" (comma = TRUE: f"{x:,.{d}f}").
sgs_py_fixed <- function(x, d, comma = FALSE) {
  if (is.na(x)) return("nan")
  if (is.infinite(x)) return(if (x > 0) "inf" else "-inf")
  ed <- sgs_exact_decimal(x)
  D <- ed$digits; s <- ed$scale
  nd <- nchar(D)
  if (nd <= s) { D <- paste0(strrep("0", s - nd + 1), D); nd <- nchar(D) }
  ip <- substr(D, 1, nd - s)
  fp <- if (s > 0) substr(D, nd - s + 1, nd) else ""
  if (s <= d) {
    fp <- paste0(fp, strrep("0", d - s))
  } else {
    keep <- substr(fp, 1, d)
    rest <- substr(fp, d + 1, s)
    last <- if (d > 0) substr(keep, d, d) else substr(ip, nchar(ip), nchar(ip))
    if (.sgs_round_up(rest, last)) {
      r <- .sgs_inc_digits(paste0(ip, keep))
      ip <- substr(r, 1, nchar(r) - d)
      keep <- if (d > 0) substr(r, nchar(r) - d + 1, nchar(r)) else ""
    }
    fp <- keep
  }
  if (comma) ip <- .sgs_group3(ip)
  out <- if (d > 0) paste0(ip, ".", fp) else ip
  if (ed$neg) paste0("-", out) else out
}

# Python f"{x:.{p}g}" (general format, no '#' flag).
sgs_py_g <- function(x, p = 6L) {
  if (is.na(x)) return("nan")
  if (is.infinite(x)) return(if (x > 0) "inf" else "-inf")
  if (p == 0) p <- 1L
  if (x == 0) return(if (1 / x < 0) "-0" else "0")
  ed <- sgs_exact_decimal(x)
  D <- sub("^0+", "", ed$digits)
  s <- ed$scale
  L <- nchar(D)
  X <- (L - 1L) - s
  if (L <= p) {
    keep <- paste0(D, strrep("0", p - L))
  } else {
    keep <- substr(D, 1, p)
    if (.sgs_round_up(substr(D, p + 1, L), substr(keep, p, p))) {
      keep <- .sgs_inc_digits(keep)
      if (nchar(keep) > p) { keep <- substr(keep, 1, p); X <- X + 1L }
    }
  }
  if (X >= -4 && X < p) {
    if (X >= 0) { ip <- substr(keep, 1, X + 1); fp <- substr(keep, X + 2, p) } else {
      ip <- "0"; fp <- paste0(strrep("0", -X - 1), keep)
    }
    fp <- sub("0+$", "", fp)
    out <- if (nzchar(fp)) paste0(ip, ".", fp) else ip
  } else {
    fr <- sub("0+$", "", substr(keep, 2, p))
    out <- paste0(substr(keep, 1, 1), if (nzchar(fr)) paste0(".", fr) else "", "e", if (X < 0) "-" else "+",
                  sprintf("%02d", as.integer(abs(X))))
  }
  if (ed$neg) paste0("-", out) else out
}

# report.fmt / champions._fmt: n/a for None/NaN, +-inf, %.4g below 1e-3 in absolute value, else %,.4f.
sgs_fmt <- function(x, digits = 4L) {
  if (is.null(x) || length(x) == 0L || is.na(x)) return("n/a")
  if (is.infinite(x)) return(if (x < 0) "-inf" else "+inf")
  if (abs(x) < 1e-3 && x != 0) sgs_py_g(x, digits) else sgs_py_fixed(x, digits, comma = TRUE)
}

sgs_ci_text <- function(lo, hi) paste0("[", sgs_fmt(lo), ", ", sgs_fmt(hi), "]")

# Python str() of an int-valued number (counts, years) and of a float (repr, shortest round trip).
sgs_int_str <- function(x) sprintf("%.0f", as.numeric(x))

.sgs_sig_digits <- function(x, p) {
  ed <- sgs_exact_decimal(x)
  D <- sub("^0+", "", ed$digits)
  L <- nchar(D)
  X <- (L - 1L) - ed$scale
  if (L <= p) keep <- D else {
    keep <- substr(D, 1, p)
    if (.sgs_round_up(substr(D, p + 1, L), substr(keep, p, p))) {
      keep <- .sgs_inc_digits(keep)
      if (nchar(keep) > p) { keep <- substr(keep, 1, p); X <- X + 1L }
    }
  }
  keep <- sub("0+$", "", keep)
  if (!nzchar(keep)) keep <- "0"
  list(neg = ed$neg, digits = keep, exp10 = X)
}

# Python repr(float).
sgs_py_repr_float <- function(x) {
  if (is.na(x)) return("nan")
  if (is.infinite(x)) return(if (x > 0) "inf" else "-inf")
  if (x == 0) return(if (1 / x < 0) "-0.0" else "0.0")
  sd <- NULL
  for (p in 1:17) {
    sd <- .sgs_sig_digits(x, p)
    txt <- paste0(if (sd$neg) "-" else "", "0.", sd$digits, "e", sd$exp10 + 1L)
    if (p == 17L || identical(as.numeric(txt), x)) break
  }
  dg <- sd$digits; n <- nchar(dg); decpt <- sd$exp10 + 1L
  if (decpt > -4 && decpt <= 16) {
    if (decpt <= 0) body <- paste0("0.", strrep("0", -decpt), dg)
    else if (decpt >= n) body <- paste0(dg, strrep("0", decpt - n), ".0")
    else body <- paste0(substr(dg, 1, decpt), ".", substr(dg, decpt + 1, n))
  } else {
    body <- paste0(substr(dg, 1, 1), if (n > 1) paste0(".", substr(dg, 2, n)) else "", "e",
                   if (decpt - 1 < 0) "-" else "+", sprintf("%02d", as.integer(abs(decpt - 1))))
  }
  paste0(if (sd$neg) "-" else "", body)
}

# Python repr() of a scalar (strings quoted as Python quotes them; numbers as int or float repr; None).
sgs_py_repr <- function(x) {
  if (is.null(x) || length(x) == 0L) return("None")
  if (length(x) > 1L) return(paste0("[", paste(vapply(as.list(x), sgs_py_repr, ""), collapse = ", "), "]"))
  if (is.na(x)) return("None")
  if (is.logical(x)) return(if (x) "True" else "False")
  if (is.numeric(x)) {
    if (is.finite(x) && x == round(x) && abs(x) < 1e15 && !isTRUE(attr(x, "py_float"))) return(sgs_int_str(x))
    return(sgs_py_repr_float(x))
  }
  x <- as.character(x)
  q <- if (grepl("'", x, fixed = TRUE) && !grepl("\"", x, fixed = TRUE)) "\"" else "'"
  y <- gsub("\\", "\\\\", x, fixed = TRUE)
  if (q == "'") y <- gsub("'", "\\'", y, fixed = TRUE)
  y <- gsub("\n", "\\n", y, fixed = TRUE)
  y <- gsub("\r", "\\r", y, fixed = TRUE)
  y <- gsub("\t", "\\t", y, fixed = TRUE)
  paste0(q, y, q)
}

sgs_py_list_repr <- function(x) paste0("[", paste(vapply(as.list(x), sgs_py_repr, ""), collapse = ", "), "]")

# pandas to_dict("records") repr of the rows of a small data frame (error messages).
sgs_records_repr <- function(df) {
  if (!nrow(df)) return("[]")
  recs <- vapply(seq_len(nrow(df)), function(i) {
    paste0("{", paste(vapply(names(df), function(c) paste0(sgs_py_repr(c), ": ", sgs_py_repr(df[[c]][i])), ""),
                      collapse = ", "), "}")
  }, "")
  paste0("[", paste(recs, collapse = ", "), "]")
}

# "key: value" texts of a named list (character(0) when the list is empty; paste0 would recycle to ": ").
sgs_kv <- function(lst) if (!length(lst)) character(0) else paste0(names(lst), ": ", vapply(lst, sgs_py_str, ""))

# Python str() of a scalar as an f-string prints it: None for NULL / NA, ints without ".0", True / False.
sgs_py_str <- function(x) {
  if (is.null(x) || length(x) == 0L) return("None")
  if (length(x) > 1L) return(paste0("[", paste(vapply(as.list(x), sgs_py_repr, ""), collapse = ", "), "]"))
  if (is.na(x)) return("None")
  if (is.logical(x)) return(if (x) "True" else "False")
  if (is.numeric(x)) {
    if (is.finite(x) && x == round(x) && abs(x) < 1e15) return(sgs_int_str(x))
    return(sgs_py_repr_float(x))
  }
  as.character(x)
}

# ---- years and ordering ----------------------------------------------------------------------------------------

# sample.years_text: compact year list, e.g. "2016-2019, 2021, 2023-2025"; "none" when empty.
sgs_years_text <- function(years) {
  ys <- sort(unique(as.integer(round(as.numeric(years[!is.na(years)])))))
  if (!length(ys)) return("none")
  parts <- character(0)
  start <- prev <- ys[1]
  for (y in c(ys[-1], NA)) {
    if (!is.na(y) && y == prev + 1L) { prev <- y; next }
    parts <- c(parts, if (start == prev) as.character(start) else paste0(start, "-", prev))
    if (!is.na(y)) { start <- y; prev <- y }
  }
  paste(parts, collapse = ", ")
}

# champions.cycles_text: "2022, 2024, 2026"; "none" when empty.
sgs_cycles_text <- function(cycles) {
  cs <- sort(unique(as.integer(round(as.numeric(cycles[!is.na(cycles)])))))
  if (!length(cs)) "none" else paste(cs, collapse = ", ")
}

# Position of a unit in the study-sector order; 99 for units that are not study sectors (SECTOR_ORDER.get(s, 99)).
sgs_sector_rank <- function(s) {
  r <- match(s, SGS$STUDY_SECTORS) - 1L
  r[is.na(r)] <- 99L
  r
}

# sorted(set(values), key=SECTOR_ORDER.get(s, 99)): stable, so units outside the study sectors keep the order of first
# appearance in `values`.
sgs_sort_sectors <- function(values) {
  u <- unique(values[!is.na(values)])
  u[order(sgs_sector_rank(u), method = "radix")]
}

# Python sorted() of unique strings (code point order).
sgs_sorted <- function(x) {
  u <- unique(x[!is.na(x)])
  u[order(u, method = "radix")]
}

# ---- pandas-like joins and sums ------------------------------------------------------------------------------------

.sgs_key_part <- function(v) {
  if (is.numeric(v)) return(ifelse(is.na(v), "\001", sprintf("%.17g", v)))
  if (is.logical(v)) return(ifelse(is.na(v), "\001", ifelse(v, "TRUE", "FALSE")))
  v <- as.character(v)
  ifelse(is.na(v), "\001", v)
}

sgs_key_of <- function(df, cols) {
  if (!length(cols)) return(rep("", nrow(df)))
  parts <- lapply(cols, function(c) .sgs_key_part(df[[c]]))
  do.call(paste, c(parts, sep = "\037"))
}

# pandas DataFrame.merge(how="left"): keeps x's row order; each x row gets every matching y row in y's order;
# overlapping non-key columns get suffixes; NA keys match NA keys (as in pandas).
sgs_left_join <- function(x, y, by, suffixes = c("_x", "_y")) {
  y_other <- setdiff(names(y), by)
  overlap <- intersect(y_other, setdiff(names(x), by))
  if (length(overlap)) {
    if (nzchar(suffixes[1])) names(x)[match(overlap, names(x))] <- paste0(overlap, suffixes[1])
    names(y)[match(overlap, names(y))] <- paste0(overlap, suffixes[2])
    y_other <- setdiff(names(y), by)
  }
  kx <- sgs_key_of(x, by)
  ky <- sgs_key_of(y, by)
  if (!anyDuplicated(ky)) {
    idx <- match(kx, ky)
    out <- x
    for (c in y_other) out[[c]] <- y[[c]][idx]
    rownames(out) <- NULL
    return(out)
  }
  groups <- split(seq_along(ky), factor(ky, levels = unique(ky)))
  xi <- integer(0); yi <- integer(0)
  for (i in seq_along(kx)) {
    m <- groups[[kx[i]]]
    if (is.null(m)) { xi <- c(xi, i); yi <- c(yi, NA_integer_) } else { xi <- c(xi, rep(i, length(m))); yi <- c(yi, m) }
  }
  out <- x[xi, , drop = FALSE]
  for (c in y_other) out[[c]] <- y[[c]][yi]
  rownames(out) <- NULL
  out
}

# Groups of the rows whose key columns are all present: list(keys = unique keys in sorted order (pandas groupby),
# index = row indices per group in row order).
sgs_groups <- function(df, keys) {
  ok <- rep(TRUE, nrow(df))
  for (k in keys) ok <- ok & !is.na(df[[k]])
  rows <- which(ok)
  if (!length(rows)) return(list(keys = df[0, keys, drop = FALSE], index = list()))
  kk <- sgs_key_of(df[rows, , drop = FALSE], keys)
  first <- rows[!duplicated(kk)]
  ukeys <- df[first, keys, drop = FALSE]
  ord <- do.call(order, c(lapply(keys, function(k) ukeys[[k]]), list(method = "radix")))
  ukeys <- ukeys[ord, , drop = FALSE]
  ulab <- sgs_key_of(ukeys, keys)
  index <- split(rows, factor(kk, levels = ulab))
  rownames(ukeys) <- NULL
  list(keys = ukeys, index = unname(index))
}

# pandas groupby(...).sum(min_count=...): Kahan-compensated summation as pandas' cython group_sum; NA when fewer
# than min_count values are present.
sgs_kahan_sum <- function(v, min_count = 0L) {
  v <- v[!is.na(v)]
  if (length(v) < min_count) return(NA_real_)
  s <- 0; comp <- 0
  for (val in v) {
    y <- val - comp
    t <- s + y
    comp <- t - s - y
    if (is.nan(comp)) comp <- 0
    s <- t
  }
  s
}

sgs_group_sum <- function(df, keys, col, min_count = 1L, name = col) {
  g <- sgs_groups(df, keys)
  out <- g$keys
  out[[name]] <- vapply(g$index, function(ix) sgs_kahan_sum(df[[col]][ix], min_count), 0)
  out
}

# numpy's pairwise summation of a float64 vector (np.add.reduce): Series.sum() / nansum inside a groupby lambda.
sgs_np_sum <- function(v) {
  n <- length(v)
  if (n < 8) {
    res <- 0
    for (x in v) res <- res + x
    return(res)
  }
  if (n <= 128) {
    r <- v[1:8]
    i <- 9
    lim <- n - (n %% 8)
    while (i <= lim) {
      r <- r + v[i:(i + 7)]
      i <- i + 8
    }
    res <- ((r[1] + r[2]) + (r[3] + r[4])) + ((r[5] + r[6]) + (r[7] + r[8]))
    while (i <= n) { res <- res + v[i]; i <- i + 1 }
    return(res)
  }
  n2 <- n %/% 2
  n2 <- n2 - n2 %% 8
  sgs_np_sum(v[1:n2]) + sgs_np_sum(v[(n2 + 1):n])
}

# Series.sum(min_count=1) (nanops.nansum: NaN filled with 0, numpy sum, NaN when no value is present).
sgs_nansum <- function(v, min_count = 1L) {
  if (sum(!is.na(v)) < min_count) return(NA_real_)
  v[is.na(v)] <- 0
  sgs_np_sum(as.numeric(v))
}

# ---- rows (named lists) to data frames ----------------------------------------------------------------------------

.sgs_is_blank <- function(v) is.null(v) || length(v) == 0L || (length(v) == 1L && is.na(v))

sgs_simplify <- function(vals) {
  n <- length(vals)
  if (!n) return(logical(0))
  isnull <- vapply(vals, .sgs_is_blank, TRUE)
  kinds <- vapply(vals, function(v) if (is.null(v) || length(v) == 0L) "null" else class(v)[1], "")
  real <- kinds[!isnull]
  if (!length(real)) return(rep(NA, n))
  if (all(real %in% c("numeric", "integer"))) {
    out <- rep(NA_real_, n); out[!isnull] <- vapply(vals[!isnull], function(v) as.numeric(v)[1], 0); return(out)
  }
  if (all(real == "logical")) {
    out <- rep(NA, n); out[!isnull] <- vapply(vals[!isnull], function(v) as.logical(v)[1], TRUE); return(out)
  }
  out <- rep(NA_character_, n)
  out[!isnull] <- vapply(vals[!isnull], function(v) {
    if (is.character(v)) v[1] else if (is.logical(v)) (if (v[1]) "True" else "False") else sgs_py_repr(v[1])
  }, "")
  out
}

# A list of named lists -> data frame with columns `cols` (missing names -> NA), like pd.DataFrame(rows, columns=cols).
sgs_rows_df <- function(rows, cols) {
  if (!length(rows)) {
    df <- as.data.frame(setNames(replicate(length(cols), logical(0), simplify = FALSE), cols), check.names = FALSE)
    return(df)
  }
  out <- lapply(cols, function(c) sgs_simplify(lapply(rows, function(r) r[[c, exact = TRUE]])))
  names(out) <- cols
  as.data.frame(out, stringsAsFactors = FALSE, check.names = FALSE)
}

sgs_df_rows <- function(df) {
  if (!nrow(df)) return(list())
  lapply(seq_len(nrow(df)), function(i) {
    r <- lapply(df, function(col) col[[i]])
    r
  })
}

# ---- values-only .xlsx writer ----------------------------------------------------------------------------------------

sgs_col_letter <- function(j) {
  out <- character(length(j))
  for (i in seq_along(j)) {
    n <- j[i]; s <- ""
    while (n > 0) { r <- (n - 1) %% 26; s <- paste0(LETTERS[r + 1], s); n <- (n - 1) %/% 26 }
    out[i] <- s
  }
  out
}

sgs_xml_escape <- function(x) {
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  x <- gsub(">", "&gt;", x, fixed = TRUE)
  x <- gsub("\"", "&quot;", x, fixed = TRUE)
  x
}

# Number text: integers below 1e15 exactly; other values with 17 significant digits (round-trips a double).
sgs_num_text <- function(x) {
  out <- character(length(x))
  whole <- is.finite(x) & x == round(x) & abs(x) < 1e15
  out[whole] <- sprintf("%.0f", x[whole])
  other <- !whole & is.finite(x)
  out[other] <- sprintf("%.17g", x[other])
  out
}

.sgs_sheet_xml <- function(df, allow_formulas) {
  nc <- ncol(df); nr <- nrow(df)
  letters_ <- sgs_col_letter(seq_len(max(nc, 1)))
  rows <- character(nr + 1L)
  hdr <- names(df)
  if (nc) {
    hdr_cells <- paste0('<c r="', letters_[seq_len(nc)], '1" t="inlineStr"><is><t xml:space="preserve">',
                        sgs_xml_escape(enc2utf8(hdr)), "</t></is></c>")
    rows[1] <- paste0('<row r="1">', paste(hdr_cells, collapse = ""), "</row>")
  } else {
    rows[1] <- '<row r="1"></row>'
  }
  if (nr > 0 && nc > 0) {
    cells <- matrix("", nr, nc)
    for (j in seq_len(nc)) {
      v <- df[[j]]
      ref <- paste0(letters_[j], seq_len(nr) + 1L)
      if (is.logical(v)) {
        ok <- !is.na(v)
        cells[ok, j] <- paste0('<c r="', ref[ok], '" t="b"><v>', ifelse(v[ok], "1", "0"), "</v></c>")
      } else if (is.numeric(v)) {
        v[!is.finite(v)] <- NA
        ok <- !is.na(v)
        cells[ok, j] <- paste0('<c r="', ref[ok], '"><v>', sgs_num_text(v[ok]), "</v></c>")
      } else {
        v <- as.character(v)
        ok <- !is.na(v) & nzchar(v)
        vv <- ifelse(is.na(v), "", v)
        if (any(grepl("[\001-\010\013\014\016-\037]", vv[ok]))) stop("illegal control character in a cell value", call. = FALSE)
        fml <- ok & startsWith(vv, "=")
        if (any(fml) && !allow_formulas) {
          stop("refusing to write a cell starting with '=': ", sgs_py_repr(substr(vv[fml][1], 1, 40)), call. = FALSE)
        }
        st <- ok & !fml
        cells[st, j] <- paste0('<c r="', ref[st], '" t="inlineStr"><is><t xml:space="preserve">',
                               sgs_xml_escape(enc2utf8(vv[st])), "</t></is></c>")
        if (any(fml)) cells[fml, j] <- paste0('<c r="', ref[fml], '"><f>', sgs_xml_escape(substring(vv[fml], 2)), "</f></c>")
      }
    }
    body <- apply(cells, 1, paste, collapse = "")
    rows[-1] <- paste0('<row r="', seq_len(nr) + 1L, '">', body, "</row>")
  }
  dim_ref <- paste0("A1:", letters_[max(nc, 1)], nr + 1L)
  paste0('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
         '<dimension ref="', dim_ref, '"/><sheetData>', paste(rows, collapse = ""), "</sheetData></worksheet>")
}

.sgs_write_utf8 <- function(path, text) {
  con <- file(path, open = "wb")
  on.exit(close(con))
  writeBin(charToRaw(enc2utf8(text)), con)
}

# Write a workbook of values only (the study format): header row = column names; numbers, booleans and inline
# strings; blank for NA or "". allow_formulas = TRUE (synthetic test inputs only) writes strings starting with "=" as
# formulas, as openpyxl does; otherwise such a string is refused. Written to a temporary file, then renamed.
sgs_write_xlsx <- function(path, sheets, allow_formulas = FALSE) {
  require_package("zip")
  stage <- tempfile("sgsxlsx")
  dir.create(file.path(stage, "_rels"), recursive = TRUE)
  dir.create(file.path(stage, "xl", "_rels"), recursive = TRUE)
  dir.create(file.path(stage, "xl", "worksheets"), recursive = TRUE)
  on.exit(unlink(stage, recursive = TRUE), add = TRUE)
  n <- length(sheets)
  nm <- names(sheets)
  ct <- paste0('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
               '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
               '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
               '<Default Extension="xml" ContentType="application/xml"/>',
               '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
               '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
               paste0('<Override PartName="/xl/worksheets/sheet', seq_len(n),
                      '.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>',
                      collapse = ""),
               "</Types>")
  rels <- paste0('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>',
                 "</Relationships>")
  wb <- paste0('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
               '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ',
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>',
               paste0('<sheet name="', sgs_xml_escape(enc2utf8(nm)), '" sheetId="', seq_len(n), '" r:id="rId', seq_len(n),
                      '"/>', collapse = ""),
               "</sheets></workbook>")
  wbrels <- paste0('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
                   paste0('<Relationship Id="rId', seq_len(n),
                          '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet',
                          seq_len(n), '.xml"/>', collapse = ""),
                   '<Relationship Id="rId', n + 1L,
                   '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
                   "</Relationships>")
  styles <- paste0('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
                   '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
                   '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>',
                   '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>',
                   '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>',
                   '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>',
                   '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>',
                   '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>',
                   "</styleSheet>")
  .sgs_write_utf8(file.path(stage, "[Content_Types].xml"), ct)
  .sgs_write_utf8(file.path(stage, "_rels", ".rels"), rels)
  .sgs_write_utf8(file.path(stage, "xl", "workbook.xml"), wb)
  .sgs_write_utf8(file.path(stage, "xl", "_rels", "workbook.xml.rels"), wbrels)
  .sgs_write_utf8(file.path(stage, "xl", "styles.xml"), styles)
  for (i in seq_len(n)) {
    .sgs_write_utf8(file.path(stage, "xl", "worksheets", paste0("sheet", i, ".xml")),
                    .sgs_sheet_xml(sheets[[i]], allow_formulas))
  }
  files <- c("[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels", "xl/styles.xml",
             paste0("xl/worksheets/sheet", seq_len(n), ".xml"))
  target <- normalizePath(path, winslash = "/", mustWork = FALSE)
  tmp <- paste0(target, ".tmp.xlsx")
  if (file.exists(tmp)) unlink(tmp)
  zip::zip(tmp, files = files, root = stage, mode = "mirror")
  if (file.exists(target)) unlink(target)
  file.rename(tmp, target)
  invisible(path)
}

# ---- text, hashes, time ------------------------------------------------------------------------------------------

# Text lines with CRLF line ends (Python's Path.write_text on Windows), UTF-8 without BOM.
sgs_write_lines_crlf <- function(path, lines) {
  .sgs_write_utf8(path, paste0(paste(lines, collapse = "\r\n"), "\r\n"))
}

sgs_utc_iso <- function(t) format(as.POSIXct(t, origin = "1970-01-01", tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
sgs_utc_stamp <- function(t = Sys.time()) format(as.POSIXct(t, tz = "UTC"), "%Y%m%dT%H%M%SZ", tz = "UTC")

sgs_sha256_file <- function(path) {
  require_package("digest")
  digest::digest(file = path, algo = "sha256")
}

sgs_sha256_raw <- function(raw) {
  require_package("digest")
  digest::digest(raw, algo = "sha256", serialize = FALSE)
}

sgs_mtime <- function(path) as.numeric(file.info(path)$mtime)
