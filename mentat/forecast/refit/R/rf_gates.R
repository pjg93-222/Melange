# Gates G4-G9 of the refit (SPEC 3.13, as amended by the rulings of 2026-09-30) and the decision.
#   status PASS / WARN (report only) / HOLD (no publish, packet written) / FAIL (no publish, error).
#   G0 environment, G1 inputs, G2 parity and G3 panel validity come from rf_parity.R and are passed in.
#   G4 sample adequacy   per industry and model: >= 5 cycles (PAC, control) / >= 5 annual pairs (lobbying), pooled residual df >= 3,
#                        interaction df >= 2; an industry that fails a model is WITHHELD for it (WARN, reason stated), never silently.
#   G5 stability         no pooled focal slope and no existing industry's slope flips sign versus the published bundle; leave-one-out
#                        sign consistency >= 80% for every calculator focal term.                                            HOLD
#   G6 non-degradation   HARD backtest gate: no existing industry's calculator-path leave-one-election-out MAE may exceed the published
#                        bundle's on the common folds (new <= published + 1e-9).                                              HOLD
#   G7 bundle            schema-valid, every number finite, every calculator industry has a capability or a stated reason per model. FAIL
#   G8 consumer smoke    the v2-capable Python calculator loads the staged bundle (MENTAT_G8_CMD); HOLD until it exists.
#   G9 vs naive          a calculator path that does not beat last-cycle naive is a WARNING only.

RF_G5_MIN_SIGN <- 0.8
RF_G6_SLACK <- 1e-9

.rf_gate <- function(gate, status, detail) data.frame(gate = gate, status = status, detail = detail, stringsAsFactors = FALSE)

# ---- G4 --------------------------------------------------------------------------------------------------------------------------

# -> list(table = data.frame(industry, model, n, need, pooled_df, interaction_df, ok), withheld = list(industry = list(list(model, reason))), gate)
rf_gate_adequacy <- function(ctx, reg = ctx$reg, min_n = 5L, min_pooled_df = 3L, min_interaction_df = 2L) {
  rows <- list()
  counts <- list(pac = table(ctx$pac_panel$sector), control = table(ctx$share$control_House$sector), lobbying = NULL)
  lobc <- table(ctx$lobby$diffs$study_sector)
  pooled_df <- c(pac = stats::df.residual(ctx$fits$pac), control = min(stats::df.residual(ctx$fits$control_House), stats::df.residual(ctx$fits$control_Senate)), lobbying = stats::df.residual(ctx$fits$lobby))
  inter_df <- c(pac = NA_integer_, control = NA_integer_, lobbying = NA_integer_)
  specs <- rf_backtest_specs(ctx)
  inter_df["pac"] <- rf_partial_pool(specs$pac, specs$pac$d)$df_interaction
  inter_df["control"] <- min(rf_partial_pool(specs$control_House.selected, specs$control_House.selected$d)$df_interaction, rf_partial_pool(specs$control_Senate.selected, specs$control_Senate.selected$d)$df_interaction)
  inter_df["lobbying"] <- rf_partial_pool(specs$lobby, specs$lobby$d)$df_interaction
  for (id in names(reg$industries)) {
    i <- reg$industries[[id]]
    if (identical(i$status, "declined")) next
    for (m in c("pac", "control", "lobbying")) {
      if (!id %in% rf_capable(reg, m)) next
      n <- if (m == "lobbying") { ls <- i$lobbyview$study_sector; if (ls %in% names(lobc)) as.integer(lobc[[ls]]) else 0L } else { t <- counts[[m]]; if (id %in% names(t)) as.integer(t[[id]]) else 0L }
      ok <- n >= min_n && pooled_df[[m]] >= min_pooled_df && inter_df[[m]] >= min_interaction_df
      rows[[length(rows) + 1L]] <- data.frame(industry = id, model = m, n = n, need = min_n, pooled_df = unname(pooled_df[[m]]), interaction_df = unname(inter_df[[m]]), ok = ok, stringsAsFactors = FALSE)
    }
  }
  tab <- do.call(rbind, rows)
  bad <- tab[!tab$ok, ]
  withheld <- list()
  for (k in seq_len(nrow(bad))) {
    b <- bad[k, ]
    withheld[[b$industry]] <- c(withheld[[b$industry]], list(list(model = b$model,
      reason = sprintf("sample adequacy: %d %s (need %d), pooled residual df %d (need %d), interaction df %d (need %d)", b$n, if (b$model == "lobbying") "annual pairs" else "cycles",
                       b$need, b$pooled_df, min_pooled_df, b$interaction_df, min_interaction_df))))
  }
  list(table = tab, withheld = withheld,
       gate = .rf_gate("G4 sample adequacy", if (nrow(bad)) "WARN" else "PASS",
                       if (nrow(bad)) paste("withheld:", paste(sprintf("%s/%s", bad$industry, bad$model), collapse = ", ")) else sprintf("%d industry-model cells adequate", nrow(tab))))
}

