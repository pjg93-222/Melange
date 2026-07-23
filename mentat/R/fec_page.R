fec_runtime_value <- function(session, expression) {
  response <- session$Runtime$evaluate(
    expression = expression,
    returnByValue = TRUE,
    awaitPromise = TRUE
  )
  value <- response$result$value
  if (is.null(value)) {
    stop("Chromote evaluation returned no value.", call. = FALSE)
  }
  value
}

fec_build_url <- function(
  cycle,
  variants,
  query_field = "contributor_employer",
  query_filters = list()
) {
  cycle <- as.integer(cycle)
  if (!cycle %in% c(2022L, 2024L, 2026L)) {
    stop("Unsupported two-year transaction period: ", cycle, call. = FALSE)
  }
  allowed_fields <- c("contributor_employer", "contributor_name")
  if (!query_field %in% allowed_fields) {
    stop("Unsupported FEC query field: ", query_field, call. = FALSE)
  }
  variants <- unique(trim_text(variants))
  variants <- variants[!is.na(variants) & nzchar(variants)]
  if (identical(query_field, "contributor_employer")) {
    variants <- unique(normalize_register_key(variants))
    variants <- variants[nzchar(variants)]
  }
  if (!length(variants)) {
    stop("At least one non-empty FEC query value is required.", call. = FALSE)
  }
  parameters <- c(
    paste0("two_year_transaction_period=", cycle),
    paste0(
      query_field,
      "=",
      vapply(
        variants,
        utils::URLencode,
        character(1L),
        reserved = TRUE,
        repeated = TRUE,
        USE.NAMES = FALSE
      )
    )
  )
  allowed_filters <- c(
    "contributor_zip",
    "contributor_city",
    "contributor_state"
  )
  if (length(query_filters)) {
    if (is.null(names(query_filters)) ||
        any(!names(query_filters) %in% allowed_filters)) {
      stop("Unsupported FEC query filter.", call. = FALSE)
    }
    for (filter_name in names(query_filters)) {
      filter_values <- unique(trim_text(query_filters[[filter_name]]))
      filter_values <- filter_values[
        !is.na(filter_values) & nzchar(filter_values)
      ]
      if (!length(filter_values)) {
        next
      }
      parameters <- c(
        parameters,
        paste0(
          filter_name,
          "=",
          vapply(
            filter_values,
            utils::URLencode,
            character(1L),
            reserved = TRUE,
            repeated = TRUE,
            USE.NAMES = FALSE
          )
        )
      )
    }
  }
  paste0(
    "https://www.fec.gov/data/receipts/individual-contributions/?",
    paste(parameters, collapse = "&")
  )
}

new_fec_session <- function() {
  require_package("chromote")
  chromote::ChromoteSession$new()
}

new_fec_session_state <- function(session) {
  state <- new.env(parent = emptyenv())
  state$session <- session
  class(state) <- "mentat_fec_session_state"
  state
}

fec_active_session <- function(session) {
  if (inherits(session, "mentat_fec_session_state")) {
    return(session$session)
  }
  session
}

fec_replace_session <- function(session, replacement) {
  if (inherits(session, "mentat_fec_session_state")) {
    session$session <- replacement
  }
  invisible(replacement)
}

fec_recover_session <- function(session) {
  replacement <- tryCatch(
    session$respawn(),
    error = function(error) NULL
  )
  if (is.null(replacement)) {
    replacement <- new_fec_session()
  }
  replacement
}

fec_results_ready <- function(session) {
  # recordsDisplay==0 is ALSO the table's state before the API response lands,
  # so it cannot mean "ready" by itself (verified live 2026-07-18: reading at
  # that moment yields recordsTotal=0 for employers that have rows). Ready =
  # the fetch overlay is hidden AND either data rows exist or the table shows
  # its confirmed-empty message row.
  isTRUE(fec_runtime_value(
    session,
    paste0(
      "(function(){try{",
      "if(!window.jQuery){return false;}",
      "var dt=window.jQuery('#results').DataTable();",
      "var info=dt.page.info();",
      "if(!info||typeof info.recordsTotal!=='number'){return false;}",
      "var ov=document.querySelector('.overlay');",
      "if(ov && getComputedStyle(ov).display!=='none'){return false;}",
      "if(dt.rows().data().toArray().length>0){return true;}",
      "var r=document.querySelector('#results tbody tr');",
      "return !!r && /No data available in table/.test(r.textContent);",
      "}catch(e){return false;}})()"
    )
  ))
}

