# R port only: the SEATS family (Paul's follow-up of 2026-09-26, "What about the partisanship of the spending as it
# correlates to expected seat gain for a party in the upcoming election?"), rule set paul-2026-09-25, on synthetic data:
# the seat-call definition, SEATS-A (DESCRIPTIVE cycle retrospective), estimand A on a synthetic 09 `aligned` sheet
# (primary_window, available_at gating, split weeks, gross / net, the conditional fixed-X and recursive block
# bootstraps, calendar-aware HAC, Holm, leave one sector out), the race level (538 rows, availability, named-candidate
# matching, classes, incumbency at the origin, favored non-incumbents, expert ratings) and the cell gates. The parity
# rule set has none of it.

.seats_old_B <- SGS_SEATS_BOOT_B
SGS_SEATS_BOOT_B <<- 199L    # the tests use fewer draws (restored at the end of the file)
SEATS8 <- c(SGS$STUDY_SECTORS, "community_banks")

# A synthetic 09 `aligned` sheet: 8 sectors x chambers x weeks x sources, the week's share responding to the paired
# expected seats with `slope` (share points per seat), one election-week row (primary_window FALSE) and one row paired
# with a forecast available ON the week's first day (must be dropped).
seats_aligned <- function(weeks = 18, slope = 0.8, seed = 11, sources = c("Lite", "Classic"), start = as.Date("2022-07-04"),
                          noise = 0.02) {
  set.seed(seed)
  rows <- list()
  for (ch in c("House", "Senate")) {
    path <- cumsum(c(0, stats::rnorm(weeks - 1, 0, if (ch == "House") 1.5 else 0.4))) + if (ch == "House") 205 else 49
    for (src in sources) for (k in seq_len(weeks)) for (s in SEATS8) {
      wk <- start + 7 * (k - 1)
      share <- min(0.95, max(0.05, 0.55 + slope / 100 * (path[k] - path[1]) + stats::rnorm(1, 0, noise)))
      tot <- stats::runif(1, 2e4, 2e5)
      rows[[length(rows) + 1L]] <- list(study_sector = s, chamber = ch, week_start = format(wk), d_gross_usd = tot * share,
                                        r_gross_usd = tot * (1 - share), d_usd = tot * share - 100, r_usd = tot * (1 - share),
                                        source = "538 (FiveThirtyEight)", model_version = src,
                                        available_at = paste0(format(wk - 1), "T20:13:30"), expected_dem_seats = path[k],
                                        primary_window = TRUE)
    }
  }
  df <- .rows_df(rows)
  el <- df[df$week_start == format(start), , drop = FALSE][1, , drop = FALSE]
  el$week_start <- "2022-11-07"; el$primary_window <- FALSE
  late <- df[1, , drop = FALSE]; late$available_at <- paste0(late$week_start, "T01:00:00"); late$study_sector <- "crypto"
  late$d_gross_usd <- 1e9                       # a leak: dropped by the available_at gate
  rbind(df, el, late)
}

test_that("registry: 28 SEATS-A tests (DESCRIPTIVE, no inference) under Paul's rule set, none under parity", {
  rp <- sgs_registry(PAUL); rq <- sgs_registry(PARITY)
  sa <- Filter(function(t) identical(t$family, "SEATS-A"), rp)
  expect_equal(length(sa), 28L)
  expect_equal(length(Filter(function(t) grepl("^SEATS", t$family), rq)), 0L)
  expect_true(all(vapply(sa, function(t) identical(t$inference, "none") && identical(t$label, "DESCRIPTIVE"), TRUE)))
  expect_true(all(vapply(sa[grepl("^SEATS-A-538", names(sa))], function(t) "seats_538" %in% t$requires, TRUE)))
  expect_equal(sort(unique(vapply(sa, `[[`, "", "table"))), c("seats_cycle_house", "seats_cycle_senate"))
  expect_equal(length(Filter(function(t) identical(t$family, "SEATS-W"), rp)), 0L)   # estimand A is outside the registry
})

test_that("the streaming sheet reader keeps the wanted columns, equal to readxl's text read (strings, numbers, booleans, entities)", {
  d <- tmp_dir(); p <- file.path(d, "s.xlsx")
  df <- data.frame(district = c("WY-1", "CA-42", "AK-1"), forecastdate = c("11/8/22", "7/1/22", "7/5/22"), winner_D1 = c(0.000825, 0.6, 1e-7),
                   junk = 1:3, name_D1 = c("Lynnette GreyBull", "Robert Garcia", "Mary Peltola & co <x>"), backfilled = c(TRUE, FALSE, NA),
                   stringsAsFactors = FALSE)
  sgs_write_xlsx(p, list(house = df))
  want <- c("district", "forecastdate", "winner_D1", "name_D1", "backfilled")
  s <- .seats_read_sheet_stream(p, "house", want, "test")
  r <- .seats_read_sheet_text(p, "house", "test")
  expect_setequal(names(s), want)
  expect_equal(s$district, r$district); expect_equal(s$forecastdate, r$forecastdate); expect_equal(s$name_D1, r$name_D1)
  expect_equal(as.numeric(s$winner_D1), as.numeric(r$winner_D1))
  expect_equal(.truthy_col(s$backfilled), .truthy_col(r$backfilled))
  expect_equal(s$name_D1[3], "Mary Peltola & co <x>")
})

