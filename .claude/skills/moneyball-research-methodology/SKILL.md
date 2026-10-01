---
name: moneyball-research-methodology
description: Load this skill whenever a task involves proposing, testing, or judging a RESEARCH claim in the Moneyball repo - e.g. "test whether X predicts Y", "improve the A trait", "re-run that validation", "can we validate ES now?", writing or amending any big5_*_prereg.md file, running any b5_* script with --look or --simulate, interpreting a battery refusal, or deciding whether a result counts as PASS/MISS/RETIRED. It defines the prereg -> battery -> one-look discipline, the outcome vocabulary, and the full idea lifecycle from hunch to shipped change or documented retirement. It does NOT cover engineering QA (tests/audit checks/gold labels - see moneyball-validation-and-qa), statistics theory from zero (see psychometrics-reference), reusable analysis recipes (see moneyball-proof-and-analysis-toolkit), or the exact wording of claims after a result lands (see moneyball-docs-and-claims).
---

# Moneyball research methodology — how a hunch becomes an accepted result

This project measures the personalities and persuadability of 533 members of Congress from their text, voice, and legislative behavior, and it does so under a hard scientific discipline: **every validity claim must be earned through a pre-registration ("prereg") that locks the hypothesis, the numeric pass bars, and the consequences BEFORE the data is examined — and each prereg gets exactly ONE evaluation against real data (the "look"), consumed forever.** The discipline exists because an LLM analyst under conversational pressure will otherwise tune bars, re-run until something passes, and narrate noise as signal. The master scientific ledger is `big5_methods.md` at repo root (537 lines, 21 numbered sections as of 2026-07-09); the individual experiment contracts are the 20 `big5_*prereg*.md` files at repo root. This skill teaches the mechanics exactly as the repo enforces them — including the machine-enforced look gates in the `fec/b5_*` scripts — so you can run the discipline, not just admire it.

## When NOT to use this skill

- **Engineering QA** (adding tests, audit checks, gold-label sheets, acceptance thresholds for code changes) → `moneyball-validation-and-qa`.
- **Statistics/measurement theory from zero** (what reliability, permutation tests, halo, MTMM actually are) → `psychometrics-reference`.
- **Reusable analysis recipes** (how to build a power study, plant battery, split-half, byte-match purity proof) → `moneyball-proof-and-analysis-toolkit`.
- **What you may write/claim after a result** (exact caveat wording, the validated-claims ledger) → `moneyball-docs-and-claims`.
- **The history of every dead end** (what was tried, refuted, do-not-reflag) → `moneyball-failure-archaeology`.
- **Gating vocabulary as project law** (user-gated / DATA-GATED / etc. master list) → `moneyball-change-control`. This skill uses those terms; that skill owns the rules.

## Quick reference

**The lifecycle** (details in the numbered sections):

```
hunch -> cheap pre-lock probe ($0, criterion-side/synthetic only — NEVER pairs instrument with criterion)
      -> prereg written (hypothesis, numeric bars, roster pinned, SHA-256 fingerprints,
         adverse priors disclosed, consequences for EVERY outcome, stopping rules)
      -> adversarial review of the prereg itself, required changes in
      -> STATUS: LOCKED + committed (pre-look; pre-COLLECTION if data doesn't exist yet)
      -> simulate battery (--simulate / in-process before --look): planted/null/confound checks
           battery FAILS -> RETIRED WITHOUT A LOOK (look NOT consumed; successor condition pinned)
           battery passes -> THE ONE LOOK
      -> RESULT appended verbatim to the prereg (MISSes included), committed SAME SESSION
      -> PASS: adversarially re-derived, then pre-declared consequences fire;
         promotion into engines/artifacts is USER-GATED (the .candidate convention)
         MISS: route CLOSED with evidence -> methods section + kill-ledger, never re-run
```

**Look-gate scripts** (all refuse to look unless every condition holds). No-arg invocation = a status print (lock / look / fingerprint state) for the n_matrix, a_matrix, votesmart, and panel scripts; NOTE `b5_behavioral_instrument.py` loads the corpus and featurizes (Empath cache writes possible) on ANY invocation, including no-arg (fec/members/b5_behavioral_instrument.py:210-212):

