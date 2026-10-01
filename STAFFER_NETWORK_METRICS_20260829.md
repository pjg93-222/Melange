# Staffer Network Metrics and Gate Adjudication

**Version:** 3.1<br>
**Date:** 2026-08-29<br>
**Status:** Metric definitions are implementation-ready; empirical quality bars remain unfrozen until their stated pilots<br>
**Supersedes as metric authority:** the attached `STAFFER_NETWORK_METRICS_20260829.md` v2 evidence document

## 1. Ruling

No v2 numeric quality threshold is frozen merely because a phase ships. The v2 wording that a metric “arms automatically” conflicts with its own freeze requirement and is retired.

Metrics have five lifecycle states:

- `INVARIANT`: a constitutive exact rule (for example conservation, referential integrity, privacy, or atomic publication) that is binding immediately and does not require empirical calibration.
- `DEFINED`: denominator, statistic, evidence, and consequence are implementable.
- `PILOT`: measured on development/calibration data; a proposed bar may be evaluated but is not binding.
- `FROZEN`: dated threshold, source/config vintage, owner, and untouched holdout are recorded in a freeze packet.
- `RETIRED`: replaced because it measured the wrong construct.

Every run emits the statistic even when a gate is not frozen. A missing denominator or omitted cohort is a metric failure, not zero.

## 2. Consequence classes

| Class | Effect |
|---|---|
| `ABORT_BUILD` | No base corpus/artifact publication; used only for schema, referential, conservation, hard-date, privacy, and deterministic-integrity failures |
| `QUARANTINE_SOURCE` | Publish unaffected corpus planes but exclude the affected source/sublayer from canonical or graph use |
| `SUPPRESS_CLAIM` | Corpus/artifact may exist; the failed analytical/publication claim is not emitted |
| `BLOCK_ANALYSIS_ARM` | Analysis loader remains off |
| `BLOCK_CONSUMER_ARM` | A named engine consumer remains off; other consumers are unaffected |
| `REPORT_QUEUE` | Report and adjudicate; does not by itself halt unaffected work |

There is no rule that all I-metrics are fail-closed. Consequence follows the construct being tested.

## 3. Acquisition and coverage metrics

