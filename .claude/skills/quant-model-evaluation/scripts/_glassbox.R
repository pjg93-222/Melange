# Shared plumbing for the quant-model-evaluation R scripts.
#
# Mirrors scripts/_common.py: same verdict words, same exit codes, same Glass Box
# event shape, same write-once run directories. Source it from a script with
#   source(file.path(qme_script_dir, "_glassbox.R"))
# Emission can never break a run: every failure inside qme_emit() is swallowed.

QME_SKILL <- "quant-model-evaluation"
QME_VERSION <- "1.0.0"
QME_VERDICTS <- c("SURVIVES", "WOUNDED", "KILLED", "UNVERIFIED-HERE")
QME_EXIT <- list(ok = 0L, findings = 1L, usage = 2L, unverified = 3L)

.qme_state <- new.env(parent = emptyenv())
.qme_state$glassbox_on <- !identical(Sys.getenv("QME_GLASSBOX", "1"), "0")

qme_disable_glassbox <- function() {
  .qme_state$glassbox_on <- FALSE
  invisible(NULL)
}

.qme_events_dir <- function() {
  if (!isTRUE(.qme_state$glassbox_on)) return(NULL)
  override <- Sys.getenv("GLASSBOX_EVENTS_DIR", "")
  if (nzchar(override)) return(override)
  home <- Sys.getenv("USERPROFILE", Sys.getenv("HOME", ""))
  if (!nzchar(home)) return(NULL)
  parent <- file.path(home, ".claude", "glassbox")
  # Only emit on machines that already run a Glass Box; never create one.
  if (!dir.exists(parent)) return(NULL)
  file.path(parent, "events")
}

.qme_iso <- function() {
  t <- Sys.time()
  paste0(format(t, "%Y-%m-%dT%H:%M:%S", tz = "UTC"),
         substr(sprintf("%.7f", as.numeric(t) %% 1), 2, 9), "Z")
}

.qme_stamp <- function() {
  t <- Sys.time()
  paste0(format(t, "%Y%m%dT%H%M%S", tz = "UTC"),
         substr(sprintf("%.7f", as.numeric(t) %% 1), 3, 9), "Z")
}

qme_emit <- function(kind, status, summary, run_id = "", source = QME_SKILL, stage = "",
                     detail = "", current = -1L, total = -1L, duration_ms = -1L) {
  tryCatch({
    dir <- .qme_events_dir()
    if (is.null(dir)) return(invisible(NULL))
    if (!requireNamespace("jsonlite", quietly = TRUE)) return(invisible(NULL))
    dir.create(dir, recursive = TRUE, showWarnings = FALSE)
    suffix <- paste(sample(c(0:9, letters[1:6]), 10, replace = TRUE), collapse = "")
    eid <- paste0("evt-", .qme_stamp(), "-", suffix)
    payload <- list(
      schema_version = 1L, id = eid, timestamp_utc = .qme_iso(), run_id = run_id,
      correlation_id = "", parent_id = "", lane = Sys.getenv("QME_GLASSBOX_LANE", "claude"),
      source = source, kind = kind, status = status, stage = stage,
      summary = substr(summary, 1, 400), detail = substr(detail, 1, 2000),
      cwd = getwd(), duration_ms = as.integer(duration_ms), bytes = -1L, metadata = NULL
    )
    if (current >= 0) payload$current <- as.integer(current)
    if (total >= 0) payload$total <- as.integer(total)
    final <- file.path(dir, paste0(eid, ".json"))
    tmp <- file.path(dir, paste0(".", eid, ".", Sys.getpid(), ".tmp"))
    writeLines(jsonlite::toJSON(payload, auto_unbox = TRUE, null = "null"), tmp, useBytes = TRUE)
    file.rename(tmp, final)
    invisible(eid)
  }, error = function(e) invisible(NULL))
}

qme_run_dir <- function(out, script) {
  base <- normalizePath(path.expand(out), winslash = "/", mustWork = FALSE)
  if (file.exists(base) && !dir.exists(base)) stop("--out must be a directory: ", base, call. = FALSE)
  run <- file.path(base, sprintf("%s-%s-%d", script,
                                 format(Sys.time(), "%Y%m%dT%H%M%SZ", tz = "UTC"), Sys.getpid()))
  if (dir.exists(run)) stop("run directory already exists: ", run, call. = FALSE)
  dir.create(run, recursive = TRUE)
  run
}

qme_write_once <- function(path, lines) {
  if (file.exists(path)) stop("refusing to overwrite ", path, call. = FALSE)
  tmp <- file.path(dirname(path), paste0(".", basename(path), ".", Sys.getpid(), ".tmp"))
  con <- file(tmp, open = "wb")
  writeBin(charToRaw(enc2utf8(paste0(paste(lines, collapse = "\n"), "\n"))), con)
  close(con)
  file.rename(tmp, path)
  invisible(path)
}

qme_sha256 <- function(path) {
  if (requireNamespace("digest", quietly = TRUE)) return(digest::digest(file = path, algo = "sha256"))
  NA_character_
}

qme_exit_code <- function(verdicts) {
  if (any(verdicts %in% c("KILLED", "WOUNDED"))) return(QME_EXIT$findings)
  if (any(verdicts == "UNVERIFIED-HERE")) return(QME_EXIT$unverified)
  QME_EXIT$ok
}
