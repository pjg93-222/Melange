# Moneyball — open items ledger

Created 2026-07-19 (Paul: "do create todo list document"). One line per item, with owner,
receipt, and what unblocks it. **Maintenance rule:** when an item closes, move it to the
Closed section at the bottom with the closing commit/date — never delete silently. Dates
are absolute. This file records OPEN work only; settled results live in `big5_methods.md`
and the audit reports, and the refuted/do-not-reflag lists in those reports stay binding.

## 1 — Paul's gate (decisions only he can make)

- [ ] **Crapo CCM cell** — the blank Credit Card Mandates cell; real anti-CCCA evidence is
      the only lever back to Champion. Evidence is Paul's to supply. (Standing since 07-07.)
- [ ] **94-row CFPB review queue** — awaiting Paul's labels (queued 2026-07-16).
- [ ] **Bluesky: ~180 unverified handles** — posts collected but withheld from the desk
      until Paul confirms handle identity (look-alike rule, 2026-07-16). Desk shows
      "handle pending verification" per member.
- [ ] **cu_passages appendix root-cause** — a chair's final turn absorbs the transcript
      appendix into one graded blob. Measured immaterial today (5/263 gold rows, 4 outcome-
      neutral, 1 tie-break; bounded ≤10 by audit tripwire @33b07a9). Fixing extraction
      changes grading → press pillar → ranks, so it is a scoring change at Paul's gate.
- [ ] **C11 upstream filing calls** — 8 privacy/cyber-titled bills filed under other slots
      (5× CBDC Anti-Surveillance → Technology & Emerging; 3× Saving Privacy Act →
      Examination & Supervision). Sections come from the upstream archive export; whether
      to override is a domain call. Receipt: `fec/bill_coverage_audit.py` C11, 2026-07-19.
- [ ] **Stranded codex worktrees (uncommitted work product, 2026-07-18):**
      `codex/coop-sector-probe` (coop-vs-A sector probe script, 1 dirty path at
      `%TEMP%\claude\cxwt-coop-sector`) and `codex/stance-curve-gold-tier` (MBL/Mortgage
      champion-curve 282→114 / 159→68, 4 dirty paths at `%TEMP%\claude\cxwt-stance-gold`).
      Commit-and-merge or discard — either is fine, but deciding prevents another
      stranded-work audit finding.
- [ ] **Mentat** (separate repo, `C:\Users\pgoff\Mentat`, branch codex/mentat-crypto) —
      crypto industry built + reviewed, UNCOMMITTED; other 4 industries + Phases 3-5
      pending. Paul gates the merge.
- [ ] **Standing user flags in code/docs:** `fec/retiring_members.txt` population;
      `BP_SRC=aug` ratification; 'CU Tax Status' DEFENSIVE-set membership.
- [ ] **electoral_plays re-run** — permanently user-gated chain
      (`build_electoral_plays.py → build_dashboard_bundle.py → make_dashboard_html.py`);
      never run unprompted (law 11).
- [ ] **D2/legacy dedup DELETEs** — ledger stands (CREC ~299 + legacy rows); no deletion
      without Paul (law 15).

## 2 — Data-gated / diagnostic-gated research (reopen only when the gate lifts)

- [ ] **Reactivity N-route round-4 reopen** — DATA-GATED at MEM_N ≥ 250 covered members
      (216 at last check; C-SPAN INTERVIEW rows raise it — observe the crossing when the
      chain runs after C-SPAN loads). Receipt: commit 48fd00d, `big5_n_matrix_prereg.md`.
- [ ] **A-route round-5 reopen** — DIAGNOSTIC-GATED on the pinned 5-seed synthetic
      passing ≥ 3/5 on bars 1-4 (safe to re-check anytime, synthetic-only). Receipt:
      commit d223188, `big5_a_matrix_prereg.md`.
