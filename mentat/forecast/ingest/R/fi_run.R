# The CLI paths of the ingest (FEEDS_SPEC 7.1): run_ingest.R parses the arguments and calls fi_main(). Every path - success,
# review-required, stopped, waiting, dry run, error - writes feeds.run.start and exactly one of feeds.run.done / feeds.run.fail to
# the Glass Box, writes a sha256 receipt, and never edits an inbox file, a registry or the refit's manifest (proposals only).
#
# Exit codes: 0 ok / waiting / dry run, 2 files need review, 3 stopped (blocked, gate closed, verification or calibration failed),
# 1 error.

FI_FEEDS <- c("ibisworld", "opensecrets-bulk", "opensecrets-pages", "opensecrets-fetch", "calibrate")

fi_parse_args <- function(args) {
  o <- list(feed = NULL, industry = NULL, dry_run = FALSE, run_id = NULL, refresh = FALSE)
  i <- 1L
  while (i <= length(args)) {
    a <- args[i]
    if (a == "--feed") { o$feed <- args[i + 1L]; i <- i + 2L }
    else if (a == "--industry") { o$industry <- args[i + 1L]; i <- i + 2L }
    else if (a == "--run-id") { o$run_id <- args[i + 1L]; i <- i + 2L }
    else if (a == "--dry-run") { o$dry_run <- TRUE; i <- i + 1L }
    else if (a == "--refresh") { o$refresh <- TRUE; i <- i + 1L }
    else stop("unknown argument: ", a, call. = FALSE)
  }
  if (is.null(o$feed) || is.na(o$feed) || !(o$feed %in% FI_FEEDS)) stop("--feed must be one of: ", paste(FI_FEEDS, collapse = ", "), call. = FALSE)
  o
}

.fi_say <- function(...) cat(paste0(..., "\n"), sep = "")

# Industries of the feeds registry that have the given block ("ibisworld" / "opensecrets"), optionally restricted to one id.
.fi_industries <- function(feeds, block, industry = NULL) {
  ids <- names(feeds$industries)
  ids <- ids[vapply(ids, function(i) !is.null(feeds$industries[[i]][[block]]), NA)]
  if (!is.null(industry)) {
    if (!(industry %in% names(feeds$industries))) stop("--industry ", industry, " is not in the feeds registry", call. = FALSE)
    ids <- intersect(ids, industry)
  }
  ids
}

# ---- IBISWorld ------------------------------------------------------------------------------------------------------------------

