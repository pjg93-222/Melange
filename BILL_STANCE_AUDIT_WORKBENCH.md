# Bill and Stance Audit Workbench

This is the operating guide for reviewing the 18 stance domains one at a time. It keeps three questions separate:

1. Was the bill collected and assigned to the correct topic?
2. Was the member's role and the bill's credit-union direction scored correctly?
3. Did that evidence produce a defensible category label and overall Champion result?

## Interactive console

Launch `bill_audit_terminal.ps1`, or run:

```powershell
python -u fec\bill_audit_console.py
```

Useful commands:

```text
topics
topic 1
sponsored 1
member Young Kim
bill H.R.1707
override H.R.1181 119 "Data Privacy & Cyber" +1 include "Barr original cosponsor"
manual "Andy Barr" original H.R.1181 119 "Data Privacy & Cyber" +1 "Protecting Privacy in Purchases Act"
overrides
rebuild
```

`override` writes `bill_overrides.csv`. An explicit override can change a bill's category, direction, or include/exclude state for one Congress. `rebuild` regenerates `archive_leg.json`, category stances, the Excel overall tier, and the member desk.

## Domain order

1. Examination & Supervision
2. CU Capital Requirements
3. NCUA Budget & Insurance
4. Interchange
5. Payments
6. Technology & Emerging
7. Fraud Prevention
8. Data Privacy & Cyber
9. Charter Modernization
10. Defense CU Issues
11. Field of Membership
12. CU Tax Status
13. CDFI Fund
14. CFPB
15. Credit Card Mandates
16. TCPA
17. Member Business Lending
18. Mortgage & Housing

## Source documents

| Source | Role in the audit |
|---|---|
| `congress_bills_archive_20260624_115822.xlsx` | All collected bill/member/role rows and keyword topic assignments |
| `Moneyball Main Version - Blended.xlsx` | Sponsor/original/cosponsor interaction sheets and the media-score view |
| `archive_leg.json` | Signed, role-weighted legislative contribution by member and topic |
| `category_stance.json` | Current label, numeric score, and say-do gate result |
| `bill_directions.csv` | Existing per-bill direction registry |
| `bill_overrides.csv` | Explicit audit decisions that supersede defaults |
| `manual_bill_evidence.csv` | Missing sponsor/original-cosponsor evidence that the archive collector did not capture |
| `tweet_stance_final.csv` and `press_stance_final.csv` | Production social and press classification sidecars |
| `member_desk_bundle.json` | Exact evidence and labels sent to the member desk |
| `outputs/019f61b6-8906-7eb1-b5f2-517f522e4afe/topic_csv/` | Eighteen editable domain extracts |
| `outputs/019f61b6-8906-7eb1-b5f2-517f522e4afe/Moneyball_Bill_Stance_Audit_Workbench.xlsx` | Human review workbook with one sheet per domain |

## Production routing rules

- Sponsor rows receive weight 3, original cosponsor rows weight 2, and ordinary cosponsor rows weight 1.
- Sponsor and original-cosponsor evidence can satisfy the say-do Champion corroboration gate. Ordinary cosponsorship remains visible and scored but does not independently prove a Champion cell.
- Broad NDAA records are restored to the member desk and sponsorship corroboration path.
- Auto-repair SMART bills H.R.3664 (117th Congress) and H.R.1707 (118th Congress) are excluded by bill number and Congress, even when a source row contains only the ambiguous title `SMART Act`.
- Financial/regulatory SMART Acts remain included.
- Shared false-positive exclusions now apply consistently to legislative scoring, Champion corroboration, and the member desk.
- `build_archive_legislative.py` now runs immediately before `per_category_stance.py` in the canonical pipeline.
- `Credit Union Tax Status` is normalized to the canonical `CU Tax Status` domain.
- H.R.8395, sponsored by Young Kim, is routed to Payments rather than Examination & Supervision.
- Manual sponsor/original-cosponsor rows feed the legislative score, Champion corroboration gate, and member desk.

## Review rule

Do not approve a domain from its aggregate label distribution alone. Review sponsored and original-cosponsor bills first, then inspect negative directions, exclusions, cross-topic assignments, positive-score skeptic labels, and say-do caps.
