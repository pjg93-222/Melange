# Standardized OpenSecrets collector (`osc`)

Cache-first, resumable, rate-limit-aware collector and offline extractor for public OpenSecrets pages. Configured period: election cycles
2008-2026 and lobbying years 2008-2026 (2026 partial), nominal USD. Ordinary HTTP only: `curl.exe` (default when installed) or `requests`,
truthful `MentatResearchCollector/1.0` User-Agent. No cookies, credentials, browser automation, TLS impersonation, proxies, CAPTCHA/challenge
solving or access bypass. A Cloudflare managed challenge (HTTP 429 + `Cf-Mitigated: challenge`, or HTTP 200 "Just a moment") is treated as
an access gap, never solved.

## Install and run (Windows PowerShell, Python 3.12 tested)
```powershell
cd C:\Users\pgoff\Mentat\outputs\opensecrets-2008-2026-20261001\standardized      # the folder that contains osc\, scopes.json, tests\
python -m pip install -r requirements.txt            # beautifulsoup4, requests, pytest (versions constrained in requirements.txt)
python -m osc collect --tiers all                    # network; every tier; bounded; resumable (re-run the same command to resume)
python -m osc build                                  # offline: cache -> csv\*.csv + cross-checks + census + gaps + manifest
python -m osc receipt                                # runs the tests, writes RECEIPT.md + csv\receipt.json from the run artifacts
python -m osc status                                 # read-only: persisted status + process query (never signals a process)
```
Other commands: `discover` (seed pages + derived-stage plan sizes), `extract` (tables only), `validate` (checks only), `run` (= collect + build).
`python -m osc build --extract-only national --out-dir <dir>` extracts/validates only the national tables into a separate directory.
Only one `discover`/`collect`/`run` process may own a cache directory: an OS-level lock (`<data-dir>\collector.lock`, released automatically if the
process dies) makes a second launch exit with code 2. `extract`/`validate`/`build`/`status`/`receipt` are read-only and may run during a collection.

## Paths, defaults and overrides
Defaults are absolute paths **on the workstation this was built on** (`osc/config.py`); every one is overridable on the command line, so nothing else
is machine-bound:

| flag | default (2026-10-01, this workstation) | what |
|---|---|---|
| `--scopes` | `<folder>\scopes.json` | scope registry and requested periods |
| `--data-dir` | `C:\melange-data\forecast-redesign-20261001-review\standardized-collector\data` | raw-byte cache, `request_log.jsonl`, `retry_state.json`, owner lock |
| `--state-dir` | `C:\melange-data\forecast-redesign-20261001-review\standardized-collector\state` | `work_queue.json`, `status.json`, `pid.json` |
| `--out-dir` | `<folder>\csv` | CSV tables, `crosschecks.csv`, `validation.json`, ... |
| `--roster-csv` | `C:\melange-data\forecast-redesign-20261001-review\roster-discovery\mentat_roster_organizations.csv` | read-only Mentat roster (80 current top-10 company names, 8 canonical workbooks) for exact-name org search; `""` disables |
| `--offline-lobby-dir` | `C:\melange-data\forecast-redesign-20261001-review\source-recovery\lobbying` | unchanged native annual-lobbying exports + `RECOVERY_NOTES.txt` (supplemental; `""` disables) |

