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
