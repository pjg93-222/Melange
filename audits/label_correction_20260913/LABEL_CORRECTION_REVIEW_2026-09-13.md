# Label correction review — 2026-09-13

The previous implementation changed the member table unnecessarily, introduced an independent behavioral-action ranking, and let a broadly positive action balance label almost the entire roster persuadable. It also used percentile thresholds on a two-person negative cohort, producing zero members in the stronger opposition bands.

The correction restores the five-column member table and uses authoritative primacy rank for overall label bands and tier sorting, including when a subfield is selected. Champion remains a table stance. There is one overall order; evidence-based opposition rules can cap a member's label without changing that order.

## Classification

Generation: `2d966e49989f882a6b07810f`; policy: `overall_primacy_standing_v2`.

Champion remains the existing 13-member crown. Positive bands require supportive observed actions and use primacy cutoffs: Ally 15%, Highly Persuadable 20%, Persuadable 50%, Lean Persuadable 75%. Low-ranked observed members without an applicable opposition classification are Uncommitted. Neutral-only and missing records retain explicit neutral/missing states.

Core adverse evidence requires a negative recorded action and a CU-adverse beneficiary/tensor direction. Legislative sponsorship or original cosponsorship on at least two distinct core adverse measures spanning at least two Congresses produces Opponent. Two core leadership measures within one Congress produce Highly Skeptical; two core adverse measures or a core adverse sponsorship produce Skeptic. Other qualifying negative records can produce Lean Skeptic. A single original cosponsorship does not automatically override high primacy. Shared-benefit category negatives do not by themselves trigger the severe core-opposition rules.

Peter Welch (primacy 529), Richard Durbin (532), and Roger Marshall (531) each classify as Opponent through repeated core adverse legislative leadership across Congresses. These are evidence-based outcomes, not name overrides. Typed measures, Congresses, action identifiers, and classification reasons are retained in the records.

Counts: Champion 13; Ally 66; Highly Persuadable 27; Persuadable 160; Lean Persuadable 125; Uncommitted 101; Lean Skeptic 29; Skeptic 6; Highly Skeptical 1; Opponent 5.

## Validation

`candidate_receipt.json` records a passing independent reconstruction audit. `semantic_review.json` verifies all 533 overall ranks follow primacy, the authoritative order and tier memberships are unchanged from the refreshed baseline, all 9,594 subfield records are unchanged, and no member below primacy 399 has a positive catchall label.

`tests/receipt.json` records passing targeted classification, independent-audit, workbook, dashboard, member-table, publication, and primacy suites. Member-table tests include Node-based rendering and sorting checks. Alias idempotency and concurrent-edit rejection were checked with a standard-library runner; the bundled runtime used for those checks did not provide pytest. All 12 table behavior checks also passed against the actual generated HTML (`shipped_table_tests.log`).

## Completed publication

Publication passed in `activation_20260913T050925Z/receipt.json`. The user approved rebuilding the five existing industry pages needed by the combined app. The interrupted concurrent source refresh had also left the derived industry CU board and analytical workbook cells stale; their existing producers synchronized those dependencies to the reviewed authorities. No scoring, ranking, primacy-factor, classification, or evidence-source input changed during completion.

`published_projection_receipt.json` verifies the actual local app HTTP response, standalone and combined page payloads, exact published-file hashes, the three named Opponent cases, all 9,594 unchanged subfield records relative to the reviewed refreshed baseline, and the unchanged authoritative primacy order. Differences from the older pre-refresh dashboard are explicitly recorded rather than described as label-only changes.

The workbook audit confirms 26 original worksheets retain byte-identical cell blocks. Changes in the other four analytical worksheets are confined to the artifact-authored plan: Rank & Allocation 3 cells, Category Stance 30, Blended Model 273, and Coalition Profiles 9. All 533 scores and ranks passed the workbook recalculation check. The three recognition views match the reviewed generation; recognition previews and analytical before/after previews were visually inspected.

The family ZIP is 5,288,690 bytes. Both all-in-one copies are 14,289,923 bytes, below the existing 14 MiB limit. Lossless DEFLATE recompression retained the exact extracted HTML. ZIP CRCs and extracted bytes were verified against the delivered files.

Browser attachment timed out in both available browser routes. Verification used generated-HTML behavior tests and the actual served HTTP payload; no browser screenshot review is claimed.
