# READ-ONLY reproduction of the receipt-evidence gate that
# tools/export_crypto_spending_data.R:225 applies before publishing.
#
# usage: Rscript gate_census.R <mentat.db> <Industry Label> <slug> <out_dir>
#
# Writes ONLY into <out_dir>. Opens the database read-only. Never calls
# apply_amendment_versioning (we pass versioning_applied = TRUE exactly as the
# exporter does, which is what makes the load read-only).

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4L) {
  stop("usage: Rscript gate_census.R <mentat.db> <Industry Label> <slug> <out_dir>",
       call. = FALSE)
}

database_path <- normalizePath(args[[1L]], winslash = "/", mustWork = TRUE)
industry_label <- trimws(args[[2L]])
slug <- trimws(args[[3L]])
out_dir <- normalizePath(args[[4L]], winslash = "/", mustWork = TRUE)

MENTAT_PROJECT_ROOT <- "C:/Users/pgoff/Mentat/mentat"

# THE TRAP: MENTAT_INDUSTRY is a global R variable, not an environment variable.
# Every module guards with if (!exists("MENTAT_INDUSTRY")), so assigning it in
# .GlobalEnv BEFORE sourcing is what makes report_industry_filter() query the
# right industry. Leaving it unset silently queries Crypto.
MENTAT_INDUSTRY <- industry_label

# Same 14 modules the exporter sources, in the same order.
for (module in c(
  "paths.R", "schema.R", "ingest.R", "fec_page.R", "collect.R",
  "fec_api.R", "reconcile.R", "report.R", "fec_beneficiary.R",
  "identity_components.R", "export_guards.R", "fec_transfer_graph.R",
  "state_destinations.R", "tidy_stage.R"
)) {
  source(file.path(MENTAT_PROJECT_ROOT, "R", module), local = .GlobalEnv)
}

require_package("data.table")
require_package("DBI")
require_package("RSQLite")

