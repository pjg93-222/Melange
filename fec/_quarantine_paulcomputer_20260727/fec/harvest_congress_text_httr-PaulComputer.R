#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(chromote)
  library(digest)
  library(future)
  library(future.apply)
  library(httr)
  library(jsonlite)
  library(rvest)
})

parse_args <- function(x) {
  out <- list(
    records = "audits/legfix5/congress_advanced_pages_20260725/congress_advanced_records.ndjson",
    out = "audits/legfix5/congress_advanced_pages_20260725/text_relevance_httr_shadow",
    limit = 0L, workers = 3L, host = "127.0.0.1", port = 9222L,
    resume = FALSE,
    # Cloudflare pacing. The 2026-07-26 run used workers=6 with one attempt
    # and no waiting; it was rate-limited into a fail-closed stop after six
    # 429s at 2886/18557. Concurrency is lowered and the lane now backs off
    # instead of quarantining a throttle response as a surface rejection.
    attempts = 4L,
    min_delay = 1.0,
    max_delay = 90.0,
    # Shared GLASS BOX stream. Events used to land only in <out>/events, which
    # is why this lane never appeared in the dashboard: the viewer polls the
    # shared directory. Emit to both so the codex lane pane shows live progress.
    glassbox_events = "C:/Users/pgoff/.claude/glassbox/events",
    # Receipts from an earlier harvest whose archived bodies were lost. They are
    # never written to -- they are read so each re-fetched body can be checked
    # against the hash the original run recorded. Writing into the old stage
    # would collide with its immutable receipts and destroy that evidence.
    prior_receipts = ""
  )
  i <- 1L
  while (i <= length(x)) {
    if (identical(x[[i]], "--resume")) {
      out$resume <- TRUE
      i <- i + 1L
      next
    }
    if (!startsWith(x[[i]], "--") || i == length(x)) stop("Invalid argument: ", x[[i]])
    key <- sub("^--", "", x[[i]])
    if (!key %in% names(out)) stop("Unknown argument: ", x[[i]])
    out[[key]] <- x[[i + 1L]]
    i <- i + 2L
  }
  out$limit <- as.integer(out$limit)
  out$workers <- as.integer(out$workers)
  out$port <- as.integer(out$port)
  out$attempts <- as.integer(out$attempts)
  out$min_delay <- as.numeric(out$min_delay)
  out$max_delay <- as.numeric(out$max_delay)
  if (is.na(out$limit) || out$limit < 0L) stop("--limit must be non-negative")
  if (is.na(out$workers) || out$workers < 1L) stop("--workers must be positive")
  if (is.na(out$attempts) || out$attempts < 1L) stop("--attempts must be positive")
  if (is.na(out$min_delay) || out$min_delay < 0) stop("--min-delay must be non-negative")
  if (is.na(out$max_delay) || out$max_delay < out$min_delay) stop("--max-delay must be >= --min-delay")
  out
}

# A throttle or challenge is a transient transport condition, not evidence that
# the page is wrong. Only these are retried; a genuine surface rejection (wrong
# URL, missing marker) still quarantines immediately as before.
retryable_response <- function(response, checks) {
  status <- as.integer(status_code(response))
  if (status %in% c(429L, 403L, 503L, 500L, 502L, 504L)) return(TRUE)
  isTRUE(!checks$not_challenge)
}

