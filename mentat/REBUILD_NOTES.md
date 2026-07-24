# Mentat rebuild notes — fix batch R3

## Scope and safety

This rebuild implements every item in FIX_TASK.md Groups A through D. No commit was created. No live network request was made, no API key was read or persisted, and no database outside this workspace was opened or changed. All executable verification used synthetic fixtures or package-independent unit tests.

## Changes that alter reported dollar amounts

The following changes can change report totals or their allocation:

- Downstream `EARMARKED THROUGH` attribution legs are removed while the ActBlue/WinRed conduit receipt is retained. This removes the confirmed conduit/downstream double count and can reduce totals that previously included both legs.
- The squashed-prefix matcher now accepts only an exact squashed alias or a remainder composed entirely of known corporate qualifiers. False associations such as `G.E. MINISTRIES INC.` → Gemini and `CRYPTO COMPANY` → Crypto.com move to review, reducing affected company totals. Load-bearing exact forms such as `BINANCEUS` and `COIN BASE` remain accepted.
- Roster exclusions now inspect contributor name, employer, and occupation on every pass, including the corporate-name pass. Rows such as excluded tZero corporate names are rejected and no longer contribute dollars.
- Legacy `corporate_giving` rows with no computed match reason are excluded. A migration that adds the status field marks existing rows `review` with `migration_requires_revalidation`; databases already carrying the older accepted-by-default field are protected by the report's nonblank-reason requirement. Corporate totals can decrease until those rows are explicitly revalidated.
- The restored corporate API projection allows valid corporate pages to be stored. Relative to the broken phase that stored no corporate rows, valid corporate and total-giving dollars can increase.
- Party names abbreviated `Cmte`, `Cmte.`, or `Comm` are classified as `Party Committee`; other unmarked rows become `Unclassified` instead of `Candidate`. This changes the underlying category allocation. Both categories deliberately roll into the Stats Candidate column, so this relabeling alone does not change that aggregate column.
- Leadership PAC dollars now map to the Company PAC Stats column. Party Committee, JFC, and Unclassified dollars map to Candidate. This fixes category allocation and the reconciliation blocker.
- API pagination now refuses count shortfalls, partial cursors, cursor cycles, count changes, overruns, and page-ceiling overruns. A successful API result therefore cannot silently omit rows; complete totals may be higher than a previously truncated run.
- Data-driven diminutives can establish an identity-name equivalence only when the rest of the identity ladder also qualifies the row, such as matching ZIP or city. This can restore qualifying personal giving that an exact-first-name comparison missed.
- Unverified bare `GEMINI` employer hits go to review; a known-person cross-reference is required for acceptance. This can remove false Gemini dollars while retaining verified people.
- Blank or missing `entity_type` now defaults to a person unless the contributor name itself is company-shaped. Report generation recomputes this flag instead of preserving a stale stored flag. Total Giving is unchanged, but Corporate Giving can decrease while person and Chief/Middle/Employee columns increase.

The legitimate ActBlue split-receipt change does not itself add or remove dollars: distinct `sub_id` receipts are retained and no longer trigger a false hard stop. Retry, checkpoint, batching, BOM, geometry, and query-cache changes do not intentionally change dollar values.

## Group A — dollar correctness

- **A1:** `spending_downstream_earmark_mask()` identifies downstream legs from `receipt_type_full` and `conduit_committee_id`. The report keeps the conduit receipt and drops downstream and memo-X legs. The regression uses the confirmed three-row SILVERBERG anatomy.
- **A2:** The kept-receipt invariant uses nonblank, unique FEC `sub_id` values and separately asserts that no downstream earmark leg survived. A ten-row BALACHANDER/ActBlue split fixture proves legitimate equal-value rows are allowed.
- **A3:** Squashed-prefix matching parses the entire remainder as known corporate qualifier tokens; other remainders are review-only.
- **A4:** Exclusion evaluation includes contributor name, employer, and occupation. Exclusions take precedence over persistent accept overrides.
- **A5:** New corporate rows default to `review`/non-entity until computed, migrated rows require revalidation, and reports require an explicit accepted status plus a nonblank match reason.
- **A6:** Party detection accepts `COMMITTEE`, `CMTE`, and `COMM` after intervening words; the unmarked default is `Unclassified`.

