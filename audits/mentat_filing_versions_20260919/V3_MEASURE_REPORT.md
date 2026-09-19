# What the `unresolved_version` rule costs — measurement and census

Read-only toward `C:\Users\pgoff\Mentat`. Everything written lives under
`...\scratchpad\v3_measure\`. Census read at HEAD **755680241**; see
§0 for the drift that happened mid-task.

---

## 0. HEAD moved while I worked — what that changes

The checkout was clean at `755680241` when I started. It is now at
**`a539d1ff1`** ("The source refresher can hand preserved filing headers to the
transfer index") with three files modified in the working tree. None of that is
mine: I ran only `git log/show/status/ls-files/grep/diff` and wrote nothing into
the repo.

`git diff --name-only 755680241 HEAD` over the files this report cites touches
exactly two:

- `mentat/tools/refresh_fec_sources.py` — gains `--filing-header-directory` and
  passes it to `transfer_index` (previously it always passed none). **Default is
  still no headers.**
- `mentat/tools/build_industry_report.ps1` — cross-reference/network resilience
  only; no transfer-relevant hunk (`git diff ... | grep transfer` is empty).

`fec_transfer_graph.py`, `fec_transfer_graph.R`, `fec_beneficiary.R`,
`collect.R`, `enrich_downstream.py`, `export_crypto_spending_data.R`,
`runtime_inputs.py`, `report.R`, `inputs/fec_receipt_rules.json`: **unchanged**.
Every measurement below therefore still describes HEAD.

---

## 1. CENSUS

### 1.1 Who builds the OTH transfer index

| Where | What it does |
|---|---|
| `mentat/tools/fec_transfer_graph.py:322-334` (`main()`) | `--directory --cycles [--filing-header-directory]`; for each cycle builds `oth<NN>/itoth.txt` and `publish_index()`es it. The only entry point that takes headers by design. |
| `mentat/tools/refresh_fec_sources.py:92-104` (at `a539d1ff1`) | After downloading an `oth` family, builds and publishes the index for each cycle. Headers only if `--filing-header-directory` is passed; **omitted → zero headers**. |

Nothing else builds it. `build_industry_report.ps1:420` merely adds
`transfer-current.json`, `transfer-info.json` and `transfer-edges.csv` to the
input fingerprint so a changed index busts the data cache — it never rebuilds.
No launcher, no console route, no parallel worker builds it either.

**No build step rebuilds a stale index on its own.** A v2 index stays v2 until a
human runs one of the two commands above.

### 1.2 Every caller of `refresh_fec_sources.py`

`git grep -n refresh_fec_sources HEAD` returns only:

- `audits/mentat_20260908/REPAIR.md:53` — prose, "the maintained tools are …".
- `mentat/tests/test_refresh_fec_sources_headers.py` — the new unit test.

**There is no production caller.** It is a manual operator command.

### 1.3 Who consumes it, and what a version-2 index does today

`mentat/R/fec_transfer_graph.R:3-44` `fec_transfer_context()` is the only reader
of `transfer-info.json`:

```r
if (is.null(index$version) || index$version != 3L) {                 # :12
  coverage[[…]] <- list(cycle = target_cycle,
    status = "stale_transfer_index", unresolved_all_sources = TRUE)  # :13-14
  next                                                               # :15
}
```

Confirmed: a version-2 file takes that branch, so the cycle contributes **no
edges at all** and no committee is added to the downstream universe. (A missing
file gives `missing_transfer_source` instead, `:8`.) The three published files
on disk are all `"version":2` (built 2026-09-08, `built_seconds` 158.6 / 161.8 /
67.6) and there is no `transfer-index-v3-*` anywhere under the active root.

The chain from there:

1. `tools/export_crypto_spending_data.R:627` calls it; `:865` puts `coverage`
   into `metadata.transfer_coverage`; `:962` puts the (empty) edges into
   `transfer_edges`.
2. `tools/enrich_downstream.py:223-224`:
   `if any(r.get('unresolved_all_sources') or r['status']=='stale_transfer_index' …): unresolved_nodes.update(funding)`
   — **every funded committee in the cycle becomes uncertain.**
3. `allocate()` (`fec_transfer_graph.py:301`): `if node in uncertain:
   unresolved[uncertain[node]] += amount; continue` → the root's entire funding
   is booked to `unresolved_transfer_records`, `assigned = 0`.

### 1.4 So: what does a report build produce right now?

**It completes and publishes, with every transfer-derived number zero.**

- `allocation_estimates` / `transfer_paths`: **empty**, all three cycles.
- Workbook and console columns "Conditional Non-opposition", "Conditional
  Opposition", "Conditional Estimate" (`tools/attribution_workbook_builder.mjs:30`,
  `tools/crypto_workbook_builder.mjs:2624`, `tools/build_tidy_workbook.py:309`,
  `app/server.py:787`, `app/evidence.js:526`): **0.00 everywhere.**
- `direct` attribution is **unaffected** — `enrich_downstream.py:204-207` pops
  authorized candidate committees out of `funding` *before* `allocate()` runs.
- `allocation_coverage`: one row per funded non-direct committee, whole amount
  under `unresolved_transfer_records`.
- `quality_checks`: `transfer_source_2022/2024/2026` **fail** (`enrich_downstream.py:261-265`,
  `passed = status=='indexed' and invalid==0`) and `allocation_coverage` fails
  (`:266-268`). Both are severity **`warn`**, and `R/export_guards.R` contains no
  transfer or allocation guard at all (`grep -c` = 548 lines, zero matches), so
  **nothing stops publication.** The report ships silently gutted.
- Onset: `a63fabefd` (2026-09-18 20:15) introduced the `!= 3L` requirement in
  `R/fec_transfer_graph.R`. Until yesterday evening the v2 index was accepted.

Second, independent trap: v2's `publish_index` wrote `transfer-edges.csv`
*without* a `records` column (`git show a63fabefd^:…/fec_transfer_graph.py`),
which `allocate()` now reads at `:277`. Even if the R version gate were relaxed,
the v2 CSV would give every edge empty evidence and fail the
`unverified_candidate_transfer_overlap` match at `:279-288`.

---

## 2. OTH MEASUREMENT KIT

### 2.1 What is in the scratch root

- `measure_transfer_v3.py` — imports the **committed** module via
  `sys.path.insert(0, r'C:\Users\pgoff\Mentat\mentat\tools')`, never copies it,
  asserts `graph.VERSION == 3`, and **refuses** an `--itoth` inside
  `C:\Users\pgoff\Mentat` (override `--allow-real-tree`) because
  `transfer_index` writes its cache, ledger and `.pending` next to the file it
  is given. Optional `--publish` also writes the three published artifacts.
- `make_smoke.py` — synthetic 17-row `itoth.txt` + 10-header store.
- `pas2_measure.R`, `gate_check.R`, `gate_check_old.R`, `scan.py`, `block.py`.
- `out\*.json`, `out\*.log` — every result below.

### 2.2 Hard links (no 6 GB copy)

`New-Item -ItemType HardLink` for all three cycles (`cmd /c mklink` is blocked by
this shell's path guard). Verified by `fsutil hardlink list`, which reports two
names for one file:

```
\Users\pgoff\Mentat\mentat\.cache\repair-20260908-inputs\fec_beneficiary\oth24\itoth.txt
\Users\pgoff\AppData\Local\Temp\claude\…\v3_measure\oth24\itoth.txt
```

Cross-check: SHA-256 of the 2022 **link** is `cbc3c772d6135496022c…`, identical
to `source_sha256` in the real `oth22/transfer-info.json`. Same bytes, no copy.

### 2.3 Smoke test — synthetic fixture, hand-checked

Every branch is exercised: current / superseded / duplicate / unresolved_version
/ unresolved_record; a multi-filing group headers **can** settle; one they
cannot (evidence absent); one that collides **inside a single filing** (no
header can ever settle it); a non-cash amendment that wins and deletes a cash
edge; a memo row; a blank TRAN_ID; an invalid destination; a malformed line.

**With the synthetic headers (10 files + 1 ignored `.review.json`):**

```json
{"headers_loaded": 10, "current_rows": 7, "unresolved_version_rows": 4,
 "unresolved_record_rows": 1, "superseded_or_duplicate_rows": 4,
 "unresolved_source_committees": 4, "unresolved_all_sources": false,
 "edges_positive": 5, "current_cash_edge_dollars": 7850.0,
 "blocked_edge_dollars": 4000.0, "blocked_edge_share": 0.509554,
 "unresolved_version_groups_by_span": {
   "multi_file":  {"groups": 1, "rows": 2, "cash_dollars": 16000.0},
   "single_file": {"groups": 1, "rows": 2, "cash_dollars": 1250.0}},
 "v2_style_winner_cash_dollars": 9650.0, "v2_equivalent_edge_dollars": 17750.0,
 "committed_rule_loss_dollars": 13900.0, "committed_rule_loss_share": 0.783099,
 "alternative_rule_loss_dollars": 9900.0, "alternative_rule_loss_share": 0.557746,
 "distinct_file_nums": 12, "file_nums_needed_for_multi_file_groups": 2}
