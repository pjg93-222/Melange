# Open work — 2026-09-18

Six lanes reported back this pass; this file replaces the same-day draft, whose main error was marking already-committed Mentat patches (S2 through S8, the UI clean-up, the collector fix, the console-hang fix) as "awaiting Paul's commit" — every one of them is landed.
17 items sit on Paul across the six lanes below: rulings, one merge, one restart-and-resume, and a retention rule.
Highest risk isn't any one lane, it's disk: C: was at **2.85 GB free of 952.5 GB** as of 2026-09-18 15:17, down from 108.4 GB right after this morning's clearance.
Top consumers: Melange Systems 279 GB (worktrees 164.3, audits 57.2, outputs 17.9), `C:\Users\pgoff\Mentat` 88.61 GB, `Temp\claude` scratchpads 54.3 GB, `AppData\Local\Mentat` 33 GB, `AppData\Local\Melange` 28.66 GB; 16.6 GB more landed today alone from legfix5 audit packets, staged review queues and git pack files.
A chain run writes hundred-MB artifacts and will start failing at this level — see Cross-cutting for why the fix is a retention rule, not another sweep.
Census: `audits\open_work_20260918\DISK_CENSUS.md`; a reclamation pass is running now and will report to `audits\open_work_20260918\DISK_RECLAIM.md`.

---

## 1. Mentat collection (collector slowdown, worker scaling)

Why FEC collection lanes were failing and losing runs, and the shared API-key pool behind it. Branch `codex/mentat-crypto` in `C:\Users\pgoff\Mentat`.

**Landed**
- `494dc133c` — pool quarantines an `API_KEY_*` 403 and re-issues on a healthy key; pool width follows key supply; lands the worker-scaling set, including `api_request_pool.py` (already imported elsewhere but never itself committed before now).
- `f0ec60b74` — a moving `pagination.count` re-walks instead of aborting; `MENTAT_RECONCILE_PASSES` default 3; union-aware determinism check.
- `bd8c65ebb` — console Resume-last-run: `POST /api/resume`, `-ResumeRunId`, stop flags cleared.
- `dba77f87f` — an estimated count is verified by date windows instead of failing outright.
- `2a5f05761` — a run whose process is gone now reports stopped, so its work becomes resumable.
- `b9fe34d02` — diagnosis packet; `55cbc88b6` — provenance plus five tracked patch diffs.
- Operational: key `13ffe51ce05b` (truncated to 39 characters) is disabled; the 21 remaining active keys are all 40 characters.

**Built, not landed** — Nothing is uncommitted, but the console on 8806 must be RESTARTED. It started 00:24, before `2a5f05761` landed at 12:27, so the 09-17 12:41 Credit Unions run (27 of 30 tasks) still reports "starting" with Resume disabled; after restart it reports stopped and becomes resumable.

**Blocked on Paul**
- Apply and commit the three drafted brain entries (a STATE bullet, DE-026, D-040) and ratify D-040. Default if silent: they stay drafts in the packet.
- Restart the console, then resume the 12:41 Credit Unions run — the only way that 27-of-30 data reaches the database, since merge is all-or-nothing. Default if silent: that run's data never lands.
- Set a retention rule for lane databases: they're the only evidence of what a run collected (the merged DB keeps no response bodies), and Banking's ten were already deleted in the 09-16/09-18 disk clearances, leaving a $32.5M attribution question unanswerable offline. Default if silent: cleanups keep happening ad hoc and more unrecoverable evidence gets deleted before it's used.
- Key-store hardening: a hard 40-character reject on ingest is more correct but would lock Paul out if data.gov changes its key format, so warn-and-record is the safer default — his call which to adopt. Default if silent: no hardening change is made.
- Optional: recovering the missing 40th character of `13ffe51ce05b` would restore 22 keys to the pool. Default if silent: those keys stay unrecovered.

Known and live, not Paul's to decide: single-cycle runs fail the workbook wanting cm22; a staged runtime path beyond ~275 characters breaks `sys.path[0]`.

## 2. Mentat cross-reference and evidence CSV

Whether the cross-reference engine's exclusions and totals can be trusted and reconciled against the published workbook. Branch `codex/mentat-crypto` in `C:\Users\pgoff\Mentat`; detail at `C:\Users\pgoff\.claude\session-data\2026-09-18-mentat-xref-what-to-finish.md`.

