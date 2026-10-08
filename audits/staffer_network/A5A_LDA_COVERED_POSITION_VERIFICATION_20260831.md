# A5a LDA covered-position verification — 2026-08-31

Status: **PASS**

The primary ledger was not modified. A clean generation was written to
`lda_covered_position_employment_ledger_20260831_verify`, and every one of the
four generated artifacts is byte-identical to the primary generation.

## Conservation results

- Source people: 25,340 rows, 25,340 unique source-person IDs.
- Materialized people: 25,340 rows, 25,340 unique source-person IDs, exact ID
  set equality with the source-native people universe.
- Output people: 25,340 rows, 25,340 unique source-person IDs, exact ID,
  numeric-ID, display-name, and source-order conservation.
- Source covered-position occurrences: 748,589 rows and 748,589 unique
  assertion IDs.
- Output covered-position occurrences: 748,589 rows and 748,589 unique
  assertion IDs; zero projected-field mismatches.
- Official filing URL bindings: 748,589 exact template matches and zero
  mismatches.
- Source claims: 41,680 rows and 41,680 unique claim IDs.
- Exact-span mentions: 41,680 rows and 41,680 unique claim IDs.
- Episode candidates: 41,680 rows and 41,680 unique claim IDs; zero claim or
  mention projection mismatches.
- Canonical-promotion or complete-history violations: 0.
- Credential-token matches: 0 across the four primary and four twin
  artifacts, scanning decompressed gzip contents.

## Exact source bindings

| Role | Bytes | SHA-256 |
|---|---:|---|
| source-native lobbyists | 1,928,569 | `80ac82346c435bb8f1231d9f3425d759ca9a8ae063db879ec104244f9fcd282e` |
| source-native covered-position occurrences | 58,789,826 | `81841c810269bf967cb3edc10664dbbad5aa17261089eaa67e4f288c2fcda625` |
| materialized person universe | 1,652,798 | `49fbdc1e03f8cac931b56b265222a594583774857b650b0b987b471bf01e3908` |
| materialized source fragments | 2,769,809 | `39fb98a5ef2fe68b990356e84ce38f5d61b900f2f691d66156c84c48e84e9311` |
| exact-span candidate mentions | 3,910,651 | `d131b963027d73a760a542b4f82143165d816ab18aa36eaf57f74a21680cbd59` |

Both the primary and twin receipts bind all five paths, byte counts, and
hashes exactly.

## Primary/twin artifacts

| Artifact | Bytes | Primary SHA-256 | Twin SHA-256 | Byte equal |
|---|---:|---|---|---|
| occurrences | 64,865,227 | `5d389c0352dd3df03b4b4405daed95cd46a01ffbb78bd19d372fa1f2eaa42def` | `5d389c0352dd3df03b4b4405daed95cd46a01ffbb78bd19d372fa1f2eaa42def` | yes |
| episode candidates | 5,418,205 | `86504e9d8b049bf9920da0d09a24e0af3a96111b10c7e795ca4bd4a5760b6e16` | `86504e9d8b049bf9920da0d09a24e0af3a96111b10c7e795ca4bd4a5760b6e16` | yes |
| people coverage | 830,456 | `7449ee5233bb384c3dcafefc90b172f999335423776bad891b1216f5e47ae436` | `7449ee5233bb384c3dcafefc90b172f999335423776bad891b1216f5e47ae436` | yes |
| ledger receipt | 3,966 | `3e7604ee0eef191fd87ecf1e02f7abe9e02ac3f8a64c490b0b47ab14c88f57e3` | `3e7604ee0eef191fd87ecf1e02f7abe9e02ac3f8a64c490b0b47ab14c88f57e3` | yes |

Independent verification receipt SHA-256:
`016e1a944c5bbd6613ff1a57cf3cc16dba74ce1a3476410476d2d65224b64da2`.

## Raw-schema audit

The default `lda_raw_covered_position_schema_audit_20260831` directory was
empty. The audit was run without modifying it, into
`lda_raw_covered_position_schema_audit_20260831_verify`.

- 12,484 of 12,484 raw page files parsed; zero errors.
- 1,416,168,383 source bytes inventoried.
- 311,558 filings, 621,878 activities, and 1,785,452 lobbyist activity items.
- The employment source shape is exactly
  `filing.lobbying_activities[].lobbyists[].covered_position`.
- The lobbyist identity subobject has no separate structured current,
  employer/office, employment-start, employment-end, or title field.
- Inventory binding SHA-256:
  `de60cfe03be26a515c06e6ba78f6f82d0c3613e1a497bd97c0dbd99a531757e2`.
- Schema-audit receipt SHA-256:
  `1c9a75cf0d439d6e93243127f92fa87d2032e987821077ca42672d9db8a36ac0`.

## LegiList ID diagnosis

The supplied LegiList path contains lobbyist numeric ID `147664`. The exact
local Senate LDA source row is `lda:lobbyist:147664`, source numeric ID
`147664`, display name `GORDON HOLZBERG`. A single page request returned the
title `Gordon Holzberg — Federal Lobbyist | LegiList` and contained both the
numeric ID and name. No bulk crawl or link-following was performed; the site's
published 10-second crawl delay was respected by limiting verification to one
request. This establishes numeric-key equivalence, not an independent
name-only identity adjudication.

## Tests and artifacts

- Focused unit tests: 5 passed.
- Independent verifier: `verify_lda_covered_position_employment_ledger.py`.
- Focused tests: `test_verify_lda_covered_position_employment_ledger.py`.
- Independent receipt:
  `lda_covered_position_employment_ledger_verification_20260831/verification_receipt.json`.
- LegiList check:
  `lda_covered_position_employment_ledger_verification_20260831/legilist_id_equivalence_check.json`.

No blocked checks remain.
