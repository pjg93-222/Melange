# Staffer people-network identifier follow-up: LIVE patch set v3, second cut (cut 2026-10-03, NOT applied)

One patch set, cut with `fec/tools/live_patch.py` (D-060) against the bytes LIVE holds now, with `..\landing_v2\` already applied there (landing_v2 went into LIVE at 14:59:02 on 2026-10-03). It finishes Paul's ruling D-083 in the two
client searches that still matched pieces of identifiers, and it documents the verifier's LOW-1 finding about ranked alternatives without changing any behaviour. No file in LIVE's working tree was written, applied, staged or committed
by the cut or by any proof, and the sidecar on 127.0.0.1:8841 was not touched (no script here connects to it; the tests that start servers use ephemeral ports). It is a second patch, not a replacement: apply it on top of landing_v2
(the apply script refuses otherwise).

## This is the second cut; the first cut is superseded

This folder replaces the first cut of the same name. The first cut (tip `a5e33a0b2`, 6 files, 59,126 bytes, sha256 `e503cd6aeb80838e08542625d58d091e3f1ad7200a12c6711356876624d2c6fc`) is kept whole and byte for byte in the **sibling** folder
`..\landing_v3_ids_superseded_20261003-1517\` (its own `SHA256SUMS.txt` still checks there: 43 files). It would still pass a dry run against LIVE, so it would apply: do not apply it, apply this one. What differs:

| | first cut (superseded) | this cut |
|---|---|---|
| Branch tip | `a5e33a0b2` | `f23a40aee`, one more commit: it documents LOW-1 (two files, +3 / -1 lines) |
| Files | 6 | 7: `fec/surfaces/staffer_closeness_routes.py` is new in the set (docstring only) |
| Patch | 59,126 bytes, sha256 `e503cd6a...` | 64,522 bytes, sha256 `1d408991...` |
| `staffer_live/README.md` post-image | `9b6edaf9...` | `8efd1982...` (one more sentence, in the near-tie paragraph) |
| Pre-images | landing_v2's post-images from `landing_v2\post_images` (LIVE did not hold them yet) | LIVE's own files as they are now, which are landing_v2's post-images (the cut checks that byte for byte and stops if not) |
| The other 5 files | pre- and post-image sha256 identical in both cuts | |

| | |
|---|---|
| Branch | `claude/staffer-search-ids-followup-20261003`, worktree `C:\Users\pgoff\Melange-wt\route-search`, tip `f23a40aee4c749bae9db132599a853a52c81d9bf`, two commits on top of landing_v2's tip `86631c454815533798eb1ad81136ddb1a76a23b9`: `a5e33a0b2` (the identifier follow-up) and `f23a40aee` (documents LOW-1) |
| Requires | `..\landing_v2\` (`route_latency.patch`) applied to LIVE first. It is: LIVE holds its post-images, and the dry run below is clean |
| Base = LIVE main | `3248a6a02e42bd23665995e69dc649ac926aab95` (LIVE HEAD unchanged at the cut and at the last proof) |
| Patch | `ids_followup.patch`, 64,522 bytes, sha256 `1d4089913b279dd566efaf80b4da347f5aa613743a4ab3aff97b3123e5bee338` |
| Files | 7: 5 edited in place, 2 new; list, pre- and post-image hashes and terminator profiles in MANIFEST.txt |
| Needs a restart | No. The page files (`staffer-live.js`, `staffer-inventory-worker.js`) and the README are static, and the sidecar reads its static files from disk on every request (`send_asset`, `Cache-Control: no-store`), so the new page code is served on the next page load. `staffer_closeness_routes.py` gains two docstring lines and nothing else (no statement changes; the code below them shifts down by two lines, and no file or document pins a line number in it), and a running sidecar keeps the module it loaded, so nothing needs a restart. landing_v2's Python still needs the 8841 restart it asks for, which is Paul's call (D-080). |

## What it contains

D-083: a search never matches a piece of a machine identifier. A query equal to a whole identifier (trimmed, in any case; the bare uuid of a `politico:<uuid>` id counts) still finds
the rows. landing_v2 applied that to the server typeahead, the static graph search and the record browser's column 0 (the node id). This applies it to the rest.

| Function | Searched by pieces before | Searched by pieces after | Matched only whole after (trimmed, any case) |
|---|---|---|---|
| `matchesQuery` in `staffer-live.js:105-109` (the map's query filter and the legacy result list) | the label, which is the node id when a node has neither label nor name; the node id; the source summary; `member_ids`, `committee_ids`, `policy_ids` | the label or name (no id fallback); the source summary | the node id; the bare uuid of a `politico:<uuid>` id; each member, committee and policy id. The server's search flag is honoured as before. |
| `filter` in `staffer-inventory-worker.js:22-39` (the record browser's People found list) | columns 1 to 6 and 11 by word prefix: name, summary, member id, committee id, policy id, source, aliases (column 0, the node id, was already whole-only since 86631c454) | columns 1, 2, 6 and 11: name, summary, source, aliases | column 0 (and the bare uuid), listed first; then columns 3, 4 and 5 (member, committee, policy id), listed next; then the rows that match by words; each group in row order |

Callers of `matchesQuery`: `rebuild()` (the matching people stay in the bounded sample) and `results()` (the legacy list, which the page skips when `staffer-explorer.js` is loaded);
nothing else reads the search index it fills. Neither caller changed, and the predicate is the same one, so a whole-identifier match is a plain match there: `results()` keeps its
order. A code that merely begins with the query, and a code inside a longer query, no longer match in the browser; a null among the codes is skipped and a number is a code.

LOW-1, documented and not changed (new in this cut, commit `f23a40aee`). The verifier's finding: in `ClosenessRoutes.route()`'s Yen loop (`staffer_closeness_routes.py`, lines 686-707 before the patch, 688-709 after it) each spur search
judges the 10**-12 tie window against its own spur cost, not the whole route's cost, so two ranked alternatives that tie within the window over the whole route can occasionally be listed out of step order (reproduced once: a 5e-12 spur gap,
9.8e-14 on the whole route). The commit says so in two places and changes no code:

- the `ClosenessRoutes` class docstring, two inserted lines (559-560 after the patch): "Each spur search of the ranked loop judges that width against its own spur cost, not the whole route's, so two alternatives that tie within the width over the whole route can occasionally be listed out of step order."
- the near-tie paragraph of `fec/surfaces/staffer_live/README.md` (line 56), one sentence, placed before the sentence about `distinct` and `independent`: "In the ranked list of alternatives, the tie window is judged within each alternative's own search, so two alternatives that tie only over the whole route can occasionally appear out of step order."

Files:
- `fec/surfaces/staffer_live/staffer-live.js`: `matchesQuery` and a new `wholeIds` (the cached index entry is now `{words, ids}`).
- `fec/surfaces/staffer_live/staffer-inventory-worker.js`: `filter`, a new `wholeCode`, the comment above them.
- `fec/surfaces/staffer_live/README.md`, two hunks: line 56, the LOW-1 sentence (above); line 72, the identifier sentence, which says a whole person id or uuid puts that person first and a whole bioguide id lists the staff attached to that member
  (typeahead), and that the record browser and the map's query filter follow the same rule over their own text. The old wording said the person "ranks first", which is not true of a bioguide id.
- `fec/surfaces/staffer_closeness_routes.py`: the two docstring lines above, +2 / -0, nothing else.
- `fec/tests/surfaces/test_staffer_live_query_ids.cjs` (new, 25 tests) and `test_staffer_inventory_worker_codes.cjs` (new, 20 tests); see Test evidence.
- `fec/tests/surfaces/test_staffer_inventory_worker_ids.cjs` (landing_v2's record-browser test, edited): its `expected()` stated "columns 3 to 5 searched as before", and two of its deliberate bugs
  name worker source text that moved. Those three places change; nothing else in it does.

## Apply (Paul's step), landing_v2 first (it is already in)

Preconditions are enforced twice, by `apply_landing.py`'s pre-flight and again by `apply_to()`: every file the patch edits must hash to its pre-image in MANIFEST.txt (landing_v2's post-image where
landing_v2 touches the file, which is what LIVE holds now; LIVE's own `staffer-live.js` where it does not) and neither new file may exist. A tree that does not hold them gets the dry run's own refusal, with the files named.

```powershell
# 0. optional read-only report: HEAD, each file's hash against its pre-image, the dry run, the raw git check, the rollback plan
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v3_ids\scripts\dry_run_live.py"

