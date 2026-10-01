# Gates G4-G9 and the decision (SPEC 3.13 with the rulings of 2026-09-30). The published bundle is v1 today, so G5 / G6 compare the
# refit with it; a v2 bundle published earlier supplies the same numbers through its recorded evidence. Comparisons against a bundle
# built on another platform (BLAS differs at ~1e-14) are tolerance-based, never byte-equal.

published_v1 <- function() v1_bundle()

test_that("G4 sample adequacy: a thin industry is withheld for that model with a stated reason (WARN), everything else adequate", {
  g4 <- test_v2()$adequacy
  expect_identical(g4$gate$status, "WARN")
  tab <- g4$table
  expect_true(all(tab$ok[tab$industry != "auto_light_duty_manufacturing" | tab$model != "lobbying"]))
  a <- tab[tab$industry == "auto_light_duty_manufacturing" & tab$model == "lobbying", ]
  expect_equal(a$n, 1L); expect_false(a$ok)
  w <- g4$withheld$auto_light_duty_manufacturing
  expect_identical(w[[1]]$model, "lobbying")
  expect_match(w[[1]]$reason, "sample adequacy: 1 annual pairs \\(need 5\\)")
  # 6 cycles (control) and 7 (PAC) per industry; pooled residual df and interaction df clear their floors
  expect_true(all(tab$n[tab$model == "pac"] == 7L)); expect_true(all(tab$n[tab$model == "control"] == 6L))
  expect_true(all(tab$pooled_df >= 3L)); expect_true(all(tab$interaction_df >= 2L))
})

test_that("G4 withholds a model whose sample is too small and names it (negative control)", {
  ctx <- test_ctx()
  small <- ctx
  small$pac_panel <- ctx$pac_panel[ctx$pac_panel$cycle_end >= 2020 | ctx$pac_panel$sector != "credit_unions", ]
  g4 <- rf_gate_adequacy(small)
  cu <- g4$table[g4$table$industry == "credit_unions" & g4$table$model == "pac", ]
  expect_equal(cu$n, 3L); expect_false(cu$ok)
  expect_identical(g4$gate$status, "WARN")
  expect_true(any(vapply(g4$withheld$credit_unions, function(w) w$model == "pac", logical(1))))
})

test_that("G5 stability against the published v1: pooled slopes and own slopes keep their signs; leave-one-out sign consistency is reported", {
  v <- test_v2(); b <- test_bundle2()
  g5 <- rf_gate_stability(v, b, published_v1())
  if (g5$gate$status != "PASS") print(g5$table[!g5$table$ok, ])
  tab <- g5$table
  expect_true(any(grepl("pooled slope sign: pac", tab$check)))
  expect_true(any(grepl("existing industry slope sign: PAC commercial_banks", tab$check)))
  expect_true(any(grepl("leave-one-election-out sign consistency: lobby_log", tab$check)))
  expect_true(all(tab$ok[grepl("pooled slope sign|existing industry slope sign", tab$check)]))
  # PAC: every fold keeps the sign (7 of 7 cycles)
  expect_equal(v$sign$pac$loeo$share, 1)
})

test_that("G5 fails a flipped slope and a low sign consistency (negative controls)", {
  v <- test_v2(); b <- test_bundle2()
  flipped <- b; flipped$pac_model$slopes$commercial_banks$applied$beta <- abs(flipped$pac_model$slopes$commercial_banks$applied$beta)
  g <- rf_gate_stability(v, flipped, published_v1())
  expect_identical(g$gate$status, "HOLD")
  expect_match(g$gate$detail, "existing industry slope sign: PAC commercial_banks")
  pub <- published_v1(); pub$pac_model$beta <- -pub$pac_model$beta
  expect_identical(rf_gate_stability(v, b, pub)$gate$status, "HOLD")
  weak <- v; weak$sign$pac$loeo$share <- 0.5
  g2 <- rf_gate_stability(weak, b, published_v1())
  expect_identical(g2$gate$status, "HOLD"); expect_match(g2$gate$detail, "sign consistency: pac")
})