test_that("seat calls: projected Democratic seats minus the seats before; the stated change when no seat total", {
  wbs <- list(election = list(frames = list(seat_calls = data.frame(
    chamber = c("House", "Senate", "House"), election_year = c(2022, 2020, 2018), pred_dem_net_change = c(-24, 4, 34),
    proj_dem_seats = c(198, 50, NA), status = "observed", stringsAsFactors = FALSE))),
    seats = list(frames = list(data = data.frame(chamber = c("House", "Senate"), election_year = c(2022, 2020),
                                                 democratic_seats_before = c(222, 47), stringsAsFactors = FALSE))))
  sc <- sgs_seat_calls(wbs)
  expect_equal(sc$seat_net_gain, c(-24, 3, 34))
  expect_match(sc$definition[2], "the call's stated net change: 4", fixed = TRUE)
  expect_match(sc$definition[3], "stated net change", fixed = TRUE)
})

test_that("dates: ISO, offsets to UTC, 538 forecast dates and run timestamps, Excel serials", {
  d <- .seats_day(c("2022-06-29", "2022-07-03T23:30:00-04:00", "2022-07-03T20:13:30", "6/29/22", "11/8/2022",
                    "00:12:39  8 Nov 2022", "44803", "", NA))
  expect_equal(format(d[1:7]), c("2022-06-29", "2022-07-04", "2022-07-03", "2022-06-29", "2022-11-08", "2022-11-08", "2022-08-30"))
  expect_equal(format(.seats_day("44562")), "2022-01-01")                           # Excel's serial of 1 January 2022
  expect_true(all(is.na(d[8:9])))
  expect_equal(format(.seats_mondays(as.Date("2022-07-01"), as.Date("2022-07-20"))), c("2022-07-04", "2022-07-11", "2022-07-18"))
})

test_that("names: surname runs, nicknames, given-name tie-breaks, flagged surname-only matches, ambiguity, party and district", {
  cands <- data.frame(cycle = 2022L, chamber = "House",
                      cand_id = c("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9"),
                      name = c("DE LA CRUZ, MONICA", "HINES, ROBERT NICHOLAS", "GARCIA, ROBERT", "GARCIA, CRISTINA", "KELLY, GEORGE J JR",
                               "LEE, SUSIE", "SMITH, JOHN", "SMITH, JOHN A", "HAGEMAN, HARRIET"),
                      party = c("R", "R", "D", "D", "R", "D", "R", "R", "R"), state = c("TX", "NC", "CA", "CA", "PA", "NV", "OH", "OH", "WY"),
                      district2 = c("15", "13", "42", "42", "16", "03", "02", "02", "00"), stringsAsFactors = FALSE)
  slots <- data.frame(cycle = 2022L, chamber = "House",
                      race = c("TX-15", "NC-13", "CA-42", "CA-42", "PA-16", "NV-03", "OH-02", "WY-00", "WY-00", "TX-15"),
                      state = c("TX", "NC", "CA", "CA", "PA", "NV", "OH", "WY", "WY", "TX"),
                      party = c("R", "R", "D", "D", "R", "D", "R", "R", "D", "D"),
                      name = c("Monica De La Cruz", "Bo Hines", "Robert Garcia", "Cristina Garcia", "Mike Kelly", "Susie McLee",
                               "John Smith", "Harriet Hageman", "Harriet Hageman", "Monica De La Cruz"), stringsAsFactors = FALSE)
  m <- sgs_seats_name_map(slots, cands)
  get <- function(nm, party, race) m[m$name == nm & m$party == party & m$race == race, , drop = FALSE]
  expect_equal(get("Monica De La Cruz", "R", "TX-15")$cand_id, "H1")
  expect_equal(get("Monica De La Cruz", "R", "TX-15")$rule, "surname + given name")
  expect_equal(get("Bo Hines", "R", "NC-13")$cand_id, "H2")
  expect_equal(get("Bo Hines", "R", "NC-13")$rule, "surname + nickname")
  expect_equal(get("Robert Garcia", "D", "CA-42")$cand_id, "H3")
  expect_equal(get("Cristina Garcia", "D", "CA-42")$cand_id, "H4")
  expect_match(get("Cristina Garcia", "D", "CA-42")$rule, "(2 surname hits)", fixed = TRUE)
  expect_equal(get("Mike Kelly", "R", "PA-16")$cand_id, "H5")
  expect_match(get("Mike Kelly", "R", "PA-16")$rule, "flagged", fixed = TRUE)
  expect_equal(get("Susie McLee", "D", "NV-03")$match_status, "unmatched")          # LEE never matches MCLEE
  expect_equal(get("John Smith", "R", "OH-02")$match_status, "ambiguous")          # two JOHN SMITHs: no probability
  expect_equal(get("Harriet Hageman", "R", "WY-00")$cand_id, "H9")                   # at-large 00
  expect_equal(get("Harriet Hageman", "D", "WY-00")$match_status, "unmatched")     # party must agree
  expect_equal(get("Monica De La Cruz", "D", "TX-15")$match_status, "unmatched")
})

