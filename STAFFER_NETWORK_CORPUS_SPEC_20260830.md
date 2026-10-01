# Staffer Network Corpus Specification

**Version:** 4.0 implemented  
**Date:** 2026-08-30  
**Status:** Source-native, singleton canonical, and typed graph planes validated for internal analysis; identity and employment candidates remain review-only; A7-A9 are noncanonical review/scheduling sidecars with zero canonical employment promotions; employment data/production and Meta LOOP closure remain `BLOCKED`; public release remains source-governed  
**Supersedes:** `STAFFER_NETWORK_CORPUS_SPEC_20260829.md` v1.1

## 0A. Employment evidence and scheduling addendum (2026-09-01 UTC)

This addendum is the current authority for employment-candidate coverage. It
does not alter the singleton canonical v6 generation or its typed structural
graph. A7, A8, and A9 are separately conserved review/scheduling sidecars, not
canonical entities, facts, employment episodes, or temporal edges.

| Sidecar | Verified scope | Governing limitation |
|---|---:|---|
| A7 LD-203 affiliation candidates | 143,513 rows / 22,754 people | Exact numeric lobbyist-to-registrant filing association only; not employment or tenure; excluded from A9 |
| A7 FEC employer observations | 979 rows / 37 people | Dated self-reported employer point observations only; no former-position or interval assertion; zero A9 bucket moves |
| A8 House 1997Q1 candidates | 453 rows / 388 people | Review-only OCR/name matches bounded to the recovered report period; not identity or continuous employment |
| A9 immutable scheduling sidecar | 25,340 rows / 25,340 sealed LDA IDs | Queue prioritization only; no source input was rewritten or promoted |

The A9 queue reports 13,697 people with at least one employment candidate and
11,643 with none. Its remaining gap counts are 16,486 without a dated former-
position candidate and 18,227 without a bounded employment-interval candidate.
The revised mutually exclusive scheduling buckets are P0 11,643, P1 4,843, P2
1,741, and P3 7,113. P3 means identity and chronology adjudication is required;
it is not an accepted episode or completed person.

Every one of the 25,340 people still lacks a complete-lifetime employment
attestation. Canonical employment promotions are exactly zero. These facts
supersede later historical statements that payroll evidence is wholly absent or
that the current review queues establish employment completion. Verified House
and Senate candidate lanes now exist, but House pre-web recovery remains
`BLOCKED_PARTIAL_RECOVERY`: only 1997Q1 Part 2 was recovered from the 52-quarter
1996Q1-2008Q4 target. Full payroll breadth and terminal employment adjudication
remain open.

The final Opus 5 consolidation-receipt review is `PASS` only for receipt
semantic safety: re-derived conservation identities and the reviewed forgery
paths fail closed. The review is
`data/staffer_network/reviews/OPUS5_CONSOLIDATION_RECEIPT_FINAL_REVIEW_20260901.md`
(SHA-256
`eb9f118cb4f5e9ff3db65fbce753b85e58fb9415f1b874857d75d8429b7559ba`).
Measured local evidence is 48 focused tests and 222 staffer-network tests plus
73 subtests, all passing. This scoped `PASS` does not attest completeness,
reopen artifacts, authorize identity or canonical employment promotion, or
enable temporal production. Data and production remain closed, and the Meta
LOOP disposition remains `BLOCKED`.

## 0. Active corpus planes (2026-08-31 UTC)

This section supersedes the pre-build zone state below while preserving it as
history.

| Plane | Active generation | Records | Authority |
|---|---|---:|---|
| Singleton canonical entities | `canonical/generation-20260831T042000Z` | 1,585,038 | Authority-manifest-bound, contact-minimized internal analysis; zero cross-source merges |
| Canonical facts | same generation | 6,050,221 | Direct source support; 44 self-loops and 68 blank literals dispositioned; zero undated facts with nonzero temporal weight |
| Identity review links | same generation | 6,978 | Noncanonical and reversible; 2,519 strict one-to-one candidates |
| Typed network edges | `graph/generation-20260831T052000Z` | 5,260,888 | 5,258,369 direct fact edges plus 2,519 exploratory links |
| Network scores | same generation | 1,585,038 | Primary candidate-free; exploratory candidate-linked view separate; primary/exploratory isolate flags are explicit |