# 1. dry run: pre-image check, then git apply --check; writes nothing
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v3_ids\scripts\apply_landing.py"

# 2. apply to LIVE (live_patch.apply_to: refuses a moved target, checks every post-image sha256, puts the bytes back on any failure)
python "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v3_ids\scripts\apply_landing.py" --apply
```

The same patch with plain git, without the hash gates (D-060's command):

```powershell
git -C "C:\Users\pgoff\OneDrive\Desktop\Melange Systems" -c core.autocrlf=false -c core.safecrlf=false apply "C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems\4f30368b-c2d1-47f6-a368-3d68b2892c85\scratchpad\landing_v3_ids\ids_followup.patch"
```

Never use `--index` or `--cached` (LIVE blobs are pure LF), never a plain `git apply` without `-c core.autocrlf=false`, and do not EOL-normalise LIVE (D-060, DE-041). Applying leaves LIVE with 14 ` M` entries from the two patch sets
(landing_v2's 13 plus `staffer-live.js`; `staffer_closeness_routes.py` is already one of landing_v2's 13) and 17 `??` entries (landing_v2's 15 plus the two new tests; the edited test is one of landing_v2's new files); committing is a separate decision.

## Rollback

```powershell
python "...\landing_v3_ids\scripts\rollback_landing.py"                # plan: writes nothing
python "...\landing_v3_ids\scripts\rollback_landing.py" --rollback     # restores the 5 saved pre-images byte for byte, removes the 2 new files
```

A file edited after the apply stops the rollback and nothing changes (`--force` overrides). The pre-images in `pre_images\` are landing_v2's post-images (and LIVE's `staffer-live.js`), so this rollback puts LIVE
back to "landing_v2 applied", not to before landing_v2. Roll back in reverse order: landing_v2's own rollback refuses while this patch is on. For a tree whose files are still exactly the post-images, the other way back
is `git -C "<LIVE>" -c core.autocrlf=false -c core.safecrlf=false apply -R "...\landing_v3_ids\ids_followup.patch"`.

To re-run the node tests in LIVE after the apply (node only; the negative controls read `86631c454` from LIVE's own repository, which holds it, so they run there too):

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
node --test fec/tests/surfaces/test_staffer_live_query_ids.cjs fec/tests/surfaces/test_staffer_inventory_worker_codes.cjs fec/tests/surfaces/test_staffer_inventory_worker_ids.cjs
node --test fec/tests/surfaces/test_staffer_inventory_worker.cjs fec/tests/surfaces/test_staffer_payroll_map.cjs fec/tests/surfaces/test_staffer_map_scope.cjs fec/tests/surfaces/test_staffer_route_jobs_client.cjs
```

