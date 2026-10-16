---
name: mentat-compute-and-money
description: Review or perform explicitly scoped Mentat compute-job parity and bounded money record/replay. Covers immutable inputs, exact money gates, image trust and controlled launch/task changes. Does not resume collectors, change accounting semantics or trigger Electron releases.
---

# Mentat compute and money parity

Prepared 2026-10-16 from the 2026-10-14 compute procedure. This document does not
claim that the pending job streaks or money cutover are complete. Read the five
`../ops-shared/` references, beginning with `chain-of-command.md`.

Use the owner-selected Mentat checkout, with runbook `mentat/COMPUTE.md`.
Canonical app-source publication is `pjg93-222/Mentat/main` through its established
filtered route. No local branch name is an assumed release target. Source publishing,
native Electron packaging and container-job activation are separate operations.

## Inspect and preserve

1. Record current scope, exact source identity and unfinished work. Historical money
   rulings are context; do not infer permission to change collection/counting rules
   or launchers from a general compute task. Keep held collection batches held.
2. Optional metadata check:
   `powershell -NoProfile -File <skill-dir>/scripts/check-state.ps1 -Repo <absolute-mentat-checkout>`.
   This reads local metadata only; it does not query a collector, Docker, task or app.
3. Read `references/traps.md` and the selected runbook. Establish active job ownership
   separately; a clean tracked tree is not proof that no writer is running.

## Gates for an authorized parity run

- Trusted CI image digest from the selected `mentat/compute.images.lock`, Docker
  available, clock checked, one coordinated heavy operation.
- C: reserve of at least 35,000,000,000 bytes after projected allocations; explicit
  reserve for any other data volume.
- Immutable source identity and complete frozen inputs for the whole run. Do not
  freeze other owners' shared work by assumption; use an isolated accepted source.
- No overlapping money collector/report sharing keys or quotas. Live R0 spends
  requests; current authorization and budget must cover it. Never resume a paused
  batch as a side effect of parity work.

## Money replay and official-job proof

`references/money-runbook.md` preserves the R0/A1/A2/B sequence, proxy pinning,
three-snapshot streaks, exact Decimal/multiset gates and stop rules. A mask must
never hide money. Secret leaks, refused TLS hosts, incomplete B or a changed source
identity invalidate proof. Do not widen proxy trust or alter semantics to pass.

`references/jobs.md` covers anchors, refit-detect, pocket-build and refit-parity on
the official image. Historical local-image passes are not transferable to another
digest; old missing inputs are not a completed streak.

## Controlled transition

Money-job launchers and scheduled jobs are different transition points. There is
no shared Melange `collect` flag that activates Mentat money. Only make a launcher
or task change when current scope includes it, its exact prerequisites pass and a
preserved rollback is available. Existing authorization need not be asked again;
old D-numbered notes do not supply new permission.

Record exact source/image/snapshot identities, actual request counts and verdicts.
Cassettes, keys, replay stores and local financial data remain private and are not
committed or exported. Retain unfinished work and required recovery artifacts.
