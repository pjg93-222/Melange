# Melange compute pitfalls

Prepared 2026-10-16; historical failures from the 2026-10-14 notes are leads, not
assertions that the current source still has them.

| Pitfall | Required handling |
|---|---|
| Wrong evidence filename | The chain gate reads `chain_parity.json`, not a similarly named narrative report; verify the selected tool's slot |
| Shared dirty files or line endings | Preserve owner edits and exact bytes; no blanket commit, stash, restore or EOL normalization |
| Empty worktree data plane | Confirm the harness's actual data roots; do not infer main's behavior from missing local fixtures |
| VM-blind PID locks | Use separate frozen inputs and coordinated sequential heavy runs |
| Relocated run writes live local state | Require the supported isolated `--local-dir`; never bypass its guard |
| Pinned date leaks into production | Limit `MELANGE_TODAY` to the owned parity process and restore it afterwards |
| Image tag/local build substituted for CI evidence | Use the existing authenticated manifest/trusted digest and record its identity |
| Docs assert old engine/repair state | Inspect selected code, current engine settings and actual evidence |
| Scheduler/lease race or cancellation uncertainty | Verify writer-lease transfer and signal behavior in selected bytes before cutover |
| Missing dashboard credential wiring | Report the exact missing setup without exposing keys or weakening authentication |
| Partial chain skips intake/money gates | Do not claim full-chain equivalence from `--from` or dashboard-only output |
| Temp cleaner removes scratch with old mtimes | Use approved retained scratch storage and check retention before execution |
| Historical retrain/cleanup/task request | Treat it as dated context, not permission to schedule, delete or restart now |

Optional private context: the 2026-10-13/14 handoffs and
`audits/deploy_20261011` designs. Do not publish them or depend on private session
paths. Completed current repairs must not be reverted to reproduce those notes.
