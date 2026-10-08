# Completed ranking mathematics and spine integration

The ranking work is complete in the supplied worktree and integrated into main. The controlled v7 comparison and final v8 primary/twin builds both passed independent full graph verification. The v8 graph, identity spine and source-row payroll evidence now drive the published consumers and service on port 8841.

## Released inputs and output

| Component | Verified generation or artifact |
|---|---|
| Identity spine | `hill_personnel_spine_20260908_v8_primary`: 144,692 people, 204,699 spans, 1,351,415 admitted observations; 50/50 checks |
| Native Politico remap | `spine_identity_adjudication_20260908/spine_id_map_v6_to_v8.ndjson.gz`: 7,712 referenced native IDs, one target each |
| Math graph | `staffer_social_network_20260908_v8_math_primary`: 4,546,099 positive edges, 120,993 scored people, 23,699 isolates |
| Payroll evidence | `payroll_identity_20260908_v8_primary/payroll_identity_evidence.json.gz`: 425,825 episodes, 135,039 employment people, 231 pairs |
| Guarded switch | `audits/staffer_live_runtime/repin_20260908T060735Z.json`: completed, 120 tests passed |
| Live validation | `audits/staffer_ranking_math_20260908/live_cutover_validation.json`: PASS |

Full graph verification SHA256: `66574aa1e3e520b367c40ef81b82dfbe32d5675c9a001c9e6617e1730fe43034`. Graph receipt SHA256: `9c5384786f9b260edeca643297ab575c59324969077627ca6680788499d54723`. Payroll migration receipt SHA256: `e6851422d5c7c741aa68c388393d4cad282c8d9be349d580c3dbccadffea3234`.

## Contract and integration

Duration uses the union of guaranteed overlap days across eligible workplaces. Each office receives a share proportional to its overlap days times the exact shared-role factor (0.05). Admin/intern compensation headers provide no scoring support. People and provenance remain, and valid support from other offices survives. Office strengths conserve each person's total strength.

Member ties use published PageRank then eligible member-specific office strength. Bridges require supported connections to at least two eligible members and rank strength beyond the strongest member office, then PageRank. Exact ties stay explicit; IDs are display-order keys only. The legacy member template renders shared ranks and cutoff explanations.

The verified outreach CLI compares exact origin/candidate/target IDs on the complete positive operator using independently shortest reciprocal-weight legs. These can retrace nodes; the result is not a simple introduction-path claim. It does not replace the live UI's separate feature-based route objective.

All canonical/primary promotion flags remain false/zero. Five-percent damping is provisional, not a calibrated relationship probability or finite cap on aggregate strength. Report-period continuity and `title_last` remain inherited input limitations.

Ten math source/test files were integrated after baseline hash checks: builder, verifier, shared helper, member/bridge producer, outreach CLI, three test files, pipeline JSON budget and legacy member template. Copied context dependencies were not substituted for the identity task's changes. Do not apply the integration patch twice.

Main additionally selects v8 in the graph loader, producer, pipeline guards and repin helper. Inventory/routing fallbacks follow the graph's shared selector. Payroll JSON selects verified v8 evidence. The launcher preserves the selected dashboard and defaults to the authorized `Moneyball_Redesign.html` target.

`build_candidate.py` takes explicit spine, native remap and configuration inputs with a bound baseline receipt. Build independent primary/twin directories and run full verification. Never copy scores through an ID map or resolve a one-to-many split arbitrarily. Both split pairs survive as four distinct live IDs.

All four staffer section JSON files are published and hash-checked. The final member section is 5,393,487 bytes with 533 members, 7,675 ranked rows, 888 tie rows and 25 bridges. Its cap is 6 MB; each Groups artifact retains its 5 MB cap. The `_01` staffer page uses provenance scope deliberately.

The member desk and combined redesign pages were rebuilt using the dashboard task's requested commands. Live validation accounts for all 144,692 payroll IDs in profiles/accepted aliases, with zero invalid v8 references in the inventory, live groups, split API results or published data/pages. HTTP matches the authorized redesign plus local shell and identical external profile script.

## Receipts and remaining wider audit issues

`completion_receipt.json`, `live_cutover_validation.json` and `audit_failure_classification.json` record hashes, checks and the delivery boundary. `live_rollout.patch` preserves the exact cutover, including v8 guards in the other task's existing uncommitted Groups pipeline block. Unrelated source edits remain untouched.

The broader dashboard audit is 554 passed / 15 failed. Pre-cutover backup hashes prove the two email-input mismatches and old staffer-manifest mismatch already existed. Other differences concern historical manifest sentinels and absent rescue/git-pack paths outside the v8 cutover; no unsupported claim of an unrecorded baseline is made.

Carbonite locks canonical `Moneyball.html`. The dashboard owner explicitly authorized the rebuilt `Moneyball_Redesign.html` as the live target and preserved global manifests. Its HTTP bytes, complete v8 data islands and committed launcher fallback are verified. The canonical filename freshness check remains recorded, not falsely marked passing. No global publication-audit PASS is claimed.
