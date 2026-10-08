# Opus 5 adversarial review — v1 employment adjudication overlay

Date: 2026-09-01  
Reviewer model: canonical `claude-opus-5`  
Effort: `max`  
Verdict: **FAIL**

This file records the first read-only Opus 5 review returned through the Claude lane.
It applies only to the superseded v1 primary/twin generation. The review ran while v2
repairs were being developed, so its findings are evidence against v1 and must not be
treated as an attestation over v2.

## Blocking findings returned by Opus 5

1. `audit_history_completeness` could return `COMPLETE` without requiring an active
   canonical episode, accepted person identity, or accepted container identity.
2. The v1 generated artifacts predated and did not validate against the newly introduced
   v2 schemas and verifier, so the v1 twin receipt did not bind the implementation under
   review.
3. Seven covered-position provisional intervals ended at `2027-01-01` despite a
   `2026-09-01` source cutoff.

Opus additionally confirmed that v1 provisional records could not enter the primary
temporal builder, and that source-page bindings and filing associations remained distinct
from employment facts. It nevertheless correctly withheld the Fable gate because the
three blockers above were open.

## Disposition

All three blockers were accepted. The coordinator then:

- added fail-closed canonical-schema, active-status, identity, container, blocker, and
  eligibility checks to `audit_history_completeness`, with negative tests;
- regenerated a fresh v2 primary/twin pair under five registered strict schemas;
- quarantined all intervals beyond the cutoff;
- separated payroll observations from asserted employment episodes;
- removed disjoint Senate interval envelopes;
- content-bound decision and episode identifiers;
- collapsed exact duplicate facts while retaining every supporting decision;
- replaced the compressed-byte token scan with decompressed payload scanning; and
- expanded the verifier to independently recompute IDs, digests, interval quartets,
  decision/episode reciprocity, exact queue membership, summaries, schemas, and sample
  strata.

The v1 verdict remains **FAIL**. A separate fresh Opus 5 review is required for v2.
