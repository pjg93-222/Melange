# Opus 5 employment-consolidation terminal micro-review

Use Claude Opus 5 maximum effort, read-only. Inspect only:

- `audits/staffer_network/consolidate_employment_corpus.py`;
- `audits/staffer_network/test_consolidate_employment_corpus.py`;
- `fec/staffer_network/schemas/working_history_corpus_receipt.schema.json`;
- the receipt-validation helpers those files directly call; and
- `audits/staffer_network/R0A2B_CONSOLIDATION_REPAIR_DIAGNOSTIC_20260901.md`.

Pinned hashes:

- consolidator:
  `e276ad325e13aeef221462e6c143e8fa343d73c9286bdd02853b93194f110aa7`;
- tests:
  `efc88fdaf9cae975b7a4cc87e958dbe31d0a0d557a06c22fca9878faf86f38f9`;
- receipt schema:
  `f6ba663a7aba8d65e1c56ca7958f2877354be90dbd1ddb368be8947753683b4b`.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, and exact file/line `EVIDENCE`.

Re-test only these prior blocking routes:

1. consolidation attestations bind the complete merged/gapped episode set,
   not a stale input row;
2. status is evidence-derived and unresolved people cannot receive hardcoded
   `PASS`;
3. identity-less rows are never silently dropped or merged through a shared
   sentinel; they are deterministically conserved in a separate ledger;
4. input, emitted, duplicate, unidentified, people-level, and episode-level
   counts conserve exactly;
5. receipt schema plus semantic validation rejects contradictory or forged
   PASS values; and
6. primary/twin outputs are deterministic and byte-identical for identical
   inputs.

A consolidation PASS is code/receipt safety only. It does not assert actual
25,340-person completeness, adjudicate identities, or authorize promotion.
