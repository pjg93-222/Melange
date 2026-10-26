# Pure fixture tests: no network, no live checkpoints. Every REST/HTML fixture under
# fixtures/press_host_routes was recorded from the official site on 2026-10-20 (PROVENANCE.md there).
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 4L)   # press_host_routes.R, press_wordpress_custom_posts.R, press_backlog.R, fixture dir
.libPaths(c(file.path(dirname(args[[1]]), "..", "..", "outputs", "r-library"), .libPaths()))
suppressMessages({library(xml2); library(rvest)})
fixture_dir <- args[[4]]
read_fixture <- function(name) paste(readLines(file.path(fixture_dir, name), warn = FALSE, encoding = "UTF-8"),
                                     collapse = "\n")
words <- function(text) length(strsplit(trimws(text), "[[:space:]]+")[[1L]])
squish <- function(value) trimws(gsub("[[:space:]]+", " ", value))

HUSTED_URL <- "https://www.husted.senate.gov/media/press-releases/democrats-block-husteds-bill-forcing-data-centers-to-pay-their-own-way"
HUSTED_SLUG <- "democrats-block-husteds-bill-forcing-data-centers-to-pay-their-own-way"
KIGGANS_URL <- "https://kiggans.house.gov/2026/09/14/kiggans-bill-to-ensure-proper-lifeguard-staffing-on-public-beaches-passes-the-house-with-bipartisan-support/"
KIGGANS_SLUG <- "kiggans-bill-to-ensure-proper-lifeguard-staffing-on-public-beaches-passes-the-house-with-bipartisan-support"
NTTNT_SLUG <- "lankford-subcommittee-examines-judicial-review-in-federal-regulatory-process"
NTTNT_URL <- paste0("https://www.lankford.senate.gov/news/press-releases/", NTTNT_SLUG, "nttnt")
TRUNC_SLUG <- "lankford-abraham-accords-caucus-"
TRUNC_URL <- paste0("https://www.lankford.senate.gov/news/press-releases/", TRUNC_SLUG)
PREFIX_SLUG <- "lankford-abraham-accords-caucus-members-commemorate-four-year-anniversary-of-historic-agreement"

# One harness per case: a fresh environment, the upstream pieces stubbed, the real route code and the real
# backlog "complete body" predicate, a request log, and a member-fetch stub that records what the existing path saw.
harness <- function(responses = list(), fetch_page = function(u) NULL, extract = function(pg, u) NULL,
                    existing_rows = NULL, delay = 0, crash = FALSE, clock = NULL) {
  env <- new.env(parent = globalenv())
  env$squish <- squish
  source(args[[2]], local = env)
  source(args[[3]], local = env)
  source(args[[1]], local = env)
  env$CHECKPOINT_DIR <- tempfile("press-host-routes-")
  dir.create(file.path(env$CHECKPOINT_DIR, "fulltext"), recursive = TRUE)
  log <- new.env(parent = emptyenv())
  log$requests <- character(0)
  log$existing <- list()
  request <- function(url) {
    log$requests <- c(log$requests, url)
    for (pattern in names(responses)) if (grepl(pattern, url, fixed = TRUE)) {
      value <- responses[[pattern]]
      if (is.function(value)) return(value(url))
      return(list(status = 200L, text = value, url = url))
    }
    list(status = 404L, text = "{}", url = url)
  }
  # Stand-in for the upstream member walk: honour force/prev exactly as the real one does, "fetch" only what the
  # test configured (existing_rows), and save + return the member checkpoint.
  env$fetch_member_fulltext <- function(bg, urls, force = FALSE, js = FALSE) {
    log$existing[[length(log$existing) + 1L]] <- list(bg = bg, urls = urls, force = force, js = js,
                                                      budget = if (exists("JS_MEMBER_BUDGET", envir = env)) env$JS_MEMBER_BUDGET)
    if (crash) stop("the existing walk crashed")
    ck <- file.path(env$CHECKPOINT_DIR, "fulltext", paste0(bg, ".rds"))
    prev <- if (file.exists(ck) && !force) readRDS(ck) else NULL
    fetched <- if (is.null(existing_rows)) NULL else existing_rows[existing_rows$url %in% urls, , drop = FALSE]
    out <- dplyr::bind_rows(prev, fetched)
    if (nrow(out)) out <- out[!duplicated(out$url, fromLast = TRUE), , drop = FALSE]
    saveRDS(out, ck)
    out
  }
  log$network <- list()
  # Stand-in for the backlog ledger writer: record the call and what the checkpoint held at that moment.
  env$press_member_network_result <- function(result) {
    path <- file.path(env$CHECKPOINT_DIR, "fulltext", paste0(result$bioguide, ".rds"))
    result$checkpoint_urls <- if (file.exists(path)) readRDS(path)$url else character(0)
    log$network[[length(log$network) + 1L]] <- result
    invisible(NULL)
  }
  if (is.null(clock)) env$install_press_host_routes(env, request = request, fetch_page = fetch_page, extract = extract, delay = delay)
  else env$install_press_host_routes(env, request = request, fetch_page = fetch_page, extract = extract, delay = delay, clock = clock)
  list(env = env, log = log, member = function(bg, urls, force = FALSE, js = FALSE)
         env$fetch_member_fulltext(bg, urls, force = force, js = js),
       checkpoint = function(bg) {
         path <- file.path(env$CHECKPOINT_DIR, "fulltext", paste0(bg, ".rds"))
         if (file.exists(path)) readRDS(path) else NULL
       })
}
route_columns <- c("press_route_kind", "press_route_endpoint", "press_route_link", "press_route_body_sha256")
no_route <- function(frame) !any(route_columns %in% names(frame)) ||
  all(is.na(unlist(frame[intersect(route_columns, names(frame))])))

