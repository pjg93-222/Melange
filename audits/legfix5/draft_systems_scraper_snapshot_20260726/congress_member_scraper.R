# Overview: congress.gov advanced-search scraper. A real Chrome window clears
# Cloudflare once; a cookie-replay httr fast path then fetches every page in
# parallel (browser fallback for anything re-challenged).
#
# DRIVEN BY congress_search_urls.R: the scraper loops every *_url_parts template
# defined there (one "section" each). Within a section it sweeps all members for
# THREE sponsorship roles in turn -- sponsor -> original cosponsor -> cosponsor
# -- by swapping the switch condition's field token; then it advances to the
# next section. Each scraped bill row is tagged with its Section + Role. The
# per-bill EXTRACTION (parse_result_node / parse_single_bill_page) is unchanged.
#
# Two outputs:
#   * Moneyball_Legislative_Score_Raw_*.xlsx -> one sheet, "Legislative Score -
#     Raw", replicating the attached workbook's layout (143 cols: Name,
#     District/State, then 17 sections x 8 metrics, then committee/leadership).
#   * congress_bills_archive_*.xlsx -> every individual bill (All Bills sheet +
#     one sheet per section).
#
# DECAY: a per-session decay (DECAY_PER_CONGRESS = 0.8) weights the three COUNT
# metrics by how recent the bill's congress is (119th x1, 118th x0.8, 117th
# x0.64); averages and success rates stay un-decayed.
#
# The advanced-search queries are EXACT known-good URLs stored as vectors of
# short chunks and paste0()'d back together -- so no single source line is long
# enough for the RStudio console to truncate, AND we never rebuild them from
# JSON. Only the member name (a __MEMBER__ placeholder) and the role field token
# vary.
#
# SINGLE-RESULT LAYOUT: when a member matches exactly ONE bill, congress.gov
# redirects straight to that bill's detail page instead of showing a results
# list, so the results-list selectors find nothing and the bill used to be
# dropped. parse_single_bill_page() now recovers that bill from the detail-page
# layout via alternative selectors (and grabs its summary on the spot, saving a
# Stage-2 fetch).

library(clipr)
library(rvest)
library(dplyr)
library(chromote)
library(writexl)
library(future)
library(future.apply)
library(progressr)
library(httr)      # fast cookie-replay HTTP path (no browser render)

# ---------------------------------------------------------------
# LINKED to congress_search_urls.R + per-session decay  (NEW)
# ---------------------------------------------------------------
# This scraper is driven by congress_search_urls.R: every *_url_parts template
# defined there is scraped, for three sponsorship ROLES each (sponsor ->
# original cosponsor -> cosponsor), looping section by section. Nothing about
# the per-bill EXTRACTION changes -- only which URL is fetched, and how the
# resulting rows are tagged (Section + Role) and aggregated.
# Self-locate: make THIS script's folder the working directory. Everything here
# uses paths relative to the script (congress_search_urls.R, the cookie/roster
# caches, the output workbooks), but RStudio's working dir is often elsewhere
# (e.g. ~/Documents). Detect the script folder whether it was Source'd, run via
# Rscript, or run in the RStudio editor, and setwd() to it.
get_script_dir <- function() {
  # (a) Rscript: --file=<path>
  args <- commandArgs(trailingOnly = FALSE)
  fa <- grep("^--file=", args, value = TRUE)
  if (length(fa) > 0) {
    p <- tryCatch(normalizePath(sub("^--file=", "", fa[1]), mustWork = FALSE),
                  error = function(e) "")
    if (nzchar(p)) return(dirname(p))
  }
  # (b) source()'d, incl. the RStudio "Source" button: an `ofile` is set in a
  #     parent frame of the source() call.
  for (i in rev(seq_len(sys.nframe()))) {
    of <- tryCatch(get("ofile", envir = sys.frame(i), inherits = FALSE),
                   error = function(e) NULL)
    if (is.character(of) && length(of) == 1 && nzchar(of)) {
      return(dirname(normalizePath(of, mustWork = FALSE)))
    }
  }
  # (c) RStudio, code run interactively (no source): the active editor document.
  if (requireNamespace("rstudioapi", quietly = TRUE) &&
      isTRUE(tryCatch(rstudioapi::isAvailable(), error = function(e) FALSE))) {
    p <- tryCatch(rstudioapi::getSourceEditorContext()$path, error = function(e) "")
    if (length(p) == 1 && nzchar(p)) return(dirname(normalizePath(p, mustWork = FALSE)))
  }
  NA_character_
}

.script_dir <- get_script_dir()
if (!is.na(.script_dir) && dir.exists(.script_dir)) {
  setwd(.script_dir)
  message("Working directory set to script folder: ", .script_dir)
}

SEARCH_URLS_FILE <- "congress_search_urls.R"
if (!file.exists(SEARCH_URLS_FILE)) {
  stop("congress_search_urls.R not found. Looked in: ", normalizePath(getwd()),
       if (!is.na(.script_dir)) paste0("  (auto-detected script folder: ", .script_dir, ")")
       else "  (could not auto-detect this script's folder)",
       ".\nOpen this script from the folder that holds congress_search_urls.R, ",
       "or run setwd(\"<that folder>\") then re-source.")
}
source(SEARCH_URLS_FILE, local = FALSE)  # defines the 17 *_url_parts vectors

# Per-session decay: a bill in the NEWEST congress (119th) counts at full
# weight; each older congress is multiplied by DECAY_PER_CONGRESS once more
# (118th x 0.8, 117th x 0.8^2, ...). Per your spec this weights ONLY the three
# COUNT columns (sponsor / original-cosponsor / cosponsor); the averages and
# success-rate columns stay un-decayed.
NEWEST_CONGRESS    <- 119L
DECAY_PER_CONGRESS <- 0.8
congress_decay_weight <- function(congress) {
  cg  <- suppressWarnings(as.integer(congress))
  age <- NEWEST_CONGRESS - cg
  age[is.na(age) | age < 0] <- 0L        # NA / newer-than-newest -> full weight
  DECAY_PER_CONGRESS ^ age
}

# ---------------------------------------------------------------
# Checkpoint / resume  (NEW): don't re-scrape what's already done
# ---------------------------------------------------------------
# The scrape is 17 sections x 3 roles = 51 passes over the whole roster. After
# EACH pass finishes it is saved to CHECKPOINT_FILE, so an interrupted/crashed
# run (or just re-sourcing) picks up where it left off instead of starting over.
# Once summaries are fetched too, the finished Bills table is cached, so a later
# re-run skips straight to writing the workbooks.
#   RESUME <- TRUE   reuse the checkpoint if present (default).
#   RESUME <- FALSE  ignore it and scrape everything fresh (overwrites it).
# Delete CHECKPOINT_FILE (or set RESUME <- FALSE) for a clean run -- also do this
# if you change the roster, the templates, or the decay factor.
RESUME          <- TRUE
CHECKPOINT_FILE <- "congress_scrape_checkpoint.rds"

# Force-re-scrape specific passes even when cached / scrape_complete is locked,
# e.g.  RESCRAPE_PASSES <- c("member_business_lending||sponsor"). The cached
# version is KEPT for comparison, so the no-regression guard still applies (a
# flaky/fallback undercount will NOT overwrite it; only a clean, >= result does).
# Reset to character(0) when done so normal runs reuse the locked scrape.
RESCRAPE_PASSES <- character(0)

# ---- STAGE TOGGLES (the slow optional stages) ----
# Stage 2 = bill-summary fetch (this flag). Stage 3 = cosponsor network
# (RUN_COSPONSOR_EDGES, set in the Stage 3 section near the bottom of the file).
# Set either FALSE to run just the scrape + the Legislative Score / interaction
# database output (no summary fetch, no cosponsor fetch).
FETCH_SUMMARIES <- FALSE   # Stage 2 OFF

new_checkpoint  <- function() list(passes = list(), scrape_complete = FALSE,
                                   summaries_done = FALSE, bills = NULL,
                                   saved_at = Sys.time())
pass_key        <- function(section_key, role) paste0(section_key, "||", role)

load_checkpoint <- function() {
  if (RESUME && file.exists(CHECKPOINT_FILE)) {
    ck <- tryCatch(readRDS(CHECKPOINT_FILE), error = function(e) NULL)
    if (!is.null(ck) && is.list(ck) && !is.null(ck$passes)) {
      message("Resuming from ", CHECKPOINT_FILE, ": ", length(ck$passes),
              "/51 pass(es) done",
              if (isTRUE(ck$summaries_done)) " + summaries cached" else "",
              ". (set RESUME <- FALSE or delete the file for a fresh run)")
      return(ck)
    }
  }
  new_checkpoint()
}

save_checkpoint <- function(ck) {
  ck$saved_at <- Sys.time()
  ok <- tryCatch({ saveRDS(ck, CHECKPOINT_FILE); TRUE },
                 error = function(e) { message("  (checkpoint save FAILED: ",
                                               conditionMessage(e), ")"); FALSE })
  invisible(ck)
}

# ---------------------------------------------------------------
# Browser / anti-bot configuration
# ---------------------------------------------------------------
# Cloudflare serves headless Chrome a "Just a moment..." interstitial. What
# defeats it: (1) a REAL, headful Chrome window (the JS challenge solves
# itself), and (2) a SINGLE consistent user-agent matching the actual engine.
#
# BROWSER_MODE:
#   "remote"   -> attach to a real Chrome launched via launch_scrape_chrome()
#                 (recommended; reliably clears Cloudflare).
#   "headless" -> default chromote headless Chrome + stealth patches + UA
#                 override (faster, but Cloudflare may still challenge it).
BROWSER_MODE <- "remote"
REMOTE_HOST  <- "127.0.0.1"
REMOTE_PORT  <- 9222L

# One consistent UA matching the installed Chrome (v148 on this machine).
CHROME_UA <- "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"

# Chromote per-command timeout (seconds). The default (~30s) is too short when a
# page is slow or sitting behind a Cloudflare challenge, which surfaces as
# "timed out waiting for response to command Page.navigate". We bump this AND
# issue navigate asynchronously (wait_ = FALSE) so a slow load no longer throws.
CHROMOTE_TIMEOUT <- 120

# TRUE if a Chrome DevTools endpoint is already listening on the port.
chrome_debugger_up <- function(host = REMOTE_HOST, port = REMOTE_PORT) {
  url_str <- sprintf("http://%s:%d/json/version", host, port)
  tryCatch({
    con <- url(url_str)
    on.exit(close(con), add = TRUE)
    line <- suppressWarnings(readLines(con, n = 1, warn = FALSE))
    length(line) > 0
  }, error = function(e) FALSE)
}

# Find chrome.exe (env override, then the usual install locations).
find_chrome_exe <- function() {
  cand <- c(
    Sys.getenv("CHROMOTE_CHROME", ""),
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    file.path(Sys.getenv("LOCALAPPDATA"), "Google/Chrome/Application/chrome.exe")
  )
  cand <- cand[nzchar(cand)]
  hit <- cand[file.exists(cand)]
  if (length(hit) == 0) {
    stop("chrome.exe not found. Set CHROMOTE_CHROME to its full path, e.g.\n",
         "  Sys.setenv(CHROMOTE_CHROME = \"C:/Path/To/chrome.exe\")")
  }
  hit[1]
}

# Launch a real, headful Chrome with remote debugging enabled, then WAIT until
# the DevTools port is actually listening (system2 returns instantly, so a bare
# launch + immediate attach races and fails). Idempotent: if the port is already
# up it just returns. Leave the window open; solve any one-time captcha by hand.
launch_scrape_chrome <- function(port = REMOTE_PORT, wait = 30) {
  if (chrome_debugger_up(port = port)) {
    message("Chrome DevTools already listening on port ", port, " -- reusing it.")
    return(invisible(TRUE))
  }
  chrome_exe <- find_chrome_exe()
  profile <- file.path(Sys.getenv("USERPROFILE"), "chrome_scrape_profile")
  args <- c(
    sprintf("--remote-debugging-port=%d", port),
    sprintf("--user-data-dir=%s", profile),
    "--no-first-run", "--no-default-browser-check"
  )
  system2(chrome_exe, args = args, wait = FALSE, stdout = FALSE, stderr = FALSE)

  waited <- 0
  while (!chrome_debugger_up(port = port) && waited < wait) {
    Sys.sleep(1); waited <- waited + 1
  }
  if (!chrome_debugger_up(port = port)) {
    stop("Launched Chrome but port ", port, " never came up after ", wait, "s.\n",
         "Most likely a leftover chrome.exe intercepted the launch. Fix:\n",
         "  1. Close ALL Chrome windows.\n",
         "  2. In Task Manager, End any remaining 'chrome.exe' / 'Google Chrome' tasks.\n",
         "  3. Run launch_scrape_chrome() again.")
  }
  message("Chrome DevTools up on port ", port, ". Leave that window open.")
  invisible(TRUE)
}

# Point chromote's default session at the right browser for the chosen mode.
# In remote mode this AUTO-LAUNCHES Chrome if nothing is listening yet.
init_browser <- function(auto_launch = TRUE) {
  if (identical(BROWSER_MODE, "remote")) {
    if (!chrome_debugger_up() && auto_launch) {
      message("No Chrome debugger on ", REMOTE_HOST, ":", REMOTE_PORT,
              " -- launching a real Chrome window...")
      launch_scrape_chrome()
    }
    ok <- tryCatch({
      set_default_chromote_object(
        Chromote$new(browser = ChromeRemote$new(host = REMOTE_HOST, port = REMOTE_PORT))
      )
      TRUE
    }, error = function(e) { message("Remote attach failed: ", e$message); FALSE })
    if (!ok) {
      stop("Could not attach to Chrome on ", REMOTE_HOST, ":", REMOTE_PORT,
           ". Run launch_scrape_chrome() and confirm the window stays open.")
    }
  }
  # In "headless" mode chromote spawns its own default browser.
  invisible(TRUE)
}

