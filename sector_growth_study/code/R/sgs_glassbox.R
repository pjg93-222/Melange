# Glass Box event emission (R port of code/sgs/glassbox.py; shape of the sector-growth-build events of 2026-09-25,
# schema_version 1). File name: evt-<UTC yyyyMMddTHHmmss + 7-digit fraction>Z-<10-digit pid>.json, written atomically
# (temporary file + rename), UTF-8 without BOM, compact JSON, keys in the order of the existing events.

.gb_stamp <- function(t) {
  secs <- as.numeric(t)
  whole <- floor(secs)
  micro <- min(999999, max(0, round((secs - whole) * 1e6)))
  base <- as.POSIXct(whole, origin = "1970-01-01", tz = "UTC")
  frac7 <- sprintf("%07d", as.integer(micro * 10))
  list(compact = paste0(format(base, "%Y%m%dT%H%M%S", tz = "UTC"), frac7, "Z"),
       iso = paste0(format(base, "%Y-%m-%dT%H:%M:%S", tz = "UTC"), ".", frac7, "Z"), secs = whole + micro / 1e6)
}

# Write one event; returns its id, or NULL (with a warning on stderr) if the event could not be written.
sgs_glassbox_emit <- function(kind, status, stage, summary, run_id, correlation_id = "", parent_id = "", detail = "",
                              duration_ms = -1, cwd = "", events_dir = SGS$GLASSBOX_EVENTS_DIR, metadata = NULL) {
  out <- tryCatch({
    dir.create(events_dir, recursive = TRUE, showWarnings = FALSE)
    t <- Sys.time()
    repeat {
      st <- .gb_stamp(t)
      eid <- paste0("evt-", st$compact, "-", sprintf("%010d", Sys.getpid()))
      final <- file.path(events_dir, paste0(eid, ".json"))
      if (!file.exists(final)) break
      t <- st$secs + 1e-6
    }
    event <- list(schema_version = 1L, id = eid, timestamp_utc = st$iso, run_id = run_id,
                  correlation_id = if (nzchar(correlation_id)) correlation_id else eid, parent_id = parent_id,
                  lane = SGS$GLASSBOX_LANE, source = SGS$GLASSBOX_SOURCE, kind = kind, status = status, stage = stage,
                  summary = substr(summary, 1, 320), detail = substr(detail, 1, 2400),
                  cwd = if (nzchar(cwd)) cwd else normalizePath(getwd(), winslash = "\\"),
                  duration_ms = as.integer(duration_ms), bytes = -1L, metadata = metadata)
    txt <- as.character(jsonlite::toJSON(event, auto_unbox = TRUE, null = "null", digits = NA))
    tmp <- file.path(events_dir, paste0(eid, ".json.", paste(sample(c(0:9, letters[1:6]), 32, TRUE), collapse = ""), ".tmp"))
    con <- file(tmp, open = "wb")
    writeBin(charToRaw(enc2utf8(txt)), con)
    close(con)
    if (!file.rename(tmp, final)) stop("rename failed")
    eid
  }, error = function(e) {
    message("WARNING: Glass Box event not written (", conditionMessage(e), ")")
    NULL
  })
  out
}
