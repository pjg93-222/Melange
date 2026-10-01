# Staffer Network Metrics and Gate Adjudication

**Version:** 6.2 structural implementation plus verified employment-adjudication overlay  
**Date:** 2026-08-30  
**Latest adjudication:** 2026-09-01 UTC  
**Status:** Five-source v6 structural graph and the deterministic employment-adjudication overlay pass their technical gates; 4,996 employment/payroll facts remain provisional; zero canonical employment promotions; human gold, container, Senate-observation, temporal production, consumers, and public release remain closed  
**Supersedes as metric authority:** `STAFFER_NETWORK_METRICS_20260829.md` v3.1 and the attached v2 evidence document

## 0A.0 Final employment-adjudication overlay measurement (2026-09-01)

The sealed 25,340-person scope produced 235,454 conserved candidate decisions.
Exactly 5,667 provisionally accepted support decisions consolidate to 4,996
unique provisional facts covering 1,186 people; 671 duplicate supports collapse
without loss. The remaining 24,154 people have no provisional fact in this
overlay. Lane facts are House 3,552, LDA covered-position 1,243, Senate 125, and
structured public profile 76. Temporal semantics are 3,677 `OBSERVATION_ONLY`
and 1,319 `ASSERTED_EPISODE`; every row is ineligible for primary temporal
weight and canonical promotion.

Primary and twin payloads are byte-identical. Independent verifier v4 returns
`PASS` with all assertions true, empty failure inventories, and zero token-scan
matches. The final staffer suite is 250 tests plus 73 subtests, all passing.
Normalized exact-fact duplicates are zero. Residual review surfaces are 57
year-precision ordering ambiguities across 55 people, 39 weak
`REPORT_PERIOD_ONLY` Senate observations, and container review on all 4,996
facts. The user waived the external Opus review for this closure; that gate is
`WAIVED_NOT_RUN`, not `PASS`. No substantive promotion gate is thereby closed.

## 0A. Employment and temporal gate addendum (2026-09-01 UTC)

This addendum is the current metric authority for employment coverage,
employment-source activation, and temporal readiness. Later sections retain
the dated build trail; where they describe the graph, payroll lanes, or loader
as unbuilt or closed, this addendum supersedes those historical statements.

| Gate/measure | Result | Exact measurement | Consequence/state |
|---|---|---|---|
| Fixed employment scope | `INVARIANT`; `PASS` for scope conservation | 25,340 LDA source identities | This denominator is scheduling scope, not a set of complete careers. |
| Any/no employment candidate | `REPORT`; verifier `PASS` | 13,697 have any candidate; 11,643 have none | Candidate presence is not accepted identity or canonical employment. |
| Missing dated/bounded evidence | `REPORT`; verifier `PASS` | 16,486 lack a dated former-position candidate; 18,227 lack a bounded employment-interval candidate | The two measures overlap and are not additive. |
| A9 scheduling partition | `INVARIANT`; verifier `PASS` | P0/P1/P2/P3 = 11,643/4,843/1,741/7,113 | A9 moves 209 A8-supported people into P3 without rewriting A4/A5b. |
| A7 LD-203 affiliations | verifier `PASS`; employment `NOT_EVALUABLE` | 143,513 dated registrant-affiliation candidates across 22,754 people | Affiliations are not employment-tenure facts and cause no bucket move. |
| A7 FEC employer points | verifier `PASS`; contextual only | 979 dated self-reported employer point observations across 37 people | Point observations are not tenure intervals and cause no bucket move. |
| A8 House review evidence | verifier `PASS`; review-only | 453 candidate matches covering 388 people from recovered 1997Q1 Part 2 observations | A8 is discovery evidence, not identity truth; A5c remains `BLOCKED_PARTIAL_RECOVERY`. |
| Complete-lifetime gate | `NOT_EVALUABLE`; blocked | all 25,340 lack complete-lifetime employment attestation; canonical employment promotions = 0 | Canonical episode and lifetime-history claims remain closed. |
| M1 temporal audit | `PASS` after fix | `INTERVAL_BLOCKED` now conserves the unknown-ordering case with null gap bounds, zero weights, and no revolving edge | The repaired fail-closed code path does not enable temporal data. |
| Structural Opus review | `PASS` | independent review of implemented structural graph mathematics | Confined to structural connectedness, not temporal employment truth. |
| Interval/co-tenure Opus review | `PASS` | independent review of interval normalization, union, intersection, bounds, and duration transform | Confined to code mathematics; incomplete candidate histories remain barred. |
| Selected regression suite | `PASS` | 48 focused tests; 222 staffer-network tests plus 73 subtests | Code regression evidence only; not corpus-completeness evidence. |
| Revolving-door Opus review | `PASS`, confined to math/validation | `data/staffer_network/reviews/OPUS5_REVOLVING_DOOR_MICROREVIEW_20260901.md`; SHA-256 `58db6b2e3ca1b4d7cc03131407d358521655ba5538c6d3e236e5a4425625c01f` | Does not authorize incomplete or review-candidate data. The eight nonblocking hardening findings remain in `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md` §7.1, including `possible_weight` gap-decay semantics and unvalidated edge-decay ordering. |
| Consolidation receipt final Opus review | `PASS`, confined to receipt semantics | `data/staffer_network/reviews/OPUS5_CONSOLIDATION_RECEIPT_FINAL_REVIEW_20260901.md`; SHA-256 `eb9f118cb4f5e9ff3db65fbce753b85e58fb9415f1b874857d75d8429b7559ba` | Re-derived conservation and reviewed forgery paths fail closed. This is not corpus-completeness, identity-resolution, or temporal-production evidence; the seven nonblocking hardening findings remain open. |

