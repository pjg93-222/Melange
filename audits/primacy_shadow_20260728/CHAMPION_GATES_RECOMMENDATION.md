# Champion should be something a member can fail
**Recommendation — 2026-07-28.** Supersedes `GRIEVANCE_LAYER_DESIGN_2026-07-28.md`, which stands as background.
**Scope, as directed:** the gates apply to the **Champion label and Tier 1**. **Rank is untouched.**

---

## 1. The recommendation in one paragraph

Your boss's complaint was never "Barr is ranked too high." It was that Barr and Hill shouldn't be
called **Champions**. Those became the same thing only because the code makes them the same thing —
`overall_display_tier()` reads `if legislative_press_tier == 1: return 'Champion'`, with no other
input and no way to lose it. So the fix is to separate them again: leave rank and the score order
exactly as they are, and make Tier-1 *eligibility* conditional on three gates. Because the Champion
crown already keys off Tier 1, gating Tier 1 gates the crown for free.

**This is a display-layer change with zero rank delta.** `tier_util` is already documented as
"DISPLAY-ONLY … writes nothing, touches no engine." No pillar moves, no weight is re-ratified,
`ranks_python.json` is byte-identical, and the verification protocol's zero-rank-delta requirement
holds trivially.

## 2. Why not the alternatives (what four shadow runs actually showed)

We tried to fix this by re-weighting a single blended score, four different ways. Each one produced
a different pathology, because one scalar was being asked to answer four different questions:

| Run | Change | What broke |
|---|---|---|
| v3 | live pillar × primacy discount factor | A multiplier can only deflate. Caught Hill (3→13), never touched Barr, couldn't lift Waters. |
| v5/v6 | legislative credit rebuilt, delivery dropped | Fixed Waters (144→3) but authorship *volume* is not loyalty — **Ted Cruz entered at #5 with 0.00 CU-primary credit** — and with delivery gone, Barr's introduction mill returned him to raw #1. |
| v7 | delivery restored as a multiplier | Over-corrected the other way: tiny-agenda members flooded Tier 1 and the CU floor, now denominated in delivery-discounted credit, knocked Waters out on a pure scaling artifact. |

The lesson is structural, not a tuning miss: **press-weighted gives you frenemies, volume-weighted
gives you Ted Cruz, delivery-weighted gives you noise.** Gates answer the four questions separately
and are the only version that survives all three stress cases at once.

## 3. The three gates

| | Gate | Test | Rationale |
|---|---|---|---|
| **G1** | **Primacy** | CU-primary credit ≥ **0.50**, de-duped by policy family, significance- and decay-weighted | "Champion *for whom.*" Answers the Huizenga/crypto problem. **Hill scores 0.00.** |
| **G2** | **Delivery** | **Chair of jurisdiction:** ≥1 CU-primary act advanced past introduction. **Everyone else:** ≥1 CU-primary act advanced **or** authored | For gavel-holders inaction is a decision; a minority member who cannot move a bill is judged on effort. Ranking members are deliberately *not* held to the chair test — they don't control the calendar. |
| **G3** | **Conduct** | No unexpired severity-3 grievance | The Main Street refusal. Each event carries an evidence quote and a stated cure, so a demotion is the next ask with a price tag on it. |

Gate inputs come from the workbook's own role sheets (`DecayWeight` honored) plus letters,
amendments and resolutions as full-weight beneficiary-classified acts, with same-title
reintroductions collapsed to one policy family. **72 of 533 members clear all three**, so the
12/24/48 buckets fill comfortably.

## 4. The result

**Champions (gated Tier 1):** Meuser · Roger Williams · Timmons · Wagner · Young Kim · Hagerty ·
Fitzpatrick · Emmer · Cramer · Fitzgerald · Neguse · Brownley.

**Removed from the live top-12:**

| Member | Why |
|---|---|
| **Andy Barr** | Open refusal MS-2026-002/003. **Passes G1 and G2 outright** — the ledger is his only disqualifier. |
| **French Hill** | Fails all three: 0.00 CU-primary credit; chair of jurisdiction with nothing advanced; open refusal MS-2026-001. |
| **Katie Britt** | 0.12 CU-primary credit; chair with nothing advanced. |
| **Tim Scott** | Chairs Banking and has advanced no CU-primary act. He sponsored S.762 — the Senate loan-maturities ask — and has not moved it. |

Two things worth saying out loud to your boss:

- **Hill fails without the ledger even being consulted.** The system now catches that pattern unaided.
- **Barr does not.** He clears primacy and delivery; only the grievance event stops him. That is the
  standing argument for keeping the ledger maintained rather than decorative — and the reason
  every demotion row must cite an event ID.

**Members the gates surface without anyone pinning them:** Waters (live 144) and Padilla (live 46)
clear all three on authored CU-primary work; Ciscomani clears from live slot 168 on 1.75 CU credit
and the CU-tax letter he led — a real watch-list champion the score alone will never see.

**What the gates do not do:** they don't touch rank. Tim Scott keeps every bit of the Banking gavel
in the overall rank's 40% committee pillar. The gate says "not engaged for us," never "not powerful."

## 5. Ship it

| # | Step | Effort |
|---|---|---|
| 1 | Replace `tier_overrides.json` with `tier_overrides.proposed.json` — all 8 pins retired, `demotions[]` added | minutes |
| 2 | Apply `tier_util_gates.patch.py` into `fec/tier_util.py`; add `test_champion_gates.py` to the kernel suite (10 tests, passing) | ~half day |
| 3 | Wire the gate producer into the chain so `champion_gates.json` regenerates with the bundle | ~1 day |
| 4 | Surface the fail reason in the desk/dashboard — "not a Champion because…" is the whole product | ~1 day |
| 5 | Adjudicate `beneficiary_review_queue.csv` (299 rows, 33% of agenda credit at defaults) | ongoing |

Verification: kernel tests → pipeline → **rank delta must be exactly zero** (if any rank moves,
something was wired into the wrong layer) → `audit_full` clean.

## 6. Open items for your judgment

1. **The 0.50 floor is a first proposal, not a derived constant.** Sensitivity-test it — at 0.25 the
   board loosens toward token cosponsors; at 1.00 it tightens toward authors only.
2. **One adjudication is already applied**: Risk-Based Credit Examination Act → `cu_primary` (NCUA
   exam policy). It is what keeps Ann Wagner a Champion — a good illustration that the review queue
   is not clerical work, it decides who is a Champion.
3. **The 6 CU-primary amendment classifications** ride on title/summary text and deserve your eye.
4. **Grievance expiry** (4y severity-3, 2y severity-2) is recorded in the ledger but nothing expires
   automatically yet.
5. **Gate 2 currently ignores shared-class delivery.** A member who moved a major joint-fight bill
   (interchange, 1071) gets no delivery credit unless it was CU-primary. Defensible, but worth a
   deliberate ruling.

---

*Evidence appendix: `champion_gates.html` (before/after) · `champion_gates.csv` (all 533, every gate
value and fail reason) · `before_after_tier1.html` + `scenario_slots.csv` (the four retired shadow
variants, kept as the record of why gates beat re-weighting) · `grievance_ledger.ndjson` ·
`bill_beneficiary_tags.ndjson` · `beneficiary_review_queue.csv`.*
