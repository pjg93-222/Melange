# LANDED -- 2026-09-19 (Paul: "land it")

## What is live
- main fast-forwarded 776ce0d3a -> 333cafbf3 in the LIVE tree (9 commits: the packet + six fixes).
- The two producers whose LIVE copies carry other lanes' uncommitted drift received their hooks in the working
  tree, byte-identical to the dry-run result (md5 in receipts):
    fec/legislation/build_archive_legislative.py   N4  (LEG_SPONSOR_FROM_COLUMN)
    fec/stance/build_media_blend.py                N2 engine key + A5 ingest ledger
  plus two new wiring suites and their two registration tokens in fec/tests/run_tests.py.
  These five paths are UNCOMMITTED ON PURPOSE: the hook hunks overlap the other lanes' drift, so they cannot be
  staged alone against HEAD. The live-tree reconcile lane commits them together with those files.
- The other lane's uncommitted change to .claude/skills/moneyball-config-and-flags/SKILL.md was set aside, the
  merge ran, and the change was put back by a byte-level three-way merge: git diff --stat still reads
  3 insertions / 1 deletion, and the re-applied hunk lines equal the original hunk lines (cmp clean).

## Verification protocol (all in the LIVE tree; receipts in this folder)
| Step | Before | After |
|------|--------|-------|
| Kernel tests | 237 passed, 2 FAILED | 244 passed, 2 FAILED -- the same two (missing backups\bill_directions.PRE-LEGFIX3.csv; test_make_staffer_network_html "unrecognised verdict"); all 7 new suites clean |
| Chain | -- | run_pipeline.py --from build_archive_legislative.py, 03:18 -> 03:49 (31 min), 65 steps OK; only the audit step non-zero |
| Rank delta | ranks_python.json E1F1F0E8... | 2 of 533 members moved, each by ONE place: Andrew Ogles 39 -> 38, Pete Sessions 38 -> 39 |
| Audit (LIVE's own audit code) | 563 passed, 5 FAILED | 561 passed, 7 FAILED -- the same five, plus two manifest sentinels for files this run regenerated |

Why the chain started at build_archive_legislative.py and not at step 1: it is the earliest step any landed
fix touches (N4), and it runs the reference-layer rebuild (R1), the media blend (A5, N2) and every surface (N1a,
R10). A run from step 1 would also have pulled in fresh collection intake (press engine feed, FEC money
refresh, sentinel ledger sync) and mixed unrelated movement into the rank delta.

## Every mover, explained
N4 gave Tim Scott the three sponsor rows the archive named but never rowed. In the live legislative pillar
(blend 0.7 agenda / 0.3 efficiency) his agenda rose 48.162 -> 50.034, and his efficiency -- the advancement
rate of his sponsored bills -- fell 0.21718 -> 0.21228, because none of the three bills advanced. Net pillar
0.92706 -> 0.92537, legislative percentile 0.97368 -> 0.96992 (two steps). He stays rank 1
(score 0.83196 -> 0.83027). Three other members' efficiency percentiles moved one step by displacement; one of
them, Andrew Ogles (leg 0.97180 -> 0.97368), passed Pete Sessions, who sat 1 place above him. That is the whole
rank delta. 452 members' press percentiles moved in the 5th decimal (media-blend date decay 09-17 -> 09-19, plus
A5 for Roger Marshall: -0.56701 -> -0.56568, rank 399 unchanged); no rank moved on press alone.
NOTE FOR PAUL: more complete evidence made the #1 member's legislative percentile slightly LOWER. That is the
pillar's designed behaviour (undelivered sponsorships dilute the advancement rate), not a defect of the hook.

## Each fix took effect (effect_check.txt)
- N4: legislation_routing_audit.json rows 10,820 -> 10,825; 5 rows carry evidence_source
  'archive-sponsor-column': Tim Scott S.762/117, S.3382/117, S.3992/118 SELECTED (+1.92, +1.92, +2.40);
  Anna Paulina Luna H.R.4686/118, H.R.6410/118 'duplicate-same-role' (her sentinel rows already count).
  archive_leg.json Tim Scott / Member Business Lending = 17.0 (was 10.76; predicted 17.00).
- A5: press_component_meta.json tone_ingest_dedup: 2,679 read, 11 duplicate-url-form collapsed,
  1 release-key conflict KEPT (Vargas), 2,668 returned.
- R1: member_references.json edges 8,017 -> 8,010, drawn 3,562 -> 3,482 (both exactly as predicted); excluded:
  8 third-party press, 749 roster windows, 191 identical repeats (predicted 192).
- N1a: member_desk_bundle.json press_source 'engine'; 291 engine rows appended; rows walked 3,992; unknown-member 6.
- N2: desk built with the whole-statement key; R10: the built dashboard carries the hub-core line.

## The two new audit reds
'A2b repo.data_legislation sentinels unchanged' (bank_anchor_reconciliation.json sha) and
'A2b repo.data_engine sentinels unchanged' (per_area_grade.json 1,105,448 -> 1,105,663 bytes) compare
data/system/system_manifest.json (generated 2026-09-18T17:35Z, not rewritten by this run) with files this run
legitimately regenerated -- per_area_grade.json grew because Tim Scott's area gained three rows. They clear when
the manifest is next rebuilt by its own lane. The generated manifest was not hand-edited.

## Incident worth keeping
The packet's .patch files were committed as text, so the merge checked them out in LIVE with CRLF conversion
and the LIVE copies stopped applying (the media-blend producer has MIXED line endings: 433 CR over 480 lines).
The hooks were applied from the original bytes instead, and the result was proved equal to the dry-run result
by md5 before it was copied in. This commit re-adds the four patches byte-exact under a '-text' attribute.

## Tracked files the chain rewrote (for the reconcile lane)
bill_beneficiary_tags.ndjson, data/members/bank_anchor_memberships.ndjson,
data/members/registry_anchor_memberships.ndjson, data/money/Moneyball_email.zip.
The set of git-status lines was identical before and after the chain (501 lines).

## Rollback
Dial flips, never a revert: REF_PRESS_OWN_DOMAIN=0, REF_ROSTER_FILTER=0, REF_IDENTICAL_ONCE=0,
PRESS_URL_CANON=1, CROSSPOST_KEY_CHARS=120, LEG_SPONSOR_FROM_COLUMN=0, DESK_PRESS_SOURCE=sheet, and the
template constant SHOW_HUB_CORE=false. Pre-landing copies: backups\member_references.PRE-LANDING-20260919.json;
ranks snapshot and artifact hashes in this folder.