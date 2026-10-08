# Staffer Network Expansion — Post-Build Implementation Diagnostic

**Date:** 2026-08-30  
**Assessment:** **CANONICAL FACTS, TYPED GRAPH, NETWORK SCORES, AND RECEIPT-VERIFIED ANALYSIS LOADER ARE IMPLEMENTED; ALL SOURCES ARE ENABLED FOR INTERNAL ANALYSIS; IDENTITY CANDIDATES REMAIN NONCANONICAL; PUBLIC RELEASE REMAINS SOURCE-GOVERNED**

## 0. Closure diagnostic (2026-08-31 UTC)

This section supersedes the pre-build assessment in Sections 1 onward. Those
sections are retained as the historical baseline that motivated the build.

- Canonical v6: `PASS`, 1,585,038 singleton entities, 6,050,221 valid facts,
  6,978 reversible identity links, zero cross-source memberships or merges;
  source states are derived from authority manifest SHA `e7c56c1a…3352f`.
  Active root: `canonical/generation-20260831T042000Z`; fact SHA-256
  `d9c34371…9a3d84`.
- Source anomaly adjudication: 44 LittleSis self-loops retained in source-native
  evidence but excluded and counted at canonical promotion.
- Typed graph v6: `PASS`, 5,260,888 evidence edges and 1,585,038 score rows;
  23,022 repeated unordered endpoint/layer supports are excluded, leaving
  5,235,347 primary scoring keys. Active root:
  `graph/generation-20260831T052000Z`; the edge SHA-256 remains
  `8c27a6c4…8d0ecd` and the guarded score SHA-256 is
  `cda3fc07…3352aa2`.
- Primary connectedness: candidate-free, entity-kind-balanced PageRank; all
  damping runs converged below `1e-11` L1 residual.
- PageRank isolate guard: score rows explicitly carry `primary_isolate` and
  `exploratory_isolate`. Teleport-only isolate values remain mathematically in
  the stationary distribution but must be filtered from connectedness ranks.
- Exploratory connectedness: adds only 2,519 strict one-to-one exact-name review
  candidates and is explicitly not an identity or influence finding.
- Eigenvector: component-local diagnostic; four nonconverged components (585
  nodes) are null. Values are not comparable across components and it is not
  used as the primary score.
- Bridging: normalized Simpson layer-balanced neighbor-kind diversity, separate
  from strength and not directly comparable across incompatible entity kinds.
- Composite influence: deliberately absent (`null`) because no validated unit
  model justifies combining centralities.
- Loader: `STAFF_NET=analysis` verifies immutable receipt, roles, sizes, and
  hashes before returning artifact paths. Default `off` remains a zero-read
  branch.
- Implementation test gate: 107 tests and 53 schema subtests pass.
- Contact gate: entity and score scans pass with zero phone/email-pattern hits;
  68 empty LDA covered-position literals are dispositioned separately.
- Opus 5 final adversarial review: `PASS`. Its temporal follow-up is closed:
  all 11,758 undated Politico member-role weights are zero and the builder
  enforces zero for every `undated-only` fact. Duration math remains unbuilt
  pending dated episodes and resolved identity evidence.
- Exact temporal delta audit: all 6,050,221 v5/v6 fact rows compared in order;
  exactly 11,758 differed, every difference was solely `temporal_weight` 1→0
  on an undated Politico `STAFFS_FOR` assertion, and bad differences were zero.
- Exact graph score audit: all 1,585,038 v5/v6 rows compared; primary/exploratory
  isolate counts were 185,628/185,221 with zero flag inconsistencies, zero
  contact hits, and zero nonnumeric differences. Removing redundant row
  renormalization changed numerical cells only at floating roundoff scale
  (maximum absolute delta `3.55e-14`).

The older 99-test/69-subtest figures later in this diagnostic are milestone
history from a differently parameterized suite, not a regression baseline. The
current integrated suite is 107 tests and 53 subtests and is the binding gate.

LittleSis is no longer compute-disabled: `frozen` means only that its exact
input vintage is pinned. Politico Pro is enabled for internal normalized use by
the v3 manifest. Neither activation removes privacy minimization, turns a
candidate into identity truth, or asserts a right to redistribute raw source
rows publicly.

## 1. Executive ruling

The requested corpus expansion has materially advanced from design evidence to
two separately conserved source-native generations. The 873,236-row P2 corpus
spans the LittleSis entity spine, selected source-native relationships, and the
contact-free legacy staff seed. The separate 6,682,108-row LDA corpus spans
541,659 reconciled filings and their lobbyist, organization, activity,
filing-participation, and covered-position assertions. A 6,978-row restricted
exact-name artifact is a review queue only. All 13 staffer-network test modules
pass: 99 tests and 69 subtests; 37 schemas are registered.

