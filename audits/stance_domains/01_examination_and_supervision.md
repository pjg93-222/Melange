# Domain 01 — Examination & Supervision

Status: In progress

## Current source population

- 674 archive rows before exclusions
- 70 collected bill/Congress combinations before exclusions
- 236 members represented before exclusions
- 63 sponsor rows, 216 original-cosponsor rows, and 395 ordinary-cosponsor rows before exclusions

After the current SMART and domain-routing corrections:

- 573 active rows
- 63 active bill/Congress combinations
- 56 sponsor rows, 195 original-cosponsor rows, and 322 ordinary-cosponsor rows
- 25 rows excluded across the two auto-repair bills
- 73 rows removed or held neutral across H.R.1030, H.R.4895, H.R.5502, and H.R.5746
- 3 H.R.8395 rows moved to Payments

## Confirmed wiring defect and correction

The old desk filter used title/summary phrases. Some rows for H.R.1707 and H.R.3664 contained only the short title `SMART Act`, so those rows escaped the phrase filter and could still influence legislative scoring.

The exclusion is now pinned to:

- H.R.3664, 117th Congress — Save Money on Auto Repair Transportation Act
- H.R.1707, 118th Congress — Save Money on Auto Repair Transportation Act

All rows for those two bill/Congress pairs are excluded regardless of short-title quality.

These financial/regulatory SMART bills remain included:

- S.2801, 117th Congress — SMART Act of 2022
- S.4264, 118th Congress — SMART Act of 2024
- H.R.4437, 119th Congress — Supervisory Modifications for Appropriate Risk-based Testing Act of 2025
- S.76, 119th Congress — Setting Manageable Analysis Requirements in Text Act of 2025

H.R.8395, Young Kim's Payments Access and Consumer Efficiency Act, was collected only under Examination & Supervision. Its primary purpose is payment access and payment-rail modernization, so it is now explicitly routed to Payments. The shadow rebuild gives Young Kim a +3.0 legislative score in Payments and changes her preview label from Opponent (-0.328) to Highly Persuadable (+0.284). The remaining gap is the separate social-media direction/join defect, which will be handled in Domain 05.

Four additional first-pass routing decisions are recorded in `bill_overrides.csv`:

- H.R.1030 and H.R.4895 move from Examination & Supervision to Payments with direction `0` pending a CU-direction decision. Their operative provisions concern digital-dollar wallets and FedAccounts, not financial-institution examinations.
- H.R.5502 is excluded because it governs verification of high-volume sellers on online marketplaces.
- H.R.5746 is excluded because it concerns voting access, elections, redistricting, and campaign finance.

## Outstanding domain review

The source still assigns several broad digital-asset, voting, cyber, privacy, and stablecoin bills to Examination & Supervision. These are visible in the topic workbook with their other assigned categories. They should be reviewed bill by bill before this domain is approved; no blanket deletion has been made.

Current label warning: 60 members are labeled Lean Skeptic in this domain and 59 of those scores are positive. That is a stance-label semantic issue, not negative legislative evidence, and remains open for the domain-by-domain label review.

## Next decisions

1. Approve or override the multi-topic digital-asset and stablecoin assignments.
2. Review all 56 remaining sponsor rows before reviewing ordinary cosponsors.
3. Decide whether positive scores may ever display as Lean Skeptic.
4. Re-run the stance producer and compare member-level label changes after the workbook lock is released.
