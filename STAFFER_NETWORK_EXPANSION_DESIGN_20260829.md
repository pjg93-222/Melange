# Staffer Network Expansion Design

**Version:** 3.0 adjudicated<br>
**Date:** 2026-08-29<br>
**Status:** Phase 0 exit passed with sealed isolation, atomicity, and privacy/license evidence; restricted Politico normalization passed and the first no-auto-merge resolution pilot reports; LDA C-5 remains failing and quarantined; not approved for canonical ingest, analysis, or engine arming<br>
**Supersedes as design authority:** the attached `STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md` v2 evidence document

## 1. Decision summary

Build a typed, bitemporal evidence corpus first. Build network layers only as reproducible projections of that corpus. Do not begin with a single weighted person graph.

The corrected hierarchy is:

```text
Person --HELD_TERM--> Legislative term --CONSTITUTES_OFFICE--> Member office
   |
   +--WORKED_AT-----------------------------------------------> Office / organization
   +--NAMED_ON_ACTIVITY--> LDA activity --FILED_BY-----------> Registrant
   |                                  +--FOR_CLIENT----------> Client
   |                                  +--CONTACTED-----------> Chamber / agency
   +--ATTENDED / EARNED_CREDENTIAL_AT------------------------> Institution
```

Legislator, current staffer, former staffer, and lobbyist are temporal roles of a person. They are not disjoint entity classes. Industry actors include human lobbyists, registrants, clients, affiliated organizations, and foreign entities; a lobbying firm is not interchangeable with the client it represents.

The first release is an analysis-only, opt-in staff layer. It must not alter the existing member-network family when disabled. Engine use requires a later, named consumer-by-consumer approval packet.

## 2. Scope and non-claims

### In scope

- Current and historical congressional employment assertions.
- Member personal offices, committees, leadership, chamber administrative offices, and other governmental containers.
- Lobbyist filing observations, registrants, clients, lobbying activities, issues, bills, and disclosed covered-position text.
- Education assertions and normalization to institutions and programs where support exists.
- Reversible person, organization, office, and institution resolution.
- Derived co-tenure, transitions, shared-personnel member overlays, education affinity, and revolving-door evidence.

### Out of scope for initial arming

- Causal claims about access, influence, policy outcomes, or lobbying effectiveness.
- Inferring direct contact with a legislator or staffer from an LDA activity.
- Inferring supervision or reporting lines from title rank.
- Treating shared education as proof of acquaintance.
- Treating payroll observations as complete employment episodes without consolidation rules.
- Treating an undated LDA covered position as a dated departure or employment interval.
- A default composite that collapses substantively different relation layers.

## 3. Design invariants

1. **Assertions precede facts.** Preserve every accepted source assertion and its locator before consolidation.
2. **Valid time differs from observed time.** Employment time, source publication time, retrieval time, and system decision time remain distinct.
3. **Source IDs are not canonical IDs.** Canonical entities use opaque stable IDs; names are attributes and blocking features only.
4. **Roles may overlap.** A person may simultaneously or sequentially be a legislator, staffer, lobbyist, candidate, or employee of another organization.
5. **Resolution is reversible.** Merge, distinct, possible, and split decisions are append-only, replayable, and supported by evidence.
6. **Uncertainty survives derivation.** Missing or coarse dates are not silently converted to exact dates.
7. **Every derived edge is traceable.** Each edge carries a build ID, derivation version, support digest, and support links.
8. **Relations stay typed.** Co-tenure, sequence, education similarity, and lobbying transitions remain separate layers.
9. **No graph PII.** Email, phone, address, and unnecessary education detail are excluded from canonical network outputs.
10. **Disabled means absent.** With `STAFF_NET=off`, no production reader opens a staff artifact and existing output hashes remain unchanged on frozen inputs.

## 4. Entity and predicate model

### 4.1 Entity kinds

- `person`
- `organization`
- `legislative_term`
- `office`
- `committee`
- `lda_filing`
- `lda_activity`
- `issue`
- `bill`

`institution` is an organization subtype. Office/container subtypes include member personal office, committee/subcommittee, chamber leadership, congressional officer/administrative office, executive agency, campaign, registrant, lobbying client, private employer, nonprofit/academic, state/local government, and school.

### 4.2 Observed predicates

