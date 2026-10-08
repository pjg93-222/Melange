# Collector Supervisor — Repair Status & Finish Runbook
**Run:** RUN3 (updated) · **Date:** 2026-08-28, last updated ~23:45 · **Author:** Fable (session `fervent-mendeleev-1c9dc5`), coordinated with peer session `collector-supervisor-actions-review-1a88-97`
**Purpose:** Durable record of the repair. Several background agents this session were killed mid-task by host/app restarts before reporting — this file exists so the work survives regardless. States exactly what is fixed, what is proven (with evidence), what is still open, and exact commands to finish it.

**Cross-reference:** A peer session ran an independent read-only code review of this diff and committed its findings at `audits/COLLECTOR_SUPERVISOR_CODE_REVIEW_2026-08-28.md` (branch `claude/collector-supervisor-actions-review-1a8864`, unmerged, mirror-pushed). Five of the six fixes in §2b below were driven by that review; cite it rather than re-deriving.

---

## 0. Executing tree (established fact)

Both scheduled tasks run out of the **main checkout**, not any worktree:
```
MoneyballWeeklyRefresh:        python.exe  "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\weekly_refresh.py"
MoneyballCollectorSupervisor:  python.exe  "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\collect\collector_supervisor.py"
                                WorkingDirectory: C:\Users\pgoff\OneDrive\Desktop\Melange Systems
```
Python interpreter used throughout: `C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe` (bare `python` is not on PATH). All of tonight's edits are **uncommitted changes on `main`** in that checkout. This worktree (`claude/fervent-mendeleev-1c9dc5`) is clean and is not what production runs.

## 1. What was broken (original three asks)
1. Collectors (email/media/press) not properly wired into the engine.
2. Not updating on a synchronized weekly basis.
3. Not feeding into the live system / downstream channels.

---

## 2a. Root cause chain, fully resolved

The night's actual causal chain, established through direct log evidence and cross-checked by an independent peer review:

1. Weeks ago, a fail-closed contract was added requiring `bill_repository_live.json` to exist and validate before a weekly refresh could complete — correct design, but **the file had never once been produced**, so every single weekly cycle was doomed to hard-fail at that check regardless of anything else (`weekly_refresh.log:375-378`: `legislation.congress_bill_repository.RepositoryError: bill repository is missing`).
2. Layered on top, the ABC interview collector was independently hard-failing every cycle from ~16:21 onward (`ABC done: 0 member turns` in ~2s, empty stderr) — a real, separate bug, fixed tonight (§2b confirmed live: 188 real member turns collected at 19:24:41).
3. Once ABC was fixed, cycles still hard-failed downstream at the bill-repository check (confirmed: cycles ending 20:26:38 (7130s), 21:12:34 (2170s), 22:00:06 (2623s) all still HARD_FAILURE) — because the bill repository still didn't exist.
4. At some point between 19:49 and 23:00 tonight, **one of this session's earlier dispatched agents completed a full Congress.gov bill-repository production run before its process was marked "killed"** by a host restart — the "killed" notification reflected lost visibility into the agent, not that its work didn't finish (consistent with the Project Brain's own `DE-013`: a stopped/killed notification is not proof the underlying work didn't land). Result, confirmed by direct inspection:
   ```json
   {
     "status": "PASS", "seeded": 464, "refreshed": 464, "failed": 0,
     "transport": "GovInfo BILLSTATUS bulk XML + Congress.gov headless fallback",
     "completed_at": "2026-08-29T03:00:58Z",
     "contract": {"complete_pass_required_for_publication": true, "partial_or_stale_refresh_authorizes_publication": false, "repository_and_seed_universe_hash_bound": true}
   }
   ```
   464 unique bill seeds (not the ~5,442 raw URL-mention estimate from an earlier regex pass over `member_desk_bundle.json` — that estimate over-counted incidental bill links in text fields; 464 is the authoritative, receipt-confirmed, hash-bound seed count from the actual structured extraction). Primary transport was GovInfo's bulk BILLSTATUS XML API (fast, no browser needed), with the Playwright/headless-Chrome path as fallback only — which is why no Chrome instance was ever observed using the scraper profile.
