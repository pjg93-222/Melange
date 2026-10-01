# Staffer Network Corpus Specification

**Version:** 1.1<br>
**Date:** 2026-08-29<br>
**Status:** Adjudicated acquisition and normalization contract; Phase 0 exit passed; restricted Politico corpus normalized; identity pilot remains unadjudicated and canonical publication is blocked

## 1. Purpose

This document defines the evidence corpus below the legislator layer: what each source can establish, how it enters the corpus, what is retained, how records are counted, and which gaps quarantine a source. It distinguishes source assertions from canonical facts and analytical projections.

The corpus is not a contact list. It is a versioned evidence system for people, government service, lobbying observations, organizations, education, and the provenance needed to reproduce or reverse each conclusion.

## 2. Corpus zones

| Zone | Contents | Cross-source merges | Repository policy |
|---|---|---:|---|
| Raw / immutable | Exact bytes, request census, hashes, retrieval/source times, terms and schema | No | Machine-local; restricted/licensed/PII material never checked in |
| Normalized / source-native | Lossless source IDs, strings, amendments, locators, native time semantics, explicit rejects | No | Machine-local unless redistribution is clearly permitted |
| Resolved / canonical | Entities, accepted mappings, competing claims, conflicts, append-only decisions | Yes, reversible | Local ledger; public-safe summaries only |
| Derived / analytical | Episodes, transitions, co-tenure, overlays, weights, support digests | Yes, versioned | Deterministic safe artifacts may be published |
| Adjudication | Identity, container, interval, institution/program, amendment and split queues | Candidate pairs only | Local labels; de-identified aggregate receipts may be published |

Primary raw root:

```text
%LOCALAPPDATA%\Melange\staffer_network\raw
```

Restricted normalized rows and adjudication candidates live under sibling `normalized` and `resolution_pilots` roots. They are immutable, machine-local, and excluded from repository/synced storage.

Existing LDA sweeps remain in their established `%LOCALAPPDATA%\Melange\lda_rebuild\raw\sweeps` location and are referenced by hash/manifest.

## 3. Measured local baseline

All facts in this section were measured read-only on 2026-08-29. Counts are evidence for planning, not frozen future denominators.

### 3.1 Current staff directory

`data/members/staff_directory.json` contains:

- 533 member-office keys.
- 5,773 staff rows and 5,773 distinct Quorum IDs.
- 2–54 rows per member; mean 10.83.
- no missing `id`, `name`, or `title` in the derived artifact.
- 54 starred profiles.
- pre-remediation baseline: 5,769 nonempty email fields and 5,773 nonempty phone fields; current artifact: zero contact keys/values.
- 5,760 distinct display names; 13 display names repeat, demonstrating that names cannot be identifiers.
- original SHA-256 `8B245787C8C1AE1A8B385EA4B6C886FC7DAF5C8A309FA19F8AF412DFA4F8B4BA`; contact-free current SHA-256 `7ABFBC9EDBBCA828009EE270DFC1542C582FC6CAD1746F1AFD4DE7D179DF3B52`.

The producer is `fec/members/build_staff_directory.py`. Its configured `source_data/staff` inputs are absent, so the derived artifact is not presently reproducible from the repository checkout. P-1 remediation removed all direct email/phone fields from this file and the two member-desk surfaces, patched both future producers, registered every artifact, and retained hash-verified originals in restricted machine-local quarantine outside OneDrive. The contact-free file remains a restricted legacy input, not an enabled public-safe seed, pending an A-0 internal-use authority ruling and C-10a source-native import.

### 3.2 Quorum workbooks 45–52

Eight source workbooks were found in the supplied Downloads location. A lossless workbook audit found:

| Measure | Count | Share of 5,777 unique source IDs |
|---|---:|---:|
| Physical data rows | 6,773 | — |
| Unique Quorum IDs | 5,777 | 100% |
| Duplicate rows by ID | 996 | — |
| Any Education 1–3 | 1,641 | 28.41% |
| Any Degree 1–3 | 1,606 | 27.80% |
| Previous Industry | 3,090 | 53.49% |
| Previous Role 1–2 | 553 | 9.57% |
| Committee Works For, raw rows | 81 | — |
| Committee Works For, unique IDs | 66 | 1.14% |

