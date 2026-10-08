# A9 A7/A8 immutable priority sidecar diagnostic — 2026-09-01

Run: `run-20260831T1850525496629Z-8993807782`  
Stage: `A9-a7-a8-priority-sidecar-integration`  
Status: `PASS`

## Result

A9 produced a deterministic, immutable 25,340-person scheduling sidecar over
the sealed final A5b baseline. It consumes only A7 FEC employer point
observations and A8 House 1997Q1 name-match candidates. It does not consume the
A7 LD-203 affiliation ledger and does not treat registrant affiliation as
employment.

Primary and twin ledgers are byte-identical. The independent verifier rebuilt
every person-level evidence summary and scheduling decision from the sealed
inputs, conserved all 25,340 exact IDs, and returned `PASS` with 33/33
assertions, zero row failures, zero input-binding failures, and zero source
semantic failures.

## Conservative scheduling semantics

### A7 FEC observations

The 979 A7 rows cover 37 people and report an employer/occupation at a dated
FEC transaction. They are point observations only. They do not prove that a
position is former, do not establish start or end bounds, and do not establish
continuous tenure. Accordingly:

- no FEC observation clears `FORMER_POSITION_CANDIDATE_MISSING`;
- no FEC observation clears `DATED_FORMER_POSITION_CANDIDATE_MISSING`;
- no FEC observation clears `BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING`;
- all 37 FEC people retain their sealed A5b priority bucket.

The FEC baseline distribution is P0 14, P1 5, P2 6, and P3 12. All have zero
bucket movement. The sidecar explicitly encodes `employment_interval_asserted:
false`, `former_position_asserted: false`, and an empty `gap_clearances` list.

### A8 House 1997Q1 candidates

The 453 A8 rows cover 388 people. Each is a dated and bounded candidate within
the 1997Q1 report and represents a candidate former House position for
scheduling. Because the link remains a review-only name match, it cannot be
canonical and must still undergo identity and chronology adjudication.

Thus an A8 candidate moves a baseline P0, P1, or P2 person to revised P3; a
baseline P3 person stays P3. This changes 209 buckets and leaves 179 A8 people
already in P3.

## Exact evidence overlaps

| Combination | People |
|---|---:|
| A7 FEC only | 37 |
| A8 House 1997Q1 only | 388 |
| Both A7 FEC and A8 | 0 |
| Neither | 24,915 |
| **Exact scope** | **25,340** |

The exact A7-FEC/A8 person overlap is zero.

## Revised scheduling buckets

| Bucket | Sealed A5b | A9 sidecar | Delta |
|---|---:|---:|---:|
| `P0_NO_EMPLOYMENT_CANDIDATE` | 11,720 | 11,643 | -77 |
| `P1_DATED_FORMER_POSITION_MISSING` | 4,932 | 4,843 | -89 |
| `P2_BOUNDED_INTERVAL_MISSING` | 1,784 | 1,741 | -43 |
| `P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION` | 6,904 | 7,113 | +209 |
| **Total** | **25,340** | **25,340** | **0** |

| Transition | People |
|---|---:|
| P0 → P0 | 11,643 |
| P0 → P3 | 77 |
| P1 → P1 | 4,843 |
| P1 → P3 | 89 |
| P2 → P2 | 1,741 |
| P2 → P3 | 43 |
| P3 → P3 | 6,904 |

A9 supplies a revised queue ordinal but retains the complete A5b priority
snapshot on every row. Its deterministic order is revised bucket, baseline
bucket, baseline queue ordinal, sealed queue ordinal, and exact LDA ID.

## Frozen input bindings

| Input | Bytes | SHA-256 |
|---|---:|---|
| Final A5b priority ledger | 2,530,929 | `59b24e1bc6c7af1b68b99203d831c43e2df97fac04d676161e45a9042b4e8ea2` |
| Final A5b receipt | 2,892 | `ea8748acc208fc74dc33b5f55b777eb03be082e79351c94af94c44633bd7adf1` |
| Final A5b independent verification | 1,461 | `62165b4b329ef56ef260dca5997994d2dff09b6af1d270f9055048b431f3a256` |
| A7 FEC employer-observation ledger | 244,043 | `6f67f0d8c731277a761ad0d18ad1610e57d21d371dfc38f5a84982ed9063db35` |
| A7 build receipt | 3,252 | `f005be8f5999dcf006dbdd7093cec12356d9cb35376a6dbc228ef4af9bcfaa1c` |
| A7 independent verification | 480 | `7c8402784db9861c928bd4045ac7792022d96a92d18bf7e9d91bf38d3590d969` |
| A8 House match ledger | 65,304 | `fd7adbdd68cd9c23fb511ae737c1892e4d50212207f434d4e0a5f96fd8918607` |
| A8 match receipt | 5,727 | `8c3f5abba8c6f81b4afea2a1646add11a7c98fa5bb5964f9a6dd402a3cda93e8` |
| A8 independent verification | 3,289 | `e05c9e31b32229b116ec91c043950ec84321ff5e3d88a9cc77cdb6038bd5e87d` |

## A9 artifacts and hashes

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Manifest | 3,607 | `ac81be58945fadbc5288117d80bc93da111d68ab66dbd207ffa0a244e133cc62` |
| Primary sidecar ledger | 1,376,912 | `f7e3350f122b5d5c5347baabf4ec1e268c00e300df282ae61db78ab0b8a68423` |
| Twin sidecar ledger | 1,376,912 | `f7e3350f122b5d5c5347baabf4ec1e268c00e300df282ae61db78ab0b8a68423` |
| Primary receipt | 5,432 | `ebb40e26c4eaf2766024b47a1b32cd51666c411c669d239e06ee517141d59f1f` |
| Twin receipt | 5,432 | `ebb40e26c4eaf2766024b47a1b32cd51666c411c669d239e06ee517141d59f1f` |
| Independent verification receipt | 3,908 | `0b1dca553a254c686bee197d172e0d35ce1a86eb27a3ddf2c2bf7c4960423429` |

## Integrity controls

- Exact A5b ID conservation: 25,340 input IDs = 25,340 unique sidecar IDs.
- A5b, A7, and A8 inputs remain hash-identical after generation.
- The A7 LD-203 candidate ledger is absent from the manifest input set and the
  sidecar payload contains zero `ld203` mentions.
- A7 FEC source semantics and all A8 report/date/name-match invariants were
  independently checked.
- Structured token-negative scan: 50,683 JSON/NDJSON documents, zero matches.
- Eight focused A9 tests plus six A7 and five A8 regression tests: `19 passed`.
- `canonical_identity_promotions = 0`, `canonical_employment_promotions = 0`,
  and `complete_lifetime_employment_assertions = 0`.
- A5b, A7, and A8 were not mutated. A9 writes only new sidecar artifacts.
