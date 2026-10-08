# Decisions for Paul -- laundry-list close-out

2026-09-19. Nothing below has been applied. Each item: what was measured, the options, a recommendation.
Reply with the item ids and your ruling (e.g. "N1 a, N4 b, R8 attic, R9 no"). A blank stays HOLD.
Evidence for every number: FINDINGS.md and the receipts directories beside this file.

## Closed -- no ruling needed
- R5 '+1' direction parse: unreachable today (0 rows; no writer emits into bill_directions.csv).
- R6 bill_key() type-blindness: 0 live collisions; Congress guards every outcome-changing lookup.
- R7 CU Tax Status column: already on every surface.
- R11 chain run for D-031 / D-034: already published by the 2026-09-18 chain (Champion = 13 = board top 13; 895 cross-post notes on the desk).
- Item 7 base branch: moot, everything is on main.
- Stance bands: closed by D-031. Not reopened.

## Worth your attention first
N1  PRESS DESK GAP (HIGH). 291 refresh press rows (221 scoring) move ranks but never appear on the desk: the desk reads the R-written 'Press Release Articles' sheet, the engine reads the tone CSVs. Your rule was "nothing hidden".
    a) desk reads the same tone CSVs as the engine (one source of truth)   b) a chain step appends refresh rows to the sheet   c) hold
    Recommend a. Display-only; ranks do not move.
R1  REFERENCE LAYER (HIGH). Measured: 54.3% of contexts unscored; speaker-tag bleed 249 flagged windows at 100% graded precision plus ~15% of UNFLAGGED interview windows; 749 roster/signature-block mentions read as references; 170 identical windows double-counted (53 drawn edges depend on them); 8 third-party press mentions (Magaziner cluster still 5 false edges).
    a) own-domain gate on the PRESS pass (rule already ratified, never called)      -- recommend GO
    b) exclude roster / signature-block windows (precision 40/40, missed 0/40)       -- recommend GO
    c) count byte-identical windows once in n_scored. Q11 "reposts count" was a STANCE ruling; does it extend to reference edges? -- your call; recommend count once
    d) speaker-tag bleed: fix the turn recogniser so any NAME: or NAME (voice-over): tag ends a turn, not only roster surnames. This is upstream of the reference layer and may also touch the interview footprint and interview stance channel -- recommend DESIGN FIRST (measure the upstream effect, then patch)
    Each behind a revert dial; --rebuild is $0 and cache-only; propagation needs a chain pass.
R2  REFERENCE LAYER MODEL. 19,537 of 19,793 cache rows record no model; 256 record sonnet / claude-cli; the artifact says Fable-valenced. Rule: which model scores from now on (your cost rule says Haiku 4.5), and record the model per row. Mixing raters in one cache needs either a full re-score or a per-row rater field.
R3  PAID --score PASS. 19,618 unscored contexts; 8,996 of them are the new PRESS_OFFICIAL_MENTION feed; C-SPAN 502 of 507 unscored. Options: a) score everything (cap $____, model ____)  b) score all except POM  c) rule that POM contexts are never scored and stop counting them as a gap  d) hold.
N4  TIM SCOTT SPONSOR ROWS. +6.24 MBL sponsor weight (58% of his published MBL cell) is missing because the archive has no sponsor-role row for S.3382/117, S.3992/118 and S.762/117-MBL, though its own Sponsor column names him on every row. He is the only member affected. Rank-moving, small.
    a) add three rows to manual_bill_evidence.csv (your data file)   b) producer synthesises a sponsor row from the archive's Sponsor column when the named sponsor is a current member with no row (covers 4 bills today, future-proof)   c) hold
    Recommend b, with a as the immediate fix if you want it today.
N6  PERS PARITY DRIFT. The 2026-07-02 ratification text reads "Ally parity -- silence never outranks a declared Ally", but Ally is 0.40 now and the no-stance price is 0.45; flip_model.py still says Ally = 0.45. Which moves?
    a) no-stance -> 0.40 (restores the ratified intent; moves flip / allocation artifacts, never ranks)   b) keep 0.45 and correct the three comments   c) hold
    No recommendation: it is your constant.

