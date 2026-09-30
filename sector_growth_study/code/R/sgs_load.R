# Read the study workbooks read-only and validate them (R port of code/sgs/load.py). Any violation raises a LoadError
# naming file, sheet and column.
#
# Checks per sheet read: the sheet exists; header in row 1 with unique non-empty names; required columns present;
# no cell anywhere in the workbook starts with "=" (formula or formula-like text); the key columns are unique (a blank
# key part is compared as its own value "<blank>"). Sheets flagged study_sector = TRUE require the column
# `study_sector`; a sheet that still carries only `sector` is rejected with a message naming the rename.
# Optional sheets are validated when present and skipped when absent.
#
# The values-only guard works on the workbook XML (every <f> formula cell and every string cell whose text starts
# with "="), so sheets the rule set does not use (e.g. 02 expected_control_markets under Paul's rulings) are never
# parsed into data. Only the sheets of the specification are read into data frames (readxl).

.sheet_spec <- function(required, key, study_sector = FALSE, optional = FALSE) {
  list(required = required, key = key, study_sector = study_sector, optional = optional)
}

# The workbooks of a rule set: list(name = list(file, sheets = list(sheet = spec), optional_file)).
sgs_workbook_specs <- function(rules = sgs_rules()) {
  paul <- identical(rules$name, "paul-2026-09-25")
  election <- list(
    data = .sheet_spec(c("calendar_year", "chamber", "p_dem_expected", "status"), c("calendar_year", "chamber")),
    seat_calls = .sheet_spec(c("chamber", "election_year", "pred_dem_net_change", "status"), c("chamber", "election_year")),
    expected_control_2023_2026 = .sheet_spec(
      c("calendar_year", "chamber", "exp_dem", "method", "flag", "status", "source_id"), c("calendar_year", "chamber"),
      optional = TRUE)
  )
  if (isTRUE(rules$read_markets)) {
    election$expected_control_markets <- .sheet_spec(c("date", "calendar_year", "chamber", "market", "status"),
                                                     c("date", "chamber", "market"), optional = TRUE)
  }
  if (isTRUE(rules$h4_538)) {
    election$expected_control_538 <- .sheet_spec(c("year", "series", "value"), c("year", "chamber", "series"),
                                                 optional = TRUE)
  }
  lobbying <- list(
    data = .sheet_spec(c("source", "sector", "confidence", "year", "period", "lobby_income_real_2025_usd",
                         "lobby_expenses_real_2025_usd", "lobby_amount_undifferentiated_real_2025_usd", "status"),
                       c("source", "sector", "confidence", "year", "period"))
  )
  if (identical(rules$lobbyview, "all_sectors")) {
    lobbying[[SGS$LOBBYVIEW_ALL_SHEET]] <- .sheet_spec(
      c("year", "lobby_amount_undifferentiated_real_2025_usd", "status"), character(0), optional = TRUE)
  }
  predicted <- list(
    data = .sheet_spec(c("year", "predicted_growth_pct", "forecast_publication_month", "forecast_age_months", "status"),
                       c("study_sector", "year"), study_sector = TRUE)
  )
  if (isTRUE(rules$multiyear)) {
    predicted$supplemental_observations <- .sheet_spec(
      c("observation_id", "study_sector", "growth_measure", "growth_pct", "status"), c("observation_id"), optional = TRUE)
    predicted$component_forecasts <- .sheet_spec(c("record_source", "study_sector", "status"), character(0),
                                                 optional = TRUE)
  }
  out <- list(
    controls = list(file = "00_controls.xlsx", sheets = list(
      data = .sheet_spec(c("year", "presidential_year", "midterm_year", "status"), c("year")))),
    lobbying = list(file = "01_lobbying_expenditures.xlsx", sheets = lobbying),
    election = list(file = "02_election_forecasting.xlsx", sheets = election),
    seats = list(file = "03_actual_seat_gain.xlsx", sheets = list(
      current_control = .sheet_spec(c("calendar_year", "chamber", "dem_control", "status"), c("calendar_year", "chamber")))),
    spending = list(file = "04_campaign_spending.xlsx", sheets = list(
      data = .sheet_spec(c("year", "company", "recipient_category", "party", "funding_source", "giving_real_2025_usd", "status"),
                         c("year", "study_sector", "company", "recipient_category", "party", "funding_source"),
                         study_sector = TRUE),
      sector_year = .sheet_spec(c("year", "giving_real_2025_usd", "status"), c("study_sector", "year"), study_sector = TRUE),
      tier_by_year = .sheet_spec(c("year", "company", "employee_tier", "giving_real_2025_usd", "status"),
                                 c("year", "study_sector", "company", "employee_tier"), study_sector = TRUE))),
    predicted = list(file = "06_predicted_industry_growth.xlsx", sheets = predicted),
    actual = list(file = "07_actual_industry_growth.xlsx", sheets = list(
      data = .sheet_spec(c("sector", "year", "growth_same_year_pct", "growth_previous_year_pct", "status"),
                         c("sector", "year"), study_sector = TRUE))),
    crosswalk = list(file = "sector_crosswalk.xlsx", sheets = list(
      data = .sheet_spec(c("mentat_industry", "lda_lobbying_sector"), c("study_sector"), study_sector = TRUE)))
  )
  if (isTRUE(rules$seats)) {
    # SEATS: the chamber composition before each election (03 data: seats at the start of the outgoing Congress), the
    # base of the forecast Democratic net seat gain
    out$seats$sheets$data <- .sheet_spec(c("chamber", "election_year", "democratic_seats_before", "republican_seats_before"),
                                         c("chamber", "election_year"), optional = TRUE)
  }
  if (isTRUE(rules$ds_chamber)) {
    out$chamber <- list(file = SGS$CHAMBER_FILE, optional_file = TRUE, sheets = list(
      sector_year_chamber = .sheet_spec(c("study_sector", "year", "chamber", "dem_usd", "rep_usd", "dem_share", "status"),
                                        c("study_sector", "year", "chamber")),
      other_recipients = .sheet_spec(c("study_sector", "year"), c("study_sector", "year"), optional = TRUE)))
    if (isTRUE(rules$shift)) {
      # SHIFT Hill variants and DS+Hill: 08 sector_year_chamber with DCCC / DSCC added to D and NRCC / NRSC to R (the
      # same columns and keys as sector_year_chamber); NOT BUILT until the sheet exists
      out$chamber$sheets[[SGS$CHAMBER_HILL_SHEET]] <- .sheet_spec(
        c("study_sector", "year", "chamber", "dem_usd", "rep_usd", "dem_share", "status"), c("study_sector", "year", "chamber"),
        optional = TRUE)
    }
  }
  out
}

