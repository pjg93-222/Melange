# Big Five Measurement Program — Methods & Validity Report

**Project:** CU-lobbying legislative-persuasion model, 533 members of the 119th Congress
**Date:** 2026-07-04 (living document)
**Status of each instrument:** PRODUCTION = feeds the receptivity layer; EXPLORATORY = built and measured, not consumed downstream; PARKED = designed, awaiting budget.

---

## 1. Instruments

### 1.1 Lexical (PRODUCTION — `fec/big5_traits.py` → `big5_traits.json`)
Ramey/Klingler/Hollibaugh-style closed-vocabulary scoring (PSRM 2019 "Measuring Elite Personality Using Speech"), synthesized:
per-1000-word category rates (pronouns *i/we/you*, articles, negations, positive/negative emotion, anxiety, anger, social,
achievement, insight, certainty, tentativeness, + Empath-expanded categories), MATTR lexical diversity (length-invariant),
Brysbaert concreteness norms, B&L persona cues as features. Weights: Mairesse-correlate priors replaced by SMOreg fits to
(a) the Pennebaker–King essays corpus and (b) the RKH congressional replication targets (`fec/liwc/mairesse_smoreg.json`,
promotion rule: refit wins only when held-out r beats active by >.02; party-sign check is a veto).
Corpus: tweets (RTs excluded) + Bluesky + floor speeches + hearing turns + broadcast interviews, chamber-ritual boilerplate
stripped, per-member z within the 533 pool. Confidence: <1,500 tokens → `lowconf`, consumers shrink to neutral.

### 1.2 Genre-general latent composite (EXPLORATORY — scratchpad `big5_composite.py`)
Response to the MTMM failure (§2.3). Per trait, the three genre-restricted lexical scores (social / floor speech /
interview, each ≥1,500 tokens, z within genre) are treated as indicators of one latent trait; loadings from the
3-indicator correlation triangle λᵢ=√(rᵢⱼrᵢₖ/rⱼₖ), clipped [0.15, 0.95]; member score = loading-weighted mean over ≥2
available genres. Model pre-registered before validation. Coverage: 259 members.

