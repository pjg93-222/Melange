# Tidy analysis tables (plan section 7) built from the loaded workbooks (R port of code/sgs/panel.py).
#
# sector_year       one row per study sector x calendar year 2006-2026 (nine sectors x 21 years)
# sector_year_tier  one row per study sector x year x job tier (Chief, Middle Management, Employee, Corporate)
# industry_year     one row per 04 unit (the study sectors with a Mentat workbook plus community_banks) x year (H1-PV)
# Expected control (exp_dem_*): see sgs_expected_control; method, timing flag and source of every value are carried
# as exp_dem_*_method / _flag / _source.
#
# Status vocabulary of every *_status column:
#   observed        value present in an observed source row (03 current control 2026 keeps its label 'derived')
#   partial         source row is partial (2026 through mid-year; LobbyView 2024 sliver); never used in estimation
#   missing         the sector has a source series (or the input is national) but no usable value for the year
#   not_applicable  no source series is mapped to the sector for this input, or the design withholds it
# Missing values are NA, never 0, except one documented derivation: a tier absent from 04 tier_by_year in a
# sector-year whose total giving is observed is 0 (the source keeps rows only where giving != 0 or gifts > 0).
#
# Paul's rulings (rule set paul-2026-09-25) add to sector_year: LobbyView for every study sector (01
# lobbyview_sector_year_all), the de-duplicated contributions (no gifts to a roster company's own PAC), the 538
# House generic-ballot margin (02 expected_control_538), the multi-year projections of compliant (i) (06), and the
# Democratic share of House / Senate giving (08 sector_year_chamber). Each is NOT BUILT when its sheet is absent.

sgs_panel_years <- function() seq(SGS$PANEL_FIRST_YEAR, SGS$PANEL_LAST_YEAR)

.grid <- function() {
  g <- expand.grid(year = sgs_panel_years(), study_sector = SGS$STUDY_SECTORS, stringsAsFactors = FALSE)
  g <- data.frame(study_sector = g$study_sector, year = as.numeric(g$year), stringsAsFactors = FALSE)
  g$partial_year <- g$year %in% SGS$PARTIAL_YEARS
  g
}

# panel._status_fill: row status where a source row exists (missing when its value is blank but the status is
# usable), else missing for sectors with a source series, else not_applicable.
.status_fill <- function(df, col, has_series_sectors, row_status_col = NULL, value_col = NULL) {
  st <- if (!is.null(row_status_col)) df[[row_status_col]] else rep(NA_character_, nrow(df))
  val <- if (!is.null(value_col)) df[[value_col]] else NULL
  out <- ifelse(df$study_sector %in% has_series_sectors, SGS_MISSING, SGS_NA)
  has <- !is.na(st) & is.character(st) & nzchar(ifelse(is.na(st), "", st))
  out[has] <- st[has]
  if (!is.null(value_col)) {
    blank <- has & is.na(val) & st %in% SGS_USABLE_STATUSES
    out[blank] <- SGS_MISSING
  }
  df[[col]] <- out
  df
}

.crosswalk <- function(wbs) {
  xw <- wbs$crosswalk$frames$data
  xw <- xw[xw$study_sector %in% SGS$STUDY_SECTORS, , drop = FALSE]
  absent <- setdiff(SGS$STUDY_SECTORS, xw$study_sector)
  if (length(absent)) {
    sgs_raise("PanelError", paste0("sector_crosswalk.xlsx [data]: study sectors missing from the crosswalk: ",
                                   sgs_py_list_repr(sort(absent, method = "radix"))))
  }
  xw
}

.drop_private <- function(g) g[, !startsWith(names(g), "_"), drop = FALSE]

.sort_sector_year <- function(g) {
  g[order(sgs_sector_rank(g$study_sector), g$year, method = "radix"), , drop = FALSE]
}

.chk_04_sums <- function(sy4, agg) {
  chk <- sgs_left_join(sy4[, c("study_sector", "year", "giving_real_2025_usd"), drop = FALSE], agg, c("study_sector", "year"))
  # as pandas: a NaN difference (no data rows for a sector_year total) compares False and is not flagged
  bad <- !is.na(chk$giving_real_2025_usd) & abs(chk$contributions_real_m * 1e6 - chk$giving_real_2025_usd) > 1.0
  bad[is.na(bad)] <- FALSE
  if (any(bad)) {
    sgs_raise("PanelError", paste0("04_campaign_spending.xlsx: data-sheet sums disagree with sector_year by more than $1: ",
                                   sgs_records_repr(chk[bad, c("study_sector", "year"), drop = FALSE])))
  }
}

.agg_04 <- function(d4, name = "contributions_real_m") {
  agg <- sgs_group_sum(d4, c("study_sector", "year"), "giving_real_2025_usd", min_count = 1L, name = name)
  agg[[name]] <- agg[[name]] / 1e6
  agg
}

