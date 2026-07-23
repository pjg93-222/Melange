args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2L || length(args) > 5L) {
  stop(
    paste(
      "usage: Rscript tools/export_crypto_spending_data.R",
      "<mentat.db> <output.json> [fec-committee-master-dir]",
      "[fec-beneficiary-dir] [industry]"
    ),
    call. = FALSE
  )
}

database_path <- normalizePath(args[[1L]], winslash = "/", mustWork = TRUE)
output_path <- normalizePath(args[[2L]], winslash = "/", mustWork = FALSE)
committee_master_dir <- if (length(args) == 3L) {
  normalizePath(args[[3L]], winslash = "/", mustWork = TRUE)
} else {
  ""
}
if (length(args) >= 3L) {
  committee_master_dir <- normalizePath(args[[3L]], winslash = "/", mustWork = TRUE)
}
beneficiary_dir <- if (length(args) >= 4L) {
  normalizePath(args[[4L]], winslash = "/", mustWork = TRUE)
} else {
  ""
}
script_argument <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_path <- normalizePath(
  sub("^--file=", "", script_argument[[1L]]),
  winslash = "/",
  mustWork = TRUE
)
MENTAT_PROJECT_ROOT <- dirname(dirname(script_path))
MENTAT_INDUSTRY <- if (length(args) >= 5L && nzchar(trimws(args[[5L]]))) {
  trimws(args[[5L]])
} else {
  trimws(Sys.getenv("MENTAT_INDUSTRY", unset = "Crypto"))
}
if (!nzchar(MENTAT_INDUSTRY)) {
  stop("Industry cannot be empty.", call. = FALSE)
}

for (module in c(
  "paths.R", "schema.R", "ingest.R", "fec_page.R", "collect.R",
  "fec_api.R", "reconcile.R", "report.R", "fec_beneficiary.R"
)) {
  source(file.path(MENTAT_PROJECT_ROOT, "R", module), local = .GlobalEnv)
}

require_package("data.table")
require_package("DBI")
require_package("RSQLite")
require_package("jsonlite")

supported_cycles <- c(2022L, 2024L, 2026L)

contribution_cycle <- function(values) {
  dates <- normalize_reconcile_date(values)
  years <- as.integer(format(dates, "%Y"))
  years + years %% 2L
}

read_fec_committee_master <- function(directory) {
  if (!nzchar(directory)) {
    return(data.table::data.table(
      cycle = integer(), committee_id = character(), committee_name = character(),
      designation = character(), committee_type = character(),
      party_affiliation = character(), party = character(),
      connected_organization = character(), candidate_id = character(),
      source_url = character()
    ))
  }
  headers <- c(
    "committee_id", "committee_name", "treasurer", "street_1", "street_2",
    "city", "state", "zip", "designation", "committee_type",
    "party_affiliation", "filing_frequency", "organization_type",
    "connected_organization", "candidate_id"
  )
  output <- lapply(supported_cycles, function(cycle) {
    suffix <- substr(as.character(cycle), 3L, 4L)
    path <- file.path(directory, paste0("cm", suffix), "cm.txt")
    if (!file.exists(path)) {
      stop("Missing official FEC committee master: ", path, call. = FALSE)
    }
    master <- data.table::fread(
      path,
      sep = "|",
      header = FALSE,
      fill = TRUE,
      quote = "",
      col.names = headers,
      encoding = "UTF-8",
      showProgress = FALSE
    )
    master[, cycle := cycle]
    master[, source_url := paste0(
      "https://www.fec.gov/files/bulk-downloads/", cycle, "/cm", suffix, ".zip"
    )]
    master[, .(
      cycle,
      committee_id = toupper(trim_text(committee_id)),
      committee_name = trim_text(committee_name),
      designation = toupper(trim_text(designation)),
      committee_type = toupper(trim_text(committee_type)),
      party_affiliation = toupper(trim_text(party_affiliation)),
      connected_organization = trim_text(connected_organization),
      candidate_id = toupper(trim_text(candidate_id)),
      source_url
    )]
  })
  master <- data.table::rbindlist(output, use.names = TRUE, fill = TRUE)
  master[, party := ifelse(
    party_affiliation %in% c("DEM", "DEMOCRATIC", "DFL"),
    "D",
    ifelse(party_affiliation %in% c("REP", "REPUBLICAN", "GOP"), "R", "")
  )]
  master[nzchar(committee_id)]
}