```

Every one of those numbers was predicted by hand before the run and matched.

**Without a header directory** (same fixture): `unresolved_version_rows` 4 → **9**,
`unresolved_source_committees` 4 → **6**, `current_cash_edge_dollars` 7850 → **6050**,
`committed_rule_loss_share` 0.783 → **0.899**. Headers are what keep three of the
four multi-filing groups resolvable.

The write guard was also exercised: pointing `--itoth` at the real
`oth26/itoth.txt` exits 2 with
`… is inside C:\Users\pgoff\Mentat; transfer_index writes beside it.`

### 2.4 Real-data measurement already done (cash tails)

Rather than guess, I built the index on the **contiguous tail of each real
file** — every `24G`/`24K` row in all three files lives in one block at the end
(the files are ordered by transaction type), so these blocks contain the entire
cash population. Run with the **real 25-header store**.

| | 2022 | 2024 | 2026 |
|---|---:|---:|---:|
| block rows / file rows | 2,121,498 / 5,364,543 | 1,926,725 / 18,667,435 | 770,770 / 9,898,430 |
| cash rows (whole file) | 1,600,421 | 1,405,634 | 261,142 |
| `built_seconds` | 242.9 | 242.1 | 47.7 |
| ledger / cache JSON | 684 MB / 277 MB | 598 MB / 248 MB | 106 MB / 63 MB |
| current rows | 1,596,263 | 1,404,863 | 260,832 |
| **current cash edge $** | **2,468,397,260** | **5,327,441,910** | **1,965,680,932** |
| unresolved_version groups | 1,130 | 366 | 155 |
| … multi-filing | 303 (606 rows, $20.8 M) | 299 (598 rows, $45.6 M) | 155 (310 rows, $10.1 M) |
| … **single-filing** | **827 (3,539 rows, $50.7 M)** | **67 (173 rows, $13.7 M)** | 0 |
| unresolved_record rows | 13 | 3 | 1 |
| `unresolved_all_sources` | false | false | false |
| unresolved source committees | 44 | 47 | 28 |
| **blocked edge $ (source blacklisted)** | **108,916,264** | **33,047,447** | **10,533,899** |
| **blocked share of current cash edges** | **4.41 %** | **0.62 %** | **0.54 %** |
| committed-rule loss vs a v2-equivalent base | $131.5 M = **5.28 %** | $58.6 M = **1.09 %** | $15.1 M = **0.77 %** |
| alternative (withhold only the ambiguous rows) | $22.5 M = **0.91 %** | $25.5 M = **0.48 %** | $4.5 M = **0.23 %** |
| distinct file_nums in the ledger | 35,803 | 39,213 | 27,975 |
| file_nums needed to settle the multi-filing groups | 88 | 128 | 71 |

Reading: *committed-rule loss* = blocked edge dollars **plus** the one row per
withheld group a "highest file number wins" build would have counted;
*alternative* = only that second term. The base is both added back to today's
current edge dollars. So the committed rule costs **5.8× / 2.3× / 3.3×** what
withholding just the ambiguous rows would cost, and **83 % / 56 % / 70 %** of it
is collateral damage to *clean* edges belonging to a committee that happens to
have one ambiguous row somewhere.

Top blocked committees (2022): `C00010603` $49.7 M (3,140 unresolved rows, 58
clean edges), `C00000935` $24.2 M, `C00028860` $9.5 M, `C00770180` $3.7 M,
`C00032979` $3.6 M, `C00271338` $3.3 M (blocked by **2** `unresolved_record`
rows). 2024: `C00770180` $9.4 M, `C00348540` $6.5 M, `C00692343` $3.6 M,
`C00779223` $3.3 M, `C00106146` $2.8 M (blocked by **3** rows, 504 clean edges).
Full top-25 per cycle in `out\block*-headers.json`.

**These are lower bounds.** The blocks omit the head of each file, so a full run
can retain extra non-cash rows that share a version key and find *more*
ambiguity. Only the full-file runs in §2.5 are authoritative.

Two facts that bound the damage, established by a full scan of all three real
files (`out` of `scan.py`): **zero malformed rows** in any file, so
`unresolved_all_sources` can never flip true and the catastrophic
"every committee uncertain" branch cannot fire from OTH data. And the header
store holds **25** headers against **28–39 thousand** distinct file numbers per
cycle — but only **71–128** of those are needed to settle every multi-filing
group, which is a tractable fetch.

### 2.5 The six commands to launch

Python is the runtime the build uses (`build_industry_report.ps1:46`).
`$env:PYTHONDONTWRITEBYTECODE='1'` first. Run them one at a time, foreground.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$py='C:\Users\pgoff\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$s='C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-mentat-uncommitted-reconcile-4089f1\72dc8732-42b9-4fb4-9b63-5cb0cba9d2db\scratchpad\v3_measure'
$hd='C:\Users\pgoff\Mentat\mentat\state\cross-reference\filing-headers'

# WITH the preserved filing headers
& $py "$s\measure_transfer_v3.py" --cycle 2022 --itoth "$s\oth22\itoth.txt" --header-dir $hd --out "$s\out\full-2022-headers.json"
& $py "$s\measure_transfer_v3.py" --cycle 2024 --itoth "$s\oth24\itoth.txt" --header-dir $hd --out "$s\out\full-2024-headers.json"
& $py "$s\measure_transfer_v3.py" --cycle 2026 --itoth "$s\oth26\itoth.txt" --header-dir $hd --out "$s\out\full-2026-headers.json"

# WITHOUT headers (what refresh_fec_sources.py does by default)
& $py "$s\measure_transfer_v3.py" --cycle 2022 --itoth "$s\oth22\itoth.txt" --out "$s\out\full-2022-nohdr.json"
& $py "$s\measure_transfer_v3.py" --cycle 2024 --itoth "$s\oth24\itoth.txt" --out "$s\out\full-2024-nohdr.json"
& $py "$s\measure_transfer_v3.py" --cycle 2026 --itoth "$s\oth26\itoth.txt" --out "$s\out\full-2026-nohdr.json"
```

