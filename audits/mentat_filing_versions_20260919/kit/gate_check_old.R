# Same databases, same rows, but classified by the PRE-7d364883e collect.R, to
# establish the 80/4 baseline the 2026-09-15 lane recorded and show which rows
# the commit moved. raw_rows are loaded with the CURRENT report.R first, then the
# old collect.R is sourced over the classifier functions only.
args <- commandArgs(trailingOnly = TRUE)
database_path <- normalizePath(args[[1L]], winslash = "/", mustWork = TRUE)
MENTAT_INDUSTRY <- args[[2L]]
old_collect <- normalizePath(args[[3L]], winslash = "/", mustWork = TRUE)
MENTAT_PROJECT_ROOT <- "C:/Users/pgoff/Mentat/mentat"
Sys.setenv(MENTAT_INPUT_DIR = file.path(MENTAT_PROJECT_ROOT, "inputs"))
setwd(MENTAT_PROJECT_ROOT)
for (module in c("paths.R", "schema.R", "ingest.R", "fec_page.R", "collect.R",
                 "fec_api.R", "reconcile.R", "report.R", "fec_beneficiary.R",
                 "identity_components.R", "export_guards.R", "fec_transfer_graph.R",
                 "state_destinations.R", "tidy_stage.R")) {
  source(file.path(MENTAT_PROJECT_ROOT, "R", module), local = .GlobalEnv)
}
require_package("data.table"); require_package("DBI"); require_package("RSQLite")
options(width = 250, scipen = 99)

connection <- DBI::dbConnect(RSQLite::SQLite(), database_path, flags = RSQLite::SQLITE_RO)
on.exit(DBI::dbDisconnect(connection), add = TRUE)
raw_rows <- spending_raw_report_rows(connection, versioning_applied = TRUE)
for (column in c("contributor_street_1", "contributor_street_2")) {
  if (!column %in% names(raw_rows)) raw_rows[, (column) := NA_character_]
}
new_role <- fec_receipt_role(raw_rows)
new_unresolved <- fec_receipt_countable(raw_rows) & fec_receipt_role_unresolved(new_role)

# Overwrite the classifier with the pre-commit version.
source(old_collect, local = .GlobalEnv)
cat("\n########## OLD CLASSIFIER |", MENTAT_INDUSTRY, "| rules v", fec_receipt_rules()$version, "##########\n")
old_role <- fec_receipt_role(raw_rows)
old_unresolved <- fec_receipt_countable(raw_rows) & fec_receipt_role_unresolved(old_role)
cat("OLD gate would refuse (countable & unresolved):", sum(old_unresolved, na.rm = TRUE), "\n")
cat("NEW still unresolved (but counted and flagged) :", sum(new_unresolved, na.rm = TRUE), "\n")
moved <- old_unresolved & !new_unresolved
cat("rows the commit resolved:", sum(moved, na.rm = TRUE), "\n")
cat("rows newly unresolved   :", sum(new_unresolved & !old_unresolved, na.rm = TRUE), "\n")
if (any(moved, na.rm = TRUE)) {
  cat("\ndisposition of the rows the commit resolved (old role -> new role):\n")
  print(data.table::data.table(old = old_role[moved], new = new_role[moved])[, .N, by = .(old, new)][order(-N)])
}
cat("\nold gate verdict on this database: ")
outcome <- try(fec_assert_receipt_evidence(raw_rows), silent = TRUE)
cat(if (inherits(outcome, "try-error")) paste("REFUSED ->", conditionMessage(attr(outcome, "condition")))
    else "PASSED", "\n")
cat("DONE\n")