## Smaller rulings
N2  Dedup key truncated at 120 chars: 490 rows in false duplicate groups -- wrong "also posted on" notes today, silent drops if CROSSPOST_DEDUP is ever set back to 1. Fix = key on the full normalised text. Recommend GO (display-only at dial 0).
N3  'CU-Bank Competitive Dynamics': press weight 0.03 reaches rank; no stance column, no dashboard column; 587 scored items / 156 members. a) keep press-only and say so on the surfaces   b) give it a column   c) hold.
N5  Desk vs matrix bill fork: the desk reads append-only workbook role sheets no production script writes (627 workbook-only keys, 258 archive-only). Point the desk at the routing audit like the say-do gate? Recommend yes, after N4.
N7  Electoral-leverage disclosure: the frontier the dashboard shows is built with leverage ON, and the bundle drops the 'mode' and 'leverage' fields so the page cannot disclose it. a) forward the fields and caption the curve   b) build the dashboard frontier with LEV=0   c) hold.
A5  Press two-URL duplicates: 12 groups, 6 in use; one doubles into a stance cell (Marshall, Interchange), six double in the press pillar. Normalise URLs before keying? Recommend GO.
A6  69 same-platform same-day identical social items: repost (counts, per Q11) or re-ingest (drop)? Your call.
R4  Regenerate member_reference_verify.csv (free, no API). It is 74 days stale, capped at 500 rows, and graded 0 of 500. Recommend: only if you intend to grade it; otherwise retire it.
R8  sna_compact.json: producer fixed, still no reader. Attic the producer, or name a consumer.
R9  Re-click on the selected member toggles it off (the one July deselect idea that never landed). Everything else in deselect works. Optional.
R10 Max route hub core: Kennedy is fixed (19-21% of routes), but Hill / Emmer / Barr appear in 64-89% of routes on every issue.
    a) keep and disclose ("routes converge on the House Financial Services core")   b) per-recruit diversity penalty   c) lower the PageRank prior (0.75 + 0.25 PR)   d) hold. Recommend a or design-only: the hubs are genuine.
R12 Annotate HANDOFF_LAUNDRY_LIST_2026-07-16.md as SUPERSEDED with a pointer to this packet.
D6  Un-gate review: the two KNOWN_GATED_FAILURES (vote-lean, culling) now satisfy their conditions statically.

## Outside this lane -- you should know
N8  main is not runnable: run_pipeline.py:123 names build_vote_category.py and member_reference_layer.py:245 imports members.reference_cache -- both untracked and LIVE-only. LIVE has 149 modified + 349 untracked paths. A reconcile lane like today's Mentat one is the fix; a task chip was raised for it.
N9  Verification cannot be run from a worktree: run_tests.py sub-suites resolve the data root from __file__ (35 false failures). Until that routes through paths.py, "kernel green" can only be measured in the LIVE tree, which is dirty.
N10 Audit against LIVE data stands at 544 passed / 15 FAILED (list in FINDINGS section E), including the pillar snapshot vintage check (stamped 2026-09-03 -- open ruling S-5).
N11 Not measured: whether unrecognised host tags also put host speech into member-attributed interview rows on the desk.

## Packet note
This packet is untracked in the worktree (committing is gated). Say "commit the packet" to land it on branch
claude/unfinished-work-handoff-a3bbad, or it lives only in this worktree.
## STATUS AFTER "GO on all your recommendations" -- 2026-09-19 (appended)
BUILT and committed on the worktree branch, NOT yet landed (FIXES_AND_LANDING.md has the procedure):
  N1 a, R1 a/b/c, N4 b, N2, A5, R10 a, R12.
