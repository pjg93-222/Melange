# Per-host body routes for official sites whose article pages the generic detail fetch cannot turn into a
# dated body. These are the SAME official pages through the endpoint the site itself publishes for them
# (WordPress REST by slug) or at the path the site now serves them from; nothing here changes which sources
# are collected.
#
# Why (2026-10-18 run: 633 `body_unavailable_after_network_retry` rows, 492 of them on nine hosts; live probes
# 2026-10-20, robots.txt read first, collector User-Agent, one request every >= 3 s):
#   * husted, schmitt, lankford, bluntrochester: the page answers 200 but the upstream extractor finds no date
#     (no <time>/meta; its visible-date fallback also returns NA for any "September DD, YYYY", because the
#     "Sept." clean-up in parse_release_date turns "September" into "Sepember"). These members are in the
#     sequential CDX/fallback lane, which refuses a body without a date (fetch_member_fulltext `ok_r`, upstream
#     lines 2099/2145), then spends its 600 s member budget on Wayback lookups. The WordPress `press_releases`
#     record carries the full body AND the publication date.
#   * kiggans: the theme leaves one <div> unclosed inside <header>, so the parser nests <main> under <header> and
#     the upstream chrome-stripping (`header`, `nav`, `aside`, ...) deletes the whole article; the `posts` record is
#     unaffected.
#   * fetterman is deliberately NOT routed: 75 of its 87 failures are script strings (terminal non-articles, see
#     refresh_press_delta.R) and the rest are category pages or dead 404s; 1 of 12 sampled recovered.
#   * takano: the old /media-center/... and /issues/takano.house.gov/newsroom/... paths answer HTTP 410; the same
#     slug is served from /newsroom/press-releases/.
#   * algreen: the page loads, but the upstream extractor takes the whole <body>, its junk filter rejects it, and
#     the real container (.evo-press-release__body) is never used. Most containers are 26-38-word ICYMI link stubs;
#     those below the backlog's 200-character completeness floor are NOT routed (lead ruling 2026-10-20) and keep
#     their existing fate; the ones at or above it are.
# The upstream scraper (Draft Systems/cu_press_release_scraper.R) is outside this repository and is not edited.
#
# Every route is an addition: a URL the route cannot read with a verified, dated, usable body is left to the
# existing path untouched. Rows carry press_route_* columns recording the endpoint that produced the body.

PRESS_HOST_ROUTES <- data.frame(
  host = c("husted.senate.gov", "schmitt.senate.gov", "lankford.senate.gov", "bluntrochester.senate.gov",
           "kiggans.house.gov", "takano.house.gov", "algreen.house.gov"),
  kind = c(rep("wp", 5L), rep("html", 2L)),
  rest_base = c(rep("press_releases", 4L), "posts", NA_character_, NA_character_),
  rewrite_from = c(rep(NA_character_, 5L),
                   "^/(media-center|news-room|issues/takano[.]house[.]gov/newsroom)/press-releases/", NA_character_),
  rewrite_to = c(rep(NA_character_, 5L), "/newsroom/press-releases/", NA_character_),
  selector = c(rep(NA_character_, 6L), ".evo-press-release__body"),
  stringsAsFactors = FALSE
)

press_route_host <- function(url) {
  url <- trimws(as.character(url))
  host <- sub("^www[.]", "", tolower(sub("^https?://([^/:?#]+).*$", "\\1", url, ignore.case = TRUE)))
  ifelse(grepl("^https?://", url, ignore.case = TRUE), host, NA_character_)
}

# WordPress slugs only: lowercase alphanumerics and dashes, a trailing dash allowed (a truncated listing slug).
# The second candidate drops the literal "nttnt" a CDX inventory glued onto old lankford hrefs ("\n\t\n\t").
press_route_slugs <- function(url) {
  path <- sub("[?#].*$", "", sub("^https?://[^/]+", "", trimws(url)))
  slug <- tolower(sub("^.*/", "", sub("/+$", "", path)))
  slugs <- unique(c(slug, sub("nttnt$", "", slug)))
  slugs[grepl("^[a-z0-9_]+(-[a-z0-9_]+)*-?$", slugs)]
}

