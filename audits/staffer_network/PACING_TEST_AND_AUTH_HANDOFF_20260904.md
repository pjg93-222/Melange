# Politico pacing test and authentication handoff

## Resume update — 2026-09-04 18:05 Eastern

The earlier paused status below is superseded. The user explicitly requested resumption. The current single-page writer launched at 18:05:25 Eastern (launcher PID 70232; `python_resume_20260904T180525.log`). Authentication canary API200 passed, new records are being saved, and the first-three-checkpoint independent verification passes. At 18:05:48, state reported 5,038 accounted and 13,580 remaining, not halted. The 18:05:43 receipt independently covers 5,033 records: 4,943 content-bearing plus 90 authoritative404 exceptions. Later live counts may exceed that verified prefix until the next writer-owned verification.

Resume ordering now persists `next_profile_uuid`, with a legacy fallback after the last saved success. This prevents every restart from hitting the same early incomplete profiles first. All unresolved UUIDs remain queued for later review/retry; none are dropped or promoted to successful profiles. Creating a replacement tab before closing the final existing tab also fixes persistent-browser shutdown during recovery. The 58-test suite passes. The existing heartbeat monitor is ACTIVE again. The target remains a 0.5-second navigation start interval after the gentle ramp; this is not a claim of 120 completed profiles/minute.

Recorded 2026-09-04, approximately 17:40 Eastern. This is an incomplete-crawl handoff, not a completion report.

## Outcome

Implemented a shared navigation pacer with a 0.5-second minimum start interval at the authorized 120/minute ceiling. It includes explicit profile loads, retries, and directory initialization, without catch-up bursts. It does not count the browser's automatic asset/API requests. Gentle ramping and automatic backoff remain enabled. Removed the extra per-batch sleep that previously added idle time after rendering.

A three-page overlapping pipeline passed unit tests and sequential authenticated canaries, but failed live throughput validation: two pages repeatedly timed out while another made progress. Sequential startup solved initial startup timeouts, but did not make concurrent collection reliable. Brief foreground activation was also tested and removed after failing to improve the result. One page is now the stable default; do not claim that 120 completed profiles/minute was achieved.

The subsequent one-page restart redirected to `login.politicopro.com/`. Collection and its heartbeat monitor are paused pending reauthentication. The last crawler's exact owned process tree was stopped; unrelated browser windows, the dashboard, and other services were not stopped. No credentials or browser storage were exported or inspected.

## Verified checkpoint

The independent stopped-writer verification reports integrity **PASS** and completion **INCOMPLETE**:

- Sealed directory: 18,618 unique profile UUIDs.
- Accounted: 5,030 (4,941 content-bearing profiles plus 89 authoritative unavailable/404 exceptions).
- Remaining: 13,588.
- Hard crawl failures recorded: 0. The runtime itself is halted for authentication.
- Employment-history records: 25,099.
- Same-UUID name changes: 4, still review exceptions rather than automatic identity merges.
- Profile prefix: 8,027,516 bytes.
- Profile SHA-256: `424625567acf57bc1e42159078d9428cf33417c49ec0c3ba8767979979795684`.

The verification receipt is `politico_profile_crawl_20260903_raw/crawl_verification.json`. The last startup log is `politico_profile_crawl_20260903_raw/python_paced_20260904T173756.log`; it records the login-host redirect. `state.json` truthfully records `halted: true`.

## Preserved safeguards

Content acceptance still requires the expected final UUID, exact person API200, loaded/settled complete modeled data, and three identical snapshots. Soft404 still requires an actual person API404 and a stable visible error with no contradictory content. Authentication/challenges stop collection; throttling and server errors trigger backoff. No shells, timeouts, or unscheduled jobs become successful profiles.

The pipeline now preserves every queued UUID when stopping admission, counts only actually started attempts, drains cancelled siblings before releasing writer ownership, and uses one append/checkpoint writer. Tests cover these invariants alongside the original extraction and repair gates.

## Next steps

1. Restore authentication in the dedicated crawler Chrome profile, without copying another browser's cookies or credentials.
2. Confirm no crawler/dedicated-profile process remains. Resume one page with the gentle ramp and shared pacer; require authenticated content canary and fresh successful verified output before announcing resumed collection.
3. Report measured accounted/content-bearing throughput separately from the configured start interval. Do not re-enable concurrent pages without a successful independent live test.
4. Resume the existing `finish-staffer-lda-reconciliation` heartbeat after authentication and actual progress are verified. Keep routine progress notifications quiet.
5. At zero remaining, run terminal complete-crawl verification, finish strict matching and deterministic twin graph verification, and write the final reconciliation/coverage/next-steps Markdown. No complete-network or full-coverage claim is warranted now.

No dashboard modeling defaults or network layers were changed by this pacing work.
