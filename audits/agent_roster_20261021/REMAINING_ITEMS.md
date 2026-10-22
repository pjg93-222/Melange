# Remaining items, 2026-10-21

Source: the "Remaining items" section of the approved plan `<local plan file, not published>`. State context is in `STATE_2026-10-21.md` in this folder. Every row was open as of 2026-10-21 except where the Status column says otherwise (P0 rows updated 2026-10-22).

## Legend

Owner letters:

- F = Fable overseer
- O = Opus manager
- S = Sonnet coder
- P = Paul (not AI-fixable)

The Owner column follows the plan's wording, so "O triage, S fix, F rules" is written as letters with the role in parentheses.

## P0: the daily pipeline is red (five consecutive FAILED runs)

Runs in `audits/congress_pipeline/`: 20261020T200207Z, 20261020T224638Z, 20261021T040051Z, 20261021T141759Z, 20261021T155707Z. Each failed at the first fault, so later faults may hide behind the last one.

| ID | Fault or item | Fix approach | Owner (F/O/S/P) | Gate | Status |
|---|---|---|---|---|---|
| P0-1 | Run 2026-10-20 20:02: admissions exit 1, `hr:8720` "complete evidence exceeds model envelope" (errors=1 fails run) | Fixed in 2ce09188d. The real cause was an invalid classifier category on `119:hr:10082`, not the envelope lines, which were holds. | E2E lane (chain session) | None stated | fixed on main, verified read-only 2026-10-21 |
| P0-2 | Run 2026-10-20 22:46: media exit 1, press PARTIAL cascaded to SKIPPED_AFTER_FAILURE | DE-043 Fix A (media before repository) moved media first, so a partial press killed the whole chain. Cause now known: media all_intake FAIL (178 errors, missing houselive and axe WAVs). D-273 says FAIL is correct. Blocked until the P7/P8 audio restore. | E2E lane (chain session) | None stated | fixed on main, verified read-only 2026-10-21 |
| P0-3 | Run 2026-10-21 04:00: competitiveness input `cook_house_csv` changed; chain `ROLLBACK_FAILED` left `rank_honors/active.json` and `workbook_publications.json` modified (ca9bb6751 followed) | Cook PVI CRLF provenance restored in 734cd7b24 and 24f947a7c. The pin matches, so no re-pin is needed. | E2E lane (chain session) | None stated | fixed on main, verified read-only 2026-10-21 |
| P0-4 | Run 2026-10-21 14:17: `make_member_desk`, district brief roster differs, missing=3 extras=1 | Fixed in 256c60c21: briefs keyed to 533, with a withhold test. | E2E lane (chain session) | None stated | fixed on main, verified read-only 2026-10-21 |
| P0-5 | Run 2026-10-21 15:57: `tier_util.py:549` "no primacy factor for 'Aisha Wahab'" | Aisha Wahab is a California state senator, not a member. Cause: a roster-535 circular contract in build_primacy_surfaces (desk step ran before primacy_factors.py and per_area_grade.py rebuilt for 535). Fixed in e347e0bb6 and e47a232fe on main. | E2E lane (chain session) | None stated | fixed on main, verified read-only 2026-10-21 |
| P0-6 | Briefs-v3 copy of `make_member_desk.py` (codex/member-briefs-v3-resume-20261021 @ 0bedf256c) in the working tree writes tier=None in the analytic pass; `fec/lobbying/champions_v2.py:675-677` `_integer` rejects a non-integer tier and would halt the chain. | Chain session's Opus reviewer confirmed. The working-tree copy was byte-identical to that branch @ 0bedf256c and was written into the live tree at 13:41 CDT on 2026-10-21, after attempt 5. `make_member_desk.py:2750` skips the board unconditionally when `--analytic-inputs-only` is set, and `:2868-2870` write tier=None. Attempt 5 reached `legislative_press_tiers` because it ran before the copy landed. Paul ruled to set the copy aside: saved under `audits/e2e_20261020/before_attempt6/set_aside/`, HEAD's copy restored, so attempts 6 and 7 ran HEAD's desk code. | E2E lane | None stated | confirmed; copy set aside by Paul's ruling 2026-10-21; closed for the chain, open for the briefs-v3 lane to land properly |
| P0-7 | `workbook_publications.json` hand-repaired after attempt 3 ROLLBACK_FAILED (hash 1b9854fe vs pre-run 0ddb4059; pre-repair copy in `<local data dir>/e2e_20261021_repairs/`); no brain or memory record. | Record the repair in the brain and memory. | E2E lane / P | None stated | open: record it |

Attempts 6 and 7 (2026-10-21/22). Attempt 6 (`audits/congress_pipeline/20261021T225854Z`): all 7 congress steps PASS at 535; the chain refused to start at the 30 GB free-disk floor (14.3 GB free), nothing ran, and rollback restored. Attempt 7 (`20261022T012234Z`) FAILED at admissions: the Claude CLI account for the paid sentinel classifier hit its weekly limit (HTTP 429, resets 18:00 America/Chicago). A quota stop is FAIL by design (`refresh_sentinel_admissions.py:1149-1150`, `test_sentinel_classifier_budget.py:264`). No chain step ran and rollback was verified. Live main is ad1b23621, with F1, R1, R2 and a launch-time disk preflight. Next launch after 2026-10-22 18:00 CDT.

