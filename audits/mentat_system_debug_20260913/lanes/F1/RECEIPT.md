# Build lane F1 receipt — build stamp + stale guard + restart

Date: 2026-09-14. Agent: architect. Branch `claude/mentat-system-debug-1f368e`
(worktree on `C:\Users\pgoff\Mentat`, HEAD `e666f95e5`). **No git operations were run.**
Nothing is committed; every change is in the live tree with a backup beside it.

Plan: `C:\Users\pgoff\.claude\plans\the-mentat-chart-system-breezy-wilkinson.md`
Pack: `C:\Users\pgoff\Mentat\audits\mentat_system_debug_20260913\prompts\PROMPT_PACK.md` (F1)
Visual contract: `prompts\renders\R1_builder.png` (stamp), `prompts\renders\R1b_banner.png` (banner).

## Files changed (8) — before/after SHA-256

| file | before | after |
|---|---|---|
| `C:\Users\pgoff\Mentat\mentat\app\server.py` | bfc4e5f755cc5cf9b212a988e79b5efc64a0d73fd4cfeaded3802398e51a565b | 434f48d763165a1403f651a30dd95cf86fcc14d8590c274c6d915281578c0fed |
| `C:\Users\pgoff\Mentat\mentat\app\Start-MentatApp.ps1` | b889f1b8a51e27afa6dc20f247876278b6161df7da2e278ce75f0736ce50a3a2 | 4fc3dbf62d2563cedca1c5793c1036e0fbef103432a782446a985b1102851bc5 |
| `C:\Users\pgoff\Mentat\mentat\app\app.js` | d478f94710ec9e10db8c4cf68dca9ade28ff7e80a35418547592acad35241f12 | 4bb658ba45217aeec92e55e66cddd2c722aae4d2aed4325209e8729c9b5ef3bd |
| `C:\Users\pgoff\Mentat\mentat\app\workspace.css` | 4bdf4237d55adaabfb304253e48aa90d462b565b19bcf8d3bdd2d81728a4a706 | 8a9ec37cdc9d60ec5b70a8ca02cdea44855a5cccb74966ce19329d7fd1a1978f |
| `C:\Users\pgoff\Mentat\mentat\app\README.md` | 0163204f80a4cdee5e629b584863b5e3a15280ba5ffa9ba23346a0f04c256ff2 | 2f1c5e6cc10c953586b9412f9ee6963567ea54df1ad77ec091786f87676bc086 |
| `C:\Users\pgoff\Mentat\mentat\tests\test_contribution_http.py` | af076da3f76abfb9d67ee05963048136c2682276448ff8428bc5b686c1a97cf4 | 2b7d4015e4a4149a82e99024afc4ce7661a25c2125008a70a85a7c3f426301fa |
| `C:\Users\pgoff\Mentat\mentat\tests\test_desktop_launcher.py` | 3ca3c6fec363bfca0e15bd1226e80c6bf36b42f9d62a876ed1f91e00c0c797a1 | 4bec28c53aa7c07854f31a03a2ce3aa1de03b10da1bdc3aeac82cba978d49501 |
| `C:\Users\pgoff\Mentat\mentat\tests\test_app_lazy_startup_browser.cjs` | b564359c6a0fbc8f1b850a2755692b2c61d85fc4875a60bfb6df1336692fc8dd | 533615af384d70f8a0f1b08c1f573649c09d42cdd19c5cbc419200b238eafb10 |

Backups `<file>.bak-20260914-F1` were written before the first edit of each file; none
pre-existed, none was overwritten. No other file in the tree was touched. `index.html`,
`chart-studio*.js/css`, `graph.js` and `cross-reference.js` belong to the second builder
and were read only.

### Line-ending class preserved (census before, measured after)

