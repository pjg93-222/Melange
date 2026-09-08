script <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[[1L]])
project_root <- normalizePath(file.path(dirname(script), ".."), winslash = "/")
for (file in c("paths.R", "schema.R", "ingest.R", "collect.R", "fec_api.R", "report.R")) {
  source(file.path(project_root, "R", file), local = .GlobalEnv)
}
suppressPackageStartupMessages(library(data.table))
rows <- data.table(
  contributor_name = c("ACME", "ACME EXCHANGE", "ACME", "ACME EXCHANGE", "ACME"),
  filing_form = c("F3X", "F3X", "F3X", "", "F3X"),
  line_number = c("11AI", "17", "17", "", "11AI"),
  receipt_type_full = c("IN-KIND - USDC NOT LIQUIDATED", "25M USDC SOLD VIA ACME - PURCHASER UNKNOWN",
                        "CONTRIBUTION PREVIOUSLY DISCLOSED", "", ""),
  is_memo_leg = c(0L, 0L, 1L, 0L, 0L)
)
roles <- fec_receipt_role(rows)
stopifnot(identical(roles, c("contribution", "asset_liquidation", "previously_disclosed_memo", "intermediary_role_review", "contribution")))
stopifnot(identical(fec_receipt_role_excluded(roles), c(FALSE, TRUE, TRUE, TRUE, FALSE)))
connection <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
init_schema(connection)
for (table in c("contributions", "corporate_giving")) {
  stopifnot(all(c("filing_form", "receipt_type_full", "memo_text", "line_number", "back_reference_transaction_id") %in% DBI::dbListFields(connection, table)))
}
unit <- list(industry = "Crypto", company = "Acme", company_variants = "Acme", exclusions = character(), cycle = 2024L)
api_rows <- list(list(sub_id = "fixture-1", contributor_name = "ACME", committee_id = "C00000001", entity_type = "ORG",
                     contribution_receipt_amount = 10, contribution_receipt_date = "2024-01-01", filing_form = "F3X",
                     line_number = "17", receipt_type_full = "CONTRIBUTION PREVIOUSLY DISCLOSED", memo_code = "X",
                     memoed_subtotal = TRUE, transaction_id = "MEMO1", back_reference_transaction_id = "ORIGINAL1"))
corporate <- fec_api_corporate_records(connection, unit, api_rows, match_overrides = data.frame(), home_states = data.frame())
stopifnot(corporate$is_memo_leg == 1L, corporate$receipt_type_full == "CONTRIBUTION PREVIOUSLY DISCLOSED")
# Mimic an old browser row, then hydrate the same sub-ID from the API.
legacy <- copy(corporate)
legacy[, `:=`(filing_form = "", receipt_type_full = "", memo_code = "", memoed_subtotal = 0L, is_memo_leg = 0L)]
checkpoint_corporate_page(connection, legacy, "Acme", 2024L, "fixture", 1L, 1L)
checkpoint_corporate_page(connection, corporate, "Acme", 2024L, "fixture", 1L, 1L)
stored <- DBI::dbReadTable(connection, "corporate_giving")
stopifnot(nrow(stored) == 1L, stored$is_memo_leg == 1L, stored$memoed_subtotal == 1L,
          stored$back_reference_transaction_id == "ORIGINAL1", stored$receipt_type_full == "CONTRIBUTION PREVIOUSLY DISCLOSED")
DBI::dbDisconnect(connection)
cat("test_receipt_roles: PASS\n")