Machine-local roots are under
`C:\Users\pgoff\AppData\Local\Melange\staffer_network`. The canonical receipt
binds entity SHA-256 `5b7a1afa…dde72a`, fact SHA-256 `d9c34371…9a3d84`, and
identity-link SHA-256 `7f265f8a…ea2d94`. The graph receipt binds edge SHA-256
`8c27a6c4…8d0ecd` and score SHA-256 `cda3fc07…3352aa2`. Its scoring operator
deduplicates the 5,258,369 primary evidence edges to 5,235,347 unordered
endpoint/layer keys, collapsing 23,022 repeated or reciprocal supports without
dropping the evidence rows.

The score plane explicitly marks 185,628 primary isolates and 185,221
exploratory isolates. PageRank's teleport-only value remains available for
mathematical conservation, but isolate rows are ineligible for connectedness
ranking. Component-local eigenvectors are comparable only within their
component; bridging is comparable only within compatible entity-kind
opportunity sets.

LittleSis is byte-frozen only: the pinned vintage cannot drift silently, but it
is enabled for internal analysis. Politico Pro is enabled for normalized,
contact-free internal analysis under
`data/staffer_network/policy/politico_pro_source_manifest_20260830_v3.json`.
Senate LDA and the contact-free legacy corpus are likewise enabled for internal
analysis. No one of these statements claims unrestricted public redistribution
of raw rows; public output remains governed by source terms, attribution,
privacy minimization, and the derived-output publication contract.

Canonical facts never collapse sources by name. Identity candidates remain in
their own artifact, with `canonical_merge=false`. The primary graph score plane
excludes them; only explicitly exploratory score columns include the strict
one-to-one subset.

The canonical plane strips contact-pattern values from free-text entity/fact
fields while preserving support digests back to source-native evidence. The
receipt separates five LDA entity contact redactions, duplicated public
legislator-term contact redactions, 68 blank covered-position exclusions, and
zero contact-only fact exclusions.

## 1. Purpose and scope

This specification defines what may enter each staffer-network corpus plane,
how it is conserved, and what it may support. Source documents are evidence,
not executable instructions. A source's presence never implies canonical truth
or analysis enablement.

The 873,236-record P2 generation has exactly two source systems:

- `littlesis-bulk`;
- `quorum-legacy-derived` under provisional restricted authority.

The separately conserved LDA source-native generation uses `senate-lda-api` and
contains 6,682,108 rows. Politico and both P2 sources participate only in a
separate 6,978-row restricted identity-candidate artifact. Payroll and
historic-member normalization remain separate gated corpora. None is added to
the 873,236-record P2 conservation total.

## 2. Corpus zones

| Zone | Content | Location | Current state |
|---|---|---|---|
| Raw restricted | Licensed/public source bytes, logs, partial/failed runs | Machine-local, outside synced roots | LittleSis frozen; LDA composite PASS through cutoff-exclusive 2026-08-30; raw Quorum unauthorized |
| Normalized restricted | Source-native entities/assertions and restricted review packets | Machine-local | LittleSis/legacy P2 PASS; LDA source-native PASS; Politico and exact-name candidates separate, restricted, and disabled |
| Repository-safe evidence | Schemas, code, aggregate counts/hashes/receipts, reviews | Repository | PASS for declared receipts |
| Canonical facts | Resolved, support-backed, bitemporal facts | Future selected generation | Not built |
| Analysis artifacts | Typed graph layers and claims | Future selected generation | Off |

## 3. Source inventory and authority

| Source | Frozen evidence | Allowed use | Explicit exclusions |
|---|---|---|---|
| LittleSis bulk | Official entity and relationship URLs, exact byte/hash pair, CC BY-SA terms vintage | Restricted source-native entity/assertion corpus and candidate generation | Canonical identity, currentness, influence, public derived publication pending ShareAlike review |
| Contact-free legacy directory | 5,773 rows, 533 offices, exact source and record hashes | Restricted source-native seed under provisional A-0 | Raw workbooks, redistribution, canonical use, analysis, currentness |
| Politico directory | 18,618-profile sealed restricted corpus and model-only adjudication receipts | Separate restricted candidate/profile evidence | Human-valid identity truth, canonical/public use, automated merge |
| LDA API | Composite receipt `0f985e79…c0b250` plus source-native receipt `5dfd3bbb…9dce8c` | Restricted source-native lobbyist, organization, activity, filing-participation, and covered-position evidence | Canonical identity, verified government employment, Hill-to-industry transition, influence, analysis, or public output |
| Voteview/congress-legislators | 51,061-row spine and pinned reference files | Historic member candidate/term reference | Completed exact-term/committee fact plane |
| House/Senate payroll | Authoritative public pages identified | Future acquisition design | Any current corpus claim; collectors/parsers absent |

