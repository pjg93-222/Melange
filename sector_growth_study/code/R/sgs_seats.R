# SEATS (rule set paul-2026-09-25 only): Paul's follow-up, relayed 2026-09-26 by the Codex reviewer - "What about the
# partisanship of the spending as it correlates to expected seat gain for a party in the upcoming election?" - built to
# the coordinator's specification (after the Codex note SEAT_GAIN_FOLLOWUP.md). No earlier family tests it: SHIFT
# regresses the party share on the probability of chamber control, and H4seat regresses total dollars (not the party
# share) on seat calls.
#
#   SEATS-A (DESCRIPTIVE): sector x election cycle. The party share D / (D + R) of the cycle's giving - to the chamber's
#     candidate committees (08, "cand") or all party-labelled 04 giving ("all") - and D$ and R$ separately, on the
#     chamber's final pre-election Crystal Ball call of the Democratic net seat gain (02 seat_calls). Average-sector
#     (unweighted, unit baselines) and dollar-weighted (weights = the cycle's D + R dollars) estimands separately; the
#     sector's prior-cycle share (lagged allocation); a changes model (change in share on change in forecast gain, no
#     intercept). Retrospective: the final call comes after most of the cycle's spending.
#   SEATS-A-538 (DESCRIPTIVE): the same with 538's probability-weighted expected seats (09 aligned: the Lite expected seats
#     paired with the cycle's last whole pre-election week) - a separate predictor from the point call; NOT BUILT until 09 exists.
#   SEATS-W, estimand A (EXPLORATORY): the national response - 09's aligned unit-weeks (each paired by 09 with the latest
#     forecast AVAILABLE strictly before the week starts) collapsed to the chamber x cycle x week series; the week's
#     Democratic share (and its change) on the prior week's change in expected Democratic seats, pp per seat; primary
#     models without the lagged outcome, residual block bootstrap within cycle (3- and 5-week blocks; intervals
#     conditional on the forecast path), the lagged-outcome model a sensitivity with a recursive (dynamic) bootstrap,
#     HAC secondary; per cycle and pooled; pooled-dollar and equal-sector targets; leave one sector out; 538 "Lite"
#     primary (not polls-only: it imputes unpolled races); NOT BUILT until 09 exists.
#   Race level, estimands B (differential, group series by incumbency and 538 class) and C (own prospects):
#     sgs_seats_race.R, gated cell by cell (sgs_seats_cells).
# House and Senate are always separate, each on its own seat scale.

SGS_SEATS_CHAMBERS <- c(house = "House", senate = "Senate")
SGS_SEATS_TABLES <- c("seats_cycle_house", "seats_cycle_senate")

SGS_SEATS_QUESTION <- paste0("Paul's follow-up (2026-09-26): \"What about the partisanship of the spending as it correlates to ",
                             "expected seat gain for a party in the upcoming election?\"")
SGS_SEATS_PREDICTOR_DEF <- paste0(
  "Predictor: the forecast Democratic net seat gain in the chamber's upcoming election = the forecast's projected Democratic ",
  "seats after the election minus the Democratic seats at the start of the outgoing Congress (03 data ",
  "democratic_seats_before, the result of the previous election; Senate: Democrats plus the independents who caucus with ",
  "them); where the call states no seat total, the net change it states (02 seat_calls pred_dem_net_change). SEATS-A uses ",
  "the point call, Sabato's Crystal Ball final pre-election call (02 seat_calls, from House_Senate_Control_Forecasts_CSV.zip); ",
  "SEATS-A-538 and SEATS-W use 538's probability-weighted expected seats (09 aligned expected_dem_seats minus the seats before the election), a ",
  "separate predictor. House and Senate each on their own seat scale; a House seat is never pooled with a Senate seat.")
SGS_SEATS_OUTCOME_DEF <- paste0(
  "Outcome: the partisan allocation D / (D + R) of an election cycle's giving (cycle 2022 = calendar 2021-2022; both years ",
  "complete, so the partial 2026 cycle never enters), nominal dollars: cand = giving to the chamber's candidate committees ",
  "(08 sector_year_chamber); all = all party-labelled 04 giving (party D / R; 'Other / Unclassified' outside both; every ",
  "funding source kept). The denominator D + R and its coverage (D + R as a share of the unit's included receipts in the ",
  "cycle) are shown with every share, and D$ and R$ ($M 2025) are outcomes too, so new support for one party can be told ",
  "apart from a cut to the other.")
SGS_SEATS_A_FLAG <- paste0("DESCRIPTIVE retrospective description: the final pre-election call comes after most of the cycle's ",
                           "spending, so this describes, it does not test a response; independent election forecasts = cycles, ",
                           "not sectors x cycles; no significance claim")
SGS_SEATS_A_RULE <- paste0("SEATS-A gate: election cycles ", SGS$SEATS_WINDOW[1], "-", SGS$SEATS_WINDOW[2], " with both calendar ",
                           "years complete; >= 2 cycles (changes model: >= 1 change), >= ", SGS$MIN_SECTORS, " units, full-rank ",
                           "design, residual df >= ", SGS$MIN_RESID_DF, "; DESCRIPTIVE (estimate and HC1 error only)")
SGS_SEATS_W_RULE <- paste0("SEATS-W gate: whole pre-election weeks of 09 aligned, each paired by 09 with the latest forecast ",
                           "available strictly before the week starts; weeks within a cycle and cycles are the observations; fits ",
                           "with fewer than ", SGS$SEATS_MIN_WEEKS, " usable weeks are DESCRIPTIVE; EXPLORATORY")
SGS_SEATS_METHOD_NOTES <- c(
  paste0("The control-probability SHIFT results (the stacked preview SHIFT-Chamber-PV: {SHIFT_PV}) do NOT ",
         "test or disprove the seat-gain hypothesis. SHIFT regresses the party share on the probability that the Democrats ",
         "control the chamber; the expected seat gain is a different quantity (a party can be expected to gain many seats ",
         "while control stays out of reach, or a few seats that decide control). The H4seat tests regress total dollars, not ",
         "the party share, on seat calls, and are NOT ESTIMABLE."),
  paste0("SEATS-A is a retrospective description: the final call is made in the week of the election, after most of the ",
         "cycle's giving, so it can only describe how the cycle's allocation lines up with the outlook at its end. The number ",
         "of independent election forecasts is the number of cycles (House and Senate: 2022 and 2024 now; 2020 joins when it ",
         "lands), not sectors x cycles: every unit in a cycle shares one forecast. With two cycles each level estimate is a ",
         "fixed contrast of the two cycles' means (SATURATED), and a 2-3 election correlation gets no significance claim."),
  paste0("Inference in the weekly designs: the forecast change is shared by every sector and candidate in a week, so the ",
         "observations are weeks within a cycle and the cycles themselves, never sectors or candidates. The primary models have ",
         "no lagged outcome; a residual moving-block bootstrap within cycle (3- and 5-week blocks, both shown) holding the ",
         "exogenous regressors fixed gives intervals CONDITIONAL on the observed forecast path. With the lagged outcome the ",
         "fixed-X bootstrap is only a conditional sensitivity; dynamic inference comes only from the recursive block bootstrap, ",
         "labelled as such. Newey-West HAC errors are secondary and carry no p-value, no bootstrap p-value is proof, and a fit ",
         "with fewer than ", SGS$SEATS_MIN_WEEKS, " usable weeks is DESCRIPTIVE (the 2022 post-primary window, 7 weeks from ",
         "19 September, is descriptive), as is a series with calendar gaps inside a cycle or an outcome that never varies. The ",
         "interval resamples the full model's residuals and the p-value the residuals of the model without the forecast change ",
         "(the null imposed), so with 17 weeks an interval can exclude zero while p > 0.05; neither alone decides. The Codex ",
         "check's Senate first-term result shows why HAC alone is not enough: significant with HAC errors, it loses Holm support ",
         "under the block bootstrap and its raw significance when telecom is left out."),
  paste0("Groups and timing at the race level: incumbency comes from dated service in the chamber at each origin (a House ",
         "member running for the Senate is not an incumbent senator). The incoming-officeholder group is the favored ",
         "NON-INCUMBENT - no dated service in the chamber at the origin and the candidate's own named 538 Lite probability ",
         "above 0.5 before the window - pooling FEC challengers and open-seat candidates, because FEC C / O codes are not ",
         "reliable general-election status (Dale Strong, Harriet Hageman and Rich McCormick are counterexamples); the C / O ",
         "split is a provisional sensitivity. The 538 classes (toss-up < 60%, lean 60-75%, likely 75-95%, safe >= 95%) come ",
         "from the candidates' own named win probabilities - the race's class from its favourite candidate's probability ",
         "(538's evaluation convention; the same as max(p, 1 - p) in a two-candidate race, never folded, so a three-way ",
         "favourite below 0.5, as in 2022 AK-00, is a toss-up), the candidate-relative band ",
         "max(p, 1 - p) as a sensitivity - and are not Cook / Inside Elections / Sabato ratings. A named forecast ",
         "candidate is not necessarily the nominee: pre-primary probabilities condition on an assumed matchup, so those weeks ",
         "are flagged and a post-primary sensitivity is kept. Estimand B's groups are fixed at the pre-spending origin (the first ",
         "window) so membership never moves with the donations; the rolling re-classification is a sensitivity with its ",
         "transition counts. 538 Lite is labelled Lite: it imputes unpolled races (it is not ",
         "a polls-only model) and leaves out the fundraising fundamentals of Classic and Deluxe, which is why it is primary."),
  paste0("What a real test needs: dated within-cycle forecast histories (in hand: 538's 2022 national, House district and ",
         "Senate state forecasts with run timestamps; the 2020 national forecasts), transaction-dated money by committee (09), ",
         "and more election cycles. With 2022 alone every weekly design is one election (18 strict Lite weeks per chamber); ",
         "2020 adds only 3 (House) and 6 (Senate) strict weeks, and each further cycle adds one independent election per ",
         "chamber."))

# ---- the forecast Democratic net seat gain per chamber x election ----------------------------------------------------
SGS_SEATS_CALL_COLS <- c("chamber", "election_year", "seat_net_gain", "stated_net_change", "proj_dem_seats", "dem_seats_before",
                         "definition", "forecast_source", "quote", "status")