fec_committee_master <- read_fec_committee_master(committee_master_dir)

connection <- DBI::dbConnect(
  RSQLite::SQLite(),
  database_path,
  flags = RSQLite::SQLITE_RO
)
on.exit(DBI::dbDisconnect(connection), add = TRUE)

lookups <- spending_report_lookups(connection)
raw_rows <- spending_raw_report_rows(connection, versioning_applied = TRUE)
analysis_rows <- spending_report_rows(
  connection,
  lookups = lookups,
  raw_rows = raw_rows
)

if (!nrow(raw_rows) || !nrow(analysis_rows)) {
  stop(MENTAT_INDUSTRY, " report source contains no rows.", call. = FALSE)
}

analysis_rows[, analysis_cycle := contribution_cycle(contribution_receipt_date)]
analysis_rows[, committee_master_key := paste(
  as.integer(two_year_transaction_period),
  toupper(trim_text(committee_id)),
  sep = "\r"
)]
fec_committee_master[, committee_master_key := paste(
  cycle,
  committee_id,
  sep = "\r"
)]
master_index <- match(
  analysis_rows$committee_master_key,
  fec_committee_master$committee_master_key
)
analysis_rows[, type_filled_from_master := FALSE]
analysis_rows[, designation_filled_from_master := FALSE]
type_fill <- !is.na(master_index) &
  !nzchar(trim_text(analysis_rows$recipient_committee_type)) &
  nzchar(fec_committee_master$committee_type[master_index])
designation_fill <- !is.na(master_index) &
  !nzchar(trim_text(analysis_rows$recipient_committee_designation)) &
  nzchar(fec_committee_master$designation[master_index])
analysis_rows[type_fill, recipient_committee_type :=
  fec_committee_master$committee_type[master_index[type_fill]]]
analysis_rows[designation_fill, recipient_committee_designation :=
  fec_committee_master$designation[master_index[designation_fill]]]
analysis_rows[type_fill, type_filled_from_master := TRUE]
analysis_rows[designation_fill, designation_filled_from_master := TRUE]

classifications <- spending_recipient_classification(
  connection,
  analysis_rows,
  lookups = lookups
)
master_party <- ifelse(
  is.na(master_index),
  "",
  fec_committee_master$party[master_index]
)
party_fill <- !nzchar(trim_text(classifications$party)) &
  master_party %in% c("D", "R")
classifications$party[party_fill] <- master_party[party_fill]
classifications$party_source[party_fill] <- paste0(
  "fec_committee_master:",
  analysis_rows$two_year_transaction_period[party_fill]
)
master_category_fill <- (
  analysis_rows$type_filled_from_master |
    analysis_rows$designation_filled_from_master
) & grepl("^fec:", classifications$category_source)
classifications$category_source[master_category_fill] <- paste0(
  "fec_committee_master:",
  analysis_rows$two_year_transaction_period[master_category_fill],
  ":committee_type_designation"
)
analysis_rows[, recipient_category := classifications$recipient_category]
analysis_rows[, party := trim_text(classifications$party)]
analysis_rows[, category_source := trim_text(classifications$category_source)]
analysis_rows[, party_source := trim_text(classifications$party_source)]
analysis_rows[!nzchar(party), party := "Other / Unclassified"]

