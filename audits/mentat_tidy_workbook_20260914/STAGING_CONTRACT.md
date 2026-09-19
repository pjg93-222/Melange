# Tidy staging contract (schema_version = "tidy-1")

Shared contract between the R staging writer (`R/tidy_stage.R`, drafted by Lane B) and the Python
workbook writer (`tools/build_tidy_workbook.py`, built by Lane A). Both lanes implement THIS file.
Any change to a table or column is made here first, by the coordinator, and both lanes re-read it.

## 1. Store

- One SQLite file per export: `<stage-dir>/tidy-<hash16>.sqlite` (written as `<name>.pending-<pid>` then renamed).
- One table per sheet, snake_case names below. No views, no triggers, no indexes required.
- Column storage: TEXT for everything that is not a number; REAL for money; INTEGER for counts and flags.
- Dates: ISO `YYYY-MM-DD` TEXT (never REAL, never datetime). The Python writer converts to Excel dates.
- Flags: INTEGER 0/1 (never "Yes"/"No" in the store). The Python writer converts to Excel booleans.
- Missing: SQL NULL (never "", never 0 as a sentinel). Empty strings from R are written as NULL.
- Identifiers (`source_id`, `committee_id`, `candidate_id`, `person_key`, `transaction_id`, ZIPs,
  `district`, `line_number`): TEXT always. `source_id` is the FEC `sub_id`, 19 digits.
- Money: REAL dollars with cents (e.g. 2500.00). Reconciliation compares rounded to cents.
- Row order in the store is irrelevant; the writer sorts by the key columns listed per table.

## 2. Tables

Column order below is the sheet column order. `key` marks the unique-row key. Types: T text, R money,
I integer, D date, B flag, ID text-identifier.

### 2.1 metadata (key/value; NOT a sheet by itself - the writer renders it into `About`)
| key | value |
|---|---|
| schema_version | tidy-1 |
| industry | Credit Union |
| industry_slug | credit_union |
| cycle_label | (empty for all cycles; "2025-2026" for a -CycleLabel build) |
| supported_cycles | JSON array of end years, e.g. [2022,2024,2026] |
| cycle_labels | JSON array, e.g. ["2021-2022","2023-2024","2025-2026"] |
| database_path | path of the mentat.db the export read |
| database_sha256 | 64 hex (R writes it if known, else NULL; the orchestrator passes it to the writer as --database-sha256) |
| generated_at | ISO 8601 UTC datetime of the export |
| exporter_version | git describe or file sha of the exporter, if known |
| expected_cycle_totals | JSON object {cycle_label: dollars} from the exporter's expected_cycle_totals |
| accounting_note | one sentence: what Analysis Amount counts and what it excludes |
| blank_columns | JSON array of sheet headers that are entirely NULL for this industry (writer may recompute) |

