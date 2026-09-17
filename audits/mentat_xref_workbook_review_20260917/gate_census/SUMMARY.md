# Receipt-evidence gate census

Read-only reproduction of `fec_assert_receipt_evidence(raw_rows[evidence_scope])`
(`mentat/tools/export_crypto_spending_data.R:225`, gate body at
`mentat/R/collect.R:137-147`). These are the rows the exporter would
REFUSE at export time, per industry.

## Per-industry

| industry | rows loaded | rows in evidence scope | rows refused | dollars refused | % of scope |
| --- | ---: | ---: | ---: | ---: | ---: |
| Banking | 851,197 | 849,399 | 593 | $1,797,578.54 | 0.070% |
| Community Banks | 4,661 | 4,649 | 11 | $43,614.46 | 0.237% |
| Credit Arms | 435,416 | 434,958 | 17 | $503,814.17 | 0.004% |
| Credit Union | 67,282 | 67,169 | 4 | $3,012.57 | 0.006% |
| Crypto | 14,839 | 14,801 | 80 | $187,536,167.90 | 0.541% |
| Fintech | 86,444 | 86,270 | 94 | $267,009.24 | 0.109% |
| Property & Casualty Insurance | 360,984 | 360,207 | 53 | $16,679.98 | 0.015% |
| Telecom | 809,355 | 808,066 | 96 | $1,844,658.17 | 0.012% |
| **total** | **2,630,178** | **2,625,519** | **948** | **$192,012,535.03** | |

## Top 5 description groups per industry

Grouped by `(filing_form, line_number, normalized description)`, where the
normalized description is exactly what the classifier keys on:
`normalized(receipt_type_full)` then `normalized(memo_text)`, pasted and
trimmed (`collect.R:46-49`). Full top-60 tables are in `<slug>_groups.csv`.

### Banking

| form | line | normalized description | rows | dollars | example sub_id |
| --- | --- | --- | ---: | ---: | --- |
| F13 | F132 | (empty) | 1 | $1,000,000.00 | `4092420211371961952` |
| F3X | 17 | (empty) | 230 | $456,843.38 | `4012120231719623781` |
| F3 | 15 | (empty) | 196 | $225,322.85 | `1051720240265374956` |
| F3 | 15 | CONTRIBUTION EARMARKED FROM WINRED | 26 | $67,050.00 | `4032920241888320307` |
| F3 | 15 | CONTRIBUTION REDESIGNATION FROM GENERAL | 3 | $8,700.00 | `4032920241888318661` |

(51 distinct groups total)

### Community Banks

| form | line | normalized description | rows | dollars | example sub_id |
| --- | --- | --- | ---: | ---: | --- |
| F3 | 15 | NON CONFORMING CHECK REDEPOSIT | 1 | $30,032.00 | `4120820221633618951` |
| F3 | 15 | ACH FAILURE TO SETTLE RETURN | 1 | $4,082.46 | `4110920221625161798` |
| F3 | 15 | NON CONFORMING IMAGE CHECK REDEPOSIT | 2 | $3,400.00 | `4110920221625161799` |
| F3 | 15 | NON CONFORMING IMAGE CHECK RETURN | 1 | $3,000.00 | `4110920221625161797` |
| F3 | 15 | NON CONFIRMING CHECK REDEPOSIT | 1 | $2,000.00 | `4120820221633618950` |

(7 distinct groups total)

### Credit Arms

| form | line | normalized description | rows | dollars | example sub_id |
| --- | --- | --- | ---: | ---: | --- |
| F13 | F132 | (empty) | 1 | $500,000.00 | `4092420211371966880` |
| F3X | 17 | (empty) | 2 | $1,505.00 | `4012120231719624281` |
| F3X | 17 | EARMARKED THROUGH ACTBLUE VOTER FILE PURCHASE AT FAIR MARKET VALUE | 3 | $750.00 | `4050220231746130144` |
| F3X | 17 | EARMARKED CONTRIBUTION THROUGH ACTBLUE PAC ON 12 07 2025 HQ ACCOUNT... | 1 | $500.00 | `4021120261305869205` |
| F3X | 17 | VOTEBUILDER ACCESS AT FAIR MARKET VALUE | 1 | $500.00 | `4120120221632523612` |

(10 distinct groups total)

### Credit Union

