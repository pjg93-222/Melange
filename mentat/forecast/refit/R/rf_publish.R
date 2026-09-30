# Publishing: write giving-models-vN.json (+ its receipt) and switch an atomic pointer, under a lock, with rollback. Never commits, never
# touches git, never overwrites v1 (the v1 file stays where it is and stays the rollback target).
#
#   <publish dir>/giving-models-v1.json               the frozen v1 bundle (kept)
#   <publish dir>/giving-models-v2.json               the published v2 bundle
#   <publish dir>/giving-models-v2.receipt.json       its receipt
#   <publish dir>/giving-models-current.json          the pointer the console follows: {active, sha256, model_version, previous: {...}}
#   <runtime>/published/<model_version>/              archive of every publish: bundle, receipt and the pointer as it was before the switch
#   <runtime>/refit.lock/                             mutex directory (dir.create is atomic); stale after 6 h with a dead owner pid
#
# The publish dir is RF_PUBLISH_DIR, default mentat/app/data of the checkout holding this code. A publish happens only when the decision
# is PUBLISH. All comparisons of a bundle with another (another platform's BLAS differs at ~1e-14) are tolerance-based.

rf_publish_dir <- function() rf_env_path("RF_PUBLISH_DIR", file.path(dirname(dirname(rf_home())), "app", "data"))
rf_pointer_path <- function(dir = rf_publish_dir()) file.path(dir, "giving-models-current.json")
rf_archive_dir <- function(model_version) file.path(rf_runtime(), "published", model_version)
rf_lock_path <- function() file.path(rf_runtime(), "refit.lock")

rf_pid_alive <- function(pid) {
  pid <- suppressWarnings(as.integer(pid))
  if (is.na(pid) || pid <= 0L) return(FALSE)
  if (.Platform$OS.type == "windows") {
    out <- suppressWarnings(system2("tasklist", c("/FI", shQuote(paste0("PID eq ", pid)), "/NH"), stdout = TRUE, stderr = TRUE))
    return(any(grepl(paste0("\\b", pid, "\\b"), out)))
  }
  file.exists(file.path("/proc", pid))
}

# Acquire the refit lock (a directory). A lock older than `stale_hours` whose owner process is gone is broken (with a Glass Box event by the caller
# via the returned flag); any other existing lock stops the caller. -> list(path, broke_stale)
rf_lock_acquire <- function(stale_hours = 6, path = rf_lock_path()) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  broke <- FALSE
  if (dir.exists(path)) {
    owner <- tryCatch(jsonlite::fromJSON(file.path(path, "owner.json"), simplifyVector = FALSE), error = function(e) list())
    age_h <- as.numeric(difftime(Sys.time(), file.mtime(path), units = "hours"))
    if (age_h > stale_hours && !rf_pid_alive(owner$pid)) { unlink(path, recursive = TRUE); broke <- TRUE }
    else stop(sprintf("rf_lock_acquire: another refit holds the lock (pid %s, since %s)", owner$pid %||% "?", owner$acquired_utc %||% "?"), call. = FALSE)
  }
  if (!dir.create(path, showWarnings = FALSE)) stop("rf_lock_acquire: could not create the lock (another refit won the race)", call. = FALSE)
  writeLines(as.character(jsonlite::toJSON(list(pid = Sys.getpid(), acquired_utc = rf_now_utc(), host = Sys.info()[["nodename"]]), auto_unbox = TRUE)), file.path(path, "owner.json"))
  list(path = path, broke_stale = broke)
}

rf_lock_release <- function(path = rf_lock_path()) { unlink(path, recursive = TRUE); invisible(!dir.exists(path)) }

# The pointer file's content, or a pointer derived from the kept v1 file when none has been written yet.
rf_read_pointer <- function(dir = rf_publish_dir()) {
  p <- rf_pointer_path(dir)
  if (file.exists(p)) return(jsonlite::fromJSON(p, simplifyVector = FALSE))
  v1 <- file.path(dir, "giving-models-v1.json")
  if (!file.exists(v1)) return(NULL)
  list(schema_version = 1L, active = "giving-models-v1.json", sha256 = rf_sha256(v1), model_version = jsonlite::fromJSON(v1, simplifyVector = FALSE)$model_version,
       switched_at_utc = NA_character_, previous = NULL)
}

.rf_write_pointer <- function(ptr, dir) {
  ptr <- ptr[!vapply(ptr, is.null, logical(1))]
  rf_write_json_atomic(ptr, rf_pointer_path(dir))
}

