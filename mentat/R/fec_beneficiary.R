fec_party_bucket <- function(values) {
  value <- toupper(trim_text(values))
  ifelse(
    value %in% c("DEM", "DEMOCRATIC", "DFL", "D"),
    "D",
    ifelse(value %in% c("REP", "REPUBLICAN", "GOP", "R"), "R", "Other / Unclassified")
  )
}

fec_office_label <- function(values) {
  value <- toupper(trim_text(values))
  ifelse(value == "H", "House", ifelse(value == "S", "Senate", ifelse(value == "P", "President", "")))
}

fec_mode_text <- function(values) {
  value <- trim_text(values)
  value <- value[nzchar(value)]
  if (!length(value)) return("")
  first <- value[[1L]]
  if (all(value == first)) return(first)
  ordered <- sort(unique(value))
  counts <- tabulate(match(value, ordered), nbins = length(ordered))
  ordered[[which.max(counts)]]
}

fec_join_unique <- function(values) {
  value <- unique(trim_text(values))
  value <- value[nzchar(value)]
  if (!length(value)) return("")
  if (length(value) == 1L) return(value[[1L]])
  paste(sort(value), collapse = "; ")
}

fec_min_text <- function(values) {
  value <- unique(trim_text(values))
  value <- value[nzchar(value)]
  if (!length(value)) return("")
  if (length(value) == 1L) return(value[[1L]])
  sort(value)[[1L]]
}

fec_max_text <- function(values) {
  value <- unique(trim_text(values))
  value <- value[nzchar(value)]
  if (!length(value)) return("")
  if (length(value) == 1L) return(value[[1L]])
  ordered <- sort(value)
  ordered[[length(ordered)]]
}

fec_grouped_join_unique <- function(rows, key_columns, value_column, output_column) {
  values <- rows[, c(key_columns, value_column), with = FALSE]
  data.table::setnames(values, value_column, ".fec_value")
  values[, .fec_value := trim_text(.fec_value)]
  values <- unique(values[nzchar(.fec_value)])
  if (!nrow(values)) {
    result <- rows[0L, ..key_columns]
    result[, (output_column) := character()]
    return(result[])
  }
  data.table::setorderv(values, c(key_columns, ".fec_value"))
  result <- values[, .(
    .fec_output = if (.N == 1L) .fec_value[[1L]] else paste(.fec_value, collapse = "; ")
  ), by = key_columns]
  data.table::setnames(result, ".fec_output", output_column)
  result[]
}

fec_grouped_text_bounds <- function(rows, key_columns, value_column) {
  values <- rows[, c(key_columns, value_column), with = FALSE]
  data.table::setnames(values, value_column, ".fec_value")
  values[, .fec_value := trim_text(.fec_value)]
  values <- unique(values[nzchar(.fec_value)])
  if (!nrow(values)) {
    result <- rows[0L, ..key_columns]
    result[, `:=`(
      first_activity_date = character(),
      last_activity_date = character()
    )]
    return(result[])
  }
  data.table::setorderv(values, c(key_columns, ".fec_value"))
  first_rows <- values[!duplicated(values, by = key_columns)]
  last_rows <- values[!duplicated(values, by = key_columns, fromLast = TRUE)]
  data.table::setnames(first_rows, ".fec_value", "first_activity_date")
  data.table::setnames(last_rows, ".fec_value", "last_activity_date")
  merge(
    first_rows,
    last_rows,
    by = key_columns,
    all = TRUE,
    sort = FALSE
  )[]
}

fec_grouped_candidate_metadata <- function(rows, key_columns, metadata_columns) {
  metadata <- unique(rows[, c(key_columns, metadata_columns), with = FALSE])
  metadata[, (metadata_columns) := lapply(.SD, trim_text), .SDcols = metadata_columns]
  metadata <- unique(metadata)
  group_sizes <- metadata[, .N, by = key_columns]
  stable_keys <- group_sizes[N == 1L, ..key_columns]
  stable <- metadata[stable_keys, on = key_columns, nomatch = 0L]
  ambiguous_keys <- group_sizes[N > 1L, ..key_columns]
  if (!nrow(ambiguous_keys)) return(stable[])

  ambiguous <- rows[ambiguous_keys, on = key_columns, nomatch = 0L]
  resolved <- ambiguous[, lapply(.SD, fec_mode_text), by = key_columns, .SDcols = metadata_columns]
  data.table::rbindlist(list(stable, resolved), use.names = TRUE)[]
}

