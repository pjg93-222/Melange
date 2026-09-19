# Automatic FEC cross-referencing

Implemented September 10, 2026. Scope: FEC political giving; lobbying is excluded.

Mentat now runs **Define → Collect → Identify → Connect → Count → Verify/report** automatically before report builds, including workbook cache hits. The console's **Cross-reference** view shows the process, its evidence, changes, funding categories, partisan denominators and remaining questions. [Open the local read-only preview](http://127.0.0.1:8811/#cross-reference).

## What happens automatically

1. Pin the company/date scope, database, accepted baseline and counting rules. Use receipt dates for giving cycles and preserve the original FEC query period separately.
2. Preserve complete FEC responses, query provenance and competing observations through collection and shard merging. Reuse indexed evidence; request missing filing headers and exact receipts within a shared, bounded request budget.
3. Classify the source and transaction. Keep employee giving, supported corporate treasury giving, unverified ownership and recipient-reported PAC activity distinct. Ambiguous company claims enter review.
4. Connect records only with compatible filing, amendment, memo or intermediary evidence. Multiple search results with the same FEC source ID produce one decision while all search claims remain saved. Equal amounts alone never prove duplication.
5. Compute the provisional original-giving view and separate PAC activity. Retain meaningful partisan views with their dollar denominators and classification coverage.
6. Reconcile every signed change in cents, verify source preservation and evidence hashes, save a versioned ledger, and expose unresolved questions with links to FEC filings.

## Fintech test

| Measure | Result |
|---|---:|
| Companies / cycles | 10 / 2022, 2024, 2026 |
| Original stored observations | 86,662 |
| Distinct FEC source IDs | 86,270 |
| Previous accepted receipt total | $9,803,891.31 |
| Provisional original-giving candidate amount | $9,089,743.52 |
| Explained net change | −$714,147.79 |
| Changed accounting decisions | 110 |
| Evidence-backed relationship links | 4 |
| Records with unresolved questions | 35,106 |

The candidate amount includes $8,506,671.08 of employee-attributed receipts and $583,072.44 of unverified funding attribution. Zero supported corporate treasury or observed PAC amounts in this view do **not** establish zero real-world giving or spending. No amount in this historical test has yet satisfied the complete-filing, origin and route evidence requirements for the strictly supported unique-dollar subtotal.

A bounded live test made 12 public FEC requests in a 68-second run: nine exact receipts and one filing header were recovered; two unavailable or invalid headers remained unresolved. Saved-evidence replay produced identical totals, accounting decisions, links and review records. Source database hashes remained unchanged. The run ledger preserves used and conflicting evidence documents, rule snapshots and source observations.

Independent inspection of the 20 largest reductions and all four links found no incorrect exclusion in that bounded sample. Examples: Stripe's $190,000 return of an erroneous debit and $128,262.88 processing-fee refund were excluded; Chime's $75,000 special-account contribution remained provisionally included. A later SoFi $6,600 redesignation disclosure remains unresolved, so the related gift is not certified unique.

## What this establishes—and what remains

Targeted Python accounting, runner, evidence, merge and application tests passed, along with R collection/report tests, 6,035 workbook formula checks, and desktop/mobile browser checks. Tests cover source loss, offsetting financial mutations, ambiguous claims, false duplicates, conflicting metadata, accounting stages, signed percentages, evidence tampering, recovery limits and reproducibility.

The automated workflow is operational. Historical coverage, complete filing inventories, dated ownership, complete intermediary routes and Schedule B spending/refund coverage still require evidence. The system preserves these limitations instead of interpreting missing evidence as zero. Existing workbooks retain their receipt accounting basis and were not overwritten by this test.

**99.9% accuracy remains an independently measured target.** Neither processed-record counts nor agreement with OpenSecrets establishes that claim. No fresh OpenSecrets benchmark was verified in this implementation pass.

See [the methodology](../mentat/METHODOLOGY.md) and [operating instructions](../mentat/README.md) for the accounting rules, inputs and command options. Full run artifacts are under `mentat/state/cross-reference/`; `latest.json` identifies the latest run.
