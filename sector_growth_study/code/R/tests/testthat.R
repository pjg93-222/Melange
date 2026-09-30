# Run the testthat suite of the R port:
#   & "C:\Program Files\R\R-4.6.0\bin\Rscript.exe" "C:\Users\pgoff\Mentat\sector_growth_study\code\R\tests\testthat.R"
# Optional: SGS_NULL_REPS (default 200) sets the repetitions of the null p-value simulation.
if (!requireNamespace("testthat", quietly = TRUE)) .libPaths(c("C:/Users/pgoff/AppData/Local/R/win-library/4.6", .libPaths()))
library(testthat)
fa <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
here <- if (length(fa)) dirname(normalizePath(sub("^--file=", "", fa[1]), winslash = "/")) else getwd()
filter <- Sys.getenv("SGS_TEST_FILTER", unset = "")
res <- testthat::test_dir(file.path(here, "testthat"), reporter = testthat::ProgressReporter$new(show_praise = FALSE),
                          filter = if (nzchar(filter)) filter else NULL, stop_on_failure = FALSE)
df <- as.data.frame(res)
cat(sprintf("\nTOTAL: %d tests (test_that blocks), %d expectations; failed %d, errors %d, skipped %d, warnings %d\n",
            nrow(df), sum(df$nb), sum(df$failed), sum(df$error), sum(df$skipped), sum(df$warning)))
quit(status = if (sum(df$failed) + sum(df$error) > 0) 1L else 0L)