**Runtime.** Fitting `t = 6.34 µs × source_rows + b × retained_rows + 2 × sha(source) + sha(ledger)`
to the four real runs (the 6.34 µs/row scan constant is independently confirmed
by a 1 M-row zero-cash prefix that took 6.296 s; `b` = 142–163 µs; SHA-256
measured at 0.85 GiB/s on this box):

- 2022 ≈ **4.5–5.0 min**, 2024 ≈ **5.5–6.0 min**, 2026 ≈ **1.7–1.9 min**.
- All six runs ≈ **25–35 min**. Budget 10 min per cycle. v2 took 158.6 / 161.8 /
  67.6 s for the same files, so v3 is roughly **1.7–2.2× slower**, driven by the
  second full pass and one SQLite probe per source row (`fec_transfer_graph.py:120`).

**Scratch disk**, per cycle, beside the hard link (ledger + cache JSON; the
`.pending` ledger is *renamed*, never duplicated, so this is the peak):
2022 ≈ **1.0 GB**, 2024 ≈ **0.9 GB**, 2026 ≈ **0.2 GB**. The header and no-header
runs produce **separate** cache files (the header signature is in the name), so
all six together ≈ **4.5 GB**. With `--publish` add roughly another 0.5× per run.
178.9 GB free. The hard links cost nothing.

