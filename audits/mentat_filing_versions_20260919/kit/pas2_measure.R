# Read-only measurement of what parser version "4" ("Unresolved filing
# relationship") costs versus version "3", from the two cached indexes.
# Runs against SCRATCH COPIES of the .rds caches; nothing under C:\Users\pgoff\Mentat
# is opened for writing and no FEC source file is re-read.
suppressPackageStartupMessages(library(data.table))
options(datatable.print.class = FALSE, width = 200, scipen = 99)

scratch <- "C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-mentat-uncommitted-reconcile-4089f1/72dc8732-42b9-4fb4-9b63-5cb0cba9d2db/scratchpad/v3_measure"
pas2 <- file.path(scratch, "pas2")
p4_file <- file.path(pas2, "pas2_index_p4-2aa0b6678c-9df4df6216-9164c40709.rds")
p3_file <- file.path(pas2, "pas2_index_p3-2aa0b6678c-9df4df6216-9164c40709.rds")
p3_cycle_files <- c(
  "2022" = file.path(pas2, "pas2_index_p3-2aa0b6678c.rds"),
  "2024" = file.path(pas2, "pas2_index_p3-9df4df6216.rds"),
  "2026" = file.path(pas2, "pas2_index_p3-9164c40709.rds"))

money <- function(x) format(round(sum(x, na.rm = TRUE), 2), big.mark = ",", nsmall = 2)

p4 <- readRDS(p4_file); setDT(p4)
p3 <- readRDS(p3_file); setDT(p3)

cat("=== COLUMN SETS ===\n")
cat("p4 (", ncol(p4), "):", paste(names(p4), collapse = ", "), "\n")
cat("p3 (", ncol(p3), "):", paste(names(p3), collapse = ", "), "\n")
cat("only in p4:", paste(setdiff(names(p4), names(p3)), collapse = ", "), "\n")
cat("only in p3:", paste(setdiff(names(p3), names(p4)), collapse = ", "), "\n")
shared <- intersect(names(p3), names(p4))
cat("alignment: compared on the", length(shared), "shared columns; row identity is",
    "(cycle, sub_id) where sub_id is non-empty.\n\n")

cat("=== PER-CYCLE TOTALS: p3 vs p4 ===\n")
totals <- merge(
  p3[, .(p3_rows = .N, p3_included_rows = sum(include_in_total == "Yes"),
         p3_included_dollars = sum(transaction_amount[include_in_total == "Yes"], na.rm = TRUE)), by = cycle],
  p4[, .(p4_rows = .N, p4_included_rows = sum(include_in_total == "Yes"),
         p4_included_dollars = sum(transaction_amount[include_in_total == "Yes"], na.rm = TRUE)), by = cycle],
  by = "cycle")
totals[, `:=`(delta_rows = p4_included_rows - p3_included_rows,
              delta_dollars = p4_included_dollars - p3_included_dollars)]
print(totals)
cat("\nTOTAL across cycles: p3 included", money(totals$p3_included_dollars),
    "| p4 included", money(totals$p4_included_dollars),
    "| delta", money(totals$delta_dollars), "\n\n")

cat("=== p3 PER-CYCLE EXCLUSION REASONS ===\n")
print(dcast(p3[, .(rows = .N, dollars = round(sum(transaction_amount, na.rm = TRUE), 2)),
               by = .(cycle, exclusion_reason)], exclusion_reason ~ cycle,
            value.var = c("rows", "dollars"), fill = 0))
cat("\n=== p4 PER-CYCLE EXCLUSION REASONS ===\n")
print(dcast(p4[, .(rows = .N, dollars = round(sum(transaction_amount, na.rm = TRUE), 2)),
               by = .(cycle, exclusion_reason)], exclusion_reason ~ cycle,
            value.var = c("rows", "dollars"), fill = 0))

# version_key is dropped before the index is saved (fec_beneficiary.R:469-472).
# Rebuild it exactly as fec_build_pas2_index() does; rows are stored in
# original_order within each cycle, so .I reproduces original_order.
p4[, original_order := seq_len(.N), by = cycle]
p4[, version_key := ifelse(nzchar(transaction_id),
                           paste(committee_id, report_type, transaction_id, sep = "|"),
                           paste0("SUB|", ifelse(nzchar(sub_id), sub_id, original_order)))]
# by = .(cycle, version_key): fec_build_pas2_index() groups inside one cycle's
# lapply() pass, so the same version_key in two cycles is two groups.
p4[, competing_versions := as.integer(
  sum(exact_duplicate == 0L) > 1L & !startsWith(version_key[[1L]], "SUB|")), by = .(cycle, version_key)]
p4[, no_candidate_id := as.integer(!nzchar(candidate_id) & memo_code != "X")]

stopifnot(all(p4[unresolved_version == 1L, competing_versions == 1L | no_candidate_id == 1L]))
stopifnot(all(p4[competing_versions == 1L | no_candidate_id == 1L, unresolved_version == 1L]))
cat("\nreconstruction check: the rebuilt flags reproduce unresolved_version exactly.\n")

unres <- p4[exclusion_reason == "Unresolved filing relationship"]
unres[, bucket := fifelse(competing_versions == 1L & no_candidate_id == 1L, "both",
                  fifelse(competing_versions == 1L, "(i) competing versions of one version_key",
                          "(ii) no candidate_id"))]
