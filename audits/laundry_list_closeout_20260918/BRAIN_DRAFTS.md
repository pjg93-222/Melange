# Brain update drafts -- for Paul to apply and commit (or direct the session to, per D-006)

## STATE.md -- Current position (new bullet)
- LAUNDRY-LIST HANDOFF (2026-07-16) CLOSED OUT 2026-09-19 (worktree unfinished-work-handoff-a3bbad, read-only; nothing edited, regenerated or committed). The handoff's "NOTHING has been applied" is SUPERSEDED: the lane landed the same night as 391a4a8b5, merged e58a807da; record AUDIT_COMPLETION_REPORT_2026-07-16.md. Item 1 (bands/crown) is further superseded by D-031. Verified landed: deselect (all paths incl. the ?coal= view, logic-level), max route (Kennedy 19-21% of routes vs ~99%; legacy algorithm still yields one set for 98.9% of seeds on today's data), CU Tax Status on every surface, original-cosponsor collapse, domain placements except H.R.3009/117. OPEN and measured: press desk gap (291 refresh rows reach rank, never the desk); reference layer (54.3% of 36,148 contexts unscored, speaker-tag bleed, 749 roster-artefact mentions, 170 identical windows, no model recorded on 19,537 of 19,793 cache rows); Tim Scott +6.24 MBL sponsor weight missing (only member affected); 120-char dedup key (490 rows in false groups); PERS parity drift (no-stance 0.45 vs Ally 0.40 under an "Ally parity" ratification); max-route hub core (Hill/Emmer/Barr in 64-89% of routes); sna_compact.json orphan. Packet: audits/laundry_list_closeout_20260918/ (LEDGER.md, FINDINGS.md, DECISIONS_FOR_PAUL.md, receipts per lane), UNTRACKED in that worktree. The July companion results JSON and the old worktree session directory no longer exist.
- COMMIT GAP ON MAIN (found 2026-09-19): main's fec/run_pipeline.py:123 names build_vote_category.py and main's fec/members/member_reference_layer.py:245 imports members.reference_cache; both files are untracked and exist only in the LIVE tree (149 modified + 349 untracked paths there; part of the modified count is CRLF-only). main's chain cannot resolve and main cannot run the reference layer.
- AUDIT vs LIVE DATA 2026-09-19 (main's audit code): 544 passed / 15 FAILED, exit 1. Kernel from a worktree is structurally invalid for 35 sub-suites (see DEADENDS draft).

## DECISIONS.md -- status-line corrections (no new decision)
- D-031 Status: replace "chain not yet run, so the desk still serves the pre-change honors generation" with "PUBLISHED by the 2026-09-18 chain (~02:36 local): overall Champion = 13 == honors_meta.overall_board.top13; Champion 0 in the three defend fields, Defender 0 in the 15 offence fields; field ladder Champion 225 / Ally 459 / Highly Persuadable 224 (laneC q7_d031_labels.txt)."
- D-034 Status: replace "chain not yet run, so rank movement is unmeasured" with "PUBLISHED by the 2026-09-18 chain: the desk payload carries exactly 895 'also posted on' notes, equal to an independent recomputation (laneA r7). Rank movement attributable to D-034 is still unmeasured. Open defect: the cross-post key truncates at 120 characters (490 rows in false duplicate groups), which makes the documented rollback CROSSPOST_DEDUP=1 unsafe until fixed."

## DEADENDS.md -- new entry (draft)
## DE-0XX -- Verifying main by running fec/tests/run_tests.py from a worktree with MONEYBALL_ROOT set
Date: 2026-09-19
Approach: set MONEYBALL_ROOT to the live tree and run the kernel from a clean worktree at main's tip, so that code is main and data is live.
Failure mode: 204 passed / 35 FAILED, none of it evidence about main. run_tests.py:8 resolves FEC from __file__ and never consults paths.py, so the sub-suite walk and PYTHONPATH pin to the worktree, and suites such as tests/legislation/test_bill_collision_guards.py open the worktree's empty data plane (FileNotFoundError on data\legislation\bill_directions.csv). The environment variable did propagate; the in-process checks that go through paths.py all passed. audit_full.py does honour paths.py and is valid from a worktree.
Would reconsider if: run_tests.py and the sub-suites resolve their data root through paths.py.
Second-order lesson: the 2026-07-16 completion report's "tests now honor MONEYBALL_ROOT" is true for the in-process checks only.

## Handoff digest corrections (for whoever next reads HANDOFF_LAUNDRY_LIST_2026-07-16.md)
- audit_full.py exit code is no longer always 0: it exits 1 on failure.
# ADDENDUM 2026-09-19 (after Paul's "GO on all your recommendations") -- drafts, IDs to be assigned

## STATE.md -- replace the close-out bullet's last sentences with
- ... BUILT 2026-09-19 on branch claude/unfinished-work-handoff-a3bbad, NOT LANDED (main still 776ce0d3a): reference-layer admission filters 105907a59; press release identity df707df0a; whole-statement cross-post key 07576dfc6; sponsor rows from the archive's Sponsor column 7c24547e2 (+ live hook patch); Max-route hub-core disclosure bfb40573b; desk reads the engine's press stream b02296ae8. Each ships behind a revert dial and with a read-only prediction on live data; kernel / chain / rank delta / audit were NOT run (impossible from a worktree; main's chain cannot resolve) and are owed in the LIVE tree at landing. Landing procedure: audits/laundry_list_closeout_20260918/FIXES_AND_LANDING.md. One blocker: .claude/skills/moneyball-config-and-flags/SKILL.md is dirty in LIVE and will stop the merge until committed. N5 (desk -> routing audit) WITHDRAWN on evidence. Open rulings N12-N15.

## DECISIONS.md -- new entries
## D-0XX -- The reference layer admits only real references
Date: 2026-09-19
Status: BUILT 105907a59 on claude/unfinished-work-handoff-a3bbad; not landed.
Decision: a PRESS headline counts only off the speaker's own .house.gov/.senate.gov domain; a roll-call roster or signature block is not a reference (>=10 roster surnames and >=35% surname tokens); windows identical after whitespace normalisation count once per edge in n_scored and the tone tallies, while n_raw keeps every mention. Q11 ("reposts count") is a STANCE ruling and does not extend to reference edges.
Context: Paul, 2026-09-19: "GO on all your recommendations" (packet DECISIONS R1 a/b/c, where c was flagged as his call and recommended count-once).
Rationale: measured on the shipped artifact, re-derived 8,017/8,017 edges: 8 third-party PRESS mentions incl. the 5-edge Magaziner cluster; 749 roster mentions at graded precision 40/40 and 0/40 missed; 53 drawn edges standing on copies alone. All dials off reproduces the artifact exactly.
Reversal condition: REF_PRESS_OWN_DOMAIN / REF_ROSTER_FILTER / REF_IDENTICAL_ONCE = 0, or Paul rules that reposts count on reference edges too.

## D-0XX -- One press release is one release only when key, date and title agree
Date: 2026-09-19
Status: BUILT df707df0a; not landed.
Decision: press_stream keys ingest on the release slug (path aliases and the Drupal '-0' marker folded), but the key only NOMINATES a pair; rows merge only when date and title agree. canonical_url is unchanged.
Context: Paul, 2026-09-19 GO (packet A5).
Rationale: 11 live pairs are one release under two URL forms; the twelfth candidate, Vargas, is one headline on 2022-09-30 and again on 2023-01-30 -- two releases -- and would have been silently merged. Folding the rules into canonical_url drops the press router's api-target basis from 627 hits to 93.
Reversal condition: PRESS_URL_CANON=1.

## D-0XX -- The cross-post duplicate key is the whole statement
Date: 2026-09-19
Status: BUILT 07576dfc6 (desk sites) + live hook patch (engine site); not landed.
Decision: media_rules.crosspost_key keys duplicates on the full normalised text; normalized_text keeps its 120-character truncation because it is the tweet_stance_final join key. CROSSPOST_DEDUP stays 0 (D-034).
Rationale: 445 of 1,434 groups were false prefix collisions; at CROSSPOST_DEDUP=0 the same 5,722 rows score under either key; 298 desk notes were wrong; D-034's own rollback would have dropped 289 rows that are not duplicates.
Reversal condition: CROSSPOST_KEY_CHARS=120.

## D-0XX -- The archive's Sponsor column mints the sponsor rows it names but never rowed
Date: 2026-09-19
Status: helper + tests BUILT 7c24547e2; producer hook is a patch against the LIVE bytes; not landed. RANK-MOVING when landed.
Decision: where the bill-level Sponsor resolves, fail-closed through the producer's own Resolver, to a roster member with no row in a (bill, Congress, category) cell, one sponsor-role row is injected before the row loop and judged by every unchanged gate.
Rationale: Tim Scott / Member Business Lending was published at 10.76 with +6.24 missing (58%); he is the only member affected; not a regression.
Reversal condition: LEG_SPONSOR_FROM_COLUMN=0.

## D-0XX -- The member desk reads the engine's press stream; the sheet wins the overlap
Date: 2026-09-19
Status: BUILT b02296ae8; not landed.
Decision: desk press rows = every 'Press Release Articles' row, plus every engine tone row the sheet lacks (matched on release key AND day). For a release both hold, the sheet's bytes render.
Rationale: 291 engine rows (221 scoring) never reached the desk. The sheet wins because the two sources disagree on the displayed stance of 57 shared releases and the graded score of 1,207, and a displayed press stance is Paul's to move (open ruling N14). Measured: +288 rows / 146 members, 0 removed, 0 changed.
Reversal condition: DESK_PRESS_SOURCE=sheet, or Paul rules the CSV authoritative on the overlap.

## D-0XX -- Max route keeps its algorithm and discloses its hub core
Date: 2026-09-19
Status: BUILT bfb40573b; not landed.
Decision: the Max-route panel names the three members with the largest share of all viable routes on the current issue / network / dropout set, computed lazily and cached; closedCascadeRoute is untouched.
Rationale: Kennedy is fixed (19-21% of routes) but Hill / Emmer / Barr sit in 64-89% on every issue; the hubs are genuine, so disclosure beats redesign.
Reversal condition: SHOW_HUB_CORE=false, or Paul asks for a diversity penalty.

## DEADENDS.md -- new entries
## DE-0XX -- Pointing the member desk's bill list at the legislation routing audit
Date: 2026-09-19
Approach: make the desk read the routing audit's SELECTED rows, as the say-do gate does, to close the desk/matrix fork (627 workbook-only keys).
Failure mode: it would LOSE 377 desk rows across 194 members; 331 of them are adjudicated sidecar memberships (bank_anchor 139, primacy_act 117, registry_anchor 73) that the producer's frame never sees. The 627 were never hidden actions: 622 are a redundant plain-cosponsor twin the desk's own collapse already eats.
Would reconsider if: the sidecar lanes flow through the producer's frame, so the routing audit is a superset of what the desk shows.
Lesson: I recommended this before measuring it. Measure a recommendation's blast radius before it goes on a ruling sheet.

## DE-0XX -- A URL slug as a press release's identity
Date: 2026-09-19
Approach: merge tone rows whose URLs share a release slug (Drupal appends '-0' to a duplicate path).
Failure mode: Drupal appends '-0' whenever a NEW node reuses a title. Vargas's "House Passes ... Credit Union Board Modernization Act" exists for 2022-09-30 and again for 2023-01-30 (two Congresses). Slug-only merging silently drops a real release. The build lane reported the pair as "same title/date"; it was not.
Would reconsider if: never without the date and the title agreeing as well.
Lesson: an architect's census claim needs the same adversarial re-measurement as a scout's.
# APPLIED 2026-09-19 (appended)
These drafts were superseded by entries written to the Project Brain directly (direct-commit override, brain
D-006): decisions D-052..D-057, dead ends DE-037..DE-040, the published-status notes on D-031 and D-034, and the
STATE bullet "LAUNDRY-LIST CLOSE-OUT + LANDING". The brain holds the final wording (landed, not "built, not
landed"); this file is kept as the record of what was drafted before the landing.
