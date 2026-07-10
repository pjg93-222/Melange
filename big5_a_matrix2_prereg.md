# Psych-audit round 6 — A vs the de-entangled cooperation criterion, NEW INSTRUMENT (st_mean)

STATUS: LOCKED (2026-07-10, committed before any look; adversarially reviewed pre-lock — two
independent lenses: statistics [0 CRITICAL / 0 MAJOR / 1 MINOR, incorporated] and discipline
[1 CRITICAL + 4 MAJOR, ALL required changes incorporated: fresh-lock reframing, round-5-scope
closure + anti-basis-shopping clause, grounds-no-claim context-matrix ban, pinned desk wording,
restored A_v1 repro secondary, branch-hygiene note]). User-authorized: Paul, "Lock it in"
(2026-07-10), following the successor-gate result. Goal: round 5 established that the
criterion side is clean (cooperation_v2) and that its look-refusal was INSTRUMENT-limited — the
supervised-Empath machinery cannot recover a true r=.40 signal on the MEM_A stratum (Addendum 1:
median +0.132, 2/5). **Successor-gate framing (adversarial-review Finding 1 incorporated): the
Addendum-1 successor clause ("the SAME diagnostic … passes ≥3/5 on bars 1–4") belongs to the
EMPATH instrument's data-growth path and is NOT claimed to be satisfied here — a new instrument
cannot satisfy a "SAME diagnostic" clause. This round is therefore a FRESH lock with its own
adversarial review (the audio/voice-round precedent for fielding a new instrument), which the
diagnostic INFORMS but does not gate: the diagnostic's role is power-honesty (rounds 4–5 doctrine
— no look may be taken by an instrument that cannot recover a planted true signal), and st_mean
demonstrably can (4/5 selection, 3/5 fresh-seed confirmation, b5_a_stratum_diag_record.md
@1609c25). Round 5's Empath data-growth gate remains open, untouched by this round in both
directions.** This round takes ONE look at whether a supervised **st_mean** text-A read is
distinct against cooperation_v2. Structure, bars, gates, and discipline mirror rounds 4–5
(big5_n_matrix_prereg.md, big5_a_matrix_prereg.md); shared mechanics are cited, not restated.
**The lock commit CONTAINS the executable spec: fec/b5_a_matrix2.py (the look script) rides this
same commit and imports the round-5 machinery (fec/b5_a_matrix.py), the diagnostic composition
(fec/b5_a_stratum_diag.py), and the §17 primitives (fec/b5_behavioral_instrument.py,
fec/b5_n_matrix.py) — the same-commit doctrine of rounds 4–5.**

## Compliance

- **Round 5's disposition is untouched**: it remains RETIRED WITHOUT A LOOK, diagnostic-gated for
  the EMPATH instrument; its data-growth gate stays open and is unaffected by this round's outcome.
  No Empath-A × cooperation_v2 pairing is computed here or ever has been.
- **Instrument change, honestly disclosed**: §17's instrument of record (Empath-supervised) is not
  abandoned or modified; §17/§18/§21 records stand as written. This round fields a SECOND
  instrument. Precedent: the program has always allowed new instruments under new preregs (audio,
  voice, interaction-structure); what it forbids is re-specing a closed one.
- **Prior contact disclosure (BEMB, 2026-07-07)**: big5_round4_prereg.md authored a display-Blue
  promotion for open-vocab bases vs the OLD criteria and the cache was built, but NO RESULT section
  exists, big5_blue_emb.json does not exist, and big5_methods.md has no BEMB entry — the test-half
  look was never taken (the campaign closed at §11 that evening). Any selection-half exploration
  would have touched cooperation_v1 on the even-md5 half only, never cooperation_v2. The 07-07
  "blue lever closed" phrasing refers to that display-promotion design, not to this validity
  question.
