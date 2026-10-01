# Big-5 Round 4 Pre-Registration — open-vocabulary Blue + latent Pink halo overlay
**Locked: 2026-07-07 (late), user directive "make the necessary changes for both Blue and Pink",
BEFORE any embedding is computed or any model is fit. New designs → new bars (rounds 1-3 exhausted
the closed-vocabulary lexical family and the lexical-Blue CT-CM; both failures LICENSE these new
designs under the standing rule "iteration across rounds is legitimate").**

Frozen inputs: the post-gate corpus (social_media.db CREC+INTERVIEW, posts=social), behavioral
dispositions (behavioral_dispositions.json), the shipped pink artifact (big5_llm_opus.json raw_z),
behavior_panel (votes_cast), lep_criterion (follow-through). Baselines to beat: lexical Blue v2 on
the doubled corpus = held-out r A +.149, C +.273, E +.521 (genre/volume-inflated), O +.213, and
family-MTMM FAILS (same-trait cross-genre < cross-trait within-genre). CT-CM with lexical Blue was
boundary-degenerate (blue A/C/O collinear → factors unidentified).

## BEMB — Blue rebuilt on OPEN-vocabulary embeddings
**Design principle:** closed-vocabulary (hand-picked lexicon / word-rate) features hit a published
ceiling (Koutsoumpis ~.08-.14) and cannot carry genre-stable multi-trait structure (3 bases failed
MTMM). Open-vocabulary embeddings capture semantic content, published ceiling ~.30-.40, and are the
one basis with a real chance at MTMM. Feature = per-member document embedding, computed PER GENRE
and standardized WITHIN genre (genre-controlled by construction), token-weighted averaged across
genres, then ridge-fit to the behavioral targets (A<-cooperation, C<-diligence, E<-visibility,
O<-breadth), same nested 5-fold as v2. Independence intact: fit to BEHAVIORAL targets, never to pink.

**Candidate bases (explored on the SELECTION half ONLY):** any of — LSA (TF-IDF word+char ->
TruncatedSVD at K in {128,256,512}); a local sentence-transformer (mean-pool over chunks, and a
volume-controlled variant that residualizes the embedding on log(tokens) to kill the E-volume
common-source). No pink data at any step.
**No-peek split:** SELECTION = even md5(member); TEST = odd md5(member). On SELECTION only, pick the
single base maximizing [mean held-out r over A/C/O] among bases whose family-MTMM same>cross on the
SELECTION half; if NONE pass MTMM on selection, the base with the highest MTMM margin is chosen and
BEMB is expected to MISS on test (reported honestly). Deterministic argmax; ties -> fewer dims -> name.

**TEST bars (ONE look on the TEST half, all must hold to PROMOTE):**
- family-MTMM mean same-trait cross-genre **> 1.15x** mean cross-trait within-genre (the wall every
  lexical basis failed; the 1.15x margin guards against a coin-flip pass)
- held-out r: A >= **+0.14**, C >= **+0.20**, O >= **+0.18** (no material regression vs v2 shipped)
- E >= **+0.20** AND the volume-controlled variant's E within 0.05 of the raw variant's E (i.e. E is
  not merely text-volume; if E collapses under volume control, E is documented as genre-bound, and
  the A/C/O+MTMM promotion can still stand with E carried from v2)
**Promote on PASS:** BEMB becomes big5_blue_emb.json; make_member_desk's blue radar + agreement
zones switch to it (display only — Blue feeds NO rank/engine, verified 2026-07-07); v2 retained as
the fallback + on-disk record. **On MISS:** lexical v2 stands; BEMB documented; blue lever closed.

## CTCM2 — Pink A-ES halo latent overlay, with the improved Blue as the third indicator
**Design principle:** the audit + rounds 2/7 proved pink's A-ES halo is text-tone that scoring/judge
arithmetic cannot separate from C's signal. A CT-CM latent model can absorb the judge halo into an
orthogonal PINK METHOD factor WITHOUT recalibrating any instrument — but tonight it was
under-identified because lexical Blue's traits were collinear. A better (embedding) Blue provides
the independent third indicator the model needs. Instruments' own scores are UNTOUCHED (independence
prohibition intact); the latent is a THIRD artifact (overlay), never a replacement.
**Runs only if BEMB is built (pass OR miss — a non-collinear Blue may identify the model even if it
misses its own promotion bars); the Blue indicator = the best available (BEMB winner, else v2).**
**Bars (ONE look, all must hold to SHIP the overlay):**
- latent A-ES |r| <= **0.50** (RKH-anchored: population truth .443)
- latent C vs votes_cast Spearman >= **+0.15** (must not lose the earned criterion)
- latent discriminant mean off-diag |r| <= **0.30**
- no Heywood case (no negative variance), all on-trait loadings positive, model converges clean
**Ship on PASS:** big5_latent.json (desk overlay) + a new audit guard. **On MISS:** documented; the
psychology stack's terminus is the P6+retest gains + the RKH-anchored halo caveat, unchanged.

## Standing rules
One look per test on its TEST partition; misses revert; bars never move after data is seen;
blue-on-pink calibration PROHIBITED. Every claimed PASS is adversarially re-verified (independent
re-derivation) before promotion — the P6 lesson (a pass that was a metric artifact) is now doctrine.
