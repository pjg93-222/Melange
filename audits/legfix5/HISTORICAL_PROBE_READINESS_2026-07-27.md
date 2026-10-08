# Historical-probe readiness note

Generated 2026-07-27 America/Chicago. **Inventory and planning only.** No network request was
issued, no probe was collected, and no existing artifact was modified. The only files written by
this pass are this note and its sibling NDJSON.

Companion machine-readable file:
`audits/legfix5/historical_probe_outstanding_identifiers_20260727.ndjson`
(598 rows, 623,714 bytes, sha256 `bc31884d4a6900802be83c1b7e37474367723633bcdad9c48c51cfd22fd9a844`)

---

## 1. Verified counts — the handoff's 15 / 598 is exact

`CLAUDE_CONTINUATION_HANDOFF_2026-07-27.md` line 91 states: *"15 historical probes covering 598
identifiers remain uncollected (`historical_probe_gate_complete: false`)."*

Both numbers verify against the registry itself.

| Quantity | Registry value | Independently recomputed | Agree |
|---|---|---|---|
| Probes (`categories`) | `category_count: 15` | 15 | yes |
| Identifiers (`historical_record_count`) | 598 | 598 query terms, 598 `expected_canonical_keys` | yes |
| Distinct identifiers | — | **598** (zero duplicates across all 15 probes) | yes |
| `coverage_probes` | `[]` | 0 | yes |
| `scoring_category_count` | 0 | 0 (`scoring_category: false` on all 15) | yes |

Registry: `source_data/legislation/acu_legislation_historical_probe_registry.json`
sha256 `045c991b3a081d7f840d860fab10bed0c761891915efb9fdcbd07c93fded4696`, 414,026 bytes,
mtime 2026-07-26 00:41.

Shape: 598 identifiers chunked at `chunk_size: 40` → fourteen probes of 40 plus one of 38.

Provenance of the 598 (from `source_kinds` on each term):

| Source | Identifiers |
|---|---|
| `historical_archive` only | 410 |
| `trusted_press_article` only | 130 |
| both | 58 |
| **total** | **598** |

188 terms carry at least one `trusted_article_references` entry.

Congress distribution: 117 → 171, 118 → 212, 119 → 215. **The 116th contributes zero.** The
registry declares this itself (`historical_source_missing_required_congresses: [116]`,
`historical_source_is_not_six_year_coverage_authority: true`) and states that six-year coverage is
established by the Advanced Search category and recall queries, not by this archive. That is a
declared gap, not a defect introduced here.

### One correction to make about the "15"

The literal `historical_probes_remaining: 15` that appears in
`fec/import_verified_membership_exclusions_to_junk_pile.py:221` is a **hardcoded constant**, sitting
next to a hardcoded `historical_probe_gate_complete: False` on line 220. Nothing computes it from
the registry or from disk. It happens to be correct today because the registry does contain 15
probes and none are collected — but that field is not evidence, and it will not move on its own when
the probes are collected. If the gate is closed, that constant must be changed by hand or replaced
with a real check.

---

## 2. They are genuinely uncollected — not collected-but-unrecorded

Re-checked with `Test-Path` / `Get-ChildItem -Recurse -Force` immediately before writing this note,
after the OneDrive resync completed.

| Path | State |
|---|---|
| `audits/legfix5/historical_probe_pages_20260725/` | **EXISTS, 0 files, 0 subdirectories, 0 bytes** |
| Any file named `*trusted_source_recall*` anywhere under `audits/legfix5/` | **none** |
| `audits/legfix5/congress_advanced_final_20260725/` (the merge output) | **absent** |
| `audits/legfix5/identifier_probe_pages_parallel_20260726/` | **absent** |

Every `queries/` directory that exists under `audits/legfix5` was enumerated; all four belong to
other runs (core-62: 62 files, identifier fast: 210, identifier pages: 55, interchange test: 1). No
`trusted_source_recall_0NN` query artifact exists anywhere.

`audits/legfix5/coverage_reconciliation/recon-20260727a/receipt.json` does **not** carry a
historical-probe check at all — its nine findings cover discovery/BillStatus/GovInfo only. So the
gate is not merely failing there; it is unmeasured there.

### OneDrive correction to the handoff's premises