# A tiny 538 House sheet (text columns, as the fast reader returns them): WY at-large and CA-42 (same-party early rows).
seats_538_df <- function() {
  row <- function(dist, fd, ts, d1, pd1, r1, pr1, d2 = "", pd2 = "0", avail = NA_character_) {
    list(cycle = "2022", branch = "House", district = dist, forecastdate = fd, expression = "_lite", name_D1 = d1, name_D2 = d2,
         name_D3 = "", name_D4 = "", name_I1 = "", name_R1 = r1, name_R2 = "", name_R3 = "", name_R4 = "", name_O1 = "",
         winner_D1 = pd1, winner_D2 = pd2, winner_D3 = "0", winner_D4 = "0", winner_R1 = pr1, winner_R2 = "0", winner_R3 = "0",
         winner_R4 = "0", winner_I1 = "0", winner_O1 = "0",
         winner_Dparty = as.character(as.numeric(pd1) + as.numeric(pd2)), winner_Rparty = pr1, timestamp = ts, available_at = avail)
  }
  .rows_df(list(
    row("WY-1", "6/1/22", "10:00:00  1 Jun 2022", "Lynnette GreyBull", "0.2", "Harriet Hageman", "0.8"),       # launch-gated to 30 Jun
    row("WY-1", "7/1/22", "10:00:00  1 Jul 2022", "Lynnette GreyBull", "0.1", "Harriet Hageman", "0.9"),
    row("WY-1", "7/2/22", "01:00:00  6 Jul 2022", "Lynnette GreyBull", "0.3", "Harriet Hageman", "0.7"),       # backfilled: run 6 Jul
    row("WY-1", "7/5/22", "01:00:00  5 Jul 2022", "Lynnette GreyBull", "0.05", "Harriet Hageman", "0.95"),
    row("CA-42", "7/1/22", "10:00:00  1 Jul 2022", "Robert Garcia", "0.6", "", "0", d2 = "Cristina Garcia", pd2 = "0.4"),
    row("CA-42", "7/5/22", "10:00:00  5 Jul 2022", "Robert Garcia", "0.99", "John Briscoe", "0.01")))
}
seats_cands <- function() data.frame(cycle = 2022L, chamber = "House", cand_id = c("H9", "H3", "H4", "H0"),
                                     name = c("HAGEMAN, HARRIET", "GARCIA, ROBERT", "GARCIA, CRISTINA", "GREYBULL, LYNNETTE"),
                                     party = c("R", "D", "D", "D"), state = c("WY", "CA", "CA", "WY"), district2 = c("00", "42", "42", "00"),
                                     fec_ico = c("O", "O", "O", "C"), usd = c(10, 20, 30, 5), active = TRUE, stringsAsFactors = FALSE)
seats_terms <- function() data.frame(
  cand_id = c("H3", "H3", "S1", "H7", "H6", "H6"), chamber = c("House", "House", "House", "House", "Senate", "Senate"),
  start = c("2013-01-03", "2021-01-03", "2019-01-03", "2021-05-11", "2011-01-03", "2021-01-20"),
  end = c("2015-01-03", "2023-01-03", "2023-01-03", "2023-01-03", "2017-01-03", "2023-01-03"),
  term_index_same_chamber = c("1", "2", "2", "1", "1", "2"), how = c("", "", "", "special-election", "", "appointment"),
  stringsAsFactors = FALSE)

test_that("538 rows: availability is the latest of forecast date, run date, available_at and the public launch", {
  r <- sgs_seats_538_rows(seats_538_df(), "House")
  expect_equal(unique(r$rows$race[r$rows$district_538 == "WY-1"]), "WY-00")      # at-large
  expect_equal(format(r$rows$available), c("2022-06-30", "2022-07-01", "2022-07-06", "2022-07-05", "2022-07-01", "2022-07-05"))
  expect_equal(r$rows$backfilled, c(FALSE, FALSE, TRUE, FALSE, FALSE, FALSE))
  expect_equal(r$rows$same_party, c(FALSE, FALSE, FALSE, FALSE, TRUE, FALSE))
  expect_equal(r$rows$favorite_p, c(0.8, 0.9, 0.7, 0.95, 0.6, 0.99))
})

test_that("538 class: the favourite's own probability is never folded (a three-way favourite at 0.39 is a toss-up)", {
  expect_equal(.seats_538_class(c(0.39, 0.59, 0.6, 0.74, 0.75, 0.949, 0.95, NA), fold = FALSE),
               c("toss-up", "toss-up", "lean", "lean", "likely", "likely", "safe", NA))
  expect_equal(.seats_538_class(c(0.39, 0.33, 0.05), fold = TRUE), c("lean", "lean", "safe"))   # candidate-relative sensitivity
  expect_equal(.seats_538_class(0.7), .seats_538_class(0.7, fold = FALSE))                       # two-candidate favourite: same band
})

test_that("exposure: the latest row available strictly before the window; the NAMED candidate's own probability only", {
  r <- sgs_seats_538_rows(seats_538_df(), "House")
  cands <- seats_cands()
  map <- sgs_seats_name_map(r$slots, cands)
  ex <- sgs_seats_exposure(r, map, cands, seats_terms(), as.Date(c("2022-07-04", "2022-07-11")), "House")$exposure
  g <- function(cid, w) ex[ex$cand_id == cid & ex$week_start == as.Date(w) & ex$source == "lite", , drop = FALSE]
  expect_equal(g("H9", "2022-07-04")$own_p, 0.9)          # the 1 Jul row: the backfilled 2 Jul row (run 6 Jul) is not yet available
  expect_equal(g("H9", "2022-07-11")$own_p, 0.95)         # the latest forecast date among available rows (5 Jul), not the later-available backfilled 2 Jul row
  expect_true(g("H4", "2022-07-04")$named)                # Cristina named in the early same-party row
  expect_equal(g("H4", "2022-07-04")$own_p, 0.4)
  expect_false(g("H4", "2022-07-11")$named)               # the primary loser is not named later: no probability, never the favourite's
  expect_true(is.na(g("H4", "2022-07-11")$own_p))
  expect_match(g("H4", "2022-07-11")$reason, "not named", fixed = TRUE)
  expect_equal(g("H3", "2022-07-04")$class538, "lean")    # race class from the favourite's 0.6
  expect_equal(g("H4", "2022-07-04")$class538, "lean")
  expect_equal(g("H4", "2022-07-04")$class538_own, "lean")
  expect_equal(g("H3", "2022-07-04")$side538, "favored"); expect_equal(g("H4", "2022-07-04")$side538, "underdog")
  expect_equal(g("H3", "2022-07-11")$class538, "safe")
  # incumbency from dated service: H3 serves (term 2) -> established, never a favored non-incumbent even at p 0.99
  expect_equal(g("H3", "2022-07-11")$status, "established_incumbent")
  expect_false(g("H3", "2022-07-11")$favored_nonincumbent)
  expect_true(g("H3", "2022-07-11")$nonconsecutive)
  # H9 (no service; FEC says open seat) with p 0.9 -> favored non-incumbent at both thresholds
  expect_true(g("H9", "2022-07-04")$favored_nonincumbent); expect_true(g("H9", "2022-07-04")$favored_nonincumbent_p60)
  expect_equal(g("H9", "2022-07-04")$fec_role_provisional, "open seat")
  expect_false(g("H0", "2022-07-04")$favored_nonincumbent)   # the underdog
})

