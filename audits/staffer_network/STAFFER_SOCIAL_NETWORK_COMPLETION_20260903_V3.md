# Staffer Social Network v3 — Completion and Coverage Report

Generated 2026-09-03. This report describes the verified candidate-plane graph and
the exact limits of the source corpus. It does not promote any identity, employment,
office, or network weight into a canonical table.

## Outcome

- Primary build: **PASS**
- Deterministic twin: **PASS**
- Primary/twin substantive artifacts: **byte-identical**
- Independent verifier: **PASS, 0 failures**
- Gordon Holzberg regression: **PASS** — one person, Adams→Sykes, one day-precise
  abutting move with a zero-day gap
- Stephanie Belk regression: **PASS** — one payroll-spine person attached to the
  David Vitter office
- Canonical promotions: **0**
- Review status: **REVIEW_REQUIRED**
- Modeling dials: retained as **UNTESTED_DEFAULTS_PENDING_FREEZE**

## Source coverage

| Source | Covered corpus | Verified coverage |
|---|---:|---|
| House payroll | 2009Q3–2026Q1, 67 quarters | 2009Q3–2015Q4 official PDFs; 2016Q1–2026Q1 detail CSVs |
| Senate payroll | 2011–2026 collection | Latest observed official period is 2025-10-01 |
| Payroll spine | 142,135 people; 201,239 source spans | All admitted rows conserved; 142,135 distinct people |
| LDA sealed corpus | 25,340 people | Full sealed population retained |
| LDA match lanes | 6,143 people | 6,072 linked, **98.8442%** |
| Politico current directory | 18,618 profiles | 18,618 current cards collected |
| Politico strict payroll bridge | 18,618 profiles | 8,543 linked profiles / 8,542 people; **45.8857%** of the full directory and **61.9687%** of profiles with supported office evidence |

“All years” therefore means all years in the declared source windows above. It does
not mean all historical congressional payrolls: Senate before 2011 and House before
2009Q3 are outside the acquired official corpus, and no Senate publication later
than 2025-10-01 was observed.

## Politico reconciliation

- 18,618 unique current profiles
- 8,543 strict links, requiring exact normalized first/last name plus an exact
  current Member bioguide or allowlisted-normalized current committee employer
- 7,074 Member-office matches
- 1,485 committee-employer matches
- 193 ambiguous profiles left unresolved
- 5,050 profiles not present on the current payroll snapshot
- 4,832 profiles with no supported current role for this bridge
- 11,159 unique person-policy memberships over 1,633 payroll people and 36 policy areas
- Negative control: 33 of 13,786 profiles matched a deliberately rotated false office,
  **0.239373%**, below the 1% acceptance bar
- Every Politico assertion is current-snapshot-only with `duration_weight=0`

The individual Politico profile-history crawl is not complete. Current directory
cards are complete, but historical employment month ranges, education, and explicit
majority/minority labels have only been validated on sample profiles. Those data
must not be backdated into historical committee episodes until the full profile crawl
is acquired and verified.

## LDA reconciliation

- LDA revolving source rows: 6,176
- Exact-bioguide mappings: 5,301
- Additional exact chamber+office-key mappings recovered: 283
- Total mapped source rows: 5,584, **90.4145%**
- Remaining unresolved source rows: 592
- Emitted revolving graph rows after container expansion/deduplication: 5,999
- Organizations represented: 1,772

The remaining 592 rows are dominated by legacy House surname-only or truncated keys
such as `HON:RODGERS`, `HON:JOHNSON`, and `HON:BA`. They remain unresolved because a
surname inference would merge different Members. No fuzzy repair was admitted.

## Final network

| Measure | Verified value |
|---|---:|
| Total nodes | 145,773 |
| Person nodes | 142,135 |
| Office/container nodes | 1,830 |
| LDA organization nodes | 1,772 |
| Politico policy-area nodes | 36 |
| Total emitted edge rows | 15,206,625 |
| Guaranteed co-tenure edges | 12,365,004 |
| Possible-only co-tenure rows, zero weight | 2,639,846 |
| Same-container pairs rejected for zero overlap | 15,459,247 |
| Person→office membership rows | 184,617 |
| Revolving rows | 5,999 |
| Person→policy membership rows | 11,159 |
| Largest weighted component | 145,480 nodes, **99.7990%** |
| Largest person-only co-tenure component | 141,523 people, **99.5694%** |

The graph has four separate layers: co-tenure, office membership, LDA revolving, and
Politico policy area. Congress/Member offices remain attachment containers; no
Member-to-Member or person-to-person sequence edge is emitted. A person-to-person
edge requires actual temporal overlap.

## Structural repairs relative to v2

- 199 leading-year office fragments collapsed: 2,029 published keys → 1,830 graph
  containers. No transformation other than a leading `FISCAL YEAR YYYY ` or `YYYY `
  token was allowed.
- A resolved `admin` or `committee` classification may supersede `unresolved` for the
  same normalized office; two conflicting resolved kinds still hard-fail.
- Guaranteed co-tenure edges increased by 260,145.
- Politico policy memberships increased from 6,442 to 11,159.
- LDA revolving rows increased from 5,717 to 5,999.
- Total graph rows increased from 14,958,104 to 15,206,625.

## Committee layer

- Committee episodes: 25,770
- Side known as majority/minority: 1,053, **4.0861%**
- Side unknown: 24,717, **95.9139%**
- Committee-derived guaranteed edges: 1,446,827
- Committee-only component: 19,577 people
- Largest person component after removing committee-derived edges: 126,966 people

Politico supplies 1,889 current committee assertions, but they are point observations.
They are retained as review-only metadata and are not applied across historical
payroll intervals. The 0.40 opposite-side kappa remains structurally reachable but
historically unpopulated until month-bounded profile histories are collected.

## Verification evidence

The independent verifier used full per-container pair enumeration instead of the
builder's sweep line and reproduced exactly:

- 30,464,097 distinct same-container candidate pairs
- 12,365,004 guaranteed pairs
- 2,639,846 possible-only pairs
- 15,459,247 zero-overlap rejections
- every layer count
- a 2,000-edge guaranteed-day sample with zero mismatches
- component structure, committee ablations, trajectories, named regressions, and
  zero-promotion tripwires

Key hashes:

- Edge artifact: `0C2CCB5F134200A534E50CF66194AFA89AD6A4361E2A01A834F9A5E665E9713C`
- Primary receipt: `2F9E3258ABC228CDC239D9A9F28E347BF2B273AC20E37DEC70E78E5997C37643`
- Independent verification receipt: `35820BE577C305E0F6C51A90AE4B2A35C73C6291194575314565592719D2370B`

## Remaining coverage limits

1. Complete authenticated Politico individual-profile histories are still outstanding.
2. Historical committee side is 95.9139% unknown and cannot be safely inferred from
   the current Congress.
3. 592 LDA revolving rows retain non-unique legacy House office keys.
4. 71 people in the defined LDA match lanes remain unlinked.
5. Payroll years outside House 2009Q3+ and Senate 2011+ are not in this corpus.

These are explicit source-coverage limits, not hidden graph defaults. The v3 graph is
complete and verified within the declared corpus, but the overall historical research
corpus is not exhaustive beyond those boundaries.
