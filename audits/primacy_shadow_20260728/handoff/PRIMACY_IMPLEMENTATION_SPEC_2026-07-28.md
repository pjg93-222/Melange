# Primacy tier — implementation specification
**2026-07-28 · Melange Systems · prepared for coding**
Supersedes `CHAMPION_GATES_RECOMMENDATION.md` and `GRIEVANCE_LAYER_DESIGN_2026-07-28.md` as the build target; both remain valid as background.

---

## 0. Status — full-authority reset, 2026-07-29

Paul's directive: *"the configuration has to be perfect — reset, look at all the materials."*
Done. The classifier was rebuilt as a **nine-level authority ladder** over every material provided,
in explicit precedence, every call carrying its authority and rationale in
`bill_beneficiary_tags.ndjson`:

| Level | Authority | Acts | Weight |
|---|---|---|---|
| L0 | Manual adjudications (4, each with cited grounds) | 4 | 1.5% |
| L1 | Registry `acu_position` = OPPOSE → act weight **−1.0** | 5 | 0.4% |
| L2 | Quorum export `Issues` (ACU's own taxonomy) | 9 | 3.1% |
| L3 | Operative text — amends FCUA / NCUA, or explicit CU title | 25 | 4.2% |
| L4 | Registry anchor in a CU-scoped category (scoping **derived from the outline itself**: a category is CU-scoped when ≥⅓ of its search identifiers name CU tokens — Exam & Supervision 40% in, Mortgage 31% out, no hand-picking) | 32 | 13.4% |
| L5 | Letter topic slug | 5 | 5.4% |
| L6 | Content rules: cross-industry families (Fair Access, Small LENDER…), CBDC→shared (consistent with the registry filing CBDC under Technology), crypto, bank-primary | ~91 | ~14% |
| L7 | Title rules (the original regexes, where they matched) | ~178 | ~38% |
| L8 | Pipeline `areas` assignment — **may only assert `shared`, never `cu_primary`** (see correction below) | 265 | 20.1% |
| L9 | Naked default | **0** | **0.0%** |

**Paul directive 2026-07-29 — ACU letters are their own class, weight 0.60 (calibrated).** Signing
an ACU-organised letter is direct credit-union advocacy, so letters are lifted out of `shared`
(0.50) — but the two large CDFI letters carry 121 and 104 member links, so at the full 1.0 they
behave like a broad participation bonus and displace CU-bill authors. Swept: **0.50 → Masto 16 /
Huizenga 14 (out); 0.60 → Masto 17 / Huizenga 12 (in), 6/7@12 and 7/7@18; 0.70 → Masto 20, 6/7@18;
1.00 → Masto 27, 5/7@12.** **0.60 is the optimum on both objectives simultaneously** and is the
shipped value. Authority level **L2:acu-letter**. This is the only part of the wider adjudication
adopted — see the rejection note below.

### The multiplicative form is correct — and here is the proof (2026-07-29)

An earlier draft of this spec claimed the primacy factor was "nearly decorative," on the strength of
a global variance decomposition (Leg% 97.3% of log-variance; Spearman vs a pure-Leg% board 0.9939).
**That conclusion was wrong, and the error is instructive enough to record.**

Global Spearman is the wrong statistic for a top-k selection problem. It is dominated by the ~500
members whose ordering nobody consumes — and among whom primacy genuinely cannot discriminate,
because their files are thin and undifferentiated. Measure the same two components *inside the
region that decides the board* and the picture inverts:

| Pool | Leg% sd | F sd | primacy share of log-variance |
|---|---|---|---|
| all 532 *(one member has Leg% = 0; log undefined, excluded)* | 0.2900 | 0.0420 | 0.6% |
| top 100 (contenders) | 0.0605 | 0.0496 | **61.5%** |
| top 40 | 0.0361 | 0.0632 | **86.6%** |
| **top 20 (selection region)** | **0.0435** | **0.0725** | **84.2%** |

The mechanism is saturation: **Leg% is a percentile, so it compresses at the ceiling** — the top 20
occupy 0.850–1.000 — while the primacy factor keeps its spread (0.531–0.850). Interquartile ranges
tell it plainly: across all 533, Leg% IQR 0.500 vs F IQR 0.020 (Leg% discriminates); inside the top
20, Leg% IQR 0.068 vs **F IQR 0.080 — F discriminates.** Multiplying a saturating selector by a
non-saturating one is exactly the right construction: Leg% decides *who is in contention*, primacy
decides *who wins among contenders*.

The board proves it directly. **Turn primacy off entirely and only 4 of 12 Tier-1 seats survive:**

| | Tier 1 hits on the named seven | Huizenga |
|---|---|---|
| pure Leg% (no primacy) | **2/7 @12, 3/7 @18** | 7 |
| shipped (primacy on) | **6/7 @12, 7/7 @18** | 12 |

Pure Leg% would seat Meuser, Roger Williams, Warren Davidson, Eleanor Norton, Lawler, Emmer,
Dwight Evans — a legislative-volume list. Primacy replaces 8 of the 12 with Padilla, Gonzalez,
Cramer, Tim Scott, Sherman, Vargas, Sullivan and Fitzgerald. **This is the single largest effect of
any mechanism in the framework.**

*(The additive percentile form — `w_L·Leg% + w_P·PERCENTRANK(F)`, the convention used by the overall
rank — was built and swept as a cross-check: at w_P 0.40 it reaches only 5/7@12, 6/7@18 and scores
worse on the objective. It is retained as `board_additive_ref.json`. The multiplicative form is
preferred on both grounds: it is the better selector in the saturation region, and it fits the
markers better.)*

**Fourth audit pass (2026-07-29):** roles census clean (sponsor/original/cosponsor only) · zero
duplicate member-act rows · pcts↔bundle membership exact (533=533, no silent drops) · 7 letters
confirmed in-universe · one misclassification fixed: **H.R.154 RESCUE Act for Black and Community
Banks** was `bank_primary` on a regex misfire — it is an MDI/CDFI community-development bill, now
`shared` (sub-threshold: board unchanged, invariants re-pass). Judgment flag for Paul: **H.R.7056
Community Bank Regulatory Tailoring Act sits at `cu_primary`** because the outline files it in
Exam & Supervision (a CU-scoped section) and ACU supports it — the framework's precedence produces
this, but the title argues `shared`; one row, Paul's call. Pending-device check: whether
`fetch_acu_letters.py`'s full snapshot contains more than the 7 letters the bundle carries.

**Second-pass corrections (2026-07-29), then a 13-invariant verification sweep — ALL PASS:**
(a) **OPPOSE position now inherits across congresses by title family** — 4 prior-congress CCCA acts
(H.R.8874/S.4674 c117, H.R.3881/S.1838 c118) were still scoring +0.5; now −1.0.
(b) **Amendments inherit their in-universe parent's class** (never `oppose`; CU operative text still
wins first) — 30 GENIUS-Act amendments fell from `shared` 0.5 to `crypto_primary` 0.15, deflating
Hagerty 9→14. (c) Verified invariants: universe conservation (614/614), zero naked defaults, area
authority can never assert cu_primary, all OPPOSE anchors and families negative, every Quorum
CU-issue bill cu_primary, determinism, gate integrity (531 eligible), shrink containment,
shared≈baseline (0.4999 — the neutral bucket cannot manufacture champions), zero rank delta,
and the board fixture below.