## How it was cut (D-060, DE-040, DE-041) and proved

`scripts\cut_landing.py` (landing_v2's cutter; this cut changes only where the pre-images come from). Bytes end to end, lines split on LF only (`live_patch.split_lines`). The pre-image of every edited file is LIVE's own working file as it is now,
read in binary and read-only; for the four files landing_v2 edits, the cut also requires those bytes to be landing_v2's post-image (its manifest hash, and byte for byte against `landing_v2\post_images`), and it stops otherwise; it stops too if LIVE's HEAD is not
`3248a6a02` or if a new file already exists in LIVE. For each edited file the pre-image must equal the base blob (86631c454) line for line (it did, for all 5). Every changed region of base to tip (two commits now) is spliced into the pre-image's own lines;
its anchor (unchanged context on both sides plus the old lines) must hit exactly once; inserted lines carry the file's majority terminator; untouched lines are never rewritten; after the last splice the content equals the
tip blob line for line. The two new files carry the exact tip bytes (pure LF in the blobs). The patch is stored here, outside every repository (DE-040). No string replacement is used to cut. `prove()` passed at the cut (`proof\cut_output.txt`).

The terminator profiles that matter, from MANIFEST.txt: `staffer_closeness_routes.py` is MIXED in LIVE (770 CRLF, 6 bare LF; after: 772 and 6: the two new lines carry the majority, CRLF), `staffer-inventory-worker.js` is MIXED (67 CRLF, 27 bare LF; after: 70 and 27),
`staffer-live.js` is MIXED (149 CRLF, 4 bare LF; after: 153 and 4), `README.md` is PURE_CRLF and stays so, the edited test is PURE_LF and stays so.

All four proofs were re-run on this cut, in the state LIVE is in now (landing_v2 applied, LIVE HEAD `3248a6a02`):

1. **Main proof**, `scripts\prove_landing.py` (`proof\proof_results.txt`): **80 checks passed, 0 failed.**
   - Each pre-image is checked to be landing_v2's post-image (sha256 equal and byte-identical to `landing_v2\post_images`) for the four files landing_v2 edits, or LIVE's own file for `staffer-live.js`; all five are LIVE's bytes now.
   - Scratch tree of the pre-images, `apply_to()` there, then `live_patch.py drift` of every post-image against the branch tip's file: **3 IDENTICAL_BYTES, 4 EOL_ONLY, 0 CONTENT.** Each EOL_ONLY file (`staffer_closeness_routes.py`, the worker,
     `staffer-live.js`, the edited test) has the same content as the tip blob line for line and only terminators differ, because the pre-image keeps its own and the branch worktree holds git-checkout CRLF.
   - Terminator audit: with lines aligned by the base-to-tip diff, every untouched line is byte-identical (terminator included) between pre-image and post-image in all 5 edited files, every inserted line carries the majority
     terminator, no lone CR appears, bare-LF counts do not grow in the CRLF-majority files.
   - Gated on landing_v2 and checked against LIVE itself (read-only): the dry run passes with rc=0, raw `git apply --check` passes, the five edited files hold exactly this patch's pre-images, LIVE HEAD is `3248a6a02`, neither new path exists or is tracked.
   - Both rollbacks (`git apply -R`, and the saved pre-images) restore the scratch tree byte for byte and remove the new files.
   - Every post-image JavaScript file passes `node --check` (5 files) and the Python file compiles.