fec_wait_until <- function(predicate, timeout_seconds = 60, interval_seconds = 0.5) {
  deadline <- Sys.time() + timeout_seconds
  repeat {
    if (isTRUE(predicate())) {
      return(invisible(TRUE))
    }
    if (Sys.time() >= deadline) {
      stop("Timed out waiting for the FEC results table.", call. = FALSE)
    }
    Sys.sleep(interval_seconds)
  }
}

fec_navigate <- function(
  session,
  url,
  timeout_seconds = 180,
  retries = 3L
) {
  retries <- as.integer(retries)
  last_error <- NULL
  for (attempt in seq_len(retries + 1L)) {
    result <- tryCatch({
      session$Page$navigate(url = url)
      fec_wait_until(
        function() fec_results_ready(session),
        timeout_seconds = timeout_seconds
      )
      TRUE
    }, error = function(error) {
      last_error <<- error
      if (fec_is_transient_chromote_error(error)) {
        stop(error)
      }
      FALSE
    })
    if (isTRUE(result)) {
      return(attempt - 1L)
    }
    if (attempt <= retries) {
      Sys.sleep(min(30, 2 ^ attempt))
    }
  }
  stop(
    "FEC navigation failed after ", retries, " retries: ",
    conditionMessage(last_error),
    call. = FALSE
  )
}

fec_set_page_length <- function(session, page_length = 100L) {
  page_length <- as.integer(page_length)
  changed <- fec_runtime_value(
    session,
    sprintf(
      paste0(
        "(function(){var dt=window.jQuery('#results').DataTable();",
        "if(dt.page.len()===%d){return false;}",
        "var select=document.querySelector('#results_length select, ",
        ".dataTables_length select');",
        "if(select){select.value='%d';",
        "window.jQuery(select).trigger('change');}",
        "else{dt.page.len(%d).draw();}",
        "return true;})()"
      ),
      page_length,
      page_length,
      page_length
    )
  )
  if (!is.logical(changed) || length(changed) != 1L || is.na(changed)) {
    stop("Could not set the FEC results page length.", call. = FALSE)
  }
  fec_wait_until(function() {
    if (!fec_results_ready(session)) {
      return(FALSE)
    }
    isTRUE(fec_runtime_value(
      session,
      sprintf(
        paste0(
          "(function(){",
          "var dt=window.jQuery('#results').DataTable();",
          "var info=dt.page.info();",
          "var rows=dt.rows().data().toArray().length;",
          "var expected=(info.page+1<info.pages)",
          "?info.length:(info.recordsDisplay-info.start);",
          "return (info.length===%d || info.recordsDisplay===0)",
          " && rows===expected;",
          "})()"
        ),
        page_length
      )
    ))
  })
  payload <- fec_read_page(session)
  if (payload$info$length != page_length &&
      payload$info$recordsDisplay != 0L) {
    stop("Could not set the FEC results page length.", call. = FALSE)
  }
  payload
}

fec_read_page <- function(session) {
  require_package("jsonlite")
  expression <- paste0(
    "JSON.stringify((function(){",
    "var dt=window.jQuery('#results').DataTable();",
    "var info=dt.page.info();",
    "var rows=dt.rows().data().toArray();",
    "return {info:info,rows:rows};",
    "})())"
  )
  json <- fec_runtime_value(session, expression)
  payload <- jsonlite::fromJSON(json, simplifyVector = FALSE)
  if (is.null(payload$info) || is.null(payload$rows)) {
    stop("FEC DataTable payload is missing info or rows.", call. = FALSE)
  }
  payload$info <- lapply(payload$info, function(value) {
    if (length(value) == 1L) value else value
  })
  numeric_fields <- c(
    "page", "pages", "start", "end", "length", "recordsTotal", "recordsDisplay"
  )
  for (field in numeric_fields) {
    payload$info[[field]] <- as.integer(payload$info[[field]] %||% NA_integer_)
  }
  payload$info$serverSide <- isTRUE(payload$info$serverSide)
  payload
}

