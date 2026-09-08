if (!exists("MENTAT_INDUSTRY")) MENTAT_INDUSTRY <- "Crypto"
FEC_API_ENDPOINT <- "https://api.open.fec.gov/v1/schedules/schedule_a/"
FEC_API_PER_PAGE <- 100L
FEC_API_MAX_ATTEMPTS <- 5L
FEC_API_MAX_PAGES_PER_UNIT <- 10000L
FEC_API_RETRY_AFTER_CAP_SECONDS <- 120
FEC_API_HOURLY_REQUEST_CAP <- 1000L
FEC_API_BUDGET_WINDOW_SECONDS <- 3600

fec_api_key <- function(value = Sys.getenv("FEC_API_KEY", unset = "")) {
  key <- trimws(value)
  if (!nzchar(key)) {
    stop(
      paste(
        "FEC_API_KEY is unset. Register for a key at",
        "https://api.data.gov/signup and set the FEC_API_KEY environment variable."
      ),
      call. = FALSE
    )
  }
  key
}

# The persistent request budget is governed PER API KEY, not per database.
# api.data.gov enforces its hourly cap per registered key, so workers holding
# distinct keys are independent even when they share one database and industry.
# Keying the budget row by a derived id is what makes that parallelism real: a
# single hardcoded id collapses every worker onto one shared 1,000/hr bucket,
# which silently caps an N-key fan-out at 1x. The key is never stored - only a
# non-reversible polynomial digest of it.
fec_api_budget_id <- function(
  api_key = Sys.getenv("FEC_API_KEY", unset = ""),
  configured = Sys.getenv("MENTAT_API_BUDGET_ID", unset = "")
) {
  configured <- trimws(configured)
  if (nzchar(configured)) {
    if (!grepl("^openfec:sha256:[0-9a-f]{12,64}$", configured, perl = TRUE)) {
      stop(
        "MENTAT_API_BUDGET_ID must be an openfec:sha256:<hex> identifier.",
        call. = FALSE
      )
    }
    return(configured)
  }
  key <- trimws(api_key)
  if (!nzchar(key)) return("openfec")
  codes <- utf8ToInt(key)
  digest <- 0
  for (code in codes) {
    digest <- (digest * 31 + code) %% 1000003
  }
  paste0("openfec:", format(digest, scientific = FALSE))
}

fec_api_concurrency <- function(
  value = Sys.getenv("MENTAT_CONCURRENCY", unset = "8")
) {
  concurrency <- suppressWarnings(as.integer(trimws(value)))
  if (length(concurrency) != 1L || is.na(concurrency) || concurrency < 1L) {
    stop("MENTAT_CONCURRENCY must be a positive integer.", call. = FALSE)
  }
  concurrency
}

fec_api_budget_exhausted <- function(used, requested, cap) {
  structure(
    list(
      message = paste0(
        "FEC API persistent request budget is exhausted: used=", used,
        ", requested=", requested, ", cap=", cap,
        ". Checkpoints are saved; resume after the budget window resets."
      ),
      call = NULL,
      used = as.integer(used),
      requested = as.integer(requested),
      cap = as.integer(cap)
    ),
    class = c("mentat_api_budget_exhausted", "error", "condition")
  )
}

fec_api_budget_reserve <- function(
  connection,
  requests,
  cap = FEC_API_HOURLY_REQUEST_CAP,
  now = as.numeric(Sys.time()),
  budget_id = fec_api_budget_id()
) {
  requests <- as.integer(requests)
  if (length(requests) != 1L || is.na(requests) || requests < 0L) {
    stop("FEC API budget reservation must be a nonnegative integer.", call. = FALSE)
  }
  # A deferred transaction lets concurrent readers both reach the later write;
  # SQLite cannot safely wait while upgrading both read locks, so one lane gets
  # SQLITE_BUSY immediately despite busy_timeout. BEGIN IMMEDIATE serializes
  # that upgrade before the read. This transaction contains SQLite work only
  # and is committed before the caller performs any API request.
  DBI::dbExecute(connection, "BEGIN IMMEDIATE")
  transaction_open <- TRUE
  on.exit(
    if (transaction_open) try(DBI::dbRollback(connection), silent = TRUE),
    add = TRUE
  )
  row <- DBI::dbGetQuery(
    connection,
    paste(
      "SELECT window_started_epoch, requests_used FROM api_request_budget",
      "WHERE budget_id=?"
    ),
    params = list(budget_id)
  )
  if (!nrow(row) || now - row$window_started_epoch[[1L]] >=
      FEC_API_BUDGET_WINDOW_SECONDS) {
    started <- now
    used <- 0L
  } else {
    started <- as.numeric(row$window_started_epoch[[1L]])
    used <- as.integer(row$requests_used[[1L]])
  }
  if (used + requests > as.integer(cap)) {
    stop(fec_api_budget_exhausted(used, requests, cap))
  }
  used <- used + requests
  DBI::dbExecute(
    connection,
    paste(
      "INSERT INTO api_request_budget",
      "(budget_id, window_started_epoch, requests_used) VALUES (?, ?, ?)",
      "ON CONFLICT(budget_id) DO UPDATE SET",
      "window_started_epoch=excluded.window_started_epoch,",
      "requests_used=excluded.requests_used"
    ),
    params = list(budget_id, started, used)
  )
  status <- list(
    requests_used = used,
    requests_remaining = as.integer(cap) - used,
    window_started_epoch = started
  )
  DBI::dbCommit(connection)
  transaction_open <- FALSE
  status
}

fec_api_budget_status <- function(
  connection,
  cap = FEC_API_HOURLY_REQUEST_CAP,
  now = as.numeric(Sys.time()),
  budget_id = fec_api_budget_id()
) {
  row <- DBI::dbGetQuery(
    connection,
    paste(
      "SELECT window_started_epoch, requests_used FROM api_request_budget",
      "WHERE budget_id=?"
    ),
    params = list(budget_id)
  )
  active <- nrow(row) &&
    now - row$window_started_epoch[[1L]] < FEC_API_BUDGET_WINDOW_SECONDS
  used <- if (active) as.integer(row$requests_used[[1L]]) else 0L
  list(
    requests_used = used,
    requests_remaining = as.integer(cap) - used
  )
}

fec_api_query_pairs <- function(params) {
  pairs <- list()
  for (name in names(params)) {
    values <- params[[name]]
    if (is.null(values) || !length(values)) next
    values <- as.character(values)
    values <- values[!is.na(values) & nzchar(values)]
    for (value in values) {
      pairs[[length(pairs) + 1L]] <- c(name = name, value = value)
    }
  }
  pairs
}

fec_api_encode_query <- function(params) {
  pairs <- fec_api_query_pairs(params)
  if (!length(pairs)) return("")
  paste(vapply(pairs, function(pair) {
    paste0(
      utils::URLencode(pair[["name"]], reserved = TRUE, repeated = TRUE),
      "=",
      utils::URLencode(pair[["value"]], reserved = TRUE, repeated = TRUE)
    )
  }, character(1L)), collapse = "&")
}

fec_api_spec_url <- function(spec) {
  query <- fec_api_encode_query(spec$params)
  if (nzchar(query)) paste0(spec$url, "?", query) else spec$url
}

fec_api_validate_cursor <- function(last_indexes, unit_id = "") {
  cursor_names <- c("last_index", "last_contribution_receipt_date")
  present <- names(last_indexes) %||% character()
  missing <- setdiff(cursor_names, present)
  supported <- intersect(cursor_names, present)
  invalid <- supported[vapply(
    supported,
    function(name) {
      value <- last_indexes[[name]]
      is.null(value) || length(value) != 1L || is.na(value) ||
        !nzchar(trimws(as.character(value)))
    },
    logical(1L)
  )]
  if (length(missing) || length(invalid)) {
    detail <- c(
      if (length(missing)) paste0("missing=", paste(missing, collapse = ",")),
      if (length(invalid)) paste0("null_or_blank=", paste(invalid, collapse = ","))
    )
    stop(
      paste0(
        "FEC API keyset cursor is partial for ", unit_id,
        ": ", paste(detail, collapse = "; ")
      ),
      call. = FALSE
    )
  }
  last_indexes[cursor_names]
}

fec_api_request_spec <- function(unit, last_indexes = NULL) {
  query_values <- unit$variants
  if (identical(unit$query_field, "contributor_employer") &&
      !isTRUE(unit$preserve_query_spelling)) {
    query_values <- unique(normalize_variant_key(query_values))
    query_values <- query_values[nzchar(query_values)]
  }
  if (!length(query_values)) {
    stop("FEC API work unit has no normalized query value: ", unit$id, call. = FALSE)
  }
  per_page <- suppressWarnings(as.integer(
    unit$per_page %||% FEC_API_PER_PAGE
  ))
  if (length(per_page) != 1L || is.na(per_page) ||
      per_page < 1L || per_page > FEC_API_PER_PAGE) {
    stop(
      "FEC API work unit has an invalid per_page value: ",
      unit$id,
      call. = FALSE
    )
  }
  params <- c(
    list(
      per_page = as.character(per_page),
      two_year_transaction_period = as.character(as.integer(unit$cycle)),
      sort = "-contribution_receipt_date"
    ),
    stats::setNames(list(query_values), unit$query_field),
    unit$query_filters %||% list()
  )
  if (!is.null(last_indexes) && length(last_indexes)) {
    cursor <- fec_api_validate_cursor(last_indexes, unit$id)
    params <- c(params, cursor)
  }
  list(id = unit$id, url = FEC_API_ENDPOINT, params = params)
}

fec_api_smaller_page_size <- function(unit) {
  current <- suppressWarnings(as.integer(
    unit$per_page %||% FEC_API_PER_PAGE
  ))
  candidates <- c(50L, 20L, 10L, 5L, 1L)
  smaller <- candidates[candidates < current]
  if (length(smaller)) smaller[[1L]] else NA_integer_
}

fec_api_response_header <- function(response, name) {
  headers <- response$headers %||% list()
  if (!length(headers)) return(NA_character_)
  header_names <- tolower(names(headers) %||% rep("", length(headers)))
  index <- which(header_names == tolower(name))
  if (!length(index)) NA_character_ else as.character(headers[[index[[1L]]]])
}

