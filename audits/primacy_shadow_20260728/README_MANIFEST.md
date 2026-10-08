# Primacy shadow recompute — audits/primacy_shadow_20260728
*Session 2026-07-28 (Paul + Claude). Companion to `GRIEVANCE_LAYER_DESIGN_2026-07-28.md` (four axes / seven moves).*

**Nothing live was touched.** This folder is additive, in the standing audits/ pattern. The live
pipeline, ranks_python.json, tier_overrides.json, and all engines are exactly as they were.

## 2026-07-28 addendum — the pin purge

Paul's directive, same session: **"any pin we can get rid of."** All eight standing placements are
retired in `tier_overrides.proposed.json` (`placements: []`); the only forced moves permitted are
evidence-cited `demotions[]`. Verified consequences on the primacy-reweighted board:

- **Young Kim holds Tier 1 on merit** (raw slot 10) — her pin was redundant.
- **Juan Vargas (raw 12) and Scott Fitzgerald (raw 13) earn Tier-1 seats** — the 2026-07-16 Tier-2
  pins had been suppressing two members the honest math puts top-12. They displace Ann Wagner (15)
  and Roger Williams (16).
- Crapo lands Tier 2 (28); Tim Moore (68), Velázquez (66), Waters (73) land upper Tier 3 on
  today's tags — Waters' path up runs through the review queue (her agenda is heavy in CDFI/consumer
  rows still at the default 0.5 weight), not through a pin.
- Note: dropping placements against TODAY'S live scores (without the primacy integration) changes
  almost nothing — Barr remains #1 mathematically. The purge, the primacy weights, and the
  demotions are one package and should land together.

## Contents

| File | What it is |
|---|---|
| `before_after_tier1.html` | The deliverable — live Tier 1 vs primacy-reweighted + accountability Tier 1 |
| `bill_beneficiary_tags.ndjson` | All 614 tracked bills/letters tagged by primary beneficiary (first pass) |
| `beneficiary_review_queue.csv` | 299 low-confidence keys (33% of agenda credit) awaiting Paul's adjudication, sorted by credit at stake |
| `grievance_ledger.ndjson` | MS-2026-001/002/003 — the Main Street refusal (Hill, Barr) + Barr credit-appropriation, with evidence URLs, quotes, leverage, cure conditions, decay |
| `tier_overrides.proposed.json` | Drop-in replacement: Barr #1 anchor retired, `demotions[]` added, Waters pin flagged (still binding) |
| `primacy_member_table.csv` | All 533 members: pillar pcts, raw + shrunk factors, before/after score, slot, tier |

## 2026-07-28 addendum 2 — press-stripped variant ("try this first")

Paul asked for the board with press removed (1.00 Leg / 0.00 Press), primacy + pinless + demotions.
Result in `before_after_tier1.html` (variant section) and `scenario_slots.csv` (all 533 members ×
four scenarios). Headlines: Cortez Masto's press pillar is **negative** (−0.007), so stripping press
lifts her to Tier 1 slot 11 — she is the Senate sponsor of the loan-maturities ask (S.3616); Sherman
(H.R.4167 original) and Brownley (veterans MBL author) also enter; Scott (→40) and Nunn (→47) fall —
their standing was press-built; Waters falls too (→156, authored conversion is her case, which a
volume pillar undercounts); Ciscomani (42% CU-primary, led the CU-tax letter, agenda 4.8) stays
invisible to every volume-driven scenario — watch-list material until leadership acts are weighted.
Structural caveat: the tier deliberately excludes the Influence pillar, so demoting Scott from the
*tier* does not erase his Banking-gavel power — that lives in the overall rank's 40% committee term.

## 2026-07-28 addendum 3 — v3 policy board, v4 null result, v5 Waters fix

Paul's directives, same session: back to 0.84/0.16; family de-dup ("Board Modernization alone
shouldn't get them there" — its 5 keys collapse to 1 act at 0.5 significance); amendments, letters
and resolutions primacy-classified at **full weight** (160 amendments were already in the bundle —
6 cu_primary, 42 crypto_primary); commemoratives 0.25. Diagnosis correction recorded: Padilla's #1
was never Board Modernization — it is 5 sponsored CU amendments + authored CLF/FCU-sunset bills
(7.0 CU-authored credit, most on the roster).

- **v3 (policy)**: live pillar × de-duped/sig primacy factor. Tier 1: Padilla, Meuser, Fitzpatrick,
  Britt, Cramer, Gonzalez, Daines, Scott, Williams, Wagner, Timmons, Young Kim. Waters stuck at 74.