fec_aggregate_beneficiary_downstream <- function(downstream_activity) {
  key_columns <- c("cycle", "source_committee_id", "candidate_id")
  metadata_columns <- c(
    "candidate_name", "candidate_party", "office", "office_label",
    "office_state", "district"
  )
  included <- downstream_activity[include_in_total == "Yes", c(
    list(
      cycle = as.integer(cycle),
      source_committee_id = trim_text(committee_id),
      candidate_id = trim_text(candidate_id),
      transaction_amount = as.numeric(transaction_amount),
      activity_type = trim_text(activity_type),
      support_oppose = trim_text(support_oppose),
      transaction_date = trim_text(transaction_date)
    ),
    lapply(.SD, trim_text)
  ), .SDcols = metadata_columns]
  if (!nrow(included)) return(data.table::data.table())

  totals <- included[, .(
    preliminary_downstream_amount = sum(transaction_amount, na.rm = TRUE),
    transaction_count = .N
  ), by = key_columns]
  relationships <- fec_grouped_join_unique(
    included, key_columns, "activity_type", "activity_relationships"
  )
  directions <- fec_grouped_join_unique(
    included, key_columns, "support_oppose", "directions"
  )
  dates <- fec_grouped_text_bounds(
    included, key_columns, "transaction_date"
  )
  metadata <- fec_grouped_candidate_metadata(
    included, key_columns, metadata_columns
  )
  result <- Reduce(
    function(left, right) merge(
      left, right,
      by = key_columns,
      all.x = TRUE,
      sort = FALSE
    ),
    list(totals, relationships, directions, dates, metadata)
  )
  text_columns <- c(
    "activity_relationships", "directions", "first_activity_date",
    "last_activity_date", metadata_columns
  )
  for (column in text_columns) {
    data.table::set(result, which(is.na(result[[column]])), column, "")
  }
  result[]
}

fec_aggregate_beneficiary_summary <- function(bridge) {
  key_columns <- c("cycle", "view", "company", "candidate_id", "candidate_key")
  metadata_columns <- c(
    "candidate_name", "candidate_party", "office", "office_label",
    "office_state", "district"
  )
  totals <- bridge[, .(
    preliminary_downstream_amount = sum(preliminary_downstream_amount, na.rm = TRUE),
    # Keep base-R summation order identical to the legacy mixed aggregation.
    # data.table's GForce sum is faster but can differ in the final floating
    # point bit, which would make formula-cache parity needlessly noisy.
    preliminary_crypto_funding = sum(preliminary_crypto_funding + 0, na.rm = TRUE)
  ), by = key_columns]
  source_rows <- unique(bridge[, c(key_columns, "source_committee_id"), with = FALSE])
  source_counts <- source_rows[, .(source_committee_count = .N), by = key_columns]

  source_labels <- bridge[, c(key_columns, "source_committee", "source_committee_id"), with = FALSE]
  source_labels[, source_committee_label := paste0(
    trim_text(source_committee), " (", trim_text(source_committee_id), ")"
  )]
  source_committees <- fec_grouped_join_unique(
    source_labels, key_columns, "source_committee_label", "source_committees"
  )
  relationships <- fec_grouped_join_unique(
    bridge, key_columns, "activity_relationships", "activity_relationships"
  )
  directions <- fec_grouped_join_unique(
    bridge, key_columns, "directions", "directions"
  )
  metadata <- fec_grouped_candidate_metadata(
    bridge, key_columns, metadata_columns
  )
  result <- Reduce(
    function(left, right) merge(
      left, right,
      by = key_columns,
      all.x = TRUE,
      sort = FALSE
    ),
    list(
      totals, source_counts, source_committees, relationships, directions,
      metadata
    )
  )
  text_columns <- c(
    "source_committees", "activity_relationships", "directions",
    metadata_columns
  )
  for (column in text_columns) {
    data.table::set(result, which(is.na(result[[column]])), column, "")
  }
  result[]
}