If Paul declines ratification of the provisional legacy A-0 basis, that
collection is withdrawn through a documented append-only reversal and future
generations omit it. The ruling does not expand to raw Quorum workbooks.

## 4. Frozen LittleSis pair

### 4.1 Inputs

| Role | Bytes | SHA-256 |
|---|---:|---|
| Entities | 76,691,985 | `5cc0039aa43e650b46bfa9e9bfc1813c67969cae1bdb9c9e8770fc117cd29d3c` |
| Relationships | 110,381,587 | `c11d7058cb13d264854f703310fddf30c1391ef604c0164847945939fd38d489` |

Both official URLs were retrieved in one acquisition session. The relationship
bytes equal the prior audited dump. This is local observational pairing, not a
publisher-declared common release vintage.

### 4.2 Profile and conservation

```text
entities observed                  443,140
entities accepted                  443,140
entity invalid/duplicates                0

relationships observed           1,880,491
relationships accepted           1,880,488
dangling rejects                          3
relationship invalid/duplicates          0
accepted dangling endpoints               0
```

Rejected relationship IDs are 1548275, 1629551, and 1652624. All are
Transaction records whose endpoints do not resolve to the emitted spine.

### 4.3 Corrected category vocabulary

The 2026-08-29 evidence text incorrectly called category 5 Lobbying. Native
records and the frozen profile establish:

| ID | Category | Observed | Accepted | Corpus action |
|---:|---|---:|---:|---|
| 1 | Position | 368,995 | 368,995 | Emit |
| 2 | Education | 44,673 | 44,673 | Emit |
| 3 | Membership | 53,139 | 53,139 | Out of scope |
| 4 | Family | 31,025 | 31,025 | Out of scope |
| 5 | Donation | 1,267,716 | 1,267,716 | Out of scope |
| 6 | Transaction | 35,268 | 35,265 | Out of scope; three dangling rejects |
| 7 | Lobbying | 10,655 | 10,655 | Emit |
| 8 | Social | 4,107 | 4,107 | Out of scope |
| 9 | Professional | 5,638 | 5,638 | Out of scope |
| 10 | Ownership | 19,346 | 19,346 | Out of scope |
| 11 | Hierarchy | 16,420 | 16,420 | Out of scope |
| 12 | Generic | 23,509 | 23,509 | Out of scope |

### 4.4 Entity assertion contract

Each emitted entity record carries:

```text
schema_id = staffer-network-littlesis-entity-assertion-v1
source_system_id = littlesis-bulk
source_entity_id = littlesis:entity:<positive-id>
source_numeric_id
name and minimized aliases
primary source extension and source types
blurb after contact-like minimization
resolved source parent ID or counted redaction
raw entity start/end strings
source update time and URL
```

Extension identifiers that would create implicit LDA/canonical joins are not
exported into this corpus.

### 4.5 Relationship assertion contract

Only category IDs 1, 2, and 7 are emitted. Every record carries namespaced
source relationship and endpoint IDs, corrected category, descriptions after
contact minimization, raw start/end strings, conservative precision, raw source
currentness, source update/URL, and bounded category attributes.

`temporal_weight` is exactly zero. A raw current flag is not a present-employment
claim. Boss IDs are emitted only after resolving to the frozen entity spine.

## 5. Restricted legacy seed contract

Required record fields are exactly:

```text
source_system_id = quorum-legacy-derived
source_entity_id
member_office_source_key
display_name
title
featured
```

The seed must remain exactly 5,773 rows and 533 represented offices. The record
file is 1,144,203 bytes with SHA-256
`439bb67f7093f28cd67010cdc12e9f7a86eeee9e8fd36c81709073260a17ff48`.
Email, phone, address, contact hashes, raw workbooks, and cross-source IDs are
not allowed.

