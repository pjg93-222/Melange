# Host observations and preservation

Prepared 2026-10-16. Docker/WSL versions, ports, task states and machine settings
quoted in the 2026-10-14 source notes are historical, not assertions about this host.

## Container availability

For an authorized compute run, use one bounded read-only Docker availability probe.
A timeout means unavailable or unverified, not a diagnosis or permission to restart
services. Report it and continue independent work where possible. Do not change
WSL configuration, restart Docker/Windows, install software or shut down a VM as a
side effect of a state check. Such actions can interrupt unrelated writers.

Inspect selected compose definitions and image sources before execution. Images
must use the expected digest and the existing authenticated release/pinning policy.
Do not paste old image digests or weaken signature checks. Native desktop packaging
and runtime work remain separate; this skill does not migrate them to Docker.

## Storage and cleanup

The current C: reserve is **35,000,000,000 bytes**, with projected allocation checks
as described in `efficiency.md`. No deletion target in the old D-205 list remains
preapproved merely because the list existed.

Before any authorized cleanup, identify exact owned paths or volume IDs, active
users, retention needs and recovery coverage. Preserve data, credentials, research
caches, uncommitted/ignored work, installed-only files and held recovery snapshots.
Do not blanket prune Docker images or volumes: an apparently unused image can still
be pinned for a required release or fallback. Do not force-remove worktrees.

Voter-derived stage volumes and comparison copies remain private. When their
retention period ends and scoped disposal is authorized, remove only the verified
owned copies/volumes after retaining non-sensitive evidence. A broad compose
`down -v` against a shared project can destroy another run's state and is not a
generic cleanup command. A failed or interrupted run is not evidence that its
recovery copies are disposable.

Keep long-running scratch work outside automatic temporary-file cleanup locations.
Preserved old mtimes can make a fresh copy eligible for a cleaner. Choose a dedicated
approved scratch root; this is not permission to change global cleanup settings.
Use literal resolved paths and the native worktree lifecycle when removal is in
scope. Confirm results without trusting exit status alone.

## Processes, services and ports

Inspect only relevant process metadata and listener ownership; do not print full
command lines, tokens, task actions or environment values. Historical ports in the
source notes are clues to verify, not a free-port allocation or restart instruction.
No broad process-name kill, server restart, task enablement or installer replacement
is part of these state scripts. Preserve active sessions and atomic operations.

The scripts inspect repository/file metadata and free space only. They deliberately
do not contact Docker, enumerate processes/tasks, call application code or start a
network request. Complete any remaining readiness checks separately within scope.