sgs_build_sector_year <- function(wbs, rules = sgs_rules()) {
  g <- .grid()
  xw <- .crosswalk(wbs)

  # ---- controls (00): election-cycle indicators; the CPI status is kept for transparency only
  c0 <- wbs$controls$frames$data
  ctl <- data.frame(year = c0$year, pres_year = c0$presidential_year, midterm_year = c0$midterm_year,
                    cpi_status = c0$status, stringsAsFactors = FALSE)
  g <- sgs_left_join(g, ctl, "year")
  g$controls_status <- ifelse(!is.na(g$pres_year) & !is.na(g$midterm_year), SGS_OBS, SGS_MISSING)

  # ---- contributions (04 general giving): sum over companies, recipient categories, parties and funding sources
  d4 <- wbs$spending$frames$data
  d4 <- d4[d4$study_sector %in% SGS$STUDY_SECTORS, , drop = FALSE]
  agg <- .agg_04(d4)
  sy4 <- wbs$spending$frames$sector_year
  sy4 <- sy4[sy4$study_sector %in% SGS$STUDY_SECTORS, c("study_sector", "year", "giving_real_2025_usd", "status"), drop = FALSE]
  .chk_04_sums(sy4, agg)
  g <- sgs_left_join(g, agg, c("study_sector", "year"))
  g <- sgs_left_join(g, data.frame(study_sector = sy4$study_sector, year = sy4$year, `_c_status` = sy4$status,
                                   check.names = FALSE, stringsAsFactors = FALSE), c("study_sector", "year"))
  workbook_sectors <- unique(xw$study_sector[!is.na(xw$mentat_industry)])
  g <- .status_fill(g, "contributions_status", workbook_sectors, "_c_status", "contributions_real_m")

  # ---- lobbying (01): LDA income and expenses (never summed); LobbyView undifferentiated amount (high confidence)
  lx <- xw[!is.na(xw$lda_lobbying_sector), , drop = FALSE]
  if (anyDuplicated(lx$lda_lobbying_sector)) {
    sgs_raise("PanelError", "sector_crosswalk.xlsx [data] column lda_lobbying_sector: one LDA sector maps to two study sectors")
  }
  lmap <- setNames(lx$study_sector, lx$lda_lobbying_sector)
  lob <- wbs$lobbying$frames$data
  lob$study_sector <- unname(lmap[lob$sector])
  sel <- lob$source %in% "lda_rebuild" & lob$period %in% "annual" & !is.na(lob$study_sector)
  lda <- data.frame(study_sector = lob$study_sector[sel], year = lob$year[sel], `_lda_status` = lob$status[sel],
                    lobby_income_real_m = lob$lobby_income_real_2025_usd[sel] / 1e6,
                    lobby_expenses_real_m = lob$lobby_expenses_real_2025_usd[sel] / 1e6,
                    check.names = FALSE, stringsAsFactors = FALSE)
  g <- sgs_left_join(g, lda, c("study_sector", "year"))
  lda_sectors <- unique(unname(lmap))
  g <- .status_fill(g, "lobby_income_status", lda_sectors, "_lda_status", "lobby_income_real_m")
  g <- .status_fill(g, "lobby_expenses_status", lda_sectors, "_lda_status", "lobby_expenses_real_m")
  lv <- .lobbyview_rows(wbs, lmap, rules)
  g <- sgs_left_join(g, lv$rows, c("study_sector", "year"))
  g <- .status_fill(g, "lobby_undiff_status", lv$sectors, "_lv_status", "lobby_amount_undiff_real_m")
  if (identical(rules$lobbyview, "all_sectors")) {
    # Paul's LobbyView rules: primary = de-duplicated amount when 01 has it (else the undifferentiated amount,
    # "dedup pending"); thin sector-years (coverage_flag "thin": fewer than 5 reporting clients) excluded from the
    # primary and from the undifferentiated robustness, kept in the keep-thin robustness.
    g <- .status_fill(g, "lobby_lv_status", lv$sectors, "_lv_status", "lobby_lv_real_m")
    g <- .status_fill(g, "lobby_lv_thin_status", lv$sectors, "_lv_status", "lobby_lv_thin_real_m")
    thin <- g$`_lv_thin` %in% TRUE
    g$lobby_undiff_status[thin & g$lobby_undiff_status %in% SGS_USABLE_STATUSES] <- "thin"
    g$lobby_lv_status[thin & g$lobby_lv_status %in% SGS_USABLE_STATUSES] <- "thin"
    g$lobby_lv_coverage_flag <- g$`_lv_cov`
  }

  # ---- actual growth (07); telecom: components kept separate, sector growth withheld
  a7 <- wbs$actual$frames$data
  a7s <- a7[a7$study_sector %in% SGS$STUDY_SECTORS & a7$study_sector != "telecom", , drop = FALSE]
  per <- tapply(a7s$sector, a7s$study_sector, function(v) length(unique(v[!is.na(v)])))
  if (any(per > 1)) {
    many <- per[per > 1]
    sgs_raise("PanelError", paste0("07_actual_industry_growth.xlsx [data]: several series map to one study sector: {",
                                   paste0(vapply(names(many), sgs_py_repr, ""), ": ", many, collapse = ", "), "}"))
  }
  a7v <- data.frame(study_sector = a7s$study_sector, year = a7s$year, growth_same_year_pct = a7s$growth_same_year_pct,
                    growth_previous_year_pct = a7s$growth_previous_year_pct, `_g_status` = a7s$status,
                    check.names = FALSE, stringsAsFactors = FALSE)
  g <- sgs_left_join(g, a7v, c("study_sector", "year"))
  growth_sectors <- unique(a7v$study_sector)
  g <- .status_fill(g, "growth_same_status", growth_sectors, "_g_status", "growth_same_year_pct")
  g <- .status_fill(g, "growth_prev_status", growth_sectors, "_g_status", "growth_previous_year_pct")
  for (comp in SGS_TELECOM_COMPONENTS) {
    cm <- a7[a7$sector %in% comp, , drop = FALSE]
    c7 <- data.frame(year = cm$year, a = cm$growth_same_year_pct, b = cm$growth_previous_year_pct,
                     study_sector = rep("telecom", nrow(cm)), stringsAsFactors = FALSE)
    names(c7)[2:3] <- c(paste0("growth_same_year_pct_", comp), paste0("growth_previous_year_pct_", comp))
    g <- sgs_left_join(g, c7, c("study_sector", "year"))
  }
  tel <- g$study_sector == "telecom"
  g$growth_same_year_pct[tel] <- NA
  g$growth_previous_year_pct[tel] <- NA
  g$growth_same_status[tel] <- SGS_NA
  g$growth_prev_status[tel] <- SGS_NA
  if (isTRUE(rules$chronology) && "report_vintage" %in% names(a7)) {
    # chronology (coordinator's revision of 2026-09-26): the 07 report vintage each growth value comes from (07 is a
    # retrospective series, one recent vintage per sector); telecom: the later of its two components' vintages
    v7 <- data.frame(study_sector = a7s$study_sector, year = as.numeric(a7s$year), growth_vintage = as.character(a7s$report_vintage),
                     stringsAsFactors = FALSE)
    tcv <- a7[a7$sector %in% SGS_TELECOM_COMPONENTS & !is.na(a7$report_vintage), , drop = FALSE]
    if (nrow(tcv)) {
      tv <- tapply(as.character(tcv$report_vintage), as.numeric(tcv$year), function(v) max(v))
      v7 <- rbind(v7, data.frame(study_sector = "telecom", year = as.numeric(names(tv)), growth_vintage = unname(as.character(tv)),
                                 stringsAsFactors = FALSE))
    }
    g <- sgs_left_join(g, v7, c("study_sector", "year"))
  }

  # ---- predicted growth (06 strict column only); vintage fields only where the strict value is used
  p6 <- wbs$predicted$frames$data
  p6 <- p6[p6$study_sector %in% SGS$STUDY_SECTORS, , drop = FALSE]
  p6 <- data.frame(study_sector = p6$study_sector, year = p6$year, predicted_growth_pct = p6$predicted_growth_pct,
                   forecast_publication_month = p6$forecast_publication_month,
                   forecast_age_months = p6$forecast_age_months, predicted_source_status = p6$status,
                   stringsAsFactors = FALSE)
  g <- sgs_left_join(g, p6, c("study_sector", "year"))
  has_p <- !is.na(g$predicted_growth_pct)
  g$forecast_publication_month[!has_p] <- NA
  g$forecast_age_months[!has_p] <- NA
  g$predicted_status <- ifelse(has_p, SGS_OBS, SGS_MISSING)

  # ---- rulings of 2026-09-26 (Paul's rule set only): telecom growth = the revenue-weighted wireless + cable components
  # (07 actual, 06 component forecasts) with component variants; the one-year growth values 06 holds for crypto and
  # fintech outside the strict column; the ASYM (g >= 0 / g < 0) and DECEL (g_t < g_{t-1}) columns
  telecom_built <- NULL; proxy_built <- NULL
  if (isTRUE(rules$telecom_combined)) {
    g <- .add_telecom_combined(g, wbs)
    telecom_built <- attr(g, "telecom")
  }
  if (isTRUE(rules$annual_proxies)) {
    g <- .add_annual_proxies(g, wbs)
    proxy_built <- attr(g, "annual_proxies")
  }
  if (isTRUE(rules$extensions_0926)) g <- .add_asym_decel(g)

  # ---- expected control (02) and current control (03); final seat calls (02 seat_calls)
  ec <- sgs_expected_control(wbs, rules)
  for (ch in c("House", "Senate")) {
    s <- tolower(ch)
    e <- ec[ec$chamber == ch, , drop = FALSE]
    e <- data.frame(year = e$year, a = e$exp_dem, b = e$status, m = e$method, f = e$flag, src = e$source,
                    stringsAsFactors = FALSE)
    names(e) <- c("year", paste0("exp_dem_", s), paste0("_e_", s), paste0("exp_dem_", s, "_method"),
                  paste0("exp_dem_", s, "_flag"), paste0("exp_dem_", s, "_source"))
    if (isTRUE(rules$chronology)) {
      # coordinator's revision of 2026-09-26: when each value was measured (= available), and whether after its year
      ma <- ec$measured_at[ec$chamber == ch]
      e[[paste0("exp_dem_", s, "_measured_at")]] <- ma
      e[[paste0("exp_dem_", s, "_available_at")]] <- ma
      e[[paste0("exp_dem_", s, "_after_year")]] <- !is.na(ma) & !is.na(e$year) & suppressWarnings(as.numeric(substr(ma, 1, 4))) > e$year
    }
    g <- sgs_left_join(g, e, "year")
    g <- .status_fill(g, paste0("exp_dem_", s, "_status"), SGS$STUDY_SECTORS, paste0("_e_", s), paste0("exp_dem_", s))
    cc <- wbs$seats$frames$current_control
    cc <- cc[cc$chamber %in% ch, , drop = FALSE]
    c3 <- data.frame(year = cc$calendar_year, a = cc$dem_control, b = cc$status, stringsAsFactors = FALSE)
    names(c3) <- c("year", paste0("cur_dem_", s), paste0("_cc_", s))
    g <- sgs_left_join(g, c3, "year")
    g <- .status_fill(g, paste0("cur_dem_", s, "_status"), SGS$STUDY_SECTORS, paste0("_cc_", s), paste0("cur_dem_", s))
    ex <- g[[paste0("exp_dem_", s)]]
    cu <- g[[paste0("cur_dem_", s)]]
    ok <- !is.na(ex) & !is.na(cu) & g[[paste0("exp_dem_", s, "_status")]] %in% SGS_USABLE_STATUSES &
      g[[paste0("cur_dem_", s, "_status")]] %in% SGS_USABLE_STATUSES
    g[[paste0("exp_shift_", s)]] <- ifelse(ok, ex - cu, NA_real_)
    g[[paste0("exp_shift_", s, "_status")]] <- ifelse(ok, SGS_OBS, SGS_MISSING)
    sc <- wbs$election$frames$seat_calls
    sc <- sc[sc$chamber %in% ch, , drop = FALSE]
    c2 <- data.frame(year = sc$election_year, a = sc$pred_dem_net_change, b = sc$status, stringsAsFactors = FALSE)
    names(c2) <- c("year", paste0("pred_dem_seat_change_", s), paste0("_sc_", s))
    g <- sgs_left_join(g, c2, "year")
    g <- .status_fill(g, paste0("seat_calls_", s, "_status"), SGS$STUDY_SECTORS, paste0("_sc_", s),
                      paste0("pred_dem_seat_change_", s))
    odd <- g$year %% 2 == 1
    g[[paste0("pred_dem_seat_change_", s)]][odd] <- NA
    g[[paste0("seat_calls_", s, "_status")]][odd] <- SGS_NA
  }

  # ---- Paul's rulings: extra series (absent in the parity rule set); `built` records which inputs exist
  built <- list()
  if (identical(rules$lobbyview, "all_sectors")) {
    built$lobbyview_all <- list(built = lv$built, note = lv$note, label = lv$label, dedup = lv$dedup)
    built$lobbyview_dedup <- list(built = isTRUE(lv$dedup), note = if (isTRUE(lv$dedup)) lv$note else paste0(
      "01 ", SGS$LOBBYVIEW_ALL_SHEET, " has no ", SGS$LOBBYVIEW_DEDUP_COLUMN, " yet (dedup pending): the primary LobbyView ",
      "tests already use the undifferentiated amount, so this robustness variant would repeat them"))
  }
  if (isTRUE(rules$pac_dedup)) {
    g <- .add_dedup_contributions(g, wbs, workbook_sectors)
    built$pac_dedup <- list(built = TRUE, note = paste0("04 data without recipient_category '", SGS$COMPANY_PAC_CATEGORY, "'"))
  }
  if (isTRUE(rules$h4_538)) {
    g <- .add_538(g, wbs)
    built$gb538 <- attr(g, "gb538")
  }
  if (isTRUE(rules$multiyear)) {
    g <- .add_multiyear(g, wbs, rules)
    reg <- attr(g, "multiyear_register")
    n_use <- if (is.null(reg) || !nrow(reg)) 0 else sum(reg$use == "yes")
    built$multiyear <- list(built = n_use > 0, register = reg,
                            note = if (n_use > 0) paste0(n_use, " multi-year projections placed by the vintage rule")
                                   else "06 has no crypto or fintech multi-year projection with a publication date")
  }
  if (isTRUE(rules$ds_chamber)) {
    g <- .add_dem_share(g, wbs)
    built$dem_share <- attr(g, "dem_share")
    built$dem_share_hill <- attr(g, "dem_share_hill")
    if (isTRUE(rules$shift)) {
      # DS+Hill: 08 sector_year_chamber_with_hill (added 2026-09-26) supplies the Hill-inclusive shares when present
      g <- .add_dem_share_hill_sheet(g, wbs)
      built$dem_share_hill <- attr(g, "dem_share_hill") %||% built$dem_share_hill
    }
  }
  if (!is.null(telecom_built)) {
    built$telecom_combined <- telecom_built
    for (tag in SGS$TELECOM_COMPONENT_TAGS) built[[paste0("telecom_", tag)]] <- telecom_built$components[[tag]]
    built$telecom_combined$components <- NULL
  }
  if (!is.null(proxy_built)) built$annual_proxies <- proxy_built

  g <- .drop_private(g)
  if (anyDuplicated(sgs_key_of(g, c("study_sector", "year")))) {
    sgs_raise("PanelError", "sector_year: duplicate study_sector x year rows after joins")
  }
  if (nrow(g) != length(SGS$STUDY_SECTORS) * length(sgs_panel_years())) {
    sgs_raise("PanelError", paste0("sector_year: ", nrow(g), " rows, expected ",
                                   length(SGS$STUDY_SECTORS) * length(sgs_panel_years())))
  }
  g <- .sort_sector_year(g)
  rownames(g) <- NULL
  attr(g, "built") <- built
  g
}

# LobbyView rows for sector_year: list(rows = data.frame(study_sector, year, _lv_status, lobby_amount_undiff_real_m),
# sectors = sectors with a LobbyView series, note).
.lobbyview_rows <- function(wbs, lmap, rules) {
  empty <- data.frame(study_sector = character(0), year = numeric(0), `_lv_status` = character(0),
                      lobby_amount_undiff_real_m = numeric(0), check.names = FALSE, stringsAsFactors = FALSE)
  if (!identical(rules$lobbyview, "all_sectors")) {
    lob <- wbs$lobbying$frames$data
    lob$study_sector <- unname(lmap[lob$sector])
    sel <- lob$source %in% "lobbyview_adversary_spend" & lob$period %in% "annual" & lob$confidence %in% "high" &
      !is.na(lob$study_sector)
    rows <- data.frame(study_sector = lob$study_sector[sel], year = lob$year[sel], `_lv_status` = lob$status[sel],
                       lobby_amount_undiff_real_m = lob$lobby_amount_undifferentiated_real_2025_usd[sel] / 1e6,
                       check.names = FALSE, stringsAsFactors = FALSE)
    return(list(rows = rows, sectors = unique(rows$study_sector), built = TRUE, note = ""))
  }
  sh <- wbs$lobbying$frames[[SGS$LOBBYVIEW_ALL_SHEET]]
  empty$lobby_lv_real_m <- numeric(0); empty$lobby_lv_thin_real_m <- numeric(0)
  empty$`_lv_thin` <- logical(0); empty$`_lv_cov` <- character(0)
  if (is.null(sh)) {
    return(list(rows = empty, sectors = character(0), built = FALSE, dedup = FALSE, label = "",
                note = paste0("01 sheet ", SGS$LOBBYVIEW_ALL_SHEET, " not present")))
  }
  lab <- paste0("01_lobbying_expenditures.xlsx [", SGS$LOBBYVIEW_ALL_SHEET, "]")
  ss <- if ("study_sector" %in% names(sh)) sh$study_sector else rep(NA_character_, nrow(sh))
  if ("sector" %in% names(sh)) {
    by_map <- unname(lmap[sh$sector])
    direct <- ifelse(sh$sector %in% SGS$STUDY_SECTORS, sh$sector, NA_character_)
    ss <- ifelse(is.na(ss), ifelse(!is.na(direct), direct, by_map), ss)
  }
  keep <- ss %in% SGS$STUDY_SECTORS
  if ("period" %in% names(sh)) keep <- keep & (is.na(sh$period) | sh$period %in% "annual")
  if ("confidence" %in% names(sh)) keep <- keep & !(sh$confidence %in% "low")  # high / roster / naics: one row each
  dedup <- SGS$LOBBYVIEW_DEDUP_COLUMN %in% names(sh)
  undiff <- sh$lobby_amount_undifferentiated_real_2025_usd / 1e6
  primary <- if (dedup) as.numeric(sh[[SGS$LOBBYVIEW_DEDUP_COLUMN]]) / 1e6 else undiff
  cov <- if ("coverage_flag" %in% names(sh)) as.character(sh$coverage_flag) else rep(NA_character_, nrow(sh))
  thin <- grepl("thin", cov, fixed = TRUE)
  rows <- data.frame(study_sector = ss[keep], year = sh$year[keep], `_lv_status` = sh$status[keep],
                     lobby_amount_undiff_real_m = undiff[keep], lobby_lv_real_m = primary[keep],
                     lobby_lv_thin_real_m = primary[keep], `_lv_thin` = thin[keep], `_lv_cov` = cov[keep],
                     check.names = FALSE, stringsAsFactors = FALSE)
  k <- sgs_key_of(rows, c("study_sector", "year"))
  if (anyDuplicated(k)) {
    sgs_raise("PanelError", paste0(lab, ": more than one LobbyView row per study sector x year after the filters ",
                                   "(annual, confidence other than low); never summed"))
  }
  label <- if (dedup) paste0("LobbyView amount, de-duplicated (01 ", SGS$LOBBYVIEW_ALL_SHEET, " ", SGS$LOBBYVIEW_DEDUP_COLUMN, ")")
           else paste0("LobbyView undifferentiated amount (01 ", SGS$LOBBYVIEW_ALL_SHEET, "), undifferentiated, dedup pending")
  list(rows = rows, sectors = unique(rows$study_sector), built = TRUE, dedup = dedup, label = label,
       note = paste0(nrow(rows), " rows (", length(unique(rows$study_sector)), " study sectors, confidence other than low) from ",
                     lab, "; primary amount: ", if (dedup) SGS$LOBBYVIEW_DEDUP_COLUMN else
                       "lobby_amount_undifferentiated_real_2025_usd (dedup pending)", "; thin sector-years: ",
                     sum(rows$`_lv_thin`)))
}