| Subject | Predicate | Object |
|---|---|---|
| Person | `HELD_TERM` | Legislative term |
| Legislative term | `CONSTITUTES_OFFICE` | Member office |
| Person | `WORKED_AT` | Office or organization |
| Person | `NAMED_ON_ACTIVITY` | LDA activity |
| LDA activity | `FILED_BY` | Registrant organization |
| LDA activity | `FOR_CLIENT` | Client organization |
| LDA activity | `CONTACTED` | Chamber or agency |
| LDA activity | `CONCERNS` | Issue or bill |
| Person | `ATTENDED` | Institution |
| Person | `EARNED_CREDENTIAL_AT` | Institution |

### 4.3 Derived predicates

- `CO_TENURE`: supported overlapping work at the same container.
- `OFFICE_TRANSITION`: sequential service across Hill containers.
- `HILL_TO_LOBBYING_TRANSITION`: dated Hill service followed by a supported lobbying observation or private-sector episode.
- `SHARED_PERSONNEL`: member-office projection through the same canonical person.
- `EDUCATION_AFFINITY`: institution/program/time similarity, explicitly not a social tie.
- `TITLE_SENIORITY_DIFFERENTIAL`: optional title-derived feature, not `SUPERVISED`.

Observed and derived predicates must use separate namespaces or an explicit `is_derived` field.

## 5. Bitemporal assertion ledger

The ledger is a local, queryable build artifact. It is not the sole system of record; immutable raw bytes plus manifests are the source record.

### 5.1 Provenance tables

```text
source_system(
  source_system_id, name, authority_scope, terms_uri, license,
  redistribution_class, authorization_status
)

ingest_run(
  run_id, source_system_id, collected_at, source_as_of,
  query_json, collector_version, parser_version,
  expected_count, observed_count, accepted_count, rejected_count,
  completeness_status, manifest_sha256
)

raw_record(
  raw_record_id, run_id, source_record_type, source_record_key,
  source_uri, blob_sha256, media_type,
  source_created_at, source_updated_at, locator_json
)
```

`locator_json` stores a JSON pointer, CSV/workbook row, PDF page and bounding box, or HTML selector as appropriate.

### 5.2 Identity tables

```text
entity(entity_id, entity_kind, created_system_at, retired_system_at)

source_entity(
  source_entity_id, source_system_id, entity_kind,
  source_key, first_raw_record_id
)

source_entity_observation(
  source_entity_id, raw_record_id, observed_at,
  observation_role
)

resolution_decision(
  decision_id, left_source_entity_id, right_source_entity_id,
  decision, method, model_version, score,
  adjudicator, rationale, system_from, system_to
)

entity_membership(
  source_entity_id, entity_id, decision_id, assignment_method,
  system_from, system_to
)

identifier_assertion(
  assertion_id, entity_id, namespace, identifier,
  source_entity_id, system_from, system_to
)
```

`decision` is one of `MATCH`, `DISTINCT`, `POSSIBLE`, or `SPLIT`. A normalized SOD name-office tuple is a blocking feature, not an identifier assertion.

`assignment_method` is `SOURCE_NATIVE` for the first source entity admitted to a canonical entity and `RESOLUTION` for later cross-source membership. `decision_id` is null only for `SOURCE_NATIVE`; this prevents inventing a fake pairwise match merely to seed an entity.

### 5.3 Relation assertions and facts

```text
relation_assertion(
  assertion_id, subject_source_entity_id, predicate,
  object_source_entity_id, literal_json,
  valid_start_earliest, valid_start_latest,
  valid_end_earliest, valid_end_latest,
  start_precision, end_precision, asserted_current,
  observed_at, system_from, system_to,
  raw_record_id, extraction_method,
  extraction_confidence, parser_version
)

canonical_fact(
  fact_id, subject_entity_id, predicate, object_entity_id,
  literal_json,
  valid_start_earliest, valid_start_latest,
  valid_end_earliest, valid_end_latest,
  fact_status, consolidation_build_id,
  system_from, system_to, supersedes_fact_id
)

fact_support(
  fact_id, assertion_id, support_role,
  system_from, system_to
)
```

`source_entity_observation` permits repeated source snapshots/rows for one stable source key without duplicating the source entity or losing provenance. Source-native tables preserve lossless fields before canonicalization, including `payroll_observation`, `profile_employment_claim`, `profile_education_claim`, `lda_filing`, `lda_activity`, and:

```text
lda_activity_lobbyist_observation(
  observation_id, raw_record_id, activity_source_entity_id,
  lobbyist_source_entity_id, occurrence_ordinal,
  covered_position_raw, new_flag, observed_at,
  system_from, system_to
)
```

The LDA lobbyist ID and its covered-position string must remain paired. Flattening names and positions into independent lists is forbidden.

### 5.4 Time semantics

Intervals are half-open: `[start, end)`. Uncertain bounds retain four values:

- start is in `[start_earliest, start_latest]`
- end is in `[end_earliest, end_latest]`

For assertions `a` and `b`, guaranteed overlap is:

```text
max(0,
    min(a.end_earliest, b.end_earliest)
    - max(a.start_latest, b.start_latest))
```

Possible overlap may be reported separately using outer bounds. Open or source-asserted-current intervals are right-censored at that source snapshot and clipped to the build `as_of`; they are not proven current after the snapshot. Month/year precision remains uncertain rather than becoming an exact first-of-period date. A documented source/export `as_of` is used when available. Filesystem modification time is never valid time; if a source timestamp is absent, retain receipt/collection time as observed time and leave valid time unknown.

A payroll row is evidence of compensated service in its performance interval. A canonical employment episode is a later derivation with a versioned gap rule and explicit assertion support.

## 6. Identity resolution and adjudication

### 6.1 Stable keys

- Persons: opaque `person_id`; source keys include Quorum IDs, LDA lobbyist IDs, Politico UUIDs, LittleSis entity IDs, and Bioguide IDs when the person is a member.
- Member offices: term-valid `bioguide_id + congress/chamber/service interval` container key.
- Registrants: `lda_registrant_id` namespace.
- Clients: `lda_client_id` namespace, optionally crosswalked to existing organization axes.
- Institutions: IPEDS `UNITID` where eligible; a separate namespace for foreign, secondary, historical, or unresolved institutions.
- Programs: CIP vintage plus code when a supported major maps.

Never silently join `lda_registrant_id` to the existing client-oriented `lob_id` plane.

### 6.2 Resolution pipeline

1. Normalize source-native names and organization strings without destroying originals.
2. Generate candidates with source IDs, term-valid offices, name variants, titles, email/phone hashes where authorized, dates, schools, and employers.
3. Apply deterministic exact rules first.
4. Score remaining candidates with a versioned model/rule set.
5. Auto-accept only under a frozen, source-pair-specific threshold.
6. Queue common-name, high-degree, conflicting-date, and cross-role cases for adjudication.
7. Persist positive and negative decisions; retain unresolved candidates.
8. Support later split/undo and replay all derived facts.

Names are never keys. The current directory contains duplicate display names, so name-only bridges are candidate generators only.

### 6.3 Required adjudication queues

- person identity
- member-office and historic-member parsing
- committee/office/container normalization
- registrant/client/organization resolution
- interval conflicts and implausible concurrency
- UNITID and CIP mapping
- source amendments/retractions

Each decision records status, owner, evidence references, rationale, decision time, and supersession link. A double-reviewed subset is reserved for agreement measurement; calibration and final holdout labels remain separate.

## 7. Derived network contract

### 7.1 Network build tables

```text
network_build(
  build_id, as_of, corpus_manifest_sha256,
  config_json, derivation_version
)

network_edge(
  edge_id, build_id, layer, predicate,
  subject_entity_id, object_entity_id, directed,
  raw_weight, scaled_weight, evidence_class, precision_bucket,
  support_count, support_digest
)

network_edge_support(edge_id, fact_id, contribution)
```

### 7.2 Layer rules

**Co-tenure.** Produce person-person edges only from supported employment at the same normalized container. Preserve same-office location where known. Weight may use guaranteed overlap days. Possible-only overlap is a separate uncertainty feature and is not substituted for guaranteed overlap.

**Title seniority.** Title taxonomy may yield `TITLE_SENIORITY_DIFFERENTIAL`; it never yields `SUPERVISED` without direct evidence. This feature defaults off.

**Education affinity.** Produce a similarity/affiliation layer with institution, program, and supported temporal fields. It is not evidence that two people met.

**Office transitions.** Distinguish simultaneous multi-office support, sequential staff migration, member-to-staffer transitions, and committee/personal-office transitions.