# ---------------------------------------------------------------------------
# DEVIATION D1 (documented in SUMMARY.md).
#
# report.R:2032 and :2051 SELECT contributor_street_1 / contributor_street_2
# unconditionally. Commit d78cf0b8f added them. EVERY hydrated snapshot in this
# census predates that commit, so the live exporter aborts with
# "no such column: contributor_street_1" inside spending_raw_report_rows(),
# BEFORE the gate at export_crypto_spending_data.R:225 is ever reached.
#
# This override is report.R:2011-2083 copied verbatim with exactly one change:
# the two street columns go through the same tolerant projection report.R
# already applies to absent receipt metadata (receipt_projection's
# "NULL AS <field>", report.R:2018-2026). Neither column is read by
# fec_receipt_role(), fec_receipt_countable(), fec_receipt_role_unresolved()
# or mentat_memo_duplicate_plan(), so the refusal set is unaffected. Verified
# by grep: the only consumers are the exporter's .() projection at :216-218.
# ---------------------------------------------------------------------------
spending_raw_report_rows <- function(connection, versioning_applied = FALSE) {
  require_package("data.table")
  if (!isTRUE(versioning_applied)) {
    stop("census refuses to run amendment versioning (it writes).", call. = FALSE)
  }
  optional_projection <- function(table, fields) {
    present <- DBI::dbListFields(connection, table)
    paste0(paste(vapply(fields, function(field) {
      if (field %in% present) field else paste0("NULL AS ", field)
    }, character(1L)), collapse = ", "), ",")
  }
  receipt_projection <- function(table) {
    optional_projection(table, c(
      "receipt_type_full", "filing_form", "receipt_type", "line_number",
      "line_number_label", "file_num", "report_year", "report_type",
      "memo_code", "memoed_subtotal", "memo_text",
      "back_reference_transaction_id", "back_reference_schedule_name"))
  }
  street_projection <- function(table) {
    optional_projection(table, c("contributor_street_1", "contributor_street_2"))
  }
  people <- data.table::as.data.table(DBI::dbGetQuery(
    connection,
    paste(
      "SELECT contributor_name, committee_name, contribution_receipt_date,",
      "contribution_receipt_amount, contributor_city, contributor_state,",
      "contributor_zip, contributor_employer, contributor_occupation,",
      street_projection("contributions"), "company, sub_id, matched_variant,",
      "committee_id, recipient_committee_type, recipient_committee_designation,",
      "two_year_transaction_period, entity_type, is_entity_contributor,",
      receipt_projection("contributions"), "transaction_id, pdf_url,",
      "conduit_committee_id, conduit_committee_name, is_conduit_leg,",
      "is_memo_leg, is_passthrough_leg, memo_review, possible_amendment, is_refund,",
      "superseded_by_amendment, duplicate_filing_version, duplicate_memo,",
      "company_match_status, company_match_reason, excluded_reason,",
      "'contributions' AS source_table,",
      "CASE WHEN is_entity_contributor=1 THEN 'CORPORATE'",
      "ELSE 'CONTRIBUTION' END AS record_type",
      paste0("FROM contributions WHERE ", report_industry_filter())
    )
  ))
  corporate <- data.table::as.data.table(DBI::dbGetQuery(
    connection,
    paste(
      "SELECT contributor_name, committee_name, contribution_receipt_date,",
      "contribution_receipt_amount, contributor_city, contributor_state,",
      "contributor_zip, contributor_employer, contributor_occupation,",
      street_projection("corporate_giving"), "company, sub_id, matched_variant,",
      "committee_id, recipient_committee_type, recipient_committee_designation,",
      "cycle AS two_year_transaction_period, entity_type, is_entity_contributor,",
      receipt_projection("corporate_giving"), "transaction_id, pdf_url, '' AS conduit_committee_id,",
      "'' AS conduit_committee_name, is_conduit_leg, is_memo_leg,",
      "is_passthrough_leg, 0 AS memo_review,",
      "CASE WHEN original_sub_id IS NOT NULL AND TRIM(original_sub_id)<>''",
      "OR UPPER(TRIM(amendment_indicator)) IN ('A','C','T') THEN 1 ELSE 0 END",
      "AS possible_amendment,",
      "CASE WHEN contribution_receipt_amount < 0 THEN 1 ELSE 0 END AS is_refund,",
      "superseded_by_amendment, duplicate_filing_version, duplicate_memo,",
      "company_match_status, company_match_reason, excluded_reason,",
      "'corporate_giving' AS source_table,",
      "'CORPORATE' AS record_type",
      paste0("FROM corporate_giving WHERE ", report_industry_filter())
    )
  ))
  rows <- data.table::rbindlist(list(people, corporate), use.names = TRUE, fill = TRUE)
  if (!nrow(rows)) return(rows)
  rows[, source_priority :=
    ifelse(company_match_status == "accepted", 0L, 2L) +
      ifelse(record_type == "CORPORATE", 1L, 0L)]
  data.table::setorder(rows, source_priority, sub_id)
  rows <- unique(rows, by = "sub_id")
  rows[, source_priority := NULL]
  rows[, receipt_role := fec_receipt_role(rows)]
  memo_plan <- mentat_memo_duplicate_plan(rows)
  rows[, `:=`(duplicate_memo = memo_plan$duplicate_memo,
              duplicate_of_sub_id = memo_plan$duplicate_of_sub_id,
              duplicate_reason = memo_plan$duplicate_reason)]
  rows[]
}

# Copied verbatim from tools/export_crypto_spending_data.R:97 and :133-137.
# These live in the exporter script itself, not in a sourced module.
supported_cycles_local <- c(2022L, 2024L, 2026L)
contribution_cycle_local <- function(values) {
  dates <- normalize_reconcile_date(values)
  years <- as.integer(format(dates, "%Y"))
  years + years %% 2L
}
# MENTAT_CYCLE_FILTER would narrow supported_cycles before the gate runs
# (exporter lines 112-131). Refuse to run under one so the census is the
# full-payload refusal set.
if (nzchar(trimws(Sys.getenv("MENTAT_CYCLE_FILTER", unset = "")))) {
  stop("MENTAT_CYCLE_FILTER is set; census must run unfiltered.", call. = FALSE)
}

stopifnot(identical(MENTAT_INDUSTRY, industry_label))
cat(sprintf("INDUSTRY  label=%s slug=%s\n", MENTAT_INDUSTRY, slug))
cat(sprintf("FILTER    %s\n", report_industry_filter()))
cat(sprintf("RULESET   %s\n", file.path(mentat_input_dir(), "fec_receipt_rules.json")))
cat(sprintf("DATABASE  %s\n", database_path))
flush(stdout())

connection <- DBI::dbConnect(
  RSQLite::SQLite(),
  database_path,
  flags = RSQLite::SQLITE_RO
)
on.exit(DBI::dbDisconnect(connection), add = TRUE)