| ID | Status | Statistic and denominator | Target / freeze rule | Failure action |
|---|---|---|---|---|
| A-0 Source authority | `INVARIANT` | Sources with recorded authority scope, terms/license vintage, authorization, extraction mode, retention, and redistribution class / all enabled sources | Exactly 100% before source enablement | `QUARANTINE_SOURCE` |
| A-1 Raw provenance | `INVARIANT` | Snapshots with URL/query or report inventory, watermark, bytes/hashes, schema/parser versions, count reconciliation, and source-specific freshness / all enabled snapshots | Exactly 100% | `QUARANTINE_SOURCE`; `ABORT_BUILD` if a claimed complete snapshot is untraceable |
| A-2 Non-vacuous enablement | `INVARIANT` minimum plus source-specific `PILOT` coverage | (a) accepted records / observed eligible records; (b) accepted records > 0; (c) source-specific accepted-coverage statistic and rejection reasons | An enabled source may never pass by rejecting everything. Accepted count must exceed zero, and the source remains quarantined until its separately frozen acceptance-coverage bar passes | `QUARANTINE_SOURCE` |
| C-1 Profile census and normalization conservation | `INVARIANT` census/normalization passed for 2026-08-29 snapshot; `PILOT` profile quality | (a) valid unique profile UUIDs inventoried / frozen directory UUID census; (b) fetched and parsed UUIDs / valid inventoried UUIDs; (c) normalized source-person assertions / accepted UUID rows. Current receipts: 18,618/18,618 unique UUIDs and 18,618/18,618 normalized persons, with 22,309 role and 20,485 issue assertions, zero duplicates/failures/contact retention, and exact four-partition conservation | Exact census and normalization conservation; profile-detail/field-quality bars require a separate pilot | `QUARANTINE_SOURCE` |
| C-2 Quorum↔Politico reconciliation | `PILOT`, outcome conservation passed; identity quality unadjudicated | Frozen Quorum seed records dispositioned against the authorized frozen Politico UUID census / Quorum records eligible for the source-pair comparison. The first no-auto-merge pilot conserved 5,773/5,773 legacy rows: 4,836 unique-name candidates, 60 collision-review rows, and 877 without exact-name overlap; candidate strata are 2,643 strict name+title+office, 425 title/no office evidence, 50 title/office conflict, and 1,718 name-only | Outcome conservation exactly 100%. Match-yield and ER precision remain unfrozen until a dated stratified, independently adjudicated source-pair holdout; the deterministic 200-row strict sample is a queue, not a gold result | `REPORT_QUEUE` for all candidates/unresolved rows; `QUARANTINE_SOURCE` until precision/authority gates pass |
| C-3 House report census | `INVARIANT` | Authoritative/revised quarter artifacts acquired / expected manifest from 2009Q3 through last fully published quarter; partial current quarter separate | Exactly 100% byte acquisition | `QUARANTINE_SOURCE` |
| C-3b House row conservation/parser | `INVARIANT` conservation; `PILOT` parser | (a) accepted + rejected / all physical data rows after frozen header/footer rules; (b) employee/payroll classification precision and recall on annotated rows | (a) exactly 100%; (b) threshold frozen after representative pilot | Conservation failure `ABORT_BUILD`; quality failure `QUARANTINE_SOURCE` |
| C-4 Senate report/parser | `INVARIANT` acquisition; `PILOT` parser | (a) acquired report/PDF parts / frozen official inventory; (b) parser precision/recall on annotated pages or printed control totals | (a) exactly 100%; (b) threshold frozen after multipart pilot | `QUARANTINE_SOURCE` |
| C-5 LDA filing census | `INVARIANT`, currently failing | Unique filing/version UUIDs ingested / frozen endpoint-query-year inventory at start and end watermarks; also require exact manifest↔disk pages/hashes, explicit identical/conflicting duplicate disposition, zero cross-year UUID collision, and amendment preservation | Exactly 100% for the frozen scan set. The 2026-08-29 receipt has 21,599/21,599 page/hash integrity but only 539,782 unique UUIDs from 539,870 objects, with 88 identical duplicate occurrences; the endpoint count sum moved 539,865→539,870 during pagination | `QUARANTINE_SOURCE` |
| C-5b Covered-position prevalence | `DEFINED`, report-only | (a) lobbyist-filing occurrences with nonempty text / all occurrences; (b) unique lobbyist IDs ever carrying text / all unique lobbyist IDs | Report by year and source vintage; no quality bar | `REPORT_QUEUE` |
| C-5c Covered-position classification/resolution | `DEFINED`, pilot required | First classify all nonempty occurrences as member-office, committee, executive, generic, other, or unparsed. Report exact Bioguide/container resolution among eligible member-office strings, both occurrence-weighted and unique-string | Coverage, precision, and abstention thresholds frozen on stratified holdout | `QUARANTINE_SOURCE` for affected derived sublayer |
| C-6 LittleSis ingestion | `INVARIANT` conservation/FK; `PILOT` acceptance coverage | Accepted + rejected / all declared relationship rows for a frozen entity+relationship dump pair; entity foreign-key coverage over accepted relationships; accepted relationships / declared relationships | Conservation exactly 100%; accepted endpoint FK coverage exactly 100%; accepted count > 0 and a frozen non-vacuous acceptance-coverage bar required before enablement | `QUARANTINE_SOURCE` |
| C-7 Profile history depth | `DEFINED`, report-only | Distribution of parsed employment/education claims per valid unique profile, including zeros; distinguish absent, empty, and parse failure | Report by member-office/committee and other explicit cohorts | `REPORT_QUEUE` |
| C-8 Cohort education coverage | `DEFINED`, report-only | Persons with at least one supported education assertion / all canonical persons in frozen, explicitly overlapping or mutually exclusive current/historic/lobbyist cohorts, including unresolved source rows separately | Report cells and source vintage; no arm bar | `REPORT_QUEUE` |
| C-8b UNITID/CIP normalization | `DEFINED`, pilot required | UNITID: resolved / domestic postsecondary IPEDS-eligible education assertions with nonempty institution. CIP: mapped / assertions with nonempty major eligible for CIP. Report precision and coverage, separating exact CIP-6, CIP-2-only, broader/ambiguous, and unresolved mappings | Proposed 90% coverage is not binding; freeze coverage and precision after cohort/source pilots | `QUARANTINE_SOURCE` for education layer |
| C-8c Committee-side coverage | `DEFINED`, report-only | Supported committee employment assertions with resolved committee and side / committee assertions eligible for side resolution; report personal-office/committee overlap separately | Report by source, chamber, congress, and source vintage; no universal arm bar | `REPORT_QUEUE` |
| C-8d Employment-source contribution | `DEFINED`, report-only | Canonical episodes and supporting assertions by source/vintage/evidence class | Report counts and shares; never call a partial source phase exhaustive | `REPORT_QUEUE` |
| C-10a Current stripped-seed ingestion | `INVARIANT`, authority-gated | (a) imported + rejected / 5,773 legacy rows; (b) imported stripped rows / 5,773; (c) offices with at least one accepted row / 533; (d) prohibited contact fields in stripped output | Conservation 5,773/5,773; acceptance 5,773/5,773; office coverage 533/533; prohibited fields zero. Any lower future-vintage acceptance bar requires a separate freeze packet | `ABORT_BUILD` for seed build; source remains quarantined until A-0/P-1 pass |
| C-10b Alumni reach | `DEFINED`, report-only | Historical member-office service spans with at least one supported staff episode / spans eligible inside actual House/Senate/profile source windows | Report by chamber, congress, source window; no universal denominator | `REPORT_QUEUE` |
| C-11 Historic roster | `INVARIANT` conservation; `PILOT` resolution | Expected member-service spans ingested / frozen source roster spans; plus temporally valid Bioguide resolutions / eligible office assertions | Conservation exactly 100%; temporal resolution precision bar after audit pilot | Conservation `ABORT_BUILD`; resolution issues `REPORT_QUEUE`/quarantine affected joins |