2. **Operator scripts**, `scripts\prove_scripts.py` (`proof\script_proofs.txt`): ALL PASS (19 checks), on scratch trees: refused on what LIVE held before landing_v2 (nothing written), refused on a landing_v2 tree with one moved target (nothing written, the other files included),
   dry run, `--apply`, a second `--apply` refused, rollback plan, rollback refused after a later edit, rollback, a second rollback a no-op.
3. **Order**, `scripts\prove_chain.py` (`proof\chain_proof.txt`): ALL PASS (18 checks), with both patch sets' real scripts on a scratch tree built from LIVE's own pre-images: follow-up refused, landing_v2 applied, follow-up dry run and applied (31 watched paths checked byte
   for byte at every step; the follow-up changed exactly its 7 files), landing_v2's rollback refused while the follow-up is on, follow-up rolled back, landing_v2 rolled back, LIVE-as-it-was again.
4. **The dry run against the real LIVE tree**, read-only, `scripts\dry_run_live.py` (`proof\dry_run_against_live_after_landing_v2.txt`): LIVE HEAD `3248a6a02`; all 7 files at their pre-image hashes (5 hash-equal, 2 absent as they should be);
   `apply_landing.py` dry run rc=0; the raw `git -c core.autocrlf=false -c core.safecrlf=false apply --check` rc=0; the rollback plan reports every edited file "already original" and both new files "already absent".

