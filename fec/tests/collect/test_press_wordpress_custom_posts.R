# Pure fixture tests. All HTTP responses and checkpoint paths are private.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 2L)
.libPaths(c(file.path(dirname(args[[1]]), "..", "..", "outputs", "r-library"), .libPaths()))
source(args[[1]], local = globalenv())
# In-run retry wait: zero by default so no test sleeps; the knob test sets and records it.
Sys.setenv(PRESS_SITE_RETRY_DELAY_S = "0")
slept <- numeric(0)
options(press_site_sleep = function(seconds) slept <<- c(slept, seconds))

make_record <- function(id, slug, day = Sys.Date(), host = "www.ossoff.senate.gov") list(
  id = id,
  date = paste0(as.character(day), "T12:00:00"),
  date_gmt = paste0(as.character(day), "T16:00:00"),
  modified = paste0(as.character(day), "T13:00:00"),
  link = paste0("https://", host, "/press-releases/", slug, "/"),
  slug = slug,
  title = list(rendered = paste("Official &amp; dated", slug)),
  content = list(rendered = paste0("<p>Official body for ", slug, " ",
    paste(rep("with enough retained words to establish that the rendered API content is used.",
              3L), collapse = " "), "</p>"))
)

fixture <- function(records, declared_total = length(records), second_total = declared_total,
                    unavailable = NULL, by_host = NULL, fail_times = Inf) {
  env <- new.env(parent = globalenv())
  source(args[[2]], local = env)
  env$DATE_FLOOR <- Sys.Date() - 10L
  env$CHECKPOINT_DIR <- tempfile("press-wp-checkpoints-")
  dir.create(file.path(env$CHECKPOINT_DIR, "fulltext"), recursive = TRUE)
  env$squish <- function(value) trimws(gsub("[[:space:]]+", " ", value))
  env$write_rds_atomic <- function(value, path) {
    temp <- paste0(path, ".part")
    saveRDS(value, temp)
    if (file.exists(path)) unlink(path)
    stopifnot(file.rename(temp, path))
  }
  env$stage_index <- function(members, disc, force = FALSE) data.frame(
    bioguide = c("O000174", "O000174"),
    title = c("undated archive duplicate", "archive only"),
    url = c("https://www.ossoff.senate.gov/press-releases/current/",
            "https://www.ossoff.senate.gov/es/press-releases/archive-only"),
    date = as.Date(c(NA, NA)), member = "Jon Ossoff", chamber = "Senate",
    state = "GA", party = "Democrat", stringsAsFactors = FALSE)
  env$fulltext_calls <- list()
  env$stage_fulltext <- function(idx, force = FALSE, js_bgs = character(0)) {
    env$fulltext_calls[[length(env$fulltext_calls) + 1L]] <- idx
    idx
  }
  calls <- character(0)
  hits <- 0L
  request <- function(url) {
    calls <<- c(calls, url)
    if (!is.null(unavailable) && grepl(unavailable, url) && (hits <<- hits + 1L) <= fail_times)
      press_site_unavailable(paste0("official WordPress endpoint unavailable (403): ", url),
                                 url, status = "403", error_class = "http_403")
    if (!is.null(by_host)) records <- by_host[[sub("^https?://([^/]+).*$", "\\1", url)]]
    declared_total <- if (is.null(by_host)) declared_total else length(records)
    second_total <- declared_total
    if (grepl("/types$", url)) {
      payload <- list(post = list(rest_base = "posts"),
                      release = list(rest_base = "press_releases"))
      return(list(status = 200L, headers = list(),
                  text = jsonlite::toJSON(payload, auto_unbox = TRUE), url = url))
    }
    page <- if (grepl("page=2", url, fixed = TRUE)) 2L else 1L
    selected <- if (page == 1L) utils::head(records, 100L) else utils::tail(records, -100L)
    total <- if (page == 1L) declared_total else second_total
    list(status = 200L,
         headers = list(`x-wp-total` = as.character(total),
                         `x-wp-totalpages` = as.character(if (declared_total > 100L) 2L else 1L)),
         text = jsonlite::toJSON(selected, auto_unbox = TRUE), url = url)
  }
  env$install_press_wordpress_custom_posts(env, request)
  list(env = env, calls = function() calls)
}

