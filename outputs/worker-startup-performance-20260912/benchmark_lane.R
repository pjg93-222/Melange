# Parse the worker's functions only; the real collector and command-line entry
# point are never executed. All SQLite writes remain in a temporary fixture.
args <- commandArgs(TRUE)
script <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[[1]])
root <- normalizePath(file.path(dirname(script), "..", "..", "mentat"), winslash = "/")
for (file in c("paths.R", "schema.R", "ingest.R", "fec_page.R", "collect.R", "fec_api.R", "reconcile.R", "report.R")) {
  source(file.path(root, "R", file), local = .GlobalEnv)
}
for (expression in parse(file.path(root, "tools", "collect_api_lane.R"))) {
  if (is.call(expression) && identical(expression[[1]], as.name("<-")) &&
      is.call(expression[[3]]) && identical(expression[[3]][[1]], as.name("function"))) eval(expression)
}
fixture <- tempfile("mentat-worker-benchmark-")
dir.create(fixture)
industry <- "Synthetic"
key_id <- "openfec:sha256:synthetic"
concurrency <- 1L
fec_api_key <- function(...) "synthetic-unused-key"
budget_path <- file.path(fixture, "budget.sqlite")
budget <- DBI::dbConnect(RSQLite::SQLite(), budget_path)
DBI::dbExecute(budget, "PRAGMA journal_mode=WAL")
DBI::dbExecute(budget, "CREATE TABLE api_request_budget (budget_id TEXT PRIMARY KEY, window_started_epoch REAL NOT NULL, requests_used INTEGER NOT NULL DEFAULT 0)")
DBI::dbExecute(budget, "INSERT INTO api_request_budget VALUES ('fixture',1,42)")
DBI::dbDisconnect(budget)
Sys.setenv(MENTAT_API_BUDGET_DB = budget_path, MENTAT_REQUEST_POOL_URL = "http://127.0.0.1:1/batch", MENTAT_REQUEST_POOL_TOKEN = "synthetic-unused")
collect_crypto_api <- function(..., budget_connection) {
  stopifnot(DBI::dbGetQuery(budget_connection, "SELECT requests_used FROM api_request_budget WHERE budget_id='fixture'")[[1]][[1]] == 42)
  list(paused = FALSE, rows = 0L, request_count = 0L, retries = 0L, determinism = TRUE)
}
results <- list()
for (lane in c(1L, 32L)) {
  database_path <- file.path(fixture, paste0("lane-", lane, ".sqlite"))
  file.create(database_path)
  assignments_path <- file.path(fixture, paste0("assignments-", lane, ".json"))
  receipt_path <- file.path(fixture, paste0("receipt-", lane, ".json"))
  jsonlite::write_json(list(lane = lane, tasks = list(list(task_id = "fixture-2026", company = "Fixture", cycle = 2026L))), assignments_path, auto_unbox = TRUE)
  watch <- proc.time()[['elapsed']]
  stopifnot(run_lane() == 0L)
  results[[length(results) + 1L]] <- list(lane = lane, seconds = unname(proc.time()[['elapsed']] - watch), receipt = jsonlite::read_json(receipt_path))
}
jsonlite::write_json(list(scope = "Mock collector; no HTTP calls; isolated SQLite fixtures", lanes = results),
  file.path(dirname(script), paste0(args[[1]], "-lane.json")), auto_unbox = TRUE, pretty = TRUE)
unlink(fixture, recursive = TRUE)
cat("Mock lane benchmark: PASS\n")
