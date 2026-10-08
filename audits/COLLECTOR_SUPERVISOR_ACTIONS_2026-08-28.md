# COLLECTOR SUPERVISOR — ACTIONS TAKEN AND FUTURE STEPS

Date: 2026-08-28
Lane: claude/collector-sentinels-inventory-895b67 (worktree hmm-melange-analysis-6f6786)
Companion record: `audits/COLLECTOR_SENTINELS_INVENTORY_2026-08-28.md` (the full sentinel inventory this
arc began with). Every action below was Paul-ordered in-session; his words are quoted at each gate.

---

## 1. Actions taken (chronological, with receipts)

| # | Time (local) | Action | Receipt |
|---|-------------|--------|---------|
| 1 | ~01:50 | **Collector-sentinel inventory** written, verified (11/11 claim groups), committed | `6f1bedb22`, merged to main on Paul's order ("Merge the branch to main"), mirror in sync |
| 2 | 02:24 | **`MoneyballCollectorSupervisor` re-registered** (Paul: "Re-register the supervisor task so the gates run"). No in-repo registration command exists; recreated from the docstring design: Python 3.12 → the LIVE tree's `fec\collect\collector_supervisor.py`, every 10 min, StartWhenAvailable + WakeToRun. PS 5.1 trap hit: `[TimeSpan]::MaxValue` serializes to a rejected duration — used 3650 d | Task registered `Ready`; first tick 02:25:23 |
| 3 | 02:25–02:26 | First tick relaunched `cnn-deep`; the resumable leg found its range complete and wrote its sentinel 5 s later. Next tick: "2 done, 0 pending" → **GATE-1 entered 02:26:22** | supervisor log |
| 4 | ~02:45 | **All gate-step time caps removed** (Paul: "There should be no cap"). Ten `gate_step`/`spend_guard` caps → `GATE_TIMEOUT` (default `None`); revert dial `GATE_STEP_TIMEOUT=<seconds>`. Wedge detection and plumbing timeouts untouched | `f14fd6429`, merged, mirror in sync |
| 5 | ~02:55 | **Spend caps lifted** (Paul: "Lift the spend caps too"). `B5_GATE_CAP`/`REF_GATE_CAP` defaults `'200'`/`'100'` → `'inf'`; the dry-run estimate and the fail-closed unparseable-estimate guard KEPT (they prove the script runs and print the cost — they are not caps) | `e22ab3e7d`, merged, mirror in sync |
| 6 | 04:26:42 | **GATE-1 timeout incident** (the in-flight tick still carried the old code): the 6000 s cap fired at 7,220 s wall (~20 min monotonic skew, sleep suspected, unproven), killing `weekly_refresh` MID-CHAIN; `audit_full` then failed in 0 s; old code stamped `gate1.done` on a dirty gate. **Self-healed**: the orphaned chain (`run_pipeline`, pid 10372) survived the parent kill and completed its own surfaces + terminal audit. Slow pre-chain phase traced to CPU contention from the contact-inference lane's `lobbyist_associations.py` build (3,400+ CPU-s since 02:53) | supervisor log; brain `4205993` |
| 7 | 04:31–04:35 | **GATE-2 opened**: big5 dry estimate **$118.57** (4,687 chunks; 1,525 cached; 3,162 to score; batch −50%); `--go` SUBMITTED the batch and exited PEND; gate aborted by design ("no double-spend, cache resume"). Retry ticks from 04:36 onward ran the NEW code — log shows `within cap $inf — proceeding` hourly | supervisor log 04:36–06:08 |
| 8 | 04:37→08:36 window | **Twelve sentinels deleted by something outside the repo's code** (the inventory proves no in-repo deleter exists; candidates: a launcher/human session, or OneDrive sync propagating deletions). `fox` read pending → the supervisor entered a fox relaunch loop from 08:36, which BLOCKED the gates (gates require 0 pending). `collector_fox.out` shows each fox pass completing ("~36k urls, 0 member turns") yet `fox.done` never reappearing — consistent with either repeat deletion or `_sentinel()`'s silent `except: pass` swallowing a write failure | log 08:36–09:36; sentinel dir listing |
| 9 | 12:02:16 | **Sentinels restored on Paul's order** ("restore the sentinals"): 14 files rewritten — `fox.done` BYTE-EXACT to its recorded content (`2026-08-28T01:27:10.737351`), the other 13 reconstructed to the second from their observed pre-deletion mtimes; `cnn.done`/`cnn-deep.done` were intact and untouched. All 16 legs these files describe genuinely completed in tonight's 00:57–02:25 sweep, so this restores a true record. ASCII, no trailing newline, matching the producer's write. The six git-tracked sentinels now show as uncommitted modifications vs their committed 2026-08-02 vintage — the same state they were in before the deletion; sentinel contents are runtime state and are deliberately NOT committed | this file; directory listing 12:02 |

