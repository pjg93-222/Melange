# Frozen, explicit registry of every test of the study (R port of code/sgs/registry.py; plan sections 2, 3, 5, 9).
#
# Each test spec names its DV, focal regressors, controls, fixed effects, sample-window rule and label. Labels: CORE
# (the six core tests, nine DV runs), EXTENSION, ROBUSTNESS, EXPLORATORY, DESCRIPTIVE (estimate and HC1 reference
# errors only, no inference), PREVIEW (fixed window 2021-2025, below the 6-year minimum).
# The parity rule set builds the 139 tests of the Python package, in its order. Paul's rulings (rule set
# paul-2026-09-25) change that registry:
#   * DS-House-C1..C3 and DS-Senate-C1..C3 (08 sector_year_chamber) replace the DS-House / DS-Senate stubs;
#   * L1-LV..L3-LV read 01 lobbyview_sector_year_all (every study sector, every year), bootstrap inference with >= 3
#     sector clusters (DESCRIPTIVE with 2), fallback window = the whole qualifying run (no 10-year cap);
#   * H4-538-<core>: the 02 expected_control_538 House generic-ballot margin in place of exp_dem_house (ROBUSTNESS);
#   * R-dedup-C1..C3: contributions without gifts to a roster company's own PAC (ROBUSTNESS);
#   * MY-C3, MY-L3-income, MY-L3-expenses, MY-L3-LV: compliant (i), multi-year projections (EXPLORATORY);
#   * every test with a growth regressor carries the flag "growth = whole industry (IBISWorld); spending = 10-company
#     roster".

SGS_WINDOW_RULE <- paste0("primary 2020-2025 (>= 6 distinct years); only if it fails, fallback = the most recent run of ",
                          ">= 10 consecutive calendar years within 2008-2025 with a complete-case sample (its most recent 10 years)")
SGS_H5_GATE_RULE <- paste0("H5 gate (member-cycle based, not the 6-year sector-year gate): >= 3 cycles, >= 30 member-cycles ",
                           "(distinct bioguide x cycle), non-zero variance of the focal regressor (within champion for H5-within), ",
                           "focal identified, residual df >= 3, >= 2 champion clusters")
SGS_LV_NOTE <- "2 sectors: wild cluster bootstrap cannot reach p < 0.056; inference not available"
SGS_PREVIEW_RULE <- paste0("PREVIEW gate: fixed window ", SGS$PREVIEW_WINDOW[1], "-", SGS$PREVIEW_WINDOW[2],
                           " (5 full years, below Paul's 6-year minimum), >= ", SGS$PREVIEW_MIN_YEARS, " distinct years, >= ",
                           SGS$MIN_SECTORS, " sectors, full-rank design, residual df >= ", SGS$MIN_RESID_DF, "; no fallback; ",
                           "full core specification NOT IDENTIFIED when year-level parameters >= distinct years")
SGS_LV_WINDOW_RULE <- paste0("primary 2020-2025 (>= 6 distinct years); only if it fails, fallback = the most recent run of ",
                             ">= 10 consecutive calendar years within 2008-2025 with a complete-case sample, used whole ",
                             "(LobbyView: no 10-year cap; Paul: \"no Lobbyview can go all the way\")")

SGS_GROWTH <- c("1" = "growth_previous_year_pct", "2" = "growth_same_year_pct", "3" = "predicted_growth_pct")
SGS_GROWTH_VARS <- c(unname(SGS_GROWTH), "predicted_growth_multiyear_pct")
SGS_C_CONTROLS <- c("pres_year", "midterm_year", "exp_dem_house", "exp_dem_senate")
SGS_L_CONTROLS <- c(SGS_C_CONTROLS, "cur_dem_house", "cur_dem_senate")
SGS_DVS <- c(contributions = "contributions_real_m", lobby_income = "lobby_income_real_m",
             lobby_expenses = "lobby_expenses_real_m")

# A test spec (registry.TestSpec) with the Python defaults; extra fields of Paul's rulings default to "off".
sgs_test_spec <- function(id, family, label, dv, focal = character(0), controls = character(0), fe = "sector",
                          variant = "level", table = "sector_year", base = NA_character_, year_filter = NA_character_,
                          tiers = NULL, interactions = list(), note = "", window_rule = SGS_WINDOW_RULE,
                          inference = "wcr", dv_transform = "level", drop_cycles = numeric(0), keep_lost_primary = FALSE,
                          flag = "", unit = "sector x year", gate = "r8", saturation_check = FALSE,
                          requires = character(0), fallback_whole_run = FALSE, min_clusters_inference = NA_integer_,
                          dv_label = NA_character_, equality = character(0), sectors = NULL, drop_singletons = FALSE,
                          near_collinear_r2 = NA_real_, count_var = NA_character_, count_kind = NA_character_,
                          joint = list(), weight_var = NA_character_, carry = character(0), trend_group = NA_character_,
                          predicted_sign = character(0), identification = FALSE, preview_min_years = NA_integer_,
                          min_base = NA_real_, base_var = NA_character_, matched = FALSE, matched_transform = "none",
                          strict_time = FALSE, dv_unit = NA_character_) {
  list(id = id, family = family, label = label, dv = dv, focal = as.character(focal), controls = as.character(controls),
       fe = as.character(fe), variant = variant, table = table, base = base, year_filter = year_filter, tiers = tiers,
       interactions = interactions, note = note, window_rule = window_rule, inference = inference,
       dv_transform = dv_transform, drop_cycles = drop_cycles, keep_lost_primary = keep_lost_primary, flag = flag,
       unit = unit, gate = gate, saturation_check = saturation_check, requires = requires,
       fallback_whole_run = fallback_whole_run, min_clusters_inference = min_clusters_inference, dv_label = dv_label,
       # rulings of 2026-09-26 (all off in the parity rule set): equality = two focal terms tested for equality (ASYM);
       # sectors = the units a test keeps (bank-only models); drop_singletons = leave out a sector with one complete
       # sector-year from fixed-effect samples; near_collinear_r2 = the near-collinearity threshold (H5);
       # count_var / count_kind = the growth variable whose declines (g < 0) or decelerations (g_t < g_{t-1}) are
       # counted per sector in the test's sample
       equality = as.character(equality), sectors = sectors, drop_singletons = drop_singletons,
       near_collinear_r2 = near_collinear_r2, count_var = count_var, count_kind = count_kind,
       # joint = the joint tests of a per-sector design: list(list(kind = "equal" | "zero", var, label, key))
       joint = joint,
       # SHIFT / TRENDS (rulings of 2026-09-26; all off unless set): weight_var = the column whose values weight the rows
       # (weighted least squares); carry = columns a first-difference sample keeps from the year-t row (dollar bases,
       # input flags); trend_group = the test whose variants this one is compared with in TRENDS; predicted_sign = the
       # sign the stated hypothesis predicts, named by focal term ("+" / "-"); identification = report how the year-level
       # focal term is identified (year-level parameters, residual df, the OLS weight of each year); preview_min_years =
       # the PREVIEW gate's minimum distinct years when it is not SGS$PREVIEW_MIN_YEARS (first-difference previews)
       weight_var = weight_var, carry = as.character(carry), trend_group = trend_group, predicted_sign = predicted_sign,
       identification = identification, preview_min_years = preview_min_years,
       # coordinator's revisions of 2026-09-26: min_base / base_var = the SHIFT minimum base of the EXPLORATORY
       # post-result variants (rows whose nominal D + R dollars base_var are below min_base leave the sample, counted and
       # listed); matched = the test is fitted on its base test's gated sample (L-LV robustness, as the Codex review),
       # transformed by matched_transform ("none", "log", "fd_pairs": consecutive years both in the base sample);
       # strict_time = expected-control values measured after their year are not usable (STRICT)
       min_base = min_base, base_var = base_var, matched = matched, matched_transform = matched_transform,
       strict_time = strict_time,
       # dv_unit = the DV's unit when the default ($M 2025 / Democratic share) does not fit (SEATS)
       dv_unit = dv_unit)
}

sgs_spec_update <- function(spec, ...) {
  kw <- list(...)
  for (k in names(kw)) spec[k] <- list(kw[[k]])
  spec
}

# Panel variables the design needs (before interactions / transformations).
sgs_raw_regressors <- function(spec) {
  if (spec$variant %in% c("tier", "sector_interaction")) {
    return(unique(c(vapply(spec$interactions, `[[`, "", 1), spec$controls)))
  }
  unique(c(spec$focal, spec$controls))
}

# A growth regressor, or a column derived from one (ASYM _pos / _neg, DECEL _decel / _x_decel, telecom _tw / _tc).
sgs_is_growth_var <- function(v) {
  v %in% c(SGS_GROWTH_VARS, "contracted_prior") |
    grepl("^(growth_previous_year_pct|growth_same_year_pct|predicted_growth_pct)_(pos|neg|decel|x_decel|tw|tc)$", v)
}