- [ ] **A-validation open search** — Paul's STANDING directive (2026-07-12): keep an
      open-ended corpus search running for a better A criterion until he says stop.
      Kill-ledger A-closures do NOT bind this. Levers on file: agency/communion split,
      warmth cut, alt criteria, RKH lifeAgree.
- [ ] **Armed preregs on main (merged from gallant-gates 2026-07-19, looks NOT consumed):**
      O coverage-recovery and ONC cross-panel successor — FROZEN criteria await their one
      look. Audio speaker-identity layer is TDD, research-only, pilot + user gates pending.

## 3 — Collection cadence (Paul's ~3-week collector rhythm)

- [ ] **Collectors refresh** — interviews / hearings / social; graded-stance desk coverage
      (interviews 25 members, hearings 72 of 533) grows only with collection + labeling.
- [ ] **C-SPAN load** — scraper + repaired loader are on main (07-14 repair supersedes the
      07-11 lane); `load_cspan.py --dry-run` first, then decide `--replace`. Raises
      reactivity MEM_N toward the 250 gate.
- [ ] **Bills archive refresh** — newest export is `congress_bills_archive_20260624_*`
      (June 24). On refresh: `bill_coverage_audit.py` re-run catches new orphans/collisions;
      the 5 truncated titles (H.R.4052 "2023"; S.919/S.2290/S.1494 "21") may fix themselves
      upstream — if not, they are display-only blemishes.
- [ ] **Hearing-stance labeling tail** — 57 hearing rows sit at tier `review` (below the
      gold-only pillar bar); they surface on the desk but carry the weakest tier.

## 4 — Engineering follow-ups (no gate needed, just time)

- [ ] **One ambiguous interview passage** attaches to 2 sibling packages (36/37 pin
      exactly; the 37th shows on both rather than guessing). Cosmetic duplicate.
- [ ] **Doc-rot sweep** — two stale lines found this week by cross-checking docs against
      code (change-control §2.2 `--from` trap [fixed @565136c]; `.claude/commands/`
      `fable-audit.md:76` still names col-G in the convergence story). A systematic pass of
      skill/doc claims vs code would likely find more.
- [ ] **`make_combined.py` id-collision note** — build prints `id collisions: ['backbtn']`
      (handled by rename, by design). If a second collision ever appears, the rename map
      needs extending; today it is expected output, not a defect.

## 5 — Horizon (dated)

- [ ] **120th-Congress rollover** (new Congress seats 2027-01-03) — the
      `moneyball-congress-rollover-campaign` skill owns sequencing: congestion.json
      producer resurrection, roster swap, freshman impact, validation bars. The
      `archive_leg ≥ 516` audit floor (@565136c) re-bases here.
- [ ] **RL envelope** — Paul's roadmap; do not build uninvited (law 16).

## Closed (move items here with receipt)

- [x] 2026-07-19 — Bill plane coverage/orphan audit: CLEAN (0 orphans, 18/18 slots, no
      collisions); `bill_coverage_audit.py` + 4 standing checks @aa392e6.
- [x] 2026-07-19 — Interview/hearing stance + snippet display on the Press & social media
      tab: SHIPPED behind `DESK_MEDIA_STANCE` @45e1c82 + @ca1585a; live regenerated.
- [x] 2026-07-19 — Appendix-in-pillar worry: measured immaterial, bounded by tripwire
      @33b07a9 (item stays open in §1 only as the root-cause extraction decision).
- [x] 2026-07-19 — Ops hardening via Codex lane @565136c: stale-desk-HTML guard in
      `make_combined.py`, archive_leg floor check, docstring + dial-catalog doc-rot.
- [x] 2026-07-19 — Merge debt CLEARED: data-collection-rules-audit (antag v2 kept over
      main's v1 @290b4b9), cspan-video-scraper (main's 07-14 repair kept @4307515),
      gallant-gates (prereg ledger + audio TDD, 84 kernel tests @18a0ec2). Zero branches
      ahead of main.