test_that("G6 is the hard backtest gate: PAC improves for every existing industry, and the previous-cycle House share anchor is worse for banks", {
  v <- test_v2()
  waivers <- rf_read_waivers()
  g6 <- rf_gate_nondegradation(v, published_v1(), waivers = waivers[waivers$term == "lobby", ])
  tab <- g6$table
  pac <- tab[tab$term == "pac", ]
  expect_equal(nrow(pac), 3L)
  expect_true(all(pac$ok))
  expect_equal(pac$new_MAE[pac$industry == "commercial_banks"], 10.81, tolerance = 1e-3)
  expect_equal(pac$published_MAE[pac$industry == "commercial_banks"], 27.74, tolerance = 1e-3)
  expect_equal(pac$published_MAE[pac$industry == "credit_unions"], 15.88, tolerance = 1e-3)
  h <- tab[tab$term == "control_House" & tab$industry == "commercial_banks", ]
  expect_equal(h$new_MAE, 1.54, tolerance = 1e-2); expect_equal(h$published_MAE, 1.05, tolerance = 1e-2)
  expect_false(h$ok)
  expect_identical(g6$gate$status, "HOLD")
  expect_match(g6$gate$detail, "control_House / commercial_banks")
  expect_false(grepl("lobby / commercial_banks", g6$gate$detail))                  # waived by the owner (registry/gate_waivers.json): not a HOLD cell
  lb <- tab[tab$term == "lobby" & tab$industry == "commercial_banks", ]
  expect_false(lb$ok); expect_true(lb$waived); expect_false(h$waived)
  expect_match(g6$baseline, "v1 calculator recomputed")
})

test_that("G6 waivers: a listed cell is WAIVED (not HOLD), every other cell stays strict, show_warning decides whether the gate speaks", {
  v <- test_v2()
  registered <- rf_read_waivers()
  expect_setequal(registered$cell, c("lobby / commercial_banks", "control_House / commercial_banks", "control_House / credit_unions", "control_House / auto_light_duty_manufacturing"))
  expect_true(all(registered$show_warning[registered$term == "control_House"]))
  w0 <- registered[registered$term == "lobby", ]
  expect_identical(w0$cell, "lobby / commercial_banks"); expect_identical(w0$owner, "Paul Goff"); expect_identical(w0$date, "2026-09-30")
  expect_identical(w0$reason, "owner ruling: keep log refit"); expect_false(w0$show_warning)
  none <- rf_gate_nondegradation(v, published_v1(), waivers = w0[0, ])
  expect_match(none$gate$detail, "lobby / commercial_banks")                        # without the list both cells hold
  expect_false(any(none$table$waived))
  one <- rf_gate_nondegradation(v, published_v1(), waivers = w0)
  expect_identical(one$gate$status, "HOLD"); expect_match(one$gate$detail, "control_House / commercial_banks"); expect_false(grepl("lobby / commercial_banks", one$gate$detail))
  expect_true(one$waivers$applied)
  both <- rbind(w0, transform(w0, cell = "control_House / commercial_banks", term = "control_House", industry = "commercial_banks", reason = "test"))
  quiet <- rf_gate_nondegradation(v, published_v1(), waivers = both)
  expect_identical(quiet$gate$status, "PASS"); expect_false(grepl("waived", quiet$gate$detail))       # show_warning false on both: the gate is silent
  expect_identical(nrow(quiet$waivers), 2L); expect_true(all(quiet$waivers$applied))                   # ...but both are still listed
  loud <- both; loud$show_warning[2] <- TRUE
  warned <- rf_gate_nondegradation(v, published_v1(), waivers = loud)
  expect_identical(warned$gate$status, "WARN"); expect_match(warned$gate$detail, "control_House / commercial_banks (test)", fixed = TRUE); expect_false(grepl("lobby / commercial_banks", warned$gate$detail))
  # a waiver whose cell no longer fails is listed as not applied
  pac <- transform(w0, cell = "pac / commercial_banks", term = "pac", industry = "commercial_banks")
  un <- rf_gate_nondegradation(v, published_v1(), waivers = pac)
  expect_false(un$waivers$applied); expect_identical(un$gate$status, "HOLD")
})

test_that("the waiver file is validated: a waiver without its reason, owner or date is an error", {
  f <- file.path(tempdir(), "w.json")
  writeLines('{"waivers": [{"cell": "lobby / x", "term": "lobby", "industry": "x", "owner": "Paul Goff", "date": "2026-09-30", "show_warning": false}]}', f)
  expect_error(rf_read_waivers(f), "lacks reason")
  writeLines('{"waivers": [{"cell": "a", "term": "lobby", "industry": "x", "reason": "r", "owner": "o", "date": "d", "show_warning": "no"}]}', f)
  expect_error(rf_read_waivers(f), "show_warning")
  expect_equal(nrow(rf_read_waivers(file.path(tempdir(), "missing.json"))), 0L)
})

