# Port of code/tests/test_load_and_run.py: loader validation, then full synthetic end-to-end runs (all workbooks
# synthetic, rule set python-parity) with Glass Box emission.

REG_L <- sgs_registry(PARITY)
N_TESTS <- length(REG_L)
H5_IDS <- names(REG_L)[vapply(REG_L, function(t) t$family == "H5", TRUE)]
LOADER_SPEC <- list(data = .sheet_spec(c("year", "value"), c("study_sector", "year"), study_sector = TRUE))

.xlsx1 <- function(path, header, rows) {
  df <- as.data.frame(setNames(lapply(seq_along(header), function(j) {
    vals <- lapply(rows, `[[`, j)
    if (all(vapply(vals, is.numeric, TRUE))) unlist(vals) else vapply(vals, as.character, "")
  }), header), stringsAsFactors = FALSE, check.names = FALSE)
  sgs_write_xlsx(path, list(data = df), allow_formulas = TRUE)
  path
}

test_that("TestLoader.test_rejects_formula_cell", {
  p <- .xlsx1(file.path(tmp_dir(), "f.xlsx"), c("study_sector", "year", "value"), list(list("crypto", 2021, "1.0"), list("crypto", 2022, "=B2*2")))
  err <- tryCatch(sgs_read_workbook(p, LOADER_SPEC), LoadError = function(e) e)
  expect_s3_class(err, "LoadError")
  expect_match(conditionMessage(err), "f.xlsx [data] cell C3", fixed = TRUE)
})

test_that("TestLoader.test_rejects_duplicate_key", {
  p <- .xlsx1(file.path(tmp_dir(), "d.xlsx"), c("study_sector", "year", "value"), list(list("crypto", 2021, 1.0), list("crypto", 2021, 2.0)))
  err <- tryCatch(sgs_read_workbook(p, LOADER_SPEC), LoadError = function(e) e)
  expect_match(conditionMessage(err), "d.xlsx [data] key ['study_sector', 'year']", fixed = TRUE)
})

test_that("TestLoader.test_rejects_missing_column", {
  p <- .xlsx1(file.path(tmp_dir(), "m.xlsx"), c("study_sector", "year"), list(list("crypto", 2021)))
  err <- tryCatch(sgs_read_workbook(p, LOADER_SPEC), LoadError = function(e) e)
  expect_match(conditionMessage(err), "m.xlsx [data] column value", fixed = TRUE)
})

test_that("TestLoader.test_requires_study_sector", {
  d <- tmp_dir()
  p <- .xlsx1(file.path(d, "s.xlsx"), c("sector", "year", "value"), list(list("crypto", 2021, 1.0), list("fintech", 2021, 2.0)))
  err <- tryCatch(sgs_read_workbook(p, LOADER_SPEC), LoadError = function(e) e)
  expect_match(conditionMessage(err), "s.xlsx [data] column study_sector: required column missing", fixed = TRUE)
  expect_match(conditionMessage(err), "`sector` column is present", fixed = TRUE)
  q <- .xlsx1(file.path(d, "t.xlsx"), c("sector", "study_sector", "year", "value"), list(list("life_insurance_annuities", "life_insurance", 2021, 1.0)))
  wb <- sgs_read_workbook(q, LOADER_SPEC)
  expect_equal(wb$frames$data$study_sector, "life_insurance")
  expect_equal(nchar(wb$sha256), 64)
})

e2e <- local({
  base <- tmp_dir()
  data <- synth_build(file.path(base, "data"))  # no 05 in this folder: H5 is NOT BUILT
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "results"), B = 999, run_id = "analysis-test", rules = PARITY)
  list(out = out, rows = setNames(out$est_rows, vapply(out$est_rows, `[[`, "", "test_id")))
})

