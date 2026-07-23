# Collect a bounded company subset into a private SQLite shard.
#
# Usage:
#   Rscript collect_company_shard.R DATABASE INDUSTRY RESUME_AFTER COMPANY|COMPANY

options(stringsAsFactors = FALSE)

arguments <- commandArgs(trailingOnly = TRUE)
if (length(arguments) != 4L) {
  stop(
    paste(
      "usage: collect_company_shard.R",
      "DATABASE INDUSTRY RESUME_AFTER COMPANY|COMPANY"
    ),
    call. = FALSE
  )
}

database_path <- normalizePath(
  arguments[[1L]],
  winslash = "/",
  mustWork = TRUE
)
industry <- trimws(arguments[[2L]])
resume_after <- trimws(arguments[[3L]])
companies <- unique(trimws(strsplit(
  arguments[[4L]],
  "|",
  fixed = TRUE
)[[1L]]))
companies <- companies[nzchar(companies)]
if (!nzchar(industry) || !length(companies)) {
  stop("Industry and at least one company are required.", call. = FALSE)
}

script_path <- normalizePath(
  sub("^--file=", "", grep(
    "^--file=",
    commandArgs(trailingOnly = FALSE),
    value = TRUE
  )[[1L]]),
  winslash = "/",
  mustWork = TRUE
)
project_root <- dirname(dirname(script_path))
assign("MENTAT_PROJECT_ROOT", project_root, envir = .GlobalEnv)
assign("MENTAT_INDUSTRY", industry, envir = .GlobalEnv)

for (module in c(
  "paths.R", "schema.R", "ingest.R", "fec_page.R", "collect.R",
  "fec_api.R", "reconcile.R", "report.R"
)) {
  source(file.path(project_root, "R", module), local = .GlobalEnv)
}

require_package("DBI")
require_package("RSQLite")
connection <- DBI::dbConnect(RSQLite::SQLite(), database_path)
on.exit(DBI::dbDisconnect(connection), add = TRUE)
DBI::dbExecute(connection, "PRAGMA busy_timeout=30000")
init_schema(connection)

cat(
  "Company shard:", industry, "|",
  paste(companies, collapse = ", "), "\n"
)
result <- collect_crypto(
  connection,
  cycles = c(2022L, 2024L, 2026L),
  phase2_names = FALSE,
  resume_after = resume_after,
  company_filter = companies
)
quick_check <- DBI::dbGetQuery(
  connection,
  "PRAGMA quick_check(1)"
)[[1L]][[1L]]
if (!identical(quick_check, "ok")) {
  stop("Shard database quick_check failed: ", quick_check, call. = FALSE)
}
cat(
  "Company shard complete: rows=", result$rows,
  " retries=", result$retries,
  " quick_check=", quick_check,
  "\n",
  sep = ""
)
