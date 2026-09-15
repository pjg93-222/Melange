# Commit lane 2026-09-14 -- Chart Studio usability lane commit + clean-checkout proof

Branch `codex/mentat-crypto`, starting HEAD `e666f95e5ee3680b900b2b29897d500c3f7039ee`,
282 `git status --porcelain` lines, working tree otherwise dirty with other lanes' work.
Authorized by Paul ("commit this in the Mentat tree"). Four commits landed: A, B, D, and
this receipt's own commit C. `git add -A` / `git add .` / stash / checkout -- / reset
--hard / commit --amend / branch switches / push were never used; every stage was by
explicit path.

## Preconditions (STEP 0)

`git branch --show-current` = `codex/mentat-crypto`. `git rev-parse HEAD` =
`e666f95e5ee3680b900b2b29897d500c3f7039ee`. `git diff --cached --stat` empty. Status line
count 282. Gates from the live tree before any staging: `node --test "mentat/app/tests/**/*.test.js"`
-- 108 pass, 0 fail. `python -m unittest mentat.tests.test_studio_views
mentat.tests.test_studio_briefing mentat.tests.test_publish_pocket
mentat.tests.test_contribution_http mentat.tests.test_desktop_launcher
mentat.tests.test_studio_contract_examples -q` -- Ran 58, OK. Both green.

## Commit A -- ed64743515257d5310e26ec52fd9d93824b97a26

"Track the pre-lane state of eight console files the usability lane builds on"

Method: for each of the 8 files, `git hash-object -w --path <repo path> <backup file>`
followed by `git update-index --add --cacheinfo 100644,<blob>,<repo path>` -- the working
tree itself was never touched. Backups used:
`.gitignore.bak-20260914-E`, `mentat/app/README.md.bak-20260914-F1`,
`mentat/app/Start-MentatApp.ps1.bak-20260914-F1`, `mentat/app/app.js.bak-20260914-F1`,
`mentat/app/chart-export.js.bak-20260914-E`, `mentat/app/charts.js.bak-20260914-E`,
`mentat/app/graph.js.bak-20260914-Fc`, `mentat/tests/test_desktop_launcher.py.bak-20260914-F1`.

Staged-blob proof: a python script read `git show :<path>` for each of the 8 and compared
it, with `b'\r'` stripped from both sides, against the corresponding backup file's bytes,
also `\r`-stripped. All 8 came back EQUAL. `git diff --cached --stat`:

```
 .gitignore                            |   6 +
 mentat/app/README.md                  | 304 +++++++++++++++++++++++++++++++---
 mentat/app/Start-MentatApp.ps1        |  59 +++++--
 mentat/app/app.js                     |  27 ++-
 mentat/app/chart-export.js            |  39 +++--
 mentat/app/charts.js                  |  13 +-
 mentat/app/graph.js                   |  64 ++++---
 mentat/tests/test_desktop_launcher.py |  61 ++++++-
 8 files changed, 492 insertions(+), 81 deletions(-)
```

Syntax checks on the staged blobs (dumped via `git show :<path>` to temp files): `node
--check` clean on app.js, chart-export.js, charts.js, graph.js; `python -m py_compile`
clean on test_desktop_launcher.py; PowerShell `[System.Management.Automation.PSParser]::Tokenize`
on Start-MentatApp.ps1 -- 1165 tokens, 0 errors. `.gitignore` and README needed no syntax
check per the spec. `git diff --cached --name-only` listed exactly these 8 paths, nothing
else. Committed with `git commit -F <msgfile>` (no `-a`).

## Commit B -- 215faa9db5e00d257df5f3128bd3f8dc8d21a414

"Finish the Chart Studio usability lane: build stamp, exports, saved views, briefing, fixes"

