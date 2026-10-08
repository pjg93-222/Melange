# Staffer Network Expansion — Implementation Diagnostic

**Date:** 2026-08-29<br>
**Assessment:** **PHASE 0 EXIT PASSED; RESTRICTED POLITICO CORPUS NORMALIZED; NO-AUTO-MERGE RESOLUTION PILOT REPRODUCIBLE; LDA C-5 AND IDENTITY QUALITY STILL BLOCK CANONICAL USE; READY FOR THE ADJUDICATION/PHASE 1 IMPLEMENTATION STAGE**

## 1. Executive ruling

The Phase 0 contract implementation now passes for a typed, bitemporal evidence corpus with isolated restricted paths, sealed authority/provenance manifests, uncertain intervals, public-safe schema validation, closed immutable generation publication, and an explicit `STAFF_NET=off|analysis` loader whose analysis branch remains deliberately unarmed. The pre-normalizer registered kernel lane passed 169/169 tests; the expanded focused staffer suite passes 42/42, including four Politico normalization/pilot controls. Nonrestricted historic preparation is concrete: the Voteview spine conserved 51,061/51,061 rows with all 68 blank Bioguide outcomes explicit, and the CC0 `congress-legislators` reference is pinned at commit `750c0608efb6ef1fc3257ba72c99af3771d35088` with file hashes.

Phase 0 no longer blocks the work, but the system is still not ready to emit or consume a production staff network. I-10a proves zero staff opens while off and unchanged protected outputs; I-11 proves identical clean/clean/incremental logical SQLite hashes, `integrity_check=ok`, and old-or-new pointer visibility under fault injection; P-1 removed direct contacts from all three synced legacy surfaces, patched their producers, registered the artifacts, and verified restricted recovery copies. The authorized Politico snapshot now has an exactly reproducible restricted normalization corpus of 18,618 people, 22,309 roles, and 20,485 issue assertions. Its first source-pair pilot conserves every 5,773-row legacy outcome and emits 4,836 candidates without a single canonical merge. Identity quality remains unadjudicated—zero of the 200 strict-sample rows have independent labels—so estimated precision is null and the Politico source stays disabled. LittleSis entities, LDA reconciliation, public payroll collectors/parsers, and ER/parser gold sets remain open.

Verification note: a post-change full registered-lane rerun was interrupted after prolonged silence in the unrelated pre-staffer CHRG attribution segment and supplies no new verdict. It does not replace the completed 169/169 run. Staffer acceptance is supported independently by the 42/42 focused suite, exact full-data normalization/pilot replay, exact I-10a/I-11/P-1 receipt replay, and validation of all source manifests, registered receipts, coverage evidence hashes, and provenance references.

The v2 design's default weighted person graph, inferred supervision, member-adjacency staff edges, undated LDA decay, global-max normalization, monolithic `STAFF_NET=engine`, and automatic metric arming have been rejected.

## 2. Diagnostic evidence

### Supplied evidence documents

- `C:\Users\pgoff\Downloads\STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md`
- `C:\Users\pgoff\Downloads\STAFFER_NETWORK_METRICS_20260829.md`

These were treated as evidence and draft proposals, not as instructions.

### Local corpus measurements