executive_keys <- unique(paste(
  spending_report_company_labels(lookups$executives$company),
  vapply(lookups$executives$executive_name, person_identity_key, character(1L)),
  sep = "\r"
))
verified_employee_names <- if (identical(MENTAT_INDUSTRY, "Crypto")) {
  data.table::data.table(
    company = rep("Coinbase", 5L),
    person = c(
      "POLLAK, JESSE",
      "TUSAR, GREG",
      "GREWAL, PAUL",
      "GUPTA, MANISH",
      "BAUGUESS, SCOTT"
    )
  )
} else {
  data.table::data.table(company = character(), person = character())
}
verified_employee_keys <- unique(paste(
  verified_employee_names$company,
  vapply(verified_employee_names$person, person_identity_key, character(1L)),
  sep = "\r"
))
analysis_rows[, display_company := spending_report_company_labels(company)]
analysis_rows[, canonical_person_key := vapply(
  contributor_name,
  person_identity_key,
  character(1L)
)]
analysis_rows[, known_executive := paste(
  display_company,
  canonical_person_key,
  sep = "\r"
) %in% executive_keys]
analysis_rows[, verified_employee := paste(
  display_company,
  canonical_person_key,
  sep = "\r"
) %in% verified_employee_keys]
analysis_rows[, employee_tier := vapply(seq_len(.N), function(index) {
  spending_contributor_tier(
    contributor_occupation[[index]],
    known_executive[[index]],
    is_entity_contributor[[index]] == 1L
  )
}, character(1L))]
analysis_rows[, included_summary := !recipient_category %in% c("527", "501c")]

person_rows <- analysis_rows[
  is_entity_contributor == 0L,
  .(
    sub_id,
    cycle = as.integer(analysis_cycle),
    company = display_company,
    contributor_name = trim_text(contributor_name),
    exact_name_key = normalize_variant_key(contributor_name),
    base_key = gsub("\034", "|", canonical_person_key, fixed = TRUE),
    city = trim_text(contributor_city),
    state = trim_text(contributor_state),
    zipcode = trim_text(contributor_zip),
    employer = trim_text(contributor_employer),
    employer_key = vapply(contributor_employer, strip_legal_suffix, character(1L)),
    occupation = trim_text(contributor_occupation),
    occupation_key = normalize_occupation(contributor_occupation),
    amount = as.numeric(contribution_receipt_amount),
    party,
    included_summary,
    known_executive,
    verified_employee
  )
]
person_rows[!nzchar(base_key), base_key := exact_name_key]

nonblank_equal <- function(left, right) {
  nzchar(left) && nzchar(right) && identical(left, right)
}

assign_identity_components <- function(group) {
  group <- data.table::copy(group)
  count <- nrow(group)
  parent <- seq_len(count)
  root <- function(index) {
    while (parent[[index]] != index) {
      parent[[index]] <<- parent[[parent[[index]]]]
      index <- parent[[index]]
    }
    index
  }
  unite <- function(left, right) {
    left_root <- root(left)
    right_root <- root(right)
    if (left_root != right_root) parent[[right_root]] <<- left_root
  }

  if (any(group$known_executive) || any(group$verified_employee)) {
    if (count > 1L) for (index in 2L:count) unite(1L, index)
  } else if (count > 1L) {
    for (left in seq_len(count - 1L)) {
      for (right in seq.int(left + 1L, count)) {
        same_exact <- nonblank_equal(
          group$exact_name_key[[left]],
          group$exact_name_key[[right]]
        )
        same_zip <- nonblank_equal(
          substr(group$zipcode[[left]], 1L, 5L),
          substr(group$zipcode[[right]], 1L, 5L)
        )
        same_location <- nonblank_equal(
          paste(group$city[[left]], group$state[[left]], sep = "|"),
          paste(group$city[[right]], group$state[[right]], sep = "|")
        ) && nzchar(group$city[[left]]) && nzchar(group$state[[left]])
        same_occupation <- nonblank_equal(
          group$occupation_key[[left]],
          group$occupation_key[[right]]
        )
        same_employer <- nonblank_equal(
          group$employer_key[[left]],
          group$employer_key[[right]]
        )
        merge_exact <- same_exact && (same_zip || same_location || same_occupation)
        merge_variant <- !same_exact && (
          same_zip || same_location || (same_occupation && same_employer)
        )
        if (merge_exact || merge_variant) unite(left, right)
      }
    }
  }

  roots <- vapply(seq_len(count), root, integer(1L))
  root_order <- unique(roots[order(
    group$exact_name_key,
    group$state,
    group$zipcode,
    group$sub_id
  )])
  component <- match(roots, root_order)
  group[, identity_component := component]
  group
}

