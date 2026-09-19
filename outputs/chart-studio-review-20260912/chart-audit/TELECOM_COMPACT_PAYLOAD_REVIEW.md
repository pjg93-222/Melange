# Telecom compact payload compatibility review

The failed final index build was caused by a missing date field in the published compact payload. It was not an amount mismatch.

Independent full comparison (`telecom-compact-payload-audit.py`, receipt in the adjacent JSON file) checked all **506,017 distinct payload source IDs** against the fingerprint-verified accepted source snapshot. Every payload row omits the date key. There are no duplicate IDs, missing source IDs, or discrepancies in amount cents, normalized contributor name, committee ID, source-date-derived election cycle, or cycle label.

| Election cycle | Published included receipts |
| --- | ---: |
| 2021–2022 | $12,463,873.75 |
| 2023–2024 | $17,978,153.89 |
| 2025–2026 | $7,256,093.45 |
| Total | $37,698,121.09 |

The pinned payload declares `metadata.payload_compaction.mode = formula_fact_required_fields`. Its explicit 19-field `raw_fields` list excludes date. It records a full source payload SHA of `ceb1988527e588356d1a7d44e506a3a2095b82ddf2400ba630e9a17d60d6ee2b`. The current `prepare_workbook_payload.py` implements an analogous projection that excludes dates, although its newer metadata field names differ.

The earlier separate full-universe comparison proved that all **808,066 original financial IDs** remain identical in the recovered Telecom source, including rows omitted from the compact report. It checked source ID, amount, contributor, committee and exact calendar date; there were no additions, deletions or conflicting financial copies. Its 808,414 observations include 348 agreeing repeated query copies. This is stronger than checking published totals alone.

Lineage:

- Original published DB SHA: `34ef41793b3ab4c970e2d913ea7b42d50766b6c8f1430b40adbd9b0f8bd06d15`.
- Accepted snapshot SHA: `87027a8ea9eec4149ce67ca94192869e96670c675318f2948b8c15227474d447`.
- Current recovered DB SHA: `44148eb4f504a8fe723dcb41b7a7b79db7a556d70758ced206b056316d1628cb`.
- Compact payload SHA: `f37e976021a265f30bfa191e66de344bb68f7cddcc08ec1023aa82a0265c9bd6`.

The reviewed adapter requires declared date omission, an absent row date key, and a complete verified source-universe proof. It obtains the date from the preserved source and requires its election cycle to match the compact payload. It continues checking amount, contributor and committee identity. Present but null, blank or conflicting dates still fail. All 21 backend tests passed, including the five new compact-schema regressions.

This establishes compatibility and receipt reconciliation. It does not certify published receipts as unique original giving or remove the separate provisional status of the original-giving accounting basis.