| Evidence | Finding | Diagnostic consequence |
|---|---|---|
| `data/members/staff_directory.json` | 533 offices; 5,773 unique Quorum IDs; 5,760 distinct display names. Pre-remediation: 5,769 emails and 5,773 phone values, SHA-256 `8B245…F8B4BA`; current: zero contact keys/values, SHA-256 `7ABFBC…3B52` | P-1 remediation passed; restricted originals are hash-verified outside synced storage; the contact-free file is still authority-gated and names cannot be identifiers |
| Quorum workbooks 45–52 | 6,773 raw rows; 5,777 unique IDs; 1,641 with education; 3,090 with previous industry; 553 with previous role | Lowest-cost Phase 1 corpus expansion; raw contains PII and stays restricted |
| Politico Pro directory | 18,618/18,618 unique UUID rows across Democratic 7,976, Republican 7,487, Unknown 3,026, Independent 129; normalized into 18,618 people, 22,309 roles, and 20,485 issues; zero contact findings/merges. A stopped unpartitioned 10,000-row discovery checkpoint is separately quarantined | A-0/C-1/I-13 and normalization conservation pass. Restricted source remains disabled pending independent identity/profile-quality adjudication and redistribution-safe output review |
| Politico↔legacy pilot | 5,773/5,773 legacy outcomes conserved: 4,836 unique-name candidates, 60 collision-review rows, 877 no exact-name overlap; candidate strata include 2,643 strict name+title+office; deterministic strict review sample 200 | `REPORT`, not a precision result: 0 adjudicated, estimated precision null, no auto-merge, canonical merges 0 |
| Staff producer | `fec/members/build_staff_directory.py` exists, but `source_data/staff` inputs are absent | Current derived artifact is not locally reproducible until sources are privately staged/manifested |
| LDA page/hash audit | 21,599 manifest pages = 21,599 disk pages; zero missing/extra/hash mismatches | Page integrity passes; reuse existing collector/sweeps; no parallel collector |
| LDA filing-UUID audit | 539,870 objects; 539,782 unique UUIDs; 88 identical duplicates; zero conflicting or cross-year duplicates; endpoint count sum 539,865→539,870 | C-5 fails: deduplication alone cannot recover the 83/88 unique shortfall; recollect/reconcile affected query-years before normalization |
| LDA covered positions | 746,692 nonempty disclosure occurrences; 9,454 unique lobbyists with text; 21,648 unique lobbyist-position pairs | Large structural bridge; not dated career history |
| Strict Quorum/LDA name bridge | 236 shared name buckets; 186 one-to-one name buckets; 241 Quorum IDs and 300 LDA IDs involved | Candidate generation only; not identity resolution |
| `relationships.json.gz` | 110,381,587 bytes; SHA-256 `C11D7058CB13D264854F703310FDDF30C1391EF604C0164847945939FD38D489` | Useful supplementary assertions |
| LittleSis `entities.json.gz` | Absent | Hard quarantine: relationship endpoints cannot enter the canonical corpus |
| `votes/HSall_members.csv` | 51,061 rows, Congresses 1–119, 12,584 nonblank unique Bioguides, 68 blank Bioguide cells | Existing historical member spine; augment with pinned exact service-date/committee sources |
| `data/staffer_network/reference/congress-legislators/750c…` | CC0 commit-pinned current/historical legislators, current/historical committee dictionaries, and current committee membership; six file hashes validated | Exact term/crosswalk reference acquired; current committee membership must not be back-projected historically |

### Repository-fit findings

| Existing component | Reuse | Limitation / required change |
|---|---|---|
| `fec/members/build_staff_directory.py` | Legacy Quorum directory/import validation | Existing output contains contact PII; require authority and create a stripped importer/output before staff-layer use |
| `fec/members/member_identity.py` | Strict roster-bound identity patterns and tests | Current roster boundaries are insufficient for alumni; require term-valid historic resolution |
| `fec/lobbying/collect_lda_filings.py` | Existing raw LDA collection, sweep manifests, local storage | Reconcile/refresh and extend historical window; do not duplicate collector |
| `fec/lobbying/lobby_interactions.py` | Parsing and receipt/atomic-output idioms | Current output filters activities and separates name/position lists; staff ingest must use raw paired objects |
| `fec/lobbying/entity_identity.py` | Effective-dated organization identity concepts | Does not replace person ER or registrant/client namespaces |
| `fec/moneyball_core.py` atomic writers | Atomic/canonical publication patterns | SQLite needs canonical logical hash and integrity check, not byte identity |
| `fec/moneyball_core.py::NETWORKS` | Existing member-network configs only | Do not add staff; staff is an orthogonal overlay |
| `fec/network/build_multilayer_network.py` | None in initial staff build | Writes existing production workbook family; separate staff builder/loader required |
| `fec/collect/collector_supervisor.py` | Design ideas only | Interview-specific command, liveness, progress DB, and seven-day freshness; cannot accept simple staff target registration |
| `fec/tests/run_tests.py` | Test infrastructure | New test modules must be explicitly registered in a lane |
| `fec/paths.py` and path audit | Root/accessor pattern | Add staff-specific roots/accessors and extend path-resolution audit |

## 3. Architecture diagnosis

The durable model is an evidence graph, not a weighted social graph:

```text
immutable source bytes
        |
        v
source-native assertions -- exact source IDs, strings, locators, time semantics
        |
        v
reversible entity resolution -- persons, offices, organizations, institutions
        |
        v
canonical supported facts -- bitemporal, conflict-preserving
        |
        v
typed derived layers -- co-tenure, transitions, education affinity,
                        member overlay, lobbying/industry observations
```

This corrects the conceptual hierarchy in four ways:

1. Current/former staffer, legislator, and lobbyist are temporal roles of one person model.
2. Member offices and legislative terms anchor staff assertions to legislators without collapsing a member into an office.
3. Human lobbyists, registrants, and clients remain distinct; the filing supplies the relationship among them.
4. Education and title rank are contextual features, not inferred social contact or supervision.

## 4. Adjudicated design changes

| v2 proposal/problem | Ruling |
|---|---|
| Five-table canonical ledger without retained source assertions | Replace with raw/source-native, identity decision, assertion, canonical fact, and fact-support planes |
| One raw-record pointer per source entity | Add many-to-many `source_entity_observation`; conserve repeated snapshots/rows without duplicating identity |
| Canonical facts without system validity | Add consolidation build, system-time validity and supersession to facts/supports so replay and reversal are real |
| Current and former staff as separate node types | Model temporal roles/episodes on canonical persons |
| `w_x` based on legislator/member adjacency | Remove; it imports the parent graph into the staff layer and creates feedback risk |
| Title-derived `w_sup`/supervision | Rename to optional `TITLE_SENIORITY_DIFFERENTIAL`; never infer supervision without direct evidence |
| Education mixed into social composite | Keep a separate affinity/affiliation layer |
| Default `0.60/0.15/0.25` composite | Do not ship; preserve raw typed layers |
| Per-build global-max normalization | Reject as expansion/outlier unstable; use raw weights or a frozen reference-vintage transform later |
| LDA covered position supplies tenure/departure/decay | Reject; text is undated unless corroborated; structural link has temporal weight zero |
| Registrant joined to existing industry/client ID | Reject; use separate `lda_registrant_id` and `lda_client_id` namespaces/crosswalks |
| Payroll row equals continuous employment | Reject; payroll is an observation, episode consolidation is a versioned derivation |
| Exact month bounds and overlap | Preserve uncertain half-open bounds; guaranteed overlap uses inner bounds |
| Member overlay sums all supporting episodes | Union person/member intervals before aggregation; distinguish concurrent from sequential |
| Global `STAFF_NET` dial with `off`, `analysis`, and `engine` values | Initial values are only `off` and `analysis`; each engine consumer gets its own later contract/flag |
| Add staff to `NETWORKS` or production multilayer workbook | Separate artifact family, builder, and loader |
| Register collectors in existing supervisor | Use dedicated manifest-driven `fec/staffer_network/refresh.py` initially or separately generalize supervisor |
| Replace each output file independently | Publish an immutable generation directory and atomically swap a validated current-generation pointer last |
| Every metric arms when phase ships | Retire; exact invariants bind now, empirical quality bars require dated pilot/freeze packets |

## 5. Readiness by phase

| Phase | Status | Required before exit |
|---|---|---|
| 0 — contracts, roots, schema, fixtures, isolation | **PASSED; SEALED I-10a/I-11/P-1 RECEIPTS** | Exit complete. Keep the loader unarmed; later source/consumer failures do not reopen the contract exit |
| 1 — restricted seed, historic anchor, LDA, LittleSis | **REFERENCE/P-1 PREPARATION EXISTS; CANONICAL INGEST NOT APPROVED** | Require A-0/C-10a before a source-native legacy seed; require separate A-0/A-1 before raw Quorum; reconcile LDA mismatch/delta; acquire LittleSis entities; normalize pinned historic references |
| 2 — House/Senate public payroll breadth | **DESIGNED, NOT BUILT** | Report inventories, collectors/parsers, raw conservation, annotated pilots |
| 3 — restricted profile depth | **POLITICO CENSUS AND NORMALIZATION PASSED; SOURCE DISABLED** | Independently adjudicate profile/source-pair quality and approve redistribution-safe output; separately authorize every other licensed source |
| 4 — identity/container/date normalization | **FIRST CANDIDATE/REVIEW QUEUE BUILT; NOT CALIBRATED** | Double-reviewed calibration set, untouched source-pair holdout, precision/recall/abstention bars, UNITID/CIP resources |
| 5 — standalone graph artifacts | **BLOCKED BY UPSTREAM GATES** | Canonical facts, temporal admissibility, numerical invariants, ablation/null/sensitivity evidence |
| 6 — analysis-only loader | **NOT APPROVED** | Exact schema handshake and off-vs-absent isolation packet |
| 7 — engine consumers | **NOT APPROVED** | One accepted comparability/stability/rollback/claim packet per named consumer |