identity_groups <- person_rows[, assign_identity_components(.SD), by = .(company, base_key)]
identity_groups[, component_count := data.table::uniqueN(identity_component), by = .(company, base_key)]
identity_groups[, person_key := paste0(
  company, "|", base_key, "|C", sprintf("%02d", identity_component)
)]
identity_groups[, identity_basis := ifelse(
  known_executive,
  "Known executive: canonical name + company",
  ifelse(
    verified_employee,
    "Verified employee identity: canonical name + company + legacy role continuity",
    ifelse(
      component_count > 1L,
      "Conservative split: same-name evidence was insufficient",
      ifelse(
        data.table::uniqueN(state[nzchar(state)]) > 1L,
        "Exact/canonical name + company + shared title/location evidence",
        "Exact/canonical name + company + location evidence"
      )
    )
  )
), by = person_key]

identity_map <- unique(identity_groups[, .(
  sub_id,
  person_key,
  identity_basis
)], by = "sub_id")

person_cycle <- identity_groups[
  included_summary == TRUE & cycle %in% supported_cycles,
  .(
  preliminary_total = sum(amount, na.rm = TRUE),
  contribution_count = .N,
  person = names(sort(table(contributor_name), decreasing = TRUE))[[1L]],
  locations = paste(sort(unique(trim_text(paste0(
    ifelse(nzchar(city), paste0(city, ", "), ""),
    state
  ))))[nzchar(sort(unique(trim_text(paste0(
    ifelse(nzchar(city), paste0(city, ", "), ""),
    state
  )))))], collapse = "; "),
  zipcodes = paste(sort(unique(zipcode[nzchar(zipcode)])), collapse = "; "),
  titles = paste(sort(unique(occupation[nzchar(occupation)])), collapse = "; "),
  identity_basis = identity_basis[[1L]]
), by = .(cycle, company, person_key)]
data.table::setorder(person_cycle, cycle, -preliminary_total, company, person)

analysis_map <- analysis_rows[, .(
  sub_id,
  record_type,
  display_company,
  employee_tier,
  recipient_category,
  party,
  category_source,
  party_source,
  included_summary
)]
analysis_map <- merge(
  analysis_map,
  identity_map,
  by = "sub_id",
  all.x = TRUE,
  sort = FALSE
)

raw_export <- data.table::copy(raw_rows)
raw_export <- merge(
  raw_export,
  analysis_map,
  by = "sub_id",
  all.x = TRUE,
  sort = FALSE,
  suffixes = c("_raw", "")
)
raw_export[, source_cycle := as.integer(two_year_transaction_period)]
raw_export[, cycle := contribution_cycle(contribution_receipt_date)]
raw_export[, cycle_label := sprintf("%d-%d", cycle - 1L, cycle)]
raw_export[, company_display := spending_report_company_labels(company)]
raw_export[, amount := as.numeric(contribution_receipt_amount)]
raw_export[, date := format(
  normalize_reconcile_date(contribution_receipt_date),
  "%Y-%m-%d"
)]
raw_export[, include_in_analysis := ifelse(
  cycle %in% supported_cycles & !is.na(included_summary) & included_summary,
  "Yes",
  "No"
)]
raw_export[, inclusion_reason := ifelse(
  !cycle %in% supported_cycles,
  "Outside requested contribution-date cycles",
  ifelse(
    include_in_analysis == "Yes",
  "Included",
  ifelse(
    !is.na(recipient_category) & recipient_category %in% c("527", "501c"),
    "Excluded recipient class from summaries",
    ifelse(
      duplicate_memo == 1L,
      "Exact five-key memo duplicate",
      ifelse(
        nzchar(trim_text(excluded_reason)),
        trim_text(excluded_reason),
        paste0("Company match: ", trim_text(company_match_status))
      )
    )
  ))
)]
raw_export[, cycle_alignment := ifelse(
  cycle == source_cycle,
  "OK",
  ifelse(
    cycle %in% supported_cycles,
    "Reassigned by contribution date",
    "Outside requested cycles"
  )
)]
raw_export[is.na(party) | !nzchar(party), party := "Other / Unclassified"]
raw_export[is.na(recipient_category), recipient_category := ""]
raw_export[is.na(category_source), category_source := ""]
raw_export[is.na(party_source), party_source := ""]
raw_export[is.na(employee_tier), employee_tier := ""]
raw_export[is.na(person_key), person_key := ""]
raw_export[is.na(identity_basis), identity_basis := ""]