fec_read_candidate_master <- function(directory, cycles = c(2022L, 2024L, 2026L)) {
  headers <- c(
    "candidate_id", "candidate_name", "party_affiliation", "election_year",
    "office_state", "office", "district", "incumbent_challenger", "status",
    "principal_committee_id", "street_1", "street_2", "city", "state", "zip"
  )
  output <- lapply(cycles, function(cycle) {
    suffix <- substr(as.character(cycle), 3L, 4L)
    path <- file.path(directory, paste0("cn", suffix), "cn.txt")
    if (!file.exists(path)) stop("Missing official FEC candidate master: ", path, call. = FALSE)
    rows <- data.table::fread(
      path, sep = "|", header = FALSE, fill = TRUE, quote = "",
      col.names = headers, encoding = "UTF-8", showProgress = FALSE
    )
    rows[, .(
      cycle = cycle,
      candidate_id = toupper(trim_text(candidate_id)),
      candidate_name = trim_text(candidate_name),
      candidate_name_key = normalize_variant_key(candidate_name),
      candidate_party = fec_party_bucket(party_affiliation),
      party_affiliation = toupper(trim_text(party_affiliation)),
      office = toupper(trim_text(office)),
      office_label = fec_office_label(office),
      office_state = toupper(trim_text(office_state)),
      district = trim_text(district),
      incumbent_challenger = toupper(trim_text(incumbent_challenger)),
      principal_committee_id = toupper(trim_text(principal_committee_id)),
      source_url = paste0("https://www.fec.gov/files/bulk-downloads/", cycle, "/cn", suffix, ".zip")
    )]
  })
  rows <- data.table::rbindlist(output, use.names = TRUE, fill = TRUE)
  unique(rows[nzchar(candidate_id)], by = c("cycle", "candidate_id"))
}

fec_read_candidate_committee_links <- function(directory, cycles = c(2022L, 2024L, 2026L)) {
  headers <- c(
    "candidate_id", "candidate_election_year", "fec_election_year",
    "committee_id", "committee_type", "designation", "linkage_id"
  )
  labels <- c(
    P = "Principal campaign committee",
    A = "Authorized candidate committee",
    D = "Leadership PAC linked to candidate",
    J = "Joint fundraiser linked to candidate",
    U = "Unauthorized committee linked to candidate"
  )
  output <- lapply(cycles, function(cycle) {
    suffix <- substr(as.character(cycle), 3L, 4L)
    path <- file.path(directory, paste0("ccl", suffix), "ccl.txt")
    if (!file.exists(path)) stop("Missing official FEC candidate-committee linkage: ", path, call. = FALSE)
    rows <- data.table::fread(
      path, sep = "|", header = FALSE, fill = TRUE, quote = "",
      col.names = headers, encoding = "UTF-8", showProgress = FALSE
    )
    rows[, designation := toupper(trim_text(designation))]
    rows[, .(
      cycle = cycle,
      candidate_id = toupper(trim_text(candidate_id)),
      committee_id = toupper(trim_text(committee_id)),
      committee_type = toupper(trim_text(committee_type)),
      designation,
      relationship = ifelse(designation %in% names(labels), unname(labels[designation]), "Candidate-committee linkage"),
      source_url = paste0("https://www.fec.gov/files/bulk-downloads/", cycle, "/ccl", suffix, ".zip")
    )]
  })
  unique(data.table::rbindlist(output, use.names = TRUE, fill = TRUE)[
    nzchar(candidate_id) & nzchar(committee_id)
  ], by = c("cycle", "candidate_id", "committee_id", "designation"))
}

fec_read_leadership_pacs <- function(directory, cycles = c(2022L, 2024L, 2026L)) {
  output <- lapply(cycles, function(cycle) {
    path <- file.path(directory, paste0("leadership", cycle, ".csv"))
    if (!file.exists(path)) stop("Missing official FEC leadership PAC file: ", path, call. = FALSE)
    rows <- data.table::fread(path, encoding = "UTF-8", showProgress = FALSE)
    data.table::setnames(rows, names(rows), tolower(names(rows)))
    rows[, .(
      cycle = cycle,
      committee_id = toupper(trim_text(committee_id)),
      committee_name = trim_text(committee_name),
      sponsor_name = trim_text(sponsor_name),
      sponsor_name_key = normalize_variant_key(sponsor_name),
      source_url = paste0(
        "https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership",
        cycle, ".csv"
      )
    )]
  })
  unique(data.table::rbindlist(output, use.names = TRUE, fill = TRUE)[
    nzchar(committee_id) & nzchar(sponsor_name)
  ], by = c("cycle", "committee_id", "sponsor_name"))
}

