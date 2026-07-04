# AUDIT FINDINGS — 2026-07-04 (extensive audit + true run-through)

Auditor: Claude (Fable), session branch `claude/epic-aryabhata-7aa1e1`.
Target: live tree `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` (checked out on `main` @ 7ab9ef0).

## Session state at audit start (16:2x local)
- Live tree is **DIRTY**: 11 modified tracked files (+320/−50) + 8 untracked new files — today's
  (07-04) campaign: press stance-stack wiring, press-intensity degeneracy fix ("flipped Warren
  +310 ranks" per new audit-check comment), **receptivity switched to behavioral basis** (lexical
  Big5 indicted per `big5_nomological_prereg.md`), Big5 v2/v3 experiments.
- **Live activity detected**: big5_v3_hybrid.json written 16:22:42, social_media.db 16:21,
  member_desk_bundle.json 16:15:26; full chain ran 15:52–16:05 (ranks_python.json 15:54:42).
  Only python proc = http.server 8802 (read-only). Treating tree as ACTIVE → true run-through
  DEFERRED until mtimes quiesce; static sweeps proceed read-only against live-tree code.
- Audit expectation drift: committed audit = 53 checks; live audit_full.py adds 3 more
  (press-intensity non-degenerate, press stack drives component, receptivity behavioral basis)
  → expect 56 count-verified at baseline time.
- `bill_direction_queue.csv.tmp` (15:12) alongside final .csv (15:19) — orphaned atomic-write
  temp, investigate (P2).
- `_audit_tmp_frontier.json` / `_audit_tmp_optimize.json` in LIVE ROOT (16:03–16:04) — determine
  writer; if a session's determinism probe, temps belong in scratchpad (hygiene candidate).

