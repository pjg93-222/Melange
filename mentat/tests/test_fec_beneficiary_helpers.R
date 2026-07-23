script_argument <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
stopifnot(length(script_argument) == 1L)
script_path <- normalizePath(
  sub("^--file=", "", script_argument[[1L]]),
  winslash = "/",
  mustWork = TRUE
)
project_root <- normalizePath(
  file.path(dirname(script_path), ".."),
  winslash = "/",
  mustWork = TRUE
)
source(file.path(project_root, "R", "paths.R"), local = .GlobalEnv)
source(file.path(project_root, "R", "ingest.R"), local = .GlobalEnv)

fec_mode_text_reference <- function(values) {
  value <- trim_text(values)
  value <- value[nzchar(value)]
  if (!length(value)) return("")
  counts <- sort(table(value), decreasing = TRUE)
  sort(names(counts)[counts == counts[[1L]]])[[1L]]
}
fec_join_unique_reference <- function(values) {
  value <- sort(unique(trim_text(values)))
  paste(value[nzchar(value)], collapse = "; ")
}
fec_min_text_reference <- function(values) {
  value <- sort(unique(trim_text(values)))
  value <- value[nzchar(value)]
  if (length(value)) value[[1L]] else ""
}
fec_max_text_reference <- function(values) {
  value <- sort(unique(trim_text(values)))
  value <- value[nzchar(value)]
  if (length(value)) value[[length(value)]] else ""
}

source(
  file.path(project_root, "R", "fec_beneficiary.R"),
  local = .GlobalEnv
)

set.seed(20260723)
pool <- c("", " ", NA_character_, "Alpha", "ALPHA", "Beta", "Gamma", "Zeta")
for (case in seq_len(5000L)) {
  values <- sample(pool, sample.int(50L, 1L) - 1L, replace = TRUE)
  stopifnot(
    identical(fec_mode_text(values), fec_mode_text_reference(values)),
    identical(fec_join_unique(values), fec_join_unique_reference(values)),
    identical(fec_min_text(values), fec_min_text_reference(values)),
    identical(fec_max_text(values), fec_max_text_reference(values))
  )
}

# Candidate/source fields are normally constant within downstream groups.
# This benchmark pins the fast path that matters for the 870k-row workload.
constant_groups <- rep(list(rep("Candidate Name", 8L)), 20000L)
reference_seconds <- unname(system.time(
  reference <- vapply(
    constant_groups,
    fec_mode_text_reference,
    character(1L)
  )
)[["elapsed"]])
optimized_seconds <- unname(system.time(
  optimized <- vapply(constant_groups, fec_mode_text, character(1L))
)[["elapsed"]])
stopifnot(identical(optimized, reference))
cat(sprintf(
  paste0(
    "test_fec_beneficiary_helpers: randomized=5000 groups=%d ",
    "reference=%.3fs optimized=%.3fs speedup=%.1fx PASS\n"
  ),
  length(constant_groups),
  reference_seconds,
  optimized_seconds,
  reference_seconds / max(optimized_seconds, .Machine$double.eps)
))