# ---- workbook XML: sheet list and the values-only guard -------------------------------------------------------------

.xml_unescape <- function(x) {
  x <- gsub("&lt;", "<", x, fixed = TRUE)
  x <- gsub("&gt;", ">", x, fixed = TRUE)
  x <- gsub("&quot;", "\"", x, fixed = TRUE)
  x <- gsub("&apos;", "'", x, fixed = TRUE)
  x <- gsub("&amp;", "&", x, fixed = TRUE)
  x
}

.xml_attr <- function(tag, name) {
  m <- regmatches(tag, regexec(paste0("\\s", name, "=\"([^\"]*)\""), tag))[[1]]
  if (length(m) < 2) NA_character_ else .xml_unescape(m[2])
}

.zip_text <- function(path, member) {
  con <- unz(path, member, open = "rb")
  on.exit(close(con))
  chunks <- list()
  repeat {
    b <- readBin(con, "raw", 1048576L)
    if (!length(b)) break
    chunks[[length(chunks) + 1L]] <- b
  }
  txt <- rawToChar(do.call(c, chunks))
  Encoding(txt) <- "UTF-8"
  txt
}

.zip_members <- function(path) utils::unzip(path, list = TRUE)$Name

# Sheets in workbook order: data.frame(name, member).
sgs_xlsx_sheets <- function(path) {
  members <- .zip_members(path)
  wb <- .zip_text(path, "xl/workbook.xml")
  rels <- .zip_text(path, "xl/_rels/workbook.xml.rels")
  stags <- regmatches(wb, gregexpr("<sheet\\s[^>]*>", wb))[[1]]
  rtags <- regmatches(rels, gregexpr("<Relationship\\s[^>]*>", rels))[[1]]
  rid <- vapply(rtags, .xml_attr, "", name = "Id", USE.NAMES = FALSE)
  target <- vapply(rtags, .xml_attr, "", name = "Target", USE.NAMES = FALSE)
  out <- data.frame(name = character(0), member = character(0), stringsAsFactors = FALSE)
  for (st in stags) {
    nm <- .xml_attr(st, "name")
    id <- .xml_attr(st, "r:id")
    tg <- target[match(id, rid)]
    tg <- if (startsWith(tg, "/")) substring(tg, 2) else paste0("xl/", tg)
    tg <- gsub("/\\./", "/", tg)
    if (!tg %in% members) tg <- members[tolower(members) == tolower(tg)][1]
    out[nrow(out) + 1L, ] <- list(nm, tg)
  }
  out
}

