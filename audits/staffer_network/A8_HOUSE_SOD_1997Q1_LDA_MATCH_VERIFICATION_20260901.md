# A8 House SOD 1997Q1–LDA Candidate Match Verification

Status: `PASS` (independent reconstruction; zero canonical promotions)

## Outcome

A8 conservatively matched the independently verified 4,939-row Google Books
OCR extraction for House Statement of Disbursements 1997Q1 Part 2 against the
exact final A5b universe of 25,340 LDA people. The primary and twin candidate
ledgers are byte-identical. The independent verifier imports no builder code
and reproduced the complete ordered source/person candidate sequence.

The output contains 453 review-only name-match candidate rows for 388 distinct
LDA people, supported by 375 distinct OCR personnel rows. No name match is an
identity adjudication, canonical employment fact, or assertion of continuous
tenure.

## Exact row and person accounting

| Measure | Count |
|---|---:|
| OCR personnel input rows | 4,939 |
| Unusable House payee-name shapes | 240 |
| Parseable OCR rows without a compatible LDA name | 4,324 |
| Distinct matched OCR personnel rows | 375 |
| Emitted source/person match candidates | 453 |
| Distinct matched normalized House-name keys | 324 |
| Distinct matched LDA people | 388 |
| Unmatched A5b people | 24,952 |

The source-row conservation is exact: `240 + 4,324 + 375 = 4,939`.

## Candidate classes and ambiguity

The matcher preserves the normalization and compatibility grammar in
`match_lda_house_payroll.py`: NFKD/ASCII uppercase alphanumeric tokens, trailing
suffix removal, House surname-first parsing, exact first/last equality, and
middle-token compatibility only when the first stated middle initials agree.

| Candidate class | Match rows |
|---|---:|
| `EXACT_NORMALIZED_FULL_NAME` | 128 |
| `EXACT_FIRST_LAST_MIDDLE_INITIAL_COMPATIBLE` | 17 |
| `EXACT_FIRST_LAST_MIDDLE_UNSPECIFIED` | 308 |

| Ambiguity measure | Single candidate | Multiple compatible LDA candidates |
|---|---:|---:|
| OCR source rows | 310 | 65 |
| Emitted match candidates | 310 | 143 |
| Distinct LDA people | 264 | 124 |
| Distinct normalized House-name keys | 265 | 59 |

Every compatible same-name LDA person is retained. The 59 ambiguous normalized
keys remain explicitly review-required; the 265 single-candidate keys also do
not constitute identity proof. No exact name is treated as a canonical identity.

## Incremental dated/bounded coverage by final A5b bucket

All matched source rows contain start and end observations wholly within
1997Q1. Therefore each matched person gains a dated and bounded *candidate* for
this report period only. A8 does not rewrite A5b or change its priority bucket.

| Final A5b bucket | People gaining a dated candidate | People gaining a bounded candidate | A8 match rows |
|---|---:|---:|---:|
| `P0_NO_EMPLOYMENT_CANDIDATE` | 77 | 77 | 84 |
| `P1_DATED_FORMER_POSITION_MISSING` | 89 | 89 | 102 |
| `P2_BOUNDED_INTERVAL_MISSING` | 43 | 43 | 52 |
| `P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION` | 179 | 179 | 215 |
| **Total** | **388** | **388** | **453** |

“Gain” means the person receives an additional A8 review candidate relative to
the frozen A5b ledger. It does not mean an adjudicated identity, a canonical
episode, or proof of employment beyond the observed 1997Q1 row.

## Frozen input bindings

| Input | Bytes | SHA-256 |
|---|---:|---|
| Google Books source PDF response | 39,235,422 | `21bb07508249c8ec28dd731a64bdc343cdc6347c3355b0523fc6e011104215d4` |
| 4,939-row personnel ledger | 411,038 | `99ce0f633f56d12c4fbce615371d3604a22353411d68c7d25de226e4fd1d89b6` |
| Personnel extraction receipt | 2,076 | `3f748b20c8760e56c98fa1c677bacdd27e98567fd5a9994ae090f2b3ee091530` |
| Source independent verification/audit | 34,909 | `3407342f66586390e99dbd830f7c7f1fc45f949526ab442c8c4d10feb3c44d38` |
| Final A5b 25,340-person ledger | 2,530,929 | `59b24e1bc6c7af1b68b99203d831c43e2df97fac04d676161e45a9042b4e8ea2` |
| Final A5b receipt | 2,892 | `ea8748acc208fc74dc33b5f55b777eb03be082e79351c94af94c44633bd7adf1` |
| Final A5b independent verifier | 1,461 | `62165b4b329ef56ef260dca5997994d2dff09b6af1d270f9055048b431f3a256` |
| A4 normalization reference implementation | 9,440 | `9fb65e37900e3a9dc4880f09ae8ca4f28ed09df49b285fc114f9142958ad9a7d` |

The source audit has `audit_status: PASS` for its validation and confirms the
4,939-row extraction twins are byte-identical. Its broader pre-web acquisition
state remains incomplete because other Google Books volumes were blocked or
undiscovered; A8 makes no claim beyond the acquired 1997Q1 Part 2 volume.

## A8 output bindings

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| A8 manifest | 3,186 | `739a662731392e1e9cf36e2340882be90b5f97b9dae6a72c5a63e57efe475659` |
| Primary candidate ledger | 65,304 | `fd7adbdd68cd9c23fb511ae737c1892e4d50212207f434d4e0a5f96fd8918607` |
| Twin candidate ledger | 65,304 | `fd7adbdd68cd9c23fb511ae737c1892e4d50212207f434d4e0a5f96fd8918607` |
| Primary match receipt | 5,727 | `8c3f5abba8c6f81b4afea2a1646add11a7c98fa5bb5964f9a6dd402a3cda93e8` |
| Twin match receipt | 5,727 | `8c3f5abba8c6f81b4afea2a1646add11a7c98fa5bb5964f9a6dd402a3cda93e8` |
| Independent verification receipt | 3,289 | `e05c9e31b32229b116ec91c043950ec84321ff5e3d88a9cc77cdb6038bd5e87d` |

The verifier reported `PASS`, zero row failures, zero input-binding failures,
and 28 passing assertions. Five focused A8 tests and three source-extraction
regression tests reported `8 passed` in total.

## Evidence limits

- The underlying House document is a Google Books public scan, not an official
  House-hosted PDF. Names, offices, titles, dates, and amounts may contain OCR
  errors.
- House payees are parsed surname-first under the pre-existing conservative
  grammar. Compound surnames, malformed OCR, ditto marks, vendors, and other
  edge cases are not repaired into stronger matches.
- Dates are retained only as bounded observations in the 1997Q1 report. They do
  not establish continuity, complete tenure, or complete employment history.
- `canonical_identity_promotions = 0`, `canonical_employment_promotions = 0`,
  and `complete_lifetime_employment_assertions = 0`.
- A8 is additive. No A4, A5b, source extraction, or prior integration artifact
  was overwritten.