fec_canaries <- function(payload, expected_total = NULL) {
  info <- payload$info
  rows <- payload$rows
  row_ids <- vapply(
    rows,
    function(row) trim_text(row$sub_id %||% ""),
    character(1L)
  )
  checks <- list(
    server_side = list(
      passed = isTRUE(info$serverSide),
      detail = paste0("serverSide=", as.character(info$serverSide))
    ),
    records_total_stable = list(
      passed = is.null(expected_total) ||
        identical(as.integer(info$recordsTotal), as.integer(expected_total)),
      detail = paste0(
        "recordsTotal=", info$recordsTotal,
        if (!is.null(expected_total)) paste0("; expected=", expected_total) else ""
      )
    ),
    nonempty_rows_while_pages_remain = list(
      passed = !(info$page + 1L < info$pages && length(rows) == 0L),
      detail = paste0("page=", info$page, "; pages=", info$pages, "; rows=", length(rows))
    ),
    nonempty_sub_id = list(
      passed = !length(rows) || all(nzchar(row_ids)),
      detail = paste0("rows=", length(rows), "; nonempty_sub_id=", sum(nzchar(row_ids)))
    ),
    page_row_count = list(
      passed = length(rows) == if (info$page + 1L < info$pages) {
        info$length
      } else {
        info$recordsDisplay - info$start
      },
      detail = paste0(
        "page=", info$page, "; pages=", info$pages, "; rows=", length(rows),
        "; expected=", if (info$page + 1L < info$pages) {
          info$length
        } else {
          info$recordsDisplay - info$start
        }
      )
    )
  )
  data.table::rbindlist(lapply(names(checks), function(name) {
    data.table::data.table(
      check_name = name,
      passed = as.integer(isTRUE(checks[[name]]$passed)),
      detail = checks[[name]]$detail
    )
  }))
}

fec_click_next <- function(session, current_page) {
  clicked <- fec_runtime_value(
    session,
    paste0(
      "(function(){",
      "var next=document.querySelector('.next:not(.disabled)');",
      "if(!next){return false;} next.click(); return true;",
      "})()"
    )
  )
  if (!isTRUE(clicked)) {
    stop("FEC pagination expected another page but .next was unavailable.", call. = FALSE)
  }
  fec_wait_until(function() {
    if (!fec_results_ready(session)) {
      return(FALSE)
    }
    page_is_complete <- fec_runtime_value(
      session,
      sprintf(
        paste0(
          "(function(){",
          "var dt=window.jQuery('#results').DataTable();",
          "var info=dt.page.info();",
          "var rows=dt.rows().data().toArray().length;",
          "var expected=(info.page+1<info.pages)",
          "?info.length:(info.recordsDisplay-info.start);",
          "return info.page>%d && rows===expected;",
          "})()"
        ),
        as.integer(current_page)
      )
    )
    isTRUE(page_is_complete)
  })
  fec_read_page(session)
}

fec_is_transient_chromote_error <- function(error) {
  message <- tolower(conditionMessage(error))
  signatures <- c(
    "chromote: timed out waiting for response",
    "timed out waiting for response to command",
    "timed out waiting for the fec results table",
    # A canary mismatch means the DataTable DOM was read between browser-side
    # updates. Never accept that page, but replay the complete query through
    # the existing bounded retry path instead of aborting the industry run.
    "fec canary failure",
    "fec export",
    "websocket",
    "connection closed",
    "target closed",
    "session closed",
    "session has been closed"
  )
  any(vapply(
    signatures,
    function(signature) grepl(signature, message, fixed = TRUE),
    logical(1L)
  ))
}

fec_query_retry_sleep <- function(attempt) {
  Sys.sleep(min(15, 2 ^ as.integer(attempt)))
}