| Script | Prereg it enforces | Current state (2026-07-09) |
|---|---|---|
| `fec/members/b5_behavioral_instrument.py` | big5_behavioral_instrument_prereg.md | look TAKEN (3/5) — permanently refuses |
| `fec/members/b5_n_matrix.py` | big5_n_matrix_prereg.md (round 4) | RETIRED WITHOUT A LOOK — battery refuses; fingerprints single-vintage |
| `fec/members/b5_a_matrix.py` | big5_a_matrix_prereg.md (round 5) | RETIRED WITHOUT A LOOK — battery refuses |
| `fec/members/b5_es_votesmart_look.py` | big5_es_votesmart_prereg.md | LOCKED pre-collection; on MAIN it reads as awaiting `fec/votesmart_api_key.txt` (user-gated) — **main-state only**: an active session branch may already hold the collection and the consumed RESULT (as of 2026-07-10, `claude/clever-elbakyan-15fa11` @e77703c records RESULT-VS TIER 5 UNCORROBORATED after a user-directed browser-session collection amendment). Check per `moneyball-docs-and-claims` §3.2 (`git log --all --oneline \| Select-String "Vote Smart"`) before citing; a consumed look is never re-taken |
| `fec/members/b5_panel_score.py` | big5_expert_panel_prereg.md | panel CANCELED by Paul; scorer permanently refuses (prereg unlocked) |

**WARNING before running anything:** in this repo import == execution, and `fec/paths.py:7-8` sets ROOT to `MONEYBALL_ROOT` when set, else to the parent of the imported paths.py, so a script run from a git worktree targets that worktree's EMPTY data plane; with `MONEYBALL_ROOT` pointed at LIVE, writes DO land in LIVE. `fec/tests/run_tests.py` resolves its own root from `__file__` and ignores `MONEYBALL_ROOT` (`fec/tests/run_tests.py:8`; the kernel it imports still reads through `paths.py`, `fec/moneyball_core.py:16`). See `moneyball-change-control` law 7. (Corrected 2026-09-30; verified against `fec/paths.py:7-8`.) Only `fec/tests/run_tests.py` and `fec/audit/audit_full.py` are casually read-only-safe (session-ratified, 2026-07). The scripts above have deliberately read-only no-arg status modes, but check for Paul's live jobs first and prefer grepping the prereg files when you only need state.

**Outcome vocabulary** (§7 below): PASS · MISS · FRAGILE = MISS · VOID-FOR-COVERAGE · VOID-FOR-DEGENERACY · RETIRED WITHOUT A LOOK.

---

## 1. The evidence bar

Three working standards, all visible in the record:

**1a. Hypotheses must predict NUMBERS before any data is run.** Every bar in every prereg is numeric and set before the data it judges exists: e.g. "held-out r ≥ +0.15 AND exact permutation p < .05" (big5_n_matrix_prereg.md, Bars section), "Split-half SB improves on ≥3 of 5 traits AND mean SB ≥ +0.03 over .674" (big5_improvements_prereg.md, P1). "Bars are set here, once, before the data they will be judged on is generated... Misses revert; no post-hoc bar adjustment" (big5_improvements_prereg.md header). Jargon: *held-out r* = a correlation measured on data the model never trained on; *permutation p* = the probability of seeing that correlation if the true pairing were random, computed by actually shuffling labels K=5000 times (see `psychometrics-reference` for theory).