# ---- Paul's rulings: de-duplicated contributions, 538, multi-year projections, Democratic share ------------------

# 04 general giving without the gifts to a roster company's own PAC (recipient_category 'Company PAC', Mentat's
# report.R company-alias + PAC match), and the overlap share of those gifts in general giving.
.add_dedup_contributions <- function(g, wbs, workbook_sectors) {
  d4 <- wbs$spending$frames$data
  d4 <- d4[d4$study_sector %in% SGS$STUDY_SECTORS, , drop = FALSE]
  pac <- d4$recipient_category %in% SGS$COMPANY_PAC_CATEGORY
  dd <- .agg_04(d4[!pac, , drop = FALSE], "contributions_dedup_real_m")
  cp <- .agg_04(d4[pac, , drop = FALSE], "company_pac_real_m")
  g <- sgs_left_join(g, dd, c("study_sector", "year"))
  g <- sgs_left_join(g, cp, c("study_sector", "year"))
  obs <- g$contributions_status %in% SGS_USABLE_STATUSES & !is.na(g$contributions_real_m)
  # a sector-year whose total is observed but has no non-PAC (or no PAC) gift has 0 there
  g$contributions_dedup_real_m[obs & is.na(g$contributions_dedup_real_m)] <- 0
  g$company_pac_real_m[obs & is.na(g$company_pac_real_m)] <- 0
  g$contributions_dedup_status <- g$contributions_status
  g$contributions_dedup_real_m[!obs] <- NA
  g$company_pac_real_m[!obs] <- NA
  g$company_pac_share <- ifelse(obs & g$contributions_real_m != 0, g$company_pac_real_m / g$contributions_real_m, NA_real_)
  g
}

# 02 expected_control_538 (columns year, chamber, series, value, n_days, first_date, last_date, source_url, sha256,
# method): series generic_ballot_margin, chamber House = the within-year mean of 538's daily generic-ballot average,
# Democratic minus Republican, points (robustness family H4-538 only). The house_control_* / senate_control_*
# forecast rows (2018, 2020, 2022 only) are ignored.
SGS_538_SERIES <- "generic_ballot_margin"

.add_538 <- function(g, wbs) {
  sh <- wbs$election$frames[[SGS$EXPECTED_CONTROL_538_SHEET]]
  g$gb538_margin_house <- NA_real_
  g$gb538_margin_house_status <- SGS_MISSING
  if (is.null(sh)) {
    attr(g, "gb538") <- list(built = FALSE, note = paste0("02 sheet ", SGS$EXPECTED_CONTROL_538_SHEET, " not present"))
    return(g)
  }
  rows <- sh[sh$series %in% SGS_538_SERIES, , drop = FALSE]
  if ("chamber" %in% names(rows)) rows <- rows[is.na(rows$chamber) | rows$chamber %in% "House", , drop = FALSE]
  st <- if ("status" %in% names(rows)) rows$status else rep(SGS_OBS, nrow(rows))
  ok <- !is.na(rows$value) & st %in% SGS_USABLE_STATUSES & !is.na(rows$year)
  v <- rows[ok, , drop = FALSE]
  if (anyDuplicated(v$year)) {
    sgs_raise("PanelError", paste0("02_election_forecasting.xlsx [", SGS$EXPECTED_CONTROL_538_SHEET,
                                   "]: more than one usable House generic_ballot_margin row per year"))
  }
  if (!nrow(v)) {
    attr(g, "gb538") <- list(built = FALSE, note = paste0("02 ", SGS$EXPECTED_CONTROL_538_SHEET, ": no usable House ",
                                                          SGS_538_SERIES, " value"))
    return(g)
  }
  m <- match(g$year, v$year)
  g$gb538_margin_house <- as.numeric(v$value[m])
  g$gb538_margin_house_status <- ifelse(is.na(m), SGS_MISSING, SGS_OBS)
  blank <- rows$year[is.na(rows$value)]
  attr(g, "gb538") <- list(built = TRUE, note = paste0(
    "02 ", SGS$EXPECTED_CONTROL_538_SHEET, " series ", SGS_538_SERIES, " (House, D minus R, points): ", nrow(v),
    " calendar years ", sgs_years_text(v$year), if (length(blank)) paste0("; blank ", sgs_years_text(blank)) else "",
    "; the forecast series house_control_* / senate_control_* are not used"))
  g
}

# Compliant (i), plan section 9: each multi-year crypto / fintech CAGR of 06 (supplemental_observations,
# component_forecasts) enters only the spending year right after its publication (the vintage rule: for spending
# year t, the latest projection available by 31 December of t-1). Returns the register with every candidate.
.field <- function(r, name) if (name %in% names(r)) r[[name]][1] else NA
.first_present <- function(...) {
  for (v in list(...)) if (!is.null(v) && length(v) && !is.na(v)) return(v)
  NA
}

sgs_multiyear_register <- function(wbs, rules = sgs_rules()) {
  fr <- wbs$predicted$frames
  out <- list()
  norm <- function(s) if (isTRUE(rules$normalise_06_labels)) tolower(trimws(s)) else s
  sup <- fr$supplemental_observations
  if (!is.null(sup)) {
    for (i in seq_len(nrow(sup))) {
      r <- sup[i, , drop = FALSE]
      out[[length(out) + 1L]] <- list(source_sheet = "supplemental_observations", record = .field(r, "observation_id"),
                                      record_source = "additional_forecast_observations",
                                      study_sector_raw = .field(r, "study_sector"),
                                      study_sector = norm(.field(r, "study_sector")),
                                      growth_pct = .field(r, "growth_pct"), measure = .field(r, "growth_measure"),
                                      available = .field(r, "known_available_by"),
                                      published = .field(r, "publication_date_or_month"), status = .field(r, "status"))
    }
  }
  cf <- fr$component_forecasts
  if (!is.null(cf)) {
    for (i in seq_len(nrow(cf))) {
      r <- cf[i, , drop = FALSE]
      cagr <- .field(r, "published_cagr_pct")
      comp <- .field(r, "published_growth_pct")
      if (!is.na(cagr)) {
        measure <- paste0("multiyear CAGR ", .field(r, "forecast_period_start"), "-", .field(r, "forecast_period_end"),
                          " (", .field(r, "provider"), ")")
        gval <- cagr
      } else if (!is.na(comp)) {
        measure <- paste0("component growth, target ", .field(r, "forecast_target_year"), " (",
                          .field(r, "metric_status"), ")")
        gval <- comp
      } else {
        measure <- "component annual growth (predicted_growth_pct)"
        gval <- .field(r, "predicted_growth_pct")
      }
      out[[length(out) + 1L]] <- list(source_sheet = "component_forecasts",
                                      record = .first_present(.field(r, "observation_id"), .field(r, "record_key")),
                                      record_source = .field(r, "record_source"),
                                      study_sector_raw = .field(r, "study_sector"),
                                      study_sector = norm(.field(r, "study_sector")),
                                      growth_pct = gval, measure = measure, available = .field(r, "known_available_by"),
                                      published = .first_present(.field(r, "publication_date"), .field(r, "forecast_vintage")),
                                      status = .field(r, "status"))
    }
  }
  if (!length(out)) return(data.frame())
  reg <- sgs_rows_df(out, c("source_sheet", "record", "record_source", "study_sector_raw", "study_sector", "growth_pct",
                            "measure", "available", "published", "status"))
  reg$is_cagr <- grepl("CAGR", reg$measure, ignore.case = TRUE)
  reg$in_scope <- reg$study_sector %in% c("crypto", "fintech") & reg$is_cagr
  date_txt <- ifelse(!is.na(reg$available), reg$available, reg$published)
  reg$availability_date <- substr(date_txt, 1, 10)
  reg$publication_year <- suppressWarnings(as.numeric(substr(date_txt, 1, 4)))
  reg$spending_year <- reg$publication_year + 1
  reg$use <- "no"
  reg$why <- ifelse(!reg$study_sector %in% c("crypto", "fintech"), "not a crypto or fintech projection",
                    ifelse(!reg$is_cagr, "not a multi-year CAGR", ""))
  reg$why[reg$in_scope & is.na(reg$publication_year)] <- "no publication or availability date"
  cand <- which(reg$in_scope & !is.na(reg$publication_year) & !is.na(reg$growth_pct) & reg$status %in% SGS_USABLE_STATUSES)
  if (length(cand)) {
    key <- paste(reg$study_sector[cand], reg$spending_year[cand])
    for (k in unique(key)) {
      idx <- cand[key == k]
      o <- order(reg$availability_date[idx], decreasing = TRUE, method = "radix")
      reg$use[idx[o[1]]] <- "yes"
      reg$why[idx[o[1]]] <- paste0("latest projection available by 31 Dec ", reg$publication_year[idx[o[1]]],
                                   " -> spending year ", reg$spending_year[idx[o[1]]])
      if (length(idx) > 1) {
        for (j in idx[o[-1]]) reg$why[j] <- paste0("superseded by the later projection ", reg$record[idx[o[1]]],
                                                   " for spending year ", reg$spending_year[j])
      }
    }
  }
  reg
}

.add_multiyear <- function(g, wbs, rules) {
  reg <- sgs_multiyear_register(wbs, rules)
  g$predicted_growth_multiyear_pct <- NA_real_
  g$predicted_multiyear_record <- NA_character_
  g$predicted_multiyear_status <- ifelse(g$study_sector %in% c("crypto", "fintech"), SGS_MISSING, SGS_NA)
  if (nrow(reg)) {
    u <- reg[reg$use == "yes", , drop = FALSE]
    m <- match(paste(g$study_sector, g$year), paste(u$study_sector, u$spending_year))
    has <- !is.na(m)
    g$predicted_growth_multiyear_pct[has] <- u$growth_pct[m[has]]
    g$predicted_multiyear_record[has] <- paste0(u$source_sheet[m[has]], ":", u$record[m[has]], " (", u$measure[m[has]],
                                                ", available ", u$availability_date[m[has]], ")")
    g$predicted_multiyear_status[has] <- SGS_OBS
  }
  attr(g, "multiyear_register") <- reg
  g
}

# 08 sector_year_chamber: Democratic share of general giving to House / Senate candidate committees by sector-year
# (dem_share = dem_usd / (dem_usd + rep_usd), as built; ActBlue / WinRed conduit gifts are outside the chambers in
# 08). The dollar base of every share (dem_usd + rep_usd) is carried so each DS test can report it.
# DS+Hill (robustness): DCCC and DSCC added to D, NRCC and NRSC to R for the matching chamber, from 08
# other_recipients when that sheet splits the four Hill committees (columns of_which_dccc_usd, of_which_nrcc_usd,
# of_which_dscc_usd, of_which_nrsc_usd); a single combined of_which_hill_committees_usd cannot be split: NOT BUILT.
SGS_HILL_COLUMNS <- list(house = c(D = "of_which_dccc_usd", R = "of_which_nrcc_usd"),
                         senate = c(D = "of_which_dscc_usd", R = "of_which_nrsc_usd"))

