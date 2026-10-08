# Staffer people-network latency fix: LIVE patch set v2 (cut 2026-10-03, NOT applied)

One patch set, cut against the LIVE working-tree bytes with `fec/tools/live_patch.py` (D-060), covering every file the branch changed since LIVE main.
It replaces `..\landing\` (cut at 33a87a321, marked SUPERSEDED). No file in LIVE's working tree was written, applied, staged or committed, and the
sidecar on 127.0.0.1:8841 was not touched.

| | |
|---|---|
| Branch | `claude/staffer-route-latency-20261002`, worktree `C:\Users\pgoff\Melange-wt\route-jobs`, tip `86631c4548155338...` (full hash in MANIFEST.txt) |
| Base = LIVE main | `3248a6a02e42bd23665995e69dc649ac926aab95` (LIVE HEAD unchanged at the cut and at the last proof) |
| Patch | `route_latency.patch`, 534,450 bytes, sha256 `0b5db04b5d0cb785ab98b6f4e33e758d916102d421d75c27ec5a3bd2331c3076` |
| Files | 28: 13 edited in place, 15 new (2 source modules, 1 shared test fixture module, 10 pytest modules, 2 node tests); list, hashes and terminator profiles in MANIFEST.txt |
| Commits on the branch | 629da986f, d91c21478, 977f37dcf, 50b994883, 73839b6dc, 9035f18d5, 970e8c6d7, 33a87a321 (the v1 set), then c9f15c456, b94102743, 3ea561ac0, d1656d81e, 722a55ba7, 6fc248d8d, a4da9f92f, 86631c454 |

## What it contains

Everything of v1: the exact bidirectional work-time search seeded from office staff at their terminal costs with compact hop-row caches shared across
requests and the three distinct routes; cancellable background route searches with supersede, per-page holders, an abandonment sweeper and route 1 shown
while the alternatives finish; typeahead and the map served from one published view without the service lock, a memoised 30-second refresh, a SQL status
count and a pre-tokenised short-query index; and the fixes of the final verification.

Added since v1:

- **D-082, near ties (b94102743, 3ea561ac0, d1656d81e, 722a55ba7).** Routes whose exact costs lie within one part in 10^12 of the cheapest tie; fewer steps
  wins, then lower exact cost; the reported cost is still the float sum from the origin. Alternatives under `ranked` follow the same rule. This replaces
  v1's documented near-tie behaviour (the old open ruling T1). A test pins that a raise from the near-tie guard ends a route job as `search_error`.
- **D-083, identifiers are searched whole (c9f15c456, merged in 6fc248d8d).** Typeahead matches pieces of a query only against names, titles, aliases and
  office names. A node id, `politico:<uuid>`, a bare uuid or a bioguide id matches only when the whole query is that identifier, in any case.
  The profile search, the static graph search and the live refresh's profile text build changed; `staffer_search_index.py` is new.
- **The same rule in the record browser (86631c454).** `staffer-inventory-worker.js` no longer searches column 0 (the node id) by word prefix; a query that
  is a row's whole id (trimmed, any case; for `politico:<uuid>` also the bare uuid) still finds the row and lists it first. New node test with the previous
  filter embedded as a negative control and seven deliberate bugs.
- **README (a4da9f92f).** One paragraph in `staffer_live/README.md` states the D-083 rule.

## Apply (Paul's step)

Preconditions are enforced by `apply_to()`: LIVE files must still hash to the pre-image values in MANIFEST.txt, and none of the 15 new paths may exist.
Close any chain or refresh that is writing these files first.

```powershell
# 1. dry run: git apply --check only, writes nothing
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v2\scripts\apply_landing.py"

