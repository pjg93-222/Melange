# Contribution analytics accounting receipt

The default chart basis is the **published included receipt view**. This preserves a known, source-bound baseline while removing chart-layer multiplication of totals and repeated summary views. It is not a claim that the historical receipt view measures unique original gifts.

The alternative **observed original giving** basis applies Mentat's existing evidence-aware accounting engine and remains provisional. **Supported original giving (gross subset)** is the positive supported amount backed by the engine's completeness evidence and certificates; it does not represent complete net giving after refunds or adjustments. Neither a zero supported subset nor a nonzero provisional value certifies a complete unique-dollar total. PAC activity and raw source observations are separately named views. These overlapping views must not be added together.

## Source and evidence binding

All eight datasets are discovered only from the configured authoritative report folder. The chain is the published workbook's printed source database hash, the matching industry payload manifest, the hashed payload, and its pinned source database. Where the original database path no longer exists, a preserved hydration receipt must identify the same original database hash and a concrete recovered database inside the internal cache. The recovered database is hashed and every published source ID is reconciled against its contributor, committee, date and amount. Every included receipt total is checked in integer cents, separately for each election cycle.

The API also checks the actual current workbook's cached `Total Giving` row for every cycle. This independent workbook guard rejects altered totals or duplicate total rows. Old `workbook_manifest_all_cycles.json` files are stale for six industries and are not used as authority for later published files. All eight current published workbooks match their pinned payload cycle totals exactly; see [published-workbook-reconciliation.json](published-workbook-reconciliation.json).

The seven recovered databases have later metadata enrichment, so their current file hashes legitimately differ from the first hydration receipts. A separate source guard verifies the **complete financial source universe** against the original-hash-pinned accepted snapshot: every source ID, contributor, committee, contribution date, cycle and integer-cent amount, including rejected and source-only observations. All seven comparisons show zero added, missing, financially changed or conflicting source IDs. This proof is independent of the narrower payload rows and the included receipt total. The original Banking database is checked directly against its published fingerprint. Both branches reject active WAL/journal writes and source changes during validation. The HTTP response carries the source proof token and rejects a database change between verification and query.

Telecom's compact payload explicitly preserves election cycle while omitting the date field. Its first build correctly stopped at the strict date guard. The adapter now permits that omission only when the pinned payload declares the compact schema and a full source-universe proof has passed before materialization. The actual source date must produce the exact payload cycle; amount, committee and contributor must still match. A present but blank, invalid or differing payload date remains an error. An independent audit checked all 506,017 distinct Telecom payload IDs against the accepted snapshot with zero identity, amount or cycle differences.

No source database or published workbook is changed. Indexed analytical caches are created under `mentat/state/contribution-analytics`; source verification receipts are cached separately under `mentat/state/contribution-source-proofs`. The map implementation keeps its own geographic reference cache separate from contribution facts.

Compatible saved decision ledgers must match the database, industry, all three cycles, full company roster, distinct source-ID count, complete accounting rule fingerprint set and ledger hash. Otherwise the current engine is run against the pinned source and existing validated evidence. The current engine fix intentionally invalidates older ledger rule fingerprints.

## Grain and counts

- One fact represents one physical FEC source ID. Repeated observations of that ID across queries are coalesced with the existing accepted-query priority and retain all company claims and metadata conflicts.
- Equal contributor/date/amount values do not establish duplicate gifts. No blanket memo or amendment deletion is applied.
- A canonical rejected attribution cannot be restored to a counted amount by conflicting metadata. The new regression specifically covers rejected copies with differing ZIPs.
- ZIP is the contribution's reported ZIP, preserved as text with a separate validated ZIP5. A donor's multi-ZIP history is never expanded into repeated copies of their full giving total.
- Distinct donor counts use known report person keys where available, otherwise reported name/state/ZIP identities. They are explicitly **distinct reported donor identities**, not certified distinct people. Total distinct counts are computed from facts, never by summing group distinct counts.
- Observation counts, averages and related measures in an included basis exclude zero/noncounted representations. The raw basis and drill-through with excluded records expose those source representations.
- Negative adjustments stay signed. A negative receipt is not automatically asserted to be an actual refund.

