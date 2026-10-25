# Pure fixture test of terminal_nonarticle_reason(): evaluate only that function's definition from the producer, never
# its driver. The URLs are real ones from the 2026-10-18 press run's failed-body list (body_unavailable_after_network_retry).
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 1L)
if (!exists("%||%")) `%||%` <- function(x, y) if (is.null(x)) y else x
definition <- Filter(function(expr) is.call(expr) && identical(expr[[1]], as.name("<-")) &&
                       identical(expr[[2]], as.name("terminal_nonarticle_reason")), as.list(parse(file = args[[1]])))
stopifnot(length(definition) == 1L)
eval(definition[[1]], envir = globalenv())

expect <- function(reason, urls) for (url in urls)
  if (!identical(terminal_nonarticle_reason(url), reason))
    stop("expected '", reason, "' for ", url, " but got '", terminal_nonarticle_reason(url), "'")

# Elementor / JetEngine widget names and jQuery event names, scraped out of inline JS as if they were links
# (63 on fetterman, 41 on schmitt, 2 on bluntrochester in the failed list).
fet <- "https://www.fetterman.senate.gov/press-releases/fetterman-pushes-for-safer-pedestrian-friendly-streets-in-new-letters-to-federal-agencies"
expect("page_builder_widget_hook", c(
  paste0("https://www.fetterman.senate.gov/press-releases/casey-fetterman-announce-340-million-for-philadelphia-water-infrastructure-lead-pipe-replacement/text-editor.default"),
  paste0(fet, "/ha-skills.default"), paste0(fet, "/image-carousel.default"), paste0(fet, "/nested-tabs.default"),
  paste0(fet, "/wp-widget-media_audio.default"), paste0(fet, "/jet-popup-mailchimp.default"),
  paste0(fet, "/blur.validate-equalTo"), paste0(fet, "/invalid-form.validate"), paste0(fet, "/reset.ui-form-reset"),
  paste0(fet, "/frontend.element-ready"), paste0(fet, "/jet-popup/ajax/frontend-init"),
  paste0(fet, "/jet-popup/render-content/show-content"), paste0(fet, "/jet-ajax-search/show-results"),
  paste0(fet, "/jet-search/search-suggestions"), paste0(fet, "/elementor/frontend/documents-manager/init-classes"),
  paste0(fet, "/get-style-property/get-style-property"), paste0(fet, "/matches-selector/matches-selector"),
  "https://www.schmitt.senate.gov/media/press-releases/2/eael-advanced-search.default",
  "https://www.schmitt.senate.gov/media/press-releases/2/frontend/element_ready/eael-advanced-search.default",
  "https://www.bluntrochester.senate.gov/media/press-releases/frontend/element_ready/eael-advanced-search.default",
  "https://www.lankford.senate.gov/jet-popup/press-release-filter",
  "HTTPS://WWW.SCHMITT.SENATE.GOV/MEDIA/PRESS-RELEASES/2/EAEL-ADVANCED-SEARCH.DEFAULT?X=1#frag"))

# babin.house.gov: a document href with another member's press URL concatenated after the extension (26 in the failed list).
expect("document_or_media_asset", c(
  "https://babin.house.gov/uploadedfiles/hs_approps-babin.pdfhttp://mcgovern.house.gov/media-center/press-releases",
  "https://babin.house.gov/uploadedfiles/babin_refugee_cr_letter_final.pdfhttp://boustany.house.gov/114th-congress/boustany-abraham-and-graves-tell-senate-to-act-on-refugee-security/https://abraham.house.gov/media-center/press-releases/abraham-votes-against-omnibus",
  "https://babin.house.gov/uploadedfiles/hs_approps-babin.pdfhttps://ratcliffe.house.gov/media-center/press-releases/ratcliffe-votes-no-fy-2016-funding-package[610"))

# Everything that was retryable stays retryable: real articles, truncated slugs, IQ-CMS document pages, slugs that merely
# contain a trigger word, and the listing pages the route work does not claim.
expect("", c(
  "https://www.husted.senate.gov/media/press-releases/democrats-block-husteds-bill-forcing-data-centers-to-pay-their-own-way",
  "https://kiggans.house.gov/2026/09/14/kiggans-bill-to-ensure-proper-lifeguard-staffing-on-public-beaches-passes-the-house-with-bipartisan-support/",
  "https://takano.house.gov/media-center/press-releases/rep-takano-votes-no-on-house-republican-budget",
  "https://www.schmitt.senate.gov/media/press-releases/senator-schmitt-introduces-the-gateway-",
  "https://www.lankford.senate.gov/news/press-releases/lankford-subcommittee-examines-judicial-review-in-federal-regulatory-processnttnt",
  "https://babin.house.gov/news/documentsingle.aspx?DocumentID=401234",
  "https://www.example.senate.gov/press-releases/senators-warn-of-default-on-debt",
  "https://www.example.senate.gov/press-releases/elementor-workers-union-statement",
  "https://www.example.senate.gov/press-releases/jet-popup-vendor-update",
  "https://www.example.senate.gov/press-releases/validate-the-election-results",
  "https://www.fetterman.senate.gov/press-releases/defense-foreign-affairs"))