| form | line | normalized description | rows | dollars | example sub_id |
| --- | --- | --- | ---: | ---: | --- |
| F3X | 17 | DUPLICATE TRANSACTION SENT IN ERROR RETURN INITIATED 06 05 2025 | 1 | $1,392.27 | `4011320261301413154` |
| F3X | 17 | DUPLICATE TRANSACTION SENT IN ERROR RETURNED ON 3 13 25 | 1 | $1,308.27 | `4042420251186468572` |
| F3X | 17 | VOTER FILE PURCHASE AT FAIR MARKET VALUE | 1 | $309.95 | `4082020251219018174` |
| F3 | 15 | (empty) | 1 | $2.08 | `4011320251128197633` |

(4 distinct groups total)

### Crypto

| form | line | normalized description | rows | dollars | example sub_id |
| --- | --- | --- | ---: | ---: | --- |
| F3X | 17 | 236 20702457 BITCOINS BTC CONTRIBUTION PREVIOUSLY DISCLOSED AGGREGA... | 4 | $92,000,000.00 | `4030420261386079659` |
| F3X | 17 | NON CONTRIBUTION | 4 | $35,000,000.00 | `4012020261302797780` |
| F3X | 17 | 24 999 995 USDC CONTRIBUTION PREVIOUSLY DISCLOSED | 1 | $24,999,995.00 | `4081220242011729506` |
| F3X | (blank) | (empty) | 4 | $19,767,475.00 | `4030420261386079642` |
| F3X | 17 | 15 500 000 USDC CONTRIBUTION DISCLOSEDON ON LINE 11 A | 1 | $15,500,000.00 | `4021420241824800143` |

(34 distinct groups total)

### Fintech

| form | line | normalized description | rows | dollars | example sub_id |
| --- | --- | --- | ---: | ---: | --- |
| F3X | 17 | LEGAL PROCEEDINGS ACCOUNT CONTRIBUTION IMPERMISSIBLE CONTRIBUTION S... | 1 | $132,900.00 | `4061120251205747992` |
| F3X | 17 | HEADQUARTERS ACCOUNT CONTRIBUTION IMPERMISSIBLE CONTRIBUTION SEE JU... | 1 | $72,800.00 | `4061120251205747991` |
| F3X | 11AI | CONTRIBUTION IMPERMISSIBLE CONTRIBUTION SEE JUNE MONTHLY REPORT FOR... | 1 | $44,300.00 | `4061120251205744909` |
| F3 | 15 | CONTRIBUTION REFUND TO BE ISSUED | 1 | $5,800.00 | `4032920241888320302` |
| (blank) | 11AI | (empty) | 2 | $4,000.00 | `4062320261522332595` |

(14 distinct groups total)

### Property & Casualty Insurance

| form | line | normalized description | rows | dollars | example sub_id |
| --- | --- | --- | ---: | ---: | --- |
| F3X | SL1A | (empty) | 1 | $5,000.00 | `4052420231748251675` |
| F3 | 15 | REDESIGNATION TO RECOUNT REDESIGNATION TORECOUNT RECEIPT AS PER AO ... | 1 | $3,300.00 | `4022820241858369449` |
| F3P | 21 | REDESIGNATION FROM GENERAL | 2 | $2,390.00 | `4011320251129875053` |
| F3X | 17 | REFUND FOR WORKERS COMPENSATION INSURANCE | 1 | $2,180.00 | `4051320241923129474` |
| F3X | 17 | OVERPAYMENT OF PAYROLL TO BE CORRECTED IN AUGUST | 1 | $1,500.00 | `4080720231763367585` |

(28 distinct groups total)

### Telecom

| form | line | normalized description | rows | dollars | example sub_id |
| --- | --- | --- | ---: | ---: | --- |
| F13 | F132 | (empty) | 3 | $1,550,000.00 | `4092420211371961726` |
| F3X | 17 | RECOUNT LEGAL FUND CONTRIBUTION | 4 | $184,900.00 | `4010720251127211278` |
| F3X | SL1A | (empty) | 10 | $54,500.00 | `4012820251137387742` |
| F3X | 17 | (empty) | 7 | $21,944.06 | `4012120231719624222` |
| F3X | SL1A | REASSIGNED FUNDS SEE MEMO ENTRIES AND TEXT | 2 | $7,500.00 | `4020820231723403027` |

