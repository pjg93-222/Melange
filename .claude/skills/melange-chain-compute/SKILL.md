---
name: melange-chain-compute
description: Review or perform explicitly scoped Melange chain, collector-replay and office compute parity or engine changes. Covers frozen inputs, evidence and fallback. Does not trigger Electron packaging, publication, collection or container activation merely because the skill is loaded.
---

# Melange compute parity and controlled cutover

Prepared 2026-10-16 from source commit `6df9422a6` (2026-10-14). This is a procedure,
not a claim that the historical pending chain/collect cutovers are complete.
Read the five references in `../ops-shared/`, starting with
`chain-of-command.md`. Historical approvals do not add current scope.

Use the explicit Melange checkout selected by its owner. Canonical app-source
publication is `pjg93-222/Melange/main` through the existing filtered route, not a
raw-history push. Local compute branches and container image refs are separate.

## Inspect before execution

1. Record the selected source SHA, existing owner, current request and unfinished
   work disposition. Read `ops/compute/README.md` and `references/traps.md`.
2. Optional metadata check: `powershell -NoProfile -File <skill-dir>/scripts/check-state.ps1 -Repo <absolute-melange-checkout>`.
   It runs only read-only Git/metadata queries; it does not certify Docker, jobs,
   signatures, parity verdicts or readiness.
3. Inspect the current `ops/compute/engines.json`, relevant environment overrides
   and exact evidence before concluding which phases use containers.

## Gates for a separately authorized compute run

- Docker available through a bounded probe; trusted digest-pinned images.
- C: retains at least 35,000,000,000 bytes after projected allocations; sufficient
  reserve on every other output volume; one coordinated heavy local job.
- No overlapping chain/refresh writer; a PID-based lock cannot see across a VM.
  A missing `.pipeline_run.lock` alone does not prove the tree is free.
- Scheduler coordination is explicit; do not disable or re-enable tasks from an old
  handoff. Preserve any current collector hold.
- Verify writer-lease transfer/reacquisition, cancellation/SIGTERM behavior,
  relocatable receipt paths and required inputs in the exact selected source.
  Old commit IDs in private notes are historical leads, not a current gate result.
  Unknown ownership or unfinished fixes remain unresolved until reviewed.

## Proof and transition

Use `references/parity.md` for chain freeze/reference/container/compare procedures.
Do not manufacture A2 to satisfy a harness that still requires two reference runs.
Keep outputs and scratch state isolated from live data.

For chain/collect/office, use `references/cutover.md` only after both the applicable
evidence and current authorization cover the transition. A PASS alone does not
switch a system. Record the evidence hash, exact source/image identities, engine
change and fallback verification.

Collector replay of one keyless collector does not prove every network collector
or the FEC money lane. Secret-file wiring, scheduler integration and cancellation
must be verified separately; never invent keys or widen replay TLS trust.

The older notes reported office on a container, but current engine state and image
trust must be read. Re-prove only changed relevant code/image/input contracts; do
not treat this document as an instruction to rerun passing desktop acceptance.

Retain required recovery evidence and private-data protections. Dispose of owned
comparison copies only under the current scoped retention/cleanup decision. No
Docker prune, global observer hook, task restart or source publication is implicit.