Measured baseline receipts are descriptive, not thresholds: 5,773 contact-free current directory rows; 533 offices; Politico 18,618 normalized persons, 22,309 roles, and 20,485 issue assertions; Voteview 51,061/51,061 rows with 68 explicit blank-Bioguide outcomes; LDA 21,599/21,599 page/hash integrity but 539,782 unique UUIDs from 539,870 objects and 88 duplicate occurrences; LittleSis relationships present but entity dump absent.

## 4. Parsing, ledger, resolution, and temporal metrics

| ID | Status | Statistic and denominator | Target / freeze rule | Failure action |
|---|---|---|---|---|
| R-1 Container normalization | `DEFINED`, pilot required | Precision, coverage, and abstention separately for member offices, committees/side, administrative offices, registrants, clients, UNITID and CIP on stratified holdouts | Freeze per container class and source | Quarantine affected projection; `REPORT_QUEUE` |
| R-2 Ledger losslessness | `INVARIANT` | Accepted source rows represented by source-native ledger rows or explicit reject / all physical source rows; unresolved/adjudication items with status, owner and source ref / all queued | Exactly 100% | `ABORT_BUILD` |
| R-3 Duplicate/consolidation diagnostics | `DEFINED`, report-only until pilots | (a) duplicate physical source observations / all source observations by source; (b) assertions consolidated into multi-support fact clusters / accepted assertions; (c) residual high-score unlinked duplicate candidates / eligible candidate clusters | Report by source/source-pair and hard-name stratum; later bars freeze with I-4 evaluation | `REPORT_QUEUE`; catastrophic false-merge evidence can quarantine the affected resolution build |
| Q-1 Adjudication reliability | `DEFINED`, pilot required | Agreement on a double-reviewed subset; conflict disposition rate; calibration/holdout label separation audit | Freeze agreement/conflict bar after first queue pilot; label leakage must be zero | `REPORT_QUEUE`; holdout leakage invalidates evaluation |
| I-1 Schema/referential integrity | `INVARIANT` | Predicate endpoint types, primary/foreign keys, `(source, source_key)` uniqueness, source refs and observation links, container keys, xref one-source-key-to-one-canonical-entity, legal direction and self-loop contracts | Zero violations | `ABORT_BUILD` |
| L-1 LDA pairing/namespace integrity | `INVARIANT` | Activity-lobbyist observations retaining the original lobbyist ID ↔ covered-position occurrence, distinct registrant/client namespaces, and filing/activity support / all accepted LDA lobbyist observations | Exactly 100%; zero silent registrant↔client namespace joins | `ABORT_BUILD` for LDA normalized build |
| I-2 Date integrity/concurrency | `INVARIANT` hard dates; `DEFINED` concurrency | Hard errors: reversed bounds, impossible source dates, invalid precision/envelopes. Separately report concurrent distinct Hill containers after clipping current/open bounds to `as_of` | Zero hard errors. Concurrency is a queue until full-time/FTE semantics exist | Hard errors `ABORT_BUILD`; concurrency `REPORT_QUEUE` |
| I-3 Duplicate rate | `RETIRED` | Replaced by R-3 duplicate/consolidation diagnostics and I-4 evaluated linkage quality | Cross-source corroboration is expected and not a defect | See R-3/I-4 |
| I-4 Entity resolution | `DEFINED`, eval design required | Cluster and pair precision/recall by source pair and hard-name/common-name stratum on weighted samples; recall requires an exhaustively labeled candidate universe; report confidence intervals | Separate calibration and frozen holdout; thresholds frozen per source pair. Pooled 200 pairs are insufficient | `QUARANTINE_SOURCE` joins; high-risk false merge may invalidate canonical build |
| I-5 Hard-negative control | `DEFINED`, supplemental | False matches on blocked/permuted hard negatives after removing known positives, over multiple fixed seeds; report upper confidence bound | Report; does not replace I-4 real-negative evaluation | `REPORT_QUEUE` |
| I-7 Episode agreement | `DEFINED`, pilot required | On matched episode pairs: start gap, end gap, interval containment/IoU, median and p90, plus unmatched episode count; report by source pair | Universal one-quarter bar retired; freeze source-pair bars after pilot | `REPORT_QUEUE`; suppress unsupported consolidation rule |
| I-8 Covered-position parser | `DEFINED`, pilot required | Segmentation precision/recall, office/member resolution precision, eligible-string coverage, abstention, and outcome conservation on frequency/long-tail/committee/executive/multi-office strata. Explicit date tokens, if present, remain literal source assertions and are not inferred when absent | Frozen holdout and confidence-bound targets required | `QUARANTINE_SOURCE` for parsed transition layer |
| I-9 Historic member resolution | `INVARIANT` key validity; `PILOT` resolution quality | Exact Bioguide/container resolutions valid for the named office/chamber during asserted interval / eligible assertions; roster key uniqueness; unresolved outcome census | Key uniqueness zero violations; temporal precision bar frozen after stratified audit | Schema violations `ABORT_BUILD`; affected resolutions quarantined |

