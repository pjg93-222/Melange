# Staffer people-network landing v4.1: the fix round after the Opus re-check and the live panel (cut 2026-10-04, NOT applied)

One patch, cut with `fec/tools/live_patch.py` (D-060) against the bytes LIVE holds now, with `..\landing_v2\`, `..\landing_v3_ids\` and `..\landing_v4\` applied there. It carries five fixes to features Paul approved, found by the Opus re-check of v4 (`..\verify_v4b\`) and by the live panel on the sidecar that runs v4 (`..\live_panel_v4\`).
It changes no data file, schema or dial, and no route answer: every new test compares an answer with the same request on an untouched twin router.
No file in LIVE's working tree was written, applied, staged or committed by the cut or by any proof, and the sidecar on 127.0.0.1:8841 (PID 36412) was not touched (no script here connects to it; the tests that start servers use ephemeral ports).
It is a fourth patch, not a replacement: apply it on top of landing_v4 (the apply script refuses otherwise).

| | |
|---|---|
| Branch | `claude/staffer-route-v4-1-20261004`, worktree `C:\Users\pgoff\Melange-wt\route-core`, tip `19a5c28bcf98f13e346ea27e4c7ca56bd1d9680b` |
| Built from | `79ef9f1b7440bcee21c7f7c677a93263d9fcc04a`, the v4 tip that LIVE runs, plus three commits: `c2dbf7148` (fixes 1 to 3), `85be3cb4c` (fix 4), `19a5c28bc` (fix 5) |
| Requires | `..\landing_v4\` applied to LIVE first. It is: all 26 files landing_v4 touched hold its post-images, byte for byte (the dry run below is clean) |
| LIVE HEAD | `3366a7840f90a204d496070da11354245d18f741` ("Land the people-network latency work (landing_v2, landing_v3_ids, landing_v4)"): another lane committed the 45 files of the three landings (all of them under `fec/`, as LF blobs) and an audit packet of 128 files while this was cut. No working file changed. HEAD is recorded and is not a gate: the gate is the sha256 of every edited working file, in the cut and again in the apply script |
| Patch | `staffer_route_v4_1.patch`, 100,838 bytes, sha256 `fcb52fbdad630b20dd9f98d0c3a3a558f40ef41873afc0c1ccb1ee8ce3a6844d` (+967 / -66 lines) |
| Files | 11: 10 edited in place, 1 new (a test). List, pre- and post-image hashes and terminator profiles in MANIFEST.txt |
| Effect on LIVE's `git status` | the 10 edited files, clean now that HEAD holds them, become ` M`; the new test file is `??` (committing is a separate decision) |
| Needs a restart | **The Python half, yes; the page half, no.** See "Restart" below |

## What it contains

Five fixes, in three commits. Each is a fix to an approved feature, not a new one.

1. **The collection runs only after a router was replaced (`c2dbf7148`).** The prewarm ran one full `gc.collect()` before its first build at a start as well as after every publish. At a start nothing has been replaced, so it freed nothing, and it held every request thread for **10.1 s** on the live heap (`gc_ms` 10,145.99 on `GET /api/staffer-performance` in the live panel). `LiveService._release_replaced_router` now sets a flag (`_router_replaced`, under the prewarm lock) when it is given a router that was actually replaced (not `None`, not the router just published), and `_prewarm` collects only when it finds the flag set, clearing it in the same step, once, before its first build. A prewarm abandoned before it builds neither collects nor clears it, so the prewarm that does build collects for every swap since the last collection. The first prewarm after a start has no `gc_ms`.
2. **One work index per search request, and a released router stores nothing (`c2dbf7148`).** Distinct and independent alternatives call `ClosenessRoutes.route` once per pass and each call asked the router's table for its work index, so a release that landed between two passes of a request still running on the replaced router made the next pass build the whole index again (finding A1: tens of seconds on the live records, for one request, on a router nothing else will use). `AdvocacyRouter.route_many` now opens a request scope, a contextvar (`staffer_closeness_routes.request_work`), around `distinct_routes` and around the Yen loop of the other objectives, and `ClosenessRoutes.index` checks it first and gives a request the index it took first for all its later passes (a scope that is open already is the request's own, and it closes however the request ends). `ClosenessRoutes` also has a `released` flag, set by `release()` and never cleared: a released router stores no index and no hop-row cache it builds, and an index whose build was still running at the release is not put back into the emptied table (the re-check watched the old router's prewarm build put it back, which kept the replaced router's whole index alive). It still answers every request that reaches it: a request with a scope shares one index and one hop-row cache among its passes, one without builds its own. `AdvocacyRouter.release_search_state` now creates the search object of a router that has none yet, so that router is released as well (the service always has one; this closes the gap for any other caller).
3. **The memory claim is qualified (`c2dbf7148`).** The README and two comments in `staffer_live_service.py` said the replaced router's indexes and the new router's "are not resident together". That is so only once no request is still running on the replaced router: such a request keeps its index until it ends, and no collection frees what it still refers to. They now say so, and that a start runs no collection.
4. **The left-out line names the coverage the model reads (`85be3cb4c`, finding D1).** With `work_sources=directory` the work index holds directory episodes only, so nobody has payroll evidence there and "uncovered" means "not on the staffer roster": a person with payroll rows and no roster entry is left out of that comparison, and the page said the staff "lack the payroll or staffer-roster coverage". Every office answer now carries `uncovered_basis` beside `uncovered_staff_count` and `uncovered_staff_ids`: `payroll_or_roster`, or `roster` when `work_sources` is `directory` (decided by the mode, because that is what the model can use, not by whether the world holds payroll rows; `distinct_routes` hands it to every route). The page picks the wording:
   - `roster`: **"N of this office's current staff lack the staffer-roster coverage this model requires and were left out."** and, for one person, **"1 of this office's current staff lacks the staffer-roster coverage this model requires and was left out."**
   - `payroll_or_roster`, any other value, and none (a page in front of an older server): the strings it had, "N of this office's current staff lack the payroll or staffer-roster coverage this model requires and were left out." and "1 of this office's current staff lacks the payroll or staffer-roster coverage this model requires and was left out."
5. **`explanation` is the `message` (`19a5c28bc`, finding A4, cosmetic).** An unreachable Staffer answer that carries an `unreachable_reason` and a `message` now has the same text in `explanation`, and nothing after it (the page's default three distinct routes used to add the sentence about how alternatives are found after the generic one; such an answer has no routes). An unreachable answer without a reason (Ecosystem's) keeps the generic sentence "No supported path exists in the currently indexed evidence under these filters. This does not establish that no real-world introduction is possible." and the note about alternatives; found, `unknown_person` and `insufficient_work_coverage` answers are worded as before; a payload with a reason but no message keeps the generic sentence (the condition the page uses for its own line).

Files (the change is `+added / -removed` lines of the patch):

| File | Change | What |
|---|---|---|
| `fec/surfaces/staffer_closeness_routes.py` | +88 / -11 | `request_work` and `_RequestWork`, `released`, `_shared_index`, `_unstored_row_cache`, `uncovered_basis`, the module docstring |
| `fec/surfaces/staffer_distinct_routes.py` | +3 / -2 | `uncovered_basis` travels with the two counts |
| `fec/surfaces/staffer_live/README.md` | +2 / -2 | the sentences of fixes 1 to 5 |
| `fec/surfaces/staffer_live/staffer-route.js` | +3 / -2 | the roster wording of the left-out line |
| `fec/surfaces/staffer_live_service.py` | +33 / -14 | the collection flag (`_router_replaced`), the qualified memory comments, `explanation` for an unreachable answer with a reason |
| `fec/surfaces/staffer_routing.py` | +21 / -6 | `_one_work_index` (opened in `route_many` around `distinct_routes` and the Yen loop), `release_search_state` creates the search object of a router that has none |
| `fec/tests/surfaces/test_staffer_left_out_staff.cjs` | +70 / -4 | the roster scenario, the any-other-basis scenario, a negative control against the v4 page, four more deliberate page bugs |
| `fec/tests/surfaces/test_staffer_office_covered_staff.py` | +128 / -4 | `uncovered_basis`: the directory scenario of the re-check on a router, the service and the handler, a negative control; the new-field set |
| `fec/tests/surfaces/test_staffer_prewarm.py` | +110 / -19 | no collection at a start, one after a replacement, abandoned prewarms, only an actual replacement asks, a request waiting on the replaced router's in-flight build; the released router keeps nothing |
| `fec/tests/surfaces/test_staffer_request_work_index.py` | +416 (new file) | new: the re-check's release between the passes (distinct, independent, ranked) with its negative controls, a request on a released router, an in-flight build, the scope itself, a short stress run |
| `fec/tests/surfaces/test_staffer_unreachable_hint.py` | +93 / -2 | `explanation` equals `message` for all nine reasons and four strategies, over HTTP, the cases that keep the generic sentence, a negative control; the new-field set |

## Intended changes of existing expectations

The four existing test files the round changed, as they were at `79ef9f1b7`, run against the new code (`proof\old_tests_on_new_code.txt`): **40 of 142 tests fail (35 of 62 in `test_staffer_office_covered_staff.py`, 3 of 31 in `test_staffer_prewarm.py`, 1 of 21 in `test_staffer_unreachable_hint.py`, 1 of 28 in `test_staffer_left_out_staff.cjs`)**. Every one asserts something the round changed on purpose, and every other test of those files passes:

1. `test_staffer_prewarm.py`, 3 tests (the released router stores nothing, and a start collects nothing): `test_a_router_swap_during_the_prewarm_discards_it` asserted that the replaced router's table holds the index its in-flight build finished (it is not put back now);
   `test_a_request_that_reaches_the_released_router_builds_again_and_answers_exactly_as_before` asserted that the released router stored the index its next request built (it keeps nothing now; renamed `..._builds_its_own_index_...`);
   `test_one_collection_runs_before_the_first_build_of_a_prewarm_and_none_in_an_abandoned_one` asserted a collection at a start (replaced by four tests: none at a start, one after a replacement and a later prewarm none, abandoned prewarms collect nothing and the one that builds collects for every swap, only an actual replacement asks for one).
   The identity-rebuild test gains one assertion (the replacement asked for a collection), and one test is new (the in-flight build of the replaced router).
2. `test_staffer_office_covered_staff.py`, 35 tests: `uncovered_basis` is a third field an office answer gains, and every comparison with the base commit drops the fields the change added (`NEW_FIELDS` has three members now; `left_out()` still returns the two count fields): the nine fully-covered cases, the nobody-covered case, the two uncovered-origin cases, the eighteen mixed-office cases, the four unreachable reasons and the random-world comparison.
3. `test_staffer_unreachable_hint.py`, 1 test: its comparison with the base commit (`OFFICE_COVERAGE_FIELDS` has the third field).
4. `test_staffer_left_out_staff.cjs`, 1 test: the deliberate page bug that puts the "no work records" wording back reads its anchor from the new template (the line is built from `${coverage}` now).
   Nothing else changed its expectation: the other 102 tests of those four files pass against the new code, as they were.

## Restart

- **Page half, no restart.** `staffer-route.js` and the README are static: the sidecar reads them from disk on every request (`send_asset`, `Cache-Control: no-store`), so they are served on the next page load. New page code in front of the old Python still works: an old answer has no `uncovered_basis`, so the line keeps the payroll-or-roster wording it always had.
- **Python half, yes.** `staffer_closeness_routes.py`, `staffer_distinct_routes.py`, `staffer_live_service.py` and `staffer_routing.py` are loaded by the running sidecar (PID 36412), which keeps what it imported. The collection rule, the request scope, the released router and the `uncovered_basis` and `explanation` fields take effect only when 8841 restarts. Restarting is Paul's call (D-080: started once, the scheduled task stays disabled).
- **Order: stop 8841, apply, start**, as for the earlier landings: `staffer_routing.py` imports `staffer_closeness_routes` and `staffer_distinct_routes` lazily, so a sidecar that has not served a Staffer route since its start would load the new files next to its old `staffer_live_service.py` and `staffer_routing.py`.
- After the start, `GET /api/staffer-performance` should show `metrics.prewarm` without `gc_ms` for the first prewarm (nothing was replaced) and a `total_ms` shorter by what `gc_ms` was (10.1 s on the live heap in the panel); the first publish after it shows a `gc_ms`, which is the one collection that is meant to stay (it frees the replaced router before the new indexes are built). `MELANGE_STAFFER_PREWARM=0` still turns the prewarm and its collection off.

## Apply (Paul's step)

Preconditions are enforced twice, by `apply_landing.py`'s pre-flight and again by `apply_to()`: every file the patch edits must hash to its pre-image in MANIFEST.txt (landing_v4's post-image: what LIVE holds now) and the new file must not exist. A tree that does not hold them gets the dry run's own refusal, with the files named, and nothing is written.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'      # the scripts import fec/tools/live_patch.py from LIVE; write no bytecode there

# 0. optional read-only report: HEAD, each file's hash against its pre-image, the dry run, the raw git check, the rollback plan
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4_1\scripts\dry_run_live.py"

# 1. dry run: pre-image check, then git apply --check; writes nothing
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4_1\scripts\apply_landing.py"

# 2. apply to LIVE (live_patch.apply_to: refuses a moved target, checks every post-image sha256, puts the bytes back on any failure)
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4_1\scripts\apply_landing.py" --apply
```