sgs_required_vars <- function(spec) {
  w <- spec$weight_var %||% NA_character_
  c(spec$dv, sgs_raw_regressors(spec), if (length(w) == 1L && !is.na(w)) w)
}

.core <- function() {
  out <- list()
  for (k in c("1", "2", "3")) {
    out[[length(out) + 1L]] <- sgs_test_spec(id = paste0("C", k), family = "C", label = "CORE", dv = "contributions_real_m",
                                             focal = SGS_GROWTH[[k]], controls = SGS_C_CONTROLS)
  }
  for (k in c("1", "2", "3")) {
    for (dvkey in names(SGS_DVS)[-1]) {
      out[[length(out) + 1L]] <- sgs_test_spec(id = paste0("L", k, "-", strsplit(dvkey, "_")[[1]][2]), family = "L",
                                               label = "CORE", dv = SGS_DVS[[dvkey]], focal = SGS_GROWTH[[k]],
                                               controls = SGS_L_CONTROLS)
    }
  }
  out
}

.replace_exp <- function(controls, new) {
  out <- controls
  out[controls == "exp_dem_house"] <- new[1]
  out[controls == "exp_dem_senate"] <- new[2]
  out
}

.lobbyview <- function(rules) {
  out <- list()
  paul <- identical(rules$lobbyview, "all_sectors")
  for (k in c("1", "2", "3")) {
    if (!paul) {
      out[[length(out) + 1L]] <- sgs_test_spec(
        id = paste0("L", k, "-LV"), family = "L-LV", label = "DESCRIPTIVE", dv = "lobby_amount_undiff_real_m",
        focal = SGS_GROWTH[[k]], controls = SGS_L_CONTROLS, inference = "none",
        note = paste0("LobbyView undifferentiated amount, high-confidence classification (commercial_banks and credit_unions ",
                      "only); L-test controls and sector baselines; gated through the fallback window. DESCRIPTIVE: ",
                      "coefficients and HC1 errors (reference only); ", SGS_LV_NOTE, ". Never added to LDA amounts."))
    } else {
      lv <- function(id, family, label, dv, note, requires, base = NA_character_) sgs_test_spec(
        id = id, family = family, label = label, dv = dv, focal = SGS_GROWTH[[k]], controls = SGS_L_CONTROLS,
        inference = "wcr", min_clusters_inference = SGS$LOBBYVIEW_MIN_CLUSTERS_INFERENCE, fallback_whole_run = TRUE,
        window_rule = SGS_LV_WINDOW_RULE, requires = requires, base = base, note = note)
      common <- paste0("01 ", SGS$LOBBYVIEW_ALL_SHEET, ", every study sector and every year available (Paul: \"no ",
                       "Lobbyview can go all the way\"), one row per sector-year (confidence high for banks and credit ",
                       "unions, roster for crypto and fintech, naics for the other sectors; low never enters); L-test ",
                       "controls and sector baselines; the normal window rule, with the fallback window taken as the whole ",
                       "qualifying run; wild cluster bootstrap inference with >= 3 sector clusters, DESCRIPTIVE with 2. A ",
                       "separate series and family: never added to LDA amounts.")
      out[[length(out) + 1L]] <- lv(paste0("L", k, "-LV"), "L-LV", "CORE", "lobby_lv_real_m",
                                    paste0("LobbyView primary amount (the de-duplicated amount; only if 01 lacked the ",
                                           "de-duplicated column would the undifferentiated sum stand in, and the DV label ",
                                           "would say so), thin sector-years excluded; ", common), "lobbyview_all")
      out[[length(out) + 1L]] <- lv(paste0("R-LV-undiff-L", k), "L-LV", "ROBUSTNESS", "lobby_amount_undiff_real_m",
                                    paste0("Robustness of L", k, "-LV: the undifferentiated LobbyView sum (double counts ",
                                           "the outside-firm fees of self-filers), thin sector-years excluded; ", common),
                                    c("lobbyview_all", "lobbyview_dedup"), base = paste0("L", k, "-LV"))
      out[[length(out) + 1L]] <- lv(paste0("R-LV-thin-L", k), "L-LV", "ROBUSTNESS", "lobby_lv_thin_real_m",
                                    paste0("Robustness of L", k, "-LV: thin sector-years (fewer than 5 reporting clients) ",
                                           "kept; ", common), "lobbyview_all", base = paste0("L", k, "-LV"))
    }
  }
  out
}

.champions <- function() {
  ctl <- c("chamber", "party", "seniority_years")
  base_note <- paste0("toughness_general = mean competitiveness of Cook, Inside Elections and Sabato (0 safe ... 3 toss-up); ",
                      "sample up_for_election = 1 (retiring rows excluded by that flag), lost-renomination rows excluded; ",
                      "controls chamber, party, seniority_years; cycle and board fixed effects; CR1 and wild cluster bootstrap ",
                      "by champion (bioguide).")
  within_note <- paste0(" Champion fixed effects: identified from cycles in which the same member's toughness varies; ",
                        "controls without within-champion variation are dropped and named.")
  h5 <- function(id, label, fe, note, ...) {
    sgs_test_spec(id = id, family = "H5", label = label, dv = "industry_money_primary", focal = "toughness_general",
                  controls = ctl, fe = fe, variant = "h5", table = "champions", window_rule = SGS_H5_GATE_RULE,
                  inference = "wcr", unit = "board x champion x cycle", note = note, ...)
  }
  pooled_fe <- c("board", "cycle")
  within_fe <- c("champion", "board", "cycle")
  out <- list(h5("H5-pooled", "EXTENSION", pooled_fe, base_note),
              h5("H5-within", "EXTENSION", within_fe, paste0(base_note, within_note)))
  variants <- list(
    list(tag = "log1p", kw = list(dv_transform = "log1p"), txt = "log1p(DV); rows with DV < 0 are counted and excluded, never altered."),
    list(tag = "any", kw = list(dv_transform = "any"), txt = "Extensive margin: 1 if the DV > 0, linear probability model."),
    list(tag = "no2026", kw = list(drop_cycles = 2026),
         txt = "Excludes 2026 (partial cycle: current, not final, ratings; money to mid-2026)."))
  for (v in variants) {
    out[[length(out) + 1L]] <- do.call(sgs_spec_update, c(list(h5(paste0("H5-pooled-", v$tag), "ROBUSTNESS", pooled_fe, v$txt,
                                                                  base = "H5-pooled")), v$kw))
    out[[length(out) + 1L]] <- do.call(sgs_spec_update, c(list(h5(paste0("H5-within-", v$tag), "ROBUSTNESS", within_fe, v$txt,
                                                                  base = "H5-within")), v$kw))
  }
  trade <- paste0("Sensitivity DV industry_money_with_trade_real_2025_usd (NOT BUILT when 05 has no such column); ",
                  "otherwise as the base test.")
  out[[length(out) + 1L]] <- sgs_spec_update(h5("H5-pooled-trade", "ROBUSTNESS", pooled_fe, trade, base = "H5-pooled"),
                                             dv = "industry_money_with_trade")
  out[[length(out) + 1L]] <- sgs_spec_update(h5("H5-within-trade", "ROBUSTNESS", within_fe, trade, base = "H5-within"),
                                             dv = "industry_money_with_trade")
  sec <- paste0("Secondary regressor in its own model (pooled specification). Sample: up_for_election = 1 ",
                "including lost-renomination rows (primary models only).")
  out[[length(out) + 1L]] <- sgs_spec_update(h5("H5-primary_contested", "EXPLORATORY", pooled_fe, sec, keep_lost_primary = TRUE),
                                             focal = "primary_contested")
  out[[length(out) + 1L]] <- sgs_spec_update(h5("H5-primary_margin", "EXPLORATORY", pooled_fe, sec, keep_lost_primary = TRUE),
                                             focal = "primary_margin")
  out[[length(out) + 1L]] <- sgs_spec_update(
    h5("H5-general_margin", "EXPLORATORY", pooled_fe,
       paste0("Secondary regressor in its own model (pooled specification); lost-renomination rows ",
              "excluded (no general election). Flag: ", SGS$H5_GENERAL_MARGIN_FLAG, "."),
       flag = SGS$H5_GENERAL_MARGIN_FLAG),
    focal = "general_margin")
  out
}

