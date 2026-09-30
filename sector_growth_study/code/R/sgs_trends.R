# TRENDS (rulings of 2026-09-26; Paul: "Doesn't matter if it is significant if the trend is there"): one row per focal
# term of every ESTIMABLE test, pooled and per sector (the strata: each sector's own regression; H5: each board), trend
# first: the sign, the size in plain units ($M 2025, share points, USD per toughness point), whether the hypothesis'
# stated sign holds, and whether the sign is the same across the test's variants; p and CI after. Joint F tests (no
# sign) and leave-one-out sub-fits (diagnostics) are not rows.
#
# Variants: a test's trend group is its registry trend_group (SHIFT: the main test of each variant set); else, for a
# ROBUSTNESS or PREVIEW test, the root of its base chain (R-LV-thin-L1 -> L1-LV, C1-PV-reduced -> C1); H5 tests share
# the group H5; every other test is its own group. Within a group, terms are compared by name (the telecom-component
# suffixes _tw / _tc dropped), and per-sector rows by name and sector.
#
# DESCRIPTIVE terms (coordinator's rulings of 2026-09-26): a saturated SHIFT test (no year-level residual df) keeps its
# rows in the sheet (term_label "DESCRIPTIVE (SATURATED)") but takes no part in the sign agreement of its group and is
# left out of the report's headline table (listed under it); a per-sector term resting on one sector cluster stays in
# the headline, labelled, without p or CI there. The Holm p, the two-way sensitivity and the incremental fit of the
# coefficient rows are carried when present (sgs_review.R).

SGS_TREND_COLS <- c("test_id", "family", "label", "term_label", "trend_group", "coefficient", "scope", "window", "n", "sign", "size",
                    "plain_value", "plain_unit", "predicted_sign", "matches_prediction", "same_sign_across_variants", "variants",
                    "n_variants", "sectors_plus_minus", "identification", "estimate", "unit", "se", "se_kind", "boot_p", "ci_low",
                    "ci_high", "ci_text", "boot_draws", "flag", "holm_family", "holm_p", "se_2way", "p_2way", "adj_r2_with",
                    "adj_r2_without")

sgs_trend_group <- function(t, registry) {
  tg <- t$trend_group %||% NA_character_
  if (length(tg) == 1L && !is.na(tg)) return(tg)
  if (identical(t$family, "H5")) return("H5")
  cur <- t; seen <- character(0)
  while (cur$label %in% c("ROBUSTNESS", "PREVIEW") && length(cur$base) == 1L && !is.na(cur$base) &&
         cur$base %in% names(registry) && !(cur$base %in% seen)) {
    seen <- c(seen, cur$id)
    cur <- registry[[cur$base]]
    tg <- cur$trend_group %||% NA_character_
    if (length(tg) == 1L && !is.na(tg)) return(tg)
  }
  cur$id
}

.trend_key <- function(coef) sub("_(tw|tc)(:|$)", "\\2", coef)

# "0" for an estimate that is zero to rounding (|b| < 1e-10: a constant outcome's slopes print as ~1e-17 noise)
.trend_sign <- function(x) if (is.na(x)) "n/a" else if (abs(x) < 1e-10) "0" else if (x > 0) "+" else "-"