test_that("incumbency at the origin: same chamber only; first-term, established; appointment, partial and nonconsecutive flags", {
  st <- sgs_seats_status_at(data.frame(cand_id = c("S1", "H7", "H3", "H3"), week_start = as.Date(c("2022-07-04", "2022-07-04", "2022-07-04", "2014-07-07")),
                                       stringsAsFactors = FALSE), seats_terms(), "House")
  expect_equal(st$status, c("established_incumbent", "first_term_incumbent", "established_incumbent", "first_term_incumbent"))
  expect_true(st$partial_first_term[2]); expect_false(st$partial_first_term[4])
  sen <- sgs_seats_status_at(data.frame(cand_id = c("S1", "H6"), week_start = as.Date("2022-07-04"), stringsAsFactors = FALSE), seats_terms(), "Senate")
  expect_equal(sen$status, c("non-incumbent", "established_incumbent"))   # a House member running for the Senate is no incumbent senator
  expect_true(sen$appointment[2]); expect_true(sen$nonconsecutive[2])
})

test_that("expert ratings: primary whitelist, availability strictly before, Tilt separate, unrated never safe, one CA-S3", {
  rh <- data.frame(cycle = "2022", race_id = c("WY-00", "WY-00", "WY-00", "OK-S2-special", "CA-S3", "CA-S3-special"),
                   source = c("inside", "inside", "cook", "inside", "inside", "inside"), bucket = c("likely", "lean", "safe", "safe", "safe", "safe"),
                   favored_party = c("R", "R", "R", "R", "D", "D"), chamber = c("House", "House", "House", "Senate", "Senate", "Senate"),
                   tilt_flag = c("0", "1", "0", "0", "0", "0"), availability_date_conservative = c("2022-07-01", "2022-07-11", "2022-07-01", "2022-07-01", "2022-07-01", "2022-07-01"),
                   timing_eligible_primary = c("1", "1", "0", "1", "1", "1"), timing_eligible_extended = c("1", "1", "1", "1", "1", "1"),
                   stringsAsFactors = FALSE)
  ef <- sgs_seats_expert_frame(rh)
  expect_equal(sort(ef$race[ef$chamber == "Senate"]), c("CA-S3", "OK-S2"))          # the CA special is not duplicated
  x <- sgs_seats_expert_at(ef, c("WY-00", "XX-01"), as.Date(c("2022-07-04", "2022-07-11", "2022-07-18")), 2022, "House", "primary")
  g <- function(rc, w, src = "inside") x[x$race == rc & x$week_start == as.Date(w) & x$source == src, , drop = FALSE]
  expect_equal(g("WY-00", "2022-07-04")$category, "likely")
  expect_equal(g("WY-00", "2022-07-11")$category, "likely")                        # the 11 Jul Tilt is not available before 11 Jul
  expect_equal(g("WY-00", "2022-07-18")$category, "tilt")
  expect_equal(g("WY-00", "2022-07-18")$bucket4_tilt_lean, "lean"); expect_equal(g("WY-00", "2022-07-18")$bucket4_tilt_tossup, "toss-up")
  expect_equal(g("WY-00", "2022-07-18", "cook")$category, "unrated")                # extended only: out of the primary whitelist
  expect_equal(g("XX-01", "2022-07-18")$category, "unrated")                        # unrated is unknown, never safe
})

test_that("HAC: calendar-aware Bartlett errors equal a manual Newey-West; blocks stay within cycles", {
  set.seed(3)
  week <- c(1:5, 7:10, 1:6); cycle <- c(rep(2022, 9), rep(2020, 6))
  X <- cbind(1, stats::rnorm(15), week); u <- stats::rnorm(15)
  A <- solve(crossprod(X)); S <- X * u; meat <- crossprod(S); L <- 2
  for (l in 1:L) for (i in seq_len(15)) for (j in seq_len(15)) {
    if (cycle[i] == cycle[j] && week[i] - week[j] == l) meat <- meat + (1 - l / (L + 1)) * (S[i, ] %o% S[j, ] + S[j, ] %o% S[i, ])
  }
  V <- A %*% meat %*% A * 15 / (15 - 3)
  expect_equal(.seats_hac_se(X, u, cycle, week, L, 2), sqrt(V[2, 2]), tolerance = 1e-12)
  set.seed(9); i1 <- .seats_block_index(cycle, 3, 50)
  set.seed(9); i2 <- .seats_block_index(cycle, 3, 50)
  expect_identical(i1, i2)
  expect_true(all(cycle[i1] == rep(cycle, 50)))                                    # every draw from the row's own cycle
  expect_false(.seats_contiguous(cycle, week)); expect_true(.seats_contiguous(cycle[10:15], week[10:15]))
})

