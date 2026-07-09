# A & ES round 2 — dialogic assent, sex-relative voice, NPAT criterion (pre-registration)

**Locked 2026-07-09 BEFORE any look (user-directed: "Fix A and ES"; mechanisms proposed by Paul —
sex-RELATIVE vocal inflection for ES, assent/accommodation language for A). Three INDEPENDENT tests,
each ONE look, bars immovable after data seen. Compliance: none is a CT-CM/halo re-spec (stopping
rule respected); each uses a genuinely new feature basis or new external criterion; nothing is wired
into engines (display/validity layer only). The gender/party partial is now a GATING bar wherever
applicable — the ES-confound lesson institutionalized, not repeated.**

## Motivating evidence (computed pre-lock, $0, no look consumed — external instruments / criterion-side only)
- Criterion structure: corr(cooperation_z, breadth_z) = **+0.708** (volume common cause: 2 of
  cooperation's 3 components are cosponsorship volume) — why A's dominance bar is intrinsically hard;
  diligence is near-orthogonal to cooperation (+0.094), so pred_A reading diligence (+.210) in the
  3/5 round was feature-level cross-loading, exactly what an assent basis targets.
- RKH hou114 LIWC **Assent** (floor-speech MONOLOGUE, n≈126 joined): r vs cooperation_z = +0.013,
  diligence_z +0.023, bipartisan-ratio +0.069, visibility_z +0.136. Floor-speech assent does NOT
  track cooperation — evidence AGAINST a monologue-assent route and FOR restricting to DIALOGUE
  (interview turns), where assent is a responsive move. Prior lowered accordingly; hypothesis (Paul's)
  unchanged: dialogic accommodation ("that makes sense", "sure", "I understand") is the A-specific act.
- NPAT pre-check on RKH's OWN traits (HouseNPATwithPers.tab, 997 rows, 349/648 respond): Emoti is the
  STRONGEST trait predictor of votesmart_respond (+0.063; others ≤ +0.031) → the locked ES-specificity
  precondition PASSES on the field's instrument; a-priori SIGN fixed **positive** (stable → responds).
  Power honesty: current-roster overlap n≈155 (67 responders); r_crit(.05, one-sided) ≈ .13; if the
  true effect ≈ RKH's .063, the expected outcome is MISS — a MISS closes the NPAT route for the
  current roster (the powered path would be a fresh full-roster Vote Smart pull, user-gated).
- The repo's existing 'agree' feature (interaction_features.py:30) is DEAD BY MECHANISM: its regex
  requires an ENTIRE turn to be a bare assent token while ingest drops all turns <8 words — it can
  never fire. No assent lexicon exists anywhere in the repo (grep=0) → new feature basis, as round-2
  blue's stopping rule demands. Corpus: INTERVIEW turns now 117,322 / 512 members (3.8x the 07-04 snapshot).

## TEST A — dialogic-assent Agreeableness instrument
**Data:** INTERVIEW member turns (social_media.db, source='INTERVIEW'; program = the show slug stored
in the `chamber` column — NOT interaction_features' program_of(), which pools CBS/ABC/Fox/Hewitt into
'other'). Members with ≥20 turns total AND full criterion coverage — ≈321 before the per-program
floors below; the floors (≥12 member-turns per program row, ≥8 members per program) bring the
working roster to ≈242 (exact N reported in the RESULT; r_crit(.05, one-sided) ≈ .106 at N=242, so
the +.15 bar remains properly powered).
**Features (FIXED a-priori, verbatim; all rates, no volume terms; per-(member,program) computed on
programs with ≥12 member-turns, z within program across members on programs with ≥8 members,
turn-weighted member aggregate — the interaction_features normalization doctrine):**
1. `assent_initial` — share of turns whose first 4 tokens contain an assent token. Unambiguous tokens
   (bare): exactly, absolutely, agreed, certainly, indeed, of course, yes, yeah. Ambiguous tokens
   (require immediate `,` `.` `!` `—` `-` after the token to avoid "right now"/"sure to"): right,
   sure, true, correct, fair enough, that's right, that's true, no doubt.
2. `assent_phrases` — per-1k-words count of: that makes sense | makes sense to me | i agree |
   i couldn't agree more | could not agree more | you're right | you are right | you're absolutely
   right | that's a fair point | fair point | good point | great point | well said | i understand |
   i hear you | i take your point | point well taken | i see your point | you make a good point |
   that's exactly right | i think that's right | no question | without question.
3. `concession` — per-1k-words: to be fair | i'll grant | granted, | look, i understand | i get it |
   i get that | you're not wrong.
4. `gratitude` — per-1k-words: thank you | thanks for having | i appreciate | grateful.
5. `disagreement` (negative pole) — per-1k-words: i disagree | i don't agree | that's not true |
   that's wrong | that's false | that's not right | no, no | with all due respect | let me push back |
   i take issue | that's ridiculous | nonsense | couldn't disagree more | that's simply not |
   that's just not.
6. `defense` (negative pole) — the existing interaction_features DEFENSE regex verbatim (let me
   finish | may i finish | i'm not finished | if i could just finish | hold on | wait a
   minute/second | as i was saying | excuse me, i/let), per-1k-words. [tagged dom+/A− in-repo]
7. `llm_communion`, 8. `llm_agency` — the production B&L cue-shares (agency_communion.json, n≥15;
   others mean-imputed), roster-z. [precedent: features in big5_traits/big5_hybrid]
**Model:** ridge, nested CV (alphas [1,3,10,30,100,300,1000], outer 5-fold × seeds [7,17,29,43,61],
out-of-fold), identical to the instrument round.
**Bars (ONE look, ALL must hold):**
- A1: held-out r(pred, cooperation_z) ≥ **+0.15** AND exact perm-p (5000 label perms vs fixed OOF
  preds, seed 20260709) < .05;
- A2: **diagonal-dominant** — |r(pred, cooperation_z)| is the max over {cooperation, diligence,
  breadth, visibility, residual-GMP} (abs semantics, own r > 0), same as the 3/5 round;
- A3: **confound partial (GATING)** — partial r(pred, cooperation_z | gender, party) ≥ **+0.10**
  with exact perm-p < .05.
**Reported, non-gating:** r vs the volume-free bipartisanship RATIO; per-feature criterion
correlations; side-by-side vs the Empath-A row (+.183, not dominant).
**MISS ⇒** the dialogic-assent route is CLOSED; A stands as criterion-valid-but-not-distinct.

## TEST E1 — sex-relative voice ES (Paul's inflection mechanism)
**Data:** the 395 verified voiceprints (b5_audio_cache z, 88 eGeMAPS). **Features: each of the 88,
OLS-residualized on [1, gender], re-standardized** — every feature becomes "relative to your sex's
baseline" (a monotone-for-a-woman reads as monotone). **Target: big5_v2-ES residualized on
[1, gender, party], re-standardized** (discriminant comparator big5_v2-A residualized identically).
**Model:** identical ridge nested-CV protocol. **This is the configuration never tried** — the
gender-robustness look only partialled the OLD (sex-confounded) model's predictions; training on
sex-relative features reallocates all model capacity to within-sex variance.
**Bars (ONE look, ALL must hold — the original cross-modal bars, sex-clean by construction):**
- E1a: held-out r(pred, ES_resid) ≥ **+0.15**, right-signed;
- E1b: exact perm-p (5000, seed 20260709) < **.01**;
- E1c: discriminant r(pred, ES_resid) > r(pred, A_resid).
**Honest prior: LOW** (the old model's within-sex correlations were null both sexes; F=113 caps the
female stratum's information). **MISS ⇒ the voice-ES route is CLOSED PERMANENTLY** (this is the
pre-declared final voice attempt; no further audio-ES work of any kind without new data of a
different modality).

## TEST E2 — NPAT survey-response criterion for text-ES (the recorded last-standing ES criterion)
**Data:** fec/liwc/rkh/HouseNPATwithPers.tab votesmart_respond (0/1; 349/648), joined
icpsr→bioguide→member (HS119_members.csv → congestion.json); current-roster overlap n≈155
(House-only; provenance note: the two NPAT .tab files are not in fetch_rkh_data.py — pulled manually
2026-07-08; a fetch entry should be added). NPATrespICPSR.tab is a parse-audit-flagged sidecar; used
only if its clean 0/1 rows RAISE n (reported either way).
**Instruments tested (fixed):** PRIMARY = big5_v2 ES; SECONDARY (reported) = Pink raw_z ES.
No training/CV — these are existing scores vs an external binary criterion (point-biserial).
**Bars (ONE look, ALL must hold, on the PRIMARY):**
- E2a: point-biserial r(v2-ES, respond) ≥ **+0.15** with the pre-fixed **positive** sign AND exact
  perm-p (5000, seed 20260709) < .05;
- E2b: **ES-specificity** — |r| for v2-ES exceeds |r| for v2 O/C/E/A vs the same criterion;
- E2c: **confound partial (GATING)** — partial r(v2-ES, respond | gender, party) ≥ **+0.10**,
  perm-p < .05.
**MISS ⇒** the NPAT route is closed for the current roster; the only remaining ES path is a fresh
full-roster Vote Smart pull (external data collection, user-gated) — documented, not attempted here.

## Discipline
Locked + committed BEFORE any look. Lexicons/models/criteria fixed above; no feature search, no bar
movement, no re-runs after unblinding. Machinery validated by `--simulate` (planted-signal recovery
+ permuted-null calibration per test) before each look. Looks gated on this file lacking the
matching '## RESULT-A' / '## RESULT-E1' / '## RESULT-E2' heading (heading-match, the hardened gate).
Each test's outcome is recorded verbatim under its RESULT heading, MISSes included. Any PASS is
adversarially re-derived before promotion of any claim. Fable/Haiku cost rule: no LLM calls anywhere
in this round (lexicon + arithmetic only).

## RESULT-A — THE ONE LOOK (2026-07-09, N=242; machinery pre-validated: planted r=+.52 recovered, null 0-pass, confound killed)
**MISS on all three bars.** Row: cooperation **−0.231** | diligence −0.080 | visibility +0.052 |
breadth −0.256 | residGMP −0.025; exact perm-p = 1.0000 (the negative OOF r is the standard CV-null
artifact — there is no recoverable linear signal). A3 partial −0.242 (p 1.0). Secondary:
pred vs bipartisan-RATIO −0.044. **Per-feature diagnostics (the informative part):** turn-initial
assent is RIGHT-SIGNED vs cooperation (+0.074) — Paul's directional hypothesis has a trace — but
assent_phrases sit at +0.003 and nothing exceeds |.08| vs cooperation; llm_communion's largest
correlate is diligence (−0.170), not cooperation. **Dialogic-assent route CLOSED** (matches the
pre-lock probe: RKH floor-speech Assent was also null vs cooperation, +.013). A's honest label is
unchanged: criterion-valid (+.183, Empath instrument) but NOT discriminant; the assent mechanism is
now tested-and-closed rather than open speculation.

## RESULT-E1 — THE ONE LOOK (2026-07-09, N=395, F=113/M=282; sex-residualization exact to 1e-6)
**MISS.** Held-out r(pred, ES_resid) = **−0.024**, exact perm-p = 0.6767 (E1c vacuously CLEAR:
−0.024 > −0.041). Training on sex-relative features against a sex/party-residualized target finds
NOTHING — confirming the robustness look's within-sex nulls were the true state, not an artifact of
sex-confounded training. **The voice-ES route is CLOSED PERMANENTLY** (pre-declared: this was the
final voice attempt). The full voice-ES record: raw +.208 (gender-confounded) → within-sex null →
sex-relative retrain null.

## RESULT-E2 — THE ONE LOOK (2026-07-09, N=171 current members, 67 responders, +16 from the sidecar)
**MISS on all three bars.** r(v2-ES, respond) = **−0.042** (wrong-signed vs the pre-fixed + sign;
perm-p .70); ES-specificity FAILS (v2-E carries the largest |r|, −0.072; O +.010, C +.011, A −.017);
partial +0.008 (p .47). Secondary: Pink-ES −0.062 (p .80, n=167). **The NPAT route is closed for the
current roster.** Context: RKH's own in-sample Emoti↔respond was only +.063 (n=997), so even perfect
transfer was below our bar at n=171 — the pre-lock power warning realized. The one remaining powered
ES path is a fresh full-roster Vote Smart PCT pull (533 members via legislators.csv votesmart_id) —
external data collection, user-gated, NOT attempted here.

**Round-2 net: 0/3 — both user-proposed mechanisms (dialogic assent for A, sex-relative inflection
for ES) were the right untested configurations and are now closed with recorded evidence. ES has
exhausted every in-repo route (text near-miss, GMP invalid, residual-GMP not dominant, affect
lability invalid, voice confounded→null, NPAT null/underpowered). Grade A− unaffected (these were
candidate ADDITIONS that did not pass; nothing shipped changes).**