sgs_seat_calls <- function(wbs) {
  sc <- wbs$election$frames$seat_calls
  d3 <- if (!is.null(wbs$seats)) wbs$seats$frames$data else NULL
  num <- function(v) suppressWarnings(as.numeric(v))
  out <- list()
  for (i in seq_len(if (is.null(sc)) 0L else nrow(sc))) {
    ch <- as.character(sc$chamber[i]); y <- num(sc$election_year[i])
    stated <- num(sc$pred_dem_net_change[i])
    usable <- !is.na(stated) && sc$status[i] %in% SGS_USABLE_STATUSES
    proj <- if ("proj_dem_seats" %in% names(sc)) num(sc$proj_dem_seats[i]) else NA_real_
    before <- NA_real_
    if (!is.null(d3)) {
      k <- which(as.character(d3$chamber) %in% ch & num(d3$election_year) %in% y)
      if (length(k)) before <- num(d3$democratic_seats_before[k[1]])
    }
    computed <- usable && !is.na(proj) && !is.na(before)
    net <- if (computed) proj - before else if (usable) stated else NA_real_
    out[[length(out) + 1L]] <- list(
      chamber = ch, election_year = y, seat_net_gain = net, stated_net_change = stated, proj_dem_seats = proj,
      dem_seats_before = before,
      definition = if (!usable) "no call recorded" else if (computed) {
        paste0("projected Democratic seats ", sgs_py_str(proj), " - Democratic seats before the election ", sgs_py_str(before),
               if (!is.na(stated) && stated != net) paste0(" (the call's stated net change: ", sgs_py_str(stated), ")") else "")
      } else "the call's stated net change (no projected seat total in the call, or no 03 composition)",
      forecast_source = .txt0(if ("forecast_source" %in% names(sc)) sc$forecast_source[i] else NA),
      quote = .txt0(if ("quote" %in% names(sc)) sc$quote[i] else NA), status = if (usable) SGS_OBS else SGS_MISSING)
  }
  sgs_rows_df(out, SGS_SEATS_CALL_COLS)
}

.seats_election_day <- function(y) {
  d <- as.Date(sprintf("%d-11-01", as.integer(y)))
  wd <- as.POSIXlt(d)$wday                       # 0 Sunday ... 6 Saturday
  d + ((1 - wd) %% 7) + 1                        # the first Tuesday after the first Monday in November
}
# The election a date belongs to: the next general election on or after it (even years).
.seats_cycle_of <- function(d) {
  y <- as.integer(format(d, "%Y"))
  out <- ifelse(y %% 2 == 1, y + 1L, y)
  even <- !is.na(y) & y %% 2 == 0
  late <- even & d > .seats_election_day(ifelse(even, y, 2000L))
  out[late] <- out[late] + 2L
  out
}
.seats_week_of_cycle <- function(d, cycle) {
  start <- .seats_election_day(cycle - 2L) + 1
  as.numeric(floor(as.numeric(d - start) / 7))
}

# ---- SEATS-A tables: unit x election cycle, one per chamber ----------------------------------------------------------
SGS_SEATS_BASES <- c(cand = "giving to the chamber's candidate committees (08)", all = "all party-labelled giving (04)")

.seats_cycle_sum <- function(v) if (any(is.na(v))) NA_real_ else sum(v)

# shift = the SHIFT tables (units, shift_year); wbs = the workbooks. Returns list(tables, coverage, calls, built).
sgs_build_seats_tables <- function(wbs, shift) {
  calls <- sgs_seat_calls(wbs)
  units <- shift$units
  ch08 <- if (!is.null(wbs$chamber)) wbs$chamber$frames[[SGS$CHAMBER_SHEET]] else NULL
  sy4 <- wbs$spending$frames$sector_year
  p4 <- .shift_04_party(wbs$spending$frames$data)
  st4 <- function(u, y) { s <- sy4$status[sy4$study_sector == u & as.numeric(sy4$year) == y]; if (length(s)) s[1] else SGS_MISSING }
  cycles <- seq(SGS$SEATS_WINDOW[1], SGS$PANEL_LAST_YEAR, by = 2)
  tables <- list(); cov <- list()
  for (key in names(SGS_SEATS_CHAMBERS)) {
    ch <- SGS_SEATS_CHAMBERS[[key]]
    rows <- list()
    for (u in units) for (cy in cycles) {
      yrs <- c(cy - 1, cy)
      call <- calls[calls$chamber == ch & calls$election_year == cy, , drop = FALSE]
      r <- list(study_sector = u, year = cy, cycle_years = paste0(yrs[1], "-", yrs[2]), partial_year = FALSE,
                seat_net_gain = if (nrow(call) && call$status[1] == SGS_OBS) call$seat_net_gain[1] else NA_real_,
                seat_net_gain_538 = NA_real_)
      st <- vapply(yrs, function(y) st4(u, y), "")
      gg <- vapply(yrs, function(y) { k <- p4$study_sector == u & p4$year == y; if (any(k)) p4$total_real_m[k][1] else NA_real_ }, 0)
      r$general_giving_real_m <- if (all(st %in% SGS_USABLE_STATUSES)) .seats_cycle_sum(gg) else NA_real_
      # all party-labelled 04 giving
      ok4 <- all(st %in% SGS_USABLE_STATUSES)
      pick <- function(col) vapply(yrs, function(y) { k <- p4$study_sector == u & p4$year == y; if (any(k)) p4[[col]][k][1] else NA_real_ }, 0)
      vals <- list(all = list(ok = ok4, d = pick("d_usd"), r = pick("r_usd"), dr = pick("d_real_m"), rr = pick("r_real_m"),
                              why = if (ok4) "" else paste0("04 ", paste(yrs, st, collapse = ", "))))
      # the chamber's candidate committees (08)
      if (!is.null(ch08)) {
        r8 <- ch08[as.character(ch08$study_sector) == u & as.character(ch08$chamber) == ch & as.numeric(ch08$year) %in% yrs, , drop = FALSE]
        s8 <- vapply(yrs, function(y) { s <- r8$status[as.numeric(r8$year) == y]; if (length(s)) s[1] else SGS_MISSING }, "")
        ok8 <- all(s8 %in% SGS_USABLE_STATUSES)
        g8 <- function(col) vapply(yrs, function(y) { k <- as.numeric(r8$year) == y; if (any(k)) suppressWarnings(as.numeric(r8[[col]][k][1])) else NA_real_ }, 0)
        vals$cand <- list(ok = ok8, d = g8("dem_usd"), r = g8("rep_usd"), dr = g8("dem_real_m"), rr = g8("rep_real_m"),
                          why = if (ok8) "" else paste0("08 ", paste(yrs, s8, collapse = ", ")))
      } else {
        vals$cand <- list(ok = FALSE, d = c(NA, NA), r = c(NA, NA), dr = c(NA, NA), rr = c(NA, NA), why = "08 not present")
      }
      for (b in names(SGS_SEATS_BASES)) {
        v <- vals[[b]]
        d <- if (v$ok) .seats_cycle_sum(v$d) else NA_real_; rr <- if (v$ok) .seats_cycle_sum(v$r) else NA_real_
        den <- d + rr
        r[[paste0("dem_share_", b)]] <- if (!is.na(den) && den > 0) d / den else NA_real_
        r[[paste0("d_usd_", b)]] <- d; r[[paste0("r_usd_", b)]] <- rr; r[[paste0("base_usd_", b)]] <- den
        r[[paste0("d_real_m_", b)]] <- if (v$ok) .seats_cycle_sum(v$dr) else NA_real_
        r[[paste0("r_real_m_", b)]] <- if (v$ok) .seats_cycle_sum(v$rr) else NA_real_
        r[[paste0("base_real_m_", b)]] <- r[[paste0("d_real_m_", b)]] + r[[paste0("r_real_m_", b)]]
        r[[paste0("coverage_", b)]] <- if (!is.na(r$general_giving_real_m) && r$general_giving_real_m > 0 &&
                                           !is.na(r[[paste0("base_real_m_", b)]])) r[[paste0("base_real_m_", b)]] / r$general_giving_real_m else NA_real_
        r[[paste0("status_", b)]] <- if (!v$ok) paste0("incomplete cycle (", v$why, ")") else if (is.na(r[[paste0("dem_share_", b)]]))
          "no D + R dollars" else SGS_OBS
      }
      rows[[length(rows) + 1L]] <- r
    }
    g <- .rows_to_df(rows)
    # prior-cycle share and the changes (same unit, cycle - 2)
    for (b in names(SGS_SEATS_BASES)) {
      s <- paste0("dem_share_", b)
      lagi <- match(paste(g$study_sector, g$year - 2), paste(g$study_sector, g$year))
      g[[paste0(s, "_lag")]] <- g[[s]][lagi]
      g[[paste0(s, "_change")]] <- g[[s]] - g[[s]][lagi]
    }
    lagi <- match(paste(g$study_sector, g$year - 2), paste(g$study_sector, g$year))
    g$seat_net_gain_change <- g$seat_net_gain - g$seat_net_gain[lagi]
    g <- g[order(sgs_sector_rank(g$study_sector), g$study_sector, g$year, method = "radix"), , drop = FALSE]
    rownames(g) <- NULL
    tables[[paste0("seats_cycle_", key)]] <- g
    for (i in seq_len(nrow(g))) for (b in names(SGS_SEATS_BASES)) {
      cov[[length(cov) + 1L]] <- list(chamber = ch, base = b, study_sector = g$study_sector[i], cycle = g$year[i],
                                      cycle_years = g$cycle_years[i], status = g[[paste0("status_", b)]][i],
                                      d_usd = g[[paste0("d_usd_", b)]][i], r_usd = g[[paste0("r_usd_", b)]][i],
                                      dem_share = g[[paste0("dem_share_", b)]][i], base_usd = g[[paste0("base_usd_", b)]][i],
                                      d_real_m = g[[paste0("d_real_m_", b)]][i], r_real_m = g[[paste0("r_real_m_", b)]][i],
                                      coverage = g[[paste0("coverage_", b)]][i], general_giving_real_m = g$general_giving_real_m[i],
                                      seat_net_gain = g$seat_net_gain[i])
    }
  }
  covdf <- sgs_rows_df(cov, c("chamber", "base", "study_sector", "cycle", "cycle_years", "status", "d_usd", "r_usd", "dem_share",
                              "base_usd", "d_real_m", "r_real_m", "coverage", "general_giving_real_m", "seat_net_gain"))
  win_calls <- calls[calls$election_year >= SGS$SEATS_WINDOW[1] & calls$election_year <= SGS$SEATS_WINDOW[2], , drop = FALSE]
  built <- list(seats_calls = list(
    built = any(win_calls$status == SGS_OBS),
    note = paste0("02 seat_calls (Crystal Ball final pre-election calls) and 03 data (seats before the election): ",
                  paste0(win_calls$chamber, " ", win_calls$election_year, " ", ifelse(is.na(win_calls$seat_net_gain), "n/a",
                         sprintf("%+g", win_calls$seat_net_gain)), collapse = "; "))))
  list(tables = tables, coverage = covdf, calls = calls, built = built)
}

.rows_to_df <- function(rows) {
  cols <- unique(unlist(lapply(rows, names)))
  sgs_rows_df(rows, cols)
}

# ---- 09: the dated within-cycle workbook (SEATS-W estimand A, SEATS-A-538) --------------------------------------------
# Binding timing rule (coordinator, from the Codex audit of 2026-09-26): some 538 forecast rows were backfilled (2020
# House 57 of 87 dates generated on 2020-10-06; 2020 Senate 44 of 95 on 2020-09-15; 2022 20 of 153 on 2022-06-29). 09
# carries available_at, backfilled and availability_verified, and its sheet `aligned` pairs each unit-week with the
# latest forecast AVAILABLE strictly before the week starts. The pipeline uses that pairing as it is - it never re-pairs
# by forecast date - re-checks available_at < week_start, and uses rows with unverified availability (the 2018 files)
# only in a labelled sensitivity.
SGS_SEATS_W_REQUIRED <- c("study_sector", "chamber", "week_start", "d_gross_usd", "r_gross_usd", "d_usd", "r_usd", "source",
                          "model_version", "available_at", "expected_dem_seats", "primary_window")
