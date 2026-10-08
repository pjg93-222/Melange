# Fable C6 LDA identity-candidate corpus review

Act as the read-only adversarial reviewer for the candidate-only bridge from LDA lobbyists to existing staff/person sources. Inspect these files in `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`:

- `fec/staffer_network/lda_identity_candidates.py`
- `fec/staffer_network/schemas/lda_identity_candidate.schema.json`
- `fec/staffer_network/schemas/lda_identity_candidate_receipt.schema.json`
- the new candidate semantics in `fec/staffer_network/publication.py`
- `test_lda_identity_crosswalk_is_candidate_only_and_conserved` in `fec/tests/staffer_network/test_staffer_ingest_contracts.py`
- the upstream LDA source-native assertions and receipt code in `fec/staffer_network/lda_source_native_corpus.py`

Objective: exact normalized-name matches should produce useful review candidates across the Politico staff directory, Quorum legacy staff seed, and LittleSis persons/aliases, without a confidence score, identity assertion, canonical merge, or downstream gate opening. The candidate file is restricted machine-local. It must be deterministic, source-bound, count-conserved, collision-aware, and upstream-receipt-bound.

The focused synthetic test passes. Review for false claims, unsafe merging, normalization ambiguity, alias multiplication, ID/digest weaknesses, missing provenance/integrity checks, determinism failures, privacy leakage, and receipt overclaim. Decide whether the live candidate build may proceed after the reconciled LDA corpus is sealed.

Return exactly:

1. `VERDICT: PROCEED` or `VERDICT: STOP`.
2. Findings ordered by severity with file/line references.
3. Required fixes versus non-blocking hardening.
4. A concise acceptance table covering zero-merge, no confidence, exact-name-only, deterministic output, collision notation, upstream binding, conservation, and closed downstream gates.

Do not modify files and do not use network access.