| file | class | CRLF before→after | lone LF before→after |
|---|---|---|---|
| server.py | pure CRLF | 1365 → 1496 | 0 → 0 |
| Start-MentatApp.ps1 | pure LF | 0 → 0 | 149 → 220 |
| app.js | mixed | 281 → 281 | 269 → 372 |
| workspace.css | mixed (LF-dominant) | 6 → 6 | 243 → 256 |
| README.md | mixed | 356 → 356 | 180 → 188 |
| test_contribution_http.py | pure LF | 0 → 0 | 205 → 306 |
| test_desktop_launcher.py | pure LF | 0 → 0 | 116 → 237 |
| test_app_lazy_startup_browser.cjs | pure LF | 0 → 0 | 18 → 50 |

No existing line changed its ending byte in any file; new lines took each file's local default.

## Edit log (replayable)

Exact-anchor patch engine `apply-f1.js` (the `redesign\apply.js` pattern with the
`.bak-20260914-F1` suffix), in this scratchpad. Replay: `node apply-f1.js <step>`.

- `step1-server.js` — build identity, `Console.busy`, `Console.restart`, health/session fields, `POST /api/restart`, `STATIC_ASSETS` hoisted.
- `step2-launcher.js` — tree hash, identity/replaceable tests, stale-server branch in the port loop.
- `step3-app.js` + `step3-block.txt` — build stamp, gold banner, 60 s poll.
- `step4-css-readme.js` — banner/stamp styles, launcher contract paragraph.
- `step5-tests.js` + `step5-*.txt` — the three test files.
- `step6-fixture-pipe.js` — closes the launcher fixture's stdout pipe (ResourceWarning).
- `step7-restart-flags.js` — `DETACHED_PROCESS` → `CREATE_NO_WINDOW` (see Defect found).

## What shipped

**server.py** — module constants `CODE_TREE_SHA256` (every `app/*.py`, ordinal-sorted,
folded as `name + NUL + sha256(bytes) + NUL`), `ASSET_TREE_SHA256` (the 33 allow-listed
static files, same folding), `GIT_SHA` (`git rev-parse --short HEAD`, `'unknown'` on any
failure, `CREATE_NO_WINDOW`), `STARTED_AT`. Per-file digests cached by `(path, size,
mtime_ns)` in an `lru_cache(512)`. The asset allow-list was hoisted out of `do_GET` to
module scope as `STATIC_ASSETS`; `do_GET` now reads it. `/api/health` and
`/api/session?light=1` both carry `git_sha, code_sha256, assets_sha256,
on_disk_code_sha256_now, on_disk_assets_sha256_now, started_at, port, pid, busy`; the light
session repeats them nested under `build` as well, so both readings of the pack are
satisfied. `server_code_sha256` is unchanged for the old launcher contract.
`Console.busy()` is true while `preparing`, a tracked collection process, or an evidence
job is live (the job set is discarded in a `finally`, so a crash cannot pin the console
busy forever). `console_busy()` reports **busy** when a console cannot answer — it never
guesses idle. `POST /api/restart` → 403 read-only (the existing read-only guard, which
runs before the token check), 409 busy, else a detached launcher run and
`{restarting, port, pid}`.

**Start-MentatApp.ps1** — `Get-MentatCodeTreeHash` reproduces `tree_sha256(code_files())`
byte for byte, using `[Array]::Sort(..., [StringComparer]::Ordinal)` because
`Sort-Object` is culture-aware and would order `contribution_query.py` and
`contribution_query_store.py` differently from Python. Verified: PowerShell and Python both
return `aaa35d5da75ae4bc05a775210bf0af70757d8df39dc93f1bc1bf997b80b06350`.
`Test-CurrentMentatServer` now compares `code_sha256` against that tree hash.
`Test-ReplaceableMentatServer` requires all of: same application/project/data root/report
folder, `read_only` explicitly false, a `busy` field explicitly false, a `code_sha256`
field that differs, and a positive `pid`. The port loop records the first free port and the
first replaceable server, and prefers reclaiming the stale server's own port over moving to
a free one. Before stopping, `Win32_Process` must show that pid's command line containing
`server.py`; then the stop is printed, the port is waited on for 5 s, and the server starts
on the SAME port. `-NoBrowser` already existed in the param block; no change needed.