.add_dem_share <- function(g, wbs) {
  for (ch in c("house", "senate")) {
    g[[paste0("dem_share_", ch)]] <- NA_real_
    g[[paste0("dem_share_", ch, "_status")]] <- SGS_MISSING
    g[[paste0("dem_share_", ch, "_base_usd")]] <- NA_real_
    g[[paste0("dem_share_", ch, "_base_real_m")]] <- NA_real_
    g[[paste0("dem_share_hill_", ch)]] <- NA_real_
    g[[paste0("dem_share_hill_", ch, "_status")]] <- SGS_MISSING
  }
  if (is.null(wbs$chamber)) {
    attr(g, "dem_share") <- list(built = FALSE, note = paste0(SGS$CHAMBER_FILE, " not present in the input folder"))
    attr(g, "dem_share_hill") <- attr(g, "dem_share")
    return(g)
  }
  sh <- wbs$chamber$frames[[SGS$CHAMBER_SHEET]]
  lab <- paste0(SGS$CHAMBER_FILE, " [", SGS$CHAMBER_SHEET, "]")
  sh <- sh[sh$study_sector %in% SGS$STUDY_SECTORS, , drop = FALSE]
  den <- sh$dem_usd + sh$rep_usd
  calc <- ifelse(!is.na(den) & den != 0, sh$dem_usd / den, NA_real_)
  share <- as.numeric(sh$dem_share)  # the supplied share is used as linked; the recomputation is a check only
  bad <- (!is.na(share) & !is.na(calc) & abs(share - calc) > 1e-9) | (is.na(share) != is.na(calc))
  st <- if ("status" %in% names(sh)) sh$status else rep(SGS_OBS, nrow(sh))
  real_base <- if (all(c("dem_real_m", "rep_real_m") %in% names(sh))) sh$dem_real_m + sh$rep_real_m else rep(NA_real_, nrow(sh))
  orr <- wbs$chamber$frames$other_recipients
  hill_ok <- !is.null(orr) && all(unlist(SGS_HILL_COLUMNS) %in% names(orr))
  for (ch in c("House", "Senate")) {
    s <- tolower(ch)
    rows <- which(sh$chamber %in% ch)
    m <- match(paste(g$study_sector, g$year), paste(sh$study_sector[rows], sh$year[rows]))
    has <- !is.na(m)
    ix <- rows[m[has]]
    g[[paste0("dem_share_", s)]][has] <- share[ix]
    stc <- st[ix]
    stc[is.na(share[ix]) & stc %in% SGS_USABLE_STATUSES] <- SGS_MISSING
    g[[paste0("dem_share_", s, "_status")]][has] <- stc
    g[[paste0("dem_share_", s, "_base_usd")]][has] <- den[ix]
    g[[paste0("dem_share_", s, "_base_real_m")]][has] <- real_base[ix]
    if (hill_ok) {
      hc <- SGS_HILL_COLUMNS[[s]]
      mo <- match(paste(sh$study_sector[ix], sh$year[ix]), paste(orr$study_sector, orr$year))
      d_h <- sh$dem_usd[ix] + orr[[hc[["D"]]]][mo]
      r_h <- sh$rep_usd[ix] + orr[[hc[["R"]]]][mo]
      sh_h <- ifelse(!is.na(d_h + r_h) & (d_h + r_h) > 0, d_h / (d_h + r_h), NA_real_)
      g[[paste0("dem_share_hill_", s)]][has] <- sh_h
      sth <- stc
      sth[is.na(sh_h) & sth %in% SGS_USABLE_STATUSES] <- SGS_MISSING
      g[[paste0("dem_share_hill_", s, "_status")]][has] <- sth
    }
  }
  attr(g, "dem_share_hill") <- if (hill_ok) {
    list(built = TRUE, note = paste0("08 other_recipients ", paste(unlist(SGS_HILL_COLUMNS), collapse = ", ")))
  } else {
    list(built = FALSE, note = paste0(
      "08 other_recipients carries the four Hill committees only as one combined total per sector-year ",
      "(of_which_hill_committees_usd = DCCC + NRCC + DSCC + NRSC); the D / R x House / Senate split that DS+Hill needs ",
      "is not in the sheet (committee_map has committee totals per cycle pooled across sectors)"))
  }
  attr(g, "dem_share") <- list(built = TRUE, note = paste0(
    nrow(sh), " rows from ", lab, "; dem_share as supplied",
    if (any(bad)) paste0("; CHECK: ", sum(bad), " rows differ from dem_usd / (dem_usd + rep_usd) by more than 1e-9")
    else "; equal to dem_usd / (dem_usd + rep_usd) in every row"))
  g
}

# DS+Hill from 08 sector_year_chamber_with_hill (SHIFT rule, 2026-09-26): the Hill-inclusive share of each study sector's
# House / Senate giving (DCCC / DSCC added to D, NRCC / NRSC to R, dem_share as 08 recomputed it) with its dollar base.
# Without that sheet the other_recipients split rule of .add_dem_share stands (and the attribute is left as it set it).
.add_dem_share_hill_sheet <- function(g, wbs) {
  sh <- if (!is.null(wbs$chamber)) wbs$chamber$frames[[SGS$CHAMBER_HILL_SHEET]] else NULL
  if (is.null(sh)) return(g)
  r <- .shift_08_rows(sh[sh$study_sector %in% SGS$STUDY_SECTORS, , drop = FALSE],
                      paste0(SGS$CHAMBER_FILE, " [", SGS$CHAMBER_HILL_SHEET, "]"))
  for (ch in c("House", "Senate")) {
    col <- paste0("dem_share_hill_", tolower(ch))
    g[[col]] <- NA_real_
    g[[paste0(col, "_status")]] <- SGS_MISSING
    g[[paste0(col, "_base_usd")]] <- NA_real_
    g[[paste0(col, "_base_real_m")]] <- NA_real_
    rr <- r$rows[r$rows$chamber %in% ch, , drop = FALSE]
    m <- match(paste(g$study_sector, g$year), paste(rr$study_sector, rr$year))
    has <- !is.na(m)
    g[[col]][has] <- rr$share[m[has]]
    g[[paste0(col, "_status")]][has] <- rr$status[m[has]]
    g[[paste0(col, "_base_usd")]][has] <- rr$base_usd[m[has]]
    g[[paste0(col, "_base_real_m")]][has] <- rr$base_real_m[m[has]]
  }
  attr(g, "dem_share_hill") <- list(built = TRUE, note = paste0(
    r$note, "; DS+Hill reads this sheet (DCCC / DSCC added to D, NRCC / NRSC to R by 08 itself), which replaces the ",
    "other_recipients split rule"))
  g
}

# ---- SHIFT tables (rulings of 2026-09-26: Paul's partisan-allocation hypothesis) ---------------------------------------
#
# shift_year     one row per Mentat industry of 04 / 08 (the seven study sectors with a Mentat book plus community_banks)
#                x year 2006-2026: the Democratic share D / (D + R) of the unit's giving to House and to Senate candidate
#                committees (08 sector_year_chamber), the same with the Hill committees (08 sector_year_chamber_with_hill),
#                and of ALL its party-labelled general giving (04 party D / R; "Other / Unclassified" is outside both),
#                each with its dollar base; the unit-year's general giving (04, all recipients, parties and funding
#                sources); the year-level terms of sector_year, identical for every unit in a year.
# shift_chamber  the House and Senate rows stacked (unit x year x chamber), with the expected and current Democratic
#                control of the recipient's own chamber (exp_dem_own_chamber, cur_dem_own_chamber).
# A zero or negative denominator is a missing share, never 0 (08 leaves dem_share blank when D + R <= 0). Every 04
# funding source stays in (Paul: "Keep those receipts": the non_giving "other receipt" rows are never dropped).

SGS_SHIFT_YEAR_COLS <- c("pres_year", "midterm_year", "controls_status",
                         "exp_dem_house", "exp_dem_house_status", "exp_dem_house_method", "exp_dem_house_flag",
                         "exp_dem_house_source", "exp_dem_senate", "exp_dem_senate_status", "exp_dem_senate_method",
                         "exp_dem_senate_flag", "exp_dem_senate_source", "cur_dem_house", "cur_dem_house_status",
                         "cur_dem_senate", "cur_dem_senate_status",
                         # chronology (present when sector_year carries them)
                         "exp_dem_house_measured_at", "exp_dem_house_available_at", "exp_dem_house_after_year",
                         "exp_dem_senate_measured_at", "exp_dem_senate_available_at", "exp_dem_senate_after_year")
SGS_SHIFT_TABLES <- c("shift_year", "shift_chamber")

# The units of the SHIFT tables: every unit of 04 sector_year and 08 sector_year_chamber, study sectors first in the
# plan's order, then the others (community_banks) by name.
.shift_units <- function(wbs) {
  u0 <- unique(c(wbs$spending$frames$sector_year$study_sector,
                 if (!is.null(wbs$chamber)) wbs$chamber$frames[[SGS$CHAMBER_SHEET]]$study_sector))
  u0 <- u0[!is.na(u0)]
  u0[order(sgs_sector_rank(u0), u0, method = "radix")]
}

# One 08 chamber sheet -> list(rows = data.frame(study_sector, year, chamber, share, status, base_usd, base_real_m), note).
# dem_share is used as supplied; dem_usd / (dem_usd + rep_usd) is a check only.
.shift_08_rows <- function(sh, label) {
  dem <- as.numeric(sh$dem_usd); rep <- as.numeric(sh$rep_usd)
  den <- dem + rep
  calc <- ifelse(!is.na(den) & den > 0, dem / den, NA_real_)
  share <- as.numeric(sh$dem_share)
  bad <- (!is.na(share) & !is.na(calc) & abs(share - calc) > 1e-9) | (is.na(share) != is.na(calc))
  st <- if ("status" %in% names(sh)) as.character(sh$status) else rep(SGS_OBS, nrow(sh))
  st[is.na(share) & st %in% SGS_USABLE_STATUSES] <- SGS_MISSING
  real <- if (all(c("dem_real_m", "rep_real_m") %in% names(sh))) as.numeric(sh$dem_real_m) + as.numeric(sh$rep_real_m) else
    rep(NA_real_, nrow(sh))
  rows <- data.frame(study_sector = as.character(sh$study_sector), year = as.numeric(sh$year), chamber = as.character(sh$chamber),
                     share = share, status = st, base_usd = den, base_real_m = real, stringsAsFactors = FALSE)
  list(rows = rows, note = paste0(nrow(sh), " rows from ", label, "; dem_share as supplied",
                                  if (any(bad)) paste0("; CHECK: ", sum(bad), " rows differ from dem_usd / (dem_usd + rep_usd) by more than 1e-9")
                                  else "; equal to dem_usd / (dem_usd + rep_usd) in every row"))
}

# A sum that is NA only when every value is NA (a partial year without real dollars), else the sum of the kept values
# (0 when none is kept: no gift of that party in an observed unit-year).
.sum_kept <- function(v, keep) if (!length(v) || all(is.na(v))) NA_real_ else sgs_kahan_sum(v[keep], 0L)

# 04 data -> per unit x year: D, R, other and all general giving (nominal USD and real $M 2025). Every funding source.
.shift_04_party <- function(d4) {
  gr <- sgs_groups(d4, c("study_sector", "year"))
  out <- gr$keys
  nom <- as.numeric(d4$giving_nominal_usd); real <- as.numeric(d4$giving_real_2025_usd); pty <- as.character(d4$party)
  isD <- pty %in% SGS$SHIFT_PARTIES[["D"]]; isR <- pty %in% SGS$SHIFT_PARTIES[["R"]]
  out$d_usd <- vapply(gr$index, function(ix) .sum_kept(nom[ix], isD[ix]), 0)
  out$r_usd <- vapply(gr$index, function(ix) .sum_kept(nom[ix], isR[ix]), 0)
  out$d_real_m <- vapply(gr$index, function(ix) .sum_kept(real[ix], isD[ix]), 0) / 1e6
  out$r_real_m <- vapply(gr$index, function(ix) .sum_kept(real[ix], isR[ix]), 0) / 1e6
  out$other_real_m <- vapply(gr$index, function(ix) .sum_kept(real[ix], !(isD[ix] | isR[ix])), 0) / 1e6
  out$total_real_m <- vapply(gr$index, function(ix) .sum_kept(real[ix], rep(TRUE, length(ix))), 0) / 1e6
  out$non_giving_real_m <- vapply(gr$index, function(ix) .sum_kept(real[ix], d4$funding_source[ix] %in% "non_giving"), 0) / 1e6
  out
}

.shift_flag_text <- function(units, years, chamber) {
  out <- rep(NA_character_, length(units))
  for (f in SGS$SHIFT_FLAGS) {
    same <- if (is.na(f$chamber)) is.na(chamber) else (!is.na(chamber) && identical(f$chamber, chamber))
    if (!same) next
    k <- units == f$study_sector & years == f$year
    out[k] <- ifelse(is.na(out[k]), f$text, paste0(out[k], "; ", f$text))
  }
  out
}

