# Staffer people-network landing v4: unreachable hint, covered-staff office search, cold-path speed, committee-name search (re-cut 2026-10-03 after the fix round, NOT applied)

One patch set, cut with `fec/tools/live_patch.py` (D-060) against the bytes LIVE holds now, with `..\landing_v2\` (applied 14:59:02 on 2026-10-03) and `..\landing_v3_ids\` (applied 16:24:42) already in LIVE. It carries three branches that were
built on the content LIVE runs, merged and tested together: the unreachable hint with the office covered-staff search (D-085, D-086), the cold-path speed round (D-087) and the restored committee-name search (the part of D-083 still pending).
No file in LIVE's working tree was written, applied, staged or committed by the cut or by any proof, and the sidecar on 127.0.0.1:8841 (PID 35320) was not touched (no script here connects to it; the tests that start servers use ephemeral ports).
It is a third patch, not a replacement: apply it on top of landing_v2 and landing_v3_ids (the apply script refuses otherwise).
**This is the second cut.** The first one (tip `5d4a9bd0a`, patch sha256 `d91cc386be74...`) is in `..\landing_v4_superseded_20261003-2257\` with a SUPERSEDED.txt and must not be applied: a verifier found two sentences in it that claimed more than the code
establishes, a loose test assertion and two memory leaks, and the fix round (section "The fix round" below) replaced it.

| | |
|---|---|
| Branch | `claude/staffer-route-v4-20261003`, worktree `C:\Users\pgoff\Melange-wt\route-core`, tip `79ef9f1b7440bcee21c7f7c677a93263d9fcc04a` |
| Built from | `f23a40aee` (`claude/staffer-search-ids-followup-20261003`, exactly the content LIVE holds after the two landings) plus the three branches below, merged by `2303ef79b` and `7bf774055` (no conflicts), plus three fix commits `20aefec50`, `fb3f874c2`, `5d4a9bd0a`, plus the four commits of the fix round `453718ddc`, `7ce88cc52`, `0cb0593b1`, `79ef9f1b7` |
| Requires | `..\landing_v2\` and `..\landing_v3_ids\` applied to LIVE first. They are: the dry run below is clean |
| Base = LIVE main | `3248a6a02e42bd23665995e69dc649ac926aab95` (LIVE HEAD unchanged at the cut and at the last proof) |
| Patch | `staffer_route_v4.patch`, 374,611 bytes, sha256 `35ec5a23470d2107179018170eceeb29872e2cd65b51dc57daee40b6ce54499a` (+4,879 / -54 lines) |
| Files | 26: 15 edited in place, 11 new (all tests); the same 26 as the first cut. List, pre- and post-image hashes and terminator profiles in MANIFEST.txt |
| Effect on LIVE's `git status` | 17 ` M` entries (the 14 the two landings made, plus `closeness_math.py`, `staffer_work_sources.py` and `test_staffer_route_models.cjs`) and 28 `??` (the 17 the two landings made, plus the 11 new files); committing is a separate decision |
| Needs a restart | **The Python half, yes; the page half, no.** See "Restart" below |

## What it contains

Three branches, each descended from `f23a40aee`:

| Branch | Tip | Ruling | What it does |
|---|---|---|---|
| `claude/staffer-unreachable-hint-20261003` | `1c66a85ba` (2 commits: `a9db5fd5f`, `1c66a85ba`) | D-085, D-086 | A Staffer (work_time) search that finds no route answers `unreachable` with an `unreachable_reason`, a one-sentence `message` and `suggested_objective` `evidence_cost` (so does `insufficient_work_coverage`); the page shows the message and one **Search Ecosystem** button that reruns the same search. An office search routes to the office's covered staff and reports the rest (`uncovered_staff_count`, `uncovered_staff_ids`); it fails as `insufficient_work_coverage` only when the origin is uncovered or none of the staff is. The page says so in one line. |
| `claude/staffer-coldpath-20261003` | `c6c6c1c58` (6 commits) | D-087 | Cached per-search lookups (payroll people kept on the work index, same-name contacts indexed once per nodes mapping), a background prewarm of the work index and the people index after every router publish (single flight, `metrics.prewarm` on `/api/staffer-performance`, `MELANGE_STAFFER_PREWARM=0` turns it off), and zero-overlap pairs skipped before pair arithmetic (`pair_row`, `overlaps`; the result gains `pairs_scored`). No answer, cost or tie rule changes; rows are bit-identical to the old ones (`test_staffer_row_equality.py`, 151 tests). Rows are not pre-scored in bulk (D-087). |
| `claude/staffer-search-committee-names-20261003` | `6a198d600` (1 commit) | D-083 (committee-name part) | The name inside a committee id (`container:office:senate:AGRICULTURE, NUTRITION & FORESTRY`) is searchable again in the map's query filter (substring) and the record browser (word prefix); the part before it never is; whole ids still match whole. |

The integration adds three commits of its own on top of the two merges. The merges were conflict-free (`git merge-tree` before each one, then the merge itself); the staffer_live README was edited by all three branches in different paragraphs, so every sentence of the three is
in the file, each where its own branch put it (`proof\merge_and_commits.txt` lists them).

- `20aefec50` **test edits that the new counter needs** (not weakenings): `dump()` in `test_staffer_office_covered_staff.py` and `without_timing` in `test_staffer_unreachable_hint.py` drop `pairs_scored` as they drop `search_elapsed_ms`;
  `work_of` counts the pairs priced through both `ExposureIndex.pair` and `ExposureIndex.pair_row`; `test_the_checks_build_no_rows_the_search_did_not_and_price_no_pairs` asserts the rows built are exactly the base commit's and the pairs priced are never more
  (`new_pairs <= old_pairs`) where it asserted equality, because the cold-path change skips two people who never stood in one workplace together before it prices them. Without the edits 35 of the two files' 66 tests fail on the merged code, with them all 66 pass (`proof\test_edits_negative_control.txt`).
- `fb3f874c2` **flaky test**: `test_a_lost_cheapest_route_reaches_the_page_as_a_search_error_over_http` (`test_staffer_route_jobs.py`) asserted that an async search's first answer is queued or searching, and the worker can finish first (0.4 to 0.9 percent of runs). It now accepts queued, searching or
  search_error for that first answer, then polls until the search is no longer queued or searching and asserts `search_error` with the same error text, id and status as before; everything else it checks is unchanged. With the race forced (a pytest plugin makes the worker always win) the old test fails
  at once and the new one passes (`proof\flaky_test_probe.txt`).
- `5d4a9bd0a` **UI tweak**: an office answer that is `insufficient_work_coverage` because the ORIGIN is uncovered no longer shows "N of this office's current staff ... left out", because no search ran. `leftOutLine` in `staffer-route.js` returns nothing for an `insufficient_work_coverage`
  answer whose `unavailable_person_ids` contain its `origin`; every other answer shows the line exactly as before (found, unreachable, a coverage answer where the origin is covered and none of the staff is, and any answer that does not name the origin among the unavailable people). The server still counts the staff.
  One README sentence says so. `test_staffer_left_out_staff.cjs` gains four scenarios and five deliberate page bugs that must each be caught (27 tests); `test_staffer_office_covered_staff.py` gains a test that pins `origin` and `unavailable_person_ids` on the real producer, through the service and the HTTP handler.

## The fix round (after the verifier's findings on the first cut; four commits on top of `5d4a9bd0a`)

Every user-facing sentence was re-read against the code. Five findings, five fixes (`proof\fix_round.txt` has the commits, the diffstat, the mutation checks and the memory table):

1. **The left-out line (MEDIUM, `453718ddc`).** It said the staff an office search left out "have no work records this model uses". Left out means uncovered: no payroll row and not in the operational staffer roster (`allowed()` in `ClosenessRoutes.route`), and a staffer with a dated
   directory episode at the office can be one (the verifier's scenario A: the answer is `found`, `uncovered_staff_ids` holds the person, and the index has their directory cells at the office). The line now reads
   **"N of this office's current staff lack the payroll or staffer-roster coverage this model requires and were left out."** and, for one person, **"1 of this office's current staff lacks the payroll or staffer-roster coverage this model requires and was left out."**
   (`staffer-route.js`, the staffer_live README sentence and the code comment say the same). `test_staffer_left_out_staff.cjs`: 28 tests (was 27), thirteen deliberate page bugs (was twelve; the new one puts the old wording back and is caught).
2. **`office_without_work_records` (LOW, `453718ddc`).** The reason is decided on the staff the search used (covered, and not avoided: `route_many` drops avoided staff from the targets before the search), but its sentence said "none of this office's current staff have dated employment at this office".
   When some staff were left out or avoided that says more than the search saw. In that case it now says **"No Staffer route: none of the staff this search could use have dated employment at this office in the records this model uses."**
   (`SEARCHED_STAFF_MESSAGES`); with nobody left out or avoided the sentence is the one it was. Avoided staff reach the closeness search through a new internal option `_avoided_targets` (`route_many` fills it for a Staffer office request, `distinct_routes` hands it on with the other
   options; the HTTP handler does not accept it); a person avoided who is not on the staff changes nothing. Tests in `test_staffer_office_covered_staff.py`: the verifier's scenario B, avoided staff through `avoid_people` and `_excluded_nodes`, an avoided outsider, every strategy and route count, the service and the HTTP handler, and every case of a small
   world (16 coverage patterns x every named set x every avoided set, with and without an outsider) against an oracle that reads the data, with a negative control.
3. **The pair-count assertion (LOW, `7ce88cc52`).** `new_pairs <= old_pairs` is now exact: `work_of(..., overlapping_only=True)` counts only the base commit's priced pairs whose people overlapped (`ExposureIndex.overlaps`) and the tip's count must equal it, with the same rows. Negative controls: an explanation that prices one more pair
   fails it, and in a world where the base prices five pairs of which two cannot overlap the explanation with one extra pair passes the old assertion and fails the exact one.
4. **The name index outlived its mapping (LOW, `0cb0593b1`).** `_contact_groups` holds the nodes mapping it was built from; when the service installs a new mapping on the same router (the branch after a label change) it now calls `AdvocacyRouter.forget_contact_groups()`, so the replaced mapping is freed.
   A weak-reference test shows it freed with the drop and held without it.
5. **Memory (D-087, `0cb0593b1` and `79ef9f1b7`).** After every router publish (both sites: the refresh that builds a router, and the identity rebuild) the service calls `AdvocacyRouter.release_search_state()` on the router it replaced: `ClosenessRoutes.release()` empties its work indexes and hop-row caches and the name index is dropped.
   The prewarm runs one `gc.collect()` before its first build (reported as `gc_ms` under `metrics.prewarm`; none in a prewarm that is abandoned before it builds). A search still running keeps what it holds; one that asks afterwards builds again; no answer changes (a service whose publish releases is compared with one whose does not, over five requests).
   `ClosenessRoutes.route` no longer asks for its index a second time after the first (the second call returned the same object, or would have built another if a release had emptied the table in between). The router and its search object still refer to each other; the release does not touch that, because breaking it would make a
   late request on the replaced router fail and `test_a_router_swap_during_the_prewarm_discards_it` pins that a build running when the router was replaced finishes onto its own router. The router shell that the cycle holds is what the collection frees. Weak-reference tests: the replaced router's index, row cache and name index are gone right after the publish;
   the router itself, its index and its rows are gone before the next prewarm's work index build starts; with neither the release nor the collection they are still there (negative control).
   **Measured** (`proof\fix_round.txt`, section 5; synthetic world, `scripts\publish_memory.py`, one process under a 1,000 MB cap): on a 40,000-person world (about 112,000 episodes, 600 offices; two runs each) the peak resident set of the process over the publish and its prewarm was **588 MB before and 522 MB after** (-66 MB, -11%); the prewarm that follows the swap, on its own, peaked at 587-588 MB before and 499 MB after (-88 to -89 MB, -15%), with 6.2 million live allocated blocks at that peak before and 5.3 million after, and the process held 495-497 MB when the prewarm ended before and 459-461 MB after.
   On a 20,000-person world: 380 MB before, 312-313 MB after (the prewarm alone 375-377 MB before, 300 MB after). Every run stayed far under the 1,000 MB cap (the largest, 588 MB). Building the second router while the first still serves (522-523 MB at 40,000 people) is the same before and after and sets the after peak: the release comes after the swap, so it cannot lower that phase. The people-index stage of the prewarm is not in these runs.
   The one collection took 0.42-0.44 s (20,000 people) and 0.84-0.85 s (40,000) there.

Intended changes of existing expectations (the tests as they were at `5d4a9bd0a` run against the new code fail exactly here, and nowhere else; `proof\fix_round.txt`, section 2): 11 of 163 tests fail, ten in `test_staffer_left_out_staff.cjs` (they assert the old left-out sentence) and `test_an_unreachable_reason_is_judged_on_the_covered_staff[office_without_work_records]` in `test_staffer_office_covered_staff.py` (it asserts the old sentence for an office judged with staff left out); the other 152 pass unchanged, including the old pair-count assertion. Items 6 to 8 of "Test evidence" list them.

Files (the change is `+added / -removed` lines of the patch):

| File | Change | What |
|---|---|---|
| `fec/staffer_network/closeness_math.py` | +64 | `ExposureIndex.overlaps` and `pair_row` (cold path) |
| `fec/surfaces/staffer_closeness_routes.py` | +209 / -14 | unreachable reason, message and suggested objective (and the sentence for an office judged on the staff the search could use); the office covered-staff rule; the single-flight work index; `pairs_scored`; kept payroll people; `release()`; the module docstring |
| `fec/surfaces/staffer_distinct_routes.py` | +36 / -3 | distinct and independent passes keep the dropped staff out; the same-name contact index |
| `fec/surfaces/staffer_live_service.py` | +147 / -3 | the prewarm after every router publish, `metrics.prewarm` (with `gc_ms`), the router's closeness search created before it is published, the release of the replaced router and the name index dropped with a replaced nodes mapping |
| `fec/surfaces/staffer_routing.py` | +47 / -6 | the closeness search created under a lock, once per router; `release_search_state`, `forget_contact_groups`; the internal option `_avoided_targets` |
| `fec/surfaces/staffer_work_sources.py` | +10 | `payroll_people` kept on the work index |
| `fec/surfaces/staffer_live/staffer-route.js` | +20 / -5 | the Ecosystem offer and the message, the left-out line (and not for an uncovered origin) |
| `fec/surfaces/staffer_live/staffer-live.js`, `staffer-inventory-worker.js` | +7 / -4, +16 / -1 | committee names in the map's query filter and the record browser |
| `fec/surfaces/staffer_live/README.md` | +4 / -2 | the sentences of all three branches, of the UI tweak and of the fix round |
| `fec/surfaces/test_staffer_closeness_bidirectional.py` | +188 / -12 | `--coldpath` harness, `pair_row` in its test doubles and counters, `pairs_scored` in its comparisons |
| `fec/tests/surfaces/test_staffer_route_jobs.py` | +10 / -2 | the flaky test |
| `fec/tests/surfaces/test_staffer_route_models.cjs` | +2 / -2 | the Ecosystem button now reads `Search Ecosystem` (expectation change of the hint branch, D-085) |
| `test_staffer_inventory_worker_codes.cjs`, `test_staffer_live_query_ids.cjs` | +2, +2 | a pointer comment each |
| 11 new test files | +4,115 | `staffer_unreachable_hint_contract.cjs`, `test_staffer_unreachable_hint.{py,cjs}`, `test_staffer_office_covered_staff.py`, `test_staffer_left_out_staff.cjs`, `test_staffer_contact_group.py`, `test_staffer_payroll_people.py`, `test_staffer_prewarm.py`, `test_staffer_row_equality.py`, `test_staffer_inventory_worker_committee_names.cjs`, `test_staffer_live_query_committee_names.cjs` |

No data file, schema or dial changes. The new test modules are not registered in `fec/tests/run_tests.py`, as landing_v2's and landing_v3_ids's were not.

## Restart

- **Page half, no restart.** `staffer-route.js`, `staffer-live.js`, `staffer-inventory-worker.js` and the README are static: the sidecar reads them from disk on every request (`send_asset`, `Cache-Control: no-store`), so they are served on the next page load. New page code in front of the
  old Python still works: an old answer has no `suggested_objective` (the button falls back to `evidence_cost`), no reason or message (the page keeps its own sentence) and no `uncovered_staff_count` (no line).
- **Python half, yes.** `closeness_math.py`, `staffer_closeness_routes.py`, `staffer_distinct_routes.py`, `staffer_live_service.py`, `staffer_routing.py` and `staffer_work_sources.py` are loaded by the running sidecar (PID 35320, started 14:59:15), which keeps what it imported. The unreachable reason and message,
  the covered-staff office rule and its counts, the prewarm, the single-flight index and the zero-overlap skip take effect only when 8841 restarts. Restarting is Paul's call (D-080: started once, the scheduled task stays disabled).
- **Order: stop 8841, apply, start**, as for landing_v2 on 2026-10-03 (stopped 14:58:58, applied 14:59:02, started 14:59:13, Ready and PASS at 15:02:36). Do not apply under a running sidecar: `staffer_routing.py` imports `staffer_closeness_routes`, `staffer_distinct_routes` and (through them) `closeness_math` and
  `staffer_work_sources` lazily, at the first request that needs them, so a sidecar that has not served a Staffer route since its start would load the new files next to its old `staffer_live_service.py` and `staffer_routing.py`. The sidecar's current command line is in `proof\live_untouched.txt`.
- After the start, the prewarm builds the work index (about forty seconds on the live records, per its commit) and then the people index (about thirteen), once per published router, in the background; `GET /api/staffer-performance` shows `metrics.prewarm`. D-087's constraint is memory (host free RAM fell to 0.65 GB during the 2026-10-03 panel; 4.8 GB were free when this cut began). In the first cut the old router's indexes were still held while the prewarm of a rebuilt router ran; now the service
  lets go of the replaced router's work indexes, hop-row caches and name index at the publish, and the prewarm runs one garbage collection before its first build (`gc_ms` under `metrics.prewarm`), so the old indexes and the new ones are not held together (measurements in "The fix round").
  **That collection holds the interpreter while it runs**, so every request thread waits for it: it took 0.4 s in a 20,000-person synthetic world and 0.85 s in a 40,000-person one (measurements in "The fix round") and grows with the number of live objects, so on the live heap it will be longer. It happens once per published router (and once at the start), in the prewarm thread, before the 40-second build; `gc_ms` on
  `GET /api/staffer-performance` after the first publish tells Paul the real figure. `MELANGE_STAFFER_PREWARM=0` before the start turns the prewarm and that collection off (the release at a publish stays).

## Apply (Paul's step)

Preconditions are enforced twice, by `apply_landing.py`'s pre-flight and again by `apply_to()`: every file the patch edits must hash to its pre-image in MANIFEST.txt (landing_v3_ids's or landing_v2's post-image where one of them touches the file, LIVE's own file otherwise, which is what LIVE holds now) and none of the 11 new files may exist.
A tree that does not hold them gets the dry run's own refusal, with the files named, and nothing is written.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'      # the scripts import fec/tools/live_patch.py from LIVE; write no bytecode there

# 0. optional read-only report: HEAD, each file's hash against its pre-image, the dry run, the raw git check, the rollback plan
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4\scripts\dry_run_live.py"

# 1. dry run: pre-image check, then git apply --check; writes nothing
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4\scripts\apply_landing.py"

# 2. apply to LIVE (live_patch.apply_to: refuses a moved target, checks every post-image sha256, puts the bytes back on any failure)
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4\scripts\apply_landing.py" --apply
```