# 09 as installed (coordinator, 2026-09-26): `aligned` holds the verified pairings (election and post-election weeks kept,
# flagged: every response estimate uses primary_window = TRUE); `aligned_sensitivity` the unverified-availability rows
# (2018, undated Crystal Ball; assumed_available_date); `committee_week` the committee money (gross, refunds, net);
# `donor_committee_cycle` the donor-keyed cycle money; `channel_map` the channel composition. A week crossing 1 January is
# two rows: they are summed per sector x chamber x week.
SGS_SEATS_W_SHEETS <- list(aligned = list(required = SGS_SEATS_W_REQUIRED, optional = FALSE),
                           aligned_sensitivity = list(required = character(0), optional = TRUE),
                           committee_week = list(required = character(0), optional = TRUE),
                           donor_committee_cycle = list(required = character(0), optional = TRUE),
                           channel_map = list(required = character(0), optional = TRUE))
SGS_SEATS_MONEY_BASES <- c(gross = "gross positive receipts (primary: dem_share_gross)", net = "net of refunds (sensitivity: dem_share)")

# Estimand A inference (coordinator's binding corrections of 2026-09-26, after the Codex reviews; fixed before any 09
# row was seen). The primary models have no lagged outcome (levels and changes); the regressors - the forecast change,
# cycle effects and a week-of-cycle trend per cycle - are exogenous, so a residual moving-block bootstrap within cycle
# holding them fixed gives intervals CONDITIONAL on the observed forecast path. The lagged-outcome model is a
# sensitivity: the same fixed-X bootstrap is only a conditional sensitivity there, and its dynamic inference comes from
# a recursive residual block bootstrap (the outcome rebuilt week by week from its own lag), labelled as such. Newey-West
# HAC errors are shown as a secondary check and never carry a p-value. No bootstrap p-value is proof of anything.
SGS_SEATS_HAC_LAGS <- c(2L, 4L, 8L)            # Bartlett lags in weeks, calendar-aware, within cycle, n / (n - k)
SGS_SEATS_BLOCKS <- c(3L, 5L)                  # residual moving-block lengths in weeks (both reported)
SGS_SEATS_BOOT_B <- 4999L
SGS_SEATS_W_COLS <- c("chamber", "source", "weighting", "money", "availability", "window", "model", "scope", "omitted_sector", "gate",
                      "n_weeks", "n_updates", "cycles", "estimate", "unit",
                      "fx3_ci_low", "fx3_ci_high", "fx3_p", "fx5_ci_low", "fx5_ci_high", "fx5_p",
                      "rec3_ci_low", "rec3_ci_high", "rec3_p", "rec5_ci_low", "rec5_ci_high", "rec5_p",
                      "hac2_se", "hac4_se", "hac8_se", "boot_note", "holm_family", "holm_fx3_p", "holm_fx5_p", "cycles_agree", "label")
SGS_SEATS_MODELS <- c(level = "levels, no lagged outcome (primary)", change = "changes, no lagged outcome (primary)",
                      lag = "levels with the lagged outcome (sensitivity; fixed-X bootstrap conditional, recursive bootstrap dynamic)")

# Read 09 read-only; any problem (absent, younger than the quiet period, unreadable, a column missing) leaves SEATS-W
# and SEATS-A-538 NOT BUILT with the reason, and never stops the run.
sgs_load_seats_weekly <- function(data_dir, now = NULL) {
  r <- sgs_seats_load_input(data_dir, SGS$SEATS_W_FILE, SGS_SEATS_W_SHEETS, "seats_weekly", now,
                            absent = "the dated within-cycle workbook is being built by another agent")
  if (!isTRUE(r$ok)) return(r)
  r$source$note <- "SEATS-W / SEATS-A-538: 09 aligned read at run time"
  r
}

.truthy_col <- function(v) toupper(trimws(as.character(v))) %in% c("TRUE", "1", "YES", "T", "1.0")

.seats_source_key <- function(source, model) {
  s <- tolower(trimws(as.character(source))); m <- tolower(trimws(as.character(model)))
  ifelse(grepl("538|fivethirtyeight", s), paste0("538 ", m), ifelse(grepl("crystal", s), "crystal_ball", s))
}
.seats_w_rows <- function(al, avail_col, basis) {
  if (is.null(al) || !nrow(al) || !avail_col %in% names(al)) return(NULL)
  num <- function(v) suppressWarnings(as.numeric(v))
  dc <- if (basis == "gross") "d_gross_usd" else "d_usd"; rc <- if (basis == "gross") "r_gross_usd" else "r_usd"
  if (!all(c(dc, rc, "primary_window", "model_version") %in% names(al))) return(NULL)
  data.frame(study_sector = as.character(al$study_sector), chamber = as.character(al$chamber), week_start = .seats_day(al$week_start),
             available_at = .seats_day(al[[avail_col]]), source = .seats_source_key(al$source, al$model_version),
             seats = num(al$expected_dem_seats), d = num(al[[dc]]), r = num(al[[rc]]), primary = .truthy_col(al$primary_window),
             stringsAsFactors = FALSE)
}
# 09 aligned -> the chamber x source x cycle x week series (primary_window weeks only): the pooled-dollar share (sum D /
# sum D + R over the units) and the equal-sector share (mean of the units' shares, >= 3 units with a valid share: D >= 0,
# R >= 0, D + R > 0), in percentage points, on gross positive receipts (primary) or net (sensitivity); the paired
# forecast's expected Democratic seats and its change from the previous week's pairing. verified_only = FALSE adds the
# aligned_sensitivity rows (their assumed availability dates).
sgs_seats_w_series <- function(al, sens = NULL, basis = "gross", verified_only = TRUE, omit_sector = NULL) {
  a <- .seats_w_rows(al, "available_at", basis)
  if (!verified_only) a <- rbind(a, .seats_w_rows(sens, "assumed_available_date", basis))
  n0 <- if (is.null(a)) 0L else nrow(a)
  empty <- sgs_rows_df(list(), c("chamber", "source", "cycle", "week_start", "week_of_cycle", "seats", "seats_unique", "d_usd",
                                 "r_usd", "share_pooled", "share_equal", "n_units", "n_valid_units"))
  if (is.null(a) || !nrow(a)) return(list(series = empty, dropped_late = 0L, rows_in = n0))
  a <- a[a$primary, , drop = FALSE]
  late <- !is.na(a$available_at) & !is.na(a$week_start) & !(a$available_at < a$week_start)
  a <- a[!late & !is.na(a$week_start) & !is.na(a$available_at) & !is.na(a$seats), , drop = FALSE]
  if (length(omit_sector)) a <- a[!a$study_sector %in% omit_sector, , drop = FALSE]
  if (!nrow(a)) return(list(series = empty, dropped_late = sum(late), rows_in = n0))
  # a week split at 1 January is two rows: one per sector x chamber x source x week
  k1 <- paste(a$study_sector, a$chamber, a$source, a$week_start, sep = "\r")
  if (anyDuplicated(k1)) {
    dd <- tapply(a$d, k1, sum); rr <- tapply(a$r, k1, sum)
    a <- a[!duplicated(k1), , drop = FALSE]
    kk <- paste(a$study_sector, a$chamber, a$source, a$week_start, sep = "\r")
    a$d <- as.numeric(dd[kk]); a$r <- as.numeric(rr[kk])
  }
  a$cycle <- .seats_cycle_of(a$week_start)
  a <- a[a$week_start + 6 < .seats_election_day(a$cycle), , drop = FALSE]
  a$week_of_cycle <- .seats_week_of_cycle(a$week_start, a$cycle)
  key <- paste(a$chamber, a$source, a$week_start, sep = "\r")
  gr <- split(seq_len(nrow(a)), key)
  rows <- lapply(gr, function(ix) {
    x <- a[ix, , drop = FALSE]
    den <- x$d + x$r
    okd <- !is.na(den) & den > 0 & x$d >= 0 & x$r >= 0
    sd <- sum(x$d, na.rm = TRUE); sr <- sum(x$r, na.rm = TRUE)
    list(chamber = x$chamber[1], source = x$source[1], cycle = x$cycle[1], week_start = as.numeric(x$week_start[1]),
         week_of_cycle = x$week_of_cycle[1], seats = x$seats[1], seats_unique = length(unique(x$seats)) == 1L,
         d_usd = sd, r_usd = sr, share_pooled = if (sd + sr > 0 && sd >= 0 && sr >= 0) 100 * sd / (sd + sr) else NA_real_,
         share_equal = if (sum(okd) >= 3) mean(100 * x$d[okd] / den[okd]) else NA_real_,
         n_units = length(unique(x$study_sector)), n_valid_units = sum(okd))
  })
  s <- sgs_rows_df(unname(rows), names(empty))
  s$week_start <- as.Date(s$week_start, origin = "1970-01-01")
  s <- s[order(s$chamber, s$source, s$week_start), , drop = FALSE]
  prev <- match(paste(s$chamber, s$source, s$cycle, s$week_start - 7), paste(s$chamber, s$source, s$cycle, s$week_start))
  s$d_seats <- s$seats - s$seats[prev]                         # the forecast revision that became available in the prior week
  for (w in c("pooled", "equal")) {
    v <- s[[paste0("share_", w)]]
    s[[paste0("lag_share_", w)]] <- v[prev]
    s[[paste0("d_share_", w)]] <- v - v[prev]
  }
  rownames(s) <- NULL
  list(series = s, dropped_late = sum(late), rows_in = n0)
}

# ---- the weekly fit engine (shared by estimands A and B) ---------------------------------------------------------------
.seats_seed <- function(...) {
  e <- sgs_seed_entropy(SGS$SEED, ...)
  as.integer(sum(e * c(1, 7, 13, 17, 19, 23)[seq_along(e)]) %% .Machine$integer.max)
}
# Rows must be in cycle then week order. TRUE when every cycle's weeks are consecutive.
.seats_contiguous <- function(cycle, week) all(vapply(split(week, cycle), function(w) length(w) < 2 || all(diff(w) == 1), TRUE))
# n x B matrix of row indices: moving blocks of L consecutive rows drawn within each cycle, truncated to its length.
.seats_block_index <- function(cycle, L, B) {
  n <- length(cycle)
  idx <- matrix(0L, n, B)
  for (cy in unique(cycle)) {
    r <- which(cycle == cy); nc <- length(r); Lc <- min(L, nc); nb <- ceiling(nc / Lc)
    st <- matrix(sample.int(nc - Lc + 1L, nb * B, replace = TRUE), nb, B)
    S <- st[rep(seq_len(nb), each = Lc), , drop = FALSE] + rep(0:(Lc - 1L), nb)
    idx[r, ] <- r[S[seq_len(nc), , drop = FALSE]]
  }
  idx
}
.seats_center <- function(e, cycle) e - stats::ave(e, cycle)
# Newey-West (Bartlett) standard error of column k: lags pair weeks exactly l apart in the same cycle (calendar gaps are
# never treated as adjacent), with the n / (n - p) adjustment.
.seats_hac_se <- function(X, u, cycle, week, L, k) {
  n <- nrow(X); p <- ncol(X)
  A <- solve(crossprod(X)); S <- X * u
  meat <- crossprod(S)
  key <- paste(cycle, week)
  if (L > 0) for (l in seq_len(L)) {
    j <- match(paste(cycle, week - l), key); ok <- which(!is.na(j))
    if (length(ok)) { G <- crossprod(S[ok, , drop = FALSE], S[j[ok], , drop = FALSE]); meat <- meat + (1 - l / (L + 1)) * (G + t(G)) }
  }
  V <- A %*% meat %*% A * n / (n - p)
  sqrt(max(V[k, k], 0))
}
.seats_basic_ci <- function(b, bs) {
  bs <- bs[is.finite(bs)]
  if (length(bs) < 2) return(c(NA_real_, NA_real_))
  q <- stats::quantile(bs - b, c(0.975, 0.025), names = FALSE)
  c(b - q[1], b - q[2])
}
.seats_null_p <- function(b, bn) { bn <- bn[is.finite(bn)]; if (!length(bn)) NA_real_ else (1 + sum(abs(bn) >= abs(b))) / (length(bn) + 1) }