# The one error the route absorbs: a request that failed at the transport level or came back 429/5xx twice. Anything else
# that goes wrong in here is a bug and must surface.
press_route_request_error <- function(message)
  structure(class = c("press_route_request_error", "error", "condition"), list(message = message, call = NULL))

press_route_default_request <- function(url) {
  # An answer (200, 404, ...) is returned; only a transport failure, 429 or 5xx -- twice -- is an error.
  for (attempt in 1:2) {
    response <- tryCatch(
      httr::GET(url, httr::user_agent(CHROME_UA), httr::timeout(HTTP_TIMEOUT),
                httr::add_headers(Accept = "application/json")),
      error = function(error) NULL)
    status <- if (is.null(response)) NA_integer_ else httr::status_code(response)
    if (!is.na(status) && status != 429L && status < 500L)
      return(list(status = status, text = httr::content(response, as = "text", encoding = "UTF-8"),
                  url = response$url))
    if (attempt < 2L) Sys.sleep(2)
  }
  stop(press_route_request_error(paste0("official host route request failed: ", url, " (",
                                        if (is.na(status)) "network error" else status, ")")))
}

press_route_json <- function(response, origin) {
  if (is.null(response) || !identical(as.integer(response$status), 200L)) return(NULL)
  if (!identical(press_route_host(response$url), press_route_host(origin))) return(NULL)   # never leave the official host
  tryCatch(jsonlite::fromJSON(response$text, simplifyVector = FALSE), error = function(error) NULL)
}

# Every routed row, wp and html, must pass the backlog's own completeness predicate (valid past date, >= 200 characters,
# >= 20 words) so the URL settles as completed instead of being asked for again tomorrow. Whatever it refuses is left
# to the existing path -- including a link-stub body that is real but short.
press_route_row <- function(url, title, date, body, kind, endpoint, link) {
  row <- data.frame(url = url, title_detail = title, date_detail = date, body = body,
                    press_route_kind = kind, press_route_endpoint = endpoint, press_route_link = link,
                    stringsAsFactors = FALSE)
  if (!isTRUE(press_cached_body_complete(row)[[1L]])) return(NULL)
  row$press_route_body_sha256 <- digest::digest(body, algo = "sha256", serialize = FALSE)
  row
}

# One verified row from a WordPress record, or NULL (same host, a real ISO date, a body that survives the row gate).
press_route_wp_row <- function(record, url, endpoint, origin, kind) {
  if (!is.list(record) || length(record$link) != 1L || length(record$date) != 1L ||
      !is.list(record$content) || length(record$content$rendered) != 1L ||
      !identical(press_route_host(as.character(record$link)), press_route_host(origin))) return(NULL)
  text <- substr(as.character(record$date), 1L, 10L)
  date <- suppressWarnings(as.Date(text, format = "%Y-%m-%d"))
  if (is.na(date) || as.character(date) != text || date < as.Date("1990-01-01") || date > Sys.Date()) return(NULL)
  body <- tryCatch(press_wp_plain_text(as.character(record$content$rendered)), error = function(error) "")
  title <- if (is.list(record$title) && length(record$title$rendered) == 1L)
    tryCatch(press_wp_plain_text(as.character(record$title$rendered)), error = function(error) "") else ""
  press_route_row(url, title, date, body, kind, endpoint, as.character(record$link))
}

