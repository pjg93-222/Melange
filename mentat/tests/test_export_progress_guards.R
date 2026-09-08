suppressPackageStartupMessages(library(data.table))
source(if (file.exists("mentat/R/export_guards.R")) "mentat/R/export_guards.R" else "R/export_guards.R")
p <- data.table(company = "Fixture", cycle = 2024L,
  variant_set = c("P1_employer:legacy", "P1_employer:current"),
  records_total = c(100, 50), zero_verified = c(0L, 1L),
  updated_at = c("2026-07-01T12:00:00.000-0400", "2026-09-08T12:00:00.000-0400"))
a <- data.table(company = "Fixture", cycle = 2024L, unit_id = "P1_employer:current",
  kind = "employer", rows_seen = 50, records_total = 50, fetched_complete = 1L,
  stored_complete = 1L, updated_at = "2026-09-08T12:00:01.000-0400")
v <- mentat_guard_progress_views(p, a)
stopifnot(nrow(v$completeness) == 0L, nrow(v$zero) == 1L, v$api_guard$passed)

# A partial or unstamped search must never clear the previous warning.
a[, stored_complete := 0L]
v <- mentat_guard_progress_views(p, a)
stopifnot(nrow(v$completeness) == 2L, !v$api_guard$passed)
a[, stored_complete := 1L]
p[, zero_verified := 0L]
stopifnot(nrow(mentat_guard_progress_views(p, a)$completeness) == 2L)
p[variant_set == "P1_employer:current", zero_verified := 1L]
a[, rows_seen := 49]
stopifnot(!mentat_guard_progress_views(p, a)$api_guard$passed)
a[, rows_seen := 50]
p[variant_set == "P1_employer:legacy", updated_at := "2026-09-09T12:00:00.000-0400"]
stopifnot(nrow(mentat_guard_progress_views(p, a)$completeness) == 2L)

# A current verified zero supersedes historical unverified zeros.
p[, records_total := 0]
p[variant_set == "P1_employer:legacy", updated_at := "2026-07-01T12:00:00.000-0400"]
a[, `:=`(records_total = 0, rows_seen = 0)]
stopifnot(mentat_guard_zero_provenance(mentat_guard_progress_views(p, a)$zero)$passed)
cat("test_export_progress_guards: PASS\n")