**Landed**
- `3fdfeae8f` — FEC transaction-type ruling: codes map to channels via `mentat/inputs/fec_transaction_types.json`; memo entries, 24/48-hour notices and excluded codes stay visible and out of totals.
- `627300bc9` — attribution rule: a row whose own text names another identifiable organisation is excluded; text naming the company itself counts, flagged (brain D-043).
- `215ddf85c` — four company PACs registered against the FEC committee master; 34 rows / $155,231.06 moved to PAC activity.
- `7fa9c8a4b` — three aliases removed; a fourth kept as the only match for 242 rows / $572,500.00.
- `bdd818c11` — one adjudicated treasury record opens the corporate line, $0.00 to $1,025,874.75.
- `8a96066` — brain D-043 plus a STATE bullet.
- Suite 113 passing.

**Built, not landed** — Nothing is uncommitted, but the LAUNCHER needs a full re-run, not a console restart: 8806 was last verified on `627300bc9` and HEAD has moved several times since; the cross-reference tab only shows run `20260918T183722-d8f0fb287912` after that re-run.

**Mid-flight, no decision needed yet** — A bounded 300-request FEC re-fetch is testing whether Banking's stored employer text was recorded faithfully; that text decides whether 29,816 rows worth $32,538,668.49 count. Free evidence for this is exhausted — Banking's ten lane databases are already deleted (see Lane 1).

**Blocked on Paul**
- Treasury policy beyond the one accepted row: the corporate line currently rests on a single lawful 2021 inaugural donation — a finding, not a distribution. Default if silent: it stays that one row.
- Amendment de-duplication: $344,433.54 of probable duplicate dollars stays counted pending a rule on `AMNDT_IND` / `FILE_NUM` where the latest filing wins. Default if silent: those dollars stay counted.
- Whether observed Banking giving above the published workbook total ($76,899,254.70 against $54,762,844.05) is acceptable. Default if silent: the gap stays open and unreconciled.
- An engine change: `affiliations_for` matches on name only and never consults receipt role, so $25,874.75 of interest/artefact rows ride into the corporate line under the Bank of America name. Default if silent: those rows keep riding in.
- A reconciliation job for $251,029.90 of the workbook's corporate tier that could not be reproduced (`R/report.R` around lines 2060-2090). Default if silent: that gap stays unexplained.

## 3. Mentat console — PAC evidence (S6, S7, S8, S8b)

The console's evidence tab: scope bar, cross-industry panes, district map and street geocoding. Branch `codex/mentat-crypto`.

**Landed**
- `882f1f93f` — S7 categories, type filter, search, CORPORATE rows counted, workbook exclusions honoured; Fairshake now reads $177,980,393.39 instead of $1.0M.
- `ea222fadb` — ledger.
- `487589584` — S6 scope bar, four cross-industry PAC panes, compare strip; `evidence.js` replaces `evidence-csv.js`.
- `491570a0b` — S8 district map, all spend reconciled (Fairshake 2024: $193,545,160.56 located + $2,281,350.87 unlocated = $195,826,511.43).
- `d62498cb1` — S8b street geocoding behind an explicit Start, one Congress per map.
- `03ba77aaa` — two defects the console lane found.
- Suites 32/32, 22/22, 214, 149, zero page errors.

**Built, not landed** — Nothing is uncommitted, but Paul must RE-RUN THE LAUNCHER: the lane added `evidence.js`, `geocode.py`, `district_geo.py`, `evidence_geo.py` and eight assets under `app/geo`, and an old console serves an `index.html` pointing at scripts that will 404.

**Blocked on Paul**
- The street layer can't place real money: Overview workbooks carry City/State/ZIP but no street column, and the companion Data workbook (which defines Street 1/2) has never been generated. He chooses between generating Data workbooks with the tidy-workbook tool, or adding a street column to Overview. Default if silent: the map's Raised side stays ZIP-level only.

Minor, harmless if left, no action needed: no "Top districts" row in the Compare strip; tracts straddling districts keep their ZIP basis. For awareness only, not urgent: console background and body size differ from the approved mockup — those are console-wide tokens, so it's a retheme call whenever Paul wants to make it.

## 4. Mentat console startup hang — closed

The console-build-stamp hang that could block 8806 on a request. Branch `codex/mentat-crypto`.

**Landed**
- `0ad366e01` — git sha taken off the HTTP request path: pure-Python gitdir reader, non-hanging subprocess fallback, non-blocking single-flight resolver replacing `lru_cache`; new `test_console_build_stamp.py`, 16 tests.
- `aa8a3f884` — three browser suites realigned, 12 assertions re-homed.
- `869419d` — brain D-045, DE-026, DE-027.
- Six suites green.

No blocked items — this lane is closed. One open chip that is explicitly not a decision: `Start-MentatApp.ps1:49` computes a code-tree hash and never uses it, vestige or an unwired comparison, waiting on Paul's click rather than his judgment.

## 5. System manifest writer — pin correction