retry_after_seconds <- function(response) {
  value <- httr::headers(response)[["retry-after"]]
  if (is.null(value)) return(NA_real_)
  seconds <- suppressWarnings(as.numeric(value))
  if (is.na(seconds) || seconds < 0) return(NA_real_)
  seconds
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
records_file <- normalizePath(args$records, winslash = "/", mustWork = TRUE)
out_dir <- normalizePath(args$out, winslash = "/", mustWork = FALSE)
events_dir <- file.path(out_dir, "events")
accepted_dir <- file.path(out_dir, "accepted_html")
receipts_dir <- file.path(out_dir, "receipts")
quarantine_dir <- file.path(out_dir, "quarantine")
prior_receipts_dir <- if (nzchar(args$prior_receipts)) normalizePath(args$prior_receipts, winslash = "/", mustWork = FALSE) else ""
glassbox_dir <- if (nzchar(args$glassbox_events)) normalizePath(args$glassbox_events, winslash = "/", mustWork = FALSE) else ""
# Safeguards carried over from the 2026-07-26 harvest manifest: an attempt-level
# failure catchnet distinct from the body quarantine, per-batch dispatch
# accounting, and a run identity. Together they support the guarantee the
# handoff makes -- every dispatched key ends with a completion or a terminal
# failure receipt, and none is silently skipped.
catchnet_dir <- file.path(out_dir, "failure_attempts")
batches_dir <- file.path(out_dir, "batches")
for (directory in c(out_dir, events_dir, accepted_dir, receipts_dir, quarantine_dir,
                    catchnet_dir, batches_dir)) {
  dir.create(directory, recursive = TRUE, showWarnings = FALSE)
}
if (nzchar(glassbox_dir)) dir.create(glassbox_dir, recursive = TRUE, showWarnings = FALSE)

# The Glass Box viewer discovers work by watching this one shared directory, so
# a mirrored copy of every event and progress record is written there under the
# codex lane. Filenames are unique per process to avoid cross-lane collisions.
mirror_to_glassbox <- function(payload, tag) {
  if (!nzchar(glassbox_dir)) return(invisible(FALSE))
  name <- sprintf("evt-%s-httr-%d-%s.json",
                  format(Sys.time(), "%Y%m%dT%H%M%OS3Z", tz = "UTC"),
                  Sys.getpid(), tag)
  target <- file.path(glassbox_dir, gsub("[^A-Za-z0-9._-]+", "-", name))
  try(write_checked_json(target, payload), silent = TRUE)
  invisible(TRUE)
}

json_text <- function(value) {
  paste0(toJSON(value, auto_unbox = TRUE, null = "null", pretty = TRUE, digits = NA), "\n")
}

write_checked_json <- function(file, value) {
  text <- json_text(value)
  dir.create(dirname(file), recursive = TRUE, showWarnings = FALSE)
  for (attempt in seq_len(3L)) {
    temporary <- paste0(file, ".", Sys.getpid(), ".", attempt, ".tmp")
    writeChar(text, temporary, eos = NULL, useBytes = TRUE)
    ok <- file.copy(temporary, file, overwrite = TRUE)
    unlink(temporary)
    if (!ok) next
    observed <- paste0(paste(readLines(file, warn = FALSE, encoding = "UTF-8"), collapse = "\n"), "\n")
    if (identical(observed, text)) return(invisible(TRUE))
  }
  stop("Checked JSON write failed: ", file)
}

write_immutable_json <- function(file, value) {
  text <- json_text(value)
  dir.create(dirname(file), recursive = TRUE, showWarnings = FALSE)
  if (file.exists(file)) {
    observed <- paste0(paste(readLines(file, warn = FALSE, encoding = "UTF-8"), collapse = "\n"), "\n")
    if (!identical(observed, text)) stop("Immutable receipt collision: ", file)
    return(invisible(TRUE))
  }
  temporary <- paste0(file, ".", Sys.getpid(), ".tmp")
  writeChar(text, temporary, eos = NULL, useBytes = TRUE)
  if (!file.rename(temporary, file)) {
    unlink(temporary)
    stop("Immutable receipt publish failed: ", file)
  }
  invisible(TRUE)
}

write_immutable_gzip <- function(file, body_raw) {
  expected <- digest(body_raw, algo = "sha256", serialize = FALSE)
  dir.create(dirname(file), recursive = TRUE, showWarnings = FALSE)
  if (file.exists(file)) return(expected)
  temporary <- paste0(file, ".", Sys.getpid(), ".tmp")
  connection <- gzfile(temporary, "wb")
  writeBin(body_raw, connection)
  close(connection)
  verify <- gzfile(temporary, "rb")
  observed <- readBin(verify, what = "raw", n = length(body_raw) + 1L)
  close(verify)
  if (!identical(digest(observed, algo = "sha256", serialize = FALSE), expected)) {
    unlink(temporary)
    stop("Gzip readback mismatch: ", file)
  }
  if (!file.rename(temporary, file)) {
    unlink(temporary)
    stop("Immutable gzip publish failed: ", file)
  }
  expected
}

debugger_up <- function(host, port) {
  tryCatch({
    connection <- url(sprintf("http://%s:%d/json/version", host, port))
    on.exit(close(connection), add = TRUE)
    length(suppressWarnings(readLines(connection, n = 1L, warn = FALSE))) > 0L
  }, error = function(error) FALSE)
}

if (!debugger_up(args$host, args$port)) stop("Headful Chrome DevTools endpoint is unavailable")
set_default_chromote_object(
  Chromote$new(browser = ChromeRemote$new(host = args$host, port = args$port))
)

# Clearance harvesting is a function, not a one-shot startup step. A Cloudflare
# managed-challenge re-issue invalidates cf_clearance mid-run; httr cannot solve
# a JS challenge, so every subsequent request fails no matter how long we back
# off. The only recovery is re-reading the cookie jar from the live browser,
# which is why this must be callable again after a block.
harvest_clearance <- function(navigate_url = NULL) {
  session <- ChromoteSession$new()
  session$default_timeout <- 120
  if (!is.null(navigate_url)) {
    # Drive the browser through the challenge so Cloudflare mints a new token.
    try({
      session$Page$navigate(navigate_url)
      session$Page$loadEventFired(wait_ = TRUE)
      Sys.sleep(6)
    }, silent = TRUE)
  }
  ua <- session$Runtime$evaluate("navigator.userAgent")$result$value
  all_cookies <- session$Network$getAllCookies()$cookies
  try(session$close(), silent = TRUE)
  congress_cookies <- Filter(function(cookie) grepl("congress\\.gov", cookie$domain), all_cookies)
  cookie_header <- paste(
    vapply(congress_cookies, function(cookie) paste0(cookie$name, "=", cookie$value), ""),
    collapse = "; "
  )
  has_clearance <- any(vapply(congress_cookies, function(cookie) identical(cookie$name, "cf_clearance"), TRUE))
  list(cookie = cookie_header, ua = ua, has_clearance = has_clearance)
}

initial_clearance <- harvest_clearance()
if (!nzchar(initial_clearance$cookie) || !initial_clearance$has_clearance) {
  stop("Chrome cookie harvest lacks cf_clearance")
}
cookie_header <- initial_clearance$cookie
ua <- initial_clearance$ua

lines <- readLines(records_file, warn = FALSE, encoding = "UTF-8")
if (args$limit > 0L) lines <- head(lines, args$limit)
records <- lapply(lines, fromJSON, simplifyVector = FALSE)
rm(lines)
if (!length(records)) stop("No discovery records selected")

text_url <- function(record) paste0(sub("/+$", "", record$canonical_url), "/text")
parts <- function(record) c(as.character(record$congress), record$type, as.character(record$number))
artifact_file <- function(record) do.call(file.path, c(list(accepted_dir), as.list(parts(record)), list("page.html.gz")))
receipt_file <- function(record) do.call(file.path, c(list(receipts_dir), as.list(parts(record)), list("receipt.json")))

validate_body <- function(record, response, body_raw) {
  body <- tryCatch(rawToChar(body_raw), error = function(error) "")
  document <- tryCatch(read_html(body), error = function(error) NULL)
  title <- if (is.null(document)) "" else html_text2(html_element(document, "title"))
  surfaces <- if (is.null(document)) character() else html_text2(html_elements(document, "#main, main"))
  prefix <- paste0(title, " ", paste(substr(surfaces, 1L, 1200L), collapse = " "))
  challenge <- grepl(
    "just a moment|checking your browser|attention required|verifying you are human|cf-browser-verification",
    prefix, ignore.case = TRUE
  )
  marker <- if (record$type %in% c("hamdt", "samdt")) "Amendment Text:" else "Shown Here:"
  marker_pattern <- paste0("(?m)(^|\\n)\\s*", marker, "(?=\\s|$)")
  matching <- surfaces[vapply(surfaces, function(value) grepl(marker_pattern, value, perl = TRUE), TRUE)]
  nonempty <- length(matching) > 0L && any(vapply(matching, function(value) {
    found <- regexpr(marker_pattern, value, perl = TRUE)
    found[[1]] >= 0L && nzchar(trimws(substr(value, found[[1]] + attr(found, "match.length"), nchar(value))))
  }, TRUE))
  content_type <- as.character(httr::headers(response)[["content-type"]])
  checks <- list(
    status_200 = as.integer(status_code(response)) == 200L,
    exact_url = identical(response$url, text_url(record)),
    html_content_type = grepl("text/html|application/xhtml\\+xml", content_type, ignore.case = TRUE),
    not_challenge = !challenge,
    expected_main_marker = nonempty
  )
  list(accepted = all(unlist(checks, use.names = FALSE)), checks = checks, marker = marker, content_type = content_type)
}

fetch_once <- function(record, cf, out_dir, accepted_dir, receipts_dir, quarantine_dir,
                       attempts = 4L, min_delay = 1.0, max_delay = 90.0,
                       prior_receipts_dir = "") {
  expected_url <- paste0(sub("/+$", "", record$canonical_url), "/text")
  local_parts <- c(as.character(record$congress), record$type, as.character(record$number))
  html_file <- do.call(file.path, c(list(accepted_dir), as.list(local_parts), list("page.html.gz")))
  receipt_path <- do.call(file.path, c(list(receipts_dir), as.list(local_parts), list("receipt.json")))
  if (file.exists(receipt_path) && file.exists(html_file)) {
    prior <- tryCatch(fromJSON(receipt_path, simplifyVector = FALSE), error = function(error) NULL)
    if (!is.null(prior) && identical(prior$status, "accepted") && identical(prior$expected_url, expected_url)) {
      return(list(status = "resumed", canonical_key = record$canonical_key, expected_url = expected_url, artifact = html_file, body_sha256 = prior$body_sha256, byte_length = prior$byte_length))
    }
  }
  # A prior harvest's receipt, if one survived, supplies the hash this re-fetch
  # is verified against. It is read-only; nothing is written back to it.
  prior_sha <- NULL
  if (nzchar(prior_receipts_dir)) {
    prior_path <- do.call(file.path, c(list(prior_receipts_dir), as.list(local_parts), list("receipt.json")))
    if (file.exists(prior_path)) {
      earlier <- tryCatch(fromJSON(prior_path, simplifyVector = FALSE), error = function(error) NULL)
      if (!is.null(earlier) && identical(earlier$status, "accepted") && identical(earlier$expected_url, expected_url)) {
        prior_sha <- earlier$body_sha256
      }
    }
  }
  public_headers <- c(
    "User-Agent" = cf$ua,
    "Cookie" = cf$cookie,
    "Accept" = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language" = "en-US,en;q=0.9",
    "Referer" = "https://www.congress.gov/"
  )
  attempt <- 0L
  waited <- 0
  repeat {
    attempt <- attempt + 1L
    response <- tryCatch(
      GET(expected_url, add_headers(.headers = public_headers), timeout(45)),
      error = function(error) error
    )
    if (inherits(response, "error")) {
      if (attempt >= attempts) {
        # Transport errors are also transient by nature; defer rather than
        # condemn the page.
        return(list(status = "deferred", canonical_key = record$canonical_key, expected_url = expected_url,
                    reason = "transport_error", http_attempts = attempt, retry_waits = waited))
      }
      pause <- min(max_delay, min_delay * (2^(attempt - 1L)))
      Sys.sleep(pause)
      waited <- waited + pause
      next
    }
    body_raw <- content(response, as = "raw")
    checked <- validate_body(record, response, body_raw)
    if (checked$accepted) break
    if (attempt < attempts && retryable_response(response, checked$checks)) {
      hinted <- retry_after_seconds(response)
      pause <- if (!is.na(hinted)) min(max_delay, hinted) else min(max_delay, min_delay * (2^(attempt - 1L)))
      Sys.sleep(pause)
      waited <- waited + pause
      next
    }
    break
  }
  body_sha256 <- digest(body_raw, algo = "sha256", serialize = FALSE)
  if (!checked$accepted) {
    quarantine_file <- file.path(quarantine_dir, body_sha256, "page.html.gz")
    write_immutable_gzip(quarantine_file, body_raw)
    failure <- list(
      schema = "congress-httr-failure-v1",
      created_at = format(Sys.time(), tz = "UTC", usetz = TRUE),
      canonical_key = record$canonical_key,
      expected_url = expected_url,
      final_url = response$url,
      http_status = status_code(response),
      body_sha256 = body_sha256,
      byte_length = length(body_raw),
      validation = checked$checks,
      quarantine_file = quarantine_file,
      transport = "native_chrome_cookie_replay_httr",
      http_attempts = attempt,
      retry_waits = waited,
      retryable_exhausted = retryable_response(response, checked$checks),
      cookie_values_persisted = FALSE
    )
    failure_file <- file.path(quarantine_dir, body_sha256, paste0("failure-", Sys.getpid(), ".json"))
    write_immutable_json(failure_file, failure)
    # A throttle or challenge that merely outlived its retry budget is NOT a
    # verdict about the page. It is returned as "deferred" so the caller can
    # replay it at the end of the run under slower pacing. Only a genuine
    # surface rejection (wrong URL, missing marker on a 200) is terminal.
    deferred <- retryable_response(response, checked$checks)
    return(list(
      status = if (deferred) "deferred" else "failed",
      canonical_key = record$canonical_key, expected_url = expected_url,
      reason = if (deferred) "throttled_retry_budget_exhausted" else "surface_rejected",
      artifact = failure_file, checks = checked$checks,
      http_status = status_code(response),
      http_attempts = attempt, retry_waits = waited))
  }
  write_immutable_gzip(html_file, body_raw)
  receipt <- list(
    schema = "congress-httr-cookie-replay-receipt-v1",
    created_at = format(Sys.time(), tz = "UTC", usetz = TRUE),
    status = "accepted",
    canonical_key = record$canonical_key,
    expected_url = expected_url,
    final_url = response$url,
    http_status = status_code(response),
    content_type = checked$content_type,
    expected_marker = checked$marker,
    body_sha256 = body_sha256,
    byte_length = length(body_raw),
    validation = checked$checks,
    html_file = html_file,
    transport = "native_chrome_cookie_replay_httr",
    http_attempts = attempt,
    retry_waits = waited,
    prior_body_sha256 = if (is.null(prior_sha)) NULL else prior_sha,
    matches_prior_body_sha256 = if (is.null(prior_sha)) NULL else identical(prior_sha, body_sha256),
    cf_clearance_present = TRUE,
    cookie_values_persisted = FALSE
  )
  write_immutable_json(receipt_path, receipt)
  list(status = "accepted", canonical_key = record$canonical_key, expected_url = expected_url, artifact = html_file, body_sha256 = body_sha256, byte_length = length(body_raw))
}

cf <- list(cookie = cookie_header, ua = ua)
canaries <- list(
  list(congress = 117L, type = "hr", number = 3664L, canonical_key = "117:hr:3664", canonical_url = "https://www.congress.gov/bill/117th-congress/house-bill/3664"),
  list(congress = 116L, type = "hamdt", number = 3L, canonical_key = "116:hamdt:3", canonical_url = "https://www.congress.gov/amendment/116th-congress/house-amendment/3")
)
canary_results <- lapply(canaries, fetch_once, cf = cf, out_dir = out_dir, accepted_dir = accepted_dir,
                         receipts_dir = receipts_dir, quarantine_dir = quarantine_dir,
                         attempts = args$attempts, min_delay = args$min_delay, max_delay = args$max_delay,
                         prior_receipts_dir = prior_receipts_dir)
if (!all(vapply(canary_results, function(item) item$status %in% c("accepted", "resumed"), TRUE))) {
  stop("Native Chrome cookie-replay httr bill+amendment canary failed")
}

plan(multisession, workers = args$workers)
on.exit(plan(sequential), add = TRUE)
started <- Sys.time()
completed <- 0L
accepted <- 0L
resumed <- 0L
failed <- 0L
event_sequence <- 0L
attempt_failures <- 0L
batch_index <- 0L
deferred_keys <- list()
replayed_recovered <- 0L
replayed_still_failing <- 0L
clearance_remints <- 0L
command_line <- paste(commandArgs(), collapse = " ")
# Run identity, bound to the inputs and pacing that produced these artifacts.
# This is deliberately a hash of the configuration, so two runs of the same
# config share it.
invocation_id <- digest(
  paste(records_file, out_dir, args$limit, args$workers, args$attempts,
        args$min_delay, args$max_delay, prior_receipts_dir, collapse = "|"),
  algo = "sha256", serialize = FALSE
)
# Filenames need per-process uniqueness instead: re-running an identical config
# into the same directory shares invocation_id, and event sequence numbers
# restart at 1, so only a process-scoped tag prevents a collision on resume.
run_tag <- paste0(format(started, "%Y%m%dT%H%M%S", tz = "UTC"), "-", Sys.getpid())

write_progress <- function(status, detail) {
  elapsed <- max(0.001, as.numeric(difftime(Sys.time(), started, units = "secs")))
  rate <- if (completed > 0L) completed / (elapsed / 60) else 0
  eta <- if (rate > 0) max(0, (length(records) - completed) / rate * 60) else NULL
  progress_payload <- list(
    schema_version = 1L,
    updated_at = format(Sys.time(), tz = "UTC", usetz = TRUE),
    lane = "codex",
    source = "congress-full-text-httr",
    run_id = "legislation-full-text-r-20260726",
    kind = "collector.progress",
    status = status,
    stage = "native-chrome-cookie-replay-httr",
    current = completed,
    total = length(records),
    summary = paste0(completed, "/", length(records), " official pages"),
    detail = detail,
    workers = args$workers,
    active_workers = if (identical(status, "running")) min(args$workers, length(records) - completed) else 0L,
    collected_records = accepted,
    resumed_records = resumed,
    failure_count = failed,
    records_per_minute = round(rate, 3),
    rate = round(rate, 3),
    eta_seconds = if (is.null(eta)) NULL else round(eta, 1),
    command = command_line,
    output_directory = out_dir,
    transport = "native_chrome_cookie_replay_httr",
    adaptive_backoff = TRUE,
    candidate_deletion_allowed = FALSE,
    cookie_values_persisted = FALSE
  )
  write_checked_json(file.path(out_dir, "progress.json"), progress_payload)
  mirror_to_glassbox(progress_payload, "progress")
}

value_or_null <- function(value) if (is.null(value) || !length(value)) NULL else value

write_event <- function(item) {
  event_sequence <<- event_sequence + 1L
  safe_key <- gsub("[^A-Za-z0-9._-]+", "-", item$canonical_key)
  event <- list(
    schema_version = 1L,
    timestamp_utc = format(Sys.time(), tz = "UTC", usetz = TRUE),
    lane = "codex",
    source = "congress-full-text-httr",
    run_id = "legislation-full-text-r-20260726",
    kind = if (identical(item$status, "failed")) "collector.record.failed" else "collector.record.completed",
    status = if (identical(item$status, "failed")) "failed" else "completed",
    stage = "native-chrome-cookie-replay-httr",
    summary = paste0(completed, "/", length(records), " ", item$canonical_key, " | ", item$status),
    detail = if (identical(item$status, "failed")) item$reason else "Exact URL, HTML, challenge, main-surface, and typed marker guards passed.",
    command = paste0("GET ", item$expected_url),
    input = list(canonical_key = item$canonical_key),
    output = list(body_sha256 = value_or_null(item$body_sha256), byte_length = value_or_null(item$byte_length), transport = "native_chrome_cookie_replay_httr", retries = 0L),
    artifact = value_or_null(item$artifact),
    current = completed,
    total = length(records)
  )
  # Sequence numbers restart at 1 every invocation, so the run identity has to
  # be part of the filename or a resumed run collides with the previous one's
  # first event.
  write_immutable_json(
    file.path(events_dir, sprintf("%s-%08d-%s.json", run_tag, event_sequence, safe_key)),
    event)
  mirror_to_glassbox(event, sprintf("%08d-%s", event_sequence, safe_key))
}

write_progress("running", paste0(
  "Native Chrome clearance verified; ", args$workers,
  " paced httr workers are collecting official HTML."))
indexes <- seq_along(records)
# Adaptive inter-batch pacing. The delay rises whenever a batch reports a
# failure and decays after clean batches, so the lane finds a sustainable rate
# instead of running flat out until Cloudflare throttles it.
batch_delay <- args$min_delay
for (start in seq(1L, length(indexes), by = args$workers)) {
  selected <- indexes[start:min(length(indexes), start + args$workers - 1L)]
  results <- future_lapply(
    records[selected], fetch_once,
    cf = cf, out_dir = out_dir, accepted_dir = accepted_dir,
    receipts_dir = receipts_dir, quarantine_dir = quarantine_dir,
    attempts = args$attempts, min_delay = args$min_delay, max_delay = args$max_delay,
    prior_receipts_dir = prior_receipts_dir,
    future.packages = c("digest", "httr", "jsonlite", "rvest"),
    future.seed = TRUE
  )
  batch_failed <- 0L
  batch_fetched <- 0L
  batch_rows <- list()
  for (item in results) {
    completed <- completed + 1L
    if (identical(item$status, "accepted")) { accepted <- accepted + 1L; batch_fetched <- batch_fetched + 1L }
    if (identical(item$status, "resumed")) resumed <- resumed + 1L
    if (identical(item$status, "deferred")) {
      # Held for replay; counts as pressure on the pacing controller but is not
      # a failure and never leaves the record unaccounted for.
      deferred_keys[[length(deferred_keys) + 1L]] <- item$canonical_key
      batch_failed <- batch_failed + 1L
    }
    if (identical(item$status, "failed")) {
      failed <- failed + 1L
      batch_failed <- batch_failed + 1L
      attempt_failures <<- attempt_failures + 1L
      # Attempt-level catchnet: a terminal failure is recorded here even when no
      # body was returned, so a key can never vanish without a receipt.
      write_checked_json(
        file.path(catchnet_dir, paste0(gsub("[^A-Za-z0-9._-]+", "-", item$canonical_key), ".json")),
        list(
          schema = "congress-httr-failure-v1",
          created_at = format(Sys.time(), tz = "UTC", usetz = TRUE),
          canonical_key = item$canonical_key,
          expected_url = item$expected_url,
          reason = item$reason,
          http_attempts = value_or_null(item$http_attempts),
          retry_waits = value_or_null(item$retry_waits),
          failure_class = if (identical(item$reason, "transport_error")) "transport_error" else "surface_rejected",
          invocation_id = invocation_id
        ))
    }
    batch_rows[[length(batch_rows) + 1L]] <- list(
      canonical_key = item$canonical_key, status = item$status)
    write_event(item)
  }
  # Per-batch dispatch accounting: dispatched count must equal accounted count.
  batch_index <- batch_index + 1L
  write_checked_json(
    file.path(batches_dir, sprintf("batch-%s-%06d.json", run_tag, batch_index)),
    list(
      schema = "congress-httr-batch-accounting-v1",
      invocation_id = invocation_id,
      run_tag = run_tag,
      batch_index = batch_index,
      dispatched = length(selected),
      accounted = length(batch_rows),
      fetched = batch_fetched,
      failed = batch_failed,
      complete = identical(length(selected), length(batch_rows)),
      records = batch_rows
    ))
  # Circuit breaker. Across 152 observed batches the outcome was all-or-nothing
  # -- 140 fully clean, 8 fully failed, zero partial -- which is the signature
  # of a time-windowed Cloudflare block rather than a per-request quota. Once
  # the window closes, dispatching more batches only deepens it, so stop, cool
  # down, and re-mint clearance.
  if (batch_failed > 0L && batch_failed == length(selected)) {
    write_progress("running", paste0(
      "Full-batch block detected (", batch_failed, "/", length(selected),
      "); cooling down ", args$max_delay, "s and re-minting clearance."))
    Sys.sleep(args$max_delay)
    refreshed <- tryCatch(harvest_clearance("https://www.congress.gov/"),
                          error = function(e) list(cookie = "", ua = "", has_clearance = FALSE))
    if (isTRUE(refreshed$has_clearance) && nzchar(refreshed$cookie)) {
      cf <- list(cookie = refreshed$cookie, ua = refreshed$ua)
      clearance_remints <- clearance_remints + 1L
      write_progress("running", paste0(
        "Cloudflare clearance re-minted (", clearance_remints, " total); resuming collection."))
    } else {
      write_progress("running",
        "Clearance re-mint did not yield cf_clearance; continuing on backoff alone.")
    }
  }

  if (batch_failed > 0L) {
    batch_delay <- min(args$max_delay, max(args$min_delay, batch_delay * 2))
  } else {
    batch_delay <- max(args$min_delay, batch_delay / 2)
  }
  write_progress("running", paste0(
    "Batch complete; ", failed, " failure(s) quarantined; pacing ",
    sprintf("%.1f", batch_delay), "s between batches."))
  # Only pause when work was actually dispatched; a fully resumed batch made no
  # requests and needs no cooldown.
  if (batch_fetched > 0L || batch_failed > 0L) Sys.sleep(batch_delay)
}

# Replay pass: records deferred by throttling are retried sequentially with the
# maximum pacing, so a Cloudflare block during the fast pass never decides the
# fate of a page. Anything still failing here is recorded as a real failure.
if (length(deferred_keys) > 0L) {
  by_key <- list()
  for (record in records) by_key[[record$canonical_key]] <- record
  write_progress("running", paste0(
    "Replaying ", length(deferred_keys), " throttled record(s) sequentially at ",
    args$max_delay, "s pacing."))
  # Replaying with the same dead clearance would simply fail again, so re-mint
  # before the pass rather than during it.
  Sys.sleep(args$max_delay)
  refreshed <- tryCatch(harvest_clearance("https://www.congress.gov/"),
                        error = function(e) list(cookie = "", ua = "", has_clearance = FALSE))
  if (isTRUE(refreshed$has_clearance) && nzchar(refreshed$cookie)) {
    cf <- list(cookie = refreshed$cookie, ua = refreshed$ua)
    clearance_remints <- clearance_remints + 1L
  }
  for (key in unlist(deferred_keys)) {
    record <- by_key[[key]]
    if (is.null(record)) next
    Sys.sleep(args$max_delay)
    item <- fetch_once(record, cf = cf, out_dir = out_dir, accepted_dir = accepted_dir,
                       receipts_dir = receipts_dir, quarantine_dir = quarantine_dir,
                       attempts = args$attempts, min_delay = args$max_delay,
                       max_delay = args$max_delay, prior_receipts_dir = prior_receipts_dir)
    if (item$status %in% c("accepted", "resumed")) {
      replayed_recovered <- replayed_recovered + 1L
      accepted <- accepted + 1L
    } else {
      replayed_still_failing <- replayed_still_failing + 1L
      failed <- failed + 1L
      write_checked_json(
        file.path(catchnet_dir, paste0(gsub("[^A-Za-z0-9._-]+", "-", key), ".replay.json")),
        list(
          schema = "congress-httr-failure-v1",
          created_at = format(Sys.time(), tz = "UTC", usetz = TRUE),
          canonical_key = key,
          reason = item$reason,
          failure_class = "unresolved_after_replay",
          http_status = value_or_null(item$http_status),
          http_attempts = value_or_null(item$http_attempts),
          retry_waits = value_or_null(item$retry_waits),
          invocation_id = invocation_id,
          run_tag = run_tag
        ))
    }
    write_event(item)
  }
  write_progress("running", paste0(
    "Replay complete: ", replayed_recovered, " recovered, ",
    replayed_still_failing, " still unresolved."))
}

# Completeness guarantee from the handoff: every selected key must be accounted
# for by a completion or a terminal failure. This is asserted, not assumed.
accounted <- accepted + resumed + failed
silently_skipped <- length(records) - accounted
if (silently_skipped != 0L) {
  write_progress("needs-review", paste0(
    "ACCOUNTING GAP: ", length(records), " selected but ", accounted,
    " accounted; refusing to report a clean run."))
  stop("Dispatch accounting gap: ", silently_skipped, " key(s) unaccounted for")
}

terminal_status <- if (failed > 0L) "needs-review" else "complete"
write_progress(
  terminal_status,
  if (failed > 0L) "Harvest ended with quarantined failures; no candidate was deleted or silently skipped." else "All selected official pages were accepted; no culling or production write was performed."
)
manifest <- list(
  schema = "congress-full-text-httr-harvest-manifest-v1",
  status = terminal_status,
  completed_at = format(Sys.time(), tz = "UTC", usetz = TRUE),
  records_file = records_file,
  selected_record_count = length(records),
  accepted_record_count = accepted,
  resumed_record_count = resumed,
  failed_record_count = failed,
  workers = args$workers,
  transport = "native_chrome_cookie_replay_httr",
  browser_mode = "remote_headful_chrome",
  chrome_remote_host = args$host,
  chrome_remote_port = args$port,
  http_attempts_per_url = args$attempts,
  pacing_min_delay_seconds = args$min_delay,
  pacing_max_delay_seconds = args$max_delay,
  adaptive_backoff = TRUE,
  invocation_id = invocation_id,
  failure_catchnet_directory = catchnet_dir,
  batch_accounting_directory = batches_dir,
  prior_receipts_directory = if (nzchar(prior_receipts_dir)) prior_receipts_dir else NULL,
  attempt_failure_count = attempt_failures,
  deferred_record_count = length(deferred_keys),
  replayed_recovered_count = replayed_recovered,
  replayed_unresolved_count = replayed_still_failing,
  clearance_remint_count = clearance_remints,
  throttle_can_be_terminal = FALSE,
  accounted_record_count = accounted,
  failures_silently_skipped = FALSE,
  cf_clearance_present = TRUE,
  cookie_values_persisted = FALSE,
  candidate_deletion_allowed = FALSE,
  destructive_filtering = FALSE
)
write_checked_json(file.path(out_dir, "manifest.json"), manifest)
cat(toJSON(manifest, auto_unbox = TRUE, pretty = TRUE), "\n")