# Original-giving accounting trial — September 10, 2026

Status: **initial test with partial evidence, not production totals**. The approved accounting basis is original employee and corporate giving counted once, with PAC outgoing activity separate. Existing reports, baselines and source databases were not changed.

The comparison uses the same stored 2021–2022, 2023–2024 and incomplete 2025–2026 snapshots as the earlier working totals. Header metadata recovery produced no change to those working sums. Historical company, tier and partisan classifications are held fixed so this test isolates accounting changes. No lobbying is included.

## Before/after with supported test adjustments

| Industry | Previous provisional total | Trial provisional total | Difference |
|---|---:|---:|---:|
| Fintech | $9,631,991.31 | $9,630,491.31 | -$1,500.00 |
| Credit Union | $1,422,005.65 | $1,422,005.65 | $0.00 |
| Crypto | $224,957,733.17 | $224,941,633.17 | -$16,100.00 |

The test changes six counted records: $2,500 of superseded amendment representations, $14,100 of duplicate conduit/destination representations, and $1,000 moved to the separate PAC activity view. The underlying original contributions remain. This is a supported adjustment for the tested cases, not an estimate of all remaining overcounting.

## Record-level changes

| Company | Cycle | Reduction in headline | Reason | Removed representation → retained representation |
|---|---|---:|---|---|
| Coinbase | 2023–2024 | $1,000.00 | Same transaction in an explicit amendment family | 4061220231749182347 → 4080720231763418299 |
| Coinbase | 2025–2026 | $1,000.00 | Coinbase Innovation PAC payment; separate PAC activity | 4041720251185269173 → Separate PAC activity record |
| Coinbase | 2023–2024 | $8,300.00 | Reciprocal FEC earmark evidence; count original gift once | 4021420241824762368 → 4022920241862249350 |
| Coinbase | 2021–2022 | $5,800.00 | Reciprocal FEC earmark evidence; count original gift once | 4110720221605884343 → 4011720231699665737 |
| Chime | 2023–2024 | $500.00 | Same transaction in an explicit amendment family | 4061220231749180188 → 4080720231763416139 |
| SoFi | 2023–2024 | $1,000.00 | Same transaction in an explicit amendment family | 4061220231749190761 → 4080720231763426720 |

The amendment cases use original filing 1706672 and its explicitly identified amendment 1716822, plus the same transaction IDs and independently recovered FEC transaction facts. They remove $500 for Chime, $1,000 for SoFi and $1,000 for Coinbase. The trial selects the later representation within this observed filing family; it does not claim that every subsequently filed amendment has been collected.

The routing cases are Coinbase employees’ $8,300 contribution earmarked through WinRed to Tim Scott Victory Fund and $5,800 earmarked through WinRed to McHenry for Congress. Each has reciprocal routing descriptions, the named destination committee ID, matching donor/date/amount/ZIP and a unique matching counterpart in the tested source. A separate same-day, same-amount $5,800 gift to Lummis Victory Committee remains because its recipient is different.

The $1,000 Coinbase item identifies contributor committee C00804179 (Coinbase Innovation PAC) in the FEC response. It is retained as **recipient-reported PAC giving**, outside employee/corporate original giving. This one observed record is not the PAC’s complete outgoing-spending total.

## What the test deliberately leaves unresolved

Sixteen repeated-transaction-ID groups across 22 filings were examined. Only three groups establish the tested amendment replacement. Other groups include memos and disclosures in different report families; repeated IDs alone do not justify deleting them. Twenty-one filing headers passed the supported parser; one uses an unsupported older format. Exact FEC API evidence was recovered for 49 distinct source IDs across the amendment, PAC and routing examples.

Four additional routing pairs have an explicit destination on the conduit record, but the recipient entry says to see the supporting conduit disclosure. They remain unchanged in this automated trial: $3,300 for a Credit Union case and $70,000 across three Fintech cases. A referenced filed row was recovered for the Credit Union case, but its organization-name mapping still needs a general validated rule. A further $6,600 Fintech route has multiple candidate recipient representations and remains ambiguous. These are review amounts, not asserted duplicate dollars or bounds.

| Industry | Dollars remaining without verified form/line evidence in this trial |
|---|---:|
| Fintech | $8,163,012.13 |
| Credit Union | $1,096,297.92 |
| Crypto | $175,456,062.98 |

These dollars remain included provisionally. This measures receipt-role evidence gaps only; it does not measure every unresolved amendment, route, refund or company-attribution question. Completing form metadata does not establish unique dollars.

## Test safeguards

Seven offline tests passed: corrected amendment amount; repeated IDs in unrelated reports; reciprocal route evidence and ambiguous equal-amount candidates; a same-amount gift to another recipient; employee-to-PAC inflow separated from PAC outgoing; unresolved/signed amounts preserved; and input-order/identity checks. The real-data run reconciles every changed cent and company sum.

Original-giving trial code is isolated in `mentat/tools/original_giving_experiment.py` and is not wired into report generation. It consumes existing receipt eligibility plus supplied FEC evidence. Similarity creates review candidates, not exclusions. Each industry is evaluated separately because a raw FEC row can occur in multiple industry query warehouses.

## Interpretation

The accounting basis works for the tested cases and produces traceable changes. This test does **not** justify a wholesale reduction of earmarked or memo receipts, a completed unique-dollar headline, or a complete PAC-spending claim. Broader adoption needs the remaining relationship evidence and an explicit current-filing cutoff.

## Primary evidence

- [Original report 1706672](https://docquery.fec.gov/dcdev/posted/1706672.fec) and [amendment 1716822](https://docquery.fec.gov/dcdev/posted/1716822.fec).
- [FEC conduit reporting guidance](https://www.fec.gov/help-candidates-and-committees/filing-reports/contributions-received-through-conduits/) and [electronic filing specification](https://docquery.fec.gov/formatspecs/FEC_EFO_Format_Specifications.xlsx).
- [Coinbase, source 4041720251185269173, source url](https://docquery.fec.gov/cgi-bin/fecimg/?202504149755320120).
- [Coinbase, source 4021420241824762368, origin url](https://docquery.fec.gov/cgi-bin/fecimg/?202401319602586469).
- [Coinbase, source 4021420241824762368, destination url](https://docquery.fec.gov/cgi-bin/fecimg/?202401319619448670).
- [Coinbase, source 4110720221605884343, origin url](https://docquery.fec.gov/cgi-bin/fecimg/?202212159568167614).
- [Coinbase, source 4110720221605884343, destination url](https://docquery.fec.gov/cgi-bin/fecimg/?202210159532913295).