# ---- 1. WordPress custom post type (husted, schmitt, lankford, bluntrochester): body AND date from the REST record
husted <- read_fixture("husted_press_releases_slug.json")
h <- harness(list("husted.senate.gov/wp-json/wp/v2/press_releases?slug=" = husted))
out <- h$member("H001104", HUSTED_URL)
stopifnot(nrow(out) == 1L, identical(out$url, HUSTED_URL),
          identical(out$date_detail, as.Date("2026-09-30")), words(out$body) > 300L,
          startsWith(out$body, "“Let"), !grepl("<p>|&#8217;", out$body),
          identical(out$title_detail, "Democrats block Husted’s bill forcing data centers to pay their own way"),
          identical(out$press_route_kind, "wp_slug"),
          identical(out$press_route_endpoint, h$log$requests[[1L]]),
          grepl(paste0("https://www.husted.senate.gov/wp-json/wp/v2/press_releases?slug=", HUSTED_SLUG),
                out$press_route_endpoint, fixed = TRUE),
          identical(out$press_route_link, paste0(HUSTED_URL, "/")),
          identical(out$press_route_body_sha256, digest::digest(out$body, algo = "sha256", serialize = FALSE)),
          length(h$log$requests) == 1L)
# The body and date satisfy the SAME predicate the backlog uses, so the URL is settled as completed.
stopifnot(isTRUE(h$env$press_cached_body_complete(out)[[1L]]))
# Persisted: the checkpoint now holds the row, and the existing path is not asked for a URL a route already read.
saved <- h$checkpoint("H001104")
stopifnot(identical(saved$url, HUSTED_URL), identical(saved$body, out$body), length(h$log$existing) == 0L)

# ---- 2. WordPress posts (kiggans): same shape, different rest_base, trailing-slash URL
h <- harness(list("kiggans.house.gov/wp-json/wp/v2/posts?slug=" = read_fixture("kiggans_posts_slug.json")))
out <- h$member("K000399", KIGGANS_URL)
stopifnot(nrow(out) == 1L, identical(out$url, KIGGANS_URL), identical(out$date_detail, as.Date("2026-09-14")),
          words(out$body) > 100L, identical(out$press_route_kind, "wp_slug"),
          grepl(paste0("kiggans.house.gov/wp-json/wp/v2/posts?slug=", KIGGANS_SLUG), h$log$requests[[1L]], fixed = TRUE),
          isTRUE(h$env$press_cached_body_complete(out)[[1L]]))

# ---- 3. Literal "nttnt" glued onto old lankford hrefs: exact slug misses, the stripped slug hits; the row keeps the
#         REQUESTED url (the identity the index and ledger use) and records the true link.
h <- harness(list(
  "slug=lankford-subcommittee-examines-judicial-review-in-federal-regulatory-processnttnt" = "[]",
  "slug=lankford-subcommittee-examines-judicial-review-in-federal-regulatory-process&" =
    read_fixture("lankford_press_releases_slug_stripped.json")))
out <- h$member("L000575", NTTNT_URL)
stopifnot(nrow(out) == 1L, identical(out$url, NTTNT_URL), identical(out$date_detail, as.Date("2015-04-28")),
          length(h$log$requests) == 2L, grepl("processnttnt&", h$log$requests[[1L]], fixed = TRUE),
          grepl(paste0(NTTNT_SLUG, "&"), h$log$requests[[2L]], fixed = TRUE),
          grepl(paste0("/", NTTNT_SLUG, "/"), out$press_route_link, fixed = TRUE))

# ---- 4. Truncated slug (trailing "-"): exact misses; search finds EXACTLY ONE slug with that prefix; its record is fetched
search_json <- read_fixture("lankford_press_releases_search.json")
prefix_json <- read_fixture("lankford_press_releases_prefix_match.json")
responses <- list("press_releases?search=" = search_json)
responses[[paste0("slug=", TRUNC_SLUG, "&")]] <- "[]"
responses[[paste0("slug=", PREFIX_SLUG, "&")]] <- prefix_json
h <- harness(responses)
out <- h$member("L000575", TRUNC_URL)
stopifnot(nrow(out) == 1L, identical(out$url, TRUNC_URL), identical(out$press_route_kind, "wp_search_prefix"),
          grepl(PREFIX_SLUG, out$press_route_link, fixed = TRUE), length(h$log$requests) == 3L,
          grepl("search=lankford%20abraham%20accords%20caucus", h$log$requests[[2L]], fixed = TRUE),
          isTRUE(h$env$press_cached_body_complete(out)[[1L]]))
# Every REST request is paced by the delay (the member walk is one worker, so this is the per-host request rate).
paced <- harness(responses, delay = 0.15)
elapsed <- system.time(paced$member("L000575", TRUNC_URL))[["elapsed"]]
stopifnot(length(paced$log$requests) == 3L, elapsed >= 0.4)
# Two prefix matches (ambiguous) or none: no route, the existing path keeps the URL.
two <- sub("]$", paste0(',{"slug":"', TRUNC_SLUG, 'second-match","link":"https://www.lankford.senate.gov/x/"}]'),
           search_json)
