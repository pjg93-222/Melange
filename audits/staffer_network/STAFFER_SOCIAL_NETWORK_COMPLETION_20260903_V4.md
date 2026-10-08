# Staffer Social Network v4 — Verified Completion and Coverage Report

Generated and independently rechecked 2026-09-03. This report describes the
verified candidate-plane graph and its explicit source limits. It does not promote
identity, employment, office, or network weights into canonical production tables.

## Audited outcome

- Primary graph build: **PASS**
- Deterministic twin graph build: **PASS**
- Independent full-graph verifier: **PASS, 0 failures**
- Primary/twin substantive artifacts: **byte-identical**
- Gordon Holzberg regression: **PASS** — one person, Adams to Sykes, one
  day-precise abutting move with a zero-day gap
- Stephanie Belk regression: **PASS** — one payroll-spine person attached to the
  David Vitter office
- Canonical promotions: **0**
- Review status: **REVIEW_REQUIRED**
- Modeling dials: retained as **UNTESTED_DEFAULTS_PENDING_FREEZE**

## Source coverage

| Source | Covered corpus | Verified result |
|---|---:|---|
| House payroll | 2009Q3–2026Q2, 68 quarters | PASS; 1,083,510 observations and 141,024 spans |
| House PDF era | 2009Q3–2015Q4, 26 quarters | PASS; 385,480 admitted rows |
| Senate payroll | 2011–2026 collection | PASS in combined spine; latest observed period 2025-10-01 |
| Combined payroll spine | House + Senate | PASS; 144,693 people and 204,700 office spans |
| LDA sealed corpus | 25,340 people | Full sealed population retained |
| LDA match lanes | 6,143 people | 6,072 linked, **98.8442%** |
| Politico current directory | 18,618 profiles | 18,618 current cards collected |
| Politico strict payroll bridge | 18,618 profiles | 8,769 linked profiles / 8,768 people |
| Politico profile histories | Committee-first queue | 277/2,584, **10.7198%**, zero failures |
| Politico profile histories | Full current directory | 277/18,618, **1.4878%** |

“All years” means all years within these acquired source windows. House before
2009Q3 and Senate before 2011 are not represented in the corpus.

## Reconciliation results

The Q2-aware payroll spine contains 144,693 people, 204,700 person-office spans,
2,032 Member-office index rows, 5,773 current staffer link rows, and 10,579 LDA
spine link rows. The independent spine verifier passed with zero failures and the
primary/twin payloads are identical.

The strict Politico bridge contains:

- 8,769 linked profiles, covering **47.0996%** of all 18,618 profiles
- 8,769/13,786, or **63.6080%**, of profiles carrying supported office evidence
- 7,291 exact Member-office matches
- 1,494 exact committee-employer matches
- 199 ambiguous profiles retained as unresolved
- 4,818 profiles not on the current payroll snapshot
- 4,832 profiles without a supported current role
- 11,525 person-policy memberships over 1,677 payroll people and 36 policy areas
- 1,888 current committee assertions
- negative control 34/13,786, **0.246627%**, below the 1% acceptance bar
- zero promotions

The bridge is exact normalized first/last name plus an exact current Member
bioguide or allowlisted-normalized committee employer. No fuzzy repair was admitted.

## Verified network

| Measure | Verified value |
|---|---:|
| Total nodes | 148,334 |
| Person nodes | 144,693 |
| Office/container nodes | 1,833 |
| LDA organization nodes | 1,772 |
| Politico policy-area nodes | 36 |
| Total emitted edge rows | 15,343,553 |
| Guaranteed co-tenure edges | 12,498,349 |
| Possible-only co-tenure rows, zero weight | 2,639,891 |
| Same-container pairs rejected for zero overlap | 16,001,459 |
| Person-to-office membership rows | 187,789 |
| LDA revolving rows | 5,999 |
| Person-to-policy membership rows | 11,525 |
| Largest weighted component | 148,041 nodes, **99.8025%** |
| Largest person-only co-tenure component | 144,107 people, **99.5950%** |

