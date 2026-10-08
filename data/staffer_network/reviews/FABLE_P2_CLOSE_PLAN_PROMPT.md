# Fable P2 residual-closure preflight

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

Act as a read-only adversarial reviewer. Return `PROCEED`, `REVISE`, or
`BLOCK`, followed by concise binding requirements. Do not edit files.

Read completely:

- `data/staffer_network/reviews/FABLE_P2R2_REVIEW.md`
- `data/staffer_network/reviews/FABLE_C1R_REVIEW.md`
- `fec/staffer_network/source_native_corpus.py`
- `fec/staffer_network/publication.py`
- `fec/staffer_network/schema_validation.py`
- `fec/staffer_network/schemas/littlesis_relationship_assertion.schema.json`
- `fec/tests/staffer_network/test_staffer_source_native_corpus.py`
- `fec/tests/staffer_network/test_staffer_schema.py`

Review this proposed closure of Fable's two non-blocking P2 residuals:

1. Add and register a JSON schema for the six-field
   `staffer-network-legacy-source-native-record-v1` row, and make both corpus
   construction and full local validation use it while preserving exact key
   shape, restricted namespace, public-safety checks, and the sealed 5,773-row
   bytes.
2. Add a fabricated Position whose `boss_id` is absent from the full entity
   spine. Require the build to emit `boss_source_entity_id: null`, increment
   `boss_references_redacted`, and never create a dangling namespaced ID.
3. Keep production corpus and receipt bytes unchanged; rerun the full staffer
   suite and update only the 2026-08-30 diagnostic facts needed to mark these
   two residuals closed.

Identify any needed negative control or scope protection. This stage must not
enable identity resolution, analysis, LDA, publication, or `STAFF_NET`.
