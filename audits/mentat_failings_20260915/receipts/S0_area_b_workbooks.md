# S0 receipt — Area B workbook layouts and payload street check (2026-09-16)

Read-only. Workbooks opened with `openpyxl.load_workbook(read_only=True, data_only=True)`;
SQLite files copied to temp and opened with `?mode=ro`. Scripts:
`C:\Users\pgoff\AppData\Local\Temp\claude\mentat_s0_scratch\s0_verify_b.py` (Part A)
and `s0_verify_b2.py` (Part 0 + Part B). Full raw stdout is in the S0 session
transcript; this receipt keeps the decisive lines.

## Part A — plain cycle sheets, all eight published workbooks

Directory: `C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files`.
Every cycle sheet has its title on row 1, a note on row 2, `Source DB SHA-256: …`
on row 3, and its header on **row 4**. Data begins on row 5.

| Workbook | Bytes | Cycle sheet rows (2021-22 / 2023-24 / 2025-26) | Header cols | City/State/ZIP/Employer/Occupation |
| --- | --- | --- | --- | --- |
| Banking | 39,994,686 | 5963 / 6229 / 4684 | 12 | **absent** |
| Community Banks | 4,682,775 | 1348 / 1827 / 803 | 35 | present |
| Credit Arms | 18,648,829 | 18640 / 21777 / 15243 | 18 | **absent** |
| Credit Union | 15,113,389 | 7653 / 14766 / 5112 | 35 | present |
| Crypto | 5,788,519 | 1067 / 3387 / 1863 | 35 | present |
| Fintech | 14,211,321 | 7114 / 12728 / 5078 | 35 | present |
| Property & Casualty Insurance | 22,781,912 | 12534 / 19830 / 9831 | 18 | **absent** |
| Telecom | 28,459,430 | 4816 / 5010 / 4067 | 12 | **absent** |

Row-1 titles (28-char truncation as printed): `2021-2022 Banking Formula Fa`,
`2021-2022 Telecom Formula Fa`, `2021-2022 Credit Arms Formul`,
`2021-2022 Property & Casualt`; versus `2021-2022 Crypto Contributio`,
`2021-2022 Community Banks Co`, `2021-2022 Credit Union Contr`,
`2021-2022 Fintech Contributi`. Row-2 for the aggregate layout begins
`Exact accepted transactions`; for the per-contribution layout
`Contribution-date cycle. Ana`.

12-column header (Banking, Telecom):
`Fact Type, Company, Employee Tier, Amount, Analysis Amount, Party, Recipient Category, Recipient Key, Gift Count, Include in Analysis, Person Key, Logic Check`

18-column header (Credit Arms, P&C):
`Fact ID, Cycle, Fact Type, Cycle Alignment, Company, Contributor, Employee Tier, Amount, Analysis Amount, Party, Recipient Category, Recipient, Committee ID, Recipient Key, Gift Count, Include in Analysis, Person Key, Logic Check`

35-column header (Crypto, Community Banks, Credit Union, Fintech):
`Source ID, Cycle, FEC Filing Cycle, Cycle Alignment, Company, Contributor, Employee Tier, Amount, Analysis Amount, Party, Recipient Category, Category Source, Party Source, Recipient, Committee ID, Recipient Key, Date, City, State, ZIP, Employer, Occupation, Record Type, Source Table, Company Match Status, Include in Analysis, Inclusion Reason, Person Key, Identity Basis, Memo Leg, Conduit Leg, Superseded Amendment, Duplicate Filing Version, Duplicate Memo, Logic Check`

Representative aggregate row (Banking 2021-2022, r9):
`Master, Wells Fargo Bank NA, Employee, 1015474.3799999875, 1015474.3799999875, Other / Unclassified, Carey, '', 44721, Yes, '', OK`

