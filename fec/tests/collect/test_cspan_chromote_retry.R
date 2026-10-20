# Private fixtures only (no Chrome, no network): parse the scraper's function definitions without running
# its driver, then replace the chromote primitive and the clock before invoking them.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 1L)
definitions <- as.list(parse(file = args[[1]]))
functions <- c("log_msg", "js_val", "js_retry", "is_blocked", "nav_wait", "run_search")
definition <- function(name) {
  result <- Filter(function(expr) is.call(expr) && identical(expr[[1]], as.name("<-")) &&
                     identical(expr[[2]], as.name(name)), definitions)
  stopifnot(length(result) == 1L)
  result[[1]]
}
check <- function(ok, label) { if (!isTRUE(ok)) stop("FAIL: ", label, call. = FALSE); cat("ok:", label, "\n") }
timeout_error <- function() stop("Timed out waiting for response to command Runtime.evaluate")

# `script`: one entry per chromote call -- TRUE/value = answer, "timeout" = the transient error --
# or a function(expr) giving the answer for that expression.
fixture <- function(script) {
  env <- new.env(parent = globalenv())
  for (name in functions) eval(definition(name), envir = env)
  state <- new.env(parent = emptyenv()); state$calls <- 0L; state$sleeps <- 0
  env$Sys.sleep <- function(seconds) state$sleeps <- state$sleeps + seconds
  env$js_val <- function(b, expr) {
    state$calls <- state$calls + 1L
    answer <- if (is.function(script)) script(expr)
              else if (length(script) >= state$calls) script[[state$calls]] else script[[length(script)]]
    if (identical(answer, "timeout")) timeout_error()
    answer
  }
  env$DELAY <- 0
  env$toJSON <- jsonlite::toJSON
  list(env = env, state = state)
}

# js_retry: a transient timeout is retried, a clean answer passes through untouched.
f <- fixture(list("timeout", "timeout", "complete"))
check(identical(f$env$js_retry(NULL, "document.readyState"), "complete"), "two timeouts then an answer recovers")
check(f$state$calls == 3L, "recovery took exactly three calls")

# js_retry: bounded, and exhaustion is a classed condition, not a bare R error.
f <- fixture(list("timeout"))
caught <- tryCatch(f$env$js_retry(NULL, "x"), chromote_exhausted = function(e) "exhausted", error = function(e) "bare")
check(identical(caught, "exhausted"), "exhaustion signals chromote_exhausted")
check(f$state$calls == 3L, "exhaustion stops after exactly three calls")

# is_blocked: transient timeout retried; exhaustion reads as blocked (so nav_wait backs off), never an error.
f <- fixture(list("timeout", TRUE))
check(isTRUE(f$env$is_blocked(NULL)), "is_blocked survives one timeout")
f <- fixture(list("timeout"))
check(isTRUE(f$env$is_blocked(NULL)), "is_blocked on exhaustion returns TRUE instead of raising")

# nav_wait: chromote dead the whole time -> FALSE (strict mode then exits 2), no uncaught error.
f <- fixture(function(expr) if (grepl("readyState", expr)) "complete" else "timeout")
f$env$log_msg <- function(...) invisible()
b <- list(Page = list(navigate = function(url, wait_) TRUE))
check(identical(f$env$nav_wait(b, "https://example.test/", tries = 2), FALSE), "nav_wait returns FALSE when is_blocked cannot run")

# run_search: the load-more clicks time out for good -> FALSE with a logged reason, not an uncaught error.
f <- fixture(function(expr) {   # the page loads and shows #loadmore, then every click times out
  if (grepl("showing", expr)) "" else if (grepl("length", expr)) 5L
  else if (grepl("offsetParent", expr)) TRUE else "timeout"
})
env <- f$env
logged <- character()
env$log_msg <- function(...) logged <<- c(logged, paste0(...))
env$flag <- function(name, default = NA) default
env$cspan_search_url <- function(since, until) "https://example.test/search"
env$DATE_SINCE <- "2026-10-12"; env$DATE_UNTIL <- "2026-10-18"
env$OUT <- tempfile("cspan-retry-"); dir.create(env$OUT)
env$MAXN <- NA_integer_; env$LOADMORE_DELAY <- 0
env$new_session <- function() list(close = function() invisible())
env$nav_wait <- function(...) TRUE
result <- tryCatch(env$run_search(), error = function(e) paste("uncaught:", conditionMessage(e)))
check(identical(result, FALSE), "run_search returns FALSE when chromote keeps timing out")
check(any(grepl("chromote", logged, ignore.case = TRUE)), "run_search logs why it gave up")
cat("PASS: cspan chromote retry\n")