### 2.2 contributions  (key: source_id)
| column | type | sheet header | source (R) |
|---|---|---|---|
| source_id | ID | Source ID | raw_export$source_id (sub_id) |
| transaction_id | ID | Transaction ID | raw_export$transaction_id |
| back_reference_transaction_id | ID | Back Reference Transaction ID | raw_export$back_reference_transaction_id |
| cycle_label | T | Election Cycle | raw_export$cycle_label |
| cycle | I | Cycle End Year | raw_export$cycle |
| source_cycle | I | FEC Filing Cycle | raw_export$source_cycle |
| cycle_alignment | T | Cycle Alignment | raw_export$cycle_alignment |
| company | T | Company | raw_export$company |
| contributor | T | Contributor | raw_export$contributor |
| person_key | T | Person Key | raw_export$person_key (NULL for entity rows) |
| identity_basis | T | Identity Basis | raw_export$identity_basis |
| employee_tier | T | Contributor Tier | raw_export$employee_tier |
| employer | T | Employer | raw_export$employer |
| occupation | T | Occupation | raw_export$occupation |
| city | T | City | raw_export$city |
| state | T | State | raw_export$state |
| zip5 | ID | Contributor ZIP | substr(zipcode,1,5) when it matches ^[0-9]{5} else NULL (R/report.R:1885-1886 rule) |
| zipcode | ID | Contributor ZIP Raw | raw_export$zipcode |
| date | D | Date | raw_export$date |
| amount | R | Amount | raw_export$amount |
| analysis_amount | R | Analysis Amount | amount when include_in_analysis == "Yes" else 0 (exporter :572) |
| include_in_analysis | B | Include in Analysis | raw_export$include_in_analysis == "Yes" |
| inclusion_reason | T | Inclusion Reason | raw_export$inclusion_reason |
| company_match_status | T | Company Match Status | raw_export$company_match_status |
| company_match_reason | T | Company Match Reason | raw_export$company_match_reason |
| matched_alias | T | Matched Alias | raw_export$matched_alias |
| recipient | T | Recipient | raw_export$recipient |
| committee_id | ID | Committee ID | raw_export$committee_id |
| recipient_key | T | Recipient Key | raw_export$recipient_key |
| recipient_category | T | Recipient Category | raw_export$recipient_category |
| category_source | T | Category Source | raw_export$category_source |
| party | T | Recipient Party | raw_export$party |
| party_source | T | Party Source | raw_export$party_source |
| committee_type_code | T | Committee Type Code | raw_export$committee_type |
| committee_type | T | Committee Type | mentat_fec_code_label(committee_type, MENTAT_FEC_COMMITTEE_TYPE_LABELS) |
| committee_designation_code | T | Committee Designation Code | raw_export$committee_designation |
| committee_designation | T | Committee Designation | mentat_fec_code_label(designation, MENTAT_FEC_DESIGNATION_LABELS) |
| record_type | T | Record Type | raw_export$record_type |
| source_table | T | Source Table | raw_export$source_table |
| funding_source_type | T | Funding Source Type | raw_export$funding_source_type |
| funding_direction | T | Funding Direction | raw_export$funding_direction |
| receipt_role | T | Receipt Role | raw_export$receipt_role |
| receipt_type_full | T | Receipt Type | raw_export$receipt_type_full |
| filing_form | T | Filing Form | raw_export$filing_form |
| line_number | ID | Line Number | raw_export$line_number |
| memo_text | T | Memo Text | raw_export$memo_text |
| is_memo_leg | B | Memo Leg | raw_export$is_memo_leg |
| is_conduit_leg | B | Conduit Leg | raw_export$is_conduit_leg |
| superseded_by_amendment | B | Superseded Amendment | raw_export$superseded_by_amendment |
| duplicate_filing_version | B | Duplicate Filing Version | raw_export$duplicate_filing_version |
| duplicate_memo | B | Duplicate Memo | raw_export$duplicate_memo |
| duplicate_of_sub_id | ID | Duplicate Of Source ID | raw_export$duplicate_of_sub_id |
| duplicate_reason | T | Duplicate Reason | raw_export$duplicate_reason |
| recipient_state | T | Recipient State | raw_export$recipient_state (state destinations) |
| represented_state | T | Represented State | raw_export$represented_state |
| source_url | T | Source URL | raw_export$source_url |

Universe: `workbook_raw_export` rows (accepted company match, supported cycles) - included AND excluded.

### 2.3 giving_facts  (key: cycle_label, company, employee_tier, recipient_category, party)
| column | type | sheet header | derivation over contributions WHERE include_in_analysis = 1 |
|---|---|---|---|
| cycle_label | T | Election Cycle | group |
| cycle | I | Cycle End Year | group |
| company | T | Company | group |
| employee_tier | T | Contributor Tier | group |
| recipient_category | T | Recipient Category | group |
| party | T | Recipient Party | group |
| giving | R | Giving | SUM(analysis_amount) |
| gift_count | I | Gift Count | COUNT(*) |
| distinct_contributors | I | Distinct Contributors | COUNT(DISTINCT person_key) over non-NULL person_key |
| distinct_recipients | I | Distinct Recipients | COUNT(DISTINCT committee_id) |