# Inject stealth patches + (headless only) the consistent UA override.
apply_stealth <- function(session) {
  js <- paste(
    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});",
    "window.chrome={runtime:{}};",
    "Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});",
    "Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});",
    sep = ""
  )
  tryCatch(session$Page$addScriptToEvaluateOnNewDocument(source = js),
           error = function(e) NULL)
  if (identical(BROWSER_MODE, "headless")) {
    tryCatch(session$Network$setUserAgentOverride(userAgent = CHROME_UA),
             error = function(e) NULL)
  }
  invisible(session)
}

# ---------------------------------------------------------------
# FAST PATH: cookie-replay HTTP (the speed knob)
# ---------------------------------------------------------------
# FETCH_MODE:
#   "http"    -> clear Cloudflare ONCE in the real browser, harvest its cookies +
#                user-agent, then fetch every page with plain parallel httr GETs
#                (no rendering). 10-30x faster. Falls back to the browser for any
#                page Cloudflare re-challenges (cf_clearance can be TLS-bound --
#                run validate_http() once to see which path you're on).
#   "browser" -> the one-tab-at-a-time chromote path (robust, slow).
FETCH_MODE   <- "http"
HTTP_WORKERS <- 6L           # parallel httr workers; keep modest to stay polite
HTTP_PAUSE   <- c(0.3, 1.2)  # random per-request pause range (seconds), politeness
# Per-request resilience (covers Stage 1 search, Stage 2 summaries, Stage 3
# cosponsors -- ALL go through fetch_html_http). On a timeout / stalled
# connection / 429 / 5xx / empty body we back off and RETRY rather than dropping
# the page. 403 Cloudflare challenges are NOT retried here (they need a cookie
# re-harvest, handled upstream).
HTTP_TIMEOUT_S    <- 45L   # per-request timeout, seconds
HTTP_MAX_TRIES    <- 3L    # total attempts before giving up
HTTP_RETRY_BASE_S <- 3     # exp backoff base: ~3s, 6s (+jitter), capped 60s; honors Retry-After
COOKIE_RDS   <- "cf_session.rds"   # harvested cookies + UA cached here

# Stability guard: after the HTTP rounds (incl. cookie re-harvest), if MORE than
# this many members are STILL challenged, congress.gov is unstable / rate-
# limiting. In that state the per-member browser fallback both hammers the site
# AND silently records challenged members as "0 bills" (baking bad data into the
# pass, which then gets marked done). So instead we ABORT the run WITHOUT saving
# the pass -- the checkpoint keeps the completed passes, and a later re-run redoes
# this pass cleanly once the site is healthy. Raise it to allow a bigger browser
# fallback; the healthy steady state leaves only a handful challenged.
MAX_CHALLENGED_BEFORE_ABORT <- 40L

# Harvested Cloudflare session lives here once captured: list(cookie=, ua=).
CF_SESSION <- NULL

# Plan: parallel for the HTTP path, sequential (shared browser) for the browser path.
if (identical(FETCH_MODE, "http")) {
  plan(multisession, workers = HTTP_WORKERS)
} else {
  plan(sequential)
}

# Harvest cf_clearance (+ all congress.gov cookies) and the UA from the real
# browser after it has cleared Cloudflare. Run once up front; re-run to refresh
# an expired cookie. Returns/sets CF_SESSION and caches it to COOKIE_RDS.
harvest_cf_session <- function(probe_member = members[1]) {
  init_browser()
  session <- tryCatch(ChromoteSession$new(), error = function(e) {
    warning("harvest: could not create a Chrome session: ", conditionMessage(e)); NULL
  })
  if (is.null(session)) return(invisible(NULL))
  on.exit(try(session$close(), silent = TRUE), add = TRUE)
  session$default_timeout <- CHROMOTE_TIMEOUT
  apply_stealth(session)

  url <- build_member_url(probe_member, 1, 250)
  # wait_ = FALSE: fire navigate async and let the polling below detect when the
  # page is actually ready. A blocking navigate can throw "timed out waiting for
  # response to command Page.navigate" while Cloudflare holds the response.
  nav_ok <- tryCatch({ session$Page$navigate(url, wait_ = FALSE); TRUE },
                     error = function(e) {
                       warning("harvest: Page.navigate failed: ", conditionMessage(e)); FALSE
                     })
  if (!nav_ok) return(invisible(NULL))
  Sys.sleep(3)
  # Wait for the challenge to clear (solve by hand in the window if prompted).
  if (!wait_past_cloudflare(session, timeout = 90)) {
    warning("Cloudflare not cleared during harvest -- solve it by hand in the ",
            "Chrome window, then re-run harvest_cf_session().")
  }
  wait_for_results(session)

  ua <- tryCatch(session$Runtime$evaluate("navigator.userAgent")$result$value,
                 error = function(e) CHROME_UA)
  cookies <- tryCatch(session$Network$getAllCookies()$cookies, error = function(e) list())
  keep <- Filter(function(ck) grepl("congress\\.gov", ck$domain), cookies)
  cookie_str <- paste(vapply(keep, function(ck) paste0(ck$name, "=", ck$value), ""),
                      collapse = "; ")
  if (!nzchar(cookie_str)) {
    warning("No congress.gov cookies captured -- harvest likely failed.")
  }

  CF_SESSION <<- list(cookie = cookie_str, ua = ua, harvested = Sys.time())
  saveRDS(CF_SESSION, COOKIE_RDS)
  message("Harvested ", length(keep), " congress.gov cookies",
          if (any(vapply(keep, function(ck) identical(ck$name, "cf_clearance"), TRUE)))
            " (incl. cf_clearance)" else " (no cf_clearance!)", ".")
  invisible(CF_SESSION)
}

# Load a previously cached session from disk into CF_SESSION (if present).
load_cf_session <- function() {
  if (is.null(CF_SESSION) && file.exists(COOKIE_RDS)) {
    CF_SESSION <<- readRDS(COOKIE_RDS)
    message("Loaded cached Cloudflare session from ", COOKIE_RDS, ".")
  }
  invisible(CF_SESSION)
}

# Does this HTML look like a Cloudflare challenge rather than real results?
is_challenge_html <- function(html_str) {
  grepl("just a moment|checking your browser|attention required|verifying you are human|cf-browser-verification|challenge-platform",
        html_str, ignore.case = TRUE)
}

# Fetch a page with plain httr using the harvested cookies + UA. Returns a parsed
# html_document, the string "CHALLENGED" if Cloudflare blocked it, or NULL on a
# hard error.
fetch_html_http <- function(url, label = "", cf = CF_SESSION) {
  if (is.null(cf) || !nzchar(cf$cookie)) return("CHALLENGED")
  backoff <- function(attempt) Sys.sleep(min(60, HTTP_RETRY_BASE_S * 2^(attempt - 1)) + runif(1, 0, 1.5))

  for (attempt in seq_len(HTTP_MAX_TRIES)) {
    resp <- tryCatch(
      httr::GET(
        url,
        httr::add_headers(
          `User-Agent`      = cf$ua,
          `Cookie`          = cf$cookie,
          `Accept`          = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          `Accept-Language` = "en-US,en;q=0.9",
          `Referer`         = "https://www.congress.gov/"
        ),
        httr::timeout(HTTP_TIMEOUT_S)
      ),
      error = function(e) e   # timeout / stalled connection / DNS / reset
    )

    # --- transient transport error: back off + retry ---
    if (inherits(resp, "error")) {
      if (attempt < HTTP_MAX_TRIES) {
        message("  [http] ", label, " try ", attempt, "/", HTTP_MAX_TRIES,
                " transport error (", conditionMessage(resp), ") -> retry")
        backoff(attempt); next
      }
      message("  [http] error ", label, " (gave up after ", attempt, "): ", conditionMessage(resp))
      return(NULL)
    }

    code     <- httr::status_code(resp)
    html_str <- httr::content(resp, as = "text", encoding = "UTF-8")

    # --- rate-limited / server error: honor Retry-After, else back off; retry ---
    if (code == 429 || code >= 500) {
      if (attempt < HTTP_MAX_TRIES) {
        ra <- suppressWarnings(as.numeric(httr::headers(resp)[["retry-after"]]))
        if (length(ra) == 1 && !is.na(ra) && ra > 0) Sys.sleep(min(ra, 60)) else backoff(attempt)
        message("  [http] ", label, " HTTP ", code, " (try ", attempt, "/", HTTP_MAX_TRIES, ") -> retry")
        next
      }
      return("CHALLENGED")   # exhausted -> let the round/re-harvest machinery handle it
    }

    # --- 403 / Cloudflare challenge: don't retry here (needs a fresh cookie) ---
    if (code >= 400 || is_challenge_html(html_str)) return("CHALLENGED")

    # --- empty body (partial/stalled): retry ---
    if (is.null(html_str) || !nzchar(html_str)) {
      if (attempt < HTTP_MAX_TRIES) { backoff(attempt); next }
      message("  [http] empty response ", label); return(NULL)
    }

    return(tryCatch(read_html(html_str), error = function(e) {
      message("  [http] parse error ", label, ": ", e$message); NULL
    }))
  }
  NULL
}

# Dispatcher used by the scrapers: HTTP fast path with optional browser fallback,
# or the pure browser path, depending on FETCH_MODE. Returns parsed HTML or NULL.
# allow_browser_fallback MUST be FALSE inside parallel workers (the browser is
# only reachable from the main process); the driver retries challenged members in
# the main process with allow_browser_fallback = TRUE.
fetch_page <- function(url, label, allow_browser_fallback = FALSE, cf = CF_SESSION) {
  if (identical(FETCH_MODE, "http")) {
    res <- fetch_html_http(url, label, cf = cf)
    if (inherits(res, "xml_document")) return(res)
    if (allow_browser_fallback) {
      message("  [http] ", label, " failed (",
              if (identical(res, "CHALLENGED")) "challenged" else "error",
              ") -> browser fallback")
      return(fetch_rendered_html(url, label))
    }
    return(NULL)  # NULL signals "challenged/failed" to the caller
  }
  fetch_rendered_html(url, label)
}

# ---------------------------------------------------------------
# Roster: current members of the 119th Congress (no API key needed).
# Source: theunitedstates.io congress-legislators (well-maintained, not behind
# Cloudflare).
#
# congress.gov names members by their OFFICIAL bioguide name -- the CSV's
# full_name column -- NOT by the CSV nickname. Bioguide has "James P. McGovern"
# even though the nickname is "Jim", so a "Jim McGovern" sponsor search returns
# nothing; meanwhile official names that ARE nicknames ("Andy Barr", "Chuck
# Edwards", "Nikki Budzinski") stay as-is. Display name = first non-initial
# given-name token of full_name + last_name (drops middle initials, suffixes,
# and quoted/parenthesised nicknames). This corrected 33 miscalled members vs
# the old nickname-first logic (Jim McGovern, Bernie Sanders, Chuck Schumer,
# Bobby Scott, Buddy Carter, ...).
# ---------------------------------------------------------------

# Manual fixes for any member congress.gov spells differently than the roster
# CSV: c("constructed name" = "name congress.gov expects"). Applied last.
MEMBER_NAME_OVERRIDES <- c()

# Build congress.gov's display name from one roster row (first non-initial
# given-name token of full_name + last_name). Factored out so the roster AND the
# District/State lookup below construct IDENTICAL names -> the join always hits.
construct_display_name <- function(off, fallback_first, last) {
  src <- if (!is.na(off) && nzchar(off)) off else paste(fallback_first, last)
  src <- gsub('"[^"]*"', " ", src)          # drop "Buddy"-style quoted nicknames
  src <- gsub("\\([^)]*\\)", " ", src)      # drop (Nick) parentheticals
  tok <- gsub(",$", "", strsplit(trimws(src), "\\s+")[[1]])
  tok <- tok[!grepl("^[A-Za-z]\\.?$", tok)]             # single-letter initials
  tok <- tok[!grepl("^(Jr|Sr|II|III|IV|V)\\.?$", tok)]  # suffixes
  last_toks <- tolower(strsplit(last, "\\s+")[[1]])
  tok <- tok[!(tolower(tok) %in% last_toks)]            # surname tokens
  first <- if (length(tok) > 0) tok[1] else trimws(fallback_first)
  trimws(paste(first, last))
}

get_roster_119 <- function(types = c("rep", "sen")) {
  csv_url <- "https://unitedstates.github.io/congress-legislators/legislators-current.csv"
  df <- tryCatch(
    read.csv(url(csv_url), stringsAsFactors = FALSE, encoding = "UTF-8"),
    error = function(e) { message("Roster download failed: ", e$message); NULL }
  )
  if (is.null(df)) return(character(0))
  if ("type" %in% names(df)) df <- df[df$type %in% types, , drop = FALSE]

  official <- if ("full_name" %in% names(df)) df$full_name else rep(NA_character_, nrow(df))
  nm <- mapply(construct_display_name, official, df$first_name, df$last_name,
               USE.NAMES = FALSE)

  nm <- nm[nzchar(nm)]
  hit <- nm %in% names(MEMBER_NAME_OVERRIDES)
  nm[hit] <- unname(MEMBER_NAME_OVERRIDES[nm[hit]])
  dup <- unique(nm[duplicated(nm)])
  if (length(dup) > 0) {
    message("Roster warning: identical first+last for different members (their ",
            "results would merge): ", paste(dup, collapse = "; "))
  }
  unique(nm)
}