.col_index <- function(letters_) {
  vapply(letters_, function(s) {
    ch <- utf8ToInt(s) - 64L
    sum(ch * 26^(rev(seq_along(ch)) - 1))
  }, 0, USE.NAMES = FALSE)
}

# Cells of one worksheet XML that break the values-only rule: data.frame(row, col, ref, value) in no particular order.
.offending_cells <- function(xml, eq_shared) {
  out <- data.frame(row = numeric(0), col = numeric(0), ref = character(0), value = character(0), stringsAsFactors = FALSE)
  has_f <- grepl("<f[ >/]", xml, perl = TRUE)
  has_inline_eq <- grepl("<is>\\s*(<r>\\s*(<rPr>.*?</rPr>\\s*)?)?<t[^>]*>=", xml, perl = TRUE)
  has_shared <- length(eq_shared) > 0 && grepl('t="s"', xml, fixed = TRUE)
  if (!has_f && !has_inline_eq && !has_shared) return(out)
  cells <- regmatches(xml, gregexpr("<c\\s[^>]*?(/>|>.*?</c>)", xml, perl = TRUE))[[1]]
  for (cell in cells) {
    head <- regmatches(cell, regexpr("^<c\\s[^>]*?(/>|>)", cell, perl = TRUE))
    ref <- .xml_attr(head, "r")
    typ <- .xml_attr(head, "t")
    val <- NA_character_
    if (grepl("<f[ >/]", cell, perl = TRUE)) {
      f <- regmatches(cell, regexec("<f[^>]*>(.*?)</f>", cell, perl = TRUE))[[1]]
      val <- paste0("=", if (length(f) >= 2) .xml_unescape(f[2]) else "")
    } else if (identical(typ, "inlineStr")) {
      ts <- regmatches(cell, gregexpr("<t[^>]*>(.*?)</t>", cell, perl = TRUE))[[1]]
      txt <- .xml_unescape(paste(sub("^<t[^>]*>", "", sub("</t>$", "", ts)), collapse = ""))
      if (startsWith(txt, "=")) val <- txt
    } else if (identical(typ, "s") && has_shared) {
      v <- regmatches(cell, regexec("<v>([0-9]+)</v>", cell))[[1]]
      if (length(v) >= 2) {
        k <- as.integer(v[2])
        if (k %in% eq_shared$index) val <- eq_shared$text[match(k, eq_shared$index)]
      }
    }
    if (!is.na(val)) {
      m <- regmatches(ref, regexec("^([A-Z]+)([0-9]+)$", ref))[[1]]
      out[nrow(out) + 1L, ] <- list(as.numeric(m[3]), .col_index(m[2]), ref, val)
    }
  }
  out
}

.shared_eq_strings <- function(path, members) {
  if (!"xl/sharedStrings.xml" %in% members) return(data.frame(index = integer(0), text = character(0)))
  sst <- .zip_text(path, "xl/sharedStrings.xml")
  if (!grepl(">=", sst, fixed = TRUE)) return(data.frame(index = integer(0), text = character(0)))
  sis <- regmatches(sst, gregexpr("<si>.*?</si>|<si/>", sst, perl = TRUE))[[1]]
  txt <- vapply(sis, function(si) {
    ts <- regmatches(si, gregexpr("<t[^>]*>(.*?)</t>", si, perl = TRUE))[[1]]
    .xml_unescape(paste(sub("^<t[^>]*>", "", sub("</t>$", "", ts)), collapse = ""))
  }, "", USE.NAMES = FALSE)
  hit <- which(startsWith(txt, "="))
  data.frame(index = hit - 1L, text = txt[hit], stringsAsFactors = FALSE)
}