### 2.4 recipient_facts  (key: cycle_label, company, committee_id, employee_tier)
| column | type | sheet header | source |
|---|---|---|---|
| cycle_label, cycle, company | as above | Election Cycle, Cycle End Year, Company | group |
| committee_id | ID | Committee ID | group |
| employee_tier | T | Contributor Tier | group |
| recipient | T | Recipient | committee name as in contributions (most frequent spelling) |
| recipient_category | T | Recipient Category | committees table |
| category_source | T | Category Source | committees table |
| party | T | Recipient Party | committees table |
| party_source | T | Party Source | committees table |
| committee_type_code, committee_type, committee_designation_code, committee_designation | T | as in 2.2 | committees table |
| sponsor_candidate_id | ID | Sponsor Candidate ID | the single linked candidate when sponsor_count = 1, else NULL |
| sponsor_candidate | T | Sponsor Candidate | candidates.candidate for that id |
| sponsor_office | T | Sponsor Office | candidates.office |
| sponsor_state | T | Sponsor State | candidates.state |
| sponsor_district | ID | Sponsor District | candidates.district |
| sponsor_count | I | Sponsor Count | committees.sponsor_count |
| connected_organization | T | Connected Organization | committees table |
| committee_relationship | T | Committee Relationship | committees table |
| ownership_status | T | Ownership Status | committees table |
| giving | R | Giving | SUM(analysis_amount) |
| gift_count | I | Gift Count | COUNT(*) |
| distinct_contributors | I | Distinct Contributors | COUNT(DISTINCT person_key) non-NULL |
| first_gift_date | D | First Gift Date | MIN(date) |
| last_gift_date | D | Last Gift Date | MAX(date) |
| fec_committee_url | T | FEC Committee URL | https://www.fec.gov/data/committee/<committee_id>/ |

### 2.5 contributor_facts  (key: cycle_label, company, person_key, party) - rows with NULL person_key are EXCLUDED
| column | type | sheet header | source |
|---|---|---|---|
| cycle_label, cycle, company | | Election Cycle, Cycle End Year, Company | group |
| person_key | T | Person Key | group |
| party | T | Recipient Party | group |
| contributor | T | Contributor | modal contributor spelling for the person in that cycle (ties: first alphabetically) |
| employee_tier | T | Contributor Tier | modal |
| identity_basis | T | Identity Basis | modal |
| city | T | City | modal |
| state | T | State | modal |
| zip5 | ID | Contributor ZIP | modal |
| employer | T | Employer | modal |
| occupation | T | Occupation | modal |
| distinct_addresses | I | Distinct Addresses | COUNT(DISTINCT city||state||zip5) for the person in that cycle (all parties) |
| giving | R | Giving | SUM(analysis_amount) |
| gift_count | I | Gift Count | COUNT(*) |

### 2.6 location_facts  (key: cycle_label, company, state, city, zip5)
| column | type | sheet header |
|---|---|---|
| cycle_label, cycle, company | | Election Cycle, Cycle End Year, Company |
| state | T | State |
| city | T | City |
| zip5 | ID | Contributor ZIP |
| giving | R | Giving |
| gift_count | I | Gift Count |
| distinct_contributors | I | Distinct Contributors |

### 2.7 committees  (key: committee_id, cycle_label)
| column | type | sheet header | source (R) |
|---|---|---|---|
| committee_id | ID | Committee ID | committee_map / contributions |
| cycle_label | T | Election Cycle | |
| cycle | I | Cycle End Year | |
| committee_name | T | Committee | committee_map$master_committee_name, else recipient spelling |
| committee_type_code, committee_type | T | Committee Type Code, Committee Type | master_committee_type + label |
| committee_designation_code, committee_designation | T | Committee Designation Code, Committee Designation | master_designation + label |
| party | T | Committee Party | D/R/Other bucket used by the export |
| party_affiliation | T | Party Affiliation | fec_committee_master raw code |
| committee_state | T | Committee State | fec_committee_master state |
| recipient_category | T | Recipient Category | export classification |
| category_source | T | Category Source | |
| party_source | T | Party Source | |
| connected_organization | T | Connected Organization | committee_map |
| ownership_status | T | Ownership Status | committee_map |
| committee_relationship | T | Committee Relationship | committee_map$relationship when single-valued, else "Multiple" |
| mapping_source | T | Mapping Source | committee_map when single-valued, else "Multiple" |
| sponsor_count | I | Sponsor Count | rows in committee_sponsors for the id/cycle |
| top_downstream_candidate_id | ID | Top Downstream Candidate ID | committee_map |
| top_downstream_candidate | T | Top Downstream Candidate | committee_map |
| top_downstream_activity | R | Top Downstream Activity | committee_map |
| fec_committee_url | T | FEC Committee URL | |