fec_url_with_date_range <- function(url, min_date, max_date) {
  separator <- if (grepl("?", url, fixed = TRUE)) "&" else "?"
  paste0(
    url,
    separator,
    "min_date=",
    utils::URLencode(format(as.Date(min_date), "%m/%d/%Y"), reserved = TRUE),
    "&max_date=",
    utils::URLencode(format(as.Date(max_date), "%m/%d/%Y"), reserved = TRUE)
  )
}

fec_export_current_query <- function(
  session,
  expected_rows,
  timeout_seconds = 300
) {
  expected_rows <- as.integer(expected_rows)
  if (is.na(expected_rows) || expected_rows < 0L || expected_rows > 100000L) {
    stop("FEC export row count must be between 0 and 100,000.", call. = FALSE)
  }
  if (!expected_rows) return(data.table::data.table())
  clicked <- fec_runtime_value(
    session,
    paste0(
      "(function(){",
      "document.querySelectorAll('.download .js-close').forEach(",
      "function(button){button.click();});",
      "Object.keys(localStorage).filter(function(key){",
      "return key.indexOf('download-')===0;",
      "}).forEach(function(key){localStorage.removeItem(key);});",
      "var button=document.querySelector('.js-export');",
      "if(!button){return false;} button.click(); return true;",
      "})()"
    )
  )
  if (!isTRUE(clicked)) {
    stop("FEC export button was unavailable.", call. = FALSE)
  }
  download_url <- ""
  export_error <- ""
  deadline <- Sys.time() + timeout_seconds
  message("FEC export requested for ", expected_rows, " rows.")
  repeat {
    status <- fec_runtime_value(
      session,
      paste0(
        "(function(){",
        "var keys=Object.keys(localStorage).filter(function(key){",
        "return key.indexOf('download-')===0;",
        "});",
        "for(var i=0;i<keys.length;i++){",
        "try{var value=JSON.parse(localStorage.getItem(keys[i]));",
        "if(value.downloadUrl){return {url:value.downloadUrl,error:''};}",
        "}catch(e){}",
        "}",
        "var alert=document.querySelector('.message--alert');",
        "return {url:'',error:alert?(alert.textContent||'').trim():''};",
        "})()"
      )
    )
    if (is.list(status)) {
      download_url <- trim_text(status$url %||% "")
      export_error <- trim_text(status$error %||% "")
    }
    if (nzchar(download_url)) break
    if (nzchar(export_error)) {
      stop("FEC export server error: ", export_error, call. = FALSE)
    }
    if (Sys.time() >= deadline) {
      stop("Timed out waiting for the FEC export.", call. = FALSE)
    }
    Sys.sleep(2)
  }
  require_package("data.table")
  csv_path <- tempfile("mentat-fec-export-", fileext = ".csv")
  on.exit(unlink(csv_path, force = TRUE), add = TRUE)
  download_result <- tryCatch(
    utils::download.file(
      download_url,
      csv_path,
      mode = "wb",
      quiet = TRUE
    ),
    error = function(error) {
      stop(
        "FEC export download failed: ",
        conditionMessage(error),
        call. = FALSE
      )
    }
  )
  if (!identical(as.integer(download_result), 0L)) {
    stop(
      "FEC export download failed with status ",
      download_result,
      ".",
      call. = FALSE
    )
  }
  rows <- data.table::fread(
    csv_path,
    colClasses = "character",
    na.strings = "NA",
    showProgress = FALSE,
    encoding = "UTF-8"
  )
  if (nrow(rows) != expected_rows) {
    stop(
      "FEC export row-count mismatch: expected=", expected_rows,
      " downloaded=", nrow(rows),
      call. = FALSE
    )
  }
  message("FEC export downloaded and verified: ", nrow(rows), " rows.")
  rows[]
}