## Baselines (Phase 1) — ALL GREEN (run serially after live-job check, per guardrails)
| Check | Expected | Got | Status |
|---|---|---|---|
| kernel tests (run_tests.py) | 30 passed, 0 FAILED | 30 passed, 0 FAILED | **PASS** (16:36, live tree) |
| py_compile sweep fec/*.py | all clean | 96 files, 0 failures | **PASS** (incl. uncommitted files) |
| audit_full.py | ALL MODULES CLEAN (53 committed / 56 live) | 56 passed, 0 FAILED, ALL MODULES CLEAN | **PASS** (16:38–16:41; all 3 new guards pass) |

## Run-through gates (Phase 2) — PENDING
| Gate | Result |
|---|---|
| (a) every chain step OK, exit 0 | **PASS** — 16/16 steps OK, PIPELINE COMPLETE in 7.4 min (16:42–16:50) |
| (b) audit tail ALL MODULES CLEAN | **PASS** — in-chain audit 150.2s, ALL MODULES CLEAN (56 checks; + standalone 56/56 @16:41) |
| (c) rank delta vs pre-state = 0/533 | **PASS — 0/533** |
| (d) engine artifact hashes identical vs pre-state | **PASS — 11/11 byte-identical** (incl. receptivity, stance, bipartisan, dashboard bundle: full idempotency, two-run convergence settled) |
| determinism: budget_frontier ×2 byte-identical | **PASS** — md5 b0e3038d… identical both runs (TOPIC=Interchange, scratchpad temps; audit check [8] concurs) |

Run notes: sync_stance_g workbook save succeeded (Excel closed, 17.9s); compute_pillars took the
view-stale snapshot path (known-benign); step 8's completion line still misnames its output
("wrote budget_frontier.json (mode ELECTORAL…)") — the S3-05 fix for exactly this sits unmerged
on audit/fixes-2026-07-03 (see S2-01). Run executed DURING the other session's CNN interview
collection (db-only writer; chain reads no db) after a 14-min edit-loop quiesce window.

## P5 — UI smoke (served 8802, fresh post-run HTML)
- cu-member-desk.html: 533 ranked rows; #1 (Mike Crapo) opens; staff directory cards render with
  12 gold + 12 star controls and 15 note boxes; all 7 sections incl. new "Behavior" (Behavioral
  profile bars, Meeting take-rate, Cross-media references present in DOM); In-contact panel
  switches. ZERO console errors/warnings. No localStorage test state written (read-only clicks).
- Moneyball Dashboard.html: renders (19 issue options, 533-name datalist, 16 target rows, canvas
  painted); all 5 NEW layer toggles (cosponsor/social/committee/engagement/references±) present;
  Receptivity color mode button present. ZERO console errors/warnings.

## Fix lane — NO-GO this round (deliberate)
Every fix candidate either (a) touches files carrying ANOTHER SESSION'S uncommitted campaign
(S3-03 TORD import, S3-04 ordinal, tpl copy), (b) is that session's workspace residue (S3-05
tmp file), (c) is already fixed on a stranded branch awaiting merge (S3-05-run-3 print), or
(d) is doc rot whose correct fix describes the UNCOMMITTED code and belongs in the campaign
commit (P4 items). Committing any of these from this session would manufacture merge conflicts
against live work. The fix lane for this audit is therefore: MERGE + COMMIT actions listed in
S2-01/S2-02, owned by the user (or the wizardly-jemison session), not auditor-appliable.

## Run-4b — user-directed optimization pass (same day, post-audit; all changes in the LIVE tree)

**1. Big5 "keep it — is it accurate?"** Kept, with honest labeling already in place: the desk radar
is v2 (behavior-calibrated text instrument; held-out r A+.14 / C+.13 / E+.34 / O+.20 — every trait
right-signed out-of-sample, at/above the published lexical ceiling ρ .08–.14); v1 survives as the
N-source (no behavioral criterion for Neuroticism exists) and desk fallback; ES rides the
genre-general composite (split-half .92). As a *style/persona* read the Big5 is reliable
(split-half .60–.92) and RKH-convergent (.42–.52); as a *behavior predictor* v1 was indicted —
which is exactly why engines run on behavioral dispositions while the Big5 stays the human-facing
context layer. The ceiling-breaker remains the parked ~$30 LLM item-level pilot.

**2. Bottleneck (valence-hop 0.689) — explained + attacked.** The stance model reads WHO a text
targets and the direction toward that target at 0.915; what it fumbles is whether the TARGET is
good or bad for CUs (0.689) — fix that and composition hits 0.872. Re-ran the registry derivation:
11 families carry user-derived valences; the 5 skipped ones fall to the flat model, and the
biggest is **interchange itself** (user golds split 11 neutral / 11 anti / 1 pro — the family bag
mixes pushing-the-CCCA with blocking-it with generic swipe-fee chatter). Built
**valence_family_review.csv** (live root): the 5 family questions with all 38 of the user's own
prior gold rows as evidence, including a proposed interchange direction-split
(interchange_push −1 / interchange_defend +1 / swipe_fee_generic 0). Five answers unblock the
bottleneck; re-derive with `python fec/derive_valence_registry.py --write` after answering.

**3. The three graded gaps ("fix these"):**
- Persona C+ → **fec/validate_persona_gold.py** built: scores agency_communion.json against the
  30-member persona gold sheet the moment it's rated (Spearman per axis; pass bars pre-set at
  .30 PASS / .15 DIRECTIONAL — locked before scores are knowable). Sheet is currently 0/30 rated.
- Attribution C → **fec/validate_attribution_gold.py** built: scores the production reader's
  attribution field against attribution_gold_sheet.csv (0/60 labeled); recovers urls via title
  match; per-class precision/recall + confusion. Filling the sheet is the entire remaining step.
- Receptivity effect sizes B− → **fec/receptivity_sensitivity.py** built + run. Replication gate
  533/533 exact. Result: **every pressure_mult constant is decision-ROBUST** — susc scale .18
  halved/×1.5, PT mild/strong, retiring 0.60→{.45,.80,1.00}, persona weight 0→.45 all leave the
  top-20 flip-target set at 19–20/20 (rank-ρ ≥ .998). The literature-shaped magnitudes cannot
  have bought a wrong targeting decision; they are fine-tuning on a decision surface dominated by
  stance/network/money. The exception with real leverage: **seed_prob coefficients** (~200/533
  members move cascade gates >0.05 under sweeps) → the pre-registered outcome test that matters
  first is seed_prob vs NEW next-quarter cosponsorship adoptions; second, pressure_mult vs
  stance-tier movement among actually-engaged members (In-contact log). Both designs are in the
  harness docstring.

**4. Committee positions checked.** All spot-checked leadership seats are 119th-correct (Crapo
Finance Chair + JCT Chair present — an earlier probe truncation, not a data gap; Scott Banking
Chair, Warren Banking RM, Wyden Finance RM, Hill FS Chair, Barr FS-FI Chair, Ernst SB Chair,
Markey SB RM, Cantwell Commerce RM). The real finding is COVERAGE: **245/533 members have no
Committee Data row** — including Durbin (Senate Whip, Judiciary RM — the interchange antagonist),
Schumer, Collins (Approps CHAIR), Murray, Jeffries, Johnson, Scalise, Clark. Judiciary,
Appropriations, Rules, Ag and leadership offices are untracked, yet NCUA Budget & Insurance and
CDFI Fund categories are appropriator-decided, and interchange runs through Judiciary-antitrust
framing. DECISION MENU for the user (tiers are calibration, not auditor's to set): (a) add
Appropriations—FSGG [Moderately?] (NCUA/CDFI jurisdiction), (b) add Senate Judiciary [Moderately?]
(interchange/antitrust), (c) price leadership offices (Speaker/Leaders/Whips) as pseudo-seats,
(d) leave as-is knowing 245 members carry zero committee pillar by design.

**5. Small Business retier — APPLIED (user directive).** The workbook Committee Data sheet already
tiers Small Business (full) [Highly] on every row; the desk was overriding it to 'Moderately'
(make_member_desk.py:351 "UNIFY" line). Override deleted — the desk now displays the sheet's own
[Highly]. Display-only (committee_score column unchanged), no rank impact.

**6. Mentions person-verification + phrase evidence — APPLIED.** member_reference_layer.py
resolver upgraded (kernel-single-sourced NICK_SETS nickname classes — bernie~bernard now resolves
in bare-name form; chamber-scoped title pools — "senator johnson" resolves to Ron Johnson inside
the Senate surname pool instead of dying on House-Johnson ambiguity; single-alternation bare-name
scan). Examples now attach to EVERY kept class (pos/neg preferred, neutral fills), and
make_member_desk.py now passes the evidence quote on ALL reference rows, both directions — the
tpl already renders it, so every desk reference row shows its phrase. New free modes:
`--rebuild` (re-extract + re-aggregate from cache, $0 — new resolver recall lands in n_raw; scoring
new windows stays behind the --score --go cost gate) and `--verify` (writes
member_reference_verify.csv — every edge with quotes + a wrong-person/wrong-valence column for the
user's eyeball pass). NICK_SETS added to moneyball_core (kernel tests 30/30 post-edit);
fetch_interviews.py still carries its inline copy — consolidation note for the campaign owner.

## Run-4c — A-grade drive (user: "get everything to an A")

**Twin radar charts SHIPPED (user directive):** the desk Behavior section now renders TWO radars
with identical geometry — Behavioral dispositions (Cooperation/Diligence/Floor presence/Visibility/
Breadth, teal) above Text Big-5 v2 (blue). n/a behavioral axes plot at the 0.5 neutral ring and are
listed under the chart (never fake-low). Verified live on Crapo: 2 radar SVGs, zero console errors.

**Prospective outcome test ARMED (the receptivity A-path):** fec/outcome_snapshot.py froze
outcome_snapshot_2026-07-04.json (533 members, 511 with cosponsor baselines) with pre-registered
hypotheses + bars locked before outcomes are knowable: H1 seed_prob→new cosponsorships, H2
pressure_mult→|tier movement| (engaged-only variant when In-contact data exists); rho ≥.20 PASS /
≥.10 directional / ≤−.10 indicted; scorer refuses before 60 days + 150 movers. One command in
September: `python fec/outcome_snapshot.py --score outcome_snapshot_2026-07-04.json`.

**A-grade matrix — what each item needs, and who holds the pen:**
| Item | Now | A requires | Owner |
|---|---|---|---|
| Behavioral dispositions | A− (valid by construction; visibility interim-guarded) | nickfix reingest lands → rebuild interaction→panel→dispositions (visibility/dominance full-roster) | auto (reingest running) |
| Receptivity magnitudes | B+ (decision-robust bounded; outcome test armed) | H1/H2 ≥.20 at ≥60 days | time + Sept command |
| Text Big5 | B+ (v2 right-signed OOS at lexical ceiling) | above-ceiling instrument = $30 LLM pilot, or accept ceiling as method-final | Paul ($30 call) |
| Persona | C+ (harness ready, bars pre-set) | rate 30 blind rows → validate_persona_gold.py ≥.30 both axes | Paul (~20 min) |
| Attribution | C (harness ready) | label 60 rows (own/action/thirdparty) → validator | Paul (~30 min) |
| Tweet stance | A− (0.855/0.819 OOF) | pre-registered confirmation on next fresh adjudication batch | Paul (next batch) |
| Press stance | B+ (0.837/0.765; wired, guarded) | readjudication queue pass on the adversarial frame | Paul (queue exists) |
| Valence hop | B− (0.689, the bottleneck) | 5 family answers → re-derive → compose toward 0.872 | Paul (~10 min) |
| Reference layer | B (precision-gated display; 0.68 neg-precision measured) | score the 731 new mentions (~$4.40) + spot-check verify sheet | Paul ($4.40 call) |

## Run-4d — $34.40 spend executed (user: "go with the 34.40 … prompt caching and other
## efficient methods, in opus")

- **Mention scoring (~$4.40, Fable):** relaunched `member_reference_layer.py --score --go` (the
  first launch died with a harness error — cache mtime proved no spend happened). Kept on FABLE
  deliberately: 6,575 existing edge judgments are Fable-rated; switching raters mid-corpus mixes
  instruments (the repo's own per-model-cache discipline).
- **Big5 LLM pilot (Opus, efficient config):** big5_llm.py upgraded — (1) `--batch` mode via the
  Batches API (**flat 50% discount**, submit-or-resume with a persisted batch id so an interrupted
  poll can never double-spend); (2) Opus calls now use the repo's measured-best reader config
  (adaptive thinking + effort medium — the 0.779 press-reader replica); (3) documented that the
  existing system-block `cache_control` is a silent no-op on Opus 4.8 (minimum cacheable prefix
  4096 tokens; this system is ~700) — the batch discount is the real lever. Launched
  `--pilot --opus --batch --go` (1,313-chunk scope, 185 RKH-overlap members; direct-cost estimate
  ~$22–45 with thinking → **~$11–22 at batch pricing**). Contamination probe (`--named`) queued
  behind the pilot's validation, same batch path.

## The three sheets — exact protocol (user asked "what do I need to do")
1. **Valence (~10 min, biggest single payoff):** open `valence_family_review.csv` (root). Five
   family blocks, each with a QUESTION row + your own prior gold rows as evidence. Write +1 / −1 /
   0 in `your_valence_+1_0_-1` on each QUESTION row (for interchange, either one blanket valence
   or adopt the proposed split — write `split: push=-1 defend=+1 generic=0`). Then any session
   runs `python fec/derive_valence_registry.py --write`; the weekly stack re-score folds it in.
2. **Attribution (~30 min):** open `attribution_gold_sheet.csv`. Per row, read the excerpt and
   type exactly one of `own` / `action` / `thirdparty` in the label column. 15 rows = first
   stable number; all 60 = the real grade. Then `python fec/validate_attribution_gold.py`.
3. **Persona (~20 min):** open `persona_gold_sheet_BLIND.csv` (STAY in the blind sheet — names
   redacted; 1:1 row order with the named sheet, verified). Rate each excerpt 1–9 on
   `your_agency_1to9` and `your_communion_1to9` from the text only. Then
   `python fec/validate_persona_gold.py` — it now reads the blind sheet directly and maps by row
   order (no copying step).

## Run-4e — attribution closed via domain rule (user: "cross reference the link for it — if it
## is from a member's website its theirs, anything else is third party")

Built `fec/resolve_attribution_domain.py`: title-matches each gold-sheet row to its source url
(same join the production reader already makes), applies the user's rule (own .house.gov/
.senate.gov → 'own', else → 'thirdparty' — a 2-class collapse of the reader's 3-class field,
matching the channel-weight logic already ratified in build_media_blend.py), and writes the
result back into attribution_gold_sheet.csv with a `resolved_url` column for the user's own
cross-reference. **Never overwrites a row already hand-labeled** — confirmed live: the user had
typed 6 labels into the sheet (open in Excel) between the dry run and the write; those 6 survived
untouched, domain-rule filled the other 54 (18 own / 42 third-party in the dry run; final file
13 user + 54 auto-resolved after the user's edits landed). Hit a real PermissionError (sheet open
in Excel) — asked the user rather than force-closing Excel; they closed it, write succeeded.

`fec/validate_attribution_gold.py` rewritten to grade fairly against a 2-class truth: reader's
`reported-action` and `third-party-voice` both collapse to "thirdparty" before comparing (domain
truth can only ever assert own-vs-not, never action-vs-opinion). **Result: attribution accuracy
0.947 (n=57)** — own precision .88/recall .94, thirdparty precision .97/recall .95, only 3
disagreements (2 false-own, 1 false-thirdparty). Attribution is no longer an open item — it went
from "0/60 unlabeled, no non-circular number" (C) to a validated 94.7% in one command.

## Run-4f — valence review resolved via per-row confirm/correct (user: "it matched up almost
## perfectly, double check")

The 5 blank family-level QUESTION cells stayed empty — but the 40 evidence rows underneath them
carried a real signal the user had confirmed row-by-row against their own historical labels:
**37/40 matched exactly**, and the 3 corrections were the decisive information. Diffed prior vs.
typed per row to separate signal from noise:
- **interchange**: 12 on-topic rows, 11/12 unanimously -1 on the CCCA/swipe-fee target (1 outlier).
  The other 11 rows in the family were pure keyword collision — literal highway interchanges
  ("I-90 interchange", "SR-210 interchange") false-matching the bare word "interchange". Fixed at
  the source: dropped that keyword from derive_valence_registry.py's FAMILIES list (the remaining
  "credit card competition"/"swipe fee"/"durbin" keywords catch every genuine on-topic mention).
- **overdraft** -1 (1/1), **reg_relief** +1 (2/2): unanimous, ship as-is.
- **big_banks**: the user's 2 corrections (support→neutral) flipped the family from a 6-way split
  to 8/9 neutral — resolves cleanly to 0 (orthogonal), one of the three options originally posed.
- **defense_cu** deliberately left UNWRITTEN: the 3-row sample splits by what looks like a
  sub-topic difference (CU-access policy, +1, vs. a specific institution's discrimination-
  investigation coverage, likely off-target "navy federal" keyword noise) rather than genuine
  inconsistency — a real judgment call on a thin sample, flagged for the user rather than decided.

Added a `CONFIRMED` dict to derive_valence_registry.py (source-tagged `user-confirmed-review`,
distinct from `derived-from-gold`) and wired it into the 5-fold CV as fixed external knowledge
(included in every fold, not derived from train — no leakage). **Result: CV accuracy 0.782→0.787,
macro-F1 →0.759, registry coverage 74%→81% of rows** (296→324/399 hit the registry instead of
falling to the flat baseline). Registry written (15 entries: 11 derived + 4 user-confirmed).

**Not yet propagated to production**: tweet_stance_stack.py / press_stance_stack.py /
apply_two_hop_stance.py all consume this registry to build tweet_stance_final.csv /
press_stance_final.csv, which feed the live media blend and WILL move some ranks if re-run. That
re-run needs no new API spend (the stance-hop/valence/confidence fields come from an existing
Fable cache) but is a visible, rank-affecting change — held for the user's go-ahead rather than
cascaded silently, especially with another session's uncommitted campaign live on this same tree.

## Run-4g — valence registry propagated to production (user: "yes, run it now" on both the
## defense_cu call [+1] and the re-score)

Wrote defense_cu=+1 (16 registry entries: 11 derived, 5 user-confirmed). Then ran the full
propagation chain live on the shared tree: `tweet_stance_stack.py --score` (9,559 tweets:
support 3,515 / oppose 3,124 / neutral 1,861 / unrelated 1,059; tiers unanimous 2,567 / majority
6,211 / review 781) → `press_stance_stack.py` (2,388 articles, 486 changed vs. DEBATE = 20%) →
`build_media_blend.py` (2,221 workbook cells changed, backup auto-created) → `run_pipeline.py
--from compute_pillars` (skipped receptivity/category-stance — verified unaffected by media-blend
inputs; confirmed post-hoc: category_stance.json hash UNCHANGED).

**Gates: 15/15 steps OK, audit tail ALL MODULES CLEAN (326s).** Rank delta: **374/533 members
moved** — large, but this re-scored the ENTIRE tweet+press corpus against a registry where 5
families went from skip→flat-fallback to actively-derived, plus the interchange keyword-collision
fix. Biggest movers: Jack Reed 373→69 (-304), Nicole Malliotakis 21→106 (+85), Chip Roy 477→341
(-136). Checked a hypothesis that Jack Reed's swing traced to the highway-interchange keyword fix
specifically — **falsified it** (zero of his 26 press rows contain the literal word
"interchange") before reporting it, so the per-member driver for the largest individual moves is
NOT pinned down to a specific family; only the aggregate cause (full corpus re-score across 5
newly-resolved families) is verified. Available on request: an isolated single-family before/after
diff for any specific member. Artifacts confirmed changed: tweet_stance_final.csv,
press_stance_final.csv, press_component_meta.json, budget_frontier(_electoral).json,
optimize_result.json, dashboard_data.json. category_stance.json confirmed BYTE-UNCHANGED (proves
the skip of receptivity/per_category_stance was safe — those systems are genuinely independent of
the media-blend/stance-stack inputs).

## Verdict
ALL GATES GREEN at the effective (uncommitted) live-tree state. The system's math, determinism,
idempotency, contracts, kernel single-sourcing, and both UIs verify clean. The material risk is
not in the running system but in VERSION CONTROL: today's ratified integrity fixes exist only as
uncommitted working-tree changes + two stranded branches (S2-01, S2-02).

## Findings

[S2-01] fec/run_pipeline.py:19-34 + fec/audit_full.py:66 — user-ratified lt_priming work is NOT in
production. Evidence: commit 285e604 ("lt_priming stance-integrity gates, user-ratified 2026-07-04,
LS carved out" — adds lt_priming to the CHAIN) exists ONLY on branch `claude/eager-wright-c73612`
(tip 7283298, merge commit "into session branch"); `git log -- fec/run_pipeline.py` on main tops out
at fd9f3d6 — main's CHAIN has 16 steps, no lt_priming. Yet audit_full.py:66 reads lt_priming.json
UNCONDITIONALLY (`pr=json.load(open(B+r'\lt_priming.json'))`) — it passes only because a stale
branch-produced lt_priming.json (mtime 07-04 00:13) sits on disk. Impact: the Warren-class
false-flip-target kills (overall-tier gate, recruit floors, COMMIT θ, PERS pricing) are ABSENT from
every main-chain run; lt_priming.json silently drifts stale as stance/network data moves; the
GOLD-format audit fix landed on main separately (e5451dd) so the branch looks "landed" at a glance.
Related: audit/fixes-2026-07-03 @4527b8f (S3-05 print fix) ALSO awaits merge (known from run-3).
Remedy: merge/cherry-pick 285e604 (+ 4527b8f) to main, or (if the user un-ratifies) remove the
chain-step expectation and make audit_full's lt_priming read freshness-guarded.

[S3-01] Memory/docs describe the 17-step chain as live ("lt_priming now IN chain") — true only on
the unmerged branch. INDEX.md/README verification protocol still says "audit 52/52" — committed
audit is 53 checks, live (uncommitted) audit is 56. Doc/expectation rot around the audit count.

[S2-02] main @7ab9ef0 is BEHIND the ratified state by three integrity-critical uncommitted fixes:
(1) press intensity 0.25-floor degeneracy fix (committed dynamic-press code saturates 100% of
articles → pure count measure — the "flipped Warren +310 ranks" class), (2) press stance-stack
wiring (committed code signs from DEBATE-era tone csv stances), (3) receptivity behavioral basis
(committed code runs the INDICTED lexical Big5). A pipeline run from any clean checkout of main
regenerates all artifacts on the regressed math AND self-certifies clean — main's 53-check audit
predates the three guards that would catch it. Evidence: `git diff` on live tree (+320/−50 across
11 files); new guards exist only in uncommitted audit_full.py:208-235. Impact: silent full-system
regression on any fresh clone / checkout / OneDrive rollback. Remedy: commit today's campaign
(wizardly-jemison session or user ratifies), then merge the two stranded branches (S2-01).

[S3-02] fec/member_reference_layer.py:231 — member_references.json (new cross-media reference
layer; desk + dashboard consume it) has NO automated refresh: not a chain step, not in
weekly_refresh's new step list. QUESTION for user: deliberate (each run spends Fable API calls) or
wiring gap? If deliberate, desk/dashboard reference panels silently age. Suggest a staleness print
in the two consumers.

[S3-03] fec/build_dashboard_bundle.py:47 — `_TORD` is a value-identical local copy of kernel TORD
(moneyball_core.py:154). The surrounding `_agg_stance` is a DOCUMENTED display variant (Defender
carve-out + Persuadable rungs — intentional, comment block explains), but the dict itself should
import: `from moneyball_core import TORD as _TORD` — else a future kernel re-tier silently
diverges the dashboard's overall-stance badges. One-line inert fix; deferred (file carries
uncommitted third-party work today).

[S3-04] fec/templates/make_member_desk_00.tpl (bar()) — "91th pct" ordinal carry-over from run-3
still present (`${Math.round(v*100)}th pct` → 1th/2th/3th/91th). Cosmetic.

[S3-05] Live root: `bill_direction_queue.csv.tmp` (15:12, 119KB) — orphaned atomic-write temp from
session curation tooling (no writer in fec/); final csv + FILLED versions postdate it, flow
completed. Safe to delete once today's session closes.

### Verified clean (checked, no finding)
- py_compile sweep: 96 files (live tree incl. all uncommitted work), 0 failures.
- Kernel drift (P3): NO residual copies of cpf/sm64/PERS/IMP/SGATE/BLOCKCAT/dump_atomic/build_P
  outside moneyball_core; sync_stance_clean.py hard-guard intact; MBC/MC aliasing correct
  everywhere (cascade engines alias module as MBC).
- Silent-failure surfaces (P2): all chain writers atomic (dump_atomic); all missing-input
  fallbacks announce themselves (big5_traits/electoral_plays/agency_communion/salience/advisory);
  no silent member/category-zeroing .get defaults in chain scripts. make_dashboard_html writes
  HTML non-atomically — accepted (browser-only consumer).
- budget_frontier.py:116 `EP[m]['value']` — NOT a KeyError risk: build_electoral_plays.py writes
  'value' on all four play branches (lines 28/35/40/42); filter guarantees membership.
- behavioral_dispositions.json ↔ receptivity_layer contract: producer keys (cooperation_z,
  diligence_z, dominance_z, visibility_z, breadth_z) exactly match consumer reads; missing →
  0-neutral by design; 533/533 members ≥1 component (audit floor 450); loud coverage print.
- New scripts' dump targets: behavior_panel.json / behavioral_dispositions.json /
  interaction_features.json / big5_v2.json / big5_v3_hybrid.json / big5_llm_*.json /
  member_references.json — none clobber chain artifacts (big5_traits.json untouched).
- Templates ↔ bundle mirror: new fields elay/refs/recept all null-guarded in dashboard JS; desk
  tpl's behav_pct/basis/seed_prob/refs all emitted by make_member_desk.py. Blend meta (15:20 run):
  1201 articles → 290 members, pv n_distinct 608 / median .03 ∈ (0,.0697), stack 1569 signed /
  0 DEBATE-fallback / 30 unrelated-zeroed, channel 661 own @1.0 / 540 third @0.5 — all four new
  audit guards pass on live data.
- fetch_interviews nickname classes: variant sets union-merged (ted∈{edward,theodore} bridges by
  design), FULL registration setdefault-first-wins, surname-scoped — no realistic collision in
  current roster; QA2 succession guard preserved.
- audit_full.py write-surface: only _audit_tmp_optimize/_audit_tmp_frontier temp probes (by
  design, gitignored) — read-only-safe classification still correct with the 3 new checks.

## Accuracy, condensing & optimization — psychology/behavior + sentiment (user-requested)

### Accuracy state of record (all numbers from repo docs/commits/meta artifacts, none re-derived)
**Sentiment/stance.**
- Tweets: production transfer 0.481 → Fable flat 0.616 → classical-on-golds 0.737 → registry
  two-hop 0.782 → **stack 0.850–0.855 acc / 0.816–0.819 macro-F1 honest OOF** (f8cc8ee). Corpus
  scored 9,559; tiers unanimous 2,644 / majority 6,170 / review 745 (7.8%). PRE-REGISTERED
  confirmation on the next fresh adjudication batch still OPEN.
- Press: DEBATE 0.796 all-gold / **0.571 adversarial** → **stack 0.837 / 0.765** (760-gold meta);
  tier trust measured unanimous .955 / majority .776 / review .638; production reader = Opus
  replica 0.779 goldeval (Fable flat 0.608–0.618). Blend wiring live: 100% stack coverage
  (1,569 signed, 0 DEBATE fallback), 30 unrelated zeroed, intensity non-degenerate (608 distinct
  pv), attribution channel 661 own @1.0 / 540 third-party @0.5 (PRESS_THIRD_W).
- Decomposition: stance-hop 0.915 (solved) / valence-hop 0.689 (the bottleneck); compose ceiling
  0.872 — the residual gap lives in the 5 skipped valence families (needs the user's 5-question
  review or direction-splits).
- Cross-media reference layer: negative-class precision 0.68 (all errors over-signed neutrals,
  0/50 inversions) — display red-gated at net<−0.4 accordingly.
**Psychology/behavior.**
- Lexical Big5 v1: split-half .60–.81, RKH convergence .42–.52 (method-shared), but MTMM FAIL
  (cross-genre .21–.28 < within-genre halo .27–.32) and **nomologically INDICTED** (pre-registered
  label-free battery: 5/8 primary signs, r_alerting −0.76, C REVERSED on participation, E =
  broadcast talkativeness). Composite INDICTED (3/8). Persona: right-signed 4/5 but |r|<.05.
  Sole survivor: lexical A→cooperation +.11 FDR-sig.
- Production fix (live, audit-guarded): receptivity on **behavioral dispositions** — validity by
  construction (criteria ARE the behavior); N remains text (no behavioral criterion exists).
- v2 behavior-calibrated text instrument: held-out r **A+.14 / C+.13 / E+.34 / O+.20** — every
  trait right-signed OOS, at/above the published closed-vocab ceiling (ρ .08–.14); desk radar now
  v2. v3 hybrid currently TIES v2 (interaction channel covers only 113 members pre-nickfix
  re-ingest — its real test is queued behind the running reingest).
- Ceiling-breaker on record: parked LLM item-level instrument (§1.4, ~$30 pilot; published
  zero-shot consensus ≈ .42–.44 — the only method class with headroom above the lexical ceiling).

### Condensing opportunities (report-only; nothing retired by the auditor)
1. Big5 instrument sprawl is now 7 artifacts (v1 traits, v2, v3_hybrid, llm pilot fragment,
   genre composite [scratchpad], persona, behavioral dispositions). PRODUCTION consumes only:
   dispositions (+ v1's N and tokens/lowconf; + persona channel). Candidates once v2/v3 are
   ratified: fold v1's remaining roles (N-source, desk fallback, featz for SMOreg) into v2's
   artifact and move v1 + composite to attic; retire big5_llm_sonnet.json pilot fragment (itemset
   superseded by v2 anyway) or fund the pilot and decide.
2. Stance classifiers: the tweet stack subsumes classical/registry/API-flat as FEATURES — keep
   (they are stack inputs), but the standalone stance_clf_composed.pkl audit check tests a
   component, not the production path; consider an audit check on tweet_stance_final.csv tier
   distribution instead (guards the actual consumed artifact).
3. Runtime: full chain ≈13 min observed (19 min worst-case cache-dead). Two known sinks: (a)
   openpyxl re-parses of the workbook (spec already names caching the frozen Legislative-
   Normalized sheet as the candidate); (b) audit_full re-runs optimize/frontier/scenario/route
   engines 2–3× each (~9 min standalone) — determinism probes could reuse the chain's own outputs
   as one leg instead of running both legs fresh.

### Optimization recommendations (user decides; ranked by measured headroom)
1. Valence-hop review (sentiment): the user's 5-question family review on the skipped valence
   families is the single highest-leverage step on record (0.689 → toward the 0.872 compose
   ceiling; everything else in the tweet path is already at 0.855).
2. Press adversarial frame: work the readjudication queue (press_gold_readjudication_queue.csv,
   63 KB) — 0.765 adversarial vs .955 unanimous-tier trust says the gap is concentrated where
   frames conflict.
3. Behavior: let the nickname-fixed reingest finish → rebuild interaction_features/behavior_panel
   → re-run the v3 hybrid promotion test (dominance/visibility coverage 113→full roster is the
   blocked variable); then the $30 LLM pilot as the only above-ceiling play.
4. Close the pre-registered confirmations: tweet stack on next fresh adjudication batch; persona
   gold sheet (30 members) unlocks persona + interaction channels' criterion.

## P4 — spec vs code (code presumed authoritative; reconciling NEITHER side; user decides)
1. MATHEMATICAL_SPECIFICATION.md §media-blend row: "press ALWAYS from press_raw_original.json
   cache" — code (build_media_blend.py, PRESS_DYNAMIC default ON since 7ab9ef0 + live stack
   wiring) builds the press component dynamically from cu_press_stance_tone.csv signed by
   press_stance_final.csv stack labels with channel weights. Spec row is one generation stale.
2. Spec §receptivity row: "susc = .40A+.30N−.20C−.10E; seed_prob = .60+.10A+.06O+.04E" — live
   code (behavioral basis default): susc = .40·cooperation+.30·N−.20·diligence−.10·dominance;
   seed_prob = .60+.10·cooperation+.06·breadth+.04·visibility. Lexical formulas remain as the
   RECEPT_TRAITS=lexical fallback only.
3. Spec §standing dials: missing PRESS_DYNAMIC (default 1), PRESS_THIRD_W (default 0.5),
   RECEPT_TRAITS (default behavioral) — all three are new ratified-default dials.
4. README §model layer 4: "Big Five from 6.6M words … → susceptibility" — susceptibility now
   behavioral (text Big5 supplies only N + desk radar); §Running says "52 checks".
5. run_pipeline.py CHAIN comment for receptivity still names big5_traits.py as the manual
   dependency; the load-bearing manual dependency is now behavioral_dispositions.py (ordering
   handled in weekly_refresh: dispositions before pipeline — same pattern as big5_traits).
6. Unchanged & verified against code: two-physics table, '—' ontology (PERS 0.45 / SGATE 0.85 /
   tier-exclusion), post-journey social formula, determinism contract (SEED 7 / MC 20 / sm64),
   workbook phase-2 contract, IMP/BLOCKCAT/CATBLOCKS tables, DTHRESH/MAXSHIFT/LOSSFRAME values.