.preview <- function() {
  pv <- function(...) sgs_test_spec(label = "PREVIEW", dv = "contributions_real_m", gate = "preview", flag = SGS$PREVIEW_FLAG,
                                    window_rule = SGS_PREVIEW_RULE, ...)
  out <- list()
  for (k in c("1", "2", "3")) {
    x <- SGS_GROWTH[[k]]
    out[[length(out) + 1L]] <- pv(id = paste0("C", k, "-PV-reduced"), family = "C-PV", focal = x,
                                  controls = c("pres_year", "midterm_year"), base = paste0("C", k),
                                  note = paste0("PREVIEW (i) reduced: sector FE + pres_year + midterm_year + ", x, "."))
    out[[length(out) + 1L]] <- pv(id = paste0("C", k, "-PV-yearFE"), family = "C-PV", focal = x, controls = character(0),
                                  fe = c("sector", "year"), variant = "year_fe", base = paste0("C", k),
                                  note = paste0("PREVIEW (ii) year FE: sector FE + year FE + ", x, "."))
    out[[length(out) + 1L]] <- pv(id = paste0("C", k, "-PV-core"), family = "C-PV", focal = x, controls = SGS_C_CONTROLS,
                                  base = paste0("C", k), saturation_check = TRUE,
                                  note = paste0("PREVIEW full core specification (sector FE + pres_year + midterm_year + exp_dem_house + ",
                                                "exp_dem_senate + ", x, "), exp_dem 2023-2026 filled from 02 ",
                                                "expected_control_2023_2026; NOT IDENTIFIED when the national terms saturate the ",
                                                "distinct years (not forced)."))
  }
  out[[length(out) + 1L]] <- pv(id = "H1-PV", family = "H1-PV", focal = c("pres_year", "midterm_year"), controls = character(0),
                                table = "industry_year", unit = "Mentat industry x year",
                                note = paste0("PREVIEW: contributions ~ sector FE + pres_year + midterm_year over every Mentat industry of 04 ",
                                              "(the seven study sectors with a Mentat workbook plus community_banks, which is not a study ",
                                              "sector), 2021-2025."))
  out
}

# Tests of Paul's rulings that the Python package does not have.
.paul_extra <- function(core) {
  out <- list()
  for (cc in core) {
    ctl <- cc$controls
    ctl[ctl == "exp_dem_house"] <- "gb538_margin_house"
    out[[length(out) + 1L]] <- sgs_test_spec(
      id = paste0("H4-538-", cc$id), family = "H4-538", label = "ROBUSTNESS", dv = cc$dv,
      focal = c(cc$focal, "gb538_margin_house"), controls = setdiff(ctl, "gb538_margin_house"), base = cc$id,
      requires = "gb538",
      note = paste0("Robustness of ", cc$id, ": the 538 House generic-ballot margin (02 ", SGS$EXPECTED_CONTROL_538_SHEET,
                    ") in place of exp_dem_house; never the main expected-control measure."))
  }
  for (k in c("1", "2", "3")) {
    out[[length(out) + 1L]] <- sgs_test_spec(
      id = paste0("R-dedup-C", k), family = "robustness", label = "ROBUSTNESS", dv = "contributions_dedup_real_m",
      focal = SGS_GROWTH[[k]], controls = SGS_C_CONTROLS, base = paste0("C", k), requires = "pac_dedup",
      dv_label = paste0("general giving (04) excluding own-PAC receipts (recipient_category '", SGS$COMPANY_PAC_CATEGORY,
                        "'), $M 2025"),
      note = paste0("Excluding own-PAC receipts (Paul's approved PAC double-count check; named so after the Codex methodology ",
                    "review of 2026-09-26): C", k, " on general giving without the receipts of a roster company's own PAC, so ",
                    "a donor's gift to the PAC and the PAC's onward gift are not both counted. It is not transaction-level ",
                    "de-duplication: the conduit / candidate path (08 notes n6) is not resolved by it."))
  }
  for (ch in c("House", "Senate")) {
    for (k in c("1", "2", "3")) {
      out[[length(out) + 1L]] <- sgs_test_spec(
        id = paste0("DS-", ch, "-C", k), family = "DS", label = "EXTENSION", dv = paste0("dem_share_", tolower(ch)),
        focal = SGS_GROWTH[[k]], controls = SGS_C_CONTROLS, requires = "dem_share",
        dv_label = paste0("Democratic share of general giving to ", ch, " candidates, dem / (dem + rep) (08 ",
                          SGS$CHAMBER_SHEET, "), 0-1"),
        note = paste0("Partisan direction (plan section 5): Democratic share of general giving to ", ch,
                      " candidates by sector-year (08 ", SGS$CHAMBER_FILE, " sheet ", SGS$CHAMBER_SHEET, "); focal ",
                      "and controls as in C", k, "; a zero denominator is a missing share."))
    }
  }
  for (ch in c("House", "Senate")) {
    hill <- if (ch == "House") "DCCC to D and NRCC to R" else "DSCC to D and NRSC to R"
    for (k in c("1", "2", "3")) {
      out[[length(out) + 1L]] <- sgs_test_spec(
        id = paste0("DS+Hill-", ch, "-C", k), family = "DS+Hill", label = "ROBUSTNESS",
        dv = paste0("dem_share_hill_", tolower(ch)), focal = SGS_GROWTH[[k]], controls = SGS_C_CONTROLS,
        base = paste0("DS-", ch, "-C", k), requires = "dem_share_hill",
        dv_label = paste0("Democratic share of House / Senate giving with the Hill committees (", hill, "), 0-1"),
        note = paste0("Robustness of DS-", ch, "-C", k, ": the chamber's Hill committees added (", hill, "); ActBlue and ",
                      "WinRed conduit money stays out of both parties."))
    }
  }
  my <- list(c("MY-C3", "contributions_real_m", "C"), c("MY-L3-income", "lobby_income_real_m", "L"),
             c("MY-L3-expenses", "lobby_expenses_real_m", "L"), c("MY-L3-LV", "lobby_lv_real_m", "L"))
  for (m in my) {
    out[[length(out) + 1L]] <- sgs_test_spec(
      id = m[1], family = "MY", label = "EXPLORATORY", dv = m[2], focal = "predicted_growth_multiyear_pct",
      controls = if (m[3] == "C") SGS_C_CONTROLS else SGS_L_CONTROLS, flag = SGS$MULTIYEAR_FLAG,
      requires = c("multiyear", if (m[2] == "lobby_lv_real_m") "lobbyview_all"),
      fallback_whole_run = m[2] == "lobby_lv_real_m",
      note = paste0("Compliant (i), plan section 9: the multi-year crypto and fintech projections of 06 ",
                    "(supplemental_observations, component_forecasts), each used only for the spending year right after its ",
                    "publication (vintage rule: the latest projection available by 31 December of the previous year); a ",
                    "separate family, never the comparable annual input."))
  }
  out
}

