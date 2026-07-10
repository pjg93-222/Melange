---
name: psychometrics-reference
description: Measurement-theory reference for this project, written for readers with zero statistics training. Load it when a task involves interpreting or citing any Big Five / disposition / receptivity NUMBER — reliability (split-half, Spearman-Brown), validity (convergent, discriminant, criterion, diagonal dominance), halo, CT-CM, confounds (the gender-confounded ES), statistical power, the 3/5 instrument result, the A- grade, or the susceptibility formula — or when reviewing text that makes a psychometric claim ("validated", "reliable", "5/5", "cross-modally validated"). Also load it before proposing any new trait measure or validation test, to learn why past ones failed. It does NOT cover how to run the prereg/one-look process (moneyball-research-methodology), how to operate the receptivity pipeline (moneyball-run-and-operate), analysis recipes like running your own power study (moneyball-proof-and-analysis-toolkit), or the exact approved claim wordings (moneyball-docs-and-claims).
---

# Psychometrics Reference — measurement theory as practiced here

This project estimates personality-like "dispositions" for 533 members of the US Congress and feeds them into a lobbying-influence model. Because those numbers move real targeting decisions, the project holds them to formal measurement standards — reliability, validity, confound control — and has a long recorded history of measures that LOOKED fine and were proven broken. This skill teaches the measurement concepts from zero and then gives the project's actual numbers, verified against the repo's document of record (`big5_methods.md`, at repo root) and the pre-registration files (`big5_*_prereg.md`). Read the concepts sections in order if you have no statistics background; use the quick-reference table if you just need a number checked.

## When NOT to use this skill

- Running/locking a pre-registration, deciding whether a "look" is allowed, retiring a route → **moneyball-research-methodology** (it owns the scientific process; this skill owns the concepts and results).
- Regenerating `behavioral_dispositions.json` / `member_receptivity.json`, chain order, dials → **moneyball-run-and-operate** and **moneyball-config-and-flags**.
- Step-by-step recipes (compute a split-half yourself, run a power study, build a plant battery) → **moneyball-proof-and-analysis-toolkit**.
- Exact sentence-level wording allowed in docs/commits for each validated claim → **moneyball-docs-and-claims**.
- The story of each dead-end investigation → **moneyball-failure-archaeology**.
- Influence/network math (cascades, greedy seeding) → **influence-modeling-reference**.

## Quick reference — the numbers and the forbidden claims (as of 2026-07-09)

| Fact | Value | Source |
|---|---|---|
| Instrument grade | **A− (FINAL — user canceled the panel; never re-propose raters)** | `big5_expert_panel_prereg.md:3-7`, `big5_methods.md` §12/§16 |
| Per-trait text instrument result | **3/5** diagonal-dominant: O +.198, C +.277, E +.552 pass; A +.183 miss (not discriminant); ES +.149 miss | `big5_behavioral_instrument_prereg.md` RESULT |
| ES cross-modal (voice) | +0.208 pass **stands as history only**; GENDER-CONFOUNDED (partial r = −0.029, p .7151) | `big5_es_robustness_prereg.md` RESULT |
| Audio program's real finding | eGeMAPS voice validly reads **E (+.284) and ES (+.298) vs Pink**; audio-A null twice | `big5_audio_faithful_prereg.md` RESULT; `big5_methods.md` §14 |
| CT-CM halo modeling | **failed 4×, permanently CLOSED — DO NOT re-run** | `big5_halo_neuroticism_prereg.md` RESULT; §15 |
| Round-4 power study | true r=.40 unstable at n=201 (3/5, range +0.015…+0.372); reliable from n≈250 | `big5_n_matrix_prereg.md` Addendum 2 |
| Round-5 stratum diagnostic | median recovery +0.132 < +0.15 bar (2/5) on MEM_A=290 → stratum genuinely signal-poor | `big5_a_matrix_prereg.md` Addendum 1 |
| Susceptibility formula (engine) | `.40*coop + .30*N − .20*dil − .10*dom`, N slot = reactivity_z | `fec/receptivity_layer.py:119-121` |
| Reactivity reliability | SB ≈ .43 (code of record); modest — low-weight by design | `fec/behavioral_dispositions.py:97` |
| Dominance disposition | **277/533 (52.0%) share one identical value (−0.381)** — a constant, not a measurement, for half the roster | verified against live `behavioral_dispositions.json` 2026-07-09 |
| coop_v2 criterion | SB .873/.821; breadth entanglement +.708 → −0.140; engine promotion **granted+shipped 2026-07-10, merged to main** (@94f09cf; `RECEPT_COOP=v2`) | `big5_a_matrix_prereg.md:42-46` |