The same patch with plain git, without the hash gates (D-060's command):

```powershell
git -C "C:\Users\pgoff\OneDrive\Desktop\Melange Systems" -c core.autocrlf=false -c core.safecrlf=false apply "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v4\staffer_route_v4.patch"
```

Never use `--index` or `--cached` (LIVE blobs are pure LF), never a plain `git apply` without `-c core.autocrlf=false`, and do not EOL-normalise LIVE (D-060, DE-041).

## Rollback

```powershell
python "...\landing_v4\scripts\rollback_landing.py"                # plan: writes nothing
python "...\landing_v4\scripts\rollback_landing.py" --rollback     # restores the 15 saved pre-images byte for byte, removes the 11 new files
```

A file edited after the apply stops the rollback and nothing changes (`--force` overrides). The pre-images in `pre_images\` are LIVE's bytes as they were (landing_v3_ids's and landing_v2's post-images where those touch the file), so this puts LIVE back to "landing_v2 and landing_v3_ids applied", not to before them. Roll back in reverse
order: landing_v3_ids's own rollback refuses while this patch is on. For a tree whose files are still exactly the post-images, the other way back is `git -C "<LIVE>" -c core.autocrlf=false -c core.safecrlf=false apply -R "...\landing_v4\staffer_route_v4.patch"`.
Rolling back the Python half needs the same stop, roll back, start sequence as the apply.

Node tests in LIVE after the apply (node only for these; the negative controls read `a9db5fd5f` and `f23a40aee` from LIVE's own repository, which holds them, so they run there too):

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
node --test fec/tests/surfaces/test_staffer_left_out_staff.cjs fec/tests/surfaces/test_staffer_unreachable_hint.cjs fec/tests/surfaces/test_staffer_route_models.cjs
node --test fec/tests/surfaces/test_staffer_live_query_committee_names.cjs fec/tests/surfaces/test_staffer_inventory_worker_committee_names.cjs fec/tests/surfaces/test_staffer_live_query_ids.cjs fec/tests/surfaces/test_staffer_inventory_worker_codes.cjs
```

## How it was cut (D-060, DE-040, DE-041) and proved

`scripts\cut_landing.py` (landing_v2's and landing_v3_ids's cutter; this cut changes where the pre-images come from and the base). Bytes end to end, lines split on LF only (`live_patch.split_lines`). The pre-image of every edited file is LIVE's own working file as it is now, read in binary and read-only; for a file either earlier landing
touched the cut also requires those bytes to be that landing's post-image (its summary's hash, and byte for byte against its `post_images`) and stops otherwise; it stops too if LIVE's HEAD is not `3248a6a02` or if a new file already exists in LIVE. For each edited file the pre-image must equal the base blob (`f23a40aee`) line for line (it did, for all 15).
Every changed region of base to tip is spliced into the pre-image's own lines; its anchor (unchanged context on both sides plus the old lines) must hit exactly once; inserted lines carry the file's majority terminator; untouched lines are never rewritten; after the last splice the content equals the tip blob line for line.
The 11 new files carry the exact tip bytes (pure LF in the blobs). The patch is stored here, outside every repository (DE-040). No string replacement is used to cut. `prove()` passed at the cut (`proof\cut_output.txt`).
The terminator profiles that matter, from MANIFEST.txt: `staffer_closeness_routes.py` is MIXED in LIVE (772 CRLF, 6 bare LF; after: 968 and 5, one bare-LF line sat inside a changed region and is replaced by a majority-terminator line), `staffer-inventory-worker.js` MIXED (70 and 27; after 85 and 27), `staffer-live.js` MIXED (153 and 4; after 156 and 4),
`staffer_routing.py` MIXED (650 and 1; after 691 and 1), `test_staffer_route_models.cjs` MIXED (124 and 25; after 124 and 25), `README.md`, `staffer-route.js` and `staffer_live_service.py` PURE_CRLF and stay so, the other edited files PURE_LF and stay so.