# Families of the rulings of 2026-09-26 (Paul's rule set only), for L1-LV..L3-LV and for C1-C3 (the C variants are
# gated like C1-C3, so they become estimable with the core tests once the Mentat 2020 cycle lands):
#   ASYM   g replaced by g_pos = max(g, 0) and g_neg = min(g, 0), plus the bootstrap test of g_pos = g_neg; the
#          sector-years with g < 0 are counted per sector (EXTENSION; "what happens when that sector experiences a
#          decrease");
#   DECEL  g, an indicator of growth falling from the prior year (g_t < g_{t-1}) and its interaction with g (EXTENSION;
#          the second reading of "decrease");
#   SLOPES one growth slope per sector, Y ~ g:factor(study_sector) + controls + factor(study_sector), every slope with
#          the study's inference, and the bootstrap F test that all slopes are equal (EXTENSION);
#   H4-L*-LV  exp_dem_house, exp_dem_senate, cur_dem_house, cur_dem_senate read from L*-LV with the study's inference
#          (EXTENSION; H4-C1..C3 read exp_dem from C1-C3 as before);
#   BS / BANK  the bank split: big_banks and community_banks as two sectors sharing the commercial-banking growth series
#          (BS-*: every sector; BANK-*: the two banks only, with a growth x community_banks interaction; EXTENSION);
#          the LobbyView versions need community_banks rows in 01 lobbyview_sector_year_all;
#   R-TW / R-TC  telecom's growth = the wireless (tw) or cable (tc) component only, instead of the revenue-weighted
#          combination (ROBUSTNESS).
.extensions_0926 <- function() {
  out <- list()
  lvk <- list(inference = "wcr", min_clusters_inference = SGS$LOBBYVIEW_MIN_CLUSTERS_INFERENCE, fallback_whole_run = TRUE,
              window_rule = SGS_LV_WINDOW_RULE, requires = "lobbyview_all")
  lv_common <- paste0("LobbyView as in L-LV (01 ", SGS$LOBBYVIEW_ALL_SHEET, ", de-duplicated amount, thin sector-years ",
                      "excluded, whole qualifying fallback run, bootstrap inference with >= 3 sector clusters).")
  bases <- list()
  for (k in c("1", "2", "3")) {
    bases[[length(bases) + 1L]] <- list(id = paste0("L", k, "-LV"), dv = "lobby_lv_real_m", controls = SGS_L_CONTROLS,
                                        g = SGS_GROWTH[[k]], lv = TRUE)
  }
  for (k in c("1", "2", "3")) {
    bases[[length(bases) + 1L]] <- list(id = paste0("C", k), dv = "contributions_real_m", controls = SGS_C_CONTROLS,
                                        g = SGS_GROWTH[[k]], lv = FALSE)
  }
  mk <- function(b, ...) {
    kw <- list(...)
    if (b$lv) for (nm in names(lvk)) if (is.null(kw[[nm]])) kw[[nm]] <- lvk[[nm]]
    do.call(sgs_test_spec, kw)
  }
  lvtxt <- function(b) if (b$lv) paste0(" ", lv_common) else ""
  for (b in bases) {
    g <- b$g
    out[[length(out) + 1L]] <- mk(b, id = paste0("ASYM-", b$id), family = "ASYM", label = "EXTENSION", dv = b$dv,
                                  focal = paste0(g, c("_pos", "_neg")), controls = b$controls, base = b$id,
                                  equality = paste0(g, c("_pos", "_neg")), count_var = g, count_kind = "decline",
                                  note = paste0("Declines (Paul: \"what happens when that sector experiences a decrease\"): ", b$id,
                                                " with ", g, " split into ", g, "_pos = max(", g, ", 0) and ", g, "_neg = min(", g,
                                                ", 0); the slope in decline years (g < 0) and in growth years, and the bootstrap ",
                                                "test that they are equal. The sector-years with g < 0 are counted per sector.",
                                                lvtxt(b)))
    out[[length(out) + 1L]] <- mk(b, id = paste0("DECEL-", b$id), family = "DECEL", label = "EXTENSION", dv = b$dv,
                                  focal = c(g, paste0(g, "_decel"), paste0(g, "_x_decel")), controls = b$controls, base = b$id,
                                  count_var = g, count_kind = "deceleration",
                                  note = paste0("Deceleration (the second reading of \"decrease\"): ", b$id, " plus ", g,
                                                "_decel = 1 when ", g, " falls from the prior year (g_t < g_{t-1}, same sector) ",
                                                "and its interaction ", g, "_x_decel = ", g, " x ", g, "_decel. The years with ",
                                                "g_t < g_{t-1} are counted per sector.", lvtxt(b)))
    out[[length(out) + 1L]] <- mk(b, id = paste0("SLOPES-", b$id), family = "SLOPES", label = "EXTENSION", dv = b$dv,
                                  focal = g, controls = b$controls, variant = "slopes", base = b$id,
                                  joint = list(list(kind = "equal", var = g, label = "slopes", key = "joint: equal slopes")),
                                  note = paste0("Each sector's own growth slope: ", b$dv, " ~ ", g, ":factor(study_sector) + ",
                                                "controls + factor(study_sector); every slope with the study's inference, and the ",
                                                "wild cluster restricted bootstrap F test that all slopes are equal (restricted ",
                                                "model: ", b$id, "). Each slope is identified by one sector cluster: its CR1 error ",
                                                "and wild cluster bootstrap rest on that single cluster and are unreliable (few ",
                                                "treated clusters; MacKinnon and Webb 2017); read them with the HC1 error and the ",
                                                "sector's own regression (strata).", lvtxt(b)))
  }
  # Paul's hypothesis (2026-09-26): "if the industry contracted, they would spend more to meet their policy
  # objectives" - growth from the year before, so L1-LV now and C1 once 2020 lands
  one_sector <- paste0("Each per-sector term is identified by one sector cluster: its CR1 error and wild cluster bootstrap ",
                       "rest on that single cluster and are unreliable (few treated clusters; MacKinnon and Webb 2017); read ",
                       "them with the HC1 error, the sector's own regression (strata) and the joint tests. A sector whose ",
                       "term does not vary within it (e.g. no contraction year) has no estimable term (lm() prints NA).")
  for (b in bases[vapply(bases, function(b) identical(b$g, "growth_previous_year_pct"), TRUE)]) {
    g <- b$g
    out[[length(out) + 1L]] <- mk(b, id = paste0("CONTRACT-a-", b$id), family = "CONTRACT", label = "EXTENSION", dv = b$dv,
                                  focal = "contracted_prior", controls = b$controls, base = b$id,
                                  count_var = g, count_kind = "contraction", predicted_sign = c(contracted_prior = "+"),
                                  note = paste0("Paul's hypothesis (\"if the industry contracted, they would spend more to meet ",
                                                "their policy objectives\"), variant (a): contracted_prior = 1(", g, " < 0), the ",
                                                "industry contracted the year before; its coefficient is the level shift in ",
                                                "spending in the year after a contraction (the hypothesis predicts it > 0), with ",
                                                "the ", b$id, " controls and sector baselines. Contraction years are counted per ",
                                                "sector.", lvtxt(b)))
    out[[length(out) + 1L]] <- mk(b, id = paste0("CONTRACT-b-", b$id), family = "CONTRACT", label = "EXTENSION", dv = b$dv,
                                  focal = "contracted_prior", controls = b$controls, variant = "slopes", base = b$id,
                                  count_var = g, count_kind = "contraction", predicted_sign = c(contracted_prior = "+"),
                                  joint = list(list(kind = "zero", var = "contracted_prior", label = "contracted_prior effects"),
                                               list(kind = "equal", var = "contracted_prior", label = "contracted_prior effects")),
                                  note = paste0("Paul's hypothesis, variant (b): ", b$dv, " ~ contracted_prior:factor(study_sector) ",
                                                "+ controls + factor(study_sector) (the SLOPES design): each sector's own level ",
                                                "shift in the year after a contraction (the hypothesis predicts > 0), with the ",
                                                "joint tests that all are zero and that all are equal. ", one_sector, lvtxt(b)))
    out[[length(out) + 1L]] <- mk(b, id = paste0("ASYM-SLOPES-", b$id), family = "ASYM-SLOPES", label = "EXTENSION",
                                  dv = b$dv, focal = paste0(g, c("_pos", "_neg")), controls = b$controls, variant = "slopes",
                                  base = b$id, count_var = g, count_kind = "decline",
                                  predicted_sign = setNames("-", paste0(g, "_neg")),
                                  joint = list(list(kind = "zero", var = paste0(g, "_neg"), label = "decline-year slopes")),
                                  note = paste0("Paul's hypothesis by sector: ", b$dv, " ~ ", g, "_pos:factor(study_sector) + ",
                                                g, "_neg:factor(study_sector) + controls + factor(study_sector), each sector's ",
                                                "growth-year slope (", g, "_pos = max(", g, ", 0)) and decline-year slope (", g,
                                                "_neg = min(", g, ", 0) <= 0). Sign convention: a deeper contraction is a more ",
                                                "negative ", g, "_neg, so the hypothesis (deeper contraction, more spending) ",
                                                "predicts a NEGATIVE decline-year slope. Joint test: all decline-year slopes are ",
                                                "zero. ", one_sector, lvtxt(b)))
  }
  for (k in c("1", "2", "3")) {
    out[[length(out) + 1L]] <- sgs_test_spec(
      id = paste0("H4-L", k, "-LV"), family = "H4", label = "EXTENSION", dv = "lobby_lv_real_m",
      focal = c("exp_dem_house", "exp_dem_senate", "cur_dem_house", "cur_dem_senate"),
      controls = c(SGS_GROWTH[[k]], "pres_year", "midterm_year"), variant = "derived", base = paste0("L", k, "-LV"),
      note = paste0("Expected and current partisan control as headline terms: exp_dem_house, exp_dem_senate, cur_dem_house ",
                    "and cur_dem_senate read from L", k, "-LV with the study's inference."))
  }
  big <- SGS$BANK_SPLIT_BIG; com <- SGS$BANK_SPLIT_COMMUNITY
  for (b in bases) {
    g <- b$g
    req <- if (b$lv) c("lobbyview_all", "lobbyview_community_banks", "bank_split") else "bank_split"
    split_txt <- if (b$lv) paste0(" ", SGS_BANK_LV_NOTE) else
      paste0(" Contributions: ", big, " = 04 Mentat banking, ", com, " = 04 Mentat community_banks.")
    out[[length(out) + 1L]] <- mk(b, id = paste0("BS-", b$id), family = "BANKSPLIT", label = "EXTENSION", dv = b$dv,
                                  focal = g, controls = b$controls, table = "sector_year_banks", base = b$id, requires = req,
                                  note = paste0("Bank split: ", b$id, " with the banks split into ", big, " and ", com,
                                                " as separate sectors; both carry the commercial-banking growth series ",
                                                "(IBISWorld 52211).", split_txt, lvtxt(b)))
    out[[length(out) + 1L]] <- mk(b, id = paste0("BANK-", b$id), family = "BANKSPLIT", label = "EXTENSION", dv = b$dv,
                                  focal = c(g, paste0(g, ":", com)), controls = b$controls, table = "sector_year_banks",
                                  sectors = c(big, com), variant = "sector_interaction", interactions = list(c(g, com)),
                                  min_clusters_inference = SGS$LOBBYVIEW_MIN_CLUSTERS_INFERENCE, base = b$id, requires = req,
                                  note = paste0("Banks only (", big, " and ", com, "): ", b$dv, " ~ ", g, " + ", g, ":", com,
                                                " + controls + factor(study_sector); ", g, ":", com, " is the community-bank ",
                                                "slope minus the big-bank slope. Two sector clusters: DESCRIPTIVE (estimate and ",
                                                "HC1 error only; the wild cluster bootstrap cannot reach p < 0.056).", split_txt,
                                                lvtxt(b)))
  }
  for (b in bases) {
    for (cn in names(SGS$TELECOM_COMPONENT_TAGS)) {
      tag <- SGS$TELECOM_COMPONENT_TAGS[[cn]]
      out[[length(out) + 1L]] <- mk(b, id = paste0("R-", toupper(tag), "-", b$id), family = "telecom", label = "ROBUSTNESS",
                                    dv = b$dv, focal = paste0(b$g, "_", tag), controls = b$controls, base = b$id,
                                    requires = c(if (b$lv) "lobbyview_all", paste0("telecom_", tag)),
                                    note = paste0("Robustness of ", b$id, ": telecom's growth is the ", sub("telecom_", "", cn),
                                                  " component alone (IBISWorld ", SGS$TELECOM_COMPONENT_CODES[[cn]],
                                                  ") instead of the revenue-weighted wireless + cable combination; every other ",
                                                  "sector as in ", b$id, "."))
    }
  }
  out
}