Representative per-contribution row (Crypto 2021-2022, r5):
`4013020231721146431, 2021-2022, 2022, OK, Coinbase, CHOI, EMILIE, Chief, 208.33, 208.33, Other / Unclassified, Company PAC, company_pac:company_alias_an, '', COINBASE, INC. INNOVATION PA, C00804179, FEC:C00804179, 2022-12-24 00:00:00, OAKLAND, CA, 946074375, COINBASE, INC., COO, CONTRIBUTION, contributions, accepted, Yes, Included, …`

A first pass in this lane read `ws[1]` (row 1) instead of row 4 and reported
"no address fields" for every workbook including Crypto. That pass was
invalid and is superseded by this one.

## Part 0 — other entries in the report directory

`~$Credit Union Industry Spending Overview.xlsx` (165 B, 2026-09-14T17:21:51 — Excel lock file);
`bulk_rescue_overflow.csv` (192 B, 2026-09-15T15:40:34); `accuracy_report.md`,
`fixture_unmatched.csv`, `pipeline_only.csv` (2026-09-12); `production-readiness.json`
(2026-07-29); `Cross Reference Further Review - 2026-09-13.md` and
`… Complete - 2026-09-13.md`.

## Part B — `api_page_checkpoints` record keys, evidence run

Run `20260915T152258-18548`, `industries\credit-unions\fanout\lanes\lane-NN\mentat.db`.

| Lane | Rows | Sample unit_id | Records per page | Record keys |
| --- | --- | --- | --- | --- |
| 02 | 2 | `P1_employer:Boeing Employees Credit Union:2022:BECU` | 100 | 81 |
| 03 | 6 | `P1_employer:Navy Federal Credit Union:2022:NFCU` | 100 | 81 |
| 04 | 12 | `P1_employer:Pentagon Federal Credit Union:2022:PenFed` | 100 | 81 |
| 09 | 22 | `P1_employer:State Employees' Credit Union:2022:SECU::window::01` | 100 | 81 |

Envelope keys: `complete, count, is_count_exact, last_indexes, page_number, rows, rows_collected, source_request, source_response`.

Record keys (81, identical in every lane): `amendment_indicator, amendment_indicator_desc, back_reference_schedule_name, back_reference_transaction_id, candidate_first_name, candidate_id, candidate_last_name, candidate_middle_name, candidate_name, candidate_office, candidate_office_district, candidate_office_full, candidate_office_state, candidate_office_state_full, candidate_prefix, candidate_suffix, committee, committee_id, committee_name, conduit_committee_city, conduit_committee_id, conduit_committee_name, conduit_committee_state, conduit_committee_street1, conduit_committee_street2, conduit_committee_zip, contribution_receipt_amount, contribution_receipt_date, contributor, contributor_aggregate_ytd, contributor_city, contributor_employer, contributor_first_name, contributor_id, contributor_last_name, contributor_middle_name, contributor_name, contributor_occupation, contributor_prefix, contributor_state, contributor_street_1, contributor_street_2, contributor_suffix, contributor_zip, donor_committee_name, election_type, election_type_full, entity_type, entity_type_desc, fec_election_type_desc, fec_election_year, file_number, filing_form, image_number, increased_limit, is_individual, line_number, line_number_label, link_id, load_date, memo_code, memo_code_full, memo_text, memoed_subtotal, national_committee_nonfederal_account, original_sub_id, pdf_url, receipt_type, receipt_type_desc, receipt_type_full, recipient_committee_designation, recipient_committee_org_type, recipient_committee_type, report_type, report_year, schedule_type, schedule_type_full, sub_id, transaction_id, two_year_transaction_period, unused_contbr_id`

Sample values (house numbers redacted): lane 02 `contributor_street_1='### BRADNER PL S'`, city `SEATTLE`, zip `98144`;
lane 03 `'### GALLOWS RD'`, `ANNANDALE`, `220031755`; lane 04 `'### CALIBRE SPRINGS WAY NE'`, `ATLANTA`, `30342`;
lane 09 `'### ASHFORD WAY'`, `FREMONT`, `945365254`. `contributor_street_2` was `None` in every sample.

A first pass in this lane tested the envelope keys instead of a record inside
`rows[0]` and reported street "NOT PRESENT". That pass was invalid and is
superseded by this one.