test_that("G6 passes when the refit equals the published calculator within 1e-9 and fails a hair above it (boundary controls)", {
  v <- test_v2(); b <- test_bundle2()
  self <- rf_gate_nondegradation(v, b)                    # a v2 bundle published earlier supplies its recorded MAE
  expect_identical(self$gate$status, "PASS")
  expect_match(self$baseline, "published bundle")
  pub <- b
  mae <- pub$pac_model$evidence$calculator_path_loeo_mae_by_industry$commercial_banks
  pub$pac_model$evidence$calculator_path_loeo_mae_by_industry$commercial_banks <- mae - 5e-10     # published slightly better, inside the 1e-9 slack
  expect_identical(rf_gate_nondegradation(v, pub)$gate$status, "PASS")
  pub$pac_model$evidence$calculator_path_loeo_mae_by_industry$commercial_banks <- mae - 2e-9      # published better by more than the slack
  expect_identical(rf_gate_nondegradation(v, pub)$gate$status, "HOLD")
})

test_that("G7 validates the bundle against the contract and fails a bad one", {
  b <- test_bundle2()
  expect_identical(rf_gate_bundle(b, test_ctx()$reg)$status, "PASS")
  bad <- b; bad$share_models$seats_House <- list(id = "seats_House")
  expect_identical(rf_gate_bundle(bad, test_ctx()$reg)$status, "FAIL")
  bad <- b; bad$lobby_model$log_refit$beta <- NaN
  expect_identical(rf_gate_bundle(bad, test_ctx()$reg)$status, "FAIL")
  bad <- b; bad$industries$commercial_banks$capabilities$pac <- FALSE; bad$industries$commercial_banks$withheld <- list()
  g <- rf_gate_bundle(bad, test_ctx()$reg)
  expect_identical(g$status, "FAIL"); expect_match(g$detail, "capability 'pac' is false with no withheld reason")
})

test_that("G8 holds until a v2-capable calculator is configured, and follows the command's exit status (Windows included)", {
  p <- file.path(tempdir(), "g8_bundle.json"); writeLines("{}", p)
  expect_identical(rf_gate_consumer(p, cmd = "")$status, "HOLD")
  expect_match(rf_gate_consumer(p, cmd = "")$detail, "HOLD until the v2 calculator exists")
  skip_if(!nzchar(rf_g8_bash()), "no bash on this machine")
  # The detail is asserted as well as the status: before the fix every command on Windows ended with exit status 127 (bash read VAR=value, which R puts after the
  # command, as a script name), so "exit 3" held for the wrong reason. Here the status must be the command's own, and the variable must carry the bundle path.
  expect_identical(rf_gate_consumer(p, cmd = "test -n \"$MENTAT_GIVING_MODELS\"")$status, "PASS")
  shown <- rf_gate_consumer(p, cmd = "echo \"[$MENTAT_GIVING_MODELS]\"")
  expect_identical(shown$status, "PASS"); expect_match(shown$detail, "^exit status 0: \\[.*g8_bundle\\.json\\]$")
  failed <- rf_gate_consumer(p, cmd = "exit 3")
  expect_identical(failed$status, "HOLD"); expect_match(failed$detail, "^exit status 3:")
  unknown <- rf_gate_consumer(p, cmd = "g8_no_such_command_xyz")
  expect_identical(unknown$status, "HOLD"); expect_match(unknown$detail, "^exit status 127:")      # a missing command is the command's failure, not an R error
  # A command that uses coreutils (cat, head, tr) must work from a plain Windows PATH, where Git's usr/bin is not listed: <Git>/bin/bash.exe is the launcher that sets PATH up,
  # while the bash in usr/bin, started straight from R, answers "command not found" (exit status 127). The PATH of this check has no usr/bin entry on Windows.
  plain <- if (.Platform$OS.type == "windows") c(PATH = paste(Filter(function(d) !grepl("usr[\\\\/]bin", d, ignore.case = TRUE), strsplit(Sys.getenv("PATH"), ";")[[1]]), collapse = ";")) else character()
  with_plain_path <- function(code) if (length(plain)) rf_with_env(plain, code) else code
  skip_if(!nzchar(with_plain_path(rf_g8_bash())), "no Git for Windows bash outside the PATH's usr/bin")
  coreutils <- with_plain_path(rf_gate_consumer(p, cmd = "cat \"$MENTAT_GIVING_MODELS\" | head -c 2; echo abc | tr a-c A-C"))
  expect_identical(coreutils$status, "PASS"); expect_identical(coreutils$detail, "exit status 0: {}ABC")
})