# SHIFT (Paul, 2026-09-26: "does that money shift more toward the party in favor to take control?"): the partisan
# ALLOCATION of contributions, not their level, on expected control (lobbying has no party split and cannot test it;
# the DS tests, with a growth focal, do not test it). CORE: Paul's stated hypothesis; the prediction is a POSITIVE
# coefficient (more expected Democratic control, a larger Democratic share). Every Mentat industry of 04 / 08 (eight
# units: the seven study sectors with a Mentat book plus community_banks), clustered by unit. Main window 2020-2025 by
# the standard gate (it switches on when the 2020 cycle lands); PREVIEW 2021-2025 now. ROBUSTNESS: Hill (08 with the Hill
# committees), FD (first differences) and W (weighted by the party-labelled dollars). Every 04 funding source stays in
# (Paul: "Keep those receipts"); there are no giving-only variants.
SGS_SHIFT_HYPOTHESIS <- paste0("Paul's hypothesis (2026-09-26: \"does that money shift more toward the party in favor to take ",
                               "control?\"): the partisan ALLOCATION of contributions, not their level (lobbying has no party ",
                               "split and cannot test it). The prediction is a POSITIVE coefficient: more expected Democratic ",
                               "control, a larger Democratic share.")
SGS_SHIFT_ID_NOTE <- paste0("Expected control varies only by year (by year and chamber in the stacked model), so the focal term ",
                            "is identified from the 5-6 yearly values of the window (10-12 year x chamber values), however many ",
                            "unit-years there are; the identification line gives the year-level parameters, the year-level ",
                            "residual df and the OLS weight of each year on the estimate.")
SGS_SHIFT_UNITS_NOTE <- paste0("Units: every Mentat industry of 04 / 08 (commercial_banks, credit_unions, crypto, credit_arms, ",
                               "fintech, property_casualty, telecom and community_banks), clustered by unit. Every 04 funding ",
                               "source is kept (Paul: \"Keep those receipts\").")
SGS_SHIFT_PREVIEW_FD_RULE <- paste0(SGS_PREVIEW_RULE, "; first differences: >= ", SGS$PREVIEW_MIN_YEARS - 1, " year-to-year ",
                                    "changes (the 5 preview years give 4 changes; a lag level before 2021 enters when it exists)")
# Coordinator's rulings of 2026-09-26 (TRENDS and SHIFT notes): the pre-specified SHIFT models stay primary as in run
# analysis-R-20260926T070630Z; SHIFT-Chamber is the primary reading of the preview; the saturated previews are DESCRIPTIVE
# (SATURATED); the minimum-base variants are post-result EXPLORATORY choices.
SGS_SHIFT_PREVIEW_READING <- paste0("SHIFT preview (coordinator's rulings of 2026-09-26): the six pre-specified SHIFT models are ",
                                    "primary, as in run analysis-R-20260926T070630Z (unweighted, no minimum base). SHIFT-Chamber is the ",
                                    "primary reading of the preview - the stacked model has 10 year x chamber cells for 6 cell-level ",
                                    "parameters, so it keeps year-level residual df; the single-chamber and all-giving previews (5 ",
                                    "year-level parameters on 5 years) are SATURATED, labelled ", SGS$SATURATED_LABEL, ": each ",
                                    "estimate is a fixed contrast of the years, a descriptive contrast; their summary blocks stay in the ",
                                    "summaries file, out of the Trends headline and the SHIFT table. The minimum-base variants (-B25K, ",
                                    "-B10K, -B50K) were proposed after the preview results were seen: ", SGS$POST_RESULT_FLAG, ".")
# Coordinator's ruling of 2026-09-26: the unweighted models are primary for SHIFT, as for every other test. Weighting
# changes the population the estimate describes (Codex methodology review, adopted by the coordinator).
SGS_SHIFT_WEIGHT_NOTE <- paste0("The unweighted model (every unit-year counts equally) is the primary SHIFT model, as for every ",
                                "other test; the dollar-weighted -W variant is ROBUSTNESS only (coordinator's ruling of 2026-09-26). ",
                                "Weighting by dollars changes the population and the question (a dollar-weighted share, dominated by ",
                                "the largest units), so a difference from the unweighted model, or a higher weighted R^2, is not ",
                                "evidence that small bases are noise.")
# The minimum-base variants (EXPLORATORY, post-result): the threshold and why they are not confirmatory.
sgs_shift_min_base_note <- function(threshold) {
  paste0("Minimum base $", sgs_py_fixed(threshold, 0, comma = TRUE), " (", SGS$POST_RESULT_FLAG, "; proposed on 2026-09-26 ",
         "after the preview results were seen, so not a confirmatory specification): a share whose nominal D + R base is below $",
         sgs_py_fixed(threshold, 0, comma = TRUE), " is left out (a unit x year x chamber cell; a unit x year for the all-giving ",
         "share; first differences need both years); the cells left out are listed. The pre-specified SHIFT models keep every ",
         "share.")
}

