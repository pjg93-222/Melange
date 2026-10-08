# Fable A1R2 — remediation review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`  
Stage: `A1R2`  
Reviewer: Fable through the read-only Claude lane  
Date: 2026-08-30  
Ruling: **PASS**  
Preservation note: Codex normalized mojibake in the lane transcript to ordinary Unicode punctuation; findings and numbers are otherwise unchanged.

## Ruling

A2 may proceed under the conditional contract. All four required A1R fixes are present in code, each has a planted failure for the exact attack, and no previously passing invariant regressed.

## Remediation matrix

| Finding | Code and test evidence | Verdict |
|---|---|---|
| F1 — self-anchored receipt | `_load_anchored_receipt` requires an external 64-hex anchor, hashes the restricted receipt, then validates schema and semantics. Both append and verify call it before trusting the framework. Receipt mutation makes both APIs fail. | PASS |
| F2 — allocation trusted before hashing | `append_label` checks `allocation_manifest_sha256` before reading assignments. A forged assignment row fails append. | PASS |
| F3 — copy-to-synced attack | Build seals a resolved-path fingerprint in `root_binding.json`; the receipt hash-references it; append and verify recompute it. Copying the framework to another root makes both APIs fail. | PASS |
| F4 — missing schema maxima | The validator now implements `maxItems`, `maxLength`, and numeric `maximum`. A 3,000-character rationale and direct keyword tests fail correctly. | PASS |

The hardening chain is closed: forging the root binding or allocation requires changing the receipt, and the receipt is pinned to an external anchor.

## Regression check

The following remain intact:

- pilot pre-label and sample-hash gates;
- Politico `AUTHORIZED`, `restricted-local-only`, and `enabled:false` requirements;
- synced-output refusal at build time;
- strict-stratum and candidate uniqueness checks;
- packet machine-flag blinding at build and verification;
- duplicate-label and prior-review-visible refusals;
- permanent merge negative control;
- 200 candidates, 100/100 split, 400 assignments, zero labels, zero merges, and null precision in the committed v2 receipt;
- core deterministic replay, with root binding intentionally path-specific.

Fable accepted the v1 zero-label state from its prior review but could not re-inspect v1 because A1R2 was deliberately limited to v2. Only v2 is eligible for A2.

## Residual A2 obligations

1. The lane driver must obtain `expected_receipt_sha256` from the committed public receipt, never from the restricted root.
2. A1 verification remains a pre-label gate. A2 needs a new post-label receipt bound to the same anchor chain; A1 must not be loosened.
3. Holdout labels and results remain quarantined until one evaluation bound to the sealed split hash.
4. Downstream text may claim machine-flag blinding only. Partition is reviewer-visible and source identity can remain structurally inferable.
5. Every label remains `MODEL_ASSISTED`, never human gold.
6. Disagreement uses separate appended adjudication records; prior reviewer labels are not edited.
7. Aggregate outputs and hashes only may enter synced storage. `MATCH` plus `DISTINCT` define the precision denominator; `POSSIBLE` and `ABSTAIN` remain separately reported.
8. A2 runs on the original machine and path bound by v2.

Source enablement, canonical publication, and merges remain blocked.