stopifnot(!identical(two, search_json))
for (case in list(two, "[]", '[{"slug":"unrelated-post","link":"https://www.lankford.senate.gov/y/"}]')) {
  responses[["press_releases?search="]] <- case
  h <- harness(responses)
  out <- h$member("L000575", TRUNC_URL)
  stopifnot(nrow(out) == 0L, identical(h$log$existing[[1L]]$urls, TRUNC_URL))
}
# The search asks for a full page (per_page=100); a page that comes back full may hide more matches, so it is ambiguous.
page_of <- function(n) as.character(jsonlite::toJSON(c(
  list(list(slug = PREFIX_SLUG, link = paste0("https://www.lankford.senate.gov/news/press-releases/", PREFIX_SLUG, "/"))),
  lapply(seq_len(n - 1L), function(i) list(slug = paste0("unrelated-post-", i), link = "https://www.lankford.senate.gov/x/"))),
  auto_unbox = TRUE))
responses[["press_releases?search="]] <- page_of(99L)
h <- harness(responses)
stopifnot(nrow(h$member("L000575", TRUNC_URL)) == 1L, grepl("per_page=100", h$log$requests[[2L]], fixed = TRUE),
          !grepl("per_page=20", h$log$requests[[2L]], fixed = TRUE))
responses[["press_releases?search="]] <- page_of(100L)
h <- harness(responses)
stopifnot(nrow(h$member("L000575", TRUNC_URL)) == 0L, length(h$log$requests) == 2L)    # no third (record) request
# A complete (non-truncated) slug that simply is not on the site never triggers a search.
h <- harness(list())
invisible(h$member("L000575", "https://www.lankford.senate.gov/news/press-releases/defense-foreign-affairs"))
stopifnot(!any(grepl("search=", h$log$requests, fixed = TRUE)))

# ---- 5. Every rejection falls back to the existing path with the url untouched and no route columns
good <- jsonlite::fromJSON(husted, simplifyVector = FALSE)
variant <- function(edit) {
  record <- good[[1L]]
  record <- edit(record)
  as.character(jsonlite::toJSON(list(record), auto_unbox = TRUE))
}
long_body <- paste(rep("An official body with plenty of words to be usable.", 12L), collapse = " ")
cases <- list(
  empty_array = "[]",
  http_404 = function(url) list(status = 404L, text = '{"code":"rest_no_route"}', url = url),
  not_json = "<html>maintenance</html>",
  other_host = variant(function(r) { r$link <- "https://evil.example.com/media/press-releases/x/"; r }),
  slug_mismatch = variant(function(r) { r$slug <- "a-different-post"; r }),
  short_body = variant(function(r) { r$content$rendered <- "<p>Too short to be a press release body.</p>"; r }),
  future_date = variant(function(r) { r$date <- paste0(Sys.Date() + 30L, "T12:00:00"); r }),
  garbled_date = variant(function(r) { r$date <- "yesterday"; r }),
  missing_content = variant(function(r) { r$content <- NULL; r }),
  redirected_off_host = function(url) list(status = 200L, text = husted, url = "https://other.example.com/wp-json/")
)
for (name in names(cases)) {
  h <- harness(list("husted.senate.gov/wp-json/" = cases[[name]]))
  out <- h$member("H001104", HUSTED_URL)
  stopifnot(nrow(out) == 0L, identical(h$log$existing[[1L]]$urls, HUSTED_URL), is.null(h$checkpoint("H001104")) ||
              !nrow(h$checkpoint("H001104")))
}
# a usable record whose rendered body really is long enough IS accepted (guards the short_body case above)
ok <- variant(function(r) { r$content$rendered <- paste0("<p>", long_body, "</p>"); r })
h <- harness(list("husted.senate.gov/wp-json/" = ok))
stopifnot(nrow(h$member("H001104", HUSTED_URL)) == 1L)

# ---- 6. HTML routes. takano: the retired path prefixes are rewritten to /newsroom/ and fetched with the upstream fetch
takano_html <- read_html(read_fixture("takano_press_release.html"))
takano_slug <- "rep-takano-sen-sanders-reintroduce-32-hour-workweek-act"
fetched <- character(0)
extract_takano <- function(pg, u) {
  text <- squish(html_text2(html_element(pg, "#content")))
  data.frame(url = u, title_detail = squish(html_text2(html_element(pg, "h1"))),
             date_detail = as.Date("2026-09-08"), body = text, stringsAsFactors = FALSE)
}
for (old in c("/media-center/press-releases/", "/news-room/press-releases/",
              "/issues/takano.house.gov/newsroom/press-releases/", "/newsroom/press-releases/")) {
  fetched <- character(0)
  h <- harness(fetch_page = function(u) { fetched <<- c(fetched, u); list(html = takano_html, url_final = u, status = 200L) },
               extract = extract_takano)
  url <- paste0("https://takano.house.gov", old, takano_slug)
  out <- h$member("T000472", url)
  stopifnot(nrow(out) == 1L, identical(out$url, url), identical(fetched, paste0("https://takano.house.gov/newsroom/press-releases/", takano_slug)),
            identical(out$press_route_kind, "html"), identical(out$press_route_endpoint, fetched),
            length(h$log$requests) == 0L, words(out$body) > 100L, identical(out$date_detail, as.Date("2026-09-08")),
            isTRUE(h$env$press_cached_body_complete(out)[[1L]]))
}
# The page must be the one asked for. The final URL must stay on the article's own host; for a rewrite its path (trailing
# slashes aside) must also be the rewritten target's, so a redirect to a home page, a listing or another slug is refused.
takano_old <- paste0("https://takano.house.gov/media-center/press-releases/", takano_slug)
takano_target <- paste0("https://takano.house.gov/newsroom/press-releases/", takano_slug)
via <- function(final) harness(fetch_page = function(u) list(html = takano_html, url_final = final, status = 200L),
                               extract = extract_takano)
