# R_LIBS_USER is the supported configuration; this fallback covers stripped environments.
if (!requireNamespace("data.table", quietly = TRUE)) {
  .libPaths(c(
    "C:/Users/pgoff/AppData/Local/R/win-library/4.6",
    .libPaths()
  ))
}

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0L || (length(x) == 1L && is.na(x))) y else x
}

require_package <- function(package) {
  if (!requireNamespace(package, quietly = TRUE)) {
    stop("Required installed package is unavailable: ", package, call. = FALSE)
  }
  invisible(TRUE)
}

mentat_default_data_root <- function() {
  configured <- trimws(Sys.getenv("MENTAT_DATA_ROOT", unset = ""))
  if (nzchar(configured)) {
    return(normalizePath(configured, winslash = "/", mustWork = FALSE))
  }
  local_app_data <- trimws(Sys.getenv("LOCALAPPDATA", unset = ""))
  if (!nzchar(local_app_data)) {
    stop(
      "LOCALAPPDATA is empty; set MENTAT_DATA_ROOT to a writable local directory.",
      call. = FALSE
    )
  }
  normalizePath(
    file.path(local_app_data, "Mentat"),
    winslash = "/",
    mustWork = FALSE
  )
}

mentat_paths <- function(data_root = mentat_default_data_root()) {
  root <- normalizePath(data_root, winslash = "/", mustWork = FALSE)
  list(
    root = root,
    database = file.path(root, "mentat.db"),
    reports = file.path(root, "reports"),
    rosters_summary = file.path(root, "rosters_summary.txt")
  )
}

mentat_bulk_dir <- function(data_root = mentat_default_data_root()) {
  configured <- trimws(Sys.getenv("MENTAT_BULK_DIR", unset = ""))
  root <- if (nzchar(configured)) configured else file.path(data_root, "bulk")
  normalizePath(root, winslash = "/", mustWork = FALSE)
}

mentat_bootstrap_dirs <- function(data_root = mentat_default_data_root()) {
  paths <- mentat_paths(data_root)
  for (directory in c(paths$root, paths$reports)) {
    if (!dir.exists(directory) &&
        !dir.create(directory, recursive = TRUE, showWarnings = FALSE)) {
      stop("Could not create directory: ", directory, call. = FALSE)
    }
  }
  paths
}

mentat_project_root <- function(start = getwd()) {
  current <- normalizePath(start, winslash = "/", mustWork = TRUE)
  repeat {
    if (file.exists(file.path(current, "CODEX_TASK.md")) &&
        dir.exists(file.path(current, "R"))) {
      return(current)
    }
    nested <- file.path(current, "mentat")
    if (file.exists(file.path(nested, "CODEX_TASK.md")) &&
        dir.exists(file.path(nested, "R"))) {
      return(normalizePath(nested, winslash = "/", mustWork = TRUE))
    }
    parent <- dirname(current)
    if (identical(parent, current)) {
      stop("Could not locate the mentat project directory.", call. = FALSE)
    }
    current <- parent
  }
}

mentat_input_dir <- function(project_root = mentat_project_root()) {
  normalizePath(
    file.path(project_root, "inputs"),
    winslash = "/",
    mustWork = TRUE
  )
}

db_connect <- function(data_root = mentat_default_data_root()) {
  require_package("DBI")
  require_package("RSQLite")
  paths <- mentat_bootstrap_dirs(data_root)
  connection <- DBI::dbConnect(RSQLite::SQLite(), dbname = paths$database)
  ok <- FALSE
  on.exit(if (!ok) DBI::dbDisconnect(connection), add = TRUE)
  DBI::dbExecute(connection, "PRAGMA busy_timeout = 60000")
  journal_mode <- DBI::dbGetQuery(connection, "PRAGMA journal_mode = WAL")[[1L]]
  if (!identical(tolower(as.character(journal_mode)), "wal")) {
    stop("SQLite refused WAL mode for: ", paths$database, call. = FALSE)
  }
  DBI::dbExecute(connection, "PRAGMA synchronous = NORMAL")
  DBI::dbExecute(connection, "PRAGMA foreign_keys = ON")
  ok <- TRUE
  connection
}

atomic_replace <- function(temporary, target) {
  if (!file.exists(temporary)) {
    stop("Atomic-write temporary file is missing: ", temporary, call. = FALSE)
  }
  target_dir <- dirname(target)
  if (!dir.exists(target_dir) &&
      !dir.create(target_dir, recursive = TRUE, showWarnings = FALSE)) {
    stop("Could not create output directory: ", target_dir, call. = FALSE)
  }
  backup <- NULL
  if (file.exists(target)) {
    backup <- tempfile(
      pattern = paste0(".", basename(target), ".backup-"),
      tmpdir = target_dir
    )
    if (!file.rename(target, backup)) {
      stop("Could not stage existing output: ", target, call. = FALSE)
    }
  }
  installed <- file.rename(temporary, target)
  if (!installed) {
    if (!is.null(backup) && file.exists(backup)) {
      file.rename(backup, target)
    }
    stop("Could not atomically install output: ", target, call. = FALSE)
  }
  if (!is.null(backup) && file.exists(backup)) {
    unlink(backup, force = TRUE)
  }
  invisible(target)
}

atomic_write_lines <- function(lines, target) {
  directory <- dirname(target)
  if (!dir.exists(directory) &&
      !dir.create(directory, recursive = TRUE, showWarnings = FALSE)) {
    stop("Could not create output directory: ", directory, call. = FALSE)
  }
  temporary <- tempfile(
    pattern = paste0(".", basename(target), "."),
    tmpdir = directory
  )
  on.exit(if (file.exists(temporary)) unlink(temporary, force = TRUE), add = TRUE)
  writeLines(enc2utf8(lines), temporary, useBytes = TRUE)
  atomic_replace(temporary, target)
}

atomic_write_csv <- function(data, target) {
  require_package("data.table")
  data <- as.data.frame(data, stringsAsFactors = FALSE)
  for (column in names(data)) {
    if (is.character(data[[column]])) {
      data[[column]] <- enc2utf8(data[[column]])
    }
  }
  directory <- dirname(target)
  if (!dir.exists(directory) &&
      !dir.create(directory, recursive = TRUE, showWarnings = FALSE)) {
    stop("Could not create output directory: ", directory, call. = FALSE)
  }
  temporary <- tempfile(
    pattern = paste0(".", basename(target), "."),
    tmpdir = directory
  )
  on.exit(if (file.exists(temporary)) unlink(temporary, force = TRUE), add = TRUE)
  data.table::fwrite(
    data,
    file = temporary,
    quote = TRUE,
    na = "",
    bom = TRUE
  )
  atomic_replace(temporary, target)
}

atomic_write_xlsx <- function(sheets, target, col_names = TRUE) {
  require_package("writexl")
  directory <- dirname(target)
  if (!dir.exists(directory) &&
      !dir.create(directory, recursive = TRUE, showWarnings = FALSE)) {
    stop("Could not create output directory: ", directory, call. = FALSE)
  }
  temporary <- tempfile(
    pattern = paste0(".", basename(target), "."),
    tmpdir = directory,
    fileext = ".xlsx"
  )
  on.exit(if (file.exists(temporary)) unlink(temporary, force = TRUE), add = TRUE)
  writexl::write_xlsx(sheets, path = temporary, col_names = col_names)
  atomic_replace(temporary, target)
}
