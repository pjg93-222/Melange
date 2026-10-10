script_argument <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
stopifnot(length(script_argument) == 1L)
script_path <- normalizePath(
  sub("^--file=", "", script_argument[[1L]]),
  winslash = "/",
  mustWork = TRUE
)
scraper_path <- normalizePath(
  file.path(dirname(script_path), "..", "..", "cspan", "cspan_scrape.R"),
  winslash = "/",
  mustWork = TRUE
)

# cspan_scrape.R is a script that runs a command on load, so evaluate only the
# functions under test. Nothing here starts a browser, ffmpeg, or the network.
scraper <- new.env()
for (expression in parse(scraper_path, keep.source = FALSE)) {
  if (
    is.call(expression) &&
      identical(as.character(expression[[1L]]), "<-") &&
      as.character(expression[[2L]])[[1L]] %in%
        c("media_url_for", "log_msg", "is_web_media_url", "download_audio")
  ) {
    eval(expression, scraper)
  }
}
stopifnot(is.function(scraper$is_web_media_url), is.function(scraper$download_audio))

accepted <- c(
  "https://m3u8-0.c-spanvideo.org/program/program.123.tsc.m3u8",
  "http://m3u8-0.c-spanvideo.org/program/program.123.tsc.m3u8",
  "HTTPS://cdn.example.org/a.mp4?token=abc&exp=1"
)
rejected <- list(
  "file:///C:/Windows/win.ini",
  "concat:file:///C:/a.ts|https://x.org/b.ts",
  "subfile,,start,0,end,0,,:C:/a.ts",
  "ftp://example.org/a.mp3",
  "//example.org/a.mp4",
  "javascript:alert(1)",
  " https://example.org/a.mp4",
  "https://example.org/a b.mp4",
  "https://example.org/a\".mp4",
  "https://example.org/a\\",
  "https://example.org/a\\b.mp4",
  "https://example.org/a\nfile:///etc/passwd",
  "https://",
  "",
  NA_character_,
  NULL,
  c("https://example.org/a", "https://example.org/b"),
  42L
)
stopifnot(
  all(vapply(accepted, scraper$is_web_media_url, logical(1L))),
  !any(vapply(rejected, scraper$is_web_media_url, logical(1L)))
)

# download_audio: a refused URL never reaches ffmpeg; an accepted one reaches it
# with the protocol whitelist placed before -i. system2 is stubbed to record calls.
calls <- list()
scraper$OUT <- tempfile("cspan-test-")
scraper$FFMPEG <- "ffmpeg-not-run"
scraper$UA <- "test-agent"
scraper$has_flag <- function(name) FALSE
scraper$system2 <- function(command, args, ...) {
  calls[[length(calls) + 1L]] <<- args
  1L
}
environment(scraper$download_audio) <- scraper
scraper$log_msg <- function(...) invisible(NULL)

for (url in c("file:///C:/Windows/win.ini", "concat:a|b", "ftp://example.org/a.mp3")) {
  scraper$download_audio("p1", url)
}
stopifnot(identical(length(calls), 0L), !dir.exists(file.path(scraper$OUT, "audio")))

scraper$download_audio("p1", "https://m3u8-0.c-spanvideo.org/program/program.1.tsc.m3u8")
stopifnot(identical(length(calls), 1L))
args <- gsub("^\"|\"$|^'|'$", "", calls[[1L]])
whitelist <- match("-protocol_whitelist", args)
input <- match("-i", args)
stopifnot(
  !is.na(whitelist),
  !is.na(input),
  whitelist < input,
  identical(args[[whitelist + 1L]], "https,tls,tcp,crypto,http"),
  identical(args[[input + 1L]], "https://m3u8-0.c-spanvideo.org/program/program.1.tsc.m3u8")
)
unlink(scraper$OUT, recursive = TRUE)

cat("test_cspan_media_url: only http(s) media URLs accepted\n")
cat("test_cspan_media_url: refused URLs never reach ffmpeg\n")
cat("test_cspan_media_url: protocol whitelist precedes -i\n")
cat("test_cspan_media_url: PASS\n")
