# PRE-REGISTRATION — Nomological (label-free) validation of trait instruments
**Locked 2026-07-04, BEFORE any trait×behavior correlation was computed.**
Framework: ValiTex Phase III external evidence (criterion prediction V.6) replacing human annotation
(III.1), per Birkenmaier/Lechner/Wagner 2024; predictions from the RKH congressional findings,
Judge et al. 2002 leadership meta-analysis, Dietrich 2012 / Dynes 2019 elite studies, and the
Abele/Trapnell-Paulhus agency-communion literature. Effect-size priors per Funder & Ozer 2019
(single elite trait→behavior links expected |r| ≈ .10–.25; judge the PATTERN, not lone coefficients).

## Instruments under test (all scored before this file; frozen)
L = lexical Big5 (big5_traits.json, production) · G = genre-general composite (scratchpad, 259 members)
P = persona agency/communion (agency_communion.json, n≥15) · X = interaction features (exploratory)

## Criteria (behavior_panel.json, assembled before this file; frozen)
**PRIMARY (channel-separated — non-text behavior; carries the verdict):**
bipartisanship, cosponsor_degree, n_cosponsored, n_sponsored, votes_cast, committee_leader
**SECONDARY (text-channel CONTAMINATED — the traits are estimated from speech/interview/social text,
so these share a generative source; reported but excluded from the pass/fail verdict):**
n_floor_speeches, floor_words, n_interviews, n_interview_programs, n_tweets
Transforms: count criteria log1p then z WITHIN CHAMBER; bipartisanship raw; committee_leader binary
(point-biserial). Covariate variants (specification curve, all reported): (a) raw, (b) partial on
nominate_extremity, (c) within-party (D and R separately, averaged).

## Directional hypotheses — PRIMARY family (one-tailed; BH-FDR α=.05 within family)
| # | Trait | Criterion | Sign | Precedent |
|---|---|---|---|---|
| 1 | A (L,G) | bipartisanship | + | STRONG (RKH H5) |
| 2 | A (L,G) | cosponsor_degree | + | MEDIUM |
| 3 | A (L,G) | n_cosponsored | + | MEDIUM |
| 4 | C (L,G) | votes_cast | + | STRONG (RKH absenteeism −) |
| 5 | C (L,G) | committee_leader | + | MEDIUM-STRONG (RKH book) |
| 6 | C (L,G) | n_sponsored | + | STRONG (RKH: largest sponsorship effect) |
| 7 | E (L,G) | n_sponsored | + | STRONG (RKH H1) |
| 8 | ES (L,G) | n_sponsored | + | STRONG (RKH H2) |
| 9 | Agency (P) | committee_leader | + | STRONG (agency→status attainment) |
| 10 | Agency (P) | n_sponsored | + | MEDIUM |
| 11 | Communion (P) | bipartisanship | + | STRONG (communion→cooperation) |
| 12 | Communion (P) | cosponsor_degree | + | MEDIUM-STRONG (network embedding) |
| 13 | Communion (P) | n_cosponsored | + | MEDIUM |

## Discriminant requirements (Campbell-Fiske; required for PASS)
D1: Agency predicts committee_leader MORE than Communion does (r_Agency > r_Communion on that criterion).
D2: Communion predicts bipartisanship MORE than Agency does.
D3: The five Big5 traits show differentiated criterion profiles (not one general factor pattern).

## SECONDARY (contaminated) family — reported descriptively only
E→n_interviews +, E→n_tweets +, E→n_floor_speeches +, Agency→n_interviews +, X:wpt_mean→n_interviews +.
O predictions: low-prior/exploratory only (weakest trait; RKH found cosponsorship null).

## Decision rule (locked)
PASS for an instrument: ≥70% of its PRIMARY directional tests correct in sign AND the STRONG-precedent
subset individually r ≥ +.08 with BH-FDR q<.05 AND discriminant requirements hold AND effects do not
invert across the three specification variants.
INDICTED: STRONG-precedent links null/reversed in the least-constrained subsample, or discriminant
collapse (agency≈communion profiles), or effects exist only on contaminated criteria.
EXCUSABLE nulls (do not indict): O anywhere; leadership among junior members; effects inside safe-seat
subsample; any single |r|<.10 when the family pattern holds.
Pattern statistic: r_alerting (correlation between predicted and observed r-vectors) reported per
instrument alongside the hit count.
