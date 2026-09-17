# D2 PROOF. Runs the census the ORIGINAL way: no override. The real
# spending_raw_report_rows() is used, sourced from the PATCHED copy of report.R
# in the scratchpad. Everything else comes from the live modules.
#
# usage: Rscript proof_patched.R <mentat.db> <Industry Label> <out_dir>
args <- commandArgs(trailingOnly = TRUE)
database_path <- normalizePath(args[[1L]], winslash = "/", mustWork = TRUE)
industry_label <- trimws(args[[2L]])
out_dir <- normalizePath(args[[3L]], winslash = "/", mustWork = TRUE)

MENTAT_PROJECT_ROOT <- "C:/Users/pgoff/Mentat/mentat"
MENTAT_INDUSTRY <- industry_label

for (module in c(
  "paths.R", "schema.R", "ingest.R", "fec_page.R", "collect.R",
  "fec_api.R", "reconcile.R", "report.R", "fec_beneficiary.R",
  "identity_components.R", "export_guards.R", "fec_transfer_graph.R",
  "state_destinations.R", "tidy_stage.R"
)) {
  path <- if (identical(module, "report.R")) {
    file.path(out_dir, "report_patched.R")   # <- the patched file, in its slot
  } else {
    file.path(MENTAT_PROJECT_ROOT, "R", module)
  }
  source(path, local = .GlobalEnv)
}
require_package("data.table"); require_package("DBI"); require_package("RSQLite")

# Prove we are running the PATCHED real function, not the census override.
body_text <- paste(deparse(body(spending_raw_report_rows)), collapse = "\n")
cat("uses street_projection:", grepl("street_projection", body_text), "\n")
cat("census override absent:",
    !grepl("census refuses to run amendment versioning", body_text), "\n")

supported_cycles <- c(2022L, 2024L, 2026L)
contribution_cycle <- function(values) {
  dates <- normalize_reconcile_date(values)
  years <- as.integer(format(dates, "%Y"))
  years + years %% 2L
}

connection <- DBI::dbConnect(RSQLite::SQLite(), database_path,
                             flags = RSQLite::SQLITE_RO)
on.exit(DBI::dbDisconnect(connection), add = TRUE)

raw_rows <- spending_raw_report_rows(connection, versioning_applied = TRUE)
cat("LOADED    raw_rows=", nrow(raw_rows), "\n", sep = "")

evidence_scope <- contribution_cycle(raw_rows$contribution_receipt_date) %in%
  supported_cycles
scoped <- raw_rows[evidence_scope]
gate <- fec_receipt_countable(scoped) &
  fec_receipt_role_unresolved(fec_receipt_role(scoped))
refused <- scoped[gate]
cat("SCOPE     in_scope=", sum(evidence_scope), "\n", sep = "")
cat("REFUSED   gate=", nrow(refused), "\n", sep = "")
cat("DOLLARS   ", sprintf("%.2f", sum(suppressWarnings(as.numeric(
  refused$contribution_receipt_amount)), na.rm = TRUE)), "\n", sep = "")

# Street columns must exist on the frame and be all-NA for a pre-migration db.
for (column in c("contributor_street_1", "contributor_street_2")) {
  cat(column, ": present=", column %in% names(raw_rows),
      " non_blank=", sum(nzchar(trim_text(raw_rows[[column]])), na.rm = TRUE),
      "\n", sep = "")
}

data.table::fwrite(
  data.table::data.table(sub_id = as.character(refused$sub_id)),
  file.path(out_dir, "proof_patched_subids.csv"))
cat("DONE\n")