.fi_run_ibisworld <- function(ctx) {
  feeds <- ctx$feeds; rec <- ctx$rec; gb <- ctx$gb
  inbox_dir <- file.path(fi_inbox_dir(), "ibisworld")
  if (!ctx$dry_run) dir.create(inbox_dir, recursive = TRUE, showWarnings = FALSE)
  before <- fi_inbox_state(inbox_dir)
  scan <- fi_inbox_scan(inbox_dir, allowed = c("pdf", "xlsx"), ledger_path = file.path(fi_frt_dir(), "inbox_seen.json"), write = !ctx$dry_run)
  s <- attr(scan, "summary")
  gb$event("feeds.inbox.scan", "succeeded", "scan", sprintf("inbox scan: %d files, %d new, %d duplicate, %d unsupported", s$files, s$new, s$duplicate, s$unsupported), "", s)
  for (i in seq_len(nrow(scan))) fi_receipt_input(rec, scan[i, ])
  col <- fi_ibis_collect(scan, feeds, emit = function(kind, summary, metadata) gb$event(kind, "succeeded", "ibis", summary, "", metadata))
  fi_receipt_checks_df(rec, col$checks)
  ids <- .fi_industries(feeds, "ibisworld", ctx$industry)
  pred <- list(); act <- list(); waiting <- character(); replaced <- NA_character_
  cur <- file.path(fi_frt_dir(), "current.json")
  prev_actual <- if (file.exists(cur)) jsonlite::fromJSON(cur, simplifyVector = FALSE)[["ibis_actual_growth"]] else NULL
  for (id in ids) {
    cfg <- feeds$industries[[id]]
    if (identical(cfg$ibisworld$actual_vintage_policy, "pinned_workbook")) { fi_receipt_decision(rec, sprintf("%s: pinned_workbook - the workbook rows stay as they are; not part of this feed", id)); next }
    p <- fi_ibis_derive_predicted(col$editions, col$long, id, cfg)
    a <- fi_ibis_derive_actual(col$editions, col$long, id, cfg)
    pred[[id]] <- p; act[[id]] <- a
    vin <- attr(a, "vintage")
    if (isTRUE(attr(a, "waiting"))) waiting <- c(waiting, sprintf("%s (IBISWorld %s): waiting for owner file - no edition published %s or later in the inbox%s", id, cfg$ibisworld$code, cfg$ibisworld$actual_min_edition %||% "?",
                                                                 if (!is.na(vin)) sprintf("; history is the %s vintage through %s", vin, as.integer(substr(vin, 1, 4)) - 1L) else "; no edition at all"))
    if (!is.null(prev_actual) && file.exists(prev_actual$path)) {
      pa <- fi_read_csv(prev_actual$path); pv <- unique(pa$report_vintage[pa$sector == id])
      if (length(pv) && !is.na(vin) && !identical(pv[1], vin)) { replaced <- pv[1]; fi_receipt_decision(rec, sprintf("%s: the %s vintage replaces the whole %s history (no splicing)", id, vin, pv[1])) }
    }
    gb$event("feeds.derive", "succeeded", "derive", sprintf("%s: %d predicted rows, %d actual rows", id, nrow(p), nrow(a)), "",
             list(rows_06 = nrow(p), rows_07 = nrow(a), replaced_vintage = if (is.na(replaced)) NULL else replaced))
  }
  pred_df <- if (length(pred)) do.call(rbind, pred) else as.data.frame(stats::setNames(rep(list(logical()), length(FI_COLS_06)), FI_COLS_06))
  act_df <- if (length(act)) do.call(rbind, act) else as.data.frame(stats::setNames(rep(list(logical()), length(FI_COLS_07)), FI_COLS_07))
  n_checked <- sum(col$editions$status == "checked")
  needs_review <- col$editions[col$editions$status %in% c("review_required", "unregistered_code", "unsupported"), , drop = FALSE]
  for (i in seq_len(nrow(needs_review))) fi_receipt_issue(rec, sprintf("%s: %s (%s)", needs_review$inbox_name[i], needs_review$status[i], needs_review$issues[i]))
  after <- fi_inbox_state(inbox_dir)
  same <- identical(before, after)
  fi_receipt_check(rec, "inbox files unchanged (name, size, mtime, sha256)", nrow(before), as.integer(!same))
  outputs <- list()
  if (!ctx$dry_run) {
    od <- file.path(ctx$run_dir, "outputs"); dir.create(od, recursive = TRUE, showWarnings = FALSE)
    wr <- function(name, df) { p <- file.path(od, paste0(name, ".csv")); fi_write_csv_atomic(df, p); fi_receipt_output(rec, p, nrow(df), role = name); outputs[[name]] <<- p; p }
    wr("ibis_editions", col$editions); wr("ibis_key_statistics_long", col$long); wr("ibis_predicted_growth", pred_df); wr("ibis_actual_growth", act_df)
    ent <- fi_manifest_ibis(col$editions, outputs, fi_code_sha256())
    patch <- list(industries = stats::setNames(lapply(ids, function(id) list(ibisworld = list(actual_source = "feed", predicted_source = "feed"))), ids))
    pr <- fi_write_proposals(ctx$run_dir, ent, patch, "IBISWorld feed: point the industry's actual and predicted sources at the feed CSVs once a 2025+ edition is in.")
    fi_receipt_output(rec, pr$inputs, length(ent), role = "proposed_inputs"); fi_receipt_output(rec, pr$registry_patch, NA_integer_, role = "proposed_registry_patch")
    gb$event("feeds.manifest.proposed", "succeeded", "manifest", sprintf("proposed %d manifest entries", length(ent)), "", list(entries = length(ent)))
    if (n_checked > 0L) for (nm in names(outputs)) fi_current_update(nm, outputs[[nm]], ctx$run_id)
    else fi_receipt_decision(rec, "no checked edition: current.json left as it was")
  }
  rec$extra$files <- list(scanned = s$files, checked = n_checked, review = nrow(needs_review), unsupported = s$unsupported)
  rec$extra$replaced_vintage <- if (is.na(replaced)) NULL else replaced
  if (length(waiting)) { rec$feed_state <- "waiting_for_owner_file"; for (w in waiting) { fi_receipt_decision(rec, w); .fi_say("ibisworld: ", w) } }
  status <- if (nrow(needs_review)) "review_required" else if (length(waiting)) "waiting_for_owner_file" else "ok"
  if (!same) status <- "failed"
  list(status = status, message = sprintf("ibisworld: %d file(s) scanned, %d edition(s) checked, %d need review%s", s$files, n_checked, nrow(needs_review), if (length(waiting)) "; waiting for owner file" else ""))
}

