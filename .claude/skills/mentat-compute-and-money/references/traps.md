# Mentat compute pitfalls

Prepared 2026-10-16 from historical 2026-10-14 findings. These are conditions to
check, not claims that old incidents or missing fixes still describe current state.

| Pitfall | Required handling |
|---|---|
| Accounting or launcher edits inferred from a rejected proposal | Follow the current human scope; preserve money semantics and exact acceptance gates |
| Source changes during a streak | Pin isolated committed source and complete frozen inputs; a new identity invalidates reuse |
| Local branch mistaken for canonical release source | Inspect the checkout/ref; publication destination is `pjg93-222/Mentat/main` via its existing filtered route |
| Worktree/permission guard blocks a write | Stop that write, identify the supported owning checkout and use the applicable approval process; never route around the guard with another command/tool |
| Stale Docker/digest status in prose | Read selected lock/config and current metadata, preserving authenticated digest validation |
| Replay proxy changes in another source tree | Pin exact proxy bytes and hash per snapshot; keep the private replay root outside publication |
| Replay reaches an untrusted TLS host | Fail closed and record scope; never widen trust just to pass |
| Secret-leak record | Preserve refusal/cleanup behavior and private evidence; do not commit or upload a cassette |
| Melange collect flag confused with Mentat money | Verify the actual Mentat launcher; the Melange flag does not activate it |
| Stale console or absent listener | Report observed identity/state; do not infer cause or restart it from an old incident |
| Cloud placeholders or clock uncertainty | Ensure required inputs are local and complete and clock checks pass before an authorized run |
| R/package version differences | Preserve locks and actual parity evidence; don't declare equivalence from another build's versions |
| Historical broad-process-kill report | Never infer a new exit cause from it; no broad process-name kills |

Private memories and old handoffs may explain these lessons locally; they need not
be exported, read wholesale, or treated as current permissions.