5. With the bill repository now present, the next weekly cycle (PID 14248, started 22:06:25) is the first to get past that check: `[2026-08-28 23:00:58] Congress.gov bill repository OK 38s — official GovInfo BILLSTATUS: 464 refreshed, 0 failed`, running as a step **inside** `weekly_refresh.py`'s own chain (confirming it was correctly wired in already — it simply had nothing valid to validate against until now). That cycle continued through CU extracts, Big Five traits, interaction features, behavior panels, Big5 v2/v3, social/press/HCoI network layers, multilayer network export, co-appearance layer, and the member-reference-layer rebuild (7,972 directed edges), all OK, as of last observation (23:37:43) — still `RUNNING`, not yet at GATE-1/GATE-2.

**Both structural blockers of the original loop (ABC, bill repository) are now resolved with direct evidence, not inference.**

## 2b. Six additional correctness/safety fixes (peer-reviewed, architect-applied, test-verified)

An independent peer session ran a read-only architect review of tonight's diff and found two HIGH-severity issues plus four medium ones. All six were applied by an architect agent tonight. Verification: **41 tests passed (up from a 23 baseline)**, all touched files compile.

| # | Item | Severity | Status |
|---|------|----------|--------|
| 1 | Fox sentinel dispatch regression | HIGH | Fixed |
| 2 | `_hard_abort` never named the failing step in status JSON | Medium | Fixed |
| 3 | GATE-2 permanently deadlocked against 2 standing Paul-gated audit items | HIGH | Fixed |
| 4 | `member_reference_layer.py` resume-safety (spend risk) | HIGH (investigate) | **Confirmed already safe — no change** |
| 5 | No cooldown on GATE-1 retry (resource waste) | Medium | Fixed |
| 6 | `gate_step` only logged last line + stderr contaminated success-path spend-parse | Medium | Fixed |

**1. Fox sentinel dispatch regression.** Tonight's `fetch_interviews.py` rework called `_sentinel()` (the function that commits a leg's `collector_sentinels/<tag>.done`) only on the `cnn` branch — `fox` and 7 other legs (`hewitt, nprfeed, axefiles, csis, cfr, aei, aspen`) ran their collection but never wrote their sentinel. The supervisor treats a leg as "done" *only* via that sentinel file (`collector_supervisor.py:245`), so those legs would never register as complete and the "pending forever" loop would have simply moved to a new source. **Fixed:** all 15 legs now call `_sentinel()` (six strict legs keep their existing `sys.exit(2)` contract and gain a `sys.exit(3)` on sentinel-write failure; the eight non-strict legs restore the original run-then-sentinel shape, now fail-loud instead of silent). **New test** walks the actual dispatch table via AST and asserts every leg has a `_sentinel()` call — a negative-control run (against mutated scratch copies, not the live file) confirmed the check flips correctly when a leg is broken again. `collector_sentinels/fox.done` remains a stale hand-restored file for now; this fix doesn't retroactively repair tonight's state, it guarantees correctness going forward.

**2. `_hard_abort` step-name propagation.** `weekly_refresh_status.json`'s `failures` field was always `[]` even on a named hard failure — tonight's HARD_FAILUREs showed no step name anywhere except the raw log file. **Fixed**, and verified strictly additive by grepping every consumer of that field (exactly one, `collector_supervisor.py:211`, and it only reads `failures` on the success path — never on `HARD_FAILURE` — so this is pure diagnostic upside with zero behavioral risk).