## API and cache contract

`catalog`, `query` and `records` serve typed fields; monetary values and monetary filter thresholds use integer cents. Queries allow multiple dimensions, dimension and row-money filters, independent aggregate filters, count/distinct count, net/positive/negative amounts, average, median, minimum and maximum. Query pages support up to 100,000 groups and explicit offset/has-more metadata. Drill-through pages support up to 5,000 source observations with contributor, source ID, raw ZIP, basis amounts and accounting reasons/evidence IDs.

Aggregate filters operate after grouping. Returned totals and basis comparisons describe the row-filtered population before aggregate filtering; the reconciliation object separately identifies the retained group amount. This distinction is returned as a visible notice. Geography uses the same fact population, including a visible unmapped amount.

The cache binds source, accounting code, selected evidence epoch and index token. Editing loaded accounting code requires an app restart; an old process cannot stamp old Python objects as new rules. Builds detect source/evidence changes before publication. SQLite shared-memory read locks and empty WAL creation do not count as new evidence; a nonempty WAL does. Failed builds allow explicit retry and cooldown recovery while retaining source fingerprint checks. Large payloads and canonical source observations are staged in SQLite to bound memory.

The compact-schema adapter does not alter facts that already passed the stricter present-date comparison. The seven completed indexes were copied under new cache tokens with an explicit compatibility receipt, preserving the original indexes and original build provenance. Every complete fact row has the same SHA-256 before and after the metadata-only copy; source/workbook proofs, all other accounting rule hashes, cycle totals and SQLite integrity were rechecked. See [cache-migration/receipt.json](cache-migration/receipt.json). Telecom alone required another build.

## Validation

The focused contribution, legacy worksheet, accounting engine and runner suite passed **86 tests**, including money/ZIP conservation, signed adjustments, distinct counts, pagination, aggregate filters, source claim priority, preserved conflicts, rejected conflict exclusion, evidence identity validation, invalid dates, compact-schema preconditions and cache epoch behavior. The final HTTP integration separately passed 13 tests, and the current-workbook/source guards passed 18 tests. The optimized read-only query planner passed 10 focused tests covering more than 100 comparisons with the reference implementation.

The live, authoritative per-industry validation is recorded in [data-validation.json](data-validation.json), including expected and actual amounts for each cycle, workbook/database/payload hashes, index token, ZIP grouping conservation, coverage and elapsed time. The script uses the production API functions and the exact configured reports; it does not substitute historical workbooks.

All eight datasets passed exact integer-cent reconciliation for each of the three election cycles and contribution-level ZIP grouping conservation. The included receipt totals are:

| Dataset | Included receipts |
| --- | ---: |
| Banking | $54,762,844.05 |
| Community Banks | $863,505.98 |
| Credit Arms | $23,932,445.25 |
| Credit Union | $1,422,005.65 |
| Crypto | $249,949,483.17 |
| Fintech | $9,803,891.31 |
| Property & Casualty Insurance | $16,687,365.59 |
| Telecom | $37,698,121.09 |

These are separate dataset receipt views, not a combined unique-giving total. The supplemental [source-only-observations.json](source-only-observations.json) also verifies every company-by-cycle subtotal against the pinned payload. Crypto's raw company labels use the existing `R/ingest.R` display register; the receipt preserves both those raw-label differences and the exact normalized reconciliation. Source-only observations remain in the index for audit and raw/unresolved views, and contribute zero observed-original or PAC dollars in all eight datasets.

The initial Banking build plus reference-query validation took 1,324.36 seconds; the successful Telecom build plus optimized validation took 614.14 seconds. These cold checks include constructing and verifying the index. After indexing, the final live Banking API check took 13.713 seconds. Index reuse avoids repeating the cold accounting work.
