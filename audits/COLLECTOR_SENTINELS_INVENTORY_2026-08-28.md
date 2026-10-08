# COLLECTOR SENTINELS — COMPLETE INVENTORY

Date: 2026-08-28
Lane: claude/collector-sentinels-inventory-895b67 (worktree hmm-melange-analysis-6f6786, branched at main `022c3c728`)
Method: repo-wide case-insensitive content grep for `sentinel` (76 matching files; 15 with substantive logic under
`fec/`), plus a per-collector sweep of `fec/collect/`, `fec/members/`, `fec/lobbying/`, `fec/speech/`, and the
grok-companion X collector. Every claim carries a `file:line` pointer. Measurement caveat: file CONTENTS quoted
here are from this worktree's checkout of the branch tip; the LIVE tree may carry newer uncommitted sentinel
writes (see §1.4), so operational live-state reads are labeled where taken.

The word "sentinel" names THREE distinct mechanisms in this system. This document inventories all three, then
the marker/checkpoint machinery adjacent to them, then a per-collector coverage table so nothing is left
unaccounted for.

1. **Collector completion sentinels** — `collector_sentinels/<target>.done` files marking a collection leg
   finished, driving the collector supervisor's execution-queue gates. (§1)
2. **Other collector-side markers** — approval markers, state files, run manifests, and in-database sentinel
   values written or required by individual collectors. (§2)
3. **System-manifest sentinels** — per-store integrity sentinels in `data/system/system_manifest.json`,
   covering (among others) every store that holds collector output. (§3)

---

## 1. The collector completion-sentinel system (`collector_sentinels/`)

### 1.1 Mechanism

**Writer** — `fec/members/fetch_interviews.py:1132-1136`:

```python
def _sentinel():
    try:
        sd = os.path.join(B, 'collector_sentinels'); os.makedirs(sd, exist_ok=True)
        open(os.path.join(sd, _leg + '.done'), 'w').write(datetime.datetime.now().isoformat())
    except Exception: pass
```

- Content: a bare ISO-8601 timestamp (`datetime.now().isoformat()`, ~26 bytes).
- Written **on success only**: each leg's dispatch is `run_<leg>(...); _sentinel()`
  (`fetch_interviews.py:1137-1150`), so an exception in the run means no sentinel.
- Written by **every** successful `fetch_interviews.py <leg>` invocation — the supervisor's detached legs AND
  `weekly_refresh.py`'s interview steps both refresh these files (see §1.6).

**Reader** — `fec/collect/collector_supervisor.py`:

```python
SENT = os.path.join(B, 'collector_sentinels')          # :30
done    = {t for t in targets if os.path.exists(os.path.join(SENT, t + '.done'))}   # :235
pending = [t for t in targets if t not in done]                                     # :236
```

Targets carrying a sentinel are complete; pending targets are (re)launched detached
(`collector_supervisor.py:100-102`, stdout to `collector_<tag>.out`, `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`).

### 1.2 Target roster — every sentinel name that can exist

The operative target set is **dynamic**: `data/stance/collector_targets.json` (assignment
`collector_supervisor.py:32`, read at `:233`), format `{tag: [args...]}`, written by the launcher. The file is
**absent in this checkout**; in the **live tree** (measured 2026-08-28, read-only) it EXISTS, uncommitted,
configuring a two-target sweep:

```json
{"fox": ["fox"], "cnn-deep": ["cnn", "--since", "2019-01-01", "--until", "2024-02-29"]}
```

The full leg vocabulary hardcoded in the collector (`fetch_interviews.py:1130`) — i.e. every possible
`<leg>.done` sentinel:

| # | Leg | Sentinel file | Notes |
|---|-----|---------------|-------|
| 1 | `cnn` | `cnn.done` | incremental daily |
| 2 | `cnn-deep` | `cnn-deep.done` | deep backfill alias: taken when `until <= '2024-06-01'` and no `--verify` (`:1131`) — own sentinel so it never collides with daily `cnn.done` |
| 3 | `mtp` | `mtp.done` | Meet the Press |
| 4 | `cbs` | `cbs.done` | |
| 5 | `abc` | `abc.done` | |
| 6 | `pbs` | `pbs.done` | |
| 7 | `npr` | `npr.done` | |
| 8 | `fox` | `fox.done` | excluded from weekly refresh (archive ended ~2022) |
| 9 | `hewitt` | `hewitt.done` | |
| 10 | `msnow` | `msnow.done` | MS NOW |
| 11 | `nprfeed` | `nprfeed.done` | |
| 12 | `axefiles` | `axefiles.done` | |
| 13 | `csis` | `csis.done` | |
| 14 | `cfr` | `cfr.done` | |
| 15 | `aei` | `aei.done` | |
| 16 | `aspen` | `aspen.done` | |

All 16 legs run the **same script** (`fec/members/fetch_interviews.py`, dispatched per
`collector_supervisor.py:100-102`); the sentinel namespace is the leg name, not the script.

### 1.3 Sentinels present in this checkout — 7 of 16

All seven are **git-tracked** (in `git ls-files`; `.gitignore` does not cover them). Contents:

| File | Content (completion time) |
|------|---------------------------|
| `collector_sentinels/cnn.done` | `2026-08-02T06:05:13.298782` |
| `collector_sentinels/mtp.done` | `2026-08-02T06:08:34.451969` |
| `collector_sentinels/cbs.done` | `2026-08-02T06:08:53.425475` |
| `collector_sentinels/abc.done` | `2026-08-02T06:08:56.675158` |
| `collector_sentinels/pbs.done` | `2026-08-02T06:14:07.886968` |
| `collector_sentinels/npr.done` | `2026-08-02T06:17:38.387489` |
| `collector_sentinels/msnow.done` | `2026-08-02T06:32:58.631895` |

The committed vintage is one sweep, 2026-08-02 06:05–06:32. On-disk mtimes in a worktree reflect checkout
time, not collection time — the file **contents** are the authoritative timestamps.

**Live tree, measured 2026-08-28 (read-only):** `collector_sentinels/` holds **14 of the 16** possible
sentinels — the seven above (rewritten, uncommitted) plus `fox.done`, `hewitt.done`, `csis.done`, `cfr.done`,
`aspen.done`, `axefiles.done`, `cnn-deep.done` (untracked) — and every one's content carries a **2026-08-28**
timestamp: a sweep completed today. The only sentinels that have never existed are `aei.done` and
`nprfeed.done` (2 of 16). For the supervisor this means: any leg without a sentinel that appears in
`collector_targets.json` reads as pending and is launched; the current live target pair (`fox`, `cnn-deep`)
is fully sentineled.

### 1.4 Lifecycle — nothing ever resets them

A repo-wide search found **no code that deletes or rewrites-to-empty a `.done` sentinel**: no `--reset` flag,
no sweep-start clearing, nothing in `weekly_refresh.py`, nothing in the supervisor. A sentinel persists until
a new successful run of the same leg overwrites it, or someone deletes it by hand. Consequences worth knowing:

- A **fresh clone arrives with the seven tracked sentinels already "done"** — a newly configured supervised
  sweep over those legs would consider them complete without collecting anything, until the sentinels are
  manually removed.
- Measured 2026-08-28: the live tree's sentinel contents ARE newer than the committed 08-02 vintage — all 14
  carry today's date (any successful `fetch_interviews.py` leg, supervised or weekly-refresh, rewrites its
  file uncommitted).

### 1.5 What the sentinels gate — the supervisor's execution queue

`fec/collect/collector_supervisor.py` runs from Windows Task Scheduler as **`MoneyballCollectorSupervisor`**
(every 10 minutes; docstring `:6`, task name `:280`). Each tick: relaunch dead pending legs, wedge-check live
ones (§1.7), and when **all targets have sentinels** (`:275`), run the gates:

**GATE-1 — free corpus absorption** (`:146-151`), once (guarded by `gate1.done` `:146`):

| Step | Command | Timeout |
|------|---------|---------|
| 1 | `weekly_refresh.py` | 6000 s |
| 2 | `audit/audit_full.py` | 6000 s |