fec_downstream_relationship <- function(values) {
  codes <- toupper(trim_text(values))
  labels <- c(
    "24A" = "Independent expenditure - oppose",
    "24C" = "Coordinated party expenditure",
    "24E" = "Independent expenditure - support",
    "24F" = "Communication cost - support",
    "24H" = "Honorarium to candidate",
    "24K" = "Contribution to nonaffiliated committee",
    "24N" = "Communication cost - oppose",
    "24P" = "Contribution to possible federal candidate",
    "24R" = "Election recount disbursement",
    "24Z" = "In-kind contribution to registered filer"
  )
  ifelse(codes %in% names(labels), unname(labels[codes]), paste0("FEC transaction ", codes))
}

fec_downstream_direction <- function(values) {
  codes <- toupper(trim_text(values))
  ifelse(codes %in% c("24A", "24N"), "Oppose", ifelse(codes %in% c("24E", "24F"), "Support", "Contribution / Other"))
}

fec_pas2_cache_file <- function(directory, cycles) {
  paths <- vapply(cycles, function(cycle) {
    suffix <- substr(as.character(cycle), 3L, 4L)
    file.path(directory, paste0("pas2", suffix), "itpas2.txt")
  }, character(1L))
  missing <- paths[!file.exists(paths)]
  if (length(missing)) stop("Missing official FEC committee-to-candidate file: ", missing[[1L]], call. = FALSE)
  signature <- paste(substr(unname(tools::md5sum(paths)), 1L, 10L), collapse = "-")
  cache_directory <- file.path(directory, "cache")
  if (!dir.exists(cache_directory) && !dir.create(cache_directory, recursive = TRUE, showWarnings = FALSE)) {
    stop("Could not create FEC beneficiary cache directory: ", cache_directory, call. = FALSE)
  }
  file.path(cache_directory, paste0("pas2_index_", signature, ".rds"))
}

fec_build_pas2_index <- function(directory, cycles) {
  headers <- c(
    "committee_id", "amendment_indicator", "report_type", "transaction_pgi",
    "image_number", "transaction_type", "entity_type", "recipient_name",
    "city", "state", "zip", "employer", "occupation", "transaction_date",
    "transaction_amount", "other_id", "candidate_id", "transaction_id",
    "file_num", "memo_code", "memo_text", "sub_id"
  )
  output <- lapply(cycles, function(target_cycle) {
    suffix <- substr(as.character(target_cycle), 3L, 4L)
    path <- file.path(directory, paste0("pas2", suffix), "itpas2.txt")
    rows <- data.table::fread(
      path, sep = "|", header = FALSE, fill = TRUE, quote = "",
      col.names = headers, encoding = "UTF-8", showProgress = FALSE
    )
    rows <- rows[, .(
      cycle = target_cycle,
      committee_id = toupper(trim_text(committee_id)),
      candidate_id = toupper(trim_text(candidate_id)),
      amendment_indicator = toupper(trim_text(amendment_indicator)),
      report_type = toupper(trim_text(report_type)),
      transaction_type = toupper(trim_text(transaction_type)),
      recipient_name = trim_text(recipient_name),
      destination_committee_id = toupper(trim_text(other_id)),
      transaction_date_raw = trim_text(transaction_date),
      transaction_amount = suppressWarnings(as.numeric(transaction_amount)),
      transaction_id = trim_text(transaction_id),
      file_num = suppressWarnings(as.numeric(file_num)),
      memo_code = toupper(trim_text(memo_code)),
      memo_text = trim_text(memo_text),
      sub_id = trim_text(sub_id)
    )]
    rows <- rows[nzchar(committee_id) & nzchar(candidate_id)]
    rows[is.na(transaction_amount), transaction_amount := 0]
    rows[, original_order := .I]
    rows[, version_key := ifelse(
      nzchar(transaction_id),
      paste(committee_id, report_type, transaction_id, sep = "|"),
      paste0("SUB|", ifelse(nzchar(sub_id), sub_id, original_order))
    )]
    rows[, amendment_priority := ifelse(
      amendment_indicator == "T", 2L,
      ifelse(amendment_indicator == "A", 1L, 0L)
    )]
    rows[, file_num_sort := ifelse(is.na(file_num), -Inf, file_num)]
    rows[, sub_id_sort := ifelse(nzchar(sub_id), sub_id, sprintf("%020d", original_order))]
    data.table::setorder(
      rows, version_key, -file_num_sort, -amendment_priority, -sub_id_sort,
      na.last = TRUE
    )
    rows[, superseded_by_amendment := as.integer(
      seq_len(.N) > 1L & !startsWith(version_key[[1L]], "SUB|")
    ), by = version_key]
    rows[, exact_duplicate := as.integer(
      nzchar(sub_id) & duplicated(sub_id)
    )]
    rows[, include_in_total := ifelse(
      exact_duplicate == 0L & superseded_by_amendment == 0L & memo_code != "X",
      "Yes", "No"
    )]
    rows[, exclusion_reason := ifelse(
      exact_duplicate == 1L, "Duplicate FEC sub-ID",
      ifelse(superseded_by_amendment == 1L, "Superseded filing amendment",
        ifelse(memo_code == "X", "Memo-only transaction", "Included"))
    )]
    parsed_date <- suppressWarnings(as.Date(rows$transaction_date_raw, format = "%m%d%Y"))
    rows[, transaction_date := ifelse(is.na(parsed_date), "", format(parsed_date, "%Y-%m-%d"))]
    rows[, activity_type := fec_downstream_relationship(transaction_type)]
    rows[, support_oppose := fec_downstream_direction(transaction_type)]
    rows[, source_url := paste0(
      "https://www.fec.gov/files/bulk-downloads/", target_cycle, "/pas2", suffix, ".zip"
    )]
    data.table::setorder(rows, original_order)
    rows[, c(
      "original_order", "version_key", "amendment_priority", "file_num_sort",
      "sub_id_sort", "transaction_date_raw"
    ) := NULL]
    rows
  })
  data.table::rbindlist(output, use.names = TRUE, fill = TRUE)
}