LIVE was fingerprinted read-only (`scripts\live_fingerprint.py`: HEAD, the full `git status --porcelain -uall` text, and path, size and mtime of the 883 files under `fec/surfaces`, `fec/tests/surfaces` and `fec/tools`) before the cut, midway and after the last suite run, and
the three are identical: `proof\live_untouched.txt`.

## Test evidence

Node tests, in the worktree at the new tip `f23a40aee` (git available, so no negative control is skipped): three runs in a row of the three files, then every node test in `fec/tests/surfaces` (`proof\new_tests_three_in_a_row.txt`): 59 passed each time
(25 + 20 + 14), 0 failed, 0 skipped; all 20 files, 159 tests, pass. `fec/surfaces/test_staffer_closeness_bidirectional.py`, the module whose docstring this cut touches, passes at the new tip (57 tests; once in the worktree before the commit, and inside both suite runs below).

- `test_staffer_live_query_ids.cjs` runs the real `staffer-live.js` in a vm over a fake DOM, so the predicate and both callers are exercised. Ten hand-written ruling checks; a seeded world of 120 nodes and 3,767 queries
  (every 1- and 2-character query over a-z, 0-9 and the punctuation of ids, sampled names, summaries, pieces of ids and codes, whole ids and codes in six capitalisations; 452,040 predicate calls; 419 queries also through both
  callers) compared with the ruling written out by brute force; a cache test; the page as it was at 86631c454 read from git as the negative control (it fails 5 of the 10 checks and differs from the ruling on 1,604 of the 3,767
  queries, 10,399 matches too many, none missing); 11 deliberate bugs, each caught.
- `test_staffer_inventory_worker_codes.cjs` does the same for the worker: eight ruling checks, a seeded world of 125 rows and 3,748 queries (63 whole-code queries, 188 strict pieces of codes, labels that are codes so rows match by
  words before and after the rows holding the code), the worker at 86631c454 from git as the negative control (fails the code-fragment, whole-code and ranking checks; differs on 295 queries, 2,436 matches too many, none missing,
  26 in another order), 9 deliberate bugs, each caught.
- Against the two source files as they were before (read from git into a scratch tree, `proof\previous_tip_a5e33a0b2\new_tests_fail_on_old_code.txt`): the live test fails 16 of 25 (the five ruling checks and the seeded world among them), the worker test 11 of 20
  (three ruling checks and the seeded world among them); the rest are the deliberate-bug tests, which cannot find the text they break in the old source.
- The negative controls read the old code with `git show 86631c454:<file>` and are skipped, with the reason printed, in a tree that has no such commit; the positive checks always run.

The whole staffer suite, one process per file (`scripts\run_suites.py`: `fec/surfaces/test_staffer_*.py`, `fec/tests/surfaces/test_staffer_*.py`, two `staffer_network` tests, every `fec/tests/surfaces/*.cjs`, and the known-red repin test), run three ways:

| | files | passed | failed | skipped |
|---|---|---|---|---|
| first cut's tip `a5e33a0b2`, clean `git archive` export (the run recorded for the first cut) | 69 | 1415 | 1 | 10 |
| new tip `f23a40aee`, clean `git archive` export (`proof\test_results_previous_tip_vs_new_tip.txt`) | 69 | 1415 | 1 | 10 |
| the applied tree: LIVE-as-it-was + landing_v2 + this patch, each by its own `apply_landing.py --apply` (`proof\applied_tree_suites.txt`) | 69 | 1415 | 1 | 10 |