# ---------------------------------------------------------------
# Roster metadata: District/State for column B of the score sheet
# ---------------------------------------------------------------
# congress.gov stores state as a 2-letter code; the score sheet wants the full
# state name, and -- for House members -- "Congressional District N (119th
# Congress), <State>". Senators (and at-large/territory seats with no numbered
# district) get just the full state name, matching the attached workbook.
STATE_ABBR_TO_NAME <- c(
  setNames(state.name, state.abb),
  DC = "District of Columbia", PR = "Puerto Rico", VI = "Virgin Islands",
  GU = "Guam", AS = "American Samoa", MP = "Northern Mariana Islands"
)

get_roster_meta_119 <- function(types = c("rep", "sen")) {
  empty <- data.frame(Member = character(), DistrictState = character(),
                      stringsAsFactors = FALSE)
  csv_url <- "https://unitedstates.github.io/congress-legislators/legislators-current.csv"
  df <- tryCatch(
    read.csv(url(csv_url), stringsAsFactors = FALSE, encoding = "UTF-8"),
    error = function(e) { message("Roster meta download failed: ", e$message); NULL }
  )
  if (is.null(df)) return(empty)
  if ("type" %in% names(df)) df <- df[df$type %in% types, , drop = FALSE]

  official <- if ("full_name" %in% names(df)) df$full_name else rep(NA_character_, nrow(df))
  member   <- mapply(construct_display_name, official, df$first_name, df$last_name,
                     USE.NAMES = FALSE)
  st_abbr  <- if ("state" %in% names(df)) df$state else rep(NA_character_, nrow(df))
  st_full  <- unname(STATE_ABBR_TO_NAME[st_abbr]); st_full[is.na(st_full)] <- st_abbr[is.na(st_full)]
  dist     <- if ("district" %in% names(df)) suppressWarnings(as.integer(df$district)) else rep(NA_integer_, nrow(df))
  typ      <- if ("type" %in% names(df)) df$type else rep(NA_character_, nrow(df))

  ds <- ifelse(
    typ == "sen" | is.na(dist) | dist <= 0,
    st_full,
    paste0("Congressional District ", dist, " (119th Congress), ", st_full)
  )
  out <- data.frame(Member = member, DistrictState = ds, stringsAsFactors = FALSE)
  out[nzchar(out$Member) & !duplicated(out$Member), , drop = FALSE]
}

# ---------------------------------------------------------------
# PINNED roster order
# ---------------------------------------------------------------
# The clipboard columns get pasted side-by-side into one spreadsheet, so every
# run must produce the IDENTICAL vertical sequence of members. Two things would
# silently break that: the source CSV reorders/changes as membership churns,
# and locale-dependent alphabetical sorting. So the FIRST run builds the
# roster, sorts it with the locale-independent radix method, and pins it to
# ROSTER_CACHE; every later run reuses that file byte-for-byte.
#
# To refresh membership (or after editing MEMBER_NAME_OVERRIDES), DELETE the
# cache file -- and expect the row order to change, so re-anchor your
# spreadsheet with a fresh Name column afterwards.
ROSTER_CACHE <- "roster_119_names.rds"

get_pinned_roster <- function() {
  if (file.exists(ROSTER_CACHE)) {
    nm <- readRDS(ROSTER_CACHE)
    message("Using pinned roster from ", ROSTER_CACHE, " (", length(nm),
            " members). Delete that file to refresh -- row order will change.")
    return(nm)
  }
  nm <- sort(get_roster_119(), method = "radix")
  if (length(nm) > 0) {
    saveRDS(nm, ROSTER_CACHE)
    message("Pinned roster of ", length(nm), " members to ", ROSTER_CACHE, ".")
  }
  nm
}

# ---------------------------------------------------------------
# validate_http(): run ONCE before the big run to confirm the cookie-replay HTTP
# path works on this machine (cf_clearance can be TLS-bound, in which case httr
# gets re-challenged and you should set FETCH_MODE <- "browser").
# ---------------------------------------------------------------
validate_http <- function(probe_member = members[1]) {
  load_cf_session()
  if (is.null(CF_SESSION)) harvest_cf_session(probe_member)
  url <- build_member_url(probe_member, 1, 250)
  res <- fetch_html_http(url, label = paste0(probe_member, " (validate)"))
  if (inherits(res, "xml_document")) {
    n <- length(html_nodes(res, "li.expanded"))
    cnt <- html_text(html_nodes(res, "#innerbox_congress .count"), trim = TRUE)
    message("[validate] HTTP PATH WORKS. li.expanded nodes: ", n,
            " | facet counts: ", paste(cnt, collapse = ","),
            if (is_bill_detail_page(res)) " | single-result detail layout" else "")
    message("[validate] You're clear to run the full roster in HTTP mode.")
    return(invisible(TRUE))
  }
  if (identical(res, "CHALLENGED")) {
    message("[validate] HTTP was CHALLENGED by Cloudflare (cf_clearance likely ",
            "TLS-bound). Either re-run harvest_cf_session() (fresh cookie) and try ",
            "again, or set FETCH_MODE <- \"browser\" for the slower-but-robust path.")
  } else {
    message("[validate] HTTP fetch failed (network/parse). See messages above.")
  }
  invisible(FALSE)
}

# Set FALSE to source the functions only (no scraping run).
RUN_FULL <- TRUE

# ---------------------------------------------------------------
# Switch variable: members of congress
# ---------------------------------------------------------------
# USE_FULL_ROSTER:
#   FALSE -> the short test list below (validate the pipeline first).
#   TRUE  -> ALL current members of the 119th Congress (~540 names). Do this only
#            after validate_http() confirms the fast path works.
USE_FULL_ROSTER <- TRUE

members <- if (USE_FULL_ROSTER) {
  m <- get_pinned_roster()
  message("Loaded ", length(m), " members of the 119th Congress.")
  m
} else {
  c(
    "Ann Wagner"
    ,"French Hill"
    ,"Bill Huizenga"
    ,"Andy Barr"
  )
}

if (length(members) == 0) {
  stop("Member roster is EMPTY (roster download failed and no ", ROSTER_CACHE,
       " pin exists on disk). Fix the connection and re-source -- continuing ",
       "would harvest cookies against a literal 'NA' member search.")
}

# ---------------------------------------------------------------
# URL builder (verbatim known-good link, truncation-proof)
# ---------------------------------------------------------------
# Your EXACT advanced-search URL, split into short chunks so no single physical
# line can be truncated by the console. NOT rebuilt from JSON. Concatenating the
# chunks reproduces the link byte-for-byte; only the sponsor name (the
# __MEMBER__ placeholder) changes.
#
# To edit the search: each element is ONE condition (decodes to one
# {"op":...,"inputs":{...}} object). Every condition after the first begins with
# "%2C" (an encoded comma) -- keep that leading comma if you add/remove lines.
raw_url_parts <- c(   "https://www.congress.gov/advanced-search?raw=",
                      # --- Block 1: congresses 119 / 118 / 117 ---
                      "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
                      # --- Block 2: subject-matter terms (all OR) ---
                      "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
                      "%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CDFI%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Community+Development+Financial+Institution%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Community+Development+Financial+Institution+Fund%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CDFI+Fund%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CDFI+Fund+appropriations%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CDFI+certification%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Community+Development+Financial+Institution+Fund+appropriations%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Community+Development+Financial+Institution+certification%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CDFI+bond+guarantee%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22minority+depository+institution%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Community+Development+Financial+Institution+bond+guarantee%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22MDI%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CDFI+Fund+Transparency+Act%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22AFFORD+Act%22%7D%7D",
                      "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CDFI+Bond+Guarantee+Program+Improvement+Act%22%7D%7D",
                      "%5D%7D",
                      # --- Block 3: subject areas (Agriculture / Commerce / Finance / Housing) ---
                      "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Agriculture+and+Food%22%2C%22Commerce%22%2C%22Finance+and+Financial+Sector%22%2C%22Housing+and+Community+Development%22%5D%7D%7D%5D%7D",
                      # --- Block 4: search == SWITCH VARIABLE (the member) ---
                      "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22contains%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D"
)



# Rebuild the full template once (assembled from chunks -> no truncation).
raw_url_template <- paste0(raw_url_parts, collapse = "")

# NOTE: raw_url_parts / raw_url_template above are now used ONLY as the default
# probe template for cookie harvesting + validate_http(). The actual scrape is
# driven section-by-section by SECTION_REGISTRY (built from congress_search_urls.R)
# just below, with `template` passed in explicitly.
build_member_url <- function(member_name, page_num = 1, page_size = 250,
                             template = raw_url_template) {
  if (!grepl("__MEMBER__", template, fixed = TRUE)) {
    stop("URL template has no '__MEMBER__' placeholder -- the member name cannot ",
         "be substituted. Check the sponsor chunk of the template ",
         "(the encoded value must be exactly %22__MEMBER__%22).")
  }
  # Percent-encode the name so accented letters (André -> Andr%C3%A9, García ->
  # Garc%C3%ADa, etc.) survive in the URL; then put spaces back to '+' to match
  # how congress.gov encodes this query (e.g. "Ann+Wagner"). Without this, raw
  # multibyte bytes produce a malformed URL and an empty response.
  nm <- enc2utf8(trimws(member_name))
  member_enc <- gsub("%20", "+", URLencode(nm, reserved = TRUE), fixed = TRUE)
  url <- sub("__MEMBER__", member_enc, template, fixed = TRUE)
  paste0(url, "&pageSize=", page_size, "&page=", page_num)
}

# ---------------------------------------------------------------
# SECTION REGISTRY (linked to congress_search_urls.R) + ROLE swap
# ---------------------------------------------------------------
# Every section is one *_url_parts vector from congress_search_urls.R. The order
# here MUST match the column order of the "Legislative Score - Raw" sheet.
SECTION_REGISTRY <- list(
  list(key = "examination_supervision",   label = "Examination & Supervision",                parts = examination_supervision_url_parts),
  list(key = "cu_capital_requirements",    label = "Credit Union Capital Requirements",        parts = cu_capital_requirements_url_parts),
  list(key = "ncua_budget_share_insurance",label = "NCUA Budget & Share Insurance Fund",       parts = ncua_budget_share_insurance_url_parts),
  list(key = "interchange_status_quo",     label = "Interchange",                              parts = interchange_status_quo_url_parts),
  list(key = "payments",                   label = "Payments",                                 parts = payments_url_parts),
  list(key = "technology_emerging",        label = "Technology & Emerging Issues",             parts = technology_emerging_url_parts),
  list(key = "fraud_prevention",           label = "Fraud Prevention",                         parts = fraud_prevention_url_parts),
  list(key = "data_privacy_cybersecurity", label = "Data Privacy & Cybersecurity",             parts = data_privacy_cybersecurity_url_parts),
  list(key = "charter_modernization",      label = "Charter Modernization & Governance",       parts = charter_modernization_url_parts),
  list(key = "defense_credit_union",       label = "Defense Credit Union Issues",              parts = defense_credit_union_url_parts),
  list(key = "field_of_membership",        label = "Field of Membership",                      parts = field_of_membership_url_parts),
  list(key = "cdfi_fund",                  label = "CDFI Fund",                                parts = cdfi_fund_url_parts),
  list(key = "cfpb_reform",                label = "CFPB Issues & Structural Reform",          parts = cfpb_reform_url_parts),
  list(key = "credit_card_consumer_fee",   label = "Credit Card & Consumer-Fee Mandates",      parts = credit_card_consumer_fee_url_parts),
  list(key = "tcpa",                       label = "Telephone Consumer Protection Act Issues", parts = tcpa_url_parts),
  list(key = "member_business_lending",    label = "Member Business Lending",                  parts = member_business_lending_url_parts),
  list(key = "mortgage_lending_housing",   label = "Mortgage Lending & Housing",               parts = mortgage_lending_housing_url_parts)
)

# Assemble a template's chunks into one truncation-proof string.
assemble_url_template <- function(parts) paste0(parts, collapse = "")

# The three sponsorship roles, in scrape order, and the congress.gov "field"
# token each maps to. Every template's switch condition is field":"sponsor";
# swapping that token re-points the same query at the other roles. (Token for
# original cosponsor confirmed from the project's examination-query backup.)
ROLES               <- c("sponsor", "original-cosponsor", "cosponsor")
SPONSOR_FIELD_TOKEN <- "%22field%22%3A%22sponsor%22"

apply_role <- function(template, role) {
  if (identical(role, "sponsor")) return(template)
  hits <- gregexpr(SPONSOR_FIELD_TOKEN, template, fixed = TRUE)[[1]]
  n <- if (length(hits) == 1 && hits[1] == -1) 0 else length(hits)
  if (n != 1) {
    stop("Expected exactly ONE sponsor switch token in the template, found ", n,
         ". Cannot safely swap to role '", role, "'.")
  }
  sub(SPONSOR_FIELD_TOKEN, paste0("%22field%22%3A%22", role, "%22"),
      template, fixed = TRUE)
}

# ---------------------------------------------------------------
# JS wait helpers (browser path)
# ---------------------------------------------------------------
# A page counts as "rendered" when the results list OR a bill detail page
# (single-result redirect) is present.
PAGE_READY_SELECTORS <- c(
  "ol.basic-search-results-lists li.expanded",
  "li.expanded",
  "h1.legDetail"
)

