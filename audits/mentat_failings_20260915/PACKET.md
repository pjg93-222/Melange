# PACKET — MENTAT FAILINGS LANE (2026-09-15)

S0 diagnosis. Read-only: this session edited nothing outside
`audits/mentat_failings_20260915/`.

Companion files: `HANDOFF.md` (ledger, session sections, files-owned table,
proven test commands) and `contracts/README.md` (fixture convention).

---

## 0. Scope, method, and what is NOT established

**Method.** Every claim carries a file:line or a quoted log line. Line numbers
were re-grepped against the **live working tree**, not HEAD, because the tree is
dirty. Claims that could not be settled from evidence are marked
`NOT ESTABLISHED` rather than inferred.

**Corrections to the lane brief.** The brief is wrong in three places:

1. **HEAD.** The brief says `1b8499147`. Live HEAD is
   `bd5dc8ea18a1641f3e08116f0d666fa98ba8750f`. Branch (`codex/mentat-crypto`),
   ahead-count (24) and dirty counts (58 tracked-modified, 201 untracked) all
   confirm. The tree is also **465 commits behind `main`**, which the brief does
   not mention. Every line number in the brief came from a different commit;
   several were off by 1-3 and two pointed at the wrong construct.
2. **"Rushed to finish" is not `lane_ceiling`.** The brief offers three
   candidates. The answer is **none of the three** — Area A(d).
3. **No surface drops the address fields.** The brief assumes one of three
   surfaces lacks them. All three carry them; the split is **per industry
   workbook** — Area B.