Universe: every committee_id that appears in contributions (any include flag) for that cycle.

### 2.8 committee_sponsors  (key: committee_id, candidate_id, cycle_label, link_source)
| column | type | sheet header | source |
|---|---|---|---|
| committee_id | ID | Committee ID | candidate_committee_links / leadership mappings |
| candidate_id | ID | Candidate ID | |
| cycle_label | T | Election Cycle | |
| cycle | I | Cycle End Year | |
| relationship | T | Relationship | link relationship label (e.g. Principal campaign committee, Leadership PAC sponsor) |
| link_source | T | Link Source | "FEC ccl" or "Leadership PAC roster" |
| candidate | T | Candidate | candidates.candidate |
| source_url | T | Source URL | |

Universe: committees present in 2.7.

### 2.9 candidates  (key: candidate_id)
| column | type | sheet header | source |
|---|---|---|---|
| candidate_id | ID | Candidate ID | candidate_master |
| candidate | T | Candidate | candidate_name |
| party | T | Candidate Party | candidate_party bucket |
| party_affiliation | T | Party Affiliation | raw |
| office_code | T | Office Code | office |
| office | T | Office | office_label |
| state | T | State | office_state |
| district | ID | District | district |
| incumbent_status | T | Incumbent Status | incumbent_challenger (decoded: Incumbent / Challenger / Open seat) |
| principal_committee_id | ID | Principal Committee ID | |
| fec_candidate_url | T | FEC Candidate URL | https://www.fec.gov/data/candidate/<id>/ |
| source_url | T | Source URL | |

Universe: every candidate_id referenced by committee_sponsors, downstream_activity, beneficiary_bridge or committees.top_downstream_candidate_id.

### 2.10 downstream_activity  (key: cycle_label, source_committee_id, candidate_id, candidate, activity_type, support_oppose, transaction_type)
AMENDED 2026-09-15 (Lane A finding D2): on the real Credit Union export the six-column key collides in 92 groups because
the exporter's frame carries candidate NAME variants under one candidate_id; adding `candidate` makes all 98,917 rows unique.
Same columns as the Overview's `Downstream Activity` sheet, renamed: cycle_label (Election Cycle), cycle (Cycle End Year),
source_committee (Source Committee), source_committee_id (Source Committee ID), source_recipient_category (Source Recipient Category),
candidate (Candidate), candidate_id (Candidate ID), candidate_party (Candidate Party), office, state, district,
activity_type (Activity Type), support_oppose (Support / Oppose), transaction_type (Transaction Type),
first_activity_date D (First Activity Date), last_activity_date D (Last Activity Date),
source_rows, included_rows, excluded_rows, superseded_rows, memo_rows, duplicate_rows I (Source Rows ... Duplicate Rows),
reported_amount, excluded_amount, net_included_amount R (Reported Amount, Excluded Amount, Net Included Amount),
fec_committee_url, fec_candidate_url, source_url T, transfer_records T (Transfer Records, JSON text).

