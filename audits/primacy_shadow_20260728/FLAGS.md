# FLAGS — what is known to be weak

**Moneyball primacy tier · 2026-07-29 · read alongside `START_HERE.md`**

Everything in this package is verified to reproduce itself. That is not the same as everything
being *right*. This file is the complete list of what is thin, unproven, or deliberately deferred —
written down so nobody has to rediscover it, and so nobody presents this work as more settled than
it is.

Ordered by what would actually cost you.

---

## 🔴 Blockers — do not ship past these

### F1. Steps 1–4 without step 5 is worse than not shipping

The code change alone moves **Andy Barr from slot 12 to 37 and shows no reason anywhere.** A board
that silently demotes the subcommittee chair of jurisdiction, with no cited event and no cure
printed, gets dismissed the first time someone asks why — and they will be right to dismiss it.

**The rendered reason is the deliverable; the re-ranking is just the mechanism.** If step 5 (surface
the reason in the desk and dashboard) cannot land in the same change, do not land steps 1–4.

The desk line must show **both sides of the ledger**:

> *"French Hill — Tier 3. Conduct 8.00 (MS-2026-001, MS-2026-004) less delivery 3.00 (moved H.R.975,
> H.R.4437, H.R.4544) = net 5.00, ceiling Tier 2. Cure: any of H.R.4167 / H.R.7647 / H.R.507 /
> H.R.1791 attached to or reported through an FSC vehicle under his control."*

A staffer shown only the grievance half will dispute it, correctly.

### F2. "Rank delta zero" is a design claim, not yet a verified one

`verify.py` confirms `ranks_python.json` was never written. That is true and trivial. **The real
test is patching `fec/tier_util.py` and running `run_pipeline.py`.** Until someone does that and
diffs the ranks, the acceptance criterion of this entire piece of work is unproven. It should be
the first thing done after integration, not the last.

---

## 🟠 Substantive — these limit what the output can be trusted to say

### F3. ~38% of role weight rests on title regexes (L7)

The single largest soft spot, and it sits *underneath* the primacy factor, which sits underneath
everything else. 178 acts are classified by pattern-matching their titles. Every one is in
`beneficiary_review_queue.csv`, weight-sorted. **The right instrument is Quorum's full export with
its AI summaries** — see F4.

### F4. The Quorum full export is the highest-value input by a wide margin

One export unblocks three separate problems at once:

1. **F3**, the L7 title-rule mass.
2. **Cortez Masto's two FHLB bills** (`S.1684|117`, `S.1439|119`). Plausibly `cu_primary` on the
   same reasoning that promoted H.R.7647, currently `shared`. **Cannot be adjudicated** — the bundle
   summaries are 51 and 47 characters, the title and nothing else. Only 11 of her 24 acts carry
   usable text. Promoting them without evidence is exactly the circularity error that cost five
   members their seats earlier in this work.
3. **F7**, the 559 acts with no authoritative ACU position.

### F5. The delivery ledger is a general mechanism built on a sample of one

`delivery_ledger.ndjson` has **French Hill 3.00, John Rose 0.38, Mike Bost 0.38, everyone else
zero.** The shape is right and the arithmetic is tested, but it has not been stress-tested by
contact with more data.

Worse, it **systematically understates every committee chair**: the highest-agency instrument —
*reporting a bill out of committee under your own gavel*, weight 1.00 — is **not extractable**.
Nothing in the corpus records markup outcomes by member. Only `floor_managed` events exist today.

And the speech corpus is CU-scoped (307 rows), so this measures floor management *within
credit-union floor debate*. That is the correct scope for this purpose, but it is **not a census of
legislative throughput. Do not compare members on totals.**

### F6. Both ledgers measure the ledger, not the world

Effective severity and delivered credit are both sums over *logged* events. **This bit twice in one
day:**

- First, Barr (7.25) out-scored Hill (6.00) — the arithmetic called Barr the worse actor when Hill
  was the chair *and* the author of the vehicle. Barr simply had two grievances written down and
  Hill one.
- Then Hill was nearly taken off the board entirely, because his three floor-managed credit-union
  bills were written down nowhere.

**A conduct system that can only subtract will eventually be wrong about someone, in the direction
hardest to walk back.** The mitigation is procedural, not code: for every vehicle in either ledger,
sweep *every* member with leverage over it — chair, ranking member, subcommittee chair, sponsor,
original cosponsors — on both sides. A partial sweep ranks whoever got researched hardest.

Asserted in `test_ladder_counts_events_so_completeness_matters` so it stays explicit.