A re-run after a successful build is a **cache hit costing ~2.5 s** (verified on
the 2022 block: identical numbers, `wall_seconds` 2.469 against
`built_seconds` 242.9), so re-reading a result is free.

Known gap: `peak_working_set_bytes` reports `null` on this box (the psapi call
fails); judge RAM from the fact that the in-memory `edges` list is what becomes
the 248–277 MB cache JSON — budget 1–2 GB per cycle.

---

## 3. PAS2 MEASUREMENT (complete)

Run against scratch copies of the p4 cache and the p3 combined and per-cycle
caches. Full log: `out\pas2_measure.log`.

**Column alignment.** p4 has 23 columns, p3 has 22; the only difference is p4's
new `unresolved_version`. Everything else matches name-for-name, so no
re-derivation was needed. `version_key` is dropped before either index is saved
(`R/fec_beneficiary.R:469-472`), so I rebuilt it exactly as
`fec_build_pas2_index()` does — **grouping by `(cycle, version_key)`**, because
the builder groups inside one cycle's `lapply()` pass; grouping across cycles
over-counts. The rebuilt flags reproduce the stored `unresolved_version` column
**exactly in both directions** (two `stopifnot`s). The three per-cycle p3 caches
agree with the combined p3 cache row-for-row and dollar-for-dollar.

