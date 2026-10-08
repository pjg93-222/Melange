# Employment acquisition and adjudication priority queue

Status: `PASS` (independent verification)

This offline stage ranks all 25,340 sealed LDA source identities without acquiring new data or promoting any identity, employment fact, date, or lifetime chronology. It preserves every explicit critical-path gap, the complete provider-coverage object, and evidence pointers bound to the validated input ledgers and receipts. Education remains nonblocking.

## Priority buckets and next actions

| Rank | Bucket | People | Next action |
|---:|---|---:|---|
| 0 | `P0_NO_EMPLOYMENT_CANDIDATE` | 11,720 | Acquire a dated employer-or-office and title from an official payroll, employer biography, or archived profile. Retain the result as `REVIEW_REQUIRED`. |
| 1 | `P1_DATED_FORMER_POSITION_MISSING` | 4,932 | Resolve dates for the known employer-or-office and title. Prefer bounded source observations and never infer continuity between observations. |
| 2 | `P2_BOUNDED_INTERVAL_MISSING` | 1,784 | Acquire start and end bounds for each dated position while retaining date uncertainty and report-period-only semantics. |
| 3 | `P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION` | 6,904 | Adjudicate identity using independent anchors, reconcile provider overlaps, and enumerate remaining chronology gaps before any canonical promotion. |

Provider coverage is intentionally a secondary rank within each evidence-gap bucket. There are 11,720 people with no employment provider, 7,595 with one employment provider, and 6,025 with multiple provider candidates requiring overlap reconciliation.

## Receipts

- Primary/twin queue payload SHA-256: `59b24e1bc6c7af1b68b99203d831c43e2df97fac04d676161e45a9042b4e8ea2`
- Primary/twin queue receipt SHA-256: `ea8748acc208fc74dc33b5f55b777eb03be082e79351c94af94c44633bd7adf1`
- Independent verification receipt SHA-256: `62165b4b329ef56ef260dca5997994d2dff09b6af1d270f9055048b431f3a256`
- Rows / unique LDA source IDs: 25,340 / 25,340
- Canonical identity/employment promotions: 0 / 0
- Network acquisition performed: false
- Structured-artifact credential scan: negative
