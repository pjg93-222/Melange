# Staffer live surface — next steps (2026-09-05)

Written by the graph-consolidation-identity session at Paul's request ("create a markdown of next steps and then stop"). Everything below is in the LIVE tree, uncommitted, with byte-exact backups under `audits\staffer_live_runtime\backups\`. No git commands were run by this lane.

## Where things stand

- The sidecar (`fec\surfaces\staffer_live_server.py`, port 8841) is running the NEW code (restarted 16:32:57Z; the restart's origin was under investigation when the session stopped — see open question 1). Page verified in the browser: no console errors; route Gordon Holzberg -> Stephanie Belk renders as a cost-1 current coworker, user-confirmed, both endpoints labelled on the map.
- Scheduled task `MelangeStafferLiveSidecar` is LIVE: logon +2 min and every 30 min, Priority 4, runs `fec\surfaces\staffer_live_watchdog.ps1` (log `audits\staffer_live_runtime\watchdog.log`). It only launches when nothing listens on 8841 and never stops anything.
- Repin runner `fec\surfaces\repin_staffer_live.py --wait --execute` was launched by Paul; it is polling for `staffer_social_network_20260904_v5_verification` and will repin + restart the sidecar only when that receipt passes. Status: `audits\staffer_live_runtime\repin_wait.stdout.log`.
- The crawl completed 18,618/18,618 at 16:24Z. The other lane's finishing chain halted at its verifier gate on 18 `SOURCE_CONFIRMED_MISSING_FIELDS` rows; Paul ruled (12:40 local) to re-crawl those 18 through the browser path, verifier untouched. That lane ("Melange long-form audio integration" session) owns the chain, watchdog, crawler and dashboard section.
- Full README test suite after the fix workflow: 197 passed, 1 failed (`test_staffer_identity_web.py::test_live_sqlite_migrates_in_place_on_open` — the test asserts on the live database's row values, which changed the moment the migrated schema went into use; the fix is a test rewrite, see step 1).

## Landed today by this lane (uncommitted)

| Area | Files | What |
|---|---|---|
| Routing | `staffer_routing.py`, `test_staffer_routing.py` | User statements of current employment stand until superseded (the Sept 4 statement had lapsed within hours); direct-edge check before the effort-capped search; timeout budget reported; `prefer_current` implemented as documented |
| Identity loop | `staffer_identity_web.py`, `tests\surfaces\test_staffer_identity_web.py` | Progress no longer reset to `queued` on every rebuild; deterministic reference failures terminal for 30 days; stray exceptions recorded; `checked` = terminal families only; seeds at priority 300; per-family 120 s budget; stale `checking` rows reclaimed; sqlite migrated in place (backward compatible) |
| Identity provenance | `staffer_identity_auto.py`, `staffer_identity_resolution.py` + tests | Automatic groups name their real proof kind (records vs references); `automatic_inferred_merges` computed; one source-id vocabulary; candidate retrieval by first+last so middle-initial pairs are considered (merge rules unchanged) |
| Service/server | `staffer_live_service.py`, `staffer_live_server.py`, `staffer_people_graph.py` + tests | Provenance notes by proof kind; freshness computed per request; people-only caption totals; institution ids refused by `/api/staffer-person`; malformed `limit` -> 400; deterministic people projection with `bounds.truncated`; `person:lda:` ids resolve |
| Browser surface | `staffer_live\staffer-live.js`, `staffer-route.js`, `README.md` | Route participants labelled; labels gated at the overview fit; hover cleared on pointer leave; stale zoom bases reset; `isPerson` = person only; honest captions |
| Ops | `staffer_live_watchdog.ps1`, `repin_staffer_live.py`, `test_repin_staffer_live.py`, task `MelangeStafferLiveSidecar` | Autostart/watchdog and the v5 repin runner |
| Builder | `audits\staffer_network\build_staffer_social_network.py` | Glassbox emit fixed (`-Kind/-Summary/-MetadataJson`); do not touch again until v5_verification exists |

## Next steps, in order

1. **Fix the one failing test** (this lane, ~15 min). Rewrite `test_live_sqlite_migrates_in_place_on_open` to migrate a COPY of the live database and a synthetic old-schema database; assert columns/tables and idempotence, never live row values. Re-run the 12-file suite; expect all green.
2. **Review follow-ups from the adversarial pass** (this lane, small, all backed up):
   - `staffer_identity_web.py allowed()`: robots.txt 408/429 should be transient, not a 30-day terminal outcome.
   - `staffer_routing.py`: cache hits must not overwrite `search_elapsed_ms` (add `cache_hit`); `coworkers()` should carry `prefer_current` on its unknown_person/search_limited returns; `min_hop` bound should exclude disabled hop classes; the timing test should use an injected clock.
   - `staffer_live_server.py summary()`: four coverage keys were added with no declared fix or test — pin them with a test or remove them.
   - `staffer-live.js` line ~104: a late edit (16:31:09Z, author not identified) flipped one line's CRLF to LF and added the coverage-key rendering; restore the CR, keep the hunk.
   - `staffer_identity_auto.py`: decide whether `EVIDENCE_VERSION` must be bumped for the changed group-record shape (only if it keys nothing outside this surface).
3. **Restart the sidecar once more after step 2** (Paul; the classifier blocks process stops from this session):
   ```powershell
   $rt='C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_live_runtime'; $p=(Get-Content "$rt\server.json" -Raw | ConvertFrom-Json).pid; $c=(Get-CimInstance Win32_Process -Filter "ProcessId=$p").CommandLine; if ($c -match 'staffer_live_server\.py') { Stop-Process -Id $p -Force; Start-Sleep 3; & 'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\surfaces\start_staffer_live.ps1' } else { "PID $p is not the sidecar: $c" }
   ```
   Then the proof (expect cost 1.0 current_coworker with the box on, 2.0 lobbying with it off):
   ```powershell
   $b='http://127.0.0.1:8841'; $g='person:hill:person:02bbfc2112b340996b60a0298ed05d729707c10137280e2bf70adf7c12e9d273'; $s='person:hill:person:ddf8902c456649265e55c8dd25306592362d23986e7b0fe29cfe0a71b6cc355b'; foreach ($ua in 1,0) { $r=Invoke-RestMethod "$b/api/staffer-route?origin=$g&target=$s&include_user_asserted=$ua&include_review=1&include_historical=1&prefer_current=1"; "user_asserted=$ua -> cost=$($r.cost) rel=$($r.hops[0].relationship)" }
   ```
4. **Let the v5 chain land** (other lane + Paul): the 18-row re-crawl, verifier COMPLETE, finishing chain `--from verify_partial --execute`, dashboard rebuild. The repin runner then fires on its own; check `repin_<stamp>.json` (success) or `repin_halt_<stamp>.json` (rolled back to v4) in `audits\staffer_live_runtime\`.
5. **Commit when Paul lifts the no-git rule.** Everything in the table above plus this document. Suggested grouping: routing/service/surface fixes; identity loop + provenance; ops (watchdog, repin, task registration note); builder emit fix.
6. **Brain update** (Paul applies): append to STATE.md Active workstream:
   `STAFFER LIVE SURFACE (2026-09-05): people-only graph + A* routes + identity loop = fec/surfaces/staffer_live + staffer_live_server.py on 8841, Codex-built, uncommitted. Autostart task MelangeStafferLiveSidecar LIVE (Priority 4; BelowNormal starved powershell startup). Fixes landed uncommitted: user-statement durability + routing follow-ups, identity-loop progress regression + terminal failures + seed priority, provenance labels by proof kind, people-only totals, deterministic projection, label gating; suite 197/1 pending a test rewrite. repin_staffer_live.py polling for v5. Ownership: chain/watchdog/dashboard = audio-integration session; sidecar/routing/assertions/identity loop = this lane.`

## Decisions for Paul (not implemented, by design)

1. **Payroll co-tenure can never be "current"** (`staffer_routing.py from_static` hardcodes `current_evidence=False`), so the only cost-1 edges today are user statements. Candidate rule: both people observed in the latest ledger quarter with overlapping intervals count as current. This is model semantics; ruling needed before implementation.
2. **Identity-loop throughput**: single worker, ~2 lookups/min against 185,893 people, so a full pass takes months. Options: more workers with per-host rate limits, a narrower target set (profiles with candidate duplicates first), or accept it as a slow background hygiene process.
3. **Retracting a user statement**: the Gordon/Stephanie/Greg coworker statement is hard-coded in `staffer_routing_evidence.py:157-162`; there is no UI or file to retract or supersede it. Decide whether it moves into `staffer_user_assertions.json` with a retract action.
4. **The 18 source-incomplete Politico rows**: whether they count as "accounted" if the browser re-crawl also returns empty content (verifier contract question).
5. **Freshness "source stale"** now shows whenever the raw crawl file stops growing for 180 s, which is always true after the crawl completes. Decide whether stale should be suppressed when the receipt reports COMPLETE.
6. **UTC vs local dates** in routing `as_of` (a same-day statement made late evening local is dated "tomorrow" in UTC for a few hours). Harmless now; decide if `as_of` should be local.

## Open questions from this session

1. **Who restarted the sidecar at 16:32:57Z and who edited `staffer-live.js` at 16:31:09Z?** Not this lane's workflow by its own records; the watchdog only launches when the port is dead, and the repin runner only acts on a v5 receipt. Check `watchdog.log` for a "not listening; launching" line near 16:32Z (would mean the old sidecar died) and the peer session's transcript for a `staffer-live.js` edit. The forensics scout was stopped before concluding.
2. **`index.html` was restyled at 02:10 today** (plain-language headings "Start here", "Find an introduction", "Show people from", and an unreferenced `staffer-map-worker.js`). Not from this lane; confirm the author and whether the new controls without handlers (zoom buttons, source filter) are wired.

## Rollback

Every edited file has a timestamped `.bak` beside its repo-relative path under `audits\staffer_live_runtime\backups\`. Restore by copying the backup over the file and restarting the sidecar (step 3). The sqlite migration is additive (new columns with defaults, one new table); old code reads the migrated database without change. The scheduled task can be removed with `Unregister-ScheduledTask -TaskName MelangeStafferLiveSidecar -Confirm:$false`.
