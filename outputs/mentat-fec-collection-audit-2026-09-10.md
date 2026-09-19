# Mentat FEC collection and counting audit

Date: 2026-09-10. Review only. No collection rules, source databases, or spending workbooks were changed.

The review examined the current working tree, including pre-existing uncommitted changes. HEAD at inspection was `b526fbc7b`. Findings describe the inspected files, not a claim that every historical report used that exact version.

## Scope and flow

Mentat collects FEC Schedule A receipts using employer, individual-name (optional), and corporate-name searches. It stores receipt rows and raw API checkpoints, merges collection shards, checks coverage, exports raw snapshots, then classifies and aggregates report records. Separate FEC committee, transfer, and spending data support downstream views. OpenSecrets is not a collection dependency.

The principal review paths were `R/fec_api.R`, `R/collect.R`, `R/schema.R`, `R/report.R`, the industry exporter and builder, merge tooling, coverage gates, and raw warehouse exporter under `mentat/`.

## Findings

### 1. Source integrity is checked, but comparison with the previously accepted dataset is missing

**Status:** confirmed historical source-selection error; remaining control gap.

The September 8 repair manifest selects Fintech from `resilient-industry-runs/20260723T233744-16884/...`, whereas the completed Fintech report used the July 29 production database. The previous investigation established that this substitution lost 2026 records. The repair manifest also names older sources for several other industries.

The current builder correctly hashes the database, verifies that it remains unchanged during export, separates caches by database hash and cycle, and fingerprints classification code. These prevent stale cache reuse and inconsistent builds. They do not establish that the selected database is the intended accepted production source. The builder can also default to `MENTAT_DATA_ROOT/mentat.db` or `%LOCALAPPDATA%/Mentat/mentat.db` when no database is supplied.

I did not find a publication gate that reconciles each removed or changed source record against the previously accepted dataset. The last-good guard preserves/restores verified files; it is not a dollar-change reconciliation.

Evidence: `mentat/.cache/repair-20260908-databases/manifest.json`; `mentat/tools/build_industry_report.ps1:57`, `:332`, `:385`, `:418`; `mentat/tools/parallel/MentatLastGoodGuard.psm1:305`.

Repair principle: bind production builds to an explicit accepted source identity and produce a before/after ledger for source changes. A lower total can be correct, but each removal must have an explanation.

### 2. Missing receipt metadata allows non-contributions into giving totals

**Status:** confirmed stored-data gap and reproduced classifier behavior.

`fec_receipt_role()` recognizes selected contribution and other-receipt lines when `filing_form` and `line_number` are present. Unrecognized or missing metadata produces `unverified_receipt_role`. `fec_receipt_role_excluded()` does not exclude or otherwise require resolution of that status before the giving summary.

Both the completed and rebuilt Fintech databases lack `filing_form` in the individual table. Their corporate tables lack `filing_form`, `line_number`, `memo_text`, and the structured back-reference field entirely. The current exporter fills missing fields with NULL, so rebuilding these snapshots with the newer classifier does not restore their evidence.

Read-only measurements in the rebuilt Fintech database: 24,130 accepted individual rows have `line_number`, but no `filing_form` column exists. The corporate source has no receipt-role metadata columns. These counts cover the stored cycles, not only 2024.

An in-memory reproduction of the current classifier showed:

| Input | Classification | Excluded by receipt-role filter |
|---|---|---|
| STRIPE, missing form/line, memo describes return of erroneous debit | unverified_receipt_role | No |
| Same description with F3X / line 17 | other_receipt | Yes |

The earlier FEC check supplies a real positive control: Stripe's $190,000 Kentucky receipt is described as a return of an erroneous debit, although the completed report counts it as corporate giving. [Original FEC receipt](https://docquery.fec.gov/pdf/500/202309209597131500/202309209597131500_000049.pdf).

Evidence: `mentat/R/collect.R:29`, `:56`; `mentat/R/report.R:1743`, `:1812`.

Repair principle: recover missing FEC receipt metadata and make unresolved classification visible. Do not solve this by deleting all older corporate receipts.

### 3. Missing metadata is treated differently based on a company-name keyword

**Status:** reproduced rule inconsistency; population-wide dollar impact not measured.

With missing metadata, a contributor name containing the word `EXCHANGE` or `PROCESSOR` becomes `intermediary_role_review`, which the report excludes. Other names with equally missing evidence remain `unverified_receipt_role` and can count.

The in-memory reproduction classified `ACME EXCHANGE` with blank metadata as excluded, while `STRIPE` with blank metadata remained eligible. A keyword can identify a review candidate, but cannot establish the economic purpose of that specific receipt. This rule can suppress genuine gifts from an exchange while admitting settlements from a processor whose name lacks those words.

Evidence: `mentat/R/collect.R:43`, `:56`.

Repair principle: apply one evidence standard for transaction role. Keep a separate review status and resolve it with FEC metadata rather than deriving a final counting decision from the name.