All audited rows had a title and member-work field. The current producer drops education, degrees, previous industry, previous roles, and committee fields. A Phase 1 importer should retain those as dated source assertions without treating them as complete history.

Source hashes:

| Workbook | SHA-256 |
|---:|---|
| 45 | `D73B842F92F16E78A697078CD3198B219F4FD15944A6E51F39F43C3A61C0975A` |
| 46 | `A2D4C59275463E2031A3475C9E599B1FFA6FEB4B9ABB892EFA6FC7319D8F2C85` |
| 47 | `DCEBA53CC4AC0702068C8403644BD1A2F2EFB419A6E5C60BDB61E71B391AC427` |
| 48 | `E8E6DA10E9FFE8D2D8091A206A43A1CC966585F6BA7885C15D319E5D20B20026` |
| 49 | `0A25DDA1B18B72B14D07F9E1FD63B2859BEE2E02589514A9A6A15F5346104DF4` |
| 50 | `1A90ABA0E7E81EB646A86B50A51CBA1810E930C37CDE835036FC8669D0F41E92` |
| 51 | `284872E440C43406EF025AE1E22E2FEB639BC59394C166F21DA6BDAE75CC7BF0` |
| 52 | `ECACE6074FAEEFB7142AF0CB5DF69D92012A5BEDE7BEA215A38BB94D5DC45266` |

These inputs contain contact PII. Stage exact bytes only in the restricted raw zone; derived graphs must omit email and phone.

### 3.3 LDA raw sweeps

The repository already includes `fec/lobbying/collect_lda_filings.py`, and the machine has 2021–2026 raw sweeps. A 2026-08-29 fail-closed reconciliation verified all 21,599 advertised pages and MD5s, then compared physical objects, unique filing UUIDs, and the per-page API census:

| Year | Pages | Physical objects | Unique filing UUIDs | Duplicate occurrences | API count first→final | C-5 year result |
|---:|---:|---:|---:|---:|---:|---|
| 2021 | 3,632 | 90,778 | 90,778 | 0 | 90,778→90,778 | Pass |
| 2022 | 3,741 | 93,513 | 93,495 | 18 | 93,513→93,513 | Fail |
| 2023 | 3,813 | 95,305 | 95,297 | 8 | 95,305→95,305 | Fail |
| 2024 | 3,878 | 96,929 | 96,911 | 18 | 96,929→96,929 | Fail |
| 2025 | 4,357 | 108,913 | 108,888 | 25 | 108,913→108,913 | Fail |
| 2026 through approximately 2026-08-01 | 2,178 | 54,432 | 54,413 | 19 | 54,427→54,432 | Fail |
| **Total** | **21,599** | **539,870** | **539,782** | **88** | **539,865→539,870** | **Fail** |

All 88 repeated UUID payloads were byte-semantically identical after JSON parsing, none conflicted, and no UUID crossed years. They may eventually be deterministically deduplicated, but doing so leaves only 539,782 unique filings—83 below the first-page census sum and 88 below the final-page census sum. The old five-object diagnosis compared physical rows to a moving count and therefore understated missing unique coverage. C-5 remains failed. Recollect/reconcile the affected query-years through the existing collector, freeze start/end watermarks, and disposition every duplicate and absent UUID before normalization. The attached source document's later 2026 probe of 56,162 remains a separate delta target.

The full page scan measured:

- 1,034,945 activities.
- 2,737,076 lobbyist disclosures.
- 746,692 disclosures with nonempty `covered_position`.
- 25,299 unique LDA lobbyist IDs.
- 9,454 lobbyists with at least one nonempty covered position.
- 21,648 unique lobbyist-position pairs.
- 19,306 unique covered-position strings.
- 7,052 registrants and 46,668 clients.

The machine-readable receipt is `data/staffer_network/receipts/lda_reconciliation_20260829.json`.

Raw LDA activities preserve `lobbyist.id`, name parts, `covered_position`, and `new` together. `fec/lobbying/lobby_interactions.py` currently flattens lobbyist names and covered positions into independent pipe-delimited sets; the staff corpus must normalize from raw API pages and preserve the pair.

A strict normalized first-plus-last-name comparison to Quorum yielded only candidate links: 236 shared name buckets, 186 one-to-one name buckets, 241 Quorum IDs, and 300 LDA IDs. These are not resolved identities.

