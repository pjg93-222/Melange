# Psych-audit round 5 — A re-tested against the DE-ENTANGLED cooperation criterion (v2)

STATUS: LOCKED (2026-07-09, committed before any look; adversarially reviewed pre-lock, all required
changes incorporated; user-authorized: "De-entangle A criterion"). Goal: the §17 A verdict
("criterion-valid, not discriminant") traced to a CRITERION defect, not a trait defect —
cooperation_z was 2/3 raw cosponsorship volume, entangled +.708 with breadth (volume common cause;
the dependability audit's "volume proxy" indictment). This round pins a share-based cooperation
criterion (v2) and takes ONE look at whether the supervised text-A read is distinct against it.
Structure, gates, and discipline mirror round 4 (big5_n_matrix_prereg.md); shared mechanics are
cited, not restated. **The lock commit CONTAINS the executable spec: fec/b5_a_matrix.py (the look
script) and fec/coop_v2_candidate.py (the composition freeze) ride this same commit — the
constructor is pinned by same-commit code (the round-4 Addendum-1 doctrine).**

## Compliance

- **Not a CT-CM/halo re-spec**; per-trait external criterion validity (§15's field-correct bar).
- **Round-2's dialogic-assent closure is untouched**: §18 closed the assent-lexicon INSTRUMENT
  route ("Dialogic-assent route CLOSED … the assent mechanism is now tested-and-closed"). The
  instrument here is the §17 Empath-supervised machinery (the instrument of record); what changes
  is the CRITERION — a revision motivated and pinned entirely on criterion-side evidence
  (dependability audit + the verified +.708/+.739 entanglement), before any instrument pairing.
- **§17/§18 records stand as written** (v1 history). This look creates a v2-criterion record; it
  does not overwrite the v1 record. NO-STATUS-CHANGE clause: the reproduced §17 matrix cells cannot
  promote or demote any trait in either direction (drift is drift — the round-4 clause verbatim);
  the only §17-touching outcome is the Williams-guarded demotion event defined below. Specifically:
  an apparent ES pass in the reproduction is drift, not evidence.
- **Honest prior: MODERATE** — unlike round 4's N (no prior text signal), A's text read is real
  (+.183, perm-p .0004) and A-specific in the §15 partial (Pink-A→cooperation +.100 controlling
  ES; Pink-ES +.049 p=.30 null). The open question is only whether the C/O cross-reads were carried
  by the criterion's volume component. If they were, de-entanglement resolves dominance; if pred_A
  genuinely reads diligence/breadth, it misses and that closes honestly.

## Criterion (pinned; criterion-side work complete BEFORE this lock)

- **cooperation_v2_z** from coop_v2_candidate.json, SHA-256
  `03418fd1d9407f8cb1a15e7beac62fec342c13f8b2fd35122a7748838fd11ecb`, composition FROZEN in the
  same-commit generator fec/coop_v2_candidate.py: composite = mean of z(c1_bip: bipartisan tie
  share) and z(c2_xshare: directional cross-party cosponsorship share, ≥10 known-party
  cosponsorships), **BOTH required**; z within chamber. c3_recip (reciprocity) is a distinct facet
  (anticorrelates with both cross-party shares) — reported, never composited, and no claim may be
  derived from it (firewall).
- Criterion-side record (measured pre-lock, quoted for the record): split-half SB c2 .873 / c3
  .821 (halves reproducible via the committed generator); entanglement old→new: breadth
  +.708→−.140, log-volume +.739→−.159, diligence +.086→−.061, party −.093→−.156; **gender loading
  corr(coop_v2, female) = −.021 (n=315, criterion-side, clean)**; new-vs-old +.507; c1-c2 +.524,
  c1-c3 −.217, c2-c3 −.189.
- Rosters (exact, verified pre-lock and independently re-verified by the adversarial reviewer):
  **MEM = 456** (§17 eligibility verbatim); **MEM_A = MEM ∩ cooperation_v2_z non-null = 290**
  (composite coverage 315 of 533; the 218 uncovered members are outside this look entirely).
  Round-4's power study: a true r=.40 planted signal passes reliably from n≈250 — properly powered
  at 290, with the honest caveat that the study showed 4/5 at n=300 (5-rep noise): a single-draw
  battery refusal remains possible, and RETIRE-WITHOUT-A-LOOK is the pre-declared outcome if so.

## Input pinning (the look ABORTS without consuming on any mismatch)

Read by the LOOK itself:
- coop_v2_candidate.json `03418fd1d9407f8cb1a15e7beac62fec342c13f8b2fd35122a7748838fd11ecb`
- behavioral_dispositions.json `6b9bb9d2a15ce9be1ddd0a8ec63c51fef1449e68f37ffda08b3c70e6564397d7`
  (core criteria O/C/E + old cooperation for the A_v1 model)
- voteview_consistency.json `0bf7c461e9eca440535484bf325c5b90d423daf0573e984a1b8691a242194751`
  (ES = residual-GMP inputs)
- behavior_panel.json `f47b9b045357cad2c5644f551fc934e8a0aa793a22d98272632547a276d22a50`
  (bar-5 volume covariate: members[m].n_cosponsored, missing → 0)
- social_media.db speeches rows 234,827 / posts rows 29,098 (corpus)
- MEM = 456; MEM_A = 290
Environment pin only (not read by this look; recorded to date the vintage):
interaction_features.json `55d908d7ed1a7b1d0b7cb889f01484f6d454a9bed57847cf39ebfdcf68f26553`.
bipartisan.json needs no pin — c1 is frozen inside the SHA-pinned candidate artifact. Lock and look
run the SAME SESSION (weekly collectors can drift the corpus counts).

## Instrument & protocol (imported, zero re-implementation)

- §17 machinery via fec/b5_behavioral_instrument.py (featurize/oof/exact_perm_p, seeds/alphas/perm
  seed 20260708 unchanged); round-4 components via fec/b5_n_matrix.py (rr/zz/fw_partial seed
  20260710/williams_t/plant_set) — imported, not copied (the non-finite counter therefore lives in
  b5_n_matrix.NONFIN and is reported from there). New script: `fec/b5_a_matrix.py` (same commit),
  PREREG constant = THIS file; gate = round-4's refusal conditions verbatim (LOCKED line present;
  no newline-anchored RESULT-A heading; fingerprints and rosters match; in-process battery green).
- Models: the five §17 models reproduced on MEM (O, C, E, A_v1 = old-cooperation-supervised, ES =
  residual-GMP-supervised); **pred_A_v2 = oof(X_sub, cooperation_v2_z)** trained/evaluated within
  MEM_A.
- **Slicing semantics (pinned)**: all five §17 criteria — including ES = residual-GMP, residualized
  on OLD cooperation/extremity/party over the FULL MEM=456 — and all five full-MEM prediction
  vectors are computed ONCE on MEM and SLICED to MEM_A rows for every MEM_A cell. Nothing is
  re-z-scored or re-residualized on the subset; X rows are the roster-z-scored matrix (round-4
  protocol). Matrix cells annotated with their n. Non-finite rule: round-4 verbatim (recorded as
  0 → counts toward MISS, event reported).

## Bars for A_v2 (ALL five; the round-4 five-bar structure with A in the hot seat)

1. Own held-out r(pred_A_v2, cooperation_v2_z) ≥ **+0.15** on MEM_A.
2. Exact permutation p < **.05** (K=5000, seed 20260708). (Power honesty: at n=290 this binds at
   r≈.097 one-sided — bar 1 remains the binding magnitude bar.)
3. **Row-dominant**: |own r| ≥ |r(pred_A_v2, crit_c)| for all four other criteria (O=breadth,
   C=diligence, E=visibility, ES=residual-GMP), all on MEM_A, own r > 0. **coop_v1 is deliberately
   NOT in the row-dominance set** (stated so its absence is not a hidden leniency): dominance over
   a noisier variant of one's own construct would be a wrong requirement — the v1/v2 relation is
   instead tested where it bites, as a bar-4 rival model and a reported secondary.
4. **Column-specific, strict**: |r(pred_A_v2, coop_v2)| strictly exceeds |r(pred_c, coop_v2)| for
   every competitor c ∈ {O, C, E, ES, **A_v1**}, all on MEM_A (full-MEM prediction vectors sliced
   to MEM_A rows); exact tie = FAIL. A_v1 is included deliberately — if the OLD-criterion model
   reads the NEW criterion as well as the model trained on it, the revision added nothing and must
   not pass. (Power note for the RESULT: the five competitors train on 456 rows vs A_v2's 290 — a
   pass is not rigged in A's favor; a miss is partly power-limited.)
5. **GATING confound partial, volume-hardened**: Frisch–Waugh partial r(pred_A_v2, coop_v2 |
   gender, party, log(1+n_cosponsored)) ≥ **+0.10 AND exact perm-p < .05** (K=5000, seed 20260710).
   Volume sits in the conditioning set because volume de-entanglement IS the claim under test;
   n_cosponsored from the pinned behavior_panel.json, missing → 0.

## Demotion events (§17-passing traits O/C/E vs the new A column)

Round-4's pinned rule verbatim, on MEM_A: demotion for trait t iff |r(pred_t, coop_v2)|_MEM_A >
|r(pred_t, crit_t)|_MEM_A AND Williams' t (shared pred_t, sign-aligned, two-sided) p < .05; failing
the guard = "stratum inversion, n.s." — reported, no demotion. A declared demotion annotates §17
("not row-dominant on the cooperation-v2 stratum"), never reverses it.

## Machinery validation (in-process, no look consumed — round-4 battery adapted to THIS round)

All generator coefficients pinned by the same-commit code of fec/b5_a_matrix.py. The battery's
fw_partial uses **this round's bar-5 conditioning set [gender, party, log1p(n_cosponsored)]
verbatim** (not round-4's turns/sh set):
(a) PLANTED (seed 424242, orthogonalized plant_set): core ≥4/5; masked-A plant clears bars 1–4.
(b) NULL (seed 535353): core 0/5; masked-A leg misses the full 5-bar stack at n=290.
(c) CONFOUND-ONLY (seed 646464): synthetic criterion driven by gender/party/**log1p(n_cosponsored)**
    alone — bar 5 must REFUSE (<+0.10).
(d) TRUE+CONFOUND (seed 757575): planted signal **plus additive gender/party AND volume loadings**
    (volume in the mix is mandatory here — the round's whole claim is that the gate admits a true
    signal that coexists with volume) — bar 5 must ADMIT (≥+0.10, p<.05).
Battery failure ⇒ the round-4 outcome: RETIRE WITHOUT A LOOK, recorded verbatim, no consumption.

## No noiv analog — and why (pre-stated so its absence is not a hidden leniency)

Round 4 needed a shared-source ship-gate because the N criterion was computed FROM the same
interview transcripts the features ingest. Here criterion (cosponsorship records, bills archive)
and features (speech/tweet text) come from DISJOINT sources; there is no shared-document channel.
The volume channel — the one genuine cross-source coupling — is gated by bar 5's conditioning set.

## Secondaries (REPORTED, non-gating, firewalled)

- Facet map: r(pred_A_v2, c1_bip_z), r(pred_A_v2, c2_xshare_z), r(pred_A_v2, c3_recip_z) on MEM_A.
- **r(pred_A_v2, coop_v1) on MEM_A** — is the new model still chasing the volume-entangled construct?
- **Within-party own r: D-only and R-only on MEM_A** — the criterion's party loading rose to −.156
  and bar 5's linear partial does not answer a party-interaction attack; these do.
- Reproduction context: r(pred_A_v1, coop_v1) on MEM and on MEM_A.
- Raw corr(pred_A_v2, gender), corr(pred_A_v2, party) on MEM_A (fairness record).
- Firewall: no claim, artifact, desk change, or methods claim from any secondary.

## Pre-declared consequences

- **PASS (bars 1–5) → fresh-seed re-derivation** (OOF seeds [101,113,127,139,151], all six model
  vectors recomputed, permutation seeds pinned) **must re-clear ALL FIVE bars**; failure = FRAGILE
  = MISS for all consequences INCLUDING closure. On a re-derived PASS: recorded as **"A: criterion-
  valid AND distinct against the de-entangled cooperation criterion (v2; MEM_A=290 stratum)"** —
  methods §21, memory, and ONE desk wording change (the Big-5 tab caveat line gains: "A reads
  distinct against the volume-de-entangled cooperation criterion (2026-07-09)"); §17's v1 record
  annotated, not overwritten. **NO engine change flows from this look.**
- **MISS on any bar**: "text-A vs de-entangled cooperation: not distinct — route CLOSED" (one look,
  no re-spec). **The closure covers ANY composite over {c1, c2, c3} — any subset, any weights, any
  re-anchoring**; a genuinely new criterion would require new behavioral data or a new construct
  and its own prereg. A stays criterion-valid / not-discriminant; recorded methods §21 + memory.
- **Separable, either way**: whether cooperation_v2 replaces cooperation_z as the ENGINE disposition
  (susceptibility .40 slot + seed_prob .10 slot + desk radar axis) is a PRODUCT decision made by
  Paul after this look, informed by the criterion-side record (reliability, de-entanglement,
  fairness) and a receptivity-stability report — produced SANDBOXED (no live artifact touched) and
  only on request; ranks_python.json is pillar-math and must stay byte-identical regardless. A
  text-side MISS does not decide it — criterion hygiene and text validity are independent
  questions. Members without coverage (218/533) would fall to neutral 0 per the missing-disposition
  rule, never a silent mixed basis.

## Discipline

One look, same session as the lock. No LLM calls. No audio. No bar/seed/roster/composition changes
after this commit; the composition was frozen on criterion-side evidence before this lock and may
not be revisited after the look. Machinery imported from rounds 3–4; all new numerics enumerated
above. The RESULT-A section appends verbatim (MISSes included), committed same session.

## ADDENDUM 1 (2026-07-09) — battery refused; stratum-power diagnostic; RETIRED WITHOUT A LOOK (diagnostic-gated)

Battery run (the `--look` invocation), recorded verbatim: sim(a) PLANTED core 4/5 (clears ≥4) |
**A own +0.105 p .0392 row FALSE col TRUE → FAIL**; sim(b) NULL OK; sim(c) CONFOUND-ONLY incl.
volume OK (partial −0.051 refused); sim(d) TRUE+CONFOUND incl. volume OK (+0.532 admitted). The
in-process gate held: **"LOOK REFUSED (not consumed): simulate battery failure." No look was taken;
no real trait × criterion pairing has ever been computed in this round.**

Stratum-power diagnostic (SYNTHETIC ONLY, the battery's exact constructor, 5 seeds
424242/515151/616161/717171/818181, on the actual MEM_A=290 stratum): own r = +0.105, +0.119,
+0.132, +0.190, +0.251 — **median +0.132 < the +0.15 bar; bars 1–2 pass 2/5; bars 1–4 pass 2/5.**
Interpretation: this is NOT single-draw flakiness (the round-4 power study's random-roster draws at
n≈290–300 recover ~.14–.24, median ≈.195). **The MEM_A stratum itself — members with ≥10
known-party cosponsorships in the finance-scoped archive — carries genuinely less recoverable text
signal at this n** (more homogeneous Empath profiles). A true r=.40 signal would MISS ~60% of the
time; taking the look would have been a coin flip on machinery noise, exactly what the battery
exists to refuse. A multi-rep battery re-spec was considered and REJECTED: it would also have
refused (2/5 < any honest threshold), so no battery amendment can license this look today.

**Disposition: RETIRED WITHOUT A LOOK.** No RESULT-A exists; no MISS is recorded; text-A vs the
de-entangled criterion is neither validated nor closed — **DIAGNOSTIC-GATED**. Successor condition,
pinned now: a new prereg (same five-bar structure, fresh fingerprints) may be locked only when the
SAME diagnostic (this constructor, these five seeds, run on the then-current MEM_A stratum) passes
**≥3/5 on bars 1–4**. Both coverage growth (more members reaching c2's ≥10-cosponsorship floor as
the bills archive accrues) and corpus growth (richer member text) feed that gate; it is
synthetic-only, so checking it never risks a look. The criterion work stands on its own record:
cooperation_v2 (SB .873/.821 components, breadth entanglement +.708→−.140, volume +.739→−.159,
gender −.021) remains the candidate for the SEPARATE, user-gated engine-promotion decision — which
never depended on this look (criterion hygiene ≠ text validity, per the lock).