# Poll the live DOM (one Runtime evaluate per poll) until any ready-selector
# matches or we time out. Returns the match counts invisibly.
wait_for_results <- function(session, timeout = 30, interval = 1.5) {
  js <- paste0(
    "[",
    paste(sprintf("document.querySelectorAll('%s').length", PAGE_READY_SELECTORS),
          collapse = ", "),
    "].join(',')"
  )
  waited <- 0
  repeat {
    counts <- tryCatch({
      v <- session$Runtime$evaluate(js)$result$value
      as.integer(strsplit(v, ",", fixed = TRUE)[[1]])
    }, error = function(e) rep(0L, length(PAGE_READY_SELECTORS)))
    counts[is.na(counts)] <- 0L
    if (any(counts > 0) || waited >= timeout) return(invisible(counts))
    Sys.sleep(interval)
    waited <- waited + interval
  }
}

# Poll (one evaluate per poll) until the Cloudflare interstitial clears or we
# time out. TRUE if past the challenge, FALSE if it timed out still on it.
wait_past_cloudflare <- function(session, timeout = 60, interval = 2) {
  js <- paste0(
    "(/just a moment|checking your browser|attention required|verifying you are human/i",
    ".test(document.title) || !!document.querySelector(",
    "'#challenge-running,#cf-challenge-running,.cf-browser-verification,#challenge-form')) ? 1 : 0"
  )
  waited <- 0
  repeat {
    # NA = the evaluate itself failed (tab dead / session gone). That is NOT
    # proof we're past the challenge, so keep polling until timeout -> FALSE.
    on_challenge <- tryCatch(
      as.integer(session$Runtime$evaluate(js)$result$value) > 0,
      error = function(e) NA
    )
    if (isFALSE(on_challenge)) return(TRUE)
    if (waited >= timeout) return(FALSE)
    Sys.sleep(interval)
    waited <- waited + interval
  }
}

# ---------------------------------------------------------------
# Render a URL with chromote and return parsed HTML (or NULL)
# ---------------------------------------------------------------
fetch_rendered_html <- function(url, label) {
  session <- tryCatch(ChromoteSession$new(), error = function(e) {
    message("Error creating session for ", label, ": ", e$message)
    NULL
  })
  if (is.null(session)) return(NULL)
  on.exit(try(session$close(), silent = TRUE), add = TRUE)
  session$default_timeout <- CHROMOTE_TIMEOUT

  apply_stealth(session)

  success <- FALSE
  for (try_time in 1:3) {
    success <- tryCatch({
      session$Page$navigate(url, wait_ = FALSE)  # async; readyState loop waits
      Sys.sleep(runif(1, min = 1.5, max = 3))
      count <- 1
      while (session$Runtime$evaluate("document.readyState")$result$value != "complete" &&
             count <= 8) {
        Sys.sleep(1)
        count <- count + 1
      }
      TRUE
    }, error = function(e) {
      message("Navigation error for ", label, " try ", try_time, ": ", e$message)
      Sys.sleep(2^try_time)
      FALSE
    })
    if (success) break
  }
  if (!success) {
    message("Failed to load ", label)
    return(NULL)
  }

  # Let the Cloudflare interstitial solve itself (real browser) before reading.
  if (!wait_past_cloudflare(session, timeout = 60)) {
    message("  WARNING: still on a Cloudflare challenge after 60s for ", label,
            ". In remote mode, solve it by hand in the Chrome window once.")
  }

  # Wait for JS to render the result rows (or bill page) before reading the DOM.
  wait_for_results(session)

  html_str <- tryCatch(
    session$DOM$getOuterHTML(session$DOM$getDocument()$root$nodeId)$outerHTML,
    error = function(e) {
      message("Error reading DOM for ", label, ": ", e$message); NULL
    })
  if (is.null(html_str)) return(NULL)

  tryCatch(read_html(html_str), error = function(e) {
    message("Error parsing HTML for ", label, ": ", e$message); NULL
  })
}

# Empty individual-bills frame (keeps bind_rows schema stable)
empty_bills <- function() {
  data.frame(
    Member = character(), Name = character(), Title = character(),
    Sponsor = character(), CosponsorCount = integer(), Committee = character(),
    LastAction = character(), DetailLink = character(), Congress = integer(),
    bill_summary = character(),
    stringsAsFactors = FALSE
  )
}

# Reduce a long "Latest Action:" string to a short status label. Only used as a
# fallback when the congress.gov status tracker isn't present.
classify_last_action <- function(x) {
  if (length(x) == 0 || is.na(x) || !nzchar(x)) return(NA_character_)
  s <- tolower(x)
  if (grepl("became (public|private) law|public law no|signed by president", s)) return("Became Law")
  if (grepl("vetoed", s))                                                       return("Vetoed")
  if (grepl("passed.*house|agreed to in house|passed/agreed to in house", s))   return("Passed House")
  if (grepl("passed.*senate|agreed to in senate|passed/agreed to in senate", s))return("Passed Senate")
  if (grepl("presented to president|to president", s))                          return("To President")
  if (grepl("reported", s))                                                     return("Reported")
  if (grepl("introduced|referred to", s))                                       return("Introduced")
  "Introduced"  # sensible default for early-stage bills
}

# Pull the summary text off an already-parsed bill detail page.
extract_bill_summary <- function(pg) {
  txt <- tryCatch(html_text(html_node(pg, "div#bill-summary > p"), trim = TRUE),
                  error = function(e) NA_character_)
  if (length(txt) == 1 && !is.na(txt) && nzchar(txt)) txt else NA_character_
}

# ---------------------------------------------------------------
# SINGLE-RESULT LAYOUT (alternative selectors)
# ---------------------------------------------------------------
# A one-hit search redirects straight to the bill detail page, which has none of
# the results-list nodes. These backup selectors recover that one bill:
#   tr:nth-child(1) a                       -> sponsor (legislator name)
#   tr:nth-child(2) td , tr:nth-child(1) a  -> committee
#   li:nth-child(6) a                       -> cosponsor count (tab text)
#   .last                                   -> last action
#   strong                                  -> bill title
#   a ~ a + a                               -> legislative session (congress no.)
#   #summarySelector a:nth-child(1)         -> detail link / summary source
is_bill_detail_page <- function(pg) {
  length(html_nodes(pg, "h1.legDetail, #summarySelector, #bill-summary")) > 0
}

parse_single_bill_page <- function(pg, member_name) {
  grab_text <- function(sel) {
    out <- tryCatch(html_text(html_node(pg, sel), trim = TRUE),
                    error = function(e) NA_character_)
    if (length(out) != 1 || is.na(out) || !nzchar(out)) NA_character_ else out
  }
  grab_attr <- function(sel, attr) {
    out <- tryCatch(html_attr(html_node(pg, sel), attr),
                    error = function(e) NA_character_)
    if (length(out) != 1 || is.na(out) || !nzchar(out)) NA_character_ else out
  }

  h1_txt <- grab_text("h1.legDetail")  # "H.R.2797 - <title> 118th Congress (2023-2024)"

  # Detail link: #summarySelector first anchor; fallback the canonical link.
  detail_link <- grab_attr("#summarySelector a:nth-child(1)", "href")
  if (is.na(detail_link)) detail_link <- grab_attr("link[rel='canonical']", "href")

  # Bill number: leading chunk of the h1; fallback rebuilt from the link path.
  name <- if (!is.na(h1_txt)) trimws(sub("\\s+-\\s+.*$", "", h1_txt)) else NA_character_
  if ((is.na(name) || identical(name, h1_txt)) && !is.na(detail_link)) {
    m <- regmatches(detail_link, regexec(
      "/(house|senate)-(bill|resolution|joint-resolution|concurrent-resolution)/([0-9]+)",
      detail_link))[[1]]
    if (length(m) == 4) {
      chamber <- if (m[2] == "house") "H" else "S"
      typ <- c(bill = if (chamber == "H") ".R." else ".",
               resolution = ".Res.", `joint-resolution` = ".J.Res.",
               `concurrent-resolution` = ".Con.Res.")[[m[3]]]
      name <- paste0(chamber, typ, m[4])
    }
  }

  # Title: first <strong>; fallback the middle of the h1.
  title <- grab_text("strong")
  if (!is.na(title) && grepl("shown here", title, ignore.case = TRUE)) title <- NA_character_
  if (is.na(title) && !is.na(h1_txt)) {
    t <- sub("\\s*[0-9]{2,3}(st|nd|rd|th)\\s+Congress.*$", "", h1_txt)
    parts <- strsplit(t, "\\s+-\\s+")[[1]]
    if (length(parts) >= 2) title <- trimws(paste(parts[-1], collapse = " - "))
  }

  sponsor <- grab_text("tr:nth-child(1) a")

  committee <- grab_text("tr:nth-child(2) td")
  if (is.na(committee)) {
    cand <- tryCatch(
      html_text(html_nodes(pg, "tr:nth-child(2) td , tr:nth-child(1) a"), trim = TRUE),
      error = function(e) character(0))
    hit <- cand[grepl("Committee|House -|Senate -", cand)]
    if (length(hit) > 0) committee <- hit[1]
  }

  # Cosponsor count: the Cosponsors tab text "Cosponsors (N)"; fallback any
  # anchor whose href targets the cosponsors page.
  cosponsor_count <- tryCatch({
    txt <- grab_text("li:nth-child(6) a")
    if (!is.na(txt) && !grepl("cosponsor", txt, ignore.case = TRUE)) txt <- NA_character_
    if (is.na(txt)) {
      ca <- tryCatch(html_text(html_nodes(pg, "a[href*='cosponsors']"), trim = TRUE),
                     error = function(e) character(0))
      ca <- ca[grepl("[0-9]", ca)]
      txt <- if (length(ca) > 0) ca[1] else NA_character_
    }
    n <- suppressWarnings(as.integer(gsub("\\D", "", txt)))
    if (is.na(n)) 0L else n
  }, error = function(e) NA_integer_)

  # Last action: the tracker's hidden "has the status X" text (same as the
  # results layout); fallback .last; fallback keyword-classified "Latest Action".
  last_action <- tryCatch({
    ps  <- html_text(html_nodes(pg, "p.hide_fromsighted"), trim = TRUE)
    hit <- ps[grepl("has the status", ps, ignore.case = TRUE)]
    if (length(hit) > 0 && nzchar(trimws(sub(".*has the status", "", hit[1])))) {
      trimws(sub(".*has the status", "", hit[1]))
    } else {
      la <- grab_text(".last")
      if (!is.na(la)) la else {
        rows <- tryCatch(html_text(html_nodes(pg, "tr"), trim = TRUE),
                         error = function(e) character(0))
        raw <- rows[grepl("Latest Action", rows)]
        classify_last_action(if (length(raw) > 0) raw[1] else NA_character_)
      }
    }
  }, error = function(e) NA_character_)

  # Legislative session ("118th Congress (2023-2024)") via sibling anchors;
  # fallback the h1 text.
  congress_num <- tryCatch({
    sess <- c(tryCatch(html_text(html_nodes(pg, "a ~ a + a"), trim = TRUE),
                       error = function(e) character(0)), h1_txt)
    sess <- sess[!is.na(sess)]
    hit <- regmatches(sess, regexpr("[0-9]{2,3}(st|nd|rd|th)\\s+Congress", sess))
    if (length(hit) > 0) as.integer(gsub("\\D", "", hit[1])) else NA_integer_
  }, error = function(e) NA_integer_)

  # We are already ON the detail page, so take the summary now (saves a Stage-2
  # fetch). If absent, Stage 2 fetches detail_link as usual.
  bill_summary <- extract_bill_summary(pg)

  if (is.na(name) && is.na(title) && is.na(detail_link)) return(NULL)
  data.frame(
    Member = member_name, Name = name, Title = title, Sponsor = sponsor,
    CosponsorCount = cosponsor_count, Committee = committee,
    LastAction = last_action, DetailLink = detail_link, Congress = congress_num,
    bill_summary = bill_summary,
    stringsAsFactors = FALSE
  )
}