fec_read_pas2_index <- function(directory, cycles) {
  cache_file <- fec_pas2_cache_file(directory, cycles)
  if (file.exists(cache_file)) {
    index <- readRDS(cache_file)
    if (!data.table::is.data.table(index)) data.table::setDT(index)
    return(index)
  }
  index <- fec_build_pas2_index(directory, cycles)
  pending <- paste0(cache_file, ".pending-", Sys.getpid())
  saveRDS(index, pending, compress = "gzip")
  if (!file.rename(pending, cache_file)) {
    if (!file.copy(pending, cache_file, overwrite = FALSE)) {
      stop("Could not publish FEC beneficiary cache: ", cache_file, call. = FALSE)
    }
    unlink(pending)
  }
  index
}

fec_read_downstream_activity <- function(directory, recipient_universe, candidate_master,
                                         cycles = c(2022L, 2024L, 2026L)) {
  relevant_keys <- paste(recipient_universe$cycle, recipient_universe$committee_id, sep = "|")
  index <- fec_read_pas2_index(directory, cycles)
  activity <- index[paste(cycle, committee_id, sep = "|") %in% relevant_keys]
  if (!nrow(activity)) return(activity)
  candidate_columns <- candidate_master[, .(
    cycle, candidate_id, candidate_name, candidate_party, office, office_label,
    office_state, district, candidate_source_url = source_url
  )]
  activity <- merge(
    activity, candidate_columns, by = c("cycle", "candidate_id"),
    all.x = TRUE, sort = FALSE
  )
  activity[is.na(candidate_name) | !nzchar(candidate_name), candidate_name := recipient_name]
  activity[is.na(candidate_party) | !nzchar(candidate_party), candidate_party := "Other / Unclassified"]
  for (column in c("office", "office_label", "office_state", "district", "candidate_source_url")) {
    data.table::set(activity, which(is.na(activity[[column]])), column, "")
  }
  activity
}