(34 distinct groups total)

## Banking cross-check

Against the failed run's own review CSV,
`.cache/industry-report/banking/industry_data-4abdea581b99cec1.json.pending-42976.receipt-review.csv`:

The CSV was written **2026-09-12 17:59**. `inputs/fec_receipt_rules.json`
was last modified **2026-09-13 03:42** - after that run - and the file is
gitignored, so the change carries no history. The raw row set is identical;
only the classification moved. Re-running **today's** `fec_receipt_role()`
over the CSV's own 2,070 rows decomposes the difference exactly:

| | rows | dollars |
| --- | ---: | ---: |
| refused by the 2026-09-12 run (the CSV) | 2070 | $20,683,413.29 |
| ...still refused under today's ruleset | 593 | $1,797,578.54 |
| ...now resolved by today's ruleset | 1477 | $18,885,834.75 |
| **this reproduction (independent, from the database)** | **593** | **$1,797,578.54** |

| consistency check | result |
| --- | :---: |
| 593 + 1477 = 2070 | OK |
| $1,797,578.54 + $18,885,834.75 = $20,683,413.29 | OK |
| reproduction row count == still-refused count | OK |
| reproduction dollars == still-refused dollars | OK |
| reproduction sub_id set == still-refused sub_id set | OK |
| reproduction is a subset of the CSV | OK |
| rows newly refused that the CSV did not have | 0 |