.shift_family <- function(opts = list()) {
  timing <- c("pres_year", "midterm_year")
  flag_cols <- c("exp_dem_house_method", "exp_dem_house_flag", "exp_dem_senate_method", "exp_dem_senate_flag",
                 "exp_dem_own_chamber_method", "exp_dem_own_chamber_flag")
  m08 <- function(ch) paste0("giving to ", ch, " candidate committees (08 ", SGS$CHAMBER_SHEET, "; ActBlue / WinRed conduit ",
                             "gifts and the party committees are outside both parties)")
  h08 <- function(ch) paste0("giving to ", ch, " candidate committees plus the chamber's national party committees (08 ",
                             SGS$CHAMBER_HILL_SHEET, ": ", if (ch == "House") "DCCC added to D, NRCC to R" else if (ch == "Senate")
                               "DSCC added to D, NRSC to R" else "DCCC / DSCC added to D, NRCC / NRSC to R",
                             "; dem_share recomputed by 08; ActBlue / WinRed conduit gifts outside both parties)")
  all04 <- paste0("ALL the unit's party-labelled general giving (04 party D / R; 'Other / Unclassified' outside both; every ",
                  "recipient category and funding source)")
  # dv / hill: what the share is of; rhs: focal and controls; fe: the baselines (dropped in first differences); extra
  models <- list(
    list(key = "House", table = "shift_year", dv = "dem_share_house", hill_dv = "dem_share_hill_house",
         focal = "exp_dem_house", controls = c("cur_dem_house", timing), fe = "sector", unit = "Mentat industry x year",
         src = "08", group = "SHIFT-House", dv_txt = m08("House"), hill_txt = h08("House"),
         rhs = "focal exp_dem_house (expected Democratic House control, 0-1); controls cur_dem_house, pres_year, midterm_year",
         fe_txt = "unit baselines factor(study_sector)"),
    list(key = "Senate", table = "shift_year", dv = "dem_share_senate", hill_dv = "dem_share_hill_senate",
         focal = "exp_dem_senate", controls = c("cur_dem_senate", timing), fe = "sector", unit = "Mentat industry x year",
         src = "08", group = "SHIFT-Senate", dv_txt = m08("Senate"), hill_txt = h08("Senate"),
         rhs = "focal exp_dem_senate (expected Democratic Senate control, 0-1); controls cur_dem_senate, pres_year, midterm_year",
         fe_txt = "unit baselines factor(study_sector)"),
    list(key = "Chamber", table = "shift_chamber", dv = "dem_share", hill_dv = "dem_share_hill",
         focal = "exp_dem_own_chamber", controls = c("cur_dem_own_chamber", timing), fe = "sector_x_chamber",
         unit = "Mentat industry x year x chamber", src = "08", group = "SHIFT-Chamber",
         dv_txt = paste0("giving to the chamber's candidate committees, House and Senate rows stacked (unit x year x chamber; 08 ",
                         SGS$CHAMBER_SHEET, ")"),
         hill_txt = paste0("giving to the chamber's candidate committees plus its national party committees, House and Senate ",
                           "rows stacked (unit x year x chamber; 08 ", SGS$CHAMBER_HILL_SHEET, ": DCCC / DSCC added to D, NRCC / ",
                           "NRSC to R; dem_share recomputed by 08)"),
         rhs = paste0("focal exp_dem_own_chamber (expected Democratic control of the recipient's own chamber); controls ",
                      "cur_dem_own_chamber, pres_year, midterm_year; both chambers of a unit are one cluster"),
         fe_txt = paste0("baselines factor(chamber) + factor(study_sector) + factor(study_sector):factor(chamber), one per ",
                         "unit x chamber (the rank allows it: the gate checks the full design)")),
    list(key = "All", table = "shift_year", dv = "dem_share_all", focal = c("exp_dem_house", "exp_dem_senate"),
         controls = timing, fe = "sector", unit = "Mentat industry x year", src = "04", group = "SHIFT-All", dv_txt = all04,
         rhs = "focal exp_dem_house and exp_dem_senate jointly; controls pres_year, midterm_year",
         fe_txt = "unit baselines factor(study_sector)",
         extra = paste0(" The joint form leaves out current control: with cur_dem_house and cur_dem_senate it would have 7 ",
                        "year-level parameters, more than the 5-6 years of any window the data allow (never identified); ",
                        "SHIFT-All-House / SHIFT-All-Senate carry their own chamber's current control.")),
    list(key = "All-House", table = "shift_year", dv = "dem_share_all", focal = "exp_dem_house",
         controls = c("cur_dem_house", timing), fe = "sector", unit = "Mentat industry x year", src = "04", group = "SHIFT-All",
         dv_txt = all04, rhs = "focal exp_dem_house alone; controls cur_dem_house, pres_year, midterm_year",
         fe_txt = "unit baselines factor(study_sector)"),
    list(key = "All-Senate", table = "shift_year", dv = "dem_share_all", focal = "exp_dem_senate",
         controls = c("cur_dem_senate", timing), fe = "sector", unit = "Mentat industry x year", src = "04", group = "SHIFT-All",
         dv_txt = all04, rhs = "focal exp_dem_senate alone; controls cur_dem_senate, pres_year, midterm_year",
         fe_txt = "unit baselines factor(study_sector)")
  )
  for (i in seq_along(models)) {
    m <- models[[i]]
    models[[i]]$what <- paste0("DV = the Democratic share D / (D + R) of the unit's ", m$dv_txt, "; ", m$rhs, "; ", m$fe_txt, ".",
                               m$extra %||% "")
  }
  out <- list()
  add <- function(s) out[[length(out) + 1L]] <<- s
  pv_txt <- function(of) paste0(" PREVIEW of ", of, ": fixed window ", SGS$PREVIEW_WINDOW[1], "-", SGS$PREVIEW_WINDOW[2],
                                " (5 full years, below the 6-year minimum); the main window 2020-2025 switches on by itself ",
                                "when the 2020 cycle lands.")
  for (m in models) {
    main <- paste0("SHIFT-", m$key)
    req <- if (m$src == "08") "shift_08" else "shift_04"
    carry_of <- function(dv) c(paste0(dv, c("_base_usd", "_base_real_m")), "general_giving_real_m", flag_cols,
                               if (dv == "dem_share_all") c("dem_share_all_d_real_m", "dem_share_all_r_real_m",
                                                             "dem_share_all_other_real_m", "dem_share_all_dr_share",
                                                             "general_giving_non_giving_real_m"))
    lead <- paste0(SGS_SHIFT_HYPOTHESIS, " ", m$what, " ", SGS_SHIFT_UNITS_NOTE, " ", SGS_SHIFT_WEIGHT_NOTE, " ", SGS_SHIFT_ID_NOTE)
    variants <- list(list(sfx = "", label = "CORE", dv = m$dv, req = req, txt = lead))
    if (!is.null(m$hill_dv)) {
      variants[[length(variants) + 1L]] <- list(
        sfx = "-Hill", label = "ROBUSTNESS", dv = m$hill_dv, req = "shift_08_hill",
        txt = paste0("Robustness of ", main, " (Hill): DV = the Democratic share D / (D + R) of the unit's ", m$hill_txt, "; ",
                     m$rhs, "; ", m$fe_txt, ". ", SGS_SHIFT_ID_NOTE))
    }
    variants[[length(variants) + 1L]] <- list(
      sfx = "-FD", label = "ROBUSTNESS", dv = m$dv, req = req, variant = "fd",
      txt = paste0("Robustness of ", main, " (first differences): the change in the Democratic share D / (D + R) of the unit's ",
                   m$dv_txt, " on the changes of the same terms (", m$rhs, "), within unit",
                   if (m$table == "shift_chamber") " and chamber" else "", " (consecutive calendar years; the year before the ",
                   "window may supply the lag level); no intercept, so the baselines drop out (as R-FD-*).", m$extra %||% "",
                   " ", SGS_SHIFT_ID_NOTE))
    variants[[length(variants) + 1L]] <- list(
      sfx = "-W", label = "ROBUSTNESS", dv = m$dv, req = req, weight = paste0(m$dv, "_base_real_m"),
      txt = paste0("Robustness of ", main, " (dollar-weighted): weighted least squares, each row weighted by the dollars its ",
                   "share is computed from (D + R, $M 2025, column ", m$dv, "_base_real_m). ", SGS_SHIFT_WEIGHT_NOTE, " ",
                   m$what, " ", SGS_SHIFT_ID_NOTE))
    if (isTRUE(opts$chronology)) {
      # STRICT (coordinator's revision of 2026-09-26): expected-control values measured after their year (2023: the Nov
      # 2024 final call; 2025: the Sep 2026 market snapshot) are left out
      variants[[length(variants) + 1L]] <- list(
        sfx = "-STRICT", label = "ROBUSTNESS", dv = m$dv, req = req, strict = TRUE,
        txt = paste0("Robustness of ", main, " (STRICT timing): as ", main, ", but an expected-control value measured after its ",
                     "year (02 measured_on / last_price_date after 31 December) is not usable, so those unit-years leave the ",
                     "sample (the main series keeps them as Paul ruled: ", SGS$RETRO_LABEL, "). ", m$what, " ", SGS_SHIFT_ID_NOTE))
    }
    # the minimum-base variants: post-result EXPLORATORY choices (coordinator's revision of 2026-09-26), in their own
    # trend group so they never enter the sign agreement of the pre-specified models
    for (b in names(SGS$SHIFT_MIN_BASE_EXPLORATORY)) {
      thr <- SGS$SHIFT_MIN_BASE_EXPLORATORY[[b]]
      variants[[length(variants) + 1L]] <- list(
        sfx = paste0("-", b), label = "EXPLORATORY", dv = m$dv, req = req, min_base = thr, group = paste0(main, "-minbase"),
        flag = SGS$POST_RESULT_FLAG,
        txt = paste0("Exploratory variant of ", main, ": ", sgs_shift_min_base_note(thr), " ", m$what, " ", SGS_SHIFT_ID_NOTE))
    }
    for (v in variants) {
      id <- paste0(main, v$sfx)
      fd <- identical(v$variant, "fd")
      ps <- setNames(rep("+", length(m$focal)), m$focal)
      vflag <- v$flag %||% ""
      spec_of <- function(pv) sgs_test_spec(
        id = if (pv) paste0(id, "-PV") else id, family = if (pv) "SHIFT-PV" else "SHIFT", label = if (pv) "PREVIEW" else v$label,
        dv = v$dv, focal = m$focal, controls = m$controls, fe = if (fd) character(0) else m$fe,
        variant = v$variant %||% "level", table = m$table, base = if (pv) id else if (nzchar(v$sfx)) main else NA_character_,
        unit = m$unit, gate = if (pv) "preview" else "r8",
        flag = paste(Filter(nzchar, c(if (pv) SGS$PREVIEW_FLAG else "", vflag)), collapse = "; "),
        window_rule = if (pv) (if (fd) SGS_SHIFT_PREVIEW_FD_RULE else SGS_PREVIEW_RULE) else SGS_WINDOW_RULE,
        requires = v$req, weight_var = v$weight %||% NA_character_, carry = if (fd) carry_of(v$dv) else character(0),
        trend_group = v$group %||% m$group, predicted_sign = ps, identification = TRUE,
        preview_min_years = if (pv && fd) as.integer(SGS$PREVIEW_MIN_YEARS - 1) else NA_integer_,
        min_base = v$min_base %||% NA_real_, base_var = if (!is.null(v$min_base)) paste0(v$dv, "_base_usd") else NA_character_,
        strict_time = isTRUE(v$strict),
        note = if (pv) paste0(v$txt, pv_txt(id)) else v$txt)
      add(spec_of(FALSE))
      add(spec_of(TRUE))
    }
  }
  out
}