Method: `git add -- <path>` one at a time (batched in one invocation) over the 8 tracked
paths from commit A plus 9 more already-tracked paths (chart-studio-contributions.js,
chart-studio-core.js, chart-studio.css, chart-studio.js, cross-reference.js, index.html,
server.py, workspace.css, tests/chart-studio-core.test.js) at their live working-tree
content, plus 30 new files (chart-briefing.css/js, studio-contract-examples.json, two new
test fixtures, the vendored PptxGenJS bundle and its license, 16 new test files across
node/python/browser harnesses, and 8 files under mentat/tools/pocket/). No path was
refused as ignored and none was missing. sha256 of `mentat/app/vendor/pptxgen.bundle.js`
on disk verified == `4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8`
before staging. `git diff --cached --name-only` returned exactly these 47 paths -- no
`*.bak-*`, no `mentat/state`, no `node_modules`. Committed with `git commit -F <msgfile>`.

```
 47 files changed, 8139 insertions(+), 141 deletions(-)
```
(Full per-file stat is in `git log --stat` for this SHA; omitted here for length.)

## STEP P, first pass (on B) -- FAILED, correctly not amended

Detached worktree `C:\Users\pgoff\Mentat_verify_b` at SHA B; the two local-only files
(`mentat/inputs/fec_receipt_rules.json`, `mentat/config/report-directory.json`) copied in,
never staged. Results:

- `node --test` -- 101 pass, 0 fail (not the 108 the task text expected). Cause:
  `mentat/app/tests/reconcile-cycle.test.js` was untracked in the live tree, belongs to
  the fix1 lane's round 3, and was correctly absent from B's file list, so it is absent
  from a clean checkout of B. No test failed; the count just differed from a stale
  expectation.