`osc/validate.py` additionally compares against optional historical evidence at this-machine paths (`NATIONAL_CANDIDATE_BROWSER_SOURCES.json`, the
old collector's CSVs, the native lobbying exports). Those comparisons are skipped when the files are absent; they are cross-checks, not inputs.
On another machine: copy `osc\`, `scopes.json`, `requirements.txt`, point `--data-dir/--state-dir/--out-dir` at local folders and pass `--roster-csv ""
--offline-lobby-dir ""` if you do not have those inputs.

Other options: `--concurrency 4` `--min-interval 0.35` (global seconds between transport calls) `--transport auto|curl|requests` `--refresh` `--retry-failed`
`--tiers all|seeds,pac_recipients,lobby_splits,orgs` (default **all**) `--only stage,stage` `--max-requests N` `--split-cap N` `--org-cap N`
`--max-retry-after 300` `--family-429-limit 3` `--family-cooldown 300` `--max-defer-wait 0` `--max-passes 500` `--deadline-utc <ISO>` `--extract-only <builders>`.

## Periods (honoured, validated)
`scopes.json` `cycles` (`first`, `last`, `step`=2, even years only) and `lobbying_years` are applied at load (`config.apply_periods`); invalid values raise.
Which cycles are *requested per source* is derived from the source's own cycle menu on a captured probe page (overview, PAC, legacy industry, legacy
lobbying), not from a hard-coded publication ceiling: a cycle the menu does not list is a reason-coded gap (`cycle_not_in_source_menu`), a cycle it
lists is requested (so a refreshed run picks up 2026 as soon as the site publishes it). If no menu evidence exists every configured cycle is attempted
and the served-cycle guards reject fallbacks (a 2026 request served as 2024 is never relabelled).

## Tiers
| tier | stages (run order) | what |
|---|---|---|
| seeds | seeds_national, seeds_pac, seeds_legacy, seeds_lobby | national overview, cost of election, PAC industry-breakdown / industry-detail (scope x cycle), legacy totals / top contributors / combined candidate lists, modern lobbying (annual chart + per-year client table), legacy lobbying for T2100 |
| orgs | org_search, org_totals | exact-name org search for every top-contributor name and every roster company, then one full-history totals page per exactly matched org |
| pac_recipients | pac_recipients | one candidate-recipients page per **unique (PAC id, cycle)** on any scope roster (dedup by ID across scopes; HSBC's two IDs stay two PACs) |
| lobby_splits | lobby_splits | per-client in-house vs outside page per lobbying client and year (largest tier) |

## Rate limits, deferral and resume (see `osc/fetch.py`)
* One global transport bound (concurrency, `--min-interval`) across all adapters. Accounting is per **transport call** (one curl/requests invocation);
  redirect HTTP hops are counted separately (`redirect_hops`; `http_requests_total` = calls + hops); URL fetches and retries are separate counters.
* Explicit `Retry-After` (seconds or HTTP-date) is honoured **globally**, also on a final 429, by workers already waiting, and **after a restart**
  (`retry_state.json` + `resume_after_utc` in the cache metadata). Waits up to `--max-retry-after` are sat out; longer ones defer (never an early retry).
* 429 **without** Retry-After: per-family exponential pause, that family's pace is cut (AIMD with a 2.5 s floor), and after `--family-429-limit`
  consecutive 429s the family is deferred for `--family-cooldown` seconds while other families keep running. A family deadline also stops workers that
  were already inside their retry loop.
* Deferred URLs are state `deferred` in `work_queue.json` with `resume_after_utc`; they are never recorded as observed, as zero or as permanently
  unavailable. `collect` prints `resume with: <command>`. `--max-defer-wait N` lets the same process wait out deferrals shorter than N seconds and
  re-run the stages (cached URLs cost nothing); `--deadline-utc` is a soft scheduling cutoff in this version: workers already admitted to a pacing wait can still issue a request after that time, and queued stage passes can continue. It does not guarantee exact process termination; inspect status and process identity.
* 403 circuit breaker per family; `--max-requests` hard budget; HTTP-200 challenge pages are rejected on live fetch and on cache reads (bytes kept).

## Output tables (`csv/`)
Every row has `source_url, final_url, http_status, retrieved_utc` (UTC capture time), `source_sha256, cache_key, source_generation, source_vintage,
source_release_date` (platform/FEC release, separate from capture), `source_cutoff_date, source_cutoff_basis`, `extraction_status` (parsing outcome),
`completeness_status`, `reason_code`, `notes`, plus `requested_*` / `served_*` period columns. Missing = blank, never zero; signed nets preserved.
Tables derived from several sources carry every operand: `pac_membership_crosswalk` (`source_urls` paired with `source_retrieved_utc`, `source_sha256s`,
`source_capture_pairs`) and `org_contribution_sources` (industry-page URL/capture/hash separately from profile and search provenance).

* National: `national_candidate_by_office`, `national_candidate_giving` (controls DERIVED from the page: selected or first-enabled `select_type`/`display_type` option
  plus the per-office "Financial activity for all ..." caption; wrong universe/display is rejected; `offices_included` is explicit - Presidential only in presidential years,
  a midterm without a Presidential table is absent, not zero; requested cycles with no usable page, e.g. 2026, get reason-coded unavailable rows), `national_election_cost`.
* PAC: `pac_industry_breakdown`, `pac_industry_candidate_totals`, `pac_roster`, `pac_membership_crosswalk`, `pac_pages`, `pac_chamber_party`, `pac_recipients`,
  `pac_candidate_giving_industry`. An industry x chamber x party cell is `amount_status=exact` (`amount_usd` filled, `complete`) only if unique PAC IDs equal the headline count
  with no duplicate roster IDs, every PAC page is retrieved, every needed amount is source-observed (an absent chamber table counts as zero only if that PAC's own headline
  reconciliation proves it; `None` is never zero), every PAC page reconciles to its own headline (D/R including Presidential; all-party total for `Other`), roster D/R equal the
  PAC page headline, the roster reconciles to the industry headline, and House+Senate+Presidential equal the industry headline. Otherwise `amount_usd` is blank,
  `partial_sum_usd` carries the labelled numeric partial and `reason_code` lists the failing predicates. Industry headlines are all-federal-candidate totals (Presidential included).
* Individuals: `individual_candidate_giving_industry` (blank + reason: no aggregate source by chamber x party); `legacy_candidate_combined(_by_chamber_party)` (PAC+individual combined; served
  chamber and mem=N universe verified from the page, mismatches rejected).
* Industry: `industry_totals`, `top_contributors`. Organisations: `org_contribution_sources`, `org_totals_history`, `org_roster_crosswalk` (exact-name matches only; ambiguous / none / candidates
  preserved; a profile may include broader affiliates and is never an ownership or parent proof; the 80-company roster is the current Mentat top-10 snapshot, not a historical census).
* Lobbying: `lobbying_annual`, `lobbying_clients`, `lobbying_client_splits`, `lobbying_annual_offline_export`. `in_house_usd`/`outside_firm_usd` are `complete_exact` only if the parent roster
  is complete (unique IDs, parsed count == source count, client spends sum to the industry total == annual chart), every client split page is cached, served the requested year, has both
  components explicitly numeric and reconciles to the client total and industry amount; otherwise they stay blank with labelled partial sums and `in_house_outside_reason`.
  Modern M02 Automotive (as-of 2026-07-23, 2026 = Jan 1-Jun 30) and the exact legacy T2100 Auto Manufacturers series (cutoff unknown) are separate scopes. The native annual exports are
  used only where the HTTP annual chart is unavailable (`source_generation=offline_native_export`, file sha256, capture DATE only - the time of day was not recorded); `Lobbyists` is a headcount, never clients.
* Run products: `coverage_census`, `gaps`, `gap_summary`, `crosschecks`, `request_manifest`, `scope_registry_resolved`, `validation.json`, `source_taxonomy.json`.

## Scope registry (`scopes.json`)
Scopes stay separate: F03 commercial banks, F05 credit unions, F09 insurance (broad; never P&C-only), T2100 auto manufacturers (category), M02 Automotive (broader comparison, never relabelled T2100),
B08/B09/F06 comparison scopes, and requested-but-unmapped community banks, crypto, fintech, telecom roster, life insurance: *no verified exact aggregate mapping was found in the inspected sources*
(stable reason code `no_published_industry_code`; absence in inspected sources is not proof that none exists; historical codes such as F3300/F3400 are unverified leads, not mappings).

## Reason codes (selection)
`cycle_not_in_source_menu`, `served_cycle_mismatch`, `served_universe_mismatch`, `wrong_candidate_universe_or_display`, `http_403/404/429`, `http200_challenge_content`, `http429_cloudflare_challenge`,
`deferred_family_429_cooldown`, `deferred_retry_after_exceeds_limit`, `deferred_resume_after_not_reached`, `deferred_run_deadline_reached`, `no_published_industry_code`, `pac_pages_missing`,
`pac_amount_missing_or_unproven_zero`, `duplicate_roster_pac_id`, `roster_not_reconciled_to_industry_headline`, `parsed_clients_differ_from_source_count`, `split_component_not_explicit`,
`client_split_served_year_mismatch`, `http_annual_chart_unavailable_offline_native_export_used`, `org_profile_component_missing`, `org_*`.

## Receipt and timing
`python -m osc receipt` writes `RECEIPT.md`: per-run benchmarks computed from `request_log.jsonl` (events carry `run_id`; archived pre-`run_id` runs are split into the documented aborted/duplicate launches and the later run),
actual first-to-last wall time (rate-limit waits and restarts are not removed), transport calls vs redirect hops, cache hits, rate constraints, coverage, gaps and test results. Cold network time is limited by the site;
warm-cache offline extraction (`python -m osc build`, ~48 s measured on this workstation for the 1-collection cache of ~450 pages) is reported separately.
The refreshed full build completed at 2026-10-02T01:10:18Z in 206.640 seconds, including all CSV writing and validation of 3,109 present HTTP-200 cached bodies. It passed 58 checks with 10 informational checks and no failures; the dataset remains partial. This larger build is separate from both the earlier 450-page measurement and the fixed-sample component comparison below.
The October 2 UTC offline optimization reuses the already hash-checked client-split result and the validator's inspected metadata. Whole-cache body hashing and challenge rejection remain enabled. On 239 frozen captured F03 pages covering 2008-2010, including 234 client splits, median component extraction time fell from 4.114143 to 2.994704 seconds (27.2% less time); all three exported CSVs were byte-identical. This measures component extraction, not the whole build or network collection. Evidence: `C:/melange-data/forecast-redesign-20261001-review/standardized-collector/speed-review/benchmark_result.json`. Source requests retain the running collector's adaptive pacing and deferrals.
Tests: `python -m pytest tests -q` (`tests/test_osc.py` parser/fetch/extraction semantics, `tests/test_reviews.py` late-review regressions, `tests/test_offline_speed.py` integrity/missing/challenge rejection and metadata-snapshot reuse). Latest run: 60 passed in 15.62 seconds.