sgs_build_shift_tables <- function(wbs, sector_year) {
  units <- .shift_units(wbs)
  g <- expand.grid(year = sgs_panel_years(), study_sector = units, stringsAsFactors = FALSE)
  g <- data.frame(study_sector = g$study_sector, year = as.numeric(g$year), stringsAsFactors = FALSE)
  g$partial_year <- g$year %in% SGS$PARTIAL_YEARS
  sy4 <- wbs$spending$frames$sector_year
  first <- sy4[!duplicated(sy4$study_sector), , drop = FALSE]
  g$mentat_industry <- if ("mentat_industry" %in% names(sy4)) first$mentat_industry[match(g$study_sector, first$study_sector)] else
    g$study_sector
  g$is_study_sector <- g$study_sector %in% SGS$STUDY_SECTORS
  yl <- sector_year[sector_year$study_sector == SGS$STUDY_SECTORS[1],
                    c("year", intersect(SGS_SHIFT_YEAR_COLS, names(sector_year))), drop = FALSE]
  g <- sgs_left_join(g, yl, "year")
  built <- list()
  # ---- 08: House / Senate candidate committees, and the same with the Hill committees
  for (v in list(list(tag = "", sheet = SGS$CHAMBER_SHEET, key = "shift_08"),
                 list(tag = "hill_", sheet = SGS$CHAMBER_HILL_SHEET, key = "shift_08_hill"))) {
    for (ch in c("house", "senate")) {
      col <- paste0("dem_share_", v$tag, ch)
      g[[col]] <- NA_real_
      g[[paste0(col, "_status")]] <- SGS_MISSING
      g[[paste0(col, "_base_usd")]] <- NA_real_
      g[[paste0(col, "_base_real_m")]] <- NA_real_
    }
    sh <- if (!is.null(wbs$chamber)) wbs$chamber$frames[[v$sheet]] else NULL
    if (is.null(sh)) {
      built[[v$key]] <- list(built = FALSE, note = if (is.null(wbs$chamber)) paste0(SGS$CHAMBER_FILE, " not present in the input folder")
                             else paste0(SGS$CHAMBER_FILE, " has no sheet ", v$sheet, " yet"))
      next
    }
    r <- .shift_08_rows(sh, paste0(SGS$CHAMBER_FILE, " [", v$sheet, "]"))
    for (ch in c("House", "Senate")) {
      col <- paste0("dem_share_", v$tag, tolower(ch))
      rr <- r$rows[r$rows$chamber %in% ch, , drop = FALSE]
      m <- match(paste(g$study_sector, g$year), paste(rr$study_sector, rr$year))
      has <- !is.na(m)
      g[[col]][has] <- rr$share[m[has]]
      g[[paste0(col, "_status")]][has] <- rr$status[m[has]]
      g[[paste0(col, "_base_usd")]][has] <- rr$base_usd[m[has]]
      g[[paste0(col, "_base_real_m")]][has] <- rr$base_real_m[m[has]]
    }
    built[[v$key]] <- list(built = TRUE, note = paste0(r$note, "; units ", paste(sgs_sort_sectors(unique(r$rows$study_sector)), collapse = ", ")))
  }
  # ---- 04: all party-labelled general giving (every recipient category and funding source)
  d4 <- wbs$spending$frames$data
  p4 <- .shift_04_party(d4)
  m <- match(paste(g$study_sector, g$year), paste(p4$study_sector, p4$year))
  d_usd <- p4$d_usd[m]; r_usd <- p4$r_usd[m]
  den <- d_usd + r_usd
  g$dem_share_all <- ifelse(!is.na(den) & den > 0, d_usd / den, NA_real_)
  st <- sy4$status[match(paste(g$study_sector, g$year), paste(sy4$study_sector, sy4$year))]
  st[is.na(st)] <- SGS_MISSING
  st[is.na(g$dem_share_all) & st %in% SGS_USABLE_STATUSES] <- SGS_MISSING
  g$dem_share_all_status <- st
  g$dem_share_all_base_usd <- den
  g$dem_share_all_d_real_m <- p4$d_real_m[m]
  g$dem_share_all_r_real_m <- p4$r_real_m[m]
  g$dem_share_all_base_real_m <- p4$d_real_m[m] + p4$r_real_m[m]
  g$dem_share_all_other_real_m <- p4$other_real_m[m]
  g$general_giving_real_m <- p4$total_real_m[m]
  g$general_giving_non_giving_real_m <- p4$non_giving_real_m[m]
  g$dem_share_all_dr_share <- ifelse(!is.na(g$general_giving_real_m) & g$general_giving_real_m > 0,
                                     g$dem_share_all_base_real_m / g$general_giving_real_m, NA_real_)
  ok4 <- g$dem_share_all_status %in% SGS_USABLE_STATUSES
  out_of_range <- sum(ok4 & (g$dem_share_all < 0 | g$dem_share_all > 1), na.rm = TRUE)
  built$shift_04 <- list(built = any(ok4), note = paste0(
    "04 data party D / R (", sum(ok4), " usable unit-years; 'Other / Unclassified' outside both; every recipient category and ",
    "funding source, non_giving 'other receipt' rows included)",
    if (out_of_range) paste0("; CHECK: ", out_of_range, " shares outside 0-1 (net refunds)") else ""))
  # ---- flags (e.g. fintech Senate 2026, Kalshi)
  g$shift_flag_house <- .shift_flag_text(g$study_sector, g$year, "House")
  g$shift_flag_senate <- .shift_flag_text(g$study_sector, g$year, "Senate")
  g$shift_flag_all <- .shift_flag_text(g$study_sector, g$year, NA_character_)
  if (anyDuplicated(sgs_key_of(g, c("study_sector", "year")))) sgs_raise("PanelError", "shift_year: duplicate unit x year rows")
  g <- g[order(sgs_sector_rank(g$study_sector), g$study_sector, g$year, method = "radix"), , drop = FALSE]
  rownames(g) <- NULL
  # ---- the stacked table
  base_cols <- c("study_sector", "year", "partial_year", "mentat_industry", "is_study_sector", "pres_year", "midterm_year",
                 "controls_status")
  parts <- list()
  for (ch in c("House", "Senate")) {
    s <- tolower(ch)
    x <- g[, intersect(base_cols, names(g)), drop = FALSE]
    x$chamber <- ch
    for (sfx in c("", "_status", "_method", "_flag", "_source", "_measured_at", "_available_at", "_after_year")) {
      src <- paste0("exp_dem_", s, sfx)
      if (sfx %in% c("_measured_at", "_available_at", "_after_year") && !src %in% names(g)) next  # chronology columns only
      x[[paste0("exp_dem_own_chamber", sfx)]] <- if (src %in% names(g)) g[[src]] else NA
    }
    for (sfx in c("", "_status")) {
      src <- paste0("cur_dem_", s, sfx)
      x[[paste0("cur_dem_own_chamber", sfx)]] <- if (src %in% names(g)) g[[src]] else NA
    }
    for (tag in c("", "hill_")) for (sfx in c("", "_status", "_base_usd", "_base_real_m")) {
      x[[paste0("dem_share", if (nzchar(tag)) "_hill" else "", sfx)]] <- g[[paste0("dem_share_", tag, s, sfx)]]
    }
    x$general_giving_real_m <- g$general_giving_real_m
    x$shift_flag <- g[[paste0("shift_flag_", s)]]
    parts[[ch]] <- x
  }
  sc <- rbind(parts$House, parts$Senate)
  sc <- sc[, c("study_sector", "year", "chamber", setdiff(names(sc), c("study_sector", "year", "chamber"))), drop = FALSE]
  sc <- sc[order(sgs_sector_rank(sc$study_sector), sc$study_sector, sc$year, match(sc$chamber, c("House", "Senate")),
                 method = "radix"), , drop = FALSE]
  rownames(sc) <- NULL
  list(shift_year = g, shift_chamber = sc, built = built, units = units)
}

# ---- rulings of 2026-09-26: telecom growth, one-year growth values, ASYM / DECEL, bank split -------------------------

.num_col <- function(df, col) if (col %in% names(df)) suppressWarnings(as.numeric(df[[col]])) else rep(NA_real_, nrow(df))
.chr_col <- function(df, col) if (col %in% names(df)) as.character(df[[col]]) else rep(NA_character_, nrow(df))
.truthy <- function(v) toupper(trimws(as.character(v))) %in% c("TRUE", "1", "YES")

SGS_TELECOM_NOTE <- paste0("telecom growth = the revenue-weighted wireless + cable components (Paul's ask of 2026-09-26; ",
                           "the plan kept the components separate)")

# Actual telecom growth (07): growth of the summed wireless + cable revenue, sum(R_t) / sum(R_{t-1}) - 1, i.e. the
# components' same-year growth weighted by their year t-1 revenue (R_{t-1} = R_t / (1 + g_t / 100): the component's
# own same-vintage growth), using the first revenue column of 07 that both components carry in one price basis; equal
# weights (and the label says so) when neither does. Previous-year growth of year t = the combined same-year growth of
# t-1 (07's definition of growth_previous_year_pct). Both components are required in a year.
.telecom_actual_combined <- function(a7) {
  comps <- names(SGS$TELECOM_COMPONENT_CODES)
  a <- a7[a7$sector %in% comps & a7$status %in% SGS_USABLE_STATUSES & !is.na(.num_col(a7, "growth_same_year_pct")), , drop = FALSE]
  revcols <- intersect(c("revenue_million_constant_2026_usd", "revenue_million_report_price_basis"), names(a))
  out <- list()
  for (y in sort(unique(a$year))) {
    r <- a[a$year == y, , drop = FALSE]
    if (!all(comps %in% r$sector) || anyDuplicated(r$sector)) next
    r <- r[match(comps, r$sector), , drop = FALSE]
    gg <- as.numeric(r$growth_same_year_pct)
    w <- c(0.5, 0.5); how <- "equal weights (07 has no component revenue in one price basis for the year)"
    for (rc in revcols) {
      v <- as.numeric(r[[rc]])
      basis <- if (rc == "revenue_million_report_price_basis") .chr_col(r, "revenue_price_basis") else rep("constant 2026 USD", 2)
      if (all(!is.na(v) & v > 0) && !anyNA(basis) && length(unique(basis)) == 1L) {
        prev <- v / (1 + gg / 100)
        w <- prev / sum(prev)
        how <- paste0("revenue-weighted (07 ", rc, ", ", basis[1], "): growth of the summed wireless + cable revenue")
        break
      }
    }
    out[[length(out) + 1L]] <- data.frame(year = as.numeric(y), g_same = sum(w * gg), w_wireless = w[1], how = how,
                                          stringsAsFactors = FALSE)
  }
  if (!length(out)) return(data.frame(year = numeric(0), g_same = numeric(0), w_wireless = numeric(0), how = character(0),
                                      g_prev = numeric(0), stringsAsFactors = FALSE))
  df <- do.call(rbind, out)
  df$g_prev <- df$g_same[match(df$year - 1, df$year)]
  df
}

# Predicted telecom growth (06 component_forecasts, study_sector Telecom): each component's one-year forecast for its
# target year (publication before the target year), weighted by the report's same-vintage baseline revenue; equal
# weights (labelled) when a baseline is missing. Both components are required. Also returns each component's series.
.telecom_predicted_combined <- function(cf) {
  empty <- data.frame(year = numeric(0), g_pred = numeric(0), w_wireless = numeric(0), how = character(0),
                      month = character(0), stringsAsFactors = FALSE)
  comps <- names(SGS$TELECOM_COMPONENT_CODES)
  if (is.null(cf) || !nrow(cf)) return(list(combined = empty, comp = setNames(vector("list", 2), comps)))
  ss <- tolower(trimws(.chr_col(cf, "study_sector")))
  code <- .chr_col(cf, "component_code")
  tgt <- .num_col(cf, "target_year"); tgt2 <- .num_col(cf, "forecast_target_year"); tgt[is.na(tgt)] <- tgt2[is.na(tgt)]
  gp <- .num_col(cf, "predicted_growth_pct")
  pre <- if ("publication_precedes_target_year" %in% names(cf)) .truthy(cf$publication_precedes_target_year) else rep(TRUE, nrow(cf))
  st <- .chr_col(cf, "status"); st[is.na(st)] <- SGS_OBS
  base <- .num_col(cf, "baseline_revenue_same_vintage")
  pub <- .chr_col(cf, "publication_date"); pub[is.na(pub)] <- .chr_col(cf, "publication_month")[is.na(pub)]
  ok <- ss %in% "telecom" & code %in% SGS$TELECOM_COMPONENT_CODES & !is.na(tgt) & !is.na(gp) & pre & st %in% SGS_USABLE_STATUSES
  comp <- list()
  for (cn in comps) {
    k <- which(ok & code == SGS$TELECOM_COMPONENT_CODES[[cn]])
    d <- data.frame(year = tgt[k], g = gp[k], base = base[k], pub = pub[k], stringsAsFactors = FALSE)
    d <- d[order(d$year, d$pub, method = "radix"), , drop = FALSE]
    d <- d[!duplicated(d$year, fromLast = TRUE), , drop = FALSE]  # one forecast per target year: the latest publication
    comp[[cn]] <- d
  }
  yrs <- sort(intersect(comp[[1]]$year, comp[[2]]$year))
  if (!length(yrs)) return(list(combined = empty, comp = comp))
  rows <- lapply(yrs, function(y) {
    a <- comp[[1]][comp[[1]]$year == y, ]; b <- comp[[2]][comp[[2]]$year == y, ]
    wb <- c(a$base, b$base)
    if (all(!is.na(wb) & wb > 0)) {
      w <- wb / sum(wb); how <- "revenue-weighted (06 component_forecasts baseline_revenue_same_vintage of each report)"
    } else {
      w <- c(0.5, 0.5); how <- "equal weights (06 lacks a component baseline revenue for the target year)"
    }
    mo <- substr(c(a$pub, b$pub), 1, 7); mo <- mo[!is.na(mo)]
    data.frame(year = y, g_pred = w[1] * a$g + w[2] * b$g, w_wireless = w[1], how = how,
               month = if (length(mo)) max(mo) else NA_character_, stringsAsFactors = FALSE)
  })
  list(combined = do.call(rbind, rows), comp = comp)
}