press_route_wp <- function(url, route, request) {
  origin <- sub("^https?://([^/]+).*$", "https://\\1", trimws(url))
  slugs <- press_route_slugs(url)
  base <- paste0(origin, "/wp-json/wp/v2/", route$rest_base)
  exact <- function(slug, kind) {
    endpoint <- paste0(base, "?slug=", slug, "&_fields=id,date,link,slug,title,content")
    for (record in press_route_json(request(endpoint), origin)) {
      if (!is.list(record) || !identical(record$slug, slug)) next
      row <- press_route_wp_row(record, url, endpoint, origin, kind)
      if (!is.null(row)) return(row)
    }
    NULL
  }
  for (slug in slugs) {
    row <- exact(slug, "wp_slug")
    if (!is.null(row)) return(row)
  }
  # A listing that cut the slug short ("lankford-abraham-accords-caucus-"): accept a search hit only when exactly one
  # post's slug starts with the cut slug (and the result page was not full), the same guess WordPress's own canonical
  # redirect makes.
  if (length(slugs) && grepl("-$", slugs[[1L]])) {
    endpoint <- paste0(base, "?search=", utils::URLencode(gsub("-", " ", sub("-+$", "", slugs[[1L]])), reserved = TRUE),
                       "&per_page=100&_fields=slug,link")
    found <- press_route_json(request(endpoint), origin)
    hits <- character(0)
    # A full page (100) may hide further matches: ambiguous, so no route.
    for (record in if (length(found) < 100L) found) {
      if (is.list(record) && length(record$slug) == 1L && startsWith(as.character(record$slug), slugs[[1L]]) &&
          identical(press_route_host(as.character(record$link)), press_route_host(origin)))
        hits <- c(hits, as.character(record$slug))
    }
    hits <- unique(hits)
    if (length(hits) == 1L) return(exact(hits, "wp_search_prefix"))
  }
  NULL
}

press_route_html <- function(url, route, fetch_page, extract) {
  url <- trimws(url)
  origin <- sub("^(https?://[^/]+).*$", "\\1", url)
  target <- if (is.na(route$rewrite_from)) url else
    paste0(origin, sub(route$rewrite_from, route$rewrite_to, substring(url, nchar(origin) + 1L), perl = TRUE))
  page <- fetch_page(target)
  if (is.null(page)) return(NULL)
  # The page must be the one asked for: it stays on the article's host, and a rewrite must land on the rewritten path
  # (trailing slashes aside), not on a home page, a listing or another release a redirect sent us to.
  final <- if (is.null(page$url_final)) NA_character_ else as.character(page$url_final)
  if (!identical(press_route_host(final), press_route_host(url))) return(NULL)
  if (!is.na(route$rewrite_from)) {
    path_of <- function(u) tolower(sub("/+$", "", sub("[?#].*$", "", sub("^https?://[^/]+", "", u, ignore.case = TRUE))))
    if (!identical(path_of(final), path_of(target))) return(NULL)
  }
  chosen <- NULL
  if (!is.na(route$selector)) {   # read before extract(): the upstream extractor strips page chrome from the tree in place
    node <- rvest::html_element(page$html, route$selector)
    if (inherits(node, "xml_missing")) return(NULL)
    chosen <- squish(rvest::html_text2(node))
  }
  # The upstream extractor throws on purpose (e.g. ambiguous article:published_time metadata) and the existing member walk
  # reads that as "no body" (cu_press_release_scraper.R: tryCatch(extract_release(...), error = function(e) NULL)); so do we.
  row <- tryCatch(extract(page$html, url), error = function(error) NULL)
  if (!is.data.frame(row) || nrow(row) != 1L || is.na(row$date_detail[[1L]])) return(NULL)
  body <- if (is.null(chosen)) as.character(row$body[[1L]]) else chosen
  press_route_row(url, as.character(row$title_detail[[1L]]), as.Date(row$date_detail[[1L]]), body, "html", target,
                  final)
}

press_route_try <- function(url, routes, request, fetch_page, extract) {
  route <- routes[match(press_route_host(url), routes$host), , drop = FALSE]
  if (is.na(route$host)) return(NULL)
  if (route$kind == "wp") press_route_wp(url, route, request) else press_route_html(url, route, fetch_page, extract)
}

press_route_key <- function(url)
  tolower(sub("/+$", "", sub("[?#].*$", "", sub("^https?://(www[.])?", "", trimws(url), ignore.case = TRUE))))

# Two index urls can be one article (a legacy alias of the canonical page). Drop a routed row whose canonical link is the
# canonical url -- or the routed link -- of ANOTHER url's complete row in the member checkpoint, or of an earlier routed row
# in this batch, so one release never becomes two scored rows. The dropped url is left to the existing path.
press_route_drop_aliases <- function(routed, prev) {
  if (!nrow(routed)) return(routed)
  keys <- press_route_key(routed$press_route_link)
  held_url <- held_key <- character(0)
  if (!is.null(prev) && nrow(prev)) {
    complete <- prev[press_cached_body_complete(prev), , drop = FALSE]
    links <- if ("press_route_link" %in% names(complete)) complete$press_route_link else rep(NA_character_, nrow(complete))
    held_url <- rep(complete$url, 2L)
    held_key <- c(press_route_key(complete$url), ifelse(is.na(links), "", press_route_key(links)))
  }
  keep <- vapply(seq_len(nrow(routed)), function(i)
    !(keys[i] %in% held_key[held_url != routed$url[i]]) && !(keys[i] %in% keys[seq_len(i - 1L)]), logical(1))
  routed[keep, , drop = FALSE]
}