# ---- OpenSecrets: saved pages -----------------------------------------------------------------------------------------------------

.fi_write_os_outputs <- function(ctx, envs, feeds) {
  # envs: list of list(env, code, cycle, kind, role); writes the envelope JSONs and the tidy CSVs; returns the written paths by role
  rec <- ctx$rec
  od <- file.path(ctx$run_dir, "outputs", "os"); dir.create(od, recursive = TRUE, showWarnings = FALSE)
  cmap <- fi_code_map(feeds)
  written <- list(); tot <- list(); cand <- list()
  for (e in envs) {
    path <- file.path(od, fi_os_envelope_name(e$code, e$cycle, e$kind))
    fi_os_write_envelope(e$env, path)
    fi_receipt_output(rec, path, NA_integer_, role = e$role)
    written[[e$role]] <- path
    id <- unname(cmap[e$code])
    if (e$kind == "totals") tot[[length(tot) + 1L]] <- fi_os_tidy_totals(e$env, id) else cand[[length(cand) + 1L]] <- fi_os_tidy_candidates(e$env, id)
  }
  cd <- file.path(ctx$run_dir, "outputs")
  if (length(tot)) { p <- file.path(cd, "os_industry_totals.csv"); d <- do.call(rbind, tot); fi_write_csv_atomic(d, p); fi_receipt_output(rec, p, nrow(d), role = "os_industry_totals") }
  if (length(cand)) { p <- file.path(cd, "os_candidate_recipients.csv"); d <- do.call(rbind, cand); fi_write_csv_atomic(d, p); fi_receipt_output(rec, p, nrow(d), role = "os_candidate_recipients") }
  written
}