test_that("the recursive bootstrap rebuilds the observed outcome exactly from its own residuals (two cycles)", {
  set.seed(5)
  cycle <- c(rep(2020, 7), rep(2022, 9)); n <- length(cycle)
  x <- stats::rnorm(n); y <- numeric(n); y0 <- c(50, 52); rho <- 0.6
  for (i in seq_len(n)) {
    prev <- if (i == 1 || cycle[i] != cycle[i - 1]) y0[match(cycle[i], c(2020, 2022))] else y[i - 1]
    y[i] <- 10 + 0.7 * x[i] + rho * prev + stats::rnorm(1, 0, 0.5)
  }
  lag <- c(y0[1], y[1:6], y0[2], y[8:15])
  X <- cbind(`(Intercept)` = 1, d_seats = x, lag_y = lag, c2022 = as.numeric(cycle == 2022))
  b <- .seats_ols(X, y)
  r <- .seats_boot_recursive(X, y, cycle, 2, 3, cbind(seq_len(n), seq_len(n)))   # identity draws: residuals in place
  expect_equal(r$ci, c(b[2], b[2]), tolerance = 1e-9)
  expect_equal(unname(b), unname(stats::coef(stats::lm(y ~ x + lag + as.numeric(cycle == 2022)))), tolerance = 1e-10)
})

test_that("the vectorized recursive bootstrap equals a naive per-draw loop (regenerate week by week, refit with lm.fit)", {
  set.seed(2)
  cycle <- c(rep(2020, 7), rep(2022, 11)); n <- length(cycle)
  x <- stats::rnorm(n); y <- numeric(n); y0 <- c(50, 52)
  for (i in seq_len(n)) {
    prev <- if (i == 1 || cycle[i] != cycle[i - 1]) y0[match(cycle[i], c(2020, 2022))] else y[i - 1]
    y[i] <- 10 + 0.7 * x[i] - 0.4 * prev + stats::rnorm(1)
  }
  lag <- c(y0[1], y[1:6], y0[2], y[8:17])
  X <- cbind(`(Intercept)` = 1, d_seats = x, lag_y = lag, c22 = as.numeric(cycle == 2022), t = seq_len(n))
  set.seed(7); idx <- .seats_block_index(cycle, 3, 60)
  fast <- .seats_boot_recursive(X, y, cycle, 2, 3, idx)
  first <- !duplicated(cycle)
  fitb <- function(Xm, yv) stats::lm.fit(Xm, yv)$coefficients
  b <- fitb(X, y); e <- as.vector(y - X %*% b); e <- e - stats::ave(e, cycle)
  Z <- X[, -2]; b0 <- fitb(Z, y); e0 <- as.vector(y - Z %*% b0); e0 <- e0 - stats::ave(e0, cycle)
  gen <- function(cf, Xg, lp, ee) { ys <- numeric(n); xb <- Xg[, -lp, drop = FALSE] %*% cf[-lp]
    for (i in seq_len(n)) ys[i] <- xb[i] + cf[lp] * (if (first[i]) lag[i] else ys[i - 1]) + ee[i]; ys }
  refit <- function(ys) { Xs <- X; Xs[, 3] <- ifelse(first, lag, c(NA, ys[-n])); fitb(Xs, ys)[2] }
  bs <- vapply(1:60, function(j) refit(gen(b, X, 3, e[idx[, j]])), 0)
  bn <- vapply(1:60, function(j) refit(gen(b0, Z, 2, e0[idx[, j]])), 0)
  expect_equal(unname(fast$ci), unname(.seats_basic_ci(b[2], bs)), tolerance = 1e-9)
  expect_equal(fast$p, .seats_null_p(b[2], bn))
})

test_that("workbook 11: available_at_launch_floor is the primary availability, plain available_at the sensitivity; flags as built", {
  df <- seats_538_df()
  df$available_at <- c("2022-06-29", "2022-07-01", "2022-07-06", "2022-07-05", "2022-07-01", "2022-07-05")
  df$available_at_launch_floor <- c("2022-06-30", "2022-07-01", "2022-07-06", "2022-07-05", "2022-07-01", "2022-07-05")
  df$same_party_flag <- c("0", "0", "0", "0", "0", "0"); df$multiparty_flag <- c("0", "0", "0", "1", "0", "0")
  r <- sgs_seats_538_rows(df, "House")
  expect_equal(format(r$rows$available[1]), "2022-06-30"); expect_equal(format(r$rows$available_sens[1]), "2022-06-29")
  expect_equal(r$rows$same_party, rep(FALSE, 6))                       # the workbook's flag, not the slot count
  expect_equal(r$rows$multiparty, c(FALSE, FALSE, FALSE, TRUE, FALSE, FALSE))
  cands <- seats_cands()
  ex <- sgs_seats_exposure(r, sgs_seats_name_map(r$slots, cands), cands, seats_terms(), as.Date(c("2022-07-04", "2022-07-11")), "House")
  expect_equal(ex$sens_diff, 0L)                                        # both rules select the same rows for these windows
})