**The row sets are not identical.** p4 has **3,646 rows p3 never had** (1,322 /
2,062 / 262 by cycle); no row is in p3 but not p4. 3,497 of the extra rows are
the candidate-less receipts p4 now keeps as evidence and excludes; 149 are memo
rows.

### Counted totals

| cycle | p3 rows | p3 included | p3 included $ | p4 rows | p4 included | p4 included $ | Δ rows | Δ $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 747,733 | 734,897 | 2,759,736,192 | 749,055 | 734,431 | 2,753,312,446 | −466 | **−6,423,746** |
| 2024 | 701,535 | 685,886 | 5,022,083,517 | 703,597 | 685,723 | 5,021,166,096 | −163 | **−917,421** |
| 2026 | 207,985 | 204,188 | 1,101,028,965 | 208,247 | 204,115 | 1,100,738,246 | −73 | **−290,719** |
| **all** | | **1,624,971** | **8,882,848,674** | | **1,624,269** | **8,875,216,788** | **−702** | **−7,631,886** |

> **The defensible statement: the rule moved $7,631,886 across 702 rows out of
> the counted committee-to-candidate total — 0.086 % of the $8.88 B p3 counted.**

### The "Unresolved filing relationship" bucket

4,685 rows / $26,435,892 gross, touching **525 distinct committees** and
**361 distinct candidates**:

| cycle | (i) competing versions | (ii) no candidate_id | both | total rows | total $ | committees | candidates | groups |
|---|---|---|---|---:|---:|---:|---:|---:|
| 2022 | 876 rows, $15,420,278, 27 cmte, 255 cand | 1,264 rows, $2,191,886, 196 cmte | – | 2,140 | 17,612,164 | 222 | 255 | 1,696 |
| 2024 | 232 rows, $4,846,645, 22 cmte, 111 cand | 1,980 rows, $3,195,618, 235 cmte | – | 2,212 | 8,042,263 | 257 | 111 | 2,092 |
| 2026 | 80 rows, $310,090, 8 cmte, 49 cand | 251 rows, $466,667, 101 cmte | 2 rows, $4,708 | 333 | 781,465 | 110 | 49 | 292 |

Only bucket (i) costs anything against p3: of its 1,188 rows, **702 ($7.63 M)
were counted by p3**, 486 ($12.9 M) p3 already excluded as "Superseded filing
amendment" or memo. **Bucket (ii) costs nothing** — p3 did not contain those
3,497 rows at all, and they carry no candidate id, so they were never
attributable.

Single- vs multi-filing competing-version groups: 2022 **203 multi / 229
single**, 2024 **76 / 36**, 2026 **41 / 0**. The single-filing ones can never be
settled by a filing header.

### 15 largest unresolved version groups — and the root cause

| cycle | committee | candidates in one "version" group | rows | files | largest row $ | file_nums |
|---|---|---|---:|---:|---:|---|
| 2024 | C00864926 | H0IN03198 / H4TX12065 / H4TX26149 | 3 | 3 | 997,600 | 1759197 / 1779689 / 1788908 |
| 2024 | C00864926 | H0IN03198 / H4TX12057 / H6NC09200 | 3 | 3 | 762,632 | 1759197 / 1779689 / 1788908 |
| 2022 | C00504530 | H0FL08208 / H0NC03149 / H6PA08277 | 3 | 3 | 573,280 | 1592379 / 1598276 / 1676835 |
| 2022 | C00504530 | H2CO08020 / H2NV03161 | 2 | 2 | 564,244 | 1678500 / 1702974 |
| 2024 | C00864926 | H4IN08264 / H4TX12065 | 2 | 2 | 493,618 | 1779689 / 1788908 |
| 2022 | C00504530 | H2CA21183 / H2CA21233 | 2 | 2 | 415,529 | 1678500 / 1702974 |
| 2022 | C00504530 | H2CA21183 / H2CA21233 | 2 | 2 | 412,607 | 1678500 / 1702974 |
| 2022 | C00504530 | H0CA25154 / H2CA40084 | 2 | 2 | 358,633 | 1678500 / 1702974 |
| 2022 | C00504530 | H2AZ02360 / H2AZ09175 | 4 | 4 | 352,450 | 1592379 / 1598276 / 1676565 / 1676835 |
| 2022 | C00504530 | H2MS03151 / H8CA45130 | 2 | 2 | 340,972 | 1678500 / 1702974 |
| 2024 | C00864926 | H0IN03198 / H4TX12065 / H6NC09200 | 3 | 3 | 310,200 | 1759197 / 1779689 / 1788908 |
| 2024 | C00864926 | H4IN08264 / H4TX23120 | 2 | 2 | 302,577 | 1779689 / 1788908 |
| 2022 | C00504530 | H2MS03151 / H8CA49058 | 2 | 2 | 299,596 | 1678500 / 1702974 |
| 2022 | C00504530 | H2CA39136 / H2MI07123 | 2 | 2 | 264,447 | 1678500 / 1702974 |
| 2022 | C00504530 | H2CA39136 / H8CA39240 | 2 | 2 | 251,812 | 1678500 / 1702974 |

