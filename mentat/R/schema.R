mentat_schema_sql <- function() {
  c(
    paste(
      "CREATE TABLE IF NOT EXISTS contributions (",
      "sub_id TEXT PRIMARY KEY,",
      "transaction_id TEXT, original_sub_id TEXT,",
      "contributor_name TEXT, contributor_first_name TEXT,",
      "contributor_last_name TEXT, contributor_suffix TEXT,",
      "contributor_city TEXT, contributor_state TEXT, contributor_zip TEXT,",
      "contributor_employer TEXT, contributor_occupation TEXT,",
      "contributor_aggregate_ytd REAL, contribution_receipt_amount REAL,",
      "contribution_receipt_date TEXT, committee_id TEXT, committee_name TEXT,",
      "recipient_committee_type TEXT, recipient_committee_designation TEXT,",
      "entity_type TEXT, election_type TEXT, fec_election_type_desc TEXT,",
      "receipt_type_full TEXT, memo_code TEXT, memoed_subtotal INTEGER,",
      "memo_text TEXT, conduit_committee_id TEXT, conduit_committee_name TEXT,",
      "amendment_indicator TEXT, report_year INTEGER, report_type TEXT,",
      "file_num INTEGER,",
      "two_year_transaction_period INTEGER, line_number TEXT, pdf_url TEXT,",
      "load_date TEXT, industry TEXT NOT NULL, company TEXT NOT NULL,",
      "matched_variant TEXT NOT NULL, phase TEXT NOT NULL,",
      "match_confidence TEXT, scraped_at TEXT NOT NULL,",
      "is_conduit_leg INTEGER NOT NULL DEFAULT 0 CHECK (is_conduit_leg IN (0,1)),",
      "is_memo_leg INTEGER NOT NULL DEFAULT 0 CHECK (is_memo_leg IN (0,1)),",
      "is_passthrough_leg INTEGER NOT NULL DEFAULT 0 CHECK (is_passthrough_leg IN (0,1)),",
      "memo_review INTEGER NOT NULL DEFAULT 0 CHECK (memo_review IN (0,1)),",
      "possible_amendment INTEGER NOT NULL DEFAULT 0 CHECK (possible_amendment IN (0,1)),",
      "superseded_by_amendment INTEGER NOT NULL DEFAULT 0",
      "CHECK (superseded_by_amendment IN (0,1)),",
      "duplicate_filing_version INTEGER NOT NULL DEFAULT 0",
      "CHECK (duplicate_filing_version IN (0,1)),",
      "duplicate_memo INTEGER NOT NULL DEFAULT 0 CHECK (duplicate_memo IN (0,1)),",
      "is_refund INTEGER NOT NULL DEFAULT 0 CHECK (is_refund IN (0,1)),",
      "is_entity_contributor INTEGER NOT NULL DEFAULT 0",
      "CHECK (is_entity_contributor IN (0,1)),",
      "company_match_status TEXT NOT NULL DEFAULT 'accepted'",
      "CHECK (company_match_status IN ('accepted','review','rejected')),",
      "company_match_reason TEXT,",
      "excluded_reason TEXT",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS scrape_progress (",
      "company TEXT NOT NULL, cycle INTEGER NOT NULL, variant_set TEXT NOT NULL,",
      "last_page INTEGER NOT NULL, records_total INTEGER NOT NULL,",
      "updated_at TEXT NOT NULL,",
      "PRIMARY KEY (company, cycle, variant_set)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS api_work_progress (",
      "unit_id TEXT PRIMARY KEY, company TEXT NOT NULL, cycle INTEGER NOT NULL,",
      "kind TEXT NOT NULL, last_page INTEGER NOT NULL DEFAULT -1,",
      "rows_seen INTEGER NOT NULL DEFAULT 0, records_total INTEGER,",
      "last_index TEXT, last_contribution_receipt_date TEXT,",
      "seen_keysets TEXT, fetched_complete INTEGER NOT NULL DEFAULT 0",
      "CHECK (fetched_complete IN (0,1)),",
      "stored_complete INTEGER NOT NULL DEFAULT 0",
      "CHECK (stored_complete IN (0,1)), updated_at TEXT NOT NULL",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS api_page_checkpoints (",
      "unit_id TEXT NOT NULL, page INTEGER NOT NULL, payload_json TEXT NOT NULL,",
      "PRIMARY KEY (unit_id, page)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS api_request_budget (",
      "budget_id TEXT PRIMARY KEY, window_started_epoch REAL NOT NULL,",
      "requests_used INTEGER NOT NULL DEFAULT 0",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS observed_employers (",
      "cycle INTEGER NOT NULL, employer_string TEXT NOT NULL,",
      "n_rows INTEGER NOT NULL CHECK (n_rows >= 0),",
      "PRIMARY KEY (cycle, employer_string)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS bulk_candidates (",
      "cycle INTEGER NOT NULL, company TEXT NOT NULL, sub_id TEXT NOT NULL,",
      "contributor_name TEXT, contributor_city TEXT, contributor_state TEXT,",
      "contributor_zip TEXT, employer_string TEXT NOT NULL,",
      "contributor_occupation TEXT, committee_id TEXT, amount REAL,",
      "PRIMARY KEY (company, cycle, sub_id)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS companies (",
      "industry TEXT NOT NULL, company TEXT NOT NULL, parent TEXT NOT NULL,",
      "variant TEXT NOT NULL, variant_order INTEGER NOT NULL,",
      "confidence TEXT NOT NULL, exclusions TEXT, metadata_json TEXT,",
      "source_sheet TEXT NOT NULL, source_row INTEGER NOT NULL,",
      "PRIMARY KEY (industry, company, variant)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS company_display_names (",
      "canonical_name TEXT PRIMARY KEY, display_name TEXT NOT NULL,",
      "source TEXT NOT NULL",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS company_match_overrides (",
      "employer_key TEXT NOT NULL, company TEXT NOT NULL,",
      "state TEXT NOT NULL DEFAULT '', occupation_pattern TEXT NOT NULL DEFAULT '',",
      "decision TEXT NOT NULL CHECK (decision IN ('accept','reject')),",
      "PRIMARY KEY (employer_key, company, state, occupation_pattern)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS company_home_states (",
      "company TEXT NOT NULL, state TEXT NOT NULL, source TEXT NOT NULL,",
      "PRIMARY KEY (company, state)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS name_diminutives (",
      "canonical TEXT NOT NULL, variant TEXT NOT NULL,",
      "PRIMARY KEY (canonical, variant)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS categories (",
      "cycle INTEGER NOT NULL, group_name TEXT NOT NULL, category TEXT NOT NULL,",
      "lean TEXT, committee_id TEXT, source_sheet TEXT NOT NULL,",
      "source_marks TEXT, provisional INTEGER NOT NULL DEFAULT 0",
      "CHECK (provisional IN (0,1)),",
      "resolution_status TEXT NOT NULL DEFAULT 'unresolved',",
      "PRIMARY KEY (cycle, group_name, category)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS leadership (",
      "cycle INTEGER NOT NULL, pac_name TEXT NOT NULL, affiliate TEXT, lean TEXT NOT NULL,",
      "provisional INTEGER NOT NULL CHECK (provisional IN (0,1)),",
      "committee_id TEXT, source TEXT NOT NULL,",
      "resolution_status TEXT NOT NULL DEFAULT 'unresolved',",
      "PRIMARY KEY (cycle, pac_name)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS trade (",
      "association_name TEXT PRIMARY KEY, section TEXT NOT NULL,",
      "committee_id TEXT, resolution_status TEXT NOT NULL DEFAULT 'unresolved',",
      "source TEXT NOT NULL",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS executives (",
      "executive_id INTEGER PRIMARY KEY, industry TEXT NOT NULL, company TEXT NOT NULL,",
      "executive_name TEXT, role TEXT NOT NULL, source_industry TEXT NOT NULL,",
      "source_company TEXT NOT NULL, source_executive TEXT, source_row INTEGER NOT NULL,",
      "UNIQUE (source_row)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS industry_assets (",
      "industry TEXT PRIMARY KEY, total_assets_trillion REAL NOT NULL,",
      "source_link TEXT, source_row INTEGER NOT NULL",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS fixture_crypto (",
      "fixture_id INTEGER PRIMARY KEY, contributor_name TEXT NOT NULL,",
      "recipient_name TEXT NOT NULL, receipt_date TEXT NOT NULL, amount REAL NOT NULL,",
      "contributor_state TEXT, city_state_zip TEXT, employer TEXT, occupation TEXT",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS review_queue_identity (",
      "review_id INTEGER PRIMARY KEY, seed_sub_id TEXT, candidate_sub_id TEXT,",
      "company TEXT NOT NULL, cycle INTEGER NOT NULL, seed_name TEXT, candidate_name TEXT,",
      "match_level TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,",
      "UNIQUE (seed_sub_id, candidate_sub_id, company, cycle)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS attribution_conflicts (",
      "sub_id TEXT NOT NULL, stored_company TEXT NOT NULL,",
      "incoming_company TEXT NOT NULL, incoming_phase TEXT NOT NULL,",
      "created_at TEXT NOT NULL,",
      "PRIMARY KEY (sub_id, stored_company, incoming_company, incoming_phase)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS canary_log (",
      "canary_id INTEGER PRIMARY KEY, company TEXT NOT NULL, cycle INTEGER NOT NULL,",
      "variant_set TEXT NOT NULL, page INTEGER NOT NULL, check_name TEXT NOT NULL,",
      "passed INTEGER NOT NULL CHECK (passed IN (0,1)), detail TEXT,",
      "checked_at TEXT NOT NULL",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS run_log (",
      "run_id TEXT NOT NULL, cycle INTEGER NOT NULL, status TEXT NOT NULL,",
      "started_at TEXT NOT NULL, ended_at TEXT, retry_count INTEGER NOT NULL DEFAULT 0,",
      "determinism_result TEXT, decomposition_log TEXT, message TEXT,",
      "PRIMARY KEY (run_id, cycle)",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS corporate_giving (",
      "sub_id TEXT PRIMARY KEY, contributor_name TEXT, contributor_city TEXT,",
      "contributor_state TEXT, contributor_zip TEXT, contributor_employer TEXT,",
      "contributor_occupation TEXT, entity_type TEXT, committee_id TEXT,",
      "is_entity_contributor INTEGER NOT NULL DEFAULT 0",
      "CHECK (is_entity_contributor IN (0,1)),",
      "committee_name TEXT, recipient_committee_type TEXT,",
      "recipient_committee_designation TEXT, contribution_receipt_date TEXT,",
      "contribution_receipt_amount REAL, industry TEXT NOT NULL, company TEXT NOT NULL,",
      "matched_variant TEXT NOT NULL, cycle INTEGER NOT NULL, scraped_at TEXT NOT NULL,",
      "transaction_id TEXT, original_sub_id TEXT, amendment_indicator TEXT,",
      "report_year INTEGER, report_type TEXT, file_num INTEGER, pdf_url TEXT, load_date TEXT,",
      "is_conduit_leg INTEGER NOT NULL DEFAULT 0 CHECK (is_conduit_leg IN (0,1)),",
      "is_memo_leg INTEGER NOT NULL DEFAULT 0 CHECK (is_memo_leg IN (0,1)),",
      "is_passthrough_leg INTEGER NOT NULL DEFAULT 0 CHECK (is_passthrough_leg IN (0,1)),",
      "superseded_by_amendment INTEGER NOT NULL DEFAULT 0",
      "CHECK (superseded_by_amendment IN (0,1)),",
      "duplicate_filing_version INTEGER NOT NULL DEFAULT 0",
      "CHECK (duplicate_filing_version IN (0,1)),",
      "duplicate_memo INTEGER NOT NULL DEFAULT 0 CHECK (duplicate_memo IN (0,1)),",
      "company_match_status TEXT NOT NULL DEFAULT 'review'",
      "CHECK (company_match_status IN ('accepted','review','rejected')),",
      "company_match_reason TEXT, excluded_reason TEXT",
      ")"
    ),
    paste(
      "CREATE TABLE IF NOT EXISTS run_metrics (",
      "run_id TEXT NOT NULL, phase TEXT NOT NULL, started_at TEXT NOT NULL,",
      "ended_at TEXT NOT NULL, wall_clock_seconds REAL NOT NULL,",
      "rows_processed INTEGER NOT NULL DEFAULT 0, request_count INTEGER NOT NULL DEFAULT 0,",
      "rows_per_second REAL NOT NULL DEFAULT 0, detail TEXT,",
      "PRIMARY KEY (run_id, phase)",
      ")"
    ),
    paste(
      "CREATE INDEX IF NOT EXISTS idx_contributions_company_cycle",
      "ON contributions (company, two_year_transaction_period)"
    ),
    paste(
      "CREATE INDEX IF NOT EXISTS idx_contributions_reconcile",
      "ON contributions (contributor_name, contribution_receipt_date, contribution_receipt_amount)"
    ),
    paste(
      "CREATE INDEX IF NOT EXISTS idx_canary_company_cycle",
      "ON canary_log (company, cycle)"
    )
  )
}

init_schema <- function(connection) {
  require_package("DBI")
  DBI::dbWithTransaction(connection, {
    for (statement in mentat_schema_sql()) {
      DBI::dbExecute(connection, statement)
    }
    if (!"memo_review" %in% DBI::dbListFields(connection, "contributions")) {
      DBI::dbExecute(
        connection,
        paste(
          "ALTER TABLE contributions ADD COLUMN memo_review INTEGER",
          "NOT NULL DEFAULT 0 CHECK (memo_review IN (0,1))"
        )
      )
    }
    contribution_fields <- DBI::dbListFields(connection, "contributions")
    if (!"company_match_status" %in% contribution_fields) {
      DBI::dbExecute(
        connection,
        paste(
          "ALTER TABLE contributions ADD COLUMN company_match_status TEXT",
          "NOT NULL DEFAULT 'accepted'",
          "CHECK (company_match_status IN ('accepted','review','rejected'))"
        )
      )
    }
    if (!"company_match_reason" %in% contribution_fields) {
      DBI::dbExecute(
        connection,
        "ALTER TABLE contributions ADD COLUMN company_match_reason TEXT"
      )
    }
    if (!"is_entity_contributor" %in% contribution_fields) {
      DBI::dbExecute(
        connection,
        paste(
          "ALTER TABLE contributions ADD COLUMN is_entity_contributor INTEGER",
          "NOT NULL DEFAULT 0 CHECK (is_entity_contributor IN (0,1))"
        )
      )
    }
    contribution_migrations <- c(
      file_num = "INTEGER",
      superseded_by_amendment = paste(
        "INTEGER NOT NULL DEFAULT 0",
        "CHECK (superseded_by_amendment IN (0,1))"
      ),
      duplicate_filing_version = paste(
        "INTEGER NOT NULL DEFAULT 0",
        "CHECK (duplicate_filing_version IN (0,1))"
      ),
      duplicate_memo = "INTEGER NOT NULL DEFAULT 0 CHECK (duplicate_memo IN (0,1))"
    )
    for (column in setdiff(names(contribution_migrations), contribution_fields)) {
      DBI::dbExecute(
        connection,
        paste(
          "ALTER TABLE contributions ADD COLUMN",
          as.character(DBI::dbQuoteIdentifier(connection, column)),
          contribution_migrations[[column]]
        )
      )
    }
    override_info <- DBI::dbGetQuery(
      connection,
      "PRAGMA table_info(company_match_overrides)"
    )
    override_pk <- override_info$name[override_info$pk > 0L][
      order(override_info$pk[override_info$pk > 0L])
    ]
    desired_override_pk <- c(
      "employer_key", "company", "state", "occupation_pattern"
    )
    if (!identical(override_pk, desired_override_pk)) {
      legacy_overrides <- DBI::dbReadTable(connection, "company_match_overrides")
      if (!"state" %in% names(legacy_overrides)) {
        legacy_overrides$state <- rep("", nrow(legacy_overrides))
      }
      if (!"occupation_pattern" %in% names(legacy_overrides)) {
        legacy_overrides$occupation_pattern <- rep("", nrow(legacy_overrides))
      }
      legacy_overrides <- legacy_overrides[, c(
        "employer_key", "company", "state", "occupation_pattern", "decision"
      ), drop = FALSE]
      DBI::dbExecute(
        connection,
        "ALTER TABLE company_match_overrides RENAME TO _mentat_legacy_match_overrides"
      )
      DBI::dbExecute(
        connection,
        paste(
          "CREATE TABLE company_match_overrides (",
          "employer_key TEXT NOT NULL, company TEXT NOT NULL,",
          "state TEXT NOT NULL DEFAULT '', occupation_pattern TEXT NOT NULL DEFAULT '',",
          "decision TEXT NOT NULL CHECK (decision IN ('accept','reject')),",
          "PRIMARY KEY (employer_key, company, state, occupation_pattern))"
        )
      )
      if (nrow(legacy_overrides)) {
        DBI::dbAppendTable(connection, "company_match_overrides", legacy_overrides)
      }
      DBI::dbExecute(connection, "DROP TABLE _mentat_legacy_match_overrides")
    }
    run_log_fields <- DBI::dbListFields(connection, "run_log")
    if (!"decomposition_log" %in% run_log_fields) {
      DBI::dbExecute(
        connection,
        "ALTER TABLE run_log ADD COLUMN decomposition_log TEXT"
      )
    }
    category_fields <- DBI::dbListFields(connection, "categories")
    if (!"provisional" %in% category_fields) {
      DBI::dbExecute(
        connection,
        paste(
          "ALTER TABLE categories ADD COLUMN provisional INTEGER",
          "NOT NULL DEFAULT 0 CHECK (provisional IN (0,1))"
        )
      )
    }
    corporate_fields <- DBI::dbListFields(connection, "corporate_giving")
    corporate_migrations <- c(
      contributor_city = "TEXT", contributor_state = "TEXT",
      contributor_zip = "TEXT", contributor_employer = "TEXT",
      contributor_occupation = "TEXT", entity_type = "TEXT",
      is_entity_contributor = "INTEGER NOT NULL DEFAULT 0 CHECK (is_entity_contributor IN (0,1))",
      recipient_committee_type = "TEXT", recipient_committee_designation = "TEXT",
      transaction_id = "TEXT", original_sub_id = "TEXT",
      amendment_indicator = "TEXT", report_year = "INTEGER", report_type = "TEXT",
      file_num = "INTEGER", pdf_url = "TEXT", load_date = "TEXT",
      is_conduit_leg = "INTEGER NOT NULL DEFAULT 0 CHECK (is_conduit_leg IN (0,1))",
      is_memo_leg = "INTEGER NOT NULL DEFAULT 0 CHECK (is_memo_leg IN (0,1))",
      is_passthrough_leg = "INTEGER NOT NULL DEFAULT 0 CHECK (is_passthrough_leg IN (0,1))",
      superseded_by_amendment = paste(
        "INTEGER NOT NULL DEFAULT 0",
        "CHECK (superseded_by_amendment IN (0,1))"
      ),
      duplicate_filing_version = paste(
        "INTEGER NOT NULL DEFAULT 0",
        "CHECK (duplicate_filing_version IN (0,1))"
      ),
      duplicate_memo = "INTEGER NOT NULL DEFAULT 0 CHECK (duplicate_memo IN (0,1))",
      company_match_status = paste(
        "TEXT NOT NULL DEFAULT 'review'",
        "CHECK (company_match_status IN ('accepted','review','rejected'))"
      ),
      company_match_reason = "TEXT", excluded_reason = "TEXT"
    )
    for (column in setdiff(names(corporate_migrations), corporate_fields)) {
      DBI::dbExecute(
        connection,
        paste(
          "ALTER TABLE corporate_giving ADD COLUMN",
          as.character(DBI::dbQuoteIdentifier(connection, column)),
          corporate_migrations[[column]]
        )
      )
    }
    if (!"company_match_status" %in% corporate_fields) {
      DBI::dbExecute(
        connection,
        paste(
          "UPDATE corporate_giving SET company_match_status='review',",
          "company_match_reason='migration_requires_revalidation'"
        )
      )
    }
    DBI::dbExecute(
      connection,
      paste(
        "CREATE INDEX IF NOT EXISTS idx_contributions_amendment_version",
        "ON contributions (committee_id, transaction_id, report_year, report_type)"
      )
    )
    DBI::dbExecute(
      connection,
      paste(
        "CREATE INDEX IF NOT EXISTS idx_corporate_amendment_version",
        "ON corporate_giving (committee_id, transaction_id, report_year, report_type)"
      )
    )
    DBI::dbExecute(
      connection,
      paste(
        "CREATE INDEX IF NOT EXISTS idx_contributions_filing_identity",
        "ON contributions (company, committee_id, contribution_receipt_date,",
        "contribution_receipt_amount, contributor_name, contributor_zip)"
      )
    )
    DBI::dbExecute(
      connection,
      paste(
        "CREATE INDEX IF NOT EXISTS idx_corporate_filing_identity",
        "ON corporate_giving (company, committee_id, contribution_receipt_date,",
        "contribution_receipt_amount)"
      )
    )
  })
  invisible(connection)
}

mentat_version_text <- function(x) {
  value <- as.character(x)
  value[is.na(value)] <- ""
  trimws(toupper(value))
}

mentat_sub_id_filing_date <- function(x) {
  value <- gsub("[^0-9]", "", as.character(x), perl = TRUE)
  result <- rep("", length(value))
  eligible <- nchar(value) >= 9L
  if (!any(eligible)) return(result)
  month_day <- substr(value[eligible], 2L, 5L)
  year <- substr(value[eligible], 6L, 9L)
  candidate <- paste0(year, month_day)
  parsed <- suppressWarnings(as.Date(candidate, format = "%Y%m%d"))
  good <- !is.na(parsed)
  result[which(eligible)[good]] <- format(parsed[good], "%Y%m%d")
  result
}

mentat_pdf_filing_id <- function(x) {
  value <- as.character(x)
  value[is.na(value)] <- ""
  result <- sub("^.*[?=/]([0-9]{12,})[^0-9]*$", "\\1", value, perl = TRUE)
  result[result == value & !grepl("^[0-9]{12,}$", value)] <- ""
  result
}

mentat_amendment_version_plan <- function(rows) {
  rows <- as.data.frame(rows, stringsAsFactors = FALSE)
  if (!nrow(rows)) {
    return(data.frame(
      sub_id = character(), version_key = character(),
      superseded_by_amendment = integer(), stringsAsFactors = FALSE
    ))
  }
  column <- function(name, default = "") {
    if (name %in% names(rows)) rows[[name]] else rep(default, nrow(rows))
  }
  sub_id <- mentat_version_text(column("sub_id"))
  committee <- mentat_version_text(column("committee_id"))
  company <- mentat_version_text(column("company"))
  transaction <- mentat_version_text(column("transaction_id"))
  original <- mentat_version_text(column("original_sub_id"))
  report_type <- mentat_version_text(column("report_type"))
  report_year <- mentat_version_text(column("report_year"))
  cycle <- mentat_version_text(column("cycle"))
  report_year[!nzchar(report_year)] <- cycle[!nzchar(report_year)]

  parent_candidates <- which(nzchar(sub_id) & nzchar(original))
  parent_map <- setNames(original[parent_candidates], sub_id[parent_candidates])
  find_root <- function(seed) {
    current <- seed
    seen <- character()
    while (nzchar(current) && current %in% names(parent_map) &&
           !current %in% seen) {
      seen <- c(seen, current)
      next_value <- unname(parent_map[[current]])
      if (!nzchar(next_value)) break
      current <- next_value
    }
    current
  }
  referenced <- sub_id %in% original[nzchar(original)]
  linked_seed <- ifelse(nzchar(original), original, ifelse(referenced, sub_id, ""))
  linked_root <- vapply(linked_seed, function(value) {
    if (nzchar(value)) find_root(value) else ""
  }, character(1L))
  transaction_key <- ifelse(
    nzchar(transaction),
    paste(company, committee, report_year, report_type, transaction, sep = "|"),
    ""
  )
  for (key in unique(transaction_key[nzchar(transaction_key)])) {
    index <- which(transaction_key == key)
    roots <- unique(linked_root[index][nzchar(linked_root[index])])
    if (length(roots) == 1L) linked_root[index] <- roots[[1L]]
  }
  version_key <- ifelse(
    nzchar(linked_root),
    paste("ORIGINAL", company, committee, linked_root, sep = "|"),
    ifelse(
      nzchar(transaction_key),
      paste0("TRANSACTION|", transaction_key),
      paste0("SUB_ID|", sub_id)
    )
  )

  file_num <- suppressWarnings(as.numeric(column("file_num", NA_real_)))
  pdf_id <- mentat_pdf_filing_id(column("pdf_url"))
  load_date <- mentat_version_text(column("load_date"))
  sub_date <- mentat_sub_id_filing_date(sub_id)
  amendment <- mentat_version_text(column("amendment_indicator"))
  amendment_priority <- ifelse(
    amendment == "N" | !nzchar(amendment),
    0L,
    ifelse(amendment == "T", 2L, 1L)
  )
  superseded <- rep(FALSE, nrow(rows))
  latest_value <- function(value) sort(unique(value), method = "radix")[[
    length(unique(value))
  ]]
  for (key in unique(version_key)) {
    index <- which(version_key == key)
    if (length(index) < 2L || startsWith(key, "SUB_ID|")) next
    candidates <- index
    if (all(!is.na(file_num[index]))) {
      candidates <- index[file_num[index] == max(file_num[index])]
      superseded[setdiff(index, candidates)] <- TRUE
    } else if (all(nzchar(pdf_id[index]))) {
      latest <- latest_value(pdf_id[index])
      candidates <- index[pdf_id[index] == latest]
      superseded[setdiff(index, candidates)] <- TRUE
    } else if (all(nzchar(load_date[index]))) {
      latest <- latest_value(load_date[index])
      candidates <- index[load_date[index] == latest]
      superseded[setdiff(index, candidates)] <- TRUE
    } else if (all(nzchar(sub_date[index]))) {
      latest <- latest_value(sub_date[index])
      candidates <- index[sub_date[index] == latest]
      superseded[setdiff(index, candidates)] <- TRUE
    }
    priority <- amendment_priority[candidates]
    if (length(candidates) > 1L && length(unique(priority)) > 1L) {
      keep <- candidates[priority == max(priority)]
      superseded[setdiff(candidates, keep)] <- TRUE
    }
  }
  data.frame(
    sub_id = as.character(column("sub_id")),
    version_key = version_key,
    superseded_by_amendment = as.integer(superseded),
    stringsAsFactors = FALSE
  )
}

mentat_filing_identity_date <- function(x) {
  value <- trimws(as.character(x))
  value[is.na(value)] <- ""
  has_iso_date <- grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}", value)
  value[has_iso_date] <- substr(value[has_iso_date], 1L, 10L)
  toupper(value)
}

mentat_filing_identity_amount <- function(x) {
  value <- suppressWarnings(as.numeric(x))
  ifelse(
    is.na(value),
    "",
    format(round(value, 2L), scientific = FALSE, trim = TRUE, nsmall = 2L)
  )
}

mentat_filing_identity_zip <- function(x) {
  value <- mentat_version_text(x)
  digits <- gsub("[^0-9]", "", value, perl = TRUE)
  has_digits <- nzchar(digits)
  value[has_digits] <- digits[has_digits]
  value
}

mentat_filing_link_components <- function(sub_id, transaction_id, original_sub_id) {
  count <- length(sub_id)
  parent <- seq_len(count)
  find_root <- function(index) {
    while (parent[[index]] != index) {
      parent[[index]] <<- parent[[parent[[index]]]]
      index <- parent[[index]]
    }
    index
  }
  join <- function(left, right) {
    left_root <- find_root(left)
    right_root <- find_root(right)
    if (left_root != right_root) parent[[right_root]] <<- left_root
  }
  transactions <- unique(transaction_id[nzchar(transaction_id)])
  for (transaction in transactions) {
    index <- which(transaction_id == transaction)
    if (length(index) > 1L) {
      for (other in index[-1L]) join(index[[1L]], other)
    }
  }
  for (index in which(nzchar(original_sub_id))) {
    original_index <- which(sub_id == original_sub_id[[index]])
    if (length(original_index)) join(index, original_index[[1L]])
  }
  vapply(seq_len(count), find_root, integer(1L))
}

mentat_filing_version_winner <- function(index, rows) {
  column <- function(name, default = "") {
    if (name %in% names(rows)) rows[[name]] else rep(default, nrow(rows))
  }
  candidates <- index
  file_num <- suppressWarnings(as.numeric(column("file_num", NA_real_)))
  known_file <- candidates[!is.na(file_num[candidates])]
  if (length(known_file)) {
    candidates <- known_file[file_num[known_file] == max(file_num[known_file])]
  }
  amendment <- mentat_version_text(column("amendment_indicator"))
  amendment_priority <- ifelse(
    amendment == "N" | !nzchar(amendment),
    0L,
    ifelse(amendment == "T", 2L, 1L)
  )
  if (length(candidates) > 1L && any(amendment_priority[candidates] > 0L)) {
    candidates <- candidates[
      amendment_priority[candidates] == max(amendment_priority[candidates])
    ]
  }
  load_date <- mentat_version_text(column("load_date"))
  known_load <- candidates[nzchar(load_date[candidates])]
  if (length(known_load)) {
    latest_load <- sort(unique(load_date[known_load]), method = "radix")
    candidates <- known_load[
      load_date[known_load] == latest_load[[length(latest_load)]]
    ]
  }
  sub_id <- mentat_version_text(column("sub_id"))
  candidates[[order(sub_id[candidates], method = "radix", decreasing = TRUE)[[1L]]]]
}

mentat_filing_version_plan <- function(rows, table) {
  table <- match.arg(table, c("contributions", "corporate_giving"))
  rows <- as.data.frame(rows, stringsAsFactors = FALSE)
  if (!nrow(rows)) {
    return(data.frame(
      sub_id = character(), identity_key = character(),
      duplicate_filing_version = integer(), stringsAsFactors = FALSE
    ))
  }
  column <- function(name, default = "") {
    if (name %in% names(rows)) rows[[name]] else rep(default, nrow(rows))
  }
  sub_id <- mentat_version_text(column("sub_id"))
  company <- mentat_version_text(column("company"))
  committee <- mentat_version_text(column("committee_id"))
  receipt_date <- mentat_filing_identity_date(column("contribution_receipt_date"))
  amount <- mentat_filing_identity_amount(column(
    "contribution_receipt_amount",
    NA_real_
  ))
  contributor <- mentat_version_text(column("contributor_name"))
  contributor_zip <- mentat_filing_identity_zip(column("contributor_zip"))
  required <- nzchar(company) & nzchar(committee) & nzchar(receipt_date) &
    nzchar(amount)
  if (identical(table, "contributions")) required <- required & nzchar(contributor)
  identity_value <- if (identical(table, "contributions")) {
    paste(
      company, committee, receipt_date, amount, contributor, contributor_zip,
      sep = "|"
    )
  } else {
    paste(company, committee, receipt_date, amount, sep = "|")
  }
  identity_key <- ifelse(required, identity_value, "")
  excluded_reason <- mentat_version_text(column("excluded_reason"))
  eligible <- !nzchar(excluded_reason) |
    excluded_reason == "DUPLICATE_FILING_VERSION"
  transaction <- mentat_version_text(column("transaction_id"))
  original <- mentat_version_text(column("original_sub_id"))
  duplicate <- rep(FALSE, nrow(rows))
  for (key in unique(identity_key[nzchar(identity_key) & eligible])) {
    index <- which(identity_key == key & eligible)
    if (length(index) < 2L) next
    groups <- if (identical(table, "corporate_giving")) {
      rep(1L, length(index))
    } else {
      mentat_filing_link_components(
        sub_id[index],
        transaction[index],
        original[index]
      )
    }
    for (group in unique(groups)) {
      candidates <- index[groups == group]
      if (length(candidates) < 2L) next
      winner <- mentat_filing_version_winner(candidates, rows)
      duplicate[setdiff(candidates, winner)] <- TRUE
    }
  }
  data.frame(
    sub_id = as.character(column("sub_id")),
    identity_key = identity_key,
    duplicate_filing_version = as.integer(duplicate),
    stringsAsFactors = FALSE
  )
}

mentat_memo_duplicate_plan <- function(rows) {
  rows <- as.data.frame(rows, stringsAsFactors = FALSE)
  if (!nrow(rows)) {
    return(data.frame(
      sub_id = character(), memo_key = character(), duplicate_memo = integer(),
      stringsAsFactors = FALSE
    ))
  }
  column <- function(name, default = "") {
    if (name %in% names(rows)) rows[[name]] else rep(default, nrow(rows))
  }
  company <- mentat_version_text(column("company"))
  committee <- mentat_version_text(column("committee_id"))
  receipt_date <- mentat_filing_identity_date(column("contribution_receipt_date"))
  amount <- mentat_filing_identity_amount(column(
    "contribution_receipt_amount",
    NA_real_
  ))
  contributor <- mentat_version_text(column("contributor_name"))
  required <- nzchar(company) & nzchar(committee) & nzchar(receipt_date) &
    nzchar(amount) & nzchar(contributor)
  memo_key <- ifelse(
    required,
    paste(company, committee, receipt_date, amount, contributor, sep = "|"),
    ""
  )
  is_memo <- suppressWarnings(as.integer(column("is_memo_leg", 0L))) == 1L
  is_memo[is.na(is_memo)] <- FALSE
  non_memo_keys <- unique(memo_key[nzchar(memo_key) & !is_memo])
  duplicate <- is_memo & nzchar(memo_key) & memo_key %in% non_memo_keys
  data.frame(
    sub_id = as.character(column("sub_id")),
    memo_key = memo_key,
    duplicate_memo = as.integer(duplicate),
    stringsAsFactors = FALSE
  )
}

apply_amendment_versioning <- function(connection, print_summary = FALSE) {
  require_package("DBI")
  summaries <- list()
  tables <- intersect(
    c("contributions", "corporate_giving"),
    DBI::dbListTables(connection)
  )
  DBI::dbWithTransaction(connection, {
    global_memo_rows <- do.call(rbind, lapply(tables, function(table) {
      fields <- DBI::dbListFields(connection, table)
      wanted <- intersect(c(
        "sub_id", "company", "committee_id", "contribution_receipt_date",
        "contribution_receipt_amount", "contributor_name", "is_memo_leg"
      ), fields)
      rows <- DBI::dbGetQuery(
        connection,
        paste("SELECT", paste(wanted, collapse = ", "), "FROM", table)
      )
      # rep() not a scalar: assigning a length-1 value to a zero-row frame
      # errors, which an empty corporate_giving table triggers.
      rows$.source_table <- rep(table, nrow(rows))
      rows
    }))
    global_memo_plan <- mentat_memo_duplicate_plan(global_memo_rows)
    global_duplicate_memo_ids <- unique(global_memo_plan$sub_id[
      global_memo_plan$duplicate_memo == 1L
    ])
    for (table in tables) {
      fields <- DBI::dbListFields(connection, table)
      wanted <- intersect(c(
        "sub_id", "company", "committee_id", "transaction_id",
        "original_sub_id", "amendment_indicator", "report_year", "report_type",
        "cycle", "file_num", "pdf_url", "load_date",
        "contributor_name", "committee_name", "contribution_receipt_date",
        "contribution_receipt_amount", "contributor_zip", "is_memo_leg",
        "excluded_reason"
      ), fields)
      quoted_fields <- paste(vapply(
        wanted,
        function(field) as.character(DBI::dbQuoteIdentifier(connection, field)),
        character(1L)
      ), collapse = ", ")
      rows <- DBI::dbGetQuery(
        connection,
        paste("SELECT", quoted_fields, "FROM", table, "ORDER BY sub_id")
      )
      plan <- mentat_amendment_version_plan(rows)
      filing_plan <- mentat_filing_version_plan(rows, table)
      memo_plan <- mentat_memo_duplicate_plan(rows)
      memo_plan$duplicate_memo <- as.integer(
        memo_plan$sub_id %in% global_duplicate_memo_ids
      )
      DBI::dbExecute(
        connection,
        paste0("UPDATE ", table, " SET superseded_by_amendment=0")
      )
      DBI::dbExecute(
        connection,
        paste0(
          "UPDATE ", table, " SET excluded_reason=NULL ",
          "WHERE LOWER(TRIM(excluded_reason))='duplicate_filing_version'"
        )
      )
      DBI::dbExecute(
        connection,
        paste0(
          "UPDATE ", table,
          " SET duplicate_filing_version=0, duplicate_memo=0"
        )
      )
      if (nrow(plan) && any(plan$superseded_by_amendment == 1L)) {
        stage <- paste0("_mentat_amendment_", table)
        DBI::dbExecute(connection, paste("DROP TABLE IF EXISTS temp.", stage))
        DBI::dbExecute(
          connection,
          paste("CREATE TEMP TABLE", stage, "(sub_id TEXT PRIMARY KEY)")
        )
        DBI::dbAppendTable(
          connection,
          stage,
          plan[plan$superseded_by_amendment == 1L, "sub_id", drop = FALSE]
        )
        DBI::dbExecute(
          connection,
          paste0(
            "UPDATE ", table, " SET superseded_by_amendment=1 ",
            "WHERE sub_id IN (SELECT sub_id FROM ", stage, ")"
          )
        )
        DBI::dbExecute(connection, paste("DROP TABLE", stage))
      }
      if (nrow(filing_plan) && any(filing_plan$duplicate_filing_version == 1L)) {
        stage <- paste0("_mentat_filing_", table)
        DBI::dbExecute(connection, paste("DROP TABLE IF EXISTS temp.", stage))
        DBI::dbExecute(
          connection,
          paste("CREATE TEMP TABLE", stage, "(sub_id TEXT PRIMARY KEY)")
        )
        DBI::dbAppendTable(
          connection,
          stage,
          filing_plan[
            filing_plan$duplicate_filing_version == 1L,
            "sub_id",
            drop = FALSE
          ]
        )
        DBI::dbExecute(
          connection,
          paste0(
            "UPDATE ", table,
            " SET duplicate_filing_version=1 ",
            "WHERE sub_id IN (SELECT sub_id FROM ", stage, ")"
          )
        )
        DBI::dbExecute(connection, paste("DROP TABLE", stage))
      }
      if (nrow(memo_plan) && any(memo_plan$duplicate_memo == 1L)) {
        stage <- paste0("_mentat_memo_", table)
        DBI::dbExecute(connection, paste("DROP TABLE IF EXISTS temp.", stage))
        DBI::dbExecute(
          connection,
          paste("CREATE TEMP TABLE", stage, "(sub_id TEXT PRIMARY KEY)")
        )
        DBI::dbAppendTable(
          connection,
          stage,
          memo_plan[memo_plan$duplicate_memo == 1L, "sub_id", drop = FALSE]
        )
        DBI::dbExecute(
          connection,
          paste0(
            "UPDATE ", table, " SET duplicate_memo=1 ",
            "WHERE sub_id IN (SELECT sub_id FROM ", stage, ")"
          )
        )
        DBI::dbExecute(connection, paste("DROP TABLE", stage))
      }
      if (nrow(rows)) {
        amount <- suppressWarnings(as.numeric(rows$contribution_receipt_amount))
        amount[is.na(amount)] <- 0
        company_values <- as.character(rows$company)
        company_values[is.na(company_values)] <- ""
        for (company in sort(unique(company_values), method = "radix")) {
          index <- which(company_values == company)
          superseded <- plan$superseded_by_amendment[index] == 1L
          duplicate <- filing_plan$duplicate_filing_version[index] == 1L
          memo_duplicate <- memo_plan$duplicate_memo[index] == 1L
          excluded_from_analysis <- memo_duplicate
          summaries[[length(summaries) + 1L]] <- data.frame(
            table = table,
            company = company,
            before_rows = length(index),
            current_rows = sum(!excluded_from_analysis),
            rows_superseded = sum(superseded),
            rows_duplicate_filing_versions = sum(duplicate),
            rows_memo_duplicates = sum(memo_duplicate),
            rows_collapsed = sum(excluded_from_analysis),
            before_total = sum(amount[index]),
            current_total = sum(amount[index][!excluded_from_analysis]),
            filing_version_dollar_delta = 0,
            memo_duplicate_dollar_delta = -sum(amount[index][memo_duplicate]),
            dollar_delta = -sum(amount[index][excluded_from_analysis]),
            stringsAsFactors = FALSE
          )
        }
      }
    }
  })
  summary <- if (length(summaries)) {
    do.call(rbind, summaries)
  } else {
    data.frame(
      table = character(), company = character(), before_rows = integer(),
      current_rows = integer(), rows_superseded = integer(),
      rows_duplicate_filing_versions = integer(), rows_memo_duplicates = integer(),
      rows_collapsed = integer(),
      before_total = numeric(), current_total = numeric(),
      filing_version_dollar_delta = numeric(), memo_duplicate_dollar_delta = numeric(),
      dollar_delta = numeric(),
      stringsAsFactors = FALSE
    )
  }
  if (isTRUE(print_summary)) {
    cat("R8 row flags (only exact five-key memo duplicates are excluded from analysis):\n")
    print(summary, row.names = FALSE)
    coinbase <- summary[
      summary$table == "corporate_giving" & summary$company == "Coinbase",
      , drop = FALSE
    ]
    if (nrow(coinbase)) {
      cat(sprintf(
        paste0(
          "Coinbase corporate raw/analysis: $%.2f -> $%.2f ",
          "(%d amendment flags; %d filing-version flags; %d memo duplicates)\n"
        ),
        coinbase$before_total[[1L]], coinbase$current_total[[1L]],
        coinbase$rows_superseded[[1L]],
        coinbase$rows_duplicate_filing_versions[[1L]],
        coinbase$rows_memo_duplicates[[1L]]
      ))
    }
  }
  summary
}

replace_table_atomic <- function(connection, table, data) {
  require_package("DBI")
  if (!DBI::dbExistsTable(connection, table)) {
    stop("Schema table is missing: ", table, call. = FALSE)
  }
  expected <- DBI::dbListFields(connection, table)
  unknown <- setdiff(names(data), expected)
  if (length(unknown)) {
    stop(
      "Unexpected columns for ", table, ": ", paste(unknown, collapse = ", "),
      call. = FALSE
    )
  }
  quoted <- as.character(DBI::dbQuoteIdentifier(connection, table))
  DBI::dbWithTransaction(connection, {
    DBI::dbExecute(connection, paste("DELETE FROM", quoted))
    if (nrow(data)) {
      DBI::dbAppendTable(connection, table, as.data.frame(data))
    }
  })
  invisible(nrow(data))
}
