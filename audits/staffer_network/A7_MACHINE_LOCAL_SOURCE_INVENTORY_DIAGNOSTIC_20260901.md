# A7 machine-local source inventory diagnostic — 2026-09-01

## Result

**PASS.** A bounded, local-only scan found two already-held source families that can add review evidence to the sealed 25,340-ID LDA census. It produced deterministic primary/twin candidate ledgers and an independent verification receipt. It made **zero identity promotions, zero employment promotions, and zero complete-history assertions**.

- Official Senate LDA LD-203 sweep: 210,562 raw report rows for 2021–2026; four canonically identical pagination duplicates; 210,558 unique filings. Exact numeric LDA lobbyist-to-registrant anchors yielded 143,513 dated **registrant-affiliation** candidates for 22,754 people and 6,194 registrants.
- Machine-local Mentat/FEC warehouse: 1,615,346 official contribution records in 210 partitions across seven sector snapshots. The three-anchor rule yielded 979 dated **employer point observations** for 37 people and 18 registrants. Fourteen of those people had no prior A1–A4 employment candidate.
- Exact census conservation: 25,340 coverage rows; 2,586 people have no A7 candidate; the A4 baseline contained 11,720 people with no prior employment candidate.
- User-supplied LegiList was not fetched. Earlier work already established that LegiList numeric ID `147664` maps to exact sealed ID `lda:lobbyist:147664`; this A7 pass needed no network or browser activity.

## Candidate rules and nonclaims

The LD-203 ledger requires the exact numeric lobbyist ID to exist in the sealed census and the exact numeric registrant ID to exist in the source-native registrant set. A report-period bound and posting timestamp are retained, but an LD-203 filing association is **not** treated as proof of employment or tenure. Name consistency is only a review signal: 112,598 candidates are name-consistent and 30,915 carry a name-inconsistent review flag; exact numeric IDs remain the identity anchor.

The FEC ledger requires all three independent anchors to agree:

1. The complete FEC contributor name exactly matches a globally unique normalized LDA name key. Comma-order reversal is supported; middle names are not dropped.
2. The FEC employer exactly matches a normalized source-native LDA registrant name. No fuzzy legal-suffix stripping is used.
3. The exact LDA person ID has at least one official LD-203 filing under that exact registrant ID.

Every FEC row has anchor count 3, status `REVIEW_REQUIRED`, and day precision. Dates span 2021-01-25 through 2026-06-29; 978/979 rows have a non-empty occupation field. Sector yield was Community Banks 2, Credit Arms 385, Credit Union 2, Fintech 64, Property & Casualty Insurance 130, Telecom 396, and Crypto 0. Repeated FEC receipts remain separate source observations by unique `sub_id`.

## Primary artifacts

Root: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\a7_machine_local_source_inventory_20260901_primary`

| Artifact | Schema / rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `a7_source_inventory.json` | `staffer-network-a7-machine-local-source-inventory-v1` / 1 | 65,848 | `7cf11edf88c0a5d5325f985b87c00da930077de6b1b0f561d3be1ceb307252f5` |
| `a7_source_file_inventory.ndjson.gz` | source-file receipts / 8,651 | 452,846 | `6d09989565dd837b695c090db77c7e64cd025680607441ced5c31c93fe35dbe8` |
| `a7_ld203_affiliation_candidates.ndjson.gz` | `staffer-network-a7-ld203-affiliation-candidate-v1` / 143,513 | 20,634,747 | `bdcd2452afeb6b8f12457e1ef61dcf9e7c6785994ebebb1dc50d1e3688f1fbb2` |
| `a7_fec_employment_observation_candidates.ndjson.gz` | `staffer-network-a7-fec-employer-observation-v1` / 979 | 244,043 | `6f67f0d8c731277a761ad0d18ad1610e57d21d371dfc38f5a84982ed9063db35` |
| `a7_coverage_25340.ndjson.gz` | `staffer-network-a7-machine-local-coverage-v1` / 25,340 | 558,904 | `2532d2946bd352359c9c79c30156d130a171e88fb3d05f628bfee6545f526546` |
| `a7_build_receipt.json` | `staffer-network-a7-machine-local-source-inventory-receipt-v1` / 1 | 3,252 | `f005be8f5999dcf006dbdd7093cec12356d9cb35376a6dbc228ef4af9bcfaa1c` |

Twin root: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\a7_machine_local_source_inventory_20260901_twin`. All five payload artifacts and the build receipt are byte-identical to primary.

