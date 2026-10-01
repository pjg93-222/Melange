---
name: moneyball-docs-and-claims
description: Load when updating, citing, or writing any Moneyball project document or claim - README.md, MATHEMATICAL_SPECIFICATION.md, INDEX.md, big5_methods.md, audit reports, prereg files - or when answering "is X validated?", "what can we claim about trait Y?", "which doc do I update after this change?", "how do I word this commit message?", or preparing any external write-up or citation. Owns the doc plane (living vs frozen vintages), house style, the commit-message vocabulary, the validated-claims ledger with mandatory caveats, the forbidden-claims receipts block, citation-honesty standards, and the reproducibility standard for published artifacts. Does NOT cover prereg/look mechanics (moneyball-research-methodology), evidence thresholds and test-adding (moneyball-validation-and-qa), the change-control rules themselves (moneyball-change-control), or past-investigation history (moneyball-failure-archaeology).
---

# Moneyball docs and claims

This skill governs what may be WRITTEN and what may be CLAIMED in this project. The Moneyball repo treats documents as a two-tier system: a small set of short living docs that must stay current, and dated frozen snapshots that are history, not law — the project retired its long-form spec precisely because it drifted behind the code. Every scientific claim (especially about the Big Five personality measurements) has an exact validation status with mandatory caveats, recorded in `big5_methods.md`; misquoting that status is the project's most common documentation failure, so this skill carries a verified claims ledger and a list of forbidden phrasings. It also defines the commit-message vocabulary, because commit messages here are the lab notebook: bars, results, and user ratifications often exist nowhere else.

**Jargon quick-defs** (full theory lives in sibling skills): a *prereg* is a markdown file locking an experiment's method and numeric pass/fail bars BEFORE data is examined; a *look* is the single permitted evaluation of real data against those bars; *Big Five / O,C,E,A,ES* are the five personality traits (Openness, Conscientiousness, Extraversion, Agreeableness, Emotional Stability) measured per member of Congress; *SB* is Spearman-Brown split-half reliability (a 0-1 consistency score); *r* is a correlation coefficient; *diagonal-dominant* means a trait's text score predicts its OWN behavioral criterion better than any other trait's.

## When NOT to use this skill

- How to design, lock, or consume a prereg/look; battery/fingerprint discipline → **moneyball-research-methodology**
- What counts as evidence, gold-label machinery, acceptance thresholds, adding tests/audit checks → **moneyball-validation-and-qa**
- The change classes, gating vocabulary definitions, and the non-negotiables master list → **moneyball-change-control**
- The chronicle of past investigations, refuted findings, kill-ledgers → **moneyball-failure-archaeology**
- Dial values and env-var catalog → **moneyball-config-and-flags**
- Measurement theory from zero (reliability, validity, halo) → **psychometrics-reference**

## Quick reference