WITHDRAWN on evidence: N5 (it would hide 331 real memberships).
MEASURED, design delivered, nothing patched: R1 d -> becomes ruling N12.
STILL HOLD (the sheet made no recommendation): R2, R3, R4, N3, N6, N7, A6, R8, R9, D6.
NEW rulings: N12 speeches migration, N13 the Risch gold item, N14 sheet-vs-engine press stance (57 rows),
  N15 23 withdrawn memberships still on the desk, N16 (recorded) identical windows count once.
THE ONE DECISION THAT GATES EVERYTHING BUILT: land it? Landing = merge into main in the LIVE tree, apply two
  hook patches, run the media blend and the full chain (mutates every live artifact and the workbook, about
  25 minutes, ranks move for Tim Scott and marginally Roger Marshall). Say "land it" and I will run the
  procedure with the protocol and report the movers; or run it yourself from FIXES_AND_LANDING.md.
## LANDED -- 2026-09-19 (appended; supersedes "NOT yet landed" in the section above)
Paul: "land it". Everything marked BUILT above is live: main 776ce0d3a -> 333cafbf3 -> 109249aaa, and the two
producer hooks were committed by the live-tree reconcile lane as da32d3016. Protocol, rank movers (2 of 533, one
place each) and the two manifest-only audit reds: landing/LANDED.md. Recorded in the Project Brain as D-052..D-057
and DE-037..DE-040. Nothing else on this sheet has been acted on: R2, R3, R4, N3, N6, N7, A6, R8, R9, D6 remain
HOLD, and N12-N15 await your ruling.

## N12-N15 RESULTS -- 2026-09-19 (appended after Paul's "GO on N12 through N15, your recommendations")
The sheet had posed N13, N14 and N15 as questions, not recommendations, because they touch your labels. I treated
the GO as: build N12 test-first, measure N14 and N15 first, leave every label alone. Receipts: measN14, measN15,
fixN12, gradeN12.

N15  CLOSED -- NO DEFECT. All 23 are role-supersessions (archive says cosponsor, the official record says original
     cosponsor), none is a withdrawal, and the desk shows the official role on all 23. Across all 6,130 desk bill rows:
     0 display a withdrawn membership, 0 display a role that differs from the official one (negative control: the
     pre-filter ledger holds 2,715 violating rows, exactly the bundle's own removed-rows counter). My framing was wrong:
     the disposition string 'official-membership-withdrawn-or-role-superseded' lumps two cases; only 2 of 5,683 official
     facts are withdrawals at all.
     TIME BOMB FOUND WHILE LOOKING: official_membership_movements.json was last checked 2026-09-14T04:38Z and OM.load
     refuses it after 8 days. From 2026-09-22 04:38 UTC the desk build RAISES until that file is refreshed (the congress
     refresh task is Disabled). Also: 13 Robert Menendez rows are never judged (BILLSTATUS bioguide M000639 vs roster
     M001226).

N14  NOT MECHANICAL -- needs your ruling. Facts: (1) the ENGINE never scores the 'stance' column of either source: it
     signs all 2,668 press rows from press_stance_final.csv (the stack) and then your overrides. (2) The DESK displays
     the sheet's 'stance' (the R pipeline's 'debate' label; the sheet has flattened all 497 human_label rows to
     'debate'). (3) After both sides' override steps, 33 of the 57 releases still differ between what the desk DISPLAYS
     and what the engine SCORES (25 members); 21 more are not scored at all; 3 agree. (4) The tone CSV matches your
     label set (cu_stance_label_set.csv) on 57 of 57 and the sheet on 0 -- but your newer cu_golden_labels.csv backs the
     SHEET on 4 of them (Ossoff Spanish online-predators, Gillibrand seniors/fraud, Gooden interchange, Marshall NDAA
     interchange), and the engine's stack agrees with that newer file on all 4. Your two label records conflict; I did
     not resolve it. (5) score_graded is display-only; the engine never reads it.
     Options: a) the desk displays the label the engine scores (stack + overrides), raw label shown second -- my
     recommendation, it is the only option under which the desk says what moved the rank;  b) keep the sheet's label;
     c) show the CSV / human label.  Latent: the desk matches override URLs exactly while the engine strips a trailing
     slash -- equal today, would diverge on the first override URL ending in '/'.