The task brief said `fec/build_legislation_historical_probe_registry.py` was missing from disk.
**It is present**: 9,256 bytes, mtime 2026-07-25 19:34:59. So is
`fec/build_legislation_identifier_probe_registry.py` (3,518 bytes). Both are readable and were read
in full for this analysis. Whatever recovery effort was underway is either finished or unnecessary —
worth confirming before more time is spent on it.

---

## 3. What collection requires

### Instrument

**Congress.gov Advanced Search – Legislation**, the same surface as the core-62 discovery run. Not
GovInfo, not the API. Each probe is one Advanced Search query whose `enterTerms` is 40 (or 38)
`(congressId:N AND cite:"typeNNN")` clauses OR'd together.

The canonical invocation already exists, fully wired, in
`fec/run_legislation_coverage_pipeline.ps1` lines 170–182:

```powershell
node fec\collect_congress_advanced_pages.mjs `
  --registry source_data\legislation\acu_legislation_historical_probe_registry.json `
  --out      audits\legfix5\historical_probe_pages_20260725 `
  --profile  C:\tmp\congress-pages-interchange-profile-2 `
  --delay-ms 1500 --headless --resume
```

The collector reads `[...registry.categories, ...registry.coverage_probes]`, so the historical
registry's 15 categories + empty `coverage_probes` bind correctly with no code change.

### Request volume

| Line item | Count | Basis |
|---|---|---|
| Advanced Search result pages | **15** | Each probe's result total is bounded by its 40 cites; `pageSize=250` → exactly one page per probe |
| Document GETs, no retries | **15** | one `page.goto` per page |
| Worst case with `gotoWithRetry` exhausting all 3 attempts on every probe | **45** | `attempts = 3`, backoff `4000ms × attempt` |
| Sub-resource requests (CSS/JS/images per navigation) | ~30–60 × 15 ≈ **450–900** | `collect_congress_advanced_pages.mjs` uses full browser navigation (`page.goto`, `waitUntil: domcontentloaded`), not an API request context |

**Fifteen document requests is the honest floor and 45 the honest ceiling** for the sequential
collector. If sub-resource traffic matters (it does while a Cloudflare block is in play), the
`collect_congress_identifier_fast.mjs` transport issues exactly **1 HTTP request per page** via the
CDP BrowserContext `APIRequestContext` — sampled 47 of 60 page artifacts in the fast run, all with
`http_attempt_count: 1`. That path needs a shard plan from
`build_legislation_identifier_probe_shards.py plan --registry <historical registry>`; that builder
defaults `--expected-preserved 55` and carries identifier-run-specific preserved-run logic, so its
generalization to the historical registry is **unverified** and must be checked offline before use.

Estimated wall clock, sequential collector: median intra-query page-to-page interval measured on the
comparable sequential run (`identifier_probe_pages_20260725`) is 4.3 s (mean 5.3 s, p90 5.0 s). With
per-query setup and the 1,500 ms inter-query delay, **15 single-page probes ≈ 2–5 minutes**. This is
by far the cheapest outstanding collection lane in the project.

### Known risk: URL length is 41 % beyond anything proven

Each probe's `enterTerms` is ~1,476–1,594 raw characters; percent-encoded into the fixed Advanced
Search URL template this yields **3,710–3,876 character GET URLs**.

The longest URL any *completed* run has actually exercised is **2,738 characters**
(`examination_supervision`, core-62). No probe in this project has yet driven a ~3.9 KB Advanced
Search URL. That is under the common 8 KB server limit but well over the 2 KB one, and it is
untested against this specific surface. **Smoke-test exactly one probe before dispatching all 15.**

### Output contract

Written into `audits/legfix5/historical_probe_pages_20260725/`, matching
`acu-congress-advanced-pages-manifest-v1` as produced by the identifier and core-62 runs:

```
historical_probe_pages_20260725/
  manifest.json                       # status, registry_sha256, collection_contract,
                                      #   page_contract, transport_policy,
                                      #   selected_query_ids, queries[], union{}, visibility
  manifest.partial.<PID>.json         # in-flight checkpoints
  progress.json                       # live counters
  congress_advanced_records.ndjson    # union records, one JSON object per line
  congress_advanced_memberships.ndjson
  coverage_gap_ledger.ndjson
  exclusion_ledger.ndjson             # must stay 0 bytes
  scope_and_exclusion_contract.json
  queries/trusted_source_recall_0NN.json   # 15 files
  raw/pages/trusted_source_recall_0NN/page_001.json   # 15 files
```