.add_telecom_combined <- function(g, wbs) {
  a7 <- wbs$actual$frames$data
  act <- .telecom_actual_combined(a7)
  pr <- .telecom_predicted_combined(wbs$predicted$frames$component_forecasts)
  tel <- g$study_sector == "telecom"
  m <- match(g$year[tel], act$year)
  g$growth_same_year_pct[tel] <- act$g_same[m]
  g$growth_previous_year_pct[tel] <- act$g_prev[m]
  g$growth_same_status[tel] <- ifelse(is.na(g$growth_same_year_pct[tel]), SGS_MISSING, SGS_OBS)
  g$growth_prev_status[tel] <- ifelse(is.na(g$growth_previous_year_pct[tel]), SGS_MISSING, SGS_OBS)
  g$telecom_growth_method <- NA_character_
  g$telecom_growth_method[tel] <- act$how[m]
  mp <- match(g$year[tel], pr$combined$year)
  g$predicted_growth_pct[tel] <- pr$combined$g_pred[mp]
  g$predicted_status[tel] <- ifelse(is.na(g$predicted_growth_pct[tel]), SGS_MISSING, SGS_OBS)
  g$forecast_publication_month[tel] <- pr$combined$month[mp]
  g$telecom_predicted_method <- NA_character_
  g$telecom_predicted_method[tel] <- pr$combined$how[mp]
  comps_built <- list()
  for (cn in names(SGS$TELECOM_COMPONENT_CODES)) {
    tag <- SGS$TELECOM_COMPONENT_TAGS[[cn]]
    for (v in SGS_GROWTH_BASE_VARS) {
      g[[paste0(v, "_", tag)]] <- g[[v]]
      g[[paste0(v, "_", tag, "_status")]] <- g[[SGS_STATUS_OF[[v]]]]
    }
    cm <- a7[a7$sector %in% cn & a7$status %in% SGS_USABLE_STATUSES, , drop = FALSE]
    mm <- match(g$year[tel], cm$year)
    for (v in c("growth_same_year_pct", "growth_previous_year_pct")) {
      vals <- .num_col(cm, v)[mm]
      g[[paste0(v, "_", tag)]][tel] <- vals
      g[[paste0(v, "_", tag, "_status")]][tel] <- ifelse(is.na(vals), SGS_MISSING, SGS_OBS)
    }
    pc <- pr$comp[[cn]]
    vals <- if (is.null(pc)) rep(NA_real_, sum(tel)) else pc$g[match(g$year[tel], pc$year)]
    g[[paste0("predicted_growth_pct_", tag)]][tel] <- vals
    g[[paste0("predicted_growth_pct_", tag, "_status")]][tel] <- ifelse(is.na(vals), SGS_MISSING, SGS_OBS)
    ya <- g$year[tel][!is.na(g[[paste0("growth_same_year_pct_", tag)]][tel])]
    yp <- g$year[tel][!is.na(vals)]
    comps_built[[tag]] <- list(built = length(ya) + length(yp) > 0, note = paste0(
      "telecom = the ", sub("telecom_", "", cn), " component (IBISWorld ", SGS$TELECOM_COMPONENT_CODES[[cn]], ") only: 07 actual ",
      if (length(ya)) sgs_years_text(ya) else "none", "; 06 component forecasts ", if (length(yp)) sgs_years_text(yp) else "none"))
  }
  ya <- act$year; yp <- pr$combined$year
  attr(g, "telecom") <- list(
    built = length(ya) + length(yp) > 0, components = comps_built,
    note = paste0(SGS_TELECOM_NOTE, ". Actual (07): ", if (length(ya)) paste0(sgs_years_text(ya), ", ", unique(act$how)[1],
                  "; year t-1 revenue weight of wireless ", sgs_py_fixed(min(act$w_wireless), 3), "-", sgs_py_fixed(max(act$w_wireless), 3)) else "no year with both components",
                  ". Predicted (06 component_forecasts): ", if (length(yp)) paste0(sgs_years_text(yp), ", ", paste(unique(pr$combined$how), collapse = "; "),
                  "; wireless weight ", sgs_py_fixed(min(pr$combined$w_wireless), 3), "-", sgs_py_fixed(max(pr$combined$w_wireless), 3),
                  " (the reports' scope changes move the weights: 06 marks the components aggregation_authorized = False)") else "no target year with both components",
                  "."))
  g
}

# One-year growth values that 06 holds for crypto and fintech outside the strict annual column (rulings of 2026-09-26:
# "use every sector-year that has one"): a one-year collected forecast of 06 data (forecast_horizon_years = 1) where
# predicted_growth_pct is blank, then a one-year component growth of 06 component_forecasts (published_growth_pct with a
# target year, not a CAGR). Each value placed carries its source in predicted_growth_flag.
.add_annual_proxies <- function(g, wbs) {
  secs <- c("crypto", "fintech")
  fr <- wbs$predicted$frames
  cand <- list()
  p6 <- fr$data
  cfg <- .num_col(p6, "collected_forecast_growth_pct"); hz <- .num_col(p6, "forecast_horizon_years")
  k <- which(p6$study_sector %in% secs & is.na(.num_col(p6, "predicted_growth_pct")) & !is.na(cfg) & hz %in% 1)
  for (i in k) {
    cand[[length(cand) + 1L]] <- list(study_sector = p6$study_sector[i], year = as.numeric(p6$year[i]), value = cfg[i],
                                      month = substr(.chr_col(p6, "forecast_known_available_by")[i], 1, 7),
                                      source = paste0("06 data collected_forecast_growth_pct, one-year (forecast_status ",
                                                      .chr_col(p6, "forecast_status")[i], ", forecast_method ",
                                                      .chr_col(p6, "forecast_method")[i], ", 06 row status ", p6$status[i],
                                                      "); a proxy, not the strict IBISWorld-comparable column"))
  }
  cf <- fr$component_forecasts
  if (!is.null(cf) && nrow(cf)) {
    ss <- tolower(trimws(.chr_col(cf, "study_sector")))
    pg <- .num_col(cf, "published_growth_pct"); ty <- .num_col(cf, "forecast_target_year"); cagr <- .num_col(cf, "published_cagr_pct")
    st <- .chr_col(cf, "status"); st[is.na(st)] <- SGS_OBS
    k <- which(ss %in% secs & !is.na(pg) & !is.na(ty) & is.na(cagr) & st %in% SGS_USABLE_STATUSES)
    for (i in k) {
      rec <- .chr_col(cf, "record_key")[i]; if (is.na(rec)) rec <- .chr_col(cf, "observation_id")[i]
      cand[[length(cand) + 1L]] <- list(study_sector = ss[i], year = ty[i], value = pg[i],
                                        month = substr(.chr_col(cf, "known_available_by")[i], 1, 7),
                                        source = paste0("06 component_forecasts ", rec, " (", .chr_col(cf, "provider")[i], ", ",
                                                        .chr_col(cf, "source_component")[i], ", available ",
                                                        .chr_col(cf, "known_available_by")[i], "): one-year component growth, ",
                                                        "not the broad sector"))
    }
  }
  g$predicted_growth_flag <- NA_character_
  placed <- character(0)
  for (c0 in cand) {
    i <- which(g$study_sector == c0$study_sector & g$year == c0$year)
    if (length(i) != 1L || !is.na(g$predicted_growth_pct[i])) next
    g$predicted_growth_pct[i] <- c0$value
    g$predicted_status[i] <- SGS_OBS
    g$forecast_publication_month[i] <- c0$month
    g$predicted_growth_flag[i] <- c0$source
    placed <- c(placed, paste0(c0$study_sector, " ", sgs_int_str(c0$year), " = ", sgs_py_repr_float(c0$value), " (", c0$source, ")"))
  }
  attr(g, "annual_proxies") <- list(built = length(placed) > 0, note = if (length(placed)) paste0(
    length(placed), " one-year growth value(s) of 06 placed in predicted_growth_pct: ", paste(placed, collapse = "; "))
    else "06 has no one-year growth value for crypto or fintech outside the strict column")
  g
}

# ASYM: <g>_pos = max(g, 0), <g>_neg = min(g, 0) (g = g_pos + g_neg), status of g. DECEL: <g>_decel = 1 when g_t <
# g_{t-1} in the same sector (both usable), <g>_x_decel = g x <g>_decel.
.add_asym_decel <- function(g) {
  key <- paste(g$study_sector, g$year)
  m <- match(paste(g$study_sector, g$year - 1), key)
  for (v in SGS_GROWTH_BASE_VARS) {
    x <- g[[v]]; st <- g[[SGS_STATUS_OF[[v]]]]
    g[[paste0(v, "_pos")]] <- ifelse(is.na(x), NA_real_, pmax(x, 0))
    g[[paste0(v, "_neg")]] <- ifelse(is.na(x), NA_real_, pmin(x, 0))
    xl <- x[m]; stl <- st[m]
    ok <- !is.na(x) & !is.na(xl) & st %in% SGS_USABLE_STATUSES & stl %in% SGS_USABLE_STATUSES
    dec <- ifelse(ok, as.numeric(x < xl), NA_real_)
    g[[paste0(v, "_decel")]] <- dec
    g[[paste0(v, "_x_decel")]] <- ifelse(ok, x * dec, NA_real_)
    g[[paste0(v, "_decel_status")]] <- ifelse(ok, SGS_OBS, ifelse(st %in% SGS_NA, SGS_NA, SGS_MISSING))
  }
  # CONTRACT (Paul: "if the industry contracted, they would spend more to meet their policy objectives"): 1 when the
  # industry contracted the year before (growth_previous_year_pct < 0), status of growth_previous_year_pct
  x <- g$growth_previous_year_pct
  g$contracted_prior <- ifelse(is.na(x), NA_real_, as.numeric(x < 0))
  g
}

# LobbyView rows of one unit of 01 lobbyview_sector_year_all that is not a study sector (community_banks), with the same
# filters as the study sectors (annual, confidence other than low, one row per year, thin flagged).
.lobbyview_unit_rows <- function(wbs, unit) {
  sh <- wbs$lobbying$frames[[SGS$LOBBYVIEW_ALL_SHEET]]
  if (is.null(sh)) return(NULL)
  ss <- .chr_col(sh, "study_sector")
  if ("sector" %in% names(sh)) ss[is.na(ss)] <- as.character(sh$sector)[is.na(ss)]
  keep <- ss %in% unit
  if ("period" %in% names(sh)) keep <- keep & (is.na(sh$period) | sh$period %in% "annual")
  if ("confidence" %in% names(sh)) keep <- keep & !(sh$confidence %in% "low")
  if (!any(keep)) return(NULL)
  s <- sh[keep, , drop = FALSE]
  if (anyDuplicated(s$year)) {
    sgs_raise("PanelError", paste0("01_lobbying_expenditures.xlsx [", SGS$LOBBYVIEW_ALL_SHEET, "]: more than one LobbyView row per ",
                                   unit, " x year after the filters; never summed"))
  }
  dedup <- SGS$LOBBYVIEW_DEDUP_COLUMN %in% names(s)
  undiff <- .num_col(s, "lobby_amount_undifferentiated_real_2025_usd") / 1e6
  primary <- if (dedup) .num_col(s, SGS$LOBBYVIEW_DEDUP_COLUMN) / 1e6 else undiff
  cov <- .chr_col(s, "coverage_flag")
  data.frame(year = as.numeric(s$year), status = s$status, undiff = undiff, primary = primary, thin = grepl("thin", cov, fixed = TRUE),
             cov = cov, confidence = .chr_col(s, "confidence"), stringsAsFactors = FALSE)
}

# LobbyView values of a bank-split unit (rows of .lobbyview_unit_rows) placed on its sector_year rows. keep_thin: thin
# sector-years stay usable in the primary amount (community banks: their "thin" flag, fewer than 5 clients, reflects
# lobbying through ICBA, not missing data); exclude_flag: sector-years whose coverage_flag carries it are unusable
# (community banks' id_merge years, when LobbyView merged America's Community Bankers into ICBA's client id).
.set_bank_lv <- function(df, lv, keep_thin, exclude_flag = NULL) {
  mm <- match(df$year, lv$year)
  st <- lv$status[mm]
  st[is.na(mm)] <- SGS_MISSING
  st[is.na(lv$primary[mm]) & st %in% SGS_USABLE_STATUSES] <- SGS_MISSING
  df$lobby_lv_real_m <- lv$primary[mm]
  df$lobby_lv_thin_real_m <- lv$primary[mm]
  df$lobby_amount_undiff_real_m <- lv$undiff[mm]
  for (col in c("lobby_lv_status", "lobby_lv_thin_status", "lobby_undiff_status")) df[[col]] <- st
  thin <- lv$thin[mm] %in% TRUE
  if (!keep_thin) {
    df$lobby_lv_status[thin & df$lobby_lv_status %in% SGS_USABLE_STATUSES] <- "thin"
    df$lobby_undiff_status[thin & df$lobby_undiff_status %in% SGS_USABLE_STATUSES] <- "thin"
  }
  if (!is.null(exclude_flag)) {
    ex <- grepl(exclude_flag, lv$cov[mm], fixed = TRUE)
    for (col in c("lobby_lv_status", "lobby_lv_thin_status", "lobby_undiff_status")) {
      df[[col]][ex & df[[col]] %in% SGS_USABLE_STATUSES] <- exclude_flag
    }
  }
  df$lobby_lv_coverage_flag <- lv$cov[mm]
  df
}