Current source/phase effect: only the five v6 structural sources are enabled in
the canonical internal-analysis generation. A7, A8, A9, employment candidate
ledgers, completeness audits, and temporal sidecars are noncanonical. Phase 2
is partial; Phase 5 structural, interval/co-tenure, and revolving-door math
reviews pass, but canonical temporal production remains blocked by incomplete
and unadjudicated employment data; Phase 6 passes for the immutable structural
loader; Phase 7 remains closed. The data/production gate remains closed and the
overall Meta LOOP disposition is `BLOCKED`.

## 0. Post-implementation adjudication (2026-08-31 UTC)

This table supersedes pre-build `NOT_EVALUABLE` and disabled-source rulings
later in this document. Historical rows remain to preserve the decision trail.

| Gate | Result | Measured evidence | Consequence |
|---|---|---|---|
| Canonical materialization | `PASS` | 1,585,038 entities; 6,050,221 facts; zero cross-source memberships/merges; 44 source self-loops excluded and counted | Singleton canonical fact plane is analysis-eligible |
| Contact minimization | `PASS` | 549 legislator contact occurrences removed in each of entity/fact planes; five LDA entity contacts removed; zero contact-only facts; 68 blank LDA covered-position literals excluded | Source-native evidence retained; canonical/score planes are minimized |
| Source activation | `PASS` for five-source v6 internal analysis | Congress reference, LittleSis, Politico Pro, legacy, and Senate LDA are the enabled structural sources | A7–A9 and all employment/temporal sidecars remain noncanonical and are not loader inputs |
| Identity containment | `PASS` | 6,978 reversible links; 2,519 strict one-to-one review candidates; candidates-as-facts false | Primary scores exclude every candidate; exploratory score may include the strict subset |
| Graph construction | `PASS` | 1,585,038 nodes; 5,260,888 evidence edges, of which 2,519 are exploratory candidate links; 185,628 primary and 185,221 exploratory isolates explicitly flagged | Typed structural graph and guarded score plane are built |
| Non-additive support | `PASS` | 5,258,369 primary evidence edges reduce to 5,235,347 unordered endpoint/layer scoring keys; 23,022 repeated or reciprocal supports collapse | Evidence rows remain conserved; source direction stays on evidence rows, while undirected traversal cannot double-count either orientation |
| PageRank convergence | `PASS` | residual L1: `9.56e-12` at 0.70, `9.14e-12` at 0.85, `9.68e-12` at 0.95 | Connectedness is numerically eligible; filter `primary_isolate=true` before ranking because teleport gives isolates positive prior mass |
| PageRank sensitivity | `REPORT` | top-1,000 overlap with 0.85: 0.982 at 0.70 and 0.973 at 0.95; L1 drift 0.1210 and 0.0931 (total variation 0.0605 and 0.0465) | Retain all three values; top-overlap uses tie-blind `argpartition`, so treat it as a head diagnostic rather than a rank-stability proof |
| Eigenvector diagnostic | `REPORT/PARTIAL_NULL` | 199,634/199,638 components converged; four components and 585 nodes null | Never substitute approximate values; compare only within a component; do not call it standard Bonacich centrality or an influence score |
| Bridging diversity | `PASS` definition | normalized Simpson diversity over layer-balanced neighbor-kind mass | Report independently of strength/PageRank and compare only within compatible entity-kind opportunity sets |
| Composite influence | `REJECTED` | emitted value is null for every node | Avoid unit mixing and connectivity double counting |
| Loader | `PASS` | explicit root, PASS receipt, exact roles/bytes/SHA-256 required | `STAFF_NET=analysis` is armed; default remains no-read `off` |
| Temporal weight invariant | `PASS`; canonical temporal data still `NOT_EVALUABLE` | builder aborts before promotion on any nonzero `undated-only` weight; exact 6,050,221-row v5→v6 comparison found only the intended 11,758 Politico weight changes and zero bad deltas; M1 passes after the `INTERVAL_BLOCKED` fix and interval/co-tenure Opus review passes | Code mathematics is ready, but dated admissible employment episodes and resolved identities are still required; LDA filing dates and A7 affiliations are not employment episodes |
| Score guard audit | `PASS` | all 1,585,038 score rows compared with prior graph; isolate flags exactly match strength, zero contact/nonnumeric differences; largest numerical delta after removing redundant row normalization is `3.55e-14` | Guard fields are exact and centrality changes are floating-point roundoff only |