## Group B — blockers

- **B1:** Category reconciliation uses `rep(names(groups), lengths(groups))`, aligned to the flattened category values, rather than indexing the five group names with nine category positions.
- **B2:** Header-only company-match override columns are coerced to character before normalization.
- **B3:** Corporate API records retain `recipient_committee_type` for checkpoint storage.
- **B4:** The rebuilt Stats contract is strict at 86 headers, 85 formula metrics, and an 84 × 87 grid. The synthetic report fixture has six sheets: two template sheets, three dynamic raw-input sheets, and `Sheet4`. Its post-header-restoration formula count is 6,035. The old 83/82/84 × 84/four-sheet/5,822 expectations were updated because they described the pre-rebuild artifact.

## Category to Stats-column mapping

| Source category | Stats column |
| --- | --- |
| Super PAC | Super PAC |
| Carey | Carey |
| Company PAC | Company PAC |
| Leadership PAC | Company PAC |
| Trade Association | Trade Association |
| Candidate | Candidate |
| Party Committee | Candidate |
| JFC | Candidate |
| Unclassified | Candidate |

Registered `527` and `501c` rows remain visible in support data as `EXCLUDED_527_501C` and are excluded from the Stats giving range.

## Group C — API correctness

- **C1:** Each work unit establishes and enforces `pagination.count`; count completion stops without an unnecessary empty request, while a missing cursor before count completion is a hard error.
- **C2:** Both keyset cursor members must be present, scalar, non-null, and nonblank in responses and requests.
- **C3:** Every cursor signature is retained for the work unit, so A→B→A cycles fail; a 10,000-page ceiling is also enforced.
- **C4:** `Retry-After` is honored for all retryable responses, capped at 120 seconds, and scheduled per request rather than as one batch-wide maximum.
- **C5:** Parallel httr2 calls use `on_error = "continue"`; successful responses survive and only failed requests retry. Transport errors are normalized without exposing the API key.

## Group D — optimization and resilience

- **D1:** Contributor-name identity collection defaults off and is enabled with `--phase2-names`. Raw API pages, cursors, seen keysets, fetched/stored state, and a persistent 1,000-request hourly budget are stored in the local Mentat database. Budget exhaustion or sustained 429 responses records a paused run and exits before reconciliation/reporting; a later run resumes checkpoints. Logs report requests used and remaining.
- **D2:** Roster overrides and trusted-name keys are cached per company/work phase. Data inserts use temporary staging tables and set-based `INSERT OR IGNORE`; completed API work units are stored in one transaction. API concurrency halves after a 429 and increments toward the configured maximum after a clean batch.
- **D3:** `inputs/name_diminutives.csv` contains 168 unique canonical/variant seed rows, is validated and loaded at ingest, and drives `person_identity_key()` without code edits. This is a seed, not an exhaustive authority.
- **D4:** Bare Gemini employer matches require a trusted person key; verified Gemini legal aliases remain accepted and unverified extensions are rejected or reviewed.
- **D5:** CSV output again uses UTF-8 with a BOM through `data.table::fwrite(..., bom = TRUE)` followed by atomic replacement.
- **D6:** Only explicit `ORG`, `COM`, `PAC`, or `CCM` types, or a company-shaped contributor name, mark an entity. Blank/NA types default to individual.

### Ambiguous diminutive seed values

These variants occur under more than one canonical and therefore normalize only to themselves; they are never a sole identity-match basis:

- `chris`: CHRISTOPHER / CHRISTINE
- `harry`: HAROLD / HENRY
- `jon`: JOHN / JONATHAN
- `kate`, `katie`: CATHERINE / KATHERINE
- `pat`: PATRICK / PATRICIA
- `patty`: MARTHA / PATRICIA
- `rick`: FREDERICK / PATRICK / RICHARD
- `sam`, `sammy`: SAMUEL / SAMANTHA
- `sandy`: ALEXANDER / SANDRA
- `steve`: STEPHEN / STEVEN
- `ted`, `teddy`: EDWARD / THEODORE

## Verification and live follow-up

Offline regressions cover the real earmark anatomy, legitimate split receipts, false squashed prefixes, exclusion precedence, category mapping, cursor count/cycle/ceiling behavior, capped per-request retries, partial-batch recovery, adaptive concurrency, Gemini trust gating, ambiguous diminutives, blank entity types, corporate report formulas, and BOM bytes.

No live database or API verification was performed by design. Before publishing production reports, run the rebuild against an authorized scratch copy of the live Mentat database and compare, by company/year/category: dropped downstream earmark dollars, newly reviewed squashed-prefix and Gemini dollars, exclusion removals, corporate rows awaiting revalidation, corporate rows restored by the API phase, and person-versus-corporate reclassification. Confirm that the corporate migration and checkpoint resume behave as expected on that copy.

In this managed session, `test_fec_api.R`, `test_fec_page.R`, and `test_rules.R` pass. The prescribed external R 4.6 user library exists but is not traversable from the sandbox, so R sees only its base library; `test_ingest.R` and `test_reconcile.R` stop before assertions because `data.table` is unavailable, while `test_names.R` and `test_report.R` stop before assertions because `DBI` is unavailable. No network install or sandbox bypass was attempted.

## R4 — unservable employer queries and bulk completeness audit

### Evidence and fallback design

The live evidence supplied for this batch showed that `contributor_employer=Binance` in cycle 2024 reproducibly returned 504 while the same term served in adjacent cycles. After one slow 504, openFEC also returned an immediate circuit-breaker 504. The API retry layer now classifies a query as `unservable_query` after no more than two 504 attempts; ordinary 503/other transient responses retain the existing `Retry-After` and retry behavior.

An unservable employer unit is decomposed into spellings observed in the optional FEC bulk supersets. The failed normalized term is excluded, each narrower spelling is queried independently, and every returned API row is unioned by exact `sub_id` and sorted before checkpoint/storage. If no observed register is available, roster variants provide the fallback candidates. The console emits `unservable_query: <term> cycle <n> -> decomposed into k queries, m rows`, and the same event—including its spelling list and union row count—is stored as JSON in that cycle's `run_log.decomposition_log`.

### Bulk register, rescue, and audit

Phase 0 reads the 2022/2024/2026 pipe-delimited 21-column bulk supersets from `MENTAT_BULK_DIR` or `<MENTAT_DATA_ROOT>/bulk`. Missing files warn and do not block API collection. Only rows accepted by `company_employer_match`, with normal roster exclusions applied, enter the row-level `bulk_candidates` register. `observed_employers` stores distinct cycle/spelling counts and is the decomposition source. In particular, an excluded `SEATTLE KRAKEN` row cannot seed a Kraken fallback query.

After employer collection, each still-missing bulk `sub_id` is queried by contributor name and ZIP when available. Pagination continues only until the exact target ID is found or the narrow query completes. Near-miss IDs are discarded; the matching API row—not the whole-dollar bulk row—is flattened through the normal matcher/exclusion path with phase `P3_bulk_rescue`. `MENTAT_RESCUE_CAP` defaults to 50 actual requests, including retries and additional pages. Rows not started because the cap is exhausted are written to `reports/bulk_rescue_overflow.csv` without another request.

`reports/bulk_audit.csv` contains every Crypto company × supported cycle with bulk candidate, ordinary API capture, rescued, and unreachable counts. `reports/bulk_audit_unmatched.csv` lists the remaining IDs and bulk provenance fields. Unreachable rows are reported and printed but do not fail the run.

### Offline verification and live follow-up