The result is ready for source-ledger loading, human resolution evaluation,
covered-position semantic work, historic member normalization, and public
payroll collection. It is not ready for a canonical person graph or analytical
use. Cross-source identity assertions and canonical merges remain zero;
candidate confidence is null; `STAFF_NET=off`.

## 2. Evidence treatment

The two attached Downloads documents were treated as evidence, not
instructions, and were not modified. Their hashes differ from the later
workspace adjudications. All 2026-08-29 workspace specifications and the prior
diagnostic remain unchanged as historical records. The 2026-08-30 documents are
new dated authorities.

## 3. Measured evidence

| Evidence | Measured result | Diagnostic consequence |
|---|---|---|
| Restricted legacy seed | 5,773/5,773 rows; 533/533 offices; zero contact fields; exact output hash `439bb67f…a17ff48` | C-10a invariants pass within provisional restricted A-0; no raw Quorum/canonical/analysis authority |
| LittleSis raw pair | 443,140/443,140 entities; 1,880,491 relationships; 1,880,488 accepted; three dangling rejects; zero invalid/duplicates | C-6 conservation and accepted-endpoint integrity pass for restricted source-native ingest |
| Category adjudication | Category 5 is Donation (1,267,716), not Lobbying; category 7 is Lobbying (10,655) | The material 2026-08-29 category error is corrected; donation records are not ingested as lobbying assertions |
| Source-native corpus | 443,140 entities; 368,995 Position + 44,673 Education + 10,655 Lobbying = 424,323 assertions; 1,456,165 explicit out-of-scope dispositions; 5,773 legacy rows | 873,236 emitted records; exact source-boundary conservation; zero silent drops |
| Temporal/minimization | 226,370 undated Positions; temporal weight nonzero count 0; 38 contact-like free-text and two dangling parent references redacted; zero boss redactions | P-1/C-9 pass for this source-native scope; no duration/currentness claim |
| Determinism | Initial real twin differed by one byte due alias case-fold ties; defect recorded and fixed with total ordering; two fresh real twins byte-identical across all four files | I-16 passes same machine/environment; prior failure remains visible; cross-machine determinism not evaluated |
| Full validation | 873,236/873,236 rows pass public-safety, schema, and semantic checks; upgraded validation re-passed the accepted local generation under the registered legacy row schema and receipt hash `3914df98…604e2` | I-1 and restricted source-native R-2 pass |
| Politico dual-model review | 400 model-assisted labels; 100/100 calibration exact agreement and 100 consensus MATCH; holdout outcomes unpublished/evaluation count 0; human gold 0; precision null | Consistency REPORT only. All-positive/easy stratum cannot freeze Q-1/I-4; source stays disabled |
| LDA legacy audit | 539,870 objects, 539,782 unique UUIDs, 88 identical repeats, moving count evidence | Historical defect evidence remains quarantined; the reconciled composite, not the legacy sweep alone, owns final C-5 PASS |
| LDA fresh attempt 1 | Failed safely at 2022 page 10 after five HTTP 503s; before/after legacy inventory identical | Safe-fail verified; no partial generation promoted |
| LDA composite reconciliation | `PASS`; receipt SHA `0f985e79…c0b250`; 541,659 unique filings through cutoff-exclusive 2026-08-30; 12 twin windows; six yearly counts; zero shortfall/cross-year duplicate UUIDs; unchanged legacy seal `d7304591…94961e`; registered 120 RPM/page 25/eight in flight; one hash-bound resume after DNS error | C-5 closes as PASS. Earlier failed/incomplete attempts remain visible and unpromoted |
| LDA source-native corpus | Receipt SHA `5dfd3bbb…9dce8c`; 25,340 lobbyists; 54,073 organizations; 1,037,547 activities; 4,816,559 filing-participation edges; 748,589 covered-position assertions; all 6,682,108 rows independently validated | Restricted source-native ledger input passes; identity, transition, analysis, and publication remain closed |
| LDA identity candidates | Receipt SHA `b8be6326…e1f4a`; 6,978 review rows: LittleSis 6,313, Politico 446, legacy 219; 4,741 unique LDA lobbyists; 5,526 unique targets; 3,910 normalized keys; 4,459 collision rows; 3,345 cross-source multiplicity rows | Review queue only; confidence null/zero emitted; zero canonical merges |
| Test integration | 13/13 staffer modules; 99/99 tests; 69 subtests | Code, schema registry (37 schemas), receipts, negative controls, and main-runner registration integrate |