test_that("rf_with_env sets variables for the call only, and G8 leaves MENTAT_GIVING_MODELS as it found it", {
  keep <- Sys.getenv("MENTAT_GIVING_MODELS", unset = NA)
  on.exit({ if (is.na(keep)) Sys.unsetenv("MENTAT_GIVING_MODELS") else Sys.setenv(MENTAT_GIVING_MODELS = keep); Sys.unsetenv(c("RF_T_A", "RF_T_B")) }, add = TRUE)
  Sys.setenv(RF_T_A = "a0"); Sys.unsetenv("RF_T_B")
  expect_identical(rf_with_env(c(RF_T_A = "a1", RF_T_B = "b1"), paste(Sys.getenv("RF_T_A"), Sys.getenv("RF_T_B"))), "a1 b1")
  expect_identical(Sys.getenv("RF_T_A"), "a0"); expect_true(is.na(Sys.getenv("RF_T_B", unset = NA)))        # the previous value is back, the unset one is unset again
  expect_error(rf_with_env(c(RF_T_A = "a2", RF_T_B = "b2"), stop("boom")), "boom")                        # also when the call fails
  expect_identical(Sys.getenv("RF_T_A"), "a0"); expect_true(is.na(Sys.getenv("RF_T_B", unset = NA)))
  skip_if(!nzchar(rf_g8_bash()), "no bash on this machine")
  p <- file.path(tempdir(), "g8_bundle.json"); writeLines("{}", p)
  Sys.unsetenv("MENTAT_GIVING_MODELS")
  expect_identical(rf_gate_consumer(p, cmd = "exit 0")$status, "PASS")
  expect_true(is.na(Sys.getenv("MENTAT_GIVING_MODELS", unset = NA)))
  Sys.setenv(MENTAT_GIVING_MODELS = "previous-value")
  expect_identical(rf_gate_consumer(p, cmd = "exit 3")$status, "HOLD")
  expect_identical(Sys.getenv("MENTAT_GIVING_MODELS"), "previous-value")
})

test_that("rf_g8_bash picks Git for Windows' bash launcher (bin) before usr/bin, never the WSL launcher, and G8 holds with the reason when there is none", {
  tree <- file.path(tempdir(), "g8_git_tree")
  for (d in c("cmd", "bin", "usr/bin", "mingw64/bin")) dir.create(file.path(tree, "Git", d), recursive = TRUE, showWarnings = FALSE)
  for (f in c("cmd/git.exe", "bin/bash.exe", "usr/bin/bash.exe", "mingw64/bin/git.exe")) file.create(file.path(tree, "Git", f))
  launcher <- normalizePath(file.path(tree, "Git", "bin", "bash.exe"), winslash = "/")
  for (git in file.path(tree, "Git", c("cmd/git.exe", "mingw64/bin/git.exe"))) {                            # git.exe in <Git>/cmd and in <Git>/mingw64/bin both lead to <Git>/bin/bash.exe
    for (wsl in c("C:\\Windows\\System32\\bash.exe", "C:/Windows/Sysnative/bash.exe", "C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps\\bash.exe", ""))
      expect_identical(rf_g8_bash(found = wsl, git = git, windows = TRUE), launcher, info = paste(wsl, git))   # the WSL launcher, or no bash on the PATH at all
    expect_identical(rf_g8_bash(found = "D:/tools/msys64/usr/bin/bash.exe", git = git, windows = TRUE), "D:/tools/msys64/usr/bin/bash.exe")   # any other bash is kept
  }
  expect_identical(rf_g8_bash(found = "/usr/bin/bash", git = "", windows = FALSE), "/usr/bin/bash")
  expect_identical(rf_g8_bash(found = "", git = "", windows = FALSE), "bash")
  skip_on_os(c("mac", "linux", "solaris"))                                                               # no Git for Windows anywhere: "" and an explained HOLD
  none <- file.path(tempdir(), "g8_nothing"); dir.create(none, showWarnings = FALSE)
  no_folders <- c(ProgramFiles = none, ProgramW6432 = none, "ProgramFiles(x86)" = none, LOCALAPPDATA = none)   # the default install folders hold no Git either
  # an installation without the launcher: the plain usr/bin bash is the fallback
  usr_only <- file.path(tempdir(), "g8_git_usr_only")
  for (d in c("cmd", "usr/bin")) dir.create(file.path(usr_only, "Git", d), recursive = TRUE, showWarnings = FALSE)
  for (f in c("cmd/git.exe", "usr/bin/bash.exe")) file.create(file.path(usr_only, "Git", f))
  expect_identical(rf_with_env(no_folders, rf_g8_bash(found = "", git = file.path(usr_only, "Git", "cmd", "git.exe"), windows = TRUE)),
                   normalizePath(file.path(usr_only, "Git", "usr", "bin", "bash.exe"), winslash = "/"))
  void <- c(PATH = none, no_folders)
  expect_identical(rf_with_env(void, rf_g8_bash(found = Sys.which("bash"), git = Sys.which("git"), windows = TRUE)), "")
  g <- rf_with_env(void, rf_gate_consumer(file.path(tempdir(), "g8_bundle.json"), cmd = "exit 0"))
  expect_identical(g$status, "HOLD"); expect_match(g$detail, "no bash to run the G8 command")
})

