# HANDOFF — Laundry-List Investigation + Engine Deep Audit (2026-07-16)

Written mid-flight so any agent (or a fresh session) can pick this up without loss. Everything below is
**investigation output only — NOTHING has been applied, edited, committed, or run against the live tree.**
Companion file: `HANDOFF_LAUNDRY_LIST_2026-07-16_results.json` (raw structured reports from every finished
investigator, same directory) — consult it for full tables/patches wherever this document truncates.

---

**[ANNOTATION 2026-09-19: SUPERSEDED. "NOTHING has been applied" stopped being true the same night: the lane landed as `391a4a8b5` (merged `e58a807da`; record `AUDIT_COMPLETION_REPORT_2026-07-16.md`), and its stance-band item was later superseded by brain decision D-031. The companion results JSON and the workflow scripts named in section 8 no longer exist. Every claim below is reconciled, with receipts, in `audits/laundry_list_closeout_20260918/LEDGER.md`; what was still open is in `FINDINGS.md` there, and what was built from it in `FIXES_AND_LANDING.md`. Two digest lines below are also stale: `audit_full.py` now exits 1 on failure, and kernel tests cannot be run validly from a worktree. The text below stands as the 2026-07-16 record.]**

## 0. Mission and standing orders (binding on whoever picks this up)

Paul's laundry list (2026-07-16):
1. **Stance bands**: Ally takes the place of Champion at the top; "Champion" reserved exclusively for
   Tier-1 members (the Legislative+Press tier). Tune band cutoffs — heavy outside scrutiny expected.
   Anchors: Crapo should be "highly persuadable or an Ally" (not Champion); Velázquez should be Highly Persuadable.
2. **Network UI**: can't de-select a member and get back to the plain overview — fix.
3. **Pathfinding/cascade max route almost always lists John Kennedy** — audit `moneyball_core.py`,
   `per_topic_coalition.py`, `budget_frontier.py`, `optimize.py`, `per_topic_flip.py`, `sna.py`
   (real file is `sna_layout.py`; `sna.py` does not exist).
4. **All legislation sorted into correct domain/column on dashboard** — nothing hidden, nothing excluded,
   true-duplicate check. Same for media and press.
5. **Cross-reference check**: relevance, direction, tone.

Follow-up order (same day): additionally sweep those six scripts for **bugs, collisions, integration errors,
synchronization, dead code, orphans, pipeline, logical flaws, faulty math, seed errors** — "Take no Prisoners".

**Gate (Paul, verbatim intent): "Apply fixes after consulting with me."** Present findings + plan, WAIT for
his sign-off, then apply. This overrides any keep-going/auto mode. Session toggles Paul enabled:
Test-Driven Design (write/update tests before the fix) and Deliberate pacing.

Project-law digest (full constitution: `.claude/skills/moneyball-change-control/SKILL.md` — READ IT before
applying anything):
- Never run or import `fec/*.py` casually (import == execution; scripts overwrite production artifacts at
  import). Only `fec/tests/run_tests.py` and `fec/audit_full.py` are safe to run.
- Verification protocol for any code change: kernel tests → full chain (`fec/run_pipeline.py`) → zero rank
  delta vs snapshot (unless change is supposed to move ranks) → `audit_full.py` tail reads `ALL MODULES CLEAN.`
  (its exit code is ALWAYS 0 — gate on the text). Check Paul has no live python jobs first; Excel must be closed.