cat("\n=== p4 'Unresolved filing relationship' SPLIT ===\n")
print(unres[, .(rows = .N, dollars = round(sum(transaction_amount, na.rm = TRUE), 2),
                committees = uniqueN(committee_id), candidates = uniqueN(candidate_id[nzchar(candidate_id)])),
            by = .(cycle, bucket)][order(cycle, bucket)])
cat("\n=== p4 'Unresolved filing relationship' TOTAL per cycle ===\n")
print(unres[, .(rows = .N, dollars = round(sum(transaction_amount, na.rm = TRUE), 2),
                positive_dollars = round(sum(transaction_amount[transaction_amount > 0], na.rm = TRUE), 2),
                distinct_committees = uniqueN(committee_id),
                distinct_candidates = uniqueN(candidate_id[nzchar(candidate_id)]),
                version_groups = uniqueN(version_key)), by = cycle][order(cycle)])
cat("\nacross all cycles: rows", nrow(unres),
    "| dollars", money(unres$transaction_amount),
    "| distinct committees", uniqueN(unres$committee_id),
    "| distinct candidates", uniqueN(unres[nzchar(candidate_id), candidate_id]), "\n")

cat("\n=== ROW-SET DIFFERENCE p3 vs p4 (they are not the same row set) ===\n")
p3_ids <- p3[, paste(cycle, sub_id)]
p4_ids <- p4[, paste(cycle, sub_id)]
cat("rows only in p4:", sum(!p4_ids %in% p3_ids), "| rows only in p3:", sum(!p3_ids %in% p4_ids), "\n")
extra <- p4[!p4_ids %in% p3_ids]
if (nrow(extra)) {
  cat("p4-only rows by cycle/blank-sub_id/include:\n")
  print(extra[, .(rows = .N, blank_sub_id = sum(!nzchar(sub_id)),
                  dollars = round(sum(transaction_amount, na.rm = TRUE), 2)),
              by = .(cycle, include_in_total, exclusion_reason)][order(cycle)])
}

cat("\n=== HOW MANY OF THOSE ROWS p3 WAS COUNTING ===\n")
key3 <- p3[nzchar(sub_id), .(cycle, sub_id, p3_include = include_in_total,
                             p3_reason = exclusion_reason, p3_amount = transaction_amount)]
joined <- merge(unres[nzchar(sub_id), .(cycle, sub_id, bucket, transaction_amount)],
                key3, by = c("cycle", "sub_id"), all.x = TRUE)
print(joined[, .(rows = .N, dollars = round(sum(transaction_amount, na.rm = TRUE), 2)),
             by = .(cycle, bucket, p3_include)][order(cycle, bucket, p3_include)])
cat("\nrows newly excluded by p4 that p3 counted:",
    joined[p3_include == "Yes", .N], "| dollars",
    money(joined[p3_include == "Yes", transaction_amount]), "\n")

cat("\n=== 15 LARGEST UNRESOLVED VERSION GROUPS (competing versions only) ===\n")
groups <- unres[competing_versions == 1L, .(
  rows = .N,
  group_dollars = round(sum(transaction_amount, na.rm = TRUE), 2),
  max_row_dollars = round(max(transaction_amount, na.rm = TRUE), 2),
  amounts = paste(format(round(transaction_amount, 2), trim = TRUE), collapse = " / "),
  file_nums = paste(sort(unique(file_num)), collapse = " / "),
  distinct_file_nums = uniqueN(file_num),
  committee_id = committee_id[[1L]],
  candidate_id = paste(sort(unique(candidate_id)), collapse = " / "),
  recipient = recipient_name[[1L]],
  report_types = paste(sort(unique(report_type)), collapse = "/"),
  types = paste(sort(unique(transaction_type)), collapse = "/")),
  by = .(cycle, version_key)][order(-max_row_dollars)][1:15]
print(groups[, .(cycle, committee_id, candidate_id, recipient, rows, distinct_file_nums,
                 max_row_dollars, group_dollars, amounts, file_nums, types)])

cat("\n=== SINGLE-FILING vs MULTI-FILING COMPETING-VERSION GROUPS ===\n")
span <- unres[competing_versions == 1L, .(
  files = uniqueN(file_num),
  rows = .N,
  dollars = sum(transaction_amount, na.rm = TRUE)), by = .(cycle, version_key)]
span[, span := fifelse(files > 1L, "multi_filing (a header could settle it)",
                       "single_filing (no header can settle it)")]
print(span[, .(groups = .N, rows = sum(rows), dollars = round(sum(dollars), 2)),
           by = .(cycle, span)][order(cycle, span)])

cat("\n=== PER-CYCLE p3 CACHE CROSS-CHECK (per-cycle .rds files) ===\n")
for (cy in names(p3_cycle_files)) {
  one <- readRDS(p3_cycle_files[[cy]]); setDT(one)
  cat(sprintf("p3 %s: rows=%d included=%d dollars=%s (combined-cache rows=%d included=%d dollars=%s)\n",
      cy, nrow(one), sum(one$include_in_total == "Yes"),
      money(one$transaction_amount[one$include_in_total == "Yes"]),
      p3[cycle == as.integer(cy), .N], p3[cycle == as.integer(cy) & include_in_total == "Yes", .N],
      money(p3[cycle == as.integer(cy) & include_in_total == "Yes", transaction_amount])))
  rm(one); invisible(gc())
}
cat("\nDONE\n")