test_that("TestSyntheticEndToEnd.test_panel_shapes_and_statuses", {
  sy <- e2e$out$tables$sector_year
  expect_equal(nrow(sy), 9 * 21)
  expect_true(all(sy$contributions_status[sy$study_sector == "life_insurance"] == "not_applicable"))
  expect_true(all(is.na(sy$contributions_real_m[sy$year == 2026])))
  expect_equal(nrow(e2e$out$tables$sector_year_tier), 9 * 21 * 4)
  expect_equal(sort(unique(sy$study_sector[!is.na(sy$lobby_amount_undiff_real_m)])), c("commercial_banks", "credit_unions"))
})

test_that("TestSyntheticEndToEnd.test_core_test_estimable_and_recovers_slope", {
  rows <- e2e$rows
  expect_equal(rows[["C1"]]$status, "ESTIMABLE")
  expect_equal(rows[["C1"]]$window_used, "2020-2025")
  expect_equal(c(rows[["L1-income"]]$window_used, rows[["L1-income"]]$window_kind), c("2016-2025", "fallback"))
  expect_match(rows[["L1-income"]]$fallback_search, "complete-case years in 2008-2025: 2008-2025", fixed = TRUE)
  c1 <- Filter(function(c) c$test_id == "C1", e2e$out$coef_rows)
  expect_equal(vapply(c1, `[[`, "", "coefficient"), "growth_previous_year_pct")
  expect_lt(abs(c1[[1]]$estimate - 0.3), 0.05)
  expect_true(startsWith(c1[[1]]$stratification, "STRATIFIED") || startsWith(c1[[1]]$stratification, "UNSTRATIFIED"))
  h1 <- Filter(function(c) c$test_id == "H1-C1", e2e$out$coef_rows)
  expect_equal(vapply(h1, `[[`, "", "coefficient"), c("pres_year", "midterm_year"))
  expect_equal(rows[["DS-House"]]$status, "NOT BUILT")
  expect_equal(rows[["H4seat-C1"]]$status, "NOT ESTIMABLE")
})

test_that("TestSyntheticEndToEnd.test_lobbyview_tests_descriptive_in_fallback", {
  for (k in 1:3) {
    r <- e2e$rows[[paste0("L", k, "-LV")]]
    expect_equal(list(r$status, r$label, r$window_used, r$window_kind), list("ESTIMABLE", "DESCRIPTIVE", "2014-2023", "fallback"))
    expect_equal(r$sectors, "commercial_banks, credit_unions")
  }
  lv <- Filter(function(c) c$test_id == "L1-LV", e2e$out$coef_rows)
  expect_equal(length(lv), 1)
  expect_lt(abs(lv[[1]]$estimate - 0.5), 0.05)
  expect_true(is.nan(lv[[1]]$boot_p))
  expect_equal(lv[[1]]$ci_text, "n/a (inference not available)")
  expect_equal(lv[[1]]$boot_note, "2 sectors: wild cluster bootstrap cannot reach p < 0.056; inference not available")
})

test_that("TestSyntheticEndToEnd.test_h5_not_built_without_05", {
  for (tid in H5_IDS) {
    expect_equal(e2e$rows[[tid]]$status, "NOT BUILT", info = tid)
    expect_match(e2e$rows[[tid]]$reason, "05_industry_champions.xlsx not found", fixed = TRUE)
  }
  expect_equal(length(H5_IDS), 13)
})

test_that("TestSyntheticEndToEnd.test_outputs_written_in_study_format", {
  xl <- e2e$out$xlsx
  expect_true(file.exists(xl) && file.exists(e2e$out$report) && file.exists(e2e$out$estimability))
  expect_equal(readxl::excel_sheets(xl), c("estimability", "coefficients", "strata", "samples", "sector_year",
                                          "sector_year_tier", "industry_year", "champions", "dictionary", "sources"))
  expect_silent(sgs_values_only_guard(xl))
  est <- readxl::read_excel(xl, sheet = "estimability")
  expect_equal(nrow(est), N_TESTS)
  expect_equal(N_TESTS, 139)
  src <- readxl::read_excel(xl, sheet = "sources")
  expect_true("05_industry_champions.xlsx" %in% src$file)
})

