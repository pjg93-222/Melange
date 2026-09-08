# Name reconciliation and PAC spending evidence — September 8, 2026

We can document company → PAC receipts, PAC → PAC transfers, and PAC spending
supporting or opposing named candidates. Those connected records do **not**
establish which pooled donor dollars paid for a particular advertisement.
Mentat now presents the observed legs separately and leaves company-attributed
candidate dollars unresolved. A dated route is a possibility, not an allocation.

## Coinbase and Fairshake: a material correction

Fairshake is **C00835959**; Defend American Jobs is **C00836221**; Protect
Progress is **C00848440**. The evidence collector fetched complete, exact-count
API query results for all three committees in the 2024 and 2026 cycles, including
itemized Schedule A and B and regular-report Schedule E. It retained public
source URLs and response hashes. Complete queries do not prove that the FEC
has processed every filing or that the data agree with financial summaries.

| Coinbase corporate receipts at Fairshake | Previous Crypto report | Verified itemized contributions | Correction |
|---|---:|---:|---|
| 2023–2024 | $93,500,000.00 | $68,499,995.00 | Exclude a $25m exchange liquidation and a $5 disclosure-only memo |
| 2025–2026 | $41,294,213.87 | $33,092,475.00 | Exclude $8,201,738.87 in exchange liquidation proceeds |

These corrected amounts include in-kind contributions valued as reported. They
are not spendable-cash estimates. The $5 memo says it refers to a previously
disclosed unitemized contribution; it is preserved as evidence but does not
become a new itemized donation. Coinbase also has a separate $1.5m contribution
to Protect Progress in 2024; it is not a Fairshake receipt.