raw_export <- raw_export[, .(
  source_id = sub_id,
  cycle,
  cycle_label,
  source_cycle,
  cycle_alignment,
  company = company_display,
  contributor = trim_text(contributor_name),
  employee_tier,
  amount,
  party,
  recipient_category,
  category_source = trim_text(category_source),
  party_source = trim_text(party_source),
  recipient = trim_text(committee_name),
  committee_id = toupper(trim_text(committee_id)),
  recipient_key = ifelse(
    nzchar(toupper(trim_text(committee_id))),
    paste0("FEC:", toupper(trim_text(committee_id))),
    paste0("NAME:", normalize_variant_key(committee_name))
  ),
  date,
  city = trim_text(contributor_city),
  state = trim_text(contributor_state),
  zipcode = trim_text(contributor_zip),
  employer = trim_text(contributor_employer),
  occupation = trim_text(contributor_occupation),
  record_type = ifelse(is.na(record_type), trim_text(record_type_raw), record_type),
  source_table = trim_text(source_table),
  company_match_status = trim_text(company_match_status),
  include_in_analysis,
  inclusion_reason,
  person_key,
  identity_basis,
  is_memo_leg = as.integer(is_memo_leg),
  is_conduit_leg = as.integer(is_conduit_leg),
  superseded_by_amendment = as.integer(superseded_by_amendment),
  duplicate_filing_version = as.integer(duplicate_filing_version),
  duplicate_memo = as.integer(duplicate_memo)
)]
raw_export[, sort_date := as.integer(as.Date(date))]
data.table::setorder(raw_export, cycle, -sort_date, contributor, source_id)
raw_export[, sort_date := NULL]

if (!nzchar(beneficiary_dir)) {
  stop(
    "FEC beneficiary directory is required for candidate and downstream resolution.",
    call. = FALSE
  )
}

recipient_universe <- raw_export[
  cycle %in% supported_cycles & nzchar(committee_id),
  .(
    committee_name = fec_mode_text(recipient),
    recipient_category = fec_mode_text(recipient_category),
    preliminary_crypto_funding = sum(
      ifelse(include_in_analysis == "Yes", amount, 0),
      na.rm = TRUE
    )
  ),
  by = .(cycle, committee_id)
]
candidate_master <- fec_read_candidate_master(beneficiary_dir, supported_cycles)
candidate_links <- fec_read_candidate_committee_links(
  beneficiary_dir,
  supported_cycles
)
leadership_pacs <- fec_read_leadership_pacs(beneficiary_dir, supported_cycles)
direct_candidate_keys <- unique(paste(
  candidate_links$cycle[candidate_links$designation %in% c("P", "A")],
  candidate_links$committee_id[candidate_links$designation %in% c("P", "A")],
  sep = "|"
))
downstream_universe <- recipient_universe[
  !paste(cycle, committee_id, sep = "|") %in% direct_candidate_keys
]
downstream_activity <- fec_read_downstream_activity(
  beneficiary_dir,
  downstream_universe,
  candidate_master,
  supported_cycles
)
committee_map <- fec_build_committee_map(
  recipient_universe,
  fec_committee_master,
  candidate_master,
  candidate_links,
  leadership_pacs,
  downstream_activity
)
beneficiary_tables <- fec_build_beneficiary_tables(
  raw_export,
  downstream_activity
)
downstream_activity_export <- fec_aggregate_downstream_activity(
  downstream_activity,
  downstream_universe
)