SGS_BANK_LV_BIG <- "commercial_banks_ex_community"
SGS_BANK_LV_NOTE <- paste0("LobbyView bank split: big_banks = 01 ", SGS$LOBBYVIEW_ALL_SHEET, " commercial_banks_ex_community (the bank ",
                           "series minus the community-bank clients), community_banks = its community_banks rows (confidence ",
                           "roster: ICBA, the community-banker associations and 2 roster banks); community banks lobby almost ",
                           "entirely through ICBA, so their thin flag (fewer than 5 clients) reflects that association structure, ",
                           "not missing data, and their thin years are KEPT; their id_merge years (2006-2007 in real dollars: ",
                           "LobbyView merged America's Community Bankers into ICBA's client id) are excluded. Never combined with ",
                           "the old commercial_banks series, which includes ICBA (a double count); the main L-LV tests keep it.")

# Bank split (Paul, 2026-09-26): sector_year with commercial_banks (Mentat "banking", big banks) renamed big_banks and
# a community_banks unit added from 04. LobbyView: when 01 lobbyview_sector_year_all has both commercial_banks_ex_community
# and community_banks rows, big_banks takes the former and community_banks the latter (see SGS_BANK_LV_NOTE). Both
# banks carry the commercial-banking growth series (IBISWorld 52211) and the national controls; everything else
# sector-specific that community banks do not have is blank (not applicable).
sgs_build_sector_year_banks <- function(wbs, sy) {
  big <- SGS$BANK_SPLIT_BIG; com <- SGS$BANK_SPLIT_COMMUNITY
  cb <- sy[sy$study_sector == "commercial_banks", , drop = FALSE]
  b <- cb; b$study_sector <- big
  cm <- cb; cm$study_sector <- com
  own <- names(sy)[grepl("^(contributions|company_pac|lobby_|dem_share)", names(sy))]
  for (col in own) {
    if (endsWith(col, "_status")) cm[[col]] <- SGS_NA
    else if (is.numeric(cm[[col]])) cm[[col]] <- NA_real_
    else cm[[col]] <- NA
  }
  d4 <- wbs$spending$frames$data
  agg <- .agg_04(d4[d4$study_sector %in% com, , drop = FALSE])
  sy4 <- wbs$spending$frames$sector_year
  sy4 <- sy4[sy4$study_sector %in% com, c("study_sector", "year", "giving_real_2025_usd", "status"), drop = FALSE]
  .chk_04_sums(sy4, agg)
  cm$contributions_real_m <- agg$contributions_real_m[match(cm$year, agg$year)]
  st <- sy4$status[match(cm$year, sy4$year)]
  cm$contributions_status <- ifelse(is.na(st), SGS_MISSING, st)
  cm$contributions_status[is.na(cm$contributions_real_m) & cm$contributions_status %in% SGS_USABLE_STATUSES] <- SGS_MISSING
  lvb <- .lobbyview_unit_rows(wbs, SGS_BANK_LV_BIG)
  lvc <- .lobbyview_unit_rows(wbs, com)
  has_lv <- !is.null(lvb) && nrow(lvb) > 0 && !is.null(lvc) && nrow(lvc) > 0
  if (has_lv) {
    b <- .set_bank_lv(b, lvb, keep_thin = FALSE)
    cm <- .set_bank_lv(cm, lvc, keep_thin = TRUE, exclude_flag = "id_merge")
  }
  out <- rbind(b, cm, sy[sy$study_sector != "commercial_banks", , drop = FALSE])  # big banks first: the cluster order
  rownames(out) <- NULL
  ny <- sum(!is.na(cm$contributions_real_m) & cm$contributions_status %in% SGS_USABLE_STATUSES)
  lv_note <- if (has_lv) {
    use <- cm$lobby_lv_status %in% SGS_USABLE_STATUSES & !is.na(cm$lobby_lv_real_m)
    idm <- cm$year[cm$lobby_lv_status %in% "id_merge"]
    paste0(SGS_BANK_LV_NOTE, " community_banks: ", nrow(lvc), " rows (confidence ", paste(unique(lvc$confidence), collapse = ", "),
           "), usable ", if (any(use)) sgs_years_text(cm$year[use]) else "none", if (length(idm)) paste0(", id_merge excluded ",
           sgs_years_text(idm)) else "", "; big_banks: ", nrow(lvb), " ", SGS_BANK_LV_BIG, " rows")
  } else {
    missing <- c(if (is.null(lvb) || !nrow(lvb)) SGS_BANK_LV_BIG, if (is.null(lvc) || !nrow(lvc)) com)
    paste0("01 ", SGS$LOBBYVIEW_ALL_SHEET, " has no ", paste(missing, collapse = " / "), " rows yet")
  }
  attr(out, "built") <- list(
    bank_split = list(built = ny > 0, note = paste0(
      "big_banks = 04 Mentat 'banking' (the commercial_banks sector); community_banks = 04 Mentat 'community_banks' (",
      ny, " observed sector-years); both carry the commercial-banking growth series (IBISWorld 52211), so the split ",
      "compares the spending response of the two bank groups to the same growth")),
    lobbyview_community_banks = list(built = has_lv, note = lv_note))
  out
}

# ---- expected control ---------------------------------------------------------------------------------------------

.txt <- function(v) {
  if (is.null(v) || length(v) == 0L || is.na(v) || (is.character(v) && !nzchar(trimws(v)))) return(NA_character_)
  as.character(v)
}

# panel.market_annual: 02 expected_control_markets (daily rows) -> annual means for the fill years (parity rule set
# only; Paul's rulings never read the sheet).
sgs_market_annual <- function(m, years = SGS$EXPECTED_CONTROL_FILL_YEARS) {
  label <- paste0("02_election_forecasting.xlsx [", SGS$EXPECTED_CONTROL_MARKETS_SHEET, "]")
  if (!"p_dem_control" %in% names(m) && !"p_rep_control" %in% names(m)) {
    sgs_raise("PanelError", paste0(label, ": needs a p_dem_control or p_rep_control column"))
  }
  num <- function(v) suppressWarnings(as.numeric(v))
  p <- if ("p_dem_control" %in% names(m)) num(m$p_dem_control) else rep(NA_real_, nrow(m))
  if ("p_rep_control" %in% names(m)) p <- ifelse(!is.na(p), p, 1.0 - num(m$p_rep_control))
  ok <- !is.na(p) & m$status %in% SGS_USABLE_STATUSES
  if ("before_election_day" %in% names(m)) ok <- ok & (num(m$before_election_day) %in% 1)
  d <- as.Date(substr(as.character(m$date), 1, 10), format = "%Y-%m-%d")
  ok <- ok & !is.na(d)
  out <- list()
  sub <- which(ok & !is.na(m$calendar_year) & !is.na(m$chamber))
  if (!length(sub)) return(out)
  key <- data.frame(y = num(m$calendar_year[sub]), ch = m$chamber[sub], stringsAsFactors = FALSE)
  gr <- sgs_groups(key, c("y", "ch"))
  for (gi in seq_along(gr$index)) {
    ix <- sub[gr$index[[gi]]]
    y <- gr$keys$y[gi]; ch <- gr$keys$ch[gi]
    if (!(years[1] <= y && y <= years[2])) next
    first <- min(d[ix]); last <- max(d[ix])
    flag <- if (as.numeric(format(last, "%Y")) > y) {
      paste0("measured ", month.abb[as.integer(format(last, "%m"))], " ", format(last, "%Y"), ", after the year")
    } else NA
    mkts <- paste(sort(unique(as.character(m$market[ix])), method = "radix"), collapse = ", ")
    out[[paste(y, ch)]] <- list(year = y, chamber = ch, exp_dem = sgs_np_sum(p[ix]) / length(ix), status = SGS_OBS,
                                method = "market_daily_mean", flag = flag,
                                source = paste0("02 ", SGS$EXPECTED_CONTROL_MARKETS_SHEET, ": ", length(ix), " daily rows ",
                                                format(first, "%Y-%m-%d"), "..", format(last, "%Y-%m-%d"), " (", mkts, ")"),
                                measured_at = format(last, "%Y-%m-%d"))
  }
  out
}

# Expected Democratic control by calendar year x chamber: year, chamber, exp_dem, status, method, flag, source.
#   parity rule set (panel.expected_control): every year the IEM annual mean of 02 data (method iem_annual_mean) where
#     present and usable; for 2023-2026, in order: 02 expected_control_markets (when the sheet exists), the IEM value,
#     02 expected_control_2023_2026.
#   Paul's rulings: 2008-2022 the IEM annual mean; 2023-2026 02 expected_control_2023_2026 (method and flag as the
#     sheet states them), the IEM value only where the sheet has no usable row; the markets sheet is never read.
sgs_expected_control <- function(wbs, rules = sgs_rules()) {
  frames <- wbs$election$frames
  lo <- SGS$EXPECTED_CONTROL_FILL_YEARS[1]; hi <- SGS$EXPECTED_CONTROL_FILL_YEARS[2]
  rows <- list()
  d <- frames$data
  for (i in seq_len(nrow(d))) {
    y <- as.numeric(d$calendar_year[i]); ch <- d$chamber[i]
    usable <- !is.na(d$p_dem_expected[i]) && d$status[i] %in% SGS_USABLE_STATUSES
    # measured_at (chronology): the IEM annual mean is known once its last daily price is (02 data last_price_date)
    lp <- if ("last_price_date" %in% names(d)) sgs_date_text(d$last_price_date[i]) else NA_character_
    rows[[paste(y, ch)]] <- list(year = y, chamber = ch, exp_dem = if (usable) as.numeric(d$p_dem_expected[i]) else NA_real_,
                                 status = d$status[i], method = if (usable) "iem_annual_mean" else NA_character_,
                                 flag = NA_character_, source = if (usable) "02 data (IEM annual mean)" else NA_character_,
                                 measured_at = if (usable) lp else NA_character_)
  }
  fill <- frames[[SGS$EXPECTED_CONTROL_SHEET]]
  markets <- if (isTRUE(rules$read_markets)) frames[[SGS$EXPECTED_CONTROL_MARKETS_SHEET]] else NULL
  mk <- if (!is.null(markets)) sgs_market_annual(markets) else list()
  fill_row <- function(y, ch) {
    if (is.null(fill)) return(NULL)
    m <- which(suppressWarnings(as.numeric(fill$calendar_year)) %in% y & fill$chamber %in% ch)
    if (!length(m)) return(NULL)
    r <- fill[m[1], , drop = FALSE]
    if (is.na(r$exp_dem) || !(r$status %in% SGS_USABLE_STATUSES)) return(NULL)
    list(year = y, chamber = ch, exp_dem = as.numeric(r$exp_dem), status = r$status, method = .txt(r$method),
         flag = .txt(r$flag), source = paste0("02 ", SGS$EXPECTED_CONTROL_SHEET, " (", .txt(r$source_id), ")"),
         measured_at = if ("measured_on" %in% names(r)) sgs_date_text(r$measured_on) else NA_character_)
  }
  for (y in lo:hi) {
    for (ch in c("House", "Senate")) {
      key <- paste(y, ch)
      if (!is.null(mk[[key]])) { rows[[key]] <- mk[[key]]; next }
      cur <- rows[[key]]
      if (isTRUE(rules$fill_sheet_first)) {
        fr <- fill_row(y, ch)
        if (!is.null(fr)) { rows[[key]] <- fr; next }
        next
      }
      if (!is.null(cur) && !is.na(cur$exp_dem)) next
      fr <- fill_row(y, ch)
      if (!is.null(fr)) rows[[key]] <- fr
    }
  }
  out <- sgs_rows_df(unname(rows), c("year", "chamber", "exp_dem", "status", "method", "flag", "source", "measured_at"))
  out$year <- as.numeric(out$year)
  out$exp_dem <- as.numeric(out$exp_dem)
  out <- out[order(out$chamber, out$year, method = "radix"), , drop = FALSE]
  rownames(out) <- NULL
  out
}

