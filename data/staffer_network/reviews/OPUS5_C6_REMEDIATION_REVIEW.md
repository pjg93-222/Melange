# Opus 5 C6 remediation review

`VERDICT: PROCEED`

Opus 5 re-read the remediated implementation, schemas, publication containment, upstream producers, and tests. No repository file was modified and no network was used. The reported 94 tests and 47 subtests were treated as supplied evidence.

## Original findings

| Finding | State | Evidence |
|---|---|---|
| R1 publication containment | CLOSED | Both schemas are restricted on publish/load; negative controls exercise both IDs. |
| R2 measured build safety | CLOSED | Rows are schema/semantically validated before write and after reread; receipt counts derive from persisted rows and file bytes/hash. |
| R3 shared government-term definition | CLOSED | Candidate build imports and uses the upstream LDA function. |
| R4 cross-source multiplicity | CLOSED | Per-name and row-level total/per-source multiplicities are required and receipt-counted. |
| R5 honest normalizer contract | CLOSED | Method says normalized-name equality; version and four lossy rules are pinned. |
| R6 paired raw evidence | CLOSED | Each normalized key pairs raw LDA variants with raw target names and DISPLAY_NAME/ALIAS basis. |

Opus also verified exact upstream schema/status/zero-merge checks, byte/hash inventory binding, method-and-corpus-bound candidate IDs, build-time ID recomputation, and a full pinned-time byte-identity twin.

## Non-blocking residuals

- Add planted failures for upstream receipt/hash/count gates.
- Promote the full output directory atomically rather than leaving a loud, receipt-less partial directory after a crash.
- Pin tests directly to the name normalizer behavior/version.
- Recompute receipt-to-row source binding during standalone validation.
- Treat the three zero-confidence/merge counters as summaries of enforced row constants, not independent evidence.

These residuals do not permit a merge, score, publication, or downstream gate opening. The live restricted candidate build may proceed after the reconciled LDA corpus is sealed.
