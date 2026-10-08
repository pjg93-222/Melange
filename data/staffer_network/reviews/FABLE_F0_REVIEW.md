# Fable F0 — staffer-network completion-contract audit

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`  
Stage: `F0`  
Reviewer: Fable through the read-only Claude lane  
Date: 2026-08-30  
Preservation note: Codex normalized mojibake in the lane transcript to ordinary Unicode punctuation; the findings and numbers are otherwise unchanged.

## Artifact acknowledgement

Fable read all seven required artifacts in full. The lane could not execute hash commands, so it verified the cross-artifact hash interlocks and required Codex to seal the supplied hashes independently. Codex's pre-dispatch `Get-FileHash -Algorithm SHA256` pass matched all seven expected values.

| Artifact | Fable evidence used | SHA-256 status |
|---|---|---|
| `STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md` | Phase 0 exit near line 418; Politico Phase 3 near 442; pilot state near 449; sections 13–14 | Codex matched expected hash |
| `STAFFER_NETWORK_CORPUS_SPEC_20260829.md` | Baseline section 3.1, lines 39–50; LDA C-5, lines 87–99; readiness ruling near 312 | Codex matched expected hash |
| `STAFFER_NETWORK_METRICS_20260829.md` | C-2 near 43; C-5 near 47; P-1 near 99; I-10a near 101; I-11 near 103; final adjudication near 165 | Codex matched expected hash |
| `audits/STAFFER_NETWORK_IMPLEMENTATION_DIAGNOSTIC_20260829.md` | 42/42 pass and interrupted-rerun note, lines 8–12; pilot near 32; backlog section 7 | Codex matched expected hash |
| `data/staffer_network/receipts/politico_resolution_pilot_20260829.json` | Entire receipt and recomputed arithmetic | Codex matched expected hash |
| `data/staffer_network/policy/politico_pro_source_manifest_20260829_v2.json` | `enabled:false`, authorization, counts, files | Codex matched expected hash |
| `fec/staffer_network/politico_normalize.py` | Contact fail-closed, dispositions, deterministic sample, null-precision receipt | Codex matched expected hash |

Fable also inventoried 9 receipts, 5 policy files, 17 staffer-network modules, 15 schemas, and 8 staffer-network test modules registered in `fec/tests/run_tests.py`.

Independent arithmetic checks passed:

- `4,836 + 60 + 877 = 5,773` legacy rows.
- `4,836 + 60 = 4,896` legacy rows with exact-name overlap.
- `2,643 + 425 + 50 + 1,718 + 94 = 4,930` exact-name-overlap Politico profiles.
- A case-insensitive scan of `data/members/staff_directory.json` found no `email` or `phone` keys.
- The other two synced surfaces are supported as zero-finding by the P-1 receipt.

## Ruling

**PASS** for proceeding to A1, the deterministic adjudication framework, and for that scope only.

The sample is 200 generated, 0 adjudicated; precision is correctly `null`; `auto_merge_enabled` is false; and canonical merges are 0. This does not clear Politico for canonical use, does not clear LDA C-5, and does not arm any analysis or delivery engine.

## Metric adjudication

- **Observed:** Politico census/normalization counts of 18,618 persons, 22,309 roles, and 20,485 issues; crawl-conduct receipt; P-1 zero-contact findings; 5,773/5,773 pilot conservation.
- **Derived:** `legacy_outcomes.REVIEW_NAME_COLLISION = 60` is a legacy-row subtraction. The disposition-side `REVIEW_NAME_COLLISION = 94` counts Politico profiles. The shared label has different units and denominators. Outcome conservation is bookkeeping, not identity quality.
- **Provisional:** 4,836 unique-name candidate yield; 2,643 strict-stratum candidates; title and office heuristic behavior.
- **Null:** strict-sample precision because 0 of 200 rows are adjudicated.
- **Blocked:** recall, because a strict-only sample cannot measure it; I-4 requires an exhaustively labeled candidate universe.
- **Failing:** LDA C-5, with 539,782 unique UUIDs versus 539,870 objects, 88 identical duplicates, and a moving endpoint census.
- **Inconclusive:** the interrupted repository-wide test rerun.

Two circularity defects must be fixed in A1:

1. The current review-sample records contain the machine's `disposition`, `title_match`, and `office_match` flags. Showing them to reviewers would anchor the supposedly independent judgment.
2. The same 200 rows cannot be used both to revise a rule and to quote its final precision. Calibration and holdout membership must be sealed before the first label.

## Completion contract

Required in dependency order:

1. Build a blinded presentation layer that strips machine flags; deterministic dual-reviewer allocation with recorded seed and hash; calibration/holdout membership sealed before the first label; append-only restricted-local label store; `MATCH`, `DISTINCT`, `POSSIBLE`, and `ABSTAIN` vocabulary; public-safe aggregate receipt.
2. Double-review the 200 strict rows without changing the candidate rule.
3. Measure agreement, resolve conflicts, audit zero leakage, and emit a public-safe receipt with precision confidence bounds.
4. Extend the sample across title/office conflict, no-office-evidence, name-only, and collision strata; label a bounded exhaustive block for recall estimation.
5. Revise on calibration labels only; evaluate once on untouched holdout; produce the I-4/Q-1 freeze packet before proposing any merge policy.

Required for the canonical corpus but independent of A1:

- Recollect affected LDA query-years with frozen watermarks and disposition all 88 duplicates.
- Resolve A-0 internal-use authority for the legacy seed, then run C-10a stripped-seed import with 5,773/5,773 rows, 533/533 offices, and no contact fields.
- Acquire the matching-vintage LittleSis entity dump.

Optional future breadth, not required for an honest A1 result: House SOD and Senate disbursement collectors, IPEDS/CIP references, covered-position parsing, pre-2021 LDA backfill, and additional licensed profile sources.

## A1 acceptance tests

1. Every sampled row has two independent reviewer identities; no reviewer sees the other's label or rationale before submitting.
2. Allocation reruns from the same review-sample hash and seed are byte-identical.
3. Calibration/holdout membership hash is recorded before label 1; no holdout candidate appears in rule-revision inputs; holdout is evaluated once.
4. Reviewer-visible payload excludes `disposition`, `title_match`, and `office_match`.
5. `ABSTAIN` and `POSSIBLE` remain explicit outcomes and are excluded from the precision numerator and denominator while their counts remain visible.
6. Labels and rationales remain under the restricted machine-local root; synced receipts contain only counts, rates, and hashes.
7. The Politico v2 manifest remains `enabled:false`, and adjudication does not widen A-0 authority.
8. Canonical merges remain 0 and auto-merge remains false; a negative merge-path control must fail closed.

## Risk register

| Severity | Finding | Required remediation |
|---|---|---|
| High | Reviewer anchoring from machine flags in sample records (`politico_normalize.py` near 404–424). | Present a blinded projection and seal a blinding manifest. |
| Medium | Collision label carries two units: 94 profiles versus 60 legacy rows. | Introduce unit-distinct names in the next method version; do not mutate the sealed receipt. |
| Medium | Office “conflict” can reflect container-type mismatch rather than contradictory evidence. | Sample that stratum and record container mismatch as a distinct adjudication reason. |
| Medium | Fable could not execute direct file hashing. | Resolved by Codex's matching SHA-256 pass before and after review. |
| Medium-low | LDA C-5 remains failing. | Recollect affected years with frozen watermarks and disposition the duplicates. |
| Low | Repository-wide test state is inconclusive. | Re-run the full registered lane after A1 code lands; keep status unknown until then. |
| Low | Restricted review content could leak into synced storage. | Keep record-level artifacts outside OneDrive and enforce aggregate-only receipt tests. |

## Bottom line

The pilot is a conserved, deterministic, zero-merge candidate report with honestly null precision. A1 may proceed under the contract above. Canonical publication, source enablement, and all arming remain blocked.