## 2. Current state (as of 12:05)

- All 16 sentinels present; live targets (`fox`, `cnn-deep`) both read done.
- The supervisor task is registered and ticking every 10 minutes on fully uncapped code (no time caps,
  no spend ceilings — both Paul-ratified same-day).
- `gate1.done` exists (stamped during the incident); GATE-1 will not re-fire this sweep — acceptable
  because the orphaned chain completed the same work and audited itself.
- The $118.57 big5 batch (submitted 04:35) is ~7.5 h old and almost certainly finished server-side;
  the next GATE-2 retry should COLLECT it, write `big5_llm_opus.json` fresh, and pass the freshness gate.

## 3. Future steps

**Automatic (no action needed — the supervisor drives these):**
1. Next tick: GATE-2 retry → batch collection → `big5_llm_opus.json` fresh → `validate_big5` → the
   pre-registered C retest (freshness-guarded) → reference dry est (uncapped) → `reference --score`
   (the July 6000 s timeout victim, now uncapped — expect it to FINISH this time) → `co_appearance` →
   member desk → combined → `audit_full`.
2. `gate2.done` written ONLY if co_appearance + desk + combined + audit all succeed; then the task
   self-unregisters. If any fail, the flag is withheld and the next tick retries.

**Watch items (this lane monitors while the session lives):**
3. Confirm GATE-2 completes and the task unregisters itself; report the C-retest verdict and the final
   audit tally to Paul.
4. If sentinels vanish AGAIN, that settles the deletion question in favor of an active deleter (vs a
   one-time event) — re-diagnose then, per Paul's "not necessary if they are abiding by the python code".

**Paul-gated (flagged, deliberately not done):**
5. **GATE-1's unconditional `gate1.done` write** (`collector_supervisor.py`, GATE-1 block): a crashed
   refresh still stamps the flag — the same class the C-1 fix closed for GATE-2. Fix = mirror the
   conditional. Twice-observed (2026-07-07 reference timeout; today's incident).
6. **`_sentinel()`'s silent `except Exception: pass`** (`fetch_interviews.py:1136`): a failed sentinel
   write is invisible, which is one of the two candidate mechanisms for today's fox loop. A one-line
   loud log would make the next occurrence diagnosable.
7. **The fox leg collects 0 member turns every pass** (archive ended ~2022; it is excluded from weekly
   refresh for this reason). Whether fox belongs in any future `collector_targets.json` is a sweep-design
   question.
8. **Sentinel-deletion source unknown**: no in-repo deleter exists; candidates are a launcher/human
   session or OneDrive sync. If Paul knows the deleter (his own launcher prep), no action; otherwise
   worth an eye on the next sweep.
9. Dial-catalog registration debt: `GATE_STEP_TIMEOUT` + the `'inf'` cap defaults belong in
   `moneyball-config-and-flags` once the other lane's uncommitted skills-tree edits land.
10. Carried from the manifest arc, unchanged: D-015 cost measurement, the live gate re-measure at
    `022c3c728`, the `build_system_manifest.py:960` duplicate-candidate fix, manifest regeneration.

---
*Provenance: all timestamps from `data\stance\collector_supervisor.log`, `collector_fox.out`, live
process/CIM listings, and directory reads taken in-session; commits named inline. The deletion-window
bound (04:37→08:36) is the gap between the last full-16 directory listing and the first "1 pending"
tick.*