**Never write any of these** (each is a documented mis-claim; see `moneyball-docs-and-claims` for approved wordings):
- "5/5 traits validated" or "all five traits validated" — superseded; the real look was **3/5** (`big5_es_robustness_prereg.md:52-54`).
- "ES is cross-modally validated" without the gender-confound caveat.
- "A passed via audio" — FALSE. Audio-A was null twice; audio's real pass was E+ES.
- "shipped v2 C = +.24" — the fact-check corrected it to **+.13** (`big5_methods.md` §16).
- Proposing a human rater panel — canceled by the user; A− is final.

---

## 1. Statistics from zero (the five ideas everything below uses)

**Correlation (r).** A number from −1 to +1 measuring how much two lists of numbers move together across the same people. r = +1: whoever is high on one is exactly proportionally high on the other. r = 0: knowing one tells you nothing about the other. r = −1: perfectly opposite. In this project r ≈ .15 is a small-but-real effect, r ≈ .30 is strong, and r above .50 is rare and usually means the two measures share machinery rather than both measuring a real trait well. r on ~200–500 people is NOISY: the same true effect can come out anywhere in a wide band (see §9, power).

**z-score.** A raw number rescaled to "how many standard deviations above/below the group average." z = 0 is average, z = +2 is unusually high. Every trait score in this project is a z-score **relative to this specific corpus of members** — a member's cooperation_z = +1.0 means "more cooperative-looking than the average member of this Congress," never an absolute claim about the person. Disposition z-scores are computed **within chamber** (House and Senate separately) wherever the raw scale differs by chamber (`fec/behavioral_dispositions.py:23,33-43`); lexical trait z-scores are within the 533-member pool. Consequence: scores are not comparable across corpus rebuilds or across Congresses, and "the roster changed" silently changes every score.

**Permutation p-value.** "If there were truly no relationship, how often would shuffling the labels produce an r this big by luck?" p < .05 means less than 5% of random shuffles do. The project uses exact permutation tests (typically 5,000 shuffles with a pinned random seed) rather than textbook formulas, because formulas assume things small weird samples violate. A pass here always requires BOTH a minimum r AND a permutation p.

**Partial correlation (confound control).** The correlation between A and B *after removing* everything a third variable C explains in both. Mechanically (the Frisch–Waugh method used here): predict A from C, predict B from C, correlate the leftovers. If r(A,B) is +0.21 but the partial given gender is −0.03, the "relationship" was really both A and B tracking gender. Confound partials are GATING bars in every recent prereg — this exact scenario happened (§8).

**Held-out / out-of-fold prediction.** When a model is *fit* to data and then *scored* on the same data, its score is inflated (it memorized noise). All supervised results here are "held-out": the model is trained on part of the roster and scored only on members it never saw, repeated across folds. A held-out r cannot be sign-hacked or overfit the same way an in-sample r can — this is why the project trusts held-out numbers and distrusts hand-built composites (the mis-signed acoustic-ES composite, `big5_es_crossmodal_prereg.md:3-12`, is the cautionary tale).

## 2. The Big Five, and why a lobbying model wants them

The **Big Five** (OCEAN) is psychology's standard five-dimension summary of personality:

| Trait | Everyday meaning | Why the lobbying model cares |
|---|---|---|
| **O** — Openness | curiosity, breadth of interests | engages across novel policy domains → persuadable on new issues |
| **C** — Conscientiousness | diligence, follow-through | does the work; less swayed by momentary pressure |
| **E** — Extraversion | sociability, dominance | takes meetings, holds the floor; dominance resists pressure |
| **A** — Agreeableness | cooperativeness, deference | the core susceptibility trait (agreeable/deferential members yield to social pressure) |
| **ES** — Emotional Stability | calm under stress (its inverse is **N**, Neuroticism; N = −ES exactly) | high-N members degrade under pressure (Byrne et al. 2015 "choking" result) |

The model's use is narrow and downstream: a **susceptibility-to-pressure composite** (`fec/receptivity_layer.py:121`) that scales how much lobbying pressure, money, and cascade influence move each member. The engine does NOT read Big-Five trait scores; it reads *behavioral dispositions* filling the same construct roles (§5). The Big-Five text/LLM instruments are DISPLAY-ONLY on the member desk ("firewall": no engine reads trait scores — `big5_methods.md` §15). Keep that firewall in mind whenever someone worries a trait-measurement defect corrupts rankings: it can't, by construction, unless someone promotes an instrument into the engine (a user-gated ratified step).

