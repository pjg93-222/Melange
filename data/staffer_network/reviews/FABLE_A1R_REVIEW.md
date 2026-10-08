# Fable A1R — independent review of the A1 adjudication framework

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`  
Stage: `A1R`  
Reviewer: Fable through the read-only Claude lane  
Date: 2026-08-30  
Ruling: **REVISE**  
Preservation note: Codex normalized mojibake in the lane transcript to ordinary Unicode punctuation; findings and numbers are otherwise unchanged.

## Ruling

The framework is real, deterministic, blinded, and sealed as claimed, and A2 may be prepared. Three tamper/relocation gaps mean that “restricted-local labels” and “sealed controls are trustworthy at label time” currently depend on the honesty of whoever holds the restricted directory. These small, testable defects must be fixed before label 1.

## Artifact acknowledgement

Fable read the adjudication module, receipt semantics, privacy/source/schema validators, receipt schema, adjudication tests, schema tests, test registration, committed receipt, and F0 review. It inventoried all 10 restricted files, read the restricted receipts and policies, and performed key-shape/negative-control greps on all four packets without reproducing record values.

The read-only lane could not execute hashes. Codex independently verified the expected file hashes, exact public/restricted receipt equality, the 47-test focused pass, and byte-identical replay.

## Acceptance matrix

| Invariant | Verdict | Evidence |
|---|---|---|
| Reviewer separation | PASS, structural | 400 assignments for 200 × 2 reviewers; separate logs; prior-review visibility forced false. |
| Deterministic allocation | PASS | Seeded SHA-256 split/order/orientation and byte-determinism test. |
| Split sealed before label 1 | PASS | Real 100/100 seal states zero labels and is hash-referenced. |
| Holdout isolation | REVISE-note | Membership is sealed, but the no-rule-revision flag is procedural until A2/A3 receipts enforce it. |
| Machine-flag blinding | PASS | Zero occurrences of the five excluded machine keys in 400 real reviewer rows. |
| Explicit abstentions | PASS | `ABSTAIN` and `POSSIBLE` are schema/packet outcomes; A1 precision remains null. |
| Restricted storage | REVISE | Build refuses synced output, but append was not bound to the original root. |
| Authority / source disabled | PASS | `AUTHORIZED`, `restricted-local-only`, and `enabled:false` are hard requirements. |
| Unit-distinct collisions | PASS | 60 legacy rows and 94 Politico profiles have different fields. |
| No auto-merge | PASS | Merge request always raises; A1 report pins labels/precision/merges to zero. |
| Zero labels | PASS | Restricted label directory contains policy only. |

## Adversarial findings

### F1 — High: self-anchored restricted receipt

`verify_adjudication_framework` and `append_label` trusted the receipt inside the restricted root. Internal files were checked against hashes supplied by that same receipt, but code did not compare it to the committed public receipt hash.

Required fix: both APIs take a required external expected receipt SHA-256; both fail closed if the restricted receipt differs. Verification must also validate the receipt schema and semantics.

### F2 — High: allocation trusted before hashing

`append_label` read the allocation manifest without first checking its hash. A forged assignment could authorize an otherwise unassigned label until a later verification run.

Required fix: hash-check the allocation before reading assignments; add a forged-assignment planted failure.

### F3 — Medium: copy-to-synced attack

A valid restricted framework could be copied into OneDrive and `append_label` called on the copy because the synced-root check only ran at build time.

Required fix: seal a root binding at build time and verify the resolved root at append and verification time; add a copied-framework planted failure.

### F4 — Low: missing JSON Schema maxima

The local schema validator enforced minimums but ignored `maxLength`, `maxItems`, and numeric `maximum`. The label-rationale cap and some receipt bounds were decorative.

Required fix: implement those keywords and plant an overlong-rationale failure.

### F5/F6 — method notes

Partition membership is visible to reviewers, and source identity remains structurally inferable despite randomized A/B position. These do not falsify A1's machine-flag blinding, but downstream documentation must not overstate the kind of blinding achieved. Dropping reviewer-visible partition is a method-v2 consideration.

## Required re-review evidence

1. External receipt anchor required by append and verify; receipt mutation fails both.
2. Allocation hash verified before assignment trust; forged assignment fails append.
3. Original-root binding; copied framework fails append and verification.
4. `maxLength`, `maxItems`, and `maximum` enforced; 3,000-character rationale fails.
5. Focused lane and deterministic real-data replay pass after a new immutable framework version is generated.

## Conditional A2 contract

- Each reviewer sees only its own packets and instructions, never the other reviewer’s labels, machine crosswalk, split seal, or pilot sample.
- The lane driver holds the allocation and calls `append_label` with the externally anchored receipt hash.
- Labels cite only packet evidence, prefer abstention, remain `MODEL_ASSISTED`, and are never described as human gold.
- Calibration labels may inform revision. Holdout results remain quarantined until one later evaluation bound to the split hash.
- Synced output contains aggregates and hashes only. `MATCH` and `DISTINCT` form the precision denominator; `POSSIBLE` and `ABSTAIN` remain separately reported.
- Disagreement is handled by a separate appended adjudication record; prior labels are never edited.
- Canonical publication, source enablement, and merges remain blocked.
