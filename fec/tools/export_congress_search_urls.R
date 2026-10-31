# Export Paul's original Congress.gov member-search design to JSON, verbatim.
#
# Reads (never writes) Draft Systems\congress_search_urls.R (the 17 *_url_parts
# vectors, the "link repository") and the URL helpers of congress_member_scraper.R.
# Only the selected top-level assignments are evaluated, so no scrape runs.
#
#   Rscript fec/tools/export_congress_search_urls.R "<Draft Systems dir>" <sections.json> [<fixture.json>]
#
# sections.json  -> fec/collect/congress_member_search_sections.json (the parts, unchanged)
# fixture.json   -> R-built URLs / encodings / decay weights the node tests compare byte-for-byte.
args <- commandArgs(trailingOnly = TRUE)
src_dir <- args[1]; out_sections <- args[2]; out_fixture <- if (length(args) >= 3) args[3] else NA

env <- new.env()
sys.source(file.path(src_dir, "congress_search_urls.R"), envir = env)
wanted <- c("SECTION_REGISTRY", "assemble_url_template", "ROLES", "SPONSOR_FIELD_TOKEN",
            "apply_role", "build_member_url", "raw_url_parts", "raw_url_template",
            "NEWEST_CONGRESS", "DECAY_PER_CONGRESS", "congress_decay_weight",
            "construct_display_name")
for (e in parse(file.path(src_dir, "congress_member_scraper.R"))) {
  if (is.call(e) && identical(e[[1]], as.name("<-")) && is.name(e[[2]]) &&
      as.character(e[[2]]) %in% wanted) eval(e, env)
}

sections <- lapply(env$SECTION_REGISTRY, function(s) list(key = s$key, label = s$label, parts = s$parts))
# D-359 (Paul 2026-10-27, "Fix it"): cdfi_fund lacked its closing %5D and matched the member with
# "contains"; correct only that section (sponsor "phrase" like the other 16, plus the closing %5D).
for (i in seq_along(sections)) if (sections[[i]]$key == "cdfi_fund") {
  n <- length(sections[[i]]$parts)
  sections[[i]]$parts[n] <- sub("%22operator%22%3A%22contains%22", "%22operator%22%3A%22phrase%22",
                                sections[[i]]$parts[n], fixed = TRUE)
  sections[[i]]$parts <- c(sections[[i]]$parts, "%5D")
}
# D-360 (Paul 2026-10-27): revert the 06-25 edit of congress_search_urls.R; keyword conditions search
# `metadata` (as in the 06-24 baseline run), not `title`. 145 conditions; nothing else changes.
for (i in seq_along(sections)) sections[[i]]$parts <- gsub(
  "%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22",
  "%22field%22%3A%22metadata%22%2C%22operator%22%3A%22containsAll%22", sections[[i]]$parts, fixed = TRUE)
jsonlite::write_json(list(
  schema = "congress-member-search-sections-v1",
  source = "Draft Systems/congress_search_urls.R (SECTION_REGISTRY order from congress_member_scraper.R)",
  roles = env$ROLES,
  sponsor_field_token = env$SPONSOR_FIELD_TOKEN,
  sections = sections
), out_sections, auto_unbox = TRUE, pretty = TRUE)

if (!is.na(out_fixture)) {
  roster <- readRDS(file.path(src_dir, "roster_119_names.rds"))
  members <- c("Ann Wagner", "French Hill", "Andy Barr")
  urls <- list()
  for (s in env$SECTION_REGISTRY) {
    base <- env$assemble_url_template(s$parts)
    for (role in env$ROLES) {
      tmpl <- env$apply_role(base, role)
      for (m in members) for (pg in c(1, 2)) {
        u <- env$build_member_url(m, pg, 250, template = tmpl)
        # Full URL for the first section; sha256 for every URL (equally exact, 1/50 the size).
        urls[[length(urls) + 1]] <- list(section = s$key, role = role, member = m, page = pg,
                                         sha256 = digest::digest(enc2utf8(u), algo = "sha256", serialize = FALSE),
                                         url = if (s$key == env$SECTION_REGISTRY[[1]]$key) u else NULL)
      }
    }
  }
  # Encoded member segment only: build_member_url on the bare placeholder template.
  enc <- lapply(c(roster, "Nydia M. Velázquez", "Tom O'Halleran", "Jesús \"Chuy\" García"),
                function(m) list(member = m, encoded = env$build_member_url(m, 1, 250, template = "__MEMBER__")))
  names_cases <- list(
    list("James P. McGovern", "James", "McGovern"), list("Earl L. \"Buddy\" Carter", "Earl", "Carter"),
    list("Robert C. \"Bobby\" Scott", "Robert", "Scott"), list("Bernard Sanders", "Bernard", "Sanders"),
    list("Charles E. Schumer", "Charles", "Schumer"), list(NA, "Andy", "Barr"),
    list("J. French Hill", "French", "Hill"), list("Raja Krishnamoorthi", "Raja", "Krishnamoorthi"),
    list("Donald S. Beyer Jr.", "Donald", "Beyer"), list("María Elvira Salazar", "María", "Salazar"),
    list("Debbie Wasserman Schultz", "Debbie", "Wasserman Schultz"))
  display <- lapply(names_cases, function(x) list(full_name = x[[1]], first = x[[2]], last = x[[3]],
                                                  display = env$construct_display_name(x[[1]], x[[2]], x[[3]])))
  jsonlite::write_json(list(
    roster_119_names = roster,
    urls = urls, encodings = enc, display_names = display,
    decay = lapply(115:119, function(c) list(congress = c, weight = env$congress_decay_weight(c)))
  ), out_fixture, auto_unbox = TRUE, pretty = TRUE, digits = NA, na = "null")
}