today <- Sys.Date()
records <- c(
  list(make_record(1L, "current", today)),
  lapply(2:101, function(number)
    make_record(number, sprintf("new-%03d", number), today - min(number - 1L, 10L)))
)
one <- fixture(records)
members <- data.frame(
  bioguide = c("O000174", "X000001"), member = c("Jon Ossoff", "Other"),
  chamber = c("Senate", "House"), state = c("GA", "XX"), party = c("Democrat", "Other"),
  url = c("https://www.ossoff.senate.gov", "https://other.house.gov"),
  stringsAsFactors = FALSE)
discovery <- data.frame(bioguide = members$bioguide)
checkpoint <- file.path(one$env$CHECKPOINT_DIR, "fulltext", "O000174.rds")
old <- data.frame(
  url = c("https://www.ossoff.senate.gov/press-releases/retained/",
          "https://www.ossoff.senate.gov/press-releases/current"),
  title_detail = c("retained title", "old deficient title"),
  date_detail = as.Date(c(today - 4L, NA)),
  body = c("immutable retained body", ""), stringsAsFactors = FALSE)
saveRDS(old, checkpoint)

index <- one$env$stage_index(members, discovery)
coverage <- press_official_coverage_snapshot(one$env)
stopifnot(nrow(index) == 102L, sum(index$press_wp_api %in% TRUE, na.rm = TRUE) == 101L,
          sum(!is.na(index$date)) == 101L,
          length(setdiff(vapply(records, `[[`, character(1), "link"),
                         c("https://www.ossoff.senate.gov/press-releases/current/",
                           "https://www.ossoff.senate.gov/es/press-releases/archive-only"))) == 100L,
          coverage$member_count == 1L, coverage$current_url_count == 101L,
          length(coverage$members[[1]]$requests) == 3L,
          all(vapply(coverage$members[[1]]$requests, function(request)
            grepl("^[a-f0-9]{64}$", request$raw_response_sha256), logical(1L))),
          index$title[index$url == records[[1]]$link] == "Official & dated current",
          length(one$calls()) == 3L,
          grepl("/wp-json/wp/v2/types$", one$calls()[1]),
          grepl("after=", one$calls()[2], fixed = TRUE),
          grepl("page=2", one$calls()[3], fixed = TRUE))
invisible(one$env$stage_fulltext(index))
cached <- readRDS(checkpoint)
stopifnot(nrow(cached) == 102L,
          cached$body[cached$url == old$url[1]] == old$body[1],
          all(vapply(records, function(record) record$link %in% cached$url, logical(1))),
          all(!is.na(cached$date_detail[cached$url %in% vapply(records, `[[`, character(1), "link")])),
          length(one$calls()) == 3L, length(one$env$fulltext_calls) == 1L)
wrapped <- one$env$stage_index
one$env$install_press_wordpress_custom_posts(one$env, function(url) stop("must not reinstall"))
stopifnot(identical(wrapped, one$env$stage_index))

