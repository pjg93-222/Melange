# PERSONALITY & INCENTIVE RECEPTIVITY LAYER — 2026-07-02

> **ADDENDUM (same day) — TRANSCRIPT CORPUS + STANCE GATE.**
> 1. **The trait corpus is now the papers' native medium**: `fec/fetch_congressional_record.py`
>    pulls CREC floor speeches (16,088 attributed turns, 500 members) + CHRG finance-hearing
>    transcripts (2,379 Q&A turns, 132 members) = **6.6M words**, 2025-07→2026-06. Median tokens
>    per member: **735 → 5,575**; low-confidence members: **391 → 75**. Traps found & handled:
>    GovInfo's API lists by last-*modified* (it once fed us the 1995 Record — now keyless,
>    date-generated package IDs with hard bounds); hearing prints use mixed-case speakers; witness
>    surname collisions (Gov. Michael Barr vs Rep. Andy Barr) are excluded via STATEMENT OF headers.
>    RTs and URLs scrubbed from the corpus; chamber ritual boilerplate stripped.
> 2. **Validation (Ramey Table-1 style, traits vs party)**: ES +0.43 ✓, C +0.11 ✓, E −0.10 ✓,
>    A ≈ 0 (null — Ramey's weakest too), **O +0.33 REVERSED** — the compact O proxy reads formal
>    register, which skews R in this Congress. O is flagged low-validity; its only engine role is a
>    0.06 weight inside seed_prob. We do NOT tune weights to force validation signs.
> 3. **Stance-graded contingency gate** (user-directed): the lobbying take-rate falls down the
>    ladder — allies ungated (core seeds), HP 1.00, TN 0.90, '—' 0.85, LS 0.75, Skeptic 0.55,
>    Opponent 0.35 — × personality seed_prob, floor 0.15, per topic, in frontier + coalition.
> 4. The contest partisan-balance audit was redesigned to test what matters: **gate parity**
>    (mean D-vs-R contest gate gap = 0.002, threshold 0.10) + pool balance, with the entry-mix
>    proportion enforced only at n≥12 (one seed = 12.5pp at n=8). **Audit: 50/50 CLEAN.**
> GovInfo key: `fec/govinfo_key.txt`. Rerun cadence: `fetch_congressional_record.py crec` weekly
> (resumable; non-session days cached), then `big5_traits.py` → pipeline.

Seven-paper augmentation: who is receptive to lobbying, who chokes under pressure, who has nothing
to lose, and how prospect theory frames their choices — wired into every influence engine.

## Paper → mechanism map

| Paper | What it contributes | Where it lives |
|---|---|---|
| Ramey, Klingler & Hollibaugh (PSRM 2016) *Measuring Elite Personality Using Speech* | The measurement pipeline, copied step for step: aggregate a member's text → standardized closed-vocabulary (LIWC/MRC-style) category rates → standardized linear trait model → Big Five z-scores **relative to this corpus**; confidence degrades below ~1k words | `fec/members/big5_traits.py` → `big5_traits.json` |
| Birkenmaier & Lechner (Pol. Analysis 2025) *Measuring Politicians' Public Personality* | Validates text-cue-based trait measurement at scale; the scores are the **public persona** — which is exactly the surface lobbying interacts with | Design justification; social posts as trait corpus |
| Byrne, Silasi-Mansat & Worthy (PAID 2015) *Who chokes under pressure?* | The susceptibility framework (user: "very agreeable, or submissive to authority, should be very susceptible"): SUSC = .40·A + .30·N − .20·C − .10·E | `receptivity_layer.py` → `susc_mult` (pressure), `edge_mult` (cascade receiver) |
| Fouirnaies & Hall *How Do Electoral Incentives Affect Legislator Behavior?* | Final-term members without a reelection incentive are systematically less responsive — "nothing to lose politically" → incent_mult 0.60 (retiring) / 0.85–1.15 (safety gradient) | `incent_mult`; hook file `fec/retiring_members.txt` (populate as retirements are announced) |
| Linde & Vis (Pol. Psych 2016) *Do Politicians Take Risks Like the Rest of Us?* | MPs obey prospect theory: risk-seeking in the LOSS domain, risk-averse in GAINS, loss-averse overall → pt_mult 1.15 (live race) / 0.92 (safe); LOSSFRAME 1.10 (a competitor threat moves lean more than an equal CU gift; K&T λ attenuated to elite scale per their findings) | `pt_domain`, `pt_mult`; `LOSSFRAME` in money_response |
| Chen et al. (ICML 2021) + Zareie & Sakellariou (SNAM 2023) behaviour-aware IM survey | **Contingency-aware seeding**: legislators know they're being lobbied — a contacted seed activates only with probability seed_prob = 0.60 + .10·A + .06·O + .04·E ∈ [0.30, 0.90]; committed allies are never gated (already active, not lobbied). Node behavior (BV) belongs in the diffusion model, not just topology | seed gating in `budget_frontier.py` + `per_topic_coalition.py` (dedicated CRN stream — no RNG desync) |

## The composite

`pressure_mult = clip(susc_mult × incent_mult × pt_mult, 0.50, 1.60)` — one number for "how hard
does pressure land on this member," consumed by:

- **money_response.shift_lean** — donations/threats move lean ×pressure_mult; threats additionally
  ×LOSSFRAME. Defection thresholds unchanged; who crosses them now depends on personality+incentive.
- **flip_model / per_topic_flip pflip** — the money-pull terms scale with pressure_mult (peer-channel
  susceptibility is handled by edge_mult inside the cascades, not double-counted here).
- **salience_shock steps_for** — going-public shocks move susceptible members more (multiplies the
  existing Noble A.4 electoral-gamble term).
- **cascades (frontier / coalition / salience)** — edge probability into a receiver scales with
  edge_mult (behaviour-aware diffusion).

## Measurement honesty

- Trait corpus: 509/533 members have text (median 735 tokens — tweet corpora are thin vs Ramey's
  11k words/yr). Uncertainty is handled by **graded shrinkage** (z × √(tokens/1500), capped at 1):
  thin-corpus members drift toward neutral multipliers instead of getting an invented personality.
- Face validity checks out (high-C: Steil/Feenstra; low-C: Paul/Cruz; pressure-resistant:
  Jayapal/Goldman; susceptible: Kennedy/Kim). Formal validation (Ramey does ideology correlations)
  is a follow-up once more text accumulates.
- The scores are corpus-relative z-scores — comparable within this member set only.
- All engine wiring degrades to EXACT legacy behavior if `member_receptivity.json` is absent or
  `RECEPT_LAYER=0`. Constants are env-dialable (`LOSSFRAME`, `LOWCONF_TOKENS`).

## Current landscape (first build)

- PT domains: 259 loss / 274 gain. Retiring: 0 (hook file empty — populate it).
- pressure_mult median 0.97, range [0.72, 1.45]. Most susceptible: Andy Kim 1.45, Cortez Masto
  1.40, Warnock 1.39, Levin 1.38, Kennedy 1.36. Most resistant: Goldman 0.73, Jayapal 0.74,
  Evans 0.75, Sylvia Garcia 0.77, Clarke 0.77.
- seed_prob median 0.59, range [0.39, 0.89] — the frontier's greedy now natively prefers members
  who will actually take the meeting (contingency-aware objective).

## What does NOT change

The workbook rank is untouched — this layer lives entirely in the influence engines (allocations,
frontiers, cascades, advisories). `big5_traits.py` is corpus-driven and run manually when the tweet
corpus refreshes; `receptivity_layer.py` is in the canonical `run_pipeline.py` chain.
