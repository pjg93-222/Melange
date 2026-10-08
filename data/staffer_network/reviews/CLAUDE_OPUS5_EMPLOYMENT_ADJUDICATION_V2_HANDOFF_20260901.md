# Claude Opus 5 handoff — employment adjudication overlay v2

Date: 2026-09-01  
Repository: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`  
Meta LOOP run: `run-20260901T1341531206612Z-06b5ca2f8a`  
Required reviewer: canonical Claude Opus 5 at effort `max`; no Sonnet fallback.

## Objective

Perform a fresh read-only adversarial review of the pinned v2 implementation and its
fresh primary/twin generations. Return `PASS` only if this is a deterministic,
fail-closed quarantine/adjudication overlay. This review does **not** close the human gold,
container-adjudication, or Senate observation-audit gates, and it must not call the 5,030
provisional facts canonical employment histories.

Do not modify the repository. Return complete Markdown; the coordinator will save it.

## Pinned implementation hashes

```text
692865821e0fdc3766c1f64237e5a9e37f00443541a6ac6ba47773a54ba445a5  audits/staffer_network/adjudicate_bulk_employment_candidates.py
e7150fc3e96142b160c0c850f71bca7d95a7aeccbe2ab2ffa00a2e3f1d48d1a2  audits/staffer_network/verify_bulk_employment_adjudication.py
01de7516022acb20853d026c91991779da286beb459156cf36ab62ebd34fb46a  audits/staffer_network/test_adjudicate_bulk_employment_candidates.py
8bf2c2e391c10d5af27cf36958da05b9aa5ab16486b01f08781e1cf949685f11  fec/staffer_network/employment_history.py
eb17e3b1d7b5dc5ba36554ad8c4b55cf073f3af370b5f070c4e4da32ca3e2e0d  fec/tests/staffer_network/test_staffer_employment_history.py
```

If any hash differs, return `FAIL` with `REVIEW_INPUT_DRIFT` and stop.

## Fresh generation and verification

```text
audits/staffer_network/employment_adjudication_generation_20260901_v2_primary
audits/staffer_network/employment_adjudication_generation_20260901_v2_twin
audits/staffer_network/employment_adjudication_generation_20260901_v2_verification
```

Pinned receipts:

```text
0f91bf9082d1c75b0f632745870e830b411df4b05bee29681b9feca7285f400f  v2 primary employment_adjudication_receipt.json
0b6d62765ea3f46ba90a910e85636454e7bc852e2648130eb4fd7819f96e94be  v2 verification employment_adjudication_verification_receipt.json
```

Primary and twin receipts and all five payloads are byte- and hash-identical. The fresh
independent verifier returns `PASS` with no decision, episode, summary, or sample failures.
The full suite returns `235 passed, 73 subtests passed`.

## v2 measured outcome

```text
sealed people                         25,340
decision rows                        235,454
provisional support decisions          5,667
unique provisional facts               5,030
exact duplicate rows collapsed           637
canonical employment promotions             0
complete lifetime assertions                 0
primary temporal eligible episodes           0
cross-source identity merges                  0
```

Provisional supports by lane, followed by unique facts after same-lane exact-fact
consolidation:

| Lane | Support decisions | Unique facts |
|---|---:|---:|
| House payroll observation | 3,588 | 3,582 |
| LDA covered-position assertion | 1,878 | 1,247 |
| Senate payroll observation | 125 | 125 |
| Structured public-profile assertion | 76 | 76 |

The semantic partition of unique provisional facts is 3,707 `OBSERVATION_ONLY` and 1,323
`ASSERTED_EPISODE`. Neither class is temporal-weight eligible.

## Required checks

1. Recompute the pinned file hashes before reading substantive content.
2. Confirm the five generated schema IDs are registered, strict, bound by hash in the
   receipt, and validated by both producer and verifier.
3. Confirm decision IDs bind the immutable decision payload, episode IDs bind the exact
   provisional fact, and duplicate consolidation unions all support/decision IDs without
   adding weight.
4. Confirm all payroll outputs are `OBSERVATION_ONLY`; every Senate provisional fact has
   exactly one clean half-open observed range; no `COMPLEX_QUALIFIER_REVIEW_REQUIRED`
   range is emitted; Mark Ritacco's former disjoint multi-year envelope is absent.
5. Confirm every uncertainty quartet is coherent and `valid_end_latest <= source_as_of + 1
   day`; the seven former `2027-01-01` rows must be absent.
6. Confirm the verifier scans decompressed payload text and recomputes, rather than trusts,
   decision/episode IDs, support digests, exact queue membership, summaries, sample strata,
   schema hashes, cutoff bounds, and decision/episode reciprocity.
7. Confirm the identity calibration sample is exactly lane/status stratified 60/30/10 for
   House/Senate/structured in both proposed-accept and review strata, and accepted payroll
   samples expose the LDA corroborating claim, similarity scores, thresholds, and uniqueness
   cardinality.
8. Confirm LegiStorm is not in `OFFICIAL_HOSTS`; a single LegiStorm domain cannot satisfy
   the structured official-source branch.
9. Confirm `audit_history_completeness` now fails closed for provisional, rejected, absent,
   or review-required identity/container/status fields, even with a forged exhaustive PASS
   attestation and aliased dates.
10. Attempt to route any provisional row into canonical facts, complete lifetime history,
    or primary temporal weights. Any successful route is a blocking failure.

## Verdict scope

A `PASS` means only that v2 is a sound deterministic quarantine/adjudication overlay and
that the Fable code/artifact review gate may close for this version. It must leave these
substantive gates open:

```text
COVERED_POSITION_PARSER_PRECISION_GOLD_100_REQUIRED
IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED
CONTAINER_ADJUDICATION_REQUIRED
SENATE_TEMPORAL_OBSERVATION_AUDIT_REQUIRED
```

Return the exact canonical model name, effort, pinned hashes inspected, `PASS` or `FAIL`,
blocking findings, non-blocking limitations, commands/evidence inspected, and an explicit
statement that no provisional episode was promoted.