The edge transition invariant is

```text
P[i,j] = sum_l (1 / |L_i|) * w[i,j,l] / sum_k w[i,k,l]
```

and PageRank is `r = alpha P.T r + alpha*dangling(r)*v +
(1-alpha)*v`, with entity-kind-balanced teleport `v`. These are connectedness
measures, not causal influence estimates. Equal mass per active layer and equal
teleport mass per entity kind are explicit priors; neither is empirically
neutral. Any substantive “influence” claim requires a separately validated
outcome model and must not be inferred from centrality alone.

## 1. Ruling

Metric definitions are implementation-ready. Exact invariants bind now;
empirical accuracy, coverage, and claim thresholds remain unfrozen until a dated
pilot/freeze packet supplies the denominator, sampling design, calibration and
untouched holdout, consequence, owner, and evidence hash.

The 2026-08-30 evidence now contains two separately conserved restricted
source-native generations: the 873,236-row LittleSis/legacy P2 generation and a
6,682,108-row LDA filing-participation generation. A third restricted artifact
contains 6,978 exact-name identity candidates for human review. These artifacts
were implementation substrates, not identity truth. The later five-source v6
canonical singleton plane, typed structural graph, and guarded analysis loader
are built, but cross-source identity remains unpromoted. Employment truth,
canonical temporal production, publication, and consumers are not armed.

Lifecycle states remain:

- `INVARIANT`: exact constitutive rule, immediately binding.
- `DEFINED`: implementable statistic with denominator and consequence.
- `PILOT`: measured development/calibration result, not a frozen bar.
- `FROZEN`: dated, versioned bar with an untouched holdout and accepted receipt.
- `RETIRED`: replaced because it measured the wrong construct.

Result values are `PASS`, `FAIL`, `REPORT`, and `NOT_EVALUABLE`. A missing
denominator is never zero and never passes.

## 2. Consequence classes

| Class | Effect |
|---|---|
| `ABORT_BUILD` | Prevent publication of the affected corpus/artifact generation |
| `QUARANTINE_SOURCE` | Exclude the source/sublayer from canonical or graph use |
| `SUPPRESS_CLAIM` | Keep evidence, but do not emit the failed analytical claim |
| `BLOCK_ANALYSIS_ARM` | Keep the analysis loader off |
| `BLOCK_CONSUMER_ARM` | Keep the named consumer off |
| `REPORT_QUEUE` | Report and adjudicate without halting unaffected evidence work |

## 3. Measured corpus status

> **2026-09-01 source update:** the C-1, C-3, and C-4 rows below preserve the
> 2026-08-30 pre-build state. Politico is now enabled only within the five-source
> v6 structural generation. Verified House 2009Q3–2015Q4 and Senate 2011–2026
> candidate lanes exist; A5c pre-web House recovery is partial, and A8 covers
> only 453 review rows/388 people from 1997Q1 Part 2. These lanes establish no
> canonical employment promotion or complete career.

