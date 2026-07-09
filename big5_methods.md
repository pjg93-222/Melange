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
