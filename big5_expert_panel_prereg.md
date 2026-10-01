# Multi-rater expert gold panel — the independent-TRAIT anchor (pre-registration)

**STATUS: CANCELED (user decision 2026-07-09 — "We aren't doing this actually, let us just augment
what we have"). No raters will be recruited; the A- grade STANDS as final absent this anchor. The
infrastructure (items/build/scorer/rater HTML) is retained committed and dormant — if the panel is
ever revived, re-open this prereg, finalize rater count, and replace this line with 'STATUS: LOCKED'.
The scorer hard-refuses THE LOOK while not locked, so the dormant state is safe. Drafted 2026-07-09.**

## Why this exists (the A-path)
The formal re-grade (2026-07-09, 32-agent judge panel) ratified **A-** and was explicit: the ONLY path
to A is an **independent-TRAIT anchor** — a multi-rater human observer panel that separates trait
variance from genre/method variance. Text-vs-text comparisons cannot do it (method-shared); behavioral
criteria are criteria, not trait comparators (CMC ruling, big5_methods §13); eleven pre-registered
design families already missed the discriminant bar without new data. This panel is that data.

## Materials (built, gitignored)
- **98 de-identified packets, 77 members** (`expert_panel_rater.html`, packets embedded; sealed key
  `panel_key.json` raters never see). Stratified party x chamber x visibility tertile (12 strata,
  seed 20260709). Primary genre INTERVIEW (~840 words: 2 excerpts, different programs, temporal
  spread); 21-25 members also carry a CREC packet (cross-genre diagnostic).
- De-identification: names/titles/party/states (big5_llm.py scrubber) + demonyms + district ordinals;
  leak scan over all packets = 0 name/state/party hits. Residual risk = content-based recognition,
  handled by the per-packet **recognition probe** (see exclusions).
- **Items: BFI-2-XS, observer-adapted** (Soto & John 2017, JRP 68:69-81; 15 items, 3/domain, 1-5
  Likert). **Item text VERIFIED VERBATIM** vs the published Appendix + the Colby bfi2xs-form.pdf
  (research workflow wu6cbr5od, verdict CONFIRMED); the verify pass caught and fixed one drafting
  error (item 8 = "Has difficulty getting started on tasks.", reverse-keyed). Six reverse-keyed
  items (1,3,7,8,10,14 = E1/C1/A2/C3/O2/N3). Panel Negative-Emotionality is sign-flipped to ES.
  **Disclosed adaptation:** the published stem is self-report ("I am someone who..."); we use the
  standard informant-form third-person stem ("This person is someone who..."). The BFI-2 informant
  form exists (Colby lab); our stem follows that convention.

## Raters (Paul's step — the only human input)
**5 raters RECOMMENDED (3 = hard minimum)** — stranger-rating norms warn single-rater text-based
reliability is low (ICC ~.2-.5 by trait), so k=3 may miss the .60 floor on the harder traits (N/ES
especially); k=5 buys the aggregation margin (Spearman-Brown). Politically literate adults,
independent (no discussion until all exports are in),
each rates ALL packets blind (~4-5 min/packet ≈ 6-9 hrs; splittable across sittings, autosaves).
Raters must not be project members and must not look anyone up. Deliverable per rater: the JSON export.
Compensation/recruiting is Paul's domain (~$20-25/hr market rate if paid).

## Analysis plan
**Pre-look (allowed anytime — about the panel, not the instruments):** per-trait inter-rater
reliability on INTERVIEW packets, recognition-excluded: ICC(2,k) (Shrout-Fleiss) + Krippendorff
alpha (interval). **Floor: ICC(2,k) >= .60** (below -> that trait DROPS from the A-case; it cannot
anchor anything). Target .72 (the B&L trained-coder ceiling on an easier task). Machinery validated
by synthetic selftest (planted: ICC .86/diag .91; null: ICC -.08/diag +.01 — no false pass).

**Exclusions (locked):** any (rater, packet) where the recognition probe names the true member ->
excluded from primary (sensitivity analysis with inclusion reported). Packets with <2 clean raters drop.

**THE LOOK (one look, gated by the scorer):** consensus = mean across clean raters per member-trait.
5x5 Campbell-Fiske matrix corr(instrument trait_i, panel trait_j):
- **PRIMARY instrument: Pink LLM item-read** (big5_llm_opus raw_z; the five-trait item instrument,
  461-member coverage, the one whose MTMM .41 carried the external grade). big5_v2 = SECONDARY
  (reported in full, not gating — its traits are criterion-fit, so panel convergence is expected
  but non-adjudicating).
- **Per-trait PASS bars (locked):** validity diagonal r >= **+0.30**, one-sided p < .05, AND full
  Campbell-Fiske dominance (diagonal exceeds every heterotrait cell in its ROW and COLUMN).
- **A-case verdict: >= 4/5 traits PASS on the primary instrument** (with those traits' panel
  reliability >= floor). 3/5 = partial anchor (report; grade likely stays A-). <=2/5 = the anchor
  refutes the instrument's trait structure (grade RE-OPENS downward — accepted risk, stated now).
- **Reported diagnostics (non-gating):** panel heterotrait A-ES r (>= .5 -> the text .65 halo is
  partly REAL trait covariance; <= .3 -> method halo); human cross-genre consistency on the CREC
  subsample (if HUMANS fail cross-genre too, public personas are genre-bound at the construct level
  and the lexical MTMM 'failure' was partly construct, not instrument).

**Power:** n=77 members -> r_crit(.05, one-sided) ~= .19; ~80% power for r >= .28. The +.30 bar is
detectable. Paul may raise n (325 eligible) BEFORE lock; never after.

## Honest expectations (stated before any rating exists)
Stranger observer ratings from text are hard (Connelly & Ones 2010: acquaintance drives accuracy).
Real possibilities: (a) panel fails reliability on some traits (likely N/ES from text alone) -> those
traits drop and the A-case narrows; (b) panel reliable but instrument convergence < +.30 -> the A is
unreachable by this route and A- STANDS as final; (c) panel replicates the A-ES halo -> halo partly
real. A PASS is NOT presumed. One look; misses documented; bars never move after data exists.

## Machinery-only pilots (explicitly NOT the anchor)
LLM raters share the method family with Pink and CANNOT count toward the anchor. A small Haiku-rater
pilot is permitted SOLELY to check packet rateability (do packets carry enough signal for ANY rater
to agree on) and interface/scoring plumbing, on a subsample, before human hours are spent. Its
numbers are quarantined from all validity claims.

## Run recipe
1. Verify items verbatim -> set PROVISIONAL_TEXT=False (research workflow output).
2. Paul finalizes n / raters -> replace STATUS line with 'STATUS: LOCKED' + commit.
3. Send each rater `expert_panel_rater.html` (one file; works offline in any browser).
4. Collect `panel_ratings_<ID>.json` exports into the repo root.
5. `python fec/members/b5_panel_score.py` (reliability report, safe anytime).
6. `python fec/members/b5_panel_score.py --look` = THE ONE LOOK. Record results + 'LOOK TAKEN' here.
7. If A-case passes -> re-run the judge-panel re-grade workflow with the panel result added.