Synthetic tests cover two 504s followed by observed-spelling decomposition, cross-spelling `sub_id` deduplication and sort order, unchanged 503 `Retry-After` behavior, exact rescue acceptance versus a same-name near miss, the 50-request boundary with candidate 51 never sent, a pipe-delimited register fixture whose `SEATTLE KRAKEN` row is excluded, and captured/rescued/unreachable audit counts. No live network call was made.

Before publishing refreshed reports, verify against an authorized scratch copy that the three real supersets ingest with expected company-cycle counts; Binance 2024 decomposes specifically to the serving observed spellings; bare-employer sub_id `4051020251191476176` is recovered by the name/ZIP query with the cent-exact API amount; the decomposition JSON survives a resume; and the audit totals reconcile to independent bulk `sub_id` sets. Also confirm whether any narrow rescue query needs more than one page and whether the default cap leaves overflow in the real run.

## R5 — Paul's recipient-as-shown convention and amendment versioning

Paul's ruling is the design authority: every current FEC row counts to the recipient shown on that row. Memo-code-X, conduit, passthrough, negative, refund, and redesignation rows therefore remain in report raw sheets, `Sheet4`, Stats inputs, and reconciliation. The leg columns remain analytical flags only. The kept-row invariant is now a nonblank, unique FEC `sub_id`, plus exclusion of filing versions actually superseded by an amendment; `spending_downstream_earmark_mask()` is retained only as an unused analytical helper.

Amendment versioning runs identically over `contributions` and `corporate_giving`. Collection now persists `transaction_id`, `original_sub_id`, `amendment_indicator`, `report_year`, `report_type`, `file_num`, `pdf_url`, and `load_date` into both stores. Explicit original-sub-ID chains take precedence, followed by committee/report/transaction identity. `file_num` determines the latest filing when present, then the FEC document ID, load timestamp, and the filing date encoded in `sub_id`; all rows tied within the current filing remain because distinct current-view `sub_id` rows are facts. For legacy corporate rows whose older schema discarded transaction fields, an exact row identity seen across distinct encoded filing dates is versioned to the latest filing date, while multiple rows in that latest filing are all retained. Earlier rows are marked `superseded_by_amendment=1`, remain in SQLite, and are the only amendment rows omitted from reports and reconciliation. Reliability output and the console log rows superseded and before/current dollar totals by company.

On the supplied offline scratch database, Coinbase corporate giving changes from **$307,890,854.93 across 457 rows** to **$213,890,859.93 across 453 current rows**: four older filing rows and $93,999,995.00 are superseded. Coinbase-to-FAIRSHAKE changes from **$293,974,208.87 across 22 rows** to **$199,974,213.87 across 18 current rows**. This is the intended $100M-plus order of magnitude rather than the amendment-stacked roughly $300M result. No live request was made for this verification.

Full-row fixture reconciliation adds the 93 previously suppressed memo-X rows. Strict one-to-one matching is **1,180 / 1,189 (99.24%)**; the three explicitly named rows present in SQLite bring database coverage to **1,183 / 1,189 (99.50%)**, above the 99.33% gate. They remain named as residuals rather than being silently counted as one-to-one matches:

- Fixture 562 — OBRIEN, MOLLY → ACTBLUE, 2025-10-07, $100: exact database row present; the single candidate was already consumed by a duplicate fixture tuple.
- Fixture 1177 — PETERS, ERIC → HIMES FOR CONGRESS, 2025-01-06, $3,300: exact database row present; the single candidate was already consumed by a duplicate fixture tuple.
- Fixture 1182 — ARMSTRONG, BRIAN → NRCC, 2025-05-06, $44,300: contributor/date/amount are present, but the row's displayed recipient differs.

The six genuinely absent fixture rows are:

- Fixture 1183 — CHOI, EMILIE → NRSC, 2026-02-10, $44,300.
- Fixture 1184 — CHOI, EMILIE → NRSC, 2026-02-10, $5,700.
- Fixture 1185 — CHOI, EMILIE MONICA → TOMORROW IS MEANINGFUL PAC, 2025-04-11, $5,000.
- Fixture 1186 — TUSAR, GREG → DEMOCRATIC GRASSROOTS VICTORY FUND, 2026-05-01, $44,300.
- Fixture 1187 — TUSAR, GREG → DNC SERVICES CORP / DEMOCRATIC NATIONAL COMMITTEE, 2026-05-01, $44,300.
- Fixture 1189 — SHIRZAD, FARYAR → CLUB FOR GROWTH ACTION, 2025-02-18, $2,850.

The updated offline regressions retain and independently classify all three SILVERBERG recipient rows, keep both signed redesignation rows and prove they net to zero in Stats facts, and verify that original/amended transactions in both contribution stores report only the amended amount. The seven-file suite remains the required final verification surface.

## R7 — cross-cycle corporate filing versions

The confirmed Coinbase-to-FAIRSHAKE receipt on 2024-12-20 for $23,000,000 was stored five times under `sub_id` values `4020420251141540904`, `4030420261386079659`, `4030420261386079661`, `4081520251218411849`, and `4081520251218411851`. The first capture came from the 2024 query and the other four from the 2026 query. All eight amendment/version columns on these legacy `corporate_giving` rows are null, so transaction-ID amendment versioning cannot connect them.

R7 adds a filing-capture identity independent of `sub_id`: normalized `(company, committee_id, contribution_receipt_date, contribution_receipt_amount)` for corporate rows. Each identity keeps one deterministic row, preferring the highest available `file_num` and latest amendment metadata, then the lexicographically highest `sub_id`; every loser remains in SQLite with `excluded_reason='duplicate_filing_version'`. Corporate checkpoint writes carry `transaction_id`, `original_sub_id`, `amendment_indicator`, `report_year`, `report_type`, `file_num`, `pdf_url`, and `load_date` end to end and backfill those fields when a previously stored `sub_id` is seen again with version metadata. The run summary reports duplicate filing rows and their dollar delta for every company.

The person-contribution identity additionally includes normalized `contributor_name` and ZIP. It collapses only rows connected by a shared nonblank `transaction_id` or an explicit `original_sub_id` chain. Unlinked same-person/same-day/same-amount receipts therefore remain separate facts: all ten BALACHANDER-to-ActBlue $1.67 rows survive, as do equal receipts from two different people. This is the split-versus-version boundary; the broader four-field collapse is confined to the corporate store where the cross-cycle damage is proven.

A read-only parity calculation over the supplied live scratch database projects **$130,005,470.68** of accepted Coinbase corporate giving after R7, including **$117,092,475.00** to FAIRSHAKE. Across all Coinbase corporate rows, independent of match-status report filters, filing-identity collapse flags 83 rows and $133,144,778.72, changing the raw $307,890,854.93 to $174,746,076.21. The managed sandbox could not execute the required final R report run because it cannot traverse `C:/Users/pgoff/AppData/Local/R/win-library/4.6`; these projected report totals must be replaced or confirmed by the prescribed `--skip-scrape` run once that library is visible.

## R8 — no-culling law, location-aware brand matching, and optimization

Paul's standing law is that raw/extract output contains every row returned by the FEC. Memo-X, conduit, negative/refund, redesignation, amendment, and duplicate filing-version rows are never filtered from raw sheets. `excluded_reason`, `is_memo_leg`, `is_conduit_leg`, `superseded_by_amendment`, and `duplicate_filing_version` are visible audit columns. Deduplication is a flag, never a raw-row filter.

Analysis uses one duplicate rule and no date/amount collapse: a memo-X row is flagged only when a non-memo row exists with the same `(company, committee_id, date, amount, contributor_name)`. A memo row naming a different committee is a real earmark leg and counts. This preserves Coinbase → FAIRSHAKE sub-ID `4020420251141540904` as the real line-11AI receipt while flagging the four same-recipient line-17 memo re-descriptions. The resulting real total is **$161,474,209**, not **$293,974,209**. Split gifts remain independent facts; all ten BALACHANDER $1.67 rows survive raw output and analysis. Each netting sheet states this rule and the flagged-row count.

