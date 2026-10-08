# Claude Opus 5 adversarial review — automated staffer/lobbyist acquisition

## Role and scope

Act as a fresh read-only adversarial reviewer. Do not edit files, browse, or promote evidence. Review the latest automated acquisition generation and its compatibility with the existing staffer-network mathematics and fail-closed canonical gates.

## Required inputs

1. `audits/staffer_network/full_profile_acquisition_cycle_current.json`
2. `audits/staffer_network/rapid_public_profile_continuous_20260901/incremental_public_profile_pipeline_receipt.json`
3. `audits/staffer_network/rapid_structured_profile_evidence_20260901_current/rapid_structured_profile_evidence_receipt.json`
4. The latest `audits/staffer_network/incremental_public_fact_candidates_generation_*/incremental_public_fact_candidates_receipt.json`
5. `audits/staffer_network/run_full_profile_acquisition_cycle.py`
6. `audits/staffer_network/run_incremental_public_profile_pipeline.py`
7. `audits/staffer_network/build_incremental_public_fact_candidates.py`
8. `audits/staffer_network/consolidate_rapid_structured_profile_evidence.py`
9. `STAFFER_NETWORK_EXPANSION_DESIGN_20260830.md`, especially sections 0A, 0.1, 0.3, and 8
10. `STAFFER_NETWORK_METRICS_20260830.md`, especially the connectedness, eigenvector, composite-influence, and temporal rows

## Reconciled generation facts

- Cycle: `profile-acquisition-20260901T034753Z`
- Public URLs: 2,300 discovered; 1,863 captured; 56 fetch errors; 122 HTTP errors; 259 skips
- Public candidate corpus: 1,442 people; 833 with spans; 1,993 spans; 28,548 employment-bearing lines; 30,208 education-bearing lines
- Structured corpus: 60 people; 404 employment episodes; 94 education episodes
- Canonical identity promotions: 0
- Canonical employment promotions: 0
- Complete-lifetime employment assertions: 0
- Capture evidence SHA-256: `c055221216b62f6aec5252ea38bd34db30904ce3269d42b6a1c4dd4b2d44fd82`
- Candidate evidence SHA-256: `2c2da2f50c6504ed87e10f35ead66ff3b61bb0372d2dca8a63a5ed3dca133b196`
- Structured evidence SHA-256: `82470cfadcedb0177e5abd7a6b076b822516693a27aec41c30e813d63c6e4862`

## Required adjudication

Return `PASS`, `PASS_WITH_FINDINGS`, or `FAIL` for each item:

1. Receipt composition and hash/count conservation.
2. Incremental/checkpoint/locking correctness, including failure and overlap behavior.
3. Whether candidate-only parsing can accidentally promote identity, employment dates, a lifetime-completeness assertion, a temporal edge, or a composite influence score.
4. Whether the new corpus is honestly characterized: distinguish URL capture, unstructured candidate spans, structured episodes, identity adjudication, complete employment histories, and production-ready temporal facts.
5. Compatibility with edge weighting, PageRank connectedness, component-local eigenvector diagnostics, bridging metrics, co-tenure, and revolving-door scoring. Re-derive enough of the stated mathematics to identify double counting, invalid normalization, directed/undirected mistakes, isolate leakage, component-comparability errors, or temporal use of undated evidence.
6. Whether the design/metrics text should change now, and exact blocking versus nonblocking findings.

## Output contract

Write a concise Markdown review with:

- overall verdict;
- a severity-ordered findings table with file/line references;
- independently recomputed counts/hashes where practical;
- explicit statement that data volume is not lifetime-history completeness;
- exact remediation for every blocking finding;
- a final `READY_FOR_IMPLEMENTATION`, `IMPLEMENTATION_PARTIAL`, or `NOT_READY` decision, with scope.

Do not weaken gates to obtain a pass. A pass for acquisition mechanics must not be described as corpus completeness or authorization for temporal graph publication.