| Metric | Lifecycle/result | Measurement and ruling | Consequence/state |
|---|---|---|---|
| A-0 source authority | `INVARIANT`; mixed | LittleSis public bulk use is recorded under CC BY-SA. The legacy seed scope is a provisional session interpretation of Paul's corpus-completion request, restricted to source-native local use and pending ratification. Raw Quorum, canonical use, analysis, and redistribution are excluded. | LittleSis publication review remains open. Refusal of legacy ratification requires append-only withdrawal of that collection. |
| A-1 raw provenance | `INVARIANT`; `PASS` for LittleSis pair and restricted legacy seed | LittleSis entities: 76,691,985 bytes, SHA-256 `5cc0039a…cd29d3c`; relationships: 110,381,587 bytes, `c11d7058…38d489`. The files were retrieved in one session; the relationship bytes match the prior audited dump. This is observed pairing evidence, not a publisher-declared shared vintage. Legacy input is pinned to `7abfbc9e…d179df3b52`. | Fail closed on any byte drift. |
| A-2 non-vacuous enablement | `INVARIANT` minimum passed; quality bar unfrozen | LittleSis accepted 1,880,488 of 1,880,491 relationships (99.999840%). The observed percentage is descriptive; no empirical acceptance-quality bar is frozen. | `source_enabled=false`; restricted source-native use only. |
| C-1 Politico census/normalization | `INVARIANT`; `PASS` mechanically | Existing sealed snapshot retains 18,618/18,618 profiles, 22,309 roles, and 20,485 issue assertions with zero contact findings or merges. | Source remains disabled pending validity and redistribution gates. |
| C-2 Quorum↔Politico reconciliation | `PILOT`; `REPORT` | 5,773/5,773 legacy outcomes conserved; 4,836 unique-name candidates, 60 collision-review rows, 877 no exact-name overlap. Candidate generation is not identity truth. | Queue only; zero canonical merges. |
| C-3/C-3b House SOD | `INVARIANT`/`PILOT`; `NOT_EVALUABLE` | No frozen House report inventory, collector corpus, or parser gold set exists. Planned public window begins 2009Q3. | House source unavailable to canonical episodes. |
| C-4 Senate reports | `INVARIANT`/`PILOT`; `NOT_EVALUABLE` | No complete report/part inventory, parser corpus, or annotated gold pages exist. Planned public window begins April 2011 unless official inventory proves otherwise. | Senate source unavailable to canonical episodes. |
| C-5 LDA filing census | `INVARIANT`; `PASS` | Composite receipt SHA-256 `0f985e79487a9965e9cfd05af6fb6a049a0bde6482031ba4134d4e7b93c0b250` binds 541,659 unique filings through cutoff-exclusive 2026-08-30: 2021 90,778; 2022 93,513; 2023 95,307; 2024 96,939; 2025 108,960; 2026 56,162. All 12 twin windows agree; shortfall and cross-year duplicate UUID occurrences are zero. Legacy seal `d7304591…94961e` is unchanged. Collection used registered access at 120 RPM, page size 25, and eight in-flight requests; one DNS interruption was resumed under a hash-bound event. | C-5 acquisition/reconciliation is closed as PASS. This does not establish identity, employment, transition, influence, or coverage beyond the cutoff. |
| C-5b/C-5c LDA source-native/covered positions | `INVARIANT`; `PASS` for source-native conservation; parser accuracy `NOT_EVALUABLE` | Receipt SHA-256 `5dfd3bbb16dea6ce940a687b15c74f07e720073d02b559d8000bb33db49dce8c` binds 541,659 filings, 25,340 lobbyists, 7,077 registrants, 46,996 clients, 1,037,547 activities, 4,816,559 filing-participation edges, and 748,589 covered-position assertions. Of 9,484 lobbyists with covered-position text, 6,527 have a government-term lexical hit. All 6,682,108 rows independently validated. | Source-native plane may enter a restricted ledger. Covered-position parsing, identity resolution, and Hill-to-industry transition derivation remain closed. Lexical hits are not verified government employment. |
| C-5d LDA identity candidates | `DEFINED`; `REPORT` | Receipt SHA-256 `b8be6326f17fa2cb367f1e2f75393935d5b6324c4986c35d2379d9e50b4e1f4a` binds 6,978 review rows: LittleSis 6,313, Politico 446, legacy 219; unique LDA lobbyists by source 4,451/412/214; 4,741 unique LDA lobbyists overall, 5,526 unique targets, and 3,910 normalized keys. There are 1,953 government-term lexical-hit rows, 4,459 collision rows, and 3,345 rows with cross-source multiplicity. | Restricted review queue only. Confidence is null with zero confidence values emitted; review is required; canonical merges and cross-source identity assertions remain zero. |
| C-6 LittleSis ingestion | `INVARIANT`; `PASS` for restricted source-native ingest | 443,140/443,140 entities; 1,880,491 observed relationships; 1,880,488 accepted; three dangling rejects; zero invalid/duplicates; zero accepted dangles. Accepted endpoint coverage is 100%. | Canonical/analysis enablement false; ShareAlike publication review deferred. |
| C-7/C-8 profile/history/education coverage | `DEFINED`; `NOT_EVALUABLE` for a canonical cohort | The local LittleSis spine and Politico corpus are source-native only and are not resolved into a canonical person cohort. | Report source-native counts only. |
| C-8b UNITID/CIP | `DEFINED`; `NOT_EVALUABLE` | No pinned IPEDS/CIP normalization evaluation exists. | Education normalization remains quarantined. |
| C-8c/C-8d committee/source contribution | `DEFINED`; `REPORT` | Current/historical reference files are pinned, but historical committee-side coverage and canonical fact contribution are incomplete. | No historical committee back-projection. |
| C-9 temporal precision | `INVARIANT` weight rule; `PASS` for emitted source assertions | 226,370 of 368,995 Position assertions are undated-only (61.3477%). All 424,323 emitted LittleSis assertions carry temporal weight zero; raw date strings remain literal. | Any nonzero temporal weight aborts the source-native build. |
| C-10a stripped legacy seed | `INVARIANT`; `PASS` within provisional A-0 scope | 5,773/5,773 accepted rows, 533/533 offices, zero retained contacts, exact record-file SHA-256 `439bb67f…a17ff48`. | Restricted local source-native seed only. Pending Paul ratification; raw workbooks remain unauthorized. |
| C-10b alumni reach | `DEFINED`; `NOT_EVALUABLE` | No canonical employment episodes exist across the planned source windows. | Report only after source-window-specific denominators exist. |
| C-11 historic roster | `INVARIANT` conservation; `REPORT` | Voteview 51,061/51,061 rows and 68 blank-Bioguide outcomes remain explicit; congress-legislators references are commit-pinned. Normalized term/committee reconciliation is incomplete. | Useful reference spine; not a completed normalized corpus plane. |