## 3. Reliability — does the measure agree with itself?

**Reliability** asks: if you measured the same person twice with the same instrument, would you get the same answer? A measure can be reliable and still measure the wrong thing (see validity, §4), but an *unreliable* measure can't be valid at all.

**Split-half + Spearman-Brown (SB).** The project's workhorse: split each member's raw data into two halves (e.g., odd vs even utterances, or odd vs even bill IDs), score each half separately, correlate the two half-scores across members, then apply the Spearman-Brown correction `SB = 2r/(1+r)` (which adjusts for the fact that each half has only half the data). SB near 1.0 = the measure is stable; SB near 0 = the score is mostly luck of the draw.

**The attenuation ceiling — the single most useful rule here.** A measure's validity correlation against anything can never exceed √(its reliability). Example stated pre-look in `big5_n_matrix_prereg.md:121-122`: the reactivity criterion's SB ≈ .43, so any text instrument's observed r against it is capped at ≈ √.43 ≈ .66 × the text-side ceiling. When you see a modest r against a noisy criterion, part of the "miss" is the criterion's noise, not the instrument's failure.

**Split-half is easy to get artifactually wrong.** Three documented traps:
1. **A constant survives any split.** A binary flag (e.g., committee_leader) that is identical for most members lands identically in both halves, manufacturing a huge fake SB. This inflated an early dominance SB to ~.96 when its real interaction-signal SB is ≈ .50.
2. **The split must break the data unit that repeats.** Splitting breadth by hashed (section, member) pairs forced each section wholly into one half and produced SB = .037; the corrected bill-id split gave .81. A bizarre SB is a *split-design* bug before it is a finding.
3. **A sorted (non-random) split can land on a lucky edge.** Reactivity's code-of-record SB is .43 (`fec/behavioral_dispositions.py:97`); an adversarial re-read found random splits average lower (~.27–.40 band). Treat .43 as the value of record and reactivity as a modest measure either way — it is deliberately low-weight (.30 slot, shrunken, neutral-fallback).

### The dispositions' actual reliability (dependability audit, 2026-07-09)

A six-auditor adversarial reliability read of the engine-input dispositions. **The audit's verdict is cited in-repo** (`big5_a_matrix_prereg.md:7,21` and `fec/coop_v2_candidate.py:6` invoke its "volume proxy" indictment), **but its full number table is session-recorded, not in a repo doc** — the SB values below are marked accordingly; coverage counts and the dominance-constant fact were independently re-verified against the live artifact on 2026-07-09.

| Disposition (role) | SB (split-half) | Coverage /533 | The catch |
|---|---|---|---|
| visibility_z (E-sociability) | ≈ .99 † | 481 | near-perfect reliability, but its two parts are ~+.97 collinear — it is an interview-VOLUME census ("how much airtime"), not sociability per se |
| breadth_z (O) | .77–.81 † (bill-id split) | 511 | correlates ~.83 with raw distinct-bill count → largely an issue-VOLUME proxy |
| cooperation_z (A) | ≈ .75 † composite (a circulated **.867 was a mislabel** — one component alone) | 513 | 2/3 of it is cosponsorship volume; entangled +.708 with breadth (`big5_a_matrix_prereg.md:6`). The only truly "cooperative" part (bipartisanship) is near-noise on its own. Fix built: **coop_v2**, SB .873/.821, entanglement → −0.140 — promotion granted+shipped 2026-07-10, merged to main (`RECEPT_COOP=v2` @94f09cf; coverage 315/533, uncovered → neutral 0) |
| reactivity_z (N) | .43 (code of record; adversarial re-read lower †) | 207 | modest but genuinely NEW signal — orthogonal to all other dispositions (worst \|r\| ≈ .15), party/gender-clean; keep low-weight |
| dominance_z (E-dominance) | ≈ .50 † on the 132–207 members with real interaction data | 533 nominal | **coverage mirage: 277/533 (52.0%) share the single identical value −0.381** (committee_leader=0, no interview data) — verified live 2026-07-09. For half the roster this is a constant, not a measurement |
| diligence_z (C) | not meaningfully splittable † (saturated) | 529 | roll-call participation is a near-census: ~90% of members vote near the chamber max, so the z mostly encodes tenure/absence; its 3 components share ~zero variance; largest demographic confounds of the six |