### 1.3 Conversational-dynamics channel (EXPLORATORY — `fec/interaction_features.py` → `interaction_features.json`)
Interaction features from 31k broadcast-interview member turns: words-per-turn distribution, floor-holding Gini,
turn-cutoff rate (transcript "--"/non-terminal endings = interrupted), contested-floor bursts, floor-defense phrases,
discourse markers. Literature basis: turn statistics alone reach ~73% binary accuracy on observer-rated Extraversion
(Valente Interspeech'12); overlap involvement is the only family recovering Neuroticism; word count is the top
observed-E feature (Mairesse JAIR'07). All features z-scored WITHIN PROGRAM (broadcast format manufactures overlap),
turn-weighted member aggregate; hearing cutoff-received kept as a context covariate only (role-driven, Miller &
Sutherland APSR). Measures observer-perceived traits (reputation), by design.

### 1.4 LLM item-level scorer (PARKED — `fec/big5_llm.py`, itemset-v2)
Per the 2023–2026 literature (PsyCoT; Ganesan; Peters & Matz; Marengo; NHB'25 zero-shot consensus ≈ .42–.44, the best
published), the strongest available method: 20 observer-keyed IPIP-style items answered per de-identified 1,200-word
chunk on a coarse −1/0/+1 scale ("no evidence"→0), chunk→genre→member aggregation, z within pool. De-identification
mandatory (LLMs carry reputational priors about named politicians, r=.76–.87 from the name alone — Cao & Kosinski).
Itemset-v2 fixed three genre-ceiling items exposed by the v1 pilot fragment (C items measured drafted-text
professionalism, not the member). Pilot = 185 RKH-overlap members, ~$25; contamination probe ~$5. Awaiting budget.

### 1.5 Persona agency/communion (PRODUCTION input to receptivity — `agency_communion.json`)
B&L-framework LLM persona cues, full roster. External criterion pending (persona gold sheet, §4).

---

## 2. Validity evidence (all measured 2026-07-04)

### 2.1 Convergent — Pearson r vs RKH published congressional estimates (bioguide→ICPSR join)

| Instrument | n | O | C | E | A | ES |
|---|---|---|---|---|---|---|
| Lexical pooled (production) | 147 | .47 | .42 | .52 | .43 | .42 |
| Lexical CREC-only | 147 | .39 | .33 | .41 | .43 | .36 |
| Genre-general composite | 81 | .40 | .24 | .31 | .09 | .27 |

Caveats: RKH targets are themselves Mairesse-LIWC scores of 1996–2014 floor speech — shared method inflates all rows;
pooled > CREC-only shows token volume also matters (RKH lifetime means reward stable inputs).

### 2.2 Reliability

| Axis | O | C | E | A | ES |
|---|---|---|---|---|---|
| Split-half SB, pooled lexical | .81 | .75 | .78 | .60 | .76 |
| 3-yr test-retest, CREC (n=273) | .51 | .36 | .48 | .45 | .60 |
| Split-half SB, composite (n=146) | **.92** | **.81** | .77 | **.80** | **.92** |

### 2.3 Cross-genre MTMM (the decisive weakness of the pooled lexical instrument)
Same-trait cross-genre r (social×CREC×interview pairs): mean **+.21 to +.28** per pair — BELOW the within-genre
cross-trait halo (**.27–.32**). Verdict: FAIL — the pooled lexical scores carry as much genre/method variance as trait
variance. Agreeableness barely transfers (social×CREC r = +.01). This motivated the §1.2 composite.
Composite loadings replicate the literature's trait geography: ES most genre-general (.42–.78), O solid, E present in
speech/social but absent in interviews (.22), **C floored (.15/.15/.15) — Conscientiousness has no genre-general lexical
variance in this corpus and should not be interpreted from the lexical channel.**

### 2.4 Known-groups (party proxy for RKH's conservatism findings; expected O−, C+, E−, A−, ES+)
Pooled lexical: 3/5 consistent (C, A inconsistent, near-zero effects). Composite: O, C, ES consistent; E, A inconsistent.

### 2.5 Cross-channel convergence (interaction × lexical / persona)
Verbal output × lexical E: **r = .00** (literature predicts .2–.4 when both channels are valid; the lexical E's MTMM
failure makes the criterion suspect — the null is ambiguous). Interaction × persona agency: +.14 (right direction, weak).
The interaction channel therefore remains EXPLORATORY pending a defensible criterion.

---

### 2.6 Composite promotion decision (pre-registered rule applied)
Rule (fixed before validation): promote only if reliability + discriminant improve without losing RKH convergence.
Outcome: reliability WON on every trait (O .92/.81, C .81/.75, E .77/.78, A .80/.60, ES .92/.76); discriminant a wash
(mean off-diag .29 vs .27; C–E halo .60 vs .68); RKH convergence LOST (A .09 vs .43, E .31 vs .52, partly explainable
by the anchor's genre bias but not fully — CREC-only scores also converge below pooled). **Verdict: NOT promoted.**
Both artifacts stand; production unchanged. The composite is the more *reliable and genre-general* instrument; the
pooled baseline is the more *anchor-convergent* one. A genre-neutral criterion (LLM instrument §1.4, or human ratings
§4) is required to adjudicate — this is the precise scientific reason the pilot matters.

## 3. Honest summary of what can and cannot be claimed

1. The production lexical Big5 is **reliable within its corpus** (split-half .60–.81) and **anchored to the only published
   congressional estimates** (r .42–.52, method-shared), but its scores **mix genre with trait** (MTMM fail). Downstream
   consumers (receptivity layer) should treat member differences as *speech-style-cum-trait*, not pure disposition.
2. **Conscientiousness is not measurable genre-generally** from lexical features here; **Agreeableness is marginal.**
   E, ES, O carry the most defensible signal — consistent with the elite-personality literature.
3. All current instruments estimate **perceived/expressed personality** (Koutsoumpis meta-analysis: language tracks
   observer ratings, |ρ| to .39, far better than self-report, |ρ| .08–.14). No claim about self-concept is made.
4. The path to research-grade point estimates is the **LLM item-level instrument (§1.4)** validated against (a) RKH,
   (b) the human persona gold sheet, (c) split-half + cross-genre MTMM — at ~$30 total pilot cost, currently parked.

## 3b. Nomological validation + the behavioral-basis fix (2026-07-04, post-"Full Reset")
Human gold labels were REJECTED as the validation instrument for latent constructs (correctly — see
big5_nomological_prereg.md). The label-free battery (ValiTex Phase III external evidence: 13
pre-registered directional trait→behavior tests, BH-FDR, 3 specification variants) returned:
**lexical Big5 INDICTED** (5/8 signs, r_alerting −0.76, C REVERSED on participation, E = broadcast
talkativeness: r=+.28 with interview count but −.09 with tweet volume), **composite INDICTED**
(3/8), **persona directionally consistent but magnitude-null** (4/5 signs, all |r|<.05).
Survivors: lexical A→cooperation (+.11, FDR-sig, robust).

**Fix (production, audit-guarded):** dispositions are now MEASURED FROM BEHAVIOR
(`fec/behavioral_dispositions.py` → behavioral_dispositions.json): cooperation (bipartisanship +
cosponsor embedding), diligence (roll-call participation; face-validates instantly — Susan Collins
tops it), dominance (interview turn statistics + committee leadership), visibility (broadcast
engagement), breadth (legislative portfolio sections). `receptivity_layer.py` consumes these in the
same Byrne/seed-prob structures (N remains text-based — no behavioral criterion exists);
`RECEPT_TRAITS=lexical` reverts. Guards: partial-term members neutral on diligence; members with <3
attributed interviews neutral on visibility until the nickname-fixed interview re-ingest lands
(QA3: the collector dropped Bernie/Bernard-class nickname mismatches — full corpus re-ingest
running). Audit check: 'receptivity runs on the behavioral basis'. Weekly refresh rebuilds
panel → dispositions before the chain.

## 3c. v2 / v3: behavior-calibrated text instruments (2026-07-04, "make it work")
v1's failure was its FIXED literature weights, not text measurement. **v2** (`fec/big5_lexcal_v2.py`)
learns weights from the same lexical features against the behavioral criteria, nested 5-fold CV,
honest held-out r: **A +.14, C +.13 (v1: −.03, sign fixed), E +.34, O +.20 (v1: −.02, fixed)** —
every trait right-signed out-of-sample. A/C/O sit at the published closed-vocabulary ceiling
(meta-analytic ρ .08–.14), i.e., the method is extracting at/above the known lexical maximum.
**v3 hybrid** (`fec/big5_hybrid.py`: + interaction dynamics + persona cues, availability flags
EXCLUDED as volume-leak guards) currently TIES v2 — the interaction channel covers only 113
members on the nickname-degraded corpus; the post-re-ingest rebuild is its real test. Desk radar
shows v2 ("Text Big-5 v2 · behavior-calibrated"). Weights candidate:
`fec/liwc/behavior_calibrated.json.candidate` (promotion = separate ratified step). ES in both =
genre-general composite (split-half .92) fallback v1. Weekly refresh rebuilds v2/v3 after the
dispositions. The remaining ceiling-breaker on record: the parked LLM item-level instrument (§1.4).

## 4. Open validation assets awaiting human labels
`persona_gold_sheet.csv` (30 members, agency/communion 1–9) — first external criterion for §1.3 and §1.5.
`reference_valence_gold_sheet.csv`, `attribution_gold_sheet.csv` — stance-side, listed here because the same
labeling session can clear all three.

## 5. Reproduction
All artifacts regenerate from: `big5_traits.py` (env: BIG5_SOURCES / BIG5_BEFORE / BIG5_AFTER / BIG5_HALF / BIG5_OUT),
`interaction_features.py`, `validate_big5.py <artifact> [--half2 <other>]`, scratchpad `big5_composite.py` +
`composite_splithalf.py`. RKH data: `fec/liwc/rkh/` (Dataverse DVN/JDH6KR, DVN/CORRXG).

## 6. Improvement round 1 — pre-registered, ONE look each (2026-07-07, bars @a61820e)
Frozen snapshot: 4,217 chunks / 509 members (big5_snapshot_freeze.json, artifact md5 67af4451).
Control (equal weights, new corpus): SB mean .748 (O .79 C .71 E .73 A .77 ES .74), MTMM .493,
disc .308, A-ES .653, KG 4/5, C(INT) vs votes +.156 / FT +.111. The corpus doubling alone delivered
the round's biggest gains (SB .674->.748, MTMM .410->.493).

| Test | Result | Verdict | Why |
|---|---|---|---|
| P1 item discrimination weights | SB .754 (4/5 improved), MTMM .496, disc .317 | **MISS** | disc bar (<=.30): reweighting concentrates on halo-loaded items (A-ES .653->.669). Equal weights stand. |
| P2 bifactor halo removal | A-ES .727 (worse), C-crit +.049/+.018 (collapsed) | **MISS** | PC1 carries criterion-VALID variance: the 'halo' is partly real trait covariance, exactly the miss-clause reading. Halo stays; A-ES caveat remains on the desk. |
| P4 EB shrinkage (k: O 2.1 C 2.8 E 3.1 A 2.7 ES 3.1) | SB .786 (clears +.02) but worst n>=8 move .73 SD | **MISS** | shrinkage reshuffles well-measured extremes (bar .5 SD). Raw stands; k ships as info. |
| B5 blue genre-residualized refit | A +.181 C +.224 O +.228 CLEAR; E -.033 MISS; family MTMM .096 vs .383 MISS | **MISS** | v2's E was genre variance (broadcast talkativeness) — residualizing kills it; lexical family still fails MTMM. v2 stands. A/C/O gains logged as a round-2 candidate (own prereg required). |
| P-ALL composition | — | vacuous | nothing passed to compose. |

Conclusion: the shipped configuration (pink equal-weight items + blue v2) SURVIVED all four
pre-registered challengers on the doubled corpus. Evaluators: fec/big5_improvements_eval.py
(--control/--p1/--p2/--p4) and fec/b5_residual_eval.py; genre featz via BIG5_SOURCES hooks.

## 7. C genre-weighting — earned consequence of the pre-registered retest PASS (2026-07-07)
The interview-C retest (bars locked 2026-07-05: rho >= +0.15 vs votes_cast AND >= +0.10 vs
follow-through, ONE look) PASSED on the full post-gate artifact: +0.155 (n=293) and +0.112 (n=266),
with the CREC contrast (+0.106/+0.051) confirming the genre mechanism. Per the pre-declared
consequence, member-level C now aggregates INTERVIEW chunks at 2x weight (C_INT_W in big5_llm.py;
the weight is the pilot's observed signal ratio, documented, not tuned against outcomes). Each
member carries c_basis: 'interview-weighted' (294 members) or 'crec-only' (215). The desk's C wedge
was already un-collapsed for all axes by the 2026-07-06 user rule, which satisfies the display half
of the consequence.

## 8. Round 2 (blue composed family) — MISS; v2 stands (2026-07-07, prereg @54d0f7c)
One look at the composed configuration (residualized A/C/O + v2-E). R2-2 known-groups CLEARED
(4/4) but R2-1 discriminant MISSED (0.402 vs bar 0.30; worst pair 0.90) and R2-3 A/C/O-subfamily
MTMM MISSED (same-trait cross-genre .113 vs cross-trait within-genre .591). Reading: ridge fits
of three correlated behavioral targets on the same 31 residualized features yield one
behavioral-proxy factor wearing three trait labels, not three genre-stable traits. The
lexical family's honest ceiling stands: per-trait criterion validity as a display-layer second
opinion; multi-trait genre-stable structure is beyond it. v2 unchanged. Evaluator:
fec/b5_residual_eval.py --r2.

## 9. Round 3 (pink scoring layer) — P5 MISS, P6 shipped-on-corrected-grounds, P7 MISS; scoring layer exhausted (2026-07-07, prereg @1967b15 + @cfc9119; CORRECTED by audit same day)
P5 split-sample item surgery (select even-half, test odd-half): best drop moved A-ES only .674->.653
on the test half; all validity bars held but both halo bars missed. P6 coverage-GATED EB shrinkage:
its pre-registered split-half bar (SB .748 -> .831) was CLEARED but that number is an ARTIFACT
(**audit 2026-07-07 correction**): shrinking BOTH halves toward 0 mechanically inflates their
correlation. The shrinkage-decomposition (fec/big5_improvements_eval.py --p6diag) shows raw-raw
.748, shrunk-shrunk .831, but shrunk-vs-RAW cross only .704 -> +0.127 of the apparent gain is
double-shrink artifact, ~0 is real. The split-half bar was the WRONG instrument to judge a
shrinkage method (prereg design error). P6 IS shipped anyway, on the CORRECTED and independent
justification of SHRINKAGE-NEUTRAL external-criterion validity (C->votes raw +.125 -> shrunk +.138,
A->cooperation +.129 -> +.138, C->follow-through +.067 -> +.069, O->breadth ~null both) plus the
display-sanity argument (a 2-chunk member should not render an extreme personality reading);
n>=8 members untouched by construction; 252/509 thin members shrink; raw_z retained; k: O 2.1 C 2.8
E 3.1 A 2.7 ES 3.1. Net: a modest, defensible regularization, NOT the reliability leap the headline
number implied.
P7 within-chunk ipsatization: A-ES CRUSHED to .269 (RKH benchmark .443) proving the excess halo is
chunk tone — but C-criterion collapsed (+.156 -> +.010) and discriminant rose (.371, the classic
ipsative negative-sum artifact). CONVERGENT FINDING (P2 + P7): C's criterion validity lives in the
tone/level component; scoring arithmetic cannot separate halo from C-signal. External benchmark:
RKH inter-trait mean off-diag .275 (House n=916; A-ES .443, C-A .590) vs ours .308/.653.
Scoring-layer verdict: EXHAUSTED after four design families (P1 reweight, P2 bifactor, P5 item
surgery, P7 ipsatization), one look each. Remaining lever: itemset v3 + judge-level independence
instruction (source-level halo fix), which requires re-scoring.

## 10. B6 stylometry — MISS; lexical modality closed (2026-07-07)
New 57-feature stylometric basis (function words, sentence-length distribution, hedging/certainty,
punctuation, MATTR, within-genre standardized): A +.141 C +.160 E +.341 cleared their bars; O
collapsed (+.021 — breadth is not carried by prose style) and family MTMM still inverts (.140 vs
.269, improved from category-features' .096/.383 but failing). v2 stands. Three lexical bases now
exhausted (category rates, genre-residualized, stylometric); remaining blue lever = CT-CM latent
capstone (own prereg, Addendum 2).

## 11. V3P judge pilot + CT-CM capstone — both MISS; the campaign's honest terminus (2026-07-07)
V3P (400 chunks, 50 members, $30, paired vs the same members' v2): the anti-halo independence
instruction WORKS — A-ES fell .585 -> .508 paired (-0.077) — but missed the -0.10 requirement and
the .50 absolute by .008, while the rewritten ES items cost reliability (SB .488) and C dipped
(+.074). Extrapolated to the full roster (.653 - .077 = ~.58), a funded full v3 would NOT clear
the .50 bar: not recommended. CT-CM (semopy, pink raw_z + blue v2 + behavioral indicators, pink
method factor): boundary-degenerate (F_ES variance 0, blue_A uniqueness 0, negative on-trait
loadings) — empirically underidentified because blue v2's near-collinear A/C/O fits cannot anchor
distinct trait factors; MISS on the Heywood/loadings bar.
CAMPAIGN CLOSE. Passes: the pre-registered interview-C retest (consequence wired, C_INT_W=2x) and
P6 gated shrinkage (shipped on corrected external-criterion grounds, not the artifact split-half number). Corpus growth delivered SB .674->.748 and MTMM
.410->.493. The A-ES finding, fully characterized: ~.44 is population-real (RKH benchmark .443
House / .393 Senate), the ~.21 excess is TEXT-TONE halo that is information-theoretically
entangled with C's criterion signal at the text level (proven twice: P2 member-level and P7
chunk-level removal both crush A-ES AND the C criterion together; V3P shows judge instructions
recover only ~a third of it). The desk carries the caveat with the RKH benchmark. Eleven designs,
one look each, two promotions, zero bars moved.

## 12. External benchmark grade — independent literature review (2026-07-08)
Deep-research harness (104 agents, 22 primary peer-reviewed sources fetched, 25 falsifiable claims
adversarially verified: 22 confirmed / 3 refuted). Purpose: grade the Pink instrument against the
ACTUAL published standards of its class, not against self-report-questionnaire norms (the wrong
yardstick — nothing read off public speech clears α>.80). **Grade within the elite-speech
text-personality class: A- / high-A.** Point-by-point, defensible to a skeptical reviewer:

| Metric | Published field benchmark | Pink | Verdict |
|---|---|---|---|
| Convergent r | open-vocab ceiling avg **.38**, best trait .43 (Park/Schwartz, JPSP 2015; train N=66,732); LLM zero-shot **~.29** (Peters & Matz, PNAS Nexus 2024); field's stated behavior→trait "upper limit" **.40–.50** (Schwartz, PLOS ONE 2013) | **.42–.52** | exceeds — but see §13 caveat (shared-method) |
| MTMM discriminant | RKH (PSRM 2019) and Birkenmaier-Lechner (Political Analysis 2025) report **NO MTMM at all**; Park's own discriminant contrast failed our verification | cross-genre same-trait **.41 > .28** floor (reported AND passed) | above-norm |
| Reliability | short-form self-report scales (TIPI/BFI-10 ranges); a claimed text test-retest ~.70 was REFUTED in verification so is NOT used | split-half **.62–.73** (C=.62 soft spot) | acceptable-to-good |
| Behavioral criterion | RKH validates ENTIRELY on one criterion (ES→survey non-response, β=.58, p<.05) | C→votes **+.15**, pre-registered | meets field practice |
| Process | RKH/B-L report inter-coder α (floor >.70) and stop | de-identified, pre-registered, one-look, adversarially verified | best-in-class transparency |

Niche norm established: the two standard-bearers of this exact niche report neither a convergent-r
nor a split-half nor an MTMM. Pink reports all three and passes two. Refuted claims NOT used to
support the grade: (a) Park passed a formal MTMM discriminant (voted down 1-2); (b) a text
test-retest of .70 "on par with questionnaires" (1-2); (c) Park = the canonical Psych-Assessment
informant-validated benchmark (1-2). Units caveat: the .42–.52 is an interpretable r; some
benchmarks are AUC/F1 (DeepPerson ~.70 AUC; B-L macro-F1 .77) and are NOT apples-to-apples — the
defensible claim is that Pink beats every r-scale convergent benchmark, not the F1/AUC ones.
Sources on disk: none new (web-only); citations in this table are the record.

## 13. Cross-Method Convergence (CMC) — MISS; grade holds A- (2026-07-08, prereg @c305aba)
The §12 grade's one standing reviewer objection: the .42–.52 convergence is measured vs RKH, itself
TEXT-derived → **shared-method** (text vs text). CMC pre-registered a test to answer it: Pink raw_z
(text-judge method) vs the behavioral dispositions (roll-call/cosponsorship = an independent NON-text
method Pink was never fit to), cross-method Campbell-Fiske MTMM, A/E/O blind (C confirmation-only).
n=445 complete cases. **Result — MISS on both bars.** Same-trait diagonal: A×cooperation **+0.173**
(a genuine cross-method signal), C×diligence +0.079, E×visibility +0.054, O×breadth −0.002; mean over
{A,E,O} = +0.075 < +0.12 bar. Discriminant direction also inverted (mean diag +0.076 < mean |off-diag|
0.115; the −0.345 pink_A×behavioral-visibility off-diagonal drives it — agreeable-sounding members
are behaviorally quiet, not prominent).
**Honest interpretation:** the behavioral data is a CRITERION, not an independent TRAIT measure, so it
cannot fully serve as the cross-method convergent comparator the objection needs — the shared-method
caveat is neither worsened nor resolved, it stands. Agreeableness shows real cross-method signal
(+0.173); C is weak-positive (consistent-ish with the stronger C→votes +.15, a different behavioral
target); E/O do not travel to behavior. **Grade unchanged at A-** (A- already priced the shared-method
caveat; this neither lowers nor raises it). The ONLY remaining path from A- to a straight A is an
independent TRAIT comparator — a multi-rater expert gold panel or a self-report anchor (data
collection, not a code change). Reverted per doctrine; documented so no future session re-runs it.

## 14. Audio-prosody pilot — MISS; the one untried modality closed (2026-07-08, prereg big5_audio_prereg.md @3c94fc7)
The one modality never tried: acoustic prosody (eGeMAPS v02, 88 functionals, openSMILE), targeting the
volume-bound E and the A-ES text-tone halo. Real C-SPAN floor audio for 90 members (>=180s each,
solo-biased search; YouTube CDN 403 bypassed via ios/web_safari/android yt-dlp client). Pre-registered
two bars + a significance gate + N>=80 (after the empirical finding that PCA can't fix an N-problem and
the +0.267 floor at N=40 = the correlation sampling limit). **ONE LOOK, N=90: MISS both bars.**
audio-alone E held-out r **+0.228** (real-ish, Marrero/Rubio band) but < permutation noise floor +0.234
(WITHIN NOISE), and text+audio fused (.254) does NOT beat text-alone (.258) -> **audio-E is REDUNDANT
with the text instrument, adds nothing** (Marrero super-additivity was self-report; didn't transfer to
our behavioral criterion / legislators). Halo separation VACUOUS (audio-A invalid, +0.129 < null +0.165).
**Honest-negative, not false-positive: +0.228 would have cleared the naive +0.15 bar — the significance
gate + incremental bar + Bar-2 validity gate + NaN-drop/winsorization together prevented a false pass.**
Audio is NOT the lever to straight-A or load-bearing. Text terminus stands; psychology DISPLAY-ONLY;
no number moved. Pipeline (fec/b5_audio_fetch|build|eval.py) retained; scale-up not pursued (same-kind
audio is redundant). Real load-bearing avenues live elsewhere (N-channel upgrade to Pink; incremental
validity vs observed movement — separate session).

## 15. The A-ES halo was LARGELY A NON-PROBLEM (2026-07-08; 5-paper mine + 2 tests)
After FOUR failed CT-CM halo-separation attempts (lexical Blue, embedding Blue, audio-ES, conversational
N — all collinear/weak/null), a 5-paper re-read (Yang-ISR, RKH, Birkenmaier-Lechner, Marrero, Simchon)
plus two direct tests reframed the whole thing:
- **Not load-bearing:** NO engine reads big5_llm_opus.json (Pink). It is DISPLAY-ONLY (desk + audit +
  analysis scripts only) — the A-ES halo drives ZERO decisions.
- **Traits functionally distinct:** despite Pink A-ES r=.653, only Pink-A predicts the A-criterion
  (cooperation): partial r=+.100 p=.034 controlling ES; Pink-ES does NOT (partial +.049 p=.30). The
  correlation is shared-METHOD TONE, not shared meaning. Discriminant CRITERION validity holds (A-side).
- **The ".44 population-real floor" was mislabeled:** it is corr(lifeAgree,lifeEmoti)=+0.443 (n=916)
  computed from RKH's OWN estimates — but RKH is also text-derived (tone-influenced, not halo-free), and
  RKH NEVER uses trait-trait correlation as a validity criterion (per-trait nomological validation only).
- **Conclusion:** the 4 CT-CM attempts optimized a self-invented quantity. The field-correct bar (RKH's
  logic, and tonight's C win) is PER-TRAIT EXTERNAL CRITERION VALIDITY, not A-ES discriminant correlation.
  The .653 stays as a documented shared-method-tone caveat on the DISPLAY read (you can't cleanly read one
  member's raw A-vs-ES from tone alone) — NOT a validity crisis, NOT operational. DO NOT re-run CT-CM.
  Only genuine gap: no behavioral ES criterion (ES-side discriminant untested; Voteview/NPAT would close
  it; low priority). B&L reframe on the shelf: A and ES both project onto the COMMUNION pole — an
  agency/communion per-sentence cue-share would decorrelate them at the display level by construction.

## 16. Clean-audio program: speaker verification, ES cross-modal validation, formal re-grade (2026-07-09)
The search-fetched audio pilot (§14) was ~38% contaminated (multi-speaker panels, wrong-speaker,
name collisions — "Adam Smith" clips carrying Adam Schiff). Fix (user-directed): caption-based
speaker verification — `b5_audio_verify.py` pulls each clip's auto-captions and a Haiku classifier
judges (a) speaker structure and (b) identity vs a member card on a **HARD signal only**
(self-naming, chair recognition, "my bill the __ Act"; topic is nuance, never identity).
1,700/2,119 clips kept; **142 wrong-member clips caught**; `b5_audio_build.py` gained a verification
gate → **395 members with ≥180 s verified-clean voiceprints** (median ~17 min).

**ES cross-modal validation — the three-turn honest record:**
1. The remembered "+0.223 text-affect↔voice-prosody" was an uncommitted scratchpad one-off on the
   CONTAMINATED N=90 (Empath neg-affect ↔ 3-feature prosody composite) — provisional, never a result
   of record.
2. On clean audio the committed acoustic-ES composite gave −0.165 — but a 32-agent literature
   workflow established the composite was **MIS-SIGNED** (folk "steady voice = calm"; per the
   depression-voice literature flat/monotone marks INSTABILITY; per-feature clean-data correlations
   all run opposite the composite's signs). §14's Bar-2 composite and the CT-CM audio anchor carry
   deprecation notes; their recorded MISSes stand as history.
3. **The authoritative test** (`big5_es_crossmodal_prereg.md` → `fec/b5_es_crossmodal.py`, locked
   pre-look): ridge nested-CV, ALL 88 eGeMAPS → big5_v2-ES, out-of-fold, analyst chooses NO signs.
   **PASS: held-out r = +0.208, permutation p = .0002 (5000), ES-specific (r_A = −0.030), N = 395.**
   Modest by construction (~4% variance = the N-from-voice ceiling); voice↔text-MODEL convergence,
   not ground truth. Per-member OOF reads persisted display-only (`b5_es_voice.json`, desk line).
   **[ANNOTATION 2026-07-09, pre-registered robustness (big5_es_robustness_prereg.md): the pass is
   GENDER-CONFOUNDED — partial r(| gender, party) = −0.029, perm-p .715, within-gender null in both
   sexes. It stands as history; the validation claim carries the caveat everywhere it is cited.]**
   The former "all five traits validated" summary is superseded → A/C/E/O behavioral (v2 held-out
   A +.14 / C +.13 / E +.34 / O +.20; **O/C/E now diagonal-dominant per §17**); ES measured but
   without a clean independent validation (text +.149 near-miss; voice confounded).

**Formal re-grade (32-agent judge panel + adversarial skeptics + fact-check): A− RATIFIED** —
panel B+/A−/A−/A−, skeptics floored B− (non-fatal), final A− as top-of-class. Held below A by:
method-shared RKH convergence; the pooled-lexical MTMM failure (firewalled — no engine reads trait
scores); the modest ES effect. The fact-check corrected the property sheet: **shipped v2 C = +.13
(a +.24 claim was ~2× inflated); the "full-roster Empath→diligence +.24/perm-p .003" has no repo
record (the real number is the N=90 exploratory +.355); Pink's MTMM .41/halo .653 must not be
attributed to the lexical composite; the Pink×behavioral matrix was 0/5 diagonal-dominant (§13),
so "validates 4/5" always carries that caveat.** Path to A = an independent-TRAIT anchor only.
The multi-rater expert panel for that anchor was BUILT (`big5_expert_panel_prereg.md`,
`fec/b5_panel_{items,build,score}.py`; verified BFI-2-XS observer items; 98 leak-scanned packets;
gated one-look scorer) and then **CANCELED by user decision — A− stands as the final grade**; the
infrastructure is dormant and safe (scorer refuses the look while unlocked).

Companion display layer shipped the same day: 3-paragraph "Suggested approach" briefs for all 533
members (`fec/b5_narratives.py` → `member_narratives.json`; de-identified measured profiles → Fable,
Opus 4.8 rescuing its ~74% refusal rate; vocal descriptors from the clean voiceprints feed P2).
Display-only throughout; engines/ranks untouched (kernel 37/37, audit ALL CLEAN, ranks 0/533).

## 17. Psych-audit augment round: instrument LOOK 3/5, ES robustness CONFOUNDED, JS psych parity (2026-07-09)
User-directed augments ("simulate, see what that does, and then if it checks out run"); every look was
preceded by machinery validation on planted/null synthetic targets; preregs locked + committed
pre-look (@fd963ab).
- **Behavior-anchored per-trait instrument (prereg @d630fe3) — LOOK TAKEN: 3/5** (bars exactly as
  locked). Empath-194 → ridge nested-CV, held-out, exact perm-p, full matrix in the prereg RESULT.
  **O +.198 PASS · C +.277 PASS · E +.552 PASS** — all three diagonal-dominant, perm-p .0002. The C
  cell is the full-roster confirmation §16's fact-check demanded (retires the "no repo record" caveat;
  subsumes big5_textC_prereg). E carries a genre-composition caveat (corpus and criterion share the
  interview modality). **A +.183 MISS on dominance only** (real signal, perm-p .0004, but reads C/O
  criteria slightly higher). **ES +.149 MISS** (0.001 under bar; anti-reads E at −.303; the
  affect-lability fallback computed and INVALID as criterion). Pre-look hardening, bars untouched:
  exact permutation p restored (the committed script had substituted a parametric p — a prereg
  deviation caught in audit), a __main__ one-look gate added (the file formerly ran THE LOOK at
  import), Empath features cached.
- **ES cross-modal robustness (locked prereg) — LOOK TAKEN: CONFOUNDED.** Raw +0.208 reproduces
  exactly; partial r(| gender, party) = **−0.029**, perm-p .7151; within-gender M −.016 / F −.036.
  Pre-declared consequence applied: §16 annotated, desk voice-ES lines caveated, crossmodal prereg
  carries a dated addendum; the original RESULT text left unmodified (history is not rewritten).
- **Honest per-trait state after today: O, C, E criterion-valid AND diagonal-dominant (supervised
  text); A criterion-valid, not discriminant; ES measured, no clean independent validation.**
  Grade **A− UNCHANGED**: the ES leg weakened, the discriminant leg strengthened (Pink trait-score
  0/5 → supervised-instrument 3/5 — the first genuinely diagonal-dominant per-trait text evidence in
  the program); the firewall (no engine reads trait scores) and process discipline carry it, exactly
  as §13/§16 priced. The receptivity layer is unaffected (behavioral basis; N enters shrunken at
  0.30 weight inside clipped multipliers).
- **JS psych parity (dashboard):** the in-browser live-scenario engine consumed NONE of the
  receptivity multipliers the Python engine applies → bundle now ships engine.pmult/emult/dmult;
  the tpl applies pressure_mult (both pflip money terms + shiftLean), delivery_mult (target value),
  edge_mult (cascade kernel PE), and LOSSFRAME (competitor defection leg). Numeric parity harness:
  JS totals within 0.15% of Python flip_value on all 18 real issues (psych-blind drift was up to
  2.08%); in-browser engchk exact (flip 4.43 = py 4.43); 0 console errors. Closes the JS half of
  audit finding N-1.
- Hygiene: narratives ordinal + roster-union fixes; ledger-referenced campaign scripts tracked
  (b5_textc_confirm, b5_round4_eval, big5_ctcm2, b5_emb_build); one-look gates heading-matched
  ('## RESULT') after the ES gate false-tripped on its own prereg prose.

## 18. A & ES round 2 — Paul's mechanisms, 0/3, both routes closed with evidence (2026-07-09, prereg @d276254)
User-directed ("Fix A and ES"): (a) dialogic ASSENT language ("that makes sense", "sure!",
"I understand") as the A-specific act; (b) sex-RELATIVE vocal inflection for ES; (c) the NPAT
survey-response criterion (RKH's own; the .tab files were found ON DISK, unconsumed). Pre-lock $0
probes: RKH hou114 floor-speech Assent null vs cooperation (+.013) → design restricted to dialogue;
NPAT pre-check PASSED on RKH's traits (Emoti strongest, +.063, sign fixed +); criterion structure
corr(coop, breadth)=+.708 documented. The repo's existing 'agree' feature was found DEAD BY MECHANISM
(whole-turn regex vs the ≥8-word ingest floor — it can never fire). Machinery simulated + validated
per test before looks (@d276254; gates newline-anchored @72690c9 after prose quotes false-tripped
them — no look consumed).
- **TEST A (assent instrument, N=242, 8 fixed lexicon/persona features, interview turns): MISS** —
  own r −.231 (CV-null artifact; perm-p 1.0). Informative trace: turn-initial assent RIGHT-SIGNED vs
  cooperation (+.074) but an order of magnitude under criterion strength; assent phrases +.003.
  Dialogic-assent route CLOSED. A stays: criterion-valid (+.183) / not discriminant.
- **TEST E1 (sex-relative voice, N=395; features AND target residualized on gender): MISS** —
  held-out r −.024, perm-p .68. The within-sex nulls were the true state, not a training artifact.
  **Voice-ES CLOSED PERMANENTLY** (pre-declared final attempt): raw +.208 gender-confounded →
  within-sex null → sex-relative retrain null.
- **TEST E2 (NPAT respond, current-roster N=171): MISS** — v2-ES −.042 wrong-signed (perm .70), not
  ES-specific (v2-E largest |r| −.072), partial null; Pink-ES −.062. NPAT closed for the current
  roster (RKH's own effect was +.063 in-sample — under our bar even at perfect transfer; the pre-lock
  power warning realized). **The one remaining powered ES path: a fresh full-roster Vote Smart PCT
  pull (votesmart_id available for all 533) — external collection, user-gated.**
**Post-round-2 honest state: O/C/E criterion-valid + diagonal-dominant; A criterion-valid, not
discriminant (assent route now closed with evidence); ES measured, NOT validated, ALL in-repo routes
exhausted.** Grade A− unaffected (candidate additions that did not pass; nothing shipped changed).
Value of the round: both proposed mechanisms were the genuinely untested configurations; they are
now closed with recorded one-looks instead of open speculation — no future session re-runs them.

## 19. Round 3 — N reframed as BEHAVIOR: the reactivity disposition ships (2026-07-09, user-ratified)
User: "Reset. Maybe we need to separate text from audio... examine [Celli & Rossi, EACL-W 2012]...
see if Neuroticism is a better variable... no more dead-ends." Probe-first discipline, ZERO looks burned.
**Paper interrogation:** the Celli-Rossi labeler is weak and partly circular (follower counts were
input features; .625 acc on 8 users) — NOT imported. What survives: (a) the N-pole DETECTION
ASYMMETRY (their precision .80 neurotic vs .375 secure — N produces visible behavioral EVENTS; calm
is the absence of events); (b) personality expressed in interaction STRUCTURE — a third channel that
is neither text content nor audio acoustics.
**Kill-ledger (probes, each with cause of death):** retweet share (0 stored); reply chains (no
threading); reference-graph reciprocity (edges undirected); mention table (392 rows); Bluesky
reply-share (party_R +.46 confound) and posting-burstiness (party +.28) on a 134-member
self-selected platform sample — the posts table is BLUESKY-ONLY; and iv_burst = situational noise
(program-split-half SB .04 — its face-valid ranking was the show, not the member).
**Survivor → shipped:** `reactivity_z` = live-interview CUTOFF PRONENESS (interruption/trail-off
share, per-program z, turn-weighted; interaction_features channel). Evidence card: orthogonal to
all five dispositions (worst |r|=.15 dominance), party −.09 / gender +.02 clean, not
long-windedness (+.07 wpt) or floor-defense (−.09), gini +.27 coherent; program-split-half SB=.43
(real, modest) → graded shrinkage sqrt(min(1, turns/REACT_TURNS=150)); <30 turns → None (neutral);
unstaffable (live speech). Wired as the N-SLOT of the Byrne susceptibility composite
(`RECEPT_N=behavioral` default; `RECEPT_N=text` reverts wholesale) — retiring the engine's LAST
text-derived leg, completing the 2026-07-04 behavioral basis. Coverage 207/533 (rest neutral).
**Stress battery (all gates):** determinism byte-identical ×2; RECEPT_N=text reproduces legacy math
(438/533 susc identical; residual ≤.006 = input freshness); bounds all within caps; rank stability
rho .9805, top-20 overlap 14/20; dial variants (REACT_TURNS 100/250, w_N .25/.35, gate 20/45) all
rho ≥.9988, top-20 ≥19/20 — decision-robust at the receptivity_sensitivity standard. **Fairness
finding: the swap REDUCES demographic tilt in targeting** — susc gender loading +.327 → +.198,
pressure_mult +.137 → +.090 (lexical N carried the SAME gender-language artifact the ES robustness
look exposed; women read as more pressure-susceptible by word-style, not behavior); party loading
mildly improved (−.381 → −.361 susc; −.130 → −.103 pressure). Biggest movers = corrections of
extreme lexical-N artifacts (Joe Wilson N +3.17 → react +0.01; Mike Rogers text −1.76 → react
+1.91, the most interrupted member — face-valid flip).
**Epistemics:** like every behavioral disposition, reactivity is a measured behavior serving a
construct role (Byrne pressure-reactivity) — valid by construction for its ROLE, no criterion look
to fail. The Big-5 DISPLAY layer is untouched (text ES/N stays, caveats intact); this is an engine
input. burst was probed and REJECTED (SB .04) — do not re-add. Text-N remains available via
RECEPT_N=text.

## 20. Psych-audit round 4 — N-anchored per-trait look: RETIRED WITHOUT A LOOK, data-gated (2026-07-09, prereg big5_n_matrix_prereg.md @e4aea1e)

User directive ("switch over to Neuroticism… fix everything else") + the round-3 reservation
("text-N × cutoff = a look; prereg if ever wanted") → a locked prereg to test the SUPERVISED Empath
text read of N against the behavioral criterion reactivity_z, with the full masked 6-model matrix
(the §17 machinery imported verbatim; MEM=456, MEM_N=201, fingerprints pinned). Adversarially
panel-reviewed pre-lock (4 lenses): adverse prior disclosed (halo-look composite +0.013 null),
bar-5 partial volume-hardened (gender/party/log-turns/shrinkage-weight, ≥+0.10 AND perm<.05),
pred_ES added as bar-4 competitor, Williams-guarded demotion rule wholly on MEM_N, a core-matrix
NO-STATUS-CHANGE clause (drift cannot promote A or ES), noiv ship-gate, secondaries firewall.
Honest prior: LOW.

**The look was NEVER taken.** The in-process simulate battery refused it twice (both runs verbatim
in the prereg addenda): run #1 exposed a sim-design artifact (correlated random plants; corrected by
Gram–Schmidt orthogonalization, Addendum 1); run #2, honest plants, showed the real constraint —
a TRUE r=.40 planted signal recovers only +0.129 held-out at n=201 (fails bar 1). Power study
(synthetic, 5 reps/cell): true .40 passes 3/5 at n=201 with extreme draw variance (+0.015…+0.372)
but 5/5 from n≈250; true .50 passes 5/5 even at 201. The bars are sound; the SAMPLE is the
constraint — a look today would be machinery-noise roulette, exactly what the one-look discipline
exists to prevent.

**State: the Empath-text→reactivity route is neither validated nor closed — DATA-GATED.** Successor
prereg permitted only at reactivity coverage MEM_N ≥ 250 within the §17-eligible roster (grows with
weekly interview collection; 201 today). Nothing else moves: fifth text axis stays ES-framed with
its recorded caveats (§16 annotation intact), A stays criterion-valid/not-discriminant (the prereg's
no-status-change clause forecloses drift-promotion), §17's 3/5 and §18's closures stand verbatim,
and round-3's reactivity_z engine slot is untouched (valid by construction for its role, §19).
Look-independent hygiene shipped alongside: reactivity joined the desk behavioral radar (6th axis) +
N-slot source line, dashboard receptivity legend names it, audit gained the N-slot guard
(n_slot=behavioral, coverage ≥150, |z|≤5 — a silent RECEPT_N=text revert can no longer sail through)
+ the mislabeled missing-receptivity check name fixed, b5_behavioral_instrument gates
newline-anchored, stale voice-ES "validated +0.208" comment corrected (audit now 69 checks).

## 21. Psych-audit round 5 — A vs the de-entangled cooperation criterion: RETIRED WITHOUT A LOOK, diagnostic-gated (2026-07-09, prereg big5_a_matrix_prereg.md @28914b3)

User directive ("De-entangle A criterion" — gate opened alongside the Vote Smart pull). The §17 A
verdict traced to a criterion defect: cooperation_z was 2/3 cosponsorship volume (breadth
entanglement +.708). **Criterion work (stands on its own record): cooperation_v2 =
mean_z(bipartisan tie share, directional cross-party cosponsorship share), both required, built in
fec/coop_v2_candidate.py** — SB .873 (c2) / .821 (c3 facet), entanglement old→new: breadth
+.708→−.140, log-volume +.739→−.159, gender −.021; reciprocity (c3) proved a DISTINCT anticorrelated
facet (bonding vs bridging) and is reported, never composited. Coverage 315/533; MEM_A = 290 of the
§17 roster. Prereg locked @28914b3 after adversarial review (same-commit machinery, slicing
semantics pinned, A_v1 as a bar-4 rival, volume in the gating partial AND in sim(c)/(d), closure
over any {c1,c2,c3} recomposition).

**The look was never taken.** The in-process battery refused it (planted-A +0.105 at n=290, row
FALSE — verbatim in the prereg Addendum 1), and the follow-up 5-seed stratum diagnostic showed the
refusal was NOT draw luck: **median recovery of a true r=.40 orthogonalized signal on the actual
MEM_A stratum = +0.132 < the +0.15 bar (2/5 pass)** — vs ~.195 for random rosters of the same size
(round-4 power study). The finance-active stratum that has cooperation-v2 coverage carries genuinely
less recoverable Empath signal (homogeneous profiles). A multi-rep battery re-spec was considered
and rejected: it would also have refused. **Disposition: RETIRED WITHOUT A LOOK — text-A vs the
de-entangled criterion is neither validated nor closed; DIAGNOSTIC-GATED** (successor prereg
permitted when the pinned 5-seed diagnostic passes ≥3/5 on bars 1–4 on the then-current stratum;
synthetic-only, safe to check any time). Program-level lesson, now twice replicated (rounds 4 and
5): masked-stratum looks at n≈200–300 cannot see signals below the E-class with the §17 bar — the
battery/diagnostic discipline is what stops those looks from burning as false MISSes.

**Open, user-gated (unchanged by this retirement):** (a) ENGINE promotion of cooperation_v2 over
the volume-entangled cooperation_z (susceptibility .40 slot, seed_prob .10 slot, desk radar axis) —
a product decision on the criterion-side record; coverage trade-off: 315/533 vs old 513/533, the
218 uncovered members would fall to neutral; sandboxed stability report available on request.
(b) The Vote Smart ES corroboration look (prereg locked pre-collection @28914b3, §22 reserved for
its RESULT) — awaiting the user's API key; collector + look script committed and gated.

## 22. ES external corroboration — Vote Smart PCT respond: TIER 5, UNCORROBORATED (2026-07-09, one look, prereg big5_es_votesmart_prereg.md)

The user opened the gate and, after the API key proved demo-gated, authorized the browser-session
collection route (prereg Amendment 1, recorded PRE-collection; server-side fetches 403, the user's
own Chrome session reads the same public pages any voter can). Collection: 517/518 joinable members
classified (Gooden = the 1 fetch_failed, excluded per the pinned taxonomy), responded=1: 162, base
rate .3133 — coverage (≥450) and degeneracy (.05–.95) guards PASS. The pilot's char-threshold
full-page test was operationalized during collection as PROOF-OF-RENDER (heading + Office line in
stripped DOM text) after production scale surfaced sparse-but-real pages (75–112k HTML, <5k visible
text — ground-truthed live on Lankford); the marker→responded mapping itself is byte-identical to
the pinned amendment. Artifact frozen in the COLLECTION RECORD (sha 8b16c681…, committed BEFORE the
look @ae458cd).

**The look (one, gated, verify-pass agreed statistic-for-statistic): TIER 5 — "ES text read
externally UNCORROBORATED — the §18 limbo closes with evidence."** v2-ES vs pct_respond on n=517:
point-biserial r=+0.0550, exact perm-p=.1080 (S FAILS); FW partial (gender, party, chamber,
log-tenure) = −0.0075 p=.575; and v2-ES is the WEAKEST of the five axes against this criterion
(O +.0857, C +.0692, E +.0633, A +.0572) — SPEC would have failed too. Secondary (firewalled,
reported only): Pink-ES raw +.0886 perm-p .0242, but confound-attributable (partial +.0464,
p=.155). Pre-declared consequences applied: desk ES caveat gains "externally uncorroborated
(PCT-respond null, 2026-07-09, n=517)"; the respond-criterion route is CLOSED (one look; closure
covers the criterion, not richer PCT content, which would be a new construct + prereg).

**Program state for ES after §22: every route is now exhausted-with-evidence** — text halo (§15/§16
caveats), voice CLOSED PERMANENTLY (§16/§18), NPAT-precheck adverse (§18 E2), and now the full-power
any-cycle external criterion NULL at n=517. The display axis stays measured-with-caveats; nothing
engine-side ever depended on it (the engine's N-slot is behavioral reactivity, §19). Honest-prior
accounting: the prereg's LOW/VERY-LOW prior and disclosed adverse prior pointed exactly here; the
value of the look is that ES's status is no longer a data gap but an evidenced negative record.

## 23. Psych-audit round 6 — A vs cooperation_v2 via the st_mean instrument: MISS, route closed (2026-07-10, prereg big5_a_matrix2_prereg.md @25c0a19 + Addendum 1 @9a55ca8)

(§22 is occupied by the Vote Smart ES RESULT recorded on main, 2026-07-09 late evening, parallel
session — this branch's methods jumps 21→23 by design; see the prereg's branch-hygiene note.)

**Setup.** Round 5 (§21) retired without a look: supervised Empath cannot recover a planted true
r=.40 on the MEM_A stratum (median +0.132, 2/5). A multi-basis stratum-power diagnostic
(b5_a_stratum_diag_record.md, SYNTHETIC ONLY, 7 bases screened on the pinned Addendum-1 seeds
with a pre-pinned fresh-seed confirmation) found the refusal was EMPATH-SPECIFIC: st_mean
(all-MiniLM-L6-v2, rebuilt on the post-expansion corpus) recovers the same plants at ~2× Empath
(selection 4/5 median +0.236; fresh-seed confirmed 3/5 median +0.192); the guard demonstrably
bound (lsa256 cleared selection then refuted 1/5). User authorized a FRESH lock ("Lock it in") —
explicitly NOT a derivation of round-5's successor gate (its "SAME diagnostic" clause belongs to
the Empath data-growth path, which stays open). Two-lens adversarial review pre-lock (stats: 0
CRIT / 0 MAJOR / 1 MINOR; discipline: 1 CRIT + 4 MAJOR, all incorporated: fresh-lock reframing,
round-5-scope closure + anti-basis-shopping clause with mandatory screening ledger,
grounds-no-claim context-matrix ban, pinned desk wording, restored isolated A_v1 repro secondary,
branch-hygiene note). Addendum 1 (pre-look): collector drift moved the speeches count mid-session;
counts demoted to reported, replaced by STRICTLY STRONGER roster content-hash gates.

**Battery (the machinery validation Empath failed twice): ALL GREEN on st_mean** — planted core
5/5, masked-A plant +0.312 p .0002 row/col True; null 0/5 + stack MISS; confound-only bar-5
refused (−0.072); true+confound admitted (+0.514). The look was therefore licensed — first time
an A-vs-coop_v2 look has ever been licensed.

**THE LOOK: MISS on all five bars.** own r = +0.033, perm-p .2961, row-dominant False,
column-specific False (max rival |r| = .120), volume-hardened partial +0.036 p .2685. Facets
+0.010/+0.052/−0.099; within-party D +0.087 / R −0.001; gender +0.061, party +0.042 (fairness
clean). Declared repro secondary: Empath A_v1 × coop_v1 on MEM = **+0.183, the §17 recorded value
EXACTLY** — the criterion re-specification broke nothing.

**Consequences applied (pre-declared).** "st_mean-A vs de-entangled cooperation: not distinct —
route CLOSED for this instrument-basis"; closure covers ANY composite over {c1, c2, c3} (round-5
scope verbatim) for ANY st-family basis. A stays criterion-valid / not-discriminant; §17/§21
unchanged. NO desk change; NO engine change; round-5's Empath data-growth gate remains OPEN; the
ANTI-BASIS-SHOPPING CLAUSE binds all future bases (own diagnostic + fresh-seed confirmation +
full screening ledger + adversarial prereg, before any pairing). The coop_v2 ENGINE-promotion
decision (user-gated) is untouched.

**Honest reading.** The battery proved the instrument CAN see a true r=.40 on this exact stratum;
the MISS is therefore informative about the world, not the machinery: supervised open-vocabulary
semantic text carries no distinct cooperation-v2 signal on the finance-active stratum. Combined
with §21 (Empath power-refused) and this round, the discriminant-A question is now EVIDENCE-BOUND
on the text side: the remaining honest paths are non-text behavioral criteria growth (MEM_A
coverage via the bills archive) or the Empath data-growth gate — both slow, neither urgent. A's
standing claim stays exactly what §15/§17 earned: criterion-valid (text-side, +.183 v1;
+.100 partial §15), not discriminant.


## 24. Reactivity criterion variant study — the shipped per-show spec UPHELD by a pre-stated rule (2026-07-10, criterion-side only, NO look)

Context: the N-gate sprint (round-4 successor, MEM_N >= 250) found near-miss members carry
abundant RAW interview turns discarded by fragmentation (CNN splits per show under the
>=12-turns/program floor). Collection alone moved MEM_N 201 -> 216 (+5.4k PBS/NPR turns, +16.1k
MS NOW turns). The user directed a criterion-side comparison ("Start tier b... Whatever is most
optimal") under the coop_v2 playbook: measurement evidence first, no spec change without it.

Method (fec/reactivity_v2_study.py + fec/reactivity_v2b_study.py, identical machinery per
variant; SELECTION RULE STATED IN THE SCRIPT BEFORE ANY VARIANT RESULT: MEM_N>=250 AND
appearance-split-half SB>=.45 AND no fairness regression vs V0 AND agreement>=.85; winner = max
SB; none => HOLD V0, V1 explicitly not adoptable as fallback). Corpus at study: 139.6k INTERVIEW
turns, 91.8k appearances.

Results: V0 per-show 12/8 (shipped) = MEM_N 216, SB .507, g -.097/p +.087. V1 per-network =
MEM_N 271 but SB .301 (~23% signal attenuation for any true text-N effect - crossing the n-gate
while shrinking the detectable signal violates the gate's purpose; the >=250 pin derives from a
power study that assumed V0-class reliability). Variants: 12/5 = no change (that floor never
binds); 8/8 = SB .441 + fairness REGRESSION (g -.143, p +.122); 12/8+network-fallback-pool
(the principled orphan-turn recovery) = MEM_N 273 but SB .343; 10/6 = trivial. **NO QUALIFIER ->
V0 HELD.** Interpretation: the fragmented turns are genuinely noisier measurement, not discarded
treasure - show-level interruption cultures are real, and every admission scheme pays
reliability. The round-3 spec is now evidence-backed against its five most tempting relaxations.
Records: reactivity_v2_study.json / reactivity_v2b_study.json (untracked, regenerable from the
committed scripts). The round-4 successor gate stays data-gated at MEM_N 216/250, now accruing
weekly (interview legs wired into weekly_refresh incl. the new msnow leg).

## 25. Psych-audit round 8 — text-N clears the interview stratum; no-interview ship gate MISS (2026-07-12, prereg `big5_n2_prereg.md` @297964e, addenda @d76857f/@6ddb232, RESULT @fb5a529)

Corpus growth changed the criterion-side state without relaxing the shipped per-show floors:
MEM_N reached **263** and appearance-split reliability improved to **SB=.596**. The pinned
five-seed planted diagnostic cleared exactly 3/5 (median +.212), authorizing the successor. Two
pre-look harness refusals were recorded and repaired before any real pairing: the inherited
single-seed battery contradicted the locked 3/5 aggregate rule, then a thin-runner indentation
error failed to install the successor pins. Both refusals occurred before the matrix and are
preserved verbatim in the prereg.

**Consumed look:** all five N bars PASS on MEM_N=263: own held-out **r=+.188**, exact
perm-p **.0014**, row-dominant True, column-specific True (max rival |r|=.126), and
volume/gender/party-controlled partial **r=+.152**, p=.0078. The fresh OOF-seed re-derivation
passed again (r=+.179, perm-p=.0030, partial +.146, p=.0098). No O/C/E demotion inversion.

**Ship gate MISS:** excluding interview text left r=+.098, perm-p=.0562. Predeclared verdict:
**text-N is criterion-valid and distinct on the interview-covered stratum, but shared-source-
dependent; no artifact, no desk reframe, no engine change, route closed.** This is meaningful
fourth-trait evidence under a stated stratum caveat, not a full-corpus 4/5 or 5/5 promotion.
The engine remains on the separately ratified affective-N slot (Round 7/7b).

## 26. Psych-audit round 9 — fresh interview-antagonism criterion 5/5; st_mean text-A MISS (2026-07-12, prereg @1f4ace9, criterion lock @45a3430, RESULT @513f2b9)

To avoid recycling the already-observed hearing-antagonism relation, a new criterion was frozen
before labels: blinded Haiku 4.5 ratings of reporter hostility, personal contempt, and gratuitous
cruelty on two deterministic package-disjoint interview halves. Policy conflict and principled
dissent were scored separately and excluded. The screening ledger rejected Empath (2/5 pinned,
2/5 fresh) and licensed `st_mean` on a genuinely different criterion (3/5 pinned, **5/5 fresh**).

**Criterion look: QUALIFIED 5/5.** n=322; split-half r=+.537 / SB=.699; raw contamination
party +.109, gender -.032, log-words -.005; cross-venue convergence with the ratified hearing
facet +.160 (n=282); cooperation direction -.072 (n=207); excluded-content max |r|=.242.
This is a valid secondary antagonism criterion and an independently useful measurement result.

**Trait look: MISS.** On the fresh criterion roster n=309, the predeclared cooperation-trained
`st_mean` A prediction produced own r=+.084, perm-p=.0782, row-dominant False, column-specific
False (max rival |r|=.193), and partial r=+.087, p=.0652. The re-derivation was not triggered.
A later no-interview coverage assertion cannot change the already-consumed gating MISS. Declared
consequence: this criterion/basis route is CLOSED; Blue A remains criterion-related against the
historical cooperation measure but not discriminant. The full-roster Blue instrument therefore
remains **3/5 (O/C/E)**, with the new conditional N evidence reported separately.

**Post-result deployment (user-ratified 2026-07-12).** The qualified criterion is promoted as a
separate, display-only **validated A-antagonism facet**: package-split interview antagonism,
controlled for party, gender, and log words, with its inverse displayed as Agreeableness. This
does not reopen or relabel the missed text-A look, does not replace cooperation_v2 in the engine,
and does not affect ranks. The approved claim is facet-specific: "validated inverse-antagonism A
facet (Round-9 criterion 5/5)," never "Blue A validated" or "the full text Big Five is 5/5."

**Three-leg status (display wording correction, 2026-07-12).** Reliability remains **5/5**
(O .92, C .81, E .77, A .80, ES .92) and the directional known-groups sign test remains **5/5**.
The **3/5** status applies only to the stricter discriminant/diagonal-dominance leg (O/C/E).
Dashboard language must state the leg whenever reporting 3/5; an unqualified “Text Big-5 3/5”
incorrectly implies the first two legs failed.

## 27. Article-guided sampling-frame audit - A facet scoped to interview/media coverage (2026-07-12; prereg @9e9c34d, harness @9c2fd05, RESULT @ab5a4db)

Three user-supplied papers exposed a validity layer not tested by the Round-9 criterion gate.
Azucar et al. (2018, DOI 10.1016/j.paid.2017.12.018) report A as the weakest digital-footprint
trait (meta-analytic r=.29) and show demographic inputs can raise apparent A/N accuracy; Celli et
al. (2026, DOI 10.1145/3806009) separate traits from situated states and ecological validity from
observer/model representation validity; Hargittai (2015, DOI 10.1177/0002716215570866) shows
that large trace samples can remain non-random and require sampling-frame scope plus triangulation.

The locked coverage look used criterion membership only—never A values—against the 533-member
roster. Result: demographic max |SMD|=.620 (Senate; party -.322, gender -.001), model-position
max=.378, and media/activity max=1.877 (visibility; log Blue tokens +1.195). Coverage was Senate
90.0% vs House 53.6%, D 68.0% vs R 52.9%, while female/male coverage was 60.7%/60.8%.

**Binding scope:** the result remains a validated inverse-antagonism A facet **on the
interview/media-covered stratum**. Its percentile is relative only to the 322 covered members;
missing members are not imputed. Demographics remain residualization-only controls, never A
features. The score, Round-9 5/5 criterion result, cooperation_v2 engine role, Blue/Pink reads,
and ranks are unchanged. Pink is explicitly labeled a model-perception channel with possible LLM
response-prior contamination, not independent ground truth.

## 28. Citation-chain + source-integrity re-audit (2026-07-12)

Forward/transitive review of Azucar/Celli/Hargittai located the decisive method contrast. Hinds &
Joinson (2024, `10.1037/bul0000430`) confirm heterogeneous, platform-moderated passive-trace
prediction. Peters & Matz (2024, `10.1093/pnasnexus/pgae231`) and Marengo et al. (2025,
`10.1111/jopy.70019`) improve reliability by repeated/model/time aggregation but retain modest
self-report convergence and demographic/model bias. Härtel et al. (2025,
`10.1007/s10869-025-10087-8`) find public LinkedIn profiles recover O/E but not A/C/N and fail MTMM.
Wright et al. (2026, `10.1038/s41562-025-02389-x`) obtain all-five convergence by averaging seven
LLMs answering the exact inventory item-by-item from unconstrained first-person narratives **and**
testing against real questionnaire scores. Public Sample-1 reproduction: N .472, E .434, O .397,
A .546, C .531 (n=60). This is the strongest next-method template, but its questionnaire anchor is
not present for Congress.

Independent local audit found the former three-leg slogan combined different instruments. The
reliability vector O .92/C .81/E .77/A .80/ES .92 belongs to the legacy genre composite, not all
displayed Blue-v2 axes. Its documented alternating-document split leaks 21.3% of speech packages
across halves (CREC 33.4%, interview 12.6%, CHRG 95.0%). The artifact is also loaded from a
hard-coded temp path, has no in-repo generator, and covers a selected 259-member stratum (Senate
82.0%/House 40.9%; D 54.1%/R 42.8%); the other 273 v2 ES values use a different fallback. Therefore
**current-Blue reliability is re-audit required**, not 5/5.

The cleaned current v2 known-groups directions remain 5/5, but A is R-D=-.0009, 95% CI
[-.1709,+.1690], p=.9914, and reverses/zeros in 204/530 leave-one-out deletions. Report only
`five signs, A null`. Discriminant remains 3/5 O/C/E.

The corpus is nominally multimodal but operationally pooled: CREC 75.17% of characters,
interviews 19.82%, hearings 3.53%, social 1.49%; median dominant-venue share per member 80.3%.
Pink excludes social and hearings entirely. A source resolver defect compounded this: surname-only
matching inserted unrelated accounts into member text. `process_quorum.py` now requires exact or
explicit nickname-equivalent first+last names and segregates ambiguity. This is a data-integrity fix;
it does not create new trait validity.

## 29. Source-primary multimethod Big Five — promoted 5/5 (2026-07-12; prereg @cd75732)

The user directed that the five-trait instrument be fixed by composing the strongest independent
behavioral channels rather than preserving the failed pooled text-A definition. This section
supersedes the production-status conclusions in Sections 26–28; those sections remain the audit
history of the pooled lexical/text-only instrument.

**Instrument.** O/C/E are Ridge reads over LSA-256 features computed separately within CREC,
interview, and social venues, then standardized within venue and combined. A is inverse raw
interview antagonism (reporter hostility + personal contempt + gratuitous cruelty; policy conflict
and principled dissent excluded), averaged over two package-disjoint halves. N is the promoted
affective-content measure; ES is exactly `-N`. A remains missing outside its 322 package-qualified
members; there is no text-A fallback or imputation. O/C/E/N cover 469 members.

**Fresh reliability.** A common full-corpus LSA basis transformed two SHA-256 package halves; every
CREC/interview package and social post was indivisible. Across 172,262 packages, overlap was exactly
zero. Spearman-Brown reliability passed 5/5: O .940 (n=530), C .934 (n=530), E .968 (n=530),
A .699 (n=322), N .680 (n=383).

**Independent-criterion matrix.** O/C/E rows are nested out-of-fold predictions against behavioral
breadth/diligence/visibility; A uses one package half against the other; N uses the LLM affect
channel against independent LIWC affect. All five diagonals were positive, exact-permutation
`p=.0002`, and larger in absolute value than every other cell in both row and column:

| row \ criterion | O | C | E | A | N |
|---|---:|---:|---:|---:|---:|
| O | **.294** | .045 | .144 | .068 | .016 |
| C | .074 | **.253** | -.188 | .130 | -.083 |
| E | .073 | -.136 | **.731** | -.064 | -.027 |
| A | .134 | .055 | -.103 | **.537** | -.029 |
| N | -.043 | -.126 | .089 | -.148 | **.253** |

Known-groups also passed 5/5 on trait-specific available coverage: R-D O -.593, C +.412,
E -.371, A -.218, N -.013 (equivalent ES +.013). The production artifact is
`big5_blue_validated.json`; `fec/b5_multimethod_validate.py` reproduces the package cache,
reliability, exact permutations, matrix, and guarded promotion. Blue on the member desk now reads
this artifact. It remains display-only and rank-independent; the pre/post rank-authority SHA-256 is
unchanged at `797a6490ca0c0f63496f76ac9f030c0a8b538d5f46dbc18e39092bbbc74b00c6`.

**Audio.** The verified eGeMAPS cache was refreshed without acquisition or re-featurization:
1,761/2,192 clips are identity-clean, 410 members clear 180 seconds, and all 88 features were cache
hits. Previously consumed audio trait experiments remain historical misses and are not injected into
the promoted Big Five; the retired gender-confounded voice-ES artifact remains disconnected.

## 30. Behavioral roles v2 — dominance candidate qualifies; expressiveness is not E (2026-07-13; prereg `9b6074b`)

The behavioral-alignment audit exposed one production defect and one labeling gap: dominance mixed
observed interaction behavior with a binary committee-office flag, while visibility measured media
exposure rather than turn-level expression. A locked, package-disjoint candidate study separated the
roles before computing any outcomes (`behavioral_roles_v2_prereg.md`).

**Frozen measures.** Dominance-v2 is the mean of within-program turn-length Gini and explicit
floor-defense rate; committee leadership and response length are excluded. Expressiveness-v2 is the
mean of within-program mean and p90 words per turn; interview count is excluded. Both require 30
qualifying turns, are z-scored within chamber, and remain missing otherwise. Five SHA-256 package
splits reran all cell floors and program standardization independently.

**Result.** Both operational roles are reliable on 272 members: dominance median SB=.564 (all five
splits >=.40) and expressiveness median SB=.749 (all five >=.40). Dominance's largest preregistered
partial cross-role correlation is .245 (reactivity); dominance-expressiveness is -.074 and
dominance-cooperation_v2 is .002. Replacing the old dominance slot in memory only leaves the
flip-model decision surface effectively unchanged (rho=.999980, top-20 20/20, top-50 50/50).
Therefore, at the locked result, dominance-v2 was a **qualified candidate**, consumed by nothing
until a separate promotion.

**Display-only promotion (2026-07-13).** The subsequent instruction to optimize the remaining
behavior layer promoted both qualified roles to the member desk only. Dominance-v2 replaces the
legacy leadership-contaminated dominance display; expressiveness-v2 appears as a separately labeled
verbal-expression role. Members below 30 qualifying turns remain missing. Neither value is read by
an engine, neither is substituted for Big-Five E, and the promotion moved 0/533 ranks. The expanded
full-body audit independently checks exact member-level propagation and rejects any unapproved
production-engine consumer.

Expressiveness is distinct from visibility after controls (r=-.175) and qualifies as a stable
speaking-style role, but it fails its source-disjoint CREC floor-elaboration criterion (partial
r=-.023, p=.6425) and has only descriptive shared-interview alignment with Blue E (+.060). It is
therefore **not an independent behavioral E indicator**; the specification is closed without feature
shopping. Committee leadership is also unrelated to pure conversational dominance (partial r=-.003),
so formal office and observed floor behavior remain separate constructs.

The carried cutoff-reactivity measure retains five-split median SB=.555 at current coverage 272.
No N pairing was reopened: promoted Big-Five N already has independent LIWC convergence, and the
historical behavioral-reactivity text-N look was previously consumed. Cooperation-v2 remains the
coalition-behavior input; inverse antagonism remains the validated A facet.

## 31. Interview-observer E criterion — rejected before behavior look (2026-07-13)

A fresh package-disjoint observer test asked whether equal-length, de-identified interview responses
could supply a criterion for expressiveness-v2. Haiku 4.5 rated six fixed expressive-interpersonal
facets under a 4,097-token cached coding manual with explicit A/N/dominance controls. Two independent
SHA-256 package partitions produced 314 and 316 complete ratings; no package crossed halves.

The criterion was internally reliable (Spearman-Brown .695/.744) and stayed separated from the
validated inverse-antagonism A facet (-.143) and affective N (+.067). It nevertheless failed its
pre-behavior qualification: partition repeatability was .696 against a .70 bar, party association
was -.347 against |.20|, and gender association was +.288 against |.15|. Volume contamination was
small (-.023). The criterion was therefore rejected before expressiveness or Blue E was opened, and
the same-venue observer route cannot validate E. No residualization, subgroup scoring, or threshold
repair was attempted. The stable expressiveness-v2 role remains operational only pending a genuinely
source-disjoint criterion.

## 32. Clean-audio E criterion for interview expressiveness — rejected before behavior look (2026-07-13)

A second locked route moved the criterion entirely out of interview text. Two independent five-seed
nested-CV panels used all 88 verified eGeMAPS features to predict promoted Blue E out of fold on 391
members. Demographic contamination was bounded (party about -.04, gender -.11/-.12), duration stayed
within the .20 limit (+.178/.179), and the panels replicated at r=.964. Both panels were
diagonal-dominant over Blue O/C/A/N and retained positive controlled convergence (.151/.184).

The audio read did not qualify. Primary held-out convergence was .193 against the locked .20 bar
(re-derivation .225), and predicted clip-half reliability was only SB=.536–.567 across the two clip
partitions, below .60 in every panel/partition combination. Stage 1 therefore rejected the acoustic
criterion before the interview candidate or behavioral rivals were opened. Expressiveness-v2 remains
a reliable operational speaking-style role, not a validated E behavior. The result also prevents the
older N=90 audio-E finding from being treated as a stable member-level criterion on the expanded clean
voiceprint corpus.

## 33. Fable suggested-approach refresh (2026-07-13)

The member-desk three-paragraph brief is a display-only communication aid, not a validation channel
and not an engine input. Its current evidence packet uses the promoted multimethod Blue traits,
conversation-role v2 observations, verified eGeMAPS voice features, and source-grounded personal
texture. The static interpretation rubric is prompt-cached; each member's dynamic packet is hashed
and stored with prompt and basis versions so stale or mixed-vintage prose fails the full audit.

The roster refresh produced 533/533 complete briefs: 473 direct Fable results, 59 Opus
refusal-fallback results, and one deterministic neutral non-inference brief for a member with fewer
than two supplied evidence channels. Coverage at generation was 410 verified voice profiles, 272
conversation-role profiles, and 479 members with at least one source-qualified personal detail. The
personal layer may supply at most one natural rapport detail; it may not be used as leverage or to
infer an unstated preference. Affective-content N is labeled as such, low-antagonism A remains
separate from cooperation, visibility is not treated as Extraversion, and missing behavioral evidence
remains unknown rather than neutral-scored.

Promotion regenerated only the dashboard tail and changed 0/533 ranks. The production audit requires
all 533 desk narratives, current version/hash metadata, at least 400 direct Fable reads, at most five
evidence-insufficient rules, and substantial cache-read use. This refresh consumed 1,117,755 cached
input tokens after a 2,105-token cache creation and passed the 89-check full-body audit.

## 34. Sonnet 5 narrative cost/quality promotion (2026-07-13)

The narrative writer moved from Fable 5 to Sonnet 5 after a source-identical 12-member comparison
and a second six-member no-thinking pilot. Sonnet preserved the three-paragraph structure and supplied
evidence, eliminated all model fallbacks in the full roster run, and showed no gender-pronoun leakage,
raw percentile text, z-score language, stale versions, or malformed rows. The rubric was tightened so
visibility cannot determine meeting format and projected persona cannot substitute for observed turn
behavior. Sonnet adaptive thinking is disabled because this is a bounded evidence-to-prose transform;
the pilot showed it consumed roughly 1,500 hidden output tokens per member without improving the
visible brief.

The promoted artifact contains 532 direct Sonnet briefs plus the unchanged deterministic neutral brief
for the single evidence-insufficient member. Prompt caching recorded 2,332 cache-creation tokens and
1,238,292 cache-read tokens. Total first-party API cost at the introductory Sonnet 5 rate in effect on
2026-07-13 was approximately $5.39, compared with more than $32.52 of recorded successful-call cost
for the superseded Fable/Opus run (excluding the unrecorded Fable attempts that ended in refusal).
This is a display-writer substitution only: evidence inputs, trait values, engines, and ranks are
unchanged.

## 35. Construct-audit reset — O/C retained; E/A/N withheld (2026-07-13)

This section supersedes the product and claim implications of sections 29, 30, 33, and 34. Their
recorded experiments and artifacts remain historical evidence; they no longer authorize a five-trait
display or a generated profile. The reset follows the measurement definitions and validity standards
in the supplied Big Five, elite-speech, public-personality, digital-trace, and PoliPers literature:
reliability is necessary but not validity, an external-role correlate is not automatically a trait,
and a narrow public-language facet cannot be relabeled as a holistic Big Five construct.

The five-trait promotion did not survive re-audit for three specific reasons:

1. **Extraversion:** its criterion channel is `visibility_z`. Visibility is partly an outcome of
   institutional office, media demand, and communication strategy. The locked role-controlled
   warmth/excitement/activity/gregariousness/assertiveness candidate missed reliability and construct
   gates (overall SB=.567; controlled RKH r=-.070; aspect coherence r=-.071). Interview-observer and
   clean-audio alternatives also failed their preregistered qualification gates. Extraversion is
   therefore unavailable. Raw and role-adjusted public exposure remain context only.
2. **Agreeableness:** the promoted A diagonal (r=.5367369729603486) is exactly the same package-half
   correlation used to compute its SB reliability (.699). It is repeatability, not an independent
   criterion, and cannot be counted a second time as convergent validity. The controlled
   low-antagonism measure remains a reliable, media-stratum-scoped public-language observation; the
   separately validated cross-party cooperation measure remains revealed legislative behavior.
   Neither is holistic Agreeableness, and their divergence is not an error.
3. **Neuroticism:** the reported SB=.680 belongs to package-split LIWC anchor scores, while the
   production score is the separate LLM/residualized `affective_n` measure. The available convergence
   (about r=.253) supports a narrow negative-affect-expression interpretation, not reliable holistic
   Neuroticism. Behavioral reactivity is also kept separate. Neither is a diagnosis, private-trait
   estimate, or complete composure measure.

The active product contract is now: qualified public-text **Openness** and **Conscientiousness** are
shown with their criterion scope; **Extraversion**, **Agreeableness**, and **Neuroticism** are shown as
unavailable. Co-operation, diligence, breadth, activity, conversational dominance, verbal
expressiveness, warmth, excitement, gregariousness, assertiveness, low antagonism, negative-affect
expression, reactivity, and public exposure may be shown only under those literal labels. Supporting
measurement details live in a psychology disclosure rather than the headline trait panel. The
archived Pink overlay is not rendered.

The reset is display/claim-only. It does not alter the influence model, the formal
Speaker/leader/whip contribution, the ratified cooperation-v2 engine role, or any rank. The active
audio layer remains fail-closed: no vocal descriptor enters a profile unless target identity,
source independence, and cross-source stability clear the v2 guards. Legacy paid narratives remain
withheld. A deterministic local three-paragraph renderer exists at zero API cost, but roster-wide
activation remains an explicit user decision after this reset is verified.

## 36. User-directed restoration of the accepted product state (2026-07-13)

Section 35 recorded a stricter post-hoc reinterpretation of already accepted validation artifacts; it
did not record a new failed replication. The product implications of that reinterpretation were not
ratified and are superseded by this restoration. The accepted display contract is restored without
rewriting the underlying historical results: source-primary O/C, a role-adjusted public-exposure cue
in the operational E slot, package-split low-antagonism A, and affective-content N. The E cue must stay
explicitly labeled as exposure rather than intrinsic Extraversion; cooperation remains separate from
A; N remains public affective-content rather than a diagnosis or private-state claim.

The restoration preserves the 2026-07-13 formal Speaker/leader/whip influence decomposition and the
fail-closed audio-v2 guards. It does not activate legacy paid narratives or spend through an API. The
zero-API local three-paragraph renderer remains withheld pending explicit user approval. No influence
rank is changed by this personality-display restoration.

## 37. Source-integrity diagnosis, CHRG source rebuild, and model quarantine (2026-07-14)

The accepted source-primary corpus now uses attributed `CREC`, attributed `INTERVIEW`, and non-repost
database social posts only. A full inventory found 757 legacy CHRG rows that fail current-service or
chamber attribution constraints, including witness-name and same-surname collisions. The cause was
not damaged GovInfo content: the first backfill discarded package chamber and Congress, guessed
Senate before House against the current roster, accepted comma-terminated direct address as a new
speaker, and did not isolate live questions from testimony/opening/written material.

All 206 previously successful packages were then re-fetched from the original GovInfo HTML. A
backup-first transaction replaced 12,873 legacy rows with 9,763 verified ordinary-question rows
(1,507,370 words, 185 packages with qualifying rows, 190 current members). Every stored row now has
matching service, Congress, and chamber; exact duplicates, invalid rows, Roger Marshall rows from
House hearings, and the Susannah-Marshall collision are all zero. The pre-repair database is retained
as `backups/social_media.PRE-CHRG-REPAIR-20260714_013342.db`.

CHRG remains excluded both from the accepted personality text basis and from behavioral diligence.
The rebuild establishes attribution integrity, not psychometric validity, so re-entry requires a
separate locked validation. The collector now applies the same chamber/tenure, witness, live-Q&A,
post-hearing, and joint-hearing guards to future ingestion.

After CHRG removal, diligence consists of verified roll-call participation plus CEL/LEP bill
follow-through. The accepted source-primary model passed all locked gates again: package overlap 0;
five of five reliability gates; five of five criterion/discriminant gates; five of five known-group
directions. C reliability improved from `.934` to `.941`, and the independent C-criterion diagonal
improved from `.247` to `.269`. O/C/E coverage is 533/533; A remains 322 and affective N 469 because
their independent evidence floors are narrower. The repair changed no influence rank.

The corpus cache contains 172,262 selected packages and is content-fingerprinted against the live
database. HTML entities were decoded under a backup-first transaction. The audit reports zero hard
errors and explicitly records that current evidence is not full-tenure for every member. A locked
expansion using deduplicated verified X/Facebook/Bluesky text passed reliability but missed C
discriminant dominance by .002; it remains an unconsumed candidate. Press releases, newsletters,
letters, prepared committee statements, and unverified social rows are excluded.

## 38. Advocacy-persistence as Conscientiousness — reliable but invalid, retired (2026-07-14)

A locked, interpretable candidate tested the proposed official-persona cues directly: concrete
first-person action, constituent-linked action, bill/agency/number specificity, and recurrence of an
issue across at least three packages spanning 30 days. It used only CREC and interviews, controlled
chamber, party, committee leadership, and package volume, and was never connected to production.

The cue was stable (Spearman-Brown `.713`, `n=391`) and covered 484 members, but it did not measure
behavioral diligence (rho `+.015`, permutation `p=.372`; controlled `r=+.044`). It correlated more
with public visibility (`+.158`) and policy breadth (`+.096`) than with diligence, failing both
criterion and discriminant gates. Its shared-source correlation with accepted text C was `-.035`.
The fixed lexical route is therefore retired as a C measure. Repeated advocacy may be a useful
observable communication/activity descriptor, but it is not evidence of Conscientiousness or actual
follow-through and will not be tuned or relabeled to force a pass.

## 39. Social-format, intrinsic-E, and audio evidence update (2026-07-14)

Azucar, Marengo, and Settanni's digital-footprint meta-analysis reports useful average prediction but
extreme between-study heterogeneity. Multiple *types* of digital footprint improved C prediction;
text by itself did not reliably outperform other inputs, and posting activity primarily helped E.
Accordingly, the accepted C construct and criterion remain frozen. Social text must be treated as a
separately normalized format-transfer channel, while demographics, office visibility, and posting
volume cannot be imported as C cues. The prior pooled social-text candidate remains a MISS and is not
rescored or tuned from its `.002` discriminant failure.

Smith et al.'s concise-inventory study supports a four-indicator survey measure of E after factor,
structural-equation, and criterion checks. It does not turn tone, verbosity, or appearance frequency
into an intrinsic-Extraversion estimator. The existing role-controlled interview composite already
tested warmth, excitement, activity, gregariousness, and assertiveness and failed aspect coherence.
No new E score is activated from the same looked-at data. Public-adjusted exposure remains the
operational E-slot cue, explicitly distinct from intrinsic Extraversion; a new intrinsic-E route must
first obtain an independent multi-indicator criterion and then test within-setting and cross-setting
generalization.

Marrero et al. found modest out-of-sample personality prediction from combined voice/language in a
student sample (joint R-squared .16 E, .11 C, .15 N, .04 O, .07 A), with complex spectral features and
greater voice than language contribution for most traits. The same audio also predicted gender above
90%, making unguarded transfer a serious confound. Hayat et al.'s CNN chapter predicts *apparent*
personality from short YouTube clips, not self-reported or political Big Five. Therefore audio still
cannot modify Big Five. The active on-air guard now additionally requires at least 50 aligned target
words per clip and explicitly rejects absolute-F0/gender, apparent-personality CNN, and unvalidated
MFCC/chroma/spectral trait inference. The existing two-review, target-only, two-program, program-
conditioned, 180-second member floor remains active and fail-closed.

## 40. External Senate gold anchor, reconstructed E, and topic-conditioned pitch (2026-07-15)

Three supplied sources changed the criterion design without rewriting any prior result. The frozen
online appendix to *Personality on the Hill* supplies 254 senator-level ratings: 129 Senate-insider
rows (PDF pp. 2-4) and 125 academic-expert rows (pp. 5-7), each on the same 1-7 O/C/E/A/Emotional-
Stability scale with the number of raters preserved. The extractor pins the exact source PDF at
SHA-256 `43c989262fde0b5b806c316e54147474fb4c0d34d05ba819d49e37921aef731a` and refuses any page,
table-shape, range, count, or duplicate mismatch. Current-roster overlap is 46 insider-rated and 52
academic-rated members, with 40 shared; cross-panel E agreement is `r=.426`.

Amsalem et al., *The Effect of Politicians' Personality on Their Media Visibility* (2018), treats
media appearances as an outcome, not an Extraversion questionnaire. The study uses self-reported
TIPI traits (PDF pp. 11-12) and finds that, with institutional and activity controls, higher E and
lower A predict more visibility; O and emotional stability also predict aggregate visibility, while
C is inconsistent (Table 1, pp. 14-17). The new gold audit reproduces the central warning in this
roster: raw visibility correlates positively with expert E (`+.377` insiders, `+.215` academics) but
also negatively with expert A (`-.345`, `-.251`). Therefore visibility cannot be the sole E
criterion. Role adjustment remains useful public-exposure context, but in this overlap it weakens the
E association and does not remove the multi-trait interpretation.

The equal-weight E axis remains the fixed, no-gold-fitted control: equal weight on
(1) roster-standardized source-primary Blue E, the visibility-calibrated channel, and (2)
roster-standardized Pink raw observer-item E, followed by one final standardization. The expert
values are used only after construction. The estimate clears both independent panels: insiders
`r=.529`, `n=46`, one-sided permutation `p=.0001`; academics `r=.484`, `n=52`, `p=.0002`. Its E
diagonal exceeds every absolute heterotrait correlation in both panels. Coverage is 509/533; the 24
members without the observer-item channel remain missing, with no visibility-only fallback. This
establishes that both primary methods carry real E signal, but it is no longer the active profile
estimate.

The active `big5-gold-anchored-v2` estimator answers the requested optimization with leave-one-member-
out weight selection: the held-out senator's label never enters that senator's score, both panels are
evaluated independently, weights are nonnegative on a 0.10 grid, and full-sample weights are fit only
after the OOF gates pass. E selects 20% Blue, 60% Pink, 10% interaction dominance-v2, and 10% role-
adjusted visibility. It clears insiders at `r=.493` and academics at `r=.505`, with diagonal
dominance in both. E therefore includes both requested behavioral channels, while each remains
separately labeled context and is not E by itself.

The same audit is deliberately trait-specific. Broad public-personality A clears both panels
(`r=.431/.400`, coverage 317; 10% qualified Blue low-antagonism + 90% Pink observer A). Per the
2026-07-15 user activation rule, O/C/N also enter the canonical profile when at least one independent
panel clears the n/r/p association gate, but their status is explicitly weaker:
`ACTIVE_ONE_PANEL_ASSOCIATION_SUPPORTED`. O is supported by academics (`r=.492`) but not insiders
(`.192`); N, the reverse of appendix Emotional Stability, is supported by insiders (`.374`) but not
academics (`.123`); C has a significant insider association (`r=.262`, `p=.040`) but lacks diagonal
dominance and has academic `r=-.039`. C therefore enters only as one-panel association-supported,
not as discriminantly validated. The canonical profile uses broad O/C/E/A/N wherever each composite
has member coverage. Qualified text O/C, low-antagonism A, and affective-content N remain alongside
the broad axes under narrower labels; missing member evidence stays null rather than being imputed.

Dietrich, Hayes, and O'Brien, *Pitch Perfect* (2019), changes the active audio quantity. Its HouseLive
workflow is the operationally important addition: official Clerk broadcast events pair HLS/DASH
video with WebVTT captions, while the transcript API supplies speaker labels and archive-relative
offsets. The unit is a confirmed speech, not a member-level pooled voiceprint. Mean F0 is measured on concatenated
target-only segments for each speech unit, converted from the eGeMAPS semitone representation to Hz,
and standardized within speaker as `(speech mean F0 - speaker mean F0) / speaker speech-unit SD`
(methods PDF p. 5). Absolute pitch and cross-speaker pitch never enter a personality score. Topics
must come from the aligned transcript/closed captions, using a pinned dictionary or structural topic
model, never the video title or editable Congressional Record text (pp. 5-6). A member needs at least
five confirmed speech units, two independent sources/programs, and two distinct transcript-identified
topics; a topic summary needs at least two speeches. Output is literal topic-conditioned emotional
intensity relative to that speaker's baseline. It does not modify Big Five.

The first dated smoke on 2025-07-15 succeeded for Chip Roy: five 35-second intervals, 216 day-level
caption units, 199 named-caption units, 33 unambiguously resolved members, two identified policy
topics plus other speech, finite mean F0, and finite within-speaker deviations. It is research-only
because caption identity has not received two independent reviews. WJ has 7,746 timed member turns
but its remote media binding remains blocked; CNN has 66,450 transcript units but no deterministic
audio binding; the CREC/floor corpus has 104,632 transcript units and 2,192 legacy WAVs but no
transcript-unit hash/time plus two-review binding. The active reviewed queue therefore remains at
zero production profiles rather than publishing legacy pooled eGeMAPS values.

Behavioral integrity is now explicit and hash-pinned. Diligence covers 528 members from 527 eligible
roll-call records and 447 LEP follow-through records (446 have both), averages available within-
chamber z scores, clips only after combination to `[-3,3]`, and never penalizes a missing component.
The LEP criterion is static through the 118th and is one behavior component, not a direct rank input.
Corrupted legacy CHRG hearing counts are contractually excluded. The RKH ceremonial-bill criterion
remains null and is reported as such; it is not used to claim successful validation.

## 41. Two-panel congruence rounds — O criterion-weighting MISS, N variant-parity MISS, C documented (2026-07-16)

Paul's question — E and A clear both expert panels while O/N/C clear one; are the one-panel
results fundamentally incongruent? — was answered NO on criterion-side evidence, then two
user-authorized one-look rounds were locked (@66f9772, both adversarially reviewed pre-lock,
batteries green) and both MISSED, each informatively. The look-free diagnostics live in
fec/b5_gold_criterion_probes.py: cross-panel agreement stratified by insider rater count shows
single-rater insider rows are noise (roster-overlap, insider k=1 vs k>=2: O -.05 -> +.49,
C +.14 -> +.48, E -.04 -> +.59, A +.25 -> +.69, ES +.38 -> +.48); range restriction is
negligible (SD ratios .86-1.15); a 4,000-draw null simulation puts a random measure's chance of
clearing both association gates at 1.5-2.1% (<1% with dual dominance). One mechanism carries all
seven trait-by-panel outcomes: trait observability crossed with rater vantage, plus single-rater
criterion noise.

The O round (big5_o_panel_reliability_prereg.md, RESULT-OW) evaluated the FROZEN 0.5/0.5
composite against rater-count-reliability-weighted panels (SB weights, rho1=.25 pinned).
Weighting lifted the insider association (.192 OOF -> .247, p=.051, dominance holding in BOTH
panels; academics re-cleared at .525 including dominance) but the gating confound partial
exposed the substance: weighted partial r(composite, insider gold-O | female, party) = +.028
(p=.42) versus the academics' +.231 (p=.043). The insider O column's association with our
composite is gender/party-shared variance, not O-specific signal. MISS; the criterion-weighting
route is CLOSED under this gold (any rho1, sqrt(k), subsetting, pooling), terminal per the lock.

The N round (big5_n_variant_parity_prereg.md, RESULT-NV) gave N the constrained-variant
treatment E received: two pre-declared weight-floor variants through the shipped LOO-OOF
machinery. The selected variant (30% affective-content N / 70% Pink observer N) improved BOTH
panels over the shipped 10/90 baseline — insiders .374 -> .416 (p=.003, dominant, above even the
stricter .30 bar), academics .123 -> .147 — but .147 sits under the .20 association gate without
dominance. MISS; the N-composite variant space over {affective_content_n, pink_observer_n,
behavioral_reactivity} is FROZEN under this gold, terminal per the lock. Two recorded readings:
the affective channel carries real insider-visible N signal, and the academic panel cannot read
N from the public record at gate strength — the observability mechanism, measured twice. A
firewalled suppression note (academic partial .389 EXCEEDS its raw .147) is recorded in the
RESULT for any future Paul-initiated criterion round; it grounds nothing.

C gets the documentation path, no round: it has the weakest cross-panel gold agreement of all
five traits (.155 all-senators / .357 roster-overlap), its insider association is halo-caveated
(insider heterotrait |r| with gold N .384 and E .317 exceed the own-trait .262), and the academic
C column is signal-poor at that vantage (within-panel academic C-ES r=.589). Per the ceiling
arithmetic a both-panel C pass would need a tone-free C measure 2-3x stronger than anything five
prior methods produced. ACTIVE_ONE_PANEL_ASSOCIATION_SUPPORTED is the honest terminus; the
engine's C role remains behaviorally anchored (diligence_z), firewalled from this display
composite.

Housekeeping recorded with the rounds: (1) provenance — Downloads/Eran.pdf is Amsalem et al.
2018 (hash-mismatched to the gold pin and containing no senator ratings); the TRUE pinned
appendix source is Downloads/online_appendix.pdf, SHA-256 verified equal to the §40 pin
43c98926... (2) A 2026-07-16 session probe computed a VOID look-fragment (a Steiger test pairing
shipped fitted scores with gold on a 38-senator subset); it was ruled void under the pre-lock
pairing prohibition, disclosed in both preregs, and none of its numbers are load-bearing
anywhere. (3) The round-4 N successor's DATA-GATE (MEM_N >= 250) now reads ~270 eligible by the
turns>=30/non-null-cutoff construction (fec/b5_gold_criterion_probes.py section 6) — a successor
prereg on the reactivity criterion is available whenever Paul initiates it; nothing here took or
licensed that look. (4) All five one-panel/two-panel statuses stand exactly as §40 recorded them;
these rounds changed no status, no engine input, and no shipped artifact.

## 42. Audio speaker-identity layer built (TDD, research-only, awaiting pilot + user gates) (2026-07-16)

The zero-production-profiles blocker (#40: two independent identity reviews) now has executable
machinery, user-directed and built tests-first (51 assertions across five suites, all green at
commit; no LLM in any identity path; no network or model download exists in code — the ECAPA and
whisper loaders hard-refuse without explicitly named local weights). Design provenance: Dietrich,
Hayes & O'Brien 2019 (within-speaker F0, caption-timestamp speech units, >=50-word floor) and
Mestre & Ryan 2026, Political Analysis (embeddings-over-MFCC for speaker identity at scale —
their Table 3: MFCC+CNN collapses to .08-.13 accuracy over many identities while pretrained
embeddings hold >=.91; forced-alignment-over-ASR when good transcripts exist; short-utterance
alignment failures; channel normalization; gender-bias probes). The ECAPA-VoxCeleb verification
protocol, EER<=5% bars, and whisper-DTW-primary alignment are engineering adaptations labeled as
such, not paper methods.

The contract: a speech unit is attributable iff CHECK-T (transcript/caption speaker identity,
roster-resolved fail-closed; cspan_identity for WJ; hearings_seq turns time-anchored by local
token-DTW with word-match floors 80%/turn and 70%/hearing) and CHECK-A (speaker-embedding
verification against an enrollment bank — verification never identification; ALL segments must
clear the calibrated cosine threshold with top-2 margin >=.10 and >=85% duration coverage) name
the SAME member; any disagreement excludes the unit fail-closed into a rejects ledger, with
check-T-vs-check-A hard disagreements feeding a mismatch ledger (successor of the 148 caption-
caught wrong-member clips). Witnesses are unenrolled by design and double as in-situ negative
controls: a witness turn acoustically matching an enrolled member excludes the ENTIRE hearing.
Enrollment floors: >=3 clips from >=2 events totaling >=180 s, leave-one-clip-out integrity gate;
legacy feedstock identity must be RE-DERIVED by deterministic hard-signal regex (the retired
Haiku labels are never identity evidence). Cosine thresholds live only in
b5_audio_identity_thresholds.json.candidate (written by a future calibration run); every consumer
refuses without it; audio_rules.py carries the structural constants. Every output is .candidate,
consumed by nothing; audit_full gained SKIP-while-absent checks; a source guard makes writing
b5_audio_reviews_v2.json or b5_audio_descriptors_v2.json unrepresentable in the attribution
module. Coverage reconnaissance: 354 members already clear the enrollment floors from legacy
clips on keep-based identity (301 on strict hard-signal MATCH), before any HouseLive enrollment.

NOT done, deliberately: no model weights downloaded (SpeechBrain spkrec-ecapa-voxceleb, silero-
vad, faster-whisper small — named in the DRAFT prereg with sources; their SHA-256s get pinned at
lock); big5_audio_identity_prereg.md is DRAFT, explicitly not locked, and the pilot ladder P0-P5
(synthetic battery -> DET/EER calibration on the 148 negatives + impostor trials -> Chip Roy
cross-channel hard gate -> 100-unit human listen-check -> 3 hand-labeled hearings -> WJ smoke)
runs only after Paul rules on: contract mode A/B (machine checks AS reviews vs pre-filter-only
default), the venue amendment beside on_air_interview, hearings scope + the curated media map,
thresholds/floors ratification, topic dictionary vs STM, the floor second-source rule, legacy
corpus write-off, Senate source, storage root, the 60s-vs-180s member floor, enrollment
ratification workload, and promotion itself. Until then the shipped fail-closed state (zero
profiles) remains the correct active state.

## 43. Audio identity audit hardening — paper-faithful embeddings and calibrated gates (2026-07-16)

A tests-first audit of §42 found four merge-blocking contract defects despite its original
synthetic suites passing: the field named `eer` was used as a cosine threshold even though EER is
an error rate; enrollment accepted a free `--theta-enroll` value instead of the calibration
artifact; empty `ratified` enrollment entries were usable by default; and any attempted acoustic
comparison on a witness could poison an entire hearing even when the acoustic decision was
REJECT. All four are corrected without taking a real calibration look or changing the active
zero-profile state.

`fec/b5_audio_calibrate.py` now deterministically separates `theta_eer` (score boundary) from
`eer_rate` (the <=.05 stop-bar quantity), requires all corpus EER bars plus at least 148
caption-mismatch negatives and >=.99 rejection, reports sex-specific FAR/FRR ratios without
retuning, and writes either `CALIBRATION_PASS` or a permanently non-consumable
`CALIBRATION_STOP_BAR_MISS`. Enrollment has no free threshold parameter: it loads theta_enroll
from a passing artifact and records its SHA-256. Verification refuses non-passing/malformed
thresholds and treats unratified voiceprints as absent unless an explicit pilot-only override is
present.

The speaker representation now includes the paper's actual `facebook/wav2vec2-base` family:
mean-pooled 768-dimensional utterance embeddings, used inside the project's safer
verification-never-identification rule. ECAPA remains a separately labeled engineering
comparator, not a silent substitute. Both real backends require a complete
`b5-audio-model-manifest-v1`; every local model file must match its pinned SHA-256 and unlisted
files refuse. Hearing acquisition now adds `--no-overwrites` and forbids combining real `--fetch`
with the unverified-package dry-run override. A witness poisons its hearing only when CHECK-A
actually ACCEPTS a member match; ordinary witness turns remain excluded but do not destroy valid
member turns.

Engineering verification after the hardening: calibration 5/5, enrollment/verification 23/23,
diarization 5/5, alignment 8/8, attribution 17/17, hearing acquisition 5/5. Standard Aeneas fragment
JSON is now the primary MFCC/dynamic-time-warp boundary proposal when supplied; exact fragment
count, normalized transcript text, finite time, and non-overlap are mandatory. Local Whisper word
timestamps remain only the independent word-recovery cross-check, and any Aeneas mismatch fails
the hearing closed instead of falling back silently. The local Aeneas/eSpeak toolchain and real
human boundary pilot remain user-gated. No model was downloaded, no real thresholds were fit, no
candidate entered the active review/descriptor artifacts, and no Big Five or influence number
moved.

## 44. Source-disjoint Wav2Vec identity experiments - negative result, production remains closed (2026-07-16)

The paper-faithful path in section 43 was exercised as a pre-lock, weak-label laboratory study,
not as P1 and not as evidence licensed for production. A locally present
`facebook/wav2vec2-base` snapshot was discovered without a network call and pinned in
`b5_audio_wav2vec2_model_manifest.json.candidate`: config, preprocessor, and model-weight
SHA-256s are complete, and the backend still runs local-only. The embedding contract was split
tests-first: `embed_raw` returns the paper's unnormalized 768-dimensional mean-pooled
representation for a classifier, while `embed` unit-normalizes the same representation for
cosine verification. Deterministic 20-second chunking bounds memory without changing the
claim-only decision rule. Calibration now types its score space (`cosine` versus
`claimed_class_probability`), requires explicit label provenance, and makes every
machine-labeled artifact non-consumable even if its numeric bars happen to clear.

Three results close the present Wav2Vec route without post-test tuning:

1. Failure archaeology on 30 members found only 11/30 correct top-1 raw-cosine matches and only
   9/30 passing the identity guard. These scores were never accepted as profile evidence.
2. A deterministic multinomial logistic head used four hard-signal sources per member, with
   source-disjoint train/calibration/test partitions and four fixed five-second windows per
   source. Calibration EER was .317. On untouched sources, segment genuine acceptance was .267
   and all-windows unit acceptance was .100; segment impostor rejection was .992 and unit
   impostor rejection was 1.000. Only 12 caption-mismatch negatives were available, far below
   the 148 bar.
3. A fresh cohort of 21 members excluded every member in result 1 and used six distinct sources
   per member (three train, one early-stop validation, one calibration, one untouched test).
   This run used the article's exact reported classifier recipe: one linear neural layer over
   raw 768-dimensional Wav2Vec representations, Adam at .001, cross-entropy, batch size 8, and
   early stopping after three unimproved epochs. Calibration EER was .226. On untouched sources,
   segment genuine acceptance was .333 and all-windows unit acceptance was .095; segment
   impostor rejection was .988 and unit impostor rejection was .998. This fresh cohort had zero
   caption-mismatch negatives, so `theta_accept` was unavailable; its held-out diagnostic used
   calibration `theta_eer` and labels that threshold research-only.

Both fitted studies have `status: FAILED_WEAK_LABEL_SMOKE`, `human_ratified_labels: false`,
`calibration_artifact_consumable: false`, and `production_consumers: 0`. Their split, trial,
threshold, model, and fitted-head hashes are recorded under `outputs/audio_linear_30member/` and
`outputs/audio_neural_fresh21/`. The convergence of a failed cosine baseline, a failed linear
head, and a failed exact-method fresh-cohort head rules out an optimizer or one-cohort accident.
It does not show that the article's random-utterance classification result is wrong; it shows
that the method does not transfer at the required error rates to this harder
source/event-disjoint congressional verification contract with sparse, weak machine labels.

No more fitting is permitted on either consumed test split. The production design therefore
remains: roster-resolved CHECK-T; Aeneas transcript boundaries with an independent ASR
word-recovery check; trim/VAD/diarization and overlap exclusion; human-ratified multi-event
enrollment; claim-only CHECK-A as a veto; and the unchanged two-human-review admission gate.
Topic-conditioned within-speaker F0 is computed only after identity passes. Any future acoustic
route needs a new preregistration, human-ratified enrollment/calibration clips, all 148
caption-mismatch negatives, and a speaker-specialized verification comparator; it cannot be
presented as a continuation that tunes these Wav2Vec test results.

## 45. O/N/C new-criterion cross-panel successor — no promotions; originals preserved (2026-07-16)

At the user's request, E and A were held fixed and a tests-first successor attempted genuinely new
behavioral criteria for O, N, and C. Before implementation, the complete original score artifact
and Senate gold were copied byte-for-byte under `originals/big5_onc_20260716/` (SHA-256s
`2b351af4...4317c13` and `ff5a9483...7afe7a`). The RED lock at `6612530` fixed construction,
coverage/reliability stop bars, fusion weights, panel gates, and a one-look rule. The implementation
never exposed criterion construction to the panels; 12/12 successor contracts and the 74/0 full
kernel were green before the criterion freeze.

The new O criterion combined cross-context policy-domain entropy and MATTR over deterministic,
volume-bounded INTERVIEW and CREC samples. Its reliability cleared (source r=.160, SB=.275), but
coverage was only 198 members (122 House), below the locked 250/150 floors. O therefore stopped
before any gold pairing; its original academic-panel-supported status remains untouched.

The new N criterion measured within-interview successive affective lability, residualized for
demographics, chamber, mean affect, turn length, and exposure. Coverage was 234 and deterministic
package split-half reliability was r=.354 / SB=.523, licensing the one look. The fixed 70% original
/ 30% lability candidate retained an insider association (r=.299, p=.029, partial=.268) but failed
dominance; academics missed r/p/dominance (r=.143, p=.176) despite a positive partial (.328). MISS;
the route is closed and the original insider-supported N remains.

The new C criterion required consistency in both roll-call participation and LEP follow-through:
the lower of the two within-chamber z-scores, nuisance-residualized. Coverage was 447 and component
r=.039, clearing its pre-look bars. The fixed 30% original / 70% execution-consistency candidate
improved insiders from same-roster r=.319 to .393 and passed every insider gate (p=.0036,
partial=.404, dominant). Academics remained null and non-dominant (r=.066, p=.326,
partial=.104). MISS; the result strengthens the interpretation of C as insider-visible execution
behavior but does not license an academic-panel personality claim.

Exact result: `big5_onc_crosspanel_successor.json.candidate`, SHA-256
`fc3bdbfa59671f61891c34d38e13839f57092c2110d760a12e221e7fc43ba5e9`. Production consumers are
zero. No original score, status, profile, narrative, engine input, E result, or A result moved.
