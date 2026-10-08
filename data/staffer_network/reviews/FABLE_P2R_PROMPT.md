# Fable P2 source-native corpus implementation review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

Act as a fresh read-only adversarial reviewer. Return `PASS`, `REVISE`, or
`BLOCK`, then list findings by severity. Do not edit files.

Read:

- `data/staffer_network/reviews/FABLE_P2_PLAN_REVIEW.md`
- `fec/staffer_network/source_native_corpus.py`
- `fec/staffer_network/schemas/littlesis_entity_assertion.schema.json`
- `fec/staffer_network/schemas/littlesis_relationship_assertion.schema.json`
- `fec/staffer_network/schemas/source_native_corpus_receipt.schema.json`
- `fec/staffer_network/schemas/source_native_corpus_determinism_receipt.schema.json`
- `fec/staffer_network/publication.py` (new source-native branches)
- `fec/tests/staffer_network/test_staffer_source_native_corpus.py`
- `fec/tests/staffer_network/test_staffer_schema.py`
- `fec/tests/run_tests.py` (registration)
- `fec/paths.py` (restricted root)
- `data/staffer_network/receipts/source_native_corpus_20260830.json`
- `data/staffer_network/receipts/source_native_corpus_determinism_20260830.json`

Observed real-build evidence:

- Full entity spine: 443,140 emitted, zero invalid/duplicates.
- Scoped relationship assertions: 424,323 = 368,995 Position + 44,673
  Education + 10,655 true Lobbying.
- Explicit out-of-scope dispositions: 1,456,165, including 1,267,716
  Donation records.
- Three dangling relationship IDs were re-derived and rejected; zero missing
  endpoints in emitted assertions.
- 226,370 undated Position records; every emitted assertion has temporal weight
  zero. Raw dates are preserved. `2008-00-10` is conservatively classified as
  year precision because its month is unknown.
- 38 contact-like free-text values and two dangling parent references were
  redacted and counted.
- The 5,773-record legacy file was copied exactly by sealed hash.
- Zero canonical merges, cross-source identity assertions, source/analysis
  enablement, or changes to the Politico queue. LDA and Politico gates remain
  closed for this standalone generation.

Determinism incident and remediation:

- First real twin attempt found a one-byte entity-gzip mismatch caused by alias
  values tied under a case-fold-only sort key. The two attempts were not
  selected and their differing receipt hashes are recorded.
- The key is now a total `(casefold, original value)` ordering with a regression
  assertion.
- Two fresh real generations in separate processes produced identical SHA-256
  and byte counts for all four artifacts. Their accepted aggregate receipt hash
  is `4516ba05a63b3d0f70da82453d85a9e7eef97e1ff4890222e9be073149ea9c15`.

Focused tests currently pass: 6/6 corpus tests, 4/4 schema tests, and the module
is explicitly registered in the main lane.

Audit every P2-plan safeguard, especially whether schema/semantic validation is
truly fail closed, whether the local entity/relationship record content stays
source-native without implicit resolution, whether the receipt proves exact
conservation and isolation, and whether the determinism evidence is sufficient
to close P2-CORPUS.