Covered-position text is a self-disclosed lookback and is often not repeated on later filings. A blank later observation does not negate prior government service. Targeted first-disclosure backfill or a wider historical filing corpus is required for coverage; the text alone supplies no dates.

### 3.4 LittleSis bulk data

`relationships.json.gz` is present:

- size 110,381,587 bytes.
- SHA-256 `C11D7058CB13D264854F703310FDDF30C1391EF604C0164847945939FD38D489`.
- attached-document audit: 1,880,491 relationship records, including 1,267,716 Lobbying, 368,995 Position, and 44,673 Education relationships.
- attached-document audit: 61.4% of Position relationships are undated.

The matching `entities.json.gz` is absent. LittleSis is quarantined until both files share a frozen vintage/manifest and every relationship endpoint resolves to the entity spine. Undated Position records may corroborate structure but cannot supply duration or temporal weight.

### 3.5 Historical member spine

`votes/HSall_members.csv` contains 51,061 rows spanning Congresses 1–119, with 12,584 unique nonblank Bioguide IDs and 68 blank Bioguide cells. It is a useful broad member/service spine, but it does not by itself provide all exact service dates.

Pin both current and historical files from `unitedstates/congress-legislators`, record the commit hash, load service terms and committee data needed for term-valid resolution, and reconcile to official House, Senate, Congress.gov, and Bioguide identifiers. The existing current-only `name2bio()` path is insufficient for alumni and same-name historic members.

## 4. Source authority matrix

| Source | Authority for | Not authority for | Corpus status |
|---|---|---|---|
| House Statement of Disbursements | Published House disbursement/payroll observations and performance dates | Complete workforce, unpaid roles, continuous employment, person identity | Phase 2 primary breadth; collector absent |
| Senate Report of the Secretary | Published Senate payment observations | Complete workforce, stable person IDs, continuous employment | Phase 2 primary breadth; parser absent |
| LDA.gov API | Filed lobbyist/activity, registrant, client, covered-position, chamber/agency and issue assertions | Complete career history, prior-service dates, direct contact with an individual | Existing 2021–2026 baseline; reconcile and refresh |
| Official member identifiers/rosters | Legislator identity and official service | Staff identity | Canonical member anchor |
| `unitedstates/congress-legislators` | Convenient term/name/committee crosswalk | Sole final authority; may lag | Pin and reconcile |
| Quorum export | Directory/profile assertions as of a documented export time | Exhaustive history or currentness after snapshot | Existing derived file is a restricted legacy input; stripped seed and raw enrichment require explicit A-0 scopes |
| Politico Pro | Current directory UUID, displayed name, role/employer assertions, party partition and issue-area labels under the user-attested physical permission letter | Exhaustive history, exact employment dates, supervision, complete education, or redistributable public truth | Restricted census and source-native normalization complete: 18,618 persons, 22,309 role assertions, 20,485 issue assertions, zero contact findings/merges; C-2 identity quality and redistribution-safe canonical output remain gated |
| LittleSis entities + relationships | Candidate generation and corroborative assertions | Census, canonical identity truth, complete dates | Supplementary; entity dump missing |
| NCES IPEDS and CIP | Institution/program normalization | Proof a person attended or studied a subject | Reference normalization |
| Existing LobbyView/industry axes | Organization crosswalk and analytical sector coding | Person career history or primary disclosure | Versioned supplementary crosswalk |
| LegiStorm, if licensed | Additional profile claims | Publicly redistributable truth | Optional restricted source |

Authoritative references:

- [House Statement of Disbursements](https://www.house.gov/the-house-explained/open-government/statement-of-disbursements)
- [Senate Report of the Secretary](https://www.senate.gov/legislative/common/generic/report_secsen.htm)
- [LDA API](https://lda.gov/api/) and [API terms/rate limits](https://lda.gov/api/tos/)
- [LittleSis bulk data](https://littlesis.org/bulk_data)
- [Congress Legislators data](https://github.com/unitedstates/congress-legislators)
- [NCES CIP resources](https://nces.ed.gov/ipeds/cipcode/resources.aspx)
- [NCES IPEDS Data Center](https://nces.ed.gov/ipeds/datacenter/Data.aspx)
- [Congress.gov API](https://api.congress.gov/)

## 5. Source-native record contracts

### 5.1 Quorum/current directory

Required retained fields:

```text
quorum_observation_id              # source file hash + physical row
quorum_person_id
source_as_of                       # nullable; documented export time only
observed_at                        # receipt/collection time
name_raw
title_raw
member_works_for_raw
committee_works_for_raw
education_institution_raw[1..3]
degree_raw[1..3]
previous_industry_raw
previous_role_raw[1..2]
source_file_sha256
source_row_number
```

Email and phone may remain only in restricted raw input or be converted to authorized salted local ER features. They do not enter normalized public exports.

Filesystem modification time is not a source snapshot or valid-time assertion. Use a documented export/source `as_of` when available; otherwise keep `source_as_of` and valid time unknown while retaining receipt time as observed time.

Raw ingestion conserves all 6,773 physical observations through a many-observation-to-one-source-entity relation, creates or dispositions all 5,777 unique Quorum source IDs, reproduces the 5,773 current derived office mappings, and reason-codes the four source IDs absent from that derived seed. After an explicit authority scope permits use of the legacy derived file, stripped-seed ingestion must accept all 5,773 validated rows, exclude every email/phone/contact hash, and represent all 533 offices; imported-plus-rejected conservation cannot substitute for usable coverage. Cross-source Quorum↔Politico identity reconciliation is a later metric and must not be conflated with seed ingestion.

### 5.2 House SOD

Retain source-native report/quarter, office/vendor/payee raw fields, vendor ID where present, title/description, amount, start/end performance dates, amendment/revision identity, file hash, CSV row or PDF page locator, and parser outcome.

A payment row is a `payroll_observation`, not a continuous `employment_episode`. Non-employee rows must be explicitly classified or rejected with a reason.

Expected inventory begins with 2009Q3, when official online coverage begins, through the last fully published quarter. Partial/current quarters are reported separately.

### 5.3 Senate disbursements

Retain report half, volume/part, page/table locator, office, name/payee, title/description, amount, performance fields where printed, digital source identity, and parser outcome.

Expected inventory begins with April–September 2011 availability unless the official census establishes an earlier machine-retrievable span. Multipart reports are inventoried at the part/byte level. Gold pages and printed control totals, when available, provide parser denominators.

### 5.4 LDA

Retain filing UUID/version/amendment, filing and posting times, registration/report identity, activity ID, issue code, bill identifiers, contacted chamber/agency, client ID, registrant ID, lobbyist ID/name parts, `covered_position_raw`, `new_flag`, source page/hash, and raw JSON pointer.

Required invariants:

- `lda_registrant_id` and `lda_client_id` stay in distinct namespaces.
- each lobbyist-position occurrence remains paired within its activity.
- blanks are observations, not negative career assertions.
- covered-position-only links have no inferred start/end/departure dates.
- no direct person-contact edge is inferred from an activity.

### 5.5 LittleSis

Retain dump vintage/hash, entity ID/type/name/aliases, relationship ID/category/order, endpoints, raw fields, date fields with precision, description, and parse disposition. Ingest entities first; reject/quarantine dangling relationships. Category vocabulary and license/redistribution status belong in the manifest.

### 5.6 Historical members and committees

Retain Bioguide ID, source member/term key, congress, chamber, state/district, party, valid service bounds, name variants with time, committee/subcommittee code, side/role, source version, and provenance. Unknown exact dates remain coarse.

### 5.7 IPEDS/CIP

Retain reference vintage, UNITID, institution names/aliases/status, program code/title and crosswalk history. Foreign schools, high schools, closed/merged institutions, and ambiguous campuses receive explicit non-IPEDS/unresolved outcomes rather than lowering an ineligible denominator.

## 6. Manifests and conservation

Every source snapshot has a canonical manifest containing:

```text
source_system
authority_scope
terms_uri
license
authorization_status
redistribution_class
source_as_of
collected_at
query_or_inventory
crawl_watermark
collector_version
parser_version
schema_version
file list with byte size and sha256
expected source records/parts
observed physical records/parts
accepted count
rejected count by reason
duplicate source-key count
amendment/version policy
freshness rule
manifest content hash
```

Conservation is exact at each boundary:

```text
observed_physical_records = accepted_records + rejected_records
```

Semantic extraction coverage is measured separately. A parser cannot define its own denominator by emitting only rows it recognizes.

For mutable APIs, freeze endpoint/query, crawl watermark, pagination identity, and start/end counts. For reports, freeze the expected report/part inventory. For bulk dumps, freeze both entity and relationship files to the same release/vintage.

## 7. Coverage policy and known blind spots

- House data before 2009Q3 and Senate data before April 2011 are left-censored in the planned public payroll corpus.
- Payroll omits unpaid staff, fellows, detailees, contractors, and some interns; title, location, committee side, and employment fraction may be unknown.
- Current commercial directories create survivorship and availability bias and do not establish history after the snapshot.
- LDA covered-position history is selective, client-specific, limited in lookback, frequently undated, and not repeated on every filing.
- LDA activity supports filing/activity relationships, not access, influence, or contact with an individual.
- LittleSis is curated and non-random; undated relations cannot support duration.
- IPEDS coverage excludes many foreign and secondary institutions; UNITIDs and institutions change over time.
- High-degree false person merges are catastrophic. Common names, member/staffer role changes, and same-name historic members receive special review.
- House revisions, Senate multipart reports, API amendments, and source retractions require bitemporal replay.
- Committee membership/leadership history and office location may remain incomplete until an effective-dated source is pinned.

Coverage receipts always state the source window and eligible denominator. “Historic staff coverage” is never reported against all people who may ever have worked on the Hill.

## 8. Acquisition order

1. **P-1 complete:** inventory, remediate, and quarantine the restricted legacy derived directory. Next, after a specific internal-use authority/retention ruling, produce a source-native 5,773-row/533-office seed from the now contact-free input. Privately stage Quorum workbooks 45–52 only after a separate raw-source authority scope passes; then conserve all physical observations without exporting PII.
2. Load the existing historical member spine and pin/reconcile exact term/committee references.
3. Reconcile existing LDA manifests to raw pages, collect the 2026 delta, then plan targeted historical first-disclosure backfill.
4. Acquire the matching LittleSis entity dump and verify referential integrity before enabling that source.
5. Build House report inventory and lossless collector.
6. Build Senate report/part inventory and annotated parser pilots.
7. Acquire NCES reference vintages.
8. **Normalization complete:** the authorized Politico snapshot is conserved into 18,618 source-native people, 22,309 roles, and 20,485 issues under the restricted root. The next step is independent adjudication of the deterministic source-pair queue; any future profile-detail expansion or other licensed source still requires its own authority, retention, rate, and redistribution decision.

Dead ends do not authorize silent substitution. When an authoritative source is unavailable, record the gap, use a clearly labeled supplementary source for candidate generation if permitted, and quarantine unsupported semantic fields.

## 9. Publication and privacy classes

| Class | Examples | Allowed output |
|---|---|---|
| Public source | Official reports, public API records, permitted reference data | Manifests and public-safe normalized/derived fields subject to source terms |
| Restricted licensed | Quorum, Politico, LegiStorm or similar exports | Local raw/normalized; only contractually permitted aggregates/derived fields |
| Direct PII | Email, phone, address | Restricted raw only; authorized salted local ER features; never graph output |
| Adjudication sensitive | Candidate pairs, reviewer rationales | Local; aggregate agreement/coverage receipts only |
| Public-safe derived | Opaque person IDs, typed edges, weights, support digests | Deterministic artifacts after PII/license audit |

Every output manifest declares its class and its upstream redistribution constraints. A support digest points to local evidence without embedding restricted source text.

## 10. Corpus readiness ruling

Phase 0 has passed with sealed I-10a isolation, I-11 deterministic/atomic publication, and P-1 privacy/license receipts. Politico A-0, census/normalization C-1, and I-13 pass for the acquired snapshot: 18,618 unique UUID rows were conserved across four party partitions into 18,618 people, 22,309 roles, and 20,485 issues with zero contact findings. A reproducible no-auto-merge C-2 pilot accounts for every one of the 5,773 legacy rows and emits 4,836 restricted candidates, including 2,643 strict name+title+office candidates; the 200-row strict review sample is not yet adjudicated, so estimated precision is null and canonical merges remain zero. This is therefore a fleshed restricted source-native corpus, not a completed canonical corpus. The Quorum-derived seed/raw enrichment remain separately authority-gated; LDA C-5, exact-term normalization, LittleSis entities, public payroll collectors/parsers, institution/program references, and ER/parser gold sets remain open. Staff/industry analysis and engine consumers remain off.