# ---------------------------------------------------------------
# Results-list layout: one row from one li.expanded node
# ---------------------------------------------------------------
parse_result_node <- function(bill, member_name) {
  name <- tryCatch(bill %>% html_node(".result-heading a") %>% html_text(trim = TRUE),
                   error = function(e) NA)
  detail_link <- tryCatch(bill %>% html_node(".result-heading a") %>% html_attr("href"),
                          error = function(e) NA)

  title <- tryCatch(bill %>% html_node(".result-title") %>% html_text(trim = TRUE),
                    error = function(e) NA)

  sponsor <- tryCatch({
    s <- bill %>% html_node(".result-title + .result-item a:nth-child(2)") %>% html_text(trim = TRUE)
    if (length(s) == 0 || is.na(s)) {
      s2 <- bill %>% html_nodes(".result-title + .result-item a")
      if (length(s2) >= 1) html_text(s2[[1]], trim = TRUE) else NA
    } else s
  }, error = function(e) NA)

  # Co-sponsor count = TEXT of the cosponsors link:
  # `<strong>Cosponsors:</strong> (<a href=".../cosponsors...">42</a>)`.
  # Fallback the parenthesised "Cosponsors: (N)" text; 0 if none.
  cosponsor_count <- tryCatch({
    ca <- bill %>% html_nodes("a[href*='cosponsors']") %>% html_text(trim = TRUE)
    ca <- suppressWarnings(as.integer(ca[grepl("^[0-9]+$", ca)]))
    if (length(ca) > 0 && !is.na(ca[1])) {
      ca[1]
    } else {
      ri_text  <- bill %>% html_nodes(".result-item") %>% html_text(trim = TRUE)
      cos_line <- ri_text[grepl("Cosponsors:", ri_text)]
      m <- if (length(cos_line) > 0)
        regmatches(cos_line[1], regexpr("Cosponsors:\\s*\\(\\s*[0-9]+", cos_line[1])) else character(0)
      if (length(m) > 0 && nzchar(m)) as.integer(gsub("\\D", "", m)) else 0L
    }
  }, error = function(e) NA_integer_)

  committee <- tryCatch({
    c5 <- bill %>% html_node(".result-item:nth-child(5)") %>% html_text(trim = TRUE)
    if (length(c5) == 0 || is.na(c5) || !grepl("Committee", c5)) {
      txt <- bill %>% html_nodes(".result-item") %>% html_text(trim = TRUE)
      hit <- txt[grep("Committee", txt)]
      if (length(hit) > 0) hit[1] else if (!is.na(c5)) c5 else NA
    } else c5
  }, error = function(e) NA)

  # Last Action: the tracker carries it verbatim as "This bill has the status
  # <X>". Fallback: keyword-classify the raw "Latest Action:" text.
  last_action <- tryCatch({
    ps  <- bill %>% html_nodes("p.hide_fromsighted") %>% html_text(trim = TRUE)
    hit <- ps[grepl("has the status", ps, ignore.case = TRUE)]
    if (length(hit) > 0) {
      s <- trimws(sub(".*has the status", "", hit[1]))
      if (nzchar(s)) s else NA_character_
    } else {
      txt <- bill %>% html_nodes(".result-item") %>% html_text(trim = TRUE)
      raw <- txt[grep("Latest Action", txt)]
      classify_last_action(if (length(raw) > 0) raw[1] else NA_character_)
    }
  }, error = function(e) NA_character_)

  data.frame(
    Member         = member_name,
    Name           = if (length(name) > 0) name else NA_character_,
    Title          = if (length(title) > 0) title else NA_character_,
    Sponsor        = if (length(sponsor) > 0) sponsor else NA_character_,
    CosponsorCount = if (length(cosponsor_count) > 0) cosponsor_count else NA_integer_,
    Committee      = if (length(committee) > 0) committee else NA_character_,
    LastAction     = if (length(last_action) > 0) last_action else NA_character_,
    DetailLink     = if (length(detail_link) > 0) detail_link else NA_character_,
    Congress       = NA_integer_,   # filled from DetailLink in Stage 2.2
    bill_summary   = NA_character_, # filled in Stage 2
    stringsAsFactors = FALSE
  )
}

# ---------------------------------------------------------------
# Stage 1: Scrape one member's advanced-search results
# Returns list(bills = <data.frame>, billcount_total = <numeric>, status = <chr>)
# ---------------------------------------------------------------
scrape_member_overview_impl <- function(member_name, allow_browser_fallback = FALSE,
                                        cf = CF_SESSION, template = raw_url_template) {
  page_size            <- 250
  max_pages_per_member <- 20
  all_rows             <- list()
  billcount_total      <- NA_real_
  page_num             <- 1
  status               <- "ok"

  repeat {
    member_url <- build_member_url(member_name, page_num, page_size, template = template)
    label <- paste0(member_name, " (page ", page_num, ")")
    message("Member '", member_name, "' page ", page_num)

    overview_page <- fetch_page(member_url, label,
                                allow_browser_fallback = allow_browser_fallback, cf = cf)
    if (is.null(overview_page)) {
      # In HTTP mode a NULL means Cloudflare challenged us (or the request hard-
      # failed) -- on ANY page, not just page 1: a mid-pagination failure would
      # otherwise ship partial rows as "ok". Flagged members are re-scraped from
      # page 1 and the driver keeps only the fresh result, so no duplicates.
      # (A real zero-results page is non-NULL.)
      if (identical(FETCH_MODE, "http")) status <- "challenged"
      break
    }

    # --- Member statistic: Bill Count facet #innerbox_congress .count, summed ---
    if (page_num == 1) {
      billcount_total <- tryCatch({
        counts <- overview_page %>% html_nodes("#innerbox_congress .count") %>% html_text(trim = TRUE)
        counts_num <- as.numeric(gsub("[^0-9]", "", counts))
        if (length(counts_num) > 0) sum(counts_num, na.rm = TRUE) else NA_real_
      }, error = function(e) NA_real_)
      message("  Bill Count (summed) for ", member_name, ": ", billcount_total)
    }

    bill_nodes <- overview_page %>% html_nodes("ol.basic-search-results-lists li.expanded")
    if (length(bill_nodes) == 0) {
      bill_nodes <- overview_page %>% html_nodes("li.expanded")
    }

    # Single-result layout: a one-hit search redirects straight to the bill page.
    if (length(bill_nodes) == 0 && page_num == 1 && is_bill_detail_page(overview_page)) {
      one <- parse_single_bill_page(overview_page, member_name)
      if (!is.null(one)) {
        message("  Single-result layout (redirected to bill page) -> 1 bill")
        all_rows <- c(all_rows, list(one))
        if (is.na(billcount_total)) billcount_total <- 1
      }
      break
    }

    message("  Found ", length(bill_nodes), " bill nodes")
    if (length(bill_nodes) == 0) break

    all_rows <- c(all_rows, lapply(bill_nodes, parse_result_node,
                                   member_name = member_name))

    if (length(bill_nodes) < page_size) break
    page_num <- page_num + 1
    if (page_num > max_pages_per_member) break
    Sys.sleep(runif(1, HTTP_PAUSE[1], HTTP_PAUSE[2]))  # politeness between pages
  }

  bills <- if (length(all_rows) == 0) empty_bills() else bind_rows(all_rows)
  list(bills = bills, billcount_total = billcount_total, status = status)
}

# Error-proof wrapper: future_lapply propagates errors, so one unexpected
# failure in one member would abort the WHOLE parallel round. A failed member
# instead comes back empty + "challenged", which the HTTP driver retries and
# ultimately hands to the browser fallback.
scrape_member_overview <- function(member_name, allow_browser_fallback = FALSE,
                                   cf = CF_SESSION, template = raw_url_template) {
  tryCatch(
    scrape_member_overview_impl(member_name, allow_browser_fallback, cf, template = template),
    error = function(e) {
      message("  ERROR scraping '", member_name, "': ", conditionMessage(e))
      list(bills = empty_bills(), billcount_total = NA_real_, status = "challenged")
    }
  )
}

# ---------------------------------------------------------------
# Stage 1 driver: switch over members
# ---------------------------------------------------------------
if (RUN_FULL) {

  # Load any prior progress. If a previous run already finished scraping AND
  # summaries, just reuse its Bills and skip straight to writing the workbooks.
  .ckpt <- load_checkpoint()
  SKIP_SCRAPE <- RESUME && isTRUE(.ckpt$summaries_done) && !is.null(.ckpt$bills)

  # Every (section, role) pass key the run expects to exist.
  ROLE_KEYS <- unlist(lapply(SECTION_REGISTRY, function(s)
                 vapply(ROLES, function(r) pass_key(s$key, r), character(1))), use.names = FALSE)

  if (SKIP_SCRAPE) {
    Bills <- .ckpt$bills
    message("Checkpoint already complete (scrape + summaries). Reusing ",
            nrow(Bills), " bill rows; skipping straight to the output build.")
  } else {

  # Harvest the Cloudflare cookie ONCE (needed for the scrape and/or the Stage 2
  # summary fetch), open the browser ONCE up front.
  if (identical(FETCH_MODE, "http")) {
    load_cf_session()
    if (is.null(CF_SESSION)) harvest_cf_session(members[1])
  } else {
    init_browser()
  }

  if (isTRUE(.ckpt$scrape_complete) && length(RESCRAPE_PASSES) == 0) {
    # ============================================================
    # GUARDRAIL #1 -- Stage 1 is LOCKED complete. Reuse the cached
    # passes verbatim; NEVER re-scrape part of a finished scrape (that
    # is exactly how a flaky re-run silently undercounts a section).
    # If a pass is missing, STOP rather than quietly re-scraping it.
    # ============================================================
    missing <- setdiff(ROLE_KEYS, names(.ckpt$passes))
    if (length(missing) > 0) {
      stop("GUARDRAIL (scrape_complete=TRUE) but ", length(missing),
           " pass(es) MISSING: ", paste(head(missing, 6), collapse = ", "),
           if (length(missing) > 6) ", ..." else "",
           ".\nRefusing to silently re-scrape part of a finished scrape. Restore a ",
           "checkpoint backup, OR deliberately unlock to re-scrape with:\n",
           "  ck <- readRDS(\"", CHECKPOINT_FILE, "\"); ck$scrape_complete <- FALSE; ",
           "saveRDS(ck, \"", CHECKPOINT_FILE, "\")")
    }
    Bills <- bind_rows(Filter(function(d) nrow(d) > 0, .ckpt$passes[ROLE_KEYS]))
    message("Stage 1 LOCKED (scrape_complete=TRUE): reusing ", length(.ckpt$passes),
            " cached passes verbatim, NO scraping. ", nrow(Bills), " bill rows.")

  } else {

  # Scrape ALL members for ONE assembled+role-substituted template. Returns the
  # per-member results AND how many members fell to the (unreliable) browser
  # fallback, so the caller can refuse to trust a fallback-heavy re-scrape.
  scrape_members_for_template <- function(template) {
    if (identical(FETCH_MODE, "http")) {
      run_round <- function(names_vec) {
        future_lapply(names_vec, scrape_member_overview,
                      allow_browser_fallback = FALSE, cf = CF_SESSION,
                      template = template, future.seed = TRUE)
      }
      results_by_member <- setNames(vector("list", length(members)), members)
      todo <- members
      max_rounds <- 3
      for (round in seq_len(max_rounds)) {
        if (length(todo) == 0) break
        message("    round ", round, ": ", length(todo), " member(s) via parallel HTTP")
        res <- run_round(todo)
        names(res) <- todo
        done <- vapply(res, function(x) !identical(x$status, "challenged"), logical(1))
        results_by_member[todo[done]] <- res[done]
        todo <- todo[!done]
        if (length(todo) > 0 && round < max_rounds) {
          message("    ", length(todo), " member(s) challenged -> re-harvesting cookie")
          harvest_cf_session(todo[1])
        }
      }
      if (length(todo) > MAX_CHALLENGED_BEFORE_ABORT) {
        stop(sprintf(paste0(
          "Aborting: %d / %d members still challenged after %d HTTP rounds + cookie ",
          "re-harvest -- congress.gov is unstable / rate-limiting right now. This pass ",
          "was NOT saved; the checkpoint still holds the completed passes, so a later ",
          "re-run resumes cleanly. (Guard: MAX_CHALLENGED_BEFORE_ABORT = %d.)"),
          length(todo), length(members), max_rounds, MAX_CHALLENGED_BEFORE_ABORT))
      }
      n_fallback <- length(todo)
      if (n_fallback > 0) {
        message("    ", n_fallback, " member(s) still challenged -> browser fallback")
        init_browser()
        for (m in todo) {
          results_by_member[[m]] <- scrape_member_overview(m, allow_browser_fallback = TRUE,
                                                           cf = CF_SESSION, template = template)
        }
      }
      list(results = results_by_member[members], n_fallback = n_fallback)
    } else {
      # --- Browser path: one shared real Chrome, sequential ---
      r <- setNames(
        future_lapply(members, scrape_member_overview,
                      allow_browser_fallback = TRUE, template = template,
                      future.seed = TRUE),
        members)
      list(results = r, n_fallback = 0L)
    }
  }

  # ---- Loop: section by section; within each, sponsor -> orig cosponsor -> cosponsor ----
  # Each (section, role) is one "pass". Finished passes are cached in
  # .ckpt$passes and skipped on resume; we save after EVERY pass, so a crash
  # loses at most the pass in flight.
  n_sec  <- length(SECTION_REGISTRY)
  n_pass <- n_sec * length(ROLES)
  pass_i <- 0L
  for (si in seq_len(n_sec)) {
    sec  <- SECTION_REGISTRY[[si]]
    base <- assemble_url_template(sec$parts)
    for (role in ROLES) {
      pass_i <- pass_i + 1L
      key <- pass_key(sec$key, role)
      if (RESUME && !is.null(.ckpt$passes[[key]]) && !(key %in% RESCRAPE_PASSES)) {
        message(sprintf("[pass %d/%d] %s | %s  -- cached, skipping (%d rows)",
                        pass_i, n_pass, sec$label, role, nrow(.ckpt$passes[[key]])))
        next
      }
      if (key %in% RESCRAPE_PASSES && !is.null(.ckpt$passes[[key]])) {
        message(sprintf("[pass %d/%d] %s | %s  -- FORCE re-scrape (cached %d rows; no-regression guard active)",
                        pass_i, n_pass, sec$label, role, nrow(.ckpt$passes[[key]])))
      }
      message(sprintf("\n[pass %d/%d | section %d/%d | %s] role: %s",
                      pass_i, n_pass, si, n_sec, sec$label, role))
      tmpl <- apply_role(base, role)
      mres <- scrape_members_for_template(tmpl)

      pass_list <- list()
      for (m in members) {
        b <- mres$results[[m]]$bills
        if (!is.null(b) && nrow(b) > 0) {
          b$Section <- sec$label; b$SectionKey <- sec$key; b$Role <- role
          pass_list[[length(pass_list) + 1L]] <- b
        }
      }
      pass_bills <- if (length(pass_list) == 0) {
        cbind(empty_bills(), Section = character(), SectionKey = character(), Role = character())
      } else bind_rows(pass_list)

      # ============================================================
      # GUARDRAIL #2 -- no-regression. Never overwrite a previously
      # cached pass with a SMALLER result that came out of the browser
      # fallback (a flaky, likely-incomplete scrape). Keep the larger,
      # trusted version. (This is exactly the MBL 90 -> 65 mistake.)
      # ============================================================
      prev <- .ckpt$passes[[key]]
      if (!is.null(prev) && nrow(prev) > nrow(pass_bills) && mres$n_fallback > 0) {
        message("  GUARDRAIL: re-scrape got ", nrow(pass_bills), " rows < cached ",
                nrow(prev), " AND used browser fallback (", mres$n_fallback,
                " member(s)) -> KEEPING the cached version, not overwriting.")
      } else {
        .ckpt$passes[[key]] <- pass_bills
        save_checkpoint(.ckpt)
        message("  pass saved to checkpoint (", nrow(pass_bills), " bill rows",
                if (mres$n_fallback > 0) paste0("; ", mres$n_fallback, " via fallback") else "",
                "; ", length(.ckpt$passes), "/", n_pass, " passes done)")
      }
    }
  }

  # Combine all passes into the individual bills table.
  nonempty <- Filter(function(d) nrow(d) > 0, .ckpt$passes)
  Bills <- if (length(nonempty) == 0) {
    cbind(empty_bills(), Section = character(), SectionKey = character(), Role = character())
  } else {
    bind_rows(nonempty)
  }

  # Lock Stage 1 once every expected pass is present, so future re-runs reuse it
  # verbatim instead of risking a flaky re-scrape.
  if (length(setdiff(ROLE_KEYS, names(.ckpt$passes))) == 0) {
    .ckpt$scrape_complete <- TRUE
    save_checkpoint(.ckpt)
    message("Stage 1 complete -> checkpoint LOCKED (scrape_complete = TRUE).")
  }

  gc()
  message("\nOverview scraping complete. ", length(.ckpt$passes), "/", n_pass,
          " passes | Individual bill rows: ", nrow(Bills))

  } # end else (fresh scrape, not locked)
  } # end else (not skip-to-output)
} # end if (RUN_FULL) -- Stage 1 driver

