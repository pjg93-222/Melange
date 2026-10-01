# Diagnostic adoption and publication status — September 20, 2026

**Adoption is committed; live publication is blocked.** Paul selected the diagnostic twice and authorized committing, regenerating and continuing the review. Implementation commit `fd740c4a0` was fast-forwarded to live main. The canonical pipeline was attempted and stopped at the interview intake gate before producing the new board.

## What is adopted

`CLASS_DOCK_PRESS_GRADE_ALL`, within-chamber seating, is now the default `PRIMACY_METHOD=diagnostic_v1`. No new member-specific overrides or ACU-label bonuses were introduced. Young Kim is 11/Tier 1; Daines 29/Tier 2; Barr is naturally 15/Tier 2 and remains 38/Tier 3 under the existing conduct cap. These are verified diagnostic placements, not a claim about the currently published generation.

The actual factor, grade and seating producers reproduced all 533 approved ranks, tiers and grade percentiles on the frozen inputs. There are 511 board-rank changes and 29 tier changes versus the old board. `legacy` reproduced both old factor/grade files byte-for-byte and all 533 old placements. The new press ledger reproduced all 483 approved member aggregates from 7,413 statement occurrences. Git checkout and importer round trips preserved its exact LF-normalized hash.

The focused primacy suites ran 89 tests with no failures and one skip. The explicit industry-valence suite passed 30 tests. Independent adversarial review approved the implementation after a Windows line-ending fix and additional identity validation.

## Publication blocker

The full pipeline stopped at `audit_collection.py` after 780.7 seconds. The receipt reports exactly one error: four repeated interview-turn groups. The prepared cleanup removes one redundant stored row per group, four rows and 65 word occurrences total, preserving each unique statement. A full database-clone rehearsal clears the interview duplicate gate while leaving the live database byte-identical. Optimized-Python tests confirm that the cleanup performs the deletion and rejects a changed source row even when assertions are disabled.

Owner approval remains pending under moneyball-change-control law 15: **“no dedup DELETE without Paul.”** Two repeated passages are verified repetitions in the source broadcasts; calling all four collection errors would be incorrect. See [the exact cleanup and policy choice](INTAKE_BLOCKER_REVIEW.md). No live deletion or intake bypass has occurred.

The live factor, grade, dashboard, member desk, industry tiers, reporting ranks and workbook remained byte-identical after the failed pipeline. Official reporting-rank changes: 0/533. The audit receipt itself records the rejected intake and is not a successful publication receipt.

## Broad verification

The full live kernel finished with **250 passed, 3 failed**. All three failures were rerun once to capture their precise causes:

- `test_bill_collision_guards`: missing historical fixture `backups/bill_directions.PRE-LEGFIX3.csv`. Documented before this promotion.
- `test_make_staffer_network_html`: the absent-offices fixture does not render its output file, then raises `FileNotFoundError`; the kernel reports an unrecognized verdict. The same suite failure is documented before this promotion.
- `test_per_area_board`: the still-installed old grade artifact lacks the four newly declared provenance inputs (beneficiary tags, sentinel admissions, press ledger and press receipt). This is an outstanding integration failure caused by blocked regeneration; the frozen diagnostic producer verification passes.

The earlier baseline is recorded in `audits/refresh_tick_20260919/COMPLETION_20260920.md` (250 passed, 2 failed). No failing test was relaxed.

The full-body audit finished with **549 passed, 19 failed**. One failure detects the old primacy artifact's K=.25 where the adopted default requires zero. Ten failures cover live data/provenance/freshness: own-source identities, interview stance receipt, hearing appendix alignment, pillar age, personal texture, audio partition, accepted press feed, vote provenance, champions threat-board freshness and cosponsor forecast freshness. Eight failures concern system-manifest agreement with current stores or repository metadata. These are unresolved publication checks; the four-row cleanup alone is not a promise of a clean full pipeline. Every failed check and the seven preserved artifact hashes are recorded in [verification_receipt.json](verification_receipt.json).

The final preservation check confirms all seven published artifacts remain byte-identical and official reporting ranks remain unchanged. The SQLite main-file bytes did change during verification: its size caught up with the earlier SQLite backup. A complete read-only comparison against that pre-cleanup backup found identical schemas and identical rowids and values in **all 15 tables**, including all 271,255 speech rows. Only five physical bytes differ from the backup, all in the SQLite header. This is consistent with checkpoint/header bookkeeping; no records were deleted or edited. The receipt distinguishes physical-file change from unchanged database content instead of claiming final database byte parity.

A clean publication is not claimed while intake is rejected, old generated files remain installed and the above gates fail.

## Review artifacts and remaining work

- [Top 50 with ACU references and grading space](TOP50_FOR_GRADING.md).
- [All 533 approved placements and changes](APPROVED_BOARD_533.md).
- [Boundary cases, component comparisons, chamber seating and remaining system risks](NEXT_REVIEW.md).
- [Project Brain update draft](PROJECT_BRAIN_DRAFT.md), prepared without modifying the external Brain.

The committed media ledger is a reviewed historical corpus, not a continuously refreshed classifier. Neutral/unclassified new items, crosspost dependence, association attribution, evidence depth, vote-direction provenance and chamber comparability remain explicit review topics. This promotion preserves the approved arithmetic and does not claim to resolve those measurement questions.

Local evidence is retained in `tmp/primacy_promotion_20260920/`; the frozen full audit and comparisons are in `tmp/codex_primacy_full_audit_20260920/`. Resume by resolving the four-row policy decision, completing the canonical regeneration, verifying all published surfaces and recording any new movement against the approved board.