`D-Q5` is not an ER-owner ruling; the v2 cross-reference is retired. Adjudication ownership is defined in the queue contract and freeze packet.

## 5. Graph, uncertainty, and claim metrics

| ID | Status | Statistic and denominator | Target / freeze rule | Failure action |
|---|---|---|---|---|
| C-9 Temporal precision | `INVARIANT` weight rule; `DEFINED` distribution | (a) support-record mix by day/month/year/undated; (b) mutually exclusive edge best-support bucket day/month/year/undated-only, separately by layer/evidence class | Report complete distribution; undated-only temporal weight must be zero | Weight violation `ABORT_BUILD`; distribution report required |
| G-1 Numerical invariants | `INVARIANT` | Finite nonnegative weights; legal self-loops; required symmetry/direction; raw sublayers preserved; formula fixtures; fixed reference scaling if used | Zero violations | `ABORT_BUILD` |
| G-2 Temporal admissibility | `INVARIANT` | Temporal edges whose duration/order/decay is supported by an admissible dated assertion / all temporal edges; LDA-covered-position-only structural links with temporal weight zero / all such links | Exactly 100% | `ABORT_BUILD` |
| G-3 Uncertainty robustness | `DEFINED`, claim pilot required | Rebuild after excluding low-confidence links and under source ablation; report top-k edge Jaccard, member-strength Spearman, community ARI, mover counts and key claim changes | Stability bars predeclared and frozen per claim/use case | `SUPPRESS_CLAIM`; may `BLOCK_ANALYSIS_ARM` for load-bearing instability |
| I-6 Temporal null | `DEFINED`, claim gate | Compare the observed statistic to the permutation distribution of the same statistic using predeclared permutations/seed; report p-value and effect size | Freeze statistic/effect/p-value bar before claim evaluation | `SUPPRESS_CLAIM`, not corpus build |
| I-14 Sensitivity | `DEFINED`, claim gate | Renormalized-simplex coefficient perturbations, bounded continuous dial sweeps, categorical modes separately, and source ablation; report predeclared stability outcomes | No independent coefficient changes that violate the simplex; freeze claim-specific stability bars | `SUPPRESS_CLAIM`/`BLOCK_CONSUMER_ARM` |