stopifnot(nrow(via("https://www.house.gov/")$member("T000472", takano_old)) == 0L,
          nrow(via("https://evil.example.com/newsroom/press-releases/x")$member("T000472", takano_old)) == 0L,
          nrow(via("https://takano.house.gov/")$member("T000472", takano_old)) == 0L,
          nrow(via("https://takano.house.gov/newsroom/press-releases/another-release")$member("T000472", takano_old)) == 0L,
          nrow(via("https://takano.house.gov/newsroom/press-releases")$member("T000472", takano_old)) == 0L,
          nrow(via(NULL)$member("T000472", takano_old)) == 0L)
stopifnot(nrow(via(paste0(takano_target, "/"))$member("T000472", takano_old)) == 1L,      # canonical trailing slash
          nrow(via(paste0(takano_target, "?utm=1"))$member("T000472", takano_old)) == 1L,
          nrow(via(sub("//takano", "//www.takano", takano_target))$member("T000472", takano_old)) == 1L,   # www alias
          nrow(via(toupper(takano_target))$member("T000472", takano_old)) == 1L)
# A page the upstream fetch cannot read (410/404 -> NULL) is a clean fall back.
h <- harness(fetch_page = function(u) NULL, extract = extract_takano)
stopifnot(nrow(h$member("T000472", paste0("https://takano.house.gov/media-center/press-releases/", takano_slug))) == 0L)

# algreen: the upstream extractor takes the whole <body> (nav text, flagged junk) and drops the real container; the
# route keeps the extractor's title/date and swaps in the container text -- but only a row the backlog would settle as
# complete (its 200-character floor) is handed on. The recorded page's container is a 26-word, 166-character link stub:
# NOT complete (lead ruling 2026-10-20), so that URL keeps its existing fate.
algreen_text <- read_fixture("algreen_press_release.html")
algreen_html <- read_html(algreen_text)
algreen_url <- "https://algreen.house.gov/media/press-releases/icymi-austin-american-statesman-article-below-titled-texas-leading-nation"
upstream_extract <- function(pg, u) data.frame(url = u, title_detail = squish(html_text2(html_element(pg, "h1"))),
                                              date_detail = as.Date("2026-10-08"), body = "", stringsAsFactors = FALSE)
h <- harness(fetch_page = function(u) list(html = algreen_html, url_final = u, status = 200L), extract = upstream_extract)
stopifnot(nrow(h$member("G000553", algreen_url)) == 0L, identical(h$log$existing[[1L]]$urls, algreen_url))
# A container that does reach the floor is routed, with the extractor's date and the swapped-in text.
longer <- gsub("speaks for itself.", paste("speaks for itself, and the Congressman asks readers to open the full article",
                                           "and read it through to the end because it documents what happened."),
              algreen_text, fixed = TRUE)
stopifnot(!identical(longer, algreen_text))
longer_html <- read_html(longer)
h <- harness(fetch_page = function(u) list(html = longer_html, url_final = u, status = 200L), extract = upstream_extract)
out <- h$member("G000553", algreen_url)
stopifnot(nrow(out) == 1L, identical(out$url, algreen_url), identical(out$date_detail, as.Date("2026-10-08")),
          startsWith(out$body, "The Austin American-Statesman article below, titled"), nchar(out$body) >= 200L,
          !grepl("Skip to main content|BANNER", out$body), identical(out$press_route_kind, "html"),
          identical(out$press_route_endpoint, algreen_url), isTRUE(h$env$press_cached_body_complete(out)[[1L]]))
# Without a rewrite only the host must hold: another host is refused, a same-host canonical path is accepted.
elsewhere <- harness(fetch_page = function(u) list(html = longer_html, url_final = "https://www.house.gov/", status = 200L),
                     extract = upstream_extract)
stopifnot(nrow(elsewhere$member("G000553", algreen_url)) == 0L)
canonical <- harness(fetch_page = function(u) list(html = longer_html, url_final = paste0(u, "/"), status = 200L),
                     extract = upstream_extract)
stopifnot(nrow(canonical$member("G000553", algreen_url)) == 1L)
# No such container on the page -> no route.
h <- harness(fetch_page = function(u) list(html = takano_html, url_final = u, status = 200L), extract = upstream_extract)
stopifnot(nrow(h$member("G000553", algreen_url)) == 0L)
# A dateless extraction is refused (the backlog would never settle a dateless body).
h <- harness(fetch_page = function(u) list(html = longer_html, url_final = u, status = 200L),
             extract = function(pg, u) { r <- upstream_extract(pg, u); r$date_detail <- as.Date(NA); r })
stopifnot(nrow(h$member("G000553", algreen_url)) == 0L)