test_that("G9 is a warning only: a calculator path that does not beat last-period naive is reported, not blocked", {
  g9 <- rf_gate_naive(test_v2())
  expect_true(g9$status %in% c("PASS", "WARN"))
  expect_false(g9$status %in% c("HOLD", "FAIL"))
  lose <- test_v2(); lose$backtests$MAE[lose$backtests$term == "pac" & lose$backtests$rule == "naive_prev"] <- 1
  g <- rf_gate_naive(lose)
  expect_identical(g$status, "WARN"); expect_match(g$detail, "pac")
})

test_that("decision: any FAIL is FAIL, else any HOLD is HOLD, else PUBLISH; WARN never blocks", {
  mk <- function(...) data.frame(gate = paste0("G", seq_along(c(...))), status = c(...), detail = "", stringsAsFactors = FALSE)
  expect_identical(rf_decision(mk("PASS", "WARN", "PASS")), "PUBLISH")
  expect_identical(rf_decision(mk("PASS", "HOLD", "WARN")), "HOLD")
  expect_identical(rf_decision(mk("HOLD", "FAIL", "PASS")), "FAIL")
})

test_that("all gates of today's refit: HOLD because G8 is deliberately absent; owner-waived G6 degradations remain visible as WARN; nothing FAILs", {
  v <- test_v2(); b <- test_bundle2()
  base <- data.frame(gate = c("G0 environment", "G1 inputs", "G2 parity", "G3 panel validity"), status = "PASS", detail = "", stringsAsFactors = FALSE)
  g <- rf_gates(v, b, published = published_v1(), base = base, bundle_path = NULL, consumer_cmd = "")
  expect_identical(g$decision, "HOLD")
  st <- stats::setNames(g$gates$status, substr(g$gates$gate, 1, 2))
  expect_identical(st[["G4"]], "WARN"); expect_identical(st[["G5"]], "PASS"); expect_identical(st[["G6"]], "WARN")
  expect_identical(st[["G7"]], "PASS"); expect_identical(st[["G8"]], "HOLD")
  expect_false(any(g$gates$status == "FAIL"))
  # the finalized bundle carries its own gate summary and still validates against the contract
  b2 <- rf_bundle_v2(v, g$gates)
  expect_identical(b2$gates$decision, "HOLD")
  expect_identical(rf_validate_bundle(b2), character(0))
})

test_that("the default G8 command is MENTAT_G8_CMD when set, else the smoke script when the console's calculator sits beside the pipeline", {
  withr_env <- Sys.getenv("MENTAT_G8_CMD", unset = NA)
  on.exit(if (is.na(withr_env)) Sys.unsetenv("MENTAT_G8_CMD") else Sys.setenv(MENTAT_G8_CMD = withr_env), add = TRUE)
  Sys.setenv(MENTAT_G8_CMD = "exit 0"); expect_identical(rf_g8_default_cmd(), "exit 0")
  Sys.unsetenv("MENTAT_G8_CMD")
  app <- file.path(dirname(dirname(rf_home())), "app", "giving_forecast.py")
  if (file.exists(app) && nzchar(Sys.which("python"))) expect_match(rf_g8_default_cmd(), "g8_consumer_smoke.py", fixed = TRUE)
  else expect_identical(rf_g8_default_cmd(), "")        # a pod snapshot carries mentat/forecast only: G8 holds there, with the reason stated
})
