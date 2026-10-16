# Records and provenance

Prepared 2026-10-16 from the 2026-10-14 compute notes. Private Brain records,
D-/DE-numbered decisions, memories, session scratchpads and unpublished audit files
may supply local historical context. They are optional inputs, not dependencies
that must be exported or automatically updated to use these skills.

## Use a current handoff

Read the existing owner's current checkpoint before starting related work. Preserve
historical evidence, mark superseded status with a date, and avoid treating an old
OPEN item or completion claim as current. Do not write into another owner's ledger
or private vault without the applicable task scope. No Brain boot, write, mirror,
commit or auto-push is prescribed by this publication.

For commands, use the selected committed runbooks: Melange `ops/compute/README.md`,
Mentat `mentat/COMPUTE.md`, Terrier `COMPUTE.md`/`HOSTED.md`. Validate CLI options
against the selected source. Private `audits/deploy_20261011` designs and the
2026-10-13/14 handoffs may explain intent; they need not exist in a public checkout.

## Record each claim separately

| Claim | Minimum evidence |
|---|---|
| Selected source | Checkout/ref/full SHA, dirty-work disposition and exact selected paths |
| Published source | Canonical remote/ref/full SHA, filtered source/blob mapping and redactions |
| Compute parity | Input manifest, source/image identities, scope/counts, verdict, negative controls and evidence hash |
| Cutover | Existing authorization scope, before/after engine state, exact verified evidence and rollback plan |
| Mentat replay | Snapshot identities, actual R0 request counts, secret-leak status, judge/streak evidence |
| Desktop package | Exact source provenance, artifact hash, signing status and actual acceptance scope |
| Interrupted work | Current operation, verified partial artifacts, preserved unfinished paths and concrete next step |

State UTC observation time and distinguish direct observations from relayed claims.
Quote human instructions only when the words are available; otherwise label the
source as a relay. Label implementation choices and hypotheses as such. Never
invent a decision ID or imply that an old ruling authorizes a new action.

Record failures and unverified phases alongside passes. Express money semantics in
terms of what a change starts/stops counting, without implying that a rejected
proposal was approved. A baseline attribution needs actual baseline evidence.

Keep private datasets, cassette contents, keys, full process arguments and recovery
snapshots out of GitHub and public receipts. Use scoped non-sensitive summaries and
hashes. Retain original private records locally under their existing policy; do
not publish the whole Brain to satisfy a citation.