- **Selection disclosure (the diagnostic that licensed this round)**: 7 bases were screened on the
  five PINNED Addendum-1 seeds (empath, lsa128/256/512, st_mean, st_volctrl, empath+lsa256);
  st_mean was selected (4/5 bars 1–4, median +0.236) and CONFIRMED on five fresh seeds pinned
  before any sweep and never used for selection (3/5, median +0.192). The guard demonstrably binds:
  lsa256 cleared selection then REFUTED at 1/5 (+0.071). st_volctrl confirmed nearly identically to
  st_mean (+0.194), so the recovery is not volume-carried at the feature level. Full per-seed
  tables: b5_a_stratum_diag_record.md (same repo). **The entire selection was SYNTHETIC-ONLY**
  (planted signals; coop_v2 read only for its coverage mask) — no real-label information entered
  basis selection.
- **Honest prior: MODERATE-LOW.** The diagnostic proves st_mean CAN see a true r=.40 signal on
  this stratum; it says nothing about whether real A-signal exists there. The +.183 v1 text-A
  evidence was Empath-side; st features have never been paired with any real criterion in this
  program (BEMB look never taken). A MISS surprises no one and closes honestly.

## Criterion (pinned — unchanged from round 5)

- **cooperation_v2_z** from coop_v2_candidate.json, SHA-256 pinned below, composition FROZEN in
  fec/coop_v2_candidate.py (round-5 lock @28914b3): composite = mean of z(c1_bip) and z(c2_xshare),
  BOTH required; z within chamber; c3_recip = distinct facet, reported never composited (firewall).
- Criterion-side record: SB .873/.821; entanglement breadth +.708→−.140, log-volume +.739→−.159;
  gender −.021; coverage 315/533. Rosters: **MEM = 456** (§17 eligibility verbatim);
  **MEM_A = 290** (re-verified this session at every diagnostic run).

## Instrument (NEW — pinned)

- **st_mean**: all-MiniLM-L6-v2 chunk embeddings (256-word chunks, ≤40/doc, L2-normalized,
  mean-pooled) per member-genre doc (CREC / INTERVIEW / social, ≥50 tokens), ritual-phrase-stripped;
  artifact **b5_emb_cache_r6_st.npz** + meta, SHA-pinned below, built 2026-07-10 on the
  post-expansion corpus by fec/b5_a_stratum_diag.py --build st (recipe = b5_emb_build.py verbatim).
- Member matrix: within-genre z across members present in the genre, token-weighted cross-genre
  average (the b5_round4_eval composition, imported from fec/b5_a_stratum_diag.member_matrix).
  Coverage: all 456 MEM members (verified; the look ABORTS if keep ≠ MEM or dims ≠ 384).
- Supervision: identical §17 recipe — Ridge, ALPHAS [1..1000], nested 5-fold OOF over SEEDS
  [7,17,29,43,61], GridSearchCV cv=3 neg-MSE. **BI.oof is replaced process-wide by
  b5_a_stratum_diag.oof: the same deterministic fits distributed via n_jobs — numerical identity
  demonstrated by the diagnostic's EXACT Addendum-1 Empath reproduction (per-seed +0.105/+0.119/
  +0.132/+0.190/+0.251). Stats-review MINOR noted: the two implementations take different sklearn
  dispatch paths (n_jobs=None vs n_jobs=k), so the identity claim is EMPIRICAL (that exact
  reproduction), not by-construction — recorded so the RESULT inherits the caveat.**
- **All six models fit on st_mean features**: the five competitors (O=breadth, C=diligence,
  E=visibility, A_v1=old cooperation, ES=residual-GMP — BI.criteria verbatim, computed ONCE on MEM
  and sliced) and pred_A_v2 = oof(X_st[mask], cooperation_v2_z) within MEM_A. Bar 4 therefore
  compares within ONE instrument — an Empath competitor set would under-read the new column and
  rig the pass.
- Slicing semantics: round-5 verbatim (full-MEM vectors sliced to MEM_A rows; nothing re-z-scored
  or re-residualized on the subset; non-finite rule = recorded as 0 → MISS, counted in NM.NONFIN).