# Missing/short API bodies keep inventory coverage but never replace a good
# checkpoint or turn an unrequested detail page into a completed article.
for (rendered in c("", "<p>Read more.</p>",
                   paste0("<p>", paste(rep("a", 25L), collapse = " "), "</p>"),
                   paste0("<p>", paste(rep(strrep("x", 30L), 10L), collapse = " "), "</p>"))) {
  weak_records <- list(make_record(1L, "retained-good"), make_record(2L, "needs-detail"))
  weak_records <- lapply(weak_records, function(record) {
    record$content$rendered <- rendered
    record
  })
  weak <- fixture(weak_records)
  weak_checkpoint <- file.path(weak$env$CHECKPOINT_DIR, "fulltext", "O000174.rds")
  retained <- data.frame(url = weak_records[[1L]]$link, title_detail = "retained title",
    date_detail = as.Date(today - 3L),
    body = paste(rep("Previously fetched complete official release evidence.", 20L), collapse = " "),
    stringsAsFactors = FALSE)
  saveRDS(retained, weak_checkpoint)
  before_bytes <- readBin(weak_checkpoint, "raw", file.info(weak_checkpoint)$size)
  weak_index <- weak$env$stage_index(members, discovery)
  stopifnot(sum(weak_index$press_wp_api %in% TRUE) == 2L,
            !any(weak_index$press_wp_body_usable %in% TRUE))
  invisible(weak$env$stage_fulltext(weak_index))
  stopifnot(identical(before_bytes, readBin(weak_checkpoint, "raw", file.info(weak_checkpoint)$size)),
            all(vapply(weak_records, `[[`, character(1L), "link") %in%
                  weak$env$fulltext_calls[[1L]]$url))

  # Execute the actual upstream member fetcher with a mocked HTTP function,
  # using only this private checkpoint. A retained good body skips collection;
  # the unseeded URL performs a real collector GET and stores the detail body.
  upstream <- file.path(dirname(args[[2L]]), "..", "..", "..", "Draft Systems",
                         "cu_press_release_scraper.R")
  expressions <- parse(upstream)
  assignment <- Filter(function(expression) is.call(expression) &&
    identical(expression[[1L]], as.name("<-")) &&
    identical(expression[[2L]], as.name("fetch_member_fulltext")), as.list(expressions))
  stopifnot(length(assignment) == 1L)
  eval(assignment[[1L]], envir = weak$env)
  weak$env$bind_rows <- dplyr::bind_rows
  weak$env$FULLTEXT_DELAY <- 0
  weak$env$CKPT_EVERY <- 100L
  detail_gets <- character(0)
  weak$env$fetch_html <- function(url, delay) {
    detail_gets <<- c(detail_gets, url)
    list(html = url)
  }
  weak$env$extract_release <- function(page, url) data.frame(
    url = url, title_detail = "retrieved detail", date_detail = today,
    body = paste(rep("A complete independently retrieved official detail article.", 20L), collapse = " "),
    stringsAsFactors = FALSE)
  invisible(weak$env$fetch_member_fulltext("O000174",
    vapply(weak_records, `[[`, character(1L), "link")))
  recovered <- readRDS(weak_checkpoint)
  stopifnot(identical(detail_gets, weak_records[[2L]]$link),
    identical(recovered[recovered$url == retained$url, names(retained), drop = FALSE], retained),
    nrow(recovered) == 2L,
    weak$env$press_wp_usable_body(recovered$body[recovered$url == weak_records[[2L]]$link]))
}

# Hash-bound index metadata cannot authorize mutated body text at seed time.
tamper <- fixture(list(make_record(1L, "current")))
tamper_index <- tamper$env$stage_index(members, discovery)
tamper_records <- get("state", envir = environment(tamper$env$stage_fulltext))$records
tamper_records$press_wp_body[[1L]] <- paste(rep("Unbound replacement body text.", 30L), collapse = " ")
stopifnot(inherits(try(tamper$env$press_wp_seed_checkpoints(
  tamper_index, tamper_records, tamper$env), silent = TRUE), "try-error"),
  !file.exists(file.path(tamper$env$CHECKPOINT_DIR, "fulltext", "O000174.rds")))

# Partial pagination is fatal and cannot write a body checkpoint.
partial <- fixture(records, declared_total = 102L)
bad_checkpoint <- file.path(partial$env$CHECKPOINT_DIR, "fulltext", "O000174.rds")
stopifnot(inherits(try(partial$env$stage_index(members, discovery), silent = TRUE), "try-error"),
          !file.exists(bad_checkpoint))

# A cross-origin link or future publication date is rejected before caching.
for (bad in list(
    list(make_record(1L, "foreign", today, "example.com")),
    list(make_record(1L, "future", today + 1L)),
    list(make_record(1L, "out-of-order-old", today - 1L),
         make_record(2L, "out-of-order-new", today)))) {
  broken <- fixture(bad)
  broken_checkpoint <- file.path(broken$env$CHECKPOINT_DIR, "fulltext", "O000174.rds")
  stopifnot(inherits(try(broken$env$stage_index(members, discovery), silent = TRUE), "try-error"),
            !file.exists(broken_checkpoint))
}

# D-294: one member site's availability failure (403, timeout, SSL, non-JSON) is recorded and the
# member skipped; the other members are still collected and the run goes on.
two_members <- data.frame(
  bioguide = c("O000174", "M001198"), member = c("Jon Ossoff", "Roger Marshall"),
  chamber = c("Senate", "Senate"), state = c("GA", "KS"), party = c("Democrat", "Republican"),
  url = c("https://www.ossoff.senate.gov", "https://www.marshall.senate.gov"),
  stringsAsFactors = FALSE)