**3. GATE-2 permanent-deadlock risk.** `audit_full.py` always exits 1 while two **standing, already-known, already-open** items fire (V-1 at `audit_full.py:1513`, the culling check at `:1642` — re-derived against current source; a prior estimate of `~1353`/`~1482` was based on pre-diff line offsets). GATE-2 required `audit_full` to return 0, which it structurally never will — meaning once the (still-open, see §3.1) Big5 400 error is ever fixed, GATE-2 would loop forever, re-running a real-money re-score every ~10 minutes under Paul's already-lifted spend caps. **Fixed** by extending the *same* fail-closed tolerance pattern already used for GATE-1 (`KNOWN_GATED_FAILURES`) to GATE-2 — moved (not duplicated) into a new shared module `fec/audit_failure_gate.py`, imported by both `weekly_refresh.py` (re-exported for back-compat) and `collector_supervisor.py`. Tolerance is scoped **strictly** to the two named items — any different or novel `audit_full` failure still hard-blocks GATE-2 exactly as before. Four new tests include two drift guards: one asserting there's a single source of truth for the tolerated list, and one asserting the two ratified item names still exist verbatim in `audit_full.py` (so a future rewording of those checks can't silently re-deadlock the gate without a test noticing).

**4. `member_reference_layer.py` spend-safety — investigated, confirmed already safe.** This was the one item investigated before deciding whether to change anything, given real financial exposure (Paul's spend caps were explicitly lifted this week). Finding: the script uses a content-addressed, append-only cache (`data/members/member_reference_cache_fable.jsonl`, currently 19,537 entries) keyed by an MD5 of each record's content; only cache-misses are ever submitted (`todo = [r for r in target_all if key(r) not in cache]`); results are flushed to the cache immediately per-item, not batched at the end; and the printed cost estimate is computed directly from the to-do list size — so **a GATE-2 retry after a complete pass costs $0.00 and makes zero API calls.** No change was made. Two minor, pre-existing, out-of-scope issues were noted for Paul's future judgment, not fixed: the cache file is block-buffered so a hard kill mid-pass could lose ~$0.33–0.48 of already-done classifications (a one-line `.flush()` would close it), and `collector_supervisor.py`'s spend guard discards the dry-run's own success/failure flag before authorizing spend.

**5. GATE-1 retry cooldown.** The actual log showed the weekly refresh was relaunched on **every** 10-minute tick from 16:26 to 22:06 — roughly **15 full attempts**, each burning up to ~50–120 minutes of real collector/scrape work before hitting the (until tonight, permanent) bill-repository failure. **Fixed:** a cooldown starts at 15 minutes after a failure, doubles on each repeat failure, caps at 4 hours, and is cleared on the next success. Deliberately **fails open** (never blocks a refresh) on any corrupt, missing, or future-dated cooldown marker — the opposite posture from the correctness gates, since a broken cooldown must never be what permanently prevents a weekly refresh. Five new tests cover start/elapse/success-clears/doubling-and-cap/fail-open-on-corruption.

**6. `gate_step` output handling.** Two issues: (a) even after tonight's earlier stderr-preservation fix, only the *last line* of captured output was logged on failure — exactly why tonight's ABC/bill-repo failures showed the misleading `EMAIL REPORT SKIPPED` line instead of the real error. **Fixed:** full output is now persisted to `data\engine\gate_step_<name>.err` on failure (atomic write, one file per step so a chronically failing step can't fill the disk), and the last 5 non-blank lines are logged instead of 1. (b) stdout+stderr were concatenated for a regex cost-estimate parse on **both** success and failure paths — meaning stray dollar-figure text in stderr on a *successful* dry run could have been misread as the real cost estimate. **Fixed:** stderr is now included in that parse only when the step failed. A new regression test recreates the exact scenario (stdout says `est ~$0.01`, stderr contains a decoy `est ~$980.00`, spend cap `$1.00`) and confirms the fix returns the correct `$0.01`, not the decoy.

**Unrelated finding, not part of this repair:** running the full test suite (not just the focused wiring suite) surfaced 13 pre-existing failures in two other test files. Verified — both files and everything they import are byte-identical to `main` HEAD `7d773302c`, so these failed before tonight's work too and are out of scope: a stale import path from an earlier repo reorg (`test_ndjson_bom_tolerance.py`, 3 failures) and unrelated dashboard/template assertions (`test_bug_report_regressions.py`, 8 failures). Worth a separate ticket, not urgent for this repair.

### ⚠️ Caveat: the six §2b fixes are not active in the *currently running* tick — but self-activate at the next one, no restart needed
`collector_supervisor.py` (currently running as PID 15880) and `weekly_refresh.py` (currently running as PID 14248, started 22:06:25) both loaded their code **before** these fixes were written to disk tonight — Python does not hot-reload a running process. However, `MoneyballCollectorSupervisor` is not one long-lived process: Task Scheduler launches a **fresh process each ~10-minute tick**, with `IgnoreNew` simply skipping a launch attempt if the previous tick is still running (confirmed by direct evidence: the supervisor's own PID changed from 18176 to 15880 earlier tonight, and the log's `tick:` lines land at ~10-minute boundaries — consistent with fresh spawns, not one process looping internally).
- The in-flight cycle (PID 14248) will **not** show the new step-name-in-failures behavior even if it hard-fails again, and if the current supervisor tick (PID 15880) reaches GATE-2, it will still apply the **old, deadlocked** audit_full check.
- But that old-code deadlock **cannot actually manifest tonight**: GATE-2 first requires the Big5 re-score step to succeed, and that step still 400s at submission time (§3.1, unfixed, $0 cost, fails fast) — so tonight's tick will exit on that failure long before it would ever reach the audit_full check. Once this tick's process exits, Task Scheduler's next 10-minute trigger spawns a brand-new process that loads all six fixes from disk automatically.
- **No manual restart is required.** Paul restarting the task early is a legitimate option only to shorten the wait until the fixes are active — not something that needs to happen for them to take effect.

## 3. What is CONFIRMED STILL OPEN

### 3.1 Big5 Opus batch re-score: 400 BadRequestError — root payload cause still unknown
This is now the **last open item**. `fec\members\big5_llm.py`'s Anthropic Batches API submission (`--opus --batch --go`, artifact `data\members\big5_llm_opus.json`, untouched since Jul 7) failed 3 times tonight with an identical `est ~$118.57` payload shape (13:44, 14:02, 14:16) — `BATCH SUBMISSION FAILED [BadRequestError]: Error code: 400`. This is a **different program on a different path** than `big5_traits.py` (the feature-builder that ran fine as part of tonight's weekly cycle) — do not conflate the two, as this document did briefly before catching the error. The identical payload shape across 3 attempts makes a deterministic request-validation cause (a parameter the API now rejects) more likely than a transient one. Tonight's fix (§2b item 6, gate_step full-output persistence) means the **next** occurrence of this error — which only fires when GATE-2 actually runs the re-score — will finally have its complete body captured in `data\engine\gate_step_<name>.err` instead of being truncated. This has deliberately **not** been fixed yet, because fixing it before §2b item 3 (GATE-2 tolerance) would have converted an inert risk into a live repeated-spend loop; that ordering constraint is now satisfied, so fixing the 400 is unblocked and safe to attempt next.

### 3.2-OUTCOME (added 2026-08-29 13:05) — what actually happened overnight
- The 22:06 cycle ran the **entire** FULL PIPELINE chain and **rebuilt all three live surfaces at 00:51** (`member_desk_bundle.json` 00:51:25, `cu-member-desk-profiles.js` 00:51:28, `Moneyball.html` 00:51:33). Because `make_member_desk.py` runs as a fresh subprocess with the new fail-closed bill contract, those rebuilds prove the 464-bill repository validated and **is now feeding the live surfaces** — the original ask #3, done with evidence. Anomaly: the cycle then died during final bookkeeping (~00:51:50–00:56) without writing its terminal status or a GATE-1 receipt — no outcome line in either log. Cause unestablished; the work landed, the receipt didn't.
- A fresh cycle started **00:56:23 on the new code** — the six §2b fixes are visibly active (every interview leg now logs `completion sentinel committed`, the fox-class sentinel fix working live; bill-repo step passes in 23s). It ran through MS NOW (01:27:31), then the laptop entered Modern Standby overnight (kernel-power log: low-power until **12:57:18 PM** — the keep-awake lock did not prevent lid-close standby). The processes (PIDs 61804/65940) **survived suspension and resumed at 12:57 PM; both alive as of 13:03**, with Task Scheduler correctly refusing new ticks (`0x800710E0`, IgnoreNew) while this instance runs. Expected: first-ever `collector_gate1_receipt.json` in roughly 2.5–3 hours if it completes, then GATE-2 fires under the new code — which will finally capture the full Big5 400 body in `data\engine\gate_step_*.err` (§2b item 6).

### 3.2 Live weekly cycle (PID 14248) — outcome still pending (superseded by 3.2-OUTCOME above)
As of last observation (~23:37:43), the cycle started at 22:06:25 was still `RUNNING`, having just completed the reference-layer rebuild and press stance stack, with `collector_gate1_receipt.json` and `gate2.done` both still absent. This is a long-running but healthy pipeline (steady step-by-step progress, no stall) — leave it alone. Given the caveat in §2b, even a full success here will exercise the **old** GATE-2 logic, not tonight's fix.

### 3.3 Email delivery channel stays "skipped" by design, not by bug
`fec\icloud_smtp.txt` (apple-id / app-specific password / from-address, 3 lines) does not exist — explicitly Paul's credential step. No action needed unless he wants the channel live, in which case he creates that file himself.

## 3b. Sentinel-deletion forensics — SETTLED (added 2026-08-29 ~15:20, verdict by the review lane)

The 2026-08-28 sentinel disappearance is fully explained, with a receipt. At **07:19:15 EDT on 08-28**, the Codex N4 "adversarial review" agent of metaloop run `run-20260828T0436464194035Z-65299375bd` ran a PowerShell command (rollout `...01a046a7...` event 6863) that **MOVED 14 sentinel files to `outputs\quarantine\legacy_false_sentinels_20260828\`** — quarantine, not deletion — labeling them "legacy false sentinels" (sparing the 2 newest, cnn/cnn-deep). Physically confirmed: exactly those 14 files sit in the quarantine directory with original timestamps intact. No malice, no OneDrive artifact, no human: one agent judgment call, executed as a raw shell move that emitted **zero glassbox telemetry**. The all-day relaunch loop that followed was this one event compounding with the then-live missing-sentinel-write defect (since fixed). The 12:02 hand-reconstruction was recovering files that still existed in quarantine; today's fox event was Paul's own deliberate fire test (§ fire-test notes).

Standing items from the verdict: (1) the quarantine directory is the evidence record — **Paul's call** whether/when to clean it; (2) **process lesson**: a Codex-lane shell action inside the live tree bypassed the everything-must-emit rule entirely — collector-critical file operations by any lane need a glassbox receipt, and the timed-refire semantics Paul ratified on 08-29 now make ad-hoc "stale sentinel cleanup" unnecessary by construction (stale sentinels refire without anyone touching files).

## 4. Exact next steps

1. **Do not touch PID 14248 / its parent supervisor process.** Let it finish naturally; check `data\engine\weekly_refresh_status.json` and `collector_gate1_receipt.json` periodically.
2. **No action needed for the six §2b fixes to take effect** — they activate automatically at the next scheduler tick once the current one exits (see caveat above). Restarting the task early is optional, only to hasten this.
3. **Root-cause the Big5 400** (§3.1) — now unblocked and safe. Once GATE-2 next runs (after the supervisor restart), the full error body will land in `data\engine\gate_step_big5*.err` — read that file first rather than re-deriving from the log tail.
4. **Review and commit tonight's diff** when Paul is ready — nothing has been committed. Do not merge or treat any `audit_full.py` figure from a worktree as authoritative (per the Project Brain's `DE-012`); the main-checkout run is the one that counts.
5. **Close the Meta LOOP / Glassbox run** (`run-20260828T2241516689371Z-fcf646e825`) once the supervisor has been restarted and a full cycle is observed to reach GATE-1 and GATE-2 cleanly under the new code.

## 5. Files touched tonight (main checkout, all uncommitted on `main`)
```
fec/audit/audit_full.py
fec/audit_failure_gate.py                      (new — shared KNOWN_GATED_FAILURES source of truth)
fec/collect/collector_supervisor.py
fec/collect/fetch_press_text.py
fec/legislation/congress_bill_repository.py
fec/legislation/update_bill_repository.py
fec/members/big5_llm.py
fec/members/fetch_interviews.py
fec/run_pipeline.py
fec/surfaces/make_email_package.py             (new)
fec/surfaces/make_member_desk.py
fec/tests/engine/test_dashboard_legislative_workbench.py
fec/tests/infra/test_collection_stream_wiring.py
fec/weekly_refresh.py
```
Plus generated artifacts from live runs (not hand edits): `bill_repository_live.json`, `data/engine/congress_bill_refresh_receipt.json`, collector sentinels, `.pipeline_run.lock`, `.weekly_refresh.lock`, `data/system/system_manifest.json`.

**None of this has been committed.**

## 6. Honest summary of remaining risk
1. **Big5 400 root cause unknown** (§3.1) — the only item where the actual defect (not just its safety net) hasn't been fixed. Now safely unblocked to investigate.
2. **Tonight's six §2b fixes are not active in the current supervisor tick** but self-activate automatically at the next scheduler-spawned tick, no restart required (§2b caveat).
3. **The in-flight cycle's final outcome is unconfirmed** — it was still running as of last check, ~90 minutes in.
4. **Process/session fragility observed all night**: multiple background agents were killed by host restarts mid-task; in every case their underlying work either survived (the bill-repository production) or was cleanly resumable from a saved transcript. Prefer detached processes (`Start-Process -WindowStyle Hidden`) for anything long-running, and resume-by-name rather than re-dispatch-from-scratch when an agent shows as "stopped."
5. **Worktree vs. main-tree audit figures**: per the Project Brain (`DE-012`), any `audit_full.py` run from a worktree is a vacuous self-pass — only a main-checkout run is authoritative.