`gate1.done` (ISO timestamp, `:150`) is written **unconditionally** — an audit failure is logged
("audit clean=False", `:151`) but does not withhold the flag. Observation, not a defect claim: GATE-1's done
flag records "ran", not "ran clean".

**GATE-2 — paid full re-score + C retest + desks** (`:158-198`), once (guarded by `gate2.done` `:158`);
sets `B5_FAST=0` (`:160`). Steps in order:

| # | Step | Script | Timeout | Guard |
|---|------|--------|---------|-------|
| 1 | big5 re-score dry estimate | `members/big5_llm.py --opus --batch` | 3600 s | spend guard, cap `B5_GATE_CAP` (default **$200**), **fail-closed**: unparseable estimate or estimate > cap halts GATE-2 (`:132-139,163-165`) |
| 2 | big5 full re-score | `members/big5_llm.py --opus --batch --go` | 36000 s | failure aborts GATE-2 (`:168`) |
| 3 | freshness gate | — | — | `big5_llm_opus.json` must be fresh within 60 s of gate start or GATE-2 aborts — "no stale-data look" (`:167-170`) |
| 4 | validate_big5 | `members/validate_big5.py` | 1200 s | |
| 5 | C retest (prereg) | `c_prereg_test.py` | 1200 s | conditional |
| 6 | reference dry estimate | `members/member_reference_layer.py --score` | 3600 s | spend guard, cap `REF_GATE_CAP` (default **$100**), fail-closed (`:178`) |
| 7 | reference score | `... --score --go` | 6000 s | conditional on 6 |
| 8 | co_appearance | `co_appearance_layer.py` | 1200 s | required |
| 9 | member desk | `surfaces/make_member_desk.py` | 1200 s | required |
| 10 | combined | `surfaces/make_combined.py` | 1200 s | required |
| 11 | audit_full | `audit/audit_full.py` | 6000 s | required |

`gate2.done` (`:197`) is written only if steps 8–11 all succeed (`:192-196`); on completion the supervisor
**unregisters its own scheduled task** (`schtasks /Delete /TN MoneyballCollectorSupervisor /F`, `:277-283`).

The codex-executor lane is **barred** from running the supervisor (`.claude/skills/codex-executor/SKILL.md`,
hard rules); spend caps are catalogued in `moneyball-config-and-flags`.

**Live status, measured 2026-08-28 (read-only):** the `MoneyballCollectorSupervisor` scheduled task does
**not** currently exist (`schtasks /Query /TN MoneyballCollectorSupervisor` → not found), and neither
`gate1.done` nor `gate2.done` exists in the live tree. With the live target set (`fox`, `cnn-deep`) fully
sentineled as of today, the observed state means the execution-queue gates currently have **no runner**:
either the sweep's legs ran without the supervisor ever being registered, or the task was removed out-of-band
(the self-unregister at `:277-283` fires only after `gate2.done` is written, and it is absent). Recorded as
an observation for Paul — nothing was changed by this lane.

### 1.6 Two invocation paths write the same sentinels

- **Supervised path**: launcher writes `collector_targets.json` → scheduled supervisor launches detached legs
  → each success writes its sentinel → sentinels gate GATE-1/GATE-2.
- **Weekly-refresh path**: `fec/weekly_refresh.py:262-298` runs CREC (14 d window) → CHRG (400 d) → the seven
  interview legs (CNN, MTP, CBS, ABC, PBS, NPR, MS NOW; 1200–1800 s each; tolerant — a failed fetch never
  blocks the chain, `:8-9`) → the three CU extractors → big5 → … → `run_pipeline.py` (hard, gated). Its
  interview steps call the same `fetch_interviews.py`, so **each success rewrites that leg's `.done` file**
  even though weekly_refresh itself never reads the sentinels.

### 1.7 The supervisor's own marker/state files