## 6. Blocking and nonblocking gaps

### Hard blockers for an affected source or arming

- LittleSis entity dump missing; relationships remain quarantined.
- The legacy directory is contact-free and P-1-remediated, but its internal derived-file authority and C-10a source-native import are unresolved; it remains disabled.
- Quorum raw-source authorization/retention is unresolved and the workbooks are not privately staged.
- LDA C-5 unique-UUID shortfall, duplicate disposition, and current 2026 delta are unreconciled even though page/hash integrity passes.
- No House SOD collector/corpus.
- No Senate report inventory/parser/corpus.
- Politico raw census acquisition and normalization are complete and authorized, but canonical use remains disabled pending independent source-pair/profile-quality adjudication and redistribution-safe output review; other licensed profile sources remain separately authority-gated.
- No accepted person-ER gold/holdout corpus; the 200-row strict queue is generated but unadjudicated. Covered-position parsing, general container resolution, and episode gold sets are also absent.
- No IPEDS/CIP reference snapshot or normalization evaluation.
- No per-consumer engine comparability/governance packet.

### Known gaps that do not reopen Phase 0 but block later gates

- Exact term files are pinned but not normalized/reconciled; historical committee membership remains absent beyond the current-membership snapshot and committee dictionaries.
- Committee side, physical office location, reporting lines, and employment fraction.
- Public payroll left-censoring before House 2009Q3 and Senate 2011 availability.
- Unpaid/fellow/detailee/contractor/intern omission from payroll.
- Foreign/high-school/closed-institution normalization outside IPEDS.
- Pre-2021 LDA historical first-disclosure backfill.

## 7. Exact first implementation backlog

### Immediate adjudication stage

1. Double-review the deterministic 200-row strict Politico↔legacy sample without changing the candidate rule; record match/distinct/possible outcomes and rationales in restricted storage.
2. Freeze calibration/holdout separation and add hard-name/common-name, office-evidence, title-conflict, and collision strata. A pooled strict-only sample cannot establish recall.
3. Emit a public-safe adjudication receipt with sample counts, agreement/conflict rates, precision confidence bounds, label-leakage audit, and zero canonical merges during evaluation.
4. Revise the source-pair rule only on calibration labels, then evaluate once on the untouched holdout. Keep Politico disabled unless the dated I-4/Q-1 freeze packet passes.

### Phase 1A pull request

1. After A-0 explicitly permits internal derived-file use, import the P-1-remediated contact-free directory as a source-native seed with 5,773/5,773 accepted rows and 533/533 represented offices. Only after a separate raw Quorum A-0/A-1 scope passes, implement raw `ingest_quorum.py`: conserve 6,773 physical observations, create/disposition 5,777 source IDs through many-to-one observation links, reproduce 5,773 current mappings, and reason-code the four additional IDs.
2. Implement historic member import from `HSall_members.csv` plus a pinned exact-term reference, preserving all 68 blank-Bioguide outcomes explicitly.
3. Implement `ingest_lda_covered_positions.py` against raw sweeps, preserving lobbyist ID ↔ position pairing, registrant/client namespaces, and filing/activity support.
4. Recollect/reconcile affected LDA query-years until unique UUIDs equal the frozen start/end inventory, explicitly disposition the 88 identical repeats, then collect the incremental 2026 delta through the existing collector.
5. Produce coverage and conservation receipts; do not emit weighted network edges.

### Phase 1B pull request

1. Acquire and hash the LittleSis entity dump matching the relationship dump.
2. Ingest entity and relationship files with exact conservation and 100% accepted endpoint referential integrity.
3. Emit only source-native assertions/candidates until resolution precision is frozen.

## 8. Proposed code/artifact map