# The estimate in plain units: share DVs (0-1) x 100 = share points; the H5 'any' probability x 100 = percentage
# points; $M 2025, USD 2025 and log units as they are.
sgs_trend_plain <- function(estimate, unit) {
  u <- as.character(unit %||% "")
  if (is.na(estimate)) return(list(value = NA_real_, unit = u, text = "n/a"))
  v <- estimate
  if (startsWith(u, "Democratic share (0-1)")) {
    v <- 100 * estimate; u <- sub("^Democratic share \\(0-1\\)", "share points of the Democratic share", u)
  } else if (startsWith(u, "probability (0-1) of any money > 0")) {
    v <- 100 * estimate; u <- sub("^probability \\(0-1\\) of any money > 0", "percentage points of the probability of any money", u)
  } else if (grepl("^difference of the two slopes .*Democratic share \\(0-1\\)", u)) {
    v <- 100 * estimate; u <- sub("Democratic share \\(0-1\\)", "share points of the Democratic share", u)
  }
  sg <- .trend_sign(v)
  sg <- if (sg %in% c("+", "-")) sg else ""
  txt <- paste0(sg, sgs_fmt(abs(v)), " ", u)
  # expected control is a 0-1 probability: also the size per 0.1 of it (the whole 0-1 range is rarely crossed)
  if (grepl("per unit \\(0-1\\) of expected Democratic", u)) txt <- paste0(txt, " (", sg, sgs_fmt(abs(v) / 10), " per 0.1)")
  list(value = v, unit = u, text = txt)
}

.trend_predicted <- function(spec, coef) {
  ps <- spec$predicted_sign %||% character(0)
  if (!length(ps) || is.null(names(ps))) return("")
  if (coef %in% names(ps)) return(unname(ps[[coef]]))
  b <- sub(":.*$", "", coef)
  if (b %in% names(ps)) return(unname(ps[[b]]))
  ""
}

