# Claude Opus 5 handoff — employment adjudication overlay v3

Date: 2026-09-01  
Repository: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`  
Meta LOOP run: `run-20260901T1341531206612Z-06b5ca2f8a`  
Required reviewer: canonical Claude Opus 5 at effort `max`; no Sonnet fallback.

## Objective

Perform a fresh, read-only, adversarial review of the pinned v3 implementation, schemas,
primary/twin generations, and independent verification receipt. Return `PASS` only if this
is a deterministic, provenance-bound, fail-closed quarantine/adjudication overlay.

This review does **not** close the human gold, container-adjudication, or Senate
observation-audit gates. It must not call the provisional facts complete or canonical
employment histories. Do not modify the repository. Return complete Markdown; the
coordinator will save it.

## Pinned implementation hashes

```text
7cfadd8680408639a0b79889ae5542508436942cd70c8e31f3d9a7c339f04135  audits/staffer_network/adjudicate_bulk_employment_candidates.py
3947320f8673c16bbb3a67a1b3806d9768e738e06aea72727c7c8d08fc0f2317  audits/staffer_network/verify_bulk_employment_adjudication.py
a6a26fb86e8f3aa040081502c2fb1c61e55b50ecd3b6bff4f86ccf8537b56910  audits/staffer_network/test_adjudicate_bulk_employment_candidates.py
0099dfe496d4fb8a8ab209d043a9a83f6abd1cfe998e96ad38f92990c60288c9  fec/staffer_network/employment_history.py
d1f6b90dc4be6a6498eba9e610b9d13c9230b7af0afed5fdd9ccfcf0c7316398  fec/tests/staffer_network/test_staffer_employment_history.py
```

Pinned v2 schema hashes:

```text
1a901fecba1a90514eb46ca3c80b789bcc390a8521f49d6f00d5f262d6e39d94  employment_candidate_adjudication_v2.schema.json
74a16164447170b0beba9443ca1edd3a83ee11432269845110a0d1170728b367  provisional_employment_episode_v2.schema.json
f30ada0e0a63ada06ab0f4a0fcaafd6c50adbd5f7d459dc7c3d2bba2431547b0  employment_adjudication_gold_sample_v2.schema.json
747f057a3a6e0db020c7e18d8ba4cbb7d94f62a4d7df763e61cf3ff14eba2434  employment_adjudication_receipt_v2.schema.json
b8feea1a8df6b48a4dfe8ea419408783c4e44c5d31204a2fa3a24e7b19053f46  employment_adjudication_verification_receipt_v2.schema.json
```

If any pinned implementation or schema hash differs, return `FAIL` with
`REVIEW_INPUT_DRIFT` and stop.

## Fresh generation and verification

```text
audits/staffer_network/employment_adjudication_generation_20260901_v3_primary
audits/staffer_network/employment_adjudication_generation_20260901_v3_twin
audits/staffer_network/employment_adjudication_generation_20260901_v3_verification
```

Pinned receipts:

```text
02ff23202da31be3ae49db04dc84735316dd4f8c42c632f98380effa11a4a263  primary/twin employment_adjudication_receipt.json
4d587dd14b5b9f2b0a29540933009f6f5f880fc973997d30533e7e716e8777bb  verification employment_adjudication_verification_receipt.json
```

The primary and twin receipts and all five payloads are byte-identical. The independent
verifier returns `PASS` with no decision, episode, summary, or sample failures, and zero
token-scan matches. Full tests return `240 passed, 73 subtests passed`.

## Measured v3 outcome

```text
sealed people                         25,340
decision rows                        235,454
provisional support decisions          5,667
unique provisional facts               4,996
exact duplicate supports collapsed       671
people with provisional facts           1,186
canonical employment promotions             0
complete lifetime assertions                 0
primary temporal eligible episodes           0
cross-source identity merges                  0
```

| Lane | Support decisions | Unique facts |
|---|---:|---:|
| House payroll observation | 3,588 | 3,552 |
| LDA covered-position assertion | 1,878 | 1,243 |
| Senate payroll observation | 125 | 125 |
| Structured public-profile assertion | 76 | 76 |

The semantic partition is 3,677 `OBSERVATION_ONLY` and 1,319 `ASSERTED_EPISODE`.
Neither class is temporal-weight eligible. Compared with v2, normalized identifiers
consolidate the remaining four case-only and 34 parenthesized `OTHER COMPENSATION`
variants without losing support decisions; raw variants remain preserved in arrays.

## Required adversarial checks

1. Recompute every pinned hash before substantive review.
2. Confirm the new v2 schema IDs are separate immutable contracts, strict, producer- and
   verifier-validated, and hash-bound by both receipts. Confirm old v1 schemas were not
   silently repurposed.
3. Confirm the generation receipt binds the exact generator bytes and the verification
   receipt binds the exact verifier bytes plus the verified generator hash.
4. Confirm decision IDs bind immutable decision payloads; episode IDs bind normalized
   fact identity; raw employer/title variants remain preserved; support/decision IDs are
   unioned without adding graph weight.
5. Recompute the prior 38 normalized duplicate groups and confirm they are gone without
   support loss.
6. Confirm all payroll output is `OBSERVATION_ONLY`; every Senate provisional fact has one
   clean half-open observed range; no `COMPLEX_QUALIFIER_REVIEW_REQUIRED` range is emitted;
   no disjoint min/max envelope is treated as continuous employment.
7. Confirm every uncertainty quartet is coherent and
   `valid_end_latest <= source_as_of + 1 day`; future uncertainty is quarantined.
8. Confirm verifier recomputation covers decision/episode IDs, exact sealed-queue person
   membership, exact accepted-decision/episode reciprocity, support digests, input and
   schema hashes, source transforms, summaries, sample strata, content-bound sample
   evidence, cutoff bounds, and decompressed token scanning.
9. Confirm identity calibration is exactly 60/30/10 House/Senate/structured for both
   proposed-accept and review strata, with corroborating LDA claim, similarity thresholds,
   and cardinality reproduced from pinned sources.
10. Confirm LegiStorm is not an official-source host and a single commercial-domain page
    cannot satisfy the structured official-source branch.
11. Confirm `audit_history_completeness` schema-validates a canonical v1 episode and fails
    closed for provisional, rejected, absent, or review-required identity/container/status
    values, forged attestations, aliased dates, and raw-month-only claims.
12. Attempt to route any provisional row into canonical facts, complete lifetime history,
    or primary temporal weights. Any successful route is a blocking failure.

## Verdict scope

A `PASS` means only that v3 is a sound deterministic quarantine/adjudication overlay and
that the Fable code/artifact review gate may close for this exact version. It must leave
these substantive gates open:

```text
COVERED_POSITION_PARSER_PRECISION_GOLD_100_REQUIRED
IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED
CONTAINER_ADJUDICATION_REQUIRED
SENATE_TEMPORAL_OBSERVATION_AUDIT_REQUIRED
```

Return the exact canonical model name, effort, hashes inspected, `PASS` or `FAIL`, blocking
findings, non-blocking limitations, commands/evidence inspected, and an explicit statement
that no provisional episode was promoted.