```text
fec/staffer_network/
  schema.sql, source_manifest.py, identity.py, intervals.py, containers.py
  phase0_gates.py, privacy_audit.py, politico_normalize.py
  ingest_quorum.py, ingest_lda_covered_positions.py, ingest_littlesis.py
  build_ledger.py, build_edges.py, build_member_overlay.py, validate.py, refresh.py

fec/collect/
  collect_house_sod.py, collect_senate_disbursements.py

fec/network/
  build_staffer_network.py, staffer_network_loader.py

fec/audit/
  audit_staffer_network.py

fec/tests/staffer_network/
  test_schema.py, test_identity.py, test_intervals.py
  test_collectors.py, test_network.py, test_isolation.py

data/staffer_network/
  generations/<generation_id>/
    staffer_network_manifest.json
    staffer_network_coverage.json
    staffer_network_person_edges.ndjson.gz
    staffer_network_member_overlay.ndjson.gz
    staffer_network_industry_edges.ndjson.gz
  staffer_network_current.json
```

## 9. Metric diagnosis

The v3 metric system separates acquisition, parsing/ledger/resolution, graph computation, operations/legal, integration, and publication. `INVARIANT` marks immediate binding gates: exact raw-row conservation, non-vacuous source acceptance, key/referential/schema integrity, LDA pairing/namespaces, hard-date validity, temporal admissibility, PII exclusion/legacy quarantine, generation-level atomicity, and semantic determinism.

Parser, ER, normalization, stability, and claim thresholds remain `PILOT` until a dated freeze packet records the eligible denominator, sampling design, calibration/holdout separation, confidence rule, consequence, owner, and evidence receipt. A source failing a quality bar is quarantined without aborting unaffected corpus planes; a claim-gate failure suppresses the claim; an integration failure blocks arming.

## 10. Implementation acceptance checklist

Phase 0 evidence and all later corpus work are judged against these conditions:

- [x] No raw licensed/PII input is copied into the repository or synced project tree; legacy contact values were removed and recovery originals are restricted outside OneDrive.
- [x] Source assertions and canonical facts remain distinct and traceable in the schema/contracts.
- [x] Identity merges/splits are modeled as append-only and replayable; the current pilot performs zero merges.
- [x] Valid-time uncertainty and observed/system time remain separate.
- [ ] LDA lobbyist ID and covered-position pairs remain intact.
- [ ] Registrants and clients use distinct namespaces.
- [ ] Undated-only evidence receives zero temporal weight.
- [x] No direct person-contact, supervision, or influence claim is inferred from proxy data.
- [x] No default composite or current member adjacency enters the staff graph.
- [x] Staff code/artifacts remain outside existing production workbook/config families.
- [x] New tests are registered in the actual test runner.
- [x] `STAFF_NET` defaults off; `analysis` is the only other accepted value and engine use is rejected.

## 11. External authority references

- [House Statement of Disbursements](https://www.house.gov/the-house-explained/open-government/statement-of-disbursements)
- [Senate Report of the Secretary](https://www.senate.gov/legislative/common/generic/report_secsen.htm)
- [LDA API](https://lda.gov/api/), [documentation](https://lda.gov/api/redoc/v1/), and [terms/rate limits](https://lda.gov/api/tos/)
- [LittleSis bulk data](https://littlesis.org/bulk_data)
- [Congress Legislators data](https://github.com/unitedstates/congress-legislators)
- [NCES CIP resources](https://nces.ed.gov/ipeds/cipcode/resources.aspx)
- [NCES IPEDS Data Center](https://nces.ed.gov/ipeds/datacenter/Data.aspx)
- [Congress.gov API](https://api.congress.gov/)

## 12. Final diagnostic

Phase 0 is complete and evidence-backed: I-10a, I-11, and P-1 pass with sealed receipts, while the analysis loader remains unarmed. The authorized restricted Politico census and normalization exactly reproduce 18,618 people, 22,309 roles, and 20,485 issues from the sealed snapshot with zero contact findings and zero canonical merges. The first C-2 pilot accounts for all 5,773 legacy rows and creates a deterministic 200-row strict review queue, but with zero independent adjudications it cannot claim identity precision or enable the source. The historic spine is conserved and exact-term references are pinned, though legacy provenance keeps the relevant receipt at `REPORT`; LDA C-5 still fails unique-UUID coverage and moving-census evidence. The repository is ready for the adjudication/Phase 1 implementation stage, not canonical corpus publication. Quorum-derived seed/raw enablement still needs separate authority, and analysis plus every engine consumer remain unreachable pending source-specific quality gates, corpus completion, and explicit consumer approval.