## Input pinning (the look ABORTS without consuming on any mismatch)

Values computed at lock by fec/_pin_round6.py (same commit):
- coop_v2_candidate.json `03418fd1d9407f8cb1a15e7beac62fec342c13f8b2fd35122a7748838fd11ecb`
  (IDENTICAL to the round-5 pin — criterion artifact unchanged)
- behavioral_dispositions.json `6b9bb9d2a15ce9be1ddd0a8ec63c51fef1449e68f37ffda08b3c70e6564397d7`
  (identical to round-5 pin)
- voteview_consistency.json `0bf7c461e9eca440535484bf325c5b90d423daf0573e984a1b8691a242194751`
  (identical to round-5 pin)
- behavior_panel.json `f47b9b045357cad2c5644f551fc934e8a0aa793a22d98272632547a276d22a50`
  (identical to round-5 pin)
- b5_emb_cache_r6_st.npz `69b1da00ebcc7bf4ecdbb07676630f39f6bbb01591ad8e8f8a83f6f4edd17619`
- b5_emb_meta_r6_st.json `e3189a7a4fcc5d13c4815da65481e5393ff0804d50cb2169f3a14a74ea0f2ea8`
- social_media.db speeches rows 234856 / posts rows 29098 (round-5 lock was 234827 — collectors
  added 29 rows since; the st cache was built AFTER that drift, so features and pins are
  self-consistent; the corpus feeds FEATURES only, never the criterion)
- MEM = 456; MEM_A = 290; st_mean dims = 384; st_mean coverage = MEM exactly (verified at pin)
Lock and look run the SAME SESSION (collectors can drift corpus counts).

## Bars for A_v2 (ALL five — round-5 wording verbatim, applied to the st_mean models)

1. Own held-out r(pred_A_v2, cooperation_v2_z) ≥ **+0.15** on MEM_A.
2. Exact permutation p < **.05** (K=5000, seed 20260708).
3. **Row-dominant**: |own r| ≥ |r(pred_A_v2, crit_c)| for c ∈ {O, C, E, ES} on MEM_A, own r > 0
   (coop_v1 excluded from the row set for the round-5 reason, stated so its absence is not hidden
   leniency; it bites at bar 4 instead).
4. **Column-specific, strict**: |r(pred_A_v2, coop_v2)| strictly exceeds |r(pred_c, coop_v2)| for
   every competitor c ∈ {O, C, E, ES, A_v1}, all st_mean-based, full-MEM vectors sliced to MEM_A;
   exact tie = FAIL.
5. **GATING confound partial, volume-hardened**: Frisch–Waugh partial r(pred_A_v2, coop_v2 |
   gender, party, log(1+n_cosponsored)) ≥ **+0.10 AND exact perm-p < .05** (K=5000, seed 20260710);
   n_cosponsored from the pinned behavior_panel.json, missing → 0.

## No demotion events this round — and why (pre-stated)

