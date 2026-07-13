# Psych-audit round 9 — fresh interview-antagonism criterion for Agreeableness

STATUS: LOOK LOCKED 2026-07-12 — criterion qualified 5/5; A look not yet taken.

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

LABEL_SHA256: `15ffb00ba199708c17733260205e0580ce766f3b37e0c69a74965b35b4ab0575`

- cooperation_v2: `f0f958dfd35e89f7ab08e73e4f4aab59f762e50558803da4f6dec3a455ff224c`
- hearing antagonism: `7eb389593de20dd555fb3d23ffffa3e7fc48d6cbf2611434548ec06b5d282206`
- behavioral dispositions: `57ca1e2b1731cbeed4411645c2b527a8db0136362c2d3d4654dda8faaa852e03`
- Voteview consistency: `0bf7c461e9eca440535484bf325c5b90d423daf0573e984a1b8691a242194751`
- behavior panel: `491761ea130f8458ae0d09d15be20619b31011ab14e56e6a05bfbdf3d703a4cb`
- st_mean NPZ/meta: `69b1da00ebcc7bf4ecdbb07676630f39f6bbb01591ad8e8f8a83f6f4edd17619` / `e3189a7a4fcc5d13c4815da65481e5393ff0804d50cb2169f3a14a74ea0f2ea8`
- Empath cache: `fd5ff76d59f59ed67889d1dd6a2e2f9d42ca596122bf831ae1a126b5d9d7383f`
- social_media.db rows: speeches **268173**, posts **29098**

No result bar, threshold, basis, prompt, exclusion, seed, or consequence changes after label generation.

## Collection addendum 1 — parser-only repair before criterion inspection

The first operational scoring launch was stopped after 9 accepted members and 18 parse failures.
Only completion/error counts and exception strings were inspected; no accepted score, member ranking,
correlation, reliability, or gate statistic was viewed. The failures were valid JSON followed by
trailing model text (`JSONDecodeError: Extra data`). The parser now accepts the first complete JSON
object with `JSONDecoder.raw_decode`, and a successful retry removes that member's stale error entry.
The prompt, model, halves, numeric fields, score formula, roster, gates, and trait protocol are unchanged.

## STAGE-1 RESULT — CONSUMED 2026-07-12: criterion QUALIFIED 5/5

```text
=== INTERVIEW-ANTAGONISM CRITERION GATE ===
  G1 coverage/reliability: n=322 half-r=+0.537 SB=0.699 (n>=250, SB>=.60) -> PASS
  G2 raw confounds: party=+0.109 gender=-0.032 log_words=-0.005 -> PASS
  G3 cross-venue hearing convergence: r=+0.160 n=282 -> PASS
  G4 cooperation direction: r=-0.072 n=207 (must <0) -> PASS
  G5 excluded-content discriminant max|r|=0.242 (<.50) -> PASS
  CRITERION VERDICT: 5/5 -> QUALIFIED
```

Stage 2 is now armed under the fingerprints above. No trait prediction was paired with this
criterion during Stage 1.
