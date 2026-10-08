# GovInfo overlay integration and Melange theme receipt

Verified: 2026-09-08T20:32:10.201604+00:00

## Integration result

PASS. The reviewed overlay from `claude/govinfo-candidates-review-98f805` (`dbcf16cdc511b0399a76c7f3e619a7324c0f3eaf`) is integrated in the current `main` worktree and verified against the installed Sentinel Bill Ledger.

The reader, 22-row overlay, focused tests and runner registration were already present when this task started. Their behavior passed verification. The two missing historical review artifacts were imported byte-for-byte. The modern test runner retains all its other registrations. No merge, stash, reset, stage, or commit was needed.

The live workbook was already current: the receipt dated 2026-09-06T23:55:24Z, every bound source hash, the freshly rebuilt in-memory plan, and the installed XLSX agree. No workbook or durable-history rewrite was necessary.

## Live ledger effect

| Measure | Without overlay (same current inputs) | Live overlay |
|---|---:|---:|
| Pending discovery review | 14,031 | 14,009 |
| Discovery candidates | 18,579 | 18,579 |
| Verified memberships | 205 | 205 |
| Verified interaction rows | 210 | 210 |
| Ledger rows | 18,834 | 18,834 |

All 22 rows are discovery candidates with `Scoring Eligible = FALSE`. There are 14 exclusions, 6 holds, and 2 membership-only inclusions. These decisions do not create new accepted member edges or change scores. The frozen adjudication ledger wins collisions; this overlay has zero collisions. The without-overlay column is a counterfactual using the same current inputs, not a claim that this task changed the installed workbook.

## The 22 decisions

| Canonical bill | Live review status | Excel row | Scoring |
|---|---|---:|---|
| 119:hr:9623 | excluded_false_positive | 16375 | False |
| 119:hr:9857 | excluded_false_positive | 16423 | False |
| 119:hr:9879 | excluded_false_positive | 16424 | False |
| 119:hr:10013 | excluded_false_positive | 14487 | False |
| 119:hr:10081 | excluded_false_positive | 14489 | False |
| 119:hr:10124 | excluded_false_positive | 14491 | False |
| 119:s:5042 | excluded_false_positive | 17550 | False |
| 119:s:5090 | excluded_false_positive | 17556 | False |
| 119:s:5156 | excluded_false_positive | 17558 | False |
| 119:s:5183 | excluded_false_positive | 17560 | False |
| 119:s:5219 | excluded_false_positive | 17561 | False |
| 119:s:5238 | excluded_false_positive | 17562 | False |
| 119:s:5296 | excluded_false_positive | 17565 | False |
| 119:s:5354 | excluded_false_positive | 17569 | False |
| 119:hr:10017 | held_visible_non_scoring | 14488 | False |
| 119:hr:10184 | held_visible_non_scoring | 14492 | False |
| 119:hr:10242 | held_visible_non_scoring | 14495 | False |
| 119:s:5335 | held_visible_non_scoring | 17567 | False |
| 119:s:5358 | held_visible_non_scoring | 17570 | False |
| 119:sres:817 | held_visible_non_scoring | 18604 | False |
| 119:hr:10082 | included_membership_only_non_scoring | 14490 | False |
| 119:hr:10230 | included_membership_only_non_scoring | 14494 | False |

Full reasons and check-by-check evidence are in [ledger_verification.json](ledger_verification.json).

## Preservation

The starting worktree had 99 modified tracked files. This task changed only the two presentation stylesheets and added audit files. Backups of the touched stylesheets, relevant overlay files, history, workbook and receipt are under `before/`. The 95 other stable modified tracked files retain their starting hashes. Two additional files, `staffer-person-facts.js` and `staffer-route.js`, changed concurrently through another writer; this task did not write or revert either. See [preservation_verification.json](preservation_verification.json).

## Melange styling and debugging

The shared dashboard and embedded People styles use the observed America’s Credit Unions palette and Articulat CF / Freight Text Pro typography, with system fallbacks. Existing layout and data encodings remain in place. The locally served dashboard reads these source stylesheets directly; offline export HTML was not rebuilt.

Higgsfield was used for the palette contrast audit: purple/cream 11.97:1, purple/gold 6.75:1, purple/teal 7.05:1. Gold/cream was rejected for normal text at 1.77:1. The browser checks covered the Influence map, Members (533 records), Industry navigation, and People iframe styling. The People source inventory was still loading during observation, so this is not a claim of completed backend network readiness.

Fixed inherited heading-font specificity, the disclosure chevron encoding, and two controls retaining the previous theme. Member layout passed at 390 × 844 with no horizontal page overflow. No console errors were observed during these checks.

## Validation

- 46 focused supplemental-adjudication and sentinel workbook tests passed.
- 7 dashboard integration tests passed.
- 5 People-navigation tests passed.
- Live workbook rows and all recorded hash bindings passed read-only reconciliation.
- Scoped CSS whitespace/error check passed.

## Immutable hashes

- Overlay: `87164cca308258065e0736abbdf7688d68921cab4789533b19d1c0466d3a54f5`
- Frozen ledger: `47dacc6df80d6a190c40aea6ab2321fff061f462d63a5f9604172451cd4b101d`
- Verified history: `59c3807a2502b90ea472a9d0def3711d059ac6cdef6fa698ef578af9d4ecdde3`
- Installed workbook: `0d679cd2b737ed5fa7c006f78fdfddf31d371e62add8e142785cacb6c5e71867`

Historical `RECONCILIATION_RECEIPT_2026-09-06.md` retains its original proposed/not-applied wording as provenance. This receipt records the verified current integration state.