† session-recorded value from the 2026-07-09 dependability audit; not tabulated in any repo doc. If a decision hinges on the exact number, re-derive it (split-half recipe in `moneyball-proof-and-analysis-toolkit`) rather than citing this table as primary evidence.

**What "a constant for 52% of members" does to a correlation.** A constant carries zero information: it has no variance, so it cannot co-vary with anything. Any full-roster correlation involving dominance_z is really computed on the ~48% who have actual measurements, diluted by a frozen block that drags r toward whatever the constant's position implies; and naive split-half on it is inflated (trap 1 above). Practical rule: never propose dominance_z as a validation criterion or a new-signal source, and treat any correlation involving it as an underestimate computed on half the roster.

**The cross-cutting finding:** the reliable dispositions (visibility, breadth, cooperation-v1) are reliable *because they are volume counters* — activity/prominence proxies wearing trait names. High reliability + doubtful construct is a recurring pattern here; reliability alone proves nothing about meaning. That is why validity (§4) has its own machinery.

For contrast, the DISPLAY-side lexical instrument's reliability (a different family — do not mix these up with the disposition table): pooled lexical split-half SB O .81 / C .75 / E .78 / A .60 / ES .76 (`big5_methods.md` §2.2).

## 4. Validity — does it measure what it claims? (and the halo problem)

Three types of validity evidence, in this project's vocabulary:

- **Convergent validity**: the measure correlates with an independent measure of the *same* trait. Here: lexical Big-5 vs the RKH published congressional estimates, r .42–.52 (`big5_methods.md` §2.1) — with the permanent caveat that RKH is itself text-derived, so this is text-vs-text ("shared method") and inflated.
- **Discriminant validity**: the measure correlates with its own trait's evidence MORE than with other traits'. This is where most attempts here die.
- **Criterion validity**: the measure predicts an independent *behavior* the trait theoretically implies (C should predict roll-call participation; A should predict cross-party cooperation). Since the §15 reframe, **per-trait external criterion validity is the project's field-correct bar** — not trait-vs-trait correlations.

**Halo** = a spurious correlation between two different traits' scores caused by the *method*, not the people. Text read by any scorer carries an overall tone: members who "sound good" get rated up on everything at once. Two measured halos of record:
- Lexical **C–E halo = .68** (`big5_methods.md` §2.6) — pooled lexical C and E scores correlate .68 across members, far above what real C and E share.
- Pink (LLM instrument) **A–ES = .653**, vs the RKH benchmark of .443 (House) — so roughly .44 of it is population-real trait covariance and ~.21 is text-tone halo (`big5_methods.md` §11).

Crucially, the halo was proven **functionally shallow**: despite A–ES = .653, only Pink-A predicts the A-criterion (partial r +.100, p .034, controlling ES; Pink-ES does not, +.049 n.s.) — shared TONE, not shared meaning (`big5_methods.md` §15). The halo is a display caveat, not a validity crisis.

**Why the lexical Big-5 was indicted (the founding event of the behavioral basis).** A pre-registered, label-free "nomological" battery — 13 directional trait→behavior predictions from theory — tested whether lexical scores predict the behaviors the traits imply (`big5_methods.md` §3b, `big5_nomological_prereg.md`). Result: lexical **C came out REVERSED** on roll-call participation (higher "conscientious" text score → *less* participation), lexical **E was just broadcast talkativeness** (r +.28 with interview count, −.09 with tweet volume), overall sign agreement 5/8 with r_alerting −0.76. A measure that predicts theory-specified behavior backwards is not measuring the trait. The one survivor: lexical A → cooperation (+.11, FDR-significant). Consequence: engine inputs were rebuilt FROM behavior (§5), and the fixed-weight lexical instrument (v1) was demoted; its successor **v2** learns weights against the behavioral criteria with honest held-out CV (held-out A +.14, **C +.13**, E +.34, O +.20 — `big5_methods.md` §3c; the C value was once mis-quoted as +.24, corrected in §16).

## 5. Behavioral criteria vs text instruments — the project's anchoring decision

The project's central measurement stance: **when the behavior IS the construct, measure the behavior.** Cooperation is cross-party cosponsorship; diligence is showing up to vote. These are called **behavioral dispositions** (producer `fec/behavioral_dispositions.py` → `behavioral_dispositions.json`) and they are the ONLY personality-adjacent engine inputs. Text/LLM instruments remain as display-layer second opinions and as things to *validate against* the dispositions.

