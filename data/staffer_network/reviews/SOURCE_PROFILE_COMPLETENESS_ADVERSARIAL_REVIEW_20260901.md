# Source-profile completeness independent review — 2026-09-01

## Verdict

**PASS for the narrowly defined practical metric.** A read-only recomputation from the
three structured profile ledgers exactly reproduced the V4 receipt:

- 912 exact LDA people have at least one structured profile employment assertion;
- 890 are `SOURCE_PROFILE_ROLE_EMPLOYER_COMPLETE`;
- 22 are `SOURCE_PROFILE_ROLE_EMPLOYER_INCOMPLETE`.

This verdict establishes employer/role field completeness on captured structured
profile jobs. It does not establish lifetime exhaustiveness, identity promotion,
canonical employment promotion, or chronology validity.

## Independent source recomputation

| Source | People with employment | Assertions | Complete people | Incomplete people |
|---|---:|---:|---:|---:|
| Working-history corpus | 835 | 2,470 | 814 | 21 |
| Rapid structured profiles | 72 | 478 | 71 | 1 |
| Authenticated profiles | 10 | 74 | 10 | 0 |

The raw source qualifying counts overlap. Five people appear in both rapid and
authenticated ledgers; exact `lda_source_person_id` deduplication produces 890 unique
complete people. Rapid `employment` and `employment_episodes` aliases are coalesced,
never concatenated.

## Control cases

- Stephanie Belk (`lda:lobbyist:147663`) passes with five authenticated employment
  assertions and zero missing employers or titles.
- Gordon Holzberg (`lda:lobbyist:147664`) has no structured profile employment in these
  three selected ledgers, so he is neither a source-profile pass nor a source-profile
  field failure. His surviving LDA and LegiStorm evidence is separately recorded as a
  capture-conservation defect.

## Determinism

The primary and twin 25,340-row payloads are byte-identical with SHA-256
`a9a3f2a4a8e33196b3ac9a58cf7181ab86eff6e19669e27246bb204eb5d06f8c`.
The seven focused classification tests passed, the selected-pointer receipt hash was
verified, and the token-negative artifact scan returned zero matches.