- `python -m unittest` (6 modules) -- **Ran 58, FAILED (failures=4)**.
  1. `test_the_vendor_powerpoint_bundle_is_served_at_its_pinned_hash`: actual sha256
     `135ad5b3c18865afc28a4424aa303b0f6c2b1ac280a7fac437f95946446eccfc` != pinned
     `4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8`. Root cause:
     `core.autocrlf=true`, no `.gitattributes`. A fresh `git worktree add` checkout of the
     minified JS bundle converts 96 bare LF to CRLF (460889 -> 460985 bytes), corrupting
     its raw hash. The committed blob was correct; the corruption happened at checkout time.
  2. `test_assets_are_same_origin_and_accessible_in_read_only_mode`, 3 sub-failures:
     `/contribution-studio`, `/contribution-studio.js`, `/contribution-studio.css` all
     404 (expected 200). Root cause: `mentat/app/server.py` (committed in B) has routed
     these three paths to `mentat/app/contribution-studio.{html,css,js}` since before
     this lane, but those three files were untracked in the live tree (a different,
     uncommitted lane's work) and were never named in B's file list.
- Server/asset check on what B's `index.html` actually references: started
  `python mentat/app/server.py --port 8831 --read-only` from the clean checkout (pid
  31896), waited 5s. `/`, `/api/health`, and all 30 `index.html` src/href assets -> 200
  (contribution-studio is not referenced by index.html, so this check alone did not
  surface failure 2 -- only the python unit test did). Killed pid 31896 (confirmed dead).
  `git worktree remove --force` -- confirmed removed.
- Commit A's 8 files re-dumped from `git show ed6474351...:<path>` and re-syntax-checked:
  identical byte sizes to the STEP A dump, all checks clean (same results as STEP A).

Per instruction, this was not amended or widened. STEP C was skipped at that point and
the failures were reported for a ruling.

## Coordinator's ruling and Commit D -- 9b14e1d535278400ef35e8055a0b6989eb8ee9ca

"Pin the vendor bundle as binary and track the files the console already routes"

1. No `.gitattributes` existed. Created one (LF endings) with exactly:
   ```
   mentat/app/vendor/pptxgen.bundle.js -text
   mentat/tools/pocket/mentat-pocket.html -text
   mentat/tools/pocket/icon-180.png binary
   ```
   `git add -- .gitattributes`, then `git add --renormalize -- mentat/app/vendor/pptxgen.bundle.js
   mentat/tools/pocket/mentat-pocket.html`. `pptxgen.bundle.js` renormalized as a true
   no-op (its working-tree copy in the main checkout was still LF, byte-identical to the
   committed blob -- the corruption in STEP P only happens on a *fresh* checkout, which
   is exactly what `-text` now prevents). `mentat-pocket.html` did NOT renormalize as a
   no-op: its working-tree copy carries 1142 CRLF line endings (0 bare LF) while the blob
   committed in B was LF-only (autocrlf silently converted it away at the original `git
   add` time). With `-text` now set, `--renormalize` correctly recaptured the true on-disk
   CRLF bytes into the index (diff: 1145 insertions / 1142 deletions). Recorded per
   instruction, not treated as a stop condition.
2. Confirmed `mentat/app/contribution-studio.{html,css,js}` exist and are untracked
   (`git status --porcelain` showed `??` for all three). Syntax-checked the `.js` with
   `node --check` -- OK. Staged all three by explicit path.
3. Read `audits/mentat_system_debug_20260913/lanes/fix1/RECEIPT.md`, "Round 3" section.
   Its file table names six files touched in round 3; five (server.py, chart-studio.js,
   chart-studio-contributions.js, app.js, test_studio_wording.cjs) carry round-2 SHAs,
   meaning they already existed and were already part of B's committed content. Only
   `mentat/app/tests/reconcile-cycle.test.js` is marked "new" in that table. The three
   files the receipt elsewhere calls "created itself" (studio-contract-examples.json,
   tests/studio-contract.test.js, tests/test_studio_contract_examples.py, from round 1)
   were already tracked and already committed in B. So only reconcile-cycle.test.js
   qualified as untracked-and-not-yet-in-B; it was syntax-checked (`node --check`, OK)
   and staged.
4. `git diff --cached --name-only` == exactly `.gitattributes`,
   `mentat/app/contribution-studio.css`, `mentat/app/contribution-studio.html`,
   `mentat/app/contribution-studio.js`, `mentat/app/tests/reconcile-cycle.test.js`,
   `mentat/tools/pocket/mentat-pocket.html` -- 6 files, nothing else. Committed with
   `git commit -F <msgfile>`.

```
 .gitattributes                           |    3 +
 mentat/app/contribution-studio.css       |   15 +
 mentat/app/contribution-studio.html      |   44 +
 mentat/app/contribution-studio.js        |  300 ++
 mentat/app/tests/reconcile-cycle.test.js |   77 +
 mentat/tools/pocket/mentat-pocket.html   | 2284 +++++++++++++++---------------
 6 files changed, 1581 insertions(+), 1142 deletions(-)
```

## STEP P, second pass (on D) -- ALL GREEN

Detached worktree `C:\Users\pgoff\Mentat_verify_d` at SHA D; the two local-only files
copied in again, never staged.

- `mentat/app/vendor/pptxgen.bundle.js` on the fresh checkout: length 460889 (matches the
  original, was 460985 before the fix), sha256
  `4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8` -- MATCH.
- `node --test` -- **108 pass, 0 fail** (reconcile-cycle.test.js now present and counted).
- `python -m unittest` (6 modules) -- **Ran 58, OK**, including the vendor-hash test and
  the same-origin assets test that failed on B.
- Booted `python mentat/app/server.py --port 8832 --read-only` from the clean checkout
  (pid 53932), waited 5s. `/`, `/api/health`, all 30 `index.html` assets, and
  `/contribution-studio`, `/contribution-studio.js`, `/contribution-studio.css` -- **36/36
  responses 200**. Killed pid 53932 (confirmed dead). `git worktree remove --force` --
  confirmed removed (directory gone, not in `git worktree list`).

## Status line counts

Before this session: 282. After commits A + B: 244. After commit D: 240. (The residual
240 lines are other lanes' uncommitted work in the same dirty tree -- untouched throughout,
as instructed.)

## Skipped / not done

- No `.gitattributes` rule or missing-file fix was attempted on the first STEP P failure
  itself -- that decision was deferred to the coordinator's ruling, which specified
  commit D exactly as executed above.
- Files left uncommitted by design: everything outside the two file lists (the other
  lanes' dirty-tree work, 240 status lines' worth) was never staged or touched.
- `commit_A_msg.txt`, `commit_B_msg.txt`, `commit_D_msg.txt` (scratch commit-message
  files written into this folder to satisfy the "write with the Write tool via a script,
  LF endings" instruction) are moved out before this receipt's own commit -- see below.
