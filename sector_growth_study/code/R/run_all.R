# Sector growth and political spending study: R entry point (R port of code/sgs/run_all.py).
#
# One command (PowerShell) runs the whole study on the live data folder with Paul's rulings and writes new result
# files with a new run id (nothing is overwritten):
#   & "C:\Program Files\R\R-4.6.0\bin\Rscript.exe" "C:\Users\pgoff\Mentat\sector_growth_study\code\R\run_all.R"
#
# Flags:
#   --ruleset=paul-2026-09-25|python-parity   rule set (default paul-2026-09-25; python-parity = the frozen Python code)
#   --data-dir=DIR          input folder (default <study>\data)
#   --results-dir=DIR       output folder (default <study>\results)
#   --receipt-05=FILE       05 build receipt (default: build_receipt_05.json in the parent of the input folder)
#   --window=2020-2025      primary window of the sector-year tests
#   --fallback=2008-2025    span searched for the fallback window, or none
#   --seed=20260925  --B=9999
#   --only=C1,L1,H5         test ids or id prefixes
#   --run-id=ID             default analysis-R-<UTC stamp>
#   --include-partial       let the partial year 2026 enter
#   --no-glassbox           do not emit Glass Box events
#   --quiet                 no per-test log lines
#   --help
# R library: C:/Users/pgoff/AppData/Local/R/win-library/4.6 (added when readxl is not on the default path).

if (!requireNamespace("readxl", quietly = TRUE)) .libPaths(c("C:/Users/pgoff/AppData/Local/R/win-library/4.6", .libPaths()))

sgs_entry_dir <- function() {
  fa <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  if (length(fa)) return(dirname(normalizePath(sub("^--file=", "", fa[1]), winslash = "/", mustWork = TRUE)))
  for (fr in rev(sys.frames())) {
    f <- get0("ofile", envir = fr, inherits = FALSE, ifnotfound = "")
    if (length(f) == 1L && nzchar(f) && file.exists(f)) return(dirname(normalizePath(f, winslash = "/")))
  }
  normalizePath(getwd(), winslash = "/")
}

SGS_CODE_DIR <- sgs_entry_dir()
for (m in c("sgs_config.R", "sgs_utils.R", "sgs_rng.R", "sgs_load.R", "sgs_panel.R", "sgs_registry.R", "sgs_sample.R",
            "sgs_gates.R", "sgs_estimate.R", "sgs_champions.R", "sgs_report.R", "sgs_summaries.R", "sgs_glassbox.R",
            "sgs_trends.R", "sgs_forecast.R", "sgs_review.R", "sgs_seats.R", "sgs_seats_race.R", "sgs_run.R")) {
  source(file.path(SGS_CODE_DIR, m), encoding = "UTF-8")
}

sgs_parse_window <- function(text) {
  if (is.null(text) || tolower(text) %in% c("none", "off", "")) return(NULL)
  as.numeric(strsplit(text, "-", fixed = TRUE)[[1]])
}

