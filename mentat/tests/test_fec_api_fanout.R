script_argument <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
stopifnot(length(script_argument) == 1L)
script_path <- normalizePath(
  sub("^--file=", "", script_argument[[1L]]),
  winslash = "/",
  mustWork = TRUE
)
project_root <- normalizePath(
  file.path(dirname(script_path), ".."),
  winslash = "/",
  mustWork = TRUE
)
for (file in c("paths.R", "schema.R", "ingest.R", "collect.R", "fec_api.R")) {
  source(file.path(project_root, "R", file), local = .GlobalEnv)
}

filter_fixture <- list(
  rosters = list(
    Alpha = data.frame(variant = "ALPHA", stringsAsFactors = FALSE),
    Beta = data.frame(variant = "BETA", stringsAsFactors = FALSE)
  ),
  match_overrides = data.frame(),
  home_states = data.frame(),
  trusted_by_company = list(Alpha = "A PERSON", Beta = "B PERSON")
)
stopifnot(
  identical(fec_api_filter_lookups(filter_fixture, NULL), filter_fixture),
  identical(
    names(fec_api_filter_lookups(filter_fixture, "Beta")$rosters),
    "Beta"
  ),
  identical(
    names(fec_api_filter_lookups(filter_fixture, "Beta")$trusted_by_company),
    "Beta"
  )
)
unknown_company <- tryCatch(
  {
    fec_api_filter_lookups(filter_fixture, "Gamma")
    ""
  },
  error = conditionMessage
)
stopifnot(grepl("unknown company names: Gamma", unknown_company, fixed = TRUE))

# The persistent redacted budget ledger is global to a key, not a run/shard.
# Reopening the database simulates a same-key rerun; a second key must retain an
# independent count in the same hourly window.
budget_database <- tempfile(fileext = ".sqlite")
budget_connection <- DBI::dbConnect(RSQLite::SQLite(), budget_database)
init_schema(budget_connection)
first_key_id <- "openfec:sha256:aaaaaaaaaaaa"
second_key_id <- "openfec:sha256:bbbbbbbbbbbb"
first_reservation <- fec_api_budget_reserve(
  budget_connection,
  requests = 3L,
  cap = 10L,
  now = 100,
  budget_id = first_key_id
)
DBI::dbDisconnect(budget_connection)
budget_connection <- DBI::dbConnect(RSQLite::SQLite(), budget_database)
same_key_rerun <- fec_api_budget_reserve(
  budget_connection,
  requests = 2L,
  cap = 10L,
  now = 101,
  budget_id = first_key_id
)
other_key <- fec_api_budget_reserve(
  budget_connection,
  requests = 4L,
  cap = 10L,
  now = 101,
  budget_id = second_key_id
)
stopifnot(
  first_reservation$requests_used == 3L,
  same_key_rerun$requests_used == 5L,
  other_key$requests_used == 4L,
  fec_api_budget_status(
    budget_connection,
    cap = 10L,
    now = 102,
    budget_id = first_key_id
  )$requests_remaining == 5L,
  fec_api_budget_status(
    budget_connection,
    cap = 10L,
    now = 102,
    budget_id = second_key_id
  )$requests_remaining == 6L,
  identical(
    fec_api_budget_id("never-stored", first_key_id),
    first_key_id
  )
)
DBI::dbDisconnect(budget_connection)
unlink(budget_database, force = TRUE)

cat("test_fec_api_fanout: PASS\n")