test_that("estimand A series: primary_window, available_at strictly before the week, split weeks summed, gross and net", {
  al <- seats_aligned(weeks = 4)
  sp <- al[al$week_start == "2022-07-11" & al$study_sector == "telecom" & al$chamber == "House" & al$model_version == "Lite", , drop = FALSE]
  sp$d_gross_usd <- 1000; sp$r_gross_usd <- 0; sp$d_usd <- 1000; sp$r_usd <- 0
  al2 <- rbind(al, sp)                                         # a second row of the same sector-week (a week split at 1 January)
  s <- sgs_seats_w_series(al2, basis = "gross")$series
  x <- s[s$chamber == "House" & s$source == "538 lite", , drop = FALSE]
  expect_equal(nrow(x), 4L)                                    # the election-week row is outside the primary window
  expect_equal(sgs_seats_w_series(al2)$dropped_late, 1L)       # available on the week's first day: dropped
  rows <- al2[al2$chamber == "House" & al2$model_version == "Lite" & al2$week_start == "2022-07-11" & .truthy_col(al2$primary_window) &
                substr(al2$available_at, 1, 10) < al2$week_start, , drop = FALSE]
  expect_equal(x$d_usd[x$week_start == as.Date("2022-07-11")], sum(as.numeric(rows$d_gross_usd)))
  expect_equal(x$d_seats[2], x$seats[2] - x$seats[1])
  sn <- sgs_seats_w_series(al2, basis = "net")$series
  expect_false(isTRUE(all.equal(sn$d_usd, s$d_usd)))
})

test_that("estimand A: no-lag primaries with conditional bootstrap, the lagged model's recursive bootstrap, HAC secondary, Holm, LOSO", {
  w <- list(wb = list(frames = list(aligned = seats_aligned(weeks = 18, slope = 0.8))))
  r <- sgs_seats_w_run(w)
  e <- r$estimates
  pri <- e[e$source == "538 lite" & e$scope == "pooled" & startsWith(e$money, "gross") & e$window == "all weeks" & !nzchar(e$omitted_sector) &
             startsWith(e$availability, "availability verified"), , drop = FALSE]
  expect_setequal(unique(pri$model), c("level", "change", "lag"))
  lev <- pri[pri$chamber == "House" & pri$model == "level" & pri$weighting == "pooled-dollar", ]
  expect_equal(lev$gate, "estimated"); expect_equal(lev$n_weeks, 17L)
  # the primary blocks print the real summary(lm()) with the formula in the Call, then the labelled study inference
  expect_true(any(grepl("stats::lm(formula = y ~ d_seats + week_of_cycle, data = d)", r$blocks, fixed = TRUE)))
  expect_true(any(grepl("are NOT the study's inference", r$blocks, fixed = TRUE)))
  expect_true(any(startsWith(r$blocks, "Variables: y = ")))
  expect_true(lev$fx3_ci_low <= lev$estimate && lev$estimate <= lev$fx3_ci_high)
  chg <- pri[pri$chamber == "House" & pri$model == "change" & pri$weighting == "pooled-dollar", ]
  expect_true(chg$estimate > 0.4 && chg$estimate < 1.2)                  # the planted 0.8 pp per seat, seen in changes
  expect_true(chg$fx3_p < 0.05 && chg$fx5_p < 0.05)
  lag <- pri[pri$chamber == "House" & pri$model == "lag" & pri$weighting == "pooled-dollar", ]
  expect_false(is.na(lag$rec3_p)); expect_false(is.na(lag$fx3_p))        # recursive (dynamic) and fixed-X (conditional)
  expect_true(all(is.na(pri$rec3_p[pri$model != "lag"])))
  # the estimate equals lm() on the same rows
  s <- r$series[r$series$chamber == "House" & r$series$source == "538 lite", , drop = FALSE]
  d <- data.frame(y = s$share_pooled, d_seats = s$d_seats, week_of_cycle = s$week_of_cycle)
  expect_equal(lev$estimate, unname(stats::coef(stats::lm(y ~ d_seats + week_of_cycle, data = d))["d_seats"]), tolerance = 1e-10)
  # Holm: 4 primary tests per chamber
  expect_equal(sum(e$holm_family == "A overall response, House"), 4L)
  fam <- e[e$holm_family == "A overall response, House", ]
  expect_equal(fam$holm_fx3_p, stats::p.adjust(fam$fx3_p, "holm"))
  # leave one sector out: every sector, telecom included
  lo <- e[nzchar(e$omitted_sector) & e$chamber == "House", ]
  expect_setequal(unique(lo$omitted_sector), SEATS8)
  # the post-primary window (7 weeks from 19 September 2022 in the data used here: none) and a short series are DESCRIPTIVE
  short <- .seats_fit_series(transform(s[1:8, ], y_level = share_pooled, y_change = d_share_pooled, y_lag = lag_share_pooled), "d_seats", "short")
  expect_match(short[["level pooled"]]$gate, "descriptive only", fixed = TRUE)
  expect_equal(length(short[["level pooled"]]$fx), 0L)
  # a constant outcome (one candidate taking one party's money every week) leaves nothing to resample: descriptive, no p
  flat <- .seats_fit_series(transform(s, y_level = 100, y_change = 0, y_lag = 100), "d_seats", "flat", models = c("level", "change"))
  expect_match(flat[["level pooled"]]$gate, "the outcome never varies", fixed = TRUE)
  expect_equal(length(flat[["level pooled"]]$fx), 0L); expect_true(isTRUE(flat[["change pooled"]]$degenerate))
  expect_false(isTRUE(.seats_fit_series(transform(s, y_level = share_pooled, y_change = d_share_pooled, y_lag = lag_share_pooled), "d_seats",
                                        "varied", models = "level")[["level pooled"]]$degenerate))
})