## 4. Resolution, ledger, and adjudication

| Metric | Lifecycle/result | Measurement and ruling | Consequence/state |
|---|---|---|---|
| R-1 container normalization | `DEFINED`; `NOT_EVALUABLE` | No stratified person/office/committee/registrant/client/institution gold set. | Quarantine projections requiring unresolved containers. |
| R-2 source-native losslessness | `INVARIANT`; `PASS` for this restricted generation | Full 443,140 entity spine; 424,323 in-scope relationship assertions; 1,456,165 accepted out-of-scope dispositions; three dangling rejects; 5,773 legacy rows. Counted minimization: 38 contact-like free-text redactions, two dangling parent-reference redactions, zero boss-reference redactions. | Does not exercise canonical-ledger R-2. |
| R-3 duplicate/consolidation diagnostics | `DEFINED`; `REPORT` | Zero duplicate LittleSis entity/relationship IDs. No cross-source consolidation was attempted. | Report; no false-merge claim. |
| Q-1 adjudication reliability | `DEFINED`; `REPORT` | Two model-assisted reviewers submitted 400 labels: each labeled 100 calibration and 100 holdout candidates. Calibration exact agreement is 100/100 and consensus is 100 MATCH. This all-positive strict stratum has zero negative/ambiguous cases; chance-corrected agreement is undefined. Holdout labels exist, but outcomes remain unpublished and evaluation count is zero. Human gold is zero; precision is null. | No Q-1/I-4 threshold may freeze. Holdout is single-use; any peek/tuning invalidates it. |
| I-1 schema/referential integrity | `INVARIANT`; `PASS` for P2 corpus | All 873,236 emitted records passed schema and semantic validation; emitted endpoint misses are zero. | Abort affected build on any violation. |
| L-1 LDA pairing/namespace integrity | `INVARIANT`; `PASS` for restricted source-native corpus | The composite receipt binds the sealed legacy input to the reconciled cutoff; the source-native receipt binds five deterministic files, 6,682,108 independently validated rows, and zero canonical merges/cross-source identity assertions. | Restricted source-native loading may proceed; canonical resolution and derived transition layers remain closed. |
| I-2 date integrity/concurrency | `INVARIANT` hard dates; temporal code `PASS`; canonical episode data `NOT_EVALUABLE` | Coarse/irregular raw dates are preserved; precision only degrades. M1 passes after `INTERVAL_BLOCKED`; interval/co-tenure Opus review passes. No candidate employment chronology is promoted. | Canonical episode/co-tenure claims remain blocked despite code readiness. |
| I-4 entity resolution | `DEFINED`; `NOT_EVALUABLE` | Human-gold count 0, recall universe absent, and the calibration stratum is all positive. | No canonical cross-source joins. |
| I-5/I-7/I-8/I-9 | `DEFINED` or pilot; `NOT_EVALUABLE` except historic key fixtures | Hard negatives, episode agreement, covered-position parser, and term-valid historic resolution require their own samples. | Queue/quarantine affected layers. |