# Exporter line 208. versioning_applied = TRUE skips apply_amendment_versioning,
# which is the only writing step in this path.
raw_rows <- spending_raw_report_rows(connection, versioning_applied = TRUE)
cat(sprintf("LOADED    raw_rows=%d\n", nrow(raw_rows)))
flush(stdout())
if (!nrow(raw_rows)) {
  stop("ZERO ROWS LOADED for ", industry_label,
       " - this is a FAILED check, not a clean one.", call. = FALSE)
}

for (column in c("contributor_street_1", "contributor_street_2")) {
  if (!column %in% names(raw_rows)) raw_rows[, (column) := NA_character_]
}

# Exporter line 219.
evidence_scope <- contribution_cycle_local(raw_rows$contribution_receipt_date) %in%
  supported_cycles_local
cat(sprintf("SCOPE     in_scope=%d out_of_scope=%d\n",
            sum(evidence_scope), sum(!evidence_scope)))

# Exporter lines 220-221 (the review CSV the failed run wrote).
csv_mask <- evidence_scope & fec_receipt_countable(raw_rows) &
  fec_receipt_role_unresolved(raw_rows$receipt_role)

# Exporter line 225: fec_assert_receipt_evidence(raw_rows[evidence_scope]).
# Reproduced by inlining the gate body against the same subset so the refusal
# set is the gate's own, not the CSV's.
scoped <- raw_rows[evidence_scope]
gate_mask_scoped <- fec_receipt_countable(scoped) &
  fec_receipt_role_unresolved(fec_receipt_role(scoped))
gate_mask <- rep(FALSE, nrow(raw_rows))
gate_mask[which(evidence_scope)] <- gate_mask_scoped

cat(sprintf("REFUSED   gate=%d review_csv_logic=%d agree=%s\n",
            sum(gate_mask), sum(csv_mask), identical(gate_mask, csv_mask)))

refused <- raw_rows[gate_mask]
cat(sprintf("DOLLARS   %.2f\n",
            sum(suppressWarnings(as.numeric(
              refused$contribution_receipt_amount)), na.rm = TRUE)))
flush(stdout())

# The exact text the classifier keys on: normalized(receipt_type_full) then
# normalized(memo_text), pasted and trimmed (collect.R:46-49).
normalized <- function(x) trim_text(gsub("[^A-Z0-9]+", " ", x))
column_of <- function(rows, name) {
  if (!name %in% names(rows)) return(rep("", nrow(rows)))
  value <- toupper(trim_text(rows[[name]]))
  value[is.na(value)] <- ""
  value
}
receipt_description <- normalized(column_of(refused, "receipt_type_full"))
memo_description <- normalized(column_of(refused, "memo_text"))

out <- data.table::data.table(
  sub_id = as.character(refused$sub_id),
  company = as.character(refused$company),
  cycle = as.character(refused$two_year_transaction_period),
  contribution_receipt_date = as.character(refused$contribution_receipt_date),
  filing_form = as.character(refused$filing_form),
  line_number = as.character(refused$line_number),
  line_number_label = as.character(refused$line_number_label),
  receipt_type = as.character(refused$receipt_type),
  receipt_type_full = as.character(refused$receipt_type_full),
  memo_text = as.character(refused$memo_text),
  memo_code = as.character(refused$memo_code),
  normalized_description = trim_text(paste(receipt_description, memo_description)),
  contributor_name = as.character(refused$contributor_name),
  entity_type = as.character(refused$entity_type),
  committee_id = as.character(refused$committee_id),
  committee_name = as.character(refused$committee_name),
  amount = suppressWarnings(as.numeric(refused$contribution_receipt_amount)),
  record_type = as.character(refused$record_type),
  source_table = as.character(refused$source_table),
  reason = as.character(refused$receipt_role)
)
out[, industry := industry_label]

data.table::fwrite(out, file.path(out_dir, paste0(slug, "_refused.csv")),
                   bom = TRUE)

# One-line machine-readable receipt for the summary builder.
receipt <- data.table::data.table(
  slug = slug,
  industry = industry_label,
  database = database_path,
  raw_rows = nrow(raw_rows),
  in_scope = sum(evidence_scope),
  refused_rows = sum(gate_mask),
  refused_dollars = sum(suppressWarnings(as.numeric(
    refused$contribution_receipt_amount)), na.rm = TRUE),
  csv_logic_rows = sum(csv_mask),
  masks_agree = identical(gate_mask, csv_mask)
)
data.table::fwrite(receipt, file.path(out_dir, paste0(slug, "_receipt.csv")))
cat("DONE\n")