# Fixed-X residual moving-block bootstrap of coefficient k (intervals conditional on the regressors; the null draws
# rebuild the outcome from the model without column k).
.seats_boot_fixed <- function(X, y, cycle, k, idx) {
  B <- ncol(idx); n <- nrow(X)
  pinv <- solve(crossprod(X), t(X))
  b <- as.vector(pinv %*% y); f <- as.vector(X %*% b); e <- .seats_center(y - f, cycle)
  Z <- X[, -k, drop = FALSE]
  f0 <- if (ncol(Z)) as.vector(Z %*% solve(crossprod(Z), crossprod(Z, y))) else rep(0, n)
  e0 <- .seats_center(y - f0, cycle)
  bs <- as.vector(pinv[k, , drop = FALSE] %*% (matrix(f, n, B) + matrix(e[idx], n, B)))
  bn <- as.vector(pinv[k, , drop = FALSE] %*% (matrix(f0, n, B) + matrix(e0[idx], n, B)))
  list(ci = .seats_basic_ci(b[k], bs), p = .seats_null_p(b[k], bn))
}

# Recursive residual moving-block bootstrap for a model with the lagged outcome (column `lag` of X): each draw rebuilds
# the outcome week by week from its own lag (the first model week of each cycle starts from the observed lag), then
# refits; the null draws are generated from the model without column k and refitted with it.
.seats_ols <- function(X, y) {
  f <- .lm.fit(X, y)
  cf <- rep(NA_real_, ncol(X))
  if (f$rank == ncol(X)) cf[f$pivot] <- f$coefficients
  cf
}
.seats_boot_recursive <- function(X, y, cycle, k, lag, idx) {
  B <- ncol(idx); n <- nrow(X)
  ylag <- X[, lag]
  segs <- split(seq_len(n), factor(cycle, levels = unique(cycle)))
  # y*_t = x_t'b + rho y*_{t-1} + e*_t within each cycle, from the observed lag of the cycle's first model week, for all
  # draws at once: Y*[s, ] = Psi %*% (xb[s] + E*[s, ]) + rho^(1..m) y_lag, Psi[t, j] = rho^(t - j) for t >= j
  gen <- function(xb, rho, E) {
    Y <- matrix(0, n, B)
    for (s in segs) {
      m <- length(s)
      Psi <- outer(seq_len(m), seq_len(m), function(t, j) ifelse(t >= j, rho^pmax(t - j, 0), 0))
      Y[s, ] <- Psi %*% (xb[s] + E[s, , drop = FALSE]) + (rho^seq_len(m)) * ylag[s[1]]
    }
    Y
  }
  # the refit of every draw at once (partitioned regression: the fixed columns W and the draw's own lag column)
  W <- X[, -lag, drop = FALSE]; kw <- match(colnames(X)[k], colnames(W))
  Pw <- solve(crossprod(W), t(W)); Mw <- diag(n) - W %*% Pw
  coef_k <- function(Y) {
    Lm <- matrix(0, n, B)
    for (s in segs) { m <- length(s); Lm[s[1], ] <- ylag[s[1]]; if (m > 1) Lm[s[-1], ] <- Y[s[-m], , drop = FALSE] }
    ML <- Mw %*% Lm
    g <- colSums(ML * (Mw %*% Y)) / colSums(ML * ML)
    as.vector(Pw[kw, , drop = FALSE] %*% (Y - Lm * rep(g, each = n)))
  }
  b <- .seats_ols(X, y); e <- .seats_center(as.vector(y - X %*% b), cycle)
  Z <- X[, -k, drop = FALSE]; b0 <- .seats_ols(Z, y); e0 <- .seats_center(as.vector(y - Z %*% b0), cycle)
  lag0 <- match(colnames(X)[lag], colnames(Z))
  xb <- as.vector(X[, -lag, drop = FALSE] %*% b[-lag]); rho <- b[lag]
  xb0 <- as.vector(Z[, -lag0, drop = FALSE] %*% b0[-lag0]); rho0 <- b0[lag0]
  bs <- coef_k(gen(xb, rho, matrix(e[idx], n, B)))
  bn <- coef_k(gen(xb0, rho0, matrix(e0[idx], n, B)))
  list(ci = .seats_basic_ci(b[k], bs), p = .seats_null_p(b[k], bn))
}

# One weekly model. d: rows in cycle then week order with columns y, the focal regressor, cycle, week_of_cycle (and
# lag_y for the lagged model). Returns NULL when the design is rank deficient or has no residual df.
.seats_fit <- function(d, formula, focal, seed_key, dynamic = FALSE, bootstrap = TRUE) {
  d <- d[order(d$cycle, d$week_of_cycle), , drop = FALSE]
  f <- eval(bquote(stats::lm(.(formula), data = d)))   # the formula itself in the printed Call, not "formula = formula"
  X <- stats::model.matrix(f); y <- stats::model.response(stats::model.frame(f)); u <- stats::residuals(f)
  k <- match(focal, colnames(X))
  if (is.na(k) || any(is.na(stats::coef(f))) || nrow(X) <= ncol(X)) return(NULL)
  b <- unname(stats::coef(f)[k])
  hac <- vapply(SGS_SEATS_HAC_LAGS, function(L) .seats_hac_se(X, u, d$cycle, d$week_of_cycle, L, k), 0)
  contiguous <- .seats_contiguous(d$cycle, d$week_of_cycle)
  # an outcome that never varies beyond the fitted terms (e.g. a group whose only candidate took one party's money every
  # week: a constant share) leaves nothing to resample; its bootstrap p would be an artefact, so none is computed
  degenerate <- sqrt(mean(u^2)) <= 1e-9 * max(1, stats::sd(y), max(abs(y)))
  fx <- list(); rec <- list(); note <- ""
  if (bootstrap && degenerate) {
    note <- "bootstrap not computed: the outcome never varies beyond the fitted terms (all residuals zero)"
  } else if (bootstrap && contiguous) {
    for (L in SGS_SEATS_BLOCKS) {
      set.seed(.seats_seed(seed_key, paste0("L", L)))
      idx <- .seats_block_index(d$cycle, L, SGS_SEATS_BOOT_B)
      fx[[paste0("L", L)]] <- .seats_boot_fixed(X, y, d$cycle, k, idx)
      if (dynamic) rec[[paste0("L", L)]] <- .seats_boot_recursive(X, y, d$cycle, k, match("lag_y", colnames(X)), idx)
    }
  } else if (bootstrap) {
    note <- "bootstrap not computed: calendar gaps inside a cycle (blocks and the recursion need consecutive weeks)"
  }
  list(fit = f, estimate = b, hac = hac, fx = fx, rec = rec, note = note, n = nrow(X), degenerate = degenerate,
       updates = sum(d[[focal]] != 0, na.rm = TRUE), cycles = paste(sort(unique(d$cycle)), collapse = ", "))
}

# The models of one weekly series (estimand A or a group series of estimand B). x: series rows with y_level, y_change,
# y_lag (the lagged level), the focal column, cycle, week_of_cycle. Returns a list of fitted entries by model x scope.
.seats_fit_series <- function(x, focal, seed_key, models = names(SGS_SEATS_MODELS), per_cycle = TRUE) {
  out <- list()
  for (m in models) {
    d0 <- x
    d0$y <- if (m == "change") d0$y_change else d0$y_level
    d0$lag_y <- d0$y_lag
    d0 <- d0[!is.na(d0$y) & !is.na(d0[[focal]]) & (m != "lag" | !is.na(d0$lag_y)), , drop = FALSE]
    if (nrow(d0) < 4) next
    multi <- length(unique(d0$cycle)) > 1
    rhs <- function(multi_) {
      base <- switch(m, level = if (multi_) "factor(cycle) + factor(cycle):week_of_cycle" else "week_of_cycle",
                     change = if (multi_) "factor(cycle)" else "1",
                     lag = if (multi_) "lag_y + factor(cycle) + factor(cycle):week_of_cycle" else "lag_y + week_of_cycle")
      stats::as.formula(paste0("y ~ ", focal, " + ", base))
    }
    scopes <- c("pooled", if (multi && per_cycle) paste0("cycle ", sort(unique(d0$cycle))))
    for (sc in scopes) {
      dd <- if (sc == "pooled") d0 else d0[d0$cycle == as.numeric(sub("cycle ", "", sc)), , drop = FALSE]
      boot <- nrow(dd) >= SGS$SEATS_MIN_WEEKS
      r <- tryCatch(.seats_fit(dd, rhs(sc == "pooled" && multi), focal, paste(seed_key, m, sc), dynamic = m == "lag", bootstrap = boot),
                    error = function(e) NULL)
      if (is.null(r)) next
      r$model <- m; r$scope <- sc
      r$gate <- if (isTRUE(r$degenerate)) "descriptive only (the outcome never varies beyond the fitted terms: nothing to resample)" else
        if (!boot) paste0("descriptive only (", r$n, " usable weeks < ", SGS$SEATS_MIN_WEEKS, ")") else
        if (!length(r$fx)) "descriptive only (calendar gaps inside a cycle: no block bootstrap)" else "estimated"
      out[[paste(m, sc)]] <- r
    }
  }
  out
}