- **v4 (null result, kept for the record)**: authorship-steepened role curve *inside the factor*
  moved nothing — a discount factor multiplies the live pillar and can only deflate; it can never
  lift a member above their pillar. The Waters fix cannot be a factor tweak.
- **v5 (the Waters fix realized)**: legislative credit REBUILT from de-duped family credit
  (sponsor 1.0 / original 0.33 / ride 0.10) × primacy, delivery-free, then percentiled. **Waters
  74 → 3 (Tier 1)** — 11.0 authored credit, most of anyone. Trade-offs, stated honestly: bundle-only
  credit is narrower than the workbook pillar; volume-of-authorship admits shared-heavy authors with
  zero CU-authored work (Ted Cruz enters at 5); Gonzalez/Fitzpatrick (breadth members) drop; and
  with delivery dropped, Barr and Hill go raw #1/#2 on their introduction volume — **the grievance
  ceiling becomes the only guard against the Barr strategy. Dropping delivery obligates the ledger.**
- **Production recommendation**: v5's credit semantics (family de-dup, sig, full-weight acts,
  primacy, authorship-first) applied at the pillar source over the full workbook interaction set —
  keeps the Waters fix while restoring the breadth that bundle-only credit loses.

## 2026-07-28 addendum 4 — RECOMMENDATION EXECUTED (v6, the production-semantics board)

Paul: "proceed with the recommendation." Built. `before_after_tier1.html` now shows the live board
against the **recommended board**; `primacy_member_table.csv` and `scenario_slots.csv` carry all 533.

**What changed from the shadow variants.** Legislative credit is now rebuilt *at the source* from the
workbook's full interaction set — 10,979 role rows across `Sponsor Interactions`,
`Original Co-Sponsor Interaction`, and `Co-Sponsor Interactions`, with the workbook's own
`DecayWeight` honored — plus 572 letters, amendments and resolutions from the bundle as full-weight
primacy-classified acts. **The `Success Sponsor` / `Success Original Co-Sponsor` sheets are
deliberately excluded: that is the delivery variable, dropped per directive.**

**Recommended Tier 1:** Waters · Meuser · Padilla · Tim Scott · Cramer · Gonzalez · Emmer ·
Fitzgerald · Hagerty · Clyde · Tina Smith · Fitzpatrick.

**The CU-primacy floor (≥0.50 CU-primary credit) is the new and necessary piece.** Authorship volume
alone is not loyalty: without the floor the board seats **Ted Cruz (CU credit 0.00)**, Loudermilk
(0.03), Crapo (0.05), Torres (0.13), Roger Williams (0.20) and Young Kim (0.38). The floor swaps all
six for members with real CU-primary records — Clyde (2.00), Emmer (1.36), Fitzpatrick (1.36),
Fitzgerald (1.00), Smith (0.69), Hagerty (0.56). **All 12 recommended Tier-1 members hold genuine
credit-union work.** The 0.50 value is a first proposal, not a derived constant — sensitivity-test it.

**Two findings worth carrying into the boss conversation:**
- **French Hill's CU-primary credit is 0.00.** He fails the primacy floor outright, before the
  grievance ledger is consulted. The system now catches him unaided.
- **Barr does not fail either test.** Delivery-free, his introduction mill returns him to raw slot 1,
  and his CU credit (1.13) clears the floor. **The grievance ceiling is the only mechanism that stops
  him** — which is the standing argument for keeping the ledger load-bearing rather than decorative.
- **Waters 144 → 3**, confirming the v4 null result's lesson: the fix had to be applied to the credit,
  never to a discount factor.


## 2026-07-28 FINAL — Champion gates (this is the recommendation)

Paul: gates apply to **the label and Tier 1, not to rank**. Delivered as
`CHAMPION_GATES_RECOMMENDATION.md` + `champion_gates.html`. Rank, pillars, weights and
`ranks_python.json` are untouched — the change lives entirely in `tier_util`, which is already
display-only, and `overall_display_tier` already reads Tier 1 ⇒ Champion, so gating Tier-1
eligibility gates the crown with **zero rank delta**.

Gates: **G1 primacy** (CU-primary credit ≥ 0.50) · **G2 delivery** (chairs of jurisdiction must have
advanced a CU-primary act; everyone else must have advanced *or* authored one — ranking members are
NOT held to the chair test) · **G3 conduct** (no unexpired severity-3 grievance). 72/533 clear all
three. Champions: Meuser, R. Williams, Timmons, Wagner, Young Kim, Hagerty, Fitzpatrick, Emmer,
Cramer, Fitzgerald, Neguse, Brownley. Removed from the live top-12: Barr (ledger only — he passes
G1/G2, which is why the ledger must stay maintained), Hill (fails all three, 0.00 CU credit),
Britt (0.12), Tim Scott (chairs Banking, sponsored S.762, never moved it).