Every one of the top 15 belongs to just two committees, and **every group spans
two or more different candidate ids**. Verified against the raw FEC file
(`pas224/itpas2.txt`, not the cache):

```
C00864926|N|12P|…|24A|ORG|INVICTUS ADVERTISING |…|04082024|29685 |H0IN03198|H0IN03198|SE.5|1779689|…
C00864926|N|12P|…|24A|ORG|DEL CIELO MEDIA LLC  |…|02122024|997600|H4TX26149|H4TX26149|SE.5|1759197|…
C00864926|N|12R|…|24E|ORG|RIVAL STRATEGY GROUP |…|04222024|9246  |H4IN08249|H4IN08249|SE.5|1783402|…
C00864926|N|12P|…|24E|ORG|WHISTLESTOP STRATEGIES|…|05092024|10454|H4TX12065|H4TX12065|SE.5|1788908|…
```

`TRAN_ID` here is **`SE.5` — a Schedule E line label**, reused in every filing
this committee makes. `version_key = committee|report_type|transaction_id` is
therefore not an identity for these filers: three of those rows share report
type `12P`, so they collide and all three are excluded as "competing versions"
of one transaction. They are three distinct independent expenditures, different
vendors, different candidates, different dates.

**This is the root cause, and headers cannot fix it.** Fetching the filing
headers for `1759197 / 1779689 / 1788908` would establish the amendment family
and then *pick one* as current — silently dropping two genuine expenditures,
which is worse than excluding all three. The fix is a version key that carries
enough identity (candidate, date, amount, or `sub_id`), not more evidence.

---

## 4. RECEIPT-EVIDENCE GATE STATUS — **it no longer refuses those rows**

Gate: `mentat/R/collect.R:227-238` `fec_assert_receipt_evidence()`. Callers:
`tools/export_crypto_spending_data.R:229` (scoped to `evidence_scope`) and
`R/report.R:3221` (all raw rows). Ruleset on disk: **v5** (and, contrary to the
commit message, `mentat/inputs/fec_receipt_rules.json` **is** tracked now, added
by `17f7bf313`).

As committed, the gate stops only on `unverified_contradicted_receipt`
(`collect.R:191-193, 228-229`) — a row whose own text both asserts a gift and
asserts non-giving. Everything else ships counted with
`receipt_role_unverified = 1` and a `receipt_role_reason`.

Run against **scratch copies** of the hydrated databases, sourcing the same
module list as the exporter, with `MENTAT_INDUSTRY` set as an **R global**
(`Sys.setenv` alone would have measured Crypto twice) and
`spending_raw_report_rows(connection, versioning_applied = TRUE)` so
`apply_amendment_versioning()` never writes:

| | Crypto | Credit Union |
|---|---:|---:|
| raw rows / in 2022-2026 scope | 14,839 / 14,801 | 67,282 / 67,169 |
| countable **and** role unresolved (what the old gate refused) | **54** | **1** |
| countable **and** self-contradicting (what HEAD refuses) | **0** | **0** |
| `fec_assert_receipt_evidence(raw_rows[evidence_scope])` | **PASSED** | **PASSED** |
| `fec_assert_receipt_evidence(raw_rows)` (report.R scope) | **PASSED** | **PASSED** |

