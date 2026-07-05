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

## Run-4h — persona gold validation: FAIL, and it strengthens rather than adds a new concern

The user rated all 30 blind excerpts (agency + communion, 1–9, full range used both axes — no
straight-lining). Pre-set bars (locked before any score was knowable): PASS ≥+0.30 both axes,
DIRECTIONAL ≥+0.15, else FAIL. **Result: agency rho = +0.035 (n=30, no discernible relationship),
communion rho = −0.245 (n=30, WRONG SIGN — the model's "warmer" scores correspond to text the user
rated LESS warm). VERDICT: FAIL on both axes**, communion by sign not just magnitude.

This is not a standalone surprise — it's the SECOND independent validation method landing on
persona as unreliable, via a completely different design: the label-free nomological battery
(big5_nomological_prereg.md) found persona "directionally consistent but magnitude-null" (right
sign, |r|<.05 on all 5 tests); this human-blind-rating test now finds one axis wrong-signed
outright. Two different methods (behavior-criterion correlation vs. blind human re-rating of the
same text) agree the channel isn't measuring what it's built to measure.

**Recommendation (not applied — PERSONA_W is the user's calibrated dial, same standing as every
other dial this campaign): reconsider PERSONA_W=0.30's place in the susceptibility blend.** Two
validation attempts, two different methods, zero support. The persona channel can still stand as a
*display-only* projected-persona note on the desk (already labeled as such), but mixing it 30%
into the actual pressure_mult/susc_z that drives money-targeting decisions is currently
unsupported by any evidence collected to date.

