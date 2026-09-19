suppressPackageStartupMessages(library(data.table))
options(width = 250, scipen = 99)
scratch <- "C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-mentat-uncommitted-reconcile-4089f1/72dc8732-42b9-4fb4-9b63-5cb0cba9d2db/scratchpad/v3_measure"
p4 <- readRDS(file.path(scratch, "pas2", "pas2_index_p4-2aa0b6678c-9df4df6216-9164c40709.rds"))
setDT(p4)
x <- p4[cycle == 2024L & committee_id == "C00864926" &
        transaction_amount %in% c(29685, 997600, 10454) &
        file_num %in% c(1759197, 1779689, 1788908)]
print(x[, .(committee_id, report_type, transaction_id, file_num, candidate_id,
            transaction_amount, transaction_date, transaction_type, memo_code,
            sub_id, include_in_total, exclusion_reason)])
cat("\nTRAN_IDs:", paste(unique(x$transaction_id), collapse = ", "), "\n")