# The completeness gate is the backlog's own predicate, called for every routed row: whatever it refuses is not routed
# (a stub that says "no" refuses a perfectly good record; wp and html alike).
h <- harness(list("husted.senate.gov/wp-json/" = husted))
h$env$press_cached_body_complete <- function(frame) rep(FALSE, nrow(frame))
stopifnot(nrow(h$member("H001104", HUSTED_URL)) == 0L)
h <- harness(fetch_page = function(u) list(html = longer_html, url_final = u, status = 200L), extract = upstream_extract)
h$env$press_cached_body_complete <- function(frame) rep(FALSE, nrow(frame))
stopifnot(nrow(h$member("G000553", algreen_url)) == 0L)

# ---- 7. Scope: only table hosts, only real member ids, never a cached/complete URL, never offline
h <- harness(list("wp-json" = husted))
other <- "https://www.other.senate.gov/media/press-releases/anything"
stopifnot(nrow(h$member("O000001", other)) == 0L, length(h$log$requests) == 0L)
stopifnot(nrow(h$member("NEWS_A", HUSTED_URL)) == 0L, length(h$log$requests) == 0L)     # pseudo-member lanes pass through
h <- harness(list("wp-json" = husted))
saved <- data.frame(url = HUSTED_URL, title_detail = "Already here", date_detail = as.Date("2026-09-30"),
                    body = paste(rep("complete body words here", 20L), collapse = " "), stringsAsFactors = FALSE)
saveRDS(saved, file.path(h$env$CHECKPOINT_DIR, "fulltext", "H001104.rds"))
out <- h$member("H001104", HUSTED_URL)
stopifnot(length(h$log$requests) == 0L, identical(out$title_detail, "Already here"), no_route(out))
# An INCOMPLETE cached row (body but no date: exactly what the fallback lane refused) is routed and replaced.
saved$date_detail <- as.Date(NA)
saveRDS(saved, file.path(h$env$CHECKPOINT_DIR, "fulltext", "H001104.rds"))
out <- h$member("H001104", HUSTED_URL)
stopifnot(length(h$log$requests) == 1L, nrow(out) == 1L, identical(out$date_detail, as.Date("2026-09-30")),
          identical(out$press_route_kind, "wp_slug"))
old <- Sys.getenv("CU_PR_OFFLINE", NA)
Sys.setenv(CU_PR_OFFLINE = "1")
h <- harness(list("wp-json" = husted))
stopifnot(nrow(h$member("H001104", HUSTED_URL)) == 0L, length(h$log$requests) == 0L)
if (is.na(old)) Sys.unsetenv("CU_PR_OFFLINE") else Sys.setenv(CU_PR_OFFLINE = old)

# ---- 8. force = TRUE (the --retry-from recovery): the existing path sees ONLY the unrouted urls, with force kept, and the
#         checkpoint ends up holding both; a routed row never depends on the stale checkpoint.
fallback_url <- "https://www.husted.senate.gov/media/press-releases/not-on-the-api"
fallback_row <- data.frame(url = fallback_url, title_detail = "From the existing path", date_detail = as.Date("2026-10-01"),
                           body = paste(rep("existing path body words", 20L), collapse = " "), stringsAsFactors = FALSE)
h <- harness(stats::setNames(list(husted), paste0("slug=", HUSTED_SLUG, "&")), existing_rows = fallback_row)
out <- h$member("H001104", c(HUSTED_URL, fallback_url), force = TRUE)
stopifnot(length(h$log$existing) == 1L, h$log$existing[[1L]]$force, identical(h$log$existing[[1L]]$urls, fallback_url),
          setequal(out$url, c(HUSTED_URL, fallback_url)), setequal(h$checkpoint("H001104")$url, c(HUSTED_URL, fallback_url)),
          identical(out$press_route_kind[out$url == HUSTED_URL], "wp_slug"), is.na(out$press_route_kind[out$url == fallback_url]))
# Everything routed under force: the existing path is not even called, the result is the routed rows.
h <- harness(list("wp-json" = husted))
out <- h$member("H001104", HUSTED_URL, force = TRUE)
stopifnot(length(h$log$existing) == 0L, nrow(out) == 1L, identical(h$checkpoint("H001104")$url, HUSTED_URL))
# Non-force with a mix: the existing walk is handed only what no route read, and the checkpoint keeps both.
h <- harness(stats::setNames(list(husted), paste0("slug=", HUSTED_SLUG, "&")), existing_rows = fallback_row)
out <- h$member("H001104", c(HUSTED_URL, fallback_url))
stopifnot(setequal(out$url, c(HUSTED_URL, fallback_url)), identical(h$log$existing[[1L]]$urls, fallback_url),
          !h$log$existing[[1L]]$force, setequal(h$checkpoint("H001104")$url, c(HUSTED_URL, fallback_url)))
# The routed rows reach the checkpoint BEFORE the existing walk runs: a crash or kill inside it must not lose them, and a
# row already cached stays (prev + routed, deduplicated by url, the routed row winning).
cached_before <- data.frame(url = HUSTED_URL, title_detail = "Old shell", date_detail = as.Date(NA), body = "stub",
                            stringsAsFactors = FALSE)
cached_other <- data.frame(url = "https://www.husted.senate.gov/media/press-releases/earlier-one", title_detail = "Earlier",
                           date_detail = as.Date("2026-09-01"), body = paste(rep("earlier body words", 30L), collapse = " "),
                           stringsAsFactors = FALSE)