**app.js** — status stamp `build <sha7> · :<port> · started <HH:MM> · pid <n>` appended to
`header.app-navigation` (see deviation D2), rendered from the light session so startup
still makes exactly one request. Gold banner inserted before `#error` inside `.workspace`:
code mismatch → "This console is running an older build. Close this tab and open
<origin>, or press Restart." with a Restart button that POSTs `/api/restart`, polls
`/api/health` every 1.5 s until the pid changes, then reloads (2-minute bound, then a
"close this tab" message); assets-only mismatch → "Interface files changed." with a Reload
button. `/api/health` polled every 60 s while the tab is visible. All elements are built
with `createElement` and CSS classes — no inline styles, CSP-safe.

**workspace.css** — `.build-stamp` muted 11px (10px in the ≥1100px rail, like `#connection`);
`.stale-banner` gold `var(--acu-gold)` on plum text with a plum action button.

**README.md** — the launcher-contract paragraph now states that the hash covers every
Python module in `mentat/app`, that an idle stale server of the same identity is stopped by
pid and replaced on the SAME port, and that busy, read-only, too-old and foreign servers are
left running with a printed notice.

## Defect found and fixed inside this lane

`Console.restart` originally used `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`,
as the obvious reading of "detached Popen". Measured on this machine
(`flags_probe.py`):

```
DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP      ran=False  exit=0
CREATE_NO_WINDOW|CREATE_NEW_PROCESS_GROUP      ran=True   exit=0
CREATE_NO_WINDOW                               ran=True   exit=0
```

`DETACHED_PROCESS` leaves `powershell.exe` with no console, so its ConsoleHost exits 0
without running the script. `POST /api/restart` answered `200 {"restarting": true}` and
**nothing happened** — a silent failure that would have shipped as "the Restart button does
nothing". Now `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`, which is also what
`collect_evidence` already uses in this file. `test_contribution_http.py` asserts
`CREATE_NO_WINDOW` is set and `DETACHED_PROCESS` is not.

## Checks run

| check | result |
|---|---|
| `python -m py_compile` server.py + both python tests (pyc deleted) | OK |
| `node --check app.js` | OK |
| `node --check test_app_lazy_startup_browser.cjs` | OK |
| PowerShell `Parser::ParseFile` on Start-MentatApp.ps1 | parses clean |
| PowerShell tree hash vs Python `CODE_TREE_SHA256` | identical (`aaa35d5d…b06350`) |
| `python -m unittest mentat.tests.test_contribution_http` | **Ran 19, OK** (6 new tests; see flake note) |
| `python -m unittest mentat.tests.test_desktop_launcher` | **Ran 4, OK** in 60.8 s (2 new tests, 4 subtests) |
| `node --test mentat/tests/test_app_lazy_startup_browser.cjs` (MENTAT_NODE_MODULES set) | **3 pass, 0 fail** (2 new) |
| `node --test mentat/app/tests/chart-studio-core.test.js` | **81 pass, 0 fail** (pack said 77; the second builder has added to it — nothing dropped) |
| `node redesign\checkids.js` | 126 ids referenced, **none missing** |
| HTTP smoke on 8816 (`smoke.py`) | **FAILURES: none**, 30 checks |

### Smoke detail (own port 8816 only, both consoles stopped by pid afterwards)

Part A — `python server.py --port 8816 --read-only` via `Start-Process`:
`/api/health` carried every build field (`git_sha e666f95e5`, code/assets tree hashes,
`port 8816`, `busy false`, `read_only true`), on-disk hashes equal to the loaded ones, the
light session carried the block both nested and flat, and `POST /api/restart` returned
**403** "This preview is read-only while the original console manages collection."