Independent verification of the system manifest writer's commit `482d24df0`, which turned up one wrong re-pin.

**Landed** — `482d24df0` verified independently; no duplicate change was needed.

**Built, not landed** — `a84842eb7` on `claude/amazing-lewin-409893` (not main): corrects `build_media_blend.py`'s saved-at pin from `:479` to `:466` (`:479` is only true against the live working copy, which carries thirteen uncommitted lines of drift; `a0c45a709` had already moved the call from `:451` to `:466`). It landed off main because Paul's standing rule pins receipts to committed source, not live drift.

**Blocked on Paul** — Merge or cherry-pick `a84842eb7` into main so the committed pin matches reality. Default if silent: main keeps citing the stale `:479` line.

## 6. Members Section consistency (Melange dashboard)

Rebuilt how members are scored and labelled on the desk and dashboard, using Donald Davis as the worked case.

**Landed** — 24 commits on main, `2f11d9490..776ce0d3a`: the field ladder now runs Champion to Opponent with no label only where there is no evidence, and each field card carries its itemized ledger; votes count as concrete action and carry their sign; the primacy board is the per-area grade times the purity factor, within chamber; Demographic Potential measures credit-union footprint; every social post scores, with cross-post twins noted rather than dropped; the Responsiveness section is retired behind a dial. Committee registry gained six bodies for 113 members, and the relevance tiers were ruled by inference (brain D-042): Veterans' Affairs is [Slightly], Agriculture stays [Moderately]. Committee scores became a chain producer and the honors workbook binding was scoped to the sheets it writes (brain D-046). Packet and evidence committed on the lane branch through `f51a8fca9`.

**Blocked on Paul** — Whether votes should drive honors overall opposition labels; unbounded they relabelled 372 of 533 members, so they are currently bounded to field ladders only. Whether the four-pillar weights are 45/10/40/5 as the code runs them or 30/25/40/5 as the 2026-07-07 ratification says; the docs now state both and flag it as open ruling S-5, and nothing changes until he rules. Whether press should become a fourth recognition kind, which needs an immutable press-evidence artifact built first. Committee relevance tiers are ruled but remain his to override in Excel. Whether to regenerate and commit a fresh manifest: main's manifest agreement (305 checks / 0 failed) was measured against a regenerated manifest that was deliberately never committed, so agreement against HEAD's actually-committed manifest is unmeasured — not known-red, just unverified — until that happens.

---

## Cross-cutting

- **Disk is the top risk across every lane, not just Lane 1.** C: is at 2.85 GB free of 952.5 GB (2026-09-18 15:17), down from 108.4 GB right after this morning's clearance; top consumers are Melange Systems (279 GB), `C:\Users\pgoff\Mentat` (88.61 GB), `Temp\claude` scratchpads (54.3 GB), `AppData\Local\Mentat` (33 GB) and `AppData\Local\Melange` (28.66 GB), with 16.6 GB more written today alone. A chain run writes hundred-MB artifacts and will start failing at this level.
- **Deletion now needs a rule, not a sweep.** Lane 1's retention decision — lane databases are the only surviving evidence of a run, and Banking's ten are already gone — is the disk problem and the data-integrity problem at once. Freeing space by deleting more lane databases before that rule exists repeats the mistake that made the $32.5M Banking question unanswerable.
- **Three lanes are each waiting on the same kind of action.** Lane 1 (collector-slowdown) needs the console RESTARTED; Lanes 2 (cross-reference) and 3 (PAC evidence) need a full LAUNCHER re-run, not just a restart. A launcher re-run does both — one action clears all three lanes' blocking note at once.
- Census: `audits\open_work_20260918\DISK_CENSUS.md`. A reclamation pass is running now and will report to `audits\open_work_20260918\DISK_RECLAIM.md`.

## Traps worth knowing

- **`codex/mentat-crypto` lives only in `C:\Users\pgoff\Mentat`**, a separate checkout from this Melange Systems tree. Lanes 1 through 4 above all commit there, not here — grepping this repo for those SHAs will correctly find nothing.
- **Committed is not the same as landed on main.** Lanes 1 through 4 are committed but on `codex/mentat-crypto`, unmerged; Lane 5's fix is committed but on `claude/amazing-lewin-409893`, not main. "Committed" means safe from loss, not shipped.
- **DE-026 is not one thing.** `869419d` (Lane 4, console-hang) landed one DE-026; Lane 1's (collector-slowdown) brain packet still carries a different, unapplied DE-026 draft. Don't assume one status covers both just because the label matches.
- A launcher re-run and a console restart are different actions — Lane 2's own reply is explicit that a restart alone will not pick up its new evidence-tab build.
