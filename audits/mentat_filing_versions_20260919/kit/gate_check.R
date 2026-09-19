# Run the COMMITTED receipt-evidence gate the way the exporter runs it, against a
# SCRATCH COPY of a hydrated database. Read-only: SQLITE_RO, and
# versioning_applied = TRUE so apply_amendment_versioning() never writes.
#
# MENTAT_INDUSTRY is an R GLOBAL (collect.R / fec_api.R / report.R read the
# variable, not the environment variable): it is set below before sourcing,
# exactly as tools/export_crypto_spending_data.R does.
args <- commandArgs(trailingOnly = TRUE)
database_path <- normalizePath(args[[1L]], winslash = "/", mustWork = TRUE)
MENTAT_INDUSTRY <- args[[2L]]
MENTAT_PROJECT_ROOT <- "C:/Users/pgoff/Mentat/mentat"
# mentat_input_dir() walks up from getwd() and aborts outside the project
# (paths.R:110-135). MENTAT_INPUT_DIR is the supported pin; setwd() only changes
# this process's directory and writes nothing.
Sys.setenv(MENTAT_INPUT_DIR = file.path(MENTAT_PROJECT_ROOT, "inputs"))
setwd(MENTAT_PROJECT_ROOT)

for (module in c("paths.R", "schema.R", "ingest.R", "fec_page.R", "collect.R",
                 "fec_api.R", "reconcile.R", "report.R", "fec_beneficiary.R",
                 "identity_components.R", "export_guards.R", "fec_transfer_graph.R",
                 "state_destinations.R", "tidy_stage.R")) {
  source(file.path(MENTAT_PROJECT_ROOT, "R", module), local = .GlobalEnv)
}
require_package("data.table")
require_package("DBI")
require_package("RSQLite")
options(width = 250, scipen = 99)

cat("\n########## INDUSTRY:", MENTAT_INDUSTRY, "| DB:", database_path, "##########\n")
cat("ruleset version:", fec_receipt_rules()$version, "\n")
cat("gate source: C:/Users/pgoff/Mentat/mentat/R/collect.R fec_assert_receipt_evidence()\n")

connection <- DBI::dbConnect(RSQLite::SQLite(), database_path, flags = RSQLite::SQLITE_RO)
on.exit(DBI::dbDisconnect(connection), add = TRUE)
raw_rows <- spending_raw_report_rows(connection, versioning_applied = TRUE)
for (column in c("contributor_street_1", "contributor_street_2")) {
  if (!column %in% names(raw_rows)) raw_rows[, (column) := NA_character_]
}
cat("raw_rows:", nrow(raw_rows), "\n")

supported_cycles <- c(2022L, 2024L, 2026L)
contribution_cycle <- function(values) {
  year <- as.integer(format(normalize_reconcile_date(values), "%Y"))
  ifelse(is.na(year), NA_integer_, ifelse(year %% 2L == 0L, year, year + 1L))
}
evidence_scope <- contribution_cycle(raw_rows$contribution_receipt_date) %in% supported_cycles
cat("rows in evidence_scope (2022/2024/2026):", sum(evidence_scope), "\n")

role <- fec_receipt_role(raw_rows)
countable <- fec_receipt_countable(raw_rows)
unresolved <- countable & fec_receipt_role_unresolved(role)
contradicted <- countable & fec_receipt_role_contradicted(role)

cat("\n--- what the OLD (pre-7d364883e) gate refused: countable & unresolved role ---\n")
cat("all rows:", sum(unresolved, na.rm = TRUE),
    "| in evidence_scope:", sum(unresolved & evidence_scope, na.rm = TRUE), "\n")
print(data.table::data.table(role = role[unresolved])[, .N, by = role][order(-N)])
cat("\nreceipt_role_reason breakdown (the flag readers now filter on):\n")
print(data.table::data.table(reason = fec_receipt_role_reason(role)[unresolved])[, .N, by = reason][order(-N)])
cat("\nincluded-in-analysis status of those rows (spending_raw_report_rows view):\n")
if ("include_in_analysis" %in% names(raw_rows)) {
  print(raw_rows[unresolved, .N, by = include_in_analysis])
} else {
  cat("  (no include_in_analysis column in this view)\n")
}
cat("\nsub_ids of the unresolved rows (first 100):\n")
print(head(raw_rows$sub_id[unresolved], 100L))

cat("\n--- what the COMMITTED gate refuses: countable & self-contradicting ---\n")
cat("all rows:", sum(contradicted, na.rm = TRUE),
    "| in evidence_scope:", sum(contradicted & evidence_scope, na.rm = TRUE), "\n")
if (any(contradicted, na.rm = TRUE)) print(raw_rows[contradicted, .(sub_id, committee_id)])

cat("\n--- fec_assert_receipt_evidence() AS THE EXPORTER CALLS IT ---\n")
scoped <- try(fec_assert_receipt_evidence(raw_rows[evidence_scope]), silent = TRUE)
cat("exporter scope  (raw_rows[evidence_scope]):",
    if (inherits(scoped, "try-error")) paste("REFUSED ->", conditionMessage(attr(scoped, "condition")))
    else "PASSED (invisible TRUE)", "\n")
whole <- try(fec_assert_receipt_evidence(raw_rows), silent = TRUE)
cat("report.R scope  (all raw_rows)          :",
    if (inherits(whole, "try-error")) paste("REFUSED ->", conditionMessage(attr(whole, "condition")))
    else "PASSED (invisible TRUE)", "\n")
cat("\nDONE", MENTAT_INDUSTRY, "\n")