.fi_run_os_pages <- function(ctx) {
  feeds <- ctx$feeds; rec <- ctx$rec; gb <- ctx$gb
  dir <- file.path(fi_inbox_dir(), "opensecrets", "pages")
  if (!ctx$dry_run) dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  before <- fi_inbox_state(dir)
  scan <- fi_inbox_scan(dir, allowed = "html", ledger_path = file.path(fi_frt_dir(), "inbox_seen.json"), write = !ctx$dry_run)
  s <- attr(scan, "summary")
  gb$event("feeds.inbox.scan", "succeeded", "scan", sprintf("pages scan: %d files, %d new, %d duplicate, %d unsupported", s$files, s$new, s$duplicate, s$unsupported), "", s)
  cmap <- fi_code_map(feeds); frozen <- unlist(feeds$opensecrets_frozen$codes)
  envs <- list(); n_bad <- 0L
  for (i in seq_len(nrow(scan))) {
    r <- scan[i, ]; fi_receipt_input(rec, r)
    if (r$status != "new" && r$status != "seen_before") next
    html <- rawToChar(fi_read_raw(r$vault_path %||% r$path)); Encoding(html) <- "UTF-8"
    tgt <- fi_os_target_from_filename(r$inbox_name)
    if (is.null(tgt)) { meta <- fi_os_page_meta(html); tgt <- fi_os_target_from_url(gsub("&amp;", "&", meta$canonical %||% "", fixed = TRUE)) }
    if (is.na(tgt$code) || is.na(tgt$cycle) || is.na(tgt$kind)) { n_bad <- n_bad + 1L; fi_receipt_issue(rec, sprintf("%s: cannot tell which OpenSecrets page this is (name it like F3400_2012_candidates_H.html)", r$inbox_name)); next }
    if (tgt$code %in% frozen) { fi_receipt_decision(rec, sprintf("%s: code %s belongs to the frozen baseline; not re-derived", r$inbox_name, tgt$code)); next }
    if (!(tgt$code %in% names(cmap))) { n_bad <- n_bad + 1L; fi_receipt_issue(rec, sprintf("%s: code %s is not in the feeds registry (unregistered_code)", r$inbox_name, tgt$code)); next }
    env <- fi_os_envelope(html, fi_os_url(tgt$code, tgt$cycle, tgt$kind), route = "manual_save", source_sha = r$sha256, expect = tgt)
    fi_receipt_checks_df(rec, env$checks)
    if (!env$ok) { n_bad <- n_bad + 1L; fi_receipt_issue(rec, sprintf("%s: rejected (%s)", r$inbox_name, paste(env$issues, collapse = "; "))); next }
    id <- unname(cmap[tgt$code])
    role <- switch(tgt$kind, totals = sprintf("os_totals:%s", id), presidential = sprintf("os_presidential:%s:%d", id, tgt$cycle),
                   sprintf("os_recipients:%s:%d:%s", id, tgt$cycle, substr(tgt$kind, 12, 12)))
    envs[[length(envs) + 1L]] <- list(env = env$envelope, code = tgt$code, cycle = tgt$cycle, kind = tgt$kind, role = role)
  }
  fi_receipt_check(rec, "inbox files unchanged (name, size, mtime, sha256)", nrow(before), as.integer(!identical(before, fi_inbox_state(dir))))
  written <- list()
  if (length(envs) && !ctx$dry_run) {
    written <- .fi_write_os_outputs(ctx, envs, feeds)
    ent <- fi_manifest_os(written, NULL, fi_code_sha256())
    pr <- fi_write_proposals(ctx$run_dir, ent, list(), "OpenSecrets saved pages")
    fi_receipt_output(rec, pr$inputs, length(ent), role = "proposed_inputs"); fi_receipt_output(rec, pr$registry_patch, NA_integer_, role = "proposed_registry_patch")
    gb$event("feeds.manifest.proposed", "succeeded", "manifest", sprintf("proposed %d manifest entries", length(ent)), "", list(entries = length(ent)))
  }
  list(status = if (n_bad) "review_required" else if (!nrow(scan)) "waiting_for_owner_file" else "ok",
       message = sprintf("opensecrets-pages: %d file(s) scanned, %d page(s) accepted, %d rejected", s$files, length(envs), n_bad))
}

# ---- OpenSecrets: the polite fetcher ------------------------------------------------------------------------------------------------