N13  NOT SELF-RESOLVING. 36 of your 37 interview gold labels survive any split unchanged. The Risch 2020-02-23 row
     orphans (its credit-union sentence was Chris Wallace's voice-over), and own_source_stance_model.py then returns 3
     ("GOLD ORPHANS") and stops the interview channel until you re-adjudicate that row or a run sets
     CU_GOLD_ORPHAN_OK=1. So N12 cannot be applied before you rule on that one gold row.

N12  BUILT, NOT APPLIED, NOT LANDED (branch claude/unfinished-work-handoff-a3bbad). turn_tags.py (pure grammar),
     the collector fix behind IV_TURN_TAGS (2 new / 1 legacy byte-for-byte), migrate_interview_turn_bleed.py
     (--dry-run / --apply with verified backup / --restore, byte-exact round trip), 151 tests green. Dry run reproduces
     5,834 of the 5,835 measured rows (+29 it graded real).
     AN INDEPENDENT GRADE SAYS DO NOT APPLY IT AS BUILT (gradeN12): of the 64 rows it would INSERT only 46 are
     speaker-correct (71.9%, CI 59-82%): 3 are chyron text, 5 attribute a parks official named Mike Johnson to Rep.
     Mike Johnson (bare-surname match), 10 carry host words, 35 start with label debris. Kept text is clean in 52 of 60
     sampled rows (87%, CI 75-94%): PBS anchors with non-ASCII names, curly apostrophes and "FORMER U.S." are missed.
     1 of 60 splits removes the member's OWN untagged words (est. ~98 rows, CI 2-524). It deletes 56% of the words in
     the flagged rows; 639 rows would keep fewer than 8 words.
     Other consequences of any apply, measured by the builder: ~85 rows' speech-identity records (text_sha256-bound)
     and 25 personal-relationship windows break until their lanes re-derive; 529 already-paid reference labels are
     invalidated; audit_full's interview-DB receipt fails until the extract re-runs; psychometric inputs change at the
     next weekly refresh.
     My recommendation NOW (not yet approved): a v2 that TRUNCATES ONLY -- never inserts a new attribution -- with the
     grammar gaps fixed (non-ASCII and curly-apostrophe names, no-space colon "TODD:It", abbreviation periods, the
     surname-only match), rows that would keep fewer than 8 words left untouched, then the SAME independent grade, then
     apply with a verified backup. Rulings needed from you: truncate-only acceptable? the Risch gold row? accept the
     downstream re-derivations?
     The builder graded its own class E as clean; the independent lane found 12 of 46 not clean. Same lesson as DE-038.

## N12 v2 APPLIED AND LANDED, MEMBERSHIP FILE REFRESHED -- 2026-09-19 (appended after Paul's "GO on the truncate-only v2 and refresh the membership file")

### 1. Interview turn-bleed repair, version 2 (truncate only)

- **What it does.** Cuts a member-attributed INTERVIEW row at the first foreign speaker tag. It never inserts a
  row and never re-attributes text. Every removed character is kept in the table `speeches_turn_split_ledger`.
  Rows that a gold label, identity contract, reviewed record or credit-union interview passage points at are
  skipped, and so is any row that would keep fewer than 8 words. Brain D-062.
- **Independent grade (gradeN12v2).** Cut precision 90 of 90 (95% lower bound 0.9598); all 935 distinct cut tags
  read and real; 0 inserts. Harm census: 6 rows where the member's own tag reappears after the cut
  (`V3_own_member_tag_after_cut.json`). Five were protected. The sixth, rowid 245558 ('Mike Johnson', 502 words
  under `JOHNSON (voice-over)`), was truncated on purpose: those segments are a Summit Metro Parks naturalist,
  not the Speaker. Two Maxine Dexter rows (83061, 83158) return without a tag and were protected too. That is
  the "7 extra protected rowids" (5 + 2).
- **Apply (applyN12v2).** LIVE `social_media.db`: 5,477 rows truncated, 807 skipped, 0 inserted, 270,489 rows
  before and after, 13 of 13 checks against the hash-verified backup
  `backups\social_media.PRE-TURNSPLIT-20260919.db`. The Risch gold row 245771 is untouched.
  Undo: `python fec\members\migrate_interview_turn_bleed.py --restore --db <path>` (byte-exact, from the ledger).
- **Landed.** LIVE main `624e593eb` -> `ce0dc5b21` (fast-forward; the branch first merged main as `1dc64ba8a`,
  `fec/tests/run_tests.py` auto-merged as the union of both registrations). Kernel in LIVE after landing:
  247 passed / 2 FAILED, the same two pre-existing reds (`test_bill_collision_guards`,
  `test_make_staffer_network_html`). A dry run from the landed code plans 0 truncations and leaves the
  database's size and mtime unchanged (landN12v2). Collector dial: `IV_TURN_TAGS=2` (repaired, default),
  `=1` legacy.
- **Collector gate checked before landing.** The collector's only write is a plain `INSERT INTO speeches`
  (`fec/members/fetch_interviews.py:253`); there is no UPDATE or REPLACE and the table has no unique key, so a
  re-fetch cannot rewrite a protected row. It is not a chain step; its callers are
  `fec/collect/collector_supervisor.py:357` and `fec/collect/daily_media_refresh.py:176`. Residual risk: a
  `--verify` re-walk would append a correctly split copy beside a truncated row; `iv_fetch_log` idempotence
  (`:287`) and the CNN per-day package check (`:301`) guard it.
- **Rank effect of the repair: none.** `interviews_cu.csv` is byte-identical (sha256 `9a237205...8cf5`) before
  the apply and after the chain re-extracted it; the interview channel still signs 25 rows for 16 members.
- **Expected side effect.** The reference layer lost the mentions that lived in other speakers' words:
  edges 8,010 -> 7,884, drawn edges 3,482 -> 3,393.
- **Corrections to commit `770aaf154`'s message (history is not amended).** "95% CI >= 0.96": the bound is
  0.9598. "The only harm found was 7 rows": the census holds 6 rows (5 protected, 1 correctly truncated) plus
  the 2 Dexter rows.
- **Known blemishes.** Rows 83813 and 219962 now end in "...D." (the cut fell after a party abbreviation).
  Cosmetic; the ledger restores either row.

### 2. Membership refresh

- **Command.** `python fec\legislation\update_bill_repository.py --rebuild-dashboard` from the LIVE root,
  15:46-16:13 local: free GovInfo fetch (473 bills refreshed, 0 failed), then the chain from
  `verify_collector_roster_updates.py`. All 67 steps ran. Exit code 1 and `publication.status=FAIL` in the
  receipt come only from the terminal `audit_full.py`, which exits 1 while any audit check is red (DE-044).
- **The membership file.** `data/legislation/official_membership_movements.json`: status PASS, `checked_at`
  2026-09-19T19:46:30Z, `repository_sha256` equals sha256 of `bill_repository_live.json` (`fdb12754...`).
  Facts 5,683 -> 5,704. `additions` 207 -> 45 because 162 were absorbed into the desk ledger ("75 accepted,
  5237 already present"); `additions` is by definition the not-yet-in-ledger residue. **New expiry
  2026-09-27T19:46:30Z. The 2026-09-22 desk-build deadline is retired.**
- **Ranks moved for 279 of 533 members.** 254 unmoved, 267 by 1-5 places, 10 by 6-20, 1 by 21-50, 1 by 51+.
  Only the legislative pillar changed (press, influence, demographics: 0 members). Cause: five days of new
  congressional data -- 21 new cosponsor links on 8 bills and 3 latest-action changes. 20 members' agenda
  changed and 1 member's efficiency (Himes: H.R.4936 ordered reported 49-0). Everyone else was re-ranked around
  them: 151 of the 279 movers have a byte-identical score.
- **The one large move.** Tony Wied 366 -> 434. New cosponsorship of H.R.7035 (2026-09-15) routes to Interchange
  with sign -1 and topic weight 2.0: agenda 3.0 -> 1.0. The model is working as designed. For your eye only:
  one adverse Interchange cosponsorship outweighs six pro-credit-union MBL cosponsorships (0.3 each).
- **Nothing was lost.** 0 bills removed, 0 cosponsor links removed, 0 sponsor changes, 0 movement facts removed,
  archive cells 3,395 -> 3,401. Receipts: `measRefresh/`.
- **Audit 561 passed / 7 FAILED -> 559 / 9.** The seven standing reds persist. Two new:
  (a) `champions threat boards fresh vs live crown set` -- exactly one row, Pete Sessions (bank). Ordering
  defect, not a data defect: `champions_v2.py` (`run_pipeline.py:215`) runs before `make_member_desk.py`
  (`:285`), so the 16:04 boards read the previous desk bundle and the 16:08 bundle made Sessions tier 1. See N18.
  (b) `A2b mirror.melange sentinels unchanged` -- the off-box mirror repacked
  (`pack-9b083bbd...pack` is gone). `build_system_manifest.py` is not a chain step; its own lane rebuilds it.

### 3. Deadlines, soonest first

| When (UTC) | What dies | Why | What clears it |
|---|---|---|---|
| already red since 2026-09-17 | an audit check only | `pillar_inputs_snapshot.json` stamped 2026-09-03, 14-day tripwire (`audit_full.py:815`) | its producer's lane |
| **2026-09-21T03:41:10Z** | `build_archive_legislative.py` at import, so the chain and the desk | `sentinel_admissions.json`: oldest per-bill decision + 8 days (`sentinel_admissions.py:24,:33,:45`); this run did not change the file | the PAID admissions step (claude-cli) -- needs your spend + model ruling |
| 2026-09-27T19:46:30Z | `build_archive_legislative.py`, `make_member_desk.py` | membership movements + 8 days | the same free refresh command |
| 2027-01-03 | `compute_pillars.py:126` | `data/members/formal_visibility_roles.json` `valid_until` | a registry update (no producer exists) |

`fec_refresh_current.json` lives in `data/money/`, and no N-day window was found on it. My earlier "09-25"
date for it is withdrawn as unverified.

### 4. New items

- **N17 -- chain ordering.** Any cycle in which a primacy tier flips will redden the threat-board check,
  because the boards are built before the desk. Options: build the boards after the desk, or re-run
  `champions_v2.py` as a late step. No recommendation until the producers that read `boards.json` are mapped
  (see the addendum if present).
- **N18 -- Pete Sessions gained a tier-1 crown in this run.** His own score and legislative percentile are
  byte-identical before and after. Cause under measurement at the time of writing; see the addendum.
- **N19 -- sentinel admissions expire 2026-09-21T03:41Z.** The refresh is a paid model call. HOLD until you
  rule on spend and model.
- **N20 -- row 245558.** The whole 'Mike Johnson' row looks like a surname false positive (a park naturalist).
  The v1 grade found five such rows. The collector's member matching by surname is a separate defect; count
  unknown.

### Addendum -- the crown change behind N17 and N18 (measured read-only, 2026-09-19 evening)

- **The rule.** The desk's `tier` is the primacy board's seating (`make_member_desk.py:2545, :2663` ->
  `tier_util.py`). Board product = `factor_ranked x (0.80 + 0.20 x grade_percentile)` (`tier_util.py:460-474`),
  seated on its within-chamber percentile (`:796-802`), then your placements (`tier_overrides.json`: none), the
  `cu_primary >= 0.75` evidence floor (`:822`; 419 of 533 displaced), and the conduct ladder (`:825`; Barr and
  Hill floored). Buckets 13 / 24 / 48, so tier 1 is the top 13 seats and nothing else. A scratch transcription of
  the rule reproduces the live rank_honors generation exactly (533 of 533 in order).
- **What changed between the two chains of 2026-09-19** (rank_honors generations `049fbd78...`, 03:28, and
  `6df55c40...`, 15:55). Seats 1-12 are identical. **Pete Sessions seat 15 -> 13, tier 2 -> 1. Daniel Meuser
  seat 13 -> 14, tier 1 -> 2.** Two more tier changes: Bernie Moreno 0 -> 3 (seat 211 -> 80) and Patrick Ryan
  3 -> 0 (seat 85 -> 181). In all, 4 tiers changed and 416 of 533 seats changed occupant.
- **Why.** None of the four had any change in his own evidence: none is among the 21 new cosponsor links or the
  archive cell movements. `factor_ranked` shrinks a thin-evidence member toward a roster-wide baseline
  (`primacy_factors.py:438-457`): below 15 agenda credits a member moves whenever OTHER members' credits move
  that baseline; at 15 or more he does not. Meuser (22.75 credits) is baseline-immune. Sessions (12.25) moves at
  +0.23 per unit of baseline. Moreno (4.25) and Ryan (3.50) move at about 0.9, among the most baseline-sensitive
  members on the board. Both inputs of the product changed in the run (`primacy_factors.json` and
  `per_area_grade.json` hashes differ). Sessions now leads Meuser by 0.0018 (0.517476 against 0.515695) and keeps
  seat 13 while the baseline stays above 0.474393 (live 0.482222).
- **UNKNOWN.** How the crossing splits between the factor term and the grade term, and the exact cause of
  Moreno's and Ryan's opposite moves. The before versions of `primacy_factors.json`, `per_area_grade.json` and
  `member_desk_bundle.json` were overwritten at 15:54 and no copy exists. Proven: neither Moreno nor Ryan crossed
  the evidence floor (cu_primary 1.250 and 1.000 at both generations). Lesson recorded: copy those three files
  before any refresh.
- **What a viewer sees now.** `lobby-champions.html` (16:06) still lists Sessions as the top bank threat and as
  "omitted" under cross-sector exclusions. The desk, `Moneyball.html` and `Moneyball_Email.html` (16:08) show him
  crowned: tier 1, seat 13. The contradiction is split across two published files, never inside one.
- **N17 is structural, not a one-off.** `run_pipeline.py:223-225` documents that `champions_v2.py` and
  `industry_tiers.py` deliberately read the PREVIOUS cycle's desk bundle, so the threat-board audit check fails
  on any chain run in which the top 13 changes. Note: the credit-union instance of `industry_tiers.py`, built
  4 seconds after `boards.json`, already showed Sessions' new tier, so its "reproduces the desk bundle's tiers
  exactly" hard-fail may not bind -- worth a look.
  - **Recommended now (free, NOT run -- your GO):** `python fec\run_pipeline.py --from champions_v2.py`.
    18 steps, first `champions_v2.py`, last `audit_full.py`, zero LLM. None of them rewrites the two primacy
    inputs, so the tiers stay put; the boards re-read the current bundle, Sessions routes to "mixed" under crown
    supremacy, and Meuser is on no threat board. Best run before 2026-09-21T03:41Z (whether any of those 18
    steps loads the sentinel admissions was not checked).
  - **Structural fix (needs a design pass -- your GO):** let `champions_v2.py` take this cycle's crown set from
    the rank_honors generation, which is written before the boards, instead of last cycle's desk bundle.
- **N18 for your eye.** The 13th crown now turns on a roster-wide mean with a 1.6% margin, so a routine refresh
  that touches only other members can pass the last crown between a thin-evidence member and a fully evidenced
  one. This belongs with the primacy-methodology work. Nothing was changed. Receipts: `measRefresh/sessions_*`.