# load._sheet_rows: raise on the first cell (sheet order, then row, then column) whose value starts with "=".
sgs_values_only_guard <- function(path, file_label = basename(path)) {
  members <- .zip_members(path)
  sheets <- sgs_xlsx_sheets(path)
  eq_shared <- .shared_eq_strings(path, members)
  for (i in seq_len(nrow(sheets))) {
    xml <- .zip_text(path, sheets$member[i])
    bad <- .offending_cells(xml, eq_shared)
    if (nrow(bad)) {
      b <- bad[order(bad$row, bad$col), ][1, ]
      sgs_raise("LoadError", paste0(file_label, " [", sheets$name[i], "] cell ", b$ref, ": value starts with '=' (",
                                    sgs_py_repr(substr(b$value, 1, 40)), "); the study format is values only"))
    }
  }
  invisible(sheets$name)
}

# ---- one sheet -> data frame (load._frame) ----------------------------------------------------------------------------

.cell_scalar <- function(v) {
  if (is.null(v) || length(v) == 0L) return(NA)
  v[[1]]
}

# A readxl list column -> a typed vector: numeric, logical, or character (dates as ISO text; mixed -> text).
.simplify_cells <- function(vals) {
  n <- length(vals)
  kinds <- vapply(vals, function(v) {
    if (is.null(v) || length(v) == 0L || (length(v) == 1L && is.na(v) && !inherits(v, "POSIXct"))) "blank"
    else if (inherits(v, "POSIXct")) "date"
    else class(v)[1]
  }, "")
  real <- unique(kinds[kinds != "blank"])
  if (!length(real)) return(rep(NA, n))
  if (all(real %in% c("numeric", "integer"))) {
    out <- rep(NA_real_, n); out[kinds != "blank"] <- vapply(vals[kinds != "blank"], function(v) as.numeric(v), 0); return(out)
  }
  if (identical(real, "logical")) {
    out <- rep(NA, n); out[kinds != "blank"] <- vapply(vals[kinds != "blank"], function(v) as.logical(v), TRUE); return(out)
  }
  out <- rep(NA_character_, n)
  for (i in which(kinds != "blank")) {
    v <- vals[[i]]
    out[i] <- if (kinds[i] == "date") format(v, "%Y-%m-%d %H:%M:%S", tz = "UTC")
      else if (is.character(v)) v
      else if (is.logical(v)) (if (v) "True" else "False")
      else sgs_py_repr(v)
  }
  out
}

.read_sheet_raw <- function(path, sheet) {
  require_package("readxl")
  require_package("cellranger")
  suppressWarnings(readxl::read_excel(path, sheet = sheet, col_names = FALSE, col_types = "list",
                                      range = cellranger::cell_limits(c(1, 1), c(NA, NA)), trim_ws = FALSE,
                                      na = character(), .name_repair = "minimal"))
}

sgs_frame_from_raw <- function(raw, file_label, sheet) {
  if (!nrow(raw) || !ncol(raw)) sgs_raise("LoadError", paste0(file_label, " [", sheet, "]: empty sheet (no header row)"))
  header <- lapply(raw, function(col) .cell_scalar(col[[1]]))
  while (length(header) && (is.na(header[[length(header)]]))) header <- header[-length(header)]
  names_ <- character(length(header))
  for (i in seq_along(header)) {
    h <- header[[i]]
    if (is.na(h) || (is.character(h) && !nzchar(trimws(h)))) {
      sgs_raise("LoadError", paste0(file_label, " [", sheet, "] header column ", i, ": empty header name in row 1"))
    }
    names_[i] <- if (is.character(h)) trimws(h) else sgs_py_repr(h)
  }
  dup <- sort(unique(names_[duplicated(names_)]), method = "radix")
  if (length(dup)) sgs_raise("LoadError", paste0(file_label, " [", sheet, "] header: duplicate column names ", sgs_py_list_repr(dup)))
  nh <- length(names_)
  cols <- vector("list", nh)
  nr <- nrow(raw) - 1L
  for (j in seq_len(nh)) {
    cols[[j]] <- if (j <= ncol(raw) && nr > 0) raw[[j]][-1] else rep(list(NA), max(nr, 0))
  }
  if (nr > 0) {
    blank <- matrix(TRUE, nr, max(nh, 1))
    for (j in seq_len(nh)) {
      blank[, j] <- vapply(cols[[j]], function(v) is.null(v) || length(v) == 0L || (length(v) == 1L && is.na(v)), TRUE)
    }
    keep <- !apply(blank, 1, all)
  } else {
    keep <- logical(0)
  }
  out <- lapply(cols, function(c) .simplify_cells(c[keep]))
  names(out) <- names_
  df <- as.data.frame(out, stringsAsFactors = FALSE, check.names = FALSE, optional = TRUE)
  if (!length(out)) df <- data.frame()
  if (nrow(df) == 0 && length(names_)) {
    df <- as.data.frame(setNames(replicate(nh, logical(0), simplify = FALSE), names_), check.names = FALSE)
  }
  attr(df, "raw_rows") <- nrow(raw)
  df
}

