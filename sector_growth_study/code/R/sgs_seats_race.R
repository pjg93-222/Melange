# SEATS race level (rule set paul-2026-09-25 only), built to the coordinator's contract of 2026-09-26 after the Codex
# reviews (TEST_CONTRACT_REVIEW.md, RECIPIENT_HANDOFF.md, RACE_FORECAST_SOURCE_NOTE.md and the binding corrections).
#
# Exposure side (inputs: workbook 10 - recipient classification and dated service terms - and workbook 11 - the
# verified 538 House district and Senate state forecasts and the dated expert ratings; all read-only):
#   - the candidate's OWN win probability at each spending window's origin: the latest 538 row of the candidate's race
#     available strictly before the window (availability = the latest of forecast date, run-timestamp date, available_at
#     and the public model launch); 538 "Lite" primary (Lite is not a polls-only model: it imputes unpolled races),
#     Classic and Deluxe sensitivities;
#   - the NAMED candidate only: 538 slot names (name_D1..D4, name_R1..R4, name_I1) are matched to the recipients'
#     cand_ids within cycle, chamber, state (House: and district) and party by surname (first name breaks ties); a
#     candidate not named in the selected row gets no probability - never the race favourite's; unmatched and ambiguous
#     names are kept and reported; at-large 538 districts ("WY-1") become FEC "WY-00";
#   - 538 probability classes from the candidate's own probability q = max(p, 1 - p): toss-up < 60%, lean 60-75%,
#     likely 75-95%, safe >= 95% (538 classes, never Cook / Inside / Sabato ratings), with the candidate-relative side
#     (favoured / underdog) and the race favourite's party;
#   - incumbency at each origin from the dated service intervals (end exclusive; same chamber only, so a House member
#     running for the Senate is not an incumbent senator): first-term, established; appointments, partial first terms
#     and nonconsecutive service flagged;
#   - the favoured NON-INCUMBENT (primary incoming-officeholder group): no dated service in the chamber at the origin and
#     the candidate's own named 538 Lite probability above 0.5 before the window (0.6 as a sensitivity), pooling FEC
#     challengers and open-seat candidates; the FEC C / O split is a PROVISIONAL sensitivity only (FEC codes are not
#     reliable general-election status); its four 538-class cross-cuts are exploratory; never an eventual winner;
#   - nominee status: a named forecast candidate is not necessarily the nominee (pre-primary forecasts condition on an
#     assumed matchup): windows before the race's named matchup became final are flagged (a proxy from the forecast rows
#     unless an official primary calendar sheet is supplied), with a post-primary-only sensitivity;
#   - expert ratings as a separate categorical path: primary rows are timing_eligible_primary with
#     availability_date_conservative strictly before the window (NMA reprints dated 30 September and the cache and
#     Wikipedia rows stay out of the primary); Tilt kept separate (forced four groups: Tilt -> Lean, Tilt -> Toss-up as a
#     sensitivity); an unrated race is unknown, never safe.
# Money side (estimands B and C): 09's committee sheet (primary money; the Codex helper CSV is a cross-check only).
# Every cell is gated estimated / descriptive only / unavailable with its reason (sgs_seats_cells).

SGS_SEATS_538_CLASSES <- c("toss-up", "lean", "likely", "safe")
SGS_SEATS_538_SOURCES <- c("lite", "classic", "deluxe")
SGS_SEATS_SLOTS <- c(D1 = "D", D2 = "D", D3 = "D", D4 = "D", R1 = "R", R2 = "R", R3 = "R", R4 = "R", I1 = "I")
SGS_SEATS_EXPERT_SOURCES <- c("cook", "inside", "sabato")
SGS_SEATS_538_REQUIRED <- c("district", "forecastdate", "timestamp", "name_D1", "name_R1", "winner_D1", "winner_R1")
SGS_SEATS_10_SHEETS <- list(
  recipient_classification = .sheet_spec(c("cycle", "committee_id", "cand_id", "candidate_name", "party", "chamber", "state",
                                           "district", "fec_incumbent_challenger_open"), c("cycle", "committee_id")),
  candidate_service_terms = .sheet_spec(c("cand_id", "chamber", "start", "end", "term_index_same_chamber"), character(0)))
SGS_SEATS_538_COLS <- c("cycle", "district", "forecastdate", "expression", "timestamp", "available_at", "available_at_launch_floor",
                        "backfilled", "same_party_flag", "multiparty_flag", paste0("name_", names(SGS_SEATS_SLOTS)),
                        paste0("winner_", names(SGS_SEATS_SLOTS)), "winner_O1", "winner_Dparty", "winner_Rparty")
SGS_SEATS_11_SHEETS <- list(
  house_district_538_2022 = list(required = SGS_SEATS_538_REQUIRED, optional = TRUE, stream_cols = SGS_SEATS_538_COLS),
  senate_state_538_2022 = list(required = SGS_SEATS_538_REQUIRED, optional = TRUE, stream_cols = SGS_SEATS_538_COLS),
  rating_history_expert = list(required = c("cycle", "race_id", "source", "bucket", "favored_party", "chamber", "tilt_flag",
                                            "availability_date_conservative", "timing_eligible_primary", "timing_eligible_extended"),
                               optional = TRUE),
  primary_calendar = list(required = c("cycle", "state", "primary_date"), optional = TRUE))
SGS_SEATS_09_MONEY <- list(sheet = "committee_week", required = c("study_sector", "committee_id", "week_start", "gross_usd"),
                           optional = c("refund_usd", "usd", "party", "fec_cycle"))

# ---- reading: quiet period, a values-only guard that streams the XML, and a fast text reader ---------------------------
.seats_guard_stream <- function(path, label, skip = character(0)) {
  sheets <- sgs_xlsx_sheets(path); members <- .zip_members(path)
  scan <- function(member, rx) {
    con <- unz(path, member, open = "rb"); on.exit(close(con))
    prev <- raw(0)
    repeat {
      b <- readBin(con, "raw", 8388608L)
      if (!length(b)) break
      if (grepl(rx, rawToChar(c(prev, b)), perl = TRUE, useBytes = TRUE)) return(TRUE)
      prev <- utils::tail(b, 512L)
    }
    FALSE
  }
  for (i in seq_len(nrow(sheets))) {
    if (sheets$name[i] %in% skip) next                      # streamed sheets are checked as they are read
    if (scan(sheets$member[i], "<f[ >/]|<is>\\s*(?:<r>\\s*(?:<rPr>.*?</rPr>\\s*)?)?<t[^>]*>=")) {
      sgs_raise("LoadError", paste0(label, " [", sheets$name[i], "]: a formula or a cell starting with '='; the study format is values only"))
    }
  }
  if ("xl/sharedStrings.xml" %in% members && scan("xl/sharedStrings.xml", "<si>\\s*(?:<r>\\s*(?:<rPr>.*?</rPr>\\s*)?)?<t[^>]*>=")) {
    sgs_raise("LoadError", paste0(label, ": a shared string starts with '='; the study format is values only"))
  }
  invisible(sheets$name)
}
.seats_read_sheet_text <- function(path, sheet, label) {
  require_package("readxl")
  df <- suppressWarnings(readxl::read_excel(path, sheet = sheet, col_types = "text", na = character(), trim_ws = FALSE,
                                            .name_repair = "minimal"))
  nm <- trimws(names(df))
  if (any(!nzchar(nm))) sgs_raise("LoadError", paste0(label, " [", sheet, "] header: an empty column name in row 1"))
  if (anyDuplicated(nm)) sgs_raise("LoadError", paste0(label, " [", sheet, "] header: duplicate column names ",
                                                       paste(unique(nm[duplicated(nm)]), collapse = ", ")))
  df <- as.data.frame(df, stringsAsFactors = FALSE, optional = TRUE)
  names(df) <- nm
  df
}
# A large sheet read as a stream (workbook 11's 538 sheets: 199,665 rows x 96 columns; readxl's whole-sheet parse needs
# several GB): the sheet XML is read in 16 MB pieces cut at row ends and only the wanted columns are kept, as text
# (shared strings resolved, XML entities unescaped, booleans TRUE / FALSE). A formula in the sheet is a LoadError.
.seats_col_letters <- function(n) vapply(n, function(i) { s <- ""; while (i > 0) { r <- (i - 1) %% 26; s <- paste0(LETTERS[r + 1], s); i <- (i - 1) %/% 26 }; s }, "")
.seats_sst <- function(path) {
  if (!"xl/sharedStrings.xml" %in% .zip_members(path)) return(character(0))
  x <- .zip_text(path, "xl/sharedStrings.xml")
  si <- regmatches(x, gregexpr("<si>.*?</si>|<si/>", x, perl = TRUE))[[1]]
  si <- gsub("<rPh.*?</rPh>", "", si, perl = TRUE)
  .xml_unescape(gsub("<[^>]+>", "", si, perl = TRUE))
}
.seats_parse_cells <- function(rows_txt, letters_rx) {
  m <- unlist(regmatches(rows_txt, gregexpr(paste0("<c r=\"(?:", letters_rx, ")[0-9]+\"[^>]*?(?:/>|>.*?</c>)"), rows_txt, perl = TRUE)),
              use.names = FALSE)
  if (!length(m)) return(NULL)
  head <- sub("^(<c[^>]*?)/?>.*$", "\\1", m, perl = TRUE)
  typ <- ifelse(grepl(" t=\"", head, fixed = TRUE), sub("^.* t=\"([a-zA-Z]+)\".*$", "\\1", head, perl = TRUE), "n")
  val <- rep(NA_character_, length(m))
  hv <- grepl("<v>", m, fixed = TRUE)
  val[hv] <- sub("^.*?<v>(.*?)</v>.*$", "\\1", m[hv], perl = TRUE)
  hi <- !hv & grepl("<is>", m, fixed = TRUE)
  val[hi] <- gsub("<[^>]+>", "", sub("^.*?<is>(.*?)</is>.*$", "\\1", m[hi], perl = TRUE), perl = TRUE)
  list(col = sub("^<c r=\"([A-Z]+)[0-9]+\".*$", "\\1", m, perl = TRUE), row = as.integer(sub("^<c r=\"[A-Z]+([0-9]+)\".*$", "\\1", m, perl = TRUE)),
       typ = typ, val = val)
}
.seats_read_sheet_stream <- function(path, sheet, want, label) {
  sh <- sgs_xlsx_sheets(path)
  member <- sh$member[match(sheet, sh$name)]
  sst <- .seats_sst(path)
  if (any(startsWith(sst, "="))) sgs_raise("LoadError", paste0(label, ": a shared string starts with '='; the study format is values only"))
  con <- unz(path, member, open = "rb"); on.exit(close(con))
  rest <- raw(0); cols <- NULL; rx <- ""; store <- list(); maxrow <- 1L
  resolve <- function(v, t) {
    s <- t == "s"; v[s] <- sst[as.integer(v[s]) + 1L]
    v[!s] <- .xml_unescape(v[!s])
    b <- t == "b"; v[b] <- ifelse(v[b] == "1", "TRUE", "FALSE")
    v
  }
  repeat {
    b <- readBin(con, "raw", 16777216L)
    eof <- !length(b)
    buf <- c(rest, b)
    if (!length(buf)) break
    pos <- grepRaw("</row>", buf, fixed = TRUE, all = TRUE)
    if (!length(pos)) { if (eof) break; rest <- buf; next }
    cut <- pos[length(pos)] + 5L
    txt <- rawToChar(buf[seq_len(cut)]); Encoding(txt) <- "UTF-8"
    rest <- if (cut < length(buf)) buf[(cut + 1L):length(buf)] else raw(0)
    if (grepl("<f[ >/]", txt, perl = TRUE, useBytes = TRUE) || grepl("<is>\\s*(?:<r>\\s*(?:<rPr>.*?</rPr>\\s*)?)?<t[^>]*>=", txt, perl = TRUE, useBytes = TRUE)) {
      sgs_raise("LoadError", paste0(label, " [", sheet, "]: a formula or a cell starting with '='; the study format is values only"))
    }
    rows <- strsplit(txt, "</row>", fixed = TRUE)[[1]]
    if (is.null(cols)) {
      hc <- .seats_parse_cells(rows[1], "[A-Z]+")
      hv <- trimws(resolve(hc$val, hc$typ))
      if (anyDuplicated(hv[!is.na(hv)])) sgs_raise("LoadError", paste0(label, " [", sheet, "] header: duplicate column names"))
      cols <- setNames(hc$col[hv %in% want], hv[hv %in% want])
      rx <- paste(cols, collapse = "|")
      rows <- rows[-1]
    }
    if (length(rows) && length(cols)) {
      pc <- .seats_parse_cells(rows, rx)
      if (!is.null(pc)) { pc$val <- resolve(pc$val, pc$typ); store[[length(store) + 1L]] <- pc; maxrow <- max(maxrow, pc$row) }
    }
    if (eof) break
  }
  n <- maxrow - 1L
  df <- as.data.frame(setNames(lapply(names(cols), function(x) rep(NA_character_, max(n, 0L))), names(cols)), stringsAsFactors = FALSE,
                      optional = TRUE)
  for (pc in store) for (nm in names(cols)) {
    k <- pc$col == cols[[nm]]
    if (any(k)) df[[nm]][pc$row[k] - 1L] <- pc$val[k]
  }
  if (n > 0) df <- df[rowSums(!is.na(df)) > 0, , drop = FALSE]
  rownames(df) <- NULL
  df
}
.seats_quiet <- function(path, now, file) {
  age <- as.numeric(difftime(now %||% Sys.time(), file.info(path)$mtime, units = "mins"))
  if (is.finite(age) && age < SGS$SEATS_W_QUIET_MINUTES) {
    return(paste0(file, " was modified ", sgs_py_fixed(age, 1), " minutes ago (less than ", SGS$SEATS_W_QUIET_MINUTES,
                  "): it may still be being written"))
  }
  ""
}
# One SEATS input workbook: list(ok, reason, wb (frames of text columns), source). sheets: name = list(required, optional).
sgs_seats_load_input <- function(data_dir, file, sheets, label, now = NULL, absent = "") {
  path <- file.path(data_dir, file)
  if (!file.exists(path)) return(list(ok = FALSE, reason = paste0(file, " not present in the input folder", if (nzchar(absent)) paste0(" (", absent, ")") else "")))
  q <- .seats_quiet(path, now, file)
  if (nzchar(q)) return(list(ok = FALSE, reason = q))
  wb <- tryCatch({
    present <- .seats_guard_stream(path, file, skip = names(Filter(function(s) !is.null(s$stream_cols), sheets)))
    frames <- list()
    for (sh in names(sheets)) {
      if (!sh %in% present) {
        if (isTRUE(sheets[[sh]]$optional)) next
        sgs_raise("LoadError", paste0(file, " [", sh, "]: sheet missing (present: ", paste(present, collapse = ", "), ")"))
      }
      df <- if (!is.null(sheets[[sh]]$stream_cols)) .seats_read_sheet_stream(path, sh, sheets[[sh]]$stream_cols, file) else .seats_read_sheet_text(path, sh, file)
      miss <- setdiff(sheets[[sh]]$required, names(df))
      if (length(miss)) sgs_raise("LoadError", paste0(file, " [", sh, "] lacks ", paste(miss, collapse = ", ")))
      frames[[sh]] <- df
    }
    info <- file.info(path)
    list(path = normalizePath(path, winslash = "\\", mustWork = TRUE), file = file, sha256 = sgs_sha256_file(path),
         size_bytes = as.numeric(info$size), mtime_utc = sgs_utc_iso(as.numeric(info$mtime)), read_at_utc = sgs_utc_iso(Sys.time()),
         frames = frames, sheets_present = present)
  }, error = function(e) e)
  if (inherits(wb, "error")) return(list(ok = FALSE, reason = paste0(file, " not read: ", conditionMessage(wb))))
  list(ok = TRUE, reason = "", wb = wb,
       source = list(file = wb$file, workbook = label, absolute_path = wb$path, sha256 = wb$sha256, size_bytes = wb$size_bytes,
                     mtime_utc = wb$mtime_utc, read_at_utc = wb$read_at_utc, sheets_read = paste(names(wb$frames), collapse = ", "),
                     rows_read = paste0(names(wb$frames), "=", vapply(wb$frames, nrow, 0), collapse = ", "), note = paste0("SEATS: ", label)))
}
sgs_seats_load_10 <- function(data_dir, now = NULL) {
  path <- file.path(data_dir, SGS$SEATS_10_FILE)
  if (!file.exists(path)) return(list(ok = FALSE, reason = paste0(SGS$SEATS_10_FILE, " not present in the input folder (being imported)")))
  q <- .seats_quiet(path, now, SGS$SEATS_10_FILE)
  if (nzchar(q)) return(list(ok = FALSE, reason = q))
  wb <- tryCatch(sgs_read_workbook(path, SGS_SEATS_10_SHEETS, "seats_recipients"), error = function(e) e)
  if (inherits(wb, "error")) return(list(ok = FALSE, reason = paste0(SGS$SEATS_10_FILE, " not read: ", conditionMessage(wb))))
  list(ok = TRUE, reason = "", wb = wb,
       source = list(file = wb$file, workbook = "seats_recipients", absolute_path = wb$path, sha256 = wb$sha256, size_bytes = wb$size_bytes,
                     mtime_utc = wb$mtime_utc, read_at_utc = wb$read_at_utc, sheets_read = paste(names(wb$frames), collapse = ", "),
                     rows_read = paste0(names(wb$frames), "=", vapply(wb$frames, nrow, 0), collapse = ", "),
                     note = "SEATS race level: recipient classification and dated service terms (Codex, read-only)"))
}

