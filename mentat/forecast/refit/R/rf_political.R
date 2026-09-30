# Expected-control and seat-call inputs: the IEM Jan-Jun control score (loo/work/partisan_quality/build_scores.py:4-37), current
# congressional control (workbook 03), the Crystal Ball final seat calls (zip predicted_*.csv), and the 2026 Kalshi /
# Polymarket window. Every rebuild is proven against the Codex files in political_probe.R and janjun_2026.R.

# Daily IEM Republican-control score per cycle and chamber, Jan 1 - Oct 31 of the election year.
# House P_R = (RH_DS + RH_RS) / sum of the four named joint contracts; Senate P_R = (DH_RS + RH_RS) / the same sum
# (numerator needs 2 quotes, denominator 4; a zero denominator is NA). P_other = OTHER / all five contracts.
# -> cycle_end, chamber, date, P_R, P_other
rf_iem_daily <- function(iem_zip, cycles = seq(2012, 2022, 2)) {
  raw <- unique(rf_read_zip_csv(iem_zip, "iem_contract_prices_raw.csv"))
  out <- list()
  for (cy in cycles) {
    yy <- sprintf("%02d", cy %% 100)
    d <- raw[raw$market == paste0("CONGRESS", yy), ]
    if (anyDuplicated(d[c("date", "contract")])) rf_raise("PanelError", paste("duplicate IEM (date, contract) rows in CONGRESS", yy))
    named <- paste0(c("DH_DS", "DH_RS", "RH_DS", "RH_RS"), yy)
    other <- paste0("OTHER", yy)
    if (!setequal(unique(d$contract), c(named, other))) rf_raise("PanelError", paste("unexpected IEM contracts in CONGRESS", yy))
    if (min(d$last_price, na.rm = TRUE) < 0 || max(d$last_price, na.rm = TRUE) > 1) rf_raise("PanelError", paste("IEM price outside [0,1] in CONGRESS", yy))
    p <- reshape(d[, c("date", "contract", "last_price")], idvar = "date", timevar = "contract", direction = "wide")
    names(p) <- sub("last_price.", "", names(p), fixed = TRUE)
    p <- p[order(p$date), ]
    den <- rowSums(p[, named]); den[rowSums(!is.na(p[, named])) < 4L | den == 0] <- NA
    den5 <- rowSums(p[, c(named, other)]); den5[rowSums(!is.na(p[, c(named, other)])) < 5L | den5 == 0] <- NA
    for (ch in c("House", "Senate")) {
      cols <- if (ch == "House") named[3:4] else named[c(2, 4)]
      num <- rowSums(p[, cols]); num[rowSums(!is.na(p[, cols])) < 2L] <- NA
      pr <- num / den
      keep <- p$date >= sprintf("%d-01-01", cy) & p$date <= sprintf("%d-10-31", cy) & !is.na(pr)
      out[[length(out) + 1L]] <- data.frame(cycle_end = cy, chamber = ch, date = p$date[keep], P_R = pr[keep],
                                            P_other = (p[[other]] / den5)[keep], stringsAsFactors = FALSE)
    }
  }
  do.call(rbind, out)
}

RF_IEM_WINDOWS <- list(JanJun = c("01-01", "06-30"), SepOct = c("09-01", "10-31"))

# Mean score over a fixed calendar window of the election year; every calendar day must be present (build_scores.py:27-29).
# -> cycle_end, chamber, window, P_R, P_other, days, first_date, last_date
rf_iem_window <- function(daily, window = "JanJun") {
  w <- RF_IEM_WINDOWS[[window]]
  if (is.null(w)) rf_raise("PanelError", paste("unknown IEM window", window))
  out <- list()
  for (cy in sort(unique(daily$cycle_end))) for (ch in c("House", "Senate")) {
    q <- daily[daily$cycle_end == cy & daily$chamber == ch & daily$date >= sprintf("%d-%s", cy, w[1]) & daily$date <= sprintf("%d-%s", cy, w[2]), ]
    expected <- length(seq(as.Date(sprintf("%d-%s", cy, w[1])), as.Date(sprintf("%d-%s", cy, w[2])), by = "day"))
    if (nrow(q) != expected) rf_raise("PanelError", sprintf("IEM %s %d %s: %d of %d calendar days present (every calendar day is required)", window, cy, ch, nrow(q), expected))
    out[[length(out) + 1L]] <- data.frame(cycle_end = cy, chamber = ch, window = window, P_R = mean(q$P_R), P_other = mean(q$P_other),
                                          days = nrow(q), first_date = min(q$date), last_date = max(q$date), stringsAsFactors = FALSE)
  }
  do.call(rbind, out)
}

# Current congressional control by calendar year (workbook 03 sheet current_control): dem_control and RMajNow = 1 - dem_control.
rf_current_control <- function(seat_xlsx) {
  cc <- rf_read_xlsx(seat_xlsx, "current_control")
  if (!all(c("calendar_year", "chamber", "dem_control") %in% names(cc))) rf_raise("PanelError", "current_control lacks its columns")
  out <- data.frame(year = as.integer(cc$calendar_year), chamber = cc$chamber, dem_control = as.integer(cc$dem_control), stringsAsFactors = FALSE)
  out$RMajNow <- 1L - out$dem_control
  out
}

# Sabato's Crystal Ball final pre-election calls: predicted Republican net seat change per election year and chamber.
rf_seat_calls <- function(iem_zip) {
  one <- function(member, chamber) {
    d <- rf_read_zip_csv(iem_zip, member)
    data.frame(cycle_end = as.integer(d$election_year), chamber = chamber, pred_rep_net_change = as.numeric(d$pred_rep_net_change),
               forecast_source = d$forecast_source, stringsAsFactors = FALSE)
  }
  x <- rbind(one("predicted_house.csv", "House"), one("predicted_senate.csv", "Senate"))
  x[!is.na(x$pred_rep_net_change), ]
}

# Mean Republican-control probability over a window for one daily market file: 1 - p_dem_normalized.
rf_market_mean <- function(path, start, end) {
  d <- utils::read.csv(path, stringsAsFactors = FALSE)
  if (!all(c("date", "p_dem_normalized") %in% names(d))) rf_raise("PanelError", paste("unexpected market file", basename(path)))
  q <- d[d$date >= start & d$date <= end, ]
  list(days = nrow(q), p_rep = mean(1 - q$p_dem_normalized), first = min(q$date), last = max(q$date))
}

# 2026 expected control over [start, end]: per market the mean of 1 - p_dem_normalized, then the equal-weight mean of the
# markets of each chamber. `daily_files` = data.frame(market, chamber, path). Returns
# list(markets = data.frame(chamber, market, days, first_date, last_date, p_rep, sha256), control = data.frame(chamber, p_rep, markets)).
rf_market_window <- function(daily_files, start, end) {
  rows <- lapply(seq_len(nrow(daily_files)), function(i) {
    m <- rf_market_mean(daily_files$path[i], start, end)
    data.frame(chamber = daily_files$chamber[i], market = daily_files$market[i], days = m$days, first_date = m$first, last_date = m$last,
               p_rep = m$p_rep, sha256 = rf_sha256(daily_files$path[i]), stringsAsFactors = FALSE)
  })
  mk <- do.call(rbind, rows)
  ctl <- do.call(rbind, lapply(split(mk, mk$chamber), function(q) data.frame(chamber = q$chamber[1], p_rep = mean(q$p_rep),
                                                                              markets = paste(q$market, collapse = "+"), stringsAsFactors = FALSE)))
  rownames(ctl) <- NULL
  list(markets = mk, control = ctl)
}