Ambiguous single-token brands are disambiguated from file-backed roster metadata rather than a company exception in R. `inputs/company_home_states.csv` declares one or more home states; Gemini declares **NY**. A bare-brand row in a home state is accepted when its occupation is outside the manual-trades denylist. A home-state manual-trade row remains review, while an out-of-state manual-trade row is rejected. `company_match_overrides.csv` now supports optional `state` and `occupation_pattern` scopes while legacy three-column files remain valid, and the supplied 31-row override register takes precedence over automatic rules. This restores the verified **86 Gemini rows / $681,565** in New York and prevents roughly **$240,000** of unrelated Gemini-brand accepts in NH, TX, KS, and MN.

Run-level lookup caches now load company rosters, company-match overrides, home states, trusted names, and report committee-master registers once. Page matching reuses one precomputed company context, and completed API work units retain one insert transaction across all stored pages. Collection and report generation both emit rows/second benchmark lines. No live network verification was performed for R8.

## R9 — fail-closed pagination and production-size report speed

The API page ceiling is fail-closed again: exceeding `FEC_API_MAX_PAGES_PER_UNIT` raises `FEC API page ceiling exceeded` instead of warning and marking an incomplete work unit complete. The existing ceiling regression now passes with the full API suite.

Report preparation now applies amendment/filing/memo version flags once per `write_reports()` call and shares the prepared lookup, raw-row, and analysis-row objects across the workbook, reliability report, and unclassified-recipient export. The normal and retag-only entry paths also avoid a second company/identity retag inside `write_reports()`. Standalone report helpers retain safe defaults and still prepare their own state when called directly. `test_report.R` pins the one-versioning-pass contract.

Raw-sheet date and amount formatting no longer reconstructs an entire worksheet XML string once per cell. Each column is rewritten in one linear pass, preserving the same style IDs and workbook contract. On a disposable copy of the 15.6 MB scratch database, the no-network pipeline completed in **175.6 seconds**; report generation processed **12,934 rows in 60.56 seconds (213.57 rows/second)**. The prior implementation exceeded a 304-second command ceiling. Reconciliation finished at **1,184/1,189 strict matches (99.58%)** and **1,189/1,189 database coverage (100.00%)**. All seven offline test scripts and all 16 R-file parse checks pass. No live database or network request was used.

## R10 - Spending Report visibility, Excel compatibility, and corporate coverage

The missing Stats display had four independent causes. First, all 6,035 formula caches were zero, so non-calculating viewers showed an empty report. Second, 82 legacy `corporate_giving` rows were stranded at `migration_requires_revalidation`, so no corporate facts reached Stats. Third, qualified legal/trade names accepted by the corporate matcher were later downgraded by the report's older exact-only entity recomputation. Fourth, 180 generated partisan formulas exceeded Excel's hard 8,192-character limit (maximum 8,932), causing Excel itself to reject the workbook.

Report generation now computes and bulk-patches exact formula caches, preserves validated corporate-source provenance, and keeps automatic calculation enabled without forcing a full rebuild on open. The partisan formula uses an algebraically equivalent `IFERROR` guard and the production maximum is **5,365 characters**. Calculation metadata inherits the template's current `calcId=191029`; cached values remain immediately visible, while edits still recalculate automatically. The Stats Super PAC value column is widened just enough to eliminate the twelve production `####` cells found by the visual pass.

Corporate revalidation now runs in normal, retag-only, and standalone report flows. Literal aliases, vetted corporate qualifiers, and the scoped `COINBASE COMMERCE EXCHANGE` persistent override restore all **82/82 corporate rows** to Sheet4 as `CORPORATE`; unrelated `KRAKEN COMMERCE` remains review. `--retag-only` reloads file-backed rosters and overrides before applying tags, so newly approved register changes are no longer silently ignored. Reliability output includes corporate accepted/review/rejected coverage, the company review queue includes corporate contributor names, and run wall-clock is reported once per `run_id` rather than duplicated across cycles.