The June 3, 2024 $25m receipt names **Coinbase Commerce (Exchange)** and describes
USDC sold through Coinbase to an unknown purchaser. Its Form 3X line is **17,
Other Federal Receipts**, even though its transaction code is `10`. An alias
match and transaction code alone were therefore insufficient. The original
$24,999,995 USDC contribution was reported May 30 on line 11AI; counting the
sale again as a Coinbase donation counted the same funding twice. See the
[June filing](https://docquery.fec.gov/cgi-bin/fecimg/?202407209661447526) and
[original contribution](https://docquery.fec.gov/cgi-bin/fecimg/?202406209652010582).

FEC guidance distinguishes a contribution from a sale through an exchange to
an unknown purchaser. It also describes the memo identifying the original
donor. This is a general transaction-role problem, not a Coinbase-specific
exception. [FEC: liquidating bitcoins](https://www.fec.gov/help-candidates-and-committees/filing-reports/liquidating-bitcoins/)

The full fresh Fairshake snapshots contain $40,505,000 in Coinbase-named exchange
sale proceeds in 2024 and $19,376,738.87 in 2026. Those figures exceed the
overcount above because the older company dataset did not contain every sale.
They must not be added to the corporate contribution totals.

## What the downstream records establish

| 2024 recorded leg or activity | Amount | Meaning |
|---|---:|---|
| Fairshake → Defend American Jobs | $54,550,000.00 | Seven reported committee disbursements |
| Fairshake → Protect Progress | $31,700,000.00 | Seven reported committee disbursements |
| Defend American Jobs: support Bernie Moreno | $40,134,929.71 | The committee's regular-report independent expenditures |
| Protect Progress: support Elissa Slotkin | $10,046,680.00 | The committee's regular-report independent expenditures |
| Protect Progress: support Ruben Gallego | $10,039,655.00 | The committee's regular-report independent expenditures |
| Fairshake: oppose Katie Porter | $10,041,118.54 | Opposition against the named candidate |

The evidence view supplies filing links for every group, including the
[Moreno spending](https://docquery.fec.gov/cgi-bin/fecimg/?202409209684055093),
[Slotkin spending](https://docquery.fec.gov/cgi-bin/fecimg/?202409209684212707),
and [Fairshake transfers](https://docquery.fec.gov/cgi-bin/fecimg/?202409209684212667).
Different reported name spellings remain separate groups until reconciled.
The table does not add transfers to candidate spending or assign the spending
to Coinbase. An independent expenditure is separate from money contributed to
a candidate's campaign. [FEC: independent expenditures](https://www.fec.gov/help-candidates-and-committees/making-independent-expenditures/)

The older industry allocation conserved money arithmetically but allocated a
root's entire positive funding across observed activity and outgoing transfers.
It pooled corporate and personal money, ignored donation dates, omitted
operating expenses and retained cash, and did not use all-donor receipts as a
denominator. It is an industry activity allocation, not a donor cash model.

The December 20, 2024 Coinbase contribution is **$23m of bitcoin, not liquidated
at receipt**. It cannot explain advertising paid earlier in 2024. The new dated
route check blocks backwards-time cash paths and requires a documented
liquidation link before treating in-kind gifts as available cash. Cross-cycle
carryover is not inferred. [Original December filing](https://docquery.fec.gov/cgi-bin/fecimg/?202501319752374587)

Fairshake reported $64,244,197.94 in ending cash for 2024 and $112,988,184.58
through July 31, 2026. Forcing every donated dollar onto observed candidates
ignores those retained balances. These are the committee's reported balances,
not Coinbase's remaining funds. [Fairshake filings](https://www.fec.gov/data/committee/C00835959/)

## Name reconciliation findings

1. **Company association and transaction role are separate questions.** The
   existing matcher normalizes punctuation and legal suffixes, uses roster
   aliases and approved overrides, and accepts certain corporate qualifiers.
   Unverified trailing tokens go to review. Ambiguous single-word brands can
   use state/occupation rules. These are deterministic rules, not calibrated
   probabilities that a contribution belongs to a company.
2. **People remain company-scoped.** Name variants, ZIP/city, occupation and
   employer signals join person components. Known-executive or verified-employee
   labels can join an entire canonical-name group. Shared locations, common
   names and transitive joins can still over-merge people. Those heuristics were
   inspected, not revalidated against an independently labeled identity set or
   broadly retuned in this change. Personal donations must stay distinct from
   corporate funding even when the employer match is correct.
3. **A vendor is not a candidate.** The PAS2 enrichment used the payee/vendor
   name when the current-cycle candidate master lacked a match. Fairshake's
   record consequently displayed “TARGETED PLATFORM MEDIA” as a candidate.
   Missing candidate identities now have an explicit unresolved label.
4. **An ID can disagree with the name as filed.** Fairshake Schedule E reports
   Donald/Don Davis with ID `H2NC01149`; the FEC candidate endpoint registers that
   ID to Samuel Sykes Davis III. The fresh records total $2,260,606.00 for these
   two name groups. The older bulk-derived group totaled $2,253,478.00. Preserve
   the discrepancy; neither amount nor identity should be silently patched by
   a name-only guess. The app displays both names and the ID for review.
   [As-filed expenditure](https://docquery.fec.gov/cgi-bin/fecimg/?202409209684212669),
   [candidate register](https://www.fec.gov/data/candidate/H2NC01149/).

The evidence view has 127 committee/candidate-name/direction groups: 61 names
exactly match the register and 66 require name/ID review. **66 is not an error
count**: many differences are titles, initials or aliases. No fuzzy candidate
reassignment was made.

## Changes applied across the collection/reporting code

- Preserve filing form, receipt description, line, memo indicators, transaction
  references and source URLs in corporate records as well as individual records.
  API refreshes hydrate existing source IDs, including lost memo flags. Indexed
  sub-ID updates avoid scanning a whole contributions table for each page.
- Evaluate receipt roles after company matching. Exclude documented exchange
  liquidations, relevant other-receipt lines and previously disclosed asset
  memos from company contribution totals. Exchange/processor names with missing
  role evidence go to review. Raw evidence stays available.
- Preserve matched aliases and match reasons in the full export. Add **Funding
  Cohorts** to new workbooks and audit bundles, separating company, funding type,
  committee, receipt role, and first/last receipt dates. Industry estimates now
  explicitly disclose their timing, cash and personal/corporate pooling limits.
- Replace the vendor-name fallback with an unresolved candidate label. The
  evidence collector independently compares as-filed names with registered IDs.
- Filter transfer paths, funding cohorts, allocation arrays and other evidence
  together when selecting one cycle. Previously the cycle filter covered the
  main report rows but left these added audit arrays outside the filter.
- Provide a reusable PAC evidence collector with exact-count/cursor guards,
  bounded requests, encrypted-key loading, retry handling and hashed response
  caches. It collects each selected committee once for all donor comparisons,
  uses regular Schedule E separately from notices, and checks financial totals.
- Acknowledge prior UI notices using workbook-hash-bound review receipts; do not
  delete Data Quality facts or permit a hard failure to be dismissed.

## What is required before estimating company-to-candidate dollars

Build a dated ledger for every selected committee, including **all donors**,
opening balances, transfers, refunds, other expenses, liabilities and retained
funds. Reconcile it to filings; distinguish noncash contributions, asset sales
and value changes so economic events are not counted twice. Preserve donor
provenance through documented asset conversions and carryover across cycles.
Use confirmed IDs and dated alias relationships; retain unresolved identities.

Only then consider a declared assumption such as proportional mixing of the
available cash balance before each expenditure. Report it as an estimate, with
unresolved amounts and sensitivity to FIFO/other mixing assumptions. Where the
records do not identify an allocation, leave it unknown; arithmetic conservation
does not identify causation. Documented earmarks or segregated-account evidence
can sometimes support a stronger link, but ordinary Super PAC receipts do not
establish one. [FEC: earmarked contributions](https://www.fec.gov/updates/earmarked-contributions/)

## Verification and remaining coverage

All three 2024 regular-report IE totals reconcile exactly to the FEC financial
summaries: Fairshake $40,661,820.61; Defend American Jobs $57,809,173.64; Protect
Progress $34,535,912.31. Fairshake 2026 also reconciles at $13,296,611.79.

For 2026, Defend American Jobs' collected regular IE total is $29,426,414.52
versus $32,450,134.42 in its summary; Protect Progress is $22,739,518.35 versus
$25,248,603.35. Their collected IE dates stop June 29 and June 25, respectively,
while summaries run through July 31. Processing lag is possible, but it has not
been established as the cause. The app explicitly retains these gaps.

The corrected Crypto workbook removes 36 rows totaling $33,203,777.83 from
analysis while retaining their evidence: the four established Fairshake
corrections above plus 32 small Coinbase Exchange rows totaling $2,033.96 whose
role remains unverified. Those 32 rows are pending review, not proven bad gifts.
There are still 6,036 included legacy rows without enough filing-form/line
metadata to verify their receipt role. A new warning discloses that limitation.
The 23 source-ID hydration updates used a separate SQLite snapshot; originals
remain unchanged.

The Crypto workbook and consolidated workbook were rebuilt. The other eight
industry workbooks remain the previous independently audited editions; the
new generic guards and Funding Cohorts apply on their next build. Existing
industry conditional allocations should not be read as Coinbase cash traces.

Validation receipts and source hashes are retained alongside this audit. The
Crypto export has 34 sheets and 349,198 evaluated formulas with no formula or
integrity failures; independent workbook checks verify amounts, directions,
sorting and audit artifacts. Source records remain under
`mentat/.cache/pac-evidence/fairshake-20260908/` and the full corrected export is
bound to the workbook by its audit manifest.

Final validation: **85 Python tests passed**, alongside the R API, fanout,
receipt-role hydration, reporting, matching-rule and beneficiary helper checks.
Browser checks confirmed committee/cycle filtering, incoming transfers, the
retained 2026 coverage gap, readable amounts in the narrow app pane, ten report
links, and no browser console errors. The original notices were acknowledged;
the new legacy receipt-role warning remains visible in Crypto and the
consolidated workbook.

Published workbook SHA-256:

- Crypto: `3226c66cd22ae7434ef2497f661bb5f2d29de4118681e9e82f03fb0f1f7b8f63`
- Consolidated: `eaf1f6442b106d7269c741c40943752b6e2090e01300dfef8ce7a207239ef6b4`
- PAC source snapshot: `ffee8b261b28fe15cd93f1b5c30b74d493a0b6a955baa22bc0e4a9cfb2af43fa`