test_that("estimand B: groups fixed at the pre-spending origin (primary) and rolling (sensitivity), contrasts, Holm on fixed rows, transitions; C runs", {
  set.seed(4)
  weeks <- as.Date("2022-07-04") + 7 * (0:17)
  cands <- data.frame(cand_id = sprintf("C%02d", 1:24), party = rep(c("D", "R"), 12), stringsAsFactors = FALSE)
  status <- rep(c("first_term_incumbent", "established_incumbent", "non-incumbent"), each = 8)
  ex <- do.call(rbind, lapply(seq_along(weeks), function(i) {
    p <- stats::runif(24, 0.05, 0.95)
    if (i > 9) p[17] <- 0.2                                    # C17 stops being favored after week 9 (a rolling transition)
    data.frame(cand_id = cands$cand_id, party = cands$party, week_start = weeks[i], source = "lite", status = status, named = TRUE,
               own_p = p, class538 = .seats_538_class(pmax(p, 1 - p)), fec_ico = ifelse(status == "non-incumbent", "C", "I"),
               favored_nonincumbent = status == "non-incumbent" & p > 0.5, favored_nonincumbent_p60 = status == "non-incumbent" & p > 0.6,
               in_election = TRUE, row = NA_integer_, stringsAsFactors = FALSE)
  }))
  ex$own_p[ex$cand_id == "C17" & ex$week_start == weeks[1]] <- 0.9; ex$favored_nonincumbent[ex$cand_id == "C17" & ex$week_start == weeks[1]] <- TRUE
  nat <- data.frame(chamber = "House", cycle = 2022, week_start = weeks, week_of_cycle = 83:100, d_seats = c(NA, stats::rnorm(17, 0, 2)))
  money <- do.call(rbind, lapply(seq_along(weeks), function(i) {
    data.frame(cand_id = rep(cands$cand_id, each = 4), party = rep(cands$party, each = 4), week_start = weeks[i],
               study_sector = rep(SEATS8[1:4], 24), gross = stats::rexp(96, 1 / 500) * (1 + 0.05 * ifelse(is.na(nat$d_seats[i]), 0, nat$d_seats[i])),
               refund = -stats::rbinom(96, 1, 0.05) * 100, net = NA_real_, stringsAsFactors = FALSE)
  }))
  money$net <- money$gross + money$refund
  b <- sgs_seats_b_run(ex, money, nat, "House")
  expect_true(b$ok)
  e <- b$estimates
  expect_setequal(unique(e$classification), c("fixed", "rolling"))
  expect_true(all(c("first_term_minus_established", "favored_nonincumbent_minus_established", "toss-up_minus_safe") %in% e$group))
  expect_true(all(e$classification[nzchar(e$holm_family)] == "fixed"))
  fam <- e[e$holm_family == "B incumbency contrasts, House, share_equal", ]
  expect_equal(nrow(fam), 4L)                                                          # 2 contrasts x levels / changes
  expect_equal(fam$holm_fx3_p, stats::p.adjust(fam$fx3_p, "holm"))
  tr <- b$transitions[b$transitions$group == "favored_nonincumbent", ]
  expect_gte(tr$fixed_leaving_in_some_week, 1L)                                        # C17 leaves the rolling group
  # the contrast equals the difference of the two groups' series fitted by lm
  s <- b$series[b$series$classification == "fixed", ]
  d <- data.frame(y = s$share_equal[s$group == "first_term"] - s$share_equal[s$group == "established"], d_seats = s$d_seats[s$group == "first_term"],
                  week_of_cycle = s$week_of_cycle[s$group == "first_term"])
  est <- e$estimate[e$group == "first_term_minus_established" & e$weighting == "share_equal" & e$model == "level" & e$classification == "fixed"]
  expect_equal(est, unname(stats::coef(stats::lm(y ~ d_seats + week_of_cycle, data = d))["d_seats"]), tolerance = 1e-10)
  # printed summary(lm()) blocks: one per fixed-origin D-share row of the primary slopes and the contrasts
  n_rows <- sum(e$classification == "fixed" & e$weighting == "share_equal" & e$kind %in% c("slope", "contrast") & e$scope == "pooled")
  expect_gt(n_rows, 0L)
  expect_equal(sum(startsWith(b$blocks, "==== SEATS-B House ")), n_rows)
  expect_true(any(grepl("stats::lm(formula = y ~ d_seats + week_of_cycle, data = d)", b$blocks, fixed = TRUE)))
  expect_true(any(grepl("are NOT the study's inference", b$blocks, fixed = TRUE)))
  expect_false(any(grepl("rolling|favored_nonincumbent_p60 ", b$blocks[startsWith(b$blocks, "==== SEATS-B")])))
  # C: fixed candidate set, week-block bootstrap; every candidate its own race, one 538 row per race x week (available before it)
  rr <- expand.grid(k = seq_along(weeks), c = seq_len(24))
  r538 <- list(rows = data.frame(row = seq_len(nrow(rr)), source = "lite", race = sprintf("R%02d", rr$c), p_dem_party = stats::runif(nrow(rr)),
                                 forecastdate = weeks[rr$k] - 2, run_date = weeks[rr$k] - 2, available = weeks[rr$k] - 2, stringsAsFactors = FALSE))
  ex$row <- match(paste(sprintf("R%02d", match(ex$cand_id, cands$cand_id)), ex$week_start - 2), paste(r538$rows$race, r538$rows$available))
  cc <- sgs_seats_c_run(ex, money, r538, "House")
  expect_true(cc$ok); expect_equal(cc$candidates, 24L); expect_true(all(c("L3", "L5") %in% names(cc$boot)))
})

