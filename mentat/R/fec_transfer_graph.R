# OTH cash-transfer indexes are built by tools/fec_transfer_graph.py.
# Discover the whole observed network; candidate activity stays separate from
# donor receipts and conditional allocation estimates.
fec_transfer_context <- function(directory, roots, candidate_links, cycles, max_depth = Inf) {
  edges <- list(); coverage <- list(); expanded <- data.table::copy(roots)
  for (target_cycle in cycles) {
    path <- file.path(directory, paste0("oth", substr(target_cycle, 3, 4)), "transfer-info.json")
    if (!file.exists(path)) {
      coverage[[length(coverage) + 1L]] <- list(cycle = target_cycle, status = "missing_transfer_source")
      next
    }
    index <- jsonlite::fromJSON(path)
    # VERSION 5 preserves ambiguous distinct observations by default. Older
    # indexes and sensitivity-policy results cannot stand in for this view.
    if (is.null(index$version) || index$version != 5L || !identical(index$ambiguous_version_policy, "count_all")) {
      coverage[[length(coverage) + 1L]] <- list(cycle = target_cycle,
        status = "stale_transfer_index", unresolved_all_sources = TRUE)
      next
    }
    raw_path <- file.path(dirname(path), "itoth.txt")
    if (file.exists(raw_path) && (is.null(index$source_sha256) ||
        digest::digest(file = raw_path, algo = "sha256") != index$source_sha256)) {
      coverage[[length(coverage) + 1L]] <- list(cycle = target_cycle,
        status = "stale_transfer_index", unresolved_all_sources = TRUE,
        reason = "Transfer index does not match the current raw OTH source")
      next
    }
    edge_path <- file.path(dirname(path), "transfer-edges.csv")
    if (is.null(index$edges_sha256) ||
        digest::digest(file = edge_path, algo = "sha256") != index$edges_sha256)
      stop("Transfer edge checksum failed: ", edge_path)
    rows <- data.table::fread(edge_path, showProgress = FALSE)
    coverage[[length(coverage) + 1L]] <- list(cycle = target_cycle, status = "indexed",
      source_sha256 = index$source_sha256, counts = index$counts,
      raw_source_available = file.exists(raw_path),
      ledger_path = index$ledger_path, max_depth = if (is.finite(max_depth)) max_depth else NULL,
      traversal = "cycle-safe observed network",
      unresolved_sources = as.list(index$unresolved_sources),
      # Per-source withheld dollars travel beside the source list: the list says
      # WHICH committees hold an unplaceable row, this says HOW MUCH, and only
      # the amount lets the allocator keep that committee's clean edges.
      unresolved_source_amounts = as.list(index$unresolved_source_amounts),
      unresolved_all_sources = isTRUE(index$unresolved_all_sources))
    if (!nrow(rows)) next
    stops <- candidate_links[cycle == target_cycle & designation %in% c("A", "P"), committee_id]
    seed_mask <- if ("traversal_seed" %in% names(roots)) roots$traversal_seed else roots$preliminary_crypto_funding > 0
    visited <- roots$committee_id[roots$cycle == target_cycle & seed_mask]
    frontier <- setdiff(visited, stops)
    depth <- 0L
    while (length(frontier) && depth < max_depth) {
      depth <- depth + 1L
      next_ids <- unique(rows[source %in% frontier & amount > 0, destination])
      next_ids <- setdiff(next_ids, c(visited, stops))
      visited <- unique(c(visited, next_ids)); frontier <- next_ids
      if (!length(frontier)) break
    }
    edges[[length(edges) + 1L]] <- rows[source %in% setdiff(visited, stops)]
    missing <- setdiff(visited, expanded[cycle == target_cycle, committee_id])
    if (length(missing)) expanded <- data.table::rbindlist(list(expanded,
      data.table::data.table(cycle = target_cycle, committee_id = missing,
        committee_name = missing, recipient_category = "", preliminary_crypto_funding = 0)), fill = TRUE)
  }
  list(universe = expanded, edges = data.table::rbindlist(edges, fill = TRUE), coverage = coverage)
}