**Revolving door.** A dated Hill episode plus a later dated lobbying/private-sector observation may produce a temporal transition. LDA covered-position text alone is undated: it may create a structural evidence link with temporal weight zero, but cannot supply tenure duration, exit date, decay, or ordering.

**Member overlay.** Project through canonical persons to Bioguide-keyed member offices. Union each person's supported intervals per member before aggregation to prevent duplicate-source double counting. Keep concurrent shared staffing separate from sequential movement. Report contributing persons and support digests.

**Industry overlay.** Preserve human lobbyist, registrant, and client as distinct nodes/roles. LDA establishes a filing/activity relationship on behalf of a client, not influence or direct contact with an individual.

### 7.3 No default composite

Do not ship the v2 `0.60/0.15/0.25` composite. Remove member-adjacency-derived `w_x` from the staff graph because it imports the legislator network into a staff relationship and creates feedback risk. Preserve raw sublayers.

If a later use case needs a composite, it must have a dated calibration packet, frozen coefficients, source-ablation results, and a fixed reference-vintage scaling transform. Do not normalize by each build's global maximum.

## 8. Storage and artifact layout

### 8.1 Machine-local, restricted data

```text
%LOCALAPPDATA%\Melange\staffer_network\
  raw\{quorum,house_sod,senate_disbursements,politico,littlesis,reference}\
  normalized\
  ledger\staffer_ledger.db
  adjudication\
```

Existing LDA raw sweeps remain under `%LOCALAPPDATA%\Melange\lda_rebuild\raw\sweeps`; reference them by manifest rather than copying them.

Authenticated/licensed material and contact PII stay outside the repository and synced project tree. The existing untracked `data/members/staff_directory.json` is a known restricted legacy exception: it contains contact fields in the synced tree, is quarantined from the staff layer, and must receive an authority/retention ruling plus a remediation record. It is not a compliant public-safe seed. Salted contact hashes may be used locally for resolution when authorization permits; they are not exported.

### 8.2 Repository-safe outputs

```text
data/staffer_network/
  generations/<generation_id>/
    staffer_network_manifest.json
    staffer_network_coverage.json
    staffer_network_person_edges.ndjson.gz
    staffer_network_member_overlay.ndjson.gz
    staffer_network_industry_edges.ndjson.gz
    staffer_network_adjudication_summary.json
  staffer_network_current.json
```

All published records are sorted canonically. JSON serialization, numeric formatting, record order, and gzip `mtime=0` are fixed. The Phase 0 generation manifest contains record-level JSON Schema IDs/hashes, source manifest hashes, derivation version, `as_of`, record counts, content hashes, and privacy classification. Source-producing generations additionally bind a hashed canonical derivation config and explicit metric-receipt references before source enablement.

SQLite byte identity is not required. Determinism is evaluated through a canonical ordered logical dump and canonical derived artifacts. A build writes and validates an entire immutable generation directory first. It atomically replaces `staffer_network_current.json` last; the pointer identifies one generation and repeats its manifest hash. The loader verifies the selected manifest, every advertised schema, file hash, and record count before returning any record. Incomplete generations are unreachable and may be garbage-collected later. SQLite targets use sibling temporary files, close, pass `PRAGMA integrity_check`, and publish with `os.replace` before the generation becomes selectable.

## 9. Code and integration layout

```text
fec/staffer_network/
  schema.sql
  schemas/
    generation_manifest.schema.json
    coverage.schema.json
    person_edge.schema.json
    member_overlay.schema.json
    industry_edge.schema.json
  source_manifest.py
  phase0_gates.py
  privacy_audit.py
  politico_normalize.py
  identity.py
  intervals.py
  containers.py
  ingest_quorum.py
  ingest_lda_covered_positions.py
  ingest_littlesis.py
  build_ledger.py
  build_edges.py
  build_member_overlay.py
  validate.py
  refresh.py

fec/collect/
  collect_house_sod.py
  collect_senate_disbursements.py

fec/network/
  build_staffer_network.py
  staffer_network_loader.py

fec/audit/
  audit_staffer_network.py

fec/tests/staffer_network/
  test_schema.py
  test_identity.py
  test_intervals.py
  test_collectors.py
  test_network.py
  test_isolation.py
```

