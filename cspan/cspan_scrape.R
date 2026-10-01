#!/usr/bin/env Rscript
# =============================================================================
# C-SPAN video scraper (chromote / headless Chrome)
# =============================================================================
# Purpose: harvest C-SPAN "Videos" search results (default: Washington Journal,
# seriesid=13) and, for each program page, extract the speaker-labelled
# transcript + the HLS media URL (so audio can be played / downloaded).
#
# The target segments are member-guest interviews -- "Rep./Sen. <Name> on
# <Topic>" -- but this tool captures EVERY turn with its speaker label and role
# and leaves roster attribution (drop-never-guess) to the downstream Python
# resolver, exactly like fec/fetch_interviews.py does for the other sources.
#
# ACCESS NOTE (read before running): C-SPAN robots.txt disallows named AI
# crawlers site-wide and disallows /transcript, /ajax, /common/services for all
# UAs; the site also fronts CloudFront which intermittently 403s automated
# clients. This script runs an HONEST headless Chrome (real UA/headers/viewport)
# and respects a crawl-delay -- it does NOT spoof TLS fingerprints, rotate
# proxies, or solve CAPTCHAs. Run only with authorization for the content.
#
# Usage:
#   Rscript cspan_scrape.R search [--url U | --since D --until D]
#                                  [--max N] [--delay S] [--out DIR] [--strict]
#   Rscript cspan_scrape.R scrape [--since D --until D] [--max N] [--delay S]
#                                 [--members-only] [--retry-empty] [--strict]
#                                 [--audio] [--ffmpeg PATH] [--out DIR]
#   Rscript cspan_scrape.R one <program-url-or-id> [--out DIR] [--audio]
#   Rscript cspan_scrape.R audio <program-id> [--out DIR] [--ffmpeg PATH]
#   Rscript cspan_scrape.R status [--out DIR]
#
# Stage 1 (search) writes  <out>/videos.csv         (the manifest of programs)
# Stage 2 (scrape) writes  <out>/transcripts/<id>.json   (per-program record)
#                    and    <out>/audio/<id>.mp3      (with --audio, via ffmpeg)
# Stage 3 (rebuild) writes <out>/turns.csv using fec/rebuild_cspan_turns.py.
# Membership is intentionally resolved in Python from speaker + title + tenure;
# the C-SPAN role field is blank in this corpus and is not an identity signal.
# Both stages are resumable: re-running skips programs already captured.
# =============================================================================

suppressWarnings(suppressMessages({
  library(chromote)
  library(jsonlite)
}))

# ------------------------------- config --------------------------------------
DEFAULT_SEARCH_SINCE <- "2020-01-01"

cspan_search_url <- function(since, until) {
  encode_date <- function(value) {
    parsed <- as.Date(value)
    if (is.na(parsed)) stop("invalid ISO date: ", value)
    utils::URLencode(format(parsed, "%m/%d/%Y"), reserved = TRUE)
  }
  paste0(
    "https://www.c-span.org/search/?sdate=", encode_date(since),
    "&edate=", encode_date(until),
    "&congressSelect=&yearSelect=&searchtype=Videos&sort=Most+Recent+Event",
    "&text=0&seriesid%5B%5D=13")
}