press_route_tally_fields <- c("eligible", "attempted", "routed", "errors", "tripped")

# Per-member, per-host counts, one file per member under CHECKPOINT_DIR/host_routes (the member walk runs in future
# workers, so the receipt cannot read them from memory); repeated calls for a member add up.
press_route_record <- function(bg, tally) {
  directory <- file.path(CHECKPOINT_DIR, "host_routes")
  dir.create(directory, recursive = TRUE, showWarnings = FALSE)
  path <- file.path(directory, paste0(bg, ".rds"))
  if (file.exists(path)) tally <- rbind(readRDS(path), tally)
  saveRDS(stats::aggregate(tally[press_route_tally_fields], by = list(host = tally$host), FUN = sum), path)
}

# The run's counts by host, for run_receipt_metrics$host_routes.
press_route_summary <- function(checkpoint_dir = CHECKPOINT_DIR) {
  files <- list.files(file.path(checkpoint_dir, "host_routes"), pattern = "[.]rds$", full.names = TRUE)
  if (!length(files)) return(stats::setNames(list(), character(0)))
  all <- do.call(rbind, lapply(files, readRDS))
  all <- stats::aggregate(all[press_route_tally_fields], by = list(host = all$host), FUN = sum)
  stats::setNames(lapply(seq_len(nrow(all)), function(i) as.list(all[i, press_route_tally_fields])), all$host)
}

