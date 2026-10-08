# Extraction-to-display review — September 20, 2026

The review traced collection, checkpoint/resume, SQLite storage, shard merge, raw warehouse export, reconciliation, workbook staging/writing, and the UI query/display paths. Tests ran in isolated fixture directories; no production collection, published workbook replacement, historical-ID rewrite, or active-server restart was performed.

## Fixed defects

**Long numeric FEC identifiers lost precision during JSON parsing.** R's default JSON conversion parsed `4020420242001634771` as `4020420242001634816`. Adjacent IDs could collapse before duplicate detection/storage; keyset cursors and original-record links were exposed to the same problem. The new raw-JSON regression failed before the fix (`identity-before.log`).

`R/fec_api.R` now preserves large integer tokens as text at the API, local request-pool, and checkpoint boundaries. The browser API fallback in `R/fec_page.R` also parses raw response text without first rounding integer tokens in JavaScript. Its string-aware token handling leaves quoted memo text and decimal amounts intact. This changes representation, not attribution, exclusion, or transfer-version policies; no new application validation layer was added.

**Collection's explanatory text still described observed transfer reach as three hops.** It now distinguishes all reachable transfers in the saved evidence from the separate conditional allocation model's three-transfer bound. Missing coverage remains explicit.

## Isolated end-to-end replay

`mentat/tests/test_extraction_identity.R` exercises two adjacent long numeric source IDs, original-record and image IDs, an exact long cursor, an interruption after page one, resume, a second completed-run resume without refetch, raw-response hashes, storage, and tidy projections. The generated browser-fallback JavaScript runs against a fake fetch in Node, so both language boundaries are tested without live network traffic.

The preserved complete replay is `complete-replay/`. Actual application producers exported its raw warehouse and seven-sheet Data workbook; the shared reconciliation engine and UI query functions processed the same stored rows.

| Stage | Rows | Amount |
|---|---:|---:|
| Raw JSON source | 2 | $31.00 |
| SQLite collection | 2 | $31.00 |
| Compressed raw warehouse | 2 | $31.00 |
| Excel Contributions | 2 | $31.00 |
| Giving Facts | regrouped | $31.00 |
| Recipient Facts | regrouped | $31.00 |
| Location Facts | regrouped | $31.00 |
| Reconciliation / UI query | 2 | 3,100 cents |

Dollar delta across stages: **$0.00**. Both distinct IDs remain exact Excel text cells. Source/workbook hashes, rows, and totals are saved in `complete-replay/flow-ledger.json`; `ui-response.json` retains the UI's provenance and provisional-evidence wording. This synthetic test does not establish unique economic giving or a production dollar correction. Earlier fixture attempts are separate diagnostic artifacts, not the final replay.

The preserved Andy Barr source replay also passed again. Defend American Jobs activity reached through Fairshake remains **$106,708.00 for 2024** and **$7,170,138.40 for 2026**, counted once within each separate view. Company and Industry views are not additive. `barr-replay-ledger.json` preserves the source hash and direct-only/reachable comparison; these are the established algorithm deltas, not new dollar changes from the identifier fix.

## Verification

- 225 Python tests passed: 187 extraction/fanout/merge/warehouse/reconciliation/downstream/workbook/graph tests, 26 contribution data tests, and 12 query-store tests.
- Eight R suites passed: API collection, moving-count reconciliation, collection contracts, browser collection helpers, raw-column propagation, tidy staging, downstream system, and the new identity/resume replay.
- The existing downstream drawer browser test passed: signed amounts, source differences, missing coverage, direction switching, and expansion.
- Golden template check and focused whitespace checks run separately; see logs.

## Coverage limits

- This was a deterministic offline integration run. Live FEC availability, rate limits, changing inventories, and a full production report/Excel-finalization run were not tested.
- The newest Banking and Credit Unions merged databases inspected had no archived raw API response pages. `historical-sample.json` records the exact paths and zero-page coverage. No historical precision damage or production dollar delta can be quantified from that sample.
- A separate read-only sample of 50 PAC evidence cache envelopes contained 702 large source IDs, all already encoded as JSON strings and therefore unaffected by numeric-token rounding (`pac-cache-id-types.json`). The new bug regression exercises numeric encodings; no production loss is claimed from it.
- Already rounded stored IDs cannot be reconstructed from their rounded values. Existing stored-complete runs are not silently reset or rewritten; historical recovery needs original raw evidence or a controlled recollection and reconciliation.
- The browser API fallback is covered. Reading rows already parsed by the external FEC DataTables page cannot recover precision that the external page may already have lost. The default API collector avoids that dependency.
- The receipt replay deliberately has no candidate-spending source. Descendant spending, shared roots, cycles, signed transfers, missing frontiers, and Andy Barr behavior are covered by the downstream suites and the separate preserved-source review in `audits/mentat_downstream_system_20260920/`.

## Selected UI mockup and coordination

The user selected Higgsfield job `b6a2ab5e-3ef9-48e2-a728-604dc63468c0` as the exact visual target. Its native preview was shown and selection was relayed to the existing task **Finish PAC evidence map overlays**, which owns map interaction/layout files. That lane completed the reference composition and responsive version; the final desktop capture is the same **1168 x 880** as the selected image. Review caught an initial 86px height mismatch, which was corrected before final capture. Desktop and phone captures were inspected.

The map lane passed 22 browser scenarios, 17 unit tests, and real-geography/performance checks. It fixed accidental scroll capture, navigation animations overriding subsequent input, search/state focus loss, and enlargement/layout defects. No horizontal overflow was measured at desktop, intermediate, or phone sizes.

`outputs/pac-map-polish-20260921/verification.md` records the exact visual comparison and limits. The composition matches; literal pixel identity is not claimed. Real Census geometry and source-derived amounts replace generated illustration. Find, numeric zoom, contributor filtering, focus indicators, regional breadcrumb, and source disclosure remain functional. Final images are `selected-design-desktop.png` and `selected-design-mobile.png` in that same directory. No generated geographic pixels or invented financial amounts were installed.

Mockup: https://d8j0ntlcm91z4.cloudfront.net/user_3J1aVESwhbXLraSW8PtRFWWgpV2/hf_20260921_024245_b6a2ab5e-3ef9-48e2-a728-604dc63468c0.png