The same patch with plain git, without the hash gates (D-060's command):

```powershell
git -C "C:\Users\pgoff\OneDrive\Desktop\Melange Systems" -c core.autocrlf=false -c core.safecrlf=false apply "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4_1\staffer_route_v4_1.patch"
```

Never use `--index` or `--cached` (LIVE blobs are pure LF), never a plain `git apply` without `-c core.autocrlf=false`, and do not EOL-normalise LIVE (D-060, DE-041).

## Rollback

```powershell
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4_1\scripts\rollback_landing.py"                # plan: writes nothing
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4_1\scripts\rollback_landing.py" --rollback     # restores the 10 saved pre-images byte for byte, removes the new file
```

A file edited after the apply stops the rollback and nothing changes (`--force` overrides). The pre-images in `pre_images\` are LIVE's bytes as they were (landing_v4's post-images), so this puts LIVE back to "landing_v4 applied". Roll back in reverse order: landing_v4's own rollback refuses while this patch is on. For a tree whose files are still exactly the post-images, the other way back is `git -C "<LIVE>" -c core.autocrlf=false -c core.safecrlf=false apply -R "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4_1\staffer_route_v4_1.patch"`. Rolling back the Python half needs the same stop, roll back, start sequence as the apply.

Node tests in LIVE after the apply (the negative controls read `a9db5fd5f` and `79ef9f1b7` from LIVE's own repository, which holds them, so they run there too):

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
node --test fec/tests/surfaces/test_staffer_left_out_staff.cjs fec/tests/surfaces/test_staffer_unreachable_hint.cjs fec/tests/surfaces/test_staffer_route_models.cjs
python -m pytest fec/tests/surfaces/test_staffer_prewarm.py fec/tests/surfaces/test_staffer_request_work_index.py fec/tests/surfaces/test_staffer_office_covered_staff.py fec/tests/surfaces/test_staffer_unreachable_hint.py -q
```

## How it was cut (D-060, DE-040, DE-041) and proved

`scripts\cut_landing.py` (landing_v4's cutter; this cut changes where the pre-images and the base come from). Bytes end to end, lines split on LF only (`live_patch.split_lines`). The pre-image of every edited file is LIVE's own working file as it is now, read in binary and read-only, and it must equal landing_v4's post-image (its summary's hash, and byte for byte against its `post_images`) or the cut stops. For each edited file the pre-image must equal the base blob (`79ef9f1b7`) line for line (it did, for all 10).
Every changed region of base to tip is spliced into the pre-image's own lines; its anchor (unchanged context on both sides plus the old lines) must hit exactly once; inserted lines carry the file's majority terminator; untouched lines are never rewritten; after the last splice the content equals the tip blob line for line. The new file carries the exact tip bytes (pure LF in the blob). The patch is stored here, outside every repository (DE-040). No string replacement is used to cut. `prove()` passed at the cut (`proof\cut_output.txt`).
The terminator profiles that matter, from MANIFEST.txt: `staffer_closeness_routes.py` is MIXED in LIVE (968 CRLF, 5 bare LF; after 1,045 and 5), `staffer_routing.py` MIXED (691 and 1; after 706 and 1), `README.md`, `staffer-route.js` and `staffer_live_service.py` PURE_CRLF and stay so, the other edited files PURE_LF and stay so.

Proofs, all run on the cut as it is (`proof\`):

1. **Main proof**, `scripts\prove_landing.py` (`proof\proof_results.txt`): **142 checks passed, 0 failed.**
   - The patch holds exactly the files that differ between `79ef9f1b7` and the tip (11: 1 added, 10 modified, no deletion or rename). Each pre-image is LIVE's bytes now, byte for byte, and equals landing_v4's post-image (its summary hash, and its `post_images`).
   - Scratch tree of the pre-images, `apply_to()` there, then `live_patch.py drift` of every post-image against the branch tip's file in the worktree: **3 IDENTICAL_BYTES, 8 EOL_ONLY, 0 CONTENT.** Each EOL_ONLY file has the same content as the tip blob line for line and only terminators differ (an edited file keeps its own terminators, a new file carries the blob's LF, the worktree holds git-checkout CRLF; explained file by file in the proof). Against the tip's git blob: 6 IDENTICAL_BYTES, 5 EOL_ONLY, 0 CONTENT.
   - Terminator audit: with lines aligned by the base-to-tip diff, every untouched line is byte-identical (terminator included) between pre-image and post-image in all 10 edited files, every inserted line carries the majority terminator, no lone CR appears, bare-LF counts do not grow in the CRLF-majority files.
   - Against LIVE itself (read-only): the dry run passes with rc=0 (all 11 files at their pre-image hashes, 10 equal, the new file absent), raw `git -c core.autocrlf=false apply --check` passes, all 26 files landing_v4 touched hold its post-image, the new path does not exist and is not tracked. LIVE HEAD (`3366a7840`) is printed with the commits since landing_v4's base; it is not a gate.
   - Both rollbacks (`git apply -R`, and the saved pre-images) restore the scratch tree byte for byte and remove the new file.
   - Every post-image JavaScript file passes `node --check` (2 files) and every Python file compiles (8).
2. **Operator scripts**, `scripts\prove_scripts.py` (`proof\script_proofs.txt`): ALL PASS (22 checks), on scratch trees: refused on what LIVE held before landing_v4 (dry run and `--apply`, nothing written), refused on a tree with one moved target and on a tree that already holds the new file (nothing written), dry run, `--apply`, a second `--apply` refused, rollback plan, rollback refused after a later edit, rollback, a second rollback a no-op.
3. **Order**, `scripts\prove_chain.py` (`proof\chain_proof.txt`): ALL PASS (23 checks), with landing_v4's and v4.1's real scripts on a scratch tree built from landing_v4's pre-images: v4.1 refused before landing_v4, landing_v4 applied, v4.1 applied (27 watched paths checked byte for byte at every step; v4.1 changed exactly its 11 files), landing_v4 applied again and refused, landing_v4's rollback refused while v4.1 is on, then both rolled back in reverse to the start.
4. **The applied tree against the tip**, `scripts\build_applied_tree.py` and `scripts\applied_tree_run.sh` (`proof\applied_tree_suites.txt`): the tree LIVE will hold after the apply (clean `git archive 3366a7840 fec`, LIVE's current bytes for the 45 files of the three landings, `apply_landing.py --apply`) and every staffer suite on it: **80 files, 1,786 passed, 1 failed (the known red), 64 skipped; all 80 files have the same counts and the same failures as the clean export of the tip**, peak memory of the process tree 587 MB (`proof\applied_tree_suites.txt`).
5. **The dry run against the real LIVE tree**, read-only, `scripts\dry_run_live.py` (`proof\dry_run_against_live.txt`): rc=0 as above, and the rollback plan reports every edited file "already original" and the new file "already absent".

LIVE was fingerprinted read-only (`scripts\live_fingerprint.py`) at the start of the work and at its end: `proof\live_untouched.txt`.

The branch's three commits were made from the finished work by `scripts\branch_work\build_commits.py` (the exact-anchor edit scripts `edit_*.py` beside it made the changes; the commit messages are in `scripts\branch_work\commit_messages\`): it restores the ten changed files to the v4 tip, applies each fix's edits and commits, and compares the worktree with the finished state byte for byte after the third commit (11 files identical, worktree clean). The first two commits each pass the suites they touch on their own exports (148 and 153 pytest tests, 28 and 35 page tests; `proof\history_check.txt`), so the history bisects. Every file keeps the line endings the worktree's checkout gives it (pure CRLF), and git stores the LF blobs.

## Test evidence

The whole staffer suite, one process per file (`scripts\run_suites.py`: `fec/surfaces/test_staffer_*.py`, `fec/tests/surfaces/test_staffer_*.py`, two `staffer_network` tests, every `fec/tests/surfaces/test_*.cjs`, and the known-red repin test; a file pytest collects no tests from is run as a script), on clean `git archive` exports (autocrlf off)
plus the 4 gitignored data files copied read-only from LIVE and deleted afterwards (`scripts\run_tip_and_base.sh`, `scripts\export_and_run.sh`):

| | files | passed | failed | skipped | peak memory of the process tree |
|---|---|---|---|---|---|
| `79ef9f1b7` (the v4 tip: what LIVE runs now) | 79 | 1,749 | 1 (the repin red) | 63 | 501 MB |
| the v4.1 tip `19a5c28bc` | 80 | 1,786 | 1 (the same red) | 64 | 593 MB |
| the applied tree: clean `3366a7840` + LIVE's current bytes for the 45 files of the three landings + landing_v4_1 by its own `apply_landing.py --apply` | 80 | 1,786 | 1 (the same red) | 64 | 587 MB |

`proof\test_results_79ef9f1b7_vs_tip.txt`, `proof\applied_tree_suites.txt`. The one red that is always there is the same in every run: `fec/surfaces/test_repin_staffer_live.py::VerificationDerivationTests::test_default_generation_derives_expected_default_verification` (known baseline; it fails identically at the v4 tip).
**Zero new failures against `79ef9f1b7`**: `compare_baseline.py` says "new failures: none". The tip run has the same failure as the v4 run and nothing else. The known intermittent socket abort of `test_staffer_identity_api.py` (the test's own HTTP client on this host; not this patch's) did not occur in any run this time. The files whose counts differ are the five the round changed or added: `test_staffer_left_out_staff.cjs` 27 to 33 passed (and 1 to 2 skipped in an export: the new control that reads the v4 page needs git), `test_staffer_office_covered_staff.py` 21 to 26 (41 skipped in an export, as before: the tests that read a base commit), `test_staffer_prewarm.py` 31 to 35, `test_staffer_unreachable_hint.py` 15 to 20 (6 skipped, as before), and `test_staffer_request_work_index.py`, new, 17.
Every other file has the same counts. The six tests that mention `staffer_live` without being named `test_staffer_*` (`proof\extra_tests.txt`): 287 passed, 0 failed, 2 skipped at `79ef9f1b7`, at the tip and on the applied tree.
**The applied tree equals the tip run file for file**: all 80 files have identical counts and identical failures. The applied tree runs this patch's post-images themselves, with their mixed terminators; the tip export is the pure-LF blobs.
The tip's peak is 92 MB above the v4 tip's: the largest single file is `test_staffer_unreachable_hint.py` (about 530 MB in its own process, 480 MB at v4; its new tests build nine more services and servers); every process stayed far under the 1,000 MB limit.

The skips: the exports have no `.git`, so the tests that read a base commit with `git show` skip (the same tests in the tip and applied runs). They are not skipped anywhere that matters: in the worktree (git available) the 16 files of the new, changed and neighbouring suites (`scripts\run_new_tests_3x.sh`) run **598 passed, 0 failed, 0 skipped, three times in a row** (16 files; `proof\new_tests_three_in_a_row.txt`); in the exports 548 / 0 / 50 three times in a row; and the 10 files that skip in an export run with `GIT_DIR` pointed at the shared object store (read-only) on the tip export and on the applied tree: **302 passed, 0 failed, 0 skipped on both** (`proof\git_history_subset.txt`).
`python -m fec.surfaces.test_staffer_closeness_bidirectional --ties` (20,000 tie-heavy graphs per mode, both modes): **violations 0** on the tip export and on the applied tree (`proof\ties.txt`; decimal: same route 19,478, equal-cost swap 29, same steps and lower exact cost 78, fewer steps 90, unreachable 325, MORE steps 0, WORSE exact cost 0; log: same route 19,338, equal-cost swap 355, fewer steps 13, unreachable 294, MORE steps 0, WORSE exact cost 0; the same lines on both trees, and the same as at landing_v4).
Mutation checks (`proof\mutations.txt`, `scripts\mutations.py`): 21 single edits to production code, each in a scratch copy of the tip export, each run against the tests named for it: **20 are caught** (the flag never set, a collection at every prewarm, a flag never cleared, a flag set for the router just published, an abandoned prewarm that collects; no scope for distinct, none for the Yen loop, a scope that is never closed, an index that ignores the scope, a release that does not mark the router, a finished build that is put back, a released router that stores hop rows, unstored rows that are not shared by the passes, a release that skips a fresh router; a basis that is always `payroll_or_roster`, one that is always `roster`, a page that ignores the basis; an explanation that is not the message, a note added after a reasoned one, a reason without a message still counted as reasoned). **One is an equivalent mutant**, `distinct_loop_drops_the_basis`: every pass of an office request already returns `uncovered_basis` in its own result (`ClosenessRoutes.route`), and `distinct_routes` builds each route from that result, so naming the basis in the carried fields as well changes nothing a caller can see (all 67, 26 and 13 tests of the office, hint and distinct suites still pass with it removed). The line keeps the three fields of an office answer written in one place; no test can tell it from its absence.
The first mutation run counted one mutation caught that had run no test (its `-k` matched nothing, pytest exit 5); the harness now counts only exit 1, and that mutation was re-run and is caught for real (`reason_without_message_still_reasoned`).

## The gc and rebuild evidence

All of it in `proof\evidence_gc_and_rebuild.txt` (`scripts\evidence.sh` and `scripts\rebuild_between_passes.py`), on clean exports of `79ef9f1b7` (before) and the tip (after), one process at a time under `memrun.py` with a 1,000 MB cap (none came near it: 94 to 521 MB).

**1. The collection (fix 1).** In the live panel the first prewarm of the sidecar that runs v4 reported `gc_ms` 10,145.99 on a 61.6 s prewarm: the collection at a start, with nothing to free, held every request thread for 10.1 s (`live_panel_v4\final_performance.json`).
`publish_memory.py` (the service's own swap and prewarm on a synthetic world, one process; the people index stage left out), 40,000 people and about 112,000 episodes:

| | the first prewarm (a start) | the prewarm after the swap | peak, building the second router | peak, the prewarm after the swap |
|---|---|---|---|---|
| v4 (`79ef9f1b7`) | `gc_ms` 180.07 | `gc_ms` 976.22 | 521 MB | 498 MB |
| v4.1 | **no `gc_ms`: no collection ran** | `gc_ms` 919.68 | 521 MB | 499 MB |

At 20,000 people: v4 `gc_ms` 105.95 at the start and 361.99 after the swap, peaks 311 / 299 MB; v4.1 none at the start and 533.70 after the swap (it varies between runs), peaks 310 / 299 MB. So the collection at a start is gone and the one at a publish stays, with the same memory saving.
`gc_measure.py 20000` (what one collection costs, with nothing to free, on a heap of 0.42 million tracked objects): 145 to 172 ms on both trees over three runs alternating them (346 to 370 ns per tracked object; the first evidence run read 105 ms on v4 and 153 to 181 ms on v4.1, which is run-to-run variation on this host). This round did not change what a collection costs; it removed the one that ran at a start. At about 250 to 370 ns per tracked object the live 10.1 s is the cost of some 27 to 40 million tracked objects (an inference from the per-object cost, not a measurement of the live heap).
In the suite: `test_a_prewarm_at_a_start_runs_no_collection_because_no_router_was_replaced` and `test_the_prewarm_after_a_replacement_runs_one_collection_before_its_first_build_and_a_later_one_runs_none`.

**2. The rebuild between the passes (fix 2).** The re-check's part 2 on a router that has never been released (`rebuild_between_passes.py`: a warm router per strategy, one release inside the request after its first search ran; the same answer is compared with an untouched twin):

| | builds during the request | index objects the passes used | same answer as the untouched twin |
|---|---|---|---|
| v4, distinct (3 routes, 3 index fetches) | **1** | **2** | yes |
| v4, independent | **1** | **2** | yes |
| v4, ranked and single | 0 | 1 | yes |
| v4.1, distinct, independent, ranked, single | **0** | 1 | yes |

The re-check's stress script (`stress_release.py`: 36 requests of five kinds, 6 workers on one router while a releaser empties it every 0 to 15 ms and a forgetter drops its name index, every answer compared with the twin's), peak resident set 238 MB (v4, 15 s) and 240 MB (v4.1, 40 s):
v4: 102 requests, 275 releases, 83 forgets, 0 errors, 0 mismatches, **41 requests used more than one index object** (a rebuild between their own passes: distinct 13, independent 10, avoid 18).
v4.1: 184 requests, 583 releases, 187 forgets, 0 errors, 0 mismatches, **no request used more than one index object**.
Its part 3 (a service whose old router's prewarm build is in flight while a request waits on it, a new router is published, and the new prewarm collects): the in-flight build **re-inserted into the released table on v4 (variants a and b) and does not on v4.1 (a, b and c)**; the request on the old router is answered the same way in every variant; with nothing holding the old router it is gone after the collection in variant c (both), and in variant b it is still alive while the request that holds it runs and gone one collection after (both), which is what the README now says.
(The script's own part 2 runs on the router its part 1 has been releasing, which v4.1 keeps released for good, so its "builds during the request=1" there is the one index such a request builds for all its passes, in one object; `rebuild_between_passes.py` is the same scenario on an unreleased router.)
In the suite: `test_a_release_between_the_passes_costs_no_rebuild_and_changes_no_answer[distinct|independent]` (0 builds, one index object, the twin's answer), its negative control without the scope (a pass builds again), `test_a_request_on_a_released_router_builds_one_index_for_all_its_passes_and_the_router_keeps_nothing`, `test_an_index_whose_build_finishes_after_the_release_goes_to_the_callers_waiting_on_it_and_is_not_put_back` and the short stress run.

**3. The directory-only comparison (fix 4)** (the re-check's `directory_mode.py`, extended to print the answer's basis and the line the page builds from it, by running `leftOutLine` of each tree's own `staffer-route.js` in node): the person `p1` has payroll rows and no roster entry.
v4, work_sources=directory: left out `['p1']`, no basis, line "1 of this office's current staff lacks the payroll or staffer-roster coverage this model requires and was left out."
v4.1, work_sources=directory: left out `['p1']`, basis `roster`, line **"1 of this office's current staff lacks the staffer-roster coverage this model requires and was left out."**
v4.1, work_sources=payroll_and_directory: `p1` is covered by payroll, nobody left out, basis `payroll_or_roster`, no line.

## Needs Paul

1. APPLY landing_v4_1 (the dry run against the real LIVE is clean) and the 8841 restart for its Python half, in the order stop, apply, start (see Restart). Both are Paul's calls (D-060, D-080).
2. Brain updates, for Paul to apply and commit once the patch is in (draft text; the brain is not touched by this work). `DECISIONS.md`, D-087 (cold-path speed and memory) gains: "Refined 2026-10-04 (landing_v4_1): the prewarm's one collection runs only after a router was replaced, never at a start (the live panel measured gc_ms 10,145.99 at the first prewarm, which held every request thread for 10.1 s for nothing); a released router stores nothing it builds and one search request keeps one work index for all its passes, so a publish between the passes of a distinct or independent search costs no rebuild; the old router's indexes and the new router's are not resident together only once no request is still running on the replaced router." D-086 gains: "The left-out line names the coverage the model reads: uncovered_basis is payroll_or_roster (the line says "payroll or staffer-roster") or roster for a directory-only comparison (the line says "staffer-roster")." D-085 gains: "An unreachable answer with a reason has explanation equal to message."
   `STATE.md`, the people-network lane: "landing_v4_1 (staffer_route_v4_1.patch sha256 fcb52fbdad63..., branch claude/staffer-route-v4-1-20261004, tip 19a5c28bc) is cut against LIVE's working bytes (landing_v4 applied, HEAD 3366a7840) and not applied; it waits for Paul's apply and the 8841 restart."
3. Interpretations, in one place: (a) **uncovered_basis is decided by the mode** (`work_sources == 'directory'` gives `roster`, anything else `payroll_or_roster`), not by whether the world happens to hold payroll rows: the brief said "payroll_or_roster or roster" and described the directory case; a world with no payroll rows at all in the default mode still says `payroll_or_roster`, which is what the model can use there (a test pins it). (b) For an unreachable answer that has a reason, **`explanation` is the message alone**: the note about how alternatives are found, which the page's default three distinct routes added, is not appended (the answer has no routes). (c) `release_search_state` creates the search object of a router that has none, so that router is born released; the service always has one, so this changes nothing there. (d) The request scope is opened around both multi-pass flows of `route_many` as the brief said; for the Yen loop of the other objectives (`_route_alternatives`) it covers nothing today, because those searches do not ask for the work index (a test pins where it is open). (e) A released router stays released for good (the flag is never cleared). (f) The commits carry both trailers, as every commit of this lane does: Claude Sonnet 5.5 (who wrote them) and Claude Opus 5.5 (the brief's).
4. One line of this round no test can tell from its absence: `uncovered_basis` in `distinct_routes`' carried fields (equivalent mutant, above).
5. The new test module is not registered in `fec/tests/run_tests.py` (as landing_v2's, landing_v3_ids's and landing_v4's were not).
6. Whether and how the applied files are committed in LIVE (D-060 leaves the working tree as it is; the reconcile lane commits). After the apply the 10 edited files show ` M` and the new test `??`, since 3366a7840 already holds landing_v2, landing_v3_ids and landing_v4. The branch is in the shared repository and the repository's post-commit hook has copied it to the local `mirror` remote (`C:\Users\pgoff\GitMirrors\melange-systems.git` holds `claude/staffer-route-v4-1-20261004` at `19a5c28bcf98f13e346ea27e4c7ca56bd1d9680b`); nothing was pushed to `origin` (GitHub).
7. This directory is in the session scratchpad. Copy it somewhere durable if it must outlive the session (the audit packet `audits/staffer_route_latency_20261004/` that 3366a7840 committed holds landing_v2, landing_v3_ids and landing_v4, not this one). `SHA256SUMS.txt` lists every file in it (`python scripts\make_sums.py --check`).
8. The running sidecar's memory: its working set was 1,888 MB at 06:09 (started 03:17:41). This work never touched it, and its size was not examined here; the 10.1 s stall at its next start is what the first fix removes.