**Correction applied 2026-07-29 (first once-over).** L8 was initially allowed to assert `cu_primary` from the pipeline's `areas` tag. That is **circular**: the universe was collected *by* ACU's CU-scoped queries, so `areas` records which query found a bill, not who the bill benefits. It was inflating 54 acts — mostly opaque amendments (`S.Amdt.2241`, an amendment to the GENIUS Act, tagged *Field of Membership*; `S.Amdt.5788`, an NDAA amendment, tagged *Charter Modernization*) — to full `cu_primary` at sponsor weight 1.0. Every one was re-tested against its own operative text for FCUA/NCUA/credit-union language; **0 of 54 survived**, so all 54 were demoted to `shared`. This removed Rounds, Tillis, Crapo, Loudermilk and Titus from the top 18 — an entire third of the board that was resting on a collection artifact.

**The naked-default residue went from 299 acts / 33.3% of weight to zero.** The weakest rung is now
L8 (the pipeline's own category assignment, conf 0.6) — all L8 and L7 calls are in the regenerated
review queue, weight-sorted.

**FINAL board (leg-only · OPPOSE −1.0 · ACU letters 0.60 · conduct ladder · zero pins · baseline 0.5024):**
1–12: Padilla · Gonzalez★ · Fitzpatrick★ · Cramer★ · Timmons · Sullivan · Fitzgerald · Vargas ·
**Tim Scott★ (9)** · Young Kim★ · Sherman★ · **Huizenga (12)** — 13–18: Hagerty · Meuser · Sessions ·
Crapo · **Cortez Masto★ (17)** · Bonamici.
**At 12: 6/7 + Huizenga in Tier 1. At 18: 7/7.**

**Andy Barr raw #12 → final slot 37 = Tier 3.** Effective severity 7.25 clears the 6.00 rung. The
ledger is the *only* thing removing him — on score alone he is a Tier-1 member, and the framework
says so plainly rather than hiding it.
**French Hill raw #73 → final slot 85 = untiered.** Effective severity 10.00 clears the 9.00 rung.
He is the one member who fails on *both* counts: his own record puts him at 73 before the ledger is
opened (factor 0.473 against a 0.502 baseline, **1.0 of 20.50 agenda credit CU-primary**, and his
two authored bills of the 119th are `bank_primary` H.R.6955 and `crypto_primary` H.R.3633), and the
ledger then takes him off the board. Eleven members between 74 and 84 move up one as he vacates;
Tiers 1 and 2 are untouched.
Wagner 33; Waters 134.

Earlier §0 (kept for history): the Quorum audit that triggered the reset found 24 agree / 7
unadjudicated / 5 misclassified / 8 missing-from-universe among ACU's 44 tracked bills, and the
OPPOSE sign error (+5.00 credit awarded for fighting ACU, now −1.0).

---

## 1. Architecture and blast radius

**The tier is display-only.** `fec/tier_util.py` states it: *"Pure: reads ranks_python.json,
returns dicts; writes nothing, touches no engine."* And `moneyball_core.overall_display_tier()`
already reads `if legislative_press_tier == 1: return 'Champion'`.

Consequences, and they are the whole reason for this design:

- Changing the tier changes **the Champion label for free**. No change to `moneyball_core`.
- **Rank must not move. `ranks_python.json` is byte-identical. Zero rank delta is the acceptance test** — if any rank moves, the change was wired into the wrong layer.
- No pillar is recomputed, no ratified weight is re-opened, no engine is touched.

New producer → new artifact → `tier_util` consumes it. That is the entire footprint.

---

## 2. What IS being used

### 2.1 Inputs

| Input | Source | Notes |
|---|---|---|
| `Leg%` | `ranks_python.json` → `pcts[member].leg` | Consumed as-is. Already carries `LEGSTANCE_ORIGCO=1`, workbook `DecayWeight`, and all upstream relevance filtering (`BR.excluded_bill`, `EXCLUDED_TITLE_PHRASES`, `bill_overrides.csv`, legfix5 junk-pile decisions). Never recomputed. |
| Act universe | `member_desk_bundle.json` | 614 distinct `(bill\|congress)` keys, 533 members. Bills, amendments, letters, resolutions — all included at role weight. |
| Beneficiary tag | `bill_beneficiary_tags.ndjson` | One row per act. **See §6 — this input is not final.** |
| **ACU position** | `source_data/legislation/acu_legislation_search_registry.json` → `categories[].known_bills[].acu_position` | **Authoritative where present** (55 anchor bills). Built from `Moneyball_ACU_Search_Outline.docx` by `fec/build_legislation_search_registry.py`, which already declares *"The source document is authoritative."* Overrides the beneficiary weight. |

### 2.2 Constants

```python
ROLE_W   = {'sponsor': 1.0, 'original': 0.5, 'cosponsor': 0.25}   # unknown role -> 0.25
PRIMACY_W = {'cu_primary': 1.0, 'shared': 0.5,
             'bank_primary': 0.15, 'crypto_primary': 0.15, 'fintech': 0.15,
             'offtopic': 0.0}
OPPOSE_W        = -1.0            # registry acu_position == 'OPPOSE'; symmetric with cu_primary
SHRINK_ANCHOR   = 15.0
ROSTER_BASELINE = 0.509600        # recomputed each run; this is the current value
TIER_WEIGHTS    = {'legislation': 1.00, 'press': 0.00}
BUCKETS         = (12, 24, 48)
```

`ROLE_W` is the system's own ratified role weighting, matching `say_do_gap.py`.

### 2.3 The computation

```
per member:
    agenda_credit = Σ ROLE_W[role]                      over every act, every instance
    act_weight    = OPPOSE_W  if registry acu_position == 'OPPOSE'   # authoritative
                    else PRIMACY_W[beneficiary_class]
    factor_raw    = Σ ROLE_W[role]·act_weight / agenda_credit
                    (no acts -> factor_raw = 1.0)

    The OPPOSE branch is the only way the factor can move below zero. It is what
    lets the primacy axis express "worked against us," which it previously could not.

ROSTER_BASELINE   = Σ(factor_raw·agenda_credit) / Σ(agenda_credit)      # credit-weighted mean

λ                 = min(1.0, agenda_credit / SHRINK_ANCHOR)
factor_shrunk     = ROSTER_BASELINE + λ·(factor_raw − ROSTER_BASELINE)

score             = Leg% · factor_shrunk
order             = sort by score desc, member name asc as tiebreak
tier              = 1 if slot ≤ 12 else 2 if ≤ 36 else 3 if ≤ 84 else 0
```

**Every act instance counts once.** No de-duplication of reintroductions.

### 2.4 The one gate that IS used — a graduated conduct ladder

**Superseded 2026-07-29.** The earlier draft consumed one field (`severity >= 3`) and emitted one
verdict ("not eligible for Tier 1"). But the ledger schema **already carries `leverage_mult` on
every event**, and the code was collecting it and throwing it away. Two consequences followed:
Barr and Hill drew the identical penalty though their leverage differs by design, and severity-2
events cost exactly nothing, so they could accumulate without bound. The ladder consumes the
ledger's own numbers instead of thresholding one of them.

```
effective_severity(member) = Σ severity × leverage_mult   over OPEN, unexpired events

eff ≥ 3  →  tier ceiling 2   (cannot be a Champion)
eff ≥ 6  →  tier ceiling 3
eff ≥ 9  →  untiered
```

A ceiling is **a floor on slot index, not a fixed demotion**. The member is barred from slots above
their ceiling's first slot, then re-enters at their own score position among the remainder. A
capped member whose score already sits below the ceiling does not move at all — which is why
**French Hill stays at slot 73**: his score put him in Tier 3 before the ledger was consulted.
The placement is greedy and stable, so it can only push a capped member down and can only pull an
uncapped member up; it is a permutation, and nobody is dropped.

| Member | Events | Effective severity | Ceiling | Slot |
|---|---|---|---|---|
| **French Hill** | MS-2026-001 (3 × 2.00) + **MS-2026-004 (2 × 2.00)** | **10.00** | **untiered** | 73 → **85, off the board** |
| **Andy Barr** | MS-2026-002 (3 × 1.75) + MS-2026-003 (2 × 1.00) | **7.25** | 3 | raw 12 → **37** |

Barr's multiplier is 1.75 (subcommittee chair of jurisdiction, original cosponsor of the vehicle);
Hill's is 2.00 (full-committee chair *and* vehicle sponsor). Under the old binary gate both of the
severity-2 credit-appropriation events were worth zero.

**MS-2026-004 was added 2026-07-29** in answer to *"why the fuck is French Hill in Tier 3?"* — and
the first half of that answer is that **the ledger was not what put him there.** His score order is
73 and Tier 3 is slots 37–84, so with an empty ledger he lands at 73 anyway. The cap was doing
nothing. Investigating why produced a second documented event: the **Financial Services Committee's
own release**, issued under his gavel, claiming the bill lifts *"burdens on community banks and
credit unions"* on the same vehicle from which all four ACU asks had been stripped, with no credit
union organization quoted. Full evidence, arithmetic, and the one judgment call (the 2.0 multiplier
vs Barr's 1.0) are in **`CONDUCT_LADDER.md` §4–5**.

**Documented limitation.** Effective severity sums *logged* events, so the ladder measures the
ledger, not the world. Before MS-2026-004 was found, Barr (7.25) out-scored Hill (6.00) — the
arithmetic called Barr the worse actor when Hill was the chair *and* the author of the vehicle.
That inversion was an artifact of ledger coverage. The mitigation is procedural: for every logged
vehicle, sweep every member with leverage over it. Asserted in
`test_ladder_counts_events_so_completeness_matters` so it stays explicit.

Each event still carries an evidence quote, the member's leverage at the time, a decay clock, and a
stated cure. **The cure arithmetic is now legible to a member's staff**: Barr clearing MS-2026-002
drops him to 2.00 and off the ladder entirely; clearing only MS-2026-003 leaves him at 5.25, still
capped at Tier 2. That asymmetry is the ask, priced.

Reference implementation and 24 passing unit tests: `tier_util_primacy.patch.py`,
`test_primacy_tier.py` (`load_open_breaches` → `tier_ceiling` → `apply_conduct_ladder`).

---

## 3. What is NOT being used — do not re-add these

Each was built and empirically rejected. The evidence is recorded so nobody re-litigates it.

| Rejected | Why |
|---|---|
| **Family de-dup** (collapse same-title reintroductions) | Buried Juan Vargas at #41. He sponsored the CU Board Modernization Act in three straight Congresses and passed the House all three times; de-dup counted that as one act. Removing it puts him at **#6 on F 0.780**, the second-highest purity in Tier 1. |
| **Significance weights** (commemorative 0.25 / governance tweak 0.5) | The 0.5 "governance tweak" haircut landed on the *author* of the most successful CU bill in the system. Removed with de-dup. |
| **Delivery / advancement weighting** | Was a workaround for de-dup damage. Unnecessary once de-dup is gone, and it costs 3 of 7 target members. |
| **Author-significance, persistence bonus** | Same — scaffolding for a problem that no longer exists. |
| **Primacy floor + standing gates** | Achieves 7/7 on the target list but is explicitly "forcing." Retained as the *calibrated* variant, not the board of record. |
| **Jurisdiction leverage multiplier** | **Unsafe bare.** Without an eligibility floor in front of it, chair ×1.15 seats **Barr at #3 and Wagner at #10**. Only ever valid downstream of a primacy floor. |
| **IMP-weighted `shared`** | Board quality 6/7 → 4/7. Rewards CFPB / Credit-Card-Mandates volume, which the generalists have most of; seats Huizenga and Loudermilk. |
| **Any leniency toward `shared`** | Decisively rejected. Sweep: flat 0.50 → 0.60 → 0.70 → split 0.70/0.35 walks **Barr 26 → 23 → 15 → 5** and Hill 89 → 67. Shared is ~85% of most files, so raising it is a direct subsidy to whoever has the largest undifferentiated portfolio — i.e. the frenemies. **Flat 0.50 sits at the roster baseline, making shared acts score-neutral by construction. That is the property we want.** |
| **Press pillar** | Weighted 0.00. |
| **All 8 standing pins** | Retired. `tier_overrides.proposed.json` ships `placements: []`. The only permitted forced move is an evidence-cited demotion. |
| **Say-do gate / delivery_mult / say_do_gap** | Untouched, left exactly as they are in the live system. |

---

## 4. Current output (regression fixture)

Configuration of record: **letters as acts at `LETTER_W = 0.60`; letter lead = `sponsor` role 1.00,
letter signatory = `original` role 0.50**; shrink anchor 15.0; buckets 12/36/84; conduct ladder on.
Roster baseline **0.502380**.

**Tier 1 (Champions), slots 1–12:**
Padilla · Gonzalez★ · Fitzpatrick★ · Cramer★ · Timmons · Sullivan · Fitzgerald · Vargas ·
Tim Scott★ · Young Kim★ · Sherman★ · Huizenga

**Slots 13–18:** Hagerty · Meuser · Sessions · Crapo · **Cortez Masto★ (17)** · Bonamici

★ = named on Paul's ground-truth list. **6 of 7 at 12 seats, 7 of 7 at 18.** The one that needs
18 seats is Cortez Masto, at slot 17 — see §7.1. Huizenga is in at 12 and was reviewed and
accepted. Wagner (32) and Sullivan — Paul's two exclusions — Wagner is out; Sullivan sits at 6,
noted in §7.

Reference positions: **Barr slot 37 (raw 12, ladder-capped to Tier 3)** · **Hill slot 73 (raw 73,
capped but unmoved)** · Wagner 32 · Nunn 42 · Blunt Rochester 117 · Waters 134 · Ciscomani 144.

Golden fixtures for regression: `FIXTURE_expected_board.csv` / `primacy_board_reference.csv` (all
533 — slot, tier, score, Leg%, factors, λ, class-share decomposition, score_order,
effective_severity, ceiling, event IDs) and `primacy_factors.json` (the artifact the producer must
reproduce). Same inputs must give byte-identical output.

The OPPOSE join moves 20 members and leaves Tier 1 intact — **no Tier-1 member carries an OPPOSE
act.** Largest penalties: Fetterman −56, Sanders −50, Ocasio-Cortez −49, Baldwin −37,
Gillibrand −19, Durbin −8.

### 4.1 Mathematical verification (all pass, 2026-07-29)

| Check | Result | Reading |
|---|---|---|
| Primacy share of log-score variance, all 532 | 0.6% | Leg% dominates globally, as it should. (One member has Leg% = 0, so log is undefined; excluded.) |
| …top 100 | 61.5% | |
| …top 40 | 86.6% | |
| **…top 20** | **84.2%** | **In the selection region primacy is the deciding term.** Leg% is a percentile and saturates at the ceiling; it cannot discriminate among the top 20. Global Spearman (0.9928) is the wrong statistic for a top-k problem — it is dominated by the 400 members nobody is selecting. |
| Shrink containment: `factor_shrunk` strictly between `factor_raw` and baseline | 0 / 533 violations | λ is a convex weight; no member is pushed past either endpoint |
| `shared` weight 0.500 vs roster baseline 0.502380 | gap 0.0024 | Shared acts are score-neutral **by construction**, not by tuning |
| Ladder is a permutation, never promotes a capped member | 0 violations | also proven in `test_ladder_never_promotes_and_preserves_the_roster` |
| Uncapped members never pushed down by the ladder | 0 violations | a capped member's seat is released, never taken |
| Ladder is monotone in effective severity | proven | more grievance never yields a better ceiling |
| λ == min(1, credit / 15) for all 533 | 0 violations | |
| Universe closure: bundle acts == tag acts | 614 / 614 | classification and universe in sync |
| Zero naked defaults (L9) | 0 acts | down from 299 acts / 33.3% of weight |
| L8 `areas` never asserts `cu_primary` | 0 violations | the circularity fix holds |
| No Tier-1 member carries an OPPOSE act | 0 members | |
| Producer determinism (same inputs → same output) | True | |
| Rank delta vs `ranks_python.json` | **0** | display layer only; file is read-only, sha256 `79c087aa31091e75…` |

---

## 5. Build order

1. **Producer** — `fec/primacy_factors.py`. Reads `member_desk_bundle.json` + `bill_beneficiary_tags.ndjson`, writes `primacy_factors.json` via `MC.dump_atomic`. Pure, no network, chain-independent.
2. **Consumer** — `tier_util.legislative_press_tiers()`: apply `TIER_WEIGHTS` (1.00/0.00), multiply `Leg%` by `factor_shrunk`, then re-seat through `apply_conduct_ladder()`. **Fail open** if either artifact is absent (mirrors `moneyball_core`'s bill-corroboration sentinel); **fail loud** if either is present but malformed.
3. **Tests** — add `test_primacy_tier.py` (24 tests) to `fec/tests/run_tests.py`; add fixture tests asserting `ROSTER_BASELINE`, λ, and the Tier-1 roster against §4.
4. **Overrides** — swap in `tier_overrides.proposed.json` (`placements: []` + `demotions[]`). `load_tier_overrides()` returns `{}` on empty placements and ignores the unknown `demotions` key, so it is safe to land ahead of the code.
5. **Desk / dashboard** — surface the fail reason. *"Not a Champion because…"* is the product.

**Verification:** kernel tests → `run_pipeline.py` → **rank delta exactly zero** → `audit_full.py` clean.

---

## 6. Blocking: fix the classification input first

**Adopt Quorum as the classification authority.** ACU's export already carries `Issues`, `Priority`,
`Stance`, and real AI summaries. The `Issues` field *is* the adjudication — my 38 regex rules are a
lossy reconstruction of a taxonomy that already exists, and Quorum sees what titles hide.

Mapping validated against the 44-bill export:

| ACU `Issues` | beneficiary |
|---|---|
| Credit Union Powers · Credit Union Governance · Credit Union Capital · Credit Union Tax Status · Member Business Lending | `cu_primary` |
| CFPB · Housing-Mortgage Lending · Fraud and Illicit Finance · Regulatory Reform · Small Business · Data Privacy · CDFI | `shared` — **then override to `cu_primary` where the text amends the Federal Credit Union Act or concerns NCUA** (this is what H.R.7647 needs) |
| Digital Assets | `crypto_primary` |

Also available and currently unused: **`Priority` = "High Priority"** — ACU's own flag, on 8 of 44,
and *every one of those 8 is a CU bill*. It is a far better priority signal than inferring from IMP.
And `Stance` exists in Quorum, meaning **oppose positions are tracked upstream and are absent from my
inputs entirely.**

**The five confirmed misclassifications** (row-level detail in `quorum_adjudication_audit.csv`):

| Bill | ACU Issues | Mine | Should be | Note |
|---|---|---|---|---|
| **H.R.7647** | Housing-Mortgage Lending | `shared` 0.35 | **`cu_primary`** | **High Priority.** Amends the FHLB Act to include FCU-insured institutions. |
| H.R.4437 SMART Act | Regulatory Reform | `shared` 0.35 | `cu_primary` | |
| H.R.7056 Community Bank Regulatory Tailoring | Regulatory Reform | `bank_primary` | `cu_primary` | ACU supports it; my title rule saw "community bank" and assumed the competitor. |
| H.R.1919 / S.1124 Anti-CBDC | Digital Assets | `shared` | `crypto_primary` | My registry treats CBDC as shared; ACU files it under Digital Assets. Reconcile with the standing stablecoin(+1)/CBDC(−1) contradiction already flagged in `cu_valence_registry.json`. |

### 6.1 Coverage defect — traced, 2026-07-28

`fec/build_legislation_search_registry.py` reads the outline and produces
`acu_legislation_search_registry.json` correctly: **all 55 anchor bills are present, with positions
and source-paragraph provenance.** The hard-coded `CATEGORY_SPECS` paragraph windows were checked
against the live document — zero bills fall outside them, so the outline→registry step is sound.

The loss is **downstream of the registry**. Five anchor bills reach neither
`member_desk_bundle.json` **nor the workbook role sheets** (0 rows in all five sheets), which places
the defect at collection, not scoring:

| Bill | ACU position | Category |
|---|---|---|
| S.427 / H.R.3380 TAILOR Act | SUPPORT | Examination & Supervision |
| S.3940 AFFORD Act | SUPPORT | CDFI Fund |
| S.1880 CDFI Bond Guarantee | SUPPORT | CDFI Fund |
| H.R.1 | PASSED / MONITOR | **Credit Union Tax Status (IMP 3.0)** |

Work order in `coverage_reconciliation.csv`. Trace each through the collector and the legfix5
relevance/junk-pile decisions to establish whether it was culled deliberately or never fetched.
**A recurring registry-vs-collected reconciliation belongs in `audit_full.py`** — the registry is a
declared expectation, so any anchor bill absent from the bundle is an auditable defect rather than
something a human has to notice.

Work order:

1. Pull the **full** Quorum bill export, not this 44-row slice (`process_quorum.py` / `quorum_query.txt` already exist).
2. Join on `(Label, Session)` → `(bill, congress)`; make `Issues` the classifier, regex the fallback for anything Quorum doesn't cover.
3. **Reconcile the universe gap** — 8 of 44 tracked bills are missing, including H.R.1 on CU Tax Status. Determine whether `member_desk_bundle` is under-collecting or those bills are excluded upstream by the junk-pile / relevance decisions, and record the answer.
4. Re-run the board and re-baseline the fixtures in §4.

Until step 4, treat every factor as provisional.

---

## 6.2 Three members run to exhaustion, 2026-07-29

### Maxine Waters — the letters were parsed; she is not failing on primacy

All 7 ACU advocacy letters in the bundle were opened and read at the signature block, with leaders
coded `sponsor` (1.00) and signatories `original` (0.50). **She led LTR-119-CDFI-WATERS with Bill
Foster — 119 signatories.** Her raw primacy factor is **F = +0.5922, above the 0.502380 baseline.**
On the question the primacy axis was built to answer — *champion for whom* — she passes.

Her constraint is upstream: **Leg% = 0.641**, and the workbook shows exactly why.

| | Sponsor | Original | Cosponsor | Decay-weighted total |
|---|---|---|---|---|
| **Waters** | 22 | 2 | **7** | **18.11** |
| Cortez Masto | — | — | — | 25.10 |
| Barr | — | — | — | 51.25 |

She is an author, not a joiner. The Leg pillar rewards cosponsorship breadth, and she has seven
cosponsorships on the whole CU universe. **No primacy configuration can seat her**, because primacy
is a multiplier on a percentile she does not have — 0.641 × 1.00 (a perfect factor) = 0.641, which
is slot ~40, not slot 12. Seating her requires changing `Leg%`, which moves rank, which is outside
the zero-rank-delta contract of this work. This was tested four ways in the shadow runs (§3) and
every version that lifted her broke something else.

**The honest statement to your boss:** the system says Waters is loyal and low-volume. That is a
true description of her file. If ACU's view is that leading the CDFI letter should count like
authorship, the lever is `LETTER_W` or the Leg pillar's role weights — not primacy.

### Catherine Cortez Masto — blocked on data, not on judgment

She signed **no** letters, so every increase in `LETTER_W` costs her ground relative to the roster.
She sits at **slot 17** — inside Tier 1 at 18 seats, outside at 12.

Her two FHLB bills, **S.1684|117** and **S.1439|119**, are plausibly `cu_primary` on the same
reasoning that made H.R.7647 CU-primary (the FHLB community-financial-institution definition). They
are currently `shared`. **They cannot be adjudicated from what we have**: the bundle summaries are
**51 and 47 characters** — the title and nothing else. Only **11 of her 24 acts** carry usable text.

Promoting both would move her to roughly slot 13–14; promoting them *without evidence* is exactly
the L8 circularity error that cost five members their seats earlier in this work. **Blocked pending
the full Quorum export** (see §7.6). This is a two-row fix once the text exists.

### Andy Barr — the ladder is the answer, and it was already in the ledger

Covered in §2.4. The point worth repeating: **no new evidence was invented and no new field was
added.** `severity` and `leverage_mult` were both already recorded on every event by the schema
Paul approved on 2026-07-28; the consumer was reading one and discarding the other. Barr moves
Tier 2 → **Tier 3, slot 37** because summing the two numbers the ledger already holds gives 7.25,
and 7.25 clears the 6.00 rung.

---

## 7. Open decisions for Paul

1. **Letter signatory role weight — one line, and it is a genuine judgment call.** Signatories are
   currently coded `original` (0.50). The arguably more principled coding is `cosponsor` (0.25),
   since signing a letter is endorsement, not authorship — and it is what the role vocabulary means
   everywhere else in the system. Tested: **at 0.25 Masto rises 17 → 16 but Huizenga falls 12 → 13,
   out of Tier 1.** There is no setting that seats Masto at 12 *and* keeps Huizenga, so this is a
   preference, not an optimum. Shipping at **0.50** because Huizenga was explicitly reviewed and
   accepted.
2. **Tier 1 size: 12 or 18.** 12 gives 6/7 of the named list plus Huizenga; 18 gives 7/7 by
   catching Cortez Masto at 17. `BUCKETS` is one constant. Note that 18 is not a neutral widening —
   it also admits Hagerty, Meuser, Sessions, Crapo and Bonamici.
3. **Tim Scott (#9) — resolved, kept for the record.** He was the hardest case at #40 under the
   pre-letter configuration: 85.9% `shared`, 5.6% CU-primary, factor 0.499 against a 0.504
   baseline. Every attempt to reach him by tuning the primacy weights degraded the board. What
   actually seated him was **evidence, not tuning** — joining the ACU advocacy letters as
   full-weight acts. That is the pattern worth internalizing: when a member you know is a champion
   scores badly, the first hypothesis should be a missing input, not a wrong constant.
4. **Dan Sullivan (#6)**, flagged for removal, still in. Not removable by primacy — he is genuinely
   pure (48.7% CU-primary), so the axis has no grip on him. The only thing separating him from the
   rest of Tier 1 is no seat on Banking or Financial Services and only 2 authored CU acts. Removing
   him needs a standing rule (committee-of-jurisdiction requirement) or a ledger event. **The
   system is telling you something true here and it disagrees with the list** — worth resolving
   deliberately rather than by pin.
5. **`SHRINK_ANCHOR = 15`** is inherited from `build_media_blend`'s press convention, but the
   legislative agenda's median credit is **2.6** and 98% of the roster sits below the anchor. It is
   doing real work un-examined. Loosening it was tested and made the board worse — but it deserves
   a deliberate ruling rather than inheritance.
6. **The full Quorum export is the single highest-value data request.** It unblocks three separate
   things at once: Cortez Masto's two FHLB bills (§6.2), the ~38% of role weight still resting on
   L7 title-rules, and the 559 acts with no authoritative ACU position (item 8). One export.
7. **`OPPOSE_W = -1.0`** is set symmetric with `cu_primary = +1.0` — opposing on Interchange is
   treated as exactly as consequential as helping. Defensible, but it is a values judgment, not a
   derived constant. No member currently ends with a negative factor; the most adverse is Zoe
   Lofgren at +0.100.
8. **Only 55 of 614 acts carry an authoritative position.** The other 559 came from the outline's
   search queries, not its named-bill list, and have no ACU stance attached. Bills in the two
   defensive categories (Interchange, Credit Card & Consumer-Fee Mandates) that are *not* registry
   anchors are the highest-risk unknowns — a CCCA companion or a fee-mandate bill introduced after
   the outline was written would currently score **+0.5** instead of **−1.0**, a 1.5-point sign
   error per act.
9. **Decay asymmetry.** `Leg%` applies the workbook's `DecayWeight`; the primacy factor does not. A
   117th-Congress cosponsorship weighs the same as a 119th inside the ratio. Not fatal, but it
   quietly favours members whose CU work is old.
10. **Ladder rungs 3 / 6 / 9 are a first proposal.** They are evenly spaced and they place the two
   known cases sensibly, but no member currently sits near a boundary except Hill at exactly 6.00 —
   so the rungs have not really been stress-tested. Worth revisiting after the ledger has more than
   three events in it. **Nothing expires automatically yet**: `decay_years` is recorded on every
   event and read by nothing.

---

*Artifacts, all in `audits/primacy_shadow_20260728/ship/`: `primacy_factors.py` (producer) ·
`primacy_factors.json` · `tier_util_primacy.patch.py` (consumer + ladder) · `test_primacy_tier.py`
(24 tests) · `FIXTURE_expected_board.csv` and `primacy_board_reference.csv` (all 533 rows) ·
`bill_beneficiary_tags.ndjson` (614 acts) · `grievance_ledger.ndjson` · `tier_overrides.proposed.json`
(`placements: []`) · `beneficiary_review_queue.csv` · `INTEGRATION.md`.*