# 2. apply to LIVE (live_patch.apply_to: refuses a moved target, checks every post-image sha256, puts the bytes back on any failure)
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v2\scripts\apply_landing.py" --apply
```

The same patch with plain git, without the hash gates (D-060's command):

```powershell
git -C "C:\Users\pgoff\OneDrive\Desktop\Melange Systems" -c core.autocrlf=false -c core.safecrlf=false apply "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v2\route_latency.patch"
```

Never use `--index` or `--cached` (LIVE blobs are pure LF), never a plain `git apply` without `-c core.autocrlf=false`, and do not EOL-normalise LIVE (D-060,
DE-041). Applying leaves 13 ` M` and 15 `??` entries in LIVE; committing them is a separate decision. Python loads the modules at start, so the running
sidecar keeps the old code until Paul restarts 8841 (D-080: the restart is Paul's call; the MelangeStafferLiveSidecar task stays disabled).

Apply and restart back to back. The sidecar reads its static files from disk on every request (`send_asset`, `Cache-Control: no-store`), so the changed `index.html`,
`staffer-route.js` and `staffer-inventory-worker.js` are served the moment the patch lands, while the old Python keeps answering until the restart. The new
`staffer-route.js` reads the new response fields optionally (`partial_routes?.`, `search_id`), but old server and new page were not run together.

After the apply, `python scripts\rollback_landing.py` (no flag) prints `restore pre-image` / `remove new file` for every file only if it is still exactly
the patch's post-image, so it doubles as an "applied exactly" check.

## Rollback

```powershell
python "...\landing_v2\scripts\rollback_landing.py"                # plan: writes nothing
python "...\landing_v2\scripts\rollback_landing.py" --rollback     # restores the 13 saved pre-images byte for byte, removes the 15 new files
```

A file edited after the apply stops the rollback and nothing changes (`--force` overrides). The pre-images are in `pre_images\` (byte-exact copies of LIVE as
cut). For a tree whose files are still exactly the post-images, the other way back is
`git -C "<LIVE>" -c core.autocrlf=false -c core.safecrlf=false apply -R "...\landing_v2\route_latency.patch"`. Both were run on a scratch tree.

## How it was cut (D-060, DE-040, DE-041) and proved

`scripts\cut_landing.py` (unchanged from v1). Bytes end to end, lines split on LF only (`live_patch.split_lines`). For each edited file LIVE's content must equal
the base blob line for line (it did, for all 13). Every changed region of base to tip is spliced into LIVE's own lines; its anchor (unchanged context on both
sides plus the old lines) must hit exactly once in LIVE's content with the terminator stripped. Inserted lines carry the file's majority terminator;
untouched lines are never rewritten; after the last splice the content equals the tip blob line for line. New files carry the exact tip bytes (all 15 are pure
LF in the blobs and stay LF). No string replacement is used to cut. The patch lives outside every repository. `prove()` passed at the cut
(`proof\cut_output.txt`). `scripts\prove_landing.py` (v1's, plus a new syntax step) then proved, in `proof\proof_results.txt` (205 checks, 0 failed):

1. Scratch tree of LIVE's own pre-images, `apply_to()` there, then `live_patch.py drift` of every post-image against the branch tip's file:
   **21 IDENTICAL_BYTES, 7 EOL_ONLY, 0 CONTENT.** In each EOL_ONLY file the EOL-normalised content is identical and only terminators differ, because LIVE
   keeps its own:
   - `staffer_distinct_routes.py`, `staffer_overlap_routes.py`: LIVE is PURE_LF, the branch worktree is CRLF (git checkout under autocrlf). The patch keeps LF.
   - `staffer_closeness_routes.py`: LIVE is MIXED (235 CRLF, 8 bare LF), the branch worktree file is PURE_LF. Post-image: 770 CRLF, 6 LF. Two of LIVE's eight
     bare-LF lines (pre-image lines 192 and 193) sit inside a region the patch replaces, so their replacements carry CRLF, the majority.
   - `staffer_graph_snapshot.py` (9 bare-LF lines), `staffer_live_server.py` (35), `staffer_routing.py` (1), `staffer-inventory-worker.js` (27): LIVE is MIXED, the
     branch worktree is PURE_CRLF. The untouched bare-LF lines stay bare LF (none of the worker's 27 is in the replaced region).
2. Terminator audit: with lines aligned by the base-to-tip diff, every untouched line is byte-identical (terminator included) between LIVE and the post-image
   in all 13 edited files, every inserted line carries the file's majority terminator, no lone CR appears.
3. `git -C LIVE -c core.autocrlf=false -c core.safecrlf=false apply --check` against LIVE itself: rc 0 (read-only).
4. LIVE has not moved: HEAD is `3248a6a02`, all 13 pre-image hashes equal the manifest, none of the 15 new paths exists or is tracked.
5. Both rollbacks (`git apply -R`, and the saved pre-images) restore the scratch tree byte for byte and remove the new files.
6. Every post-image Python file compiles (22 files) and every JavaScript file passes `node --check` (4 files), read from the saved post-images.

Beyond `prove_landing.py`, `scripts\applied_tree_run.sh` runs the patch as applied: a clean export of `fec/` at 3248a6a02 with the 13 edited files replaced by LIVE's
exact pre-image bytes, the patch applied with `scripts\apply_landing.py --apply`, then every staffer suite (`proof\applied_tree_suites.txt`): 1374 passed, 1 failed,
6 skipped over 67 files, file by file identical to the run on the clean tip export (the one red is the baseline one below). That executes the mixed-terminator
post-images themselves, not only their normalised content.

`proof\script_proofs.txt` covers the operator scripts on a scratch tree (dry run against LIVE, `--apply`, a second `--apply` refused, rollback plan, rollback
refused after a later edit, rollback, second rollback a no-op): ALL PASS.

One note on the cut itself: its guard that a new file's worktree bytes equal the tip blob stopped the first attempt, because the merge of the uuid branch had
rewritten three new files' working copies as CRLF (autocrlf checkout). Their working copies were made LF (blobs unchanged, `git diff` empty), and the cut then ran
clean.

## Test evidence

Clean `git archive` exports of `fec/` with autocrlf off, plus the four gitignored data files copied read-only from LIVE `fec/surfaces/` (deleted afterwards), one process per
file; the runner, the comparison and the memory sampler are `scripts\run_suites.py`, `scripts\compare_baseline.py` and `scripts\run_with_peak.py` (usage in their
docstrings). `proof\test_results_baseline_vs_tip.txt`:

| | files | passed | failed | skipped |
|---|---|---|---|---|
| baseline 722a55ba7 | 65 | 1338 | 1 | 6 |
| tip 86631c454 | 67 | 1374 | 1 | 6 |

The one red is the same at both: `fec/surfaces/test_repin_staffer_live.py::VerificationDerivationTests::test_default_generation_derives_expected_default_verification`
(known baseline, an informational extra in the run). **Zero new failures.** The count changes are the uuid branch's and the record browser's own tests:
`test_staffer_search_differential.py` 16 to 21 (five tests whose expectation was "the new search equals the old one" now state the ruling, five added),
`test_staffer_typeahead_identifiers.py` 17 new, `test_staffer_inventory_worker_ids.cjs` 14 new; the lists are in that file. The uuid and record-browser tests, three
runs in a row: 56 passed each time (`proof\uuid_and_record_browser_tests_three_in_a_row.txt`). The previous worker file fails the new node test, 12 of 14
(`proof\old_worker_fails_the_new_test.txt`). `python -m fec.surfaces.test_staffer_closeness_bidirectional --ties` reports `violations 0` in both modes
(`proof\ties.txt`). The record browser's filter costs nothing measurable on 145,000 rows: medians 202 to 291 ms new against 207 to 357 ms old across five queries
(`proof\worker_filter_cost.txt`). Peak resident memory where it was sampled: the 145,000-row benchmark 339 MB, the repeated uuid and record-browser runs 165 MB, `--ties` 68 MB (the three full-suite runs were not sampled).

To re-run in LIVE after the apply (LIVE already has the four data files):

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
python -m pytest fec/surfaces/test_staffer_closeness_bidirectional.py fec/tests/surfaces/test_staffer_route_jobs.py fec/tests/surfaces/test_staffer_lock_free_view.py fec/tests/surfaces/test_staffer_refresh_memo.py fec/tests/surfaces/test_staffer_route_latency.py fec/tests/surfaces/test_staffer_typeahead_http.py fec/tests/surfaces/test_staffer_typeahead_identifiers.py fec/tests/surfaces/test_staffer_search_differential.py fec/tests/surfaces/test_staffer_rebuild_view.py fec/tests/surfaces/test_staffer_identity_status_count.py -q -p no:cacheprovider
node --test fec/tests/surfaces/test_staffer_route_jobs_client.cjs fec/tests/surfaces/test_staffer_inventory_worker_ids.cjs fec/tests/surfaces/test_staffer_inventory_worker.cjs
python -m fec.surfaces.test_staffer_closeness_bidirectional --ties
```