# ---- G5 --------------------------------------------------------------------------------------------------------------------------

.rf_forecast_beta <- function(block) { k <- match("Forecast", unlist(block$terms)); if (is.na(k)) NA_real_ else unlist(block$beta)[k] }

# Signs of the published bundle's pooled focal slopes (v1 or v2): list(pac, control_House, control_Senate, lobby).
rf_published_signs <- function(published) {
  if (is.null(published)) return(NULL)
  list(pac = published$pac_model$beta, control_House = .rf_forecast_beta(published$share_models$control_House), control_Senate = .rf_forecast_beta(published$share_models$control_Senate),
       lobby = published$lobby_model$beta_million, pac_slopes = if (!is.null(published$pac_model$slopes)) vapply(published$pac_model$slopes, function(s) s$applied$beta, 0) else NULL)
}

# -> list(table, gate)
rf_gate_stability <- function(v, bundle, published = NULL, min_share = RF_G5_MIN_SIGN) {
  rows <- list()
  add <- function(check, ok, detail) rows[[length(rows) + 1L]] <<- data.frame(check = check, ok = ok, detail = detail, stringsAsFactors = FALSE)
  ps <- rf_published_signs(published)
  new <- list(pac = bundle$pac_model$beta, control_House = .rf_forecast_beta(bundle$share_models$control_House), control_Senate = .rf_forecast_beta(bundle$share_models$control_Senate),
              lobby = bundle$lobby_model$beta_million)
  if (!is.null(ps)) {
    for (nm in names(new)) add(paste("pooled slope sign:", nm), sign(new[[nm]]) == sign(ps[[nm]]), sprintf("new %.6g, published %.6g", new[[nm]], ps[[nm]]))
    add("lobbying log slope sign vs published dollar slope", sign(bundle$lobby_model$log_refit$beta) == sign(ps$lobby), sprintf("log slope %.6g, published dollar slope %.6g", bundle$lobby_model$log_refit$beta, ps$lobby))
    for (id in names(bundle$pac_model$slopes)) {
      ref <- if (!is.null(ps$pac_slopes) && id %in% names(ps$pac_slopes)) ps$pac_slopes[[id]] else ps$pac
      add(paste("existing industry slope sign: PAC", id), sign(bundle$pac_model$slopes[[id]]$applied$beta) == sign(ref),
          sprintf("new %.6g, published %s %.6g", bundle$pac_model$slopes[[id]]$applied$beta, if (!is.null(ps$pac_slopes) && id %in% names(ps$pac_slopes)) "own slope" else "pooled slope", ref))
    }
  }
  sc <- list(pac = v$sign$pac$loeo$share, control_House = v$sign$control_House$loeo$share, control_Senate = v$sign$control_Senate$loeo$share,
             lobby = v$sign$lobby$loeo$share, lobby_log = v$sign$lobby_log$loeo)
  for (nm in names(sc)) add(paste("leave-one-election-out sign consistency:", nm), sc[[nm]] >= min_share - 1e-12, sprintf("%.0f%% of folds keep the sign (need %.0f%%)", 100 * sc[[nm]], 100 * min_share))
  tab <- do.call(rbind, rows)
  bad <- tab[!tab$ok, ]
  list(table = tab, gate = .rf_gate("G5 stability", if (nrow(bad)) "HOLD" else "PASS", if (nrow(bad)) paste(sprintf("%s (%s)", bad$check, bad$detail), collapse = "; ") else sprintf("%d sign checks hold", nrow(tab))))
}

# ---- G6 --------------------------------------------------------------------------------------------------------------------------

# Per-industry leave-one-election-out MAE of a backtest cell: named numeric by industry (NA when the industry has no rows).
.rf_cell_mae <- function(bt, term, base, design, path, rule) {
  r <- bt[bt$term == term & bt$base == base & bt$design == design & bt$path == path & bt$rule == rule, ]
  if (!nrow(r)) return(numeric())
  cols <- grep("^MAE_", names(r), value = TRUE)
  stats::setNames(unlist(r[1, cols]), sub("^MAE_", "", cols))
}