# Fitted entries -> rows of the estimates table (common fields supplied by the caller).
.seats_fit_rows <- function(fits, common, unit_of) {
  lapply(fits, function(r) {
    g <- function(lst, L, what) { z <- lst[[paste0("L", L)]]; if (is.null(z)) NA_real_ else if (what == "p") z$p else z$ci[if (what == "lo") 1 else 2] }
    c(common, list(model = r$model, scope = r$scope, gate = r$gate, n_weeks = r$n, n_updates = r$updates, cycles = r$cycles,
                   estimate = r$estimate, unit = unit_of(r$model),
                   fx3_ci_low = g(r$fx, 3, "lo"), fx3_ci_high = g(r$fx, 3, "hi"), fx3_p = g(r$fx, 3, "p"),
                   fx5_ci_low = g(r$fx, 5, "lo"), fx5_ci_high = g(r$fx, 5, "hi"), fx5_p = g(r$fx, 5, "p"),
                   rec3_ci_low = g(r$rec, 3, "lo"), rec3_ci_high = g(r$rec, 3, "hi"), rec3_p = g(r$rec, 3, "p"),
                   rec5_ci_low = g(r$rec, 5, "lo"), rec5_ci_high = g(r$rec, 5, "hi"), rec5_p = g(r$rec, 5, "p"),
                   hac2_se = r$hac[1], hac4_se = r$hac[2], hac8_se = r$hac[3], boot_note = r$note,
                   holm_family = "", holm_fx3_p = NA_real_, holm_fx5_p = NA_real_, cycles_agree = "",
                   label = if (identical(r$model, "lag")) "sensitivity: fixed-X interval conditional; recursive interval dynamic" else
                     "conditional on the observed forecast path"))
  })
}

# One weekly fit as a printed block: header, the variables, the real summary(lm()) output, then the labelled study
# inference (Paul's presentation rule: every regression as its summary(lm()) plus the bootstrap block).
.seats_block <- function(r, header, dv) {
  g <- function(lst, L) { z <- lst[[paste0("L", L)]]; if (is.null(z)) "not computed" else paste0(sgs_ci_text(z$ci[1], z$ci[2]), ", p ", sgs_fmt(z$p)) }
  c(strrep("=", 100), header, strrep("=", 100), dv, "", utils::capture.output(summary(r$fit)),
    "--- the Std. Error, t value and Pr(>|t|) above are classical OLS (independent weekly errors) and are NOT the study's inference, which is:",
    paste0("  study inference   d_seats ", sgs_fmt(r$estimate), " (", SGS_SEATS_MODELS[[r$model]], ")"),
    paste0("    fixed-X residual block bootstrap within cycle, conditional (", SGS_SEATS_BOOT_B, " draws): 3-week blocks ",
           g(r$fx, 3), "; 5-week blocks ", g(r$fx, 5)),
    if (identical(r$model, "lag")) paste0("    recursive residual block bootstrap, dynamic: 3-week blocks ", g(r$rec, 3), "; 5-week blocks ", g(r$rec, 5)),
    paste0("    Newey-West HAC SE (secondary, no p-value): lags 2 / 4 / 8 weeks ", sgs_fmt(r$hac[1]), " / ", sgs_fmt(r$hac[2]),
           " / ", sgs_fmt(r$hac[3]), if (nzchar(r$note)) paste0("; ", r$note) else ""),
    paste0("  gate              ", r$gate),
    paste0("  support           ", r$n, " weeks, cycles ", r$cycles, ", ", r$updates, " forecast updates ",
           "(effectively a one-election test until 2020 joins)"), "")
}
.seats_dv_text <- function(model, what, ch) {
  paste0("Variables: y = ", if (identical(model, "change")) "the week-on-week change in " else "", what, "; d_seats = the prior week's ",
         "change in 538 Lite expected Democratic ", ch, " seats", if (!identical(model, "change")) "; week_of_cycle = linear week trend" else "",
         if (identical(model, "lag")) "; lag_y = the prior week's y" else "")
}

# Per-cycle agreement text for the pooled rows of each (common key, model).
.seats_agree <- function(rows) {
  key <- vapply(rows, function(r) paste(r$chamber, r$source, r$weighting, r$money %||% "", r$availability, r$window, r$omitted_sector, r$model, sep = "|"), "")
  for (kk in unique(key)) {
    ix <- which(key == kk)
    cyc <- ix[vapply(rows[ix], function(r) startsWith(r$scope, "cycle "), TRUE)]
    if (length(cyc) < 2) next
    sg <- vapply(rows[cyc], function(r) sign(r$estimate), 0)
    txt <- paste0(if (length(unique(sg)) == 1L) "same sign in every cycle" else "signs differ across cycles", " (",
                  paste0(vapply(rows[cyc], function(r) paste0(r$scope, " ", sgs_fmt(r$estimate)), ""), collapse = ", "), ")")
    for (i in ix) rows[[i]]$cycles_agree <- txt
  }
  rows
}

# Holm within a named family, separately for the 3- and 5-week fixed-X bootstrap p-values.
.seats_holm <- function(rows, in_family, family_of) {
  fam <- vapply(rows, function(r) if (in_family(r)) family_of(r) else "", "")
  for (f in setdiff(unique(fam), "")) {
    ix <- which(fam == f)
    for (L in c(3, 5)) {
      p <- vapply(rows[ix], function(r) r[[paste0("fx", L, "_p")]], 0)
      adj <- rep(NA_real_, length(p)); ok <- !is.na(p)
      adj[ok] <- stats::p.adjust(p[ok], method = "holm", n = length(p))
      for (j in seq_along(ix)) { rows[[ix[j]]][[paste0("holm_fx", L, "_p")]] <- adj[j]; rows[[ix[j]]]$holm_family <- f }
    }
  }
  rows
}

# Estimand A for every chamber x source x weighting x money basis x availability x window, pooled over cycles and per
# cycle, and the leave-one-sector-out refits of the primary specification (every sector in turn, telecom included).
sgs_seats_w_run <- function(w) {
  al <- w$wb$frames$aligned; sens <- w$wb$frames$aligned_sensitivity
  unit_of <- function(m) if (m == "change") "percentage points of change in the Democratic share per forecast Democratic seat" else
    "percentage points of the week's Democratic share per forecast Democratic seat"
  out <- list(); blocks <- character(0); support <- list(); ser_all <- NULL
  primary <- tolower(SGS$SEATS_W_PRIMARY)
  post <- SGS$SEATS_POST_PRIMARY_START
  sens_primary <- if (!is.null(sens) && "primary_window" %in% names(sens)) sum(.truthy_col(sens$primary_window)) else 0L
  prep <- function(x, wt) {
    x$y_level <- x[[paste0("share_", wt)]]; x$y_change <- x[[paste0("d_share_", wt)]]; x$y_lag <- x[[paste0("lag_share_", wt)]]
    x
  }
  for (basis in names(SGS_SEATS_MONEY_BASES)) for (ver in c("verified", if (sens_primary > 0) "all")) {
    sr <- sgs_seats_w_series(al, sens, basis = basis, verified_only = ver == "verified")
    s <- sr$series
    if (ver == "verified" && basis == "gross") ser_all <- sr
    if (!nrow(s)) next
    avail <- if (ver == "verified") "availability verified (primary)" else "incl. aligned_sensitivity rows (unverified; sensitivity)"
    money <- if (basis == "gross") "gross positive (primary)" else "net (sensitivity)"
    for (ch in unique(s$chamber)) for (src in unique(s$source[s$chamber == ch])) {
      x <- s[s$chamber == ch & s$source == src, , drop = FALSE]
      if (ver == "verified" && basis == "gross") for (cy in sort(unique(x$cycle))) {
        xc <- x[x$cycle == cy, , drop = FALSE]
        support[[length(support) + 1L]] <- list(chamber = ch, source = src, cycle = cy, weeks = nrow(xc),
                                                weeks_with_change = sum(!is.na(xc$d_seats)),
                                                forecast_updates = sum(xc$d_seats != 0, na.rm = TRUE), units = max(xc$n_units),
                                                min_valid_units = min(xc$n_valid_units), non_unique_forecast_weeks = sum(!xc$seats_unique),
                                                post_primary_weeks = if (!is.na(post[as.character(cy)])) sum(xc$week_start >= as.Date(post[as.character(cy)])) else NA_real_)
      }
      for (win in c("all weeks", "post-primary")) {
        xw <- x
        if (win == "post-primary") {
          st <- as.Date(post[as.character(xw$cycle)])
          xw <- xw[!is.na(st) & xw$week_start >= st, , drop = FALSE]
          if (!nrow(xw)) next
        }
        for (wt in c("pooled", "equal")) {
          fits <- .seats_fit_series(prep(xw, wt), "d_seats", paste(ch, src, wt, basis, ver, win))
          common <- list(chamber = ch, source = src, weighting = if (wt == "pooled") "pooled-dollar" else "equal-sector", money = money,
                         availability = avail, window = win, omitted_sector = "")
          out <- c(out, .seats_fit_rows(fits, common, unit_of))
          if (ver == "verified" && basis == "gross" && win == "all weeks" && src == primary) {
            for (nm in names(fits)) {
              r <- fits[[nm]]
              if (r$scope != "pooled") next
              blocks <- c(blocks, .seats_block(r,
                paste0("==== SEATS-W ", ch, " ", r$model, " (", src, ", ", common$weighting, ", gross positive receipts, availability verified)  [EXPLORATORY; ", r$gate, "]"),
                .seats_dv_text(r$model, paste0("the week's Democratic share D / (D + R) of gross positive receipts to ", ch, " candidate committees, ",
                                               common$weighting, " (percentage points)"), ch)))
            }
          }
        }
      }
      # leave one sector out: primary source, gross, availability verified, all weeks, pooled over cycles
      if (ver == "verified" && basis == "gross" && src == primary) {
        secs <- sort(unique(as.character(al$study_sector)))
        for (sec in secs) {
          so <- sgs_seats_w_series(al, sens, basis = "gross", verified_only = TRUE, omit_sector = sec)$series
          xo <- so[so$chamber == ch & so$source == src, , drop = FALSE]
          if (!nrow(xo)) next
          for (wt in c("pooled", "equal")) {
            fits <- .seats_fit_series(prep(xo, wt), "d_seats", paste(ch, src, wt, "loso", sec), per_cycle = FALSE)
            common <- list(chamber = ch, source = src, weighting = if (wt == "pooled") "pooled-dollar" else "equal-sector", money = money,
                           availability = avail, window = "all weeks", omitted_sector = sec)
            out <- c(out, .seats_fit_rows(fits, common, unit_of))
          }
        }
      }
    }
  }
  out <- .seats_agree(out)
  out <- .seats_holm(out, function(r) r$source == primary && startsWith(r$availability, "availability verified") && r$window == "all weeks" &&
                       startsWith(r$money, "gross") && !nzchar(r$omitted_sector) && r$scope == "pooled" && r$model %in% c("level", "change") &&
                       r$gate == "estimated",
                     function(r) paste0("A overall response, ", r$chamber))
  list(estimates = sgs_rows_df(out, SGS_SEATS_W_COLS), blocks = blocks,
       support = sgs_rows_df(support, c("chamber", "source", "cycle", "weeks", "weeks_with_change", "forecast_updates", "units",
                                        "min_valid_units", "non_unique_forecast_weeks", "post_primary_weeks")),
       series = ser_all$series, dropped_late = ser_all$dropped_late %||% 0L, sens_primary_rows = sens_primary,
       aligned_rows = nrow(al), aligned_primary_rows = sum(.truthy_col(al$primary_window)))
}