h <- harness(stats::setNames(list(husted), paste0("slug=", HUSTED_SLUG, "&")), crash = TRUE)
saveRDS(rbind(cached_before, cached_other), file.path(h$env$CHECKPOINT_DIR, "fulltext", "H001104.rds"))
crashed <- try(h$member("H001104", c(HUSTED_URL, fallback_url)), silent = TRUE)
saved_after <- h$checkpoint("H001104")
stopifnot(inherits(crashed, "try-error"), setequal(saved_after$url, c(HUSTED_URL, cached_other$url)),
          anyDuplicated(saved_after$url) == 0L, saved_after$press_route_kind[saved_after$url == HUSTED_URL] == "wp_slug",
          words(saved_after$body[saved_after$url == HUSTED_URL]) > 300L, identical(h$log$existing[[1L]]$urls, fallback_url))
# Under force the walk comes first (it overwrites the checkpoint) and the merge follows it.
h <- harness(stats::setNames(list(husted), paste0("slug=", HUSTED_SLUG, "&")), crash = TRUE)
crashed <- try(h$member("H001104", c(HUSTED_URL, fallback_url), force = TRUE), silent = TRUE)
stopifnot(inherits(crashed, "try-error"), is.null(h$checkpoint("H001104")))
# The sequential (js) lane has no outer ledger hook for the rows a route read, so the wrapper records them itself:
# attempted = completed = the routed urls, after the checkpoint holds them. The non-js lane is recorded by the backlog
# wrapper from the returned frame, so the route does not double-record it.
h <- harness(stats::setNames(list(husted), paste0("slug=", HUSTED_SLUG, "&")), existing_rows = fallback_row)
invisible(h$member("H001104", c(HUSTED_URL, fallback_url), js = TRUE))
stopifnot(length(h$log$network) == 1L, identical(h$log$network[[1L]]$bioguide, "H001104"),
          identical(h$log$network[[1L]]$requested_urls, HUSTED_URL), identical(h$log$network[[1L]]$attempted_urls, HUSTED_URL),
          identical(h$log$network[[1L]]$completed_urls, HUSTED_URL), length(h$log$network[[1L]]$budget_deferred_urls) == 0L,
          HUSTED_URL %in% h$log$network[[1L]]$checkpoint_urls, identical(h$log$existing[[1L]]$urls, fallback_url),
          isTRUE(h$log$existing[[1L]]$js))
h <- harness(stats::setNames(list(husted), paste0("slug=", HUSTED_SLUG, "&")), existing_rows = fallback_row)
invisible(h$member("H001104", c(HUSTED_URL, fallback_url), js = FALSE))
stopifnot(length(h$log$network) == 0L)
h <- harness(list(), existing_rows = fallback_row)
invisible(h$member("H001104", fallback_url, js = TRUE))      # nothing routed in the js lane: nothing to record
stopifnot(length(h$log$network) == 0L)

# Routing time in the sequential lane is charged to the member's JS_MEMBER_BUDGET: routing stops once it is spent, and the
# existing walk only gets what is left (never less than 1 s, the deadline adapter wants a positive duration), restored after.
urls <- paste0("https://www.husted.senate.gov/media/press-releases/post-", 1:6)
spent <- 0
slow <- function(cost) function(url) { spent <<- spent + cost; list(status = 404L, text = "{}", url = url) }
h <- harness(list("wp-json" = slow(100)), clock = function() spent)
h$env$JS_MEMBER_BUDGET <- 250
seen <- character(0)
out <- withCallingHandlers(h$member("H001104", urls, js = TRUE), message = function(m) {
  seen <<- c(seen, conditionMessage(m)); invokeRestart("muffleMessage") })
stopifnot(length(h$log$requests) == 3L, identical(h$log$existing[[1L]]$urls, urls), h$log$existing[[1L]]$budget == 1,
          h$env$JS_MEMBER_BUDGET == 250, any(grepl("JS_MEMBER_BUDGET", seen, fixed = TRUE)))
spent <- 0
h <- harness(list("wp-json" = slow(10)), clock = function() spent)
h$env$JS_MEMBER_BUDGET <- 600
invisible(h$member("H001104", urls[1:2], js = TRUE))
stopifnot(length(h$log$requests) == 2L, h$log$existing[[1L]]$budget == 580, h$env$JS_MEMBER_BUDGET == 600)
# Not charged outside the js lane, and not when the budget is absent or nothing was eligible.
spent <- 0
h <- harness(list("wp-json" = slow(100)), clock = function() spent)
h$env$JS_MEMBER_BUDGET <- 250
invisible(h$member("H001104", urls, js = FALSE))
stopifnot(length(h$log$requests) == 6L, h$log$existing[[1L]]$budget == 250)
spent <- 0
h <- harness(list("wp-json" = slow(100)), clock = function() spent)      # no JS_MEMBER_BUDGET defined at all
invisible(h$member("H001104", urls, js = TRUE))
stopifnot(length(h$log$requests) == 6L, is.null(h$log$existing[[1L]]$budget))
h <- harness(list(), clock = function() spent)
h$env$JS_MEMBER_BUDGET <- 250
invisible(h$member("O000001", other, js = TRUE))
stopifnot(h$log$existing[[1L]]$budget == 250)