candidate_link_coverage <- sum(nzchar(committee_map$direct_person))
downstream_coverage <- sum(nzchar(committee_map$top_downstream_person))

companies <- sort(unique(spending_report_company_labels(lookups$companies$company)))
cycles <- data.frame(
  cycle = c(2022L, 2024L, 2026L),
  label = c("2021-2022", "2023-2024", "2025-2026"),
  table_name = c("Cycle_2021_2022", "Cycle_2023_2024", "Cycle_2025_2026"),
  stringsAsFactors = FALSE
)

payload <- list(
  metadata = list(
    industry = MENTAT_INDUSTRY,
    database_path = database_path,
    database_bytes = file.info(database_path)$size,
    raw_rows = nrow(raw_export),
    cycle_table_rows = sum(raw_export$cycle %in% supported_cycles),
    cycle_exception_rows = sum(!raw_export$cycle %in% supported_cycles),
    reassigned_by_date_rows = sum(
      raw_export$cycle %in% supported_cycles &
        raw_export$cycle != raw_export$source_cycle
    ),
    included_rows = sum(raw_export$include_in_analysis == "Yes"),
    official_party_rows = sum(grepl(
      "^fec_committee_master:",
      raw_export$party_source
    )),
    employee_groups = nrow(person_cycle),
    identity_review_groups = sum(grepl(
      "^Conservative split",
      person_cycle$identity_basis
    )),
    recipient_committee_cycle_groups = nrow(recipient_universe),
    candidate_linked_committee_cycle_groups = candidate_link_coverage,
    downstream_resolved_committee_cycle_groups = downstream_coverage,
    downstream_organization_committee_cycle_groups = nrow(downstream_universe),
    downstream_rows = nrow(downstream_activity),
    downstream_included_rows = sum(
      downstream_activity$include_in_total == "Yes",
      na.rm = TRUE
    ),
    downstream_superseded_rows = sum(
      downstream_activity$superseded_by_amendment == 1L,
      na.rm = TRUE
    ),
    downstream_memo_rows = sum(
      downstream_activity$memo_code == "X",
      na.rm = TRUE
    ),
    beneficiary_bridge_rows = nrow(beneficiary_tables$bridge),
    beneficiary_summary_rows = nrow(beneficiary_tables$summary),
    downstream_aggregate_rows = nrow(downstream_activity_export),
    generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%OS%z")
  ),
  cycles = cycles,
  companies = companies,
  raw_rows = raw_export[cycle %in% supported_cycles],
  cycle_exceptions = raw_export[!cycle %in% supported_cycles],
  committee_master_sources = unique(fec_committee_master$source_url),
  beneficiary_sources = unique(c(
    candidate_master$source_url,
    candidate_links$source_url,
    leadership_pacs$source_url,
    downstream_activity$source_url
  )),
  employees = person_cycle,
  committee_map = committee_map,
  downstream_activity = downstream_activity_export,
  beneficiary_bridge = beneficiary_tables$bridge,
  beneficiary_summary = beneficiary_tables$summary
)

dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
jsonlite::write_json(
  payload,
  output_path,
  dataframe = "rows",
  auto_unbox = TRUE,
  digits = NA,
  na = "null",
  pretty = FALSE
)
cat(sprintf(
  paste0(
    "%s workbook export: raw=%d included=%d employee_groups=%d ",
    "identity_review_groups=%d downstream=%d beneficiary_summary=%d output=%s\n"
  ),
  MENTAT_INDUSTRY,
  payload$metadata$raw_rows,
  payload$metadata$included_rows,
  payload$metadata$employee_groups,
  payload$metadata$identity_review_groups,
  payload$metadata$downstream_rows,
  payload$metadata$beneficiary_summary_rows,
  output_path
))