# The pre-existing rules are untouched.
expect("document_or_media_asset", c("https://www.example.senate.gov/uploads/letter.pdf",
                                    "https://www.example.senate.gov/press-releases/slug/photo.png"))
expect("nested_press_release_media_asset",
       "https://www.bluntrochester.senate.gov/news/press-releases/some-release/screenshot-2025-02-12-at-9-04-32-pm")
expect("nonarticle_service_page", "https://www.example.senate.gov/services/help")
expect("listing_or_feed_page", "https://www.example.senate.gov/press-releases/category/health")
stopifnot(identical(terminal_nonarticle_reason(NULL), ""), identical(terminal_nonarticle_reason(NA_character_), ""))
# ---- The classification also guards the materialize step, whichever path fed it (live walk or --retry-from): a terminal
# non-article that reaches the body partitions is never a failed body, never title-fallback scored, and is handed back for the
# terminal artifacts. (--score-only re-reads a sealed fulltext and keeps its partitions exactly as sealed.)
grab <- function(name) {
  hit <- Filter(function(expr) is.call(expr) && identical(expr[[1]], as.name("<-")) && identical(expr[[2]], as.name(name)),
                as.list(parse(file = args[[1]])))
  stopifnot(length(hit) == 1L)
  hit[[1]]
}
producer <- new.env(parent = globalenv())
producer$`%||%` <- `%||%`
for (name in c("canonical_url", "terminal_nonarticle_reason", "split_terminal_nonarticles", "materialize_press_outputs",
               "merge_late_terminal")) eval(grab(name), envir = producer)
producer$run_root <- tempfile("late-terminal-")
dir.create(producer$run_root)
producer$DATE_FLOOR <- as.Date("2026-06-25")
producer$write_rds_atomic <- function(frame, path) saveRDS(frame, path)
producer$write_csv_atomic <- function(frame, path) utils::write.csv(frame, path, row.names = FALSE)
words30 <- paste(rep("credit unions serve members across every district", 5L), collapse = " ")
full <- data.frame(
  url = c("https://www.husted.senate.gov/media/press-releases/real-article",
          "https://www.husted.senate.gov/media/press-releases/real-but-empty",
          "https://www.fetterman.senate.gov/press-releases/x/text-editor.default",
          "https://babin.house.gov/uploadedfiles/hs.pdfhttp://huffman.house.gov/media-center/press-releases/rep-huffman-25#H001068"),
  bioguide = c("H001104", "H001104", "F000479", "H001068"),
  title = c("Credit union relief act", "Credit union shell title", "text editor.default", "rep huffman 25 members of congress"),
  body = c(words30, "", "", paste(rep("rep huffman 25 members of congress urge", 5L), collapse = " ")),
  source = c(NA, NA, NA, "OFFICIAL_MENTION"),
  date_final = as.Date(c("2026-09-30", NA, NA, NA)), stringsAsFactors = FALSE)
out <- producer$materialize_press_outputs(full, "after_network_retry")
stopifnot(nrow(out$terminal_late) == 2L,
          setequal(out$terminal_late$terminal_reason, c("page_builder_widget_hook", "document_or_media_asset")),
          setequal(out$fulltext$url, full$url[1:2]), identical(out$articles$url, full$url[[1]]),
          identical(out$failed_bodies$url, full$url[[2]]),
          identical(out$failed_bodies$collection_status, "body_unavailable_after_network_retry"),
          nrow(out$article_mentions) == 0L, setequal(out$scorable$url, full$url[1:2]),
          identical(out$scorable$body_fallback[out$scorable$url == full$url[[2]]], "title"),
          !any(grepl("terminal_late", list.files(producer$run_root), fixed = TRUE)))
sealed <- producer$materialize_press_outputs(full, "after_network_retry", rewrite_fulltext = FALSE)
stopifnot(nrow(sealed$terminal_late) == 0L, nrow(sealed$fulltext) == 4L, nrow(sealed$failed_bodies) == 2L)
none <- producer$materialize_press_outputs(full[1, ], "after_network_retry")
stopifnot(nrow(none$terminal_late) == 0L, nrow(none$fulltext) == 1L)

# The late rows join the terminal artifacts (deduplicated by url + member) and the caller learns the new total for the receipt.
earlier <- data.frame(url = "https://www.schmitt.senate.gov/media/press-releases/2/eael-advanced-search.default",
                      bioguide = "S001227", terminal_reason = "page_builder_widget_hook", stringsAsFactors = FALSE)
producer$write_rds_atomic(earlier, file.path(producer$run_root, "press_delta_terminal_nonarticles.rds"))
producer$write_csv_atomic(earlier, file.path(producer$run_root, "press_delta_terminal_nonarticles.csv"))
total <- suppressMessages(producer$merge_late_terminal(out$terminal_late))
written <- utils::read.csv(file.path(producer$run_root, "press_delta_terminal_nonarticles.csv"), stringsAsFactors = FALSE)
stopifnot(identical(total, 3L), nrow(written) == 3L, all(nzchar(written$terminal_reason)),
          identical(readRDS(file.path(producer$run_root, "press_delta_terminal_nonarticles.rds"))$url, written$url))
stopifnot(identical(suppressMessages(producer$merge_late_terminal(out$terminal_late)), 3L))     # idempotent
cat("PASS: terminal non-article rules\n")