**Search-scope warning for every later session.** Collections do **not** write
into `C:\Users\pgoff\Mentat`. The console data root is
`C:\Users\pgoff\AppData\Local\Mentat\console\f897a21e05a24d1e9246b0bf972145e0\runs\`.
An initial sweep that searched only the repo returned "no hits" for every retry,
timeout and quota string; re-run against the data root it found the failure at
once. **Absence claims from a repo-only search are worthless here.**

**The evidence run.** Credit-unions run `20260915T152258-18548` started
2026-09-15 15:22:58 with 10 lanes and terminated after 1116.5 s. Final tally:
**19 of 30 tasks succeeded, 11 permanently failed**, every failure
`status=HTTP_403`. Final stdout line:

```
MENTAT API FANOUT FAILED succeeded=19/30 merged=False wall=1116.546s receipt=...\fanout-receipt.json
```

---

## AREA A — Collection

### A(d) The exact failure, with its log line

```
TASK FAILED: Navy Federal Credit Union 2024 | rows=0 requests=0 retries=0 wall=125.830s |
FEC API request failed after 1 attempt(s): status=HTTP_403;
query=https://api.open.fec.gov/v1/schedules/schedule_a/?per_page=100&two_year_transaction_period=2024
&sort=-contribution_receipt_date&contributor_employer=NFCU&min_date=04%2F01%2F2023&max_date=04%2F30%2F2023;
API key redacted.
```

`...\runs\20260915T152258-18548\industries\credit-unions\fanout\lanes\lane-03\process.log`,
2026-09-15T19:36:57Z (15:36 local).

**How to read this line — one trap.** `rows=0 requests=0 retries=0` is a
**reporting artifact, not a measurement**. `mentat/tools/collect_api_lane.R:409-415`
hardcodes all three to zero on *any* error before the receipt and the
`TASK FAILED:` line are written:

```r
    if (inherits(collected, "condition")) {
      status <- "failed"
      error_message <- conditionMessage(collected)
      retries <- 0L
      requests <- 0L
      rows <- 0L
```

Two facts in the same line contradict the zeros: `wall=125.830s`, and the URL
carries `min_date=04/01/2023&max_date=04/30/2023` — a **decomposed date-window
child query**, which only exists after a parent query was fetched, found
unservable, and split (`fec_api.R:1121-1135`). Many successful requests preceded
this 403. The task died deep into real work, not on arrival.

**`after 1 attempt(s)` is real**, and it is the diagnosis. The retry classifier,
verbatim at `mentat/R/fec_api.R:501-502`:

```r
      retryable <- status == 0L || status == 429L ||
        (status >= 500L && status <= 599L)
```

**403 is outside that set.** With `retryable == FALSE` and `status != 200L`, both
middle branches (`:506`, `:512`) are short-circuited by their leading
`retryable &&`, so control falls to the `else` at `:520` on the **first pass**,
where `attempts[[index]]` is already `1` (incremented at `:467`). The `stop()` at
`:534-542` therefore emits exactly `status=HTTP_403` and `after 1 attempt(s)`.

Consequently the Retry-After handling (`:513`), the exponential backoff with
jitter (`:515`), the `FEC_API_RETRY_AFTER_CAP_SECONDS <- 120` cap (`:6`, applied
`:291-305`) and the five-attempt loop (`FEC_API_MAX_ATTEMPTS <- 5L`, `:4`) are
**all dead code for this failure mode**. It also explains why **`HTTP_429`
appears nowhere in the run**: a 429 would be retried five times with backoff and
would surface only as the quota message.

**The message fork.** Both failure strings live in the same `else` block; the
branch is one condition at `:522`, `if (status == 429L) {`:

- **429 only** → `:525-528`, *"FEC API quota remained rate-limited after N
  attempt(s). Checkpoints are saved; resume after reset."*, thrown with class
  `c("mentat_api_quota_exhausted", "error", "condition")` (`:531`). This is the
  class `is_pause_condition` recognises (`:2410-2415`), so **only this becomes
  `paused = TRUE`**.
- **everything else non-retryable, including 403** → `:535-540`, thrown as a
  plain `stop(..., call. = FALSE)` with **no condition class**. It is caught at
  `collect_api_lane.R:409-411` as a bare condition → `status <- "failed"`, never
  `"paused"`. **A 403 is structurally indistinguishable from a crash.**

**The 403 response body is discarded.** `:521` builds `status_label` from the
numeric status alone; nothing logs `response$body`. So the api.data.gov error
code inside the 403 — `OVER_RATE_LIMIT` versus `API_KEY_INVALID` /
`API_KEY_DISABLED` / `API_KEY_UNAUTHORIZED` — **is not preserved anywhere**. This
is the single most important missing datum in the lane.

**Why this is a Mentat defect regardless of which 403 it is.** The identical call
succeeds later:

| Lane | Company / cycle | Outcome |
| --- | --- | --- |
| 01 | SchoolsFirst FCU 2026 | 403 at 19:23:08, **succeeded 19:32:41, 605 rows** (gap 9m33s) |
| 06 | America First CU 2022, 2024 | 403 on attempt 1, both recovered on attempt 2 |
| 07 | Golden 1 CU 2024 | 403 on attempt 1, recovered on attempt 2 |
| 02 | Boeing Employees CU 2022, 2024 | 403 on all four attempts, never recovered |
| 03 | Navy Federal CU 2022, 2024, 2026 | 403 on every attempt, 0/3, total loss |
| 04 | PenFed 2022, 2024 | permanent 403; 2026 succeeded 19:39 |
| 05 | Alliant CU 2022 | permanent 403 |

A status that succeeds unchanged nine minutes later is **transient**. Classifying
it as fatal converts a self-clearing condition into permanent data loss.

### A(d) — 403 is never attributed to a key, anywhere in production

This is the finding S1 should build on.

- **The pool only recognises 429.** `mentat/tools/api_request_pool.py:105` is
  `if result.get('status')==429:`. There is no 403 branch, so a 403-returning key
  is never cooled down, never deprioritised, and is handed straight back out by
  the round-robin at `:96-98`.
- **R never attributes a 403 to a key.** `fec_api.R:534-542` names the query and
  redacts the key; nothing increments a per-key counter. 403 is absent from the
  retryable set (`:501-502`), from `is_pause_condition` (`:2411-2414`), and from
  the unservable classification (`:506-511`, which is 504-only).
- **The fanout never attributes a 403 to a key** — grep for `403` across
  `api_company_cycle_fanout.py` returns nothing.
- **The one function that could disable a key on 403 is dead code.**
  `mentat/tools/fec_key_store.py:154-159`:

```python
def record_validation_locked(results,path):
    data=json.loads(crypt(path.read_bytes(),decrypt=True))
    disabled=data.setdefault('disabled',{})
    for result in results:
        if result['status'] in ('http_401','http_403'):disabled[result['key_id']]=result['status']
```

  It has **zero production callers**. `server.py:51` imports `load_keys`,
  `save_keys`, `environment_keys`, `status` — not `record_validation`, not
  `set_disabled`. `main()` (`:169-193`) has no `--validate` flag. It is exercised
  only by `mentat/tests/test_fec_key_store.py:12,36,41`.
- **Even a disabled key would still be used.** `load_keys` filters the disabled
  map (`fec_key_store.py:63-69`), but the fanout reaches `load_keys()` only as a
  last-resort fallback (`api_company_cycle_fanout.py:122-124`). A run launched
  with `--keys-file` or `FEC_API_KEYS` — how the console launches it — **never
  consults the disabled list**.

**Leading hypothesis, NOT ESTABLISHED: per-key quota exhaustion presenting as
403.** Keys are bound one-per-lane and constant for every task in that lane
(`:1164-1165`), and recovery reuses the same key when `spare_keys` is empty
(`:1483-1492`), so a task that succeeds on a later attempt succeeded *on the same
key at a later time* — which requires a time-varying, self-clearing key
condition. An invalid or permanently-disabled key does not clear in nine minutes.
But because the 403 body is discarded at `:521`, "quota" and "authorization that
happened to clear" are **not separable from anything on disk**. S1 must not
assume the quota reading. Confirmation steps are listed in section 8.

### A(a) Recovery passes and delay

**Exactly two recovery passes — three attempts total — with ZERO delay between
them.** No max-attempt constant and no loop counter exist; the bound is
structural, declared as a literal three-element list at
`mentat/tools/api_company_cycle_fanout.py:1227-1231` and again at `:1753-1757`:

```python
        "recovery_ladder": [
            "primary_lane",
            "fresh_lane_retry",
            "fresh_company_cycle_split",
        ],
```

- Rung 1 to 2 (`fresh_lane_retry`): failures accumulate per lane (`:1441-1452`)
  and are submitted immediately at `:1498-1510`. No sleep.
- Rung 2 is **drained once, never iterated** (`:1512-1533`) — results are
  appended, never re-submitted. The `timeout=1` is the status-file write cadence,
  not backoff.
- Rung 3 (`fresh_company_cycle_split`, `:1539-1546`) splits each still-failed
  task into its own single-task run at `attempt = recovery_run.attempt + 1`
  (`:1553`), one queued split per lane (`:1608-1611`). Also drained once
  (`:1614-1634`); control then falls to `combine_task_results` at `:1636`.

The only waits in the entire ladder are three
`concurrent.futures.wait(..., timeout=1)` polls (`:1436-1440`, `:1524-1528`,
`:1625-1629`). Real backoff exists only *inside* one attempt, in R.

**Consequence:** a task failing for a time-based reason burns all three rungs in
seconds. This is why lane 03 exhausted its ladder while lane 01's identical
failure survived — lane 01 happened to be re-dispatched 9m33s later.

**And the ladder usually cannot even change the key.** Keys are bound one per
lane at `:1164-1165` (`key=keys[index]`, `key_id=key_id(keys[index])`), with
`lane_count = max(1, min(len(keys), len(companies)))` (`:1083-1090`), so two lanes
never share a key on the primary path. Spares are whatever is left over —
`spare_keys = keys[lane_count:]` (`:1091`) — and rung 2 uses one only when
`run.lane <= len(spare_keys)` (`:1483-1492`), otherwise `else run.key`. **Rung 3
has no spare-key logic at all** and always copies the recovery key (`:1583-1584`).

With 10 lanes and 10 keys, `spare_keys` is empty and **every recovery replays on
the key that just failed, within seconds**. Whether that was this run's
configuration is being read from `manifest.json`'s `spare_key_count`; see
section 8.

The resume guard at `:1061-1065` protects the same invariant:

```python
        if len(keys) < lane_count:
            raise RuntimeError(
                f"Resume requires at least {lane_count} configured keys so "
                "existing lanes never share a key concurrently."
            )
```

### A(b) Terminal state after recovery is exhausted

Literal terminal status is **`"failed"`**. The full vocabulary is
`succeeded` / `failed` / `paused` / `skipped`, plus stage strings
`collecting` / `recovering` / `splitting` / `merging`. There is **no
`"exhausted"` and no `"PARTIAL"`** anywhere in this path.

Observed in the run receipt:

```json
{
  "company": "Alliant Credit Union",
  "cycle": 2022,
  "status": "failed",
  "task_id": "alliant-credit-union-2022",
  "error": "FEC API request failed after 1 attempt(s): status=HTTP_403; ..."
}
```

Other terminal writes: Rscript dying before a receipt →
`"Managed Rscript exited with code N before producing a task receipt."`
(`api_company_cycle_fanout.py:577-585`); no receipt in any attempt →
`"No task receipt was produced."` (`:807-811`); operator stop → `"skipped"`
with `"Operator stopped the run before this lane started."` (`:655-669`).

**DE-020 repeats itself one layer down.** A budget pause *is* correctly captured
as task status `"paused"` (`collect_api_lane.R:409-430`), reaching the task
receipt (`:442-458`) and a `run_log` row (`:431-441`; `run_id` is per-task at
`:377`, so rows do not collide). Then the lane aggregate destroys the
distinction — `collect_api_lane.R:486-493`:

```r
  failed <- sum(vapply(
    task_receipts,
    function(task) !identical(task$status, "succeeded"),
    logical(1L)
  ))
  ...
    status = if (failed) "failed" else "succeeded",
```

The fanout re-applies the same predicate at `:480`
(`if item.get("status") != "succeeded"`). A by-design budget pause is therefore
fed into rungs 2 and 3 indistinguishably from a crash — exactly DE-020's failure
mode. The design already proves the distinction is expressible: an operator stop
earns its own exit code 3 and an explicit comment (`:1792-1795`).

**The converse matters more here, and is the live failure mode: a non-429
throttle cannot reach `"paused"` at all.** The pause classes are assigned only at
`fec_api.R:523-532` (429) and `:65-79` (budget). If 403 is api.data.gov's
throttle for this key type, **every PARTIAL-handling mechanism in the system is
bypassed.**

**Failures ARE surfaced — this is a genuine strength, and S1 must not "fix" it.**
Aggregation is first-class: `combine_task_results` at `:1636`, then
`"succeeded": task_total - len(final_failed)` and `"failed": len(final_failed)`
(`:1743-1744`), `"tasks"` and `"failures"` arrays (`:1771-1772`), every attempt's
metadata (`:1773-1780`), `final_failed` into `status.json` (`:1725`), and a
stdout summary (`:1786-1791`). Observed in the run:

- run `status.json`: `"stage": "failed"`
- run `summary.json`: `"status": "failed"`
- `fanout-receipt.json`: `"failed": 11, "succeeded": 19, "task_count": 30`,
  `"merge": {"attempted": false}`
- `events.jsonl`: `{"event":"industry_failed","industry":"Credit Unions",...}`

No per-lane `process.log` is needed to see the run failed. **The reporting layer
is not the defect.**

**One reporting-fidelity defect, minor but real — DEFECT-EXIT-CODE.** Python
returned **2**, its documented "failed tasks remain" code (`:1799`:
`return 0 if final_status == "succeeded" else 2`), and printed its normal summary
line. The PowerShell wrapper rewrote it, so the run detail records
`"Fanout failed: exit=1; stderr=...fanout.stderr.log"`, with
`fanout.stderr.log` holding
`System.Management.Automation.RuntimeException: API company-cycle fanout exited with code 2.`
**exit=1 is not a documented fanout code**, so a triager reading `status.json`
sees an undocumented value and must open two more files to learn it was an
orderly failure. Wrapper artifact, not a crash.

Because failures remained, the source database was **never merged** (`:1646`), so
lane snapshots are intact on disk and the run is resumable.

### A(d) — what the runtime evidence rules IN and OUT

The run's `manifest.json` reports `configured_key_count: 22`,
`spare_key_count: 12`, and **empty** `key_cap`, `lane_ceiling` and
`active_lane_cap`. Spares were available and recovery did hand out fresh keys.

Per-key budget table (`...\runtime\mentat\.cache\fec-api-budget.sqlite`,
`SELECT budget_id, window_started_epoch, requests_used FROM api_request_budget`),
joined to lanes by the last 12 hex characters of `budget_id`:

| Lane | Initial key_id | requests_used | Tasks | Succeeded | Failed |
| --- | --- | --- | --- | --- | --- |
| 1 | f8c6aab098e3 | 45 | 3 | 2 | 1 |
| 2 | 4389427ebe2b | 45 | 3 | 1 | 2 |
| 3 | 13ffe51ce05b | 46 | 3 | 0 | 3 |
| 4 | a48ff6b7adf9 | 45 | 3 | 1 | 2 |
| 5 | 51243b3c7ca0 | 42 | 3 | 1 | 2 |
| 6 | 41d6b623c056 | 45 | 3 | 2 | 1 |
| 7 | c934edc83dcc | 43 | 3 | 2 | 1 |
| 8 | 3eb6e9f1ae29 | 43 | 3 | 3 | 0 |
| 9 | 40cdaa7ca0b4 | 45 | 3 | 0 | 3 |
| 10 | c008cd76d027 | 43 | 3 | 3 | 0 |

Recovery keys (0e0b6ee1c03a, c6bfedd0d49a, 838eabba069c, f1c6dfbfac2c,
cbcb95fcffcd, 576eb6d665fb, ca20849db80e and others) all sit at 42-45.

**RULED OUT — per-key quota exhaustion.** Every one of the 22 keys sits between
**42 and 46 requests against a cap of 1000** (`FEC_API_HOURLY_REQUEST_CAP <- 1000L`,
`fec_api.R:7`). Failing keys (45, 46) and succeeding keys (43, 45) are
indistinguishable. Nothing was close to a quota. **The leading hypothesis stated
above is refuted by this table**, and no later session should revive it without
new evidence.

**RULED OUT — the key itself.** Lane 3 ran initial key `13ffe51ce05b` and
recovery key `838eabba069c` and failed all three cycles on both. A failure that
follows a task across a key change is not a property of the key.

**RULED OUT — `lane_ceiling`.** Empty in the manifest, and in code it bounds
concurrency rather than coverage (d-5 below).

**UNDECIDABLE FROM STORED DATA — key-specific versus query-specific.** The
fanout assigns **exactly one company per lane**, so lane and company are
perfectly confounded: no arrangement of this run's data separates "this key
failed" from "these companies' queries failed". The failures do cluster by lane
(3 and 9 lost every cycle; 8 and 10 lost none), but that observation is equally
consistent with both readings. An earlier agent report asserting "failures
cluster by LANE, not by COMPANY" **overreached and is corrected here.**

**Therefore the true headline is a diagnosability defect, not a retry defect:**

> **DEFECT-403-OPAQUE.** `fec_api.R:521` builds `status_label` from the numeric
> status alone and nothing logs `response$body`, so `OVER_RATE_LIMIT`,
> `API_KEY_INVALID`, `API_KEY_DISABLED` and `API_KEY_UNAUTHORIZED` all collapse
> into the single string `HTTP_403`. **Mentat discards the only field that
> explains its most common failure.** Until the body is observable, any retry or
> key-rotation policy is guesswork.

S1's first deliverable is making that body observable. Everything else in Area A
is downstream of it.

### A(c) Does the chromote path checkpoint before it raises?

**Split answer.** The only checkpoint writer on this path is the `page_callback`
at `mentat/R/collect.R:1771` (handed down at `:1759-1783`), each call its own
committed transaction (`:1605-1606`).

| Raise | Reached via | Checkpointed? |
| --- | --- | --- |
| `fec_page.R:192` "Timed out waiting for the FEC results table." | `fec_click_next` (`:412`), bottom of the page loop `:1239-1250` | **YES** — pages 0..N committed; only the un-read next page is lost |
| `fec_page.R:192` same string | `fec_navigate` (`:221-224`) via `:1173-1178` | **NO** — the loop calling `page_callback` starts at `:1202`; nothing was read, nothing lost |
| `fec_page.R:535` "Timed out waiting for the FEC export." | `fec_export_current_query` (`:1067-1068`) | **NO** — `consume_export` (`:1034-1053`) runs at `:1096` only after a *successful* export; zero rows checkpointed |

Both raises are classified transient (`fec_page.R:439-453`) and trigger a full
replay from page 0, up to `query_retries = 3L` + 1 (`:1273`, `:1281`), with
`fec_query_retry_sleep(attempt) = min(15, 2^attempt)` (`:461-462`). Replay is
safe against double-insertion: `contributions` is keyed `sub_id TEXT PRIMARY KEY`
(`schema.R:14`) and writes use `insert_rows_or_ignore` (`collect.R:1566-1571`).

**On the API path, aborts do flush.** `fec_api.R:2211-2216` and `:2242-2245`
document a wrapper that catches **every** abort path, not only budget/quota,
flushes fetched work to checkpoints, prints
`"FEC API pause flush: stored %d fetched work unit(s) before pausing."` (`:2236`)
and re-signals the original condition (`:2256`). So a 403 landing mid-unit does
preserve already-fetched pages; a 403 on a unit's first request leaves nothing.
**NOT DETERMINABLE FROM CODE** which case a given task hit — the log line's
hardcoded zeros cannot tell you. Settle per task with
`SELECT unit_id, COUNT(*) FROM api_page_checkpoints GROUP BY unit_id` and the
`api_work_progress` table (`schema.R:72`) in that lane's database.

**Three secondary defects on the chromote path:**

- **DEFECT-EXPORT-FALLBACK.** An export *timeout* never reaches the browser-API
  fallback at `fec_page.R:1110-1118`. The guard at `:1100-1106` re-raises unless
  the message contains `"fec export server error"`, which the timeout message
  does not. Only a server-side export error gets the fallback.
- **DEFECT-EXPORT-CHUNK.** `fec_page.R:1179-1181` documents a 100-rows-per-page
  checkpoint contract, but `consume_export` checkpoints in 20,000-row chunks with
  a synthetic page number `page = floor((processed - 1L) / 100L)` (`:1043`,
  `chunk_size = 20000L` at `:1026`). A mid-export crash leaves `scrape_progress`
  at a chunk boundary and the variant_set restarts from zero.
- **DEFECT-RESUME-OPT-IN.** Checkpoints are always *written* but only *consumed*
  on request: `completed_scrape_checkpoint` returns `NULL` unless `resume_after`
  is non-empty (`collect.R:1652-1655`), and the only producer is the
  `--resume-after=` flag (`mentat/mentat.R:126-131`), chrome-engine only
  (`:146-148`). A normal re-run ignores every checkpoint it wrote.

Also noted, deliberate but worth knowing: rows that *were* read are discarded on
an integrity refusal — `fec_page.R:1219-1223` (canary failure) and `:1232-1236`
(repeated sub_id) raise after the payload is read but before `page_callback` at
`:1239`, by design (`:443-445`: "Never accept that page").

### A(d) Full census of early-exit mechanisms

Eight mechanisms can end a collection with less than complete data.

| # | Mechanism | Constant / value | Live line | On hit |
| --- | --- | --- | --- | --- |
| **d-8** | **non-retryable status, incl. 403** | **inline set, no constant** | **`fec_api.R:501-502`, raise `:534-542`** | **hard fail after 1 attempt; NOT a PARTIAL. THIS RUN'S CAUSE.** |
| d-1 | per-key hourly budget | `FEC_API_HOURLY_REQUEST_CAP <- 1000L`, window `3600` | `fec_api.R:7-8`, raise `:120-121` | PARTIAL (`"paused"`), distinguishable only at task level |
| d-2 | 429 quota after retries | `FEC_API_MAX_ATTEMPTS <- 5L` | `fec_api.R:4`, raise `:523-532` | PARTIAL (`"paused"`), same |
| d-3 | bulk name-rescue cap | `MENTAT_RESCUE_CAP` default `"50"` | `fec_api.R:1612`, swallowed `:1728-1734` | **silent truncation; run reports `"succeeded"`** |
| d-7 | page ceiling per unit | `FEC_API_MAX_PAGES_PER_UNIT <- 10000L` | `fec_api.R:5`, raise `:1260-1266` | hard fail, specific message |
| d-4 | operator stop | `control.json` | fanout `:1364-1372` | PARTIAL, exit 3, fully distinguishable |
| d-5 | lane ceilings | `--max-lane-ceiling` default `0`; `active_lane_cap` | fanout `:922`, `:250-266`, `:328-330` | throughput only, **no data loss** |
| d-6 | caller-side page cap | `max_pages = 1L` probe; default `Inf` | `collect.R:2926`; `fec_page.R:1161` | probe-then-decompose; `truncated` flag at `fec_page.R:1256` **read by nobody** |
| — | pool exhaustion | `cap=1000, window=3600`; R `timeout = 0` | `api_request_pool.py:39`, `:91-99`; `fec_api.R:414` | **unbounded block**, not an early exit |

**Answer to the brief's question.** "Rushed to finish" is **none of** the three
candidates offered (per-key budget, `lane_ceiling`, caller-side page cap). It is
**d-8**: tasks dying on their first request because 403 is not retryable.

**DEFECT-RESCUE-CAP — the one true silent failure.** `MENTAT_RESCUE_CAP` defaults
to **50**. On hit, the condition is caught inside the loop (`fec_api.R:1728-1734`),
remaining candidates are written to `bulk_rescue_overflow.csv` (`:1906-1911`)
tagged `"rescue_request_cap"` (`:1791`), and the function **returns normally**
(`:1792-1802`). `mentat_rescue_cap_reached` is not in `is_pause_condition`
(`:2411-2414`), so the run reports `paused = FALSE` and the task reports
**`"succeeded"`**. This is the only mechanism in the path that ships an
incomplete collection as a success. Whether 50 is a deliberate budget (DE-020's
"designed PARTIAL") or an oversight is **Paul's call, not a session's.**

**DEFECT-POOL-BLOCK — the opposite failure, an unbounded hang.** With a shared
request pool, R skips its own budget reservation (`fec_api.R:2401-2406`); the
pool cools an exhausted key and returns `False` (`api_request_pool.py:81-82`),
then spins with no timeout (`:91-99`) while R waits on `timeout = 0`
(`fec_api.R:413-414`). Every key exhausted and no operator stop means a lane does
not pause, fail, or exit — it blocks for up to 3600 s per key, invisible to the
fanout except as stage `"collecting"`. **NOT ESTABLISHED** whether real runs hit
this; this run did not use the pool (no `MENTAT_REQUEST_POOL_URL` in the lane
logs; the budget rows were written by the lane processes).

### A(e) D-029 and the restart gate — BOUNDED, NOT REVERSED

The gate is real and fail-closed. `mentat/app/server.py:1868-1870`:

```python
            if self.path == '/api/restart':
                if console_busy(self.server.app):
                    return self.send({'error': 'Collection is running. Restart after it finishes.'}, 409)
```

`busy()` (`:524-528`) returns True on `self.preparing`, `self.jobs`, or any live
child in `self.processes`; `console_busy` (`:147-158`) returns **True on any
exception** — "never stop work on a guess". `Start-MentatApp.ps1:87-101` applies
the same test from outside and refuses to kill a server that does not state
`busy == $false`. The 403 branches on that POST path (`:1837`, `:1840`, `:1843`
read-only preview; `:1846` token/host; `:1850` cross-origin) all precede the
restart dispatch; the restart handler's own rejection is the 409.

**The bound:** all three inputs to `busy()` are in-process. `self.processes` is
populated only where the console spawns its own child (`:754`, after the `Popen`
at `:746-749`); `self.preparing` / `self.jobs` are in-memory (`:514-516`). There
is **no filesystem, lock-file or PID check in `busy()`** — although the console
already contains exactly that machinery and uses it when *starting* a collection,
`:653-656`, which scans `*/upload.json` and probes recorded PIDs with
`process_alive()` (`:233-251`).

Three blind spots, increasing in severity:

1. A collection owned by a **second console process** on the same data root: seen
   by `launch()`, not by `busy()`.
2. A **fanout or lane launched from a shell** writes no `upload.json` under the
   console root, so neither check sees it.
3. The launcher's kill (`Start-MentatApp.ps1:166`, `Stop-Process -Force`) rides
   the same flag, so a stale console can be force-killed while an external
   collection runs. The kill does not touch that process, but does drop the
   console-side state it reports into.

**Has D-029's reversal condition been met?** *"a restart is observed killing an
in-flight collection job, or Paul withdraws same-port reuse."* **NO.** No restart
was observed coinciding with any lane death; all 11 failures are HTTP_403 and no
server restart banner falls within 120 s of one. **D-029 STANDS.** What is
recorded here is a bound on its meaning: "IDLE" means *idle with respect to this
process's own children*.

**NOT ESTABLISHED:** whether an externally launched lane writing into the same
lane database would actually be corrupted by a console restart. Settling
evidence: run the fanout from a shell against a data root a console is serving,
POST `/api/restart`, observe whether the answer is 409 or `restarting:true` (code
says the latter), then check `PRAGMA quick_check(1)`
(`collect_api_lane.R:482-485`).

### A — separate defects found in passing

**DEFECT-KEYSTORE.** `.tmp\cross-reference-preview\server.stderr.log`,
2026-09-11 17:40, **3.59 MB containing 1,975 identical tracebacks**:

```
RuntimeError: Windows could not access the encrypted FEC key store for this user.
```

`mentat/tools/fec_key_store.py:49` in `crypt()`, reached via `server.py:929`
`do_GET` → `:624` `summary()` → `fec_key_store.py:66` `load_keys()`. This is a
**cross-reference preview server**, not a collection lane, so it is not Area A's
answer. It is recorded because a server that emits 1,975 identical unhandled
tracebacks instead of failing once and reporting the condition is a
silent-failure surface in its own right. **NOT ESTABLISHED** whether it still
reproduces.

**DEFECT-DEAD-403-HANDLER.** `fec_key_store.record_validation_locked`
(`:154-159`) marks a key disabled on `http_401`/`http_403`. It is tested
(`mentat/tests/test_fec_key_store.py:12,36,41`) and has **zero production
callers** — `server.py:51` does not import it, `main()` (`:169-193`) has no
`--validate` flag, and nothing constructs a `{'status': 'http_403'}` result. Even
if a key were disabled, the fanout consults the disabled list only as a
last-resort fallback (`api_company_cycle_fanout.py:122-124`), bypassed whenever
keys arrive via `--keys-file` or `FEC_API_KEYS` — which is how the console
launches it.

**Disk note, outside this lane.** `mentat\state\cross-reference\` holds **five
`ledger.sqlite` files of 3.4-3.6 GB each** (2026-09-12 to 09-13), roughly 17 GB.
Not corrupt, genuinely that large.

---

## AREA B — Address fields

**The brief's premise does not hold as stated.** No *surface* drops the five
fields. Four of eight published workbooks lack them — **because those workbooks
carry no per-contribution rows at all, by documented design.** And street, the
one field genuinely absent everywhere, **arrives from openFEC on every page and
is discarded by the collector.**

### B — schema and collection carry the five fields

`corporate_giving` (`mentat/R/schema.R:255-281`): `contributor_id`,
`contributor_name`, `contributor_city`, `contributor_state`, `contributor_zip`,
`contributor_employer`, `contributor_occupation`. **No street column.**

Populated at `mentat/R/collect.R:1266-1270`, carried in the SELECT list at
`mentat/R/fec_api.R:2003-2004`:

```r
      contributor_city = page_text("contributor_city"),
      contributor_state = contributor_states,
      contributor_zip = page_text("contributor_zip"),
      contributor_employer = employer_values,
      contributor_occupation = occupation_values,
```

**Live production data confirms it.** Evidence run `20260915T152258-18548`, all
eleven databases copied and opened read-only:

| Database | Size | `corporate_giving` rows | City | State | ZIP | Employer | Occupation | `api_page_checkpoints` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data/mentat.db | 860 KB | 0 | — | — | — | — | — | 0 |
| lane-01 | 33.9 MB | 228 | 100% | 100% | 100% | **0%** | **0%** | 0 |
| lane-02 | 12.1 MB | 24 | 100% | 100% | 100% | 91.7% | 91.7% | 2 |
| lane-03 | 28.5 MB | 0 | — | — | — | — | — | 6 |
| lane-04 | 34.0 MB | 0 | — | — | — | — | — | 12 |
| lane-05 | 3.6 MB | 1 | 100% | 100% | 100% | 100% | 100% | 0 |
| lane-06 | 15.0 MB | 0 | — | — | — | — | — | 0 |
| lane-07 | 8.6 MB | 15 | 100% | 100% | 100% | 100% | 100% | 0 |
| lane-08 | 43.1 MB | 3132 | 100% | 100% | 100% | 99.7% | 99.7% | 0 |
| lane-09 | 55.3 MB | 0 | — | — | — | — | — | 22 |
| lane-10 | 8.7 MB | 6 | 100% | 100% | 100% | 100% | 100% | 0 |

City/State/ZIP are at 100% wherever rows exist; 3,406 rows in total.

**DEFECT-EMPLOYER-ZERO.** Lane-01's 228 rows carry `contributor_employer` and
`contributor_occupation` as the empty string `''` on **every** row — not NULL,
not sparse — while City/State/ZIP are populated on every row
(`('LOS ANGELES', 'CA', '900713314', '', '')`). Every other populated lane is at
92-100%. Cause **not established**; S2 explains it before any employer-keyed
join is trusted.

### B — the three export surfaces all carry the fields (code)

| Surface | Verdict | Evidence |
| --- | --- | --- |
| Raw warehouse export | **PRESENT** | `export_raw_contribution_warehouse.py:244-263` introspects `PRAGMA table_info` and exports **every** schema column; no allow-list or deny-list. Selection at `:357-359`. |
| Workbook builder (R stage) | **PRESENT** | `export_crypto_spending_data.R:534-538` names `city`, `state`, `zipcode`, `employer`, `occupation` |
| Chart Studio detail sheets | **PRESENT** | `contribution_data.py:48-58` `DIMENSIONS` includes `state`, `city`, `zip5`, `employer`, `occupation`; populated `:346-348`; row cap `MENTAT_DETAIL_ROW_CAP` default 45000 at `:679` |

### B — WHICH workbooks lack them, and WHY: a 120 MB layout switch, by design

Verified by dumping rows 1-10 of every plain cycle sheet in all eight published
workbooks at `C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files`
(`receipts/S0_area_b_workbooks.md`). Two layouts come out of the same builder:

| Layout | Row-1 title | Header (row 4) | Industries (rows per cycle sheet) |
| --- | --- | --- | --- |
| **Contributions**, 35 cols | `2021-2022 Crypto Contributions` | Source ID, Cycle, FEC Filing Cycle, Cycle Alignment, Company, Contributor, Employee Tier, Amount, Analysis Amount, Party, Recipient Category, Category Source, Party Source, Recipient, Committee ID, Recipient Key, Date, **City, State, ZIP, Employer, Occupation**, Record Type, Source Table, Company Match Status, Include in Analysis, Inclusion Reason, Person Key, Identity Basis, Memo Leg, Conduit Leg, Superseded Amendment, Duplicate Filing Version, Duplicate Memo, Logic Check | Crypto (1067 / 3387 / 1863), Community Banks (1348 / 1827 / 803), Credit Union (7653 / 14766 / 5112), Fintech (7114 / 12728 / 5078) |
| **Formula Facts**, 12 cols | `2021-2022 Banking Formula Fa…` | Fact Type, Company, Employee Tier, Amount, Analysis Amount, Party, Recipient Category, Recipient Key, Gift Count, Include in Analysis, Person Key, Logic Check | **Banking** (5963 / 6229 / 4684), **Telecom** (4816 / 5010 / 4067) |
| **Formula Facts**, 18 cols | `2021-2022 Credit Arms Formul…` | Fact ID, Cycle, Fact Type, Cycle Alignment, Company, Contributor, Employee Tier, Amount, Analysis Amount, Party, Recipient Category, Recipient, Committee ID, Recipient Key, Gift Count, Include in Analysis, Person Key, Logic Check | **Credit Arms** (18640 / 21777 / 15243), **Property & Casualty** (12534 / 19830 / 9831) |

One Banking row, verbatim: `Master | Wells Fargo Bank NA | Employee | 1015474.38 | … | Carey | Gift Count 44721`.
Forty-four thousand gifts in one cell. **There are no contributor columns
because there are no contributor rows.**

**The switch** — `mentat/tools/build_industry_report.ps1:601`:

```powershell
$largePayloadThresholdBytes = 120MB
```

and the decision at `:614-625`: `formulaFactsMode` is taken from
`priorFormulaFacts` whenever that is set to `'0'` or `'1'`; otherwise it is
`'1'` when the staging payload file's length is at or above
`largePayloadThresholdBytes`, else `'0'`. So a staging payload of **120 MB or
more** selects Formula Facts, and **the decision is sticky:** an industry once
built as Formula Facts stays that way on every rebuild regardless of current
size.

**The projection that strips the fields** — `mentat/tools/prepare_workbook_payload.py:12-16`
defines `RAW_FIELDS` (22 keys: cycle, company, amount, tier, party, recipient
category, recipient/represented state and location evidence …) with **no
`zip5`/`zipcode`, `city`, `state`, `employer` or `occupation`**; `:41-46` `project()`
filters every `raw_rows` record to those keys and stamps
`metadata['workbook_projection'] = 'formula-facts-v1'`. The flag is read at
`finalize_crypto_excel.ps1:228` (`$formulaFacts = [bool]$payload.metadata.formula_facts`)
and `verify_repaired_reports.py:82` filters on `row.get('Fact Type','Master')=='Master'`.

**This is documented intent, not an accident.** `mentat/R/report.R:1785-1787`,
verbatim:

> the raw transaction sheet is the first thing a large industry loses:
> tools/prepare_workbook_payload.py projects raw_rows onto 18 fields that carry
> no ZIP, city, state, employer or occupation, and formula-fact mode replaces
> raw_rows outright with aggregate facts.

And the designed remedy already exists in the tree — `mentat/R/tidy_stage.R:14-17`:

> tools/prepare_workbook_payload.py, whose RAW_FIELDS projection drops geography,
> employer and occupation from large industries. A Banking build therefore gets
> full-width receipt rows here regardless of MENTAT_COMPACT_RAW.

The tidy staging store feeds `mentat/tools/build_tidy_workbook.py` (**present on
disk**; `CONTRIBUTIONS` = 56 fields incl. `city`, `state`, `zip5`, `zipcode`,
`employer`, `occupation` at `:113-153`; `Sheet("contributions", ...)` at `:357`),
which produces the companion `<Industry> Industry Spending Data.xlsx`. **That
companion is the designed delivery vehicle for large-industry per-contribution
detail — and it has never been built for a real industry.** Only the tidy lane's
mock exists (`audits/mentat_tidy_workbook_20260914/mock/Credit Union Industry Spending Data (MOCK).xlsx`).
`build_tidy_workbook.py` is **tracked and clean** in git — verified (the
tidy-workbook lane's work is applied but uncommitted). An earlier statement in
this lane that the script "is not in the repo" is **withdrawn**.

**NOT FOUND in R, Python or PowerShell:** the sheet writer that emits the
row-1/row-2 titles and picks 12 versus 18 columns (Telecom is post-processed by
`split_telecom_workbook.py:264-289`). It lives in the Node artifact tool. **S2
locates it before touching layout.**

**Consequence.** For Banking, Telecom, Credit Arms and Property & Casualty,
per-contribution detail — including City/State/ZIP/Employer/Occupation — is
**not in the Overview workbook, by design.** It exists in the snapshot database
(100% coverage), reaches Chart Studio's detail sheets (`contribution_data.py`,
45,000-row cap) and the raw warehouse export, and is *meant* to reach the
companion Data workbook that has not been built. "Add the columns" is not the
fix. "Finish the designed vehicle, or choose another" is the question, and it is
Paul's (Q1). **S2 and the tidy-workbook lane are working the same problem and
must not diverge.**

### B — street: delivered, received, discarded

The evidence run's `api_page_checkpoints` tables hold 42 pages (lanes 02: 2,
03: 6, 04: 12, 09: 22), 100 records each. Every record carries **81 keys — the
complete openFEC schedule_a shape — including `contributor_street_1` and
`contributor_street_2`**, with real values (house numbers redacted here):
`'### GALLOWS RD'` Annandale VA 22003, `'### CALIBRE SPRINGS WAY NE'` Atlanta
30342, `'### BRADNER PL S'` Seattle 98144.

- `collect.R:1266-1270` maps five of those 81 keys and discards the rest.
  `schema.R:255-281` has no street column.
- Checkpoints persist only for units that did **not** complete (`fec_api.R:698`
  clears a decomposed unit's pages on completion under the `:695` guard; observed: every lane with stored rows holds 0 checkpoint rows). The 42 pages belong to 403-failed units; lane-08's
  3,132 stored rows have 0 checkpoints. **Street for every row already in
  `corporate_giving` is gone.**
- An earlier reading in this lane — "no raw payloads stored anywhere" — came from
  the `.tmp` verify databases (0 checkpoint rows) and is **overturned** by the
  production data.

**S2 scope for street, if Paul wants it:** `contributor_street_1`,
`contributor_street_2` in `schema.R` with a migration; two lines at
`collect.R:1266-1270`; the three export surfaces and the tidy `CONTRIBUTIONS`
registry; then a **re-collect** to populate existing rows. openFEC needs no
change.

### B — report-directory census (bearing on Q1)

`C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files` holds the eight
workbooks plus:

- **An Excel lock file for `Credit Union Industry Spending Overview.xlsx`** —
  165 B, 2026-09-14 17:21:51. **Credit Union is the workbook most recently open
  on Paul's desk**, and it is one of the four that HAS the five fields.
- **`bulk_rescue_overflow.csv`** — 192 B, **2026-09-15 15:40:34**, written
  during the evidence run. **DEFECT-RESCUE-CAP fired live**, and wrote into the
  OneDrive report directory rather than the run directory.
- Other lanes' artifacts: `accuracy_report.md`, `fixture_unmatched.csv`,
  `pipeline_only.csv` (09-12), `production-readiness.json` (07-29), two
  `Cross Reference Further Review … 2026-09-13.md` notes.

---

## AREA C — PAC Evidence

**The brief's symptom — "fails to fetch the files" — did not reproduce, and
the evidence says it cannot be a fetch failure.** Both fetch paths returned 200
with correct bodies on a writable scratch instance (port 8899, throwaway
`--data-root`), and Paul's three live consoles (8802, 8806, 8808 — all
`read_only: false`) serve the snapshot path correctly right now. What the tab
does is **fetch correctly, then forget**, and **block for seconds while
parsing**. Which of those Paul saw depends on wording S0 does not have.

### C — the two fetch paths, named

Selected by the `#evidence-source` dropdown (`evidence-csv.js:6-12`, persisted
in `localStorage` key `mentat-evidence-source`).

**Path 1 — Imported CSV. Ephemeral, in-process RAM.** Client `evidence-csv.js`:

- file-input handler `:51-65` → `POST /api/evidence-csv` `{name, text}` →
  `server.py:1900-1901` → `Console.import_evidence_csv` (`:1275-1289`) →
  `evidence_csv.parse` → `evidence_csv.catalog`
- `loadRows()` `:34-50` → `GET /api/evidence-csv?id&committee&cycle&offset&limit`
  → `server.py:1729-1731` → `Console.evidence_csv_view` (`:1291-1300`) →
  `evidence_csv.select`

The browser reads the user's file with `file.text()`; the server reads nothing
from its filesystem. The parsed document lives only in `Console.csv_imports`, a
plain dict created lazily at `server.py:1278-1280`, capped at 10 files / 20 MB
(`:1285`), **never persisted, absent from `Console.__init__` (`:501-522`)**.

**Path 2 — Saved snapshot. Disk-backed, shared across consoles.** Client `app.js`:

- `initEvidence()` `:478-497` → `GET /api/evidence` (catalog)
- `loadEvidence()` `:452-470` → `GET /api/evidence?id=<snapshot>` →
  `server.py:1732-1752`, which reads `PROJECT/.cache/pac-evidence/<id>/evidence.json`
- write side: `:534-545` → `POST /api/evidence-collect` (`server.py:1888-1889`
  → `collect_evidence` `:852-898`), polled by `pollEvidenceJob()` `:517-533` →
  `GET /api/evidence-job` (`:1753-1764`)

**What distinguishes them:** Path 1 is keyed by a `csv-<32hex>` id that exists
inside one server process only. Path 2 is keyed by directory name under
`PROJECT` (`server.py:29`, `= C:\Users\pgoff\Mentat\mentat`) and is **identical
for every console instance regardless of `--data-root`**. Path 1 errors land in
`#evidence-csv-status` (`evidence-csv.js:49`, `:64`); Path 2 errors in
`#evidence-empty` (`app.js:448-451`) or `#evidence-job-status`.

### C — verified anchors (live line numbers)

| File | Anchor | Live | Verbatim |
| --- | --- | --- | --- |
| `evidence_csv.py` | size cap | `:14` | `MAX_BYTES = 5_000_000` |
| | row cap | `:15` | `MAX_ROWS = 50_000` |
| | column cap | `:16` | `MAX_COLUMNS = 200` |
| | size raise | `:158-159` | `if len(encoded) > MAX_BYTES:` / `raise ValueError('Choose a CSV file smaller than 5 MB.')` |
| | column raise | `:169-170` | `raise ValueError('The CSV needs unique nonempty column names, with no more than 200 columns.')` |
| `evidence-csv.js` | client size gate | `:54` | `if (file.size > 5_000_000) { <status>.textContent = 'Choose a CSV no larger than 5 MB.'; return; }` (`<status>` = the `evidence-csv-status` element lookup) |
| `server.py` | body-length gate | `:1853` | `if length < 1 or length > 7_000_000` |
| | spawn | `:876-879` | `tools/pac_evidence.py` with `'--output', str(root)` |
| | not-finalized | `:885` | `'Collection did not finalize a snapshot. Saved responses are retained; see ' + str(root / 'collection.log')` |
| | could-not-start | `:888` | `'Could not start the evidence collector.'` |
| `pac_evidence.py` | timeout | `:126` | `with urlopen(request, timeout=60) as stream:` |
| | backoff | `:132` | `time.sleep(min(30, 2 ** attempt * 2))` inside `for attempt in range(4):` (`:119`) |
| | pool | `:307`, `:332` | `with ThreadPoolExecutor(max_workers=3) as executor:` |

### C — reproduction transcript (writable scratch instance, port 8899)

Launched `server.py --port 8899 --data-root <throwaway>` directly, bypassing the
launcher. `GET /api/health` → `"read_only": false`, `"busy": false`.
`Start-MentatApp.ps1` takes `-Port` (`:3`) and never passes `--read-only`
(`:192`), so every launcher-started console is writable.

| Request | Status | Time | Body |
| --- | --- | --- | --- |
| `GET /api/evidence-csv` | 200 | 0.021 s | `{"sources":[],"session_only":true}` |
| `GET /api/evidence-csv?id=csv-000…` | **400** | 0.062 s | `{"error":"This CSV import is unavailable in the current app session. Choose the file again."}` |
| `GET /api/evidence` | 200 | — | catalog with `fairshake-20260908` (Coinbase, cycles 2024/2026) |
| `GET /api/evidence?id=fairshake-20260908` | 200 | **0.013 s** | 364,252 B JSON; gzip → 23,694 B |
| `GET /api/evidence-job?id=fairshake-20260908` | **400** | 0.028 s | `{"error":"Invalid evidence collection."}` — fails the `snapshot-[a-f0-9]{32}` regex at `:1755` |
| `POST /api/evidence-csv`, 200 rows | 200 | 0.062 s | `{"id":"csv-1f51…","row_count":200,…}` |
| `POST /api/evidence-csv`, no token | **403** | 0.014 s | `{"error":"Refresh the app before continuing."}` |
| `POST /api/evidence-csv`, **4.95 MB** | 200 | **11.69 s** (nine runs: 3.72–15.52 s) | `row_count: 14334` |
| `POST /api/evidence-csv`, **19.9 MB** | **400** | 0.025 s | `{"error":"Request is empty or too large."}` (`:1853`) |
| `GET …?offset=abc` | **400** | 0.008 s | `{"error":"invalid literal for int() with base 10: 'abc'"}` |
| `POST /api/evidence-collect`, no token | 403 | — | `Refresh the app before continuing.` |
| `POST /api/evidence-collect`, `Origin: evil` | 403 | — | `Local access only.` |
| validation cases (empty company, bad committee id, odd cycle, >30 combos, >50 aliases) | 400 | — | each with its own exact message |

**A successful `/api/evidence-collect` was deliberately not triggered:** it runs
`root.mkdir(parents=True)` at `:869` against `PROJECT / '.cache/pac-evidence' / identifier`
(`:868`) — **inside the git working tree**. Stated limitation.

### C — FINDING 1: Path 1 forgets, and every live console has already forgotten

`csv_imports` is process memory. **All three of Paul's consoles report
`"sources":[]`** — whatever he imported is already gone from every one of them.
Once gone, *every* subsequent interaction with that CSV — committee change,
cycle change (`evidence-csv.js:66`), prev (`:67`), next (`:68`) — calls
`loadRows()`, receives the 400, and writes this into the status line, verbatim:

> **This CSV import is unavailable in the current app session. Choose the file again.**

Three routine events wipe it: the stale-build banner's same-port restart
(`server.py:1868-1883`), the launcher stopping an idle stale console
(`Start-MentatApp.ps1:155-176`), and the launcher landing the user on a
**different port** in its `$Port` through `$Port+9` scan (`:123`) — which is
exactly how 8806 and 8808 came to exist beside 8802, each with its own token and
its own empty `csv_imports`. **If Paul's symptom is a visible message, this is
the one.**

### C — FINDING 2: the import is a synchronous blocking parse, 3.7–15.5 s

`POST /api/evidence-csv` with 4.95 MB took **3.72–15.52 s across nine runs**.
The status line says `Reading <file>…` (`evidence-csv.js:55`) with no progress
and no cancel. Isolated:

- socket read + `json.loads` + immediate raise: 0.07–0.13 s
- `evidence_csv.parse` standalone, same interpreter: **0.64–0.81 s**
- the same parse inside the server, same moment: **3.72–4.69 s**

A GC/retention hypothesis was tested and **refuted** (flat timings with GC on
and off). What the evidence supports is working-set trimming under host memory
pressure: server `WorkingSet 105.3 MB` vs `PrivateMemory 347.6 MB`, 2.5 GB free
of 31.5 GB, another python process holding 7.3 GB, and **21,295 page faults on
the server process during one 11.1 s import**. The 5-6× in-server slowdown is
measured fact; the paging explanation is well-supported inference (the counter
does not separate hard from soft faults).

Either way: a multi-second synchronous parse on a request thread is exactly the
shape that produces the `ConnectionAbortedError: [WinError 10053]` tracebacks
already in Paul's `server-8806.stderr.log` (13,376 B) and `server-8808.stderr.log`
(2,658 B) — all at `server.py:1636` `self.wfile.write(content)`, on
`/api/contributions/query`, `/api/health`, `/api/runs`. The browser hangs up on a
slow response mid-write. **If Paul's symptom is a spinner or a blank tab, this
is the one.**

### C — the brief's premise about logs is wrong: there is no server log

`server.py:1612-1613`:

```python
    def log_message(self, *_):
        pass
```

`BaseHTTPRequestHandler` access logging is suppressed outright, and `server.py`
imports no `logging` module. `mentat/app/server.log` (35 B, gitignored) holds one
launch line. The launcher redirects stdout/stderr to `<DataRoot>\server-<port>.stdout/.stderr.log`
(`Start-MentatApp.ps1:196`, `:203-204`); stdout is one line per launch, stderr is
tracebacks only. **A "server log line for the failing request" cannot be
captured because none is written.** Paul's `server-8802.stderr.log` is 0 bytes.

### C — `collection.log`: NOT CREATED, and the one snapshot can never be polled

The only snapshot on disk, `mentat\.cache\pac-evidence\fairshake-20260908\`,
holds `evidence.json`, `snapshots.json`, `cash-estimates.json`,
`hydration-receipt.json`, `crypto_hydrated.db`, `source-cache\` (143 files,
5.93 MB) — and **no `collection.json`, no `collection.log`**. It was produced by
running `tools/pac_evidence.py` directly, not through the console. Its id fails
the `snapshot-[a-f0-9]{32}` regex at `server.py:1755`, so `/api/evidence-job` can
never report on it.

### C — measurements for S3's streaming design

Corpus: 20 columns matching a realistic Schedule A export, one committee-id
column (required by `evidence_csv.py:92-94`), 345 B/row. Limits raised only by
runtime attribute assignment in the harness; `evidence_csv.py` mtime unchanged.

| Case | Outcome | Wall | RSS Δ retained | tracemalloc peak |
| --- | --- | --- | --- | --- |
| 4.95 MB, real limits | parsed, 14,334 rows | **0.53 s** | **38.4 MB** | **58.5 MB** |
| 19.9 MB, real limits | `ValueError: Choose a CSV file smaller than 5 MB.` | 0.02 s | 8 KB | **19.0 MB** (a full extra copy before rejecting) |
| 19.9 MB, `MAX_BYTES` raised | `ValueError: Choose a CSV containing no more than 50,000 rows.` | **5.1 s** | 5 MB | **216 MB** — builds 50,000 dicts, then discards them, to print an error |
| 19.9 MB, both raised | parsed, 57,611 rows | **1.9–4.4 s** | **154 MB** | **235 MB** |

Three facts for S3:

1. **Retention ≈ 7.8× and peak ≈ 11.8× the CSV size, stable across both sizes.**
   The 20 MB session cap (`server.py:1285`) therefore implies **~155 MB of
   permanently retained heap per console** — `import_evidence_csv` stores the
   document and nothing ever evicts it. The memory *is* reclaimable once the
   reference is dropped (RSS 65.8 → 29.1 MB); the server never drops it.
2. **The 5 MB gate costs a full extra copy before it rejects** —
   `evidence_csv.py:157` does `encoded = text.encode('utf-8')` and `:158` checks
   afterwards.
3. **A 20 MB CSV breaks two gates, not one** — `MAX_ROWS = 50_000` (`:15`,
   enforced `:177`) fires *after* materialising every row.

Measurement script preserved at `receipts/S0_area_c_measure.py`.

### C — defects found in passing

- **DEFECT-5MB-UNREACHABLE.** `'Choose a CSV file smaller than 5 MB.'`
  (`evidence_csv.py:159`) **cannot be shown through the UI**: the client blocks
  `> 5,000,000` (`js:54`) and the server body gate blocks `> 7,000,000` (`:1853`),
  so the only band that could reach it is one the client already refuses. Two
  different strings exist for one limit (`'no larger than'` vs `'smaller than'`).
- **DEFECT-INT-LEAK.** `server.py:1731` calls `int(query.get('offset',['0'])[0])`
  unguarded; `do_GET`'s handler at `:1830-1831` sends `str(error)`, so the user's
  status line shows `invalid literal for int() with base 10: 'abc'`.
- **DEFECT-EVIDENCE-STORE-GLOBAL.** The evidence store is keyed on **`PROJECT`,
  not `--data-root`** (`:867-869`). Four consoles share one
  `mentat\.cache\pac-evidence\` in the git working tree (gitignored at
  `.gitignore:66`), with **no lock** — `collect_evidence` never takes
  `console_state_lock`. A throwaway data root does not isolate this tab.
- **DEFECT-SO-REUSEADDR.** `server.py:1944` builds
  `ThreadingHTTPServer(("127.0.0.1", options.port), Handler)` and never overrides
  `allow_reuse_address`, inheriting `HTTPServer.allow_reuse_address = 1` →
  `SO_REUSEADDR`. **On Windows, unlike POSIX, that permits a second socket to
  bind a port another socket is actively listening on, with undefined delivery
  between them.** A second console on 8802 could bind it and silently steal a
  share of Paul's traffic rather than failing cleanly. **NOT TESTED** — testing
  requires binding 8802. This is the mechanism that makes the port rule
  load-bearing.
- **DEFECT-KEYS-AT-STARTUP.** `server.py:520-522` calls `save_keys(configured)`
  whenever `FEC_API_KEY*` is set and the instance is writable, rewriting the
  shared `%LOCALAPPDATA%\Mentat\credentials\fec-keys.dpapi` (`fec_key_store.py:15-16`)
  at every launch, from any data root. Verified unchanged this session (1222 B,
  2026-09-10 22:23:18).
- Also relevant to Area A: `console_state_lock` (`server.py:258-287`) is a
  cross-console file lock on `<data-root>\collection-control.lock` with a 10 s
  deadline, held by `launch`, `stop`, `set_workers`, `archive_run` — **every
  console sharing the default data root contends for it, and Paul runs three.**

### C — the question S0 cannot answer

"Fails to fetch the files" is consistent with Finding 1 (a visible message after
a restart or port hop) **or** Finding 2 (a spinner that never finishes, followed
by a 10053 abort). **The literal status-line text Paul saw settles it in one
sentence.** Asked in section 10.

**Cleanup verified:** scratch server pid 59852 stopped; 8899 and 8898 free;
8802 (pid 41244), 8806 (12500), 8808 (1612) unchanged; no repo file written;
no `snapshot-*` directory created; tracked-modified still 58; the single new
untracked entry is this packet's own directory; `fec-keys.dpapi` and
`collection-control.lock` byte-identical.

**Note on the evidence run:** its `status.json` reports `effective_api_lanes: 3`
and `fanout_max_parallel: 3` alongside `sqlite_merge_cap: 10`. Ten lane
directories exist (one per company, `lane_count = min(len(keys), len(companies))`),
but **three ran concurrently**. Earlier references in this packet to "10 worker
lanes" mean ten lane directories, not ten concurrent processes.

---
## AREA D — Downstream and links

### D — the tabs, and what Downstream actually is

Six top-level tabs (`mentat/app/index.html:13-20`), in three groups:
**Workspace** (Loading `:13`, Collection `:14`), **Analysis** (Graph `:16`,
Chart Studio `:17`, Cross-reference `:18`), **Evidence** (PAC evidence `:20`).

**Downstream is not a tab.** It is one option of the graph-mode select inside
Graph (`index.html:105`):

```html
<label for="graph-mode">Candidate view<select id="graph-mode">
  <option value="direct">Direct contributions</option>
  <option value="activity">Downstream PAC activity</option>
  <option value="estimates">Conditional industry estimates</option>
</select></label>
```

with the caveat at `:107`:

```html
<p id="graph-candidate-separation" class="chart-note">Direct contributions only. Downstream PAC activity and conditional estimates are separate candidate views.</p>
```

Data comes from the `"Downstream Activity"` worksheet
(`mentat/app/graph_data.py:91`, read by `activity_xml_rows()` at `:83-136`),
produced by `mentat/R/fec_beneficiary.R`, with two failure texts:

- `:93` — `raise ValueError('This report has no saved downstream activity.')`
- `:257` — `raise ValueError('Downstream worksheet is a partial display; full activity rankings are unavailable.')`

**Confirmed:** no symbol named "PAC analysis" exists anywhere in `mentat/app/`.
Case-insensitive grep for `pac analysis`, `pac_analysis`, `pacAnalysis`:
**NO HITS.**

### D — linking is tab-name hash routing and nothing else

- `history.replaceState(null, '', '#' + currentView)` — `app.js:42`
- `window.addEventListener('hashchange', () => showView(location.hash.slice(1)))` — `:53`
- `showView(location.hash.slice(1))` at init — `:676`
- `currentView` is one of `['loading','collection','cross-reference','evidence','graph','chart-studio']` — `:23`

**The hash encodes the tab name only** — no entity, no company id, no cycle, no
filter. `history.pushState`: **NOT FOUND**. `permalink`, `entity_link`: **NOT
FOUND**. `URLSearchParams` appears in 7 files but every use builds an **API query
string**, not navigation — the sole exception being a pane selector,
`chart-studio.js:17`:

```js
const paneName = new URLSearchParams(location.search).get('studioPane');
const STORE = 'mentat-chart-studio-v1' + (/^[BCD]$/.test(paneName || '') ? '-pane-' + paneName : '');
```

That is a pane address, not an entity address. **There is no way to link to an
entity in this console.**

### D — click-path audit

From a named entity in Graph. Every destination is one click; the cost is not
clicks, it is **state destroyed**.

| Destination | Clicks | State lost |
| --- | --- | --- |
| (a) Downstream PAC activity | 1 (graph-mode select) | **none** — same view, data in memory |
| (b) PAC evidence | 1 (tab) | **industry, entity, cycle, tier, funding, company filters** — Evidence has independent controls (`evidence-source`, `evidence-snapshot`) and shares nothing |
| (c) Chart Studio | 1 (tab) | **all Graph selections**, unless the "Create chart" handler (`graph.js:2610-2616`) passes `pendingScope = graphScope()`; returning to Graph loses the scope again |
| (d) Cross-reference | 1 (tab) | **all Graph selections and loaded data** — separate source via `window.MentatCrossReference?.setActive()` (`app.js:33`) |

The destructive primitive is `graph.js:14`:

```js
function clear() {
  view=null;
  window.dispatchEvent(new CustomEvent('mentat:graph',{detail:null}));
  get('results').hidden=true;
  get('candidate-detail').hidden=true;
  get('freshness').replaceChildren();
  get('provenance').replaceChildren();
  error();
}
```

called from `loadCatalog()` (`:59`) and `refresh()` (`:74`). `showView()`
(`app.js:21-49`) does not itself clear Graph; the loss is **deferred**, which is
the trap — DOM control values persist while the loaded `view` object is nulled on
the next interaction, so the UI can show a selection whose data is already gone.

### D — reload survival

`sessionStorage` is **not used anywhere.** `localStorage` keys:

| Key | File:line | Holds |
| --- | --- | --- |
| `mentat-roster-draft-v1` | `app.js:78, 97` | Loading-tab sector and company list |
| `mentat-evidence-selection` | `app.js:440, 445` | Evidence preferences |
| `mentat-evidence-job` | `app.js:524, 542, 546` | in-progress evidence job id |
| `mentat-chart-studio-v1` / `-pane-[BCD]` | `chart-studio.js:18, 72, 86` | sheets, field layout, shelves, filters |
| `mentat-chart-comparison-v1` | `chart-comparison.js:29, 31` | comparison workspace |
| `mentat-evidence-source` | `evidence-csv.js:9, 11` | CSV-vs-snapshot mode |
| `mentat-chart-studio-show-identifiers` | `chart-studio.js:2476, 2620` | identifier-field checkbox |

| Tab | Industry | Entity | Cycle | View/filters | Data |
| --- | --- | --- | --- | --- | --- |
| Loading | survives | survives | n/a | — | draft reloads |
| Collection | lost | lost | lost | lost | re-syncs from server |
| Graph | lost | lost | lost | lost | must re-load |
| Chart Studio | partial (`?studioPane`) | lost | lost | **survives** (localStorage) | must refresh |
| Cross-reference | lost | lost | lost | lost | re-fetches |
| PAC evidence | lost | lost | lost | mode only | must reconfigure |

**Absent by construction:** entity deep links, permalinks, query-parameter state,
`pushState` history, shareable saved-view URLs, cross-tab state sync.

---

## AREA E — Cross-industry

### E — the console is ALREADY multi-industry; the constraint is in R

`mentat/app/server.py:1932-1945` parses `--port` (default 8802), `--data-root`
(default `%LOCALAPPDATA%\Mentat\console`), `--keys-file`, `--rscript`,
`--read-only`. **There is no `--industry` and no `--db`.** `Console.__init__`
(`:501-523`) takes no industry either.

Industries are discovered **per request**, by glob (`server.py:1505-1507`):

```python
    for fanout_manifest in directory.glob("industries/*/fanout/manifest.json"):
        fanout = read_json(fanout_manifest)
        fanout_dirs[fanout.get("industry")] = fanout_manifest.parent
```

No instance caching, no `lru_cache`; the lane is selected per call (`:1532`) and
all discovered lanes are returned (`:1529-1531`). **State lives in the run
directory, not in the Console object, so one process can serve many industries.**

| Route | Line | Industry binding |
| --- | --- | --- |
| `/api/contributions/session` | 1713 | none — metadata only |
| `/api/contributions/catalog` | 1715 | **all industries at once** — `contribution_data.py:182` globs `'* Industry Spending Overview.xlsx'` |
| `/api/contributions/geography/catalog` | 1726 | none — static (`contribution_geo.py:178-184`) |
| `/api/contributions/query` | 1862 | **explicit** in POST body: `name=request.get('dataset')` (`contribution_data.py:293`) |
| `/api/contributions/records` | 1864 | explicit, same |
| `/api/comparison`, `/api/comparison-flows` | 1784, 1786 | explicit query parameter |
| `/api/graph` | 1788 | explicit query parameter |

`X-Mentat-Token` (`:1846`) is a bare auth token, **not** a scoped credential — it
encodes no industry.

**Chart Studio reads WORKBOOKS, not snapshot databases.**
`/api/contributions/catalog` resolves against `app.report_directory`
(`C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files`). This is why the
snapshot row counts and workbook row counts disagree — **two different data
planes.** Any cross-industry work must state which plane it addresses. It also
means Area B's workbook gap is invisible to the collection layer entirely.

**The single-industry boundary is the R side.** `mentat/R/collect.R:1`,
`fec_api.R:1`, `report.R:1` each open with:

```r
if (!exists("MENTAT_INDUSTRY")) MENTAT_INDUSTRY <- "Crypto"
```

assigned per process in seven places (`collect_api_lane.R:60`,
`collect_employer_date_partition.R:56`, `collect_company_shard.R:84`,
`collect_company.R:43`, `sweep_collect.R:54`, `apply_versioning.R:32`,
`mentat.R:232`) and interpolated straight into SQL — `collect.R:3292`
(`"FROM companies WHERE industry = '", MENTAT_INDUSTRY, "'"`), `:3438`, and the
filter builder `report.R:10`. Further implicit reads at `collect.R:3343, 3364,
3400, 3415` and `fec_api.R:1387, 1512, 1538, 1568, 1595, 1875`.

**The console does not set `MENTAT_INDUSTRY` when it shells to R.**
`server.py:701-706` launches
`tools/parallel/Start-MentatResilientIndustryReports.ps1` with `-Cycles`,
`-RunRoot`, `-OutputDirectory`, `-RawDataDirectory`, `-PythonPath`,
`-RScriptPath`, `-NoCache` and `environment = os.environ.copy()` with **no
`MENTAT_INDUSTRY`** — the PowerShell script owns per-industry R subprocess
dispatch. (PowerShell reads `$env:MENTAT_INDUSTRY` at
`build_industry_report.ps1:597, 850, 868`.)

### E — live inventory

Eight industries have built workbooks (Area B table). **One** run existed under
the data root: `20260915T152258-18548`, holding exactly one industry,
`credit-unions`. The glob `industries/*/` *expects* several; today each run
carries one. Five console workspaces exist (four inactive, dated 09-09 and 09-10).

### E — what "comparison" already means

`CHART_COMPARISON.md`: 1 / 2 / 3 / 4 charts, four in a two-by-two grid; "Hide all
options" creates a comparison view; "Linked filters" link Company, Party,
Contributor state, Recipient committee state, or Candidate represented state;
**"Each chart uses its own axis scale."**

`CONTRIBUTION_STUDIO.md:5` — *"Choose an industry and accounting basis, place
dimensions and measures on the shelves, then choose a chart."* `:21` — *"The
receipt identifies the industry, workbook, cycles, company filter and source
fingerprints."*

**So comparison today means several charts side by side, each pinned to one
chosen industry, workbook and accounting basis. Nothing compares across
industries — but nothing in the Python layer forbids it either.** Each chart
already selects its own `dataset`, and the catalog already returns all eight
industries in one response. This bears directly on open question 3.

Gates: `STUDIO_GROUP_LIMIT = 60` (`chart-studio-core.js:191`); a 512 KB saved-view
gate (`server.py:1856`) raising *"That view is too large to save. Remove a sheet
and save again."*; a 7 MB upload limit on the contributions POST routes (`:1853`).

---

## 8. Defect index

Ordered by how much damage they do, not by how hard they are to fix.

| ID | Defect | Where | Owner |
| --- | --- | --- | --- |
| **DEFECT-403-OPAQUE** | 403 response body discarded; `status_label` built from the numeric status alone, so `OVER_RATE_LIMIT` / `API_KEY_INVALID` / `API_KEY_DISABLED` all collapse to `HTTP_403`. The cause of 11 of 30 lost tasks is undiagnosable. | `fec_api.R:521` | S1 |
| **DEFECT-403-FATAL** | 403 outside the retryable set, so a self-clearing condition kills a task on attempt 1 with all backoff machinery bypassed. | `fec_api.R:501-502`, raise `:534-542` | S1 |
| **DEFECT-LADDER-NODELAY** | Recovery ladder is 3 attempts with zero inter-pass delay; cannot outlast any time-based cause. | `api_company_cycle_fanout.py:1227-1231`, `:1512-1533`, `:1614-1634` | S1 |
| **DEFECT-RESCUE-CAP** | `MENTAT_RESCUE_CAP` default 50 truncates the rescue phase and reports the task `"succeeded"`. **Only mechanism that ships incomplete data as success.** FIRED in the evidence run: `bulk_rescue_overflow.csv`, 192 B, 2026-09-15 15:40:34, in the OneDrive report directory. | `fec_api.R:1612`, swallowed `:1728-1734` | S1, **Paul rules on intent** |
| **DEFECT-PAUSE-FLATTENED** | Task `"paused"` is collapsed to lane `"failed"` by a `!= "succeeded"` predicate; DE-020's failure mode one layer down. | `collect_api_lane.R:486-493`, fanout `:480` | S1 |
| **DEFECT-DEAD-403-HANDLER** | `record_validation_locked`'s `http_403` branch marks keys disabled, is tested, and has zero production callers; the disabled list is bypassed by `--keys-file`/`FEC_API_KEYS` anyway. | `fec_key_store.py:154-159`; fanout `:122-124` | S1 |
| **DEFECT-POOL-BLOCK** | Pool exhaustion spins with no timeout while R waits on `timeout = 0`; a lane hangs up to an hour rather than pausing. NOT ESTABLISHED in production. | `api_request_pool.py:91-99`; `fec_api.R:413-414` | S1 |
| **DEFECT-EXPORT-FALLBACK** | Export *timeout* never reaches the browser-API fallback because the guard matches only `"fec export server error"`. | `fec_page.R:1100-1106` vs `:1110-1118` | S1 |
| **DEFECT-EXPORT-CHUNK** | Documented 100-row checkpoint contract vs actual 20,000-row chunks with synthetic page numbers; mid-export crash restarts the variant_set from zero. | `fec_page.R:1179-1181` vs `:1026`, `:1043` | S1 |
| **DEFECT-RESUME-OPT-IN** | Checkpoints always written, consumed only when `--resume-after=` is passed, chrome-engine only. A normal re-run ignores them. | `collect.R:1652-1655`; `mentat.R:126-131`, `:146-148` | S1 |
| **DEFECT-FORMULA-FACTS-NO-DETAIL** | Banking, Telecom, Credit Arms and P&C workbooks carry aggregate Formula Facts cycle sheets with NO per-contribution rows, hence no City/State/ZIP/Employer/Occupation; 120 MB staging threshold, sticky on rebuild, documented intent; the designed companion Data workbook has never been built. | `build_industry_report.ps1:601`, `:614-625`; `prepare_workbook_payload.py:12-16`, `:41-46`; `report.R:1785-1787` | S2 + tidy lane, **Paul rules on delivery** |
| **DEFECT-STREET-DROPPED** | openFEC returns `contributor_street_1/2` on every page (81-key records in stored checkpoints prove it); the collector maps five fields and discards street; no schema column exists. Re-collect required for existing rows. | `collect.R:1266-1270`; `schema.R:255-281` | S2 |
| **DEFECT-EMPLOYER-ZERO** | lane-01 holds 228 rows with `contributor_employer`/`contributor_occupation` as `'` on every row while City/State/ZIP are 100% and peers are at 92-100%. Cause unknown. | evidence run lane-01 | S2 |
| **DEFECT-CSV-FORGETS** | Imported CSV lives only in process RAM; every restart or port hop erases it, and all three live consoles are already empty. User sees *"This CSV import is unavailable in the current app session. Choose the file again."* | `server.py:1278-1280`, `:1285`; `evidence-csv.js:49`, `:64` | S3 |
| **DEFECT-PARSE-BLOCKS** | `POST /api/evidence-csv` parses synchronously on the request thread: 4.95 MB takes 3.7–15.5 s in-server (0.6–0.8 s standalone); same shape as the `WinError 10053` aborts in Paul's stderr logs. | `server.py:1900-1901` → `:1275-1289`; `evidence_csv.parse` | S3 |
| **DEFECT-CSV-NEVER-EVICTED** | `csv_imports` has no eviction; the 20 MB cap implies ~155 MB permanently retained heap per console. | `server.py:1285` | S3 |
| **DEFECT-NO-REQUEST-LOG** | `log_message` is `pass`; no per-request log exists anywhere, so no request failure can be traced server-side. | `server.py:1612-1613` | S3 |
| **DEFECT-5MB-UNREACHABLE** | The 5 MB server message cannot be shown through the UI (client blocks >5 MB, body gate blocks >7 MB); two strings for one limit. | `evidence_csv.py:159`; `evidence-csv.js:54`; `server.py:1853` | S3 |
| **DEFECT-INT-LEAK** | Unguarded `int()` on `offset` sends raw Python exception text to the status line. | `server.py:1731`, `:1830-1831` | S3 |
| **DEFECT-SNAPSHOT-UNPOLLABLE** | The only snapshot on disk (`fairshake-20260908`) fails the `snapshot-[a-f0-9]{32}` regex, so `/api/evidence-job` can never report on it; it has no `collection.log`. | `server.py:1755` | S3 |
| **DEFECT-EVIDENCE-STORE-GLOBAL** | Evidence store keyed on `PROJECT`, not `--data-root`: all consoles share `mentat\.cache\pac-evidence\` in the git tree, with no lock. | `server.py:867-869` | **Paul rules** (cross-console) |
| **DEFECT-SO-REUSEADDR** | `ThreadingHTTPServer` inherits `allow_reuse_address = 1`; on Windows a second console can bind a listening port and silently share its traffic. NOT TESTED. | `server.py:1944` | **Paul rules** |
| **DEFECT-KEYS-AT-STARTUP** | Any writable instance with `FEC_API_KEY*` set rewrites the shared `fec-keys.dpapi` at launch, from any data root. | `server.py:520-522` | **Paul rules** |
| **DEFECT-KEYSTORE** | 1,975 identical unhandled tracebacks (3.59 MB) instead of one reported failure. | `fec_key_store.py:49` via `server.py:929` → `:624` | S3 |
| **DEFECT-EXIT-CODE** | PowerShell wrapper rewrites the fanout's documented exit 2 into `exit=1`, an undocumented value, in the run detail. | wrapper around `api_company_cycle_fanout.py:1799` | S1 |
| **DEFECT-TRUNCATED-UNREAD** | `fec_walk_variant_set_once` returns a `truncated` flag no caller anywhere reads. | `fec_page.R:1256` | S1 |
| **DEFECT-NO-DEEPLINK** | No entity addressing of any kind; hash carries only the tab name. | `app.js:42`, `:53`, `:676` | S5 |
| **DEFECT-STATE-LOSS** | Every tab hop from Graph destroys industry/entity/cycle/filters; loss is deferred, so the UI can show a selection whose data is gone. | `graph.js:14` via `:59`, `:74` | S5 |

### Confirmation steps S1 should run first (cheapest first, all read-only)

1. **Make the 403 body observable.** Nothing else in Area A can be decided
   without it. This is a logging change, not a policy change.
2. Re-run one failing company/cycle **manually, outside the collector**, against
   a known-good key, and capture the raw 403 body. Operator action.
3. Re-check `api_request_budget` after any new run; the 42-46 / 1000 figures
   above are the baseline.

---

## 9. Blueprint — S1 to S6

**PROVENANCE WARNING.** The lane brief instructs S0 to copy acceptance criteria
"from Paul's session prompts". **S0 was given only its own prompt.** The scopes
below are *derived* from the ECC-component assignments named in the S0 brief and
from the Area findings — they are **DERIVED, NOT COPIED**. When Paul supplies the
real S1-S6 prompts, replace these verbatim. Every session must check its own
prompt against this section and flag any divergence in HANDOFF.md before starting.

### Gates that apply to every session

- Present the design and **WAIT for Paul's go** before editing.
- Contract first: any new or changed API shape, URL scheme, or column order is
  written to `contracts/*.json` **before** code, imported by both suites,
  asserted against **producers**, with a **negative control that must fail**
  (DE-021, `contracts/README.md`).
- Patch + receipt: `git diff -- <files you own>` into `patches/S<n>_<slug>.patch`,
  test output beside it. **Paul commits.**
- Re-grep every line number; the tree is dirty and 465 commits behind `main`.
- `server.py` is CONTENDED (S3/S4/S5 plus the tidy-workbook lane's uncommitted
  edits). Diff hunk by hunk; never hand Paul a patch you have not separated.
- **Known-red baseline before this lane starts** — do not claim credit or blame
  for these: Node sweep **27/31 pass, 4 fail** —
  `test_console_browser.cjs:188`, `test_contribution_export_browser.cjs:102`,
  `test_cross_reference_view.cjs:75`, and
  `test_studio_briefing_tray_browser.cjs:121,155` (the last is a **date-boundary
  flake**: it expected `2026-09-16` and got `2026-09-15`, so it fails whenever a
  run straddles midnight — a genuine test bug). PowerShell sweep 5/5 pass. The
  Python and R sweeps were **not** run by S0 and have no baseline; the session
  that first runs one records it in HANDOFF.md.

### S1 — Collection resilience (Area A)

*ECC: `ecc:architect`, `ecc:code-architect`, `ecc:error-handling`,
`ecc:data-scraper-agent`, `ecc:architecture-decision-records`.*

Scope: `fec_api.R`, `collect.R`, `fec_page.R`, `api_company_cycle_fanout.py`,
`collect_api_lane.R`.

Acceptance criteria (DERIVED):

1. The 403 response body is captured and surfaced wherever `HTTP_403` is reported
   today, with the api.data.gov error code distinguishable in a log and in the
   task receipt. **This lands before any retry-policy change.**
2. A written ADR records what a 403 *means* for this system, backed by a real
   captured body — not an assumption.
3. Retry classification changes, if any, follow from that ADR and carry a
   contract for the terminal-state vocabulary.
4. A task that ends incomplete is distinguishable from one that crashed, at every
   level above the task receipt (addresses DEFECT-PAUSE-FLATTENED and DE-020).
5. `DEFECT-RESCUE-CAP` is resolved by Paul's ruling on intent, then implemented:
   either a documented budget that reports PARTIAL, or a raised cap.
6. Tests: a producer-asserted contract for the task/lane/run status vocabulary,
   with a negative control; plus a regression that a non-retryable status cannot
   silently report `"succeeded"`.

Out of scope: the reporting layer, which works (see A(b)).

### S2 — Address fields and schema (Area B)

*ECC: `ecc:database-migrations`, `ecc:contract-first`.*

Scope: `schema.R`, `export_raw_contribution_warehouse.py`,
`export_crypto_spending_data.R`, `prepare_workbook_payload.py`,
`build_industry_report.ps1`, `build_tidy_workbook.py` (**shared with the
tidy-workbook lane — coordinate before touching**), the Node sheet writer once
located, and **two lines of `collect.R:1266-1270`** — S1 owns `collect.R`; S2
coordinates that edit through HANDOFF.md rather than editing the file while S1
is in progress.

**Precondition: Paul answers Q1 (a), (b) and (c).** Each answer changes the
work; S2 does not guess.

Acceptance criteria (DERIVED):

1. **If street is wanted (Q1 b):** `contributor_street_1`, `contributor_street_2`
   added to `corporate_giving` with a migration; mapped at `collect.R:1266-1270`;
   carried by all three export surfaces and the tidy `CONTRIBUTIONS` registry; a
   contract fixes column order and is asserted against every producer with a
   negative control; a re-collect plan with cost stated in the receipt.
2. **`DEFECT-EMPLOYER-ZERO` explained** (lane-01: 228 rows, employer/occupation
   `''` on every row) before any employer-keyed join is trusted.
3. **For the Formula Facts industries (Q1 c):** implement Paul's chosen delivery
   vehicle. If it is the companion Data workbook, S2 works *with* the
   tidy-workbook lane's applied-but-uncommitted state, not around it, and the
   receipt-evidence gate that blocks real runs is Paul's ruleset to relax. Do not
   raise the 120 MB threshold without a measured Excel-limit justification. Make
   the sticky `priorFormulaFacts` behaviour explicit and documented, or drop
   it — Paul's call.
4. Locate the Node sheet writer before touching layout; it is **not** in R,
   Python or PowerShell.
5. `build_tidy_workbook.py` is tracked and clean. `prepare_workbook_payload.py`, `build_industry_report.ps1`, `finalize_crypto_excel.ps1`, `report.R`, `tidy_stage.R`, `schema.R`, `collect.R` and `fec_api.R` are all **modified-uncommitted by other lanes** in the working tree (verified 2026-09-16) — separate your hunks from theirs exactly as required for `server.py`.

### S3 — PAC evidence ingestion (Area C)

*ECC: `ecc:performance-optimizer`, `ecc:silent-failure-hunter`.*

Scope: `evidence_csv.py`, `evidence-csv.js`, `pac_evidence.py`,
`fec_key_store.py`, evidence routes in `server.py` (CONTENDED).

**Precondition: Paul states the literal status-line text or symptom he saw
(Q2).** Finding 1 and Finding 2 in Area C call for different work; S3 does not
guess between them.

Acceptance criteria (DERIVED):

1. **If Finding 1:** an imported CSV survives a same-port restart and a port
   hop — either persisted beside the snapshot store, or the UI states plainly
   that imports are session-only and makes re-import the primary action. *"This
   CSV import is unavailable…"* must no longer be the default outcome after a
   restart.
2. **If Finding 2:** `POST /api/evidence-csv` never blocks a request thread for
   an unbounded time — the parse streams (size checked *before* the second copy
   at `evidence_csv.py:157`; `MAX_ROWS` enforced incrementally, not after
   materialising every row) or moves off-thread with progress on
   `#evidence-csv-status`. Measured against S0's baseline: 4.95 MB in-server
   3.7–15.5 s; retention 7.8×, peak 11.8×.
3. Either way: `csv_imports` gains an eviction policy, and the ~155 MB
   retained-heap ceiling per console is bounded and documented.
4. `DEFECT-5MB-UNREACHABLE` resolved — one limit, one string, reachable — and
   `DEFECT-INT-LEAK` closed (no raw Python exception text reaches a status line).
5. `DEFECT-KEYSTORE`: one reported failure per condition, not 1,975 tracebacks.
6. Contracts `contracts/evidence-job-status.json` and
   `contracts/evidence-csv-import.json`, asserted against **every** producer
   (`server.py` import and select handlers, `pac_evidence.py`), negative control
   failing.
7. A real-client pass on a writable console at a scratch port — never 8802 —
   exercising every write path, **including one real `/api/evidence-collect`**.
   That call writes into `mentat\.cache\pac-evidence\` inside the working tree;
   the receipt must show the resulting `snapshot-<hex>` directory and its
   `collection.log` (DE-021).
8. Does **not** change `SO_REUSEADDR`, the evidence-store location, or the
   startup `save_keys` call without a separate ruling from Paul — all three are
   cross-console behaviour.
### S4 — Cross-industry addressing (Area E)

*ECC: `ecc:architect`, `ecc:code-architect`, `ecc:database-migrations`,
`ecc:contract-first`, `ecc:dashboard-builder`, `dataviz`.*

Scope: `contribution_data.py`, `chart-studio.js`, `chart-studio-core.js`,
`server.py` (CONTENDED).

Acceptance criteria (DERIVED):

1. Proceeds only after Paul answers open question 3.
2. States explicitly which **data plane** it addresses — workbooks or snapshot
   databases — since Chart Studio reads workbooks.
3. Any cross-industry shape carries a contract for the request/response,
   asserted against producers.
4. Respects the R-side boundary: `MENTAT_INDUSTRY` is a per-process global and
   collection stays one industry per process.
5. Does not weaken the 512 KB saved-view gate or `STUDIO_GROUP_LIMIT` without a
   measured justification.

### S5 — Navigation and linking (Area D)

*ECC: `ecc:click-path-audit`, `ecc:workspace-surface-audit`, `ecc:api-design`,
`/ecc:gan-build`.*

Scope: `index.html`, `app.js`, `graph.js`, `graph_data.py`, `fec_beneficiary.R`,
`server.py` (CONTENDED).

Acceptance criteria (DERIVED):

1. A URL scheme for addressing an entity is written to `contracts/*.json`
   **first** — this is precisely the class of change DE-021 governs.
2. State carried across a tab hop is specified before it is implemented; the
   deferred-loss behaviour at `graph.js:14` is addressed explicitly.
3. Reload survival is specified per tab against the table in Area D.
4. Does not rename or relocate the existing tabs without Paul's go.

### S6 — Surface (dashboard / dataviz)

*ECC: `ecc:dashboard-builder`, `dataviz`.*

**Scope not derivable from the S0 brief.** S6 must not claim a file held by an
in-progress session, and must confirm its scope with Paul before starting.

---

## 10. Three open questions for Paul

**Q1 — Which surface lacks the address fields?**
Answered, with a twist. **None of the three surfaces drops them.** Four of the
eight published workbooks — **Banking** (newest, 2026-09-10), **Telecom**,
**Credit Arms**, **Property & Casualty** — have no City/State/ZIP/Employer/
Occupation because their cycle sheets are the aggregate **Formula Facts** layout
with no per-contribution rows at all: selected when the staging payload is
≥ 120 MB (`build_industry_report.ps1:601`, `:614-625`), sticky on rebuild, and
**documented as intent** at `report.R:1785-1787`. The designed remedy — the
companion `<Industry> Industry Spending Data.xlsx` fed by `tidy_stage.R` and
`build_tidy_workbook.py` — exists in code and has never been built for a real
industry. The other four workbooks carry all five fields at header row 4, and
collection has them at 100%.

Three things only you can answer:

(a) **Which workbook were you looking at?** The Excel lock file on your desk
says **Credit Union** (2026-09-14 17:21) — which *has* the five fields. If that
is the one, the field you are missing is almost certainly **street**.

(b) **Do you want `contributor_street_1` / `_2`?** openFEC sends it on every
page and Mentat discards it. Adding it is two schema columns, two collector
lines, and a **re-collect** for existing rows. No API change.

(c) **For the four large industries: finish the designed companion Data
workbook (the tidy-workbook lane's territory), or deliver per-contribution
detail some other way** — a per-transaction sheet (the 120 MB fallback exists
for a reason), the raw warehouse export, or Chart Studio's detail sheets
(45,000-row cap)?

**Q2 — What does "sheets" mean — and what did you actually see?**
Chart Studio sheets, or CSV/workbook sheets? S0 assumed **Chart Studio sheets**
throughout, per the brief. **And, same tab: what was the literal text on screen
when it "failed to fetch"?** If it read *"This CSV import is unavailable in the
current app session. Choose the file again."*, the cause is Finding 1 — the
import is process memory, every restart or port hop erases it, and all three of
your consoles are empty right now. If it was *"Reading <file>…"* that never
finished, or a blank tab, the cause is Finding 2 — a 4–15 s blocking parse the
browser abandons. Different fixes; S3 does not start until you say which.
**Q3 — One console addressing many snapshots, or two consoles?**
Evidence says this is **less a build than a completion**. The Python console is
already multi-industry: no `--industry` flag, per-request glob discovery
(`server.py:1505-1507`), explicit `industry` / `dataset` parameters on every data
route, and `/api/contributions/catalog` already returns **all eight industries in
one response**. The single-industry constraint is the R side
(`MENTAT_INDUSTRY` as a per-process global), which governs **collection**, not
viewing. A second console would duplicate a capability that already exists.
**The real question is whether you want cross-industry *comparison* in one
view** — today comparison means 1-4 charts each pinned to one industry — and
**which data plane it should read**, since Chart Studio reads workbooks while
collection writes snapshot databases.




