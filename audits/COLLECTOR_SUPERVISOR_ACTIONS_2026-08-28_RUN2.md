# COLLECTOR SUPERVISOR ARC — DONE / NEXT (RUN 2)

Date: 2026-08-28, ~12:50 local
Lane: claude/collector-sentinels-inventory-895b67
Supersedes-and-extends: `audits/COLLECTOR_SUPERVISOR_ACTIONS_2026-08-28.md` (the 12:05 record; it stands
as written per the frozen-vintage rule — this RUN2 carries everything since, plus the full day's ledger).
Companion: `audits/COLLECTOR_SENTINELS_INVENTORY_2026-08-28.md` (the sentinel inventory).

---

## 1. WHAT HAS BEEN DONE (the whole arc, with receipts)

1. **Collector-sentinel inventory** — every sentinel in the system documented and independently verified
   (11/11 claim groups). `6f1bedb22`, merged to main, mirror in sync.
2. **`MoneyballCollectorSupervisor` re-registered** (no in-repo registration command exists; recreated
   from the docstring design: live-tree script, every 10 min, StartWhenAvailable + WakeToRun). First tick
   completed the `cnn-deep` backfill sentinel in 5 s via resume; GATE-1 entered 02:26:22.
3. **All gate-step time caps removed** (Paul: "There should be no cap") → `GATE_TIMEOUT=None` default,
   revert dial `GATE_STEP_TIMEOUT=<seconds>`. `f14fd6429`, merged, mirrored.
4. **Spend caps lifted** (Paul: "Lift the spend caps too") → `B5_GATE_CAP`/`REF_GATE_CAP` default `'inf'`;
   dry-run estimate + fail-closed unparseable-estimate guard kept. `e22ab3e7d`, merged, mirrored.
5. **GATE-1 timeout incident, self-healed** — the in-flight old-code tick killed `weekly_refresh`
   mid-chain at 7,220 s (~20 min monotonic skew); `audit_full` crashed in 0 s; old code stamped
   `gate1.done` dirty. The orphaned chain survived and completed its own surfaces + terminal audit.
   Contention source identified: the contact-inference lane's build (3,400+ CPU-s).
6. **Sentinel deletion + restoration** — 12 of 16 sentinels deleted 04:37→08:36 by an actor outside the
   repo's code (no in-repo deleter exists — inventory-proven; source unresolved: launcher/human session
   or OneDrive sync). Effect: fox relaunch loop from 08:36, gates blocked. **Restored 12:02:16 on Paul's
   order** — `fox.done` byte-exact, 13 reconstructed to the second from recorded pre-deletion mtimes; all
   16 legs genuinely completed in the 00:57–02:25 sweep, so the record is true. Gates unblocked; 16/16
   still present at last check (no re-deletion → no evidence yet of an active deleter).
7. **big5 batch diagnosed: NEVER SUBMITTED, $0 SPENT.** Evidence (read-only, scout-verified):
   the PEND file every successful submission writes (`big5_llm_batch_opus.json`, `big5_llm.py:264,271-272`)
   does not exist; artifact + score cache byte-untouched since **July 7**; the submission call
   (`client.messages.batches.create`, `big5_llm.py:270`) has **no try/except**, so any API error crashes
   the script before the PEND write — and `gate_step` keeps only the last *stdout* line, discarding the
   stderr traceback every 10 minutes since 04:35. The "$118.57 proceeding" lines were estimates only.
8. Brain (STATE.md) updated and committed at every milestone; all lane commits merged to main
   fast-forward with the shared-tree protocol (porcelain identical before/after, every time) and pushed
   to the mirror.

## 2. CURRENT STATE (as of ~12:50)

- Supervisor registered, ticking every 10 min, fully uncapped (no time caps, no spend ceilings).
- 16/16 sentinels present; both targets (`fox`, `cnn-deep`) read done; `gate1.done` exists.
- GATE-2 loops on the invisible submission failure — harmless (each attempt dies in ~1–11 min, spends
  nothing) but it cannot converge until the error is seen and fixed.
- **A manual chain run is in flight** (`run_pipeline.py --from per_category_stance`, started 12:39:38 —
  not a supervisor path; Paul's or a lane's). This lane is holding all diagnostics per law 5.
- The contact-inference lane remains active on the box.

## 3. WHAT NEEDS TO BE DONE NEXT

**The one blocking decision (Paul):** how to capture the big5 submission error —
- **(a) Loud-error patch (recommended):** wrap `big5_llm.py:270` so the exception prints to stdout; the
  supervisor's own log then carries the root cause on the next tick, permanently (everything-must-emit).
  Small code change, Paul's gate.
- **(b) Controlled one-shot:** once the manual run finishes and the box is quiet, briefly pause the task,
  run one `--go` with stderr captured, re-enable. Worst "failure" = the traceback; worst "success" = the
  already-authorized batch, which the supervisor then resumes via PEND.
- **(c) Paul console run:** `python fec\members\big5_llm.py --opus --batch --go` from `fec\` and read the
  traceback directly.
- **Checkable without any run (Paul-side):** API account credit state, and whether the key in
  `fec\anthropic_key.txt` (unchanged since Jul 3) is still valid — if either is the cause, the fix is an
  account/key action, not code.

**Then, automatic (the supervisor drives it):** batch submits → PEND → collect → `big5_llm_opus.json`
fresh → freshness gate → `validate_big5` → the pre-registered C retest → reference dry est (uncapped) →
`reference --score` (July's timeout victim, now uncapped — should finish) → co_appearance → desk →
combined → audit → `gate2.done` → task self-unregisters. This lane verifies and reports the verdicts.

**Paul-gated code fixes flagged along the way (none applied):**
1. `big5_llm.py:270` — no exception handling on batch submission (the proximate cause of the invisible
   failure loop).
2. `gate_step` discards stderr — only the last stdout line survives into the log; any crashing gate step
   is undiagnosable from the supervisor log alone. Same fix family as (1).
3. GATE-1 writes `gate1.done` unconditionally even when its steps fail (`collector_supervisor.py`,
   GATE-1 block) — the class the C-1 fix closed for GATE-2; twice-observed (2026-07-07, today).
4. `_sentinel()`'s silent `except Exception: pass` (`fetch_interviews.py:1136`) — a failed sentinel write
   is invisible; one loud log line makes the next fox-style loop diagnosable.

**Sweep design (Paul):**
5. `fox` collects 0 member turns every pass (archive ended ~2022) — whether it belongs in future
   `collector_targets.json` sets is a sweep-design call.
6. Sentinel-deletion source stays unresolved by ruling ("Not necessary if they are abiding by the python
   code") — if sentinels vanish again, that proves an active deleter; re-diagnose then.

**Housekeeping debts:**
7. Dial-catalog registration (`GATE_STEP_TIMEOUT`, the `'inf'` cap defaults, `DESK_SPLIT` from the UI
   lane) — blocked on another lane's uncommitted `moneyball-config-and-flags` edits (never-clobber).
8. Carried from the manifest arc, unchanged: D-015 implementation + cost measurement, the live-tree gate
   re-measure at `022c3c728`, the `build_system_manifest.py:960` duplicate-candidate fix, manifest
   regeneration (APPLY, Paul's gate).
9. Standing: V-1 waits on Paul's `cu_rollcall_votes_clean.csv` (rank-delta gate when it lands); the
   weekly-refresh tolerance path's first real live test is the 08-30 Sunday run.

---
*Everything in section 1 is receipt-backed in the supervisor log, the named commits, and the brain's
2026-08-28 STATE entries; nothing in section 3 has been started without its named gate.*