Extend `fec/lobbying/collect_lda_filings.py` for a reconciled delta/backfill; do not create a second LDA collector. Reuse atomic-output, receipt, canonical-hash, and effective-dated organization identity idioms where appropriate.

Add explicit roots/accessors to `fec/paths.py`. Register the new test suite in `fec/tests/run_tests.py`; directory discovery alone does not execute it. Extend path-resolution auditing to the new domain.

Do not add the staff layer to `fec/moneyball_core.py::NETWORKS`; that registry selects mutually exclusive member-network configurations. Do not initially modify `fec/network/build_multilayer_network.py`, which writes the existing production workbook family. Staff artifacts live in a separate subdirectory and filename family.

## 10. Enablement and isolation

Initial runtime dial:

```text
STAFF_NET=off       # default; loader not invoked; no artifact opened
STAFF_NET=analysis  # explicit read-only analytical overlay
```

There is no global `engine` value. Each later engine consumer must receive a separate feature flag, artifact/schema contract, frozen-input comparison, impact analysis, rollback path, and approval receipt.

Isolation tests must instrument file opens, enumerate production readers rather than all repository `rglob` uses, and compare an explicit existing-output manifest for `off` versus staff artifacts physically absent. Staff build/collection does not enter the canonical extraction chain until its own source, privacy, determinism, and isolation gates pass.

## 11. Implementation phases and exits

### Phase 0 — contracts and negative controls

- Ratify this design, corpus specification, and metric lifecycle.
- Implement roots, source manifest, schemas, canonical serialization, and privacy classes.
- Add test-runner registration, path audit coverage, schema fixtures, and off/absent negative controls.
- Define source-specific receipts and a dedicated `fec/staffer_network/refresh.py`; do not register targets into the current interview-specific supervisor.

**Exit:** **PASSED 2026-08-30.** Schema/reference/invariant tests pass; the complete P-1 repository privacy/license scan, I-10a production-reader/output-hash/physical-absence packet, and I-11 clean/incremental/SQLite-integrity/pointer-fault packet have sealed passing receipts; no analysis or engine loader is armed. The registered kernel lane passed 169/169 before the Politico normalizer tests were added, and the expanded focused staffer suite passes 42/42.

### Phase 1 — restricted seed gate, public references, and LDA

- The 5,773-row/533-office directory is now a contact-free restricted legacy Quorum-derived input. P-1 records the quarantine/remediation, and the three synced surfaces contain zero email/phone fields; hash-verified originals remain in restricted machine-local quarantine. Do not enable or import it through the new staff layer until A-0 records an authority scope for internal derived-file use.
- Once that scope passes, create a stripped source-native seed containing only authorized fields and excluding email/phone/contact hashes. C-10a requires all 5,773 rows accepted and all 533 offices represented; outcome conservation alone is insufficient.
- Raw-workbook enrichment requires its own A-0/A-1 scope. After it passes, stage the eight workbooks in the restricted raw root, conserve all 6,773 physical rows, create or disposition all 5,777 source IDs, reproduce the 5,773 current office mappings, and reason-code the remaining four source IDs. Until then, raw Quorum enrichment is quarantined.
- Load `votes/HSall_members.csv` as a broad historical member spine and pin current/historical `congress-legislators` data for exact service dates and committee crosswalks, reconciled to official identifiers.
- Reconcile the 2021–2026 LDA sweep manifests to raw pages, refresh the 2026 delta, preserve lobbyist-position pairing, and materialize full-sweep assertions.
- Acquire the matching LittleSis entities dump; ingest entities and relationships only when referential checks pass.

**Exit:** A-0/A-1 and non-vacuous acceptance coverage pass for every enabled source; raw-to-normalized conservation, source-key uniqueness, historic roster coverage, PII, and LDA pairing gates pass. LittleSis remains quarantined until the entity spine is present. Quorum-derived seed output remains absent until its authority scope and stripped-seed C-10a/P-1 gates pass; raw enrichment is independently optional and quarantined until authorized.

### Phase 2 — public payroll breadth

- Census and collect House SOD from 2009Q3 through the last complete quarter.
- Census all available Senate Secretary report parts from April 2011 onward.
- Develop parsers against annotated gold pages/rows and preserve reject records.
- Derive employment episodes only after source-specific semantics and gap rules are frozen.

**Exit:** acquisition gates pass; parser precision/recall bars are frozen from pilots; affected sources remain quarantined until then.

