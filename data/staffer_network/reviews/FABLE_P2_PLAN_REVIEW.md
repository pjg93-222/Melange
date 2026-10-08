# Fable P2 source-native corpus preflight review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

## Ruling: PROCEED — with binding safeguards

Fable read and cross-checked all eleven evidence items. The plan is
structurally conservative: one immutable restricted generation outside synced
storage, source-native IDs only, no cross-source merges or currentness claims,
LDA and Politico out of scope, and only an aggregate receipt in the repository.

The category correction is material and verified: category 5 is `Donation`
(1,267,716 accepted), while category 7 is true `Lobbying` (10,655). The old
specification text is wrong and must be corrected before final implementation
readiness is claimed.

## Adjudicated design

1. Approve a separate source-native assertion schema. Preserve raw LittleSis
   dates verbatim and derive conservative precision (`day`, `month`, `year`, or
   `undated-only`). Do not coerce zero-padded coarse dates to exact dates. A raw
   `is_current` value may be retained only as a source assertion and may never
   become a present-employment claim.
2. Emit exactly the accepted `Position`, `Education`, and true `Lobbying`
   assertions: 368,995 + 44,673 + 10,655 = 424,323. Disposition the other
   1,456,165 accepted relationships as `OUT_OF_SCOPE_CATEGORY`.
3. Emit the full valid LittleSis entity spine of 443,140 entities. This keeps
   endpoint conservation and future category expansion deterministic.
4. Keep LittleSis and legacy records in separate files and namespaces. Copy the
   already stripped legacy record file by its sealed hash; do not rederive it
   and do not create cross-source references.
5. Follow the atomic legacy-generation pattern: refuse an existing target,
   stage in a sibling directory, use canonical JSON and deterministic gzip,
   publish with one rename, and prove clean double-build byte equality.

## Binding safeguards

### S-1 — Input pins

Refuse to run unless the entity gzip is exactly 76,691,985 bytes with SHA-256
`5cc0039aa43e650b46bfa9e9bfc1813c67969cae1bdb9c9e8770fc117cd29d3c` and
the relationship gzip is exactly 110,381,587 bytes with SHA-256
`c11d7058cb13d264854f703310fddf30c1391ef604c0164847945939fd38d489`.
The profile receipt itself must be sealed, `PASS`, and source-native ready.

### S-2 — Category provenance

The receipt records the corrected category map and states that native
`category_id` values are the basis. Queue the draft/spec correction; the local
generation need not wait for the prose correction.

### S-3 — Placement and quarantine

Fail closed if the generation is inside a synced root. The repository receipt
contains no entity names or record bodies. It must assert `STAFF_NET=off`,
`source_enabled=false`, `analysis_enabled=false`, zero canonical merges, and a
deferred CC BY-SA publication review.

### S-4 — Cross-source firewall

Use distinct `littlesis-bulk` and `quorum-legacy-derived` namespaces. No output
record may reference the other namespace, a Politico UUID, a Bioguide ID, or an
LDA identifier. The legacy collection must equal the sealed 5,773-record file
hash `439bb67f7093f28cd67010cdc12e9f7a86eeee9e8fd36c81709073260a17ff48`.

### S-5 — Exact conservation

- `entities_emitted = 443,140`.
- `emitted_in_scope + out_of_scope_category + dangling_rejected + invalid +
  duplicates = 1,880,491`.
- Emitted per-category counts equal the profile receipt exactly.
- Out-of-scope counts equal the remaining categories exactly.
- Re-derive and list the three dangling relationship IDs; all three are
  `Transaction`.
- Recheck every emitted endpoint against the emitted spine.
- Recompute 226,370 undated Position assertions; undated assertions have zero
  temporal weight.
- Two clean builds must be byte-identical.

### S-6 — Publication and tests

Register the new receipt schema and semantic validation. Add registered
negative controls for a fabricated dangling endpoint, an emitted Donation,
cross-namespace references, `source_enabled=true`, and wrong input hashes. Add
the restricted corpus root to the path contract.

### S-7 — No premature completion

The receipt must say explicitly that this substage does not complete or advance
cross-source person resolution. There are zero merges and identity assertions;
the Politico adjudication queue is untouched; LDA and Politico gates remain
closed.

Fable made no file changes. Codex remains the only writer.