fec_api_retry_after_seconds <- function(
  response,
  now = Sys.time(),
  cap = FEC_API_RETRY_AFTER_CAP_SECONDS
) {
  value <- trimws(fec_api_response_header(response, "Retry-After"))
  if (is.na(value) || !nzchar(value)) return(NA_real_)
  numeric_value <- suppressWarnings(as.numeric(value))
  if (!is.na(numeric_value)) return(min(as.numeric(cap), max(0, numeric_value)))
  parsed <- as.POSIXct(
    value,
    format = "%a, %d %b %Y %H:%M:%S GMT",
    tz = "GMT"
  )
  if (is.na(parsed)) {
    NA_real_
  } else {
    min(as.numeric(cap), max(0, as.numeric(parsed - now, units = "secs")))
  }
}

fec_api_parse_raw_headers <- function(headers) {
  if (is.null(headers) || !length(headers)) return(list())
  text <- if (is.raw(headers)) rawToChar(headers) else paste(headers, collapse = "
")
  blocks <- strsplit(text, "\r?\n\r?\n", perl = TRUE)[[1L]]
  block <- tail(blocks[nzchar(trimws(blocks))], 1L)
  lines <- strsplit(block, "\r?\n", perl = TRUE)[[1L]]
  lines <- lines[grepl(":", lines, fixed = TRUE)]
  result <- list()
  for (line in lines) {
    split_at <- regexpr(":", line, fixed = TRUE)[[1L]]
    name <- trimws(substr(line, 1L, split_at - 1L))
    value <- trimws(substr(line, split_at + 1L, nchar(line)))
    if (nzchar(name)) result[[name]] <- value
  }
  result
}

fec_api_httr2_transport <- function(specs, api_key, concurrency) {
  requests <- lapply(specs, function(spec) {
    request <- httr2::request(fec_api_spec_url(spec))
    request <- do.call(
      httr2::req_headers,
      c(list(request), stats::setNames(list(api_key), "X-Api-Key"))
    )
    httr2::req_error(request, is_error = function(response) FALSE)
  })
  responses <- httr2::req_perform_parallel(
    requests,
    max_active = min(as.integer(concurrency), length(requests)),
    on_error = "continue"
  )
  lapply(responses, function(response) {
    if (is.null(response) || inherits(response, "condition")) {
      return(list(
        status = 0L,
        headers = list(),
        body = "",
        error = if (inherits(response, "condition")) {
          conditionMessage(response)
        } else {
          "parallel transport failure"
        }
      ))
    }
    list(
      status = httr2::resp_status(response),
      headers = as.list(httr2::resp_headers(response)),
      body = httr2::resp_body_string(response)
    )
  })
}

fec_api_curl_transport <- function(specs, api_key, concurrency) {
  require_package("curl")
  if (!length(specs)) return(list())
  maximum <- min(as.integer(concurrency), length(specs))
  pool <- curl::new_pool(total_con = maximum, host_con = maximum)
  results <- vector("list", length(specs))
  for (index in seq_along(specs)) {
    handle <- curl::new_handle()
    do.call(
      curl::handle_setheaders,
      c(list(handle = handle), stats::setNames(list(api_key), "X-Api-Key"))
    )
    local({
      result_index <- index
      curl::curl_fetch_multi(
        fec_api_spec_url(specs[[result_index]]),
        done = function(response) {
          results[[result_index]] <<- list(
            status = as.integer(response$status_code),
            headers = fec_api_parse_raw_headers(response$headers),
            body = rawToChar(response$content)
          )
        },
        fail = function(message) {
          results[[result_index]] <<- list(
            status = 0L,
            headers = list(),
            body = "",
            error = enc2utf8(as.character(message))
          )
        },
        handle = handle,
        pool = pool
      )
    })
  }
  curl::multi_run(pool = pool)
  if (any(vapply(results, is.null, logical(1L)))) {
    stop("curl completed without a response for one or more FEC API requests.", call. = FALSE)
  }
  results
}

fec_api_default_transport <- function(specs, api_key, concurrency) {
  if (!length(specs)) return(list())
  if (requireNamespace("httr2", quietly = TRUE)) {
    return(fec_api_httr2_transport(specs, api_key, concurrency))
  }
  fec_api_curl_transport(specs, api_key, concurrency)
}

fec_api_query_label <- function(spec) {
  fec_api_spec_url(spec)
}

fec_api_fetch_with_retry <- function(
  specs,
  api_key,
  concurrency = fec_api_concurrency(),
  transport = fec_api_default_transport,
  max_attempts = FEC_API_MAX_ATTEMPTS,
  sleep = Sys.sleep,
  jitter = stats::runif,
  before_request = function(count) invisible(NULL)
) {
  if (!length(specs)) {
    return(list(
      responses = list(), request_count = 0L, retry_count = 0L,
      rate_limit_count = 0L, unservable_queries = integer(),
      instant_504_queries = integer()
    ))
  }
  pending <- seq_along(specs)
  attempts <- integer(length(specs))
  results <- vector("list", length(specs))
  request_count <- 0L
  retry_count <- 0L
  rate_limit_count <- 0L
  unservable <- logical(length(specs))
  saw_504 <- logical(length(specs))
  instant_504 <- logical(length(specs))
  waiting <- integer()
  wait_remaining <- numeric(length(specs))
  while (length(pending) || length(waiting)) {
    if (!length(pending)) {
      delay <- min(wait_remaining[waiting])
      if (delay > 0) sleep(delay)
      wait_remaining[waiting] <- pmax(0, wait_remaining[waiting] - delay)
      pending <- waiting[wait_remaining[waiting] <= 0]
      waiting <- setdiff(waiting, pending)
    }
    before_request(length(pending))
    attempts[pending] <- attempts[pending] + 1L
    batch_started <- proc.time()[["elapsed"]]
    batch <- tryCatch(
      transport(specs[pending], api_key, concurrency),
      error = function(condition) {
        replicate(
          length(pending),
          list(status = 0L, headers = list(), body = ""),
          simplify = FALSE
        )
      }
    )
    batch_elapsed <- proc.time()[["elapsed"]] - batch_started
    if (length(batch) != length(pending)) {
      stop("FEC API transport returned the wrong response count.", call. = FALSE)
    }
    request_count <- request_count + length(batch)
    retry <- integer()
    retry_delays <- numeric()
    for (offset in seq_along(pending)) {
      index <- pending[[offset]]
      response <- batch[[offset]]
      status <- suppressWarnings(as.integer(response$status %||% 0L))
      if (is.null(response$elapsed_seconds)) {
        response$elapsed_seconds <- unname(batch_elapsed)
      }
      is_504 <- identical(status, 504L)
      prior_504 <- saw_504[[index]]
      elapsed_seconds <- suppressWarnings(as.numeric(response$elapsed_seconds))
      if (is_504 && prior_504 && length(elapsed_seconds) == 1L &&
          is.finite(elapsed_seconds) && elapsed_seconds < 2) {
        instant_504[[index]] <- TRUE
      }
      if (is_504) saw_504[[index]] <- TRUE
      retryable <- status == 0L || status == 429L ||
        (status >= 500L && status <= 599L)
      if (status == 429L) rate_limit_count <- rate_limit_count + 1L
      if (identical(status, 200L)) {
        results[[index]] <- response
      } else if (retryable && saw_504[[index]] &&
                 (attempts[[index]] >= min(2L, max_attempts) ||
                  instant_504[[index]])) {
        response$classification <- "unservable_query"
        results[[index]] <- response
        unservable[[index]] <- TRUE
      } else if (retryable && attempts[[index]] < max_attempts) {
        retry_after <- fec_api_retry_after_seconds(response)
        if (is.na(retry_after)) {
          retry_after <- 2^(attempts[[index]] - 1L) + jitter(1L, 0, 1)
        }
        retry <- c(retry, index)
        retry_delays <- c(retry_delays, retry_after)
        retry_count <- retry_count + 1L
      } else {
        status_label <- if (status == 0L) "connection_error" else paste0("HTTP_", status)
        if (status == 429L) {
          stop(structure(
            list(
              message = paste0(
                "FEC API quota remained rate-limited after ", attempts[[index]],
                " attempt(s). Checkpoints are saved; resume after reset."
              ),
              call = NULL
            ),
            class = c("mentat_api_quota_exhausted", "error", "condition")
          ))
        }
        stop(
          paste0(
            "FEC API request failed after ", attempts[[index]],
            " attempt(s): status=", status_label,
            "; query=", fec_api_query_label(specs[[index]]),
            "; API key redacted."
          ),
          call. = FALSE
        )
      }
    }
    if (length(retry)) {
      waiting <- unique(c(waiting, retry))
      wait_remaining[retry] <- retry_delays
    }
    pending <- integer()
  }
  list(
    responses = results,
    request_count = request_count,
    retry_count = retry_count,
    rate_limit_count = rate_limit_count,
    unservable_queries = which(unservable),
    instant_504_queries = which(instant_504 & unservable)
  )
}

fec_api_json <- function(response) {
  if (!is.null(response$json)) return(response$json)
  body <- response$body %||% ""
  if (is.list(body)) return(body)
  if (!nzchar(trimws(body))) {
    stop("FEC API returned an empty success response.", call. = FALSE)
  }
  jsonlite::fromJSON(body, simplifyVector = FALSE)
}

fec_api_rows_as_list <- function(rows) {
  if (is.null(rows)) return(list())
  if (is.data.frame(rows)) {
    return(lapply(seq_len(nrow(rows)), function(index) as.list(rows[index, , drop = FALSE])))
  }
  if (!is.list(rows)) {
    stop("FEC API results must be a list of records.", call. = FALSE)
  }
  rows
}

fec_api_parse_page <- function(response) {
  payload <- fec_api_json(response)
  rows <- fec_api_rows_as_list(payload$results %||% list())
  pagination <- payload$pagination %||% list()
  last_indexes <- pagination$last_indexes %||% list()
  if (!is.list(last_indexes)) {
    stop("FEC API pagination.last_indexes must be an object.", call. = FALSE)
  }
  if (length(last_indexes)) {
    last_indexes <- fec_api_validate_cursor(last_indexes, "API response")
  }
  sub_ids <- vapply(rows, function(row) {
    trim_text(row_scalar(row, "sub_id", ""))
  }, character(1L))
  if (length(sub_ids) && any(!nzchar(sub_ids))) {
    stop("FEC API returned a schedule_a row without sub_id.", call. = FALSE)
  }
  if (length(rows)) rows <- rows[order(sub_ids, method = "radix")]
  count <- suppressWarnings(as.integer(pagination$count %||% NA_integer_))
  list(rows = rows, last_indexes = last_indexes, count = count)
}

fec_api_checkpoint_page <- function(connection, state, page) {
  payload <- jsonlite::toJSON(
    page,
    auto_unbox = TRUE,
    null = "null",
    na = "null",
    digits = NA
  )
  cursor <- state$last_indexes %||% list()
  DBI::dbWithTransaction(connection, {
    if (isTRUE(page$decomposed)) {
      DBI::dbExecute(
        connection,
        "DELETE FROM api_page_checkpoints WHERE unit_id=?",
        params = list(state$unit$id)
      )
    }
    DBI::dbExecute(
      connection,
      paste(
        "INSERT INTO api_page_checkpoints (unit_id, page, payload_json)",
        "VALUES (?, ?, ?) ON CONFLICT(unit_id, page) DO UPDATE SET",
        "payload_json=excluded.payload_json"
      ),
      params = list(state$unit$id, as.integer(page$page_number), payload)
    )
    DBI::dbExecute(
      connection,
      paste(
        "INSERT INTO api_work_progress",
        "(unit_id, company, cycle, kind, last_page, rows_seen, records_total,",
        "last_index, last_contribution_receipt_date, seen_keysets,",
        "fetched_complete, stored_complete, updated_at)",
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
        "ON CONFLICT(unit_id) DO UPDATE SET",
        "last_page=excluded.last_page, rows_seen=excluded.rows_seen,",
        "records_total=excluded.records_total, last_index=excluded.last_index,",
        "last_contribution_receipt_date=excluded.last_contribution_receipt_date,",
        "seen_keysets=excluded.seen_keysets,",
        "fetched_complete=excluded.fetched_complete, updated_at=excluded.updated_at"
      ),
      params = list(
        state$unit$id,
        state$unit$company,
        as.integer(state$unit$cycle),
        state$unit$kind,
        as.integer(page$page_number),
        as.integer(state$rows_seen),
        if (is.na(state$expected_count)) NA_integer_ else as.integer(state$expected_count),
        trim_text(cursor$last_index %||% ""),
        trim_text(cursor$last_contribution_receipt_date %||% ""),
        paste(state$seen_keysets, collapse = "\n"),
        as.integer(state$complete),
        format(Sys.time(), "%Y-%m-%dT%H:%M:%OS3%z")
      )
    )
  })
  invisible(TRUE)
}

fec_api_load_progress <- function(connection, units) {
  if (!length(units)) return(list())
  progress <- DBI::dbGetQuery(
    connection,
    "SELECT * FROM api_work_progress ORDER BY unit_id"
  )
  if (!nrow(progress)) return(list())
  unit_ids <- vapply(units, function(unit) unit$id, character(1L))
  progress <- progress[progress$unit_id %in% unit_ids, , drop = FALSE]
  restored <- list()
  for (index in seq_len(nrow(progress))) {
    row <- progress[index, , drop = FALSE]
    stored <- isTRUE(as.integer(row$stored_complete[[1L]]) == 1L)
    pages <- list()
    if (!stored) {
      payloads <- DBI::dbGetQuery(
        connection,
        paste(
          "SELECT page, payload_json FROM api_page_checkpoints",
          "WHERE unit_id=? ORDER BY page"
        ),
        params = list(row$unit_id[[1L]])
      )
      if (nrow(payloads)) {
        pages <- lapply(payloads$payload_json, function(payload) {
          jsonlite::fromJSON(payload, simplifyVector = FALSE)
        })
      }
    }
    cursor <- list()
    if (nzchar(trim_text(row$last_index[[1L]])) ||
        nzchar(trim_text(row$last_contribution_receipt_date[[1L]]))) {
      cursor <- fec_api_validate_cursor(
        list(
          last_index = row$last_index[[1L]],
          last_contribution_receipt_date = row$last_contribution_receipt_date[[1L]]
        ),
        row$unit_id[[1L]]
      )
    }
    seen <- trim_text(row$seen_keysets[[1L]])
    seen <- if (nzchar(seen)) strsplit(seen, "\n", fixed = TRUE)[[1L]] else character()
    restored[[row$unit_id[[1L]]]] <- list(
      last_indexes = cursor,
      seen_keysets = seen,
      expected_count = suppressWarnings(as.integer(row$records_total[[1L]])),
      page = as.integer(row$last_page[[1L]]) + 1L,
      rows_seen = as.integer(row$rows_seen[[1L]]),
      pages = pages,
      complete = stored || isTRUE(as.integer(row$fetched_complete[[1L]]) == 1L),
      stored_complete = stored
    )
  }
  restored
}

fec_api_mark_work_unit_stored <- function(connection, unit_id) {
  DBI::dbExecute(
    connection,
    paste(
      "UPDATE api_work_progress SET stored_complete=1, updated_at=?",
      "WHERE unit_id=?"
    ),
    params = list(format(Sys.time(), "%Y-%m-%dT%H:%M:%OS3%z"), unit_id)
  )
  DBI::dbExecute(
    connection,
    "DELETE FROM api_page_checkpoints WHERE unit_id=?",
    params = list(unit_id)
  )
  invisible(TRUE)
}

reset_api_progress <- function(connection, tasks) {
  reset <- 0L
  DBI::dbWithTransaction(connection, {
    for (task in tasks) {
      # A fresh API task covers the entire company-cycle. Remove every older
      # browser/API progress row for that cell before repopulating it; otherwise
      # export guards sum historical and current FEC counts and falsely report
      # a complete refresh as short.
      DBI::dbExecute(
        connection,
        "DELETE FROM scrape_progress WHERE company=? AND cycle=?",
        params = list(task$company, as.integer(task$cycle))
      )
      unit_ids <- DBI::dbGetQuery(
        connection,
        paste(
          "SELECT unit_id FROM api_work_progress",
          "WHERE company=? AND cycle=?"
        ),
        params = list(task$company, as.integer(task$cycle))
      )$unit_id
      if (!length(unit_ids)) next
      placeholders <- paste(rep("?", length(unit_ids)), collapse = ",")
      DBI::dbExecute(
        connection,
        paste0(
          "DELETE FROM api_page_checkpoints WHERE unit_id IN (",
          placeholders,
          ")"
        ),
        params = as.list(unit_ids)
      )
      DBI::dbExecute(
        connection,
        paste0(
          "DELETE FROM api_work_progress WHERE unit_id IN (",
          placeholders,
          ")"
        ),
        params = as.list(unit_ids)
      )
      reset <- reset + length(unit_ids)
    }
  })
  as.integer(reset)
}

fec_api_keyset_signature <- function(indexes) {
  if (!length(indexes)) return("")
  names_sorted <- sort(names(indexes), method = "radix")
  paste(vapply(names_sorted, function(name) {
    paste0(name, "=", as.character(indexes[[name]]))
  }, character(1L)), collapse = "&")
}

fec_api_decomposition_queries <- function(unit) {
  values <- unit$decomposition_variants %||% unit$company_variants %||% character()
  values <- trim_text(values)
  values <- values[nzchar(values)]
  if (!length(values)) return(character())
  failed_keys <- unique(normalize_variant_key(unit$variants))
  values <- values[!normalize_variant_key(values) %in% failed_keys]
  if (!length(values)) return(character())
  values <- values[order(toupper(values), values, method = "radix")]
  values[!duplicated(toupper(values))]
}

fec_api_decomposition_units <- function(unit, queries = fec_api_decomposition_queries(unit)) {
  if (!length(queries)) return(list())
  lapply(seq_along(queries), function(index) {
    child <- unit
    child$id <- paste0(unit$id, "::decomposed::", sprintf("%04d", index))
    child$variants <- queries[[index]]
    child$decomposition_variants <- character()
    child$is_decomposition <- TRUE
    child$preserve_query_spelling <- identical(
      unit$decomposition_source %||% "roster",
      "observed_employers"
    )
    child
  })
}

fec_api_state_rows <- function(state) {
  unlist(lapply(state$pages %||% list(), function(page) page$rows), recursive = FALSE)
}

fec_api_union_rows <- function(rows) {
  if (!length(rows)) return(list())
  sub_ids <- vapply(rows, function(row) {
    trim_text(row_scalar(row, "sub_id", ""))
  }, character(1L))
  if (any(!nzchar(sub_ids))) {
    stop("A decomposed FEC API result contained a blank sub_id.", call. = FALSE)
  }
  order_index <- order(sub_ids, method = "radix")
  rows <- rows[order_index]
  sub_ids <- sub_ids[order_index]
  rows[!duplicated(sub_ids)]
}

fec_api_collect_work_units <- function(
  units,
  api_key = fec_api_key(),
  concurrency = fec_api_concurrency(),
  transport = fec_api_default_transport,
  sleep = Sys.sleep,
  jitter = stats::runif,
  initial_states = list(),
  page_callback = NULL,
  before_request = function(count) invisible(NULL)
) {
  if (!length(units)) {
    return(list(
      units = list(), request_count = 0L, retry_count = 0L,
      rate_limit_count = 0L, rows = 0L, rows_total = 0L,
      final_concurrency = as.integer(concurrency), wall_clock_seconds = 0,
      decompositions = list()
    ))
  }
  unit_ids <- vapply(units, function(unit) unit$id, character(1L))
  if (any(!nzchar(unit_ids)) || anyDuplicated(unit_ids)) {
    stop("FEC API work-unit IDs must be non-empty and unique.", call. = FALSE)
  }
  units <- units[order(unit_ids, method = "radix")]
  states <- lapply(units, function(unit) {
    restored <- initial_states[[unit$id]] %||% list()
    restored_pages <- restored$pages %||% list()
    restored_sub_ids <- vapply(
      fec_api_state_rows(list(pages = restored_pages)),
      function(row) trim_text(row_scalar(row, "sub_id", "")),
      character(1L)
    )
    if (
      any(!nzchar(restored_sub_ids)) ||
      anyDuplicated(restored_sub_ids)
    ) {
      stop(
        "Saved FEC API checkpoints contain blank or repeated sub_id(s) for ",
        "work unit: ",
        unit$id,
        call. = FALSE
      )
    }
    list(
      unit = unit,
      last_indexes = restored$last_indexes %||% list(),
      seen_keysets = restored$seen_keysets %||% character(),
      expected_count = restored$expected_count %||% NA_integer_,
      page = restored$page %||% 0L,
      rows_seen = restored$rows_seen %||% 0L,
      rows_collected_run = 0L,
      pages = restored_pages,
      seen_sub_ids = restored_sub_ids,
      complete = isTRUE(restored$complete),
      stored_complete = isTRUE(restored$stored_complete)
    )
  })
  queue <- which(!vapply(states, function(state) state$complete, logical(1L)))
  request_count <- 0L
  retry_count <- 0L
  rate_limit_count <- 0L
  decompositions <- list()
  current_concurrency <- as.integer(concurrency)
  started <- proc.time()[["elapsed"]]
  while (length(queue)) {
    selected <- head(queue, current_concurrency)
    rest <- setdiff(queue, selected)
    specs <- lapply(selected, function(index) {
      fec_api_request_spec(states[[index]]$unit, states[[index]]$last_indexes)
    })
    fetched <- fec_api_fetch_with_retry(
      specs,
      api_key = api_key,
      concurrency = current_concurrency,
      transport = transport,
      sleep = sleep,
      jitter = jitter,
      before_request = before_request
    )
    request_count <- request_count + fetched$request_count
    retry_count <- retry_count + fetched$retry_count
    rate_limit_count <- rate_limit_count + fetched$rate_limit_count
    if (fetched$rate_limit_count > 0L) {
      current_concurrency <- max(1L, current_concurrency %/% 2L)
    } else if (current_concurrency < as.integer(concurrency)) {
      current_concurrency <- current_concurrency + 1L
    }
    unfinished <- integer()
    for (offset in seq_along(selected)) {
      index <- selected[[offset]]
      state <- states[[index]]
      if (offset %in% fetched$unservable_queries) {
        if (isTRUE(state$unit$is_decomposition)) {
          current_page_size <- suppressWarnings(as.integer(
            state$unit$per_page %||% FEC_API_PER_PAGE
          ))
          smaller_page_size <- fec_api_smaller_page_size(state$unit)
          if (!is.na(smaller_page_size)) {
            cat(sprintf(
              paste0(
                "unservable_decomposed_query: %s cycle %d per_page %d",
                " -> retrying from page 1 at per_page %d\n"
              ),
              paste(state$unit$variants, collapse = "|"),
              as.integer(state$unit$cycle),
              current_page_size,
              smaller_page_size
            ))
            state$unit$per_page <- smaller_page_size
            state$last_indexes <- list()
            state$seen_keysets <- character()
            state$expected_count <- NA_integer_
            state$page <- 0L
            state$rows_seen <- 0L
            state$rows_collected_run <- 0L
            state$pages <- list()
            state$seen_sub_ids <- character()
            state$complete <- FALSE
            state$stored_complete <- FALSE
            states[[index]] <- state
            unfinished <- c(unfinished, index)
            next
          }
          stop(
            "Decomposed FEC API query remained unservable; refusing a partial ",
            "parent result: ",
            paste(state$unit$variants, collapse = "|"),
            " cycle ", state$unit$cycle,
            call. = FALSE
          )
        }
        queries <- fec_api_decomposition_queries(state$unit)
        children <- fec_api_decomposition_units(state$unit, queries)
        if (!length(children)) {
          stop(
            "Unservable FEC API query has no decomposition spellings; ",
            "refusing an unverified zero: ",
            paste(state$unit$variants, collapse = "|"),
            " cycle ", state$unit$cycle,
            call. = FALSE
          )
        }
        child_result <- if (length(children)) {
          fec_api_collect_work_units(
            children,
            api_key = api_key,
            concurrency = current_concurrency,
            transport = transport,
            sleep = sleep,
            jitter = jitter,
            initial_states = list(),
            page_callback = NULL,
            before_request = before_request
          )
        } else {
          stop("unreachable: decomposition children were checked above")
        }
        request_count <- request_count + child_result$request_count
        retry_count <- retry_count + child_result$retry_count
        rate_limit_count <- rate_limit_count + child_result$rate_limit_count
        child_names <- sort(names(child_result$units), method = "radix")
        child_rows <- unlist(lapply(child_names, function(name) {
          fec_api_state_rows(child_result$units[[name]])
        }), recursive = FALSE)
        union_rows <- fec_api_union_rows(c(fec_api_state_rows(state), child_rows))
        union_count <- length(union_rows)
        state$last_indexes <- list()
        state$seen_keysets <- character()
        state$expected_count <- as.integer(union_count)
        state$page <- 1L
        state$rows_seen <- as.integer(union_count)
        state$rows_collected_run <- as.integer(union_count)
        state$complete <- TRUE
        state$stored_complete <- FALSE
        state$pages <- list(list(
          rows = union_rows,
          last_indexes = list(),
          count = as.integer(union_count),
          rows_collected = as.integer(union_count),
          page_number = 0L,
          complete = TRUE,
          decomposed = TRUE
        ))
        event <- list(
          unit_id = state$unit$id,
          company = state$unit$company,
          cycle = as.integer(state$unit$cycle),
          term = paste(state$unit$variants, collapse = " | "),
          queries = as.list(queries),
          query_count = length(queries),
          row_count = union_count
        )
        decompositions[[length(decompositions) + 1L]] <- event
        cat(sprintf(
          "unservable_query: %s cycle %d -> decomposed into %d queries, %d rows\n",
          event$term,
          event$cycle,
          event$query_count,
          event$row_count
        ))
        if (is.function(page_callback)) {
          page_callback(state, state$pages[[1L]])
        }
        states[[index]] <- state
        next
      }
      page <- fec_api_parse_page(fetched$responses[[offset]])
      page_sub_ids <- vapply(
        page$rows,
        function(row) trim_text(row_scalar(row, "sub_id", "")),
        character(1L)
      )
      if (any(!nzchar(page_sub_ids))) {
        stop(
          "FEC API page contained a blank sub_id for work unit: ",
          state$unit$id,
          call. = FALSE
        )
      }
      duplicate_sub_ids <- unique(c(
        page_sub_ids[duplicated(page_sub_ids)],
        intersect(page_sub_ids, state$seen_sub_ids)
      ))
      if (length(duplicate_sub_ids)) {
        stop(
          "FEC API pagination repeated sub_id(s) for work unit ",
          state$unit$id, ": ",
          paste(head(duplicate_sub_ids, 5L), collapse = ", "),
          call. = FALSE
        )
      }
      state$seen_sub_ids <- c(state$seen_sub_ids, page_sub_ids)
      state$page <- state$page + 1L
      if (state$page > FEC_API_MAX_PAGES_PER_UNIT) {
        stop(
          "FEC API page ceiling exceeded for work unit: ",
          state$unit$id,
          call. = FALSE
        )
      }
      if (!is.na(page$count)) {
        if (page$count < 0L) {
          stop("FEC API pagination.count cannot be negative.", call. = FALSE)
        }
        if (is.na(state$expected_count)) {
          state$expected_count <- page$count
        } else if (state$expected_count != page$count) {
          # FEC's pagination.count legitimately moves mid-crawl as new filings
          # and amendments post.  On a long crawl (Verizon, State Farm, USAA)
          # this is GUARANTEED.  Aborting the whole run discards every unit
          # already fetched, so warn and adopt the newer count instead.
          warning(
            "FEC API pagination.count moved during work unit (continuing): ",
            state$unit$id, " ", state$expected_count, " -> ", page$count,
            call. = FALSE
          )
          state$expected_count <- page$count
        }
      }
      state$rows_seen <- state$rows_seen + length(page$rows)
      state$rows_collected_run <- state$rows_collected_run + length(page$rows)
      page$rows_collected <- state$rows_seen
      page$page_number <- state$page - 1L
      page_position <- length(state$pages) + 1L
      state$pages[[page_position]] <- page
      observed_counts <- vapply(
        state$pages,
        function(saved_page) suppressWarnings(as.integer(
          saved_page$count %||% NA_integer_
        )),
        integer(1L)
      )
      observed_counts <- observed_counts[
        !is.na(observed_counts) & observed_counts >= 0L
      ]
      counts_moved <- length(unique(observed_counts)) > 1L
      terminal_page <- !length(page$rows) || !length(page$last_indexes)
      count_complete <- if (counts_moved) {
        terminal_page && state$rows_seen %in% unique(observed_counts)
      } else {
        !is.na(state$expected_count) &&
          state$rows_seen == state$expected_count
      }
      if (counts_moved && count_complete) {
        warning(
          "FEC API pagination.count moved after a complete previously ",
          "reported snapshot; accepting ", state$rows_seen,
          " rows for work unit: ", state$unit$id,
          call. = FALSE
        )
        state$expected_count <- as.integer(state$rows_seen)
      }
      if (!count_complete && terminal_page) {
        count_detail <- if (length(unique(observed_counts)) == 1L) {
          paste0(" of ", unique(observed_counts)[[1L]])
        } else {
          paste0(
            " rows; reported counts=",
            paste(unique(observed_counts), collapse = ",")
          )
        }
        stop(
          paste0(
            "FEC API pagination shortfall for ", state$unit$id,
            ": collected ", state$rows_seen, count_detail,
            " rows without a continuation cursor."
          ),
          call. = FALSE
        )
      }
      if (!counts_moved && !is.na(state$expected_count) &&
          state$rows_seen > state$expected_count) {
        stop(
          "FEC API collected more rows than pagination.count for work unit: ",
          state$unit$id,
          call. = FALSE
        )
      }
      has_more <- if (!is.na(state$expected_count)) {
        !count_complete
      } else {
        length(page$rows) > 0L && length(page$last_indexes) > 0L
      }
      if (has_more) {
        signature <- fec_api_keyset_signature(page$last_indexes)
        if (!nzchar(signature)) {
          stop(
            "FEC API omitted pagination.last_indexes before the query was complete.",
            call. = FALSE
          )
        }
        if (signature %in% state$seen_keysets) {
          stop("FEC API cycled to a seen keyset cursor; refusing an infinite loop.", call. = FALSE)
        }
        state$seen_keysets <- c(state$seen_keysets, signature)
        state$last_indexes <- page$last_indexes
        unfinished <- c(unfinished, index)
      } else {
        state$complete <- TRUE
      }
      state$pages[[page_position]]$complete <- state$complete
      if (is.function(page_callback)) {
        page_callback(state, state$pages[[page_position]])
      }
      states[[index]] <- state
    }
    queue <- c(rest, unfinished)
  }
  elapsed <- proc.time()[["elapsed"]] - started
  names(states) <- vapply(states, function(state) state$unit$id, character(1L))
  list(
    units = states,
    request_count = request_count,
    retry_count = retry_count,
    rate_limit_count = rate_limit_count,
    rows = sum(vapply(states, function(state) state$rows_collected_run, integer(1L))),
    rows_total = sum(vapply(states, function(state) state$rows_seen, integer(1L))),
    final_concurrency = current_concurrency,
    wall_clock_seconds = unname(elapsed),
    decompositions = decompositions
  )
}

fec_api_company_rosters <- function(connection) {
  companies <- data.table::as.data.table(DBI::dbGetQuery(
    connection,
    paste(
      "SELECT company, variant, variant_order, exclusions",
      paste0("FROM companies WHERE industry = '", MENTAT_INDUSTRY, "'"),
      "ORDER BY company, variant_order"
    )
  ))
  if (!nrow(companies)) {
    stop("Crypto company register is empty; run Phase 0 ingest first.", call. = FALSE)
  }
  split(companies, companies$company)
}

fec_api_run_lookups <- function(connection) {
  rosters <- fec_api_company_rosters(connection)
  list(
    rosters = rosters,
    match_overrides = company_match_overrides_data(connection),
    home_states = company_home_states_data(connection),
    trusted_by_company = setNames(lapply(names(rosters), function(company) {
      company_cross_reference_people(connection, company)
    }), names(rosters))
  )
}

fec_api_filter_lookups <- function(lookup_cache, company_filter = NULL) {
  if (is.null(company_filter)) return(lookup_cache)
  requested <- unique(trim_text(company_filter))
  requested <- requested[nzchar(requested)]
  if (!length(requested)) {
    stop("FEC API company_filter must contain at least one company.", call. = FALSE)
  }
  available <- names(lookup_cache$rosters)
  unknown <- setdiff(requested, available)
  if (length(unknown)) {
    stop(
      "FEC API company_filter contains unknown company names: ",
      paste(sort(unknown, method = "radix"), collapse = ", "),
      call. = FALSE
    )
  }
  selected <- available[available %in% requested]
  lookup_cache$rosters <- lookup_cache$rosters[selected]
  lookup_cache$trusted_by_company <-
    lookup_cache$trusted_by_company[selected]
  lookup_cache
}

fec_api_roster_exclusions <- function(roster) {
  values <- unique(unlist(strsplit(
    paste(na.omit(roster$exclusions), collapse = "|"),
    "|",
    fixed = TRUE
  )))
  values[nzchar(values)]
}

fec_api_decomposition_spellings <- function(
  connection,
  company,
  cycle,
  roster,
  match_overrides = NULL,
  home_states = NULL
) {
  fallback <- function() {
    list(values = unique(trim_text(roster$variant)), source = "roster")
  }
  if (!DBI::dbExistsTable(connection, "observed_employers")) return(fallback())
  observed <- DBI::dbGetQuery(
    connection,
    paste(
      "SELECT employer_string FROM observed_employers",
      "WHERE cycle=? ORDER BY employer_string"
    ),
    params = list(as.integer(cycle))
  )$employer_string
  observed <- unique(trim_text(observed))
  observed <- observed[nzchar(observed)]
  if (!length(observed)) return(fallback())
  overrides <- match_overrides %||% company_match_overrides_data(connection)
  accepted <- vapply(observed, function(employer) {
    match <- company_employer_match(
      company = company,
      employer = employer,
      contributor_name = "",
      variants = roster$variant,
      trusted_name_keys = character(),
      overrides = overrides,
      excluded_reason = NA_character_,
      home_states = home_states
    )
    identical(match$status, "accepted")
  }, logical(1L))
  values <- observed[accepted]
  if (!length(values)) return(fallback())
  list(values = values, source = "observed_employers")
}

fec_api_employer_units <- function(
  connection,
  cycles,
  rosters = NULL,
  match_overrides = NULL,
  home_states = NULL
) {
  rosters <- rosters %||% fec_api_company_rosters(connection)
  units <- list()
  for (company in sort(names(rosters), method = "radix")) {
    roster <- rosters[[company]]
    partition <- partition_company_variants(roster$variant)
    phases <- list(P1_employer = partition$phase1, P2_variant = partition$phase2)
    for (cycle in sort(as.integer(cycles))) {
      decomposition <- fec_api_decomposition_spellings(
        connection,
        company,
        cycle,
        roster,
        match_overrides = match_overrides,
        home_states = home_states
      )
      for (phase in names(phases)) {
        variants <- phases[[phase]]
        if (!length(variants)) next
        id <- paste(phase, company, cycle, paste(variants, collapse = "||"), sep = ":")
        units[[length(units) + 1L]] <- list(
          id = id,
          kind = "employer",
          industry = MENTAT_INDUSTRY,
          company = company,
          cycle = as.integer(cycle),
          variants = variants,
          company_variants = roster$variant,
          phase = phase,
          query_field = "contributor_employer",
          query_filters = list(),
          exclusions = fec_api_roster_exclusions(roster),
          decomposition_variants = decomposition$values,
          decomposition_source = decomposition$source
        )
      }
    }
  }
  units
}

fec_api_identity_units <- function(connection, cycles, rosters = NULL) {
  rosters <- rosters %||% fec_api_company_rosters(connection)
  seeds <- data.table::as.data.table(DBI::dbGetQuery(
    connection,
    paste(
      "SELECT sub_id, contributor_name, contributor_city, contributor_state,",
      "contributor_zip, contributor_employer, contributor_occupation, company,",
      "two_year_transaction_period AS cycle FROM contributions",
      paste0("WHERE industry='", MENTAT_INDUSTRY, "' AND phase IN ('P1_employer','P2_variant')"),
      "AND company_match_status='accepted'",
      "AND (excluded_reason IS NULL OR excluded_reason='')"
    )
  ))
  seeds <- seeds[cycle %in% as.integer(cycles)]
  seeds <- seeds[company %in% names(rosters)]
  seeds <- seeds[vapply(contributor_name, plausible_person_query, logical(1L))]
  data.table::setorder(seeds, company, cycle, contributor_name, sub_id)
  seeds <- unique(
    seeds,
    by = c("company", "cycle", "contributor_name", "contributor_zip", "contributor_city")
  )
  units <- list()
  for (index in seq_len(nrow(seeds))) {
    seed <- as.list(seeds[index])
    filters <- list()
    zip <- normalize_zip5(seed$contributor_zip)
    city <- toupper(trim_text(seed$contributor_city))
    if (nzchar(zip)) {
      filters$contributor_zip <- zip
    } else if (nzchar(city)) {
      filters$contributor_city <- city
    }
    company <- seed$company
    roster <- rosters[[company]]
    id <- paste("P2_name", company, seed$cycle, seed$sub_id, sep = ":")
    units[[length(units) + 1L]] <- list(
      id = id,
      kind = "identity",
      industry = MENTAT_INDUSTRY,
      company = company,
      cycle = as.integer(seed$cycle),
      variants = seed$contributor_name,
      company_variants = roster$variant,
      phase = "P2_name",
      query_field = "contributor_name",
      query_filters = filters,
      exclusions = fec_api_roster_exclusions(roster),
      seed = seed
    )
  }
  units
}

fec_api_corporate_units <- function(connection, cycles, rosters = NULL) {
  rosters <- rosters %||% fec_api_company_rosters(connection)
  units <- list()
  for (company in sort(names(rosters), method = "radix")) {
    roster <- rosters[[company]]
    queries <- company_contributor_queries(company, roster$variant)
    for (cycle in sort(as.integer(cycles))) {
      for (query in queries) {
        id <- paste("P2_company_name", company, cycle, query, sep = ":")
        units[[length(units) + 1L]] <- list(
          id = id,
          kind = "corporate",
          industry = MENTAT_INDUSTRY,
          company = company,
          cycle = as.integer(cycle),
          variants = query,
          company_variants = roster$variant,
          phase = "P2_company_name",
          query_field = "contributor_name",
          query_filters = list(),
          exclusions = fec_api_roster_exclusions(roster)
        )
      }
    }
  }
  units
}

fec_api_rescue_cap <- function(
  value = Sys.getenv("MENTAT_RESCUE_CAP", unset = "50")
) {
  cap <- suppressWarnings(as.integer(trimws(value)))
  if (length(cap) != 1L || is.na(cap) || cap < 0L) {
    stop("MENTAT_RESCUE_CAP must be a nonnegative integer.", call. = FALSE)
  }
  cap
}

fec_api_rescue_cap_reached <- function(cap) {
  structure(
    list(
      message = paste0("Bulk name-rescue request cap reached: ", cap),
      call = NULL,
      cap = as.integer(cap)
    ),
    class = c("mentat_rescue_cap_reached", "error", "condition")
  )
}

fec_api_bulk_rescue_match <- function(rows, target_sub_id) {
  rows <- fec_api_rows_as_list(rows)
  target <- trim_text(target_sub_id)
  if (!length(rows) || !nzchar(target)) return(list())
  exact <- rows[vapply(rows, function(row) {
    identical(trim_text(row_scalar(row, "sub_id", "")), target)
  }, logical(1L))]
  fec_api_union_rows(exact)
}

fec_api_execute_rescue_plan <- function(
  candidates,
  cap = fec_api_rescue_cap(),
  api_key,
  concurrency = 1L,
  transport = fec_api_default_transport,
  sleep = Sys.sleep,
  jitter = stats::runif,
  before_request = function(count) invisible(NULL),
  on_exact = function(candidate, rows, page) invisible(TRUE),
  on_complete = function(candidate, pages, exact_rows) invisible(TRUE)
) {
  candidates <- as.data.frame(candidates, stringsAsFactors = FALSE)
  required <- c("company", "cycle", "sub_id", "contributor_name", "contributor_zip")
  missing <- setdiff(required, names(candidates))
  if (length(missing)) {
    stop(
      "Bulk rescue candidates are missing columns: ", paste(missing, collapse = ", "),
      call. = FALSE
    )
  }
  started <- proc.time()[["elapsed"]]
  requests <- 0L
  retries <- 0L
  rate_limits <- 0L
  raw_rows <- 0L
  rescued_ids <- character()
  overflow_index <- integer()
  if (!nrow(candidates)) {
    return(list(
      rows = 0L, request_count = 0L, retry_count = 0L,
      rate_limit_count = 0L, rescued_sub_ids = character(),
      overflow = candidates, wall_clock_seconds = 0, queries_walked = 0L,
      raw_rows = 0L
    ))
  }
  reserve <- function(count) {
    count <- as.integer(count)
    if (requests + count > as.integer(cap)) {
      stop(fec_api_rescue_cap_reached(cap))
    }
    before_request(count)
    requests <<- requests + count
    invisible(NULL)
  }
  queries_walked <- 0L
  for (index in seq_len(nrow(candidates))) {
    if (requests >= as.integer(cap)) {
      overflow_index <- seq.int(index, nrow(candidates))
      break
    }
    candidate <- as.list(candidates[index, , drop = FALSE])
    name <- trim_text(candidate$contributor_name)
    if (!nzchar(name)) next
    zip <- normalize_zip5(candidate$contributor_zip)
    filters <- if (nzchar(zip)) list(contributor_zip = zip) else list()
    unit <- list(
      id = paste(
        "P3_bulk_rescue", candidate$company, candidate$cycle,
        candidate$sub_id, sep = ":"
      ),
      company = trim_text(candidate$company),
      cycle = as.integer(candidate$cycle),
      variants = name,
      query_field = "contributor_name",
      query_filters = filters
    )
    queries_walked <- queries_walked + 1L
    cursor <- list()
    rows_seen <- 0L
    expected_count <- NA_integer_
    seen_keysets <- character()
    cap_hit <- FALSE
    candidate_pages <- list()
    exact_rows <- list()
    repeat {
      fetched <- tryCatch(
        fec_api_fetch_with_retry(
          list(fec_api_request_spec(unit, cursor)),
          api_key = api_key,
          concurrency = min(1L, as.integer(concurrency)),
          transport = transport,
          sleep = sleep,
          jitter = jitter,
          before_request = reserve
        ),
        mentat_rescue_cap_reached = function(condition) condition
      )
      if (inherits(fetched, "mentat_rescue_cap_reached")) {
        overflow_index <- seq.int(index, nrow(candidates))
        cap_hit <- TRUE
        break
      }
      retries <- retries + fetched$retry_count
      rate_limits <- rate_limits + fetched$rate_limit_count
      if (length(fetched$unservable_queries)) break
      page <- fec_api_parse_page(fetched$responses[[1L]])
      if (!is.na(page$count)) {
        if (is.na(expected_count)) {
          expected_count <- page$count
        } else if (!identical(expected_count, page$count)) {
          warning(
            "FEC API pagination.count moved during bulk rescue (continuing) for ",
            candidate$sub_id,
            call. = FALSE
          )
          expected_count <- page$count
        }
      }
      rows_seen <- rows_seen + length(page$rows)
      raw_rows <- raw_rows + length(page$rows)
      candidate_pages[[length(candidate_pages) + 1L]] <- page
      exact <- fec_api_bulk_rescue_match(page$rows, candidate$sub_id)
      if (length(exact)) {
        on_exact(candidate, exact, page)
        exact_rows <- exact
        rescued_ids <- c(rescued_ids, trim_text(candidate$sub_id))
        break
      }
      count_complete <- !is.na(expected_count) && rows_seen >= expected_count
      if (!is.na(expected_count) && rows_seen < expected_count &&
          (!length(page$rows) || !length(page$last_indexes))) {
        stop(
          "FEC API pagination shortfall during bulk rescue for ",
          candidate$sub_id,
          call. = FALSE
        )
      }
      if (count_complete || !length(page$rows) || !length(page$last_indexes)) break
      signature <- fec_api_keyset_signature(page$last_indexes)
      if (!nzchar(signature) || signature %in% seen_keysets) {
        stop(
          "FEC API bulk-rescue pagination returned an invalid or repeated cursor.",
          call. = FALSE
        )
      }
      seen_keysets <- c(seen_keysets, signature)
      cursor <- page$last_indexes
    }
    if (length(candidate_pages)) {
      on_complete(candidate, candidate_pages, exact_rows)
    }
    if (cap_hit) break
  }
  overflow <- if (length(overflow_index)) {
    candidates[overflow_index, , drop = FALSE]
  } else {
    candidates[FALSE, , drop = FALSE]
  }
  if (nrow(overflow)) overflow$overflow_reason <- "rescue_request_cap"
  list(
    rows = length(unique(rescued_ids)),
    request_count = as.integer(requests),
    retry_count = as.integer(retries),
    rate_limit_count = as.integer(rate_limits),
    rescued_sub_ids = sort(unique(rescued_ids), method = "radix"),
    overflow = overflow,
    wall_clock_seconds = unname(proc.time()[["elapsed"]] - started),
    queries_walked = as.integer(queries_walked),
    raw_rows = as.integer(raw_rows)
  )
}

fec_api_bulk_rescue <- function(
  connection,
  cycles,
  api_key,
  concurrency,
  transport,
  sleep,
  jitter,
  before_request,
  data_root = mentat_default_data_root(),
  cap = fec_api_rescue_cap(),
  lookup_cache = NULL,
  company_filter = NULL
) {
  if (!DBI::dbExistsTable(connection, "bulk_candidates")) {
    candidates <- data.frame(
      company = character(), cycle = integer(), sub_id = character(),
      contributor_name = character(), contributor_zip = character(),
      stringsAsFactors = FALSE
    )
  } else {
    placeholders <- paste(rep("?", length(cycles)), collapse = ", ")
    candidates <- DBI::dbGetQuery(
      connection,
      paste0(
        "SELECT b.* FROM bulk_candidates b ",
        "LEFT JOIN contributions c ON c.sub_id=b.sub_id ",
        "WHERE c.sub_id IS NULL AND b.cycle IN (", placeholders, ") ",
        "ORDER BY b.company, b.cycle, b.sub_id"
      ),
      params = as.list(as.integer(cycles))
    )
  }
  if (!is.null(company_filter) && nrow(candidates)) {
    candidates <- candidates[
      candidates$company %in% trim_text(company_filter),
      ,
      drop = FALSE
    ]
  }
  if (nrow(candidates)) {
    candidates <- candidates[!duplicated(candidates$sub_id), , drop = FALSE]
  }
  lookup_cache <- lookup_cache %||% fec_api_run_lookups(connection)
  rosters <- lookup_cache$rosters
  match_overrides <- lookup_cache$match_overrides
  home_states <- lookup_cache$home_states
  trusted_by_company <- lookup_cache$trusted_by_company
  result <- fec_api_execute_rescue_plan(
    candidates = candidates,
    cap = cap,
    api_key = api_key,
    concurrency = concurrency,
    transport = transport,
    sleep = sleep,
    jitter = jitter,
    before_request = before_request,
    on_exact = function(candidate, rows, page) invisible(TRUE),
    on_complete = function(candidate, pages, exact_rows) {
      company <- trim_text(candidate$company)
      roster <- rosters[[company]]
      variant_set <- paste(
        "P3_bulk_rescue", company, candidate$cycle, candidate$sub_id,
        sep = ":"
      )
      DBI::dbWithTransaction(connection, {
        for (page_index in seq_along(pages)) {
          page <- pages[[page_index]]
          records <- flatten_fec_rows(
            page$rows,
            industry = MENTAT_INDUSTRY,
            company = company,
            variants = roster$variant,
            phase = "P3_bulk_rescue",
            exclusions = fec_api_roster_exclusions(roster),
            trusted_name_keys = trusted_by_company[[company]],
            match_overrides = match_overrides,
            home_states = home_states,
            scraped_at_value = fec_api_deterministic_timestamp(page$rows)
          )
          if (nrow(records)) data.table::setorder(records, sub_id)
          checkpoint_contribution_page(
            connection,
            records,
            company,
            as.integer(candidate$cycle),
             variant_set,
             page = page_index - 1L,
             records_total = page$count %||% length(page$rows),
             zero_verified = 1L,
             use_transaction = FALSE
           )
        }
      })
      invisible(TRUE)
    }
  )
  overflow <- result$overflow
  if (!"overflow_reason" %in% names(overflow)) {
    overflow$overflow_reason <- character(nrow(overflow))
  }
  overflow_target <- file.path(
    mentat_bootstrap_dirs(data_root)$reports,
    "bulk_rescue_overflow.csv"
  )
  atomic_write_csv(overflow, overflow_target)
  result$overflow_path <- overflow_target
  result
}

fec_api_deterministic_timestamp <- function(rows) {
  load_dates <- vapply(rows, function(row) {
    trim_text(row_scalar(row, "load_date", ""))
  }, character(1L))
  load_dates <- load_dates[nzchar(load_dates)]
  if (length(load_dates)) max(load_dates) else "1970-01-01T00:00:00+0000"
}

fec_api_log_page_canaries <- function(
  connection,
  unit,
  page_index,
  page,
  use_transaction = TRUE
) {
  sub_ids <- vapply(page$rows, function(row) {
    trim_text(row_scalar(row, "sub_id", ""))
  }, character(1L))
  checks <- data.table::data.table(
    check_name = c("api_http_success", "api_sub_id", "api_keyset_pagination"),
    passed = c(
      TRUE,
      !length(sub_ids) || all(nzchar(sub_ids)),
      isTRUE(page$complete) || length(page$last_indexes) > 0L
    ),
    detail = c(
      paste0("rows=", length(page$rows)),
      paste0("rows=", length(sub_ids)),
      paste0(
        "rows_collected=", page$rows_collected %||% length(page$rows),
        "; count=", page$count,
        "; last_indexes=", fec_api_keyset_signature(page$last_indexes)
      )
    )
  )
  log_page_canaries(
    connection,
    unit$company,
    unit$cycle,
    unit$id,
    page_index,
    checks,
    use_transaction = use_transaction
  )
  if (any(!checks$passed)) {
    stop("FEC API page canary failed for work unit: ", unit$id, call. = FALSE)
  }
}

fec_api_corporate_records <- function(
  connection,
  unit,
  rows,
  match_overrides = NULL,
  trusted_name_keys = character(),
  home_states = NULL
) {
  records <- flatten_fec_rows(
    rows,
    industry = unit$industry,
    company = unit$company,
    variants = unit$company_variants,
    phase = "P2_company_name",
    exclusions = unit$exclusions,
    trusted_name_keys = trusted_name_keys,
    match_overrides = match_overrides %||% company_match_overrides_data(connection),
    home_states = home_states %||% company_home_states_data(connection),
    scraped_at_value = fec_api_deterministic_timestamp(rows)
  )
  if (nrow(records)) {
    individual <- which(toupper(trim_text(records$entity_type)) == "IND")
    if (length(individual)) {
      records$company_match_status[individual] <- "rejected"
      records$company_match_reason[individual] <- "corporate_query_individual_entity"
    }
    missing_entity <- which(!nzchar(trim_text(records$entity_type)))
    if (length(missing_entity)) {
      records$company_match_status[missing_entity] <- "review"
      records$company_match_reason[missing_entity] <- "corporate_query_missing_entity_type"
    }
    junk <- vapply(records$contributor_employer, junk_employer_reason, character(1L))
    junk_index <- which(!is.na(junk))
    if (length(junk_index)) {
      records$company_match_status[junk_index] <- "rejected"
      records$company_match_reason[junk_index] <- junk[junk_index]
    }
  }
  records[, .(
    sub_id, contributor_name, contributor_city, contributor_state,
    contributor_zip, contributor_employer, contributor_occupation,
    entity_type, is_entity_contributor, committee_id, committee_name,
    recipient_committee_type, recipient_committee_designation,
    contribution_receipt_date,
    contribution_receipt_amount, industry, company, matched_variant,
    cycle = as.integer(unit$cycle), scraped_at, transaction_id, original_sub_id,
    amendment_indicator, report_year, report_type, file_num, pdf_url, load_date,
    filing_form, receipt_type, receipt_type_full, line_number, line_number_label,
    memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name,
    is_conduit_leg, is_memo_leg, is_passthrough_leg,
    superseded_by_amendment, duplicate_filing_version, duplicate_memo,
    company_match_status, company_match_reason,
    excluded_reason
  )]
}

fec_api_store_page <- function(
  connection,
  state,
  page,
  match_overrides,
  trusted_name_keys,
  home_states,
  use_transaction = TRUE
) {
  action <- function() {
    unit <- state$unit
    page_index <- as.integer(page$page_number)
    fec_api_log_page_canaries(
      connection,
      unit,
      page_index,
      page,
      use_transaction = FALSE
    )
    records_total <- if (!is.na(page$count)) page$count else state$rows_seen
    if (identical(unit$kind, "employer")) {
      records <- flatten_fec_rows(
        page$rows,
        industry = unit$industry,
        company = unit$company,
        variants = unit$company_variants,
        phase = unit$phase,
        exclusions = unit$exclusions,
        trusted_name_keys = trusted_name_keys,
        match_overrides = match_overrides,
        home_states = home_states,
        scraped_at_value = fec_api_deterministic_timestamp(page$rows)
      )
      if (nrow(records)) data.table::setorder(records, sub_id)
      checkpoint_contribution_page(
        connection,
        records,
        unit$company,
        unit$cycle,
        unit$id,
        page_index,
        records_total,
        zero_verified = 1L,
        use_transaction = FALSE
      )
    } else if (identical(unit$kind, "identity")) {
      checkpoint_identity_query_page(
        connection = connection,
        rows = page$rows,
        page = page_index,
        records_total = records_total,
        variant_set = unit$id,
        industry = unit$industry,
        company = unit$company,
        cycle = unit$cycle,
        seed = unit$seed,
        company_variants = unit$company_variants,
        exclusions = unit$exclusions,
        scraped_at_value = fec_api_deterministic_timestamp(page$rows),
        match_overrides = match_overrides,
        use_transaction = FALSE
      )
    } else if (identical(unit$kind, "corporate")) {
      corporate <- fec_api_corporate_records(
        connection,
        unit,
        page$rows,
        match_overrides = match_overrides,
        trusted_name_keys = trusted_name_keys,
        home_states = home_states
      )
      if (nrow(corporate)) data.table::setorder(corporate, sub_id)
      checkpoint_corporate_page(
        connection,
        corporate,
        unit$company,
        unit$cycle,
        unit$id,
        page_index,
        records_total,
        zero_verified = 1L,
        use_transaction = FALSE
      )
    } else {
      stop("Unknown FEC API work-unit kind: ", unit$kind, call. = FALSE)
    }
  }
  if (isTRUE(use_transaction)) {
    DBI::dbWithTransaction(connection, action())
  } else {
    action()
  }
  invisible(TRUE)
}

fec_api_store_results <- function(connection, result, lookup_cache = NULL) {
  state_names <- sort(names(result$units), method = "radix")
  lookup_cache <- lookup_cache %||% fec_api_run_lookups(connection)
  match_overrides <- lookup_cache$match_overrides
  home_states <- lookup_cache$home_states
  trusted_by_company <- lookup_cache$trusted_by_company
  for (state_name in state_names) {
    state <- result$units[[state_name]]
    if (isTRUE(state$stored_complete)) next
    pages <- state$pages
    if (!isTRUE(state$complete)) {
      stop("Cannot store an incomplete FEC API work unit: ", state_name, call. = FALSE)
    }
    DBI::dbWithTransaction(connection, {
      for (page in pages) {
        fec_api_store_page(
          connection,
          state,
          page,
          match_overrides,
          trusted_by_company[[state$unit$company]],
          home_states,
          use_transaction = FALSE
        )
      }
      fec_api_mark_work_unit_stored(connection, state_name)
    })
  }
  invisible(result$rows)
}

fec_api_record_decompositions <- function(connection, run_id, decompositions) {
  if (is.null(run_id) || !nzchar(trim_text(run_id)) || !length(decompositions)) {
    return(invisible(NULL))
  }
  cycles <- sort(unique(vapply(
    decompositions,
    function(event) as.integer(event$cycle),
    integer(1L)
  )))
  DBI::dbWithTransaction(connection, {
    for (cycle in cycles) {
      events <- decompositions[vapply(
        decompositions,
        function(event) identical(as.integer(event$cycle), as.integer(cycle)),
        logical(1L)
      )]
      current <- DBI::dbGetQuery(
        connection,
        paste(
          "SELECT decomposition_log FROM run_log",
          "WHERE run_id=? AND cycle=?"
        ),
        params = list(run_id, as.integer(cycle))
      )
      existing <- list()
      if (nrow(current)) {
        text <- trim_text(current$decomposition_log[[1L]])
        if (nzchar(text)) {
          existing <- jsonlite::fromJSON(text, simplifyVector = FALSE)
        }
      }
      payload <- jsonlite::toJSON(
        c(existing, events),
        auto_unbox = TRUE,
        null = "null",
        na = "null",
        digits = NA
      )
      DBI::dbExecute(
        connection,
        paste(
          "UPDATE run_log SET decomposition_log=?",
          "WHERE run_id=? AND cycle=?"
        ),
        params = list(payload, run_id, as.integer(cycle))
      )
    }
  })
  invisible(NULL)
}

fec_api_collect_checkpointed <- function(
  connection,
  units,
  api_key,
  concurrency,
  transport,
  sleep,
  jitter,
  before_request,
  run_id = NULL,
  lookup_cache = NULL
) {
  initial_states <- fec_api_load_progress(connection, units)

  # A budget/quota pause is raised INSIDE fec_api_collect_work_units and unwinds
  # past the fec_api_store_results call below. Any unit fetched during that
  # window stayed checkpointed but was never stored, so a phase that always
  # exhausts its budget before finishing (e.g. thousands of P2_name units) could
  # fetch forever and store nothing. Flush the fetched-but-unstored units first,
  # then re-signal the pause so the caller still stops.
  flush_fetched <- function() {
    states <- fec_api_load_progress(connection, units)
    pending <- list()
    for (unit in units) {
      state <- states[[unit$id]]
      if (is.null(state)) next
      if (!isTRUE(state$complete) || isTRUE(state$stored_complete)) next
      state$unit <- unit
      pending[[unit$id]] <- state
    }
    if (!length(pending)) {
      return(invisible(0L))
    }
    fec_api_store_results(
      connection,
      list(units = pending, rows = 0L),
      lookup_cache = lookup_cache
    )
    cat(sprintf(
      "FEC API pause flush: stored %d fetched work unit(s) before pausing.
",
      length(pending)
    ))
    invisible(length(pending))
  }
  # Catch EVERY abort path, not just budget/quota. A hard error (e.g. an FEC
  # connection_error after retries) unwinds past the store call exactly the same
  # way and would discard the whole window's fetched work. Re-signalling the
  # original condition preserves the caller's pause-vs-fail semantics.
  on_abort <- function(cond) {
    # The flush must never mask the original abort, but it must not vanish either:
    # a silent try() here hid a store failure behind a clean-looking fetch loop.
    flushed <- try(flush_fetched(), silent = TRUE)
    if (inherits(flushed, "try-error")) {
      cat(sprintf(
        "FEC API pause flush FAILED (fetched work stays checkpointed): %s\n",
        conditionMessage(attr(flushed, "condition"))
      ))
    }
    stop(cond)
  }

  result <- tryCatch(
    fec_api_collect_work_units(
      units,
      api_key = api_key,
      concurrency = concurrency,
      transport = transport,
      sleep = sleep,
      jitter = jitter,
      initial_states = initial_states,
      page_callback = function(state, page) {
        fec_api_checkpoint_page(connection, state, page)
      },
      before_request = before_request
    ),
    error = on_abort
  )
  fec_api_record_decompositions(connection, run_id, result$decompositions)
  fec_api_store_results(connection, result, lookup_cache = lookup_cache)
  result
}

fec_api_determinism_spot_check <- function(
  result,
  api_key,
  concurrency,
  transport,
  sleep,
  jitter,
  before_request = function(count) invisible(NULL)
) {
  if (!length(result$units)) return(NA)
  decomposed_ids <- vapply(
    result$decompositions %||% list(),
    function(event) trim_text(event$unit_id),
    character(1L)
  )
  eligible <- setdiff(sort(names(result$units), method = "radix"), decomposed_ids)
  if (!length(eligible)) return(TRUE)
  first_name <- eligible[[1L]]
  first <- result$units[[first_name]]
  if (!length(first$pages)) return(TRUE)
  spec <- fec_api_request_spec(first$unit, list())
  repeated <- fec_api_fetch_with_retry(
    list(spec),
    api_key,
    concurrency,
    transport,
    sleep = sleep,
    jitter = jitter,
    before_request = before_request
  )
  page <- fec_api_parse_page(repeated$responses[[1L]])
  expected <- vapply(first$pages[[1L]]$rows, function(row) {
    row_scalar(row, "sub_id", "")
  }, character(1L))
  actual <- vapply(page$rows, function(row) {
    row_scalar(row, "sub_id", "")
  }, character(1L))
  list(
    identical = identical(sort(expected), sort(actual)),
    request_count = repeated$request_count,
    retry_count = repeated$retry_count
  )
}

fec_api_record_metric <- function(connection, run_id, phase, result) {
  if (is.null(run_id) || !nzchar(trim_text(run_id))) return(invisible(NULL))
  rows_per_second <- if (result$wall_clock_seconds > 0) {
    result$rows / result$wall_clock_seconds
  } else 0
  ended <- format(Sys.time(), "%Y-%m-%dT%H:%M:%OS3%z")
  started <- format(
    Sys.time() - result$wall_clock_seconds,
    "%Y-%m-%dT%H:%M:%OS3%z"
  )
  DBI::dbExecute(
    connection,
    paste(
      "INSERT OR REPLACE INTO run_metrics",
      "(run_id, phase, started_at, ended_at, wall_clock_seconds,",
      "rows_processed, request_count, rows_per_second, detail)",
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ),
    params = list(
      run_id,
      phase,
      started,
      ended,
      result$wall_clock_seconds,
      as.integer(result$rows),
      as.integer(result$request_count),
      as.numeric(rows_per_second),
      "FEC schedule_a JSON API"
    )
  )
  invisible(NULL)
}

fec_api_log_phase <- function(phase, result) {
  rate <- if (result$wall_clock_seconds > 0) {
    result$rows / result$wall_clock_seconds
  } else 0
  cat(sprintf(
    "FEC API phase %s: rows=%d requests=%d retries=%d wall=%.3fs rows/sec=%.2f\n",
    phase,
    result$rows,
    result$request_count,
    result$retry_count,
    result$wall_clock_seconds,
    rate
  ))
}

collect_crypto_api <- function(
  connection,
  cycles = c(2022L, 2024L, 2026L),
  phase2_names = FALSE,
  api_key = fec_api_key(),
  concurrency = fec_api_concurrency(),
  transport = fec_api_default_transport,
  sleep = Sys.sleep,
  jitter = stats::runif,
  run_id = NULL,
  data_root = mentat_default_data_root(),
  company_filter = NULL,
  budget_connection = NULL
) {
  require_package("data.table")
  require_package("jsonlite")
  run_started <- proc.time()[["elapsed"]]
  cycles <- sort(unique(as.integer(cycles)))
  if (!length(cycles) || anyNA(cycles) ||
      any(!cycles %in% c(2022L, 2024L, 2026L))) {
    stop("Cycles must be a subset of 2022, 2024, and 2026.", call. = FALSE)
  }
  lookup_cache <- fec_api_filter_lookups(
    fec_api_run_lookups(connection),
    company_filter
  )
  budget_connection <- budget_connection %||% connection
  budget_id <- fec_api_budget_id(api_key)
  requests_reserved_run <- 0L
  reserve_request <- function(count) {
    fec_api_budget_reserve(
      budget_connection,
      count,
      budget_id = budget_id
    )
    requests_reserved_run <<- requests_reserved_run + as.integer(count)
    invisible(NULL)
  }
  is_pause_condition <- function(value) {
    inherits(value, c(
      "mentat_api_budget_exhausted",
      "mentat_api_quota_exhausted"
    ))
  }
  collect_phase <- function(units) {
    tryCatch(
      fec_api_collect_checkpointed(
        connection,
        units,
        api_key,
        concurrency,
        transport,
        sleep,
        jitter,
        reserve_request,
        run_id = run_id,
        lookup_cache = lookup_cache
      ),
      mentat_api_budget_exhausted = function(condition) condition,
      mentat_api_quota_exhausted = function(condition) condition
    )
  }
  pause_result <- function(condition, rows = 0L, retries = 0L) {
    budget <- fec_api_budget_status(
      budget_connection,
      budget_id = budget_id
    )
    requests_run <- requests_reserved_run
    cat(sprintf(
      paste0(
        "FEC API run paused: requests-used-run=%d requests-used-window=%d ",
        "requests-remaining=%d; checkpoints saved.\n"
      ),
      requests_run,
      budget$requests_used,
      budget$requests_remaining
    ))
    list(
      paused = TRUE,
      pause_reason = conditionMessage(condition),
      retries = as.integer(retries),
      request_count = as.integer(requests_run),
      requests_used = budget$requests_used,
      requests_remaining = budget$requests_remaining,
      rows = as.integer(rows),
      determinism = NA,
      variant_sets_walked = 0L
    )
  }
  total_requests <- 0L
  total_retries <- 0L
  employer <- collect_phase(fec_api_employer_units(
    connection,
    cycles,
    rosters = lookup_cache$rosters,
    match_overrides = lookup_cache$match_overrides,
    home_states = lookup_cache$home_states
  ))
  if (is_pause_condition(employer)) {
    return(pause_result(employer))
  }
  fec_api_log_phase("employer", employer)
  fec_api_record_metric(connection, run_id, "collect_employer", employer)
  total_requests <- total_requests + employer$request_count
  total_retries <- total_retries + employer$retry_count
  employer_companies <- unique(vapply(
    employer$units,
    function(state) state$unit$company,
    character(1L)
  ))
  for (company in sort(employer_companies, method = "radix")) {
    for (cycle in cycles) {
      retag_employer_company_matches(connection, company, cycle)
    }
  }
  rescue <- tryCatch(
    fec_api_bulk_rescue(
      connection = connection,
      cycles = cycles,
      api_key = api_key,
      concurrency = concurrency,
      transport = transport,
      sleep = sleep,
      jitter = jitter,
      before_request = reserve_request,
      data_root = data_root,
      lookup_cache = lookup_cache,
      company_filter = names(lookup_cache$rosters)
    ),
    mentat_api_budget_exhausted = function(condition) condition,
    mentat_api_quota_exhausted = function(condition) condition
  )
  if (is_pause_condition(rescue)) {
    return(pause_result(rescue, employer$rows, total_retries))
  }
  fec_api_log_phase("bulk_rescue", rescue)
  fec_api_record_metric(connection, run_id, "collect_bulk_rescue", rescue)
  total_requests <- total_requests + rescue$request_count
  total_retries <- total_retries + rescue$retry_count
  determinism <- tryCatch(
    fec_api_determinism_spot_check(
      employer,
      api_key,
      concurrency,
      transport,
      sleep,
      jitter,
      before_request = reserve_request
    ),
    mentat_api_budget_exhausted = function(condition) condition,
    mentat_api_quota_exhausted = function(condition) condition
  )
  if (is_pause_condition(determinism)) {
    return(pause_result(determinism, employer$rows, total_retries))
  }
  if (is.list(determinism)) {
    total_requests <- total_requests + determinism$request_count
    total_retries <- total_retries + determinism$retry_count
    determinism_value <- determinism$identical
  } else {
    determinism_value <- determinism
  }
  if (identical(determinism_value, FALSE)) {
    stop("FEC API determinism spot-check returned a different sub_id set.", call. = FALSE)
  }
  identity <- list(
    units = list(), request_count = 0L, retry_count = 0L,
    rate_limit_count = 0L, rows = 0L, rows_total = 0L,
    final_concurrency = as.integer(concurrency), wall_clock_seconds = 0
  )
  if (isTRUE(phase2_names)) {
    identity <- collect_phase(fec_api_identity_units(
      connection,
      cycles,
      rosters = lookup_cache$rosters
    ))
    if (is_pause_condition(identity)) {
      return(pause_result(identity, employer$rows + rescue$rows, total_retries))
    }
    fec_api_log_phase("identity", identity)
    fec_api_record_metric(connection, run_id, "collect_identity", identity)
    total_requests <- total_requests + identity$request_count
    total_retries <- total_retries + identity$retry_count
  }
  corporate <- collect_phase(fec_api_corporate_units(
    connection,
    cycles,
    rosters = lookup_cache$rosters
  ))
  if (is_pause_condition(corporate)) {
    return(pause_result(
      corporate,
      employer$rows + rescue$rows + identity$rows,
      total_retries
    ))
  }
  fec_api_log_phase("corporate", corporate)
  fec_api_record_metric(connection, run_id, "collect_corporate", corporate)
  total_requests <- total_requests + corporate$request_count
  total_retries <- total_retries + corporate$retry_count
  resolve_recipient_register_committee_ids(connection, log = TRUE)
  total_rows <- employer$rows + rescue$rows + identity$rows + corporate$rows
  wall_clock_seconds <- proc.time()[["elapsed"]] - run_started
  rows_per_second <- if (wall_clock_seconds > 0) {
    total_rows / wall_clock_seconds
  } else {
    0
  }
  total_metric <- list(
    rows = total_rows,
    request_count = total_requests,
    wall_clock_seconds = unname(wall_clock_seconds)
  )
  fec_api_record_metric(connection, run_id, "collect_total", total_metric)
  budget <- fec_api_budget_status(
    budget_connection,
    budget_id = budget_id
  )
  requests_used_run <- requests_reserved_run
  cat(sprintf(
    paste0(
      "FEC API run total: rows=%d requests=%d retries=%d ",
      "wall=%.3fs rows/sec=%.2f rate-cap-usage=%.1f%% ",
      "requests-used-run=%d requests-used-window=%d requests-remaining=%d\n"
    ),
    total_rows,
    total_requests,
    total_retries,
    wall_clock_seconds,
    rows_per_second,
    100 * total_requests / FEC_API_HOURLY_REQUEST_CAP,
    requests_used_run,
    budget$requests_used,
    budget$requests_remaining
  ))
  if (total_requests >= 900L) {
    warning(
      "FEC API request count is near or above the registered-key hourly cap of 1,000.",
      call. = FALSE
    )
  }
  list(
    paused = FALSE,
    retries = total_retries,
    determinism = determinism_value,
    request_count = total_requests,
    requests_used = budget$requests_used,
    requests_remaining = budget$requests_remaining,
    rows = total_rows,
    wall_clock_seconds = unname(wall_clock_seconds),
    rows_per_second = rows_per_second,
    rescued = rescue$rows,
    rescue_overflow = nrow(rescue$overflow),
    rescue_overflow_path = rescue$overflow_path,
    variant_sets_walked = length(employer$units) +
      length(identity$units) + length(corporate$units) + rescue$queries_walked
  )
}