Independent receipt: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\a7_machine_local_source_inventory_20260901_verification\verification_receipt.json`; 480 bytes; SHA-256 `7c8402784db9861c928bd4045ac7792022d96a92d18bf7e9d91bf38d3590d969`; status `PASS`.

## Source inventory

### Sealed source-native LDA and A4 baseline

Root: `C:\Users\pgoff\AppData\Local\Melange\staffer_network\normalized\lda-source-native\generation-20260830T231200Z`

- Receipt: 2,386 bytes; SHA-256 `5dfd3bbb16dea6ce940a687b15c74f07e720073d02b559d8000bb33db49dce8c`; status PASS.
- Lobbyist assertions: 25,340 rows; 1,928,569 bytes; SHA-256 `80ac82346c435bb8f1231d9f3425d759ca9a8ae063db879ec104244f9fcd282e`; schema `staffer-network-lda-lobbyist-assertion-v1`.
- Organization assertions: 54,073 rows; 2,503,228 bytes; SHA-256 `0d35902244f02688d9ac961379efee0f96e3cfab1184409a4c93bb0584a1aed2`; schema `staffer-network-lda-organization-assertion-v1`.
- Activity, industry-edge, and covered-position files were inventoried in the source receipt but were not used as new A7 evidence because they belong to previously covered LDA lanes.

A4 baseline: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\employment_candidate_coverage_house_senate_20260901_a\employment_candidate_coverage_25340.ndjson.gz`; 25,340 rows; 1,729,506 bytes; SHA-256 `453d34666509a20c9154f775996824574e81cb31311c238f8e515d374c0c6f56`.

### Official LD-203 pages

Root: `C:\Users\pgoff\AppData\Local\Melange\lda_rebuild\raw\ld203_sweeps`. Schema was discovered directly from the JSON pages. Top-level fields include filing UUID/type/year/period/document URL, filer type, posting timestamp, lobbyist, registrant, PACs, no-contribution flag, and contribution items; nested lobbyists include exact numeric `id` plus name components; nested registrants include exact numeric `id`, House registrant ID, name, and metadata; contribution items include type, contributor, payee, honoree, amount, and date.

| Year | Reports | Pages | Receipt SHA-256 |
|---:|---:|---:|---|
| 2021 | 36,165 | 1,447 | `234f69f3b1a858a8105106393336ce36cb29c22069b9424ffc8769bf6a3254d6` |
| 2022 | 38,489 | 1,540 | `8d36469492eba9399fa786e593143d2cf6d8a0228c2cd52f64964fef4b39699e` |
| 2023 | 38,901 | 1,557 | `bd34ef6a1b789acdf8bdb40bb84669dca38fe1e352965a3ddf632a68d075a098` |
| 2024 | 38,877 | 1,556 | `c5319a8efb3db8c53539051a566857c9bb24e651e2f02f242193a7af8e2da5dd` |
| 2025 | 40,452 | 1,619 | `65d299f46da902123a43b737ee8947326d1a9c8533bdf745692795ebd05cea49` |
| 2026 | 17,678 | 708 | `d4e3678dffcaf8f9ca1c1fd9379d1cbb86d44c0746402c6886cd43cded43adad` |

Every one of the 8,427 page files and six receipts is individually path/byte/hash recorded in `a7_source_file_inventory.ndjson.gz`.

### FEC contribution warehouse

Catalog: `C:\Users\pgoff\Mentat\outputs\raw-contributions\production-all-20260728T204300\catalog.json`; seven industries, 210 partitions, 1,615,346 rows; 5,364 bytes; SHA-256 `6e6804c7434cc9376810fcc2385671025c37b97dd0e4e66cb7150ff32650a6de`.

The 55-column contribution schema includes stable FEC IDs, full and component contributor names, city/state/ZIP, employer, occupation, amount/date, committee metadata, entity/amendment/report fields, source/PDF/load metadata, sector/company/variant provenance, and conduit/memo/amendment/duplicate/refund/entity flags. Snapshot logical hashes and counts are recorded in `a7_source_inventory.json`; every consumed snapshot manifest and compressed partition is individually recorded in the 8,651-row source-file ledger.

Read-only `PRAGMA quick_check` returned `ok` for each source database:

| Industry | Contribution rows | Bytes | Database SHA-256 | Exact path |
|---|---:|---:|---|---|
| Community Banks | 4,293 | 4,624,384 | `42b733201efff95404e9cc89e237d0d1b1655775f1b3d9ebd0b14ae256b42edc` | `C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs\20260728T204315-41296\industries\community-banks\data\mentat.db` |
| Credit Arms | 424,988 | 355,512,320 | `ce2d9c6b79da586c2176a755a81a2d46e0270acaf037c2049aeb95910661de38` | `C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs\20260728T204315-41296\industries\credit-arms\data\mentat.db` |
| Credit Union | 56,078 | 53,133,312 | `9a7c88ff97fdac51f26fad0a8b1731e8da0b77d35925bc44e67ab0e78b1d2279` | `C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs\20260728T204315-41296\industries\credit-union\data\mentat.db` |
| Crypto | 13,326 | 11,325,440 | `371f51e69ba2b9e477ec3a198d2a8e1ec689cd06f48b1c85683704772810893d` | `C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs\20260728T204315-41296\industries\crypto\data\mentat.db` |
| Fintech | 41,082 | 57,831,424 | `2a9bc0199a9065bde48c48e4a87b92e76fcb5557e15e146f59e557a40643231e` | `C:\Users\pgoff\Mentat\tmp\production-remaining-10lane-20260729T1235\runs\20260729T123437-15692\industries\fintech\data\mentat.db` |
| Property & Casualty Insurance | 329,509 | 282,054,656 | `712a1080ba38c2bcc94443c487dab0cfdc96a5c88ec0d68e9e0e8b4b59abe44e` | `C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs\20260728T204315-41296\industries\property-casualty-insurance\data\mentat.db` |
| Telecom | 746,070 | 605,716,480 | `34ef41793b3ab4c970e2d913ea7b42d50766b6c8f1430b40adbd9b0f8bd06d15` | `C:\Users\pgoff\Mentat\tmp\production-remaining-10lane-20260729T1235\runs\20260729T123437-15692\industries\telecom\data\mentat.db` |

### Local sources with no new defensible A7 linkage

- Current contact-free staff directory: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\members\staff_directory.json`; 533 office keys / 5,773 staff rows; schema `office -> [{id,n,t,star}]`; SHA-256 `7abfbc9edbbca828009ee270dfc1542c582fc6cad1746f1afd4de7d179df3b52`. No dates or exact LDA IDs; name-only linkage prohibited.
- Legacy copy: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\CLEAN_STATE_2026-07-05_1932\staff_directory.json`; 533 / 5,773; SHA-256 `8b245787c8c1ae1a8b385ea4b6c886fc7daf5c8a309fa19f8af412dfa4f8b4ba`. Same blocker.
- `Quorum Master.xlsx`: 8,478,026 bytes; SHA-256 `bcaac191fecaa5a197ecfb8794eccc4a6b9859989cfa01e4572ef2cf91026482`. Restricted contact source, not opened; prior remediation lane, no new exact-ID link.
- Politico and LittleSis local files were hashed and excluded because A3 already covered them. Exact paths and hashes are in `a7_source_inventory.json`.

## Verification

`a7_verify_machine_local_source_inventory.py` independently rehashed all source and output files, verified receipt byte/row claims, exact 25,340-ID conservation, LD-203 numeric ID anchors, all three FEC anchors, review-only status, zero promotions, and primary/twin equality. `test_a7_machine_local_source_inventory.py` has six passing tests covering person-name order, refusal to drop middle names, conservative organization normalization, observation-date bounds, LD-203 period semantics, and deterministic gzip.

## Remaining blocker and recommended next route

The already-held FEC warehouse is sector-scoped, so it cannot establish exhaustive coverage of the 11,706 baseline-uncovered people who remain without a newly defensible FEC employer observation after this lane. The two staff directories lack dates and exact LDA identifiers. No other already-held source inspected here supplied a defensible new exact-ID or multi-anchor employment link.

The next source route, in a separately authorized acquisition lane, is a complete official FEC individual-receipt corpus rather than the seven-sector warehouse, followed by the same three-anchor rule. For residual cases, use official employer/firm directories or archived official payroll/staff records only when an exact identifier or at least two independent non-name anchors are present. Do not promote LD-203 affiliation observations or FEC point observations directly into employment intervals.