# The chamber x cycle series plot (the actual time series, shown before any model): pooled-dollar and equal-sector
# Democratic share and the paired expected Democratic seats, primary source.
sgs_seats_w_plot <- function(series, path) {
  s <- series[series$source == tolower(SGS$SEATS_W_PRIMARY), , drop = FALSE]
  if (!nrow(s)) return(invisible(FALSE))
  grDevices::png(path, width = 1400, height = 450 * length(unique(s$chamber)), res = 110)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mfrow = c(length(unique(s$chamber)), 1), mar = c(4, 4, 3, 4))
  for (ch in unique(s$chamber)) {
    x <- s[s$chamber == ch, , drop = FALSE]
    graphics::plot(x$week_start, x$share_pooled, type = "l", ylim = c(0, 100), xlab = "week", ylab = "Democratic share (pp)",
                   main = paste0(ch, ": weekly Democratic share of D + R and the prior 538 Lite expected Democratic seats"))
    graphics::lines(x$week_start, x$share_equal, lty = 2)
    graphics::par(new = TRUE)
    graphics::plot(x$week_start, x$seats, type = "l", col = "grey40", axes = FALSE, xlab = "", ylab = "")
    graphics::axis(4); graphics::mtext("expected Democratic seats", side = 4, line = 2.5)
    graphics::legend("topleft", c("pooled-dollar share", "equal-sector share", "expected seats (right axis)"), lty = c(1, 2, 1),
                     col = c("black", "black", "grey40"), bty = "n")
  }
  invisible(TRUE)
}

# 09 channel_map -> gross positive dollars by chamber x channel with the chamber share.
.seats_channels <- function(w) {
  cm <- w$wb$frames$channel_map
  if (is.null(cm) || !all(c("channel", "chamber", "gross_usd") %in% names(cm))) return(NULL)
  g <- suppressWarnings(as.numeric(cm$gross_usd)); n <- suppressWarnings(as.numeric(cm$n_rows))
  k <- paste(cm$chamber, cm$channel, sep = "\r")
  out <- data.frame(chamber = sub("\r.*$", "", unique(k)), channel = sub("^.*\r", "", unique(k)),
                    gross_usd = as.numeric(tapply(g, k, sum, na.rm = TRUE)[unique(k)]), n_rows = as.numeric(tapply(n, k, sum, na.rm = TRUE)[unique(k)]),
                    stringsAsFactors = FALSE)
  tot <- tapply(out$gross_usd, out$chamber, sum)
  out$share <- out$gross_usd / as.numeric(tot[out$chamber])
  out[order(out$chamber, -out$gross_usd), , drop = FALSE]
}
# 09 donor_committee_cycle -> continuing donors between the 2022 and 2024 cycles per chamber (DESCRIPTIVE), and the
# linkage quality (report person keys vs the name / state / ZIP fallback, by gross dollars).
.seats_donors <- function(w) {
  dc <- w$wb$frames$donor_committee_cycle
  if (is.null(dc) || !all(c("donor_key", "key_type", "fec_cycle", "chamber", "party", "gross_usd") %in% names(dc))) return(NULL)
  g <- suppressWarnings(as.numeric(dc$gross_usd)); g[is.na(g)] <- 0
  kt <- as.character(dc$key_type)
  lk <- tapply(g, kt, sum)
  linkage <- paste0(paste0(names(lk), " ", vapply(as.numeric(lk) / sum(lk), .fmt_pct, ""), " of gross dollars (",
                           vapply(as.numeric(table(kt)[names(lk)]), sgs_py_str, ""), " rows)"), collapse = "; ")
  cyc <- c("2021-2022" = 2022, "2023-2024" = 2024)
  rows <- list()
  for (ch in SGS_SEATS_CHAMBERS) {
    k <- dc$chamber == ch & dc$fec_cycle %in% names(cyc) & g > 0 & dc$party %in% c("D", "R")
    x <- data.frame(key = dc$donor_key[k], cycle = cyc[dc$fec_cycle[k]], party = dc$party[k], g = g[k], stringsAsFactors = FALSE)
    s22 <- unique(x$key[x$cycle == 2022]); s24 <- unique(x$key[x$cycle == 2024]); cont <- intersect(s22, s24)
    for (cy in c(2022, 2024)) {
      y <- x[x$cycle == cy, , drop = FALSE]; yc <- y[y$key %in% cont, , drop = FALSE]
      sh <- function(z) { d <- sum(z$g[z$party == "D"]); r <- sum(z$g[z$party == "R"]); if (d + r > 0) d / (d + r) else NA_real_ }
      rows[[length(rows) + 1L]] <- list(chamber = ch, cycle = cy, donors = length(unique(y$key)), continuing = length(cont),
                                        entering = if (cy == 2024) length(setdiff(s24, s22)) else NA_real_,
                                        exiting = if (cy == 2022) length(setdiff(s22, s24)) else NA_real_,
                                        dshare_all = sh(y), dshare_continuing = sh(yc), gross_all = sum(y$g), gross_continuing = sum(yc$g))
    }
  }
  list(table = sgs_rows_df(rows, c("chamber", "cycle", "donors", "continuing", "entering", "exiting", "dshare_all", "dshare_continuing",
                                   "gross_all", "gross_continuing")), linkage = linkage)
}

# All SEATS inputs of a run. Returns list(tables, coverage, calls, built, source, weekly_ok, weekly_reason, w, race,
# data_dir, shift_year, channels, donors).
sgs_build_seats <- function(wbs, shift, data_dir, now = NULL) {
  a <- sgs_build_seats_tables(wbs, shift)
  w <- sgs_load_seats_weekly(data_dir, now)
  built <- a$built
  srcs <- list(); wr <- NULL
  if (isTRUE(w$ok)) {
    srcs$seats_weekly <- w$source
    wr <- sgs_seats_w_run(w)
    built$seats_weekly <- list(built = nrow(wr$estimates) > 0,
                               note = paste0("09 aligned: ", wr$aligned_rows, " rows (", wr$aligned_primary_rows, " in the primary window); ",
                                             wr$dropped_late, " primary rows with available_at not strictly before week_start dropped; ",
                                             "aligned_sensitivity primary-window rows: ", wr$sens_primary_rows))
    # SEATS-A-538: the last 538 Lite forecast available before the cycle's last whole pre-election week (verified)
    s <- wr$series
    fin <- if (!is.null(s) && nrow(s)) s[s$source == tolower(SGS$SEATS_W_PRIMARY), , drop = FALSE] else s
    ok538 <- !is.null(fin) && nrow(fin) > 0
    built$seats_538 <- list(built = ok538, note = if (ok538) "538 Lite expected seats from 09 aligned (availability verified)" else
      "09 aligned has no verified 538 Lite rows")
    for (key in names(SGS_SEATS_CHAMBERS)) {
      tn <- paste0("seats_cycle_", key); ch <- SGS_SEATS_CHAMBERS[[key]]
      if (!ok538) next
      f <- fin[fin$chamber == ch, , drop = FALSE]
      if (!nrow(f)) next
      last <- tapply(seq_len(nrow(f)), f$cycle, function(ix) f$seats[ix][which.max(f$week_start[ix])])
      calls <- a$calls[a$calls$chamber == ch, , drop = FALSE]
      before <- calls$dem_seats_before[match(a$tables[[tn]]$year, calls$election_year)]
      a$tables[[tn]]$seat_net_gain_538 <- unname(last[as.character(a$tables[[tn]]$year)]) - before
    }
  } else {
    built$seats_weekly <- list(built = FALSE, note = w$reason)
    built$seats_538 <- list(built = FALSE, note = w$reason)
  }
  race <- sgs_build_seats_race(data_dir, now, w = if (isTRUE(w$ok)) w else NULL, wr = wr)
  for (nm in names(race$sources)) srcs[[nm]] <- race$sources[[nm]]
  built$seats_race <- list(built = isTRUE(race$ok), note = race$reason)
  channels <- if (isTRUE(w$ok)) tryCatch(.seats_channels(w), error = function(e) NULL) else NULL
  donors <- if (isTRUE(w$ok)) tryCatch(.seats_donors(w), error = function(e) NULL) else NULL
  # a carries its own element "built" (seats_calls only); drop it so the combined list has one "built" (seats_calls,
  # seats_weekly, seats_538, seats_race). A duplicated name made seats$built return a$built and left SEATS-A-538 not built.
  a$built <- NULL
  c(a, list(built = built, source = srcs, weekly_ok = isTRUE(w$ok), weekly_reason = w$reason %||% "", w = wr, race = race,
            data_dir = data_dir, shift_year = shift$shift_year, channels = channels, donors = donors))
}

# ---- the gate --------------------------------------------------------------------------------------------------------
sgs_decide_seats <- function(spec, tables, include_partial = FALSE) {
  weekly <- identical(spec$family, "SEATS-W")
  win <- if (weekly) SGS$SEATS_W_WINDOW else SGS$SEATS_WINDOW
  sspec <- sgs_sample_spec(spec)
  smp <- sgs_build_sample(tables, sspec, win, include_partial = include_partial)
  min_c <- spec$preview_min_years %||% NA_integer_
  if (length(min_c) != 1L || is.na(min_c)) min_c <- 2L
  att <- sgs_assess(smp, sspec, min_c, kind = if (weekly) "weekly" else "election cycles")
  word <- function(x) gsub("distinct years", "election cycles", gsub(" of (\\d+) years", " of \\1 cycles", x))
  att$reasons <- word(att$reasons); att$compact_parts <- word(att$compact_parts)
  if (att$ok) return(sgs_decision(SGS_ESTIMABLE, window = win, window_kind = if (weekly) "weeks" else "election cycles", attempts = list(att)))
  sgs_decision(SGS_NOT_ESTIMABLE, attempts = list(att), reason = sgs_attempt_text(att))
}