## 5. Graph, operations, and publication

| Metric | Lifecycle/result | Measurement and ruling | Consequence/state |
|---|---|---|---|
| G-1/G-2 numerical and temporal graph invariants | structural `PASS`; temporal production blocked | The five-source typed structural graph and score guards pass; structural, interval/co-tenure, and revolving-door Opus reviews pass at their scoped code/math gates. All 25,340 employment histories still lack complete-lifetime attestation. | Structural analysis is eligible; canonical temporal employment/revolving layers remain closed. |
| G-3/I-6/I-14 claim robustness | `DEFINED`; `NOT_EVALUABLE` | No graph claim, null, ablation, or sensitivity packet exists. | Suppress claims. |
| P-1 PII minimization | `INVARIANT`; `PASS` | Legacy synced surfaces are contact-free; corpus validation found/removed 38 contact-like free-text values before normalized emission. Repository receipts contain aggregate counts and hashes only. | Abort on prohibited output. |
| X-1 loader contract | `INVARIANT`; `PASS` for structural generation | Explicit immutable root, PASS receipt, exact roles, bytes, and SHA-256 are enforced. | `STAFF_NET=analysis` may load the structural generation only; employment/temporal sidecars are excluded. |
| I-10a off isolation | `INVARIANT`; `PASS` from Phase 0 packet | `STAFF_NET=off` remains required and no staffer analysis reader is armed. | Analysis stays off. |
| I-10b consumer governance | `DEFINED`; `NOT_EVALUABLE` | No named consumer packet exists. | All engine consumers closed. |
| I-11 determinism/atomicity | `INVARIANT`; Phase 0 `PASS` | Existing packet continues to own clean/incremental equality, logical SQLite hashes, fault visibility, and pointer atomicity. | Do not conflate with I-16. |
| I-12 refresh supervision | `DEFINED`; `REPORT` | LDA has an observable local runner/status receipt; a complete manifest-driven multi-source supervisor is not implemented. | No unattended source enablement. |
| I-13 acquisition conduct | `INVARIANT`; `PASS` for completed Politico and LDA acquisition | The final LDA receipt pins registered access, 120 RPM, page size 25, eight in-flight requests, bounded ascending processing, retry policy, and one hash-bound resume after a DNS error. | Reopen/quarantine only on receipt or conduct drift. |
| I-15 claim/publication review | `INVARIANT`; `NOT_EVALUABLE` | No staff/industry analytical output is approved for publication. LittleSis ShareAlike review is deferred. | Suppress publication. |
| I-16 source-native corpus twin-build byte determinism | `INVARIANT`; `PASS` same machine/environment | Two final real builds produced byte-identical entity gzip, relationship gzip, legacy NDJSON, and aggregate receipt. An earlier twin exposed unstable case-fold alias ties; both receipt hashes were recorded, the sort became total `(casefold, original)`, and fresh twins passed. Cross-machine/runtime determinism is not evaluated. | Abort if named twin artifacts differ. I-11 atomic/incremental claims are out of scope. |

## 6. Corrected category and corpus inventory

The 2026-08-29 prose mislabeled LittleSis category 5. The authoritative native
map and measured accepted counts are:

| Category | Accepted | P2 disposition |
|---|---:|---|
| Position | 368,995 | Emitted source assertion |
| Education | 44,673 | Emitted source assertion |
| Lobbying (category 7) | 10,655 | Emitted source assertion |
| Donation (category 5) | 1,267,716 | `OUT_OF_SCOPE_CATEGORY` |
| Membership | 53,139 | `OUT_OF_SCOPE_CATEGORY` |
| Family | 31,025 | `OUT_OF_SCOPE_CATEGORY` |
| Transaction | 35,265 | `OUT_OF_SCOPE_CATEGORY`; three additional dangling rejects |
| Generic | 23,509 | `OUT_OF_SCOPE_CATEGORY` |
| Ownership | 19,346 | `OUT_OF_SCOPE_CATEGORY` |
| Hierarchy | 16,420 | `OUT_OF_SCOPE_CATEGORY` |
| Professional | 5,638 | `OUT_OF_SCOPE_CATEGORY` |
| Social | 4,107 | `OUT_OF_SCOPE_CATEGORY` |

Exact conservation:

```text
424,323 emitted assertions
+ 1,456,165 accepted out-of-scope dispositions
+         3 dangling rejects
= 1,880,491 observed relationships

443,140 entity records
+ 424,323 relationship assertions
+   5,773 restricted legacy records
= 873,236 fully validated emitted records
```

## 7. Freeze packet and phase gates

No empirical metric becomes `FROZEN` without a dated packet containing metric
version, source/query/config hashes, denominator, sampling/weighting, calibration
and untouched holdout separation, confidence rule, consequence, owner, and
accepted receipt hash. Changes to source semantics, candidate universe, parser,
model, or corpus window version the packet.

> **2026-09-01 phase update:** the historical table below is superseded for
> Phases 2, 5, and 6. Phase 2 is partial (verified House/Senate candidate lanes;
> A5c `BLOCKED_PARTIAL_RECOVERY`), Phase 5 has a structural `PASS` but temporal
> production is blocked, and Phase 6 passes for the structural loader.

| Phase | Current gate ruling |
|---|---|
| 0 contracts/isolation | Passed; unchanged |
| 1 restricted seed/LittleSis/LDA | Legacy C-10a, restricted LittleSis C-6, LDA C-5, and LDA source-native conservation pass; historic normalization and canonical identity remain incomplete; canonical Phase 1 not passed |
| 2 public payroll | Not built |
| 3 restricted profile depth | Politico census/normalization passed mechanically; validity/publication gates open |
| 4 resolution | Model-only calibration REPORT; human I-4/Q-1 not evaluable |
| 5 standalone graph | Not built |
| 6 analysis loader | Closed |
| 7 named consumers | Closed |

## 8. Final metric adjudication

The measured P2 and LDA corpora are strong, separately conserved evidence
substrates. The P2 conservation total remains 873,236 records; the LDA receipt
separately binds 6,682,108 source-native rows. The 6,978-row cross-source output
is a restricted review queue, not identity truth. No artifact contains canonical
merges or cross-source identity assertions, and candidate confidence remains
null. C-5 is closed as PASS, but human identity precision, covered-position
semantics, derived Hill-to-industry transitions, public payroll, historic member
normalization, LittleSis publication review, and provisional legacy ratification
remain open. Canonical, graph, analysis, publication, consumer, and public-use
claims therefore remain closed with `STAFF_NET=off`.

**2026-09-01 final adjudication.** The five-source v6 singleton canonical fact
plane, typed structural graph, and explicit immutable analysis loader are
internally active. Employment evidence is review/scheduling-only: 13,697 of
25,340 people have some candidate, 11,643 have none, 16,486 lack a dated former
candidate, 18,227 lack a bounded interval candidate, and all 25,340 lack
complete-lifetime attestation. Canonical employment promotions are zero.
Structural math, M1 after `INTERVAL_BLOCKED`, interval/co-tenure math,
revolving-door math/validation, and consolidation-receipt semantics pass within
their declared scopes. The measured regression evidence is 48 focused tests
and 222 staffer-network tests plus 73 subtests, all passing. Employment/temporal
production, revolving-door claims, publication, and consumers remain closed
pending admissible adjudicated data; the overall Meta LOOP disposition remains
`BLOCKED`. Neither scoped review supersedes its nonblocking hardening findings.