.fi_run_os_fetch <- function(ctx) {
  feeds <- ctx$feeds; rec <- ctx$rec; gb <- ctx$gb
  ids <- .fi_industries(feeds, "opensecrets", ctx$industry)
  ids <- ids[vapply(ids, function(i) "fetch" %in% unlist(feeds$industries[[i]]$opensecrets$routes_allowed), NA)]
  if (!length(ids)) return(list(status = "failed", message = "opensecrets-fetch: no industry with the fetch route in the registry"))
  cfg <- feeds$opensecrets_fetch; frozen <- unlist(feeds$opensecrets_frozen$codes)
  plan <- do.call(rbind, lapply(ids, function(i) cbind(fi_os_fetch_plan(feeds, i), industry = i, stringsAsFactors = FALSE)))
  rec$extra$plan <- list(industries = as.list(ids), pages = nrow(plan), permission = cfg$permission)
  if (ctx$dry_run) {
    gb$event("feeds.fetch.gate", "succeeded", "fetch-gate", "dry run: no request is made", "", list(decision = "dry-run", reason = "no network in a dry run"))
    .fi_say("opensecrets-fetch (dry run): would fetch ", nrow(plan), " page(s) for ", paste(ids, collapse = ", "), "; first: ", plan$url[1])
    return(list(status = "ok", message = sprintf("opensecrets-fetch: dry run, %d page(s) planned, no request made", nrow(plan))))
  }
  ind_of <- stats::setNames(plan$industry, plan$url)
  expect <- feeds$industries[[ids[1]]]$opensecrets$expect
  envs <- list(); verification <- NULL; n_bad <- 0L
  on_page <- function(pg) {
    row <- pg$row
    id <- ind_of[[pg$url]]
    if (pg$index == 1L) {
      meta <- fi_os_page_meta(pg$html)
      v <- fi_os_verify_category_page(meta, row$code, expect$catname_regex, expect$catorder, expect$parent_industry_name)
      verification <<- v
      fi_receipt_check(rec, sprintf("OpenSecrets code %s verified from the site's own page", row$code), 1L, as.integer(!v$verified),
                       sprintf("heading '%s'; parent %s; %s", v$heading, v$parent %||% "not shown", paste(c(v$issues, v$notes), collapse = "; ")))
      fi_receipt_decision(rec, sprintf("code %s: page heading '%s', canonical code confirmed, parent industry %s (%s)", row$code, v$heading, v$parent %||% "not shown on the page", if (v$verified) "VERIFIED" else "NOT VERIFIED"))
      rec$extra$code_verification <- v
      gb$event("feeds.file", if (v$verified) "succeeded" else "failed", "verify", sprintf("code %s %s", row$code, if (v$verified) "verified" else "NOT verified"), paste(v$issues, collapse = "; "),
               list(sha256 = pg$sha256, kind = "html", code = row$code, edition = NA, status = if (v$verified) "verified" else "verification_failed"))
      if (!v$verified) return(list(stop = TRUE, reason = paste0("category_verification_failed: ", paste(v$issues, collapse = "; "))))
    }
    # vault copy of the page bytes under a readable name
    tmp <- file.path(tempdir(), fi_os_envelope_name(row$code, row$cycle, row$kind))
    tmp <- sub("\\.json$", ".html", tmp)
    file.copy(file.path(pg$cache_dir, "body.html"), tmp, overwrite = TRUE)
    vp <- rf_vault_put(tmp, pg$sha256); unlink(tmp)
    fi_receipt_input(rec, data.frame(inbox_name = pg$url, sha256 = pg$sha256, bytes = file.size(vp), first_seen_utc = pg$retrieved_utc, vault_path = vp, kind = "html",
                                     status = pg$status, stringsAsFactors = FALSE), identified = list(os_table = row$kind, cycle = row$cycle, code = row$code))
    env <- fi_os_envelope(pg$html, row$url, final_url = pg$final_url, retrieved_utc = pg$retrieved_utc, http = pg$http, route = "fetch", source_sha = pg$sha256,
                          expect = list(code = row$code, cycle = row$cycle, kind = row$kind))
    fi_receipt_checks_df(rec, env$checks)
    if (!env$ok) { n_bad <<- n_bad + 1L; fi_receipt_issue(rec, sprintf("%s: rejected (%s)", pg$url, paste(env$issues, collapse = "; "))); return(NULL) }
    envs[[length(envs) + 1L]] <<- list(env = env$envelope, code = row$code, cycle = row$cycle, kind = row$kind, role = row$role)
    NULL
  }
  res <- fi_os_fetch_run(plan, cfg, frozen, frt = fi_frt_dir(), transport = ctx$transport, clock = ctx$clock, sleep = ctx$sleep, emit = gb$event, contact = ctx$contact,
                         refresh = ctx$refresh, on_page = on_page)
  fi_receipt_network(rec, res$network)
  rec$extra$fetch <- list(requests = res$requests, pages = res$pages, stopped = res$stopped, user_agent = res$gate$user_agent)
  written <- list()
  if (length(envs)) {
    written <- .fi_write_os_outputs(ctx, envs, feeds)
    cmap <- fi_code_map(feeds)
    ent <- fi_manifest_os(written, NULL, fi_code_sha256())
    okc <- !is.null(verification) && verification$verified
    cfg0 <- feeds$industries[[ids[1]]]
    code <- cfg0$opensecrets$codes[[1]]
    complete <- length(envs) == nrow(plan) && is.null(res$stopped)
    patch <- list(industries = stats::setNames(list(list(opensecrets = c(
      list(code_status = if (okc) "verified_site_page" else "unverified_recall",
           code_verification = if (okc) list(heading = verification$heading, parent = verification$parent, verified_utc = rf_now_utc(), run_id = ctx$run_id) else NULL),
      if (complete) list(totals = file.path(ctx$run_dir, "outputs", "os", sprintf("%s_%d_totals.json", code, cfg0$opensecrets$totals_cycle_anchor)),
                         recipients = file.path(ctx$run_dir, "outputs", "os", sprintf("%s_{cycle}_candidates_{chamber}.json", code)),
                         presidential = file.path(ctx$run_dir, "outputs", "os", sprintf("%s_{cycle}_presidential.json", code)), status = "supplied")))), ids[1]))
    pr <- fi_write_proposals(ctx$run_dir, ent, patch, "OpenSecrets fetched pages; the refit registry patch sets the capture paths only when every planned page was accepted.")
    fi_receipt_output(rec, pr$inputs, length(ent), role = "proposed_inputs"); fi_receipt_output(rec, pr$registry_patch, NA_integer_, role = "proposed_registry_patch")
    gb$event("feeds.manifest.proposed", "succeeded", "manifest", sprintf("proposed %d manifest entries", length(ent)), "", list(entries = length(ent)))
    for (nm in names(written)) fi_current_update(paste0("os:", nm), written[[nm]], ctx$run_id)
  }
  rec$extra$scope_caveat <- feeds$industries[[ids[1]]]$opensecrets$scope_caveat
  fi_receipt_decision(rec, paste("scope:", feeds$industries[[ids[1]]]$opensecrets$scope_caveat))
  n_ok <- length(envs)
  if (!is.null(res$stopped)) {
    msg <- if (identical(res$stopped$kind, "block") || identical(res$stopped$kind, "gate")) FI_OS_STOP_MESSAGE else paste("opensecrets-fetch stopped:", res$stopped$reason)
    .fi_say(msg)
    if (identical(res$stopped$kind, "gate")) .fi_say("reason: ", res$stopped$reason)
    return(list(status = "stopped", message = sprintf("opensecrets-fetch: stopped (%s) after %d request(s), %d page(s) accepted", res$stopped$reason, res$requests, n_ok), stop_reason = res$stopped$reason))
  }
  list(status = if (n_bad) "review_required" else "ok", message = sprintf("opensecrets-fetch: %d request(s), %d page(s) accepted, %d rejected", res$requests, n_ok, n_bad))
}

