# R0a2b consolidation repair diagnostic

## Before / blockers

`consolidate_employment_corpus.py` previously accepted untrimmed identifiers, treated the literal `UNRESOLVED` sentinel as a person ID, merged unrelated sentinel rows, and silently omitted rows lacking a usable ID. It had no explicit input-row conservation record, did not expose normalized duplicate IDs, emitted a hardcoded `PASS` receipt, and had no committed receipt schema.

## After

Person IDs are trimmed; case-insensitive `UNRESOLVED` is reserved; conflicting top-level and nested IDs fail closed. Unidentified rows are preserved in deterministic `unidentified_input_rows.ndjson.gz` records with input/source ordinals, a source-row SHA-256, and a rejection reason. Receipt v2 records identified, unidentified, dropped, consumed, accounted, duplicate, uniqueness, and conservation evidence. `PASS` is emitted only when every processed identified person has employment status `COMPLETE` and there are no unidentified rows, normalized duplicate IDs, output duplicates, or conservation failures. The committed schema is checked with the repository validator, followed by cross-field semantic validation.

## Verification evidence

- Focused command: `python -m pytest audits/staffer_network/test_consolidate_employment_corpus.py -q` — **11 passed**.
- Staffer-network command: `python -m pytest audits/staffer_network -q` — **64 passed**.
- Focused coverage includes all-unresolved employment, missing IDs, literal/whitespace `UNRESOLVED`, whitespace-normalized duplicate IDs, row conservation, schema/semantic receipt validation, forged-`PASS` rejection, and primary/twin byte equality.
- The committed receipt schema passed `validate_schema_definition` (`schema-valid`).
- The focused credential-pattern scan was negative (`token-negative`).
- Python compilation completed successfully.

## Bound files

| File | SHA-256 |
|---|---|
| `audits/staffer_network/consolidate_employment_corpus.py` | `e276ad325e13aeef221462e6c143e8fa343d73c9286bdd02853b93194f110aa7` |
| `audits/staffer_network/test_consolidate_employment_corpus.py` | `efc88fdaf9cae975b7a4cc87e958dbe31d0a0d557a06c22fca9878faf86f38f9` |
| `fec/staffer_network/schemas/working_history_corpus_receipt.schema.json` | `f6ba663a7aba8d65e1c56ca7958f2877354be90dbd1ddb368be8947753683b4b` |
| `.gitignore` (narrow schema trackability exception) | `5216a00523e080a4f68668c59126133fc5074d50af8ee46201b95beeaaea3f7b` |

## Non-claims

This repair does not adjudicate or promote canonical identities, assert that rejected rows are distinct real people, fill employment-history gaps, certify source accuracy, or create a new production corpus run. Normalized duplicate IDs remain a receipt-level incompleteness condition rather than identity proof. The primary/twin equality evidence is synthetic regression evidence. `fec/staffer_network/employment_history.py` was not edited by this repair.
