# Classify the distinct classifier-input tuples with the AUTHORITATIVE R
# classifier, fec_receipt_role() from mentat/R/collect.R:39.
args <- commandArgs(trailingOnly = TRUE)
out_dir <- normalizePath(args[[1L]], winslash = "/", mustWork = TRUE)

MENTAT_PROJECT_ROOT <- "C:/Users/pgoff/Mentat/mentat"
MENTAT_INDUSTRY <- "Crypto"  # unused by the classifier; set so no guard fires

for (module in c("paths.R", "schema.R", "ingest.R", "collect.R")) {
  source(file.path(MENTAT_PROJECT_ROOT, "R", module), local = .GlobalEnv)
}
require_package("data.table")

rows <- data.table::fread(file.path(out_dir, "twin_inputs.csv"),
                          colClasses = "character", na.strings = NULL)
cat("tuples:", nrow(rows), "\n")
rows[, r_role := fec_receipt_role(rows)]
rows[, r_unresolved := fec_receipt_role_unresolved(r_role)]
rows[, r_excluded := fec_receipt_role_excluded(r_role)]
data.table::fwrite(rows, file.path(out_dir, "twin_r_roles.csv"))
cat("wrote twin_r_roles.csv\n")
print(table(rows$r_role))