# ---- OpenSecrets: bulk fallback and calibration ---------------------------------------------------------------------------------------

.fi_run_calibrate <- function(ctx, then_build = FALSE) {
  feeds <- ctx$feeds; rec <- ctx$rec; gb <- ctx$gb
  dir <- file.path(fi_inbox_dir(), "opensecrets", "bulk")
  if (!ctx$dry_run) dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  before <- fi_inbox_state(dir)
  scan <- fi_inbox_scan(dir, allowed = c("zip", "text"), ledger_path = file.path(fi_frt_dir(), "inbox_seen.json"), write = !ctx$dry_run)
  s <- attr(scan, "summary")
  gb$event("feeds.inbox.scan", "succeeded", "scan", sprintf("bulk scan: %d files, %d new, %d duplicate, %d unsupported", s$files, s$new, s$duplicate, s$unsupported), "", s)
  for (i in seq_len(nrow(scan))) fi_receipt_input(rec, scan[i, ])
  if (!nrow(scan)) { rec$feed_state <- "waiting_for_owner_file"; .fi_say("opensecrets bulk: waiting for owner file (", dir, " is empty)"); return(list(status = "waiting_for_owner_file", message = "opensecrets bulk: no files in the inbox")) }
  ids <- .fi_industries(feeds, "opensecrets", ctx$industry)
  cfg0 <- feeds$industries[[ids[1]]]$opensecrets
  cat_file <- scan$path[tolower(basename(scan$path)) == "crp_categories.txt"]
  if (then_build) {
    if (!length(cat_file)) return(list(status = "stopped", message = "opensecrets-bulk: CRP_Categories.txt is not in the bulk folder, so the code cannot be verified", stop_reason = "categories_file_missing"))
    v <- fi_os_verify_categories(fi_os_read_categories(cat_file[1]), cfg0$codes[[1]], cfg0$expect)
    fi_receipt_check(rec, sprintf("code %s verified from CRP_Categories.txt", cfg0$codes[[1]]), 1L, as.integer(!v$verified), paste(v$issues, collapse = "; "))
    if (!v$verified) return(list(status = "stopped", message = paste("opensecrets-bulk: code not verified:", paste(v$issues, collapse = "; ")), stop_reason = "category_verification_failed"))
  }
  cal <- fi_os_calibrate(dir, feeds)
  gb$event("feeds.calibrate", if (cal$passed) "succeeded" else "failed", "calibrate", sprintf("calibration %s", if (cal$passed) "passed" else "FAILED"), "",
           list(recipe = cal$accepted %||% "none", pass = cal$passed, max_delta = cal$max_delta))
  fi_receipt_check(rec, "bulk recipe calibration against the page captures", 1L, as.integer(!cal$passed), sprintf("max relative delta %s", format(cal$max_delta)))
  if (!ctx$dry_run && !is.null(cal$table)) {
    p <- file.path(ctx$run_dir, "outputs", "calibration.csv"); dir.create(dirname(p), recursive = TRUE, showWarnings = FALSE)
    fi_write_csv_atomic(cal$table, p); fi_receipt_output(rec, p, nrow(cal$table), role = "os_calibration")
  }
  if (!cal$passed) return(list(status = "stopped", message = "opensecrets: no bulk recipe passed calibration; bulk numbers stay withheld", stop_reason = "calibration_failed"))
  if (then_build && !ctx$dry_run) {
    recipe <- Filter(function(r) identical(r$version, cal$accepted), feeds$bulk_recipes)[[1]]
    b <- fi_os_bulk_build(dir, cfg0$codes, recipe, unlist(cfg0$cycles_required), ids[1])
    fi_receipt_checks_df(rec, b$checks)
    cal_sha <- rf_sha256(file.path(ctx$run_dir, "outputs", "calibration.csv"))
    envs <- fi_os_bulk_envelopes(b, cfg0$codes[[1]], cal$accepted, cal_sha)
    od <- file.path(ctx$run_dir, "outputs", "os"); dir.create(od, recursive = TRUE, showWarnings = FALSE)
    for (nm in names(envs)) { p <- file.path(od, nm); rf_write_json_atomic(envs[[nm]], p); fi_receipt_output(rec, p, NA_integer_, role = paste0("os:", nm)) }
    if (!is.null(b$recipients)) { p <- file.path(ctx$run_dir, "outputs", "os_candidate_recipients.csv"); fi_write_csv_atomic(b$recipients, p); fi_receipt_output(rec, p, nrow(b$recipients), role = "os_candidate_recipients") }
  }
  list(status = "ok", message = sprintf("opensecrets: recipe %s passed calibration", cal$accepted))
}