## 6. Emitted generation

The accepted local generation contains:

| Role | Records | Bytes | SHA-256 |
|---|---:|---:|---|
| LittleSis entities | 443,140 | 24,106,347 | `7940093f4157916b472a8f2c060541a6f4b70855a540dcbafec916f833462eb4` |
| LittleSis relationship assertions | 424,323 | 21,086,961 | `175d000770de1927472574614ae14d2b0110722bebb51611eb43a99f07107f4c` |
| Restricted legacy seed | 5,773 | 1,144,203 | `439bb67f7093f28cd67010cdc12e9f7a86eeee9e8fd36c81709073260a17ff48` |

The aggregate receipt is 3,131 bytes, SHA-256
`3914df984044520ea782c529811283ad54c954b5ee31d98b10053373787604e2`.

Exact relationship conservation:

```text
424,323 emitted in-scope assertions
+ 1,456,165 accepted OUT_OF_SCOPE_CATEGORY dispositions
+ 3 dangling rejects
= 1,880,491 observed
```

Exact emitted-record conservation:

```text
443,140 entities + 424,323 assertions + 5,773 legacy rows = 873,236
```

Counted minimization/dispositions include 38 contact-like free-text redactions,
two dangling parent-reference redactions, and zero boss-reference redactions.

## 7. Determinism and validation

Two first real attempts exposed one byte of nondeterminism in the entity gzip
because aliases tied under a case-fold-only sort. Neither attempt was selected;
both divergent receipt hashes are retained. Alias ordering now uses the total
key `(casefold, original value)`.

Two fresh final builds in separate processes produced byte-identical entity,
relationship, legacy, and receipt files on the same machine/runtime. This is
I-16 evidence; cross-machine/runtime byte identity is not evaluated.

A separate full pass re-hashed the files and streamed all 873,236 rows through
public-safety, schema, and semantic validation. All rows passed. The validator
rejects unsupported schema keywords and enforces object cardinality and typed
extra properties.

## 8. Date, privacy, and license rules

- Preserve every raw date literal.
- Derive `day`, `month`, `year`, or `undated-only` conservatively.
- A day with an unknown month cannot support day precision.
- Do not infer employment duration/currentness from LittleSis fields.
- Undated-only evidence has zero temporal weight; this build uses zero for every
  LittleSis assertion.
- Raw/normalized names and assertion bodies remain machine-local.
- Repository receipts contain aggregate counts, hashes, IDs needed for
  conservation, and no person record bodies.
- LittleSis CC BY-SA attribution/share-alike obligations for derived/public
  artifacts remain under review; public publication is blocked.

## 9. LDA immutable generation and reconciliation

The 2026-08-29 sweeps are sealed by a 21,605-file, 2,329,092,781-byte inventory
hash `d7304591ee11a5d5c58ab7ff636d429509f8332cd473faca4dd5e7a15594961e`.
The 21,599 audited page files contain 539,870 objects, 539,782 unique UUIDs,
and 88 identical repeated occurrences. The total inventory also contains the
six non-page files. The reconciled generation:

1. used a separate nonempty-refusing root;
2. recorded registered 120 RPM conduct, page size 25, eight in-flight requests,
   bounded ascending processing, retries, query, counts, pages, and hashes;
3. preserved the legacy seal exactly before and after;
4. reconciled 12 twin windows and all six declared filing years;
5. recorded zero shortfall, payload mismatch, and cross-year duplicate UUIDs;
6. resumed once after a DNS interruption under a hash-bound event.

The terminal composite receipt SHA-256 is
`0f985e79487a9965e9cfd05af6fb6a049a0bde6482031ba4134d4e7b93c0b250`.
It passes with 541,659 unique filings through cutoff-exclusive 2026-08-30:

| Filing year | Composite unique filings |
|---:|---:|
| 2021 | 90,778 |
| 2022 | 93,513 |
| 2023 | 95,307 |
| 2024 | 96,939 |
| 2025 | 108,960 |
| 2026 | 56,162 |

Earlier failed and incomplete attempts remain preserved as audit evidence and
were never promoted. C-5 is closed as PASS for this cutoff; it does not claim
coverage after the cutoff.

