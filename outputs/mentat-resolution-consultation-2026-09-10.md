# Resolving historical metadata and unique-dollar accounting

September 10, 2026. Work in progress; headline accounting choice pending consultation. No production report or original database changed.

Subsequent decision: the user approved original employee/corporate giving counted once, with PAC outgoing separately, and requested testing before adoption. The choice is resolved; [the initial test diff](C:/Users/pgoff/Mentat/outputs/mentat-original-giving-test-diff-2026-09-10.md) records the results and remaining evidence limits. The consultation discussion below preserves the proposal as presented.

## Evidence recovery completed so far

The seven pinned industry sources contain 1,266,109 accepted receipt rows missing a filing form or receipt line. Of those, 1,264,212 are individual-table rows that already have a receipt line. All missing-role rows have a filing number, across 13,061 distinct filings. These are raw accepted-row counts, not counts of verified contributions or dollars to add.

A bounded pilot retrieved 25 original filing headers, reading at most 8 KB per request rather than downloading entire transaction files. Twenty-three passed the supported FEC 8.4/8.5 parser. Two use 8.3 and remain unresolved; their bytes are preserved for a validated adapter. The recovered headers correspond to 430,649 stored rows across the seven sources, but have been applied only to the existing three private recovery copies below.

| Recovery copy | Missing forms filled across the pilot | Rows still missing form or receipt line |
|---|---:|---:|
| Fintech | 12,279 | 12,667 |
| Credit Union | 12,310 | 15,285 |
| Crypto | 1,769 | 4,521 |

One recovered Fintech corporate form still lacks its transaction line, so restored-form counts do not equal the reduction in unresolved-role counts. Financial amounts and original source hashes were preserved. Each update records the source ID, prior/new form, filing URL and header hash. This recovers form evidence only; it does not certify every other field or resolve intermediary relationships.

The parser follows the [FEC electronic filing specification](https://docquery.fec.gov/formatspecs/FEC_EFO_Format_Specifications.xlsx). Its change log leaves the relevant report fields unchanged from 8.4 to 8.5. Unsupported formats and conflicting committee/form identities remain review cases. Five offline tests cover supported forms, malformed input, cache reuse/corruption, unsupported-evidence preservation, identity conflicts, idempotence and preservation of financial facts.

## Amendment resolution

The current report test deliberately sums a $100 original and its $125 amendment to $225. That documents the historical receipt view; it is not the appropriate result for a unique-contribution view.

The proposed unique view would count $125 only when filing-chain and transaction evidence establish that it replaces the $100. Original/amended rows remain in the audit view, with a $100 reconciliation difference. A larger file number, shared amount or shared reporting year alone cannot establish replacement.

Use the header's original-report reference to establish report families, verify committee and coverage, and resolve the current filed version as of a stated cutoff. Match transaction identifiers within that family. If a receipt is removed by an amendment, require complete replacement-report evidence before treating its absence as a deletion. A missing employer-search result is insufficient. Ties, conflicting chains and unavailable replacement filings remain unresolved.

The FEC specification identifies the header's report ID as the original report reference and requires transaction IDs to remain unique for the life of the report and amendments. The [FECFile manual](https://www.fec.gov/documents/190/GettingStarted_FECFileManual_pac-party.pdf) also describes modifying, adding and deleting transactions in amendments. Existing heuristic amendment flags are useful review candidates, not independent proof for the new headline.

## Intermediary resolution and headline choice

The recommendation awaiting the user's decision is to count original employee/corporate giving once, while reporting PAC outgoing activity separately. A hypothetical employee-to-PAC $100 and PAC-to-candidate $100 would contribute $100 to the original-giving headline, with $100 also displayed in the separate PAC-spending view. Those views must not be added together.

An earmarked conduit transfer and discretionary spending from a pooled PAC require different treatment. For an earmark, recover evidence of original donor, intended recipient and the linked disclosure; preserve the intermediary as a route. The [FEC conduit example](https://www.fec.gov/help-candidates-and-committees/filing-reports/contributions-received-through-conduits/) shows that the dates of the contributor and conduit entries can differ. Therefore a blanket same-date rule is not appropriate for every cross-stage relationship.

For pooled PAC money, show actual outgoing activity but do not claim that a particular employee's or company's dollars funded a particular candidate without supporting evidence. Equal amounts and nearby dates are candidates for review, not proof of a path.

The alternative headline is money reaching final recipients. That answers a different question, requires a declared definition of final recipient, and cannot silently allocate pooled balances or spending to companies. Both views can be useful, but the headline must be selected before changing report accounting.

## Remaining work after consultation

Finish supported-format recovery across all pinned sources, validate an 8.3 adapter, and recover transaction-level metadata for corporate receipts and relationship cases. Build the filing-family/current-transaction evidence ledger and the conduit-versus-pooled-money ledger. Reconcile any unique-dollar view against the existing receipt view, retain unresolved counts and dollars, and validate additions and exclusions against original filings before replacing headline totals.

The live question is the headline's accounting basis. Evidence recovery is independent of that choice; no answer has been assumed.
