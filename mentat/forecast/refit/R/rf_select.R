# Slope-rule auto-pick (Paul's ruling of 2026-09-30, superseding the DL-everywhere default of SPEC 9 item 4):
#
#   For each term (PAC, control House, control Senate, lobbying) run the no-leakage backtests for R0 pooled / R1 own / R2 DL blend in
#   BOTH designs (leave-one-election-out and chronological, fold-restandardized growth, the calculator path with that term's anchor).
#   Choose the rule with the lowest MAE in both designs. If the designs disagree, use R2. Record the full comparison table and the
#   choice. When R2 resolves to the pooled slope (tau2 = 0) the pooled rule R0 is reported.
#
# Lobbying has a single rolling-origin design, so its one design decides alone.
# Library code: not wired into the v1 parity bundle.
#
# Interpretation notes (stated, not silent):
#   * "lowest MAE in both designs": ties within RF$RULE_TIE_TOL are broken toward the simpler rule (R0, then R2, then R1).
#   * min_gain (default RF$RULE_MIN_GAIN = 0, the literal rule): when > 0 a design only has a clear winner if the winner beats the
#     best OTHER rule by that relative margin; a design without a clear winner counts as disagreeing, which resolves to R2.
#   * "R2 resolves to the pooled slope" is judged on the full-sample fit (tau2 = 0, so every blended slope equals the pooled one),
#     or on an exact MAE tie of R0 and R2 in every design.

# The choice from a comparison table (design, rule, MAE). Pure function, unit-tested.
# -> list(choice, winner_by_design, reason)
rf_choose_rule <- function(table, designs = unique(table$design), min_gain = RF$RULE_MIN_GAIN, tol = RF$RULE_TIE_TOL) {
  cand <- c("R0", "R2", "R1")                       # simplest first: used to break exact ties
  winners <- stats::setNames(rep(NA_character_, length(designs)), designs)
  for (ds in designs) {
    t <- table[table$design == ds & table$rule %in% cand, ]
    mae <- stats::setNames(t$MAE, t$rule)[cand]
    best <- min(mae, na.rm = TRUE)
    tied <- cand[!is.na(mae) & mae <= best + tol]
    w <- tied[1]
    if (min_gain > 0) {
      others <- mae[setdiff(cand, tied)]
      others <- others[!is.na(others)]
      if (length(others) && (min(others) - best) / min(others) < min_gain) w <- NA_character_
    }
    winners[[ds]] <- w
  }
  if (!anyNA(winners) && length(unique(winners)) == 1L) {
    reason <- if (length(designs) > 1L) sprintf("%s has the lowest MAE in both designs (%s)", winners[[1]], paste(designs, collapse = ", "))
              else sprintf("%s has the lowest MAE in the single design (%s)", winners[[1]], designs)
    return(list(choice = winners[[1]], winner_by_design = winners, reason = reason))
  }
  list(choice = "R2", winner_by_design = winners,
       reason = sprintf("designs disagree or have no clear winner (%s): the DL blend R2 is used", paste(sprintf("%s -> %s", designs, ifelse(is.na(winners), "none", winners)), collapse = "; ")))
}

# Backtest one spec in its designs and pick the rule. `path` = the calculator path of the term's anchor ("prevchg" for PAC, "calc"
# for control and lobbying). -> list(term, base, path, designs, table, winner_by_design, choice, reported_rule, tau2_full_sample, reason, min_gain)
rf_select_rule <- function(spec, path = spec$calc_path, designs = NULL, min_gain = RF$RULE_MIN_GAIN, tol = RF$RULE_TIE_TOL) {
  designs <- designs %||% if (spec$kind == "lobby") "rolling" else c("loeo", "chrono")
  tabs <- lapply(designs, function(ds) {
    m <- rf_backtest_metrics(rf_backtest(spec, spec$d, ds))
    m <- m[m$path == path & m$rule %in% c(RF$RULES, "naive_prev"), c("term", "base", "design", "path", "rule", "n", "folds", "targets", "MAE", "RMSE", "units", "beats_naive")]
    m
  })
  tab <- do.call(rbind, tabs)
  rownames(tab) <- NULL
  ch <- rf_choose_rule(tab, designs, min_gain, tol)
  pp <- rf_partial_pool(spec, spec$d)
  reported <- ch$choice
  resolved <- FALSE
  if (ch$choice == "R2") {
    tie_all <- all(vapply(designs, function(ds) abs(tab$MAE[tab$design == ds & tab$rule == "R0"] - tab$MAE[tab$design == ds & tab$rule == "R2"]) <= tol, logical(1)))
    if (identical(pp$tau2, 0) || tie_all) { reported <- "R0"; resolved <- TRUE }
  }
  list(term = spec$id, base = spec$base, path = path, designs = designs, table = tab, winner_by_design = ch$winner_by_design, choice = ch$choice,
       reported_rule = reported, resolved_to_pooled = resolved, tau2_full_sample = pp$tau2, reason = ch$reason, min_gain = min_gain)
}

# Selection for every calculator term of a spec list (the four terms of the ruling) -> named list of rf_select_rule() results.
rf_select_rules <- function(specs, min_gain = RF$RULE_MIN_GAIN) {
  keys <- c(pac = "pac", control_House = "control_House.selected", control_Senate = "control_Senate.selected", lobby = "lobby")
  out <- lapply(keys, function(k) rf_select_rule(specs[[k]], min_gain = min_gain))
  names(out) <- names(keys)
  out
}

# One long comparison table (every term, design, rule) for the receipt and the review packet.
rf_selection_table <- function(selections) {
  do.call(rbind, lapply(names(selections), function(nm) {
    s <- selections[[nm]]
    t <- s$table
    t$choice <- s$choice; t$reported_rule <- s$reported_rule; t$selection_term <- nm
    t
  }))
}
