# Package loading without network installs. clubSandwich exists on this machine only inside a dated Codex work folder
# (RLIBX); rf_setup_rlib() copies it (and sandwich, for a version lock) once into the pipeline-owned library
# <RUNTIME>\Rlib, outside git, and writes registry/rlib_manifest.json with the sha256 of each package's identifying
# files. rf_load_packages() puts that library first on .libPaths(), loads every required package, checks its version
# against the pins of registry/models.json, and refuses to fall back silently when clubSandwich is missing.

RF_VENDORED <- c("clubSandwich", "sandwich")

rf_rlib_manifest_path <- function() file.path(rf_home(), "registry", "rlib_manifest.json")

# sha256 of the files that identify an installed package build (relative paths as names).
rf_rlib_hash_tree <- function(pkg_dir) {
  rdb <- list.files(file.path(pkg_dir, "R"), pattern = "\\.(rdb|rdx)$")
  rel <- c("DESCRIPTION", "NAMESPACE", "Meta/package.rds", if (length(rdb)) file.path("R", rdb))
  paths <- file.path(pkg_dir, rel)
  ok <- file.exists(paths)
  out <- vapply(paths[ok], rf_sha256, "")
  stats::setNames(unname(out), rel[ok])
}

# Copy the vendored packages from `source` into `target` once. An existing copy is never overwritten: it must match
# the manifest (created here if there is none yet). Returns the verification table.
rf_setup_rlib <- function(source = rf_roots()$RLIBX, target = rf_rlib_dir(), packages = RF_VENDORED,
                          manifest_path = rf_rlib_manifest_path()) {
  dir.create(target, recursive = TRUE, showWarnings = FALSE)
  for (p in packages) {
    src <- file.path(source, p)
    dst <- file.path(target, p)
    if (!dir.exists(src) && !dir.exists(dst)) stop("rf_setup_rlib: ", p, " not found in ", source, call. = FALSE)
    if (!dir.exists(dst)) {
      ok <- file.copy(src, target, recursive = TRUE, copy.mode = FALSE)
      if (!all(ok)) stop("rf_setup_rlib: copying ", p, " failed", call. = FALSE)
    }
  }
  if (!file.exists(manifest_path)) {
    man <- lapply(stats::setNames(packages, packages), function(p) {
      d <- read.dcf(file.path(target, p, "DESCRIPTION"), c("Version", "Built"))
      list(version = unname(d[1, "Version"]), built = unname(d[1, "Built"]), files = as.list(rf_rlib_hash_tree(file.path(target, p))))
    })
    rf_write_json_atomic(list(schema_version = 1L, note = "sha256 of the vendored package files; RUNTIME/Rlib is outside git",
                              packages = man), manifest_path)
  }
  rf_verify_rlib(target, manifest_path)
}

rf_verify_rlib <- function(target = rf_rlib_dir(), manifest_path = rf_rlib_manifest_path()) {
  man <- jsonlite::fromJSON(manifest_path, simplifyVector = FALSE)$packages
  rows <- list()
  for (p in names(man)) {
    have <- if (dir.exists(file.path(target, p))) rf_rlib_hash_tree(file.path(target, p)) else character()
    for (f in names(man[[p]]$files)) {
      exp <- man[[p]]$files[[f]]
      act <- if (f %in% names(have)) unname(have[[f]]) else NA_character_
      rows[[length(rows) + 1L]] <- data.frame(package = p, file = f, expected = exp, actual = act, ok = identical(act, exp),
                                              stringsAsFactors = FALSE)
    }
  }
  do.call(rbind, rows)
}

# Prepend the vendored library, load each package, compare versions with the pins. Returns
# data.frame(package, version, pinned, ok, lib). Fails (stop) when a vendored package is missing or a pin differs.
rf_load_packages <- function(required = c("jsonlite", "readxl", "sandwich", "clubSandwich"), pins = NULL) {
  rlib <- rf_rlib_dir()
  if (dir.exists(rlib)) .libPaths(unique(c(rlib, .libPaths())))
  if (getRversion() < "4.6.0") stop("rf_load_packages: R >= 4.6.0 is required (found ", as.character(getRversion()), ")", call. = FALSE)
  pins <- pins %||% rf_read_json(file.path(rf_home(), "registry", "models.json"))$packages
  rows <- list()
  for (p in required) {
    loaded <- suppressWarnings(requireNamespace(p, quietly = TRUE))
    if (!loaded) stop("rf_load_packages: required package ", p, " is unavailable", call. = FALSE)
    v <- utils::packageDescription(p)$Version   # the DESCRIPTION text ("3.1-3"), not the normalised "3.1.3"
    pin <- pins[[p]] %||% NA_character_
    ok <- is.na(pin) || identical(v, pin)
    rows[[length(rows) + 1L]] <- data.frame(package = p, version = v, pinned = pin, ok = ok,
                                            lib = dirname(find.package(p)), stringsAsFactors = FALSE)
    if (!ok) stop("rf_load_packages: ", p, " is ", v, " but the registry pins ", pin, call. = FALSE)
    if (p %in% RF_VENDORED && dir.exists(rlib) && !identical(normalizePath(dirname(find.package(p)), winslash = "/"), rlib)) {
      stop("rf_load_packages: ", p, " loaded from ", dirname(find.package(p)), " not from the vendored library ", rlib, call. = FALSE)
    }
  }
  do.call(rbind, rows)
}