Proofs, all run on the cut as it is (`proof\`):

1. **Main proof**, `scripts\prove_landing.py` (`proof\proof_results.txt`): **278 checks passed, 0 failed.**
   - The patch holds exactly the files that differ between `f23a40aee` and the tip (26: 11 added, 15 modified, no deletion or rename). Each pre-image is LIVE's bytes now, byte for byte, and equals the post-image of the last earlier landing that touched the file (checked against its summary and its `post_images`).
   - Scratch tree of the pre-images, `apply_to()` there, then `live_patch.py drift` of every post-image against the branch tip's file in the worktree: **3 IDENTICAL_BYTES, 23 EOL_ONLY, 0 CONTENT.** Each EOL_ONLY file has the same content as the tip blob line for line and only terminators differ: an edited file keeps its own terminators, a new file carries the
     blob's LF, and the worktree holds git-checkout CRLF (explained file by file in the proof). Against the tip's git blob: 18 IDENTICAL_BYTES (every new file among them), 8 EOL_ONLY, 0 CONTENT.
   - Terminator audit: with lines aligned by the base-to-tip diff, every untouched line is byte-identical (terminator included) between pre-image and post-image in all 15 edited files, every inserted line carries the majority terminator, no lone CR appears, bare-LF counts do not grow in the CRLF-majority files.
   - Against LIVE itself (read-only): the dry run passes with rc=0 (all 26 files at their pre-image hashes, 15 equal, 11 absent as they should be), raw `git -c core.autocrlf=false apply --check` passes, LIVE HEAD is `3248a6a02`, all 31 files either earlier landing touched hold the post-image of the last landing that touched them
     (**LIVE is unmoved from the landing_v3_ids post-images**), the three files only v4 edits hold this patch's pre-images, none of the new paths exists or is tracked.
   - Both rollbacks (`git apply -R`, and the saved pre-images) restore the scratch tree byte for byte and remove the new files.
   - Every post-image JavaScript file passes `node --check` (11 files) and every Python file compiles (14).
2. **Operator scripts**, `scripts\prove_scripts.py` (`proof\script_proofs.txt`): ALL PASS (20 checks), on scratch trees: refused on what LIVE held before landing_v3_ids (dry run and `--apply`, nothing written), refused on a tree with one moved target (nothing written, the other files included), dry run, `--apply`, a second `--apply` refused,
   rollback plan, rollback refused after a later edit, rollback, a second rollback a no-op.
3. **Order**, `scripts\prove_chain.py` (`proof\chain_proof.txt`): ALL PASS (29 checks), with all three patch sets' real scripts on a scratch tree built from LIVE's own pre-images: v4 and landing_v3_ids refused before landing_v2, v4 refused before landing_v3_ids, landing_v2, landing_v3_ids and v4 applied in order (45 watched paths
   checked byte for byte at every step; v4 changed exactly its 26 files), landing_v3_ids's and landing_v2's rollbacks refused while v4 is on, then all three rolled back in reverse to LIVE-as-it-was.
4. **The applied tree against the tip**, `scripts\compare_trees.py` (`proof\applied_tree_vs_tip.txt`): the tree LIVE will hold after the apply (clean `git archive 3248a6a02 fec`, LIVE's current bytes for the 34 patched files, `apply_landing.py --apply`) against the clean export of the tip, all 1,732 files the tip tracks under `fec/`: **1,719 IDENTICAL_BYTES, 13 EOL_ONLY, 0 CONTENT, none missing.**
5. **The dry run against the real LIVE tree**, read-only, `scripts\dry_run_live.py` (`proof\dry_run_against_live.txt`): rc=0 as above, and the rollback plan reports every edited file "already original" and every new file "already absent".

LIVE was fingerprinted read-only (`scripts\live_fingerprint.py`: HEAD, the full `git status --porcelain -uall` text, and path, size and mtime of the 885 files under `fec/surfaces`, `fec/tests/surfaces` and `fec/tools`) before any work of the re-cut (22:56), midway (00:08) and after the last proof (00:16), and the three are identical (and equal to the three of the first cut): `proof\live_untouched.txt` (which also records the sidecar: the same PID 35320 listening on 8841 throughout).

The fix round's own scripts are in `scripts\` beside the cutter and the proofs: `run_tip_and_bases.sh` and `driver2.sh` (the suite, applied-tree, git-history, three-in-a-row, `--ties`, old-tests and memory runs), `old_tests_on_new_code.sh`, `publish_memory.py` with `run_memory.sh` and `memrun.py`, `mutations.py`, `flake_identity_api.sh` and `build_fix_round_proof.py`.

## Test evidence

The whole staffer suite, one process per file (`scripts\run_suites.py`: `fec/surfaces/test_staffer_*.py`, `fec/tests/surfaces/test_staffer_*.py`, two `staffer_network` tests, every `fec/tests/surfaces/test_*.cjs`, and the known-red repin test; a file pytest collects no tests from is run as a script), on clean `git archive` exports (autocrlf off)
plus the 4 gitignored data files copied read-only from LIVE and deleted afterwards (`scripts\run_tip_and_bases.sh`):

| | files | passed | failed | skipped | peak memory of the process tree |
|---|---|---|---|---|---|
| `f23a40aee` (what LIVE runs now) | 69 | 1,414 | 2 (the repin red and an intermittent test, see below) | 10 | 420 MB |
| `5d4a9bd0a` (the first cut's tip: the baseline of the fix round) | 79 | 1,722 | 1 | 61 | 501 MB |
| the v4 tip `79ef9f1b7` | 79 | 1,749 | 1 | 63 | 501 MB |
| the applied tree: clean `3248a6a02` + LIVE's current bytes for the 34 patched files + landing_v4 by its own `apply_landing.py --apply` | 79 | 1,749 | 2 (the same two reds) | 63 | 501 MB |

`proof\test_results_5d4a9bd0a_vs_tip.txt`, `proof\test_results_f23a40aee_vs_tip.txt`, `proof\applied_tree_suites.txt`. The one red that is always there is the same in every run: `fec/surfaces/test_repin_staffer_live.py::VerificationDerivationTests::test_default_generation_derives_expected_default_verification` (known baseline; fails identically at `722a55ba7`, `86631c454`, `f23a40aee` and `5d4a9bd0a`).
**Zero new failures against `5d4a9bd0a`.** The tip run has the same failure as the `5d4a9bd0a` run and nothing else; the only files whose counts differ are the five the fix round changed (passed 9 to 12 in `test_staffer_contact_group.py`, 26 to 27 in `test_staffer_left_out_staff.cjs`, 7 to 21 in `test_staffer_office_covered_staff.py`, 22 to 31 in `test_staffer_prewarm.py`; `test_staffer_unreachable_hint.py` 15 to 15 passed and 4 to 6 skipped, the two new tests needing git history).
Against `f23a40aee` the tip has 10 new files (all pass) and one file whose count changed, `test_staffer_closeness_bidirectional.py`, 57 to 58 (the `--coldpath` harness smoke test); every other file has the same counts apart from the flaky one below.
**The applied tree equals the tip run file for file** apart from the same flaky file: all 79 files have identical counts and identical failures. The applied tree runs this patch's post-images themselves, with their mixed terminators; the tip export is the pure-LF blobs.

**One intermittent test, not this patch's.** `fec/tests/surfaces/test_staffer_identity_api.py` failed one test in this session's `f23a40aee` run and one in the applied-tree run, and passed in the tip and `5d4a9bd0a` runs. It is the test's own HTTP client getting WinError 10053 while it reads the answer to a POST the handler rejects before reading the body
(`fec/surfaces/staffer_live_server.py`, which no patch set here edits). Run 20 times in each tree (`scripts\flake_identity_api.sh`, `proof\flake_identity_api.txt`) it fails in 0 of 20 at `f23a40aee`, 2 of 20 at `5d4a9bd0a`, 3 of 20 at the tip and 6 of 20 in the applied tree, with the names of a few tests of that file each time; the earlier session's baseline had it green.

The skips: the exports have no `.git`, so the tests that read a base commit with `git show` skip (53 more than the baseline's 10; they are the same tests in the tip and applied runs). They are not skipped anywhere that matters: in the worktree (git available) the 16 new and changed test files run **588 passed, 0 failed, 0 skipped, three times in a row**
(`proof\new_tests_three_in_a_row.txt`; 559 before the fix round, +29 tests); in the exports 531 / 0 / 57 three times in a row; and the 8 files that skip in an export run with `GIT_DIR` pointed at the shared object store (read-only) on the tip export and on the applied tree: **233 passed, 0 skipped on both** (`proof\git_history_subset.txt`).
`python -m fec.surfaces.test_staffer_closeness_bidirectional --ties` (20,000 tie-heavy graphs per mode, both modes): **violations 0** on the tip export and on the applied tree (`proof\ties.txt`). The six tests that mention `staffer_live` without being named `test_staffer_*` (`proof\extra_tests.txt`): 287 passed, 0 failed, 2 skipped at `f23a40aee`, at `5d4a9bd0a`, at the tip and on the applied tree.
Mutation checks of the fix round (`proof\fix_round.txt`, section 4): 18 single edits to production code, each caught by the tests named for it.

Intended expectation changes against `f23a40aee` (no test that passed at `f23a40aee` fails at the tip; these are the expectations that moved on purpose):

1. `test_staffer_route_models.cjs`, two assertions: the Ecosystem button after an unreachable or insufficient-coverage answer reads `Search Ecosystem`, not `Search Ecosystem routes` (D-085; the hint branch's own commit says so).
2. `test_staffer_closeness_bidirectional.py`: `pairs_scored` joins the counters its result comparisons drop, `CostedIndex` fixes `pair_row` costs as well as `pair`, the benchmark counts both, and `--coldpath` plus its smoke test are added (the cold-path branch).
3. `test_staffer_office_covered_staff.py` and `test_staffer_unreachable_hint.py` (new files of the hint branch, edited here): `pairs_scored` is dropped from the comparisons with the base commit and the pairs-priced check counts both pair functions (commit `20aefec50`, above); the fix round then made that check exact again (`7ce88cc52`).
4. `test_staffer_route_jobs.py`: the flaky test (commit `fb3f874c2`, above).
5. `test_staffer_inventory_worker_codes.cjs`, `test_staffer_live_query_ids.cjs`: a pointer comment each; their committee ids are not of the `container:office:<chamber>:<name>` shape, so nothing else moves.

Intended expectation changes of the fix round, against `5d4a9bd0a` (the five changed test files as they were at `5d4a9bd0a`, run against the new code, `proof\fix_round.txt` section 2: **11 of 163 tests fail, every one of them asserts a sentence the round changed on purpose**):

6. `test_staffer_left_out_staff.cjs`: 10 tests assert the old left-out line ("have no work records this model uses" / "has no work records ..."): the plural line, the singular line, the line with an unreachable answer and with a coverage answer, one line per route, the three scenarios in which the line stays, the positive control that runs all scenarios again, and the old `"have"` negative control.
   They now expect "N of this office's current staff lack the payroll or staffer-roster coverage this model requires and were left out." and the singular "1 of this office's current staff lacks ... and was left out."
7. `test_staffer_office_covered_staff.py::test_an_unreachable_reason_is_judged_on_the_covered_staff[office_without_work_records]` (and the same expectation in the random-world comparison with the base commit) expects the sentence for staff left out or avoided, "No Staffer route: none of the staff this search could use have dated employment at this office in the records this model uses."
8. The pair-count assertion of `test_staffer_unreachable_hint.py` is stricter (equality with the base commit's pairs between people who overlapped); the old version still passes against the new code, since the new code prices exactly those pairs.
   No other test changed its expectation: the other 152 tests of those files (the five the round changed and the page suite of the hint, `test_staffer_unreachable_hint.cjs`) as they were at `5d4a9bd0a` pass against the new code.

## Needs Paul

1. APPLY landing_v4 (the dry run against the real LIVE is clean) and the 8841 restart for its Python half, in the order stop, apply, start (see Restart). Both are Paul's calls (D-060, D-080).
2. Brain updates, for Paul to apply and commit once the patch is in (draft text; the brain is not touched by this work). `DECISIONS.md`: D-083's Outcome ends "committee-name restoration PENDING the next landing" and becomes "committee-name restoration LANDED <apply date> (landing_v4)"; D-085, D-086 and D-087 each end
   `Outcome: PENDING the next landing.` and become `Outcome: LANDED <apply date> (landing_v4); the Python half takes effect at the 8841 restart.` The UI tweak refines D-086, which could carry one more sentence in its Decision: "When the answer is insufficient_work_coverage because the origin is the uncovered person, the page does not say that staff were left out (no search ran); the server still counts them."
   The fix round refines D-085/D-086 in two sentences (the page's left-out line now names the coverage the model requires, and the no-work-records message speaks of "the staff this search could use" when staff were left out or avoided) and D-087 (a publish releases the replaced router's work state and the prewarm collects once; the collection stalls requests for `gc_ms`).
   `STATE.md`, the people-network lane: "landing_v4 (staffer_route_v4.patch sha256 35ec5a23470d..., branch claude/staffer-route-v4-20261003, tip 79ef9f1b7) is cut against LIVE 3248a6a02 on top of landing_v2 and landing_v3_ids and not applied; it waits for Paul's apply and the 8841 restart. It replaces the first cut (tip 5d4a9bd0a, sha256 d91cc386be74...), which is in landing_v4_superseded_20261003-2257."
3. Interpretation, one place: "the origin is uncovered" is read from the answer (`unavailable_person_ids` contains `origin`), which is what the producer sends for exactly that case (pinned in `test_staffer_office_covered_staff.py`). A coverage answer that does not say so keeps the line. I also changed one README sentence and added the producer-side test; the brief named the page and a node test only.
4. The merges did not conflict, README included, so no sentence had to be ordered by hand; the README paragraphs are where each branch put them.
   Fix-round interpretations, in one place: (a) "avoided" is read as the office's named staff that `route_many` drops because they are in `_excluded_nodes` (people avoided, and people who share an avoided person's displayed name); an avoided person who is not on the staff changes nothing. (b) The brief said to break any
   reference cycle when releasing the replaced router; the router and its search object still refer to each other (see fix 5), and the heavy structures are freed by dropping the references to them instead. (c) `ClosenessRoutes.route` no longer calls `index()` a second time; that is one line outside the five findings, made so that a release cannot cost an in-flight request a second index build.
   (d) The collection stalls every request thread while it runs; the figure for the live heap is not known until the first publish after the restart (`gc_ms`). If it is too long, the options are to skip the collection (the release alone frees the indexes; the router shell then waits for the ordinary collector) or to run it only when a router was replaced.
5. Six other asserts of the flaky test's shape (`... ['status'] in ('queued', 'searching')`) are in `test_staffer_route_jobs.py` and were not changed: each is on a search held at a `GateRouter` gate, which cannot finish first, and none failed in the nine full runs of that file here.
6. The new test modules are not registered in `fec/tests/run_tests.py` (as landing_v2's and landing_v3_ids's were not).
7. Whether and how the applied files are committed in LIVE (D-060 leaves the working tree as it is; the reconcile lane commits). The integration branch is in the shared repository, and the repository's post-commit hook has copied it to the local `mirror` remote (`C:\Users\pgoff\GitMirrors\melange-systems.git` holds `claude/staffer-route-v4-20261003` at `79ef9f1b7`, as it does for the other branches); nothing was pushed to `origin` (GitHub).
8. This directory is in the session scratchpad. Copy it somewhere durable if it must outlive the session. `SHA256SUMS.txt` lists every file in it (`python scripts\make_sums.py --check`).
9. The running sidecar's memory: its working set was 1.5 GB when this work began (22:57) and 8.4 GB when it ended (00:17), and the host's free physical memory fell from 4.3 GB to 1.3 GB in the same time. This work never touched the sidecar (the suites, the proofs and the memory harness run in their own processes, the largest at 0.59 GB), and its cause was not examined here; it matters for when to stop it for the apply
   (`proof\live_untouched.txt` records the readings).