**Corollary for anyone maintaining this: if a member's placement looks wrong, the first hypothesis
should be a missing ledger row, not a wrong constant.** That was true both times it came up. See
`CONDUCT_LADDER.md` §5 for a multiplier that was tuned toward a destination and then had to be cut
back — recorded on purpose.

### F7. Only 55 of 614 acts carry an authoritative ACU position

The other 559 came from the outline's search queries, not its named-bill list. Highest-risk
unknowns are bills in the two **defensive** categories (Interchange, Credit Card & Consumer-Fee
Mandates) that are not registry anchors: a CCCA companion or fee-mandate bill introduced after the
outline was written currently scores **+0.5 instead of −1.0 — a 1.5-point sign error per act.**

### F8. The role vocabulary has no `floor_manager`

`sponsor` / `original` / `cosponsor` is the entire set. French Hill carried H.R.975 Credit Union
Board Modernization across the House floor, saying on the record it *"will be a great service to
those credit unions"* — and appears nowhere among that bill's **23 credited members.**

Delivery is deliberately kept **out** of the primacy factor (primacy answers *champion for whom*;
delivery answers *did you spend your position*, and merging them corrupts the beneficiary ratio),
but the desk should surface it beside the factor.

### F9. Five registry anchor bills were lost at collection

S.427 / H.R.3380 TAILOR, S.3940 AFFORD, S.1880 CDFI Bond Guarantee, and **H.R.1 — the last tagged
Credit Union Tax Status.** Present in neither `member_desk_bundle.json` nor any workbook role
sheet, so the loss is at **collection, not scoring.** It took a lucky document upload to notice.
`INTEGRATION.md` proposes a registry-vs-collected reconciliation audit so it cannot happen silently
again.

---

## 🟡 Known and deferred — fine to leave, but do not forget

### F10. Nothing expires

`decay_years` is recorded on every grievance event and read by nothing. MS-2026-003 and MS-2026-004
are 2-year clocks from July 2026, so this does not bite until 2028 — but an expiry pass should exist
before then, or the ledger becomes a permanent record of a single week in July.

### F11. `SHRINK_ANCHOR = 15` is inherited, not derived

Taken from `build_media_blend`'s press convention. The legislative agenda's median credit is **2.6**
and 98% of the roster sits below the anchor, so it is doing real work un-examined. Loosening it was
tested and made the board worse — but that is evidence it matters, not evidence it is right.

### F12. `OPPOSE_W = −1.0` is a values judgment

Set symmetric with `cu_primary = +1.0`: opposing on Interchange is treated as exactly as
consequential as helping. Defensible, not derived. No member currently ends with a negative factor;
the most adverse is Zoe Lofgren at +0.100.

### F13. Decay asymmetry between the pillar and the factor

`Leg%` applies the workbook's `DecayWeight`; the primacy factor does not. A 117th-Congress
cosponsorship weighs the same as a 119th inside the ratio. Not fatal, but it quietly favours members
whose credit-union work is old.

### F14. Ladder rungs 3 / 6 / 9 are a first proposal

Evenly spaced, and they place the two known cases sensibly — but with only two capped members,
nothing has really tested them. Hill sat at exactly 6.00 before the delivery ledger, which is closer
to a boundary than is comfortable. Revisit once the ledger holds more than a handful of events.

### F15. Maxine Waters cannot be seated by any primacy change

Her factor is **+0.5922, above the 0.5024 baseline** — she passes the axis this work was built to
test. Her constraint is **`Leg% = 0.641`** (22 sponsor, 2 original, **7 cosponsor**; decay-weighted
18.11 against Cortez Masto's 25.10 and Barr's 51.25). She is an author, not a joiner, and the Leg
pillar rewards cosponsorship breadth.

`0.641 × 1.00` — a perfect factor — is still roughly slot 40. **Moving her means moving `Leg%`,
which moves rank, which is outside this work's contract.** If the org's view is that leading the
CDFI letter should count like authorship, the lever is `LETTER_W` or the Leg pillar's role weights.
Not primacy.

### F16. H.R.7056 Community Bank Regulatory Tailoring Act sits at `cu_primary`

The outline files it under Exam & Supervision (a CU-scoped section) and ACU supports it, so the
framework's precedence produces this — but the title argues `shared`. One row, one judgment call,
sub-threshold either way.

---

## What is *not* on this list

The three configuration questions that were open on 2026-07-29 are **closed** — see
`START_HERE.md` §7. Tier 1 size, letter signatory weight, and Dan Sullivan's seat are decided, not
deferred.
