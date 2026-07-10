# Round-5 successor-gate diagnostic record — 2026-07-09/10 session (SYNTHETIC ONLY, NO LOOK)

Machinery: fec/b5_a_stratum_diag.py (@e142de0 serial, @4d11a5b parallel — numerics identical).
The big5_a_matrix_prereg.md Addendum-1 diagnostic (NM.plant_set orthogonalized constructor, true
r=.40 plants, bars 1-4, actual MEM_A stratum), parameterized by feature basis. No real trait x
criterion pairing was computed at any point; coop_v2_candidate.json was read ONLY for its
coverage mask. Roster at every run: MEM=456, MEM_A=290 — EXACT match to the Addendum-1 lock.
Successor-gate bar (pinned in Addendum 1): >=3/5 on bars 1-4.

Selection-effect guard (pinned in-script BEFORE any sweep): bases screened on the five PINNED
Addendum seeds (424242/515151/616161/717171/818181); any basis clearing >=3/5 must CONFIRM >=3/5
on five FRESH seeds (131313/272727/393939/515253/676767) never used for selection.

Embedding bases rebuilt fresh on the post-expansion corpus (interviews 3.8x'd 07-09, after the
07-07 BEMB cache): b5_emb_cache_r6_lsa.npz + b5_emb_cache_r6_st.npz (533 members, 1130
member-genre docs; b5_emb_build.py recipe verbatim; 07-07 cache untouched). Member matrices =
within-genre z + token-weighted cross-genre average (b5_round4_eval composition verbatim).

## Selection stage (PIN5), per-seed own r (bars1-4 pass marked *)

| basis          | 424242  | 515151  | 616161  | 717171  | 818181  | median | b1-4 | gate |
|----------------|---------|---------|---------|---------|---------|--------|------|------|
| empath         | +0.105  | +0.119  | +0.132  | +0.190  | +0.251  | +0.132 | 2/5  | refused — EXACT Addendum-1 reproduction |
| lsa128         |         |         |         |         |         | +0.112 | 1/5  | refused |
| lsa256         | +0.109  | +0.209* | +0.075  | +0.153* | +0.195* | +0.153 | 3/5  | cleared |
| lsa512         |         |         |         |         |         | +0.098 | 1/5  | refused |
| st_mean        | +0.312* | +0.250* | +0.162* | +0.132  | +0.236* | +0.236 | 4/5  | cleared |
| st_volctrl     | +0.270* | +0.243* | +0.176  | +0.152* | +0.238* | +0.238 | 4/5  | cleared (b1-2 5/5; 616161 col fail only) |
| empath+lsa256  | +0.205* | +0.120  | +0.217* | +0.064  | +0.212* | +0.205 | 3/5  | cleared |

(empath per-seed row quoted from the Addendum-1 record; lsa128/lsa512 per-seed detail in the
session scratchpad JSONs — both uniformly weak, medians as shown.)

## Confirmation stage (FRESH5), per-seed own r

| basis          | 131313  | 272727  | 393939  | 515253  | 676767  | median | b1-4 | verdict |
|----------------|---------|---------|---------|---------|---------|--------|------|---------|
| st_mean        | +0.290* | +0.129  | +0.192* | +0.293* | +0.131  | +0.192 | 3/5  | **CONFIRMED** |
| st_volctrl     | +0.279* | +0.130  | +0.194* | +0.269* | +0.125  | +0.194 | 3/5  | **CONFIRMED** |
| empath+lsa256  | +0.225* | +0.110  | +0.239* | +0.096  | +0.228* | +0.178 | 3/5  | **CONFIRMED** |
| lsa256         | +0.045  | +0.021  | +0.071  | +0.094  | +0.228* | +0.071 | 1/5  | REFUTED — selection artifact; the guard bound |

## Findings

1. **The round-5 refusal was Empath-specific, not stratum-intrinsic.** On the same 290 members,
   the same constructor, and the same bars, MiniLM semantic embeddings recover planted true r=.40
   at roughly twice Empath's level (fresh medians +0.192/+0.194 vs +0.132).
2. **Volume does not carry the recovery**: st_volctrl (each embedding dim residualized on
   log-tokens within genre) confirms with a fresh profile nearly identical to st_mean.
3. **LSA is draw-fragile at n=290**: lsa256 cleared selection then collapsed to 1/5 on fresh
   seeds; 128/512 never cleared. Open-vocab is not sufficient — transformer semantics are what
   see this stratum.
4. **The Addendum-1 successor condition (>=3/5 bars 1-4) is MET by a new instrument basis**, with
   the honest caveat that the pinned successor clause contemplated the SAME (Empath) instrument
   passing via data growth; a new instrument requires its own prereg + adversarial review
   (instrument-of-record language in the round-5 lock). Draft staged in session scratchpad
   (big5_a_matrix2_prereg_DRAFT.md); proposed instrument = st_mean, with st_volctrl as the
   robustness record and the 07-07 BEMB display-closure explicitly distinguished.
5. **Discipline: nothing was looked at.** No real pairing computed, no status change, no prereg
   locked. Next step is USER-GATED: Paul authorizes (or declines) a round-6 lock.