# ---- the registry family -------------------------------------------------------------------------------------------
.seats_family <- function() {
  out <- list()
  add <- function(s) out[[length(out) + 1L]] <<- s
  for (key in names(SGS_SEATS_CHAMBERS)) {
    ch <- SGS_SEATS_CHAMBERS[[key]]
    tab <- paste0("seats_cycle_", key)
    call_txt <- paste0("the Democratic net ", ch, " seat gain of the cycle's final Crystal Ball call (", ch, " seats)")
    for (b in names(SGS_SEATS_BASES)) {
      share <- paste0("dem_share_", b)
      id0 <- paste0("SEATS-A-", ch, "-", b)
      req <- c("seats_calls", if (b == "cand") "shift_08" else "shift_04")
      what <- if (b == "cand") paste0("giving to ", ch, " candidate committees (08 ", SGS$CHAMBER_SHEET, ")") else
        "all party-labelled 04 giving (party D / R)"
      dvl <- function(kind) paste0(switch(kind, share = "Democratic share D / (D + R) of ", d = "dollars to Democrats in ",
                                          r = "dollars to Republicans in "), what, " per election cycle",
                                   if (kind == "share") ", 0-1" else ", $M 2025")
      mk <- function(sfx, dv, focal, controls = character(0), fe = "sector", weight = NA_character_, min_c = 2L, grp = id0,
                     ps = TRUE, unit = NA_character_, kind = "share", txt = "", extra_req = character(0)) {
        sgs_test_spec(
          id = paste0(id0, sfx), family = "SEATS-A", label = "DESCRIPTIVE", dv = dv, focal = focal, controls = controls, fe = fe,
          table = tab, unit = "Mentat industry x election cycle", gate = "seats", inference = "none", window_rule = SGS_SEATS_A_RULE,
          requires = c(req, extra_req), weight_var = weight, trend_group = grp,
          predicted_sign = if (ps) setNames("+", focal[1]) else character(0), identification = TRUE, preview_min_years = min_c,
          flag = SGS_SEATS_A_FLAG, dv_label = dvl(kind), dv_unit = unit,
          note = paste0(SGS_SEATS_QUESTION, " SEATS-A (DESCRIPTIVE): ", txt, " ", SGS_SEATS_PREDICTOR_DEF, " ", SGS_SEATS_OUTCOME_DEF,
                        " ", SGS_SEATS_A_FLAG, "."))
      }
      add(mk("", share, "seat_net_gain",
             txt = paste0("average-sector estimand: the cycle's Democratic share of ", what, " on ", call_txt, ", unit baselines ",
                          "(each unit counts equally).")))
      add(mk("-W", share, "seat_net_gain", weight = paste0("base_real_m_", b),
             txt = paste0("dollar-weighted estimand: as ", id0, ", each unit-cycle weighted by its D + R dollars ($M 2025).")))
      add(mk("-LAG", share, "seat_net_gain", controls = paste0(share, "_lag"), fe = "intercept",
             txt = paste0("lagged allocation: the cycle's share on ", call_txt, " and the unit's prior-cycle share (a common level, ",
                          "no unit baselines); needs two cycles with a prior cycle (the 2020 cycle).")))
      add(mk("-CHG", paste0(share, "_change"), "seat_net_gain_change", fe = character(0), min_c = 1L,
             txt = paste0("changes: the change in the unit's share between consecutive cycles on the change in the forecast net ",
                          "gain (no intercept: an unchanged outlook predicts an unchanged share).")))
      add(mk("-D", paste0("d_real_m_", b), "seat_net_gain", grp = paste0(id0, "-D"), ps = FALSE, kind = "d",
             unit = "$M 2025 to Democrats", txt = paste0("dollars to Democrats in ", what, " on ", call_txt, ", unit baselines.")))
      add(mk("-R", paste0("r_real_m_", b), "seat_net_gain", grp = paste0(id0, "-R"), ps = FALSE, kind = "r",
             unit = "$M 2025 to Republicans", txt = paste0("dollars to Republicans in ", what, " on ", call_txt, ", unit baselines.")))
      add(sgs_spec_update(mk("", share, "seat_net_gain_538", grp = paste0("SEATS-A-538-", ch, "-", b), extra_req = "seats_538",
                             txt = paste0("the same as ", id0, " with 538's probability-weighted expected ", ch, " seats (the ",
                                          "538 Lite expected seats paired with the cycle's last whole pre-election week, 09 aligned) ",
                                          "in place of the point call.")),
                          id = paste0("SEATS-A-538-", ch, "-", b)))
    }
  }
  out
}

# ---- report ----------------------------------------------------------------------------------------------------------
.fmt_usd <- function(x) if (is.na(x)) "n/a" else paste0("$", sgs_py_fixed(x, 0, comma = TRUE))
.fmt_pct <- function(x) if (is.na(x)) "n/a" else paste0(sgs_py_fixed(100 * x, 1), "%")