## Needs Paul

1. APPLY and restart 8841 back to back (the page files go live at the apply, the Python at the restart), then run the live panel (C2/C3 of the eval) with GET only; abort if host available RAM < 400 MB.
2. The brain entries D-082 and D-083 are drafts in the packet for Paul to apply.
3. D-083 is applied in this set to the server typeahead and to the record browser's column 0 only. Still open, not in this patch, each one a ruling:
   - The record browser's columns 3, 4 and 5 hold the member (bioguide) id, committee id and policy id; its search still matches them by word prefix.
   - `staffer-live.js` `matchesQuery` (line 105, the map's query filter and the legacy result list) matches substrings of `n.id` and of the member, committee and policy ids.
   - The unused legacy `IncrementalProfiles.graph(query)` in `staffer_live_server.py` (line 362) matches the query against the JSON text of each profile row (uuid,
     source url, hashes); only `LiveDashboard.snapshot` calls it and only a test uses that.
4. The README sentence says the person named by an identifier "ranks first". That holds for a node id and a bare uuid; a whole bioguide id returns the staff attached to
   that member in the usual order. One clause to adjust if Paul wants the text exact.
5. The new test modules are pytest or node native and are not registered in `fec/tests/run_tests.py` (its explicit module list; the branch never touched it).
6. Whether and how the applied files are committed in LIVE (D-060 leaves the working tree as it is; the reconcile lane commits).
7. This directory is in the session scratchpad. Copy it somewhere durable if it must outlive the session.