## 4. Architecture diagnosis

The correct hierarchy is institutional and temporal:

```text
legislator + term -> member office / committee
                         ^
                         |
               supported employment assertion
                         |
                 person with temporal roles
                         |
        organization / registrant / client / school / activity
```

This is preferable to a strict parent-child graph. Legislators anchor effective
offices; staff/current/former/lobbyist are roles of people; organizations and
filed activities anchor industry evidence. The design avoids identity collapse,
feedback from the existing legislator network, and proxy claims of contact or
influence.

The evidence planes remain:

```text
source bytes -> source-native assertions -> resolution decisions
             -> canonical supported facts -> typed graph layers
```

Both the P2 and LDA source-native planes have passed for their separately
declared generations. The candidate plane is a `REPORT`, not identity truth.

## 5. Metric adjudication

| Metric | Final 2026-08-30 state |
|---|---|
| C-6 LittleSis | `PASS`, restricted source-native only; quality bar unfrozen; source disabled; ShareAlike publication review open |
| C-10a legacy seed | `PASS` for conservation/coverage/PII; A-0 provisional pending Paul ratification |
| R-2 source-native | `PASS` with counted redactions/dispositions; canonical ledger not evaluated |
| I-1 source-native integrity | `PASS`, 873,236 complete row validations |
| I-16 same-machine twin byte determinism | `PASS` after recorded remediation; distinct from I-11 |
| Q-1 model-assisted reliability | `REPORT`; degenerate all-MATCH calibration; human validity not evaluated |
| I-4 entity resolution | `NOT_EVALUABLE`; human gold 0, precision null, recall universe absent |
| C-5 LDA | `PASS`; composite acquisition/reconciliation through cutoff-exclusive 2026-08-30 |
| C-5b/C-5c LDA source-native | `PASS` for conservation and integrity; covered-position semantics and transition derivation remain `NOT_EVALUABLE` |
| C-5d LDA identity candidates | `REPORT`; restricted review-required exact-name candidates; confidence null; zero merges |
| House/Senate payroll metrics | `NOT_EVALUABLE`; sources and parsers not built |
| Analysis/consumer/publication | `CLOSED` |

## 6. What is ready to implement

The following work has a stable evidence base and can proceed without changing
canonical production outputs:

1. A source-native ledger importer for the validated LittleSis/legacy files,
   preserving namespaces, record hashes, raw dates, dispositions, and zero
   cross-source identity decisions.
2. Historic member/term normalization from the pinned reference spine, with 68
   blank-Bioguide outcomes retained and no current committee back-projection.
3. A human adjudication packet spanning negative, hard-name, collision,
   title-conflict, and missing-office strata. Calibration may revise the rule;
   the sealed holdout is evaluated once.
4. House SOD and Senate report inventory/collector/parser implementation behind
   raw conservation and annotated-gold gates.
5. Human adjudication of the restricted LDA identity candidates and explicit
   covered-position semantic evaluation before any transition derivation.
6. A manifest-driven staff refresh supervisor that records locks, progress,
   rate/retry policy, freshness, reconciliation, and terminal receipts.

## 7. Blocking gates

### 7.1 LDA evidence and industry transitions

C-5 acquisition/reconciliation is closed as PASS. Receipt SHA
`0f985e79…c0b250` binds all six years, 12 twin windows, zero shortfall and
cross-year duplicate UUIDs, explicit treatment of the 88 legacy identical
repeats, the 2026 delta, conduct, and unchanged legacy-tree hash. The restricted
source-native receipt binds 6,682,108 independently validated rows.

The 4,816,559 industry edges are filing-participation edges, not verified
personal contact, employment, influence, or Hill-to-industry transitions. Of
9,484 lobbyists with covered-position text, 6,527 have a government-term lexical
hit; this is not verified government employment. Identity adjudication,
covered-position parsing accuracy, and transition derivation remain blockers.

### 7.2 Human identity validity

Both current reviewers are models. The calibration sample is strict and 100%
MATCH, providing no observed negative/ambiguous case and undefined kappa. Human
gold remains zero; precision and recall remain unknown. The holdout labels are
already collected but their outcomes are sealed and single-use. Any tuning peek
invalidates evaluation.

No Politico↔legacy or LittleSis↔other identity link may become canonical until a
human-reviewed, stratified, confidence-bounded I-4/Q-1 packet passes.

### 7.3 Payroll breadth