# ---- industry_year (H1-PV) ------------------------------------------------------------------------------------------

sgs_build_industry_year <- function(wbs) {
  sy4 <- wbs$spending$frames$sector_year
  u0 <- unique(sy4$study_sector)
  units <- u0[order(ifelse(u0 %in% SGS$STUDY_SECTORS, match(u0, SGS$STUDY_SECTORS) - 1L, 99L), u0, method = "radix")]
  g <- expand.grid(year = sgs_panel_years(), study_sector = units, stringsAsFactors = FALSE)
  g <- data.frame(study_sector = g$study_sector, year = as.numeric(g$year), stringsAsFactors = FALSE)
  g$partial_year <- g$year %in% SGS$PARTIAL_YEARS
  if ("mentat_industry" %in% names(sy4)) {
    first <- sy4[!duplicated(sy4$study_sector), , drop = FALSE]
    g$mentat_industry <- first$mentat_industry[match(g$study_sector, first$study_sector)]
  } else {
    g$mentat_industry <- g$study_sector
  }
  g$is_study_sector <- g$study_sector %in% SGS$STUDY_SECTORS
  c0 <- wbs$controls$frames$data
  g <- sgs_left_join(g, data.frame(year = c0$year, pres_year = c0$presidential_year, midterm_year = c0$midterm_year),
                     "year")
  g$controls_status <- ifelse(!is.na(g$pres_year) & !is.na(g$midterm_year), SGS_OBS, SGS_MISSING)
  agg <- .agg_04(wbs$spending$frames$data)
  .chk_04_sums(sy4, agg)
  g <- sgs_left_join(g, agg, c("study_sector", "year"))
  g <- sgs_left_join(g, data.frame(study_sector = sy4$study_sector, year = sy4$year, `_c_status` = sy4$status,
                                   check.names = FALSE, stringsAsFactors = FALSE), c("study_sector", "year"))
  g <- .status_fill(g, "contributions_status", units, "_c_status", "contributions_real_m")
  g <- .drop_private(g)
  if (anyDuplicated(sgs_key_of(g, c("study_sector", "year")))) sgs_raise("PanelError", "industry_year: duplicate unit x year rows")
  rownames(g) <- NULL
  g
}

# ---- sector_year_tier ------------------------------------------------------------------------------------------------

sgs_build_sector_year_tier <- function(wbs, sector_year) {
  t4 <- wbs$spending$frames$tier_by_year
  t4 <- t4[t4$study_sector %in% SGS$STUDY_SECTORS, , drop = FALSE]
  t4$employee_tier[is.na(t4$employee_tier)] <- "(blank)"
  unknown <- sort(setdiff(unique(t4$employee_tier), c(SGS$TIERS, "(blank)")), method = "radix")
  if (length(unknown)) {
    sgs_raise("PanelError", paste0("04_campaign_spending.xlsx [tier_by_year] column employee_tier: unknown tiers ",
                                   sgs_py_list_repr(unknown)))
  }
  rank <- c(observed = 0, derived = 0, partial = 1, missing = 2)
  gr <- sgs_groups(t4, c("study_sector", "year", "employee_tier"))
  has_gifts <- "gifts" %in% names(t4)
  agg <- gr$keys
  agg$contributions_real_m <- vapply(gr$index, function(ix) sgs_nansum(t4$giving_real_2025_usd[ix], 1L) / 1e6, 0)
  agg$gifts <- vapply(gr$index, function(ix) {
    if (has_gifts) sgs_kahan_sum(t4$gifts[ix], 0L) else as.numeric(length(ix))
  }, 0)
  agg$`_st` <- vapply(gr$index, function(ix) {
    s <- t4$status[ix]
    r <- ifelse(s %in% names(rank), rank[s], 3)
    s[which.max(r)]
  }, "")
  # reconcile: tiers (including any blank tier) add up to the sector-year total
  tot <- sgs_group_sum(agg, c("study_sector", "year"), "contributions_real_m", min_count = 1L, name = "_tier_total")
  chk <- sgs_left_join(sector_year[, c("study_sector", "year", "contributions_real_m", "contributions_status")], tot,
                       c("study_sector", "year"))
  chk <- chk[chk$contributions_status %in% SGS_OBS, , drop = FALSE]
  tt <- ifelse(is.na(chk$`_tier_total`), 0, chk$`_tier_total`)
  bad <- abs(tt - chk$contributions_real_m) > 1e-6
  bad[is.na(bad)] <- FALSE
  if (any(bad)) {
    sgs_raise("PanelError", paste0("04 tier_by_year totals disagree with the data sheet by more than $1: ",
                                   sgs_records_repr(chk[bad, c("study_sector", "year"), drop = FALSE])))
  }
  grid <- expand.grid(tier = SGS$TIERS, year = sgs_panel_years(), study_sector = SGS$STUDY_SECTORS, stringsAsFactors = FALSE)
  grid <- data.frame(study_sector = grid$study_sector, year = as.numeric(grid$year), tier = grid$tier, stringsAsFactors = FALSE)
  names(agg)[names(agg) == "employee_tier"] <- "tier"
  grid <- sgs_left_join(grid, agg, c("study_sector", "year", "tier"))
  grid$tier_row_present <- !is.na(grid$`_st`)
  cst <- sector_year$contributions_status[match(paste(grid$study_sector, grid$year),
                                                paste(sector_year$study_sector, sector_year$year))]
  zero <- !grid$tier_row_present & cst %in% SGS_OBS
  grid$contributions_real_m[zero] <- 0
  grid$gifts[zero] <- 0
  grid$contributions_status <- ifelse(grid$tier_row_present, grid$`_st`, cst)
  grid$contributions_status[zero] <- SGS_OBS
  grid$`_st` <- NULL
  drop <- c("contributions_real_m", "contributions_status", "lobby_income_real_m", "lobby_expenses_real_m",
            "lobby_amount_undiff_real_m", "lobby_income_status", "lobby_expenses_status", "lobby_undiff_status")
  drop <- c(drop, grep("^(contributions_dedup|company_pac|dem_share|lobby_lv)", names(sector_year), value = TRUE))
  carry <- setdiff(names(sector_year), drop)
  out <- sgs_left_join(grid, sector_year[, carry, drop = FALSE], c("study_sector", "year"))
  if (anyDuplicated(sgs_key_of(out, c("study_sector", "year", "tier")))) {
    sgs_raise("PanelError", "sector_year_tier: duplicate study_sector x year x tier rows")
  }
  rownames(out) <- NULL
  out
}

# PAC overlap table (Paul's ruling 4): per 04 unit x year, general giving, the part given to the roster company's
# own PAC (recipient_category 'Company PAC') and its share; also the pooled 2021-2025 nominal share.
sgs_pac_overlap <- function(wbs) {
  d4 <- wbs$spending$frames$data
  pac <- d4$recipient_category %in% SGS$COMPANY_PAC_CATEGORY
  gr <- sgs_groups(d4, c("study_sector", "year"))
  out <- gr$keys
  out$general_giving_nominal_usd <- vapply(gr$index, function(ix) sgs_kahan_sum(d4$giving_nominal_usd[ix], 1L), 0)
  out$company_pac_nominal_usd <- vapply(gr$index, function(ix) sgs_kahan_sum(d4$giving_nominal_usd[ix][pac[ix]], 0L), 0)
  out$general_giving_real_m <- vapply(gr$index, function(ix) sgs_kahan_sum(d4$giving_real_2025_usd[ix], 1L), 0) / 1e6
  out$company_pac_real_m <- vapply(gr$index, function(ix) sgs_kahan_sum(d4$giving_real_2025_usd[ix][pac[ix]], 0L), 0) / 1e6
  out$company_pac_share_nominal <- ifelse(out$general_giving_nominal_usd != 0,
                                          out$company_pac_nominal_usd / out$general_giving_nominal_usd, NA_real_)
  out$company_pac_rows <- vapply(gr$index, function(ix) sum(pac[ix]), 0)
  out$rows <- vapply(gr$index, function(ix) length(ix), 0)
  out$status <- vapply(gr$index, function(ix) if (all(d4$status[ix] %in% SGS_OBS)) SGS_OBS else SGS_PARTIAL, "")
  out$is_study_sector <- out$study_sector %in% SGS$STUDY_SECTORS
  out <- out[order(sgs_sector_rank(out$study_sector), out$study_sector, out$year, method = "radix"), , drop = FALSE]
  sel <- d4$year >= 2021 & d4$year <= 2025
  ss <- d4$study_sector %in% SGS$STUDY_SECTORS
  pooled <- list(
    all_units = sum(d4$giving_nominal_usd[sel & pac], na.rm = TRUE) / sum(d4$giving_nominal_usd[sel], na.rm = TRUE),
    study_sectors = sum(d4$giving_nominal_usd[sel & pac & ss], na.rm = TRUE) / sum(d4$giving_nominal_usd[sel & ss], na.rm = TRUE))
  rownames(out) <- NULL
  attr(out, "pooled") <- pooled
  out
}

# Status column of every analysis variable (the sample builder excludes partial / unusable values).
SGS_STATUS_OF <- c(
  contributions_real_m = "contributions_status",
  lobby_income_real_m = "lobby_income_status",
  lobby_expenses_real_m = "lobby_expenses_status",
  lobby_amount_undiff_real_m = "lobby_undiff_status",
  lobby_lv_real_m = "lobby_lv_status",
  lobby_lv_thin_real_m = "lobby_lv_thin_status",
  growth_same_year_pct = "growth_same_status",
  growth_previous_year_pct = "growth_prev_status",
  predicted_growth_pct = "predicted_status",
  pres_year = "controls_status",
  midterm_year = "controls_status",
  exp_dem_house = "exp_dem_house_status",
  exp_dem_senate = "exp_dem_senate_status",
  cur_dem_house = "cur_dem_house_status",
  cur_dem_senate = "cur_dem_senate_status",
  exp_shift_house = "exp_shift_house_status",
  exp_shift_senate = "exp_shift_senate_status",
  pred_dem_seat_change_house = "seat_calls_house_status",
  pred_dem_seat_change_senate = "seat_calls_senate_status",
  contributions_dedup_real_m = "contributions_dedup_status",
  gb538_margin_house = "gb538_margin_house_status",
  predicted_growth_multiyear_pct = "predicted_multiyear_status",
  dem_share_house = "dem_share_house_status",
  dem_share_senate = "dem_share_senate_status",
  dem_share_hill_house = "dem_share_hill_house_status",
  dem_share_hill_senate = "dem_share_hill_senate_status"
)

# Rulings of 2026-09-26: the derived growth columns of ASYM (<g>_pos, <g>_neg: the status of g), DECEL (<g>_decel,
# <g>_x_decel: usable when g_t and g_{t-1} are) and the telecom component variants (<g>_tw, <g>_tc).
SGS_GROWTH_BASE_VARS <- c("growth_previous_year_pct", "growth_same_year_pct", "predicted_growth_pct")
for (.v in SGS_GROWTH_BASE_VARS) {
  SGS_STATUS_OF[paste0(.v, "_pos")] <- SGS_STATUS_OF[[.v]]
  SGS_STATUS_OF[paste0(.v, "_neg")] <- SGS_STATUS_OF[[.v]]
  SGS_STATUS_OF[paste0(.v, "_decel")] <- paste0(.v, "_decel_status")
  SGS_STATUS_OF[paste0(.v, "_x_decel")] <- paste0(.v, "_decel_status")
  for (.t in SGS$TELECOM_COMPONENT_TAGS) SGS_STATUS_OF[paste0(.v, "_", .t)] <- paste0(.v, "_", .t, "_status")
}
rm(.v, .t)
SGS_STATUS_OF["contracted_prior"] <- SGS_STATUS_OF[["growth_previous_year_pct"]]
# SHIFT (rulings of 2026-09-26): the stacked table's DVs and own-chamber control, the all-giving share, and the dollar
# bases used as weights (usable with their share)
SGS_STATUS_OF["dem_share_all"] <- "dem_share_all_status"
SGS_STATUS_OF["dem_share"] <- "dem_share_status"
SGS_STATUS_OF["dem_share_hill"] <- "dem_share_hill_status"
SGS_STATUS_OF["exp_dem_own_chamber"] <- "exp_dem_own_chamber_status"
SGS_STATUS_OF["cur_dem_own_chamber"] <- "cur_dem_own_chamber_status"
for (.d in c("dem_share_house", "dem_share_senate", "dem_share_hill_house", "dem_share_hill_senate", "dem_share", "dem_share_hill",
             "dem_share_all")) {
  SGS_STATUS_OF[paste0(.d, "_base_real_m")] <- SGS_STATUS_OF[[.d]]
}
rm(.d)