### 4. Memo linkage has two concrete defects

**Status:** both reproduced against the actual R function in memory. Historical dollar impact remains unquantified.

The textual parent-reference matcher uses committee ID plus transaction ID. It does not scope that lookup by filing year or report, and its returned plan does not identify the retained parent.

Reproduction: a 2022 non-memo parent with transaction `SA11AI.42` and a 2024 memo containing `[SA11AI:42]`, at the same committee, caused the 2024 memo to receive `duplicate_memo=1` even though no 2024 parent was provided.

Separately, collection now stores `back_reference_transaction_id` and `back_reference_schedule_name`, but the memo planner and its database projection do not use them. A same-year memo with a structured link to a supplied parent, different amount, and no formatted text reference received `duplicate_memo=0`.

A targeted read-only scan of the rebuilt Fintech, Credit Union, and Crypto snapshots did not find cross-year-only textual parent matches. Crypto had four textual matches, all with a same-year parent available. Thus this is a demonstrated implementation defect, not a demonstrated cause of those reports' historical reductions.

Evidence: `mentat/R/schema.R:834`, `:881`, `:894`, `:921`; structured fields are collected at `mentat/R/fec_api.R:1876`.

Repair principle: match FEC relationships within the correct filing context, record the retained counterpart, and verify that counterpart actually contributes to the intended total. Matching amounts alone cannot establish duplication.

### 5. QA 'countable' amounts and report amounts use different rules

**Status:** confirmed code inconsistency.

The report filters receipt-role exclusions. The QA queries for `countable_rows` and corporate `countable_dollars` only test accepted company matching, blank exclusion reason, and the memo-duplicate flag. They omit the receipt-role filter.

Consequently, a known other receipt can be excluded from the giving report but still described as countable by QA. This does not by itself prove a bad workbook total; it means that QA metric cannot validate that total.

Evidence: report predicate at `mentat/R/report.R:1812`; QA predicates at `:3129` and `:3154`.

Repair principle: derive giving-related QA metrics from the same explicit inclusion decisions used by the report, then independently test whether those decisions are supported by the source records.

## Existing behavior that must not be misreported as missing or silently changed

- **Raw preservation already exists.** The warehouse retains scoped raw rows, including rejected, superseded, and duplicate-flagged records. Newer exports include receipt roles, inclusion reasons, and source links. Large workbook projections preserve the complete source payload separately. What is missing is a consistent explanation of changes between accepted versions.
- **Funding and party breakdowns already exist.** They should be retained. The report's `Company PAC` category identifies a recipient PAC (`report.R:2478–2521`), meaning employee-to-PAC funding. It is not an outgoing PAC-spending measure. Separate PAC evidence and downstream views already exist; they need consistent direction labels and separation from corporate treasury giving.
- **Conduit legs are deliberately retained.** `schema.R:863–868` records the prior recipient-as-shown R5/R8 decision. Removing every intermediary or memo leg would change that decision. A gross flow view and a unique-contribution view require explicit, different definitions. FEC itself documents that one earmarked contribution can generate several receipt and memo records: [FEC reporting example](https://www.fec.gov/help-candidates-and-committees/filing-reports/contributions-received-through-conduits/).
- **Amendment handling also has an explicit existing behavior.** Tests currently require both original and amended donor rows in the donor report, while version flags are retained. This differs from some README wording and downstream current-version treatment. This audit does not authorize silently changing that counting policy.
- **Collection controls are substantial.** The API checks pagination/cursors and checkpointed completion; merges use ownership/collision checks; coverage gates and raw snapshot hashes are present. Those controls cannot independently establish the economic meaning of every receipt.

## Verification and limits

- Read-only SQLite inspection of completed and rebuilt Fintech sources; targeted memo-reference scans of rebuilt Fintech, Credit Union, and Crypto.
- Executed the current R receipt classifier and memo planner on small in-memory reproductions. No database was opened for writing by those reproductions.
- `test_collection_coverage.py`: 23 tests passed.
- `test_validate_industry_coverage.py`: 7 tests passed.
- The full R receipt-role test could not run because the available R runtime could not load `data.table`, including after using the configured library path. No packages or environment configuration were installed or changed persistently.
- An isolated Python coverage-grid check confirms that this particular gate requires at least one employer and one corporate unit per company/cycle. It does not independently enumerate every expected alias. The surrounding collector has additional completion checks, so this observation is not evidence that a normal successful run omits aliases.
- No fresh production collection, database migration, workbook rebuild, or automatic exclusion was performed.

## Recommended order after approval

1. Add accepted-source and before/after record reconciliation controls.
2. Recover missing FEC role metadata; expose unresolved receipts without blanket deletions.
3. Correct memo linking and preserve both the excluded record and its counted counterpart.
4. Align QA counting predicates and make donor, treasury, PAC inflow, and PAC outflow labels explicit.
5. Keep existing partisan metrics, with coverage denominators attached to each view.