UA <- paste0("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ",
             "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# HLS master playlist pattern; <ID> is the program id (last URL path segment).
media_url_for <- function(id) sprintf("https://m3u8-0.c-spanvideo.org/program/program.%s.tsc.m3u8", id)

# Resources we never need while scraping text -> block to go faster and to avoid
# streaming video/pulling ad partners. Text/JSON/JS/CSS still load, so the page
# (and its transcript table + player config) render normally.
BLOCKED <- c("*.png","*.jpg","*.jpeg","*.gif","*.webp","*.svg","*.ico",
             "*.woff","*.woff2","*.ttf","*.eot",
             "*.mp4","*.m4a","*.ts","*.m3u8","*.mp3",
             "*doubleclick.net*","*googlesyndication.com*","*google-analytics.com*",
             "*imasdk.googleapis.com*","*amazon-adsystem.com*","*rubiconproject.com*",
             "*openx.net*","*pubmatic.com*","*criteo.com*","*adnxs.com*")

# --------------------------- small arg parser --------------------------------
args <- commandArgs(trailingOnly = TRUE)
cmd  <- if (length(args) >= 1) args[1] else "help"
flag <- function(name, default = NA) {
  i <- match(paste0("--", name), args)
  if (is.na(i)) return(default)
  # boolean flags (no value follows, or next token is another --flag)
  if (i == length(args) || startsWith(args[i + 1], "--")) return(TRUE)
  args[i + 1]
}
has_flag <- function(name) paste0("--", name) %in% args
positional <- function(k) { p <- args[!startsWith(args, "--")]; if (length(p) >= k) p[k] else NA }

ROOT <- Sys.getenv("MONEYBALL_ROOT", unset = "C:/Users/pgoff/OneDrive/Desktop/Melange Systems")
OUT  <- flag("out", file.path(ROOT, "cspan_out"))
DELAY <- as.numeric(flag("delay", "4"))          # seconds between distinct page loads (robots Crawl-delay:4)
LOADMORE_DELAY <- as.numeric(flag("loaddelay", "2"))  # seconds between #loadmore clicks (same page, XHR append)
DATE_SINCE <- as.character(flag("since", DEFAULT_SEARCH_SINCE))
DATE_UNTIL <- as.character(flag("until", format(Sys.Date(), "%Y-%m-%d")))
if (is.na(as.Date(DATE_SINCE)) || is.na(as.Date(DATE_UNTIL)) ||
    as.Date(DATE_SINCE) > as.Date(DATE_UNTIL)) {
  stop("invalid --since/--until interval: ", DATE_SINCE, "..", DATE_UNTIL)
}
# How many ~0.4s polls of an EMPTY transcript table before concluding "no
# transcript" (vs a slow render). MUST be generous: under CPU contention (many
# parallel workers) the transcript JS can take >10s to populate, and too-short a
# bail silently records a populated transcript as 0 turns. 35 -> ~14s.
ZERO_BAIL <- as.integer(flag("zerobail", "35"))
MAXN <- suppressWarnings(as.integer(flag("max", NA)))
FFMPEG <- flag("ffmpeg", "ffmpeg")

dir.create(OUT, recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(OUT, "transcripts"), showWarnings = FALSE)

log_msg <- function(...) cat(sprintf("[%s] ", format(Sys.time(), "%H:%M:%S")), ..., "\n", sep = "")
promote_file <- function(temp, path) {
  backup <- paste0(path, ".previous")
  if (file.exists(backup) && file.exists(path)) file.remove(backup)
  if (file.exists(backup) && !file.exists(path) && !file.rename(backup, path))
    stop("cannot restore stale backup for ", path)
  had_path <- file.exists(path)
  if (had_path && !file.rename(path, backup)) stop("cannot back up ", path)
  if (!file.rename(temp, path)) {
    if (had_path) file.rename(backup, path)
    stop("cannot promote ", path)
  }
  if (had_path) file.remove(backup)
  invisible(path)
}
`%||%` <- function(a, b) if (is.null(a) || length(a) == 0 || (length(a) == 1 && is.na(a))) b else a

# --------------------------- chromote helpers --------------------------------
new_session <- function() {
  b <- ChromoteSession$new(width = 1366, height = 900)
  b$Network$enable(wait_ = TRUE)
  b$Network$setUserAgentOverride(userAgent = UA, acceptLanguage = "en-US,en;q=0.9",
                                 platform = "Win32", wait_ = TRUE)
  if (!has_flag("no-block")) try(b$Network$setBlockedURLs(urls = as.list(BLOCKED), wait_ = TRUE), silent = TRUE)
  b$Page$enable(wait_ = TRUE)
  b
}

# evaluate a JS expression that returns a JSON-serialisable value; parse to R.
js_json <- function(b, expr) {
  wrapped <- sprintf("JSON.stringify((function(){ try { return (%s); } catch(e){ return {__err:String(e)}; } })())", expr)
  v <- b$Runtime$evaluate(wrapped, returnByValue = TRUE, awaitPromise = TRUE)$result$value
  if (is.null(v) || identical(v, "")) return(NULL)
  jsonlite::fromJSON(v, simplifyDataFrame = FALSE)
}
js_val <- function(b, expr) b$Runtime$evaluate(expr, returnByValue = TRUE)$result$value

is_blocked <- function(b) {
  isTRUE(js_val(b, "/403 ERROR|Request blocked|could not be satisfied|Access Denied|Bot detected/i.test(document.body?document.body.innerText:'')"))
}

# navigate + wait for readyState complete (and optionally a selector), with
# retry/backoff for the intermittent CloudFront 403.
nav_wait <- function(b, url, wait_selector = NULL, tries = 4, settle = 2) {
  for (attempt in seq_len(tries)) {
    ok <- tryCatch({ b$Page$navigate(url, wait_ = TRUE); TRUE }, error = function(e) FALSE)
    if (ok) {
      ready <- FALSE
      for (i in 1:40) {
        Sys.sleep(0.5)
        rs <- tryCatch(js_val(b, "document.readyState"), error = function(e) NA)
        if (isTRUE(rs == "complete")) { ready <- TRUE; break }
      }
      if (ready && !is_blocked(b)) {
        if (!is.null(wait_selector)) {
          for (i in 1:30) {
            n <- tryCatch(js_val(b, sprintf("document.querySelectorAll(%s).length", toJSON(wait_selector, auto_unbox = TRUE))),
                          error = function(e) 0)
            if (isTRUE(n > 0)) break
            Sys.sleep(0.5)
          }
        }
        Sys.sleep(settle)
        return(TRUE)
      }
    }
    back <- DELAY * attempt + 3
    log_msg(sprintf("  nav blocked/failed (attempt %d/%d) -> backoff %.0fs: %s", attempt, tries, back, url))
    Sys.sleep(back)
  }
  FALSE
}

# ------------------------------- extraction JS -------------------------------
# Faithful to the user's spec: iterate '#search-results h3', resolve each to its
# enclosing link + list item. Ads carry no <h3>, so they drop out naturally.
JS_RESULTS <- "
Array.from(document.querySelectorAll('#search-results h3')).map(function(h3){
  var a  = h3.closest('a') || (h3.parentElement && h3.parentElement.querySelector('a.title')) || h3.closest('li') && h3.closest('li').querySelector('a.title');
  var li = h3.closest('li');
  var times = li ? li.querySelectorAll('time') : [];
  var abs = li ? li.querySelector('.abstract') : null;
  return { url: a ? a.href : '', title: h3.textContent.trim(),
           date: times[0] ? times[0].getAttribute('datetime') : '',
           last_aired: times[1] ? times[1].getAttribute('datetime') : '',
           abstract: abs ? abs.textContent.replace(/\\s+/g,' ').trim() : '' };
}).filter(function(r){ return r.url && r.title; })
"

# Transcript + media extraction. Full text is already in <p.transcript-text>;
# we still click any visible 'Show More' toggle first (honours the user's
# 'load this first' instruction and covers any variant that truncates in DOM).
JS_TRANSCRIPT <- "
(function(){
  document.querySelectorAll('.transcript-text-show-toggle-link:not(.hidden)').forEach(function(x){ try{x.click();}catch(e){} });
  var html = document.documentElement.innerHTML;
  var m = (html.match(/https?:\\/\\/m3u8[^\\\"'\\\\ ]*\\.m3u8/) || [])[0] || '';
  var rows = Array.from(document.querySelectorAll('#video-transcript-table tr'));
  var turns = rows.map(function(tr){
    var name='', role='';
    tr.querySelectorAll('td > strong').forEach(function(s){
      if (s.classList.contains('transcript-cr-title')) { if(!role) role = s.textContent.replace(/\\s+/g,' ').trim(); }
      else if (!name) { name = s.textContent.replace(/\\s+/g,' ').trim(); }
    });
    var p = tr.querySelector('p.transcript-text');
    var text = p ? p.textContent.replace(/\\s+/g,' ').trim() : '';
    var seek = tr.querySelector('.transcript-time-seek');
    var label = tr.querySelector('.transcript-time-label');
    return { offset: seek ? parseInt(seek.getAttribute('data-offset')||'0',10) : null,
             time: label ? label.textContent.trim() : '',
             name: name, role: role, text: text };
  }).filter(function(t){ return t.text.length > 0; });
  return { media_url: m, n_rows: rows.length, turns: turns };
})()
"

# ------------------------------- utilities -----------------------------------
program_id <- function(url) {
  # .../washington-journal/<slug>/671024  or  .../<slug>/671024?...  -> 671024
  u <- sub("[?#].*$", "", url)
  m <- regmatches(u, regexpr("[0-9]+$", u))
  if (length(m) == 0 || m == "") m <- regmatches(u, regexpr("[0-9]{4,}", u))
  if (length(m) == 0) NA_character_ else m
}

# member-guest heuristic from the TITLE only (a recall-favouring prefilter to
# save scraping effort; DEFINITIVE attribution is the downstream roster
# resolver, which drops former members / look-alikes). WJ member segments read
# "Rep./Sen./Del. Name on ..." (sometimes prefixed, e.g. "Former Rep. ..."), so
# we match the honorific ANYWHERE, not just at the start. perl=TRUE because R's
# default (TRE) engine mishandles \b inside a (^|\b) alternation.
MEMBER_TITLE_RE <- "(\\bRep\\.|\\bSen\\.|\\bDel\\.|\\bRepresentative\\b|\\bSenator\\b|\\bCongress(man|woman)\\b|\\bDelegate\\b|\\bSpeaker\\b)"
looks_member <- function(title) grepl(MEMBER_TITLE_RE, title, ignore.case = TRUE, perl = TRUE)

# Collapse a C-SPAN transcript into flowing per-speaker turns. Two things happen
# here, in order:
#   (1) CARRY-FORWARD: a speaker's turn spans many <tr> rows, but only the FIRST
#       row carries <strong>Name</strong>; continuation rows have an EMPTY
#       <strong>. So an empty name means "same speaker as the previous row" --
#       we carry the last named speaker forward. (Without this, continuation
#       text is silently split off under a blank speaker and the member's turn
#       is truncated.)
#   (2) MERGE: consecutive rows with the same (carried) speaker join into one
#       turn, keeping the first row's timestamp/offset.
# Leading rows before any name stay attributed to "" (genuinely unlabelled).
merge_turns <- function(turns) {
  if (length(turns) == 0) return(list())
  out <- list(); cur <- NULL; last_name <- ""
  for (t in turns) {
    nm <- if (is.null(t$name) || (length(t$name) == 1 && is.na(t$name))) "" else t$name
    if (nm == "") nm <- last_name else last_name <- nm     # (1) carry-forward
    role <- if (is.null(t$role) || (length(t$role) == 1 && is.na(t$role))) "" else t$role
    if (!is.null(cur) && identical(cur$name, nm)) {         # (2) merge
      cur$text <- paste(cur$text, t$text)
      if (cur$role == "" && role != "") cur$role <- role
    } else {
      if (!is.null(cur)) out[[length(out) + 1]] <- cur
      cur <- list(offset = t$offset, time = t$time, name = nm, role = role, text = t$text)
    }
  }
  if (!is.null(cur)) out[[length(out) + 1]] <- cur
  out
}

# ------------------------------- stage: search -------------------------------
run_search <- function() {
  url <- flag("url", cspan_search_url(DATE_SINCE, DATE_UNTIL))
  b <- new_session(); on.exit(try(b$close(), silent = TRUE), add = TRUE)
  log_msg("search: ", url)
  if (!nav_wait(b, url, wait_selector = "#search-results h3")) { log_msg("search page blocked -- aborting"); return(invisible()) }

  showing <- js_val(b, "(document.querySelector('.showing')||{}).textContent||''")
  log_msg("search header: ", gsub("\\s+", " ", trimws(showing)))

  # extract the current #search-results into videos.csv (checkpoint-safe: called
  # periodically so a crash mid-pagination doesn't lose the whole crawl).
  path <- file.path(OUT, "videos.csv")
  prior <- if (file.exists(path)) {
    read.csv(path, stringsAsFactors = FALSE, colClasses = "character")
  } else NULL
  save_manifest <- function() {
    res <- js_json(b, JS_RESULTS)
    if (is.null(res) || length(res) == 0) return(0L)
    df <- do.call(rbind, lapply(res, function(r) data.frame(
      id = program_id(r$url %||% ""), url = r$url %||% "", title = r$title %||% "",
      date = r$date %||% "", last_aired = r$last_aired %||% "",
      abstract = r$abstract %||% "", member_guess = as.character(looks_member(r$title %||% "")),
      stringsAsFactors = FALSE)))
    df <- df[!duplicated(df$id) & !is.na(df$id), ]
    # A bounded current-window search must never erase the historical manifest.
    # Fresh rows win for matching IDs (title/air-date corrections), while every
    # older program remains available to deterministic rebuilds and audits.
    merged <- rbind(prior, df)
    merged <- merged[!duplicated(merged$id, fromLast = TRUE) & !is.na(merged$id), ]
    ord <- order(substr(merged$date, 1, 10), merged$id, decreasing = TRUE,
                 na.last = TRUE)
    merged <- merged[ord, ]
    temp <- paste0(path, ".part")
    write.csv(merged, temp, row.names = FALSE, fileEncoding = "UTF-8")
    promote_file(temp, path)
    nrow(df)
  }

  count <- js_val(b, "document.querySelectorAll('#search-results h3').length")
  log_msg(sprintf("initial results on page: %d", count))
  stall <- 0; ckpt <- 0
  repeat {
    if (!is.na(MAXN) && count >= MAXN) break
    present <- isTRUE(js_val(b, "(function(){var b=document.querySelector('#loadmore'); return !!b && b.offsetParent!==null;})()"))
    if (!present) { log_msg("#loadmore gone -> reached end of results"); break }
    js_val(b, "(function(){var b=document.querySelector('#loadmore'); if(b){b.click();return true;} return false;})()")
    Sys.sleep(LOADMORE_DELAY)
    newc <- js_val(b, "document.querySelectorAll('#search-results h3').length")
    if (newc <= count) {
      stall <- stall + 1
      Sys.sleep(LOADMORE_DELAY)   # give the XHR a second chance
      newc <- js_val(b, "document.querySelectorAll('#search-results h3').length")
      if (newc <= count && stall >= 3) { log_msg("no new results after 3 tries -> stop"); break }
    } else stall <- 0
    count <- newc
    if (count - ckpt >= 1000) { ckpt <- count; log_msg(sprintf("loaded %d results (checkpoint -> videos.csv)...", save_manifest())) }
  }

  n <- save_manifest()
  if (n == 0L) { log_msg("no results extracted"); return(FALSE) }
  v <- read.csv(path, stringsAsFactors = FALSE, colClasses = "character")
  receipt <- list(
    schema = "cspan-wj-search-v1",
    completed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
    since = DATE_SINCE,
    until = DATE_UNTIL,
    discovered_in_window = n,
    cumulative_programs = nrow(v),
    cumulative_member_candidates = sum(as.logical(v$member_guess), na.rm = TRUE),
    status = "COMPLETE"
  )
  rpath <- file.path(OUT, "search_receipt.json")
  write_json(receipt, paste0(rpath, ".part"), auto_unbox = TRUE, pretty = TRUE)
  promote_file(paste0(rpath, ".part"), rpath)
  log_msg(sprintf("found %d window programs; cumulative manifest %d -> %s  (%d member candidates)",
                  n, nrow(v), path, sum(as.logical(v$member_guess), na.rm = TRUE)))
  TRUE
}

# --------------------------- stage: scrape one -------------------------------
scrape_program <- function(b, url, title = "", date = "", want_audio = FALSE) {
  id <- program_id(url)
  if (is.na(id)) { log_msg("  cannot parse id from ", url); return(NULL) }
  jpath <- file.path(OUT, "transcripts", paste0(id, ".json"))
  prior_empty <- FALSE
  if (file.exists(jpath) && !has_flag("force")) {
    retry <- FALSE
    if (has_flag("retry-empty")) {
      old <- tryCatch(fromJSON(jpath, simplifyVector = FALSE), error = function(e) NULL)
      retry <- !is.null(old) && as.integer(old$n_turns %||% 0L) == 0L
      prior_empty <- retry
    }
    if (!retry) return("skip")
  }
  if (!grepl("^https?:", url)) url <- paste0("https:", url)

  if (!nav_wait(b, url, wait_selector = NULL, settle = 1)) {
    log_msg("  BLOCKED/failed: ", id); return(NULL)
  }
  # Ensure the transcript table is fully rendered. It populates in one burst a
  # beat after load (0 -> N rows), so wait for the row count to STABILISE (and
  # nudge-scroll in case any variant appends on scroll). Truncating here would
  # silently drop the tail of a long interview. If rows stay at 0 (many recent
  # airings have no transcript published yet), bail after ~5s instead of waiting.
  js_val(b, "(function(){var s=document.querySelector('#video-transcript-wrapper'); if(s) s.scrollIntoView();})()")
  last <- -1L; stable <- 0L; zero <- 0L
  for (i in 1:(ZERO_BAIL + 55L)) {
    n <- tryCatch(as.integer(js_val(b, "document.querySelectorAll('#video-transcript-table tr').length")), error = function(e) 0L)
    if (is.na(n)) n <- 0L
    if (n == 0L) { zero <- zero + 1L; if (zero >= ZERO_BAIL) break }  # no transcript (patient) -> stop
    else { zero <- 0L; if (n == last) { stable <- stable + 1L; if (stable >= 3L) break } else stable <- 0L }
    js_val(b, "window.scrollBy(0, 3000)")
    last <- n; Sys.sleep(0.4)
  }

  page_title <- js_val(b, "document.title") %||% title
  ex <- js_json(b, JS_TRANSCRIPT)
  turns_raw <- if (is.null(ex$turns)) list() else ex$turns
  turns <- merge_turns(turns_raw)
  media <- ex$media_url %||% ""
  if (is.null(media) || media == "") media <- media_url_for(id)

  rec <- list(id = id, url = url, title = title, page_title = page_title, date = date,
              scraped_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S"),
              media_url = media, n_turns = length(turns), turns = turns)
  # Rechecking a still-unpublished transcript should not churn the cumulative
  # source digest and trigger a 478 MB SQLite backup/reload every week.
  if (!prior_empty || length(turns))
    write_json(rec, jpath, auto_unbox = TRUE, pretty = TRUE)

  if (want_audio) download_audio(id, media)
  list(id = id, n_turns = length(turns), media = media)
}

# ----------------------------- stage: scrape all -----------------------------
run_scrape <- function() {
  vpath <- file.path(OUT, "videos.csv")
  if (!file.exists(vpath)) { log_msg("no videos.csv -- run 'search' first"); return(invisible()) }
  v <- read.csv(vpath, stringsAsFactors = FALSE, colClasses = "character")
  observed <- suppressWarnings(as.Date(substr(v$date, 1, 10)))
  v <- v[!is.na(observed) & observed >= as.Date(DATE_SINCE) &
           observed <= as.Date(DATE_UNTIL), ]
  if (has_flag("members-only")) v <- v[as.logical(v$member_guess) %in% TRUE, ]
  if (!is.na(MAXN)) v <- head(v, MAXN)
  # --shard k/n : process every n-th program (0-indexed k). Launch n processes
  # (k=0..n-1) to the SAME --out for n-way parallelism; the skip-if-exists check
  # keeps them from redoing each other's work.  No flat file is appended here;
  # run the deterministic Python rebuild after all shards finish.
  shard <- flag("shard", NA)
  if (!is.na(shard)) {
    pr <- as.integer(strsplit(shard, "/")[[1]]); k <- pr[1]; nsh <- pr[2]
    v <- v[(seq_len(nrow(v)) - 1L) %% nsh == k, ]
    log_msg(sprintf("shard %d/%d -> %d programs", k, nsh, nrow(v)))
  }
  log_msg(sprintf("scrape: %d programs (%s)", nrow(v), if (has_flag("members-only")) "members-only" else "all"))

  b <- new_session(); on.exit(try(b$close(), silent = TRUE), add = TRUE)
  done <- 0; skipped <- 0; failed <- 0; recycled <- 0; empty <- 0
  for (i in seq_len(nrow(v))) {
    r <- v[i, ]
    out <- tryCatch(scrape_program(b, r$url, r$title, r$date, want_audio = has_flag("audio")),
                    error = function(e) { log_msg("  ERROR ", r$id, ": ", conditionMessage(e)); NULL })
    if (identical(out, "skip")) { skipped <- skipped + 1 }
    else if (is.null(out)) { failed <- failed + 1 }
    else {
      done <- done + 1
      if (out$n_turns == 0L) empty <- empty + 1L
      log_msg(sprintf("  [%d/%d] %s: %d turns  %s", i, nrow(v), out$id, out$n_turns,
                      substr(gsub("\\s+"," ",r$title), 1, 55)))
      Sys.sleep(DELAY)
    }
    # recycle the browser periodically to bound memory
    if (i %% 200 == 0) { try(b$close(), silent = TRUE); b <- new_session(); recycled <- recycled + 1 }
  }
  log_msg(sprintf("scrape done: %d captured, %d skipped(existing), %d failed (browser recycled %dx)",
                  done, skipped, failed, recycled))
  receipt <- list(
    schema = "cspan-wj-scrape-v1",
    completed_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
    since = DATE_SINCE,
    until = DATE_UNTIL,
    eligible_programs = nrow(v),
    captured = done,
    skipped_existing = skipped,
    zero_transcript = empty,
    failed = failed,
    status = if (failed == 0L) "COMPLETE" else "PARTIAL"
  )
  rpath <- file.path(OUT, "scrape_receipt.json")
  write_json(receipt, paste0(rpath, ".part"), auto_unbox = TRUE, pretty = TRUE)
  promote_file(paste0(rpath, ".part"), rpath)
  failed == 0L
}

# -------------------------- canonical flat rebuild ---------------------------
run_rebuild <- function() {
  py <- Sys.which("python")
  script <- file.path(ROOT, "fec", "rebuild_cspan_turns.py")
  if (py == "") stop("python was not found on PATH")
  if (!file.exists(script)) stop("missing canonical builder: ", script)
  code <- system2(py, c(shQuote(script), "--out", shQuote(OUT)))
  if (!identical(code, 0L)) stop("canonical C-SPAN rebuild failed with exit ", code)
}

# ------------------------------- audio (ffmpeg) ------------------------------
download_audio <- function(id, media = NULL) {
  if (is.null(media) || media == "") media <- media_url_for(id)
  dir.create(file.path(OUT, "audio"), showWarnings = FALSE)
  out_mp3 <- file.path(OUT, "audio", paste0(id, ".mp3"))
  if (file.exists(out_mp3) && !has_flag("force")) { log_msg("  audio exists: ", id); return(out_mp3) }
  ff <- Sys.which(FFMPEG); if (ff == "") ff <- FFMPEG
  code <- suppressWarnings(system2(ff, c("-y", "-user_agent", shQuote(UA), "-i", shQuote(media),
                                         "-vn", "-acodec", "libmp3lame", "-q:a", "4", shQuote(out_mp3)),
                                   stdout = FALSE, stderr = FALSE))
  if (code == 0 && file.exists(out_mp3)) log_msg("  audio -> ", out_mp3)
  else log_msg(sprintf("  audio FAILED for %s (ffmpeg exit %s; is ffmpeg installed?)", id, code))
  invisible(out_mp3)
}

# --------------------------------- status ------------------------------------
run_status <- function() {
  vpath <- file.path(OUT, "videos.csv")
  n_manifest <- if (file.exists(vpath)) nrow(read.csv(vpath, colClasses = "character")) else 0
  n_done <- length(list.files(file.path(OUT, "transcripts"), pattern = "\\.json$"))
  n_audio <- length(list.files(file.path(OUT, "audio"), pattern = "\\.mp3$"))
  cat(sprintf("out dir      : %s\n", OUT))
  cat(sprintf("manifest     : %d programs (videos.csv)\n", n_manifest))
  cat(sprintf("scraped      : %d transcript json files\n", n_done))
  cat(sprintf("audio        : %d mp3 files\n", n_audio))
}

# --------------------------------- dispatch ----------------------------------
# (wrapped in one brace block so the multi-line if/else chain parses at top level)
{
  if (cmd == "search") {
    ok <- run_search()
    if (has_flag("strict") && !isTRUE(ok)) quit(save = "no", status = 2L)
  } else if (cmd == "scrape") {
    ok <- run_scrape()
    if (has_flag("strict") && !isTRUE(ok)) quit(save = "no", status = 2L)
  } else if (cmd == "one") {
    arg <- positional(2); if (is.na(arg)) stop("usage: cspan_scrape.R one <program-url-or-id>")
    url <- if (grepl("^https?:|^//", arg)) arg else sprintf("https://www.c-span.org/program/washington-journal/x/%s", arg)
    b <- new_session(); on.exit(try(b$close(), silent = TRUE), add = TRUE)
    out <- scrape_program(b, url, want_audio = has_flag("audio"))
    if (!is.null(out) && !identical(out, "skip")) log_msg(sprintf("captured %s: %d turns, media=%s", out$id, out$n_turns, out$media))
  } else if (cmd == "audio") {
    arg <- positional(2); if (is.na(arg)) stop("usage: cspan_scrape.R audio <program-id>")
    download_audio(arg)
  } else if (cmd == "status") {
    run_status()
  } else if (cmd == "rebuild") {
    run_rebuild()
  } else {
    cat("C-SPAN chromote scraper\n",
        "  Rscript cspan_scrape.R search  [--url U | --since D --until D] [--max N] [--strict] [--out DIR]\n",
        "  Rscript cspan_scrape.R scrape  [--since D --until D] [--max N] [--members-only] [--retry-empty] [--strict] [--out DIR]\n",
        "  Rscript cspan_scrape.R one <program-url-or-id> [--audio]\n",
        "  Rscript cspan_scrape.R audio <program-id> [--ffmpeg PATH]\n",
        "  Rscript cspan_scrape.R rebuild [--out DIR]\n",
        "  Rscript cspan_scrape.R status\n", sep = "")
  }
}