New artifacts: `champion_gates.html`, `champion_gates.csv` (all 533 + fail reasons),
`champion_gates.json` (gate inputs), `tier_util_gates.patch.py`, `test_champion_gates.py`
(10 kernel tests, passing).

**The earlier shadow boards (v3 / press-stripped / v6 / v7) are retired** — kept in
`before_after_tier1.html` and `scenario_slots.csv` as the evidence record for why gates beat
re-weighting: press-weighted produced frenemies, volume-weighted produced Ted Cruz at #5 with zero
CU work, delivery-weighted produced noise and knocked Waters out on a scaling artifact.

## Method (exact)

- Classes and weights: `cu_primary` 1.0 · `shared` 0.5 · `bank_primary`/`crypto_primary`/`fintech` 0.15 · `offtopic` 0.0.
  Classification = manual adjudications for the high-credit titles (Main Street → bank_primary; CLARITY/FIT21/GENIUS/stablecoin → crypto_primary;
  anti-CBDC → shared, matching the registry's own CBDC=-1 logic; Board Modernization / loan-maturities H.R.4167 / veterans MBL H.R.507 / MBL threshold H.R.1791 → cu_primary; SAFE Banking / notarization / housing / CFPB-structure fights / interchange → shared)
  + keyword rules + LTR- topic slugs (CUTAX → cu_primary, CDFI → shared). Everything below 0.6 confidence defaults to shared 0.5 and queues.
- Member legislative factor = Σ role_w·class_w / Σ role_w over the member's tracked agenda (ROLE_W: sponsor 1.0 / original 0.5 / cosponsor 0.25 — say_do_gap's constants).
- Press factor = mean over supportive articles (pol ≥ 0) of [0.15 if crypto-topical by title else 1.0].
- Shrink: factor′ = baseline + min(1, credit/15)·(factor − baseline); baselines are credit-weighted roster means (leg 0.504, press 0.966). The 15 mirrors build_media_blend's thin-category f = min(1, nz/15).
- After-score = 0.84·Leg%·legF′ + 0.16·Press%·pressF′ on ranks_python.json pcts (the exact tier_util inputs); overrides applied with the placement contract semantics; demoted members are ineligible for Tier 1 (ceiling 2) while their cited events are open; buckets fixed 12/24/48.
- Regression check: the reconstructed BEFORE board matches the live board (tier_util semantics + current tier_overrides.json) exactly, 12/12.

## To make it real (in order)

1. Adjudicate `beneficiary_review_queue.csv` (33% of credit sits at defaults — top rows carry most of it).
2. Ratify `tier_overrides.proposed.json` → replace `tier_overrides.json`. It now carries `placements: []` (all pins retired) + `demotions[]`. `load_tier_overrides()` returns {} on empty placements and ignores the unknown `demotions` key, so the drop-in is safe today; land it together with the primacy integration so the purge bites (see addendum above).
3. Patch `tier_util.apply_tier_overrides()` (~10 lines): accept `demotions` (member → ceiling, events); demoted members are excluded from Tier-1 forced/eligible lists and join Tier 2; fail loud on unresolved names, same as placements. Add a kernel test.
4. Move the beneficiary weights from this shadow into the legislative pillar's raw credit (and the registry's industry tags into the press pipe) via the normal chain, with the standard protocol: kernel tests → pipeline → rank-delta review (deltas ARE expected and intended here) → audit_full.
5. Adjudicate flags: the stablecoin(+1)/CBDC(−1) registry contradiction; the Waters Tier-2 pin; Tim Scott exiting at raw slot 17 (the 0.84/0.16 weights were chosen partly to keep him Tier 1).

## Caveats (honest limits of the shadow)

- Press factor is a crude title-level crypto flag; the durable fix is industry tags on cu_valence_registry families.
- 299 keys (33% of credit) are at default shared/0.5 pending adjudication — the after-board can move as Paul rules on them.
- The shadow multiplies tier-score *inputs*; the production integration should weight bill credit at the source (leg pillar raw), which is cleaner and will differ at the margins.
- Grievance decay (4y G1–G3, 2y G4–G6) is recorded in the ledger but nothing expires automatically yet.

Source snapshot: member_desk_bundle.json (mtime 2026-07-28 14:23), ranks_python.json (2026-07-28 14:05), tier_overrides.json (2026-07-19), say_do_gap.json (2026-07-19).