Final offline receipts on the disposable production-size database: SQLite `integrity_check=ok`, no foreign-key violations, **12,934/12,934 raw rows** present across company-cycle sheets, **5,410 contribution + 82 corporate facts** in Sheet4, 34 sheets, 6,035 formulas, and no ZIP/XML corruption. Excel 16 opened the 2.40 MB workbook read-only in **0.923 seconds**, reported `xlDone`, returned the cached Coinbase 2026 total **$1,370,221.74** and corporate total **$500,000**, and found **0 formula errors / 0 clipped Stats cells**. The full clean no-network pipeline completed in **135.585 seconds**; the final report-only regeneration completed in **47.296 seconds**. Reconciliation remained **1,184/1,189 strict (99.58%)** and **1,189/1,189 database coverage (100.00%)**. All seven offline test files passed in **14.968 seconds**. No live database or network request was used for these receipts.

## R11 - checkpointed live augmentation and completion telemetry

With no registered `FEC_API_KEY` present at process, user, or machine scope, the authorized live augmentation used Mentat's documented Chrome fallback against the isolated R10 scratch database. `--resume-after=2026-07-18T00:00:00-0500` activated the 1,066 July 19 browser checkpoints, so completed employer and identity walks were skipped while the previously interrupted Gemini/Kraken/MIAXdx/tZero tail resumed after the strict retag fix. Run `20260722T150443-27692` completed all three cycles with zero retries in **1,480.7 seconds (24m41s)**. The collection phase reported **1,302.940 seconds**, **14,818 contribution rows**, and **11.37 rows/second**; report generation processed **15,840 raw rows** in **65.570 seconds (241.57 rows/second)**.

The augmented SQLite database is **20,271,104 bytes**, passes `PRAGMA integrity_check`, has no foreign-key violations and no freelist pages, and contains **14,818 contribution rows + 1,022 corporate-query rows**. Corporate revalidation leaves **91 accepted corporate facts**, **928 rejected individual-entity query hits**, and **3 review rows**. The three review rows are the deliberately ambiguous Gemini names `GEMINI G.E.L.` and `GEMINI ELECTRIC, INC`; unrelated `KRAKEN COMMERCE` remains review in the contribution store. Fixture reconciliation remains **1,184/1,189 strict (99.58%)** and **1,189/1,189 database coverage (100.00%)**.

The promoted workbook is **2,868,485 bytes** with 35 sheets, a clean ZIP, valid XML, **6,035 formulas**, maximum formula length **5,365**, and **5,980 contribution + 91 corporate + 16 method** facts in Sheet4. Excel 16 opened it read-only in **1.780 seconds**, reached `xlDone`, returned Coinbase 2026 C3 **$1,370,221.74** and F3 **$500,000**, and found **0 formula errors / 0 clipped Stats cells**. The complete seven-file regression suite passed in **15.384 seconds** after augmentation; after the telemetry correction, all 16 R files parsed and the suite passed again in **17.529 seconds**. The promoted SHA-256 is `C15AF41FADAE883EED0EBD26BD340E1662693F16D2E98729A93ACC3046E8AB06`.

The run exposed a completion-telemetry bug: Chrome collection was recorded as `requests=0` because only the API engine returns an exact request count. Future completion messages now distinguish `engine=api; network_requests=N`, `engine=offline; network_requests=0`, and `engine=chrome; network_requests=n/a` while persisting Chrome row and collection-wall metrics; all three cases have a regression assertion.

One external coverage limitation remains explicit: the optional `indiv22_crypto_superset.psv`, `indiv24_crypto_superset.psv`, and `indiv26_crypto_superset.psv` files are absent from the isolated data root. Browser collection and fixture reconciliation completed, but the independent bulk-candidate/API-capture/rescue audit has no candidate population until those supersets are supplied. The pipeline warned and used roster variants as designed; this is missing optional source coverage, not database or workbook corruption.