# Publish a gated bundle. `receipt` = the run receipt (list). Returns list(status, ...): "published" or "not_published" (with the reason).
rf_publish <- function(bundle, gates, receipt = list(), dir = rf_publish_dir(), gb = NULL) {
  decision <- rf_decision(gates)
  mv <- bundle$model_version
  note <- function(kind, status, summary, detail = "") if (!is.null(gb)) gb$emit_event(kind, status, "publish", summary, detail)
  if (decision != "PUBLISH") {
    note("publish.hold", "failed", sprintf("not published: decision %s", decision), paste(gates$gate[gates$status %in% c("HOLD", "FAIL")], collapse = ", "))
    return(list(status = "not_published", decision = decision, reason = paste(gates$gate[gates$status %in% c("HOLD", "FAIL")], gates$detail[gates$status %in% c("HOLD", "FAIL")], sep = ": ", collapse = " | ")))
  }
  problems <- rf_validate_bundle(bundle)
  if (length(problems)) stop("rf_publish: bundle fails the contract schema: ", paste(utils::head(problems, 3), collapse = "; "), call. = FALSE)
  lock <- rf_lock_acquire()
  on.exit(rf_lock_release(lock$path), add = TRUE)
  note("publish.start", "running", sprintf("publishing %s", mv), if (lock$broke_stale) "a stale lock was broken" else "")
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  file_name <- sprintf("giving-models-v%d.json", bundle$schema_version)
  receipt_name <- sub("\\.json$", ".receipt.json", file_name)
  before <- rf_read_pointer(dir)
  # stage + verify: the bundle is written under a temporary name, re-read, re-validated, hash-compared, then renamed into place
  tmp <- file.path(dir, paste0(file_name, ".", paste(sample(c(0:9, letters[1:6]), 12, TRUE), collapse = ""), ".tmp"))
  sha <- rf_write_json_atomic(bundle, tmp)
  back <- jsonlite::fromJSON(tmp, simplifyVector = FALSE)
  if (length(rf_validate_parsed(back)) || !identical(rf_sha256(tmp), sha)) { unlink(tmp); stop("rf_publish: staged bundle did not verify", call. = FALSE) }
  target <- file.path(dir, file_name)
  ok <- FALSE
  for (k in seq_len(40L)) { if (suppressWarnings(file.rename(tmp, target))) { ok <- TRUE; break }; Sys.sleep(stats::runif(1, 0.05, 0.25)) }   # the console may hold the file briefly
  if (!ok) { unlink(tmp); stop("rf_publish: could not replace ", target, call. = FALSE) }
  rsha <- rf_write_json_atomic(c(receipt, list(published_to = list(dir = dir, file = file_name, sha256 = sha, model_version = mv), decision = decision)), file.path(dir, receipt_name))
  arch <- rf_archive_dir(mv)
  dir.create(arch, recursive = TRUE, showWarnings = FALSE)
  file.copy(target, file.path(arch, file_name), overwrite = TRUE); file.copy(file.path(dir, receipt_name), file.path(arch, receipt_name), overwrite = TRUE)
  if (!is.null(before)) rf_write_json_atomic(before, file.path(arch, "pointer-before.json"))
  ptr <- list(schema_version = 1L, active = file_name, sha256 = sha, model_version = mv, switched_at_utc = rf_now_utc(),
              previous = if (!is.null(before)) list(active = before$active, sha256 = before$sha256, model_version = before$model_version) else NULL)
  .rf_write_pointer(ptr, dir)                                   # the atomic switch: the console follows the pointer
  note("publish.done", "succeeded", sprintf("published %s -> %s", mv, file_name), sha)
  list(status = "published", decision = decision, model_version = mv, file = target, sha256 = sha, receipt_sha256 = rsha, pointer = ptr, archive = arch, broke_stale = lock$broke_stale)
}

