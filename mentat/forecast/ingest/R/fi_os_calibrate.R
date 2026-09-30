# Calibration gate of the bulk route (FEEDS_SPEC 4.3). A bulk recipe is used for numbers only if, for every calibration code and
# every cycle 2012-2024 that the frozen page captures cover,
#   - the PAC total is within 0.5% of the page,
#   - each chamber's Democratic and Republican sums are within 1%,
#   - at least 98% of the page's recipients match by name key with amounts within $1.
# If no recipe passes, the run STOPS with the residual table and the bulk-route capabilities stay withheld. The page captures are
# the frozen baseline (never re-fetched, never overwritten); they are only read.

FI_CAL_TOL <- list(pac = 0.005, party = 0.01, match = 0.98, amount = 1)

.fi_rel <- function(a, b) if (is.na(a) || is.na(b)) NA_real_ else if (b == 0) (if (a == 0) 0 else Inf) else abs(a - b) / abs(b)

# Compare one code's bulk build with its page captures.
#   bulk_rec / page_rec  data.frame(cycle, chamber ("H"|"S"), name_key, party, amount)
#   bulk_tot / page_tot  data.frame(cycle, pac)
# -> data.frame(cycle, pac_rel_delta, dem_H, rep_H, dem_S, rep_S (relative deltas), match_H, match_S (match rates), pass)
fi_os_calibrate_compare <- function(bulk_rec, bulk_tot, page_rec, page_tot, tol = FI_CAL_TOL) {
  cycles <- sort(intersect(page_tot$cycle, bulk_tot$cycle))
  rows <- lapply(cycles, function(cy) {
    pac <- .fi_rel(bulk_tot$pac[bulk_tot$cycle == cy], page_tot$pac[page_tot$cycle == cy])
    one <- function(ch, p) {
      b <- bulk_rec[bulk_rec$cycle == cy & bulk_rec$chamber == ch, , drop = FALSE]
      g <- page_rec[page_rec$cycle == cy & page_rec$chamber == ch, , drop = FALSE]
      if (!nrow(g)) return(c(NA_real_, NA_real_))
      c(.fi_rel(sum(b$amount[b$party == p]), sum(g$amount[g$party == p])), NA_real_)
    }
    mr <- function(ch) {
      b <- bulk_rec[bulk_rec$cycle == cy & bulk_rec$chamber == ch, , drop = FALSE]
      g <- page_rec[page_rec$cycle == cy & page_rec$chamber == ch, , drop = FALSE]
      if (!nrow(g)) return(NA_real_)
      j <- match(g$name_key, b$name_key)
      mean(!is.na(j) & abs(b$amount[j] - g$amount) <= tol$amount, na.rm = FALSE)
    }
    d <- c(dem_H = one("H", "D")[1], rep_H = one("H", "R")[1], dem_S = one("S", "D")[1], rep_S = one("S", "R")[1])
    m <- c(match_H = mr("H"), match_S = mr("S"))
    ok <- !is.na(pac) && pac <= tol$pac && all(is.na(d) | d <= tol$party) && all(is.na(m) | m >= tol$match)
    data.frame(cycle = cy, pac_rel_delta = pac, t(d), t(m), pass = ok, stringsAsFactors = FALSE)
  })
  if (length(rows)) do.call(rbind, rows) else data.frame(cycle = integer(), pac_rel_delta = numeric(), pass = logical())
}

# Paths of the frozen page captures of a calibration code (under the LOO root of the refit's aliases).
fi_os_frozen_paths <- function(code, cycles = seq(2012L, 2024L, 2L), roots = rf_roots()) {
  base <- roots$LOO
  list(totals = file.path(base, "outputs/opensecrets_baseline/direct_sources", sprintf("%s_2024_totals.json", code)),
       candidates = lapply(stats::setNames(cycles, cycles), function(cy) c(H = file.path(base, "outputs/opensecrets_partisanship/direct_sources", sprintf("%s_%d_candidates_H.json", code, cy)),
                                                                           S = file.path(base, "outputs/opensecrets_partisanship/direct_sources", sprintf("%s_%d_candidates_S.json", code, cy)))))
}

