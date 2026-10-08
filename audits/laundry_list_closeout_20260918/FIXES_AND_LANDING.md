# Fixes built on 2026-09-19, and how to land them

Paul, 2026-09-19: "GO on all your recommendations, commit the packet."

## What that covered
- BUILT: N1 a, R1 a/b/c, N4 b, N2, A5, R10 a, R12.
- MEASURED FIRST, as the recommendation said: R1 d (design first), N5 ("yes, after N4").
- WITHDRAWN ON EVIDENCE: N5. My recommendation was wrong; see below.
- NOT COVERED, because the sheet made no recommendation on them, so they stay HOLD:
  R2, R3, N3, N6, N7, A6, R8, R9, D6, and R4 (conditional on whether you will grade the sheet).

## Commits on branch claude/unfinished-work-handoff-a3bbad (main is still 776ce0d3a)
| Commit | Fix | What it does | Dial (default / revert) |
|--------|-----|--------------|-------------------------|
| 0000ebf26 | packet | ledger, findings, ruling sheet, receipts | -- |
| 105907a59 | R1 a/b/c | reference layer: own-domain PRESS gate, roster/signature-block exclusion, identical windows count once | REF_PRESS_OWN_DOMAIN, REF_ROSTER_FILTER, REF_IDENTICAL_ONCE (1 / 0) |
| df707df0a | A5 | one press release under two URL forms counts once; same date AND title required | PRESS_URL_CANON (2 / 1) |
| 07576dfc6 | N2 | cross-post duplicate key = whole statement, not first 120 chars (desk sites) | CROSSPOST_KEY_CHARS (0 / 120) |
| 7c24547e2 | N4 b | sponsor rows from the archive's Sponsor column: helper + tests + live hook patch | LEG_SPONSOR_FROM_COLUMN (1 / 0) |
| bfb40573b | R10 a | Max route discloses its hub core | SHOW_HUB_CORE (true / false, template constant) |
| e100eae56 | -- | suites registered, dials catalogued | -- |
| b02296ae8 | N1 a | member desk reads the press the engine reads (union; the sheet wins the overlap) | DESK_PRESS_SOURCE (engine / sheet) |

Hooks into the two producers whose LIVE copies carry uncommitted drift ship as patches cut against
the LIVE bytes (git apply --check clean), not as edits on this branch:
- patches/N4_sponsor_column_live_hook.patch   (build_archive_legislative.py + its wiring test)
- patches/M_both_live_hooks.patch             (build_media_blend.py: N2 engine key + A5 ingest ledger, + wiring test)
  (N2_crosspost_key_live_hook.patch and A5_press_ledger_live_hook.patch are the same two hooks separately;
   apply EITHER the combined patch OR the two single ones, never both.)

## What review changed on top of the build lanes
- A5: a release key only NOMINATES a pair. Rows now merge only when date and title agree too. This was
  not theoretical: on live rows it keeps Vargas's two releases apart (one headline, 2022-09-30 and again
  2023-01-30 under a Drupal '-0' slug -- the House passed the bill in two Congresses). The build lane had
  reported that pair as "same title/date" and merged it. Live result: 11 merges, 1 conflict kept,
  2,679 -> 2,668 rows.
- N1 a: the desk union matched on the release key alone, so a future reused slug that the frozen sheet
  lacks would have been skipped. It now requires the same day (or an unreadable date on either side).
  Measured safe: all 2,377 overlapping rows agree on the day; nothing extra is appended today.
- A5 impact corrected: the press pillar moves for ONE member (Roger Marshall, Interchange, contributing
  rows 77 -> 76). The other merged rows sit in General Credit Union, which carries no pillar weight.
  FINDINGS A5 ("six double in the press pillar") overstated it.

## What is verified, and what is not
- Every fix: its own suite, written fail-first, run from the worktree with MONEYBALL_ROOT unset
  (70 + 23 + 18 + 20 + 44 tests, plus DashboardContracts 4); neighbouring suites unchanged.
- Every fix: a read-only prediction against LIVE data, saved under fixR1 / fixM / fixN4 / fixN1.
  R1 with all three dials off reproduces the shipped artifact 8,017 of 8,017 edges on every field.
- R10: driven in a preview built from this template + live dashboard_data.json: nothing computed at load,
  42 ms click, line fills to "Emmer 72% / Barr 65% / Hill 64% of all 487 max-cascade routes" (equal to the
  audited replay), cache hit instant, issue change blanks it, name click selects. Logic only: the browser
  pane is hidden, so appearance is unverified.
- NOT RUN: kernel tests, the chain, the rank delta, the audit. They cannot be run validly from a worktree
  (run_tests.py resolves data from __file__) and main's chain cannot resolve its producers. Change-control
  section 2.6 says a change is committable only after that protocol; these commits sit on an isolated
  branch for exactly that reason, and the protocol is owed in the LIVE tree before anything reaches main.

