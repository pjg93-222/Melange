# A hand-written JSON Schema validator for the keyword subset of the shared contract (mentat/forecast/contracts, brain DE-021):
#   $schema $id $defs $ref(#/$defs/x only) title description type(string|list) enum const properties required additionalProperties(bool|schema)
#   propertyNames(pattern only) minProperties items minItems minimum maximum exclusiveMinimum minLength pattern.
# It mirrors contracts/contract.py::_check (the reference implementation): `number` and `integer` reject booleans and non-finite values,
# an integral double is an integer, `const` compares type and value, and a keyword outside the subset is an error, not silently ignored.
# The schema, the example and the negative controls live in mentat/forecast/contracts and are read-only for this pipeline.

RF_SCHEMA_KEYWORDS <- c("$schema", "$id", "$defs", "$ref", "title", "description", "type", "enum", "const", "properties", "required",
                        "additionalProperties", "propertyNames", "minProperties", "items", "minItems", "minimum", "maximum",
                        "exclusiveMinimum", "minLength", "pattern")

rf_contracts_dir <- function() normalizePath(file.path(rf_home(), "..", "contracts"), winslash = "/", mustWork = FALSE)
rf_schema_default_path <- function() file.path(rf_contracts_dir(), "giving-models-v2.schema.json")

.rf_is_type <- function(x, type) {
  switch(type,
    object = is.list(x) && !is.null(names(x)),                          # JSON {} parses to a NAMED empty list, [] to an unnamed one
    array = is.list(x) && is.null(names(x)),
    string = is.character(x) && length(x) == 1L && !is.na(x),
    number = is.numeric(x) && length(x) == 1L && is.finite(x),
    integer = is.numeric(x) && length(x) == 1L && is.finite(x) && x == round(x),
    boolean = is.logical(x) && length(x) == 1L && !is.na(x),
    null = is.null(x),
    FALSE)
}

.rf_type_name <- function(x) if (is.null(x)) "null" else if (is.list(x)) (if (is.null(names(x))) "array" else "object") else paste0(class(x)[1], "[", length(x), "]")

.rf_const_equal <- function(x, const) {
  if (is.character(const)) return(is.character(x) && length(x) == 1L && identical(as.character(x), const))
  if (is.logical(const)) return(is.logical(x) && length(x) == 1L && !is.na(x) && x == const)
  if (is.numeric(const)) return(is.numeric(x) && length(x) == 1L && is.finite(x) && x == const)
  FALSE
}