- **Query artifact** (`congress-advanced-search-query-v1`): `query_id`, `label`,
  `scoring_category`, `record_kind`, `registry_sha256`, `query_sha256`, `advanced_search_query`,
  `result_transport`, `search_url`, `resolved_search_url`, `result_total`, `unique_record_count`,
  `page_count`, `counts_by_congress`, `counts_by_type`, `records_sha256`, `pages[]`, `validation{}`,
  `records[]`.
- **Page artifact** (`congress-advanced-search-page-v1`): adds `collected_at`, `requested_url`,
  `loaded_url`, `page_number`, `page_size`, `page_sort`, `result_range`, and
  `transport_provenance{}` (`selected_transport`, `http_attempt_count`, `response_body_sha256`,
  `cookie_values_read`, `cookie_values_persisted`, `fixed_retry_waits`).
- **`validation`** must be all-true: `exact_result_total`, `unique_result_total`,
  `every_page_exact`, `single_result_redirect_proven`.

### The merge is fail-closed with zero tolerance — read this before dispatching

`fec/merge_congress_advanced_coverage_runs.py` consumes the run. Its acceptance is exact, not
statistical:

- Per probe (lines 148–168): `{records[].canonical_key} != set(expected_canonical_keys)` →
  writes `historical_probe_failures.json` and **raises `RuntimeError`**. Not "flag and continue."
- Across the run (lines 169–172): the union of recovered keys must **equal** all 598 exactly, or
  `"Historical probe union does not equal the archive key universe"` → **`RuntimeError`**.
- There is no override flag, no tolerance parameter, and no partial-accept path.

Consequence: **one phantom citation blocks the entire gate.** If any of the 598 keys does not exist
on Congress.gov as cited — the obvious failure mode for citations parsed out of press-release prose —
the probe returns fewer than 40 rows and the merge refuses to produce
`congress_advanced_final_20260725`. Section 4 quantifies exactly which cohort carries that risk.

On success the merge:
- collapses all 15 probes into **one** membership `query_id` = `trusted_source_recall`
  (`record_kind: coverage_probe`, `scoring_category: false`), adding 598 membership edges;
- adds recall-only records as
  `candidate_status: "included_trusted_source_recall_unclassified_candidate"` with empty
  `matched_scoring_categories` / `matched_monitor_categories`;
- appends `gap_kind: "trusted_source_recall_only"` rows to the gap ledger for those records;
- writes `congress_advanced_final_20260725/` as `acu-congress-advanced-merged-manifest-v1`.

Merge prerequisites are already satisfied: the base run
`audits/legfix5/congress_advanced_pages_20260725/manifest.json` is `status: complete`, and its
`registry_sha256 ba865417…` matches the live `acu_legislation_search_registry.json` byte-for-byte.

---

## 4. Overlap — 503 of 598 are already in hand; only 95 are new records

Computed by streaming every collected record set and intersecting `canonical_key` against the
registry's 598.

| Source | Rows | Distinct keys | Of the 598, covers |
|---|---|---|---|
| `congress_advanced_pages_20260725` (the 62 discovery queries) | 18,557 | 18,557 | **503** |
| `identifier_probe_fast_20260726` (210 identifier probes) | 18,201 | 18,201 | 493 |
| `congress_advanced_records-PaulComputer.ndjson` | 18,557 | 18,557 | (identical key set) |
| **union of all collected discovery** | — | **18,557** | **503 (84.1 %)** |

The identifier-probe universe is a strict subset of the core-62 universe: 10 of the 598 are in
core-62 but not in the identifier run, and **0** are in the identifier run but not core-62. So the
62 discovery queries alone account for the entire 503.

**95 identifiers (15.9 %) appear in no collected record set.** Those are the only ones that would
enter the corpus as new candidates — expanding it from 18,557 to at most **18,652 (+0.51 %)**.

New-record breakdown by measure type: `hr` 62, `s` 17, `hjres` 6, `hres` 5, `sjres` 4, `hconres` 1.
By Congress: 119 → 46, 118 → 32, 117 → 17.

### The decisive split: recall rate by provenance

| Provenance | In registry | Already covered | Recall |
|---|---|---|---|
| `historical_archive` only | 410 | 388 | **94.6 %** |
| both sources | 58 | 57 | **98.3 %** |
| `trusted_press_article` only | 130 | 58 | **44.6 %** |

