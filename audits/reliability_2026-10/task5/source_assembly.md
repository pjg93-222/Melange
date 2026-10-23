# Melange 1.0.17 release source assembly (Task 5)

Branch `release/1.0.17-prep`, cut from public main `34bfb2213cee0515b364d89318f6716d7c4f3243` (PR #57 merge). It is in the worktree `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\release-1.0.17-prep`. This phase did no build, no binary signing, no tag and no GitHub write. Commits went only to the local bare mirror, through the post-commit hook.

Code HEAD (the version commit plus the last Task 3 test commit): `a029e2dc3b1456b14fb3c45db56eed2f376931d3`, tree ``617a1c6d0a4368e19891707a6a6e2624a6fb652d``. The commit that adds this file and `build_plan.md` sits on top of it and adds only these two files under `audits/reliability_2026-10/task5/`.

Every commit in `34bfb2213..HEAD` has `%G?` = `G`. The signing key is the x509 smimesign key `0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30`. Imported commits keep their original author and message. `-x` was not used, because the instruction for re-signed commits was to add nothing; this table is the trace.

## Imported commits (old -> new)

| # | Source | Old | New | Subject | Notes |
|---|---|---|---|---|---|
| 1 | PR #59 signing layer | 8072057af | c16787a89 | Sign staged Windows payload and NSIS dependencies before packaging | clean |
| 2 | PR #59 | 859835911 | 3f5958a06 | Preserve Windows signing subprocess paths and verify native invocation | clean |
| 3 | PR #59 | 0fef93e20 | e8555df96 | Prepare Melange 1.0.16 signing-only release metadata | clean |
| 4 | PR #59 | 3958bc60b | 0fe293978 | Bound independent private binary signing to four workers | clean |
| 5 | visible startup | 46c22a9b4 | 7f0e32d9c | Show authorized data preparation before startup work | clean |
| 6 | PR #60 | f33fd73f6 | b7c593c73 | Require current helper evidence and fixed PowerShell verification | clean |
| 7 | PR #60 | 187ccd569 | 35d96759b | Remove signing policy and module-path overrides and test on Windows | clean; see risk R1 |
| 8 | PR #60 | b410b936d | 87fdf2d65 | Identify failed signature-result field without relaxing verification | clean |
| 9 | PR #60 | df9586f24 | 3c864393d | Diagnose copied vendor path identity without changing verification | clean |
| 10 | PR #60 | 3a76763cf | 0ddecbc9f | Canonicalize verified signing inputs and preserve current file identity | clean (PR #60 head) |
| 11 | Task 1 | d6db9c5b1 | 1db1d6862 | fix(surfaces): serve staffer-live workspace from pointer-flipped generations inside the chain transaction | conflicts C1-C3 |
| 12 | Task 1 | fd015fb37 | ef4e027a2 | fix(surfaces): install the served-generation resolver with the staffer-live server | clean |
| 13 | Task 1 | 3643b0a79 | a4d651480 | feat(pipeline): name served staffer-live generations after the chain run | audits hunk dropped (C4) |
| 14 | Task 1 | 7d9ba8cdc | a7a0c050d | fix(surfaces): seal served generations byte-exact and never prune without readable journals | audits hunks dropped (C4) |
| 15 | Task 4 | cdf9aa01a | a50b0bbbd | desktop: pin the installer publisher by thumbprint in the signed manifest | clean; its audits file removed in #20 |
| - | Task 4 | fc79b502f | (skipped) | desktop-admin: port PR #57 supervisor hardening onto local main lineage | empty on public main (PR #57 present); `--skip` |
| 16 | Task 4 | 6f5b8ec40 | db39f4eba | test(desktop-admin): cover supervisor log rotation and unwritable logs | clean |
| 17 | Task 4 | 3c36e8c91 | c5eef30e4 | desktop: port the shared scrape broker from the on-demand tree (default off) | conflicts C5-C6 |
| 18 | Task 4 | f9ca77e7f | 0bcbee160 | test(scrape-broker): cover the remaining shared-service guarantees | clean |
| 19 | Task 4 | cca06f479 | 8a60616df | test(stance): reproduce the weekly 10-18 Stage 5 failure as a cloud recall | clean |
| 20 | assembly | - | 707d0abfb | chore(release): keep the Task 4 decision record off the public release source | authored here |
| 21 | Task 2 | 6e4a07ce8 | d762327c3 | fix(personal-texture): publish catch-net rows only for current roster members | clean |
| 22 | Task 2 | 91ed28ff3 | f468d7292 | fix(big5): cap each trait's published evidence status at its ratified level | clean |
| 23 | Task 3 | 2d9a013d2 | 303ff815a | Port on-demand public payroll pages from the preserved on-demand tree | conflict C7 |
| 24 | Task 3 | b9550a938 | 6588ffe40 | Add public page contracts, a verified publication seam and a module reader | clean (auto-merged with Task 4 in refresh_fec_money.py and collect_official_rollcall_events.py) |
| 25 | Task 3 | 64c474b5b | 9d556970d | feat(desktop): leave legacy module-data providers on their default transport (Task 3) | `-n`; 9 audits paths dropped; main.cjs only |
| 26 | assembly | - | 92fe1550e | fix(desktop): re-hash the Melange program inventory after merging Tasks 1 and 3 | authored here (C8) |
| 27 | assembly | - | 336e00a9c | Prepare Melange 1.0.17 release metadata | package.json + package-lock.json 1.0.16 -> 1.0.17, same files as 0fef93e20 |
| 28 | Task 3 | f159a37c7 | a029e2dc3 | test(desktop): stricter Task 3 demand-cache and paged-mode catalogue tests | `-n`; 5 audits paths dropped; two test files only |

Order note: f159a37c7 arrived after the version commit was made, so it sits on top of it. The version commit changes only the two version fields, so the order has no effect on content.

`git cherry -v 34bfb2213 HEAD`: 28 commits before this documentation commit.

## Conflicts and resolutions

- **C1 `.gitignore` (d6db9c5b1), deleted on public main, modified by Task 1.** Public main has no root `.gitignore`, because the export filter publishes only `fec/`, `ops/` and `requirements.txt`. Resolved by keeping it absent. The generations directory is still excluded from packaging by the `runtime-manifest.json` hunk, which merged cleanly (`fec/surfaces/staffer_live/generations` in `excludedSourcePrefixes`).
- **C2 `fec/tests/surfaces/test_original_workspace.py` (d6db9c5b1), deleted on public main.** Kept absent; the export filter excluded it from the public tree.
- **C3 `fec/surfaces/build_clean_workspace.py`.** The private side's context held `remove_tree()`, which came from a separate private-lineage commit (the OneDrive read-only rmtree fix) that is not on public main. Took the public side without `remove_tree` and applied Task 1's new `people_days(prior_dir=None)` signature and body. The public file keeps its own `shutil.rmtree` calls. py_compile passes and the Task 1 suite passes (53).
- **C4 `audits/reliability_2026-10/task1/receipt.md` and `tests.md` (3643b0a79, 7d9ba8cdc).** These receipt hunks rode in code commits. The files do not exist on this branch, so they were dropped; the code hunks are intact.
- **C5 `ops/desktop/client/builder.cjs` (3c36e8c91).** Kept the public signing layer (`...releaseSigning`, `...releaseSigning.win`) and added the broker switch (`DESKTOP_SHARED_SCRAPE`, default off) and `desktopScrapeBroker` in `desktopAppConfig`.
- **C6 `ops/desktop/client/runtime.cjs` (3c36e8c91).** Kept the public module-data runtime: `initializeModuleRuntime`, `start(configuration,capability)`, `refuseModuleDataSettings`, module input piping and the coordinator teardown. Wove the broker into it: `scrapeFactory` option and `this.scrape` field; the scrape service is closed on spawn failure (a new `catch` around `spawn` closes renderer and scrape), on backend exit, and in `stop()`. The broker setup and check hunks merged cleanly.
- **C7 `ops/desktop/client/builder.cjs` (2d9a013d2).** Kept both declarations (broker switch and `DESKTOP_PUBLIC_DATA_MODE`, default `legacy`). `desktopAppConfig` carries both `desktopScrapeBroker` and `desktopPublicData`; the signing spread is unchanged. `main.cjs` auto-merged and carries both `scrapeFactory` (line 309) and `desktopPublicData`.
- **C8 program inventory (Task 1 x Task 3).** `refresh_module_inventory.py --app melange` (check mode) reported drift in exactly the two inventoried files that Task 1 changed: `ops/desktop/packaging/desktop_backend.py` and `fec/surfaces/staffer_live_server.py`. Both now import `fec/surfaces/staffer_live_generation.py`. The inventory lists the import closure (it includes `staffer_assertions.py` and `melange_dashboard.py`, which `staffer_live_server.py` imports alongside it), so the resolver was added to `ADDITIONS` and the Melange declaration re-hashed with `--write`. Check mode now verifies clean. The Mentat declaration is retained as-is (split-repository rule), so its `desktop_backend.py` bootstrap entry still carries the pre-Task-1 hash. That matters only if Mentat is ever packaged from this tree.

fc79b502f check: against HEAD, four of its five files are byte-identical (DEPLOYMENT.md, Register-LanPublisherStartup.ps1, Start-LanPublisherAtLogin.ps1, test_windows_admin_supervisor.py). `README.md` differs only in a launcher sentence that already differed between the lineages; its PR #57 section is present.

## Excluded items

- **PR #25** (D-157 residual, deferred to Task 6, open against main): `be31698334cef9b121a6ab7401f6b7c67e37c8dc` "D-157 residual items: frontier caption, press-only disclosure, re-click deselect, live crown source, interview name match, two retirements"; `306cfb1c4b823622f1df0aa83c94a874d7be4f60` "D-157 follow-up: stop the F-17 test reading the unpublished attic copy, and register the new node test"; `933afa44440c14aa87f79f6f6eabbee083b6c083` "D-157 CodeRabbit round 1: interview recovery note, pinned name-match mode, real word boundary". Reason: deferred to Task 6 by the lead.
- **Task 0 `d1123709`**: receipts only, on private-lineage audit paths. The final report lands separately.
- **Receipt-only commits:** Task 1 `0cf79845d` (task1 receipt and tests), Task 4 `f5e13e656` (Task 4 receipts), Task 2 `055a9b900` (failure classification, decisions, audit_full logs, before-hashes) and `481edc1e7` (rulings, residual list, and the 6.6 MB `before_image_uncommitted/member_personal_texture.json`). Reason: step 3 imports code commits, and the public lineage carries code only. These files name private data stores and incident details, so neither they nor the data artifact entered the branch.
- **`audits/` paths inside code commits:** `audits/reliability_2026-10/updater-publisher-verification-decision.md` (from cdf9aa01a, removed by 707d0abfb; it remains in this branch's history and has no private paths); task1 receipt/tests hunks (3643b0a79, 7d9ba8cdc); 9 paths from 64c474b5b (serving_inventory.json, task3/check_node.txt, check_packaging.txt, check_surfaces.txt, inventory_summary.md, on-demand-current.unsigned-payload.json, port_notes.md, receipt.md, scout_runtime_trace.md); 5 paths from f159a37c7 (serving_inventory.json, task3/inventory_summary.md, port_notes.md, receipt.md, scout_runtime_trace.md).
- **Task 2 `54022759c`** "fix(profiles): bind the profile refresh and its readers to the roster snapshot": **not cherry-picked; it does not apply to this lineage.** It calls `roster.names()/drift()/count()/members()/arrivals()` from `fec/roster.py`, the 535-member roster module (private commits 632029479 and 6420612ac). That module does not exist on the public lineage, where `regenerate_member_profiles.py` and `make_member_desk.py` still hard-code 533. Its `make_member_desk.py` hunk also depends on private district-brief coverage code (`kept`, `withheld`, `dropped`). Porting it means porting the roster feature first; that is a scope decision for the lead. The cherry-pick was aborted with no partial content.

## Tests

Data-dependent failures are listed separately and not fixed: the public lineage has no `data/`, Terrier source or Mentat engine.

| Step | Command | Result |
|---|---|---|
| Task 1 | `pytest fec/tests/surfaces/test_served_generation_txn.py fec/tests/infra/test_chain_transaction.py` | 53 passed |
| Task 4 | `node --test ops/desktop/client/tests/*.test.cjs` (NODE_PATH = main checkout node_modules, read-only) | 647 tests, 646 pass, 1 fail (R1) |
| Task 4 | `pytest test_scrape_broker.py test_access_http.py test_windows_admin_supervisor.py test_github_release.py` | 89 passed, 2 skipped, 61 subtests |
| Task 4 | `pytest fec/tests/test_scrape_client.py fec/tests/stance/test_press_stage5_unreadable_model.py` | 13 passed |
| Task 2 | `pytest fec/tests/members/test_ratified_trait_status.py fec/tests/members/test_personal_texture_roster_scope.py` | 5 passed |
| Task 3 | `node --test ops/desktop/client/tests/*.test.cjs` | 650 tests, 649 pass, 1 fail (R1) |
| Task 3 | `pytest ops/desktop/packaging fec/tests/surfaces/test_demand_cache.py` | 404 passed, 7 skipped, 1 failed, 42 errors: all environmental (below) |
| Inventory | module inventory / data launch / snapshot / generation publish tests + module contract and transport node tests | 52 passed, 1 skipped; node 23/23 |
| Final, at a029e2dc3 | `node --test ops/desktop/client/tests/*.test.cjs` | 651 tests, 650 pass, 1 fail (R1) |
| Final, at 336e00a9c (a029e2dc3 touches neither directory) | `pytest ops/desktop/packaging ops/desktop/server` | 688 passed, 7 skipped, 469 subtests; 1 failed + 42 errors, all environmental (below) |
| Final, at a029e2dc3 | `pytest` demand_cache, served_generation_txn, chain_transaction, ratified_trait_status, personal_texture_roster_scope, profile_evidence_refresh, scrape_client, press_stage5_unreadable_model | 86 passed, 4 subtests |
| Final | `refresh_module_inventory.py --app melange` (check) | verified, no drift |

Environmental failures, the same set every run: 42 errors in `test_terrier_desktop_access.py` (9), `test_terrier_district.py` (10), `test_terrier_owner.py` (6) and `test_terrier_principal.py` (17), all `KeyError: 'TERRIER_TEST_SOURCE'`; 1 failure in `test_mentat_layout.py::test_index_identity_preserved_with_installed_code_and_selected_data` (`KeyError: 'MENTAT_TEST_ENGINE'`). These suites need an external Terrier source or Mentat engine named by environment variable.

Static checks over `34bfb2213..HEAD`: `node --check` on all 25 added or modified `.cjs` files: 0 failures. `py_compile` on all 47 added or modified `.py` files (bytecode prefix in the session scratchpad): pass. No path under `data/` was added. No added or modified file is over 1 MB; the largest is `fec/audit/audit_full.py` at 213 KB, an existing source file.

Signing-surface confirmations:
- `publisherThumbprints` is emitted by both manifest writers: `ops/desktop/packaging/github_release.py:134` (`'publisherThumbprints': list(PUBLISHER_THUMBPRINTS)`, imported from desktop_admin) and `ops/desktop/server/desktop_admin.py:519`. `PUBLISHER_THUMBPRINTS = ("0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30",)` (desktop_admin.py:47).
- `ops/desktop/client/release-signing.cjs` (10286 bytes) and `ops/desktop/client/sign-staged-binary.ps1` (4524 bytes) are present. The timestamp line, `sign-staged-binary.ps1:40`: `& $signtool sign /sha1 $thumbprint /s My /fd sha256 /tr http://timestamp.digicert.com /td sha256 $filePath | Out-Null`.
- Version: `ops/desktop/client/package.json` and `package-lock.json` (2 fields) are `1.0.17`.

`git diff --shortstat 46c22a9b4..HEAD` (1.0.16 source to this code HEAD; includes PR #55-57): 84 files changed, 5823 insertions(+), 215 deletions(-). `git diff --shortstat 34bfb2213..HEAD`: 80 files changed, 4934 insertions(+), 137 deletions(-).

## Open risks

- **R1 PowerShell execution policy (signing hook).** PR #60 `187ccd569` removed `-ExecutionPolicy Bypass` from the hook's `powershell.exe` invocation. On this machine every policy scope is `Undefined`, so Windows applies `Restricted` and refuses `sign-staged-binary.ps1`. That is the one failing node test ("actual Windows subprocess verifies a copied vendor binary without signing or changing it"), and the release build's signing hook will fail the same way. How the build host permits that script is a security-setting decision for Paul; see build_plan.md.
- **R2 Module journal shared across modes (Task 3, not resolved here).** Both module-data modes (`legacy` and `paged-v1`) share one module journal. A paged-mode probe with the network down returned the old legacy snapshot as its candidate. Paged mode stays off by default in this source (`DESKTOP_PUBLIC_DATA_MODE` unset means `legacy`). Listed for the Task 8 FAIL/OPS rows.
- **R3 Task 2 roster binding absent** (54022759c above). The public lineage still has 533 hard-coded in the profile refresh and the member desk. The fix ships only after the roster module is ported.
- **R4 Release verifier and runtime.** The 1.0.16 build re-packaged the 1.0.15 runtime, and the existing verifier accepts only signing deltas. See build_plan.md for the required runtime re-stage and verifier variant.
- **R5 Mentat inventory entry** carries the pre-Task-1 `desktop_backend.py` hash (C8). Inert for a Melange build.