test_that("TestSyntheticEndToEnd.test_glassbox_event_shape", {
  d <- tmp_dir()
  eid <- sgs_glassbox_emit("run.start", "running", "start", "test", "analysis-test", events_dir = d)
  files <- list.files(d)
  expect_equal(files, paste0(eid, ".json"))
  raw <- readBin(file.path(d, files[1]), "raw", 100000)
  expect_false(identical(raw[1:3], as.raw(c(0xef, 0xbb, 0xbf))))  # no BOM
  ev <- jsonlite::fromJSON(file.path(d, files[1]), simplifyVector = FALSE)
  expect_equal(names(ev), c("schema_version", "id", "timestamp_utc", "run_id", "correlation_id", "parent_id", "lane", "source",
                            "kind", "status", "stage", "summary", "detail", "cwd", "duration_ms", "bytes", "metadata"))
  expect_equal(c(ev$lane, ev$source), c("claude", "sector-growth-analysis"))
  expect_match(eid, "^evt-[0-9]{8}T[0-9]{13}Z-[0-9]{10}$")
})

test_that("TestSyntheticEndToEndWithChampions.test_h5_estimated_and_reported", {
  base <- tmp_dir()
  data <- synth_build(file.path(base, "data"))
  write_champions(data, champions_frame(slope = 5000.0, noise = 500.0), age_minutes = 30)
  out <- quiet_run(data_dir = data, results_dir = file.path(base, "results"), B = 999, run_id = "analysis-test-h5",
                   only = c("H5", "C1"), rules = PARITY)
  rows <- setNames(out$est_rows, vapply(out$est_rows, `[[`, "", "test_id"))
  expect_equal(rows[["H5-pooled"]]$status, "ESTIMABLE")
  expect_equal(rows[["H5-within"]]$status, "ESTIMABLE")
  expect_equal(rows[["H5-pooled"]]$window_used, "cycles 2022, 2024, 2026")
  expect_equal(rows[["H5-pooled"]]$dv_column, "direct_giving_real_2025_usd")
  expect_match(rows[["H5-pooled"]]$flag, "employee channel only", fixed = TRUE)
  expect_equal(rows[["H5-pooled-no2026"]]$status, "NOT ESTIMABLE")
  expect_equal(rows[["H5-pooled-trade"]]$status, "NOT BUILT")
  expect_match(rows[["H5-general_margin"]]$flag, "outcome-contaminated: money affects margins", fixed = TRUE)
  coefs <- Filter(function(c) startsWith(c$test_id, "H5"), out$coef_rows)
  coefs <- setNames(coefs, vapply(coefs, `[[`, "", "test_id"))
  expect_lt(abs(coefs[["H5-within"]]$estimate - 5000.0), 600.0)
  expect_equal(coefs[["H5-pooled"]]$unit_of_analysis, "board x champion x cycle")
  expect_true(any(vapply(out$strata_rows, function(s) !is.null(s$board), TRUE)))
  md <- paste(readLines(out$report, encoding = "UTF-8"), collapse = "\n")
  expect_match(md, "### H5-pooled (EXTENSION): ESTIMABLE", fixed = TRUE)
  expect_match(md, "stratum board bank", fixed = TRUE)
  src <- Filter(function(s) s$file == "05_industry_champions.xlsx", out$sources)[[1]]
  expect_equal(nchar(src$sha256), 64)
  expect_gt(nrow(out$tables$champions), 0)
})

test_that("TestDemShareStub.test_not_built", {
  d <- sgs_decide(REG_L[["DS-House"]], list())
  expect_equal(d$status, SGS_NOT_BUILT)
  expect_equal(d$reason, "NotBuilt: recipient chamber mapping not yet prepared")
})
