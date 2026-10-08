# Staffer Network Database Overview — 2026-09-01

## Direct answer

The corrected answer has three levels:

- **890 people have a structured source profile whose captured employment is role/employer complete**, out of 912 people with at least one structured source-profile employment assertion (**97.588%**; **3.512%** of the sealed census). This is the practical profile count the earlier zero obscured. It ignores education, dates, duration, chronology, canonical promotion, and lifetime attestation.
- **4,802 profiles are field-complete on the employment assertions collected so far**, out of 9,847 people with substantive collected employment evidence (**48.766%**; **18.950%** of the sealed census). Education and every date, duration, chronology, and gap field are ignored for this number.
- **0 profiles have an external exhaustive-lifetime attestation.** This is a separate legalistic provenance state, not the answer to how many usable employer/role profiles exist.

For the 890 figure, the person must have at least one employment assertion in the structured working-history, rapid structured-profile, or authenticated-profile ledgers, and every such assertion must have both an employer and role/title. For the broader 4,802 figure, the same field rule is applied across every collected evidence lane. Candidate rows remain candidates; the audit does not promote them. A person with no employment evidence cannot pass vacuously.

Two control cases make the distinction concrete:

- **Stephanie Belk (`lda:lobbyist:147663`) is included in the 890.** Her authenticated profile contains five employer/role-complete jobs. The V5 prototype contains 12 provisional employment episodes, the same-person LDA covered-position claim is represented, and her profile row is field-complete under the user-requested education/time exclusion.
- **Gordon Holzberg (`lda:lobbyist:147664`) is not yet included in the 890 because his earlier profile capture was not conserved into any current structured profile ledger.** The database still holds his exact LDA identity, exact LegiStorm crosswalk (`267918`), a field-complete LDA claim containing five Hill role/office mentions, and his registrant affiliation, but zero canonical episodes. This is a capture-conservation defect and repair requirement—not evidence that no employment information exists.

Two narrower representation counts must remain visible:

- **2,672 V5 field-complete people**: at least one provisional V5 episode and every episode has a normalized container and title. This says the prototype rows are structurally usable; it does not say all source facts were represented or authorize canonical promotion.
- **460 strict V5 LDA-representation-complete people**: at least one substantive LDA covered-position claim and every such claim ID is present in V5 episode support.

There are also **332 explicit-no-position-only LDA dispositions**. They are reported separately and are not counted as complete employment profiles. An LDA “no covered position” response is not evidence of no employment or of a complete lifetime history.

## Current corpus

| Layer | Current result | Interpretation |
|---|---:|---|
| Sealed LDA people | 25,340 | Full census denominator |
| People with structured source-profile employment | 912 | Exact person-ID union across working, rapid, and authenticated profile ledgers |
| Structured source profiles role/employer complete | 890 | Every captured source-profile job has both employer and role/title; education/time ignored |
| People with substantive collected employment assertions | 9,847 | Denominator for the relaxed content audit |
| Field-complete on collected assertions | 4,802 | Every collected assertion has employer/office and role/title; candidates are not promoted |
| Lifetime-history attested complete | 0 | No acquisition-closure or exhaustive-history attestation exists |
| Provisional V5 people | 2,672 | All 18,815 V5 episodes are structurally usable within the prototype |
| Strict all-LDA-claim represented people | 460 | Every positive LDA claim ID is carried into V5 support |
| LDA registrant associations | 25,469 across all 25,340 people | All 25,469 are represented in the affiliation membership layer |
| Service-affiliation memberships | 102,162 | 18,815 employment plus 83,347 annual registrant memberships |
| Shared-affiliation edges | 189,098 | Existing dated/filing-year overlap graph |

## Source inventory

| Evidence lane | Rows / people | Current treatment |
|---|---:|---|
| LDA covered-position claims | 41,262 substantive claims / 9,152 people | 2,812 claims are bound to V5 episode support |
| LDA explicit-no-position claims | 418 claims / 376 people | 332 explicit-only; 44 mixed with substantive claims |
| LDA registrant associations | 25,469 / 25,340 people | Fully represented as annual affiliation memberships |
| House payroll name-match candidates | 32,103 / 2,135 people | 3,552 corroborated rows for 352 people reached provisional promotion; remaining rows stay review evidence |
| Senate payroll name-match candidates | 6,953 / 2,798 people | 13,895 split interval promotions for 1,715 people plus 125 corroborated provisional rows for 110 people; nonunique and invalid observations remain blocked |
| Latest working-history corpus | 2,470 episodes / 835 people with episodes | 814 people have employer and title on every working-history episode; the artifact covers 1,371 processed people |
| Rapid structured profile evidence | 478 employment episodes / 72 people | 71 people are field-complete; `employment` and `employment_episodes` aliases are coalesced, never concatenated |
| Authenticated profile evidence | 74 employment facts / 10 people | All ten people reached provisional V5 materialization; education is ignored here |
| Bulk candidate adjudication | 235,454 decisions | Preserves 116,195 bulk public fact candidates plus official/source-native lanes; review-required rows are retained, not deleted |

## Material local lanes absent from V5

These sources are already on disk but are not represented in V5 support. They overlap and must not be summed.