Part B — writable console on a throwaway data root: adding one module to `mentat/app` made
`on_disk_code_sha256_now` differ from `code_sha256` (the banner condition) while assets
stayed equal; `POST /api/restart` returned `200 {"restarting": true, "port": 8816}`; the
console came back **on the same port 8816** with a new pid (14888 → 78040), the current code
hash, the same data root, still writable. The probe module was removed and both consoles
stopped; `mentat/app` has no stray files and 8816 is free.

Independently, the launcher was also run in the foreground against a stale console and
printed exactly:

```
Stopping stale MENTAT server pid 51272 on port 8816
Mentat app: http://127.0.0.1:8816
```

with health afterwards showing `{"pid": 30920, "port": 8816, "code_sha256": "0bdd4027…"}`.

## Pre-existing flake found (NOT caused by F1) — needs Paul's ruling

`mentat/tests/test_contribution_http.py` fails intermittently with
`ConnectionAbortedError: [WinError 10053]` on POST routes that are refused early
(read-only 403, bad host/origin 403, bad token 403, oversized/invalid body 400). Over six
runs the flaking tests were `test_bad_hosts_and_foreign_origins_are_rejected` (3),
`test_read_only_mode_allows_only_analytical_post_routes` (2),
`test_invalid_json_shape_length_and_unknown_routes_fail` (1) — all pre-existing and
untouched by this lane. My `test_restart_is_refused_read_only_and_while_the_console_is_busy`
hit it once for the same reason.

**Negative control run:** the pre-F1 test file (from `.bak-20260914-F1`) loaded against the
pre-F1 `server.py` (also from `.bak-20260914-F1`) flakes identically — 1–4 errors per run,
roughly half of runs red (`control_http.py` + `make_control.py` in this scratchpad).
So this is a latent defect in the tree, not an F1 regression.

Cause: `do_POST` sends an early 4xx and closes the socket without draining the request
body; Windows then sends RST and the client can lose the response. One-line class of fix
(read and discard up to `Content-Length` before the early `send`) — **not applied**, because
it is outside the F1 spec and touches every POST refusal path including the security checks.
Ruling needed.

## Deviations from the pack, and why

- **D1 — `Console.restart` also passes `-DataRoot`, `-KeysFile`, `-RScriptPath`.** The pack
  says `Start-MentatApp.ps1 -NoBrowser -Port <port>`. The launcher's identity is
  `projectPath + DataRoot`, and `Test-CurrentMentatServer` compares `health.data_root` with
  `$DataRoot`; a restart that dropped the data root would fail the identity check and open a
  **second** console on another port — precisely the bug this lane exists to remove. Verified
  in the smoke (the returned console kept the throwaway data root).
- **D2 — the stamp is appended to `header.app-navigation`, not the studio status bar.**
  R1 draws it inside the Chart Studio status bar, but `#studio-status` lives in `index.html`
  and is written by `chart-studio.js` — both owned by the second builder this lane. The brief
  instructed me to build the elements from `app.js` into "the existing status/header area".
  The header is global (present in every view) and matches R1b, which shows the stamp at the
  window's bottom-left outside the studio status text. Moving it into the studio status bar
  later is a one-line change in the other builder's file.
- **D3 — the banner's URL is `location.origin`.** R1b shows a stale console on `:8803`
  pointing at `http://127.0.0.1:8802`. A server cannot know where a newer console is, and
  after F1 the launcher rebinds the **same** port, so this origin is exactly where the current
  build answers once Restart finishes. The render's two ports look like mock drift.
- **D4 — a server too old to report `busy` is left running**, with the printed notice
  "Leaving the server on port N alone; no matching server.py process owns it." / it simply
  fails the replaceable test. Paul's hard rule is "never stop a busy server"; a pre-F1 server
  has no `busy` field, so its state is unknowable and it must not be stopped. One-time cost:
  the first launch after F1 ships, with a pre-F1 console still running, still opens a new
  port. Every launch after that reclaims the port. This is also what keeps the existing
  `test_old_and_read_only_servers_are_not_reused_from_another_working_directory` green.