No canonical Phase 5 build uses a default composite. If a later composite is proposed, its calibration, reference-vintage scaling, alpha simplex, and claim-specific sensitivity thresholds are new freeze-packet fields.

## 6. Operations, integration, privacy, and publication metrics

| ID | Status | Statistic and denominator | Target / freeze rule | Failure action |
|---|---|---|---|---|
| P-1 PII minimization and legacy remediation | `INVARIANT`, passed 2026-08-30 | (a) new normalized/derived artifacts containing email, phone, address, contact hashes, or disallowed source text; (b) known legacy PII artifacts with classification, quarantine, authority, retention, and remediation status / all discovered legacy artifacts; (c) unauthorized opens of quarantined inputs | Zero prohibited fields in new outputs; 100% legacy artifacts registered/quarantined; zero unauthorized opens. The 5,769 email and 5,773 phone values formerly in each synced legacy surface were removed; originals are hash-verified in restricted machine-local quarantine | New-output/unauthorized-use failure `ABORT_BUILD`; legacy exception `REPORT_QUEUE` and blocks that source's enablement |
| X-1 Loader contract | `INVARIANT` for selected generation | Artifacts whose schema ID/hash, key/version domains, file hash and record count validate / every artifact advertised by the atomically selected generation manifest; report pointer/manifest/version negotiation and rejection outcomes | Exactly 100%; loader returns no partial generation and fails closed on any incompatibility | `BLOCK_ANALYSIS_ARM` |
| I-10a Off isolation | `INVARIANT` for arming; Phase 0 packet passed 2026-08-30 | Instrumented production network/engine/surface readers that open staff artifacts while off; frozen existing-output manifest equality for `off` versus physical absence. Current packet inventories 491 production Python files, one approved reader, seven protected outputs, and zero opens in both controls | Zero staff file opens; exact canonical output hash equality | `BLOCK_ANALYSIS_ARM` |
| I-10b Consumer governance | `DEFINED` at packet level, consumer bars unresolved | Each named consumer has schema handshake, frozen-input comparability, stability/impact measures, source/claim scope, rollback, reviewer and acceptance receipt | Exactly one accepted packet per consumer; no global automatic arm | `BLOCK_CONSUMER_ARM` |
| I-11 Determinism/atomicity | `INVARIANT`, Phase 0 packet passed 2026-08-30 | (a) canonical derived artifact and logical ordered DB-dump hashes across two clean builds; (b) clean vs incremental parity; (c) fault-injection exposes either the complete previous or complete new immutable generation through the pointer, never a mixed family; (d) `PRAGMA integrity_check`. Current nonvacuous fixture covers all 17 logical tables and clean/incremental digests agree | Exact semantic/content equality; zero partial/mixed publication cases. Operational run IDs/timestamps excluded | `ABORT_BUILD` |
| I-12 Refresh supervision | `DEFINED`, repo-blocked | Source jobs with declared command, progress probe, cadence/freshness, lock, retry and reconciliation policy / enabled staff sources | Exactly 100%. Current interview-only supervisor is ineligible | `QUARANTINE_SOURCE`; no attended refresh |
| I-13 Crawl authorization/conduct | `INVARIANT`; Politico 2026-08-29 crawl passed | (a) terms/permission vintage and approved mode; (b) requests conforming to frozen concurrency/rate/retry/status-log policy / all requests. Politico: 188/188 successful page requests, observed maximum concurrency 4 under ceiling 4, and rolling-minute maximum 28 under ceiling 60 | Authorization exactly 100%; request violations zero | `QUARANTINE_SOURCE` |
| I-15 Claim/publication review | `INVARIANT` for publication | Generated staff reports/manifests passing scoped phrase policy plus human review / published outputs | Exactly 100% reviewed; zero unapproved causal/direct-contact claims | `SUPPRESS_CLAIM`/publication |