# Wraps fetch_member_fulltext(bg, urls, force, js). The existing walk is given only the urls no route could read, so a
# fresh empty extraction can never replace a routed body. Routed rows are written into the member checkpoint before the walk
# (so a crash in it loses nothing, and a later run finds them cached) -- or, under force, merged over what the walk returns.
# A member whose site keeps failing stops being asked after three consecutive request errors.
press_route_member <- function(original, bg, urls, force, js, request, fetch_page, extract, delay, envir, clock,
                               routes = PRESS_HOST_ROUTES) {
  offline <- nzchar(Sys.getenv("CU_PR_OFFLINE")) || nzchar(Sys.getenv("CU_PR_SKIP_FETCH"))
  if (offline || length(bg) != 1L || !grepl("^[A-Z][0-9]{6}$", bg)) return(original(bg, urls, force = force, js = js))
  ck <- file.path(CHECKPOINT_DIR, "fulltext", paste0(bg, ".rds"))
  prev <- if (!force && file.exists(ck)) readRDS(ck) else NULL
  if (!is.null(prev) && !"url" %in% names(prev)) prev <- NULL
  done <- if (is.null(prev)) character(0) else prev$url[press_cached_body_complete(prev)]
  todo <- setdiff(urls, done)
  todo <- todo[!is.na(match(press_route_host(todo), routes$host))]
  rows <- list()
  streak <- 0L
  # In the sequential (js) lane the member has a wall-clock budget (JS_MEMBER_BUDGET); routing spends from it. Stop routing
  # once it is gone, and give the existing walk only what is left (never under 1 s: the deadline adapter wants a positive one).
  budget <- if (isTRUE(js) && exists("JS_MEMBER_BUDGET", envir = envir, inherits = TRUE))
    get("JS_MEMBER_BUDGET", envir = envir, inherits = TRUE) else Inf
  started <- clock()
  hosts <- unique(press_route_host(todo))
  tally <- data.frame(host = hosts, stringsAsFactors = FALSE)
  for (field in press_route_tally_fields) tally[[field]] <- integer(length(hosts))
  tally$eligible <- as.integer(table(factor(press_route_host(todo), levels = tally$host)))
  paced <- function(endpoint) { Sys.sleep(delay); request(endpoint) }   # one member is one worker: this IS the per-host rate
  for (url in todo) {
    if (clock() - started > budget) {
      message("    [host route] ", bg, ": JS_MEMBER_BUDGET spent on routing; the existing path takes the rest.")
      break
    }
    at <- match(press_route_host(url), tally$host)
    tally$attempted[at] <- tally$attempted[at] + 1L
    failed <- FALSE
    row <- tryCatch(press_route_try(url, routes, paced, fetch_page, extract),
                    press_route_request_error = function(error) {
                      failed <<- TRUE
                      message("    [host route] ", bg, ": ", conditionMessage(error))
                      NULL
                    })
    if (failed) tally$errors[at] <- tally$errors[at] + 1L
    streak <- if (failed) streak + 1L else 0L
    if (streak >= 3L) {
      tally$tripped[at] <- 1L
      message("    [host route] ", bg, ": three consecutive request errors; the existing path takes the rest.")
      break
    }
    if (!is.null(row)) rows[[length(rows) + 1L]] <- row
  }
  routed <- dplyr::bind_rows(rows)
  before <- nrow(routed)
  routed <- press_route_drop_aliases(routed, prev)
  if (nrow(routed) < before)
    message("    [host route] ", bg, ": ", before - nrow(routed), " routed row(s) dropped as aliases of an article already held.")
  routed_urls <- if (nrow(routed)) routed$url else character(0)
  tally$routed <- as.integer(table(factor(press_route_host(routed_urls), levels = tally$host)))
  if (nrow(tally)) press_route_record(bg, tally)
  walk <- function(unrouted) {
    if (is.finite(budget) && length(todo)) {
      assign("JS_MEMBER_BUDGET", max(1, budget - (clock() - started)), envir = envir)
      on.exit(assign("JS_MEMBER_BUDGET", budget, envir = envir))
    }
    original(bg, unrouted, force = force, js = js)
  }
  if (!nrow(routed)) return(walk(urls))
  message("    [host route] ", bg, ": ", nrow(routed), " of ", length(todo),
          " body URL(s) read through the official endpoint.")
  rest <- setdiff(urls, routed$url)
  newest_wins <- function(frame) frame[!duplicated(frame$url, fromLast = TRUE), , drop = FALSE]
  # The sequential (js) lane is recorded in the backlog ledger by the deadline adapter, which only ever sees `rest`;
  # the non-js lane by the backlog wrapper from the frame returned here. So the routed urls are recorded here for js only,
  # once the checkpoint holds them (the ledger reads it): attempted = completed = the routed urls.
  record <- function() if (isTRUE(js)) press_member_network_result(list(
    bioguide = bg, requested_urls = routed$url, attempted_urls = routed$url, completed_urls = routed$url,
    budget_deferred_urls = character(0)))
  if (!force) {
    merged <- newest_wins(dplyr::bind_rows(prev, routed))
    saveRDS(merged, ck)   # BEFORE the walk: a crash or kill inside it must not lose bodies already read
    record()
    return(if (length(rest)) walk(rest) else merged)
  }
  # force: the walk ignores and overwrites the checkpoint, so the routed rows are merged in after it.
  merged <- newest_wins(dplyr::bind_rows(if (length(rest)) walk(rest), routed))
  saveRDS(merged, ck)
  record()
  merged
}

install_press_host_routes <- function(envir = .GlobalEnv, request = press_route_default_request,
                                      fetch_page = function(u) fetch_html(u),
                                      extract = function(pg, u) extract_release(pg, u), delay = 0.5,
                                      clock = function() unname(proc.time()[["elapsed"]])) {
  original <- get("fetch_member_fulltext", envir = envir, inherits = FALSE)
  if (isTRUE(attr(original, "melange_press_host_routes"))) return(invisible(NULL))
  force(request); force(fetch_page); force(extract); force(delay); force(clock); force(envir)
  member <- function(bg, urls, force = FALSE, js = FALSE)
    press_route_member(original, bg, urls, force, js, request, fetch_page, extract, delay, envir, clock)
  attr(member, "melange_press_host_routes") <- TRUE
  assign("fetch_member_fulltext", member, envir = envir)
  invisible(NULL)
}