| Disposition | Construct role | Data source (all non-text behavior except reactivity's structure) |
|---|---|---|
| cooperation_z | A | bipartisanship ratio + cosponsor network degree + count cosponsored (`behavioral_dispositions.py:53-56`) |
| diligence_z | C | roll-call participation + LEP legislative follow-through + hearing participation (`:58-81`) |
| dominance_z | E-dominance | interview turn statistics (words/turn, floor-holding, floor defense) + committee leadership (`:83-90`) |
| visibility_z | E-sociability | broadcast interview count + program breadth, ≥3 attributed interviews (`:111-115`) |
| breadth_z | O | # distinct bill Sections with any sponsor/cosponsor role (`:117-126`) |
| reactivity_z | N | live-interview cutoff proneness (share of turns cut off mid-speech), per-program z, coverage-shrunken (`:92-109`) — shipped round 3 as the engine's N slot, retiring its last text-derived leg |

Missing data → `None` → neutral 0 downstream, "never an invented disposition" (`behavioral_dispositions.py:23-24`).

**The epistemics distinction that resolves most confusion:** a disposition is *valid by construction for its ROLE* (it is a measured behavior placed in a construct slot; there is no criterion look for it to fail — `big5_methods.md` §19), while a text *instrument* claiming to read a trait must EARN validity through a pre-registered look against a disposition used as criterion. And per the CMC result (§10): behavioral data is a **criterion**, not an independent trait *method* — correlating a text instrument with behavior tests criterion validity, but cannot serve as the "independent trait comparator" that would lift the grade to A (only human raters or self-report could; both closed).

## 6. Diagonal dominance — the instrument bar, and the real 3/5 result

Arrange a matrix: rows = each trait's text model prediction, columns = each trait's behavioral criterion. **Diagonal-dominant** means each model correlates with its OWN criterion more than with any other trait's — the discriminant-validity test in matrix form (an MTMM, multitrait-multimethod matrix, in the classic Campbell–Fiske sense).

The look of record (`big5_behavioral_instrument_prereg.md` RESULT, 2026-07-09, N=456; bars: held-out r ≥ +0.15 AND exact perm-p < .05 AND diagonal-dominant):

| model \ criterion | O | C | E | A | ES |
|---|---|---|---|---|---|
| pred_O | **+.198** | +.137 | +.028 | +.187 | +.079 |
| pred_C | +.117 | **+.277** | −.146 | +.149 | +.126 |
| pred_E | +.023 | −.096 | **+.552** | −.035 | −.148 |
| pred_A | +.197 | +.210 | −.083 | **+.183** | +.066 |
| pred_ES | +.092 | +.155 | −.303 | +.072 | **+.149** |

- **O, C, E PASS** (all perm-p .0002, all diagonal-dominant). E carries a genre caveat (corpus and criterion share the interview modality).
- **A MISS on dominance only**: +.183 is real (perm-p .0004) but pred_A reads C's and O's criteria slightly higher → "criterion-valid, not discriminant."
- **ES MISS**: +.149, 0.001 under the bar, and anti-reads E at −.303.

**The honest count is 3/5 — NEVER "5/5".** (A "5/5"/"all five validated" sentence existed briefly on the strength of the voice-ES pass and was formally superseded when that pass was shown gender-confounded — `big5_es_robustness_prereg.md:52-54`.) The current per-trait truth to state: *O/C/E criterion-valid AND diagonal-dominant; A criterion-valid but not discriminant; ES measured, no clean independent validation* (`big5_methods.md` §17-§18). For contrast: Pink's raw LLM trait scores were **0/5** diagonal-dominant against behavior — supervising text features per-trait is what recovered real diagonal structure.

## 7. CT-CM in plain words — and why it missed four times

**CT-CM (correlated traits, correlated methods)** is a latent-variable model that tries to split each observed score into "true trait" + "method flavor" (e.g., the LLM judge's tone-halo) by triangulating across multiple instruments. Intuition: if text-A and text-ES are entangled by tone, add a NON-text A or ES indicator; the model can then apportion the shared variance to a method factor and read the de-haloed trait correlation.

It requires the extra indicator to be (a) genuinely independent of the contaminated method and (b) strong enough to anchor a factor. Four attempts, four failures (`big5_halo_neuroticism_prereg.md` RESULT):
1. lexical Blue anchor — collinear with the text it was meant to check;
2. embedding Blue anchor — collinear again;
3. audio-ES anchor — too weak (r = −.25);
4. conversational-dynamics N anchor — empty (converged +.013 with text ES; latent A–ES came out **.928**, worse than the raw .653).

The fourth prereg carried a pre-declared **stopping rule**, honored: the derived-measure route is EXHAUSTED; the halo is irreducible without NEW data. Then §15 delivered the deeper lesson: the four attempts were optimizing a **self-invented quantity** — the field's own standard (including RKH, the anchor paper) never uses trait–trait correlation as a validity criterion; it uses per-trait external criterion validity, which the project now does. **DO NOT re-run CT-CM in any form** (`big5_methods.md` §15). If you feel tempted, re-read failure #4.

## 8. Confounds — the repo's recurring failure mode

A **confound** is a third variable driving both sides of a correlation. This project's confounds of record are **gender, party, and volume** — every recent prereg makes a confound partial a GATING bar, because each of these has actually produced a false positive:

- **The gender-confounded ES (the mandatory caveat).** Voice features (eGeMAPS) → text-ES scored held-out r = **+0.208**, perm-p .0002, ES-specific — a clean-looking pass (`big5_es_crossmodal_prereg.md` RESULT). The locked robustness retest: partial r given gender and party = **−0.029** (perm-p .7151); within-men r = −.016 (n=282), within-women r = −.036 (n=113) (`big5_es_robustness_prereg.md` RESULT). The voice model was predominantly reading *speaker sex* (pitch-family features encode sex almost perfectly) and text-ES differs by sex in this roster. Verdict of record: **CONFOUNDED**. The +0.208 stands as history (its own locked bars were met; history is not rewritten) but the validation claim carries the gender-confound caveat *everywhere it is cited*. Never write "ES cross-modally validated" unqualified.
- **Lexical N carried a gender-language artifact**: swapping the engine's N slot from text-N to behavioral reactivity_z REDUCED demographic tilt in targeting (susceptibility gender loading +.327 → +.198) — women had been reading as more pressure-susceptible by word-style, not behavior (`big5_methods.md` §19).
- **Volume**: cooperation_z was 2/3 cosponsorship volume (§3 above); round-5 put log-volume directly in the gating partial's conditioning set (`big5_a_matrix_prereg.md` bar 5).
- **Party** is always controlled alongside gender (members' text style and voice register differ by party demographics).

Also note this direction of error: a caveat can only be ADDED to a settled result via a **locked robustness look with pre-declared consequences** — exactly how the ES caveat legitimately landed. Never reverse or caveat a settled result under conversational pressure (session-ratified, 2026-07; see `moneyball-change-control`).

## 9. Statistical power and draw-stability — why two rounds retired WITHOUT a look

**Statistical power** = the probability your test detects an effect that is really there, at your sample size. Underpowered tests don't just miss — they return wildly unstable estimates, so a single test ("one look") at low n is a coin flip that permanently burns the question.

The project measures this empirically with **plant recovery**: synthesize a fake trait signal of known true strength (e.g., r = .40) into the real feature matrix, and check whether the real machinery recovers it. Two decisive results:

- **Round-4 power study** (`big5_n_matrix_prereg.md` Addendum 2): a TRUE r=.40 planted signal at the actual reactivity coverage n=201 passed the bar only **3/5 seeds, with recovered r ranging +0.015…+0.372** — extreme draw variance; from **n≈250 it passes 5/5**; a true r=.50 passes 5/5 even at 201. Consequence: the round-4 look was refused by its own battery and the route is **DATA-GATED at MEM_N ≥ 250** (201 as of 2026-07-09).
- **Round-5 stratum diagnostic** (`big5_a_matrix_prereg.md` Addendum 1): on the actual MEM_A=290 stratum (members with coop_v2 coverage), five seeded plants of a true r=.40 recovered median **+0.132 — below the +0.15 bar (2/5 pass)** — versus ~.195 for random rosters of the same size (round-4 study). So the refusal was NOT draw luck: that particular stratum carries genuinely less recoverable text signal (homogeneous profiles). Route **DIAGNOSTIC-GATED** (reopens when the pinned synthetic diagnostic passes ≥3/5; synthetic-only, safe to check any time).

Program-level lesson, twice replicated: masked-stratum looks at n≈200–300 cannot see signals below the E-class (~.5) with the +0.15 bar (`big5_methods.md` §21). Before proposing ANY new validation test, ask "can this n even see the effect?" — and remember RETIRED WITHOUT A LOOK ≠ MISS: those routes are neither validated nor closed.

## 10. Method variance across modalities — what audio actually validated

**Method variance** = the part of a score contributed by HOW you measured rather than WHO you measured. The project has three modalities: text (speeches/interviews/tweets), audio (voice acoustics — eGeMAPS, 88 standard features), and votes/cosponsorship behavior. Same-modality comparisons (text vs text, e.g., anything vs RKH) are always inflated by shared method; the whole point of the audio program was a genuinely different modality.

The audio record, precisely (get this right — it is the most mis-remembered result in the project):
- **What audio validly measures**: the full 88-feature model read **Pink-E at held-out r = +.284 (perm-p .030) and Pink-ES at +.298 (perm-p .017)** — a genuine partial replication of the literature (voice carries the arousal traits E and ES) (`big5_audio_faithful_prereg.md` Bar 1b).
- **Audio-A was null TWICE**: pilot 1 (+0.129, below its permutation floor +0.165 — `big5_methods.md` §14) and the faithful replication (−0.043, p .69; audio's own A–ES came out .819 — it has no A read at all). **"A passed via audio" is FALSE.**
- Audio-E is **redundant** with text for measurement (fusion adds ~nothing), so audio never became load-bearing; and the voice→text-ES convergence (+.208) later fell to the gender confound (§8).
- The **CMC** look (`big5_methods.md` §13) settled the modality question for votes: Pink vs behavioral dispositions as a cross-method MTMM MISSED (mean same-trait r +0.075 < +0.12 bar; only A×cooperation +0.173 was real) — with the honest interpretation that behavior is a *criterion*, not a trait *method*, so the shared-method caveat on the RKH convergence is permanent and priced into A−.

## 11. The grade ledger and the engine formula

**What the letter grades mean here.** Grades are analyst shorthand *relative to a named benchmark class*, not absolute quality. The instrument grade **A−** means: top of the published elite-speech text-personality class (the §12 literature benchmark: convergence .42–.52 exceeds every r-scale published ceiling; process transparency best-in-class; held below A by the shared-method RKH anchor, the pooled-lexical MTMM failure, and the weak ES). It was independently ratified by a 32-agent judge panel (B+/A−/A−/A−) in §16. **A− is FINAL**: the only path to A was an independent-trait anchor (human rater panel), which the user canceled 2026-07-09 (`big5_expert_panel_prereg.md:3-7`) — never re-propose raters; the panel scorer hard-refuses its look while the prereg is unlocked. The dependability audit's letter grades (§3 table: visibility A−, breadth B+, cooperation B, reactivity C+, dominance C−, diligence D) use the same convention: a B+ is "reliable, construct caveat"; a D is "do not trust the signal, trust the neutral-fallback."

**The one formula the engine actually runs** (`fec/receptivity_layer.py:119-126`):

```
susc_trait = .40*cooperation_z + .30*N − .20*diligence_z − .10*dominance_z
```

where **N = reactivity_z** (the behavioral N slot, default `RECEPT_N=behavioral`; missing → neutral 0; `RECEPT_N=text` reverts the slot to shrunken lexical N). The trait composite is then blended with the persona channel at `PERSONA_W=0.30` (user-ratified KEEP — do not propose removal; it reopens only on a failed 3+ rater panel to Bono & Loomis standards; session-ratified, 2026-07) and clipped into bounded multipliers. The A/N-positive, C/E-negative structure follows Byrne et al. 2015 (N degrades decisions under pressure; A adds under social pressure); the C−/E− dampeners are design priors, NOT Byrne findings (`receptivity_layer.py:8-13`). Weights are local calibration, decision-robust per `fec/receptivity_sensitivity.py` (9/9 variants keep the top-20). Measurement-theory reading of the formula: its .40 slot is carried by a volume-entangled criterion (coop v1 — replacement candidate built, user-gated) and its −.20/−.10 slots by the two weakest measures (diligence D, dominance C−) — a known-open concern recorded in the dependability audit; changing any weight is Paul's decision, never a silent code edit.

## 12. Checklist before you cite or produce a psychometric number

1. Is the claim in the LIVE set? (O/C/E valid+dominant; A valid-not-discriminant; ES no clean validation; A− final.) If it's not, it's CLOSED or GATED — check `big5_methods.md` §17–§21 and the prereg's RESULT before repeating it.
2. Does it carry its mandatory caveat? (ES → gender-confounded; E → genre-composition; RKH convergence → shared-method; v2 C → +.13.)
3. Is your correlation computed on a slice with a constant in it (dominance) or a saturated census (diligence)?
4. Is your n big enough for the bar? (r=.40-class effects need n≳250 here.)
5. Are gender, party, and volume partialed?
6. Held-out, not in-sample? No hand-chosen signs?
7. If it's a NEW claim: it needs its own prereg → `moneyball-research-methodology`. One fact, one home: the wording ledger lives in `moneyball-docs-and-claims`.

---

## Provenance and maintenance (2026-07-09)

All numbers above were re-verified against the repo on 2026-07-09 (`big5_methods.md` 537 lines, §1–§21, §22 reserved for the Vote Smart RESULT). Volatile facts and how to re-check them — run from the repo root, e.g. `cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"` (or your worktree). **Never run `fec/*.py` scripts to "check" anything — import == execution and they write to the live data tree; every command below is read-only.**

- 3/5 result + matrix: `Select-String -Path "big5_behavioral_instrument_prereg.md" -Pattern "VERDICT: 3/5"`
- ES gender confound (partial −0.029, p .7151): `Select-String -Path "big5_es_robustness_prereg.md" -Pattern "CONFOUNDED|-0.029"`
- ES +0.208 history + addendum: `Select-String -Path "big5_es_crossmodal_prereg.md" -Pattern "0.208|ADDENDUM"`
- Audio E/ES pass, A null: `Select-String -Path "big5_audio_faithful_prereg.md" -Pattern "0.284|0.298|-0.043"` and `Select-String -Path "big5_methods.md" -Pattern "\+0.129"`
- CT-CM 4 failures + stopping rule: `Select-String -Path "big5_halo_neuroticism_prereg.md" -Pattern "4th CT-CM|STOPPING RULE"`
- Power study (n=201 unstable, ≥250 reliable): `Select-String -Path "big5_n_matrix_prereg.md" -Pattern "n=250|0.015"`
- Round-5 diagnostic (median +0.132 < +0.15): `Select-String -Path "big5_a_matrix_prereg.md" -Pattern "median \+0.132"`
- coop_v2 SB .873/.821 + entanglement: `Select-String -Path "big5_a_matrix_prereg.md" -Pattern "\.873"`
- Susceptibility formula + N slot: `Select-String -Path "fec\receptivity_layer.py" -Pattern "susc_trait=|RECEPT_N"`
- Reactivity SB .43 / burst .04 (do-not-re-add): `Select-String -Path "fec\behavioral_dispositions.py" -Pattern "SB=.43|SB=.04"`
- Panel canceled / A− final: `Select-String -Path "big5_expert_panel_prereg.md" -Pattern "CANCELED"`
- Dominance 52%-constant + coverage counts (live artifact; re-verify after any dispositions rebuild):
  `python -c "import json,collections; m=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\behavioral_dispositions.json'))['members']; c=collections.Counter(v['dominance_z'] for v in m.values() if 'dominance_z' in v); v,n=c.most_common(1)[0]; print('modal',v,'count',n,'of',len(m))"`
  (2026-07-09: modal −0.381, count 277 of 533 = 52.0%; coverage coop 513 / dil 529 / dom 533 / vis 481 / bre 511 / rea 207.)
- Dependability-audit SB table (§3, † rows): session-recorded 2026-07-09; no repo table exists; repo footprint = `Select-String -Path "big5_a_matrix_prereg.md","fec\coop_v2_candidate.py" -Pattern "dependability"`. If any † number becomes load-bearing, re-derive it via the split-half recipe in `moneyball-proof-and-analysis-toolkit` instead of citing this skill.
- Gate status of open routes (MEM_N 201→250 accrual; round-5 diagnostic; Vote Smart key): `Select-String -Path "big5_n_matrix_prereg.md" -Pattern "MEM_N"` and `Select-String -Path "big5_es_votesmart_prereg.md" -Pattern "STATUS"` — and check whether `big5_methods.md` has grown past §21 (§22 = the Vote Smart RESULT landing). **Vote Smart status describes MAIN only** — an unmerged branch may already hold the consumed RESULT-VS (as of 2026-07-10, `claude/clever-elbakyan-15fa11` @e77703c records TIER 5 UNCORROBORATED, r=+.055 n.s.); before citing, run `git log --all --oneline | Select-String "Vote Smart"` per `moneyball-docs-and-claims` §3.2.