# ---------------------------------------------------------------
# Stage 2.1: bill detail pages (summary text)
# ---------------------------------------------------------------
# HTTP fast path: summaries are in the server HTML, so one httr GET with the
# harvested cookies suffices. Browser path reuses fetch_rendered_html.
# Returns the summary text, NA when the page has none, or "CHALLENGED" so the
# driver can re-harvest the cookie and retry instead of silently writing NA.
scrape_detail_page <- function(detail_link, cf = CF_SESSION) {
  if (is.na(detail_link) || !nzchar(detail_link)) return(NA_character_)
  if (!grepl("^http", detail_link)) {
    detail_link <- paste0("https://www.congress.gov", detail_link)
  }
  Sys.sleep(runif(1, HTTP_PAUSE[1], HTTP_PAUSE[2]))
  pg <- if (identical(FETCH_MODE, "http")) {
    fetch_html_http(detail_link, label = "detail", cf = cf)
  } else {
    fetch_rendered_html(detail_link, "detail")
  }
  if (identical(pg, "CHALLENGED")) return("CHALLENGED")
  if (!inherits(pg, "xml_document")) return(NA_character_)
  extract_bill_summary(pg)
}

# ---------------------------------------------------------------
# Stage 2.2: bill summaries + member statistics + export
# ---------------------------------------------------------------
if (RUN_FULL) {

  handlers("txtprogressbar")

  if (!FETCH_SUMMARIES) {
    message("[summaries] FETCH_SUMMARIES = FALSE -- Stage 2 OFF, skipping the summary fetch ",
            "(bill_summary left as-is).")
  } else if (RESUME && isTRUE(.ckpt$summaries_done)) {
    message("[summaries] cached in checkpoint -- skipping summary fetch.")
  } else {
  # Only fetch summaries still missing (single-result rows already carry theirs),
  # and fetch each distinct link once.
  need  <- which(is.na(Bills$bill_summary) & !is.na(Bills$DetailLink))
  links <- unique(Bills$DetailLink[need])
  if (length(links) > 0) {
    if (!identical(FETCH_MODE, "http")) init_browser()

    fetch_summary_round <- function(lnks, cf) {
      with_progress({
        p <- progressor(steps = length(lnks))
        res <- future_lapply(lnks, function(lnk, cf) {
          out <- scrape_detail_page(lnk, cf = cf)
          p()
          out
        }, cf = cf, future.seed = TRUE)
        unlist(res)
      })
    }

    summaries <- fetch_summary_round(links, CF_SESSION)
    names(summaries) <- links

    # The cookie can expire mid-run: re-harvest ONCE and retry just the
    # challenged links rather than silently writing NA summaries.
    chal <- names(summaries)[which(summaries == "CHALLENGED")]
    if (length(chal) > 0 && identical(FETCH_MODE, "http")) {
      message("[summaries] ", length(chal),
              " link(s) challenged -> re-harvesting cookie and retrying")
      harvest_cf_session()
      retry <- fetch_summary_round(chal, CF_SESSION)
      names(retry) <- chal
      summaries[chal] <- retry
    }
    still <- which(summaries == "CHALLENGED")
    if (length(still) > 0) {
      warning(length(still), " summary fetch(es) still challenged -- left NA. ",
              "Re-run after harvest_cf_session(), or set FETCH_MODE <- \"browser\".")
      summaries[still] <- NA_character_
    }
    Bills$bill_summary[need] <- unname(summaries[Bills$DetailLink[need]])
  }
  # Cache the finished, summarized Bills so a later re-run skips Stages 1-2 and
  # goes straight to writing the workbooks.
  .ckpt$bills <- Bills
  .ckpt$summaries_done <- TRUE
  save_checkpoint(.ckpt)
  message("[summaries] complete -- Bills cached to checkpoint (",
          CHECKPOINT_FILE, ").")
  }  # end else (summaries not yet cached)
  gc()

  # ---------------------------------------------------------------
  # Congress column: the single-result parser sets it directly; everything else
  # derives from the DetailLink path. Backfilled ON Bills ITSELF so the decay
  # weight (below) and the archive both carry it.
  # ---------------------------------------------------------------
  if (nrow(Bills) > 0) {
    Bills$Congress <- ifelse(!is.na(Bills$Congress), as.integer(Bills$Congress),
                             suppressWarnings(as.integer(
                               sub(".*/([0-9]+)[a-z]{2}-congress/.*", "\\1", Bills$DetailLink))))
  }

  # Per-session decay weight. ONLY the three COUNT columns use it (per spec);
  # averages + success rates stay un-decayed. 119th -> 1, 118th -> 0.8, 117th -> 0.64.
  Bills$DecayWeight <- if (nrow(Bills) > 0) congress_decay_weight(Bills$Congress) else numeric(0)

  # --- Precision cleanup: drop audited false-positive bills (bill_drop_final.csv) ---
  # Matches by congress + chamber letter + bill number (robust to H.R./H.Res. forms).
  EXCLUDE_BILLS_CSV <- "bill_drop_final.csv"
  if (file.exists(EXCLUDE_BILLS_CSV) && nrow(Bills) > 0) {
    .ex <- tryCatch(read.csv(EXCLUDE_BILLS_CSV, stringsAsFactors = FALSE), error = function(e) NULL)
    if (!is.null(.ex) && all(c("congress", "bill") %in% names(.ex))) {
      .bkey <- function(name, cong) {
        s <- toupper(as.character(name))
        ch <- substr(gsub("[^HS]", "", s), 1, 1)
        paste0(suppressWarnings(as.integer(cong)), "_", ch, "_", gsub("\\D", "", s))
      }
      exset <- .bkey(.ex$bill, .ex$congress)
      keep  <- !(.bkey(Bills$Name, Bills$Congress) %in% exset)
      nb <- nrow(Bills); Bills <- Bills[keep, , drop = FALSE]
      message(sprintf("[precision] excluded %d false-positive bill-rows (%d -> %d) per %s",
                      nb - nrow(Bills), nb, nrow(Bills), EXCLUDE_BILLS_CSV))
    }
  }

  # ===============================================================
  # OUTPUT 1: "Legislative Score - Raw"  (replicates the attached workbook)
  # ===============================================================
  # Exact 143-col header row + Weight row, lifted from "Moneyball Main Version -
  # Presentation.xlsx" so the layout matches the sheet 1:1. Columns 3..138 are
  # 17 sections x 8 metrics (in SECTION_REGISTRY order); 139..143 are the
  # committee/leadership columns, which come from other data sources and are
  # left blank by the scraper.
  LEGIS_HEADERS <- c(
    "Names ", "District/State",
    "Examination & Supervision Sponsor", "Average Co-Sponsors (Sponsor)",
    "Examination & Supervision Original Co-Sponsorship", "Average Cosponsor (Original Co-Sponsor)",
    "Examination & Supervision Co-Sponsorship", "Examination & Supervision Success Rate",
    "Sponsor Success - ES", "Original Co-Sponsor Success - ES",
    "Credit Union Capital Requirements - Sponsor", "Average",
    "Credit Union Capital Requirements - Original Co-Sponsorship",
    "Credit Union Capital Requirements - Original Co-Sponsorship Average",
    "Credit Union Capital Requirements Co-Sponsorship", "Credit Union Capital Requirements Success Rate",
    "Sponsor Success", "Original Co-sponsor Success",
    "NCUA Budget & Share Insurance Fund - Sponsor", "Average - Sponsor - NCUA Budget & Share Insurance Fund",
    "NCUA Budget & Share Insurance Fund Original Co-Sponsorship",
    "NCUA Budget & Share Insurance Fund - Original Co-Sponsorship - Average",
    "NCUA Budget & Share Insurance Fund Co-Sponsorship", "NCUA Budget & Share Insurance Fund - Success Rate",
    "Sponsor - Success Rate - NCUA Budget & Share Insurance Fund",
    "Original Co-sponsor - Success Rate - NCUA Budget & Share Insurance Fund",
    "Interchange - Sponsor", "Interchange - Sponsor - Average",
    "Interchange - Original Co-Sponsorship", "Interchange - Original Co-Sponsorship - Average",
    "Interchange - Co-Sponsorship", "Interchange - Success Rate",
    "Interchange - Sponsor -  Success Rate", "Original Co-Sponsor - Success Rate - Interchange",
    "Payments - Sponsor", "Payments - Sponsor - Average",
    "Payments - Original Co-Sponsorship", "Payments - Average - Original Co-Sponsorship",
    "Payments - Co-Sponsorship", "Payments - Success Rate",
    "Payment - Sponsor - Success Rate", "Payment - Original Co-Sponsor - Success Rate",
    "Technology & Emerging Issues - Sponsor", "Technology & Emerging Issues - Sponsor - Average",
    "Technology and Emerging Issues - Original Co-Sponsorship",
    "Technology and Emerging Issues - Original Co-Sponsorship - Average",
    "Technology & Emerging Issues - Co-Sponsorship", "Technology & Emerging Issues - Success Rate",
    "Technology & Emerging Issues - Success Rate - Sponsor",
    "Technology & Emerging Issues - Success Rate - Original Co-Sponsorship",
    "Fraud Prevention - Sponsor", "Fraud Prevention - Sponsor - Average",
    "Fraud Prevention - Original Co-Sponsorship", "Fraud Prevention - Original Co-Sponsorship - Average",
    "Fraud Prevention - Co-Sponsorship", "Fraud Prevention - Success Rate",
    "Fraud - Sponsor - Success Rate", "Fraud - Original Co-sponsor - Success Rate",
    "Data Privacy & Cybersecurity - Sponsor", "Data Privacy & Cybersecurity - Sponsor - Average",
    "Data Privacy & Cybersecurity - Original Co-Sponsorship",
    "Data Privacy & Cybersecurity - Original Co-Sponsorship - Average",
    "Data Privacy & Cybersecurity - Co-Sponsorship", "Data Privacy & Cybersecurity - Success Rate",
    "Data Privacy & Cybersecurity - Sponsor - Success Rate",
    "Data Privacy & Cybersecurity - Original Co-sponsor  - Success Rate",
    "Charter Modernization & Governance - Sponsor", "Charter Modernization & Governance - Sponsor - Average",
    "Charter Modernization & Governance- Original Co-Sponsorship",
    "Charter Modernization & Governance- Original Co-Sponsorship - Average",
    "Charter Modernization & Governance - Co-Sponsorship", "Charter Modernization & Governance - Success Rate",
    "Charter Modernization & Governance - Sponsor - Success Rate",
    "Charter Modernization & Governance - Original Co-sponsor - Success Rate",
    "Defense Credit Union Issues - Sponsor", "Defense Credit Union Issues - Sponsor - Average",
    "Defense Credit Union Issues - Original Co-Sponsorship",
    "Defense Credit Union Issues - Original Co-Sponsorship - Average",
    "Defense Credit Union Issues - Co-Sponsorship", "Defense Credit Union Issues - Success Rate",
    "Defense Credit Union Issues - Sponsor - Success Rate",
    "Defense Credit Union Issues - Original Co-Sponsor - Success Rate",
    "Field of Membership - Sponsor", "Field of Membership - Sponsor - Average",
    "Field of Membership - Original Co-Sponsorship", "Field of Membership - Original Co-Sponsorship - Average",
    "Field of Membership - Co-Sponsorship", "Field of Membership - Success Rate",
    "Field of Membership - Sponsor - Success Rate", "Field of Membership - Original Co-Sponsor - Success Rate",
    "CDFI Fund - Sponsor", "CDFI Fund - Sponsor - Average",
    "CDFI Fund - Original Co-Sponsorship", "Column17",
    "CDFI Fund - Co-Sponsorship", "CDFI Fund - Success Rate",
    "CDFI Fund - Success Rate - Sponsor", "CDFI Fund - Success Rate - Original Co-Sponsor",
    "CFPB Issues & Structural Reform - Sponsor", "CFPB Issues & Structural Reform - Sponsor - Average",
    "CFPB Issues & Structural Reform -Original Co-Sponsor",
    "CFPB Issues & Structural Reform -Original Co-Sponsor - Average",
    "CFPB Issues & Structural Reform - Co-Sponsor", "CFPB Issues & Structural Reform - Success Rate",
    "CFPB Issues & Structural Reform - Sponsor - Success Rate",
    "CFPB Issues & Structural Reform - Original Co-Sponsor - Success Rate",
    "Credit Card & Consumer-Fee Mandates - Sponsor", "Credit Card & Consumer-Fee Mandates - Sponsor - Average",
    "Credit Card & Consumer-Fee Mandates - Original Co-Sponsor",
    "Credit Card & Consumer-Fee Mandates - Original Co-Sponsor - Average",
    "Credit Card & Consumer-Fee Mandates - Co-Sponsor", "Credit Card & Consumer-Fee Mandates - Success Rate",
    "Credit Card & Consumer-Fee Mandates - Sponsor - Success Rate",
    "Credit Card & Consumer-Fee Mandates - Original Co-Sponsor - Success Rate",
    "Telephone Consumer Protection Act Issues - Sponsor",
    "Telephone Consumer Protection Act Issues - Sponsor - Average",
    "Telephone Consumer Protection Act Issues - Original Co-Sponsor",
    "Telephone Consumer Protection Act Issues - Original Co-Sponsor - Average",
    "Telephone Consumer Protection Act Issues - Co-Sponsor",
    "Telephone Consumer Protection Act Issues - Success Rate",
    "Telephone Consumer Protection Act Issues - Sponsor - Success Rate",
    "Telephone Consumer Protection Act Issues - Original Co-Sponsor - Success Rate",
    "Member Business Lending - Sponsor", "Member Business Lending - Sponsor - Average",
    "Member Business Lending - Original Co-Sponsor", "Member Business Lending - Original Co-Sponsor - Average",
    "Member Business Lending - Co-Sponsor", "Member Business Lending - Success Rate",
    "Member Business Lending - Sponsor - Success Rate", "Member Business Lending - Original Co-Sponsor - Success Rate",
    "Mortgage Lending & Housing - Sponsor", "Mortgage Lending & Housing - Sponsor - Average",
    "Mortgage Lending & Housing - Original Co-Sponsor", "Mortgage Lending & Housing - Original Co-Sponsor - Average",
    "Mortgage Lending & Housing - Co-Sponsor", "Mortgage Lending & Housing - Success Rate",
    "Mortgage Lending & Housing - Sponsor - Success Rate", "Mortgage Lending & Housing - Original Co-Sponsor - Success Rate"
  )
  LEGIS_WEIGHTS <- c(
    0, 0,
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Examination & Supervision
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0.7142857142857143, 0, 0,  # Credit Union Capital Requirements
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0.7142857142857143, 0, 0,  # NCUA Budget & Share Insurance Fund
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Interchange
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Payments
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Technology & Emerging Issues
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Fraud Prevention
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Data Privacy & Cybersecurity
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Charter Modernization & Governance
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Defense Credit Union Issues
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Field of Membership
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # CDFI Fund
    0.285714285714286, 0, 0.142857142857143, 0, 0.07142857142857144, 0, 0, 0,  # CFPB Issues & Structural Reform
    0.2857142857142858, 0, 0.1428571428571429, 0, 0, 0, 0, 0,  # Credit Card & Consumer-Fee Mandates
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Telephone Consumer Protection Act Issues
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0,  # Member Business Lending
    0.285714285714286, 0, 0.142857142857143, 0, 0.0714285714285714, 0, 0, 0  # Mortgage Lending & Housing
  )

  past_intro <- function(la) !is.na(la) & la != "Introduced"

  # The 8 metrics for one member within one section, in sheet column order:
  #   1 Sponsor count             (DECAY-weighted)
  #   2 Avg cosponsors | sponsor   (plain mean, NOT decayed)
  #   3 Original-cosponsor count  (DECAY-weighted)
  #   4 Avg cosponsors | orig      (plain mean, NOT decayed)
  #   5 Cosponsor count           (DECAY-weighted)
  #   6 GENERAL Success Rate = mean(Sponsor success, Orig-cosponsor success); an
  #     empty role counts as 0% -- matches the reference sheet's "Success Rate".
  #   7 Sponsor Success (plain %)
  #   8 Orig-cosponsor Success (plain %)
  member_section_block <- function(mb, key) {
    d  <- mb[mb$SectionKey == key, , drop = FALSE]
    S  <- d[d$Role == "sponsor", , drop = FALSE]
    O  <- d[d$Role == "original-cosponsor", , drop = FALSE]
    Cc <- d[d$Role == "cosponsor", , drop = FALSE]
    wsum <- function(x) if (nrow(x) == 0) 0 else round(sum(x$DecayWeight, na.rm = TRUE), 4)
    avgc <- function(x) if (nrow(x) == 0 || all(is.na(x$CosponsorCount))) 0 else
                          round(mean(x$CosponsorCount, na.rm = TRUE), 2)
    succ <- function(x) if (nrow(x) == 0) 0 else round(100 * mean(past_intro(x$LastAction)), 1)
    succ_S  <- succ(S); succ_O <- succ(O)
    # general = average of the two DISPLAYED rates, so on the sheet col6 equals
    # AVERAGE(col7, col8) exactly (an empty role counts as 0%).
    general <- round((succ_S + succ_O) / 2, 1)
    c(wsum(S), avgc(S), wsum(O), avgc(O), wsum(Cc), general, succ_S, succ_O)
  }

  section_keys <- vapply(SECTION_REGISTRY, function(s) s$key, character(1))

  score_mat <- matrix(0, nrow = length(members), ncol = length(section_keys) * 8L)
  for (i in seq_along(members)) {
    mb   <- Bills[Bills$Member == members[i], , drop = FALSE]
    vals <- numeric(0)
    for (key in section_keys) vals <- c(vals, member_section_block(mb, key))
    score_mat[i, ] <- vals
  }

  # District/State (col B) from the roster, joined by the same display name.
  roster_meta    <- get_roster_meta_119()
  ds_lookup      <- setNames(roster_meta$DistrictState, roster_meta$Member)
  district_state <- unname(ds_lookup[members]); district_state[is.na(district_state)] <- ""

  # Assemble the 143-col sheet: writexl writes row1 = headers; the first data row
  # is the Weight row; rows after that are one per member in pinned-roster order.
  n_score <- ncol(score_mat)
  legis <- vector("list", length(LEGIS_HEADERS))
  names(legis) <- LEGIS_HEADERS
  legis[[1]] <- c("Weight", members)              # A: Names
  legis[[2]] <- c(NA, district_state)             # B: District/State
  for (j in seq_len(n_score)) legis[[2L + j]] <- c(LEGIS_WEIGHTS[2L + j], score_mat[, j])
  if ((2L + n_score) < length(LEGIS_HEADERS)) {
    for (j in (2L + n_score + 1L):length(LEGIS_HEADERS)) {
      legis[[j]] <- c(LEGIS_WEIGHTS[j], rep(NA_real_, length(members)))  # committee/leadership: not scraped
    }
  }
  legis_df <- as.data.frame(legis, check.names = FALSE, stringsAsFactors = FALSE)

  # ===============================================================
  # OUTPUT: ONE workbook -- the wide "Legislative Score - Raw" sheet + the
  # individual interactions archived as tabs (all + one per role, for the
  # later dashboard). Date = Congress only (no separate date scrape).
  # ===============================================================
  interaction_cols <- c("Section", "Role", "Member", "Name", "Title", "Sponsor",
                        "CosponsorCount", "Committee", "LastAction", "Congress",
                        "DecayWeight", "DetailLink", "bill_summary")
  arch <- if (nrow(Bills) > 0)
            Bills[, interaction_cols[interaction_cols %in% names(Bills)], drop = FALSE]
          else Bills
  role_tab <- function(role) if (nrow(arch) > 0) arch[Bills$Role == role, , drop = FALSE] else arch
  # "Successful" = the bill advanced PAST INTRODUCTION, split by role to match the
  # Sponsor Success / Original Co-Sponsor Success score columns. Each row carries
  # its Section (= group/topic tag) and Role.
  succ_tab <- function(role) if (nrow(arch) > 0)
                arch[Bills$Role == role & past_intro(Bills$LastAction), , drop = FALSE] else arch

  # The interaction database: Legislative Score - Raw + the 5 bill-interaction pages.
  out <- list(
    `Legislative Score - Raw`      = legis_df,
    `Sponsor Bills`                = role_tab("sponsor"),
    `Original Co-sponsor`          = role_tab("original-cosponsor"),
    `Co-sponsor`                   = role_tab("cosponsor"),
    `Successful - Sponsor`         = succ_tab("sponsor"),
    `Successful - Orig Co-sponsor` = succ_tab("original-cosponsor")
  )
  out_path <- paste0("Moneyball_Legislative_Score_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".xlsx")
  write_xlsx(out, path = out_path)
  message("OUTPUT written: ", out_path, " | score ", length(members), "x", length(LEGIS_HEADERS),
          " | sponsor ", nrow(role_tab("sponsor")), " / orig ", nrow(role_tab("original-cosponsor")),
          " / cosponsor ", nrow(role_tab("cosponsor")),
          " | successful: sponsor ", nrow(succ_tab("sponsor")),
          " / orig ", nrow(succ_tab("original-cosponsor")))

} # end if (RUN_FULL) -- Stage 2.2

# ===============================================================
# STAGE 3 (optional): cosponsor network edges + centrality   [NEW]
# ===============================================================
# For each bill a member SPONSORS (the Role == "sponsor" rows already scraped),
# fetch its cosponsors page, read the cosponsors (#main a -> /member/ links),
# weight each tie (ORIGINAL cosponsor, marked with a trailing '*', = 1.0;
# REGULAR cosponsor = 0.5), and build a DIRECTED  sponsor -> cosponsor  weighted
# graph. Edge weight = summed ties across all of the sponsor's bills = how
# "close" the sponsor is to that member. Nodes are keyed by BIOGUIDE id so a
# member who both sponsors and cosponsors is ONE node (centrality stays valid).
# Output: congress_cosponsor_network_<ts>.xlsx  (Edges + Centrality).
#
# OFF by default. Enable ONLY after the main scrape is complete AND the
# cosponsor-page selectors are verified against a live bill (the '*' that marks
# an original cosponsor often sits just OUTSIDE the <a>, so we also read the
# surrounding cell text). Resumable via COSPONSOR_CKPT; safe to re-run.
RUN_COSPONSOR_EDGES  <- TRUE
COSPONSOR_CKPT       <- "congress_cosponsor_checkpoint.rds"
W_ORIGINAL_COSPONSOR <- 1.0
W_REGULAR_COSPONSOR  <- 0.5

# --- Phase 1 high-resolution edge weighting (success / size / decay) --------
# Each sponsor->cosponsor tie on bill b is weighted:
#   w = role(1.0 orig / 0.5 reg) * SUCCESS * DECAY / sizenorm(C)
# where C = # cosponsors on b. Tunable dials (analyst's call):
SUCCESS_MULT   <- 3.0     # tie on a bill that PASSED its origin chamber is worth this x an un-passed one (base 1.0)
SIZE_NORM      <- "sqrt"  # "off" | "log" (1/log2(1+C)) | "sqrt" (1/sqrt C) | "newman" (1/C) -- discounts big multi-cosponsor bills
USE_BILL_DECAY <- TRUE    # multiply each tie by the bill's per-congress DecayWeight (0.8^age)
# "passed its respective body" = LastAction reached floor passage of its origin
# chamber (Became Law / veto imply origin-chamber passage; everything beyond caps
# at the same level). Regex is robust to raw-tracker + classified labels.
PASSED_RE          <- "passed|agreed to in|became.*law|public law|to president|resolving differences|veto"
passed_own_chamber <- function(la) !is.na(la) & grepl(PASSED_RE, la, ignore.case = TRUE)
sizenorm_factor    <- function(C) switch(SIZE_NORM, off = 1, log = 1/log2(1 + C), sqrt = 1/sqrt(C), newman = 1/C, 1)

# Combined influence score (Stage 3): a single normalized 0-100 ranking blending
# coalition LEADERSHIP (weighted out-degree -- bills you sponsor that others
# join), BROKERAGE (betweenness -- bridging otherwise-separate clusters), and a
# smaller PRESTIGE term (eigenvector -- the in-direction "sought-after cosponsor"
# signal). Each component is min-max normalized BEFORE weighting, so their very
# different scales don't let one column dominate. Weights need not sum to 1 (the
# result is rescaled), but keeping them at 1 lets you read each as a share of the
# blend. Out-degree leads, per the directed sponsor->cosponsor semantics. Only
# components present in `cent` are used (if igraph is unavailable, just
# WeightedOutDegree survives), with weights renormalized over whatever is present.
INFLUENCE_WEIGHTS <- c(
  WeightedOutDegree = 0.60,
  Betweenness       = 0.25,
  Eigenvector       = 0.15
)

# Display name -> bioguide id, from the same roster CSV (for sponsor node ids).
get_member_bioguide <- function(types = c("rep", "sen")) {
  csv_url <- "https://unitedstates.github.io/congress-legislators/legislators-current.csv"
  df <- tryCatch(read.csv(url(csv_url), stringsAsFactors = FALSE, encoding = "UTF-8"),
                 error = function(e) NULL)
  if (is.null(df) || !("bioguide_id" %in% names(df)))
    return(setNames(character(0), character(0)))
  if ("type" %in% names(df)) df <- df[df$type %in% types, , drop = FALSE]
  off <- if ("full_name" %in% names(df)) df$full_name else rep(NA_character_, nrow(df))
  nm  <- mapply(construct_display_name, off, df$first_name, df$last_name, USE.NAMES = FALSE)
  v <- df$bioguide_id; names(v) <- nm
  v[nzchar(nm) & !duplicated(nm)]
}

# Bill DetailLink -> its cosponsors page URL (== clicking the "li:nth-child(6) a" tab).
cosponsors_url <- function(detail_link) {
  if (is.na(detail_link) || !nzchar(detail_link)) return(NA_character_)
  u <- detail_link
  if (!grepl("^http", u)) u <- paste0("https://www.congress.gov", u)
  u <- sub("\\?.*$", "", u); u <- sub("/+$", "", u)
  if (!grepl("/cosponsors$", u)) u <- paste0(u, "/cosponsors")
  u
}

# Parse one cosponsors page -> data.frame(cosponsor, cosponsor_bioguide, original).
# Original cosponsors carry a trailing '*'; it usually sits in the surrounding
# cell rather than the link text, so we test both.
parse_cosponsors_page <- function(pg) {
  nodes <- tryCatch(html_elements(pg, "#main a"), error = function(e) NULL)
  if (is.null(nodes) || length(nodes) == 0) return(NULL)
  href  <- html_attr(nodes, "href")
  keep  <- !is.na(href) & grepl("/member/", href)
  nodes <- nodes[keep]; href <- href[keep]
  if (length(nodes) == 0) return(NULL)
  rows <- lapply(seq_along(nodes), function(i) {
    nm <- trimws(html_text(nodes[[i]]))
    bg <- regmatches(href[i], regexpr("[A-Z][0-9]{6}", href[i]))
    bg <- if (length(bg) == 1) bg else NA_character_
    cell <- tryCatch(trimws(html_text(xml2::xml_parent(nodes[[i]]))),
                     error = function(e) nm)
    orig <- grepl("\\*\\s*$", cell) || grepl("\\*\\s*$", nm)
    data.frame(cosponsor = nm, cosponsor_bioguide = bg, original = orig,
               stringsAsFactors = FALSE)
  })
  d   <- do.call(rbind, rows)
  d   <- d[nzchar(d$cosponsor), , drop = FALSE]
  key <- ifelse(is.na(d$cosponsor_bioguide), d$cosponsor, d$cosponsor_bioguide)
  d[!duplicated(key), , drop = FALSE]
}

# Fetch + parse one bill's cosponsors page (cookie-replay; "CHALLENGED" bubbles up).
scrape_cosponsors <- function(detail_link, cf = CF_SESSION) {
  u <- cosponsors_url(detail_link)
  if (is.na(u)) return(NULL)
  Sys.sleep(runif(1, HTTP_PAUSE[1], HTTP_PAUSE[2]))
  pg <- if (identical(FETCH_MODE, "http")) fetch_html_http(u, "cosponsors", cf = cf)
        else fetch_rendered_html(u, "cosponsors")
  if (identical(pg, "CHALLENGED")) return("CHALLENGED")
  if (!inherits(pg, "xml_document")) return(NULL)
  res <- parse_cosponsors_page(pg)
  if (is.null(res))
    data.frame(cosponsor = character(), cosponsor_bioguide = character(),
               original = logical(), stringsAsFactors = FALSE)
  else res
}

if (RUN_FULL && RUN_COSPONSOR_EDGES && exists("Bills") && is.data.frame(Bills) && nrow(Bills) > 0) {

  handlers("txtprogressbar")
  message("\n[Stage 3] Cosponsor network: gathering sponsored bills ...")
  spon <- Bills[Bills$Role == "sponsor" & !is.na(Bills$DetailLink) & nzchar(Bills$DetailLink),
                c("Member", "Name", "DetailLink", "LastAction", "Congress", "DecayWeight"), drop = FALSE]
  spon <- spon[!duplicated(spon$DetailLink), , drop = FALSE]
  message("  ", nrow(spon), " distinct sponsored bills to pull cosponsors for")
  message(sprintf("  [weighting] success x%.1f (passed-own-chamber) | size-norm '%s' | decay %s",
                  SUCCESS_MULT, SIZE_NORM, if (USE_BILL_DECAY) "on" else "off"))

  bg_map       <- tryCatch(get_member_bioguide(), error = function(e) setNames(character(0), character(0)))
  sponsor_node <- function(member) { b <- unname(bg_map[member]); if (length(b) == 1 && !is.na(b) && nzchar(b)) b else member }

  # ---- resumable fetch of cosponsor pages ----
  cc   <- if (file.exists(COSPONSOR_CKPT)) readRDS(COSPONSOR_CKPT) else list()
  links <- spon$DetailLink
  todo  <- setdiff(links, names(cc))
  message("  ", length(todo), " to fetch (", length(links) - length(todo), " cached)")

  fetch_cos_round <- function(lnks, cf) {
    with_progress({
      p <- progressor(steps = length(lnks))
      future_lapply(lnks, function(lnk, cf) { out <- scrape_cosponsors(lnk, cf = cf); p(); out },
                    cf = cf, future.seed = TRUE)
    })
  }
  is_chal <- function(x) identical(x, "CHALLENGED")

  if (length(todo) > 0) {
    if (!identical(FETCH_MODE, "http")) init_browser()
    res <- fetch_cos_round(todo, CF_SESSION); names(res) <- todo
    chal <- names(res)[vapply(res, is_chal, logical(1))]
    if (length(chal) > 0 && identical(FETCH_MODE, "http")) {
      message("  ", length(chal), " challenged -> re-harvest + retry")
      harvest_cf_session()
      r2 <- fetch_cos_round(chal, CF_SESSION); names(r2) <- chal
      res[chal] <- r2
    }
    for (k in names(res)) if (!is_chal(res[[k]])) cc[[k]] <- res[[k]]
    saveRDS(cc, COSPONSOR_CKPT)
    still <- names(res)[vapply(res, is_chal, logical(1))]
    if (length(still) > 0) message("  ", length(still), " still challenged -- left for a later re-run")
  }

  # ---- build directed edges  sponsor -> cosponsor ----
  edge_rows <- list()
  for (i in seq_len(nrow(spon))) {
    cdf <- cc[[spon$DetailLink[i]]]
    if (is.null(cdf) || !is.data.frame(cdf) || nrow(cdf) == 0) next
    from_id <- sponsor_node(spon$Member[i])
    # ---- per-bill weighting factors: success x decay / size ----
    C_b     <- nrow(cdf)                                          # # cosponsors on this bill
    f_succ  <- if (passed_own_chamber(spon$LastAction[i])) SUCCESS_MULT else 1
    f_decay <- if (USE_BILL_DECAY) { d <- suppressWarnings(as.numeric(spon$DecayWeight[i])); if (is.finite(d)) d else 1 } else 1
    f_bill  <- f_succ * f_decay * sizenorm_factor(C_b)
    for (j in seq_len(nrow(cdf))) {
      to_id <- if (!is.na(cdf$cosponsor_bioguide[j]) && nzchar(cdf$cosponsor_bioguide[j]))
                 cdf$cosponsor_bioguide[j] else cdf$cosponsor[j]
      if (identical(to_id, from_id)) next                 # drop self-loops
      role_w <- if (isTRUE(cdf$original[j])) W_ORIGINAL_COSPONSOR else W_REGULAR_COSPONSOR
      edge_rows[[length(edge_rows) + 1L]] <- data.frame(
        From = from_id, To = to_id, From_name = spon$Member[i], To_name = cdf$cosponsor[j],
        weight = role_w * f_bill,
        original = isTRUE(cdf$original[j]), stringsAsFactors = FALSE)
    }
  }

  if (length(edge_rows) == 0) {
    warning("[Stage 3] No cosponsor edges built -- check selectors / that pages were fetched.")
  } else {
    e <- bind_rows(edge_rows)
    n_orig <- sum(e$original)
    if (n_orig == 0)
      warning("[Stage 3] 0 ORIGINAL cosponsors detected across ALL bills -- the '*' detection ",
              "likely missed; verify the cosponsors-page markup before trusting the weights.")

    edges <- e %>% group_by(From, To) %>%
      summarise(Weight = sum(weight), NBills = n(),
                NOriginal = sum(original), NRegular = sum(!original), .groups = "drop") %>%
      as.data.frame()

    lbl      <- setNames(names(bg_map), unname(bg_map))          # bioguide -> roster name
    seen     <- unique(rbind(data.frame(id = e$From, name = e$From_name, stringsAsFactors = FALSE),
                             data.frame(id = e$To,   name = e$To_name,   stringsAsFactors = FALSE)))
    seen_lbl <- setNames(seen$name, seen$id)
    node_label <- function(id) { l <- unname(lbl[id]); if (length(l) == 1 && !is.na(l) && nzchar(l)) l else unname(seen_lbl[id]) }
    edges$From_label <- vapply(edges$From, node_label, character(1))
    edges$To_label   <- vapply(edges$To,   node_label, character(1))

    # ---- directed centrality ----
    cent <- data.frame(node = unique(c(edges$From, edges$To)), stringsAsFactors = FALSE)
    cent$label <- vapply(cent$node, node_label, character(1))
    if (requireNamespace("igraph", quietly = TRUE)) {
      g    <- igraph::graph_from_data_frame(edges[, c("From", "To", "Weight")], directed = TRUE)
      W    <- igraph::E(g)$Weight
      dist <- 1 / W                       # path metrics treat weight as DISTANCE: stronger tie = closer
      m    <- match(cent$node, igraph::V(g)$name)
      cent$WeightedOutDegree <- igraph::strength(g, mode = "out", weights = W)[m]
      cent$WeightedInDegree  <- igraph::strength(g, mode = "in",  weights = W)[m]
      cent$OutDegree   <- igraph::degree(g, mode = "out")[m]
      cent$InDegree    <- igraph::degree(g, mode = "in")[m]
      cent$Closeness   <- suppressWarnings(igraph::closeness(g, mode = "out", weights = dist)[m])
      cent$Betweenness <- suppressWarnings(igraph::betweenness(g, directed = TRUE, weights = dist)[m])
      cent$Eigenvector <- suppressWarnings(igraph::eigen_centrality(g, directed = TRUE, weights = W)$vector[m])
      cent$PageRank    <- suppressWarnings(igraph::page_rank(g, directed = TRUE, weights = W)$vector[m])
    } else {
      warning("[Stage 3] igraph unavailable -- writing weighted degree only.")
      od <- tapply(edges$Weight, edges$From, sum); idg <- tapply(edges$Weight, edges$To, sum)
      cent$WeightedOutDegree <- ifelse(is.na(od[cent$node]),  0, od[cent$node])
      cent$WeightedInDegree  <- ifelse(is.na(idg[cent$node]), 0, idg[cent$node])
    }
    # ---- combined influence score ----
    # Min-max normalize each component to [0,1] across nodes, weight + sum, then
    # rescale to 0-100. norm01 also flattens NA/NaN/Inf (igraph hands back NaN
    # betweenness/closeness for disconnected nodes) to 0 so they don't poison the
    # blend. Weights are renormalized over the components that actually exist.
    norm01 <- function(x) {
      x <- as.numeric(x); x[!is.finite(x)] <- NA_real_
      lo <- suppressWarnings(min(x, na.rm = TRUE)); hi <- suppressWarnings(max(x, na.rm = TRUE))
      if (!is.finite(lo) || !is.finite(hi) || hi <= lo) return(rep(0, length(x)))
      out <- (x - lo) / (hi - lo); out[is.na(out)] <- 0; out
    }
    comp_w <- INFLUENCE_WEIGHTS[names(INFLUENCE_WEIGHTS) %in% names(cent)]
    if (length(comp_w) > 0 && nrow(cent) > 0) {
      comp_w <- comp_w / sum(comp_w)
      score_mat <- matrix(0, nrow = nrow(cent), ncol = length(comp_w))
      for (k in seq_along(comp_w))
        score_mat[, k] <- norm01(cent[[names(comp_w)[k]]]) * comp_w[k]
      cent$InfluenceScore <- round(100 * norm01(rowSums(score_mat)), 1)
    } else {
      cent$InfluenceScore <- NA_real_
    }

    # InfluenceScore is the headline -> put it up front and sort by it
    # (WeightedOutDegree breaks ties, preserving the old leadership ordering).
    lead <- c("node", "label", "InfluenceScore")
    cent <- cent[, c(lead, setdiff(names(cent), lead)), drop = FALSE]
    cent <- cent[order(-cent$InfluenceScore, -cent$WeightedOutDegree), , drop = FALSE]

    ts       <- format(Sys.time(), "%Y%m%d_%H%M%S")
    net_path <- paste0("congress_cosponsor_network_", ts, ".xlsx")
    write_xlsx(list(Edges = edges, Centrality = cent), path = net_path)
    message("[Stage 3] wrote ", net_path, " | edges: ", nrow(edges),
            " | nodes: ", nrow(cent), " | original ties: ", n_orig)

    # Also print the `cent` (Centrality) tab on its own as a standalone workbook.
    cent_path <- paste0("congress_centrality_", ts, ".xlsx")
    write_xlsx(list(Centrality = cent), path = cent_path)
    top <- if (nrow(cent) > 0) paste0(" | top: ", cent$label[1], " (", cent$InfluenceScore[1], ")") else ""
    message("[Stage 3] wrote ", cent_path, " | Centrality tab only (", nrow(cent), " nodes)", top)
  }
} # end Stage 3