# order_ = the tests of the run; registry = the full registry (for base chains); results = the fitted results by test.
sgs_trends_table <- function(order_, est_rows, coef_rows, strata_rows, results, registry = order_) {
  rows <- setNames(est_rows, vapply(est_rows, `[[`, "", "test_id"))
  st_key <- vapply(strata_rows, function(s) paste(s$test_id, s$coefficient, sep = "\r"), "")
  num <- function(x) if (is.null(x) || !length(x)) NA_real_ else as.numeric(x)
  out <- list()
  for (t in order_) {
    r <- rows[[t$id]]
    if (is.null(r) || !identical(r$status, SGS_ESTIMABLE)) next
    grp <- sgs_trend_group(t, registry)
    src <- if (identical(t$variant, "derived")) t$base else t$id
    ident <- results[[src]]$identification$short %||% character(0)
    # a saturated SHIFT test is DESCRIPTIVE (SATURATED) (also without the diagnostics of sgs_review.R)
    sat <- grepl(SGS$SATURATED_LABEL, as.character(r$flag %||% ""), fixed = TRUE) ||
      (t$family %in% c("SHIFT", "SHIFT-PV") && isTRUE(results[[src]]$identification$saturated))
    cs <- Filter(function(c) identical(c$test_id, t$id) && is.null(c$left_out) && !identical(c$test, "joint"), coef_rows)
    for (c in cs) {
      pl <- sgs_trend_plain(c$estimate, c$unit)
      pred <- .trend_predicted(t, c$coefficient)
      sg <- .trend_sign(c$estimate)
      desc <- startsWith(as.character(c$inference %||% ""), "none")
      lab <- as.character(c$term_label %||% "")
      if (sat) lab <- SGS$SATURATED_LABEL
      srcid <- if (!is.null(c$source_test) && nzchar(as.character(c$source_test))) c$source_test else t$id
      strata <- Filter(function(s) identical(s$status, "estimated"), strata_rows[st_key == paste(srcid, c$coefficient, sep = "\r")])
      ssg <- vapply(strata, function(s) .trend_sign(s$estimate), "")
      pm <- if (length(strata)) paste0("+ ", sum(ssg == "+"), ", - ", sum(ssg == "-"), " of ", length(strata), " estimated") else ""
      diag <- list(holm_family = as.character(c$holm_family %||% ""), holm_p = num(c$holm_p), se_2way = num(c$se_2way),
                   p_2way = num(c$p_2way), adj_r2_with = num(c$adj_r2_with), adj_r2_without = num(c$adj_r2_without))
      out[[length(out) + 1L]] <- c(list(
        test_id = t$id, family = t$family, label = r$label, term_label = lab, trend_group = grp, coefficient = c$coefficient,
        scope = "pooled",
        window = as.character(c$window_used %||% r$window_used), n = c$n %||% r$n, sign = sg, size = pl$text, plain_value = pl$value,
        plain_unit = pl$unit, predicted_sign = pred,
        matches_prediction = if (!nzchar(pred) || sg %in% c("0", "n/a")) "" else if (sg == pred) "yes" else "no",
        sectors_plus_minus = pm,
        identification = if (c$coefficient %in% names(ident)) unname(ident[[c$coefficient]]) else "",
        estimate = c$estimate, unit = c$unit, se = if (desc) c$hc1_se else c$cr1_se,
        se_kind = if (desc) "HC1 (reference; DESCRIPTIVE)" else "CR1", boot_p = c$boot_p, ci_low = c$ci_low, ci_high = c$ci_high,
        ci_text = c$ci_text %||% "", boot_draws = c$boot_draws, flag = c$flag %||% "", .key = .trend_key(c$coefficient)), diag)
      for (s in strata) {
        ps <- sgs_trend_plain(s$estimate, c$unit)
        scope <- if (!is.null(s$board)) paste0("board ", s$board) else s$study_sector
        out[[length(out) + 1L]] <- list(
          test_id = t$id, family = t$family, label = r$label, term_label = lab, trend_group = grp, coefficient = c$coefficient,
          scope = scope,
          window = if (!is.null(s$cycles)) paste0("cycles ", s$cycles) else as.character(s$years %||% ""), n = s$n,
          sign = .trend_sign(s$estimate), size = ps$text, plain_value = ps$value, plain_unit = ps$unit, predicted_sign = pred,
          matches_prediction = if (!nzchar(pred) || .trend_sign(s$estimate) %in% c("0", "n/a")) "" else
            if (.trend_sign(s$estimate) == pred) "yes" else "no",
          sectors_plus_minus = "", identification = "", estimate = s$estimate, unit = c$unit, se = s$hc1_se,
          se_kind = "HC1 (stratum: the sector's own regression; no inference)", boot_p = NA_real_, ci_low = NA_real_,
          ci_high = NA_real_, ci_text = "", boot_draws = NA_real_, flag = c$flag %||% "", .key = .trend_key(c$coefficient),
          holm_family = "", holm_p = NA_real_, se_2way = NA_real_, p_2way = NA_real_, adj_r2_with = NA_real_,
          adj_r2_without = NA_real_)
      }
    }
  }
  if (!length(out)) return(sgs_rows_df(list(), SGS_TREND_COLS))
  df <- sgs_rows_df(out, c(SGS_TREND_COLS, ".key"))
  # sign agreement across each group's variants (same term, same scope); DESCRIPTIVE (SATURATED) rows take no part
  gk <- paste(df$trend_group, df$.key, df$scope, sep = "\r")
  df$same_sign_across_variants <- ""; df$variants <- ""; df$n_variants <- NA_real_
  satr <- df$term_label %in% SGS$SATURATED_LABEL
  df$same_sign_across_variants[satr] <- paste0("n/a (", SGS$SATURATED_LABEL, ")")
  for (k in unique(gk[!satr])) {
    i <- which(gk == k & !satr)
    sg <- df$sign[i]; ids <- df$test_id[i]
    df$n_variants[i] <- length(i)
    if (length(i) == 1L) { df$same_sign_across_variants[i] <- "single test"; df$variants[i] <- ids; next }
    known <- sg %in% c("+", "-")
    same <- length(unique(sg[known])) <= 1L && all(known)
    df$same_sign_across_variants[i] <- if (same) "yes" else "no"
    parts <- vapply(c("+", "-", "0", "n/a"), function(x) {
      h <- ids[sg == x]
      if (!length(h)) "" else paste0(x, " in ", length(h), " (", paste(h, collapse = ", "), ")")
    }, "")
    df$variants[i] <- paste(parts[nzchar(parts)], collapse = "; ")
  }
  df$.key <- NULL
  df[, SGS_TREND_COLS, drop = FALSE]
}