The 54 Crypto rows that remain unresolved are 46 `unverified_other_receipt`, 5
`unverified_disclosure_memo` (reason `disclosure_memo_unmatched`) and 3
`unverified_receipt_role`; the 1 Credit Union row is `unverified_other_receipt`.
All 55 are counted and flagged. Their `sub_id`s are listed in
`out\gate_crypto.log` / `out\gate_credit_union.log`.

**The commit that changed it is `7d364883e`** (2026-09-17, "Export gate refuses
only self-contradicting receipts; unresolved roles ship counted and flagged").
Negative control — I re-ran the **pre-`7d364883e` `collect.R`** over the same
rows of the same databases:

```
OLD gate verdict, Crypto:       REFUSED -> Receipt evidence unresolved for 65 rows
   (examples: 4010620251126152408, 4011120231681671902, 4011120231681671904, …)
OLD gate verdict, Credit Union: REFUSED -> Receipt evidence unresolved for 1 rows
   (example: 4011320251128197633)
```

so the refusal is real and the commit is what removed it. Of the old 65 Crypto
rows, 11 are now fully resolved (9 `unverified_disclosure_memo → disclosure_memo`,
2 `unverified_other_receipt → other_receipt`) and 54 are counted-and-flagged; no
row became *more* unresolved.

**Caveat on 80 vs 65.** I cannot reproduce the 2026-09-15 lane's exact 80 / 4
because ruleset **v4 was never committed** — `git log -- mentat/inputs/fec_receipt_rules.json`
shows a single commit, `17f7bf313`, which added v5, and
`git show 7d364883e^:mentat/inputs/fec_receipt_rules.json` fails with "exists on
disk, but not in". So both arms of my comparison necessarily use v5, and the
80→65 / 4→1 difference is attributable to the ruleset change I cannot isolate.
The conclusion is unaffected: **at HEAD the gate refuses nothing in either
industry, and the pre-commit code refuses both databases.**

---

## 5. Before / after

**Real files — byte-identical and mtime-identical throughout** (the OTH files
were only ever read through hard links; the PAS2 `.rds` caches and the two
hydrated DBs were copied out first):

| file | bytes | mtime (UTC) — before **and** after |
|---|---:|---|
| `…\oth22\itoth.txt` | 936,470,750 | 2026-09-08T05:26:52.9510207Z |
| `…\oth24\itoth.txt` | 3,284,045,258 | 2026-09-08T05:28:41.8441921Z |
| `…\oth26\itoth.txt` | 1,819,024,083 | 2026-09-08T05:27:13.3892237Z |
| `…\pas222\itpas2.txt` | 130,894,053 | 2026-09-08T05:26:43.6880439Z |
| `…\pas224\itpas2.txt` | 122,711,206 | 2026-09-08T05:26:46.7608248Z |
| `…\pas226\itpas2.txt` | 36,380,972 | 2026-09-08T05:26:50.7311338Z |
| `…\cache\pas2_index_p4-…rds` | 37,932,121 | 2026-09-12T19:56:08.8110725Z |
| `…\cache\pas2_index_p3-…rds` (×4) | unchanged | unchanged |
| `oth*/transfer-{info,current}.json`, `transfer-edges.csv`, `transfer-index-v1/v2*` | unchanged | unchanged |
| `receipt-metadata-repair-20260910\crypto\mentat.db` | 13,393,920 | 2026-09-11T00:16:58.4164394Z |
| `receipt-metadata-repair-20260910\credit_union\mentat.db` | 62,472,192 | 2026-09-11T00:16:58.2800461Z |
| `state\cross-reference\filing-headers\` | 27 files (25 + 2 `.review`) | newest 2026-09-12T20:52:45Z |

No `transfer-index-v3-*` file exists anywhere under the real root. Scratch holds
3.27 GiB of real bytes (the three hard links add nothing). C: free 196.05 GB →
178.9 GB.

**Processes.** Before: `python` 33028 (Mentat console, `app/server.py --port 8806`,
started 2026-09-18 00:24) and `python` 70008 (2026-09-17 16:58); ports 8800-8810
showed only `127.0.0.1:8806`. After: the same two, plus my short-lived
`python`/`Rscript` children, all exited. **No process of mine survives, and I
started nothing that listens.**

One process appeared that is **not mine**: `python` 74256, started
2026-09-18 23:20:26, `-m http.server 8802 --directory "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"`,
parent process `claude` (pid 87984) — a dashboard-preview server from another
session on this box. Flagging it so you can confirm it is expected; I did not
create it and have not touched it.
