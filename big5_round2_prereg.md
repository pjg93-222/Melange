# Big-5 Blue Instrument — Round 2 Pre-Registration (composed residualized family)
**Locked: 2026-07-07, user GO ("Go ahead with round-2 psychology"), BEFORE the composed
configuration is evaluated.**

## What round 1 already established (NOT re-tested; these numbers are OBSERVED, not bars)
The B5 look (big5_methods.md §6) measured, with honest nested 5-fold CV on the frozen snapshot:
residualized A +0.181 / C +0.224 / O +0.228 (all above their round-1 bars) while E collapsed to
−0.033 (v2's E was genre variance) and the FULL family MTMM (including E) failed (.096 vs .383).

## The round-2 configuration (R2)
Blue = ridge fits for **A, C, O on genre-residualized features** (residualize each of the 31
features on [share_CREC, share_INTERVIEW, share_social, log tokens], the round-1 method,
unchanged) + **E kept exactly as v2** (raw features; explicitly labeled genre-bound on the desk)
+ ES carried as v2 does today. Same targets, same nested CV, same seed, same alpha grid.
Instrument independence preserved: residualization uses ONLY genre covariates — never pink.

## Bars (ONE look, all on quantities round 1 did NOT measure)
- **R2-1 discriminant:** mean off-diagonal |r| among the composed member scores {A, C, E, O}
  <= **0.30** (the standing discriminant bar).
- **R2-2 known-groups:** party signs correct on >= **3 of 4** of {O−, C+, E−, A−}.
- **R2-3 A/C/O-subfamily MTMM:** mean same-trait cross-genre r among the three RESIDUALIZED
  traits (3 genre pairs x 3 traits, refit weights applied to per-genre featz) **exceeds** the
  mean cross-trait within-genre |r| among those same three traits. This is the construct claim
  being promoted ("A/C/O are genre-clean"); E is excluded from this bar by construction and its
  genre-boundness is documented, not hidden.

## Promotion on PASS (all three bars)
big5_lexcal_v2.py gains the residualization step for A/C/O only; big5_v2.json regenerates;
desk rebuilds (blue radar changes for A/C/O); audit + kernel; commit. Desk documentation notes
E = genre-bound display signal. On any MISS: current v2 stands, result documented in
big5_methods.md, no post-hoc adjustment.

## Out of scope
Reliability (split-half) for the residualized family: no chunk-level lexical data exists without
a corpus re-featurization; declared out of scope for this round rather than improvised.
PROHIBITED (standing): calibrating blue against pink in any form.