## Landing procedure -- NOTHING below has been done
Pre-conditions: no .pipeline_run.lock; no pipeline / collector / refresh python process; Excel closed;
copy ranks_python.json aside; note the audit baseline (2026-09-19: 544 passed / 15 FAILED on main's
audit code -- LIVE's audit_full.py differs, so re-take the baseline in LIVE first).
1. One path this branch touches is dirty in LIVE and will stop the merge cleanly (git aborts before
   writing): .claude/skills/moneyball-config-and-flags/SKILL.md (3 insertions / 1 deletion, another
   lane's). Commit that file first (the live-tree reconcile lane owns it). Every other path this branch
   touches is clean in LIVE (checked 2026-09-19).
2. In LIVE, on main:  git merge --ff-only claude/unfinished-work-handoff-a3bbad
   (main has not moved; if it has by then, a normal merge commit -- never rebase or squash.)
3. In LIVE:  git apply audits/laundry_list_closeout_20260918/patches/N4_sponsor_column_live_hook.patch
             git apply audits/laundry_list_closeout_20260918/patches/M_both_live_hooks.patch
   Re-run `git apply --check` first; both were clean on 2026-09-19 but LIVE moves.
4. Register the two wiring suites the patches create: add 'test_sponsor_column_producer_wiring' to
   _LANE_LEGISLATION and 'test_crosspost_key_engine_wiring' to _LANE_MODULES in fec/tests/run_tests.py.
5. Protocol, in LIVE: kernel tests -> build_media_blend (A5 and the N2 engine key are blend inputs, and
   the nightly chain starts at compute_pillars, so the blend will not run by itself) -> full chain ->
   rank delta -> audit against the baseline.
6. Reference layer: `member_reference_layer.py --rebuild` is cache-only and free; the weekly refresh runs
   it anyway. Expect edges 8,017 -> 8,010 and drawn edges 3,562 -> 3,482.
7. Commit the two hooked producers + the run_tests.py registration with the receipts (kernel count, the
   movers, audit tail).

Expected rank movement: Tim Scott up (Member Business Lending 10.76 -> 17.00 feeds the legislative
pillar); Roger Marshall by a hair (one press row); anything else should be displacement by those two.
Any other mover is an S1 finding -- stop.
Expected interim reds, by design, until the blend and chain have run once: audit_full's press row-count
check (press_domain_routing_audit.json 2,679 vs load_tone_rows 2,668); dashboard_integrity's desk input
hash changes once (new declared inputs); say_do_gap.json say_n rises for 146 members (non-chain artifact).
Rollback is always a dial flip (table above), never a git revert.

## N5 WITHDRAWN -- "point the desk at the routing audit" would hide real memberships
Measured (measN5 receipts): of the 627 workbook-only keys, 622 are a redundant plain-cosponsor twin of
a row the routing audit already SELECTS as original-cosponsor, and the desk's own collapse already eats
them; 2 are excluded-title rows the desk does not show; 1 is a non-roster delegate; 2 are the Tim Scott
sponsor rows that N4 fixes. Switching the desk to the routing audit's selected rows would LOSE 377 rows
and gain 24 across 194 members -- and 331 of the lost rows are adjudicated sidecar memberships
(bank_anchor 139, primacy_act 117, registry_anchor 73) that the producer's frame never sees. That breaks
"nothing hidden". The fork is benign; the desk stays as it is. One residual question: 23 memberships that
official_membership_movements marks withdrawn / role-superseded still display although apply_to_desk runs.

## R1 d -- design first: measured, not patched (measR1d receipts)
- The bleed mechanism is NOT roster-surname gating (FINDINGS B3 said so; that was the detector's rule).
  It is the collector's turn regex, fec/members/fetch_interviews.py ~202: an ALL-CAPS-only character
  class anchored at line start. It rejects a backtick (O`DONNELL:) and any lower-case parenthetical
  ("WALLACE (voice-over):"), so those turns stay inside the previous speaker's row. scrub() uses the same
  class and misses the same shapes; ingest_wj.py never calls scrub().
- Size: 5,835 of 153,576 INTERVIEW rows (3.8%) carry another speaker's words; MS NOW 8.7%, CNN 4.5%,
  PBS / NPR / C-SPAN 0%. 40 of 40 graded flagged rows are real; residual classes 72 of 72.
- Reference layer: 999 mentions are mis-attributed today (908 sit in a host's words, 91 belong to another
  member, 67 truncate) -- 4.8x the first detector's count.
- Desk: the interview footprint shows counts, not text; 2.4% of its displayed word tallies are foreign
  words. But 18 of the 1,059 verbatim "speaker-verified member details" excerpts show another speaker's
  words as the member's (14 members).
- Stance: 1 of the 25 in-use interview items is contaminated -- James Risch, 2020-02-23, Fox, labelled
  support, gold, weight 1.0. His own words are "Oh, he does, clearly. We all take orders from Bertie.";
  the credit-union sentence that triggered the item is Chris Wallace's voice-over.
- Repair design: there is NO raw transcript archive, so the collector cannot re-segment history. The
  repair is a one-off in-place split of the stored speeches text (the tags survive in the text) plus the
  regex fix for new rows; then --rebuild (free), optional --score for 158 changed windows (about $0.95),
  personal-texture, cu_passages, interview stance stack, media blend (rank-affecting), desk. Unmeasured:
  7,117 all-caps Washington Journal rows; about 40 psychometric scripts that read INTERVIEW text.

## New rulings this work surfaced
N12  Speeches migration (above): a data change to the speeches store and rank-affecting through the blend.
     Go / design further / hold?
N13  The Risch 2020-02-23 gold item scores words he did not say. Your label; untouched.
N14  The desk shows the SHEET's stance for 57 shared press releases where the engine scores the CSV's
     (e.g. sheet 'oppose', CSV 'support'), and the graded score differs on 1,207. Which source is
     authoritative? I kept the desk exactly as it renders today and only added rows.
N15  23 withdrawn / role-superseded memberships still display on the desk -- which side is right?
N16  R1 c recorded: "identical windows count once in the reference layer; Q11 'reposts count' is a stance
     ruling and does not extend to reference edges" -- implemented on your GO; REF_IDENTICAL_ONCE=0 reverses it.