| File | Writer | Content | Purpose |
|------|--------|---------|---------|
| `gate1.done` | `collector_supervisor.py:150` | ISO timestamp | GATE-1 ran (unconditional; see §1.5) |
| `gate2.done` | `:197` | ISO timestamp | GATE-2 complete; also the self-unregister trigger (`:277`) |
| `collector_supervisor.lock` | `:213` (read `:208`) | ISO datetime | single-instance lock |
| `data/stance/collector_progress.json` | `:96` (read `:91,240`) | `{tag: {pid, db, cpu, since}}` | wedge detection: a leg flat on DB progress (via `iv_fetch_log` count, `:68-90`) AND CPU (`CPU_EPS=1.0` s, `:36`) for `STALL_SECONDS=2700` (45 min, `:35`) is killed and relaunched |
| `data/stance/collector_supervisor.log` | `:43` | timestamped lines | append-only log |
| `collector_<tag>.out` | `:100` | leg stdout | per-leg console capture |

None of these are git-tracked; only the `.done` sentinels are.

---

## 2. Other collector-side sentinels and markers

### 2.1 `SWEEP_APPROVED` — campaign-sites 2026 approval marker

- **Required by** `fec/collect/campaign_sites_2026.py:753-761`: `--sweep` refuses (exit 2) unless
  `source_data/campaign_sites_2026/SWEEP_APPROVED` exists. Existence-only check; content unread.
- **No in-repo producer writes it** — creation is a coordinator/Paul action (the only writer is the test
  fixture, `fec/tests/collect/test_campaign_sites_2026.py:496`). Not git-tracked.
- Provenance: the marker gate was an adjudicated finding of the 2026-08-17 Codex adversarial review of the
  C1-2026 collector (STATE, collector merged `13df44998`); `SWEEP_APPROVED` for the smoke sweep was created
  under Paul-delegated authority 2026-08-17. Sweep 1 proper is late-September per
  `CAMPAIGN_SITE_COLLECTION_2026_RUNBOOK.md`.

### 2.2 `state.json` — Monday X collector success sentinel

`.claude/skills/grok-companion/scripts/monday_x_collector.py`:

- **Path**: `%LOCALAPPDATA%\melange_x_collector\state.json`; atomic writer `write_state_atomic()` `:996-1027`.
- **Fields**: `batch_format_version` (=2), `last_success_utc` (ISO or null), `failed_batches` (list).
- **Written** only after a fully successful collection (all batches, no residual failures; `:1384-1427`,
  success write `:1419-1426`).
- **Read** by `should_run()` (`:1183-1190`: run on Monday, or >7 days since last success) and
  `compute_window()` (`:1192-1196`: query window starts at `last_success_utc − 1 day`) via `:1155-1156`.
