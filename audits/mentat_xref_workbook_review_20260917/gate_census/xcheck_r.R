# Re-classify the 2,070 rows of the failed Banking run's own receipt-review CSV
# with TODAY's fec_receipt_role(), and compare against the receipt_role the
# Sep-12 run stamped into that same CSV. Read-only.
args <- commandArgs(trailingOnly = TRUE)
out_dir <- normalizePath(args[[1L]], winslash = "/", mustWork = TRUE)

MENTAT_PROJECT_ROOT <- "C:/Users/pgoff/Mentat/mentat"
MENTAT_INDUSTRY <- "Banking"
for (module in c("paths.R", "schema.R", "ingest.R", "collect.R")) {
  source(file.path(MENTAT_PROJECT_ROOT, "R", module), local = .GlobalEnv)
}
require_package("data.table")

path <- file.path(
  "C:/Users/pgoff/Mentat/mentat/.cache/industry-report/banking",
  "industry_data-4abdea581b99cec1.json.pending-42976.receipt-review.csv")
rows <- data.table::fread(path, colClasses = "character", na.strings = NULL)
cat("csv rows:", nrow(rows), "\n")

rows[, role_sep12 := receipt_role]
rows[, role_today := fec_receipt_role(rows)]
rows[, unresolved_sep12 := fec_receipt_role_unresolved(role_sep12)]
rows[, unresolved_today := fec_receipt_role_unresolved(role_today)]
rows[, amount := suppressWarnings(as.numeric(contribution_receipt_amount))]

cat("\n-- Sep-12 role (as stamped in the CSV) x TODAY's role --\n")
print(table(rows$role_sep12, rows$role_today))

cat("\n-- still refused by today's classifier --\n")
cat("rows:", sum(rows$unresolved_today),
    " dollars:", format(sum(rows$amount[rows$unresolved_today], na.rm = TRUE),
                        big.mark = ",", nsmall = 2), "\n")
cat("-- no longer refused --\n")
cat("rows:", sum(!rows$unresolved_today),
    " dollars:", format(sum(rows$amount[!rows$unresolved_today], na.rm = TRUE),
                        big.mark = ",", nsmall = 2), "\n")

data.table::fwrite(
  rows[, .(sub_id, company, filing_form, line_number, receipt_type_full,
           memo_text, amount, role_sep12, role_today,
           unresolved_sep12, unresolved_today)],
  file.path(out_dir, "banking_xcheck_reclassified.csv"), bom = TRUE)
cat("\nwrote banking_xcheck_reclassified.csv\n")