# ---- the dispatcher --------------------------------------------------------------------------------------------------------------------

# Run one feed. Transport, clock and sleep are injectable for tests; contact overrides MENTAT_OS_CONTACT.
# -> list(status, exit_code, run_id, run_dir, receipt, message)
fi_run <- function(feed, industry = NULL, dry_run = FALSE, run_id = NULL, refresh = FALSE, transport = fi_curl_transport,
                   clock = function() as.numeric(Sys.time()), sleep = Sys.sleep, contact = NULL, events_dir = rf_glassbox_dir(), verbose = TRUE,
                   feeds = NULL) {
  if (!(feed %in% FI_FEEDS)) stop("unknown feed: ", feed, call. = FALSE)
  run_id <- run_id %||% fi_new_run_id(feed)
  feeds <- feeds %||% fi_read_feeds()
  run_dir <- file.path(fi_frt_dir(), "runs", run_id)
  gb <- fi_gb_run(run_id, events_dir)
  rec <- fi_receipt_new(run_id, feed, if (dry_run) "dry-run" else "run", industry %||% "", fi_inbox_dir())
  gb$start(feed, industry %||% "", fi_inbox_dir(), if (dry_run) "dry-run" else "run")
  ctx <- list(feeds = feeds, rec = rec, gb = gb, run_id = run_id, run_dir = run_dir, dry_run = dry_run, industry = industry, transport = transport, clock = clock,
              sleep = sleep, contact = contact, refresh = refresh)
  out <- tryCatch({
    switch(feed, ibisworld = .fi_run_ibisworld(ctx), "opensecrets-pages" = .fi_run_os_pages(ctx), "opensecrets-fetch" = .fi_run_os_fetch(ctx),
           "opensecrets-bulk" = .fi_run_calibrate(ctx, then_build = TRUE), calibrate = .fi_run_calibrate(ctx, then_build = FALSE))
  }, error = function(e) list(status = "failed", message = conditionMessage(e), error = conditionMessage(e)))
  rec$status <- out$status
  code <- switch(out$status, ok = 0L, waiting_for_owner_file = 0L, review_required = 2L, stopped = 3L, 1L)
  rcpt <- NULL
  if (!dry_run) {
    rcpt <- tryCatch({
      # the receipt is the last write of the run; its own Glass Box events are emitted just before so it can list their ids
      if (out$status %in% c("stopped", "failed")) gb$fail(if (out$status == "stopped") "fetch" else "run", out$message, out$stop_reason %||% "")
      else gb$done(out$message, file.path(run_dir, "receipt.json"), length(rec$outputs))
      fi_receipt_write(rec, run_dir, gb$ids())
    }, error = function(e) { message("WARNING: receipt not written (", conditionMessage(e), ")"); NULL })
  } else {
    if (out$status %in% c("stopped", "failed")) gb$fail("run", out$message) else gb$done(out$message, "", 0L)
  }
  if (verbose) .fi_say("[", out$status, "] ", out$message, if (!is.null(rcpt)) paste0("\nreceipt: ", rcpt$path) else "")
  list(status = out$status, exit_code = code, run_id = run_id, run_dir = run_dir, receipt = rcpt, message = out$message, stop_reason = out$stop_reason %||% NULL)
}

fi_main <- function(args = commandArgs(trailingOnly = TRUE)) {
  o <- tryCatch(fi_parse_args(args), error = function(e) { message("ERROR: ", conditionMessage(e)); NULL })
  if (is.null(o)) return(invisible(1L))
  r <- fi_run(o$feed, o$industry, o$dry_run, o$run_id, o$refresh)
  invisible(r$exit_code)
}
