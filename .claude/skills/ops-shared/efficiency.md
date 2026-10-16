# Capacity and coordination

Prepared 2026-10-16. Historical parallel-run approvals and agent-model preferences
from the 2026-10-14 notes are not current permissions or defaults.

- Default to one heavy local operation at a time. Coordinate builds, parity sides,
  collection and large copies with their existing owners. Small independent reviews
  can proceed within scope; do not start a duplicate release worker or re-run a
  passing unchanged build merely to demonstrate activity.
- Preserve at least **35,000,000,000 bytes** of free storage on C: for the current
  release work. This is a decimal-byte reserve, not 30 GiB. For other target volumes,
  establish their reserve explicitly; don't assume C: headroom covers them.
- Check projected free space after the next allocation, including staging,
  decompression and verification re-copy. Parallel writers share one budget; a
  startup-only free-space check is insufficient. Pause new allocations before the
  reserve would be crossed. Do not delete research caches, snapshots or unfinished
  work to satisfy the floor.
- Legacy Terrier runners may remove all containers with their shared project label
  on timeout. Until ownership-scoped cleanup is verified, never overlap those
  runners with another job using that label. A label is not proof of ownership.
- Avoid parallel recursive walks. Search explicit relevant directories, exclude
  datasets/dependencies, and bound the search. Do not dump process command lines or
  private logs into a publication receipt.
- Prefer supported completion notifications or an existing scheduler over repeated
  tight polling. Use bounded status reads and write a checkpoint before stopping.
  Do not create a scheduler, detached job or monitor merely because this note lists
  one as an option.
- Keep the existing owner and its verified partial work. A stopped or uncertain
  session is not permission to kill, restart or duplicate it. Reconcile handoffs and
  exact active operations before assigning a replacement.
- Give any authorized collaborator an exact path scope and acceptance criteria.
  Use the current configured tools/models; historical model names are not a
  requirement. Never route around a permission or worktree guard.

The read-only state scripts report current metadata and reserve bytes, but do not
predict job size or certify that no competing writer exists. See `host.md` for
cleanup and `records.md` for evidence that survives an interrupted session.
