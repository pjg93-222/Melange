# Laundry-list close-out -- findings (Phase 1)

2026-09-19. Read-only. Eight measurement lanes (laneA-E, F1-F3) plus two runs inside the published page.
Every number below is backed by a script + raw output in the named receipts directory. The sub-lanes could
not write report files, so this document is the consolidated report. Labels, categories and directions were
never judged: mechanical routing only.

State at measurement: no .pipeline_run.lock, no pipeline process, Excel closed, last full chain finished
2026-09-18 ~02:36 local. No artifact mtime moved during any lane (laneE fingerprint BEFORE == AFTER).

## A. Media and press accounting (laneA, F3) -- the half July never delivered

Every channel closes to zero unaccounted rows.
- Press engine: 2,679 in = 1,387 used + 816 neutral + 384 zero-intensity + 60 no-domain + 29 unrelated + 3 unresolved. (laneA r1)
- Social: Quorum Master 43,038 -> 729 true dups removed -> 42,309 = 13,362 member + 6,723 staffer + 22,224 excluded bucket; corpus 9,541 -> 9,502 = 5,709 scored + 2,994 zero-sign + 780 no-category + 19 link-only. (r4, r5)
- Own-source: speech 311 -> 172; hearing 790 -> 187 (529 non-gold excluded, ratified gold-only); interview 37 -> 25. All equal press_component_meta.json. (r5)
- Stance path (F3): 9,594 cells, 1,701 carry media, 0 cells lost; rebuilt signal == artifact signal (4,790), 0 disagreements. Dashboard labels == category_stance.json for 9,594 of 9,594 cells.
- Routing: zero alias failures in any channel (F3 f1, f2, f5).
- D-034 is live: the desk payload carries exactly 895 "also posted on" notes; independent recomputation = 895. (r7)

Defects and gaps
- A1 HIGH -- 291 press rows reach the ranking engine and never reach the desk; 221 of them score. The engine reads the two tone CSVs (incl. press_refresh_tone.csv); the desk reads workbook sheet 'Press Release Articles' (make_member_desk.py ~1648). No .py in LIVE fec writes that sheet (coordinator grep: 5 hits, all readers) -- it comes from the external R pipeline, so the desk shows a frozen press corpus. Independently corroborated: audit_full check "press refresh feed" FAILS with sources=False intake=False (laneE). (laneA r8, r9)
- A2 MED -- 'CU-Bank Competitive Dynamics' carries press-pillar weight 0.03 (raw col 18, inside E:W) and so reaches rank, but is absent from the stance categories and every dashboard column. 587 scored media items / 156 members land there and show in no stance cell (F3); laneA counts 1,058 desk evidence rows. It is a declared non-legislative 19th press category (code comments, test_bill_rules_routing.py), so this is a disclosure question, not a bug.
- A3 MED -- the cross-post dedup key truncates at 120 characters: 445 of 1,434 duplicate groups (490 rows) are false collisions (8,647 of 9,502 rows exceed 120 normalised chars). With CROSSPOST_DEDUP=0 no score is wrong, but up to 490 "also posted on" notes name the wrong statement; on the documented rollback (dial=1) those 490 rows would be dropped as duplicates of posts they are not. (r8)
- A4 LOW -- 'General Credit Union' is the largest media exclusion (782 scored items -> no stance cell, no pillar weight; 270 members). Ratified non-projection (media_rules.py); recorded in the artifact as applied_to_policy_domains=False; invisible on both surfaces.
- A5 LOW -- press releases ingested under two URL forms: 12 groups, 6 in use (Crapo, Marshall, 4 on americascreditunions.org). 6 double-count in the press pillar; only 1 reaches a real stance cell (Roger Marshall, Interchange). (r6, F3 f5)
- A6 LOW -- same-platform, same-date byte-identical social items: 69 keys (F3) / 75 groups (laneA, looser key). Ruling Q11/R9 ("reposts count") covers reposts; whether an exact same-day re-ingest is a repost is the owner's call.
- A7 LOW -- 'unrelated-zeroed' is unreachable in press_domain_routing_audit.json: set at build_media_blend.py ~371, overwritten at ~385 (845 = 816 + 29). Ledger label only.
- A8 LOW latent -- has_press = abs(x) > 1e-9 records a cell whose items cancel to zero as ABSENT media, the opposite of the rule used for legislation. 0 cells affected today; unmeasurable in principle. Social has no on-disk producer ledger.
- Ratification register: crosspost-off (Q11, R9, a0c45a709), hearing gold-only, General-CU non-projection, unverified-handle exclusion, billstatus routing, bluesky refusal, PRESS_THIRD_W=1.0 are RATIFIED. NO RECORD FOUND for: the Quorum cu_relevant gate (3,897 member rows), the bluesky CU-relevance gate, the 120-char truncation. AUTHORIZATION.md lives at audits/members_section_20260914/phase2/ @e043a1447, not on this branch.
- The media blend did not run in the last chain (chain log shows --from compute_pillars.py); blend artifacts are dated 09-17 and all six inputs_sha256 still match, so shipped values are consistent.