# L-LV robustness (coordinator's revision of 2026-09-26, after the Codex methodology review): the registry built the
# year-FE / log / LOSO / LOYO / FD family for .core() only, so the LobbyView tests - the currently estimable growth
# family - had none. Every variant here is fitted on its base test's gated sample (matched = TRUE, as the review did):
#   R-yearFE-Lk-LV  sector + year fixed effects replace the national controls;
#   R-log-Lk-LV     ln(DV) with the base controls (as R-log-* of the core tests);
#   R-logFE-Lk-LV   ln(DV) with sector + year fixed effects (the review's log specification);
#   R-LOSO / R-LOYO leave one sector / one year out of the base sample;
#   R-FD-Lk-LV      first differences of consecutive years both in the base sample, controls differenced, no intercept;
#   FDY-Lk-LV       first differences with year effects (the review's new, narrower question: a sector's change in lobbying
#                   on its change in the growth measure across successive years, after common yearly changes), with its
#                   leave-one-sector-out and leave-one-year-out fits: EXPLORATORY, no inference (estimate and HC1 only).
.lv_robustness <- function() {
  out <- list()
  lvk <- list(inference = "wcr", min_clusters_inference = SGS$LOBBYVIEW_MIN_CLUSTERS_INFERENCE, fallback_whole_run = TRUE,
              window_rule = paste0("the gated sample of the base test (matched, as the Codex review); ", SGS_LV_WINDOW_RULE),
              requires = "lobbyview_all", matched = TRUE)
  mk <- function(...) {
    kw <- list(...)
    for (nm in names(lvk)) if (is.null(kw[[nm]])) kw[[nm]] <- lvk[[nm]]
    do.call(sgs_test_spec, kw)
  }
  for (k in c("1", "2", "3")) {
    base <- paste0("L", k, "-LV"); g <- SGS_GROWTH[[k]]; dv <- "lobby_lv_real_m"
    on <- paste0(" Fitted on the gated sample of ", base, " (the same sector-years; matched as in the Codex methodology ",
                 "review of 2026-09-26).")
    out[[length(out) + 1L]] <- mk(id = paste0("R-yearFE-", base), family = "robustness", label = "ROBUSTNESS", dv = dv, focal = g,
                                  controls = character(0), fe = c("sector", "year"), variant = "year_fe", base = base,
                                  note = paste0("Year fixed effects replace the national controls (sector + year fixed effects).", on))
    out[[length(out) + 1L]] <- mk(id = paste0("R-log-", base), family = "robustness", label = "ROBUSTNESS", dv = dv, focal = g,
                                  controls = SGS_L_CONTROLS, variant = "log", base = base, matched_transform = "log",
                                  note = paste0("ln(DV) with the base controls and sector baselines; rows with DV <= 0 are counted, ",
                                                "never altered.", on))
    out[[length(out) + 1L]] <- mk(id = paste0("R-logFE-", base), family = "robustness", label = "ROBUSTNESS", dv = dv, focal = g,
                                  controls = character(0), fe = c("sector", "year"), variant = "log", base = base,
                                  matched_transform = "log",
                                  note = paste0("ln(DV) with sector + year fixed effects (the Codex review's log specification).", on))
    out[[length(out) + 1L]] <- mk(id = paste0("R-LOSO-", base), family = "robustness", label = "ROBUSTNESS", dv = dv, focal = g,
                                  controls = SGS_L_CONTROLS, variant = "loso", base = base,
                                  note = paste0("Leave one sector out: refits on the base sample without each sector in turn.", on))
    out[[length(out) + 1L]] <- mk(id = paste0("R-LOYO-", base), family = "robustness", label = "ROBUSTNESS", dv = dv, focal = g,
                                  controls = SGS_L_CONTROLS, variant = "loyo", base = base,
                                  note = paste0("Leave one year out: refits on the base sample without each year in turn; sub-fits ",
                                                "have one year fewer than the minimum they were gated at (diagnostic).", on))
    out[[length(out) + 1L]] <- mk(id = paste0("R-FD-", base), family = "robustness", label = "ROBUSTNESS", dv = dv, focal = g,
                                  controls = SGS_L_CONTROLS, fe = character(0), variant = "fd", base = base,
                                  matched_transform = "fd_pairs",
                                  note = paste0("First differences within sector of consecutive years both in the base sample ",
                                                "(controls differenced); no intercept, so sector baselines drop out.", on))
    fdy_note <- paste0("First differences with year effects (the Codex review's check): the change in ", dv, " on the change in ",
                       g, " between consecutive years both in the base sample, plus one effect per year (the common yearly ",
                       "change), no sector baselines. A new, narrower question - whether a sector's change in lobbying moves with ",
                       "its change in the growth measure across successive years after common yearly changes (for predicted ",
                       "growth: forecasts for different target years, not revisions of one forecast) - not a test of contraction ",
                       "causality. EXPLORATORY and descriptive: estimate and HC1 error only, no inference, no confirmatory ",
                       "p-value.", on)
    for (v in list(list(sfx = "", variant = "fd", txt = ""),
                   list(sfx = "-LOSO", variant = "loso", txt = " Leave one sector out of the differenced sample."),
                   list(sfx = "-LOYO", variant = "loyo", txt = " Leave one year out of the differenced sample."))) {
      out[[length(out) + 1L]] <- mk(id = paste0("FDY", v$sfx, "-", base), family = "FDY", label = "EXPLORATORY", dv = dv, focal = g,
                                    controls = character(0), fe = "year_full", variant = v$variant, base = base,
                                    matched_transform = "fd_pairs", inference = "none", note = paste0(fdy_note, v$txt))
    }
  }
  out
}

# STRICT timing variants of the core growth tests (coordinator's revision of 2026-09-26): as the base test, but an
# expected-control value measured after its year is not usable (the main series keeps it, labelled RETRO_LABEL).
.strict_core <- function() {
  out <- list()
  txt <- paste0(" (STRICT timing): an expected-control value measured after its year (02 measured_on / last_price_date after ",
                "31 December: 2023, the Nov 2024 final call; 2025, the Sep 2026 market snapshot) is not usable, so those ",
                "sector-years leave the sample; the main test keeps them as Paul ruled (", SGS$RETRO_LABEL, ").")
  for (k in c("1", "2", "3")) {
    out[[length(out) + 1L]] <- sgs_test_spec(
      id = paste0("STRICT-C", k), family = "STRICT", label = "ROBUSTNESS", dv = "contributions_real_m", focal = SGS_GROWTH[[k]],
      controls = SGS_C_CONTROLS, base = paste0("C", k), strict_time = TRUE, note = paste0("Robustness of C", k, txt))
    out[[length(out) + 1L]] <- sgs_test_spec(
      id = paste0("STRICT-L", k, "-LV"), family = "STRICT", label = "ROBUSTNESS", dv = "lobby_lv_real_m", focal = SGS_GROWTH[[k]],
      controls = SGS_L_CONTROLS, base = paste0("L", k, "-LV"), strict_time = TRUE, inference = "wcr",
      min_clusters_inference = SGS$LOBBYVIEW_MIN_CLUSTERS_INFERENCE, fallback_whole_run = TRUE, window_rule = SGS_LV_WINDOW_RULE,
      requires = "lobbyview_all", note = paste0("Robustness of L", k, "-LV", txt))
  }
  out
}