### Phase 3 — restricted profile depth

- Politico extraction authority is satisfied by the user's attestation of a physical permission letter. The 2026-08-29 party-partitioned directory census acquired 18,618/18,618 unique UUID records under a four-worker/60-request-per-minute ceiling, with observed maxima of four in flight and 28 requests per rolling minute and zero retained contact fields. A deterministic restricted normalizer now reproduces 18,618 source-person records, 22,309 role assertions, and 20,485 issue assertions with exact conservation and no contact findings or canonical merges. Raw names, UUIDs, roles, issue areas, and resolution candidates remain machine-local. The source stays disabled for canonical publication until independent identity adjudication, profile-quality evaluation, and redistribution-safe output contracts pass. Other licensed profile sources and any Quorum raw/profile enrichment not authorized in Phase 1 follow the same gates here.
- Keep these raw and normalized records machine-local; export only permitted aggregate/derived fields.

**Exit:** source authorization and PII policies pass; profile metrics have a frozen census and holdout.

### Phase 4 — entity resolution and normalization

- The first Politico↔legacy exact-name candidate set and deterministic 200-row strict review queue now exist: all 5,773 legacy rows are dispositioned, 4,836 unique-name candidates were emitted, and no merge was applied. Next, independently adjudicate stratified calibration and untouched holdout samples; the current queue has no precision claim.
- Resolve containers, registrants/clients, institutions, and programs.
- Consolidate employment episodes with support links and bitemporal replay.

**Exit:** ER/container/date/normalization gates pass by source pair and hard-name stratum; unresolved records remain visible.

### Phase 5 — standalone network computation

- Emit separate person, member-overlay, and industry layers.
- Run temporal nulls, source ablations, uncertainty sensitivity, deterministic rebuild, and fault-injection tests.

**Exit:** graph invariants, robustness, semantic determinism, and claim gates pass. No production reader is changed.

### Phase 6 — analysis-only loader

- Add the explicit analysis loader and schema handshake.
- Prove `off` versus absent equivalence over frozen inputs and instrumented file opens.

**Exit:** integration and isolation packet accepted. Analysis-only use may arm.

### Phase 7 — named engine consumers

- Evaluate and approve each consumer independently.

**Exit:** per-consumer comparability, stability, rollback, governance, and claim packet accepted. There is no automatic promotion from analysis.

## 12. Resolved design questions

- Former and current staff are states/intervals of the same person model, not separate node classes.
- Industry is modeled through distinct person, registrant, and client roles.
- Committee staff and personal-office staff use typed containers; unknown side/location remains unknown.
- Title rank is a seniority proxy, not supervision.
- Education is an affinity layer, not a social edge.
- LDA covered positions remain undated unless another source supplies dates.
- Existing legislator adjacency does not create staffer edges.
- The canonical graph is multiplex; a composite is optional and later.
- Historic member resolution is term-valid and combines the existing `HSall_members.csv` spine with pinned service-date sources.
- Raw/private corpus lives outside the repository; safe deterministic projections may be checked in.
- Analysis and each engine consumer arm independently.

## 13. Remaining policy decisions

These do not reopen the passed Phase 0 contract exit, but they block the affected source or later arming:

- Long-term Politico retention/refresh cadence and any numeric rate ceiling supplied later; Quorum/LegiStorm authorization, extraction mode, retention, and redistribution.
- Whether public-safe derived education detail may be published below institution/program aggregates.
- Long-term raw retention and deletion policy for licensed/PII-bearing sources.
- Exact committee-history authority and effective-date reconciliation.
- Numeric quality thresholds after pilots; thresholds do not auto-freeze when a parser ships.

## 14. Acceptance statement

This design has passed the Phase 0 contract exit and now includes nonrestricted historic-reference preparation, a complete restricted Politico directory census, a deterministic restricted normalization corpus, and a report-only identity-resolution pilot. The next implementation stage is independent adjudication of the source-pair queue while LDA C-5 is reconciled and pinned term references are normalized. Public payroll collector/parser work may proceed independently behind the same source gates, but no source-native records may enter a canonical generation until its authority, conservation, privacy, normalization, and applicable quality contracts pass. Quorum-derived seed enablement, raw Quorum enrichment, canonical Phase 1 exit, corpus completeness, calibrated weights, and access by any analysis/engine consumer remain explicitly metric-gated.