fec_build_committee_map <- function(recipient_universe, committee_master, candidate_master,
                                    candidate_links, leadership_pacs, downstream_activity) {
  candidate_columns <- candidate_master[, .(
    cycle, candidate_id, candidate_name, candidate_name_key, candidate_party, office, office_label,
    office_state, district
  )]
  linked <- merge(
    candidate_links[committee_id %in% recipient_universe$committee_id],
    candidate_columns, by = c("cycle", "candidate_id"), all.x = TRUE, sort = FALSE
  )
  linked[, mapping_source := source_url]

  sponsors <- merge(
    leadership_pacs[committee_id %in% recipient_universe$committee_id],
    candidate_columns,
    by.x = c("cycle", "sponsor_name_key"),
    by.y = c("cycle", "candidate_name_key"),
    all.x = TRUE,
    allow.cartesian = TRUE,
    sort = FALSE
  )
  if (nrow(sponsors)) {
    sponsors[, candidate_name := sponsor_name]
    sponsors[, relationship := "Leadership PAC sponsor"]
    sponsors[, mapping_source := source_url]
    sponsors <- sponsors[, .(
      cycle, committee_id, candidate_id, candidate_name, candidate_party,
      office, office_label, office_state, district, relationship, mapping_source
    )]
  }

  mappings <- data.table::rbindlist(list(
    linked[, .(
      cycle, committee_id, candidate_id, candidate_name, candidate_party,
      office, office_label, office_state, district, relationship, mapping_source
    )],
    sponsors
  ), use.names = TRUE, fill = TRUE)
  if (nrow(mappings)) {
    for (column in names(mappings)) data.table::set(mappings, which(is.na(mappings[[column]])), column, "")
    mappings <- unique(mappings, by = c("cycle", "committee_id", "candidate_id", "candidate_name", "relationship"))
  }

  master_fields <- committee_master[, .(
    cycle, committee_id,
    master_committee_name = committee_name,
    connected_organization,
    master_designation = designation,
    master_committee_type = committee_type
  )]
  base <- merge(recipient_universe, master_fields, by = c("cycle", "committee_id"), all.x = TRUE, sort = FALSE)
  for (column in c("master_committee_name", "connected_organization", "master_designation", "master_committee_type")) {
    data.table::set(base, which(is.na(base[[column]])), column, "")
  }
  base[!nzchar(committee_name), committee_name := master_committee_name]

  direct <- if (nrow(mappings)) mappings[, .(
    direct_person = fec_join_unique(candidate_name),
    direct_candidate_ids = fec_join_unique(candidate_id),
    direct_party = fec_join_unique(candidate_party),
    direct_offices = fec_join_unique(paste(
      office_label,
      trim_text(paste(office_state, district, sep = "-"))
    )),
    relationship = fec_join_unique(relationship),
    mapping_source = fec_join_unique(mapping_source)
  ), by = .(cycle, committee_id)] else data.table::data.table(
    cycle = integer(), committee_id = character(), direct_person = character(),
    direct_candidate_ids = character(), direct_party = character(),
    direct_offices = character(), relationship = character(), mapping_source = character()
  )
  result <- merge(base, direct, by = c("cycle", "committee_id"), all.x = TRUE, sort = FALSE)
  for (column in c("direct_person", "direct_candidate_ids", "direct_party", "direct_offices", "relationship", "mapping_source")) {
    data.table::set(result, which(is.na(result[[column]])), column, "")
  }
  result[, ownership_status := ifelse(
    nzchar(direct_person),
    ifelse(grepl("Leadership PAC", relationship, fixed = TRUE), "Candidate/officeholder-sponsored PAC", "Candidate-linked committee"),
    "Organization/committee; no individual ownership link in FEC files"
  )]
  result[!nzchar(relationship), relationship := "No direct candidate/officeholder link"]

  downstream <- downstream_activity[
    include_in_total == "Yes" & office %in% c("H", "S"),
    .(downstream_amount = sum(transaction_amount, na.rm = TRUE)),
    by = .(cycle, committee_id, candidate_id, candidate_name)
  ]
  if (nrow(downstream)) {
    data.table::setorder(downstream, cycle, committee_id, -downstream_amount, candidate_name)
    top <- downstream[, .SD[1L], by = .(cycle, committee_id)]
    data.table::setnames(top, c("candidate_id", "candidate_name", "downstream_amount"), c(
      "top_downstream_candidate_id", "top_downstream_person", "preliminary_top_downstream_amount"
    ))
    result <- merge(result, top, by = c("cycle", "committee_id"), all.x = TRUE, sort = FALSE)
  } else {
    result[, `:=`(
      top_downstream_candidate_id = "",
      top_downstream_person = "",
      preliminary_top_downstream_amount = 0
    )]
  }
  for (column in c("top_downstream_candidate_id", "top_downstream_person")) {
    data.table::set(result, which(is.na(result[[column]])), column, "")
  }
  result[is.na(preliminary_top_downstream_amount), preliminary_top_downstream_amount := 0]
  result[, lookup_key := paste(cycle, committee_id, sep = "|")]
  result
}