.build_registry <- function(rules) {
  core <- .core()
  reg <- core
  add <- function(s) reg[[length(reg) + 1L]] <<- s
  for (cc in core) {
    add(sgs_test_spec(id = paste0("H1-", cc$id), family = "H1", label = "EXTENSION", dv = cc$dv,
                      focal = c("pres_year", "midterm_year"),
                      controls = c(cc$focal, setdiff(cc$controls, c("pres_year", "midterm_year"))),
                      variant = "derived", base = cc$id,
                      note = paste0("Timing: pres_year and midterm_year coefficients read from ", cc$id, ".")))
  }
  for (dvkey in names(SGS_DVS)) {
    add(sgs_test_spec(id = paste0("H1-phase-", dvkey), family = "H1", label = "EXTENSION", dv = SGS_DVS[[dvkey]],
                      focal = c("pres_year", "midterm_year"), controls = character(0),
                      note = "DV ~ sector FE + pres_year + midterm_year: the largest complete-case sample of the DV."))
  }
  for (cc in core) {
    add(sgs_test_spec(id = paste0("H4-", cc$id), family = "H4", label = "EXTENSION", dv = cc$dv,
                      focal = c("exp_dem_house", "exp_dem_senate"),
                      controls = c(cc$focal, cc$controls[!startsWith(cc$controls, "exp_dem")]),
                      variant = "derived", base = cc$id, note = paste0("Partisan: exp_dem coefficients read from ", cc$id, ".")))
  }
  for (cc in core) {
    ctl <- .replace_exp(cc$controls, c("exp_shift_house", "exp_shift_senate"))
    note <- "exp_shift = exp_dem - cur_dem replaces exp_dem."
    if ("cur_dem_house" %in% ctl) {
      note <- paste0(note, " cur_dem is retained in this lobbying model, so the shift terms reparametrise the core model: ",
                     "their coefficients equal the core model's exp_dem coefficients.")
    }
    add(sgs_test_spec(id = paste0("H4shift-", cc$id), family = "H4", label = "EXPLORATORY", dv = cc$dv,
                      focal = c("exp_shift_house", "exp_shift_senate"),
                      controls = c(cc$focal, ctl[!startsWith(ctl, "exp_shift")]), note = note))
  }
  for (cc in core) {
    ctl <- cc$controls[!startsWith(cc$controls, "exp_dem") & cc$controls != "midterm_year"]
    add(sgs_test_spec(id = paste0("H4seat-", cc$id), family = "H4", label = "EXPLORATORY", dv = cc$dv,
                      focal = c("pred_dem_seat_change_house", "pred_dem_seat_change_senate"),
                      controls = c(cc$focal, ctl), year_filter = "election_years",
                      note = paste0("Final pre-election seat calls replace exp_dem; election years only, so midterm_year ",
                                    "(= 1 - pres_year on those years) is omitted.")))
  }
  for (dvkey in names(SGS_DVS)) {
    dv <- SGS_DVS[[dvkey]]
    add(sgs_test_spec(id = paste0("E1-", dvkey), family = "E1", label = "EXTENSION", dv = dv,
                      focal = c("growth_previous_year_pct", "predicted_growth_pct"),
                      controls = if (dv == "contributions_real_m") SGS_C_CONTROLS else SGS_L_CONTROLS,
                      note = "Prior actual and predicted growth together (plan section 5, extension 1)."))
  }
  for (k in c("1", "2", "3")) {
    x <- SGS_GROWTH[[k]]
    add(sgs_test_spec(id = paste0("T", k), family = "T", label = "EXTENSION", dv = "contributions_real_m",
                      table = "sector_year_tier", focal = c(x, paste0(x, ":Chief"), paste0(x, ":Middle Management")),
                      controls = SGS_C_CONTROLS, fe = "sector_x_tier", variant = "tier", tiers = SGS$TIER_MODEL_TIERS,
                      interactions = list(c(x, "Chief"), c(x, "Middle Management")),
                      note = paste0("Tier model: sector x tier baselines; the slope on X is the Employee slope (reference tier); ",
                                    "X:Chief and X:Middle Management are slope differences from Employee.")))
  }
  for (k in c("1", "2", "3")) {
    add(sgs_test_spec(id = paste0("T", k, "-corporate"), family = "T", label = "EXTENSION", dv = "contributions_real_m",
                      table = "sector_year_tier", focal = SGS_GROWTH[[k]], controls = SGS_C_CONTROLS,
                      tiers = SGS$CORPORATE_TIER, note = "Corporate (organisational) giving, fitted separately from the person tiers."))
  }
  for (cc in core) {
    add(sgs_test_spec(id = paste0("CR-", cc$id), family = "core_reduced", label = "EXPLORATORY", dv = cc$dv, focal = cc$focal,
                      controls = cc$controls[!startsWith(cc$controls, "exp_dem")], base = cc$id,
                      note = "Core test without the exp_dem controls (expected control is blank for 2023-2025)."))
  }
  for (cc in core) {
    add(sgs_test_spec(id = paste0("R-yearFE-", cc$id), family = "robustness", label = "ROBUSTNESS", dv = cc$dv, focal = cc$focal,
                      controls = character(0), fe = c("sector", "year"), variant = "year_fe", base = cc$id,
                      note = "Year fixed effects replace the national controls."))
    add(sgs_test_spec(id = paste0("R-log-", cc$id), family = "robustness", label = "ROBUSTNESS", dv = cc$dv, focal = cc$focal,
                      controls = cc$controls, variant = "log", base = cc$id,
                      note = "ln(DV) on positive DV values only; rows with DV <= 0 are counted, never altered."))
    add(sgs_test_spec(id = paste0("R-LOSO-", cc$id), family = "robustness", label = "ROBUSTNESS", dv = cc$dv, focal = cc$focal,
                      controls = cc$controls, variant = "loso", base = cc$id,
                      note = "Leave one sector out: refits on the gated sample without each sector in turn."))
    add(sgs_test_spec(id = paste0("R-LOYO-", cc$id), family = "robustness", label = "ROBUSTNESS", dv = cc$dv, focal = cc$focal,
                      controls = cc$controls, variant = "loyo", base = cc$id,
                      note = paste0("Leave one year out: refits on the gated sample without each year in turn; sub-fits ",
                                    "necessarily have one year fewer than the minimum they were gated at (diagnostic).")))
    add(sgs_test_spec(id = paste0("R-FD-", cc$id), family = "robustness", label = "ROBUSTNESS", dv = cc$dv, focal = cc$focal,
                      controls = cc$controls, fe = character(0), variant = "fd", base = cc$id,
                      note = paste0("First differences within sector (consecutive calendar years; the year before the ",
                                    "window may supply the lag level); no intercept, so sector baselines drop out.")))
  }
  paul_ds <- isTRUE(rules$ds_chamber)
  extra <- if (identical(rules$name, "paul-2026-09-25")) .paul_extra(core) else list()
  if (!paul_ds) {
    for (ch in c("House", "Senate")) {
      add(sgs_test_spec(id = paste0("DS-", ch), family = "DS", label = "EXTENSION", dv = paste0("dem_share_", tolower(ch)),
                        table = "dem_share", variant = "not_built",
                        note = "Democratic share of chamber-mapped contributions (plan section 5)."))
    }
  } else {
    for (s in extra) if (identical(s$family, "DS")) add(s)
  }
  for (s in .lobbyview(rules)) add(s)
  for (s in .champions()) add(s)
  for (s in .preview()) add(s)
  for (s in extra) if (!identical(s$family, "DS")) add(s)
  if (isTRUE(rules$extensions_0926)) for (s in .extensions_0926()) add(s)
  if (isTRUE(rules$shift)) for (s in .shift_family(rules)) add(s)
  if (isTRUE(rules$lv_robustness)) for (s in .lv_robustness()) add(s)
  if (isTRUE(rules$chronology)) for (s in .strict_core()) add(s)
  if (isTRUE(rules$seats)) for (s in .seats_family()) add(s)
  thr <- rules$near_collinear_r2 %||% NA_real_
  if (length(thr) == 1L && is.finite(thr)) {
    for (i in seq_along(reg)) if (identical(reg[[i]]$table, "champions")) reg[[i]]$near_collinear_r2 <- thr
  }
  if (isTRUE(rules$drop_singletons)) {
    for (i in seq_along(reg)) if (!identical(reg[[i]]$table, "champions")) reg[[i]]$drop_singletons <- TRUE
  }
  if (isTRUE(rules$population_note)) {
    for (i in seq_along(reg)) {
      if (any(sgs_is_growth_var(sgs_required_vars(reg[[i]])))) {
        fl <- reg[[i]]$flag
        reg[[i]]$flag <- if (nzchar(fl)) paste0(fl, "; ", SGS$POPULATION_NOTE) else SGS$POPULATION_NOTE
      }
    }
  }
  ids <- vapply(reg, `[[`, "", "id")
  if (anyDuplicated(ids)) sgs_raise("RegistryError", "registry: duplicate test ids")
  names(reg) <- ids
  reg
}

sgs_registry <- function(rules = sgs_rules()) .build_registry(rules)

# registry.select: tests to run; `only` entries match an id exactly or as a prefix followed by '-'.
sgs_select <- function(registry, only = NULL) {
  if (!length(only)) return(registry)
  ids <- names(registry)
  hit <- function(o) ids == o | startsWith(ids, paste0(o, "-"))
  unknown <- only[!vapply(only, function(o) any(hit(o)), TRUE)]
  if (length(unknown)) sgs_raise("KeyError", paste0("unknown test ids: ", sgs_py_list_repr(unknown)))
  keep <- Reduce(`|`, lapply(only, hit))
  registry[keep]
}
