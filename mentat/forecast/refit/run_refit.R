# Command line entry of the Giving Forecast refit pipeline.
#   Rscript run_refit.R --mode parity [--run-id <id>] [--no-tests]    rebuild the v1 bundle from raw inputs, compare, write a run folder
# Phase 1 implements parity mode only. `detect`, `refit` and `--rollback` belong to later phases and stop with a message.
# Environment: RF_RUNTIME, RF_RLIB, RF_INPUT_ROOT / RF_ROOT_<ALIAS>, RF_GLASSBOX_DIR, REFIT_OUT, REFIT_CORES (see R/rf_config.R).
fa <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
here <- if (length(fa)) dirname(normalizePath(sub("^--file=", "", fa[1]), winslash = "/")) else getwd()
assign(".RF_HOME", here, envir = globalenv())
source(file.path(here, "R", "rf_config.R"), encoding = "UTF-8")
rf_source_all(here)

args <- commandArgs(trailingOnly = TRUE)
opt <- function(name, default = NULL) { i <- match(name, args); if (is.na(i) || i == length(args)) default else args[i + 1L] }
mode <- opt("--mode", "parity")
if ("--rollback" %in% args || mode != "parity") {
  message("run_refit.R: mode '", if ("--rollback" %in% args) "--rollback" else mode, "' is not implemented in Phase 1 (only --mode parity)")
  quit(status = 2L)
}
res <- rf_run_parity(run_id = opt("--run-id"), run_tests = !("--no-tests" %in% args))
cat(sprintf("\nparity run %s -> %s\n", res$run_id, res$decision))
print(res$gates, row.names = FALSE)
cat("run folder:", res$dir, "\n")
quit(status = if (res$decision == "FAIL") 1L else 0L)