P0 acceptance. After each fix, re-run the pipeline in no-media mode (as `audits/e2e_20261020/attempt3-5_nomedia.*` did) until it passes, then one media run. Acceptance: `congress_pipeline_status.json` shows PASS, the rollback line is absent, and the membership sidecar is bound to the live repository hash.

## P1: reconcile public and local history, and the 2026-10-25 weekly

| ID | Fault or item | Fix approach | Owner (F/O/S/P) | Gate | Status |
|---|---|---|---|---|---|
| P1-1 | PR #23 is merged on public main only; its source commits and `fec/tests/stance/test_speech_channel_no_live_writes.py` are not on local main | Port PR #23 source commits (b552bc45f, 673ae62c7) to local main; confirm `test_speech_channel_no_live_writes.py` lands. | S, O (S ports, O reviews) | O review | open |
| P1-2 | PR #25 is OPEN; branch `d157-residual-20261020` (21 commits ahead) sits in worktree `.claude/worktrees/gallant-visvesvaraya-1c7276` | Land `d157-residual-20261020` (PR #25 content, 21 commits) on local main after review; then re-export so PR #25 can merge or be superseded. | O, F (O reviews, F gates) | F gate (public-facing) | open |
| P1-3 | The public-vs-local rule is unrecorded | Record the rule in the state doc: local main and origin/main are separate histories; "landed" means source commit on local main AND re-export merged on origin. | O (the plan assigns no owner; update_state is the manager function) | None stated | open |
| P1-4 | The 2026-10-25 weekly (first run on Wave 1 code) | Watch list only; no code until it runs (see the list below this table). | O, S, F (O reads logs Monday; S fixes clear failures; F rules on anything touching the lease or rollback) | F rules on lease or rollback changes | open |

Weekly watch list (2026-10-25). Expect: the press feed passes (pin plus Stage5Refused); `audits/weekly_refresh/<stamp>/<step>.log` appears; the run passes "prepare dashboard deployment" now that `DASHBOARD_PASSWORD_FILE` is set. On abort, the status must carry one of restored, verified, unhealable_drift, restore_failed, or skipped-no-lease.

## P2: finish and tidy the sweep

| ID | Fault or item | Fix approach | Owner (F/O/S/P) | Gate | Status |
|---|---|---|---|---|---|
| P2-1 | Surfaces folder half-swept: 11 unfixed files, review groups g7 to g12 never run | Re-run `folder-debug.js` for the 11 unfixed files and review groups g7 to g12 using `audits/fec_sweep_20261013/remaining_args.json`. | O, S, F (O launches, S fixes inside the workflow, F gate) | F gate | open |
| P2-2 | `.claude/workflows/folder-debug.js` has uncommitted edits (22+/13-) | Review and commit (they are process improvements, low risk) or discard. | O | O decides commit or discard | open |
| P2-3 | Working tree: 48 modified files | Assign each of the 48 modified files to a lane (briefs v3, holistic network, audit_postrefresh, research challengers, speech longform, tests), then commit per lane or revert. | O, F (O triage, F approves what lands) | F approves what lands | open |
| P2-4 | Line endings: 3 files LF in the index but CRLF in the working tree | Restore LF on the 3 index-LF files (`build_holistic_base.py`, `build_holistic_normalized.py`, `tests/research/test_mine_anchors_matcher.py`); leave the 21 index-CRLF files alone. | S | None stated | open |
| P2-5 | 326 untracked files, mostly `audits/` | Commit receipts that gates cite; ignore the rest via `.gitignore`. | O, P (O proposes list, P confirms) | P confirms the list | open |

## P3: Paul's decision backlog and Mentat

| ID | Fault or item | Fix approach | Owner (F/O/S/P) | Gate | Status |
|---|---|---|---|---|---|
| P3-1 | About 130 held items across the 16 sweep reports, plus 3 wave-1 decisions and the governance matrix | Not fixable by agents; fixable in how it is presented. Opus groups the held items into about ten themes and proposes one default per theme. Deliverable: `PAUL_DECISION_PACKET.md` with theme, affected files, recommended default, what changes if Paul says no. | O, F, P (O groups; F checks each default against change-control; P rules) | F checks defaults before they go to Paul | open |
| P3-2 | Mentat Banking residual +$251,029.90 | O writes a reconciliation brief against `R/report.R:2060-2090` (sub_id dedup by source_priority); S builds a read-only script that attributes the residual by sub_id. | O, S | No report publication until Paul reads it | open |
| P3-3 | Mentat S8/S8b console OPEN list | Two UI items are S work after Paul rules on the console-wide tokens. | S, P | Paul rules on the console-wide tokens | open |
| P3-4 | Mentat `TODO.md` and `HANDOFF_LAUNDRY_LIST_2026-07-16.md` are stale | O rewrites against the current tree (the Mentat merge line and the "UNCOMMITTED" claims are stale). Check whether `member_reference_layer.py:36` still hardcodes `claude-fable-5`. | O | None stated | open |

The ten P3 themes (detail in `PAUL_DECISION_PACKET.md`):

1. Non-atomic writes of receipts, ledgers and sealed keys.
2. Fail-open PASS: stale PASS receipts surviving a failure or exception.
3. Paid-API retry policy.
4. Resume semantics.
5. Sealed-input hash drift.
6. Roster and identity.
7. Measurement direction and definition.
8. Forecast and vintage.
9. Gate semantics.
10. Ops.