**Of the 95 uncovered, 73 carry a press-article source and only 22 are archive-only.** The 62
discovery queries already recall the historical archive almost completely; what they miss is
concentrated in citations extracted from press-release text.

Two readings:

1. Press releases legitimately cite bills outside the outline's topical scope — real records the
   discovery queries were never going to find. The probe recovers them; the gate closes.
2. Some of those press-derived citations are wrong (wrong Congress, wrong type, text damage). Those
   return zero rows and, under §3's exact contract, **hard-fail the merge**.

Evidence on disk favours reading 1, but does not eliminate reading 2:

- **The citation text is clean.** Sampling `matched_citation_text` across the uncovered
  press-sourced keys returns well-formed citations (`'H.R. 336'`, `'S.4072'`, `'H.J. Res. 109'`) from
  real member press releases on `*.house.gov` / `*.senate.gov`. No truncation or OCR damage is
  visible in the sample. The 97.7 % paywall truncation recorded for `press_text_cache` does not
  appear to have corrupted these particular extractions.
- **The residual risk is Congress attribution, not text.** `congress_for_article_date`
  (`cross_reference_legislation_press_articles.py:196`) derives the Congress purely from the article
  publication date. A release that cites a bill from a *previous* Congress ("the bill I introduced
  last Congress") yields a canonical key with the wrong Congress prefix, and the cite probe then
  returns zero rows. The code knows this — it emits
  `congress_basis: "article_date_points_to_different_congress"` — but the historical registry
  builder writes the derived key regardless.
- **Date-boundary exposure is small.** Of the 73 press-sourced uncovered keys, only **4** have a
  supporting article dated within 90 days of that Congress's start; the median article is 470 days
  in. So naive boundary error is a 4-key problem, not a 73-key one. Cross-Congress back-references
  are not bounded by that analysis and remain the open risk.

Net: the exposed cohort is 73, of which 4 are date-boundary-suspect. That is small enough to
pre-clear offline — see step 0 — and too large to discover at merge time.

### Per-probe detail

| probe_id | ids | already covered | new if recovered | congresses | archive-only new | press-sourced new |
|---|---|---|---|---|---|---|
| trusted_source_recall_001 | 40 | 36 | 4 | 117 | 2 | 2 |
| trusted_source_recall_002 | 40 | 38 | 2 | 117 | 1 | 1 |
| trusted_source_recall_003 | 40 | 34 | 6 | 117 | 5 | 1 |
| trusted_source_recall_004 | 40 | 36 | 4 | 117 | 2 | 2 |
| trusted_source_recall_005 | 40 | 35 | 5 | 117,118 | 3 | 2 |
| trusted_source_recall_006 | 40 | 35 | 5 | 118 | 2 | 3 |
| trusted_source_recall_007 | 40 | 29 | 11 | 118 | 0 | 11 |
| trusted_source_recall_008 | 40 | 33 | 7 | 118 | 0 | 7 |
| trusted_source_recall_009 | 40 | 36 | 4 | 118 | 2 | 2 |
| trusted_source_recall_010 | 40 | 32 | 8 | 118,119 | 1 | 7 |
| trusted_source_recall_011 | 40 | 35 | 5 | 119 | 0 | 5 |
| trusted_source_recall_012 | 40 | 27 | 13 | 119 | 0 | 13 |
| trusted_source_recall_013 | 40 | 32 | 8 | 119 | 0 | 8 |
| trusted_source_recall_014 | 40 | 32 | 8 | 119 | 2 | 6 |
| trusted_source_recall_015 | 38 | 33 | 5 | 119 | 2 | 3 |
| **TOTAL** | **598** | **503** | **95** | 117–119 | **22** | **73** |

Highest-risk probes for a merge hard-fail, in order: **012** (13 new, all press-sourced), **007**
(11 new, all press-sourced), **008** and **013** (7–8 new, all press-sourced).

### What this does *not* buy

All 15 probes are `scoring_category: false` / `record_kind: trusted_source_recall_probe`, and the
merge files their memberships under a single non-scoring `coverage_probe` query. Closing this gate
adds recall evidence and at most 95 unclassified candidates. **It does not produce a single
`category_evidence` row**, so it does not move `membership_is_finalizable` for anything. The
handoff's primary blocker — the never-performed 19-category adjudication — is untouched by this
work, and closing this gate makes 95 more candidates that will need adjudicating.

---

## 5. Recommended execution order

Everything below step 0 requires network. **Do not start any of it while the Cloudflare block or the
live congress.gov run is in play.** Steps 0–2 are offline and can be done now.

**0 — Offline. Pre-clear the 95 against the GovInfo BILLSTATUS sitemaps. Blocked today; see §6.**

The obvious candidates for an offline existence oracle do **not** work, and this was checked rather
than assumed:

- The GovInfo run plan (`runs/full-18440-20260727b/selected_jobs.ndjson`, 14,844 distinct keys)
  contains **0 of the 95** — and exactly **503 of the 598**, i.e. precisely the already-covered set.
- The BillStatus enrichment plan declares its input as
  `congress_advanced_pages_20260725/congress_advanced_records.ndjson` (18,557 records) with the
  acceptance rule *"contain no side-loaded key"*.

Both stores are candidate-scoped by construction, so neither can ever confirm a key that is not
already a candidate. That is the whole point of the historical probe.

What *does* work: the GovInfo **BILLSTATUS sitemaps**, already fetched and receipted on disk at
`billstatus_bulk_enrichment/fetch_runs/<run>/sitemaps/` — 32 receipts, all HTTP 200, covering
4 Congresses × 8 non-amendment types, **71,635 records total**, with the 119th segments
last-modified 2026-07-24 … 2026-07-26 (fresh). None of the 95 is an amendment, so the sitemaps cover
the full cohort. Intersecting the 95 against the URLs those sitemaps enumerate settles existence for
every one of them at **zero network cost**.

That check could not be completed today: the sitemap raw XML is currently unreadable (§6). Run it
the moment the store rehydrates — it is the single highest-value offline step in this lane.

**1 — Offline. Decide the phantom-citation policy before collecting, not after.**
The merge has no tolerance path. Either (a) confirm all 598 exist via step 0 and proceed, or (b)
agree in advance what happens to a citation that returns zero rows: quarantine it out of the
registry with a receipt and rebuild, or amend the merge to flag rather than raise. **(b) is a
contract change and is Paul's decision, not an implementation detail.** Do not discover this at
merge time with a half-collected run on disk.

Note that (a) via step 0 is cheap and probably sufficient — the exposed cohort is 73 keys and the
sitemaps settle every one of them — so (b) may never need to be exercised. But the decision must
exist *before* dispatch, because the merge's failure mode is a `RuntimeError` on a completed run.

**2 — Offline. Confirm the URL-length assumption is survivable.**
~3.9 KB GET URLs versus a 2,738-character proven maximum. Inspect `configureAndSearch` URL
assembly and confirm nothing truncates. If the fast/`APIRequestContext` transport is preferred for
its 1-request-per-page profile, verify `build_legislation_identifier_probe_shards.py plan
--registry <historical registry>` produces a valid plan — offline, `--plan` output only, no launch.

**3 — Network, one request. Smoke-test a single probe.**
Run `--categories trusted_source_recall_002` (only 2 new records, so the least informative to lose
and the most likely to reconcile cleanly). Verify: HTTP 200 not a challenge page, the ~3.9 KB URL is
accepted, `result_total == 40`, `validation` all-true, `records_sha256` present. **Stop here and
report.** One request tells you whether the remaining fourteen are viable.

**4 — Network, 14 requests. Collect the remainder, worst first.**
Order `012, 007, 008, 013, 010, 014, 003, 006, 011, 015, 005, 001, 004, 009` — highest new-record
count first, so a phantom-citation failure surfaces on request one rather than request fourteen.
Keep `--delay-ms 1500`, `--headless`, `--resume`. Total lane cost: **15 document requests, 2–5
minutes.**

**5 — Offline. Merge and reconcile.**
`merge_congress_advanced_coverage_runs.py --base-run congress_advanced_pages_20260725
--historical-run historical_probe_pages_20260725 --out congress_advanced_final_20260725`, then
`audit_quorum_recall_floor.py --primary-dir <final>`. Expect 18,557 → ≤18,652 records and
64,004 → ≤64,602 membership edges.

**6 — Offline. Replace the hardcoded gate.**
`import_verified_membership_exclusions_to_junk_pile.py:220–221` must stop asserting
`historical_probe_gate_complete: False` / `historical_probes_remaining: 15` as literals. Derive both
from the run manifest, and add a historical-probe finding to
`audit_legfix5_coverage_reconciliation.py`, which currently does not check this gate at all.

**7 — Do not proceed past the merge.** Steps 5–6 change the discovery universe that candidate
evidence, culling, and every downstream artifact were computed against. Re-running those is a
separate authorized action. No scoring, sync, promotion, or main-corpus write.

### Sequencing against the other blocker

This lane is cheap (15 requests, minutes) but it *enlarges* the 19-category adjudication queue by up
to 95 candidates. If the adjudication method is about to be decided, closing this gate first is the
right order — adjudicate 18,652 once rather than 18,557 now and 95 again later. If adjudication is
not imminent, this lane can wait; it blocks nothing that is currently moving.

---

## 6. Blocking availability finding — parts of the evidence store are OneDrive cloud-only

Found while attempting step 0. **This is a sync/availability state, not data loss.** Every file is
present with its correct size and hash-addressed name; the bytes are simply not materialized
locally, and hydration is currently refused.

| Store | Files | Cloud-only placeholders |
|---|---|---|
| `govinfo_bill_xml_versions/objects` (the 18,406-document official-text store) | 18,406 | **18,406 (100 %)** |
| `billstatus_bulk_enrichment/fetch_runs` (incl. the sitemap raw XML) | 44,628 | 14,887 (33.4 %) |
| `congress_advanced_pages_20260725/raw` | 414 | 49 (11.8 %) — all collector-failure PNGs |
| `identifier_probe_fast_20260726/raw` | 704 | 0 |
| `candidate_evidence` | 2,890 | 0 |
| `govinfo_bill_xml_versions/runs` | 73,982 | 17 |

Placeholders carry `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`. Opening one throws
`OSError: [Errno 22] Invalid argument` from Python and *"The cloud operation is invalid"* from
.NET — on every GovInfo object and every BillStatus raw XML tried. Notably, the cloud-only PNGs
under `congress_advanced_pages_20260725/raw` **do** hydrate on demand, so this is not a general
OneDrive outage. OneDrive is running (PID 20096, started 04:20, ~4,500 s CPU — consistent with a
large in-flight sync of exactly the material written today). C: has 728 GB free, so it is not a
space problem.

Read this the way the 2026-07-27 restore incident should have been read: **an in-progress sync is
not loss.** No conclusion about missing or corrupt GovInfo evidence should be drawn from it. But two
practical consequences hold right now:

1. Step 0 cannot run until the BillStatus sitemap XMLs rehydrate.
2. Any pipeline stage that reads the GovInfo object store — re-verification, rehashing, text
   extraction — will fail today with a misleading I/O error, not a data error. Check
   `(Get-Item $p).Attributes -band 0x400000` before believing any such failure.

Re-test with a single read before concluding anything:

```powershell
$p = 'audits\legfix5\billstatus_bulk_enrichment\fetch_runs\<run>\sitemaps'
Get-ChildItem $p -File | Select-Object -First 1 | ForEach-Object {
    (Get-Content -LiteralPath (Get-Content $_.FullName -Raw | ConvertFrom-Json).raw_path -TotalCount 1)
}
```

---

## Appendix — NDJSON schema

`historical_probe_outstanding_identifiers_20260727.ndjson`, one object per line, 598 lines,
schema `acu-legfix5-historical-probe-outstanding-identifier-v1`:

| field | meaning |
|---|---|
| `registry_sha256` | binds the row to `045c991b…` |
| `probe_id`, `probe_label`, `probe_record_kind`, `probe_scoring_category` | the owning probe |
| `term_index_within_probe` | 1-based position in that probe's `query_terms` |
| `canonical_key`, `congress`, `measure_type`, `number`, `cite` | the identifier |
| `advanced_search_term` | the exact `(congressId:N AND cite:"…")` clause |
| `source_kinds`, `trusted_article_reference_count` | provenance — drives the §4 risk split |
| `already_in_collected_discovery`, `covered_by_runs` | overlap result |
| `new_record_if_recovered` | true for the 95 |
| `probe_collected`, `probe_output_dir_expected`, `probe_output_dir_present_but_empty` | gate state as verified 2026-07-27 |

Filter the 95: `.new_record_if_recovered == true`.
Filter the merge-risk cohort: `.new_record_if_recovered == true and (.source_kinds | index("trusted_press_article"))` → 73 rows.