- Never hand-edit generated JSON; never relabel stance/press items (Paul's domain — build overrides / ask);
  data deletions and the electoral_plays chain are user-gated; no `git revert`/rebase/squash ever.
- Port 8801 is Paul's server — previews on 8802. Fable model only for the 533 narratives; Haiku 4.5 for every
  other LLM step. PERS `'-'`=0.45, DTHRESH=11.25, pillar weights 30/25/40/5 are user-ratified constants.
  **[ANNOTATION 2026-09-18: 30/25/40/5 was current when this was written -- the 2026-07-07 GATE-2 ratification. The LIVE value is now 45/10/40/5 (`ranks_python.json` `ab_weights`, `fec/engine/pillar_policy.py:11-15`), changed out-of-lane on 2026-09-03 and not re-ratified since; open ruling S-5. The original line stands as the 2026-07-16 record.]**
- Refuted-findings lists in `AUDIT_FINDINGS_*.md` and the known-benign registry
  (`.claude/commands/fable-audit.md:72-82`) are binding — don't re-flag.

## 1. Repo state (2026-07-16)

- **Live tree** `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` is on branch
  **`claude/cfpb-sentiment-recorrection` @35b8a09** — 13 Paul-directed commits ahead of `main` (@e3d2923),
  which is a strict ancestor (0 commits main-only; fast-forwardable). ALL investigation below was done
  against this live branch, code and data.
- **Working branch for this task**: `claude/laundry-list-updates-a832c2` in worktree
  `.claude/worktrees/moneyball-tier-option-b0ff84`, currently parked at e3d2923 with no commits of its own.
  **Recommendation: fast-forward it onto 35b8a09 before applying any fix** (everything was diagnosed there).
- Worktrees have NO data (MONEYBALL_ROOT unset; `fec/paths.py` resolves ROOT to the script's own tree).
  Data-dependent runs must happen in the live tree.
- Live artifact freshness at investigation time: full chain last ran 2026-07-15 ~20:09–20:15
  (`category_stance.json` 20:09, `ranks_python.json` 20:09, `dashboard_data.json` 20:13, desk bundle 20:15).
  Live tree had untracked-only dirt (candidates, orphan/, outputs/, tmp/) — tracked files clean.

## 2. ITEM 1 — Stance bands  [INVESTIGATION COMPLETE — awaiting Paul's decisions]

### Mechanics (bands:mechanics report; every claim carries file:line receipts in the results JSON)
- **Two distinct ladders.** Per-category: `fec/stance/stance_rules.py:11-41` on a [-1,1] evidence score
  (0.70 = 'top' → 'Champion', or **'Defender'** for the 3 DEFENSIVE categories {Interchange, Credit Card
  Mandates, CU Tax Status}; True Neutral band at -0.05; no env dials in that file).
  **Overall**: `OVERALL_BANDS` at `fec/moneyball_core.py:215-217` on the [-4,+4] IMP-weighted TORD mean
  computed by `overall_tier()` (`moneyball_core.py:227-242`, ±0.05 rounding); Paul's env dial
  `OVERALL_OPPONENT_CUTOFF=-1.10` at :214, pinned exactly by `fec/tests/test_recorrection_contracts.py:22`.
- **Band changes are RANK-NEUTRAL but NOT display-only.** Stances never feed the four rank pillars, so ranks
  won't move. But band label STRINGS are dict keys into engine math: PERS pricing
  (`moneyball_core.py:188-191`; Champion=0.10, Ally=0.40), SGATE seeding (:202-205), TORD (:207-209) — these
  consume PER-CATEGORY bands, so an overall-ladder change is engine-safe there. The OVERALL label, however,
  is written to workbook col G (`sync_stance_g.py:22-25`, rows 3-535) and read back by
  `money_response.py:11` (defection ladder) and `build_electoral_plays.py:23` (plays gating — that chain is
  user-gated anyway). Changing overall cutoffs therefore moves persuasion/allocation artifacts, not ranks.
- **Say-do gate** applies AFTER the cutoff ladders, twice: cell-level `cap_uncorroborated`
  (`per_category_stance.py:343-359`) lowers Champion/Defender→'Ally' without Path A/V corroboration; overall
  read-time cap via `gate.overall_capped` in `category_stance.json` (`moneyball_core.py:240-241`). The cap
  output is the **hardcoded string 'Ally'** — collides head-on with renaming the top band; decide its fate.
- **Tier machinery** (`fec/tier_util.py`, BUCKETS 12/24/48) is display-only, consumed by
  `build_dashboard_bundle.py:289-301` (`tier`/`tierrank` fields) and `make_member_desk.py`; zero test
  coverage today; no existing tier↔band coupling. `gate.overall_capped` / the bundle decode maps
  (TC/SC/SCN/TIERNAME, `build_dashboard_bundle.py:86`) are the natural hooks for a Champion overlay.
- **~20 pinned checks** reference cutoffs/labels by exact value/string (`run_tests.py:49,51-54,70-76,80`;
  `test_recorrection_contracts.py`; audit_full band checks) — under TDD, update these FIRST.

### Data (bands:data report; validated 0/533 mismatch vs live dashboard_data.json)
Current overall ladder and census (n=533; 11 unscored; median +2.38, max +4.05):

| Band | floor | count |
|---|---|---|
| Champion | 3.65 | 5 |
| Ally | 3.05 | 116 |
| Highly Persuadable | 2.30 | 157 |
| Persuadable | 1.55 | 97 |
| Lean Persuadable | 1.05 | 53 |
| True Neutral | 0.55 | 55 |
| Lean Skeptic | 0.05 | 16 |
| Skeptic | -0.70 | 17 |
| Highly Skeptical | -1.10 | 3 |
| Opponent | below | 3 |

Key members: **Crapo +2.5802 (HP, LP-tier 2 r19)** — Ally would need floor ≤2.58 → 232 Allies (absurd);
he is HP in every sane ladder, which satisfies Paul's either/or. **Velázquez +2.0776 (Persuadable, tier 2
r15)** — needs HP floor lowered 2.30 → ≤2.0776 (2.05 is the clean choice). Britt +2.9786 (HP). Kennedy
+2.8006 (HP). Warren +0.3139 (Lean Skeptic). French Hill +3.2041 (Ally, tier 2 r14). Tim Scott +3.0914
(Ally, **Tier 1** r10).

- **The 5 current Champions** (Moran +3.8956 tier0, Rutherford +3.8253 T3, De La Cruz +3.7167 T2,
  Angus King +3.696 T3, Mike Rogers +3.6796 tier0) have **ZERO overlap with Tier-1** → all become Ally
  under Paul's rule.
- **Tier-1 twelve** (blended leg+press): Young Kim (Ally +3.0605), Hagerty (HP +2.877), Barr (Ally +3.0536),
  Fitzpatrick (HP +2.7161), Timmons (HP +2.9863), Lummis (Ally +3.3326), Cortez Masto (Persuadable +2.1033),
  Ritchie Torres (HP +2.3096), Roger Williams (HP +2.8692), Tim Scott (Ally +3.0914), Nunn (HP +3.0492),
  Cramer (HP +2.7886).
- **16 say-do-capped raw-Champions** currently display Ally (incl. all seven +4.05 max scorers: Gray,
  Austin Scott, Rouzer, McIver, Fallon, Elfreth, Cole; plus Strickland, McClain Delaney, Pfluger, Latta,
  McClintock, Franklin, John James, Matsui, Glenn Thompson).

### Candidate ladders (all keep the bottom five cutoffs = Paul's 07-15 scale shift untouched)
- **A — minimal (recommended)**: Ally≥3.05, HP≥2.05. Counts: Ally 121 / HP 191 / P 63. Champion overlay
  (Tier-1 ∩ Ally) = **Kim, Barr, Lummis, Tim Scott** (4). Crapo HP, Velázquez HP (+0.028 margin), Britt HP,
  Kennedy HP, Warren LSk.
- **B — round numbers**: Ally≥3.00, HP≥2.05. Ally 142 / HP 170. Crown = A's four + **Nunn** (5). Britt
  misses Ally by 0.0214.
- **C — champion-forward**: Ally≥2.85, HP≥2.05. Ally 174 (33% of roster — visible cost) / HP 138. Crown = 8
  (adds Hagerty, Timmons, Williams). **Britt becomes Ally** (echoes Paul's 07-07 Britt-upgrade instinct).
- Rejected shapes (documented so the walls are visible): Crapo-as-Ally (absurd), Ally≥3.30 (crown collapses
  to Lummis alone — Tier-1 stances top out at 3.33), any ladder without an HP floor ≤2.0776 (Velázquez).
- **Alternative crown rule** — ALL 12 Tier-1 = Champion regardless of stance: would crown Cortez Masto
  (Persuadable) and Torres (barely HP); 'Champion' would then mean "most important", not "most supportive",
  inverting how every other band reads. Intersection rule recommended.

### Decisions Paul must make (item 1)
1. Crown rule: Tier-1 ∩ top-band (recommended) vs all-12-Tier-1.
2. Ladder A / B / C (or dictate cutoffs; every 0.05 near 3.0 moves ~8–20 members — member-level review advised).
3. Fate of the say-do overall cap (its output string 'Ally' becomes the top band — keep as-is/vestigial,
   or repurpose; NOTE the 16 capped members are unaffected by A/B/C since they were already capped to Ally).
4. Does the PER-CATEGORY 'Champion'/'Defender' cell label survive unchanged? (Paul's ask reads as the
   OVERALL band; per-category labels feed PERS/SGATE/TORD engine tables — renaming those is a bigger change.)
5. Implementation layer: rules-layer (overall_tier band assignment + col G) vs display-decode-only.
   Note a subtlety for the implementer: tier_util reads `ranks_python.json` from the PRIOR run — wiring tier
   into the rules layer creates a new (benign, but must-be-documented) prior-run dependency, like bipartisan.json.

## 3. ITEM 2 — Network deselect  [DIAGNOSED — patch designed, not applied]

All in `fec/surfaces/templates/make_dashboard_html_00.tpl` (live branch): selection state `sel` (:184);
`selectMember()` (:639-662) zooms camera 2.4× via flyTo (:336); the canvas click handler (:323)
**has no else branch** — background clicks are no-ops and clicking the selected node re-selects; touchend
(:335) same; the only deselect control '← Targets' (#backbtn :161, wired :887 → `backToTargets()` :766)
**omits `fit()`** so the camera stays zoomed on the ex-member; the `?coal=` coalition handoff
(:906 → `loadCoalition` :626-633) is **un-clearable** (its clear controls live in the hidden member panel).

**Fix (3 display-only JS edits; exact snippets in results JSON, network-ui report):**
1. `:323` click handler → toggle: same-node click deselects; background click clears when
   `sel>=0||route||cascadeOn`.
2. `:335` touchend → same else-branch.
3. `:766` `backToTargets()` → add `fit()` (+ optionally clear the Find box).

Member desk tpl has no network widget (links out only) — no parallel fix. Engine math in the tpl
(prime/cascadeProbs/flipModel) untouched. Verify: rebuild `make_dashboard_html.py` → `make_combined.py`,
click-test on **8802**. Apply only after Paul's go.

## 4. ITEM 3 — Kennedy max-route  [ROOT-CAUSED — design decision needed]

**Mechanism (reproduced exactly, 3 independent agents):** the dashboard "Max route" is computed live in the
browser: `maxCascadeRoute` (tpl:564) → `budgetRecruit(sel, 7, -1)` (tpl:515-526), a GCOMB max-coverage
greedy whose gain `g=(1-cov[c]) + Σ_v PE[c][v]*(1-cov[v])` has **no seed-locality** (target=-1 disables the
dT steering term at :521), **no stance/tier/cost gates** (contrast every Python engine and the JS `prime()`
BLOCKOV gates), over a PE kernel (`build_P`, `moneyball_core.py:181-185`, `p=w·cpf·σ/(w·cpf·σ+6)`) that
saturates per-edge but never damps per-node aggregate. Result: the recruit list is a seed-invariant,
issue-invariant global-hub constant — **{Emmer, Barr, Vargas, Kennedy, Merkley, Hill} for 532/533 seeds**
(Reed substitutes when the seed is one of them). Faithful stdlib re-implementations reproduced this 532/532
and 12/12.

**Kennedy's hub-ness is genuine input**: #5 network strength 40.7 (median 1.0), 92% plain cosponsor layer —
few (46) but very heavy Senate dyads (Cassidy 4.99 = #5-heaviest edge in the network, Hyde-Smith 2.35,
Hagerty 2.02, Lummis 2.00). REFUTED: press-mention inflation (hcoi 0.1, social 0.0; refs don't feed engine
adjacency), '-'/PERS_NONE cheap-routing (budgetRecruit is stance-blind), Python-engine origin (stored
artifacts rank him ~#83; coalition most-funded is Markey 11/18). Point-to-point path mode is hub-dominated
too but Kennedy is only the #8 relay — the phenomenon is specific to the Max-route sub-mode.
`budgetRecruit` is JS-only (no Python mirror to keep in lockstep — confirm at implementation).

**Fix options for Paul** (any change is display-layer): (a) pass a real seed-locality/steering term
(use dT from the selected member); (b) add the same stance/tier gates the other modes use (BLOCKOV etc.);
(c) per-node out-strength damping in the route-mode PE only; (d) hub-diversity penalty; (e) keep the
behavior but relabel the UI honestly ("top global amplifiers").

**Adjacent engine findings (report-only, from the same audit):** PERS `'-'`=0.45 sits ABOVE Ally=0.40,
contradicting the in-code "Ally parity" comments (0.45 itself is Paul's ratified dial — flagged as a
question, not a fix); `budget_frontier_electoral` seeds Ted Budd 17/17 topics (electoral play pool is
topic-independent); per-member CRN draws are topic-invariant (same 20 uniforms decide a member's
seed-taking in every topic); alphabetical first-wins tie-breaks on 0.05-quantized MC marginals in all three
greedy heaps.

## 5. ITEM 4 — Legislation domains  [LEGISLATION DONE; MEDIA/PRESS RE-RUNNING]

Pipeline: `congress_bills_archive_20260624_115822.xlsx` 'All Bills' (10,986 rows, mtime 07-01) +
`manual_bill_evidence.csv` (1) → `build_archive_legislative.py` → `archive_leg.json` →
`per_category_stance.py` → `category_stance.json` (18 cats) → `build_dashboard_bundle.py` →
`dashboard_data.json`. A stdlib re-implementation reproduced `archive_leg.json` EXACTLY (0 mismatches, 509
members) — accounting closed: **10,987 in = 10,277 scored + 710 dropped, every drop user-ratified**
(phrase/pin 580 rows/19 bills, 10 non-voting delegates, overrides/neutrals). **Zero true duplicates**;
1,459 multi-domain listings are by-design.

Findings needing Paul:
- **HIGH — 'CU Tax Status' has NO dashboard column** (17 of 18 rendered). It's an IMP-3.0 protect flagship,
  visible on the member desk but absent from dashboard columns, per-topic flip/coalition, and allocations.
  Root: issue columns derive from `per_topic_alloc.json` keys ← workbook Legislative-Normalized topic blocks
  (`moneyball_core.py` blocks/BLOCKCAT). Add the 18th column + topic?
- **HIGH — bill universe forked**: workbook role sheets carry 5 Tim Scott MBL sponsor rows (12.24 signed
  weight, incl. Became-Law S.J.Res.18) absent from the archive xlsx — say-do gate and desk see them, the
  stance matrix does not (Tim Scott's MBL legislative evidence ≈ half what the workbook supports). Which
  universe is canonical / add to `manual_bill_evidence.csv`?
- **MED — original-cosponsor rows double-count** with plain-cosponsor twins in the scorer (2,708 combos,
  ~+2,708 weight) while `make_member_desk.py:600-618` collapses them for display. Intended?
- **Domain questions (labels = Paul's)**: CDFI Fund column has zero legislative evidence while 2
  CDFI-titled bills sit under Member Business Lending (S.869/118, H.R.7733/117); overdraft CRA disapprovals
  H.J.Res.59 + S.J.Res.18 (119th, 124 rows) sit under CU Capital Requirements + MBL; H.R.3009/117
  (mortgage-servicing language access) under MBL.
- **LOW latent**: `bill_key()` ignores bill type (`('H',59)` collides H.R.59/H.J.Res.59 — zero live
  collisions today); `bill_directions` parse `{'1':1,'-1':-1}.get(v,0)` silently neutralizes a '+1'.

**Media/press half was lost in a session crash and is re-running** (see §8). Known constraints for whoever
finishes it: press sheet is written by an external R pipeline (Draft Systems) with known mojibake; a
user-gated legacy press-dup ledger already exists (`apply_press_dedup.py` history).

## 6. ITEM 5 — Cross-reference relevance/direction/tone  [DONE]

Layer: `fec/members/member_reference_layer.py` → `member_references.json` (mtime 07-14, 7,972 directed edges from
CREC 14,511 / INTERVIEW 8,134 / X 545 / CHRG 425 / PRESS 29 raw mentions; 0 self-refs, 0 unresolved).
- **DIRECTION: clean.** 54-edge stratified sample: zero speaker/target swaps among genuine references.
  C-SPAN attribution repair (d66da46) regression PASSES upstream: 512/512 programs match the attributed
  member (511 slug matches + known 'Gimemez' typo alias, `cspan_identity.py:61-63`).
- **TONE: ~92-95%, zero polarity inversions** in 40 graded sign-bearing examples; sarcasm/quote-critically
  handled correctly; disagreements were one-notch neutral-boundary cases.
- **RELEVANCE: ~93-95%** with three concrete failure patterns:
  (1) **PRESS pass has no own-domain gate** — one third-party trade-press article fanned into 5 false edges
  (Magaziner cluster); the already-ratified rule in `resolve_attribution_domain.py:45-47` is not applied here;
  (2) **interview speaker-tag bleed** — windows crossing into another member's speaking turn create
  references where the "target" is actually the speaker (6+ edges, one signed negative, e.g.
  Raskin→Blumenthal); (3) **famous-namesake collision** — bare full-name scan accepts non-members
  (Angus King → "Mike Rogers at N.S.A.", signed positive).
- **HIGH structural hole: no C-SPAN mention has ever been tone-scored.** The Fable valence cache (07-07)
  predates the C-SPAN reload (07-14); the artifact was rebuilt cache-only → 0/382 C-SPAN windows scored.
  AND `MODEL` is still hardcoded `'claude-fable-5'` (`member_reference_layer.py:36`) — the pending
  ~1,881-context scoring pass must be gated by Paul on BOTH spend and model (cost rule says Haiku).
- LOW: 152 edges double-count byte-identical windows (dup tweets counted 2-4×, inflates the n_scored≥2
  drawing floor); `member_reference_verify.csv` (Paul's eyeball sheet) predates the 07-14 rebuild —
  regeneration is free (`--verify`, no API) but was not run (ask-first).

## 7. Engine deep audit (10 dimensions)  [IN FLIGHT — 1 of 10 auditors done]

Done — **`sna_layout.py`** (the real 'sna.py'; writes `sna_compact.json`, which has ZERO consumers and is
not in the pipeline chain — re-verified orphan):
- **NEW MED (seeds)**: output is nondeterministic across processes despite `spring_layout(seed=7)` —
  `keep=set(M)` hash-randomized iteration order sets node order → layout geometry, row order, AND which 28
  of 42 weight-tied edges survive the top-650 cut (PYTHONHASHSEED unset; demonstrated across 3 runs).
- **NEW MED (integration)**: line 9 picks newest-by-mtime across ALL `congress_cosponsor_network_*.xlsx`
  while the kernel prefers AUG files (`select_network_file`, `moneyball_core.py:145-150`) — a fresh base
  vendor export (exactly the rollover flow) silently makes the viz lay out a different graph than the
  engines. All 7 base files share one OneDrive-stomped mtime — receipt of mtime fragility.
- Known-and-quantified: additive dup-pair summation vs kernel mean (INERT today — 0 dup pairs in live AUG
  file); non-atomic write [KNOWN S2-03]. LOW/INFO: dead `import os` (:34), zero-lean stats-print bucket gap,
  degenerate-range division, dead rounding. Clean after adversarial check: Centrality radius join is
  correctly bioguide-keyed. Since the artifact ships to nothing: candidate remedies = attic the script, or
  fix + wire a consumer — **Paul's call**.

Pending auditors: `moneyball_core.py`, `per_topic_coalition.py`, `budget_frontier.py`, `optimize.py`,
`per_topic_flip.py`, plus 4 cross-cutting (collisions/sync incl. full Python↔JS constant-table diff;
integration/pipeline/orphans; seeds/determinism incl. roster-change CRN hazard; faulty-math). Then an
adversarial verification phase (HIGH gets 2 refuters, MED gets 1; only CONFIRMED/PLAUSIBLE survive).

## 8. Work in flight + how to resume

Two background workflows were running when this handoff was written (session `fb1642cb…`, worktree
moneyball-tier-option-b0ff84):
1. **Investigation** run `wf_0b5465aa-854` — items 1–3 + legislation + crossref are COMPLETE (results
   captured here and in the companion JSON); re-running: item-4 media/press investigator, replication
   copies of items 1–3, then a completeness critic.
2. **Deep audit** run `wf_591f0f50-f62` — 1/10 auditors done (sna_layout, captured above), 9 pending +
   verification phase.

Script files (self-contained, contain every agent prompt — re-runnable from any session via
`Workflow({scriptPath})`; note resume-cache is same-session-only, so a NEW session should re-run only
what's missing rather than `resumeFromRunId`):
- `C:\Users\pgoff\.claude\projects\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-moneyball-tier-option-b0ff84\2f62e2ba-968f-46dc-ad9b-d30ccd96bdfc\workflows\scripts\laundry-list-investigation-wf_0b5465aa-854.js`
- `C:\Users\pgoff\.claude\projects\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-moneyball-tier-option-b0ff84\fb1642cb-c1ec-4f62-8b36-003108dcba62\workflows\scripts\engine-deep-audit-wf_591f0f50-f62.js`

Full raw agent results (JSON journals): under each script's sibling
`subagents\workflows\<runId>\journal.jsonl`; consolidated dump = the companion
`HANDOFF_LAUNDRY_LIST_2026-07-16_results.json`.

## 9. Consolidated decision list for Paul (nothing proceeds without these)

1. **Bands**: crown rule (intersection vs all-Tier-1); ladder A/B/C; say-do cap fate; per-category
   Champion/Defender labels untouched?; rules-layer vs display-layer implementation.
2. **Network deselect**: approve the 3-edit patch (+ make the coalition view clearable)?
3. **Max route**: which redesign (locality / gates / damping / relabel)?
4. **Legislation**: add CU Tax Status dashboard column+topic?; canonical bill universe (Tim Scott MBL rows)?;
   original-cosponsor double-count intended?; 3 domain-placement questions (CDFI, overdraft CRA pair, H.R.3009).
5. **Cross-refs**: authorize C-SPAN tone-scoring pass (spend + model — code hardcodes Fable, cost rule says
   Haiku)?; apply own-domain gate to PRESS pass?; speaker-tag-bleed exclusion?; namesake guard?;
   dedupe identical windows?; regenerate the (free) verify CSV?
6. **sna_layout**: orphan — attic it, or fix (determinism + AUG-preference) and wire a consumer?
7. **Base branch**: OK to fast-forward `claude/laundry-list-updates-a832c2` onto
   `claude/cfpb-sentiment-recorrection` @35b8a09 for the apply phase?

*After sign-off, per change-control: TDD test updates first, one fix per commit with verification receipts
(kernel count, rank-delta result, audit tail), revert dial where behavior changes.*