# Page-side data of a code: totals (cycle, pac) and recipients (cycle, chamber, name_key, party, amount; empty for a code with no
# recipient captures, e.g. F09).
fi_os_frozen_page_data <- function(code, cycles = seq(2012L, 2024L, 2L), roots = rf_roots()) {
  p <- fi_os_frozen_paths(code, cycles, roots)
  tot <- NULL
  if (file.exists(p$totals)) { t <- rf_os_totals(p$totals); tot <- data.frame(cycle = t$cycle_end, pac = t$pac_nominal, stringsAsFactors = FALSE) }
  recs <- list()
  for (cy in cycles) for (ch in c("H", "S")) {
    f <- p$candidates[[as.character(cy)]][[ch]]
    if (!file.exists(f)) next
    x <- rf_os_candidates(f, ch)
    recs[[length(recs) + 1L]] <- data.frame(cycle = cy, chamber = ch, name_key = x$name_key, party = x$party, amount = x$amount, stringsAsFactors = FALSE)
  }
  list(totals = tot, recipients = if (length(recs)) do.call(rbind, recs) else NULL)
}

# Run the gate. `recipes` are the registry's bulk recipes in order of preference; the first that passes everywhere is accepted.
# -> list(accepted (recipe version or NULL), table (recipe, code, cycle, deltas, pass), passed, max_delta)
fi_os_calibrate <- function(dir, feeds, cycles = seq(2012L, 2024L, 2L), roots = rf_roots(), recipes = feeds$bulk_recipes, tol = FI_CAL_TOL, build = fi_os_bulk_build) {
  codes <- unlist(feeds$industries[[1]]$opensecrets$calibration_codes)
  if (!length(codes)) stop("fi_os_calibrate: no calibration_codes in the feeds registry", call. = FALSE)
  pages <- lapply(stats::setNames(codes, codes), fi_os_frozen_page_data, cycles = cycles, roots = roots)
  table <- list(); accepted <- NULL
  for (rc in recipes) {
    ok_all <- TRUE
    for (cd in codes) {
      pg <- pages[[cd]]
      if (is.null(pg$totals)) next
      cyc <- intersect(cycles, pg$totals$cycle)
      b <- build(dir, cd, rc, cyc, industry_id = cd)
      bt <- if (is.null(b$totals)) data.frame(cycle = integer(), pac = numeric()) else data.frame(cycle = b$totals$cycle, pac = b$totals$pacs)
      br <- if (is.null(b$recipients)) data.frame(cycle = integer(), chamber = character(), name_key = character(), party = character(), amount = numeric()) else
        b$recipients[b$recipients$chamber %in% c("H", "S"), c("cycle", "chamber", "name_key", "party", "amount")]
      cmp <- fi_os_calibrate_compare(br, bt, if (is.null(pg$recipients)) br[0, ] else pg$recipients, pg$totals, tol)
      if (nrow(cmp)) table[[length(table) + 1L]] <- cbind(data.frame(recipe = rc$version, code = cd, stringsAsFactors = FALSE), cmp)
      ok_all <- ok_all && nrow(cmp) > 0L && all(cmp$pass)
    }
    if (ok_all) { accepted <- rc$version; break }
  }
  tb <- if (length(table)) do.call(rbind, table) else NULL
  num <- if (!is.null(tb)) unlist(tb[, intersect(c("pac_rel_delta", "dem_H", "rep_H", "dem_S", "rep_S"), names(tb))]) else numeric()
  list(accepted = accepted, table = tb, passed = !is.null(accepted), max_delta = if (length(num) && any(is.finite(num))) max(num[is.finite(num)]) else NA_real_)
}