# Two index urls for ONE article (a legacy /news/ or bare /press-releases/ alias of the canonical /media/ page) must not become
# two scored rows: a routed row whose canonical link equals another url's complete row for the same member is dropped (that
# url is left to the existing path), whether the other row is cached, was itself routed, or is earlier in the same batch.
alias_a <- paste0("https://www.husted.senate.gov/news/press-releases/", HUSTED_SLUG)
alias_b <- paste0("https://www.husted.senate.gov/press-releases/", HUSTED_SLUG, "/")
canonical_row <- data.frame(url = HUSTED_URL, title_detail = "Canonical", date_detail = as.Date("2026-09-30"),
                            body = paste(rep("the canonical page body words", 20L), collapse = " "), stringsAsFactors = FALSE)
one_record <- stats::setNames(list(husted), paste0("slug=", HUSTED_SLUG, "&"))
h <- harness(one_record)
saveRDS(canonical_row, file.path(h$env$CHECKPOINT_DIR, "fulltext", "H001104.rds"))
out <- suppressMessages(h$member("H001104", alias_a))
stopifnot(identical(out$url, HUSTED_URL), identical(out$title_detail, "Canonical"), identical(h$log$existing[[1L]]$urls, alias_a),
          identical(h$env$press_route_summary(h$env$CHECKPOINT_DIR)[["husted.senate.gov"]]$routed, 0L))
routed_row <- cbind(canonical_row, press_route_kind = "wp_slug", press_route_endpoint = "x",
                    press_route_link = paste0(HUSTED_URL, "/"), press_route_body_sha256 = "x")
routed_row$url <- "https://www.husted.senate.gov/media/press-releases/earlier-alias"
h <- harness(one_record)
saveRDS(routed_row, file.path(h$env$CHECKPOINT_DIR, "fulltext", "H001104.rds"))
out <- suppressMessages(h$member("H001104", alias_b))        # its link equals what an earlier ROUTED row already holds
stopifnot(identical(out$url, routed_row$url), identical(h$log$existing[[1L]]$urls, alias_b))
h <- harness(one_record)                                      # same batch: the first alias is kept, the second left to the walk
out <- suppressMessages(h$member("H001104", c(alias_a, alias_b)))
stopifnot(identical(out$url, alias_a), identical(h$log$existing[[1L]]$urls, alias_b),
          identical(h$env$press_route_summary(h$env$CHECKPOINT_DIR)[["husted.senate.gov"]]$routed, 1L))
h <- harness(one_record)                                      # an unrelated complete row blocks nothing
other_row <- canonical_row; other_row$url <- "https://www.husted.senate.gov/media/press-releases/something-else"
saveRDS(other_row, file.path(h$env$CHECKPOINT_DIR, "fulltext", "H001104.rds"))
out <- suppressMessages(h$member("H001104", HUSTED_URL))
stopifnot(setequal(out$url, c(HUSTED_URL, other_row$url)))

# A routed body is not replaced by a fresh empty extraction of the same URL, and a prior row of another URL survives.
earlier <- data.frame(url = "https://www.husted.senate.gov/media/press-releases/earlier", title_detail = "Earlier",
                      date_detail = as.Date("2026-09-01"), body = paste(rep("earlier body words", 30L), collapse = " "),
                      stringsAsFactors = FALSE)
empty_again <- data.frame(url = HUSTED_URL, title_detail = "", date_detail = as.Date(NA), body = "", stringsAsFactors = FALSE)
h <- harness(stats::setNames(list(husted), paste0("slug=", HUSTED_SLUG, "&")), existing_rows = rbind(empty_again, fallback_row))
saveRDS(earlier, file.path(h$env$CHECKPOINT_DIR, "fulltext", "H001104.rds"))
out <- h$member("H001104", c(HUSTED_URL, fallback_url))
stopifnot(words(out$body[out$url == HUSTED_URL]) > 300L, "https://www.husted.senate.gov/media/press-releases/earlier" %in% out$url)

# ---- 9. A member whose site keeps failing stops being asked: three consecutive REQUEST errors end the routing.
#         Only the route's own classed request error is absorbed (and its text is reported); anything else is a bug and propagates.
request_error <- function(text) structure(class = c("press_route_request_error", "error", "condition"),
                                          list(message = text, call = NULL))
urls <- paste0("https://www.husted.senate.gov/media/press-releases/post-", 1:6)
h <- harness(list("wp-json" = function(url) stop(request_error("official host route request failed: connection reset"))))
seen <- character(0)
out <- withCallingHandlers(h$member("H001104", urls), message = function(m) {
  seen <<- c(seen, conditionMessage(m)); invokeRestart("muffleMessage") })
stopifnot(nrow(out) == 0L, length(h$log$requests) == 3L, identical(h$log$existing[[1L]]$urls, urls),
          sum(grepl("connection reset", seen, fixed = TRUE)) == 3L, any(grepl("three consecutive", seen, fixed = TRUE)))
# A plain error (a bug, not a failed request) is NOT swallowed.
h <- harness(list("wp-json" = function(url) stop("object 'oops' not found")))
caught <- try(h$member("H001104", urls), silent = TRUE)
stopifnot(inherits(caught, "try-error"), grepl("oops", as.character(caught), fixed = TRUE), length(h$log$existing) == 0L)
# ...and so is a plain error from the page fetch; but the upstream extractor throws on purpose (ambiguous page metadata), and
# the existing walk treats that as "no body", so the route does too.
boom_page <- function(u) stop("fetch bug")
h <- harness(fetch_page = boom_page, extract = extract_takano)
stopifnot(inherits(try(h$member("T000472", paste0("https://takano.house.gov/newsroom/press-releases/", takano_slug)),
                       silent = TRUE), "try-error"))