| Omitted lane | Local evidence | Status |
|---|---:|---|
| House payroll 2016–2026 | 11,788 candidates / 3,355 people; 7,627 source-unique rows / 2,125 people | No support IDs in V5 |
| House 1997Q1 A8 | 453 candidates / 388 people; 310 single-candidate rows | No support IDs in V5 |
| A7 FEC employer observations | 979 dated point observations / 37 people | Candidate point evidence; no interval may be inferred |
| A7 LD-203 affiliations | 143,513 filings / 79,475 unique person-registrant-year triples | V5 covers 75,887 coarse triples, misses 3,588 triples involving 2,478 people, and retains no A7 IDs |
| Politico | 560 role observations / 412 people | Review-required role text; omitted |
| LittleSis LDA-linked candidates | 12,726 observations / 3,907 people | Review-required identity candidates; omitted |
| Public LinkedIn ledger | 177 employment facts / 39 people | Candidate-only; omitted |
| Working-history corpus | 2,470 employment facts / 1,371 processed people | Not a direct V5 input |
| Rapid structured profiles | 478 source-profile episodes in the current input | The narrow V5 promoter does not conserve this current source ledger directly |
| Bulk public corpus | 97,358 employment candidates / 12,672 people | 77,028 review-required; 20,330 rejected upstream |

The omitted candidate-family union contains **11,337 people with no V5 provisional employment**.

The source-native industry layer is also absent: **4,816,559 edges**—2,741,465 `NAMED_ON_ACTIVITY`, 1,037,547 `FILED_BY`, and 1,037,547 `FOR_CLIENT`. V5 therefore has registrant co-filing affiliations but does not yet provide the requested client/industry-actor layer. Separately, the source-native corpus preserves 368,995 LittleSis `Position` relationships, including 226,370 undated positions, plus 5,773 Quorum-derived `STAFFS_FOR` records; these are not exact LDA-person employment facts without an accepted binding.

## Overlooked or underused data

The principal omission is the non-temporal LDA content.

- **38,450 of 41,262 substantive LDA claims are not carried in V5 episode support.**
- **21,650 of those unrepresented claims already contain both a role mention and an employer/office mention.** They are unusable as dated episodes without temporal evidence, but they are immediately useful as non-temporal affiliation candidates.
- The remaining positive LDA claims divide into 7,020 role-only, 5,307 employer-only, and 4,473 with neither parser class. These require targeted parsing or another source before they can form complete role-employer records.
- **2,970 field-complete collected profiles are not present in the V5 episode population.** Their evidence remains in source/candidate ledgers rather than the prototype graph.
- The latest working-history and rapid structured corpora are not direct inputs to the V5 promoter. Parts flow through the V3 provisional ledger, but the source artifacts are not fully conserved into a dedicated non-temporal canonical-affiliation layer.

The official payroll and bulk-public rows are not missing. They are present in candidate/adjudication ledgers. Most are intentionally unresolved name-only, ambiguous, or unstructured evidence and should not be silently treated as verified identity matches.

## V5 conservation defects

V5 is a narrow materialization, not a conserved database build.

- Its receipt records no input hashes, generator hash, or verifier hash.
- The 2,712-row blocked ledger (SHA-256 `a79bf2fc58c9892b7c1740bde5e350da27cb798a525a459d8bf952351a4ca71b`) is omitted from the receipt payload manifest and twin verifier.
- `blocked_records=2712` covers only Senate-stage exclusions, not upstream or omitted-lane exclusions.
- All 1,243 covered-position promotions incorrectly say `covered_position_parser_gate=NOT_APPLICABLE` because of a prefixed-lane comparison bug.
- 7,965 promotion decisions use automatic `NORMALIZED_LITERAL` container slugs while reporting the retained container gate as passed. These are deterministic container candidates, not substantive container adjudications.

## Database implementation status

V5 prototype facts exist as deterministic, receipt-bound NDJSON ledgers: 18,815 provisional employment episodes, 102,162 affiliation memberships, and 189,098 shared-affiliation edges. The current verification-selected generation is `employment_promotion_generation_20260901_v5_primary`; it is not canonically promoted or armed for production.

There is **no materialized SQLite, DuckDB, Parquet, or other queryable database file in the workspace**. `fec/staffer_network/schema.sql` supplies a relational framework—including `canonical_fact`, `fact_support`, `network_build`, and `network_edge`—but it has not been populated. Accordingly:

- “V5 prototype facts are built” is true at the ledger layer;
- “canonical employment facts are built” is false under the governing completeness and identity gates;
- “the canonical relational database is built” is false.

## Required implementation revision

Add a separate, fail-closed **non-temporal affiliation fact** layer instead of forcing undated claims into dated employment episodes.

1. Materialize every parseable employer/office mention as a source-bound affiliation candidate with its claim ID, person ID, role mentions, exact spans, and a role-container linkage status.
2. Keep multi-role/multi-office claims explicit. A common organization membership may be represented without inventing a one-to-one role pairing.
3. Build organization groups from accepted source-native LDA identity and normalized containers.
4. Do not assign overlap days or the temporal edge formula to undated facts. Emit an evidence-weighted affiliation candidate edge separately; temporal weighting becomes available only when dates are later attached.
5. Load canonical episodes, fact support, non-temporal affiliations, memberships, and edge builds into the relational schema with receipt/hash bindings.

## Audit receipt

The revised source-neutral evidence inventory produced byte-identical 25,340-row outputs. Its `PASS` means scope, row conservation, exact person-bound support joins, hashes, and deterministic serialization passed; it does not mean employment histories are complete.

- Primary generation: `audits/staffer_network/profile_evidence_inventory_20260901_v4_primary`
- Twin generation: `audits/staffer_network/profile_evidence_inventory_20260901_v4_twin`
- Payload SHA-256: `a9a3f2a4a8e33196b3ac9a58cf7181ab86eff6e19669e27246bb204eb5d06f8c`
- Receipt SHA-256: `babe4d0172c8bb5ce810387169af1014ded060c7c1c849d6b165ce7e7ae94aac`
- Credential/token scan: zero matches
- Focused tests: 7 passed
- Prior full-suite baseline: 260 tests and 73 subtests passed; this isolated revision reran the seven focused classification tests

The current pointer is `data/staffer_network/profile_evidence_inventory_current.json`.
