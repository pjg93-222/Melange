# OVERNIGHT DEEP AUDIT — 2026-07-02 (brutal, as ordered)

**Bottom line:** the math is right, the blend is exact, the pipeline is deterministic — but the audit
found one CRITICAL silent data loss (now fixed), one CRITICAL train/test leak (quantified; your real
accuracy is *better* than reported), and three judgment calls in the social blend that are yours to
make, shipped as default-off dials. Everything fixed tonight is listed with how to revert it.

---

## SEV-1: CRITICAL — found and FIXED tonight

### 1. The 18th category (CU Tax Status) silently fell out of the model
- `category_stance.json` was extended to 18 categories by hand on 07-01, but the *producer*
  (`per_category_stance.py`) still had a hard-coded 17-category list. Tonight's regeneration
  clobbered the file back to 17 — the stance matrix, flip model, cascade, and salience advisory all
  lost your weight-3.0 flagship category while the ABB26 IMP dicts kept expecting it.
- The only reason it was caught: the audit's `>=18` count check failed. That check is now the
  guardrail it was accidentally proven to be.
- **Fix:** `('CU Tax Status', 16)` added to the producer list (Normalized col 16; 190 press rows +
  social data now flow). Full pipeline regenerated on 18 categories.
- **Your call standing:** CU Tax Status is scored with *offensive* weights (0.55/0.35/0.10). It is a
  defend-type fight — moving it into the DEFENSIVE set changes weighting and is your domain.