- Input path resolution `_resolve_repo_path()` `:24-44`: `data\stance\` first, legacy root fallback — the
  2026-08-25 fix for the startup death that had left `last_success_utc` null since 08-10 (STATE).

### 2.3 `weekly_refresh_status.json` — refresh health marker

`fec/weekly_refresh.py`:

- **Path**: `data/engine/weekly_refresh_status.json` (`:48`); atomic tmp-then-replace writer `_write_status()`
  (`:50-58`).
- **Fields**: `last_start`, `last_outcome`, `failures`, `rank_moves`.
- **Write sites / outcomes**: start `RUNNING` (`:148`); `KILLED_SIGBREAK` (`:161`); `FATAL_PRESTEP` (`:187`);
  `HARD_FAILURE` (`:203`); `RUNNING_AFTER_KNOWN_FAILURE` (`:232`); completion `COMPLETE` /
  `COMPLETE_WITH_KNOWN_GATED_FAILURES` (`:325`).
- Paired glassbox emission (`refresh.run` / `refresh.tolerated_failure` events) at `:149,162,188,199,227,327`
  via `surfaces/glassbox_emit.py` (`:34,41-44`) — since `fec/icloud_smtp.txt` is absent, this marker plus the
  glassbox stream IS the refresh's health reporting.
- **Live tree, measured 2026-08-28**: the marker reads `last_start="2026-08-25 20:57:00"`,
  `last_outcome="HARD_FAILURE"`, `failures=[]`, `rank_moves=null` — the 08-25 run-2 wrapper-timeout verdict
  (STATE). The healing chain ran outside the wrapper, so the marker still carries the wrapper's outcome; it
  next moves on the 08-30 Sunday run.

### 2.4 Run-completion manifests in the Congress.gov collectors

- `fec/collect/collect_congress_advanced.mjs`: writes `run_manifest.partial.json` during the run and
  `run_manifest.json` with `status: "complete"` at the end (`:270-271`, `:521`, `:528-532`). `--resume` reads
  the **partial** manifest (`:305-312`); nothing gates on the final one — it is a completion receipt, not a
  re-run guard.
- `fec/collect/collect_congress_advanced_pages.mjs`: same shape — `manifest.json`, `status: "complete"`
  (`:1414`, `:1557`, `:1610`); no re-run gate reads it.

### 2.5 In-database sentinel values

- `fec/collect/tweet_collector.py:309` — `UPDATE members SET bluesky='none-found'` with the inline comment
  "sentinel: don't re-probe on the next chunk": the literal string `none-found` in `social_media.db` marks a
  member as probed-and-absent on Bluesky so later chunks skip the lookup.

### 2.6 Partial-write guard

- `fec/collect/fetch_acu_letters.py:29` — snapshot is written to a `.partial` path and renamed on completion,
  so a crashed fetch can never masquerade as the durable ACU-letters snapshot.

### 2.7 Resume checkpoints (per-item markers, not completion sentinels)

Listed for completeness because they are the per-unit cousins of the `.done` files — each marks a unit of paid
or slow work as done so a relaunch never repeats it. They are data-plane state, not gate inputs:

| Checkpoint | Store | Writer | Keyspace |
|------------|-------|--------|----------|
| `iv_fetch_log` | `social_media.db` | `fec/members/fetch_interviews.py` | per-interview fetch log (also the supervisor's DB-progress metric, `collector_supervisor.py:68-90`) |
| `cr_fetch_log` | `social_media.db` | `fec/collect/fetch_congressional_record.py` | `crec:*`, `chrg:*` |
| `cr_fetch_log` | `social_media.db` | `fec/collect/fetch_hearings_antag.py` | `antag2:*` (v1 `antag:*` superseded) |
| `seq_log` | `hearings_seq.db` | `fec/collect/fetch_hearings_seq.py` | `seq:<pid>` |
| `fetch_log` | `social_media.db` | `fec/collect/tweet_collector.py` | per-platform/bioguide checkpoints |
| one-JSONL-row-per-URL | `press_text_cache.jsonl` | `fec/collect/fetch_press_text.py:22-28` | cached-URL set is the resume state |
| MD5 per-filing manifests | `%LOCALAPPDATA%\Melange\lda_rebuild` | `fec/lobbying/collect_lda_filings.py:79-91` | idempotent re-fetch |
| `runs/<timestamp>.jsonl` | campaign-sites out dir | `fec/collect/campaign_sites_2026.py` | resumable run log |
| file-exists cache | `fec/liwc/rkh/*.tab` | `fec/collect/fetch_rkh_data.py:20` | skip if downloaded |

---

## 3. System-manifest sentinels over the collector data plane

The second sentinel system: `data/system/system_manifest.json` (schema `melange-system-manifest-v1`, Phase 0
of containerization, landed `dfb47fc6b` → fixed `022c3c728`) records per-store **integrity sentinels** — files
whose bytes are re-checked days later by the `[SYS]` audit gate. Collector output stores are a large share of
the sentinel-bearing stores, so these are "collector sentinels" in the store-integrity sense.

### 3.1 Selection mechanics — `fec/audit/build_system_manifest.py`

- A sentinel must be content-stable: not rewritten by ordinary operation (`:50-57`).
- Per store: the `SENTINEL_COUNT = 3` (`:101`) **largest** files (`by_size … [:SENTINEL_COUNT]`, `:1066`)
  plus the single **newest** file (`:1074`) — up to 4 rows, deduped via `seen` (`:1082-1086`). Inside a git
  directory the newest-file pick is dropped (`:1074`), per **DE-011** (the newest file in a git dir is by
  construction what the last commit/push wrote — the always-red gate fixed at `022c3c728`).
- Volatility predicate `_volatile()` (`:1047-1055`): excludes `SENTINEL_EXCLUDE`
  (`__pycache__/ .pytest_cache/ .tmp .part .lock .log .swp`, `:107`) and git bookkeeping
  (`GIT_BOOKKEEPING_FILES`/`_DIRS`/`GIT_DERIVED_INDEX_PATHS`, `:136-159`); the same predicate derives each
  row's `content_stable` flag — a volatile path can never reach the manifest claiming stable bytes.
- Hashing: sentinels ≤ `SENTINEL_HASH_MAX_BYTES = 8 MiB` (`:100`) get a pinned sha256; larger record
  `sha256: null` (size+mtime evidence only). **D-015** (ruled, implementation pending) raises this cap for
  git stores, because `repo.git`'s three surviving sentinels are all over-cap → zero hash-verifiable evidence.
- Per **D-014**, `hash_always` covers only what git does not protect; a scale- or policy-refused store keeps
  its sentinel evidence — sentinels are the integrity floor for stores too big to hash or walk.

### 3.2 Checking — `fec/audit/system_manifest_check.py` (A2b)

`_check_sentinels()` (`:658-704`), invoked from four sites (`:508,513,520,548` — incomplete walks, stores over
`WALK_LIMIT = 20000` files (`:47`), and after normal A2 walks): refuses any recorded sentinel that is git
bookkeeping (`:680`, manifest defect), then asserts existence (`:686`), byte size when `content_stable`
(`:693`), and sha256 when recorded (`:697`). One verdict per store naming all disagreements. Checker and
producer hold **independent copies** of the bookkeeping predicate (`:150-197`) — the checker never imports the
producer (anti-vacuity contract).

### 3.3 Stores carrying sentinels, collector-fed stores marked ●

`integrity_policy: sentinel_files` declarations in the REGISTRY (`build_system_manifest.py:210-782`), grouped:

**Repo data plane** — `repo.source_data` ● (:292), `repo.data_stance` ● (:406), `repo.data_legislation` ●
(:411), `repo.data_lobbying` ● (:416), `repo.data_network` (:421), `repo.data_members` ● (:426),
`repo.data_money` ● (:432), `repo.data_engine` (:437), `repo.data_district` ● (:442), `repo.data_reference`
(:447), `repo.outputs` (:452), `repo.fec_code` (:488), `repo.git` (:551).

**Media/off-repo data (`C:\melange-data`)** — `mdata.npr_audio` ● (:617), `mdata.wj_audio` ● (:622),
`mdata.sunday_audio` ● (:629), `mdata.axe_audio` ● (:634), `mdata.youtube_audio` ● (:639),
`mdata.sunday_pilot` ● (:644), `mdata.bicam_zips` ● (:650), `mdata.bicam_extracted` ● (:657), `mdata.models`
(:662), `mdata.golden_run` (:667), `mdata.residual` (:674).

**LOCALAPPDATA stores** — `local.lda_sweeps` ● (:687), `local.lda_positions` ● (:692), `local.lda_derived` ●
(:698), `local.billstatus` ● (:704), `local.lobbyview_raw` ● (:713), `local.lobbyview_derived` ● (:718),
`local.demographics` ● (:723), `local.fec_spending` ● (:729).

**Mirrors / glassbox** — `mirror.melange` (:746), `mirror.glassbox` (:753), `glassbox.scripts` (:761),
`glassbox.events` (:775), `glassbox.state` (:781).

(● = the store's contents are produced or acquired by the collectors in §appendix A / the external R scrapers.
`hash_always` stores (:231-287, :529-577, :602) are protected by full hashing rather than sentinels and are
out of scope here.)

### 3.4 Known sentinel defects and open items (brain-recorded, none new here)

- **`build_system_manifest.py:960` duplicate-candidate defect** (OPEN, STATE Next-action #3): `measure()`
  appends the newest file without checking membership in the largest-by-size list; when newest == largest the
  duplicate eats a slot at `:1066` and is collapsed by the dedup at `:1082`, silently costing one sentinel
  row. Proven on `mdata.bicam_zips` (8 candidates → 2 sentinels; deduped → 3, recovering
  `bicam_hearings.zip`, 1.83 GB). Affects `mdata.bicam_zips`, `mdata.bicam_extracted`, `mdata.residual` — all
  collector-acquired stores. Nothing asserts a minimum sentinel count, so it is silent.
- **D-015 pending**: `repo.git` currently has 3 sentinels, 0 hashed (all over the 8 MiB cap); the cap raise is
  ruled, cost measurement owed.
- **DE-011 residual** (Paul-gated): `repo.fec_code` / `repo.audits` still take newest-file sentinels, so a
  commit touching a recorded path falsifies A2b — narrower than the git case, same family.
- **`.git/lost-found`** (Paul-gated): 17,174 files / 2.55 GB of 2026-07-27 `git fsck` scratch holds repo.git's
  third sentinel slot; deleting it would fail A2b while A2 stays green (DE-010 known gap).

---

## 4. Adjacent guard machinery (guards, not sentinels — listed so the boundary is explicit)

| Guard | Where | What it does |
|-------|-------|--------------|
| 28-day own-source freshness tripwire | `fec/audit/audit_full.py:610-627` | fails when CREC/hearing/interview channel inputs are >28 days older than the corpus (Paul's 3-week cadence + grace); deliberately NOT in weekly_refresh's tolerance allowlist (`weekly_refresh.py:74-79`) |
| Own-source sidecar identity | `audit_full.py:336-394` | source-row identity preserved across speech/hearing/interview extraction |
| Weekly-refresh tolerance gate | `weekly_refresh.py:67-101` | fail-closed allowlist of exactly the Paul-ratified audit dissents (culling, V-1 vote-lean); unreadable audit report = abort stands |
| Chain-tail guard | `weekly_refresh.py:114-142,220` | tolerance refused unless `audit_full.py` is textually the chain's LAST step |
| Stall/wedge detection | `collector_supervisor.py:35-36,68-96` | kill+relaunch a leg flat on DB and CPU for 45 min |
| Spend guards | `collector_supervisor.py:132-139,163,178` | `B5_GATE_CAP`/`REF_GATE_CAP`, fail-closed on unparseable estimates |
| Robots/delay/size gates | `campaign_sites_2026.py` (8 MB response cap `:33`; delay floor + redirect robots per the adversarial review) | polite collection invariants |
| Budget/census mechanism | `fetch_interviews.py` (CNN, landed default-inert 2026-08-25) | activation is a pending decision package |
| API-key redaction | `fetch_hearings_seq.py:28-35` | key stripped from logs/proxies, sent via header |

Non-collector sentinel, noted only because a bare grep will surface it: the glassbox hook-capture is
**sentinel-gated** — creating `glassbox\hookcap\ARM` re-arms a payload capture in `mirror.ps1` (DE-005).

---

## Appendix A — per-collector sentinel coverage (every collector, no exceptions)

| Collector | Completion sentinel | Other marker/sentinel | Resume checkpoint |
|-----------|--------------------|-----------------------|-------------------|
| `fec/members/fetch_interviews.py` (16 legs, §1.2) | **`collector_sentinels/<leg>.done`** | — | `iv_fetch_log` |
| `fec/collect/fetch_congressional_record.py` (CREC/CHRG) | none | — | `cr_fetch_log` `crec:*`/`chrg:*` |
| `fec/collect/fetch_hearings_seq.py` | none | — | `seq_log` `seq:*` |
| `fec/collect/fetch_hearings_antag.py` | none | — | `cr_fetch_log` `antag2:*` |
| `fec/collect/tweet_collector.py` (X + Bluesky) | none | `bluesky='none-found'` DB sentinel (`:309`) | `fetch_log` |
| `.claude/skills/grok-companion/scripts/monday_x_collector.py` | none | `state.json` `last_success_utc` (§2.2) | `failed_batches` in same file |
| `fec/collect/campaign_sites_2026.py` (C1-2026) | none | **requires `SWEEP_APPROVED`** (§2.1) | `runs/*.jsonl` |
| `fec/collect/collect_congress_advanced.mjs` | `run_manifest.json` `status:"complete"` (§2.4) | — | `run_manifest.partial.json` |
| `fec/collect/collect_congress_advanced_pages.mjs` | `manifest.json` `status:"complete"` | — | per-entry page files |
| `fec/collect/collect_congress_identifier_fast.mjs` | manifest family (same shape) | fail-closed HTML envelope validation | shard plan |
| `fec/collect/fetch_acu_letters.py` | none | `.partial` rename guard (§2.6) | — |
| `fec/collect/fetch_press_text.py` | none | — | one-row-per-URL in `press_text_cache.jsonl` |
| `fec/collect/backfill_press_text_from_rds.R` | none (stdout counts) | additive-only contract | — |
| `fec/collect/collect_fec_spending.py` | `fec_spending_manifest.json` (fail-closed) | — | — |
| `fec/collect/collect_lda_filings.py` | none | MD5 per-filing manifests | manifest = checkpoint |
| `fec/lobbying/collect_lobbyview.py` | none | manifest with `present:false` declarations (`:160`) | — |
| `fec/collect/fetch_cbp_4digit.py` | none | `CBP_FORCE` dial governs re-fetch | geo cache |
| `fec/collect/fetch_cd_geography.py` | none | `GEO_FORCE` dial | geo cache |
| `fec/collect/fetch_district_employers.py` | none | `EMP_FORCE` dial | per-geo JSON cache |
| `fec/collect/fetch_financial_branches.py` | none | `FIN_FORCE` dial | geocode + raw cache |
| `fec/collect/fetch_lodes_wac.py` | none | `lodes_panel_manifest.json` | `LODES_FORCE` dial |
| `fec/collect/fetch_rkh_data.py` | none | — | file-exists skip (`:20`) |
| `fec/members/votesmart_npat_fetch.py` | none | — | — |
| `fec/speech/houselive_collect.py` | none | hash-bearing manifest append | manifest rows |
| `fec/stance/extract_cu_{hearings,interviews,bluesky}.py` (extractors, not fetchers) | none | ADJUDICATED_RETIRED gold ledger (`own_source_stance_model.py`) governs their gold binding | CSV regeneration is idempotent |
| External R scrapers (`Desktop\Draft Systems`, CU press/bills) | out of repo | — | RDS checkpoints (consumed by `backfill_press_text_from_rds.R`) |

**The headline of the coverage table**: exactly ONE collector family (the interview legs) participates in the
`.done` completion-sentinel system; the Congress.gov `.mjs` pair write completion manifests; the X collector
and weekly refresh write success/state markers; the campaign-site collector is the only one gated on a
human-created approval marker; everything else relies on resume checkpoints plus the audit-layer freshness
tripwires.

---

## Appendix B — provenance

- Facts gathered 2026-08-28 by three read-only scout passes (repo-wide `sentinel` grep; collector-layer sweep;
  targeted deep-dives on `collector_supervisor.py`, `fetch_interviews.py`, `monday_x_collector.py`,
  `weekly_refresh.py`, `build_system_manifest.py`, the `.mjs` collectors), cross-checked against the project
  brain (STATE 2026-08-27; D-014, D-015; DE-010, DE-011, DE-012).
- Every `file:line` claim in this document was independently re-verified against the code by a separate
  verification pass on 2026-08-28 (11/11 claim groups matched exactly). Live-tree operational reads (the
  sentinel directory, gate flags, targets file, `schtasks` query, refresh status marker) were taken the same
  day, read-only.
- Brain-sourced open items in §3.4 are restated, not re-adjudicated; their gates are unchanged.
- This document is an inventory. It changes no behavior, weakens no check, and proposes nothing; anything
  actionable it mentions was already recorded and Paul-gated in the brain.