### 2.11 beneficiary_bridge  (key: bridge_key)
Company-view rows only (`view == "Company"`). Columns: bridge_key T (Bridge Key; the exporter's reference key), cycle_label, cycle, company,
source_committee (Source Committee), source_committee_id (Source Committee ID), source_recipient_category, candidate, candidate_id,
candidate_party (Candidate Party), office, state, district, transaction_count I (Transaction Count),
first_activity_date D, last_activity_date D, downstream_activity R (Downstream Activity), associated_funding R (Associated Funding),
then one flag column per observed token of the `;`-joined relationship and direction sets:
has_direct B (Has Direct Activity) ... one per distinct token, header "Has <Token> Activity" for relationships and
"Has Support Activity" / "Has Oppose Activity" for directions. The token vocabulary is derived from the data, sorted.
Note the header `Associated Funding` replaces the industry-parameterised `Associated <Industry> Funding`.

### 2.12 carry-throughs (one table each, columns exactly as the Sept-2026 Overview headers, snake_cased)
transfer_paths (Cycle -> Election Cycle, Funded Committee, Source Committee, Destination Committee, Reported Net Transfer R, Depth I, Representative Path, Traversal Status);
funding_cohorts (Election Cycle, Company, Funding Type, Recipient Committee, Receipt Role, Included Net Receipts R, Receipt Count I, First Receipt D, Last Receipt D);
allocation_estimates (Election Cycle, Funded Committee, Candidate ID, Candidate, Direction, Conditional Estimate R);
allocation_coverage (Election Cycle, Funded Committee, Net Input Funding R, Nonnegative Model Funding R, Estimated Candidate Activity R, Unresolved R, Negative Net Funding R, Unresolved Reasons T);
source_freshness (Election Cycle, FEC Dataset, Checked At D or T, Server Last Modified T, SHA-256 T, Source URL);
classification_review (Election Cycle, Committee ID, Committee, Official Type, Reporting Category, Included Funding R);
state_destinations and recipient_locations: as the R frames, headers title-cased; any `;`-joined evidence column is DROPPED;
accounting_basis (Basis, Rule) - the six static rows of the Node builder.
These tables may be absent from a store (older export); the writer skips absent tables and lists them in About.

### 2.13 data_quality  (key: check_id, source)
| column | type | sheet header |
|---|---|---|
| check_id | T | Check |
| source | T | Source (r_guard / enrichment / writer) |
| severity | T | Severity |
| passed | B | Passed |
| detail | T | Detail |
| metric | T | Metric |
R guard results and enrichment quality checks are inserted by their producers; the writer APPENDS its own rows.

## 3. Writer behaviour (build_tidy_workbook.py)
- CLI: `--staging <sqlite>` (required), `--out <xlsx>` (required), `--database <mentat.db>` (optional; independent SQL checks),
  `--database-sha256 <hex>` (optional; verified against --database when both given), `--payload <industry_data json>` (optional; expected_cycle_totals),
  `--overview <Overview xlsx>` (optional; its sha256 goes into About), `--overview-receipt <finalizer receipt json>` (optional; cycle_totals),
  `--split-rows <int>` (default env MENTAT_DATA_SPLIT_ROWS or 50000), `--industry <name>` (overrides metadata), `--cycle-label <label>`.
- Sheet order: About, Contributions, Giving Facts, Recipient Facts, Contributor Facts, Location Facts, Committees, Committee Sponsors, Candidates,
  Downstream Activity, Beneficiary Bridge, Transfer Paths, Funding Cohorts, Allocation Estimates, Allocation Coverage, Source Freshness,
  Classification Review, State Destinations, Recipient Locations, Accounting Basis, Data Quality.
- Any sheet with more rows than --split-rows is emitted as `<Sheet> <cycle_label>` per cycle (identical columns), never as a bare cycle label.
- Header row 1; freeze A2; one ListObject per sheet named `tbl_<snake>` (split sheets: `tbl_<snake>_<end_year>`); TableStyleMedium2; autofilter.
- Number formats: money `$#,##0.00;[Red]($#,##0.00);-`, integer `#,##0`, date `yyyy-mm-dd`. Booleans written as Python bool. IDs written as str.
- About rows (Key | Value): Industry, Schema Version, Generated At, Cycle Label, Cycles, Lineage (value = `Source DB SHA-256: <hex>` as ONE string),
  Source DB SHA-256, Source DB Path, Overview Workbook SHA-256, Payload SHA-256, Exporter Version, Writer Version, Accounting Note,
  Split Rows Threshold, then `Rows: <Sheet>` per sheet, then `Blank columns` (JSON list), then `Absent tables` (JSON list).
- Data Quality rows appended by the writer (all severity "fail" unless noted):
  W1 `giving_facts_vs_contributions` per cycle: SUM(giving) == SUM(analysis_amount);
  W2 `recipient_facts_vs_contributions`, W3 `contributor_facts_vs_contributions` (person rows only vs contributions with person_key), W4 `location_facts_vs_contributions`;
  W5 `expected_cycle_totals` per cycle vs metadata/payload (skip with detail when absent);
  W6 `overview_cycle_totals` per cycle vs --overview-receipt (skip when absent);
  W7 `database_amount_and_rows` per cycle x company: SUM(amount) and COUNT(source_id) of accepted rows in supported cycles recomputed by SQL over --database
     (mirror report_source_guard.source_facts; skip with reason when the DB is absent/unreadable);
  W8 `unique_keys` per table; W9 `no_multivalue_cells` (no ';' in any T column of fact/dimension sheets, EXCEPT prose columns:
     Ownership Status, Memo Text, Source URL, Representative Path, Transfer Records, Unresolved Reasons, Detail - amended 2026-09-15, Lane A finding D3);
  W10 `header_vocabulary` (all headers unique, row 1);
  WRITER NOTE (Lane A finding F6): every write-only sheet part MUST carry a `<dimension ref="A1:..."/>` element; without it openpyxl's
  read-only loader walks the whole sheetData on every open (418 s measured on the 33 MB mock vs 0.03 s with it).
  W11 `lineage_literal` (About contains the literal `Source DB SHA-256: <hex>`).
- Exit code 0 only when every severity-fail check passed; otherwise remove the pending file and exit 2. Writes `<out>.receipt.json`
  {expected_worksheet_count, sha256, rows_per_sheet, checks, split_sheets, schema_version, writer_version}.

## 4. Example rows (JSON, one per table; synthetic values; use these in fixtures and tests)
```json
{"contributions": {"source_id":"4021620231727827649","transaction_id":"SA11AI.12345","back_reference_transaction_id":null,
  "cycle_label":"2021-2022","cycle":2022,"source_cycle":2022,"cycle_alignment":"OK","company":"Example Credit Union",
  "contributor":"DOE, JANE","person_key":"Example Credit Union|DOE|JANE|C01","identity_basis":"Exact name + employer",
  "employee_tier":"Employee","employer":"EXAMPLE CREDIT UNION","occupation":"MEMBER SERVICE","city":"VIENNA","state":"VA",
  "zip5":"22180","zipcode":"221804907","date":"2021-06-28","amount":25.0,"analysis_amount":25.0,"include_in_analysis":1,
  "inclusion_reason":"Countable receipt","company_match_status":"accepted","company_match_reason":"verified_roster_alias","matched_alias":"EXAMPLE CREDIT UNION",
  "recipient":"EXAMPLE CONDUIT","committee_id":"C00000001","recipient_key":"FEC:C00000001","recipient_category":"Candidate","category_source":"master",
  "party":"Democratic","party_source":"master","committee_type_code":"O","committee_type":"Super PAC (independent expenditure-only)",
  "committee_designation_code":"U","committee_designation":"Unauthorized","record_type":"contribution","source_table":"contributions",
  "funding_source_type":"individual","funding_direction":"inbound","receipt_role":"original","receipt_type_full":"Earmarked contribution",
  "filing_form":"F3X","line_number":"11AI","memo_text":null,"is_memo_leg":0,"is_conduit_leg":0,"superseded_by_amendment":0,
  "duplicate_filing_version":0,"duplicate_memo":0,"duplicate_of_sub_id":null,"duplicate_reason":null,"recipient_state":"MA","represented_state":null,
  "source_url":"https://docquery.fec.gov/cgi-bin/fecimg/?000000000000000000"},
 "giving_facts": {"cycle_label":"2021-2022","cycle":2022,"company":"Example Credit Union","employee_tier":"Employee",
  "recipient_category":"Candidate","party":"Democratic","giving":1250.0,"gift_count":48,"distinct_contributors":12,"distinct_recipients":9},
 "recipient_facts": {"cycle_label":"2021-2022","cycle":2022,"company":"Example Credit Union","committee_id":"C00000001","employee_tier":"Employee",
  "recipient":"EXAMPLE CONDUIT","recipient_category":"Candidate","category_source":"master","party":"Democratic","party_source":"master",
  "committee_type_code":"O","committee_type":"Super PAC (independent expenditure-only)","committee_designation_code":"U","committee_designation":"Unauthorized",
  "sponsor_candidate_id":null,"sponsor_candidate":null,"sponsor_office":null,"sponsor_state":null,"sponsor_district":null,"sponsor_count":0,
  "connected_organization":null,"committee_relationship":"Conduit","ownership_status":"Unaffiliated","giving":1250.0,"gift_count":48,
  "distinct_contributors":12,"first_gift_date":"2021-03-02","last_gift_date":"2022-10-30","fec_committee_url":"https://www.fec.gov/data/committee/C00000001/"},
 "contributor_facts": {"cycle_label":"2021-2022","cycle":2022,"company":"Example Credit Union","person_key":"Example Credit Union|DOE|JANE|C01",
  "party":"Democratic","contributor":"DOE, JANE","employee_tier":"Employee","identity_basis":"Exact name + employer","city":"VIENNA","state":"VA",
  "zip5":"22180","employer":"EXAMPLE CREDIT UNION","occupation":"MEMBER SERVICE","distinct_addresses":1,"giving":125.0,"gift_count":5},
 "location_facts": {"cycle_label":"2021-2022","cycle":2022,"company":"Example Credit Union","state":"VA","city":"VIENNA","zip5":"22180",
  "giving":4300.0,"gift_count":71,"distinct_contributors":19},
 "committees": {"committee_id":"C00000001","cycle_label":"2021-2022","cycle":2022,"committee_name":"EXAMPLE CONDUIT","committee_type_code":"O",
  "committee_type":"Super PAC (independent expenditure-only)","committee_designation_code":"U","committee_designation":"Unauthorized","party":"Democratic",
  "party_affiliation":"DEM","committee_state":"MA","recipient_category":"Candidate","category_source":"master","party_source":"master",
  "connected_organization":null,"ownership_status":"Unaffiliated","committee_relationship":"Conduit","mapping_source":"FEC master","sponsor_count":0,
  "top_downstream_candidate_id":"H0XX00001","top_downstream_candidate":"ROE, RICHARD","top_downstream_activity":15800.0,
  "fec_committee_url":"https://www.fec.gov/data/committee/C00000001/"},
 "committee_sponsors": {"committee_id":"C00000002","candidate_id":"H0XX00001","cycle_label":"2021-2022","cycle":2022,
  "relationship":"Principal campaign committee","link_source":"FEC ccl","candidate":"ROE, RICHARD","source_url":"https://www.fec.gov/files/bulk-downloads/2022/ccl22.zip"},
 "candidates": {"candidate_id":"H0XX00001","candidate":"ROE, RICHARD","party":"Democratic","party_affiliation":"DEM","office_code":"H","office":"House",
  "state":"XX","district":"01","incumbent_status":"Incumbent","principal_committee_id":"C00000002","fec_candidate_url":"https://www.fec.gov/data/candidate/H0XX00001/",
  "source_url":"https://www.fec.gov/files/bulk-downloads/2022/cn22.zip"},
 "data_quality": {"check_id":"giving_facts_vs_contributions","source":"writer","severity":"fail","passed":1,
  "detail":"2021-2022: Giving Facts 1,250.00 == Contributions analysis 1,250.00","metric":"1250.00"}}
```