**1b. Adversarial refutation is ASSIGNED, not optional.** Three distinct mechanisms, all mandatory:
- *Pre-lock*: the prereg document itself is adversarially reviewed before locking — round 4's header records "adversarially panel-reviewed pre-lock, 4 lenses, all required changes incorporated" (big5_n_matrix_prereg.md line 3). The reviewer's job is to find the hidden leniency (round 4's review added pred_ES as a rival model and volume-hardened the confound gate BEFORE the lock).
- *Post-pass*: "Any PASS is adversarially re-derived before promotion of any claim" (big5_aes_round2_prereg.md, Discipline). In rounds 4-5 this is concrete: on a PASS, all model predictions are recomputed with fresh cross-validation seeds [101,113,127,139,151] and must re-clear ALL bars; failure = "FRAGILE = MISS for ALL consequences INCLUDING closure" (big5_n_matrix_prereg.md, Pre-declared consequences; enforced in fec/members/b5_n_matrix.py:332). The doctrine dates to the P6 incident: a prereg's own split-half bar was proven a double-shrinkage metric artifact by same-day audit — +0.127 of the apparent gain was fake (big5_methods.md §9). Lesson: **a prereg bar can itself be the wrong instrument; a pass is a metric artifact until re-derived by an independent route.**
- *Deterministic pipelines*: where there are no CV folds to reseed, re-derivation = independent recomputation of every statistic in a fresh process; "a mismatch is a DEFECT HALT — nothing is recorded until both computations agree" (big5_es_votesmart_prereg.md, Instruments section).

**1c. One mechanism must explain ALL observations, including the negatives** (session-ratified, 2026-07; the repo demonstrates it rather than states it). The working standard: a proposed explanation is accepted only when it accounts for every data point on the table — especially the ones that don't fit the preferred story. Worked examples: round 4's battery-failure diagnosis had to explain why the N-plant's prediction read the E-plant at −.224 when the raw plants overlapped only −.146 (answer: out-of-fold prediction AMPLIFIES shared feature-space variance — which also explained why real criteria were immune, since reactivity_z is empirically orthogonal to every disposition; big5_n_matrix_prereg.md Addendum 1). Round 5's retirement had to rule out draw luck before blaming the stratum: the 5-seed diagnostic median +0.132 was compared against the round-4 power study's random-roster median ≈.195 at the same n — only "the stratum itself is signal-poor" explains both numbers (big5_a_matrix_prereg.md Addendum 1). The mis-signed acoustic composite (−0.165 that was real signal read upside-down, big5_methods.md §16) is the cautionary opposite: a hand-signed composite let one wrong mechanism silently explain the data.

---

## 2. The prereg contract — what the file must contain

A prereg is a markdown file at repo root, named `big5_<topic>_prereg.md`. Copy the structure of `big5_n_matrix_prereg.md` (round 4) or `big5_a_matrix_prereg.md` (round 5) — they are the hardened templates. Required contents checklist:

| # | Element | What it is | Live example |
|---|---|---|---|
| 1 | Lock statement | Date + "committed before any look" + who authorized (Paul's directive quoted) + adversarial-review note | big5_n_matrix_prereg.md:3-8 |
| 2 | Compliance section | Proof this test does not violate any recorded closure or stopping rule; names every prior record it could touch and states that it doesn't | big5_n_matrix_prereg.md "Compliance with recorded closures" |
| 3 | Hypothesis + honest prior | What is claimed, and the honest probability it's true (LOW/MODERATE), with ADVERSE PRIORS DISCLOSED — every prior negative result touching this route, quoted, with why this design differs | round 4: halo-look +0.013 null disclosed; Vote Smart: §18's wrong-signed −.042 disclosed, prior LOWERED by the disclosure |
| 4 | Roster/stratum pinned | Exact member counts, verified pre-lock (e.g. "MEM = 456 (exact)... MEM_N = 201 (exact)") — a *stratum* is the subset of the roster the criterion covers | big5_n_matrix_prereg.md Roster section |
| 5 | Input fingerprints | SHA-256 hash of every input artifact + row counts of live databases, recorded at lock; the look ABORTS (without consuming) on any mismatch — this makes the prereg "single-vintage by design" | big5_n_matrix_prereg.md Input pinning; big5_a_matrix_prereg.md pins 4 SHAs + 2 row counts |
| 6 | Instrument/machinery spec | IMPORTED from prior validated code wherever possible ("machinery imported... no re-implementation drift"); every NEW numeric enumerated ("New code, complete list (nothing else)") | big5_n_matrix_prereg.md Instrument section |
| 7 | Numeric bars, all-must-hold | Each with its exact threshold, seed, and roster; power honesty stated (what r the p-bar binds at, attenuation ceilings) | round 4's five bars, incl. bar-5 gating confound partial ≥ +0.10 |
| 8 | Simulate battery spec | The four planted/null/confound checks with pinned RNG seeds (§5 below) | big5_n_matrix_prereg.md Machinery validation |
| 9 | Pre-declared consequences for EVERY outcome | What happens on PASS (incl. the re-derivation requirement), on MISS (what closes, what the closure COVERS), on demotion events — with FIXED WORDING where language could be gamed | Vote Smart's five nested tiers each carry verbatim quoted wording, "stated now so its wording cannot be composed post-look" |
| 10 | No-status-change clause | Reproduced prior-round numbers "cannot change any core trait's status in EITHER direction — no promotion... from drift"; the only prior-touching outcome is a significance-guarded demotion that ANNOTATES, never reverses | big5_n_matrix_prereg.md Compliance + Demotion event |
| 11 | Secondaries firewall | Extra quantities may be REPORTED in the same look but can ground NO claim, artifact, or desk change | big5_n_matrix_prereg.md Secondary reads + firewall clause |
| 12 | Stopping rules | Pre-declared "do not re-specify past this" limits | big5_halo_neuroticism_prereg.md:31-33 ("MISS -> STOP... Do not re-specify past this") — honored verbatim in its RESULT |
| 13 | Look gate | The literal refusal conditions the companion script enforces (§4) | big5_n_matrix_prereg.md "Look gate (complete refusal conditions)" |
| 14 | Discipline block | One look; no LLM calls in look rounds ("lexicon + arithmetic only" — the Fable/Haiku cost rule); no bar/seed/roster/wording changes after the commit | big5_a_matrix_prereg.md Discipline |

Standing permanent prohibition carried by every round: **never calibrate the Blue (lexical/behavioral) instrument against the Pink (LLM item) instrument or vice versa** — "Instrument independence is what gives the desk's agreement zones evidentiary meaning" (big5_improvements_prereg.md:81-82).

---

## 3. LOCK mechanics

**The lock marker is the literal line `STATUS: LOCKED`** near the top of the prereg. The look scripts check for that exact substring (fec/members/b5_n_matrix.py:356, b5_a_matrix.py:232, b5_es_votesmart_look.py:153); a prereg without it is unlocked and nothing can run. This is also how the canceled expert panel stays safely dormant: its scorer "hard-refuses the look while prereg not LOCKED" — do not add the line to big5_expert_panel_prereg.md; the panel is CANCELED, A− is the final grade, never re-propose human raters (session-ratified, 2026-07).

**Lock = commit.** The prereg is committed BEFORE the look, and the lock commit should CONTAIN the executable spec: round 5's header states "fec/members/b5_a_matrix.py (the look script) and fec/members/coop_v2_candidate.py (the composition freeze) ride this same commit — the constructor is pinned by same-commit code." Lock and look run the same session where inputs can drift ("weekly collectors can drift the corpus counts", big5_a_matrix_prereg.md Input pinning).

**Pre-COLLECTION lock is the strongest ordering.** The Vote Smart prereg was "committed BEFORE the data exists in-repo... locking pre-collection is the strongest possible ordering" (big5_es_votesmart_prereg.md:3-5) — bars, outcome tiers, error taxonomy, and even the void conditions were fixed before a single API row existed. Use this ordering whenever the criterion data hasn't been collected yet.

**The look-consumed marker is a NEWLINE-ANCHORED H2 heading**: the scripts check for `'\n## RESULT-N'` / `'\n## RESULT-A'` / `'\n## RESULT-VS'` in the prereg text (fec/members/b5_n_matrix.py:357, b5_a_matrix.py:233, b5_es_votesmart_look.py:154). WHY newline-anchored: the original gates were plain substring checks, and quoting the heading in prose (e.g. the prereg's own "Looks gated on this file lacking the matching '## RESULT-A' heading" sentence) FALSE-TRIPPED them. Fixed at commit **72690c9** — "Round-2 look-gates newline-anchored (prose quotes of the RESULT headings false-tripped the substring gate; bars untouched, no look consumed)". When you write a new look script, anchor the gate: match `\n## RESULT-<TAG>`, never a bare substring.

---

## 4. The LOOK — one per prereg, consumed forever

A **look** = the single permitted computation of the real instrument x criterion pairing against the locked bars. Simulate-battery runs and pre-lock criterion-side probes are explicitly NOT looks (they never pair the instrument with the real criterion). The look's output is recorded verbatim under the `## RESULT-*` heading — MISSes included, numbers unrounded — and committed the same session.

**The look is taken by a script, never by hand**, and the script refuses unless ALL conditions hold (verified in fec/members/b5_n_matrix.py:364-367, b5_a_matrix.py:239-242, b5_es_votesmart_look.py:165-169):

| Refusal condition | Message | Consumes the look? |
|---|---|---|
| Prereg file absent | `!! prereg ABSENT` | no |
| `STATUS: LOCKED` line absent | `!! LOOK REFUSED: prereg not LOCKED` | no |
| Newline-anchored `## RESULT-*` heading already present | `!! LOOK REFUSED: RESULT-* already recorded (one look only)` | already consumed |
| Any input SHA-256 / row count mismatches the pinned values | `!! LOOK REFUSED (not consumed): input fingerprint drift` | **no — fix inputs or write a NEW prereg** |
| (Vote Smart only) collection artifact absent, or COLLECTION RECORD addendum absent/mismatched | `!! LOOK REFUSED: collection artifact absent` | no |
| Simulate battery fails in-process | `LOOK REFUSED (not consumed): simulate battery failure` | **no — see §5** |

No-arg invocation of each script prints status only (lock state / look state / fingerprint MATCH-or-DRIFT) and exits. `--simulate` runs the battery standalone; `--look` runs battery-then-look.

**One look means one.** No re-runs after unblinding, no bar movement, no seed shopping, no "just checking one variant" — a MISS's closure clause pre-declares what the closure COVERS precisely so variants cannot be resurrected as re-specs (round 4's closure covers the noiv and unshrunken-criterion variants; round 5's covers "ANY composite over {c1, c2, c3} — any subset, any weights, any re-anchoring"). Iterating ACROSS rounds with a genuinely new prereg (new criterion, new feature basis, new data) is legitimate; iterating WITHIN a look is not.

**Import==execution hazard**: `fec/members/b5_behavioral_instrument.py` "previously took THE LOOK at import time" before a `__main__` gate was added (its docstring, lines 14-17). Any new look script MUST put the look behind `if __name__ == '__main__':` plus the gate checks.

---

## 5. The simulate battery — machinery validation that can refuse the look

Before any real pairing, `--look` runs a four-part synthetic battery IN-PROCESS and aborts if any check fails ("no sentinel files — the gate is the battery itself"). The battery proves the machinery can (a) find signal that exists, (b) find nothing when nothing exists, (c) refuse pure confound, (d) admit true signal that coexists with confound. Pinned form (big5_n_matrix_prereg.md, Machinery validation; adapted per round):

| Check | RNG seed | Construction | Must |
|---|---|---|---|
| (a) PLANTED | 424242 | synthetic criteria with a true ~r=.40 signal from the real feature matrix | be recovered (core plants ≥4/5; the masked new-trait plant clears bars 1-4) |
| (b) NULL | 535353 | real criteria permuted before pairing (pairing destroyed) | yield 0 passes at the TRUE subset size |
| (c) CONFOUND-ONLY | 646464 | criterion driven by gender/party/volume alone | be REFUSED by the gating confound partial (bar-5 < +0.10) |
| (d) TRUE+CONFOUND | 757575 | planted signal PLUS additive confound loadings on both sides | be ADMITTED (bar-5 ≥ +0.10) |

Real trait x criterion pairings are never computed in simulate. Battery output is recorded VERBATIM in a prereg addendum whether it passes or fails.

**A battery refusal is fundamentally different from a MISS.** A MISS is a measurement: the look ran, the real data answered, the route closes with evidence. A battery refusal means the machinery-or-sample could not have delivered a trustworthy measurement — so the look is NOT taken, NOT consumed, and the route is NEITHER validated NOR closed. Calling a retired round "failed" is a mis-claim.

**Worked example 1 — round 4 (big5_n_matrix_prereg.md, retired @48fd00d), and the plant-orthogonalization lesson.** Battery run #1 failed check (a): the N-plant's prediction read the E-plant at −.224, beating its own recovery (+.187). Diagnosis: random plant directions over the low-effective-rank Empath feature matrix share signal-space variance, and **out-of-fold (OOF) prediction AMPLIFIES the shared X-span component** — the plants accidentally tested a harder, different property than the machinery must prove, because the REAL criteria don't share that property (reactivity_z is empirically orthogonal to every disposition). Fix (Addendum 1, scoped to sim(a) only, bars byte-identical): plant signals made **orthogonal by construction via sequential Gram-Schmidt in signal space**, same seed, same target r. **Lesson: when you plant multiple synthetic signals into one feature matrix, orthogonalize them — otherwise you test cross-plant leakage, not recovery.** Battery run #2 (honest plants) then failed on the real constraint: a true r=.40 signal recovers only +0.129 held-out at n=201. The follow-up power study (synthetic, seeds 9001-9005): true .40 passes bar-1 only 3/5 at n=201 with extreme draw variance (+0.015...+0.372), but 5/5 from n=250; true .50 passes 5/5 even at 201. So the bars are sound, the SAMPLE is the constraint — a look would have been "machinery-noise roulette". Disposition: **RETIRED WITHOUT A LOOK, DATA-GATED**: successor prereg permitted only at reactivity coverage MEM_N ≥ 250 (201 as of 2026-07-09; grows with interview collection).

**Worked example 2 — round 5 (big5_a_matrix_prereg.md, retired @d223188): distinguishing stratum from draw luck.** Battery refused (planted-A recovered only +0.105 at n=290). Because round 4's power study said n≈290 random rosters recover ~.195 median, a diagnostic was required before blaming luck: the battery's exact constructor re-run with 5 seeds (424242/515151/616161/717171/818181) on the ACTUAL MEM_A=290 stratum gave own r = +0.105...+0.251, **median +0.132 < the +0.15 bar, 2/5 pass** — so the covered stratum (finance-active members with ≥10 known-party cosponsorships) genuinely carries less recoverable text signal, NOT a bad draw. A multi-rep battery re-spec was considered and REJECTED because it would also have refused — "no battery amendment can license this look today." Disposition: **RETIRED WITHOUT A LOOK, DIAGNOSTIC-GATED**: successor prereg permitted only when the SAME pinned diagnostic passes ≥3/5 on bars 1-4 on the then-current stratum; it is synthetic-only, so **checking the gate never risks a look**.

Program-level lesson, twice replicated (big5_methods.md §21): masked-stratum looks at n≈200-300 cannot see signals below the E-class (~r .3-.5) with the +0.15/perm-p bar — the battery/diagnostic discipline is what stops those looks from burning as false MISSes.

---

## 6. Addendum rules — what may touch a locked prereg

After `STATUS: LOCKED`, the prereg body is immutable. The ONLY permitted appends:

| Permitted addendum | Example |
|---|---|
| Battery/diagnostic runs recorded VERBATIM (pass or fail), plus a sim-machinery correction that leaves "bars, roster, criteria, input fingerprints, and every consequence clause byte-identical to the lock" | round 4 Addendum 1 (plant orthogonalization) — explicitly scoped "amends machinery validation only" |
| Retirement disposition + pinned successor condition | round 4 Addendum 2; round 5 Addendum 1 |
| The `## RESULT-*` section itself, verbatim, committed same session as the look | big5_aes_round2_prereg.md RESULT-A/E1/E2 |
| A COLLECTION RECORD for pre-collection locks — "the ONLY permitted post-lock edit before the RESULT", containing exactly: artifact SHA-256, joined N, base rate, fetch-failure count, exact API field mapping. "Nothing else in this document may be touched." | big5_es_votesmart_prereg.md COLLECTION RECORD section |
| A dated ANNOTATION when a later locked look adds a caveat — "the original result text is left unmodified" (history is never rewritten) | §16's gender-confound annotation on the +0.208 crossmodal RESULT |

**NEVER permitted post-lock**: bar changes, seed changes, roster/criterion re-scoping, wording changes to consequence clauses, deleting or editing a RESULT. If the design is wrong, retire the prereg and write a new one — that costs nothing, because the look wasn't consumed.

---

## 7. Outcome vocabulary

| Outcome | Meaning | Look consumed? | Route state |
|---|---|---|---|
| **PASS** | All bars cleared AND the adversarial re-derivation re-cleared all bars | yes | pre-declared consequences fire; promotion beyond display is separately user-gated |
| **FRAGILE = MISS** | Bars cleared but the fresh-seed re-derivation did not; "MISS for ALL consequences INCLUDING closure" — both runs reported verbatim | yes | route CLOSED |
| **MISS** | A bar failed on the real data — a documented negative | yes | route CLOSED with evidence, recorded in methods + kill-ledger "so no future session re-runs them"; closure covers the pre-declared variant set |
| **VOID-FOR-COVERAGE** | Joined analysis N below the pre-declared floor (Vote Smart: N < 450) | **no** | collection may be completed/retried and the check re-run |
| **VOID-FOR-DEGENERACY** | Criterion degenerate (Vote Smart: base rate <5% or >95%), computed from the collection artifact ALONE before any instrument file is opened — "the ordering makes the no-consumption claim true" | **no** | route pauses; criterion unusable as designed |
| **RETIRED WITHOUT A LOOK** | Simulate battery refused; no RESULT exists, no MISS recorded | **no** | neither validated nor closed — **GATED** on the successor condition pinned verbatim in the retirement addendum (DATA-GATED = wait for sample growth; DIAGNOSTIC-GATED = wait for a pinned synthetic check to pass) |

Successor conditions are pinned VERBATIM at retirement time, with numbers: round 4 = "a NEW prereg... may be locked only when reactivity coverage within the §17-eligible roster reaches MEM_N ≥ 250"; round 5 = "when the SAME diagnostic (this constructor, these five seeds, run on the then-current MEM_A stratum) passes ≥3/5 on bars 1-4". A successor prereg gets FRESH fingerprints and its own one look; the retired document stays as-is forever.

---

## 8. The idea lifecycle end-to-end

**Step 1 — hunch.** Often Paul's directive ("Fix A and ES", "De-entangle A criterion", "switch over to Neuroticism") or a defect traced in a prior RESULT (round 5 began because §17's A verdict was traced to a CRITERION defect: cooperation_z was 2/3 raw cosponsorship volume).

**Step 2 — cheap pre-lock probe ($0, never risks a look).** Allowed BEFORE locking: criterion-side diagnostics (criterion vs criterion, criterion vs covariate), external-instrument checks on OTHER people's data, mechanism checks on repo plumbing, synthetic simulations. Examples (big5_aes_round2_prereg.md, Motivating evidence): the RKH floor-speech Assent null (+.013) that restricted the design to dialogue; the NPAT pre-check on RKH's own traits that fixed the sign; the discovery that the repo's existing 'agree' feature was "DEAD BY MECHANISM" (its regex could never fire past the ingest floor). FORBIDDEN pre-lock: pairing your instrument with your criterion in any form — that IS the look. A hunch that dies at probe stage costs nothing and goes to the kill-ledger with its cause of death (methods §19's probe ledger: retweet share "0 stored", iv_burst "SB .04 situational noise", Bluesky burstiness "party +.28 confound on a 134-member self-selected sample").

**Step 3 — prereg** (§2), **adversarial review**, **LOCK** (§3).

**Step 4 — battery** (§5). Refusal → retire, pin the successor gate, stop.

**Step 5 — THE LOOK** (§4). RESULT appended verbatim + committed same session, whatever it says.

**Step 6a — on PASS: promotion is USER-GATED.** A research pass never auto-ships into engines. The repo's convention is the **`.candidate` suffix**: build the artifact/generator, mark it consumed-by-nothing, and wait for Paul. Live examples: `fec/members/coop_v2_candidate.py` → `coop_v2_candidate.json` — "Writes coop_v2_candidate.json (consumed by NOTHING until user-ratified promotion)" (fec/members/coop_v2_candidate.py:22); `fec/liwc/behavior_calibrated.json.candidate` — "promotion = separate ratified step" (big5_methods.md §3c). Note the round-5 subtlety: cooperation_v2's ENGINE promotion "never depended on this look (criterion hygiene ≠ text validity)" — a criterion can be a better measurement on its own record while the text-instrument question stays open. Even display-layer consequences are pre-declared in the prereg, and "NO engine change flows from this look" can itself be a locked clause (round 5's PASS consequence). Epilogue: Paul granted the coop_v2 promotion 2026-07-10 and it shipped as `RECEPT_COOP=v2` (@94f09cf, merged to main 2026-07-10) — a clean worked example of the full lifecycle: candidate built → stands on its record → user ratifies → ships behind a revert dial.

**Step 6b — on MISS: retirement is documented, twice.** (1) A numbered section in `big5_methods.md` (the living ledger — §6 through §21 on main; §22 = the Vote Smart RESULT, §23 = round 6 — both merged to main 2026-07-10); (2) the kill-ledger convention — the closure recorded with cause of death so no future session re-runs it. Refuted/closed items are BINDING: do not re-flag or re-attempt anything a RESULT, stopping rule, or methods section marks closed (see `moneyball-failure-archaeology` for the full list; `moneyball-change-control` for the law).

---

## 9. Where good ideas came from (the three productive patterns)

1. **Replace the proxy with the behavior it was proxying.** The 2026-07-04 nomological battery indicted the lexical Big-5 as engine input (C reversed on participation, E = broadcast talkativeness), so dispositions were rebuilt MEASURED FROM BEHAVIOR — roll-call participation, cosponsorship, portfolio breadth (big5_methods.md §3b). Text instruments then became the thing being VALIDATED against behavior instead of the thing feeding engines.
2. **De-entangle a criterion by rebuilding it from SHARES instead of counts.** cooperation_z was 2/3 volume (breadth entanglement +.708); cooperation_v2 rebuilt it from ratio measures only (bipartisan tie share + directional cross-party cosponsorship share) → entanglement +.708→−0.140, split-half SB .873, gender loading −.021 (big5_methods.md §21, fec/members/coop_v2_candidate.py). Volume is this repo's recurring confound — visibility, cooperation, and lexical-N all fell to it; when a criterion correlates with everything, check whether it's secretly "how much" rather than "what kind".
3. **Re-anchor a trait to a behavioral slot when its text read won't validate.** Neuroticism's text/audio reads kept failing, but the engine only needed the ROLE (pressure-reactivity in the susceptibility composite) — so round 3 shipped `reactivity_z` (live-interview cutoff proneness, split-half SB .43, orthogonal to all dispositions, party/gender clean), "a measured behavior serving a construct role — valid by construction for its ROLE, no criterion look to fail" (big5_methods.md §19). Bonus: the swap REDUCED demographic tilt (susceptibility gender loading +.327→+.198) because lexical-N had carried a gender-language artifact.

Common thread: the wins came from CRITERION-side and CONSTRUCT-side work (which is cheap, $0, look-free), not from ever-fancier instruments chasing a fixed criterion. Eleven instrument-side designs in campaign 1 produced two promotions and nine documented misses (big5_methods.md §11).

---

## 10. Corroboration vs validation looks

A **validation look** asks "does this instrument measure its construct?" and demands the full bar (r ≥ +0.15, specificity, confound partial). A **corroboration look** asks the much weaker "does an external record point the same direction?" — and must be LABELED as such up front, with the power arithmetic shown. The Vote Smart ES prereg is the template (big5_es_votesmart_prereg.md, "What this look is — and is not"): the field's own effect size for ES→survey-response is +.063; at N≈518 that is detectable at only **~40% power** (one-sided .05 threshold ≈ .072) and can NEVER clear the +0.15 validity bar. So the prereg pre-declares: "This is a CORROBORATION look, not a validation look. A corroboration MISS at ~40% power is recorded as **'uncorroborated,' never 'disproven'** — wording fixed here." Its five nested outcome tiers (VALIDITY expected-UNMET → WEAKLY CORROBORATED → signal-not-specific → confound-attributable → UNCORROBORATED) each carry fixed wording, and even the best realistic outcome buys only "annotation only; no promotion, no un-caveating."

Rule of thumb: before locking, compute the detection threshold at your N against the best published effect size for the phenomenon. If the honest power against the true effect is under ~80%, either (a) label the look corroboration with tiered wording, or (b) don't lock — pin a data gate instead (that IS what DATA-GATED means). See `moneyball-proof-and-analysis-toolkit` for the power-study recipe.

---

## 11. Claim hygiene after a result lands

The exact permitted wording of every validated claim, with its mandatory caveats, is owned by `moneyball-docs-and-claims` — check it BEFORE writing any summary of psych-program state. The three claims most often mis-recalled (verified against big5_methods.md §16-§18, embed-them-correctly-or-not-at-all):
- The instrument look was **3/5** (O/C/E diagonal-dominant). Never "5/5"; "all five traits validated" is formally SUPERSEDED.
- **"A passed via audio" is FALSE** — audio-A was null twice; audio's real signal was E and ES vs the Pink instrument; A's real pass is text-side (+.183, criterion-valid, NOT discriminant).
- **ES always carries the gender-confound caveat.** The +0.208 voice-ES pass "stands as history only"; the pre-registered robustness look found partial r | gender,party = −0.029. Never "cross-modally validated" unqualified.

And the general rules that live here because they are METHOD, not wording: a RESULT is never edited, only annotated by a later LOCKED look with pre-declared consequences ("Never reverse a settled result under conversational pressure" — session-ratified, 2026-07); a MISS is reported as the closure it is, not softened; a RETIRED round is reported as gated, not failed; secondaries ground nothing.

---

## Provenance and maintenance (2026-07-09)

All facts verified against the working tree at branch `claude/nifty-cray-f6d053` (main merged @88a7048). Run these from the repo root: `cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"` (or the current worktree). All commands are read-only.

- **20 prereg files at repo root** — `Get-ChildItem big5_*prereg*.md | Measure-Object`
- **big5_methods.md is the ledger, §21 latest, §22 reserved (537 lines)** — `Select-String -Path big5_methods.md -Pattern "^## 2[12]"`
- **Lock marker literal in the gate code** — `Select-String -Path fec\members\b5_n_matrix.py,fec\members\b5_a_matrix.py,fec\members\b5_es_votesmart_look.py -Pattern "STATUS: LOCKED"`
- **Newline-anchored RESULT gates** — `Select-String -Path fec\members\b5_n_matrix.py,fec\members\b5_a_matrix.py,fec\members\b5_es_votesmart_look.py,fec\members\b5_behavioral_instrument.py -Pattern "RESULT-N","RESULT-A","RESULT-VS","## RESULT"`
- **Commit 72690c9 (gate-anchoring lesson)** — `git log --oneline -1 72690c9`
- **Round 4 retired, DATA-GATED at MEM_N ≥ 250** — `Select-String -Path big5_n_matrix_prereg.md -Pattern "RETIRED WITHOUT A LOOK","250"`
- **Round 5 retired, DIAGNOSTIC-GATED ≥3/5** — `Select-String -Path big5_a_matrix_prereg.md -Pattern "DIAGNOSTIC-GATED"`
- **Vote Smart lock state / look status** — `Select-String -Path big5_es_votesmart_prereg.md -Pattern "STATUS: LOCKED","RESULT-VS"` (or `python fec\members\b5_es_votesmart_look.py` no-arg status — check for Paul's live jobs first). The collection + consumed RESULT-VS were merged to main 2026-07-10 — the prereg on main carries the RESULT
- **Battery seeds 424242/535353/646464/757575 + re-derivation seeds [101,113,127,139,151]** — `Select-String -Path fec\members\b5_n_matrix.py -Pattern "424242","101, 113"`
- **.candidate convention** — `Select-String -Path fec\members\coop_v2_candidate.py -Pattern "consumed by NOTHING"` and `git ls-files *.candidate`
- **Blue-on-pink prohibition** — `Select-String -Path big5_improvements_prereg.md -Pattern "PROHIBITED permanently"`
- **Stopping-rule template honored** — `Select-String -Path big5_halo_neuroticism_prereg.md -Pattern "Do not re-specify","STOPPING RULE"`
- **coop_v2 engine promotion — granted+shipped 2026-07-10, merged to main (@94f09cf)** — `git log --oneline | Select-String "ENGINE PROMOTION"`; round 6 is also on main (fresh lock @25c0a19 → RESULT-A2 MISS all 5 bars @b7573c9, st_mean route closed, anti-basis-shopping clause binds future bases)
- **Coverage counts (MEM_N=201/456, MEM_A=290) — these are PINNED LOCK VALUES; live coverage drifts as collection accrues** — `Select-String -Path big5_n_matrix_prereg.md,big5_a_matrix_prereg.md -Pattern "MEM_N = ","MEM_A = "` (checking the successor gates themselves is synthetic-only and never risks a look)

If any prereg gains a new `## RESULT-*` section or a new prereg file appears, update the Quick-reference table and §7/§8 examples accordingly — the mechanics themselves (lock marker, newline-anchored gates, battery structure, one-look rule) change only by a commit touching the b5_* gate code; grep before trusting.
