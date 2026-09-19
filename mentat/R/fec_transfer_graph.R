# OTH cash-transfer indexes are built by tools/fec_transfer_graph.py.
# Descendant activity stays separate from the directly funded committee views.
fec_transfer_context <- function(directory, roots, candidate_links, cycles, max_depth = 3L) {
  edges <- list(); coverage <- list(); expanded <- data.table::copy(roots)
  for (target_cycle in cycles) {
    path <- file.path(directory, paste0("oth", substr(target_cycle, 3, 4)), "transfer-info.json")
    if (!file.exists(path)) {
      coverage[[length(coverage) + 1L]] <- list(cycle = target_cycle, status = "missing_transfer_source")
      next
    }
    index <- jsonlite::fromJSON(path)
    if (is.null(index$version) || index$version != 3L) {
      coverage[[length(coverage) + 1L]] <- list(cycle = target_cycle,
        status = "stale_transfer_index", unresolved_all_sources = TRUE)
      next
    }
    edge_path <- file.path(dirname(path), "transfer-edges.csv")
    if (is.null(index$edges_sha256) ||
        digest::digest(file = edge_path, algo = "sha256") != index$edges_sha256)
      stop("Transfer edge checksum failed: ", edge_path)
    rows <- data.table::fread(edge_path, showProgress = FALSE)
    coverage[[length(coverage) + 1L]] <- list(cycle = target_cycle, status = "indexed",
      source_sha256 = index$source_sha256, counts = index$counts,
      ledger_path = index$ledger_path, max_depth = max_depth,
      unresolved_sources = as.list(index$unresolved_sources),
      unresolved_all_sources = isTRUE(index$unresolved_all_sources))
    if (!nrow(rows)) next
    stops <- candidate_links[cycle == target_cycle & designation %in% c("A", "P"), committee_id]
    visited <- roots[cycle == target_cycle & preliminary_crypto_funding > 0, committee_id]
    frontier <- visited
    for (depth in seq_len(max_depth)) {
      next_ids <- unique(rows[source %in% frontier & amount > 0, destination])
      next_ids <- setdiff(next_ids, c(visited, stops))
      visited <- unique(c(visited, next_ids)); frontier <- next_ids
      if (!length(frontier)) break
    }
    edges[[length(edges) + 1L]] <- rows[source %in% visited]
    missing <- setdiff(visited, expanded[cycle == target_cycle, committee_id])
    if (length(missing)) expanded <- data.table::rbindlist(list(expanded,
      data.table::data.table(cycle = target_cycle, committee_id = missing,
        committee_name = missing, recipient_category = "", preliminary_crypto_funding = 0)), fill = TRUE)
  }
  list(universe = expanded, edges = data.table::rbindlist(edges, fill = TRUE), coverage = coverage)
}