### 2. Train/test leak in the stance classifier — 4 text-hash collisions
- Two ACU articles were filed under multiple members and straddle the split ("Don't Tax My Credit
  Union postcards" rows 109/75; "Simpson overdraft" rows 215/345/214). Same text, both sides of the
  fence.
- **Leak-free re-test: 84.7% / 0.816 macro-F1 — your headline number IMPROVES when the leak is
  removed** (the leaked rows were being scored *against* the classifier due to conflicting labels:
  identical Booker=support vs Warren=neutral inputs are also training noise).
- Your split itself was never touched (standing rule). Permanent audit check installed:
  `train/test split-leak within known bound (≤4)` — it will scream if a future label refresh adds
  more.
- **Next label refresh rule (recommendation):** same text ⇒ same split.

### 3. AUG network file carried 41 duplicate edge pairs (inherited wart)
- The 41 reverse-dup asymmetric pairs in the original cosponsor xlsx were reproduced verbatim into
  the AUG file. Loaders mean-symmetrize on read, so *live math was never wrong* — but the artifact
  at rest was dirty and any future non-symmetrizing consumer would inherit it.
- **Fix:** builder now symmetrizes at rest; rebuilt as `congress_cosponsor_network_AUG20260702.xlsx`;
  adjacency equivalence vs the old file proven (0 diffs) before deleting the 0701 file.

---

## SEV-2: JUDGMENT CALLS — dials built, DEFAULT OFF, you decide

### 4. Thin-category amplification (6 categories)
In categories where almost nobody tweets, one post is worth a lot: CU Capital Requirements has ONE
member with social signal — that single post moves ~5 units of media pillar; Defense CU Issues,
15.3 units. The p80 scaling that makes 50/50 fair in thick categories overpays in thin ones.
- **Dial:** `SOCIAL_SHRINK=1` → in categories with <15 members carrying signal, social share shrinks
  by nz/15 and press absorbs the remainder. *(Declared in `build_media_blend.py`; wiring lands with
  your go-ahead — flipping it on is a one-line aggregation change + re-blend.)*

### 5. Retweets count at full stance weight (1,444 RT rows)
An RT is amplification, not authorship — defensible per Fink, but a hostile-quote-RT scores exactly
wrong. - **Dial:** `RT_W=<0..1>` (same status as above; you pick the discount, e.g. 0.5).

### 6. Pos-max squash in 3 normalized columns
Technology & Emerging, Fraud Prevention, and CU Tax Status each have one loud member whose max
compresses everyone else's normalized score toward zero. This is the workbook's own pos/neg-max
normalization doing what it always did — the media blend just made it visible. Changing the
normalization is a formula-design decision = yours.

### 7. Keyword category routing has known noise
"charter" catches charter schools, "housing" catches all housing politics, `\bai\b` is broad.
Acceptable for a signed sum; not a supervised classifier. Upgrade path exists (route through the
stance classifier's category head) if you want it.

---

## SEV-3: RISKS ON RECORD (no action tonight)

- **Tweet-domain accuracy is UNKNOWN** until you adjudicate `tweet_gold_queue.csv` (400 rows). The
  71% tier-consistency proxy is the only current evidence. Related anchoring risk: 75% of queue
  labels equal the API pre-seed — recommend adjudicating the raw-text subset first.
- **`press_raw_original.json` cache trap:** if the R pipeline refreshes press data, rebuild the cache
  from the new raw BEFORE re-blending, or the blend resurrects stale press numbers.
- **`build_social_master.py` imports `process_quorum`** → re-runs the whole Quorum pipeline as an
  import side effect. Refactor candidate: shared CU_TERMS module.
- The Anthropic API key pasted in chat earlier is a live secret — **rotate it**.

---

## VERIFIED EXACT (the boring good news)
- Every blended cell matches independent recomputation exactly (0 mismatches).
- Rank & Allocation SUMPRODUCT spot-checks: 0 mismatches.
- Frontier fully deterministic on the augmented graph (identical hashes, two runs).
- SQLite integrity ok; 0 orphan interactions; Quorum↔Social Master reconcile 9,559 = 9,559.
- Attribution spot-check 0/12 suspect. Regime probabilities all sum to 1.

## INFRASTRUCTURE SHIPPED TONIGHT
- **`fec/run_pipeline.py`** — canonical one-command runner (kills the forgotten---electoral-pass
  failure class). Salience advisory now INSIDE the chain before the bundle export.
- Audit grown to **47 checks** (18-category count guard + split-leak bound).

## RANK IMPACT OF THE TAX-STATUS FIX
**Zero.** All 533 members hold their exact ranks (Warren 146, Durbin 482, Marshall 531 — unchanged).
The workbook rank formula never lost the tax-status column (raw sheet + row-535 weight always fed the
pillar); what was lost and is now restored is the python side: stance matrix, flip model, cascade,
and salience advisory. The rankings you saw last night stand.

What the restored category now shows:
- **Stance matrix:** 43 members with tax-status signal — 8 Champions, 5 Allies, 10 Highly
  Persuadable, 9 True Neutral, 10 Lean Skeptic, 1 Opponent (490 no-signal).
- **Salience advisory:** CU Tax Status priced at value 14.75 (E_dspread +11.75, worst-regime −17.8,
  ψ=0.98 = high uncertainty ⇒ handle with care); defections prevented: **Mike Crapo, Scott
  Fitzgerald**.
- **Caveat:** the $ allocation frontier has NO tax sub-category — the flip model is bill-driven and
  no active bill maps to tax status. Money can't target it through the frontier until a bill exists;
  the advisory's defensive-appeal channel is the instrument that covers it. (The frontier's "17
  topics" vs the alloc's 18 is the pre-existing, deliberate exclusion of `CFPB Reach (-)` — benign.)

**Final state: pipeline regenerated end-to-end via `run_pipeline.py` in 4.5 min — audit 47/47 CLEAN.**

## YOUR QUEUE (unchanged)
tweet_gold_queue.csv (400) · 39 golden CFPB conflicts · 21 oppose candidates · unverified Bluesky
handles · X pay-per-use + TRUTH_TOKEN · Jayapal tier/rank mismatch · DEFENSIVE membership for CU Tax
Status · SOCIAL_SHRINK / RT_W decisions.