marshall_records <- list(make_record(7L, "marshall-current", today, "www.marshall.senate.gov"))
skip <- fixture(list(make_record(1L, "unused")), unavailable = "ossoff",
                by_host = list(`www.marshall.senate.gov` = marshall_records))
skipped_index <- skip$env$stage_index(two_members, data.frame(bioguide = two_members$bioguide))
failures <- press_site_failures_snapshot(skip$env)
stopifnot(length(failures) == 1L, failures[[1]]$member_id == "O000174",
          failures[[1]]$http_status == "403", failures[[1]]$error_class == "http_403",
          grepl("/wp-json/wp/v2/types$", failures[[1]]$url),
          sum(skipped_index$press_wp_api %in% TRUE, na.rm = TRUE) == 1L,
          press_site_failures_snapshot(skip$env)[[1]]$source == "official_wordpress_custom_post",
          press_official_coverage_snapshot(skip$env)$member_count == 1L)
stopifnot(!press_site_all_failed(failures, skipped_index))
# The skipped site was retried exactly once (two /types requests), after zero wait (knob = 0).
stopifnot(sum(grepl("ossoff.*/types$", skip$calls())) == 2L, length(slept) == 0L)
# Every member that contributed an index row failed: the run is genuinely down.
only <- skipped_index[skipped_index$bioguide == "O000174", , drop = FALSE]
stopifnot(press_site_all_failed(failures, only),
          !press_site_all_failed(list(), only))

# In-run retry: a site that is down on the first pass and up on the retry is collected normally
# and is NOT recorded as a failure.  The wait is the PRESS_SITE_RETRY_DELAY_S knob, taken once.
Sys.setenv(PRESS_SITE_RETRY_DELAY_S = "7")
by_host_both <- list(`www.ossoff.senate.gov` = list(make_record(1L, "ossoff-current", today)),
                     `www.marshall.senate.gov` = marshall_records)
flaky <- fixture(list(), unavailable = "ossoff", fail_times = 1L, by_host = by_host_both)
flaky_index <- flaky$env$stage_index(two_members, data.frame(bioguide = two_members$bioguide))
stopifnot(length(press_site_failures_snapshot(flaky$env)) == 0L,
          sum(flaky_index$press_wp_api %in% TRUE, na.rm = TRUE) == 2L,
          press_official_coverage_snapshot(flaky$env)$member_count == 2L,
          identical(slept, 7))
# Both sites down for good: one wait for the whole retry pass, both recorded.
slept <- numeric(0)
both_down <- fixture(list(), unavailable = "senate", by_host = by_host_both)
try(both_down$env$stage_index(two_members, data.frame(bioguide = two_members$bioguide)), silent = TRUE)
stopifnot(length(press_site_failures_snapshot(both_down$env)) == 2L, identical(slept, 7))
# An integrity stop is never deferred or retried.
slept <- numeric(0)
integrity <- fixture(list(make_record(1L, "foreign", today, "example.com")))
try(integrity$env$stage_index(members, discovery), silent = TRUE)
stopifnot(length(slept) == 0L)
Sys.setenv(PRESS_SITE_RETRY_DELAY_S = "0")
stopifnot(press_site_retry_delay() == 0)
Sys.setenv(PRESS_SITE_RETRY_DELAY_S = "garbage")
stopifnot(press_site_retry_delay() == 60)
Sys.setenv(PRESS_SITE_RETRY_DELAY_S = "0")

# An integrity violation (not an availability failure) stays fatal and is never recorded as a skip.
foreign <- fixture(list(make_record(1L, "foreign", today, "example.com")))
stopifnot(inherits(try(foreign$env$stage_index(members, discovery), silent = TRUE), "try-error"),
          length(press_site_failures_snapshot(foreign$env)) == 0L)

# Availability classes.
env_classes <- skip$env
stopifnot(press_site_error_class(403L, "") == "http_403",
          press_site_error_class(404L, "") == "http_404",
          press_site_error_class(503L, "") == "http_5xx",
          press_site_error_class(NA, "Timeout was reached") == "timeout",
          press_site_error_class(NA, "SSL certificate problem") == "ssl",
          press_site_error_class(NA, "Could not resolve host") == "network_error")

cat("PASS: official custom-post pagination, exact dates, canonical identity, body seeding, provenance rejection and retained caches\n")