# load.validate_frame
sgs_validate_frame <- function(df, spec, file_label, sheet) {
  if (isTRUE(spec$study_sector) && !"study_sector" %in% names(df)) {
    extra <- if ("sector" %in% names(df)) paste0(" (a `sector` column is present: the study format names the study-sector ",
                                                 "column `study_sector` since the 2026-09-25 uniform-column ruling)") else ""
    sgs_raise("LoadError", paste0(file_label, " [", sheet, "] column study_sector: required column missing", extra))
  }
  for (col in spec$required) {
    if (!col %in% names(df)) sgs_raise("LoadError", paste0(file_label, " [", sheet, "] column ", col, ": required column missing"))
  }
  for (col in spec$key) {
    if (!col %in% names(df)) sgs_raise("LoadError", paste0(file_label, " [", sheet, "] column ", col, ": key column missing"))
  }
  key <- spec$key
  if (length(key) && nrow(df)) {
    keyed <- df[, key, drop = FALSE]
    for (k in key) {
      v <- keyed[[k]]
      if (anyNA(v)) {
        v <- if (is.character(v)) v else vapply(v, function(z) if (is.na(z)) NA_character_ else sgs_py_repr(z), "")
        v[is.na(v)] <- "<blank>"
        keyed[[k]] <- v
      }
    }
    kk <- sgs_key_of(keyed, key)
    dups <- duplicated(kk) | duplicated(kk, fromLast = TRUE)
    if (any(dups)) {
      example <- sgs_records_repr(keyed[which(dups)[seq_len(min(3, sum(dups)))], , drop = FALSE])
      sgs_raise("LoadError", paste0(file_label, " [", sheet, "] key ", sgs_py_list_repr(key), ": ", sum(dups),
                                    " rows share a key; e.g. ", example))
    }
  }
  df
}

# load.read_workbook: list(name, path, sha256, size_bytes, mtime_utc, read_at_utc, frames, raw_rows).
sgs_read_workbook <- function(path, sheets, name = "", file_label = basename(path)) {
  if (!file.exists(path)) sgs_raise("LoadError", paste0(file_label, ": file not found at ", path))
  info <- file.info(path)
  read_at <- sgs_utc_iso(Sys.time())
  present <- sgs_values_only_guard(path, file_label)
  frames <- list()
  raw_rows <- list()
  for (sheet in names(sheets)) {
    spec <- sheets[[sheet]]
    if (!sheet %in% present) {
      if (isTRUE(spec$optional)) next
      sgs_raise("LoadError", paste0(file_label, " [", sheet, "]: sheet missing (present: ",
                                    sgs_py_list_repr(sort(present, method = "radix")), ")"))
    }
    raw <- .read_sheet_raw(path, sheet)
    fr <- sgs_frame_from_raw(raw, file_label, sheet)
    raw_rows[[sheet]] <- attr(fr, "raw_rows")
    frames[[sheet]] <- sgs_validate_frame(fr, spec, file_label, sheet)
  }
  list(name = if (nzchar(name)) name else file_label, path = normalizePath(path, winslash = "\\", mustWork = TRUE),
       file = basename(path), sha256 = sgs_sha256_file(path), size_bytes = as.numeric(info$size),
       mtime_utc = sgs_utc_iso(as.numeric(info$mtime)), read_at_utc = read_at, frames = frames, raw_rows = raw_rows,
       sheets_present = present)
}

# load.load_all: every study workbook of the rule set; optional workbooks (08) are skipped when absent.
sgs_load_all <- function(data_dir = SGS$DATA_DIR, rules = sgs_rules()) {
  specs <- sgs_workbook_specs(rules)
  out <- list()
  for (nm in names(specs)) {
    sp <- specs[[nm]]
    path <- file.path(data_dir, sp$file)
    if (isTRUE(sp$optional_file) && !file.exists(path)) next
    out[[nm]] <- sgs_read_workbook(path, sp$sheets, nm)
  }
  out
}