# Restore an earlier state: make `model_version` the active bundle again. An archived publish is restored from <runtime>/published/<mv>/;
# the kept v1 file is restored by its model_version. The pointer switch is atomic; the bundle files being replaced stay in their archives.
rf_rollback <- function(model_version, dir = rf_publish_dir(), gb = NULL) {
  note <- function(kind, status, summary, detail = "") if (!is.null(gb)) gb$emit_event(kind, status, "rollback", summary, detail)
  lock <- rf_lock_acquire()
  on.exit(rf_lock_release(lock$path), add = TRUE)
  before <- rf_read_pointer(dir)
  arch <- rf_archive_dir(model_version)
  v1 <- file.path(dir, "giving-models-v1.json")
  if (dir.exists(arch) && length(list.files(arch, pattern = "^giving-models-v[0-9]+\\.json$"))) {
    file_name <- list.files(arch, pattern = "^giving-models-v[0-9]+\\.json$")[1]
    target <- file.path(dir, file_name)
    if (!file.exists(target) || !identical(rf_sha256(target), rf_sha256(file.path(arch, file_name)))) {
      tmp <- paste0(target, ".", paste(sample(c(0:9, letters[1:6]), 12, TRUE), collapse = ""), ".tmp")
      file.copy(file.path(arch, file_name), tmp, overwrite = TRUE)
      if (!suppressWarnings(file.rename(tmp, target))) { unlink(tmp); stop("rf_rollback: could not restore ", target, call. = FALSE) }
      rf <- sub("\\.json$", ".receipt.json", file_name)
      if (file.exists(file.path(arch, rf))) file.copy(file.path(arch, rf), file.path(dir, rf), overwrite = TRUE)
    }
    sha <- rf_sha256(target)
  } else if (file.exists(v1) && identical(jsonlite::fromJSON(v1, simplifyVector = FALSE)$model_version, model_version)) {
    file_name <- "giving-models-v1.json"; sha <- rf_sha256(v1)
  } else {
    stop("rf_rollback: no archived publish and no kept bundle for model_version ", model_version, call. = FALSE)
  }
  ptr <- list(schema_version = 1L, active = file_name, sha256 = sha, model_version = model_version, switched_at_utc = rf_now_utc(),
              previous = if (!is.null(before)) list(active = before$active, sha256 = before$sha256, model_version = before$model_version) else NULL, rolled_back = TRUE)
  .rf_write_pointer(ptr, dir)
  note("rollback.done", "succeeded", sprintf("rolled back to %s (%s)", model_version, file_name), sha)
  list(status = "rolled_back", model_version = model_version, file = file_name, sha256 = sha, pointer = ptr)
}

# Tolerance-based comparison of two parsed bundles (e.g. a pod-built and a Windows-built one): every numeric leaf within rel_tol (abs_tol near zero),
# strings and integers exact, keys equal. -> data.frame(path, a, b, dev) of the leaves beyond tolerance (empty = equivalent); attr "max_dev".
rf_bundle_diff <- function(a, b, rel_tol = 1e-9, abs_tol = 1e-12, ignore = c("built_at_utc", "model_version", "run_id", "code_sha256", "R_version", "packages", "note", "as_of")) {
  rows <- list(); maxdev <- 0
  walk <- function(x, y, p, key) {
    if (key %in% ignore) return(invisible())
    if (is.list(x) && is.list(y)) {
      nx <- names(x); ny <- names(y)
      if (!is.null(nx) || !is.null(ny)) {
        for (k in setdiff(union(nx, ny), intersect(nx, ny))) rows[[length(rows) + 1L]] <<- data.frame(path = paste0(p, ".", k), a = NA_character_, b = "missing on one side", dev = Inf, stringsAsFactors = FALSE)
        for (k in intersect(nx, ny)) walk(x[[k]], y[[k]], paste0(p, ".", k), k)
      } else if (length(x) != length(y)) rows[[length(rows) + 1L]] <<- data.frame(path = p, a = as.character(length(x)), b = as.character(length(y)), dev = Inf, stringsAsFactors = FALSE)
      else for (i in seq_along(x)) walk(x[[i]], y[[i]], paste0(p, "[", i - 1L, "]"), "")
    } else if (is.null(x) && is.null(y)) {
      invisible()
    } else if (is.numeric(x) && is.numeric(y) && length(x) == 1L && length(y) == 1L) {
      d <- abs(x - y); s <- max(abs(x), abs(y)); dev <- if (s < 1e-6) d else d / s
      maxdev <<- max(maxdev, dev)
      if ((s < 1e-6 && d > abs_tol) || (s >= 1e-6 && dev > rel_tol)) rows[[length(rows) + 1L]] <<- data.frame(path = p, a = format(x, digits = 15), b = format(y, digits = 15), dev = dev, stringsAsFactors = FALSE)
    } else if (!identical(x, y)) {
      rows[[length(rows) + 1L]] <<- data.frame(path = p, a = format(x)[1], b = format(y)[1], dev = Inf, stringsAsFactors = FALSE)
    }
    invisible()
  }
  walk(a, b, "$", "")
  out <- if (length(rows)) do.call(rbind, rows) else data.frame(path = character(), a = character(), b = character(), dev = numeric())
  attr(out, "max_dev") <- maxdev
  out
}

# R, BLAS and LAPACK of this session: stated in every receipt (a pod's ATLAS BLAS and a laptop's reference BLAS differ at ~1e-14).
rf_platform_info <- function() {
  si <- utils::sessionInfo()
  list(R_version = R.version.string, platform = R.version$platform, os = si$running %||% R.version$os, blas = si$BLAS %||% NA_character_, lapack = si$LAPACK %||% NA_character_,
       cores = rf_cores(), node = Sys.info()[["nodename"]], note = "numerical results agree across platforms to ~1e-13; compare bundles with rf_bundle_diff(), never byte equality")
}