**Run-4h CALIBRATION (user pushback: "you can't use a human gold label for something like this,
too subjective unless you get thirty people") — partly sustained, verdict softened but not
reversed.** What's right in the objection: (1) at n=30, communion rho=−0.245 is NOT statistically
significant (Fisher 95% CI ≈ [−0.56, +0.13], p≈.19 two-tailed) — my "WRONG SIGN" framing
over-claimed a point estimate; the honest read is "somewhere between moderately negative and
weakly positive, centered below zero." (2) A single human rater IS a noisy criterion — published
observer-rating gold standards aggregate multiple raters precisely because single-rater
reliability for personality-from-text runs ~.4–.5; attenuation means even a genuinely valid
instrument would only be EXPECTED to show ~.2–.35 against one rater, so the pre-set .30 PASS bar
was harsh for this design (the .15 DIRECTIONAL bar was the fair one, and both axes missed it).
What the objection does NOT touch: the FIRST indictment (nomological battery) had no human rater
anywhere in it — it correlated persona against roll-call/cosponsorship BEHAVIOR and found all
5 pre-registered tests |r|<.05. So the evidence state after calibration: one clean method → null;
one noisy method → uninformative-to-null. Still zero positive support for PERSONA_W=0.30, but
today's test alone would not justify the dial change — the nomological null is the load-bearing
evidence. Cheap upgrades if the user wants a decisive test: (a) 3–5 raters on the same 30
excerpts (Spearman-Brown: 5 raters at single-rater reliability .45 → panel reliability ≈ .80 —
30 people not needed), or (b) the user re-rates 10 excerpts in a week to measure his own
test-retest reliability, which lets us disattenuate today's numbers properly.

## Run-4i — PERSONA_W: user-ratified KEEP at 0.30; removal recommendation WITHDRAWN after
## reading the three source papers the user provided (B&L PA'25, RKH PSRM'16, Yang ISR'23)

The user rejected the removal recommendation and directed a return to the original literature.
Read in full. The papers do not merely support keeping the channel — they show BOTH of this
session's validation tests applied the wrong standard, and that the channel already passed the
construct-appropriate validations at build time.

**What the papers establish.** (1) B&L 2025 (Political Analysis): agency/communion are PUBLIC
persona constructs under Brunswik's lens model — the paper explicitly states intrinsic-vs-
strategic influence on cues "cannot be determined" and that the measurement target is the
judgments observers form from cues. Its validation standard: trained-coder agreement (3 coders +
codebook + consensus loops reached only Krippendorff α .70–.78 on a TERNARY task), 18-unit
functional tests, and GROUP-LEVEL external patterns (party-level communion tracks CHES left-
right; Trump-Harris agency/communion reversal). No model exceeded F1 .80; the paper itself
says cues are fuzzy and "not all observers will use the same available cues in the same way."
(2) RKH 2016 (PSRM): elite personality is measurable from speech; surveys are infeasible and
selection-biased (response rate itself correlates with personality). (3) Yang 2023 (ISR):
measurement quality is the bottleneck, and text-based personality features materially improve
downstream forecasting — the utility warrant for personality channels in predictive engines.

**Why both of this session's tests were scope-mismatched.** The blind single-rater gold test:
one untrained rater doing 1–9 holistic ratings is far below B&L's own measurement floor (their
trained multi-coder consensus process topped out at α≈.72 on an easier task) — a near-zero
correlation was PREDICTABLE from the paper's framework; the user's "too subjective unless you
get thirty people" is functionally B&L's own multi-coder position. The nomological battery's
persona hypotheses (Agency→committee_leader, Communion→bipartisanship) imported INTRINSIC-trait
precedents; a projected-persona measure failing intrinsic-behavior criteria does not contradict
a construct that explicitly disclaims measuring intrinsic disposition. Meanwhile the channel's
construct-appropriate validations — the B&L 18/18 functional-gate replication and the party-
signature replication (communion D>R, matching the paper's own external-validity design) —
PASSED at build time and were under-weighted in this session's "zero positive evidence" framing.
That framing was the auditor's error: it demanded evidence of a kind the construct doesn't
claim, while discounting the evidence of the kind it does.

**What stands on the record.** The two test RESULTS remain as scoped facts: projected persona
did not predict those behavior criteria here (right-signed 4/5, magnitudes null), and one
untrained rater's blind readings did not correlate with the instrument. Neither is evidence
against the channel as designed and used (approach-styling + a 0.30 share of susceptibility,
where the persona IS what an approaching lobbyist meets). **PERSONA_W=0.30 is USER-RATIFIED
2026-07-04. Do not re-litigate absent new construct-appropriate evidence** (i.e., a multi-rater
panel run to B&L standards — 3+ raters, codebook, consensus — failing to converge with the
instrument).

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

---

# Run-4j — Literature-conformance audit (user: "full access to all my research articles… audit both them and then my model, and make sure everything is up-to-code")

**Method.** Cataloged every research PDF on the machine (repo `research/` ×2, Downloads ×76,
Desktop ×7; the three *Journal 3* PDFs are personal journals — excluded). Extracted 39 paper texts
to a scratchpad library (pypdf; image-only PDFs rasterized via PyMuPDF), identified every unknown
by page-1 text, then ran 4 verification agents (money/persuasion · salience/incentive ·
IM/cascade/route · text/network), each briefed with the exact code claims. **Every agent verdict
was re-checked against the actual code wording before acceptance — all four agents over-claimed at
least once** (calibration ledger below), so this matrix is the calibrated result, not raw agent output.

## Verdict: the model is up to code, with 3 sentences of over-attribution (now fixed)

Zero formula or constant changes are required by the literature. The citation practice is
overwhelmingly **honest-analogical** — papers are cited for settings, principles, and directions;
magnitudes are local calibration (and after run-4b, decision-robustness-bounded). The audit found
**3 comment-level over-attributions** and **1 venue error**, all fixed this run (comment-only,
compile-checked, no behavior change):

1. **Byrne attribution** (`receptivity_layer.py` docstring) — the code credited all four
   susceptibility trait directions to Byrne, Silasi-Mansat & Worthy (PAID 2015). The paper actually
   supports **N+ (replicated core result)** and **A+ (Exp-2 social-pressure interaction)** only;
   their E effect was **null** and their lone C signal was weak, unreplicated, and **opposite-signed**
   vs our −.20. The C−/E− dampeners are design priors; A-above-N ordering is the user's directive.
   Docstring now states exactly this and points to `receptivity_sensitivity.py` (9/9 variants
   top-20-stable, ρ≥.998) as the magnitude bound. Constants untouched. *Mirror note:* the live-tree
   behavioral-basis campaign (other session, uncommitted — see S2) analogizes the same composite to
   cooperation/diligence/dominance; the same attribution note belongs there when it commits.
2. **(1−1/e) guarantee scope** (`scenario.py` header) — the old sentence could be read as claiming
   the greedy guarantee for the *competitive cascade*. Calibrated truth: the guarantee covers the
   **allocator** objective (`optimize.py` — separable-concave money curve; G-K explicitly supports
   item costs + the data-dependent bound) and the **COALITION** side (follower-vs-fixed-opponent
   competitive IC **is** submodular — Bharathi-Kempe-Salek, the exact first-to-reach model the
   kernel implements). **FLIP** (competitive LT) has **no** general guarantee — Borodin et al.
   prove submodularity fails there — and the code never claimed one; `audit_frontier.py:18` already
   checks marginal non-increase empirically each run. Header now scoped.
3. **Chen venue** (`receptivity_layer.py`, `budget_frontier.py`) — "Chen et al. (ICML 2021)" →
   **UAI 2021** (arXiv 2106.07039, PMLR v161). The substantive use is honest as written: the code
   cites Chen for the contingency **setting** ("a lobbied seed takes with probability") and openly
   implements a simpler gate, not their RL solution. The committed-allies carve-out is a documented
   domain rule (ally parity), not presented as Chen's.
4. **Library hygiene** — scratchpad extract `rkh_book_excerpt.txt` renamed
   `steinert_threlkeld_twitter_as_data_excerpt.txt`: the Cambridge excerpt on disk (9781108438339)
   is Steinert-Threlkeld *Twitter as Data*, **not** the RKH book (my extraction mislabel; it briefly
   produced a false "fabricated citation" agent verdict — see calibration ledger).

## Conformance matrix (paper ↔ mechanism, calibrated)

| Source | Where used | Verdict | Note |
|---|---|---|---|
| Fink et al. 2023 (Data in Brief) | cascade kernel `build_P` + social-layer normalization | **SUPPORTED** | inverse map w=6p/(1−p) is exact algebra on their probability-of-influence; floor 25 / cap 0.25 are local calibration of their normalize-by-volume discipline (their 100-tweet floor was a membership filter) |
| Golovin & Krause (JAIR) | `optimize.py` adaptive allocator + bound | **SUPPORTED** | framework explicitly covers item costs (§2.4, §6) and the data-dependent bound (Lemma 5.3) the code prints |
| Bharathi-Kempe-Salek | COALITION competitive IC | **SUPPORTED** | follower's spread vs fixed opponent seeds is monotone-submodular — their theorem is the load-bearing one, and the kernel's first-to-reach coloring is their model |
| Borodin et al. | FLIP competitive LT | **SUPPORTED (as scoped)** | cited for the model, not a guarantee; no guarantee exists (Thms 1-2, hardness Thm 7) and none is claimed; empirical marginal check in `audit_frontier.py` |
| Chen et al. UAI'21 + Zareie-Sakellariou | contingency seed gate | **PARTIAL-ANALOGICAL (honest)** | setting adopted, RL solution not; venue fixed |
| Byrne et al. PAID 2015 | susceptibility composite | **PARTIAL: N+ A+ supported; C−/E− design priors** | comment fixed; magnitudes bounded by run-4b sensitivity |
| Fouirnaies & Hall (APSR) | incent_mult 0.60 retiring | **DIRECTION SUPPORTED** | their result is *effort/responsiveness*, not roll-call position change (their Table 5 = no position change); 0.60 magnitude is local |
| Linde & Vis (Pol.Psych) | pt_domain 1.15/0.92, LOSSFRAME 1.10 | **DIRECTION SUPPORTED** | reflection effect strongly found (39%→76% risky under loss framing) = pt_domain's basis; their loss-aversion test was inconclusive — LOSSFRAME leans on K&T attenuated per their elite-scale finding; magnitudes local |
| Noble-Turner 2024 | going-public shock engine | **STRUCTURE SUPPORTED** | defensive-appeals-hold finding is theirs (CCM holds 8); the b-formula numerics are calibrated-on-structure |
| Kalla & Broockman 2016 (on disk as `Hertel-Fernandez-2.pdf`) | money→access dampening | **SUPPORTED (as skeptic-for-low-weight)** | the model *encodes* "money buys access, not votes": MAXSHIFT 40→18, WM=0.35 minority partner; in user's bib (line 414) |
| Bakker-Lelkes-Malka (JOP) | cue receptivity (lt_priming branch) | **REPORT NOTE** | out-party cues can *backfire* (negative effect), not merely run weaker — when the stranded lt_priming branch merges, its cue channel should treat out-party cues as ≤0, not attenuated-positive |
| Furnas-LaPira-Hertel-Fernandez (PRQ) | messenger-alignment logic | **SUPPORTED (concept)** | "epistemic closure among partisan staffers" grounds persona-homophily gating; the user's own annotation names this application |
| Ramey-Klingler-Hollibaugh PSRM 2016 | `big5_traits.py`, `fit_smoreg_rkh.py`, shrinkage | **SUPPORTED** | all repo cites point to the correct 2016 article; the RKH *book* (committee-leader C criterion's source) is not on disk — cite-by-memory, and the criterion already did its job (it indicted lexical C) |
| Mairesse et al. JAIR | essays-fitted SMOreg Big5 | **SUPPORTED (canonical method)** | domain shift addressed by congress recalibration (`fit_smoreg_rkh.py`) |
| Birkenmaier & Lechner PA 2025 | persona channel (PERSONA_W=0.30, ratified) | **SUPPORTED (construct = projected persona)** | run-4i: both failed validations were scope-mismatched; functional gate 18/18 + party signature passed; user annotation: "highly relevant to the design of nodes" |
| Porter et al. PNAS 2005 | committee-cluster layout | **SUPPORTED** | normalized-interlock formula exact; centroid+jitter is implementation detail |
| Malaterre & Lareau 2024 | press HCoI | **SUPPORTED** | curated 19-cat in place of LDA is explicitly permitted ("the methods are agnostic as to which topic model is chosen"); D4 recovery test is an *added* validation |
| Zhou & Elejalde 2026 | stance_dynamics | **SUPPORTED (label-free port)** | trajectories, persistence, 7-way taxonomy, mirror flip-curves, masking protocol all faithful; no GNN and none claimed |
| Joo & Steinert-Threlkeld 2022 | frame_alignment | **PARTIAL-ANALOGICAL (labeled)** | image-duplication→title-duplication transposition is flagged in-code as an analog; the chi-squared party-association part is a direct port |
| Sotoudeh-Porter-Krishnagopal | dashboard pathfinder framing | **CONCEPT CITE** | "influence, not count, drives passage" is their thesis; their pass-weighted edge metric is not implemented (edges = curated network) — fine as concept attribution |
| Ren et al. MOPBD* / RELINK | `cosponsor_route.py`, scenario recompute | **CONCEPT CITE (honest)** | code self-describes as "Greedy"; "provably-optimal" appears only on the max-product Dijkstra path (tpl:311), where it is mathematically true |
| Ringe-Victor-Gross BJPS 2013 (*Friends/Enemies* — identified this run) | signed mention layer | **SUPPORTED (concept)** | legislators keep information ties with adversaries → the 449 negative reference edges are signal, not noise — exactly the layer's design |
| ABB26 Advocacy Priorities handout | kernel `IMP` weights | **SUPPORTED** | Protect tier (tax status, interchange, regulator) ↔ top weights 3.0/3.0–2.0/1.0; headline Advance/Empower asks at 1.0; unlisted specialties 0.1–0.75. One judgment note: Fraud Prevention (a headline Empower item) sits at 0.75 while Data Privacy holds 1.0 — defensible, user may want parity |
| Rice & Zorn PSRM | *(uncited)* | **LIBRARY-ONLY / opportunity** | their warning (off-the-shelf dictionaries fail specialized vocabularies) was independently *confirmed* by this project (lexical Big5 indicted; stance moved to trained stack + curated registry); their GloVe+seed induction pairs naturally with the Park 2025 direction-aware lexicon plan |
| Park, Lee & Cho 2025 | *(planned)* | **NOT YET IMPLEMENTED** | direction-aware lexicon remains the ratified upgrade path for valence v2 |
| Merkley-Stecula, Pritoni et al. (coalitions), Huneeus-Kim, Kim-Kunisky, Bacik et al., Jacoby et al., Alexander et al. 2009, Bickmore et al. 2025 (identified this run), Kim (Jiseon) et al., Kamarthi et al., Taherdoost | *(uncited / roadmap)* | **LIBRARY-ONLY** | present in the user's bib with intended roles (data pipelines, ROI anchors, coalition theory); nothing to conform to yet |

## Agent-calibration ledger (raw verdicts I overruled, and why)

- **Agent B "CRITICAL: Borodin contradiction"** → *dismissed as stated.* No module claims (1−1/e)
  on competitive LT. The submodularity claims live on the allocator (separable-concave) and the
  IC follower side (B-K-S theorem). Residue kept: the scenario.py wording ambiguity — fixed.
- **Agent B "D\*Lite misattribution / PROVABLY-OPTIMAL over-claim"** → *dismissed.* The phrase is
  attached to the max-product Dijkstra path (a true claim), not the greedy route builder, which
  self-describes as greedy. D\*Lite/MOPBD\*/RELINK are principle-level roadmap cites.
- **Agent B "Chen solution decoupling"** → *downgraded to a venue fix.* The code never claims
  Chen's RL mechanism — it cites the setting and documents its own gate.
- **Agent D "CRITICAL: RKH citation fabricated"** → *dismissed; my fault upstream.* The agent was
  handed a mislabeled excerpt (Twitter-as-Data filed as rkh_book_excerpt). All repo cites point to
  the correct PSRM 2016 article. Residue: the RKH book itself is not on disk (noted above).
- **Agent D "0.55 bar undervalidated vs their κ≈.84"** → *dismissed as category confusion.* κ is
  human-annotator agreement on labels; 0.55 is a barely-above-chance *screen* that prints
  "null: no homophily" when co-movement fails it. It gates a diagnostic line, not the pipeline.
- **Agent D "Rice-Zorn dismissed by the model"** → *reframed.* Rice-Zorn is uncited; nothing is
  misused. Logged as an opportunity (matrix row above).
- **Agent A "model contradicts money-buys-access-not-votes"** (prior round) → *inverted.* The model
  *implements* the skepticism as dampening (MAXSHIFT 18, WM=0.35).
- **Agent C "loss aversion unsupported"** (prior round) → *split.* Linde-Vis couldn't validly test
  loss aversion (null ≠ absent); the *reflection effect* was strongly found and is what pt_domain
  encodes.

**Bottom line:** after calibration, the literature audit produces **no S1/S2 findings**. The three
over-attribution sentences are fixed; magnitudes everywhere are labeled local calibration and are
either sensitivity-bounded (receptivity, run-4b) or pre-registered for outcome scoring (snapshot,
run-4c). One forward-looking item for the user: **when the lt_priming branch merges, sign the
out-party cue channel per Bakker-Lelkes-Malka (backfire, not attenuation).**