# The currently published calculator's per-industry MAE. For v1 (no backtests in the bundle): the v1 calculator (pooled slope, same-phase
# anchor, calc path) on the same folds and scaling. For a v2 bundle with backtests: its recorded MAE_by_industry of the published rule/path.
rf_published_baseline <- function(v, published = NULL) {
  bt <- v$backtests
  pe <- published$pac_model$evidence$calculator_path_loeo_mae_by_industry
  if (!is.null(published) && !is.null(pe)) {                     # a v2 bundle records the MAE of the path it publishes
    g <- function(x) unlist(x %||% list())
    return(list(pac = g(pe), control_House = g(published$share_models$control_House$evidence$calculator_path_loeo_mae_by_industry),
                control_Senate = g(published$share_models$control_Senate$evidence$calculator_path_loeo_mae_by_industry),
                lobby = g(published$lobby_model$evidence$calculator_path_mae_by_industry), source = "published bundle (recorded calculator-path MAE)"))
  }
  list(pac = .rf_cell_mae(bt, "pac", "bundle", "loeo", "calc", "R0"), control_House = .rf_cell_mae(bt, "control_House", "selected", "loeo", "calc", "R0"),
       control_Senate = .rf_cell_mae(bt, "control_Senate", "selected", "loeo", "calc", "R0"), lobby = .rf_cell_mae(bt, "lobby", "bundle", "rolling", "calc", "R0"),
       source = "v1 calculator recomputed on the same folds (pooled slope, same-phase anchor, calc path)")
}

# -> list(table = data.frame(term, industry, new_MAE, published_MAE, ok), gate)
rf_gate_nondegradation <- function(v, published = NULL, existing = NULL, slack = RF_G6_SLACK) {
  ctx <- v$ctx
  base <- rf_published_baseline(v, published)
  bt <- v$backtests
  rule <- c(pac = v$selection$pac$reported_rule, control_House = v$selection$control_House$reported_rule, control_Senate = v$selection$control_Senate$reported_rule)
  new <- list(pac = .rf_cell_mae(bt, "pac", "bundle", "loeo", "prevchg", rule[["pac"]]),
              control_House = .rf_cell_mae(bt, "control_House", "selected", "loeo", "prevchg", rule[["control_House"]]),
              control_Senate = .rf_cell_mae(bt, "control_Senate", "selected", "loeo", "prevchg", rule[["control_Senate"]]),
              lobby = .rf_cell_mae(bt, "lobby", "log", "rolling", "calc", "R0"))
  existing <- existing %||% (if (!is.null(published)) names(published$industries) else names(ctx$reg$industries)[vapply(ctx$reg$industries, function(i) i$status == "fitted", logical(1))])
  study <- stats::setNames(vapply(ctx$reg$industries, function(i) i$lobbyview$study_sector %||% NA_character_, ""), names(ctx$reg$industries))
  rows <- list()
  for (term in names(new)) for (id in existing) {
    key <- if (term == "lobby") study[[id]] else id
    if (is.na(key) || !(key %in% names(new[[term]])) || !(key %in% names(base[[term]]))) next
    a <- new[[term]][[key]]; b <- base[[term]][[key]]
    if (is.na(a) || is.na(b)) next
    rows[[length(rows) + 1L]] <- data.frame(term = term, industry = id, new_MAE = a, published_MAE = b, ok = a <= b + slack, stringsAsFactors = FALSE)
  }
  tab <- do.call(rbind, rows)
  bad <- tab[!tab$ok, ]
  list(table = tab, baseline = base$source,
       gate = .rf_gate("G6 non-degradation", if (nrow(bad)) "HOLD" else "PASS",
                       if (nrow(bad)) paste(sprintf("%s / %s: new %.3f > published %.3f", bad$term, bad$industry, bad$new_MAE, bad$published_MAE), collapse = "; ")
                       else sprintf("%d existing industry-term cells no worse than the published calculator (%s)", nrow(tab), base$source)))
}

# ---- G7, G8, G9 ------------------------------------------------------------------------------------------------------------------