# Markdown: the pooled rows, trend first (sign, size, prediction, variants, per-sector signs), then p and CI (with the
# Holm p where the term is in a pre-specified family). DESCRIPTIVE (SATURATED) rows are listed under the table, not in it;
# a DESCRIPTIVE term shows no p or CI.
sgs_trends_md <- function(tr) {
  all_pooled <- tr[tr$scope == "pooled", , drop = FALSE]
  satr <- if ("term_label" %in% names(all_pooled)) all_pooled$term_label %in% SGS$SATURATED_LABEL else rep(FALSE, nrow(all_pooled))
  pooled <- all_pooled[!satr, , drop = FALSE]
  gone <- unique(all_pooled$test_id[satr])
  L <- c(paste0("One row per focal term of every ESTIMABLE test (", nrow(pooled), " pooled rows; ", sum(tr$scope != "pooled"),
                " per-sector / per-board rows in sheet trends, which also keeps the ", SGS$SATURATED_LABEL, " rows). Sign and ",
                "size first, in plain units; 'hypothesis' = the sign the stated hypothesis predicts (SHIFT: +; CONTRACT: +; ",
                "ASYM-SLOPES decline-year slopes: -); 'variants' = whether the sign is the same in every ESTIMABLE variant of the ",
                "test (same term; Hill / FD / weighted / STRICT / preview, year FE / log / first differences, undifferentiated / ",
                "thin / component, jointly / alone ...; the EXPLORATORY minimum-base variants form their own group); 'sectors' = ",
                "the signs of the per-sector regressions (strata; no inference). p = wild cluster restricted bootstrap (Holm p ",
                "within the pre-specified family in brackets); CI by test inversion. A DESCRIPTIVE term (one sector cluster; a ",
                "test without inference) shows no p or CI."), "",
         if (any(all_pooled$family %in% c("SHIFT", "SHIFT-PV"))) c(paste0(SGS_SHIFT_PREVIEW_READING, " ", SGS_SHIFT_WEIGHT_NOTE), "")
         else character(0),
         if (length(gone)) c(paste0(SGS$SATURATED_LABEL, ", left out of this table and of the sign agreement (rows kept in ",
                                    "sheet trends; summary blocks in the summaries file): ", paste(gone, collapse = ", "), "."), "")
         else character(0),
         "| test | label | term | sign | size (plain units) | hypothesis | same sign across variants | sectors | p | 95% CI |",
         "|---|---|---|---|---|---|---|---|---:|---|")
  for (i in seq_len(nrow(pooled))) {
    x <- pooled[i, , drop = FALSE]
    hyp <- if (nzchar(x$predicted_sign)) paste0(x$predicted_sign, ": ", x$matches_prediction) else ""
    var <- if (x$same_sign_across_variants %in% c("yes", "no")) paste0(x$same_sign_across_variants, " (", x$variants, ")") else x$same_sign_across_variants
    lab <- sgs_label_text(x$label)
    tl <- if ("term_label" %in% names(x)) .txt0(x$term_label) else ""
    if (nzchar(tl) && !identical(tl, lab)) lab <- paste0(lab, "; ", tl)
    desc <- nzchar(tl)
    pcell <- if (desc) "n/a (DESCRIPTIVE)" else paste0(sgs_fmt(x$boot_p),
                                                        if ("holm_p" %in% names(x) && is.finite(x$holm_p)) paste0(" [Holm ", sgs_fmt(x$holm_p), "]") else "")
    L <- c(L, paste0("| ", x$test_id, " | ", lab, " | ", x$coefficient, " | ", x$sign, " | ", .md_escape(x$size),
                     " | ", hyp, " | ", .md_escape(var), " | ", .md_escape(x$sectors_plus_minus), " | ", pcell, " | ",
                     .md_escape(if (desc) "n/a (DESCRIPTIVE)" else if (nzchar(.txt0(x$ci_text))) x$ci_text else "n/a"), " |"))
  }
  L
}