h <- harness(fetch_page = function(u) list(html = takano_html, url_final = u, status = 200L),
             extract = function(pg, u) stop("ambiguous article:published_time metadata"))
stopifnot(nrow(h$member("T000472", paste0("https://takano.house.gov/newsroom/press-releases/", takano_slug))) == 0L)
# A clean answer resets the streak: the same site with errors on calls 1, 2, 4, 5 and answers between never trips.
calls <- 0L
h <- harness(list("wp-json" = function(url) {
  calls <<- calls + 1L
  if (calls %in% c(1L, 2L, 4L, 5L)) stop(request_error("timeout"))
  list(status = 200L, text = "[]", url = url)
}))
invisible(suppressMessages(h$member("H001104", urls)))
stopifnot(length(h$log$requests) >= 6L)

# A clean 404 is an answer, not an error either: it resets the streak (errors on 1, 2, 4, 5 around a 404 never trip).
calls <- 0L
h <- harness(list("wp-json" = function(url) {
  calls <<- calls + 1L
  if (calls %in% c(1L, 2L, 4L, 5L)) stop(request_error("timeout"))
  list(status = 404L, text = '{"code":"rest_no_route"}', url = url)
}))
invisible(suppressMessages(h$member("H001104", urls)))
stopifnot(length(h$log$requests) == 6L, identical(h$env$press_route_summary(h$env$CHECKPOINT_DIR)[["husted.senate.gov"]]$tripped, 0L))

# ---- 9b. Per-host counts (eligible / attempted / routed / errors / tripped) are kept per member in the checkpoint tree
#          and summed by host for the run receipt; repeated calls for a member accumulate.
h <- harness(list("wp-json" = function(url) stop(request_error("down"))))
invisible(suppressMessages(h$member("H001104", urls)))
tally <- h$env$press_route_summary(h$env$CHECKPOINT_DIR)
stopifnot(identical(names(tally), "husted.senate.gov"),
          identical(tally[["husted.senate.gov"]], list(eligible = 6L, attempted = 3L, routed = 0L, errors = 3L, tripped = 1L)))
h <- harness(stats::setNames(list(husted), paste0("slug=", HUSTED_SLUG, "&")))
invisible(h$member("H001104", c(HUSTED_URL, "https://www.husted.senate.gov/media/press-releases/not-on-the-api")))
invisible(h$member("S001227", "https://www.schmitt.senate.gov/media/press-releases/anything"))
tally <- h$env$press_route_summary(h$env$CHECKPOINT_DIR)
stopifnot(identical(sort(names(tally)), c("husted.senate.gov", "schmitt.senate.gov")),
          identical(tally[["husted.senate.gov"]], list(eligible = 2L, attempted = 2L, routed = 1L, errors = 0L, tripped = 0L)),
          identical(tally[["schmitt.senate.gov"]]$routed, 0L))
invisible(h$member("H001104", "https://www.husted.senate.gov/media/press-releases/also-missing"))   # accumulates
tally <- h$env$press_route_summary(h$env$CHECKPOINT_DIR)
stopifnot(identical(tally[["husted.senate.gov"]], list(eligible = 3L, attempted = 3L, routed = 1L, errors = 0L, tripped = 0L)))
stopifnot(identical(h$env$press_route_summary(tempfile("empty-")), stats::setNames(list(), character(0))))

# ---- 10. Installation is idempotent and the table is well formed
env <- new.env(parent = globalenv())
env$squish <- squish
source(args[[2]], local = env); source(args[[3]], local = env); source(args[[1]], local = env)
env$fetch_member_fulltext <- function(bg, urls, force = FALSE, js = FALSE) NULL
env$install_press_host_routes(env, request = function(url) NULL)
wrapped <- env$fetch_member_fulltext
env$install_press_host_routes(env, request = function(url) NULL)
stopifnot(identical(wrapped, env$fetch_member_fulltext), isTRUE(attr(wrapped, "melange_press_host_routes")))
routes <- env$PRESS_HOST_ROUTES
stopifnot(!anyDuplicated(routes$host), all(routes$kind %in% c("wp", "html")), all(!grepl("^www[.]", routes$host)),
          all(!is.na(routes$rest_base[routes$kind == "wp"])),
          all(!is.na(routes$rewrite_from[routes$kind == "html"]) | !is.na(routes$selector[routes$kind == "html"])),
          all(is.na(routes$rewrite_to) == is.na(routes$rewrite_from)))
routed_hosts <- c("takano.house.gov", "husted.senate.gov", "schmitt.senate.gov", "lankford.senate.gov",
          "algreen.house.gov", "bluntrochester.senate.gov", "kiggans.house.gov")
# babin has no article urls to route; fetterman is not worth a route (75 of its 87 failures are script strings, the rest are
# category pages or dead 404s, and 1 of 12 sampled recovered).
stopifnot(all(routed_hosts %in% routes$host), !("babin.house.gov" %in% routes$host),
          !("fetterman.senate.gov" %in% routes$host), nrow(routes) == length(routed_hosts))
cat("PASS: press host routes (", nrow(routes), " hosts)\n", sep = "")