Round 5 defined Williams-guarded demotion for §17-passing traits because its pred_t WERE the §17
models. Here every pred_t is an st_mean model — a different instrument. A cross-read by a
non-record instrument can neither demote nor promote a §17 cell. The core matrix on st_mean
features is printed as CONTEXT ONLY, explicitly labeled, **NO status change in either direction
regardless of what it shows** (stronger than round-4's drift clause), and — adversarial-review
Finding 3 incorporated — **it GROUNDS NO CLAIM: no cell of it may be remarked upon, cited,
quoted, or used as evidence for any future claim, in any document, at any confidence level — not
as "context", not as a lower-confidence signal, not as meta-analytic input. The printout exists
solely so a reviewer can verify the machinery ran; it is not a scientific record.** An apparent
ES pass in it is noise atop a Tier-5-closed axis (methods §22); any future per-trait cross-read
on a new text basis requires its own full lock (the anti-basis-shopping clause below).

## No noiv analog — and why (round-5 reasoning, restated for the new instrument)

Criterion (cosponsorship records) and features (speech/tweet text) remain DISJOINT sources; no
shared-document channel exists. The volume channel is gated by bar 5's conditioning set. The one
new channel a reviewer might raise — instrument selection — is closed above: selection was
synthetic-only, and the fresh-seed confirmation used seeds never involved in selection.

## Secondaries (REPORTED, non-gating, firewalled — round-5 list verbatim minus A_v1 repro)

- Facet map: r(pred_A_v2, c1_bip_z / c2_xshare_z / c3_recip_z) on MEM_A.
- r(pred_A_v2, coop_v1) on MEM_A — is the new model still chasing the volume-entangled construct?
- Within-party own r: D-only and R-only on MEM_A.
- Raw corr(pred_A_v2, gender), corr(pred_A_v2, party) on MEM_A (fairness record).
- **Empath-A_v1 repro (RESTORED per adversarial-review Finding 5)**: r(pred_A_v1[Empath, §17
  recipe], coop_v1) on MEM and on MEM_A — a REPRODUCTION of the already-recorded §17 pairing, kept
  as the round-5 accountability check that the criterion re-specification did not break the old
  model's signal integrity. Computed in an isolated function that returns ONLY these two numbers;
  the Empath prediction vector is never placed beside cooperation_v2 (see prohibition below).
- Firewall: no claim, artifact, desk change, or methods claim from any secondary.

## Machinery validation (in-process, no look consumed — round-5 battery VERBATIM, on st_mean)

fec/b5_a_matrix.simulate_battery(X_st, D), unchanged: (a) PLANTED seed 424242 orthogonalized —
core ≥4/5, masked-A clears bars 1–4; (b) NULL seed 535353 — core 0/5, masked-A misses the stack;
(c) CONFOUND-ONLY seed 646464 incl. volume — bar 5 must REFUSE (<+0.10); (d) TRUE+CONFOUND seed
757575 incl. volume loading — bar 5 must ADMIT (≥+0.10, p<.05). Battery failure ⇒ RETIRE WITHOUT
A LOOK, recorded verbatim, no consumption (the rounds-4/5 outcome; it has happened twice and the
discipline held both times).

## Pre-declared consequences

- **PASS (bars 1–5) → fresh-seed re-derivation** (OOF seeds [101,113,127,139,151], all six model
  vectors recomputed, permutation seeds pinned) **must re-clear ALL FIVE bars**; failure = FRAGILE
  = MISS for all consequences INCLUDING closure. On a re-derived PASS: recorded as **"A:
  criterion-valid AND distinct against the de-entangled cooperation criterion (v2; MEM_A=290
  stratum), via the st_mean semantic instrument (2026-07-10)"** — methods **§23**, memory, and ONE
  desk wording change, EXACT TEXT PINNED (Finding 4): the Big-5 tab's A caveat line gains the
  sentence **"A reads distinct against the volume-de-entangled cooperation criterion (v2) via the
  st_mean semantic instrument (2026-07-10); this claim is st_mean-specific and does not extend to
  other text instruments."** — nothing else on the desk changes; §17's and §21's records
  annotated, never overwritten. **NO engine change flows from this look** (the engine's A-slot
  basis and the separate coop_v2 engine-promotion decision are untouched and remain Paul's).
- **MISS on any bar**: "st_mean-A vs de-entangled cooperation: not distinct — route CLOSED for
  this instrument-basis" (one look, no re-spec; the closure covers ANY composite over {c1, c2, c3}
  — any subset, any weights, any re-anchoring, the round-5 scope verbatim — for ANY st-family
  basis: st_mean, st_volctrl, and any pooling/weighting/chunking variant of MiniLM-class sentence
  embeddings over this corpus). A stays criterion-valid / not-discriminant; recorded methods §23 +
  memory. **Round 5's Empath data-growth gate is NOT closed by an st MISS** (different instrument,
  per its own Addendum). **ANTI-BASIS-SHOPPING CLAUSE (binding regardless of outcome): no future
  instrument basis — LSA revisit, a different transformer, audio, anything — may be paired with
  cooperation_v2 except under its own new prereg that (i) passes the Addendum-1 stratum-power
  diagnostic AND a fresh-seed confirmation on seeds never used for its selection, (ii) discloses
  the FULL ledger of every basis ever screened against that diagnostic (currently 7:
  b5_a_stratum_diag_record.md), and (iii) is adversarially reviewed pre-lock. Diagnostic screening
  is cheap by design; looks are not — the ledger requirement is what makes repeated screening
  honest rather than shopping.**