# ---- dates ---------------------------------------------------------------------------------------------------------
.SEATS_MON <- c("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
.seats_ymd <- function(y, m, d) as.Date(sprintf("%04d-%02d-%02d", as.integer(y), as.integer(m), as.integer(d)), format = "%Y-%m-%d")
# A calendar day from ISO dates / date-times (an explicit offset is converted to UTC first), 538's m/d/yy forecast
# dates, 538 run timestamps ("00:12:39  8 Nov 2022", no time zone: the day as written) or Excel serial day numbers.
.seats_day <- function(x) {
  if (inherits(x, "Date")) return(x)
  x <- trimws(as.character(x))
  n <- length(x); out <- rep(NA_real_, n)
  ok <- !is.na(x) & nzchar(x)
  k <- which(ok & grepl("^\\d{4}-\\d{2}-\\d{2}", x))
  if (length(k)) {
    d <- as.numeric(as.Date(substr(x[k], 1, 10), format = "%Y-%m-%d"))
    m <- regmatches(x[k], regexec("^\\d{4}-\\d{2}-\\d{2}[T ](\\d{2}):(\\d{2})(?::\\d{2}(?:\\.\\d+)?)?\\s*(Z|[+-]\\d{2}:?\\d{2})$", x[k], perl = TRUE))
    for (i in which(lengths(m) > 0)) {
      z <- m[[i]][4]
      off <- if (z == "Z") 0 else (if (startsWith(z, "-")) -1 else 1) * (as.numeric(substr(gsub("[^0-9]", "", z), 1, 2)) * 60 +
                                                                          as.numeric(substr(gsub("[^0-9]", "", z), 3, 4)))
      d[i] <- d[i] + floor((as.numeric(m[[i]][2]) * 60 + as.numeric(m[[i]][3]) - off) / 1440)
    }
    out[k] <- d
  }
  k <- which(ok & is.na(out) & grepl("^\\d{1,2}/\\d{1,2}/\\d{2,4}$", x))
  if (length(k)) {
    p <- do.call(rbind, strsplit(x[k], "/", fixed = TRUE))
    yy <- as.numeric(p[, 3]); yy <- ifelse(yy < 100, 2000 + yy, yy)
    out[k] <- as.numeric(.seats_ymd(yy, p[, 1], p[, 2]))
  }
  k <- which(ok & is.na(out) & grepl("\\d{1,2}\\s+[A-Za-z]{3}[A-Za-z]*\\s+\\d{4}$", x))
  if (length(k)) {
    m <- do.call(rbind, regmatches(x[k], regexec("(\\d{1,2})\\s+([A-Za-z]{3})[A-Za-z]*\\s+(\\d{4})$", x[k])))
    out[k] <- as.numeric(.seats_ymd(m[, 4], match(tolower(m[, 3]), .SEATS_MON), m[, 2]))
  }
  k <- which(ok & is.na(out) & grepl("^\\d{5}(\\.\\d+)?$", x))
  if (length(k)) out[k] <- as.numeric(as.Date(floor(as.numeric(x[k])), origin = "1899-12-30"))
  as.Date(out, origin = "1970-01-01")
}
.seats_mondays <- function(from, to) {
  if (is.na(from) || is.na(to) || from > to) return(as.Date(character(0)))
  first <- from + ((1 - as.POSIXlt(from)$wday) %% 7)
  if (first > to) return(as.Date(character(0)))
  seq(first, to, by = 7)
}

# ---- names ---------------------------------------------------------------------------------------------------------
.seats_ascii <- function(x) {
  from <- paste0("àáâãäåçèéêëìíîïñòóô",
                 "õöùúûüýÿÀÁÂÃÄÅÇÈÉÊË",
                 "ÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ")
  to <- "aaaaaaceeeeiiiinooooouuuuyyAAAAAACEEEEIIIINOOOOOUUUUY"
  chartr(from, to, enc2utf8(as.character(x)))
}
.SEATS_SUFFIX <- c("JR", "SR", "II", "III", "IV", "V")
.SEATS_TITLES <- c("MR", "MRS", "MS", "DR", "HON", "REV", "SEN", "REP")
.seats_tokens <- function(x) {
  x <- toupper(.seats_ascii(x))
  x <- gsub("\"[^\"]*\"|\\([^)]*\\)|“[^”]*”", " ", x)   # nicknames in quotes or parentheses
  x <- gsub("[.'`’]", "", x)                                          # O'ROURKE -> OROURKE, initials
  x <- gsub("[^A-Z]+", " ", x)                                              # hyphens and other punctuation split tokens
  lapply(strsplit(trimws(x), " +"), function(t) t[nzchar(t)])
}
.seats_strip_suffix <- function(t) { while (length(t) > 1 && t[length(t)] %in% .SEATS_SUFFIX) t <- t[-length(t)]; t }
# Given-name tokens, nicknames in quotes or parentheses kept ("FOSTER, G. WILLIAM (BILL)" -> G WILLIAM BILL).
.seats_given_tokens <- function(x) {
  x <- toupper(.seats_ascii(x))
  x <- gsub("[.'`’\"“”()]", " ", x)
  x <- gsub("[^A-Z]+", " ", x)
  lapply(strsplit(trimws(x), " +"), function(t) t[nzchar(t) & !t %in% c(.SEATS_TITLES, .SEATS_SUFFIX)])
}
# FEC "LAST, FIRST MIDDLE SUFFIX" -> list(last = surname tokens, given = every given-name token, first = the first one)
.seats_fec_name <- function(nm) {
  nm <- as.character(nm)
  has <- grepl(",", nm, fixed = TRUE)
  last <- ifelse(has, sub(",.*$", "", nm), sub("^.*\\s", "", trimws(nm)))
  first <- ifelse(has, sub("^[^,]*,", "", nm), sub("\\s.*$", "", trimws(nm)))
  lt <- lapply(.seats_tokens(last), .seats_strip_suffix)
  gt <- .seats_given_tokens(first)
  list(last = lt, given = gt, first = vapply(gt, function(t) if (length(t)) t[1] else "", ""))
}
# Common given-name nicknames whose initial differs from the formal name (a nickname sharing the initial is covered by
# the initial rule): nickname -> formal names.
.SEATS_NICK <- list(BOB = "ROBERT", BOBBY = "ROBERT", BO = "ROBERT", ROB = "ROBERT", BILL = "WILLIAM", BILLY = "WILLIAM",
                    WILL = "WILLIAM", LIZ = "ELIZABETH", LIZZIE = "ELIZABETH", BETH = "ELIZABETH", BETSY = "ELIZABETH",
                    BETTY = "ELIZABETH", LIZA = "ELIZABETH", TRISH = "PATRICIA", TRICIA = "PATRICIA", PATTY = "PATRICIA",
                    DICK = "RICHARD", RICK = "RICHARD", RICH = "RICHARD", JACK = "JOHN", TED = c("EDWARD", "THEODORE"),
                    NED = "EDWARD", HANK = "HENRY", PEGGY = "MARGARET", MAGGIE = "MARGARET", MEG = "MARGARET", SALLY = "SARAH",
                    POLLY = "MARY", MOLLY = "MARY", CHUY = "JESUS", PACO = "FRANCISCO", PANCHO = "FRANCISCO", PEPE = "JOSE",
                    BECCA = "REBECCA", BECKY = "REBECCA", TONY = "ANTHONY", JERRY = c("GERALD", "JEROME"), DREW = "ANDREW",
                    SANDY = c("ALEXANDER", "SANDRA"), KIT = "CHRISTOPHER", HAL = c("HAROLD", "HENRY"), ZEKE = "EZEKIEL",
                    GUS = "AUGUSTUS", KATE = c("KATHERINE", "CATHERINE"), CATHY = "KATHERINE", KATHY = "CATHERINE",
                    TRENT = "TRENTON", JIM = "JAMES", JIMMY = "JAMES", MIKE = "MICHAEL", ANDY = "ANDREW", TOM = "THOMAS",
                    VAL = "VALERIE", CHUCK = "CHARLES", LARRY = "LAWRENCE", STEVE = c("STEVEN", "STEPHEN"), PAT = c("PATRICK", "PATRICIA"))
# Given-name compatibility of a 538 first name with the FEC given names: 3 exact, 2 nickname, 1 initial, 0 none.
.seats_given_level <- function(f538, given) {
  if (!nzchar(f538) || !length(given)) return(0L)
  if (f538 %in% given) return(3L)
  if (any(.SEATS_NICK[[f538]] %in% given) || any(vapply(given, function(g) f538 %in% (.SEATS_NICK[[g]] %||% character(0)), TRUE))) return(2L)
  if (substr(f538, 1, 1) %in% substr(given, 1, 1)) return(1L)
  0L
}
# Does a 538 name (tokens, suffix stripped) end with the FEC surname? The surname's letters must equal the letters of a
# trailing run of whole 538 tokens (so DE LA CRUZ = DELACRUZ, OCASIO-CORTEZ matches, LEE does not match MCLEE).
.seats_surname_hit <- function(t538, last) {
  if (!length(t538) || !length(last)) return(FALSE)
  target <- paste(last, collapse = "")
  n <- length(t538)
  any(vapply(seq_len(n), function(s) identical(paste(t538[s:n], collapse = ""), target), TRUE))
}
.seats_party3 <- function(p) {
  p <- toupper(trimws(as.character(p)))
  ifelse(p %in% c("D", "DEM", "DFL", "DEMOCRAT", "DEMOCRATIC"), "D", ifelse(p %in% c("R", "REP", "GOP", "REPUBLICAN"), "R", "I"))
}

# ---- 538 race rows ---------------------------------------------------------------------------------------------------
# One 538 sheet (text columns) -> list(rows = one row per race x source x run, slots = the named candidate slots).
sgs_seats_538_rows <- function(df, chamber) {
  n <- nrow(df)
  col <- function(nm) if (nm %in% names(df)) as.character(df[[nm]]) else rep(NA_character_, n)
  num <- function(nm) suppressWarnings(as.numeric(col(nm)))
  cyc <- suppressWarnings(as.integer(col("cycle")))
  fd <- .seats_day(col("forecastdate")); rt <- .seats_day(col("timestamp")); aa <- .seats_day(col("available_at"))
  cyc[is.na(cyc)] <- as.integer(format(fd[is.na(cyc)], "%Y"))
  launch <- .seats_day(unname(SGS$SEATS_538_LAUNCH[as.character(cyc)]))
  none <- is.na(fd) & is.na(rt) & is.na(aa)
  # PRIMARY availability (coordinator's ruling on workbook 11): available_at_launch_floor, Codex's rule that no row is
  # available before 538's public launch (30 June 2022); without that column, the latest of forecast date, run date,
  # available_at and the launch. The SENSITIVITY is plain available_at (the later of forecast date and run date).
  floor_ <- .seats_day(col("available_at_launch_floor"))
  comp <- as.Date(pmax(as.numeric(fd), as.numeric(rt), as.numeric(aa), as.numeric(launch), na.rm = TRUE), origin = "1970-01-01")
  avail <- if ("available_at_launch_floor" %in% names(df)) as.Date(pmax(as.numeric(floor_), as.numeric(fd), as.numeric(rt), na.rm = TRUE), origin = "1970-01-01") else comp
  avail[none] <- NA
  avail_sens <- if ("available_at" %in% names(df)) aa else as.Date(pmax(as.numeric(fd), as.numeric(rt), na.rm = TRUE), origin = "1970-01-01")
  avail_sens[none] <- NA
  src <- sub("^_", "", tolower(trimws(col("expression"))))
  src[is.na(src) | !nzchar(src)] <- "lite"
  dist <- toupper(trimws(col("district")))
  state <- sub("-.*$", "", dist)
  if (identical(chamber, "House")) {
    dn <- suppressWarnings(as.integer(sub("^[A-Z]{2}-", "", dist)))
    one <- stats::ave(dn, state, cyc, FUN = function(v) { u <- unique(v[!is.na(v)]); rep(length(u) == 1L && u[1] == 1L, length(v)) })
    race <- paste0(state, "-", ifelse(one == 1, "00", sprintf("%02d", dn)))
    at_large <- one == 1
  } else {
    race <- dist; at_large <- rep(FALSE, n)
  }
  backf <- if ("backfilled" %in% names(df)) .truthy_col(df$backfilled) else (!is.na(rt) & !is.na(fd) & as.numeric(rt - fd) >= 2)
  rows <- data.frame(row = seq_len(n), cycle = cyc, chamber = chamber, race = race, state = state, district_538 = dist,
                     at_large = at_large, source = src, forecastdate = fd, run_date = rt, available = avail, available_sens = avail_sens,
                     backfilled = backf,
                     p_dem_party = num("winner_Dparty"), p_rep_party = num("winner_Rparty"),
                     p_other = rowSums(cbind(num("winner_I1"), num("winner_O1")), na.rm = TRUE), stringsAsFactors = FALSE)
  sl <- lapply(names(SGS_SEATS_SLOTS), function(s) {
    nm <- trimws(col(paste0("name_", s)))
    k <- which(!is.na(nm) & nzchar(nm))
    data.frame(row = k, slot = rep(s, length(k)), party = rep(SGS_SEATS_SLOTS[[s]], length(k)), name = nm[k],
               p = num(paste0("winner_", s))[k], stringsAsFactors = FALSE)
  })
  slots <- do.call(rbind, sl)
  cnt <- function(pty) tabulate(slots$row[slots$party == pty], nbins = n)
  # workbook 11's flags as built (coordinator's ruling: same_party_flag = two or more same-party candidates with a win
  # chance above 0; multiparty_flag = a non-D/R candidate with a chance above 0); computed from the slots otherwise
  rows$same_party <- if ("same_party_flag" %in% names(df)) .truthy_col(df$same_party_flag) else cnt("D") >= 2 | cnt("R") >= 2
  rows$multiparty <- if ("multiparty_flag" %in% names(df)) .truthy_col(df$multiparty_flag) else cnt("I") >= 1 | rows$p_other > 0
  fav <- slots[order(slots$row, -slots$p, method = "radix"), , drop = FALSE]
  fav <- fav[!duplicated(fav$row), , drop = FALSE]
  rows$favorite_p <- NA_real_; rows$favorite_party <- NA_character_
  rows$favorite_p[fav$row] <- fav$p; rows$favorite_party[fav$row] <- fav$party
  rows$n_top <- tabulate(slots$row[!is.na(slots$p) & abs(slots$p - rows$favorite_p[slots$row]) < 1e-12], nbins = n)
  slots <- cbind(slots, rows[slots$row, c("cycle", "chamber", "race", "state", "source"), drop = FALSE])
  rownames(slots) <- NULL
  list(rows = rows, slots = slots)
}

# ---- recipients and the name map -------------------------------------------------------------------------------------
# 10 recipient_classification -> one row per cycle x chamber x cand_id (dollars = 08 committee-map dollars summed).
sgs_seats_recipients <- function(rc) {
  num <- function(v) suppressWarnings(as.numeric(v))
  d <- data.frame(cycle = as.integer(num(rc$cycle)), chamber = as.character(rc$chamber), cand_id = as.character(rc$cand_id),
                  name = as.character(rc$candidate_name), party = .seats_party3(rc$party), state = toupper(trimws(as.character(rc$state))),
                  district = as.character(rc$district), committee_id = as.character(rc$committee_id),
                  fec_ico = toupper(trimws(as.character(rc$fec_incumbent_challenger_open))),
                  usd = if ("committee_map_nominal_usd" %in% names(rc)) num(rc$committee_map_nominal_usd) else NA_real_,
                  active = if ("eligible_current_election_and_chamber" %in% names(rc)) .truthy_col(rc$eligible_current_election_and_chamber) else NA,
                  stringsAsFactors = FALSE)
  d <- d[!is.na(d$cand_id) & nzchar(d$cand_id) & d$chamber %in% SGS_SEATS_CHAMBERS, , drop = FALSE]
  dn <- suppressWarnings(as.integer(d$district))
  d$district2 <- ifelse(is.na(dn), NA_character_, sprintf("%02d", dn))
  key <- paste(d$cycle, d$chamber, d$cand_id)
  usd <- tapply(ifelse(is.na(d$usd), 0, d$usd), key, sum)
  ncom <- tapply(d$committee_id, key, function(v) length(unique(v)))
  act <- tapply(d$active, key, function(v) any(v %in% TRUE))
  u <- d[!duplicated(key), , drop = FALSE]
  uk <- paste(u$cycle, u$chamber, u$cand_id)
  u$usd <- as.numeric(usd[uk]); u$n_committees <- as.integer(ncom[uk]); u$active <- as.logical(act[uk])
  u$committee_id <- NULL
  rownames(u) <- NULL
  u
}
# Distinct named slots -> cand_id: surname within cycle, chamber, state (House: district) and party; first name breaks a
# tie; otherwise ambiguous. Returns the map (one row per distinct cycle x chamber x race x party x name).
sgs_seats_name_map <- function(slots, cands) {
  k <- unique(slots[, c("cycle", "chamber", "race", "state", "party", "name")])
  rownames(k) <- NULL
  t538 <- lapply(.seats_tokens(k$name), .seats_strip_suffix)
  fe <- .seats_fec_name(cands$name)
  k$cand_id <- NA_character_; k$match_status <- "unmatched"; k$n_pool <- 0L; k$n_hits <- 0L; k$rule <- ""
  for (i in seq_len(nrow(k))) {
    pool <- which(cands$cycle == k$cycle[i] & cands$chamber == k$chamber[i] & cands$state == k$state[i] & cands$party == k$party[i])
    if (identical(k$chamber[i], "House")) pool <- pool[!is.na(cands$district2[pool]) & cands$district2[pool] == sub("^[A-Z]{2}-", "", k$race[i])]
    k$n_pool[i] <- length(pool)
    if (!length(pool)) next
    hit <- pool[vapply(pool, function(j) .seats_surname_hit(t538[[i]], fe$last[[j]]), TRUE)]
    k$n_hits[i] <- length(hit)
    if (!length(hit)) next
    f538 <- if (length(t538[[i]])) t538[[i]][1] else ""
    lev <- vapply(hit, function(j) .seats_given_level(f538, fe$given[[j]]), 0L)
    best <- max(lev)
    top <- hit[lev == best]
    lab <- c("surname only (given name not among the FEC given names: flagged)", "surname + initial", "surname + nickname", "surname + given name")[best + 1L]
    if (length(hit) == 1L) {
      k$cand_id[i] <- cands$cand_id[hit]; k$match_status[i] <- "matched"; k$rule[i] <- lab
    } else if (length(top) == 1L && best > 0L) {
      k$cand_id[i] <- cands$cand_id[top]; k$match_status[i] <- "matched"; k$rule[i] <- paste0(lab, " (", length(hit), " surname hits)")
    } else {
      k$match_status[i] <- "ambiguous"; k$rule[i] <- paste0(length(hit), " surname hits; given names do not separate them")
    }
  }
  k
}

# ---- incumbency at an origin from the dated service intervals ------------------------------------------------------
# terms: 10 candidate_service_terms. Returns one row per (cand_id, origin) pair asked for.
sgs_seats_status_at <- function(pairs, terms, chamber) {
  t <- data.frame(cand_id = as.character(terms$cand_id), chamber = as.character(terms$chamber), start = .seats_day(terms$start),
                  end = .seats_day(terms$end), index = suppressWarnings(as.integer(terms$term_index_same_chamber)),
                  how = tolower(as.character(if ("how" %in% names(terms)) terms$how else rep("", nrow(terms)))), stringsAsFactors = FALSE)
  t <- t[t$chamber == chamber & !is.na(t$start), , drop = FALSE]
  t$end[is.na(t$end)] <- as.Date("9999-12-31")
  by <- split(seq_len(nrow(t)), t$cand_id)
  n <- nrow(pairs)
  st <- rep("non-incumbent", n); idx <- rep(NA_integer_, n); appt <- partial <- noncons <- rep(FALSE, n); serv_start <- rep(as.Date(NA), n)
  for (i in seq_len(n)) {
    ix <- by[[pairs$cand_id[i]]]
    if (is.null(ix)) next
    W <- pairs$week_start[i]
    cur <- ix[t$start[ix] <= W & W < t$end[ix]]
    if (!length(cur)) next
    j <- cur[which.max(t$start[cur])]
    idx[i] <- t$index[j]; serv_start[i] <- t$start[j]
    st[i] <- if (!is.na(t$index[j]) && t$index[j] == 1L) "first_term_incumbent" else "established_incumbent"
    appt[i] <- grepl("appoint", t$how[j])
    partial[i] <- identical(st[i], "first_term_incumbent") && (grepl("special", t$how[j]) || format(t$start[j], "%m-%d") != "01-03")
    prev <- ix[t$end[ix] <= t$start[j]]
    noncons[i] <- length(prev) > 0 && !any(t$end[prev] == t$start[j])
  }
  data.frame(cand_id = pairs$cand_id, week_start = pairs$week_start, status = st, term_index = idx, term_start = serv_start,
             appointment = appt, partial_first_term = partial, nonconsecutive = noncons, stringsAsFactors = FALSE)
}

# ---- 538 classes ---------------------------------------------------------------------------------------------------
# fold = TRUE: the candidate-relative band of max(p, 1 - p) (class538_own, a sensitivity). fold = FALSE: the band of the
# race favourite's own probability as given (class538). The favourite's probability is the largest in the row, so the fold
# changes nothing in a two-candidate race; in a race of three or more (2022 AK-00: Peltola, Palin, Begich) the favourite can
# be below 0.5, and folding it (0.39 -> 0.61) would call a toss-up "lean".
.seats_538_class <- function(p, fold = TRUE) {
  q <- if (fold) pmax(p, 1 - p) else p
  out <- ifelse(q < 0.60, "toss-up", ifelse(q < 0.75, "lean", ifelse(q < 0.95, "likely", "safe")))
  out[is.na(p)] <- NA_character_
  out
}
.seats_side <- function(p) ifelse(is.na(p), NA_character_, ifelse(p > 0.5, "favored", ifelse(p < 0.5, "underdog", "even")))

# ---- the candidate x origin exposure ---------------------------------------------------------------------------------
# Race x origin -> the row used: the latest forecast date among the rows AVAILABLE strictly before the window (the rule
# 09 uses and the coordinator accepted; a backfilled old-dated row never overrides a newer forecast).
.seats_select_rows <- function(rs, origins) {
  rs <- rs[!is.na(rs$available), , drop = FALSE]
  if (!nrow(rs)) return(data.frame(race = character(0), week_start = as.Date(character(0)), row = integer(0)))
  rs <- rs[order(rs$race, rs$forecastdate, rs$run_date, rs$available, method = "radix"), , drop = FALSE]
  by <- split(seq_len(nrow(rs)), rs$race)
  do.call(rbind, lapply(names(by), function(rc) {
    ix <- by[[rc]]; av <- as.numeric(rs$available[ix])
    row <- vapply(as.numeric(origins), function(W) { k <- which(av < W); if (length(k)) as.integer(rs$row[ix[max(k)]]) else NA_integer_ }, 0L)
    data.frame(race = rc, week_start = origins, row = row, stringsAsFactors = FALSE)
  }))
}
# r538: sgs_seats_538_rows() of one chamber; map: sgs_seats_name_map(); cands: sgs_seats_recipients() of the chamber;
# terms: 10 service terms; origins: Mondays of the cycle. Returns list(exposure, nominee, diag).
sgs_seats_exposure <- function(r538, map, cands, terms, origins, chamber, calendar = NULL) {
  rows <- r538$rows; slots <- r538$slots
  mk <- paste(map$cycle, map$chamber, map$race, map$party, map$name)
  slots$cand_id <- map$cand_id[match(paste(slots$cycle, slots$chamber, slots$race, slots$party, slots$name), mk)]
  # the candidate's race(s): races whose rows ever name the candidate
  cr <- unique(slots[!is.na(slots$cand_id), c("cand_id", "race")])
  cr$multi_race <- cr$cand_id %in% cr$cand_id[duplicated(cr$cand_id)]
  # the named major-party matchup of every row (D and R slots: cand_ids, else the names; a third-party slot never makes
  # the matchup provisional) and each race's final matchup (its last Lite row by forecast date)
  dr <- slots[slots$party %in% c("D", "R"), , drop = FALSE]
  un <- unique(dr$name[is.na(dr$cand_id)])                     # an unmatched name counts by party and surname (spelling-proof)
  sur <- setNames(vapply(lapply(.seats_tokens(un), .seats_strip_suffix), function(t) if (length(t)) t[length(t)] else "", ""), un)
  setkey <- tapply(ifelse(is.na(dr$cand_id), paste0("~", dr$party, ":", sur[dr$name]), dr$cand_id), dr$row, function(v) paste(sort(unique(v)), collapse = "|"))
  rows$set <- as.character(setkey[as.character(rows$row)])
  rows$set[is.na(rows$set)] <- ""
  rl <- rows[rows$source == "lite", , drop = FALSE]
  rl <- rl[order(rl$race, rl$forecastdate, rl$run_date, method = "radix"), , drop = FALSE]
  fin_set <- tapply(rl$set, rl$race, function(v) v[length(v)])
  chg_n <- tapply(rl$set, rl$race, function(v) sum(v[-1] != v[-length(v)]))
  lite_sel <- .seats_select_rows(rows[rows$source == "lite", , drop = FALSE], origins)
  lite_sel$final <- rows$set[match(lite_sel$row, rows$row)] == as.character(fin_set[lite_sel$race])
  # the availability sensitivity: plain available_at (no launch floor)
  rsn <- rows[rows$source == "lite", , drop = FALSE]; rsn$available <- rsn$available_sens
  sens_sel <- .seats_select_rows(rsn, origins)
  lite_sel$row_sens <- sens_sel$row[match(paste(lite_sel$race, lite_sel$week_start), paste(sens_sel$race, sens_sel$week_start))]
  a1 <- lite_sel$row; a2 <- lite_sel$row_sens
  sens_diff <- sum(ifelse(is.na(a1) & is.na(a2), FALSE, ifelse(is.na(a1) | is.na(a2), TRUE, a1 != a2)))
  nominee <- lapply(split(seq_len(nrow(lite_sel)), lite_sel$race), function(ix) {
    ok <- lite_sel$final[ix] %in% TRUE; wk <- lite_sel$week_start[ix]
    first <- if (all(ok)) min(wk) else if (!ok[length(ok)]) NA else wk[max(which(!ok)) + 1L]
    list(race = lite_sel$race[ix[1]], matchup_final_from = as.numeric(first), final_matchup = as.character(fin_set[lite_sel$race[ix[1]]]),
         changes = as.integer(chg_n[lite_sel$race[ix[1]]]))
  })
  nom <- sgs_rows_df(unname(nominee), c("race", "matchup_final_from", "final_matchup", "changes"))
  nom$matchup_final_from <- as.Date(nom$matchup_final_from, origin = "1970-01-01")
  cal <- NULL
  if (!is.null(calendar) && nrow(calendar)) {
    cal <- data.frame(state = toupper(trimws(calendar$state)), primary = .seats_day(calendar$primary_date),
                      runoff = if ("runoff_date" %in% names(calendar)) .seats_day(calendar$runoff_date) else as.Date(NA), stringsAsFactors = FALSE)
  }
  out <- list()
  for (src in intersect(SGS_SEATS_538_SOURCES, unique(rows$source))) {
    sel <- if (src == "lite") lite_sel[, c("race", "week_start", "row")] else .seats_select_rows(rows[rows$source == src, , drop = FALSE], origins)
    e <- merge(cands[, intersect(c("cycle", "cand_id", "name", "party", "state", "district2", "fec_ico", "usd", "active"), names(cands))], cr,
               by = "cand_id", all.x = TRUE)
    e <- merge(e, data.frame(week_start = origins), by = NULL)
    e <- merge(e, sel, by = c("race", "week_start"), all.x = TRUE)
    sk <- paste(slots$row, slots$cand_id)
    j <- match(paste(e$row, e$cand_id), sk)
    e$named <- !is.na(j)
    e$slot <- slots$slot[j]; e$name_538 <- slots$name[j]; e$own_p <- slots$p[j]
    rr <- match(e$row, rows$row)
    e$row_forecastdate <- rows$forecastdate[rr]; e$row_available <- rows$available[rr]; e$backfilled <- rows$backfilled[rr]
    e$same_party <- rows$same_party[rr]; e$multiparty <- rows$multiparty[rr]
    e$favorite_party <- rows$favorite_party[rr]; e$favorite_p <- rows$favorite_p[rr]
    # the race's 538 class from the favourite candidate's own probability (538's evaluation convention; equal to
    # max(p, 1 - p) in a two-candidate race); the candidate-relative band max(p, 1 - p) is kept as a sensitivity
    e$class538 <- ifelse(e$named, .seats_538_class(e$favorite_p, fold = FALSE), NA_character_)
    e$class538_own <- .seats_538_class(e$own_p)
    top <- e$named & !is.na(e$own_p) & abs(e$own_p - e$favorite_p) < 1e-12
    e$side538 <- ifelse(!e$named, NA_character_, ifelse(top & rows$n_top[rr] > 1, "even", ifelse(top, "favored", "underdog")))
    e$source <- src
    e$reason <- ifelse(is.na(e$race), "never named in any 538 row of the candidate's race",
                       ifelse(is.na(e$row), "no 538 row of the race available before the window",
                              ifelse(!e$named, "not named in the latest available row (primary loser, withdrawn or not yet listed)", "")))
    out[[src]] <- e
  }
  ex <- do.call(rbind, out)
  rownames(ex) <- NULL
  pr <- unique(ex[, c("cand_id", "week_start")])
  st <- sgs_seats_status_at(pr, terms, chamber)
  ex <- merge(ex, st, by = c("cand_id", "week_start"), all.x = TRUE)
  # in the current election: FEC-eligible for this election and chamber (10, provisional) or named in the window's row
  # (a senator not up this cycle, such as Ossoff in 2022, is not a candidate of this election)
  if (!"active" %in% names(ex)) ex$active <- NA
  ex$in_election <- (ex$active %in% TRUE) | ex$named
  ex$favored_nonincumbent <- ex$status == "non-incumbent" & ex$named & !is.na(ex$own_p) & ex$own_p > SGS$SEATS_FAVORED_P
  ex$favored_nonincumbent_p60 <- ex$status == "non-incumbent" & ex$named & !is.na(ex$own_p) & ex$own_p > SGS$SEATS_FAVORED_P_SENS
  ex$fec_role_provisional <- ifelse(ex$fec_ico == "C", "challenger", ifelse(ex$fec_ico == "O", "open seat", ifelse(ex$fec_ico == "I", "incumbent", "unknown")))
  ex$fec_says_incumbent_not_serving <- ex$fec_ico == "I" & ex$status == "non-incumbent"
  # the window's selected Lite row does not yet show the race's final matchup
  lf <- lite_sel$final[match(paste(ex$race, ex$week_start), paste(lite_sel$race, lite_sel$week_start))]
  ex$pre_matchup_final <- !is.na(ex$race) & !(lf %in% TRUE)
  if (!is.null(cal)) {
    pc <- cal[match(ex$state, cal$state), , drop = FALSE]
    last <- as.Date(pmax(as.numeric(pc$primary), as.numeric(pc$runoff), na.rm = TRUE), origin = "1970-01-01")
    ex$pre_primary <- !is.na(last) & ex$week_start <= last
    ex$nominee_basis <- "official primary calendar"
  } else {
    ex$pre_primary <- ex$pre_matchup_final
    ex$nominee_basis <- "proxy: named 538 matchup final"
  }
  ex <- ex[order(ex$source, ex$cand_id, ex$week_start, method = "radix"), , drop = FALSE]
  rownames(ex) <- NULL
  list(exposure = ex, nominee = nom, sens_diff = sens_diff, race_weeks = nrow(lite_sel))
}

# ---- expert ratings -------------------------------------------------------------------------------------------------
sgs_seats_expert_frame <- function(rh) {
  num <- function(v) suppressWarnings(as.numeric(v))
  race <- toupper(trimws(as.character(rh$race_id)))
  special <- grepl("-SPECIAL$", race)
  race <- sub("-SPECIAL$", "", race)
  b <- gsub("[^a-z]", "", tolower(as.character(rh$bucket)))
  cat <- ifelse(b %in% c("tossup", "toss"), "toss-up", ifelse(b %in% c("lean", "likely", "safe"), b, NA_character_))
  tilt <- .truthy_col(rh$tilt_flag)
  d <- data.frame(cycle = as.integer(num(rh$cycle)), chamber = as.character(rh$chamber), race = race, special = special,
                  source = tolower(trimws(as.character(rh$source))), category = ifelse(tilt, "tilt", cat),
                  bucket4_tilt_lean = ifelse(tilt, "lean", cat), bucket4_tilt_tossup = ifelse(tilt, "toss-up", cat),
                  favored_party = toupper(trimws(as.character(rh$favored_party))), available = .seats_day(rh$availability_date_conservative),
                  primary = .truthy_col(rh$timing_eligible_primary), extended = .truthy_col(rh$timing_eligible_extended),
                  evidence_kind = as.character(if ("evidence_kind" %in% names(rh)) rh$evidence_kind else NA), stringsAsFactors = FALSE)
  # a state's regular and concurrent special Senate race of the same class: keep the regular one (the forecast has one)
  d <- d[!(d$special & paste(d$cycle, d$chamber, d$race) %in% paste(d$cycle, d$chamber, d$race)[!d$special]), , drop = FALSE]
  rownames(d) <- NULL
  d
}
# The latest rating per race x source available strictly before each origin, for one whitelist ("primary" or
# "extended"). Returns race x source x origin rows (unrated where none).
sgs_seats_expert_at <- function(ef, races, origins, cycle, chamber, whitelist = "primary") {
  e <- ef[ef$cycle == cycle & ef$chamber == chamber & ef[[whitelist]] & !is.na(ef$available), , drop = FALSE]
  out <- list()
  for (src in SGS_SEATS_EXPERT_SOURCES) {
    x <- e[e$source == src, , drop = FALSE]
    x <- x[order(x$race, x$available, method = "radix"), , drop = FALSE]
    by <- split(seq_len(nrow(x)), x$race)
    g <- expand.grid(race = races, week_start = origins, stringsAsFactors = FALSE)
    g$source <- src; g$category <- "unrated"; g$favored_party <- NA_character_; g$rating_available <- as.Date(NA)
    g$bucket4_tilt_lean <- "unrated"; g$bucket4_tilt_tossup <- "unrated"
    for (rc in intersect(races, names(by))) {
      ix <- by[[rc]]
      k <- which(g$race == rc)
      pos <- findInterval(as.numeric(g$week_start[k]) - 1, as.numeric(x$available[ix]))
      h <- pos > 0
      j <- ix[pos[h]]
      g$category[k[h]] <- x$category[j]; g$favored_party[k[h]] <- x$favored_party[j]; g$rating_available[k[h]] <- x$available[j]
      g$bucket4_tilt_lean[k[h]] <- x$bucket4_tilt_lean[j]; g$bucket4_tilt_tossup[k[h]] <- x$bucket4_tilt_tossup[j]
    }
    out[[src]] <- g
  }
  r <- do.call(rbind, out)
  r$whitelist <- whitelist
  rownames(r) <- NULL
  r
}

# ---- money (09 committee sheet) and the estimand B / C engines --------------------------------------------------------
# 09 committee sheet + 10 recipient map -> candidate x week x sector money: gross (positive receipts), refunds, net.
sgs_seats_money <- function(w, rc) {
  cm <- w$wb$frames[[SGS_SEATS_09_MONEY$sheet]]
  if (is.null(cm)) return(list(ok = FALSE, reason = paste0(SGS$SEATS_W_FILE, " has no sheet ", SGS_SEATS_09_MONEY$sheet, " (",
                                                          paste(c(SGS_SEATS_09_MONEY$required, SGS_SEATS_09_MONEY$optional), collapse = ", "), ")")))
  miss <- setdiff(SGS_SEATS_09_MONEY$required, names(cm))
  if (length(miss)) return(list(ok = FALSE, reason = paste0(SGS$SEATS_W_FILE, " [", SGS_SEATS_09_MONEY$sheet, "] lacks ", paste(miss, collapse = ", "))))
  num <- function(v) suppressWarnings(as.numeric(v))
  wk <- .seats_day(cm$week_start)
  cyc <- if ("fec_cycle" %in% names(cm)) suppressWarnings(as.integer(sub("^.*-", "", as.character(cm$fec_cycle)))) else .seats_cycle_of(wk)
  m <- data.frame(study_sector = as.character(cm$study_sector), committee_id = as.character(cm$committee_id), week_start = wk,
                  cycle = cyc, gross = num(cm$gross_usd),
                  refund = if ("refund_usd" %in% names(cm)) num(cm$refund_usd) else 0,
                  net = if ("usd" %in% names(cm)) num(cm$usd) else NA_real_,
                  party09 = if ("party" %in% names(cm)) as.character(cm$party) else NA_character_, stringsAsFactors = FALSE)
  # a week split at 1 January is two rows: one per committee x sector x week
  k1 <- paste(m$committee_id, m$study_sector, m$week_start, m$cycle, sep = "\r")
  if (anyDuplicated(k1)) {
    s <- lapply(c(gross = "gross", refund = "refund", net = "net"), function(v) tapply(m[[v]], k1, sum))
    m <- m[!duplicated(k1), , drop = FALSE]
    kk <- paste(m$committee_id, m$study_sector, m$week_start, m$cycle, sep = "\r")
    for (v in names(s)) m[[v]] <- as.numeric(s[[v]][kk])
  }
  key <- paste(suppressWarnings(as.integer(rc$cycle)), as.character(rc$committee_id))
  j <- match(paste(m$cycle, m$committee_id), key)
  m$cand_id <- as.character(rc$cand_id)[j]; m$chamber <- as.character(rc$chamber)[j]
  m$party <- ifelse(!is.na(m$party09) & nzchar(m$party09), ifelse(m$party09 %in% c("D", "R"), m$party09, "I"), .seats_party3(rc$party)[j])
  list(ok = TRUE, reason = "", money = m[!is.na(m$cand_id), , drop = FALSE], unmatched_committee_rows = sum(is.na(j)),
       unmatched_gross = sum(m$gross[is.na(j)], na.rm = TRUE), matched_gross = sum(m$gross[!is.na(j)], na.rm = TRUE))
}

# One group's weekly series: eligible candidates (selector at each origin) and their money in that week.
.seats_group_week <- function(ex, money, weeks, sel) {
  rows <- lapply(seq_along(weeks), function(i) {
    W <- weeks[i]
    el <- unique(ex$cand_id[ex$week_start == W & sel])
    party <- ex$party[match(el, ex$cand_id)]
    mm <- money[money$week_start == W & money$cand_id %in% el, , drop = FALSE]
    d <- sum(mm$gross[mm$party == "D"], na.rm = TRUE); r <- sum(mm$gross[mm$party == "R"], na.rm = TRUE)
    bys <- split(mm, mm$study_sector)
    shs <- vapply(bys, function(z) { dd <- sum(z$gross[z$party == "D"], na.rm = TRUE); rr <- sum(z$gross[z$party == "R"], na.rm = TRUE)
      if (dd + rr > 0) 100 * dd / (dd + rr) else NA_real_ }, 0)
    list(week_start = as.numeric(W), n_eligible = length(el), n_eligible_d = sum(party == "D"), n_eligible_r = sum(party == "R"),
         d_gross = d, r_gross = r, total_gross = sum(mm$gross, na.rm = TRUE), refunds = sum(mm$refund, na.rm = TRUE),
         net = sum(mm$net, na.rm = TRUE), share_pooled = if (d + r > 0) 100 * d / (d + r) else NA_real_,
         share_equal = if (sum(!is.na(shs)) >= 3) mean(shs, na.rm = TRUE) else NA_real_,
         d_per_cand = if (sum(party == "D")) d / sum(party == "D") else NA_real_,
         r_per_cand = if (sum(party == "R")) r / sum(party == "R") else NA_real_,
         total_per_cand = if (length(el)) sum(mm$gross, na.rm = TRUE) / length(el) else NA_real_)
  })
  s <- sgs_rows_df(rows, c("week_start", "n_eligible", "n_eligible_d", "n_eligible_r", "d_gross", "r_gross", "total_gross", "refunds",
                           "net", "share_pooled", "share_equal", "d_per_cand", "r_per_cand", "total_per_cand"))
  s$week_start <- as.Date(s$week_start, origin = "1970-01-01")
  s
}
SGS_SEATS_B_OUTCOMES <- c(share_equal = "D share of gross receipts, equal-sector mean (pp)",
                          d_per_cand = "gross receipts to Democrats per eligible Democratic candidate ($)",
                          r_per_cand = "gross receipts to Republicans per eligible Republican candidate ($)")
SGS_SEATS_B_SENS_OUTCOMES <- c(share_pooled = "D share of gross receipts, pooled dollars (pp)", total_gross = "gross receipts, summed ($)",
                               net = "net receipts, summed ($; sensitivity)", refunds = "refunds, summed ($; reported separately)")
# The group-defining fields of every candidate held at their values at the fixed pre-spending origin W0.
SGS_SEATS_GROUP_FIELDS <- c("status", "favored_nonincumbent", "favored_nonincumbent_p60", "fec_ico", "named", "class538", "in_election")
.seats_fix_origin <- function(ex, W0) {
  at0 <- ex[ex$week_start == W0, , drop = FALSE]
  j <- match(ex$cand_id, at0$cand_id)
  for (v in intersect(SGS_SEATS_GROUP_FIELDS, names(ex))) ex[[v]] <- at0[[v]][j]
  ex
}
.seats_b_groups <- function(ex) {
  g <- list(first_term = ex$status %in% "first_term_incumbent", established = ex$status %in% "established_incumbent",
            favored_nonincumbent = ex$favored_nonincumbent %in% TRUE, favored_nonincumbent_p60 = ex$favored_nonincumbent_p60 %in% TRUE,
            favored_challenger_provisional = ex$favored_nonincumbent %in% TRUE & ex$fec_ico %in% "C",
            favored_open_provisional = ex$favored_nonincumbent %in% TRUE & ex$fec_ico %in% "O")
  for (cl in SGS_SEATS_538_CLASSES) {
    g[[paste0("class_", cl)]] <- ex$named %in% TRUE & ex$class538 %in% cl
    g[[paste0("favored_nonincumbent_x_", cl)]] <- ex$favored_nonincumbent %in% TRUE & ex$class538 %in% cl
  }
  g
}
# Estimand B: group weekly series on the national forecast change (nat: chamber-week d_seats), slopes and contrasts.
# Groups are fixed at the pre-spending origin W0 (the first window; PRIMARY: membership does not move with the
# donations) and, as a sensitivity, re-classified at every window's origin (rolling), with the transition counts.
sgs_seats_b_run <- function(ex, money, nat, chamber) {
  ex <- ex[ex$source == "lite", , drop = FALSE]
  nat <- nat[nat$chamber == chamber, , drop = FALSE]
  weeks <- sort(unique(nat$week_start))
  weeks <- weeks[weeks %in% ex$week_start]
  if (length(weeks) < 4) return(list(ok = FALSE, reason = "fewer than 4 weeks with both the national forecast change and race exposure"))
  W0 <- min(weeks)
  mkx <- function(s, y) { s$y_level <- s[[y]]; prev <- match(s$week_start - 7, s$week_start); s$y_lag <- s$y_level[prev]
    s$y_change <- s$y_level - s$y_lag; s }
  unit_of <- function(y) function(m) paste0(if (m == "change") "change in " else "", c(SGS_SEATS_B_OUTCOMES, SGS_SEATS_B_SENS_OUTCOMES)[[y]], " per forecast Democratic seat")
  rows <- list(); series <- list(); trans <- list(); blocks <- character(0)
  roll_ex <- ex[ex$in_election %in% TRUE, , drop = FALSE]
  fix_ex <- .seats_fix_origin(ex, W0); fix_ex <- fix_ex[fix_ex$in_election %in% TRUE, , drop = FALSE]
  gr_roll <- .seats_b_groups(roll_ex); gr_fix <- .seats_b_groups(fix_ex)
  for (g in names(gr_fix)) {
    fixed_c <- unique(fix_ex$cand_id[gr_fix[[g]]]); roll_c <- unique(roll_ex$cand_id[gr_roll[[g]]])
    ever_out <- vapply(fixed_c, function(cid) any(!gr_roll[[g]][roll_ex$cand_id == cid]), TRUE)
    trans[[length(trans) + 1L]] <- list(chamber = chamber, group = g, origin = format(W0), candidates_fixed = length(fixed_c),
                                        candidates_ever_rolling = length(roll_c), rolling_not_fixed = length(setdiff(roll_c, fixed_c)),
                                        fixed_leaving_in_some_week = sum(ever_out))
  }
  for (regime in c("fixed", "rolling")) {
    exr <- if (regime == "fixed") fix_ex else roll_ex
    groups <- if (regime == "fixed") gr_fix else gr_roll
    lab <- if (regime == "fixed") paste0("fixed at the pre-spending origin ", format(W0), " (primary)") else "rolling: re-classified each window (sensitivity)"
    ser <- lapply(groups, function(sel) {
      s <- .seats_group_week(exr, money, weeks, sel)
      m <- match(s$week_start, nat$week_start)
      s$d_seats <- nat$d_seats[m]; s$cycle <- nat$cycle[m]; s$week_of_cycle <- nat$week_of_cycle[m]
      s
    })
    series[[regime]] <- do.call(rbind, lapply(names(ser), function(g) cbind(classification = regime, group = g, ser[[g]], stringsAsFactors = FALSE)))
    add <- function(fits, grp, y, kind) {
      rr <- .seats_fit_rows(fits, list(chamber = chamber, source = "lite", weighting = y, money = "gross positive (primary)",
                                       availability = lab, window = "all weeks", omitted_sector = ""), unit_of(y))
      rows <<- c(rows, lapply(rr, function(r) c(r, list(group = grp, kind = kind, classification = regime))))
    }
    # the printed summary(lm()) blocks: the fixed-origin D-share series of the primary slopes and the contrasts
    bl <- function(fits, grp, y) {
      if (regime != "fixed" || y != "share_equal") return(invisible(NULL))
      for (r in fits) if (identical(r$scope, "pooled")) blocks <<- c(blocks, .seats_block(r,
        paste0("==== SEATS-B ", chamber, " ", grp, " ", r$model, " (groups fixed at ", format(W0), "; 538 Lite; D share of gross receipts, ",
               "equal-sector)  [EXPLORATORY; ", r$gate, "]"),
        .seats_dv_text(r$model, paste0(if (grepl("_minus_", grp)) "the weekly difference between the two groups' " else "the group's ",
                                       "Democratic share of gross receipts, equal-sector mean (percentage points)"), chamber)))
      invisible(NULL)
    }
    for (y in c(names(SGS_SEATS_B_OUTCOMES), names(SGS_SEATS_B_SENS_OUTCOMES))) {
      for (g in names(ser)) {
        kind_g <- if (g %in% c("first_term", "established", "favored_nonincumbent") || startsWith(g, "class_")) "slope" else "exploratory or sensitivity slope"
        fits_g <- .seats_fit_series(mkx(ser[[g]], y), "d_seats", paste(chamber, "B", regime, g, y), models = c("level", "change"), per_cycle = FALSE)
        add(fits_g, g, y, kind_g)
        if (kind_g == "slope") bl(fits_g, g, y)
      }
      diffs <- list(first_term_minus_established = c("first_term", "established"),
                    favored_nonincumbent_minus_established = c("favored_nonincumbent", "established"))
      for (cl in setdiff(SGS_SEATS_538_CLASSES, "safe")) diffs[[paste0(cl, "_minus_safe")]] <- c(paste0("class_", cl), "class_safe")
      for (dn in names(diffs)) {
        a <- mkx(ser[[diffs[[dn]][1]]], y); b <- mkx(ser[[diffs[[dn]][2]]], y)
        a$y_level <- a$y_level - b$y_level; prev <- match(a$week_start - 7, a$week_start); a$y_lag <- a$y_level[prev]; a$y_change <- a$y_level - a$y_lag
        fits_d <- .seats_fit_series(a, "d_seats", paste(chamber, "B", regime, dn, y), models = c("level", "change"), per_cycle = FALSE)
        add(fits_d, dn, y, "contrast"); bl(fits_d, dn, y)
      }
    }
  }
  fam <- function(r) {
    if (!identical(r$classification, "fixed") || !r$weighting %in% names(SGS_SEATS_B_OUTCOMES) || r$scope != "pooled" ||
        !r$model %in% c("level", "change") || r$gate != "estimated") return("")
    if (r$group %in% c("first_term_minus_established", "favored_nonincumbent_minus_established")) return(paste0("B incumbency contrasts, ", chamber, ", ", r$weighting))
    if (startsWith(r$group, "class_") || grepl("_minus_safe$", r$group)) return(paste0("B 538-class slopes and interactions, ", chamber, ", ", r$weighting))
    ""
  }
  rows <- .seats_holm(rows, function(r) nzchar(fam(r)), fam)
  list(ok = TRUE, reason = "", origin = W0, estimates = sgs_rows_df(rows, c(SGS_SEATS_W_COLS, "group", "kind", "classification")),
       series = do.call(rbind, series), blocks = blocks,
       transitions = sgs_rows_df(trans, c("chamber", "group", "origin", "candidates_fixed", "candidates_ever_rolling", "rolling_not_fixed",
                                          "fixed_leaving_in_some_week")))
}

# Estimand C: the candidate's own lagged win-probability change on the candidate's gross receipts, with the national
# exposure excluding the focal race, candidate effects and a week trend; fixed candidate set (named at every origin);
# week-block residual bootstrap within cycle (all candidates of a week move together).
sgs_seats_c_run <- function(ex, money, r538, chamber) {
  ex <- ex[ex$source == "lite" & ex$named & !is.na(ex$own_p), , drop = FALSE]
  weeks <- sort(unique(ex$week_start))
  keep <- names(which(table(ex$cand_id) == length(weeks)))
  ex <- ex[ex$cand_id %in% keep, , drop = FALSE]
  if (length(keep) < 3 || length(weeks) < SGS$SEATS_MIN_WEEKS) {
    return(list(ok = FALSE, reason = paste0("fixed candidate set: ", length(keep), " candidates named at all ", length(weeks), " origins (needs >= 3 and >= ",
                                            SGS$SEATS_MIN_WEEKS, " weeks)")))
  }
  # the national expected Democratic seats among the forecast races at each origin: every race's latest Lite row
  # available before the window (all races of the chamber, not only the candidate set); minus the focal race
  sel <- .seats_select_rows(r538$rows[r538$rows$source == "lite", , drop = FALSE], weeks)
  pdp <- r538$rows$p_dem_party[match(sel$row, r538$rows$row)]
  nat <- vapply(weeks, function(W) sum(pdp[sel$week_start == W], na.rm = TRUE), 0)
  pd <- r538$rows$p_dem_party[match(ex$row, r538$rows$row)]
  ex$e_nat <- nat[match(ex$week_start, weeks)]
  ex$e_excl <- ex$e_nat - pd
  g <- money[money$week_start %in% weeks & money$cand_id %in% keep, , drop = FALSE]
  y <- tapply(g$gross, paste(g$cand_id, g$week_start), sum)
  ex$y <- as.numeric(y[paste(ex$cand_id, ex$week_start)]); ex$y[is.na(ex$y)] <- 0
  ex <- ex[order(ex$cand_id, ex$week_start), , drop = FALSE]
  prev <- match(paste(ex$cand_id, ex$week_start - 7), paste(ex$cand_id, ex$week_start))
  ex$dp_own <- ex$own_p - ex$own_p[prev]; ex$de_excl <- ex$e_excl - ex$e_excl[prev]
  d <- ex[!is.na(ex$dp_own) & !is.na(ex$de_excl), , drop = FALSE]
  d$t <- as.numeric(d$week_start - min(d$week_start)) / 7
  dm <- function(v) v - stats::ave(v, d$cand_id)
  X <- cbind(dp_own = dm(d$dp_own), de_excl = dm(d$de_excl), trend = dm(d$t)); yy <- dm(d$y)
  if (qr(X)$rank < ncol(X)) return(list(ok = FALSE, reason = "rank-deficient candidate-week design"))
  b <- solve(crossprod(X), crossprod(X, yy)); e <- as.vector(yy - X %*% b)
  wk <- sort(unique(d$week_start)); wi <- match(d$week_start, wk)
  res <- list()
  for (L in SGS_SEATS_BLOCKS) {
    set.seed(.seats_seed(chamber, "C", paste0("L", L)))
    idx <- .seats_block_index(rep(1L, length(wk)), L, SGS_SEATS_BOOT_B)
    E <- matrix(NA_real_, length(unique(d$cand_id)), length(wk)); ci <- match(d$cand_id, unique(d$cand_id)); E[cbind(ci, wi)] <- e
    pinv <- solve(crossprod(X), t(X))
    Z <- X[, -1, drop = FALSE]; f0 <- as.vector(Z %*% solve(crossprod(Z), crossprod(Z, yy))); e0 <- yy - f0
    E0 <- matrix(NA_real_, nrow(E), ncol(E)); E0[cbind(ci, wi)] <- e0
    f <- as.vector(X %*% b)
    bs <- bn <- numeric(SGS_SEATS_BOOT_B)
    for (j in seq_len(SGS_SEATS_BOOT_B)) {
      es <- E[cbind(ci, idx[wi, j])]; e0s <- E0[cbind(ci, idx[wi, j])]
      bs[j] <- sum(pinv[1, ] * (f + ifelse(is.na(es), 0, es))); bn[j] <- sum(pinv[1, ] * (f0 + ifelse(is.na(e0s), 0, e0s)))
    }
    res[[paste0("L", L)]] <- list(ci = .seats_basic_ci(b[1], bs), p = .seats_null_p(b[1], bn))
  }
  list(ok = TRUE, reason = "", estimate = b[1], n = nrow(d), candidates = length(keep), weeks = length(wk), boot = res,
       unit = "$ of the candidate's weekly gross receipts per unit of own win probability (0-1)")
}

# ---- the orchestrator ------------------------------------------------------------------------------------------------
sgs_build_seats_race <- function(data_dir, now = NULL, w = NULL, wr = NULL) {
  out <- list(ok = FALSE, reason = "", sources = list(), chambers = list(), money = NULL, have10 = FALSE, have11 = FALSE)
  r10 <- sgs_seats_load_10(data_dir, now)
  r11 <- sgs_seats_load_input(data_dir, SGS$SEATS_11_FILE, SGS_SEATS_11_SHEETS, "seats_race_forecasts", now,
                              absent = "the verified 538 race forecasts and expert ratings are being imported")
  out$have10 <- isTRUE(r10$ok); out$have11 <- isTRUE(r11$ok)
  out$reason10 <- r10$reason; out$reason11 <- r11$reason
  if (out$have10) out$sources$seats_recipients <- r10$source
  if (out$have11) out$sources$seats_race_forecasts <- r11$source
  if (!out$have10 || !out$have11) {
    out$reason <- paste(c(if (!out$have10) r10$reason, if (!out$have11) r11$reason), collapse = "; ")
    return(out)
  }
  rc <- r10$wb$frames$recipient_classification; terms <- r10$wb$frames$candidate_service_terms
  cands_all <- sgs_seats_recipients(rc)
  ef <- if (!is.null(r11$wb$frames$rating_history_expert)) sgs_seats_expert_frame(r11$wb$frames$rating_history_expert) else NULL
  cal <- r11$wb$frames$primary_calendar
  if (!is.null(w)) {
    mo <- sgs_seats_money(w, rc)
    out$money <- mo
  } else {
    out$money <- list(ok = FALSE, reason = paste0(SGS$SEATS_W_FILE, " not built (", "the committee money and the national forecast series come from 09)"))
  }
  nat <- if (!is.null(wr) && !is.null(wr$series) && nrow(wr$series)) wr$series[wr$series$source == tolower(SGS$SEATS_W_PRIMARY), , drop = FALSE] else NULL
  sheets <- c(House = "house_district_538_2022", Senate = "senate_state_538_2022")
  for (ch in names(sheets)) {
    df <- r11$wb$frames[[sheets[[ch]]]]
    if (is.null(df)) { out$chambers[[ch]] <- list(ok = FALSE, reason = paste0(SGS$SEATS_11_FILE, " has no sheet ", sheets[[ch]])); next }
    r538 <- sgs_seats_538_rows(df, ch)
    cyc <- sort(unique(r538$rows$cycle))
    cands <- cands_all[cands_all$chamber == ch & cands_all$cycle %in% cyc, , drop = FALSE]
    map <- sgs_seats_name_map(r538$slots, cands)
    origins <- do.call(c, lapply(cyc, function(cy) {
      a <- r538$rows$available[r538$rows$cycle == cy]
      .seats_mondays(min(a, na.rm = TRUE) + 1, .seats_election_day(cy) - 7)
    }))
    ex <- sgs_seats_exposure(r538, map, cands, terms, origins, ch, calendar = cal)
    races <- sort(unique(stats::na.omit(ex$exposure$race)))
    expert <- if (!is.null(ef)) do.call(rbind, lapply(cyc, function(cy) rbind(
      sgs_seats_expert_at(ef, races, origins[.seats_cycle_of(origins) == cy], cy, ch, "primary"),
      sgs_seats_expert_at(ef, races, origins[.seats_cycle_of(origins) == cy], cy, ch, "extended")))) else NULL
    b <- if (isTRUE(out$money$ok) && !is.null(nat)) tryCatch(sgs_seats_b_run(ex$exposure, out$money$money, nat, ch), error = function(e) list(ok = FALSE, reason = conditionMessage(e))) else
      list(ok = FALSE, reason = if (!isTRUE(out$money$ok)) out$money$reason else "no national 538 Lite series from 09")
    cc <- if (isTRUE(out$money$ok)) tryCatch(sgs_seats_c_run(ex$exposure, out$money$money, r538, ch), error = function(e) list(ok = FALSE, reason = conditionMessage(e))) else
      list(ok = FALSE, reason = out$money$reason)
    out$chambers[[ch]] <- list(ok = TRUE, reason = "", rows = r538$rows, map = map, cands = cands, exposure = ex$exposure,
                               nominee = ex$nominee, expert = expert, origins = origins, b = b, c = cc,
                               sources_538 = sort(unique(r538$rows$source)), sens_diff = ex$sens_diff, race_weeks = ex$race_weeks)
  }
  out$ok <- any(vapply(out$chambers, function(z) isTRUE(z$ok), TRUE))
  out$reason <- if (out$ok) "" else paste(vapply(out$chambers, function(z) z$reason %||% "", ""), collapse = "; ")
  out
}

# ---- summaries for the report and the sheets -------------------------------------------------------------------------
# Match diagnostics per chamber.
sgs_seats_race_diag <- function(race) {
  rows <- list()
  for (ch in names(race$chambers)) {
    z <- race$chambers[[ch]]
    if (!isTRUE(z$ok)) next
    m <- z$map; ex <- z$exposure[z$exposure$source == "lite", , drop = FALSE]
    named_ever <- unique(ex$cand_id[ex$named])
    cu <- z$cands
    add <- function(metric, value, note = "") rows[[length(rows) + 1L]] <<- list(chamber = ch, metric = metric, value = value, note = note)
    add("538 rows read", nrow(z$rows), paste(z$sources_538, collapse = ", "))
    add("538 rows backfilled (run >= 2 days after the forecast date)", sum(z$rows$backfilled, na.rm = TRUE))
    add("race-weeks whose Lite row differs under plain available_at (availability sensitivity: no launch floor)", z$sens_diff %||% NA_real_,
        paste0("of ", z$race_weeks %||% NA, " race-weeks; primary = available_at_launch_floor"))
    add("races", length(unique(z$rows$race)), paste0(sum(z$rows$at_large[!duplicated(z$rows$race)]), " at-large (538 '-1' -> FEC '-00')"))
    add("distinct named 538 slots (race x party x name)", nrow(m))
    add("  matched to a recipient cand_id", sum(m$match_status == "matched"),
        paste0(sum(startsWith(m$rule, "surname only")), " by surname only (given name not among the FEC given names: flagged, listed in seats_race_match)"))
    add("  ambiguous (kept, no probability assigned)", sum(m$match_status == "ambiguous"))
    add("  unmatched (no recipient in the race: most never received sector money)", sum(m$match_status == "unmatched"))
    add("recipient candidates (cycle x cand_id)", nrow(cu), "08 committee-map recipients classified by Codex")
    add("  named in at least one available Lite row", length(named_ever))
    add("  share of recipients' 08 dollars on candidates named at least once", sum(cu$usd[cu$cand_id %in% named_ever], na.rm = TRUE) / sum(cu$usd, na.rm = TRUE),
        "dollar-weighted; whole-cycle 08 committee-map dollars")
    add("recipient candidate-weeks in the current election (FEC-eligible, provisional, or named in the window's row)", sum(ex$in_election),
        paste0("of ", nrow(ex), "; estimands B and C use these (a senator not up this cycle is not a candidate of this election)"))
    ca <- cu[cu$active %in% TRUE, , drop = FALSE]
    add("active-election recipients (FEC record lists the current election and chamber; provisional)", nrow(ca))
    add("  share of their 08 dollars on candidates named at least once", if (nrow(ca)) sum(ca$usd[ca$cand_id %in% named_ever], na.rm = TRUE) / sum(ca$usd, na.rm = TRUE) else NA_real_,
        "dollar-weighted; whole-cycle 08 committee-map dollars")
    add("origins (Mondays)", length(z$origins), paste0(format(min(z$origins)), " to ", format(max(z$origins))))
    add("rows in same-party races (Lite)", sum(z$rows$same_party & z$rows$source == "lite"))
    add("rows in multiparty races (Lite)", sum(z$rows$multiparty & z$rows$source == "lite"))
    add("favored non-incumbent candidate-weeks (p > 0.5)", sum(ex$favored_nonincumbent), paste0(length(unique(ex$cand_id[ex$favored_nonincumbent])), " candidates"))
    add("favored non-incumbent candidate-weeks (p > 0.6, sensitivity)", sum(ex$favored_nonincumbent_p60), paste0(length(unique(ex$cand_id[ex$favored_nonincumbent_p60])), " candidates"))
    add("FEC lists incumbent but no dated service at the origin (candidate-weeks)", sum(ex$fec_says_incumbent_not_serving, na.rm = TRUE))
    add("candidate-weeks before the named matchup was final", sum(ex$pre_matchup_final & ex$named), ex$nominee_basis[1] %||% "")
  }
  sgs_rows_df(rows, c("chamber", "metric", "value", "note"))
}
# Candidate-weeks by incumbency group x 538 class (Lite, named candidates) per chamber: the exposure census.
sgs_seats_race_census <- function(race) {
  rows <- list()
  for (ch in names(race$chambers)) {
    z <- race$chambers[[ch]]
    if (!isTRUE(z$ok)) next
    ex <- z$exposure[z$exposure$source == "lite" & z$exposure$in_election, , drop = FALSE]   # candidates of this election
    grp <- ifelse(ex$status == "non-incumbent", ifelse(ex$favored_nonincumbent, "favored non-incumbent", "other non-incumbent"), ex$status)
    for (g in c("first_term_incumbent", "established_incumbent", "favored non-incumbent", "other non-incumbent")) {
      k <- grp == g
      r <- list(chamber = ch, group = g, candidates = length(unique(ex$cand_id[k])), candidate_weeks = sum(k), named_weeks = sum(k & ex$named))
      for (cl in SGS_SEATS_538_CLASSES) r[[gsub("-", "_", cl)]] <- sum(k & ex$named & ex$class538 %in% cl)
      r$not_named <- sum(k & !ex$named)
      rows[[length(rows) + 1L]] <- r
    }
  }
  sgs_rows_df(rows, c("chamber", "group", "candidates", "candidate_weeks", "named_weeks", "toss_up", "lean", "likely", "safe", "not_named"))
}
# The favored non-incumbents: candidate, weeks, first and last week, probability range (Lite).
sgs_seats_favored_list <- function(race) {
  rows <- list()
  for (ch in names(race$chambers)) {
    z <- race$chambers[[ch]]
    if (!isTRUE(z$ok)) next
    ex <- z$exposure[z$exposure$source == "lite" & z$exposure$favored_nonincumbent, , drop = FALSE]
    for (cid in unique(ex$cand_id)) {
      x <- ex[ex$cand_id == cid, , drop = FALSE]
      rows[[length(rows) + 1L]] <- list(chamber = ch, cand_id = cid, fec_name = x$name[1], name_538 = x$name_538[1], party = x$party[1],
                                        race = x$race[1], fec_role_provisional = x$fec_role_provisional[1], weeks = nrow(x),
                                        first_week = format(min(x$week_start)), last_week = format(max(x$week_start)),
                                        p_min = min(x$own_p), p_max = max(x$own_p), weeks_p60 = sum(x$favored_nonincumbent_p60),
                                        weeks_pre_matchup_final = sum(x$pre_matchup_final))
    }
  }
  sgs_rows_df(rows, c("chamber", "cand_id", "fec_name", "name_538", "party", "race", "fec_role_provisional", "weeks", "first_week",
                      "last_week", "p_min", "p_max", "weeks_p60", "weeks_pre_matchup_final"))
}
# Weeks with at least one primary-eligible (and extended) expert rating per chamber x source.
sgs_seats_expert_support <- function(race) {
  rows <- list()
  for (ch in names(race$chambers)) {
    z <- race$chambers[[ch]]
    if (!isTRUE(z$ok) || is.null(z$expert)) next
    for (wl in c("primary", "extended")) for (src in SGS_SEATS_EXPERT_SOURCES) {
      x <- z$expert[z$expert$whitelist == wl & z$expert$source == src & z$expert$category != "unrated", , drop = FALSE]
      rows[[length(rows) + 1L]] <- list(chamber = ch, whitelist = wl, source = src, weeks = length(unique(x$week_start)),
                                        races_rated = length(unique(x$race)), race_weeks = nrow(x),
                                        tilt = sum(x$category == "tilt"), first_week = if (nrow(x)) format(min(x$week_start)) else "")
    }
  }
  sgs_rows_df(rows, c("chamber", "whitelist", "source", "weeks", "races_rated", "race_weeks", "tilt", "first_week"))
}

# The result-workbook sheets of the race level (dates as ISO text).
.seats_text_dates <- function(df) { for (nm in names(df)) if (inherits(df[[nm]], "Date")) df[[nm]] <- ifelse(is.na(df[[nm]]), NA_character_, format(df[[nm]], "%Y-%m-%d")); df }
sgs_seats_race_sheets <- function(race) {
  out <- list()
  if (!isTRUE(race$ok)) return(out)
  out$seats_race_diag <- sgs_seats_race_diag(race)
  out$seats_race_census <- sgs_seats_race_census(race)
  out$seats_race_favored <- sgs_seats_favored_list(race)
  es <- sgs_seats_expert_support(race)
  if (nrow(es)) out$seats_race_expert_support <- es
  mp <- list(); ex <- list(); nm <- list(); tr <- list()
  for (ch in names(race$chambers)) {
    z <- race$chambers[[ch]]
    if (!isTRUE(z$ok)) next
    mp[[ch]] <- z$map
    e <- z$exposure
    l <- e[e$source == "lite", , drop = FALSE]
    for (s in setdiff(unique(e$source), "lite")) {
      o <- e[e$source == s, , drop = FALSE]
      l[[paste0("own_p_", s)]] <- o$own_p[match(paste(l$cand_id, l$week_start, l$race), paste(o$cand_id, o$week_start, o$race))]
    }
    l$chamber <- ch
    keep <- c("chamber", "cycle", "cand_id", "name", "party", "state", "race", "week_start", "active", "in_election", "status", "term_index", "term_start",
              "appointment", "partial_first_term", "nonconsecutive", "fec_role_provisional", "fec_says_incumbent_not_serving", "named",
              "name_538", "slot", "own_p", grep("^own_p_", names(l), value = TRUE), "favorite_p", "favorite_party", "class538", "class538_own",
              "side538", "favored_nonincumbent", "favored_nonincumbent_p60", "same_party", "multiparty", "row_forecastdate", "row_available",
              "backfilled", "pre_matchup_final", "pre_primary", "nominee_basis", "reason")
    ex[[ch]] <- l[, intersect(keep, names(l)), drop = FALSE]
    nm[[ch]] <- cbind(chamber = ch, z$nominee, stringsAsFactors = FALSE)
    if (isTRUE(z$b$ok)) {
      out[[paste0("seats_b_", tolower(ch))]] <- z$b$estimates
      out[[paste0("seats_b_series_", tolower(ch))]] <- z$b$series
      tr[[ch]] <- z$b$transitions
    }
  }
  if (length(tr)) out$seats_b_transitions <- do.call(rbind, tr)
  out$seats_race_match <- do.call(rbind, mp)
  out$seats_race_exposure <- do.call(rbind, ex)
  out$seats_race_nominee <- do.call(rbind, nm)
  cc <- list()
  for (ch in names(race$chambers)) {
    z <- race$chambers[[ch]]
    if (!isTRUE(z$c$ok)) next
    for (L in SGS_SEATS_BLOCKS) {
      b <- z$c$boot[[paste0("L", L)]]
      cc[[length(cc) + 1L]] <- list(chamber = ch, block = L, estimate = z$c$estimate, ci_low = b$ci[1], ci_high = b$ci[2], p = b$p,
                                    n = z$c$n, candidates = z$c$candidates, weeks = z$c$weeks, unit = z$c$unit)
    }
  }
  if (length(cc)) out$seats_c_estimates <- sgs_rows_df(cc, c("chamber", "block", "estimate", "ci_low", "ci_high", "p", "n", "candidates", "weeks", "unit"))
  lapply(out, function(d) { rownames(d) <- NULL; .seats_text_dates(d) })
}

# ---- the cross-check references (read-only Codex outputs; quoted, never inputs) --------------------------------------
SGS_SEATS_CODEX_XCHECK <- list(
  estimates = "C:/Users/pgoff/Documents/Codex/2026-09-26/loo/outputs/seat_gain_extension/independent_weekly_estimates.csv (sha256 3c6ec08d1c13eb80...)",
  bootstrap = "C:/Users/pgoff/Documents/Codex/2026-09-26/loo/outputs/seat_gain_extension/independent_weekly_block_bootstrap.csv (sha256 425e5b35ad2ff451...)",
  validation = "C:/Users/pgoff/Documents/Codex/2026-09-26/loo/outputs/seat_gain_extension/independent_model_validation.json (sha256 3c5efedcea3a7f37...)",
  spec = paste0("Codex's independent check: 2022 only (17 usable weeks), net receipts of observed receiving committees whose FEC record ",
                "lists the current election, equal-sector mean D share, outcome on the prior week's change in expected Democratic ",
                "seats + a linear election-week trend + the LAGGED outcome + intercept, forecasts gated on forecast date and run ",
                "timestamp, HAC lags 2 and 4, conditional fixed-X residual block bootstrap (3- and 5-week blocks, 4,999 draws), Holm ",
                "over 42 declared tests"),
  rows = data.frame(
    chamber = c("House", "House", "Senate", "Senate", "Senate"),
    group = c("overall", "overall", "overall", "first-term incumbents", "first-term incumbents"),
    outcome = c("D share (pp)", "D share (pp)", "D share (pp)", "mean-sector D net $", "mean-sector D net $"),
    block = c(3, 5, 3, 3, 5),
    estimate = c(-3.12261201864081, -3.12261201864081, 5.66439616933263, -1717.55456543062, -1717.55456543062),
    ci_low = c(-4.91840070048445, -5.33529966955578, -21.392150117303, -3038.12432486726, -3165.3258755491),
    ci_high = c(-1.27235361910012, -0.92704592821219, 32.4714595951143, -462.763091507934, -808.717530638078),
    p_block = c(0.0094, 0.039, 0.6864, 0.0228, 0.0242),
    p_holm = c(0.3572, 1, 1, 0.8208, 0.9196),
    hac2_se = c(0.939635668495793, 0.939635668495793, 14.0887353759128, 402.282911751426, 402.282911751426),
    stringsAsFactors = FALSE),
  senate_first_term = paste0("Senate first-term incumbents, mean-sector D net dollars: -1,717.55 per seat with HAC(2) p 0.0009 and ",
                             "Holm(42) 0.038, but Holm 0.821 (3-week) and 0.920 (5-week) under the residual block bootstrap; ",
                             "leaving telecom out gives -497.18 (HAC(2) p 0.331); no sign reversal in the 8 leave-one-industry refits"))

# ---- cells: every requested cell gated estimated / descriptive only / unavailable, with the reason -------------------
SGS_SEATS_CELL_COLS <- c("estimand", "chamber", "cell", "status", "reason", "holm_family")
sgs_seats_cells <- function(seats, est_rows) {
  st <- setNames(vapply(est_rows, function(r) r$status, ""), vapply(est_rows, function(r) r$test_id, ""))
  w <- seats$w; race <- seats$race
  out <- list()
  add <- function(e, ch, cell, status, reason, fam = "") out[[length(out) + 1L]] <<- list(estimand = e, chamber = ch, cell = cell,
                                                                                         status = status, reason = reason, holm_family = fam)
  money_reason <- if (!is.null(race$money) && !isTRUE(race$money$ok)) race$money$reason else if (is.null(race$money)) "09 not read" else ""
  race_reason <- function(ch) {
    parts <- c(if (!isTRUE(race$have10)) race$reason10, if (!isTRUE(race$have11)) race$reason11,
               if (isTRUE(race$have10) && isTRUE(race$have11) && !isTRUE(race$chambers[[ch]]$ok)) race$chambers[[ch]]$reason)
    paste(parts, collapse = "; ")
  }
  for (ch in SGS_SEATS_CHAMBERS) {
    for (b in names(SGS_SEATS_BASES)) {
      id <- paste0("SEATS-A-", ch, "-", b)
      sti <- if (id %in% names(st)) st[[id]] else "not in this run"
      ok <- identical(sti, SGS_ESTIMABLE)
      add("SEATS-A (cycle retrospective)", ch, paste0(id, " (share, D$, R$; average-sector and dollar-weighted)"),
          if (ok) "descriptive only" else "unavailable",
          if (ok) "two election cycles (2022, 2024): each estimate is a fixed contrast of the two cycles; final calls follow most of the spending"
          else paste0(id, " ", sti))
    }
    # A: the national response
    wa <- if (!is.null(w)) w$estimates[w$estimates$chamber == ch, , drop = FALSE] else NULL
    for (src in c("538 lite", "538 classic", "538 deluxe", "crystal_ball")) for (m in names(SGS_SEATS_MODELS)) for (wt in c("pooled-dollar", "equal-sector")) {
      x <- if (!is.null(wa)) wa[wa$source == src & wa$model == m & wa$weighting == wt & wa$scope == "pooled" & wa$window == "all weeks" &
                                  !nzchar(wa$omitted_sector) & startsWith(wa$availability, "availability verified") &
                                  startsWith(wa$money, "gross"), , drop = FALSE] else NULL
      primary <- src == "538 lite" && m != "lag"
      cell <- paste0(if (src == "538 lite") "Lite" else src, ", ", SGS_SEATS_MODELS[[m]], ", ", wt)
      if (!is.null(x) && nrow(x)) {
        add("A national response (next week's share on the prior week's forecast change)", ch, cell,
            if (x$gate[1] == "estimated") "estimated" else "descriptive only",
            if (x$gate[1] == "estimated") paste0("EXPLORATORY; interval conditional", if (m == "lag") " (fixed-X) / dynamic (recursive)" else "",
                                                 "; ", x$n_weeks[1], " weeks, cycles ", x$cycles[1]) else x$gate[1],
            if (primary) paste0("A overall response, ", ch) else "")
      } else {
        add("A national response (next week's share on the prior week's forecast change)", ch, cell, "unavailable",
            if (!isTRUE(seats$weekly_ok)) seats$weekly_reason else "no series for this source in 09 aligned",
            if (primary) paste0("A overall response, ", ch) else "")
      }
    }
    for (cell in c("post-primary weeks only (national; 2022: from 19 September, 7 weeks)", "leave one sector out (every sector, telecom included)",
                   "availability-unverified rows included (sensitivity)", "per-cycle estimates and their agreement", "net receipts (dem_share; sensitivity)")) {
      have <- !is.null(wa) && nrow(wa) > 0 && (
        (startsWith(cell, "post") && any(wa$window == "post-primary")) || (startsWith(cell, "leave") && any(nzchar(wa$omitted_sector))) ||
          (startsWith(cell, "avail") && any(startsWith(wa$availability, "incl."))) || (startsWith(cell, "per-cycle") && any(startsWith(wa$scope, "cycle "))) ||
          (startsWith(cell, "net") && any(startsWith(wa$money, "net"))))
      why <- if (!isTRUE(seats$weekly_ok)) seats$weekly_reason else
        if (startsWith(cell, "avail")) paste0("09 aligned_sensitivity has ", w$sens_primary_rows %||% 0, " primary-window rows (the 2018 files and the undated ",
                                              "Crystal Ball call fall outside the pre-election weeks)") else
        if (startsWith(cell, "per-cycle")) "one election cycle with pre-election weeks (2022): no per-cycle comparison until 2020 joins" else
          "no rows in 09 for this sensitivity"
      add("A national response, sensitivities", ch, cell,
          if (!have) "unavailable" else if (startsWith(cell, "post")) "descriptive only" else "estimated",
          if (!have) why else if (startsWith(cell, "post")) paste0("fewer than ", SGS$SEATS_MIN_WEEKS, " weeks: estimate only") else
            "EXPLORATORY; conditional intervals")
    }
    # B: differential response
    z <- race$chambers[[ch]]
    bok <- !is.null(z) && isTRUE(z$b$ok)
    breason <- if (bok) "" else paste(c(race_reason(ch), if (!is.null(z) && !is.null(z$b) && !isTRUE(z$b$ok)) z$b$reason else money_reason), collapse = "; ")
    bcell <- function(grp, label, fam = "", kind = "") {
      if (!bok) return(add(paste0("B differential response", kind), ch, label, "unavailable", breason, fam))
      e <- z$b$estimates[z$b$estimates$group == grp & z$b$estimates$weighting == "share_equal" & z$b$estimates$model == "level" &
                           z$b$estimates$classification == "fixed", , drop = FALSE]
      add(paste0("B differential response", kind), ch, label, if (nrow(e) && e$gate[1] == "estimated") "estimated" else if (nrow(e)) "descriptive only" else "unavailable",
          if (nrow(e) && e$gate[1] == "estimated") paste0("EXPLORATORY, one election; groups fixed at the pre-spending origin ", format(z$b$origin),
                                                          "; conditional intervals") else if (nrow(e)) e$gate[1] else "no series", fam)
    }
    bcell("first_term", "first-term incumbents slope")
    bcell("established", "established incumbents slope (reference)")
    bcell("favored_nonincumbent", "favored non-incumbents slope (primary incoming-officeholder group: no dated service, own Lite p > 0.5)")
    bcell("favored_nonincumbent_p60", "favored non-incumbents slope, own Lite p > 0.6 (sensitivity)")
    bcell("favored_challenger_provisional", "favored challengers slope (FEC C; PROVISIONAL sensitivity)")
    bcell("favored_open_provisional", "favored open-seat candidates slope (FEC O; PROVISIONAL sensitivity)")
    bcell("first_term_minus_established", "first-term minus established (contrast)", paste0("B incumbency contrasts, ", ch))
    bcell("favored_nonincumbent_minus_established", "favored non-incumbent minus established (contrast)", paste0("B incumbency contrasts, ", ch))
    for (cl in SGS_SEATS_538_CLASSES) bcell(paste0("class_", cl), paste0("538 class ", cl, " slope", if (cl == "safe") " (reference)" else ""),
                                            paste0("B 538-class slopes and interactions, ", ch), " (538 probability classes)")
    for (cl in setdiff(SGS_SEATS_538_CLASSES, "safe")) bcell(paste0(cl, "_minus_safe"), paste0("538 class ", cl, " minus safe (interaction)"),
                                                             paste0("B 538-class slopes and interactions, ", ch), " (538 probability classes)")
    for (cl in SGS_SEATS_538_CLASSES) bcell(paste0("favored_nonincumbent_x_", cl), paste0("favored non-incumbents x 538 ", cl, " (exploratory cross-cut)"),
                                            "", " (538 probability classes)")
    es <- if (!is.null(z) && isTRUE(z$ok) && !is.null(z$expert)) z$expert[z$expert$whitelist == "primary" & z$expert$category != "unrated", , drop = FALSE] else NULL
    ew <- if (is.null(es)) 0 else length(unique(es$week_start))
    for (cl in c("toss-up", "tilt (kept separate)", "lean", "likely", "safe", "unrated (unknown, never safe)")) {
      add("B differential response (expert ratings: Cook / Inside Elections / Sabato, a separate categorical path)", ch, paste0(cl, " slope"), "unavailable",
          if (is.null(es)) paste0("expert ratings not read: ", breason) else
            paste(c(paste0(ew, " weeks with a primary-eligible rating (timing_eligible_primary, availability_date_conservative before the window) < ",
                           SGS$SEATS_MIN_WEEKS), if (!bok) breason), collapse = "; "),
          if (!grepl("tilt|unrated", cl)) paste0("B expert-rating slopes, ", ch) else "")
    }
    add("B differential response", ch, "rolling classification (re-classified each window; sensitivity) with transition counts",
        if (bok) "estimated" else "unavailable", if (bok) "EXPLORATORY; sheet seats_b_transitions counts the candidates whose group changes" else breason)
    add("B differential response", ch, "3 x 4 incumbency x rating cross-classification (exploratory)", if (bok) "descriptive only" else "unavailable",
        if (bok) "exploratory: favored non-incumbents x 538 class only, no Holm, no inference claim; first-term / established x class not built" else breason)
    add("B differential response", ch, "post-primary candidate-weeks only (sensitivity)", "unavailable",
        if (bok) "not built in this round (the candidate-level pre-matchup flag is in sheet seats_race_exposure; the national post-primary window is in estimand A)" else breason)
    add("B outcomes", ch, "fixed candidate set (weekly); continuing donors (weekly); PPML", "unavailable",
        paste(c(if (!bok) breason, "not built in this round; 09 donor_committee_cycle is cycle-level (no weekly donor rows): continuing donors are reported per cycle, DESCRIPTIVE"),
              collapse = "; "))
    add("B outcomes", ch, "continuing donors between the 2022 and 2024 cycles (cycle level)", if (!is.null(seats$donors)) "descriptive only" else "unavailable",
        if (!is.null(seats$donors)) paste0("DESCRIPTIVE; linkage: ", seats$donors$linkage) else "09 donor_committee_cycle not read")
    # C: own prospects
    cok <- !is.null(z) && isTRUE(z$c$ok)
    add("C own prospects (the candidate's own lagged win-probability change; national exposure excluding the focal race)", ch,
        "own Lite probability change, fixed candidate set", if (cok) "estimated" else "unavailable",
        if (cok) "EXPLORATORY; week-block residual bootstrap within cycle, conditional" else paste(c(race_reason(ch), if (!is.null(z$c)) z$c$reason else money_reason), collapse = "; "))
    # the exposure itself
    add("Race-level exposure (538 own probability at each origin; incumbency; favored non-incumbents; classes)", ch, "exposure census and match diagnostics",
        if (!is.null(z) && isTRUE(z$ok)) "descriptive only" else "unavailable",
        if (!is.null(z) && isTRUE(z$ok)) "no money joined: counts of candidates and candidate-weeks, not outcomes" else race_reason(ch))
  }
  add("champions breakdown (H5)", "both", "H5 champions by toughness", "descriptive only",
      "selected current industry champions (05), not an all-candidate universe: never a test of whether new or established incumbents attract or lose money")
  sgs_rows_df(out, SGS_SEATS_CELL_COLS)
}

# ---- report: the race level ------------------------------------------------------------------------------------------
sgs_seats_race_md <- function(seats) {
  race <- seats$race
  L <- c("", "**Race level: the candidate's own 538 probability at each spending window (House and Senate, 2022)**", "")
  if (!isTRUE(race$have10) || !isTRUE(race$have11)) {
    return(c(L, paste0("- NOT BUILT: ", race$reason, ". The code is in place (workbook 10: recipient_classification and ",
                       "candidate_service_terms; workbook 11: house_district_538_2022, senate_state_538_2022, rating_history_expert, ",
                       "an optional primary_calendar). It matches each named 538 candidate (name_D1..D4, name_R1..R4, name_I1) to the ",
                       "recipients' cand_ids by surname within cycle, chamber, state, district and party, takes the latest Lite row available ",
                       "strictly before each weekly window (Classic and Deluxe as sensitivities), and never gives a candidate the ",
                       "favourite's probability.")))
  }
  dg <- sgs_seats_race_diag(race)
  L <- c(L, "| chamber | metric | value | note |", "|---|---|---:|---|",
         paste0("| ", dg$chamber, " | ", dg$metric, " | ", vapply(dg$value, function(v) if (is.na(v)) "" else if (v < 1 && v > 0) sgs_py_fixed(v, 4) else sgs_py_str(v), ""),
                " | ", .md_escape(dg$note), " |"))
  cs <- sgs_seats_race_census(race)
  L <- c(L, "", "Candidate-weeks by incumbency at the origin (dated service) and the candidate's own 538 Lite class (named candidates):", "",
         "| chamber | group | candidates | candidate-weeks | named | toss-up | lean | likely | safe | not named |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
         paste0("| ", cs$chamber, " | ", cs$group, " | ", cs$candidates, " | ", cs$candidate_weeks, " | ", cs$named_weeks, " | ", cs$toss_up, " | ",
                cs$lean, " | ", cs$likely, " | ", cs$safe, " | ", cs$not_named, " |"))
  fl <- sgs_seats_favored_list(race)
  if (nrow(fl)) {
    L <- c(L, "", paste0("Favored non-incumbents (no dated service in the chamber at the origin, own named Lite probability > 0.5 before the window; ",
                         "the FEC role is provisional and never defines the group):"), "",
           "| chamber | candidate (FEC) | 538 name | party | race | FEC role (provisional) | weeks | first | last | own p | weeks p > 0.6 | weeks before matchup final |",
           "|---|---|---|---|---|---|---:|---|---|---|---:|---:|",
           paste0("| ", fl$chamber, " | ", .md_escape(fl$fec_name), " | ", .md_escape(fl$name_538), " | ", fl$party, " | ", fl$race, " | ",
                  fl$fec_role_provisional, " | ", fl$weeks, " | ", fl$first_week, " | ", fl$last_week, " | ",
                  vapply(fl$p_min, sgs_py_fixed, "", d = 3), "-", vapply(fl$p_max, sgs_py_fixed, "", d = 3), " | ", fl$weeks_p60, " | ",
                  fl$weeks_pre_matchup_final, " |"))
  }
  es <- sgs_seats_expert_support(race)
  if (nrow(es)) {
    L <- c(L, "", "Expert ratings (a separate categorical path; Tilt kept separate; an unrated race is unknown, never safe): weeks with a rating available before the window:", "",
           "| chamber | whitelist | source | weeks | races rated | race-weeks | tilt | first week |", "|---|---|---|---:|---:|---:|---:|---|",
           paste0("| ", es$chamber, " | ", es$whitelist, " | ", es$source, " | ", es$weeks, " | ", es$races_rated, " | ", es$race_weeks, " | ", es$tilt, " | ", es$first_week, " |"))
  }
  L <- c(L, "", paste0("- Nominee status: a named forecast candidate is not necessarily the nominee; pre-primary rows condition on an assumed ",
                       "matchup. Candidate-weeks before the race's named matchup became final are flagged (",
                       if (any(vapply(race$chambers, function(z) isTRUE(z$ok) && identical(z$exposure$nominee_basis[1], "official primary calendar"), TRUE)))
                         "official primary calendar" else "a proxy from the forecast rows: no official primary calendar is among the inputs",
                       "); the national post-primary sensitivity starts on ", SGS$SEATS_POST_PRIMARY_START[["2022"]], " (2022)."))
  for (ch in names(race$chambers)) {
    z <- race$chambers[[ch]]
    if (!isTRUE(z$ok)) next
    if (isTRUE(z$b$ok)) {
      e <- z$b$estimates
      e <- e[e$scope == "pooled" & e$classification == "fixed" &
               (e$weighting == "share_equal" | (e$weighting %in% names(SGS_SEATS_B_OUTCOMES) & e$kind == "contrast")), , drop = FALSE]
      tr <- z$b$transitions
      L <- c(L, "", paste0("**Estimand B, ", ch, "** (group weekly series on the prior week's national forecast change; groups FIXED at the ",
                           "pre-spending origin ", format(z$b$origin), " - the rolling re-classification is the sensitivity in sheet seats_b_",
                           tolower(ch), "; D share of gross receipts for every group, the dollar outcomes for the contrasts; conditional ",
                           "intervals; bootstrap p is never proof; EXPLORATORY, one election):"), "",
             paste0("Transitions (candidates in the group at the fixed origin / in the rolling group in any week / rolling-only / fixed ",
                    "members who leave the rolling group in some week): ",
                    paste0(tr$group, " ", tr$candidates_fixed, " / ", tr$candidates_ever_rolling, " / ", tr$rolling_not_fixed, " / ",
                           tr$fixed_leaving_in_some_week, collapse = "; "), "."), "",
             "| group | kind | outcome | model | gate | weeks | estimate | 3-week interval (p) | 5-week interval (p) | Holm 3 / 5 | family |",
             "|---|---|---|---|---|---:|---:|---|---|---|---|",
             paste0("| ", e$group, " | ", e$kind, " | ", e$weighting, " | ", e$model, " | ", .md_escape(e$gate), " | ", e$n_weeks, " | ", vapply(e$estimate, sgs_fmt, ""),
                    " | ", mapply(function(a, b, p) paste0(sgs_ci_text(a, b), " (", sgs_fmt(p), ")"), e$fx3_ci_low, e$fx3_ci_high, e$fx3_p), " | ",
                    mapply(function(a, b, p) paste0(sgs_ci_text(a, b), " (", sgs_fmt(p), ")"), e$fx5_ci_low, e$fx5_ci_high, e$fx5_p), " | ",
                    vapply(e$holm_fx3_p, sgs_fmt, ""), " / ", vapply(e$holm_fx5_p, sgs_fmt, ""), " | ", .md_escape(e$holm_family), " |"))
      if (length(z$b$blocks)) L <- c(L, "", paste0("summary(lm()) of the fixed-origin D-share series behind the slopes and contrasts above ",
                                                   "(the classical errors printed by summary() are not the study's inference):"), "", "```", z$b$blocks, "```")
    }
    if (isTRUE(z$c$ok)) {
      g <- function(L0) { r <- z$c$boot[[paste0("L", L0)]]; paste0(sgs_ci_text(r$ci[1], r$ci[2]), " (p ", sgs_fmt(r$p), ")") }
      L <- c(L, "", paste0("**Estimand C, ", ch, "**: own Lite probability change ", sgs_fmt(z$c$estimate), " ", z$c$unit, "; ", z$c$candidates,
                           " candidates x ", z$c$weeks, " weeks; week-block bootstrap 3 weeks ", g(3), ", 5 weeks ", g(5), " (conditional; EXPLORATORY)."))
    }
  }
  L
}

# ---- report: the Codex cross-check ------------------------------------------------------------------------------------
sgs_seats_codex_md <- function(seats) {
  x <- SGS_SEATS_CODEX_XCHECK
  r <- x$rows
  L <- c("", "**Cross-check with Codex's independent weekly estimates (read-only; quoted, never an input)**", "", paste0("- ", x$spec, "."),
         paste0("- Sources: ", x$estimates, "; ", x$bootstrap, "; ", x$validation, "."), "",
         "| chamber | group | outcome | block | estimate | conditional 95% interval | block p | Holm | HAC(2) SE |", "|---|---|---|---:|---:|---|---:|---:|---:|",
         paste0("| ", r$chamber, " | ", r$group, " | ", r$outcome, " | ", r$block, " | ", vapply(r$estimate, sgs_fmt, ""), " | ",
                mapply(sgs_ci_text, r$ci_low, r$ci_high), " | ", vapply(r$p_block, sgs_fmt, ""), " | ", vapply(r$p_holm, sgs_fmt, ""), " | ",
                vapply(r$hac2_se, sgs_fmt, ""), " |"),
         "", paste0("- ", x$senate_first_term, "."))
  w <- seats$w
  if (is.null(w) || !nrow(w$estimates)) {
    L <- c(L, paste0("- Comparison with this pipeline's SEATS-W: not possible in this run (", if (!isTRUE(seats$weekly_ok)) seats$weekly_reason else "no estimates",
                     "). The overlapping specification will be SEATS-W, 538 Lite, availability verified, equal-sector share, the ",
                     "lagged-outcome model (a sensitivity here) for cycle 2022; the differences that remain by design: 09's money is 08's ",
                     "included receipts by transaction date (Codex: net receipts of observed receiving committees), 09's pairing gates on ",
                     "available_at, and this pipeline's primary models have no lagged outcome."))
  } else {
    e <- w$estimates
    base <- e$source == tolower(SGS$SEATS_W_PRIMARY) & e$weighting == "equal-sector" & startsWith(e$availability, "availability verified") &
      e$window == "all weeks" & !nzchar(e$omitted_sector) & e$scope == "pooled" & e$cycles == "2022"
    for (ch in c("House", "Senate")) {
      cx <- r[r$chamber == ch & r$group == "overall", , drop = FALSE]
      ov <- e[base & e$chamber == ch & e$model == "lag" & startsWith(e$money, "net"), , drop = FALSE]
      pr <- e[base & e$chamber == ch & e$model == "level" & startsWith(e$money, "gross"), , drop = FALSE]
      if (!nrow(ov) || !nrow(cx)) { L <- c(L, paste0("- ", ch, ": no overlapping SEATS-W row (Lite, net, equal-sector, lagged outcome, 2022).")); next }
      ov <- ov[1, , drop = FALSE]
      agree <- sign(ov$estimate) == sign(cx$estimate[1])
      L <- c(L, paste0("- ", ch, ", the overlapping specification (net receipts, equal-sector share, lagged outcome, 2022; differences left: ",
                       "09's population and available_at pairing vs Codex's observed receiving committees and forecast / run-date gate): ",
                       "this pipeline ", sgs_fmt(ov$estimate), " pp per seat (", ov$n_weeks, " weeks; fixed-X 3-week ",
                       sgs_ci_text(ov$fx3_ci_low, ov$fx3_ci_high), ", p ", sgs_fmt(ov$fx3_p), "; recursive 3-week ",
                       sgs_ci_text(ov$rec3_ci_low, ov$rec3_ci_high), ", p ", sgs_fmt(ov$rec3_p), ") vs Codex ", sgs_fmt(cx$estimate[1]),
                       " (17 weeks): ", if (agree) "same sign" else "OPPOSITE sign", "; difference ", sgs_fmt(ov$estimate - cx$estimate[1]), "."),
             if (nrow(pr)) paste0("  This pipeline's primary for comparison (gross, equal-sector, levels without the lagged outcome): ", sgs_fmt(pr$estimate[1]),
                                  " pp per seat, 3-week conditional interval ", sgs_ci_text(pr$fx3_ci_low[1], pr$fx3_ci_high[1]), " (p ", sgs_fmt(pr$fx3_p[1]), ")."))
    }
  }
  L
}
