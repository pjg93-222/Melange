# Registry, frozen model specifications, package pins and the vendored library (spec 3.3, 3.4, 5).

test_that("the shipped registry is valid and carries the six fitted industries and four declined ones", {
  expect_identical(rf_validate_registry(RF_TEST_REG), character(0))
  ids <- names(RF_TEST_REG$industries)
  expect_setequal(ids[vapply(RF_TEST_REG$industries, function(i) i$status != "declined", logical(1))],
                  c("commercial_banks", "credit_unions", "auto_light_duty_manufacturing", "life_insurance", "telecom", "property_casualty"))
  declined <- Filter(function(i) i$status == "declined", RF_TEST_REG$industries)
  expect_setequal(names(declined), c("community_banks", "credit_arms", "crypto", "fintech"))
  for (i in declined) {
    expect_false(any(unlist(i$models)))
    expect_true(nzchar(i$reason))
  }
})

test_that("capabilities follow the inputs that exist, and a missing OpenSecrets capture is a stated reason", {
  expect_setequal(rf_capable(RF_TEST_REG, "pac"), c("commercial_banks", "credit_unions", "auto_light_duty_manufacturing"))
  expect_setequal(rf_capable(RF_TEST_REG, "control"), c("commercial_banks", "credit_unions", "auto_light_duty_manufacturing"))
  expect_setequal(rf_capable(RF_TEST_REG, "lobbying"),
                  c("commercial_banks", "credit_unions", "auto_light_duty_manufacturing", "life_insurance", "telecom", "property_casualty"))
  pc <- RF_TEST_REG$industries$property_casualty
  expect_identical(rf_withheld_reason(pc, "pac"), "OpenSecrets F3400 capture not supplied")
  expect_identical(rf_withheld_reason(pc, "control"), "OpenSecrets F3400 capture not supplied")
  expect_true(is.na(rf_withheld_reason(pc, "lobbying")))
  # the OpenSecrets code -> id map used by the panel builders
  expect_identical(rf_code_map(RF_TEST_REG),
                   c(F03 = "commercial_banks", F05 = "credit_unions", T2100 = "auto_light_duty_manufacturing"))
})

test_that("registry validation catches a duplicate id, a pattern without {cycle}, and a calculator industry with no model", {
  bad <- RF_TEST_REG
  bad$industries$dup <- bad$industries$credit_unions
  bad$industries$dup$id <- "commercial_banks"
  expect_true(any(grepl("duplicate ids", rf_validate_registry(bad))))
  bad <- RF_TEST_REG
  bad$industries$credit_unions$opensecrets$recipients <- "x/F05_candidates_{chamber}.json"
  expect_true(any(grepl("no \\{cycle\\}", rf_validate_registry(bad))))
  bad <- RF_TEST_REG
  bad$industries$telecom$calculator <- TRUE
  bad$industries$telecom$models <- list(pac = FALSE, control = FALSE, lobbying = FALSE)
  expect_true(any(grepl("calculator industry with no model", rf_validate_registry(bad))))
  bad <- RF_TEST_REG
  bad$industries$crypto$models$pac <- TRUE
  expect_true(any(grepl("declined industry with a model", rf_validate_registry(bad))))
})

test_that("the v1 variable selections are frozen in models.json", {
  m <- RF_TEST_MODELS$models
  expect_identical(m$pac$formula, "log_pac ~ sector + factor(cycle_end) + G_current")
  expect_identical(m$control_House$v1_mask, 11L)
  expect_identical(m$control_Senate$v1_mask, 3L)
  expect_identical(m$seats_House$v1_mask, 15L)
  expect_identical(m$lobby$formula, "dy ~ dg + factor(year)")
  expect_false(isTRUE(m$seats_House$calculator))
  expect_true(isTRUE(m$pac$calculator) && isTRUE(m$lobby$calculator))
})

test_that("packages load at the pinned versions from the vendored library, and the Rlib matches its manifest", {
  expect_true(all(RF_TEST_PKGS$ok))
  expect_identical(RF_TEST_PKGS$version[RF_TEST_PKGS$package == "clubSandwich"], "0.7.0")
  expect_identical(RF_TEST_PKGS$version[RF_TEST_PKGS$package == "sandwich"], "3.1-3")
  expect_true(all(normalizePath(RF_TEST_PKGS$lib[RF_TEST_PKGS$package %in% c("clubSandwich", "sandwich")], winslash = "/") == rf_rlib_dir()))
  ver <- rf_verify_rlib()
  expect_gt(nrow(ver), 4L)
  expect_true(all(ver$ok))
  # negative control: a wrong pin is refused, never silently accepted
  expect_error(rf_load_packages(required = "jsonlite", pins = list(jsonlite = "0.0.1")), "pins")
})

test_that("rf_rng.R is the byte copy of the SGS numpy-stream port", {
  expect_identical(rf_sha256(file.path(.RF_HOME, "R", "rf_rng.R")), RF$RNG_SHA256)
  # zlib.crc32(b"abc") == 891568578
  expect_identical(sgs_crc32("abc"), 891568578)
})