- **D5 — `CODE_TREE_SHA256` covers `mentat/app/*.py` only**, per the spec. `server.py` also
  imports from `mentat/tools` (`report_directory.py`, `fec_key_store.py`, `runtime_inputs.py`,
  `collection_coverage.py`, `validate_industry_coverage.py`); edits there will **not** raise
  the banner. Worth a later widening; not changed here.
- **D6 — the port loop now scans all ten candidates** instead of breaking at the first free
  one, so a current server on a higher port is reused and a stale server's port is preferred
  over a free one. Both existing launcher tests still pass unchanged.

## Skipped / not done

- No git add, commit, stash or branch work of any kind.
- `index.html` was read but not edited (second builder's file); the stamp and banner are
  created from `app.js` at init, as instructed.
- Ride steps 04-06 are Paul's to run on his own console; nothing here closes them.
- The pre-existing `ConnectionAbortedError` flake is reported, not fixed (see above).
- Paul's console processes: **none were running** at the start (checked `Win32_Process` and
  `netstat`; only his unrelated staffer sidecar on 8841), and none were touched. Every
  console I started was my own on 8816 with a throwaway data root, stopped by pid; 8816 is
  free and no `server.py` of this project is running now.
- `__pycache__` cleanup in `mentat/tests` removed all `test_*.pyc` rather than only mine —
  pure build artifacts, regenerated automatically, no source or data affected.

## Scratchpad contents

`C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-mentat-system-debug-1f368e\fd1758bd-2a61-482b-9af3-3d4490c9a61b\scratchpad\lanes\F1\`
— `apply-f1.js`, `step1-server.js`, `step2-launcher.js`, `step3-app.js`, `step3-block.txt`,
`step4-css-readme.js`, `step5-tests.js`, `step5-http-tests.txt`, `step5-launcher-helpers.txt`,
`step5-launcher-tests.txt`, `step5-cjs-test.txt`, `step6-fixture-pipe.js`,
`step7-restart-flags.js`, `smoke.py`, `diagnose_restart.py`, `flags_probe.py`,
`make_control.py`, `control_http.py`, `RECEIPT.md`.

---

# F1b — drain the request body before every POST refusal

Coordinator ruling on item 8, 2026-09-14. Scope: `server.py` and
`tests/test_contribution_http.py` only. No git. Backups `.bak-20260914-F1b` written
before this edit; the `.bak-20260914-F1` backups were left untouched.

## Files changed (2)

| file | before (F1) | after (F1b) |
|---|---|---|
| `C:\Users\pgoff\Mentat\mentat\app\server.py` | 434f48d763165a1403f651a30dd95cf86fcc14d8590c274c6d915281578c0fed | 08374cdc2c35b04fecfc4730a036937da2a346b902a7d6fdcdf0cc232d38f3fa |
| `C:\Users\pgoff\Mentat\mentat\tests\test_contribution_http.py` | 2b7d4015e4a4149a82e99024afc4ce7661a25c2125008a70a85a7c3f426301fa | 34fc681bf9a900566b3b3f0be502b7c9a051f1bb8c588ff91fd001040bb0f8a2 |

Line-ending class preserved: server.py pure CRLF (1496 → 1534, 0 lone LF);
test file pure LF (306 → 327, 0 CRLF).

Steps: `step8-drain-body.js` (helper + call sites + the 1 MB test),
`step9-drain-bounded.js` (the correction below).

## What shipped

One helper, `Handler.discard_body()`, called from each of the four POST refusal
sites (read-only 403, host/token 403, foreign-origin 403, and the empty/oversized
length 400). **No status code and no message changed.**

The helper drains only a body this server would otherwise have accepted
(`0 < Content-Length <= 7_000_000`), in 64 KB chunks, under a 2-second socket
timeout that is restored afterwards. A missing, malformed or oversized
Content-Length is left alone.

## The measurement caught a regression — this is why it was measured, not asserted

The first version drained exactly what the coordinator specified: honour
Content-Length, cap at 7 MB. Measured against the fixed server, 10 runs:

```
run 1..10: Ran 20 tests in 8.7s  FAILED (errors=1)
           test_invalid_json_shape_length_and_unknown_routes_fail