Where the 1,477 rows went (Sep-12 role -> today's role):

| Sep-12 role | today's role | rows |
| --- | --- | ---: |
| `unverified_other_receipt` | `other_receipt` | 1329 |
| `unverified_other_receipt` | `transfer_receipt` | 147 |
| `unverified_other_receipt` | `contribution` | 1 |

No row moved the other way: nothing that the 2026-09-12 run accepted is
refused today. The reproduction is therefore an exact match against the only
ground truth available - the failed run's own output - once the ruleset
change between the two dates is accounted for.

## What the refusals are made of

Two structural buckets account for most of the refused rows, and neither is
a description the owner can rule on as written.

**Rows with no description at all.** `receipt_type_full` and `memo_text` are
both empty, so the classifier has nothing but form+line to go on and falls
through to `unverified_*`.

| industry | refused | of which blank description | dollars (blank) |
| --- | ---: | ---: | ---: |
| Banking | 593 | 427 | $1,682,166.23 |
| Community Banks | 11 | 0 | $0.00 |
| Credit Arms | 17 | 3 | $501,505.00 |
| Credit Union | 4 | 1 | $2.08 |
| Crypto | 80 | 37 | $19,908,597.26 |
| Fintech | 94 | 7 | $4,493.68 |
| Property & Casualty Insurance | 53 | 3 | $5,171.42 |
| Telecom | 96 | 25 | $1,633,555.41 |

**Filing forms the ruleset does not cover.** `fec_receipt_rules.json` maps
line numbers for `F3`, `F3X`, `F3P` and `F4` only. A row on any other form
(or with a blank form) cannot match a line rule and lands on
`unverified_receipt_role` no matter what its line number is.

| industry | form | rows | dollars |
| --- | --- | ---: | ---: |
| Banking | `F13` | 1 | $1,000,000.00 |
| Credit Arms | `F13` | 1 | $500,000.00 |
| Fintech | `(blank)` | 2 | $4,000.00 |
| Telecom | `F13` | 3 | $1,550,000.00 |

## Method

Per industry, one `Rscript gate_census.R <db> <label> <slug> <out>` run that:

1. assigns the **global R variable** `MENTAT_INDUSTRY` before sourcing (it is
   not an environment variable; leaving it unset silently queries Crypto),
2. sources the same 14 modules the exporter sources, in the same order,
3. opens the database with `RSQLite::SQLITE_RO`,
4. calls `spending_raw_report_rows(connection, versioning_applied = TRUE)` -
   the `TRUE` skips `apply_amendment_versioning()`, the only writing step,
   exactly as the exporter does at line 208,
5. rebuilds `evidence_scope` from `contribution_cycle()` against
   `supported_cycles = c(2022, 2024, 2026)` (exporter lines 97, 133-137, 219),
6. applies the gate body from `collect.R:138` to `raw_rows[evidence_scope]`.

Every run printed its industry label, the SQL filter, and its loaded row
count; no run loaded zero rows.

Both refusal masks were computed independently and compared per industry:
the gate's own (`collect.R:138`, applied to the scoped subset) and the
exporter's review-CSV logic (lines 220-221, applied to the full table).
They agreed on every industry - see `masks_agree` in each `_receipt.csv`.

## Cross-check against the Python twin

Every DISTINCT classifier-input tuple across all 8 databases
(`filing_form`, `line_number`, `receipt_type_full`, `memo_text`,
`memo_code`, `memoed_subtotal`, `is_memo_leg`) was classified by both the
authoritative R `fec_receipt_role()` and `tools/pac_evidence.py`
`receipt_role()`.

| metric | value |
| --- | ---: |
| distinct tuples compared | 28,548 |
| role-string disagreements | 108 |
| **refuse/allow verdict disagreements** | **0** |

The only disagreement shape is ``contribution` -> `in_kind_contribution``.
`pac_evidence.py:89-90` carries an `in_kind_contribution` rule
(`IN KIND|NOT LIQUIDATED`) that `collect.R` has no counterpart for. Both
labels are *resolved*, so the refusal set is identical either way. Stated
as an observed fact about the two implementations, not a proposed change.

## Deviations and uncertainties

**D1 - Banking's database is not where the brief expected it, and the
`receipt-metadata-repair-20260910` set has no Banking entry at all.**
That directory holds 7 slugs: `community_banks`, `credit_arms`,
`credit_union`, `crypto`, `fintech`, `property_casualty_insurance`,
`telecom`. Banking was taken from
`.cache/report-repairs/banking-20260910/data/mentat.db`. This is not a guess:
its SHA-256 is
`4abdea581b99cec1674252ee098ab6afca57674bd8e90313e9f4156e88b2d991`, which is
the `database_sha256` recorded in
`.cache/industry-report/banking/manifest-4abdea581b99cec1.json` - so it is
provably the database behind `industry_data-4abdea581b99cec1.json` and its
`.pending-42976.receipt-review.csv`.

**D2 - the live exporter cannot load ANY of these 8 databases today.**
`report.R:2032` and `:2051` SELECT `contributor_street_1, contributor_street_2`
unconditionally; commit `d78cf0b8f` added them. All 16 tables (8 databases x
`contributions` + `corporate_giving`) lack both columns, so
`spending_raw_report_rows()` aborts with `no such column:
contributor_street_1` **before** the gate at line 225 is reached. Verified by
`PRAGMA table_info` on all 16 tables and by running the unmodified path once.

The census therefore overrides `spending_raw_report_rows()` with a verbatim
copy of `report.R:2011-2083` changed in exactly one way: the two street
columns are routed through the same tolerant `NULL AS <field>` projection
that `report.R:2018-2026` already applies to absent receipt metadata. Neither
column is read by `fec_receipt_role()`, `fec_receipt_countable()`,
`fec_receipt_role_unresolved()` or `mentat_memo_duplicate_plan()`; a
repo-wide grep shows the only consumer in this path is the exporter's own
`raw_export` projection at lines 545-546, which runs after the gate. The
refusal set is unaffected, and the Banking row-for-row match below confirms
it empirically.

**D3 - `MENTAT_CYCLE_FILTER` was deliberately left unset.** It would narrow
`supported_cycles`, and therefore `evidence_scope`, before the gate runs
(exporter lines 112-131). The census refuses to start if it is set, so these
are full-payload refusal sets. The Banking cross-check CSV spans 2022, 2024
and 2026, confirming the failed run was also unfiltered.

**D5 - the ruleset changed after the Banking run that produced the
cross-check CSV, and that change is invisible to git.**
`inputs/fec_receipt_rules.json` (version 4) has mtime 2026-09-13 03:42; the
cross-check CSV was written 2026-09-12 17:59. The file matches `*.json` in
`.gitignore`, so there is no history to diff and no way from this session to
recover the exact Sep-12 ruleset. The effect is measured rather than
assumed: re-classifying the CSV's own 2,070 rows with today's
`fec_receipt_role()` resolves 1,477 of them and leaves exactly the 593 this
census reports, with no row moving the other way (see the Banking
cross-check). Every count in this report is therefore the refusal set under
**today's** ruleset, which is what a run started now would produce. Anyone
comparing against an older receipt-review CSV should expect it to be larger.

**D4 - the industry labels are read from the databases, not derived from the
slugs.** `property_casualty_insurance` is the token for the label
`Property & Casualty Insurance` (`build_industry_report.ps1:54` maps
`[^A-Za-z0-9]+` to `_`), so the slug alone would not have produced a matching
SQL filter. Each database contains exactly one distinct `industry` value in
both tables.


## Follow-ups

### 1. D2 patch - tolerant street projection in `spending_raw_report_rows()`

`mentat/R/report.R` is byte-identical between the working tree and HEAD
(`git diff --stat HEAD -- mentat/R/report.R` is empty), so the patch is valid
against both. File: `gate_census/report_R_street_tolerant.patch`.

The change routes `contributor_street_1` / `contributor_street_2` through the
same `NULL AS <field>` tolerance `report.R:2018-2026` already applies to absent
receipt metadata. The shared body is lifted into `optional_projection(table,
fields)`; `receipt_projection()` now calls it with its existing field list
(identical output, no behaviour change) and `street_projection()` calls it with
the two street columns. Nothing else is touched.

```diff
--- a/mentat/R/report.R
+++ b/mentat/R/report.R
@@ -2015,21 +2015,33 @@
   }
   # Exports read immutable snapshots, including pre-migration databases. Missing
   # source metadata stays blank/unverified instead of inventing receipt roles.
-  receipt_projection <- function(table) {
-    fields <- c("receipt_type_full", "filing_form", "receipt_type", "line_number", "line_number_label",
-                "file_num", "report_year", "report_type",
-                "memo_code", "memoed_subtotal", "memo_text", "back_reference_transaction_id", "back_reference_schedule_name")
+  optional_projection <- function(table, fields) {
     present <- DBI::dbListFields(connection, table)
     paste0(paste(vapply(fields, function(field) {
       if (field %in% present) field else paste0("NULL AS ", field)
     }, character(1L)), collapse = ", "), ",")
   }
+  receipt_projection <- function(table) {
+    optional_projection(table, c(
+      "receipt_type_full", "filing_form", "receipt_type", "line_number", "line_number_label",
+      "file_num", "report_year", "report_type",
+      "memo_code", "memoed_subtotal", "memo_text", "back_reference_transaction_id", "back_reference_schedule_name"))
+  }
+  # contributor_street_1/2 arrived with the street-column migration. Snapshots
+  # taken before it do not carry the columns, and SELECTing them
+  # unconditionally aborts the whole export with "no such column" before any
+  # guard downstream can run. Give them the same tolerance the receipt
+  # metadata above already has: absent means blank, never a failed export.
+  street_projection <- function(table) {
+    optional_projection(table, c("contributor_street_1", "contributor_street_2"))
+  }
   people <- data.table::as.data.table(DBI::dbGetQuery(
     connection,
     paste(
       "SELECT contributor_name, committee_name, contribution_receipt_date,",
       "contribution_receipt_amount, contributor_city, contributor_state,",
-      "contributor_zip, contributor_employer, contributor_occupation, contributor_street_1, contributor_street_2, company, sub_id, matched_variant,",
+      "contributor_zip, contributor_employer, contributor_occupation,",
+      street_projection("contributions"), "company, sub_id, matched_variant,",
       "committee_id, recipient_committee_type, recipient_committee_designation,",
       "two_year_transaction_period, entity_type, is_entity_contributor,",
       receipt_projection("contributions"), "transaction_id, pdf_url,",
@@ -2048,7 +2060,8 @@
     paste(
       "SELECT contributor_name, committee_name, contribution_receipt_date,",
       "contribution_receipt_amount, contributor_city, contributor_state,",
-      "contributor_zip, contributor_employer, contributor_occupation, contributor_street_1, contributor_street_2, company, sub_id, matched_variant,",
+      "contributor_zip, contributor_employer, contributor_occupation,",
+      street_projection("corporate_giving"), "company, sub_id, matched_variant,",
       "committee_id, recipient_committee_type, recipient_committee_designation,",
       "cycle AS two_year_transaction_period, entity_type, is_entity_contributor,",
       receipt_projection("corporate_giving"), "transaction_id, pdf_url, '' AS conduit_committee_id,",
```

**`git apply --check`, run from `C:\Users\pgoff\Mentat` (check only, NOT applied):**

```
$ git apply --check -v gate_census/report_R_street_tolerant.patch
Checking patch mentat/R/report.R...
exit=0
```

**Proof 1 - the patched real loader, no census override.** A scratch copy of
the patched `report.R` was sourced in its normal slot among the 14 modules, so
`spending_raw_report_rows()` is report.R's own function, not the census
override. The script asserts this before loading
(`uses street_projection: TRUE`, `census override absent: TRUE`).

| measure | census (override) | patched real loader | match |
| --- | ---: | ---: | :---: |
| rows loaded | 14,839 | 14,839 | YES |
| rows in evidence scope | 14,801 | 14,801 | YES |
| rows refused | 80 | 80 | YES |
| dollars refused | $187,536,167.90 | $187,536,167.90 | YES |
| refused `sub_id` set | 80 | 80 | IDENTICAL |

On this pre-migration database both street columns arrive present and empty
(`non_blank=0`) rather than aborting the export - the whole point of the patch.

**Proof 2 - a database that HAS the street columns.** Such databases do exist,
but not under `mentat\.cache`: they are the S2 run-lane databases under
`C:\Users\pgoff\AppData\Local\Mentat\console\907694a30e934705b3a9436138efec3b\`
`runs\20260917T102814-56272\industries\credit-unions\`. That run is LIVE (it
started 10:28 today); it was opened read-only and not otherwise touched. Its
merged `data\mentat.db` is still empty; `fanout\lanes\lane-05\mentat.db` had
rows, so the proof ran against that.

| measure | result |
| --- | ---: |
| rows loaded | 250 |
| `contributor_street_1` non-blank | 250 |
| `contributor_street_2` non-blank | 3 |

The patched projection returns the **real** street values, not NULL. (The lane
held 249 rows a minute earlier and 250 at load time - the live run is still
writing. Its industry label is `Credit Unions`, plural, which is a different
label from the `Credit Union` used by the repair-cache census.)

### 2. The 4 Crypto rows in group `F3X` / blank line / empty description

$19,767,475.00 across 4 rows. All four are `entity_type = ORG` - Coinbase
entities - so no individual-contributor redaction applies. Full listing also in
`gate_census/crypto_blankline_four.csv`.

| # | sub_id | date | amount | entity | contributor | committee_id | committee |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| 1 | `4030420261386079642` | 2025-10-07 | $8,092,475.00 | ORG | COINBASE | C00835959 | FAIRSHAKE |
| 2 | `4030420261386079658` | 2025-07-13 | $6,000,000.00 | ORG | COINBASE COMMERCE (EXCHANGE) | C00835959 | FAIRSHAKE |
| 3 | `4030420261386079660` | 2025-07-10 | $5,175,000.00 | ORG | COINBASE COMMERCE (EXCHANGE) | C00835959 | FAIRSHAKE |
| 4 | `4062220261522023969` | 2026-04-10 | $500,000.00 | ORG | COINBASE GLOBAL INC. | C00504530 | CLF |

| # | receipt_type_full | memo_text | memo_code | filing_form | line_number | transaction_id | back_reference_transaction_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | (empty) | (empty) | (empty) | `F3X` | (empty) | `E966384FC6024738878E` | (empty) |
| 2 | (empty) | (empty) | (empty) | `F3X` | (empty) | `370D8DC9123B47ABA632` | (empty) |
| 3 | (empty) | (empty) | (empty) | `F3X` | (empty) | `876629BF651C491EAF3B` | (empty) |
| 4 | (empty) | (empty) | (empty) | `F3X` | (empty) | `SA17.621125` | (empty) |

All four carry an empty `receipt_type_full`, `memo_text`, `memo_code` and
`line_number`, and none is a memo leg (`is_memo_leg = 0`, no back reference).
With `filing_form = F3X` but no line number, no rule in
`fec_receipt_rules.json` can match, so each lands on `unverified_receipt_role`.
There is no description to rule on.

One observation of fact: row 4's `transaction_id` is `SA17.621125`, whose
`SA17` prefix is the Schedule A line-17 tag that `fec_receipt_role()` strips
when it reads `line_number` (`collect.R:55`). For that row the line number is
present in the transaction id while `line_number` itself is blank. Rows 1-3
carry opaque 20-character FAIRSHAKE transaction ids with no line information.

