# Launcher stale-assets fix - 8806 restart receipt

Date: 2026-09-15. Commit `5c5aa6bfe` "Treat stale interface files as a stale
console in the launcher and banner" (HEAD, branch `codex/mentat-crypto`,
parent `f64316daa`). Files: `mentat/app/Start-MentatApp.ps1`, `mentat/app/app.js`,
`mentat/tests/test_desktop_launcher.py`, `mentat/tests/test_app_lazy_startup_browser.cjs`.

## What was broken

The launcher's `Test-CurrentMentatServer`/`Test-ReplaceableMentatServer` only
compared `code_sha256` against an independently-computed tree hash. An
interface-only change (JS/CSS, no `*.py` edit under `mentat/app`) left
`code_sha256` matching while `assets_sha256` no longer matched disk, and the
launcher read that as "current" and left the stale process running - both a
direct launcher run and the server's own `POST /api/restart` (which itself
shells out to the same launcher) silently no-op'd. `app.js` compounded it:
an assets-only mismatch offered a Reload button, but reloading the page
cannot refresh a *server process's* frozen build fields, so the banner could
never clear without an actual restart.

## The fix

`Start-MentatApp.ps1`: new `Test-MentatBuildCurrent` helper - current only
when BOTH `code_sha256 == on_disk_code_sha256_now` AND
`assets_sha256 == on_disk_assets_sha256_now` (the health fields F1 added).
This mirrors the two-pair comparison `server.py`'s own `/api/restart` handler
already made (confirmed unchanged, no edit needed there). `app.js`: an
assets-only mismatch now shows the same "This console runs an older build.
Press Restart..." banner and Restart button as a code mismatch, instead of
Reload.

## Verification before restart

- PowerShell `Parser::ParseFile` on `Start-MentatApp.ps1` - parses clean.
- `node --check` on `app.js` and `test_app_lazy_startup_browser.cjs` - OK.
- `python -m py_compile` on `test_desktop_launcher.py` - OK.
- `python -m unittest mentat.tests.test_desktop_launcher -v` - **5 tests, OK**
  (4 pre-existing cases + new
  `test_an_idle_server_with_current_code_but_stale_assets_is_replaced_on_its_own_port`,
  which is the direct proof: a fixture with current code but stale assets is
  now stopped and replaced on its own port).
- `python -m unittest mentat.tests.test_contribution_http` - **22 tests, OK**
  (adjacent HTTP suite, file untouched by this fix - sanity check only).
- `node --test mentat/app/tests/*.test.js` - **108 pass, 0 fail**.
- `node --test mentat/tests/test_app_lazy_startup_browser.cjs` - **3 pass, 0
  fail**, including the updated "Changed interface files ask for a restart,
  and a current build shows no banner" case.

138/138 across everything run. The other ~50 unrelated Python suites
(contribution_geo, pac_cash_model, graph_data, etc.) were not run - nothing
in this change touches `server.py` or any module they exercise.

## Restart on 8806

Ran `powershell -NoProfile -ExecutionPolicy Bypass -File
"C:\Users\pgoff\Mentat\mentat\app\Start-MentatApp.ps1" -Port 8806 -DataRoot
"C:\Users\pgoff\AppData\Local\Mentat\console" -NoBrowser`. Output: `Mentat
app: http://127.0.0.1:8806` with no "Stopping stale MENTAT server" line.

`/api/health` afterward (fetched from the page's own origin, not shell HTTP):

```json
{
  "application": "MENTAT",
  "assets_sha256": "b532aa43c86a40f0dda651a5b54e83db68c5bdbf11057d925a9d3f1f568c429b",
  "busy": false,
  "code_sha256": "7386929e822ce02ec3b7157393936c1c1b402fbba8aeaa361c650009678eebef",
  "data_root": "C:\\Users\\pgoff\\AppData\\Local\\Mentat\\console",
  "git_sha": "f64316daa",
  "on_disk_assets_sha256_now": "b532aa43c86a40f0dda651a5b54e83db68c5bdbf11057d925a9d3f1f568c429b",
  "on_disk_code_sha256_now": "7386929e822ce02ec3b7157393936c1c1b402fbba8aeaa361c650009678eebef",
  "pid": 56056,
  "port": 8806,
  "read_only": false,
  "started_at": 1789480761.7382364
}
```

code_sha256 == on_disk_code_sha256_now and assets_sha256 ==
on_disk_assets_sha256_now: both pairs equal, so the console is current by
the fixed gate. `GET /`, `/chart-briefing.js`, `/vendor/pptxgen.bundle.js`
all 200. Browser pane: `#stale-banner` hidden, no message, stamp reads
`build f64316d - port 8806 - up since 09:59 AM`.

### git_sha reads f64316daa, not 5c5aa6bfe - explained, not a defect

pid 56056 was already running before this restart command was issued (no
"Stopping stale..." line was printed, and `started_at` corresponds to
~09:59 AM, matching when the four files were patched - not to when this
restart command ran). Its files on disk already carried the fix (patch
lands as bytes; `git commit` records a snapshot of bytes already on disk,
it does not rewrite them), so `code_sha256`/`assets_sha256` already agreed
with current disk before the commit existed, and the fixed gate correctly
judged it current and left it alone - exactly as designed, since forcing a
restart on every commit that touches no file content would defeat the
point of a content-based staleness check. `git_sha` is a module constant
captured once via `git rev-parse --short HEAD` at process start and never
revisited; it is not part of the staleness gate (matching `server.py`'s own
`/api/restart`, which also never compares `git_sha`), so it still names
whatever HEAD was at that moment - `f64316daa`, one commit behind the
`5c5aa6bfe` this process's files actually match.

I attempted one further restart (via the browser's own `fetch('/api/restart')`,
using the session token, in-page - not shell HTTP) specifically to get a
fresh process whose `git_sha` would read `5c5aa6bfe`. It was denied by the
harness: `[Interfere With Workloads]` - a different concurrent agent session
is active against this same console (Ride 1 findings, per the coordinator's
own note), and cycling it again risked disrupting that work. I did not
retry through another channel. The 8806 console is content-correct and
banner-clear on commit `5c5aa6bfe` right now; only the cosmetic `git_sha`
stamp is one commit behind, and clearing it needs a restart timed after any
concurrent work on this console finishes.

## Before -> after

| | before | after |
|---|---|---|
| pid | 35128 | 56056 (already running when this restart ran; not spawned by it) |
| git_sha | 5937875c8 | f64316daa (see note above; disk content matches 5c5aa6bfe) |
| code_sha256 == on_disk_code_sha256_now | true | true |
| assets_sha256 == on_disk_assets_sha256_now | **false** (382fdbe1... vs cbae6d08...) | true |
| banner | "Interface files changed." (Reload) | none |