## B. Cross-reference layer (laneB, F2) -- open, and larger than July measured

Re-derivation matches the shipped artifact 8,017 of 8,017 edges (100%), so the counts below are exact.
- B1 HIGH -- unscored contexts: 19,618 of 36,148 (54.3%); the brain recorded 2,434 of 20,186 on 08-26. A new feed, PRESS_OFFICIAL_MENTION, adds 9,100 contexts of which 8,996 are unscored. C-SPAN: 5 of 507 scored (July 0 of 382). Only 3,562 edges clear the n_scored >= 2 drawing floor.
- B2 HIGH -- model provenance: 19,537 of 19,793 cache rows record no model; MODEL = 'claude-fable-5' (line 38) is only a fallback imputed at ~242; the 256 rows that record one say sonnet / claude-cli. The artifact still describes itself as Fable-valenced. The cache has no per-row timestamp.
- B3 HIGH -- speaker-tag bleed (wrong-speaker attribution). Detector hits: 249 windows / 126 shipped edges / 69 signed / 64 signed and drawn. Graded precision 40 of 40 (95% CI >= 91.2%). Recall probe: 6 of 40 UNFLAGGED interview windows are also bleeds (15%, CI 5.7-29.8%) = roughly 640-3,300 more windows. Mechanism proven: a single-token broadcast tag ends a turn only when the surname happens to be a roster surname ("SULLIVAN (voice-over):" accepted, "WALLACE (voice-over):" and the backtick form of O'DONNELL rejected). 7 of 40 hits are a different defect: whole printed documents (QFR headers, amendment lists) attributed to one speaker. Raskin -> Blumenthal still exists, now unsigned.
- B4 MED -- roster artefacts (new, not on the July list): roll-call rosters, cloture signature blocks and co-signer lists read as references. 749 mentions / 502 scored / 78 shipped edges / 72 signed / 77 drawn. Precision 40 of 40; recall probe 0 of 40 missed. Explains 'austin scott' 157 and 'vicente gonzalez' 120 in the unguarded top-20.
- B5 MED -- byte-identical windows counted more than once: 157 edges (July 152), 170 surplus windows; 53 drawn edges would fall below the floor if identical windows counted once. One FHLBNY tweet is counted four times (Torres -> Meeks).
- B6 LOW -- PRESS pass has no own-domain gate: 8 of 42 mentions are third-party (all americascreditunions.org); the Magaziner cluster is still exactly 5 false edges plus Warner -> Daines +1.00. All sit at n_scored=1: invisible on the network, visible on the desk (make_member_desk.py ~677 has no floor). The ratified rule (resolve_attribution_domain.py 45-47) is never called. The new POM feed has 0 violations.
- B7 LOW -- famous-namesake collision is small: 1 of 30 graded unguarded windows (3.3%, CI 0.1-17.2%).
- B8 -- member_reference_verify.csv is 74 days older than the artifact, capped at 500 rows (6.2% of edges), with the owner's grading column filled in 0 of 500.
- Exact support loss if detector hits were excluded: bleed -- 4 drawn edges lose all scored support, 21 drop below 2; roster -- 1 and 27. No SIGNED edge loses its only scored support under either.
- NOT MEASURED: whether the same missed host tags put host speech into the member-attributed interview rows that feed the desk interview footprint (95,078 rows) and the interview stance channel (25 used).

## C. Legislation residue (laneC, F1) -- see LEDGER rows 4a-4f
Only one item is materially open: Tim Scott's +6.24 missing MBL sponsor weight (3 cells, 1 member, not systematic, not a regression). Secondary: the desk reads append-only workbook role sheets that no production script writes (627 workbook-only keys, 258 archive-only).

## D. Engine residue (laneD)
- D1 -- PERS parity drift, STILL PRESENT and now explained. moneyball_core.py ~430: the no-stance price 0.45 carries the comment "USER-RATIFIED 2026-07-02: Ally parity -- silence never outranks a declared Ally", but Ally is 0.40 today, so silence (0.45) does outrank Ally. flip_model.py ~20 still names Ally as 0.45. The ratified VALUE and the ratified INTENT have separated. Binds at per_topic_flip.py ~74, where the no-stance key is ~60% of cells.
- D2 -- common random numbers are topic-invariant (seed inputs are SEED, iteration, member index; topic never enters). STILL PRESENT. Practical effect bounded by the 2026-07 MC-stability validation (100% seed-set overlap at MC=100 and SEEDs 1/13). Not re-flagged.
- D3 -- alphabetical first-wins tie-breaks in all three heaps. STILL PRESENT; only budget_frontier's marginals sit on the 0.05 grid and most are multiplied by continuous leverage, so ties are rare. Same validation bounds it.
- D4 -- Ted Budd seeding: CHANGED, symptom gone (first seed in 1 of 18 topics; 12 distinct first seeds).
- D5 -- electoral-leverage disclosure: the dashboard reads only budget_frontier.json, which is built with leverage ON; build_dashboard_bundle.py forwards base/knee/core/path and drops 'mode' and 'leverage', so the page has no field from which to disclose the weighting. budget_frontier_electoral.json has no surface reader.
- D6 -- vote_category_lean.json now HAS a chain producer (run_pipeline.py:123 build_vote_category.py --publish) and is 22.6 days newer than the newest archive; the vote-lean and culling audit checks would both pass statically, so the KNOWN_GATED_FAILURES pair is reviewable. audit_full.py's comment (~1765) still names the old orphan producer.

## E. Harness status (laneE)
- Audit (main's code, LIVE data): 544 passed, 15 FAILED, exit 1. Failures: integrity sub-audit "no output"; capacity-aware; interview DB receipt (stance_current=False); three sentinel checks "verified row has inadmissible role: sponsor"; pillar snapshot vintage 15d (stamped 2026-09-03); personal-texture precision/schema; personal-texture propagation (480 payload mismatches); press refresh feed (see A1); desk acts 653 vs 644 tags; staffer house_member_quarters missing; three repo-size sentinels (environmental). Caveat: main's audit code read artifacts built by the drifted LIVE code, so some failures may be code/data skew.
- Kernel from the worktree: 204 passed, 35 FAILED -- an invocation artefact, not evidence about main. run_tests.py:8 resolves FEC from __file__, so sub-suites open the worktree's empty data plane (FileNotFoundError on ...\data\legislation\bill_directions.csv). In-process kernel checks, which go through paths.py, all passed.

## X. Cross-cutting: main is not the production engine
- The LIVE tree has 149 modified + 349 untracked paths. Part of the 'modified' count is CRLF-only (F3); functional drift is proven in build_media_blend.py (51 lines), press_stance_stack.py (30), workbook_stance_views.py (4) and build_archive_legislative.py (LIVE emits routing statuses main cannot).
- Two chain-critical files are untracked and LIVE-only while main depends on them [V]: main's run_pipeline.py:123 names build_vote_category.py; main's member_reference_layer.py:245 imports members.reference_cache. main's chain cannot resolve, and main cannot run the reference layer.
## CORRECTIONS AND ADDENDA -- 2026-09-19 (appended; the text above is left as written)
- B3 mechanism corrected: the speaker-tag bleed is NOT caused by roster-surname gating. That was the first
  detector's own rule. The cause is the collector's turn regex (fec/members/fetch_interviews.py ~202), an
  ALL-CAPS-only character class anchored at line start, which rejects a backtick and any lower-case
  parenthetical. Size on the rows themselves: 5,835 of 153,576 INTERVIEW rows; 999 reference mentions
  mis-attributed today (measR1d receipts). See FIXES_AND_LANDING.md.
- A5 corrected: 11 pairs merge, not 12 -- the twelfth candidate (Vargas) is two different releases and is
  kept by the date/title guard. The press pillar moves for ONE member (Roger Marshall), not six: the other
  merged rows sit in General Credit Union, which carries no pillar weight.
- Section X corrected: "part of the 'modified' count is CRLF-only" is wrong. git's own status already
  ignores line endings, so all 149 modified paths in LIVE are real content changes; what F3 found is that
  a RAW byte diff over-reports, and that several files first listed as drifted are identical. The live-tree
  reconcile lane (2026-09-19) has the authoritative census.
- N5 withdrawn on evidence (measN5): pointing the desk at the routing audit would hide 331 adjudicated
  sidecar memberships. 622 of the 627 workbook-only keys are redundant twins the desk already collapses.
- New: the desk's press sheet and the engine's tone CSV disagree on the displayed stance of 57 shared
  releases and on the graded score of 1,207 (fixN1 receipts) -- ruling N14.