- **Separable, either way**: the coop_v2 ENGINE-promotion decision (round-5 lock language) remains
  open and Paul's alone; ranks_python.json stays byte-identical regardless.

## ADDENDUM 1 (2026-07-10, PRE-LOOK) — corpus-count drift; gate REPLACED by a strictly stronger one

Recorded BEFORE the look; no look was attempted against a drifted gate (the battery ran ALL GREEN
under --simulate: sim(a) core 5/5, A plant +0.312 row/col True; sim(b) 0/5 + stack MISS; sim(c)
partial −0.072 refused; sim(d) +0.514 admitted — the machinery validation the Empath instrument
failed twice). The --look gate then reported fingerprint DRIFT. Diagnosis (fec/_pin_round6.py
re-run): **speeches row count 234856 → 234878 (+22; a live collector tick — the count also moved
234827→234856 earlier this session); ALL SIX artifact SHAs identical, posts identical, MEM=456,
MEM_A=290, st coverage == MEM, dims 384 — all identical.**

Why the count pin was the wrong proxy HERE (and right in rounds 4–5): rounds 4–5 computed their
features LIVE from the corpus, so corpus drift = feature drift and the count pin guarded the
instrument itself. Round 6's features are FROZEN in the SHA-pinned b5_emb_cache_r6_st.npz; the
live corpus's only remaining roles are (i) MEM eligibility (len(alltext)>2000) and (ii) the
declared Empath repro secondary (reported, non-gating). A raw row count is a WEAKER identity
proxy for (i) than the roster's actual content.

Amendment (bar-neutral; no bar/seed/roster/composition/consequence change; STRENGTHENS the gate):
- speeches/posts counts move from GATING to REPORTED-AT-LOOK (the RESULT records them).
- New HARD gates added: **MEM roster content-hash md5 = `374fa4a44d64b7de3d468913a0297c6d`
  (456 members, exact membership not just count) and MEM_A roster content-hash md5 =
  `3346d05a720f58bb5c46198fae1d1048` (290 members)** — strictly stronger than the counts they
  replace: a one-in-one-out eligibility flip under a stable count would now refuse the look.
- All six artifact SHA gates, roster-size gates, st coverage == MEM, and dims == 384 unchanged.
- The Empath repro secondary inherits an input-freshness caveat: it featurizes live text
  (text-hash cached), so its value may differ from §17's +.183 by input drift; it remains
  reported-only.
This addendum + the matching script change ride one commit, look taken immediately after.

## Discipline

One look, same session as the lock. No LLM calls. No audio. No bar/seed/roster/composition changes
after the lock commit. **No NEW Empath pairing may be computed under this prereg — specifically,
no Empath prediction may ever be correlated with cooperation_v2 or any of its facets; the sole
permitted Empath computation is the declared A_v1×coop_v1 REPRODUCTION secondary (an
already-recorded §17 pairing).** All new numerics enumerated above; machinery imported from
rounds 3–5 and the diagnostic. The RESULT-A2 section appends verbatim (MISSes included),
committed same session.
**Branch-hygiene note (Finding 7): methods currently ends at §21 on this branch; §22 is occupied
by the Vote Smart ES RESULT recorded on main (2026-07-09 late evening, parallel session). This
round's RESULT writes methods §23. If a merge lands additional sections before the RESULT commit,
the section number shifts to the next free integer — the CONTENT is pinned, the number is not;
the RESULT records which number it landed at.**

