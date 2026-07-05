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
