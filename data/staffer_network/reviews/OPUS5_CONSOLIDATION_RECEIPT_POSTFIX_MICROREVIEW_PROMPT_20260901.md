# Opus 5 consolidation receipt post-fix review

Use Claude Opus 5 maximum effort, read-only. Inspect only
`consolidation_status` and `validate_receipt` in
`audits/staffer_network/consolidate_employment_corpus.py`, the receipt-forgery
tests in `audits/staffer_network/test_consolidate_employment_corpus.py`, and
the incomplete-reason enum in
`fec/staffer_network/schemas/working_history_corpus_receipt.schema.json`.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, and exact file/line `EVIDENCE`.

Re-test every prior receipt blocker: master input/accounted and identified/
consumed conservation must be re-derived; unidentified-reason counts must sum
to unidentified rows; duplicate counts must agree with duplicate/uniqueness
booleans; and the exact row-to-person bridge must enforce
`duplicate_identified_input_rows == consumed_identified_input_rows - processed_people`.
Confirm the exact residual identity
`residual_incomplete_rows == processed_people - complete_people`.
Also confirm empty input and unseen queue people prevent PASS, queue rows conserve
processed+unseen, and artifact/file inventory counts are checked. Adversarial
forgeries for inflated people and false residual counts must fail closed.
Measured evidence: 48 focused tests and 222 staffer tests plus 73 subtests pass.
This is receipt safety only, not actual corpus completeness.