## RESULT-A2 (2026-07-10, the one look, appended verbatim)

Gates at look: lock True | look not yet taken | artifact fingerprints MATCH (cv 03418fd1d9… bd
6b9bb9d2a1… vv 0bf7c461e9… pn f47b9b0453… stz 69b1da00eb…) | corpus REPORTED per Addendum 1:
speeches 234878 posts 29098 | rosters MEM=456 MEM_A=290 | roster content MEM md5
374fa4a44d64b7de3d468913a0297c6d, MEM_A md5 3346d05a720f58bb5c46198fae1d1048 (both match
Addendum-1 pins) | non-finite events: 0.

In-process battery (re-run at look): sim(a) PLANTED core 5/5, A own +0.312 p .0002 row True col
True -> OK; sim(b) NULL core 0/5, stack MISS -> OK; sim(c) CONFOUND-ONLY bar5 partial −0.072
refused -> OK; sim(d) TRUE+CONFOUND bar5 partial +0.514 p .0002 admitted -> OK. ALL GREEN.

Masked discriminant matrix (st_mean instrument; CONTEXT ONLY per the lock — grounds no claim, no
cell may be cited as evidence anywhere):

    model\crit         O        C        E        A       ES      CV2
    pred_O       +0.190   +0.096   +0.056   +0.156   +0.047   +0.006
    pred_C       +0.085   +0.159   -0.146   +0.083   +0.123   -0.041
    pred_E       +0.036   -0.098   +0.460   -0.020   -0.123   -0.120
    pred_A       +0.161   +0.103   -0.048   +0.142   +0.078   -0.049
    pred_ES      +0.043   +0.139   -0.217   +0.076   +0.191   +0.056
    pred_A2      +0.044   -0.018   -0.204   -0.030   +0.013   +0.033

The five locked bars for A_v2 (st_mean):
  [primary] bar1 own r=+0.033 | bar2 perm-p=0.2961 | bar3 row-dom=False | bar4 col-specific=False
  (max rival |r|=0.120) | bar5 partial=+0.036 p=0.2685  =>  **MISS** (all five bars failed; no
  re-derivation runs on a primary MISS).

Secondaries (reported, non-gating, firewalled):
  facet r(pred_A_v2, c1 bipartisan share)  = +0.010 (n=290)
  facet r(pred_A_v2, c2 cross-party share) = +0.052 (n=290)
  facet r(pred_A_v2, c3 reciprocity)       = −0.099 (n=253)
  r(pred_A_v2, coop_v1) on MEM_A           = −0.030
  within-party own r: D-only +0.087 (n=155) | R-only −0.001 (n=135)
  raw corr: gender +0.061 | party +0.042 (fairness record: clean)
  REPRO (Empath A_v1 × coop_v1, declared accountability check): MEM **+0.183 — the §17 recorded
  value EXACTLY** (7/456 members re-featurized for input drift) | MEM_A +0.227. The criterion
  re-specification did not break the old model's recorded signal.

**VERDICT: A_v2 MISS — "st_mean-A vs de-entangled cooperation: not distinct — route CLOSED for
this instrument-basis (any composite over {c1, c2, c3}, any st-family basis per the lock)." A
stays criterion-valid / not-discriminant (§17/§21 unchanged). Consequences applied: methods §23 +
memory; NO desk change (PASS-only consequence); NO engine change; round-5's Empath data-growth
gate remains OPEN; the anti-basis-shopping clause is binding for any future basis. Honest
reading: the battery proved this instrument CAN recover a true r=.40 signal on this exact stratum
(+0.312 planted), so this MISS is informative about the WORLD, not the machinery — the
MODERATE-LOW prior was right; supervised open-vocabulary semantic text carries no distinct
cooperation-v2 signal on the finance-active stratum.**