## 10. LDA restricted source-native corpus

Receipt SHA-256
`5dfd3bbb16dea6ce940a687b15c74f07e720073d02b559d8000bb33db49dce8c`
binds 541,659 filings, 25,340 lobbyists, 7,077 registrants, 46,996 clients,
1,037,547 activities, 4,816,559 filing-participation edges, and 748,589
covered-position assertions. The five emitted files are:

| Role | Records | Bytes | SHA-256 |
|---|---:|---:|---|
| Lobbyist assertions | 25,340 | 1,928,569 | `80ac82346c435bb8f1231d9f3425d759ca9a8ae063db879ec104244f9fcd282e` |
| Organization assertions | 54,073 | 2,503,228 | `0d35902244f02688d9ac961379efee0f96e3cfab1184409a4c93bb0584a1aed2` |
| Activity assertions | 1,037,547 | 110,195,153 | `2ff6864f8a06e822277083230ab6a59abcc979ca12681e58490c89cb8a85b485` |
| Industry participation edges | 4,816,559 | 430,061,239 | `363027b2c3fff40331b304c9dd9b1d7bd81691bc9f9915aaf1b8f4acd0a869b7` |
| Covered-position assertions | 748,589 | 58,789,826 | `81841c810269bf967cb3edc10664dbbad5aa17261089eaa67e4f288c2fcda625` |

All 6,682,108 rows independently passed schema and semantic validation. Of
25,340 lobbyists, 9,484 have covered-position text and 6,527 have a
government-term lexical hit. Those hits are text-classification evidence only,
not verified government employment. Filing-participation edges likewise are not
personal contact, employment, influence, or a Hill-to-industry transition.
Canonical merges and cross-source identity assertions are zero; analysis and
publication are false and `STAFF_NET=off`.

## 11. Restricted LDA identity candidates

Receipt SHA-256
`b8be6326f17fa2cb367f1e2f75393935d5b6324c4986c35d2379d9e50b4e1f4a`
binds 6,978 review-required rows: 6,313 LittleSis, 446 Politico, and 219
restricted legacy candidates. Unique LDA lobbyists by target source are
4,451/412/214; the artifact spans 4,741 unique LDA lobbyists, 5,526 unique
targets, and 3,910 normalized keys. It reports 1,953 government-term lexical-hit
rows, 4,459 collision rows, and 3,345 rows with cross-source multiplicity.

The candidate file is 653,038 bytes with SHA-256
`e2007da31695931954d309d8c25f577fa9a072ae8fc1b88728c4d0d92d2ae41f`.
Its method is `NORMALIZED_NAME_EQUALITY_REVIEW_CANDIDATES_ONLY`, version
`lda-identity-normalized-name-candidates-v2`, with normalizer
`politico-normalize-name-v1`. Every row preserves paired raw-name evidence and
upstream receipt bindings. Confidence is null, zero confidence values are
emitted, review is required, and canonical merges are zero. Candidate rows and
their receipt are restricted, machine-local, and refused by public-generation
load/publish paths.

## 12. Separate corpus contracts

### Politico

The restricted normalized corpus and review labels remain outside the P2 and
LDA source-native generations. Politico contributes 446 rows to the restricted
candidate artifact, but human gold is zero and precision is null. No identity
join is permitted.

### Historical members

Voteview and commit-pinned congress-legislators files provide broad/reference
coverage. A normalized term-valid member/committee plane must preserve blank
Bioguide outcomes and may not back-project current committee membership.

### House/Senate payroll

Future collectors must freeze complete report inventories, conserve physical
rows/parts, preserve revisions and locators, annotate parser gold, and treat
payment as observation rather than continuous employment.

## 13. Readiness ruling

The two-source P2 generation and separate LDA generation are restricted
source-native ready and suitable for ledger implementation. The candidate
artifact is suitable only for review and evaluation. Together they are not a
canonical truth set, verified Hill-to-industry transition layer, graph, or
public artifact. Legacy authority ratification, LittleSis publication review,
human entity resolution, covered-position semantic validation, historic
normalization, and payroll breadth remain open. `STAFF_NET=off`; canonical,
graph, analysis, publication, and consumer enablement remain false.