# Problems of a parsed JSON value against a schema node (character(0) = valid).
rf_schema_check <- function(x, node, root, path = "$") {
  if (!is.null(node[["$ref"]])) {
    ref <- node[["$ref"]]
    if (!startsWith(ref, "#/$defs/")) stop("Only local $defs references are supported: ", ref, call. = FALSE)
    return(rf_schema_check(x, root[["$defs"]][[sub("^#/\\$defs/", "", ref)]], root, path))
  }
  unknown <- setdiff(names(node), RF_SCHEMA_KEYWORDS)
  if (length(unknown)) stop("Schema keyword outside the supported subset at ", path, ": ", paste(sort(unknown), collapse = ", "), call. = FALSE)
  out <- character()
  if (!is.null(node$type)) {
    wanted <- unlist(node$type)
    if (is.numeric(x) && length(x) == 1L && !is.finite(x)) return(paste0(path, ": non-finite number"))
    if (!any(vapply(wanted, function(t) .rf_is_type(x, t), logical(1)))) return(paste0(path, ": expected ", paste(wanted, collapse = "/"), ", got ", .rf_type_name(x)))
  }
  if ("const" %in% names(node) && !.rf_const_equal(x, node$const)) out <- c(out, paste0(path, ": must equal ", format(node$const)))
  if (!is.null(node$enum) && !any(vapply(node$enum, function(e) .rf_const_equal(x, e), logical(1)))) out <- c(out, paste0(path, ": must be one of ", paste(unlist(node$enum), collapse = ", ")))
  if (is.character(x) && length(x) == 1L) {
    if (!is.null(node$pattern) && !grepl(node$pattern, x, perl = TRUE)) out <- c(out, paste0(path, ": does not match ", node$pattern))
    if (!is.null(node$minLength) && nchar(x) < node$minLength) out <- c(out, paste0(path, ": shorter than ", node$minLength))
  }
  if (is.numeric(x) && length(x) == 1L && is.finite(x)) {
    if (!is.null(node$minimum) && x < node$minimum) out <- c(out, paste0(path, ": below ", node$minimum))
    if (!is.null(node$maximum) && x > node$maximum) out <- c(out, paste0(path, ": above ", node$maximum))
    if (!is.null(node$exclusiveMinimum) && x <= node$exclusiveMinimum) out <- c(out, paste0(path, ": not above ", node$exclusiveMinimum))
  }
  if (is.list(x) && !is.null(names(x))) {                                  # object
    for (k in unlist(node$required)) if (!(k %in% names(x))) out <- c(out, paste0(path, ": missing required \"", k, "\""))
    if (!is.null(node$minProperties) && length(x) < node$minProperties) out <- c(out, paste0(path, ": fewer than ", node$minProperties, " entries"))
    names_pat <- node$propertyNames$pattern
    props <- node$properties
    extra <- if ("additionalProperties" %in% names(node)) node$additionalProperties else TRUE
    for (k in names(x)) {
      child <- paste0(path, ".", k)
      if (!is.null(names_pat) && !grepl(names_pat, k, perl = TRUE)) out <- c(out, paste0(child, ": key does not match ", names_pat))
      if (!is.null(props[[k]])) out <- c(out, rf_schema_check(x[[k]], props[[k]], root, child))
      else if (identical(extra, FALSE)) out <- c(out, paste0(child, ": unexpected property"))
      else if (is.list(extra)) out <- c(out, rf_schema_check(x[[k]], extra, root, child))
    }
  } else if (is.list(x)) {
    if (!is.null(node$minItems) && length(x) < node$minItems) out <- c(out, paste0(path, ": fewer than ", node$minItems, " items"))
    if (!is.null(node$items)) for (i in seq_along(x)) out <- c(out, rf_schema_check(x[[i]], node$items, root, paste0(path, "[", i - 1L, "]")))
  }
  out
}

# The parsed (canonical) form of an R bundle: what a reader of its JSON would see. NaN / Inf are reported before the round trip.
rf_canonical_json <- function(b) jsonlite::fromJSON(as.character(jsonlite::toJSON(b, auto_unbox = TRUE, digits = NA, null = "null", na = "null")), simplifyVector = FALSE)

# Validate an already parsed JSON value (no round trip: NaN / Inf survive and are rejected).
rf_validate_parsed <- function(x, schema_path = rf_schema_default_path()) {
  schema <- jsonlite::fromJSON(schema_path, simplifyVector = FALSE)
  rf_schema_check(x, schema, schema)
}

# Validate a bundle (in-memory list or parsed JSON) against the contract schema. -> character() of problems; empty = valid.
rf_validate_bundle <- function(b, schema_path = rf_schema_default_path()) {
  bad <- rf_nonfinite_paths(b)
  if (length(bad)) return(paste0(bad, ": non-finite number"))
  rf_validate_parsed(rf_canonical_json(b), schema_path)
}

# ---- the shared negative controls ------------------------------------------------------------------------------------------------------

rf_negative_controls <- function(path = file.path(rf_contracts_dir(), "negative-controls.json")) jsonlite::fromJSON(path, simplifyVector = FALSE)$controls

# Apply one control (op delete | set) to a parsed document and return the mutated copy. {"$nonfinite": "NaN"} means R's NaN / Inf.
rf_apply_control <- function(doc, ctl) {
  path <- unlist(ctl$path)
  value <- ctl$value
  if (is.list(value) && !is.null(value[["$nonfinite"]])) {
    kind <- value[["$nonfinite"]]
    value <- if (kind %in% c("Infinity", "Inf")) Inf else if (identical(kind, "-Infinity")) -Inf else NaN
  }
  mutate <- function(x, p) {
    k <- p[1]
    if (length(p) == 1L) {
      if (ctl$op == "delete") x[[k]] <- NULL else if (is.null(value)) x[k] <- list(NULL) else x[[k]] <- value
    } else {
      x[[k]] <- mutate(x[[k]], p[-1])
    }
    x
  }
  mutate(doc, path)
}
