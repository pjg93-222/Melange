# Proposed manifest and registry changes (FEEDS_SPEC 7.5-5). The ingest NEVER edits registry\*.json or inputs.json (of the refit
# or of itself): it writes proposed_inputs.json and proposed_registry_patch.json next to its receipt and the owner applies them
# (APPLY = Paul; the refit's gate G1 keeps pinned hashes).

# One proposed inputs.json entry. `pinned` is TRUE for raw files (their sha256 must not change) and FALSE for derived feeds.
.fi_manifest_entry <- function(role, path, purpose, pinned, vintage = "", inputs_sha256 = NULL, code_sha256 = NULL) {
  e <- list(role = role, path = path, sha256 = rf_sha256(path), bytes = as.integer(file.size(path)), pinned = pinned, purpose = purpose,
            vintage = vintage, supplied_by = "giving-forecast-ingest")
  if (!is.null(inputs_sha256)) e$inputs_sha256 <- as.list(inputs_sha256)
  if (!is.null(code_sha256)) e$code_sha256 <- code_sha256
  e
}

# Entries for the IBISWorld feed: each vaulted PDF / xlsx that fed an edition, and the four derived CSVs as feed:<name>.
fi_manifest_ibis <- function(editions, outputs, code_sha) {
  used <- editions[editions$status %in% c("checked", "review_required") & !is.na(editions$vault_path) & !is.na(editions$code), , drop = FALSE]
  raw <- lapply(seq_len(nrow(used)), function(i) {
    ext <- if (identical(used$layout[i], "xlsx")) "ibis_xlsx" else "ibis_pdf"
    .fi_manifest_entry(sprintf("%s:%s:%s", ext, used$code[i], used$edition_month[i]), used$vault_path[i], "raw", TRUE, used$edition_month[i])
  })
  in_sha <- used$source_sha256
  feeds <- lapply(names(outputs), function(nm) .fi_manifest_entry(paste0("feed:", nm), outputs[[nm]], "derived", FALSE, inputs_sha256 = in_sha, code_sha256 = code_sha))
  c(raw, feeds)
}

# Entries for OpenSecrets envelopes written under outputs/os (roles of SPEC 3.5).
fi_manifest_os <- function(envelope_files, industry_id, code_sha) {
  lapply(names(envelope_files), function(role) .fi_manifest_entry(role, envelope_files[[role]], "raw", TRUE, code_sha256 = NULL))
}

fi_write_proposals <- function(run_dir, entries, registry_patch, note = "") {
  ip <- file.path(run_dir, "proposed_inputs.json")
  rp <- file.path(run_dir, "proposed_registry_patch.json")
  rf_write_json_atomic(list(schema_version = 1L, note = paste("PROPOSED entries for the refit's registry/inputs.json; the ingest never applies them.", note), inputs = entries), ip)
  rf_write_json_atomic(list(schema_version = 1L, note = paste("PROPOSED patch for the refit's registry/industries.json and the ingest's registry/feeds.json; never applied automatically.", note),
                            patch = registry_patch), rp)
  list(inputs = ip, registry_patch = rp)
}