test_that("cells: every requested cell gated with its reason when 09, 10 and 11 are absent", {
  seats <- list(weekly_ok = FALSE, weekly_reason = "09 absent (test)", w = NULL,
                race = list(ok = FALSE, have10 = FALSE, have11 = FALSE, reason10 = "10 absent (test)", reason11 = "11 absent (test)",
                            chambers = list(), money = list(ok = FALSE, reason = "no money (test)")))
  est_rows <- lapply(c("SEATS-A-House-cand", "SEATS-A-House-all", "SEATS-A-Senate-cand", "SEATS-A-Senate-all"),
                     function(i) list(test_id = i, status = SGS_ESTIMABLE))
  cells <- sgs_seats_cells(seats, est_rows)
  expect_true(all(cells$status %in% c("estimated", "descriptive only", "unavailable")))
  expect_true(all(nzchar(cells$reason)))
  expect_equal(unique(cells$status[startsWith(cells$estimand, "SEATS-A")]), "descriptive only")
  expect_true(all(grepl("09 absent", cells$reason[startsWith(cells$estimand, "A national")], fixed = TRUE)))
  b <- cells[startsWith(cells$estimand, "B differential"), ]
  expect_true(all(b$status == "unavailable")); expect_true(all(grepl("11 absent", b$reason, fixed = TRUE)))
  expect_true(any(cells$holm_family == "B incumbency contrasts, House"))
  expect_true(any(grepl("favored non-incumbent minus established", cells$cell, fixed = TRUE)))
  expect_equal(cells$status[cells$estimand == "champions breakdown (H5)"], "descriptive only")
})

test_that("end to end: 09 read, estimand A estimated, sheets and receipt; the race level NOT BUILT without 10 / 11; parity has none", {
  base <- tmp_dir()
  data <- synth_build(file.path(base, "data"))
  sgs_write_xlsx(file.path(data, SGS$SEATS_W_FILE), list(aligned = seats_aligned(weeks = 18)))
  Sys.setFileTime(file.path(data, SGS$SEATS_W_FILE), Sys.time() - 3600)
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "results"), B = 99, only = c("SEATS-A-House-cand", "SEATS-A-538-House-all"),
                   rules = PAUL, run_id = "analysis-R-20260103T000000Z")
  expect_true(out$seats$weekly_ok)
  expect_gt(nrow(out$seats$w$estimates), 0L)
  # one "built" element carrying every SEATS input (a duplicated name once hid seats_538 and left SEATS-A-538 NOT BUILT)
  expect_equal(sum(names(out$seats) == "built"), 1L)
  expect_true(all(c("seats_calls", "seats_weekly", "seats_538", "seats_race") %in% names(out$seats$built)))
  expect_true(isTRUE(out$built$seats_538$built))
  r538 <- Filter(function(r) identical(r$test_id, "SEATS-A-538-House-all"), out$est_rows)   # 04-based: the synthetic folder has no 08
  expect_length(r538, 1L)
  expect_true(r538[[1]]$status %in% c(SGS_ESTIMABLE, SGS_NOT_ESTIMABLE))   # gated on its cycles, never NOT BUILT for a missing seats_538
  expect_false(out$seats$race$ok)
  expect_match(out$seats$race$reason, "10_recipient_classification.xlsx not present", fixed = TRUE)
  sh <- readxl::excel_sheets(out$xlsx)
  for (s in c("seats_cycle_house", "seats_cycle_senate", "seats_coverage", "seats_calls", "seats_cells", "seats_w_estimates", "seats_w_support")) {
    expect_true(s %in% sh, info = s)
  }
  rc <- jsonlite::fromJSON(out$receipt)
  expect_true(rc$seats$weekly$built); expect_false(rc$seats$race$built)
  expect_true(any(vapply(out$sources, function(s) identical(s$file, SGS$SEATS_W_FILE), TRUE)))
  md <- paste(readLines(out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, "## SEATS: partisanship of the spending and the expected seat gain", fixed = TRUE)
  expect_match(md, "EFFECTIVELY A ONE-ELECTION TEST", fixed = TRUE)
  expect_false(grepl("polls-only", gsub("not a polls-only model", "", md, fixed = TRUE), fixed = TRUE))   # Lite is never labelled polls-only
  outp <- quiet_run(data_dir = data, results_dir = file.path(base, "results_parity"), B = 99, only = c("C1"), rules = PARITY,
                    run_id = "analysis-R-20260104T000000Z")
  expect_null(outp$seats)
  expect_false(any(grepl("^seats_", readxl::excel_sheets(outp$xlsx))))
  expect_false(any(vapply(outp$sources, function(s) identical(s$file, SGS$SEATS_W_FILE), TRUE)))
})

test_that("SEATS-A's no-inference note names the cycles, never a sector-count bootstrap bound", {
  expect_equal(sgs_no_inference_note(list(family = "SEATS-A", inference = "none"), 8L), SGS_SEATS_A_NO_INFERENCE_NOTE)
  expect_false(grepl("cannot reach", SGS_SEATS_A_NO_INFERENCE_NOTE, fixed = TRUE))
  expect_equal(sgs_no_inference_note(list(family = "LV", inference = "none"), 2L), sgs_descriptive_note(2L))   # the parity note unchanged
})

SGS_SEATS_BOOT_B <<- .seats_old_B