rf_gate_bundle <- function(bundle, reg, schema_path = rf_schema_default_path()) {
  problems <- rf_validate_bundle(bundle, schema_path)
  for (id in names(bundle$industries)) {
    if (!isTRUE(bundle$industries[[id]]$calculator)) next
    for (m in c("pac", "control", "lobbying")) {
      ok <- isTRUE(bundle$industries[[id]]$capabilities[[m]]) || nzchar(bundle$industries[[id]]$withheld[[m]] %||% "")
      if (!ok) problems <- c(problems, sprintf("industry %s: capability '%s' is false with no withheld reason", id, m))
    }
  }
  .rf_gate("G7 bundle", if (length(problems)) "FAIL" else "PASS", if (length(problems)) paste(utils::head(problems, 6), collapse = "; ") else "schema-valid, all numbers finite, every calculator industry has a capability or a reason per model")
}

# The staged bundle is loaded by the v2-capable calculator: the command in MENTAT_G8_CMD runs with MENTAT_GIVING_MODELS set to the path
# (for example `python -m pytest mentat/tests/test_giving_forecast.py`); exit status 0 = PASS. Without a command: HOLD.
rf_gate_consumer <- function(bundle_path, cmd = Sys.getenv("MENTAT_G8_CMD", unset = "")) {
  if (!nzchar(cmd)) return(.rf_gate("G8 consumer smoke", "HOLD", "no v2-capable calculator configured (MENTAT_G8_CMD unset): HOLD until the v2 calculator exists"))
  out <- suppressWarnings(system2("bash", c("-c", shQuote(cmd)), env = paste0("MENTAT_GIVING_MODELS=", bundle_path), stdout = TRUE, stderr = TRUE))
  st <- attr(out, "status") %||% 0L
  .rf_gate("G8 consumer smoke", if (st == 0L) "PASS" else "HOLD", sprintf("exit status %d: %s", st, paste(utils::tail(out, 2), collapse = " | ")))
}

rf_gate_naive <- function(v) {
  bt <- v$backtests
  rule <- c(pac = v$selection$pac$reported_rule, control_House = v$selection$control_House$reported_rule, control_Senate = v$selection$control_Senate$reported_rule)
  cells <- list(pac = c("pac", "bundle", "loeo", "prevchg", rule[["pac"]]), control_House = c("control_House", "selected", "loeo", "prevchg", rule[["control_House"]]),
                control_Senate = c("control_Senate", "selected", "loeo", "prevchg", rule[["control_Senate"]]), lobby_log = c("lobby", "log", "rolling", "calc", "R0"))
  lose <- character()
  for (nm in names(cells)) {
    c <- cells[[nm]]
    r <- bt[bt$term == c[1] & bt$base == c[2] & bt$design == c[3] & bt$path == c[4] & bt$rule == c[5], ]
    nv <- bt[bt$term == c[1] & bt$base == c[2] & bt$design == c[3] & bt$path == c[4] & bt$rule == "naive_prev", ]
    if (nrow(r) && nrow(nv) && r$MAE >= nv$MAE) lose <- c(lose, sprintf("%s (%.3f vs naive %.3f)", nm, r$MAE, nv$MAE))
  }
  .rf_gate("G9 vs naive", if (length(lose)) "WARN" else "PASS", if (length(lose)) paste("does not beat last-period naive:", paste(lose, collapse = "; ")) else "every calculator path beats last-period naive")
}

# ---- decision ------------------------------------------------------------------------------------------------------------------------

rf_decision <- function(gates) if (any(gates$status == "FAIL")) "FAIL" else if (any(gates$status == "HOLD")) "HOLD" else "PUBLISH"

# All gates of a refit. `base` = data.frame of G0-G3 (from the run). -> list(gates, g4, g5, g6)
rf_gates <- function(v, bundle, published = NULL, base = NULL, bundle_path = NULL, consumer_cmd = Sys.getenv("MENTAT_G8_CMD", unset = "")) {
  g4 <- v$adequacy %||% rf_gate_adequacy(v$ctx)
  g5 <- rf_gate_stability(v, bundle, published)
  g6 <- rf_gate_nondegradation(v, published)
  g7 <- rf_gate_bundle(bundle, v$ctx$reg)
  g8 <- if (is.null(bundle_path)) .rf_gate("G8 consumer smoke", "HOLD", "bundle not staged on disk") else rf_gate_consumer(bundle_path, consumer_cmd)
  g9 <- rf_gate_naive(v)
  gates <- rbind(base, g4$gate, g5$gate, g6$gate, g7, g8, g9)
  rownames(gates) <- NULL
  list(gates = gates, g4 = g4, g5 = g5, g6 = g6, decision = rf_decision(gates))
}