The one red is the same in all three: `fec/surfaces/test_repin_staffer_live.py::VerificationDerivationTests::test_default_generation_derives_expected_default_verification` (known baseline; it fails identically at 722a55ba7 and 86631c454). **Zero new failures, and every one of the 69 files has the same counts in the
three runs** (`compare_baseline.py` lists only the repin file, as the same failure). The applied tree runs this patch's post-images themselves, with their mixed terminators, including the docstring-edited `staffer_closeness_routes.py`; the baseline is the tip's pure-LF blobs. The exports have no `.git`, so the four negative controls that
need git are the 4 skips beyond the 6 that were already there. Peak resident memory of the process tree: 404 MB (applied tree), 465 MB (tip export). The machine was loaded while these ran, so each took about 830 s against about 430 s for the first cut's runs; the timings say nothing about the code. `scripts\run_suites_both.sh` ran the two (applied tree first), and `scripts\build_suite_proofs.py` assembled the three proof files from their logs.

The tests that mention `staffer_live` but are not named `test_staffer_*`, which that runner does not reach (the dashboard, clean workspace, combined section, network html, edge startup and desktop tests; `proof\extra_tests.txt`): 6 files, 287 passed, 0 failed, 2 skipped at the new tip, and the same at 86631c454 and a5e33a0b2.

Taken at the first cut's tip `a5e33a0b2` and kept in `proof\previous_tip_a5e33a0b2\`, not re-run (the new commit changes two files, a docstring and a README sentence: `git diff --name-status a5e33a0b2 f23a40aee` lists those two and nothing else, so the page files and the three node tests are byte-identical at the two tips):
`new_tests_fail_on_old_code.txt` (above), `test_results_previous_tip_vs_followup_tip.txt` (86631c454: 67 files, 1374 passed, 1 failed, 6 skipped, against a5e33a0b2), `extra_tests.txt` (86631c454 against a5e33a0b2), and `filter_cost.txt`, the cost of the two searches (medians of 7, one process, 588 MB peak):
the record browser's filter over 145,000 rows takes 164 to 236 ms before and 164 to 208 ms after across eight queries, no difference outside the noise; the map's query filter over 20,000 nodes (the page's full-mode limit) takes 35 to 42 ms to fill its index once (16 to 20 ms before) and 8 to 13 ms for a pass over the filled index (7 to 10 ms before).

## Needs Paul

1. landing_v2 is in LIVE (14:59:02). APPLY this patch next, in place of the first cut: the dry run against the real LIVE is clean. No restart for this one; landing_v2's Python still needs the 8841 restart it asks for, which is Paul's call (D-080).
2. The brain entry D-083 is a draft in the packet. This patch carries the rule to the browser's two searches; D-083's text ("typeahead") now understates it by two surfaces.
3. Interpretation, one place: `matchesQuery` is a predicate, so "listed first" does not apply to it. `rebuild()` keeps matching people ahead of the rest as before and `results()` (the legacy list, unused while `staffer-explorer.js`
   is loaded) keeps its node order; a whole id there is included, not moved. The record browser, which is what a person sees, lists whole-id rows first, then rows a whole code names, then word matches.
4. Still not changed, each one a ruling or out of scope: the unused legacy `IncrementalProfiles.graph(query)` in `staffer_live_server.py` (matches the query against each profile row's JSON text; only `LiveDashboard.snapshot`
   calls it and only a test uses that); the unused `staffer-map-worker.js` (nothing sends it a search); the Groups search (office and organisation names). The typeahead has never searched committee or policy ids, so the README
   sentence says only "bioguide id" for it.
5. LOW-1 is documented here, not fixed: judging the tie window over the whole route inside each spur search would change which alternative is listed when, so it is a ruling. The behaviour is as it was.
6. The previous step's test file was edited (see Files); the file ownership named only new tests. The three changes are listed in the commit message of `a5e33a0b2`.
7. The new test modules are node native and are not registered in `fec/tests/run_tests.py`, as landing_v2's were not.
8. Whether and how the applied files are committed in LIVE (D-060 leaves the working tree as it is; the reconcile lane commits).
9. This directory and its superseded sibling are in the session scratchpad. Copy them somewhere durable if they must outlive the session. `SHA256SUMS.txt` lists every file in this directory (`python scripts\make_sums.py --check`); the superseded sibling has its own.