sgs_main <- function(argv = commandArgs(trailingOnly = TRUE)) {
  if ("--help" %in% argv) {
    cat(paste(readLines(file.path(SGS_CODE_DIR, "run_all.R"))[1:22], collapse = "\n"), "\n")
    return(invisible(0L))
  }
  get <- function(flag, default = NULL) {
    hit <- grep(paste0("^--", flag, "="), argv, value = TRUE)
    if (length(hit)) sub(paste0("^--", flag, "="), "", hit[length(hit)]) else default
  }
  rules <- sgs_rules(get("ruleset", "paul-2026-09-25"))
  window <- sgs_parse_window(get("window", "2020-2025"))
  fallback <- sgs_parse_window(get("fallback", "2008-2025"))
  seed <- as.numeric(get("seed", SGS$SEED))
  B <- as.numeric(get("B", SGS$BOOT_B))
  only <- get("only", NULL)
  only <- if (!is.null(only)) strsplit(only, ",", fixed = TRUE)[[1]] else NULL
  data_dir <- get("data-dir", SGS$DATA_DIR)
  results_dir <- get("results-dir", SGS$RESULTS_DIR)
  receipt_05 <- get("receipt-05", NULL)
  run_id <- get("run-id", paste0("analysis-R-", sgs_utc_stamp(Sys.time())))
  gb <- !("--no-glassbox" %in% argv)
  quiet <- "--quiet" %in% argv
  command <- paste(c("& \"C:\\Program Files\\R\\R-4.6.0\\bin\\Rscript.exe\"",
                     paste0("\"", normalizePath(file.path(SGS_CODE_DIR, "run_all.R"), winslash = "\\"), "\""), argv), collapse = " ")
  start_id <- if (gb) sgs_glassbox_emit("run.start", "running", "start",
                                         paste0("sector growth analysis (R, ", rules$name, "): start (window ", get("window", "2020-2025"),
                                                ", fallback search ", get("fallback", "2008-2025"), ", seed ", seed, ", B ", B, ", only ",
                                                if (is.null(only)) "all" else paste(only, collapse = ","), ")"), run_id) else NULL
  progress <- if (gb) function(stage, summary) sgs_glassbox_emit("run.progress", "running", stage,
                                                                 paste0("sector growth analysis (R): ", summary), run_id,
                                                                 correlation_id = start_id %||% "", parent_id = start_id %||% "") else NULL
  t0 <- Sys.time()
  out <- tryCatch(sgs_run(window = window, fallback = fallback, seed = seed, only = only, B = B, data_dir = data_dir,
                          results_dir = results_dir, include_partial = "--include-partial" %in% argv, run_id = run_id,
                          log = if (quiet) function(...) NULL else function(...) message(...), rules = rules,
                          receipt_05 = receipt_05, progress = progress, command = command),
                  error = function(e) {
                    if (gb) sgs_glassbox_emit("run.finish", "failed", "finish",
                                              paste0("sector growth analysis (R): FAILED (", class(e)[1], ")"), run_id,
                                              correlation_id = start_id %||% "", parent_id = start_id %||% "",
                                              detail = substr(conditionMessage(e), 1, 2000),
                                              duration_ms = as.integer(1000 * as.numeric(difftime(Sys.time(), t0, units = "secs"))))
                    stop(e)
                  })
  c_ <- out$counts
  ch <- out$champions
  sh <- Filter(function(r) r$family %in% c("SHIFT", "SHIFT-PV"), out$est_rows)
  summary <- paste0("sector growth analysis (R, ", rules$name, "): ", length(out$est_rows), " tests; ESTIMABLE ", c_[["ESTIMABLE"]],
                    ", NOT ESTIMABLE ", c_[["NOT ESTIMABLE"]], ", NOT BUILT ", c_[["NOT BUILT"]],
                    if (is.null(ch)) "" else paste0("; 05 ", if (ch$ok) "read" else "NOT BUILT"),
                    if (length(sh)) paste0("; SHIFT ", sum(vapply(sh, function(r) r$status == SGS_ESTIMABLE, TRUE)), " of ", length(sh),
                                           " estimable") else "",
                    if (!is.null(out$forecast)) paste0("; backtest LobbyView ", out$forecast$runs$lv$status, ", contributions ",
                                                       out$forecast$runs$c$status,
                                                       if (isTRUE(out$forecast$strict)) " (retrospective and strict)" else "") else "",
                    if (isTRUE(rules$lv_robustness)) {
                      ck <- sgs_codex_check(out$est_rows, out$coef_rows, out$holm)
                      paste0("; Codex review numbers: ", sum(ck$verdict == "MATCH"), " of ", nrow(ck), " MATCH")
                    } else "",
                    if (!is.null(out$seats)) {
                      sa <- Filter(function(r) identical(r$family, "SEATS-A"), out$est_rows)
                      paste0("; SEATS-A ", sum(vapply(sa, function(r) r$status == SGS_ESTIMABLE, TRUE)), " of ", length(sa),
                             " estimable (DESCRIPTIVE); SEATS-W ", if (isTRUE(out$seats$weekly_ok)) "built" else "NOT BUILT",
                             "; race level ", if (isTRUE(out$seats$race$ok)) "built" else "NOT BUILT")
                    } else "")
  if (gb) sgs_glassbox_emit("run.finish", "succeeded", "finish", summary, run_id, correlation_id = start_id %||% "",
                            parent_id = start_id %||% "",
                            detail = paste(out$xlsx, out$report, out$estimability, out$summaries, out$receipt, sep = "; "),
                            duration_ms = as.integer(1000 * as.numeric(difftime(Sys.time(), t0, units = "secs"))))
  cat(summary, "\n", out$xlsx, "\n", out$report, "\n", out$estimability, "\n", out$summaries, "\n", out$receipt, "\n", sep = "")
  invisible(out)
}

if (sys.nframe() == 0L || identical(Sys.getenv("SGS_RUN_MAIN"), "1")) {
  sgs_main()
}