fec_export_partitions <- function(
  session,
  url,
  expected_total,
  min_date = as.Date("1900-01-01"),
  max_date = as.Date("2100-12-31")
) {
  leaves <- list()
  visit <- function(left, right) {
    partition_url <- fec_url_with_date_range(url, left, right)
    fec_navigate(session, partition_url)
    payload <- fec_set_page_length(session, 30L)
    count <- as.integer(payload$info$recordsTotal)
    if (!count) return(invisible(NULL))
    if (count <= 100000L) {
      leaves[[length(leaves) + 1L]] <<- list(
        url = partition_url,
        count = count,
        min_date = left,
        max_date = right
      )
      return(invisible(NULL))
    }
    if (left >= right) {
      stop(
        "FEC export cannot partition a single date with more than 100,000 rows: ",
        format(left),
        call. = FALSE
      )
    }
    midpoint <- left + floor(as.numeric(right - left) / 2)
    visit(left, midpoint)
    visit(midpoint + 1, right)
    invisible(NULL)
  }
  visit(as.Date(min_date), as.Date(max_date))
  partition_total <- sum(vapply(
    leaves,
    function(leaf) as.integer(leaf$count),
    integer(1L)
  ))
  if (partition_total != as.integer(expected_total)) {
    stop(
      "FEC export date partitions do not cover the query exactly: expected=",
      expected_total,
      " partition_total=",
      partition_total,
      call. = FALSE
    )
  }
  message(
    "FEC export partition plan verified: ",
    length(leaves),
    " file(s), ",
    partition_total,
    " rows."
  )
  leaves
}

fec_walk_variant_set_export <- function(
  session,
  url,
  records_total,
  page_callback,
  canary_callback,
  company,
  cycle,
  variant_set,
  chunk_size = 5000L
) {
  require_package("data.table")
  partitions <- if (records_total <= 100000L) {
    list(list(url = url, count = as.integer(records_total)))
  } else {
    fec_export_partitions(session, url, records_total)
  }
  processed <- 0L
  for (partition_index in seq_along(partitions)) {
    partition <- partitions[[partition_index]]
    message(
      "FEC export file ",
      partition_index,
      "/",
      length(partitions),
      ": ",
      partition$count,
      " rows."
    )
    fec_navigate(session, partition$url)
    payload <- fec_set_page_length(session, 30L)
    observed <- as.integer(payload$info$recordsTotal)
    if (observed != as.integer(partition$count)) {
      stop(
        "FEC export partition changed before download: expected=",
        partition$count,
        " observed=",
        observed,
        call. = FALSE
      )
    }
    exported <- fec_export_current_query(session, observed)
    if (!nrow(exported)) next
    starts <- seq.int(1L, nrow(exported), by = as.integer(chunk_size))
    for (start in starts) {
      end <- min(start + as.integer(chunk_size) - 1L, nrow(exported))
      chunk <- exported[start:end]
      rows <- lapply(seq_len(nrow(chunk)), function(index) {
        as.list(chunk[index])
      })
      processed <- processed + length(rows)
      page_callback(
        rows = rows,
        page = floor((processed - 1L) / 100L),
        records_total = records_total
      )
    }
  }
  checks <- data.table::data.table(
    check_name = "export_row_count",
    passed = as.integer(processed == as.integer(records_total)),
    detail = paste0("rows=", processed, "; expected=", records_total)
  )
  canary_callback(
    company = company,
    cycle = cycle,
    variant_set = variant_set,
    page = max(0L, ceiling(records_total / 100L) - 1L),
    checks = checks
  )
  if (processed != as.integer(records_total)) {
    stop(
      "FEC export processing mismatch: expected=", records_total,
      " processed=", processed,
      call. = FALSE
    )
  }
  list(
    records_total = as.integer(records_total),
    pages = as.integer(ceiling(records_total / 100L)),
    retries = 0L,
    truncated = FALSE,
    export = TRUE
  )
}

