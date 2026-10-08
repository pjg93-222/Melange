# Fable P2 residual-closure verification

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

Act as a fresh read-only adversarial reviewer. Return `PASS`, `REVISE`, or
`BLOCK` with findings and R1–R6 dispositions in no more than 3,500 characters.
Do not edit files.

Read completely:

- `data/staffer_network/reviews/FABLE_P2_CLOSE_PLAN_REVIEW.md`
- `fec/staffer_network/schemas/legacy_source_native_record.schema.json`
- `fec/staffer_network/source_native_corpus.py`
- `fec/staffer_network/publication.py`
- `fec/tests/staffer_network/test_staffer_source_native_corpus.py`
- `fec/tests/staffer_network/test_staffer_publication.py`
- `fec/tests/staffer_network/test_staffer_schema.py`
- `audits/STAFFER_NETWORK_IMPLEMENTATION_DIAGNOSTIC_20260830.md`

Verification evidence:

- The sealed 5,773 production rows contain digit-only nonzero IDs, nonblank
  office/name/title strings, and boolean `featured`; no nulls or type drift.
- Targeted schema/corpus/publication tests: 21/21 pass.
- Full staffer discovery: 75/75 tests across 13 modules pass.
- Full upgraded local replay validated all 873,236 rows and returned an exact
  object match to
  `data/staffer_network/receipts/source_native_corpus_validation_20260830.json`,
  including corpus receipt SHA-256
  `3914df984044520ea782c529811283ad54c954b5ee31d98b10053373787604e2`.
- No production corpus or receipt file was rewritten. The 2026-08-29
  preservation test still passes.

Verify schema parity, public-safety and count checks, explicit publication
refusal, boss positive/dangling/malformed controls, semantic namespace defense,
diagnostic accuracy, byte preservation, and absence of gate movement.