| Question | Answer |
|---|---|
| Which docs are LAW? | The code itself; `MATHEMATICAL_SPECIFICATION.md` points at it. `README.md`, `INDEX.md` are living maps. `big5_methods.md` is the living psych ledger. |
| Which docs are HISTORY? | The four 2026-07-02 baseline docs (single commit @62a209e each) + all `AUDIT_FINDINGS_*.md`. Never quote them for a current value. |
| Instrument validation status? | **3/5** — O/C/E criterion-valid and diagonal-dominant. NEVER "5/5". |
| ES status? | Measured, NO clean independent validation. The +0.208 voice pass is GENDER-CONFOUNDED — the caveat is mandatory everywhere. |
| Grade? | **A− FINAL** (expert panel canceled by Paul — never re-propose raters). |
| Do trait scores feed the engines? | No. Display-only firewall. (The engine's receptivity inputs are *behavioral* dispositions, a separate thing.) |
| Commit words? | `prereg LOCKED (pre-look)` · `LOOK RESULTS: …` / `RESULT: MISS` · `RETIRED WITHOUT A LOOK` · `SHIPPED` · `user-ratified` |
| Rewrite an old RESULT? | Never. Append a dated `ADDENDUM` / `[ANNOTATION]`; original text stays verbatim. |

---

## 1. The doc plane: living docs, frozen snapshots, and the retired spec

### 1.1 Living docs (update duties)

| Doc | Role | Last touched (as of 2026-07-09) | Update when |
|---|---|---|---|
| `MATHEMATICAL_SPECIFICATION.md` | "LAW OF THE SYSTEM" — a short pointer doc: authoritative-code table (which script owns which math), cross-module conventions, standing dials. Declares "The code is authoritative; this document tells you where to look and what must always hold" (lines 5-6). | @d0f1643, 2026-07-03 | A subsystem's owning script changes; a new standing env dial ships; a cross-module convention (determinism, '—' ontology, workbook contract) changes. Keep it SHORT — see §1.3. |
| `README.md` | Module map + run instructions + the five-layer model description. | @3f91332, 2026-07-09 | A new script family or model layer lands (precedent: media/psych layer section added @51f2f92; audio/narrative §7 added @3f91332); run commands or check counts change. |
| `INDEX.md` | Thin layout + verification-protocol index. | @b3ff99c, 2026-07-02 | Layout changes; doc-rot passes. |
| `big5_methods.md` | The living scientific ledger of the Big Five program — 21 numbered sections as of 2026-07-09, self-described "living document". | @d223188, 2026-07-09 | Every psych round appends a new numbered section (see §2.1). §22 is explicitly reserved for the Vote Smart ES RESULT (end of §21). |

**Known doc-rot as of 2026-07-09** (fixing these is a legitimate hygiene commit — precedent @b3ff99c "doc-rot pass"):
- README:11,56 and INDEX:7 say **30** kernel checks and README:57 says **59** audit checks / INDEX:21 says **52**; live counts are **37 kernel / 69 audit** (per commit 48fd00d; trust the run output, never a doc's stated count).
- Spec line 78 and README:67 still instruct `run_pipeline.py --recalc` — the flag is accepted but RETIRED (prints a notice).
- Spec line 12 hardcodes rank weights `0.25·Leg + 0.30·Press + 0.40·Infl + 0.05·Demo` — these are actually LIVE user dials read from workbook cells (`fec/engine/compute_pillars.py:81`), and the user changed them (30/25/40/5 per the 2026-07-07 GATE-2 ratification, recorded in commit 55cc808; the LIVE value is now 45/10/40/5 -- `ranks_python.json` `ab_weights` and `fec/engine/pillar_policy.py:11-15` -- a change that landed out-of-lane on 2026-09-03 and has not been re-ratified since, open ruling S-5). The *shape* in the spec is right; never present its literals as authoritative, and never "fix" the numbers in code — pillar weights are Paul's, set in Excel (session-ratified, 2026-07).
- Spec line 20 still describes the lexical receptivity basis; the live default is behavioral (`RECEPT_TRAITS=behavioral`, `RECEPT_N=behavioral`), and neither dial appears in the spec's dial list.

### 1.2 Frozen snapshots (history, not law)

Four root docs were committed once at the git baseline (@62a209e, 2026-07-02) and never touched since: `ARCHITECTURE_REVIEW_2026-07-02.md`, `PERSONALITY_RECEPTIVITY_LAYER_2026-07-02.md`, `AUDIT_ROADMAP.md`, `stance_templates_review.md`. They are valuable design history. They are also multiply stale — verified examples:
- `AUDIT_ROADMAP.md` says DTHRESH=15 (live: 11.25), PERS '—'→0.50 (live: 0.45), 17 stance categories (live: 18).
- `PERSONALITY_RECEPTIVITY_LAYER_2026-07-02.md` describes a lexical Big-5 receptivity basis that was superseded by the behavioral basis in code.

Rule: **never quote a frozen doc for a current value.** Quote it only as "the 2026-07-02 design intent was X". The same applies to every `AUDIT_FINDINGS_*.md` — they are dated, append-only records (the `_RUN2` suffix exists because the earlier same-day report was "referenced as a canonical doc — not clobbered").

### 1.3 The retired long-form spec (the load-bearing lesson)

`MATHEMATICAL_SPECIFICATION.md` lines 2-3: *"The previous long-form spec drifted behind the code repeatedly and was retired (recoverable via git history: commit 62a209e)."* The architecture review had concluded a wrong spec is worse than none. The chosen fix was NOT a better long spec — it was a **short pointer doc that names where each piece of math lives and what invariants must hold, with the code as the single source of truth**.

Maintenance rule derived from this: when documenting a subsystem, add a ROW to the spec's authoritative-code table (script name + one-line formula + "verified by" column), not paragraphs of restated math. If you find yourself transcribing formulas out of code into markdown, stop — that is how the last spec died.

To read the retired spec (read-only git, safe):

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"   # or any worktree of this repo (read-only git commands only)
git show 62a209e --stat            # see what the baseline contained
```

---

## 2. House style

### 2.1 big5_methods.md sections

Each experimental round appends one numbered section. Verified conventions (from §6-§21):

- **Heading format:** `## N. Title — verdict (date, prereg @hash)`. Real examples: `## 13. Cross-Method Convergence (CMC) — MISS; grade holds A- (2026-07-08, prereg @c305aba)`; `## 20. Psych-audit round 4 — N-anchored per-trait look: RETIRED WITHOUT A LOOK, data-gated (2026-07-09, prereg big5_n_matrix_prereg.md @e4aea1e)`. The verdict is IN the heading — a reader skimming headings gets the honest outcome.
- **Verdict words in caps:** PASS / MISS / RETIRED WITHOUT A LOOK / CONFOUNDED / CLOSED / EXHAUSTED. MISSes get as much space as passes ("documented negative" is a first-class outcome).
- **Numbers verbatim, with n:** every claim carries its correlation, n, and permutation p where applicable.
- **Bold the state-changing sentence** so the section's takeaway is machine-greppable: e.g. §17 "**Honest per-trait state after today: O, C, E criterion-valid AND diagonal-dominant…**".
- **Status vocabulary** for instruments (file top, line 5): PRODUCTION = feeds the receptivity layer; EXPLORATORY = built and measured, not consumed; PARKED = designed, awaiting budget.
- **History is never rewritten.** A later finding gets a dated bracketed annotation inside the old section — §16 carries `**[ANNOTATION 2026-07-09, pre-registered robustness …: the pass is GENDER-CONFOUNDED …]**` while the original PASS text stands. Same in preregs: `big5_es_crossmodal_prereg.md` appends `**ADDENDUM 2026-07-09 (post-look robustness …)**` under the untouched RESULT. If you learn an old section is wrong, annotate; never edit the original words.

### 2.2 Audit report structure

Audit reports are dated root files `AUDIT_FINDINGS_YYYY-MM-DD[_SUFFIX].md`, append-only (new report per run, never clobber). Verified skeleton (from the 2026-07-02-RUN2 and 2026-07-04 reports):

1. Header: what was audited, at what commit/state, protocol phases run.
2. Gate results: kernel tests N/N, audit tail, rank delta 0/533, artifact hashes.
3. `## Findings` with severity taxonomy declared inline — `(S1 corrupts/crashes/unexplained delta · S2 silent wrong-number · S3 hygiene)` — and per-finding subsections `### [S2-01] file.py:line — one-line symptom` containing symptom → root cause → fix → status. (Severity vocab varies by report era: S1/S2/S3, SEV-1/2/3, or HIGH/MED/LOW+CONFIRMED/PLAUSIBLE — say which you're using.)
4. **Refuted / do-not-re-flag list** — binding on all future sessions (project law: refuted-findings lists in audit reports are final; includes the Judiciary coverage decision, CLOSED).
5. Known-benign registry additions (explained non-defects).
6. Where sub-agents were used: an **agent-calibration ledger** of overruled verdicts and why (run-4j precedent: all four verification agents over-claimed at least once; every CRITICAL was re-checked against actual code wording before acceptance).

### 2.3 Prereg file anatomy (structure only — mechanics in moneyball-research-methodology)

A prereg is `big5_<name>_prereg.md` at repo root. Verified structural elements (from `big5_n_matrix_prereg.md` and `big5_es_votesmart_prereg.md`):

- Line ~3: the literal line `STATUS: LOCKED (date, committed before the look …)`. This exact string is **machine-read** by the look-gate scripts — its absence makes the paired script refuse to run.
- Sections, in rough order: compliance with recorded closures (why this look is legitimate) · instrument (fixed a-priori) · roster and criteria · bars (numeric, all-must-hold) · secondary reads + firewall · machinery validation (simulate battery) · pre-declared consequences with fixed wording · look gate (complete refusal conditions) · input pinning (SHA-256 of inputs + roster counts) · discipline.
- The outcome is appended as `## RESULT — THE ONE LOOK (date, N=…)` (or `## RESULT-A` etc. for multi-test preregs) with numbers verbatim, MISSes included, committed same session.
- Pre-look corrections are dated `## ADDENDUM N (date, PRE-LOOK; bars … UNTOUCHED)` sections.
- **Trap:** the gates match `## RESULT*` headings (newline-anchored since @72690c9, after prose that *quoted* a RESULT heading false-tripped the old substring gate). When writing prereg prose, still avoid reproducing a RESULT heading at column 0.

### 2.4 Commit-message vocabulary (with real examples from git log)

Commit messages are the primary lab notebook: bars, measured numbers, user directives (quoted verbatim), and revert instructions often live ONLY in message bodies. Never rebase or squash; there are zero `git revert` commits — the revert mechanism is env dials documented in the introducing commit (e.g. `BAKKER_XCUE=0` @0e131c0).

| Term | Meaning | Real example (subject, verbatim) |
|---|---|---|
| `… prereg LOCKED (pre-look)` | Bars committed before any data seen; the look is now armed | @e4aea1e "Psych-audit round 4 prereg LOCKED (pre-look): fifth trait re-anchored as N vs behavioral reactivity_z …" |
| `LOOK RESULTS:` / `RESULT:` | The one look was consumed; outcome recorded verbatim, pass or miss | @34bf7e4 "LOOK RESULTS: behavior-anchored instrument 3/5 (O/C/E diagonal-dominant) + ES cross-modal robustness CONFOUNDED (gender) — pre-declared consequences applied"; @0871c3e "Audio pilot RESULT: MISS at N=90 (one look) — documented negative, pilot closed" |
| `RETIRED WITHOUT A LOOK` | Prereg withdrawn pre-evaluation (battery refused); NO look consumed, route neither validated nor closed, re-entry gate named | @48fd00d "Round 4 RETIRED WITHOUT A LOOK … route DATA-GATED at MEM_N>=250, no look consumed, no status changes …" |
| `SHIPPED` | A change actually landed in production wiring | @31a37ae "ROUND-3 SHIPPED: reactivity_z (live-interview cutoff proneness) = behavioral N-slot in susceptibility — the engine's last text leg retired" |
| `user-ratified` / `user directive` | Paul made the call; the body quotes him and marks it non-relitigable | @18ce3b3 "Say-do gate landed (user-ratified): …"; @f12481b "Run-4i: PERSONA_W removal recommendation WITHDRAWN, user-ratified KEEP at 0.30 … Memory updated so future sessions do not re-litigate." |
| `Run-4a…` / `Run-5b…` prefix | One work unit inside an audit wave | @51f2f92 "Run-5b: EXTENSIVE audit pass …" (gotcha: history contains two "Run-4x/4y/4z" pairs — greps by run label double-hit) |

When you make a change on Paul's direction, quote his words in the commit body — that quote is the ratification record.

---

## 3. The validated-claims ledger (as of 2026-07-09, main @88a7048)

Verified word-by-word against `big5_methods.md` (§16-§21) and the prereg RESULT sections. This is what may be claimed about the Big Five program, with the caveats that MUST travel with each claim. Statuses: LIVE (claimable with caveat) / CLOSED (do not reopen) / GATED (open, blocked on a named condition).

**Framing that applies to everything below:** the Big-5 trait scores are DISPLAY-ONLY — no engine or rank reads them (the "firewall", §15/§16). The engines' receptivity inputs are the separate *behavioral dispositions* (cooperation, diligence, dominance, visibility, breadth, reactivity).

| Claim | Status | Exact current state + mandatory caveat |
|---|---|---|
| O (Openness) | LIVE | Criterion-valid **+.198** and diagonal-dominant (supervised Empath text instrument, §17 look, N=456, perm-p .0002). v2 behavioral held-out +.20. |
| C (Conscientiousness) | LIVE | Criterion-valid **+.277** and diagonal-dominant (§17). Interview-C retest PASSED **+0.155 / +0.112** (bars locked 2026-07-05, one look) → pre-declared consequence wired: interview chunks aggregate at 2× weight (`C_INT_W` in big5_llm.py); c_basis marks 294 interview-weighted / 215 crec-only members (§7). Shipped **v2 C = +.13** — a +.24 claim was ~2× inflated (§16 fact-check). |
| E (Extraversion) | LIVE | Criterion-valid **+.552**, diagonal-dominant (§17). Mandatory caveat: genre-composition — corpus and criterion share the interview modality. |
| A (Agreeableness) | LIVE (with limit) | Criterion-valid (**+.183**, perm-p .0004) but **NOT discriminant** (misses diagonal-dominance on dominance only, §17). Dialogic-assent route CLOSED with evidence (§18). The de-entangled-criterion look (round 5) was RETIRED WITHOUT A LOOK — DIAGNOSTIC-GATED (§21). **Update (2026-07-10, merged to main):** the round-5 diagnostic gate was MET by a NEW instrument (st_mean semantic embeddings, synthetic-only @1609c25), a FRESH prereg was locked (round 6 @25c0a19), its battery passed, and the look was CONSUMED: **MISS on all 5 bars (own r +0.033, perm-p .296) @b7573c9 — the st_mean A route is CLOSED** (methods §23); the round-5 Empath data-growth clause stays open; A remains criterion-valid / not-discriminant. The coop_v2 *criterion* stands on its own record (SB .873/.821, entanglement +.708→−.140) and its ENGINE promotion was **granted+shipped 2026-07-10, merged to main** (@94f09cf; `RECEPT_COOP=v2`, `v1` reverts). |
| ES (Emotional Stability) | measured, NOT validated | **No clean independent validation.** Text read +.149 = MISS by 0.001 and anti-reads E (§17). The voice cross-modal **+0.208 (perm p .0002, N=395) stands as history ONLY and is GENDER-CONFOUNDED**: partial r(\|gender,party) = −0.029, within-sex null both sexes (§16 annotation + big5_es_robustness_prereg RESULT). Voice-ES CLOSED PERMANENTLY (§18, pre-declared final attempt). NPAT closed for the current roster (§18). The sole remaining external path — the Vote Smart PCT pull — was taken 2026-07-09 (merged to main 2026-07-10): **TIER 5 UNCORROBORATED** (r=+.055 n.s., ES weakest of the 5 axes, @e77703c; methods §22). Every ES route is now exhausted WITH EVIDENCE — do not propose new ES validation routes; richer PCT content would be a NEW construct needing its own prereg. See §3.2. |
| N-slot / reactivity_z | LIVE (role-valid) | `reactivity_z` (live-interview cutoff proneness, program-split-half **SB .43**) SHIPPED as the engine's behavioral N-slot (`RECEPT_N=behavioral`, §19). It is a measured behavior serving a construct role — **valid by construction for its ROLE, no criterion look taken or claimable**. The Empath-text→reactivity validation route is DATA-GATED at MEM_N ≥ 250 (201 as of 2026-07-09; §20 — RETIRED WITHOUT A LOOK, not a MISS). |
| Instrument overall | LIVE | Behavior-anchored per-trait instrument look = **3/5** (O/C/E diagonal-dominant). This is the FIRST genuinely diagonal-dominant per-trait text evidence in the program; the earlier Pink trait-score matrix was **0/5** (§13) — any "validates 4/5" phrasing must carry that 0/5 caveat (§16 fact-check). |
| Grade | FINAL | **A−** — ratified by the §16 re-grade, held below A by method-shared RKH convergence, the pooled-lexical MTMM failure (firewalled), and the modest ES effect. The expert panel (the only A−→A lever) was built then **CANCELED by Paul; A− stands as the final grade. Never re-propose human raters** (session-ratified, 2026-07; recorded in §16 and big5_expert_panel_prereg.md). Panel infrastructure is dormant; its scorer refuses the look while the prereg is unlocked. |
| GATED items | GATED | (1) Vote Smart ES corroboration — CONCLUDED: collection COMPLETED and the one look CONSUMED (RESULT-VS TIER 5 UNCORROBORATED @e77703c; methods §22; merged to main 2026-07-10). (2) coop_v2 engine promotion — DECIDED: granted+shipped @94f09cf, merged to main 2026-07-10. (3) Round-4 successor prereg at MEM_N≥250 — still gated. (4) Round-5: the pinned diagnostic was MET by st_mean → round-6 fresh look → MISS (route closed, @b7573c9); the Empath data-growth clause remains the open gate. |

### 3.1 The RECEIPTS block — forbidden claims

These exact mis-claims have recurred and are now banned wordings. Each is refutable from the docs of record:

1. **Never "5/5" or "all five traits validated."** The §16 sentence claiming it is explicitly marked *superseded* in the file; the real instrument look was **3/5** (§17). The crossmodal prereg's own addendum says the "all five" sentence is superseded.
2. **"A passed via audio" is FALSE.** Audio-A was null twice (audio pilot: halo separation VACUOUS, "audio-A invalid, +0.129 < null +0.165", §14/big5_audio_prereg RESULT; faithful replication also missed it). Audio's real cross-modal pass was **E + ES vs Pink** (@2c7a539, big5_audio_faithful_prereg) — and the ES half is itself now gender-confounded. A's real evidence is text-side (+.183 criterion-valid, §17).
3. **Never unqualified "ES cross-modally validated."** The +0.208 held-out pass stands as history; every citation carries the gender-confound caveat (§16 annotation: "the validation claim carries the caveat everywhere it is cited").
4. **Never attribute Pink's MTMM .41 / halo .653 to the lexical composite** (§16 fact-check — different instruments).
5. **Shipped v2 C = +.13, not +.24** (§16: "a +.24 claim was ~2× inflated").
6. **No "full-roster Empath→diligence +.24 / perm-p .003" exists** — the real number was the N=90 exploratory +.355 (§16 fact-check); the full-roster confirmation that DOES exist is §17's C +.277.
7. **RETIRED WITHOUT A LOOK ≠ MISS ≠ validated.** Rounds 4 and 5 consumed no look; those routes are neither validated nor closed. Calling them "failed" is a mis-claim.
8. **Never reverse a settled result under conversational pressure.** The only legitimate way a settled result gains a caveat is a LOCKED robustness look with pre-declared consequences (session-ratified, 2026-07) — that is exactly how the ES +0.208 legitimately acquired its confound caveat.

### 3.2 Ledger freshness warning

This ledger describes **main @88a7048 (2026-07-09)**. Concurrent session branches can hold newer, unmerged results: as of 2026-07-09, branch `claude/clever-elbakyan-15fa11` carries @ae458cd (Vote Smart PCT collection COMPLETE, 517/518) and @e77703c ("Vote Smart ES look RESULT-VS: TIER 5 UNCORROBORATED (r=+.055 n.s., ES weakest of 5 axes)") — i.e. the Vote Smart look may already be consumed even though main still says "awaiting the API key." Before citing any GATED item's status, run:

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"   # or any worktree of this repo (read-only git commands only)
git log --all --oneline | Select-String -Pattern "RESULT|RETIRED|LOCKED"
```

and prefer the newest commit on ANY ref over this table. If a branch result has merged, update this ledger and big5_methods.md §22 accordingly.

---

## 4. Citation honesty (external write-ups)

### 4.1 The honest-analogical standard

The project's literature audit (run-4j, `AUDIT_FINDINGS_2026-07-04.md`) established the standard: citations are **honest-analogical** — *"papers are cited for settings, principles, and directions; magnitudes are local calibration"* (and sensitivity-bounded). A citation describes INSPIRATION, never validation-by-proxy: citing a paper does not transfer its evidence to our constants. Verified specifics that were fixed once and must not regress:

- **Byrne, Silasi-Mansat & Worthy (PAID 2015)** supports **N+ (replicated core result) and A+ (Exp-2 social-pressure interaction) ONLY**. Their E effect was null; their lone C signal was weak, unreplicated, and opposite-signed vs our −.20. The C−/E− dampeners in the susceptibility composite are design priors; the A-above-N ordering is the user's directive. Say exactly this when citing Byrne.
- **(1−1/e) greedy-guarantee scope** (corrected 2026-09-30; verified against `fec/engine/optimize.py:3-11,36-38`): **allocator** — in a fixed stance state the objective is separable with diminishing-returns chunks, so greedy is the exact discrete optimum on the `INC` grid; the Golovin-Krause data-dependent bound is kept as a diagnostic. If a MODELED money threshold can flip a stance (`conversion_reachable`), the engine replans after that modeled transition but claims neither an adaptive-submodularity guarantee nor the fixed-state certificate. **COALITION** side: competitive IC vs fixed opponent seeds IS submodular (Bharathi-Kempe-Salek). **FLIP (competitive linear-threshold) has NO general guarantee** — Borodin et al. prove submodularity fails there — and the code claims none. The only empirical marginal checks are the allocator's own per-member diminishing-returns test (`concavity_violations()`, `fec/engine/optimize.py:53`) and `fec/audit/audit_frontier.py:18-26`, which covers the budget_frontier coalition and electoral paths, not flip (corrected 2026-09-30).
- **Chen et al. = UAI 2021** (arXiv 2106.07039, PMLR v161), not ICML. Cited for the contingency *setting* ("a lobbied seed takes with probability"); the code openly implements a simpler gate, not their RL solution.
- **Units caveat** (§12 of big5_methods.md): our .42–.52 convergence is an interpretable r; benchmarks stated as AUC/F1 (DeepPerson ~.70 AUC; B-L macro-F1 .77) are NOT apples-to-apples. The defensible claim beats the r-scale benchmarks only.
- **Refuted external claims are never used**: the §12 grade explicitly excluded three claims its own verification refuted (Park's MTMM discriminant; a text test-retest of .70; Park as the canonical informant-validated benchmark). If a supporting citation fails verification, drop it from the argument — do not soften it.

### 4.2 Preconditions for any external claim

Before a number leaves this repo (paper, memo, slide, README of a public artifact), ALL of:

1. **Prereg'd and look-consumed** — the number comes from a `## RESULT` section of a locked prereg (or is an explicitly-labeled descriptive/exploratory statistic, marked as such).
2. **Caveats attached verbatim** — the mandatory caveats from the §3 ledger travel with the claim (gender-confound for ES; genre-composition for E; 0/5-Pink context for any "n/5"; shared-method for RKH convergence).
3. **Reproducible** — per the §5 standard: exact commit hash, SEED, input fingerprints, pinned roster.
4. **Honest-analogical citations** — per §4.1; every cited paper's actual finding re-checked against your sentence's wording (the run-4j lesson: all four verification agents over-claimed; calibrate against actual wording).
5. **Nothing user-gated presented as done** — stance labels, dedup deletes, engine promotions, and Vote Smart are Paul's; write "gated on user decision", not "planned".

---

## 5. Reproducibility standard for published artifacts

Any artifact whose numbers might be cited must be regenerable exactly. The three legs, all verified in-repo:

1. **Determinism**: `SEED=7`, `MC=20`, splitmix64 common-random-numbers keyed on (iteration, edge-or-member) — same-seed runs are byte-identical; any NEW random draw must claim a dedicated key range (MATHEMATICAL_SPECIFICATION.md, "Determinism contract"). State the seed and MC in the artifact's provenance line.
2. **Input fingerprints**: SHA-256 of every input artifact + exact roster counts, recorded at lock time (the prereg "Input pinning" convention — e.g. big5_n_matrix pinned MEM=456 / MEM_N=201; round 5 pinned MEM_A=290). Drift = the gated script refuses rather than silently recomputing on different data ("single-vintage by design").
3. **Exact commit**: every prereg and methods section names its commit (`prereg @e4aea1e` style). A published number without a commit hash is unverifiable — include it.

Template provenance line for any exported figure/table: `commit <hash> · SEED=7 MC=20 · inputs <artifact>=<sha256-prefix> · roster N=<n> (<stratum name>) · <date>`.

---

## 6. Checklist: "I finished a piece of work — which docs do I touch?"

Work through every row that applies. (The verification protocol itself — tests → pipeline → zero rank delta → audit — belongs to moneyball-change-control; this is only the DOC duty.)

| You just… | Touch |
|---|---|
| Changed which script owns a piece of math, or a cross-module convention | Spec: authoritative-code table row / conventions section. One line, code-pointer style. |
| Added a standing env dial | Spec: standing-dials line (value + ratification note). The full dial catalog entry → moneyball-config-and-flags' add-a-dial checklist. |
| Added a new script family or model layer | README: module map / numbered-layer list (precedents: §6 @51f2f92, §7 @3f91332). |
| Added kernel tests or audit checks | README + INDEX check counts (they WILL be stale; doc-rot-pass precedent @b3ff99c). State the new count in the commit subject too (e.g. "audit now 69 checks" @48fd00d). |
| Locked a prereg | The prereg file itself with the literal `STATUS: LOCKED` line; commit subject `… prereg LOCKED (pre-look)`. Nothing else yet — big5_methods gets its section at the outcome. |
| Consumed a look (pass or miss) | Prereg `## RESULT — THE ONE LOOK` verbatim; new numbered big5_methods.md section with verdict in the heading; commit subject `LOOK RESULTS: …` / `RESULT: MISS`; pre-declared consequences applied in the same batch. |
| Retired a prereg without a look | Prereg `## ADDENDUM` with the battery record verbatim; big5_methods section stating the GATE (DATA-GATED / DIAGNOSTIC-GATED, with the numeric re-entry condition); commit `RETIRED WITHOUT A LOOK`. |
| Learned an old result needs a caveat (via a LOCKED robustness look only) | Dated `[ANNOTATION]`/`ADDENDUM` inside the old section AND everywhere the claim renders (desk lines, prereg, methods) — original text unmodified. |
| Ran an audit | New dated `AUDIT_FINDINGS_YYYY-MM-DD[_SUFFIX].md` (append-only, never clobber an existing report); refuted list + known-benign additions included. |
| Got a user ratification / directive | Quote it verbatim in the commit body; mark "do not re-litigate" if that's the instruction (precedent @f12481b). |
| Anything at all | NEVER hand-edit a generated JSON artifact to make docs match (incident: the 18th-category producer clobber — the producer silently overwrote the hand-extended artifact; session-ratified, 2026-07). Fix the producer. |

---

## Provenance and maintenance (date-stamped 2026-07-09)

All facts above verified against the repo at main @88a7048 on 2026-07-09. Volatile facts and their one-line re-verification commands (run from the repo root; the path contains spaces — quote it):

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"   # or any worktree of this repo (read-only commands only)

# Living-doc vintages (last-touch commits)
git log --follow --oneline -3 -- README.md
git log --follow --oneline -3 -- MATHEMATICAL_SPECIFICATION.md
git log --follow --oneline -3 -- INDEX.md
git log --follow --oneline -3 -- big5_methods.md

# The four frozen docs are still single-commit @62a209e
git log --follow --oneline -- ARCHITECTURE_REVIEW_2026-07-02.md PERSONALITY_RECEPTIVITY_LAYER_2026-07-02.md
git log --follow --oneline -- AUDIT_ROADMAP.md stance_templates_review.md

# Live check counts (docs' stated counts rot; trust the run's own tail)
git grep -c "ok(" -- fec/tests/run_tests.py     # lines containing "ok(" (count grows — trust the run's own tail)
git log --all --oneline | Select-String "checks" | Select-Object -First 3   # newest audit count stated in a commit subject (count grows — trust the run's own tail)

# Claims-ledger freshness: newest look/retirement/lock on ANY ref (see §3.2)
git log --all --oneline | Select-String -Pattern "RESULT|RETIRED WITHOUT A LOOK|prereg LOCKED|SHIPPED"

# Vote Smart status specifically (main may lag a session branch)
git log --all --oneline | Select-String "Vote Smart"
git branch -a --contains e77703c                # which ref holds the RESULT-VS commit

# Mandatory-caveat wording, word-for-word sources
Select-String -Path big5_methods.md -Pattern "GENDER-CONFOUNDED|diagonal-dominant|A- |RETIRED WITHOUT A LOOK"
Select-String -Path big5_es_crossmodal_prereg.md -Pattern "ADDENDUM|superseded"
Select-String -Path big5_methods.md -Pattern "fact-check|inflated|0/5"

# Prereg anatomy conventions still hold
Select-String -Path big5_*_prereg.md -Pattern "^STATUS: LOCKED"
Select-String -Path big5_*_prereg.md -Pattern "^## RESULT"

# Citation-honesty specifics (Byrne / (1-1/e) / Chen=UAI)
Select-String -Path AUDIT_FINDINGS_2026-07-04.md -Pattern "Byrne attribution|guarantee scope|Chen venue|honest-analogical"

# Reproducibility contract
Select-String -Path MATHEMATICAL_SPECIFICATION.md -Pattern "Determinism contract|seed 7"
Select-String -Path big5_n_matrix_prereg.md, big5_es_votesmart_prereg.md -Pattern "fingerprint|Input pinning"
```

Last measured (dated — counts drift, so trust each run's own tail): `fec/tests/run_tests.py` 247 passed / 2 FAILED in LIVE on 2026-09-20 (standing reds `test_bill_collision_guards`, `test_make_staffer_network_html`); `fec/audit/audit_full.py` 559 passed / 9 FAILED in LIVE on 2026-09-19 (after that day's membership refresh) (both recorded in the Project Brain STATE); the chain has 80 `CHAIN` entries, 79 run by default (`fec/run_pipeline.py:45-302`), counted 2026-09-30 at main 25eefa3fc.

Standing maintenance duties for whoever owns this skill: (a) after any merge that adds a big5_methods.md section or consumes a look, re-derive §3's ledger from the newest sections and RESULT texts — never from memory or from this file's own previous version; (b) when the Vote Smart RESULT lands on main, fill big5_methods.md §22 per its prereg's fixed outcome-tier wording and update §3 here; (c) run a doc-rot pass (README/INDEX/spec counts, retired flags) whenever the audit-check or kernel-test count changes; (d) if this skill and a doc of record ever disagree, the doc of record wins and this skill gets fixed.
