# Psych-audit round 9 — fresh interview-antagonism criterion for Agreeableness

STATUS: CRITERION LOCKED 2026-07-12 — no labels generated; A look not armed.

## Rationale and independence

The full-roster Blue instrument remains 3/5: its cooperation-trained A row is criterion-related but
not discriminant. Round 6 closed `st_mean` against cooperation_v2; that result remains binding. This
round asks a genuinely different, untouched question: does the already-defined cooperation-trained
`st_mean` A prediction generalize to a fresh low-A criterion—dispositional interview antagonism?
No interview-antagonism labels existed when this file and its scorer were frozen.

The criterion rubric counts only reporter hostility, personal contempt, and gratuitous cruelty.
Policy conflict and principled dissent are scored separately and excluded. Member identities are
omitted from the prompt. Interview appearances are deterministically divided into package-disjoint
halves; both halves are scored in one Haiku 4.5 call under the frozen prompt in
`fec/interview_antagonism_score.py`. Cost rule satisfied: Haiku, never Fable/Opus.

## Screening ledger and synthetic gate

Coverage before labels: 322 eligible members; 309 intersect the fixed 470-member instrument roster.
Empath was screened and rejected: pinned seeds 2/5 (median +.159), fresh seeds 2/5 (median +.142).
`st_mean` cleared: pinned seeds 3/5 (median +.222), fresh confirmation 5/5 (median +.203). Exact
transcripts are in the 2026-07-12 task/audit record. This licenses this criterion-specific prereg;
it does not reopen the consumed Round-6 cooperation result.

## Stage 1 — criterion gate (one look at newly generated labels)

All five must pass before the trait look can be armed:

1. Coverage n>=250 and package-split reliability Spearman-Brown >=.60.
2. Raw (pre-control) contamination: |r(party)|<=.20, |r(gender)|<=.15, |r(log words)|<=.20.
3. Cross-venue convergence with ratified hearing antagonism r>=+.15 at n>=150.
4. Construct direction with cooperation_v2 r<0 at n>=180.
5. Excluded-content discriminance: max absolute correlation with policy-conflict or principled-dissent scores <.50.

Any failure rejects the criterion and forbids the A look. All pass permits a result addendum that
pins the label/input hashes and changes status to `LOOK LOCKED` before any trait pairing.

## Stage 2 — five locked A bars

Instrument: `st_mean` features, but the target/model is fixed independently: cooperation_v2-trained
Ridge with nested alpha selection and outer folds over the full roster; only target-covered training
rows enter each fold, and all held-out rows receive predictions. Fresh criterion = negative mean
interview antagonism, residualized on party, gender, and log interview words. Residualization is a
confound control, not independent validity evidence; Stage-1 raw-confound gates prevent construction-
guaranteed cleanliness from licensing the criterion.

On the fresh criterion roster, all five must pass:

1. r(pred_A, agreeableness-pole) >= +.15.
2. Exact one-sided permutation p<.05 (the established BI seed/K recipe).
3. Row dominance versus O/C/E/ES behavioral criteria on the same roster, own r>0.
4. Strict column specificity versus the O/C/E/ES Empath OOF models on the same A criterion.
5. Frisch-Waugh partial controlling party, gender, and log words >=+.10 with permutation p<.05.

Primary PASS must re-clear all five under OOF seeds [101,113,127,139,151]. The no-interview
`st_mean` basis (CREC+social only, same cached per-genre embeddings and model) must have positive
permutation p<.05 and r at least half the primary. Full PASS => “A criterion-valid, distinct, and
no-interview robust” and may update the instrument from 3/5 to 4/5 full-roster plus the separate
interview-stratum N result. Five-bar PASS with ship-gate failure => conditional/shared-source only,
no production promotion. Any five-bar or re-derivation miss closes this criterion/basis route.

## Lock-time fields for Stage 2

LABEL_SHA256: `[AFTER-STAGE-1]`

No result bar, threshold, basis, prompt, exclusion, seed, or consequence changes after label generation.