sgs_seats_md <- function(order_, est_rows, coef_rows, results, seats) {
  rows <- setNames(est_rows, vapply(est_rows, `[[`, "", "test_id"))
  calls <- seats$calls
  wc <- calls[calls$election_year >= SGS$SEATS_WINDOW[1] - 2 & calls$election_year <= SGS$PANEL_LAST_YEAR, , drop = FALSE]
  L <- c(SGS_SEATS_QUESTION, "", paste0("- ", SGS_SEATS_PREDICTOR_DEF), paste0("- ", SGS_SEATS_OUTCOME_DEF),
         paste0("- SEATS-A: ", SGS_SEATS_A_FLAG, "."), "",
         "**The forecast Democratic net seat gain (Crystal Ball final pre-election call)**", "",
         "| chamber | election | projected D seats | D seats before | net gain used | stated net change | definition |",
         "|---|---:|---:|---:|---:|---:|---|")
  for (i in seq_len(nrow(wc))) {
    x <- wc[i, , drop = FALSE]
    L <- c(L, paste0("| ", x$chamber, " | ", sgs_int_str(x$election_year), " | ", if (is.na(x$proj_dem_seats)) "" else sgs_py_str(x$proj_dem_seats),
                     " | ", if (is.na(x$dem_seats_before)) "" else sgs_py_str(x$dem_seats_before), " | ",
                     if (is.na(x$seat_net_gain)) "n/a" else sprintf("%+g", x$seat_net_gain), " | ",
                     if (is.na(x$stated_net_change)) "" else sprintf("%+g", x$stated_net_change), " | ", .md_escape(x$definition), " |"))
  }
  # coverage: every unit x cycle, shares with their D and R dollars and coverage
  cv <- seats$coverage
  L <- c(L, "", "**Coverage: the party share with its D and R dollars (nominal) and coverage (D + R / included receipts), per unit x cycle**", "",
         "| chamber | base | unit | cycle | D share | D$ | R$ | D + R | coverage | status |", "|---|---|---|---:|---:|---:|---:|---:|---:|---|")
  shown <- cv[cv$cycle >= SGS$SEATS_WINDOW[1] & cv$cycle <= SGS$PANEL_LAST_YEAR, , drop = FALSE]
  for (i in seq_len(nrow(shown))) {
    x <- shown[i, , drop = FALSE]
    if (x$base == "all" && x$chamber == "Senate") next                   # the all-giving outcome is the same for both chambers
    L <- c(L, paste0("| ", if (x$base == "all") "both" else x$chamber, " | ", x$base, " | ", x$study_sector, " | ", sgs_int_str(x$cycle), " | ",
                     .fmt_pct(x$dem_share), " | ", .fmt_usd(x$d_usd), " | ", .fmt_usd(x$r_usd), " | ", .fmt_usd(x$base_usd), " | ",
                     .fmt_pct(x$coverage), " | ", .md_escape(x$status), " |"))
  }
  # pooled over units (dollar totals) per complete cycle
  L <- c(L, "", "Totals over the units with a complete cycle (the dollar-weighted picture):", "")
  for (ch in c("House", "Senate")) for (b in names(SGS_SEATS_BASES)) {
    if (b == "all" && ch == "Senate") next
    x <- cv[cv$chamber == ch & cv$base == b & cv$status == SGS_OBS, , drop = FALSE]
    for (cy in sort(unique(x$cycle))) {
      y <- x[x$cycle == cy, , drop = FALSE]
      d <- sum(y$d_usd); r <- sum(y$r_usd)
      L <- c(L, paste0("- ", if (b == "all") "all party-labelled giving" else paste0(ch, " candidate committees"), ", cycle ", cy, ": D ",
                       .fmt_usd(d), ", R ", .fmt_usd(r), ", D share ", .fmt_pct(d / (d + r)), " (", nrow(y), " units)"))
    }
  }
  # results
  ids <- names(order_)[vapply(order_, function(t) identical(t$family, "SEATS-A"), TRUE)]
  L <- c(L, "", "**SEATS-A (DESCRIPTIVE): estimates as fixed contrasts of the cycles; no significance claim**", "",
         "| test | outcome | estimand | status | n | cycles | term | estimate | plain units | identification / reason |",
         "|---|---|---|---|---:|---|---|---:|---|---|")
  for (id in ids) {
    r <- rows[[id]]; t <- order_[[id]]
    if (is.null(r)) next
    est <- if (grepl("-W$", id)) "dollar-weighted" else if (grepl("-LAG$", id)) "average-sector, lagged allocation" else
      if (grepl("-CHG$", id)) "average-sector, changes" else "average-sector"
    out <- if (grepl("-D$", id)) "D$" else if (grepl("-R$", id)) "R$" else "D share"
    if (!identical(r$status, SGS_ESTIMABLE)) {
      L <- c(L, paste0("| ", id, " | ", out, " | ", est, " | ", r$status, " | | | | | | ",
                       .md_escape(if (nzchar(.txt0(r$reason_short))) r$reason_short else .txt0(r$reason)), " |"))
      next
    }
    ident <- results[[id]]$identification$short %||% character(0)
    for (c in Filter(function(c) identical(c$test_id, id) && is.null(c$left_out), coef_rows)) {
      pl <- sgs_trend_plain(c$estimate, c$unit)
      L <- c(L, paste0("| ", id, " | ", out, " | ", est, " | ", r$status, " | ", sgs_py_str(r$n), " | ", .txt0(r$years), " | ",
                       c$coefficient, " | ", sgs_fmt(c$estimate), " | ", .md_escape(pl$text), " | ",
                       .md_escape(if (c$coefficient %in% names(ident)) ident[[c$coefficient]] else ""), " |"))
    }
  }
  # calendar-year cross-check against the Codex retrospective note (calendar 2022 vs 2024 equal-sector shares of 08)
  xc <- character(0)
  sy <- seats$shift_year
  if (!is.null(sy)) for (ch in SGS_SEATS_CHAMBERS) {
    col <- paste0("dem_share_", tolower(ch)); stc <- paste0(col, "_status")
    if (!all(c(col, stc) %in% names(sy))) next
    a22 <- sy[sy$year == 2022 & sy[[stc]] %in% SGS_USABLE_STATUSES, c("study_sector", col)]
    a24 <- sy[sy$year == 2024 & sy[[stc]] %in% SGS_USABLE_STATUSES, c("study_sector", col)]
    m <- merge(a22, a24, by = "study_sector", suffixes = c("_22", "_24"))
    if (!nrow(m)) next
    dlt <- 100 * (m[[paste0(col, "_24")]] - m[[paste0(col, "_22")]])
    c22 <- calls$seat_net_gain[calls$chamber == ch & calls$election_year == 2022]
    c24 <- calls$seat_net_gain[calls$chamber == ch & calls$election_year == 2024]
    if (!length(c22) || !length(c24)) next
    same <- sum(sign(dlt) == sign(c24 - c22))
    xc <- c(xc, paste0("- ", ch, " candidate committees, calendar 2022 -> 2024 (not cycles): equal-sector Democratic share ",
                       sprintf("%+.4f", mean(dlt)), " pp (", nrow(m), " units; ", same, " move in the direction of the forecast ",
                       "change ", sprintf("%+g", c22), " -> ", sprintf("%+g", c24), ")"))
  }
  if (length(xc)) {
    L <- c(L, "", paste0("Cross-check with the Codex retrospective note (calendar years 2022 and 2024, equal-sector 08 shares: House ",
                         "+0.7767 pp with five of eight units moving with the forecast change, Senate -0.9076 pp): this run gives"), "", xc)
  }
  w <- seats$w
  L <- c(L, "", "**SEATS-W, estimand A: the national weekly response (EXPLORATORY)**", "")
  if (!isTRUE(seats$weekly_ok) || is.null(w)) {
    L <- c(L, paste0("- NOT BUILT: ", seats$weekly_reason, ". The code is in place and runs by itself when ", SGS$SEATS_W_FILE,
                     " lands: 09's `aligned` unit-weeks (each paired by 09 with the latest forecast available strictly before the ",
                     "week starts; never re-paired by forecast date; rows with unverified availability only in a labelled ",
                     "sensitivity) are collapsed to the chamber x cycle x week series; the week's Democratic share, and separately ",
                     "its change, on the prior week's change in expected Democratic seats (pp per seat). Primary models have no lagged ",
                     "outcome (levels with cycle effects and a week trend per cycle; changes with cycle effects); a residual moving-block ",
                     "bootstrap within cycle (3- and 5-week blocks, ", SGS_SEATS_BOOT_B, " draws) gives intervals conditional on the ",
                     "observed forecast path; the lagged-outcome model is a sensitivity with a recursive (dynamic) block bootstrap; ",
                     "Newey-West HAC errors (lags 2 / 4 / 8) are secondary and carry no p-value; fits with fewer than ", SGS$SEATS_MIN_WEEKS,
                     " usable weeks are DESCRIPTIVE; pooled and per cycle; pooled-dollar and equal-sector targets; 538 Lite primary ",
                     "(Lite imputes unpolled races: it is not a polls-only model), Classic, Deluxe and the dated Crystal Ball calls as ",
                     "variants; every sector left out in turn (telecom included); the post-primary weeks (2022: from ",
                     SGS$SEATS_POST_PRIMARY_START[["2022"]], ", 7 weeks) are DESCRIPTIVE; the series is plotted first."),
           paste0("- Timing support expected (the Codex audit, after generation-time gating): strict Lite support is 3 full ",
                  "pre-election weeks for 2020 House, 6 for 2020 Senate and 18 for each 2022 chamber; 2020 money is still missing. ",
                  "Whatever 09 delivers, the results will be EXPLORATORY and conditional on those cycles."))
  } else {
    sp <- w$support
    L <- c(L, paste0("- EFFECTIVELY A ONE-ELECTION TEST until 2020 joins: 2022 alone supports a prospective weekly test (18 gated ",
                     "weeks per 538 version per chamber); 2020 adds at most 3 House and 6 Senate weeks once its money lands; 2024 has ",
                     "final calls only (0 pre-election weeks)."),
           paste0("- Series from 09 aligned (primary_window = TRUE; ", w$aligned_primary_rows, " of ", w$aligned_rows, " rows; ",
                  "aligned_sensitivity primary-window rows: ", w$sens_primary_rows, "): ", nrow(w$series), " chamber-source-weeks on ",
                  "gross positive receipts (dem_share_gross, primary; net = dem_share is the sensitivity); rows with available_at not ",
                  "strictly before week_start dropped: ", w$dropped_late, ". Plot: seats_w_series_<run id>.png (the series before any ",
                  "model). Surviving weeks and forecast updates:"),
           "", "| chamber | source | cycle | weeks | weeks with a prior-week change | forecast updates | units | min units with a valid share | post-primary weeks |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|",
           paste0("| ", sp$chamber, " | ", sp$source, " | ", sp$cycle, " | ", sp$weeks, " | ", sp$weeks_with_change, " | ", sp$forecast_updates,
                  " | ", sp$units, " | ", sp$min_valid_units, " | ", ifelse(is.na(sp$post_primary_weeks), "", sp$post_primary_weeks), " |"))
    e <- w$estimates
    iv <- function(lo, hi, p) ifelse(is.na(lo), "not computed", paste0(vapply(seq_along(lo), function(i) sgs_ci_text(lo[i], hi[i]), ""),
                                                                  " (p ", vapply(p, sgs_fmt, ""), ")"))
    isprim <- e$source == tolower(SGS$SEATS_W_PRIMARY) & startsWith(e$availability, "availability verified") & e$window == "all weeks" &
      startsWith(e$money, "gross")
    pr <- e[isprim & !nzchar(e$omitted_sector), , drop = FALSE]
    if (nrow(pr)) {
      L <- c(L, "", paste0("Primary specification (538 Lite, gross positive receipts, availability verified, all primary-window weeks). ",
                           "Intervals are conditional (fixed-X residual block bootstrap within cycle; for the lagged model also the ",
                           "recursive, dynamic bootstrap); bootstrap p-values are never proof; HAC errors are secondary:"), "",
             "| chamber | model | weighting | scope | gate | weeks | updates | estimate (pp per seat) | 3-week interval (p) | 5-week interval (p) | Holm 3 / 5 | recursive 3-week (p) | HAC SE 2 / 4 / 8 | cycles |",
             "|---|---|---|---|---|---:|---:|---:|---|---|---|---|---|---|",
             paste0("| ", pr$chamber, " | ", pr$model, " | ", pr$weighting, " | ", pr$scope, " | ", .md_escape(pr$gate), " | ", pr$n_weeks, " | ",
                    pr$n_updates, " | ", vapply(pr$estimate, sgs_fmt, ""), " | ", iv(pr$fx3_ci_low, pr$fx3_ci_high, pr$fx3_p), " | ",
                    iv(pr$fx5_ci_low, pr$fx5_ci_high, pr$fx5_p), " | ", vapply(pr$holm_fx3_p, sgs_fmt, ""), " / ", vapply(pr$holm_fx5_p, sgs_fmt, ""),
                    " | ", ifelse(pr$model == "lag", iv(pr$rec3_ci_low, pr$rec3_ci_high, pr$rec3_p), ""), " | ",
                    vapply(pr$hac2_se, sgs_fmt, ""), " / ", vapply(pr$hac4_se, sgs_fmt, ""), " / ", vapply(pr$hac8_se, sgs_fmt, ""), " | ",
                    .md_escape(pr$cycles_agree), " |"))
    }
    se <- e[!isprim & !nzchar(e$omitted_sector) & e$scope == "pooled", , drop = FALSE]
    if (nrow(se)) {
      L <- c(L, "", "Sensitivities (pooled over cycles): Classic and Deluxe, net receipts, post-primary weeks (DESCRIPTIVE), unverified availability:", "",
             "| chamber | source | money | availability | window | model | weighting | gate | weeks | estimate | 3-week interval (p) | 5-week interval (p) |",
             "|---|---|---|---|---|---|---|---|---:|---:|---|---|",
             paste0("| ", se$chamber, " | ", se$source, " | ", se$money, " | ", se$availability, " | ", se$window, " | ", se$model, " | ", se$weighting, " | ",
                    .md_escape(se$gate), " | ", se$n_weeks, " | ", vapply(se$estimate, sgs_fmt, ""), " | ", iv(se$fx3_ci_low, se$fx3_ci_high, se$fx3_p),
                    " | ", iv(se$fx5_ci_low, se$fx5_ci_high, se$fx5_p), " |"))
    }
    lo <- e[nzchar(e$omitted_sector), , drop = FALSE]
    if (nrow(lo)) {
      L <- c(L, "", "Leave one sector out (Lite, gross, availability verified, all weeks, pooled; every sector in turn, telecom included):", "",
             "| chamber | omitted | model | weighting | weeks | estimate | 3-week interval (p) | 5-week interval (p) |", "|---|---|---|---|---:|---:|---|---|",
             paste0("| ", lo$chamber, " | ", lo$omitted_sector, " | ", lo$model, " | ", lo$weighting, " | ", lo$n_weeks, " | ", vapply(lo$estimate, sgs_fmt, ""),
                    " | ", iv(lo$fx3_ci_low, lo$fx3_ci_high, lo$fx3_p), " | ", iv(lo$fx5_ci_low, lo$fx5_ci_high, lo$fx5_p), " |"))
    }
    ch <- seats$channels
    if (!is.null(ch) && nrow(ch)) {
      L <- c(L, "", "Channel composition of the chamber money (09 channel_map, gross positive, all cycles in 09):", "",
             "| chamber | channel | gross $ | share of the chamber's gross | rows |", "|---|---|---:|---:|---:|",
             paste0("| ", ch$chamber, " | ", ch$channel, " | ", vapply(ch$gross_usd, .fmt_usd, ""), " | ", vapply(ch$share, .fmt_pct, ""), " | ", ch$n_rows, " |"))
    }
    dn <- seats$donors
    if (!is.null(dn) && nrow(dn$table)) {
      d <- dn$table
      L <- c(L, "", paste0("Continuing donors (09 donor_committee_cycle; DESCRIPTIVE, cycle level): donors giving to the chamber's candidate ",
                           "committees in both the 2021-2022 and 2023-2024 cycles, against all donors of each cycle. Linkage: ",
                           dn$linkage, "."), "",
             "| chamber | cycle | donors | continuing donors | entering | exiting | D share, all donors | D share, continuing donors | gross $, all | gross $, continuing |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
             paste0("| ", d$chamber, " | ", d$cycle, " | ", d$donors, " | ", d$continuing, " | ", d$entering, " | ", d$exiting, " | ",
                    vapply(d$dshare_all, .fmt_pct, ""), " | ", vapply(d$dshare_continuing, .fmt_pct, ""), " | ", vapply(d$gross_all, .fmt_usd, ""),
                    " | ", vapply(d$gross_continuing, .fmt_usd, ""), " |"))
    }
    if (length(w$blocks)) L <- c(L, "", "```", w$blocks, "```")
  }
  L <- c(L, sgs_seats_race_md(seats), sgs_seats_codex_md(seats))
  cells <- sgs_seats_cells(seats, est_rows)
  # cells sharing estimand, chamber, status, reason and family are listed on one line (every cell is in sheet seats_cells)
  gk <- paste(cells$estimand, cells$chamber, cells$status, cells$reason, cells$holm_family, sep = "\r")
  gi <- split(seq_len(nrow(cells)), factor(gk, levels = unique(gk)))
  L <- c(L, "", paste0("**Requested cells: estimated / descriptive only / unavailable (with the reason)** - ", nrow(cells), " cells: ",
                       paste0(names(table(cells$status)), " ", as.integer(table(cells$status)), collapse = ", "),
                       "; cells with the same status and reason share a line; every cell is in sheet seats_cells"), "",
         "| estimand | chamber | cells | status | reason | Holm family |", "|---|---|---|---|---|---|",
         vapply(gi, function(ix) paste0("| ", .md_escape(cells$estimand[ix[1]]), " | ", cells$chamber[ix[1]], " | ",
                                        .md_escape(paste(cells$cell[ix], collapse = "; ")), " | ", cells$status[ix[1]], " | ",
                                        .md_escape(cells$reason[ix[1]]), " | ", .md_escape(cells$holm_family[ix[1]]), " |"), ""))
  L <- c(L, "",
    "**Methodology notes**", "", paste0("- ", sgs_seats_method_notes(coef_rows)))
  L
}

# The methodology notes with this run's SHIFT-Chamber-PV estimate (its expected-control term, bootstrap p).
sgs_seats_method_notes <- function(coef_rows) {
  pv <- Filter(function(c) identical(c$test_id, "SHIFT-Chamber-PV") && isTRUE(c$focal) && is.null(c$left_out), coef_rows)
  txt <- if (length(pv)) paste0(sgs_fmt(pv[[1]]$estimate), ", bootstrap p ", sgs_fmt(pv[[1]]$boot_p %||% NA_real_)) else "not estimated in this run"
  sub("{SHIFT_PV}", txt, SGS_SEATS_METHOD_NOTES, fixed = TRUE)
}