No House SOD corpus/collector or Senate part inventory/parser exists. Planned
public windows remain left-censored before House 2009Q3 and Senate April 2011.
Payroll also omits unpaid/fellow/detailee/contractor populations and cannot by
itself establish continuous employment.

### 7.4 Authority and publication

- The legacy seed's interim A-0 is provisional pending Paul ratification. If
  declined, withdraw the collection by append-only reversal. Raw Quorum remains
  unauthorized.
- LittleSis public/derived publication is blocked pending CC BY-SA attribution
  and share-alike adjudication. The current corpus is local, not published.
- Politico lacks a redistribution-safe canonical output contract and human
  validity evidence; it remains disabled.
- LegiStorm and every other licensed source require their own A-0/A-1 scope.

### 7.5 Residual closure and carried residual

- **Closed:** the legacy record file now uses a registered, exact six-field
  per-record JSON schema in both construction and full local validation. The
  5,773 sealed rows re-passed without changing corpus or receipt bytes; the
  restricted schema is explicitly refused by both the public-generation
  publisher and verified generation loader.
- **Closed:** boss-link integrity now has valid in-spine, fabricated dangling,
  and malformed controls. Bad values emit null, increment the redaction count,
  and never create a dangling namespaced ID; float and boolean values are also
  rejected rather than coerced. The production receipt remains bound to zero
  redactions.
- **Closed:** every restricted LittleSis and LDA source-native/candidate schema
  is refused by both publication and verified loading. Publication additionally
  rejects source manifests whose redistribution class is not `public` or
  `public-safe-derived-only`. Government-term hits are documented in code and
  schema as unadjudicated lexical evidence, not employment facts.
- Historical committee side/location, IPEDS/CIP evaluation, and general
  container gold sets remain absent.

The remaining reference-normalization items do not invalidate the current
corpora, but must close before their downstream layers are relied upon.

## 8. Phase readiness

| Phase | Ruling |
|---|---|
| 0 contracts/privacy/isolation | Passed and preserved |
| 1 restricted source-native inputs | LittleSis/legacy P2 and LDA source-native substages passed; historic normalization and canonical identity remain incomplete; canonical Phase 1 not passed |
| 2 public payroll | Ready to implement, not built |
| 3 restricted profile depth | Politico corpus exists but remains disabled |
| 4 identity/container normalization | Ready to implement human evaluation; no canonical joins |
| 5 standalone graph | Blocked by canonical facts and source gates |
| 6 analysis loader | Closed; `STAFF_NET=off` |
| 7 engine consumers | Closed individually and globally |

## 9. Implementation acceptance checklist

- [x] Original attached and dated evidence preserved.
- [x] Restricted raw/normalized records remain outside OneDrive.
- [x] Exact input byte pins and aggregate receipts committed.
- [x] LittleSis entity/relationship conservation and accepted endpoint coverage pass.
- [x] Category 5 Donation / category 7 Lobbying correction recorded.
- [x] Legacy 5,773 rows and 533 offices conserved with zero contacts.
- [x] Every accepted relationship emitted or explicitly dispositioned.
- [x] Two fresh final builds byte-identical after recorded defect remediation.
- [x] All 873,236 records fully schema/semantically validated.
- [x] Zero identity merges, cross-source assertions, or temporal weight.
- [x] All 99 staffer tests and 69 subtests pass; all 37 schemas are registered.
- [ ] Paul ratifies the provisional legacy A-0 basis.
- [ ] LittleSis publication/share-alike review completes before public output.
- [x] Fresh LDA generation, terminal C-5 reconciliation, source-native build, and independent 6,682,108-row validation pass.
- [ ] LDA identity candidates receive human review and covered-position/transition gates pass.
- [ ] Human I-4/Q-1 calibration/holdout packet passes.
- [ ] House/Senate payroll collectors/parsers and gold sets pass.
- [ ] Canonical fact, graph, analysis, and per-consumer packets pass.

## 10. Final diagnostic

The project is now genuinely ready for implementation at the source-ledger,
human adjudication, covered-position evaluation, historic normalization, and
public-payroll acquisition stages. The P2 corpus is complete for its declared
LittleSis/legacy scope, and the separate LDA source-native corpus is complete
through cutoff-exclusive 2026-08-30. The broader staff/industry objective is
not complete: payroll, human identity validity, derived Hill-to-industry
transitions, and several authority/publication gates remain open. The safe next
move is to build on these evidence planes while keeping canonical identity,
graph, analytical claims, publication, engine access, and `STAFF_NET` off.