fec_walk_variant_set_once <- function(
  session,
  company,
  cycle,
  variants,
  variant_set,
  page_callback,
  canary_callback,
  query_field = "contributor_employer",
  query_filters = list(),
  timeout_seconds = 180,
  retries = 3L,
  sleep_range = c(1.5, 3.5),
  max_pages = Inf
) {
  max_pages <- as.numeric(max_pages)
  if (length(max_pages) != 1L || is.na(max_pages) || max_pages <= 0) {
    stop("max_pages must be a positive number.", call. = FALSE)
  }
  url <- fec_build_url(
    cycle,
    variants,
    query_field = query_field,
    query_filters = query_filters
  )
  retry_count <- fec_navigate(
    session,
    url,
    timeout_seconds = timeout_seconds,
    retries = retries
  )
  initial <- fec_set_page_length(session, 100L)
  records_total <- initial$info$recordsTotal
  if (records_total >= 5000L && is.infinite(max_pages)) {
    exported <- fec_walk_variant_set_export(
      session = session,
      url = url,
      records_total = records_total,
      page_callback = page_callback,
      canary_callback = canary_callback,
      company = company,
      cycle = cycle,
      variant_set = variant_set
    )
    exported$retries <- as.integer(exported$retries) + as.integer(retry_count)
    return(exported)
  }
  expected_total <- records_total
  first_payload <- initial
  processed_pages <- 0L
  repeat {
    payload <- first_payload
    first_payload <- NULL
    if (is.null(payload)) {
      payload <- fec_read_page(session)
    }
    page <- payload$info$page
    checks <- fec_canaries(payload, expected_total)
    canary_callback(
      company = company,
      cycle = cycle,
      variant_set = variant_set,
      page = page,
      checks = checks
    )
    if (any(checks$passed == 0L)) {
      failed <- checks[passed == 0L, check_name]
      stop(
        "FEC canary failure for ", company, " cycle ", cycle,
        " page ", page, ": ", paste(failed, collapse = ", "),
        call. = FALSE
      )
    }
    page_callback(
      rows = payload$rows,
      page = page,
      records_total = records_total
    )
    processed_pages <- processed_pages + 1L
    if (processed_pages >= max_pages ||
        page + 1L >= payload$info$pages) {
      break
    }
    Sys.sleep(stats::runif(1L, min(sleep_range), max(sleep_range)))
    first_payload <- fec_click_next(session, page)
  }
  list(
    records_total = records_total,
    pages = initial$info$pages,
    retries = retry_count,
    truncated = processed_pages < initial$info$pages
  )
}

fec_walk_variant_set <- function(
  session,
  company,
  cycle,
  variants,
  variant_set,
  page_callback,
  canary_callback,
  query_field = "contributor_employer",
  query_filters = list(),
  timeout_seconds = 60,
  retries = 3L,
  sleep_range = c(1.5, 3.5),
  query_retries = 3L,
  max_pages = Inf
) {
  query_retries <- as.integer(query_retries)
  if (is.na(query_retries) || query_retries < 0L) {
    stop("query_retries must be a non-negative integer.", call. = FALSE)
  }
  last_error <- NULL
  for (attempt in seq_len(query_retries + 1L)) {
    active_session <- fec_active_session(session)
    result <- tryCatch(
      fec_walk_variant_set_once(
        session = active_session,
        company = company,
        cycle = cycle,
        variants = variants,
        variant_set = variant_set,
        page_callback = page_callback,
        canary_callback = canary_callback,
        query_field = query_field,
        query_filters = query_filters,
        timeout_seconds = timeout_seconds,
        retries = retries,
        sleep_range = sleep_range,
        max_pages = max_pages
      ),
      error = function(error) {
        last_error <<- error
        NULL
      }
    )
    if (!is.null(result)) {
      result$retries <- as.integer(result$retries) + attempt - 1L
      return(result)
    }
    transient <- fec_is_transient_chromote_error(last_error)
    if (!transient || attempt > query_retries) {
      stop(conditionMessage(last_error), call. = FALSE)
    }
    message(
      "Transient FEC browser failure for ", company, " cycle ", cycle,
      " (", variant_set, "); replaying the query, attempt ",
      attempt + 1L, " of ", query_retries + 1L, ": ",
      conditionMessage(last_error)
    )
    replacement <- fec_recover_session(active_session)
    fec_replace_session(session, replacement)
    fec_query_retry_sleep(attempt)
  }
  stop(conditionMessage(last_error), call. = FALSE)
}

fec_determinism_spot_check <- function(session) {
  session <- fec_active_session(session)
  first <- fec_read_page(session)
  second <- fec_read_page(session)
  ids <- function(payload) {
    sort(vapply(payload$rows, function(row) trim_text(row$sub_id %||% ""), character(1L)))
  }
  identical(ids(first), ids(second))
}
