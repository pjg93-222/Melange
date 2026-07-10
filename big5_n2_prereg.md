# Psych-audit round 6 — text-N vs behavioral reactivity, SUCCESSOR to round 4 (coverage-gated re-attempt)

STATUS: DRAFT — LOCKS ONLY WHEN ALL LOCK-TIME FIELDS BELOW ARE FILLED AND THE PINNED
DIAGNOSTIC PASSES. This is the successor prereg round 4 pinned: "successor prereg only at
reactivity coverage MEM_N ≥ 250 within the §17-eligible roster (same five-bar structure, fresh
fingerprints)" (big5_n_matrix_prereg.md Addendum 2; methods §20). Round 4 was RETIRED WITHOUT A
LOOK (battery refused twice at MEM_N=201; power study: a true r=.40 recovers 5/5 only from
n≈250). No look has ever been taken on the text-N × reactivity pairing; §17/§18/§20 records
stand as written.

## Coverage gate (the round-4 pin, verified at lock)

- MEM_N (= §17 MEM ∩ reactivity_z non-null) must be ≥ **250** at lock, achieved by CORPUS GROWTH
  ONLY (interview back-catalog collection: pbs/npr/fox legs, 2026-07-09 backfill). The reactivity
  SPEC (interaction_features.py floors ≥12 turns/program & ≥8 members/program; behavioral_
  dispositions.py ≥30 qualifying turns, sqrt(turns/150) shrinkage) is BYTE-UNCHANGED from the
  round-3 ship — coverage came from data, not from moving the floors (stated so the gate cannot
  be accused of being re-specced to pass).
- **Pinned pre-lock diagnostic (round-4 Addendum-2 condition, adapted per round-5's stratum
  lesson): the battery's exact constructor (b5_n_matrix.plant_set, orthogonalized), 5 seeds
  424242/515151/616161/717171/818181, run on the ACTUAL new MEM_N stratum, must pass ≥3/5 on
  bars 1–4.** Synthetic-only — no real trait × criterion pairing is computed; checking it never
  consumes anything. Diagnostic transcript is appended below at lock.

## LOCK-TIME FIELDS (filled at lock, before any look; the look ABORTS on any mismatch)

- MEM = [LOCK: n]; MEM_N = [LOCK: n ≥ 250]
- behavioral_dispositions.json SHA-256 = [LOCK]   (fresh post-backfill regeneration)
- interaction_features.json SHA-256 = [LOCK]      (fresh post-backfill regeneration)
- voteview_consistency.json SHA-256 = [LOCK]
- behavior_panel.json SHA-256 = [LOCK]
- social_media.db speeches rows = [LOCK] / posts rows = [LOCK] (collectors QUIET at lock; lock
  and look same session)
- 5-seed diagnostic transcript = [LOCK: appended verbatim, ≥3/5 bars 1–4]

## Everything else: round 4 verbatim, imported not restated

Instrument, models, bars, seeds, gates, demotion rule, noiv ship-gate, non-finite rule, slicing
semantics, and discipline are **big5_n_matrix_prereg.md §§ Instrument/Bars/Demotion/Battery
verbatim**, executed by the same machinery (fec/b5_n_matrix.py) via the thin runner
fec/b5_n2_matrix.py (same commit as this lock), whose only deltas are: PREREG = THIS file;
PIN = the fresh fingerprints above; RESULT heading = `## RESULT-N2`. Five bars for pred_N
(supervised Empath text → reactivity_z): (1) own held-out r ≥ +0.15 on MEM_N; (2) exact perm-p
< .05 (K=5000, seed 20260708); (3) row-dominant vs O/C/E/ES criteria on MEM_N, own r > 0;
(4) column-specific strict vs all five §17 competitor models incl. pred_ES (full-MEM vectors
sliced to MEM_N; tie = FAIL); (5) gating FW partial r(pred_N, reactivity | gender, party,
log-turns, shrinkage-weight) ≥ +0.10 AND exact perm-p < .05 (K=5000, seed 20260710). In-process
battery (a)–(d) with THIS stratum; battery failure ⇒ RETIRE WITHOUT A LOOK again (recorded, no
consumption). Core-matrix NO-STATUS-CHANGE clause: reproduced §17 cells cannot promote or demote
any trait; an apparent A/ES pass in the reproduction is drift, not evidence.

## Pre-declared consequences (round 4 verbatim)

- PASS bars 1–5 → fresh-seed re-derivation (OOF seeds [101,113,127,139,151]) must re-clear ALL
  FIVE; failure = FRAGILE = MISS. On re-derived PASS: "text-N criterion-valid AND distinct
  against behavioral reactivity (MEM_N=[LOCK] stratum)" — methods §23, memory, ONE desk wording
  change on the N-slot line; NO engine change (RECEPT_N stays behavioral; a passing text-N is
  display-side corroboration only).
- MISS any bar: "text-N vs reactivity: not distinct — route CLOSED" (one look, no re-spec;
  closure covers this instrument class vs this criterion; a new construct needs its own prereg).
- Battery refusal: RETIRE WITHOUT A LOOK, successor condition = the same diagnostic at the
  then-current stratum (coverage keeps growing via weekly legs).

## Discipline

One look, same session as the lock. No LLM calls. No bar/seed/roster/spec changes after lock.
The RESULT-N2 section appends verbatim (MISSes included), committed same session.