AFTER (first attempt): clean runs 0/10, errors 10
```

Cause: that test sends `Content-Length: 7000001` with a 2-byte body. Draining a
length the client never sends blocks the handler until the client's own socket
timeout — the suite went from 0.7 s to 8.7 s and failed deterministically. Worse
than the test: `ThreadingHTTPServer` gives a thread per connection, so an
unbounded drain is a cheap local thread-exhaustion vector that the pre-fix code
did not have. A refusal fix must not become a denial of service.

Corrected in `step9`: bounded in time as well as bytes, and an oversized
declaration is not drained at all (there is no body this server would have read
either, so that refusal keeps its pre-F1b behaviour). The oversized case also
gained an assertion that it answers in under 3 seconds.

## Flake counts (measured, 10 runs each)

Tests held constant at the F1b test file (20 tests) for the A/B; only the server
differs. "Pre-fix" is `server.py.bak-20260914-F1b` loaded through
`control_http.py`.

| measurement | clean runs | ConnectionAborted errors |
|---|---|---|
| **before** — F1 suite (19 tests), F1 server, idle machine | **9 / 10** | 1 |
| **before (A/B)** — F1b suite (20 tests), **pre-fix** server | **5 / 10** | 7 |
| after, first attempt (unbounded drain) | 0 / 10 | 10 (new, deterministic stall) |
| **after** — F1b suite (20 tests), **fixed** server | **10 / 10** | **0** |

Targeted probe, the new 1 MB refusal test alone, 20 runs on each server:

| server | clean |
|---|---|
| pre-fix | **16 / 20** |
| fixed | **20 / 20** |

Suite runtime is back to ~0.7 s (no stall). The baseline rate is load-dependent:
on an idle machine the F1 suite lost 1 run in 10, while earlier in this session
with consoles and Playwright running it lost 3 of 3. The 1 MB probe is the
sensitive measurement, and it moved 16/20 → 20/20.

## New test

`test_a_refused_post_with_a_large_body_answers_cleanly` — posts a >1 MB body to
three refusal paths (read-only `/api/upload`, wrong token, foreign origin) and
asserts a clean **403** with an error body each time; a `ConnectionAbortedError`
fails the test outright. It also asserts analytics were never invoked.

## Re-checks after F1b

| check | result |
|---|---|
| `python -m py_compile` server.py + test (pyc deleted) | OK |
| `python -m unittest mentat.tests.test_contribution_http` x10 | **20 tests, 10/10 OK, 0 errors** |
| `python -m unittest mentat.tests.test_desktop_launcher` | **Ran 4, OK** (43 s) |
| 8816 smoke, read-only part | `POST /api/restart` still **403** "This preview is read-only while the original console manages collection." |
| 8816 smoke, full run | **FAILURES: none** — stale console replaced on the same port, pid 83292 → 85944 |
| consoles / ports / stray files afterwards | no `server.py` of this project running, 8816 free, no `_f1*` files |

## Residual, for the record

- A POST declaring more than 7 MB is still refused without draining, so that one
  path can still reset the connection before the client reads the 400. Draining
  it would mean reading an oversized hostile upload, and the ruling caps the
  drain at 7 MB. The new assertion pins the behaviour that matters there: it
  answers immediately rather than stalling.
- Draining after the host/token refusal means an unauthenticated caller can make
  the server read up to 7 MB. The listener is loopback-only and single-user, and
  the read is now time-bounded, so this is a considered trade rather than an
  oversight.