fec_aggregate_downstream_activity <- function(downstream_activity, recipient_universe) {
  if (!nrow(downstream_activity)) return(data.table::data.table())
  source_names <- recipient_universe[, .(
    cycle, committee_id,
    source_committee = committee_name,
    source_recipient_category = recipient_category
  )]
  rows <- merge(
    downstream_activity,
    source_names,
    by = c("cycle", "committee_id"),
    all.x = TRUE,
    sort = FALSE
  )
  rows[is.na(source_committee), source_committee := ""]
  rows[is.na(source_recipient_category), source_recipient_category := ""]
  result <- rows[, .(
    reported_amount = sum(transaction_amount, na.rm = TRUE),
    excluded_amount = sum(transaction_amount[include_in_total != "Yes"], na.rm = TRUE),
    preliminary_included_amount = sum(transaction_amount[include_in_total == "Yes"], na.rm = TRUE),
    source_rows = .N,
    included_rows = sum(include_in_total == "Yes"),
    excluded_rows = sum(include_in_total != "Yes"),
    superseded_rows = sum(superseded_by_amendment == 1L),
    memo_rows = sum(memo_code == "X"),
    exact_duplicate_rows = sum(exact_duplicate == 1L),
    first_activity_date = fec_min_text(transaction_date),
    last_activity_date = fec_max_text(transaction_date),
    source_url = fec_mode_text(source_url),
    candidate_source_url = fec_mode_text(candidate_source_url)
  ), by = .(
    cycle,
    source_committee,
    source_committee_id = committee_id,
    source_recipient_category,
    candidate_name,
    candidate_id,
    candidate_party,
    office,
    office_label,
    office_state,
    district,
    activity_type,
    support_oppose,
    transaction_type
  )]
  data.table::setorder(
    result, cycle, source_committee, -preliminary_included_amount,
    candidate_name, activity_type
  )
  result
}

fec_build_beneficiary_tables <- function(raw_export, downstream_activity) {
  downstream <- fec_aggregate_beneficiary_downstream(downstream_activity)
  if (!nrow(downstream)) return(list(bridge = data.table::data.table(), summary = data.table::data.table()))
  funded <- raw_export[
    include_in_analysis == "Yes" & nzchar(committee_id),
    .(
      preliminary_crypto_funding = sum(amount, na.rm = TRUE),
      source_committee = fec_mode_text(recipient)
    ),
    by = .(cycle, company, source_committee_id = committee_id)
  ]
  industry <- funded[, .(
    preliminary_crypto_funding = sum(preliminary_crypto_funding, na.rm = TRUE),
    source_committee = fec_mode_text(source_committee)
  ), by = .(cycle, source_committee_id)]
  industry[, `:=`(view = "Industry", company = "Industry Total")]
  company <- data.table::copy(funded)
  company[, view := "Company"]
  funding <- data.table::rbindlist(list(industry, company), use.names = TRUE, fill = TRUE)
  bridge <- merge(
    funding, downstream,
    by = c("cycle", "source_committee_id"),
    allow.cartesian = TRUE,
    sort = FALSE
  )
  bridge[, candidate_key := ifelse(
    nzchar(candidate_id), paste0("CAND:", candidate_id), paste0("NAME:", normalize_variant_key(candidate_name))
  )]
  bridge[, bridge_key := paste(cycle, view, company, source_committee_id, candidate_key, sep = "|")]
  data.table::setorder(bridge, cycle, view, company, -preliminary_downstream_amount, candidate_name)

  summary <- fec_aggregate_beneficiary_summary(bridge)
  data.table::setorder(summary, cycle, view, company, -preliminary_downstream_amount, candidate_name)
  summary[, preliminary_rank := seq_len(.N), by = .(cycle, view, company)]
  summary <- summary[office %in% c("H", "S") & preliminary_rank <= 100L]
  retained <- unique(summary[, .(cycle, view, company, candidate_key)])
  bridge <- merge(
    bridge,
    retained,
    by = c("cycle", "view", "company", "candidate_key"),
    sort = FALSE
  )
  data.table::setorder(bridge, cycle, view, company, -preliminary_downstream_amount, candidate_name)
  list(bridge = bridge, summary = summary)
}