The layers remain separate: co-tenure, office membership, LDA revolving, and
Politico policy area. Member offices and Congress remain attachment containers.
No Member-to-Member or person-to-person sequence edge is emitted, and no social
edge is emitted for two people whose employment intervals do not overlap.

## Committee structure

- 26,212 committee episodes
- 1,058 with known majority/minority side, **4.0363%**
- 25,154 side unknown, **95.9637%**
- 1,468,707 committee-derived guaranteed edges
- committee-only largest component: 19,836 people
- largest person component after committee-edge removal: 129,435 people

Politico committee assertions are current point observations. They are not
backdated across payroll history. The opposite-side committee parameter remains
structurally supported but largely unpopulated until month-bounded profile histories
are acquired.

## Independent verification

The verifier used full per-container pair enumeration rather than the builder's
interval sweep and independently reproduced:

- 31,139,699 distinct same-container candidate pairs
- 12,498,349 guaranteed pairs
- 2,639,891 possible-only pairs
- 16,001,459 zero-overlap rejections
- every layer and status count
- a 2,000-edge guaranteed-day sample with zero mismatches
- component structure and committee ablations
- trajectories, named regressions, and zero-promotion tripwires

Primary/twin SHA-256 parity was rechecked for all substantive graph artifacts:

- edges: `0F0851F923C5153A9E7B6500FA1F66FB8AE5EABDF6FAA4CEF7DEC5F349FE2C6E`
- node scores: `458A59C9EFE4529C14C6C9C2E87EF8BBFC0442993E5796DE4936D2DA94916041`
- trajectories: `7352E4A3C403EF253DAC1AE358AC1F41EB2AE4957BFC241368D0633E80FCDC2E`
- office moves: `3160294DE5AD6D15987ADCE1920FCFF6180B01E62D4C0D4E3704BBAFAD7EB5CD`
- graph receipt: `36B08A581F98229D35C50620A8D212EA7834ABDE96F817DCDAAB724E8403FB73`
- independent verification receipt: `3A0D953135898443B75E234CBBCAE147384A94C2BDDEF34E78692B835A60C3CB`

The two manifests intentionally differ only in `generation_id` (`primary` versus
`twin`). Their canonical output hash and complete artifact tables are identical.

## Receipt clarification

`house_personnel_ledger_20260903_v5_verification` is a superseded verifier run that
rejected the corrected PDF candidate schema v2 because the verifier still required
schema v1. No data invariant failed. The verifier was updated to accept one uniform
supported schema version and rerun at
`house_personnel_ledger_20260903_v5_verification_v2`; that run is **PASS**, all 40
checks are true, its independent PDF/CSV recounts match all 68 quarters, and its
twin check reports every substantive file byte-identical.

## Remaining coverage limits

1. Authenticated Politico individual-profile histories are only 277/18,618 complete.
2. Historical committee side is 95.9637% unknown and cannot be inferred safely from
   the current Congress.
3. 592 LDA revolving rows retain non-unique legacy House office keys.
4. 71 people in the defined LDA match lanes remain unlinked.
5. House before 2009Q3 and Senate before 2011 remain outside the acquired corpus.
6. The graph remains candidate-plane and review-only; no canonical weights or
   identities have been promoted.

The network is therefore complete and independently verified for the declared
payroll, LDA, and current Politico-card corpus. The overall historical Politico
profile-history corpus is not yet exhaustive.

## Final reconciliation 20260905

The post-crawl finishing chain completed on 20260905 and wrote its full
reconciliation to `STAFFER_SOCIAL_NETWORK_FINAL_RECONCILIATION_20260905.md` in this directory. That document carries the
final crawl coverage, the bridge and network counts, the SHA-256 of every primary
artifact and verification receipt, the limitations copied from the receipts, and the
remaining owner-gated next steps.

New generations: `politico_payroll_direct_links_20260905_v4_primary`, `staffer_social_network_20260905_v5_primary`, with byte-identical
twins and independent verification receipts. Nothing was promoted to canonical and every
generation remains REVIEW_REQUIRED.

Chain log: `finish_chain_20260905T191410Z.log`. Chain run id: `run-20260905T191410Z-finish`.
