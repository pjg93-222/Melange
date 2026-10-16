---
name: terrier-compute
description: Review or perform explicitly scoped Terrier district compute builds and parity with private staged inputs, deterministic bundles and controlled live-data installation. Does not trigger Electron builds, hosted migrations, server restarts or collection.
---

# Terrier compute and bundle parity

Prepared 2026-10-16 from the 2026-10-14 procedure. Read the five `../ops-shared/`
references, starting with `chain-of-command.md`. Historical container defaults and
completed district checks are context, not current readiness or activation claims.

Use an explicit owner-selected Terrier checkout. Canonical source is
`pjg93-222/Geo/main`. Older local and image branch names describe historical
work; none of them is automatically today's app release ref. Verify full source
and image identities independently.

## Inspect and gate

1. Record current scope, source SHA, unfinished work and selected private data roots.
   Read current `COMPUTE.md`, `HOSTED.md` as relevant, and `references/traps.md`.
2. Optional metadata check:
   `powershell -NoProfile -File <skill-dir>/scripts/check-state.ps1 -Repo <absolute-terrier-checkout>`.
   This does not launch Docker, query applications or prove an evidence verdict.
3. For an authorized compute run, require trusted digest-pinned build/score images,
   bounded Docker availability check and at least 35,000,000,000 bytes reserved on
   C: after projected allocations, plus the target volume's explicit reserve.
4. Coordinate one heavy run. Legacy runners may remove every container with the
   shared `terrier-compute` label on timeout; do not overlap another owner or rely
   on that cleanup as safe. Verify mount masks and required mount points in the
   selected source without touching live `.local` data.

## Build and compare

Plan first and build only into a new empty output folder, never a live `.local`.
Use `references/runners.md` and preserve key/salt identity; new values would re-key
voters and are not a build repair. Verify expected runtime stores and receipts.

Untracked local `_build` runners are optional private tooling, not present or trusted
because this skill names them. Review their bytes and preserve backups before an
authorized edit. Their live installation phase is distinct from isolated building.

Use `references/bundle.md` for exact bundle bytes, SQLite/FTS5 gates, accepted
variance and negative controls. Reuse valid evidence only for the actual matching
source/image/input scope. Do not rebuild unchanged data solely due to this note.

## Live data and cleanup

Live swaps, snapshot imports, account-database migrations and server restarts need
current explicit scope, verified backup/rollback and ownership. A compute PASS is
not permission for them. Preserve existing accounts and local state.

Voter-derived inputs, stage stores and comparison copies remain local/private;
do not upload them to hosted runners or third parties. Synthetic fixtures may be
used for separately scoped public checks, but cannot prove parity on real inputs.
Dispose only of verified owned copies/volumes under current retention permission;
never blanket-delete a shared compose project. Record exact verdict and scope.