The current `fec/collect/collector_supervisor.py` is hard-coded to the interview fetcher, its process name, `social_media.db.iv_fetch_log`, and a universal seven-day sentinel. I-12 therefore cannot pass through simple target registration. Use a dedicated manifest-driven staff refresh supervisor initially or generalize the existing supervisor in a separately reviewed change.

## 7. Metric implementation records

Every emitted metric record contains:

```text
metric_id
metric_definition_version
lifecycle_state
source/corpus/build manifest hashes
as_of and measurement time
eligible denominator count and cohort query
numerator count
statistic and confidence interval where applicable
threshold and comparison, or null when unfrozen
strata and exclusions with counts
evidence artifact URI/hash
result: PASS | FAIL | REPORT | NOT_EVALUABLE
consequence class
owner
```

`NOT_EVALUABLE` requires a reason and never becomes `PASS`.

## 8. Freeze packet

A quality threshold becomes `FROZEN` only when one dated packet records:

- metric definition/version and rationale;
- corpus/source/query/watermark/config vintages;
- eligible denominator and sampling design;
- development, calibration, and untouched holdout separation;
- strata and weighting scheme;
- point target and confidence-bound rule;
- fixed random seeds/permutation design where applicable;
- failure consequence and quarantine scope;
- adjudication owner and reviewer;
- accepted receipt hash.

Changing the metric, source semantics, candidate universe, parser, model, or load-bearing corpus window invalidates or versions the packet. It does not silently reuse the old threshold.

## 9. Phase gate sets

| Phase | Required gates |
|---|---|
| 0 contracts | A-0/A-1/A-2 schemas, I-1 fixtures, R-2 conservation fixtures, P-1 legacy inventory/remediation, I-11 serialization/fault fixtures, X-1 schema, I-10a negative controls |
| 1 seed/LDA/LittleSis | A-0/A-1/A-2 for every enabled source; C-5, C-6 if enabled, C-10a only if stripped seed enabled, C-11, R-2/R-3, I-1/L-1/I-2/I-9, P-1. C-2 is not a Phase 1 gate |
| 2 payroll | A-0/A-1/A-2, C-3/C-3b/C-4, R-2; parser quality frozen before canonical episode use |
| 3 restricted profiles | A-0/A-1/A-2, I-13, C-1/C-2/C-7, P-1; source remains quarantined until authorization |
| 4 resolution | R-1/R-3, Q-1, I-4/I-5/I-7/I-8/I-9, C-8b/C-8c; C-8d reports source contribution |
| 5 graph | C-9, G-1/G-2/G-3, I-6/I-11/I-14/I-15 as claim scope requires |
| 6 analysis arm | X-1, I-10a, all enabled-source quarantine checks clear |
| 7 named consumer | I-10b plus consumer-specific G-3/I-14/claim packet |

## 10. Final metric adjudication

The metric definitions are implementation-ready because every construct has a denominator, evidence record, lifecycle, and consequence. Phase 0 now passes: I-10a, I-11, and P-1 have dated passing receipts and sealed evidence. Politico A-0, census C-1, normalization conservation C-1, and I-13 pass for the sealed restricted snapshot. C-2 outcome conservation also passes mechanically, but its identity result remains `PILOT/REPORT`: zero of the deterministic 200 strict candidates have independent adjudication, estimated precision is therefore null, and canonical merges remain zero. LDA C-5 still fails unique-UUID reconciliation. Metrics without a sealed provenance manifest remain `LEGACY_UNMANIFESTED`; they may report or fail closed but cannot pass. Phase 0 exit does not enable any source, approve canonical corpus publication, establish parser/ER accuracy, or arm analysis/engine consumers.
